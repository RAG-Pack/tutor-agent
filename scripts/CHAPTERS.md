# Chaptering a lecture recording

The brief given to a coding agent (one per recording) to split a session's transcript
into chapters. Its output, `data/chapters/session<N>.json`, is what
`scripts/build_index.py` embeds for the `search_lectures` tool. To add a new session's
recording: put its captions in `data/transcripts/session<N>.srt`, add the session to
`data/sessions.json`, hand this brief to an agent with `<N>` filled in, then rebuild the
index.

---

You're splitting the recording of Session `<N>` of RAG Pack's *Introduction to Agents*
course into chapters, so a tutor agent can point students to the right place in the
video. The instructors are Luis Serrano, Josh Starmer, Chris McCormick, Maarten
Grootendorst and Jay Alammar; the captions are auto-generated and misspell names
(e.g. "Josh Starrmer", "Martin" for Maarten), so spell them correctly in what you
write. `data/sessions.json` says who taught what.

## 1. Read the talk, without timestamps

Make the plain transcript (one caption per line, no timestamps):

```bash
python3 scripts/transcript_text.py data/transcripts/session<N>.srt > /tmp/session<N>.txt
```

Read **all** of it, in order (in chunks of a few hundred lines). Mark a chapter
wherever the talk moves to a new topic: a new idea in the lecture, a demo, the hand-off
to the next speaker, Q&A (a chapter per question, or per few related questions), each
part of the coding segment. A recording runs 1.5 to 2 hours; expect a chapter every 3 to
8 minutes, so 15 to 35 in all. Short banter at the very start can be one "Welcome"
chapter.

## 2. Title and summarize each chapter

- `title`: 3 to 8 words, specific enough to search for ("Why the model forgets: message
  history"), not generic ("Discussion", "More on agents").
- `summary`: 2 to 3 sentences on what's explained, with the key terms, examples and
  analogies the speaker actually uses, so a student's question finds it by meaning.
- `speaker`: who's talking for most of the chapter, if the transcript makes it clear
  (introductions, hand-offs, "as Josh said"); otherwise `""`.

## 3. Match each chapter to the captions

- `first_line`: the caption line the chapter starts on, copied exactly from the plain
  transcript (a whole line).
- `start`: that caption's start time in `data/transcripts/session<N>.srt`, as `H:MM:SS`.
  Find it with `grep -n -F "<first_line>" data/transcripts/session<N>.srt`: the timing
  line is just above the text. If the line appears more than once, take the occurrence
  after the previous chapter's start.

## 4. Write and check

Write `data/chapters/session<N>.json`:

```json
{
  "session": <N>,
  "chapters": [
    {"start": "0:00:00", "first_line": "...", "title": "...", "speaker": "...", "summary": "..."}
  ]
}
```

Then run `python3 scripts/check_chapters.py <N>`, which confirms each `first_line` is
the caption at `start` and the starts are in order, and fix anything it reports.
