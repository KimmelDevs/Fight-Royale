#!/usr/bin/env python3
"""Veyr V7 - Bloodlust decay and real clash-capable Carrion Sweep.

Only modifies kits.ts, fighter.ts, game.ts and GameView.tsx.
Validated against the previous V6 + later patches. Preflight is all-or-nothing.
"""
from __future__ import annotations
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
FILES = {
    'kits': ROOT / 'src/game/kits.ts',
    'fighter': ROOT / 'src/game/fighter.ts',
    'game': ROOT / 'src/game/game.ts',
    'hud': ROOT / 'src/ui/GameView.tsx',
}
TAG = 'VEYR_BLOODLUST_CARRION_V7'


def sub_one(src: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    new, count = re.subn(pattern, lambda _m: replacement, src, count=0, flags=flags)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one matching anchor, found {count}; no changes applied.')
    return new


def make_changes(contents: dict[str, str]) -> dict[str, str]:
    k, f, g, h = (contents[key] for key in ('kits', 'fighter', 'game', 'hud'))

    # One Veyr-only bonus skill definition. Actual melee contacts matter for clashes.
    k = sub_one(
        k,
        r'(?m)^    case "sickle":\s*\n\s*return a\(\{ name: "Carrion Sweep"[^\n]*\n',
        '''    case "sickle":
      // VEYR_BLOODLUST_CARRION_V7: five separate sickle strikes; REAL melee collisions may clash.
      return a({ name: "Carrion Sweep", desc: "Five rapid alternating sickle cuts with a vicious crosscut finisher. Each cut can clash, be blocked, or be parried; no automatic clash is forced.",
        cd: 12, type: "melee", wind: 0.16, active: 0.72, recover: 0.30,
        dmg: 18, guard: 5, reach: 1.94, lunge: 2.2, knock: 0.25, stun: 0.10,
        style: "sickle_carrion", pose_w: "vrv_w", pose_s: "vrv1_s" });
''',
        'kits.ts Carrion Sweep definition',
    )
    k = sub_one(k,
        r'Casting fills Bloodlust and grants Blood Frenzy lifesteal\.',
        'Bloodlust fills only from landed attacks; no free Blood Frenzy on cast.',
        'kits.ts Blood Festival description')
    k = sub_one(k,
        r'(?m)^  vrv_w:',
        '''  // VEYR_BLOODLUST_CARRION_V7: distinct alternating hand and hip rotations for each beat.
  vrv1_s: P([0.30, 0.66, -0.10], [-0.14, -0.48, 0], [-1.62, 0.88, -0.24], [0.19, 0, 0], [-0.92, -0.43, 0.30], [0.32, 0, 0], [-0.68, 0, 0.14], [0.43, 0, -0.12], -0.21),
  vrv2_s: P([0.38, -0.68, 0.12], [-0.19, 0.52, 0], [-0.94, 0.43, -0.28], [0.28, 0, 0], [-1.76, -0.94, 0.22], [0.18, 0, 0], [-0.38, 0, 0.12], [0.69, 0, -0.10], -0.22),
  vrv3_s: P([0.49, 0.52, -0.16], [-0.23, -0.38, 0], [-1.84, 0.27, -0.40], [0.42, 0, 0], [-1.98, -0.23, 0.42], [0.45, 0, 0], [-0.74, 0, 0.16], [0.57, 0, -0.15], -0.25),
  vrv4_s: P([0.31, -0.73, 0.15], [-0.13, 0.57, 0], [-2.05, 0.91, -0.35], [0.24, 0, 0], [-1.54, -0.91, 0.35], [0.24, 0, 0], [-0.47, 0, 0.14], [0.77, 0, -0.16], -0.27),
  vrv5_s: P([0.54, 0.40, 0.12], [-0.27, -0.30, 0], [-1.24, 0.86, -0.13], [0.14, 0, 0], [-1.34, -0.86, 0.13], [0.14, 0, 0], [-0.86, 0, 0.16], [0.65, 0, -0.12], -0.28),
  vrv_w:''',
        'kits.ts sickle poses')

    # Keep filling from normal hits; only change how the frenzy meter empties.
    f = sub_one(f,
        r'\s*const frenzyWasActive = this\.bloodFrenzyT > 0;\s*\n\s*this\.bloodFrenzyT = Math\.max\(this\.bloodFrenzyT - dt, 0\);\s*\n\s*// Show a FULL Bloodlust meter throughout Blood Frenzy, then clear it on expiry\.\s*\n\s*if \(this\.kit === "sickle" && frenzyWasActive && this\.bloodFrenzyT === 0\) this\.bloodlust = 0;',
        '''
    // VEYR_BLOODLUST_CARRION_V7: drain the Frenzy meter evenly rather than snapping from 100 to 0.
    const frenzyWasActive = this.bloodFrenzyT > 0;
    this.bloodFrenzyT = Math.max(this.bloodFrenzyT - dt, 0);
    if (this.kit === "sickle" && frenzyWasActive)
      this.bloodlust = Math.min(100, Math.max(0, 100 * this.bloodFrenzyT / 5));''',
        'fighter.ts Blood Frenzy countdown')

    # Client-side (online) animation can reconstruct the same five beats using attack elapsed time.
    f = sub_one(f,
        r'(?m)^(\s*)// ZAREK_CYCLONE_V3: true successive poses',
        '''        // VEYR_BLOODLUST_CARRION_V7: animate every slash on host and online clients.
        if (this.kit === "sickle" && a?.style === "sickle_carrion") {
          const elapsed = this.stateT - a.wind;
          p = elapsed < 0 ? "vrv_w" : ["vrv1_s", "vrv2_s", "vrv3_s", "vrv4_s", "vrv5_s"][Math.min(4, Math.floor(elapsed / 0.14))];
          sp = elapsed < 0 ? 22 : 48;
          break;
        }
        // ZAREK_CYCLONE_V3: true successive poses''',
        'fighter.ts Carrion Sweep animation')

    # Do not grant 100 Bloodlust or 5 sec Frenzy at Festival cast.
    g = sub_one(g,
        r'(?m)^(\s*f\.bloodFestivalT = a\.duration;\s*\n)\s*// The ultimate instantly fills Bloodlust and triggers/refreshes Blood Frenzy\.\s*\n\s*this\.activateBloodFrenzy\(f\);',
        '''    f.bloodFestivalT = a.duration;
    // VEYR_BLOODLUST_CARRION_V7: Festival doesn't fill Bloodlust or start Frenzy.
    // Landing attacks inside the arena can still build Bloodlust normally.''',
        'game.ts Blood Festival activation')

    # Dispatch real five-hit sickle melee move before default strike/melee handler.
    g = sub_one(g,
        r'(?m)^    if \(f\.kit === "glaive" && \["glaive_cyclone"',
        '''    if (f.kit === "sickle" && a.style === "sickle_carrion") {
      this.carrionSweep(f, a);
      return;
    }
    if (f.kit === "glaive" && ["glaive_cyclone"''',
        'game.ts Carrion Sweep dispatch')

    method = '''  /** VEYR_BLOODLUST_CARRION_V7 — five REAL melee windows, not circular area damage. */
  private carrionSweep(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    const alive = () => this.round === round && f.swingSerial === serial &&
      !f.isDown() && f.state === S.ATTACK;
    const poses = ["vrv1_s", "vrv2_s", "vrv3_s", "vrv4_s", "vrv5_s"];
    const damage = [18, 20, 21, 22, 33];
    const guards = [5, 6, 6, 7, 10];
    const beat = (i: number) => {
      if (!alive()) return;
      f.poseOverride = poses[i];
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", tip, i % 2 ? "#ff799a" : "#ed315c");
      this.fxp("sparks", tip, i % 2 ? "#ffd9e4" : "#ff678c", 12 + i * 3, 5);
      this.fxp("flash", tip, "#fb3767", i === 4 ? 0.40 : 0.23, 0.12, 0.7);
      if (i > 0) this.snd(i === 4 ? "swing_heavy" : "dagger", 0.55);
      // Hit detection is the standard melee path: existing guard, parry, and clash rules apply.
      const part: Attack = { ...a, dmg: damage[i], guard: guards[i],
        knock: i === 4 ? 2.8 : 0.25, stun: i === 4 ? 0.30 : 0.10,
        heavy: false, style: "sickle_carrion" };
      this.melee(f, part);
    };
    beat(0);
    for (let i = 1; i < 5; i++) this.later(0.14 * i, () => beat(i));
  }

'''
    g = sub_one(g,
        r'(?m)^  /\*\* ZAREK_CYCLONE_V3: authoritative phased melee',
        method + '  /** ZAREK_CYCLONE_V3: authoritative phased melee',
        'game.ts Carrion Sweep method insertion')

    # Multi-hit V is NOT allowed to fill 100 Bloodlust on its own: each hit grants only 5.
    g = sub_one(g,
        r'if \(attacker\.kit === "sickle" && !ranged\) this\.gainBloodlust\(attacker, 25\);',
        'if (attacker.kit === "sickle" && !ranged) this.gainBloodlust(attacker, a.style === "sickle_carrion" ? 5 : 25); // VEYR_BLOODLUST_CARRION_V7',
        'game.ts multi-hit V Bloodlust balance')

    # Extra audiovisual response is ONLY for actual clashes, never generated by the skill itself.
    g = sub_one(g,
        r'(?m)^(    a\.clashRecoil\(\);)',
        '''    // VEYR_BLOODLUST_CARRION_V7: reward a genuine Carrion Sweep weapon collision.
    if ([a, b].some(f => f.kit === "sickle" && f.atk?.style === "sickle_carrion")) {
      this.fxp("slashes", pos, "#ff527f");
      this.fxp("sparks", pos, "#ffa4bb", 22, 7);
      this.fxp("flash", pos, "#ff6088", 0.45, 0.16, 0.85);
    }
    a.clashRecoil();''',
        'game.ts Carrion clash effects')

    # Don't force a full bar while Frenzy is active: display actual synced meter value.
    h = sub_one(h,
        r'<Bar v=\{me\.bloodFrenzyT > 0 \? 1 : me\.bloodlust / 100\} color="#d93965" />',
        '{/* VEYR_BLOODLUST_CARRION_V7: display the actual Bloodlust meter as Frenzy counts down. */}\n                  <Bar v={me.bloodlust / 100} color="#d93965" />',
        'GameView.tsx Bloodlust bar')

    return {'kits': k, 'fighter': f, 'game': g, 'hud': h}


def main() -> int:
    missing = [str(p) for p in FILES.values() if not p.is_file()]
    if missing:
        print('ERROR: Please place this script inside web/ alongside package.json. Missing:', *missing, sep='\n - ')
        return 1
    original = {key: path.read_text(encoding='utf-8') for key, path in FILES.items()}
    tagged = [key for key, data in original.items() if TAG in data]
    if len(tagged) == len(FILES):
        print('Already installed: Veyr Bloodlust + Carrion V7. No changes made.')
        return 0
    if tagged:
        print(f'ERROR: A partial V7 installation was detected in {tagged}. No files changed.')
        return 1
    try:
        updated = make_changes(original)  # preflight all expected anchors BEFORE touching any file
    except RuntimeError as exc:
        print('ERROR:', exc)
        print('Please upload your current kits.ts, fighter.ts, game.ts and GameView.tsx for a precise fix.')
        return 1
    # Write to timestamped backups, then atomically move prepared files into place.
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for key, path in FILES.items():
        shutil.copy2(path, path.with_name(path.name + f'.before_veyr_v7_{stamp}.bak'))
    for key, path in FILES.items():
        temp = path.with_name(path.name + '.veyr_v7_tmp')
        temp.write_text(updated[key], encoding='utf-8')
        temp.replace(path)
        print('PATCH', path.relative_to(ROOT))
    print('DONE: Blood Festival no longer fills Bloodlust; Frenzy drains smoothly; Carrion Sweep has five true melee beats.')
    print('Run: npx tsc --noEmit && npm run build && npm run dev')
    return 0


if __name__ == '__main__':
    sys.exit(main())
