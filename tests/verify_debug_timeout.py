"""Live check that an early deadline reaps both debugger and emulated DUT."""
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
command = [sys.executable, "scripts/boot.py", "--payload", "--debug-payload", "--timeout", "2"]
completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
print(completed.stdout, end="")
print(completed.stderr, end="")
assert completed.returncode == 124, completed
match = re.search(r"TIMEOUT: (.*result.json)", completed.stdout)
assert match, completed
path = Path(match[1])
data = json.loads(path.read_text())
assert data["status"] == "TIMEOUT"
assert data["qemu_reaped"] and data["gdb_reaped"]
for name in ("qemu_pid", "gdb_pid"):
    assert not Path(f"/proc/{data[name]}").exists()
assert (path.parent / "serial.log").exists() and (path.parent / "gdb.log").exists()
socket_arg = data["qemu_command"][data["qemu_command"].index("-chardev") + 1]
socket_path = Path(socket_arg.split("path=", 1)[1].split(",", 1)[0])
assert not socket_path.parent.exists()
(root / "build/debug-timeout-verification.json").write_text(json.dumps({
    "actual_exit": completed.returncode, "result": str(path.relative_to(root)), "data": data,
    "process_absence_verified": True, "socket_directory_removed": True,
}, indent=2) + "\n")
print("Debug timeout cleanup verified.")
