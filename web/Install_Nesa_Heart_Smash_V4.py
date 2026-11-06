#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale: Nesa V4 model, pink FX, horizontal charge spin, cancel rules, three-charge C.

Run from Fight Royale's `web` folder:
    python Install_Nesa_Heart_Smash_V4.py
Or pass the project folder as an argument.

Requires Nesa Momentum V3 already installed. Standalone Python 3.9+, no pip packages.
Only edits game files that contain the expected anchors; backs up originals and
rolls back if the write fails. Can be run repeatedly without stacking patches.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse
import os
import shutil
import sys
import tempfile

MARKER = 'NESA_HEART_SMASH_V4'
FILES = ['src/game/kits.ts','src/game/fighter.ts','src/game/model.ts','src/game/game.ts','src/game/fx.ts']

class PatchError(RuntimeError): pass

def one(src, old, new, why):
    n=src.count(old)
    if n != 1: raise PatchError(f'{why}: expected exactly one anchor; found {n}')
    return src.replace(old,new,1)

def between(src, start, stop, new, why):
    x=src.find(start)
    y=src.find(stop,x+len(start)) if x>=0 else -1
    if x<0 or y<0: raise PatchError(f'{why}: expected section boundaries not found')
    return src[:x] + new + src[y:]

def root_at(val):
    base=Path(val).expanduser().resolve() if val else Path.cwd()
    for p in (base,base/'web'):
        if (p/'src/game/fighter.ts').is_file() and (p/'src/game/kits.ts').is_file():return p
    raise PatchError('Could not locate Fight Royale web folder. Run from web or supply its path.')

# The new hammer is modeled after the user's reference (rose steel barrel + gold star bezel
# around a radiant heart, gold/rose shaft), not an exact geometry transfer from a photo.
HEART_HAMMER = '''  private buildHammer() {
    // NESA_HEART_SMASH_V4: ornate carnival heart hammer. Proportions remain combat-sized.
    const h = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    this.nesaHammerPivot = h;
    // Reinforced striped shaft; top connects to the broad crosswise barrel.
    mesh(h, cyl(0.036, 0.043, 1.15, 12), this.tn("#392d42"), [0, 0.37, 0]);
    for (let i = 0; i < 8; i++)
      mesh(h, cyl(0.044, 0.044, 0.034, 12), this.tn(i % 2 ? "#f5b0d6" : "#f7d38d"), [0, -0.13 + 0.115 * i, 0]);
    mesh(h, sphere(0.067, 16), this.tn("#ffc4df"), [0, -0.25, 0]);
    mesh(h, cyl(0.078, 0.078, 0.14, 12), this.tn("#eeb772"), [0, 0.82, 0]);
    // Wide dark-rose steel barrel mounted perpendicular to the shaft.
    mesh(h, cyl(0.325, 0.325, 0.75, 20), this.tn("#56445e"), [0, 1.08, 0], [0, 0, PI / 2]);
    for (const side of [-1, 1]) {
      mesh(h, cyl(0.345, 0.345, 0.09, 20), this.tn("#ec89be"), [side * 0.28, 1.08, 0], [0, 0, PI / 2]);
      mesh(h, cyl(0.302, 0.302, 0.072, 20), this.tn("#8c698c"), [side * 0.38, 1.08, 0], [0, 0, PI / 2]);
      mesh(h, torus(0.25, 0.285), this.tn("#ffc481"), [side * 0.424, 1.08, 0], [0, PI / 2, 0]);
    }
    // Five-point golden star is only a bezel; the central motif is always HEART.
    const star = new THREE.Shape();
    for (let i = 0; i < 10; i++) {
      const a = Math.PI / 2 + i * Math.PI / 5;
      const r = i % 2 ? 0.22 : 0.36;
      const x = Math.cos(a) * r, y = Math.sin(a) * r;
      if (i === 0) star.moveTo(x, y); else star.lineTo(x, y);
    }
    star.closePath();
    const starGeo = new THREE.ExtrudeGeometry(star, { depth: 0.045, bevelEnabled: true,
      bevelSize: 0.013, bevelThickness: 0.012, bevelSegments: 2, curveSegments: 8 });
    mesh(h, starGeo, this.tn("#ffc176"), [0.44, 1.08, 0], [0, PI / 2, 0]);
    const heart = new THREE.Shape();
    heart.moveTo(0, -0.22);
    heart.bezierCurveTo(-0.12, -0.13, -0.29, 0.02, -0.23, 0.15);
    heart.bezierCurveTo(-0.16, 0.28, -0.045, 0.23, 0, 0.15);
    heart.bezierCurveTo(0.045, 0.23, 0.16, 0.28, 0.23, 0.15);
    heart.bezierCurveTo(0.29, 0.02, 0.12, -0.13, 0, -0.22);
    const gem = new THREE.ExtrudeGeometry(heart, { depth: 0.052, bevelEnabled: true,
      bevelSize: 0.023, bevelThickness: 0.027, bevelSegments: 3, curveSegments: 16 });
    mesh(h, gem, this.tn("#ff4fae"), [0.505, 1.08, 0], [0, PI / 2, 0]);
    mesh(h, gem.clone(), this.tn("#ffc9f0", false), [0.574, 1.09, 0], [0, PI / 2, 0], [0.63, 0.63, 0.38]);
    // Back face: a small rosy heart emblem on the metal cap.
    mesh(h, gem.clone(), this.tn("#ff8acf"), [-0.48, 1.08, 0], [0, -PI / 2, 0], [0.42, 0.42, 0.6]);
    mesh(h, sphere(0.09, 16), this.gem(), [0, 0.86, 0.17]);
    this.bladeBase = pivot(h, [0, 0.41, 0]);
    this.bladeTip = pivot(h, [0, 1.38, 0]);
    this.gripL = pivot(h, [0, 0.04, 0]);
    this.shieldNode = pivot(h, [0, 0.70, 0]);
    this.castPoint = this.bladeTip;
  }

'''

