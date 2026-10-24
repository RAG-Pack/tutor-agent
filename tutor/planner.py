"""`NativeReAct` and `NativePlanAndSolve` from Session 4.

- `NativeReAct`: with native reasoning and tool calls, ReAct needs no prompt and no
  parsing. What's left is `max_steps`, the cap on LLM calls per message.
- `NativePlanAndSolve`: plan-and-solve as tools. It adds `update_plan` and `mark_done`
  to the registry and a planning section to the system prompt, so the model writes its
  plan, reads it back in every tool result, and checks off each task as it goes.

Unchanged from the notebook.
"""

from .llm import Response
from .tools import NativeTools


class NativeReAct:
    """ReAct using native LLM reasoning and tool calling."""

    def __init__(self, max_steps: int = 10):
        """Initialize ReAct module.

        Arguments:
            max_steps: Maximum number of ReAct steps to perform.
        """
        self.max_steps = max_steps

    @property
    def prompt(self) -> str:
        return ""

    def parse(self, response: Response) -> Response:
        return response


class NativePlanAndSolve(NativeReAct):
    """ReAct planner that gives the LLM tools to create and update its own plan."""

    def __init__(self, tools: NativeTools, max_steps: int = 10):
        """Initialize the planner, and add its tools to the registry.

        Arguments:
            tools: The tool registry to attach `update_plan` and `mark_done` to.
            max_steps: Maximum number of ReAct steps to perform.
        """
        super().__init__(max_steps)
        self.plan: list[dict] = []

        tools.add_tool("update_plan", self.update_plan)
        tools.add_tool("mark_done", self.mark_done)

    @property
    def prompt(self) -> str:
        return (
            "## Planning\n\n"
            "For non-trivial tasks, call `update_plan` first to outline your approach, "
            "then `mark_done` as you complete each sub-task. Revise the plan with "
            "`update_plan` whenever new information changes what is needed.\n"
        )

    def update_plan(self, items: list[str]) -> str:
        """Create or replace the plan: a list of sub-tasks, in order."""
        self.plan = [{"task": item, "done": False} for item in items]
        return f"Plan:\n{self._render()}"

    def mark_done(self, index: int) -> str:
        """Mark a sub-task as done, by its number in the plan (the first sub-task is 1)."""
        if not 1 <= index <= len(self.plan):
            return f"No sub-task {index}: the plan is numbered 1 to {len(self.plan)}."
        self.plan[index - 1]["done"] = True
        return f"Plan:\n{self._render()}"

    def _render(self) -> str:
        return "\n".join(
            f"{'[x]' if item['done'] else '[ ]'} {i + 1}. {item['task']}"
            for i, item in enumerate(self.plan)
        )
