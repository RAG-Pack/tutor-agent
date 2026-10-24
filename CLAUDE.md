# CLAUDE.md

A course tutor agent for RAG Pack's *Introduction to Agents* (Oct 14–31, 2026). The
code is the `TinyAgent` from the course's Session 4 notebook (*Planning*, in
`chrisjmccormick/An-Illustrated-Guide-To-AI-Agents`, `sessions/session4_planning.md`),
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

- `data/chapters/session<N>.json` is written by an agent following
  `lecture-chapters/CHAPTERS.md` in the course repo (`RAG-Pack/intro-to-agents`,
  checked out beside this one), whose `check_chapters.py <N>` checks the chapters
  against `data/transcripts/`. This repo ships the results, and the course repo keeps
  the tools.
- `data/lecture_index.npz` rebuilds itself when the chapters change, and git ignores it.
- `student/` is one student's memory and log, and git ignores it; the example student
  lives in `examples/student/`.

## Prompts

`TUTOR.md`, the `SKILL.md` files and tool docstrings are prompts. Write them in the
positive, saying what to do and what it gets the student, and keep `TUTOR.md`'s session
table current as the course goes on.
