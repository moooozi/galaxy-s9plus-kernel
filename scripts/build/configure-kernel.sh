#!/bin/bash
# One hardware configuration for every distribution image.
set -euo pipefail
src=$1
"$src/scripts/config" --file "$src/out/.config" \
    --set-str LOGO_LINUX_CLUT224_FILE drivers/video/logo/logo_linux_clut224.ppm \
    -e S9PLUS_CHARGE_LIMIT --set-val S9PLUS_CHARGE_LIMIT_DEFAULT 100
