"""Handshake config — must match the Go squadron-sdk."""
from __future__ import annotations

from pyplugin import HandshakeConfig

HANDSHAKE = HandshakeConfig(
    protocol_version=1,
    magic_cookie_key="SQUAD_PLUGIN",
    magic_cookie_value="squadron-tool-plugin-v1",
)
