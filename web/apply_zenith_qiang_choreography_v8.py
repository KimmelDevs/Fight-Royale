#!/usr/bin/env python3
"""Zenith V8 — graceful, five-path long-spear choreography (visual-only).

Run from fight-royale/web AFTER Zenith V7 and the V6 repair.
Only edits src/game/model.ts. Leaves old V7 method in place as a fallback but
routes Zenith through a new phase-driven visual motion controller.
Never changes combat values, AI, projectiles, networking, VRM rig or Zarek.
Atomic replace + .bak backup + restore on failure; idempotent marker.
"""
from pathlib import Path
from datetime import datetime
import os
import shutil
import sys

ROOT = Path.cwd()
MODEL = ROOT / 'src/game/model.ts'
KIT = ROOT / 'src/game/kits.ts'
V7 = 'ZENITH_FORWARD_SPEAR_IK_V7_20261108'
MARK = 'ZENITH_QIANG_CHOREOGRAPHY_V8_20261108'

try:
    original = MODEL.read_text('utf-8')
    kits = KIT.read_text('utf-8')
except OSError as exc:
    sys.exit(f'ERROR: Run from the web/ folder containing src/game: {exc}; no files changed.')
if MARK in original:
    print('Zenith V8 choreography is already installed. No files changed.')
    sys.exit(0)
if V7 not in original or 'private updateZenithForwardSpear(dt: number)' not in original:
    sys.exit('PREFLIGHT ERROR: Zenith V7 is required. No files changed.')
if (len(kits.splitlines()) < 900 or
    'const ZENITH: Record<string, Pose> = {' not in kits or
    'const CHAINBLADE: Record<string, Pose> = {' not in kits or
    'export function poses(' not in kits or
    'znt5_s:' not in kits or 'zncatch_w:' not in kits):
    sys.exit('PREFLIGHT ERROR: kits.ts looks damaged or lacks the V5 poses. Run the V6 build repair first. No files changed.')

src = original

def once(anchor: str, replacement: str):
    global src
    n = src.count(anchor)
    if n != 1:
        raise ValueError(f'expected ONE matching anchor, found {n}: {anchor[:110]!r}')
    src = src.replace(anchor, replacement, 1)

TUNABLES = '''// ZENITH_QIANG_CHOREOGRAPHY_V8_20261108 — EDIT THESE CONSTANTS TO TUNE THE VISUAL FEEL.
// These are cosmetic world-space/pose offsets ONLY. No gameplay movement, hitboxes or attack timings.
const ZENITH_V8_MOTION = {
  stanceDepth: 0.045,        // meters of visual knee/hip drop on committed strikes
  stepDistance: 0.082,       // meters of MODEL-only alternating lead-foot weight shift
  lungeStep: 0.19,          // extra MODEL-only drive on the fifth thrust
  windupSeconds: 0.085,     // slow, readable spear retraction/anticipation
  snapSeconds: 0.088,       // rapid tip acceleration when the attack becomes active
  overshootSeconds: 0.052,  // short follow-through past the line
  settleSeconds: 0.14,      // controlled retract / ready position
  poseEntrySeconds: 0.048,  // blend continuity when switching attack keys
  tipArc: 1.0,              // 0=straight shortcut, 1=full rising/sweeping tip curves
  spearFlower: 0.045,       // small circular redirect between attacks (radians)
  idleFigureEight: 0.044,   // subtle idle tip orbit, NOT a spinning staff
  idleBob: 0.022,           // idle tip vertical sway (meters)
  walkCounterSway: 0.065,   // spear tip moves opposite the stepping leg
  leadGripGuard: 0.32,      // lead hand is 32 cm toward the spearhead from rear grip
  leadGripExtension: 0.12,  // slides toward the rear hand while thrusting
  torsoYaw: 0.24,          // torso rotation driving the blow (radians)
  hipYaw: 0.12,            // pelvic follow-through (radians)
  thrustOvershoot: 0.032,  // meters of extra tip drive just after the snap
} as const;

'''

PROPERTIES = '''  // ZENITH_QIANG_CHOREOGRAPHY_V8_20261108 — visual timing (never replicated; reconstructs from pose keys).
  private zenithV8Pose = "";
  private zenithV8PoseAge = 0;
  private zenithV8FromPosition = new THREE.Vector3();
  private zenithV8FromRotation = new THREE.Quaternion();
'''

