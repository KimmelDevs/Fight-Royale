#!/usr/bin/env python3
"""Fight Royale V8 FIXED for Nov 7 current source: Garrick skill redesign, Bob mines, Kaizen mobile spins/CD/AI, Rook basics.

Run from Fight Royale's web folder:
    python Install_FightRoyale_Garrick_Bob_Kaizen_Rook_V8_Fixed.py --check
    python Install_FightRoyale_Garrick_Bob_Kaizen_Rook_V8_Fixed.py

Updates original skill keys/names (NOT new Z/X/C names):
 Garrick X Iron Tempest: 3 advancing slashes, progressively longer strides,
   target-tracking turn and slight steer between attacks. 3 actual hit windows remain.
 Garrick Z Ground Slam: short startup HP damage resistance, stagger on hit,
   clears weak hostile projectiles in the existing radius on impact.
 Garrick C Titan Cleave: successful eruption briefly launches the target; press
   C again while the follow-up is available for a real forward greatsword rush
   ending with ONE overhead melee strike. No hit => no follow-up.
 Bob Z Land Mine: four stored charges, 8s recharge per charge, up to two active
   mines simultaneously. No damage increase. Mine casts at cap are denied without
   spending a charge. Existing trap arm/life/impact mechanics are unchanged.
 Kaizen: +3s cooldown on each skill Z/X/C/V. Existing attacks/stats unchanged.
 Kaizen Z Razor Cyclone and C Death Spiral: walk/steer while casting at reduced
   normal movement speed; Death Spiral's hits and visuals follow Kaizen's position.
   Enemy Kaizen CPU pursues an escaping target while spinning without homing.
 Enemy AI: recognize Kaizen's damaging spinning shield, don't approach within its
   actual contact radius, and stop treating completed chainblade skills as hazards.
 Rook: +25% damage to ONLY light combo l1-l5. Heavy and skills unchanged.

Script is idempotent, validates source anchors before writing, backs up changed
files, and never edits unrelated project paths. Requires Python 3.9+, no pip.
"""
from __future__ import annotations
import argparse
import datetime as dt
import pathlib
import re
import shutil
import sys

TAG = "FIGHT_ROYALE_GARRICK_BOB_KAIZEN_ROOK_V7"  # same in-source markers as prior V8
FILES = ("kits.ts", "fighter.ts", "game.ts", "ai.ts")

class PatchError(RuntimeError): pass


def one(src: str, old: str, new: str, label: str) -> str:
    n = src.count(old)
    if n != 1:
        raise PatchError(f"{label}: expected one matching source anchor; found {n}. Nothing changed.")
    return src.replace(old, new, 1)


def locate_project(root: pathlib.Path) -> pathlib.Path:
    candidates = (root, root / "web", root.parent, root.parent / "web")
    for path in candidates:
        if all((path / "src" / "game" / f).is_file() for f in FILES):
            return path
    raise PatchError("Cannot find src/game files. Place this .py inside the Fight Royale web folder.")


