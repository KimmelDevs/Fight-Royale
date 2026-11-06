#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install Nesa (including previous Weight Passive) + Momentum V3 combat update.
Run: python Install_Nesa_Momentum_Complete.py [path_to_web]
Requires sibling base and weight installers bundled in the same ZIP. No pip dependencies.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import os, argparse, shutil, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parent
BASE = HERE / 'Install_Nesa_Heart_Hammer_Fixed.py'
WEIGHT = HERE / 'Install_Nesa_Weight_Passive_Update.py'
FILES = ['src/game/kits.ts', 'src/game/fighter.ts', 'src/game/game.ts', 'src/game/model.ts', 'src/game/ai.ts']
VERSION = 'NESA_MOMENTUM_V3'

class PatchError(RuntimeError): pass

def one(s, before, after, tag):
    c=s.count(before)
    if c!=1: raise PatchError(f'{tag}: expected one code anchor, got {c}')
    return s.replace(before,after,1)

def between(s, start, end, replacement, tag):
    a=s.find(start)
    b=s.find(end,a+len(start)) if a>=0 else -1
    if a<0 or b<0: raise PatchError(f'{tag}: cannot find code boundary')
    return s[:a]+replacement+s[b:]

def root_at(spec):
    base=Path(spec).expanduser().resolve() if spec else Path.cwd()
    for p in [base,base/'web']:
        if (p/'src/game/kits.ts').is_file() and (p/'src/game/fighter.ts').is_file(): return p
    if not spec:
        try:
            import tkinter as tk
            from tkinter import filedialog
            app=tk.Tk(); app.withdraw()
            target=filedialog.askdirectory(title='Select Fight Royale web folder')
            app.destroy()
            if target: return root_at(target)
        except Exception: pass
    raise PatchError('Cannot locate Fight Royale web folder; run from web or provide its path.')

ATTACKS = '''function hammer(): Record<string, Attack> {
  return {
    // NESA_MOMENTUM_V3: longer weighty casts, fast impact frames, higher knockback.
    l1: a({ name: "Heart Hook", desc: "Heavy horizontal opener; deliberate pull, fast contact.", wind: 0.43, active: 0.095, recover: 0.21, dmg: 97, guard: 28, reach: 2.43, lunge: 1.9, knock: 3.1, stun: 0.29, pose_w: "l1_w", pose_s: "l1_s", next: "l2" }),
    l2: a({ name: "Reverse Crush", desc: "Uses the first hit's momentum to swing back while stepping forward.", wind: 0.45, active: 0.095, recover: 0.22, dmg: 107, guard: 30, reach: 2.53, lunge: 2.35, knock: 3.7, stun: 0.32, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ name: "Overhead Spin", desc: "A staggered-foot pivot into a quick overhead strike.", wind: 0.50, active: 0.10, recover: 0.24, dmg: 129, guard: 35, reach: 2.64, lunge: 2.65, knock: 4.5, stun: 0.38, pose_w: "l3_w", pose_s: "l3_s", next: "l4" }),
    l4: a({ name: "Heartquake", desc: "Fourth hit: massive shockwave ground slam.", type: "strike", at: "self", wind: 0.57, active: 0.14, recover: 0.44, dmg: 178, guard: 47, reach: 2.55, lunge: 3.25, knock: 8.6, stun: 0.72, heavy: true, delay: 0.06, radius: 2.55, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
    heavy: a({ name: "Momentum Cyclone", desc: "Hold left-click to control spin duration; each turn hits, the final turn launches.", wind: 0.45, active: 0.48, recover: 0.43, dmg: 36, guard: 15, reach: 2.58, lunge: 2.10, knock: 1.5, stun: 0.20, heavy: false, style: "nesa_spin", pose_w: "charge", pose_s: "l3_s" }),
    z: a({ name: "Side Swipe", desc: "Huge sideways strike. Block reduces damage but cannot nullify its push.", cd: 7, wind: 0.36, active: 0.11, recover: 0.42, dmg: 180, guard: 72, reach: 2.69, lunge: 1.75, knock: 9.6, stun: 0.70, heavy: true, pose_w: "nx_w", pose_s: "nx_s" }),
    x: a({ name: "Upsie Daisie", desc: "Plant the hammer as a pole, keep a firm grip, then swing sideways into a long-reaching flying kick.", cd: 9, wind: 0.40, active: 0.16, recover: 0.50, dmg: 170, guard: 36, reach: 2.62, lunge: 7.8, knock: 7.3, stun: 0.57, heavy: true, self_jump: 6.6, pose_w: "kick_w", pose_s: "kick_s" }),
    c: a({ name: "GIGA BONK!", desc: "Struggle to lift the heart hammer, leap and smash the arena with a huge shockwave.", cd: 19, type: "strike", at: "self", mode: "leap", self_jump: 7.9, wind: 0.69, active: 0.17, recover: 0.90, dmg: 340, guard: 95, knock: 11.2, stun: 1.13, heavy: true, radius: 3.25, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
  };
}

'''
BONUS = '''    case "hammer":
      return a({ name: "Heartbreaker High Striker", desc: "Carnival smash: a stunning bonk, 4x hammer growth, then a second overwhelming blow.", cd: 26, type: "strike", at: "self", wind: 0.66, active: 2.20, recover: 0.90, dmg: 145, guard: 85, knock: 12.5, stun: 3.0, heavy: true, radius: 3.50, style: "nesa_high_striker", pose_w: "charge", pose_s: "heavy_s" });
'''

