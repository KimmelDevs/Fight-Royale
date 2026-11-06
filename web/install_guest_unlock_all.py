#!/usr/bin/env python3
"""Unlock all existing and future characters in Guest Mode only.

Run from the Fight Royale web folder (the folder containing package.json):
    py install_guest_unlock_all.py

Only changes src/lib/account.ts. Does NOT unlock bonus V skills or alter
Supabase/signed-in profiles. Creates a backup before changing anything.
"""

from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "src" / "lib" / "account.ts"
BACKUP = TARGET.with_name("account.ts.before_guest_unlock.bak")

PATTERN = re.compile(
    r'(?m)^(?P<indent>[ \t]*)owns\(charId: string\)[ \t]*\{[ \t]*'
    r'return[ \t]+this\.profile\.characters\.includes\(charId\);[ \t]*\}'
)


def main() -> int:
    if not (ROOT / "package.json").is_file():
        print("ERROR: Put this script in your main web folder, beside package.json.")
        return 1
    if not TARGET.is_file():
        print(f"ERROR: File not found: {TARGET}")
        return 1

    source = TARGET.read_text(encoding="utf-8")
    match = PATTERN.search(source)
    if not match:
        # Verify if our intended change has already been applied.
        already = re.search(
            r'owns\(charId: string\)[ \t]*\{\s*'
            r'//[^\n]*\n\s*if\s*\(!this\.signedIn\)\s*return\s+true;',
            source,
        )
        if already:
            print("Already installed: Guest Mode already unlocks all characters.")
            return 0
        print("ERROR: Could not find the expected owns(charId) function. No changes made.")
        print("Share your current src/lib/account.ts so I can make a compatible patch.")
        return 1

    # No changes to ownsSkill(); bonus V skills remain separately unlockable.
    indent = match.group("indent")
    replacement = (
        f'{indent}owns(charId: string) {{\n'
        f'{indent}  // Guest Mode: all current and future roster characters are playable.\n'
        f'{indent}  if (!this.signedIn) return true;\n'
        f'{indent}  // Signed-in accounts still use their purchased/unlocked characters.\n'
        f'{indent}  return this.profile.characters.includes(charId);\n'
        f'{indent}}}'
    )
    updated = source[:match.start()] + replacement + source[match.end():]
    if not BACKUP.exists():
        shutil.copy2(TARGET, BACKUP)
    TARGET.write_text(updated, encoding="utf-8")
    print("SUCCESS: Guest Mode now has all characters unlocked.")
    print("Modified: src/lib/account.ts")
    print("Backup: src/lib/account.ts.before_guest_unlock.bak")
    print("Signed-in purchases unchanged; bonus V skills unchanged.")
    print("Next: npx tsc --noEmit && npm run dev")
    return 0


if __name__ == "__main__":
    sys.exit(main())
