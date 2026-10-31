//! Transactional installation of the existing, verified Arch GPU artifact.
use super::arch_fs;
use anyhow::{Context, Result};
use std::{
    fs,
    os::unix::fs::PermissionsExt,
    path::{Component, Path},
};
static TRANSACTION: std::sync::Mutex<()> = std::sync::Mutex::new(());
const LIVE: &str = "opt/archohall-mobile";
const OLD: &str = "opt/archohall-mobile.previous";
const WORK: &str = "opt/archohall-mobile.staging-root";
const TRIAL: &str = "opt/archohall-mobile.trial";
const DENIED: &str = "opt/archohall-mobile.denied";
const MARKER: &str = ".archohall2-gpu";

pub fn validate(dir: &Path) -> Result<()> {
    let base = dir
        .canonicalize()
        .with_context(|| format!("Resolve GPU directory {}", dir.display()))?;
    for p in [
        "lib/dri/kgsl_dri.so",
        "lib/drmshim.so",
        "lib/libEGL_mesa.so.0",
        "lib/libgbm.so.1",
        "bin/kwin_wayland",
        "share/glvnd/egl_vendor.d/50_mesa.json",
    ] {
        let file = dir
            .join(p)
            .canonicalize()
            .with_context(|| format!("Resolve GPU/KWin component {p}"))?;
        anyhow::ensure!(
            file.starts_with(&base) && file.is_file() && fs::metadata(&file)?.len() > 0,
            "Invalid GPU/KWin component {p}"
        );
    }
    let config: serde_json::Value = serde_json::from_slice(&fs::read(dir.join("share/glvnd/egl_vendor.d/50_mesa.json"))?)
        .context("Parse GPU EGL vendor configuration")?;
    anyhow::ensure!(config.pointer("/ICD/library_path").and_then(|v| v.as_str()) == Some("/opt/archohall-mobile/lib/libEGL_mesa.so.0"), "EGL configuration does not select the pinned Arch GPU");
    anyhow::ensure!(fs::metadata(dir.join("bin/kwin_wayland"))?.permissions().mode() & 0o111 != 0, "KWin binary is not executable");
    Ok(())
}
fn remove_tree(path: &Path) -> Result<()> {
    if !path.try_exists()? {
        return Ok(());
    }
    let m = fs::symlink_metadata(path)?;
    anyhow::ensure!(
        m.is_dir() && !m.file_type().is_symlink(),
        "Expected disposable GPU directory: {}",
        path.display()
    );
    fs::set_permissions(path, fs::Permissions::from_mode(0o700))?;
    for e in fs::read_dir(path)? {
        let p = e?.path();
        let m = fs::symlink_metadata(&p)?;
        if m.is_dir() && !m.file_type().is_symlink() {
            remove_tree(&p)?;
        } else {
            fs::remove_file(p)?;
        }
    }
    fs::remove_dir(path)?;
    Ok(())
}
fn copy_tree(from: &Path, to: &Path) -> Result<()> {
    fs::create_dir_all(to)?;
    for item in fs::read_dir(from)? {
        let item = item?;
        let src = item.path();
        let dst = to.join(item.file_name());
        let m = fs::symlink_metadata(&src)?;
        if m.file_type().is_symlink() {
            std::os::unix::fs::symlink(fs::read_link(&src)?, dst)?;
        } else if m.is_dir() {
            copy_tree(&src, &dst)?;
        } else if m.is_file() {
            fs::copy(src, dst)?;
        } else {
            anyhow::bail!("Unsupported installed component: {}", src.display());
        }
    }
    Ok(())
}
fn marker(dir: &Path) -> String {
    fs::read_to_string(dir.join(MARKER))
        .unwrap_or_default()
        .trim()
        .to_owned()
}

pub fn recover(root: &Path) -> Result<()> {
    arch_fs::directory(root, "opt", 0o755)?;
    let live = root.join(LIVE);
    let old = root.join(OLD);
    // A killed promotion after live -> previous must restore before any copy.
    if !live.try_exists()? && old.try_exists()? {
        fs::rename(&old, &live).context("Restore interrupted GPU promotion")?;
    }
    anyhow::ensure!(
        !fs::symlink_metadata(&live)?.file_type().is_symlink(),
        "GPU install directory cannot be a link"
    );
    if old.try_exists()? && validate(&old).is_ok() && validate(&live).is_err() {
        let failed = root.join("opt/archohall-mobile.failed");
        remove_tree(&failed)?;
        fs::rename(&live, &failed)?;
        fs::rename(&old, &live).context("Restore GPU after incomplete promotion")?;
    }
    Ok(())
}