def patch_kits(s):
    s=between(s,'function hammer(): Record<string, Attack> {','function katana(): Record<string, Attack> {', ATTACKS,'Nesa attacks')
    a=s.find('function bonusSkill(')
    st=s.find('    case "hammer":',a)
    en=s.find('    case "katana":',st)
    if st<0 or en<0: raise PatchError('Missing hammer bonus skill')
    s=s[:st]+BONUS+s[en:]
    # All Nesa attacks have no perfect-parry nullification. Block still reduces damage.
    marker='  t.v = bonusSkill(kit, element);'
    updated='''  t.v = bonusSkill(kit, element);
  // NESA_MOMENTUM_V3: every hammer blow carries weight through ordinary blocks;
  // perfect parries are disabled for this kit, but dodges still beat the attack.
  if (kit === "hammer") for (const move of Object.values(t)) {
    if (move.dmg > 0) move.no_parry = true;
  }'''
    s=one(s,marker,updated,'hammer unparryable moves')
    # Unique weaker, strained stance and clear planted hammer kick poses.
    marker='const NESA_SWINGS: Record<string, Pose> = {'
    if marker not in s: raise PatchError('Missing Nesa pose table')
    s=one(s,
'''  idle: K(P([0.14, -0.2, 0], [-0.06, 0.15, 0], [-0.9, -0.18, -0.10], [-0.2, 0, 0], [-0.96, 0.13, 0.12], [-0.2, 0, 0], [-0.35, 0, 0.07], [0.18, 0, -0.06], -0.13), 0.15, 0.25),''',
'''  // Hammer weight pulls Nesa's shoulders down; bent knees and a forward torso counterbalance it.
  idle: K(P([0.30, -0.24, 0.06], [-0.16, 0.18, 0], [-1.12, -0.27, -0.18], [-0.10, 0, 0], [-1.14, 0.21, 0.18], [-0.10, 0, 0], [-0.47, 0, 0.12], [0.30, 0, -0.12], -0.21), 0.50, 0.42),''','strained Nesa idle')
    s=one(s,
'''  kick_w: K(P([0.48, -0.2, 0], [-0.16, 0.10, 0], [-0.5, 0.2, 0.1], [0.3, 0, 0], [-0.4, -0.2, -0.15], [0.4, 0, 0], [-0.65, 0, 0], [-0.35, 0, 0.06], -0.4), 1.0, 0.8),
  kick_s: K(P([-0.2, 0.1, 0], [0.14, -0.1, 0], [-0.65, 0.7, 0.18], [0.1, 0, 0], [-0.6, -0.6, -0.2], [0.1, 0, 0], [-1.42, 0, 0.02], [0.48, 0, -0.10], -0.04), 0.15, 0.85),''',
'''  // Pole planted: both hands low and forward; side kick follows while still gripping shaft.
  kick_w: K(P([0.58, -0.18, -0.05], [-0.24, 0.08, 0], [-0.52, 0.05, 0.20], [0.48, 0, 0], [-0.53, -0.16, -0.20], [0.48, 0, 0], [-0.90, 0, 0.05], [-0.36, 0, -0.07], -0.38), 1.10, 0.86),
  kick_s: K(P([-0.20, 0.06, 0.10], [0.17, -0.10, 0], [-0.70, 0.15, 0.12], [0.32, 0, 0], [-0.66, -0.14, -0.20], [0.34, 0, 0], [-1.51, 0, 0.04], [0.43, 0, -0.10], -0.02), 0.09, 0.92),''', 'hammer pole-kick poses')
    return s

