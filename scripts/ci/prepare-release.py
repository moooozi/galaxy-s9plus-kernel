#!/usr/bin/env python3
"""Resolve once, refuse downgrade, skip an already-published package revision."""
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request


def get(path):
    request = urllib.request.Request('https://api.github.com/repos/' + os.environ['REPOSITORY'] + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


latest = get('/releases/latest')
floor = latest['tag_name'].removeprefix('v').split('-r')[0] if latest else ''
command = ['python3', 'scripts/ci/resolve-kernel.py']
if floor:
    command += ['--floor', floor]
selection = json.loads(subprocess.check_output(command, text=True))
revision = json.loads(Path('release-policy.json').read_text())['package_revision']
if not isinstance(revision, int) or revision < 1:
    raise ValueError('package_revision must be positive')
selection['revision'] = revision
tag = 'v' + selection['version'] + '-r' + str(revision)
exists = get('/releases/tags/' + tag) is not None
Path('dist/kernel-selection.json').write_text(json.dumps(selection, indent=2) + '\n')
with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
    output.write(f'build={str(not exists).lower()}\ntag={tag}\n')
print(f'{tag}: ' + ('already released' if exists else 'building the shared kernel'))
