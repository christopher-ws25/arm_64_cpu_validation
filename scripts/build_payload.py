#!/usr/bin/env python3
"""Cross-build the first Linux payload, retaining the source and build metadata."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / "build/isa_add_flags"
    output.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / "payloads/isa_add_flags" / name for name in ("main.c", "add_flags.S")]
    binary = output / "isa_add_flags.elf"
    # A fixed, uncommon user virtual address simplifies this one system-GDB demo.
    command = ["aarch64-linux-gnu-gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
               "-g", "-O0", "-static", "-fno-pie", "-no-pie",
               "-Wl,-Ttext-segment=0x41000000", *map(str, sources), "-o", str(binary)]
    subprocess.run(command, check=True)
    metadata = {
        "command": command,
        "compiler": subprocess.check_output([command[0], "--version"], text=True).splitlines()[0],
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "sources": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
    }
    for source in sources:
        shutil.copyfile(source, output / source.name)
    (output / "build.json").write_text(json.dumps(metadata, indent=2) + "\n")
    subprocess.run(["file", str(binary)], check=True)
    print(f"Built: {binary}")


if __name__ == "__main__":
    main()
