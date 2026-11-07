#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Fight Royale: 17 smart AI personalities + Kira Phantom Step 16s + Ash bow nerf.

Run from Fight Royale web folder:
    python Install_FightRoyale_17_Smart_AI_Kira_Ash_Balance.py
Or:
    python Install_FightRoyale_17_Smart_AI_Kira_Ash_Balance.py "C:\path\to\web"
Use --check to validate without writing.
Designed to ADD new AI code without removing Nesa evasion, Kira aerial movement,
existing spectator mode, weapon changes, or other combat patches.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse
import os
import re
import shutil
import sys
import tempfile

MARKER = 'SMART_AI_PERSONALITIES_17_FINAL_V2_20261107'
class PatchError(RuntimeError): pass

def once(s: str, old: str, new: str, tag: str) -> str:
    found = s.count(old)
    if found != 1: raise PatchError(f'{tag}: expected one code anchor; found {found}. No files changed.')
    return s.replace(old, new, 1)

def project_root(source: str | None) -> Path:
    p = Path(source).expanduser().resolve() if source else Path.cwd().resolve()
    for root in (p, p/'web'):
        if (root/'src/game/ai.ts').is_file() and (root/'src/game/kits.ts').is_file() and (root/'src/game/roster.ts').is_file():
            return root
    raise PatchError('Project not found: run inside Fight Royale web folder or pass path to web.')

