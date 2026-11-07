#!/usr/bin/env python3
"""Repair the broken Zenith V6 animation patch and safely apply spear choreography.

Run from Fight Royale/web. Restores complete kits.ts from the backup the old
V6 installer made, then changes ONLY Zenith's own Pose entries. Preserves V5
Twin Metal Blades, Magnetic Catch, and overhead charge poses, plus every other
character's attack/animation definitions.
"""
from pathlib import Path
from datetime import datetime
import shutil
import re
import sys

ROOT = Path.cwd()
PATH = next((p for p in [ROOT/'src/game/kits.ts', ROOT/'game/kits.ts'] if p.is_file()), None)
if PATH is None:
    sys.exit('ERROR: Run this inside your Fight Royale web/ folder. No changes made.')

MARK = 'ZENITH_V6_SAFE_RECOVERY_20261108'
POSE_LINES = {'idle': '  idle: P([0.01,-0.12,0], [-0.01,0.10,0], [-0.92,-0.04,-0.30], [0.16,0,0.06], [-0.58,-0.62,0.20], [0.08,0,0.02], [-0.26,0,0.08], [0.30,0,-0.08], -0.07),', 'block': '  block: P([0.10,-0.05,0], [0.02,0.04,0], [-1.10,0.08,-0.28], [0.13,0,0.06], [-0.86,-0.50,0.26], [0.10,0,0.02], [-0.36,0,0.08], [0.40,0,-0.08], -0.09),', 'zn1_w': '  zn1_w: P([0.08,-0.36,0], [0,0.22,0], [-1.26,-0.26,-0.28], [0.24,0,0.06], [-0.72,-0.82,0.18], [0.10,0,0.02], [-0.34,0,0.08], [0.29,0,-0.07], -0.10),', 'zn1_s': '  zn1_s: P([0.22,0.18,0], [0,-0.12,0], [-1.72,0.02,-0.22], [0.04,0,0.06], [-1.06,-0.58,0.18], [0.05,0,0.02], [-0.54,0,0.09], [0.43,0,-0.08], -0.13),', 'zn2_w': '  zn2_w: P([0.12,0.28,0.02], [0,-0.22,0], [-1.03,0.32,-0.10], [0.20,0,0.14], [-0.60,-0.44,0.36], [0.08,0,0.02], [-0.23,0,0.09], [0.34,0,-0.07], -0.09),', 'zn2_s': '  zn2_s: P([0.22,-0.14,0], [0,0.14,0], [-1.60,-0.10,-0.17], [0.05,0,0.10], [-1.05,-0.36,0.24], [0.06,0,0.02], [-0.45,0,0.10], [0.36,0,-0.09], -0.12),', 'zn3_w': '  zn3_w: P([0.05,-0.28,-0.03], [0,0.20,0], [-0.98,-0.56,-0.34], [0.18,0,-0.04], [-0.62,-0.72,0.18], [0.10,0,0.02], [-0.33,0,0.11], [0.36,0,-0.07], -0.10),', 'zn3_s': '  zn3_s: P([0.18,0.20,0], [0,-0.17,0], [-1.46,-0.18,-0.30], [0.04,0,-0.02], [-0.96,-0.64,0.20], [0.04,0,0.02], [-0.51,0,0.10], [0.42,0,-0.08], -0.13),', 'zn4_w': '  zn4_w: P([0.10,0.20,0], [0,-0.18,0], [-0.82,0.04,-0.36], [0.20,0,0.05], [-0.78,-0.36,0.28], [0.12,0,-0.02], [-0.27,0,0.10], [0.31,0,-0.07], -0.09),', 'zn4_s': '  zn4_s: P([0.19,-0.18,0.03], [0,0.15,0], [-1.42,-0.20,-0.28], [0.04,0,0.05], [-1.08,-0.50,0.16], [0.05,0,-0.02], [-0.53,0,0.11], [0.45,0,-0.08], -0.13),', 'zn5_w': '  zn5_w: P([-0.02,-0.46,0], [0.02,0.30,0], [-1.18,-0.42,-0.32], [0.30,0,0.03], [-0.86,-0.76,0.22], [0.13,0,0.02], [-0.50,0,0.12], [0.30,0,-0.08], -0.13),', 'zn5_s': '  zn5_s: P([0.30,0.34,0], [-0.08,-0.18,0], [-1.86,-0.06,-0.30], [0.04,0,0.03], [-1.18,-0.66,0.20], [0.04,0,0.02], [-0.73,0,0.13], [0.52,0,-0.09], -0.18),', 'znz_w': '  znz_w: P([0.02,-0.24,0], [0,0.18,0], [-2.02,-0.32,-0.58], [0.42,0,0.10], [-0.74,-0.24,0.34], [0.14,0,0.02], [-0.40,0,0.09], [0.34,0,-0.08], -0.12),', 'znz_s': '  znz_s: P([0.30,0.20,0], [-0.10,-0.10,0], [-0.60,0.02,-0.08], [0.04,0,0.02], [-1.76,-0.10,0.22], [0.08,0,0.02], [-0.67,0,0.10], [0.48,0,-0.10], -0.17),', 'znx_w': '  znx_w: P([0.08,-0.22,0], [0,0.16,0], [-1.00,-0.30,-0.30], [0.22,0,0.06], [-0.68,-0.62,0.22], [0.10,0,0.02], [-0.40,0,0.09], [0.38,0,-0.08], -0.10),', 'znx_s': '  znx_s: P([0.18,0.10,0], [0,-0.06,0], [-1.42,-0.06,-0.24], [0.06,0,0.05], [-0.98,-0.44,0.20], [0.06,0,0.02], [-0.56,0,0.10], [0.42,0,-0.09], -0.12),', 'znc_w': '  znc_w: P([0.04,-0.10,0], [0,0.08,0], [-0.50,-0.18,-0.74], [0.16,0,0.12], [-1.22,-0.32,0.12], [0.18,0,0.02], [-0.30,0,0.07], [0.31,0,-0.08], -0.06),', 'znc_s': '  znc_s: P([0.14,0.14,0], [0,-0.10,0], [-0.58,0.18,-0.92], [0.08,0,0.12], [-1.20,-0.02,0.16], [0.12,0,0.02], [-0.42,0,0.10], [0.38,0,-0.09], -0.08),', 'znv_w': '  znv_w: P([-0.08,-0.06,0], [0,0.08,0], [-2.36,-0.02,-0.30], [0.14,0,0.04], [-1.00,-0.42,0.26], [0.14,0,0.02], [-0.46,0,0.12], [0.43,0,-0.08], -0.10),', 'znv_s': '  znv_s: P([0.16,0.12,0], [0,-0.10,0], [-2.54,0.10,-0.22], [0.08,0,0.04], [-0.60,-0.12,0.20], [0.10,0,0.02], [-0.54,0,0.09], [0.49,0,-0.09], -0.10),'}
REQUIRED = (
    'export function attacks(',
    'const COMMON: Record<string, Pose> = {',
    'const KNIGHT: Record<string, Pose> = {',
    'const MAGE: Record<string, Pose> = {',
    'const ASSASSIN: Record<string, Pose> = {',
    'const GLAIVE: Record<string, Pose> = {',
    'const ZENITH: Record<string, Pose> = {',
    'const CHAINBLADE: Record<string, Pose> = {',
    'const TABLES: Record<string, Record<string, Pose>> = {',
    'export function poses(',
)

