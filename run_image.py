#!/usr/bin/env python3
"""
Image generation orchestrator — thumbnails and transition clips.

Usage:
  # One thumbnail per clip from an existing pipeline run
  python run_image.py --mode thumbnail-clips --clips-json /path/to/_clips.json

  # Single thumbnail from a custom prompt
  python run_image.py --mode thumbnail-custom --prompt "dark tech background" --title "My Title"

  # Animated transition clip
  python run_image.py --mode transition --prompt "cinematic particles" --duration 2 --fade both

All outputs land in image_gen/output/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# CUDA libs (same pattern as rest of the project)
for _cuda in ("/usr/local/lib/ollama/cuda_v12", "/usr/local/lib/ollama/cuda_v13"):
    if os.path.exists(_cuda):
        os.environ["LD_LIBRARY_PATH"] = _cuda + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        break

import argparse
import importlib.util

from output_layout import ensure_image_gen_output

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def log(msg: str) -> None:
    print(msg, flush=True)


def _missing_modules(mod_names: list[str]) -> list[str]:
    missing: list[str] = []
    for name in mod_names:
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    return missing


def _ensure_image_dependencies() -> None:
    required = ["torch", "diffusers", "transformers", "accelerate", "bitsandbytes", "sentencepiece"]
    missing = _missing_modules(required)
    if not missing:
        return

    log("Missing image-generation dependencies: " + ", ".join(missing))
    log("Attempting automatic install in current environment...")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "torch",
                "diffusers",
                "transformers",
                "accelerate",
                "sentencepiece",
                "bitsandbytes",
            ],
            check=True,
        )
    except Exception as e:
        log(f"Auto-install failed: {e}")

    missing = _missing_modules(required)
    if not missing:
        log("Image-generation dependencies installed successfully.")
        return

    log("Error: Still missing image-generation dependencies: " + ", ".join(missing))
    log("")
    if os.name == "nt":
        log("Run this once from project root:")
        log("  run_image.bat --help")
        log("or:")
        log("  install.bat")
    else:
        log("Install them with:")
        log("  pip install torch diffusers transformers accelerate sentencepiece bitsandbytes")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate thumbnails and transition clips.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["thumbnail-clips", "thumbnail-custom", "transition"],
    )
    parser.add_argument("--clips-json", default=None, help="Path to _clips.json")
    parser.add_argument("--prompt", default="", help="AI image prompt")
    parser.add_argument("--title", default="", help="Title text overlay (thumbnails)")
    parser.add_argument(
        "--aspect",
        default="16:9",
        choices=["16:9", "9:16"],
        help="Output aspect ratio (default: 16:9 YouTube)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="Transition clip length in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--fade",
        default="both",
        choices=["in", "out", "both", "none"],
        help="Fade style for transition clip (default: both)",
    )
    args = parser.parse_args()

    ensure_image_gen_output(PROJECT_ROOT)
    _ensure_image_dependencies()

    log("=" * 60)
    log(f"IMAGE GENERATION — {args.mode.upper()}")
    log("=" * 60)
    log("")

    if args.mode == "thumbnail-clips":
        if not args.clips_json:
            log("Error: --clips-json is required for thumbnail-clips mode.")
            sys.exit(1)
        path = Path(args.clips_json).resolve()
        if not path.exists():
            log(f"Error: File not found: {path}")
            sys.exit(1)
        _run_thumbnail_clips(path, args.prompt, args.aspect)

    elif args.mode == "thumbnail-custom":
        if not args.prompt:
            log("Error: --prompt is required for thumbnail-custom mode.")
            sys.exit(1)
        _run_thumbnail_custom(args.prompt, args.title, args.aspect)

    elif args.mode == "transition":
        if not args.prompt:
            log("Error: --prompt is required for transition mode.")
            sys.exit(1)
        _run_transition(args.prompt, args.duration, args.fade)


def _dims(aspect: str) -> tuple[int, int]:
    return (1280, 720) if aspect == "16:9" else (1080, 1920)


def _run_thumbnail_clips(clips_path: Path, extra_prompt: str, aspect: str) -> None:
    from image_gen.thumbnail_generator import generate_thumbnail

    with open(clips_path) as f:
        data = json.load(f)

    clips = data.get("clips", [])
    if not clips:
        log("No clips found in JSON — aborting.")
        sys.exit(1)

    w, h = _dims(aspect)
    log(f"Generating {len(clips)} thumbnail(s) at {w}×{h}...")
    log("")

    for i, clip in enumerate(clips, 1):
        title = clip.get("title", f"Clip {i:02d}")
        prompt = f"{title}. {extra_prompt}".strip(". ")
        log(f"[{i}/{len(clips)}] {title}")
        stem = f"thumb_clip_{i:02d}_{title[:30].strip().replace(' ', '_')}"
        out = str(PROJECT_ROOT / "image_gen" / "output" / f"{stem}.jpg")
        generate_thumbnail(prompt=prompt, title_text=title, output_path=out, width=w, height=h)
        log("")

    log("=" * 60)
    log(f"Done — {len(clips)} thumbnail(s) saved to image_gen/output/")


def _run_thumbnail_custom(prompt: str, title: str, aspect: str) -> None:
    from image_gen.thumbnail_generator import generate_thumbnail

    w, h = _dims(aspect)
    log(f"Generating thumbnail at {w}×{h}...")
    log("")
    generate_thumbnail(prompt=prompt, title_text=title, width=w, height=h)
    log("")
    log("=" * 60)
    log("Done — thumbnail saved to image_gen/output/")


def _run_transition(prompt: str, duration: float, fade: str) -> None:
    from image_gen.transition_generator import generate_transition

    log(f"Generating {duration}s transition clip (fade: {fade})...")
    log("")
    generate_transition(prompt=prompt, duration=duration, fade=fade)
    log("")
    log("=" * 60)
    log("Done — transition clip saved to image_gen/output/")


if __name__ == "__main__":
    main()
