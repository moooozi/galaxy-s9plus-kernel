#!/usr/bin/env python3
"""Resolve the newest supported patch in the configured kernel series.

Emit a per-build source manifest. Consumers must use its resolved tag/commit
throughout the build, rather than querying again in individual jobs.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import urllib.request


def select_release(policy, metadata):
    if policy['policy'] != 'latest-supported-patch':
        raise ValueError('Unsupported kernel selection policy')
    if policy['series'] != '7.3' or 'upgrade_series' in policy:
        raise ValueError('Only the 7.3 series is supported; series upgrades are disabled')
    candidates = []
    for release in metadata['releases']:
        version = release.get('version', '')
        if not re.fullmatch(r'7\.3(?:\.[0-9]+)?', version):
            continue
        if release.get('iseol') is not False:
            continue
        if release.get('moniker') not in ('stable', 'longterm', 'mainline'):
            continue
        candidates.append(version)
    if not candidates:
        raise ValueError('No supported 7.3.x release; automatic series upgrades are disabled')
    return max(candidates, key=lambda version: tuple(map(int, version.split('.'))))


def resolve_tag(urls, tag):
    for url in dict.fromkeys(urls):
        try:
            output = subprocess.check_output(
                ['git', 'ls-remote', '--tags', url, f'refs/tags/{tag}',
                 f'refs/tags/{tag}^{{}}'], text=True, timeout=30)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        refs = dict(line.split()[::-1] for line in output.splitlines())
        commit = refs.get(f'refs/tags/{tag}^{{}}', refs.get(f'refs/tags/{tag}', ''))
        if re.fullmatch(r'[0-9a-f]{40}', commit):
            return commit, url
    raise RuntimeError(f'Could not resolve exact source commit for {tag}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path,
                        default=Path(__file__).with_name('kernel-source.json'))
    parser.add_argument('--floor', default='', help='Last published version; never downgrade')
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    with urllib.request.urlopen(policy['releases_url'], timeout=60) as response:
        metadata = json.load(response)
    version = select_release(policy, metadata)
    if args.floor and tuple(map(int, version.split('.'))) < tuple(map(int, args.floor.split('.'))):
        raise ValueError('Refusing to downgrade the published kernel series/version')
    tag = f'v{version}'
    commit, resolved_from = resolve_tag([*policy.get('mirrors', []), policy['url']], tag)
    print(json.dumps({**policy, 'version': version, 'tag': tag, 'commit': commit,
                      'resolved_from': resolved_from}, indent=2))


if __name__ == '__main__':
    main()
