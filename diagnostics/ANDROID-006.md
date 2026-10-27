# ArchOHall Android 0.06

## Distribution and migration

Deliver only a fixed-signature APK. Linux configuration remains maintained in
`rootfs/usr/local` as source, but no replacement rootfs image is required or built
for this update. `desktop-support.zip` embeds the managed guest files. The update
button deploys them, backs up existing scripts as `.before-support-006`, configures
the container, installs missing packages without upgrading installed versions,
and re-applies configuration for newly installed components. New imports receive
the same overlay. Existing user data, apps, home-screen layout and manually chosen
keyboard languages are preserved.

`archohall-configure` runs as simulated root before the user desktop and owns only:

- pacman PRoot download compatibility (`DownloadUser` disabled; `DisableSandbox`),
- the explicit `arch` passwordless sudo rule and the known sudo executable's setuid bit,
- app-managed PulseAudio client transport configuration (when supplied by the host),
- keyboard locale defaults only when unset, and Linux settings entry routes.

Configuration files are backed up as `.before-config-006`. SafeTar continues to
strip arbitrary imported set-id bits; only the installed sudo executable is
explicitly repaired. This is simulated container root, never Android root.

## Consolidated device fixes

- Keep KWin's retained QPainter compatibility build and exact verified 0.04 X11 JNI.
- Plasma/keyboard use llvmpipe OpenGL; no raster Qt Quick backend or diagnostic window.
- Default scale 1.5; rebuild the normal user's default sycoca before loading Folio.
- Set SHELL=/bin/bash before D-Bus/session startup.
- UPower BatteryLevel is NONE (1) when a numeric percentage is available, UNKNOWN (0)
  otherwise. Solid returns -1 for UNKNOWN even with a valid Percentage.
- Linux settings homepage directly launches the installed settings application;
  individual modules use kcmshell6, including the old mobile keyboard name alias.
- Host tile settingsCommand paths are absolute, so long presses use the same host
  action channel instead of resolving a Linux networking module.
- Notification titles use ArchOHall, and the terminal service notification returns
  to the control page. The launcher/control task and Linux desktop task have explicit
  separate affinities and names so both remain accessible in Android recent tasks.
- For compatibility KWin only, a session D-Bus receiver handles the task panel's
  existing `Mobile Task Switcher` shortcut and opens a Qt window list using KDE's
  TasksModel. Select activates a window; close closes that window; repeated square
  presses toggle the owned list. This does not require GL compositor effects or
  rebuilt KWin. The receiver never replaces an existing kglobalacceld service.
  This is a window list, not live thumbnail previews.

## Audio

The Android PulseAudio daemon remains foreground-owned by the desktop session.
Host management uses its private UNIX socket; guest audio uses a loopback-only TCP
module with a random 256-byte authentication cookie. The cookie is app-private and
bound as one file inside PRoot. Anonymous TCP authentication is disabled. Ports
47130–47140 are tried to avoid collisions. Stop unloads the owned TCP module and
terminates the owned daemon.

Both server shared memory and guest shared memory/memfd are disabled. Guest
PULSE_SERVER/PULSE_COOKIE and D-Bus activation environment are consistent. A guest
pactl connection is checked before desktop launch; failures go to audio.log rather
than being reported as successful just because Android has a sink. `libpulse` and
`alsa-plugins` support native PulseAudio and ALSA applications; an existing custom
.asoundrc is preserved. `archohall-audio-check --test` explicitly plays a short test
tone; startup does not play sound automatically.

AAudio with OpenSL ES fallback is retained. A null-sink CI authentication test
cannot verify physical speaker output, Bluetooth routing, device latency or OEM
AAudio behavior.

## New host controls and text clipboard

Brightness and media-volume tiles open Linux QML slider windows. Long press still
opens the Android control. Numeric messages are strictly bounded to 0–100; window
brightness remains scoped to the ArchOHall desktop, with a minimum of 2%.

`wl-paste --watch` sends Wayland text through the private acknowledged action
channel. Android decodes at most 256 KiB of valid UTF-8, writes ClipboardManager
only while the desktop is foreground, and ignores identical existing text. Existing
Android-to-X11 synchronization is retained. No clipboard text is printed to logs.
If KWin lacks the data-control protocol, the watcher reports failure and exits;
there is no claim that a successful Android-side parser test proves end-to-end
Wayland synchronization. Images, file clipboard and clipboard history are excluded.

## Verification

Python tests cover configuration idempotence/preference preservation, imported sudo
mode repair, package-upgrade refusal, bounded request and clipboard round trips,
real D-Bus UPower properties (including BatteryLevel), real PA cookie acceptance and
rejection, and PRoot setuid identity simulation. Java tests reject unknown/invalid
commands, numeric overflow and invalid/oversize UTF-8 clipboard payloads.

CI must run real socket/identity tests without the local executor skip flag, plus
Android unit tests/build, retained signature verification and X11 JNI checks.
The APK still requires ARM64 phone checks for audio playback, Wayland clipboard,
slider behavior, sudo, keyboard focus and per-OEM settings navigation.
