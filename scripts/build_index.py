"""Embed every lecture chapter, and save the index (data/lecture_index.npz).

The tutor does this on its own when the chapters change; run it to rebuild by hand,
or to try a search:

    uv run python scripts/build_index.py
    uv run python scripts/build_index.py "why does the model forget my name?"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tutor.lectures import Lectures  # noqa: E402

lectures = Lectures()
lectures.embeddings = lectures._load_index(rebuild=True)
print(f"Embedded {len(lectures.chapters)} chapters (summaries and transcripts): {lectures.embeddings.shape}")

if len(sys.argv) > 1:
    print()
    print(lectures.search_lectures(" ".join(sys.argv[1:])))
