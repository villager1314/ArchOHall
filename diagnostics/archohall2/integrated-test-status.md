# Integrated test APK candidate

This candidate combines the restored Portal session/bridge scripts with:

- Original `guest_sudo` logic, adapted to `arch` and a separate sudoers drop-in.
  The existing group allocation/idempotency/user-policy preservation logic is reused.
  Guest-side ownership repair covers sudo, configuration and plugin files.
- Original `sync_default_menu` and `sync_guest_host_path_alias` helpers.
- Existing XKB repair on every backend construction, keyboard-data checks and
  packaged native context/keymap validation before Smithay calls into C.
- Original system-services installer/rules, clipboard, IME/IBus and audio client
  policy; Arch-specific service locations and existing-account runtime directories.
- Original patched XWayland staging, with guest dependency/execution checks before
  choosing it; the original wrapper's hash selection/fallback remains.
- Reused ARM64 `anland-damage-68.so` from successful component run 41191063162.
  Its eight native Unix-socket tests and exact KWin symbol/relocation checks passed.
  The obsolete KWin 6.3 damage library is not loaded.

Checks before the build: 31 provisioning/transaction tests; four tests compiling
actual adapted upstream sudo/menu/alias functions; Linux native XKB broken-link
and repaired-keymap test; fresh pinned-source profile application; resource-name
inventory and generated Rust/shell/YAML checks. The build repeats these checks and
also checks all actual embedded files in the full Portal checkout.

Reuse: runtime run 41166047320, compositor run 41162670069, existing Mesa binary
cache/artifact, damage component run 41191063162, existing Rust/Gradle/xbuild caches.
No rootfs/KWin/Mesa/component rebuild is requested. Fixed APK signing and update
certificate verification stay enabled. A new test APK is required.

Scope limits: no on-device success claim before testing the APK. IBus/portal/
recovery helpers still depend on optional distro packages actually being present;
retaining a helper is not proof of a working microphone, camera, Flatpak or GUI
recovery compositor. The special Qt Widgets high-refresh and Steam stack-clean
preloads are deliberately outside this request and are not enabled. The original
software-rendering path is not certified for the Arch GPU bundle. Device checks
must separately cover desktop presentation, idle pacing, text input, clipboard,
audio, sudo escalation inside the guest, and X11 acceleration.