# Heart hit graphic visible from above and front: animated filled heart plus radiant outlines.
FX_HEART = '''  /** NESA_HEART_SMASH_V4: pink heart-shaped floor shockwave, visual-only, self-expiring. */
  heartSmash(pos: THREE.Vector3, radius = 2.7) {
    const group = new THREE.Group();
    group.position.set(pos.x, 0.082, pos.z);
    const shape = new THREE.Shape();
    shape.moveTo(0, -0.78);
    shape.bezierCurveTo(-0.28, -0.48, -0.98, -0.02, -0.77, 0.49);
    shape.bezierCurveTo(-0.55, 0.94, -0.10, 0.80, 0, 0.57);
    shape.bezierCurveTo(0.10, 0.80, 0.55, 0.94, 0.77, 0.49);
    shape.bezierCurveTo(0.98, -0.02, 0.28, -0.48, 0, -0.78);
    const geo = new THREE.ShapeGeometry(shape, 24);
    geo.rotateX(-Math.PI / 2);
    const fillMat = new THREE.MeshBasicMaterial({ color: '#ff4ba9', transparent: true,
      opacity: 0.36, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, depthWrite: false });
    const fill = new THREE.Mesh(geo, fillMat);
    (fill as any).ownsMat = true;
    group.add(fill);
    const outlinePoints = shape.getPoints(60);
    const edgeGeo = new THREE.BufferGeometry().setFromPoints(outlinePoints.map(p =>
      new THREE.Vector3(p.x, 0.025, -p.y)));
    const edgeMat = new THREE.LineBasicMaterial({ color: '#ffe0f5', transparent: true,
      opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false });
    const edge = new THREE.LineLoop(edgeGeo, edgeMat);
    group.add(edge);
    const inner = new THREE.LineLoop(edgeGeo, new THREE.LineBasicMaterial({ color: '#ff68ca',
      transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }));
    inner.scale.setScalar(0.76);
    inner.position.y = 0.035;
    group.add(inner);
    let age = 0;
    this.add(group, (dt) => {
      age += dt;
      const u = Math.min(1, age / 0.66);
      const e = 1 - Math.pow(1 - u, 3);
      group.scale.setScalar(0.24 + radius * 0.93 * e);
      fillMat.opacity = 0.33 * (1 - u);
      edgeMat.opacity = 0.98 * (1 - u * u);
      (inner.material as THREE.LineBasicMaterial).opacity = 0.7 * (1 - u);
      group.position.y = 0.082 + 0.014 * u;
      if (u >= 1) { edgeGeo.dispose(); geo.dispose(); edgeMat.dispose(); inner.material.dispose(); }
      return age < 0.66;
    });
    this.sparks(pos.clone().add(new THREE.Vector3(0, 0.20, 0)), '#ff83d0', 34, 6);
    this.sparks(pos.clone().add(new THREE.Vector3(0, 0.27, 0)), '#ffe4fb', 17, 5);
  }

'''

