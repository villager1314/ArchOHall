"""Check the set-id mechanism used to repair the guest's imported sudo binary."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

class SudoSimulationTests(unittest.TestCase):
    def test_setuid_executable_enters_simulated_root(self):
        proot = os.environ.get('ARCHOHALL_TEST_PROOT')
        if not proot or not Path(proot).is_file():
            if os.environ.get('ARCHOHALL_ALLOW_RESTRICTED_SOCKET_SKIP')=='1':
                self.skipTest('Local proot unavailable; CI must run identity test')
            self.fail('CI must build the checksum-locked Termux PRoot fork with android/test_proot.sh')
        with tempfile.TemporaryDirectory(prefix='archohall-setuid-') as d:
            executable=Path(d)/'id'
            shutil.copy2(shutil.which('id'),executable)
            executable.chmod(0o755)
            normal=subprocess.run([proot,'-i','1000:1000',str(executable),'-u'],capture_output=True,text=True,timeout=10)
            self.assertEqual(normal.returncode,0,normal.stderr)
            self.assertEqual(normal.stdout.strip(),'1000')
            executable.chmod(0o4755)
            elevated=subprocess.run([proot,'-i','1000:1000',str(executable),'-u'],capture_output=True,text=True,timeout=10)
            self.assertEqual(elevated.returncode,0,elevated.stderr)
            self.assertEqual(elevated.stdout.strip(),'0')
