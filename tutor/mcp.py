"""MCP: another program's tools, in our tool registry.

An MCP server is a program that lists tools and runs them for us. We start it as a
subprocess and talk JSON-RPC over its stdin and stdout, one JSON message per line,
as in Session 3B's mini client:

    -> {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": ..., "arguments": {...}}}
    <- {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "..."}]}}

The book's `MCPTools` (Ch. 5) starts a fresh server for every call. That can't work for
Colab: the server holds the connection to a browser tab, so it has to stay running.

**The Colab server** (google's `colab-mcp`) starts with one tool,
`open_colab_browser_connection`, which opens a scratch notebook in a new browser tab
and waits up to 60 s for that tab to connect back to it. Once it has, the server says
its tools changed (`notifications/tools/list_changed`), and lists the notebook tools
that the Colab page itself provides: `add_text_cell`, `add_code_cell`, `run_code_cell`,
`get_cells`, `update_cell`, `move_cell` and `delete_cell`. `MCPServer` re-lists them
when that happens, so the model sees the new tools on its next step.
"""

import json
import queue
import re
import subprocess
import threading

from .tools import NativeTools

# Google's Colab MCP server, at the commit tested in Session 3B (Oct 19)
COLAB_MCP = ["uvx", "git+https://github.com/googlecolab/colab-mcp@b9ab389"]

# Longest tool result the model sees, in characters
MAX_RESULT_CHARS = 8_000


class MCPClient:
    """JSON-RPC over a subprocess's stdin and stdout."""

    def __init__(self, command: list[str]):
        self.process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        self.inbox = queue.Queue()
        self.next_id = 0
        self.lock = threading.Lock()   # one request at a time
        self.tools_changed = False     # set by the server's notification

        # A thread reads every line the server writes, so replies wait in the inbox
        threading.Thread(target=self._read, daemon=True).start()

        # The handshake: what protocol we speak, then "ready"
        self.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "tutor-agent", "version": "0.1"},
        }, timeout=180)  # uvx may download the server the first time
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _read(self):
        for line in self.process.stdout:
            if line.strip():
                self.inbox.put(json.loads(line))

    def _send(self, message: dict):
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict | None = None, timeout: float = 120) -> dict:
        """Send a request and wait for its reply, handling anything that arrives meanwhile."""
        with self.lock:
            self.next_id += 1
            request_id = self.next_id
            message = {"jsonrpc": "2.0", "id": request_id, "method": method}
            if params is not None:
                message["params"] = params
            self._send(message)

            while True:
                try:
                    reply = self.inbox.get(timeout=timeout)
                except queue.Empty:
                    raise TimeoutError(f"No reply to {method} after {timeout:.0f} s")

                # The server checking we're alive
                if reply.get("method") == "ping" and "id" in reply:
                    self._send({"jsonrpc": "2.0", "id": reply["id"], "result": {}})

                # The server's tools changed: re-list them after this call
                elif reply.get("method") == "notifications/tools/list_changed":
                    self.tools_changed = True

                # Our reply
                elif reply.get("id") == request_id and "method" not in reply:
                    if "error" in reply:
                        raise RuntimeError(f"{method}: {reply['error'].get('message')}")
                    return reply["result"]

    def list_tools(self) -> list[dict]:
        self.tools_changed = False
        return self.request("tools/list")["tools"]

    def call_tool(self, name: str, arguments: dict, timeout: float = 300) -> str:
        """Run a tool; return its text content."""
        result = self.request("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
        text = "\n".join(item.get("text", "") for item in result.get("content", []))
        return f"Error: {text}" if result.get("isError") else text

    def close(self):
        self.process.terminate()


def _shorten(text: str) -> str:
    """Keep a tool result readable for the model: no images, no terminal colors, a length cap."""
    # A plot comes back as base64 PNG, thousands of tokens of noise
    text = re.sub(r'"(image/[a-z+]+)": ?"[A-Za-z0-9+/=\\n]{200,}"', r'"\1": "(an image)"', text)
    # Tracebacks carry terminal color codes
    text = re.sub(r"\\u001b\[[0-9;]*m|\x1b\[[0-9;]*m", "", text)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + f"\n... ({len(text) - MAX_RESULT_CHARS:,} more characters)"
    return text


class MCPServer:
    """An MCP server's tools, registered in our tool registries and kept up to date."""

    def __init__(self, command: list[str]):
        self.client = MCPClient(command)
        self.listed = self.client.list_tools()
        self.registries: list[NativeTools] = []

    def register(self, tools: NativeTools) -> None:
        """Add the server's tools to an agent's registry (and keep them current there)."""
        self.registries.append(tools)
        self._sync(tools)

    def _sync(self, tools: NativeTools) -> None:
        # Drop tools the server no longer has
        current = {tool["name"] for tool in self.listed}
        for name in [n for n, entry in tools.registry.items() if entry.get("server") is self and n not in current]:
            del tools.registry[name]

        for tool in self.listed:
            # MCP tools come with their JSON Schema; OpenAI's format wraps it
            schema = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema") or {"type": "object", "properties": {}},
                },
            }
            tools.add_tool(tool["name"], self._caller(tool["name"]), schema=schema)
            tools.registry[tool["name"]]["server"] = self

    def _caller(self, name: str):
        def call(**kwargs) -> str:
            result = self.client.call_tool(name, kwargs)

            # The tool list changed (Colab connected): every agent gets the new tools
            if self.client.tools_changed:
                self.listed = self.client.list_tools()
                for tools in self.registries:
                    self._sync(tools)
            return _shorten(result)
        return call

    def close(self):
        self.client.close()
