#!/bin/bash
set -euo pipefail
src=$1
variant=$2
case "$variant" in
full)
    "$src/scripts/config" --file "$src/out/.config" --set-str LOGO_LINUX_CLUT224_FILE drivers/video/logo/logo_linux_clut224.ppm
    "$src/scripts/config" --file "$src/out/.config" -e S9PLUS_CHARGE_LIMIT --set-val S9PLUS_CHARGE_LIMIT_DEFAULT 100
    exit 0 ;;
embedding) ;;
*) exit 1 ;;
esac
config="$src/out/.config"
# Preserve UFS, USB gadget, Wi-Fi, regulators, cpufreq and conservative CPU idle.
"$src/scripts/config" --file "$config" -d SOUND -d SND -d BT -d DRM -d FB \
    -d FRAMEBUFFER_CONSOLE -d BACKLIGHT_CLASS_DEVICE -d INPUT_TOUCHSCREEN \
    -d MEDIA_SUPPORT -d IIO -d LEDS_CLASS -d LOGO -d VT \
    -e S9PLUS_CHARGE_LIMIT --set-val S9PLUS_CHARGE_LIMIT_DEFAULT 65
