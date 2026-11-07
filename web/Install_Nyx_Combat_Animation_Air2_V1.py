#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale: Nyx combat animation overhaul + two aerial dagger attacks.

Run in the Fight Royale web directory:
    python Install_Nyx_Combat_Animation_Air2_V1.py
Or:
    python Install_Nyx_Combat_Animation_Air2_V1.py "C:\\path\\to\\Fight-Royale\\web"

No extra Python modules required. Only Nyx's animations, aerial chain and CPU usage change;
Kira retains three aerial kicks. Creates automatic timestamped source backups.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

VERSION = 'NYX_SHADOW_COMBAT_AIR_2_V1'
FILES = ['src/game/kits.ts', 'src/game/fighter.ts', 'src/game/model.ts', 'src/game/vrm.ts', 'src/game/ai.ts']

class PatchError(RuntimeError):
    pass

def require_one(src: str, old: str, new: str, msg: str) -> str:
    matches = src.count(old)
    if matches != 1:
        raise PatchError(f'{msg}: expected one source anchor, found {matches}')
    return src.replace(old, new, 1)

def section_replace(src: str, a: str, b: str, transform, msg: str) -> str:
    i = src.find(a)
    if i < 0: raise PatchError(f'{msg}: starting anchor not found')
    j = src.find(b, i + len(a))
    if j < 0: raise PatchError(f'{msg}: ending anchor not found')
    original = src[i:j]
    changed = transform(original)
    if changed == original: raise PatchError(f'{msg}: section was not modified')
    return src[:i] + changed + src[j:]

def locate(path: str | None) -> Path:
    base = Path(path).expanduser().resolve() if path else Path.cwd().resolve()
    for root in [base, base / 'web']:
        if all((root / f).is_file() for f in FILES): return root
    raise PatchError('Cannot locate Fight Royale web project. Put this file in web/ or provide web path.')

