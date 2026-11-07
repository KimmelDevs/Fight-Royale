#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale — Aster Knight Combat Animation V2.

Purely visual Aster-only update. Preserves stats, AI, combat timing and other kits.
Run in the Fight Royale web folder: python Install_Aster_Combat_Animation_V2.py
Or pass the path to web. Python 3.9+, no external packages.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

TAG = 'ASTER_KNIGHT_COMBAT_ANIM_V2'
FILES = ['src/game/kits.ts', 'src/game/fighter.ts', 'src/game/model.ts', 'src/game/vrm.ts']

class PatchError(RuntimeError):
    pass

def replace_one(src: str, before: str, after: str, label: str) -> str:
    count = src.count(before)
    if count != 1:
        raise PatchError(f'{label}: expected one matching anchor, found {count}. No files changed.')
    return src.replace(before, after, 1)

def project_root(raw: str | None) -> Path:
    p = Path(raw or os.getcwd()).expanduser().resolve()
    for x in (p, p / 'web'):
        if all((x / f).exists() for f in FILES):
            return x
    raise PatchError('Cannot find Fight Royale web folder. Put this installer inside web, or pass its path.')

ASTER_POSES = r'''// ASTER_KNIGHT_COMBAT_ANIM_V2: Aster-only sword/shield choreography.
// Each entry is a body pose at a timed combat phase; hitboxes and frame timing stay the same.
// Distinct chamber / release / reset; shield positioning is handled by Aster's VRM arm IK.
const ASTER_COMBAT_V2: Record<string, Pose> = {
  idle: P([0.065, -0.25, 0], [-0.025, 0.19, 0], [-0.84, -0.18, -0.16], [-0.28, 0, -0.03], [-1.12, -0.24, 0.21], [0.05, 0, -0.16], [-0.18, 0, 0.10], [0.15, 0, -0.11], -0.03),
  block: P([0.105, -0.07, -0.02], [-0.09, 0.06, 0], [-0.96, 0.20, -0.20], [-0.25, 0, 0], [-1.40, -0.42, 0.11], [0, 0, -0.1], [-0.26, 0, 0.12], [0.22, 0, -0.12], -0.062),
  aster_reset: P([0.095, -0.14, 0], [-0.025, 0.11, 0], [-1.00, -0.11, -0.12], [-0.17, 0, 0], [-1.18, -0.23, 0.18], [0, 0, -0.14], [-0.20, 0, 0.11], [0.17, 0, -0.1], -0.045),
  // Slash 1: sword comes to the right shoulder, then cuts horizontally across the body.
  l1_w: P([0.12, -0.58, -0.04], [0, 0.38, 0], [-1.18, -0.82, -0.20], [0.34, 0, 0], [-1.22, -0.20, 0.20], [0, 0, -0.12], [-0.31, 0, 0.11], [0.27, 0, -0.10], -0.063),
  l1_s: P([0.21, 0.60, 0.06], [-0.07, -0.29, 0], [-1.60, 0.75, -0.02], [-0.04, 0, 0], [-1.32, -0.15, 0.19], [0, 0, -0.08], [-0.48, 0, 0.12], [0.37, 0, -0.10], -0.092),
  // Slash 2: controlled reverse cut, shield still covering the center.
  l2_w: P([0.12, 0.55, 0.05], [0, -0.27, 0], [-1.52, 0.86, 0.05], [0.19, 0, 0], [-1.23, -0.16, 0.20], [0, 0, -0.1], [-0.30, 0, 0.12], [0.28, 0, -0.11], -0.066),
  l2_s: P([0.23, -0.62, -0.055], [-0.055, 0.36, 0], [-1.51, -0.81, -0.01], [0.04, 0, 0], [-1.35, -0.2, 0.17], [0, 0, -0.09], [-0.47, 0, 0.12], [0.34, 0, -0.1], -0.095),
  // Slash 3: overhead finisher, longer visual anticipation then heavy diagonal follow-through.
  l3_w: P([-0.075, -0.28, 0.015], [0.07, 0.18, 0], [-2.58, -0.48, -0.14], [0.43, 0, 0], [-1.36, -0.19, 0.22], [0, 0, -0.11], [-0.31, 0, 0.12], [0.30, 0, -0.11], -0.053),
  l3_s: P([0.37, 0.48, -0.05], [-0.13, -0.31, 0], [-0.91, 0.78, -0.045], [0.11, 0, 0], [-1.39, -0.22, 0.19], [0, 0, -0.08], [-0.57, 0, 0.12], [0.44, 0, -0.11], -0.13),
  // Charged slash: blade drawn behind right hip, weight transfers through front boot.
  aster_heavy_w: P([0.12, -0.83, -0.04], [0, 0.40, 0], [-0.74, -1.33, -0.16], [0.65, 0, 0], [-1.43, -0.23, 0.22], [0, 0, -0.11], [-0.39, 0, 0.12], [0.36, 0, -0.1], -0.107),
  aster_heavy_s: P([0.38, 0.92, 0.07], [-0.15, -0.47, 0], [-1.25, 1.18, -0.08], [0.10, 0, 0], [-1.43, -0.12, 0.22], [0, 0, -0.08], [-0.66, 0, 0.12], [0.53, 0, -0.10], -0.16),
  // Shield Bash: retract shield into the chest, then drive it forward with a planted step.
  aster_bash_w: P([0.07, -0.23, -0.01], [-0.035, 0.11, 0], [-0.79, 0.31, -0.25], [-0.18, 0, 0], [-1.48, -0.24, 0.12], [0, 0, -0.12], [-0.41, 0, 0.12], [0.33, 0, -0.11], -0.105),
  aster_bash_s: P([0.36, 0.18, -0.035], [-0.105, -0.14, 0], [-0.75, 0.15, -0.28], [-0.15, 0, 0], [-1.66, -0.06, 0.12], [0, 0, -0.1], [-0.66, 0, 0.12], [0.48, 0, -0.11], -0.13),
  // Rising Slash: load the sword low and drive an uppercut through the jump.
  aster_rise_w: P([0.21, -0.29, 0], [-0.03, 0.25, 0], [-0.39, -0.58, -0.21], [0.44, 0, 0], [-1.3, -0.2, 0.18], [0, 0, -0.1], [-0.45, 0, 0.11], [0.39, 0, -0.09], -0.095),
  aster_rise_s: P([-0.22, 0.37, 0], [-0.14, -0.25, 0], [-2.73, 0.43, -0.13], [0.34, 0, 0], [-1.18, -0.17, 0.22], [0, 0, -0.1], [-0.59, 0, 0.09], [0.23, 0, -0.09], -0.025),
  // Blade Wave: shoulder-level coil, sharp release into a broad projecting cut.
  aster_wave_w: P([-0.025, -0.49, 0.02], [0.025, 0.32, 0], [-2.06, -0.65, -0.20], [0.30, 0, 0], [-1.27, -0.14, 0.19], [0, 0, -0.1], [-0.34, 0, 0.11], [0.30, 0, -0.1], -0.057),
  aster_wave_s: P([0.24, 0.61, -0.03], [-0.06, -0.38, 0], [-1.03, 0.98, -0.04], [0.12, 0, 0], [-1.35, -0.13, 0.22], [0, 0, -0.1], [-0.48, 0, 0.12], [0.38, 0, -0.1], -0.093),
  // Judgment: sword held straight overhead, shield set close while the buff activates.
  aster_judgment: P([-0.055, -0.04, 0], [-0.20, 0.02, 0], [-2.91, -0.09, 0.035], [0.10, 0, 0], [-1.22, -0.13, 0.19], [0, 0, -0.1], [-0.30, 0, 0.12], [0.27, 0, -0.11], -0.056),
  // Reactions: shield stays across torso as the knight absorbs the impact.
  hit: P([-0.15, 0.19, -0.03], [-0.15, -0.13, 0], [-0.79, 0.12, -0.19], [-0.13, 0, 0], [-1.38, -0.20, 0.17], [0, 0, -0.10], [0.03, 0, 0.12], [-0.07, 0, -0.12], -0.065),
  stagger: P([-0.26, 0.26, -0.04], [-0.22, -0.13, 0], [-0.64, 0.20, -0.17], [-0.10, 0, 0], [-1.34, -0.14, 0.20], [0, 0, -0.11], [0.15, 0, 0.11], [-0.15, 0, -0.1], -0.09),
  clash: P([-0.19, -0.13, 0], [-0.07, 0.1, 0], [-1.06, -0.20, -0.20], [0.11, 0, 0], [-1.45, -0.17, 0.22], [0, 0, -0.1], [-0.20, 0, 0.12], [0.15, 0, -0.11], -0.095),
};

'''


