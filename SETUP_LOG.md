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

The executable was **not run**. No ARM64 target guest boot or CPU validation test
has occurred. Emulator capability listings do not establish guest functionality.

### 8. First ARM64 Linux boot — pending

Agree the guest image source and boot configuration, then implement the small
boot milestone from `TEST_PLAN.md`, retaining image provenance and boot evidence.

## References

- [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [Microsoft WSL command reference](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
