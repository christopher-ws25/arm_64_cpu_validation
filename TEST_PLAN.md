# Test Plan

## Current execution status

The first boot milestone passed on 2026-10-22. Two fresh boots and the three
negative scenarios below were executed. Low-level C/assembly CPU validation
payloads remain unimplemented and unexecuted. Evidence:
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
