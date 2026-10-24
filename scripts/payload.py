"""Small helpers for deploying and observing the first C/assembly payload."""
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil

CASE_NAMES = ["positive", "zero", "unsigned_carry", "signed_positive_overflow",
              "signed_negative_overflow", "negative_with_carry"]


def prepare(root, run):
    source = root / "build/isa_add_flags"
    metadata = json.loads((source / "build.json").read_text())
    binary = source / "isa_add_flags.elf"
    raw = binary.read_bytes()
    if hashlib.sha256(raw).hexdigest() != metadata["binary_sha256"]:
        raise ValueError("Payload checksum mismatch; rebuild with scripts/build_payload.py")
    # ELF64, little endian, ET_EXEC, AArch64 (183). Debugging needs a fixed address.
    if raw[:6] != b"\x7fELF\x02\x01" or raw[16:20] != b"\x02\x00\xb7\x00":
        raise ValueError("Expected a fixed-address AArch64 ELF64 executable")
    destination = run / "payload"
    destination.mkdir()
    for name in ("isa_add_flags.elf", "build.json", "main.c", "add_flags.S"):
        shutil.copyfile(source / name, destination / name)
    for path, expected in metadata["sources"].items():
        if hashlib.sha256((destination / Path(path).name).read_bytes()).hexdigest() != expected:
            raise ValueError("Saved payload source does not match build metadata")
    return metadata


def seed_lines(binary):
    encoded = base64.b64encode(binary.read_bytes()).decode("ascii")
    return ["  - path: /usr/local/bin/isa_add_flags", "    permissions: '0755'",
            "    encoding: b64", "    content: |",
            *["      " + encoded[i:i + 76] for i in range(0, len(encoded), 76)]]


def guest_script(nonce, sha256, inject):
    argument = " --inject-failure" if inject else ""
    return f"""
test "$(sha256sum /usr/local/bin/isa_add_flags | cut -d ' ' -f1)" = "{sha256}"
payload_rc=0
/usr/local/bin/isa_add_flags {nonce}{argument} > /run/payload.log 2>&1 || payload_rc=$?
cat /run/payload.log > /dev/ttyAMA0
printf 'ARM64_PAYLOAD_EXIT {{"nonce":"{nonce}","exit_code":%s}}\\n' "$payload_rc" > /dev/ttyAMA0
"""


def observations(text, marker, nonce):
    found = []
    for match in re.finditer(re.escape(marker) + r" (\{[^\r\n]*\})", text):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if value.get("nonce") == nonce:
            found.append(value)
    return found


def verify(text, nonce, inject):
    cases = observations(text, "ARM64_CASE", nonce)
    summaries = observations(text, "ARM64_PAYLOAD_RESULT", nonce)
    exits = observations(text, "ARM64_PAYLOAD_EXIT", nonce)
    if len(summaries) != 1 or len(exits) != 1 or [case["name"] for case in cases] != CASE_NAMES:
        raise ValueError("Missing, duplicate, or unexpected payload observations")
    summary = summaries[0]
    failures = 0
    for case in cases:
        passed = (int(case["actual"], 16) == int(case["expected"], 16)
                  and int(case["nzcv"], 16) == int(case["expected_nzcv"], 16))
        if type(case["passed"]) is not bool or case["passed"] != passed:
            raise ValueError("Payload case verdict contradicts its measurements")
        failures += not passed
    rc = 1 if failures else 0
    if (summary["test"] != "isa_add_flags" or summary["cases"] != len(cases)
            or summary["failures"] != failures or summary["injected_failure"] is not inject
            or summary["exit_code"] != rc or exits[0]["exit_code"] != rc):
        raise ValueError("Payload summary/exit status contradicts case results")
    return {"summary": summary, "cases": cases, "exit_code": rc}


def gdb_commands(binary, socket, nonce):
    return f"""set pagination off
set confirm off
set architecture aarch64
file {binary}
target remote {socket}
set schedule-multiple on
hbreak *a64_add_flags
continue
x/4i $pc
info registers x0 x1 x2 pc cpsr
if $x0 != 1 || $x1 != 2
  echo Unexpected breakpoint arguments\\n
  quit 1
end
if ($cpsr & 0xf) != 0
  echo Breakpoint did not hit EL0 user mode\\n
  quit 1
end
if *(unsigned int *)$pc != 0xab010000
  echo Unexpected instruction at breakpoint\\n
  quit 1
end
stepi
if $x0 != 3 || ($cpsr & 0xf0000000) != 0
  echo ADDS register/flag mismatch\\n
  quit 1
end
stepi
if $x3 != 0
  echo MRS NZCV mismatch\\n
  quit 1
end
printf "ARM64_GDB_RESULT {{\\"nonce\\":\\"{nonce}\\",\\"sum\\":%llu,\\"nzcv\\":%llu}}\\n", $x0, $x3
delete breakpoints
detach
quit 0
"""