def patch_kits(s: str) -> str:
    s = replace_one(s, '// Slow, braced two-handed cutting arcs.', ASTER_POSES + '// Slow, braced two-handed cutting arcs.', 'Aster poses anchor')
    s = replace_one(s, '...(kit === "knight" && element === "light" ? ASTER_SWINGS : {})',
                    '...(kit === "knight" && element === "light" ? { ...ASTER_SWINGS, ...ASTER_COMBAT_V2 } : {})',
                    'Aster poses selection')
    needle = '''  t.v = bonusSkill(kit, element);
  // NESA_MOMENTUM_V3'''
    insert = '''  t.v = bonusSkill(kit, element);
  // ASTER_KNIGHT_COMBAT_ANIM_V2: only animation pose keys change, never skill values.
  if (kit === "knight" && element === "light") {
    const asterMoves: Record<string, [string, string]> = {
      heavy: ["aster_heavy_w", "aster_heavy_s"],
      z: ["aster_bash_w", "aster_bash_s"],
      x: ["aster_rise_w", "aster_rise_s"],
      c: ["aster_wave_w", "aster_wave_s"],
      v: ["aster_judgment", "aster_judgment"],
    };
    for (const [key, [wind, swing]] of Object.entries(asterMoves)) {
      if (t[key]) { t[key].pose_w = wind; t[key].pose_s = swing; }
    }
  }
  // NESA_MOMENTUM_V3'''
    return replace_one(s, needle, insert, 'Aster move pose mapping')


