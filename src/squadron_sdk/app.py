from __future__ import annotations

import inspect
import json
import typing
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import TypeAdapter, create_model

from .interface import ToolInfo, ToolProvider

ConfigureHandler = Callable[[dict[str, str]], None | Awaitable[None]]
ToolFunc = Callable[..., Any]

_ANY_ADAPTER: TypeAdapter[Any] = TypeAdapter(Any)


@dataclass
class _Tool:
    name: str
    description: str
    fn: ToolFunc
    args_model: type
    return_adapter: TypeAdapter[Any]
    return_is_str: bool
    info: ToolInfo

    async def invoke(self, payload: str) -> str:
        params = json.loads(payload) if payload else {}
        validated = self.args_model.model_validate(params)
        kwargs = {k: getattr(validated, k) for k in self.args_model.model_fields}
        result = self.fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        if self.return_is_str and isinstance(result, str):
            return result
        return self.return_adapter.dump_json(result).decode()


def _build_args_model(name: str, fn: ToolFunc) -> type:
    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn, include_extras=True)
    except Exception:
        hints = {}
    fields: dict[str, tuple[Any, Any]] = {}
    for pname, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            raise TypeError(
                f"@tool {name!r}: *args/**kwargs are not supported in tool signatures"
            )
        annotation = hints.get(pname, str)
        default = ... if param.default is inspect.Parameter.empty else param.default
        fields[pname] = (annotation, default)
    return create_model(f"{name}_args", **fields)


def _strip_titles(schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return schema
    out = {k: v for k, v in schema.items() if k != "title"}
    if "properties" in out and isinstance(out["properties"], dict):
        out["properties"] = {k: _strip_titles(v) for k, v in out["properties"].items()}
    if "items" in out:
        out["items"] = _strip_titles(out["items"])
    if "$defs" in out and isinstance(out["$defs"], dict):
        out["$defs"] = {k: _strip_titles(v) for k, v in out["$defs"].items()}
    return out


def _build_tool(
    fn: ToolFunc,
    name: str | None,
    description: str | None,
) -> _Tool:
    tool_name = name or fn.__name__
    doc = (inspect.getdoc(fn) or "").strip()
    tool_desc = description if description is not None else doc.split("\n\n")[0]
    args_model = _build_args_model(tool_name, fn)
    schema = _strip_titles(args_model.model_json_schema())

    return_type, output_schema = _resolve_return_type(fn)
    return_adapter: TypeAdapter[Any] = TypeAdapter(return_type)
    return_is_str = return_type is str

    return _Tool(
        name=tool_name,
        description=tool_desc,
        fn=fn,
        args_model=args_model,
        return_adapter=return_adapter,
        return_is_str=return_is_str,
        info=ToolInfo(
            name=tool_name,
            description=tool_desc,
            schema=schema,
            output_schema=output_schema,
        ),
    )


def _resolve_return_type(fn: ToolFunc) -> tuple[Any, dict[str, Any] | None]:
    try:
        hints = typing.get_type_hints(fn, include_extras=True)
    except Exception:
        return Any, None
    rt = hints.get("return", Any)
    if rt is None or rt is type(None):
        return type(None), None
    if rt is Any or rt is inspect.Signature.empty:
        return Any, None
    try:
        adapter = TypeAdapter(rt)
        schema = _strip_titles(adapter.json_schema())
        return rt, schema
    except Exception:
        return rt, None


class _ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, _Tool] = {}

    def tool(
        self,
        fn: ToolFunc | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> ToolFunc:
        def decorator(f: ToolFunc) -> ToolFunc:
            built = _build_tool(f, name, description)
            if built.name in self._tools:
                raise ValueError(f"tool {built.name!r} is already registered")
            self._tools[built.name] = built
            return f

        if fn is not None and callable(fn):
            return decorator(fn)
        return decorator  # type: ignore[return-value]


class ToolGroup(_ToolRegistry):
    pass


class Squadron(_ToolRegistry):
    def __init__(self) -> None:
        super().__init__()
        self._configure_handler: ConfigureHandler | None = None

    def configure(self, fn: ConfigureHandler) -> ConfigureHandler:
        self._configure_handler = fn
        return fn

    def include(self, group: ToolGroup, *, prefix: str = "") -> None:
        for tool in group._tools.values():
            full_name = f"{prefix}{tool.name}"
            if full_name in self._tools:
                raise ValueError(f"tool {full_name!r} is already registered")
            if prefix:
                self._tools[full_name] = _Tool(
                    name=full_name,
                    description=tool.description,
                    fn=tool.fn,
                    args_model=tool.args_model,
                    return_adapter=tool.return_adapter,
                    return_is_str=tool.return_is_str,
                    info=ToolInfo(
                        name=full_name,
                        description=tool.description,
                        schema=tool.info.schema,
                        output_schema=tool.info.output_schema,
                    ),
                )
            else:
                self._tools[full_name] = tool

    def as_provider(self) -> ToolProvider:
        return _SquadronProvider(self)

    def serve(self) -> None:
        from .server import serve

        serve(self.as_provider())


class _SquadronProvider(ToolProvider):
    def __init__(self, app: Squadron) -> None:
        self._app = app

    async def configure(self, settings: dict[str, str]) -> None:
        handler = self._app._configure_handler
        if handler is None:
            return
        result = handler(settings)
        if inspect.isawaitable(result):
            await result

    async def call(self, tool_name: str, payload: str) -> str:
        tool = self._app._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"unknown tool: {tool_name!r}")
        return await tool.invoke(payload)

    async def get_tool_info(self, tool_name: str) -> ToolInfo:
        tool = self._app._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"unknown tool: {tool_name!r}")
        return tool.info

    async def list_tools(self) -> list[ToolInfo]:
        return [t.info for t in self._app._tools.values()]