MODEL_HELPERS='''  /** Nesa's heart hammer root, isolated so the carnival finisher can grow it 4x. */
  private nesaHammerPivot: THREE.Group | null = null;
  nesaHammerScale = 1;
'''

def patch_model(s):
    s=one(s,'  private glaivePivot: THREE.Group | null = null;', '  private glaivePivot: THREE.Group | null = null;\n'+MODEL_HELPERS.rstrip(), 'Nesa model fields')
    s=one(s,'    const h = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);\n    // Two-handed striped handle and soft pink heart-shaped forged head.',
'''    const h = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    this.nesaHammerPivot = h;
    // Two-handed striped handle and soft pink heart-shaped forged head.''','hammer pivot reference')
    # blend sets scale on the weapon pivot, only after the VRM hand scale already applied by code.
    s=one(s,'  blend(pose: Pose, dt: number, speed: number) {', '''  blend(pose: Pose, dt: number, speed: number) {
    if (this.nesaHammerPivot) {
      const value = THREE.MathUtils.clamp(this.nesaHammerScale, 1, 4);
      const current = this.nesaHammerPivot.scale.x;
      this.nesaHammerPivot.scale.setScalar(THREE.MathUtils.damp(current, value, value > current ? 8 : 13, dt));
    }''','Nesa hammer growth animation')
    # Strained load carry while walking; tiny uneven bob instead of princess float.
    s=one(s,'    const s = Math.sin(this.walkPhase);', '''    const s = Math.sin(this.walkPhase);
    if (this.kit === "hammer") {
      // Weight-specific walking is handled below by short steps and shoulder lag.
      this.walkPhase += Math.sin(this.t * 1.1) * 0.0004 * moving;
    }''','Nesa burdened gait')
    s=one(s,'    // Veyr\'s low stalking posture also animates the procedural fallback (no VRM yet).', '''    if (this.kit === "hammer") {
      this.torso.rotation.x += 0.09 + 0.12 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.045 * moving;
      this.head.rotation.x -= 0.06;
      this.hips.position.y -= 0.035 + moving * 0.014;
      this.leg_l.rotation.x *= 0.79;
      this.leg_r.rotation.x *= 0.79;
    }
    // Veyr's low stalking posture also animates the procedural fallback (no VRM yet).''','Nesa strain posture')
    return s

FIGHTER_FIELDS='''  // NESA_MOMENTUM_V3: isolated charge state; does not alter anyone else's controls.
  private nesaAirHolding = false;
  private nesaAirChargeT = 0;
  private nesaAirChargedSeconds = 0;
  private nesaChargeSeconds = 0;
  private nesaSpinYaw = 0;
  private nesaSpinT = 0;
'''

READ_AIR='''    // NESA_MOMENTUM_V3: charge a directional midair hammer strike instead of auto-slicing.
    if (this.kit === "hammer" && !this.stage && !this.onGround &&
        (this.state === S.IDLE || this.state === S.BLOCK || this.nesaAirHolding)) {
      if (pressed && !this.airSliceUsed && !this.nesaAirHolding) {
        this.nesaAirHolding = true; this.nesaAirChargeT = 0;
        this.holding = false;
      }
      if (this.nesaAirHolding) {
        if (on) this.nesaAirChargeT = Math.min(0.88, this.nesaAirChargeT + dt);
        if (released || this.nesaAirChargeT >= 0.88) this.nesaReleaseAirStrike();
        return;
      }
    }
'''

RELEASE_METHOD='''  private nesaReleaseAirStrike() {
    if (!this.nesaAirHolding || this.airSliceUsed || this.state === S.KO) return;
    this.nesaAirHolding = false;
    this.nesaAirChargedSeconds = Math.max(0.05, Math.min(this.nesaAirChargeT, 0.88));
    this.nesaAirChargeT = 0;
    this.tryAirSlice();
  }

'''