def patch_kits(src: str) -> str:
    if TAG in src: return src
    # Do all balancing where kits are constructed so new fighters / loadouts get it too.
    anchor = '  // ZAREK_EFFECTIVE_RANGE_NERF_V1: hitboxes now match the smaller double-ended glaive.'
    if anchor not in src:
        anchor = '  for (const k of Object.keys(t)) {\n'
    addition = '''  // FIGHT_ROYALE_GARRICK_BOB_KAIZEN_ROOK_V7: targeted kit changes.
  if (kit === "knuckles") {
    // Five light punches only. Charged punch, parry counter and all Z/X/C/V untouched.
    for (const key of ["l1", "l2", "l3", "l4", "l5"]) {
      if (t[key]) t[key].dmg = Math.round(t[key].dmg * 1.25 * 100) / 100;
    }
  }
  if (kit === "chainblade") {
    // Four skills (including the optional V); no extra multiplier at cast time.
    for (const key of ["z", "x", "c", "v"]) if (t[key]) t[key].cd += 3;
  }
  if (kit === "greatsword") {
    if (t.z?.name === "Ground Slam") {
      t.z.stagger = true; // nearby shockwave now causes an actual short stagger
      t.z.desc = "Plant the greatsword for a close shockwave that staggers foes, clears weak projectiles, and braces against damage during startup.";
    }
    if (t.x?.name === "Iron Tempest") {
      t.x.desc = "Three successive advancing greatsword cuts: short slash, deeper diagonal cut, then a lunging finisher. Steer slightly between swings.";
    }
    if (t.c?.name === "Titan Cleave") {
      t.c.desc = "Rock spikes erupt beneath the enemy. If they hit, press the same skill again to rush forward and finish with an overhead strike.";
    }
    t.garrick_follow = a({
      name: "Titan Cleave", desc: "Follow-up overhead strike after a confirmed eruption hit.",
      type: "melee", wind: 0.68, active: 0.09, recover: 0.45,
      dmg: 125, guard: 36, reach: 2.65, lunge: 0, knock: 5.0,
      stun: 0.46, heavy: true, pose_w: "charge", pose_s: "heavy_s",
      style: "garrick_rush_finish", next: "",
    });
  }
  if (kit === "bomb" && t.z?.type === "mine") {
    t.z.desc = "Four stored mine charges (one recharges every 8s); place at most two active mines. Damage unchanged.";
  }
'''
    src = one(src, anchor, addition + anchor, 'kit modifiers')
    return '// ' + TAG + '\n' + src


