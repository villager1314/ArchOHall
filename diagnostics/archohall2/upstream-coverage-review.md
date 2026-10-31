# Portal → ArchOHall2: second source coverage review

Upstream reference: `Retrorerr/Portal@9dff54c749c60b1eaf07e42b9f4e8de41e85af0a`.
Arch profile reviewed: `4af7aa2ef1474f0647f0acd40a9e70f31b670026`.
This review pauses builds. It documents missing integration; it does not claim
that the following items have already been repaired or run successfully.

## Why the previous review was insufficient

The profile replaces the 16-entry upstream setup list with five entries and
replaces 21 function bodies. Reviewing the new functions alone misses the
responsibilities removed along with the old bodies. A native keyboard crash
then exposed an omitted upstream step (`fix_xkb_symlink`). A passing 31-test
suite covers provisioning/filesystem/GPU transactions, not native XKB, the
complete desktop session, or Android input/media integrations.

## All 16 upstream setup stages

| Stage / function | Arch handling | Current assessment |
| --- | --- | --- |
| debian-runtime / setup_debian_runtime | Shared provisioning with explicit Arch identity | Adapted; actual device passed image commit |
| renderer-mode / setup_renderer_mode | Retained | Selection retained; Arch software fallback not validated |
| linux-sysdata / simulate_linux_sysdata_stage | arch_fs::sysdata | Adapted; actual device passed |
| machine-id / setup_machine_id | arch_fs::machine_id | Adapted; actual device passed |
| firefox-config / setup_firefox_config | Removed, no Arch counterpart | Browser compatibility/configuration missing |
| bwrap-shim / setup_fake_bwrap | Removed | Flatpak sandbox support cannot be claimed |
| system-services / setup_system_services | Removed | System D-Bus/polkit helper deployment missing |
| chromium-no-sandbox / setup_chromium_no_sandbox | Removed | Browser launcher adaptation missing; do not infer necessity without testing Arch packages |
| onboard-signal-fix / setup_onboard_signal_fix | Removed | Package-specific fix; check applicability, not an automatic transplant |
| mesa-kgsl-layer / setup_mesa_layer | arch_gpu plus embedded pinned payload | Adapted transaction; runtime rendering not yet validated |
| flatpak-gl / setup_flatpak_gl | Removed | Portal GL extension not installed; Flatpak GPU support absent |
| plasma-wayland / setup_plasma_wayland | Minimal scripts replace function | Incomplete: see nested session integration below |
| desktop-login / setup_desktop_login | archohall2::prepare + prepare shell | Adapted; removed UID-1000 assumption; real unprivileged login still needs validation |
| mozilla-firefox / setup_mozilla_firefox | Removed; package-based Arch desktop | Optional program installation intentionally different |
| optional-apps / setup_optional_apps | Catalog disabled | Intentional: Debian APT must not run on Arch |
| xkb-symlink / fix_xkb_symlink | Removed; future rootfs normalization does not repair current image | Confirmed omission on the native host input initialization path |

## Confirmed omissions and consequences

### 1. Native XKB repair is missing from both first-run and return paths (blocking)

`src/android/main.rs` sets the host `XKB_CONFIG_ROOT` to the guest
`usr/share/X11/xkb`. The host is outside tawcroot/PRoot. An absolute guest
symlink therefore resolves against Android, not the guest tree. Upstream
`fix_xkb_symlink` explicitly handles this case, but its implementation hardcodes
`/usr/share/xkeyboard-config-2`; any Arch replacement must inspect the actual
link and validate its confined target rather than copying that target blindly.

The supplied `archohall2-crash.txt` shows a native SIGSEGV at
`xkb_context_ref → xkb_keymap_new_from_names → Smithay add_keyboard →
Compositor::new → build_wayland_backend`. This proves the native XKB crash
location. It does not alone prove the exact installed link target or rule out
another libxkbcommon failure. Validation must precede all three backend creation
routes: initial setup completion, committed install launch, and provisional
initial-preferences handoff. Reintroducing a first-install-only stage is insufficient.

### 2. Session directory preparation was removed (launch risk)

`sync_guest_session_directories` creates `tmp/.X11-unix`, `tmp/.ICE-unix`,
`var/tmp` and sets sticky writable modes. `archohall2::prepare` only explicitly
creates the user runtime and state directories. `launch.rs` cleans the :1
socket but does not restore these directories. Missing prerequisites can affect
XWayland and X11/ICE clients; verify and repair independently of image defaults.

### 3. Clipboard integration stops at the host broker (functional omission)

Upstream `sync_portal_runtime_assets` installs `localdesktop-clipboard-sync`,
`localdesktop-clipboard-push`, and compatible wl-copy/wl-paste. Upstream
`localdesktop-startplasma.sh` starts the sync against KWin's inner Wayland socket.
The Arch profile preserves the host broker/environment but neither deploys nor
starts the corresponding Linux helpers. Retaining Android ClipboardBridge alone
is not end-to-end clipboard support. Do not copy Debian wl-clipboard binaries
without verifying Arch ABI or using compatible Arch packages.

### 4. Android IME integration lacks its guest endpoint (functional omission)

