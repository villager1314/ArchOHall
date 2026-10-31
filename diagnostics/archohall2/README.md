# ArchOHall2 experimental integration

This profile builds pinned Portal 9dff54c749c60b1eaf07e42b9f4e8de41e85af0a
under the independent Android ID `com.archohall2`, label ArchOHall2, version 0.1.0.
Internal Java/JNI names remain `app.polarbear`; these are not the application ID.
Portal attribution and GPL licensing are retained.

## Reused components

- Arch Mobile rootfs: successful run 41166047320, with installed-desktop checkpoint.
- KWin 6.8.2 Anland: successful run 41162670069, already included in that rootfs.
- Portal Android display/input transport and tawcroot/PRoot engines, reused unchanged.

Only the missing Arch KGSL Mesa and guest DRM shim are newly built. They use
lfdevs Mesa 98f3d6229d61452cef80f8563af7c56ae599dc14 plus the pinned Portal patches.
The GPU component, compiler work and Android Rust/SDK/Gradle work are cached.

## Boundaries adapted

- New application ID, label, private paths, launch manifest and disabled upstream APK feed.
- Explicit Arch distribution manifest, retaining resumable verified download and staged installation.
- Arch account UID/GID 1000, private runtime directory, machine identity and network configuration.
- Mobile session, matched KWin/QML/plugin paths, KGSL drivers, DRM shim and Anland broker binds.
- First-install appearance/scale applied directly to the isolated Arch home; no Debian desktop proof helper.
- Debian setup stages, optional app installers, APT updates, delayed installs, graphics repair and
  old KWin/framework/Mesa overlays are not used in this profile. Optional app choices are disabled.
- Runtime is separately hosted in a clearly experimental prerelease; APK is a workflow artifact.

## Test status

Source adaptation was exercised on a fresh pinned source copy. Workflow/shell/Python checks,
Rust parsing and the provisioning module/integration suites were run locally. Full ARM/Android
compilation is performed by `archohall2-test.yml`; only the final artifact checks can establish
APK identity. No device rendering, native task previews, audio, clipboard or lifecycle validation
has yet been performed for this new Arch combination. It is not a daily-use release.

The inherited Portal-specific desktop integrations (such as IBus, gaming tools, camera/audio
services and third-party app catalogue) are not all ported merely by replacing the rootfs.
The first APK is an isolated Mobile startup test; unsupported installers are blocked rather than
executing Debian commands against Arch. Never import existing Portal user data into it.
