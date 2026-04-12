import json
import sys
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, VideoClip, ImageClip, CompositeVideoClip, ColorClip

# MoviePy defaults to its bundled imageio-ffmpeg which has no GPU encoders.
# Redirect it to the system ffmpeg (/usr/bin/ffmpeg) which has h264_nvenc.
import moviepy.config as _mp_config
import moviepy.video.io.ffmpeg_writer as _mp_writer
import moviepy.video.io.ffmpeg_reader as _mp_reader
_SYSTEM_FFMPEG = "/usr/bin/ffmpeg"
if os.path.exists(_SYSTEM_FFMPEG):
    _mp_config.FFMPEG_BINARY = _SYSTEM_FFMPEG
    _mp_writer.FFMPEG_BINARY = _SYSTEM_FFMPEG
    _mp_reader.FFMPEG_BINARY = _SYSTEM_FFMPEG

# TikTok / YouTube Shorts: 1080x1920 (9:16), full frame visible (letterbox/pillarbox as needed)
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
MIN_CLIP_S = 30
MAX_CLIP_S = 180   # up to 3 min (Shorts limit)

# Caption settings
CAPTION_FONT_SIZE = 68         # px — readable on phone screens
CAPTION_WORDS_PER_CHUNK = 4   # words shown at once (CapCut/OpusClip style)
CAPTION_Y_RATIO = 0.72        # vertical position: 72% down the frame
CAPTION_STROKE = 3             # black outline thickness
CAPTION_STRIP_H = 220          # fixed height for caption strip (fits 2 lines + padding)

# Encoder: "auto" = GPU (NVENC) if available, else CPU (libx264)
#          "gpu"  = force NVENC (fails if not available)
#          "cpu"  = force libx264
ENCODE_MODE = os.getenv("CLIP_ENCODER", "auto").strip().lower()

_nvenc_checked: bool | None = None   # cached after first call


