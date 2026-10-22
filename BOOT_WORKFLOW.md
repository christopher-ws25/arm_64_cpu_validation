# First ARM64 Linux Boot

## Current state

The boot runner is drafted and has passed Python syntax and CLI checks only.
Guest configuration approval, image download, boot dependencies, and live guest
execution remain pending. Do not interpret this document as a successful boot.

The proposed configuration is in `config/boot.proposed.json`. Once agreed, it
will become `config/boot.json`, which the scripts use by default.

## Proposed DUT

| Component | Choice and reason |
| --- | --- |
| Guest OS | Official Debian 13 genericcloud ARM64 image; standard glibc userspace for later C tests |
| Image build | `20261021-2638`, fixed URL and published SHA-512 |
| Machine | `virt-8.2`, explicit GICv3; versioned machine matching installed QEMU 8.2 |
| CPU | `cortex-a72`, fixed baseline model rather than a changing maximum feature set |
| Execution | TCG, two vCPUs, 1024 MiB RAM |
| Boot path | Distribution UEFI firmware, then the guest disk's bootloader and Linux |
| Guest initialization | Local NoCloud seed containing a short boot observation script |
| Networking | No virtual NIC for this milestone; no credentials required |
| Disk state | Fresh qcow2 overlay and writable UEFI variables on every run |

This uses a real distribution kernel and root filesystem. We are not writing a
kernel, bootloader, or firmware. The model does not represent Cortex-A72 timing
or establish physical CPU correctness.

## Planned commands after agreement

Install the additional host packages in Ubuntu:

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
5. Run `uname -m`, `getconf _NPROCESSORS_ONLN`, and `uname -r` inside the guest.
6. Print a structured observation tagged with a unique per-run nonce, then
   shut the guest down.
7. Require one matching observation, architecture `aarch64`, two online CPUs,
   and QEMU exit code 0 before reporting PASS.

The nonce distinguishes the intended guest result from unrelated console text.
It is not a security or attestation mechanism. The timeout covers the running
QEMU process, including guest shutdown, and defaults to 300 seconds. A marker
without clean shutdown does not pass. On timeout, the runner terminates its
QEMU process group, escalates to kill if needed, and reaps the process.

## Evidence and reproduction

Each run records `result.json`, the complete QEMU argument list and version,
image and firmware hashes, guest observations, timeout, injection mode, process
ID and cleanup state, Git revision/dirty state, generated seed inputs,
`prepare.log`, and `serial.log` when QEMU starts. Preflight failures still produce
a JSON error record but have no serial log because no guest was launched.

Run configuration and generated boot input remain alongside the evidence.
While this code is uncommitted, the dirty-state indicator is required context;
a Git revision alone does not identify modified source contents.

Planned negative checks:

```sh
python3 scripts/boot.py --image images/does-not-exist.qcow2
python3 scripts/boot.py --inject-stall --timeout 2
```

Missing image: nonzero exit, `qemu_started: false`. Injected stall: QEMU `-S`
pauses all guest CPUs before execution; expected runner exit 124 and status
TIMEOUT, retained log, and `qemu_reaped: true`. This tests harness timeout
handling, not a Linux hang. A normal run after injection must still pass.

Exit codes: 0 PASS, 1 failure/error, 2 invalid CLI arguments, 124 timeout, and
130 operator interruption.

## Sources

- [Debian ARM64 QEMU guidance](https://wiki.debian.org/Arm64Qemu)
- [Pinned Debian build](https://cloud.debian.org/images/cloud/trixie/20261021-2638/)
- [QEMU virt machine](https://www.qemu.org/docs/master/system/arm/virt.html)
- [cloud-init NoCloud](https://docs.cloud-init.io/en/latest/reference/datasources/nocloud.html)
