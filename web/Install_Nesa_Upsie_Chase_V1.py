#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale: Nesa Upsie Daisie chase mobility only.

Run in Fight Royale web folder:
    python Install_Nesa_Upsie_Chase_V1.py
or:
    python Install_Nesa_Upsie_Chase_V1.py C:\\path\\to\\web
Optional --check validates anchors without changing files.
No third-party Python dependencies. Creates backups before writing.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys
import tempfile

MARKER = 'NESA_UPSIE_CHASE_V1_20261107'
PATCHED_FILES = [
    'src/game/kits.ts',
    'src/game/fighter.ts',
    'src/game/game.ts',
    'src/game/ai.ts',
]

class PatchError(Exception):
    pass

def replace_one(s: str, old: str, new: str, name: str) -> str:
    found = s.count(old)
    if found != 1:
        raise PatchError(f'{name}: expected exactly 1 anchor, found {found}. File may differ from supported game update.')
    return s.replace(old, new, 1)

def resolve_root(spec: str | None) -> Path:
    p = Path(spec).expanduser().resolve() if spec else Path.cwd().resolve()
    for candidate in (p, p / 'web'):
        if all((candidate / rel).is_file() for rel in PATCHED_FILES):
            return candidate
    raise PatchError('Cannot find Fight Royale web folder (expected src/game/kits.ts, fighter.ts, game.ts, ai.ts).')

def patch_kits(s: str) -> str:
    old = 'cd: 9, wind: 0.40, active: 0.16, recover: 0.50, dmg: 170, guard: 36, reach: 2.62, lunge: 7.8, knock: 7.3, stun: 0.57'
    new = 'cd: 9, wind: 0.40, active: 0.40, recover: 0.50, dmg: 170, guard: 36, reach: 2.75, lunge: 14.2, knock: 7.3, stun: 0.57'
    s = replace_one(s, old, new, 'Upsie Daisie mobility data')
    return f'// {MARKER}: dash-like kick travel, same impact damage and cooldown.\n' + s

def patch_fighter(s: str) -> str:
    old = '''      this.root.rotation.y += d * (1 - Math.exp(-12 * dt));
    }
    if (this.state === S.ATTACK && (this.atk?.mode === "leap" || this.atk?.mode === "dive") && this.atkPhase === 1) {'''
    new = '''      // Nesa may face a sidestepping target WHILE her flying kick is active.
      const nesaKickTracking = this.kit === "hammer" && this.atk?.name === "Upsie Daisie" &&
        this.state === S.ATTACK && this.atkPhase === 1;
      this.root.rotation.y += d * (1 - Math.exp(-(nesaKickTracking ? 21 : 12) * dt));
    }
    if (this.state === S.ATTACK && (this.atk?.mode === "leap" || this.atk?.mode === "dive") && this.atkPhase === 1) {'''
    s = replace_one(s, old, new, '3D kick turning')
    old = '''      } else if (this.kit === "hammer" && this.atk?.name === "Upsie Daisie") {
        // Plant during wind-up; use the fast active kick for the forward burst.
        v += this.atkPhase === 0 ? 0 : Math.min(10.5, this.atk.lunge * 1.4);
      } else if (this.kit === "hammer" && this.atkId === "heavy" && this.atk.style === "nesa_spin") {'''
    new = '''      } else if (this.kit === "hammer" && this.atk?.name === "Upsie Daisie") {
        // Keep the planted-hammer wind-up rooted; surge forward only during the flying kick.
        // Re-aim toward the opponent each frame, so one sidestep does not defeat the whole move.
        v += this.atkPhase === 0 ? 0 : Math.min(17.2, this.atk.lunge * 1.25) *
          (dist < this.atk.reach * 0.85 ? 0.76 : 1);
      } else if (this.kit === "hammer" && this.atkId === "heavy" && this.atk.style === "nesa_spin") {'''
    s = replace_one(s, old, new, '3D kick chase')
    old = '''    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 :
      this.state === S.CHARGE ? 0.4 : kiraAirSteer ? 0.92 : 0;'''
    new = '''    const nesaKickSteer = this.kit === "hammer" && this.atk?.name === "Upsie Daisie" &&
      this.state === S.ATTACK && this.atkPhase === 1;
    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 :
      this.state === S.CHARGE ? 0.4 : kiraAirSteer ? 0.92 : nesaKickSteer ? 0.35 : 0;'''
    s = replace_one(s, old, new, 'Manual steering for kick')
    old = '''      if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1 && this.atk.lunge > 3) this.vx = this.facing * Math.max(Math.abs(this.vx), this.atk.lunge * 0.6);
    }
    if (this.dashT > 0)'''
    new = '''      if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1 && this.atk.lunge > 3) this.vx = this.facing * Math.max(Math.abs(this.vx), this.atk.lunge * 0.6);
      // Side-view: actually chase along the X axis after taking off, rather than
      // remaining locked to the direction picked at launch. Platform walls still apply.
      if (this.kit === "hammer" && this.state === S.ATTACK &&
          this.atk?.name === "Upsie Daisie" && this.atkPhase === 1) {
        const target = this.opponent && !this.opponent.isDown() ?
          Math.sign(this.opponent.root.position.x - pos.x) : 0;
        const toward = target || this.facing;
        const distance = this.opponent ? Math.abs(this.opponent.root.position.x - pos.x) : 4;
        this.facing = toward;
        this.vx = toward * Math.min(16.5, this.atk.lunge * 1.12) *
          (distance < this.atk.reach * 0.7 ? 0.65 : 1);
      }
    }
    if (this.dashT > 0)'''
    s = replace_one(s, old, new, 'Side-view airborne pursuit')
    return f'// {MARKER}: enhanced Nesa flying kick tracking without changing damage.\n' + s

