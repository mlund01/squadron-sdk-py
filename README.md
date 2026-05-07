# squadron-sdk (Python)

Python SDK for writing [Squadron](https://github.com/mlund01/squadron) tool
plugins. Wire-compatible with the Go
[`squadron-sdk`](https://github.com/mlund01/squadron-sdk): a host built against
either SDK can launch plugins built against either SDK, in either language.

Built on [pyplugin](https://github.com/mlund01/py-plugin), the byte-for-byte
Python port of HashiCorp's go-plugin (including AutoMTLS with ECDSA P-521).

## Quick start

```python
# plugin.py
from typing import Literal
from pydantic import Field
from squadron_sdk import Squadron

app = Squadron()

@app.configure
def setup(settings: dict[str, str]) -> None:
    app.prefix = settings.get("prefix", "")

@app.tool
async def echo(
    message: str = Field(..., description="Text to echo back."),
    repeat: int = Field(1, ge=1, le=100),
) -> dict:
    """Echo a message back, prefixed with the configured prefix."""
    return {"echo": (app.prefix + message) * repeat}

@app.tool
def reverse(s: str, mode: Literal["chars", "words"] = "chars") -> str:
    """Reverse a string by characters or words."""
    return " ".join(reversed(s.split())) if mode == "words" else s[::-1]

if __name__ == "__main__":
    app.serve()
```

That's the whole plugin. The host gets:

- a `ToolPlugin.ListTools` response with `echo` and `reverse`,
- a JSON Schema derived from your type hints (including `Field(...)` metadata,
  `Literal` enums, defaults, validators, nested pydantic models, …),
- input validation on every `Call`,
- automatic JSON serialization of return values.

Sync and async tool functions both work. Tool name defaults to the function
name and the description defaults to the docstring; override either with
`@app.tool(name="...", description="...")`.

## Typed returns

The return type annotation is reflected into a JSON Schema and shipped as
the tool's `output_schema` — same machinery as the input. Plain `str`
returns pass through unwrapped (the LLM sees `hello` rather than
`"hello"`); everything else is JSON-marshaled via pydantic, so `BaseModel`,
dataclasses, `list[T]`, `dict[K, V]`, `Literal`, etc. all work.

```python
class Item(BaseModel):
    name: str
    count: int

@app.tool
def make_item(name: str) -> Item:
    return Item(name=name, count=3)
# wire: {"name":"x","count":3}
# output_schema: {"type":"object","properties":{"name":{"type":"string"},"count":{"type":"integer"}},"required":["name","count"]}

@app.tool
def upper(s: str) -> str:
    return s.upper()
# wire: HI
# output_schema: {"type":"string"}
```

The output schema flows over the wire and is available to LLM SDKs that
support per-tool output schemas — symmetric with the input schema.

## What gets generated

For the `echo` tool above, the schema sent to the host looks like:

```json
{
  "type": "object",
  "properties": {
    "message": {"type": "string", "description": "Text to echo back."},
    "repeat":  {"type": "integer", "default": 1, "maximum": 100, "minimum": 1}
  },
  "required": ["message"]
}
```

Nested pydantic models, `Literal[...]`, `list[T]`, `dict[K, V]`, `Annotated`,
optional fields with defaults — all the usual pydantic conveniences are
available because we go through `pydantic.create_model` and ship the
schema verbatim.

## Calling from a Python host

```python
import asyncio, sys
from pyplugin import Client, ClientConfig
from squadron_sdk import HANDSHAKE, PLUGIN_KEY, ToolPlugin

async def main():
    async with Client(ClientConfig(
        handshake_config=HANDSHAKE,
        plugins={PLUGIN_KEY: ToolPlugin()},
        cmd=[sys.executable, "plugin.py"],
    )) as client:
        tool = client.dispense(PLUGIN_KEY)
        await tool.configure({"prefix": "hi: "})
        for info in await tool.list_tools():
            print(info.name, info.description)
        print(await tool.call("echo", '{"message":"world"}'))

asyncio.run(main())
```

A complete runnable example lives in [`examples/echo/`](examples/echo/).

## Splitting tools across files

Two patterns work — pick whichever fits.

### Shared app instance

A standalone Python app that owns its own tools: just import the same `app`
everywhere and decorate as you go.

```python
# myplugin/app.py
from squadron_sdk import Squadron
app = Squadron()

# myplugin/tools/database.py
from myplugin.app import app

@app.tool
async def query(sql: str) -> dict: ...

# myplugin/main.py
from myplugin.app import app
from myplugin.tools import database  # registration happens at import time

if __name__ == "__main__":
    app.serve()
```

### Explicit `ToolGroup`

Better when tools are a reusable unit (a library, a swappable bundle, or
just clearly-bounded functionality):

```python
# myplugin/tools/database.py
from squadron_sdk import ToolGroup

db = ToolGroup()
_dsn = ""

@db.configure
def setup(settings):
    global _dsn
    _dsn = settings["dsn"]

@db.tool
async def query(sql: str) -> dict:
    return await run(_dsn, sql)

# myplugin/main.py
from squadron_sdk import Squadron
from myplugin.tools.database import db

app = Squadron()
app.include(db)                  # merge tools and configure handlers
app.include(db, prefix="db_")    # or namespace tools: db_query
app.serve()
```

`ToolGroup` has the same `@tool` and `@configure` decorators as `Squadron`
(no `serve()`). Multiple `@configure` handlers are allowed; on host
configure they all run in registration order. `app.include(group)` chains
the group's handlers into the app, so groups can own their own state and
bootstrap without reaching back to the app. Tool collisions raise on
registration or `include`.

## Low-level API

If you need fully dynamic tools (e.g. discovered at runtime from a remote
schema), implement [`ToolProvider`](src/squadron_sdk/interface.py) directly
and call `serve(provider)`. `Squadron` is a thin layer over `ToolProvider`
that handles the registration plumbing.

## Wire compatibility

Same handshake (`SQUAD_PLUGIN` / `squadron-tool-plugin-v1`, protocol
version 1) and protobuf service (`plugin.ToolPlugin`) as the Go SDK. A Go
Squadron host can launch a Python plugin built with this package, and a
Python host built with `pyplugin` can launch a Go plugin built with the Go
SDK.

The proto file lives at
[`src/squadron_sdk/proto/plugin.proto`](src/squadron_sdk/proto/plugin.proto)
and is identical to the Go SDK's. Regenerate the stubs with:

```bash
python scripts/gen_protos.py
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## License

MIT.