def patch_fighter(src: str) -> str:
    if TAG in src: return src
    # State for charge recharge and rush follow-up. Name-based checks survive skill remapping.
    src = one(src, '  private guardDelay = 0;\n', '''  // V7 Bob mine inventory. One charge is recovered per normal mine cooldown.
  bobMineCharges = 4;
  bobMineRechargeT = 0;
  bobMineCount = 0; // authoritative trap count, maintained by Game
  // V7 Garrick C follow-up is earned by a confirmed HP hit, never on a miss.
  garrickFollowT = 0;
  garrickFollowTarget: Entity | null = null;
  private garrickRushTarget: Entity | null = null;
  private garrickRushSerial = -1;
  armGarrickFollow(target: Entity) {
    if (this.kit !== "greatsword" || target.isDown()) return;
    this.garrickFollowTarget = target;
    this.garrickFollowT = 1.65;
  }
  /** A confirmed Titan Cleave eruption launches through Fighter-owned state. */
  receiveGarrickLaunch() {
    this.velY = Math.max(this.velY, 7.0);
    this.onGround = false;
    this.ground = null;
  }
  private guardDelay = 0;
''', 'new fighter fields')
    # Timer anchor stable across later installs and parry versions.
    src = one(src, '    this.clock += dt;\n', '''    // Bob ammo recharges sequentially, even while two mines remain deployed.
    if (this.kit === "bomb") {
      const mineSlot = ["z", "x", "c"].find(k => this.attacks[k]?.type === "mine");
      if (mineSlot) {
        const period = Math.max(0.2, this.attacks[mineSlot].cd * this.cdMult);
        if (this.bobMineCharges < 4) {
          this.bobMineRechargeT -= dt;
          if (this.bobMineRechargeT <= 0) {
            this.bobMineCharges = Math.min(4, this.bobMineCharges + 1);
            this.bobMineRechargeT = this.bobMineCharges === 4 ? 0 : period;
          }
        }
        this.cooldowns[mineSlot] = this.bobMineCharges > 0 ? 0 : Math.max(0, this.bobMineRechargeT);
      }
    }
    this.garrickFollowT = Math.max(0, this.garrickFollowT - dt);
    if (this.garrickFollowT <= 0 || this.garrickFollowTarget?.isDown()) {
      this.garrickFollowTarget = null;
      this.garrickFollowT = 0;
    }
    this.clock += dt;
''', 'recharge and follow timers')
    # Avoid timer assignment being immediately overwritten in regular cooldowns: inspect order; fine.
    src = one(src, '    // Powder keg out: the same key is the detonator (works any time you\'re not stunned).\n', '''    // Garrick C second press: legal ONLY after the first eruption really hit.
    if (this.kit === "greatsword" && this.attacks[k]?.name === "Titan Cleave" &&
        this.garrickFollowT > 0 && this.garrickFollowTarget &&
        !this.garrickFollowTarget.isDown() && this.onGround &&
        [S.IDLE, S.BLOCK, S.ATTACK].includes(this.state) &&
        (this.state !== S.ATTACK || this.atk?.name === "Titan Cleave" || this.atkPhase === 2)) {
      this.garrickRushTarget = this.garrickFollowTarget;
      this.garrickFollowTarget = null;
      this.garrickFollowT = 0;
      this.holding = false;
      this.startAttack("garrick_follow");
      this.garrickRushSerial = this.swingSerial;
      return;
    }
    // Powder keg out: the same key is the detonator (works any time you're not stunned).
''', 'Garrick recast')
    src = one(src, '    // The keg\'s cooldown starts when it explodes (the arena sets it).\n', '''    // A mine charge only spends after a legal cast; two deployed mines is a hard cap.
    const bobMine = this.kit === "bomb" && this.attacks[k]?.type === "mine";
    if (bobMine) {
      if (this.bobMineCharges <= 0 || this.bobMineCount >= 2) return;
      const wasFull = this.bobMineCharges === 4;
      this.bobMineCharges -= 1;
      if (wasFull) this.bobMineRechargeT = Math.max(0.2, this.attacks[k].cd * this.cdMult);
    }
    // The keg's cooldown starts when it explodes (the arena sets it).
''', 'mine cast charge spending')
    src = one(src,
        '    } else this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 : this.attacks[k].cd * this.cdMult;\n',
        '''    } else this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 :
      bobMine ? (this.bobMineCharges > 0 ? 0 : this.bobMineRechargeT) : this.attacks[k].cd * this.cdMult;
''', 'mine charge UI (Nesa-compatible)')
    # Avoid becoming invulnerable: during windup only HP damage reduction.
    src = one(src, '    let dmg = a.dmg * power;\n', '''    let dmg = a.dmg * power;
    // Garrick Ground Slam's sword-plant startup is braced, not invulnerable.
    if (this.kit === "greatsword" && this.state === S.ATTACK &&
        this.atk?.name === "Ground Slam" && this.stateT <= this.atk.wind + 0.035)
      dmg *= 0.67;
''', 'Ground Slam damage reduction')
    # Movement for X: forward bursts, stage-specific steering done in movePlat.
    anchor = '    const recoilSpeed = this.knock;\n'
    if anchor not in src: raise PatchError('Garrick X movement anchor missing')
    src = one(src, anchor, '''    // Garrick Iron Tempest: genuine travel across three consecutive hit windows.
    // The current target direction is recalculated each frame (limited steering).
    if (this.kit === "greatsword" && this.state === S.ATTACK &&
        this.atk?.style === "iron_tempest" && this.onGround && this.atkPhase <= 1) {
      const t = this.stateT - this.atk.wind;
      const stride = t >= 0.58 && t < 0.88 ? 7.2 :
        t >= 0.28 && t < 0.55 ? 5.2 : t >= -0.035 && t < 0.22 ? 3.0 : 0;
      v += stride;
      if (this.intent.move.lengthSq() > 0.1 && stride > 0 && !this.stage) {
        const desired = this.intent.move.clone().setY(0).normalize();
        if (desired.dot(dir) > 0.05) dir.lerp(desired, 0.22).normalize();
      }
    }
    // Garrick Titan Cleave recast: rush through real distance, stopping before contact.
    if (this.kit === "greatsword" && this.state === S.ATTACK &&
        this.atk?.style === "garrick_rush_finish" && this.garrickRushTarget &&
        !this.garrickRushTarget.isDown() && this.garrickRushSerial === this.swingSerial) {
      const to = this.garrickRushTarget.root.position.clone().sub(pos).setY(0);
      const gap = to.length();
      if (gap > 1.90 && this.stateT < this.atk.wind) {
        dir.copy(to.divideScalar(Math.max(0.001, gap)));
        v = Math.min(17.0, (gap - 1.90) / Math.max(0.018, dt));
        if (!this.stage) {
          const yaw = Math.atan2(dir.x, dir.z);
          let delta = yaw - this.root.rotation.y;
          delta = Math.atan2(Math.sin(delta), Math.cos(delta));
          this.root.rotation.y += delta * Math.min(1, dt * 7.5);
        }
      } else v = 0;
    }
    const recoilSpeed = this.knock;
''', 'Garrick 3D movement')
    # Stage movement target for X and C
    src = one(src, '        target = near ? 0 : this.facing * this.atk.lunge;\n', '''        target = near ? 0 : this.facing * this.atk.lunge;
        if (this.kit === "greatsword" && this.atk.style === "iron_tempest") {
          const t = this.stateT - this.atk.wind;
          const extra = t >= 0.58 && t < 0.88 ? 7.2 :
            t >= 0.28 && t < 0.55 ? 5.2 : t >= -0.035 && t < 0.22 ? 3.0 : 0;
          target += this.facing * extra;
          if (mx === this.facing) target += mx * 0.8; // small between-swing steering
        }
        if (this.kit === "greatsword" && this.atk.style === "garrick_rush_finish" &&
            this.garrickRushTarget && !this.garrickRushTarget.isDown() &&
            this.garrickRushSerial === this.swingSerial && this.stateT < this.atk.wind) {
          const dx = this.garrickRushTarget.root.position.x - pos.x;
          if (Math.abs(dx) > 1.8) {
            this.facing = Math.sign(dx);
            target = this.facing * Math.min(17, (Math.abs(dx) - 1.8) / Math.max(dt, 0.018));
          } else target = 0;
        }
''', 'Garrick stage movement')
    # Clear model target when knocked out, don't require every previous installer.
    src = one(src, '  revive(frac: number) {\n', '''  revive(frac: number) {
    this.bobMineCharges = 4; this.bobMineRechargeT = 0; this.bobMineCount = 0;
    this.garrickFollowT = 0; this.garrickFollowTarget = null; this.garrickRushTarget = null;
''', 'revive reset')
    src = one(src, '  ko() {\n', '''  ko() {
    this.garrickFollowT = 0; this.garrickFollowTarget = null; this.garrickRushTarget = null;
''', 'KO reset')
    return '// ' + TAG + '\n' + src


