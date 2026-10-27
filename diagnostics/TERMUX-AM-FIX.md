# TermuxAm caller identity hotfix

ArchOHall keeps upstream Java namespaces but uses Android application ID
`com.archoh`. TermuxAm is loaded from its own compressed DEX APK. Text/path
relocation does not change its compiled caller-package constant, so Android
rejects storage broadcasts as an attempt to send as `com.termux`.

The small DEX launcher sets the upstream, public mutable
`FakeContext.PACKAGE_NAME` field to `com.archoh` before invoking upstream
`Am.main`. Arguments are forwarded unchanged; Java class names and the
original `am.apk` are preserved. The launcher requires an ArchOHall prefix.

The installer verifies the helper hash, keeps a backup of `bin/am`, adds the
helper to the classpath, and changes the command entry point. Both classpath
archives are read-only for Android 14+ dynamic-code loading requirements.

CI run 40474838354 verifies caller-field initialization, argument forwarding,
and refusal to run with the original Termux prefix; it builds a min-API-26
DEX helper. The installer was checked for backup preservation, repeated use,
and read-only archive permissions. Android permission behavior still needs
device validation.

Run `install-am-package-fix.sh` in ArchOHall, then run
`termux-setup-storage` again. Updating the `termux-am` package may replace its
wrapper; rerun this hotfix if necessary until it is integrated into a later
APK/runtime build.

Restore the original wrapper with:

```bash
cp -p "$PREFIX/bin/am.before-archohall-caller-fix" "$PREFIX/bin/am"
```
