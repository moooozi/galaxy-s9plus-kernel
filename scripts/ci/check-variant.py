#!/usr/bin/env python3
"""Reject a package when Kconfig has silently changed a variant's contract."""
from pathlib import Path
import sys
config = dict(line.split('=', 1) for line in Path(sys.argv[1]).read_text().splitlines()
              if line.startswith('CONFIG_') and '=' in line)
variant = sys.argv[2]
required = ['SCSI_UFS_EXYNOS9810', 'EXT4_FS', 'S9PLUS_CPUIDLE', 'USB_CONFIGFS',
            'CHARGER_MAX77705', 'BATTERY_MAX17042']
for symbol in required:
    if config.get('CONFIG_' + symbol) != 'y':
        raise SystemExit(f'required built-in missing: {symbol}')
if variant == 'embedding':
    for symbol in ['SOUND', 'SND', 'BT', 'DRM', 'FB', 'IIO', 'MEDIA_SUPPORT']:
        if config.get('CONFIG_' + symbol) in ('y', 'm'):
            raise SystemExit(f'forbidden server subsystem: {symbol}')
    if config.get('CONFIG_S9PLUS_CHARGE_LIMIT') != 'y':
        raise SystemExit('embedding charge limit missing')
elif variant != 'full':
    raise SystemExit('unknown variant')