AI_PROFILES = '// SMART_AI_PERSONALITIES_17_FINAL_V1 — 17 unique fighting styles; AI inputs only.\n// This does not rewrite fighter damage/animations. Spectator and reactive dodges remain.\n// Profile keys match roster Look.name, so two knights and the three mages differ.\ntype FightStyle = {\n  range: number; heavy: number; combo: number; bait: number; pressure: number;\n  skillBias: readonly [number, number, number];\n};\nconst FIGHT_STYLES: Readonly<Record<string, FightStyle>> = {\n  aster: { range: 1.70, heavy: 0.26, combo: 0.65, bait: 0.52, pressure: 0.42, skillBias: [1.5, 1.0, 0.8] },\n  vesper: { range: 1.55, heavy: 0.18, combo: 0.94, bait: 0.18, pressure: 0.90, skillBias: [1.0, 1.35, 0.9] },\n  garrick: { range: 2.40, heavy: 0.45, combo: 0.42, bait: 0.70, pressure: 0.30, skillBias: [0.95, 1.2, 1.3] },\n  kaede: { range: 1.92, heavy: 0.34, combo: 0.77, bait: 0.65, pressure: 0.50, skillBias: [1.75, 0.8, 1.0] },\n  ember: { range: 5.50, heavy: 0.36, combo: 0.45, bait: 0.20, pressure: 0.26, skillBias: [0.8, 1.3, 1.3] },\n  marina: { range: 5.25, heavy: 0.27, combo: 0.42, bait: 0.24, pressure: 0.25, skillBias: [1.5, 1.25, 0.9] },\n  nyx: { range: 1.53, heavy: 0.17, combo: 0.90, bait: 0.62, pressure: 0.85, skillBias: [1.4, 0.9, 1.25] },\n  rook: { range: 1.35, heavy: 0.16, combo: 0.98, bait: 0.12, pressure: 1.00, skillBias: [1.3, 0.75, 1.3] },\n  gale: { range: 1.67, heavy: 0.23, combo: 0.82, bait: 0.55, pressure: 0.73, skillBias: [0.85, 1.4, 1.1] },\n  bob: { range: 5.20, heavy: 0.27, combo: 0.44, bait: 0.45, pressure: 0.16, skillBias: [1.3, 1.1, 1.4] },\n  kira: { range: 1.68, heavy: 0.15, combo: 0.96, bait: 0.59, pressure: 0.90, skillBias: [1.35, 1.1, 1.2] },\n  raven: { range: 5.75, heavy: 0.40, combo: 0.47, bait: 0.20, pressure: 0.30, skillBias: [1.4, 1.25, 1.35] },\n  ash: { range: 6.20, heavy: 0.50, combo: 0.40, bait: 0.44, pressure: 0.19, skillBias: [1.5, 1.0, 1.4] },\n  veyr: { range: 1.59, heavy: 0.15, combo: 0.98, bait: 0.68, pressure: 0.94, skillBias: [1.0, 1.35, 1.5] },\n  zarek: { range: 2.10, heavy: 0.30, combo: 0.91, bait: 0.35, pressure: 0.86, skillBias: [1.3, 1.2, 1.45] },\n  kaizen: { range: 2.65, heavy: 0.33, combo: 0.78, bait: 0.51, pressure: 0.71, skillBias: [1.2, 1.45, 1.15] },\n  nesa: { range: 2.38, heavy: 0.43, combo: 0.64, bait: 0.62, pressure: 0.52, skillBias: [1.05, 1.15, 1.2] },\n};'
AI_FIELDS = "  // Personality's brief feints and reposition decisions use ordinary movement inputs.\n  private tacticsT = 0;\n  private tacticsDir = 1;\n  private tacticsCd = 0;\n  private seenClashSwing = -1;"
AI_CLASH = '      // Zarek deliberately meets a real enemy blade occasionally to earn Clash Momentum.\n      // Unlike a forced clash this is a normal light input with genuine wind-up timing.\n      if (f.kit === "glaive" && f.onGround && f.state === S.IDLE &&\n          o.atk?.type === "melee" && !o.atk.no_parry &&\n          dist < f.attacks.l1.reach + 0.15 && tth >= f.attacks.l1.wind * 0.50 &&\n          this.seenClashSwing !== o.swingSerial &&\n          Math.random() < this.p.block * (f.clashMomentum < 3 ? 0.58 : 0.33)) {\n        this.seenClashSwing = o.swingSerial;\n        this.blockWait = -1; this.blockHold = 0;\n        this.queue = [[0, 0.065]]; this.hold = 0;\n        return;\n      }\n'
AI_METHODS = '/** Choose footwork without teleporting or exceeding the arena movement limits.\n * Leave projectile/hazard dodge decisions alone; terrain avoidance runs after this. */\nprivate tacticalFootwork(f: Fighter, o: Fighter, dt: number) {\n  const style = FIGHT_STYLES[f.look.name.toLowerCase()];\n  if (!style || f.isDown() || !f.onGround || f.state !== S.IDLE ||\n      this.sideT > 0 || this.blockHold > 0 || this.blockWait >= 0) return;\n  this.tacticsCd = Math.max(0, this.tacticsCd - dt);\n  const toward = o.root.position.clone().sub(f.root.position).setY(0);\n  const distance = toward.length();\n  if (distance < 0.05) return;\n  toward.divideScalar(distance);\n  const tangent = new THREE.Vector3(-toward.z, 0, toward.x);\n  const punish = this.hasPunishWindow(o);\n  // Never perform a deliberate bait while a real melee strike is almost active.\n  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&\n    o.atk?.type === "melee" && distance < o.atk.reach + 0.7;\n  if (danger) { this.tacticsT = 0; return; }\n  if (this.tacticsT <= 0 && this.tacticsCd <= 0 &&\n      distance < style.range + 0.75 && !punish &&\n      (o.state === S.BLOCK || (o.state === S.IDLE && distance < style.range - 0.28)) &&\n      Math.random() < dt * style.bait * (0.45 + this.p.block)) {\n    this.tacticsT = rand(0.23, 0.44);\n    this.tacticsDir = Math.random() < 0.5 ? -1 : 1;\n    this.tacticsCd = rand(1.1, 2.8);\n  }\n  if (this.tacticsT > 0) {\n    this.tacticsT -= dt;\n    const retreat = toward.clone().negate().multiplyScalar(0.65)\n      .addScaledVector(tangent, this.tacticsDir * 0.76).normalize();\n    const test = f.root.position.clone().addScaledVector(retreat, 1.1);\n    // At the arena edge, replace backward drifting with a sideways orbit.\n    if (Math.hypot(test.x, test.z) > f.arenaRadius - 0.55) {\n      const side1 = tangent.clone().multiplyScalar(this.tacticsDir);\n      const side2 = side1.clone().negate();\n      const safe = [side1, side2].sort((a, b) =>\n        f.root.position.clone().addScaledVector(a, 1.1).lengthSq() -\n        f.root.position.clone().addScaledVector(b, 1.1).lengthSq());\n      f.intent.move.copy(safe[0]);\n    } else f.intent.move.copy(retreat);\n    return;\n  }\n  // Close deliberately on a whiff rather than attacking from beyond skill range.\n  if (punish && distance > style.range * 0.64 && distance < style.range + 2.2) {\n    f.intent.move.copy(toward);\n    return;\n  }\n  // Faster melee personalities actively manage spacing; ranged kits retain kiting AI.\n  if (!RANGED.has(f.kit) && f.kit !== "bomb") {\n    if (distance > style.range + 0.35) f.intent.move.copy(toward);\n    else if (distance < style.range - 0.45 && style.bait > 0.42 && o.state === S.BLOCK)\n      f.intent.move.copy(tangent).multiplyScalar(this.tacticsDir * 0.7);\n  } else if (distance < style.range - 1.15 && !punish) {\n    const retreat = toward.clone().negate();\n    if (f.root.position.clone().addScaledVector(retreat, 0.9).length() < f.arenaRadius - 0.65)\n      f.intent.move.copy(retreat);\n  }\n}\n\nprivate hasPunishWindow(o: Fighter): boolean {\n  return o.state === S.STAGGER || o.state === S.HITSTUN ||\n    (o.state === S.ATTACK && o.atkPhase === 2 && !!o.atk &&\n      o.stateT < o.atk.wind + o.atk.active + o.atk.recover);\n}\n\n/** Score the real equipped skills by state and fighter identity.\n * Each move still uses Fighter.readSkill, normal cooldowns and hit detection. */\nprivate personalizedSkill(f: Fighter, o: Fighter, distance: number): string | null {\n  const id = f.look.name.toLowerCase();\n  const profile = FIGHT_STYLES[id];\n  if (!profile || (id === "veyr" && f.bloodFestivalT > 0)) return null;\n  const punish = this.hasPunishWindow(o);\n  const attackComing = o.state === S.ATTACK && o.atkPhase === 0;\n  const close = distance < 2.65;\n  const blocking = o.state === S.BLOCK;\n  const scored: { key: string; points: number }[] = [];\n  for (const key of ["z", "x", "c"]) {\n    const a = f.attacks[key];\n    if (!a || (f.cooldowns[key] ?? 1) > 0) continue;\n    // Nesa\'s 3 charges follow the Pink Heart Smash skill on any equipped key.\n    if (id === "nesa" && a.style === "nesa_heart_slam" && f.nesaCCharges <= 0) continue;\n    let viable = true;\n    let points = profile.skillBias[key === "z" ? 0 : key === "x" ? 1 : 2];\n    if (a.type === "melee" || a.type === "phantom") {\n      viable = distance < a.reach + Math.max(0.85, a.lunge * 0.19);\n      if (punish) points += 1.2;\n      if (blocking && a.guard > 24) points += 0.4;\n    } else if (a.type === "strike") {\n      viable = a.at !== "self" || distance < a.radius + 0.40;\n      if (punish) points += 0.85;\n    } else if (a.type === "projectile" || a.type === "lob") {\n      viable = distance < (a.type === "lob" ? 9 : 11);\n      if (distance > 3.5) points += 0.45;\n    } else if (a.type === "buff") {\n      viable = a.mode === "counter" || a.mode === "blood_feint"\n        ? attackComing && close\n        : a.mode === "ward" ? close || f.hp < f.maxHp * 0.55\n        : a.mode === "blood_festival" ? distance < 3.4\n        : f.hp < f.maxHp * 0.72;\n    } else if (a.type === "blink") {\n      viable = a.mode === "back" ? (close || attackComing) : distance < 5.5;\n    } else if (a.type === "mine") viable = distance < 4.6;\n    else if (a.type === "barrel") viable = !f.barrelOut && distance < 6.5;\n    if (!viable) continue;\n    // Actual roster-specific choices, not a skill randomly selected by key.\n    const name = a.name;\n    switch (id) {\n      case "aster":\n        if (name === "Shield Bash") points += close && (blocking || attackComing) ? 2.3 : 0.2;\n        if (name === "Rising Slash") points += punish && close ? 1.2 : 0;\n        break;\n      case "vesper":\n        if (name === "Rising Slash") points += punish && close ? 2.0 : 0.4;\n        if (name === "Shield Bash" && blocking) points += 1.1;\n        break;\n      case "garrick":\n        if (name === "Iron Tempest") points += close && punish ? 2.0 : 0.4;\n        if (name === "Titan Cleave") points += punish && distance < 3.1 ? 2.4 : 0;\n        if (name === "Ground Slam" && close) points += 1.2;\n        break;\n      case "kaede":\n        if (name === "Counter Stance") points += attackComing && close ? 2.7 : 0;\n        if (name === "Thousand Cuts") points += punish && close ? 1.8 : 0;\n        break;\n      case "ember":\n        if (name === "Flame Burst") points += close ? 2.6 : -0.7;\n        if (name === "Fireball Volley" && distance > 3) points += 1.1;\n        if (name === "Meteor" && punish) points += 1.1;\n        break;\n      case "marina":\n        if (name === "Bubble Ward" && attackComing) points += 3.0;\n        if (name === "Tidal Ring" && close) points += 2.0;\n        if (name === "Ocean Requiem" && punish) points += 1.2;\n        break;\n      case "nyx":\n        if (name === "Smoke Step" && (blocking || attackComing)) points += 2.1;\n        if (name === "Phantom Rush" && punish) points += 2.6;\n        break;\n      case "rook":\n        if (name === "Rush" && distance > 1.8) points += 1.8;\n        if (name === "Meteor Fist" && close && punish) points += 2.4;\n        if (name === "Shockwave Punch" && distance > 2.8) points += 1.8;\n        break;\n      case "gale":\n        if (name === "Wind Step" && distance > 2.2) points += 2.0;\n        if (name === "Tornado Rise" && close && punish) points += 2.1;\n        break;\n      case "bob":\n        if (a.type === "mine" && distance < 4.1) points += 2.0;\n        if (a.type === "barrel" && !f.barrelOut) points += 1.5;\n        if (name === "Paralyze Bomb" && attackComing) points += 1.7;\n        break;\n      case "kira":\n        if (name === "Cyclone Kick" && close) points += punish ? 2.3 : 0.75;\n        if (name === "Crescent Gale") points += distance > 2.5 ? 2.1 : -0.45;\n        if (name === "Phantom Step") points += punish && distance < 4.6 ? 2.7 : 0.35;\n        break;\n      case "raven":\n        if (name === "Blink") points += close || attackComing ? 3.1 : -0.8;\n        if (name === "Chain Lightning") points += distance > 2.0 && distance < 9.0 ? 1.7 : 0;\n        if (name === "Thunderstorm") points += punish ? 2.0 : 0.35;\n        break;\n      case "ash":\n        if (name === "Leap Back") points += close || attackComing ? 3.0 : -0.4;\n        if (name === "Hunter\'s Snare") points += !punish && distance > 2.7 ? 1.8 : 0.3;\n        if (name === "Arrow Rain") points += punish && distance > 2.2 ? 2.2 : 0.3;\n        break;\n      case "veyr":\n        if (name === "Death Feint") points += attackComing && close ? 3.4 : -0.6;\n        if (name === "Blood Festival") points += close && (f.hp < f.maxHp * 0.75 || punish) ? 2.6 : 0.35;\n        if (name === "Crimson Execution") points += distance > 2.3 ? 1.45 : 0.2;\n        break;\n      case "zarek":\n        if (name === "Serpent Wheel") points += blocking || close ? 1.7 : 0;\n        if (name === "Phantom Spiral") points += punish ? 2.5 : 0.5;\n        if (name === "Infinite Crescent") points += punish || f.clashMomentum >= 3 ? 2.6 : 0.25;\n        break;\n      case "kaizen":\n        // Hook catches exposed opponents just outside the five-hit sword string.\n        if (name === "Predator\'s Hook") {\n          if (blocking || distance < 1.45 || distance > 4.5) viable = false;\n          points += !attackComing && distance > 2.45 && !blocking ? 2.25 : 0.25;\n        }\n        // A death spiral is strongest against recoveries, not at maximum range.\n        if (name === "Thousand Cuts: Death Spiral") {\n          if (distance > 3.65) viable = false;\n          points += punish && distance < 3.2 ? 2.5 : close ? 0.8 : 0;\n        }\n        if (name === "Razor Cyclone") points += blocking || (close && punish) ? 1.95 : 0.30;\n        if (name === "Serpent Bind") points += !blocking && punish && distance < 3.1 ? 2.45 : 0.25;\n        break;\n      case "nesa":\n        // Favor the closing kick against ranged enemies, but it must still land.\n        if (name === "Upsie Daisie") {\n          if (distance > 5.65) viable = false;\n          points += distance > 2.20 && distance < 5.15 ? 2.65 :\n            attackComing && close ? 1.8 : 0.25;\n        }\n        // Spend a stored heart charge on a near, punishable target—not empty air.\n        if (name === "Pink Heart Smash") {\n          if (distance > 2.82) viable = false;\n          points += punish || blocking ? 2.4 : distance < 2.10 ? 1.0 : 0.0;\n          if (f.nesaCCharges === 1 && !punish) points -= 0.7;\n        }\n        if (name === "Side Swipe") points += close && blocking ? 2.0 : punish ? 1.7 : 0.1;\n        // Large second bonk needs a target likely to stay in radius.\n        if (name === "Heartbreaker High Striker") {\n          if (distance > 3.0) viable = false;\n          points += punish && distance < 2.4 ? 2.75 : 0.0;\n        }\n        break;\n    }\n    if (!viable) continue; // real ability limits, including character-specific checks\n    // The AI must occasionally choose another ability instead of being scripted.\n    points += rand(-0.55, 0.55);\n    scored.push({ key, points });\n  }\n  scored.sort((a, b) => b.points - a.points);\n  return scored.length && scored[0].points >= 0.6 ? scored[0].key : null;\n}'
AI_OFFENSE = 'private offense(f: Fighter, o: Fighter, dt: number) {\n  if (f.state !== S.IDLE || this.queue.length || this.hold > 0 || this.blockHold > 0 ||\n      this.comboParryTarget > this.threats.now()) return;\n  const distance = f.root.position.distanceTo(o.root.position);\n  if (f.guard <= f.maxGuard * 0.32 && f.onGround && f.attacks.l1?.type === "melee" &&\n    o.state === S.ATTACK && o.atk?.type === "melee" && o.atkPhase === 0 &&\n    distance < f.attacks.l1.reach + 0.35) {\n    this.queue.push([0, 0.06]);\n    return;\n  }\n  if (f.stage && Math.abs(o.root.position.y - f.root.position.y) > 1.4 && !RANGED.has(f.kit)) return;\n  const id = f.look.name.toLowerCase();\n  const style = FIGHT_STYLES[id];\n  const reach = style ? (RANGED.has(f.kit) ? 9 : style.range + 0.24)\n    : RANGED.has(f.kit) ? 9 : f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks"\n      ? 1.7 : f.kit === "greatsword" ? 2.3 : f.kit === "glaive" ? 2.1 : 1.9;\n  const punish = this.hasPunishWindow(o);\n  const blocked = o.state === S.BLOCK;\n  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&\n    o.atk?.type === "melee" && distance < o.atk.reach + 0.65;\n  this.skillCd -= dt;\n  if (this.skillCd <= 0) {\n    this.skillCd = rand(this.p.skill[0], this.p.skill[1]);\n    // Festival disables all Veyr skills until it expires; pressure with basics.\n    const skill = this.personalizedSkill(f, o, distance);\n    if (skill && (punish || Math.random() < 0.80) && this.trySkill(f, skill, true)) return;\n  }\n  if (distance > reach) return;\n  if (danger && !punish && id !== "zarek" && id !== "aster" && Math.random() < 0.80) return;\n  this.thinkCd -= dt;\n  if (this.thinkCd > 0) return;\n  const fast = ["assassin", "knuckles", "kicks", "sickle", "glaive"].includes(f.kit);\n  this.thinkCd = (fast ? rand(0.45, 0.96) : rand(0.7, 1.45)) * this.p.think;\n  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge\n  const heavyChance = style ? Math.min(0.78, style.heavy +\n      (punish ? 0.14 : 0) + (blocked ? 0.28 : 0))\n    : o.state === S.STAGGER ? 0.5 : blocked ? 0.45 : 0.22;\n  // Veyr\'s festival specifically favors sustained lights and real guard pressure.\n  const festival = id === "veyr" && f.bloodFestivalT > 0;\n  if (!festival && Math.random() < heavyChance) {\n    this.queue.push([0, HOLD_T + rand(0.24, 0.58)]);\n    return;\n  }\n  const allLights = Object.keys(f.attacks).filter(k => /^l\\d+$/.test(k));\n  const limit = Math.max(1, Math.min(this.p.combo, allLights.length));\n  let count = 1 + Math.floor(Math.random() * limit);\n  if (style) {\n    if (punish && Math.random() < style.combo) count = limit;\n    else if (blocked && Math.random() < style.bait) count = 1;\n    else if (Math.random() > style.combo) count = Math.min(count, 2);\n  }\n  if (festival) count = limit;\n  // Each tap is a real input, and the Fighter checks real animation/cancel windows.\n  for (let i = 0; i < count; i++)\n    this.queue.push([i === 0 ? 0 : 0.14 + (fast ? 0 : 0.06), 0.06]);\n}'

