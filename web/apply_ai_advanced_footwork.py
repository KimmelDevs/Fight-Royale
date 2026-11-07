#!/usr/bin/env python3
"""Fight Royale AI #8: Advanced Footwork (Nov 8, 2026).

This is a SOURCE-TARGETED, idempotent patch for the user's uploaded game ZIP,
including the optional merged AI #6/#7 fixes. It changes only src/game/ai.ts.

Installation (from the web folder):
    python apply_ai_advanced_footwork.py --dry-run
    python apply_ai_advanced_footwork.py

No third-party Python dependencies. Creates a timestamped .bak backup before
writing. It does NOT modify damage, movement speed, abilities, or cooldowns.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys
import re

MARK = 'AI_ADVANCED_FOOTWORK_V1_20261108'

SETTINGS = '''// AI_ADVANCED_FOOTWORK: movement choices are made in short plans, not every
// frame. Reaction delays and imperfect reads scale with the selected difficulty.
// Even Master uses normal move input, finite turn speed and the arena boundary.
const ADVANCED_FOOTWORK = [
  { read: 0.12, react: [0.54, 0.85], orbit: 0.10, flank: 0,    corner: 0 },
  { read: 0.54, react: [0.37, 0.60], orbit: 0.55, flank: 0.16, corner: 0.22 },
  { read: 0.79, react: [0.23, 0.40], orbit: 0.82, flank: 0.56, corner: 0.63 },
  { read: 0.96, react: [0.12, 0.24], orbit: 0.97, flank: 0.88, corner: 0.88 },
] as const;

'''

FIELDS = '''  // ADVANCED_FOOTWORK: one grounded steering plan per read; no instant turn or teleport.
  private advancedEnemy: Fighter | null = null;
  private advancedMode: "none" | "escape" | "orbit" | "flank" | "corner" = "none";
  private advancedPlanUntil = 0;
  private advancedRetryAt = 0;
  private advancedSide = Math.random() < 0.5 ? -1 : 1;
  private advancedLastDir = new THREE.Vector3();
  private advancedSampleAt = -1;
  private advancedSamplePos = new THREE.Vector3();

'''

METHOD = '''  /** Advanced 3D footwork uses existing intent.move only: no added dash,
   * attack range, i-frames, guard bypass, or privileged enemy information.
   * Scoring candidate *paths* prevents a great orbit from stepping into fire
   * or trying to walk through the circular arena wall.
   */
  private advancedFootwork(f: Fighter, o: Fighter, dt: number) {
    if (f.stage || o.stage || f.isDown() || o.isDown() || !f.onGround ||
        f.state !== S.IDLE || f.intent.block || f.intent.attack || f.intent.skill ||
        f.intent.jump || f.intent.dash.lengthSq() > 0.01 ||
        this.blockHold > 0 || this.blockWait >= 0 || this.sideT > 0 ||
        this.projectileSwordCommit > 0 || this.queue.length || this.hold > 0 ||
        this.iqBaitPhase !== "none" || this.tacticsT > 0 ||
        (this.theaterMode !== "none" && this.theaterT > 0) ||
        f.chainBindT > 0 || f.chainBoundBy) return;
    // A committed opponent attack is for dodge/block/parry AI, not voluntary
    // circling. Do not overwrite an urgent response to a visible wind-up.
    const from = f.root.position.clone().setY(0);
    const foe = o.root.position.clone().setY(0);
    const delta = foe.clone().sub(from);
    const gap = delta.length();
    if (gap < 0.08) return;
    const toward = delta.clone().divideScalar(gap);
    if (o.state === S.ATTACK && o.atkPhase === 0 &&
        o.atk?.type === "melee" && gap < o.atk.reach + 0.85) return;
    const now = this.threats.now();
    if (o !== this.advancedEnemy) {
      this.advancedEnemy = o;
      this.advancedMode = "none";
      this.advancedRetryAt = 0;
      this.advancedPlanUntil = 0;
      this.advancedLastDir.set(0, 0, 0);
      this.advancedSampleAt = now;
      this.advancedSamplePos.copy(from);
    }
    const profile = ADVANCED_FOOTWORK[this.iqLevel];
    const arena = Math.max(1.5, f.arenaRadius - f.radius - 0.32);
    const ownClearance = arena - from.length();
    const enemyClearance = arena - foe.length();
    const urgentWall = ownClearance < 1.15;
    const ranged = RANGED.has(f.kit);
    const band = this.effectiveRangeBand(f, o);
    // A small sample can detect being trapped against a wall. A change of
    // orbit direction is then deliberate instead of oscillating every frame.
    if (now - this.advancedSampleAt >= 0.52) {
      if (this.advancedLastDir.lengthSq() > 0.10 &&
          from.distanceTo(this.advancedSamplePos) < 0.16 &&
          ownClearance < 2.1 && this.iqLevel >= 2) {
        this.advancedSide *= -1;
        this.advancedPlanUntil = 0;
        this.advancedRetryAt = 0;
      }
      this.advancedSampleAt = now;
      this.advancedSamplePos.copy(from);
    }
    if (urgentWall && this.advancedMode !== "escape") {
      this.advancedMode = "escape";
      this.advancedPlanUntil = now + 0.36;
    } else if (now >= this.advancedPlanUntil) {
      if (now < this.advancedRetryAt) return;
      // Recognition happens once per short plan, not at the frame rate.
      const seen = Math.random() < profile.read;
      this.advancedRetryAt = now + rand(profile.react[0], profile.react[1]);
      this.advancedPlanUntil = this.advancedRetryAt + rand(0.36, 0.84);
      if (!seen) { this.advancedMode = "none"; return; }
      if (this.iqLevel > 0 && Math.random() < 0.24) this.advancedSide *= -1;
      if (o.state === S.BLOCK && gap < Math.max(4.0, band.far + 1.2) &&
          Math.random() < profile.flank) this.advancedMode = "flank";
      else if (enemyClearance < 2.65 && !ranged && gap < 7.6 &&
               Math.random() < profile.corner) this.advancedMode = "corner";
      else if (Math.random() < profile.orbit) this.advancedMode = "orbit";
      else this.advancedMode = "none";
    }
    if (this.advancedMode === "none") return;
    if (this.advancedMode === "flank" && o.state !== S.BLOCK) {
      this.advancedMode = "orbit";
    }
    if (this.advancedMode === "escape" && ownClearance > 2.4 &&
        now >= this.advancedPlanUntil) this.advancedMode = "orbit";

    const tangent = new THREE.Vector3(-toward.z, 0, toward.x);
    const inward = from.lengthSq() > 0.001
      ? from.clone().negate().normalize() : toward.clone();
    const desired = f.intent.move.clone().setY(0);
    if (desired.lengthSq() > 0.01) desired.normalize();
    const baseline = gap > band.far ? toward.clone() :
      gap < band.near ? toward.clone().negate() :
      tangent.clone().multiplyScalar(this.advancedSide);
    const ideal = THREE.MathUtils.clamp(band.ideal, 1.05, 6.4);
    const target = baseline.clone();
    if (this.advancedMode === "escape") {
      // Near the boundary, move back toward the middle with a tangential bias
      // if the foe is standing directly in the escape lane.
      target.copy(inward).multiplyScalar(1.5);
      if (gap < (o.attacks.l1?.reach ?? 1.8) + 0.5)
        target.addScaledVector(tangent, 0.75 * this.advancedSide);
    } else if (this.advancedMode === "flank") {
      // Use the observed shield's current direction, not hidden input. The
      // enemy still turns normally, so a flank is NEVER a forced backstab.
      const front = new THREE.Vector3(Math.sin(o.root.rotation.y), 0,
                                      Math.cos(o.root.rotation.y));
      const shieldSide = new THREE.Vector3(-front.z, 0, front.x)
        .multiplyScalar(this.advancedSide);
      const flankGoal = foe.clone()
        .addScaledVector(front, -ideal * 0.55)
        .addScaledVector(shieldSide, Math.max(1.15, ideal * 0.88));
      target.copy(flankGoal.sub(from));
      if (gap < band.near) target.addScaledVector(toward, -0.5);
    } else if (this.advancedMode === "corner") {
      // Approach an opponent pinned to the edge from the CENTER side, not
      // from outside the arena. Preserve range and a little orbit motion.
      const outward = foe.lengthSq() > 0.001
        ? foe.clone().normalize() : toward.clone();
      const cornerGoal = foe.clone().addScaledVector(outward, -ideal);
      const around = new THREE.Vector3(-outward.z, 0, outward.x);
      cornerGoal.addScaledVector(around, this.advancedSide * 0.25 * ideal);
      target.copy(cornerGoal.sub(from));
    } else { // orbit
      const correction = THREE.MathUtils.clamp((gap - ideal) * 0.62, -1, 1);
      target.copy(tangent).multiplyScalar(this.advancedSide * 0.85)
        .addScaledVector(toward, correction);
    }
    if (target.lengthSq() < 0.001) target.copy(baseline);
    target.normalize();

    // Test a normal walking-distance horizon, with several intermediate
    // samples. Unsafe paths are rejected instead of later corrected by a dash.
    const look = THREE.MathUtils.clamp(f.moveSpeed * 0.30, 0.85, 1.75);
    const angles = [-1.30, -0.98, -0.66, -0.34, 0, 0.34, 0.66, 0.98, 1.30];
    const options = [target.clone(), baseline.clone(), desired.clone(),
      inward.clone(), tangent.clone(), tangent.clone().negate(),
      ...angles.map(angle => new THREE.Vector3(
        target.x * Math.cos(angle) - target.z * Math.sin(angle), 0,
        target.x * Math.sin(angle) + target.z * Math.cos(angle))),
    ];
    const fires = this.threats.firePatches(f).filter(p =>
      Math.abs(p.pos.y - f.root.position.y) < 1.55);
    let best: THREE.Vector3 | null = null;
    let bestScore = -Infinity;
    for (const candidate of options) {
      if (candidate.lengthSq() < 0.001) continue;
      const dir = candidate.normalize();
      const future = from.clone().addScaledVector(dir, look);
      // No choosing a direction that will hit the wall; leaving a wall is OK.
      let unsafe = false;
      let penalty = 0;
      for (const t of [0.35, 0.7, 1.0]) {
        const p = from.clone().addScaledVector(dir, look * t);
        const extent = p.length();
        if (extent > arena + 0.015 && extent >= from.length() - 0.02) {
          unsafe = true;
          break;
        }
        if (extent > arena - 0.38) penalty += (extent - arena + 0.38) * 4.0;
        for (const fire of fires) {
          const fireGap = Math.hypot(p.x - fire.pos.x, p.z - fire.pos.z);
          const safe = fire.radius + f.radius * 0.35 + 0.30;
          if (fireGap < safe) {
            const hereGap = Math.hypot(from.x - fire.pos.x, from.z - fire.pos.z);
            // Already burning: allow walking OUT, not further into the fire.
            if (fireGap >= hereGap + 0.08) continue;
            penalty += 11 + (safe - fireGap) * 8;
          } else if (fireGap < safe + 0.35) {
            penalty += (safe + 0.35 - fireGap) * 1.5;
          }
        }
      }
      if (unsafe) continue;
      const nextGap = future.distanceTo(foe);
      const rangeGain = Math.abs(gap - ideal) - Math.abs(nextGap - ideal);
      let score = dir.dot(target) * 2.5 + rangeGain * 0.90 - penalty;
      if (desired.lengthSq() > 0.01) score += dir.dot(desired) * 0.43;
      if (this.advancedLastDir.lengthSq() > 0.1)
        score += dir.dot(this.advancedLastDir) * 0.16;
      if (this.advancedMode === "escape") {
        score += (future.length() < from.length() ? 2.5 : -2.0);
        score += dir.dot(inward) * 3.0;
      }
      if (this.advancedMode === "corner") {
        const outward = foe.lengthSq() > 0.001 ? foe.clone().normalize() : toward;
        const myCenterSide = future.clone().sub(foe).dot(outward);
        if (myCenterSide > -0.2) score -= 2.0;
      }
      if (score > bestScore) { bestScore = score; best = dir.clone(); }
    }
    if (!best) {
      // Don't walk into fire/walls if all candidate movement paths are unsafe.
      // Leave the existing movement choice to the hazard defense below.
      this.advancedLastDir.set(0, 0, 0);
      return;
    }
    // Planned movement remains ordinary fighter walking, not frame-perfect
    // strafing or free dodges. Higher AI just picks safer angles more often.
    const pace = this.advancedMode === "escape" ? 1 :
      this.advancedMode === "orbit" ? 0.68 : 0.86;
    f.intent.move.copy(best).multiplyScalar(pace);
    this.advancedLastDir.copy(best);
  }

'''


def replace_one(src: str, old: str, new: str, purpose: str) -> str:
    count = src.count(old)
    if count != 1:
        raise ValueError(f'{purpose}: expected 1 matching anchor, found {count}. '
                         'No files were changed. Please upload your latest ai.ts.')
    return src.replace(old, new, 1)


def patch(source: str) -> str:
    # Always repair the previous installer markers, even if Advanced Footwork
    # was already installed. A bare identifier at the beginning of a .ts file
    # is valid syntax but throws ReferenceError when the module loads.
    result = source
    for old_marker in ('AI_PROJECTILE_CLASH_IQ_V1_20261108',
                       'AI_AERIAL_COMBAT_INTELLIGENCE_V1_20261108'):
        result = re.sub(r'(?m)^([ \t]*)' + re.escape(old_marker) + r'([ \t]*)$',
                        '// ' + old_marker, result)
    if MARK in result:
        return result
    result = replace_one(result,
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n',
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n' + SETTINGS,
        'footwork configuration')
    result = replace_one(result,
        '  private rangeOrbitCd = 0;\n', FIELDS + '  private rangeOrbitCd = 0;\n',
        'footwork decision memory')
    result = replace_one(result,
        '  private position(f: Fighter, o: Fighter, dt: number) {',
        METHOD + '  private position(f: Fighter, o: Fighter, dt: number) {',
        'footwork steering method')
    # After combo IQ, pattern IQ, and normal skill choices, refine ordinary
    # walking input. This must NOT run before those systems and override their
    # decisions. Re-apply fire avoidance last since pattern IQ can set a new move.
    result = replace_one(result,
        '    // Sprint to close long gaps. A direction aimed at retreat/evade is not sprinted.\n',
        '    // AI_ADVANCED_FOOTWORK: positioning refinement only after combat decisions.\n'
        '    // Fire avoidance stays last so later pattern IQ never steers into fire.\n'
        '    if (!f.stage) {\n'
        '      this.advancedFootwork(f, o, dt);\n'
        '      this.avoidFireGround(f);\n'
        '    }\n'
        '    // Sprint to close long gaps. A direction aimed at retreat/evade is not sprinted.\n',
        'footwork final precedence')
    return '// ' + MARK + '\n' + result


def find_root(path: str | None) -> Path:
    choices = [Path(path).expanduser().resolve()] if path else [Path.cwd(), Path.cwd() / 'web']
    for candidate in choices:
        for root in (candidate, candidate / 'web'):
            if (root / 'src' / 'game' / 'ai.ts').is_file():
                return root
    raise FileNotFoundError('Could not find web/src/game/ai.ts; run inside web or pass --path.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', help='Path to your web directory (optional)')
    parser.add_argument('--dry-run', action='store_true', help='Validate without writing files')
    args = parser.parse_args()
    try:
        root = find_root(args.path)
        path = root / 'src' / 'game' / 'ai.ts'
        before = path.read_text(encoding='utf-8')
        after = patch(before)
        if after == before:
            print('Already installed; no changes needed:', path)
            return 0
        if args.dry_run:
            print('VALIDATED — would modify:', path.relative_to(root))
            print('No files changed.')
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup = path.with_name(path.name + '.before_advanced_footwork_' + stamp + '.bak')
        shutil.copy2(path, backup)
        temp = path.with_name('.ai.advanced_footwork.tmp')
        try:
            temp.write_text(after, encoding='utf-8')
            temp.replace(path)
        except Exception:
            if temp.exists(): temp.unlink()
            path.write_text(before, encoding='utf-8')
            raise
        print('Installed AI #8 — Advanced Footwork:', path.relative_to(root))
        print('Backup:', backup)
        return 0
    except Exception as error:
        print('INSTALLATION FAILED:', error, file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