METHOD = '''  /**
   * Zenith V8 — phase-based, opponent-facing single-head spear choreography.
   * Only the SPEAR MESH, two existing IK grips and MODEL-ONLY procedural bones
   * move here. Fighter root, combat reach, attack windows and network stay untouched.
   * The existing V7 method is kept for recovery/debugging, but is no longer called.
   */
  private updateZenithQiangV8(dt: number) {
    if (!this.glaivePivot || !this.zenithSpearRightGrip) return;
    const cfg = ZENITH_V8_MOTION;
    const spear = this.glaivePivot;
    const pose = this.glaivePose;
    const ageStep = THREE.MathUtils.clamp(dt, 0, 0.09);
    if (pose !== this.zenithV8Pose) {
      this.zenithV8Pose = pose;
      this.zenithV8PoseAge = 0;
      this.zenithV8FromPosition.copy(spear.position);
      this.zenithV8FromRotation.copy(spear.quaternion);
    } else this.zenithV8PoseAge += ageStep;
    const age = this.zenithV8PoseAge;
    const clamp = (n: number) => THREE.MathUtils.clamp(n, 0, 1);
    const smooth = (n: number) => { const u = clamp(n); return u * u * (3 - 2 * u); };
    const snap = (n: number) => { const u = clamp(n); return 1 - Math.pow(1 - u, 4); };
    const L = (a: number, b: number, t: number) => THREE.MathUtils.lerp(a, b, t);
    const vec = (a: readonly number[]) => new THREE.Vector3(a[0], a[1], a[2]);
    const curved = (a: readonly number[], b: readonly number[], c: readonly number[], t: number) => {
      const u = 1 - t;
      return vec(a).multiplyScalar(u * u).addScaledVector(vec(b), 2 * u * t)
        .addScaledVector(vec(c), t * t);
    };

    // Summons deliberately free the hands; twin metal blades take over whenever
    // the main spear is airborne. Existing V5 weapon/catch logic is authoritative.
    const summon = /^znh_[ws]$/.test(pose) || /^znv_[ws]$/.test(pose);
    const held = this.zenithSpearInHand && !summon;
    spear.visible = held;
    const freeLead = /^znc_[ws]$/.test(pose) || /^zncatch_[ws]$/.test(pose);
    this.gripL = held && !freeLead ? this.zenithSpearGrip : null;
    if (this.vrmRig) {
      this.vrmRig.spearGripR = held ? this.zenithSpearRightGrip : null;
      this.vrmRig.gripL = this.gripL;
    }
    if (!held) {
      if (this.zenithSpearGrip) this.zenithSpearGrip.position.y = cfg.leadGripGuard;
      // No spear in hand: let the twin-blade, charge and V pose layers lead.
      this.hips.position.x = 0;
      this.hips.position.z = 0;
      this.hips.rotation.y = 0;
      return;
    }

    // Each tuple describes three distinct TIP DIRECTIONS and a winding/landing
    // offset for the ENTIRE shaft. Directions remain positive-Z: no rear blade.
    // A quadratic Bezier through the middle control makes the arc visible.
    const routes: Record<number, {
      wind: [number,number,number]; middle: [number,number,number]; hit: [number,number,number];
      back: [number,number,number]; arc: [number,number,number]; front: [number,number,number];
      twist: number;
    }> = {
      1: {wind:[-0.13,0.09,1],middle:[-0.045,0.04,1],hit:[0,0.015,1],
          back:[-0.055,0,-0.17],arc:[-0.02,0.005,0.02],front:[0.015,0.00,0.19],twist:-0.75},
      2: {wind:[0.26,-0.32,1],middle:[0.05,-0.01,1],hit:[-0.18,0.27,1],
          back:[0.14,-0.15,-0.12],arc:[0.035,-0.005,0.05],front:[-0.07,0.105,0.12],twist:0.85},
      3: {wind:[-0.38,0.10,1],middle:[0.03,0.18,1],hit:[0.33,0.08,1],
          back:[-0.19,0.045,-0.11],arc:[0.015,0.08,0.08],front:[0.20,0.03,0.09],twist:-1.0},
      4: {wind:[0.32,-0.28,1],middle:[-0.25,-0.31,1],hit:[-0.10,0.30,1],
          back:[0.12,-0.13,-0.15],arc:[-0.155,-0.14,0.04],front:[-0.06,0.12,0.12],twist:0.94},
      5: {wind:[-0.21,0.08,1],middle:[-0.08,0.015,1],hit:[0,0.01,1],
          back:[-0.09,0,-0.22],arc:[-0.04,0.008,0.09],front:[0.0,0.0,0.30],twist:-0.5},
    };

    // Base guard is a two-hand shaft line, not a rotating glaive grip.
    let tip = new THREE.Vector3(0.025, 0.13, 1);
    let offset = new THREE.Vector3(-0.095, 0.03, 0.18);
    let thrust = 0;
    let drive = 0;
    let turn = 0;
    let plant = 0;
    const light = /^zn([1-5])_([ws])$/.exec(pose);
    const isWind = light?.[2] === "w";
    const isHit = light?.[2] === "s";
    if (light) {
      const step = Number(light[1]);
      const path = routes[step];
      const sign = step % 2 === 1 ? 1 : -1; // alternate stepping feet
      if (isWind) {
        // Slow anticipation: pull weapon across and toward the rear hip.
        const a = smooth(age / cfg.windupSeconds);
        tip.lerp(vec(path.wind), a);
        offset.lerp(vec(path.back).add(new THREE.Vector3(-0.095,0.03,0.18)), a);
        const flower = cfg.spearFlower * Math.sin(Math.PI * a);
        tip.x += sign * flower;
        tip.y += flower * 0.7;
        turn = path.twist * cfg.torsoYaw * a * -0.52;
        plant = sign * cfg.stepDistance * a * 0.38;
      } else {
        // Phase 1: fast ease-out snap along a DIFFERENT tip curve for each hit.
        const p = snap(age / cfg.snapSeconds);
        const midDir = vec(path.wind).lerp(vec(path.middle), cfg.tipArc);
        const midPos = vec(path.back).lerp(vec(path.arc), cfg.tipArc);
        tip = curved(path.wind, [midDir.x,midDir.y,midDir.z], path.hit, p);
        const pathPos = curved(path.back, [midPos.x,midPos.y,midPos.z], path.front, p);
        offset.add(pathPos);
        thrust = p;
        // Phase 2: tiny physical overshoot, then damped, poised recovery.
        const o = (age - cfg.snapSeconds) / cfg.overshootSeconds;
        const overshoot = o > 0 && o < 1 ? Math.sin(Math.PI * o) : 0;
        offset.z += cfg.thrustOvershoot * overshoot;
        tip.y += 0.025 * overshoot;
        const settle = smooth((age - cfg.snapSeconds - cfg.overshootSeconds) / cfg.settleSeconds);
        if (settle > 0) {
          tip.lerp(vec(path.hit).lerp(new THREE.Vector3(0.035,0.12,1),0.33), settle);
          offset.z -= (step === 5 ? 0.16 : 0.075) * settle;
        }
        drive = p * (1 - settle * 0.54);
        turn = path.twist * cfg.torsoYaw * drive;
        plant = sign * (cfg.stepDistance + (step === 5 ? cfg.lungeStep : 0)) * drive;
        thrust = p * (1 - settle * 0.85);
      }
    } else if (pose === "idle" || pose === "walk") {
      // Narrow figure-eight; never a full staff spin. Footstep sway opposes stride.
      const t = this.t;
      const calm = 1 - clamp(this.walk);
      tip.x += cfg.idleFigureEight * calm * Math.sin(t * 1.9);
      tip.y += cfg.idleFigureEight * calm * 0.55 * Math.sin(t * 3.8);
      offset.y += cfg.idleBob * calm * Math.sin(t * 1.9);
      tip.x -= Math.sin(this.walkPhase) * cfg.walkCounterSway * clamp(this.walk);
      offset.x -= Math.sin(this.walkPhase) * cfg.walkCounterSway * 0.36 * clamp(this.walk);
    } else if (pose === "block") {
      // Tip angled above the lead shoulder; diagonal shaft sweep on block entry.
      const guardSweep = Math.sin(Math.PI * smooth(age / 0.17));
      // receiveHit() already sets model.recoil on a successful block;
      // use that visual signal rather than adding any gameplay callback.
      const deflect = clamp((this.recoil - 0.10) / 0.60);
      tip.set(-0.30 + guardSweep * 0.17 + deflect * 0.15,0.55 - deflect * 0.09,0.86);
      offset.set(-0.05 + deflect * 0.045,0.16,0.13 - deflect * 0.05);
      turn = -0.09 * guardSweep;
      plant = -0.02;
    } else if (pose === "zncatch_w" || pose === "zncatch_s") {
      // Catch: pull the shaft back toward her shoulder, then absorb recoil.
      const c = smooth(age / (pose === "zncatch_w" ? 0.18 : 0.22));
      tip.set(-0.20 * (1-c),0.42 - 0.25*c,1);
      offset.set(-0.10,0.15 - 0.10*c,0.01 + 0.14*c);
      turn = -0.10*(1-c);
    } else if (pose === "znz_w" || pose === "znz_s") {
      // Javelin draw and release, with the tip always pointing downrange.
      const t = pose.endsWith("_w") ? smooth(age / 0.18) : snap(age / 0.12);
      tip.set(pose.endsWith("_w") ? -0.27 : 0.015,pose.endsWith("_w") ? 0.48 : 0.10,1);
      offset.set(-0.14,pose.endsWith("_w") ? 0.21 : 0.08,pose.endsWith("_w") ? 0.06 - 0.12*t : 0.26*t);
      turn = pose.endsWith("_w") ? -0.10*t : 0.16*t;
      plant = pose.endsWith("_s") ? cfg.stepDistance * t : 0;
    } else if (/^znx_[ws]$/.test(pose)) {
      const u = pose.endsWith("_s") ? snap(age / 0.13) : smooth(age / 0.13);
      tip.set(L(-0.20,0.10,u),L(-0.02,0.12,u),1);
      offset.z += (pose.endsWith("_s") ? 0.12 : -0.09) * u;
      turn = -0.10 + 0.17*u;
    } else if (/^znc_[ws]$/.test(pose)) {
      // The lead hand is free to command magnetic pull/repel.
      tip.set(-0.22,0.19,1);
      offset.set(-0.18,-0.02,0.11);
    } else {
      // Unrecognized utility pose: no unwanted staff spins or aggressive resets.
      tip.set(0.02,0.14,1);
    }

    // Rear-hand drive / lead-hand guide: the left hand physically slides toward
    // the rear grip during a thrust, then naturally returns along the shaft.
    const gripTravel = cfg.leadGripGuard - cfg.leadGripExtension;
    if (this.zenithSpearGrip)
      this.zenithSpearGrip.position.y = cfg.leadGripGuard - gripTravel * thrust;
    if (this.zenithSpearRightGrip) this.zenithSpearRightGrip.position.y = -0.02;

    // Point the single blade along the evaluated tip path. We deliberately do
    // NOT exponentially slerp to a static aim: path interpolation is phase based.
    tip.normalize();
    const desiredQ = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),tip);
    this.updateMatrixWorld(true);
    const torso = this.worldToLocal(this.torso.getWorldPosition(new THREE.Vector3()));
    const desiredPos = torso.add(offset);
    const entry = smooth(age / cfg.poseEntrySeconds);
    spear.position.copy(this.zenithV8FromPosition).lerp(desiredPos, entry);
    spear.quaternion.copy(this.zenithV8FromRotation).slerp(desiredQ, entry);

    // Whole-body martial transfer: model-only knee drop, side-to-side lead-foot
    // plant, pelvic torque followed by shoulders. NEVER move Fighter.root.
    const kick = Math.abs(plant);
    const sided = Math.sign(plant);
    this.hips.position.x = sided * Math.min(0.055, kick * 0.30);
    this.hips.position.z = kick; // purely animated VRM pelvis, no hitbox movement
    this.hips.position.y -= cfg.stanceDepth * Math.min(1,drive);
    this.hips.rotation.y = turn * cfg.hipYaw / Math.max(0.001,cfg.torsoYaw);
    this.torso.rotation.y += turn;
    this.torso.rotation.x += 0.035 * drive;
    this.head.rotation.y -= turn * 0.20;
    this.leg_l.rotation.x -= (sided > 0 ? 0.28 : -0.11) * Math.min(1,kick / Math.max(0.001,cfg.lungeStep));
    this.leg_r.rotation.x -= (sided < 0 ? 0.28 : -0.11) * Math.min(1,kick / Math.max(0.001,cfg.lungeStep));
  }

'''