SPIN_START='''    if (this.kit === "hammer" && id === "heavy") {
      // The spin persists for precisely the time earned by holding the charge.
      const held = THREE.MathUtils.clamp(this.holdT, HOLD_T, 1.75);
      const spin = 0.34 + (held - HOLD_T) * 0.77;
      this.nesaChargeSeconds = held;
      this.atk = { ...this.atk, active: spin, recover: 0.42,
        dmg: 32 + Math.round(held * 8), reach: 2.58 + held * 0.06,
        knock: 1.8 + held * 0.25, style: "nesa_spin", no_parry: true };
    }
    if (this.kit === "hammer" && id === "air_l1") {
      // A single airborne hammer hit, scaling damage and knockback with hold seconds.
      const ratio = THREE.MathUtils.clamp(this.nesaAirChargedSeconds / 0.88, 0, 1);
      this.atk = { ...this.atk, type: "melee", wind: 0.11, active: 0.15,
        recover: 0.30, dmg: 84 + 122 * ratio, knock: 3.8 + 5.0 * ratio,
        guard: 23 + 25 * ratio, reach: 2.40, lunge: 0.5,
        stun: 0.27 + ratio * 0.34, heavy: ratio >= 0.65,
        no_parry: true, next: "" };
      this.nesaAirChargedSeconds = 0;
    }
'''

SPIN_VISUAL='''    if (this.kit === "hammer") {
      const attack = this.state === S.ATTACK ? this.atk : null;
      if (attack?.style === "nesa_spin" && this.stateT >= attack.wind &&
          this.stateT <= attack.wind + attack.active) {
        const t = Math.max(0, (this.stateT - attack.wind) / attack.active);
        const turns = Math.max(1, Math.round(attack.active / 0.27));
        this.nesaSpinYaw = t * turns * Math.PI * 2;
      } else this.nesaSpinYaw = 0;
      this.model.nesaHammerScale = attack?.style === "nesa_high_striker" &&
        this.stateT >= attack.wind + 0.24 && this.stateT < attack.wind + attack.active + 0.12
        ? 4 : 1;
    } else this.nesaSpinYaw = 0;
'''

POSE_SPECIAL='''        if (this.kit === "hammer" && a) {
          if (a.style === "nesa_spin") {
            p = this.atkPhase === 0 ? "charge" : (Math.floor(Math.max(0, this.stateT - a.wind) / 0.19) % 2 === 0 ? "l3_s" : "l2_s");
            sp = this.atkPhase === 0 ? 10 : 72;
          } else if (a.style === "nesa_high_striker") {
            p = this.stateT < a.wind + 0.25 ? "charge" :
              this.stateT < a.wind + 1.74 ? "l3_w" : "heavy_s";
            sp = this.stateT < a.wind + 1.74 ? 12 : 65;
          } else if (this.atkPhase === 0) { p = a.pose_w; sp = 9.5; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = 65; }
          else { p = a.pose_s; sp = 12; }
          break;
        }
'''

