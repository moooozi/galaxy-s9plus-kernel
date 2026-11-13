#!/usr/bin/env python3
"""Reject kernels missing the shared phone hardware configuration."""
from pathlib import Path
import sys
config = dict(line.split('=', 1) for line in Path(sys.argv[1]).read_text().splitlines()
              if line.startswith('CONFIG_') and '=' in line)
required = ['SCSI_UFS_EXYNOS9810', 'EXT4_FS', 'S9PLUS_CPUIDLE', 'USB_CONFIGFS',
            'CHARGER_MAX77705', 'BATTERY_MAX17042', 'S9PLUS_CHARGE_LIMIT',
            'DRM_S9P_DECON', 'DRM_PANFROST', 'TOUCHSCREEN_S6SY761', 'RFKILL']
for symbol in required:
    if config.get('CONFIG_' + symbol) != 'y':
        raise SystemExit(f'required built-in missing: {symbol}')
for symbol in ['SND', 'BT', 'IIO']:
    if config.get('CONFIG_' + symbol) not in ('y', 'm'):
        raise SystemExit(f'required subsystem missing: {symbol}')
if config.get('CONFIG_S9PLUS_CHARGE_LIMIT_DEFAULT') != '100':
    raise SystemExit('charging profiles belong to images; kernel default must be 100')

# Validate the effective post-olddefconfig command line, not only its source.
arguments = config.get('CONFIG_CMDLINE', '').strip('"').split()
for argument in ('quiet', 'splash', 'loglevel=4', 'systemd.show_status=false',
                 'systemd.log_target=journal-or-kmsg', 'logo.nologo=1'):
    if argument not in arguments:
        raise SystemExit('quiet boot argument missing: ' + argument)
if 'ignore_loglevel' in arguments:
    raise SystemExit('ignore_loglevel would defeat quiet boot')
