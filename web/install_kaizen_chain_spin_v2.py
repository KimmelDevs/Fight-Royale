#!/usr/bin/env python3
"""KAIZEN_CHAIN_SPIN_V2 — a chain-and-blade spinning-weapon choreography update.
Run from the Fight Royale web/ folder AFTER Kaizen V1.
Preflights every patch, makes backups, and preserves all attack balance and other fighters.
"""
from pathlib import Path
from datetime import datetime
import re, sys

root = Path.cwd()
paths = ['src/game/model.ts', 'src/game/fighter.ts', 'src/game/kits.ts', 'src/game/vrm.ts']
if not (root/'package.json').exists():
    sys.exit('Run this in your main web folder (next to package.json).')
old = {p:(root/p).read_text(encoding='utf-8') for p in paths}
if 'KAIZEN_CHAIN_SPIN_V2' in old['src/game/model.ts']:
    print('Kaizen Chain Spin V2 is already installed; no files modified.')
    sys.exit(0)
if 'KAIZEN_CHAINBLADE_V1' not in old['src/game/model.ts'] or 'function chainblade()' not in old['src/game/kits.ts']:
    sys.exit('Kaizen V1 is required. Install Kaizen before V2; no files modified.')
new = dict(old)

def replace(path, before, after, count=1):
    n=new[path].count(before)
    if n != count:
        raise RuntimeError(f'ABORTED (no files changed): {path} — expected {count} matching anchors, found {n}: {before[:65]!r}')
    new[path] = new[path].replace(before,after,count)

replace('src/game/model.ts', '''  /** KAIZEN_CHAINBLADE_V1 — animated linked sword, independent of Garrick's weapon. */
  private chainLinks: THREE.Group[] = [];
  private chainBridges: THREE.Group[] = [];
  private chainLengthBlend = 0;
  chainFuryT = 0;
  chainExtended = false;''', '''  /** KAIZEN_CHAIN_SPIN_V2 — separate flying blade, with links on a curved chain. */
  private chainLinks: THREE.Group[] = [];
  private chainAnchor: THREE.Group | null = null;
  private chainBlade: THREE.Group | null = null;
  private chainGhosts: THREE.Mesh[] = [];
  private chainPoseClock = 0;
  private chainPrevPose = "";
  private chainOrbit = 0;
  chainPose = "idle";
  chainFuryT = 0;
  chainExtended = false;''')

old_section=re.search(r'  /\*\* KAIZEN_CHAINBLADE_V1: metal plates connected into one unfolding blade\. \*/\n.*?(?=  private buildSword\(\) \{)',new['src/game/model.ts'],re.S)
if not old_section: raise RuntimeError('ABORTED: could not identify complete Kaizen V1 weapon implementation')

