#!/usr/bin/env python3
"""Zenith V10.1 — Phantom Fang visual-only upgrade.

Five short, silver-blue spear afterimages synchronized with the existing V9
fifth-basic hit checks. Exact damage/timing/AI/weapon rules are untouched.
Run from Fight Royale web/ after Zenith V9 or V10.

Safe installation: strict preflight, timestamped .bak files, temporary-file
atomic replaces, best-effort rollback, idempotent marker.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import os
import shutil
import sys
import tempfile

ROOT = Path.cwd()
GAME = 'src/game/game.ts'
FX = 'src/game/fx.ts'
FILES = (GAME, FX)
MARK = 'ZENITH_PHANTOM_FANG_VISUAL_V10_1_20261108'

try:
    originals = {p: (ROOT / p).read_text(encoding='utf-8') for p in FILES}
except OSError as exc:
    sys.exit(f'ERROR: Run in your Fight Royale web/ folder: {exc}. No files changed.')

if MARK in originals[GAME] and MARK in originals[FX]:
    print('Zenith Phantom Fang V10.1 is already installed. No changes made.')
    sys.exit(0)
if MARK in originals[GAME] or MARK in originals[FX]:
    sys.exit('PREFLIGHT ERROR: Partial V10.1 installation detected. No changes made; restore backed-up game.ts and fx.ts before retrying.')
if 'ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108' not in originals[GAME] or 'private zenithPhantomFang(' not in originals[GAME]:
    sys.exit('PREFLIGHT ERROR: Phantom Fang V9 code was not found in game.ts. Install V9 first. No changes made.')
if 'export class Fx {' not in originals[FX]:
    sys.exit('PREFLIGHT ERROR: Expected Three.js FX class not found. No changes made.')

patched = dict(originals)

def replace_once(path: str, old: str, new: str):
    occurrences = patched[path].count(old)
    if occurrences != 1:
        raise ValueError(f'{path}: expected ONE matching anchor, found {occurrences}: {old[:140]!r}')
    patched[path] = patched[path].replace(old, new, 1)

try:
    # Add a dedicated event that is naturally replicated to spectators/online clients.
    replace_once(GAME,
        '      case "motes": fx.motes(v3(a[0]), a[1], a[2]); break;',
        '''      // ZENITH_PHANTOM_FANG_VISUAL_V10_1_20261108: synchronized flurry afterimages.
      case "zenithFang": fx.zenithFang(v3(a[0]), v3(a[1]), a[2] ?? 0); break;
      case "motes": fx.motes(v3(a[0]), a[1], a[2]); break;''')

    # Replace ONLY the two V9 effect/sound lines after the actual collision check.
    # No changes to this.melee, attack windows, split damage, stuns, or hitboxes.
    replace_once(GAME,
        '''      this.fxp("sparks", tip, "#bddce9", i === 4 ? 4 : 2, 1.7);
      if (i === 0 || i === 4) this.snd("metal_swish", i === 4 ? 0.43 : 0.30);''',
        '''      // V10.1: five slender overlapping silver-blue spear projections;
      // unlike a generic spark, they show the direction and speed of each thrust.
      // These are COSMETIC, do not spawn projectiles, and have zero collision.
      const forward = f.stage
        ? new THREE.Vector3(f.facing || 1, 0, 0)
        : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
      const side = new THREE.Vector3(-forward.z, 0, forward.x);
      const chest = f.chest();
      const offset = (i - 2) * 0.055;
      const from = chest.clone().addScaledVector(forward, 0.20)
        .addScaledVector(side, offset).add(new THREE.Vector3(0, -0.075, 0));
      const end = from.clone().addScaledVector(forward, i === 4 ? 1.65 : 1.36)
        .add(new THREE.Vector3(0, i === 4 ? 0.06 : (i % 2 ? 0.045 : -0.02), 0));
      this.fxp("zenithFang", from, end, i);
      if (i === 0) this.fxp("num", chest.clone().add(new THREE.Vector3(0, 0.76, 0)),
        "PHANTOM FANG", "#b3e8f7", 0.63);
      if (i === 4) {
        this.fxp("flash", end, "#dcf7ff", 0.24, 0.10, 0.68);
        this.fxp("sparks", tip, "#bfdfe9", 5, 2.2);
      }
      if (i === 0 || i === 4) this.snd("metal_swish", i === 4 ? 0.43 : 0.30);''')

    # Shared geometry with self-expiring per-pulse materials; avoid large explosions.
    replace_once(FX,
        '''const MOTE = new THREE.OctahedronGeometry(0.03, 0);''',
        '''// ZENITH_PHANTOM_FANG_VISUAL_V10_1_20261108 — narrow shared spear afterimage meshes.
const ZENITH_FANG_SHAFT = new THREE.CylinderGeometry(0.014, 0.023, 1, 6);
const ZENITH_FANG_HEAD = new THREE.ConeGeometry(0.045, 0.20, 5);
const MOTE = new THREE.OctahedronGeometry(0.03, 0);''')

    replace_once(FX,
        '  /** Quick crossing slash streaks (Thousand Cuts). */',
        '''  /** Zenith's Phantom Fang: clean spear silhouettes, not slash explosions.
   * Each burst renders three thin silver-blue ghost lances in world space.
   * The five existing contact frames spawn these independently, overlapping
   * for ~0.16s so a charged combo reads as a rapid spear flurry.
   */
  zenithFang(from: THREE.Vector3, to: THREE.Vector3, beat = 0) {
    const direction = to.clone().sub(from);
    const len = direction.length();
    if (len < 0.05) return;
    const root = new THREE.Group();
    root.position.copy(from).add(to).multiplyScalar(0.5);
    root.quaternion.setFromUnitVectors(UP, direction.divideScalar(len));
    const mats: { material: THREE.MeshBasicMaterial; alpha: number }[] = [];
    const ghost = (color: string, opacity: number) => {
      const material = new THREE.MeshBasicMaterial({
        color, transparent: true, opacity, depthWrite: false,
        blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      });
      mats.push({ material, alpha: opacity });
      return material;
    };
    // Tight lateral offsets create a fast multi-spear silhouette, not a broad fan.
    for (const [n, x, alpha] of [[0, 0, 0.82], [1, -0.084, 0.32], [2, 0.084, 0.32]] as const) {
      const material = ghost(n === 0 ? "#d9f6ff" : "#71b7d4", beat === 4 ? alpha : alpha * 0.82);
      const rod = new THREE.Mesh(ZENITH_FANG_SHAFT, material);
      rod.scale.y = len * 0.86;
      rod.position.set(x, -0.075, 0);
      root.add(rod);
      const head = new THREE.Mesh(ZENITH_FANG_HEAD, material);
      head.position.set(x, len * 0.5 - 0.095, 0);
      root.add(head);
    }
    const duration = beat === 4 ? 0.19 : 0.155;
    let age = 0;
    this.add(root, (dt) => {
      age += dt;
      const remain = Math.max(0, 1 - age / duration);
      for (const { material, alpha } of mats) material.opacity = alpha * remain * remain;
      if (age >= duration) {
        for (const { material } of mats) material.dispose();
        return false;
      }
      return true;
    });
  }

  /** Quick crossing slash streaks (Thousand Cuts). */''')
except ValueError as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')

# Ensure neither file was truncated or unreasonably transformed.
for name in FILES:
    if len(patched[name]) < len(originals[name]):
        sys.exit(f'PREFLIGHT ERROR: {name} would be unexpectedly shortened. No files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backups = {}
written = []
try:
    for name in FILES:
        src = ROOT / name
        backup = src.with_name(src.name + f'.before_zenith_fang_visual_v10_1_{stamp}.bak')
        shutil.copy2(src, backup)
        backups[name] = backup
    for name in FILES:
        target = ROOT / name
        fd, temp_name = tempfile.mkstemp(prefix=f'.{target.name}.zenithfang.', suffix='.tmp', dir=target.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as out:
                out.write(patched[name])
            os.replace(temp_name, target)
            written.append(name)
            print('Updated:', name)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
except OSError as exc:
    for name in written:
        try:
            shutil.copy2(backups[name], ROOT / name)
        except OSError:
            pass
    sys.exit(f'WRITE ERROR: {exc}. Tried restoring changed files from backups.')

print('\nZenith Phantom Fang V10.1 installed: visible five-pulse spear afterimages and a crisp final flash.')
print('Only VFX and first-hit label added. Mechanics, timers, damage, AI, Zarek and other characters unchanged.')
print('No new SFX files required. Run: npx tsc --noEmit -p . && npm run build')