def patch_game(src: str) -> str:
    if TAG in src: return src
    # explicit one damage event for Titan follow-up is already standard melee.
    # augment existing iron tempest visual choreography with distinct pose per hit.
    src = one(src, '        const at = f.root.position.clone();\n        const mid = at.clone().add(new THREE.Vector3(0, i === 1 ? 1.55 : 1.05, 0));\n', '''        // Each stage gets its own weapon silhouette. Real travel comes from Fighter.move.
        f.poseOverride = i === 0 ? "l1_s" : i === 1 ? "l2_s" : "heavy_s";
        const at = f.root.position.clone();
        const mid = at.clone().add(new THREE.Vector3(0, i === 1 ? 1.55 : 1.05, 0));
''', 'Iron Tempest animation')
    # Add projectile clear helper before runStrike.
    anchor = '  /** Area attack(s) at the target (or around the caster) after a telegraphed delay. */\n'
    helper = '''  /** Garrick Ground Slam: clear only weak, hostile non-explosive projectiles.
   * The shockwave deals no extra HP damage and never deletes powerful ultimates. */
  private garrickBreakWeakProjectiles(f: Fighter, center: THREE.Vector3, radius: number) {
    for (const p of this.projectiles) {
      if (p.done || p.visualOnly || p.team === f.team || !p.atk ||
          p.atk.type === "lob" || p.atk.dmg > 125 || p.atk.heavy) continue;
      const gap = p.pos.clone().sub(center);
      if (Math.abs(gap.y) > 2.2) continue;
      gap.y = 0;
      if (gap.length() > radius + Math.max(0.2, p.size * 0.35)) continue;
      p.done = true;
      this.fxp("sparks", p.pos.clone(), "#d7c9a4", 12, 4);
      this.fxp("flash", p.pos.clone(), "#d7c9a4", 0.18, 0.08, 0.55);
    }
  }

'''
    src = one(src, anchor, helper + anchor, 'Garrick weak projectile helper')
    src = one(src, '        this.impactFx(a, at, color, a.radius);\n', '''        this.impactFx(a, at, color, a.radius);
        if (f.kit === "greatsword" && a.name === "Ground Slam" && i === 0)
          this.garrickBreakWeakProjectiles(f, at, a.radius + 0.35);
''', 'Garrick Ground Slam projectile clearing')
    src = one(src, '''            const outcome = this.applyHit(f, d, a, power, d.chest(), dir, true);
            if (kaedeCuts && (outcome === "hit" || outcome === "crit" || outcome === "ko"))
''', '''            const outcome = this.applyHit(f, d, a, power, d.chest(), dir, true);
            // Titan Cleave: only confirmed HP damage unlocks a follow-up rush.
            if (f.kit === "greatsword" && a.name === "Titan Cleave" &&
                a.style === "cleave" && (outcome === "hit" || outcome === "crit") &&
                d instanceof Fighter && !d.isDown()) {
              d.receiveGarrickLaunch();
              f.armGarrickFollow(d);
              this.fxp("rocks", d.root.position.clone(), 15, 0.8);
              this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.7, 0)),
                "C FOLLOW-UP!", "#ffe2a0", 0.84);
            }
            if (kaedeCuts && (outcome === "hit" || outcome === "crit" || outcome === "ko"))
''', 'Garrick Titan Cleave hit confirm')
    # First guard against >2 on map; state updated by each trap placement/removal.
    src = one(src, '''  private plantMine(f: Fighter, a: Attack) {
    const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
''', '''  private plantMine(f: Fighter, a: Attack) {
    if (f.kit === "bomb" && this.traps.some(t => t.kind === "mine" && t.owner === f) &&
        this.traps.filter(t => t.kind === "mine" && t.owner === f).length >= 2) return;
    const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
''', 'Bob mine placement cap')
    src = one(src, '''    // At most 3 mines each: the oldest one fizzles.
    const mines = this.traps.filter((t) => t.kind === "mine" && t.owner === f);
    if (mines.length > 3) this.removeTrap(mines[0], true);
''', '''    // Exactly two active Bob mines; excess ammo stays in the inventory.
    const mines = this.traps.filter((t) => t.kind === "mine" && t.owner === f);
    f.bobMineCount = mines.length;
''', 'Bob mine count')
    src = one(src, '''    this.traps = this.traps.filter((x) => x !== t);
    this.emit(["trapEnd", t.id]);
''', '''    this.traps = this.traps.filter((x) => x !== t);
    if (t.kind === "mine" && t.owner)
      t.owner.bobMineCount = this.traps.filter(x => x.kind === "mine" && x.owner === t.owner).length;
    this.emit(["trapEnd", t.id]);
''', 'Bob mine count on detonate / expire')
    return '// ' + TAG + '\n' + src