# A charged spinning hammer should sweep flat on the horizontal plane, not point upward.
SPIN_MODEL = '''    if (this.nesaHammerPivot) {
      // NESA_HEART_SMASH_V4: horizontal, Beyblade-style hammer shaft during charged spin.
      const value = THREE.MathUtils.clamp(this.nesaHammerScale, 1, 4);
      const current = this.nesaHammerPivot.scale.x;
      this.nesaHammerPivot.scale.setScalar(THREE.MathUtils.damp(current, value, value > current ? 8 : 13, dt));
      const flat = THREE.MathUtils.clamp(this.nesaSpinHorizontal, 0, 1);
      this.nesaHammerPivot.rotation.z = THREE.MathUtils.damp(this.nesaHammerPivot.rotation.z,
        -Math.PI * 0.5 * flat, flat > 0 ? 28 : 15, dt);
    }
'''

# New, simple C: grounded single-impact heart smash with three rechargeable uses.
C_ATTACK = '''    c: a({ name: "Pink Heart Smash", desc: "Three stored charges. One grounded heart-hammer smash per press with a bright pink heart shockwave; charges regenerate separately.",
      cd: 7.5, type: "strike", at: "self", wind: 0.36, active: 0.13, recover: 0.36,
      dmg: 172, guard: 57, knock: 8.7, stun: 0.62, heavy: true,
      delay: 0.035, radius: 2.72, style: "nesa_heart_slam", pose_w: "charge", pose_s: "heavy_s" }),'''

C_RESET = '''    this.nesaCCharges = 3;
    this.nesaCRechargeT = 0;
    this.nesaCArmed = true;
'''

def patch_kits(s):
    anchor='    c: a({ name: "GIGA BONK!",'
    p=s.find(anchor,s.index('function hammer():'))
    q=s.find('\n  };',p)
    if p<0 or q<0: raise PatchError('Nesa C skill anchor not found (expected Momentum V3)')
    # Replace just the last C property, not earlier skills or other kits.
    s=s[:p]+C_ATTACK+s[q:]
    return s

def patch_model(s):
    s=one(s,'  nesaHammerScale = 1;','  nesaHammerScale = 1;\n  nesaSpinHorizontal = 0;', 'hammer flat-spin property')
    s=between(s,'  private buildHammer() {','  private buildKatana() {',HEART_HAMMER,'heart hammer geometry')
    old='''    if (this.nesaHammerPivot) {
      const value = THREE.MathUtils.clamp(this.nesaHammerScale, 1, 4);
      const current = this.nesaHammerPivot.scale.x;
      this.nesaHammerPivot.scale.setScalar(THREE.MathUtils.damp(current, value, value > current ? 8 : 13, dt));
    }
'''
    s=one(s,old,SPIN_MODEL,'horizontal charge pose')
    # Preserve the no-foot-heavy patch if it is already installed, or incorporate it.
    if 'NESA_NO_FOOT_HEAVINESS_V1' not in s:
        old='''    if (this.kit === "hammer") {
      this.torso.rotation.x += 0.09 + 0.12 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.045 * moving;
      this.head.rotation.x -= 0.06;
      this.hips.position.y -= 0.035 + moving * 0.014;
      this.leg_l.rotation.x *= 0.79;
      this.leg_r.rotation.x *= 0.79;
    }
'''
        new='''    if (this.kit === "hammer") {
      // NESA_NO_FOOT_HEAVINESS_V1: burden in shoulders/arms, not dragging feet.
      this.torso.rotation.x += 0.08 + 0.10 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.04 * moving;
      this.head.rotation.x -= 0.05;
      this.hips.position.y -= 0.012 + moving * 0.004;
      this.leg_l.rotation.x *= 0.95;
      this.leg_r.rotation.x *= 0.95;
      this.arm_l.rotation.x -= 0.06 + 0.03 * moving;
      this.arm_r.rotation.x += 0.04 + 0.02 * moving;
      this.arm_l.rotation.z -= 0.06;
      this.arm_r.rotation.z += 0.04;
    }
'''
        s=one(s,old,new,'preserve light feet')
    return s

