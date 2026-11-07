#!/usr/bin/env python3
"""Fight Royale: AI_LOW_HEALTH_LAST_STAND_V2.

Fixes low-HP CPU-versus-CPU stalemates without changing player combat stats.
Requires the earlier Low-Health Survival #9 update. Compatible with #8 Advanced
Footwork and #10 Character-Specific Fighting Styles.

From the Fight Royale web folder:
    python apply_ai_low_health_last_stand_v2.py --dry-run
    python apply_ai_low_health_last_stand_v2.py

Alternative: --path "C:/path/to/fight-royale/web"
Standard library only. Preflights changes and backs up ai.ts before writing.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

MARK = 'AI_LOW_HEALTH_LAST_STAND_V2_20261108'

FIELDS = '''  // LAST_STAND_V2: track *observable HP changes*, never hidden opponent inputs.
  private lastStandOpponent: Fighter | null = null;
  private lastStandObservedAt = -1;
  private lastStandSelfHp = 0;
  private lastStandEnemyHp = 0;
  private lastStandLastDamageAt = -1;
  private lastStandUntil = -1;
  private survivalPressureUntil = -1;
  private survivalRetreatStartedAt = -1;
  private survivalRetreatOrigin = new THREE.Vector3();

'''

HELPERS = '''  /** Track elapsed time without damage even when an urgent dodge/parry has
   *  returned early. Last Stand is based only on visible HP and positions.
   *  A new opponent or restarted round resets every observation.
   */
  private observeLastStand(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    const freshRound = this.lastStandOpponent !== o ||
      now < this.lastStandObservedAt - 0.15 ||
      (f.hp >= f.maxHp * 0.98 && this.lastStandSelfHp < f.maxHp * 0.40 &&
        f.hp - this.lastStandSelfHp > f.maxHp * 0.50) ||
      (o.hp >= o.maxHp * 0.98 && this.lastStandEnemyHp < o.maxHp * 0.40 &&
        o.hp - this.lastStandEnemyHp > o.maxHp * 0.50);
    if (freshRound) {
      this.lastStandOpponent = o;
      this.lastStandLastDamageAt = now;
      this.lastStandUntil = -1;
      this.survivalPressureUntil = -1;
      this.survivalRetreatStartedAt = -1;
      this.survivalMode = "none";
    } else if (f.hp < this.lastStandSelfHp - 0.05 ||
               o.hp < this.lastStandEnemyHp - 0.05) {
      this.lastStandLastDamageAt = now;
    }
    this.lastStandSelfHp = f.hp;
    this.lastStandEnemyHp = o.hp;
    this.lastStandObservedAt = now;
    if (f.stage || f.isDown() || o.isDown()) return;

    const bothLow = f.hp / Math.max(1, f.maxHp) < 0.30 &&
      o.hp / Math.max(1, o.maxHp) < 0.30;
    if (!bothLow || now < this.lastStandUntil) return;
    // Lower difficulties take longer to realize the fight has stalled.
    const delay = [6.0, 5.2, 4.5, 4.0][this.iqLevel] ?? 4.0;
    const quiet = now - this.lastStandLastDamageAt;
    if (quiet < delay) return;
    const gap = f.root.position.clone().setY(0).distanceTo(
      o.root.position.clone().setY(0));
    const desired = this.effectiveRangeBand(f, o).far;
    const nearEdge = f.root.position.clone().setY(0).length() > f.arenaRadius - f.radius - 1.5 ||
      o.root.position.clone().setY(0).length() > o.arenaRadius - o.radius - 1.5;
    // Also break a face-to-face defensive standoff after another 2.5 seconds.
    if (gap > Math.max(3.0, desired + 1.25) || nearEdge || quiet > delay + 2.5) {
      this.lastStandUntil = now + 5.5; // committed 5+ seconds, never frame toggling
      this.survivalRetreatStartedAt = -1;
    }
  }

  /** During pressure or Last Stand, advance only when outside effective range.
   * Keep regular attacks, parries, blocks, real cooldowns and fire avoidance.
   * This runs AFTER regular footwork, BEFORE the final fire safety veto.
   */
  private lastStandFootwork(f: Fighter, o: Fighter) {
    if (this.survivalMode !== "lastStand" && this.survivalMode !== "pressure") return;
    if (f.stage || !f.onGround || f.state !== S.IDLE || f.intent.block ||
        f.intent.jump || f.intent.skill || f.intent.dash.lengthSq() > 0.001 ||
        this.blockHold > 0 || this.projectileSwordCommit > 0) return;
    const from = f.root.position.clone().setY(0);
    const enemy = o.root.position.clone().setY(0);
    const toward = enemy.sub(from);
    const gap = toward.length();
    if (gap < 0.001) return;
    toward.divideScalar(gap);
    const band = this.effectiveRangeBand(f, o);
    const cap = f.arenaRadius - f.radius - 0.28;
    const edge = from.length() > cap - 0.8;
    // For ranged fighters, close to casting distance, not melee face-hugging.
    if (gap <= band.ideal + 0.75 && !edge) return;
    let dir = toward.clone();
    if (edge) {
      const inward = from.clone().negate().normalize();
      // Prevent the old retreat/orbit planner from continuing to press the wall.
      if (dir.dot(inward) < 0.15) dir.addScaledVector(inward, 0.70).normalize();
    }
    const projected = from.clone().addScaledVector(dir, Math.min(1.35, f.moveSpeed * 0.30));
    if (projected.length() > cap && projected.length() >= from.length()) return;
    for (const patch of this.threats.firePatches(f)) {
      if (Math.abs(patch.pos.y - f.root.position.y) > 1.6) continue;
      const radius = patch.radius + f.radius * 0.35 + 0.25;
      const here = Math.hypot(from.x - patch.pos.x, from.z - patch.pos.z);
      const next = Math.hypot(projected.x - patch.pos.x, projected.z - patch.pos.z);
      if (next < radius && next < here + 0.08) return;
    }
    // Don't force the fighter into the active range of an incoming melee hit.
    if (o.state === S.ATTACK && o.atk?.type === "melee" &&
        gap < o.atk.reach + 0.55) return;
    f.intent.move.copy(dir);
  }

'''

ENTRY = '''    // LAST_STAND_V2: run this before any early defensive returns so a real
    // parry/dodge doesn't erase observation of prolonged inactivity.
    this.observeLastStand(f, o);
'''

EARLY = '''    // LAST_STAND_V2: a mutual low-HP standoff beats voluntary retreat, but
    // reactive defense and legal offense still run in their existing order.
    if (this.lastStandUntil > now &&
        f.hp / Math.max(1, f.maxHp) < 0.35 &&
        o.hp / Math.max(1, o.maxHp) < 0.35) {
      this.survivalMode = "lastStand";
      return false;
    }
    // After a capped retreat, force several seconds of regular combat logic.
    if (this.survivalPressureUntil > now) {
      this.survivalMode = "pressure";
      return false;
    }
    if (this.survivalPressureUntil > 0 && now >= this.survivalPressureUntil) {
      this.survivalPressureUntil = -1;
      this.survivalRetreatStartedAt = -1;
      this.survivalMode = "none";
    }
'''

CAP = '''    // LAST_STAND_V2: survival is tactical, not an endless retreat loop.
    // Retreatment may last at most 2 seconds, travel at most 5 meters, and
    // cannot continue outward at the edge of the arena.
    if (this.survivalMode === "retreat" || this.survivalMode === "recover") {
      if (this.survivalRetreatStartedAt < 0) {
        this.survivalRetreatStartedAt = now;
        this.survivalRetreatOrigin.copy(from);
      }
      const elapsed = now - this.survivalRetreatStartedAt;
      const moved = from.distanceTo(this.survivalRetreatOrigin);
      const boundary = f.arenaRadius - f.radius - 1.0;
      const nearWall = from.length() >= boundary;
      const maxSeconds = this.survivalMode === "recover" ? 1.4 : 2.0;
      if (elapsed >= maxSeconds || moved >= 5.0 || nearWall) {
        this.survivalMode = "pressure";
        this.survivalPressureUntil = now + (this.iqLevel >= 2 ? 3.4 : 2.7);
        this.survivalUntil = -1;
        return false; // let whiff punish, combo and normal offense run
      }
    }
'''


def replace_once(src: str, old: str, new: str, label: str) -> str:
    count = src.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected 1 matching anchor, found {count}. '
                         'Upload the latest ai.ts if it differs from the prior update.')
    return src.replace(old, new, 1)


def patch_ai(src: str) -> str:
    # Repair bare legacy feature markers without making them executable.
    for old_marker in ('AI_PROJECTILE_CLASH_IQ_V1_20261108',
                       'AI_AERIAL_COMBAT_INTELLIGENCE_V1_20261108'):
        src = re.sub(r'(?m)^([ \t]*)' + re.escape(old_marker) + r'[ \t]*$',
                     r'\1// ' + old_marker, src)
    if MARK in src:
        return src
    if 'AI_LOW_HEALTH_SURVIVAL_V1_20261108' not in src:
        raise ValueError('Install Low-Health Survival AI #9 before Last Stand V2.')
    src = replace_once(src,
        '  private survivalEnemy: Fighter | null = null;\n',
        FIELDS + '  private survivalEnemy: Fighter | null = null;\n',
        'insert last stand observation state')
    src = replace_once(src,
        '  /** Low-health survival is a *choice of normal inputs*, not a defensive buff.\n',
        HELPERS + '  /** Low-health survival is a *choice of normal inputs*, not a defensive buff.\n',
        'insert last stand and pressure helpers')
    src = replace_once(src,
        '    this.observePatterns(f, o, dt);\n',
        '    this.observePatterns(f, o, dt);\n' + ENTRY,
        'observe fighter HP on every tick')
    src = replace_once(src,
        '      if (!survivalActed) this.advancedFootwork(f, o, dt);\n'
        '      this.avoidFireGround(f);\n',
        '      if (!survivalActed) {\n'
        '        this.advancedFootwork(f, o, dt);\n'
        '        this.lastStandFootwork(f, o);\n'
        '      }\n'
        '      this.avoidFireGround(f);\n',
        'advance safely during pressure or last stand')
    start = src.index('  private lowHealthSurvival(f: Fighter, o: Fighter): boolean {')
    end = src.index('\n  private position(f: Fighter, o: Fighter, dt: number) {', start)
    part = src[start:end]
    part = replace_once(part,
        '      this.survivalDashConsidered = false;\n    }\n    if (f.stage',
        '      this.survivalDashConsidered = false;\n    }\n' + EARLY + '    if (f.stage',
        'prioritize committed last stand')
    part = replace_once(part,
        '    if (this.survivalMode === "none") return false;\n\n'
        '    if (this.survivalMode === "heal" && wounded) {',
        '    if (this.survivalMode === "none") return false;\n\n'
        + CAP + '\n    if (this.survivalMode === "heal" && wounded) {',
        'cap retreat duration and distance')
    src = src[:start] + part + src[end:]
    return '// ' + MARK + '\n' + src


def find_root(arg: str | None) -> Path:
    bases = [Path(arg).expanduser().resolve()] if arg else [Path.cwd().resolve()]
    for base in bases:
        for root in (base, base / 'web'):
            if (root / 'src/game/ai.ts').is_file():
                return root
    raise FileNotFoundError('Cannot find src/game/ai.ts. Run inside web or use --path.')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--path', help='path to the web folder')
    ap.add_argument('--dry-run', action='store_true', help='validate without writing files')
    args = ap.parse_args()
    try:
        root = find_root(args.path)
        target = root / 'src/game/ai.ts'
        old = target.read_text(encoding='utf-8')
        new = patch_ai(old)
        if new == old:
            print('Already installed; no changes needed:', target)
            return 0
        if args.dry_run:
            print('DRY RUN OK: would update', target)
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = target.with_name(f'ai.ts.before_last_stand_v2_{stamp}.bak')
        shutil.copy2(target, backup)
        tmp = target.with_name(target.name + '.laststand_tmp')
        try:
            tmp.write_text(new, encoding='utf-8')
            tmp.replace(target)
        finally:
            if tmp.exists():
                tmp.unlink()
        print('Installed AI LOW HEALTH LAST STAND V2:', target)
        print('Backup:', backup)
        print('Retreat <= 2s / <= 5m; pressure recovery; 5.5s Last Stand.')
        return 0
    except Exception as exc:
        print('INSTALLATION FAILED:', exc, 'No source file was modified.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
