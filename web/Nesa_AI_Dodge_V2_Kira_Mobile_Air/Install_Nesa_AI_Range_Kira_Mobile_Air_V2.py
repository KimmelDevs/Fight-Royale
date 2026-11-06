#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale focused AI + Kira aerial movement hotfix (after dodge/three-kick updater).

Fixes enemy AI getting stuck retreating into the circular arena wall, matches
Nesa's effective hammer reach, and independently reacts to Heartbreaker's
delayed giant hammer. Kira can steer during her three aerial attacks.
No damage, cooldown, armor, or charge-duration changes.

Run in Fight Royale/web:
  python Install_Nesa_AI_Range_Kira_Mobile_Air_V2.py
or pass the web directory as the first argument. Use --check for a dry run.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys
import tempfile

MARK = 'NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2'
FILES = ('src/game/ai.ts', 'src/game/fighter.ts')

class PatchError(RuntimeError):
    pass

def one(src: str, old: str, new: str, label: str) -> str:
    n = src.count(old)
    if n != 1:
        raise PatchError(f'{label}: expected exactly one code anchor, got {n}')
    return src.replace(old, new, 1)

def root_at(value: str | None) -> Path:
    p = Path(value).expanduser().resolve() if value else Path.cwd()
    for q in (p, p / 'web'):
        if all((q / f).is_file() for f in FILES):
            return q
    raise PatchError('Fight Royale web folder not found. Run from web or pass the path.')

AI_FIELDS = '''  // NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: independently plan the later giant smash.
  private nesaGiantEvadeUsed = false;
  private nesaGiantEvadeChosen = false;
'''

