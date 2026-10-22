# Project Status

Last updated: 2026-10-22

## Completed

- Inspected the initially empty Windows project directory and available tools.
- Confirmed Git is installed and an author identity is configured.
- User confirmed Windows Python 3.14.3 works in their PowerShell session.
- User Task Manager screenshots confirmed an AMD Ryzen 9 7940HS (8 cores,
  16 logical processors), firmware virtualization enabled, and 16 GB installed
  RAM (15.2 GB usable). Approximately 2.2 GB was available at capture time.
- Added the initial README, test plan, project status, and Git hygiene files.
- Created the public GitHub repository at
  https://github.com/christopher-ws25/arm_64_cpu_validation.
- Pushed the initial documentation commit to `main` and configured `origin/main`
  as its upstream branch.
- Installed Ubuntu 24.04.5 LTS under WSL2; verified the Linux kernel and access
  to the existing Windows project directory. Detailed commands are in `SETUP_LOG.md`.
- Verified default Linux account `csutjiono` and installed QEMU 8.2.2,
  AArch64 GCC 13.3.0, GDB multiarch 15.1, Make 4.3, Linux Python 3.12.3,
  virtual-environment support, and Linux Git 2.43.0.
- Cross-compiled and linked an AArch64 ELF with libc; GDB recognized its
  architecture and source symbols. Verified Python venv/pip and QEMU capabilities.
- Completed the first boot milestone: downloaded and SHA-512-verified the pinned
  Debian 13 ARM64 image, booted it under QEMU, and retained serial/JSON evidence.
- Verified two consecutive clean boots after fault injection: `aarch64`, two
  online CPUs, valid cloud-init schema, completed initialization, no Python
  traceback, and QEMU exit 0. Missing/corrupt images fail before QEMU launch;
  paused CPUs hit timeout exit 124 and QEMU is reaped.
- Added reusable live acceptance checks in `tests/verify_boot.py` and a committed
  result summary in `reports/2026-10-22-boot.md` and `.json`.

## Decisions

- Use the Windows machine and keep the project in the current directory:
  `C:\Users\Christopher\Documents\prj\arm_64_cpu_validation`.
- Progress step by step; agree major design choices before implementation.
- Use QEMU and Linux for OS-based CPU validation, with explicit emulation limits.
- Proceed with WSL2 and Ubuntu 24.04 as the Linux tool environment.
- First milestone: reproducible ARM64 Linux boot with retained evidence; completed.
- Maintain `SETUP_LOG.md` with setup steps, commands, and actual outcomes.
- User approved Debian 13 ARM64 / `virt-8.2,gic-version=3` / Cortex-A72 / TCG /
  two vCPUs / 1024 MiB RAM. The dated image and checksum are pinned in `config/boot.json`.
- Provide an isolated virtio NIC with QEMU DHCP to satisfy cloud-image startup;
  no port forwarding or external routing. Every run gets fresh disk and UEFI state.
- Let cloud-init finish before shutdown; fail the boot check on missing
  observation/completion markers, bad schema, Python traceback, or nonzero QEMU exit.

## Outstanding issues

- No interactive DUT login, payload deployment/execution, guest GDB session,
  or low-level C/assembly validation tests are implemented yet.
- The assistant session cannot execute the WindowsApps Python alias, despite
  Python working in the user's own PowerShell session.
- Stock guest logs contain headless video, optional fsck, and AF_VSOCK messages;
  PASS covers the documented checks, not all guest service health. Earlier
  bring-up failures and fixes are documented in `BOOT_WORKFLOW.md` and the report.
- Image integrity is pinned to Debian's published checksum over HTTPS;
  detached-signature validation is not implemented.
- Open-source license selection is pending.

## Next steps

1. Agree a small first C/assembly payload with explicit expected results and a
   transfer/debug mechanism. Keep guest networking local if SSH is selected.
2. Build, deploy, execute, and debug that payload through target Linux.
3. Add memory-protection/fault tests incrementally after the payload workflow works.

## Validation evidence

The earlier build-only C executable was not run. The ARM64 guest boot checks
now pass; no low-level C/assembly CPU validation payload has been executed.
Final runner source revision: `17f71af`. Detailed observations, expected negative
outcomes, and log hashes are in `reports/2026-10-22-boot.json`. Full per-run
logs, copied runner source, writable disks, and seed inputs remain local in
ignored `artifacts/` directories. See `SETUP_LOG.md` for exact commands.

Repository bootstrap: staged whitespace checks passed, and the initial push to
GitHub succeeded. These checks do not exercise the planned validation framework.