def patch_ai(src: str) -> str:
    if TAG in src: return src
    anchor = '  think(f: Fighter, dt: number) {\n    const o = f.opponent as Fighter | null;\n    if (!o || o.isDown()) return;\n'
    if anchor not in src: raise PatchError('AI think anchor changed')
    src = one(src, anchor, '''  think(f: Fighter, dt: number) {
    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    if (this.avoidKaizenSpinGuard(f, o, dt)) return;
''', 'AI awareness entry point')
    # Recovered chainblade attack no longer triggers emergency dodge: no fake lingering threats.
    anchor2 = '  constructor(private threats: Threats, level: number) {\n'
    helper = '''  // V7: Kaizen's shield causes REAL 16 HP contact damage every 0.45 s in its
  // physical radius. Move outside that radius, then return when he drops guard.
  private kaizenGuardReact = -1;
  private kaizenGuardDashUsed = false;
  private avoidKaizenSpinGuard(f: Fighter, o: Fighter, dt: number): boolean {
    const dangerous = o.kit === "chainblade" && o.state === S.BLOCK &&
      o.guard > 0 && !o.isDown() && !o.chainBindT;
    if (!dangerous) {
      this.kaizenGuardReact = -1;
      this.kaizenGuardDashUsed = false;
      return false;
    }
    if (f.isDown() || !f.onGround ||
        (f.state !== S.IDLE && f.state !== S.BLOCK)) return false;
    const away = f.root.position.clone().sub(o.root.position).setY(0);
    const gap = away.length();
    if (gap > 1.85 || gap < 0.01) {
      if (gap > 1.85) this.kaizenGuardDashUsed = false;
      return false;
    }
    if (this.kaizenGuardReact < 0)
      this.kaizenGuardReact = this.p.react[0] + Math.random() * (this.p.react[1] - this.p.react[0]);
    this.kaizenGuardReact = Math.max(0, this.kaizenGuardReact - dt);
    if (this.kaizenGuardReact > 0) return false;
    away.normalize();
    // Do not run into arena walls while trying to escape.
    if (f.stage) {
      const main = f.stage.plats[0];
      if (!main || f.root.position.x + away.x * 1.0 < main.x0 + 0.65 ||
          f.root.position.x + away.x * 1.0 > main.x1 - 0.65) return false;
      away.set(Math.sign(away.x) || -f.facing, 0, 0);
    } else if (f.root.position.clone().setY(0).addScaledVector(away, 1.0).length() >= f.arenaRadius - 0.2) {
      const side = new THREE.Vector3(-away.z, 0, away.x);
      if (f.root.position.clone().setY(0).addScaledVector(side, 1).length() >= f.arenaRadius - 0.2)
        side.negate();
      if (f.root.position.clone().setY(0).addScaledVector(side, 1).length() >= f.arenaRadius - 0.2)
        return false;
      away.copy(side);
    }
    f.intent.move.copy(away);
    f.intent.block = false;
    f.intent.sprint = false;
    // One real dash per guard encounter, and only when dangerously close.
    if (!this.kaizenGuardDashUsed && gap < 1.42 && f.dashCd <= 0 && !f.dashing()) {
      f.intent.dash.copy(away);
      this.kaizenGuardDashUsed = true;
    }
    // Cancel a stale shield-hold decision only while in the damaging contact area.
    this.blockWait = -1;
    this.blockHold = 0;
    return true;
  }

'''
    src = one(src, anchor2, helper + anchor2, 'Kaizen shield AI method')
    # Existing heavy/continuous evasion should not treat completed skills as active.
    for sig in [
        '    if (o.state !== S.ATTACK || !atk || !o.isContinuousComboActive()) {',
        '    const dangerous = o.state === S.ATTACK && !!a &&\n',
    ]:
        if sig not in src:
            raise PatchError('AI attack-end timing anchor missing')
    src = one(src,
        '    if (o.state !== S.ATTACK || !atk || !o.isContinuousComboActive()) {',
        '    if (o.state !== S.ATTACK || !atk || !o.isContinuousComboActive() ||\n        (o.atkPhase === 2 && o.stateT >= atk.wind + atk.active)) {',
        'stop dodging ended continuous skill')
    src = one(src,
        '    const dangerous = o.state === S.ATTACK && !!a &&\n      (a.heavy || (o.isContinuousComboActive() && a.dmg >= 50));',
        '    const dangerous = o.state === S.ATTACK && !!a &&\n      !(o.atkPhase === 2 && o.stateT >= a.wind + a.active) &&\n      (a.heavy || (o.isContinuousComboActive() && a.dmg >= 50));',
        'stop dodging finished heavy skill')
    return '// ' + TAG + '\n' + src



