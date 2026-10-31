//! Arch-only setup: never install Debian libraries or invoke APT repair.
use crate::android::runtime::proot::PRootRuntime;
use crate::core::{
    config::PRODUCTION_FS_ROOT,
    runtime::{LinuxRuntime, ProcessSpec},
};
use std::{fs, path::Path};

fn executable(root: &Path, path: &str, data: &str) -> anyhow::Result<()> {
    super::arch_fs::write(root, path, data.as_bytes(), 0o755)
}
pub fn sync(root: &Path) -> anyhow::Result<()> {
    anyhow::ensure!(
        root.join("etc/arch-release").exists(),
        "Arch rootfs required"
    );
    super::arch_gpu::install(
        root,
        include_bytes!("../../../assets/archohall2-gpu.tar.zst"),
        include_str!("../../../assets/archohall2-gpu.sha256").trim(),
    )?;
    executable(
        root,
        "usr/local/bin/startplasma-localdesktop",
        include_str!("../../../assets/archohall2-session.sh"),
    )?;
    executable(
        root,
        "usr/local/bin/archohall2-mobile-shell",
        include_str!("../../../assets/archohall2-mobile-shell.sh"),
    )?;
    executable(
        root,
        "usr/local/bin/archohall2-gpu-check",
        include_str!("../../../assets/archohall2-gpu-check.sh"),
    )?;
    executable(root, "usr/local/bin/archohall2-prepare", include_str!("../../../assets/archohall2-prepare.sh"))?;
    super::arch_fs::directory(root, "etc/archohall2", 0o755)?;
    let scale = root.join("etc/archohall2/output-scale");
    if !scale.exists() {
        fs::write(scale, "1.5\n")?;
    }
    super::setup::sync_guest_network_config(root);
    Ok(())
}
pub fn prepare() -> anyhow::Result<()> {
    let root = Path::new(PRODUCTION_FS_ROOT);
    sync(root)?;
    let result = PRootRuntime::active().execute(
        ProcessSpec::new("/bin/bash /usr/local/bin/archohall2-prepare").with_user("root"),
        None, None,
    );
    anyhow::ensure!(
        result.status.success(),
        "Arch login preparation failed ({}): stdout={} stderr={}",
        result.status, String::from_utf8_lossy(&result.stdout), String::from_utf8_lossy(&result.stderr)
    );
    Ok(())
}
pub fn verify_gpu() -> anyhow::Result<()> {
    let root = Path::new(PRODUCTION_FS_ROOT);
    super::arch_gpu::validate(&root.join("opt/archohall-mobile"))
}
