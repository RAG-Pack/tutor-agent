# tutor-agent

A course tutor for RAG Pack's *Introduction to Agents*. It's the `TinyAgent` from
Session 3's notebook (*Memory and Tools*), moved into `.py` files and given:

- a **`TUTOR.md`**, always in the system prompt, with the tutor's persona and guidance
  (the way Claude Code always loads `CLAUDE.md`);
- **skills** in a `skills/` folder, discovered progressively;
- **lecture video search**: the session recordings split into chapters, so the tutor can
  answer "what did Josh say about GRPO?" and send the student to the right minute;
- **Colab lessons** over MCP: Google's Colab MCP server lets the tutor build a short
  notebook in the student's browser, with explanations and example cells it has run to
  check, and an exercise to finish;
- a **student memory** (`MEMORY.md`) and the **study log** from Sessions 2 and 3;
- **the loop** from Session 4, so a question can take several tool calls;
- a **Gradio** chat in place of the notebook's `ChatUI`.

It runs on OpenAI's `gpt-5.4-nano`, the smallest and cheapest model from the Oct 6 tests:
2–4 s per turn, about a cent for a 10-question chat.

## Run it

```bash
uv sync
export OPENAI_API_KEY=...        # or have OPENAI_AGENTS_COURSE set, as in env.sh
uv run tutor                     # http://localhost:7860
```

The app starts Google's Colab MCP server alongside it (with `uvx`, a few seconds), and
the Colab notebook opens in the default browser of the computer running the app, so
that browser needs a Google sign-in. `uv run tutor --no-colab` leaves Colab out.

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
| `skills/` | `lecture-videos`, `quiz`, `study-log`, `colab-lesson`: one folder each, with a `SKILL.md` |
| `tutor/llm.py` | `LLM` and `EmbeddingModel` (Session 3's, pointed at OpenAI) |
| `tutor/memory.py` | `Memory` and `CompactMemory` (Session 3's) |
| `tutor/tools.py` | `tool_to_schema` and `NativeTools` (Session 3's) |
| `tutor/skills.py` | `Skills`: a `NativeTools` with the `load_skill` tool and the skills list |
| `tutor/agent.py` | `Trajectory` and `TinyAgent`, with the system prompt from files and the loop |
| `tutor/lectures.py` | The chapters, their embeddings, `search_lectures` and `read_lecture` |
| `tutor/student.py` | `MEMORY.md` and the study log: `remember`, `read_log`, `log_session` |
| `tutor/mcp.py` | A minimal MCP client (JSON-RPC over stdio) and `MCPServer`, which puts a server's tools in the registry |
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
   ships the results in `data/chapters/` (Session 1: 35 chapters, Session 2: 28).
2. **Index.** Each chapter gets two embeddings (OpenAI `text-embedding-3-small`): its
   title and summary, and its transcript. A chapter's score is the better of the two. On
   16 test questions the title-and-summary embedding put the right chapter first 15
   times, the transcript alone 12 times (a whole chapter's talk dilutes its topic). The
   index builds itself on first use and whenever the chapters change.
3. **Tools.** `search_lectures(query, session)` returns the 4 best chapters (times,
   speaker, summary); `read_lecture(session, chapter)` returns that chapter's
   transcript with a time every ~30 seconds. The `lecture-videos` skill says how to
   answer: explain it the instructor's way, then give the time and the recording's page.
   The course site has no links to a time in a video, so the tutor says "open this page
   and skip to 22:09".

**Adding a session's recording:** follow `sessions/lecture-chapters/CHAPTERS.md` in
the course repo, with this repo checked out beside it. It puts the captions in
`data/transcripts/`, the session in `data/sessions.json` and the chapters in
`data/chapters/`, here; the index rebuilds on the next start.

### Colab lessons over MCP

Ask for a notebook ("Build me a Colab notebook that shows how message history works"),
or say yes when the tutor offers one, and the **colab-lesson** skill takes over:

1. **Connect.** `open_colab_browser_connection` opens a scratch Colab notebook in a new
   browser tab and waits up to 60 s for it to connect back; the chat says so while it
   waits. Once connected, the server's tool list changes to Colab's notebook tools
   (`add_text_cell`, `add_code_cell`, `run_code_cell`, `get_cells`, `update_cell`,
   `move_cell`, `delete_cell`), and the tutor sees them on its next step.
2. **Build.** Three short steps, each a text cell and a code cell, appended after the
   notebook's existing cells. The tutor runs each code cell and fixes any error, so the
   examples work when the student gets them. Ideas about the harness use a stand-in
   function for the model, so the cells run in seconds with no model or key.
3. **Hand over.** A `### Try it` cell and a starter code cell with a `# TODO`, left
   unrun, then a few lines in the chat. The tutor can read the student's attempt with
   `get_cells` and give feedback.

`tutor/mcp.py` is the client: Session 3B's mini client as a class. It starts the server
once and keeps it running, because the server holds the browser connection (the book's
`MCPTools` starts a fresh server for every call). It answers the server's pings,
re-lists tools when the server says they changed, and trims results for the model
(plots become `"(an image)"`, terminal colors go). `NativeTools.add_tool` now takes a
ready-made schema, since MCP tools arrive with their JSON Schema. One server is shared
by every chat in the app, so they share one notebook.

Tested live on Oct 21 (Chris's Mac and browser, colab-mcp `b9ab389`), four lessons:
- The tab connected on the first call each time; a second lesson in the same app reused
  the connection, with no new tab.
- In the two command-line runs, all 9 cells the tutor ran came back without an error.
- The exercise's `# TODO` starter cell made it into 1 of the 3 complete lessons; the
  other two stopped at the `### Try it` text.
- Lesson content is only as accurate as the model's idea of the course: asked about
  `CompactMemory`, it kept the last few messages plus a summary, where the course's
  version replaces the whole conversation. The tutor can't read the course's code yet.

### The loop

Session 3's `TinyAgent` stops at the observation, and **Continue** sends it back. Here
`TinyAgent.steps()` keeps going until the model answers, for up to **Max steps** LLM
calls per message (default 25: a lecture question takes about 4 steps, a Colab lesson
about 15). Set it to 1 for Session 3's behavior, and step through with **Continue**.

### The chat

From Session 3's `ChatUI`: tool steps shown as action and observation (click to open),
token counts on each step, **Continue**, **Compact** (and auto-compaction past 75% of
the context budget), attached files, the time on each message, **Clear** keeping the
system prompt. While a step runs, the chat says what it's waiting on (the model, or
which tool, and for the Colab connection what the student needs to do). Each browser tab
has its own conversation; the student's folder and the Colab notebook are shared.

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
