"""Write a lecture's transcript as plain text: one caption per line, no timestamps.

This is what the chaptering agent reads (see CHAPTERS.md): the timestamps would
only get in the way of reading the talk, and each line is still one caption, so a
chapter's first line can be found in the .srt afterwards.

    uv run python scripts/transcript_text.py data/transcripts/session1.srt > session1.txt
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tutor.captions import read_srt  # noqa: E402

for cue in read_srt(sys.argv[1]):
    print(cue.text)