def patch_fx(s):
    s=one(s,'  ring(pos: THREE.Vector3, color: string, radius = 2, dur = 0.35, opacity = 0.9) {',
        FX_HEART+'  ring(pos: THREE.Vector3, color: string, radius = 2, dur = 0.35, opacity = 0.9) {','heart-shaped shockwave')
    s=one(s,'  private color: THREE.Color;\n','  private color: THREE.Color;\n  private life: number;\n','trail lifetime field')
    s=one(s,'  constructor(base: THREE.Object3D, tip: THREE.Object3D, color: string) {\n',
        '  constructor(base: THREE.Object3D, tip: THREE.Object3D, color: string, life = 0.16) {\n    this.life = life;\n','optional Nesa trail duration')
    s=one(s,'while (this.samples.length && this.samples[0].age > 0.16) this.samples.shift();',
        'while (this.samples.length && this.samples[0].age > this.life) this.samples.shift();', 'trail fade time')
    s=one(s,'Math.max(1 - s0.age / 0.16, 0), a1 = Math.max(1 - s1.age / 0.16, 0)',
        'Math.max(1 - s0.age / this.life, 0), a1 = Math.max(1 - s1.age / this.life, 0)', 'trail alpha')
    return s

def patch_fighter(s):
    s=one(s,'  private nesaSpinT = 0;',
        '''  private nesaSpinT = 0;
  // NESA_HEART_SMASH_V4: three individual C charges; recovery is one charge at a time.
  nesaCCharges = 3;
  nesaCRechargeT = 0;
  private nesaCArmed = true;
''','C charges fields')
    s=one(s,'    this.trail = new Trail(this.model.bladeBase, this.model.bladeTip, look.glow);',
        '''    this.trail = new Trail(this.model.bladeBase, this.model.bladeTip,
      this.kit === "hammer" ? "#ff53b9" : look.glow,
      this.kit === "hammer" ? 0.25 : 0.16);''','pink weapon trail')
    s=one(s,'''    return this.stateT >= Math.min(total * 0.60, this.atk.wind * 0.70);''',
        '''    // Upsie Daisie: immune to stun/knockback from the FIRST frame of its cast.
    // Every other hammer attack is vulnerable during its entire wind-up.
    return this.atkId === "x" || this.atkPhase >= 1;''','weight-armor timing')
    s=one(s,'    const total = Math.max(0.01, this.atk.wind + this.atk.active + this.atk.recover);\n',
        '', 'remove unused armor total')
    # Crowd control immunity also covers periodic paralyze and direct forced stagger.
    s=one(s,'if (st.jolt && this.bloodFestivalT <= 0 && !this.meteorFistArmor &&',
        'if (st.jolt && this.bloodFestivalT <= 0 && !this.meteorFistArmor && !this.hammerWeightArmor &&',
        'paralyze armor')
    s=one(s,'stagger(d: number) { if (this.knockedDown() || this.bloodFestivalT > 0 || this.meteorFistArmor) return;',
        'stagger(d: number) { if (this.knockedDown() || this.bloodFestivalT > 0 || this.meteorFistArmor || this.hammerWeightArmor) return;',
        'direct stagger armor')
    s=one(s,'pushBack(speed: number) { if (!this.meteorFistArmor)',
        'pushBack(speed: number) { if (!this.meteorFistArmor && !this.hammerWeightArmor)', 'pushback armor')
    s=one(s,'if (!this.stage && !this.meteorFistArmor && !this.knockedDown())',
        'if (!this.stage && !this.meteorFistArmor && !this.hammerWeightArmor && !this.knockedDown())',
        'clash pushback armor')
    # C charge regeneration in authoritative update only; avoid affecting other kits.
    s=one(s,'    for (const k in this.cooldowns) this.cooldowns[k] = Math.max(this.cooldowns[k] - dt, 0);',
        '''    for (const k in this.cooldowns) this.cooldowns[k] = Math.max(this.cooldowns[k] - dt, 0);
    if (this.kit === "hammer") {
      // NESA_HEART_SMASH_V4: one charge returns every 7.5 seconds, max three.
      if (this.nesaCCharges < 3) {
        this.nesaCRechargeT = Math.max(0, this.nesaCRechargeT - dt);
        if (this.nesaCRechargeT <= 0) {
          this.nesaCCharges = Math.min(3, this.nesaCCharges + 1);
          this.nesaCRechargeT = this.nesaCCharges < 3 ? 7.5 * this.cdMult : 0;
        }
      } else this.nesaCRechargeT = 0;
      this.cooldowns.c = this.nesaCCharges > 0 ? 0 : this.nesaCRechargeT;
      if (this.intent.skill !== "c") this.nesaCArmed = true;
    }
''','charge regeneration')
    # Tooltip, visible skill active when stock > 0. Additional network state is appended.
    s=one(s,'    if ((this.cooldowns[k] ?? 1) > 0) return;\n    const free =',
        '''    if (this.kit === "hammer" && k === "c" &&
        (!this.nesaCArmed || this.nesaCCharges <= 0)) return;
    if ((this.cooldowns[k] ?? 1) > 0) return;
    const free =''',
        'check C stock before cast')
    s=one(s,'    // The keg\'s cooldown starts when it explodes (the arena sets it).\n    this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 : this.attacks[k].cd * this.cdMult;',
        '''    // The keg's cooldown starts when it explodes (the arena sets it).
    if (this.kit === "hammer" && k === "c") {
      this.nesaCArmed = false;
      if (this.nesaCCharges === 3) this.nesaCRechargeT = 7.5 * this.cdMult;
      this.nesaCCharges--;
      this.cooldowns.c = this.nesaCCharges > 0 ? 0 : this.nesaCRechargeT;
    } else this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 : this.attacks[k].cd * this.cdMult;''',
        'consume C charge')
    # Cancellable pre-swing using block; preserves reactability; X never cancels.
    s=one(s,'    const w = a.wind, ac = a.active, r = a.recover;\n    if (a.mode === "leap"',
        '''    const w = a.wind, ac = a.active, r = a.recover;
    if (this.kit === "hammer" && this.atkId !== "x" && this.atkPhase === 0 &&
        this.stateT < w && this.intent.block) {
      // Pre-swing cancel is intentional; this move did NOT deal any damage.
      // Refund a stored Heart Smash charge, but only before its impact window.
      if (this.atkId === "c") {
        this.nesaCCharges = Math.min(3, this.nesaCCharges + 1);
        if (this.nesaCCharges === 3) this.nesaCRechargeT = 0;
        this.cooldowns.c = 0;
      }
      this.atk = null; this.atkId = ""; this.buffered = false;
      this.holding = false; this.comboNext = "l1"; this.comboTimer = 0;
      this.setState(S.BLOCK);
      return;
    }
    if (a.mode === "leap"''',
        'block cancels pre-windup')
    # Dash is ordinarily allowed at every attack phase. For Nesa only, early cancel
    # valid; committed hammer/kick cannot be dash-canceled.
    s=one(s,'    if (![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(this.state)) return; // dash cancels attacks, not hitstun',
        '''    if (![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(this.state)) return; // dash cancels attacks, not hitstun
    if (this.kit === "hammer" && this.state === S.ATTACK &&
        (this.atkId === "x" || this.atkPhase !== 0 || !this.atk || this.stateT >= this.atk.wind)) return;''',
        'dash only before committed hammer swing')
    s=one(s,'    if (this.state !== S.IDLE) { if (this.state === S.ATTACK) this.finishAttack(); this.holding = false; this.setState(S.IDLE); }',
        '''    if (this.state !== S.IDLE) {
      if (this.state === S.ATTACK) {
        if (this.kit === "hammer" && this.atkId === "c") {
          this.nesaCCharges = Math.min(3, this.nesaCCharges + 1);
          if (this.nesaCCharges === 3) this.nesaCRechargeT = 0;
          this.cooldowns.c = 0;
        }
        if (this.kit === "hammer") {
          this.atk = null; this.atkId = ""; this.comboNext = "l1"; this.comboTimer = 0;
          this.buffered = false;
        } else this.finishAttack();
      }
      this.holding = false; this.setState(S.IDLE);
    }''','pre-swing dash cancel')
    # Apply charge pose and pink trail during any damaging hammer attack.
    s=one(s,'    this.trail.emitting = this.state === S.ATTACK && !!a && (a.type === "melee" || a.style === "iron_tempest") &&',
        '''    this.trail.emitting = this.state === S.ATTACK && !!a &&
      (a.type === "melee" || a.style === "iron_tempest" || this.kit === "hammer") &&''','trail for C/ult as well')
    s=one(s,'      this.model.nesaHammerScale = attack?.style === "nesa_high_striker" &&',
        '''      this.model.nesaSpinHorizontal = attack?.style === "nesa_spin" ?
        THREE.MathUtils.clamp(this.stateT / Math.max(0.01, attack.wind), 0, 1) : 0;
      this.model.nesaHammerScale = attack?.style === "nesa_high_striker" &&''','horizontal hammer pose during spins')
    s=one(s,'    } else this.nesaSpinYaw = 0;\n    this.model.rotation.y',
        '    } else { this.nesaSpinYaw = 0; this.model.nesaSpinHorizontal = 0; }\n    this.model.rotation.y',
        'reset flat hammer')
    # Add network fields last - old snapshots still supported.
    s=one(s,'+this.nesaSpinYaw.toFixed(3), +this.model.nesaHammerScale.toFixed(2)];',
        '+this.nesaSpinYaw.toFixed(3), +this.model.nesaHammerScale.toFixed(2),\n      this.nesaCCharges, +this.nesaCRechargeT.toFixed(2), +this.model.nesaSpinHorizontal.toFixed(2)];',
        'network charge state')
    s=one(s,'    this.model.nesaHammerScale = s.length > 43 ? s[43] : 1;',
        '''    this.model.nesaHammerScale = s.length > 43 ? s[43] : 1;
    this.nesaCCharges = s.length > 44 ? s[44] : 3;
    this.nesaCRechargeT = s.length > 45 ? s[45] : 0;
    this.model.nesaSpinHorizontal = s.length > 46 ? s[46] : 0;''',
        'network remote C charges and flat spin')
    # Reset charges when reviving / KO round: new character gets full stocks.
    reset = '    this.nesaAirHolding = false; this.nesaAirChargeT = 0; this.nesaSpinYaw = 0;'
    if s.count(reset) != 2:
        raise PatchError(f'reset Nesa C state: expected two reset points, found {s.count(reset)}')
    s=s.replace(reset,reset+'\n    this.nesaCCharges = 3; this.nesaCRechargeT = 0; this.nesaCArmed = true;\n    this.model.nesaSpinHorizontal = 0;')
    return s