def _nvenc_available() -> bool:
    """Check once whether ffmpeg was compiled with h264_nvenc."""
    global _nvenc_checked
    if _nvenc_checked is not None:
        return _nvenc_checked
    ffmpeg_bin = _SYSTEM_FFMPEG if os.path.exists(_SYSTEM_FFMPEG) else "ffmpeg"
    try:
        out = subprocess.run(
            [ffmpeg_bin, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        _nvenc_checked = "h264_nvenc" in out
    except Exception:
        _nvenc_checked = False
    return _nvenc_checked


def _get_encoder(threads: int) -> dict:
    """Return write_videofile kwargs for the best available encoder.

    Sequential pipeline means Whisper is always finished and freed before
    this is called — NVENC only needs ~300 MB during encode so there is no
    VRAM overlap between stages.
    """
    use_gpu = (ENCODE_MODE == "gpu") or (ENCODE_MODE == "auto" and _nvenc_available())

    if use_gpu:
        print("   Encoder: GPU (h264_nvenc) — NVENC")
        return dict(
            codec="h264_nvenc",
            preset="p7",           # p1=fastest … p7=best quality; 3090 handles p7 fast
            threads=threads,
            ffmpeg_params=[
                "-rc", "vbr",      # variable bitrate — best quality/size ratio
                "-cq", "18",       # constant quality (equivalent to CRF 18)
                "-b:v", "0",       # required with -cq
                "-maxrate", "20M", # increased cap for 3090 — better motion quality
                "-bufsize", "40M",
                "-profile:v", "high",
                "-b:a", "192k",
            ],
        )
    else:
        print("   Encoder: CPU (libx264)")
        return dict(
            codec="libx264",
            preset="medium",
            threads=threads,
            ffmpeg_params=[
                "-crf", "18",
                "-profile:v", "high",
                "-level", "4.0",
                "-b:a", "192k",
            ],
        )

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
]

_FONT_WARNING_SHOWN = False


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    global _FONT_WARNING_SHOWN
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    if not _FONT_WARNING_SHOWN:
        print("  ⚠ No TTF font found; captions will use PIL default")
        _FONT_WARNING_SHOWN = True
    return ImageFont.load_default()


def _render_caption_highlighted(word_texts: list[str], highlight_idx: int, video_w: int) -> np.ndarray:
    """Render a word chunk with the current word in yellow, others white.
    Returns RGBA numpy array of fixed height CAPTION_STRIP_H.
    """
    font = _load_font(CAPTION_FONT_SIZE)
    stroke = CAPTION_STROKE
    padding = 18
    max_w = video_w - 120

    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    space_w = dummy.textlength(" ", font=font)

    # Word-wrap, preserving original indices for colour lookup
    lines: list[list[tuple[str, int]]] = []
    cur: list[tuple[str, int]] = []
    for i, word in enumerate(word_texts):
        test = " ".join(w for w, _ in cur + [(word, i)])
        if dummy.textlength(test, font=font) <= max_w or not cur:
            cur.append((word, i))
        else:
            lines.append(cur)
            cur = [(word, i)]
    if cur:
        lines.append(cur)

    line_h = CAPTION_FONT_SIZE + 8
    content_h = len(lines) * line_h + padding * 2

    # Fixed-height canvas — content pinned to bottom of strip
    img = Image.new("RGBA", (video_w, CAPTION_STRIP_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y_start = CAPTION_STRIP_H - content_h

    for li, line_words in enumerate(lines):
        y = y_start + padding + li * line_h
        line_text = " ".join(w for w, _ in line_words)
        line_w = draw.textlength(line_text, font=font)
        x = (video_w - line_w) / 2

        for word, orig_idx in line_words:
            fg = (255, 220, 0, 255) if orig_idx == highlight_idx else (255, 255, 255, 255)
            w_w = draw.textlength(word, font=font)
            # Black stroke
            for dx in range(-stroke, stroke + 1):
                for dy in range(-stroke, stroke + 1):
                    if dx or dy:
                        draw.text((x + dx, y + dy), word, font=font, fill=(0, 0, 0, 255))
            # Coloured word
            draw.text((x, y), word, font=font, fill=fg)
            x += w_w + space_w

    return np.array(img)


def _build_caption_clip(words: list[dict], video_w: int, video_h: int):
    """Return a single VideoClip with per-word yellow highlighting.
    Uses a pre-rendered cache so make_frame is O(1) per call — no slowdown.
    Returns None if words is empty.
    """
    if not words:
        return None

    chunk_size = CAPTION_WORDS_PER_CHUNK
    y_pos = min(int(video_h * CAPTION_Y_RATIO), video_h - CAPTION_STRIP_H - 20)
    duration = words[-1]["end"]

    # Build chunks
    chunks = [words[i : i + chunk_size] for i in range(0, len(words), chunk_size)]

    # Pre-render every (chunk_idx, word_idx) state — done once before export starts
    cache: dict[tuple[int, int], np.ndarray] = {}
    for ci, ch in enumerate(chunks):
        texts = [w["word"].strip() for w in ch]
        for hi in range(len(ch)):
            cache[(ci, hi)] = _render_caption_highlighted(texts, hi, video_w)

    _blank_rgb  = np.zeros((CAPTION_STRIP_H, video_w, 3), dtype=np.uint8)
    _blank_mask = np.zeros((CAPTION_STRIP_H, video_w), dtype=float)

    def _active(t: float) -> tuple[int, int]:
        for ci, ch in enumerate(chunks):
            if ch[0]["start"] <= t < ch[-1]["end"] + 0.05:
                for hi, wd in enumerate(ch):
                    if t < wd["end"] + 0.05:
                        return ci, hi
                return ci, len(ch) - 1
        return -1, -1

    def make_rgb(t: float) -> np.ndarray:
        ci, hi = _active(t)
        return _blank_rgb if ci < 0 else cache[(ci, hi)][:, :, :3]

    def make_alpha(t: float) -> np.ndarray:
        ci, hi = _active(t)
        return _blank_mask if ci < 0 else cache[(ci, hi)][:, :, 3] / 255.0

    return (
        VideoClip(make_rgb, duration=duration)
        .with_mask(VideoClip(make_alpha, is_mask=True, duration=duration))
        .with_position(("center", y_pos))
    )


def snap_clip_to_transcript(segments, start, end, video_duration):
    """
    Snap clip [start, end] to transcript segment boundaries so we never cut mid-sentence.
    Returns (snap_start, snap_end) clamped to video duration.
    """
    if not segments:
        return max(0.0, start), min(float(video_duration), end)

    # Segments that overlap [start, end]
    overlapping = [s for s in segments if s["end"] > start and s["start"] < end]
    if not overlapping:
        # No overlap: use nearest segment or original range
        return max(0.0, start), min(float(video_duration), end)

    snap_start = min(s["start"] for s in overlapping)
    snap_end = max(s["end"] for s in overlapping)
    snap_start = max(0.0, snap_start)
    snap_end = min(float(video_duration), snap_end)
    if snap_end <= snap_start:
        return max(0.0, start), min(float(video_duration), end)
    return snap_start, snap_end


def _save_clip_metadata(video_path: Path, clip: dict, duration: float, words: list[dict]):
    """Save a YouTube/TikTok-ready metadata JSON alongside the clip MP4.

    Contains title, description, hashtags, and a transcript snippet — everything
    you need to paste into the upload form.
    """
    title = clip.get("title", "Untitled Clip")
    reason = clip.get("reason", "")

    transcript_text = " ".join(w["word"].strip() for w in words).strip() if words else ""
    preview = (transcript_text[:300] + "...") if len(transcript_text) > 300 else transcript_text

    description_lines = []
    if reason:
        description_lines.append(reason)
    if preview:
        description_lines.append("")
        description_lines.append(preview)
    description = "\n".join(description_lines)

    hashtags = ["#shorts", "#tutorial", "#tech", "#howto", "#tips"]

    meta = {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "duration_s": round(duration, 1),
        "source_range": f"{clip['start']:.1f}s – {clip['end']:.1f}s",
    }

    meta_path = video_path.with_suffix(".meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"📋 Metadata saved: {meta_path.name}")


def generate_clips(clips_json_file, transcript_json_file):
    """Generate clips for TikTok/YouTube Shorts: full frame visible, no mid-sentence cuts."""

    with open(clips_json_file, "r") as f:
        clips_data = json.load(f)
    with open(transcript_json_file, "r") as f:
        transcript_data = json.load(f)

    source_video = clips_data["source_video"]
    clips = clips_data["clips"]
    segments = transcript_data.get("segments", [])

    print(f"📹 Source video: {source_video}")
    print(f"🎬 Generating {len(clips)} clips (9:16, TikTok/Shorts compatible)...\n")

    output_dir = Path("generated_clips")
    output_dir.mkdir(parents=True, exist_ok=True)

    video = VideoFileClip(source_video)
    video_duration = video.duration

    for i, clip in enumerate(clips, 1):
        print(f"{'='*70}")
        print(f"🎥 CLIP {i}/{len(clips)}: {clip.get('title', 'Untitled')}")
        print(f"{'='*70}")

        start_time = clip["start"]
        end_time = clip["end"]

        # Snap to transcript boundaries so we never cut mid-sentence
        start_time, end_time = snap_clip_to_transcript(
            segments, start_time, end_time, video_duration
        )
        duration = end_time - start_time

        # Skip invalid clips (AI sometimes returns end before start)
        if duration <= 0:
            print(f"⚠️  Skipping: invalid range (start {start_time:.1f}s > end {end_time:.1f}s). Check analyzer output.")
            print()
            continue

        if duration < MIN_CLIP_S:
            print(f"⚠️  Snapped duration {duration:.1f}s is under {MIN_CLIP_S}s; keeping anyway.")
        elif duration > 60:
            print(f"📐 Duration {duration:.1f}s (OK for Shorts, max 3 min).")
        print(f"⏱️  Duration: {duration:.1f}s ({start_time:.1f}s → {end_time:.1f}s) [aligned to transcript]")

        print("✂️  Extracting segment...")
        clip_video = video.subclipped(start_time, end_time)

        # Scale to fit inside 1080x1920 so full frame is visible (letterbox or pillarbox as needed)
        print("📱 Fitting to 9:16 (1080×1920) – full frame visible, TikTok/Shorts compatible...")
        w, h = clip_video.w, clip_video.h
        scale = min(SHORTS_WIDTH / w, SHORTS_HEIGHT / h)
        new_w = int(round(w * scale))
        clip_video = clip_video.resized(width=new_w)

        background = ColorClip(
            size=(SHORTS_WIDTH, SHORTS_HEIGHT),
            color=(0, 0, 0),
            duration=clip_video.duration,
        )
        x_off = (SHORTS_WIDTH - clip_video.w) / 2
        y_off = (SHORTS_HEIGHT - clip_video.h) / 2
        clip_video = clip_video.with_position((x_off, y_off))
        clip_video = CompositeVideoClip([background, clip_video])

        # Add per-word highlighted captions (single VideoClip, pre-rendered cache)
        words = get_words_for_timerange(transcript_data, start_time, end_time)
        if words:
            print(f"📝 Building captions ({len(words)} words)...")
            try:
                cap_clip = _build_caption_clip(words, SHORTS_WIDTH, SHORTS_HEIGHT)
                if cap_clip:
                    clip_video = CompositeVideoClip([clip_video, cap_clip])
                    print("   Captions ready.")
            except Exception as e:
                print(f"   ⚠ Captions skipped: {e}")
        else:
            print("   ℹ No word timestamps in transcript — captions skipped.")

        output_filename = output_dir / f"clip_{i:02d}_{sanitize_filename(clip.get('title', 'clip'))}.mp4"
        print(f"💾 Exporting: {output_filename}")

        threads = min(8, (os.cpu_count() or 4))
        clip_video.write_videofile(
            str(output_filename),
            audio_codec="aac",
            fps=30,
            **_get_encoder(threads),
        )

        clip_video.close()

        _save_clip_metadata(output_filename, clip, duration, words)
        print(f"✅ Clip {i} complete!\n")
    
    video.close()
    print(f"\n🎉 All {len(clips)} clips generated successfully!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print(f"📱 Output: 1080×1920, 9:16, H.264/AAC – ready for TikTok & YouTube Shorts.")

def get_words_for_timerange(transcript_data: dict, start_time: float, end_time: float) -> list[dict]:
    """Extract words from any segment that overlaps [start_time, end_time], times adjusted to clip timeline."""
    words = []
    for segment in transcript_data["segments"]:
        # Include segment if it overlaps the clip range (not just fully contained)
        if segment["end"] > start_time and segment["start"] < end_time:
            for word in segment.get("words", []):
                w_start = word["start"] - start_time
                w_end = word["end"] - start_time
                # Only include words that actually fall inside the clip
                if w_end > 0 and w_start < (end_time - start_time):
                    words.append({
                        "word": word["word"],
                        "start": max(0.0, w_start),
                        "end": min(end_time - start_time, w_end),
                    })
    return words

def sanitize_filename(title):
    """Clean title for use in filename"""
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title).strip()[:50]

def process_single_video(
    video_path: str,
    transcript_file: str,
    output_dir: str,
    mode: str = "vertical-captions",
) -> str:
    """Process a single already-shorts-length video.

    mode='vertical-captions' — resize to 1080×1920 + per-word highlighted captions
    mode='captions-only'     — keep original dimensions, just add captions

    Returns the path to the exported file.
    """
    with open(transcript_file) as f:
        transcript_data = json.load(f)

    print(f"🎬 Opening video: {video_path}")
    video = VideoFileClip(video_path)
    out_w = video.w
    out_h = video.h

    if mode == "vertical-captions":
        print("📱 Converting to 9:16 (1080×1920) — full frame visible...")
        w, h = video.w, video.h
        scale = min(SHORTS_WIDTH / w, SHORTS_HEIGHT / h)
        new_w = int(round(w * scale))
        video = video.resized(width=new_w)
        background = ColorClip(
            size=(SHORTS_WIDTH, SHORTS_HEIGHT),
            color=(0, 0, 0),
            duration=video.duration,
        )
        x_off = (SHORTS_WIDTH - video.w) / 2
        y_off = (SHORTS_HEIGHT - video.h) / 2
        video = video.with_position((x_off, y_off))
        video = CompositeVideoClip([background, video])
        out_w, out_h = SHORTS_WIDTH, SHORTS_HEIGHT
    else:
        print(f"📐 Keeping original dimensions ({out_w}×{out_h}) — captions only...")

    words = get_words_for_timerange(transcript_data, 0.0, video.duration)
    if words:
        print(f"📝 Building captions ({len(words)} words)...")
        try:
            cap_clip = _build_caption_clip(words, out_w, out_h)
            if cap_clip:
                video = CompositeVideoClip([video, cap_clip])
                print("   Captions ready.")
        except Exception as e:
            print(f"   ⚠ Captions skipped: {e}")
    else:
        print("   ℹ No word timestamps in transcript — captions skipped.")

    suffix = "vertical" if mode == "vertical-captions" else "captioned"
    out_name = Path(video_path).stem + f"_{suffix}.mp4"
    out_path = Path(output_dir) / "generated_clips" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"💾 Exporting: {out_path}")
    out_fps = min(30, round(video.fps)) if video.fps else 30
    threads = min(8, (os.cpu_count() or 4))
    video.write_videofile(
        str(out_path),
        audio_codec="aac",
        fps=out_fps,
        **_get_encoder(threads),
    )
    video.close()
    print(f"✅ Done! Saved to: {out_path}")
    return str(out_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python clip_generator.py <clips_json> <transcript_json>")
        print("Example: python clip_generator.py 'Linux ssd_clips.json' 'Linux ssd_transcript.json'")
        sys.exit(1)
    
    clips_file = sys.argv[1]
    transcript_file = sys.argv[2]
    
    if not Path(clips_file).exists():
        print(f"Error: Clips file not found: {clips_file}")
        sys.exit(1)
    
    if not Path(transcript_file).exists():
        print(f"Error: Transcript file not found: {transcript_file}")
        sys.exit(1)
    
    generate_clips(clips_file, transcript_file)