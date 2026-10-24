---
name: lecture-videos
description: Answer a question about what a session's lecture or coding segment covered, and point the student to the place in the recording.
---

# Lecture videos

1. **Several things asked? Plan them.** When the question spans more than one session
   or asks for several things (a comparison, a review sheet, a catch-up on a whole
   session), call `update_plan` first, with one task for each, and `mark_done` each task
   as you finish it. Each gets its own search and read, so the answer covers all of
   them. A single question goes straight to the search.

2. **Search.** Call `search_lectures` with the student's question in your own words and
   its key terms. For a follow-up, write the query from the whole question ("How is GRPO
   different from fine-tuning?"), not its last few words.

3. **Read.** Pick the part whose summary best answers the question, and read it with
   `read_lecture(session, part)`. If the answer seems to continue past the end, read
   the next part too. Find the moment the instructor makes the point: the paragraph
   that starts `[m:ss, video_start_at=...]`.

4. **Answer.** In two to four sentences, explain it the way the instructor did, with
   their example or analogy. Name the instructor.

5. **Link to the moment, and say how long to watch.** The course site opens a recording
   at a time, so the student can click straight to the point:

   > Josh explains GRPO in the Session 2 recording from **22:09** to about **26:57**,
   > roughly 5 minutes:
   > [watch from 22:09](https://www.ragpack.ai/products/introduction-to-agents/categories/2160923677/posts/2201100744?video_start_at=1329)

   - **The link**: the recording's page plus `?video_start_at=` and the number from the
     paragraph where the point is made, which may be later than the start of what you
     read. `read_lecture` shows the full link to copy.
   - **The window**: from that time to the end of the part you read (`read_lecture`
     says when it ends), and how many minutes that is, so the student knows how long it
     takes. Write times the way `read_lecture` does, with the hour past the first hour
     (`1:13:55`).
   - **The topic, in plain words**: "the part on GRPO", "where Luis explains the
     headlight analogy". The course page shows each session as one recording, so the
     student knows its parts by what's being taught.

6. **Not covered?** If no part's summary is about the question, say that the
   recordings so far don't seem to cover it, then answer from general knowledge and say
   that's what you're doing.

For examples of good answers, read this skill's `examples.md`.
