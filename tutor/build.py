"""Put the tutor together: one `TinyAgent` with its instructions, skills and tools."""

from pathlib import Path

from .agent import TinyAgent
from .lectures import Lectures
from .llm import LLM
from .mcp import MCPServer
from .memory import CompactMemory
from .skills import Skills
from .student import Student

ROOT = Path(__file__).resolve().parents[1]


def build_tutor(
    lectures: Lectures | None = None,
    student: Student | None = None,
    model: str | None = None,
    colab: MCPServer | None = None,
) -> TinyAgent:
    """The course tutor.

    - Instructions: `TUTOR.md`, then the student's `MEMORY.md`
    - Skills: the `skills/` folder, loaded with `load_skill`
    - Tools: lecture search, the study log, `remember`, and the Colab MCP server's
      tools if one is running
    - Memory: `CompactMemory`, for the Compact button
    """
    lectures = lectures or Lectures()
    student = student or Student(ROOT / "student")

    # A Skills registry is a NativeTools registry with `load_skill` already in it
    tools = Skills(ROOT / "skills")
    tools.add_tool("search_lectures", lectures.search_lectures)
    tools.add_tool("read_lecture", lectures.read_lecture)
    tools.add_tool("read_log", student.read_log)
    tools.add_tool("log_session", student.log_session)
    tools.add_tool("remember", student.remember)
    if colab:
        colab.register(tools)

    # The same LLM for the agent and its memory
    llm = LLM(model=model) if model else LLM()

    return TinyAgent(
        llm          = llm,
        memory       = CompactMemory(llm),
        tools        = tools,
        instructions = [ROOT / "TUTOR.md", student.memory_file],
    )
