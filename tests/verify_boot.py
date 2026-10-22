"""Live boot acceptance checks; run from the project root inside Linux."""
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path.cwd()
(root / "build").mkdir(exist_ok=True)
records = []


def record(name, path, expected_status, expected_code, actual_code=None):
    data = json.loads(path.read_text())
    assert data["status"] == expected_status, data
    if actual_code is not None:
        assert actual_code == expected_code, actual_code
    if name in ("missing-image", "corrupt-image"):
        expected = "Guest image missing" if name == "missing-image" else "checksum mismatch"
        assert expected in data.get("error", ""), data
        assert data["qemu_started"] is False
    if expected_status == "TIMEOUT":
        assert data["fault_injection"] == "paused-cpus"
        assert data["qemu_started"] is True
        assert "observed" not in data
    if expected_status == "PASS":
        assert all(data["checks"].values()), data
        assert data["observed"]["architecture"] == "aarch64"
        assert data["observed"]["online_cpus"] == 2
        assert data["observed"]["schema_exit"] == 0
        assert data["qemu_returncode"] == 0
    if data["qemu_started"]:
        assert data["qemu_reaped"] is True
        assert not Path(f"/proc/{data['qemu_pid']}").exists()
        assert (path.parent / "serial.log").is_file()
    else:
        assert expected_status == "ERROR"
    records.append({"scenario": name, "result": str(path.relative_to(root)),
                    "expected_status": expected_status, "expected_exit": expected_code,
                    "actual_exit": actual_code, "data": data})
    (root / "build/boot-verification.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"Verified {name}: {data['status']} ({data['duration_seconds']} s)", flush=True)


def run(name, args, status, code):
    completed = subprocess.run([sys.executable, "scripts/boot.py", *args], text=True, capture_output=True)
    print(completed.stdout, end="", flush=True)
    print(completed.stderr, end="", flush=True)
    match = re.search(r"(?:PASS|FAIL|ERROR|TIMEOUT): (.*result.json)", completed.stdout)
    assert match, completed
    record(name, Path(match[1]), status, code, completed.returncode)


run("missing-image", ["--image", "images/does-not-exist.qcow2"], "ERROR", 1)
(root / "build/corrupt-image.qcow2").write_bytes(b"invalid guest image\n")
run("corrupt-image", ["--image", "build/corrupt-image.qcow2"], "ERROR", 1)
run("paused-cpus", ["--inject-stall", "--timeout", "2"], "TIMEOUT", 124)
run("recovery-clean-boot-1", [], "PASS", 0)
run("clean-boot-2", [], "PASS", 0)
first, second = records[-2]["data"], records[-1]["data"]
assert first["nonce"] != second["nonce"]
assert first["image_sha512"] == second["image_sha512"]
assert first["firmware_vars_sha512"] == second["firmware_vars_sha512"]
print("All milestone checks passed.", flush=True)
