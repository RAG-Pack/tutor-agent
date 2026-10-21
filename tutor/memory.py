"""`Memory` and `CompactMemory` from Session 3, unchanged."""

from .llm import LLM, Response


class Memory:
    """Simple memory module to store conversation history."""

    def __init__(self):
        self.messages = []

    def add(
        self, role: str, content: str, tool_call: dict | None = None, **kwargs
    ) -> None:
        """Add a message to memory."""
        message = {"role": role, "content": content}

        # Tool call
        if tool_call:
            message["tool_calls"] = [tool_call]

        # Tool result: which call it answers (OpenAI requires this; ollama doesn't check)
        if role == "tool":
            message["tool_call_id"] = self.messages[-1]["tool_calls"][0]["id"]

        # Append message to memory
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        """Get all messages."""
        return self.messages


class CompactMemory(Memory):
    """Memory that can compact the conversation into a summary."""

    PROMPT = """Summarize our conversation so far. Your summary will replace it, \
and we'll continue from the summary alone, so include:

- What the user is working on, and what they want from you
- What they've told you about themselves
- Decisions made, and results found (including from tools)
- Any open question, and what was about to happen next

Reply with just the bullet points, and leave out greetings and small talk."""

    def __init__(self, llm: LLM):
        super().__init__()
        self.llm = llm

    def compact(self) -> Response:
        """Replace the conversation with a summary of it."""

        # 1. Ask for the summary, as one more user message
        request = {"role": "user", "content": self.PROMPT}
        response = self.llm.generate(self.messages + [request])

        # 2. An empty summary would lose the conversation, so keep it as it is
        if not (response.content or "").strip():
            return response

        # 3. Keep the system prompt. The summary replaces the rest.
        system = [message for message in self.messages if message["role"] == "system"]
        summary = "Summary of our conversation so far:\n\n" + response.content
        self.messages = system + [{"role": "user", "content": summary}]

        return response
