"""Lecture video search: the session recordings, split into chapters, searchable by meaning.

The data, in `data/`:

- `sessions.json`: each session's title, instructors, and the course page with its
  recording.
- `transcripts/session<N>.srt`: the recording's captions.
- `chapters/session<N>.json`: the chapters (start time, title, speaker, summary). A
  coding agent wrote them by reading the transcript (the brief is in the course repo,
  `RAG-Pack/intro-to-agents`, as `lecture-chapters/CHAPTERS.md`).
- `lecture_index.npz`: two embeddings per chapter, one of its title and summary, one of
  its transcript. It's built on first use, and again whenever the chapters change.

The captions and chapters come in the **lecture bundle**, a download on the course site
(`BUNDLE_PAGE`), rather than in this public repo: the recordings' Q&A has students
speaking and named. Without the bundle the tutor still runs, and the two tools tell
the student where to get it. `sessions.json` stays in the repo, so a session listed
there without chapters here means the student's bundle predates it.

A chapter's score is the better of its two matches. The title and summary match most
questions best (15 of 16 test questions ranked the right chapter first, against 12 of
16 for the transcript alone, which dilutes the topic), and the transcript catches
details the summary leaves out.

Two tools, the same search-then-read pattern as Session 3's retrieval tool:
`search_lectures` finds the chapters, `read_lecture` reads one chapter's transcript
with the times in it, so the tutor can link the student to the moment. The course site
opens a recording at a time with `?video_start_at=<seconds>`, so each paragraph's time
comes with its seconds, ready to copy into the link.

Chapters are internal: the course page shows each session as one recording. So the
tools call them **parts**, a word a student knows ("the part on GRPO"), label each by
its title, and pass its number only in the `read_lecture(...)` call to make. Tool output
that said "chapter 13" had the tutor telling students "chapter 13" too.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .captions import Cue, format_time, parse_time, read_srt
from .llm import EmbeddingModel

DATA = Path(__file__).resolve().parents[1] / "data"

# Where students download the lecture bundle, tutor-data.zip: Session 3's lesson
BUNDLE_PAGE = "https://www.ragpack.ai/products/introduction-to-agents/categories/2160943905/posts/2201198510"

# Longest transcript embedded per chapter, in characters (~6k tokens; the model takes 8k)
MAX_EMBED_CHARS = 24_000


@dataclass
class Chapter:
    """One chapter of a session's recording."""
    session: int
    number: int          # 1, 2, ... within the session
    title: str
    speaker: str
    summary: str
    start: float         # seconds into the video
    end: float
    cues: list[Cue]

    @property
    def times(self) -> str:
        return f"{format_time(self.start)} to {format_time(self.end)}"

    def embedding_texts(self) -> tuple[str, str]:
        """What gets embedded: the title and summary (what it's about), and the transcript (the details)."""
        transcript = " ".join(cue.text for cue in self.cues)
        return f"{self.title}\n{self.summary}", transcript[:MAX_EMBED_CHARS]


