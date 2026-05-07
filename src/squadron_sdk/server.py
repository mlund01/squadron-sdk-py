"""Plugin entry point — mirrors squadron-sdk/serve.go."""
from __future__ import annotations

import os
import sys
import threading
import time

from pyplugin import ServeConfig, serve as _pyplugin_serve

from .handshake import HANDSHAKE
from .interface import ToolProvider
from .plugin import PLUGIN_KEY, ToolPlugin


def _monitor_parent() -> None:
    """Exit if the parent process dies, mirroring monitor_unix.go.

    On Unix, a process whose parent dies is reparented to PID 1 (init/launchd).
    Detect that and exit so we don't become an orphan.
    """
    if os.name == "nt":
        return
    initial = os.getppid()
    while True:
        time.sleep(5)
        current = os.getppid()
        if current != initial or current == 1:
            os._exit(0)


def serve(impl: ToolProvider) -> None:
    """Start the plugin server with ``impl`` as the tool provider.

    This is the main entry point for plugin binaries — call it from
    ``if __name__ == "__main__":``.
    """
    threading.Thread(target=_monitor_parent, daemon=True).start()
    _pyplugin_serve(ServeConfig(
        handshake_config=HANDSHAKE,
        plugins={PLUGIN_KEY: ToolPlugin(impl)},
    ))


__all__ = ["serve"]
