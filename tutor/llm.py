"""`LLM` and `EmbeddingModel` from Session 3, pointed at OpenAI's API.

Same request and response as the notebook (plain `urllib`, the chat-completions
format). Changes:

- The base URL and key default to OpenAI, with the key from the environment.
- One tool call per reply (`parallel_tool_calls: false`), because `TinyAgent` takes one
  action per step and `Memory` stores one call per assistant message.
- `metadata` keeps the cached-token count too (OpenAI caches a repeated prompt prefix
  and bills it at 10%).
- `EmbeddingModel` sends the key, and splits long lists into batches.

Thinking: the gpt-5.4 models refuse `reasoning_effort` other than `"none"` together
with `tools` in /chat/completions (HTTP 400), so the tutor runs with `think=False`.
"""

import json
import os
import urllib.request
from dataclasses import dataclass

import numpy as np

OPENAI_URL = "https://api.openai.com/v1"

# The smallest, cheapest model from the Oct 6 tests: as good as Gemma 4 E4B on the
# tutor's questions, 2-4 s per turn, ~$0.01 for a 10-question chat
DEFAULT_MODEL = os.environ.get("TUTOR_MODEL", "gpt-5.4-nano")
EMBEDDING_MODEL = "text-embedding-3-small"


def openai_key() -> str:
    """The course project's key from env.sh, or the usual OPENAI_API_KEY."""
    key = os.environ.get("OPENAI_AGENTS_COURSE") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Set OPENAI_API_KEY (or OPENAI_AGENTS_COURSE) to your OpenAI API key.")
    return key


def _post(url: str, body: dict, api_key: str) -> dict:
    """POST a JSON body, return the JSON reply."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


@dataclass
class Response:
    """Structured response from LLM calls."""
    content: str = ""
    reasoning: str = ""
    tool_call: dict | None = None
    metadata: dict | None = None


class LLM:

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = OPENAI_URL,
        api_key: str | None = None,
        think: bool = False,
        temperature: float | None = None,
    ):
        """Initialize the LLM with the given model."""
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or openai_key()
        self.think = think
        self.temperature = temperature

    def generate(
        self,
        messages: list[dict],
        tools: list | None = None,
        format: dict | None = None,
    ) -> Response:
        """Generate a response from the LLM given a list of messages."""

        # Build the request body
        body = {
            "model": self.model,
            "messages": messages,
        }

        # Tool schemas, and at most one call per reply
        if tools:
            body["tools"] = tools
            body["parallel_tool_calls"] = False

        # JSON Schema for the reply (grammar-constrained decoding)
        if format:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "reply", "schema": format},
            }

        # Enable or disable reasoning
        body["reasoning_effort"] = "medium" if self.think else "none"

        if self.temperature is not None:
            body["temperature"] = self.temperature

        # POST to the OpenAI-compatible /chat/completions endpoint
        data = _post(f"{self.base_url}/chat/completions", body, self.api_key)

        # Extract message, tool call and metadata
        message = data["choices"][0]["message"]

        content = message.get("content")
        reasoning = message.get("reasoning") or message.get("reasoning_content")

        # The first tool call, if the model made one
        tool_calls = message.get("tool_calls")
        tool_call = tool_calls[0] if tool_calls else None

        usage = data["usage"]
        metadata = {
            "model": data["model"],
            "prompt_tokens": usage["prompt_tokens"],
            "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
            "completion_tokens": usage["completion_tokens"],
        }

        return Response(
            content   = content,
            reasoning = reasoning,
            tool_call = tool_call,
            metadata  = metadata,
        )


class EmbeddingModel:
    """Generate embeddings."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        base_url: str = OPENAI_URL,
        api_key: str | None = None,
    ):
        """Initialize the embedding model with the given model."""
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or openai_key()

    def embed(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """Convert a list of texts into numerical vectors, one row per text."""
        rows = []
        # POST to the OpenAI-compatible /embeddings endpoint, a batch at a time
        for i in range(0, len(texts), batch_size):
            body = {"model": self.model, "input": texts[i:i + batch_size]}
            response = _post(f"{self.base_url}/embeddings", body, self.api_key)
            rows += [item["embedding"] for item in response["data"]]

        # OpenAI's embeddings have magnitude 1, so a dot product is the cosine similarity
        return np.array(rows, dtype=np.float32)
