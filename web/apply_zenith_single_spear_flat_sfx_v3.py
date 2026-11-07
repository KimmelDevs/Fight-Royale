#!/usr/bin/env python3
"""Fight Royale Zenith V3: single-headed spear and flat /sfx/*.mp3 sound paths.

Run inside web/ AFTER apply_zenith_spear_animation_sfx_v2.py.
Zenith-only: does not alter Zarek's glaive or any other character's attacks.
Preflight-before-write, timestamped .bak backups, repeat-run safe.
"""
from pathlib import Path
from datetime import datetime
import shutil
import sys

BASE = Path.cwd()
MODEL = 'src/game/model.ts'
GAME = 'src/game/game.ts'
KITS = 'src/game/kits.ts'
FILES = (MODEL, GAME, KITS)
MARK = 'ZENITH_SINGLE_SPEAR_FLAT_SFX_V3_20261108'

try:
    original = {name: (BASE / name).read_text(encoding='utf-8') for name in FILES}
except OSError as exc:
    sys.exit(f'ERROR: Run inside your Fight Royale web/ folder: {exc}. No changes made.')

if MARK in original[MODEL]:
    print('Zenith V3 already installed. No changes needed.')
    sys.exit(0)
if ('ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108' not in original[KITS]
        or 'private buildZenithSpear()' not in original[MODEL]):
    sys.exit('PREFLIGHT ERROR: Install Zenith spear animation V2 first. No changes made.')

updated = original.copy()

def once(path: str, anchor: str, replacement: str):
    number = updated[path].count(anchor)
    if number != 1:
        raise ValueError(f'{path}: expected one match but found {number}: {anchor[:110]!r}')
    updated[path] = updated[path].replace(anchor, replacement, 1)

def replace_region(path: str, start: str, finish: str, replacement: str):
    s = updated[path]
    if s.count(start) != 1:
        raise ValueError(f'{path}: start anchor count {s.count(start)}: {start!r}')
    a = s.index(start)
    b = s.find(finish, a + len(start))
    if b < 0:
        raise ValueError(f'{path}: missing end anchor {finish!r}')
    updated[path] = s[:a] + replacement + s[b:]