# V8 is layered over V7 so one installer can also upgrade a previously-installed V7.
V8_TAG = 'FIGHT_ROYALE_KAIZEN_MOBILE_SPIN_V8'


def patch_mobile_spin_kits(src: str) -> str:
    if V8_TAG in src: return src
    src = one(src, '  for (const k of Object.keys(t)) {\n',
'''  // Kaizen's spins now have intentional walking footwork.
  if (kit === "chainblade") {
    if (t.z?.style === "chain_razor_cyclone")
      t.z.desc = "Spin the chainblade while walking/steering toward your foe. Hold Z to extend the spinning attack.";
    if (t.c?.style === "chain_death_spiral")
      t.c.desc = "Walk during the contracting chain whirlwind; each slash follows Kaizen's live position before an overhead finisher.";
  }
  for (const k of Object.keys(t)) {
''', 'Kaizen spin skill descriptions')
    return '// ' + V8_TAG + '\n' + src


def patch_mobile_spin_fighter(src: str) -> str:
    if V8_TAG in src: return src
    src = one(src, '  // --- movement ---------------------------------------------------------------------\n  private move(dt: number) {\n',
'''  // --- movement ---------------------------------------------------------------------
  /** Only Kaizen's sustained chainblade spins unlock walk movement. */
  private kaizenCanWalkWhileSpinning() {
    return this.kit === "chainblade" && this.onGround && this.state === S.ATTACK &&
      this.atkPhase <= 1 && !!this.atk &&
      ["chain_razor_cyclone", "chain_death_spiral", "chain_carousel"].includes(this.atk.style);
  }
  private move(dt: number) {
''', 'Kaizen spin movement helper')

    src = one(src,
        '    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 :\n'
        '      this.state === S.CHARGE ? 0.4 : kiraAirSteer ? 0.92 : nyxAirSteer ? 0.63 : 0;\n',
'''    // Spinning chainblade skills unlock walking while preserving Kira/Nyx aerial steering.
    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 :
      this.state === S.CHARGE ? 0.4 : kiraAirSteer ? 0.92 : nyxAirSteer ? 0.63 :
      this.kaizenCanWalkWhileSpinning() ? 0.72 : 0;
''', 'Kaizen 3D walk while spinning (Kira/Nyx-compatible)')

    anchor = '        if (this.kit === "greatsword" && this.atk.style === "iron_tempest") {\n'
    src = one(src, anchor,
'''        // Arena/platform mode: obey actual left/right input during the spin.
        // Don't grant Kaizen any new lunge or attack speed.
        if (this.kaizenCanWalkWhileSpinning()) {
          target = mx * this.walkSpeed * 0.85;
          if (mx) this.facing = mx;
          walking = mx !== 0;
        }
        if (this.kit === "greatsword" && this.atk.style === "iron_tempest") {
''', 'Kaizen platform walk while spinning')
    return '// ' + V8_TAG + '\n' + src


