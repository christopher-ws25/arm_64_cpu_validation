# Setup Log

Record completed steps and actual outcomes here. A planned or attempted command
does not count as a successful installation. Do not record passwords or tokens.

## 2026-10-22: Windows and WSL setup

### 1. Inspect the host and workspace — complete

- Windows build 26200.9457; AMD Ryzen 9 7940HS, 8 cores / 16 threads.
- User Task Manager screenshots confirm 16 GB RAM and virtualization enabled.
- Git 2.53.0.windows.1 available. User confirmed Windows Python 3.14.3.
- Workspace retained at `C:\Users\Christopher\Documents\prj\arm_64_cpu_validation`.

### 2. Initialize the repository — complete

- Initialized Git on `main`; added project documents and Git hygiene files.
- Created and pushed to
  https://github.com/christopher-ws25/arm_64_cpu_validation.

### 3. Install the WSL platform — complete

User ran in Administrator PowerShell:

```powershell
wsl --install -d Ubuntu-24.04 --no-launch
```

The supplied output confirmed WSL 3.0.3 installation and successful enablement of
VirtualMachinePlatform, with a reboot required. The subsequent distribution
listing reported no installed distributions: this step did not install Ubuntu.

Assistant verification after the user returned:

```powershell
wsl --version
wsl --list --verbose
```

Observed WSL 3.0.3.0 and kernel 6.18.54.1-1; no distributions installed.
The sandbox denied distribution-list access; running the query outside the
sandbox succeeded. Sandbox elevation is distinct from Windows administrator
privileges.

### 4. Install Ubuntu 24.04 — complete

Assistant started:

```powershell
wsl --install -d Ubuntu-24.04 --no-launch
```

The first attempt produced no output and did not register a distribution during
observation. The assistant stopped the two installer processes from this attempt
and retried with a terminal and the supported direct-download option:

```powershell
wsl --install -d Ubuntu-24.04 --web-download --no-launch
```

The direct-download attempt completed with exit code 0 and reported:
`Distribution successfully installed. It can be launched via 'wsl.exe -d Ubuntu-24.04'`.
The command ran outside the sandbox to access the WSL service.

### 5. Verify Ubuntu and initialize normal user — complete

Assistant executed:

```powershell
wsl --list --verbose
wsl -d Ubuntu-24.04 -u root -- sh -c 'cat /etc/os-release; uname -m; uname -r; id; test -d /mnt/c/Users/Christopher/Documents/prj/arm_64_cpu_validation && echo PROJECT_DIRECTORY_ACCESS_OK'
```

Results: Ubuntu-24.04 registered as WSL version 2; Ubuntu 24.04.5 LTS;
`x86_64`; kernel `6.18.54.1-microsoft-standard-WSL2`; root verification session;
`PROJECT_DIRECTORY_ACCESS_OK`. This is the x86_64 Linux tool environment, not
the future ARM64 QEMU target guest. All verification commands exited 0.

An initial check found no UID 1000 user. The user subsequently launched
`wsl -d Ubuntu-24.04` and completed first-run setup privately. Assistant verified
the default account is `csutjiono`, UID 1000, with membership in the `sudo` group,
and confirmed project directory access again.

### 6. Install development tools — complete

Assistant executed from PowerShell, using root only for package installation:

```powershell
wsl -d Ubuntu-24.04 -u root -- sh -c 'export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y --no-install-recommends build-essential gcc-aarch64-linux-gnu libc6-dev-arm64-cross gdb-multiarch qemu-system-arm qemu-utils python3 python3-venv git ca-certificates curl file'
```

Installation exited 0. Packages came from the configured Ubuntu repositories.
Ubuntu's `qemu-system-arm` package supplies `qemu-system-aarch64`.
`dpkg --audit` returned no findings.

Versions verified under the normal Linux account:

