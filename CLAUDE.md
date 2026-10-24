# CLAUDE.md

A course tutor agent for RAG Pack's *Introduction to Agents* (Oct 14–31, 2026). The
code is the `TinyAgent` from the course's Session 4 notebook (*Session 4 - Autonomy and
Planning*, in the private course repo `RAG-Pack/intro-to-agents`, `session4/`),
moved into `.py` files. `README.md` explains every piece; read it first.

## Keep the code the course's code

Students meet these classes in the notebooks, so the tutor stays readable next to
them: `LLM`, `Memory`, `CompactMemory`, `NativeTools`, `NativeReAct`,
`NativePlanAndSolve`, `Trajectory` and `TinyAgent` keep the notebook's structure, names, step comments ("# 2. THOUGHT: ...") and plain
`urllib` requests. Add features as small, commented changes to those classes, or as new
modules beside them, and say in the module docstring what changed from Session 3 and
why. That keeps a diff against the notebook short enough to teach from.

`main` is the simple version. Colab lessons over MCP (`tutor/mcp.py`, the
`colab-lesson` skill) live on the `colab-mcp` branch; build bigger features on a
branch like that too, so `main` stays easy to read.

The tutor follows the course one session at a time. When it's caught up to a session,
tag that commit (`git tag -a session-<N>`, pushed) and make a GitHub release from the
tag with a few lines on what's new, so each session's version stays one click away.

## Run and test

- `uv sync`, then `uv run tutor` for the Gradio chat.
- To test without the browser, write a short script in an agent-ops session folder
  (`agent-ops/tutor-agent/<session>/`, laid out per `agent-ops/CONVENTION.md`) and run
  it from this repo's root with `uv run python ../agent-ops/tutor-agent/<session>/test.py`:
  the venv has `tutor` installed, so the script imports it directly. Test scripts and
  their output stay there, beside the results they back, and this repo stays what
  students read. A starting point:
  `agent-ops/tutor-agent/2026-10-23_1000pm_session-4-planning/plan_eval.py` runs each
  prompt on a fresh tutor (with a scratch student) and records every tool call.
- The OpenAI key comes from `OPENAI_AGENTS_COURSE` (Chris's env.sh) or
  `OPENAI_API_KEY`. On the Mac mini, API calls need the sandbox off.
- Check a behavior change against the model, not just by reading the prompt:
  `gpt-5.4-nano` follows instructions loosely, so run each test prompt a few times and
  count (the README's numbers came from 2–3 runs each).

## Data

- This repo is public. The recordings' captions and chapters (`data/transcripts/`,
  `data/chapters/`) name students who spoke in Q&A, so git ignores them: they live in
  the private course repo (`RAG-Pack/intro-to-agents`, checked out beside this one: the
  captions in its `session<N>/` folders, the chapters in `lecture-chapters/chapters/`)
  and reach students as the lecture bundle, `tutor-data.zip`, on Session 3's lesson
  (`BUNDLE_PAGE` in `tutor/lectures.py`). Follow that repo's
  `lecture-chapters/CHAPTERS.md` to add a recording; its `build_bundle.py --install
  ../tutor-agent` fills your `data/` to test. Keep transcripts, chat logs and students'
  names out of this repo's commits, test logs included.
- `data/sessions.json` stays in git: a session listed there whose chapters a student
  lacks makes the lecture tools tell them to download the bundle again.
- `data/lecture_index.npz` rebuilds itself when the chapters change, and git ignores it.
- `student/` is one student's memory and log, and git ignores it; the example student
  lives in `examples/student/`.

## Prompts

`TUTOR.md`, the `SKILL.md` files and tool docstrings are prompts. Write them in the
positive, saying what to do and what it gets the student, and keep `TUTOR.md`'s session
table current as the course goes on.