pub fn install(root: &Path, payload: &[u8], identity: &str) -> Result<()> {
    let _guard = TRANSACTION.lock().map_err(|_| anyhow::anyhow!("GPU transaction lock poisoned"))?;
    use sha2::{Digest, Sha256};
    recover(root)?;
    let live = root.join(LIVE);
    let denied = fs::read_to_string(root.join(DENIED)).unwrap_or_default();
    if denied.trim() == identity {
        validate(&live).context("Rejected GPU version has no usable fallback")?;
        return Ok(());
    }
    if marker(&live) == identity && validate(&live).is_ok() {
        return Ok(());
    }
    anyhow::ensure!(
        format!("{:x}", Sha256::digest(payload)) == identity,
        "GPU payload hash mismatch"
    );
    let work = root.join(WORK);
    remove_tree(&work)?;
    fs::create_dir(&work)?;
    let candidate = work.join(LIVE);
    // Preserve the already built KWin and its data, never recompile it.
    copy_tree(&live, &candidate)?;
    let decoder = zstd::stream::read::Decoder::new(payload)?;
    let mut archive = tar::Archive::new(decoder);
    // Restrict this separate artifact to its declared install prefix. Symlinks
    // must stay inside the prefix; arbitrary rootfs links are not rewritten.
    for e in archive.entries()? {
        let e = e?;
        let path = e.path()?;
        anyhow::ensure!(
            !path.is_absolute()
                && path
                    .components()
                    .all(|c| matches!(c, Component::Normal(_) | Component::CurDir)),
            "Unsafe GPU archive path"
        );
        let clean: std::path::PathBuf = path
            .components()
            .filter(|c| !matches!(c, Component::CurDir))
            .collect();
        let prefix = Path::new(LIVE);
        anyhow::ensure!(
            clean.as_os_str().is_empty() || clean == Path::new("opt") || clean.starts_with(prefix),
            "GPU archive escapes declared prefix: {}",
            clean.display()
        );
        if e.header().entry_type().is_symlink() {
            let target = e.link_name()?.context("GPU link without target")?;
            anyhow::ensure!(
                !target.is_absolute(),
                "Absolute GPU link: {}",
                clean.display()
            );
            let mut resolved = clean.parent().context("Link parent")?.to_path_buf();
            for c in target.components() {
                match c {
                    Component::ParentDir => {
                        anyhow::ensure!(resolved.pop(), "GPU link escape");
                    }
                    Component::Normal(x) => resolved.push(x),
                    Component::CurDir => {}
                    _ => anyhow::bail!("Unsafe GPU link"),
                }
            }
            anyhow::ensure!(resolved.starts_with(prefix), "GPU link escapes prefix");
        }
    }
    let decoder = zstd::stream::read::Decoder::new(payload)?;
    crate::core::provisioning::unpack_runtime_entries(
        &mut tar::Archive::new(decoder),
        &work,
        |_| {},
    )?;
    validate(&candidate)?;
    arch_fs::write(&candidate, MARKER, identity.as_bytes(), 0o644)?;
    // Persist trial intent BEFORE promotion; a crash cannot silently confirm it.
    arch_fs::write(root, TRIAL, format!("{identity}\n0\n").as_bytes(), 0o644)?;
    remove_tree(&root.join(OLD))?;
    fs::rename(&live, root.join(OLD)).context("Preserve installed KWin/GPU")?;
    fs::rename(&candidate, &live).context("Promote validated GPU tree")?;
    fs::File::open(root.join("opt"))?.sync_all()?;
    remove_tree(&work)?;
    Ok(())
}

pub fn before_launch(root: &Path) -> Result<()> {
    let _guard = TRANSACTION.lock().map_err(|_| anyhow::anyhow!("GPU transaction lock poisoned"))?;
    recover(root)?;
    let trial = root.join(TRIAL);
    if !trial.try_exists()? {
        return Ok(());
    }
    let content = fs::read_to_string(&trial)?;
    let mut lines = content.lines();
    let id = lines.next().context("Missing GPU trial identity")?;
    if marker(&root.join(LIVE)) != id {
        fs::remove_file(trial)?;
        return Ok(());
    }
    let count: u32 = lines.next().context("Missing GPU trial counter")?.parse()?;
    if count >= 3 {
        validate(&root.join(OLD)).context("GPU failed to show a desktop in three attempts; no validated previous GPU is available")?;
        arch_fs::write(root, DENIED, id.as_bytes(), 0o644)?;
        // Keep failed tree until the atomic replacement can be completed.
        let failed = root.join("opt/archohall-mobile.failed");
        remove_tree(&failed)?;
        fs::rename(root.join(LIVE), &failed)?;
        recover(root)?;
        fs::remove_file(trial)?;
        return Ok(());
    }
    arch_fs::write(
        root,
        TRIAL,
        format!("{id}\n{}\n", count + 1).as_bytes(),
        0o644,
    )
}
pub fn confirm(root: &Path) -> Result<()> {
    let _guard = TRANSACTION.lock().map_err(|_| anyhow::anyhow!("GPU transaction lock poisoned"))?;
    let trial = root.join(TRIAL);
    if !trial.try_exists()? {
        return Ok(());
    }
    let text = fs::read_to_string(&trial)?;
    anyhow::ensure!(
        text.lines().next() == Some(marker(&root.join(LIVE)).as_str()),
        "GPU readiness identity mismatch"
    );
    validate(&root.join(LIVE))?;
    fs::remove_file(trial)?;
    // Keep .previous for explicit recovery; remove only when next update starts.
    Ok(())
}
