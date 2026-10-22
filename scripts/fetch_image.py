#!/usr/bin/env python3
"""Fetch and checksum-verify the image pinned in the boot configuration."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from boot import ROOT, sha512


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/boot.json")
    args = parser.parse_args()
    try:
        image = json.loads(args.config.read_text())["image"]
        directory = ROOT / "images"
        directory.mkdir(exist_ok=True)
        destination = directory / image["filename"]
        if not destination.exists():
            partial = destination.with_suffix(destination.suffix + ".part")
            subprocess.run(["curl", "--fail", "--location", "--retry", "2",
                            "--connect-timeout", "30", "--max-time", "1800",
                            "--output", str(partial), image["url"]], check=True)
            if sha512(partial) != image["sha512"]:
                raise ValueError(f"Download checksum mismatch: {partial}")
            partial.replace(destination)
        if sha512(destination) != image["sha512"]:
            raise ValueError(f"Existing image checksum mismatch: {destination}")
        print(f"Verified SHA-512: {destination}")
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"Image preparation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
