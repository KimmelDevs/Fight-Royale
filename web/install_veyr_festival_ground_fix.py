#!/usr/bin/env python3
"""Fix Blood Festival blades spawning in the air when the target is airborne.

Place in web/ beside package.json and run: py install_veyr_festival_ground_fix.py
Changes ONLY src/game/game.ts and makes a timestamped backup.
Compatible with the Blood Festival V3-V6 arena implementation.
"""
from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
GAME = ROOT / 'src/game/game.ts'
if not (ROOT / 'package.json').is_file() or not GAME.is_file():
    sys.exit('ERROR: Place this script in the web/ directory (beside package.json and src/).')

original = GAME.read_text(encoding='utf-8')
start = original.find('private startBloodFestival(')
end = original.find('private updateBloodFestivals(', start)
if start < 0 or end < 0:
    sys.exit('ERROR: Blood Festival V3 or later must be installed first. No files changed.')

block = original[start:end]
marker = '// Anchor Blood Festival to the arena floor, never the target\'s jump height.'
if marker in block:
    print('ALREADY FIXED: Blood Festival is anchored to the ground. No files changed.')
    sys.exit(0)

# V3 to V6 used this exact expression (spacing differences are accepted).
old = re.compile(r'(?m)^(?P<indent>[ \t]*)const center\s*=\s*target\.root\.position\.clone\(\)\.setY\(\s*this\.plat\s*\?\s*0\s*:\s*target\.root\.position\.y\s*\);[ \t]*$')
matches = list(old.finditer(block))
if len(matches) != 1:
    sys.exit(f'ERROR: Expected one Blood Festival center anchor but found {len(matches)}. '
             'Your local game.ts differs; no files were changed.')

indent = matches[0].group('indent')
lines = [
    "// Anchor Blood Festival to the arena floor, never the target's jump height.",
    '// In 3D duel/team/survival, the ground is y=0. In platform brawl,',
    '// pick the highest platform directly below the target, if any.',
    'const festivalGroundY = this.plat',
    '  ? STAGE.plats.reduce((ground, platform) => {',
    '      const abovePlatform = target.root.position.y + 0.05 >= platform.y;',
    '      const overPlatform = target.root.position.x >= platform.x0 && target.root.position.x <= platform.x1;',
    '      return abovePlatform && overPlatform ? Math.max(ground, platform.y) : ground;',
    '    }, 0)',
    '  : 0;',
    'const center = new THREE.Vector3(',
    '  target.root.position.x, festivalGroundY, this.plat ? 0 : target.root.position.z',
    ');',
]
replacement = '\n'.join(indent + line for line in lines)
newblock = block[:matches[0].start()] + replacement + block[matches[0].end():]
updated = original[:start] + newblock + original[end:]
assert updated.count(marker) == 1
# Keep all unrelated rules and client networking unchanged.
assert 'this.emit(["bloodFestival", id, center.toArray(), radius, a.duration, f.id, f.team]);' in newblock

stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup = GAME.with_name(GAME.name + '.festival-ground-backup-' + stamp)
shutil.copy2(GAME, backup)
GAME.write_text(updated, encoding='utf-8')
print('PATCH src/game/game.ts')
print(f'BACKUP {backup.relative_to(ROOT)}')
print('DONE: Blood Festival arena now spawns at ground/platform level even if the target is airborne.')
print('All other mechanics, skill cooldowns, buffs and effects are unchanged.')
