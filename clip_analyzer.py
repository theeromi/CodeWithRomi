import json
import math
import os
import re
import sys
import subprocess
import threading
import time
from pathlib import Path

# Which Ollama model to use for clip selection. Change via env: CLIP_ANALYZER_MODEL=...
# llama3.1:8b follows complex multi-rule prompts better than mistral on 8GB VRAM
DEFAULT_CLIP_MODEL = os.environ.get("CLIP_ANALYZER_MODEL", "").strip() or None
DEFAULT_MODEL_CHAIN = os.environ.get(
    "CLIP_ANALYZER_MODEL_CHAIN",
    "qwen2.5:32b,qwen2.5:14b,llama3.1:8b",
)
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("CLIP_ANALYZER_TIMEOUT_SECONDS", "900"))

MIN_CLIP_SECONDS = float(os.environ.get("CLIP_MIN_SECONDS", "30"))
MAX_CLIP_SECONDS = float(os.environ.get("CLIP_MAX_SECONDS", "180"))
MIN_GAP_SECONDS = float(os.environ.get("CLIP_MIN_GAP_SECONDS", "12"))
QUALITY_RERANK_ENABLED = os.environ.get("CLIP_QUALITY_RERANK", "1").strip().lower() not in {"0", "false", "no"}

# Run analysis in smaller sequential windows to reduce context pressure / KV-cache usage.
SECTIONAL_ANALYSIS = os.environ.get("CLIP_SECTIONAL_ANALYSIS", "1").strip().lower() not in {"0", "false", "no"}
SECTION_SECONDS = float(os.environ.get("CLIP_SECTION_SECONDS", "360"))

HOOK_TERMS = (
    "here's how",
    "how to",
    "the mistake",
    "what happens",
    "this is how",
    "you can",
    "watch this",
    "if you",
    "why",
)
PAYOFF_TERMS = (
    "now",
    "so this means",
    "result",
    "works",
    "ready",
    "done",
    "success",
    "you can see",
    "that means",
)
OUTRO_TERMS = (
    "thanks for watching",
    "hit that like",
    "subscribe",
    "drop a comment",
    "check out my website",
    "see you in the next",
    "member list",
)


def analyze_transcript_for_clips(transcript_file, min_clips=5, model=None):
    """Use Ollama to analyze transcript and identify clip-worthy moments by segment range."""

    with open(transcript_file, 'r') as f:
        data = json.load(f)

    segments = data['segments']
    if not segments:
        print("⚠ Transcript has no segments; no clips generated.")
        return []

    requested_model = model or DEFAULT_CLIP_MODEL
    candidates: list[dict] = []

    print("🤖 Analyzing transcript with AI...")
    print(f"📊 Requested model: {requested_model or 'auto (fallback chain)'} | Target clips: {min_clips}")
    print(f"🧩 Sectional analysis: {'on' if SECTIONAL_ANALYSIS else 'off'} | section size: {int(SECTION_SECONDS)}s\n")

    indexed_segments = list(enumerate(segments))
    sections = (
        _split_segments_by_time(indexed_segments, SECTION_SECONDS)
        if SECTIONAL_ANALYSIS
        else [indexed_segments]
    )
    section_target = max(1, math.ceil(min_clips / max(1, len(sections))))

    for section_idx, section in enumerate(sections, start=1):
        sec_first = section[0][0]
        sec_last = section[-1][0]
        sec_start = section[0][1]["start"]
        sec_end = section[-1][1]["end"]

        print(
            f"--- Section {section_idx}/{len(sections)} | Segments {sec_first}-{sec_last} "
            f"({sec_start:.1f}s → {sec_end:.1f}s) ---"
        )

        prompt = _build_prompt(
            indexed_segments=section,
            target_clips=section_target,
            global_max_index=len(segments) - 1,
        )
        ai_response, used_model = _run_ollama_with_fallback(prompt, requested_model)

        print(f"✅ Section model used: {used_model}")

        section_clips = parse_ai_response_segment_index(ai_response, segments)
        if not section_clips:
            section_clips = parse_ai_response_timestamps(ai_response)

        if not section_clips:
            preview = ai_response.strip()[:500]
            print(f"   ⚠ AI returned no parseable clips. Raw response preview:\n{preview}", flush=True)

        print(f"📌 Section candidates: {len(section_clips)}")
        candidates.extend(section_clips)

    clips = _validate_clips(
        candidates,
        min_duration=MIN_CLIP_SECONDS,
        max_duration=MAX_CLIP_SECONDS,
        min_gap=MIN_GAP_SECONDS,
    )

    if not clips and candidates:
        relaxed_min = max(10, MIN_CLIP_SECONDS * 0.5)
        print(f"\n   ⚠ All {len(candidates)} candidates were dropped at {MIN_CLIP_SECONDS:.0f}s minimum.")
        print(f"   ↻ Retrying with relaxed minimum ({relaxed_min:.0f}s)...", flush=True)
        clips = _validate_clips(
            candidates,
            min_duration=relaxed_min,
            max_duration=MAX_CLIP_SECONDS,
            min_gap=MIN_GAP_SECONDS,
        )

    clips = _rerank_and_select(clips, segments, min_clips)

    # Save clips data
    output_file = transcript_file.replace('_transcript.json', '_clips.json')
    with open(output_file, 'w') as f:
        json.dump({
            'source_video': data['video'],
            'total_clips': len(clips),
            'clips': clips
        }, f, indent=2)
    
    print(f"\n✅ Found {len(clips)} clips")
    print(f"✅ Saved to: {output_file}")

    return clips


