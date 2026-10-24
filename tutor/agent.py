"""`Trajectory` and `TinyAgent` from Session 3, with two additions.

- **The system prompt comes from files**: `TUTOR.md` (the tutor's persona and
  guidance, like Claude Code's `CLAUDE.md`) and the student's `MEMORY.md`, re-read
  before every message so edits take effect, then the tools' prompt (the skills list).
  This replaces the notebook's **System** field, where the student listed files.
- **The loop** (Session 4): Session 3's `TinyAgent` stops at the observation, and the
  **Continue** button sends it back. Here `steps()` keeps going until the model answers,
  for up to `max_steps` LLM calls, so a lecture question can search, read the chapter,
  then answer. With `max_steps=1` it's Session 3's agent again.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .llm import LLM, Response
from .memory import Memory
from .tools import NativeTools


@dataclass
class Step:
    """A single step in an agent's trajectory."""
    thought: str = ""               # The reasoning
    action: dict | None = None      # Tool call
    observation: str | None = None  # Tool result
    answer: str | None = None       # The reply
    metadata: dict | None = None    # Token counts


class Trajectory:
    """Records agent execution as a sequence of runs."""

    def __init__(self) -> None:
        self.runs: list[dict] = []
        self.system_prompt: str | None = None

    def initialize(self, query: str) -> None:
        """Register a new run with the given query."""
        self.runs.append({"query": query, "steps": []})

    def add(self, response: Response, observation: str | None = None) -> Step:
        """Record a step from a Response, optionally with an observation."""
        # Add THOUGHT
        step = Step(
            thought  = response.reasoning or "",
            metadata = response.metadata,
        )

        # Add ACTION/OBSERVATION or ANSWER
        if observation is not None:
            step.action = response.tool_call
            step.observation = observation
        else:
            step.answer = response.content or ""

        self.runs[-1]["steps"].append(step)
        return step


class TinyAgent:
    """A minimal, modular, and educational agent framework."""

    def __init__(
        self,
        llm: LLM,
        memory: Memory,
        tools: NativeTools,
        instructions: list[str | Path] = (),
    ):
        self.llm = llm
        self.memory = memory
        self.tools = tools
        self.instructions = [Path(path) for path in instructions]  # <-- TUTOR.md, MEMORY.md
        self.trajectory = Trajectory()
        self.set_system_prompt()

    def system_prompt(self) -> str:
        """The instruction files, then the tools' prompt (the skills list)."""
        parts = [path.read_text(encoding="utf-8").strip() for path in self.instructions if path.exists()]
        if self.tools.prompt:
            parts.append(self.tools.prompt)
        return "\n\n".join(parts)

    def set_system_prompt(self) -> None:
        """Make the system prompt the first message in memory, re-reading the files."""
        messages = self.memory.messages
        if messages and messages[0]["role"] == "system":
            messages.pop(0)
        prompt = self.system_prompt()
        messages.insert(0, {"role": "system", "content": prompt})
        self.trajectory.system_prompt = prompt

    def run(self, task: str, max_steps: int = 6) -> str:
        """Run the agent on a task: step until it answers, or `max_steps`."""
        self.start(task)
        step = None
        for step in self.steps(max_steps):
            pass
        return step.answer if step.answer is not None else step.observation

    def start(self, task: str) -> None:
        """1. Add the user's message, and start a new run."""
        self.set_system_prompt()
        self.memory.add("user", task)
        self.trajectory.initialize(task)

    def steps(self, max_steps: int = 6) -> Iterator[Step]:
        """The loop: one step at a time, until the model answers."""  # <-- New
        for _ in range(max_steps):
            step = self._step()
            yield step
            if step.answer is not None:
                return

    def _step(self) -> Step:
        """Perform a single step."""

        # 2. THOUGHT: Ask the LLM, with the tools available
        response = self.llm.generate(
            self.memory.get_messages(), tools=self.tools.schemas
        )

        # 3. Add the reply to memory, including any tool call
        self.memory.add(
            "assistant", response.content, tool_call=response.tool_call
        )

        # 4. Tool parsing
        response = self.tools.parse(response)

        # 5. ANSWER: no tool call means we're done
        if self.tools.is_done(response):
            return self.trajectory.add(response)

        # Otherwise, take the action
        return self._execute_action(response)

    def _execute_action(self, response: Response) -> Step:
        """Execute a tool action."""

        # 6. ACTION: execute the tool
        result = self.tools.execute(response)

        # 7. OBSERVATION: add the result to memory, and record the step
        role, observation = self.tools.observation(result)
        self.memory.add(role, observation)
        return self.trajectory.add(response, observation)
