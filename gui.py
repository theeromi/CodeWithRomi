#!/usr/bin/env python3
"""
Video Shorts Pipeline — Desktop GUI
Three modes accessible via tabs:
  1. Full Pipeline    — long video → AI finds clips → vertical Shorts with captions
  2. Format + Captions — already-shorts file → convert to 9:16 + per-word captions
  3. Captions Only    — already-formatted file → add per-word captions, keep dimensions
"""
from __future__ import annotations

import io
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from output_layout import ensure_image_gen_output, ensure_pipeline_output_dirs

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Set CUDA path before any imports that might load GPU libs
for _cuda in ("/usr/local/lib/ollama/cuda_v12", "/usr/local/lib/ollama/cuda_v13"):
    if os.path.exists(_cuda):
        os.environ["LD_LIBRARY_PATH"] = _cuda + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        break

PROJECT_ROOT = Path(__file__).resolve().parent

ensure_pipeline_output_dirs(PROJECT_ROOT)
ensure_image_gen_output(PROJECT_ROOT)


def get_pipeline_python() -> str:
    """Use venv Python for the pipeline (has deps); fallback to current executable."""
    candidates = (
        PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / "venv" / "bin" / "python",
    )
    for venv_py in candidates:
        if venv_py.exists():
            return str(venv_py)
    return sys.executable


def get_image_command(*args: str) -> list[str]:
    """Use Windows bootstrap launcher for image tasks; fallback to Python script."""
    run_image_bat = PROJECT_ROOT / "run_image.bat"
    if os.name == "nt" and run_image_bat.exists():
        return ["cmd", "/c", "run_image.bat", *args]
    return [get_pipeline_python(), str(PROJECT_ROOT / "run_image.py"), *args]


def _run_subprocess(cmd: list[str], log_queue: queue.Queue) -> None:
    """Run cmd in a subprocess, pushing stdout lines into log_queue."""
    env = os.environ.copy()
    # Force UTF-8 for child (tqdm progress bars are UTF-8). setdefault would not override a bad user value.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    for _cuda in ("/usr/local/lib/ollama/cuda_v12", "/usr/local/lib/ollama/cuda_v13"):
        if os.path.exists(_cuda):
            env["LD_LIBRARY_PATH"] = _cuda + os.pathsep + env.get("LD_LIBRARY_PATH", "")
            break
    try:
        # Binary pipe + TextIOWrapper: reliable on Windows (avoids cp1252 decode on the pipe)
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        assert proc.stdout is not None
        text_out = io.TextIOWrapper(
            proc.stdout,
            encoding="utf-8",
            errors="replace",
            newline="",
            line_buffering=True,
        )
        try:
            for line in text_out:
                log_queue.put(("out", line.rstrip()))
        finally:
            text_out.close()
        proc.wait()
        log_queue.put(("done", proc.returncode))
    except Exception as e:
        log_queue.put(("out", f"Error: {e}"))
        log_queue.put(("done", 1))


