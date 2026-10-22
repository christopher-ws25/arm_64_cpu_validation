# Test Plan

## Current execution status

No guest boot or CPU validation tests have been executed. A boot runner has been
drafted; Python syntax and CLI checks passed. All cases below remain unexecuted.

## Milestone 1: Reproducible ARM64 Linux boot

The Linux tool environment is verified. Guest configuration approval is pending.
See `BOOT_WORKFLOW.md` for the proposed configuration and check definitions.

| ID | Scenario | Expected result and pass criterion |
| --- | --- | --- |
| BOOT-001 | Boot the selected Linux image | Serial console reaches an agreed readiness marker before the configured timeout; boot log is retained. |
| BOOT-002 | Verify guest architecture | Guest `uname -m` reports `aarch64`. |
| BOOT-003 | Verify CPU configuration | Guest reports two online CPUs when QEMU is configured with two vCPUs. |
| BOOT-004 | Repeat from clean state | Two consecutive launches using fresh writable overlays satisfy BOOT-001 through BOOT-003. |
| BOOT-005 | Supply a missing image | Launcher exits nonzero with an actionable diagnostic and does not start a guest. |
| BOOT-006 | Exercise boot timeout | A controlled stalled-boot scenario is reported as a timeout; the launcher exits nonzero, retains logs, and terminates its QEMU process. |

Record QEMU version and arguments, guest image source and checksum, relevant
configuration, timeout, commands, and actual observations with each executed run.
The drafted runner uses a per-run nonce-tagged guest observation plus clean
shutdown, with a 300-second QEMU deadline. Timeout injection pauses QEMU CPUs
using `-S`; this checks the host runner rather than inducing a Linux deadlock.
Each run creates both a fresh disk overlay and a pristine UEFI variables copy.
These mechanisms still require live verification.

## Later coverage

Define detailed cases incrementally for C/assembly execution, memory protection,
page faults, copy-on-write, atomics, synchronization, and SMP. Include negative
cases where meaningful. Memory-ordering results under QEMU are observations of
the emulated environment, not proof of hardware memory-model correctness.
