#!/usr/bin/env python3
"""Fight Royale AI Upgrade #6: Aerial Combat Intelligence.

Installs into web/src/game/ai.ts (or --path PATH). Includes:
- observed enemy jump tracking and imperfect landing prediction
- difficulty-based aerial interception and midair timing
- landing-position footwork and opportunistic grounded attacks
- normal character inputs only (no altered damage, skill range or cooldowns)

Requires Python 3.9+. Usage:
    python apply_ai_aerial_combat_intelligence.py
    python apply_ai_aerial_combat_intelligence.py --dry-run
    python apply_ai_aerial_combat_intelligence.py --path /path/to/web
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARK = "// AI_AERIAL_COMBAT_INTELLIGENCE_V1_20261108"

CONFIG = '''// Aerial reads use sampled, *visible* position changes, not enemy future inputs.
// Detection is rolled once per jump; reactions take real time. All choices are
// subject to the existing Fighter jump / attack / cooldown / collision rules.
const AERIAL_IQ = [
  { notice: 0.14, react: [0.40, 0.67], landReact: [0.34, 0.50],
    jump: 0.10, strike: 2.2, uncertainty: 1.20 },
  { notice: 0.46, react: [0.27, 0.46], landReact: [0.24, 0.38],
    jump: 0.32, strike: 4.2, uncertainty: 0.70 },
  { notice: 0.76, react: [0.16, 0.30], landReact: [0.14, 0.25],
    jump: 0.61, strike: 7.0, uncertainty: 0.34 },
  { notice: 0.93, react: [0.09, 0.18], landReact: [0.085, 0.16],
    jump: 0.82, strike: 10.5, uncertainty: 0.17 },
] as const;

'''

FIELDS = '''  // AI_AERIAL_COMBAT_INTELLIGENCE: one observation/choice per real jump.
  private aerialEnemy: Fighter | null = null;
  private aerialWasUp = false;
  private aerialHasVelocity = false;
  private aerialSeenAt = -1;
  private aerialLastPos = new THREE.Vector3();
  private aerialVelocity = new THREE.Vector3();
  private aerialLandingSpot = new THREE.Vector3();
  private aerialLandingEta = 99;
  private aerialReactAt = 0;
  private aerialLandedReactAt = 0;
  private aerialLandedUntil = 0;
  private aerialNotice = false;
  private aerialJumpChosen = false;
  private aerialJumpSpent = false;
  private aerialLandingSpent = false;
  private aerialNoise = new THREE.Vector3();

'''

METHODS = '''  /** Track a real airborne target by sampling its position as frames pass.
   * Opponent velY and private attack cooldowns are intentionally NOT read.
   * Sudden teleports, knockback, and a new opponent invalidate stale samples.
   */
  private observeAerialOpponent(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (o !== this.aerialEnemy) {
      this.aerialEnemy = o;
      this.aerialWasUp = false;
      this.aerialHasVelocity = false;
      this.aerialSeenAt = -1;
      this.aerialLandedUntil = 0;
      this.aerialLandingSpent = false;
    }
    if (f.stage || o.stage || o.isDown()) {
      this.aerialWasUp = false;
      this.aerialLandedUntil = 0;
      return;
    }
    if (o.onGround) {
      if (this.aerialWasUp) {
        this.aerialWasUp = false;
        const profile = AERIAL_IQ[this.iqLevel];
        this.aerialLandedReactAt = now + rand(profile.landReact[0], profile.landReact[1]);
        this.aerialLandedUntil = now + 0.62;
        this.aerialLandingSpent = false;
        this.aerialHasVelocity = false;
      }
      return;
    }
    if (!this.aerialWasUp) {
      const profile = AERIAL_IQ[this.iqLevel];
      this.aerialWasUp = true;
      this.aerialSeenAt = now;
      this.aerialLastPos.copy(o.root.position);
      this.aerialVelocity.set(0, 0, 0);
      this.aerialLandingSpot.copy(o.root.position).setY(0);
      this.aerialLandingEta = 99;
      this.aerialHasVelocity = false;
      this.aerialNotice = Math.random() < profile.notice;
      this.aerialReactAt = now + rand(profile.react[0], profile.react[1]);
      this.aerialJumpChosen = Math.random() < profile.jump;
      this.aerialJumpSpent = false;
      this.aerialLandingSpent = false;
      // Imprecise per-jump aim. Do not reroll random noise every animation frame.
      const angle = rand(-Math.PI, Math.PI);
      this.aerialNoise.set(Math.cos(angle), 0, Math.sin(angle))
        .multiplyScalar(rand(0.25, 1) * profile.uncertainty);
      return;
    }
    const elapsed = now - this.aerialSeenAt;
    if (elapsed <= 0.012) return;
    const pos = o.root.position;
    const delta = pos.clone().sub(this.aerialLastPos);
    // Teleports / frame stalls should not produce absurd perfect predictions.
    if (elapsed > 0.25 || delta.length() > Math.max(2.7, 28 * elapsed)) {
      this.aerialHasVelocity = false;
    } else {
      const measured = delta.divideScalar(elapsed);
      if (Math.abs(measured.y) <= 25 && measured.length() <= 28) {
        this.aerialVelocity.lerp(measured, this.aerialHasVelocity ? 0.65 : 1);
        this.aerialHasVelocity = true;
      }
    }
    this.aerialSeenAt = now;
    this.aerialLastPos.copy(pos);
    if (!this.aerialHasVelocity) {
      this.aerialLandingEta = 99;
      return;
    }
    // Arena 3D gravity is 22m/s^2. Solve a ballistic landing estimate from
    // observed height and sampled vertical displacement, not a future position.
    const g = 22;
    const vy = this.aerialVelocity.y;
    const height = Math.max(0, pos.y);
    const t = (vy + Math.sqrt(vy * vy + 2 * g * height)) / g;
    this.aerialLandingEta = THREE.MathUtils.clamp(t, 0, 2.25);
    const lead = Math.min(t, 0.85); // err against over-leading distant jumpers
    const vx = THREE.MathUtils.clamp(this.aerialVelocity.x, -5.5, 5.5);
    const vz = THREE.MathUtils.clamp(this.aerialVelocity.z, -5.5, 5.5);
    this.aerialLandingSpot.set(
      pos.x + vx * lead + this.aerialNoise.x,
      0,
      pos.z + vz * lead + this.aerialNoise.z,
    );
    const radius = Math.max(1, f.arenaRadius - 0.55);
    const flat = this.aerialLandingSpot.length();
    if (flat > radius) this.aerialLandingSpot.multiplyScalar(radius / flat);
  }

  /** Approach the estimated touchdown position, not a magically known target.
   * Normal combat footwork remains the default. Hazard avoidance runs after
   * this method, so active fire patches can still veto an unsafe route.
   */
  private aerialFootwork(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (!this.aerialNotice || !this.aerialWasUp || now < this.aerialReactAt ||
        f.stage || o.stage || f.isDown() || f.state !== S.IDLE ||
        f.intent.block || this.blockHold > 0 || this.blockWait >= 0 ||
        f.intent.dash.lengthSq() > 0.01 || this.projectileSwordCommit > 0 ||
        f.chainBindTarget || f.chainBoundBy || this.iqBaitPhase !== "none") return;
    const target = this.aerialHasVelocity && this.aerialLandingEta < 1.25
      ? this.aerialLandingSpot : o.root.position;
    const toward = target.clone().sub(f.root.position).setY(0);
    const gap = toward.length();
    if (gap < 0.10) return;
    const airReach = f.attacks.air_l1?.reach ?? f.attacks.l1?.reach ?? 1.7;
    // A melee fighter should take a position inside actual weapon range.
    // Ranged fighters preserve room to cast, instead of dashing face-first.
    const preferred = RANGED.has(f.kit) ? 4.5 : Math.max(1.05, airReach * 0.77);
    if (gap > preferred + 0.38 && gap < 9.5) {
      f.intent.move.copy(this.theaterDirection(f, o, toward));
    } else if (!RANGED.has(f.kit) && gap < 0.82) {
      f.intent.move.copy(this.theaterDirection(f, o, toward.negate())).multiplyScalar(0.36);
    }
  }

  /** A planned counter-jump is allowed only in normal 3D arena mode.
   * No auto-launches/teleports: Fighter still processes a normal Space press.
   */
  private shouldAerialJump(f: Fighter, o: Fighter, gap: number): boolean {
    if (!this.aerialNotice || !this.aerialJumpChosen || this.aerialJumpSpent ||
        !this.aerialWasUp || !this.aerialHasVelocity ||
        this.threats.now() < this.aerialReactAt || f.stage || o.stage ||
        f.intent.block || f.intent.dash.lengthSq() > 0.01 ||
        this.blockHold > 0 || this.blockWait >= 0 ||
        this.projectileSwordCommit > 0 || this.threats.firePatches(f).some(p =>
          f.root.position.distanceTo(p.pos) < p.radius + 0.5) ||
        this.aerialLandingEta < 0.34 || this.aerialLandingEta > 1.25 ||
        o.root.position.y < 0.85 || o.root.position.y > 3.4 ||
        gap > Math.max(2.6, (f.attacks.air_l1?.reach ?? 1.9) + 0.75)) return false;
    this.aerialJumpSpent = true;
    return true;
  }

  /** Small post-touchdown attack opportunity. The target gets no forced stun,
   * and the fighter must already be in legitimate basic attack range.
   */
  private aerialLandingPunish(f: Fighter, o: Fighter): boolean {
    const now = this.threats.now();
    if (!this.aerialNotice || this.aerialLandingSpent || !o.onGround ||
        now < this.aerialLandedReactAt || now > this.aerialLandedUntil ||
        !f.onGround || f.stage || o.stage || f.state !== S.IDLE ||
        f.atkLock > 0 || f.intent.skill || f.intent.block ||
        this.blockHold > 0 || this.queue.length || this.hold > 0 ||
        this.projectileSwordCommit > 0 || RANGED.has(f.kit)) return false;
    const basic = f.attacks.l1;
    if (!basic || basic.type !== "melee") return false;
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    if (gap > basic.reach + 0.10) return false;
    // A landing in an active attack is not a safe punish by itself.
    if (o.state === S.ATTACK && o.atkPhase < 2 && o.atk?.type === "melee") return false;
    this.aerialLandingSpent = true;
    this.queue = [[0, 0.065]];
    this.hold = 0;
    return true;
  }

  private aerialAirStrikeChance(o: Fighter, dt: number): boolean {
    // Even when a jump wasn't recognized, the CPU may react to a target
    // it can presently reach. Timing depends on difficulty, not frame rate.
    const profile = AERIAL_IQ[this.iqLevel];
    const speed = !o.onGround && this.aerialNotice &&
      this.threats.now() >= this.aerialReactAt ? profile.strike * 1.2 : profile.strike;
    return Math.random() < 1 - Math.exp(-Math.max(0, dt) * speed);
  }

'''


def unique_replace(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"Cannot patch {label}: expected one matching anchor; found {count}. "
                         "No files have been modified.")
    return source.replace(old, new, 1)


def patch(source: str) -> str:
    if MARK in source:
        return source
    result = MARK + "\n" + source
    result = unique_replace(result,
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n',
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n' + CONFIG,
        'Aerial IQ difficulty settings')
    result = unique_replace(result,
        '  private antiAirCd = 0;\n',
        FIELDS + '  private antiAirCd = 0;\n',
        'per-fighter aerial observation state')
    result = unique_replace(result,
        '  private airDive(f: Fighter, o: Fighter, dt: number): boolean {',
        METHODS + '  private airDive(f: Fighter, o: Fighter, dt: number): boolean {',
        'aerial observation/decision methods')
    result = unique_replace(result,
        '    if (!o || o.isDown()) return;\n',
        '    if (!o || o.isDown()) return;\n    this.observeAerialOpponent(f, o);\n',
        'aerial early observation')
    result = unique_replace(result,
        '    this.kaizenSpinAdvance(f, o);\n    // Run after normal chase/strafe choices, so fire can veto a dangerous route.',
        '    this.kaizenSpinAdvance(f, o);\n'
        '    this.aerialFootwork(f, o);\n'
        '    // Run after normal chase/strafe choices, so fire can veto a dangerous route.',
        'aerial touchdown footwork')
    result = unique_replace(result,
        '        Math.random() < dt * 0.24) {',
        '        (this.shouldAerialJump(f, o, flatGap) ||\n'
        '          (o.onGround && Math.random() < dt * 0.12))) {',
        'planned jump intercepts')
    result = unique_replace(result,
        '        Math.random() < dt * 7.0) {',
        '        this.aerialAirStrikeChance(o, dt)) {',
        'difficulty-based aerial strike timing')
    result = unique_replace(result,
        '    const iqActed = !this.aiAirTap && !f.intent.skill &&\n',
        '    const landedActed = !this.aiAirTap && !f.intent.skill &&\n'
        '      this.aerialLandingPunish(f, o);\n'
        '    const iqActed = !landedActed && !this.aiAirTap && !f.intent.skill &&\n',
        'landing punish before ordinary random offense')
    result = unique_replace(result,
        '    if (!this.aiAirTap && !f.intent.skill && !iqActed &&\n',
        '    if (!landedActed && !this.aiAirTap && !f.intent.skill && !iqActed &&\n',
        'preserve landing attack queue')
    return result


def find_ai(path_arg: str | None) -> Path:
    if path_arg:
        root = Path(path_arg).expanduser().resolve()
        if root.is_file() and root.name == 'ai.ts':
            return root
        for candidate in (root / 'src' / 'game' / 'ai.ts', root / 'web' / 'src' / 'game' / 'ai.ts'):
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(f'Cannot find src/game/ai.ts under {root}')
    for root in (Path.cwd(), Path.cwd() / 'web', Path(__file__).resolve().parent):
        candidate = root / 'src' / 'game' / 'ai.ts'
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('Cannot find src/game/ai.ts. Place the installer in the web '
                            'folder or run with --path /path/to/web')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--path', help='Game web folder or direct path to ai.ts')
    p.add_argument('--dry-run', action='store_true', help='Check patch compatibility without writing')
    args = p.parse_args()
    try:
        ai = find_ai(args.path)
        original = ai.read_text(encoding='utf-8')
        if MARK in original:
            print('Aerial Combat Intelligence is already installed:', ai)
            return 0
        updated = patch(original)
        if args.dry_run:
            print('Compatible; would update:', ai)
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup = ai.with_name(f'ai.ts.before_aerial_iq_{stamp}.bak')
        shutil.copy2(ai, backup)
        tmp = ai.with_name('.ai.aerial_iq.tmp')
        try:
            tmp.write_text(updated, encoding='utf-8')
            tmp.replace(ai)
        finally:
            if tmp.exists():
                tmp.unlink()
        print('Installed AI #6 Aerial Combat Intelligence:', ai)
        print('Backup:', backup)
        print('Preserved: AI #5 cooldown memory, Kaizen V, Combat IQ, dodge and skills')
        return 0
    except Exception as exc:
        print('INSTALLATION FAILED:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