def patch_fighter(s):
    s=one(s,'  private holdT = 0;', '  private holdT = 0;\n'+FIGHTER_FIELDS.rstrip(), 'Nesa fighter state')
    # Weight Passive: normal blocks reduce Nesa's damage by the specified 50%.
    s=s.replace('this.lastDamage = hammerCrush ? dmg * 0.55 : dmg * 0.4;',
                'this.lastDamage = hammerCrush ? dmg * 0.50 : dmg * 0.4;')
    s=s.replace('this.lastDamage = dmg * 0.58;', 'this.lastDamage = dmg * 0.50;')
    # At 60-70% of the wind-up, the swing's mass becomes difficult to interrupt.
    old='return this.stateT >= total * 0.60;'
    if old in s:
        s=one(s,old,'return this.stateT >= Math.min(total * 0.60, this.atk.wind * 0.70);','earlier weight armor')
    # Keep holding up to 1.75s for a longer spin, and launch on release.
    s=one(s,'else if (this.stateT >= CHARGE_MAX) { this.holding = false; this.startAttack("heavy"); }',
'''else if (this.stateT >= (this.kit === "hammer" ? 1.53 : CHARGE_MAX)) {
          this.holding = false; this.startAttack("heavy");
        }''','Nesa ground max hold')
    s=one(s,'    // Airborne left-click is an ordinary basic swing, even without Space held.',READ_AIR+'    // Airborne left-click is an ordinary basic swing, even without Space held.','Nesa air charge readAttack')
    s=one(s,'    if (!this.stage && pressed && this.onGround && this.intent.jump &&',
'''    if (this.kit === "hammer" && !this.stage && pressed && this.onGround && this.intent.jump) {
      this.nesaAirHolding = true; this.nesaAirChargeT = 0;
      this.holding = false; return;
    }
    if (!this.stage && pressed && this.onGround && this.intent.jump &&''','hammer space+click')
    s=one(s,'    if (!this.stage && pressed && !this.onGround) {',
'''    if (!this.stage && pressed && !this.onGround) {''','air branch anchor check')
    s=one(s,'    if (pressed) { this.holding = true; this.holdT = 0; }',
'''    if (pressed) { this.holding = true; this.holdT = 0; }''','hold anchor check')
    s=one(s,'  private tryAirSlice() {',RELEASE_METHOD+'  private tryAirSlice() {','Nesa air release method')
    s=one(s,'      if (this.airSliceQueued) this.tryAirSlice();',
'''      if (this.kit === "hammer" && this.nesaAirHolding) this.nesaAirChargeT = 0;
      else if (this.airSliceQueued) this.tryAirSlice();''','jump arm Nesa air')
    # Prevent full ground charge accidentally firing an uncharged air slice.
    s=one(s,'    if (this.root.position.y <= 0) {',
'''    if (this.kit === "hammer" && this.nesaAirHolding && this.velY < 0 &&
        this.root.position.y < 0.52) this.nesaReleaseAirStrike();
    if (this.root.position.y <= 0) {''', 'charge auto-release before landing')
    s=one(s,'    this.atkPhase = 0;\n    this.buffered = false;\n    this.comboDamageMult = 1;',
SPIN_START+'    this.atkPhase = 0;\n    this.buffered = false;\n    this.comboDamageMult = 1;', 'Nesa start attack charge')
    # Nesa plants the hammer as a lever for X, then springs upward on the KICK frame.
    s=one(s,'    if (this.atk.self_jump > 0 && this.atk.mode !== "leap") { this.velY = this.atk.self_jump * (this.stage ? 1.35 : 1); this.onGround = false; this.ground = null; }',
'''    if (this.atk.self_jump > 0 && this.atk.mode !== "leap" &&
        !(this.kit === "hammer" && id === "x")) {
      this.velY = this.atk.self_jump * (this.stage ? 1.35 : 1);
      this.onGround = false; this.ground = null;
    }''','Nesa pole-plant before flight')
    s=one(s,'      this.atkPhase = 1;\n      if (!this.stage && this.atkId === "air_l1") this.airSliceAngle = this.airAimAtOpponent();',
'''      this.atkPhase = 1;
      if (this.kit === "hammer" && this.atkId === "x") {
        // The pole is braced before the kick launches, not after.
        this.velY = Math.max(this.velY, a.self_jump);
        this.onGround = false; this.ground = null;
      }
      if (!this.stage && this.atkId === "air_l1") this.airSliceAngle = this.airAimAtOpponent();''','Nesa lever-kick takeoff')
    # Hide air hold's pose and highlight charge glow.
    s=one(s,'    this.model.charge = this.state === S.CHARGE ? Math.min(this.stateT / CHARGE_MAX, 1) : Math.max(this.model.charge - dt * 4, 0);',
'''    this.model.charge = this.kit === "hammer" && this.nesaAirHolding
      ? Math.min(1, this.nesaAirChargeT / 0.88)
      : this.state === S.CHARGE ? Math.min(this.stateT / (this.kit === "hammer" ? 1.53 : CHARGE_MAX), 1)
      : Math.max(this.model.charge - dt * 4, 0);''','Nesa air charge glow')
    s=one(s,'    this.model.rotation.y = this.viewBias + this.tempestSpin + + this.cycloneSpin + this.bladeSwingYaw;',
SPIN_VISUAL+'    this.model.rotation.y = this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw + this.nesaSpinYaw;', 'Nesa spin host animation')
    s=one(s,'    if (this.state !== S.KO) this.model.rotation.y = this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw;',
'''    if (this.state !== S.KO) this.model.rotation.y = this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw + this.nesaSpinYaw;
    this.model.nesaHammerScale = this.kit === "hammer" && this.poseName === "heavy_s" ? this.model.nesaHammerScale : this.model.nesaHammerScale;''', 'Nesa spin remote animation')
    # Remove inert self assignment; actual remote hammer scale set via snapshot below.
    s=s.replace('    this.model.nesaHammerScale = this.kit === "hammer" && this.poseName === "heavy_s" ? this.model.nesaHammerScale : this.model.nesaHammerScale;\n','')
    s=one(s,'          else { p = "jump"; sp = 12; }',
'''          else if (this.kit === "hammer" && this.nesaAirHolding) { p = "charge"; sp = 10; }
          else { p = "jump"; sp = 12; }''','Nesa airborne wind-up pose')
    s=one(s,'      case S.ATTACK:\n        if (this.poseOverride)',
'''      case S.ATTACK:
'''+POSE_SPECIAL+'''        if (this.poseOverride)''','Nesa slower wind fast swing')
    # Footsteps adapt to target after knockback; not a teleport or attack range hack.
    s=one(s,'    if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1 && dist > MIN_DIST + 0.15) v += this.atk.lunge;',
'''    if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1 && dist > MIN_DIST + 0.15) {
      if (this.kit === "hammer" && /^l[1-4]$/.test(this.atkId)) {
        // The next swing shuffles after the knockback with deliberate weighted steps.
        const gap = Math.max(0, dist - this.atk.reach * 0.74);
        const max = this.atk.lunge + (this.atkId === "l1" ? 0 : 1.1);
        v += Math.min(max, 0.85 + gap * 1.28) * (this.atkPhase === 0 ? 0.46 : 1.75);
      } else if (this.kit === "hammer" && this.atkId === "x") {
        // Plant during wind-up; use the fast active kick for the forward burst.
        v += this.atkPhase === 0 ? 0 : Math.min(10.5, this.atk.lunge * 1.4);
      } else if (this.kit === "hammer" && this.atkId === "heavy" && this.atk.style === "nesa_spin") {
        // Each hammer revolution takes a short step toward a recoiling opponent.
        v += this.atkPhase === 0 ? 0.35 : Math.min(5.5, 1.65 + Math.max(0, dist - 2.1) * 2.1);
      } else v += this.atk.lunge;
    }''','Nesa basic chase steps')
    # If Nesa is stunned while waiting to release an air charge, reset it.
    s=one(s,'    if ([S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state)) { this.holding = false; return; }',
'''    if ([S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state)) {
      this.holding = false; this.nesaAirHolding = false; return;
    }''','Nesa charged air cancellation')
    s=s.replace('    this.airSliceUsed = false; this.airSliceQueued = false;\n',
        '    this.airSliceUsed = false; this.airSliceQueued = false;\n    this.nesaAirHolding = false; this.nesaAirChargeT = 0; this.nesaSpinYaw = 0;\n')
    # Appended host->client snapshot fields, backward-compatible.
    s=one(s,'+this.comboPauseT.toFixed(2), +this.stateT.toFixed(3)];',
'''+this.comboPauseT.toFixed(2), +this.stateT.toFixed(3),
      +this.nesaSpinYaw.toFixed(3), +this.model.nesaHammerScale.toFixed(2)];''','sync Nesa visuals snapshot')
    s=one(s,'    if (s.length > 41) this.stateT = s[41];',
'''    if (s.length > 41) this.stateT = s[41];
    this.nesaSpinYaw = s.length > 42 ? s[42] : 0;
    this.model.nesaHammerScale = s.length > 43 ? s[43] : 1;''','remote hammer spin and giant scale')
    return s

