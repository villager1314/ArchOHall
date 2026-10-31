# Test build acceptance

Source: 8669f864444b2764827c685701b6b8430d77f262.

The user requested the test APK build after reviewing the adapted upstream methods.
Local checks rerun: 31 Rust regression tests and profile/shell/rootfs recipe checks passed.
Reuse the released runtime from run 41166047320, existing KWin, matching GPU payload,
and current Cargo/Gradle/xbuild caches. Keep the fixed ARCHOHALL_SIGNING_BUNDLE.
Do not rebuild or replace the released rootfs for this APK build.

Pending device acceptance: Android installation, KGSL rendering and real displayed desktop.
Software-rendering fallback and browser/Flatpak/VA-API acceleration are not certified.
