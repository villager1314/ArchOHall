# Arch component image extraction validation

The published Arch component tarball omits `etc/portal-runtime-version`.
Portal's image validation required it after successful extraction, producing
an unhelpful ENOENT after the previous hardlink fix.

For the explicit Arch profile, sealing freshly extracted, archive-hash-verified
staging validates the Arch layout and adds the absent manifest version file.
Existing version files are never overwritten. This does not mark installation
complete. Version/read failures now include their path/context.

Local validation used the actual published archive, not a rebuilt image:

- SHA-256: f445d6b4627dede1f274cffc6d176eb1c8468d0b1caeaf504fbc98c768a2800e
- Compressed size: 1165013112 bytes.
- Archive inventory: 162938 entries; 1835 hardlinks; all targets appeared first.
- Original archive identity file: absent.
- Full extraction through the amended Rust profile: passed.
- Result: REAL_ARCHIVE_EXTRACT_AND_IMAGE_VALIDATION_PASS.
- Image-ready validation passed; installation-complete remained false.
- Profile module suite: 19 passed, including missing/mismatched identity cases.

The local process had no effective Linux capabilities. This validates archive
handling and staging identity, not Android guest startup, graphics or SELinux
behavior beyond the explicit hardlink-to-file conversion.