try:
    # Single head ONLY (+Y) and a rounded counterweight on the reverse end (-Y).
    # Built using exactly the same hand pivot and VRM scale as V2, so the
    # existing spear-holding, charging, throw and recall animations still align.
    replace_region(MODEL,
        '  // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — proper compact double-point spear,',
        '  /** The game hides the held metal spear when its projectile is flying. */',
        '''  // ZENITH_SINGLE_SPEAR_FLAT_SFX_V3_20261108 — regular single-head spear.
  // Pointed silver blade only at +Y; rounded butt cap at -Y, NOT a second blade.
  private buildZenithSpear() {
    const spear = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    spear.name = "zenithMagneticSpear";
    spear.scale.setScalar(0.94);
    this.glaivePivot = spear;

    const steel = M.toon("#d9e1eb", { rim: 0.75, shade: METAL_SHADE });
    const navy = this.tn("#25364f");
    const dark = this.tn("#19283d");
    const silver = this.tn("#a9b4c7");
    const gold = this.tn("#caa86e");
    const core = this.tn("#7ccbe6");

    // Slim, straight shaft; tip at +1.29, simple pommel at -0.86.
    mesh(spear, cyl(0.015, 0.016, 1.70, 10), navy);
    mesh(spear, cyl(0.021, 0.021, 0.52, 10), dark, [0, -0.16, 0]);
    for (const y of [-0.38, -0.24, -0.10, 0.04])
      mesh(spear, torus(0.020, 0.027), gold, [0, y, 0], [PI / 2, 0, 0], [1, 0.32, 1]);

    // One leaf-shaped spearhead, broader at the base and a narrow point.
    const outline = new THREE.Shape();
    outline.moveTo(-0.019, 0.80);
    outline.lineTo(-0.056, 0.92);
    outline.lineTo(-0.046, 1.075);
    outline.lineTo(-0.026, 1.17);
    outline.lineTo(0, 1.29);
    outline.lineTo(0.026, 1.17);
    outline.lineTo(0.046, 1.075);
    outline.lineTo(0.056, 0.92);
    outline.lineTo(0.019, 0.80);
    outline.closePath();
    const geo = new THREE.ExtrudeGeometry(outline,
      { depth: 0.012, bevelEnabled: true, bevelThickness: 0.003,
        bevelSize: 0.003, bevelSegments: 1 });
    geo.translate(0, 0, -0.006);
    mesh(spear, geo, steel);
    mesh(spear, cyl(0.028, 0.025, 0.067, 10), silver, [0, 0.825, 0]);
    mesh(spear, cyl(0.025, 0.025, 0.026, 10), gold, [0, 0.885, 0]);
    mesh(spear, box(0.010, 0.175, 0.014), core, [0, 1.04, 0.009]);
    mesh(spear, sphere(0.024, 10), this.gem(), [0, 0.86, 0.008]);

    // Simple blunt butt: capped metal ferrule and small rounded pommel.
    mesh(spear, cyl(0.024, 0.021, 0.105, 10), gold, [0, -0.803, 0]);
    mesh(spear, sphere(0.026, 10), silver, [0, -0.86, 0]);

    this.gripL = pivot(spear, [0, -0.32, 0]);
    this.bladeBase = pivot(spear, [0, 0.82, 0]);
    this.bladeTip = pivot(spear, [0, 1.29, 0]);
    this.shieldNode = spear;
    this.castPoint = this.bladeTip;
  }

''')

    # Convert every emitted spear projectile to the same one-tip silhouette.
    replace_region(GAME,
        '  // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — lean two-bladed spear projectiles.',
        '  if (style === "clusterbomb") {',
        '''  // ZENITH_SINGLE_SPEAR_FLAT_SFX_V3_20261108 — single-head spear projectiles.
  if (style === "zenith_rail" || style === "zenith_heavy" || style === "zenith_construct") {
    const steel = new THREE.MeshLambertMaterial({ color: "#d5e0ed" });
    const navy = new THREE.MeshLambertMaterial({ color: "#273b5a" });
    const gold = new THREE.MeshLambertMaterial({ color: "#c7ac78" });
    const scale = size;
    // The shaft spans the rear (-Z) through the forward spearhead (+Z).
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.017*scale, 0.017*scale,
      1.15*scale, 8), navy);
    rod.rotation.x = Math.PI / 2;
    rod.position.z = -0.10*scale;
    g.add(rod);
    const head = new THREE.Mesh(new THREE.ConeGeometry(0.063*scale,
      0.34*scale, 5), steel);
    head.rotation.x = Math.PI / 2;
    head.position.z = 0.635*scale; // one forward-pointing tip
    g.add(head);
    const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.032*scale,
      0.032*scale, 0.065*scale, 8), gold);
    collar.rotation.x = Math.PI / 2;
    collar.position.z = 0.465*scale;
    g.add(collar);
    const butt = new THREE.Mesh(new THREE.SphereGeometry(0.027*scale, 8, 6), gold);
    butt.position.z = -0.69*scale; // blunt pommel, no rear blade
    g.add(butt);
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.028*scale, 0), glow);
    gem.position.z = 0.405*scale;
    g.add(gem);
    return;
  }
''')

    # Her fourth light-combo move is a spearhead diagonal redirect, not a
    # rear-blade thrust. Preserve combo hit timing/damage and dedicated pose IDs.
    once(KITS,
        '  // Reverse-end thrust: turn wrists over, no giant overhead arc.',
        '  // Fourth thrust: short diagonal spearhead redirect, not a rear-end blade attack.')
    once(KITS,
        '  zn4_w: P([0.08,0.36,0], [0,-0.27,0], [-1.13,0.18,0.11], [0.27,0,0.26], [-1.30,0.24,0.22], [0.22,0,-0.16], [-0.28,0,0.10], [0.30,0,-0.07], -0.09),',
        '  zn4_w: P([0.08,0.26,0], [0,-0.20,0], [-1.21,0.14,-0.05], [0.27,0,0.06], [-1.36,0.16,0.18], [0.22,0,-0.04], [-0.28,0,0.10], [0.30,0,-0.07], -0.09),')
    once(KITS,
        '  zn4_s: P([0.17,-0.31,0.03], [0,0.24,0], [-1.69,-0.21,0.05], [0.06,0,-0.35], [-1.69,-0.27,0.13], [0.10,0,0.22], [-0.54,0,0.11], [0.45,0,-0.08], -0.13),',
        '  zn4_s: P([0.17,-0.20,0.03], [0,0.17,0], [-1.69,-0.16,0.05], [0.06,0,0.05], [-1.69,-0.19,0.13], [0.10,0,-0.04], [-0.54,0,0.11], [0.45,0,-0.08], -0.13),')

    # The game appends '.mp3' to this name and prefixes it with '/sfx/'.
    # Consequently a plain name here always resolves /sfx/<file>.mp3.
    sound_names = {
        'fight/metal_hit_woosh': 'metal_hit_woosh',
        'fight/metal_arrow_fast_hit': 'metal_arrow_fast_hit',
        'fight/metal_arrow_hit': 'metal_arrow_hit',
        'fight/metallic_impact_with_whip': 'metallic_impact_with_whip',
        'fight/dramatic_metal_explosion_impact': 'dramatic_metal_explosion_impact',
        'transitions/metal_swish': 'metal_swish',
        'misc/hi_tech_touch_with_magnet': 'hi_tech_touch_with_magnet',
        'misc/sci_fi_gear_turn': 'sci_fi_gear_turn',
    }
    for old_path, flat_name in sound_names.items():
        occurrences = updated[GAME].count('"' + old_path + '"')
        if occurrences < 1:
            raise ValueError(f'{GAME}: missing sound {old_path!r}')
        updated[GAME] = updated[GAME].replace('"' + old_path + '"', '"' + flat_name + '"')

    # A later installer can identify this version reliably.
    once(KITS,
        '// ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108: compact weapon, dedicated spear poses, exact SFX path mapping.',
        '// ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108: compact weapon, dedicated spear poses, exact SFX path mapping.\n'
        '// ZENITH_SINGLE_SPEAR_FLAT_SFX_V3_20261108: one spearhead, flat /sfx/*.mp3 paths.')
except ValueError as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
try:
    for path in FILES:
        src = BASE / path
        shutil.copy2(src, src.with_name(src.name + f'.before_zenith_v3_{stamp}.bak'))
    for path in FILES:
        (BASE / path).write_text(updated[path], encoding='utf-8')
        print('Updated:', path)
except OSError as exc:
    sys.exit(f'WRITE ERROR: {exc}. Restore .before_zenith_v3_*.bak files if necessary.')

print('\nZenith V3 installed: one forward spearhead; flat /sfx/*.mp3 sound URLs.')
print('Copy the following MP3s directly into web/public/sfx/:')
for mp3 in sorted(sound_names.values()):
    print('  ' + mp3 + '.mp3')
print('Sound files were NOT created by this patch. The files must exist in public/sfx/.')
