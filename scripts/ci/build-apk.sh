#!/bin/sh
# Runs inside Alpine. Only packages precompiled files; no target code executes.
set -eu
bundle=${1:?apkbuild directory}
output=${2:?output directory}
: "${PACKAGER_PRIVKEY:?path to repository RSA signing key}"
apk add --no-cache abuild fakeroot openssl >/dev/null
openssl rsa -in "$PACKAGER_PRIVKEY" -pubout -out "${PACKAGER_PRIVKEY}.pub"
cmp "${PACKAGER_PRIVKEY}.pub" /work/keys/s9plus.rsa.pub
cp "${PACKAGER_PRIVKEY}.pub" /etc/apk/keys/
mkdir -p /root/.abuild
printf 'PACKAGER_PRIVKEY="%s"\nREPODEST="%s"\n' "$PACKAGER_PRIVKEY" "$output" > /root/.abuild/abuild.conf
cd "$bundle"
# CHOST controls package architecture. No dependency resolution/cross toolchain
# is needed for this file-only package, so run the phases explicitly.
CHOST=aarch64 abuild -F -d
