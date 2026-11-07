#!/usr/bin/env python3
"""Fight Royale AI Improvement #7: Projectile Clash Intelligence.

CPU fighters observe incoming shots, predict *real* counterfire collisions, and
fire their EXISTING ranged attacks or ready projectile skills when a clash is
physically plausible. It never spawns a shot, edits a cooldown, guarantees a
collision, or intercepts an explosive on purpose.

Requires the earlier projectile-vs-projectile collision update in game.ts.

Run in the `web` folder:
    python apply_ai_projectile_clash_intelligence.py
    python apply_ai_projectile_clash_intelligence.py --dry-run
    python apply_ai_projectile_clash_intelligence.py --path C:/project/web

Requires only Python 3.9+. Backs up both modified files; repeat runs are safe.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARK = 'AI_PROJECTILE_CLASH_IQ_V1_20261108'
CLASH_PREREQ = 'PROJECTILE_VS_PROJECTILE_CLASH_V1'

CONFIG = r'''// AI_PROJECTILE_CLASH_IQ: incoming shots are seen once each, never rerolled
// per frame. A read is an imperfect estimate of a physical mid-flight clash.
const PROJECTILE_CLASH_IQ = [
  { notice: 0.10, reaction: [0.34, 0.54], tolerance: 0.34, reserve: 0.82 },
  { notice: 0.43, reaction: [0.23, 0.37], tolerance: 0.26, reserve: 0.66 },
  { notice: 0.72, reaction: [0.13, 0.24], tolerance: 0.18, reserve: 0.42 },
  { notice: 0.91, reaction: [0.060, 0.135], tolerance: 0.11, reserve: 0.22 },
] as const;
type CounterfireRead = { reactAt: number; wants: boolean; spent: boolean };

'''

FIELDS = r'''  // AI_PROJECTILE_CLASH_IQ: an independent, per-shot decision memory.
  private counterfireEnemy: Fighter | null = null;
  private counterfireReads = new Map<number, CounterfireRead>();
  private counterfireRecoveryUntil = 0;

'''

METHODS = r'''  /** Observe only projectiles already in the arena. No future inputs,
   * target cooldowns, or hidden opponent abilities are inspected.
   */
  private observeCounterfire(f: Fighter, o: Fighter) {
    if (this.counterfireEnemy !== o) {
      this.counterfireEnemy = o;
      this.counterfireReads.clear();
      this.counterfireRecoveryUntil = 0;
    }
    const now = this.threats.now();
    const shots = this.threats.projectiles();
    const living = new Set<number>();
    const readyShot = (f.attacks.l1?.type === "projectile" && f.atkLock <= 0) ||
      ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]
        .some(k => f.attacks[k]?.type === "projectile" && (f.cooldowns[k] ?? 1) <= 0);
    for (const p of shots) {
      living.add(p.id);
      if (this.counterfireReads.has(p.id)) continue;
      if (!readyShot || p.target !== f || (p.team !== undefined && p.team === f.team) ||
          p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb") continue;
      const eta = this.projectileTimeToContact(f, p);
      if (eta < 0.18 || eta > 1.75) continue;
      const profile = PROJECTILE_CLASH_IQ[this.iqLevel];
      this.counterfireReads.set(p.id, {
        reactAt: now + rand(profile.reaction[0], profile.reaction[1]),
        wants: Math.random() < profile.notice, spent: false,
      });
    }
    for (const id of this.counterfireReads.keys()) {
      if (!living.has(id)) this.counterfireReads.delete(id);
    }
    if (this.counterfireReads.size > 180) this.counterfireReads.clear();
  }

  /** Closest approach for an actually fired shot vs a moving hostile shot.
   * Game.fireProjectiles aims at the fighter's current opponent, so we forecast
   * that SAME aim and spread, not an impossible AI-only aimed projectile.
   * Real game projectile collision detection determines the eventual result.
   */
  private predictCounterfireCollision(f: Fighter, o: Fighter,
    p: ReturnType<Threats["projectiles"]>[number],
    a: Fighter["attacks"][string]): { time: number; miss: number } | null {
    if (a.type !== "projectile" || a.speed <= 0 ||
        p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb") return null;
    const eta = this.projectileTimeToContact(f, p);
    if (eta >= 999) return null;
    const origin = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const toward = o.chest().sub(origin);
    if (toward.lengthSq() < 0.05) return null;
    const aim = toward.normalize();
    // Conservative input and animation-frame overhead. Attack wind remains real.
    const launch = Math.max(0.025, a.wind) + 0.025;
    if (launch >= eta - 0.055) return null;
    const offsets = Math.max(1, Math.min(7, a.count));
    const profile = PROJECTILE_CLASH_IQ[this.iqLevel];
    let best: { time: number; miss: number } | null = null;
    for (let i = 0; i < offsets; i++) {
      const angle = offsets === 1 ? 0 : -a.spread + 2 * a.spread * i / (offsets - 1);
      const ownVel = aim.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), angle)
        .multiplyScalar(a.speed);
      const incomingAtLaunch = p.pos.clone().addScaledVector(p.vel, launch);
      const separation = origin.clone().sub(incomingAtLaunch);
      const relativeVel = ownVel.sub(p.vel);
      const speedSq = relativeVel.lengthSq();
      if (speedSq < 1.0) continue;
      const afterLaunch = -separation.dot(relativeVel) / speedSq;
      if (afterLaunch < 0.015 || afterLaunch > 1.10) continue;
      const collisionTime = launch + afterLaunch;
      // An interception after the shot reaches this fighter isn't defensive.
      if (collisionTime > eta - 0.025) continue;
      const miss = separation.addScaledVector(relativeVel, afterLaunch).length();
      const ownRadius = Math.max(0.14, Math.min(0.48, a.size *
        (a.style === "wave" || a.style === "shock" ? 0.37 : 0.23)));
      const theirSize = p.size ?? 1;
      const theirRadius = Math.max(0.14, Math.min(0.48, theirSize *
        (p.style === "wave" || p.style === "shock" ? 0.37 : 0.23)));
      // Difficulty uncertainty is a *stricter* collision requirement for easier
      // bots, not a fake enlargement of the real collision hitboxes.
      const believable = ownRadius + theirRadius - profile.tolerance;
      if (miss > Math.max(0.09, believable)) continue;
      if (!best || miss < best.miss) best = { time: collisionTime, miss };
    }
    return best;
  }

  /** Try ONE legal action per observed shot. Ordinary dodge/parry handling
   * takes over whenever the timing, angle or real attack availability fails.
   */
  private projectileCounterfire(f: Fighter, o: Fighter): boolean {
    const now = this.threats.now();
    if (now < this.counterfireRecoveryUntil || f.isDown() || o.isDown() ||
        f.state !== S.IDLE || !f.onGround || f.atkLock > 0 ||
        f.chainBindT > 0 || f.chainBoundBy || f.dashing() ||
        f.intent.block || f.intent.skill || f.intent.dash.lengthSq() > 0.01 ||
        this.blockWait >= 0 || this.blockHold > 0 || this.queue.length > 0 ||
        this.hold > 0 || this.projectileSwordCommit > 0 ||
        this.comboParryTarget > now ||
        (f.kit === "sickle" && f.bloodFestivalT > 0) ||
        this.threats.firePatches(f).some(p =>
          f.root.position.distanceTo(p.pos) < p.radius + 0.35)) return false;
    const profile = PROJECTILE_CLASH_IQ[this.iqLevel];
    let best: { shot: number; key: string; score: number } | null = null;
    for (const p of this.threats.projectiles()) {
      const read = this.counterfireReads.get(p.id);
      if (!read?.wants || read.spent || now < read.reactAt || p.target !== f ||
          p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb" ||
          (p.team !== undefined && p.team === f.team)) continue;
      const eta = this.projectileTimeToContact(f, p);
      if (eta <= 0.10 || eta > 1.50) continue;
      const heavyIncoming = p.heavy === true || (p.size ?? 1) > 1.65;
      const keys = ["l1", "z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])];
      for (const key of keys) {
        const a = f.attacks[key];
        if (!a || a.type !== "projectile" ||
            (key !== "l1" && (f.cooldowns[key] ?? 1) > 0)) continue;
        const forecast = this.predictCounterfireCollision(f, o, p, a);
        if (!forecast) continue;
        // Avoid wasting an expensive skill if a free normal projectile is a
        // plausible intercept. High-strength shots can justify a heavier reply.
        const strongReply = a.heavy || a.pierce || a.dmg >= 95;
        if (heavyIncoming && !strongReply && this.iqLevel >= 2) continue;
        const expenditure = key === "l1" ? 0 :
          a.cd * (1.2 - profile.reserve) * 0.55;
        const score = (heavyIncoming && strongReply ? 4.8 : 0) +
          (key === "l1" ? 5.4 : 1.2) - expenditure - forecast.miss * 3 -
          forecast.time * 0.3;
        if (!best || score > best.score) best = { shot: p.id, key, score };
      }
    }
    if (!best) return false;
    const choice = best;
    const read = this.counterfireReads.get(choice.shot);
    if (read) read.spent = true;
    this.counterfireRecoveryUntil = now + (choice.key === "l1" ? 0.32 : 0.48);
    // Ordinary Fighter inputs only. These go through the normal attack windup,
    // cooldown, hit tests and Game.resolveProjectileClashes.
    this.queue = [];
    this.hold = 0;
    this.blockWait = -1;
    f.intent.block = false;
    f.intent.move.set(0, 0, 0);
    f.intent.sprint = false;
    if (choice.key === "l1") f.intent.attack = true;
    else {
      f.intent.attack = false;
      f.intent.skill = choice.key;
      this.skillCd = Math.max(this.skillCd, 0.27);
    }
    return true;
  }

'''

GAME_OLD = '''    projectiles: () => this.projectiles.filter((p) => !p.visualOnly).map((p) => ({ target: p.target, pos: p.pos, vel: p.vel, id: p.id })),'''
GAME_NEW = '''    // AI_PROJECTILE_CLASH_IQ: visible shape/size distinguish bombs and heavy shots.
    // No opponent cooldowns, damage values or pending player inputs are exposed.
    projectiles: () => this.projectiles.filter((p) => !p.visualOnly && !p.done).map((p) => ({
      target: p.target, pos: p.pos, vel: p.vel, id: p.id,
      team: p.team, style: p.style, size: p.size,
      atkType: p.atk?.type ?? "", heavy: p.atk?.heavy ?? false,
    })),'''


def replace_one(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise ValueError(f'{label}: expected 1 matching anchor; found {n}. No files were changed.')
    return source.replace(old, new, 1)


def patch_ai(src: str) -> str:
    if MARK in src:
        return src
    out = '// ' + MARK + '\n' + src
    out = replace_one(out,
        'projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number }[];',
        'projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number; '
        'team?: number; style?: string; size?: number; atkType?: string; heavy?: boolean }[];',
        'visible projectile metadata interface')
    out = replace_one(out,
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n',
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n' + CONFIG,
        'projectile clash difficulty parameters')
    out = replace_one(out,
        '  private antiAirCd = 0;\n',
        FIELDS + '  private antiAirCd = 0;\n',
        'per-bot projectile memory')
    out = replace_one(out,
        '  // Predict the actual crossing time of the projectile through the fighter\'s chest.',
        METHODS + '  // Predict the actual crossing time of the projectile through the fighter\'s chest.',
        'counter-fire prediction methods')
    out = replace_one(out,
        '    this.observeAerialOpponent(f, o);\n',
        '    this.observeAerialOpponent(f, o);\n    this.observeCounterfire(f, o);\n',
        'sample visible projectiles at start of think')
    out = replace_one(out,
        '    this.defendLongCombo(f, o);\n    if (!f.stage) {',
        '    this.defendLongCombo(f, o);\n    // Counterfire only when a physically possible shot beats ordinary defense.\n'
        '    if (this.projectileCounterfire(f, o)) return;\n    if (!f.stage) {',
        'choose counterfire before projectile dodge')
    out = replace_one(out,
        '      const predicted = this.projectileTimeToContact(f, p);\n'
        '      // Do not consume the shot at spawn time.',
        '      const predicted = this.projectileTimeToContact(f, p);\n'
        '      // Allow a *short* human reaction window to attempt counterfire,\n'
        '      // but never withhold defense once the projectile becomes urgent.\n'
        '      const counterRead = this.counterfireReads.get(p.id);\n'
        '      if (counterRead?.wants && !counterRead.spent && predicted < 999) {\n'
        '        const remaining = counterRead.reactAt - this.threats.now();\n'
        '        if (remaining > 0 && remaining + 0.17 < predicted) continue;\n'
        '      }\n'
        '      // Do not consume the shot at spawn time.',
        'wait briefly for a real counterfire decision before fallback defense')
    return out


def patch_game(src: str) -> str:
    if MARK in src or 'AI_PROJECTILE_CLASH_IQ: visible shape/size' in src:
        return src
    return replace_one(src, GAME_OLD, GAME_NEW, 'game threat feed')


def resolve_files(path: str | None) -> tuple[Path, Path]:
    if path:
        root = Path(path).expanduser().resolve()
        if root.is_file():
            root = root.parent.parent.parent if root.name in ('ai.ts', 'game.ts') else root.parent
        candidates = (root, root / 'web')
    else:
        script_folder = Path(__file__).resolve().parent
        candidates = (Path.cwd(), Path.cwd() / 'web', script_folder, script_folder / 'web')
    for root in candidates:
        ai = root / 'src' / 'game' / 'ai.ts'
        game = root / 'src' / 'game' / 'game.ts'
        if ai.is_file() and game.is_file():
            return ai, game
    raise FileNotFoundError('Could not find both src/game/ai.ts and src/game/game.ts. '
                            'Run inside your web folder, or pass --path /path/to/web.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', help='Game root or web folder')
    parser.add_argument('--dry-run', action='store_true', help='Verify compatibility, do not change files')
    args = parser.parse_args()
    try:
        ai, game = resolve_files(args.path)
        original_ai = ai.read_text(encoding='utf-8')
        original_game = game.read_text(encoding='utf-8')
        if CLASH_PREREQ not in original_game:
            raise ValueError('Projectile-to-projectile collisions are not installed. '
                             'Run apply_projectile_clashes.py first, then rerun this installer.')
        updated_ai = patch_ai(original_ai)
        updated_game = patch_game(original_game)
        if updated_ai == original_ai and updated_game == original_game:
            print('Projectile Clash Intelligence is already installed. No changes necessary.')
            return 0
        if args.dry_run:
            print('Compatible: can patch', ai, 'and', game)
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        originals = ((ai, original_ai, updated_ai), (game, original_game, updated_game))
        backups = []
        for path, before, after in originals:
            if before != after:
                backup = path.with_name(f'{path.name}.before_projectile_clash_iq_{stamp}.bak')
                shutil.copy2(path, backup)
                backups.append(backup)
        written = []
        try:
            for path, before, after in originals:
                if before == after:
                    continue
                temporary = path.with_name('.' + path.name + '.projectile_iq.tmp')
                try:
                    temporary.write_text(after, encoding='utf-8')
                    temporary.replace(path)
                    written.append((path, before))
                finally:
                    if temporary.exists():
                        temporary.unlink()
        except Exception:
            for path, before in written:
                path.write_text(before, encoding='utf-8')
            raise
        print('Installed AI #7 Projectile Clash Intelligence:')
        print('  ', ai)
        print('  ', game)
        print('Backups:')
        for backup in backups:
            print('  ', backup)
        print('Master aims for timely interceptions; lower difficulties react slower and less often.')
        print('Explosion shots are left to existing dodging. Cooldowns and unlocks remain authoritative.')
        return 0
    except Exception as exc:
        print('INSTALLATION FAILED:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
