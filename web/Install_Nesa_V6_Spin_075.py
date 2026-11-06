#!/usr/bin/env python3
"""Fight Royale Nesa V6: adjust ONLY ground/air charge-spin duration from 1:0.5 to 1:0.75.

Run from the Fight Royale web folder:
    python Install_Nesa_V6_Spin_075.py

Optionally pass the project path or use --check for a no-write preview.
Requires the Nesa V5 update to have been installed already.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys
import tempfile

OLD_GROUND = 'const spin = (0.34 + (held - HOLD_T) * 0.77) * 0.50; // Nesa V5: hold:spin conversion 1:0.5'
NEW_GROUND = 'const spin = (0.34 + (held - HOLD_T) * 0.77) * 0.75; // Nesa V6: hold:spin conversion 1:0.75'
OLD_AIR = 'const airSpin = (0.34 + ratio * 0.76) * 0.50;'
NEW_AIR = 'const airSpin = (0.34 + ratio * 0.76) * 0.75;'
OLD_COMMENT = '// 1s earned spin becomes 0.5s, as on the ground; shorter hold = fewer revolutions.'
NEW_COMMENT = '// 1s earned spin becomes 0.75s, as on the ground; shorter hold = fewer revolutions.'


def root_for(raw: str | None) -> Path:
    start = Path(raw).expanduser().resolve() if raw else Path.cwd()
    for candidate in (start, start / 'web'):
        if (candidate / 'src/game/fighter.ts').is_file() and (candidate / 'src/game/kits.ts').is_file():
            return candidate
    raise RuntimeError('Fight Royale web project not found. Run in your web folder or pass its path.')


def patch(s: str) -> str:
    if NEW_GROUND in s and NEW_AIR in s:
        return s  # Already installed; don't touch unrelated code.
    for label, before, after in (
        ('ground charge spin', OLD_GROUND, NEW_GROUND),
        ('aerial charge spin', OLD_AIR, NEW_AIR),
        ('aerial spin explanation', OLD_COMMENT, NEW_COMMENT),
    ):
        if after in s:
            continue
        count = s.count(before)
        if count != 1:
            raise RuntimeError(f'{label}: expected the Nesa V5 anchor once, found {count}. No changes made.')
        s = s.replace(before, after, 1)
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description='Nesa V6 charge spin 1:0.75, no other balance changes')
    ap.add_argument('project', nargs='?', help='Fight Royale repo root or web directory')
    ap.add_argument('--check', action='store_true', help='Show patch without writing')
    args = ap.parse_args()
    root = root_for(args.project)
    path = root / 'src/game/fighter.ts'
    original = path.read_text(encoding='utf-8')
    updated = patch(original)
    print('Fight Royale project:', root)
    if updated == original:
        print('[OK] Nesa 1:0.75 ground and air spin scaling is already installed.')
        return
    if args.check:
        print('[CHECK] Ready: ground spin and aerial spin 0.50 -> 0.75. No files modified.')
        return
    backup = root / '.nesa_installer_backups' / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_spin075')
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(path, backup / 'fighter.ts')
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='', dir=path.parent, delete=False) as f:
            f.write(updated)
            tmp = Path(f.name)
        os.replace(tmp, path)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()
    print('[OK] Nesa ground and aerial spin: hold-to-spin factor 0.75 (was 0.50).')
    print('[OK] Damage, cooldowns, skills, and other fighters unchanged.')
    print('Backup:', backup)
    print('Next: npm run dev')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as error:
        print('INSTALL FAILED:', error)
        sys.exit(1)
