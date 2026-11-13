#!/bin/bash
# Build signed, cumulative APT/APK indexes from staged release packages.
set -euo pipefail
site=${1:?site directory}
: "${APK_SIGNING_KEY:?}"
: "${GPG_SIGNING_WRAPPER:?import the owner GPG signing key first}"
mkdir -p "$site/apt/pool" "$site/apt/dists/stable/main/binary-arm64" "$site/apk/aarch64" "$site/keys"
cp keys/* "$site/keys/"
find dist/packages -name '*.deb' -exec cp '{}' "$site/apt/pool/" \;
find dist/packages -name '*.apk' -exec cp '{}' "$site/apk/aarch64/" \;
cp dist/kernel-selection.json "$site/latest.json"
(
    cd "$site/apt"
    dpkg-scanpackages --multiversion pool /dev/null > dists/stable/main/binary-arm64/Packages
    gzip -n -c dists/stable/main/binary-arm64/Packages > dists/stable/main/binary-arm64/Packages.gz
    apt-ftparchive -o APT::FTPArchive::Release::Origin='Galaxy S9+ kernels' \
        -o APT::FTPArchive::Release::Suite=stable \
        -o APT::FTPArchive::Release::Codename=stable \
        -o APT::FTPArchive::Release::Architectures=arm64 \
        -o APT::FTPArchive::Release::Components=main \
        release dists/stable > dists/stable/Release
    "$GPG_SIGNING_WRAPPER" --armor --detach-sign --output dists/stable/Release.gpg dists/stable/Release
    "$GPG_SIGNING_WRAPPER" --clearsign --output dists/stable/InRelease dists/stable/Release
)
# apk-tools/abuild-sign are provided by the Alpine packaging container.
docker run --rm -v "$PWD:/work" -w /work -e APK_SIGNING_KEY \
    alpine:3.24 sh -ec '
      apk add --no-cache abuild >/dev/null
      openssl rsa -in "$APK_SIGNING_KEY" -pubout -out "${APK_SIGNING_KEY}.pub"
      cmp "${APK_SIGNING_KEY}.pub" /work/keys/s9plus.rsa.pub
      cp "${APK_SIGNING_KEY}.pub" /etc/apk/keys/
      cd "$1/apk/aarch64"
      apk index --rewrite-arch aarch64 -o APKINDEX.tar.gz ./*.apk
      abuild-sign -k "$APK_SIGNING_KEY" APKINDEX.tar.gz
    ' sh "$site"
printf '%s\n' '<!doctype html><title>Galaxy S9+ kernels</title><h1>Galaxy S9+ kernels</h1><p>Signed APT and APK repositories. Sources and installation notes: <a href="https://github.com/moooozi/galaxy-s9plus-kernel">kernel repository</a>.</p>' > "$site/index.html"