def patch_mobile_spin_game(src: str) -> str:
    if V8_TAG in src: return src
    # Mobile Death Spiral must have mobile, not fixed-in-place, circular hit tests.
    # Delayed hits and one finisher remain scheduled at their original times.
    src = one(src,
        '    const round = this.round, serial = f.swingSerial, origin = f.root.position.clone();\n    const times = [0.05, 0.28, 0.51, 0.74, 0.97, 1.20, 1.43];\n',
        '    const round = this.round, serial = f.swingSerial;\n    const times = [0.05, 0.28, 0.51, 0.74, 0.97, 1.20, 1.43];\n',
        'Death Spiral remove stationary origin')
    src = one(src,
        '      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;\n      const radius = Math.max(1.7, 4.2 - i * 0.40);\n',
        '      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;\n      const origin = f.root.position.clone(); // spinning field follows Kaizen\n      const radius = Math.max(1.7, 4.2 - i * 0.40);\n',
        'Death Spiral live hit center')
    src = one(src,
        '      f.poseOverride = "cb5_s";\n      this.fxp("slashes", origin.clone().add(new THREE.Vector3(0, 1.9, 0)), "#ffbbc2");\n',
        '      f.poseOverride = "cb5_s";\n      const origin = f.root.position.clone(); // finisher follows Kaizen\n      this.fxp("slashes", origin.clone().add(new THREE.Vector3(0, 1.9, 0)), "#ffbbc2");\n',
        'Death Spiral final strike center')
    return '// ' + V8_TAG + '\n' + src


