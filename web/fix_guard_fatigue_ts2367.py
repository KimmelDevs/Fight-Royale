#!/usr/bin/env python3
"""Fix TS2367 in Fight Royale's guardFatigueTactics without touching sounds or other AI logic.

Run from the Fight Royale web directory:
    python fix_guard_fatigue_ts2367.py --dry-run
    python fix_guard_fatigue_ts2367.py
"""
from __future__ import annotations
import argparse
import datetime as dt
from pathlib import Path
import re
import shutil
import sys

PATTERN = re.compile(
    r'(?P<indent>^[ \t]*)o\.guard[ \t]*<[ \t]*o\.maxGuard[ \t]*\*[ \t]*0\.30[ \t]*\|\|[ \t]*\r?\n'
    r'[ \t]*\(o\.state[ \t]*===[ \t]*S\.ATTACK[ \t]*&&[ \t]*o\.atkPhase[ \t]*<[ \t]*2\)\)',
    re.MULTILINE,
)

def main() -> int:
    parser = argparse.ArgumentParser(description='Fix TS2367 in src/game/ai.ts (guard fatigue tactics).')
    parser.add_argument('--dry-run', action='store_true', help='Verify the target without changing files')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Fight Royale web directory')
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    target = root / 'src' / 'game' / 'ai.ts'
    if not target.is_file():
        print(f'ERROR: Missing {target}. Run this from your web folder.', file=sys.stderr)
        return 1
    raw = target.read_bytes()
    try:
        code = raw.decode('utf-8')
    except UnicodeDecodeError:
        print('ERROR: ai.ts is not UTF-8; no files changed.', file=sys.stderr)
        return 1
    begin = code.find('private guardFatigueTactics(')
    if begin == -1:
        print('ERROR: guardFatigueTactics not found. Your AI differs from the uploaded source; no files changed.', file=sys.stderr)
        return 1
    end = code.find('const danger', begin)
    if end == -1:
        print('ERROR: Guard fatigue condition could not be isolated; no files changed.', file=sys.stderr)
        return 1
    segment = code[begin:end]
    matches = list(PATTERN.finditer(segment))
    if len(matches) == 0 and re.search(r'o\.guard\s*<\s*o\.maxGuard\s*\*\s*0\.30\s*\)', segment):
        print('Already fixed; no files changed.')
        return 0
    if len(matches) != 1:
        print(f'ERROR: Expected exactly one target condition, found {len(matches)}; no files changed.', file=sys.stderr)
        return 1
    patched = PATTERN.sub(lambda m: m.group('indent') + 'o.guard < o.maxGuard * 0.30)', segment)
    newcode = code[:begin] + patched + code[end:]
    if args.dry_run:
        print('DRY RUN OK: Found the redundant BLOCK/ATTACK condition in guardFatigueTactics.')
        print('Would remove only that comparison from src/game/ai.ts.')
        return 0
    backup = target.with_name('ai.ts.before_fix_ts2367_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    shutil.copy2(target, backup)
    try:
        target.write_bytes(newcode.encode('utf-8'))
    except Exception:
        shutil.copy2(backup, target)
        raise
    print('Fixed: src/game/ai.ts (TS2367 in guardFatigueTactics)')
    print(f'Backup: {backup.name}')
    print('Next: npx tsc --noEmit -p .')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
