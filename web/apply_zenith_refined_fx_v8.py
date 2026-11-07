#!/usr/bin/env python3
"""Optional Zenith V8 visual polish. Cosmetic-only; no combat/AI/net changes.

Run from fight-royale/web after Zenith V7. Replaces only uniquely identified
Zenith particle emitter calls in src/game/game.ts. No mechanics are modified.
"""
from pathlib import Path
from datetime import datetime
import os, shutil, sys

ROOT = Path.cwd()
FILE = ROOT / 'src/game/game.ts'
MARK = 'ZENITH_REFINED_FX_V8_20261108'
try:
    original = FILE.read_text('utf-8')
except OSError as exc:
    sys.exit(f'ERROR: Run from your web/ directory: {exc}. No files changed.')
if MARK in original:
    print('Zenith V8 refined effects already installed. No changes made.')
    sys.exit(0)
if ('private zenithChargedOverhead(' not in original or 'private zenithArsenal(' not in original or
    'MAGNETIC GUARD 2s' not in original):
    sys.exit('PREFLIGHT ERROR: Zenith V5/V7 visual emitters not found. No files changed.')
new = original

# Exact, small anchors (each must appear once), chosen from the user's uploaded game.zip.
changes = [
    ('this.fxp("flash", above.clone(), "#e9f9ff", 0.46, 0.18, 0.92);',
     'this.fxp("flash", above.clone(), "#e9f9ff", 0.28, 0.12, 0.65);'),
    ('this.fxp("ring", above.clone(), "#a8ddff", 0.45, 0.16, 0.74);',
     'this.fxp("ring", above.clone(), "#a8ddff", 0.32, 0.13, 0.55);'),
    ('this.fxp("motes", above.clone(), "#d8f2ff", 13);',
     'this.fxp("motes", above.clone(), "#d8f2ff", 5);'),
    ('this.fxp("flash",origin,"#acbfd9",0.25,0.14,0.58);',
     'this.fxp("flash",origin,"#acbfd9",0.15,0.11,0.45);'),
    ('this.fxp("motes",f.chest(),"#bbd8ef",17);',
     'this.fxp("motes",f.chest(),"#bbd8ef",7);'),
    ('this.fxp("ring",p.pos.clone(),"#b1cae6",0.52,0.16,0.5);',
     'this.fxp("ring",p.pos.clone(),"#b1cae6",0.34,0.12,0.36);'),
    ('this.fxp("ring",f.chest(),"#a4bedb",0.85,0.23,0.74);',
     'this.fxp("ring",f.chest(),"#a4bedb",0.56,0.16,0.55);'),
    ('this.fxp("ring",e.chest(),repel?"#c3d0e3":"#869fc8",0.85,0.20,0.58);',
     'this.fxp("ring",e.chest(),repel?"#c3d0e3":"#869fc8",0.56,0.15,0.45);'),
    ('this.fxp("motes",f.chest(),"#a6bddc",11);',
     'this.fxp("motes",f.chest(),"#a6bddc",5);'),
    ('this.fxp("sparks",f.model.bladeTip.getWorldPosition(new THREE.Vector3()),"#a6c8de",10,4);',
     'this.fxp("sparks",f.model.bladeTip.getWorldPosition(new THREE.Vector3()),"#a6c8de",4,2.0);'),
    ('this.fxp("ring",point.clone(),"#a6bcd6",1.85,0.52,0.45);',
     'this.fxp("ring",point.clone(),"#a6bcd6",1.34,0.38,0.31);'),
    ('this.fxp("motes",point.clone().add(new THREE.Vector3(0,1,0)),"#b5cbdd",14);',
     'this.fxp("motes",point.clone().add(new THREE.Vector3(0,1,0)),"#b5cbdd",6);'),
    ('this.fxp("flash",origin,"#d0deef",0.12,0.1,0.7);',
     'this.fxp("flash",origin,"#d0deef",0.075,0.085,0.5);'),
    ('this.fxp("flash",owner.chest(),"#d4f2ff",0.49,0.19,0.85);',
     'this.fxp("flash",owner.chest(),"#d4f2ff",0.32,0.16,0.70);'),
    ('this.fxp("ring",owner.chest(),"#8bd4ff",1.02,0.22,0.75);',
     'this.fxp("ring",owner.chest(),"#8bd4ff",0.70,0.24,0.65);'),
    ('this.fxp("motes",owner.chest(),"#bfdcf5",23);',
     'this.fxp("motes",owner.chest(),"#bfdcf5",8);'),
    ('this.fxp("sparks", p, "#b4c8df", big ? 9 : 5, 2.7);',
     'this.fxp("sparks", p, "#b4c8df", big ? 5 : 3, 1.8);'),
    ('this.fxp("flash", p, "#dbeafa", 0.12, 0.07, 0.42);',
     'this.fxp("flash", p, "#dbeafa", 0.075, 0.06, 0.32);'),
]
try:
    for a,b in changes:
        c = new.count(a)
        if c != 1:
            raise ValueError(f'expected one matching emitter ({c} found): {a}')
        new = new.replace(a,b,1)
except ValueError as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')

new = new.replace('  private zenithChargedOverhead(f: Fighter, a: Attack) {',
                  '  // ' + MARK + ': restrained silver-blue magnetic flashes only.\n'
                  '  private zenithChargedOverhead(f: Fighter, a: Attack) {', 1)
if len(new.splitlines()) < len(original.splitlines()):
    sys.exit('PREFLIGHT ERROR: Unexpected truncated game.ts. No files changed.')
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = FILE.with_name(FILE.name + f'.before_zenith_fx_v8_{stamp}.bak')
tmp = FILE.with_name(FILE.name + '.zenith_fx_v8.tmp')
try:
    shutil.copy2(FILE, backup)
    tmp.write_text(new, 'utf-8')
    os.replace(tmp, FILE)
except OSError as exc:
    try:
        if backup.exists(): shutil.copy2(backup, FILE)
        if tmp.exists(): tmp.unlink()
    except OSError: pass
    sys.exit(f'WRITE ERROR: {exc}; attempted restoration from {backup.name}.')
print('Updated src/game/game.ts — 18 Zenith-only visual emitters refined.')
print(f'Backup: {backup.name}')
print('No changes to damage, cooldowns, collision, throw/return, CC guard, AI, networking or other characters.')
