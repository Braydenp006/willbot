import os, warnings

# annoying warning messages muddling my terminal
#os.environ["HF_HUB_OFFLINE"] = "1"
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
warnings.filterwarnings("ignore", message=".*LoRACompatibleLinear.*")
import json, re, subprocess, sys, time, urllib.request, torch, io
import torchaudio as ta
import sounddevice as sd
import soundfile as sf
from chatterbox.tts_turbo import ChatterboxTurboTTS
from faster_whisper import WhisperModel
from pathlib import Path

OLLAMA_MODEL = "will"
MAX_HISTORY = 20  # older messages are dropped so prompts stay short
MIN_WORDS = 6  # shorter sentences get merged into the next one
VOICE = str(Path(__file__).parent / "Assets" / "voice" / "WillVoiceFinal.wav")
history = []
# GPU on the desktop, CPU on the laptop
gpu = torch.cuda.is_available()
device = "cuda" if gpu else "cpu"
print(f"device: {device}")
# Load models once (slow the first time, they download weights)
t = time.time()
whisper = WhisperModel(
    "base.en", device=device, compute_type="float16" if gpu else "int8"
)
# Nano keeps up in real time on CPU; Turbo sounds better when a GPU can afford it
tts = ChatterboxTurboTTS.from_pretrained(device=device)
print("models initialized")
tts.prepare_conditionals(VOICE)
print("tts initialized")
OLLAMA_LOG = Path(__file__).parent / "ollama.log"


def ensure_ollama():
    """Starts `ollama serve` if it isn't answering, and waits until it is."""
    for attempt in range(40):
        try:
            urllib.request.urlopen("http://localhost:11434/", timeout=1)
            return
        except OSError:  # refused, or timed out while it boots
            if attempt == 0:
                print(f"ollama is down, restarting it (log: {OLLAMA_LOG})")
                # own session so a Ctrl+C aimed at uvicorn doesn't take ollama with it
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=open(OLLAMA_LOG, "a"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            time.sleep(0.5)
    raise RuntimeError("ollama didn't come back up, check " + str(OLLAMA_LOG))


ensure_ollama()
body = json.dumps({"model": OLLAMA_MODEL, "messages": [], "keep_alive": -1}).encode()
urllib.request.urlopen(
    urllib.request.Request(
        "http://localhost:11434/api/chat", body, {"Content-Type": "application/json"}
    )
)
print("will model initialized")


def webTranscribe(prompt):
    t = time.time()
    segments, _ = whisper.transcribe(io.BytesIO(prompt), language="en", vad_filter=True)
    heard = " ".join(s.text for s in segments).strip()
    print(f"stt:   {time.time() - t:.1f}s  -> {heard!r}")
    return heard


def AIresponse(heard, history):
    """Streams the reply, yielding whole sentences as soon as there are MIN_WORDS of them."""
    history.append({"role": "user", "content": heard})
    del history[:-MAX_HISTORY]

    ensure_ollama()
    t = time.time()
    body = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "messages": history,
            "stream": True,
            "keep_alive": -1,  # a restarted ollama would otherwise unload after 5 min
            "think": False,  # Qwen3 thinks by default
        }
    ).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        body,
        {"Content-Type": "application/json"},
    )
    reply, pending = "", ""
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            piece = json.loads(line)["message"]["content"]
            reply += piece
            pending += piece
            # only cut after a finished sentence; the tail may still be mid-sentence
            ends = [m.end() for m in re.finditer(r"[.!?]\s+", pending)]
            if ends and len(pending[: ends[-1]].split()) >= MIN_WORDS:
                print(
                    f"llm:   {time.time() - t:.1f}s  -> {pending[: ends[-1]].strip()!r}"
                )
                yield pending[: ends[-1]].strip()
                pending = pending[ends[-1] :]
    if pending.strip():
        print(f"llm:   {time.time() - t:.1f}s  -> {pending.strip()!r}")
        yield pending.strip()
    history.append({"role": "assistant", "content": reply.strip()})


def voiceResponse(reply):
    t = time.time()
    wav = tts.generate(reply)
    print(f"tts:   {time.time() - t:.1f}s  ({wav.shape[-1] / tts.sr:.1f}s of audio)")
    buf = io.BytesIO()
    ta.save(buf, wav, tts.sr, format="wav")
    return buf.getvalue()


if __name__ == "__main__":
    while True:
        ans = str(input("Press enter and talk, q to quit: "))
        if ans == "q":
            break
        # 1. Speech to text
        RATE = 16000
        SEC = 5

        audio = sd.rec(int(SEC * RATE), samplerate=RATE, channels=1, dtype="float32")
        sd.wait()

        segments, _ = whisper.transcribe(audio.flatten(), language="en")
        heard = " ".join(s.text for s in segments).strip()
        print(f"you:   {heard!r}")

        reply = " ".join(AIresponse(heard, history))

        t = time.time()
        audio = voiceResponse(reply)
        samples, rate = sf.read(io.BytesIO(audio))
        sd.play(samples, rate)
        sd.wait()
        print(f"tts:   {time.time() - t:.1f}s")
