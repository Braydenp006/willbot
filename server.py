import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pipeline import webTranscribe, AIresponse, voiceResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/voicelines", StaticFiles(directory="voice/voicelines"), name="voicelines")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    history = []
    while True:
        data = await websocket.receive_bytes()
        print(f"got {len(data)} bytes")
        heard = await asyncio.to_thread(webTranscribe, data)
        chunks = AIresponse(heard, history)
        # pull each chunk off the LLM stream in a thread so the event loop stays free
        while (chunk := await asyncio.to_thread(next, chunks, None)) is not None:
            wav = await asyncio.to_thread(voiceResponse, chunk)
            await websocket.send_bytes(wav)
        await websocket.send_text("done")
