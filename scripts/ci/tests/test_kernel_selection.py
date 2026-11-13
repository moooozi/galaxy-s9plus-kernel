import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess
spec = importlib.util.spec_from_file_location('resolve_kernel', Path(__file__).resolve().parents[1] / 'resolve-kernel.py')
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)
POLICY = {'series': '7.3', 'policy': 'latest-supported-patch'}
def release(version, eol=False, moniker='stable'):
    return {'version': version, 'iseol': eol, 'moniker': moniker}
class KernelSelection(unittest.TestCase):
    def select(self, *releases):
        return resolver.select_release(POLICY, {'releases': releases})
    def test_numeric_patch_order(self):
        self.assertEqual(self.select(release('7.3.9'), release('7.3.10')), '7.3.10')
    def test_no_release_candidates(self):
        self.assertEqual(self.select(release('7.4-rc9', moniker='mainline'), release('7.3.4')), '7.3.4')
    def test_first_stable_74_does_not_switch(self):
        self.assertEqual(self.select(release('7.4', moniker='mainline'), release('7.3.99')), '7.3.99')
    def test_75_is_never_selected(self):
        self.assertEqual(self.select(release('7.5'), release('7.4.10'), release('7.3.4')), '7.3.4')
    def test_unsupported_or_eol_fails(self):
        with self.assertRaises(ValueError): self.select(release('7.4'), release('7.3.99', eol=True))
    def test_policy_cannot_expand_series(self):
        with self.assertRaises(ValueError): resolver.select_release(dict(POLICY, upgrade_series='7.5'), {'releases': [release('7.5')]})

class SourceResolution(unittest.TestCase):
    def test_timeout_falls_back_and_records_actual_source(self):
        commit = 'a' * 40
        with patch.object(resolver.subprocess, 'check_output', side_effect=[
                subprocess.TimeoutExpired(['git'],30), commit + '\trefs/tags/v7.3.4^{}\n']):
            self.assertEqual(resolver.resolve_tag(['mirror','upstream'],'v7.3.4'),(commit,'upstream'))
    def test_missing_tag_is_not_a_valid_source(self):
        with patch.object(resolver.subprocess, 'check_output', return_value=''):
            with self.assertRaises(RuntimeError):resolver.resolve_tag(['upstream'],'v7.3.4')

class PinnedSeries(unittest.TestCase):
    def test_74_only_metadata_stops_instead_of_upgrading(self):
        with self.assertRaisesRegex(ValueError,'No supported 7.3'):
            resolver.select_release(POLICY,{'releases':[release('7.4'),release('7.5')]})
    def test_series_cannot_be_changed_in_policy(self):
        with self.assertRaises(ValueError):
            resolver.select_release(dict(POLICY,series='7.4'),{'releases':[release('7.4')]})
