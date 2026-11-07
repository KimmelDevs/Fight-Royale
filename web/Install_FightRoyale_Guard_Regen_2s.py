#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale — global guard regeneration cooldown after damage.

After either guard damage or health damage, guard regeneration waits until the
fighter has gone two continuous seconds without taking damage. Existing guard
regeneration rates remain unchanged; holding block still prevents regeneration.

Usage:
  python Install_FightRoyale_Guard_Regen_2s.py
  python Install_FightRoyale_Guard_Regen_2s.py "C:\\path\\to\\Fight-Royale\\web"
  python Install_FightRoyale_Guard_Regen_2s.py --check

No pip packages required. Backups under web/.fightroyale_guard_backups/.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

MARKER = 'FIGHT_ROYALE_GUARD_REGEN_DAMAGE_DELAY_V1'
TARGET = 'src/game/fighter.ts'

class PatchError(RuntimeError):
    pass


def replace_exact_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise PatchError(f'{label}: expected a single code match, found {count}. '
                         'Your fighter.ts differs from the supported version; no files changed.')
    return source.replace(old, new, 1)


def patch_fighter(source: str) -> str:
    if MARKER in source:
        return source

    source = replace_exact_once(
        source,
        'const GUARD_REGEN = 30;',
        'const GUARD_REGEN = 30;\n'
        '// ' + MARKER + ': continuous damage-free seconds before guard can regenerate.\n'
        'const GUARD_REGEN_DAMAGE_DELAY = 2.0;',
        'Guard regeneration configuration',
    )

    source = replace_exact_once(
        source,
        '''    if (this.state !== S.BLOCK) {
      this.guardDelay -= dt;
      if (this.guardDelay <= 0) {
        // KAIZEN_GUARD_CLASH_V8: Kaizen regenerates guard at half the usual rate.
        const guardRegen = this.kit === "chainblade" ? GUARD_REGEN * 0.5 : GUARD_REGEN;
        this.guard = Math.min(this.guard + guardRegen * dt, this.maxGuard);
      }
    }''',
        '''    // Count down the two-second damage-free timer even while defending.
    // Holding block still prevents actual guard regeneration, just as before.
    this.guardDelay = Math.max(0, this.guardDelay - dt);
    if (this.state !== S.BLOCK && this.guardDelay <= 0) {
      // KAIZEN_GUARD_CLASH_V8: Kaizen regenerates guard at half the usual rate.
      const guardRegen = this.kit === "chainblade" ? GUARD_REGEN * 0.5 : GUARD_REGEN;
      this.guard = Math.min(this.guard + guardRegen * dt, this.maxGuard);
    }''',
        'Guard regeneration clock',
    )

    source = replace_exact_once(
        source,
        '''    for (const d of st.dots) {
      this.hp = Math.max(this.hp - d.dmg, 0);
      this.dots.push({ ...d, src: this.status.src });''',
        '''    for (const d of st.dots) {
      this.hp = Math.max(this.hp - d.dmg, 0);
      // Damage-over-time counts as taking damage for guard recovery.
      if (d.dmg > 0) this.guardDelay = GUARD_REGEN_DAMAGE_DELAY;
      this.dots.push({ ...d, src: this.status.src });''',
        'Damage-over-time handling',
    )

    source = replace_exact_once(
        source,
        '      this.guardDelay = 1;',
        '      this.guardDelay = GUARD_REGEN_DAMAGE_DELAY;',
        'Blocked damage handling',
    )

    source = replace_exact_once(
        source,
        '''    if (this.stage) return this.launch(attacker, a, dmg);
    this.lastDamage = dmg;
    this.hp = Math.max(this.hp - dmg, 0);''',
        '''    // An unblocked hit also restarts guard recovery, even if the guard bar
    // itself did not change. Arena and platform combat use the same rule.
    if (dmg > 0) this.guardDelay = GUARD_REGEN_DAMAGE_DELAY;
    if (this.stage) return this.launch(attacker, a, dmg);
    this.lastDamage = dmg;
    this.hp = Math.max(this.hp - dmg, 0);''',
        'Unblocked damage handling',
    )

    source = replace_exact_once(
        source,
        '''    this.hp = this.maxHp * frac;
    this.guard = this.maxGuard;''',
        '''    this.hp = this.maxHp * frac;
    this.guard = this.maxGuard;
    this.guardDelay = 0; // Fresh round: no guard recovery penalty carries over.''',
        'Revive timer reset',
    )
    return source


def resolve_root(given: str | None) -> Path:
    start = Path(given).expanduser().resolve() if given else Path.cwd().resolve()
    for directory in (start, start / 'web'):
        if (directory / TARGET).is_file():
            return directory
    raise PatchError('Cannot locate src/game/fighter.ts. Run in your web folder or pass its path.')


def main() -> None:
    parser = argparse.ArgumentParser(description='Global guard regen: 2 seconds without taking damage')
    parser.add_argument('project', nargs='?', help='Fight Royale web folder (optional when run inside it)')
    parser.add_argument('--check', action='store_true', help='Validate code anchors without writing')
    args = parser.parse_args()
    root = resolve_root(args.project)
    file = root / TARGET
    old = file.read_text(encoding='utf-8')
    new = patch_fighter(old)
    if new == old:
        print('[OK] Guard regeneration 2-second damage cooldown is already installed.')
        return
    if args.check:
        print('[CHECK PASSED] The 2-second guard regeneration patch matches your source.')
        return

    backup_dir = root / '.fightroyale_guard_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup_file = backup_dir / TARGET
    backup_file.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(file, backup_file)

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=file.parent, delete=False) as handle:
            temp_file = Path(handle.name)
            handle.write(new)
        os.replace(temp_file, file)
    finally:
        if temp_file is not None and temp_file.exists():
            temp_file.unlink()

    print('[DONE] Global guard regen now waits 2.0 seconds after damage.')
    print('[OK] Guard regen speed and all character stats remain unchanged.')
    print('Backup:', backup_file)
    print('Then run: npx tsc --noEmit -p .   and   npm run dev')


if __name__ == '__main__':
    try:
        main()
    except (PatchError, OSError, UnicodeError) as error:
        print('[ERROR]', error, file=sys.stderr)
        raise SystemExit(1)
