# Test Plan

## Current execution status

No validation tests have been implemented or executed. All cases below are planned.

## Milestone 1: Reproducible ARM64 Linux boot

Before implementation, confirm the Linux tool environment and guest image.

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
Readiness detection, timeout values, and fault injection will be defined before
these cases are implemented.

## Later coverage

Define detailed cases incrementally for C/assembly execution, memory protection,
page faults, copy-on-write, atomics, synchronization, and SMP. Include negative
cases where meaningful. Memory-ordering results under QEMU are observations of
the emulated environment, not proof of hardware memory-model correctness.