def patch_mobile_spin_ai(src: str) -> str:
    if V8_TAG in src: return src
    src = one(src,
        '    // Run after normal chase/strafe choices, so fire can veto a dangerous route.\n    this.avoidFireGround(f);\n',
'''    // Chase carefully during spinning Z/C without overriding dodge or fire safety.
    this.kaizenSpinAdvance(f, o);
    // Run after normal chase/strafe choices, so fire can veto a dangerous route.
    this.avoidFireGround(f);
''', 'Kaizen spinning AI call')
    src = one(src,
        '  private position(f: Fighter, o: Fighter, dt: number) {\n',
'''  /** Real walking pressure while the current spin is active; no homing. */
  private kaizenSpinAdvance(f: Fighter, o: Fighter) {
    if (f.kit !== "chainblade" || f.state !== S.ATTACK || !f.onGround ||
        !f.atk || f.atkPhase > 1 || f.isDown() || o.isDown() ||
        !["chain_razor_cyclone", "chain_death_spiral", "chain_carousel"].includes(f.atk.style) ||
        f.intent.dash.lengthSq() > 0.01 || f.intent.block) return;
    const to = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = to.length();
    const seekRange = f.atk.style === "chain_death_spiral" ? 3.1 : 2.0;
    // No auto-target lock or wall crossing; walking ends when target is close.
    if (gap < 1.35 || gap > seekRange + 2.5) return;
    const dir = to.multiplyScalar(1 / Math.max(0.001, gap));
    if (!f.stage) {
      // Do not march into active Ember fire while spinning; retreat/evade AI
      // still takes priority outside this controlled pursuit routine.
      const here = f.root.position.clone().setY(0);
      const nextStep = here.clone().addScaledVector(dir, 0.8);
      for (const patch of this.threats.firePatches(f)) {
        if (Math.abs(patch.pos.y - f.root.position.y) > 1.55) continue;
        const safe = patch.radius + f.radius * 0.3 + 0.22;
        const currentGap = here.distanceTo(patch.pos.clone().setY(0));
        const nextGap = nextStep.distanceTo(patch.pos.clone().setY(0));
        if (nextGap < safe && nextGap < currentGap - 0.05) return;
      }
    }
    if (f.stage) {
      const main = f.stage.plats[0];
      if (!main || f.root.position.x + Math.sign(dir.x) * 0.65 < main.x0 + 0.6 ||
          f.root.position.x + Math.sign(dir.x) * 0.65 > main.x1 - 0.6) return;
      f.intent.move.set(Math.sign(dir.x), 0, 0);
    } else {
      const next = f.root.position.clone().addScaledVector(dir, 0.65).setY(0);
      if (next.length() > f.arenaRadius - 0.25) return;
      f.intent.move.copy(dir);
    }
    f.intent.sprint = false;
  }

  private position(f: Fighter, o: Fighter, dt: number) {
''', 'Kaizen spinning AI chase method')
    return '// ' + V8_TAG + '\n' + src



def main():
    ap = argparse.ArgumentParser(description='Garrick X/Z/C, Bob mines, Kaizen mobile spins/CD/AI, Rook +25% basics')
    ap.add_argument('project', nargs='?', help='optional path to web folder')
    ap.add_argument('--check', action='store_true', help='validate patches only; do not write')
    args = ap.parse_args()
    root = locate_project(pathlib.Path(args.project).expanduser().resolve() if args.project else pathlib.Path.cwd().resolve())
    folder = root / 'src' / 'game'
    original = {name: (folder / name).read_text(encoding='utf-8') for name in FILES}
    patched = {'kits.ts': patch_mobile_spin_kits(patch_kits(original['kits.ts'])),
               'fighter.ts': patch_mobile_spin_fighter(patch_fighter(original['fighter.ts'])),
               'game.ts': patch_mobile_spin_game(patch_game(original['game.ts'])),
               'ai.ts': patch_mobile_spin_ai(patch_ai(original['ai.ts']))}
    changed = [n for n in FILES if original[n] != patched[n]]
    if not changed:
        print('[OK] V8 already installed. Nothing to change.')
        return
    print('[CHECK OK] Patches validated:', ', '.join(changed))
    if args.check: return
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = root / '.fight_royale_v8_backups' / stamp / 'src' / 'game'
    backup.mkdir(parents=True, exist_ok=True)
    for n in changed: shutil.copy2(folder/n, backup/n)
    for n in changed: (folder/n).write_text(patched[n], encoding='utf-8', newline='\n')
    print('[DONE] Corrected V8 installed against current source. Original files backed up at', backup)
    print('Run: npx tsc --noEmit -p .  &&  npm run dev')


if __name__ == '__main__':
    try: main()
    except (PatchError, OSError) as exc:
        print('[ERROR]', exc, file=sys.stderr)
        sys.exit(1)
