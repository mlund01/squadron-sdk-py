"""Unit tests for ToolGroup and Squadron.include — no subprocess needed."""
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from squadron_sdk import Squadron, ToolGroup


class Item(BaseModel):
    name: str
    count: int


def test_tool_group_collects_tools():
    group = ToolGroup()

    @group.tool
    def reverse(s: str) -> str:
        return s[::-1]

    @group.tool(name="upper")
    def upper(s: str) -> str:
        return s.upper()

    assert sorted(group._tools.keys()) == ["reverse", "upper"]


async def test_app_include_merges_group():
    group = ToolGroup()

    @group.tool
    def reverse(s: str) -> str:
        return s[::-1]

    app = Squadron()

    @app.tool
    def echo(s: str) -> str:
        return s

    app.include(group)

    provider = app.as_provider()
    names = sorted(t.name for t in await provider.list_tools())
    assert names == ["echo", "reverse"]

    assert await provider.call("reverse", json.dumps({"s": "abc"})) == "cba"
    assert await provider.call("echo", json.dumps({"s": "hi"})) == "hi"


def test_app_include_with_prefix():
    group = ToolGroup()

    @group.tool
    def thing() -> str:
        return "thing"

    app = Squadron()
    app.include(group, prefix="text_")
    assert "text_thing" in app._tools
    assert "thing" not in app._tools


def test_collision_in_app_include_raises():
    group = ToolGroup()

    @group.tool
    def echo(s: str) -> str:
        return s

    app = Squadron()

    @app.tool
    def echo(s: str) -> str:  # noqa: F811
        return s

    with pytest.raises(ValueError, match="already registered"):
        app.include(group)


async def test_string_return_passes_through_unwrapped():
    app = Squadron()

    @app.tool
    def upper(s: str) -> str:
        return s.upper()

    @app.tool
    def make_item(name: str) -> Item:
        return Item(name=name, count=3)

    provider = app.as_provider()
    assert await provider.call("upper", json.dumps({"s": "hi"})) == "HI"
    assert await provider.call("make_item", json.dumps({"name": "x"})) == '{"name":"x","count":3}'

    upper_info = await provider.get_tool_info("upper")
    assert upper_info.output_schema == {"type": "string"}

    item_info = await provider.get_tool_info("make_item")
    assert item_info.output_schema is not None
    assert item_info.output_schema["properties"]["name"]["type"] == "string"
    assert item_info.output_schema["properties"]["count"]["type"] == "integer"


def test_collision_within_group_raises():
    group = ToolGroup()

    @group.tool
    def f(s: str) -> str:
        return s

    with pytest.raises(ValueError, match="already registered"):

        @group.tool(name="f")
        def g(s: str) -> str:
            return s
