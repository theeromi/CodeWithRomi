#!/bin/bash
# Open the Video Shorts Pipeline GUI (path + clip count + live logs).
# Uses system Python if venv has no tkinter; pipeline still runs in venv.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [ -d "venv" ]; then
  source venv/bin/activate
fi
# Prefer venv Python; if tkinter is missing, use system Python.
# On Ubuntu/Debian install GUI support once: sudo apt install python3-tk
if python3 -c "import tkinter" 2>/dev/null; then
  exec python3 gui.py
else
  exec /usr/bin/python3 gui.py
fi
