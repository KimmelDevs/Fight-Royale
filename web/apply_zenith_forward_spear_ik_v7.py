#!/usr/bin/env python3
"""Fight Royale — Zenith V7: spear orientation + two-hand shaft grip IK.

Run from the web/ project directory after Zenith V5 and the V6 build repair.
Changes ONLY Zenith-specific logic inside model.ts and VRM's magnetic branch in vrm.ts.
Does not affect Zarek, weapon damage/cooldowns, throw/recall or twin-blade gameplay.
Idempotent, strict preflight, atomic writes with dated backups.
"""
from pathlib import Path
from datetime import datetime
import os
import shutil
import sys

ROOT = Path.cwd()
MARK = 'ZENITH_FORWARD_SPEAR_IK_V7_20261108'
F_MODEL = ROOT / 'src/game/model.ts'
F_VRM = ROOT / 'src/game/vrm.ts'
FILES = [F_MODEL, F_VRM]
try:
    old = {f: f.read_text(encoding='utf-8') for f in FILES}
except OSError as e:
    sys.exit(f'ERROR: Run in your Fight Royale web/ folder: {e}. Nothing changed.')

if MARK in old[F_MODEL]:
    print('Zenith V7 already installed. No changes made.')
    sys.exit(0)

# The faulty initial V6 installer could remove the lower half of kits.ts.
# Do not report a successful V7 when the project is still missing pose exports.
KIT = ROOT / 'src/game/kits.ts'
try:
    kits = KIT.read_text(encoding='utf-8')
except OSError as e:
    sys.exit(f'PREFLIGHT ERROR: kits.ts unavailable: {e}. Nothing changed.')
if (len(kits.splitlines()) < 900 or
    'const CHAINBLADE: Record<string, Pose> = {' not in kits or
    'export function poses(' not in kits or
    'znt5_s:' not in kits or 'zncatch_w:' not in kits):
    sys.exit('PREFLIGHT ERROR: kits.ts is incomplete or missing V5 poses. '
             'Run repair_zenith_v6_kits_build.py first, then run V7 again. Nothing changed.')

if ('ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108' not in old[F_MODEL]
    or 'zenithSpearGrip' not in old[F_MODEL]
    or 'buildZenithTwinBlades()' not in old[F_MODEL]
    or 'magnetic:' not in old[F_VRM]):
    sys.exit('PREFLIGHT ERROR: Zenith V5 / magnetic rig not found. Install V5 first, then repair V6. Nothing changed.')

new = dict(old)

def once(f: Path, anchor: str, replacement: str):
    count = new[f].count(anchor)
    if count != 1:
        raise ValueError(f'{f.relative_to(ROOT)}: expected ONE occurrence, found {count}, of {anchor[:100]!r}')
    new[f] = new[f].replace(anchor, replacement, 1)

