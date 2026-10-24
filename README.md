# ARM64 OS-Based CPU Validation Framework

An open-source project for developing and debugging low-level CPU validation
tests through an ARM64 Linux operating system running under QEMU.

## Status

ARM64 Debian Linux boots under QEMU and reports its architecture and CPU count
through the serial console. The boot runner checks cloud-configuration schema
and initialization completion, clean shutdown, and Python tracebacks; it retains
logs and provides timeout handling. A first C/AArch64 assembly payload now checks
six 64-bit addition/NZCV cases and supports live GDB instruction stepping. See
[PROJECT_STATUS.md](PROJECT_STATUS.md) and [TEST_PLAN.md](TEST_PLAN.md) for coverage.
See [SETUP_LOG.md](SETUP_LOG.md) for setup commands and observed outcomes.
The first-boot commands, design, evidence format, and bring-up findings are in
[BOOT_WORKFLOW.md](BOOT_WORKFLOW.md).
The verified first milestone results are in
[reports/2026-10-22-boot.md](reports/2026-10-22-boot.md).
For the first test and debugger workflow, see [PAYLOAD_WORKFLOW.md](PAYLOAD_WORKFLOW.md).
Executed results, including the deliberate failure and recovery, are in the
[2026-10-24 payload report](reports/2026-10-24-payload.md).

## Scope

- Low-level C and AArch64 assembly tests with explicit expected results.
- Memory protection, page faults, and copy-on-write through Linux interfaces.
- SMP, atomic operations, synchronization, and memory-ordering experiments.
- Python regression automation with logs, timeouts, and failure reproduction.

QEMU provides an emulated functional environment. Passing tests does not verify
physical CPU cache coherence, cycle-level behavior, performance, or exhaustive
coverage of the Arm memory model.

## Development environment

The project workspace is `C:\Users\Christopher\Documents\prj\arm_64_cpu_validation`.
Windows is the agreed host. Ubuntu 24.04 under WSL2 is installed, and access to
this workspace is verified. QEMU, cross-GCC, GDB, Make, and Linux Python are
installed; their versions and setup checks are recorded in [SETUP_LOG.md](SETUP_LOG.md).

The target is Debian 13 ARM64 under QEMU TCG, using `virt-8.2`/GICv3,
`cortex-a72`, two vCPUs, and 1024 MiB RAM. The dated image URL and SHA-512 are
pinned in `config/boot.json`.

To enter the Linux tool environment from PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

Then enter the existing workspace:

```sh
cd /mnt/c/Users/Christopher/Documents/prj/arm_64_cpu_validation
python3 scripts/fetch_image.py
python3 scripts/boot.py
```

The downloader reuses a verified local image. Each boot creates a fresh writable
overlay and firmware state, emits guest observations, and powers off. Its result
and serial log are in a unique directory under `artifacts/`. Images and generated
artifacts stay local and are ignored by Git. This command does not open a guest
shell or execute the earlier build-only C check.

To build and execute the new validation payload instead:

```sh
python3 scripts/build_payload.py
python3 scripts/boot.py --payload
```

| Command | What happens inside the DUT |
| --- | --- |
| `python3 scripts/boot.py` | Boots Debian, checks architecture/CPUs, shuts down |
| `python3 scripts/boot.py --payload` | Also executes six C/assembly test cases |
| `python3 scripts/boot.py --payload --debug-payload` | Also stops at the assembly function and checks two live instruction steps with GDB |
| `python3 scripts/boot.py --payload --inject-payload-failure` | Deliberately corrupts one expected value; should report FAIL/exit 1 |

These are automated headless runs, not interactive guest sessions. Payload and
debugger modes retain per-case results in `result.json`, serial output in
`serial.log`, and debugger output in `gdb.log` when enabled. Build again after
editing payload source; boot executes the saved built binary.

## Engineering approach

Work in small, reviewable commits. Each test must define its purpose, expected
result, pass/fail criteria, and useful diagnostic evidence. Report only tests
actually executed, and preserve enough configuration to reproduce failures.

## License

An open-source license has not yet been selected. Select and add a LICENSE file
before inviting reuse or contributions.
