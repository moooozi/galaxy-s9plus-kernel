#!/bin/bash
# Inside an ephemeral Ubuntu 24.04 cross-build container, repository at /work.
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export BUILD=${BUILD:-$REPO/.build/kernel-ci}
WORK=$BUILD
VARIANT=${VARIANT:?set VARIANT to full or embedding}
case "$VARIANT" in full|embedding) ;; *) exit 1 ;; esac
export VARIANT
SOURCE_MANIFEST=${SOURCE_MANIFEST:-$REPO/dist/kernel-selection.json}
OUT=${KERNEL_OUT:-$REPO/dist/mobile-kernel}
[ "$(id -u)" = 0 ] || { echo 'Run in the build container as root' >&2; exit 1; }
[ ! -e "$WORK/src/mainline" ] || { echo 'Use a fresh kernel build directory' >&2; exit 1; }
mkdir -p "$OUT"
"$REPO/scripts/build/setup_build.sh"
"$REPO/scripts/build/toolchain.sh"
python3 - "$REPO" "$SOURCE_MANIFEST" "$WORK/src/mainline" <<'PY'
import importlib.util, json, sys
from pathlib import Path
repo, manifest, dest = map(Path, sys.argv[1:])
spec=importlib.util.spec_from_file_location('fetch', repo/'scripts/ci/fetch-locked-source.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
source=json.loads(manifest.read_text())
module.export(source['url'], source['commit'], dest, mirrors=source.get('mirrors', []))
PY
SRC=$WORK/src/mainline
"$REPO/scripts/build/apply_drivers.sh" "$SRC"
python3 "$REPO/experiments/bluetooth/patch-btbcm-s9plus.py" "$SRC"
python3 "$REPO/experiments/cpuidle/verify-suspend-hash.py" "$SRC"
mkdir -p "$SRC/out" "$WORK/initramfs/bin" "$WORK/initramfs/dev"
install -m 755 "$WORK/out/busybox-arm64" "$WORK/initramfs/bin/busybox"
busybox_command=("$WORK/initramfs/bin/busybox")
case "$(uname -m)" in
    aarch64|arm64) ;;
    *) busybox_command=(qemu-aarch64-static "${busybox_command[@]}") ;;
esac
for applet in $("${busybox_command[@]}" --list); do
    [ "$applet" = busybox ] || ln -s busybox "$WORK/initramfs/bin/$applet"
done
install -m 755 "$REPO/device/mainline-init-boot" "$WORK/initramfs/init"
if [ -f "$REPO/device/mainline-extra-probe" ]; then
    install -m 755 "$REPO/device/mainline-extra-probe" "$WORK/initramfs/extra-probe"
fi
sed -i 's/\r$//' "$WORK/initramfs/init" "$WORK/initramfs/extra-probe"
# gen_init_cpio creates nodes in the archive, without requiring host mknod
# privileges (also works in a rootless container).
cat > "$WORK/initramfs-nodes.list" <<'EOF'
nod /dev/console 0600 0 0 c 5 1
nod /dev/null 0666 0 0 c 1 3
nod /dev/kmsg 0600 0 0 c 1 11
nod /dev/mem 0600 0 0 c 1 1
EOF
mkdir -p "$WORK/firmware/brcm"
cp "$REPO/firmware/bcmdhd_sta.bin_b2" "$WORK/firmware/brcm/brcmfmac4361-pcie.bin"
cp "$REPO/firmware/nvram.txt_r02a_b2" "$WORK/firmware/brcm/brcmfmac4361-pcie.txt"
cp "$REPO/firmware/bcmdhd_clm.blob" "$WORK/firmware/brcm/brcmfmac4361-pcie.clm_blob"
cp "$REPO/firmware/"regulatory.db* "$WORK/firmware/"
sed -i 's/\r$//' "$WORK/firmware/brcm/brcmfmac4361-pcie.txt"
install -m 644 "$REPO/src/configs/s9plus-mobile.config" "$SRC/out/.config"
# The tested board DT is kept as source and rebuilt with this kernel's dtc.
install -m 644 "$REPO/src/mainline-dts/exynos9810-star2lte.dts" "$SRC/arch/arm64/boot/dts/exynos/"
sed -i 's/status = "disabled"; \/\* UFS-STATUS \*\//status = "okay";/' "$SRC/arch/arm64/boot/dts/exynos/exynos9810-star2lte.dts"
sed -i 's/status = "disabled"; \/\* GPU-STATUS \*\//status = "okay";/' "$SRC/arch/arm64/boot/dts/exynos/exynos9810-star2lte.dts"
sed -i 's/status = "disabled"; \/\* DECON-STATUS \*\//status = "okay";/' "$SRC/arch/arm64/boot/dts/exynos/exynos9810-star2lte.dts"
sed -i 's/status = "disabled"; \/\* WLAN-STATUS \*\//status = "okay";/' "$SRC/arch/arm64/boot/dts/exynos/exynos9810-star2lte.dts"
cd "$SRC"
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
scripts/config --file out/.config --set-str INITRAMFS_SOURCE "$WORK/initramfs $WORK/initramfs-nodes.list" \
    --set-str EXTRA_FIRMWARE_DIR "$WORK/firmware" --set-str LOCALVERSION "-s9plus-$VARIANT" -d LOCALVERSION_AUTO
bash "$REPO/scripts/build/configure-variant.sh" "$SRC" "$VARIANT"
make O=out olddefconfig
python3 "$REPO/scripts/ci/check-variant.py" "$SRC/out/.config" "$VARIANT"
# Desktop Bluetooth availability relies on the kernel's real rfkill interface.
if [ "$VARIANT" = full ]; then grep -qx 'CONFIG_RFKILL=y' out/.config; fi
grep -qx 'CONFIG_S9PLUS_CPUIDLE=y' out/.config
make O=out -j"${BUILD_JOBS:-$(nproc)}" Image exynos/exynos9810-star2lte.dtb
make O=out -j"${BUILD_JOBS:-$(nproc)}" modules
make O=out INSTALL_MOD_PATH="$WORK/module-install" modules_install
if [ "$VARIANT" = full ]; then
for kind in audio bluetooth sensors; do
    mkdir -p "$WORK/$kind-driver"
    cp -a "$REPO/experiments/$kind/driver/." "$WORK/$kind-driver/"
    make O=out M="$WORK/$kind-driver" -j"${BUILD_JOBS:-$(nproc)}" modules
done
fi
mkdir -p "$WORK/sensors-compat"
if [ "$VARIANT" = full ]; then
aarch64-linux-gnu-gcc -shared -nostdlib -fPIC -Wl,-soname,libwakelock-no-suspend.so \
    -o "$WORK/sensors-compat/libwakelock-no-suspend.so" \
    "$REPO/experiments/sensors/compat/wakelock-no-suspend.c"
fi
python3 "$REPO/scripts/ci/package-mobile-kernel.py" "$WORK" "$OUT" "$SOURCE_MANIFEST"