| Tool | Observed version |
| --- | --- |
| QEMU AArch64 and qemu-img | 8.2.2; Ubuntu package `1:8.2.2+ds-0ubuntu1.18` |
| AArch64 GCC | 13.3.0 |
| GDB multiarch | 15.1 |
| GNU Make | 4.3 |
| Linux Python | 3.12.3 |
| Linux Git | 2.43.0 |

Linux Python is separate from Windows Python 3.14.3. No change was made to the
Windows interpreter.

### 7. Verify the toolchain — complete

The following checks ran successfully as `csutjiono`:

- `qemu-system-aarch64 -accel help` listed `tcg`.
- `qemu-system-aarch64 -machine help` listed `virt` as an alias of `virt-8.2`.
- `qemu-system-aarch64 -cpu help` listed `cortex-a53` and `cortex-a72`.
- Compiled and statically linked a small C program using libc with warnings
  treated as errors. Its source prints a fixed string and returns 0; this is
  a build-only setup check, not a CPU validation test.

Commands below ran in Ubuntu from the project directory. The check source and
executable are local ignored artifacts under `build/`.

```sh
aarch64-linux-gnu-gcc -std=c11 -Wall -Wextra -Werror -g -O0 -static build/toolchain_check.c -o build/toolchain_check.elf
file build/toolchain_check.elf
aarch64-linux-gnu-readelf -h build/toolchain_check.elf
gdb-multiarch -q -batch -ex "file build/toolchain_check.elf" -ex "show architecture" -ex "info line main"
python3 -m venv /tmp/arm64-validation-toolchain-venv
/tmp/arm64-validation-toolchain-venv/bin/python -m pip --version
git check-ignore build/toolchain_check.c build/toolchain_check.elf
```

Results: ELF64 little-endian AArch64 executable, statically linked, with debug
information; GDB detected `aarch64` and resolved `main` to source line 5. The
virtual environment provided Python 3.12 and pip 24.0. Both build artifacts were
confirmed ignored by Git. The temporary virtual environment is a setup check,
not the project's eventual dependency environment.

The executable was **not run**. At this stage no ARM64 target guest boot or CPU
validation test had occurred. Emulator capability listings alone do not establish
guest functionality.

### 8. First ARM64 Linux boot — complete

Initially drafted the fetcher, boot runner, and a proposed configuration, and
checked syntax/CLI help. The user subsequently approved Debian ARM64,
`virt-8.2`, Cortex-A72, TCG, two vCPUs, and 1 GiB RAM. Activated `config/boot.json`.

Assistant installed the boot prerequisites from PowerShell:

```powershell
wsl -d Ubuntu-24.04 -u root -- sh -c 'export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y --no-install-recommends qemu-efi-aarch64 cloud-image-utils'
```

Exit 0. Verified `qemu-efi-aarch64` version `2024.02-2ubuntu0.10`,
`cloud-image-utils` `0.33-1`, and dependency `genisoimage` `9:1.1.11-3.5`.
Verified `/usr/share/AAVMF/AAVMF_CODE.fd` and `AAVMF_VARS.fd` exist.

From the project directory inside Ubuntu, ran:

```sh
python3 scripts/fetch_image.py
python3 scripts/boot.py
```

Downloaded the dated official Debian 13 genericcloud ARM64 qcow2 image and
verified its pinned SHA-512. Initial bring-up exposed network wait, schema,
optional NIC ROM, serial diagnostic, and shutdown-ordering issues. Incremental
fixes and their retained failed-run evidence are documented in
`reports/2026-10-22-boot.md`. The runner now supplies isolated DHCP, validates
cloud configuration, emits structured guest observations, and lets cloud-init
finish before powering off. The host requires completion and rejects tracebacks.

For the final source revision `17f71af`, executed:

```sh
python3 build/verify_boot_milestone.py
python3 build/write_boot_report.py
```

