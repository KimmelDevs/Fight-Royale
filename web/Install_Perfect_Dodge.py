#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale - Perfect Dodge System (standalone, safe Python installer).

Run: python Install_Perfect_Dodge.py
     python Install_Perfect_Dodge.py "C:\\path\\to\\Fight-Royale"
     python Install_Perfect_Dodge.py "C:\\path\\to\\Fight-Royale" --dry-run

Uses the existing double-tap dash. If a genuine enemy hit lands in the first
0.13s of dash invulnerability, trigger ONE Perfect Dodge per dash:
  - no damage (existing dodge invulnerability stays intact)
  - short 0.18s dramatic slow-motion at 27% speed
  - compact cyan/gold VFX and short-lived directional ghost afterimages
  - next successful melee hit within 0.95s deals +15% once (RIPOSTE)
No change to other combat mechanics, character stats, skills, Clash Momentum,
Judgment, projectiles or skill hitboxes. Works for host, offline, player and AI.

Before writing, validates all code locations. Writes source backups into
.clash_backups/ and rolls back on I/O errors. Running twice is safe.
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile

MARKER = 'FIGHT_ROYALE_PERFECT_DODGE_V1_NOV07'
FILES = ('src/game/fighter.ts', 'src/game/game.ts', 'src/game/fx.ts')


def once(source: str, old: str, new: str, reason: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'{reason}: expected one code match but found {count}. No files changed. '
                           'Check that this is your current Fight Royale source.')
    return source.replace(old, new, 1)


def section(source: str, begin: str, end: str, old: str, new: str, reason: str) -> str:
    start = source.find(begin)
    if start < 0 or source.find(begin, start + len(begin)) >= 0:
        raise RuntimeError(f'{reason}: cannot uniquely locate method. No files changed.')
    stop = source.find(end, start + len(begin))
    if stop < 0:
        raise RuntimeError(f'{reason}: cannot locate method ending. No files changed.')
    return source[:start] + once(source[start:stop], old, new, reason) + source[stop:]


def patch_fighter(src: str) -> str:
    if MARKER in src:
        return src
    src = once(src,
        '  invulnT = 0;\n',
        '''  invulnT = 0;
  // PERFECT_DODGE_V1: a real incoming hit must land during the first 0.13s
  // of a dash, not merely while other invulnerability is active.
  perfectDodgeT = 0;
  perfectDodgeUsed = false;
  perfectDodgeCounterT = 0; // one successful melee riposte, expires after 0.95s
''', 'fighter dodge state')
    src = section(src,
        '  update(dt: number) {', '  /** Double-tapped direction:',
        '    this.invulnT = Math.max(this.invulnT - dt, 0);',
        '''    this.invulnT = Math.max(this.invulnT - dt, 0);
    this.perfectDodgeT = Math.max(0, this.perfectDodgeT - dt);
    this.perfectDodgeCounterT = Math.max(0, this.perfectDodgeCounterT - dt);''',
        'fighter dodge timers')
    src = section(src,
        '  private readDash() {', '  private readAttack(dt: number)',
        '    this.invulnT = Math.max(this.invulnT, 0.15); // brief dodge window at the start of the dash',
        '''    this.invulnT = Math.max(this.invulnT, 0.15); // existing dash i-frames
    this.perfectDodgeT = 0.13; // strict timing; not the full dash duration
    this.perfectDodgeUsed = false;''', 'fighter dash perfect window')
    src = section(src,
        '  receiveHit(attacker: Entity | null, a: Attack, power: number): string {',
        '  stagger(d: number)',
        '    if (this.invulnT > 0) return "miss";',
        '''    if (this.invulnT > 0) {
      if (this.perfectDodgeT > 0 && !this.perfectDodgeUsed && this.dashing() &&
          attacker && attacker.team !== this.team && a.dmg > 0) {
        this.perfectDodgeUsed = true; // one trigger even during multi-hit attacks
        this.perfectDodgeT = 0;
        this.perfectDodgeCounterT = 0.95;
        return "perfect_dodge";
      }
      return "miss";
    }''', 'fighter real hit perfect dodge')
    return '// ' + MARKER + '\n' + src


