# ArchOHall2 installation and graphics integration audit

Scope: experimental Portal profile, pinned upstream commit
`9dff54c749c60b1eaf07e42b9f4e8de41e85af0a`. This is a source and local regression
audit, not a claim that Android installation or Adreno rendering is validated.

## Artifact boundaries and reuse

| Artifact | Change | Existing binary reused? |
| --- | --- | --- |
| APK | Parent-first sysdata permissions; safe atomic config writes; idempotent machine-id; GPU transaction and readiness hooks | Existing Cargo/Gradle/xbuild caches retained; APK must eventually be rebuilt |
| rootfs | Future build recipe normalizes absolute links and writable initialization directories; GNU tar materializes hardlinks | Current released archive and checksum remain unchanged; no rootfs rebuild triggered |
| GPU | Install the existing verified payload into a staging tree, preserving compiled KWin; validate before promotion, retain previous tree | Mesa, DRM shim and KWin binaries unchanged; GPU build script/cache key unchanged |
| Session scripts | Guest dependency/KGSL checks, separate launch failure stages, supervised process group, original Android fenced readiness callback | Scripts are synchronized by APK; no desktop recompile |

The four deliverables have separate responsibilities. KWin is a compositor, not a
GPU driver; its files currently share `/opt/archohall-mobile` with the Mesa payload.
The GPU transaction therefore copies/preserves that installed prefix before overlaying
Mesa, instead of replacing it with a driver-only directory and losing KWin.

## Upstream measures and Arch handling

| Upstream measure | Arch profile handling / evidence |
| --- | --- |
| Package hardlinks materialized at build time | Existing APK unpacker materializes them; future rootfs packaging uses `--hard-dereference`; same unpacker now handles embedded GPU tar |
| Absolute package symlinks made relative | Future unmounted rootfs normalization; existing links are not indiscriminately deleted; host-owned writes reject linked destinations |
| Runtime version marker added by packager | Existing Arch-specific verified-staging identity adaptation retained; published archive identity unchanged |
| Image install uses staging and recoverable promotion | Retained; existing directory-order/hardlink tests continue to run |
| Linux sysdata initialization | Arch parent permissions fixed before creating `.empty`; each retry repairs all seeds rather than trusting one sentinel |
| Machine identity repair | Atomic replacement handles 0444 files, preserves valid identity, fixes D-Bus link without dereferencing guest absolute links on host |
| Pinned Mesa SHA-256 | Retained, checked before extraction; cache marker accepted only with critical component validation |
| Mesa staged update and fallback | Arch-specific transaction; interruption recovery, trial count, previous version retained, rejected version not automatically reinstalled |
| Driver confirmed only after a displayed native frame | Original `notify_desktop_ready` / Anland fenced-frame proof retained; only callback confirms Arch GPU trial |
| Unsupported GPU and software fallback | Hardware profile fails explicitly on missing/inaccessible KGSL; Smithay/QPainter and software Mesa fallback are NOT certified for this Arch profile |
| KGSL sync and submit patches | Existing pinned GPU recipe reuses upstream Mesa patch set; no new driver compilation required |
| Anland buffer/fence lifecycle | Upstream Android implementation unchanged |
| Startup environment contract | Explicit KGSL variables and actual guest preflight; ARM `ldd` and KWin `--anland` check run inside guest |
| Logs and child shutdown | Preflight has named stages; session logs persist; a process group supervises D-Bus/KWin; no deletion of live Wayland sockets |

First GPU installation has no known-good previous GPU. If three attempts never
show a desktop, it reports that no validated fallback exists; it does not label
an incomplete KWin-only directory a successful GPU rollback. A real previous
GPU is rolled back and its failed replacement is blocked from automatic reapply.
The previous tree is retained until the next update, not deleted at confirmation.

## Validation performed for this revision

- 31 Rust tests: 19 existing provisioning tests plus 12 Arch initialization/GPU
  transaction tests. Actual production helper modules are compiled by the harness.
- Readonly 0555 parents, partial retry, linked destination rejection, atomic write
  preserving a hardlink alias, 0444 machine-id and absolute D-Bus link repair.
- GPU hash/link rejection, KWin preservation, cached install reuse, interrupted
  promotion, corrupt live restoration, three-attempt rollback, readiness
  confirmation, first-install failure with no valid fallback.
- Shell syntax checks, profile Python parsing, future rootfs normalization and
  normalization idempotency.
- Profile applied to a fresh worktree of the exact upstream pin.
- Local Cargo target/dependency cache reused; no KWin/Mesa/rootfs rebuild.

Earlier full-archive extraction validation is recorded separately in
`extraction-validation.md`; it does not validate the new Android execution path.
This revision's tests use representative filesystem fixtures, not an Android VM.
The current host has no KVM, Android emulator or KGSL device. GPU ioctl behavior,
actual displayed frames, input/audio/clipboard, XWayland acceleration, and
real-device upgrade recovery remain device validation items. Upstream browser/
Flatpak/VA-API assumptions must not be advertised as working in Arch merely
because their upstream code is retained.

## How to reproduce lightweight checks

```sh
cargo test --manifest-path diagnostics/archohall2/tests/Cargo.toml --lib
python3 diagnostics/archohall2/check-profile.py
```

Run these before compiling the APK. The APK workflow includes both checks and
retains the existing cache keys. If the matching GPU binary cache expired, it first tries the original successful GPU artifact (run 41167326200), verifies its checksum, and builds only if neither reusable source is available. Future rootfs packaging normalization only runs
when the rootfs workflow is explicitly built later; it does not modify the
already released runtime or force existing users to download another image.

## Device follow-up: guest account preparation

The diagnostic export `localdesktop-diagnostics-1793437512356.zip` confirms that
sysdata and machine-id now complete, followed by a nonzero guest preparation
exit with no stderr. The previous compound shell command required UID and GID
1000 even though the rootfs recipe uses `useradd arch` without explicit IDs.
The export does not report the actual account IDs, so this is a confirmed code
assumption defect, not proof that this device's arch account is specifically 1001.
Preparation now reads the existing account's numeric IDs, uses them for ownership
and its private runtime directory, and reports stage, exit status, stdout and
stderr. The session computes the same runtime directory from its current UID.
Checks cover IDs 1000 and 1001 and rejection of a root-valued desktop identity.
No account renumbering, image replacement or GPU rebuild is required.
