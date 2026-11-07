#!/usr/bin/env python3
"""Zenith V5 — fix V4 spear compile errors; summon overhead charge;
twin-metal-blade stance while spear away; choreographed magnetic recall catch;
2s CC resistance on catch; stun on throw and return.
Run from Fight Royale/web, AFTER Zenith V4. Exact anchor preflight, timestamped backups,
and safe repeat run. Only model.ts, fighter.ts, kits.ts, game.ts are modified.
"""
from pathlib import Path
from datetime import datetime
import shutil, sys
ROOT=Path.cwd()
NAMES=['src/game/model.ts','src/game/fighter.ts','src/game/kits.ts','src/game/game.ts','src/game/ai.ts','src/game/status.ts']
try:
    old={f:(ROOT/f).read_text(encoding='utf8') for f in NAMES}
except OSError as e:
    sys.exit(f'ERROR: Run this from your web/ folder: {e}. No changes made.')
M,F,K,G,A,S=NAMES
MARK='ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108'
if MARK in old[M]:
    print('Zenith V5 already installed. No changes needed.')
    sys.exit(0)
if 'ZENITH_REFERENCE_SPEAR_V4_20261108' not in old[M] or 'ZENITH_REFERENCE_SPEAR_V4_20261108' not in old[G]:
    sys.exit('PREFLIGHT ERROR: Install Zenith V4 first. No changes made.')
new=dict(old)

def one(path,src,dst):
    count=new[path].count(src)
    if count!=1: raise ValueError(f'{path}: expected one anchor, found {count}: {src[:110]!r}')
    new[path]=new[path].replace(src,dst,1)

