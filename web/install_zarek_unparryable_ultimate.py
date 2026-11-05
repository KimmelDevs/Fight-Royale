#!/usr/bin/env python3
"""Zarek Infinite Crescent: disable perfect parries for every ultimate hit.
Run from your Fight-Royale/web folder. Requires Zarek Cyclone V3.
"""
from pathlib import Path
from datetime import datetime
import re
import sys

root = Path.cwd()
file = root / 'src/game/kits.ts'
if not (root / 'package.json').is_file() or not file.is_file():
    sys.exit('Run this installer inside your web folder, beside package.json.')

source = file.read_text(encoding='utf-8')
start = source.find('function glaive(): Record<string, Attack> {')
if start == -1:
    sys.exit('Zarek glaive kit was not found. No files changed.')
end = source.find('\nfunction ', start + 1)
if end == -1:
    sys.exit('Could not locate the end of the glaive kit. No files changed.')
kit = source[start:end]

# Work ONLY on Zarek's C/Infinite Crescent, never on other fighter attacks.
match = re.search(r'(?m)^\s*c:\s*a\(\{\s*name:\s*["\']Infinite Crescent["\'].*?\}\),', kit, re.S)
if not match:
    sys.exit('Zarek Infinite Crescent (V3) was not found. Install Zarek V3 first. No files changed.')
block = match.group(0)
if 'no_parry: true' in block:
    print('Already installed: Infinite Crescent cannot be parried. No changes made.')
    sys.exit(0)
if re.search(r'\bno_parry\s*:', block):
    sys.exit('Infinite Crescent has a custom no_parry value; not changing it automatically.')
anchor = 'style: "glaive_infinite"'
if block.count(anchor) != 1:
    sys.exit('Cannot safely locate Infinite Crescent attack style. No files changed.')
new_block = block.replace(anchor, 'no_parry: true, ' + anchor, 1)

# Update the in-game description as well.
desc = re.search(r'desc:\s*"([^"]*)"', new_block)
if desc and 'cannot be parried' not in desc.group(1).lower():
    new_block = new_block[:desc.start(1)] + desc.group(1) + ' Cannot be parried; blocking and clashes still work.' + new_block[desc.end(1):]

new_kit = kit[:match.start()] + new_block + kit[match.end():]
updated = source[:start] + new_kit + source[end:]
assert updated != source and updated.count('style: "glaive_infinite"') >= 1
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = file.with_name(file.name + f'.zarek-ultimate-backup-{stamp}')
backup.write_text(source, encoding='utf-8')
file.write_text(updated, encoding='utf-8')
print('PATCH src/game/kits.ts — Infinite Crescent is now unparryable.')
print('All staged hits inherit no_parry from C. Normal blocks and clashes still work.')
print('AI also recognizes no_parry and will prefer blocking or clashing.')
print(f'Backup: {backup}')
