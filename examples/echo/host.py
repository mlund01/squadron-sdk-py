"""Sample host that launches the echo plugin and exercises every tool."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from pyplugin import Client, ClientConfig

from squadron_sdk import HANDSHAKE, PLUGIN_KEY, ToolPlugin

PLUGIN_SCRIPT = Path(__file__).resolve().parent / "plugin.py"


async def main() -> None:
    config = ClientConfig(
        handshake_config=HANDSHAKE,
        plugins={PLUGIN_KEY: ToolPlugin()},
        cmd=[sys.executable, str(PLUGIN_SCRIPT)],
    )
    async with Client(config) as client:
        tool = client.dispense(PLUGIN_KEY)
        await tool.configure({"prefix": "[echo] "})

        for info in await tool.list_tools():
            print(f"\n{info.name}: {info.description}")
            print("  schema:", json.dumps(info.schema, indent=2))

        print("\necho:", await tool.call("echo", json.dumps({"message": "hi", "repeat": 2})))
        print("count:", await tool.call("count", json.dumps({"text": "the quick brown fox"})))
        print("reverse:", await tool.call("reverse", json.dumps({"s": "hello world", "mode": "words"})))


if __name__ == "__main__":
    asyncio.run(main())
