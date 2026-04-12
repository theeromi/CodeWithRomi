"""
Transition clip generator — AI background + Ken Burns zoom + fade → short MP4.
Output: MP4 saved to image_gen/output/.
Uses MoviePy (already in project venv) and the project's _get_encoder() for NVENC.
"""
from __future__ import annotations

import os
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from PIL import Image as PILImage

# Add project root to path so we can import clip_generator
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def generate_transition(
    prompt: str,
    duration: float = 2.0,
    fps: int = 30,
    fade: str = "both",       # "in", "out", "both", "none"
    width: int = 1080,
    height: int = 1920,
    output_path: str | None = None,
) -> str:
    """Generate an animated transition clip from a text prompt.

    A single AI frame is animated with a Ken Burns zoom, then exported
    as an MP4 using the project's GPU encoder if available.
    Returns path to saved MP4.
    """
    from image_gen.image_generator import generate_image
    from moviepy import VideoClip, vfx
    from clip_generator import _get_encoder

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        stem = prompt[:30].strip().replace(" ", "_").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(OUTPUT_DIR / f"transition_{stem}_{ts}.mp4")

    # ── Step 1: Generate background frame ──────────────────────────────────
    enriched = (
        f"Abstract cinematic background: {prompt}. "
        "Dramatic atmosphere, dark rich colors, no text, no words, no people, "
        "photorealistic, 8k detail"
    )
    print("   Generating background at 1024×1024...", flush=True)
    pil_img = generate_image(enriched, width=1024, height=1024)
    # Upscale to output size — Ken Burns will crop slightly, so go slightly bigger
    padded_w = int(width * 1.12)
    padded_h = int(height * 1.12)
    pil_img = pil_img.resize((padded_w, padded_h), PILImage.LANCZOS)
    base_frame = np.array(pil_img)

    # ── Step 2: Build VideoClip with Ken Burns (slow zoom out) ─────────────
    # Start at 108% crop → end at 100% crop (natural zoom-out motion)
    def make_frame(t: float) -> np.ndarray:
        progress = t / duration
        # Zoom factor: 1.08 at t=0, 1.0 at t=end
        scale = 1.08 - 0.08 * progress
        crop_w = int(width * scale)
        crop_h = int(height * scale)

        # Crop centre of padded_frame to crop_w × crop_h
        x = (padded_w - crop_w) // 2
        y = (padded_h - crop_h) // 2
        cropped = base_frame[y : y + crop_h, x : x + crop_w]

        # Downscale back to output size
        out = np.array(
            PILImage.fromarray(cropped).resize((width, height), PILImage.BILINEAR)
        )
        return out

    clip = VideoClip(make_frame, duration=duration)

    # ── Step 3: Fades ──────────────────────────────────────────────────────
    fade_dur = min(0.4, duration * 0.2)
    effects = []
    if fade in ("in", "both"):
        effects.append(vfx.FadeIn(fade_dur))
    if fade in ("out", "both"):
        effects.append(vfx.FadeOut(fade_dur))
    if effects:
        clip = clip.with_effects(effects)

    # ── Step 4: Export ─────────────────────────────────────────────────────
    # Flush SDXL cache so NVENC has clean headroom (3090 has plenty, but good practice).
    from image_gen.image_generator import offload_pipeline
    offload_pipeline()
    threads = min(8, (os.cpu_count() or 4))
    enc = _get_encoder(threads)
    print(f"💾 Exporting: {output_path}", flush=True)
    clip.write_videofile(
        output_path,
        fps=fps,
        audio=False,
        **enc,
        logger=None,
    )
    print(f"✅ Saved: {output_path}", flush=True)
    return output_path
