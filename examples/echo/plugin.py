from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from pydantic import Field

from squadron_sdk import Squadron
from tools.text import text_tools

app = Squadron()


@app.configure
def setup(settings: dict[str, str]) -> None:
    app.prefix = settings.get("prefix", "")


@app.tool
async def echo(
    message: str = Field(..., description="Text to echo back."),
    repeat: int = Field(1, ge=1, le=100, description="How many times to repeat."),
) -> dict:
    """Echo a message back, prefixed with the configured prefix."""
    return {"echo": (app.prefix + message) * repeat}


app.include(text_tools)


if __name__ == "__main__":
    app.serve()
