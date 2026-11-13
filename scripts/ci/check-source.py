#!/usr/bin/env python3
"""Check kernel source/build tooling without touching a phone."""
import ast
import json
from pathlib import Path
import subprocess
REPO = Path(__file__).resolve().parents[2]
for directory in ('scripts', 'experiments', 'device', 'packaging'):
    for path in (REPO / directory).rglob('*'):
        if not path.is_file():
            continue
        if path.suffix == '.py' or path.name == 's9plus-install-boot':
            ast.parse(path.read_text(), filename=str(path))
        elif path.suffix == '.sh':
            subprocess.run(['bash', '-n', str(path)], check=True)
        elif path.suffix == '.json':
            json.loads(path.read_text())
subprocess.run(['python3', '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v'], cwd=REPO, check=True)
print('Kernel source and regression checks passed')