These were ignored working verification/report helpers. The live check sequence
was missing image, corrupt image, paused-CPU timeout, recovery boot, and a second
fresh boot. All expected outcomes were checked, including exit codes, absence
of remaining QEMU processes, guest results, distinct nonces, and matching base
image/pristine firmware hashes. The base image was hashed again after all runs.
The reusable live check is now `python3 tests/verify_boot.py`; source promotion
and its additional diagnostic assertions are explained in the report.

The following checks exited 0 inside Ubuntu:

```sh
python3 -m py_compile scripts/boot.py scripts/fetch_image.py tests/verify_boot.py
python3 scripts/boot.py --help
python3 scripts/fetch_image.py --help
```

`git diff --check` passed. Syntax/CLI checks are separate from the live acceptance
results. The report helper additionally checked all final saved runner copies
against the current source SHA-256 and generated `reports/2026-10-22-boot.json`.
Full per-run logs and generated VM state remain local under ignored `artifacts/`.

During diagnosis, a failed overlay was converted to an ignored raw copy with
`qemu-img convert`; a read-only loop device at its root-partition offset and
`debugfs` were used to inspect cloud-init logs, then the loop device was detached.
The original base image and failed overlay were not modified by this inspection.

### 9. First C/assembly payload — complete, 2026-10-24

Added `payloads/isa_add_flags/main.c` and `add_flags.S`, a build helper, optional
deployment/execution/debug arguments to the boot runner, and payload protocol/live
acceptance checks. No new host packages, guest package downloads, SSH forwarding,
or hardware were required. The existing seed disk carries a gzip/base64 encoded
static ELF; Debian verifies its SHA-256 before execution.

From the project directory inside Ubuntu, executed:

```sh
python3 scripts/build_payload.py
aarch64-linux-gnu-objdump -d build/isa_add_flags/isa_add_flags.elf
python3 scripts/boot.py --payload --debug-payload
```

Build passed with warnings treated as errors. Disassembly verified ADDS/MRS/STR/RET.
The first debugger run failed a debug-step check while all six C cases passed.
The subsequent revision uses selected-vCPU stepping and checks PC progression.
Payload delivery was compressed using cloud-init's supported `gz+b64` encoding.

The corrected live-debug command exited 0: EL0 breakpoint, arguments 1 and 2,
ADDS sum 3 and flags 0, then MRS result 0. GDB detached and exited 0; all six
payload cases and boot checks passed. Detailed failed/successful transcripts
are retained in the report's artifact directories.

Executed the original `python3 scripts/boot.py` separately; it still passed
without requesting or executing a payload.

Then executed:

```sh
python3 -m unittest discover -s tests -p test_payload_protocol.py -v
python3 tests/verify_payload.py --debug-result /mnt/c/Users/Christopher/Documents/prj/arm_64_cpu_validation/artifacts/20261024T075708Z-02d28ef5/result.json
python3 tests/verify_debug_timeout.py
python3 build/write_payload_report.py
```

Six host protocol tests passed. Live acceptance reused the completed debug result,
then ran the intentional last-case failure (expected FAIL / Linux exit 1) and a
fresh recovery (six cases PASS / exit 0) using the identical binary. The separate
timeout test captured Linux exit 124, verified QEMU/GDB process absence and socket
cleanup, then returned 0 itself. An earlier direct PowerShell timeout invocation
also produced a TIMEOUT record but did not preserve the inner Linux shell exit;
the Python acceptance command above captures that code explicitly.

The ignored report helper checked fixed sums/NZCV, intentional corruption, source
snapshots, process absence, and the unchanged base image, then wrote
`reports/2026-10-24-payload.json`. Build/run evidence and commands are explained in
`PAYLOAD_WORKFLOW.md` and `reports/2026-10-24-payload.md`.

The original build-only C executable from step 7 remains unexecuted. The new
six-case C/assembly payload is the program actually deployed and executed here.

### 10. Memory-protection validation — pending

Agree one mmap/mprotect test with an expected child-process fault, then add it
incrementally. Interactive DUT access and general process-aware debugging remain
separate possible extensions.

## References

- [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [Microsoft WSL command reference](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