try:
    once('const PI = Math.PI;', TUNABLES + 'const PI = Math.PI;')
    once('  private zenithSpearInHand = true;', '  private zenithSpearInHand = true;\n' + PROPERTIES.rstrip('\n'))
    once('  private updateZenithForwardSpear(dt: number) {', METHOD + '  private updateZenithForwardSpear(dt: number) {')
    once('      this.updateZenithForwardSpear(dt);', '      this.updateZenithQiangV8(dt);')
except ValueError as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')

# Structural sanity: protects unrelated fighter definitions if the input is already broken.
if len(src.splitlines()) < len(original.splitlines()) + 160 or 'class FighterModel extends THREE.Group' not in src:
    sys.exit('PREFLIGHT ERROR: Unexpected output structure. No files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = MODEL.with_name(MODEL.name + f'.before_zenith_v8_{stamp}.bak')
tmp = MODEL.with_name(MODEL.name + '.zenith_v8.tmp')
try:
    shutil.copy2(MODEL, backup)
    tmp.write_text(src, encoding='utf-8')
    os.replace(tmp, MODEL)
except OSError as exc:
    try:
        if backup.exists(): shutil.copy2(backup, MODEL)
        if tmp.exists(): tmp.unlink()
    except OSError:
        pass
    sys.exit(f'WRITE ERROR: {exc}; attempted restoration from {backup.name}.')
print('Updated: src/game/model.ts')
print(f'Backup: {backup.name}')
print('Zenith V8 installed. Basic 1 thrust | 2 rising diagonal | 3 horizontal sweep | 4 low-to-high counter | 5 full lunge.')
print('No changes to damage, cooldowns, hitboxes/reach, AI, throw/recall, twin blades, CC shield, network or Zarek.')
print('Tunable values: ZENITH_V8_MOTION near the top of src/game/model.ts.')
print('Validate with: npx tsc --noEmit -p . && npm run build')
