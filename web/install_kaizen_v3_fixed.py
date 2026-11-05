#!/usr/bin/env python3
"""Kaizen V3 safe installer. Automatically stages Chain Spin V2 when necessary.

Keep this file alongside install_kaizen_chain_spin_v2.py and
install_kaizen_directional_v3.py inside your web project, then run:
    py install_kaizen_v3_fixed.py

Both migrations are tried in a temporary copy before any original file is edited.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory
import os
import shutil
import subprocess
import sys

root = Path.cwd()
script_dir = Path(__file__).resolve().parent
v2_script = script_dir / 'install_kaizen_chain_spin_v2.py'
v3_script = script_dir / 'install_kaizen_directional_v3.py'
source_files = [
    'src/game/model.ts',
    'src/game/fighter.ts',
    'src/game/kits.ts',
    'src/game/vrm.ts',
    'src/game/game.ts',
    'src/game/input.ts',
]

if not (root / 'package.json').is_file():
    sys.exit('ERROR: Run in your web folder (next to package.json). No changes made.')
for script in (v2_script, v3_script):
    if not script.is_file():
        sys.exit(f'ERROR: Missing {script.name} next to this installer. No changes made.')
for rel in source_files:
    if not (root / rel).is_file():
        sys.exit(f'ERROR: Missing {rel}. No changes made.')

original = {rel: (root / rel).read_bytes() for rel in source_files}
model = original['src/game/model.ts'].decode('utf-8')
game = original['src/game/game.ts'].decode('utf-8')
if 'KAIZEN_DIRECTIONAL_V3' in game:
    print('Kaizen V3 is already installed. Nothing to do.')
    sys.exit(0)
if 'KAIZEN_CHAINBLADE_V1' not in model and 'KAIZEN_CHAIN_SPIN_V2' not in model:
    sys.exit('ERROR: Install Kaizen V1 before V3. No changes made.')

with TemporaryDirectory(prefix='kaizen-v3-preflight-') as tmp:
    staged = Path(tmp)
    shutil.copy2(root / 'package.json', staged / 'package.json')
    for rel in source_files:
        dest = staged / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(original[rel])

    steps = []
    if 'KAIZEN_CHAIN_SPIN_V2' not in model:
        steps.append(('Kaizen Chain Spin V2', v2_script))
    steps.append(('Kaizen Directional V3', v3_script))

    for title, script in steps:
        print(f'Checking {title} ...', flush=True)
        result = subprocess.run([sys.executable, str(script)], cwd=staged,
                                text=True, capture_output=True)
        if result.returncode != 0:
            sys.stderr.write(result.stdout + result.stderr)
            sys.exit(f'ERROR: {title} could not apply to your files. Original project unchanged.')
        print(result.stdout.strip(), flush=True)

    updated = {rel: (staged / rel).read_bytes() for rel in source_files}
    changed = [rel for rel in source_files if updated[rel] != original[rel]]
    if not changed:
        print('No differences found. Original files unchanged.')
        sys.exit(0)
    if 'KAIZEN_DIRECTIONAL_V3' not in updated['src/game/game.ts'].decode('utf-8'):
        sys.exit('ERROR: Final install marker missing. Original files unchanged.')

    # All source text edits passed preflight; make personal backups before writing.
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    for rel in changed:
        src = root / rel
        backup = src.with_name(src.name + f'.kaizen-v3safe-backup-{stamp}')
        if backup.exists():
            sys.exit(f'ERROR: Backup exists: {backup}. Original files unchanged.')
        backup.write_bytes(original[rel])

    written = []
    try:
        for rel in changed:
            path = root / rel
            new_path = path.with_name(path.name + '.kaizen-v3safe-tmp')
            new_path.write_bytes(updated[rel])
            os.replace(new_path, path)
            written.append(rel)
            print('PATCH', rel)
    except Exception:
        # Restore any file that was already replaced before the error occurred.
        for rel in written:
            (root / rel).write_bytes(original[rel])
        raise

print('\nDONE: Kaizen Directional V3 installed safely.')
print('Backups: *.kaizen-v3safe-backup-* (do not commit them).')
print('Next: npx tsc --noEmit ; npm run dev')
