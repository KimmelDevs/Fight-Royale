#!/usr/bin/env python3
"""Fight Royale — Ember ground-fire radius nerf + hazard-aware CPU V1.

Place beside web/package.json and run:
  py install_ember_ground_fire_ai_v1.py

Requirements: the Aster/Ember gameplay update (Nov 6). The code also works
with Combat V3, Parry AI V4, Zarek Range V1, and Veyr V7 installed.

This installer never patches partially: all text anchors are checked in memory
before making timestamped backups and writing the two TypeScript files.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
FILES = ('src/game/game.ts', 'src/game/ai.ts')
MARK = 'EMBER_GROUND_HAZARD_AI_V1_NOV06'

# Approximately 38% smaller than the original Ember ground-fire circles.
HEAVY_RADIUS = 0.90  # was 1.45
METEOR_RADIUS = 1.25 # was 2.10


def once(s: str, old: str, new: str, location: str) -> str:
    found = s.count(old)
    if found != 1:
        raise ValueError(f'{location}: expected 1 occurrence of {old[:120]!r}, found {found}')
    return s.replace(old, new, 1)


def patch_game(s: str) -> str:
    label = 'src/game/game.ts'
    s = once(s,
        'this.spawnEmberPatch(f, at, a.id === "c" ? 2.1 : 1.45);',
        f'// {MARK}: smaller persistent fire circles (Meteor / charged heavy).\n'
        f'          this.spawnEmberPatch(f, at, a.id === "c" ? {METEOR_RADIUS} : {HEAVY_RADIUS});', label)
    s = once(s,
        '    now: () => this.time,',
        '''    // Enemy burning ground is a navigational hazard for CPUs, not a blockable hit.
    // Same authoritative data drives fire damage, visuals, and AI avoidance.
    firePatches: (f: Fighter) => this.emberPatches
      .filter(p => {
        const owner = this.entities.get(p.ownerId);
        return owner instanceof Fighter && !owner.isDown() &&
          owner.team !== f.team && p.ttl > 0.15;
      })
      .map(p => ({ pos: p.pos, radius: p.radius })),
    now: () => this.time,''', label)
    return s


def patch_ai(s: str) -> str:
    label = 'src/game/ai.ts'
    s = once(s,
        '  now(): number;',
        '''  /** Live enemy Ember fire patches; friendly flames are filtered out by Game. */
  firePatches(f: Fighter): { pos: THREE.Vector3; radius: number }[];
  now(): number;''', label)
    s = once(s,
        '  private chainDecisionT = 0;',
        '''  private chainDecisionT = 0;
  // EMBER_GROUND_HAZARD_AI_V1_NOV06: bias the detour to one side until clear.
  private fireAvoidSide = 1;
  private fireAvoidKey = "";''', label)
    s = once(s,
        '    if (!f.stage) { this.dodge(f); this.position(f, o, dt); }',
        '''    if (!f.stage) { this.dodge(f); this.position(f, o, dt); }
    // Run after normal chase/strafe choices, so fire can veto a dangerous route.
    this.avoidFireGround(f);''', label)
    anchor = '  private trySkill(f: Fighter, key: string, force = false) {'
    method = '''  /** Navigate around enemy ground fire without teleporting or dodging through it.
   * Samples candidate movement directions so the CPU avoids both entering a
   * burning circle and stepping into a second circle while escaping the first.
   * If already burning, it attempts to leave by the shortest safe path.
   * Does not touch shield/parry/skill input or any character damage numbers. */
  private avoidFireGround(f: Fighter) {
    if (f.isDown() || !f.onGround || (f.state !== S.IDLE && f.state !== S.BLOCK)) return;
    const patches = this.threats.firePatches(f).filter(p =>
      Math.abs(p.pos.y - f.root.position.y) < 1.55);
    if (!patches.length) { this.fireAvoidKey = ""; return; }

    const at = f.root.position.clone().setY(0);
    const desired = f.intent.move.clone().setY(0);
    const hasMove = desired.lengthSq() > 0.01;
    if (hasMove) desired.normalize();
    const look = Math.min(1.85, Math.max(0.9, f.moveSpeed * 0.36));

    // Find the hazard that is being stood in or intersects the next movement.
    // A small margin keeps the CPU's body just outside the damage boundary.
    let dangerous: { pos: THREE.Vector3; radius: number } | null = null;
    let dangerScore = -Infinity;
    for (const p of patches) {
      const dx = p.pos.x - at.x, dz = p.pos.z - at.z;
      const safe = p.radius + f.radius * 0.30 + 0.22;
      const along = hasMove ? THREE.MathUtils.clamp(dx * desired.x + dz * desired.z, 0, look) : 0;
      const close = Math.hypot(dx - desired.x * along, dz - desired.z * along);
      const here = Math.hypot(dx, dz);
      const inFire = here < safe;
      // Never hijack an existing move if it heads cleanly OUT of a fire patch.
      const escaping = inFire && hasMove && (dx * desired.x + dz * desired.z) < -0.60 * here;
      if ((!hasMove && !inFire) || (escaping && close >= here - 0.12)) continue;
      if (inFire || (hasMove && close < safe)) {
        const score = (inFire ? 3 : 1) + (safe - Math.min(close, here));
        if (score > dangerScore) { dangerScore = score; dangerous = p; }
      }
    }
    if (!dangerous) { this.fireAvoidKey = ""; return; }

    const away = new THREE.Vector3(at.x - dangerous.pos.x, 0, at.z - dangerous.pos.z);
    if (away.lengthSq() < 0.0001) {
      if (hasMove) away.copy(desired).negate();
      else away.set(f.id % 2 ? 1 : -1, 0, 0);
    }
    away.normalize();
    const tangent = new THREE.Vector3(-away.z, 0, away.x);
    const key = `${dangerous.pos.x.toFixed(2)}:${dangerous.pos.z.toFixed(2)}`;
    if (this.fireAvoidKey !== key) {
      this.fireAvoidKey = key;
      const preference = hasMove ? desired.dot(tangent) : 0;
      this.fireAvoidSide = Math.abs(preference) > 0.1 ? Math.sign(preference) : (f.id % 2 ? 1 : -1);
    }

    if (f.stage) {
      // Platform arenas are effectively one-dimensional: don't step off-stage
      // merely to dodge a ground patch, and never use z (down/drop-through).
      const main = f.stage.plats[0];
      const choices = [this.fireAvoidSide, -this.fireAvoidSide];
      let best = 0, bestScore = -Infinity;
      for (const sign of choices) {
        const x = at.x + sign * look;
        if (x < main.x0 + 0.55 || x > main.x1 - 0.55) continue;
        let score = sign * desired.x * 0.7;
        for (const p of patches) {
          const gap = Math.hypot(x - p.pos.x, at.z - p.pos.z);
          const safe = p.radius + f.radius * 0.3 + 0.22;
          if (gap < safe) score -= 10 * (safe - gap + 0.15);
        }
        if (score > bestScore) { bestScore = score; best = sign; }
      }
      if (best !== 0) f.intent.move.set(best, 0, 0);
      return;
    }

    // Prefer keeping the original path, but strongly penalize any candidate
    // that intersects fire at successive lookahead points.
    const flank = tangent.clone().multiplyScalar(this.fireAvoidSide);
    const candidates = [
      ...(hasMove ? [desired.clone()] : []),
      away.clone(), flank.clone(),
      away.clone().multiplyScalar(0.5).add(flank).normalize(),
      away.clone().addScaledVector(flank, 0.45).normalize(),
      away.clone().addScaledVector(flank, -0.45).normalize(),
      flank.clone().negate(),
      ...(hasMove ? [desired.clone().add(flank).normalize(), desired.clone().sub(flank).normalize()] : []),
    ];
    let best = candidates[0], bestScore = -Infinity;
    for (const dir of candidates) {
      let score = hasMove ? dir.dot(desired) * 1.1 : 0;
      score += dir.dot(flank) * 0.10; // stable clockwise/counterclockwise detour
      for (const distance of [0.35, 0.75, 1.25, look]) {
        const x = at.x + dir.x * distance;
        const z = at.z + dir.z * distance;
        const arenaEdge = Math.hypot(x, z) - (f.arenaRadius - 0.35);
        if (arenaEdge > 0) score -= 25 * arenaEdge;
        for (const p of patches) {
          const gap = Math.hypot(x - p.pos.x, z - p.pos.z);
          const safe = p.radius + f.radius * 0.30 + 0.22;
          if (gap < safe) score -= 7 * (safe - gap + 0.18);
          else if (gap < safe + 0.25) score -= 0.8 * (safe + 0.25 - gap);
        }
      }
      if (score > bestScore) { bestScore = score; best = dir; }
    }
    f.intent.move.copy(best);
  }

'''
    s = once(s, anchor, method + anchor, label)
    return s


def main() -> int:
    if not (ROOT / 'package.json').is_file() or any(not (ROOT / f).is_file() for f in FILES):
        print('ERROR: Put this script in your web/ folder beside package.json and src/game/', file=sys.stderr)
        return 1
    current = {rel: (ROOT / rel).read_text(encoding='utf-8') for rel in FILES}
    if all(MARK in s for s in current.values()):
        print('Already installed: Ember Fire Nerf + CPU Avoidance V1. No changes.'); return 0
    if any(MARK in s for s in current.values()):
        print('ERROR: partial V1 installation markers found. No files changed.', file=sys.stderr)
        return 1
    try:
        patched = {
            'src/game/game.ts': patch_game(current['src/game/game.ts']),
            'src/game/ai.ts': patch_ai(current['src/game/ai.ts']),
        }
        for rel in FILES:
            patched[rel] = '// ' + MARK + '\n' + patched[rel]
    except Exception as exc:
        print('ERROR preflight:', exc, 'No files changed.', file=sys.stderr)
        return 1

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for rel in FILES:
        p = ROOT / rel
        backup = p.with_name(p.name + f'.before_ember_fire_ai_v1_{stamp}.bak')
        shutil.copy2(p, backup)
        tmp = p.with_name(p.name + '.emberfiretmp')
        tmp.write_text(patched[rel], encoding='utf-8')
        tmp.replace(p)
        print(f'PATCH {rel} (backup: {backup.name})')
    print(f'DONE: Ember charged heavy fire radius {HEAVY_RADIUS:.2f}; Meteor fire radius {METEOR_RADIUS:.2f}.')
    print('CPUs now treat enemy Ember fire as an avoidable floor hazard; allies ignore friendly fire.')
    print('Fire duration, DoT, skill damage, beam scaling, Veyr, Zarek and parry/clash logic unchanged.')
    print('Run: npx tsc --noEmit; npm run build; npm run dev')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