try:
    # Important: unlike V6, every replacement is a short EXACT, unique anchor.
    # V5's alternate-weapon mode remains unchanged; only holding geometry changes.
    once(F_MODEL,
         '  private zenithSpearGrip: THREE.Object3D | null = null;',
         '''  // ZENITH_FORWARD_SPEAR_IK_V7_20261108 — root-mounted, target-directed spear.
  private zenithSpearGrip: THREE.Object3D | null = null;
  private zenithSpearRightGrip: THREE.Object3D | null = null;
  private zenithSpearInHand = true;''')
    once(F_MODEL,
         '    const spear = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);\n    spear.name = "zenithRoyalSpear";',
         '''    // The spear is rooted to the fighter, NOT driven by wrist roll.
    // The shaft aims in +Z, and the arms follow its two grip targets.
    const spear = pivot(this, [0, 0.98, 0.23], [PI / 2, 0, 0]);
    spear.name = "zenithRoyalSpear";''')
    once(F_MODEL,
         '''    this.gripL = pivot(spear, [0, -0.34, 0]);
    this.zenithSpearGrip = this.gripL;
    this.buildZenithTwinBlades();''',
         '''    // Rear (right) hand guides from the hip; lead (left) hand sits ~32cm
    // toward the blade. The previous -0.34 target gripped behind the right hand.
    this.zenithSpearRightGrip = pivot(spear, [0, -0.02, 0]);
    this.gripL = pivot(spear, [0, 0.32, 0]);
    this.zenithSpearGrip = this.gripL;
    this.buildZenithTwinBlades();''')
    # V5 never stored the held spear bladeBase/bladeTip; without this, recall
    # restored the visible spear but kept the short-sword hit/cast anchors.
    once(F_MODEL,
         '    this.bladeTip = pivot(spear, [0, 1.42, 0]);\n    this.shieldNode = spear;',
         '    this.bladeTip = pivot(spear, [0, 1.42, 0]);\n'
         '    this.zenithSpearBase = this.bladeBase;\n'
         '    this.zenithSpearTip = this.bladeTip;\n'
         '    this.shieldNode = spear;')
    once(F_MODEL,
         '''  setZenithSpearHeld(held: boolean) {
    if (this.look.element !== "metal") return;
    if (this.glaivePivot) this.glaivePivot.visible = held;''',
         '''  setZenithSpearHeld(held: boolean) {
    if (this.look.element !== "metal") return;
    this.zenithSpearInHand = held;
    if (this.glaivePivot) this.glaivePivot.visible = held;''')
    once(F_MODEL,
         '''      this.vrmRig.gripL = held ? this.zenithSpearGrip : null;
      this.vrmRig.glaive = held;''',
         '''      this.vrmRig.gripL = held ? this.zenithSpearGrip : null;
      this.vrmRig.spearGripR = held ? this.zenithSpearRightGrip : null;
      this.vrmRig.glaive = held;''')
    once(F_MODEL,
         '''      if (!this.glaivePivot?.visible) {
        const left = /znt[24]_/.test(this.glaivePose);''',
         '''      if (!this.zenithSpearInHand) {
        const left = /znt[24]_/.test(this.glaivePose);''')

    # Model update: distinct throw poses, physical spear tip actually points forward.
    # Windup retracts the spear; strike moves both grip points toward the target.
    # The magnetic catch uses its own backward recoil then controlled recovery.
    once(F_MODEL,
         '  blend(pose: Pose, dt: number, speed: number, actionPose = "") {',
         '''  /** Physical spear choreography. Local +Z is the opponent-facing direction.
   * A spear is not a double glaive: keep its FRONT tip downrange and slide the
   * entire shaft through the two spaced grips during thrusts. No gameplay changes.
   */
  private updateZenithForwardSpear(dt: number) {
    if (!this.glaivePivot || !this.zenithSpearRightGrip) return;
    const pose = this.glaivePose;
    // Overhead charged/V summons have their own lifted-arm pose. During the
    // summon the real spear disappears, while the conjured spear still flies.
    const summon = /^znh_[ws]$/.test(pose) || /^znv_[ws]$/.test(pose);
    const held = this.zenithSpearInHand && !summon;
    this.glaivePivot.visible = held;
    this.gripL = held && !/^znc_[ws]$/.test(pose) && !/^zncatch_[ws]$/.test(pose)
      ? this.zenithSpearGrip : null;
    if (this.vrmRig) {
      this.vrmRig.spearGripR = held ? this.zenithSpearRightGrip : null;
      this.vrmRig.gripL = this.gripL;
    }
    if (!held) return; // Twin blades/airborne spear keep their own animations.

    const finish = /^zn[1-5]_s$/.test(pose);
    const prepare = /^zn[1-5]_w$/.test(pose);
    const catching = pose === "zncatch_w" || pose === "zncatch_s";
    // Each strike has its own point-line: straight, rising, angled, low, lunge.
    // None flips the spear tip toward Zenith or presents a rear blade.
    const aim: Record<string, [number, number, number]> = {
      zn1_w: [-0.10, 0.13, 1], zn1_s: [0.01, 0.02, 1],
      zn2_w: [0.17, -0.16, 1], zn2_s: [-0.08, 0.20, 1],
      zn3_w: [-0.18, 0.10, 1], zn3_s: [0.15, 0.07, 1],
      zn4_w: [0.17, 0.13, 1], zn4_s: [-0.11, -0.28, 1],
      zn5_w: [-0.12, 0.19, 1], zn5_s: [0.0, -0.01, 1],
      znz_w: [-0.24, 0.48, 1], znz_s: [0.0, 0.06, 1],
      znx_w: [-0.12, 0.12, 1], znx_s: [0.05, 0.05, 1],
      znc_w: [0.13, 0.18, 1], znc_s: [0.16, 0.12, 1],
      zncatch_w: [-0.26, 0.42, 1], zncatch_s: [0.05, 0.15, 1],
      block: [0.02, 0.26, 1],
    };
    const moving = THREE.MathUtils.clamp(this.walk, 0, 1);
    const [ax, ay, az] = aim[pose] ?? [0.04, 0.12 + 0.13 * moving, 1];
    // Small rhythmic steps, not wide staff spins; root faces the target already.
    const desired = new THREE.Vector3(ax, ay, az).normalize();
    const targetQ = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), desired);
    const rate = catching ? 24 : finish ? 32 : prepare ? 18 : 14;
    const s = 1 - Math.exp(-rate * Math.min(dt, 0.1));
    this.glaivePivot.quaternion.slerp(targetQ, s);

    // Right hand ~waist-high, near body. Left hand 0.32m ahead on shaft.
    // Thrusts translate the FULL weapon along +Z so the tip travels straight.
    this.updateMatrixWorld(true);
    const torso = this.worldToLocal(this.torso.getWorldPosition(new THREE.Vector3()));
    const zShift = finish ? (pose === "zn5_s" ? 0.27 : 0.16)
      : prepare ? -0.10 : pose === "znz_w" ? -0.13 : 0;
    const yShift = pose === "zn4_s" ? -0.12 : pose === "zn2_s" ? 0.07
      : pose === "zncatch_w" ? 0.16 : 0;
    const target = torso.add(new THREE.Vector3(-0.09, 0.035 + yShift, 0.18 + zShift));
    // Catch: the returning mass pushes her shoulder back, then she settles
    // into the two-hand guard instead of snapping the spear sideways.
    if (pose === "zncatch_w") target.z -= 0.16;
    this.glaivePivot.position.lerp(target, s);
  }

  /** Align a procedural arm with a physical shaft grip for fallback bodies.
   * VRM rigs use two-bone IK independently; no staff/glaive wrist tricks.
   */
  private reachZenithGrip(side: "left" | "right", target: THREE.Object3D) {
    const arm = side === "left" ? this.arm_l : this.arm_r;
    const hand = side === "left" ? this.hand_l : this.hand_r;
    this.updateMatrixWorld(true);
    const goal = this.torso.worldToLocal(target.getWorldPosition(new THREE.Vector3()));
    const delta = goal.sub(arm.position);
    if (delta.lengthSq() < 0.0001) return;
    arm.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), delta.normalize());
    hand.rotation.set(0, 0, 0);
  }

  blend(pose: Pose, dt: number, speed: number, actionPose = "") {''')
    once(F_MODEL,
         '''    if (this.glaivePivot) {
      // Attack pose angles are independent of the VRM clip.''',
         '''    if (this.glaivePivot && this.look.element === "metal" && this.zenithSpearRightGrip) {
      this.updateZenithForwardSpear(dt);
    } else if (this.glaivePivot) {
      // Attack pose angles are independent of the VRM clip.''')
    once(F_MODEL,
         '''    if (this.gripL) this.reachGrip();
    this.vrmRig?.update(dt, { t: this.t,''',
         '''    if (this.look.element === "metal" && this.zenithSpearRightGrip &&
        this.zenithSpearInHand && this.glaivePivot?.visible) {
      this.reachZenithGrip("right", this.zenithSpearRightGrip);
      if (this.gripL) this.reachZenithGrip("left", this.gripL);
    } else if (this.gripL) this.reachGrip();
    this.vrmRig?.update(dt, { t: this.t,''')
    once(F_MODEL,
         '''    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = this.kit === "chainblade" ? 0.58 : this.kit === "glaive" ? 0.4 : 1; }''',
         '''    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = this.kit === "chainblade" ? 0.58 : this.kit === "glaive" ? 0.4 : 1; }
    if (this.look.element === "metal") {
      this.vrmRig.spearGripR = this.zenithSpearRightGrip;
    }''')

    # VRM IK: two actual constrained hands. Bypass Zarek's sword hand spring
    # ONLY for magnetic style. Return to standard rig for twin-blade flight.
    once(F_VRM,
         '  gripL: THREE.Object3D | null = null;',
         '''  gripL: THREE.Object3D | null = null;
  // ZENITH_FORWARD_SPEAR_IK_V7_20261108 — physical rear grip for the right hand.
  spearGripR: THREE.Object3D | null = null;''')
    once(F_VRM,
         '''    if (this.gripL || this.restSword) this.heavyBlade(dt, !!m.combat, set, setNow);
    else if (this.hurtW > 0.02) this.handsForward(set);''',
         '''    if (this.style === "magnetic" && this.spearGripR) this.zenithSpearHands(setNow);
    else if (this.gripL || this.restSword) this.heavyBlade(dt, !!m.combat, set, setNow);
    else if (this.hurtW > 0.02) this.handsForward(set);''')
    once(F_VRM,
         '''  /**
   * Heavy two-handed sword: rests diagonally over the right shoulder when not fighting,''',
         '''  /** Zenith V7: drive both real VRM hands to their own places on the spear.
   * Unlike glaive mode, neither wrist is allowed to steer the whole weapon.
   * This runs after natural body motion so the target points are up to date.
   */
  private zenithSpearHands(setNow: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const root = this.j.root;
    if (!this.spearGripR) return;
    root.updateMatrixWorld(true);
    const point = (o: THREE.Object3D) => root.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    this.solveArm("right", point(this.spearGripR), new THREE.Vector3(-0.8, -0.65, -0.40), setNow);
    if (this.gripL)
      this.solveArm("left", point(this.gripL), new THREE.Vector3(0.75, -0.55, -0.30), setNow);
  }

  /**
   * Heavy two-handed sword: rests diagonally over the right shoulder when not fighting,''')

