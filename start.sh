#!/usr/bin/env fish

function _cleanup --on-event fish_event
  echo "Ctrl+C pressed, cleaning up..."
  sudo tailscale serve reset
  sudo systemctl stop tailscaled
end

sudo systemctl start tailscaled
tailscale up
tailscale serve --bg 8000
source .venv/bin/activate.fish
uvicorn server:app --reload