def patch_game(src: str) -> str:
    if MARKER in src:
        return src
    src = section(src,
        '    f.onDash = (x) => {', '    this.scene.add(f.root, f.trail.mesh);',
        '      this.fxp("ring", x.root.position.clone().add(new THREE.Vector3(0, 0.1, 0)), x.look.glow, 1.2, 0.2, 0.7);',
        '''      this.fxp("ring", x.root.position.clone().add(new THREE.Vector3(0, 0.1, 0)), x.look.glow, 1.2, 0.2, 0.7);
      // PERFECT_DODGE_V1: trail the *real* moving fighter with three modest ghosts.
      // Timed host-side and replicated through the normal FX event stream.
      const r = this.round;
      const ghost = () => {
        if (r === this.round && !x.isDown() && x.dashing())
          this.fxp("dodgeGhost", x.root.position.clone(), x.look.glow, x.root.rotation.y);
      };
      ghost();
      this.later(0.07, ghost);
      this.later(0.14, ghost);''', 'dodge afterimage on dash')
    src = section(src,
        '  private runFx(name: string, a: any[]) {', '  add_trauma(x: number)',
        '      case "clashBurst": fx.clashBurst(v3(a[0]), a[1], a[2]); break;',
        '''      case "clashBurst": fx.clashBurst(v3(a[0]), a[1], a[2]); break;
      case "dodgeGhost": fx.dodgeGhost(v3(a[0]), a[1], a[2] ?? 0); break;''',
        'FX replication case')
    src = section(src,
        '  private applyHit(attacker: Entity | null, d: Entity, a: Attack, power: number, hitPos: THREE.Vector3, dir: THREE.Vector3, ranged: boolean): string {',
        '  /** Blood Frenzy lasts',
        '    const result = d.receiveHit(attacker, scaledAttack, power);',
        '''    // A successful perfect dodge grants ONE +15% melee hit during the next 0.95s.
    // Misses, blocks and parries don't consume the riposte; projectiles cannot use it.
    const riposte = attacker instanceof Fighter && attacker.perfectDodgeCounterT > 0 &&
      !ranged && a.type === "melee" && a.dmg > 0;
    const result = d.receiveHit(attacker, scaledAttack, riposte ? power * 1.15 : power);
    if (riposte && attacker instanceof Fighter && ["hit", "crit", "ko"].includes(result)) {
      attacker.perfectDodgeCounterT = 0;
      this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.72, 0)),
        "RIPOSTE +15%", "#aeffff", 0.85);
    }''', 'riposte damage and consumption')
    src = section(src,
        '  private applyHit(attacker: Entity | null, d: Entity, a: Attack, power: number, hitPos: THREE.Vector3, dir: THREE.Vector3, ranged: boolean): string {',
        '  /** Blood Frenzy lasts',
        '''      case "miss":
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "MISS", "#c9d3e6", 0.8);
        break;''',
        '''      case "perfect_dodge": {
        const defender = d as Fighter;
        // No extra i-frames or damage immunity: this was already a legitimate
        // dash-invulnerable hit, with exactly one Perfect Dodge per dash.
        this.fxp("dodgeGhost", defender.root.position.clone(), "#aeffff", defender.root.rotation.y);
        this.fxp("flash", defender.chest(), "#b8faff", 0.18, 0.12, 0.65);
        this.fxp("sparks", defender.chest(), "#b8faff", 8, 2.5);
        this.fxp("num", defender.chest().add(new THREE.Vector3(0, 0.55, 0)),
          "PERFECT DODGE!", "#aef7ff", 1.12);
        this.fxp("num", defender.chest().add(new THREE.Vector3(0, 1.0, 0)),
          "COUNTER READY", "#fff0b3", 0.72);
        this.snd("parry", 0.38);
        this.add_trauma(0.10);
        this.hitStop(0.18, 0.27); // 180 ms of cinematic slow motion
        break;
      }
      case "miss":
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "MISS", "#c9d3e6", 0.8);
        break;''',
        'perfect dodge outcome VFX')
    return '// ' + MARKER + '\n' + src


FX_METHOD = '''  /** PERFECT_DODGE_V1: compact translucent anime silhouette (not a large ring).
   * Three ghosts follow a dash; meshes self-expire after 0.27s. */
  dodgeGhost(pos: THREE.Vector3, color: string, yaw = 0) {
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.32,
      blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const ghost = new THREE.Group();
    ghost.position.copy(pos);
    ghost.rotation.y = yaw;
    const oval = (x: number, y: number, z: number, sx: number, sy: number, sz: number, lean = 0) => {
      const mesh = new THREE.Mesh(SPH, mat);
      mesh.position.set(x, y, z);
      mesh.scale.set(sx, sy, sz);
      mesh.rotation.z = lean;
      ghost.add(mesh);
      return mesh;
    };
    // A human-sized, softly glowing outline; kept narrower than the fighter.
    const chest = oval(0, 1.09, 0, 0.25, 0.51, 0.18);
    (chest as any).ownsMat = true; // shared ghost material disposed just once
    oval(0, 1.78, 0, 0.21, 0.23, 0.19);
    oval(-0.33, 1.13, 0, 0.11, 0.39, 0.11, -0.18);
    oval(0.33, 1.13, 0, 0.11, 0.39, 0.11, 0.18);
    oval(-0.14, 0.43, 0, 0.13, 0.43, 0.13, -0.08);
    oval(0.14, 0.43, 0, 0.13, 0.43, 0.13, 0.08);
    const duration = 0.27;
    let elapsed = 0;
    this.add(ghost, (dt) => {
      elapsed += dt;
      const f = Math.min(1, elapsed / duration);
      mat.opacity = 0.32 * (1 - f) * (1 - f);
      ghost.position.y = pos.y + 0.12 * f;
      return elapsed < duration;
    });
  }

'''


