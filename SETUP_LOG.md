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

### 5. Verify Ubuntu — complete; normal user initialization pending

Assistant executed:

```powershell
wsl --list --verbose
wsl -d Ubuntu-24.04 -u root -- sh -c 'cat /etc/os-release; uname -m; uname -r; id; test -d /mnt/c/Users/Christopher/Documents/prj/arm_64_cpu_validation && echo PROJECT_DIRECTORY_ACCESS_OK'
```

Results: Ubuntu-24.04 registered as WSL version 2; Ubuntu 24.04.5 LTS;
`x86_64`; kernel `6.18.54.1-microsoft-standard-WSL2`; root verification session;
`PROJECT_DIRECTORY_ACCESS_OK`. This is the x86_64 Linux tool environment, not
the future ARM64 QEMU target guest. All verification commands exited 0.

An additional check found no UID 1000 user. Linux Python is present at
`/usr/bin/python3`; GCC and QEMU were not found on PATH. Normal user setup remains
pending. The user should open `wsl -d Ubuntu-24.04` in their own terminal and
complete the first-run username/password prompts. Passwords must remain private.

### 6. Install development tools — pending

Install and verify QEMU, AArch64 GCC, GDB, Make, and Linux Python after Ubuntu
initialization. Record exact commands and versions when executed.

## References

- [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [Microsoft WSL command reference](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
