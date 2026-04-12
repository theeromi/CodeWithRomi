# Video Shorts Pipeline

**Owner:** [CodeWithRomi](https://codewithromi.com). Use is subject to the [Terms of Use](TERMS.md) (no warranty, no liability).

Turn long-form videos into short, standalone clips for **YouTube Shorts** and **TikTok**—using local AI for transcription and clip selection.

## What it does

1. **Transcribe** – Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (GPU) to transcribe the video and get word-level timestamps.
2. **Analyze** – Uses [Ollama](https://ollama.com/) (local LLM, default chain: qwen2.5:32b → qwen2.5:14b → llama3.1:8b) to pick **separate highlight moments** from the transcript. Each clip is chosen so it:
   - Expresses **one clear point** (learning step, how-to, or something cool like an installation/demo).
   - Is **not cut off**—viewer understands what they saw.
   - Uses **whole transcript segments** only (no mid-sentence cuts).
   - Is **30 seconds to 3 minutes** (whatever length the moment needs).
3. **Generate** – Uses [MoviePy](https://github.com/Zulko/moviepy) to cut those ranges, fit them to **9:16 (1080×1920)** with full frame visible (letterbox/pillarbox), add per-word highlighted captions, and export H.264/AAC files ready for Shorts/TikTok.

Additionally:

4. **Thumbnails** – AI-generated thumbnail backgrounds with title text overlay, using FLUX.1-schnell (8-bit quantized).
5. **Transition clips** – AI-generated animated backgrounds with Ken Burns zoom and fade effects.
6. **Format + Captions** – Convert an already-shorts-length video to 9:16 with captions.
7. **Captions Only** – Add per-word highlighted captions to an already-formatted video.

Output goes to **`generated_clips/`** (e.g. `clip_01_Title Here.mp4`) and **`image_gen/output/`** for thumbnails/transitions.

## Requirements

- **Python 3.10+** with `venv`
- **GPU** – NVIDIA RTX 3090 (24 GB VRAM) or similar; CUDA 12 libs
- **Ollama** installed and running (for clip selection)
- **ffmpeg** (for encoding; system ffmpeg with NVENC support recommended)

## Tested / PC specs

Pipeline developed and tested on:

| Component | Spec |
|-----------|------|
| **Host** | MinisForum UM890 Pro (AMD Ryzen 9 8945HS, 30 GB RAM) |
| **GPU** | NVIDIA GeForce RTX 3090, 24 GB VRAM (connected via OCuLink) |
| **OS** | Linux (Ubuntu 24.04) |
| **CUDA** | 12.2 (driver 535); CUDA libs from Ollama |

- **24 GB VRAM** comfortably fits: faster-whisper **large-v3** (~3 GB), Ollama models up to 32B (Q4), FLUX.1-schnell 8-bit for thumbnails (~11.5 GB load / ~17 GB peak), and NVENC encoding — all run sequentially so they never overlap.
- If the GPU is external (e.g. OCuLink), ensure the driver and CUDA libs are available to the process (e.g. `run.sh` sets `LD_LIBRARY_PATH` for Ollama's CUDA).

> **Note on NVIDIA drivers:** Driver 535 (CUDA 12.2) is confirmed working. Driver 590 (CUDA 13.1) causes CTranslate2 crashes with faster-whisper — avoid it until CTranslate2 adds CUDA 13 support.

## Project structure

```
video-automation/
├── README.md                 # This file
├── README_GUI.md             # GUI setup + clip quality / AI model
├── run.sh                    # CLI pipeline (sets GPU libs, runs pipeline)
├── run_gui.sh                # Launch GUI
├── run_pipeline.py           # Full pipeline: transcribe → analyze → generate
├── run_direct.py             # Direct processing: format + captions / captions only
├── run_image.py              # Thumbnail + transition clip generation
├── test_transcription.py     # Whisper transcription → JSON
├── clip_analyzer.py          # Ollama: pick clip ranges from transcript
├── clip_generator.py         # MoviePy: cut, resize to 9:16, captions, export
├── gui.py                    # GUI: tabs for all modes, live logs
├── image_gen/                # AI image generation
│   ├── image_generator.py    # FLUX.1-schnell 8-bit model wrapper
│   ├── thumbnail_generator.py# AI background + title text → JPEG
│   └── transition_generator.py# AI background + Ken Burns zoom → MP4
├── Video-Shorts-Pipeline.desktop  # Desktop launcher (optional)
├── venv/                     # Python virtualenv
├── generated_clips/          # Output MP4s + .meta.json (created on first run)
└── image_gen/output/         # Thumbnails (JPEG) and transition clips (MP4)
```

## Installation

```bash
cd video-automation
python3 -m venv venv
source venv/bin/activate
pip install faster-whisper moviepy diffusers transformers accelerate sentencepiece bitsandbytes
```

Install **Ollama** from [ollama.com](https://ollama.com) and pull the default models:

```bash
ollama pull qwen2.5:32b    # 19 GB — best quality, uses most of 24 GB VRAM
ollama pull qwen2.5:14b    # 9 GB — good quality, comfortable fit
ollama pull llama3.1:8b    # 5 GB — fast fallback
```

On **Ubuntu/Debian**, for GUI support:

```bash
sudo apt install python3-tk
```

### Windows quick setup

From PowerShell or Command Prompt in the project folder:

```bat
install.bat
```

What `install.bat` does:
- Creates `venv` and installs Python dependencies from `requirements.txt`
- Verifies required modules for the core pipeline (`faster-whisper`, `moviepy`, `pillow`)
- Installs optional image-generation dependencies (`torch`, `diffusers`, `transformers`, `accelerate`, `sentencepiece`, `bitsandbytes`)
- Checks for `ffmpeg` and `ollama` and attempts install via `winget` when available

After setup:

```bat
run_gui.bat
```

or

```bat
run.bat "C:\path\to\video.mp4" --clips 5
```

For image generation on Windows:

```bat
run_image.bat --mode thumbnail-clips --clips-json "C:\path\to\video_clips.json"
```

`run.bat` and `run_gui.bat` also self-check the environment and call `install.bat` automatically if required dependencies are missing.

## Usage

### GUI (recommended)

Five tabs: Full Pipeline, Format + Captions, Captions Only, Thumbnail, Transition Clip.

```bash
./run_gui.sh
```

See **README_GUI.md** for desktop launcher setup.

### Command line — Full pipeline

```bash
./run.sh "/path/to/your/video.mov" --clips 5
```

- **`--clips N`** – Number of clips to find (1–10). Default: 5.
- **`--output-dir DIR`** – Where to write output. Default: project directory.

### Command line — Direct processing

```bash
# Convert to 9:16 + add captions
python run_direct.py "/path/to/clip.mp4" --mode vertical-captions

# Add captions only (keep original dimensions)
python run_direct.py "/path/to/clip.mp4" --mode captions-only
```

### Command line — Thumbnails

```bash
# Generate thumbnails for all clips from a pipeline run
python run_image.py --mode thumbnail-clips --clips-json Bookstack_clips.json --aspect 9:16

# Single custom thumbnail
python run_image.py --mode thumbnail-custom --prompt "dark tech setup" --title "My Title"

# Transition clip
python run_image.py --mode transition --prompt "neon particles" --duration 2 --fade both
```

## Output

| Output | Description |
|--------|-------------|
| `generated_clips/*.mp4` | 1080×1920, 9:16, H.264/AAC, per-word captions — ready for TikTok & YouTube Shorts |
| `generated_clips/*.meta.json` | YouTube-ready metadata: title, description, hashtags per clip |
| `image_gen/output/*.jpg` | AI-generated thumbnails (JPEG, 95% quality) |
| `image_gen/output/*.mp4` | Transition clips with Ken Burns zoom + fade |
| `*_transcript.json` | Transcript with segments and word timestamps |
| `*_clips.json` | Clip ranges (start/end) and titles from the AI |

## Clip quality and AI model

- Clips are chosen so each **expresses one clear point** and is **not cut off**.
- The AI picks **separate** moments from different parts of the video (no back-to-back chunks).
- Transcript is split into **6-minute sections** for analysis, reducing context pressure on the LLM.
- Default model chain: **qwen2.5:32b → qwen2.5:14b → llama3.1:8b** (tries each in order; uses the first that works).
- Override with environment variables:

  ```bash
  export CLIP_ANALYZER_MODEL=mistral
  # or
  export CLIP_ANALYZER_MODEL_CHAIN="qwen2.5:14b,llama3.1:8b"
  ```

- **Step 2 (Clip Analysis) can be slow** on long videos. Each section can take 1–5 minutes. A progress indicator shows elapsed time and output lines received.

## Thumbnail generation

Uses **FLUX.1-schnell** (Black Forest Labs) with **8-bit quantization** via `bitsandbytes`:
- **11.5 GB VRAM** load, **~17 GB peak** during inference — fits comfortably on 24 GB GPUs
- 4 inference steps (FLUX schnell is a distilled model), ~3.5 minutes per 1024×1024 image on 3090
- Dramatically better quality than SDXL — clean scenes, no garbled text artifacts, photorealistic output
- Dark gradient overlay + bold title text with word-wrap and shadow
- Supports 16:9 (YouTube) and 9:16 (Shorts) aspect ratios
- Downloads ~24 GB on first run, cached in `~/.cache/huggingface/hub/`
- Requires accepted license at [huggingface.co/black-forest-labs/FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) and `huggingface-cli login`

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `large-v3` | Whisper model size |
| `WHISPER_DEVICE` | `cuda` | `cuda` or `cpu` |
| `WHISPER_COMPUTE_TYPE` | `int8_float16` | Quantization type |
| `CLIP_ANALYZER_MODEL` | *(auto)* | Force a specific Ollama model |
| `CLIP_ANALYZER_MODEL_CHAIN` | `qwen2.5:32b,qwen2.5:14b,llama3.1:8b` | Fallback model chain |
| `CLIP_ANALYZER_TIMEOUT_SECONDS` | `900` | Per-model timeout |
| `CLIP_SECTIONAL_ANALYSIS` | `1` | Split long transcripts into sections |
| `CLIP_SECTION_SECONDS` | `360` | Section length for analysis |
| `CLIP_MIN_SECONDS` | `30` | Minimum clip duration |
| `CLIP_MAX_SECONDS` | `180` | Maximum clip duration (3 min Shorts limit) |
| `CLIP_MIN_GAP_SECONDS` | `12` | Minimum gap between clips |
| `CLIP_ENCODER` | `auto` | Video encoder: `auto`, `gpu` (NVENC), or `cpu` (libx264) |
