#!/usr/bin/env python3
"""Turn a verified kernel bundle into Debian payload and Alpine abuild input."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    bundle, out = args.bundle.resolve(), args.output.resolve()
    manifest = json.loads((bundle / 'kernel-manifest.json').read_text())
    variant, version = manifest['variant'], manifest['version']
    revision = str(manifest['revision'])
    if variant not in ('full', 'embedding') or not revision.isdecimal():
        raise ValueError('invalid package metadata')
    name = 'linux-s9plus-' + variant
    payload = out / 'payload'
    payload.mkdir(parents=True)
    # Producer owns this archive; still reject traversal, links and special files.
    with tarfile.open(bundle / 'modules.tar.gz') as archive:
        for item in archive.getmembers():
            if not item.isfile() or not item.name.startswith('usr/lib/modules/' + manifest['release'] + '/'):
                raise ValueError('invalid module archive member: ' + item.name)
        archive.extractall(payload, filter='data')
    target = payload / 'usr/share/s9plus-kernel' / variant
    target.mkdir(parents=True)
    for file in ('boot-s9plus.img', 'kernel-manifest.json', 'kernel.config'):
        shutil.copyfile(bundle / file, target / file)
    shutil.copytree(REPO / 'packaging/runtime', payload, dirs_exist_ok=True)
    shutil.copytree(REPO / 'experiments/cpuidle/rootfs', payload, dirs_exist_ok=True)
    if variant == 'full':
        for kind in ('audio', 'bluetooth', 'sensors'):
            shutil.copytree(REPO / f'experiments/{kind}/rootfs', payload, dirs_exist_ok=True)
        compat = payload / 'usr/local/lib/s9plus-sensors/compat/libwakelock-no-suspend.so'
        compat.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundle / 'libwakelock-no-suspend.so', compat)
    # Distribution packages own /usr paths; adapt the tested local overlays.
    local = payload / 'usr/local'
    if local.exists():
        for path in list(local.iterdir()):
            shutil.copytree(path, payload / 'usr' / path.name, dirs_exist_ok=True)
        shutil.rmtree(local)
    for path in payload.rglob('*'):
        if path.is_file() and path.suffix not in ('.ko', '.so', '.img'):
            data = path.read_bytes()
            if b'\0' not in data and b'/usr/local/' in data:
                path.write_bytes(data.replace(b'/usr/local/', b'/usr/'))
    docs = payload / 'usr/share/doc' / name
    docs.mkdir(parents=True)
    shutil.copyfile(REPO / 'THIRD-PARTY.md', docs / 'copyright')
    # Publish source alongside the release, avoiding multi-hundred MB duplication
    # in every binary package.
    (docs / 'source').write_text('Corresponding source: GitHub release assets kernel-source.tar.zst and port-build-source.tar.zst.\n')
    hook = f'''#!/bin/sh
set -eu
case "${{1:-configure}}" in configure|triggered) ;; *) exit 0 ;; esac
depmod {manifest['release']}
exec /usr/libexec/s9plus-install-boot /usr/share/s9plus-kernel/{variant}
'''
    deb = out / 'deb-root'
    shutil.copytree(payload, deb)
    control = deb / 'DEBIAN'
    control.mkdir()
    (control / 'control').write_text(f'''Package: {name}
Version: {version}-{revision}
Architecture: arm64
Maintainer: moooozi <moooozi@users.noreply.github.com>
Depends: python3, kmod, util-linux
Conflicts: linux-s9plus-{'embedding' if variant == 'full' else 'full'}
Section: kernel
Priority: optional
Description: Galaxy S9+ mainline kernel ({variant}) with matching uniLoader BOOT
 Includes verified modules and a guarded on-device BOOT update hook.
''')
    (control / 'postinst').write_text(hook)
    (control / 'postinst').chmod(0o755)
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(deb),
                    str(out / f'{name}_{version}-{revision}_arm64.deb')], check=True)
    alpine = out / 'apkbuild'
    alpine.mkdir()
    with tarfile.open(alpine / 'payload.tar.gz', 'w:gz') as archive:
        for path in sorted(payload.rglob('*')):
            if path.is_file():
                item = archive.gettarinfo(str(path), str(path.relative_to(payload)))
                item.uid = item.gid = 0
                item.uname = item.gname = 'root'
                with path.open('rb') as stream:
                    archive.addfile(item, stream)
    checksum = hashlib.sha512((alpine / 'payload.tar.gz').read_bytes()).hexdigest()
    post = f'''#!/bin/sh
set -eu
depmod {manifest['release']}
exec /usr/libexec/s9plus-install-boot /usr/share/s9plus-kernel/{variant}
'''
    for suffix in ('post-install', 'post-upgrade'):
        (alpine / f'{name}.{suffix}').write_text(post)
        (alpine / f'{name}.{suffix}').chmod(0o755)
    (alpine / 'APKBUILD').write_text(f'''# Maintainer: moooozi <moooozi@users.noreply.github.com>
# Precompiled in this repository's cross-kernel workflow; no compilation here.
pkgname={name}
pkgver={version}
pkgrel={int(revision)-1}
pkgdesc="Galaxy S9+ mainline kernel ({variant}) and matching uniLoader BOOT"
url="https://github.com/moooozi/galaxy-s9plus-kernel"
arch="aarch64"
license="GPL-2.0-only"
depends="python3 kmod util-linux merge-usr !linux-s9plus-{'embedding' if variant == 'full' else 'full'}"
provides="linux-samsung-star2lte-mainline=$pkgver-r$pkgrel"
install="$pkgname.post-install $pkgname.post-upgrade"
source="payload.tar.gz"
options="!check !strip !tracedeps !archcheck"
build() {{ :; }}
package() {{
    mkdir -p "$pkgdir"
    cp -a "$srcdir"/usr "$pkgdir"/
    if [ -d "$srcdir"/etc ]; then cp -a "$srcdir"/etc "$pkgdir"/; fi
}}
sha512sums="{checksum}  payload.tar.gz"
''')


if __name__ == '__main__':
    main()
