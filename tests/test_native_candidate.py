import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_candidate', REPO/'scripts/verify-native-candidate.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class NativeCandidateTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.directory = Path(self.workspace.name)
        self.archive = self.directory/'archohall-native-007-aarch64.tar.xz'
        with tarfile.open(self.archive, 'w:xz') as bundle:
            info = tarfile.TarInfo('usr/local/bin/archohall-kwin-compat')
            info.size = 4
            bundle.addfile(info, io.BytesIO(b'test'))
        self.meta = {
            'version': '0.07', 'kwinSource': '1b798c05c19b1124edb1e16623191fcd2c128fd0',
            'sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            'packages': {name: '6.8.1-1' for name in ['kwin', 'plasma-mobile', 'qt6-base', 'qt6-declarative', 'qt6-wayland', 'kglobalacceld']},
            'buildInputs': {name: hashlib.sha256((REPO/'diagnostics/native007'/name).read_bytes()).hexdigest()
                            for name in ['patch-kwin.py', 'build-in-arch.sh', 'archohall-kwin-compat']},
        }
        (self.directory/'kwin-native-upstream-source.tar.gz').write_bytes(b'source-fixture')

    def verify(self, version='6.8.1-1'):
        (self.directory/'native-component.json').write_text(json.dumps(self.meta))
        with patch.object(candidate.subprocess, 'check_output', return_value='package '+version+'\n'):
            candidate.verify(self.directory/'root', self.directory, REPO)

    def test_reuse_matching_binary_with_current_runtime_tests(self):
        self.verify()

    def test_reject_changed_package_version(self):
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            self.verify(version='6.8.2-1')

    def test_reject_altered_archive(self):
        with self.archive.open('ab') as stream:
            stream.write(b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.verify()

    def test_reject_changed_compositor_build_inputs(self):
        self.meta['buildInputs']['patch-kwin.py'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'build inputs changed'):
            self.verify()
