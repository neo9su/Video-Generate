#!/bin/bash
# Start ComfyUI for Sulphur 2 video generation
# Run on GPU server (10.190.0.222)
# Usage: bash start_comfyui.sh

set -e

# Activate conda env
source ~/miniconda3/etc/profile.d/conda.sh
conda activate comfyui

cd ~/ComfyUI

# Ensure model symlinks are correct
echo "[ComfyUI] Checking Sulphur 2 model..."
if [ ! -f "models/checkpoints/sulphur_dev_fp8mixed.safetensors" ]; then
    echo "ERROR: Sulphur 2 FP8 model not found!"
    exit 1
fi

echo "[ComfyUI] Model found. Starting server..."
echo "[ComfyUI] Access: http://$(hostname -I | awk '{print $1}'):8188"

# Start ComfyUI with:
# --listen: allow remote connections
# --port 8188: standard port
# --disable-auto-launch: don't try to open browser
# --lowvram: optimize for 24GB GPU
exec python3 main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --disable-auto-launch \
    --preview-method auto
