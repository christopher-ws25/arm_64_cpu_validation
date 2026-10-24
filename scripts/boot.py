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
import tempfile
import time
import uuid
from datetime import datetime, timezone

import payload as payload_support


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


def seed_data(nonce, payload_binary=None, payload_hash=None, inject=False):
    # No credentials or external connectivity are needed for this milestone.
    script = f"""#!/bin/sh
set -eu
schema_rc=0
cloud-init schema --system > /run/boot-schema.log 2>&1 || schema_rc=$?
cat /run/boot-schema.log > /dev/ttyAMA0
printf 'CLOUD_CONFIG_SCHEMA_EXIT=%s\\n' "$schema_rc" > /dev/ttyAMA0
arch=$(uname -m)
cpus=$(getconf _NPROCESSORS_ONLN)
kernel=$(uname -r)
printf 'ARM64_BOOT_RESULT {{"nonce":"{nonce}","architecture":"%s","online_cpus":%s,"kernel":"%s","schema_exit":%s}}\\n' "$arch" "$cpus" "$kernel" "$schema_rc" > /dev/ttyAMA0
"""
    if payload_binary is not None:
        script += payload_support.guest_script(nonce, payload_hash, inject)
    data = [
        "#cloud-config",
        "ssh_deletekeys: false",
        "ssh_genkeytypes: [ed25519]",
        "write_files:",
        "  - path: /usr/local/sbin/boot-check",
        "    permissions: '0755'",
        "    content: |",
        *["      " + line for line in script.splitlines()],
    ]
    if payload_binary is not None:
        data.extend(payload_support.seed_lines(payload_binary))
    data.extend([
        "runcmd:",
        "  - [/usr/local/sbin/boot-check]",
        f"final_message: 'ARM64_CLOUD_INIT_FINISHED {nonce}'",
        "power_state:",
        "  mode: poweroff",
        "  delay: now",
        "  timeout: 30",
        "  condition: true",
        "",
    ])
    return "\n".join(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/boot.json")
    parser.add_argument("--image", type=Path, help="Override image path; checksum is still enforced")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--inject-stall", action="store_true", help="Pause CPUs at startup to exercise timeout handling")
    parser.add_argument("--payload", action="store_true", help="Deploy and run the built C/assembly test")
    parser.add_argument("--inject-payload-failure", action="store_true", help="Corrupt one test expectation; run must FAIL")
    parser.add_argument("--debug-payload", action="store_true", help="Use live GDB to break and single-step the payload")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    if (args.inject_payload_failure or args.debug_payload) and not args.payload:
        parser.error("payload injection/debugging requires --payload")
    if args.debug_payload and args.inject_stall:
        parser.error("--debug-payload and --inject-stall are separate scenarios")

    nonce = uuid.uuid4().hex
    run = ROOT / "artifacts" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + nonce[:8])
    run.mkdir(parents=True)
    result = {"status": "ERROR", "run_directory": str(run), "nonce": nonce,
              "timeout_seconds": args.timeout, "fault_injection": "paused-cpus" if args.inject_stall else None,
              "qemu_started": False}
    code = 1
    process = None
    debugger = None
    debug_log = None
    debug_directory = None
    start = time.monotonic()
    try:
        config = json.loads(args.config.read_text())
        result["config"] = config
        shutil.copyfile(__file__, run / "boot.py")
        shutil.copyfile(Path(payload_support.__file__), run / "payload.py")
        payload_binary = None
        payload_hash = None
        if args.payload:
            result["payload_build"] = payload_support.prepare(ROOT, run)
            result["payload_injected_failure"] = args.inject_payload_failure
            payload_binary = run / "payload/isa_add_flags.elf"
            payload_hash = result["payload_build"]["binary_sha256"]
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
        if args.debug_payload and shutil.which("gdb-multiarch") is None:
            raise ValueError("Required tool missing: gdb-multiarch")
        for name in ("firmware_code", "firmware_vars"):
            path = Path(config[name])
            if not path.is_file():
                raise ValueError(f"Firmware missing: {path}")
            result[name + "_sha512"] = sha512(path)

        (run / "config.json").write_text(json.dumps(config, indent=2) + "\n")
        (run / "user-data").write_text(seed_data(nonce, payload_binary, payload_hash, args.inject_payload_failure))
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
                   "-serial", "stdio", "-no-reboot", "-netdev",
                   "user,id=net0,restrict=on,ipv6=off", "-device",
                   "virtio-net-pci,netdev=net0,mac=52:54:00:12:34:56,romfile=",
                   "-drive", f"if=pflash,format=raw,readonly=on,file={config['firmware_code']}",
                   "-drive", f"if=pflash,format=raw,file={run / 'vars.fd'}",
                   "-drive", f"if=none,id=os,format=qcow2,file={run / 'guest.qcow2'}",
                   "-device", "virtio-blk-pci,drive=os",
                   "-drive", f"if=none,id=seed,format=raw,readonly=on,file={run / 'seed.img'}",
                   "-device", "virtio-blk-pci,drive=seed",
                   "-device", "virtio-rng-pci"]
        if args.inject_stall:
            command.append("-S")
        if args.debug_payload:
            debug_directory = tempfile.TemporaryDirectory(prefix="arm64-gdb-")
            debug_socket = Path(debug_directory.name) / "gdb.sock"
            command.extend(["-S", "-chardev", f"socket,path={debug_socket},server=on,wait=off,id=gdb0",
                            "-gdb", "chardev:gdb0"])
            (run / "debug.gdb").write_text(payload_support.gdb_commands(payload_binary, debug_socket, nonce))
        result["qemu_command"] = command
        result["qemu_version"] = subprocess.check_output(["qemu-system-aarch64", "--version"], text=True).splitlines()[0]
        result["git_revision"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        result["git_dirty"] = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True))
        print(f"Booting; evidence: {run}", flush=True)
        with (run / "serial.log").open("wb") as serial:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=serial,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            result.update(qemu_started=True, qemu_pid=process.pid)
            deadline = time.monotonic() + args.timeout
            try:
                if args.debug_payload:
                    socket_deadline = min(deadline, time.monotonic() + 10)
                    while not debug_socket.exists() and process.poll() is None and time.monotonic() < socket_deadline:
                        time.sleep(0.05)
                    if not debug_socket.exists():
                        raise ValueError("QEMU debug socket did not become ready; inspect serial.log")
                    debug_log = (run / "gdb.log").open("wb")
                    debugger = subprocess.Popen(["gdb-multiarch", "-q", "-batch", "-x", str(run / "debug.gdb")],
                                                stdin=subprocess.DEVNULL, stdout=debug_log,
                                                stderr=subprocess.STDOUT, start_new_session=True)
                    result["gdb_pid"] = debugger.pid
                result["qemu_returncode"] = process.wait(timeout=max(0, deadline - time.monotonic()))
                if debugger is not None:
                    result["gdb_returncode"] = debugger.wait(timeout=5)
            except subprocess.TimeoutExpired:
                result.update(status="TIMEOUT", error="Guest did not shut down before the deadline")
                code = 124
            finally:
                stop_qemu(process)
                result["qemu_reaped"] = process.poll() is not None
        if result["status"] != "TIMEOUT":
            if result["qemu_returncode"] != 0:
                raise ValueError(f"QEMU exited {result['qemu_returncode']}; inspect {run / 'serial.log'}")
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
                "cloud_config_schema": observed.get("schema_exit") == 0,
                "cloud_init_finished": f"ARM64_CLOUD_INIT_FINISHED {nonce}" in text,
                "no_python_traceback": "Traceback (most recent call last)" not in text,
            }
            if args.payload:
                result["payload"] = payload_support.verify(text, nonce, args.inject_payload_failure)
                result["checks"]["payload_success"] = result["payload"]["exit_code"] == 0
            if args.debug_payload:
                debug_text = (run / "gdb.log").read_text(errors="replace")
                debug_results = payload_support.observations(debug_text, "ARM64_GDB_RESULT", nonce)
                result["gdb_observed"] = debug_results
                result["checks"]["live_debug"] = (result["gdb_returncode"] == 0 and len(debug_results) == 1
                                                    and debug_results[0].get("sum") == 3
                                                    and debug_results[0].get("nzcv") == 0)
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
        if debugger is not None:
            stop_qemu(debugger)
            result["gdb_reaped"] = debugger.poll() is not None
        if debug_log is not None:
            debug_log.close()
        if debug_directory is not None:
            debug_directory.cleanup()
        result["duration_seconds"] = round(time.monotonic() - start, 3)
        (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{result['status']}: {run / 'result.json'}")
    if "error" in result:
        print(result["error"], file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
