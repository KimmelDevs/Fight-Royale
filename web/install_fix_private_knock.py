"""Fix TypeScript TS2341 in Kaizen's game.ts by removing invalid private field access.

Run from the web/ folder: py install_fix_private_knock.py
"""
from pathlib import Path
from datetime import datetime

path = Path('src/game/game.ts')
if not path.is_file():
    raise SystemExit('ERROR: run this script inside your web folder (where package.json is).')

source = path.read_text(encoding='utf-8')
old = 'victim.vx = 0; victim.velY = 0; victim.knock = 0;'
new = 'victim.vx = 0; victim.velY = 0;'
if old in source:
    if source.count(old) != 1:
        raise SystemExit(f'ERROR: expected one matching statement; found {source.count(old)}. No changes made.')
    backup = path.with_name(f'{path.name}.before_private_knock_{datetime.now().strftime("%Y%m%d_%H%M%S")}.bak')
    backup.write_text(source, encoding='utf-8')
    path.write_text(source.replace(old, new, 1), encoding='utf-8')
    print(f'PATCH {path} (backup: {backup})')
    print('DONE. Run: npx tsc --noEmit')
elif new in source and 'victim.knock = 0;' not in source:
    print('Already fixed. No changes made.')
else:
    raise SystemExit('ERROR: statement not found; your game.ts differs. No changes made.')
