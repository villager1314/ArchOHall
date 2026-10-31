#!/usr/bin/env python3
"""Run adapted upstream sudo/menu/path-alias helpers from the prepared source."""
from pathlib import Path
import argparse,os,subprocess,tempfile,json
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args();source=a.source.resolve()
setup=(source/'src/android/proot/setup.rs').read_text()
helpers=[]
for name in ['sync_default_menu','sync_guest_host_path_alias']:
    start=setup.index('pub fn '+name+'(');end=setup.index('\n}',start)+2
    helpers.append(setup[start:end])
module=json.dumps(str(source/'src/core/guest_sudo.rs'))
rust='''extern crate self as log;
#[macro_export] macro_rules! warn { ($($a:tt)*) => {{ let _ = format_args!($($a)*); }} }
use std::{fs,path::Path};
#[path = '''+module+'''] mod sudo;
'''+ '\n'.join(helpers)+r'''
fn tree(name:&str)->std::path::PathBuf {
 let p=std::env::temp_dir().join(format!("arch-access-{}-{}",std::process::id(),name));
 let _=fs::remove_dir_all(&p);fs::create_dir_all(&p).unwrap();p
}
#[test] fn arch_sudo_idempotent_and_preserves_user_policy() {
 use std::os::unix::fs::PermissionsExt;
 let r=tree("sudo");for p in ["etc/sudoers.d","usr/bin"] {fs::create_dir_all(r.join(p)).unwrap();}
 fs::write(r.join("etc/passwd"),"root:x:0:0::/root:/bin/bash\narch:x:1001:1001::/home/arch:/bin/bash\n").unwrap();
 fs::write(r.join("etc/group"),"root:x:0:\nsudo:x:27:\n").unwrap();
 fs::write(r.join("etc/gshadow"),"sudo:!::\n").unwrap();fs::write(r.join("usr/bin/sudo"),"fixture").unwrap();
 let report=sudo::sync_sudo_access(&r);assert!(report.failed.is_empty(),"{:?}",report.failed);
 assert!(fs::read_to_string(r.join("etc/group")).unwrap().contains("sudo:x:27:arch"));
 assert!(fs::metadata(r.join("usr/bin/sudo")).unwrap().permissions().mode()&0o4000!=0);
 let policy=r.join(sudo::SUDOERS_DROPIN_RELATIVE);assert!(policy.exists());
 fs::set_permissions(&policy,fs::Permissions::from_mode(0o600)).unwrap();fs::write(&policy,"# user policy\n").unwrap();
 sudo::sync_sudo_access(&r);assert_eq!(fs::read_to_string(policy).unwrap(),"# user policy\n");fs::remove_dir_all(r).unwrap();
}
#[test] fn default_menu_repaired_without_overwriting_custom() {
 let r=tree("menu");let m=r.join("etc/xdg/menus");fs::create_dir_all(&m).unwrap();fs::write(m.join("plasma-applications.menu"),"fixture").unwrap();
 sync_default_menu(&r);assert_eq!(fs::read_link(m.join("applications.menu")).unwrap(),Path::new("plasma-applications.menu"));
 fs::remove_file(m.join("applications.menu")).unwrap();fs::write(m.join("applications.menu"),"custom").unwrap();sync_default_menu(&r);
 assert_eq!(fs::read_to_string(m.join("applications.menu")).unwrap(),"custom");fs::remove_dir_all(r).unwrap();
}
#[test] fn host_alias_idempotent() {
 let r=tree("alias");sync_guest_host_path_alias(&r);sync_guest_host_path_alias(&r);
 assert_eq!(fs::read_link(r.join(r.strip_prefix("/").unwrap())).unwrap(),Path::new("/"));fs::remove_dir_all(r).unwrap();
}
#[test] fn host_alias_never_overwrites_existing_data() {
 let r=tree("alias-custom");let alias=r.join(r.strip_prefix("/").unwrap());fs::create_dir_all(alias.parent().unwrap()).unwrap();fs::write(&alias,"custom").unwrap();
 sync_guest_host_path_alias(&r);assert_eq!(fs::read_to_string(alias).unwrap(),"custom");fs::remove_dir_all(r).unwrap();
}
'''
with tempfile.TemporaryDirectory(prefix='arch-access-compile-') as d:
    root=Path(d);(root/'test.rs').write_text(rust)
    subprocess.run([os.environ.get('RUSTC','rustc'),'--edition=2021','--test',str(root/'test.rs'),'-o',str(root/'test')],check=True)
    subprocess.run([str(root/'test')],check=True)
