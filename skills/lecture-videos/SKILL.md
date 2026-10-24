---
name: lecture-videos
description: Answer a question about what a session's lecture or coding segment covered, and point the student to the place in the recording.
---

# Lecture videos

1. **Several parts? Plan them.** When the question spans more than one session or asks
   for several things (a comparison, a review sheet, a catch-up on a whole session),
   call `update_plan` first, with one task per part, and `mark_done` each task as you
   finish it. Each part gets its own search and read, so the answer covers all of them.
   A single question goes straight to the search.

2. **Search.** Call `search_lectures` with the student's question in your own words and
   its key terms. For a follow-up, write the query from the whole question ("How is GRPO
   different from fine-tuning?"), not its last few words.

3. **Read.** Pick the chapter whose summary best answers the question, and read it with
   `read_lecture(session, chapter)`. If the answer seems to continue past the end, read
   the next chapter too. Find the moment the instructor makes the point: the `[m:ss]`
   time at the start of that paragraph.

4. **Answer.** In two to four sentences, explain it the way the instructor did, with
   their example or analogy. Name the instructor.

5. **Point to the place.** The course site has no links to a time, so give the session,
   the time to skip to, and the recording's page:

   > Josh explains this in the Session 2 recording at **22:09** (*GRPO: group relative
   > policy optimization*): open https://www.ragpack.ai/... and skip to 22:09.

   Use the time of the paragraph where the point is made, which may be later than the
   chapter's start.

6. **Not covered?** If no chapter's summary is about the question, say that the
   recordings so far don't seem to cover it, then answer from general knowledge and say
   that's what you're doing.

For examples of good answers, read this skill's `examples.md`.
