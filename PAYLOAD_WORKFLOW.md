# First C/AArch64 Assembly Validation Payload

## How this extends the DUT boot

The DUT is still the same headless ARM64 machine running Debian. The original
`python3 scripts/boot.py` command remains a boot-only check. Add `--payload` to
execute our first test inside that Linux guest; add `--debug-payload` for an
automated live debugger session. Every mode still shuts the guest down at the end.

```text
Windows project directory (same files visible under /mnt/c in WSL)
  main.c + add_flags.S
         |
  AArch64 GCC running in WSL Ubuntu
         |
  ARM64 Linux executable + symbols + build manifest
         |
  local seed disk carries compressed binary into Debian
         |
  Debian creates an EL0 Linux process and executes the test
         |
  case measurements + summary + actual process exit over serial
         |
  Python checks results and retains the evidence
```

We use the existing NoCloud seed rather than introducing SSH/file transfer
infrastructure. `write_files` decompresses/decodes the ELF into
`/usr/local/bin/isa_add_flags`. Before execution, the guest checks its SHA-256
against the built binary. No new network forwarding or guest login is configured.

## Build and run

Run these commands inside WSL Ubuntu:

```sh
cd /mnt/c/Users/Christopher/Documents/prj/arm_64_cpu_validation
python3 scripts/build_payload.py
python3 scripts/boot.py --payload
```

The builder statically links libc, includes debug symbols, and treats compiler
warnings as errors. It saves the binary, source copies, compiler command/version,
and SHA-256 hashes under ignored `build/isa_add_flags/`. Each guest run snapshots
those files into its own ignored artifact directory.

`PASS` requires both the original boot checks and a successful six-case payload.
If the OS boots and shuts down correctly but the test fails, the overall result
is `FAIL`, exit 1. Missing or contradictory observations are errors, not passes.

## What the test validates

`payloads/isa_add_flags/main.c` calls `a64_add_flags(a, b, &flags)` in
`add_flags.S`. AAPCS64 passes the arguments in `x0`, `x1`, and `x2`. The assembly
returns the sum in `x0` and stores NZCV through the pointer before returning:

```asm
adds x0, x0, x1
mrs x3, nzcv
str x3, [x2]
ret
```

The C code compares the result and flags with independent fixed constants, not
with another implementation of the same assembly. C uses unsigned 64-bit values;
the signed-overflow cases are observed in hardware-model flags rather than
performing undefined signed-overflow arithmetic in C.

| Case | Inputs, hexadecimal except first two | Expected sum | NZCV |
| --- | --- | --- | --- |
| Positive | 1 + 2 | 3 | `0x00000000` |
| Zero | 0 + 0 | 0 | `0x40000000` (Z) |
| Unsigned carry | `ffffffffffffffff + 1` | 0 | `0x60000000` (Z,C) |
| Signed positive overflow | `7fffffffffffffff + 1` | `8000000000000000` | `0x90000000` (N,V) |
| Signed negative overflow | `8000000000000000 + 8000000000000000` | 0 | `0x70000000` (Z,C,V) |
| Negative with carry | `ffffffffffffffff + ffffffffffffffff` | `fffffffffffffffe` | `0xa0000000` (N,C) |

NZCV uses bits 31:28: negative, zero, unsigned carry, and signed overflow. Flags
are not preserved across arbitrary C function calls; capturing them immediately
inside the assembly is deliberate.

Coverage is narrow: 64-bit register addition, NZCV capture, an AAPCS64 C/assembly
boundary, process execution, and reporting. This is not exhaustive ISA, MMU,
SMP, cache-coherency, timing, or physical-silicon validation.

Cloud-init launches this program as Linux user root, but its instructions still
execute at EL0. A Linux UID determines OS permissions; it does not make a normal
userspace process run at the kernel's exception level. The live debugger checks
the processor mode at the assembly breakpoint.

## Deliberately fail a test

```sh
python3 scripts/boot.py --payload --inject-payload-failure
```

This flips one bit in the last case's expected sum. It does not alter the CPU
operation or simulate a physical hardware defect. Expected outcome: five cases
pass, `negative_with_carry` fails, the payload returns 1, the guest shuts down
cleanly, and the host reports `FAIL`/exit 1. The serial log shows actual and
expected values, so this failure can be reproduced and investigated.

## Live debugging

```sh
python3 scripts/boot.py --payload --debug-payload
```

GDB runs in WSL and connects to QEMU's system debug stub over a private local
Unix socket. QEMU initially pauses; GDB installs a hardware breakpoint at the
assembly function and resumes boot. At the breakpoint it checks EL0 mode, the
instruction opcode, and arguments 1 and 2. It then pins stepping to the selected
vCPU, single-steps ADDS and MRS, and checks PC advancement, sum 3, and NZCV 0.
GDB detaches, Linux completes the test, and the guest powers off normally.

This is similar in purpose to a platform debug connection: registers, instruction
stepping, and execution control. QEMU's system stub sees vCPUs, not Linux process
threads. We deliberately link this small static executable at user virtual text
segment `0x41000000` to simplify a known fixed-address breakpoint and reduce
collision with ordinary distribution executable addresses. This is not a general
process-aware debugger workflow; gdbserver would be a later option.

`gdb.log` records the actual breakpoint, source/instruction listings, registers,
steps, and the nonce-tagged result. `debug.gdb` contains the executed commands.
The socket path in that file is temporary and removed at exit; reproduce using
the launcher command, which creates a fresh socket. The launcher cleans up both
QEMU and GDB on failure or timeout. A debugger check failure makes the overall
run fail even if every C case passes.

## Evidence and acceptance checks

Each run retains `serial.log`, `result.json`, `boot.py`, `payload.py`, and a
`payload/` directory containing the executable, source copies, and build manifest.
`result.json` includes per-case actual/expected values, flags, summary, process
exit, binary hash, and debugger observations when enabled. No executable or VM
disk is committed to Git.

```sh
python3 -m unittest discover -s tests -p test_payload_protocol.py -v
python3 tests/verify_payload.py
```

The first command checks host result rejection without a VM. The second runs a
live-debug pass, injected failure, and recovery pass, saving verification records
to `build/payload-verification.json`. It can reuse a completed debug run for the
same binary with `--debug-result /absolute/path/to/result.json`; reuse is recorded
explicitly, without claiming a new debugger execution.

The debugger cleanup path can be checked separately:

```sh
python3 tests/verify_debug_timeout.py
```

This intentionally interrupts boot after a two-second QEMU execution deadline,
requires Linux exit 124, and checks both process IDs are absent and the temporary
socket directory is removed. The test script exits 0 when that expected timeout
has been correctly handled.

Actual execution results and the first failed debugger attempt are documented in
[the payload report](reports/2026-10-24-payload.md). All six cases passed in normal
runs, the deliberate failure was detected, recovery passed, the original boot
command passed, and debugger timeout cleanup passed. These are finite functional
checks in QEMU, not proof of physical CPU correctness.

## References

- [Arm AAPCS64](https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst)
- [QEMU GDB stub and system/user debugging limits](https://www.qemu.org/docs/master/system/gdb.html)
- [GDB remote connections](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Connecting.html)
- [cloud-init file encoding](https://docs.cloud-init.io/en/24.1/reference/examples.html#writing-out-arbitrary-files)