def patch_ai(text: str) -> str:
    if MARKER in text:
        print('[OK] All 17 AI personalities already present')
        return text
    if 'SMART_AI_PERSONALITIES_17_FINAL_V1' in text or 'SMART_AI_PERSONALITIES_BATCH_1_TO_3_V1' in text:
        raise PatchError('AI has a previous staged personality patch; please supply the original project version to merge safely.')
    s = once(text, 'export class AiBrain implements Brain {',
             '// '+MARKER+'\n'+AI_PROFILES+'\n\nexport class AiBrain implements Brain {', 'profile definitions')
    s = once(s, '  private ignitionChoices = new Map<number, boolean>();',
             '  private ignitionChoices = new Map<number, boolean>();\n'+AI_FIELDS, 'personality state')
    s = once(s, '    if (!f.stage) { this.dodge(f); this.position(f, o, dt); }',
             '    if (!f.stage) { this.dodge(f); this.position(f, o, dt); this.tacticalFootwork(f, o, dt); }',
             'personality positioning')
    s = once(s, '      // Guard critical / recently guard-broken',
             AI_CLASH+'      // Guard critical / recently guard-broken', 'Zarek tactical clash')
    s = once(s, '  private trySkill(f: Fighter, key: string, force = false) {',
             AI_METHODS+'\n\n  private trySkill(f: Fighter, key: string, force = false) {',
             'personalized skill selection and footwork')
    # The offense method is the final member in ai.ts. Replace ONLY that final member.
    anchor = '  private offense(f: Fighter, o: Fighter, dt: number) {'
    pos=s.rfind(anchor)
    if pos<0: raise PatchError('AI offense() anchor missing; no files changed')
    cls_end = s.rfind('\n}')
    if cls_end<=pos: raise PatchError('AI class end anchor missing')
    tail=s[cls_end+2:]
    if tail.strip(): raise PatchError('Unexpected trailing code after AiBrain class')
    s=s[:pos]+AI_OFFENSE+'\n'+s[cls_end:]
    return s