def patch_game(s):
    s=one(s,'      case "ring": fx.ring(v3(a[0]), a[1], a[2], a[3], a[4]); break;',
        '''      case "ring": fx.ring(v3(a[0]), a[1], a[2], a[3], a[4]); break;
      case "heartSmash": fx.heartSmash(v3(a[0]), a[1]); break;''',
        'replicated heart smash VFX')
    s=one(s,'      case "slam":\n      case "cleave":',
        '''      case "nesa_heart_slam":
        this.fxp("heartSmash", g, radius);
        this.fxp("flash", g.clone().setY(0.28), "#ff80cd", 0.55, 0.20, 0.88);
        this.fxp("sparks", g.clone().setY(0.22), "#ffe0f3", 20, 7, [0, 1, 0]);
        this.add_trauma(0.35);
        break;
      case "slam":
      case "cleave":''',
        'C pink heart impact')
    # Every hammer swing emits pink sparkles and a trail, including charged attacks.
    s=one(s,'    const el = f.look.element;\n    const big =',
        '''    if (f.kit === "hammer") {
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("sparks", tip, "#ff75ce", 14, 4);
      this.fxp("flash", tip, "#ffb8e7", 0.20, 0.13, 0.65);
    }
    const el = f.look.element;
    const big =''',
        'pink attack particles')
    s=one(s,'    const me = this.local;\n    const boss =',
        '    const me = this.local;\n    const boss =', 'HUD noop')
    # A useful charge count is shown in the existing skill label rather than new controls.
    s=one(s,'        return { key: k, id: a.id, name: a.name, cd: me.cooldowns[k], max: me.attacks[k].cd * me.cdMult };',
        '''        if (me.kit === "hammer" && k === "c") return {
          key: k, id: a.id, name: `${a.name} ×${me.nesaCCharges}`,
          cd: me.nesaCCharges > 0 ? 0 : me.nesaCRechargeT,
          max: 7.5 * me.cdMult,
        };
        return { key: k, id: a.id, name: a.name, cd: me.cooldowns[k], max: me.attacks[k].cd * me.cdMult };''',
        'show remaining C charges in HUD')
    return s

