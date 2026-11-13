# Galaxy S9+ mainline kernels

Owner-created public signing keys are checked in under `keys/`. CI uses
`GPG_PRIVATE_KEY`, `GPG_PASSPHRASE`, `GPG_SIGNING_KEY_FINGERPRINT` and
`APK_PRIVATE_KEY`. Manual dispatch defaults to signed test artifacts; release
publishing remains gated until the initial pipeline is verified.

Independent kernel releases for SM-G965F (`samsung,star2lte`, Exynos 9810).
The [image repository](https://github.com/moooozi/galaxy-s9plus-mainline-linux)
assembles Debian/postmarketOS images from these released packages.

One shared kernel and module set supports headless Debian 13, postmarketOS
Plasma Mobile and postmarketOS Phosh. The package is `linux-s9plus`, its kernel
release is `<version>-s9plus`, and the bundle manifest identifies it as `unified`.
Audio, Bluetooth, graphics, touch and sensors remain available in every kernel.
Images choose which optional hardware services to activate.

Charging defaults belong to the images: Debian stops at 65%, resumes at 63%;
mobile images default to no added limit. The kernel starts with no added limit;
image settings apply once userspace starts. This does not enforce 65% before
userspace, in recovery or while another OS is running.

Headless display shutdown and whole-device consumption need hardware validation.
A shared graphics driver alone does not establish either. No second stripped
kernel is built or published.

## Releases and updates

Actions checks kernel.org every six hours and tracks only supported stable
7.3.x patches. It never switches to 7.4 or any later series. If no supported
7.3.x release remains, selection stops with an explicit error. Published versions never downgrade. The kernel is built from one exact upstream commit. Resolution/fetch can use Greg
Kroah-Hartman’s GitHub stable-tree mirror when kernel.org is unreachable; the
resolved commit is recorded and verified before export. A release is published only after
the build and source checks succeed. Bump `release-policy.json`'s
`package_revision` for a new port-driver/package revision of the same kernel.

GitHub Releases contains Debian/Alpine packages and a shared bundle with
BOOT, matching modules, configuration, manifests, checksums and corresponding
kernel/port/loader source. GitHub Pages hosts cumulative, signed APT and APK
indexes. Only public repository keys live in this checkout. Production CI signing keys
are owner-created Actions secrets (`GPG_PRIVATE_KEY`, `GPG_PASSPHRASE`,
`APK_PRIVATE_KEY`), with the signer selected by the non-secret repository
variable `GPG_SIGNING_KEY_FINGERPRINT`. The encrypted GPG key is imported into
a temporary job keyring and its passphrase is passed through a private file
descriptor. Builds remain artifact-only until release publishing is enabled. Preserve
the private keys securely when moving CI; changing keys requires distributing
new public keys to existing devices.

Debian images install this source with the checked-in public key:

```
deb [arch=arm64 signed-by=/etc/apt/keyrings/s9plus-kernel.asc] https://moooozi.github.io/galaxy-s9plus-kernel/apt stable main
```

postmarketOS images install `keys/s9plus.rsa.pub` in `/etc/apk/keys` and add:

```
https://moooozi.github.io/galaxy-s9plus-kernel/apk
```

`apt upgrade` / `apk upgrade` delivers the shared kernel. Package
hooks verify the model, BOOT size, matching module hashes, full BOOT backup and
candidate hash before writing BOOT, then verify readback. A failed candidate
write attempts backup restoration and verifies it. The hooks never reboot.
The new kernel runs after the next reboot. A power failure during BOOT writing
still requires recovery; TWRP and USERDATA are never written by this hook.
Images set `S9PLUS_IMAGE_BUILD=1`, so package installation stages files without
opening a block device. Test builds have not been validated on the phone.

## Battery preservation

The charger exposes standard power-supply `charge_control_start_threshold` and
`charge_control_end_threshold` attributes. Stop `100` disables preservation and
retains the existing charging policy. While preservation is enabled, missing or
invalid gauge capacity inhibits charging. The worker samples every two seconds;
this is a capacity-based software policy, not a hardware safety/termination
substitute. Bus failures are reported and retried; a failed write cannot
provide a guaranteed hardware stop. Existing voltage/current settings are not
increased. Manual `inhibit-charge` remains in force until `auto` is requested.

```
sudo s9plus-battery-preservation --stop 80 --start 78
sudo s9plus-battery-preservation --stop 65  # resume defaults to 63
sudo s9plus-battery-preservation --stop 100 # disable preservation
s9plus-battery-preservation               # show current thresholds
```

The tool saves `/etc/s9plus/battery-preservation.json`; the image enables the
service that reapplies it at boot. A desktop power tool can also write the
standard sysfs thresholds, but direct writes alone are volatile. A kernel update
retains the saved file. A fresh image provides its own saved defaults; package updates leave that file intact.
The old temporary 80% test on the Ubuntu validation phone is separate and is
not included here.

## Build and validate

```
python3 scripts/ci/check-source.py
mkdir -p dist
python3 scripts/ci/resolve-kernel.py > dist/kernel-selection.json
docker run --rm -v "$PWD:/work" -w /work -e KERNEL_OUT=/work/dist/unified ubuntu:24.04 bash scripts/ci/build-mobile-kernel.sh
```

Use a fresh `BUILD` directory per build. The builder exports a locked source commit, applies guarded patches,
compiles all configured modules and verifies vermagic/depmod before packaging.
`package-distributions.py` creates Debian packages and precompiled APKBUILD
inputs; Alpine's `abuild` packages those files without recompiling the kernel.

The parent port's [hardware validation](https://github.com/moooozi/galaxy-s9plus-mainline-linux/blob/kernel-driver-integration-20261112/docs/driver-validation-2026-11-12.md)
is for kernel 7.3.1, CPUs2/3 idle, guarded sensor startup and bounded audio
recovery. The new shared 7.3.4 kernel and the preservation worker need their own device
trial. Wider CPU/SoC idle, system suspend, camera, cellular/call audio and
microphones remain unsupported or unvalidated. CPU idle still starts disabled
until the existing userspace guard confirms it can enable only CPUs2/3.

Driver/firmware/loader licenses and provenance remain in `THIRD-PARTY.md`,
individual source headers and the corresponding source release assets.

Build jobs use `ubuntu-26.04-arm`; the compiler container remains Ubuntu24.04
with GCC13 to retain the tested toolchain. Image builds use the same ARM64
runner family and consume released kernel packages.
