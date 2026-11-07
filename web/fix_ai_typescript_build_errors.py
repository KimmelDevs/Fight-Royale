#!/usr/bin/env python3
"""Fix six Fight Royale TypeScript build errors from Combat IQ + Last Stand V2.

Place this file in the `web` folder and run:
    python fix_ai_typescript_build_errors.py

Changes only src/game/ai.ts and src/game/fighter.ts. Makes timestamped backups.
Safe to run again; no skill, gameplay, or AI decisions are removed.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import sys
from pathlib import Path


SURVIVAL_DECL = re.compile(
    r'(?m)^(?P<prefix>[ \t]*private survivalMode:[ \t]*)'
    r'(?P<union>"[^"\r\n]+"(?:[ \t]*\|[ \t]*"[^"\r\n]+")*)'
    r'(?P<suffix>[ \t]*=[ \t]*"none";)'
)
BAD_STUN = 'const left = Math.max(0, o.stun - o.stateT);'
GOOD_STUN = 'const left = Math.max(0, o.stunRemaining);'
PRIVATE_STUN = '  private stun = 0;'
GETTER = '''  /** Public, read-only remaining hitstun for timing legitimate Combat IQ follow-ups. */
  get stunRemaining(): number {
    return (this.state === S.HITSTUN || this.state === S.STAGGER)
      ? Math.max(0, this.stun - this.stateT)
      : 0;
  }
'''


def patch(ai: str, fighter: str) -> tuple[str, str, list[str]]:
    edits = []
    matches = list(SURVIVAL_DECL.finditer(ai))
    if len(matches) != 1:
        raise ValueError('Expected exactly one survivalMode declaration in src/game/ai.ts; found ' + str(len(matches)))
    m = matches[0]
    entries = [x.strip() for x in m.group('union').split('|')]
    missing = [s for s in ('"lastStand"', '"pressure"') if s not in entries]
    if missing:
        new_decl = m.group('prefix') + ' | '.join(entries + missing) + m.group('suffix')
        ai = ai[:m.start()] + new_decl + ai[m.end():]
        edits.append('Allow lastStand and pressure in survivalMode')

    occurrences = ai.count(BAD_STUN)
    if occurrences > 1:
        raise ValueError('Found multiple Combat IQ stun reads; refusing an ambiguous patch')
    if occurrences == 1:
        ai = ai.replace(BAD_STUN, GOOD_STUN, 1)
        edits.append('Make Combat IQ read the public remaining-stun getter')
    elif GOOD_STUN not in ai:
        raise ValueError('Could not locate the Combat IQ stun read in ai.ts')

    if 'get stunRemaining()' not in fighter:
        if fighter.count(PRIVATE_STUN) != 1:
            raise ValueError('Expected one private stun property in fighter.ts')
        fighter = fighter.replace(PRIVATE_STUN, PRIVATE_STUN + '\n' + GETTER, 1)
        edits.append('Expose remaining hitstun as a safe read-only Fighter getter')

    # Fail before writing if the expected six-error repair was not fully achieved.
    assert BAD_STUN not in ai
    assert '"lastStand"' in SURVIVAL_DECL.search(ai).group('union')
    assert '"pressure"' in SURVIVAL_DECL.search(ai).group('union')
    assert 'get stunRemaining()' in fighter
    return ai, fighter, edits


def main() -> int:
    root = Path(__file__).resolve().parent
    ai_file = root / 'src/game/ai.ts'
    fighter_file = root / 'src/game/fighter.ts'
    if not ai_file.is_file() or not fighter_file.is_file():
        print('ERROR: Put this Python installer in the web folder alongside src/ and run it there.', file=sys.stderr)
        return 1

    # Read and verify all edits before modifying either file.
    try:
        old_ai = ai_file.read_text(encoding='utf-8')
        old_fighter = fighter_file.read_text(encoding='utf-8')
        new_ai, new_fighter, edits = patch(old_ai, old_fighter)
    except (OSError, UnicodeError, ValueError, AssertionError) as exc:
        print(f'INSTALLATION FAILED: {exc}. No files were changed.', file=sys.stderr)
        return 1

    if not edits:
        print('Already fixed — no changes needed.')
        return 0

    updates = [(ai_file, old_ai, new_ai), (fighter_file, old_fighter, new_fighter)]
    updates = [(p, before, after) for p, before, after in updates if before != after]
    suffix = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        # Back up everything first, then write. Exact text/newline layout is preserved.
        for path, _, _ in updates:
            backup = path.with_name(path.name + f'.before_ts_build_fix_{suffix}.bak')
            shutil.copy2(path, backup)
            print('Backup:', backup.relative_to(root))
        for path, _, updated in updates:
            path.write_text(updated, encoding='utf-8', newline='')
            print('Patched:', path.relative_to(root))
    except OSError as exc:
        print(f'WRITE FAILED: {exc}. Original files are in timestamped backups.', file=sys.stderr)
        return 1

    print('\nFIXED:')
    for edit in edits:
        print(' -', edit)
    print('\nNow run: npx tsc --noEmit -p .')
    print('Then:    npm run build')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