def patch_fx(src: str) -> str:
    if MARKER in src:
        return src
    src = once(src,
        '  sparks(pos: THREE.Vector3, color: string, amount = 20, speed = 7, dir: THREE.Vector3 | null = null) {',
        FX_METHOD + '  sparks(pos: THREE.Vector3, color: string, amount = 20, speed = 7, dir: THREE.Vector3 | null = null) {',
        'FX ghost graphics')
    return '// ' + MARKER + '\n' + src


PATCHES = {FILES[0]: patch_fighter, FILES[1]: patch_game, FILES[2]: patch_fx}


def project_root(value: str | None) -> Path:
    for root in ([Path(value).expanduser()] if value else [Path.cwd(), Path(__file__).resolve().parent]):
        if all((root / f).is_file() for f in FILES):
            return root.resolve()
    if value:
        raise RuntimeError('Select the project root containing src/game/fighter.ts, game.ts and fx.ts.')
    choice = ''
    try:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        choice = filedialog.askdirectory(title='Select Fight Royale project folder (contains src)')
        root.destroy()
    except Exception:
        pass
    if not choice:
        try:
            choice = input('Project root folder: ').strip().strip('"')
        except (EOFError, OSError):
            pass
    if not choice:
        raise RuntimeError('No folder selected.')
    root = Path(choice).expanduser().resolve()
    if not all((root / f).is_file() for f in FILES):
        raise RuntimeError('Selected folder is missing src/game/fighter.ts, game.ts or fx.ts.')
    return root


def write_atomic(path: Path, data: bytes) -> None:
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.perfect_dodge_', delete=False) as output:
            temp = Path(output.name)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()


def install(root: Path, dry_run: bool = False) -> tuple[list[str], Path | None]:
    changes: dict[Path, tuple[bytes, bytes]] = {}
    for relative in FILES:
        path = root / relative
        before = path.read_bytes()
        bom = b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b''
        content = before[len(bom):].decode('utf-8')
        newline = '\r\n' if content.count('\r\n') > content.count('\n') / 2 else '\n'
        normalized = content.replace('\r\n', '\n').replace('\r', '\n')
        changed = PATCHES[relative](normalized)
        after = bom + changed.replace('\n', newline).encode('utf-8')
        if after != before:
            changes[path] = (before, after)
    modified = [str(p.relative_to(root)) for p in changes]
    if dry_run or not changes:
        return modified, None
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_perfect_dodge'
    backup = root / '.clash_backups' / stamp
    for path, (before, _) in changes.items():
        dest = backup / path.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(before)
    written = []
    try:
        for path, (_, after) in changes.items():
            write_atomic(path, after)
            written.append(path)
    except Exception:
        for path in reversed(written):
            write_atomic(path, changes[path][0])
        raise
    return modified, backup


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('project', nargs='?', help='Fight Royale project root')
    ap.add_argument('--dry-run', action='store_true', help='validate patches without editing')
    args = ap.parse_args()
    print('\n=== Fight Royale - Perfect Dodge System ===\n')
    try:
        root = project_root(args.project)
        paths, backup = install(root, args.dry_run)
        if not paths:
            print('Already installed. No changes needed.')
        elif args.dry_run:
            print('Compatible project. Would update:')
            for p in paths:
                print(' -', p)
        else:
            print('Updated:')
            for p in paths:
                print(' -', p)
            print('Backup:', backup)
            print('Perfect Dodge: first 0.13s of dash, 0.18s slow motion, one +15% riposte.')
        print('Existing blocks/parries, Aster Judgment, Ember and Zarek Momentum unchanged.')
        return 0
    except Exception as exc:
        print('ERROR:', exc)
        return 1


if __name__ == '__main__':
    exit_code = main()
    if len(sys.argv) == 1 and sys.stdin.isatty():
        try:
            input('\nPress Enter to close...')
        except EOFError:
            pass
    sys.exit(exit_code)
