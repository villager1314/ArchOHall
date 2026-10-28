#!/usr/bin/env bash
set -euo pipefail
mkdir -p /native-results /tmp/native-ci
ci_user=$(getent passwd 1000 | cut -d: -f1)
chown 1000 /native-results /tmp/native-ci
chmod 700 /tmp/native-ci
cat > /tmp/no-udev.c <<'C'
#include <stddef.h>
void *udev_monitor_new_from_netlink(void *u, const char *s) { (void)u; (void)s; return NULL; }
C
gcc -fPIC -shared /tmp/no-udev.c -o /tmp/no-udev.so
Xvfb :77 -screen 0 720x1280x24 -ac -nolisten tcp > /native-results/xvfb.log 2>&1 &
xpid=$!
kpid=''
cleanup(){
    if [[ -n $kpid ]]; then kill -TERM -- "-$kpid" 2>/dev/null || true; fi
    kill "$xpid" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT
for ((i=0;i<50;i++)); do xdpyinfo -display :77 >/dev/null 2>&1 && break; sleep .2; done
if xdpyinfo -display :77 -queryExtensions | grep -q DRI3; then
    echo 'Expected a DRM-less Xvfb without DRI3'; exit 1
fi
setsid runuser -u "$ci_user" -- env DISPLAY=:77 XDG_RUNTIME_DIR=/tmp/native-ci QT_QPA_PLATFORM=xcb \
 XDG_CURRENT_DESKTOP=KDE LD_PRELOAD=/tmp/no-udev.so \
 timeout 130 dbus-run-session -- /usr/local/bin/archohall-kwin-compat \
 --x11-display :77 --width 720 --height 1280 --socket native-ci \
 --exit-with-session /opt/native007/test-session.sh > /native-results/kwin.log 2>&1 &
kpid=$!
wait "$kpid" || { cat /native-results/kwin.log; exit 1; }
cat /native-results/kwin.log
test -f /native-results/PASS
cat /native-results/PASS
