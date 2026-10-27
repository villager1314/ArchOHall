# Android desktop support (0.05)

The Android app's **修复桌面组件与 Android 桥接** action installs managed guest files,
retains their previous versions as `.before-support-005`, applies quick-setting
overrides, and installs missing packages using the image's existing package databases.
Stop the desktop before running this action. It preserves the imported container.

## Implemented paths

| Feature | Implementation and scope |
| --- | --- |
| App icons / QML effects | KWin retains its QPainter compatibility backend; Plasma and the keyboard use OpenGL through Mesa llvmpipe. No Qt Quick raster backend or diagnostic window. |
| Virtual keyboard | Select the installed Plasma Keyboard (Maliit fallback) through KWin's `Wayland/InputMethod` setting. A wrapper gives the keyboard the same working Qt Quick renderer as Plasma. `KWIN_IM_SHOW_ALWAYS=1` and the nested-session input override allow touch represented as mouse input. An existing nonempty user-selected input method is preserved. |
| Audio output | Run the app-private PulseAudio process in foreground mode, expose only a private UNIX socket, try Android AAudio output then OpenSL ES. No microphone source is loaded. Failure is logged to `~/.archohall/audio.log` and does not abort the desktop. |
| Battery tile | Android battery broadcasts provide percentage and charging status; missing/stale data is shown as unknown. |
| Linux battery API / status bar | A read-only UPower facade runs on a separate container-local D-Bus and publishes the same Android snapshot. It does not claim the Android system bus, run a real power-management daemon, or invent battery energy/time estimates. |
| Wi-Fi, Bluetooth, cellular, airplane mode, hotspot | Display available Android state and open the corresponding Android panel/settings. Cellular status reports the active transport, not whether a data switch is enabled. Modern Android restrictions mean these are user-operated host controls, not NetworkManager/BlueZ devices in Linux. |
| Volume | Android media-volume dialog; Linux streams additionally use the bridged PulseAudio sink. |
| Brightness | Per-window Android brightness for the ArchOHall X11 Activity, exposed through a separate tile. No global WRITE_SETTINGS permission or nonworking PowerDevil slider. |
| Keep awake / warm tint | Affect only the ArchOHall X11 window. The warm tint is an overlay, not calibrated Night Color/gamma control. |
| Do not disturb | Open Android's notification-policy permission page until authorized; then toggle priority/all interruption filters on explicit clicks. |
| Screenshot / recording | ffmpeg X11 capture of the Linux desktop, avoiding the unsupported PipeWire/portal route. Save to `~/Pictures/ArchOHall` and `~/Videos/ArchOHall`. Recordings contain video only, not the Android display or microphone. |
| Android applications | Replace the uninitialized Waydroid tile with an explicit Android application launcher. It launches real host activities and does not emulate or claim to start Waydroid. |
| Power | Explicit stop-Linux-desktop confirmation. Does not power off or reboot the phone. |
| Dark mode, docked mode, auto-hide panels | Keep the upstream Linux controls. Keep the upstream Linux settings tile; Android settings is a separate additional tile. |

## Data path and lifecycle

The app publishes a versioned JSON snapshot and processes a fixed list of action
names beneath its private `home/.archohall/host-bridge` directory. PRoot binds
this one directory at `/run/archohall-host`. There is no TCP listener and no
arbitrary shell-command or arbitrary Android-intent endpoint. Requests are bounded,
atomically published, expire after 30 seconds, and have acknowledgements. Symlink
requests are rejected. These are same-application controls; the Linux environment
already shares the Android application's UID and is not a separate security boundary.

The guest treats a host snapshot older than 15 seconds as unavailable. The battery
facade waits for its private bus before announcing readiness; the desktop waits for
that readiness before Solid enumerates batteries. Normal missing-hardware warnings
from other Linux system services are not suppressed or disguised.

## Package installation and compatibility

Required packages: `plasma-keyboard`, `plasma-pa`, `python-dbus-fast`, `ffmpeg`,
`libnotify`. Plasma Keyboard may already be installed as a Plasma Mobile dependency;
an enabled virtual-keyboard tile alone does not prove its KWin input method is selected.

The installer performs a dry transaction and refuses to change Qt6, KF6, KWin,
libplasma, plasma-workspace or plasma-mobile. It does not run `pacman -Sy` or an
unattended full upgrade. A repository/ABI conflict must be resolved against the
retained compatibility build; a failure reports actual package errors instead of
marking uninstalled components as available.

For restoring upstream tiles and backed-up scripts, stop the desktop and run
`archohall-restore-desktop-support` inside the container. This does not uninstall
packages or delete user data. APK version 0.05 retains `com.archoh` and the retained
distribution key, so it is intended to overlay the fixed-signature 0.04 installation.

## Verification and remaining device checks

Tests cover fresh/stale battery data, battery state translation, private request
acknowledgements and action allowlisting, managed archive scope, plus real D-Bus
enumeration and property updates. Android sources are compiled against API 36 and
the APK build runs the existing importer/permission/JNI checks.

None of these checks substitutes for ARM64 Android hardware testing. Verify keyboard
focus in both Qt and GTK applications, AAudio/OpenSL ES output, battery updates while
charging, OEM settings-panel resolution, per-window brightness/tint, and X11 ffmpeg
readback on the actual device. If audio or readback fails, preserve `audio.log` or
`~/.cache/archohall/{screenshot,record}.log` rather than changing graphics drivers.

## Upstream references

- Plasma Keyboard nested-session setup: https://github.com/KDE/plasma-keyboard#troubleshooting
- Android Wi-Fi restrictions: https://developer.android.com/reference/android/net/wifi/WifiManager#setWifiEnabled(boolean)
- Android settings panels: https://developer.android.com/reference/android/provider/Settings.Panel
- UPower D-Bus API: https://upower.freedesktop.org/docs/UPower/
- Termux PulseAudio modules: https://github.com/termux/termux-packages/tree/master/packages/pulseaudio
