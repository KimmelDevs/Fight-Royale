#!/usr/bin/env python3
"""Fight Royale: Kaizen parry loses 10% speed (not 90%) and AI chooses V follow-ups.

Run from the web folder:
  python apply_kaizen_parry_speed_v_ai.py
or:
  python apply_kaizen_parry_speed_v_ai.py "C:/path/to/web"

Standalone, dependency-free, safe to rerun. Performs complete preflight then
backs up affected source files before editing them. Only changes fighter.ts,
game.ts, and ai.ts. Works whether the earlier speed-only fix was applied or not.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

SPEED_TAG = 'KAIZEN_PARRY_SPEED_MINUS_10_PERCENT_20261107_V1'
AI_TAG = 'KAIZEN_V_SERPENT_DIRECTION_AI_20261107_V1'


def once(s: str, before: str, after: str, label: str) -> str:
    n = s.count(before)
    if n != 1:
        raise ValueError(f'{label}: expected one anchor, found {n}. No changes applied.')
    return s.replace(before, after, 1)


def one_of(s: str, variants: tuple[str, ...], after: str, label: str) -> str:
    matches = [v for v in variants if s.count(v) == 1]
    if len(matches) != 1:
        raise ValueError(f'{label}: found {len(matches)} supported versions (expected 1). No changes applied.')
    return s.replace(matches[0], after, 1)


def patch_fighter(s: str) -> str:
    if SPEED_TAG in s:
        if 'this.kaizenSpinSpeed = 0.90;' not in s:
            raise ValueError('fighter.ts: speed tag found but multiplier is not 0.90.')
        return s
    s = one_of(s, (
        '  // A perfect parry drops either circular skill to 10% speed.\n'
        '  // Further parries reverse direction but do not slow it below 10%.',
        '  // The first perfect parry drops a circular skill to 1/4 speed.\n'
        '  // Subsequent parries flip direction, without slowing below that floor.',
    ), '  // A parry reduces Kaizen circular spin speed BY 10% (90% remains).\n'
       '  // Further parries reverse direction without additional slowdown.',
       'Kaizen spin-speed comment')
    s = one_of(s, (
        '      this.kaizenSpinSpeed = 0.10;',
        '      this.kaizenSpinSpeed = 0.25;',
    ), '      this.kaizenSpinSpeed = 0.90;', 'Kaizen spin-speed multiplier')
    if 'this.kaizenSpinTimerScale = previous / this.kaizenSpinSpeed;' not in s:
        raise ValueError('fighter.ts: unknown spin timing code.')
    return '// ' + SPEED_TAG + '\n' + s


def patch_game(s: str) -> str:
    if SPEED_TAG in s:
        if 'SPIN -10% - REVERSED CCW' not in s:
            raise ValueError('game.ts: speed tag found but effect text missing.')
        return s
    s = one_of(s, (
        '   * scheduled hits and Fighter.stateT at the same effective 10% tempo. */',
        '   * scheduled hits and Fighter.stateT at the same effective 25% tempo. */',
    ), '   * scheduled hits and Fighter.stateT at the same effective 90% tempo. */',
       'Kaizen combo timing documentation')
    s = one_of(s, (
        '    if (factor <= 1) return; // already at the 10%-speed floor',
        '    if (factor <= 1) return; // already at the 25%-speed floor',
    ), '    if (factor <= 1) return; // later parries reverse only (no extra slowdown)',
       'Kaizen parry clamp documentation')
    for suffix in ('CCW', 'CW'):
        s = one_of(s, (
            f'SPIN 10% - REVERSED {suffix}',
            f'SPIN 25% - REVERSED {suffix}',
        ), f'SPIN -10% - REVERSED {suffix}', f'Kaizen spin clash label {suffix}')
    return '// ' + SPEED_TAG + '\n' + s


V_HELPER = '''  /** Kaizen's V Serpent Bind has TWO existing legal follow-ups:
   * Z = Serpent Lift (forward), X = Serpent Overthrow (backward).
   * Consider arena boundaries, then alternate where both throws are safe.
   */
  private chooseSerpentVFollowup(f: Fighter): "z" | "x" {
    const heading = f.stage
      ? new THREE.Vector3(f.facing, 0, 0)
      : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const roomAt = (distance: number): number => {
      const p = f.root.position.clone().addScaledVector(heading, distance);
      if (f.stage) return Math.min(p.x - (f.stage.blast.l + 1), f.stage.blast.r - 1 - p.x);
      return f.arenaRadius - Math.hypot(p.x, p.z);
    };
    // The full animated victim trajectories end about +1.10m and -1.35m.
    const frontRoom = Math.min(roomAt(1.10), roomAt(0.80));
    const backRoom = Math.min(roomAt(-1.35), roomAt(-0.90));
    let forward: boolean;
    if (frontRoom < 0.65 && backRoom > frontRoom + 0.30) forward = false;
    else if (backRoom < 0.65 && frontRoom > backRoom + 0.30) forward = true;
    else if (Math.abs(frontRoom - backRoom) > 0.75) forward = frontRoom > backRoom;
    else forward = this.chainVAlternate;
    this.chainVAlternate = !this.chainVAlternate;
    return forward ? "z" : "x";
  }

  /** Handle an active bind before ordinary defense returns can skip the recast.
   * Uses only normal input, respects the real chain-choice arming and delay.
   */
  private handleKaizenBindFollowup(f: Fighter, dt: number): boolean {
    if (!f.chainBindTarget || f.chainBindT <= 0) {
      this.chainDecisionT = 0;
      this.chainVFollowup = "";
      return false;
    }
    this.chainDecisionT += dt;
    f.intent.attack = false;
    f.intent.block = false;
    const target = f.chainBindTarget;
    if (f.chainBindKind === "x" && f.chainBindFinishT <= 0) {
      const move = target.root.position.clone().sub(f.root.position).setY(0);
      if (move.length() > 2.3) {
        move.normalize();
        f.intent.move.copy(f.stage ? new THREE.Vector3(Math.sign(move.x), 0, 0) : move);
      }
    } else if (f.chainBindKind === "v" && !this.chainVFollowup) {
      this.chainVFollowup = this.chooseSerpentVFollowup(f);
    }
    if (f.chainBindFinishT <= 0 && f.chainChoiceArmed && this.chainDecisionT >= 0.48) {
      f.intent.skill = f.chainBindKind === "x" ? "x" : this.chainVFollowup;
    }
    return true;
  }

'''

OLD_BIND = '''    // During X binding, decide when to yank. AI can step nearer while the enemy is held.
    // During V, choose Z/X as before. Neither fighter casts ordinary skills in this state.
    if (f.chainBindTarget && f.chainBindT > 0) {
      this.chainDecisionT += dt;
      const target = f.chainBindTarget;
      if (f.chainBindKind === "x" && f.chainBindFinishT <= 0) {
        const move = target.root.position.clone().sub(f.root.position).setY(0);
        if (move.length() > 2.3) {
          move.normalize();
          f.intent.move.copy(f.stage ? new THREE.Vector3(Math.sign(move.x), 0, 0) : move);
        }
      }
      if (f.chainBindFinishT <= 0 && f.chainChoiceArmed && this.chainDecisionT >= 0.7) {
        f.intent.skill = f.chainBindKind === "x" ? "x" : Math.random() < 0.5 ? "z" : "x";
      }
      return;
    }
    this.chainDecisionT = 0;
'''


def patch_ai(s: str) -> str:
    if AI_TAG in s:
        if 'private chooseSerpentVFollowup(f: Fighter): "z" | "x"' not in s:
            raise ValueError('ai.ts: V follow-up tag found but helper is missing.')
        return s
    if 'private iqObserve(f: Fighter, o: Fighter)' not in s:
        raise ValueError('ai.ts: expected Combat IQ version not found.')
    s = once(s, '  private chainDecisionT = 0;', '''  private chainDecisionT = 0;
  // Cache one direction per V bind: don't reroll an animation choice every frame.
  private chainVFollowup: "z" | "x" | "" = "";
  private chainVAlternate = false;''', 'Kaizen V AI state')
    s = once(s, '  think(f: Fighter, dt: number) {', V_HELPER + '  think(f: Fighter, dt: number) {', 'Kaizen V helper')
    s = once(s, '''    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    this.iqObserve(f, o);''', '''    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    // An active grab locks both fighters. Commit to Z/X before other tactics.
    if (this.handleKaizenBindFollowup(f, dt)) return;
    this.iqObserve(f, o);''', 'Kaizen V follow-up priority')
    s = once(s, OLD_BIND, '', 'Remove earlier interruptible chain AI decision')
    return '// ' + AI_TAG + '\n' + s


def main() -> int:
    parser = argparse.ArgumentParser(description='Kaizen spin: 10% reduction on parry, plus CPU V forward/backward follow-ups.')
    parser.add_argument('web_dir', nargs='?', default='.', help='Fight Royale web folder')
    parser.add_argument('--dry-run', action='store_true', help='Check all files without changing them')
    args = parser.parse_args()
    root = Path(args.web_dir).expanduser().resolve()
    targets = {
        root / 'src/game/fighter.ts': patch_fighter,
        root / 'src/game/game.ts': patch_game,
        root / 'src/game/ai.ts': patch_ai,
    }
    missing = [str(p) for p in targets if not p.is_file()]
    if missing:
        print('ERROR: Run from your game web directory; missing:\n  ' + '\n  '.join(missing), file=sys.stderr)
        return 1
    try:
        old = {p: p.read_text(encoding='utf-8') for p in targets}
        new = {p: targets[p](old[p]) for p in targets}
    except (OSError, ValueError, UnicodeError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    changed = [p for p in targets if old[p] != new[p]]
    if not changed:
        print('Already installed. Kaizen spin -10% and CPU V finisher choices are active.')
        return 0
    if args.dry_run:
        print('Preflight passed. Would update: ' + ', '.join(str(p.relative_to(root)) for p in changed))
        return 0
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backups = {}
    try:
        for p in changed:
            backup = p.with_name(p.name + '.before_kaizen_spin_v_ai_' + stamp + '.bak')
            shutil.copy2(p, backup)
            backups[p] = backup
        for p in changed:
            p.write_text(new[p], encoding='utf-8')
    except OSError as e:
        for p, backup in backups.items():
            try:
                shutil.copy2(backup, p)
            except OSError as restore_err:
                print(f'WARNING: Failed to restore {p}: {restore_err}', file=sys.stderr)
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    print('Kaizen fixes installed successfully:')
    print(' - Spin parry only reduces speed by 10% (90% remains).')
    print(' - Further parries reverse the spin, no additional slowing.')
    print(' - AI Serpent Bind V chooses Z (forward) / X (backward) after a successful grab.')
    print(' - Near arena boundaries it favors the safer finish; otherwise it varies both.')
    print(' - Existing skill cooldowns, damage, player inputs, and X-hook behavior remain.')
    print(' - Backups saved beside updated files.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
