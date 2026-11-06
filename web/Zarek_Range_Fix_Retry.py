#!/usr/bin/env python3
"""Fight Royale — Zarek glaive visual-versus-hit-range calibration.

Copy into web/ beside package.json and run:
    py install_zarek_weapon_range_match_v1.py

Only edits Zarek's weapon scale and melee reach. Preserves V3/V4 parry AI,
combo timings, damage, cooldowns, all other characters, and snapshots.

A full preflight occurs BEFORE any file is modified; dated backups are created.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
MARK = 'ZAREK_WEAPON_RANGE_MATCH_V1_NOV06'
FILES = ('src/game/kits.ts', 'src/game/model.ts', 'src/game/game.ts')

# In VRM mode the original glaive shaft+blades are shrunk to 0.68x, leaving
# a small weapon while gameplay still has ~2.3 units of attack reach.
# At 0.95x the projected weapon + extended arm and enemy body radius are much
# closer to the effective hit distances below.
VRM_GLAIVE_SCALE = 0.95

# Effective distances between fighter centers on same elevation, before lunge.
# These values are used by BOTH the CPU's reach-based decisions and game hit
# detection because they modify each Attack.reach, not just the renderer.
ZAREK_REACH = {
    'l1': 2.05,
    'l2': 2.10,
    'l3': 2.08,
    'l4': 2.12,
    'l5': 2.18,
    'heavy': 2.34,
    'z': 2.06,
    'x': 2.18,
    'c': 2.18,
}


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected exactly one occurrence of {old[:100]!r}, found {count}')
    return text.replace(old, new, 1)


def patch_kits(s: str) -> str:
    label = 'src/game/kits.ts'
    start_marker = 'function glaive(): Record<string, Attack> {'
    stop_marker = '\nfunction sickle(): Record<string, Attack> {'
    if s.count(start_marker) != 1:
        raise ValueError(f'{label}: glaive() was not found exactly once')
    a = s.index(start_marker)
    b = s.find(stop_marker, a)
    if b == -1:
        raise ValueError(f'{label}: unable to isolate the Zarek kit')
    section = s[a:b]
    # Split each action at its own "key: a({...})" header, including multiline skills.
    skill_heads = list(re.finditer(r'(?m)^\s*(l[1-5]|heavy|z|x|c):\s*a\(\{', section))
    keys = [m.group(1) for m in skill_heads]
    if len(keys) != len(ZAREK_REACH) or set(keys) != set(ZAREK_REACH):
        raise ValueError(f'{label}: expected {list(ZAREK_REACH)}, found {keys}')
    changed = []
    for i, m in enumerate(skill_heads):
        end = skill_heads[i + 1].start() if i + 1 < len(skill_heads) else len(section)
        part = section[m.start():end]
        hit = re.search(r'\breach:\s*(\d+(?:\.\d+)?)', part)
        if not hit:
            raise ValueError(f'{label}: Zarek {m.group(1)} has no reach value')
        current = float(hit.group(1))
        if not 1.8 <= current <= 3.1:
            raise ValueError(f'{label}: unexpected reach {current} for Zarek {m.group(1)}; no files changed')
        part = part[:hit.start(1)] + str(ZAREK_REACH[m.group(1)]) + part[hit.end(1):]
        changed.append(part)
    section = section[:skill_heads[0].start()] + ''.join(changed)
    section = section.replace(start_marker, start_marker + '\n  // ' + MARK + ': visible blade and active combat reach are calibrated together.', 1)
    return s[:a] + section + s[b:]


def patch_model(s: str) -> str:
    label = 'src/game/model.ts'
    old = '    for (const h of [this.hand_l, this.hand_r]) h.scale.multiplyScalar(VRM_WEAPON_SCALE);'
    new = (f'    // {MARK}: keep Zarek\'s long double-ended blade visible on VRM bodies.\n'
           f'    const weaponScale = this.kit === "glaive" ? {VRM_GLAIVE_SCALE} : VRM_WEAPON_SCALE;\n'
           '    for (const h of [this.hand_l, this.hand_r]) h.scale.multiplyScalar(weaponScale);')
    if 'const VRM_WEAPON_SCALE = 0.68;' not in s:
        raise ValueError(f'{label}: expected base VRM weapon scaling anchor is missing')
    if 'this.gripL = pivot(staff, [0, -0.29, 0]);' not in s or 'this.bladeTip = pivot(staff, [0, 1.38, 0]);' not in s:
        raise ValueError(f'{label}: glaive mesh dimensions differ from verified source')
    return once(s, old, new, label)


def patch_game(s: str) -> str:
    label = 'src/game/game.ts'
    # Infinite Crescent overwrites Attack.reach for its staged hits: it MUST
    # be calibrated as well or the special would retain its old invisible reach.
    s = once(s,
        '            reach: final ? 2.65 : 2.4,',
        f'            // {MARK}: use the same visible-length calibration as the glaive.\n'
        '            reach: final ? 2.34 : 2.18,', label)
    # The melee clash check added an extra 0.30-unit buffer independent of the
    # hitbox. Keep modest weapon-on-weapon slack without long-distance clashes.
    s = once(s,
        '&& dist <= a.reach + 0.3 &&',
        '&& dist <= a.reach + (f.kit === "glaive" ? 0.12 : 0.3) &&', label)
    return s


def main() -> int:
    if not (ROOT / 'package.json').is_file():
        print('ERROR: place this installer in your web/ folder beside package.json.', file=sys.stderr)
        return 1
    missing = [n for n in FILES if not (ROOT / n).is_file()]
    if missing:
        print('ERROR: source files missing: ' + ', '.join(missing), file=sys.stderr)
        return 1
    old = {name: (ROOT / name).read_text(encoding='utf-8') for name in FILES}
    installed = [MARK in old[name] for name in FILES]
    if all(installed):
        print('Already installed. No files changed.')
        return 0
    if any(installed):
        print('ERROR: partial Zarek range installation detected. No files changed.', file=sys.stderr)
        return 1
    try:
        updated = {'src/game/kits.ts': patch_kits(old['src/game/kits.ts']),
                   'src/game/model.ts': patch_model(old['src/game/model.ts']),
                   'src/game/game.ts': patch_game(old['src/game/game.ts'])}
        if not all(MARK in updated[name] for name in FILES):
            raise ValueError('installer marker missing from an output')
    except Exception as exc:
        print('ERROR preflight: ' + str(exc) + '. No files changed.', file=sys.stderr)
        return 1
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for name in FILES:
        path = ROOT / name
        backup = path.with_name(path.name + f'.before_zarek_range_{stamp}.bak')
        shutil.copy2(path, backup)
        temp = path.with_name(path.name + '.zarekrangetmp')
        temp.write_text(updated[name], encoding='utf-8')
        temp.replace(path)
        print(f'PATCH {name} (backup {backup.name})')
    print('DONE: Zarek VRM glaive now 0.95x instead of 0.68x; attack hit ranges matched to blade; infinite finisher/clash reach aligned.')
    print('No damage, animations, parry/clash penalties, CPU scripts, or other character kits changed.')
    print('Now run: npx tsc --noEmit; npm run build; npm run dev')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
