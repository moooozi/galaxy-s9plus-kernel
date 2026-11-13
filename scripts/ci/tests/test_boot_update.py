"""Exercise BOOT validation and prove image assembly cannot write a partition."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
loader = importlib.machinery.SourceFileLoader('boot_update', str(REPO / 'packaging/runtime/usr/libexec/s9plus-install-boot'))
spec = importlib.util.spec_from_loader(loader.name, loader)
updater = importlib.util.module_from_spec(spec)
loader.exec_module(updater)


class BootUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.blob = b'ANDROID!' + b'\0' * 4096 + b'SEANDROIDENFORCE'
        (self.root / 'boot-s9plus.img').write_bytes(self.blob)
        self.manifest = {'variant':'unified', 'version':'7.3.4', 'release':'7.3.4-s9plus',
                         'boot_sha256':hashlib.sha256(self.blob).hexdigest()}
        self.write_manifest()
    def tearDown(self):
        self.tmp.cleanup()
    def write_manifest(self):
        (self.root / 'kernel-manifest.json').write_text(json.dumps(self.manifest))
    def test_image_build_never_opens_boot_partition(self):
        with patch.dict(os.environ, {'S9PLUS_IMAGE_BUILD':'1'}), patch.object(sys, 'argv', ['hook',str(self.root)]), patch.object(updater,'boot_partition',side_effect=AssertionError('must never run')):
            updater.main()
    def test_corrupt_boot_is_rejected_before_image_skip(self):
        (self.root / 'boot-s9plus.img').write_bytes(self.blob[:-16] + b'!' * 16)
        with self.assertRaises(ValueError): updater.verify_candidate(self.root)
    def test_checksum_is_required(self):
        self.manifest['boot_sha256'] = '0' * 64
        self.write_manifest()
        with self.assertRaises(ValueError): updater.verify_candidate(self.root)
    def test_cross_variant_kernel_is_rejected(self):
        self.manifest['release'] = '7.3.4-s9plus-full'
        self.write_manifest()
        with self.assertRaises(ValueError): updater.verify_candidate(self.root)

    def test_legacy_variant_is_rejected_even_with_matching_release(self):
        for variant in ('full', 'embedding'):
            self.manifest.update(variant=variant, release='7.3.4-s9plus-' + variant)
            self.write_manifest()
            with self.assertRaises(ValueError): updater.verify_candidate(self.root)