def patch_fighter(s: str) -> str:
    # Only direct main-frame and network/spectator pose blends need the fourth argument.
    old = ': (this.poses[this.poseName] ?? this.poses.idle), dt, this.poseSpeed);'
    if s.count(old) != 2:
        raise PatchError(f'Aster action forwarding: expected 2 main blend calls, found {s.count(old)}')
    s = s.replace(old, ': (this.poses[this.poseName] ?? this.poses.idle), dt, this.poseSpeed, this.poseName);')
    anchor = '''        if (this.poseOverride) { p = this.poseOverride; sp = 40; break; }
        if (a?.mode === "leap"'''
    insertion = '''        if (this.poseOverride) { p = this.poseOverride; sp = 40; break; }
        // ASTER_KNIGHT_COMBAT_ANIM_V2: visual anticipation, explosive contact, shield-first reset.
        // No changes to attackStep(), active windows, lunge, collision or damage.
        if (this.kit === "knight" && this.look.element === "light" && a) {
          if (this.atkPhase === 0) { p = a.pose_w; sp = 19; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = 76; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.46) {
            p = a.pose_s; sp = 27;
          } else { p = "aster_reset"; sp = 18; }
          break;
        }
        if (a?.mode === "leap"'''
    return replace_one(s, anchor, insertion, 'Aster attack phase choreography')


