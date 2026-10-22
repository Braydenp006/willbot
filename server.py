import asyncio
import logging
import music
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pipeline import webTranscribe, AIresponse, voiceResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount(
    "/voicelines", StaticFiles(directory="Assets/voice/voicelines"), name="voicelines"
)

COMMANDS = {
    "PLAY": music.play,
    "PAUSE": music.pause,
    # "LIGHTS": lights.set,  # future commands go here
}

def run_commands(reply):
    spoken = []
    for line in reply.splitlines():
        name, sep, arg = line.partition(":")
        if sep and name in COMMANDS:
            try:
                COMMANDS[name](arg.strip())
            except Exception as e:
                print(f"{name} failed:", e)
        else:
            spoken.append(line)
    return "\n".join(spoken)

@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/ping")
def ping():
    return {}


# the page polls /ping every few seconds; keep it out of the access log
logging.getLogger("uvicorn.access").addFilter(lambda r: r.args[2] != "/ping")


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    history = []
    while True:
        try:
            data = await websocket.receive_bytes()
        except WebSocketDisconnect:  # tab closed or server shutting down
            return
        print(f"got {len(data)} bytes")
        heard = await asyncio.to_thread(webTranscribe, data)
        if not heard:  # silence or noise; tell the page we're done so it can listen again
            await websocket.send_text("done")
            continue
        chunks = AIresponse(heard, history)
        # pull each chunk off the LLM stream in a thread so the event loop stays free
        while (chunk := await asyncio.to_thread(next, chunks, None)) is not None:
            chunk = await asyncio.to_thread(run_commands, chunk)
            if not chunk.strip():  # chunk was only a PLAY: line
                continue
            wav = await asyncio.to_thread(voiceResponse, chunk)
            await websocket.send_bytes(wav)
        await websocket.send_text("done")