AI_METHOD = '''  /** NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: choose an escape that remains inside
   * the real arena. A blocked radial retreat loses to a viable tangential route.
   * Test projected destination, not just angle to the hammer wielder.
   */
  private nesaSafeEscape(f: Fighter, o: Fighter, radial: boolean, allowDash: boolean): { dir: THREE.Vector3; gain: number } {
    const at = f.root.position.clone().setY(0);
    const from = o.root.position.clone().setY(0);
    const away = at.clone().sub(from);
    const originalDist = away.length();
    if (originalDist > 0.001) away.divideScalar(originalDist);
    else away.set(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const side = new THREE.Vector3(-away.z, 0, away.x);
    const towardCenter = at.clone().negate().setY(0);
    if (towardCenter.lengthSq() > 0.001) towardCenter.normalize();
    const dirs = [
      away, side.clone(), side.clone().negate(),
      away.clone().addScaledVector(side, 0.95),
      away.clone().addScaledVector(side, -0.95),
      side.clone().addScaledVector(towardCenter, 0.85),
      side.clone().negate().addScaledVector(towardCenter, 0.85),
      towardCenter,
    ];
    const cap = Math.max(1.5, f.arenaRadius - f.radius - 0.20);
    const dashAvailable = allowDash && f.dashCd <= 0 && f.onGround;
    const lookAhead = dashAvailable ? 3.65 : Math.max(1.10, f.moveSpeed * 0.48);
    const facing = new THREE.Vector3(Math.sin(o.root.rotation.y), 0, Math.cos(o.root.rotation.y));
    const fire = this.threats.firePatches(f);
    let bestScore = -1e10;
    let best = away.clone();
    let gain = -1;
    for (const candidate of dirs) {
      if (candidate.lengthSq() < 0.0001) continue;
      const dir = candidate.normalize();
      const projected = at.clone().addScaledVector(dir, lookAhead);
      const radialDistance = projected.length();
      if (radialDistance > cap) projected.multiplyScalar(cap / radialDistance);
      const actualMove = projected.distanceTo(at);
      const resultingDistance = projected.distanceTo(from);
      const actualGain = resultingDistance - originalDist;
      const delta = projected.clone().sub(from);
      const lateral = Math.abs(delta.x * facing.z - delta.z * facing.x);
      // Radial AoE needs maximum distance; ordinary strikes can also escape their arc.
      let score = resultingDistance + (radial ? 0 : lateral * 0.20) + actualMove * 0.18;
      if (actualGain < 0) score += actualGain * 2.8;
      // Wall clipping makes a direction ineffective even if it points away.
      if (actualMove < lookAhead * 0.30) score -= 2.5;
      if (projected.length() > cap - 0.08) score -= 0.14;
      // Avoid accidentally escaping a hammer into Ember's persistent floor flames.
      for (const patch of fire) {
        if (Math.abs(patch.pos.y - f.root.position.y) > 1.55) continue;
        const dist = Math.hypot(projected.x - patch.pos.x, projected.z - patch.pos.z);
        if (dist < patch.radius + f.radius * 0.3 + 0.12)
          score -= 4 + (patch.radius - dist) * 2;
      }
      if (score > bestScore) { bestScore = score; best.copy(dir); gain = actualGain; }
    }
    return { dir: best, gain };
  }

  /** NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: use visible wind-ups and real hit radii.
   * Heartbreaker's first bonk and giant follow-up are different threats, so a
   * dodge of the little hammer does NOT consume the dodge for the giant hammer.
   */
  private evadeNesa(f: Fighter, o: Fighter, dt: number): boolean {
    const a = o.atk;
    const active = o.kit === "hammer" && o.state === S.ATTACK && !!a && !f.isDown();
    if (!active) { this.nesaRetreatT = 0; return false; }
    // Do not override moves that the fighter cannot cancel into a real dash.
    const available = f.state === S.IDLE || f.state === S.BLOCK || f.state === S.CHARGE;
    if (!available) { this.nesaRetreatT = 0; return false; }
    const giant = a!.style === "nesa_high_striker";
    const spin = a!.style === "nesa_spin" || a!.style === "nesa_air_spin";
    const heart = a!.style === "nesa_heart_slam";
    const area = giant || spin || heart || a!.type === "strike";
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    // Actual source hitboxes: first high-striker bonk reaches 2.65, giant 3.6.
    // Normal hammer attacks may advance during the telegraphed wind-up.
    const firstRadius = giant ? 2.65 + f.radius * 0.45 + 0.22 :
      spin ? 2.80 + f.radius * 0.5 + 0.70 :
      area ? Math.max(2.4, a!.radius) + f.radius * 0.45 + 0.45 :
      a!.reach + f.radius * 0.5 + Math.min(1.25, a!.lunge * 0.33) + 0.32;
    const bigRadius = 3.60 + f.radius * 0.4 + 0.55;

    if (this.nesaThreatSerial !== o.swingSerial) {
      this.nesaThreatSerial = o.swingSerial;
      this.nesaEvadeUsed = false;
      this.nesaGiantEvadeUsed = false;
      // Keep difficulty scaling: easy is less consistent, master more alert.
      this.nesaEvadeChosen = Math.random() < Math.min(0.94, 0.13 + this.p.block * 1.18);
      this.nesaGiantEvadeChosen = Math.random() < Math.min(0.97, 0.38 + this.p.block * 0.88);
      const lead = 0.105 + this.p.react[1] * 0.28 + Math.random() * 0.025;
      this.nesaEvadeTrigger = Math.max(0.04, a!.wind - lead);
      this.nesaRetreatT = 0;
    }
    const t = o.stateT;
    const giantImpact = a!.wind + 1.90; // actual scheduled giant-smash callback
    const giantDue = giant && !this.nesaGiantEvadeUsed && this.nesaGiantEvadeChosen &&
      gap < bigRadius + 0.65 &&
      t >= giantImpact - (0.44 + this.p.react[1] * 0.15) &&
      t < giantImpact + 0.08;
    const firstDue = !this.nesaEvadeUsed && this.nesaEvadeChosen &&
      gap < firstRadius + 0.65 && t >= this.nesaEvadeTrigger &&
      t < a!.wind + (spin ? Math.max(0.26, a!.active - 0.08) : 0.18);

    if (giantDue || firstDue) {
      if (giantDue) this.nesaGiantEvadeUsed = true;
      else this.nesaEvadeUsed = true;
      const radial = giantDue || area;
      // Heartbreaker has a giant second hit: conserve the 6-second dash for it.
      const useDash = f.dashCd <= 0 && f.onGround && (!giant || giantDue);
      const plan = this.nesaSafeEscape(f, o, radial, useDash);
      this.nesaRetreatDir.copy(plan.dir);
      // Leave the danger in one burst; do not blindly walk backwards at the wall.
      this.nesaRetreatT = giantDue ? 0.48 : radial ? 0.42 : 0.33;
      // Remove an earlier planned shield/parry, not the target's real combat rules.
      this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
      this.queue = []; this.hold = 0;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.block = false;
      f.intent.move.copy(plan.dir);
      // A genuine dash is only available when its real cooldown allows it.
      if (useDash) f.intent.dash.copy(plan.dir);
      else if (plan.gain < 0.30 && (giantDue || area) && f.onGround) {
        // If trapped against the boundary, guarding is better than stuck retreat.
        f.intent.block = true;
      }
      return true;
    }

    if (this.nesaRetreatT > 0 &&
        ((giant && t < giantImpact + 0.15 && gap < bigRadius + 1.0) ||
         (t < a!.wind + (spin ? a!.active : 0.30) && gap < firstRadius + 0.85))) {
      this.nesaRetreatT = Math.max(0, this.nesaRetreatT - dt);
      // Replan every frame, so changing position / boundary never pins the CPU.
      const radial = area;
      const allowDash = !giant || t >= giantImpact - 0.55;
      const plan = this.nesaSafeEscape(f, o, radial, allowDash);
      this.nesaRetreatDir.copy(plan.dir);
      f.intent.move.copy(plan.dir);
      f.intent.block = false;
      f.intent.attack = false;
      f.intent.skill = "";
      return true;
    }
    this.nesaRetreatT = 0;
    return false;
  }

'''