GAME_SPIN = '''  /** NESA_MOMENTUM_V3: held charge controls REAL spin length, not a cosmetic loop. */
  private nesaMomentumSpin(f: Fighter, a: Attack) {
    const total = Math.max(0.32, a.active);
    const beats = Math.max(2, Math.ceil(total / 0.205));
    const round = this.round;
    const serial = f.swingSerial;
    for (let i = 0; i < beats; i++) this.laterCombo(f, i * 0.205, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK ||
          f.swingSerial !== serial || f.atk?.style !== "nesa_spin") return;
      const last = i === beats - 1;
      const strike: Attack = { ...a,
        dmg: last ? a.dmg * 1.75 : a.dmg, guard: last ? 40 : 13,
        knock: last ? 7.8 + beats * 0.30 : 1.15,
        stun: last ? 0.67 : 0.18, heavy: last,
        no_parry: true, reach: 2.65 };
      const center = f.root.position.clone();
      this.fxp("slashes", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), "#ffadd3");
      this.snd(last ? "swing_heavy" : "swing", last ? 0.88 : 0.52);
      const radius = last ? 2.8 : 2.58;
      for (const d of this.enemiesOf(f)) {
        const offset = d.root.position.clone().sub(center);
        const height = Math.abs(offset.y);
        offset.y = 0;
        if (offset.length() > radius + d.radius * 0.4 || height > 1.65) continue;
        const dir = offset.lengthSq() > 0.0001 ? offset.normalize() :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        this.applyHit(f, d, strike, f.atkPower, d.chest(), dir, false);
      }
    });
  }

  /** Nesa X: planted hammer acts as a lever before the forward horizontal kick lands. */
  private nesaLeverKick(f: Fighter, a: Attack) {
    const serial = f.swingSerial, round = this.round;
    this.fxp("sparks", f.root.position.clone().add(new THREE.Vector3(0, 0.12, 0)), "#ffc0dd", 14, 4);
    // Wait for the leg to EXTEND and fighter to traverse her real active distance.
    this.laterCombo(f, 0.12, () => {
      if (round !== this.round || f.isDown() || f.swingSerial !== serial ||
          f.state !== S.ATTACK || f.atkId !== "x") return;
      this.fxp("slashes", f.model.footR?.getWorldPosition(new THREE.Vector3()) ?? f.chest(), "#ffb7dc");
      this.melee(f, a);
    });
  }

  /** Carnival high striker: hit -> real 3s stun -> grow hammer 4x -> giant finishing blow. */
  private nesaHighStriker(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial, power = f.atkPower;
    const foes = this.enemiesOf(f);
    const first: Attack = { ...a, type: "melee", dmg: 125, knock: 0.7,
      stun: 0.30, heavy: false, no_parry: true, reach: 2.65 };
    for (const d of foes) {
      const diff = d.root.position.clone().sub(f.root.position).setY(0);
      const distance = diff.length();
      if (distance > 2.65 + d.radius * 0.3 || Math.abs(d.root.position.y - f.root.position.y) > 1.3) continue;
      const facing = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
      if (distance > 0.65 && diff.dot(facing) < distance * 0.20) continue;
      const dir = distance > 0.001 ? diff.normalize() : facing;
      const hit = this.applyHit(f, d, first, power, d.chest(), dir, false);
      if (d instanceof Fighter && (hit === "hit" || hit === "crit")) {
        d.stagger(3.0); // exactly 3 s from the first connected blow (not normal stun DR)
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.75, 0)), "STUN 3s", "#ffd1e5", 0.92);
      }
    }
    // Visual growth uses the synced model.nesaHammerScale timeline in fighter.ts.
    this.fxp("flash", f.chest(), "#ffb5df", 0.8, 0.22, 0.8);
    this.laterCombo(f, 1.90, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK ||
          f.swingSerial !== serial || f.atk?.style !== "nesa_high_striker") return;
      const center = f.root.position.clone().setY(0);
      this.fxp("rocks", center, 28, 1.5);
      this.fxp("ring", center, "#ffb0db", 3.6, 0.35, 0.95);
      this.fxp("flash", center.clone().setY(0.45), "#ffffff", 1.8, 0.23, 0.95);
      this.snd("swing_heavy", 1.0);
      this.add_trauma(0.7);
      const finisher: Attack = { ...a, type: "strike", dmg: 365, guard: 105,
        knock: 13.2, stun: 1.05, heavy: true, no_parry: true };
      for (const d of this.enemiesOf(f)) {
        const diff = d.root.position.clone().sub(center);
        const height = Math.abs(diff.y);
        diff.y = 0;
        if (diff.length() > 3.6 + d.radius * 0.4 || height > 1.65) continue;
        const dir = diff.length() > 0.04 ? diff.normalize() :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        this.applyHit(f, d, finisher, power, d.chest(), dir, true);
      }
    });
  }

'''