def patch_kits(text: str) -> str:
    # Operate on the exact named fighter kits, not similarly named bonus skills.
    b=text.index('function bow(): Record<string, Attack> {') if 'function bow(): Record<string, Attack> {' in text else -1
    if b<0: raise PatchError('Ash bow() kit not found')
    e=text.find('\n}',b)
    if e<0: raise PatchError('Ash bow() end not found')
    bow=text[b:e]
    # Light arrows -20% approximately; charged piercing arrow -25%.
    new_bow=bow
    for attack,old_val,new_val in [('l1',60,48),('l2',62,50),('l3',46,37),('heavy',260,195)]:
        pattern = re.compile(r'(^\s*'+attack+r': a\(\{[^\n]*?\bdmg: )(\d+)',re.MULTILINE)
        found=list(pattern.finditer(new_bow))
        if len(found)!=1: raise PatchError(f'Ash {attack} damage anchor changed; found {len(found)}')
        current=int(found[0].group(2))
        if current not in (old_val,new_val):
            raise PatchError(f'Ash {attack} damage is {current}, expected {old_val} or {new_val}; leaving unchanged for safety')
        if current==old_val:
            new_bow=pattern.sub(lambda m: m.group(1)+str(new_val),new_bow,count=1)
    text=text[:b]+new_bow+text[e:]
    k=text.index('function kicks(): Record<string, Attack> {') if 'function kicks(): Record<string, Attack> {' in text else -1
    if k<0: raise PatchError('Kira kicks() kit not found')
    end=text.find('\n}',k)
    if end<0: raise PatchError('Kira kicks() end not found')
    kicks=text[k:end]
    pattern=re.compile(r'(name: "Phantom Step"[^\n]*?\bcd: )(\d+)')
    found=list(pattern.finditer(kicks))
    if len(found)!=1: raise PatchError('Kira Phantom Step cooldown anchor missing or ambiguous')
    current=int(found[0].group(2))
    if current not in (12,16): raise PatchError(f'Kira cooldown is {current}, expected 12 or 16')
    if current==12: kicks=pattern.sub(lambda m:m.group(1)+'16',kicks,count=1)
    return text[:k]+kicks+text[end:]

