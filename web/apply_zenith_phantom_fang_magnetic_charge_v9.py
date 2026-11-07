#!/usr/bin/env python3
"""Fight Royale Zenith V9: Phantom Fang l5 + Magnetic Charge C + Twin Blade tempo.
Run inside web/ AFTER Zenith V8. Requires the existing V5/V7 spear/twin setup.
Single-character gameplay patch: Zarek, other classes, damage tables, throw/catch,
network authority, projectile logic and existing other skills are preserved.
Timestamped backups, preflight before writing, atomic replace + rollback, safe rerun.
"""
from pathlib import Path
from datetime import datetime
import os, shutil, sys, tempfile

ROOT = Path.cwd()
FILES = ['src/game/kits.ts','src/game/fighter.ts','src/game/game.ts','src/game/ai.ts','src/game/model.ts']
MARK = 'ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108'
try:
    orig = {f:(ROOT/f).read_text(encoding='utf-8') for f in FILES}
except OSError as exc:
    sys.exit(f'ERROR: Run from Fight Royale/web with the source files present: {exc}')
if MARK in orig[FILES[0]]:
    print('Zenith V9 is already installed. No files changed.')
    sys.exit(0)
if ('ZENITH_QIANG_CHOREOGRAPHY_V8_20261108' not in orig['src/game/model.ts'] or
        'zenithSpearOut' not in orig['src/game/fighter.ts'] or
        'zenithSkillOpportunity' not in orig['src/game/ai.ts']):
    sys.exit('PREFLIGHT ERROR: This installer needs the complete Zenith V8 source. No files changed.')

after = orig.copy()
def rep(path, old, new):
    n=after[path].count(old)
    if n!=1:
        raise ValueError(f'{path}: expected 1 occurrence, found {n}: {old[:110]!r}')
    after[path]=after[path].replace(old,new,1)

