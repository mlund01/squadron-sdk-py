"""squadron-sdk — Python SDK for writing Squadron tool plugins.

Wire-compatible with the Go ``github.com/mlund01/squadron-sdk`` package: a host
built against either SDK can launch plugins built against either SDK, in either
language.

The high-level API is :class:`Squadron`. Decorate functions with ``@app.tool``;
the JSON Schema is derived from type hints, and arguments are validated by
pydantic. Drop down to :class:`ToolProvider` if you need fully dynamic tools.
"""
from __future__ import annotations

from .app import Squadron, ToolGroup
from .handshake import HANDSHAKE
from .interface import ToolInfo, ToolProvider
from .plugin import PLUGIN_KEY, ToolClient, ToolPlugin
from .server import serve

__all__ = [
    "HANDSHAKE",
    "PLUGIN_KEY",
    "Squadron",
    "ToolClient",
    "ToolGroup",
    "ToolInfo",
    "ToolPlugin",
    "ToolProvider",
    "serve",
]