weapon=r'''  /** KAIZEN_CHAIN_SPIN_V2: a dagger-like tip on a real articulated chain, NOT a segmented rigid sword. */
  private buildChainblade() {
    // Right hand keeps only a short grip; the sharp blade travels freely around Kaizen.
    const handle = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    mesh(handle, cyl(0.037, 0.043, 0.42, 10), this.tn("#24232a"), [0, 0.045, 0]);
    mesh(handle, sphere(0.043, 12), this.tn(this.look.trim), [0, -0.17, 0]);
    mesh(handle, box(0.16, 0.041, 0.065), this.metal(), [0, 0.24, 0]);
    this.chainAnchor = pivot(handle, [0, 0.30, 0]);

    // Twenty-four interlocked steel rings. Each follows a live Bezier curve from hand to blade.
    const chainSteel = this.tn("#8d939f");
    for (let i = 0; i < 24; i++) {
      const link = pivot(this);
      mesh(link, torus(0.025, 0.074), chainSteel, [0, 0, 0],
        [i % 2 === 0 ? 0 : PI / 2, 0, 0], [0.8, 1, 1.2]);
      if (i % 4 === 0) mesh(link, sphere(0.014, 8), this.gem(), [0.038, 0, 0]);
      this.chainLinks.push(link);
    }

    // One heavy, hooked, tapered blade at the end of the chain (Toji-like motion reference).
    this.chainBlade = pivot(this, [-0.65, 0.95, 0.35]);
    mesh(this.chainBlade, cyl(0.027, 0.031, 0.19, 10), this.tn("#29252e"), [0, 0.015, 0]);
    mesh(this.chainBlade, box(0.16, 0.041, 0.07), this.tn(this.look.trim), [0, 0.13, 0]);
    const outline = new THREE.Shape();
    outline.moveTo(-0.064, 0.13);
    outline.lineTo(0.065, 0.13);
    outline.lineTo(0.14, 0.31);
    outline.lineTo(0.092, 0.49);
    outline.lineTo(-0.007, 0.70);  // sharp hook point
    outline.lineTo(-0.022, 0.48);
    outline.lineTo(-0.12, 0.33);
    outline.closePath();
    const bladeGeo = new THREE.ExtrudeGeometry(outline,
      { depth: 0.019, bevelEnabled: true, bevelThickness: 0.004, bevelSize: 0.003, bevelSegments: 1 });
    bladeGeo.translate(0, 0, -0.0095);
    mesh(this.chainBlade, bladeGeo, this.steel());
    mesh(this.chainBlade, box(0.013, 0.29, 0.022), this.glowMat, [-0.045, 0.32, 0.019], [0, 0, -0.10]);
    mesh(this.chainBlade, sphere(0.023, 10), this.gem(), [0, 0.16, 0.03]);
    this.bladeBase = pivot(this.chainBlade, [0, 0.13, 0]);
    this.bladeTip = pivot(this.chainBlade, [-0.008, 0.70, 0]);
    this.castPoint = this.bladeTip; // Existing hit sparks attach to the REAL flying blade.
    this.shieldNode = handle;
    // Deliberately NO gripL: this is a one-handed chain weapon, not a greatsword.

    // Offset echoes show blade travel, not a stationary circular VFX ring.
    for (let i = 0; i < 2; i++) {
      const mat = new THREE.MeshBasicMaterial({ color: i === 0 ? 0xff637b : 0xf7afb4,
        transparent: true, opacity: i === 0 ? 0.27 : 0.13, depthWrite: false, side: THREE.DoubleSide });
      const ghost = new THREE.Mesh(bladeGeo, mat);
      ghost.userData.fill = true;
      ghost.visible = false;
      this.add(ghost);
      this.chainGhosts.push(ghost);
    }
  }

  /** A smooth chain path driven by distinct swing phases; combat and collision stay authoritative. */
  private updateChainblade(dt: number) {
    const blade = this.chainBlade, anchor = this.chainAnchor;
    if (!blade || !anchor || this.chainLinks.length === 0) return;
    this.updateMatrixWorld(true);
    const start = this.worldToLocal(anchor.getWorldPosition(new THREE.Vector3()));
    const pose = this.chainPose;
    if (pose !== this.chainPrevPose) { this.chainPoseClock = 0; this.chainPrevPose = pose; }
    else this.chainPoseClock += dt;
    const t = this.chainPoseClock;
    const isOrbit = pose.startsWith("cbx");
    const isAttack = /^(cb[1-4]_[ws]|cbh_[ws]|cbz_[ws]|cbv_[ws]|cbx(?:[1-3])?_[ws])$/.test(pose);
    const strike = pose.endsWith("_s");
    const winding = pose.endsWith("_w") && isAttack;
    const enraged = this.chainFuryT > 0;
    let target: THREE.Vector3;
    const flat = new THREE.Vector3(start.x - 0.35, Math.max(0.43, start.y - 0.42), start.z + 0.13);

    if (isOrbit) {
      // Toji-style continuous horizontal rotation: the BLADE moves around the fighter,
      // while the chain remains attached to his right hand. Each swipe is an actual hit.
      this.chainOrbit += dt * (strike ? 23 : 12);
      const theta = this.chainOrbit;
      const radius = strike ? 1.87 : 1.16;
      target = new THREE.Vector3(Math.sin(theta) * radius,
        1.15 + Math.sin(theta * 2) * 0.13,
        0.28 + Math.cos(theta) * radius * 0.81);
    } else if (pose.startsWith("cbz") || pose.startsWith("cbv") || pose.startsWith("cbh")) {
      // Coiling preparation -> outward throw -> retracting catch.
      const isHeavy = pose.startsWith("cbh");
      const isRecall = pose.startsWith("cbv");
      const extension = winding ? Math.min(0.54, t * 3.8)
        : Math.min(1, Math.max(0, t / (isRecall ? 0.26 : isHeavy ? 0.30 : 0.23)));
      const thrust = winding ? 0.2 : Math.sin(Math.PI * extension) * (isHeavy ? 2.6 : 2.35);
      target = new THREE.Vector3(start.x + Math.sin(t * 10) * 0.25,
        1.28 + (isHeavy ? 0.15 : 0) + Math.sin(extension * PI) * 0.15,
        start.z + 0.5 + thrust);
    } else if (/^cb[1-4]_[ws]$/.test(pose)) {
      // Alternating clockwise/counter-clockwise slashes with real chain travel.
      const n = Number(pose[2]);
      const dir = n % 2 ? 1 : -1;
      const sweep = Math.min(1, t / 0.23);
      const theta = (n % 2 ? -1.2 : 1.2) + dir * (strike ? sweep * PI * 1.25 : -0.35 + sweep * 0.55);
      const radius = strike ? 1.48 : 0.80;
      target = new THREE.Vector3(start.x + radius * Math.sin(theta),
        1.25 + 0.43 * Math.cos(theta + n * 0.45),
        start.z + 0.36 + radius * 0.68 * Math.cos(theta));
    } else if (enraged || pose === "cbc_s") {
      // Unbound Drive keeps the chain in a controlled protective orbit, not a rigid stick.
      this.chainOrbit += dt * 6;
      target = new THREE.Vector3(start.x + Math.sin(this.chainOrbit) * 0.84,
        1.05 + Math.sin(this.chainOrbit * 1.3) * 0.26,
        start.z + 0.20 + Math.cos(this.chainOrbit) * 0.76);
    } else if (pose === "block") {
      target = start.clone().add(new THREE.Vector3(-0.34, 0.22, 0.31));
    } else {
      target = flat.clone().add(new THREE.Vector3(0.055 * Math.sin(this.t * 2), 0, 0));
    }

    // Spring follow-through smooths transitions between separate animation phases.
    const rate = isAttack ? 24 : 10;
    blade.position.lerp(target, 1 - Math.exp(-rate * dt));
    const end = blade.position.clone();
    const control = start.clone().lerp(end, 0.48).add(new THREE.Vector3(
      Math.sin(this.chainOrbit + 0.5) * (isOrbit ? 0.38 : 0.14),
      isAttack ? 0.08 : -0.20,
      Math.cos(this.chainOrbit) * (isOrbit ? 0.32 : 0.10)));
    const chain = new THREE.QuadraticBezierCurve3(start, control, end);
    const up = new THREE.Vector3(0, 1, 0);
    for (let i = 0; i < this.chainLinks.length; i++) {
      const a = (i + 0.5) / this.chainLinks.length;
      const node = this.chainLinks[i];
      node.position.copy(chain.getPoint(a));
      const tangent = chain.getTangent(a).normalize();
      node.quaternion.setFromUnitVectors(up, tangent);
      node.rotateY((i % 2) * PI / 2);
    }
    const outward = end.clone().sub(chain.getPoint(0.85)).normalize();
    if (outward.lengthSq() > 0.01) {
      const facing = new THREE.Quaternion().setFromUnitVectors(up, outward);
      blade.quaternion.slerp(facing, 1 - Math.exp(-18 * dt));
    }
    // Tapered afterimages track the flying blade, only while the attack is moving.
    let previous: THREE.Object3D = blade;
    for (let i = 0; i < this.chainGhosts.length; i++) {
      const ghost = this.chainGhosts[i];
      ghost.visible = isAttack && (strike || isOrbit);
      const f = 1 - Math.exp(-(i === 0 ? 19 : 12) * dt);
      ghost.position.lerp(previous.position, f);
      ghost.quaternion.slerp(previous.quaternion, f);
      ghost.scale.setScalar(i === 0 ? 0.97 : 0.87);
      previous = ghost;
    }
  }

'''
new['src/game/model.ts']=new['src/game/model.ts'].replace(old_section.group(0),weapon,1)

