#!/usr/bin/env python3
"""Run one disposable Linux boot check under full-system AArch64 QEMU."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]


def sha512(path):
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stop_qemu(process):
    """Reap our QEMU process even if graceful termination does not work."""
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    process.wait()


def seed_data(nonce):
    # No credentials or external connectivity are needed for this milestone.
    script = f"""#!/bin/sh
set -eu
arch=$(uname -m)
cpus=$(getconf _NPROCESSORS_ONLN)
kernel=$(uname -r)
printf 'ARM64_BOOT_RESULT {{"nonce":"{nonce}","architecture":"%s","online_cpus":%s,"kernel":"%s"}}\\n' "$arch" "$cpus" "$kernel" > /dev/ttyAMA0
"""
    return "\n".join([
        "#cloud-config",
        "datasource_list: [NoCloud]",
        "ssh_deletekeys: false",
        "ssh_genkeytypes: []",
        "write_files:",
        "  - path: /usr/local/sbin/boot-check",
        "    permissions: '0755'",
        "    content: |",
        *["      " + line for line in script.splitlines()],
        "runcmd:",
        "  - [sh, -c, '/usr/local/sbin/boot-check; sync; poweroff']",
        "",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/boot.json")
    parser.add_argument("--image", type=Path, help="Override image path; checksum is still enforced")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--inject-stall", action="store_true", help="Pause CPUs at startup to exercise timeout handling")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")

    nonce = uuid.uuid4().hex
    run = ROOT / "artifacts" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + nonce[:8])
    run.mkdir(parents=True)
    result = {"status": "ERROR", "run_directory": str(run), "nonce": nonce,
              "timeout_seconds": args.timeout, "fault_injection": "paused-cpus" if args.inject_stall else None,
              "qemu_started": False}
    code = 1
    process = None
    start = time.monotonic()
    try:
        config = json.loads(args.config.read_text())
        result["config"] = config
        shutil.copyfile(__file__, run / "boot.py")
        image = (args.image or ROOT / "images" / config["image"]["filename"]).resolve()
        if not image.is_file():
            raise ValueError(f"Guest image missing: {image}. Run python3 scripts/fetch_image.py first.")
        result["image_path"] = str(image)
        result["image_sha512"] = sha512(image)
        if result["image_sha512"] != config["image"]["sha512"]:
            raise ValueError("Guest image checksum mismatch; refusing to boot")
        for tool in ("qemu-system-aarch64", "qemu-img", "cloud-localds"):
            if shutil.which(tool) is None:
                raise ValueError(f"Required tool missing: {tool}")
        for name in ("firmware_code", "firmware_vars"):
            path = Path(config[name])
            if not path.is_file():
                raise ValueError(f"Firmware missing: {path}")
            result[name + "_sha512"] = sha512(path)

        (run / "config.json").write_text(json.dumps(config, indent=2) + "\n")
        (run / "user-data").write_text(seed_data(nonce))
        (run / "meta-data").write_text(f"instance-id: boot-{nonce}\nlocal-hostname: arm64-dut\n")
        (run / "network-config").write_text(
            "version: 2\nethernets:\n  dut:\n"
            "    match: {macaddress: '52:54:00:12:34:56'}\n"
            "    dhcp4: true\n    dhcp6: false\n    optional: true\n")
        with (run / "prepare.log").open("w") as log:
            subprocess.run(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(image), str(run / "guest.qcow2")],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(["cloud-localds", "--network-config", str(run / "network-config"),
                            str(run / "seed.img"), str(run / "user-data"), str(run / "meta-data")],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        shutil.copyfile(config["firmware_vars"], run / "vars.fd")
        command = ["qemu-system-aarch64", "-machine", config["machine"],
                   "-accel", "tcg", "-cpu", config["cpu"], "-smp", str(config["cpus"]),
                   "-m", str(config["memory_mib"]), "-display", "none", "-monitor", "none",
                   "-serial", "stdio", "-no-reboot", "-nic",
                   "user,model=virtio-net-pci,mac=52:54:00:12:34:56,restrict=on,ipv6=off",
                   "-drive", f"if=pflash,format=raw,readonly=on,file={config['firmware_code']}",
                   "-drive", f"if=pflash,format=raw,file={run / 'vars.fd'}",
                   "-drive", f"if=none,id=os,format=qcow2,file={run / 'guest.qcow2'}",
                   "-device", "virtio-blk-pci,drive=os",
                   "-drive", f"if=none,id=seed,format=raw,readonly=on,file={run / 'seed.img'}",
                   "-device", "virtio-blk-pci,drive=seed",
                   "-device", "virtio-rng-pci"]
        if args.inject_stall:
            command.append("-S")
        result["qemu_command"] = command
        result["qemu_version"] = subprocess.check_output(["qemu-system-aarch64", "--version"], text=True).splitlines()[0]
        result["git_revision"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        result["git_dirty"] = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True))
        print(f"Booting; evidence: {run}", flush=True)
        with (run / "serial.log").open("wb") as serial:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=serial,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            result.update(qemu_started=True, qemu_pid=process.pid)
            try:
                result["qemu_returncode"] = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                result.update(status="TIMEOUT", error="Guest did not shut down before the deadline")
                code = 124
            finally:
                stop_qemu(process)
                result["qemu_reaped"] = process.poll() is not None
        if result["status"] != "TIMEOUT":
            text = (run / "serial.log").read_text(errors="replace")
            observations = []
            for match in re.finditer(r"ARM64_BOOT_RESULT (\{[^\r\n]*\})", text):
                try:
                    observation = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
                if observation.get("nonce") == nonce:
                    observations.append(observation)
            if len(observations) != 1:
                raise ValueError(f"Expected one matching guest result; found {len(observations)}")
            observed = observations[0]
            result["observed"] = observed
            result["checks"] = {
                "clean_shutdown": result["qemu_returncode"] == 0,
                "architecture": observed.get("architecture") == "aarch64",
                "online_cpus": observed.get("online_cpus") == config["cpus"],
            }
            result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
            code = 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        result.update(status="ERROR", error=str(exc))
    except KeyboardInterrupt:
        result.update(status="INTERRUPTED", error="Interrupted by operator")
        code = 130
    finally:
        if process is not None:
            stop_qemu(process)
            result["qemu_reaped"] = process.poll() is not None
        result["duration_seconds"] = round(time.monotonic() - start, 3)
        (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{result['status']}: {run / 'result.json'}")
    if "error" in result:
        print(result["error"], file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
