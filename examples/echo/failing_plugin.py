"""Plugin used by tests to verify configure() errors propagate to the host."""
from __future__ import annotations

from squadron_sdk import Squadron

app = Squadron()


@app.configure
def fail(settings: dict[str, str]) -> None:
    raise RuntimeError("boom")


if __name__ == "__main__":
    app.serve()
