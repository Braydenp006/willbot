import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pipeline import webTranscribe, AIresponse, voiceResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount(
    "/voicelines", StaticFiles(directory="Assets/voice/voicelines"), name="voicelines"
)


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
        chunks = AIresponse(heard, history)
        # pull each chunk off the LLM stream in a thread so the event loop stays free
        while (chunk := await asyncio.to_thread(next, chunks, None)) is not None:
            wav = await asyncio.to_thread(voiceResponse, chunk)
            await websocket.send_bytes(wav)
        await websocket.send_text("done")
