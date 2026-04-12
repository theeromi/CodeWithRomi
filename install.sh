#!/bin/bash
# One-time setup: create venv and install dependencies.
# Run from the project root: ./install.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Show terms and require acceptance
if [ -f "TERMS.md" ]; then
  echo "----------------------------------------"
  cat TERMS.md
  echo "----------------------------------------"
  printf "Do you accept these terms? (yes/no): "
  read -r reply
  case "$reply" in
    [yY]es|[yY]) ;;
    *) echo "Installation cancelled."; exit 1 ;;
  esac
  echo ""
fi

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null; then
  echo "Python not found. Install Python 3.10+ and run again."
  exit 1
fi

echo "Using: $($PYTHON --version)"
echo "Creating virtual environment..."
"$PYTHON" -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Done. Activate and run:"
echo "  source venv/bin/activate"
echo "  ./run_gui.sh     # GUI"
echo "  ./run.sh /path/to/video.mp4 --clips 5"
echo ""
echo "Install Ollama from https://ollama.com and run: ollama pull qwen2.5:14b"
