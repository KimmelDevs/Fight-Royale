#!/usr/bin/env python3
"""Fight Royale cosmetic Arena Reactions installer.

Python 3.9+, standard library only. Select the project root (the folder with src/game).
Run again safely: repeat installs are detected, not layered.
"""

from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys

TAG = 'FIGHT_ROYALE_ARENA_REACTIONS_V1'

class PatchError(RuntimeError):
    pass


def replace_once(source: str, old: str, new: str, label: str) -> str:
    found = source.count(old)
    if found != 1:
        raise PatchError(f'{label}: expected one compatible insertion point, got {found}. No files updated.')
    return source.replace(old, new, 1)


ARENA_FX = r'''  // ARENA_REACTIONS_V1: entirely cosmetic ground stamps. No physics, damage, or hitboxes.
  // Shared geometry limits allocations; per-mark materials are cleaned up by Fx.add().
  private arenaClock = 0;
  private arenaActive = 0;
  private arenaRecent = new Map<string, number>();

  /** Compact cracks, scorch stains and lightning trails; these are NOT attack indicators. */
  arenaReaction(pos: THREE.Vector3, kind: string, size = 1) {
    if (kind !== "crack" && kind !== "scorch" && kind !== "arc") return;
    if (!Number.isFinite(pos.x) || !Number.isFinite(pos.z) || pos.y > 3.0) return;
    if (Math.hypot(pos.x, pos.z) > 15.5 || this.arenaActive >= 18) return;
    const scale = Math.max(0.28, Math.min(size, 1.15));
    const key = `${kind}:${Math.round(pos.x / 1.35)}:${Math.round(pos.z / 1.35)}`;
    const last = this.arenaRecent.get(key) ?? -999;
    const cooldown = kind === "arc" ? 0.25 : kind === "scorch" ? 0.75 : 0.5;
    if (this.arenaClock - last < cooldown) return;
    this.arenaRecent.set(key, this.arenaClock);
    // Avoid an indefinitely growing lookup table in hour-long survival sessions.
    if (this.arenaRecent.size > 150) this.arenaRecent.clear();

    const root = new THREE.Group();
    root.position.set(pos.x, 0.038, pos.z);
    const materials: THREE.MeshBasicMaterial[] = [];
    const material = (color: string, opacity: number) => {
      const m = new THREE.MeshBasicMaterial({ color, transparent: true, opacity,
        depthWrite: false, side: THREE.DoubleSide, polygonOffset: true,
        polygonOffsetFactor: -2 });
      materials.push(m);
      return m;
    };
    const line = (x1: number, z1: number, x2: number, z2: number,
      thickness: number, depth: number, mat: THREE.MeshBasicMaterial) => {
      const dx = x2 - x1, dz = z2 - z1;
      const mesh = new THREE.Mesh(ARENA_REACTION_STRIP, mat);
      mesh.position.set((x1 + x2) * 0.5, depth, (z1 + z2) * 0.5);
      mesh.rotation.y = Math.atan2(dx, dz);
      mesh.scale.set(thickness, 1, Math.hypot(dx, dz));
      root.add(mesh);
    };
    const flatDisc = (x: number, z: number, rx: number, rz: number, depth: number,
      mat: THREE.MeshBasicMaterial) => {
      const mesh = new THREE.Mesh(ARENA_REACTION_DISC, mat);
      mesh.position.set(x, depth, z);
      mesh.rotation.y = Math.random() * Math.PI;
      mesh.scale.set(rx, 1, rz);
      root.add(mesh);
    };

    let life = 0.45;
    if (kind === "crack") {
      life = 4.0;
      const dark = material("#22282c", 0.85);
      const edge = material("#b6a38c", 0.27);
      // Uneven branching fractures; no large circular shockwave or solid ring.
      const angle0 = Math.random() * Math.PI * 2;
      for (let arm = 0; arm < 5; arm++) {
        let x = 0, z = 0;
        let angle = angle0 + arm * Math.PI * 2 / 5;
        for (let part = 0; part < 3; part++) {
          angle += (Math.random() - 0.5) * 0.50;
          const length = (0.13 + Math.random() * 0.14) * scale;
          const nx = x + Math.sin(angle) * length;
          const nz = z + Math.cos(angle) * length;
          line(x, z, nx, nz, 0.027 * scale, 0.014, edge);
          line(x, z, nx, nz, 0.015 * scale, 0.021, dark);
          x = nx; z = nz;
        }
      }
      // A restrained puff of dirt and a few chips, not a huge ground ring.
      const dustAt = new THREE.Vector3(pos.x, 0.08, pos.z);
      this.burst(dustAt, DROP, dustMat, 5, 1.25, UP, 1.15, 4.2, 0.38, 0.55, false);
      this.burst(dustAt, ROCK, rockMats[0], 4, 2.1, UP, 1.1, 12, 0.42, 0.9, false);
    } else if (kind === "scorch") {
      life = 5.2;
      const outer = material("#3a2824", 0.43);
      const ash = material("#151a1b", 0.31);
      const ember = material("#9b441c", 0.18);
      // Irregular, mostly dark patches that sit under existing damaging fire.
      flatDisc(0, 0, 0.69 * scale, 0.48 * scale, 0.001, outer);
      flatDisc(0.11 * scale, -0.08 * scale, 0.53 * scale, 0.39 * scale, 0.004, ash);
      flatDisc(-0.17 * scale, 0.10 * scale, 0.37 * scale, 0.19 * scale, 0.008, ember);
      for (let i = 0; i < 4; i++) {
        const a = Math.random() * Math.PI * 2;
        const r = (0.35 + Math.random() * 0.36) * scale;
        flatDisc(Math.cos(a) * r, Math.sin(a) * r, 0.09 * scale,
          0.05 * scale, 0.005 + i * 0.001, outer);
      }
    } else {
      life = 0.54;
      const blue = material("#2b8eff", 0.93);
      const white = material("#d6faff", 0.87);
      const rotation = Math.random() * Math.PI * 2;
      for (let arm = 0; arm < 3; arm++) {
        let x = 0, z = 0;
        let a = rotation + arm * Math.PI * 2 / 3;
        for (let part = 0; part < 3; part++) {
          a += (Math.random() - 0.5) * 0.82;
          const length = (0.16 + Math.random() * 0.11) * scale;
          const nx = x + Math.sin(a) * length;
          const nz = z + Math.cos(a) * length;
          line(x, z, nx, nz, 0.057 * scale, 0.012, blue);
          line(x, z, nx, nz, 0.018 * scale, 0.019, white);
          x = nx; z = nz;
        }
      }
    }

    // Mark only the first mesh using each material, so shared materials are freed once.
    const owned = new Set<THREE.Material>();
    root.traverse((obj) => {
      const m = obj as THREE.Mesh;
      if (m.isMesh && !owned.has(m.material as THREE.Material)) {
        (m as any).ownsMat = true;
        owned.add(m.material as THREE.Material);
      }
    });
    this.arenaActive++;
    let elapsed = 0;
    this.add(root, (dt) => {
      elapsed += dt;
      const f = Math.min(1, elapsed / life);
      const opacity = kind === "arc" ? Math.pow(1 - f, 1.8)
        : f < 0.5 ? 1 : (1 - f) * 2;
      for (const m of materials) m.opacity = m.userData.initialOpacity * opacity;
      if (elapsed >= life) this.arenaActive = Math.max(0, this.arenaActive - 1);
      return elapsed < life;
    });
  }

'''
# Preserve the initial opacity for fading; set it at allocation time.
ARENA_FX = ARENA_FX.replace('materials.push(m);', 'm.userData.initialOpacity = opacity;\n      materials.push(m);')


