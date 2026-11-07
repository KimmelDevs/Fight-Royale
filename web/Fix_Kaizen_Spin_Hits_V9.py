#!/usr/bin/env python3
"""Fight Royale V9: Kaizen spin-hit reliability fix. No ZIP required.

Apply AFTER Install_FightRoyale_Garrick_Bob_Kaizen_Rook_V8_Fixed.py.
This narrowly updates only src/game/ai.ts and src/game/game.ts:
  * CPU Kaizen correctly holds Z while Razor Cyclone is active, allowing its
    intended extended pulses. A human still needs to hold Z to extend it.
  * Razor Cyclone and Death Spiral use a short swept-radius test between Kaizen's
    previous/current position so walking during a spin cannot leave tiny gaps.
  * Damage, cooldowns, skill names, hit cadence, parries, dodges, and guards
    remain unchanged. An opponent outside the swept area can still escape.

Usage (from the Fight Royale web folder):
  python .\\Fix_Kaizen_Spin_Hits_V9.py --check
  python .\\Fix_Kaizen_Spin_Hits_V9.py

Safety: verifies expected source shapes before writing, backs up outside your Git
project (to ~/FightRoyale_Patch_Backups), and safely skips reruns.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys
import tempfile

TAG = "KAIZEN_SPIN_HIT_RELIABILITY_V9"


class PatchError(RuntimeError):
    pass


def root_from_here(where: Path) -> Path:
    options = [where, where / "web", where.parent, where.parent / "web"]
    for root in options:
        if (root / "src/game/ai.ts").is_file() and (root / "src/game/game.ts").is_file():
            return root
    raise PatchError("Run this script inside your Fight Royale 'web' folder (src/game/ai.ts and src/game/game.ts must exist).")


def once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{description}: expected one source match; found {count}. No files were changed.")
    return text.replace(old, new, 1)


def patch_ai(src: str) -> str:
    if TAG in src:
        return src
    # Must happen before any early return from the CPU's defensive AI.
    src = once(src,
        '  think(f: Fighter, dt: number) {\n    const o = f.opponent as Fighter | null;\n',
        '''  think(f: Fighter, dt: number) {
    // KAIZEN_SPIN_HIT_RELIABILITY_V9: unlike LocalBrain, AiBrain does not
    // receive a held Z key. Keep it virtually held for the full active spin.
    // This does not bypass cooldowns, change the skill duration, or affect players.
    if (f.kit === "chainblade" && f.state === S.ATTACK &&
        f.atk?.style === "chain_razor_cyclone") f.intent.skillHeld = "z";
    const o = f.opponent as Fighter | null;
''',
        'CPU Z hold')
    return "// " + TAG + "\n" + src


def patch_game(src: str) -> str:
    if TAG in src:
        return src
    if 'const origin = f.root.position.clone(); // spinning field follows Kaizen' not in src:
        raise PatchError("Kaizen's mobile Death Spiral V8 was not detected. Install V8 Fixed first.")

    helper = '''  /** Small swept disk for mobile spin hit checks: the weapon stays damaging
   * while the body walks between timed pulses. Maximum sweep 0.9 arena units;
   * never crosses a dash/teleport gap and never overrides guards or dodges. */
  private kaizenSpinInRange(from: THREE.Vector3, now: THREE.Vector3, d: Entity,
                            radius: number, maxHeight: number): boolean {
    if (Math.abs(d.root.position.y - now.y) > maxHeight) return false;
    const movement = now.clone().sub(from).setY(0);
    const distance = movement.length();
    // Bound the swept path to natural walking between consecutive spin beats.
    const start = from.clone().setY(0);
    if (distance > 0.9) start.addScaledVector(movement, (distance - 0.9) / distance);
    const segment = now.clone().setY(0).sub(start);
    const target = d.root.position.clone().setY(0);
    const delta = target.clone().sub(start);
    const lengthSq = segment.lengthSq();
    const t = lengthSq > 0.00001
      ? THREE.MathUtils.clamp(delta.dot(segment) / lengthSq, 0, 1) : 1;
    const closest = start.addScaledVector(segment, t);
    return target.distanceTo(closest) <= radius + d.radius;
  }

'''
    src = once(src,
        '  /** KAIZEN_CHAINBLADE_V1: three independent, interruptible chain swipes. */\n',
        helper + '  /** KAIZEN_CHAINBLADE_V1: three independent, interruptible chain swipes. */\n',
        'swept spin collider helper')

    # Razor Cyclone: the original nine timed beats, damage and clashes are untouched.
    old = '''  private chainRazorCyclone(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    for (let i = 0; i < 9; i++) this.laterCombo(f, i * 0.18, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      if (i >= 4 && f.intent.skillHeld !== "z") return;
      const reach = 1.65 + Math.min(i, 8) * 0.10;
      const hit = { ...a, dmg: i >= 4 ? 22 : 28, guard: 8, stun: 0.10, heavy: false } as Attack;
      this.fxp("ring", f.root.position.clone().add(new THREE.Vector3(0, 1.1, 0)), "#ff5d78", reach, 0.10, 0.6);
      for (const d of this.enemiesOf(f)) {
        const diff = d.root.position.clone().sub(f.root.position).setY(0);
        if (diff.length() > reach + d.radius || Math.abs(d.root.position.y - f.root.position.y) > 1.9) continue;
        // Real opposing active attacks still create the standard weapon clash.
        if (d instanceof Fighter && this.isDuel() && d.state === S.ATTACK && d.atk?.type === "melee" && d.atkPhase === 1) {
          this.clash(f, d, f.chest()); return;
        }
        this.applyHit(f, d, hit, f.atkPower, d.chest(), diff.normalize(), false);
      }
    });
  }
'''
    new = '''  private chainRazorCyclone(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    let previousCenter = f.root.position.clone();
    for (let i = 0; i < 9; i++) this.laterCombo(f, i * 0.18, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      if (i >= 4 && f.intent.skillHeld !== "z") return;
      const center = f.root.position.clone();
      const from = previousCenter;
      previousCenter = center.clone();
      const reach = 1.65 + Math.min(i, 8) * 0.10;
      const hit = { ...a, dmg: i >= 4 ? 22 : 28, guard: 8, stun: 0.10, heavy: false } as Attack;
      this.fxp("ring", center.clone().add(new THREE.Vector3(0, 1.1, 0)), "#ff5d78", reach, 0.10, 0.6);
      for (const d of this.enemiesOf(f)) {
        if (!this.kaizenSpinInRange(from, center, d, reach, 1.9)) continue;
        const diff = d.root.position.clone().sub(center).setY(0);
        // Real opposing active attacks still create the standard weapon clash.
        if (d instanceof Fighter && this.isDuel() && d.state === S.ATTACK && d.atk?.type === "melee" && d.atkPhase === 1) {
          this.clash(f, d, f.chest()); return;
        }
        const direction = diff.lengthSq() > 0.00001 ? diff.normalize() :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        this.applyHit(f, d, hit, f.atkPower, d.chest(), direction, false);
      }
    });
  }
'''
    src = once(src, old, new, 'Razor Cyclone V8 hit pulses')

    # Death Spiral: keep the original radii, per-beat damage and final overhead hit.
    src = once(src,
        '  private chainDeathSpiral(f: Fighter, a: Attack) {\n    const round = this.round, serial = f.swingSerial;\n',
        '  private chainDeathSpiral(f: Fighter, a: Attack) {\n    const round = this.round, serial = f.swingSerial;\n    let previousCenter = f.root.position.clone();\n',
        'Death Spiral moving sweep tracker')
    src = once(src,
        '      const origin = f.root.position.clone(); // spinning field follows Kaizen\n      const radius = Math.max(1.7, 4.2 - i * 0.40);\n',
        '      const origin = f.root.position.clone(); // spinning field follows Kaizen\n      const from = previousCenter;\n      previousCenter = origin.clone();\n      const radius = Math.max(1.7, 4.2 - i * 0.40);\n',
        'Death Spiral center tracking')
    src = once(src,
        '''        const diff = d.root.position.clone().sub(origin).setY(0);
        if (diff.length() > radius + d.radius || Math.abs(d.root.position.y - f.root.position.y) > 1.9) continue;
        this.applyHit(f, d, { ...a, dmg: 38, guard: 11, stun: 0.13, knock: 0, heavy: false }, f.atkPower, d.chest(), diff.normalize(), false);
''',
        '''        if (!this.kaizenSpinInRange(from, origin, d, radius, 1.9)) continue;
        const diff = d.root.position.clone().sub(origin).setY(0);
        const direction = diff.lengthSq() > 0.00001 ? diff.normalize() :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        this.applyHit(f, d, { ...a, dmg: 38, guard: 11, stun: 0.13, knock: 0, heavy: false }, f.atkPower, d.chest(), direction, false);
''',
        'Death Spiral seven pulses')
    src = once(src,
        '      const origin = f.root.position.clone(); // finisher follows Kaizen\n      this.fxp("slashes", origin.clone().add(new THREE.Vector3(0, 1.9, 0)), "#ffbbc2");\n',
        '      const origin = f.root.position.clone(); // finisher follows Kaizen\n      const from = previousCenter;\n      previousCenter = origin.clone();\n      this.fxp("slashes", origin.clone().add(new THREE.Vector3(0, 1.9, 0)), "#ffbbc2");\n',
        'Death Spiral finisher tracking')
    src = once(src,
        '''        const diff = d.root.position.clone().sub(origin).setY(0);
        if (diff.length() > 2.0 + d.radius || Math.abs(d.root.position.y - f.root.position.y) > 2.2) continue;
        this.applyHit(f, d, { ...a, dmg: 135, guard: 37, knock: 5.3, stun: 0.55, heavy: true }, f.atkPower, d.chest(), diff.normalize(), false);
''',
        '''        if (!this.kaizenSpinInRange(from, origin, d, 2.0, 2.2)) continue;
        const diff = d.root.position.clone().sub(origin).setY(0);
        const direction = diff.lengthSq() > 0.00001 ? diff.normalize() :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        this.applyHit(f, d, { ...a, dmg: 135, guard: 37, knock: 5.3, stun: 0.55, heavy: true }, f.atkPower, d.chest(), direction, false);
''',
        'Death Spiral final overhead')
    return '// ' + TAG + '\n' + src


def run() -> int:
    parser = argparse.ArgumentParser(description='Fix Kaizen spinning skill hit consistency and CPU Z hold')
    parser.add_argument('--check', action='store_true', help='Check patch compatibility without writing')
    options = parser.parse_args()
    root = root_from_here(Path.cwd())
    ai_file = root / 'src/game/ai.ts'
    game_file = root / 'src/game/game.ts'
    ai = ai_file.read_text(encoding='utf-8')
    game = game_file.read_text(encoding='utf-8')
    if TAG in ai and TAG in game:
        print('[OK] Kaizen Spin Hit Reliability V9 is already installed; no changes needed.')
        return 0
    if 'FIGHT_ROYALE_GARRICK_BOB_KAIZEN_ROOK_V8' not in game and \
       'const origin = f.root.position.clone(); // spinning field follows Kaizen' not in game:
        raise PatchError('Mobile Kaizen V8 not found. Install the V8 Fixed updater first.')
    patched_ai = patch_ai(ai)
    patched_game = patch_game(game)
    if options.check:
        print('[OK] Both source files are compatible; no changes made.')
        return 0
    # Backups live outside the project: earlier inside-project backup folders
    # accidentally got included in the Next.js/TypeScript deployment.
    backup_root = Path.home() / 'FightRoyale_Patch_Backups' / f'Kaizen_Spin_V9_{datetime.now():%Y%m%d_%H%M%S}'
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ai_file, backup_root / 'ai.ts')
    shutil.copy2(game_file, backup_root / 'game.ts')
    for path, content in ((ai_file, patched_ai), (game_file, patched_game)):
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         delete=False, dir=str(path.parent), suffix='.tmp') as f:
            f.write(content)
            temp_path = Path(f.name)
        temp_path.replace(path)
    print('[DONE] Kaizen spin hit reliability V9 installed.')
    print('  Updated: src/game/ai.ts, src/game/game.ts')
    print(f'  Backups (outside repository): {backup_root}')
    print('  Run: npx tsc --noEmit -p .  then  npm run dev')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except (PatchError, OSError) as exc:
        print(f'[ERROR] {exc}')
        sys.exit(1)
