#!/usr/bin/env python3
"""Inspect the binary Android manifest, not just the build configuration."""
import glob
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
apk=Path(sys.argv[1])
candidates=[shutil.which('aapt2'),shutil.which('aapt')]
for root in [os.getenv('ANDROID_HOME',''),os.getenv('ANDROID_SDK_ROOT',''),'/usr/local/lib/android/sdk',str(Path.home()/'.cache/xbuild')]:
    if root:
        candidates += glob.glob(root+'/**/aapt2',recursive=True)
aapt=next((p for p in candidates if p and os.access(p,os.X_OK)),None)
if not aapt: raise SystemExit('Cannot validate APK: aapt2 unavailable')
text=subprocess.check_output([aapt,'dump','badging',str(apk)],text=True)
assert "package: name='com.archohall2'" in text,text[:500]
assert "application-label:'ArchOHall2'" in text,text[:1000]
assert 'app.polarbear.PortalActivity' in text,'JNI-compatible launch Activity missing'
with zipfile.ZipFile(apk) as z:
    assert 'lib/arm64-v8a/liblocaldesktop.so' in z.namelist(),'ARM64 host library missing'
print('APK package, label, launch Activity and ARM64 library verified')
