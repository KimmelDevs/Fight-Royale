#!/usr/bin/env python3
"""Zenith V11 — Sovereign Arsenal startup protection.
Run from fight-royale/web after Zenith V10.
Adds a 17-spear defensive eruption on V cast so the ultimate is safer to start.
Edits only src/game/game.ts and src/game/kits.ts.
"""
from pathlib import Path
from datetime import datetime
import os, shutil, sys, tempfile

ROOT = Path.cwd()
G = 'src/game/game.ts'
K = 'src/game/kits.ts'
FILES = (G, K)
MARK = 'ZENITH_ARSENAL_GUARD_V11_20261108'
try:
    before = {f: (ROOT / f).read_text(encoding='utf-8') for f in FILES}
except OSError as e:
    sys.exit(f'ERROR: Run this from your web/ folder. {e}. No changes made.')
if MARK in before[G]:
    print('Zenith V11 already installed. No files changed.')
    sys.exit(0)
if 'ZENITH_SOVEREIGN_HUNTRESS_V10_20261108' not in before[G]:
    sys.exit('PREFLIGHT ERROR: Zenith V10 source is required. No files changed.')

after = before.copy()

def once(path, old, new):
    c = after[path].count(old)
    if c != 1:
        raise ValueError(f'{path}: expected 1 unique anchor, found {c}: {old[:140]!r}')
    after[path] = after[path].replace(old, new, 1)

try:
    once(K,
         'desc: "Summon twelve magnetic spears in two waves, then two heavy rail spears. Fourteen weapons total; split damage, dodgeable strikes.",',
         'desc: "Summon a protective 17-spear magnetic eruption around Zenith, then follow with twelve directional spears and two rail finishers.",')

    once(G,
         '  private zenithArsenal(f:Fighter,a:Attack){',
         '  // ZENITH_ARSENAL_GUARD_V11_20261108 — V gets a protective 17-spear startup eruption\n  private zenithArsenal(f:Fighter,a:Attack){')

    once(G,
         '  private zenithArsenal(f:Fighter,a:Attack){\n    const target = (f.opponent && !f.opponent.isDown()) ? f.opponent : this.enemiesOf(f)[0];\n    if(!target) return;\n    this.snd("dramatic_metal_explosion_impact", 0.36);',
         '  private zenithArsenal(f:Fighter,a:Attack){\n    const target = (f.opponent && !f.opponent.isDown()) ? f.opponent : this.enemiesOf(f)[0];\n    if(!target) return;\n    this.snd("dramatic_metal_explosion_impact", 0.36);\n    // Startup protection: seventeen spears erupt around Zenith in a quick radial burst,\n    // buying space before the directional arsenal begins.\n    const protectCount = 17;\n    const burstBase = { ...a, style:"zenith_construct", pierce:false, heavy:false,\n      dmg:11, guard:(a.guard ?? 18) * 0.34, knock:1.15, stun:0.11, size:0.56 };\n    for(let i=0;i<protectCount;i++) this.later(i*0.018,()=>{\n      if (this.roundOver || f.isDown()) return;\n      const ang = (i/protectCount) * Math.PI * 2;\n      const center = f.chest();\n      const origin = center.clone().add(new THREE.Vector3(Math.sin(ang)*0.48, -0.22 + Math.sin(i*1.1)*0.06, Math.cos(ang)*0.48));\n      const dir = new THREE.Vector3(Math.sin(ang), 0.06, Math.cos(ang)).normalize();\n      const part = { ...burstBase, id:`v_guard_${i}` };\n      const p = this.spawnProjectile(f,f.team,part,f.atkPower*0.88,origin,dir.multiplyScalar(18.5),\n        "zenith_construct","metal",part.size,"#b9d2e8",false,null);\n      p.life = 0.34;\n      this.fxp("flash", origin, "#d7e4f1", 0.032, 0.05, 0.26);\n      if (i % 4 === 0) this.fxp("motes", origin, "#bcd7ef", 4);\n    });')

    once(G,
         '    for(let i=0;i<14;i++) this.later(0.30+i*0.11,()=>{',
         '    for(let i=0;i<14;i++) this.later(0.44+i*0.11,()=>{')

    once(G,
         '      const origin = finisher ? f.chest().add(new THREE.Vector3(i===12?-0.38:0.38,0.18,0))',
         '      const origin = finisher ? f.chest().add(new THREE.Vector3(i===12?-0.38:0.38,0.18,0))')
except ValueError as err:
    sys.exit(f'PREFLIGHT ERROR: {err}. No files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backups = {}
try:
    for path in FILES:
        src = ROOT / path
        bak = src.with_name(src.name + f'.before_zenith_v11_{stamp}.bak')
        shutil.copy2(src, bak)
        backups[path] = bak
    for path in FILES:
        dest = ROOT / path
        fd, tmp = tempfile.mkstemp(prefix=f'.{dest.name}.zenithv11.', suffix='.tmp', dir=dest.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as out:
                out.write(after[path])
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        print('Updated:', path)
except Exception as err:
    for path, bak in backups.items():
        try: shutil.copy2(bak, ROOT / path)
        except OSError: pass
    sys.exit(f'WRITE ERROR: {err}. Attempted automatic rollback.')

print('\nZenith V11 installed: Sovereign Arsenal now begins with a 17-spear defensive eruption.')
print('This startup burst creates space and protects the cast before the 14 follow-up arsenal spears fire.')
print('Run: npx tsc --noEmit -p . && npm run build')