except ValueError as e:
    sys.exit('PREFLIGHT ERROR: ' + str(e) + '. No files changed.')

if len(new[F_MODEL].splitlines()) < 1700 or len(new[F_VRM].splitlines()) < 550:
    sys.exit('PREFLIGHT ERROR: Unexpectedly truncated output. No files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backups = []
try:
    for f in FILES:
        b = f.with_name(f.name + f'.before_zenith_v7_{stamp}.bak')
        shutil.copy2(f, b)
        backups.append(b)
    for f in FILES:
        tmp = f.with_name(f.name + '.zenith_v7.tmp')
        tmp.write_text(new[f], encoding='utf-8')
        os.replace(tmp, f)
        print('Updated:', f.relative_to(ROOT))
except OSError as e:
    for f, b in zip(FILES, backups):
        shutil.copy2(b, f)
    sys.exit(f'WRITE ERROR: {e}; restored original files from backups.')

print('\nZenith V7 installed: spear mounted to character root; both hands target actual spaced grips.')
print('  - Spear tip points toward target (+Z facing), with distinct low/rise/lunge trajectories.')
print('  - VRM two-hand IK and procedural fallback, off-hand release during magnetic commands.')
print('  - Overhead charge and arsenal arm poses preserved (real spear temporarily hidden).')
print('  - Twin blades, physical catch, 2s CC guard, stuns, SFX and Zarek are unchanged.')
print('Run: npx tsc --noEmit -p . && npm run build')
