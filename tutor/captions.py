"""Caption files (.srt): read them, and write times the way a student reads them."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    """One caption: the words on screen, and when."""
    start: float  # seconds into the video
    end: float
    text: str


# 00:01:02,345 --> 00:01:05,000
TIMING = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def _seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def read_srt(path: str | Path) -> list[Cue]:
    """Parse an .srt file into cues, in order."""
    cues = []
    # Cues are separated by blank lines: a number, the timing, then the text
    for block in re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8").strip()):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            match = TIMING.search(line)
            if match:
                text = " ".join(lines[i + 1:]).strip()
                if text:
                    cues.append(Cue(_seconds(*match.groups()[:4]), _seconds(*match.groups()[4:]), text))
                break
    return cues


def parse_time(text: str) -> float:
    """'1:02:03' or '02:03' -> seconds."""
    seconds = 0.0
    for part in text.strip().split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


def format_time(seconds: float) -> str:
    """Seconds -> '1:02:03', or '2:03' under an hour (what a video player shows)."""
    seconds = int(seconds)
    h, m, s = seconds // 3600, seconds // 60 % 60, seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
