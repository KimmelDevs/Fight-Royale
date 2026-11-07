#!/usr/bin/env python3
"""Fight Royale: AI weapon/skill-range awareness and airborne Kaizen X.

Run from your web folder:
    python apply_ai_range_air_kaizen.py
or:
    python apply_ai_range_air_kaizen.py "C:/path/to/web"

Patches AI in 3D arena battles (platform AI stays as before). Kaizen's
Predator's Hook X gets a real airborne variant and 3D-aware hit detection.
No third-party Python dependencies; automatically creates backups.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

TAG = "AI_EFFECTIVE_RANGE_KAIZEN_AIR_HOOK_20261107_V1"
FILES = ["src/game/ai.ts", "src/game/kits.ts", "src/game/game.ts"]


def once(src: str, before: str, after: str, description: str) -> str:
    count = src.count(before)
    if count != 1:
        raise RuntimeError(f"{description}: expected 1 exact source block, found {count}; no files changed.")
    return src.replace(before, after, 1)


RANGE_ENGINE = '''  // EFFECTIVE_RANGE_AWARENESS: choices use the fighter's REAL reach and ready skills.
  // Do not grant AI extra attack range: this only steers its regular movement.
  private rangeOrbitCd = 0;
  private rangeOrbitSign = Math.random() < 0.5 ? -1 : 1;

  private effectiveRangeBand(f: Fighter, o: Fighter): { ideal: number; near: number; far: number } {
    const style = FIGHT_STYLES[f.look.name.toLowerCase()];
    const basicReach = Math.max(1.1, f.attacks.l1?.reach ?? 1.7);
    const enemyReach = Math.max(1.1, o.attacks.l1?.reach ?? 1.7);
    const ranged = RANGED.has(f.kit);
    // Melee fighters normally work near the outer half of their weapon reach,
    // not standing on the opponent's feet. Short-armed brawlers must close in.
    let ideal = ranged ? (style?.range ?? 5.3) :
      Math.max(1.06, Math.min(basicReach - 0.18, (style?.range ?? basicReach) * 0.94));
    if (!ranged) {
      if (basicReach > enemyReach + 0.45) ideal = Math.min(basicReach - 0.16, ideal + 0.22);
      if (basicReach < enemyReach - 0.5) ideal = Math.max(1.08, ideal - 0.23);
      // Temporarily fight at a real ready skill's range. As soon as it is used,
      // go back to weapon range. This makes projectile-capable melee fighters
      // alternate between zoning and sword pressure rather than face-hugging.
      const vAvailable = "bonusSkillUnlocked" in f && f.bonusSkillUnlocked === true;
      const keys = ["z", "x", "c", ...(vAvailable ? ["v"] : [])];
      for (const key of keys) {
        const a = f.attacks[key];
        if (!a || (f.cooldowns[key] ?? 1) > 0 || f.chainBindT > 0) continue;
        if (a.style === "chain_predator_hook" && o.state !== S.BLOCK) {
          ideal = Math.max(ideal, Math.min(3.85, a.reach - 0.78));
        } else if (a.type === "projectile" && a.speed > 0) {
          ideal = Math.max(ideal, Math.min(4.75, basicReach + 2.0));
        } else if (a.type === "strike" && a.at === "self" && a.radius > basicReach + 0.65) {
          ideal = Math.max(ideal, Math.min(3.25, a.radius - 0.66));
        } else if ((a.type === "melee" || a.type === "phantom") && a.reach > basicReach + 1.0) {
          ideal = Math.max(ideal, Math.min(3.8, a.reach - 0.7));
        }
      }
    }
    // Keep a comfortable band, rather than alternating forward/back each frame.
    ideal = THREE.MathUtils.clamp(ideal, 1.05, ranged ? 6.35 : 5.0);
    const margin = ranged ? 0.7 : Math.max(0.28, Math.min(0.48, ideal * 0.13));
    return { ideal, near: Math.max(0.9, ideal - margin), far: ideal + margin };
  }

'''

NEW_TACTICS = '''/** Range-conscious footwork. Real weapon/ready skill reach determines where to
 * stand; dodge, guard, parry, hazard and stage movement take precedence. */
private tacticalFootwork(f: Fighter, o: Fighter, dt: number) {
  const style = FIGHT_STYLES[f.look.name.toLowerCase()];
  if (!style || f.isDown() || !f.onGround || f.state !== S.IDLE ||
      this.sideT > 0 || this.blockHold > 0 || this.blockWait >= 0 ||
      f.intent.dash.lengthSq() > 0.01) return;
  this.tacticsCd = Math.max(0, this.tacticsCd - dt);
  this.rangeOrbitCd = Math.max(0, this.rangeOrbitCd - dt);
  if (this.rangeOrbitCd <= 0) {
    this.rangeOrbitCd = rand(0.9, 1.9);
    if (Math.random() < 0.72) this.rangeOrbitSign *= -1;
  }
  const toward = o.root.position.clone().sub(f.root.position).setY(0);
  const distance = toward.length();
  if (distance < 0.05) return;
  toward.divideScalar(distance);
  const tangent = new THREE.Vector3(-toward.z, 0, toward.x);
  const punish = this.hasPunishWindow(o);
  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&
    o.atk?.type === "melee" && distance < o.atk.reach + 0.7;
  if (danger) { this.tacticsT = 0; return; }
  const band = this.effectiveRangeBand(f, o);
  // A threatened block can be baited, but not endlessly or beyond the arena edge.
  if (this.tacticsT <= 0 && this.tacticsCd <= 0 &&
      distance < band.far + 0.4 && !punish &&
      (o.state === S.BLOCK || (o.state === S.IDLE && distance < band.near)) &&
      Math.random() < dt * style.bait * (0.45 + this.p.block)) {
    this.tacticsT = rand(0.23, 0.44);
    this.tacticsDir = Math.random() < 0.5 ? -1 : 1;
    this.tacticsCd = rand(1.1, 2.8);
  }
  if (this.tacticsT > 0) {
    this.tacticsT = Math.max(0, this.tacticsT - dt);
    const bait = toward.clone().negate().multiplyScalar(0.6)
      .addScaledVector(tangent, this.tacticsDir * 0.8);
    f.intent.move.copy(this.theaterDirection(f, o, bait));
    return;
  }
  // Move in for an actual punish. Normal basic range remains authoritative.
  const basicReach = f.attacks.l1?.reach ?? 1.75;
  if (punish && distance > basicReach * 0.78 && distance < band.far + 1.5) {
    f.intent.move.copy(this.theaterDirection(f, o, toward));
    return;
  }
  if (distance > band.far) {
    // Stop at effective range. Sprint is still the normal distance-based AI
    // sprint; there is no teleport and the arena boundary is checked.
    f.intent.move.copy(this.theaterDirection(f, o, toward));
  } else if (distance < band.near) {
    // Backpedal/angle out when unnecessarily close, including long melee
    // weapons and chain fighters. Edge-aware steering chooses a safe orbit.
    const away = toward.clone().negate().addScaledVector(tangent, 0.32 * this.rangeOrbitSign);
    f.intent.move.copy(this.theaterDirection(f, o, away));
  } else {
    // Strafe near the chosen distance; avoid perpetual face-to-face rushing.
    const correction = THREE.MathUtils.clamp((distance - band.ideal) * 0.48, -0.26, 0.26);
    const orbit = tangent.clone().multiplyScalar(this.rangeOrbitSign)
      .addScaledVector(toward, correction);
    f.intent.move.copy(this.theaterDirection(f, o, orbit)).multiplyScalar(0.55);
  }
}

'''


def patch_ai(s: str) -> str:
    if TAG in s: return s
    s = once(s, '  private tacticsCd = 0;', '  private tacticsCd = 0;\n' + RANGE_ENGINE,
             'AI effective-range helper')
    start = s.index('/** Choose footwork without teleporting or exceeding the arena movement limits.')
    end = s.index('private hasPunishWindow(', start)
    old = s[start:end]
    if 'private tacticalFootwork(' not in old:
        raise RuntimeError('Cannot locate AI tacticalFootwork; no changes saved.')
    s = once(s, old, NEW_TACTICS, 'Replace fixed-range melee footwork')
    # Personality footwork respects the computed range too, rather than
    # overriding it with a point-blank chase/backstep on every plan.
    s = once(s, '''        const preferred = this.theaterMode === "back" ?
          toward.clone().negate().addScaledVector(lateral, this.theaterSide * 0.3) :
          this.theaterMode === "circle" ? lateral.clone().multiplyScalar(this.theaterSide)
            .addScaledVector(toward, gap > style.range ? 0.27 : -0.15) : toward;''',
      '''        const spacing = this.effectiveRangeBand(f, o);
        const preferred = this.theaterMode === "back" ?
          (gap > spacing.far + 0.25 ? lateral.clone().multiplyScalar(this.theaterSide) :
            toward.clone().negate().addScaledVector(lateral, this.theaterSide * 0.3)) :
          this.theaterMode === "circle" ? lateral.clone().multiplyScalar(this.theaterSide)
            .addScaledVector(toward, gap > spacing.ideal ? 0.27 : -0.15) :
          gap <= spacing.near ? lateral.clone().multiplyScalar(this.theaterSide).addScaledVector(toward, -0.2) : toward;''',
      'Respect the band during showmanship chase')
    # Air X can also be chosen by CPUs when both characters are in its actual
    # vertical and horizontal catch range. Same cooldown and normal X input.
    s = once(s,
      '''    if (!this.aiAirTap && this.projectileSwordCommit <= 0 && !this.readySkillOpportunity(f, o, dt) &&
        !this.theaterOffense(f, o)) this.offense(f, o, dt);''',
      '''    // KAIZEN_AIR_X: use legitimate X key while airborne if the real hook can reach.
    const airHook = f.kit === "chainblade" && !f.stage && !f.onGround &&
      f.state === S.IDLE && f.attacks.x_air?.style === "chain_predator_hook" &&
      (f.cooldowns.x ?? 1) <= 0 && !f.chainBindT && o.state !== S.BLOCK &&
      flatGap > 1.3 && flatGap <= f.attacks.x_air.reach - 0.4 &&
      Math.abs(o.root.position.y - f.root.position.y) <= 2.7;
    if (!this.aiAirTap && airHook && this.skillCd <= 0) {
      f.intent.skill = "x";
      this.skillCd = rand(this.p.skill[0], this.p.skill[1]);
    }
    if (!this.aiAirTap && !f.intent.skill && this.projectileSwordCommit <= 0 &&
        !this.readySkillOpportunity(f, o, dt) && !this.theaterOffense(f, o))
      this.offense(f, o, dt);''',
      'Let AI fire aerial X on a real opening')
    return f'// {TAG}\n' + s


def patch_kits(s: str) -> str:
    if TAG in s: return s
    anchor = '''    x: a({ name: "Predator's Hook", desc: "Throw a long chain to bind one enemy in place for up to 4 seconds. Kaizen may move, but other attacks and skills are locked. Press X again to pull the victim toward you. Blocking or a clash prevents the bind.", cd: 10, wind: 0.22, active: 0.13, recover: 0.45, dmg: 75, guard: 24, reach: 4.8, stun: 0.28, style: "chain_predator_hook", pose_w: "cbh_w", pose_s: "cbh_s" }),'''
    addition = '''
    // Air X is the same Predator's Hook, not a new skill or a second cooldown.
    // Fighter.readSkill() automatically selects x_air when airborne.
    x_air: a({ name: "Predator's Hook", desc: "Midair X: cast the chain at an enemy above or below. A hit binds; press X again to pull. Shares X cooldown.", cd: 10, wind: 0.22, active: 0.13, recover: 0.45, dmg: 75, guard: 24, reach: 4.8, stun: 0.28, style: "chain_predator_hook", pose_w: "cbh_w", pose_s: "cbh_s" }),'''
    s = once(s, anchor, anchor + addition, 'Add explicit Kaizen aerial X')
    return f'// {TAG}\n' + s


def patch_game(s: str) -> str:
    if TAG in s: return s
    s = once(s, '''      const dir = to.clone().divideScalar(Math.max(dist, 0.001));
      // Don't allow a blade clash outside the aiming direction of an air slice.''',
      '''      const dir = to.clone().divideScalar(Math.max(dist, 0.001));
      // A hooked chain has a genuine diagonal aerial reach, unlike a sword swing.
      // Its hit still needs actual distance, facing and an unblocked attack.
      const aerialPredatorHook = f.kit === "chainblade" && a.style === "chain_predator_hook" &&
        (!f.onGround || (d instanceof Fighter && !d.onGround));
      // Don't allow a blade clash outside the aiming direction of an air slice.''',
      'Aerial chain flag in melee collision')
    s = once(s,
      '''dy < (directionalAir || d.atkId === "air_l1" ? 2.1 :
          antiAir || airCombo || d.atkId === "anti_air" || d.atkId.startsWith("air_l") ? 1.65 : 0.8)) {''',
      '''dy < (aerialPredatorHook ? 2.6 : directionalAir || d.atkId === "air_l1" ? 2.1 :
          antiAir || airCombo || d.atkId === "anti_air" || d.atkId.startsWith("air_l") ? 1.65 : 0.8)) {''',
      'Aerial X may clash at midair height')
    s = once(s,
      '''      } else if (dist - d.radius + 0.35 > a.reach ||
          dy > (antiAir ? 3.25 : airCombo ? 1.8 : 1.3) ||
          (dist > 0.6 && dir.dot(fwd) < (antiAir ? -0.08 : 0.15))) continue;''',
      '''      } else if (dist - d.radius + 0.35 > a.reach ||
          dy > (aerialPredatorHook ? 3.15 : antiAir ? 3.25 : airCombo ? 1.8 : 1.3) ||
          (aerialPredatorHook && Math.hypot(Math.max(0, dist - d.radius * 0.4), dy * 0.72) > a.reach + 0.2) ||
          (dist > 0.6 && dir.dot(fwd) < (antiAir ? -0.08 : 0.15))) continue;''',
      'Real 3D distance checks for aerial chain')
    return f'// {TAG}\n' + s


def locate(arg: Path) -> Path:
    options = [arg, arg / 'web', arg.parent]
    for root in options:
        if all((root / f).is_file() for f in FILES):
            return root
    raise RuntimeError(f'Cannot find the project src/game files under {arg}. Run from your web folder or pass its full path.')


def main() -> int:
    parser = argparse.ArgumentParser(description='Install range-aware AI and airborne Kaizen X')
    parser.add_argument('project', nargs='?', default='.', help='Your web folder')
    args = parser.parse_args()
    try:
        root = locate(Path(args.project).expanduser().resolve())
        existing = {f: (root / f).read_text(encoding='utf-8') for f in FILES}
        flags = [TAG in existing[f] for f in FILES]
        if all(flags):
            print('Already installed. No files changed.')
            return 0
        if any(flags):
            raise RuntimeError('Partial installation detected. Restore backups before retrying.')
        patches = [patch_ai, patch_kits, patch_game]
        changed = {f: fn(existing[f]) for f, fn in zip(FILES, patches)}
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for name in FILES:
            src = root / name
            shutil.copy2(src, src.with_name(src.name + f'.before_range_air_{stamp}.bak'))
        for name, content in changed.items():
            (root / name).write_text(content, encoding='utf-8')
        print('Installed: 3D AI effective range + Kaizen airborne Predator\'s Hook.')
        for name in FILES:
            print('  Updated:', name)
        print('Backups created alongside the originals.')
        return 0
    except Exception as exc:
        print('Could not apply patch:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
