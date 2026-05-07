"""pyplugin glue: servicer, host-side stub, and the Plugin class."""
from __future__ import annotations

import json
from typing import Any

from grpclib.client import Channel
from pyplugin import Plugin
from pyplugin.broker import GRPCBroker

from ._generated import plugin_grpc, plugin_pb2
from .interface import ToolInfo, ToolProvider


def _info_to_proto(info: ToolInfo) -> plugin_pb2.ToolInfo:
    return plugin_pb2.ToolInfo(
        name=info.name,
        description=info.description,
        schema_json=json.dumps(info.schema or {}),
        output_schema_json=json.dumps(info.output_schema) if info.output_schema else "",
    )


def _info_from_proto(t: plugin_pb2.ToolInfo) -> ToolInfo:
    schema = json.loads(t.schema_json) if t.schema_json else {}
    output_schema = json.loads(t.output_schema_json) if t.output_schema_json else None
    return ToolInfo(
        name=t.name,
        description=t.description,
        schema=schema,
        output_schema=output_schema,
    )


class _ToolPluginServicer(plugin_grpc.ToolPluginBase):
    """Plugin-side servicer that delegates to a ``ToolProvider``."""

    def __init__(self, impl: ToolProvider) -> None:
        self._impl = impl

    async def Configure(self, stream) -> None:
        request = await stream.recv_message()
        try:
            await self._impl.configure(dict(request.settings))
        except Exception as exc:
            await stream.send_message(
                plugin_pb2.ConfigureResponse(success=False, error=str(exc))
            )
            return
        await stream.send_message(plugin_pb2.ConfigureResponse(success=True))

    async def Call(self, stream) -> None:
        request = await stream.recv_message()
        result = await self._impl.call(request.tool_name, request.payload)
        await stream.send_message(plugin_pb2.CallResponse(result=result))

    async def GetToolInfo(self, stream) -> None:
        request = await stream.recv_message()
        info = await self._impl.get_tool_info(request.tool_name)
        await stream.send_message(plugin_pb2.GetToolInfoResponse(tool=_info_to_proto(info)))

    async def ListTools(self, stream) -> None:
        await stream.recv_message()
        tools = await self._impl.list_tools()
        await stream.send_message(
            plugin_pb2.ListToolsResponse(tools=[_info_to_proto(t) for t in tools])
        )


class ToolClient:
    """Host-side wrapper around the generated grpclib stub.

    Returned by ``Client.dispense("tool")``; presents a Pythonic API on top of
    the raw protobuf calls.
    """

    def __init__(self, stub: plugin_grpc.ToolPluginStub) -> None:
        self._stub = stub

    async def configure(self, settings: dict[str, str]) -> None:
        resp = await self._stub.Configure(plugin_pb2.ConfigureRequest(settings=settings))
        if not resp.success:
            raise RuntimeError(f"configure failed: {resp.error}")

    async def call(self, tool_name: str, payload: str) -> str:
        resp = await self._stub.Call(
            plugin_pb2.CallRequest(tool_name=tool_name, payload=payload)
        )
        return resp.result

    async def get_tool_info(self, tool_name: str) -> ToolInfo:
        resp = await self._stub.GetToolInfo(
            plugin_pb2.GetToolInfoRequest(tool_name=tool_name)
        )
        return _info_from_proto(resp.tool)

    async def list_tools(self) -> list[ToolInfo]:
        resp = await self._stub.ListTools(plugin_pb2.ListToolsRequest())
        return [_info_from_proto(t) for t in resp.tools]


class ToolPlugin(Plugin):
    """The pyplugin ``Plugin`` glue for squadron tool plugins.

    On the plugin side, ``servicers()`` is called with the broker and an
    implementation must have been provided to the constructor. On the host
    side, ``stub()`` returns a :class:`ToolClient` wrapping the generated stub.
    """

    def __init__(self, impl: ToolProvider | None = None) -> None:
        self._impl = impl

    def servicers(self, broker: GRPCBroker) -> list:
        if self._impl is None:
            raise RuntimeError(
                "ToolPlugin used as a server but no ToolProvider was supplied"
            )
        return [_ToolPluginServicer(self._impl)]

    def stub(self, broker: GRPCBroker, channel: Channel) -> Any:
        return ToolClient(plugin_grpc.ToolPluginStub(channel))


PLUGIN_KEY = "tool"
