from __future__ import annotations

from typing import Literal

from squadron_sdk import ToolGroup

text_tools = ToolGroup()


@text_tools.tool
def reverse(s: str, mode: Literal["chars", "words"] = "chars") -> str:
    """Reverse a string by characters or by words."""
    if mode == "words":
        return " ".join(reversed(s.split()))
    return s[::-1]


@text_tools.tool(name="count")
def count_words(text: str) -> dict:
    """Count letters and words in a string."""
    return {
        "letters": sum(1 for ch in text if ch.isalpha()),
        "words": len(text.split()),
    }