def save_transaction(root:Path, changes:dict[str,str]) -> None:
    if not changes:
        print('[OK] Already installed. No changes needed.')
        return
    backup=root/'.smart_ai17_backups'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True,exist_ok=False)
    files=[]
    for rel in changes:
        src=root/rel
        dst=backup/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        files.append((rel,src,dst))
    applied=[]
    try:
        for rel,src,dst in files:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',delete=False,dir=src.parent) as fh:
                fh.write(changes[rel]); temp=Path(fh.name)
            try:
                os.replace(temp,src)
            finally:
                if temp.exists(): temp.unlink()
            applied.append((src,dst))
    except Exception:
        for src,dst in reversed(applied): shutil.copy2(dst,src)
        raise
    print('[OK] Files updated:', ', '.join(changes))
    print('[OK] Original files backed up in:',backup)

def main():
    parser=argparse.ArgumentParser(description='17 smarter CPU personalities, Phantom Step 16s, Ash bow nerf')
    parser.add_argument('project',nargs='?',help='Fight Royale web directory')
    parser.add_argument('--check',action='store_true',help='validate without writing')
    args=parser.parse_args()
    root=project_root(args.project)
    roster=(root/'src/game/roster.ts').read_text(encoding='utf-8')
    expected=('aster','vesper','garrick','kaede','ember','marina','nyx','rook','gale',
              'bob','kira','raven','ash','veyr','zarek','kaizen','nesa')
    if any(('id: "'+x+'"') not in roster for x in expected):
        raise PatchError('The expected 17-character roster is incomplete; no files changed.')
    changes={}
    for rel,fn in [('src/game/ai.ts',patch_ai),('src/game/kits.ts',patch_kits)]:
        path=root/rel
        old=path.read_text(encoding='utf-8')
        new=fn(old)
        if new!=old: changes[rel]=new
    print('Project:',root)
    print('Requested modifications:', ', '.join(changes) if changes else 'already installed')
    if args.check:
        print('[CHECK] All patch anchors verified. No files were modified.')
        return
    save_transaction(root,changes)
    print('[DONE] 17 AI personalities + Kira Phantom Step 16s + Ash bow damage nerf.')
    print('Run from web folder: npx tsc --noEmit -p . && npm run dev')

if __name__=='__main__':
    try: main()
    except (PatchError, OSError, ValueError) as e:
        print('INSTALL ERROR:',e,file=sys.stderr)
        sys.exit(1)
