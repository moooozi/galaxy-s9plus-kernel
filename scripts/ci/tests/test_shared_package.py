"""Validate shared package layout and BOOT hook without device access."""
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]


@unittest.skipUnless(shutil.which('dpkg-deb'), 'dpkg-deb required')
class SharedPackage(unittest.TestCase):
    def test_one_package_contains_hardware_helpers_without_owning_image_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / 'bundle'
            bundle.mkdir()
            manifest = {'variant': 'unified', 'version': '7.3.4', 'revision': 2, 'release': '7.3.4-s9plus'}
            (bundle / 'kernel-manifest.json').write_text(json.dumps(manifest))
            for name in ('boot-s9plus.img', 'kernel.config', 'libwakelock-no-suspend.so'):
                (bundle / name).write_bytes(b'package test fixture')
            with tarfile.open(bundle / 'modules.tar.gz', 'w:gz') as archive:
                module = root / 'fixture.ko'
                module.write_bytes(b'not a real module')
                archive.add(module, arcname='usr/lib/modules/7.3.4-s9plus/extra/fixture.ko')
            out = root / 'packages'
            subprocess.run(['python3', str(REPO / 'scripts/ci/package-distributions.py'), str(bundle), str(out)], check=True, capture_output=True)
            deb = next(out.glob('*.deb'))
            self.assertEqual(deb.name, 'linux-s9plus_7.3.4-2_arm64.deb')
            payload = out / 'payload'
            for name in ('s9plus-cpuidle', 's9plus-audio', 's9plus-bluetooth', 's9plus-sensorhub', 's9plus-sensors', 's9plus-battery-settings'):
                self.assertTrue((payload / f'usr/lib/systemd/system/{name}.service').is_file())
                self.assertFalse((payload / f'etc/systemd/system/{name}.service').exists())
            self.assertFalse((payload / 'etc/s9plus/battery-preservation.json').exists())
            self.assertIn('pkgname=linux-s9plus\n', (out / 'apkbuild/APKBUILD').read_text())
            self.assertIn('/usr/share/s9plus-kernel/unified', (out / 'deb-root/DEBIAN/postinst').read_text())
            self.assertIn('linux-s9plus-full, linux-s9plus-embedding', (out / 'deb-root/DEBIAN/control').read_text())

    def test_legacy_bundle_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'kernel-manifest.json').write_text(json.dumps({'variant': 'embedding', 'version': '7.3.4', 'revision': 1, 'release': '7.3.4-s9plus-embedding'}))
            result = subprocess.run(['python3', str(REPO / 'scripts/ci/package-distributions.py'), str(root), str(root / 'out')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('invalid package metadata', result.stderr)
