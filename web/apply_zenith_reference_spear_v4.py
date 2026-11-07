#!/usr/bin/env python3
"""Zenith V4: reference-inspired single spear and matching skill projectile models.
Run inside Fight Royale/web after Zenith V3 (or V2) is installed.
Updates only model.ts and game.ts. Creates timestamped backups. Safe to rerun.
"""
from pathlib import Path
from datetime import datetime
import shutil, sys

BASE = Path.cwd()
FILES = ['src/game/model.ts', 'src/game/game.ts']
MARK = 'ZENITH_REFERENCE_SPEAR_V4_20261108'

try:
    text = {f: (BASE / f).read_text(encoding='utf-8') for f in FILES}
except OSError as exc:
    sys.exit(f'ERROR: Run this inside your Fight Royale web/ folder: {exc}. No changes made.')

if MARK in text['src/game/model.ts']:
    print('Zenith V4 already installed. No changes needed.')
    sys.exit(0)

if 'buildZenithSpear()' not in text['src/game/model.ts']:
    sys.exit('PREFLIGHT ERROR: Zenith spear setup not found. Install Zenith first. No changes made.')

updated = dict(text)


def replace_region(path: str, candidates, finish: str, replacement: str):
    s = updated[path]
    start = None
    for c in candidates:
        if s.count(c) == 1:
            start = c
            break
    if start is None:
        found = {c: s.count(c) for c in candidates}
        raise ValueError(f'{path}: expected one matching start anchor from candidates, found {found}')
    a = s.index(start)
    b = s.find(finish, a + len(start))
    if b < 0:
        raise ValueError(f'{path}: missing end anchor {finish!r}')
    updated[path] = s[:a] + replacement + s[b:]

