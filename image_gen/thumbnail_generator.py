"""
Thumbnail generator — AI background + title text overlay.
Output: JPEG saved to image_gen/output/.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _enrich_prompt(prompt: str) -> str:
    """Add quality/style modifiers for professional YouTube thumbnail backgrounds."""
    return (
        f"Professional YouTube thumbnail background: {prompt}. "
        "Dark moody gradient, subtle neon accent lighting, "
        "single focused tech scene, cinematic depth of field, "
        "no text, no words, no letters, no people, no collage, "
        "photorealistic, 8k detail"
    )


def generate_thumbnail(
    prompt: str,
    title_text: str,
    output_path: str | None = None,
    width: int = 1280,
    height: int = 720,
) -> str:
    """Generate a thumbnail: AI background + dark gradient + title text.

    prompt      — text description of the background scene
    title_text  — text drawn in the lower third of the image
    width/height — output dimensions (1280×720 for YouTube, 1080×1920 for Shorts)
    Returns path to saved JPEG.
    """
    from image_gen.image_generator import generate_image

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        stem = title_text[:30].strip().replace(" ", "_").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(OUTPUT_DIR / f"thumb_{stem}_{ts}.jpg")

    # ── Step 1: Generate background ────────────────────────────────────────
    # Generate at 1024×1024 for sharper detail (3090 24 GB handles this easily).
    print("   Generating background at 1024×1024...", flush=True)
    img = generate_image(_enrich_prompt(prompt), width=1024, height=1024)

    # ── Step 2: Upscale to output dimensions ───────────────────────────────
    img = img.resize((width, height), Image.LANCZOS)

    # ── Step 3: Dark gradient overlay (bottom 45%) ─────────────────────────
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    grad_top = int(height * 0.52)
    for y in range(grad_top, height):
        alpha = int(195 * (y - grad_top) / (height - grad_top))
        draw_ov.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")

    # ── Step 4: Title text in lower third ──────────────────────────────────
    if title_text.strip():
        draw = ImageDraw.Draw(img)
        font_size = max(36, int(height * 0.085))
        font = _load_font(font_size)

        # Word-wrap to fit width
        words = title_text.split()
        lines: list[str] = []
        cur: list[str] = []
        for word in words:
            test = " ".join(cur + [word])
            if draw.textlength(test, font=font) <= width - 80:
                cur.append(word)
            else:
                if cur:
                    lines.append(" ".join(cur))
                cur = [word]
        if cur:
            lines.append(" ".join(cur))

        line_h = font_size + 10
        total_h = len(lines) * line_h
        y_start = height - total_h - int(height * 0.06)

        for i, line in enumerate(lines):
            y = y_start + i * line_h
            tw = draw.textlength(line, font=font)
            x = (width - tw) / 2
            # Shadow
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0))
            # White text
            draw.text((x, y), line, font=font, fill=(255, 255, 255))

    # ── Step 5: Save ───────────────────────────────────────────────────────
    img.save(output_path, "JPEG", quality=95)
    print(f"✅ Saved: {output_path}", flush=True)
    return output_path