NYX_POSES = '''// NYX_SHADOW_COMBAT_AIR_2_V1: asymmetrical, knife-forward assassin choreography.
// Changes pose data only; existing ground damage and skill cooldowns are untouched.
const NYX_SHADOW_V1: Record<string, Pose> = {
  idle: P([0.10, -0.38, 0.02], [-0.04, 0.32, -0.03], [-0.95, -0.43, -0.24], [0.70, -0.10, -0.05], [-1.12, 0.40, 0.31], [0.58, 0.09, 0.04], [-0.26, 0.0, 0.12], [0.21, 0.0, -0.12], -0.045),
  block: P([0.12, 0.02, -0.05], [-0.08, -0.02, 0.02], [-1.35, 0.38, -0.36], [1.10, 0, 0.08], [-1.40, -0.35, 0.28], [1.08, 0, -0.10], [-0.36, 0, 0.11], [0.28, 0, -0.10], -0.075),
  jump: P([0.05, -0.18, 0], [0.04, 0.18, 0], [-1.22, -0.50, -0.32], [0.82, 0, 0], [-1.30, 0.51, 0.31], [0.85, 0, 0], [-0.73, 0, 0.10], [-0.55, 0, -0.10], -0.035),
  // Four distinct dagger cuts: right cross, left reverse, forward double stab, crossing finisher.
  as1_w: P([0.12, -0.75, -0.08], [-0.03, 0.55, 0.05], [-0.68, -1.12, -0.23], [1.03, 0.18, -0.06], [-1.11, 0.40, 0.40], [0.80, 0, 0], [-0.32, 0, 0.14], [0.30, 0, -0.12], -0.08),
  as1_s: P([0.24, 0.49, 0.08], [-0.08, -0.32, 0], [-1.41, 1.06, -0.11], [1.30, -0.14, 0], [-1.05, -0.25, 0.38], [0.62, 0, -0.05], [-0.43, 0, 0.13], [0.45, 0, -0.09], -0.095),
  as2_w: P([0.14, 0.65, 0.05], [-0.04, -0.50, 0], [-1.02, -0.18, -0.32], [0.80, 0.02, 0], [-0.60, 1.18, 0.26], [1.08, -0.12, 0.05], [-0.35, 0, 0.12], [0.28, 0, -0.10], -0.07),
  as2_s: P([0.22, -0.52, -0.06], [-0.04, 0.41, 0], [-1.04, 0.33, -0.34], [0.75, 0, 0], [-1.47, -1.04, 0.05], [1.37, 0.08, 0], [-0.40, 0, 0.10], [0.46, 0, -0.13], -0.09),
  as3_w: P([0.05, -0.20, 0], [-0.08, 0.20, 0], [-0.63, -0.45, -0.52], [1.42, 0, 0], [-0.65, 0.52, 0.48], [1.39, 0, 0], [-0.51, 0, 0.14], [0.46, 0, -0.13], -0.095),
  as3_s: P([0.31, 0.08, 0], [-0.06, -0.04, 0], [-1.63, 0.06, -0.18], [1.25, 0, 0], [-1.65, -0.08, 0.18], [1.27, 0, 0], [-0.73, 0, 0.13], [0.62, 0, -0.13], -0.13),
  as4_w: P([-0.02, -0.19, 0.01], [0.03, 0.16, 0], [-0.80, -1.16, -0.30], [1.18, 0, 0], [-0.82, 1.16, 0.30], [1.18, 0, 0], [-0.39, 0, 0.12], [0.29, 0, -0.12], -0.07),
  as4_s: P([0.38, 0.10, 0], [-0.12, -0.11, 0], [-1.59, 0.61, -0.05], [1.45, 0, 0], [-1.60, -0.59, 0.03], [1.46, 0, 0], [-0.67, 0, 0.15], [0.56, 0, -0.15], -0.15),
  // Charged dagger lunge, with the arms gathered before releasing a cross-cut.
  nyx_heavy_w: P([0.12, -0.70, -0.08], [-0.03, 0.53, 0], [-0.50, -1.15, -0.53], [1.02, 0, -0.11], [-0.53, 1.08, 0.48], [1.03, 0, 0.05], [-0.47, 0, 0.13], [0.45, 0, -0.11], -0.11),
  nyx_heavy_s: P([0.35, 0.24, 0], [-0.12, -0.17, 0], [-1.85, 0.43, -0.24], [1.47, 0, 0], [-1.83, -0.43, 0.25], [1.45, 0, 0], [-0.78, 0, 0.12], [0.65, 0, -0.12], -0.16),
  // Smoke Step: dip into the disappearance, spring out of the reappearance.
  nyx_smoke_w: P([0.42, -0.22, 0.08], [-0.24, 0.20, 0], [-0.62, -0.26, -0.53], [0.82, 0, 0], [-0.59, 0.35, 0.43], [0.79, 0, 0], [-0.68, 0, 0.16], [0.59, 0, -0.14], -0.20),
  nyx_smoke_s: P([0.12, 0.37, -0.06], [0.01, -0.27, 0], [-1.26, 0.64, -0.23], [0.78, 0, 0], [-1.21, -0.65, 0.23], [0.75, 0, 0], [-0.36, 0, 0.10], [0.35, 0, -0.09], -0.06),
  // Shuriken Fan: both forearms snap from the ribs into a wide fan throw.
  nyx_throw_w: P([0.08, -0.41, 0], [-0.05, 0.33, 0], [-0.54, -1.0, -0.33], [1.17, 0, 0], [-0.60, 0.95, 0.34], [1.14, 0, 0], [-0.29, 0, 0.13], [0.32, 0, -0.12], -0.07),
  nyx_throw_s: P([0.29, 0.11, 0], [-0.07, -0.05, 0], [-1.70, -0.52, -0.10], [1.35, 0, 0], [-1.66, 0.56, 0.13], [1.35, 0, 0], [-0.52, 0, 0.13], [0.50, 0, -0.13], -0.10),
  // Phantom Rush: low coiled posture, driving double-dagger cut, immediate compact recover.
  nyx_rush_w: P([0.49, -0.52, 0], [-0.27, 0.37, 0], [-0.31, -0.95, -0.38], [1.18, 0, 0], [-0.33, 0.90, 0.42], [1.18, 0, 0], [-0.71, 0, 0.17], [0.54, 0, -0.14], -0.19),
  nyx_rush_s: P([0.30, 0.41, -0.02], [-0.14, -0.30, 0], [-1.70, 0.71, -0.14], [1.36, 0, 0], [-1.66, -0.72, 0.15], [1.34, 0, 0], [-0.87, 0, 0.17], [0.63, 0, -0.15], -0.12),
};

'''

