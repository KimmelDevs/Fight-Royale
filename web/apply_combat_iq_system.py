#!/usr/bin/env python3
"""Fight Royale — Combat IQ (hit-confirm combos, whiff punishes, feint footwork).

Usage:
  python apply_combat_iq_system.py
  python apply_combat_iq_system.py "C:/path/to/web"

Patch is restricted to src/game/ai.ts. No Python dependencies; backs up before
replacing; validates expected anchors before writing; safe to run twice.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import os
import sys
import tempfile

TAG = "COMBAT_IQ_HITCONFIRM_WHIFF_BAIT_V1_20261107"

# Difficulty values are AI decision opportunities, not guaranteed outcomes.
IQ_SETTINGS = '''// COMBAT_IQ: Easy seldom recognizes openings, Master is perceptive, not psychic.
// All reads are visible fighter state (active swings, HP/guard changes, recovery).
const COMBAT_IQ = [
  { combo: 0.13, punish: 0.10, bait: 0.00, react: [0.45, 0.70], feintCd: [8.0, 11.0] },
  { combo: 0.43, punish: 0.39, bait: 0.10, react: [0.27, 0.44], feintCd: [6.5, 9.0] },
  { combo: 0.74, punish: 0.73, bait: 0.27, react: [0.15, 0.27], feintCd: [5.0, 7.0] },
  { combo: 0.92, punish: 0.90, bait: 0.48, react: [0.09, 0.17], feintCd: [3.8, 6.0] },
] as const;
'''

IQ_ENGINE = '''  // COMBAT IQ — situational reads, never direct damage, cooldown edits or teleports.
  private iqLevel = 1;
  private iqEnemySerial = -1;
  private iqEnemySawActive = false;
  private iqEnemyAllActiveOutside = true;
  private iqEnemyMyHp = 0;
  private iqEnemyMyGuard = 0;
  private iqEnemyWhiffEvaluated = false;
  private iqWhiffSerial = -1;
  private iqWhiffReactAt = -1;
  private iqWhiffExpires = -1;
  private iqWhiffSpent = false;
  private iqOwnSerial = -1;
  private iqOwnTargetHp = 0;
  private iqOwnHitConfirmed = false;
  private iqOwnHitAt = -1;
  private iqOwnFollowWanted = false;
  private iqOwnSkillWanted = false;
  private iqOwnFollowSpent = false;
  private iqBaitCd = rand(3.2, 6.0);
  private iqBaitPhase: "none" | "step" | "retreat" = "none";
  private iqBaitT = 0;
  private iqBaitSide = 1;
  private iqLastEnemySwing = -1;

  /** Observe actual active attacks and health changes; no knowledge of player input.
   * HP changes confirm contact, guard damage disproves a clean whiff. For a
   * clean whiff we must have seen the enemy OUT of range/arc for its full active
   * animation, not just seen an attack go into recovery.
   */
  private iqObserve(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (o.state === S.ATTACK && o.atk && o.swingSerial !== this.iqEnemySerial) {
      this.iqEnemySerial = o.swingSerial;
      this.iqEnemySawActive = false;
      this.iqEnemyAllActiveOutside = true;
      this.iqEnemyMyHp = f.hp;
      this.iqEnemyMyGuard = f.guard;
      this.iqEnemyWhiffEvaluated = false;
      if (this.iqBaitPhase === "step" && o.atkPhase === 0) {
        this.iqBaitPhase = "retreat";
        this.iqBaitT = Math.min(this.iqBaitT + 0.18, 0.46);
      }
      this.iqLastEnemySwing = o.swingSerial;
    }
    if (o.state === S.ATTACK && o.atk && o.swingSerial === this.iqEnemySerial) {
      if (o.atkPhase === 1 && (o.atk.type === "melee" || o.atk.type === "phantom")) {
        this.iqEnemySawActive = true;
        const flat = o.root.position.clone().sub(f.root.position).setY(0);
        const gap = flat.length();
        const toward = f.root.position.clone().sub(o.root.position).setY(0);
        const facing = new THREE.Vector3(Math.sin(o.root.rotation.y), 0, Math.cos(o.root.rotation.y));
        const inArc = toward.lengthSq() < 0.001 || facing.dot(toward.normalize()) > 0.15;
        // Conservative: only a clearly missed swing qualifies, no presumed free punishes.
        const outside = gap > o.atk.reach + f.radius + 0.20 || !inArc;
        this.iqEnemyAllActiveOutside = this.iqEnemyAllActiveOutside && outside;
      }
      if (o.atkPhase === 2 && !this.iqEnemyWhiffEvaluated) {
        this.iqEnemyWhiffEvaluated = true;
        const remaining = o.atk.wind + o.atk.active + o.atk.recover - o.stateT;
        const simpleMelee = o.atk.type === "melee" && o.atk.repeat <= 1 &&
          !["chain_razor_cyclone", "chain_death_spiral", "nesa_spin", "nesa_air_spin"].includes(o.atk.style);
        const didNotConnect = f.hp >= this.iqEnemyMyHp - 0.1 &&
          f.guard >= this.iqEnemyMyGuard - 0.1;
        const profile = COMBAT_IQ[this.iqLevel];
        if (simpleMelee && this.iqEnemySawActive && this.iqEnemyAllActiveOutside &&
            didNotConnect && remaining > profile.react[0] + 0.10 &&
            Math.random() < profile.punish) {
          this.iqWhiffSerial = o.swingSerial;
          this.iqWhiffReactAt = now + rand(profile.react[0], profile.react[1]);
          this.iqWhiffExpires = now + Math.max(0, remaining - 0.03);
          this.iqWhiffSpent = false;
        }
      }
    }
    // A hit-confirm only uses an observed HP loss after this fighter attacked.
    // An opponent holding BLOCK with guard loss does not count as a confirmed hit.
    if (f.state === S.ATTACK && f.atk && f.swingSerial !== this.iqOwnSerial) {
      this.iqOwnSerial = f.swingSerial;
      this.iqOwnTargetHp = o.hp;
      this.iqOwnHitConfirmed = false;
      this.iqOwnHitAt = -1;
      this.iqOwnFollowWanted = false;
      this.iqOwnSkillWanted = false;
      this.iqOwnFollowSpent = false;
    }
    if (f.state === S.ATTACK && f.atk && f.swingSerial === this.iqOwnSerial &&
        f.atkPhase >= 1 && !this.iqOwnHitConfirmed &&
        o.hp < this.iqOwnTargetHp - 0.5 &&
        // A status-effect damage tick alone is not a reliable combo confirm.
        (o.state === S.HITSTUN || o.state === S.STAGGER || o.state === S.KNOCKDOWN)) {
      this.iqOwnHitConfirmed = true;
      this.iqOwnHitAt = now;
      // Roll once per connected swing, never reroll every frame until success.
      this.iqOwnFollowWanted = Math.random() < COMBAT_IQ[this.iqLevel].combo;
      this.iqOwnSkillWanted = Math.random() < COMBAT_IQ[this.iqLevel].combo * 0.55;
    }
  }

  /** Legal, ready damaging skills only. No free V on Easy/Normal/Hard CPUs.
   * In particular, no defensive buffs, counters or mines masquerade as punishes.
   */
  private iqFollowSkill(f: Fighter, o: Fighter, gap: number, remaining: number): string | null {
    let best: string | null = null;
    let bestScore = -1e5;
    for (const key of ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]) {
      const a = f.attacks[key];
      if (!a || (f.cooldowns[key] ?? 1) > 0 || a.dmg <= 0 ||
          (f.kit === "sickle" && f.bloodFestivalT > 0) ||
          (a.style === "nesa_heart_slam" && f.nesaCCharges <= 0)) continue;
      if (a.wind + 0.035 >= remaining) continue;
      let inRange = false;
      if (a.type === "melee" || a.type === "phantom")
        inRange = gap <= a.reach + Math.min(0.45, a.lunge * 0.08);
      else if (a.type === "strike")
        inRange = a.at !== "self" || gap <= a.radius + 0.12;
      else if (a.type === "projectile")
        inRange = gap <= 8.5 && gap / Math.max(0.1, a.speed) + a.wind < remaining;
      // Lob, mine, blast-zone, blink and buffs are deliberately not guaranteed combos.
      if (!inRange) continue;
      const score = a.dmg / 95 + a.stun * 0.85 - a.wind * 1.8 -
        (a.type === "projectile" ? gap * 0.11 : 0) +
        (a.effect ? 0.36 : 0) + rand(-0.12, 0.12);
      if (score > bestScore) { best = key; bestScore = score; }
    }
    return best;
  }

  /** Timed pressure reacts to confirmed contact, verified whiffs, and baited
   * approaches. All actions are normal intent movement/buttons, never special AI hits.
   * Returns true only when taking an offensive input or holding a feint movement.
   */
  private combatIQAction(f: Fighter, o: Fighter, dt: number): boolean {
    const profile = COMBAT_IQ[this.iqLevel];
    const now = this.threats.now();
    this.iqBaitCd = Math.max(0, this.iqBaitCd - dt);
    if (f.isDown() || o.isDown() || f.chainBindT > 0 || f.chainBoundBy ||
        this.blockWait >= 0 || this.blockHold > 0 || this.sideT > 0 ||
        f.intent.block || f.intent.dash.lengthSq() > 0.01 ||
        this.comboParryTarget > now ||
        (f.kit === "sickle" && f.bloodFestivalT > 0)) {
      this.iqBaitPhase = "none";
      return false;
    }
    const delta = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = delta.length();
    if (gap < 0.01) return false;
    const toward = delta.divideScalar(gap);
    const free = f.state === S.IDLE || (f.state === S.ATTACK && f.atkPhase === 2);

    // Hit-confirmed light string: buffer precisely one next click through the
    // existing Fighter.requestLight combo system. Do not blindly mash full combos.
    if (f.state === S.ATTACK && f.atk && /^l\\d+$/.test(f.atkId) &&
        !!f.atk.next && this.iqOwnHitConfirmed && this.iqOwnFollowWanted &&
        !this.iqOwnFollowSpent && f.atkPhase >= 1 && f.onGround &&
        gap <= (f.attacks[f.atk.next]?.reach ?? f.atk.reach) + 0.40) {
      this.iqOwnFollowSpent = true;
      this.queue = [[0, 0.060]];
      this.hold = 0;
      this.theaterFollow = "";
      this.theaterFollowT = 0;
      return true;
    }
    // If an attack connects but ends the light string, link to a *ready* skill
    // only if there is actual time to cast before the target can recover.
    if (f.state === S.ATTACK && f.atk && !f.atk.next &&
        this.iqOwnHitConfirmed && this.iqOwnSkillWanted &&
        !this.iqOwnFollowSpent && f.atkPhase === 2 &&
        (o.state === S.HITSTUN || o.state === S.STAGGER)) {
      const left = Math.max(0, o.stun - o.stateT);
      const key = this.iqFollowSkill(f, o, gap, left);
      if (key) {
        f.intent.skill = key;
        this.queue = []; this.hold = 0;
        this.iqOwnFollowSpent = true;
        this.skillCd = Math.max(this.skillCd, 0.24);
        return true;
      }
    }

    // Whiff punish: only a swing visibly missed in its whole active window;
    // respect reaction delay, opponent remaining recovery and our real attack windup.
    if (!this.iqWhiffSpent && this.iqWhiffSerial === o.swingSerial &&
        now >= this.iqWhiffReactAt && now < this.iqWhiffExpires &&
        o.state === S.ATTACK && o.atkPhase === 2 && free) {
      const left = Math.min(this.iqWhiffExpires - now,
        o.atk ? o.atk.wind + o.atk.active + o.atk.recover - o.stateT : 0);
      const key = this.iqFollowSkill(f, o, gap, left);
      if (key) {
        f.intent.skill = key;
        this.queue = []; this.hold = 0;
        this.iqWhiffSpent = true;
        this.iqBaitPhase = "none";
        this.theaterFollow = "";
        this.theaterFollowT = 0;
        this.skillCd = Math.max(this.skillCd, 0.22);
        return true;
      }
      const light = f.attacks.l1;
      if (f.state === S.IDLE && light && gap <= light.reach + 0.18 &&
          light.wind + 0.055 < left && f.atkLock <= 0) {
        this.queue = [[0, 0.062]]; this.hold = 0;
        this.iqWhiffSpent = true;
        this.iqBaitPhase = "none";
        this.theaterFollow = "";
        this.theaterFollowT = 0;
        return true;
      }
      if (f.state === S.IDLE && light && f.onGround && gap <= light.reach + 1.6 &&
          left > light.wind + 0.24 && this.threats.firePatches(f).length === 0) {
        f.intent.move.copy(this.theaterDirection(f, o, toward));
        // Real movement only: close in for a punish, no teleport or free dash.
        return true;
      }
    }

    // Fake a short approach then pull out of the enemy's range. On success the
    // observed swing may create a whiff window. No attack or guard input is faked.
    if (this.iqBaitPhase !== "none") {
      if (!f.onGround || f.state !== S.IDLE || f.stage ||
          this.threats.firePatches(f).length > 0) {
        this.iqBaitPhase = "none";
        return false;
      }
      this.iqBaitT = Math.max(0, this.iqBaitT - dt);
      if (this.iqBaitPhase === "step" && (o.state === S.ATTACK || this.iqBaitT <= 0)) {
        this.iqBaitPhase = "retreat";
        this.iqBaitT = rand(0.24, 0.41);
      }
      if (this.iqBaitPhase === "retreat" && this.iqBaitT <= 0) {
        this.iqBaitPhase = "none";
        return false;
      }
      const tangent = new THREE.Vector3(-toward.z, 0, toward.x);
      const preferred = this.iqBaitPhase === "step" ?
        toward.clone().addScaledVector(tangent, this.iqBaitSide * 0.16) :
        toward.clone().negate().addScaledVector(tangent, this.iqBaitSide * 0.56);
      // Never override a real warning/dodge, including nearby active attack arcs.
      if (o.state === S.ATTACK && o.atkPhase === 1 && o.atk &&
          gap <= o.atk.reach + f.radius + 0.5) return false;
      f.intent.move.copy(this.theaterDirection(f, o, preferred));
      return true;
    }
    if (profile.bait <= 0 || this.iqBaitCd > 0 || f.stage || !f.onGround ||
        f.state !== S.IDLE || o.state !== S.IDLE || RANGED.has(f.kit) ||
        this.queue.length > 0 || this.hold > 0 ||
        this.threats.firePatches(f).length > 0 ||
        this.theaterT > 0 || this.theaterFollow || this.tacticsT > 0) return false;
    const enemyReach = o.attacks.l1?.reach ?? 1.75;
    if (gap < enemyReach + 0.18 || gap > enemyReach + 1.55 ||
        Math.random() >= profile.bait * (FIGHT_STYLES[f.look.name.toLowerCase()]?.bait ?? 0.5)) {
      this.iqBaitCd = rand(profile.feintCd[0], profile.feintCd[1]);
      return false;
    }
    this.iqBaitCd = rand(profile.feintCd[0], profile.feintCd[1]);
    this.iqBaitPhase = "step";
    this.iqBaitT = rand(0.16, 0.31);
    this.iqBaitSide = Math.random() < 0.5 ? -1 : 1;
    f.intent.move.copy(this.theaterDirection(f, o, toward));
    return true;
  }

'''


def replace_exact(src: str, old: str, new: str, purpose: str) -> str:
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{purpose}: expected 1 anchor, found {n}. Refusing to modify this version.")
    return src.replace(old, new, 1)


def patch_ai(src: str) -> str:
    if TAG in src:
        return src
    if "private effectiveRangeBand(" not in src or "private readySkillOpportunity(" not in src:
        raise ValueError("This installer needs the newer AI range-awareness/skill system. Install prior updates first.")
    src = replace_exact(src, 'const RANGED = new Set(["mage", "bow", "bomb"]);',
                        'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n' + IQ_SETTINGS,
                        "Combat IQ difficulty parameters")
    src = replace_exact(src, '  private rangeOrbitCd = 0;', IQ_ENGINE + '  private rangeOrbitCd = 0;',
                        "Combat IQ observer and combat policy")
    old = '''  constructor(private threats: Threats, level: number) {
    this.p = PRESETS[Math.max(0, Math.min(level, PRESETS.length - 1))];
  }'''
    new = '''  constructor(private threats: Threats, level: number) {
    this.iqLevel = Math.max(0, Math.min(Math.floor(Number.isFinite(level) ? level : 1), PRESETS.length - 1));
    this.p = PRESETS[this.iqLevel];
  }'''
    src = replace_exact(src, old, new, "Use actual difficulty in Combat IQ")
    src = replace_exact(src, '    if (!o || o.isDown()) return;\n    // Marked ground impacts',
                        '    if (!o || o.isDown()) return;\n    this.iqObserve(f, o);\n    // Marked ground impacts',
                        "Observe hits before high-priority defensive decisions")
    old = '''    if (!this.aiAirTap && !f.intent.skill && this.projectileSwordCommit <= 0 &&
        !this.readySkillOpportunity(f, o, dt) && !this.theaterOffense(f, o))
      this.offense(f, o, dt);'''
    new = '''    // Combat IQ runs after emergency dodges and ordinary footwork, before
    // opportunistic skills, scripted personality follow-ups and random offense.
    const iqActed = !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.combatIQAction(f, o, dt);
    if (!this.aiAirTap && !f.intent.skill && !iqActed &&
        this.projectileSwordCommit <= 0 &&
        !this.readySkillOpportunity(f, o, dt) && !this.theaterOffense(f, o))
      this.offense(f, o, dt);'''
    src = replace_exact(src, old, new, "Insert Combat IQ offense before ordinary offense")
    # Older scripted combo sequences will still buffer blind hits; make Normal+
    # prefer IQ's own hit-confirm one-tap follow-up when using normal offense.
    old = '''  if (festival) count = limit;
  // Each tap is a real input, and the Fighter checks real animation/cancel windows.'''
    new = '''  if (festival) count = limit;
  // Normal/Hard/Master: launch one opener, then wait for an actual hit-confirm
  // before buffering more attacks. Easy occasionally keeps its old basic queue.
  if (this.iqLevel >= 1 && !festival && !RANGED.has(f.kit)) count = 1;
  // Each tap is a real input, and the Fighter checks real animation/cancel windows.'''
    src = replace_exact(src, old, new, "Use hit-confirmed combos rather than blind melee spam")
    return '// ' + TAG + '\n' + src


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Fight Royale Combat IQ AI patch")
    parser.add_argument("web_folder", nargs="?", default=".", help="Root folder with src/game/ai.ts (default: current directory)")
    args = parser.parse_args()
    base = Path(args.web_folder).expanduser().resolve()
    target = base / "src" / "game" / "ai.ts"
    if not target.is_file():
        print(f"[ERROR] Cannot find {target}\nPlace this installer in the web folder or pass its path.", file=sys.stderr)
        return 1
    before = target.read_text(encoding="utf-8")
    if TAG in before:
        print("[OK] Combat IQ is already installed. No changes needed.")
        return 0
    try:
        after = patch_ai(before)
        if after == before:
            raise RuntimeError("No changes produced")
        # Validate all expected integration points before touching the source.
        expected = [TAG, "this.iqObserve(f, o)", "this.combatIQAction(f, o, dt)",
                    "COMBAT_IQ[this.iqLevel]", "this.iqWhiffSerial", "this.iqOwnHitConfirmed"]
        for marker in expected:
            if marker not in after:
                raise RuntimeError(f"Patch validation missing: {marker}")
        backup = target.with_name(target.name + ".before_combat_iq_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak")
        backup.write_text(before, encoding="utf-8")
        fd, temp_name = tempfile.mkstemp(prefix=".ai_combat_iq_", suffix=".ts", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fp:
                fp.write(after)
            # Atomic replacement should preserve the repository file's permissions.
            os.chmod(temp_name, target.stat().st_mode)
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.remove(temp_name)
        print("[OK] Combat IQ installed in:", target)
        print("[BACKUP]", backup)
        print("Easy: rare combos/punishes, no baits | Normal: occasional reads | Hard: regular reads | Master: strong reads with human reaction delays")
        print("Run your usual game build/test commands to verify the full game.")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}\nNo source files changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
