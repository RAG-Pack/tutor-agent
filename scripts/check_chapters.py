"""Check a session's chapters against its captions.

Each chapter's `first_line` should be the caption that starts at its `start` time,
and the starts should run in order. Prints each chapter with its length.

    python3 scripts/check_chapters.py 1
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.captions import format_time, parse_time, read_srt  # noqa: E402

session = sys.argv[1]
cues = read_srt(ROOT / "data" / "transcripts" / f"session{session}.srt")
chapters = json.loads((ROOT / "data" / "chapters" / f"session{session}.json").read_text())["chapters"]

problems = []
previous = -1.0
for i, chapter in enumerate(chapters):
    start = parse_time(chapter["start"])

    # The caption that starts at `start` (to the second)
    matches = [cue for cue in cues if int(cue.start) == int(start)]
    if not any(cue.text.strip() == chapter["first_line"].strip() for cue in matches):
        found = [format_time(cue.start) for cue in cues if cue.text.strip() == chapter["first_line"].strip()]
        problems.append(f"chapter {i + 1}: no caption {chapter['first_line']!r} at {chapter['start']}"
                        f" (that line is at: {', '.join(found) or 'nowhere'})")
    if start <= previous:
        problems.append(f"chapter {i + 1}: starts at {chapter['start']}, not after the one before")
    for key in ("title", "summary"):
        if not chapter.get(key, "").strip():
            problems.append(f"chapter {i + 1}: empty {key}")
    previous = start

# Chapter lengths, to spot ones that are too long or too short
ends = [parse_time(c["start"]) for c in chapters[1:]] + [cues[-1].end]
for chapter, end in zip(chapters, ends):
    minutes = (end - parse_time(chapter["start"])) / 60
    print(f"{chapter['start']:>8}  {minutes:5.1f} min  {chapter['title']}")

print()
print("\n".join(problems) if problems else f"OK: {len(chapters)} chapters")
sys.exit(1 if problems else 0)
