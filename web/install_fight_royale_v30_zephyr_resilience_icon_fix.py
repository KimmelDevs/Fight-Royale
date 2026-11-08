#!/usr/bin/env python3
"""FIGHT ROYALE V30 — Zephyr resilience nerf + missing passive icon repair.

Usage (from fight-royale/web):
    python install_fight_royale_v30_zephyr_resilience_icon_fix.py

Or specify web directory:
    python install_fight_royale_v30_zephyr_resilience_icon_fix.py "C:/path/to/fight-royale/web"

Requires a game source with ZEPHYR_PASSIVE_TUNING (Zephyr V25 through V29).
Compatible with the V29 source structure; no V29-specific anchors required.
All sources checked before writes; timestamped backups; no dependencies; no Git commands.
"""
from __future__ import annotations

import base64
import datetime
import os
from pathlib import Path
import re
import shutil
import sys

MARK = "FIGHT_ROYALE_V30_ZEPHYR_RESILIENCE_ICON"
FIGHTER = Path('src/game/fighter.ts')
ROSTER = Path('src/game/roster.ts')
ICON = Path('public/icons/passives/zephyr.webp')

# 128px Dragon Rhythm WebP icon, reused from Zephyr's original passive skill art.
# Embedded to allow this one installer to fix the missing asset independently.
ICON_B64 = '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'


def update_fighter(text: str) -> tuple[str, str]:
    """Change Zephyr's 20% incoming damage reduction to 10%."""
    anchor = 'export const ZEPHYR_PASSIVE_TUNING = {'
    if text.count(anchor) != 1:
        raise RuntimeError('Missing unique ZEPHYR_PASSIVE_TUNING; install V25+ first.')
    beg = text.index(anchor)
    end = text.find('} as const;', beg)
    if end < 0 or end - beg > 2000:
        raise RuntimeError('ZEPHYR_PASSIVE_TUNING has unexpected structure; refusing to guess.')
    end += len('} as const;')
    section = text[beg:end]
    p = re.compile(r'(?m)^([ \t]*damageTakenMult[ \t]*:[ \t]*)(0\.(?:80|8|90|9))([ \t]*,[ \t]*)(?://[^\n]*)?$')
    matches = list(p.finditer(section))
    if len(matches) != 1:
        raise RuntimeError('Zephyr damageTakenMult is not a known V25–V29 value (0.80/0.90); no changes made.')
    old_value = float(matches[0].group(2))
    if abs(old_value - 0.9) < 0.0001 and MARK in section:
        return text, 'Already nerfed to 10%'
    section2 = p.sub(lambda m: m.group(1) + '0.90' + m.group(3) + '// 10% less incoming HP damage — ' + MARK, section)
    new_text = text[:beg] + section2 + text[end:]
    new_text = new_text.replace('on top (0.8 * 1.1)', 'on top (0.9 * 1.1)')
    return new_text, ('20% -> 10%' if old_value < .9 else 'Already at 10%; added version marker')


def update_roster(text: str) -> tuple[str, str]:
    # Scope to Zephyr's roster entry to avoid changing other fighters' descriptions.
    begin = text.find('id: "zephyr"')
    if begin < 0:
        raise RuntimeError('Zephyr is not in src/game/roster.ts; no files changed.')
    next_entry = text.find('id: "', begin + 5)
    end = next_entry if next_entry >= 0 else min(len(text), begin + 3000)
    section = text[begin:end]
    if '20% less incoming damage' in section:
        section2 = section.replace('20% less incoming damage', '10% less incoming damage', 1)
        return text[:begin] + section2 + text[end:], 'Description changed to 10%'
    if '10% less incoming damage' in section:
        return text, 'Description already says 10%'
    return text, 'Description wording does not need a change'


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').expanduser().resolve()
    print('FIGHT ROYALE V30 — ZEPHYR NERF + PASSIVE ICON | target:', root)
    try:
        sources = {}
        for rel in (FIGHTER, ROSTER):
            path = root / rel
            if not path.is_file():
                raise RuntimeError(f'Missing {rel}: run from fight-royale/web or pass its path.')
            sources[rel] = path.read_text(encoding='utf-8-sig')
        out_fighter, result_fighter = update_fighter(sources[FIGHTER])
        out_roster, result_roster = update_roster(sources[ROSTER])
        updates = {}
        if out_fighter != sources[FIGHTER]: updates[FIGHTER] = out_fighter
        if out_roster != sources[ROSTER]: updates[ROSTER] = out_roster
        icon_path = root / ICON
        add_icon = not icon_path.is_file()
        icon_data = base64.b64decode(ICON_B64, validate=True)
        if icon_data[:4] != b'RIFF' or icon_data[8:12] != b'WEBP':
            raise RuntimeError('Embedded icon failed WebP verification.')
        if not updates and not add_icon:
            print('Already installed: 10% reduction and passive icon present. No changes.')
            return 0
        # All anchors and payload validated. Backup before writing anything.
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = root / '.zephyr-backups' / ('v30-' + stamp)
        for rel in updates:
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dest)
        written = []
        try:
            for rel, content in updates.items():
                path = root / rel
                tmp = path.with_name(path.name + '.v30tmp')
                try:
                    tmp.write_text(content, encoding='utf-8')
                    os.replace(tmp, path)
                finally:
                    if tmp.exists(): tmp.unlink()
                written.append(rel)
                print('  updated', rel)
            if add_icon:
                icon_path.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive create: never overwrite an existing user icon.
                with icon_path.open('xb') as fh:
                    fh.write(icon_data)
                print('  created', ICON, f'({len(icon_data)} bytes)')
        except Exception:
            for rel in reversed(written):
                shutil.copy2(backup / rel, root / rel)
            raise
        print('  damage nerf:', result_fighter)
        print('  roster:', result_roster)
        print('  existing icon preserved' if not add_icon else '  Zephyr passive 404 fixed')
        print('  backup:', backup)
        print('Done. Run: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
