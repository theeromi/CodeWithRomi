#!/usr/bin/env python3
"""
Run full pipeline: transcribe video → analyze for clips → generate Shorts/TikTok clips.
Pass the video path when you run; logs stream to the terminal so you see status live.

Usage:
  python run_pipeline.py "/path/to/your/video.mov"
  python run_pipeline.py "/path/to/video.mp4" --min-clips 5
"""
from __future__ import annotations

import os
import sys

# Windows consoles often use cp1252; project output uses ✓ and emoji in prints
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Find CUDA 12 libs (e.g. Ollama’s) so faster_whisper can use the GPU
for _cuda in ("/usr/local/lib/ollama/cuda_v12", "/usr/local/lib/ollama/cuda_v13"):
    if os.path.exists(_cuda):
        os.environ["LD_LIBRARY_PATH"] = _cuda + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        break

import argparse
from pathlib import Path

from output_layout import ensure_image_gen_output, ensure_pipeline_output_dirs

# Ensure we run from project root so transcript/clips JSON and generated_clips/ land here
PROJECT_ROOT = Path(__file__).resolve().parent


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe video → find clip moments → generate TikTok/Shorts clips.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "video",
        type=str,
        help="Path to the video file (e.g. /home/user/Downloads/My video.mov)",
    )
    parser.add_argument(
        "--clips",
        type=int,
        default=5,
        metavar="N",
        help="Number of clips to find (1–10, default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        metavar="DIR",
        help="Directory for transcript/clips JSON and generated_clips (default: project directory)",
    )
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        log(f"Error: Video not found: {video_path}")
        sys.exit(1)

    n_clips = args.clips
    if not (1 <= n_clips <= 10):
        log("Error: --clips must be between 1 and 10.")
        sys.exit(1)

    out_dir = ensure_pipeline_output_dirs(
        Path(args.output_dir).resolve() if args.output_dir else PROJECT_ROOT
    )
    ensure_image_gen_output(PROJECT_ROOT)

    log("=" * 70)
    log("VIDEO SHORTS PIPELINE")
    log("=" * 70)
    log(f"Video:    {video_path}")
    log(f"Output:   {out_dir}")
    log(f"Clips:    {n_clips}")
    log("")

    # Step 1: Transcribe
    log(">>> STEP 1/3: TRANSCRIPTION (Whisper)")
    log("-" * 70)
    try:
        from test_transcription import transcribe_and_save
    except ImportError as e:
        log(f"Error: Could not import transcription module: {e}")
        sys.exit(1)

    transcript_file = transcribe_and_save(str(video_path), output_dir=str(out_dir))
    transcript_file = str(Path(transcript_file).resolve())

    # Free Whisper VRAM before Ollama / MoviePy stages
    try:
        import test_transcription, torch, gc
        test_transcription._model = None
        gc.collect()
        torch.cuda.empty_cache()
        log("   VRAM freed after transcription.")
    except Exception:
        pass
    log("")

    # Step 2: Analyze for clips (Ollama)
    log(">>> STEP 2/3: CLIP ANALYSIS (Ollama)")
    log("-" * 70)
    try:
        from clip_analyzer import analyze_transcript_for_clips
    except ImportError as e:
        log(f"Error: Could not import clip_analyzer: {e}")
        sys.exit(1)

    analyze_transcript_for_clips(transcript_file, min_clips=n_clips)
    clips_file = transcript_file.replace("_transcript.json", "_clips.json")
    if not Path(clips_file).exists():
        log("Error: Clips file was not created.")
        sys.exit(1)
    log("")

    # Step 3: Generate clip videos
    log(">>> STEP 3/3: GENERATE CLIPS (MoviePy)")
    log("-" * 70)
    try:
        from clip_generator import generate_clips
    except ImportError as e:
        log(f"Error: Could not import clip_generator: {e}")
        sys.exit(1)

    # Run from output dir so generated_clips is created there
    orig_cwd = Path.cwd()
    try:
        os.chdir(out_dir)
        generate_clips(clips_file, transcript_file)
    finally:
        os.chdir(orig_cwd)

    log("")
    log("=" * 70)
    log("PIPELINE COMPLETE")
    log("=" * 70)
    log(f"Transcript:  {transcript_file}")
    log(f"Clips list:  {clips_file}")
    log(f"Videos:      {out_dir / 'generated_clips'}")
    log("")


if __name__ == "__main__":
    main()
