"""The tutor's chat: Session 3's `ChatUI`, as a Gradio web app.

From Session 3's `ChatUI`:
- Each tool step shows as an action and its observation (click to open), with tokens
- **Continue**: one more step, when a run stopped before an answer (the step limit,
  or an empty reply)
- **Compact**: `CompactMemory` summarizes the conversation, and does it on its own
  past 75% of the context budget
- Attach files to a message, and the date and time on each message
- **Clear** keeps the system prompt

New:
- The loop: up to **Max steps** LLM calls per message (1 is Session 3's agent)
- The system prompt comes from `TUTOR.md` and the student's `MEMORY.md`, so there's
  no System field
- Tabs for what the model sees (system prompt, messages, tool schemas) and for the
  student (memory, study log)

Not carried over: the **Thinking** checkbox. The gpt-5.4 models refuse reasoning
together with tools in /chat/completions, and the tutor always has tools.

    uv run tutor               # http://localhost:7860
    uv run tutor --share       # plus a public link, for a phone or a friend
"""

import argparse
import html
import os
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import gradio as gr

from .agent import Step, TinyAgent
from .build import build_tutor
from .lectures import Lectures
from .student import Student

ROOT = Path(__file__).resolve().parents[1]

# Marks where each attached file starts, in a user message
ATTACHED = "\n\nAttached file: "

# The model takes 272k tokens, but every request re-sends the whole conversation, so
# a chat's cost grows with the square of its length. Compact well before that.
CONTEXT_BUDGET = int(os.environ.get("TUTOR_CONTEXT", 32_000))
AUTO_COMPACT = 0.75

EXAMPLES = [
    "What was the headlight analogy in Session 1?",
    "Why does the model forget my name between messages?",
    "Quiz me on Session 2.",
    "What have I studied so far?",
    "Log this session.",
]


@dataclass
class Chat:
    """One browser tab's conversation: the agent, plus what only the chat shows."""
    agent: TinyAgent
    compactions: list = field(default_factory=list)  # (runs before it, markdown)
    notice: str = ""                                  # an error or hint, under the chat
    used: int = 0                                     # context used by the last call


# Loaded once, shared by every tab
LECTURES: Lectures | None = None
STUDENT: Student | None = None


def new_chat() -> Chat:
    return Chat(agent=build_tutor(lectures=LECTURES, student=STUDENT))


# ---- Drawing the chat --------------------------------------------------------

def _quote(text: str) -> str:
    """Text as a markdown block quote."""
    return "\n".join(f"> {line}" if line.strip() else ">" for line in text.split("\n"))


def _tokens(metadata: dict | None) -> str:
    """Token counts, from a step's metadata."""
    if not metadata:
        return ""
    cached = f" ({metadata['cached_tokens']:,} cached)" if metadata.get("cached_tokens") else ""
    return f"{metadata['prompt_tokens']:,} prompt{cached} · {metadata['completion_tokens']:,} completion tokens"


def _user_message(text: str) -> dict:
    # The time goes above the message, and attached files show by name
    time = ""
    if text.startswith("["):
        time, _, text = text[1:].partition("] ")
    text, *attachments = text.split(ATTACHED)
    for attachment in attachments:
        name, contents = attachment.split("\n", 1)
        n_lines = len(contents.split("\n")) - 2  # minus the ---- lines
        text += f"\n\n📎 `{name}` ({n_lines:,} lines)"
    return {"role": "user", "content": f"<sub>{time}</sub>\n\n{text}" if time else text}


def _tool_message(step: Step) -> dict:
    """An action (the tool call) and its observation (the result), folded."""
    args = ", ".join(f"{key}={value!r}" for key, value in step.action["kwargs"].items())
    return {
        "role": "assistant",
        "content": _quote(step.observation),
        "metadata": {"title": f"🔧 {step.action['tool']}({args})", "log": _tokens(step.metadata), "status": "done"},
    }


def _answer_message(step: Step) -> dict:
    answer = step.answer if step.answer.strip() else "*(empty reply)*"
    return {"role": "assistant", "content": f"{answer}\n\n<sub>{_tokens(step.metadata)}</sub>"}


def _pending(agent: TinyAgent) -> str | None:
    """Is a reply still to come? 'tool' after a tool call, 'empty' after an empty reply."""
    runs = agent.trajectory.runs
    if not (runs and runs[-1]["steps"]):
        return None
    step = runs[-1]["steps"][-1]
    if step.action is not None:
        return "tool"
    if not (step.answer or "").strip():
        return "empty"
    return None