replace('src/game/model.ts',
    'this.vrmRig.grip = { left: !["mage", "kicks"].includes(this.kit), right: this.kit !== "kicks" };',
    'this.vrmRig.grip = { left: !["mage", "kicks", "chainblade"].includes(this.kit), right: this.kit !== "kicks" };')
replace('src/game/model.ts', 'this.kit === "chainblade" ? 0.22 :', 'this.kit === "chainblade" ? 0.14 :')

# The host and client puppet each drive model blending, so use *exactly* the same pose name.
replace('src/game/fighter.ts',
    '    this.model.chainExtended = this.kit === "chainblade" && (this.chainFuryT > 0 ||',
    '    this.model.chainPose = this.kit === "chainblade" ? this.poseName : "idle";\n    this.model.chainExtended = this.kit === "chainblade" && (this.chainFuryT > 0 ||', count=2)

# Make left arm a balancing arm during every chainblade pose, not a second-hand sword grip.
start = new['src/game/kits.ts'].index('const CHAINBLADE: Record<string, Pose> = {')
end = new['src/game/kits.ts'].index('const TABLES: Record<string, Record<string, Pose>>', start)
block = new['src/game/kits.ts'][start:end]
# Replace only the distinctive V1 poses; keep named animation references and attack data intact.
updated = block
poses = {
'idle': 'P([0.06, -0.12, 0], [-0.03, 0.1, 0], [-0.86, 0.17, -0.16], [0.25, 0, -0.2], [-0.48, -0.3, 0.40], [0.17, 0, 0.08], [-0.19, 0, 0.06], [0.19, 0, -0.06], -0.055)',
'cb1_w': 'P([0.13, -0.68, -0.05], [-0.07, 0.4, 0], [-1.28, -0.75, -0.1], [0.65, 0, -0.35], [-0.44, 0.4, 0.52], [0.12, 0, 0], [-0.34, 0, 0.07], [0.31, 0, -0.06], -0.09)',
'cb1_s': 'P([0.20, 0.58, 0.04], [-0.1, -0.32, 0], [-1.52, 0.8, 0.02], [0.2, 0, 0.65], [-0.5, -0.55, 0.35], [0.12, 0, 0], [-0.42, 0, 0.08], [0.4, 0, -0.08], -0.10)',
'cb2_w': 'P([0.12, 0.65, 0.04], [-0.05, -0.41, 0], [-1.12, 0.98, 0.04], [0.4, 0, 0.4], [-0.4, -0.48, 0.37], [0.16, 0, 0], [-0.37, 0, 0.06], [0.36, 0, -0.06], -0.11)',
'cb2_s': 'P([0.20, -0.65, -0.03], [-0.1, 0.42, 0], [-1.48, -0.9, -0.08], [0.22, 0, -0.6], [-0.54, 0.54, 0.34], [0.18, 0, 0], [-0.42, 0, 0.09], [0.38, 0, -0.07], -0.13)',
'cb3_w': 'P([-0.09, -0.39, 0], [0.04, 0.19, 0], [-1.78, -0.55, -0.12], [0.57, 0, 0.3], [-0.5, 0.28, 0.40], [0.18, 0, 0], [-0.32, 0, 0.07], [0.3, 0, -0.08], -0.10)',
'cb3_s': 'P([0.32, 0.46, 0.06], [-0.12, -0.24, 0], [-0.97, 0.74, 0.01], [0.24, 0, -0.58], [-0.4, -0.42, 0.53], [0.12, 0, 0], [-0.56, 0, 0.1], [0.46, 0, -0.08], -0.15)',
'cb4_w': 'P([0.17, 0.76, 0.06], [-0.05, -0.47, 0], [-1.5, 0.94, 0.05], [0.48, 0, 0.61], [-0.42, -0.52, 0.44], [0.12, 0, 0], [-0.42, 0, 0.08], [0.37, 0, -0.08], -0.12)',
'cb4_s': 'P([0.37, -0.86, -0.06], [-0.15, 0.54, 0], [-1.43, -1.12, -0.05], [0.14, 0, -0.68], [-0.57, 0.51, 0.33], [0.15, 0, 0], [-0.62, 0, 0.10], [0.50, 0, -0.09], -0.16)',
'cbx_w': 'P([0.17, -0.70, 0.02], [0, 0.50, 0], [-1.15, -0.82, -0.10], [0.6, 0, -0.4], [-0.60, 0.12, 0.55], [0.20, 0, 0], [-0.43, 0, 0.08], [0.43, 0, -0.08], -0.14)',
'cbx1_s': 'P([0.31, 1.05, 0.03], [-0.12, -0.52, 0], [-1.47, 1.1, -0.12], [0.18, 0, 0.55], [-0.62, -0.1, 0.40], [0.12, 0, 0], [-0.60, 0, 0.10], [0.45, 0, -0.08], -0.18)',
'cbx2_s': 'P([0.24, -1.0, -0.07], [-0.08, 0.56, 0], [-1.4, -1.15, -0.1], [0.2, 0, -0.52], [-0.52, 0.20, 0.49], [0.18, 0, 0], [-0.53, 0, 0.09], [0.46, 0, -0.08], -0.18)',
'cbx3_s': 'P([0.38, 0.93, 0.08], [-0.14, -0.50, 0], [-1.2, 1.16, 0], [0.12, 0, 0.72], [-0.65, -0.3, 0.42], [0.2, 0, 0], [-0.61, 0, 0.1], [0.51, 0, -0.09], -0.2)',
}
for key, value in poses.items():
    pat=r'(?m)^(  '+re.escape(key)+r': )P\([^\n]+\)(,?)$'
    updated, n = re.subn(pat, lambda m: m.group(1)+value+m.group(2), updated)
    if n != 1: raise RuntimeError(f'ABORTED: pose {key} missing or duplicated')
