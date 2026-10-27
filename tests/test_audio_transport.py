"""Real cookie-authenticated PulseAudio transport; Android sink requires device QA."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]


class AudioTransportTests(unittest.TestCase):
    def test_guest_tcp_accepts_cookie_and_rejects_wrong_cookie(self):
        try:
            probe=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);probe.close()
        except PermissionError:
            if os.environ.get('ARCHOHALL_ALLOW_RESTRICTED_SOCKET_SKIP')=='1':
                self.skipTest('Executor forbids sockets; CI must execute the real audio test')
            raise
        if not shutil.which('pulseaudio') or not shutil.which('pactl'):
            self.fail('CI audio test requires pulseaudio and pactl')
        with tempfile.TemporaryDirectory(prefix='archohall-audio-') as d:
            root=Path(d)
            prefix=root/'prefix';(prefix/'tmp').mkdir(parents=True)
            task=root/'task';task.mkdir()
            bridge=root/'bridge';bridge.mkdir()
            bindir=root/'bin';bindir.mkdir()
            # The Android-only sink modules are replaced by a real PA null sink
            # on the CI host. Authentication and transport use real libpulse.
            daemon=shutil.which('pulseaudio')
            wrapper=bindir/'pulseaudio'
            wrapper.write_text('#!/bin/sh\nexec '+daemon+' "$@" --load="module-null-sink sink_name=archohall_test"\n')
            wrapper.chmod(0o755)
            script='''set -euo pipefail
pulse_pid=''; pulse_tcp_module=''
cleanup(){ [[ -z $pulse_pid ]] || kill "$pulse_pid" 2>/dev/null || true; }
trap cleanup EXIT
source "$AUDIO_SCRIPT"
[[ -n $ARCHOHALL_GUEST_PULSE_SERVER ]]
PULSE_SERVER="$ARCHOHALL_GUEST_PULSE_SERVER" pactl info
head -c 256 /dev/zero > "$TASK_DIR/wrong-cookie"
if PULSE_COOKIE="$TASK_DIR/wrong-cookie" PULSE_SERVER="$ARCHOHALL_GUEST_PULSE_SERVER" pactl info; then
    echo 'Wrong cookie was accepted' >&2
    exit 1
fi
PULSE_SERVER="$ARCHOHALL_GUEST_PULSE_SERVER" pactl list short sinks
'''
            env=dict(os.environ,PATH=str(bindir)+':'+os.environ['PATH'],PREFIX=str(prefix),TASK_DIR=str(task),HOST_BRIDGE=str(bridge),AUDIO_SCRIPT=str(REPO/'android/host-bridge/host-audio.sh'))
            result=subprocess.run(['bash','-c',script],env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr+(task/'audio.log').read_text())
            self.assertIn('archohall_test',result.stdout)
            self.assertEqual((task/'pulse-cookie').stat().st_mode&0o777,0o600)
            self.assertIn('tcp:127.0.0.1:',(bridge/'audio.env').read_text())
