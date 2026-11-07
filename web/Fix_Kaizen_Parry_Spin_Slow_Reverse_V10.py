#!/usr/bin/env python3
"""Fight Royale V10: Kaizen Razor Cyclone / Death Spiral parry counterplay.

Run after V8 Fixed + Fix_Kaizen_Spin_Hits_V9.py (requires both).

When a REAL perfect parry catches one of Kaizen's two circular spinning skills:
  - The REST of that particular spin runs at 25% of normal speed.
  - Damage pulse timers are rescheduled at the same slower cadence: not just VFX.
  - Each further successful parry reverses the chain's orbit: CW -> CCW -> CW.
  - The first slowdown persists until that attack ends; does not stack below 25%.
  - Existing -10% continuous combo damage / +0.20s parry delay are retained.
  - No changes to damage values, skill cooldowns, hitboxes, or other fighters.

Applies to Razor Cyclone (Z) and Thousand Cuts: Death Spiral (C), not Kaizen's
ordinary chain combo, passive spinning guard, or other abilities.

Install from the Fight Royale web folder:
  python .\\Fix_Kaizen_Parry_Spin_Slow_Reverse_V10.py --check
  python .\\Fix_Kaizen_Parry_Spin_Slow_Reverse_V10.py

Safe: verify all anchors before writing; create backups outside the project,
prevent TypeScript from compiling backups, and skip a repeated installation.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys
import tempfile

TAG = 'KAIZEN_PARRY_SPIN_SLOW_REVERSE_V10'
FILES = ('fighter.ts', 'game.ts', 'model.ts')

class PatchError(Exception):
    pass


def project_root(here: Path) -> Path:
    candidates = [here, here / 'web', here.parent, here.parent / 'web']
    for root in candidates:
        if all((root / 'src' / 'game' / f).is_file() for f in FILES):
            return root
    raise PatchError('Run this script in your Fight Royale web folder with src/game/fighter.ts, game.ts and model.ts.')


def one(src: str, before: str, after: str, purpose: str) -> str:
    count = src.count(before)
    if count != 1:
        raise PatchError(f'{purpose}: expected 1 matching source anchor; found {count}. Nothing changed.')
    return src.replace(before, after, 1)


def exactly(src: str, fragment: str, n: int, purpose: str) -> None:
    hits = src.count(fragment)
    if hits != n:
        raise PatchError(f'{purpose}: expected {n} source matches; found {hits}. Nothing changed.')


def fighter_patch(src: str) -> str:
    fields_anchor = '  comboPauseT = 0;\n  isContinuousComboActive() {\n'
    fields = '''  comboPauseT = 0;
  // KAIZEN_PARRY_SPIN_SLOW_REVERSE_V10: per-attack spin tempo.
  // The first perfect parry drops a circular skill to 1/4 speed.
  // Subsequent parries flip direction, without slowing below that floor.
  kaizenSpinSpeed = 1;
  kaizenSpinDirection = 1;
  kaizenSpinTimerScale = 1; // one-shot rescaling factor for remaining timed hits
  isContinuousComboActive() {
'''
    src = one(src, fields_anchor, fields, 'Kaizen spin tempo fields')

    before = '''  onComboParried(): boolean {
    if (!this.isContinuousComboActive()) return false;
    this.comboDamageMult = Math.max(0.35, this.comboDamageMult * 0.90);
    this.comboPauseT += 0.20;
    this.model.recoil = Math.max(this.model.recoil, 0.30);
    return true;
  }
'''
    after = '''  onComboParried(): boolean {
    if (!this.isContinuousComboActive()) return false;
    // Only actual parries of Razor Cyclone / Death Spiral slow and reverse it.
    if (this.kit === "chainblade" && this.atk &&
        (this.atk.style === "chain_razor_cyclone" || this.atk.style === "chain_death_spiral")) {
      const previous = this.kaizenSpinSpeed;
      this.kaizenSpinSpeed = 0.25;
      this.kaizenSpinTimerScale = previous / this.kaizenSpinSpeed;
      this.kaizenSpinDirection *= -1;
    }
    this.comboDamageMult = Math.max(0.35, this.comboDamageMult * 0.90);
    this.comboPauseT += 0.20;
    this.model.recoil = Math.max(this.model.recoil, 0.30);
    return true;
  }
'''
    src = one(src, before, after, 'fighter continuous-parry behavior')

    src = one(src,
        '    this.stateT += advancing;\n',
        '''    // Keep animation pose timing aligned with the slowed damage pulse schedule.
    // Only the CURRENT circular chainblade skill is slowed, never other attacks.
    const slowedKaizenSpin = this.kit === "chainblade" && this.state === S.ATTACK &&
      (this.atk?.style === "chain_razor_cyclone" || this.atk?.style === "chain_death_spiral");
    this.stateT += advancing * (slowedKaizenSpin ? this.kaizenSpinSpeed : 1);
''',
        'attack-state clock')

    src = one(src,
        '    this.comboDamageMult = 1;\n    this.comboPauseT = 0;\n    this.swingSerial++;\n',
        '''    this.comboDamageMult = 1;
    this.comboPauseT = 0;
    this.kaizenSpinSpeed = 1;
    this.kaizenSpinDirection = 1;
    this.kaizenSpinTimerScale = 1;
    this.swingSerial++;
''',
        'reset spin tempo on next attack')

    model_anchor = '    this.model.chainPose = this.kit === "chainblade"\n'
    exactly(src, model_anchor, 2, 'host and remote chain-visual update')
    src = src.replace(model_anchor, '''    this.model.kaizenSpinSpeed = this.kaizenSpinSpeed;
    this.model.kaizenSpinDirection = this.kaizenSpinDirection;
    this.model.kaizenSpinActive = this.kit === "chainblade" && this.state === S.ATTACK &&
      this.kaizenSpinSpeed < 1;
''' + model_anchor)

    src = one(src,
        'this.atkId === "pc" ? 1 : 0];\n',
        '''this.atkId === "pc" ? 1 : 0,
      +this.kaizenSpinSpeed.toFixed(2), this.kaizenSpinDirection];
''',
        'network snapshot spin-visual sync')
    src = one(src,
        '    this.counterVisualRemote = s.length > 48 && s[48] === 1;\n',
        '''    this.counterVisualRemote = s.length > 48 && s[48] === 1;
    // Appended fields: older snapshots default to normal clockwise speed.
    this.kaizenSpinSpeed = s.length > 49 ? s[49] : 1;
    this.kaizenSpinDirection = s.length > 50 ? s[50] : 1;
''',
        'network snapshot apply')
    return '// ' + TAG + '\n' + src


def game_patch(src: str) -> str:
    src = one(src,
        '  private delayComboFollowups(f: Fighter, delay: number) {\n',
        '''  /** After a real parry, stretch only this Kaizen spin's upcoming pulses.
   * Existing 0.20s parry pause is preserved (not multiplied), keeping the
   * scheduled hits and Fighter.stateT at the same effective 25% tempo. */
  private slowKaizenSpinFollowups(f: Fighter) {
    const factor = f.kaizenSpinTimerScale;
    f.kaizenSpinTimerScale = 1;
    if (factor <= 1) return; // already at the 25%-speed floor
    const pauseEnd = this.time + 0.20;
    for (const timer of this.timers) {
      if (timer.owner !== f || timer.serial !== f.swingSerial || timer.t <= this.time) continue;
      timer.t = pauseEnd + Math.max(0, timer.t - pauseEnd) * factor;
    }
  }

  private delayComboFollowups(f: Fighter, delay: number) {
''',
        'scheduled damage pulse slow helper')

    # This branch is present in both the older and newer parry-counter builds.
    src = one(src,
        '          this.delayComboFollowups(attacker, 0.20);\n',
        '''          this.delayComboFollowups(attacker, 0.20);
          if (attacker.kit === "chainblade" && attacker.kaizenSpinSpeed < 1) {
            // The SAME parry reverses the orbit. Further parries flip it again.
            this.slowKaizenSpinFollowups(attacker);
            this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 1.13, 0)),
              attacker.kaizenSpinDirection < 0 ? "SPIN 25% - REVERSED CCW" : "SPIN 25% - REVERSED CW",
              "#9de7ff", 0.84);
          }
''',
        'real successful parry handling')
    return '// ' + TAG + '\n' + src


def model_patch(src: str) -> str:
    src = one(src,
        '  private chainOrbit = 0;\n',
        '''  private chainOrbit = 0;
  // Host/player and multiplayer visual sync; never changes collision geometry.
  kaizenSpinSpeed = 1;
  kaizenSpinDirection = 1;
  kaizenSpinActive = false;
''',
        'chain orbit visual properties')
    src = one(src,
        '    else this.chainPoseClock += dt;\n',
        '    else this.chainPoseClock += dt * (this.kaizenSpinActive ? this.kaizenSpinSpeed : 1);\n',
        'chain pose clock tempo')
    src = one(src,
        '    this.chainOrbit += dt * (blocking ? 15 : orbit ? (strike ? 20 : 11) : attack ? 8 : 1.4);\n',
        '''    // The counter-parried circular skill genuinely rotates in reverse and at
    // one quarter speed. Kaizen's normal spinning shield is NOT affected.
    const spinRate = this.kaizenSpinActive ? this.kaizenSpinSpeed : 1;
    const spinDirection = this.kaizenSpinActive ? this.kaizenSpinDirection : 1;
    this.chainOrbit += dt * (blocking ? 15 : orbit ? (strike ? 20 : 11) : attack ? 8 : 1.4)
      * spinRate * spinDirection;
''',
        'physical-looking chainblade reverse and slow')
    return '// ' + TAG + '\n' + src


def run() -> int:
    parser = argparse.ArgumentParser(description='Kaizen: spinning skills slow to 25% and reverse on perfect parry')
    parser.add_argument('--check', action='store_true', help='validate source compatibility; change nothing')
    opts = parser.parse_args()
    root = project_root(Path.cwd())
    paths = {f: root / 'src' / 'game' / f for f in FILES}
    old = {f: paths[f].read_text(encoding='utf-8') for f in FILES}
    installed = [TAG in old[f] for f in FILES]
    if all(installed):
        print('[OK] Kaizen parry spin slow + reverse V10 already installed; nothing changed.')
        return 0
    if any(installed):
        raise PatchError('Partial V10 installation detected. Restore from the external backup before rerunning.')
    if 'FIGHT_ROYALE_GARRICK_BOB_KAIZEN_ROOK_V7' not in old['fighter.ts']:
        raise PatchError('Requires Garrick/Bob/Kaizen/Rook V8 Fixed first.')
    if 'KAIZEN_SPIN_HIT_RELIABILITY_V9' not in old['game.ts']:
        raise PatchError('Requires Fix_Kaizen_Spin_Hits_V9.py first. This keeps its real hit-pulse detection.')
    patched = {
        'fighter.ts': fighter_patch(old['fighter.ts']),
        'game.ts': game_patch(old['game.ts']),
        'model.ts': model_patch(old['model.ts']),
    }
    if opts.check:
        print('[OK] All 3 files match. The patch is compatible; no files changed.')
        return 0
    backup = Path.home() / 'FightRoyale_Patch_Backups' / f'Kaizen_Parry_Spin_V10_{datetime.now():%Y%m%d_%H%M%S_%f}'
    backup.mkdir(parents=True, exist_ok=False)
    for filename in FILES:
        shutil.copy2(paths[filename], backup / filename)
    for filename in FILES:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='\n', suffix='.tmp', delete=False,
                                         dir=paths[filename].parent) as fh:
            fh.write(patched[filename])
            temp_path = Path(fh.name)
        temp_path.replace(paths[filename])
    print('[DONE] Kaizen circular skills now slow to 25% speed after a parry.')
    print('       Every additional parry reverses the direction (CW / CCW).')
    print('       Damage pulse timings and chain animation stay synchronized.')
    print(f'       Backups (outside the repository): {backup}')
    print('       Run: npx tsc --noEmit -p .  and  npm run build')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(run())
    except (PatchError, OSError) as ex:
        print(f'[ERROR] {ex}')
        raise SystemExit(1)