try:
    K='src/game/kits.ts'; F='src/game/fighter.ts'; G='src/game/game.ts'; A='src/game/ai.ts'; M='src/game/model.ts'
    # Single, explicit balance/speed block at the point where the metal kit is defined.
    rep(K, '  // ZENITH_IRON_SOVEREIGN_V1_20261108: Metal spear kit is independent of Zarek.',
        '''  // ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108
  // C: 20s real-time buff. Spear 3x attack tempo; twin blades 2x normally / 4x buffed.
  // Guard damage only is reduced by 20% while buffed; base health damage does NOT rise.
  // l5 spear Phantom Fang splits a single finisher into five contact windows.
  // ZENITH_IRON_SOVEREIGN_V1_20261108: Metal spear kit is independent of Zarek.''')
    rep(K, '''    base("heavy", { name: "Magnetic Lance", type: "projectile",''',
        '''    // A true multi-hit l5 needs enough active time to play five rapid thrusts.
    // The total damage (68) and guard damage (21) are split, not multiplied.
    t.l5.name = "Phantom Fang";
    t.l5.active = 0.40;
    t.l5.recover = 0.12;
    base("heavy", { name: "Magnetic Lance", type: "projectile",''')
    rep(K, '''    base("c", { name: "Magnetic Dominion", desc: "Tap to draw a positively marked enemy toward you, hold to repel nearby foes. With your spear thrown, zip toward its magnetic anchor instead.",
      cd: 14, type: "buff", mode: "zenith_magnet", wind: 0.12, active: 0.08, recover: 0.36,
      radius: 4.5, pose_w: "znc_w", pose_s: "znc_s" });''',
        '''    base("c", { name: "Magnetic Charge", desc: "20s buff: spear basics 3x faster; twin metal blades 4x faster (normally 2x). Basic guard damage -20%. Health damage unchanged.",
      cd: 30, type: "buff", mode: "zenith_charge", duration: 20, wind: 0.12, active: 0.08, recover: 0.36,
      pose_w: "znc_w", pose_s: "znc_s" });''')

    # Time real buff seconds, independent of attack/slow state and skill cooldown.
    rep(F,'  zenithMagnetCharges = 0;', '''  zenithMagnetCharges = 0;
  /** Zenith V9: 20 real seconds of Magnetic Charge; independent of spear throw state. */
  zenithMagneticChargeT = 0;''')
    rep(F,'    this.zenithCatchShieldT = Math.max(0, this.zenithCatchShieldT - dt);',
        '''    if (this.look.element === "metal")
      this.zenithMagneticChargeT = Math.max(0, this.zenithMagneticChargeT - dt);
    this.zenithCatchShieldT = Math.max(0, this.zenithCatchShieldT - dt);''')
    # Zarek should retain Clash Momentum but not have its modifier leak onto Zenith.
    rep(F, '''    if (this.kit === "glaive" && /^l[1-9]$/.test(id)) {
      const speed = 1 + Math.min(this.clashMomentum, 5) * 0.20;''',
        '''    if (this.kit === "glaive" && this.look.element !== "metal" && /^l[1-9]$/.test(id)) {
      const speed = 1 + Math.min(this.clashMomentum, 5) * 0.20;''')
    rep(F, '''    if (this.kit === "sickle" && this.bloodFrenzyT > 0 && id.startsWith("l"))''',
        '''    // V9 real attack speed: short twin-blade basics are 2x at all times,
    // 4x with Magnetic Charge. Spear basics are 3x only while charged.
    // No animation-only speed fakery; wind, active, and recover ALL scale.
    if (this.kit === "glaive" && this.look.element === "metal" && /^l[1-5]$/.test(id)) {
      const charged = this.zenithMagneticChargeT > 0;
      const speed = this.zenithSpearOut ? (charged ? 4 : 2) : (charged ? 3 : 1);
      this.atk = { ...this.atk,
        wind: this.atk.wind / speed,
        active: this.atk.active / speed,
        recover: this.atk.recover / speed,
        guard: this.atk.guard * (charged ? 0.8 : 1),
      };
    }
    if (this.kit === "sickle" && this.bloodFrenzyT > 0 && id.startsWith("l"))''')
    # Avoid stale C hold-to-repel behavior; no residual interaction with magnetic buffs.
    rep(F, '    if (this.look.element === "metal" && k === "c") this.zenithDominionRepel = this.intent.skillHeld === "c";',
        '    if (this.look.element === "metal" && k === "c") this.zenithDominionRepel = false; // V9 C is a timed self-buff')
    rep(F,'''      this.zenithSpearOut = false;
      this.zenithCatchShieldT = 0;''',
        '''      this.zenithSpearOut = false;
      this.zenithMagneticChargeT = 0;
      this.zenithCatchShieldT = 0;''')
    # Net: all clients see the buff timer in spectator mode, appended after V5 fields.
    rep(F, '''      this.zenithSpearOut ? 1 : 0, +this.zenithCatchShieldT.toFixed(2), +this.zenithCatchRecoilT.toFixed(2)];''',
        '''      this.zenithSpearOut ? 1 : 0, +this.zenithCatchShieldT.toFixed(2), +this.zenithCatchRecoilT.toFixed(2),
      +this.zenithMagneticChargeT.toFixed(2)];''')
    rep(F, '''      this.model.zenithCatchRecoilT = this.zenithCatchRecoilT;
    }
    this.hp = s[8];''',
        '''      this.model.zenithCatchRecoilT = this.zenithCatchRecoilT;
      this.zenithMagneticChargeT = s.length > 59 ? (s[59] ?? 0) : 0;
    }
    this.hp = s[8];''')

    rep(G, '        a.mode === "zenith_magnet" ? "hi_tech_touch_with_magnet" :',
        '        a.mode === "zenith_charge" ? "hi_tech_touch_with_magnet" :')
    rep(G, '''      if (za.style === "zenith_arsenal") { this.zenithArsenal(f, za); return; }''',
        '''      if (za.style === "zenith_arsenal") { this.zenithArsenal(f, za); return; }
      if (za.style === "zenith_basic" && f.atkId === "l5" && !f.zenithSpearOut) {
        this.zenithPhantomFang(f, za); return;
      }''')
    rep(G, '''      case "buff": if (a.mode === "zenith_magnet") this.zenithDominion(f,a); else this.applyBuff(f,a); break;''',
        '''      case "buff": if (a.mode === "zenith_charge") this.zenithCharge(f, a);
        else if (a.mode === "zenith_magnet") this.zenithDominion(f,a); else this.applyBuff(f,a); break;''')
    rep(G, '  private zenithDominion(f: Fighter, a: Attack) {',
        '''  // ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108
  private zenithCharge(f: Fighter, a: Attack) {
    if (f.isDown() || f.look.element !== "metal") return;
    f.zenithMagneticChargeT = 20.0; // real-time buff; never affects skills or heavy attacks
    this.fxp("ring", f.chest(), "#9ddada", 0.76, 0.18, 0.55);
    this.fxp("motes", f.chest(), "#bdece7", 8);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.84, 0)), "MAGNETIC CHARGE 20s", "#a8e5d6", 0.84);
  }

  // Five individually blockable/parryable thrust checks, totaling the ORIGINAL
  // fifth-hit damage and guard pressure, not five times its original value.
  private zenithPhantomFang(f: Fighter, a: Attack) {
    const serial = f.swingSerial, round = this.round;
    const damage = [12, 12, 13, 14, 17]; // sum 68
    const guard = [3, 3, 4, 4, 7];      // sum 21
    for (let i = 0; i < 5; i++) this.laterCombo(f, i * a.active / 5, () => {
      if (this.round !== round || f.isDown() || f.swingSerial !== serial ||
          f.state !== S.ATTACK || f.atkId !== "l5") return;
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      f.poseOverride = i % 2 === 0 ? "zn5_s" : "zn1_s";
      const pulse: Attack = { ...a,
        dmg: damage[i] * (a.dmg / 68), guard: guard[i] * (a.guard / 21),
        stun: i === 4 ? a.stun : 0.035, knock: i === 4 ? a.knock : 0.08,
        style: "zenith_basic" };
      this.melee(f, pulse); // uses original reach, blocks, parries, clashes and hit rules
      this.fxp("sparks", tip, "#bddce9", i === 4 ? 4 : 2, 1.7);
      if (i === 0 || i === 4) this.snd("metal_swish", i === 4 ? 0.43 : 0.30);
    });
  }

  private zenithDominion(f: Fighter, a: Attack) {''')

    # AI no longer uses the deleted pull/repel behavior, and uses C as a timed buff.
    rep(A, '''    if (f.zenithSpearOut) {
      const held = now - Math.max(0, this.zenithSpearObservedAt);''',
        '''    if (ready("c") && f.zenithMagneticChargeT <= 0 &&
        (gap <= 6.5 || f.zenithSpearOut || pressure)) {
      key = "c"; // pre-buff the next basic combo, with or without the spear
    } else if (f.zenithSpearOut) {
      const held = now - Math.max(0, this.zenithSpearObservedAt);''')
    rep(A, '''      // Don't instantly recall every Z! Attack from two positions or reposition by C first.
      if (ready("c") && anchorDist > 2.3 && gap > 2.1 && gap < 8 &&
          (marked === -1 || anchorDist > 4.2) && held > 0.36) key = "c";
      else if (held > (this.iqLevel >= 2 ? 1.75 : 2.2) &&
          (gap < 3.3 || held > 2.4 || anchorDist > 7.5)) key = "z";''',
        '''      // Keep the dual-blade phase long enough to use the fast 2x/4x slashes.
      if (held > (this.iqLevel >= 2 ? 1.75 : 2.2) &&
          (gap < 3.3 || held > 2.4 || anchorDist > 7.5)) key = "z";''')
    rep(A, '''    } else if (ready("c") && marked === 1 && gap >= 2.3 && gap <= 5.2 &&
          (ready("x") || pressure || gap >= 3.5)) {
      // Positive -> attract into close-range rapid thrusts.
      key = "c";''',
        '''    } else if (ready("c") && f.zenithMagneticChargeT <= 0 && gap < 6) {
      key = "c"; // self-buff, no more magnet pull''')
    rep(A, '''    } else if (ready("c") && marked === -1 && gap < 2.5 && !f.stage) {
      // Negative -> repel as a defensive reset (normal cooldown and collision still apply).
      f.intent.skillHeld = "c"; key = "c";''',
        '''    } else if (ready("c") && f.zenithMagneticChargeT <= 0) {
      key = "c"; // optional pre-engagement Magnetic Charge''')
    rep(A, '''        if (name === "Magnetic Dominion") points += f.zenithSpearOut ? 2.5 : distance < 4.5 ? 1.5 : 0.0;''',
        '''        if (name === "Magnetic Charge") points += f.zenithMagneticChargeT > 0 ? -3.0 : distance < 6.5 ? 2.5 : 1.0;''')

    # V8 existing fighter state drives the fast flourish. No change to IK or other characters.
    rep(M, '''        thrust = p;
        // Phase 2: tiny physical overshoot, then damped, poised recovery.''',
        '''        thrust = p;
        // V9 Phantom Fang: five ultra-quick forward tip pulses, staying narrow,
        // without increasing reach, moving Fighter.root, or turning into a staff spin.
        if (step === 5) {
          const flicker = Math.sin(age * 93);
          tip.x += flicker * 0.08;
          tip.y += Math.cos(age * 93) * 0.025;
          offset.z += Math.max(0, flicker) * 0.035;
        }
        // Phase 2: tiny physical overshoot, then damped, poised recovery.''')
except ValueError as err:
    sys.exit(f'PREFLIGHT ERROR: {err}. No files changed.')

stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
backups={}
try:
    for path in FILES:
        p=ROOT/path
        backup=p.with_name(p.name+f'.before_zenith_v9_{stamp}.bak')
        shutil.copy2(p,backup)
        backups[path]=backup
    written=[]
    for path in FILES:
        p=ROOT/path
        fd,tmp=tempfile.mkstemp(prefix=f'.{p.name}.zenithv9.',suffix='.tmp',dir=p.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8',newline='') as out: out.write(after[path])
            os.replace(tmp,p)
            written.append(path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        print('Updated:',path)
except Exception as exc:
    for path in FILES:
        if path in backups:
            try: shutil.copy2(backups[path],ROOT/path)
            except OSError: pass
    sys.exit(f'WRITE ERROR: {exc}. Attempted automatic restore from V9 backups.')
print('\nZenith V9 installed: spear l5 Phantom Fang (5 split hits), C Magnetic Charge (20s, 30s cooldown).')
print('Spear basics: normal 1x, buff 3x. Twin blades: normal 2x, buff 4x.')
print('Buffed basic guard damage x0.80; basic HP damage unchanged. Other characters/skills unchanged.')
