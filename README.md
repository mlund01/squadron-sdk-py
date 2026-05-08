# squadron-sdk (Python)

Python SDK for writing [Squadron](https://github.com/mlund01/squadron) tool
plugins. Wire-compatible with the Go
[`squadron-sdk`](https://github.com/mlund01/squadron-sdk) — a Squadron host
can launch plugins written in either language interchangeably.

## Install

```bash
pip install squadron-sdk
```

## Write a plugin

```python
# src/myplug/main.py
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


def main() -> None:
    app.serve()
```

That's the whole plugin. Schemas, validation, and serialization are all
derived from your type hints via pydantic. Sync and async tool functions
both work. Tool name defaults to the function name, description to the
docstring; override with `@app.tool(name="...", description="...")`.

### Typed returns

Return types are reflected the same way inputs are. Plain `str` returns
pass through unwrapped; everything else (`BaseModel`, dataclasses,
`list[T]`, `dict[K, V]`, …) is JSON-marshaled.

```python
class Item(BaseModel):
    name: str
    count: int

@app.tool
def make_item(name: str) -> Item:
    return Item(name=name, count=3)
# wire: {"name":"x","count":3}

@app.tool
def upper(s: str) -> str:
    return s.upper()
# wire: HI
```

### Splitting tools across files

Use `ToolGroup` to register tools in another module and merge them into the
app. Tools in a group can read app-level state via `group.app`:

```python
# src/myplug/tools/text.py
from squadron_sdk import ToolGroup
text_tools = ToolGroup()

@text_tools.tool
def shout(s: str) -> str:
    return text_tools.app.prefix + s.upper()

# src/myplug/main.py
from squadron_sdk import Squadron
from myplug.tools.text import text_tools

app = Squadron()

@app.configure
def setup(settings):
    app.prefix = settings.get("prefix", "")

app.include(text_tools)              # merge as-is
app.include(text_tools, prefix="t_") # or namespace: t_shout
app.serve()
```

A group can only be included into one app. Importing a shared `app` from
another module also works if you prefer side-effect registration.

### Low-level API

Implement [`ToolProvider`](src/squadron_sdk/interface.py) directly when
tools are fully dynamic (e.g. derived from a remote schema). `Squadron` is
a thin layer over it.

## Use the plugin with Squadron

A Python plugin needs a `pyproject.toml` with one `[project.scripts]`
entry — that script becomes the plugin's spawn entry point.

```toml
[project]
name = "myplug"
version = "0.1.0"
dependencies = ["squadron-sdk>=0.1.1"]

[project.scripts]
myplug = "myplug.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Locally

```bash
squadron plugin build myplug ./path/to/myplug
```

Squadron creates a virtualenv at
`.squadron/plugins/<platform>/myplug/local/venv/`, runs `pip install
<source>`, and writes a `runner.json` pointing at the entry script.
Reference it as `version = "local"` in HCL.

### From a release

Publish a wheel to a GitHub release alongside `checksums.txt`:

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install build
      - run: python -m build --wheel
      - run: cd dist && shasum -a 256 *.whl > checksums.txt
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/*.whl
            dist/checksums.txt
```

Reference it from squadron HCL:

```hcl
plugin "myplug" {
  source  = "github.com/<owner>/<repo>"
  version = "v0.1.0"
  settings = { prefix = "hi: " }
}
```

On first load Squadron downloads the wheel, verifies the sha256 against
`checksums.txt`, and pip-installs it into a venv — same on-disk layout as a
local build.

## License

MIT.