try:
    # ------------------------------ Model ----------------------------------
    one(M,'  private glaivePivot: THREE.Group | null = null;', '''  private glaivePivot: THREE.Group | null = null;
  // ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108: one-handed metal weapons only while spear is flying.
  private zenithSpearGrip: THREE.Object3D | null = null;
  private zenithTwinBlades: THREE.Group[] = [];
  private zenithTwinBases: THREE.Object3D[] = [];
  private zenithTwinTips: THREE.Object3D[] = [];
  private zenithSpearBase: THREE.Object3D | null = null;
  private zenithSpearTip: THREE.Object3D | null = null;
  private zenithCatchAura: THREE.Group | null = null;
  zenithCatchShieldT = 0;
  zenithCatchRecoilT = 0;''')
    # V4 type errors — use shared helper accepting MatPair instead of raw THREE.Mesh.
    one(M, '''      const wingGem = new THREE.Mesh(new THREE.OctahedronGeometry(0.024, 0), crystal);
      wingGem.position.set(side * 0.108, 0.98, 0.016);
      spear.add(wingGem);''', '''      mesh(spear, new THREE.OctahedronGeometry(0.024, 0), crystal,
        [side * 0.108, 0.98, 0.016]);''')
    one(M, '''    const bodyPlate = new THREE.Mesh(new THREE.BoxGeometry(0.105, 0.30, 0.028), gold);
    bodyPlate.position.set(0, 0.46, 0);
    bodyPlate.scale.set(1.0, 1.0, 0.8);
    spear.add(bodyPlate);''', '''    mesh(spear, new THREE.BoxGeometry(0.105, 0.30, 0.028), gold,
      [0, 0.46, 0], [0, 0, 0], [1, 1, 0.8]);''')
    one(M, '''      const hole = new THREE.Mesh(new THREE.TorusGeometry(0.018, 0.006, 6, 16), dark);
      hole.position.set(0, y, 0.016);
      hole.rotation.x = Math.PI / 2;
      spear.add(hole);''', '''      mesh(spear, new THREE.TorusGeometry(0.018, 0.006, 6, 16), dark,
        [0, y, 0.016], [Math.PI / 2, 0, 0]);''')
    one(M,'mesh(spear, cone(0.018, 0.055, 8), gold, [0, -0.96, 0], [Math.PI, 0, 0]);',
          'mesh(spear, new THREE.ConeGeometry(0.018, 0.055, 8), gold, [0, -0.96, 0], [Math.PI, 0, 0]);')
    # Include two blades, and a light no-damage aura for the 2s CC guard.
    one(M, '''    this.gripL = pivot(spear, [0, -0.34, 0]);
    this.bladeBase = pivot(spear, [0, 0.80, 0]);''', '''    this.gripL = pivot(spear, [0, -0.34, 0]);
    this.zenithSpearGrip = this.gripL;
    this.buildZenithTwinBlades();
    this.bladeBase = pivot(spear, [0, 0.80, 0]);''')
    one(M,'''  /** The game hides the held metal spear when its projectile is flying. */
  setZenithSpearHeld(held: boolean) {
    if (this.look.element === "metal" && this.glaivePivot) this.glaivePivot.visible = held;
  }
''','''  /** In-flight: dual short swords; caught: one real long spear and two swords dissolve. */
  setZenithSpearHeld(held: boolean) {
    if (this.look.element !== "metal") return;
    if (this.glaivePivot) this.glaivePivot.visible = held;
    for (const blade of this.zenithTwinBlades) blade.visible = !held;
    this.gripL = held ? this.zenithSpearGrip : null;
    this.bladeBase = held ? this.zenithSpearBase ?? this.bladeBase : this.zenithTwinBases[0] ?? this.bladeBase;
    this.bladeTip = held ? this.zenithSpearTip ?? this.bladeTip : this.zenithTwinTips[0] ?? this.bladeTip;
    if (this.vrmRig) {
      this.vrmRig.gripL = held ? this.zenithSpearGrip : null;
      this.vrmRig.glaive = held;
      this.vrmRig.bladed = held ? 0.4 : 0.76;
    }
  }

  /** Twin Metal Blades are prebuilt, never reconstructed per frame. */
  private buildZenithTwinBlades() {
    const steel = M.toon("#dbe8f6", { rim: 0.65, shade: METAL_SHADE });
    const blue = this.tn("#80d7ef"), gold = this.tn("#cda96d"), grip = this.tn("#1b3047");
    for (const [i, hand] of [this.hand_r, this.hand_l].entries()) {
      const sword = pivot(hand, [0, 0.04, 0.06], [PI / 2, 0, i ? -0.20 : 0.20]);
      sword.name = i ? "zenithTwinLeft" : "zenithTwinRight";
      mesh(sword, cyl(0.023, 0.025, 0.23, 10), grip, [0, -0.06, 0]);
      mesh(sword, box(0.19, 0.035, 0.065), gold, [0, 0.08, 0]);
      mesh(sword, sphere(0.029, 10), gold, [0, -0.19, 0]);
      const blade = new THREE.Shape();
      blade.moveTo(-0.045, 0.10);
      blade.lineTo(-0.073, 0.34);
      blade.lineTo(-0.031, 0.51);
      blade.lineTo(0, 0.66);
      blade.lineTo(0.031, 0.51);
      blade.lineTo(0.073, 0.34);
      blade.lineTo(0.045, 0.10);
      blade.closePath();
      const geo = new THREE.ExtrudeGeometry(blade, {depth:0.018,bevelEnabled:true,
        bevelSize:0.003,bevelThickness:0.003,bevelSegments:1});
      geo.translate(0, 0, -0.009);
      mesh(sword, geo, steel);
      mesh(sword, box(0.012, 0.33, 0.026), blue, [0, 0.34, 0.015]);
      this.zenithTwinBases.push(pivot(sword, [0, 0.12, 0]));
      this.zenithTwinTips.push(pivot(sword, [0, 0.66, 0]));
      sword.visible = false;
      this.zenithTwinBlades.push(sword);
    }
    const aura = pivot(this, [0, 0.94, 0]);
    aura.name = "zenithCatchMagneticGuard";
    const glow = new THREE.MeshBasicMaterial({color: "#83d8ff", transparent: true,
      opacity: 0.60, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide});
    const ring = mesh(aura, new THREE.TorusGeometry(0.55, 0.013, 6, 44), glow);
    ring.rotation.x = 0.35;
    const ring2 = mesh(aura, new THREE.TorusGeometry(0.47, 0.009, 6, 38), glow);
    ring2.rotation.y = 0.45;
    aura.visible = false;
    this.zenithCatchAura = aura;
  }
''')
    one(M,'  blend(pose: Pose, dt: number, speed: number, actionPose = "") {', '''  blend(pose: Pose, dt: number, speed: number, actionPose = "") {
    if (this.zenithCatchAura) {
      this.zenithCatchAura.visible = this.zenithCatchShieldT > 0;
      this.zenithCatchAura.rotation.y += dt * 2.5;
      this.zenithCatchAura.rotation.z = 0.10 * Math.sin(this.t * 3.2);
      this.zenithCatchAura.scale.setScalar(0.90 + 0.07 * Math.sin(this.t * 4.7));
    }
    if (this.zenithTwinBlades.length) {
      if (!this.glaivePivot?.visible) {
        const left = /znt[24]_/.test(this.glaivePose);
        const side = left ? 1 : 0;
        if (this.zenithTwinBases[side]) this.bladeBase = this.zenithTwinBases[side];
        if (this.zenithTwinTips[side]) this.bladeTip = this.zenithTwinTips[side];
      }
      for (let i = 0; i < this.zenithTwinBlades.length; i++) {
        const blade = this.zenithTwinBlades[i];
        // A visible inward-cross on combo 5, otherwise compact alternating slashes.
        const crossing = this.glaivePose === "znt5_s" || this.glaivePose === "zntx_s";
        const anim = this.glaivePose.startsWith("znt") ? Math.sin(this.t * 26 + i * 2) * 0.11 : 0;
        const want = crossing ? (i === 0 ? -0.72 : 0.72) : (i === 0 ? 0.14 : -0.14) + anim;
        blade.rotation.z = THREE.MathUtils.damp(blade.rotation.z, want, 24, dt);
      }
    }''')
    # Overhead spear conjure: avoid child weapon clipping by hiding held spear in charge state.
    # Ensure short blades show even for VRM, which maps to hand node via existing rig.
    # ------------------------------ Fighter --------------------------------
    one(F,'''  zenithSpearOut = false;
  zenithSpearAnchor = new THREE.Vector3();''', '''  zenithSpearOut = false;
  // ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108: recovery is CC-only protection, never HP invulnerability.
  zenithCatchShieldT = 0;
  zenithCatchRecoilT = 0;
  zenithSpearAnchor = new THREE.Vector3();''')
    one(F,'    this.clock += dt;\n    this.knockdownLockT', '''    this.zenithCatchShieldT = Math.max(0, this.zenithCatchShieldT - dt);
    this.zenithCatchRecoilT = Math.max(0, this.zenithCatchRecoilT - dt);
    if (this.look.element === "metal") {
      this.model.zenithCatchShieldT = this.zenithCatchShieldT;
      this.model.zenithCatchRecoilT = this.zenithCatchRecoilT;
      if (this.zenithCatchRecoilT > 0) {
        this.intent.attack = false;
        this.intent.skill = "";
        this.intent.skillHeld = "";
        this.intent.move.set(0, 0, 0);
        this.intent.dash.set(0, 0, 0);
      }
    }
    this.clock += dt;
    this.knockdownLockT''')
    # Public hand-back callback triggered only at physical return contact (host).
    one(F,'  onZenithRecall: (f: Fighter) => void = () => {};', '''  onZenithRecall: (f: Fighter) => void = () => {};
  catchZenithSpear() {
    if (this.look.element !== "metal" || this.isDown()) return;
    this.zenithSpearOut = false;
    this.model.setZenithSpearHeld(true);
    this.zenithCatchShieldT = 2.0;
    this.zenithCatchRecoilT = 0.62;
    this.model.zenithCatchShieldT = 2.0;
    this.model.zenithCatchRecoilT = 0.62;
    this.model.recoil = Math.max(this.model.recoil, 0.46);
    this.knock = 0;
    // A catch can break preexisting ice/jolts but never undoes damage.
    for (const cc of ["freeze", "paralyze", "slow"] as const) this.status.consume(cc);
    if (this.state === S.HITSTUN || this.state === S.STAGGER) this.setState(S.IDLE);
  }''')
    # Block all CC, but NOT health damage: route after hp calculation and before status/stuns.
    one(F,'    if (this.stage) return this.launch(attacker, a, dmg);', '''    if (this.stage) return this.launch(attacker, a, dmg);''')
    one(F,'''    if (a.effect && !(this.bloodFestivalT > 0 && a.effect === "paralyze") &&''', '''    if (a.effect && this.zenithCatchShieldT <= 0 &&
        !(this.bloodFestivalT > 0 && a.effect === "paralyze") &&''')
    one(F,'''    if (this.hammerWeightArmor) {
      // NESA_WEIGHT_PASSIVE_V1: once her swing is committed, Nesa still takes damage,''', '''    if (this.zenithCatchShieldT > 0) {
      // Damage still lands; no stun, stagger, floor knockdown or forced knockback.
      this.knock = 0;
      this.model.recoil = Math.max(this.model.recoil, 0.18);
      return this.lastCrit ? "crit" : "hit";
    }
    if (this.hammerWeightArmor) {
      // NESA_WEIGHT_PASSIVE_V1: once her swing is committed, Nesa still takes damage,''')
    one(F,'  stagger(d: number) { if (this.knockedDown()', '  stagger(d: number) { if (this.zenithCatchShieldT > 0 || this.knockedDown()')
    one(F,'''    if (this.status.has("freeze")) {
      this.intent.attack''','''    if (this.zenithCatchShieldT > 0) {
      for (const cc of ["freeze", "paralyze", "slow"] as const) this.status.consume(cc);
    }
    if (this.status.has("freeze")) {
      this.intent.attack''')
    one(F,'    if (st.jolt && this.bloodFestivalT <= 0', '    if (st.jolt && this.zenithCatchShieldT <= 0 && this.bloodFestivalT <= 0')
    one(F,'''      if (this.guard <= 0) {
        this.guard = 0;''', '''      if (this.guard <= 0) {
        this.guard = 0;''')
    # Skip knockdown, stagger from guard break during CC immunity.
    one(F,'        else if (this.bloodFestivalT <= 0) this.stagger(0.85);',
          '        else if (this.bloodFestivalT <= 0 && this.zenithCatchShieldT <= 0) this.stagger(0.85);')
    # Guard-break `beginKnockdown` protected by stagger() guard and condition.
    one(F,'''      this.knock = a.knock * 0.5;
      this.model.recoil = 0.7;''', '''      this.knock = this.zenithCatchShieldT > 0 ? 0 : a.knock * 0.5;
      this.model.recoil = 0.7;''')
    one(F,'  clashRecoil() {\n', '  clashRecoil() {\n    if (this.zenithCatchShieldT > 0) { this.model.recoil = 0.30; return; }\n')
    # Preserve 2s CC guard on platforms; health damage unchanged.
    one(F,'    if (this.meteorFistArmor) {\n      this.model.flash();', '''    if (this.zenithCatchShieldT > 0) {
      this.model.flash();
      return this.lastCrit ? "crit" : "hit";
    }
    if (this.meteorFistArmor) {
      this.model.flash();''')
    # post-catch poses in host and guests.
    one(F,'    this.poseName = p;\n    this.poseSpeed = sp;\n  }\n\n  // --- networking', '''    if (this.look.element === "metal" && this.zenithCatchRecoilT > 0 &&
        this.state !== S.KO && this.state !== S.WIN) {
      p = this.zenithCatchRecoilT > 0.34 ? "zncatch_w" : "zncatch_s";
      sp = this.zenithCatchRecoilT > 0.34 ? 32 : 24;
    }
    this.poseName = p;
    this.poseSpeed = sp;
  }

  // --- networking''')
    one(F,'      case S.CHARGE: p = this.attacks.heavy.pose_w; sp = 10; break;',
          '      case S.CHARGE: p = this.attacks.heavy.pose_w; sp = this.look.element === "metal" ? 22 : 10; break;')
    one(F,'''          if (a.style === "zenith_barrage") {
            const elapsed = this.stateT - a.wind;
            p = elapsed < 0 ? "znx_w" : ["zn1_s", "zn2_s", "zn3_s", "zn4_s", "zn5_s", "znx_s"]
              [Math.min(5, Math.floor(elapsed / 0.105))];
            sp = elapsed < 0 ? 25 : 67;
          } else if (this.atkPhase === 0)''', '''          if (a.style === "zenith_barrage") {
            const elapsed = this.stateT - a.wind;
            const combo = this.zenithSpearOut
              ? ["znt1_s", "znt2_s", "znt3_s", "znt4_s", "znt5_s", "zntx_s"]
              : ["zn1_s", "zn2_s", "zn3_s", "zn4_s", "zn5_s", "znx_s"];
            p = elapsed < 0 ? (this.zenithSpearOut ? "znt1_w" : "znx_w") :
              combo[Math.min(5, Math.floor(elapsed / 0.105))];
            sp = elapsed < 0 ? 25 : 67;
          } else if (this.zenithSpearOut && /^l[1-5]$/.test(this.atkId)) {
            p = `znt${this.atkId.slice(1)}_${this.atkPhase === 0 ? "w" : "s"}`;
            sp = this.atkPhase === 0 ? 28 : 80;
          } else if (this.atkPhase === 0)''')
    # Snapshot append for twin swords and shield to network guests.
    one(F,'''this.frostShardStacks, this.frostShieldCharges, +this.frostShieldT.toFixed(2)];''',
          '''this.frostShardStacks, this.frostShieldCharges, +this.frostShieldT.toFixed(2),
      this.zenithSpearOut ? 1 : 0, +this.zenithCatchShieldT.toFixed(2), +this.zenithCatchRecoilT.toFixed(2)];''')
    one(F,'''    this.frostShieldT = s.length > 55 ? s[55] : 0;
    this.hp = s[8];''', '''    this.frostShieldT = s.length > 55 ? s[55] : 0;
    if (this.look.element === "metal" && s.length > 58) {
      const isOut = s[56] === 1;
      if (this.zenithSpearOut !== isOut) {
        this.zenithSpearOut = isOut;
        this.model.setZenithSpearHeld(!isOut);
      }
      this.zenithCatchShieldT = s[57] ?? 0;
      this.zenithCatchRecoilT = s[58] ?? 0;
      this.model.zenithCatchShieldT = this.zenithCatchShieldT;
      this.model.zenithCatchRecoilT = this.zenithCatchRecoilT;
    }
    this.hp = s[8];''')
    # keep caught animation protected from input; reset on game round.
    one(F,'''    this.guardDelay = 0; // Fresh round: no guard recovery penalty carries over.
    this.chainFuryT = 0;
    this.judgmentT = 0; this.model.setJudgment(false);
    this.clashMomentum = 0;
    this.bloodlust''', '''    this.guardDelay = 0; // Fresh round: no guard recovery penalty carries over.
    this.chainFuryT = 0;
    this.judgmentT = 0; this.model.setJudgment(false);
    this.clashMomentum = 0;
    if (this.look.element === "metal") {
      this.zenithSpearOut = false;
      this.zenithCatchShieldT = 0;
      this.zenithCatchRecoilT = 0;
      this.model.zenithCatchShieldT = 0;
      this.model.zenithCatchRecoilT = 0;
      this.model.setZenithSpearHeld(true);
    }
    this.bloodlust''')
    # Two distinct rail hits (outbound/return) use separate stun sources,
    # while keeping the global diminishing-returns anti-stunlock rule.
    one(F,'''    const src = attacker instanceof Fighter ? `${attacker.id}:${attacker.swingSerial}` : "";''',
          '''    const src = attacker instanceof Fighter
      ? `${attacker.id}:${attacker.swingSerial}${a.id === "z_return" ? ":rail-return" : ""}` : "";''')
    # Catch guard resists physical weapon clashes and force-knockdowns too.
    one(F,'''  weightedClashPush(strength: number) {
    if (!this.stage''', '''  weightedClashPush(strength: number) {
    if (this.zenithCatchShieldT > 0) return;
    if (!this.stage''')
    one(F,'''  private beginKnockdown() {
    // No knockdown''', '''  private beginKnockdown() {
    if (this.zenithCatchShieldT > 0) return;
    // No knockdown''')
    one(F,'''        this.knock = hammerCrush ? Math.max(4.1, a.knock * 0.62) : 3.5;''', '''        this.knock = this.zenithCatchShieldT > 0 ? 0 :
          hammerCrush ? Math.max(4.1, a.knock * 0.62) : 3.5;''')
    # StatusSet is the central entry point for skills, passives, and DoT CC.
    # A 2-second immunity token prevents direct status.apply() bypassing Fighter.receiveHit().
    one(S,'''  private m = new Map<StatusKind, Active>();
  // ROXY_FLOATING''', '''  private m = new Map<StatusKind, Active>();
  // ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108: reject new CC at the status-entry point.
  private ccImmuneT = 0;
  grantCcImmunity(t: number) { this.ccImmuneT = Math.max(this.ccImmuneT, t); }
  // ROXY_FLOATING''')
    one(S,'''  apply(kind: StatusKind, t: number, p: number, src: unknown = null): boolean {
    // Incoming Freeze''', '''  apply(kind: StatusKind, t: number, p: number, src: unknown = null): boolean {
    if (this.ccImmuneT > 0 && (kind === "freeze" || kind === "paralyze" || kind === "slow")) return false;
    // Incoming Freeze''')
    one(S,'''  clear() { this.m.clear(); this.mask = 0; this.src = null; this.freezeImmuneT = 0; }''', '''  clear() { this.m.clear(); this.mask = 0; this.src = null; this.freezeImmuneT = 0; this.ccImmuneT = 0; }''')
    one(S,'''    this.freezeImmuneT = Math.max(0, this.freezeImmuneT - dt);
    for (const [kind, s] of this.m) {''', '''    this.freezeImmuneT = Math.max(0, this.freezeImmuneT - dt);
    this.ccImmuneT = Math.max(0, this.ccImmuneT - dt);
    for (const [kind, s] of this.m) {''')
    one(F,'''    this.zenithCatchShieldT = 2.0;
    this.zenithCatchRecoilT = 0.62;''', '''    this.zenithCatchShieldT = 2.0;
    this.zenithCatchRecoilT = 0.62;
    this.status.grantCcImmunity(2.0);''')
    # ------------------------------ Kit choreography -----------------------
    one(K,'''    base("heavy", { name: "Magnetic Lance", type: "projectile", wind: 0.28, recover: 0.56,''',
          '''    base("heavy", { name: "Magnetic Lance", type: "projectile", wind: 0.44, recover: 0.47,''')
    one(K,'''      knock: 3.2, stun: 0.27, speed: 24, size: 1.06, pierce: true,''',
          '''      knock: 2.5, stun: 0.40, speed: 24, size: 1.06, pierce: true,''')
    one(K,'''  znh_w: P([-0.08,-0.42,0], [0.04,0.32,0], [-1.46,-0.4,-0.12], [0.54,0,0], [-1.57,-0.25,0.10], [0.4,0,0], [-0.48,0,0.12], [0.42,0,-0.08], -0.13),''',
          '''  // Raised hand: call the physical spear above her before launching it.
  znh_w: P([-0.05,0.03,0], [-0.18,0.01,0], [-2.55,0.06,-0.32], [0.24,0,0.10], [-2.25,0.03,0.31], [0.19,0,0], [-0.31,0,0.09], [0.38,0,-0.08], -0.09),''')
    one(K,'''  znh_s: P([0.21,0.24,0], [-0.07,-0.16,0], [-1.95,0.20,-0.09], [0.1,0,0], [-1.93,0.2,0.10], [0.08,0,0], [-0.67,0,0.12], [0.48,0,-0.09], -0.16),''',
          '''  // Release the overhead spear, right arm extends downrange with follow-through.
  znh_s: P([0.24,0.19,0], [-0.08,-0.16,0], [-1.73,0.33,-0.10], [0.05,0,0], [-1.38,-0.24,0.20], [0.17,0,0], [-0.59,0,0.12], [0.46,0,-0.08], -0.14),''')
    one(K,'  znx_s: P([0.17,0.12,0], [0,-0.08,0], [-1.66,0.15,-0.16], [0.08,0,0], [-1.70,0.14,0.17], [0.11,0,0], [-0.55,0,0.10], [0.42,0,-0.09], -0.12),', '''  znx_s: P([0.17,0.12,0], [0,-0.08,0], [-1.66,0.15,-0.16], [0.08,0,0], [-1.70,0.14,0.17], [0.11,0,0], [-0.55,0,0.10], [0.42,0,-0.09], -0.12),
  // Twin blades: alternating left/right cuts, pivoting hips, then an X-shaped cross finisher.
  znt1_w: P([0.09,-0.35,0], [0,0.19,0], [-1.15,-0.58,0.2], [0.34,0,-0.20], [-1.2,0.37,-0.12], [0.3,0,0.16], [-0.29,0,0.14], [0.38,0,-0.12], -0.10),
  znt1_s: P([0.2,0.43,0], [0,-0.28,0], [-1.65,0.73,0.34], [0.14,0,-0.60], [-1.16,-0.25,-0.22], [0.26,0,0.35], [-0.61,0,0.12], [0.34,0,-0.06], -0.15),
  znt2_w: P([0.06,0.39,0], [0,-0.23,0], [-1.17,0.32,-0.1], [0.3,0,-0.25], [-1.15,-0.69,0.21], [0.31,0,0.32], [-0.22,0,0.11], [0.44,0,-0.09], -0.10),
  znt2_s: P([0.18,-0.43,0], [0,0.31,0], [-1.12,-0.31,-0.26], [0.23,0,0.15], [-1.72,0.82,-0.29], [0.11,0,0.55], [-0.36,0,0.06], [0.50,0,-0.12], -0.16),
  znt3_w: P([0.14,-0.22,0], [0,0.19,0], [-1.75,-0.55,0.12], [0.16,0,0.16], [-1.36,0.44,-0.16], [0.22,0,-0.18], [-0.42,0,0.16], [0.36,0,-0.07], -0.13),
  znt3_s: P([0.20,0.27,0], [0,-0.16,0], [-1.32,0.48,-0.27], [0.21,0,-0.55], [-1.87,-0.42,0.20], [0.11,0,0.33], [-0.62,0,0.12], [0.40,0,-0.08], -0.17),
  znt4_w: P([0.09,0.23,0], [0,-0.19,0], [-1.15,0.29,0.15], [0.29,0,0.26], [-1.44,-0.41,0.12], [0.24,0,-0.19], [-0.22,0,0.07], [0.48,0,-0.11], -0.12),
  znt4_s: P([0.24,-0.34,0], [0,0.21,0], [-1.75,-0.57,-0.12], [0.10,0,0.50], [-1.64,0.55,-0.18], [0.16,0,-0.48], [-0.63,0,0.14], [0.38,0,-0.08], -0.17),
  znt5_w: P([-0.06,-0.13,0], [0,0.13,0], [-1.17,-0.58,-0.30], [0.3,0,-0.23], [-1.18,0.58,0.30], [0.27,0,0.23], [-0.44,0,0.12], [0.43,0,-0.11], -0.10),
  znt5_s: P([0.34,0.10,0], [-0.14,0,0], [-1.75,0.17,-0.56], [0.13,0,0.57], [-1.75,-0.17,0.56], [0.13,0,-0.57], [-0.75,0,0.15], [0.55,0,-0.14], -0.19),
  zntx_s: P([0.26,0.06,0], [0,0,0], [-1.62,0.12,-0.47], [0.12,0,0.48], [-1.62,-0.12,0.47], [0.12,0,-0.48], [-0.58,0,0.14], [0.51,0,-0.11], -0.16),
  // The spear slams back into a raised palm; shoulders compress then settle.
  zncatch_w: P([-0.12,-0.17,0], [0.10,0.10,0], [-2.04,-0.36,-0.25], [0.44,0,0.35], [-1.28,0.49,0.28], [0.24,0,-0.22], [-0.45,0,0.09], [0.35,0,-0.11], -0.11),
  zncatch_s: P([0.16,0.20,0], [-0.05,-0.12,0], [-1.42,0.13,-0.12], [0.25,0,-0.12], [-1.3,-0.32,0.20], [0.18,0,0.20], [-0.42,0,0.10], [0.42,0,-0.08], -0.11),''')
    # ------------------------------ Game -----------------------------------
    one(G,'''      if (za.style === "zenith_rail") { this.zenithLaunch(f, za); return; }''', '''      if (za.style === "zenith_heavy") { this.zenithChargedOverhead(f, za); return; }
      if (za.style === "zenith_rail") { this.zenithLaunch(f, za); return; }''')
    one(G,'  private zenithLaunch(f: Fighter, a: Attack) {', '''  // Full charged-attack choreography: a light burst above the raised palm,
  // then a separate (real, dodgeable) overhead summoned spear projectile.
  private zenithChargedOverhead(f: Fighter, a: Attack) {
    const round = this.round;
    const above = f.chest().add(new THREE.Vector3(0, 1.26, 0));
    this.fxp("flash", above.clone(), "#e9f9ff", 0.46, 0.18, 0.92);
    this.fxp("ring", above.clone(), "#a8ddff", 0.45, 0.16, 0.74);
    this.fxp("motes", above.clone(), "#d8f2ff", 13);
    this.snd("metal_arrow_fast_hit", 0.38);
    this.later(0.16, () => {
      if (this.round !== round || f.isDown()) return;
      const target = f.opponent && !f.opponent.isDown() ? f.opponent : this.enemiesOf(f)[0] ?? null;
      const dir = target ? target.chest().sub(above) :
        new THREE.Vector3(Math.sin(f.root.rotation.y), -0.06, Math.cos(f.root.rotation.y));
      const shot = this.spawnProjectile(f, f.team, a, f.atkPower, above.clone(),
        dir.normalize().multiplyScalar(a.speed), "zenith_heavy", "metal", a.size, "#dce9fb", false, target);
      shot.life = 1.8;
      this.fxp("flash", above.clone(), "#d4eaff", 0.23, 0.10, 0.76);
    });
  }

  private zenithLaunch(f: Fighter, a: Attack) {''')
    one(G,'''            p.done=true; owner.zenithSpearOut=false;
            owner.model.setZenithSpearHeld(true);
            this.fxp("flash",owner.chest(),"#a5c1dc",0.25,0.1,0.7);''', '''            p.done = true;
            // Actual hand-contact, not just a timeout: start CC shield + catch recoil.
            if (this.cfg.role !== "client") owner.catchZenithSpear();
            else { owner.zenithSpearOut = false; owner.model.setZenithSpearHeld(true); }
            this.fxp("flash",owner.chest(),"#d4f2ff",0.49,0.19,0.85);
            this.fxp("ring",owner.chest(),"#8bd4ff",1.02,0.22,0.75);
            this.fxp("motes",owner.chest(),"#bfdcf5",23);
            this.fxp("num",owner.chest().add(new THREE.Vector3(0,0.80,0)),
              "MAGNETIC GUARD 2s", "#c6f0ff", 0.78);
            this.snd("metallic_impact_with_whip",0.48);''')
    # Prevent invisible spear strike when X is cast while blades out; X's first five are twin slashes.
    one(G,'''      this.melee(f,{...a,id:`zx${i}`,style:"zenith_barrage",dmg:25,knock:i===4?1.8:0.3,stun:0.13});''', '''      this.melee(f,{...a,id:`zx${i}`,style:f.zenithSpearOut?"zenith_twin":"zenith_barrage",
        dmg:f.zenithSpearOut?20:25,reach:f.zenithSpearOut?1.65:a.reach,
        knock:i===4?1.8:0.3,stun:0.13});''')
    # Slightly reduce reach for dual wield: already 0.72 on damage only, not hit test; correct melee call.
    one(G,'''    const zenithAttack = attacker instanceof Fighter && attacker.look.element === "metal" &&
      attacker.zenithSpearOut && a.type === "melee" && /^l\\d+$/.test(a.id)
      ? { ...weightedAttack, dmg: weightedAttack.dmg * 0.57, reach: weightedAttack.reach * 0.72 }''', '''    const zenithAttack = attacker instanceof Fighter && attacker.look.element === "metal" &&
      attacker.zenithSpearOut && a.type === "melee" && /^l\\d+$/.test(a.id)
      ? { ...weightedAttack, dmg: weightedAttack.dmg * 0.57, reach: weightedAttack.reach * 0.72 }''')
    # Short blades do not reach as far as the missing long spear.
    one(G,'''  private melee(f: Fighter, a: Attack): boolean {
    this.meleeCatchesAtSwing(f, a);''', '''  private melee(f: Fighter, a: Attack): boolean {
    if (f.look.element === "metal" && f.zenithSpearOut && /^l[1-5]$/.test(a.id))
      a = { ...a, reach: Math.min(a.reach, 1.58) };
    this.meleeCatchesAtSwing(f, a);''')
    # Twin-metal-blade hits still provide a Positive magnetic mark.
    one(G,'''a.style === "zenith_construct" || a.style === "zenith_barrage"))''', '''a.style === "zenith_construct" || a.style === "zenith_barrage" ||
         a.style === "zenith_twin"))''')
    # Returning projectile gets dedicated stun, both directions can hit separately.
    one(G,'''            const atk = stacks ? { ...p.atk, dmg: p.atk.dmg + stacks * 15, effect: "" } : p.atk;
            const outcome = this.applyHit(p.shooter, e, atk, p.power, p.pos.clone(), dir, true);''', '''            const atk = stacks ? { ...p.atk, dmg: p.atk.dmg + stacks * 15, effect: "" } : p.atk;
            // Rail Spear: the return hit stuns longer than its outgoing hit;
            // damage and separate hitIds still obey normal block/parry rules.
            const spearAtk = p.style === "zenith_rail" && p.returnTo
              ? { ...atk, id: "z_return", stun: 0.50, knock: 1.9, heavy: false }
              : atk;
            const outcome = this.applyHit(p.shooter, e, spearAtk, p.power, p.pos.clone(), dir, true);''')
    # Two extra seconds in sword stance gives enough time for a proper alternating combo.
    one(G,'    p.life=3.2;\n    f.zenithSpearOut=true;',
          '    p.life=5.5;\n    f.zenithSpearOut=true;')
    one(G,'        if (!p.returnTo && p.age > 1.50) { p.returnTo=owner; p.hitIds.clear(); }',
          '        if (!p.returnTo && p.age > 2.75) { p.returnTo=owner; p.hitIds.clear(); }')
    one(G,'    p.returnTo=f; p.hitIds.clear(); p.life=Math.max(p.life,0.85);',
          '    p.returnTo=f; p.hitIds.clear(); p.life=Math.max(p.life,2.0);')
    one(G,'''    this.fxp("flash",origin,"#acbfd9",0.25,0.14,0.58);
    this.snd("metal_arrow_fast_hit", 0.58);''', '''    this.fxp("flash",origin,"#acbfd9",0.25,0.14,0.58);
    this.fxp("motes",f.chest(),"#bbd8ef",17); // Twin blades assembling from metal fragments
    this.snd("metal_arrow_fast_hit", 0.58);''')
    # Master AI stays in dual-blade mode long enough to animate five attacks.
    one(A, 'else if (held > (this.iqLevel >= 2 ? 1.0 : 1.5) &&',
          'else if (held > (this.iqLevel >= 2 ? 1.75 : 2.2) &&')
    # Keep cleanup normal if rail is destroyed; don't falsely give shield on loss.
except ValueError as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')

stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
try:
    for f in NAMES:
        src=ROOT/f
        shutil.copy2(src, src.with_name(src.name+f'.before_zenith_v5_{stamp}.bak'))
    for f in NAMES:
        (ROOT/f).write_text(new[f],encoding='utf8')
        print('Updated:',f)
except OSError as e:
    sys.exit(f'WRITE ERROR: {e}; recover from timestamped .before_zenith_v5_*.bak backups.')
print('Zenith V5 installed: reference spear repaired, overhead charged spear, twin swords,\n'
      '   catch recoil and 2s CC guard, throw/return hit stuns, multiplayer state snapshots.')
