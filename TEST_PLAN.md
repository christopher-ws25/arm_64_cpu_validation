# Test Plan

## Current execution status

The first boot milestone passed on 2026-10-22. Two fresh boots and the three
negative scenarios below were executed. On 2026-10-24 the first C/assembly
payload's six ISA cases, live GDB, deliberate failure, recovery, and debugger
timeout cleanup checks met their expected outcomes. Payload evidence:
[report](reports/2026-10-24-payload.md) and [JSON](reports/2026-10-24-payload.json).
Boot evidence:
[boot report](reports/2026-10-22-boot.md) and
[machine-readable results](reports/2026-10-22-boot.json).

## Milestone 1: Reproducible ARM64 Linux boot

The Linux tool environment and agreed Debian 13 ARM64 / Cortex-A72 / two-vCPU /
1-GiB guest configuration are verified. See `BOOT_WORKFLOW.md` for reproduction.

| ID | Scenario | Expected result and pass criterion | Actual result |
| --- | --- | --- | --- |
| BOOT-001 | Boot the selected Linux image | Guest observation and cloud-init completion markers before deadline; valid config schema, no Python traceback, exit 0 and retained log | PASS, both final boots |
| BOOT-002 | Verify guest architecture | Guest `uname -m` reports `aarch64` | PASS, both final boots |
| BOOT-003 | Verify CPU configuration | Guest reports two online CPUs when QEMU is configured with two vCPUs | PASS, both final boots |
| BOOT-004 | Repeat from clean state | Two consecutive fresh writable overlays and UEFI-variable copies satisfy BOOT-001 through BOOT-003 | PASS; distinct run nonces, matching base image and pristine firmware hashes |
| BOOT-005 | Supply a missing image | Exit 1 with actionable missing-image diagnostic; QEMU not started | PASS, expected ERROR / exit 1 |
| BOOT-006 | Exercise boot timeout | Paused CPUs produce timeout, exit 124, retained log, and terminated/reaped QEMU | PASS, expected TIMEOUT / exit 124; subsequent boot passed |
| BOOT-007 | Supply corrupt image | Existing file differs from pinned checksum; exit 1 with checksum diagnostic; QEMU not started | PASS, expected ERROR / exit 1 |

Record QEMU version and arguments, guest image source and checksum, relevant
configuration, timeout, commands, and actual observations with each executed run.
The runner uses a per-run nonce-tagged guest observation plus completed cloud-init and clean
shutdown, with a 300-second QEMU deadline. Timeout injection pauses QEMU CPUs
using `-S`; this checks the host runner rather than inducing a Linux deadlock.
Each run creates both a fresh disk overlay and a pristine UEFI variables copy.
These mechanisms passed live verification. Timeout seconds cover QEMU execution;
total recorded duration also includes preflight and preparation.

## Later coverage

Define detailed cases incrementally for C/assembly execution, memory protection,
page faults, copy-on-write, atomics, synchronization, and SMP. Include negative
cases where meaningful. Memory-ordering results under QEMU are observations of
the emulated environment, not proof of hardware memory-model correctness.

## Milestone 2: First C/AArch64 assembly payload

Sources: `payloads/isa_add_flags/main.c` and `add_flags.S`. Fixed expectations
and command explanations are in `PAYLOAD_WORKFLOW.md`. Each case must compare
both the returned 64-bit sum and the captured raw NZCV value. Normal payload
success requires exactly these six cases, zero failures, and process exit 0.

| ID | Case | Expected sum | Expected NZCV | Executed result |
| --- | --- | --- | --- | --- |
| ISA-ADD-001 | 1 + 2 | 3 | `0x00000000` | PASS in live-debug run |
| ISA-ADD-002 | 0 + 0 | 0 | `0x40000000` | PASS in live-debug run |
| ISA-ADD-003 | UINT64_MAX + 1 | 0 | `0x60000000` | PASS in live-debug run |
| ISA-ADD-004 | Signed positive overflow | `0x8000000000000000` | `0x90000000` | PASS in live-debug run |
| ISA-ADD-005 | Signed negative overflow | 0 | `0x70000000` | PASS in live-debug run |
| ISA-ADD-006 | UINT64_MAX + UINT64_MAX | `0xfffffffffffffffe` | `0xa0000000` | PASS in live-debug run |

The payload uses unsigned C inputs and predetermined expectations; it does not
invoke C signed-overflow behavior to calculate its oracle.

| ID | Scenario | Pass criterion | Executed result |
| --- | --- | --- | --- |
| PAYLOAD-001 | Build and deliver | Compiler warnings treated as errors; fixed-address static AArch64 ELF; guest hash matches built binary | PASS |
| PAYLOAD-002 | Live debug | EL0 breakpoint at ADDS, opcode/arguments 1 and 2, exact PC advance across ADDS and MRS, sum 3 and NZCV 0; debugger exits 0 and is reaped | PASS |
| PAYLOAD-003 | Deliberate wrong expectation | Exactly ISA-ADD-006 fails; guest process exit 1; boot checks pass; host FAIL/exit 1 | PASS: expected FAIL/exit 1 observed |
| PAYLOAD-004 | Recovery | Same binary without injection passes all six cases after failure run | PASS, six cases / exit 0 |
| PAYLOAD-005 | Boot-only regression | Original default boot command still passes without executing a payload | PASS |
| PAYLOAD-006 | Host report rejection | Missing/duplicate cases, incorrect nonce, malformed JSON, contradictions, and mismatched exits cannot create a false pass | PASS, six unit tests |
| PAYLOAD-007 | Debug timeout cleanup | Two-second QEMU deadline returns 124; both QEMU/GDB reaped and absent; temporary socket directory removed | PASS |

Live GDB here is a fixed-address system-stub experiment, not Linux process-aware
debug support. The first stepping attempt failed a debug check despite all C
cases passing; selected-vCPU stepping and explicit PC checks passed on retry.
This does not indicate a CPU defect. Timeouts, OS faults, and broader memory/SMP
coverage are separate from the instruction cases above.
