#!/usr/bin/env python3
"""Fight Royale AI Improvement #9: Low-Health Survival Intelligence.

Targeted against the user's 2026-11-08 Fight Royale web ZIP and compatible
with the previous merged AI #6/#7 and Advanced Footwork #8 installers.

Run from your fight-royale/web folder:
    python apply_ai_low_health_survival.py --dry-run
    python apply_ai_low_health_survival.py

Uses only the Python standard library; backups are created automatically.
Only src/game/ai.ts and src/game/game.ts are modified; no combat stats change.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

MARK = 'AI_LOW_HEALTH_SURVIVAL_V1_20261108'

CONFIG = '''// LOW_HEALTH_SURVIVAL: recognition is sampled once per planned decision, never
// re-rolled every frame. No added health, invincibility or cooldown reductions.
const SURVIVAL_IQ = [
  { notice: 0.12, hp: 0.18, guard: 0.13, react: [0.62, 0.90], hold: [0.34, 0.52], heal: 0.32 },
  { notice: 0.46, hp: 0.30, guard: 0.22, react: [0.39, 0.62], hold: [0.42, 0.68], heal: 0.57 },
  { notice: 0.77, hp: 0.38, guard: 0.29, react: [0.22, 0.39], hold: [0.51, 0.84], heal: 0.82 },
  { notice: 0.95, hp: 0.43, guard: 0.34, react: [0.11, 0.22], hold: [0.60, 0.96], heal: 0.98 },
] as const;

'''

FIELDS = '''  // LOW_HEALTH_SURVIVAL: decisions stay committed for brief, human-like windows.
  private survivalEnemy: Fighter | null = null;
  private survivalMode: "none" | "retreat" | "recover" | "heal" = "none";
  private survivalObserveAt = -1;
  private survivalUntil = -1;
  private survivalSide = Math.random() < 0.5 ? -1 : 1;
  private survivalHealConsumed = false;
  private survivalDashConsidered = false;

'''

METHOD = '''  /** Low-health survival is a *choice of normal inputs*, not a defensive buff.
   * The AI sees its own HP/guard, visible enemy recovery and real friendly
   * healing circles. Reactive block/dodge/parry, grabs and committed attacks
   * take priority; a critically injured bot can still punish a clear whiff.
   */
  private lowHealthSurvival(f: Fighter, o: Fighter): boolean {
    const now = this.threats.now();
    if (this.survivalEnemy !== o) {
      this.survivalEnemy = o;
      this.survivalMode = "none";
      this.survivalObserveAt = now + rand(SURVIVAL_IQ[this.iqLevel].react[0],
        SURVIVAL_IQ[this.iqLevel].react[1]);
      this.survivalUntil = -1;
      this.survivalHealConsumed = false;
      this.survivalDashConsidered = false;
    }
    if (f.stage || f.isDown() || o.isDown() || !f.onGround ||
        f.state !== S.IDLE || f.intent.block || f.intent.skill ||
        f.intent.jump || f.intent.dash.lengthSq() > 0.01 ||
        this.blockWait >= 0 || this.blockHold > 0 || this.sideT > 0 ||
        this.queue.length > 0 && this.hold > 0 ||
        this.chainDecisionT > 0 && f.chainBindT > 0 || f.chainBoundBy ||
        this.projectileSwordCommit > 0 ||
        this.comboParryTarget > now || this.iqBaitPhase !== "none") return false;

    const profile = SURVIVAL_IQ[this.iqLevel];
    const hpRatio = f.hp / Math.max(1, f.maxHp);
    const guardRatio = f.guard / Math.max(1, f.maxGuard);
    const wounded = hpRatio <= profile.hp;
    const guardCritical = guardRatio <= profile.guard;
    const fullGuard = guardRatio > Math.min(0.70, profile.guard + 0.27);
    const healedEnough = hpRatio > profile.hp + 0.16;
    if (healedEnough && fullGuard) this.survivalMode = "none";
    if (!wounded && !guardCritical && this.survivalMode !== "heal") {
      this.survivalMode = "none";
      return false;
    }

    const from = f.root.position.clone().setY(0);
    const foe = o.root.position.clone().setY(0);
    const toFoe = foe.clone().sub(from);
    const gap = toFoe.length();
    if (gap < 0.001) toFoe.set(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    else toFoe.divideScalar(gap);
    const reach = o.attacks.l1?.reach ?? 1.8;
    const rangedEnemy = RANGED.has(o.kit);
    const threatened = o.state === S.ATTACK && o.atkPhase <= 1 &&
      gap < (o.atk?.type === "melee" ? (o.atk.reach + 0.8) : 5.0);
    // Real threat handling happens earlier; do not override a combat reaction.
    if (threatened) return false;
    // Desperation is NOT cowardice: a visible punish window against a near-KO
    // opponent is a rational chance to win. Normal hitboxes still decide.
    if (this.hasPunishWindow(o) &&
        o.hp / Math.max(1, o.maxHp) < 0.20 &&
        gap < (f.attacks.l1?.reach ?? 1.8) + 0.45) {
      this.survivalMode = "none";
      this.survivalObserveAt = now + 0.45;
      return false;
    }

    const pools = (this.threats.healingPools?.(f) ?? []).filter(pool =>
      pool.remaining > 0.48 &&
      Math.abs(pool.center.y - f.root.position.y) < 1.65);
    const inside = pools.find(pool =>
      from.distanceTo(pool.center.clone().setY(0)) < pool.radius * 0.78);
    const safeToHeal = gap > reach + (rangedEnemy ? 2.7 : 1.5) &&
      o.state !== S.ATTACK;
    // Refresh decisions only after the next observable, difficulty-scaled read.
    if (now >= this.survivalUntil && now >= this.survivalObserveAt) {
      const choose = Math.random() < profile.notice;
      this.survivalObserveAt = now + rand(profile.react[0], profile.react[1]);
      this.survivalUntil = now + rand(profile.hold[0], profile.hold[1]);
      this.survivalSide = Math.random() < 0.5 ? -1 : 1;
      this.survivalHealConsumed = false;
      this.survivalDashConsidered = false;
      this.survivalMode = choose ?
        wounded && (inside || pools.length > 0 || safeToHeal) ? "heal" :
          guardCritical && !wounded ? "recover" : "retreat"
        : "none";
    }
    if (this.survivalMode === "none") return false;

    if (this.survivalMode === "heal" && wounded) {
      // Only attempt a legitimately equipped and ready healing skill. Guests
      // cannot use V, and AI below Master cannot sneak in a fourth skill.
      if (!this.survivalHealConsumed && safeToHeal && !inside) {
        const healKey = ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]
          .find(key => {
            const skill = f.attacks[key];
            return skill && (f.cooldowns[key] ?? 1) <= 0 &&
              skill.type === "buff" &&
              (skill.mode === "healing_water" || skill.mode === "heal");
          });
        if (healKey && Math.random() < profile.heal) {
          f.intent.skill = healKey;
          f.intent.attack = false;
          this.queue = [];
          this.hold = 0;
          this.survivalHealConsumed = true;
          return true;
        }
      }
      if (inside && safeToHeal) {
        // Standing in the WATER is necessary for the legitimate 0.6s heal
        // pulses; do not wander out to continue orbiting for no reason.
        f.intent.move.set(0, 0, 0);
        f.intent.attack = false;
        this.queue = [];
        this.hold = 0;
        return true;
      }
      // Seek a reachable friendly healing pool, but never rush through an
      // opponent in order to reach it. Nearby ground fire is handled last.
      if (!inside && pools.length > 0 && !threatened) {
        const pool = pools.slice().sort((a, b) =>
          from.distanceToSquared(a.center.clone().setY(0)) -
          from.distanceToSquared(b.center.clone().setY(0)))[0];
        const towardPool = pool.center.clone().setY(0).sub(from);
        if (towardPool.length() > 0.15 && towardPool.length() < 6.5) {
          const move = towardPool.normalize();
          const next = from.clone().addScaledVector(move, Math.min(1.2, f.moveSpeed * 0.33));
          if (next.distanceTo(foe) > reach + 0.75 &&
              next.length() < f.arenaRadius - f.radius - 0.18) {
            f.intent.move.copy(move);
            f.intent.attack = false;
            this.queue = [];
            this.hold = 0;
            return true;
          }
        }
      }
    }

    // Choose between retreat and diagonal orbit by comparing actual walk
    // destinations. Don't repeatedly walk into the same arena wall.
    const away = toFoe.clone().negate();
    const tangent = new THREE.Vector3(-toFoe.z, 0, toFoe.x)
      .multiplyScalar(this.survivalSide);
    const inward = from.lengthSq() > 0.01 ? from.clone().negate().normalize() : away.clone();
    const candidates = [away.clone(),
      away.clone().addScaledVector(tangent, 0.70),
      away.clone().addScaledVector(tangent, -0.70),
      tangent.clone(), tangent.clone().negate(),
      inward.clone(), inward.clone().addScaledVector(tangent, 0.45),
      inward.clone().addScaledVector(tangent, -0.45)];
    const arena = f.arenaRadius - f.radius - 0.25;
    const look = Math.min(1.75, Math.max(0.95, f.moveSpeed * 0.35));
    const fire = this.threats.firePatches(f);
    let best: THREE.Vector3 | null = null;
    let score = -1e10;
    for (const candidate of candidates) {
      if (candidate.lengthSq() < 0.01) continue;
      const dir = candidate.normalize();
      const next = from.clone().addScaledVector(dir, look);
      if (next.length() > arena && next.length() >= from.length() - 0.02) continue;
      let value = next.distanceTo(foe) - gap;
      if (this.survivalMode === "recover") value *= 0.80;
      value += dir.dot(tangent) * 0.23;
      if (next.length() < from.length()) value += 0.16;
      for (const patch of fire) {
        if (Math.abs(patch.pos.y - f.root.position.y) > 1.6) continue;
        const nextDist = Math.hypot(next.x - patch.pos.x, next.z - patch.pos.z);
        const hereDist = Math.hypot(from.x - patch.pos.x, from.z - patch.pos.z);
        const limit = patch.radius + f.radius * 0.35 + 0.28;
        if (nextDist < limit && nextDist < hereDist + 0.08)
          value -= 15 + (limit - nextDist) * 5;
      }
      if (value > score) { score = value; best = dir.clone(); }
    }
    if (!best || score < -8) return false;
    f.intent.move.copy(best).multiplyScalar(this.survivalMode === "recover" ? 0.75 : 1);
    f.intent.attack = false;
    this.queue = [];
    this.hold = 0;
    // Critical HP can spend a REAL dash on separation; no invulnerability or
    // cooldown cheating. A clear whiff instead encourages a counterattack.
    if (!this.survivalDashConsidered && hpRatio < 0.14 &&
        gap < reach + 0.65 && f.dashCd <= 0 && this.iqLevel >= 2 &&
        this.survivalMode === "retreat") {
      this.survivalDashConsidered = true; // one chance per plan, not per frame
      if (Math.random() < profile.notice * 0.46) f.intent.dash.copy(best);
    }
    return true;
  }

'''

# Replace-one helper preflights exact location and avoids mangling unknown versions.
def replace_one(src: str, old: str, new: str, what: str) -> str:
    count = src.count(old)
    if count != 1:
        raise ValueError(f'{what}: expected one matching source location, found {count}. '
                         'No changes were made; please upload your current game code.')
    return src.replace(old, new, 1)


def patch_ai(src: str) -> str:
    # Repair the legacy bare update markers even when this installer is rerun.
    for marker in ('AI_PROJECTILE_CLASH_IQ_V1_20261108',
                   'AI_AERIAL_COMBAT_INTELLIGENCE_V1_20261108'):
        src = re.sub(r'(?m)^([ \t]*)' + re.escape(marker) + r'([ \t]*)$',
                     '// ' + marker, src)
    if MARK in src:
        return src
    src = replace_one(src,
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n',
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n' + CONFIG,
        'survival difficulty settings')
    src = replace_one(src,
        '  private rangeOrbitCd = 0;\n', FIELDS + '  private rangeOrbitCd = 0;\n',
        'survival decision memory')
    src = replace_one(src,
        '  private position(f: Fighter, o: Fighter, dt: number) {',
        METHOD + '  private position(f: Fighter, o: Fighter, dt: number) {',
        'survival behavior')
    src = replace_one(src,
        '    this.antiAirCd = Math.max(0, this.antiAirCd - dt);\n',
        '    // LOW_HEALTH_SURVIVAL: all immediate threat reactions already ran.\n'
        '    const survivalActed = this.lowHealthSurvival(f, o);\n'
        '    this.antiAirCd = Math.max(0, this.antiAirCd - dt);\n',
        'survival priority after emergency defense')
    src = replace_one(src,
        '    if (!f.stage && f.onGround && f.state === S.IDLE && !RANGED.has(f.kit) &&\n',
        '    if (!survivalActed && !f.stage && f.onGround && f.state === S.IDLE && !RANGED.has(f.kit) &&\n',
        'skip optional anti-air jump during retreat')
    src = replace_one(src,
        '    if (!f.stage && !f.onGround &&\n',
        '    if (!survivalActed && !f.stage && !f.onGround &&\n',
        'skip optional air slice during retreat')
    src = replace_one(src,
        '    if (!this.aiAirTap && airHook && this.skillCd <= 0) {\n',
        '    if (!survivalActed && !this.aiAirTap && airHook && this.skillCd <= 0) {\n',
        'skip optional airborne hook during retreat')
    src = replace_one(src,
        '    const landedActed = !this.aiAirTap && !f.intent.skill &&\n',
        '    const landedActed = !survivalActed && !this.aiAirTap && !f.intent.skill &&\n',
        'skip landing punish if already retreating')
    src = replace_one(src,
        '    const iqActed = !landedActed && !this.aiAirTap && !f.intent.skill &&\n',
        '    const iqActed = !survivalActed && !landedActed && !this.aiAirTap && !f.intent.skill &&\n',
        'skip combat IQ while recovering')
    src = replace_one(src,
        '    const patternActed = !landedActed && !iqActed && !this.aiAirTap && !f.intent.skill &&\n',
        '    const patternActed = !survivalActed && !landedActed && !iqActed && !this.aiAirTap && !f.intent.skill &&\n',
        'skip pattern rush while recovering')
    src = replace_one(src,
        '    if (!landedActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&\n',
        '    if (!survivalActed && !landedActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&\n',
        'skip offense while recovering')
    # Keep protective footwork from replacing the chosen escape. Existing Ember
    # ground-fire veto must still run AFTER a survival move is selected.
    src = replace_one(src,
        '      this.advancedFootwork(f, o, dt);\n      this.avoidFireGround(f);\n',
        '      if (!survivalActed) this.advancedFootwork(f, o, dt);\n'
        '      this.avoidFireGround(f);\n',
        'preserve survival steering priority') if 'AI_ADVANCED_FOOTWORK_V1_20261108' in src else src
    return '// ' + MARK + '\n' + src


def patch_game(src: str) -> str:
    if MARK in src:
        return src
    anchor = '''    fields: (f: Fighter) => this.magicPools.filter(p => p.kind === "static_field" && p.team !== f.team && p.time > 0)
      .map(p => ({ id: p.id, center: p.center, radius: p.radius })),
'''
    addition = '''    // AI_LOW_HEALTH_SURVIVAL: visible, friendly Healing Water zones; no hidden enemy info.
    healingPools: (f: Fighter) => this.magicPools
      .filter(p => p.kind === "healing_water" && p.team === f.team && p.time > 0.48 &&
        p.owner && !p.owner.isDown())
      .map(p => ({ center: p.center, radius: p.radius, remaining: p.time })),
'''
    src = replace_one(src, anchor, anchor + addition, 'friendly healing-pool feed')
    return '// ' + MARK + '\n' + src


def patch_threat_interface(src: str) -> str:
    if 'healingPools?(f: Fighter)' in src:
        return src
    old = '  fields(f: Fighter): { id: number; center: THREE.Vector3; radius: number }[];\n'
    new = old + '''  /** Visible friendly healing circles; only legitimate water pulse heals. */
  healingPools?(f: Fighter): { center: THREE.Vector3; radius: number; remaining: number }[];
'''
    return replace_one(src, old, new, 'healing-pool interface')


def find_root(path: str | None) -> Path:
    starts = [Path(path).expanduser().resolve()] if path else [Path.cwd(), Path.cwd() / 'web']
    for start in starts:
        for root in (start, start / 'web'):
            if (root / 'src/game/ai.ts').is_file() and (root / 'src/game/game.ts').is_file():
                return root
    raise FileNotFoundError('Cannot find src/game/ai.ts and src/game/game.ts. Run inside web or use --path.')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--path', help='web folder (defaults to current working directory)')
    ap.add_argument('--dry-run', action='store_true', help='Check compatibility without changing files')
    args = ap.parse_args()
    try:
        root = find_root(args.path)
        ai = root / 'src/game/ai.ts'
        game = root / 'src/game/game.ts'
        original = {ai: ai.read_text(encoding='utf-8'), game: game.read_text(encoding='utf-8')}
        # Preflight EVERY edit before writing a single file.
        new_ai = patch_threat_interface(patch_ai(original[ai]))
        new_game = patch_game(original[game])
        changed = {p: data for p, data in ((ai, new_ai), (game, new_game)) if data != original[p]}
        if not changed:
            print('Already installed. No changes needed.')
            return 0
        for p in changed:
            print('Validated:', p.relative_to(root))
        if args.dry_run:
            print('DRY RUN: no files changed.')
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backups = {}
        for p in changed:
            bak = p.with_name(p.name + '.before_survival_' + stamp + '.bak')
            shutil.copy2(p, bak)
            backups[p] = bak
        try:
            for p, data in changed.items():
                temp = p.with_name('.' + p.name + '.survival.tmp')
                temp.write_text(data, encoding='utf-8')
                temp.replace(p)
        except Exception:
            for p in changed:
                p.write_text(original[p], encoding='utf-8')
            raise
        print('Installed AI #9 — Low-Health Survival Intelligence.')
        for p, backup in backups.items():
            print('Modified:', p.relative_to(root), '| Backup:', backup.name)
        print('AI obeys real cooldowns, normal movement, healing pulse and skill unlock rules.')
        return 0
    except Exception as e:
        print('INSTALLATION FAILED:', e, file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
