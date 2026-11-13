#!/usr/bin/env python3
from pathlib import Path
import sys
src = Path(sys.argv[1])
p = src / 'drivers/power/supply/Kconfig'
s = p.read_text()
if 'config S9PLUS_CHARGE_LIMIT' not in s:
    s += """
config S9PLUS_CHARGE_LIMIT
	bool "Galaxy S9+ configurable charge preservation"
	depends on CHARGER_MAX77705=y && BATTERY_MAX17042=y
\tdefault y
	help
	  Enforce configurable charging hysteresis in the charger
	  driver. Missing or invalid capacity inhibits charging. Used by the
	  shared kernel defaults to no added limit (100/98). Images apply policy.

config S9PLUS_CHARGE_LIMIT_DEFAULT
\tint "Default Galaxy S9+ charge stop percentage"
\tdepends on S9PLUS_CHARGE_LIMIT
\trange 1 100
\tdefault 100
"""
    p.write_text(s)
p = src / 'include/linux/power/max77705_charger.h'
s = p.read_text()
anchor = 'struct max77705_charger_data {'
if 's9plus_limit_work' not in s:
    s = s.replace(anchor, anchor + """
#if IS_ENABLED(CONFIG_S9PLUS_CHARGE_LIMIT)
	struct delayed_work s9plus_limit_work;
	struct mutex s9plus_limit_lock;
	bool s9plus_limit_allowed;
	bool s9plus_manual_inhibit;
	int s9plus_charge_start;
	int s9plus_charge_end;
#endif
""", 1)
    p.write_text(s)
