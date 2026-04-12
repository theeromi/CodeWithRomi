"""Transcribe video with Whisper; save segment transcript to JSON."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _prepend_cuda_toolkit_bin_windows() -> None:
    """So cublas64_12.dll etc. resolve when using GPU (CTranslate2) on Windows."""
    if os.name != "nt":
        return
    extra: list[str] = []
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        b = Path(cuda_path) / "bin"
        if b.is_dir():
            extra.append(str(b))
    base = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
    if base.is_dir():
        for b in sorted(base.glob("v12.*/bin"), reverse=True):
            extra.append(str(b))
    for b in extra:
        if b not in os.environ.get("PATH", ""):
            os.environ["PATH"] = b + os.pathsep + os.environ.get("PATH", "")


_prepend_cuda_toolkit_bin_windows()

# Find CUDA 12 libs (e.g. Ollama’s) so faster_whisper can use the GPU
for _cuda in ("/usr/local/lib/ollama/cuda_v12", "/usr/local/lib/ollama/cuda_v13"):
    if os.path.exists(_cuda):
        os.environ["LD_LIBRARY_PATH"] = _cuda + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        break

from faster_whisper import WhisperModel

MODEL_SIZE = os.getenv("WHISPER_MODEL", "large-v3")
DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8_float16")
LANGUAGE = None  # or "en" for English-only

_model = None
_runtime_device = DEVICE
_runtime_compute = COMPUTE_TYPE

def _get_model():
    global _model, _runtime_device, _runtime_compute
    if _model is None:
        _runtime_device = DEVICE
        _runtime_compute = COMPUTE_TYPE
        try:
            _model = WhisperModel(MODEL_SIZE, device=_runtime_device, compute_type=_runtime_compute)
        except Exception as e:
            if _runtime_device == "cuda":
                print("CUDA failed, falling back to CPU:", e, flush=True)
                _runtime_device = "cpu"
                _runtime_compute = "int8"
                _model = WhisperModel(MODEL_SIZE, device=_runtime_device, compute_type=_runtime_compute)
            else:
                raise
    return _model


def _reset_whisper_to_cpu() -> None:
    global _model, _runtime_device, _runtime_compute
    _model = None
    _runtime_device = "cpu"
    _runtime_compute = "int8"


def transcribe_and_save(video_path: str, output_dir: str | Path | None = None) -> str:
    """
    Transcribe video and save transcript JSON. Returns path to the saved file.
    Logs progress to stdout (flush so you see status when run from pipeline).
    """
    video_path = str(Path(video_path).resolve())
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    out_dir = Path(output_dir) if output_dir else Path.cwd()
    out_dir = out_dir.resolve()
    video_name = Path(video_path).stem.strip() or "video"
    output_file = out_dir / f"{video_name}_transcript.json"

    model = _get_model()
    print(f"Transcribing: {video_path}", flush=True)
    print(f"Device: {_runtime_device} | Model: {MODEL_SIZE} | Compute: {_runtime_compute}\n", flush=True)

    def _do_transcribe():
        return model.transcribe(
            video_path,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            language=LANGUAGE,
            log_progress=True,
        )

    try:
        segments_iter, info = _do_transcribe()
    except RuntimeError as e:
        err = str(e).lower()
        if _runtime_device == "cuda" and (
            "cublas" in err or "cudnn" in err or "dll" in err or "cuda" in err
        ):
            print(
                "\nGPU transcription failed (missing CUDA DLLs or driver mismatch). "
                "Retrying on CPU — slower but works. For GPU, install CUDA 12 Toolkit "
                "or set WHISPER_DEVICE=cpu.\n",
                flush=True,
            )
            _reset_whisper_to_cpu()
            model = _get_model()
            print(f"Device: {_runtime_device} | Model: {MODEL_SIZE} | Compute: {_runtime_compute}\n", flush=True)
            segments_iter, info = _do_transcribe()
        else:
            raise

    # Materialize the generator — log_progress consumes it during iteration,
    # so we must collect all segments in one pass.
    segments = list(segments_iter)

    print(f"\nDetected language: {info.language} (probability: {info.language_probability:.2f})", flush=True)
    print(f"Segments found: {len(segments)}\n", flush=True)

    transcript_data = {
        "video": video_path,
        "language": info.language,
        "segments": [],
    }

    print("--- Transcript ---\n", flush=True)
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}", flush=True)
        segment_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": [],
        }
        if segment.words:
            for word in segment.words:
                segment_data["words"].append({
                    "start": word.start,
                    "end": word.end,
                    "word": word.word,
                })
        transcript_data["segments"].append(segment_data)

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(transcript_data, f, indent=2)

    print(f"\n✓ Transcription complete!", flush=True)
    print(f"✓ Saved to: {output_file}", flush=True)
    return str(output_file)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_transcription.py <video_file>")
        sys.exit(1)
    transcribe_and_save(sys.argv[1])
