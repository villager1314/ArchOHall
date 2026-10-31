#!/usr/bin/env python3
"""Apply the ArchOHall2 profile only to the pinned Portal source tree."""
import argparse
import shutil
import re
import subprocess
from pathlib import Path

PIN = '9dff54c749c60b1eaf07e42b9f4e8de41e85af0a'
p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
a = p.parse_args()
root = a.source.resolve()
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip() == PIN
here = Path(__file__).resolve().parent

def edit(name, before, after):
    path = root/name
    s = path.read_text()
    assert before in s, (name,before[:80])
    path.write_text(s.replace(before,after))

def function(name, signature, body):
    path=root/name
    s=path.read_text(); start=s.index(signature); brace=s.index('{', start)
    end=s.index('\n}',brace)+2
    path.write_text(s[:brace+1]+'\n'+body+'\n}'+s[end:])

edit('Cargo.toml', 'version = "2.7.0"', 'version = "0.1.0"')
edit('Cargo.lock', 'name = "localdesktop"\nversion = "2.7.0"', 'name = "localdesktop"\nversion = "0.1.0"')
# All transactional download/recovery code is retained, with explicit Arch identity.
shutil.copy2(here/'provisioning.rs',root/'src/core/provisioning.rs')
edit('src/core/provisioning.rs','assets/debian-runtime.json','assets/archohall2-runtime.json')
for name in ('manifest.yaml','manifest.debug.yaml'):
    s=(root/name).read_text()
    s=s.replace('package: app.polarbear.portal','package: com.archohall2').replace('package: app.polarbear\n','package: com.archohall2\n')
    s=s.replace('label: "Portal Debug"','label: "ArchOHall2"').replace('label: "Portal"','label: "ArchOHall2"')
    (root/name).write_text(s)
# Preserve app.polarbear Java/JNI class names: these are implementation names,
# independent of application ID. Data, intents and components use the new app ID.
edit('src/core/config.rs','/data/data/app.polarbear.portal/files','/data/data/com.archohall2/files')
edit('src/core/config.rs','/data/data/app.polarbear/files','/data/data/com.archohall2/files')
edit('src/core/config.rs','pub const DESKTOP_USER: &str = "desktop";','pub const DESKTOP_USER: &str = "arch";')
edit('src/core/config.rs','https://github.com/Retrorerr/Portal#readme','https://github.com/villager1314/ArchOHall#readme')
edit('src/core/runtime.rs','distro_name: "Debian 13 (Trixie) ARM64".to_string()','distro_name: "Arch Linux ARM + Plasma Mobile".to_string()')
edit('src/lib.rs','pub mod setup;','pub mod setup;\n        pub mod archohall2;')
setup='src/android/proot/setup.rs'
function(setup,'fn stages()', '''    vec![
        ("arch-runtime", Box::new(setup_debian_runtime)),
        ("renderer-mode", Box::new(setup_renderer_mode)),
        ("linux-sysdata", Box::new(simulate_linux_sysdata_stage)),
        ("machine-id", Box::new(setup_machine_id)),
        ("arch-mobile-session", Box::new(|_| Some(thread::spawn(|| {
            super::archohall2::prepare()
        })))),
    ]''')
function(setup,'pub fn sync_session_runtime_files(','''    super::archohall2::sync(fs_root).expect("Arch session sync failed");''')
function(setup,'pub fn try_sync_session_runtime_files(','''    let _ = ui_scale;
    super::archohall2::sync(fs_root)''')
function(setup,'pub fn prepare_desktop_login(','''    let _ = migrate_legacy;
    super::archohall2::prepare()''')
function(setup,'pub fn spawn_background_installs()', '    // Debian background installers are intentionally unavailable in this test.')
function(setup,'pub fn library_overlay_binds(', '    let _ = fs_root;\n    Vec::new()')
function(setup,'fn finalise_installation(','''    let _ = registration;
    super::archohall2::verify_gpu().map_err(|e| SetupFailure::from_detail(5, "arch-gpu", format!("{e:#}")))?;
    crate::core::provisioning::RuntimeArtifact::production()
        .mark_installation_complete(Path::new(PRODUCTION_FS_ROOT))
        .map_err(|e| SetupFailure::from_detail(6, "arch-installation", format!("{e:#}")))''')
