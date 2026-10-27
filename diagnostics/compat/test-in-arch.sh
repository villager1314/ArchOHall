#!/usr/bin/env bash
set -euo pipefail
mkdir -p /compat-results /tmp/compat-ci
ci_user=$(getent passwd 1000 | cut -d: -f1) || true
if [[ -z "$ci_user" ]]; then useradd -m -u 1000 compat-ci; ci_user=compat-ci; fi
chown 1000 /tmp/compat-ci
chmod 700 /tmp/compat-ci
# Reproduce unavailable udev monitoring without changing the runner kernel.
cat > /tmp/no-udev.c <<'EOF'
#include <stddef.h>
#include <unistd.h>
__attribute__((constructor)) static void ready(void) {
    static const char message[] = "ARCHOHALL_TEST_NO_UDEV_READY\n";
    (void)write(2, message, sizeof(message)-1);
}
void *udev_monitor_new_from_netlink(void *u, const char *s) {
    static const char message[] = "ARCHOHALL_TEST_UDEV_CREATION_BLOCKED\n";
    (void)write(2, message, sizeof(message)-1);
    (void)u; (void)s; return NULL;
}
EOF
gcc -fPIC -shared /tmp/no-udev.c -o /tmp/no-udev.so
Xvfb :77 -screen 0 720x1280x24 -ac -nolisten tcp > /compat-results/xvfb.log 2>&1 &
xpid=$!
kpid=''
cleanup() {
    if [[ -n "$kpid" ]]; then
        kill -TERM -- "-$kpid" 2>/dev/null || true
        wait "$kpid" 2>/dev/null || true
    fi
    kill "$xpid" 2>/dev/null || true
    wait "$xpid" 2>/dev/null || true
}
trap cleanup EXIT
ready=0
for ((i=0;i<100;i++)); do
    if xdpyinfo -display :77 >/dev/null 2>&1; then ready=1; break; fi
    sleep .1
done
((ready==1)) || { cat /compat-results/xvfb.log; exit 1; }
setsid runuser -u "$ci_user" -- env DISPLAY=:77 XDG_RUNTIME_DIR=/tmp/compat-ci \
    QT_QPA_PLATFORM=xcb dbus-run-session -- \
    env LD_PRELOAD=/tmp/no-udev.so /usr/local/bin/archohall-kwin-compat \
    --x11-display :77 --width 720 --height 1280 --socket archohall-compat-ci \
    > /compat-results/kwin.log 2>&1 &
kpid=$!
ready=0
for ((i=0;i<60;i++)); do
    if ! kill -0 "$kpid" 2>/dev/null; then break; fi
    if [[ -S /tmp/compat-ci/archohall-compat-ci ]]; then
        if runuser -u "$ci_user" -- env XDG_RUNTIME_DIR=/tmp/compat-ci \
            WAYLAND_DISPLAY=archohall-compat-ci timeout 5 wayland-info \
            > /compat-results/wayland-info.txt 2>&1; then
            ready=1; break
        fi
    fi
    sleep .5
done
cat /compat-results/kwin.log
((ready==1)) || { echo 'Nested software compositor did not respond to a Wayland client'; exit 1; }
grep -q ARCHOHALL_TEST_NO_UDEV_READY /compat-results/kwin.log
sleep 3
kill -0 "$kpid"
echo 'PASS: nested X11 software compositor answered a Wayland client with udev monitoring unavailable' | tee /compat-results/result.txt
