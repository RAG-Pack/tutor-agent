---
name: study-log
description: Log the current study session in the student's study log, or review what they've studied so far.
---

# Study log

**Logging.** When the student asks you to log the session, call `log_session` right
away and fill in everything yourself:

- `start`: the time at the start of their first message in this conversation (after a
  compaction, the earliest time you can still see).
- `end`: the time at the start of their latest message.
- `learned`: one or two sentences, in the student's voice, on what they understand now
  that they didn't before ("Retrieval can be a tool the model decides to call, with its
  own query."). Take it from the conversation, not from the course outline.

Then tell them what you logged, in one line.

**Reviewing.** When they ask what they've studied, how much, or what to review, call
`read_log`. Answer from the log, and suggest one thing to review next: the oldest topic,
or one that the next session builds on.
