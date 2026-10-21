"""`tool_to_schema` and `NativeTools` from Session 3.

Two changes:
- A tool that raises returns the error as its observation, so the model can read what
  went wrong and try again, where the notebook would stop.
- A tool can come with its schema already written, as an MCP server's tools do
  (`tutor/mcp.py`), instead of one built from a Python function.
"""

import inspect
import json
from typing import Any, Callable

from .llm import Response

# Convert Python types to JSON schema types
TYPE_MAP = {
    str: "string", int: "integer", float: "number",
    bool: "boolean", list: "array", dict: "object"
}


def tool_to_schema(function: Callable) -> dict:
    """Convert a Python function to an OpenAI-style tool schema."""
    signature = inspect.signature(function)

    # Get function arguments
    properties = {}
    required = []

    for name, parameter in signature.parameters.items():

        # Add the argument by its name. Specify its type.
        properties[name] = {
            "type": TYPE_MAP.get(parameter.annotation, "string")
        }

        # Check if required
        if parameter.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": function.__name__,

            # Pull doc string automatically.
            "description": inspect.getdoc(function),

            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class NativeTools:
    """Tool registry using native function calling."""

    def __init__(self):
        self.registry = {}

    def add_tool(self, name: str, func: Callable, schema: dict | None = None) -> None:
        """Register a tool that the Agent can use (with its schema, if it has one already)."""
        self.registry[name] = {"function": func, "schema": schema}

    @property
    def schemas(self) -> list[dict]:
        """Return tool functions for native function calling."""
        return [
            tool["schema"] or tool_to_schema(tool["function"]) for tool in self.registry.values()
        ]

    @property
    def prompt(self) -> str:
        """Empty because we don't need a prompt for native tool calling"""
        return ""

    def parse(self, response: Response) -> Response:
        """Parse a tool call."""
        # If there's no tool call, return the response as is
        if not response.tool_call:
            return response

        # Extract the tool name and arguments from the tool call
        args = response.tool_call["function"]["arguments"]
        if isinstance(args, str):
            args = json.loads(args) if args.strip() else {}
        tool_call = {
            "tool": response.tool_call["function"]["name"],
            "kwargs": args,
        }

        # Add the parsed tool call to the response
        return Response(
            content=response.content,
            reasoning=response.reasoning,
            tool_call=tool_call,
            metadata=response.metadata,
        )

    def execute(self, response: Response) -> Any:
        """Run a registered tool."""
        tool_call = response.tool_call
        name, kwargs = tool_call["tool"], tool_call.get("kwargs", {})

        if name not in self.registry:
            return f"Tool '{name}' not found."

        # A failed call goes back to the model as the observation
        try:
            return self.registry[name]["function"](**kwargs)
        except Exception as e:
            return f"Error from {name}: {type(e).__name__}: {e}"

    def observation(self, result: str) -> tuple[str, str]:
        """Native tool results use the 'tool' role."""
        return "tool", str(result)

    def is_done(self, response: Response) -> bool:
        """No tool call means the `TinyAgent` is done."""
        return not response.tool_call