def patch_fx(source: str) -> str:
    source = replace_once(source,
        'const ROCK = new THREE.DodecahedronGeometry(0.07, 0);',
        'const ROCK = new THREE.DodecahedronGeometry(0.07, 0);\n'
        '// ARENA_REACTIONS_V1 shared floor geometry, not attack collision geometry.\n'
        'const ARENA_REACTION_STRIP = new THREE.BoxGeometry(1, 0.008, 1);\n'
        'const ARENA_REACTION_DISC = new THREE.CircleGeometry(1, 22).rotateX(-Math.PI / 2);',
        'shared arena geometry')
    source = replace_once(source,
        '  private lastScreenImpact = -1e9;',
        '  private lastScreenImpact = -1e9;\n'
        '  private arenaClock = 0;\n'
        '  private arenaActive = 0;\n'
        '  private arenaRecent = new Map<string, number>();',
        'arena bookkeeping')
    source = replace_once(source,
        '  update(dt: number, realDt: number, w: number, h: number) {\n    this.items = this.items.filter((u) => u(dt));',
        '  update(dt: number, realDt: number, w: number, h: number) {\n'
        '    this.arenaClock += dt;\n'
        '    this.items = this.items.filter((u) => u(dt));',
        'arena update time')
    source = replace_once(source,
        '    this.screenFlashes = [];\n  }\n\n  private add(obj: THREE.Object3D, u: Updater) {',
        '    this.screenFlashes = [];\n'
        '    this.arenaRecent.clear();\n'
        '    this.arenaActive = 0;\n'
        '  }\n\n  private add(obj: THREE.Object3D, u: Updater) {',
        'arena cleanup')
    arena_methods = ARENA_FX.replace(
        '  private arenaClock = 0;\n  private arenaActive = 0;\n  private arenaRecent = new Map<string, number>();\n\n', '')
    source = replace_once(source,
        '  /** Real-time (not hitstop-scaled) screen flash; throttle multihit spam. */',
        arena_methods + '  /** Real-time (not hitstop-scaled) screen flash; throttle multihit spam. */',
        'arena graphics')
    return '// ' + TAG + '\n' + source