The host IME FIFO listener remains in `launch.rs`, but the profile replaces the
asset installer that deploys `portal-ime-bridge`, its environment helper and IBus
integration. The upstream KWin wrapper adds `--inputmethod .../portal-ime-bridge`;
the Arch KWin command does not. Fixing XKB enables native keyboard setup; it does
not restore Android text input, Unicode commits or focus routing by itself.

### 5. Audio session configuration is incomplete (functional omission)

The upstream runtime installer writes PipeWire non-realtime client configuration.
The upstream session launcher creates private-runtime aliases to `/tmp/pulse/native`
and `/tmp/pipewire-*` and checks audio availability. Those operations are absent
from the replacement Arch scripts. Android audio code being compiled is not
proof of guest audio connectivity. Inspect actual server transport and installed
Arch packages before adapting paths; unavailable RTKit in a container matters.

### 6. System services are silently optional in the retained runtime wrapper

`SESSION_WITH_SYSTEM_SERVICES` tests whether
`/usr/local/sbin/portal-system-services` is executable before starting/stopping it.
The stage and sync function that install it were removed. The session may still
launch with that helper absent, but system D-Bus/polkit-dependent operations are
not thereby implemented. Inspect the helper for Debian package paths and adapt
service initialization instead of running APT against Arch.

### 7. XWayland compatibility is not equivalent to upstream (graphics risk)

Upstream installs/selects a patched XWayland and sets its KGSL surfaceless path.
Arch's rootfs installs its distro `xorg-xwayland`; no matching patched XWayland
build is substituted. Keeping `XWAYLAND_FORCE_KGSL_SURFACELESS=1` does not add
support to a binary that lacks the patch. KWin/Wayland rendering and accelerated
X11 apps need separate acceptance tests. This may require a component build;
do not rebuild rootfs or Mesa merely to discover it.

### 8. Damage-hint producer is not connected (performance / compatibility risk)

Upstream's KWin wrapper conditionally preloads `anland-damage.so`; Android's
consumer listens on `damage.sock`. The Arch GPU bundle contains DRM shim but
not this interposer and the Arch session only preloads DRM shim. The retained
consumer still contains damage-hint pacing code. No corresponding producer was
found in the ported Anland backend in this workspace. This is not proof of a
first-frame failure, but pacing behavior cannot be assumed equivalent. The
interposer targets KWin 6.3.6, so its ABI must be reviewed for KWin 6.8.2.

### 9. Recovery is partial, even with GPU rollback

Upstream session assets include a recovery launcher, retry helper, KWin crash
wrapper/backtrace capture and shell supervision. Arch has session error markers,
process supervision and GPU transaction rollback, but no equivalent complete
recovery desktop or KWin backtrace wrapper. Native crashes also bypass Rust error
returns; the XKB crash demonstrates why filesystem tests are not enough.

### 10. Lower-priority desktop integrations are also not migrated

`sync_session_runtime_files` originally synchronizes Android timezone, locale/
default-app settings, profile compatibility and user-preserving migrations.
`setup_plasma_wayland` configures Konsole, non-systemd startup and lock handling.
Arch's direct KWin/Plasma Mobile entry bypasses some desktop-startup requirements,
but does not implement all these user-facing behaviors. Camera bridge, browser
launchers, wallet unlock and ping capability wrapper are further omitted assets;
review them by feature rather than silently counting them as supported.

## Replaced-function call-path audit

The 21 replaced bodies are grouped by responsibility (all covered):

- Setup list, sysdata, machine-id: retained/adapted as listed above.
- `sync_session_runtime_files`, `try_sync_session_runtime_files`: replacing the
  entire asset synchronizer removed bridges, session directories and policy repair.
- `prepare_desktop_login`: preserves non-root launch intention, but current
  account preparation is smaller than upstream service/cache/login validation.
- `finalise_installation`, `prepare_committed_runtime`: Arch image/GPU validation
  retained, but must also gate host XKB readiness on every launch.
- `apply_initial_preferences_before_commit`: scale/theme writes are not a proof
  that KWin accepted the settings; original full appearance proof is bypassed.
- `spawn_background_installs`, `queue_deferred_optional_apps`, optional app
  `catalog`/`request`, system update `schedule_background_check`/`begin_update`/
  `ui_snapshot`, app-update `feed`: intentionally disabled Debian/upstream APK
  update actions. Keep disabled until Arch-specific implementations exist.
- `library_overlay_binds`, `session_binds`: deliberately avoid Debian library
  overlays; preserve required Android transport/fake-node binds. Video/camera
  bind integration is not equivalent to upstream.
- `repair_enable_anland`: original repair action disabled; do not present it as
  functional recovery in product UI.
- `validate_launch_contract`: Arch component/env checks exist, but are not the
  same thing as native XKB initialization or successful presentation.

## Build/validation disposition

No new APK/GPU/rootfs build for this audit. Existing successful artifacts and
caches remain reusable. Repair host XKB and launch prerequisites first; then
adapt the paired host/guest endpoints for IME, clipboard and audio. Keep optional
browser/Flatpak features explicitly unsupported until tested. Add assertions that
removed upstream stages have a reviewed disposition and test native input with
the real packaged libxkbcommon/data before claiming launch coverage.