def patch_game(s):
    s=one(s,'  private onSwing(f: Fighter) {', GAME_SPIN+'  private onSwing(f: Fighter) {', 'Nesa hit windows')
    s=one(s,'    const el = f.look.element;', '''    if (f.kit === "hammer" && a.style === "nesa_spin") {
      this.nesaMomentumSpin(f, a); return;
    }
    if (f.kit === "hammer" && a.style === "nesa_high_striker") {
      this.nesaHighStriker(f, a); return;
    }
    if (f.kit === "hammer" && f.atkId === "x") {
      this.nesaLeverKick(f, a); return;
    }
    const el = f.look.element;''','hammer custom combat resolution')
    s=one(s,'        case "hammer": knockFactor = 1.30; break; // Nesa: giant hammer shove',
        '        case "hammer": knockFactor = 1.37; break; // Nesa: extreme hammer shove',
        'Nesa increased melee knockback')
    return s

def patch_ai(s):
    # The Weight Passive installer adds Nesa positioning. Now keep a half step beyond normals.
    return s

def modifications(root):
    changes={}
    for rel in FILES:
        p=root/rel
        if not p.is_file(): raise PatchError(f'Missing {rel}')
        original=p.read_text(encoding='utf-8')
        if rel=='src/game/kits.ts': patched=patch_kits(original)
        elif rel=='src/game/fighter.ts': patched=patch_fighter(original)
        elif rel=='src/game/model.ts': patched=patch_model(original)
        elif rel=='src/game/game.ts': patched=patch_game(original)
        else: patched=patch_ai(original)
        if patched!=original: changes[rel]=patched.encode('utf-8')
    # Regenerated icons from the latest Fight Royale 4x4 heart-hammer grids.
    for src_name, dest in [
        ('nesa.webp','public/icons/chars/nesa.webp'),
        ('hammer-z.webp','public/icons/skills/hammer-z.webp'),
        ('hammer-x.webp','public/icons/skills/hammer-x.webp'),
        ('hammer-c.webp','public/icons/skills/hammer-c.webp'),
        ('hammer-v.webp','public/icons/skills/hammer-v.webp'),
    ]:
        src=HERE/'nesa_momentum_assets'/src_name
        if src.is_file() and (not (root/dest).exists() or (root/dest).read_bytes()!=src.read_bytes()):
            changes[dest]=src.read_bytes()
    vrm=HERE/'nesa_optimized.vrm'
    dest='public/models/nesa.vrm'
    if vrm.is_file() and not (root/dest).exists():
        changes[dest]=vrm.read_bytes()
    return changes