def patch_game(source: str) -> str:
    source = replace_once(source,
        '      case "explosion": fx.explosion(v3(a[0]), a[1], a[2]); break;',
        '''      case "explosion":
        fx.explosion(v3(a[0]), a[1], a[2]);
        // Persistent but small cosmetic scorch; the original damage radius is unchanged.
        fx.arenaReaction(v3(a[0]), "scorch", Math.min(1.1, Math.max(0.4, (a[2] ?? 1) * 0.28)));
        break;''',
        'explosive impact mark')
    source = replace_once(source,
        '      case "rocks": fx.rocks(v3(a[0]), a[1], a[2]); break;',
        '''      case "rocks":
        fx.rocks(v3(a[0]), a[1], a[2]);
        fx.arenaReaction(v3(a[0]), "crack", Math.min(1.1, Math.max(0.55, a[2] ?? 1)));
        break;''',
        'earth ground cracks')
    source = replace_once(source,
        '      case "lightning": fx.lightning(v3(a[0]), a[1]); break;',
        '''      case "lightning":
        fx.lightning(v3(a[0]), a[1]);
        fx.arenaReaction(v3(a[0]), "arc", 0.75);
        break;''',
        'lightning traces')
    source = replace_once(source,
        '      case "emberPatch": this.emberPatchVisual(a[0], v3(a[1]), a[2], a[3]); break;',
        '''      case "emberPatch":
        this.emberPatchVisual(a[0], v3(a[1]), a[2], a[3]);
        fx.arenaReaction(v3(a[1]), "scorch", Math.min(0.85, Math.max(0.4, (a[2] ?? 1) * 0.55)));
        break;''',
        'Ember floor scorch')
    source = replace_once(source,
        '      case "dodgeGhost": fx.dodgeGhost(v3(a[0]), a[1], a[2] ?? 0); break;',
        '      case "dodgeGhost": fx.dodgeGhost(v3(a[0]), a[1], a[2] ?? 0); break;\n'
        '      case "arenaReact": fx.arenaReaction(v3(a[0]), a[1], a[2]); break;',
        'networked arena effect')
    source = replace_once(source,
        '    const big = ["z", "x", "c", "v", "heavy", "l3"].includes(f.atkId);',
        '''    const big = ["z", "x", "c", "v", "heavy", "l3"].includes(f.atkId);
    // Zarek leaves quick traces only on major glaive swings. Works for CPU and players.
    if (f.kit === "glaive" && big && f.root.position.y < 2.1)
      this.fxp("arenaReact", f.root.position.clone(), "arc", 0.68);''',
        'Zarek grounded attacks')
    source = replace_once(source,
        '''        if (a.heavy) this.fxp("ring", hitPos, glow, 1.1, 0.35, 0.9);''',
        '''        if (a.heavy) this.fxp("ring", hitPos, glow, 1.1, 0.35, 0.9);
        // Heavy sword, hammer and kick hits leave small floor fractures, not bigger rings.
        if (!ranged && a.type === "melee" && heavy && d.root.position.y < 1.4)
          this.fxp("arenaReact", d.root.position.clone(), "crack", a.heavy ? 0.72 : 0.48);''',
        'heavy melee floor response')
    return '// ' + TAG + '\n' + source