def patch_kits(text: str) -> str:
    text = require_one(text, '// Bow in the left hand.', NYX_POSES + '// Bow in the left hand.', 'Nyx pose definition')
    text = require_one(text,
        '...(kit === "knight" && element === "light" ? { ...ASTER_SWINGS, ...ASTER_COMBAT_V2 } : {})',
        '...(kit === "knight" && element === "light" ? { ...ASTER_SWINGS, ...ASTER_COMBAT_V2 } : {}), ...(kit === "assassin" ? NYX_SHADOW_V1 : {})',
        'Nyx-only pose mapping') if '...ASTER_COMBAT_V2' in text else require_one(text,
        '...(TABLES[kit] ?? KNIGHT)', '...(TABLES[kit] ?? KNIGHT), ...(kit === "assassin" ? NYX_SHADOW_V1 : {})',
        'Nyx-only pose mapping (legacy)')
    def assassin_skill_poses(section):
        pattern = {
            'heavy': ('nyx_heavy_w', 'nyx_heavy_s'),
            'z': ('nyx_smoke_w', 'nyx_smoke_s'),
            'x': ('nyx_throw_w', 'nyx_throw_s'),
            'c': ('nyx_rush_w', 'nyx_rush_s'),
        }
        for key, (w, s) in pattern.items():
            regex = rf'(^    {key}: a\(\{{[^\n]*?)(pose_w: "[^"]+", pose_s: "[^"]+")'
            section, count = re.subn(regex, lambda m: m.group(1) + f'pose_w: "{w}", pose_s: "{s}"', section, count=1, flags=re.M)
            if count != 1: raise PatchError(f'Nyx {key} combat skill pose mapping not found')
        return section
    return section_replace(text, 'function assassin(): Record<string, Attack> {', '// KAIZEN_CHAINBLADE_V1', assassin_skill_poses, 'Nyx skill pose changes')

