#!/usr/bin/env python3
"""Fight Royale merged source-targeted patch (Nov 8, 2026).

Combines fixes for the previously failing AI #6 aerial and AI #7 projectile
interception installers with Rook Meteor Fist pre-guard, Nesa kick range,
and Kira Hundred Kicks duration/visibility changes.

Run from your web folder:
    python apply_merged_ai_rook_nesa_kira.py --dry-run
    python apply_merged_ai_rook_nesa_kira.py

Requires Python 3.9+. No external Python packages. Creates backups and rolls
back changed files if a write fails. Re-running is a no-op.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARK = 'AI_ROOK_NESA_KIRA_MERGED_V1_20261108'
AERIAL_MARK = 'AI_AERIAL_COMBAT_INTELLIGENCE_V1_20261108'
COUNTER_MARK = 'AI_PROJECTILE_CLASH_IQ_V1_20261108'

AERIAL_CONFIG = '// Aerial reads use sampled, *visible* position changes, not enemy future inputs.\n// Detection is rolled once per jump; reactions take real time. All choices are\n// subject to the existing Fighter jump / attack / cooldown / collision rules.\nconst AERIAL_IQ = [\n  { notice: 0.14, react: [0.40, 0.67], landReact: [0.34, 0.50],\n    jump: 0.10, strike: 2.2, uncertainty: 1.20 },\n  { notice: 0.46, react: [0.27, 0.46], landReact: [0.24, 0.38],\n    jump: 0.32, strike: 4.2, uncertainty: 0.70 },\n  { notice: 0.76, react: [0.16, 0.30], landReact: [0.14, 0.25],\n    jump: 0.61, strike: 7.0, uncertainty: 0.34 },\n  { notice: 0.93, react: [0.09, 0.18], landReact: [0.085, 0.16],\n    jump: 0.82, strike: 10.5, uncertainty: 0.17 },\n] as const;\n\n'

AERIAL_FIELDS = '  // AI_AERIAL_COMBAT_INTELLIGENCE: one observation/choice per real jump.\n  private aerialEnemy: Fighter | null = null;\n  private aerialWasUp = false;\n  private aerialHasVelocity = false;\n  private aerialSeenAt = -1;\n  private aerialLastPos = new THREE.Vector3();\n  private aerialVelocity = new THREE.Vector3();\n  private aerialLandingSpot = new THREE.Vector3();\n  private aerialLandingEta = 99;\n  private aerialReactAt = 0;\n  private aerialLandedReactAt = 0;\n  private aerialLandedUntil = 0;\n  private aerialNotice = false;\n  private aerialJumpChosen = false;\n  private aerialJumpSpent = false;\n  private aerialLandingSpent = false;\n  private aerialNoise = new THREE.Vector3();\n\n'

AERIAL_METHODS = '  /** Track a real airborne target by sampling its position as frames pass.\n   * Opponent velY and private attack cooldowns are intentionally NOT read.\n   * Sudden teleports, knockback, and a new opponent invalidate stale samples.\n   */\n  private observeAerialOpponent(f: Fighter, o: Fighter) {\n    const now = this.threats.now();\n    if (o !== this.aerialEnemy) {\n      this.aerialEnemy = o;\n      this.aerialWasUp = false;\n      this.aerialHasVelocity = false;\n      this.aerialSeenAt = -1;\n      this.aerialLandedUntil = 0;\n      this.aerialLandingSpent = false;\n    }\n    if (f.stage || o.stage || o.isDown()) {\n      this.aerialWasUp = false;\n      this.aerialLandedUntil = 0;\n      return;\n    }\n    if (o.onGround) {\n      if (this.aerialWasUp) {\n        this.aerialWasUp = false;\n        const profile = AERIAL_IQ[this.iqLevel];\n        this.aerialLandedReactAt = now + rand(profile.landReact[0], profile.landReact[1]);\n        this.aerialLandedUntil = now + 0.62;\n        this.aerialLandingSpent = false;\n        this.aerialHasVelocity = false;\n      }\n      return;\n    }\n    if (!this.aerialWasUp) {\n      const profile = AERIAL_IQ[this.iqLevel];\n      this.aerialWasUp = true;\n      this.aerialSeenAt = now;\n      this.aerialLastPos.copy(o.root.position);\n      this.aerialVelocity.set(0, 0, 0);\n      this.aerialLandingSpot.copy(o.root.position).setY(0);\n      this.aerialLandingEta = 99;\n      this.aerialHasVelocity = false;\n      this.aerialNotice = Math.random() < profile.notice;\n      this.aerialReactAt = now + rand(profile.react[0], profile.react[1]);\n      this.aerialJumpChosen = Math.random() < profile.jump;\n      this.aerialJumpSpent = false;\n      this.aerialLandingSpent = false;\n      // Imprecise per-jump aim. Do not reroll random noise every animation frame.\n      const angle = rand(-Math.PI, Math.PI);\n      this.aerialNoise.set(Math.cos(angle), 0, Math.sin(angle))\n        .multiplyScalar(rand(0.25, 1) * profile.uncertainty);\n      return;\n    }\n    const elapsed = now - this.aerialSeenAt;\n    if (elapsed <= 0.012) return;\n    const pos = o.root.position;\n    const delta = pos.clone().sub(this.aerialLastPos);\n    // Teleports / frame stalls should not produce absurd perfect predictions.\n    if (elapsed > 0.25 || delta.length() > Math.max(2.7, 28 * elapsed)) {\n      this.aerialHasVelocity = false;\n    } else {\n      const measured = delta.divideScalar(elapsed);\n      if (Math.abs(measured.y) <= 25 && measured.length() <= 28) {\n        this.aerialVelocity.lerp(measured, this.aerialHasVelocity ? 0.65 : 1);\n        this.aerialHasVelocity = true;\n      }\n    }\n    this.aerialSeenAt = now;\n    this.aerialLastPos.copy(pos);\n    if (!this.aerialHasVelocity) {\n      this.aerialLandingEta = 99;\n      return;\n    }\n    // Arena 3D gravity is 22m/s^2. Solve a ballistic landing estimate from\n    // observed height and sampled vertical displacement, not a future position.\n    const g = 22;\n    const vy = this.aerialVelocity.y;\n    const height = Math.max(0, pos.y);\n    const t = (vy + Math.sqrt(vy * vy + 2 * g * height)) / g;\n    this.aerialLandingEta = THREE.MathUtils.clamp(t, 0, 2.25);\n    const lead = Math.min(t, 0.85); // err against over-leading distant jumpers\n    const vx = THREE.MathUtils.clamp(this.aerialVelocity.x, -5.5, 5.5);\n    const vz = THREE.MathUtils.clamp(this.aerialVelocity.z, -5.5, 5.5);\n    this.aerialLandingSpot.set(\n      pos.x + vx * lead + this.aerialNoise.x,\n      0,\n      pos.z + vz * lead + this.aerialNoise.z,\n    );\n    const radius = Math.max(1, f.arenaRadius - 0.55);\n    const flat = this.aerialLandingSpot.length();\n    if (flat > radius) this.aerialLandingSpot.multiplyScalar(radius / flat);\n  }\n\n  /** Approach the estimated touchdown position, not a magically known target.\n   * Normal combat footwork remains the default. Hazard avoidance runs after\n   * this method, so active fire patches can still veto an unsafe route.\n   */\n  private aerialFootwork(f: Fighter, o: Fighter) {\n    const now = this.threats.now();\n    if (!this.aerialNotice || !this.aerialWasUp || now < this.aerialReactAt ||\n        f.stage || o.stage || f.isDown() || f.state !== S.IDLE ||\n        f.intent.block || this.blockHold > 0 || this.blockWait >= 0 ||\n        f.intent.dash.lengthSq() > 0.01 || this.projectileSwordCommit > 0 ||\n        f.chainBindTarget || f.chainBoundBy || this.iqBaitPhase !== "none") return;\n    const target = this.aerialHasVelocity && this.aerialLandingEta < 1.25\n      ? this.aerialLandingSpot : o.root.position;\n    const toward = target.clone().sub(f.root.position).setY(0);\n    const gap = toward.length();\n    if (gap < 0.10) return;\n    const airReach = f.attacks.air_l1?.reach ?? f.attacks.l1?.reach ?? 1.7;\n    // A melee fighter should take a position inside actual weapon range.\n    // Ranged fighters preserve room to cast, instead of dashing face-first.\n    const preferred = RANGED.has(f.kit) ? 4.5 : Math.max(1.05, airReach * 0.77);\n    if (gap > preferred + 0.38 && gap < 9.5) {\n      f.intent.move.copy(this.theaterDirection(f, o, toward));\n    } else if (!RANGED.has(f.kit) && gap < 0.82) {\n      f.intent.move.copy(this.theaterDirection(f, o, toward.negate())).multiplyScalar(0.36);\n    }\n  }\n\n  /** A planned counter-jump is allowed only in normal 3D arena mode.\n   * No auto-launches/teleports: Fighter still processes a normal Space press.\n   */\n  private shouldAerialJump(f: Fighter, o: Fighter, gap: number): boolean {\n    if (!this.aerialNotice || !this.aerialJumpChosen || this.aerialJumpSpent ||\n        !this.aerialWasUp || !this.aerialHasVelocity ||\n        this.threats.now() < this.aerialReactAt || f.stage || o.stage ||\n        f.intent.block || f.intent.dash.lengthSq() > 0.01 ||\n        this.blockHold > 0 || this.blockWait >= 0 ||\n        this.projectileSwordCommit > 0 || this.threats.firePatches(f).some(p =>\n          f.root.position.distanceTo(p.pos) < p.radius + 0.5) ||\n        this.aerialLandingEta < 0.34 || this.aerialLandingEta > 1.25 ||\n        o.root.position.y < 0.85 || o.root.position.y > 3.4 ||\n        gap > Math.max(2.6, (f.attacks.air_l1?.reach ?? 1.9) + 0.75)) return false;\n    this.aerialJumpSpent = true;\n    return true;\n  }\n\n  /** Small post-touchdown attack opportunity. The target gets no forced stun,\n   * and the fighter must already be in legitimate basic attack range.\n   */\n  private aerialLandingPunish(f: Fighter, o: Fighter): boolean {\n    const now = this.threats.now();\n    if (!this.aerialNotice || this.aerialLandingSpent || !o.onGround ||\n        now < this.aerialLandedReactAt || now > this.aerialLandedUntil ||\n        !f.onGround || f.stage || o.stage || f.state !== S.IDLE ||\n        f.atkLock > 0 || f.intent.skill || f.intent.block ||\n        this.blockHold > 0 || this.queue.length || this.hold > 0 ||\n        this.projectileSwordCommit > 0 || RANGED.has(f.kit)) return false;\n    const basic = f.attacks.l1;\n    if (!basic || basic.type !== "melee") return false;\n    const gap = f.root.position.clone().setY(0)\n      .distanceTo(o.root.position.clone().setY(0));\n    if (gap > basic.reach + 0.10) return false;\n    // A landing in an active attack is not a safe punish by itself.\n    if (o.state === S.ATTACK && o.atkPhase < 2 && o.atk?.type === "melee") return false;\n    this.aerialLandingSpent = true;\n    this.queue = [[0, 0.065]];\n    this.hold = 0;\n    return true;\n  }\n\n  private aerialAirStrikeChance(o: Fighter, dt: number): boolean {\n    // Even when a jump wasn\'t recognized, the CPU may react to a target\n    // it can presently reach. Timing depends on difficulty, not frame rate.\n    const profile = AERIAL_IQ[this.iqLevel];\n    const speed = !o.onGround && this.aerialNotice &&\n      this.threats.now() >= this.aerialReactAt ? profile.strike * 1.2 : profile.strike;\n    return Math.random() < 1 - Math.exp(-Math.max(0, dt) * speed);\n  }\n\n'

COUNTER_CONFIG = '// AI_PROJECTILE_CLASH_IQ: incoming shots are seen once each, never rerolled\n// per frame. A read is an imperfect estimate of a physical mid-flight clash.\nconst PROJECTILE_CLASH_IQ = [\n  { notice: 0.10, reaction: [0.34, 0.54], tolerance: 0.34, reserve: 0.82 },\n  { notice: 0.43, reaction: [0.23, 0.37], tolerance: 0.26, reserve: 0.66 },\n  { notice: 0.72, reaction: [0.13, 0.24], tolerance: 0.18, reserve: 0.42 },\n  { notice: 0.91, reaction: [0.060, 0.135], tolerance: 0.11, reserve: 0.22 },\n] as const;\ntype CounterfireRead = { reactAt: number; wants: boolean; spent: boolean };\n\n'

COUNTER_FIELDS = '  // AI_PROJECTILE_CLASH_IQ: an independent, per-shot decision memory.\n  private counterfireEnemy: Fighter | null = null;\n  private counterfireReads = new Map<number, CounterfireRead>();\n  private counterfireRecoveryUntil = 0;\n\n'

COUNTER_METHODS = '  /** Observe only projectiles already in the arena. No future inputs,\n   * target cooldowns, or hidden opponent abilities are inspected.\n   */\n  private observeCounterfire(f: Fighter, o: Fighter) {\n    if (this.counterfireEnemy !== o) {\n      this.counterfireEnemy = o;\n      this.counterfireReads.clear();\n      this.counterfireRecoveryUntil = 0;\n    }\n    const now = this.threats.now();\n    const shots = this.threats.projectiles();\n    const living = new Set<number>();\n    const readyShot = (f.attacks.l1?.type === "projectile" && f.atkLock <= 0) ||\n      ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]\n        .some(k => f.attacks[k]?.type === "projectile" && (f.cooldowns[k] ?? 1) <= 0);\n    for (const p of shots) {\n      living.add(p.id);\n      if (this.counterfireReads.has(p.id)) continue;\n      if (!readyShot || p.target !== f || (p.team !== undefined && p.team === f.team) ||\n          p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb") continue;\n      const eta = this.projectileTimeToContact(f, p);\n      if (eta < 0.18 || eta > 1.75) continue;\n      const profile = PROJECTILE_CLASH_IQ[this.iqLevel];\n      this.counterfireReads.set(p.id, {\n        reactAt: now + rand(profile.reaction[0], profile.reaction[1]),\n        wants: Math.random() < profile.notice, spent: false,\n      });\n    }\n    for (const id of this.counterfireReads.keys()) {\n      if (!living.has(id)) this.counterfireReads.delete(id);\n    }\n    if (this.counterfireReads.size > 180) this.counterfireReads.clear();\n  }\n\n  /** Closest approach for an actually fired shot vs a moving hostile shot.\n   * Game.fireProjectiles aims at the fighter\'s current opponent, so we forecast\n   * that SAME aim and spread, not an impossible AI-only aimed projectile.\n   * Real game projectile collision detection determines the eventual result.\n   */\n  private predictCounterfireCollision(f: Fighter, o: Fighter,\n    p: ReturnType<Threats["projectiles"]>[number],\n    a: Fighter["attacks"][string]): { time: number; miss: number } | null {\n    if (a.type !== "projectile" || a.speed <= 0 ||\n        p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb") return null;\n    const eta = this.projectileTimeToContact(f, p);\n    if (eta >= 999) return null;\n    const origin = f.model.castPoint.getWorldPosition(new THREE.Vector3());\n    const toward = o.chest().sub(origin);\n    if (toward.lengthSq() < 0.05) return null;\n    const aim = toward.normalize();\n    // Conservative input and animation-frame overhead. Attack wind remains real.\n    const launch = Math.max(0.025, a.wind) + 0.025;\n    if (launch >= eta - 0.055) return null;\n    const offsets = Math.max(1, Math.min(7, a.count));\n    const profile = PROJECTILE_CLASH_IQ[this.iqLevel];\n    let best: { time: number; miss: number } | null = null;\n    for (let i = 0; i < offsets; i++) {\n      const angle = offsets === 1 ? 0 : -a.spread + 2 * a.spread * i / (offsets - 1);\n      const ownVel = aim.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), angle)\n        .multiplyScalar(a.speed);\n      const incomingAtLaunch = p.pos.clone().addScaledVector(p.vel, launch);\n      const separation = origin.clone().sub(incomingAtLaunch);\n      const relativeVel = ownVel.sub(p.vel);\n      const speedSq = relativeVel.lengthSq();\n      if (speedSq < 1.0) continue;\n      const afterLaunch = -separation.dot(relativeVel) / speedSq;\n      if (afterLaunch < 0.015 || afterLaunch > 1.10) continue;\n      const collisionTime = launch + afterLaunch;\n      // An interception after the shot reaches this fighter isn\'t defensive.\n      if (collisionTime > eta - 0.025) continue;\n      const miss = separation.addScaledVector(relativeVel, afterLaunch).length();\n      const ownRadius = Math.max(0.14, Math.min(0.48, a.size *\n        (a.style === "wave" || a.style === "shock" ? 0.37 : 0.23)));\n      const theirSize = p.size ?? 1;\n      const theirRadius = Math.max(0.14, Math.min(0.48, theirSize *\n        (p.style === "wave" || p.style === "shock" ? 0.37 : 0.23)));\n      // Difficulty uncertainty is a *stricter* collision requirement for easier\n      // bots, not a fake enlargement of the real collision hitboxes.\n      const believable = ownRadius + theirRadius - profile.tolerance;\n      if (miss > Math.max(0.09, believable)) continue;\n      if (!best || miss < best.miss) best = { time: collisionTime, miss };\n    }\n    return best;\n  }\n\n  /** Try ONE legal action per observed shot. Ordinary dodge/parry handling\n   * takes over whenever the timing, angle or real attack availability fails.\n   */\n  private projectileCounterfire(f: Fighter, o: Fighter): boolean {\n    const now = this.threats.now();\n    if (now < this.counterfireRecoveryUntil || f.isDown() || o.isDown() ||\n        f.state !== S.IDLE || !f.onGround || f.atkLock > 0 ||\n        f.chainBindT > 0 || f.chainBoundBy || f.dashing() ||\n        f.intent.block || f.intent.skill || f.intent.dash.lengthSq() > 0.01 ||\n        this.blockWait >= 0 || this.blockHold > 0 || this.queue.length > 0 ||\n        this.hold > 0 || this.projectileSwordCommit > 0 ||\n        this.comboParryTarget > now ||\n        (f.kit === "sickle" && f.bloodFestivalT > 0) ||\n        this.threats.firePatches(f).some(p =>\n          f.root.position.distanceTo(p.pos) < p.radius + 0.35)) return false;\n    const profile = PROJECTILE_CLASH_IQ[this.iqLevel];\n    let best: { shot: number; key: string; score: number } | null = null;\n    for (const p of this.threats.projectiles()) {\n      const read = this.counterfireReads.get(p.id);\n      if (!read?.wants || read.spent || now < read.reactAt || p.target !== f ||\n          p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb" ||\n          (p.team !== undefined && p.team === f.team)) continue;\n      const eta = this.projectileTimeToContact(f, p);\n      if (eta <= 0.10 || eta > 1.50) continue;\n      const heavyIncoming = p.heavy === true || (p.size ?? 1) > 1.65;\n      const keys = ["l1", "z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])];\n      for (const key of keys) {\n        const a = f.attacks[key];\n        if (!a || a.type !== "projectile" ||\n            (key !== "l1" && (f.cooldowns[key] ?? 1) > 0)) continue;\n        const forecast = this.predictCounterfireCollision(f, o, p, a);\n        if (!forecast) continue;\n        // Avoid wasting an expensive skill if a free normal projectile is a\n        // plausible intercept. High-strength shots can justify a heavier reply.\n        const strongReply = a.heavy || a.pierce || a.dmg >= 95;\n        if (heavyIncoming && !strongReply && this.iqLevel >= 2) continue;\n        const expenditure = key === "l1" ? 0 :\n          a.cd * (1.2 - profile.reserve) * 0.55;\n        const score = (heavyIncoming && strongReply ? 4.8 : 0) +\n          (key === "l1" ? 5.4 : 1.2) - expenditure - forecast.miss * 3 -\n          forecast.time * 0.3;\n        if (!best || score > best.score) best = { shot: p.id, key, score };\n      }\n    }\n    if (!best) return false;\n    const choice = best;\n    const read = this.counterfireReads.get(choice.shot);\n    if (read) read.spent = true;\n    this.counterfireRecoveryUntil = now + (choice.key === "l1" ? 0.32 : 0.48);\n    // Ordinary Fighter inputs only. These go through the normal attack windup,\n    // cooldown, hit tests and Game.resolveProjectileClashes.\n    this.queue = [];\n    this.hold = 0;\n    this.blockWait = -1;\n    f.intent.block = false;\n    f.intent.move.set(0, 0, 0);\n    f.intent.sprint = false;\n    if (choice.key === "l1") f.intent.attack = true;\n    else {\n      f.intent.attack = false;\n      f.intent.skill = choice.key;\n      this.skillCd = Math.max(this.skillCd, 0.27);\n    }\n    return true;\n  }\n\n'


def replace_exact(text: str, old: str, new: str, what: str) -> str:
    count=text.count(old)
    if count != 1:
        raise ValueError(f"{what}: expected 1 match, got {count}. No files written. "
                         "Upload your newest game ZIP to generate an updated patch.")
    return text.replace(old,new,1)

ROOK_FIELDS = '''  // Seen Rook Meteor Fist casts: choose once per jump, not once per frame.
  private rookMeteorSerial = -1;
  private rookMeteorWants = false;
  private rookMeteorReactAt = -1;

'''
ROOK_METHOD = '''  /** The leap itself is a visible warning: the scheduled ground strike marker
   * only appears on touchdown, too late to finish raising a shield. Hold
   * the NORMAL block button before touchdown, never grant fake invulnerability.
   */
  private defendRookMeteor(f: Fighter, o: Fighter): boolean {
    const a = o.atk;
    if (o.kit !== "knuckles" || o.state !== S.ATTACK ||
        a?.name !== "Meteor Fist" || o.atkPhase === 2) return false;
    if (f.isDown() || !f.onGround || f.stage || o.stage ||
        f.chainBoundBy || f.chainBindTarget) return false;
    const now = this.threats.now();
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    // The attack leap homes toward its real opponent, so it can close a gap.
    if (gap > 7.0 || o.opponent !== f) return false;
    if (o.swingSerial !== this.rookMeteorSerial) {
      this.rookMeteorSerial = o.swingSerial;
      const chance = [0.22, 0.52, 0.82, 0.995][this.iqLevel];
      this.rookMeteorWants = Math.random() < chance;
      const min = [0.32, 0.21, 0.12, 0.035][this.iqLevel];
      const max = [0.48, 0.33, 0.20, 0.065][this.iqLevel];
      this.rookMeteorReactAt = now + rand(min, max);
    }
    if (!this.rookMeteorWants || now < this.rookMeteorReactAt) return false;
    const guardCost = a.guard * (f.judgmentT > 0 ? 1.5 : 1);
    if (f.guard > guardCost + 8 &&
        (f.state === S.IDLE || f.state === S.BLOCK)) {
      // Early regular guard works when the landing marker is too late.
      this.queue = []; this.hold = 0;
      this.blockWait = -1; this.blockHold = 0;
      f.intent.block = true;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.jump = false;
      f.intent.move.set(0, 0, 0);
      f.intent.dash.set(0, 0, 0);
      return true;
    }
    // A depleted shield must not be treated as protection. Normal dash still
    // obeys its cooldown and invulnerability timing; no guaranteed escape.
    if (f.state === S.IDLE && f.dashCd <= 0 && !f.dashing() &&
        (o.atkPhase === 1 || o.stateT > a.wind * 0.5)) {
      const away = f.root.position.clone().sub(o.root.position).setY(0);
      if (away.lengthSq() < 0.01) away.set(f.id % 2 ? 1 : -1, 0, 0);
      away.normalize();
      const destination = f.root.position.clone().setY(0).addScaledVector(away, 3.4);
      if (destination.length() >= f.arenaRadius - 0.4)
        away.set(-away.z, 0, away.x);
      f.intent.dash.copy(away);
      f.intent.move.copy(away);
      f.intent.block = false;
      f.intent.attack = false;
      f.intent.skill = "";
      return true;
    }
    return false;
  }

'''

def patch_ai(source: str) -> str:
    if MARK in source:
        return source
    out=source
    # Both old installers aborted without writing in the supplied ZIP, but
    # accept installations of either one performed subsequently.
    missing_aerial = AERIAL_MARK not in out
    missing_counter = COUNTER_MARK not in out
    if missing_aerial:
        out=AERIAL_MARK+'\n'+out
        out=replace_exact(out, 'const RANGED = new Set(["mage", "bow", "bomb"]);\n',
                          'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n'+AERIAL_CONFIG,
                          'aerial difficulty settings')
        out=replace_exact(out,'  private antiAirCd = 0;\n', AERIAL_FIELDS+'  private antiAirCd = 0;\n','aerial fields')
        out=replace_exact(out,'  private airDive(f: Fighter, o: Fighter, dt: number): boolean {',
                          AERIAL_METHODS+'  private airDive(f: Fighter, o: Fighter, dt: number): boolean {',
                          'aerial methods')
        out=replace_exact(out,'    if (!o || o.isDown()) return;\n',
                          '    if (!o || o.isDown()) return;\n    this.observeAerialOpponent(f, o);\n',
                          'aerial observation')
        out=replace_exact(out,'    this.kaizenSpinAdvance(f, o);\n',
                          '    this.kaizenSpinAdvance(f, o);\n    this.aerialFootwork(f, o);\n','aerial footwork')
        out=replace_exact(out,'        Math.random() < dt * 0.24) {',
                          '        (this.shouldAerialJump(f, o, flatGap) ||\n          (o.onGround && Math.random() < dt * 0.12))) {',
                          'aerial interception trigger')
        out=replace_exact(out,'        Math.random() < dt * 7.0) {',
                          '        this.aerialAirStrikeChance(o, dt)) {',
                          'aerial real strike cadence')
        out=replace_exact(out,'    const iqActed = !this.aiAirTap && !f.intent.skill &&\n',
                          '    const landedActed = !this.aiAirTap && !f.intent.skill &&\n'
                          '      this.aerialLandingPunish(f, o);\n'
                          '    const iqActed = !landedActed && !this.aiAirTap && !f.intent.skill &&\n',
                          'landing before ordinary offense')
        # The previous installer assumed patternActed did not exist, hence its
        # "preserve landing attack queue" missing anchor. This is the correct one.
        out=replace_exact(out,'    const patternActed = !iqActed && !this.aiAirTap && !f.intent.skill &&\n',
                          '    const patternActed = !landedActed && !iqActed && !this.aiAirTap && !f.intent.skill &&\n',
                          'landing vs pattern footwork')
        out=replace_exact(out,'    if (!this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&\n',
                          '    if (!landedActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&\n',
                          'landing vs normal skill offense')
    if missing_counter:
        out=COUNTER_MARK+'\n'+out
        out=replace_exact(out,
            'projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number }[];',
            'projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number; '
            'team?: number; style?: string; size?: number; atkType?: string; heavy?: boolean }[];',
            'projectile threat interface')
        out=replace_exact(out,
            'const RANGED = new Set(["mage", "bow", "bomb"]);\n',
            'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n'+COUNTER_CONFIG,
            'counterfire difficulty settings')
        out=replace_exact(out,'  private antiAirCd = 0;\n',
                          COUNTER_FIELDS+'  private antiAirCd = 0;\n','counterfire memory')
        out=replace_exact(out,
            '  // Predict the actual crossing time of the projectile through the fighter\'s chest.',
            COUNTER_METHODS+'  // Predict the actual crossing time of the projectile through the fighter\'s chest.',
            'counterfire methods')
        # Observe current projectiles after existing cooldown observation and
        # aerial data (if installed). No dependency on exact previous script text.
        out=replace_exact(out,'    this.observeEnemyCooldown(o);\n',
                          '    this.observeEnemyCooldown(o);\n    this.observeCounterfire(f, o);\n',
                          'counterfire sampling')
        out=replace_exact(out,'    this.defendLongCombo(f, o);\n',
                          '    this.defendLongCombo(f, o);\n'
                          '    if (this.projectileCounterfire(f, o)) return;\n',
                          'counterfire priority')
        out=replace_exact(out,
            '      const predicted = this.projectileTimeToContact(f, p);\n'
            '      // Do not consume the shot at spawn time.',
            '      const predicted = this.projectileTimeToContact(f, p);\n'
            '      // Defer the first defensive reaction only if counterfire has\n'
            '      // enough time to fire before actual collision.\n'
            '      const counterRead = this.counterfireReads.get(p.id);\n'
            '      if (counterRead?.wants && !counterRead.spent && predicted < 999) {\n'
            '        const remaining = counterRead.reactAt - this.threats.now();\n'
            '        if (remaining > 0 && remaining + 0.17 < predicted) continue;\n'
            '      }\n'
            '      // Do not consume the shot at spawn time.',
            'fallback defense observation')
    # Higher skill still requires physically possible action. Against Rook's
    # landing attack, the small post-touchdown ground marker is too late.
    out=replace_exact(out,'  private antiAirCd = 0;\n',
                      ROOK_FIELDS+'  private antiAirCd = 0;\n','Rook memory')
    out=replace_exact(out,
        '  /** Kaizen\'s V Serpent Bind has TWO existing legal follow-ups:',
        ROOK_METHOD+'  /** Kaizen\'s V Serpent Bind has TWO existing legal follow-ups:',
        'Rook Meteor Fist guard method')
    out=replace_exact(out,'    this.observeEnemyCooldown(o);\n',
        '    this.observeEnemyCooldown(o);\n    if (this.defendRookMeteor(f, o)) return;\n',
        'Rook Meteor Fist priority')
    # Nesa's X real contact is a 0.12s-delayed kick, *not* a 5m teleport.
    out=replace_exact(out,
        'a.name === "Upsie Daisie" ? gap <= Math.min(6.55, a.reach + a.lunge * 0.31) :',
        'a.name === "Upsie Daisie" ? gap <= Math.min(3.35, a.reach + 0.72) :',
        'Nesa theater real kick reach')
    out=replace_exact(out,
        'if (distance > 5.65) viable = false;',
        'if (distance > 3.35 || !f.onGround) viable = false;',
        'Nesa AI max cast range')
    out=replace_exact(out,
        'points += distance > 2.20 && distance < 5.15 ? 2.65 :',
        'points += distance > 2.20 && distance < 3.25 ? 2.65 :',
        'Nesa priority cast band')
    out=replace_exact(out,
        'else if (gap > 2.7 && gap < 6.3 && intent(0.83))',
        'else if (gap > 2.7 && gap < 4.2 && intent(0.83))',
        'Nesa chase planning band')
    # Block unsafe generic "skill available" decisions from asking the
    # kick before it is within the actual delayed contact distance.
    out=replace_exact(out,
        '    if (a.type === "melee" || a.type === "phantom") {\n'
        '      viable = distance < a.reach + Math.max(0.85, a.lunge * 0.19);',
        '    if (a.type === "melee" || a.type === "phantom") {\n'
        '      viable = a.name === "Upsie Daisie"\n'
        '        ? distance <= Math.min(3.35, a.reach + 0.72) && f.onGround\n'
        '        : distance < a.reach + Math.max(0.85, a.lunge * 0.19);',
        'Nesa personalized skill reach')
    return '// '+MARK+'\n'+out


def patch_game(source: str) -> str:
    if MARK in source:
        return source
    if 'PROJECTILE_VS_PROJECTILE_CLASH_V1' not in source:
        raise ValueError('Projectile-vs-projectile collision system missing; '
                         'install apply_projectile_clashes.py before this update.')
    out=source
    if 'AI_PROJECTILE_CLASH_IQ: visible shape/size' not in out:
        out=replace_exact(out,
           'projectiles: () => this.projectiles.filter((p) => !p.visualOnly).map((p) => ({ target: p.target, pos: p.pos, vel: p.vel, id: p.id })),',
           '''// AI_PROJECTILE_CLASH_IQ: only visible live shots and their public appearance.
    projectiles: () => this.projectiles.filter((p) => !p.visualOnly && !p.done).map((p) => ({
      target: p.target, pos: p.pos, vel: p.vel, id: p.id, team: p.team,
      style: p.atk?.style ?? "", size: p.size, atkType: p.atk?.type ?? "",
      heavy: p.atk?.heavy ?? false,
    })),''',
           'visible projectile threat feed')
    return '// '+MARK+'\n'+out


def patch_fighter(source: str) -> str:
    if MARK in source: return source
    out=source
    out=replace_exact(out,
        '''  /** Hide render model only, leaving root and server hitboxes intact. */
  private updateKiraCastVisual() {
    if (this.kit !== "kicks" || this.model.loading) return;
    const casting = this.puppet
      ? this.state === S.ATTACK && this.poseName.startsWith("kira_hundred_cast_")
      : this.isKiraHundredKicksCasting();
    this.model.visible = !casting;
  }''',
        '''  /** Kira V remains visible. The existing casting poses play while
   * movement/dash/extra attacks stay locked until the stance finishes. */
  private updateKiraCastVisual() {
    if (this.kit !== "kicks" || this.model.loading) return;
    this.model.visible = true;
  }''',
        'Kira V visible stance')
    return '// '+MARK+'\n'+out


def patch_kits(source: str) -> str:
    if MARK in source: return source
    out=source
    out=replace_exact(out,
      'desc: "Stand completely still and vanish while casting eight phantom strikes. Damage reduced by 25%. Can be interrupted and hit while invisible.", cd: 10, type: "strike", wind: 0.15, recover: 0.6, dmg: 30, guard: 10, knock: 0.8, stun: 0.3, delay: 0.2, radius: 1.5, repeat: 8, interval: 0.06, style: "slashes"',
      'desc: "Visible, immobile casting pose with six phantom strikes. Casting duration reduced by 25%, damage remains 30 per hit. Still vulnerable to attacks.", cd: 10, type: "strike", wind: 0.1125, active: 0.06, recover: 0.45, dmg: 30, guard: 10, knock: 0.8, stun: 0.3, delay: 0.15, radius: 1.5, repeat: 6, interval: 0.045, style: "slashes"',
      'Kira V 25% shorter timeline')
    return '// '+MARK+'\n'+out


def locate_root(arg: str | None) -> Path:
    choices = []
    if arg:
        src = Path(arg).expanduser().resolve()
        choices=[src, src / 'web']
    else:
        choices=[Path.cwd(), Path.cwd()/'web', Path(__file__).resolve().parent]
    for root in choices:
        if all((root/'src'/'game'/file).is_file() for file in
               ('ai.ts', 'game.ts', 'fighter.ts', 'kits.ts')):
            return root
    raise FileNotFoundError('Cannot locate web/src/game/{ai,game,fighter,kits}.ts; '
                            'put this .py file inside your web folder or use --path.')

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path',help='Path to game web directory')
    parser.add_argument('--dry-run',action='store_true',help='Validate anchors without changes')
    args=parser.parse_args()
    try:
        root=locate_root(args.path)
        funcs={'ai.ts':patch_ai, 'game.ts':patch_game,
               'fighter.ts':patch_fighter, 'kits.ts':patch_kits}
        tasks=[]
        for name,fn in funcs.items():
            path=root/'src'/'game'/name
            before=path.read_text(encoding='utf-8')
            after=fn(before)
            if after!=before:tasks.append((path,before,after))
        if not tasks:
            print('Already installed; no changes needed.')
            return 0
        if args.dry_run:
            print('VALIDATED against current source; would update:')
            for path,_,_ in tasks:print(' ',path.relative_to(root))
            print('No files changed.')
            return 0
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        for path,_,_ in tasks:
            shutil.copy2(path,path.with_name(path.name+'.before_merged_ai_'+stamp+'.bak'))
        written=[]
        try:
            for path,before,after in tasks:
                temp=path.with_name('.'+path.name+'.merged_ai.tmp')
                temp.write_text(after,encoding='utf-8')
                temp.replace(path)
                written.append((path,before))
        except Exception:
            for path,before in written:path.write_text(before,encoding='utf-8')
            raise
        print('Installed merged Fight Royale AI & combat balance patch:')
        for path,_,_ in tasks:print(' ',path.relative_to(root))
        print('Backups created. This installer replaces the failed aerial/projectile AI installers.')
        return 0
    except Exception as exc:
        print('INSTALLATION FAILED:',exc,file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