def select_project_root(argument: str | None) -> Path:
    if argument:
        return Path(argument).expanduser().resolve()
    try:
        import tkinter as tk
        from tkinter import filedialog
        app = tk.Tk()
        app.withdraw()
        app.attributes('-topmost', True)
        chosen = filedialog.askdirectory(title='Select Fight Royale project folder (contains src)')
        app.destroy()
        if chosen:
            return Path(chosen).resolve()
    except (ImportError, Exception):
        pass
    value = input('Fight Royale project folder (contains src): ').strip().strip('"')
    if not value:
        raise PatchError('No project folder selected.')
    return Path(value).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description='Install cosmetic Arena Reactions in Fight Royale.')
    parser.add_argument('folder', nargs='?', help='Project root, containing src/game')
    parser.add_argument('--check', action='store_true', help='Verify compatibility without changing files')
    args = parser.parse_args()
    root = select_project_root(args.folder)
    targets = {
        Path('src/game/fx.ts'): patch_fx,
        Path('src/game/game.ts'): patch_game,
    }
    previous: dict[Path, str] = {}
    modified: dict[Path, str] = {}
    seen = []
    for rel, patch in targets.items():
        file = root / rel
        if not file.is_file():
            raise PatchError(f'File missing: {file}. Select the project root with src/game.')
        old = file.read_text(encoding='utf-8-sig')
        seen.append(TAG in old)
        previous[rel] = old
    if all(seen):
        print('Arena Reactions is already installed. No changes made.')
        return 0
    if any(seen):
        raise PatchError('Partial installation detected. Restore the pair from backup first; no changes made.')
    # In-memory compatibility validation FIRST: never modify half a project.
    for rel, patch in targets.items():
        modified[rel] = patch(previous[rel])
    if args.check:
        print('Compatible. Would update: src/game/fx.ts, src/game/game.ts')
        print('All combat values and character skills are untouched.')
        return 0
    backup = root / '.arena_reactions_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True, exist_ok=False)
    for rel in targets:
        destination = backup / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, destination)
    installed = []
    try:
        for rel, content in modified.items():
            target = root / rel
            temp = target.with_name(target.name + '.arena-installing')
            temp.write_text(content, encoding='utf-8', newline='')
            os.replace(temp, target)
            installed.append(rel)
    except Exception:
        for rel in installed:
            (root / rel).write_text(previous[rel], encoding='utf-8')
        for rel in targets:
            (root / rel).with_name(rel.name + '.arena-installing').unlink(missing_ok=True)
        raise
    print('\nSUCCESS: Arena Reactions installed. Restart your game dev server.')
    print('Features: compact floor cracks, Ember scorch, Zarek electrical traces, dust and debris.')
    print('Game damage, collision hitboxes, skill ranges, character stats and passives: unchanged.')
    print('Updated: ' + ', '.join(str(r) for r in targets))
    print('Backups: ' + str(backup))
    print('Visual effects auto-expire and clear on new rounds. Host events replicate to guests.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (PatchError, OSError, UnicodeError) as exc:
        print('Installation stopped safely: ' + str(exc), file=sys.stderr)
        sys.exit(1)
