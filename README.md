# tutor-agent

A course tutor for RAG Pack's *Introduction to Agents*. It's the `TinyAgent` from
Session 4's notebook (*Planning*), moved into `.py` files and given:

- a **`TUTOR.md`**, always in the system prompt, with the tutor's persona and guidance
  (the way Claude Code always loads `CLAUDE.md`);
- **skills** in a `skills/` folder, discovered progressively;
- **lecture video search**: the session recordings split into chapters, so the tutor can
  answer "what did Josh say about GRPO?" and send the student to the right minute;
- a **student memory** (`MEMORY.md`) and the **study log** from Sessions 2 and 3;
- **the loop and planning** from Session 4: a question can take several tool calls,
  and a request with several parts gets a plan (`update_plan`, `mark_done`);
- a **Gradio** chat in place of the notebook's `ChatUI`.

It runs on OpenAI's `gpt-5.4-nano`, the smallest and cheapest model from the Oct 6 tests:
2–4 s per turn, about a cent for a 10-question chat.

The [`colab-mcp`](https://github.com/RAG-Pack/tutor-agent/tree/colab-mcp) branch adds
**Colab lessons over MCP**: Google's Colab MCP server lets the tutor build a short
notebook in the student's browser, with example cells it has run to check and an
exercise to finish. `main` is the simpler version, without it.

Each session's version is tagged, with a release page: `session-3` is the tutor
before planning, with Session 3's **Continue** button.

## Run it

```bash
uv sync
export OPENAI_API_KEY=...        # or have OPENAI_AGENTS_COURSE set, as in env.sh
uv run tutor                     # http://localhost:7860
```

`uv run tutor --share` adds a public `gradio.live` link. `TUTOR_MODEL` picks another
model (any gpt-5.4 model works; older ones reject `reasoning_effort: "none"`), and
`TUTOR_CONTEXT` sets the context budget for auto-compaction (default 32,000 tokens).

The first run copies the example student from Session 3 (a backend engineer building
a Discord bot, with five logged study sessions) into `student/`, which git ignores.
Edit or empty `student/MEMORY.md` and `student/study_log.tsv` to make it yours.

## What's where

| | |
|---|---|
| `TUTOR.md` | The tutor's persona and guidance, re-read before every message |
| `skills/` | `lecture-videos`, `quiz`, `study-log`: one folder each, with a `SKILL.md` |
| `tutor/llm.py` | `LLM` and `EmbeddingModel` (Session 3's, pointed at OpenAI) |
| `tutor/memory.py` | `Memory` and `CompactMemory` (Session 3's) |
| `tutor/tools.py` | `tool_to_schema` and `NativeTools` (Session 3's) |
| `tutor/skills.py` | `Skills`: a `NativeTools` with the `load_skill` tool and the skills list |
| `tutor/planner.py` | `NativeReAct` and `NativePlanAndSolve` (Session 4's): `max_steps`, and the plan tools |
| `tutor/agent.py` | `Trajectory` and `TinyAgent`, with the planner, the system prompt from files, and the loop |
| `tutor/lectures.py` | The chapters, their embeddings, `search_lectures` and `read_lecture` |
| `tutor/student.py` | `MEMORY.md` and the study log: `remember`, `read_log`, `log_session` |
| `tutor/build.py` | `build_tutor()`: everything wired into one agent |
| `tutor/app.py` | The Gradio chat |
| `data/` | `sessions.json` (titles, recording pages), captions, chapters (made in the course repo) |

## How it works

### The system prompt: `TUTOR.md`, the student's memory, the skills list

`TinyAgent` builds its system prompt from files, re-read before every message so an
edit takes effect on the next one: `TUTOR.md`, then `student/MEMORY.md`, then the skills
list. That replaces the notebook's **System** field, where the student typed which
files to include. The **What the model sees** tab shows the result, the messages and
the tool schemas.

### Skills, progressively

A skill is a folder with a `SKILL.md`: frontmatter with a `name` and `description`, then
instructions. They load in three levels:

1. **Always**: each skill's name and description, one line each in the system prompt.
2. **When a request matches**: the model calls `load_skill(name)` and gets the
   instructions.
3. **When the instructions say so**: another file in the skill's folder,
   `load_skill(name, file)` (`lecture-videos` keeps example answers in `examples.md`).

So a skill costs a line of context until it's used. The book's `Skills` (Ch. 5) makes
each skill a tool of its own; here one `load_skill` tool serves them all. Adding a
folder adds a skill, no restart needed.

On 18 test requests that each matched a skill, `gpt-5.4-nano` loaded the right one 18
times, once the skills list said to load a matching skill "even when you think you know
how" and `TUTOR.md` named the skill for lecture questions (10 of 12 before).

### Lecture video search

1. **Chapters.** A coding agent reads a session's transcript without timestamps, marks
   the natural break points, titles and summarizes each chapter, then matches each
   chapter's first line to the captions for its start time. The brief and the tools
   that check its work live with the course material, in `sessions/lecture-chapters/`
   of the course repo (`chrisjmccormick/An-Illustrated-Guide-To-AI-Agents`); this repo
   ships the results in `data/chapters/` (Session 1: 35 chapters, Session 2: 28, Session 3: 25).
2. **Index.** Each chapter gets two embeddings (OpenAI `text-embedding-3-small`): its
   title and summary, and its transcript. A chapter's score is the better of the two. On
   16 test questions the title-and-summary embedding put the right chapter first 15
   times, the transcript alone 12 times (a whole chapter's talk dilutes its topic). The
   index builds itself on first use and whenever the chapters change.
3. **Tools.** `search_lectures(query, session)` returns the 4 best chapters (times,
   speaker, summary); `read_lecture(session, part)` returns that chapter's
   transcript with a time every ~30 seconds. The `lecture-videos` skill says how to
   answer: explain it the instructor's way, then link to the moment and say roughly how
   long to watch. The course site opens a recording at a time with
   `?video_start_at=<seconds>`, so each paragraph's time comes with its seconds, and the
   model copies the number rather than converting `m:ss`. The course page has no
   chapters, so what the model sees calls them **parts**, labeled by title, with the
   number only in the `read_lecture(...)` call: with "chapter 13" in the tool output,
   the tutor told students "chapter 13" too. Search results carry a link to each part's
   start as well, since answers built from the search alone otherwise put Session 1
   times on the Session 2 page (the one in the skill's example). On 30 answers (five
   lecture questions, 6 runs each, Oct 23): every answer linked, all 62 links opened the
   right recording at a real start time, 28 gave a window (15 in minutes, the rest as
   a range of times), and none said "chapter" (7 of 15 before the rename).

**Adding a session's recording:** follow `sessions/lecture-chapters/CHAPTERS.md` in
the course repo, with this repo checked out beside it. It puts the captions in
`data/transcripts/`, the session in `data/sessions.json` and the chapters in
`data/chapters/`, here; the index rebuilds on the next start.

### The loop and the plan

As in Session 4, `TinyAgent` takes a planner. `TinyAgent.steps()` keeps going until the
model answers, for up to the planner's `max_steps` LLM calls per message (20 here; a
lecture question takes about 4: load the skill, search, read, answer). A run that hits
the cap stops with a note under the chat, and carries on when the student sends another
message. That replaces Session 3's **Continue** button.

The planner is `NativePlanAndSolve`, unchanged from the notebook: it adds `update_plan`
and `mark_done` to the tools and a *Planning* section to the system prompt. The plan
comes back in every tool result, so the model sees what's done and what's left, and the
chat shows it as those tools' steps.

Where the tutor is told to plan matters with `gpt-5.4-nano`. On 3 runs each of three
multi-part requests (a catch-up on a missed session, a comparison across two sessions, a
review sheet for two sessions), the notebook's *Planning* prompt alone made 0 plans in
9, and the same rule added to `TUTOR.md` 1 in 7 (an API timeout cut that batch short):
once `load_skill` returns the **lecture-videos** steps, the model follows them. With
planning as the skill's first step, it planned 5 of 9 (the review sheet 3/3, the
comparison 2/3, the catch-up 0/3), and never for a single question or "Hi!" (0 of 6).
Its bookkeeping is loose, as the notebook warns for small models: it often marks tasks
done in a batch at the end, or skips some. A review sheet with a plan took 11 to 13
steps, and one run in 3 hit the earlier cap of 15, hence 20.

### The chat

From Session 3's `ChatUI`: tool steps shown as action and observation (click to open),
token counts on each step, **Compact** (and auto-compaction past 75% of
the context budget), attached files, the time on each message, **Clear** keeping the
system prompt. Each browser tab has its own conversation; the student's folder is
shared.

## Notes on the model

- **No Thinking checkbox.** The gpt-5.4 models refuse `reasoning_effort` other than
  `"none"` together with `tools` in `/chat/completions` (HTTP 400, still true on Oct 21),
  and the tutor always has tools. Reasoning with tools would need OpenAI's Responses API.
- **One tool call per step.** Requests set `parallel_tool_calls: false`, because
  `TinyAgent` takes one action per step.
- **Tool results need the call's id.** `Memory` copies it into each `tool` message, as in
  Session 3; OpenAI returns HTTP 400 without it (ollama doesn't check).
- **The context budget is ours, not the model's.** `gpt-5.4-nano` takes 272k prompt
  tokens, but every request re-sends the whole conversation, so cost grows with the
  square of a chat's length. Compacting at 75% of 32k keeps a long chat cheap.
- **Cost.** A lecture question is ~4 requests of 2–6k prompt tokens, mostly cached
  after the first; the course project's data-sharing allowance covers 2.5M small-model
  tokens a day. The chapter index is ~50k embedding tokens, about a tenth of a cent.
