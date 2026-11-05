#!/usr/bin/env python3
"""Kaizen V7: hold chain bind until Z/X follow-up finishes.

Run from the main Fight Royale web directory:
    py install_kaizen_bind_followup_v7.py

Requires Kaizen/Zarek V4 exact-source patch and Kaizen V6 Z/X bind patch.
Preserves existing skills, icons, blade scaling, spinning defense, and Zarek.
"""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
FILE = ROOT / 'src/game/fighter.ts'
MARKER = 'KAIZEN_BIND_FOLLOWUP_V7'


def replace_once(source: str, before: str, after: str, label: str) -> str:
    count = source.count(before)
    if count != 1:
        raise RuntimeError(
            f'V7 preflight failed in fighter.ts ({label}): expected 1 anchor, found {count}. '
            'No changes made. Please share your current fighter.ts for a matching fix.'
        )
    return source.replace(before, after, 1)


def patch(source: str) -> str:
    source = replace_once(source,
        '''  chainChoiceArmed = false;
  onChainBindResolve: (f: Fighter, dir: "forward" | "backward", kind: "x" | "v") => void = () => {};''',
        '''  chainChoiceArmed = false;
  // KAIZEN_BIND_FOLLOWUP_V7: after selecting Z/X, both remain bound until the action finishes.
  chainBindFinishT = 0;
  chainResolveDirection: "forward" | "backward" | "" = "";
  onChainBindResolve: (f: Fighter, dir: "forward" | "backward", kind: "x" | "v") => void = () => {};''',
        'follow-up state fields')

    source = replace_once(source,
        '''    if (this.chainBindTarget && this.chainBindT > 0) {
      this.chainBindT = Math.max(0, this.chainBindT - dt);
      // KAIZEN_BIND_ZX_V6: press Z to chase/launch, X to pull/throw.
      // Wait for a new skill-key press, so the original cast never auto-resolves.
      const choice = this.intent.skill;
      if (!choice) this.chainChoiceArmed = true;
      else if (this.chainChoiceArmed && (choice === "z" || choice === "x")) {
        const kind = this.chainBindKind;
        this.onChainBindResolve(this, choice === "z" ? "forward" : "backward", kind as "x" | "v");
        this.releaseChainBind();
      }
      if (this.chainBindT === 0) this.releaseChainBind();
    }
    // Both combatants are fixed in place. They can still take HP damage and DOT ticks.
    if (this.chainBindT > 0 || (this.chainBoundBy && this.chainBoundBy.chainBindT > 0)) {
      this.vx = 0; this.velY = 0; this.knock = 0; this.dashT = 0;
      this.airChaseMoveT = 0; this.model.walk = 0; this.trail.emitting = false;
      this.model.chainPose = this.kit === "chainblade" ? "cbv_s" : "idle";
      this.model.chainBindTargetWorld = this.chainBindTarget?.chest() ?? null;
      // No movement / attack / jump update; pose renders in the normal animation pipeline.
      this.poseName = this.kit === "chainblade" ? "cbv_s" : "hit";
      this.poseSpeed = 13;
      this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
      this.trail.update(dt);
      return;
    }
''',
        '''    if (this.chainBindTarget && this.chainBindT > 0) {
      if (this.chainBindFinishT > 0) {
        // KAIZEN_BIND_FOLLOWUP_V7: the chosen move owns the bind until it completes.
        // NEVER pass this key to readSkill() as an ordinary Z or X cast.
        this.intent.skill = "";
        this.chainBindFinishT = Math.max(0, this.chainBindFinishT - dt);
        this.chainBindT = this.chainBindFinishT;
        if (this.chainBindFinishT === 0) this.releaseChainBind();
      } else {
        // Four seconds to choose Z (forward) or X (backward).
        this.chainBindT = Math.max(0, this.chainBindT - dt);
        const choice = this.intent.skill;
        if (!choice) this.chainChoiceArmed = true;
        else if (this.chainChoiceArmed && (choice === "z" || choice === "x")) {
          const direction = choice === "z" ? "forward" : "backward";
          const kind = this.chainBindKind as "x" | "v";
          this.chainChoiceArmed = false;
          this.chainResolveDirection = direction;
          // Serpent Bind's forward launch and delayed landing hit ends at 0.67s.
          // Other follow-ups finish sooner but still need a short chained animation.
          this.chainBindFinishT = kind === "v" && direction === "forward" ? 0.85
            : kind === "v" ? 0.48 : 0.38;
          this.chainBindT = this.chainBindFinishT;
          this.intent.skill = ""; // consume the selection so the normal Z/X cannot fire
          this.onChainBindResolve(this, direction, kind);
        }
        if (this.chainBindT === 0) this.releaseChainBind();
      }
    }
    // Both fighters remain input-locked for the entire follow-up (not just the key press).
    if (this.chainBindT > 0 || (this.chainBoundBy && this.chainBoundBy.chainBindT > 0)) {
      // The target must be allowed to travel vertically during Serpent Bind's forward
      // launch/slam, but still cannot steer, attack, dash or activate skills.
      const launchingVictim = !!this.chainBoundBy &&
        this.chainBoundBy.chainBindFinishT > 0 &&
        this.chainBoundBy.chainBindKind === "v" &&
        this.chainBoundBy.chainResolveDirection === "forward";
      this.vx = 0;
      if (!launchingVictim) this.velY = 0;
      this.knock = 0; this.dashT = 0;
      this.airChaseMoveT = 0; this.model.walk = 0; this.trail.emitting = false;
      this.model.chainPose = this.kit === "chainblade" ? "cbv_s" : "idle";
      this.model.chainBindTargetWorld = this.chainBindTarget?.chest() ?? null;
      this.poseName = this.kit === "chainblade" ? "cbv_s" : "hit";
      this.poseSpeed = 13;
      this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
      if (launchingVictim) {
        if (this.stage) this.verticalPlat(dt);
        else this.vertical(dt);
      }
      this.trail.update(dt);
      return;
    }
''', 'V6 binding/input loop')

    source = replace_once(source,
        '''    this.chainBindT = 4;
    this.chainChoiceArmed = false; // release the initial movement key before selecting
''',
        '''    this.chainBindT = 4;
    this.chainChoiceArmed = false; // require a new key press after the bind connects
    this.chainBindFinishT = 0;
    this.chainResolveDirection = "";
''', 'start-bind cleanup')

    source = replace_once(source,
        '''    this.chainBindT = 0;
    this.chainChoiceArmed = false;
    this.model.chainBindTargetWorld = null;
''',
        '''    this.chainBindT = 0;
    this.chainChoiceArmed = false;
    this.chainBindFinishT = 0;
    this.chainResolveDirection = "";
    // KAIZEN_BIND_FOLLOWUP_V7: prevent the selection key firing after release.
    this.intent.skill = "";
    this.model.chainBindTargetWorld = null;
''', 'release-bind cleanup')

    return source


def main() -> None:
    if not FILE.is_file():
        raise RuntimeError('Missing src/game/fighter.ts; put this installer in your main web folder.')
    original = FILE.read_text(encoding='utf-8')
    if MARKER in original:
        print('Kaizen V7 is already installed. No changes made.')
        return
    updated = patch(original)  # complete preflight before any writes
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = FILE.with_name(f'fighter.ts.kaizen-v7-backup-{stamp}')
    shutil.copy2(FILE, backup)
    FILE.write_text(updated, encoding='utf-8')
    print('PATCH src/game/fighter.ts')
    print('BACKUP', backup.relative_to(ROOT))
    print('DONE: Z/X follow-ups consume inputs; bind remains until follow-up ends.')
    print('Run: npx tsc --noEmit && npm run dev')


if __name__ == '__main__':
    main()
