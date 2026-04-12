"""Ensure output directories exist (gitignored paths are missing on fresh clone / Windows)."""
from __future__ import annotations

from pathlib import Path


def ensure_pipeline_output_dirs(output_base: Path | str) -> Path:
    """Create output folder and generated_clips/. Safe to call repeatedly."""
    base = Path(output_base).resolve()
    base.mkdir(parents=True, exist_ok=True)
    (base / "generated_clips").mkdir(parents=True, exist_ok=True)
    return base


def ensure_image_gen_output(project_root: Path | str) -> Path:
    """Create image_gen/output/ for thumbnails and transition clips."""
    root = Path(project_root).resolve()
    out = root / "image_gen" / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out
