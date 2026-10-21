"""Skills: instructions in a folder, which the agent loads only when it needs them.

Each skill is a folder with a `SKILL.md`: YAML frontmatter with a `name` and a
`description`, then the instructions. Progressive discovery loads them in three levels:

1. **Always**: each skill's name and description go in the system prompt (a line each).
2. **When a task matches**: the model calls `load_skill(name)` and gets the instructions.
3. **When the instructions say so**: a skill's other files (examples, templates) load
   the same way, `load_skill(name, file)`.

So a skill costs one line of context until it's used. The book's `Skills` (Ch. 5)
registers each skill as a tool of its own; here one `load_skill` tool serves them all,
and the list lives in the system prompt, as in Claude Code.
"""

from pathlib import Path

from .tools import NativeTools


def _frontmatter(text: str) -> tuple[dict, str]:
    """'---\\nname: x\\n---\\nbody' -> ({'name': 'x'}, 'body')"""
    if not text.startswith("---"):
        return {}, text
    _, header, body = text.split("---", 2)
    fields = {}
    for line in header.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields, body.strip()


class Skills(NativeTools):
    """A tool registry, plus the skills in a folder."""

    def __init__(self, folder: str | Path):
        super().__init__()
        self.folder = Path(folder)
        self.add_tool("load_skill", self.load_skill)

    @property
    def skills(self) -> dict[str, dict]:
        """name -> {'description', 'folder'}, read fresh each time so new skills show up."""
        found = {}
        for path in sorted(self.folder.glob("*/SKILL.md")):
            fields, _ = _frontmatter(path.read_text(encoding="utf-8"))
            name = fields.get("name", path.parent.name)
            found[name] = {"description": fields.get("description", ""), "folder": path.parent}
        return found

    @property
    def prompt(self) -> str:
        """Level 1: the skills' names and descriptions, for the system prompt."""
        skills = self.skills
        if not skills:
            return ""
        lines = [f"- **{name}**: {skill['description']}" for name, skill in skills.items()]
        return (
            "## Skills\n\n"
            "Skills are step-by-step instructions for particular tasks. When a request "
            "matches a skill below, call `load_skill` with its name before anything else, "
            "even when you think you know how: the skill has details you need. Then follow it.\n\n"
            + "\n".join(lines)
        )

    def load_skill(self, name: str, file: str = "SKILL.md") -> str:
        """Load a skill's instructions by its name, before you do a task it covers. Leave out `file` for the skill's instructions (SKILL.md); pass `file` only when those instructions name another of the skill's files to read."""
        skill = self.skills.get(name)
        if skill is None:
            return f"No skill named '{name}'. Skills: {', '.join(self.skills) or 'none'}."

        # Only files inside the skill's own folder
        path = (skill["folder"] / file).resolve()
        if not path.is_relative_to(skill["folder"].resolve()) or not path.is_file():
            others = [p.name for p in skill["folder"].iterdir() if p.is_file()]
            return f"Skill '{name}' has no file '{file}'. Its files: {', '.join(others)}."

        text = path.read_text(encoding="utf-8")

        # Level 2: the instructions, without the frontmatter
        if path.name == "SKILL.md":
            _, text = _frontmatter(text)
        return text
