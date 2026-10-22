# ARM64 OS-Based CPU Validation Framework

An open-source project for developing and debugging low-level CPU validation
tests through an ARM64 Linux operating system running under QEMU.

## Status

Repository bootstrap only. No guest has been booted and no validation tests have
been implemented or executed. See [PROJECT_STATUS.md](PROJECT_STATUS.md) for
current progress and [TEST_PLAN.md](TEST_PLAN.md) for planned acceptance criteria.
See [SETUP_LOG.md](SETUP_LOG.md) for setup commands and observed outcomes.

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
Windows is the agreed host. WSL2 with Ubuntu is the proposed Linux tool environment;
installation and access to this workspace remain to be verified.

The intended target is QEMU full-system AArch64 emulation with a Linux guest.
The guest image, CPU model, machine version, and tool versions will be recorded
when selected. Setup instructions will be added after they have been exercised.

## Engineering approach

Work in small, reviewable commits. Each test must define its purpose, expected
result, pass/fail criteria, and useful diagnostic evidence. Report only tests
actually executed, and preserve enough configuration to reproduce failures.

## License

An open-source license has not yet been selected. Select and add a LICENSE file
before inviting reuse or contributions.
