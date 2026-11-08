#!/usr/bin/env python3
"""Fight Royale V13 — lower only starting attack speed for Nythera and Zenith.

Run from fight-royale/web:
    python install_nythera_zenith_speed_v13.py
Or pass a path to the web directory:
    python install_nythera_zenith_speed_v13.py "C:\\path\\to\\fight-royale\\web"

For the V12 codebase. No pip packages required.

Nythera: 0.80x base speed (was 1.00x); still reaches V12's 1.70x
  at 14 successful Dreadfall hits. The 0.20x starting penalty fades as
  stacks are earned; full-stack speed remains unchanged.
Zenith: 0.70x spear / 1.70x twin blades (were 1.00x / 2.00x),
  keeping +0.01x per hit, 14 stacks, 5-second expiry and prior ceilings.

All basic and skill attack phases use the same real Fighter attack-speed
functions. Zenith's scheduled Z/V strikes use the updated tempo too.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

TAG = 'NYTHERA_ZENITH_START_SPEED_V13'


def swap(s: str, before: str, after: str, name: str) -> str:
    n = s.count(before)
    if n != 1:
        raise ValueError(f'{name}: expected one V12 source anchor; found {n}: {before[:100]!r}')
    return s.replace(before, after, 1)


def patch_fighter(s: str) -> str:
    if TAG in s:
        return s
    s = swap(s,
        '  nytheraAttackSpeed(): number { return Math.min(1.7, 1 + Math.min(14, this.nytheraDreadfallHits) * 0.05); } // NYTHERA_BALANCE_CPU_COMPACT_V12',
        '  // ' + TAG + ': 0.80x starting speed, retaining 1.70x at full 14 Dreadfall hits.\n'
        '  // The initial 0.20x penalty fades over the same 14 earned stacks.\n'
        '  nytheraAttackSpeed(): number {\n'
        '    const stacks = Math.max(0, Math.min(14, this.nytheraDreadfallHits));\n'
        '    return Math.min(1.7, 0.80 + stacks * 0.05 + 0.20 * stacks / 14);\n'
        '  }',
        'Nythera attack speed')
    s = swap(s,
        '  zenithAttackSpeed() {\n'
        '    const bonus = Math.min(14, this.zenithTempoStacks) * 0.01;\n'
        '    return this.zenithSpearOut ? Math.min(3.4, 2 + bonus) : Math.min(2.4, 1 + bonus);\n'
        '  }',
        '  // ' + TAG + ': decrease spear and twin-blade starting attack speed by 0.30x.\n'
        '  zenithAttackSpeed() {\n'
        '    const bonus = Math.min(14, this.zenithTempoStacks) * 0.01;\n'
        '    return this.zenithSpearOut ? Math.min(3.4, 1.70 + bonus) : Math.min(2.4, 0.70 + bonus);\n'
        '  }',
        'Zenith attack speed')
    s = swap(s,
        '    // Actual current ceiling: 1.14x spear / 2.14x twin blades (14-stack cap).',
        '    // ' + TAG + ': 0.70-0.84x spear / 1.70-1.84x twin blades at 0-14 stacks.',
        'Zenith implementation comment')
    return s


def patch_game(s: str) -> str:
    if TAG in s:
        return s
    s = swap(s,
        'desc: "Orbit Marks last 25s; Dreadfall strikes gain +0.05× attack speed, max 1.70× for the round. Four air slices remain. Base scythe attacks: −10% damage; skills: −20%."',
        'desc: "Orbit Marks last 25s; Dreadfall speed begins at 0.80× and grows to 1.70× over 14 damaging hits (round only). Four air slices remain. Base scythe attacks: −10% damage; skills: −20%."',
        'Nythera passive description')
    # Keep the live value supplied by f.nytheraAttackSpeed() and f.zenithAttackSpeed().
    # No separate combat values are edited here.
    return s + '\n// ' + TAG + ': passive descriptions updated for V13 starting speeds.\n'


def patch_view(s: str) -> str:
    if TAG in s:
        return s
    s = swap(s,
        '  const speed = Math.min(blades ? 3.4 : 2.4, (blades ? 2 : 1) + count * 0.01);',
        '  const speed = Math.min(blades ? 3.4 : 2.4, (blades ? 1.70 : 0.70) + count * 0.01); // ' + TAG,
        'Zenith HUD speed formula')
    s = swap(s,
        '  const speed = Math.min(1.7, 1 + stacks * 0.05);',
        '  const speed = Math.min(1.7, 0.80 + stacks * 0.05 + 0.20 * stacks / 14); // ' + TAG,
        'Nythera HUD speed formula')
    s = swap(s,
        '// Dreadfall increases Nythera\'s real attack speed by 0.1x per damaging hit.',
        '// Dreadfall starts at 0.80x and scales to 1.70x at 14 damaging hits.',
        'Nythera HUD comment')
    s = swap(s,
        'title="Dreadfall Tempo: every real damaging hit in Dreadfall earns +0.05x attack speed. Caps at 1.70x, persists through stance switches, resets next round. Block/parry/clash deny stacks."',
        'title="Dreadfall Tempo: starts at 0.80x attack speed; 14 real damaging Dreadfall hits raise it to 1.70x. Persists through stance switches, resets next round. Block/parry/clash deny stacks."',
        'Nythera HUD tooltip')
    return s


def web_folder() -> Path:
    if len(sys.argv) > 2:
        raise ValueError('Usage: python install_nythera_zenith_speed_v13.py [web folder]')
    if len(sys.argv) == 2:
        path = Path(sys.argv[1]).expanduser().resolve()
        if (path / 'src/game/fighter.ts').is_file():
            return path
        raise FileNotFoundError(f'Not a Fight Royale web directory: {path}')
    root = Path(__file__).resolve().parent
    for p in [root, Path.cwd(), root / 'web', Path.cwd() / 'web']:
        if (p / 'src/game/fighter.ts').is_file() and (p / 'src/ui/GameView.tsx').is_file():
            return p.resolve()
    raise FileNotFoundError('Put this installer in fight-royale/web or provide the web folder path.')


def main() -> int:
    try:
        root = web_folder()
        changes = []
        # Validate all source versions *before* writing anything.
        for filename, transform in [
            ('src/game/fighter.ts', patch_fighter),
            ('src/game/game.ts', patch_game),
            ('src/ui/GameView.tsx', patch_view),
        ]:
            path = root / filename
            old = path.read_text(encoding='utf-8')
            new = transform(old)
            if old != new:
                changes.append((path, filename, old, new))
        if not changes:
            print('V13 speed patch already installed. No files changed.')
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        prepared, replaced = [], []
        try:
            for path, filename, old, new in changes:
                backup = path.with_name(f'{path.name}.before_{TAG}_{stamp}.bak')
                temp = path.with_name(f'{path.name}.{TAG}.tmp')
                backup.write_text(old, encoding='utf-8')
                temp.write_text(new, encoding='utf-8')
                prepared.append((path, filename, backup, temp))
            for path, filename, backup, temp in prepared:
                os.replace(temp, path)
                replaced.append((path, backup))
                print(f'UPDATED: {filename}')
        except Exception:
            for path, backup in reversed(replaced):
                shutil.copy2(backup, path)
            raise
        finally:
            for path, filename, backup, temp in prepared:
                if temp.exists():
                    temp.unlink()
        print('\nSUCCESS: V13 starting attack-speed nerf')
        print('  Nythera: starts 0.80x; reaches same 1.70x max at 14 Dreadfall hits.')
        print('  Zenith: spear 0.70x / twin blades 1.70x; +0.01x per hit; reset after 5s.')
        print('  No changes to damage, cooldowns, AI, scythe, or HUD layout.')
        print('  Original source backups saved beside changed files.')
        print('Check with: npx tsc --noEmit -p .')
        return 0
    except Exception as err:
        print('ERROR:', err)
        print('No partial changes should remain. Confirm your game has the V12 patch.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
