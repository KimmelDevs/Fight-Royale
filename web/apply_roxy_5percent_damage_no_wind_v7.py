#!/usr/bin/env python3
"""Fight Royale: Roxy V7 — +5% light/charged/Frostwing damage and remove wind.mp3 request.

Run from web/ with `python apply_roxy_5percent_damage_no_wind_v7.py`.
Compatible with Roxy V5 and V6. Checks every edit before writing, creates backups,
and can be run again without changing anything.
"""
from pathlib import Path
from datetime import datetime
import argparse
import sys

MARK = 'ROXY_V7_5PCT_LIGHT_CHARGED_BIRD_NO_WIND_20261108'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--path', type=Path, default=Path.cwd(), help='Path to web/ (default: current folder)')
parser.add_argument('--dry-run', action='store_true', help='Check compatibility without writing files')
args = parser.parse_args()
root = args.path.resolve()
kits = root / 'src/game/kits.ts'
game = root / 'src/game/game.ts'
if not (root / 'package.json').is_file():
    sys.exit('ERROR: Run from the Fight Royale web/ folder (where package.json lives). No files changed.')
try:
    old_k = kits.read_text(encoding='utf-8')
    old_g = game.read_text(encoding='utf-8')
except OSError as e:
    sys.exit(f'ERROR: Missing game source: {e}. No files changed.')
if MARK in old_k and MARK in old_g:
    print('Roxy V7 already installed; no changes needed.')
    sys.exit(0)
if MARK in old_k or MARK in old_g:
    sys.exit('ERROR: Partial V7 installation detected; no changes made. Check the backed-up files.')
if 'ROXY_BALANCE_GRIMOIRE_FROSTBITE_V5_20261108' not in old_g:
    sys.exit('ERROR: Roxy V5 or later is required. No files changed.')

# Scope all changes to the Frost-specific skill block: this does not buff other mages.
from_light = 'dmg: Math.round(t[key].dmg * 0.75), style: "frost_shard", pierce: false, size: 0.82'
to_light = 'dmg: Math.round(t[key].dmg * 0.75) * 1.05, style: "frost_shard", pierce: false, size: 0.82'
from_heavy = 'dmg: 40, guard: 16, knock: 1.2, stun: 0.16, speed: 13.0, size: 0.85, count: 4, spread: 0.33,'
to_heavy = 'dmg: 42, guard: 16, knock: 1.2, stun: 0.16, speed: 13.0, size: 0.85, count: 4, spread: 0.33,'
from_bird = 'cd: 52, type: "snow_puppet", style: "bird", wind: 0.35, recover: 0.45,\n        dmg: 15, guard: 8'
to_bird = 'cd: 52, type: "snow_puppet", style: "bird", wind: 0.35, recover: 0.45,\n        dmg: 15.75, guard: 8'
from_sound = '      this.snd("wind", 0.45);\n      return;'
to_sound = '      // ROXY V7: Frostwing summons silently (no missing /sfx/wind.mp3).\n      return;'

changes = [(from_light, to_light, 'Roxy basic light projectile damage'),
           (from_heavy, to_heavy, 'Roxy charged shard damage'),
           (from_bird, to_bird, 'Frostwing shard damage')]
modified_k = old_k
for original, replacement, label in changes:
    occurrences = modified_k.count(original)
    if occurrences != 1:
        sys.exit(f'ERROR: Could not safely locate {label} (matches: {occurrences}). No files changed.')
    modified_k = modified_k.replace(original, replacement, 1)
if modified_k.count('if (element === "frost")') < 1 or 'Frostwing Choir' not in modified_k:
    sys.exit('ERROR: Roxy frost kit has changed unexpectedly. No files changed.')
if old_g.count(from_sound) != 1:
    sys.exit(f'ERROR: Expected one Roxy wind summon sound, found {old_g.count(from_sound)}. No files changed.')
modified_g = old_g.replace(from_sound, to_sound, 1)
modified_k = f'// {MARK}: Roxy-only 5% light/charged/bird buff.\n' + modified_k
modified_g = f'// {MARK}: remove unavailable Frostwing wind sound.\n' + modified_g

print('Roxy V7 patch preflight OK:')
print('  Basic attack combo: +5% each hit (41 -> 43.05; 45 -> 47.25; 32 -> 33.6).')
print('  Charged attack: 40 -> 42 damage PER shard (+5%).')
print('  Frostwing Choir: 15 -> 15.75 damage PER shard (+5%); 52s cooldown unchanged.')
print('  Remove only the Frostwing summon wind sound (fixes missing wind.mp3 request).')
if args.dry_run:
    print('Dry run complete. No files changed.')
    sys.exit(0)
stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
for path, before, after in [(kits, old_k, modified_k), (game, old_g, modified_g)]:
    backup = path.with_name(f'{path.name}.before_roxy_v7_{stamp}.bak')
    backup.write_text(before, encoding='utf-8')
    path.write_text(after, encoding='utf-8')
    print(f'Updated {path.relative_to(root)} (backup {backup.name})')
print('Done. Verify with: npx tsc --noEmit -p .')
