//! Host operations on a guest tree: do not resolve guest links in Android's namespace.
use anyhow::{Context, Result};
use std::{
    fs,
    os::unix::fs::PermissionsExt,
    path::{Component, Path, PathBuf},
};

pub fn directory(root: &Path, relative: &str, mode: u32) -> Result<PathBuf> {
    let mut path = root.to_path_buf();
    for part in Path::new(relative).components() {
        let Component::Normal(part) = part else {
            anyhow::bail!("Invalid guest directory: {relative}")
        };
        path.push(part);
        match fs::symlink_metadata(&path) {
            Ok(m) => anyhow::ensure!(
                m.is_dir() && !m.file_type().is_symlink(),
                "Expected real directory: {}",
                path.display()
            ),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                fs::create_dir(&path).with_context(|| format!("Create {}", path.display()))?
            }
            Err(e) => return Err(e).with_context(|| format!("Inspect {}", path.display())),
        }
    }
    fs::set_permissions(&path, fs::Permissions::from_mode(mode))
        .with_context(|| format!("Set directory permissions: {}", path.display()))?;
    Ok(path)
}

// Rename a fresh file rather than truncating an existing hardlink or following a symlink.
pub fn write(root: &Path, relative: &str, bytes: &[u8], mode: u32) -> Result<()> {
    let relative = Path::new(relative);
    let parent = relative.parent().context("Missing parent")?;
    let dir = directory(root, parent.to_str().context("Non-UTF8 path")?, 0o755)?;
    let path = root.join(relative);
    if let Ok(m) = fs::symlink_metadata(&path) {
        anyhow::ensure!(
            m.is_file() && !m.file_type().is_symlink(),
            "Refusing non-regular destination: {}",
            path.display()
        );
    }
    let mut tmp = tempfile::NamedTempFile::new_in(&dir)?;
    use std::io::Write;
    tmp.write_all(bytes)
        .with_context(|| format!("Write {}", path.display()))?;
    tmp.as_file()
        .set_permissions(fs::Permissions::from_mode(mode))?;
    tmp.as_file().sync_all()?;
    tmp.persist(&path)
        .map_err(|e| e.error)
        .with_context(|| format!("Commit {}", path.display()))?;
    fs::File::open(&dir)?.sync_all().with_context(|| format!("Sync directory {}", dir.display()))?;
    Ok(())
}

pub fn sysdata(root: &Path) -> Result<()> {
    // Parent must become writable BEFORE creating sys/.empty.
    directory(root, "proc", 0o700)?;
    directory(root, "sys", 0o700)?;
    directory(root, "sys/.empty", 0o700)?;
    for (p, text) in [
        ("proc/.version", "Linux version 6.1.0-archohall2\n"),
        ("proc/.sysctl_entry_cap_last_cap", "40\n"),
        ("proc/.sysctl_inotify_max_user_watches", "4096\n"),
    ] {
        write(root, p, text.as_bytes(), 0o600)?;
    }
    // write() normalizes its parent for general config files; these bind-source
    // directories remain private after every attempt, including retries.
    directory(root, "proc", 0o700)?;
    Ok(())
}

pub fn machine_id(root: &Path) -> Result<()> {
    directory(root, "etc", 0o755)?;
    let path = root.join("etc/machine-id");
    if let Ok(m) = fs::symlink_metadata(&path) {
        anyhow::ensure!(
            m.is_file() && !m.file_type().is_symlink(),
            "Expected regular machine-id: {}",
            path.display()
        );
    }
    let current = fs::read_to_string(&path).unwrap_or_default();
    let id = current.trim();
    if !(id.len() == 32
        && id.bytes().all(|c| c.is_ascii_hexdigit())
        && id.bytes().any(|c| c != b'0'))
    {
        let id = fs::read_to_string("/proc/sys/kernel/random/uuid")
            .context("Generate machine-id")?
            .trim()
            .replace('-', "");
        write(root, "etc/machine-id", format!("{id}\n").as_bytes(), 0o444)?;
    }
    directory(root, "var/lib/dbus", 0o755)?;
    let link = root.join("var/lib/dbus/machine-id");
    match fs::symlink_metadata(&link) {
        Ok(m) if m.is_dir() => {
            anyhow::bail!("machine-id unexpectedly a directory: {}", link.display())
        }
        Ok(_) => {
            if fs::read_link(&link).ok().as_deref() == Some(Path::new("../../../etc/machine-id")) {
                return Ok(());
            }
            fs::remove_file(&link)?;
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => return Err(e.into()),
    }
    std::os::unix::fs::symlink("../../../etc/machine-id", link)?;
    Ok(())
}
