---
name: quiz
description: Quiz the student on a session's material with short questions, one at a time, to check what stuck.
---

# Quiz

1. **Which session?** If the student didn't say, ask which session (or topic) to cover.

2. **Ground the questions in the lecture.** Call `search_lectures` for the session's
   main topics, and read one or two parts with `read_lecture`, so each question is
   about something that was actually taught, in the instructor's terms.

3. **Ask one question at a time**, five in all, and wait for each answer. Mix the kinds:
   - explain an idea in their own words ("Why does the model forget your name?")
   - predict what code does ("What's in `memory.messages` after two turns?")
   - compare two things ("Agent or workflow: who decides when to stop?")

4. **After each answer**, say what was right first, then fill in what was missing in a
   sentence or two. If they were unsure, link to the place in the recording to rewatch,
   with how long it runs (as in the **lecture-videos** skill).

5. **At the end**, give the score, name the one idea to review, and offer to log the
   session.