def chat_messages(chat: Chat, working: str = "") -> list[dict]:
    """The trajectory as chat messages: each run's query, then its steps."""
    messages = []
    for i, run in enumerate(chat.agent.trajectory.runs, start=1):
        messages.append(_user_message(run["query"]))
        for step in run["steps"]:
            messages.append(_tool_message(step) if step.action is not None else _answer_message(step))
        for after, card in chat.compactions:
            if after == i:
                messages.append({"role": "assistant", "content": card,
                                 "metadata": {"title": "🗜️ Compacted", "status": "done"}})

    # A step in progress
    if working:
        messages.append({"role": "assistant", "content": "", "metadata": {"title": working, "status": "pending"}})
    return messages


def context_bar(used: int) -> str:
    """The context used by the last call, as a bar colored by how full it is."""
    fraction = min(used / CONTEXT_BUDGET, 1.0)
    color = "#dc2626" if fraction > 0.9 else "#d97706" if fraction > AUTO_COMPACT else "#16a34a"
    return (
        f'<div style="font-size:0.85em">Context: {used:,} / {CONTEXT_BUDGET:,} tokens '
        f'(compacts at {AUTO_COMPACT:.0%})</div>'
        f'<div style="background:#e5e7eb;border-radius:4px;height:8px">'
        f'<div style="background:{color};width:{fraction:.1%};height:8px;border-radius:4px"></div></div>'
    )


def _error(e: Exception) -> str:
    """The error, with the server's explanation if it sent one."""
    message = f"{type(e).__name__}: {e}"
    # An HTTP error's body says what the server objected to
    if isinstance(e, urllib.error.HTTPError):
        message += "\n\n" + e.read().decode(errors="replace")
    return f"**Error**\n\n```\n{message}\n```"


def views(chat: Chat, working: str = "") -> list:
    """Everything on the page that shows the chat's state."""
    agent = chat.agent
    hints = {
        "tool": "🔧 The tutor used all its steps without answering. Click **Continue** for more, or send a new message.",
        "empty": "The reply came back empty. Click **Continue** to let it try again.",
    }
    pending = None if working else _pending(agent)
    notice = chat.notice or hints.get(pending, "")
    return [
        chat,
        chat_messages(chat, working),
        notice,
        context_bar(chat.used),
        gr.update(interactive=pending is not None and not working),
        agent.trajectory.system_prompt or "",
        agent.memory.get_messages(),
        agent.tools.schemas,
        STUDENT.memory_file.read_text(encoding="utf-8") if STUDENT.memory_file.exists() else "",
        STUDENT.log_rows()[1:],
    ]


# ---- Running the agent -------------------------------------------------------

def _run(chat: Chat, max_steps: int):
    """Step the agent until it answers (or `max_steps`), re-drawing after each step."""
    chat.notice = ""
    try:
        for step in chat.agent.steps(int(max_steps)):
            chat.used = step.metadata["prompt_tokens"] + step.metadata["completion_tokens"]
            working = "" if step.answer is not None else "Thinking..."
            yield views(chat, working)
    except Exception as e:
        chat.notice = _error(e)
        yield views(chat)
        return

    # Nearly out of context: compact on our own, once the tutor has answered
    if chat.used > CONTEXT_BUDGET * AUTO_COMPACT and not _pending(chat.agent):
        yield from _compact(chat, auto=True)
    else:
        yield views(chat)


def _compact(chat: Chat, auto: bool = False):
    """Have CompactMemory summarize the conversation, and show the summary."""
    agent = chat.agent
    n_messages = sum(message["role"] != "system" for message in agent.memory.messages)
    if n_messages == 0:
        chat.notice = "Nothing to compact yet."
        yield views(chat)
        return

    yield views(chat, working="Summarizing the conversation...")
    agent.set_system_prompt()
    try:
        response = agent.memory.compact()
    except Exception as e:
        chat.notice = _error(e)
        yield views(chat)
        return

    if not (response.content or "").strip():
        chat.notice = "The summary came back empty, so the conversation is unchanged. Click **Compact** to try again."
        yield views(chat)
        return

    why = f"The context was over {AUTO_COMPACT:.0%} full. " if auto else ""
    card = (f"*{why}From here on, the model sees this summary in place of the {n_messages} messages before it:*"
            f"\n\n{_quote(response.content)}\n\n<sub>{_tokens(response.metadata)}</sub>")
    chat.compactions.append((len(agent.trajectory.runs), card))

    # What's left in memory, at roughly 4 characters per token (the next message measures it)
    chat.used = sum(len(message["content"] or "") for message in agent.memory.messages) // 4
    yield views(chat)


# ---- Buttons -----------------------------------------------------------------

