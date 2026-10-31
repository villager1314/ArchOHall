#!/usr/bin/env python3
"""Validate the applied profile against a clean pinned Portal checkout."""
import argparse
from pathlib import Path
import re
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
a=p.parse_args()
root=a.source.resolve()
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()=='9dff54c749c60b1eaf07e42b9f4e8de41e85af0a'
for path in (root/'src/android/proot').glob('arch*.rs'):
    for name in re.findall(r'include_(?:str|bytes)!\(\s*"([^"]+)"',path.read_text()):
        target=path.parent/name
        assert target.is_file(), f'Missing embedded profile asset: {target}'
setup=(root/'src/android/proot/setup.rs').read_text()
a=setup.index('fn build_wayland_backend(')
b=setup.index('Compositor::new',a)
assert 'fix_xkb_symlink()' in setup[a:b]
assert 'validate_host_keyboard()' in setup[a:b]
assert 'let target_inside = target.as_path();' in setup
assert 'pub fn sync_guest_session_directories' in setup
assert 'pub fn sync_xwayland_overlay' in setup
launcher=(root/'assets/archohall2-upstream-launcher.sh').read_text()
for fragment in ['start_clipboard_bridge', 'audio_connects', 'reap_session', 'plasma-ready', 'start-localdesktop-recovery']:
    assert fragment in launcher, fragment
assert '/usr/bin/startplasma-wayland >>' not in launcher
assert 'kwin_wayland --exit-with-session /usr/local/bin/archohall2-mobile-shell' in launcher
wrapper=(root/'assets/localdesktop-kwin-wrapper-v2.sh').read_text()
assert '--inputmethod /usr/local/bin/portal-ime-bridge' in wrapper
assert '--no-lockscreen' not in wrapper
assert wrapper.count('/opt/archohall-mobile/bin/kwin_wayland --inputmethod /usr/local/bin/portal-ime-bridge') == 3
recovery=(root/'assets/localdesktop-recovery.sh').read_text()
assert recovery.index('command -v labwc') < recovery.index('\nwrite_recovery_autostart\n')
assert 'reason=missing-labwc action=android-error-screen' in recovery
assert 'QT_QPA_PLATFORM=offscreen /opt/archohall-mobile/bin/kwin_wayland --help' in wrapper
assert 'libkwin.so.6.3.6' not in wrapper
services=(root/'assets/portal-system-services.sh').read_text()
assert 'apt-get' not in services and 'dpkg-divert --' not in services
for file in ['archohall2-upstream-launcher.sh','localdesktop-startplasma.sh','localdesktop-kwin-wrapper-v2.sh','portal-system-services.sh','localdesktop-clipboard-sync.sh','localdesktop-clipboard-push.sh','localdesktop-recovery.sh']:
    subprocess.run(['bash','-n',str(root/'assets'/file)],check=True)
print('Clean prepared profile: embedded assets, XKB gates, reused bridges and scripts: PASS')

session=(root/'assets/archohall2-session.sh').read_text()
assert 'export KWIN_RENDER_NODES=/dev/dri/renderD128' in session
assert 'unset KWIN_DRM_DEVICES' in session
assert 'export KWIN_DRM_DEVICES=' not in session