def patch_fighter(text: str) -> str:
    # Preserve Kira's existing three-hit implementation; Nyx uses completely separate counters.
    text = require_one(text, '  private kiraAirBuffered = false;\n',
        '  private kiraAirBuffered = false;\n  // NYX_SHADOW_COMBAT_AIR_2_V1: two separate airborne dagger hits per jump.\n  private nyxAirStrikes = 0;\n  private nyxAirBuffered = false;\n', 'Nyx air state')
    # The original generic air_l1 is deliberately single-hit; only Nyx overrides the separate chain.
    anchor = '    this.root.rotation.order = "YXZ";'
    inject = '''    if (this.kit === "assassin") {
      // Two real aerial melee swings, each with separate block, parry, clash and hit tests.
      this.attacks.air_l1 = { ...this.attacks.air_l1,
        name: "Falling Fang", type: "melee", wind: 0.080, active: 0.095, recover: 0.13,
        dmg: 28, guard: 12, reach: 2.04, lunge: 0,
        knock: 0.75, heavy: false, stagger: false, next: "" };
      this.attacks.air_l2 = { ...this.attacks.air_l2,
        name: "Shadow Cross", type: "melee", wind: 0.095, active: 0.105, recover: 0.23,
        dmg: 38, guard: 16, reach: 2.17, lunge: 0,
        knock: 2.2, stun: 0.30, heavy: false, stagger: false, next: "" };
    }
'''
    text = require_one(text, anchor, inject + anchor, 'Nyx aerial hit definitions')
    # Generate distinct right/left-hand animation per strike and per directional angle.
    anchor = '    }\n  }\n\n  /** Lock aim at contact time, not the earlier button press. */'
    block = '''      if (this.kit === "assassin") {
        // Dagger one sweeps across with the right hand, dagger two reverses with the left.
        // Both poses are generated for up/level/down aim; they also work for VRM avatars.
        for (let n = 1; n <= 2; n++) {
          const nw = copy(w), ns = copy(a);
          nw.torso[0] += 0.02; ns.torso[0] += 0.10;
          nw.hips_y -= 0.015;
          nw.leg_l[0] -= 0.22; nw.leg_r[0] -= 0.16;
          ns.leg_l[0] += 0.11; ns.leg_r[0] -= 0.15;
          if (n === 1) {
            nw.torso[1] -= 0.38; ns.torso[1] += 0.55;
            nw.arm_r[0] = -0.76; nw.arm_r[1] = -0.98;
            nw.hand_r[0] = 1.05;
            ns.arm_r[0] = -1.46; ns.arm_r[1] = 1.11;
            ns.hand_r[0] = 1.3;
            nw.arm_l[0] = -1.10; ns.arm_l[0] = -1.18;
          } else {
            nw.torso[1] += 0.42; ns.torso[1] -= 0.61;
            nw.arm_l[0] = -0.73; nw.arm_l[1] = 1.05;
            nw.hand_l[0] = 1.11;
            ns.arm_l[0] = -1.57; ns.arm_l[1] = -1.16;
            ns.hand_l[0] = 1.36;
            nw.arm_r[0] = -1.03; ns.arm_r[0] = -1.14;
          }
          this.poses[`nyx_air_${n}_${direction}_w`] = nw;
          this.poses[`nyx_air_${n}_${direction}_s`] = ns;
        }
      }
'''
    text = require_one(text, anchor, block + '    }\n  }\n\n  /** Lock aim at contact time, not the earlier button press. */', 'Nyx directional airborne poses')
    # Nyx and Kira maintain independent use counters; the base other-fighter path stays single-hit.
    old = '''    if (this.kit === "kicks") this.kiraAirKicks = Math.min(3, this.kiraAirKicks + 1);
    this.airSliceUsed = this.kit !== "kicks" || this.kiraAirKicks >= 3;
    this.kiraAirBuffered = false;
    this.airSliceQueued = false;
    this.airSliceAngle = this.airAimAtOpponent();
    this.holding = false;
    this.startAttack(this.kit === "kicks" ? `air_l${this.kiraAirKicks}` : "air_l1");'''
    new = '''    if (this.kit === "kicks") this.kiraAirKicks = Math.min(3, this.kiraAirKicks + 1);
    if (this.kit === "assassin") this.nyxAirStrikes = Math.min(2, this.nyxAirStrikes + 1);
    this.airSliceUsed = this.kit === "kicks" ? this.kiraAirKicks >= 3 :
      this.kit === "assassin" ? this.nyxAirStrikes >= 2 : true;
    this.kiraAirBuffered = false;
    this.nyxAirBuffered = false;
    this.airSliceQueued = false;
    this.airSliceAngle = this.airAimAtOpponent();
    this.holding = false;
    this.startAttack(this.kit === "kicks" ? `air_l${this.kiraAirKicks}` :
      this.kit === "assassin" ? `air_l${this.nyxAirStrikes}` : "air_l1");'''
    text = require_one(text, old, new, 'Nyx two-attack airborne trigger')
    old = '''        this.kiraAirBuffered = true;
      } else this.tryAirSlice();'''
    new = '''        this.kiraAirBuffered = true;
      } else if (this.kit === "assassin" && this.state === S.ATTACK &&
          this.atkId === "air_l1" && this.nyxAirStrikes < 2) {
        // Buffer second tap during Falling Fang; release into Shadow Cross on recovery.
        this.nyxAirBuffered = true;
      } else this.tryAirSlice();'''
    text = require_one(text, old, new, 'Nyx mid-air tap buffering')
    anchor = '    if (this.kit === "hammer" && a.name !== "Upsie Daisie" && this.atkPhase === 0 &&'
    new = '''    if (this.kit === "assassin" && this.nyxAirBuffered && !this.onGround &&
        this.atkId === "air_l1" && this.nyxAirStrikes < 2 &&
        this.stateT >= w + ac) {
      // A new attack instance: the second cut must hit on its own merits.
      this.nyxAirBuffered = false;
      this.nyxAirStrikes = 2;
      this.airSliceUsed = true;
      this.airSliceAngle = this.airAimAtOpponent();
      this.startAttack("air_l2");
      return;
    }

'''
    text = require_one(text, anchor, new + anchor, 'Nyx chained air slash contact')
    # Landing, death and respawn must clear the counter; do not allow additional midair hits.
    reset = 'this.kiraAirKicks = 0; this.kiraAirBuffered = false;'
    count = text.count(reset)
    if count < 4 or count > 8: raise PatchError(f'Unexpected aerial state reset count: {count}')
    text = text.replace(reset, reset + ' this.nyxAirStrikes = 0; this.nyxAirBuffered = false;')
    # Allow small steer during a committed airborne cut; much less than Kira's kicks.
    old = '''    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 :
      this.state === S.CHARGE ? 0.4 : kiraAirSteer ? 0.92 : 0;'''
    new = '''    const nyxAirSteer = this.kit === "assassin" && !this.onGround && this.state === S.ATTACK &&
      /^air_l[1-2]$/.test(this.atkId);
    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 :
      this.state === S.CHARGE ? 0.4 : kiraAirSteer ? 0.92 : nyxAirSteer ? 0.63 : 0;'''
    text = require_one(text, old, new, 'Nyx air slash input steer')
    # Faster snap to attack, soft recoil to guard; leaves actual hit windows unchanged.
    anchor = '''        if (this.poseOverride) { p = this.poseOverride; sp = 40; break; }'''
    inject = '''        // NYX_SHADOW_COMBAT_AIR_2_V1: fast dagger contact, compact recover, no wide robotic arms.
        if (this.kit === "assassin" && a) {
          if (this.atkPhase === 0) { p = a.pose_w; sp = 29; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = 76; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.63) { p = a.pose_s; sp = 23; }
          else { p = "idle"; sp = 19; }
          break;
        }
'''
    text = require_one(text, anchor, inject + anchor, 'Nyx impact and recovery pose speeds')
    # Only an assassin air_l2 is redirected to custom animation (Kira stays intact).
    old = '''(this.atkId === "air_l1" || (this.kit === "kicks" && /^air_l[2-3]$/.test(this.atkId)))'''
    new = '''(this.atkId === "air_l1" || (this.kit === "kicks" && /^air_l[2-3]$/.test(this.atkId)) ||
        (this.kit === "assassin" && this.atkId === "air_l2"))'''
    text = require_one(text, old, new, 'Nyx second air swing directional render')
    old = '''      } else p = `air_slice_${direction}_${this.atkPhase === 0 ? "w" : "s"}`;
      sp = this.atkPhase === 0 ? 24 : 56;'''
    new = '''      } else if (this.kit === "assassin") {
        p = `nyx_air_${this.atkId === "air_l2" ? 2 : 1}_${direction}_${this.atkPhase === 0 ? "w" : "s"}`;
      } else p = `air_slice_${direction}_${this.atkPhase === 0 ? "w" : "s"}`;
      sp = this.atkPhase === 0 ? (this.kit === "assassin" ? 34 : 24) : (this.kit === "assassin" ? 74 : 56);'''
    text = require_one(text, old, new, 'Nyx directional dagger strike poses')
    return text

