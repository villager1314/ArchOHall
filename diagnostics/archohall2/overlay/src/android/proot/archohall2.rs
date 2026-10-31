//! Arch-only setup: never install Debian libraries or invoke APT repair.
use std::{fs, path::Path, os::unix::fs::PermissionsExt};
use crate::core::{config::PRODUCTION_FS_ROOT, runtime::{LinuxRuntime, ProcessSpec}};
use crate::android::runtime::proot::PRootRuntime;

fn executable(root: &Path, path: &str, data: &str) -> anyhow::Result<()> {
    let path = root.join(path);
    fs::create_dir_all(path.parent().unwrap())?;
    fs::write(&path, data)?;
    fs::set_permissions(&path, fs::Permissions::from_mode(0o755))?;
    Ok(())
}
pub fn sync(root: &Path) -> anyhow::Result<()> {
    anyhow::ensure!(root.join("etc/arch-release").exists(), "Arch rootfs required");
    // Payload comes from this APK's pinned Arch build, not Portal's Debian Mesa.
    let marker = root.join("opt/archohall-mobile/.archohall2-gpu");
    let identity = include_str!("../../../assets/archohall2-gpu.sha256").trim();
    if fs::read_to_string(&marker).ok().as_deref() != Some(identity) {
        let payload = include_bytes!("../../../assets/archohall2-gpu.tar.zst");
        use sha2::{Digest, Sha256};
        anyhow::ensure!(format!("{:x}", Sha256::digest(payload)) == identity, "GPU payload hash mismatch");
        let decoder = zstd::stream::read::Decoder::new(&payload[..])?;
        tar::Archive::new(decoder).unpack(root)?;
        fs::write(&marker, identity)?;
    }
    executable(root, "usr/local/bin/startplasma-localdesktop", include_str!("../../../assets/archohall2-session.sh"))?;
    executable(root, "usr/local/bin/archohall2-mobile-shell", include_str!("../../../assets/archohall2-mobile-shell.sh"))?;
    fs::create_dir_all(root.join("etc/archohall2"))?;
    let scale = root.join("etc/archohall2/output-scale");
    if !scale.exists() { fs::write(scale, "1.5\n")?; }
    super::setup::sync_guest_network_config(root);
    Ok(())
}
pub fn prepare() -> anyhow::Result<()> {
    let root = Path::new(PRODUCTION_FS_ROOT);
    sync(root)?;
    let result = PRootRuntime::active().execute(ProcessSpec::new(
        "test \"$(id -u arch)\" = 1000 && test \"$(id -g arch)\" = 1000 && \
         chmod 0644 /etc/passwd /etc/group && \
         install -d -m 0700 -o 1000 -g 1000 /run/user/1000 /var/lib/localdesktop/session && \
         (test -f /home/arch/.archohall2-owned || \
          (chown -R 1000:1000 /home/arch && touch /home/arch/.archohall2-owned && chown 1000:1000 /home/arch/.archohall2-owned)) && \
         dbus-uuidgen --ensure=/etc/machine-id"
    ), None, None);
    anyhow::ensure!(result.status.success(), "Arch login preparation failed: {}", String::from_utf8_lossy(&result.stderr));
    Ok(())
}
pub fn verify_gpu() -> anyhow::Result<()> {
    let root = Path::new(PRODUCTION_FS_ROOT);
    for p in ["opt/archohall-mobile/lib/dri/kgsl_dri.so", "opt/archohall-mobile/lib/drmshim.so", "opt/archohall-mobile/bin/kwin_wayland"] {
        anyhow::ensure!(root.join(p).is_file(), "Missing Arch GPU component: {p}");
    }
    Ok(())
}