new['src/game/kits.ts']=new['src/game/kits.ts'][:start]+updated+new['src/game/kits.ts'][end:]

# More agile motion: chain fighter should not walk like Garrick's weighty sword guard.
replace('src/game/vrm.ts', '''  chainblade: { stance: D(9), toeOut: D(9), knee: D(12), drop: 0.035, lean: D(5), chin: D(3), shoulderUp: D(2), elbowOut: D(8),
    hipSway: 0.009, hipRoll: D(0.8), contra: D(0.8), relaxKnee: D(4), headTilt: D(0.5), headYaw: D(4),
    breath: 0.55, armSwing: D(10), walkRoll: D(1.2), walkYaw: D(2.4) },''', '''  chainblade: { stance: D(8), toeOut: D(12), knee: D(14), drop: 0.035, lean: D(8), chin: D(3), shoulderUp: D(1), elbowOut: D(7),
    hipSway: 0.008, hipRoll: D(0.8), contra: D(1.2), relaxKnee: D(6), headTilt: D(0.5), headYaw: D(5),
    breath: 0.65, armSwing: D(14), walkRoll: D(1.3), walkYaw: D(3.0) },''')

stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
for path in paths:
    if old[path] == new[path]: continue
    target=root/path
    backup=target.with_name(target.name+f'.chainspin-v2-backup-{stamp}')
    backup.write_text(old[path],encoding='utf-8')
    target.write_text(new[path],encoding='utf-8')
    print('PATCH',path)
print('\nDONE: Kaizen V2 spinning chained blade installed; Garrick VRM and all combat balance unchanged.')
print('Next: npx tsc --noEmit && npm run dev')