def patch_model(text: str) -> str:
    # Motion overlays apply only to the fallback/pose skeleton, also driving VRM input joints.
    anchor = '''    // Veyr's low stalking posture also animates the procedural fallback (no VRM yet).'''
    block = '''    // NYX_SHADOW_COMBAT_AIR_2_V1: lively side-to-side ninja footwork, not a heavy gait.
    // While moving she shifts through her shoulders; in guard she stays compact.
    if (this.kit === "assassin") {
      this.torso.rotation.x += 0.035 + 0.060 * moving;
      this.torso.rotation.y += Math.sin(this.walkPhase) * 0.045 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.018 * moving;
      this.head.rotation.y -= Math.sin(this.walkPhase) * 0.025 * moving;
      this.hips.position.y += Math.abs(Math.sin(this.walkPhase * 2)) * 0.009 * moving;
    }
'''
    return require_one(text, anchor, block + anchor, 'Nyx nimble run/guard overlay')

def patch_vrm(text: str) -> str:
    marker = '''  // Feral dual-sickle hunter: hunched, asymmetrical, with deliberately planted feet.'''
    profile = '''  // NYX_SHADOW_COMBAT_AIR_2_V1: low-bladed but light-footed dual-dagger assassin.
  shadow: { stance: D(7), toeOut: D(7), knee: D(10), drop: 0.018, lean: D(6), chin: D(2), shoulderUp: D(1), elbowOut: D(5),
    hipSway: 0.010, hipRoll: D(1.2), contra: D(2.0), relaxKnee: D(4), headTilt: D(1), headYaw: D(7),
    breath: 0.76, armSwing: D(17), walkRoll: D(2), walkYaw: D(5) },
'''
    text = require_one(text, marker, profile + marker, 'Nyx VRM locomotion style')
    return text

