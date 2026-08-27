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

CN_DIR="$ROOT/ComfyUI/models/controlnet"
mkdir -p "$CN_DIR"
if [[ ! -s "$CN_DIR/control_v11f1p_sd15_depth.pth" ]]; then
  curl -L --fail --retry 3 -o "$CN_DIR/control_v11f1p_sd15_depth.pth" \
    https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11f1p_sd15_depth.pth
fi
if [[ ! -s "$CN_DIR/control_v11p_sd15_lineart.pth" ]]; then
  curl -L --fail --retry 3 -o "$CN_DIR/control_v11p_sd15_lineart.pth" \
    https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_lineart.pth
fi

LORA_DIR="$ROOT/ComfyUI/models/loras"
mkdir -p "$LORA_DIR"
if [[ ! -s "$LORA_DIR/storybook_anime_lora.safetensors" ]]; then
  curl -L --fail --retry 3 -o "$LORA_DIR/storybook_anime_lora.safetensors" \
    https://huggingface.co/neonforestmist/sd15-storybook-anime-lora/resolve/main/storybook_anime_lora.safetensors
fi

echo "Start ComfyUI with:"
echo "  cd \"$ROOT/ComfyUI\" && .venv/bin/python main.py --port 8188 --listen 127.0.0.1"
echo "Then: PYTHONPATH=src python scripts/v2b_panel.py --comfy-only"
