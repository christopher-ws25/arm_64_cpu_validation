# First ARM64 Linux Boot

## Current state

The agreed configuration is in `config/boot.json`. The pinned image has been
downloaded and verified, and a live boot has passed architecture, CPU-count,
cloud-configuration schema, initialization completion, and clean-shutdown checks.
Two fresh boots plus missing-image, corrupt-image, and timeout checks passed their
expected outcomes. See [the milestone report](reports/2026-10-22-boot.md).

## DUT configuration

| Component | Choice and reason |
| --- | --- |
| Guest OS | Official Debian 13 genericcloud ARM64 image; standard glibc userspace for later C tests |
| Image build | `20261021-2638`, fixed URL and published SHA-512 |
| Machine | `virt-8.2`, explicit GICv3; versioned machine matching installed QEMU 8.2 |
| CPU | `cortex-a72`, fixed baseline model rather than a changing maximum feature set |
| Execution | TCG, two vCPUs, 1024 MiB RAM |
| Boot path | Distribution UEFI firmware, then the guest disk's bootloader and Linux |
| Guest initialization | Local NoCloud seed containing a short boot observation script |
| Networking | Virtio NIC with QEMU-internal DHCP, `restrict=on`, IPv6 backend disabled, and no port forwarding; no credentials required |
| Disk state | Fresh qcow2 overlay and writable UEFI variables on every run |

This uses a real distribution kernel and root filesystem. We are not writing a
kernel, bootloader, or firmware. The model does not represent Cortex-A72 timing
or establish physical CPU correctness.

## Run the boot check

The following additional host packages are installed. To reproduce on a new
Ubuntu host, install them along with the toolchain packages from `SETUP_LOG.md`:

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends qemu-efi-aarch64 cloud-image-utils
```

From the project directory in WSL:

```sh
python3 scripts/fetch_image.py
python3 scripts/boot.py
```

The image downloader checks the pinned SHA-512 and rejects an existing image
with different contents. The expected digest was obtained from Debian's official
HTTPS checksum file; detached-signature validation has not been implemented.
Images and generated run artifacts are ignored by Git.

## What the boot check will do

1. Verify the image checksum, tools, and firmware files.
2. Create a unique directory under `artifacts/`.
3. Create a writable disk overlay backed by the downloaded base image, copy
   pristine UEFI variables, and create a local cloud-init seed.
4. Launch QEMU and capture serial output and stderr in `serial.log`.
5. Validate cloud-init user-data/network schema and run `uname -m`,
   `getconf _NPROCESSORS_ONLN`, and `uname -r` inside the guest.
6. Print a structured observation tagged with a unique per-run nonce. Let
   cloud-init finish and use its `power_state` module to shut the guest down.
7. Require one matching observation, architecture `aarch64`, two online CPUs,
   schema exit code 0, the matching cloud-init completion marker, no Python
   traceback in the serial log, and QEMU exit code 0 before reporting PASS.

The nonce distinguishes the intended guest result from unrelated console text.
It is not a security or attestation mechanism. The timeout covers the running
QEMU process, including guest shutdown, and defaults to 300 seconds. A marker
without clean shutdown does not pass. On timeout, the runner terminates its
QEMU process group, escalates to kill if needed, and reaps the process.

## Evidence and reproduction

Each run records `result.json`, the complete QEMU argument list and version,
image and firmware hashes, guest observations, timeout, injection mode, process
ID and cleanup state, Git revision/dirty state, a copy of the executed runner,
generated seed inputs,
`prepare.log`, and `serial.log` when QEMU starts. Preflight failures still produce
a JSON error record but have no serial log because no guest was launched.

Run configuration and generated boot input remain alongside the evidence.
The dirty-state indicator is required context: a Git revision alone does not
identify modified source contents. The saved `boot.py` preserves the actual
executed runner even for runs from a dirty checkout.

Negative checks:

```sh
python3 scripts/boot.py --image images/does-not-exist.qcow2
python3 scripts/boot.py --image build/corrupt-image.qcow2
python3 scripts/boot.py --inject-stall --timeout 2
```

For the corrupt-image case, first create a small text file at the shown path;
the file must exist and differ from the configured checksum. Missing/corrupt
image: exit 1, `qemu_started: false`. Injected stall: QEMU `-S`
pauses all guest CPUs before execution; expected runner exit 124 and status
TIMEOUT, retained log, and `qemu_reaped: true`. This tests harness timeout
handling, not a Linux hang. A normal run after injection must still pass.

Exit codes: 0 PASS, 1 failure/error, 2 invalid CLI arguments, 124 timeout, and
130 operator interruption.

To rerun the live acceptance scenarios from the project root inside Ubuntu:

```sh
python3 tests/verify_boot.py
```

This runs the missing-image, corrupt-image, and paused-CPU checks, then two
fresh normal boots. It asserts the expected failure reasons, exit codes,
process cleanup, guest observations, distinct run IDs, unchanged base-image
hash, and identical pristine firmware-variable input. A JSON verification
record is written to `build/boot-verification.json`. Allow several minutes;
this is a boot acceptance script, not the future CPU regression framework.

## Bring-up findings and practical limits

- With no virtual NIC, the distribution's wait-online service delayed the first
  boot by about two minutes and failed. Supplying an isolated NIC and DHCP
  configuration removed that delay in the corrected run. QEMU's `restrict=on`
  prevents host/external routing; no forwarding rules are configured.
- A virtio NIC initially requested an optional `efi-virtio.rom` absent from the
  minimal package installation. `romfile=` disables this unused network-boot ROM;
  the OS still boots from its disk through UEFI.
- The first user-data produced a schema warning. The final user-data removes
  unnecessary system-level datasource/network keys and uses an explicit Ed25519
  host-key type. The guest now reports successful user-data/network validation.
- Calling `poweroff` directly from `runcmd` could interrupt cloud-init's final
  socket interaction and emit a Python traceback. The final configuration uses
  cloud-init's `power_state` module, which waits for cloud initialization before
  shutdown. The runner requires the completion marker and rejects tracebacks.
- One intermediate run shut down without the readiness report when the schema
  command wrote directly to the serial terminal. Capturing its output to a guest
  file and then printing that file and its exit status produced observable
  diagnostics and a successful report. The precise terminal interaction behind
  the intermediate failure has not been isolated; repetition checks exercise
  the resulting path.
- The stock image also logs a headless GRUB video-mode message, missing optional
  initramfs fsck, and an SSH generator AF_VSOCK message. These remain visible in
  serial evidence. PASS covers the stated boot checks, not every guest service.
- This runner boots, observes, and powers off automatically. It does not yet
  provide an interactive DUT login, SSH deployment, C payload execution, GDB
  attachment, or CPU feature coverage. Those are subsequent milestones.

## Sources

- [Debian ARM64 QEMU guidance](https://wiki.debian.org/Arm64Qemu)
- [Pinned Debian build](https://cloud.debian.org/images/cloud/trixie/20261021-2638/)
- [QEMU virt machine](https://www.qemu.org/docs/master/system/arm/virt.html)
- [cloud-init NoCloud](https://docs.cloud-init.io/en/latest/reference/datasources/nocloud.html)
- [QEMU networking options](https://www.qemu.org/docs/master/system/qemu-manpage.html)
- [cloud-init power-state module](https://docs.cloud-init.io/en/latest/reference/modules.html#power-state-change)
