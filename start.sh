#!/bin/sh

cleanup() {
  echo "Ctrl+C pressed, cleaning up..."
  tailscale serve reset$()
  kill "$UVICORN" 2>/dev/null
  pkill -x ollama # frees the GPU; pipeline.py keeps the model loaded forever
  exit 0
}
trap cleanup INT TERM

# user-level ollama, not the system service: that one runs as another user and can't see the `will` model

if ! pgrep -x ollama >/dev/null; then
  ollama serve >/dev/null 2>&1 &
fi

sudo systemctl start tailscaled
tailscale up
tailscale serve --bg 8000

cd "$(dirname "$(realpath "$0")")" || exit 1
. .venv/bin/activate
uvicorn server:app --reload &
UVICORN=$!
wait "$UVICORN"
