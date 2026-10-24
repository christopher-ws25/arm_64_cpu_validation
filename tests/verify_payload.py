"""Live first-payload acceptance: debug pass, deliberate failure, recovery pass."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
records = []


def check(name, path, actual_exit):
    data = json.loads(path.read_text())
    injected = name == "injected-failure"
    assert data["status"] == ("FAIL" if injected else "PASS"), data
    if actual_exit is not None:
        assert actual_exit == int(injected)
    assert data["payload"]["exit_code"] == int(injected)
    assert data["payload"]["summary"]["failures"] == int(injected)
    assert data["payload"]["summary"]["cases"] == 6
    assert data["payload"]["summary"]["injected_failure"] is injected
    assert data["qemu_returncode"] == 0 and data["qemu_reaped"]
    assert not Path(f"/proc/{data['qemu_pid']}").exists()
    assert all(value for key, value in data["checks"].items() if key != "payload_success")
    assert data["checks"]["payload_success"] is not injected
    current_hash = hashlib.sha256((ROOT / "build/isa_add_flags/isa_add_flags.elf").read_bytes()).hexdigest()
    assert data["payload_build"]["binary_sha256"] == current_hash
    failed = [case for case in data["payload"]["cases"] if not case["passed"]]
    if injected:
        assert [case["name"] for case in failed] == ["negative_with_carry"]
        assert int(failed[0]["actual"], 16) ^ int(failed[0]["expected"], 16) == 1
    if name == "live-debug":
        assert data["checks"]["live_debug"] and data["gdb_returncode"] == 0 and data["gdb_reaped"]
        assert not Path(f"/proc/{data['gdb_pid']}").exists()
    records.append({"scenario": name, "actual_exit": actual_exit,
                    "result": str(path.relative_to(ROOT)), "data": data})
    (ROOT / "build/payload-verification.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"Verified {name}: {data['status']}", flush=True)


def run(name, *arguments):
    completed = subprocess.run([sys.executable, "scripts/boot.py", "--payload", *arguments],
                               cwd=ROOT, text=True, capture_output=True)
    print(completed.stdout, end="", flush=True)
    print(completed.stderr, end="", flush=True)
    match = re.search(r"(?:PASS|FAIL|ERROR|TIMEOUT): (.*result.json)", completed.stdout)
    assert match, completed
    check(name, Path(match[1]), completed.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug-result", type=Path, help="Reuse an already completed live-debug result for the same binary")
    args = parser.parse_args()
    if args.debug_result:
        # Reusing an existing successful result cannot establish its shell exit;
        # retain null rather than claiming we launched that process here.
        data = json.loads(args.debug_result.read_text())
        assert data["status"] == "PASS"
        check("live-debug", args.debug_result.resolve(), None)
        records[-1]["reused_result"] = True
    else:
        run("live-debug", "--debug-payload")
    run("injected-failure", "--inject-payload-failure")
    run("recovery")
    assert len({record["data"]["nonce"] for record in records}) == 3
    print("All payload acceptance checks passed.", flush=True)
