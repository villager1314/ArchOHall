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
    // Reuse Portal's portable session/bridge implementations from its pinned source.
    super::setup::sync_guest_session_directories(root)?;
    for (path, data) in [
        ("usr/local/bin/localdesktop-startplasma-upstream", include_str!("../../../assets/archohall2-upstream-launcher.sh")),
        ("usr/local/bin/kwin_wayland", include_str!("../../../assets/localdesktop-kwin-wrapper-v2.sh")),
        ("usr/local/bin/localdesktop-clipboard-sync", include_str!("../../../assets/localdesktop-clipboard-sync.sh")),
        ("usr/local/bin/localdesktop-clipboard-push", include_str!("../../../assets/localdesktop-clipboard-push.sh")),
        ("usr/local/bin/portal-ime-bridge", include_str!("../../../assets/portal-ime-bridge.py")),
        ("usr/local/lib/portal/input-method-env.sh", include_str!("../../../assets/portal-input-method-env.sh")),
        ("usr/local/bin/portal-ibus-engine", include_str!("../../../assets/portal-ibus-engine.py")),
        ("usr/local/bin/portal-ibus-lazy", include_str!("../../../assets/portal-ibus-lazy.sh")),
        ("usr/local/sbin/portal-system-services", include_str!("../../../assets/portal-system-services.sh")),
        ("usr/local/bin/start-localdesktop-recovery", include_str!("../../../assets/localdesktop-recovery.sh")),
        ("usr/local/bin/localdesktop-retry-plasma", include_str!("../../../assets/localdesktop-retry-plasma.sh")),
        ("usr/local/lib/portal/portal-flatpak-bwrap", include_str!("../../../assets/portal-flatpak-bwrap.py")),
    ] {
        let data = data.replace("@UI_SCALE@", "1").replace("@GDB_BACKTRACE@", "0");
        executable(root, path, &data)?;
    }
    super::arch_fs::write(root, "usr/share/ibus/component/portal.xml", include_bytes!("../../../assets/portal-ibus-component.xml"), 0o644)?;
    for path in ["etc/pipewire/client.conf.d/90-localdesktop-no-rt.conf", "etc/pipewire/client-rt.conf.d/90-localdesktop-no-rt.conf"] {
        super::arch_fs::write(root, path, include_bytes!("../../../assets/localdesktop-pipewire-client-no-rt.conf"), 0o644)?;
    }
    // Original ARM64 leaf executables are reused, then ABI-checked in the guest.
    // Never copy Debian Qt/KWin libraries over Arch's library directories.
    for (path, data) in [
        ("usr/local/bin/wl-copy", &include_bytes!("../../../assets/guest-arm64/wl-copy")[..]),
        ("usr/local/bin/wl-paste", &include_bytes!("../../../assets/guest-arm64/wl-paste")[..]),
    ] { super::arch_fs::write(root, path, data, 0o755)?; }
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

/// Check the same packaged native library before Smithay's wrapper can pass a
/// null context into C. Link repair alone must not turn corrupt data into SIGSEGV.
pub fn validate_host_keyboard() -> anyhow::Result<()> {
    use anyhow::Context;
    unsafe {
        let library = libloading::Library::new("libxkbcommon.so").context("Load packaged native XKB library")?;
        let new: libloading::Symbol<unsafe extern "C" fn(u32) -> *mut libc::c_void> = library.get(b"xkb_context_new\0")?;
        let context_unref: libloading::Symbol<unsafe extern "C" fn(*mut libc::c_void)> = library.get(b"xkb_context_unref\0")?;
        let keymap_new: libloading::Symbol<unsafe extern "C" fn(*mut libc::c_void, *const libc::c_void, u32) -> *mut libc::c_void> = library.get(b"xkb_keymap_new_from_names\0")?;
        let keymap_unref: libloading::Symbol<unsafe extern "C" fn(*mut libc::c_void)> = library.get(b"xkb_keymap_unref\0")?;
        let context = new(0);
        anyhow::ensure!(!context.is_null(), "Native XKB context creation failed; check XKB_CONFIG_ROOT and keyboard data");
        let keymap = keymap_new(context, std::ptr::null(), 0);
        if !keymap.is_null() { keymap_unref(keymap); }
        context_unref(context);
        anyhow::ensure!(!keymap.is_null(), "Native XKB default keymap could not be compiled");
    }
    Ok(())
}
