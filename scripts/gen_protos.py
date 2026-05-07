#!/usr/bin/env python3
"""Generate Python protobuf + grpclib stubs for squadron-sdk."""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "src" / "squadron_sdk" / "proto"
OUT_DIR = ROOT / "src" / "squadron_sdk" / "_generated"


def rewrite_imports(out: pathlib.Path) -> None:
    pat = re.compile(r"^import (\w+_pb2)( as .+)?$", re.M)
    for py in list(out.glob("*_grpc.py")) + list(out.glob("*_pb2.py")):
        text = py.read_text()
        new = pat.sub(lambda m: f"from . import {m.group(1)}{m.group(2) or ''}", text)
        if new != text:
            py.write_text(new)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plugin_path = shutil.which("protoc-gen-grpclib_python")
    if not plugin_path:
        venv_bin = ROOT / ".venv" / "bin" / "protoc-gen-grpclib_python"
        if venv_bin.exists():
            plugin_path = str(venv_bin)
    if not plugin_path:
        sys.exit("protoc-gen-grpclib_python not found; pip install grpclib[protobuf]")

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUT_DIR}",
        f"--grpclib_python_out={OUT_DIR}",
        f"--plugin=protoc-gen-grpclib_python={plugin_path}",
        str(PROTO_DIR / "plugin.proto"),
    ]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)
    rewrite_imports(OUT_DIR)
    (OUT_DIR / "__init__.py").write_text("")


if __name__ == "__main__":
    main()