class Lectures:
    """The recordings' chapters, an embedding of each, and the two tools."""

    def __init__(self, data: str | Path = DATA, embedding_model: EmbeddingModel | None = None):
        self.data = Path(data)
        self.sessions = {s["session"]: s for s in json.loads((self.data / "sessions.json").read_text())}
        self.chapters = self._load_chapters()
        # Sessions with a recording page but no chapters here: not in the student's bundle yet
        self.missing = sorted(set(self.sessions) - {c.session for c in self.chapters})
        self.embedding_model = embedding_model or EmbeddingModel()
        self.embeddings = self._load_index() if self.chapters else None

    def _load_chapters(self) -> list[Chapter]:
        """Every session whose chapters and captions are here, with each chapter's captions."""
        chapters = []
        for n in sorted(self.sessions):
            path = self.data / "chapters" / f"session{n}.json"
            captions = self.data / "transcripts" / f"session{n}.srt"
            if not (path.exists() and captions.exists()):
                continue
            cues = read_srt(captions)
            marks = json.loads(path.read_text())["chapters"]

            # Each chapter runs to the next one's start (the last, to the end of the video)
            starts = [parse_time(mark["start"]) for mark in marks]
            ends = starts[1:] + [cues[-1].end]
            for i, (mark, start, end) in enumerate(zip(marks, starts, ends), start=1):
                chapters.append(Chapter(
                    session = n,
                    number  = i,
                    title   = mark["title"],
                    speaker = mark.get("speaker", ""),
                    summary = mark["summary"],
                    start   = start,
                    end     = end,
                    cues    = [cue for cue in cues if start <= cue.start < end],
                ))
        return chapters

    def _load_index(self, rebuild: bool = False) -> np.ndarray:
        """The chapter embeddings, shape (2, chapters, dims): summaries, then transcripts.

        From the saved index if the chapters haven't changed, else embedded now.
        """
        summaries, transcripts = zip(*[chapter.embedding_texts() for chapter in self.chapters])
        texts = list(summaries) + list(transcripts)
        key = hashlib.sha256("\n\n".join([self.embedding_model.model, *texts]).encode()).hexdigest()

        path = self.data / "lecture_index.npz"
        if path.exists() and not rebuild:
            saved = np.load(path)
            if str(saved["key"]) == key:
                return saved["embeddings"]

        # One request per 64 texts
        embeddings = self.embedding_model.embed(texts).reshape(2, len(self.chapters), -1)
        np.savez(path, key=key, embeddings=embeddings)
        return embeddings

    def chapter(self, session: int, number: int) -> Chapter | None:
        for chapter in self.chapters:
            if chapter.session == session and chapter.number == number:
                return chapter
        return None

    def bundle_note(self, sessions: list[int] | None = None) -> str:
        """What to tell the student when recordings are missing from their lecture bundle."""
        sessions = self.missing if sessions is None else sessions
        if not sessions:
            return ""
        names = ", ".join(str(n) for n in sessions)
        which = f"Session {names}'s recording isn't" if len(sessions) == 1 else f"Sessions {names}' recordings aren't"
        return (f"{which} on the student's computer yet. Tell them to download the newest lecture "
                f"bundle (tutor-data.zip) from {BUNDLE_PAGE}, unzip it in the tutor-agent folder "
                f"(it fills data/), and restart the tutor.")

    # ---- Tools ---------------------------------------------------------------

    def search_lectures(self, query: str, session: int = 0) -> str:
        """Search the course's lecture recordings for the parts that cover a topic. Write `query` as the topic itself, in the student's words plus its key terms ("why the model forgets earlier messages"), and leave out names and session titles, which match every part. Set `session` to search one session's recording only, when the student names a session; leave it out to search them all. Returns the 4 best-matching parts: session, title, start and end times in the video, a link that opens the recording at the start, speaker, a summary, and the `read_lecture` call that reads it. Then read the one whose title and summary fit the question best."""
        if not self.chapters:
            return self.bundle_note()
        if int(session) in self.missing:
            return self.bundle_note([int(session)])
        query_embedding = self.embedding_model.embed([query])[0]

        # Cosine similarity: a dot product, for embeddings of magnitude 1.
        # Each chapter scores its better match: summary or transcript.
        scores = (self.embeddings @ query_embedding).max(axis=0)

        # Only the one session's chapters, if asked
        if session:
            scores = np.where([c.session == int(session) for c in self.chapters], scores, -np.inf)
            if np.isinf(scores).all():
                return f"No recording for session {session} yet. Leave out `session` to search them all."
        ranked = [i for i in np.argsort(scores)[::-1][:4] if np.isfinite(scores[i])]

        results = []
        for index in ranked:
            chapter = self.chapters[index]
            speaker = f" ({chapter.speaker})" if chapter.speaker else ""
            minutes = max(1, round((chapter.end - chapter.start) / 60))
            url = self.sessions[chapter.session]["url"]
            results.append(
                f"Session {chapter.session}: \"{chapter.title}\"{speaker} · "
                f"read it with read_lecture(session={chapter.session}, part={chapter.number})\n"
                f"{chapter.times} in the video (about {minutes} min) · match {scores[index]:.2f}\n"
                # Its own link, so an answer from the search alone still opens the right recording
                f"Watch from the start of this part: {url}?video_start_at={int(chapter.start)}\n"
                f"{chapter.summary}"
            )

        covered = session or ", ".join(str(n) for n in sorted({c.session for c in self.chapters}))
        note = f" {self.bundle_note()}" if self.missing and not session else ""
        return "\n\n".join(results) + f"\n\n(Recordings searched: sessions {covered}.{note})"

    def read_lecture(self, session: int, part: int) -> str:
        """Read one part of a lecture recording: its transcript, with the time in the video every 30 seconds or so (and the seconds for a link that opens the recording there), so you can link the student to the moment something is said. Use the session and part numbers from `search_lectures`."""
        found = self.chapter(int(session), int(part))
        if found is None and int(session) in self.missing:
            return self.bundle_note([int(session)])
        if found is None:
            return f"No part {part} in session {session}'s recording. Use search_lectures to find one."

        info = self.sessions[found.session]
        speaker = f" ({found.speaker})" if found.speaker else ""
        link = f"{info['url']}?video_start_at="  # + seconds: the course site opens the video there
        minutes = max(1, round((found.end - found.start) / 60))
        lines = [
            f"Session {found.session} ({info['title']}): \"{found.title}\"{speaker}",
            f"{found.times} in the video (about {minutes} min). Recording: {info['url']}",
            f"Watch from the start of this part: {link}{int(found.start)}",
            "",
        ]

        # A new paragraph, with its time, every ~30 seconds
        paragraph, paragraph_start = [], None
        for cue in found.cues:
            if paragraph_start is None:
                paragraph_start = cue.start
            paragraph.append(cue.text)
            if cue.end - paragraph_start >= 30:
                lines.append(f"[{format_time(paragraph_start)}, video_start_at={int(paragraph_start)}] {' '.join(paragraph)}")
                paragraph, paragraph_start = [], None
        if paragraph:
            lines.append(f"[{format_time(paragraph_start)}, video_start_at={int(paragraph_start)}] {' '.join(paragraph)}")

        lines += [
            "",
            f"(To open the recording where a paragraph starts, link to {link}<its video_start_at>. "
            f"This part runs to {format_time(found.end)}. The student sees each session as one "
            f"recording, so describe this part by its topic.)",
        ]
        return "\n".join(lines)
