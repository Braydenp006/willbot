# willbot

I missed my friend william so much I make a second one of him

This features a webpage with a talking head, allowing you to speak to it through your browser.

Pipeline: browser mic → [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (speech to text) → [Ollama](https://ollama.com) (character LLM) → [Chatterbox](https://github.com/resemble-ai/chatterbox) (voice clone) → three.js head that lip-syncs to the audio.

The personal files (voice sample, 3D head, Modelfile) are not in this repo. You supply your own.

## Setup

Python 3.11 and [Ollama](https://ollama.com) are required. A CUDA GPU is used if available; on CPU it falls back to smaller/faster models.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Make it your own person

You need four files (paths are fixed in the code; rename to match or edit the code):

| File | What it is |
|---|---|
| `voice/WillVoiceFinal.wav` | ~10–20 s clean recording of the person speaking. Chatterbox clones this voice. |
| `static/will.glb` | 3D head model. For lip sync it needs a shape key / morph target named `jawOpen`. |
| `voice/voicelines/mmm.wav` | Sound played when you click the head to satisfy it's hunger. Generate one with `python makevoiceline.py`. |
| Ollama model `will` | The personality, built from a Modelfile (below). |

Create the character model:

```sh
cp Modelfile.example Modelfile   # fill in the <placeholders>
ollama create will -f Modelfile
```

(To use a different name, change `OLLAMA_MODEL` in `pipeline.py`.)

## How to use william
```sh

`start.sh` is for my setup using fish shell + Tailscale to reach it from a phone. Not needed locally

clone this repo, add the required files and install all requiremnts previously stated

if you are in a fish shell cd into the repo and run ./start.sh, it should ask for your password

Open http://localhost:8000, hold the button (or Space) and talk.

## Extra stuff

`python pipeline.py` runs a terminal-only version using your mic directly, used for testing, 
no 3d head in this version.

'python makevoiceline.py' can generate any voiceline you want, it'll ask for a text input and 
the output file name, using the same voice chatterbox uses defined in your piepline.py