def commit(root, changes):
    if not changes:
        print('[OK] Already installed: nothing to change.'); return
    backup=root/'.nesa_installer_backups'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True,exist_ok=False)
    for rel in changes:
        source=root/rel
        if source.exists():
            target=backup/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    written=[]
    try:
        for rel,data in changes.items():
            dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as tf:
                tf.write(data);temp=Path(tf.name)
            os.replace(temp,dest);written.append(rel)
    except Exception:
        for rel in written:
            dest=root/rel;saved=backup/rel
            if saved.exists(): shutil.copy2(saved,dest)
            elif dest.exists(): dest.unlink()
        raise
    print('[OK] Files updated:',len(written),'Backup:',backup)

def main():
    ap=argparse.ArgumentParser(description='Complete Nesa installer with Weight Passive and charged momentum combat')
    ap.add_argument('project',nargs='?',help='web project folder or repository root')
    ap.add_argument('--check',action='store_true',help='dry-run for an already installed base Nesa')
    args=ap.parse_args(); root=root_at(args.project)
    print('Fight Royale web project:',root)
    if not BASE.is_file() or not WEIGHT.is_file():
        raise PatchError('Missing bundled prerequisite Python files; extract the entire ZIP.')
    kits=(root/'src/game/kits.ts').read_text(encoding='utf-8')
    if VERSION in kits:
        print('[OK] Nesa Momentum V3 already installed; skipping prerequisites.')
        if args.check: print('[CHECK] Files already patched.'); return
        # Icons and model can be recopied but no TypeScript changes on a second run.
        changes={}
        for src_name,dest in [('nesa.webp','public/icons/chars/nesa.webp'),('hammer-z.webp','public/icons/skills/hammer-z.webp'),('hammer-x.webp','public/icons/skills/hammer-x.webp'),('hammer-c.webp','public/icons/skills/hammer-c.webp'),('hammer-v.webp','public/icons/skills/hammer-v.webp')]:
            src=HERE/'nesa_momentum_assets'/src_name
            if src.is_file() and (not (root/dest).exists() or (root/dest).read_bytes()!=src.read_bytes()): changes[dest]=src.read_bytes()
        model = HERE/'nesa_optimized.vrm'
        model_dest='public/models/nesa.vrm'
        if model.is_file() and not (root/model_dest).exists():
            changes[model_dest]=model.read_bytes()
        commit(root,changes)
        return
    # Existing users may already have Nesa V2; the uninstalled Weight Passive is
    # bundled and applied automatically, but no other character's kit is reset.
    weight_cmd=[sys.executable,str(WEIGHT),str(root)]
    if args.check:
        if 'private get hammerWeightArmor()' not in (root/'src/game/fighter.ts').read_text(encoding='utf-8'):
            print('[CHECK] Weight Passive would be installed first; run without --check for full validation.')
            return
        print('[CHECK] Weight Passive already present; checking Momentum patch.')
    else:
        subprocess.run(weight_cmd,check=True)
    changes=modifications(root)
    print('Momentum files to update:',len(changes))
    if args.check:
        print('[CHECK] Dry-run successful. Nothing changed.');return
    commit(root,changes)
    print('[DONE] Nesa Momentum V3 + Weight Passive installed. Next: npx tsc --noEmit -p . && npm run dev')

if __name__=='__main__':
    try:main()
    except (PatchError, OSError, subprocess.CalledProcessError) as exc:
        print('INSTALL FAILED:',exc)
        sys.exit(1)