def main() -> None:
    import tkinter as tk
    from tkinter import ttk, filedialog, scrolledtext

    root = tk.Tk()
    root.title("Video Shorts Pipeline")
    root.geometry("740x580")
    root.minsize(520, 440)

    # Shared state — only one process runs at a time
    running = [False]
    log_queue: queue.Queue = queue.Queue()

    # Track all per-tab interactive widgets so they can be bulk-disabled/enabled
    all_entries: list[ttk.Entry] = []
    all_buttons: list[ttk.Button] = []

    def _set_ui_state(enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for w in all_entries:
            w.config(state=state)
        for w in all_buttons:
            if enabled:
                w.state(["!disabled"])
            else:
                w.state(["disabled"])

    def _browse_for(var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[
                ("Video", "*.mp4 *.mov *.mkv *.avi *.webm"),
                ("All files", "*.*"),
            ],
        )
        if path:
            var.set(path)

    def _browse_json_for(var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            title="Select clips JSON",
            filetypes=[
                ("Clips JSON", "*_clips.json *.json"),
                ("All files", "*.*"),
            ],
        )
        if path:
            var.set(path)

    def _launch(cmd_factory) -> None:
        """Validate, build command, launch subprocess, start log polling."""
        if running[0]:
            return
        result = cmd_factory()
        if result is None:
            return  # validation failed; error already logged
        cmd, label = result

        running[0] = True
        _set_ui_state(False)
        log_area.delete(1.0, tk.END)
        log_area.insert(tk.END, f"Starting: {label}\n\n")
        if os.name == "nt" and any(part.lower() == "run_image.bat" for part in cmd):
            log_area.insert(tk.END, "Using Windows image bootstrap: run_image.bat (auto dependency checks)\n\n")

        threading.Thread(target=_run_subprocess, args=(cmd, log_queue), daemon=True).start()

        def poll():
            try:
                while True:
                    kind, msg = log_queue.get_nowait()
                    if kind == "out":
                        log_area.insert(tk.END, msg + "\n")
                        log_area.see(tk.END)
                    else:  # done
                        running[0] = False
                        _set_ui_state(True)
                        if msg != 0:
                            log_area.insert(tk.END, f"\nProcess exited with code {msg}\n")
                        log_area.see(tk.END)
                        return
            except queue.Empty:
                pass
            root.after(100, poll)

        root.after(100, poll)

    def _require_video(var: tk.StringVar) -> str | None:
        """Return the video path, or None (after logging an error) if invalid."""
        path = var.get().strip()
        if not path:
            log_area.insert(tk.END, "Please select a video file first.\n")
            log_area.see(tk.END)
            return None
        if not Path(path).exists():
            log_area.insert(tk.END, f"File not found: {path}\n")
            log_area.see(tk.END)
            return None
        return path

    # ── Notebook (tabs) ──────────────────────────────────────────────────────
    nb = ttk.Notebook(root)
    nb.pack(fill=tk.X, padx=10, pady=(10, 0))

    # ── Tab 1: Full Pipeline ─────────────────────────────────────────────────
    tab1 = ttk.Frame(nb, padding=10)
    nb.add(tab1, text="  Full Pipeline  ")

    clips_var = tk.IntVar(value=5)
    vid1_var = tk.StringVar()

    ttk.Label(tab1, text="Long video to process:").grid(row=0, column=0, sticky=tk.W, pady=(0, 3))
    e1 = ttk.Entry(tab1, textvariable=vid1_var, width=52)
    e1.grid(row=1, column=0, sticky=tk.EW)
    tab1.columnconfigure(0, weight=1)
    b1_browse = ttk.Button(tab1, text="Browse…", command=lambda: _browse_for(vid1_var))
    b1_browse.grid(row=1, column=1, padx=(8, 0))
    all_entries.append(e1)
    all_buttons.append(b1_browse)

    ttk.Label(tab1, text="Number of clips to find (1–10):").grid(row=2, column=0, sticky=tk.W, pady=(8, 3))
    clips_spin = ttk.Spinbox(tab1, from_=1, to=10, width=5, textvariable=clips_var)
    clips_spin.grid(row=3, column=0, sticky=tk.W)
    all_entries.append(clips_spin)

    def _start_pipeline():
        path = _require_video(vid1_var)
        if path is None:
            return None
        try:
            n = max(1, min(10, int(clips_var.get())))
        except Exception:
            n = 5
        clips_var.set(n)
        cmd = [
            get_pipeline_python(),
            str(PROJECT_ROOT / "run_pipeline.py"),
            path,
            "--clips", str(n),
        ]
        return cmd, f"Full Pipeline — {n} clips — {Path(path).name}"

    b1_start = ttk.Button(tab1, text="Start Pipeline", command=lambda: _launch(_start_pipeline))
    b1_start.grid(row=3, column=1, padx=(8, 0))
    all_buttons.append(b1_start)

    ttk.Label(
        tab1,
        text="Transcribes the full video, uses AI to find the best moments, then exports each as a 9:16 Short with captions.",
        wraplength=580,
        foreground="#555",
    ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    # ── Tab 2: Format + Captions ─────────────────────────────────────────────
    tab2 = ttk.Frame(nb, padding=10)
    nb.add(tab2, text="  Format + Captions  ")

    vid2_var = tk.StringVar()

    ttk.Label(tab2, text="Video to convert (already shorts length):").grid(row=0, column=0, sticky=tk.W, pady=(0, 3))
    e2 = ttk.Entry(tab2, textvariable=vid2_var, width=52)
    e2.grid(row=1, column=0, sticky=tk.EW)
    tab2.columnconfigure(0, weight=1)
    b2_browse = ttk.Button(tab2, text="Browse…", command=lambda: _browse_for(vid2_var))
    b2_browse.grid(row=1, column=1, padx=(8, 0))
    all_entries.append(e2)
    all_buttons.append(b2_browse)

    def _start_vertical():
        path = _require_video(vid2_var)
        if path is None:
            return None
        cmd = [
            get_pipeline_python(),
            str(PROJECT_ROOT / "run_direct.py"),
            path,
            "--mode", "vertical-captions",
        ]
        return cmd, f"Format + Captions — {Path(path).name}"

    b2_start = ttk.Button(
        tab2,
        text="Convert to Vertical + Add Captions",
        command=lambda: _launch(_start_vertical),
    )
    b2_start.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    all_buttons.append(b2_start)

    ttk.Label(
        tab2,
        text="Transcribes the video, scales it to 1080×1920 (full frame visible, black bars if needed), then burns in per-word highlighted captions.",
        wraplength=580,
        foreground="#555",
    ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    # ── Tab 3: Captions Only ─────────────────────────────────────────────────
    tab3 = ttk.Frame(nb, padding=10)
    nb.add(tab3, text="  Captions Only  ")

    vid3_var = tk.StringVar()

    ttk.Label(tab3, text="Video to caption (already formatted):").grid(row=0, column=0, sticky=tk.W, pady=(0, 3))
    e3 = ttk.Entry(tab3, textvariable=vid3_var, width=52)
    e3.grid(row=1, column=0, sticky=tk.EW)
    tab3.columnconfigure(0, weight=1)
    b3_browse = ttk.Button(tab3, text="Browse…", command=lambda: _browse_for(vid3_var))
    b3_browse.grid(row=1, column=1, padx=(8, 0))
    all_entries.append(e3)
    all_buttons.append(b3_browse)

    def _start_captions():
        path = _require_video(vid3_var)
        if path is None:
            return None
        cmd = [
            get_pipeline_python(),
            str(PROJECT_ROOT / "run_direct.py"),
            path,
            "--mode", "captions-only",
        ]
        return cmd, f"Captions Only — {Path(path).name}"

    b3_start = ttk.Button(
        tab3,
        text="Add Captions Only",
        command=lambda: _launch(_start_captions),
    )
    b3_start.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    all_buttons.append(b3_start)

    ttk.Label(
        tab3,
        text="Transcribes the video and overlays per-word highlighted captions. Dimensions are preserved — use this for videos already in 9:16.",
        wraplength=580,
        foreground="#555",
    ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    # ── Tab 4: Thumbnail ─────────────────────────────────────────────────────
    tab4 = ttk.Frame(nb, padding=10)
    nb.add(tab4, text="  Thumbnail  ")

    # Sub-notebook: "From Clips" / "Custom"
    thumb_nb = ttk.Notebook(tab4)
    thumb_nb.pack(fill=tk.BOTH, expand=True)

    # ── Sub-tab A: From Clips ────────────────────────────────────────────────
    subt_clips = ttk.Frame(thumb_nb, padding=8)
    thumb_nb.add(subt_clips, text=" From Clips ")

    json_var = tk.StringVar()
    extra_prompt_var = tk.StringVar()
    thumb_aspect_var = tk.StringVar(value="16:9")

    ttk.Label(subt_clips, text="Clips JSON (from a pipeline run):").grid(row=0, column=0, sticky=tk.W, pady=(0, 3))
    e_json = ttk.Entry(subt_clips, textvariable=json_var, width=46)
    e_json.grid(row=1, column=0, sticky=tk.EW)
    subt_clips.columnconfigure(0, weight=1)
    b_json_browse = ttk.Button(subt_clips, text="Browse…", command=lambda: _browse_json_for(json_var))
    b_json_browse.grid(row=1, column=1, padx=(8, 0))
    all_entries.append(e_json)
    all_buttons.append(b_json_browse)

    ttk.Label(subt_clips, text="Extra prompt (optional — adds context to each title):").grid(
        row=2, column=0, sticky=tk.W, pady=(8, 3))
    e_extra = ttk.Entry(subt_clips, textvariable=extra_prompt_var, width=46)
    e_extra.grid(row=3, column=0, columnspan=2, sticky=tk.EW)
    all_entries.append(e_extra)

    ttk.Label(subt_clips, text="Aspect ratio:").grid(row=4, column=0, sticky=tk.W, pady=(8, 3))
    ratio_frame_c = ttk.Frame(subt_clips)
    ratio_frame_c.grid(row=5, column=0, columnspan=2, sticky=tk.W)
    ttk.Radiobutton(ratio_frame_c, text="16:9  (1280×720 YouTube)", variable=thumb_aspect_var, value="16:9").pack(side=tk.LEFT)
    ttk.Radiobutton(ratio_frame_c, text="9:16  (1080×1920 Shorts)", variable=thumb_aspect_var, value="9:16").pack(side=tk.LEFT, padx=(16, 0))

    def _start_thumb_clips():
        path = json_var.get().strip()
        if not path:
            log_area.insert(tk.END, "Please select a clips JSON file first.\n")
            log_area.see(tk.END)
            return None
        if not Path(path).exists():
            log_area.insert(tk.END, f"File not found: {path}\n")
            log_area.see(tk.END)
            return None
        cmd = get_image_command(
            "--mode", "thumbnail-clips",
            "--clips-json", path,
            "--aspect", thumb_aspect_var.get(),
        )
        extra = extra_prompt_var.get().strip()
        if extra:
            cmd += ["--prompt", extra]
        return cmd, f"Thumbnails from clips — {Path(path).name}"

    b_tc_start = ttk.Button(subt_clips, text="Generate Thumbnails for All Clips",
                            command=lambda: _launch(_start_thumb_clips))
    b_tc_start.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    all_buttons.append(b_tc_start)

    # ── Sub-tab B: Custom ────────────────────────────────────────────────────
    subt_custom = ttk.Frame(thumb_nb, padding=8)
    thumb_nb.add(subt_custom, text=" Custom ")

    custom_prompt_var = tk.StringVar()
    custom_title_var = tk.StringVar()
    custom_aspect_var = tk.StringVar(value="16:9")

    ttk.Label(subt_custom, text="Prompt (describe the background image):").grid(row=0, column=0, sticky=tk.W, pady=(0, 3))
    e_cprompt = ttk.Entry(subt_custom, textvariable=custom_prompt_var, width=46)
    e_cprompt.grid(row=1, column=0, columnspan=2, sticky=tk.EW)
    subt_custom.columnconfigure(0, weight=1)
    all_entries.append(e_cprompt)

    ttk.Label(subt_custom, text="Title text (overlaid on image):").grid(row=2, column=0, sticky=tk.W, pady=(8, 3))
    e_ctitle = ttk.Entry(subt_custom, textvariable=custom_title_var, width=46)
    e_ctitle.grid(row=3, column=0, columnspan=2, sticky=tk.EW)
    all_entries.append(e_ctitle)

    ttk.Label(subt_custom, text="Aspect ratio:").grid(row=4, column=0, sticky=tk.W, pady=(8, 3))
    ratio_frame_u = ttk.Frame(subt_custom)
    ratio_frame_u.grid(row=5, column=0, columnspan=2, sticky=tk.W)
    ttk.Radiobutton(ratio_frame_u, text="16:9  (1280×720 YouTube)", variable=custom_aspect_var, value="16:9").pack(side=tk.LEFT)
    ttk.Radiobutton(ratio_frame_u, text="9:16  (1080×1920 Shorts)", variable=custom_aspect_var, value="9:16").pack(side=tk.LEFT, padx=(16, 0))

    def _start_thumb_custom():
        prompt = custom_prompt_var.get().strip()
        if not prompt:
            log_area.insert(tk.END, "Please enter a prompt first.\n")
            log_area.see(tk.END)
            return None
        cmd = get_image_command(
            "--mode", "thumbnail-custom",
            "--prompt", prompt,
            "--aspect", custom_aspect_var.get(),
        )
        title = custom_title_var.get().strip()
        if title:
            cmd += ["--title", title]
        return cmd, f"Custom thumbnail — {prompt[:40]}"

    b_cu_start = ttk.Button(subt_custom, text="Generate Thumbnail",
                            command=lambda: _launch(_start_thumb_custom))
    b_cu_start.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    all_buttons.append(b_cu_start)

    ttk.Label(
        tab4,
        text="Thumbnails save to: image_gen/output/  (JPEG, 95% quality)",
        font=("", 9),
        foreground="#555",
    ).pack(anchor=tk.W, pady=(6, 0))

    # ── Tab 5: Transition Clip ────────────────────────────────────────────────
    tab5 = ttk.Frame(nb, padding=10)
    nb.add(tab5, text="  Transition Clip  ")

    tr_prompt_var = tk.StringVar()
    tr_duration_var = tk.DoubleVar(value=2.0)
    tr_fade_var = tk.StringVar(value="both")

    ttk.Label(tab5, text="Prompt (describe the visual):").grid(row=0, column=0, sticky=tk.W, pady=(0, 3))
    ttk.Label(tab5, text='e.g. "dark space particles", "neon city bokeh", "abstract fire"',
              foreground="#888", font=("", 9)).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))
    e_tr = ttk.Entry(tab5, textvariable=tr_prompt_var, width=46)
    e_tr.grid(row=1, column=0, sticky=tk.EW, columnspan=2)
    tab5.columnconfigure(0, weight=1)
    all_entries.append(e_tr)

    ctrl_frame = ttk.Frame(tab5)
    ctrl_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    ttk.Label(ctrl_frame, text="Duration (s):").pack(side=tk.LEFT)
    dur_spin = ttk.Spinbox(ctrl_frame, from_=0.5, to=5.0, increment=0.5, width=6, textvariable=tr_duration_var)
    dur_spin.pack(side=tk.LEFT, padx=(4, 20))
    all_entries.append(dur_spin)

    ttk.Label(ctrl_frame, text="Fade:").pack(side=tk.LEFT)
    fade_cb = ttk.Combobox(ctrl_frame, textvariable=tr_fade_var,
                           values=("both", "in", "out", "none"), state="readonly", width=8)
    fade_cb.pack(side=tk.LEFT, padx=(4, 0))
    all_entries.append(fade_cb)

    def _start_transition():
        prompt = tr_prompt_var.get().strip()
        if not prompt:
            log_area.insert(tk.END, "Please enter a prompt first.\n")
            log_area.see(tk.END)
            return None
        try:
            dur = float(tr_duration_var.get())
            dur = max(0.5, min(5.0, dur))
        except Exception:
            dur = 2.0
        tr_duration_var.set(dur)
        cmd = get_image_command(
            "--mode", "transition",
            "--prompt", prompt,
            "--duration", str(dur),
            "--fade", tr_fade_var.get(),
        )
        return cmd, f"Transition — {dur}s — {prompt[:40]}"

    b_tr_start = ttk.Button(tab5, text="Generate Transition Clip",
                            command=lambda: _launch(_start_transition))
    b_tr_start.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    all_buttons.append(b_tr_start)

    ttk.Label(
        tab5,
        text="Outputs a short MP4 with Ken Burns zoom + fade. Saves to image_gen/output/.",
        wraplength=580,
        foreground="#555",
    ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    # ── Shared status + log ──────────────────────────────────────────────────
    ttk.Label(
        root,
        text="Output saves to: generated_clips/  (inside the project folder)",
        font=("", 9),
        foreground="#555",
    ).pack(anchor=tk.W, padx=10, pady=(6, 0))

    ttk.Label(root, text="Log / progress:").pack(anchor=tk.W, padx=10, pady=(4, 0))
    log_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
    log_frame.pack(fill=tk.BOTH, expand=True)
    log_area = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        font=("Consolas", 10) if sys.platform != "darwin" else ("Monaco", 10),
        state=tk.NORMAL,
    )
    log_area.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
