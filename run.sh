#!/bin/bash
# Run the video shorts pipeline with GPU (CUDA) support.
# This sets LD_LIBRARY_PATH so the loader finds libcublas.so.12 (e.g. from Ollama).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prepend Ollama CUDA libs so faster_whisper can use the GPU
for CUDA_DIR in "/usr/local/lib/ollama/cuda_v12" "/usr/local/lib/ollama/cuda_v13"; do
  if [ -d "$CUDA_DIR" ]; then
    export LD_LIBRARY_PATH="$CUDA_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    break
  fi
done

# Activate venv if present
if [ -d "venv" ]; then
  source venv/bin/activate
fi

exec python run_pipeline.py "$@"