def patch_model(s: str) -> str:
    s = replace_one(s, 'blend(pose: Pose, dt: number, speed: number) {',
                    'blend(pose: Pose, dt: number, speed: number, actionPose = "") {',
                    'Model blend pose name forwarding')
    s = replace_one(s,
                    'draw: this.draw, knee: this.knee });',
                    'draw: this.draw, knee: this.knee, pose: actionPose });',
                    'VRM motion pose forwarding')
    s = replace_one(s,
                    'this.vrmRig.style = this.kit === "chainblade" ? "chainblade" :',
                    'this.vrmRig.style = this.kit === "knight" && this.look.element === "light" ? "aster" : this.kit === "chainblade" ? "chainblade" :',
                    'Aster VRM motion style')
    s = replace_one(s,
                    'this.walkPhase += dt * ((this.kit === "greatsword" || this.kit === "hammer") ? 8.5 : 11) * moving * (1 + 0.46 * running);',
                    'this.walkPhase += dt * (this.kit === "knight" && this.look.element === "light" ? 9.2 : (this.kit === "greatsword" || this.kit === "hammer") ? 8.5 : 11) * moving * (1 + 0.46 * running);',
                    'Aster deliberate walk cadence')
    s = replace_one(s,
                    'const stride = (this.kit === "greatsword" || this.kit === "hammer") ? 0.36 : 0.55;',
                    'const stride = this.kit === "knight" && this.look.element === "light" ? 0.44 : (this.kit === "greatsword" || this.kit === "hammer") ? 0.36 : 0.55;',
                    'Aster measured steps')
    anchor = '''    if (this.kit === "hammer") {
      // NESA_NO_FOOT_HEAVINESS_V1'''
    insertion = '''    if (this.kit === "knight" && this.look.element === "light") {
      // ASTER_KNIGHT_COMBAT_ANIM_V2: grounded, upright armor gait; shoulders, not hips, do the work.
      this.torso.rotation.x += 0.025 + 0.045 * running;
      this.torso.rotation.y += Math.sin(this.walkPhase) * 0.018 * moving;
      this.head.rotation.x -= 0.025;
      this.arm_l.rotation.x -= 0.045 * moving; // shield stays near the center while walking
      this.hips.position.y -= 0.008 * (1 - running);
    }
    if (this.kit === "hammer") {
      // NESA_NO_FOOT_HEAVINESS_V1'''
    return replace_one(s, anchor, insertion, 'Aster procedural gait')


def patch_vrm(s: str) -> str:
    s = replace_one(s,
                    'combat?: boolean; hurt?: boolean; draw?: number; knee?: [number, number] }',
                    'combat?: boolean; hurt?: boolean; draw?: number; knee?: [number, number]; pose?: string }',
                    'MotionInfo pose metadata')
    needle = '''  // Feral dual-sickle hunter: hunched, asymmetrical, with deliberately planted feet.'''
    insert = '''  // ASTER_KNIGHT_COMBAT_ANIM_V2: armored one-handed swordsman, upright behind his shield.
  // Less crouched than generic heavy, no feminine hip sway or head tilting.
  aster: { stance: D(12), toeOut: D(10), knee: D(10), drop: 0.028, lean: D(3.5), chin: D(3), shoulderUp: D(2.5), elbowOut: D(8),
    hipSway: 0.002, hipRoll: D(0.3), contra: D(0.5), relaxKnee: D(1.2), headTilt: D(0.3), headYaw: D(3),
    breath: 0.48, armSwing: D(7), walkRoll: D(0.7), walkYaw: D(2) },
  // Feral dual-sickle hunter: hunched, asymmetrical, with deliberately planted feet.'''
    s = replace_one(s, needle, insert, 'Aster VRM style')
    s = replace_one(s,
                    'if (this.shield) this.shieldArm(dt, set);',
                    'if (this.shield) this.shieldArm(dt, set, m.pose ?? "");',
                    'Shield IK action input')
    needle = '''  private shieldArm(dt: number, set: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {'''
    s = replace_one(s, needle,
                    '''  private shieldArm(dt: number, set: (b: THREE.Object3D | null, q: THREE.Quaternion) => void, pose = "") {''',
                    'Shield IK method signature')
    old = '''    const r = this.shieldRaise;
    const want = root.worldToLocal(chest.getWorldPosition(new THREE.Vector3())).add(new THREE.Vector3(0.14 - 0.04 * r, -0.2 + 0.2 * r, 0.27 + 0.06 * r));
    if (this.shieldPos.lengthSq() === 0) this.shieldPos.copy(want);
    else this.shieldPos.lerp(want, 1 - Math.exp(-14 * dt));
    this.solveArm("left", this.shieldPos.clone().add(new THREE.Vector3(0, 0, -0.06)), new THREE.Vector3(0.6, -1, -0.35), set);'''
    new = '''    const r = this.shieldRaise;
    // ASTER_KNIGHT_COMBAT_ANIM_V2: shield genuinely moves to brace, parry space and bash.
    // Kept inside the existing real shoulder/elbow IK, with no unreachable teleports.
    let offset: THREE.Vector3;
    if (this.style === "aster") {
      const raised = pose === "block" || pose === "hit" || pose === "clash" || pose === "stagger";
      const thrust = pose === "aster_bash_s";
      const loaded = pose === "aster_bash_w";
      offset = thrust ? new THREE.Vector3(0.02, -0.085, 0.53)
        : raised ? new THREE.Vector3(0.07, 0.015, 0.37)
        : loaded ? new THREE.Vector3(0.11, -0.16, 0.25)
        : new THREE.Vector3(0.11, -0.14, 0.33);
    } else offset = new THREE.Vector3(0.14 - 0.04 * r, -0.2 + 0.2 * r, 0.27 + 0.06 * r);
    const want = root.worldToLocal(chest.getWorldPosition(new THREE.Vector3())).add(offset);
    if (this.shieldPos.lengthSq() === 0) this.shieldPos.copy(want);
    else this.shieldPos.lerp(want, 1 - Math.exp(-(this.style === "aster" ? 20 : 14) * dt));
    this.solveArm("left", this.shieldPos.clone().add(new THREE.Vector3(0, 0, -0.06)), new THREE.Vector3(0.6, -1, -0.35), set);'''
    s = replace_one(s, old, new, 'Shield IK movement')
    # Aster's wrist must follow the shield movement and not get the generic shield tilt.
    old = '''          const mount = new THREE.Quaternion().setFromEuler(_e.set(D(8) * raise, -D(12), 0, "YXZ"))'''
    new = '''          const tilt = this.style === "aster" ? (m.pose === "aster_bash_s" ? D(-10) : m.pose === "block" ? D(5) : D(10)) : D(8) * raise;
          const mount = new THREE.Quaternion().setFromEuler(_e.set(tilt, -D(12), 0, "YXZ"))'''
    s = replace_one(s, old, new, 'Shield orientation during bash')
    return s

