# KWin null UdevMonitor diagnostic workaround

The device backtrace identified a null-pointer crash in
`KWin::UdevMonitor::fd()` from `KWin::GpuManager::GpuManager()`, before the
Plasma session script ran. The reason monitor creation failed remains unknown.

`kwin-udev-guard.c` interposes exactly three exported member-function symbols.
For a null monitor it returns an invalid descriptor and skips filter/enable;
Qt leaves the invalid socket notifier disabled. Non-null calls are forwarded
with `dlsym(RTLD_NEXT)`. It does not provide GPU access, emulate udev devices,
or modify the installed KWin binary.

This is an opt-in experiment for the existing nested X11 diagnostic runner,
not a confirmed desktop fix. It requires dynamic symbol interposition in the
installed KWin build. If active on the failing call, its log contains
`ARCHOHALL_UDEV_GUARD: null UdevMonitor; hotplug monitoring disabled`.
An invalid-socket-notifier warning is expected with this experiment.

The ARM64 binary was built and tested on GitHub Actions run 40458696876 from
source commit c82071cc0b776a6e4c7264048432a341710b379c. The tests exercise null
handling and forwarding into a mock shared library built with real C++ member
symbols. Neither these tests nor a successful build verify phone behavior.

Run `install-udev-guard.sh` in the ArchOHall terminal. It checks the application
prefix, existing diagnostic runner, ARM64 architecture and downloaded binary
SHA256, then backs up and updates only the KWin preload in that runner.
Never set this glibc `LD_PRELOAD` on the Android host, PRoot, or all processes.

Restore the previous diagnostic runner with:

```bash
r="$PREFIX/../containers/archohall/usr/local/bin"
cp -p "$r/archohall-debug-runner.before-udev-guard" "$r/archohall-debug-runner"
```

The long-term fix belongs in KWin: check monitor creation before creating a
notifier and skip monitor filter/connect/enable when creation failed.