try:
    replace_region(
        'src/game/model.ts',
        [
            '  // ZENITH_SINGLE_SPEAR_FLAT_SFX_V3_20261108 — regular single-head spear.\n',
            '  // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — proper compact double-point spear,\n',
        ],
        '  /** The game hides the held metal spear when its projectile is flying. */',
        '''  // ZENITH_REFERENCE_SPEAR_V4_20261108 — ornate single-headed spear inspired by the new reference.
  // Larger leaf spearhead, gold side ornaments, blue crystal core, and a blunt rear pommel.
  private buildZenithSpear() {
    const spear = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    spear.name = "zenithRoyalSpear";
    spear.scale.setScalar(0.96);
    this.glaivePivot = spear;

    const steel = M.toon("#dfe6f0", { rim: 0.78, shade: METAL_SHADE });
    const whiteSteel = this.tn("#eef3fa");
    const navy = this.tn("#263a58");
    const dark = this.tn("#17263a");
    const gold = this.tn("#d4b27b");
    const paleGold = this.tn("#e9d4a5");
    const crystal = this.tn("#67c9ef");
    const gem = this.gem();

    // Shaft
    mesh(spear, cyl(0.0155, 0.0155, 1.78, 10), navy);
    mesh(spear, cyl(0.021, 0.021, 0.56, 10), dark, [0, -0.11, 0]);
    for (const y of [-0.33, -0.17, -0.01, 0.15]) {
      mesh(spear, torus(0.020, 0.027), gold, [0, y, 0], [PI / 2, 0, 0], [1, 0.32, 1]);
    }

    // Front assembly — broad leaf spearhead like the reference image.
    const outline = new THREE.Shape();
    outline.moveTo(-0.020, 0.78);
    outline.lineTo(-0.070, 0.94);
    outline.lineTo(-0.062, 1.10);
    outline.lineTo(-0.030, 1.24);
    outline.lineTo(0, 1.42);
    outline.lineTo(0.030, 1.24);
    outline.lineTo(0.062, 1.10);
    outline.lineTo(0.070, 0.94);
    outline.lineTo(0.020, 0.78);
    outline.closePath();
    const headGeo = new THREE.ExtrudeGeometry(outline, {
      depth: 0.016, bevelEnabled: true, bevelThickness: 0.004,
      bevelSize: 0.004, bevelSegments: 1
    });
    headGeo.translate(0, 0, -0.008);
    mesh(spear, headGeo, steel);
    mesh(spear, box(0.009, 0.46, 0.009), whiteSteel, [0, 1.05, 0.009]);
    mesh(spear, cyl(0.028, 0.026, 0.075, 10), gold, [0, 0.82, 0]);
    mesh(spear, cyl(0.025, 0.025, 0.028, 10), paleGold, [0, 0.89, 0]);

    // Decorative gold side wings near the base of the spearhead.
    for (const side of [-1, 1]) {
      const wing = new THREE.Shape();
      wing.moveTo(side * 0.018, 0.86);
      wing.lineTo(side * 0.13, 0.92);
      wing.lineTo(side * 0.17, 1.02);
      wing.lineTo(side * 0.08, 1.08);
      wing.lineTo(side * 0.028, 1.00);
      wing.closePath();
      const wingGeo = new THREE.ExtrudeGeometry(wing, {
        depth: 0.010, bevelEnabled: true, bevelThickness: 0.002,
        bevelSize: 0.002, bevelSegments: 1
      });
      wingGeo.translate(0, 0, -0.005);
      mesh(spear, wingGeo, gold);
      const wingGem = new THREE.Mesh(new THREE.OctahedronGeometry(0.024, 0), crystal);
      wingGem.position.set(side * 0.108, 0.98, 0.016);
      spear.add(wingGem);
    }

    // Oval gold body detail with inset circles like the reference weapon.
    const bodyPlate = new THREE.Mesh(new THREE.BoxGeometry(0.105, 0.30, 0.028), gold);
    bodyPlate.position.set(0, 0.46, 0);
    bodyPlate.scale.set(1.0, 1.0, 0.8);
    spear.add(bodyPlate);
    for (const y of [0.55, 0.46, 0.37]) {
      const hole = new THREE.Mesh(new THREE.TorusGeometry(0.018, 0.006, 6, 16), dark);
      hole.position.set(0, y, 0.016);
      hole.rotation.x = Math.PI / 2;
      spear.add(hole);
    }
    mesh(spear, sphere(0.024, 10), gem, [0, 0.73, 0.008]);
    mesh(spear, box(0.013, 0.16, 0.016), crystal, [0, 0.98, 0.01]);

    // Rear grip and butt — no blade, only a blunt counterweight.
    mesh(spear, cyl(0.025, 0.022, 0.11, 10), gold, [0, -0.83, 0]);
    mesh(spear, sphere(0.030, 10), paleGold, [0, -0.90, 0]);
    mesh(spear, cone(0.018, 0.055, 8), gold, [0, -0.96, 0], [Math.PI, 0, 0]);

    this.gripL = pivot(spear, [0, -0.34, 0]);
    this.bladeBase = pivot(spear, [0, 0.80, 0]);
    this.bladeTip = pivot(spear, [0, 1.42, 0]);
    this.shieldNode = spear;
    this.castPoint = this.bladeTip;
  }

''')

    replace_region(
        'src/game/game.ts',
        [
            '  // ZENITH_SINGLE_SPEAR_FLAT_SFX_V3_20261108 — single-head spear projectiles.\n',
            '  // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — lean two-bladed spear projectiles.\n',
        ],
        '  if (style === "clusterbomb") {',
        '''  // ZENITH_REFERENCE_SPEAR_V4_20261108 — skill projectiles and constructs match Zenith\'s ornate spear.
  if (style === "zenith_rail" || style === "zenith_heavy" || style === "zenith_construct") {
    const steel = new THREE.MeshLambertMaterial({ color: "#dfe6f0" });
    const whiteSteel = new THREE.MeshLambertMaterial({ color: "#eff4fb" });
    const navy = new THREE.MeshLambertMaterial({ color: "#263a58" });
    const dark = new THREE.MeshLambertMaterial({ color: "#17263a" });
    const gold = new THREE.MeshLambertMaterial({ color: "#d4b27b" });
    const paleGold = new THREE.MeshLambertMaterial({ color: "#e9d4a5" });
    const crystal = new THREE.MeshLambertMaterial({ color: "#67c9ef" });
    const scale = size;

    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.017*scale, 0.017*scale, 1.26*scale, 8), navy);
    shaft.rotation.x = Math.PI / 2;
    shaft.position.z = -0.08 * scale;
    g.add(shaft);
    const grip = new THREE.Mesh(new THREE.CylinderGeometry(0.022*scale, 0.022*scale, 0.34*scale, 8), dark);
    grip.rotation.x = Math.PI / 2;
    grip.position.z = -0.12 * scale;
    g.add(grip);

    // Broad forward spearhead
    const head = new THREE.Mesh(new THREE.ConeGeometry(0.085*scale, 0.44*scale, 5), steel);
    head.rotation.x = Math.PI / 2;
    head.position.z = 0.66 * scale;
    g.add(head);
    const midridge = new THREE.Mesh(new THREE.BoxGeometry(0.010*scale, 0.22*scale, 0.030*scale), whiteSteel);
    midridge.position.z = 0.60 * scale;
    g.add(midridge);
    const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.034*scale, 0.034*scale, 0.08*scale, 8), gold);
    collar.rotation.x = Math.PI / 2;
    collar.position.z = 0.45 * scale;
    g.add(collar);

    for (const side of [-1, 1]) {
      const wing = new THREE.Mesh(new THREE.BoxGeometry(0.16*scale, 0.05*scale, 0.026*scale), gold);
      wing.position.set(side * 0.10*scale, 0, 0.48*scale);
      wing.rotation.z = side * 0.60;
      wing.rotation.y = side * 0.18;
      g.add(wing);
      const wingGem = new THREE.Mesh(new THREE.OctahedronGeometry(0.028*scale, 0), crystal);
      wingGem.position.set(side * 0.12*scale, 0, 0.52*scale);
      g.add(wingGem);
    }

    const bodyPlate = new THREE.Mesh(new THREE.BoxGeometry(0.11*scale, 0.22*scale, 0.032*scale), gold);
    bodyPlate.position.z = 0.16 * scale;
    g.add(bodyPlate);
    for (const z of [0.24, 0.16, 0.08]) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.018*scale, 0.005*scale, 6, 14), dark);
      ring.rotation.x = Math.PI / 2;
      ring.position.z = z * scale;
      g.add(ring);
    }

    const butt = new THREE.Mesh(new THREE.SphereGeometry(0.030*scale, 8, 6), paleGold);
    butt.position.z = -0.73 * scale;
    g.add(butt);
    const spike = new THREE.Mesh(new THREE.ConeGeometry(0.018*scale, 0.06*scale, 6), gold);
    spike.rotation.x = -Math.PI / 2;
    spike.position.z = -0.79 * scale;
    g.add(spike);

    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.030*scale, 0), glow);
    gem.position.z = 0.36 * scale;
    g.add(gem);
    return;
  }
''')
except ValueError as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No changes made.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
try:
    for f in FILES:
        src = BASE / f
        shutil.copy2(src, src.with_name(src.name + f'.before_zenith_v4_{stamp}.bak'))
    for f in FILES:
        (BASE / f).write_text(updated[f], encoding='utf-8')
        print('Updated:', f)
except OSError as exc:
    sys.exit(f'WRITE ERROR: {exc}. Restore .before_zenith_v4_*.bak if necessary.')

print('\nZenith V4 installed: ornate single-headed spear and matching skill projectile models.')
print('Weapon inspiration: broad silver spearhead, gold wing ornaments, blue crystal core, blunt rear pommel.')