def main():
    ap=argparse.ArgumentParser(description='Nesa heart hammer, spin, C stacks, pink trail, pre-swing cancels')
    ap.add_argument('project', nargs='?', help='Fight Royale project web folder')
    ap.add_argument('--check', action='store_true', help='Validate without modifying any file')
    args=ap.parse_args()
    root=root_at(args.project)
    print('Fight Royale web folder:', root)
    if 'NESA_MOMENTUM_V3' not in (root/'src/game/kits.ts').read_text(encoding='utf-8'):
        raise PatchError('Requires the earlier Nesa Momentum V3 install. No changes were made.')
    functions={'src/game/kits.ts':patch_kits,'src/game/model.ts':patch_model,
        'src/game/fx.ts':patch_fx,'src/game/fighter.ts':patch_fighter,'src/game/game.ts':patch_game}
    changes={}
    for rel in FILES:
        src=(root/rel).read_text(encoding='utf-8')
        if f'// {MARKER}' in src:
            print('[SKIP] Already patched:',rel)
            continue
        dst=functions[rel](src)
        if dst != src:
            changes[rel]=(f'// {MARKER}\n'+dst).encode('utf-8')
    print('Files to update:',len(changes))
    for rel in changes: print('  ',rel)
    if args.check:
        print('[CHECK] All required anchors validated. No files changed.')
        return
    if not changes:
        print('[OK] Nesa Heart Smash V4 already installed.')
        return
    bak=root/'.nesa_installer_backups'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    bak.mkdir(parents=True,exist_ok=False)
    for rel in changes:
        dst=bak/rel; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/rel,dst)
    written=[]
    try:
        for rel,data in changes.items():
            dst=root/rel
            with tempfile.NamedTemporaryFile(dir=dst.parent,delete=False) as f:
                f.write(data); temp=Path(f.name)
            os.replace(temp,dst)
            written.append(rel)
    except Exception:
        for rel in written: shutil.copy2(bak/rel,root/rel)
        raise
    print('[DONE] Nesa Heart Smash V4 installed. Backups:',bak)
    print('Run: npx tsc --noEmit -p . && npm run dev')

if __name__=='__main__':
    try: main()
    except Exception as e:
        print('INSTALL FAILED:',e)
        sys.exit(1)
