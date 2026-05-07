from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolInfo:
    name: str
    description: str = ""
    schema: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    output_schema: dict[str, Any] | None = None


class ToolProvider(abc.ABC):
    @abc.abstractmethod
    async def configure(self, settings: dict[str, str]) -> None: ...

    @abc.abstractmethod
    async def call(self, tool_name: str, payload: str) -> str: ...

    @abc.abstractmethod
    async def get_tool_info(self, tool_name: str) -> ToolInfo: ...

    @abc.abstractmethod
    async def list_tools(self) -> list[ToolInfo]: ...
