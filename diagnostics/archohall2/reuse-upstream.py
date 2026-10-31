#!/usr/bin/env python3
"""Adapt pinned Portal assets in place; keep their implementations authoritative."""
from pathlib import Path


def replace(path, before, after):
    text = path.read_text()
    if before not in text:
        raise ValueError(f'Upstream contract changed: {path.name}: {before[:70]}')
    path.write_text(text.replace(before, after))


def adapt(root):
    assets = root/'assets'
    launcher = assets/'localdesktop-startplasma.sh'
    replace(launcher, 'export XDG_RUNTIME_DIR=/run/user/1000', 'export XDG_RUNTIME_DIR="/run/user/$(id -u)"')
    replace(launcher, '${HOME:-/home/desktop}', '${HOME:-/home/arch}')
    replace(launcher, 'export LANG=en_GB.UTF-8', 'export LANG=C.UTF-8')
    replace(launcher, 'export XDG_DATA_DIRS="', 'export XDG_DATA_DIRS="/opt/archohall-mobile/share:')
    replace(launcher, 'dbus-run-session -- /usr/bin/startplasma-wayland', 'dbus-run-session -- /usr/local/bin/kwin_wayland --exit-with-session /usr/local/bin/archohall2-mobile-shell')
    # Keep bounded logging, clipboard startup, readiness wait, shutdown and recovery.
    (assets/'archohall2-upstream-launcher.sh').write_text(launcher.read_text())
    wrapper = assets/'localdesktop-kwin-wrapper-v2.sh'
    replace(wrapper, '/usr/bin/kwin_wayland', '/opt/archohall-mobile/bin/kwin_wayland')
    replace(wrapper, 'kwin_anland_dir=/usr/local/lib/portal-anland', 'kwin_anland_dir=/opt/archohall-mobile/lib')
    replace(wrapper, 'libkwin.so.6.3.6', 'libkwin.so.6.8.2')
    replace(wrapper, '/usr/local/lib/portal/anland-damage.so', '/usr/local/lib/portal/anland-damage-68.so')
    replace(wrapper, '/opt/archohall-mobile/bin/kwin_wayland --help', 'QT_QPA_PLATFORM=offscreen /opt/archohall-mobile/bin/kwin_wayland --help')
    # C crash/backtrace wrapper remains; only component locations/version change.
    services = assets/'portal-system-services.sh'
    replace(services, 'messagebus', 'dbus')
    replace(services, '/usr/libexec/flatpak-system-helper', '/usr/lib/flatpak-system-helper')
    replace(services, 'getent passwd 1000', 'getent passwd arch')
    # Debian package repair is replaced by distribution package ownership. The
    # service startup/shutdown, polkit and Flatpak runtime GL logic stay upstream.
    for signature in ['app_store() {', 'divert_fwupd_backend() {']:
        text = services.read_text(); start=text.index(signature); end=text.index('\n}',start)+2
        text=text[:start]+signature+'\n\t# Not applicable to Arch; never invoke dpkg/APT here.\n\treturn 0\n}'+text[end:]
        services.write_text(text)
    setup = root/'src/android/proot/setup.rs'
    # Reuse the existing atomic symlink repair, but derive the real Arch target.
    replace(setup, 'fn fix_xkb_symlink(_options: &SetupOptions)', 'pub fn fix_xkb_symlink()')
    replace(setup, 'let target_inside = Path::new("/usr/share/xkeyboard-config-2");', 'let target_inside = target.as_path();')
    replace(setup, 'fn sync_guest_session_directories(', 'pub fn sync_guest_session_directories(')

    replace(setup, 'fn sync_xwayland_overlay(', 'pub fn sync_xwayland_overlay(')

    replace(setup, 'fn sync_default_menu(', 'pub fn sync_default_menu(')
    replace(setup, 'fn sync_guest_host_path_alias(', 'pub fn sync_guest_host_path_alias(')
    replace(root/'src/core/guest_sudo.rs', 'pub const DESKTOP_USER: &str = "desktop";', 'pub const DESKTOP_USER: &str = "arch";')
    replace(root/'src/core/guest_sudo.rs', 'etc/sudoers.d/portal-desktop', 'etc/sudoers.d/archohall2-arch')

    replace(setup, 'fn sync_system_services(', 'pub fn sync_system_services(')
    replace(setup, '/usr/libexec/flatpak-system-helper', '/usr/lib/flatpak-system-helper')
