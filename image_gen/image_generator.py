"""
FLUX.1-schnell image generator — 8-bit quantized via bitsandbytes.
Loaded once per process, stays in VRAM until the process exits.
~11.5 GB VRAM load, ~17 GB peak — fits on RTX 3090 (24 GB).
Downloads ~24 GB on first run, cached in ~/.cache/huggingface/hub/.
Generates 1024×1024 images in 4 steps (~3.5 min on 3090).
"""
from __future__ import annotations

import os
from PIL import Image

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import warnings
warnings.filterwarnings("ignore", message=".*upcast_vae.*")
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*torch_dtype.*deprecated.*")

_pipeline = None   # module-level singleton


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    print("🎨 Loading FLUX.1-schnell (8-bit quantized)...", flush=True)
    print("   First run downloads ~24 GB — subsequent runs use cache.", flush=True)

    import torch
    from diffusers import FluxPipeline
    from diffusers import BitsAndBytesConfig as DiffusersBnBConfig
    from transformers import BitsAndBytesConfig as TransformersBnBConfig
    from diffusers.quantizers import PipelineQuantizationConfig

    pipeline_quant_config = PipelineQuantizationConfig(
        quant_mapping={
            "transformer": DiffusersBnBConfig(load_in_8bit=True),
            "text_encoder_2": TransformersBnBConfig(load_in_8bit=True),
        }
    )

    _pipeline = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        quantization_config=pipeline_quant_config,
        torch_dtype=torch.bfloat16,
        device_map="balanced",
    )

    free_gb = torch.cuda.mem_get_info()[0] / 1024**3
    alloc_gb = torch.cuda.memory_allocated() / 1024**3
    print(f"   Model loaded — {alloc_gb:.1f} GB allocated, {free_gb:.1f} GB free.", flush=True)
    return _pipeline


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    seed: int | None = None,
) -> Image.Image:
    """Generate an image from a text prompt. Returns a PIL Image.

    FLUX.1-schnell at 4 steps with guidance_scale=0.0 (distilled model).
    On a 3090 (24 GB) with 8-bit quantization this takes ~3.5 minutes at 1024×1024.
    """
    import torch

    pipe = _load_pipeline()
    generator = (
        torch.Generator("cuda").manual_seed(seed) if seed is not None else None
    )

    result = pipe(
        prompt=prompt,
        num_inference_steps=steps,
        guidance_scale=0.0,
        width=width,
        height=height,
        generator=generator,
    )
    return result.images[0]


def offload_pipeline() -> None:
    """Free reserved-but-unused CUDA cache so NVENC can initialise."""
    if _pipeline is None:
        return
    import torch
    torch.cuda.empty_cache()
    print("   VRAM cache flushed.", flush=True)
