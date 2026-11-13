#!/usr/bin/env python3
"""Fetch a reviewed commit and export source with Unix text line endings."""
import argparse
import os
import signal
import re
import shutil
import subprocess
from pathlib import Path


def export(url, commit, destination, mirrors=()):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A full source commit is required')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    # A Linux tree fetch can take several minutes to generate/transfer its
    # shallow pack. Give it time, and kill the complete git/index-pack group
    # before discarding a failed checkout and trying the next mirror.
    checkout = destination.with_name(destination.name + '.git-source')
    if checkout.exists():
        raise FileExistsError(checkout)
    urls = dict.fromkeys([*mirrors, url])
    for candidate in urls:
        subprocess.run(['git', '-c', 'core.autocrlf=false', 'init', str(checkout)],
                       check=True, stdout=subprocess.DEVNULL)
        command = ['git', '-C', str(checkout), 'fetch', '--no-tags', '--depth=1', candidate, commit]
        process = subprocess.Popen(command, start_new_session=True)
        try:
            status = process.wait(timeout=900)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            status = -1
        if status == 0:
            break
        shutil.rmtree(checkout)
    else:
        raise RuntimeError('Could not fetch the locked commit from upstream or its mirrors')
    actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'FETCH_HEAD'], text=True).strip()
    if actual != commit:
        raise ValueError(f'Wrong source commit: {actual}')
    destination.mkdir(parents=True)
    with subprocess.Popen(['git', '-C', str(checkout), 'archive', actual], stdout=subprocess.PIPE) as archive:
        subprocess.run(['tar', '-x', '-C', str(destination)], stdin=archive.stdout, check=True)
        if archive.wait():
            raise RuntimeError('git archive failed')
    for path in destination.rglob('*'):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if b'\r\n' in data and b'\0' not in data:
                path.write_bytes(data.replace(b'\r\n', b'\n'))
    shutil.rmtree(checkout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('commit')
    parser.add_argument('destination')
    args = parser.parse_args()
    export(args.url, args.commit, args.destination)
