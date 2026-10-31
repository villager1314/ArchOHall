use super::{arch_fs, arch_gpu};
use std::{
    fs,
    os::unix::fs::{symlink, PermissionsExt},
    path::Path,
};
fn base() -> tempfile::TempDir {
    let t = tempfile::tempdir().unwrap();
    fs::create_dir(t.path().join("opt")).unwrap();
    fs::create_dir(t.path().join("opt/archohall-mobile")).unwrap();
    t
}
fn valid(dir: &Path) {
    for p in [
        "lib/dri/kgsl_dri.so",
        "lib/drmshim.so",
        "lib/libEGL_mesa.so.0",
        "lib/libgbm.so.1",
        "bin/kwin_wayland",
        "share/glvnd/egl_vendor.d/50_mesa.json",
    ] {
        let p = dir.join(p);
        fs::create_dir_all(p.parent().unwrap()).unwrap();
        if p.ends_with("50_mesa.json") {
            fs::write(&p, br#"{"ICD":{"library_path":"/opt/archohall-mobile/lib/libEGL_mesa.so.0"}}"#).unwrap();
        } else { fs::write(&p, b"fixture").unwrap(); }
        if p.ends_with("kwin_wayland") { fs::set_permissions(&p, fs::Permissions::from_mode(0o755)).unwrap(); }
    }
}
fn payload(escape: bool) -> (Vec<u8>, String) {
    let mut b = tar::Builder::new(Vec::new());
    for (p, data) in [
        ("opt/archohall-mobile/lib/dri/kgsl_dri.so", &b"new-gpu"[..]),
        ("opt/archohall-mobile/lib/drmshim.so", &b"shim"[..]),
        ("opt/archohall-mobile/lib/libEGL_mesa.so.0", &b"egl"[..]),
        ("opt/archohall-mobile/lib/libgbm.so.1", &b"gbm"[..]),
        (
            "opt/archohall-mobile/share/glvnd/egl_vendor.d/50_mesa.json",
            br#"{"ICD":{"library_path":"/opt/archohall-mobile/lib/libEGL_mesa.so.0"}}"# as &[u8],
        ),
    ] {
        let mut h = tar::Header::new_gnu();
        h.set_size(data.len() as u64);
        h.set_mode(0o644);
        h.set_cksum();
        b.append_data(&mut h, p, data).unwrap();
    }
    if escape {
        let mut h = tar::Header::new_gnu();
        h.set_entry_type(tar::EntryType::Symlink);
        h.set_size(0);
        h.set_mode(0o777);
        h.set_link_name("/etc/passwd").unwrap();
        h.set_cksum();
        b.append_data(&mut h, "opt/archohall-mobile/lib/escape", &b""[..])
            .unwrap();
    }
    let bytes = zstd::stream::encode_all(&b.into_inner().unwrap()[..], 1).unwrap();
    use sha2::{Digest, Sha256};
    let id = format!("{:x}", Sha256::digest(&bytes));
    (bytes, id)
}
#[test]
fn readonly_sys_and_partial_retry() {
    let t = tempfile::tempdir().unwrap();
    for p in ["proc", "sys"] {
        fs::create_dir(t.path().join(p)).unwrap();
        fs::set_permissions(t.path().join(p), fs::Permissions::from_mode(0o555)).unwrap();
    }
    arch_fs::sysdata(t.path()).unwrap();
    fs::remove_file(t.path().join("proc/.sysctl_entry_cap_last_cap")).unwrap();
    arch_fs::sysdata(t.path()).unwrap();
    assert!(t.path().join("proc/.sysctl_entry_cap_last_cap").is_file());
}
#[test]
fn seed_symlink_does_not_write_host() {
    let t = tempfile::tempdir().unwrap();
    let outside = tempfile::tempdir().unwrap();
    fs::create_dir(t.path().join("proc")).unwrap();
    symlink(
        outside.path().join("target"),
        t.path().join("proc/.version"),
    )
    .unwrap();
    assert!(arch_fs::sysdata(t.path()).is_err());
    assert!(!outside.path().join("target").exists());
}
#[test]
fn directory_symlink_is_rejected() {
    let t = tempfile::tempdir().unwrap();
    let outside = tempfile::tempdir().unwrap();
    symlink(outside.path(), t.path().join("sys")).unwrap();
    assert!(arch_fs::sysdata(t.path()).is_err());
    assert!(!outside.path().join(".empty").exists());
}
#[test]
fn machine_id_readonly_and_absolute_dbus_link() {
    let t = tempfile::tempdir().unwrap();
    fs::create_dir(t.path().join("etc")).unwrap();
    fs::write(t.path().join("etc/machine-id"), "").unwrap();
    fs::set_permissions(
        t.path().join("etc/machine-id"),
        fs::Permissions::from_mode(0o444),
    )
    .unwrap();
    fs::create_dir_all(t.path().join("var/lib/dbus")).unwrap();
    symlink("/etc/machine-id", t.path().join("var/lib/dbus/machine-id")).unwrap();
    arch_fs::machine_id(t.path()).unwrap();
    let id = fs::read_to_string(t.path().join("etc/machine-id")).unwrap();
    arch_fs::machine_id(t.path()).unwrap();
    assert_eq!(
        id,
        fs::read_to_string(t.path().join("var/lib/dbus/machine-id")).unwrap()
    );
}
#[test]
fn atomic_seed_does_not_mutate_hardlink_alias() {
    let t = tempfile::tempdir().unwrap();
    fs::create_dir(t.path().join("etc")).unwrap();
    fs::write(t.path().join("etc/original"), "old").unwrap();
    fs::hard_link(t.path().join("etc/original"), t.path().join("etc/config")).unwrap();
    arch_fs::write(t.path(), "etc/config", b"new", 0o644).unwrap();
    assert_eq!(fs::read(t.path().join("etc/original")).unwrap(), b"old");
}
#[test]
fn gpu_install_preserves_kwin_and_reuses_marker() {
    let t = base();
    fs::create_dir_all(t.path().join("opt/archohall-mobile/bin")).unwrap();
    fs::write(
        t.path().join("opt/archohall-mobile/bin/kwin_wayland"),
        "kwin",
    )
    .unwrap();
    fs::set_permissions(t.path().join("opt/archohall-mobile/bin/kwin_wayland"), fs::Permissions::from_mode(0o755)).unwrap();
    let (b, id) = payload(false);
    arch_gpu::install(t.path(), &b, &id).unwrap();
    assert_eq!(
        fs::read(t.path().join("opt/archohall-mobile/bin/kwin_wayland")).unwrap(),
        b"kwin"
    );
    arch_gpu::install(t.path(), b"unused cached archive", &id).unwrap();
}
#[test]
fn gpu_hash_or_link_failure_keeps_live() {
    let t = base();
    valid(&t.path().join("opt/archohall-mobile"));
    let (b, id) = payload(true);
    assert!(arch_gpu::install(t.path(), &b, "wrong").is_err());
    assert!(arch_gpu::install(t.path(), &b, &id).is_err());
    arch_gpu::validate(&t.path().join("opt/archohall-mobile")).unwrap();
}
#[test]
fn interrupted_promotion_restores_previous() {
    let t = base();
    valid(&t.path().join("opt/archohall-mobile"));
    fs::rename(
        t.path().join("opt/archohall-mobile"),
        t.path().join("opt/archohall-mobile.previous"),
    )
    .unwrap();
    arch_gpu::recover(t.path()).unwrap();
    arch_gpu::validate(&t.path().join("opt/archohall-mobile")).unwrap();
}
#[test]
fn gpu_rolls_back_after_three_unconfirmed_launches() {
    let t = base();
    valid(&t.path().join("opt/archohall-mobile"));
    let (b, id) = payload(false);
    arch_gpu::install(t.path(), &b, &id).unwrap();
    for _ in 0..4 {
        arch_gpu::before_launch(t.path()).unwrap();
    }
    assert_eq!(
        fs::read(t.path().join("opt/archohall-mobile/lib/dri/kgsl_dri.so")).unwrap(),
        b"fixture"
    );
    arch_gpu::install(t.path(), &b, &id).unwrap();
    assert_eq!(
        fs::read(t.path().join("opt/archohall-mobile/lib/dri/kgsl_dri.so")).unwrap(),
        b"fixture"
    );
}
#[test]
fn readiness_confirms_only_current_trial() {
    let t = base();
    valid(&t.path().join("opt/archohall-mobile"));
    let (b, id) = payload(false);
    arch_gpu::install(t.path(), &b, &id).unwrap();
    arch_gpu::before_launch(t.path()).unwrap();
    arch_gpu::confirm(t.path()).unwrap();
    assert!(!t.path().join("opt/archohall-mobile.trial").exists());
    for _ in 0..4 {
        arch_gpu::before_launch(t.path()).unwrap();
    }
    assert_eq!(
        fs::read(t.path().join("opt/archohall-mobile/lib/dri/kgsl_dri.so")).unwrap(),
        b"new-gpu"
    );
}
#[test]
fn first_gpu_without_fallback_allows_retry_without_false_confirmation() {
    let t = base();
    fs::create_dir_all(t.path().join("opt/archohall-mobile/bin")).unwrap();
    fs::write(
        t.path().join("opt/archohall-mobile/bin/kwin_wayland"),
        "kwin",
    )
    .unwrap();
    fs::set_permissions(t.path().join("opt/archohall-mobile/bin/kwin_wayland"), fs::Permissions::from_mode(0o755)).unwrap();
    let (b, id) = payload(false);
    arch_gpu::install(t.path(), &b, &id).unwrap();
    for _ in 0..3 {
        arch_gpu::before_launch(t.path()).unwrap();
    }
    let trial = t.path().join("opt/archohall-mobile.trial");
    let before = fs::read(&trial).unwrap();
    for _ in 0..5 { arch_gpu::before_launch(t.path()).unwrap(); }
    assert_eq!(fs::read(&trial).unwrap(), before);
    assert!(!t.path().join("opt/archohall-mobile.denied").exists());
    assert!(fs::read_to_string(t.path().join("opt/archohall-mobile.recovery-status")).unwrap().contains("status=unconfirmed"));
    arch_gpu::validate(&t.path().join("opt/archohall-mobile")).unwrap();
    // A real missing current component must still block the launch.
    let library = t.path().join("opt/archohall-mobile/lib/dri/kgsl_dri.so");
    let bytes = fs::read(&library).unwrap();
    fs::remove_file(&library).unwrap();
    assert!(arch_gpu::before_launch(t.path()).is_err());
    fs::write(library, bytes).unwrap();
    arch_gpu::confirm(t.path()).unwrap();
    assert!(!trial.exists());
}
#[test]
fn corrupt_live_restores_valid_previous() {
    let t = base();
    valid(&t.path().join("opt/archohall-mobile"));
    let (b, id) = payload(false);
    arch_gpu::install(t.path(), &b, &id).unwrap();
    fs::remove_file(t.path().join("opt/archohall-mobile/lib/drmshim.so")).unwrap();
    arch_gpu::recover(t.path()).unwrap();
    assert_eq!(
        fs::read(t.path().join("opt/archohall-mobile/lib/dri/kgsl_dri.so")).unwrap(),
        b"fixture"
    );
}
