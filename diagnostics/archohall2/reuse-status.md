# Reuse-first repair, source checkpoint

This source checkpoint follows the coverage audit. It does not trigger an APK
build and is not a device-validated completion declaration.

- Portable clipboard, IME/IBus, session launcher, system bus, KWin crash handling
  and recovery scripts come directly from the pinned Portal checkout.
- `reuse-upstream.py` makes asserted, limited changes to their component paths,
  dynamic account runtime directory, KWin version and Debian-only package hooks.
- The original setup session-directory helper is called again.
- The original atomic XKB symlink repair is restored before every Wayland backend
  construction, deriving the actual link target instead of assuming a fixed Arch
  data package name. Required keyboard files and the packaged native XKB context/
  keymap are checked before entering Smithay's unsafe native initialization path.
- Original wl-clipboard leaf binaries are reused with guest ABI checks. Arch's
  KWin/Qt/Mesa libraries are not replaced with Debian binaries.
- The original Android readiness proof, clipboard broker and IME FIFO listener
  remain authoritative. Asset deployment alone is not a functional acceptance test.

Local checks: 31 provisioning/transaction tests, profile/shell syntax, account-ID
checks, and adaptation of the actual pinned upstream shell assets. Full Android
linking and device behavior are pending. In particular, matching XWayland KGSL
patches, KWin damage-hint producer ABI, optional package prerequisites (IBus,
Flatpak and recovery compositor), and software rendering are still audit items.
No new rootfs, KWin or Mesa build was started for this checkpoint.