def complete(source):
    return all(s in source for s in REQUIRED) and len(source.splitlines()) > 900

original = PATH.read_text(encoding='utf-8')
if MARK in original and complete(original):
    print('Zenith V6 recovery already installed. No changes made.')
    sys.exit(0)

needs_recovery = not complete(original)
if needs_recovery:
    # Only use the immediate pre-V6 backup (the most accurate, preserving V5).
    backups = sorted(PATH.parent.glob('kits.ts.before_zenith_pose_v6_*.bak'),
                     key=lambda f: f.stat().st_mtime, reverse=True)
    match = next(((p, p.read_text(encoding='utf-8')) for p in backups
                  if complete(p.read_text(encoding='utf-8'))), None)
    if match is None:
        sys.exit('RECOVERY BLOCKED: kits.ts is damaged, but no complete '
                 'kits.ts.before_zenith_pose_v6_*.bak file was found beside it. '
                 'Do not reinstall V6. Send me kits.ts and available kits.ts backups; '
                 'no files were changed.')
    backup_source, working = match
    print('Using intact original:', backup_source.name)
else:
    working = original
    print('kits.ts already complete; applying only safe Zenith pose adjustments.')

start_token = 'const ZENITH: Record<string, Pose> = {'
finish_token = 'const CHAINBLADE: Record<string, Pose> = {'
if working.count(start_token) != 1 or working.count(finish_token) != 1:
    sys.exit('PREFLIGHT ERROR: Zenith pose boundaries not unique. No changes made.')
start = working.index(start_token)
end = working.index(finish_token, start)
section = working[start:end]

for pose_name, new_line in POSE_LINES.items():
    # Exact single-line replacement, never crossing a closing brace or other character.
    pattern = re.compile(r'(?m)^  ' + re.escape(pose_name) + r': P\([^\n]*\),$')
    section, count = pattern.subn(lambda _match, line=new_line: line, section)
    if count != 1:
        sys.exit(f'PREFLIGHT ERROR: expected Zenith pose {pose_name} exactly once, '
                 f'found {count}; no changes made.')

# Reintroduce V5-exclusive poses if they had already been removed from a prior
# damaged file? Here we restore from the exact intact pre-V6 backup, so they stay.
if 'ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108' in working:
    for pose in ('znt1_w:', 'znt5_s:', 'zncatch_w:', 'zncatch_s:'):
        if pose not in section:
            sys.exit(f'PREFLIGHT ERROR: Missing V5 choreography pose {pose}. '
                     'No files changed.')

if MARK not in working:
    section = '  // ' + MARK + ': spear style without removing other kits.\n' + section
updated = working[:start] + section + working[end:]
if not complete(updated):
    sys.exit('PREFLIGHT ERROR: full kit validation failed. No files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
safety = PATH.with_name(f'kits.ts.before_v6_recovery_{stamp}.bak')
shutil.copy2(PATH, safety)
# Atomic replace: write a temporary file then swap. All preflight happens above.
temporary = PATH.with_name('kits.ts.zenith_repair_tmp')
try:
    temporary.write_text(updated, encoding='utf-8')
    temporary.replace(PATH)
except OSError as exc:
    sys.exit(f'WRITE ERROR: {exc}. Original still saved at {safety.name}.')
print('Fixed:', PATH)
print('Safety backup:', safety.name)
print('Restored lost game code and safely applied 20 Zenith spear pose changes.')
print('Preserved V5 dual blades, charged overhead spear, catch recoil, and other characters.')
print('Now run: npx tsc --noEmit -p .')
print('Then run: npm run build')
