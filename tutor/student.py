"""What the tutor keeps about the student: a memory file and a study log.

- `MEMORY.md`: what the student has told the tutor about themselves. It goes into the
  system prompt on every message, like `TUTOR.md`, and the tutor adds to it with
  `remember`. (Session 3 searched these notes with RAG; a short file fits in the
  prompt whole, which is how Claude Code's memory works.)
- `study_log.tsv`: one row per study session, from Session 2 and 3's `log_session`.

Both live in the student's folder (`student/`, not in git). The first run copies in
the example student from Session 3, so there's something to ask about.
"""

import csv
import shutil
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "student"


class Student:
    """One student's memory file and study log, with the tools that use them."""

    def __init__(self, folder: str | Path):
        self.folder = Path(folder)
        if not self.folder.exists():
            shutil.copytree(EXAMPLE, self.folder)
        self.memory_file = self.folder / "MEMORY.md"
        self.log_file = self.folder / "study_log.tsv"

    # ---- Tools ---------------------------------------------------------------

    def remember(self, note: str) -> str:
        """Save something lasting the student told you about themselves (their background, goals, what they're building, how they like to learn), as one short sentence. It's in your instructions from the next message on, so save each fact once."""
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(f"- {note.strip()}\n")
        return f"Saved to {self.memory_file.name}: {note.strip()}"

    def read_log(self) -> str:
        """Read the student's whole study log: when they studied, and what they learned each time."""
        if not self.log_file.exists():
            return "The study log is empty."
        return self.log_file.read_text(encoding="utf-8")

    def log_session(self, start: str, end: str, learned: str) -> str:
        """Add this study session to the student's log. Fill in all three yourself, without asking the student: `start` and `end` are the times at the start of the student's first and latest messages, like '2026-10-21 17:05 EDT', and `learned` is one or two sentences, from the conversation, on what the student understands now that they didn't before."""
        new = not self.log_file.exists()
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            if new:
                writer.writerow(["start", "end", "learned"])
            writer.writerow([start, end, learned])
        return f"Added to {self.log_file.name}: {start} to {end}, {learned}"

    # ---- For the UI ----------------------------------------------------------

    def log_rows(self) -> list[list[str]]:
        """The log as rows, header first."""
        if not self.log_file.exists():
            return [["start", "end", "learned"]]
        with open(self.log_file, newline="", encoding="utf-8") as f:
            return list(csv.reader(f, delimiter="\t"))
