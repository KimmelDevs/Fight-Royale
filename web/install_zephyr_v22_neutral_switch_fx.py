#!/usr/bin/env python3
"""Fight Royale — Zephyr V22 neutral-mode-switch FX hotfix.

Run in fight-royale/web after V21:
    python install_zephyr_v22_neutral_switch_fx.py
Or pass the web folder path as the first argument.

V21 removed the F-key's explicit colored burst, but its switch melee attack
still entered the generic hit renderer with Zephyr's turquoise look.glow.
V22 removes the remaining mode-switch color sources while keeping the
normal attack, damage, Rhythm, parry, block, clash and network rules intact.

All replacements are checked in memory before any files are written.
Creates timestamped backups; refuses duplicate installation; no dependencies.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import shutil
import sys

MARK = 'ZEPHYR_SWITCH_NEUTRAL_V22'
FILES = ('src/game/game.ts', 'src/ui/GameView.tsx')


def replace_exact(source: str, old: str, new: str, file: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'{file}: expected one occurrence of {old[:90]!r}, found {count}; no files changed')
    return source.replace(old, new, 1)


def upgrade(files: dict[str, str]) -> None:
    g = 'src/game/game.ts'
    s = files[g]
    if 'ZEPHYR_DRAGON_SWITCH_SPLIT_V20' not in s or 'zephyrSwitchFlourish' not in s:
        raise RuntimeError('Zephyr V20 switch flourish not found. Install V20/V21 first.')
    if '// V21: no color-coded trails, spark bursts or flash when F is pressed.' not in s:
        raise RuntimeError('Zephyr V21 neutral-switch base not detected. Install V21 first.')

    # F no longer spawns any switch-specific colored ring when it actually lands.
    s = replace_exact(s,
        '''      if(a.id.startsWith("dragon_switch_")) {
        this.fxp("ring",d.chest(),"#a9ffe6",.65,.14,.55);
        this.add_trauma(.09);
      }
      this.fxp("num",attacker.chest().add(new THREE.Vector3(0,.83,0)),
        `HIDDEN RHYTHM ${attacker.dragonRhythm}/3`,"#b7ffe3",.72);''',
        '''      if(a.id.startsWith("dragon_switch_")) {
        // ZEPHYR_SWITCH_NEUTRAL_V22: keep the confirmed-hit camera feedback,
        // but do not emit the leftover green ring.
        this.add_trauma(.09);
      }
      this.fxp("num",attacker.chest().add(new THREE.Vector3(0,.83,0)),
        `HIDDEN RHYTHM ${attacker.dragonRhythm}/3`,
        a.style === "zephyr_switch" ? "#ffffff" : "#b7ffe3",.72);''',g)

    # The shared hit renderer previously used Zephyr's teal glow even for
    # switch hits. Neutralize it only for the F flourish, not his regular moves.
    s = replace_exact(s,
        '''    const glow = attacker instanceof Fighter ? attacker.look.glow : attacker instanceof Mob ? attacker.def.color : "#ffffff";''',
        '''    // ZEPHYR_SWITCH_NEUTRAL_V22: F-switch hits must not inherit Zephyr's teal glow.
    const neutralDragonSwitch = attacker instanceof Fighter &&
      attacker.kit === "tristaff" && a.style === "zephyr_switch";
    const glow = neutralDragonSwitch ? "#dedede" :
      attacker instanceof Fighter ? attacker.look.glow :
      attacker instanceof Mob ? attacker.def.color : "#ffffff";''',g)

    s = replace_exact(s,
        '''        if (attacker instanceof Fighter) this.highlightHit(attacker, a, d.lastDamage, result === "ko");''',
        '''        // Ordinary colorful hit-highlight was still firing on every F-switch contact.
        if (attacker instanceof Fighter && !neutralDragonSwitch)
          this.highlightHit(attacker, a, d.lastDamage, result === "ko");''',g)
    s = replace_exact(s,
        '''          this.fxp("sparks", hitPos, "#fff4d4", heavy ? 18 : 10, 6);''',
        '''          this.fxp("sparks", hitPos, neutralDragonSwitch ? "#dfdfdf" : "#fff4d4",
            neutralDragonSwitch ? 6 : heavy ? 18 : 10, 6);''',g)
    s = replace_exact(s,
        '''        this.fxp("flash", hitPos, glow, heavy ? 0.45 : 0.3, 0.14, 0.8);''',
        '''        this.fxp("flash", hitPos, glow, neutralDragonSwitch ? 0.12 : heavy ? 0.45 : 0.3,
          neutralDragonSwitch ? 0.08 : 0.14, neutralDragonSwitch ? 0.38 : 0.8);''',g)

    # Defense cues stay visible but lose their gold/cyan hue ONLY on the F hit.
    substitutions = (
      ('this.fxp("impactBurst", shieldPos, "#ffe19c", 0.76, "block");',
       'this.fxp("impactBurst", shieldPos, neutralDragonSwitch ? "#dedede" : "#ffe19c", 0.76, "block");'),
      ('this.fxp("clashBurst", shieldPos, "#ffd27a", 0.72);',
       'this.fxp("clashBurst", shieldPos, neutralDragonSwitch ? "#dedede" : "#ffd27a", 0.72);'),
      ('this.fxp("sparks", shieldPos, "#ffd27a", 16, 5, dir.clone().negate().add(new THREE.Vector3(0, 0.3, 0)));',
       'this.fxp("sparks", shieldPos, neutralDragonSwitch ? "#dedede" : "#ffd27a", 16, 5, dir.clone().negate().add(new THREE.Vector3(0, 0.3, 0)));'),
      ('this.fxp("flash", shieldPos, "#ffd980", 0.35, 0.1, 0.6);',
       'this.fxp("flash", shieldPos, neutralDragonSwitch ? "#ffffff" : "#ffd980", neutralDragonSwitch ? 0.11 : 0.35, 0.1, 0.6);'),
      ('this.fxp("impactBurst", shieldPos, "#b9f5ff", 1.65, "clash");',
       'this.fxp("impactBurst", shieldPos, neutralDragonSwitch ? "#dedede" : "#b9f5ff", 1.65, "clash");'),
      ('this.fxp("impactFrame", "parry", "#b9f5ff", 0.72);',
       'this.fxp("impactFrame", "parry", neutralDragonSwitch ? "#dedede" : "#b9f5ff", 0.72);'),
      ('this.fxp("clashBurst", shieldPos, "#aee9ff", 1.15);',
       'this.fxp("clashBurst", shieldPos, neutralDragonSwitch ? "#dedede" : "#aee9ff", 1.15);'),
      ('this.fxp("sparks", shieldPos, "#aee9ff", 40, 9);',
       'this.fxp("sparks", shieldPos, neutralDragonSwitch ? "#dedede" : "#aee9ff", 40, 9);'),
      ('this.fxp("flash", shieldPos, "#b3f2ff", 0.5, 0.2, 0.9);',
       'this.fxp("flash", shieldPos, neutralDragonSwitch ? "#ffffff" : "#b3f2ff", neutralDragonSwitch ? 0.12 : 0.5, 0.2, 0.9);'),
      ('this.fxp("ring", shieldPos, "#b3f2ff", 0.8, 0.35, 0.9);',
       'this.fxp("ring", shieldPos, neutralDragonSwitch ? "#dedede" : "#b3f2ff", 0.8, 0.35, 0.9);'),
      ('this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "PARRY!", "#8fe6ff", 1.4);',
       'this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "PARRY!", neutralDragonSwitch ? "#ffffff" : "#8fe6ff", 1.4);'),
      ('this.fxp("impactBurst", hitPos, "#ff9f43", 1.65, "clash");',
       'this.fxp("impactBurst", hitPos, neutralDragonSwitch ? "#dedede" : "#ff9f43", 1.65, "clash");'),
      ('this.fxp("impactFrame", "guardbreak", "#ff9f43", 0.85);',
       'this.fxp("impactFrame", "guardbreak", neutralDragonSwitch ? "#dedede" : "#ff9f43", 0.85);'),
      ('this.fxp("sparks", hitPos, "#ffb347", 40, 9);',
       'this.fxp("sparks", hitPos, neutralDragonSwitch ? "#dedede" : "#ffb347", 40, 9);'),
      ('this.fxp("flash", hitPos, "#ffb34d", 0.5, 0.2, 0.9);',
       'this.fxp("flash", hitPos, neutralDragonSwitch ? "#ffffff" : "#ffb34d", neutralDragonSwitch ? 0.12 : 0.5, 0.2, 0.9);'),
    )
    for old,new in substitutions:
      s=replace_exact(s,old,new,g)
    files[g]=s

    # No teal mode outline, either. Rhythm and mode text remain readable.
    ui='src/ui/GameView.tsx'
    s=files[ui]
    if 'DRAGON RHYTHM' not in s:
        raise RuntimeError('GameView.tsx: Zephyr Rhythm HUD missing')
    s=replace_exact(s,
        'border: "1px solid #69dfc5", borderRadius: 7, color: "#fff", fontSize: 12,',
        'border: "1px solid rgba(255,255,255,.42)", borderRadius: 7, color: "#fff", fontSize: 12, /* ZEPHYR_SWITCH_NEUTRAL_V22 */',ui)
    files[ui]=s


def main() -> int:
    base=Path(sys.argv[1] if len(sys.argv)>1 else '.').expanduser().resolve()
    print('ZEPHYR V22 — NEUTRAL SWITCH VISUALS |',base)
    originals: dict[str,str]={}
    try:
        for rel in FILES:
            p=base/rel
            if not p.is_file():
                raise RuntimeError(f'Missing {rel}; run from the Fight Royale web folder')
            src=p.read_text(encoding='utf-8-sig')
            if MARK in src:
                raise RuntimeError(f'V22 already installed in {rel}; no files changed')
            originals[rel]=src
        updated=originals.copy()
        upgrade(updated)
        stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup=base/'.zephyr-backups'/('v22-'+stamp)
        for rel in FILES:
            dest=backup/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(base/rel,dest)
        try:
            for rel in FILES:
                (base/rel).write_text(updated[rel],encoding='utf-8')
                print('  updated',rel)
        except Exception:
            for rel in FILES:
                if (backup/rel).is_file(): shutil.copy2(backup/rel,base/rel)
            raise
        print('\nDone. Backups:',backup)
        print('Removed remaining Zephyr F-switch color effects. Normal attacks keep their FX.')
        print('Run: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