def patch_ai(text: str) -> str:
    # Nyx's CPU also gets a second tap during her first air slash, using the same
    # real-input logic that already drives Kira's triple airborne kick attacks.
    old = '''    if (!f.stage && f.kit === "kicks" && !f.onGround && f.state === S.ATTACK &&
        /^air_l[1-3]$/.test(f.atkId)) {'''
    new = '''    // NYX_SHADOW_COMBAT_AIR_2_V1: airborne dagger pursuit uses normal steering.
    if (!f.stage && (f.kit === "kicks" || f.kit === "assassin") &&
        !f.onGround && f.state === S.ATTACK &&
        (f.kit === "kicks" ? /^air_l[1-3]$/.test(f.atkId) : /^air_l[1-2]$/.test(f.atkId))) {'''
    text = require_one(text, old, new, 'Nyx CPU midair steering')
    old = '''(f.state === S.IDLE || (f.kit === "kicks" && f.state === S.ATTACK && /^air_l[1-3]$/.test(f.atkId)))'''
    new = '''(f.state === S.IDLE || (f.state === S.ATTACK &&
          (f.kit === "kicks" ? /^air_l[1-3]$/.test(f.atkId) :
            f.kit === "assassin" && f.atkId === "air_l1")))'''
    text = require_one(text, old, new, 'Nyx CPU two-hit aerial input')
    old = 'this.airSliceCd = f.kit === "kicks" ? rand(0.17, 0.24) : rand(0.55, 0.85);'
    new = 'this.airSliceCd = f.kit === "kicks" || f.kit === "assassin" ? rand(0.17, 0.24) : rand(0.55, 0.85);'
    text = require_one(text, old, new, 'Nyx CPU aerial tap cadence')
    return text

def plan(root: Path) -> dict[str, bytes]:
    changes = {}
    for rel in FILES:
        path = root / rel
        raw = path.read_bytes()
        original = raw.decode('utf-8')
        if VERSION in original:
            # Treat preinstalled files as complete only if every file carries the version marker.
            changes[rel] = raw
            continue
        new = {
            'src/game/kits.ts': patch_kits,
            'src/game/fighter.ts': patch_fighter,
            'src/game/model.ts': patch_model,
            'src/game/vrm.ts': patch_vrm,
            'src/game/ai.ts': patch_ai,
        }[rel](original)
        if new == original: raise PatchError(f'No changes generated for {rel}')
        changes[rel] = new.encode('utf-8')
    return changes

def install(root: Path, check: bool) -> None:
    changes = plan(root)
    already = [rel for rel in FILES if VERSION in (root / rel).read_text('utf-8')]
    if already and len(already) != len(FILES):
        raise PatchError('Partial Nyx V1 installation detected. Restore from backup and rerun; no files changed.')
    updates = [rel for rel in FILES if (root / rel).read_bytes() != changes[rel]]
    print('Fight Royale web:', root)
    if not updates:
        print('[OK] Nyx Shadow Combat V1 already installed; nothing to change.')
        return
    print('Valid patches:', ', '.join(updates))
    if check:
        print('[CHECK] No files were modified.')
        return
    backup = root / '.fightroyale_nyx_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True, exist_ok=False)
    for rel in updates:
        target = root / rel
        destination = backup / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, destination)
    for rel in updates:
        dest = root / rel
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=dest.parent, prefix='.nyx_tmp_', delete=False) as stream:
                stream.write(changes[rel]); tmp = Path(stream.name)
            os.replace(tmp, dest)
        finally:
            if tmp and tmp.exists(): tmp.unlink()
    print('[DONE] Nyx animations and 2-hit airborne dagger chain installed.')
    print('Backups:', backup)
    print('Run: npx tsc --noEmit -p .  then  npm run dev')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Nyx combat animations + two strikes per jump (Kira keeps three).')
    parser.add_argument('project', nargs='?', help='Optional path to Fight Royale web folder')
    parser.add_argument('--check', action='store_true', help='Validate source patch without writing')
    ns = parser.parse_args()
    try:
        install(locate(ns.project), ns.check)
    except (OSError, UnicodeError, PatchError) as ex:
        print('[ERROR]', ex, file=sys.stderr)
        raise SystemExit(1)