def on_send(message: dict, chat: Chat | None, max_steps: int):
    chat = chat or new_chat()
    text = (message or {}).get("text", "").strip()
    files = (message or {}).get("files", [])
    if not text and not files:
        yield [gr.update()] + views(chat)
        return

    # The message: the date and time, what you typed, then the attached files
    task = f"[{datetime.now().astimezone():%Y-%m-%d %H:%M %Z}] {text}"
    for path in files:
        path = Path(path if isinstance(path, str) else path["path"])
        task += f"{ATTACHED}{path.name}\n----\n{path.read_text(encoding='utf-8', errors='replace')}\n----"

    chat.agent.start(task)
    # Clear the input (attachments go with one message)
    yield [{"text": "", "files": []}] + views(chat, working="Thinking...")
    for update in _run(chat, max_steps):
        yield [gr.update()] + update


def on_continue(chat: Chat | None, max_steps: int):
    chat = chat or new_chat()
    # After an empty reply, take it back, so the model tries that step again
    messages = chat.agent.memory.messages
    if _pending(chat.agent) == "empty" and messages[-1]["role"] == "assistant":
        messages.pop()
    yield views(chat, working="Thinking...")
    yield from _run(chat, max_steps)


def on_compact(chat: Chat | None):
    yield from _compact(chat or new_chat())


def on_clear(chat: Chat | None):
    chat = chat or new_chat()
    # Keep the system prompt
    chat.agent.memory.messages = [m for m in chat.agent.memory.messages if m["role"] == "system"]
    chat.agent.trajectory.runs = []
    chat.compactions = []
    chat.used = 0
    chat.notice = "Conversation cleared."
    return views(chat)


def on_load(chat: Chat | None):
    return views(chat or new_chat())


# ---- The page ----------------------------------------------------------------

def build_app() -> gr.Blocks:
    with gr.Blocks(title="Course Tutor", fill_height=True) as app:
        chat = gr.State(None)

        gr.Markdown("## 🎓 Course Tutor · *Introduction to Agents*")

        with gr.Tab("Chat"):
            chatbot = gr.Chatbot(
                label="Tutor", height=560, layout="bubble", buttons=["copy"],
                placeholder="Ask about the course, or pick an example below.",
            )
            notice = gr.Markdown()
            textbox = gr.MultimodalTextbox(
                placeholder="Ask the tutor... (📎 attaches a .py or .md file to your message)",
                file_count="multiple", file_types=[".py", ".md", ".txt", ".json", ".ipynb", ".csv", ".tsv"],
                show_label=False,
            )
            with gr.Row(equal_height=True):
                continue_button = gr.Button("Continue", variant="primary", interactive=False, scale=1)
                compact_button = gr.Button("Compact", scale=1)
                clear_button = gr.Button("Clear", variant="stop", scale=1)
                max_steps = gr.Slider(1, 10, value=6, step=1, label="Max steps per message", scale=2)
                context = gr.HTML(context_bar(0))
            gr.Examples([{"text": text, "files": []} for text in EXAMPLES], inputs=textbox, label="Try")

        with gr.Tab("What the model sees"):
            gr.Markdown("The system prompt (`TUTOR.md`, the student's `MEMORY.md`, the skills list), "
                        "re-read before every message:")
            system_view = gr.Code(language="markdown", label="System prompt", wrap_lines=True)
            messages_view = gr.JSON(label="Messages (memory.get_messages())")
            tools_view = gr.JSON(label="Tools (sent with every request)", open=False)

        with gr.Tab("Student"):
            memory_view = gr.Markdown(label="MEMORY.md")
            log_view = gr.Dataframe(headers=["start", "end", "learned"], label="Study log", wrap=True)

        outputs = [chat, chatbot, notice, context, continue_button,
                   system_view, messages_view, tools_view, memory_view, log_view]

        textbox.submit(on_send, [textbox, chat, max_steps], [textbox] + outputs)
        continue_button.click(on_continue, [chat, max_steps], outputs)
        compact_button.click(on_compact, [chat], outputs)
        clear_button.click(on_clear, [chat], outputs)
        app.load(on_load, [chat], outputs)

    return app


def main():
    global LECTURES, STUDENT
    parser = argparse.ArgumentParser(description="Chat with the course tutor.")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true", help="also make a public gradio.live link")
    parser.add_argument("--student", default=str(ROOT / "student"), help="the student's folder (MEMORY.md, study_log.tsv)")
    args = parser.parse_args()

    LECTURES = Lectures()
    STUDENT = Student(args.student)
    build_app().launch(server_port=args.port, share=args.share, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
