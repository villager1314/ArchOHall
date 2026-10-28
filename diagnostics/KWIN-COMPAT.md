# KWin X11 software-rendering experiment

> Historical compatibility experiment. In current 0.06 sessions only KWin uses QPainter; Plasma and the keyboard use llvmpipe OpenGL. The older Qt Quick software-session instruction below describes the initial experiment. See [Android 0.06](ANDROID-006.md).

The affected phone has KWin 6.8.1-2, Plasma Mobile/Workspace 6.8.1,
Mesa 26.2.5 and Qt 6.12.0. Its crash traces identified two separate failures:

1. `GpuManager` uses a null `UdevMonitor` when creating a socket notifier.
2. After guarding that call, `X11WindowedOutput` uses a null `RenderDevice`.

KWin 6.8.1's X11 backend does not advertise QPainter compositing. Its output
constructor unconditionally calls `backend->renderDevice()->drmDevice()`.
Changing Mesa's software driver does not supply that missing render device.

The compatibility experiment builds KWin **6.7.5**, which still has the X11
QPainter backend. It fixes monitor handling in the source and installs into
`/opt/archohall-kwin-compat`; pacman's system KWin package and Plasma packages
are retained. The wrapper selects QPainter and the existing Plasma session is
configured to use Qt Quick software rendering.

This is a diagnostic build. Decorations, screen locking, configuration modules,
tabbox, notifications, runners, activities and integration with the global
shortcut daemon are disabled. It is not a feature-equivalent replacement for
the system KWin. Global shortcut integration was disabled because the 6.7.5
code expects an interface header no longer provided by the current daemon.

The build starts from a signature-verified Arch Linux ARM base. Upstream KWin
is pinned to commit `ab7df7ccb7c6af20f4b279cd6220f7cd3d2267d7` (v6.7.5).
The release includes the upstream source, patch and build scripts, dependency
versions, logs and binary hashes.

CI starts a nested compositor on Xvfb, deliberately makes udev monitor
creation return null, and requires a Wayland client to complete a round trip.
It also requires the compositor to remain alive after the round trip. This
does not test Android's X server, actual frame presentation, Plasma Mobile,
touch input or performance. Android testing is still necessary.

The installer checks the application prefix and Qt Base, Declarative and
Wayland package versions before changing files. It verifies the binary archive
hash and backs up the existing diagnostic runner and Plasma session script.
Run it only in the ArchOHall terminal with the existing diagnostic setup.

To revert the script changes:

```bash
r="$PREFIX/../containers/archohall/usr/local/bin"
cp -p "$r/archohall-debug-runner.before-kwin-compat" "$r/archohall-debug-runner"
cp -p "$r/archohall-session.before-kwin-compat" "$r/archohall-session"
```

The compatibility files can remain under `/opt`; the restored runner no
longer selects them. The older udev guard experiment, if previously enabled,
is restored with that runner.
