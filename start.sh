#!/usr/bin/env fish

function _cleanup --on-signal INT
  echo "Ctrl+C pressed, cleaning up..."
  sudo tailscale serve reset
  sudo systemctl stop tailscaled
  pkill -x ollama  # frees the GPU; pipeline.py keeps the model loaded forever
end

# user-level ollama, not the system service: that one runs as another user and can't see the `will` model
pgrep -x ollama >/dev/null; or ollama serve >/dev/null 2>&1 &
sudo systemctl start tailscaled
tailscale up
tailscale serve --bg 8000
source .venv/bin/activate.fish
uvicorn server:app --reload
