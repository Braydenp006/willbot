#!/bin/sh

cleanup() {
  echo "Ctrl+C pressed, cleaning up..."
  tailscale serve reset$()
  kill "$UVICORN" 2>/dev/null
  pkill -x ollama # frees the GPU; pipeline.py keeps the model loaded forever
  exit 0
}
trap cleanup INT TERM HUP # HUP: ssh session dropped

# user-level ollama, not the system service: that one runs as another user and can't see the `will` model

if ! pgrep -x ollama >/dev/null; then
  ollama serve >>"$(dirname "$(realpath "$0")")/ollama.log" 2>&1 &
fi

sudo systemctl start tailscaled
tailscale up
tailscale serve --bg 8000

cd "$(dirname "$(realpath "$0")")" || exit 1
. venv/bin/activate
pkill -f "uvicorn server:app" && sleep 1 # leftover from a run whose cleanup never fired
uvicorn server:app &
UVICORN=$!
wait "$UVICORN"
