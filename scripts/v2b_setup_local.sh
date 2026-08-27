#!/usr/bin/env bash
# Local 2B deps. Run from the repo root. Do not paste comment lines into zsh as a command.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v blender >/dev/null 2>&1 && [[ ! -x /opt/homebrew/bin/blender ]]; then
  echo "Install Blender first: brew install --cask blender" >&2
  exit 1
fi

if [[ ! -d "$ROOT/ComfyUI" ]]; then
  git clone https://github.com/comfyanonymous/ComfyUI.git "$ROOT/ComfyUI"
fi

if [[ ! -x "$ROOT/ComfyUI/.venv/bin/python" ]]; then
  "$ROOT/.venv/bin/python" -m venv "$ROOT/ComfyUI/.venv"
fi

"$ROOT/ComfyUI/.venv/bin/pip" install -U pip
"$ROOT/ComfyUI/.venv/bin/pip" install -r "$ROOT/ComfyUI/requirements.txt"

echo "Start ComfyUI with:"
echo "  cd \"$ROOT/ComfyUI\" && .venv/bin/python main.py --port 8188 --listen 127.0.0.1"
echo "Then: PYTHONPATH=src python scripts/v2b_b1_panel.py"
