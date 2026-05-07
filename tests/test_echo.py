"""End-to-end smoke tests: host process launches plugin subprocesses."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pyplugin import Client, ClientConfig

from squadron_sdk import HANDSHAKE, PLUGIN_KEY, ToolPlugin

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "echo"


def _client(plugin_path: Path) -> Client:
    return Client(ClientConfig(
        handshake_config=HANDSHAKE,
        plugins={PLUGIN_KEY: ToolPlugin()},
        cmd=[sys.executable, str(plugin_path)],
    ))


async def test_decorator_plugin_roundtrip():
    async with _client(EXAMPLES / "plugin.py") as client:
        tool = client.dispense(PLUGIN_KEY)
        await tool.configure({"prefix": "got: "})

        names = sorted(t.name for t in await tool.list_tools())
        assert names == ["count", "echo", "reverse"]

        echo_info = await tool.get_tool_info("echo")
        assert echo_info.schema["properties"]["message"]["type"] == "string"
        assert echo_info.schema["properties"]["repeat"]["type"] == "integer"
        assert "message" in echo_info.schema["required"]

        result = await tool.call("echo", json.dumps({"message": "hi", "repeat": 3}))
        assert json.loads(result) == {"echo": "got: higot: higot: hi"}

        result = await tool.call("count", json.dumps({"text": "the quick brown fox"}))
        assert json.loads(result) == {"letters": 16, "words": 4}

        result = await tool.call("reverse", json.dumps({"s": "hello world", "mode": "words"}))
        assert result == "got: world hello"

        reverse_info = await tool.get_tool_info("reverse")
        assert reverse_info.output_schema == {"type": "string"}


async def test_validation_error_surfaces_to_host():
    """Invalid args should raise on the plugin side and reach the host as an error."""
    async with _client(EXAMPLES / "plugin.py") as client:
        tool = client.dispense(PLUGIN_KEY)
        with pytest.raises(Exception):
            await tool.call("echo", json.dumps({"message": "hi", "repeat": 999}))


async def test_unknown_tool_raises():
    async with _client(EXAMPLES / "plugin.py") as client:
        tool = client.dispense(PLUGIN_KEY)
        with pytest.raises(Exception):
            await tool.call("does_not_exist", "{}")


async def test_configure_failure_surfaces_error():
    async with _client(EXAMPLES / "failing_plugin.py") as client:
        tool = client.dispense(PLUGIN_KEY)
        with pytest.raises(RuntimeError, match="boom"):
            await tool.configure({})
