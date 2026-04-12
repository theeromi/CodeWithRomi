#!/usr/bin/env python3
"""
Direct video processing — for videos that are already shorts-length.

Usage:
  python run_direct.py /path/to/clip.mp4 --mode vertical-captions
  python run_direct.py /path/to/clip.mp4 --mode captions-only

Modes:
  vertical-captions  — Convert to 1080×1920 (9:16) and add per-word captions
  captions-only      — Keep original dimensions, only add per-word captions
"""
from __future__ import annotations

import os
import sys

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Find CUDA libs before importing GPU-accelerated libraries
for _cuda in ("/usr/local/lib/ollama/cuda_v12", "/usr/local/lib/ollama/cuda_v13"):
    if os.path.exists(_cuda):
        os.environ["LD_LIBRARY_PATH"] = _cuda + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        break

import argparse
from pathlib import Path

from output_layout import ensure_image_gen_output, ensure_pipeline_output_dirs

PROJECT_ROOT = Path(__file__).resolve().parent


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe + format a shorts-length video for TikTok/YouTube Shorts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--mode",
        choices=["vertical-captions", "captions-only"],
        required=True,
        help="vertical-captions: resize to 9:16 + captions | captions-only: captions only",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="Where to save output (default: project directory)",
    )
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        log(f"Error: Video not found: {video_path}")
        sys.exit(1)

    out_dir = ensure_pipeline_output_dirs(
        Path(args.output_dir).resolve() if args.output_dir else PROJECT_ROOT
    )
    ensure_image_gen_output(PROJECT_ROOT)

    mode_label = {
        "vertical-captions": "Convert to Vertical + Captions",
        "captions-only": "Add Captions Only",
    }[args.mode]

    log("=" * 70)
    log(f"DIRECT PROCESSING — {mode_label}")
    log("=" * 70)
    log(f"Video:  {video_path}")
    log(f"Output: {out_dir}")
    log("")

    # Step 1: Transcribe
    log(">>> STEP 1/2: TRANSCRIPTION (Whisper)")
    log("-" * 70)
    try:
        from test_transcription import transcribe_and_save
    except ImportError as e:
        log(f"Error: Could not import transcription module: {e}")
        sys.exit(1)

    transcript_file = transcribe_and_save(str(video_path), output_dir=str(out_dir))
    transcript_file = str(Path(transcript_file).resolve())

    # Free Whisper VRAM before video processing starts
    try:
        from test_transcription import _model as _whisper_ref
        import test_transcription
        test_transcription._model = None
        import torch, gc
        gc.collect()
        torch.cuda.empty_cache()
        log("   VRAM freed after transcription.")
    except Exception:
        pass
    log("")

    # Step 2: Process video
    log(f">>> STEP 2/2: VIDEO PROCESSING ({mode_label})")
    log("-" * 70)
    try:
        from clip_generator import process_single_video
    except ImportError as e:
        log(f"Error: Could not import clip_generator: {e}")
        sys.exit(1)

    process_single_video(str(video_path), transcript_file, str(out_dir), mode=args.mode)

    log("")
    log("=" * 70)
    log("DONE")
    log("=" * 70)
    log(f"Output: {out_dir / 'generated_clips'}")
    log("")


if __name__ == "__main__":
    main()