def patch_game(s: str) -> str:
    old = '''    // Wait for the leg to EXTEND and fighter to traverse her real active distance.
    this.laterCombo(f, 0.12, () => {
      if (round !== this.round || f.isDown() || f.swingSerial !== serial ||
          f.state !== S.ATTACK || f.atk?.name !== "Upsie Daisie") return;'''
    new = '''    // NESA_UPSIE_CHASE: resolve contact AFTER she actually flies forward. Faster
    // opponents can still dodge; no teleport, auto-hit, or second damage tick.
    const target = f.opponent;
    const gap = target && !target.isDown() ?
      target.root.position.clone().sub(f.root.position).setY(0).length() : a.reach;
    const delay = THREE.MathUtils.clamp(0.09 + Math.max(0, gap - a.reach + 0.65) / 15,
      0.09, f.stage ? 0.27 : 0.30);
    this.laterCombo(f, delay, () => {
      if (round !== this.round || f.isDown() || f.swingSerial !== serial ||
          f.state !== S.ATTACK || f.atk?.name !== "Upsie Daisie" || f.atkPhase !== 1) return;'''
    s = replace_one(s, old, new, 'Delay kick hit until chase')
    old = '''    const antiAir = f.atkId === "anti_air";
    const airCombo = f.atkId.startsWith("air_l");
    const directionalAir = !f.stage && f.atkId === "air_l1";'''
    new = '''    const antiAir = f.atkId === "anti_air";
    const airCombo = f.atkId.startsWith("air_l");
    // Flying sidekick travels upward on platform stages; allow its LEG to reach
    // the opponent while Nesa's hips are above their head, without extra X-range.
    const nesaFlyingKick = f.kit === "hammer" && a.name === "Upsie Daisie";
    const directionalAir = !f.stage && f.atkId === "air_l1";'''
    s = replace_one(s, old, new, 'Kick vertical contact declaration')
    old = '''        dy < (directionalAir || d.atkId === "air_l1" ? 2.1 :
          antiAir || airCombo || d.atkId === "anti_air" || d.atkId.startsWith("air_l") ? 1.65 : 0.8)) {'''
    new = '''        dy < (nesaFlyingKick ? 2.1 : directionalAir || d.atkId === "air_l1" ? 2.1 :
          antiAir || airCombo || d.atkId === "anti_air" || d.atkId.startsWith("air_l") ? 1.65 : 0.8)) {'''
    s = replace_one(s, old, new, 'Vertical clash contact')
    old = '''          dy > (antiAir ? 3.25 : airCombo ? 1.8 : 1.3) ||
          (dist > 0.6 && dir.dot(fwd) < (antiAir ? -0.08 : 0.15))) continue;'''
    new = '''          dy > (nesaFlyingKick ? 2.1 : antiAir ? 3.25 : airCombo ? 1.8 : 1.3) ||
          (dist > 0.6 && dir.dot(fwd) < (antiAir ? -0.08 : 0.15))) continue;'''
    s = replace_one(s, old, new, 'Vertical kick hitbox')
    return f'// {MARKER}: timed sidekick contact after real forward movement.\n' + s

