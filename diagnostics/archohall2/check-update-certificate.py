"""Report whether the new debug APK can update the existing test install."""
import glob
import os
import re
import subprocess
import sys
from pathlib import Path
previous = next(Path(sys.argv[1]).rglob('*.apk'))
current = Path(sys.argv[2])
roots = [os.getenv('ANDROID_HOME', ''), '/usr/local/lib/android/sdk', str(Path.home()/'.cache/x')]
tools = [p for root in roots if root for p in glob.glob(root+'/**/apksigner', recursive=True) if os.access(p, os.X_OK)]
if not tools:
    raise SystemExit('Cannot verify APK update certificates: apksigner missing')
def digest(apk):
    text = subprocess.check_output([tools[0], 'verify', '--print-certs', str(apk)], text=True)
    return re.search(r'Signer #1 certificate SHA-256 digest: ([0-9a-f]+)', text).group(1)
old, new = digest(previous), digest(current)
print('previous_certificate_sha256='+old)
print('new_certificate_sha256='+new)
print('can_update_existing_install='+str(old == new).lower())
if old != new:
    print('Do not uninstall or clear app data. Back up the old debug app data before changing signing identity.')