AI_OLD_START = '  /** NESA_DODGE_KIRA_AIR_3_V1: react to a *real* enemy hammer telegraph'
AI_OLD_END = '  private jumpPulse = false;'
AI_KIRA_CHASE_OLD = '''    if (!f.stage) { this.dodge(f); this.position(f, o, dt); }
    // Run after normal chase/strafe choices, so fire can veto a dangerous route.'''
AI_KIRA_CHASE_NEW = '''    if (!f.stage) { this.dodge(f); this.position(f, o, dt); }
    // NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: Kira can reposition between air kicks.
    // Use the same directional input and capped movement available to the player.
    if (!f.stage && f.kit === "kicks" && !f.onGround && f.state === S.ATTACK &&
        /^air_l[1-3]$/.test(f.atkId)) {
      const toward = o.root.position.clone().sub(f.root.position).setY(0);
      const distance = toward.length();
      if (distance > 1.1) f.intent.move.copy(toward.divideScalar(distance));
      else if (distance > 0.01) {
        const around = new THREE.Vector3(-toward.z, 0, toward.x).normalize();
        f.intent.move.copy(around).multiplyScalar(0.55);
      }
    }
    // Run after normal chase/strafe choices, so fire can veto a dangerous route.'''

FIGHTER_STEER_OLD = '    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 : this.state === S.CHARGE ? 0.4 : 0;'
FIGHTER_STEER_NEW = '''    // NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: steer Kira during all three airborne kicks.
    // No extra i-frames, dash, or sprint: movement uses her ordinary moveSpeed.
    const kiraAirSteer = this.kit === "kicks" && !this.onGround && this.state === S.ATTACK &&
      /^air_l[1-3]$/.test(this.atkId);
    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 :
      this.state === S.CHARGE ? 0.4 : kiraAirSteer ? 0.92 : 0;'''


def patch_ai(src: str) -> str:
    if MARK in src:
        return src
    s = src.find(AI_OLD_START)
    e = src.find(AI_OLD_END, s + 10) if s >= 0 else -1
    if s < 0 or e < 0:
        raise PatchError('Expected the previously installed Nesa CPU/Kira air-kick update in ai.ts.')
    src = src[:s] + AI_METHOD + src[e:]
    src = one(src, '  private nesaRetreatDir = new THREE.Vector3();',
              '  private nesaRetreatDir = new THREE.Vector3();\n' + AI_FIELDS,
              'extra giant-smash dodge decision')
    src = one(src, AI_KIRA_CHASE_OLD, AI_KIRA_CHASE_NEW,
              'Kira moving AI aerial kicks')
    return src

def patch_fighter(src: str) -> str:
    if MARK in src:
        return src
    if 'private kiraAirKicks = 0;' not in src:
        raise PatchError('Expected Kira three-air-kick update in fighter.ts.')
    return one(src, FIGHTER_STEER_OLD, FIGHTER_STEER_NEW,
               'Kira air movement while attacking')

def main():
    parser = argparse.ArgumentParser(description='Nesa CPU boundary/range/giant-smash dodge and mobile Kira air kicks')
    parser.add_argument('project', nargs='?', help='Fight Royale web directory or repository root')
    parser.add_argument('--check', action='store_true', help='Check without modifying files')
    args = parser.parse_args()
    root = root_at(args.project)
    patches: dict[str, bytes] = {}
    for rel in FILES:
        before = (root / rel).read_text(encoding='utf-8')
        after = patch_ai(before) if rel.endswith('/ai.ts') else patch_fighter(before)
        if before != after:
            patches[rel] = after.encode('utf-8')
    print('Fight Royale web project:', root)
    if not patches:
        print('[OK] Nesa CPU / Kira air steering V2 already installed; no duplicate changes.')
        return
    for rel in patches: print('[UPDATE]', rel)
    if args.check:
        print('[CHECK] All patch anchors verified; no files changed.')
        return
    backup_dir = root / '.combat_ai_installer_backups' / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_nesa_ai_v2')
    backup_dir.mkdir(parents=True, exist_ok=False)
    for rel in patches:
        backup = backup_dir / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, backup)
    changed = []
    try:
        for rel, data in patches.items():
            dest = root / rel
            with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
                tmp.write(data)
                staged = Path(tmp.name)
            os.replace(staged, dest)
            changed.append(rel)
    except Exception:
        for rel in changed: shutil.copy2(backup_dir / rel, root / rel)
        raise
    print('[OK] AI chooses arena-safe evasions, anticipates hammer range and giant smash, Kira can steer mid-air.')
    print('[BACKUP]', backup_dir)
    print('Verify: npx tsc --noEmit -p . ; npm run dev')

if __name__ == '__main__':
    try: main()
    except (OSError, PatchError) as exc:
        print('INSTALL FAILED:', exc)
        sys.exit(1)