def _build_prompt(indexed_segments: list[tuple[int, dict]], target_clips: int, global_max_index: int) -> str:
    transcript_lines = []
    for i, seg in indexed_segments:
        transcript_lines.append(f"Segment {i}: [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
    transcript_text = "\n".join(transcript_lines)
    first_idx = indexed_segments[0][0]
    last_idx = indexed_segments[-1][0]
    section_dur = indexed_segments[-1][1]["end"] - indexed_segments[0][1]["start"]

    min_dur = max(15, min(30, int(section_dur * 0.25)))

    return f"""You are a viral short-form video editor for TikTok and YouTube Shorts. Select {target_clips} clips from this transcript section that work as standalone viral shorts.

TRANSCRIPT SECTION (segment index [start-end]: text):
{transcript_text}

This section is {section_dur:.0f} seconds long.

WHAT MAKES A CLIP WORK ON TIKTOK/SHORTS:
1. HOOK: First sentence grabs attention immediately — a surprising fact, bold statement, question, or "here's how I..." moment. Never starts mid-sentence or mid-explanation.
2. ONE PAYOFF: One complete tip, trick, result, or insight. Viewer leaves knowing something. Not more, not less.
3. COMPLETE: Ends at a clear conclusion — result shown, tip delivered, question answered. Never ends mid-explanation or with "...and next we'll cover".
4. SELF-CONTAINED: Makes 100% sense with zero context from the rest of the video.
5. SPREAD OUT: Choose clips from different parts of this section. Do not overlap clips.

DURATION: {min_dur} seconds minimum. 60-90 seconds ideal. 3 minutes maximum. Each clip MUST span enough segments to reach at least {min_dur} seconds.

OUTPUT — use this exact format, no markdown, no extra text:

CLIP 1
FirstSegment: 5
LastSegment: 12
Title: How I Automated My Entire Workflow
Why: Complete demo from setup to working result

CLIP 2
FirstSegment: 31
LastSegment: 40
Title: The One Mistake Everyone Makes
Why: Names the mistake and shows the fix

Repeat for all {target_clips} clips.
Valid segments for this section are {first_idx} to {last_idx} only.
Global segment range is 0 to {global_max_index}. No overlapping clips."""


def _split_segments_by_time(indexed_segments: list[tuple[int, dict]], section_seconds: float) -> list[list[tuple[int, dict]]]:
    if not indexed_segments:
        return []
    if section_seconds <= 0:
        return [indexed_segments]

    sections: list[list[tuple[int, dict]]] = []
    current: list[tuple[int, dict]] = []
    section_start = indexed_segments[0][1]["start"]

    for pair in indexed_segments:
        _, seg = pair
        if current and (seg["start"] - section_start) >= section_seconds:
            sections.append(current)
            current = []
            section_start = seg["start"]
        current.append(pair)

    if current:
        sections.append(current)
    return sections


def _model_candidates(requested_model: str | None = None) -> list[str]:
    ordered: list[str] = []
    if requested_model:
        ordered.append(requested_model)

    for name in DEFAULT_MODEL_CHAIN.split(","):
        model = name.strip()
        if model:
            ordered.append(model)

    if DEFAULT_CLIP_MODEL:
        ordered.append(DEFAULT_CLIP_MODEL)

    deduped: list[str] = []
    seen = set()
    for model in ordered:
        if model not in seen:
            deduped.append(model)
            seen.add(model)
    return deduped


def _run_ollama_with_progress(model: str, prompt: str, timeout: int) -> tuple[int, str, str]:
    """Run Ollama with a live progress spinner so the user sees it's working.

    Uses stderr=STDOUT so all Ollama output (response + spinner junk) lands
    in one stream.  ANSI escape codes are stripped later by the caller.
    """
    proc = subprocess.Popen(
        ["ollama", "run", model, "--nowordwrap"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    stdout_chunks: list[str] = []
    stop_spinner = threading.Event()

    def _read_stdout():
        for line in proc.stdout:
            stdout_chunks.append(line)
        proc.stdout.close()

    def _spinner():
        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        start = time.time()
        last_report = 0
        while not stop_spinner.is_set():
            elapsed = int(time.time() - start)
            mins, secs = divmod(elapsed, 60)
            tokens = len(stdout_chunks)
            status = f"   AI thinking... {mins}m {secs:02d}s"
            if tokens:
                status += f" | {tokens} output lines received"

            if is_tty:
                frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
                frame = frames[int(elapsed * 3) % len(frames)]
                print(f"\r   {frame} {status[3:]}    ", end="", flush=True)
            elif elapsed - last_report >= 10:
                print(status, flush=True)
                last_report = elapsed

            stop_spinner.wait(0.3)

        if is_tty:
            print("\r" + " " * 60 + "\r", end="", flush=True)
        else:
            elapsed = int(time.time() - start)
            mins, secs = divmod(elapsed, 60)
            print(f"   AI finished in {mins}m {secs:02d}s", flush=True)

    t_out = threading.Thread(target=_read_stdout, daemon=True)
    t_spin = threading.Thread(target=_spinner, daemon=True)

    t_out.start()
    t_spin.start()

    proc.stdin.write(prompt)
    proc.stdin.close()

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        stop_spinner.set()
        t_spin.join(timeout=2)
        return -1, "", f"timed out after {timeout}s"

    stop_spinner.set()
    t_out.join(timeout=5)
    t_spin.join(timeout=2)

    return proc.returncode, "".join(stdout_chunks), ""


_ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07?|\r')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


def _run_ollama_with_fallback(prompt: str, requested_model: str | None) -> tuple[str, str]:
    errors = []
    for model in _model_candidates(requested_model):
        print(f"   → Trying model: {model}", flush=True)

        returncode, stdout, stderr = _run_ollama_with_progress(
            model, prompt, OLLAMA_TIMEOUT_SECONDS
        )

        if returncode == -1:
            errors.append(f"{model}: timed out after {OLLAMA_TIMEOUT_SECONDS}s")
            print(f"   ⚠ Model timed out: {model} (>{OLLAMA_TIMEOUT_SECONDS}s)", flush=True)
            continue

        # Ollama `run` sends its spinner to stderr and may put the actual
        # response on stdout OR stderr depending on version/tty detection.
        # Strip ANSI escape codes and accept whichever stream has real text.
        clean_out = _strip_ansi(stdout).strip()
        clean_err = _strip_ansi(stderr).strip()

        response = clean_out or clean_err

        if returncode == 0 and response:
            return response, model

        err_preview = (clean_err or clean_out or "empty response").strip()
        errors.append(f"{model}: rc={returncode} — {err_preview[:240]}")
        print(f"   ⚠ Model failed: {model} — {err_preview[:160]}", flush=True)

    print("Ollama error: all fallback models failed")
    for line in errors:
        print("  -", line)
    sys.exit(1)


def _clip_quality_score(clip: dict) -> float:
    duration = clip["end"] - clip["start"]
    title = clip.get("title", "")
    reason = clip.get("reason", "")
    score = 0.0
    score -= abs(duration - 75.0) * 0.2
    if 45.0 <= duration <= 120.0:
        score += 8.0
    score += min(len(title), 64) / 16.0
    score += min(len(reason), 180) / 45.0
    score += clip.get("quality_score", 0.0)
    return score


def _segments_for_clip(clip: dict, segments: list[dict]) -> list[dict]:
    return [s for s in segments if s["end"] > clip["start"] and s["start"] < clip["end"]]


def _score_clip_text_quality(clip: dict, segments: list[dict], total_duration: float) -> float:
    rel = _segments_for_clip(clip, segments)
    if not rel:
        return -20.0

    full_text = " ".join((s.get("text") or "").strip() for s in rel).lower()
    first_text = " ".join((s.get("text") or "").strip() for s in rel[:2]).lower()
    last_text = " ".join((s.get("text") or "").strip() for s in rel[-2:]).lower()

    score = 0.0
    if any(term in first_text for term in HOOK_TERMS) or "?" in first_text:
        score += 6.0
    else:
        score -= 4.0

    if any(term in last_text for term in PAYOFF_TERMS):
        score += 4.0
    else:
        score -= 2.0

    if any(term in full_text for term in OUTRO_TERMS):
        score -= 14.0

    if total_duration > 0 and clip["start"] > total_duration * 0.88 and any(term in full_text for term in OUTRO_TERMS):
        score -= 8.0

    if len(full_text.split()) < 35:
        score -= 3.0

    return score


def _rerank_and_select(clips: list[dict], segments: list[dict], target_count: int) -> list[dict]:
    if not clips:
        return []

    if not QUALITY_RERANK_ENABLED:
        return _select_best_diverse_clips(clips, target_count)

    total_duration = segments[-1]["end"] if segments else 0.0
    enriched = []
    for clip in clips:
        clip_copy = dict(clip)
        clip_copy["quality_score"] = _score_clip_text_quality(clip_copy, segments, total_duration)
        enriched.append(clip_copy)

    ranked = sorted(enriched, key=_clip_quality_score, reverse=True)
    pool_size = max(target_count, min(len(ranked), target_count * 3))
    pool = sorted(ranked[:pool_size], key=lambda c: c["start"])

    print(f"\n⭐ Quality reranker enabled: selecting from top {pool_size} candidates.")
    chosen = _select_best_diverse_clips(pool, target_count)
    return sorted(chosen, key=lambda c: c["start"])


def _select_best_diverse_clips(clips: list[dict], target_count: int) -> list[dict]:
    if target_count <= 0 or len(clips) <= target_count:
        return sorted(clips, key=lambda c: c["start"])

    clips_by_time = sorted(clips, key=lambda c: c["start"])
    n = len(clips_by_time)
    chosen: list[dict] = []
    used_idx = set()
    window = 2

    if target_count == 1:
        best = max(clips_by_time, key=_clip_quality_score)
        return [best]

    ideal_positions = [round(i * (n - 1) / (target_count - 1)) for i in range(target_count)]
    for pos in ideal_positions:
        lo = max(0, pos - window)
        hi = min(n - 1, pos + window)
        pool = [(i, clips_by_time[i]) for i in range(lo, hi + 1) if i not in used_idx]
        if not pool:
            continue
        best_idx, best_clip = max(pool, key=lambda p: _clip_quality_score(p[1]))
        chosen.append(best_clip)
        used_idx.add(best_idx)

    if len(chosen) < target_count:
        leftovers = [(i, c) for i, c in enumerate(clips_by_time) if i not in used_idx]
        leftovers.sort(key=lambda p: _clip_quality_score(p[1]), reverse=True)
        for i, clip in leftovers:
            chosen.append(clip)
            used_idx.add(i)
            if len(chosen) >= target_count:
                break

    return sorted(chosen[:target_count], key=lambda c: c["start"])

def _validate_clips(
    clips: list[dict],
    min_duration: float = 30.0,
    max_duration: float = 180.0,
    min_gap: float = 12.0,
) -> list[dict]:
    """Remove weak clips: too short/long, overlapping, duplicate, or too close."""
    if not clips:
        return clips

    clips = sorted(clips, key=lambda c: c["start"])
    validated = []
    seen_ranges: set[tuple[int, int]] = set()

    for clip in clips:
        duration = clip["end"] - clip["start"]
        title = clip.get("title", "?")

        if clip["end"] <= clip["start"]:
            print(f"  ⚠ Dropped '{title}': invalid range ({clip['start']:.1f}s → {clip['end']:.1f}s)")
            continue

        rounded_range = (int(round(clip["start"])), int(round(clip["end"])))
        if rounded_range in seen_ranges:
            print(f"  ⚠ Dropped '{title}': duplicate time range")
            continue

        if duration < min_duration:
            print(f"  ⚠ Dropped '{title}': too short ({duration:.0f}s < {min_duration:.0f}s min)")
            continue

        if duration > max_duration:
            print(f"  ⚠ Dropped '{title}': too long ({duration:.0f}s > {max_duration:.0f}s max)")
            continue

        if validated and clip["start"] < validated[-1]["end"]:
            print(f"  ⚠ Dropped '{title}': overlaps with previous clip")
            continue

        if validated and (clip["start"] - validated[-1]["end"]) < min_gap:
            print(
                f"  ⚠ Dropped '{title}': too close to previous clip "
                f"({clip['start'] - validated[-1]['end']:.1f}s < {min_gap:.1f}s gap)"
            )
            continue

        seen_ranges.add(rounded_range)
        validated.append(clip)

    return validated


def parse_ai_response_segment_index(response, segments):
    """Parse AI response that uses FirstSegment/LastSegment; convert to start/end times.
    Handles plain text and markdown-formatted responses (e.g. **CLIP 1:**, **FirstSegment:** 5).
    """
    clips = []
    lines = response.split('\n')
    n_seg = len(segments)

    first_re = re.compile(r'FirstSegment[:\s*]*(\d+)', re.I)
    last_re  = re.compile(r'LastSegment[:\s*]*(\d+)',  re.I)
    title_re = re.compile(r'Title[:\s*]*(.+)',          re.I)
    why_re   = re.compile(r'Why[:\s*]*(.+)',            re.I)

    def _flush(current):
        if current.get('first') is not None and current.get('last') is not None:
            first_i = int(current['first'])
            last_i  = int(current['last'])
            if 0 <= first_i <= last_i < n_seg:
                start = segments[first_i]['start']
                end   = segments[last_i]['end']
                if end > start:
                    clips.append({
                        'start':  start,
                        'end':    end,
                        'title':  current.get('title', 'Clip'),
                        'reason': current.get('reason', ''),
                    })

    current = {}
    for raw_line in lines:
        # Strip markdown symbols so **CLIP 1:** and ### CLIP 1 both match
        line = re.sub(r'[*#_`~]', '', raw_line).strip()
        if not line:
            continue

        # Detect "CLIP N" header → save previous clip and reset
        if re.match(r'CLIP\s+\d+', line, re.I):
            _flush(current)
            current = {}
            continue

        m = first_re.search(line)
        if m:
            # Seeing a new FirstSegment while one is already collected → implicit new clip
            if current.get('first') is not None:
                _flush(current)
                current = {}
            current['first'] = m.group(1)
            continue

        m = last_re.search(line)
        if m:
            current['last'] = m.group(1)
            continue

        m = title_re.search(line)
        if m:
            current['title'] = re.sub(r'[*_`]', '', m.group(1)).strip()
            continue

        m = why_re.search(line)
        if m:
            current['reason'] = re.sub(r'[*_`]', '', m.group(1)).strip()

    _flush(current)
    return clips


def parse_ai_response_timestamps(response):
    """Fallback: parse old Start:/End: timestamp format."""
    clips = []
    lines = response.split('\n')
    start_re = re.compile(r'Start:\s*([\d.]+)', re.I)
    end_re = re.compile(r'End:\s*([\d.]+)', re.I)
    title_re = re.compile(r'Title:\s*(.+)', re.I)
    why_re = re.compile(r'Why:\s*(.+)', re.I)
    current_clip = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'CLIP\s+\d+', line, re.I):
            if current_clip and 'start' in current_clip and 'end' in current_clip and current_clip['end'] > current_clip['start']:
                clips.append(current_clip)
            current_clip = {}
        m = start_re.search(line)
        if m:
            try:
                current_clip['start'] = float(m.group(1))
            except ValueError:
                pass
            continue
        m = end_re.search(line)
        if m:
            try:
                current_clip['end'] = float(m.group(1))
            except ValueError:
                pass
            continue
        m = title_re.search(line)
        if m:
            current_clip['title'] = m.group(1).strip()
            continue
        m = why_re.search(line)
        if m:
            current_clip['reason'] = m.group(1).strip()
    if current_clip and 'start' in current_clip and 'end' in current_clip and current_clip['end'] > current_clip['start']:
        clips.append(current_clip)
    return clips


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clip_analyzer.py <transcript_json_file> [min_clips]")
        print("Example: python clip_analyzer.py 'Linux ssd_transcript.json' 5")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    min_clips = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    if not Path(transcript_file).exists():
        print(f"Error: File not found: {transcript_file}")
        sys.exit(1)
    
    clips = analyze_transcript_for_clips(transcript_file, min_clips)
    
    print(f"\n🎬 Ready to generate {len(clips)} clips!")
    print("Next step: Run the clip generator to create the actual video files")