PATCH = {'src/game/kits.ts':patch_kits, 'src/game/fighter.ts':patch_fighter,
         'src/game/model.ts':patch_model, 'src/game/vrm.ts':patch_vrm}

def main() -> None:
    p = argparse.ArgumentParser(description='Install Aster knight-only combat animations (does not alter stats/AI)')
    p.add_argument('project', nargs='?', help='Fight Royale web project directory')
    p.add_argument('--check', action='store_true', help='Check expected code anchors; no files written')
    args = p.parse_args()
    root = project_root(args.project)
    changes: dict[str, bytes] = {}
    for rel in FILES:
        source = (root / rel).read_text(encoding='utf-8')
        if TAG in source:
            print(f'[SKIP] {rel}: Aster animations already installed')
            continue
        updated = PATCH[rel](source)
        if TAG not in updated:
            raise PatchError(f'{rel}: verification marker not present in updated source.')
        changes[rel] = updated.encode('utf-8')
    if not changes:
        print('[OK] Aster animations are already installed; no changes required.')
        return
    print('Target:', root)
    print('Patch files:', ', '.join(changes))
    if args.check:
        print('[CHECK PASSED] All code anchors match; nothing changed.')
        return
    # Stage everything before touching the project; preserve each source in a backup dir.
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = root / '.aster_animation_backups' / stamp
    backup.mkdir(parents=True, exist_ok=False)
    staged: dict[str, Path] = {}
    committed: list[str] = []
    try:
        for rel, contents in changes.items():
            src = root / rel
            save = backup / rel
            save.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, save)
            with tempfile.NamedTemporaryFile(dir=src.parent, prefix='.aster_v2_', delete=False) as f:
                f.write(contents)
                staged[rel] = Path(f.name)
        for rel, temp in staged.items():
            os.replace(temp, root / rel)
            committed.append(rel)
    except Exception:
        for rel in committed:
            shutil.copy2(backup / rel, root / rel)
        raise
    finally:
        for temp in staged.values():
            if temp.exists():
                temp.unlink()
    print(f'[DONE] Aster combat animation V2 installed. Backups: {backup}')
    print('Next: npx tsc --noEmit -p . && npm run dev')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        sys.exit(1)
