"""Verify a failed source mirror cannot poison the next checkout."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('locked_source',Path(__file__).resolve().parents[1]/'fetch-locked-source.py')
source=importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

class LockedSource(unittest.TestCase):
    def test_failed_mirror_falls_back_to_exact_commit_in_clean_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            upstream=root/'upstream'
            subprocess.run(['git','init','-b','main',str(upstream)],check=True,capture_output=True)
            (upstream/'payload.txt').write_bytes(b'locked source\r\n')
            subprocess.run(['git','-C',str(upstream),'-c','core.autocrlf=false','add','.'],check=True)
            subprocess.run(['git','-C',str(upstream),'-c','commit.gpgsign=false','-c','user.name=Fixture',
                            '-c','user.email=fixture@example.invalid','commit','-m','Source fixture'],check=True,capture_output=True)
            commit=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
            destination=root/'exported'
            source.export(str(upstream),commit,destination,mirrors=[str(root/'unavailable')])
            self.assertEqual((destination/'payload.txt').read_bytes(),b'locked source\n')
            self.assertFalse(destination.with_name('exported.git-source').exists())
