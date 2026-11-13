"""Execute the kernel's actual hysteresis decision for every capacity value."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
REPO = Path(__file__).resolve().parents[3]
class Preservation(unittest.TestCase):
    def test_actual_c_hysteresis(self):
        source = (REPO / 'src/soc/max77705_charger.c').read_text()
        helper = re.search(r'static bool s9plus_charge_allowed\(.*?\n}\n', source, re.S)[0]
        checks = r"""
int main(void) {
    for (int c = -1; c <= 101; c++) {
        assert(s9plus_charge_allowed(c, 63, 65, false) == (c >= 0 && c <= 63));
        assert(s9plus_charge_allowed(c, 63, 65, true) == (c >= 0 && c < 65));
        assert(s9plus_charge_allowed(c, 78, 80, false) == (c >= 0 && c <= 78));
        assert(s9plus_charge_allowed(c, 78, 80, true) == (c >= 0 && c < 80));
        assert(s9plus_charge_allowed(c, 98, 100, false));
    }
    assert(!s9plus_charge_allowed(-1, 63, 65, true));
    assert(!s9plus_charge_allowed(101, 63, 65, true));
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'test.c'
            path.write_text('#include <stdbool.h>\n#include <assert.h>\n' + helper + checks)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(Path(d)/'test')], check=True)
            subprocess.run([str(Path(d)/'test')], check=True)
