# Video Shorts Pipeline – GUI

This page covers **GUI setup** and **clip quality / AI model**. For project overview, pipeline steps, and project structure see **README.md**.

---

## 1. Install GUI support (one-time)

On Ubuntu/Debian the GUI needs **tkinter**. Install it once:

```bash
sudo apt install python3-tk
```

(Your venv will then use it; no need to recreate the venv.)

## 2. Run the GUI

**From terminal:**
```bash
cd /home/dimandem/video-automation
./run_gui.sh
```

**Double-click to run like an app:**

1. Install `python3-tk` (see above).
2. Make the launcher runnable and (optional) copy to Desktop:
   ```bash
   chmod +x /home/dimandem/video-automation/Video-Shorts-Pipeline.desktop
   # Optional: copy to Desktop so you can double-click it
   cp /home/dimandem/video-automation/Video-Shorts-Pipeline.desktop ~/Desktop/
   ```
3. In the file manager, right-click the desktop file → **Allow Launching** (or **Properties → Permissions → Allow executing as program**).
4. Double-click **Video Shorts Pipeline** to open the GUI.

If the app doesn’t start, run `./run_gui.sh` in a terminal once to see any error (e.g. “No module named 'tkinter'” → install `python3-tk`).

---

## Clip quality & AI model

The pipeline uses **Ollama** (local AI) to choose which parts of the video become clips. Default model: **Mistral**. Clips are chosen so each expresses one clear point, is not cut off, and is from a different part of the video (whole segments only, 30s–3 min).

**If clips still feel off**, you can try another Ollama model (no code change):

```bash
# Use Mistral (often good at instructions)
export CLIP_ANALYZER_MODEL=mistral
./run_gui.sh

# Or Qwen 2.5 7B
export CLIP_ANALYZER_MODEL=qwen2.5:7b
./run.sh "/path/to/video.mov" --clips 5
```

On a 3090 (24 GB), pull the best models for the highest quality clip selection:

```bash
ollama pull qwen2.5:32b
ollama pull qwen2.5:14b
ollama pull llama3.1:8b
```

Lighter fallbacks if needed: `llama3.2:3b`, `phi3`, `gemma2:2b`.

### Best quality profile (closest to Opus-style)

If your goal is clip quality over speed, run GUI/CLI with:

```bash
export CLIP_ANALYZER_MODEL_CHAIN=qwen2.5:32b,qwen2.5:14b,llama3.1:8b
export CLIP_SECTIONAL_ANALYSIS=1
export CLIP_SECTION_SECONDS=720
export CLIP_MIN_SECONDS=30
export CLIP_MIN_GAP_SECONDS=12
export CLIP_MAX_SECONDS=180
export WHISPER_MODEL=large-v3
export WHISPER_DEVICE=cuda
export WHISPER_COMPUTE_TYPE=int8_float16
export CLIP_ENCODER=auto
./run_gui.sh
```

Model behavior:

- Tries models in order from `CLIP_ANALYZER_MODEL_CHAIN`.
- Uses small transcript sections sequentially, so each call has lower context pressure.

If you want a lighter setup:

```bash
export CLIP_ANALYZER_MODEL_CHAIN=llama3.1:8b
```