def patch_ai(s: str) -> str:
    old = '''        if (name === "Upsie Daisie") {
          if (distance > 5.65) viable = false;
          points += distance > 2.20 && distance < 5.15 ? 2.65 :
            attackComing && close ? 1.8 : 0.25;
        }'''
    new = '''        if (name === "Upsie Daisie") {
          // NESA_UPSIE_CHASE: AI may use the longer REAL lunge against kiters.
          // Still checks line-of-approach and normal cooldowns through Fighter.
          viable = distance < Math.min(6.65, a.reach + a.lunge * 0.31);
          points += distance > 2.20 && distance < 6.45 ? 2.85 :
            attackComing && close ? 1.8 : 0.25;
        }'''
    s = replace_one(s, old, new, 'AI Nesa pursuit skill scoring')
    return f'// {MARKER}: Nesa AI understands extended flying kick approach.\n' + s

PATCHES = {
    'src/game/kits.ts': patch_kits,
    'src/game/fighter.ts': patch_fighter,
    'src/game/game.ts': patch_game,
    'src/game/ai.ts': patch_ai,
}

def install(root: Path, dry: bool = False) -> None:
    updated = {}
    for rel, patch in PATCHES.items():
        path = root / rel
        data = path.read_text(encoding='utf-8')
        if MARKER in data:
            print('[SKIP] Already updated:', rel)
            continue
        updated[rel] = patch(data)
        print('[READY]', rel)
    if not updated:
        print('[OK] Nesa kick mobility is already installed.')
        return
    if dry:
        print('[CHECK] All source anchors validated. No changes made.')
        return
    backup = root / '.nesa_installer_backups' / ('kick_chase_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, exist_ok=False)
    for rel in updated:
        origin = root / rel
        backup_dest = backup / rel
        backup_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, backup_dest)
    written = []
    try:
        for rel, data in updated.items():
            origin = root / rel
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=origin.parent, delete=False) as tmp:
                tmp.write(data)
                new_path = Path(tmp.name)
            os.replace(new_path, origin)
            written.append(rel)
    except Exception:
        for rel in written:
            shutil.copy2(backup / rel, root / rel)
        raise
    print('[OK] Nesa Upsie Daisie chase mobility installed.')
    print('Backup folder:', backup)
    print('Next: npx tsc --noEmit -p . && npm run dev')

def main() -> int:
    parser = argparse.ArgumentParser(description='Increase only Nesa Upsie Daisie chase mobility')
    parser.add_argument('project', nargs='?', help='Fight Royale web project path (defaults to current directory)')
    parser.add_argument('--check', action='store_true', help='Validate patch without writing')
    args = parser.parse_args()
    try:
        root = resolve_root(args.project)
        print('Fight Royale project:', root)
        install(root, args.check)
    except (OSError, UnicodeError, PatchError) as exc:
        print('[ERROR]', exc, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
