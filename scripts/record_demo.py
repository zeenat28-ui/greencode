#!/usr/bin/env python3
"""Render the system exercise into a video.

Runs `exercise_everything.py` as a subprocess, consumes its timestamped output,
and paints it into terminal-styled frames encoded to H.264/MP4 with the ffmpeg
binary bundled with `imageio-ffmpeg`.

    python scripts/record_demo.py                 # full run incl. test suite
    python scripts/record_demo.py --skip-tests    # faster
    python scripts/record_demo.py --out demo.mp4

Two things this had to get right, both found by looking at the output:

- Consolas has no U+2713/U+2717 glyphs, so status is drawn as ASCII badges.
  Using check marks rendered as empty tofu boxes.
- The typing effect *replaces* the last line rather than appending a new one.
  Appending leaves every intermediate prefix on screen and the terminal fills
  with duplicates of the same line.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

WIDTH, HEIGHT = 1600, 900
FONT_PATH = r"C:\Windows\Fonts\consola.ttf"
BOLD_FONT_PATH = r"C:\Windows\Fonts\consolab.ttf"
FONT_SIZE = 18
LINE_HEIGHT = 25
MARGIN_X = 32
MARGIN_TOP = 104
FOOTER_H = 46
MAX_LINES = (HEIGHT - MARGIN_TOP - FOOTER_H - 24) // LINE_HEIGHT
WRAP_COLS = 100

BG = (13, 17, 23)
CHROME = (22, 27, 34)
FG = (201, 209, 217)
DIM = (118, 126, 138)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
AMBER = (210, 153, 34)
CYAN = (57, 197, 207)
GREY = (125, 133, 144)

# ASCII badges, because Consolas cannot render the usual check/cross glyphs.
BADGE = {"pass": "[ OK ]", "fail": "[FAIL]", "warn": "[ ! ]"}


_FONT_CACHE: List[object] = []


def load_fonts() -> Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    """Return the cached (regular, bold) faces.

    Cached deliberately. Re-reading and re-parsing the TTF on every frame
    dominated render time and starved the encoder - the first recording came out
    less than a quarter of the length of the run it was recording.
    """
    if not _FONT_CACHE:
        _FONT_CACHE.append(ImageFont.truetype(FONT_PATH, FONT_SIZE))
        _FONT_CACHE.append(ImageFont.truetype(BOLD_FONT_PATH, FONT_SIZE))
    return _FONT_CACHE[0], _FONT_CACHE[1]


def style_for(kind: str) -> Tuple[tuple, bool]:
    return {
        "title": (CYAN, True),
        "section": (AMBER, True),
        "pass": (GREEN, True),
        "fail": (RED, True),
        "warn": (AMBER, False),
        "info": (DIM, False),
    }.get(kind, (FG, False))


def wrap(text: str, cols: int = WRAP_COLS) -> List[str]:
    if not text:
        return [""]
    return [text[i:i + cols] for i in range(0, len(text), cols)]


class Terminal:
    """A scrolling terminal buffer that can be re-rendered on demand."""

    def __init__(self) -> None:
        self.rows: List[Tuple[str, str]] = []
        self.passed = 0
        self.failed = 0

    def set_last(self, kind: str, text: str) -> None:
        if self.rows:
            self.rows[-1] = (kind, text)
        else:
            self.rows.append((kind, text))

    def add(self, kind: str, text: str) -> None:
        if kind == "pass":
            self.passed += 1
        elif kind == "fail":
            self.failed += 1
        self.rows.append((kind, text))
        if len(self.rows) > MAX_LINES:
            del self.rows[: len(self.rows) - MAX_LINES]

    def render(self, elapsed: float) -> Image.Image:
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(img)
        regular, bold = load_fonts()

        d.rectangle([0, 0, WIDTH, 54], fill=CHROME)
        for i, colour in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([22 + i * 30, 20, 38 + i * 30, 36], fill=colour)
        d.text((130, 17), "greencode-auditor  -  full system exercise",
               font=regular, fill=GREY)
        total = self.passed + self.failed
        counter = f"{self.passed} ok / {self.failed} failed" if total else "running"
        d.text((WIDTH - 300, 17), f"t+{elapsed:5.1f}s   {counter}",
               font=regular, fill=DIM)

        y = MARGIN_TOP
        for kind, text in self.rows[-MAX_LINES:]:
            colour, is_bold = style_for(kind)
            font = bold if is_bold else regular
            badge = BADGE.get(kind, "")
            prefix = f"{badge} " if badge else ""
            for i, piece in enumerate(wrap(text, max(20, WRAP_COLS - len(prefix)))):
                if y > HEIGHT - FOOTER_H - LINE_HEIGHT:
                    break
                if i == 0 and badge:
                    bw = d.textlength(badge, font=font)
                    d.rectangle([MARGIN_X, y - 3, MARGIN_X + bw + 12,
                                 y + FONT_SIZE + 3], outline=colour, width=1)
                    d.text((MARGIN_X + 6, y), badge, font=font, fill=colour)
                d.text((MARGIN_X + (110 if badge else 0), y), piece,
                       font=font, fill=colour)
                y += LINE_HEIGHT

        d.rectangle([0, HEIGHT - FOOTER_H, WIDTH, HEIGHT], fill=CHROME)
        d.text((MARGIN_X, HEIGHT - 34),
               "python scripts/exercise_everything.py    live code - real sockets "
               "- real hash-chained ledger",
               font=regular, fill=GREY)
        return img


class VideoWriter:
    """Feeds PIL frames into ffmpeg over a raw pipe."""

    def __init__(self, path: str, fps: int):
        import imageio_ffmpeg

        self.fps = fps
        self.path = path
        self.proc = subprocess.Popen(
            [
                imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{WIDTH}x{HEIGHT}", "-r", str(fps),
                "-i", "-",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p",
                # H.264 requires even dimensions.
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-movflags", "+faststart", path,
            ],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def write(self, frame: Image.Image) -> None:
        self.proc.stdin.write(frame.tobytes())

    def hold(self, term: Terminal, elapsed: float, seconds: float) -> None:
        """Emit frames for `seconds` at the real frame rate.

        This used to spin without sleeping, which queued far more frames than
        the declared fps and stretched the finished video out of proportion to
        the run it recorded.
        """
        frames = max(1, int(seconds * self.fps))
        for i in range(frames):
            self.write(term.render(elapsed))
            time.sleep(1.0 / self.fps)

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except (BrokenPipeError, ValueError):
            pass
        self.proc.wait(timeout=120)


def type_line(video: VideoWriter, term: Terminal, kind: str, text: str,
              start: float, cps: float) -> None:
    """Reveal one line in place, the way a terminal would.

    A row is appended *first* and then overwritten while typing. Typing
    straight into the last row erases the previous line instead of scrolling,
    which is what an earlier version did.
    """
    term.add(kind, "")
    if not text:
        return
    # Chunk size keeps the animation smooth without a frame per character.
    chunk = max(12, min(60, int(len(text) / 6) or 12))
    shown = 0
    while shown < len(text):
        shown = min(len(text), shown + chunk)
        term.set_last(kind, text[:shown])
        video.write(term.render(time.time() - start))
        time.sleep(1.0 / video.fps)
    term.set_last(kind, text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(ROOT, "greencode_demo.mp4"))
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--cps", type=float, default=150.0,
                        help="approximate characters revealed per second")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    cmd = [sys.executable, os.path.join(ROOT, "scripts", "exercise_everything.py"),
           "--json"]
    if args.skip_tests:
        cmd.append("--skip-tests")

    proc = subprocess.Popen(
        cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    # The subprocess is read on a separate thread. Reading it inline meant no
    # frames were emitted while it was busy - the pytest run alone is over a
    # minute of silence - so the finished video was a fraction of the length of
    # the run it was supposed to be recording. The main loop now renders at a
    # steady rate regardless of whether output is arriving.
    events: "queue.Queue[str]" = queue.Queue()
    done = threading.Event()

    def pump() -> None:
        try:
            for raw in proc.stdout:
                if raw.strip():
                    events.put(raw)
        finally:
            done.set()

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()

    term = Terminal()
    start = time.time()
    video = VideoWriter(args.out, args.fps)
    frame_dt = 1.0 / args.fps
    last_hold = 0.0

    try:
        term.add("title", "GREENCODE AUDITOR - FULL SYSTEM EXERCISE")
        term.add("info", "starting live run ...")
        video.hold(term, 0.0, 1.0)

        while not (done.is_set() and events.empty()):
            now = time.time() - start

            while not events.empty():
                raw = events.get_nowait().strip()
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                kind = event.get("kind", "info")
                text = event.get("text", "")
                type_line(video, term, kind, text, start, args.cps)
                # Results linger so each verdict is readable, not a blur.
                hold = 0.45 if kind in ("pass", "fail", "title", "section") else 0.08
                video.hold(term, time.time() - start, hold)
                last_hold = time.time() - start
                if not args.quiet:
                    print(f"\r  {term.passed} ok / {term.failed} failed   ",
                          end="", flush=True)

            # Keep the frame clock running through silent stretches.
            video.write(term.render(now))
            time.sleep(frame_dt)

        proc.wait()
        term.add("info", f"process exited with code {proc.returncode}")
        video.hold(term, time.time() - start, 3.0)
        if not args.quiet:
            print()
    finally:
        video.close()
        if proc.poll() is None:
            proc.kill()

    if os.path.exists(args.out):
        mb = os.path.getsize(args.out) / (1024 * 1024)
        print(f"Video written: {args.out}  ({mb:.1f} MB, {time.time() - start:.0f}s)")
        return 0
    print("Video was not produced.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
