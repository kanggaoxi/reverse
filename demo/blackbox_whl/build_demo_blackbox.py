#!/usr/bin/env python3
"""Build a small local wheel that acts like a black-box DSL compiler.

The produced wheel exposes a CLI named `toycc`. It accepts a tiny pseudo DSL and
emits a `.cce`-like text file plus a small host stub. The compiler intentionally
has quirky auto-padding behavior so agents can reverse engineer it.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


TOYCC_MAIN = r'''from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


HEADER = "# toycc generated pseudo-cce\n"


def parse_shape(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def align_up(value: int, unit: int) -> int:
    return ((value + unit - 1) // unit) * unit


def compile_dsl(src: str) -> dict:
    api = None
    dtype = "fp16"
    shape = None
    notes: list[str] = []
    for line in src.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"api\s*:\s*(\w+)", line)
        if m:
            api = m.group(1)
            continue
        m = re.match(r"dtype\s*:\s*(\w+)", line)
        if m:
            dtype = m.group(1)
            continue
        m = re.match(r"shape\s*:\s*\[(.*?)\]", line)
        if m:
            shape = parse_shape(m.group(1))
            continue
        notes.append(f"UNPARSED:{line}")
    if api is None or shape is None:
        raise SystemExit("toycc: expected api and shape")

    elem_bytes = 2 if dtype == "fp16" else 4
    aligned_32b = shape[-1] * elem_bytes % 32 == 0
    aligned_16 = shape[-1] % 16 == 0
    padded_shape = list(shape)
    transforms: list[str] = []
    if not aligned_32b:
        old = padded_shape[-1]
        padded_shape[-1] = align_up(padded_shape[-1], 16 if elem_bytes == 2 else 8)
        transforms.append(f"pad_last_dim_32b:{old}->{padded_shape[-1]}")
    if api in {"matmulish", "cube_load"} and not aligned_16:
        old = padded_shape[-1]
        padded_shape[-1] = align_up(padded_shape[-1], 16)
        transforms.append(f"pad_last_dim_16x16:{old}->{padded_shape[-1]}")

    pseudo_cce = HEADER
    pseudo_cce += f"api={api}\n"
    pseudo_cce += f"dtype={dtype}\n"
    pseudo_cce += f"input_shape={shape}\n"
    pseudo_cce += f"lowered_shape={padded_shape}\n"
    pseudo_cce += f"transforms={transforms}\n"
    pseudo_cce += f"notes={notes}\n"
    return {
        "api": api,
        "dtype": dtype,
        "input_shape": shape,
        "lowered_shape": padded_shape,
        "transforms": transforms,
        "pseudo_cce": pseudo_cce,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = input_path.read_text(encoding="utf-8")
    result = compile_dsl(src)
    (out_dir / "kernel.cce").write_text(result["pseudo_cce"], encoding="utf-8")
    (out_dir / "host.cpp").write_text(
        "// pseudo host stub\\n"
        f"// api={result['api']}\\n"
        f"// lowered_shape={result['lowered_shape']}\\n",
        encoding="utf-8",
    )
    (out_dir / "compile.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("toycc: success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def dist_info_dir(name: str, version: str) -> str:
    return f"{name.replace('-', '_')}-{version}.dist-info"


def wheel_name(name: str, version: str) -> str:
    return f"{name}-{version}-py3-none-any.whl"


def record_rows(files: list[tuple[str, bytes]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for path, data in files:
        digest = hashlib.sha256(data).digest()
        b64 = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        rows.append([path, f"sha256={b64}", str(len(data))])
    rows.append([f"{dist_info_dir('toycc_demo', '0.1.0')}/RECORD", "", ""])
    return rows


def build_wheel() -> Path:
    ensure = DIST
    ensure.mkdir(parents=True, exist_ok=True)

    name = "toycc_demo"
    version = "0.1.0"
    wheel_path = ensure / wheel_name(name, version)
    pkg_dir = "toycc_demo"
    dist_dir = dist_info_dir(name, version)

    files: list[tuple[str, bytes]] = [
        (f"{pkg_dir}/__init__.py", b'__version__ = "0.1.0"\n'),
        (f"{pkg_dir}/compiler.py", TOYCC_MAIN.encode("utf-8")),
        (
            f"{dist_dir}/WHEEL",
            b"Wheel-Version: 1.0\nGenerator: custom-demo\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        ),
        (
            f"{dist_dir}/METADATA",
            (
                "Metadata-Version: 2.1\n"
                "Name: toycc-demo\n"
                "Version: 0.1.0\n"
                "Summary: Demo black-box wheel for reverse engineering\n"
            ).encode("utf-8"),
        ),
        (
            f"{dist_dir}/entry_points.txt",
            b"[console_scripts]\ntoycc = toycc_demo.compiler:main\n",
        ),
    ]

    record_lines = []
    for row in record_rows(files):
        record_lines.append(",".join(row))
    files.append((f"{dist_dir}/RECORD", ("\n".join(record_lines) + "\n").encode("utf-8")))

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, data in files:
            zf.writestr(path, data)

    return wheel_path


def main() -> int:
    wheel = build_wheel()
    print(wheel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
