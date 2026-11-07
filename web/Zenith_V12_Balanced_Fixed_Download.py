#!/usr/bin/env python3
"""Fight Royale Zenith V12 — Sovereign Metal Bloom.

For V10 + V10.1. Fixes the failed V11 approach without requiring V11.
Rebuilt V12: Magnetic Charge C is nerfed to a capped 2.4x basic attack speed
(spear 1x -> 2.4x, dual swords 2x -> 2.4x), without changing its duration,
cooldown, basic damage or guard-damage penalty. Can also upgrade an existing
V12 installation in place without duplicating any V visual/weapon effects.
Creates 17 defensive spears DURING the V windup, arranges main arsenal in two
flower-petal rings, and adds clear twin rail-finisher aiming lines. Only Zenith V and Magnetic Charge's basic speed multiplier are modified;
other systems remain untouched.

Run in the web/ project folder:
    python apply_zenith_sovereign_metal_bloom_v12.py
    npx tsc --noEmit -p .
    npm run build

Strict preflight, repeat-safe, timestamped backups, atomic writes and rollback.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys
import tempfile

ROOT = Path.cwd()
G = 'src/game/game.ts'
K = 'src/game/kits.ts'
FX = 'src/game/fx.ts'
F = 'src/game/fighter.ts'
V12_FILES = (G, K, FX)
FILES = (G, K, FX, F)
MARK = 'ZENITH_SOVEREIGN_METAL_BLOOM_V12_20261108'
try:
    originals = {name: (ROOT / name).read_text(encoding='utf-8') for name in FILES}
except OSError as exc:
    sys.exit(f'ERROR: Run this inside fight-royale/web/: {exc}. No files changed.')

# Original V12 consists of exactly these three marker-bearing files. The
# rebuilt installer supports both new installs and an already-applied V12.
installed = [name for name in V12_FILES if MARK in originals[name]]
if installed and len(installed) != len(V12_FILES):
    sys.exit(f'PREFLIGHT ERROR: Partial original V12 detected in {installed}. No files changed.')
old_v12_installed = len(installed) == len(V12_FILES)
SPEED_MARK = 'ZENITH_MAGNETIC_CHARGE_24X_V12_20261108'
speed_marked = [name for name in (K, F) if SPEED_MARK in originals[name]]
if len(speed_marked) == 1:
    sys.exit(f'PREFLIGHT ERROR: Partial 2.4x C speed patch in {speed_marked}. No files changed.')
speed_nerfed = len(speed_marked) == 2
if old_v12_installed and speed_nerfed:
    print('Zenith V12 with 2.4x Magnetic Charge already installed. No files changed.')
    sys.exit(0)
if not old_v12_installed:
    if ('ZENITH_SOVEREIGN_HUNTRESS_V10_20261108' not in originals[G]
            or 'ZENITH_PHANTOM_FANG_VISUAL_V10_1_20261108' not in originals[G]
            or 'ZENITH_PHANTOM_FANG_VISUAL_V10_1_20261108' not in originals[FX]):
        sys.exit('PREFLIGHT ERROR: Install Zenith V10 and V10.1 first. V11 is NOT required. No files changed.')
    if 'ZENITH_ARSENAL_GUARD_V11_20261108' in originals[G]:
        sys.exit('PREFLIGHT ERROR: V11 is already installed, so bloom would duplicate spears. No files changed.')

patched = originals.copy()

def once(path: str, old: str, new: str):
    hits = patched[path].count(old)
    if hits != 1:
        raise ValueError(f'{path}: expected ONE exact anchor, found {hits}: {old[:130]!r}')
    patched[path] = patched[path].replace(old, new, 1)

try:
    # Full Metal Bloom is installed only if not already installed. This makes
    # the rebuilt V12 safe to apply AFTER the earlier V12 succeeded.
    if not old_v12_installed:
        # 1. Detect the cast while it is STILL IN WINDUP. The old V11 implementation
        # only ran on the swing callback, after the vulnerable 0.55s windup.
        once(G,
             '    for (const f of this.fighters) f.update(dt);',
             '''    for (const f of this.fighters) f.update(dt);
    // Zenith V12: erupt protective spears on the V windup, before onSwing.
    if (this.cfg.role !== "client") this.zenithV12BloomDuringWindup();''')

        # Insert a Zenith-only helper directly before the correctly spaced method
        # signature taken from the actual V10 source. Never replace full methods.
        once(G,
             '  private zenithArsenal(f:Fighter,a:Attack) {',
             '''  // ZENITH_SOVEREIGN_METAL_BLOOM_V12_20261108 — WINDUP protection.
  // Nine inner and eight staggered outer petals; each is an ordinary blockable,
  // dodgeable short-lived projectile, not damage or CC invulnerability.
  private zenithV12Seen = new WeakMap<Fighter, number>();
  private zenithV12BloomDuringWindup() {
    for (const f of this.fighters) {
      if (f.kit !== "glaive" || f.look.element !== "metal" || f.isDown() ||
          f.state !== S.ATTACK || f.atk?.style !== "zenith_arsenal" ||
          f.atkPhase !== 0) continue;
      const serial = f.swingSerial;
      if (this.zenithV12Seen.get(f) === serial) continue;
      this.zenithV12Seen.set(f, serial);
      const round = this.round;
      const pivot = f.chest();
      // One restrained magnetic halo instead of an opaque blast of particles.
      this.fxp("ring", pivot.clone(), "#a6cadb", 0.92, 0.24, 0.40);
      this.fxp("motes", pivot.clone(), "#d1e5ed", 4);
      this.snd("metal_swish", 0.32);
      for (let i = 0; i < 17; i++) {
        const outer = i >= 9;
        const n = outer ? i - 9 : i;
        const count = outer ? 8 : 9;
        const angle = f.root.rotation.y + n * Math.PI * 2 / count + (outer ? Math.PI / 8 : 0);
        const delay = 0.016 + (outer ? 0.105 : 0) + n * 0.007;
        this.later(delay, () => {
          if (round !== this.round || f.isDown() || f.swingSerial !== serial ||
              f.state !== S.ATTACK || f.atk?.style !== "zenith_arsenal") return;
          const original = f.atk;
          const radius = outer ? 1.02 : 0.70;
          const origin = f.chest().add(new THREE.Vector3(
            Math.sin(angle) * radius, outer ? 0.10 : -0.10, Math.cos(angle) * radius));
          const direction = new THREE.Vector3(Math.sin(angle), outer ? 0.09 : 0.04,
            Math.cos(angle)).normalize();
          const petal: Attack = { ...original, id: `zbloom_${serial}_${i}`,
            type: "projectile", style: "zenith_construct", dmg: 6,
            guard: 5, knock: 1.65, stun: 0.12, heavy: false,
            pierce: false, size: 0.46 };
          const spear = this.spawnProjectile(f, f.team, petal, f.atkPower,
            origin, direction.multiplyScalar(18), "zenith_construct", "metal",
            petal.size, "#c6dce9", false, null);
          // A local anti-rush bloom, not 17 long-range homing attacks.
          spear.life = 0.32;
        });
      }
    }
  }

  private zenithArsenal(f:Fighter,a:Attack) {''')

        # 2. Main 12 weapons form two concentric, staggered six-petal rings.
        # This is purely a projectile origin/formation change: preserve the V10
        # split-health-damage and guard budget exactly.
        once(G,
             '    this.fxp("ring",point.clone(),"#a6bcd6",1.34,0.38,0.31);',
             '    this.fxp("ring",point.clone(),"#b7d1df",1.20,0.34,0.28);')
        once(G,
             '    this.fxp("motes",point.clone().add(new THREE.Vector3(0,1,0)),"#b5cbdd",6);',
             '    this.fxp("motes",point.clone().add(new THREE.Vector3(0,1,0)),"#cbdbe5",3);')

        # 3. Twin rail guides: drawn 0.17s before each rail projectile, from two
        # shoulder-spaced points toward the enemy's actual observed position.
        once(G,
             '    for(let i=0;i<14;i++) this.later(0.30+i*0.11,()=>{',
             '''    // Twin slender rail telegraphs show the direction BEFORE the finishers.
    for (let j = 0; j < 2; j++) this.later(0.30 + (12 + j) * 0.11 - 0.17, () => {
      if (round !== this.round || f.isDown() || target.isDown()) return;
      const right = new THREE.Vector3(Math.cos(f.root.rotation.y), 0,
        -Math.sin(f.root.rotation.y));
      const from = f.chest().addScaledVector(right, j === 0 ? -0.36 : 0.36)
        .add(new THREE.Vector3(0, 0.18, 0));
      this.fxp("zenithRailGuide", from, target.chest(), 0.26);
    });
    for(let i=0;i<14;i++) this.later(0.30+i*0.11,()=>{''')
        once(G,
             '      const angle=(i%12)*Math.PI/6+0.18;',
             '''      const bloomLayer = i < 6 ? 0 : 1;
      const angle=(i%6)*Math.PI/3 + (bloomLayer ? Math.PI/6 : 0) + 0.18;
      const radius=bloomLayer ? 4.10 : 3.50;''')
        once(G,
             '''      const origin = finisher ? f.chest().add(new THREE.Vector3(i===12?-0.38:0.38,0.18,0))
        : center.clone().add(new THREE.Vector3(Math.sin(angle)*4.2,1.1,Math.cos(angle)*4.2));''',
             '''      const finisherRight = new THREE.Vector3(Math.cos(f.root.rotation.y), 0,
        -Math.sin(f.root.rotation.y));
      const origin = finisher ? f.chest().addScaledVector(finisherRight,
        i===12 ? -0.36 : 0.36).add(new THREE.Vector3(0,0.18,0))
        : center.clone().add(new THREE.Vector3(Math.sin(angle)*radius,
            1.06 + bloomLayer*0.25,Math.cos(angle)*radius));''')
        # The V10 split budget is left untouched: 12x18 + 2x48, same knock/stun.

        once(G,
             '      case "zenithFang": fx.zenithFang(v3(a[0]), v3(a[1]), a[2] ?? 0); break;',
             '''      // Zenith V12: a clean, fading directional line for the two final rail spears.
      case "zenithRailGuide": fx.zenithRailGuide(v3(a[0]), v3(a[1]), a[2] ?? 0.26); break;
      case "zenithFang": fx.zenithFang(v3(a[0]), v3(a[1]), a[2] ?? 0); break;''')

        # 4. Short, low-overdraw directional guide. It is an FX event replicated to
        # spectators/guests just like the existing V10.1 Phantom Fang silhouettes.
        once(FX,
             '  /** Quick crossing slash streaks (Thousand Cuts). */',
             '''  // ZENITH_SOVEREIGN_METAL_BLOOM_V12_20261108 — clean twin rail aiming lines.
  /** A narrow silver-blue rail line with a traveling dot and forward arrow.
   * Entirely visual: the real projectile and collision remain unchanged.
   */
  zenithRailGuide(from: THREE.Vector3, to: THREE.Vector3, duration = 0.26) {
    const travel = to.clone().sub(from);
    const len = travel.length();
    if (len < 0.10) return;
    const root = new THREE.Group();
    root.position.copy(from).add(to).multiplyScalar(0.5);
    root.quaternion.setFromUnitVectors(UP, travel.normalize());
    const make = (color: string, opacity: number) => new THREE.MeshBasicMaterial({
      color, transparent: true, opacity, depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const hazeMat = make("#6db0d2", 0.23);
    const rayMat = make("#e3f6ff", 0.72);
    const dotMat = make("#f5fcff", 0.72);
    const arrowMat = make("#b0ddeb", 0.57);
    const haze = new THREE.Mesh(new THREE.CylinderGeometry(0.030, 0.030, 1, 6), hazeMat);
    haze.scale.y = len;
    const ray = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.009, 1, 6), rayMat);
    ray.scale.y = len;
    const dot = new THREE.Mesh(SPH, dotMat);
    dot.scale.setScalar(0.045);
    const arrow = new THREE.Mesh(new THREE.ConeGeometry(0.062, 0.17, 6), arrowMat);
    arrow.position.y = len * 0.5 - 0.11;
    root.add(haze, ray, dot, arrow);
    for (const mesh of [haze, ray, dot, arrow]) (mesh as any).ownsMat = true;
    let age = 0;
    const lifetime = Math.max(0.12, Math.min(duration, 0.45));
    this.add(root, (dt) => {
      age += dt;
      const phase = Math.min(1, age / lifetime);
      dot.position.y = (phase - 0.5) * len;
      const fade = (1 - phase) * (1 - phase);
      hazeMat.opacity = 0.23 * fade;
      rayMat.opacity = 0.72 * fade;
      dotMat.opacity = 0.72 * fade;
      arrowMat.opacity = 0.57 * fade;
      return age < lifetime;
    });
  }

  /** Quick crossing slash streaks (Thousand Cuts). */''')

        once(K,
             'desc: "Summon twelve magnetic spears in two waves, then two heavy rail spears. Fourteen weapons total; split damage, dodgeable strikes.",',
             'desc: "17 protective bloom spears erupt during cast; 12 elegant directional spears and 2 guided rail finishers follow.",')
        # The kit marker also makes this version independently verifiable.
        once(K,
             '  // ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108',
             '  // ZENITH_SOVEREIGN_METAL_BLOOM_V12_20261108 — protected V windup; 17+14 spears.\n  // ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108')
    # C buff balance: independent of the V formation so existing V12 owners
    # receive the nerf without re-spawning 17 + 14 extra spear logic.
    if not speed_nerfed:
        once(K,
             '  // C: 20s real-time buff. Spear 3x attack tempo; twin blades 2x normally / 4x buffed.',
             '  // C: 20s real-time buff. Spear 2.4x attack tempo; twin blades 2x normally / 2.4x buffed.')
        once(F,
             '    // V9 real attack speed: short twin-blade basics are 2x at all times,\n'
             '    // 4x with Magnetic Charge. Spear basics are 3x only while charged.',
             '    // V12 attack speed: twin blades 2x normally / 2.4x with Magnetic Charge;\n'
             '    // spear basics 1x normally / 2.4x with Magnetic Charge.')
        once(K,
             'desc: "20s buff: spear basics 3x faster; twin metal blades 4x faster (normally 2x). Basic guard damage -20%. Health damage unchanged.",',
             'desc: "20s buff: spear and twin blade basics 2.4x speed (twin blades normally 2x). Basic guard damage -20%. Health damage unchanged.",')
        once(K,
             '  // ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108',
             '  // ZENITH_MAGNETIC_CHARGE_24X_V12_20261108 — C caps basic speed at 2.4x.\n  // ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108')
        once(F,
             '      const speed = this.zenithSpearOut ? (charged ? 4 : 2) : (charged ? 3 : 1);',
             '      // ZENITH_MAGNETIC_CHARGE_24X_V12_20261108 — effective multiplier vs original speed.\n'
             '      const speed = this.zenithSpearOut ? (charged ? 2.4 : 2) : (charged ? 2.4 : 1);')
except ValueError as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')

if any(patched[f].count(MARK) != 1 for f in V12_FILES):
    sys.exit('PREFLIGHT ERROR: V12 version markers failed consistency check. No files changed.')
if any(patched[f].count(SPEED_MARK) != 1 for f in (K, F)):
    sys.exit('PREFLIGHT ERROR: Magnetic Charge nerf markers failed consistency check. No files changed.')
for f in FILES:
    if len(patched[f].splitlines()) < len(originals[f].splitlines()):
        sys.exit(f'PREFLIGHT ERROR: Suspicious truncation of {f}. No files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
modified = [name for name in FILES if patched[name] != originals[name]]
backups: dict[str, Path] = {}
written: list[str] = []
try:
    for name in modified:
        path = ROOT / name
        backup = path.with_name(path.name + f'.before_zenith_v12_{stamp}.bak')
        shutil.copy2(path, backup)
        backups[name] = backup
    for name in modified:
        target = ROOT / name
        fd, tmp = tempfile.mkstemp(prefix=f'.{target.name}.zenithv12.', suffix='.tmp', dir=target.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as out:
                out.write(patched[name])
            os.replace(tmp, target)
            written.append(name)
            print('Updated:', name)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
except Exception as exc:
    for name in written:
        try: shutil.copy2(backups[name], ROOT / name)
        except OSError: pass
    sys.exit(f'WRITE ERROR: {exc}. Restored files where possible from V12 backups.')

print('\nZenith V12 rebuilt: Metal Bloom + Magnetic Charge basic-speed nerf to 2.4x.')
print('V keeps its V10 14 main spears; main formation is now 2 clean rings of six.')
print('Two thin rail direction guides telegraph the final two spears.')
print('Magnetic Charge C: SPEAR basic 2.4x buffed / 1x normal; TWIN BLADES 2.4x buffed / 2x normal.')
print('C still lasts 20s with 30s cooldown; -20% basic guard damage. Health damage unchanged.')
print('No V11 installation needed. No new MP3 files required.')
print('Verify: npx tsc --noEmit -p . && npm run build')