function(setup,'fn prepare_committed_runtime(','''    let _ = registration;
    super::archohall2::prepare()
        .map_err(|e| SetupFailure::from_detail(0, "arch-runtime", format!("{e:#}")))''')
function(setup,'fn apply_initial_preferences_before_commit(','''    let _ = registration;
    let apply = || -> anyhow::Result<()> {
        let root = Path::new(PRODUCTION_FS_ROOT);
        fs::create_dir_all(root.join("etc/archohall2"))?;
        fs::write(root.join("etc/archohall2/output-scale"), plan.initial_output_scale_string())?;
        let appearance = resolve_initial_appearance(android_app, plan)?;
        let scheme = match appearance { AppliedAppearance::Dark => "BreezeDark", AppliedAppearance::Light => "BreezeLight" };
        fs::create_dir_all(root.join("home/arch/.config"))?;
        fs::write(root.join("home/arch/.config/kdeglobals"), format!("[General]\\nColorScheme={scheme}\\n"))?;
        Ok(())
    };
    apply().map_err(|e| SetupFailure::from_detail(5, "arch-preferences", format!("{e:#}")))''')
function(setup,'pub fn repair_enable_anland()', '    false // Debian graphics repair must never run against Arch.')
# Optional app/update actions cannot invoke Debian commands in this profile.
function('src/android/proot/optional_apps.rs','pub fn catalog()', '    optional_app_catalog(|_| Some("Unavailable in ArchOHall2 test; use pacman in Konsole".into()))')
function('src/android/proot/optional_apps.rs','pub fn request(', '    let _ = (app_id, install);\n    false')
function('src/android/proot/system_updates.rs','pub fn schedule_background_check(', '    let _ = android_app;')
function('src/android/proot/system_updates.rs','pub fn begin_update(', '    let _ = include_app;\n    false')
function('src/android/proot/system_updates.rs','pub fn ui_snapshot()', '    None')
function('src/android/app_update.rs','fn feed()', '    None // Never install the upstream Portal APK over this independent test.')
function('src/android/proot/setup.rs','fn queue_deferred_optional_apps()', '    // No Debian optional package work in ArchOHall2.')
# Mesa is built for Arch and installed inside this rootfs, so no Debian bind layer.
function('src/android/anland/mod.rs','pub fn session_binds()', '''    use crate::core::runtime::BindMount;
    let files = std::path::Path::new(crate::core::config::APP_FILES_ROOT);
    let mut binds = vec![BindMount::new(files.join("anland"), "/tmp/anland")];
    binds.extend(fake_drm_binds(files));
    binds.extend(fake_pci_binds(files));
    binds''')
function('src/android/anland/mod.rs','pub fn validate_launch_contract()', '    super::proot::archohall2::verify_gpu()')
# Avoid installing or trialing the Debian graphics downloader at launch.
edit('src/android/proot/launch.rs','crate::android::proot::mesa_layer::trial_before_launch();','// ArchOHall2 uses the pinned in-guest Arch GPU payload.')
# Clear distribution-specific error labels and obvious visible product strings.
for name in ('src/android/proot/launch.rs','src/android/proot/setup.rs'):
    q=root/name;s=q.read_text().replace('Debian runtime','Arch runtime').replace('persistent Debian desktop user','Arch desktop user').replace('Portal installed.','ArchOHall2 installed.');q.write_text(s)
for q in (root/'src/android/kotlin').rglob('*.kt'):
    s=q.read_text()
    s=re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: re.sub(r'\bPortal(?: Debug)?\b', 'ArchOHall2', m[0]), s)
    q.write_text(s)
for q in (here/'overlay').rglob('*'):
    if q.is_file():
        target=root/q.relative_to(here/'overlay');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(q,target)
print('Applied ArchOHall2 profile to pinned Portal source')
