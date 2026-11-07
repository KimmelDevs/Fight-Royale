#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale AI Personality 2.0 — all 17 roster fighters.

Small additive updater for the already installed 17-fighter Smart AI (V1).
Only src/game/ai.ts is modified. No character balance or controls are changed.
Creates a timestamped backup, supports --check and idempotent reinstalls.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse
import os
import shutil
import sys
import tempfile

VERSION = "AI_PERSONALITY_THEATER_2_V1"
PREVIOUS_VERSION = "SMART_AI_PERSONALITIES_17_FINAL_V2_20261107"

class PatchError(RuntimeError):
    pass

def once(s: str, before: str, after: str, label: str) -> str:
    count = s.count(before)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}; nothing modified")
    return s.replace(before, after, 1)

def project_root(spec: str | None) -> Path:
    given = Path(spec).expanduser().resolve() if spec else Path.cwd().resolve()
    for root in (given, given / "web"):
        if all((root / file).is_file() for file in (
            "src/game/ai.ts", "src/game/fighter.ts", "src/game/roster.ts")):
            return root
    raise PatchError("Project not found. Run from your Fight Royale web folder or pass its path.")

METHODS = '  // AI_PERSONALITY_THEATER_2_V1 — distinct movement + follow-up decisions for all 17.\n  // Deliberately uses only ordinary controls: move, jump, dash, attack, equipped skill.\n  // Enemy defense, cooldowns, hit tests, and arena bounds remain authoritative.\n  private theaterCd = rand(0.9, 2.1);\n  private theaterT = 0;\n  private theaterMode: "none" | "back" | "circle" | "chase" = "none";\n  private theaterFollow = "";\n  private theaterFollowT = 0;\n  private theaterJump = false;\n  private theaterDash = false;\n  private theaterSide = 1;\n  private theaterLastGap = 99;\n  private theaterComboCd = 0;\n  private theaterLastTargetSwing = -1;\n\n  /** Named skills are looked up AFTER loadout remapping; missing skills never fire. */\n  private theaterKey(f: Fighter, name: string): string | null {\n    const key = ["z", "x", "c"].find(k =>\n      f.attacks[k]?.name === name && (f.cooldowns[k] ?? 1) <= 0);\n    if (!key) return null;\n    const a = f.attacks[key];\n    if (f.kit === "sickle" && f.bloodFestivalT > 0) return null;\n    if (a.style === "nesa_heart_slam" && f.nesaCCharges <= 0) return null;\n    return key;\n  }\n\n  private theaterPlan(mode: "back" | "circle" | "chase", t: number,\n      follow: string, jump = false, dash = false) {\n    this.theaterMode = mode;\n    this.theaterT = t;\n    this.theaterFollow = follow;\n    this.theaterFollowT = t + 1.65;\n    this.theaterJump = jump;\n    this.theaterDash = dash;\n    this.theaterSide = Math.random() < 0.5 ? -1 : 1;\n    // Don\'t finish an old preplanned combo after deciding to disengage.\n    this.queue = [];\n    this.hold = 0;\n    this.tacticsT = 0;\n  }\n\n  /** Find a useful movement direction that actually fits inside the circular arena.\n   * This is a steering choice, not a teleport. Projectile/fire avoidance runs later.\n   */\n  private theaterDirection(f: Fighter, o: Fighter, preference: THREE.Vector3): THREE.Vector3 {\n    const at = f.root.position.clone().setY(0);\n    const toward = o.root.position.clone().sub(at).setY(0);\n    if (toward.lengthSq() < 0.001) toward.set(0, 0, 1);\n    toward.normalize();\n    const lateral = new THREE.Vector3(-toward.z, 0, toward.x);\n    const center = at.clone().negate();\n    if (center.lengthSq() > 0.001) center.normalize();\n    const target = preference.lengthSq() > 0.001 ? preference.clone().normalize() : toward;\n    const choices = [\n      target.clone(),\n      target.clone().addScaledVector(lateral, 0.75).normalize(),\n      target.clone().addScaledVector(lateral, -0.75).normalize(),\n      lateral.clone(), lateral.clone().negate(),\n      target.clone().addScaledVector(center, 0.8).normalize(),\n      center.clone(),\n    ];\n    const cap = Math.max(1.5, f.arenaRadius - f.radius - 0.28);\n    const ahead = f.dashCd <= 0 && f.onGround ? 3.3 : 1.15;\n    let best = target, score = -Infinity;\n    for (const dir of choices) {\n      if (dir.lengthSq() < 0.001) continue;\n      const dest = at.clone().addScaledVector(dir, ahead);\n      if (dest.length() > cap) dest.setLength(cap);\n      const displacement = dest.clone().sub(at);\n      const actual = displacement.length();\n      const alignment = actual > 0.001 ? displacement.normalize().dot(target) : -1;\n      const value = alignment * 2.1 + actual * 0.44 - (actual < ahead * 0.28 ? 2.2 : 0);\n      if (value > score) { score = value; best = dir; }\n    }\n    return best.clone().normalize();\n  }\n\n  /** Start recognizable mini-sequences: step away, entice a miss, then come back\n   * with the fighter\'s real equipped move. Low HP changes temperament by class.\n   */\n  private theaterFootwork(f: Fighter, o: Fighter, dt: number) {\n    if (f.stage || f.isDown()) return;\n    const id = f.look.name.toLowerCase();\n    const style = FIGHT_STYLES[id];\n    if (!style) return;\n    const delta = o.root.position.clone().sub(f.root.position).setY(0);\n    const gap = delta.length();\n    if (gap < 0.01) return;\n    const toward = delta.divideScalar(gap);\n    const lateral = new THREE.Vector3(-toward.z, 0, toward.x);\n    const punish = this.hasPunishWindow(o);\n    const hostileSwing = o.state === S.ATTACK && o.atkPhase === 0 &&\n      !!o.atk && o.atk.type === "melee" && gap < o.atk.reach + 0.95;\n    const chased = gap < this.theaterLastGap - 0.06;\n    this.theaterLastGap = gap;\n    this.theaterComboCd = Math.max(0, this.theaterComboCd - dt);\n    this.theaterCd = Math.max(0, this.theaterCd - dt);\n    this.theaterFollowT = Math.max(0, this.theaterFollowT - dt);\n    if (this.theaterFollowT <= 0) this.theaterFollow = "";\n\n    // Existing projectile evasions, Nesa dodge, parry, and hazard reactions outrank\n    // voluntary showmanship. Never cancel an already committed attack to perform it.\n    const free = f.state === S.IDLE || f.state === S.BLOCK;\n    if (this.theaterMode !== "none" && this.theaterT > 0) {\n      this.theaterT = Math.max(0, this.theaterT - dt);\n      if (free && this.sideT <= 0 && this.blockWait < 0 && this.blockHold <= 0) {\n        const preferred = this.theaterMode === "back" ?\n          toward.clone().negate().addScaledVector(lateral, this.theaterSide * 0.3) :\n          this.theaterMode === "circle" ? lateral.clone().multiplyScalar(this.theaterSide)\n            .addScaledVector(toward, gap > style.range ? 0.27 : -0.15) : toward;\n        const safe = this.theaterDirection(f, o, preferred);\n        f.intent.move.copy(safe);\n        if (this.theaterJump && f.onGround) {\n          f.intent.jump = true;\n          this.theaterJump = false;\n        }\n        if (this.theaterDash && f.onGround && f.dashCd <= 0 &&\n            f.state === S.IDLE && this.theaterT > 0.10) {\n          f.intent.dash.copy(safe);\n          this.theaterDash = false;\n        }\n      }\n      if (this.theaterT <= 0) this.theaterMode = "none";\n      return;\n    }\n    this.theaterMode = "none";\n    if (!free || !f.onGround || this.sideT > 0 || this.blockHold > 0 ||\n        this.blockWait >= 0 || this.theaterCd > 0 || this.theaterFollow) return;\n\n    const hp = f.hp / Math.max(f.maxHp, 1);\n    // Characters with low health aren\'t all cowards: Kira/Rook/Veyr keep pushing.\n    const aggressive = id === "kira" || id === "rook" || id === "veyr";\n    const caution = hp < 0.35 && !aggressive;\n    const intensity = 0.65 + this.p.block * 0.65;\n    const intent = (prob: number) => Math.random() < prob * intensity;\n    // A little randomness is desirable, but the follow-up itself is deliberate.\n    this.theaterCd = rand(1.35, 3.05) * this.p.think;\n    switch (id) {\n      case "aster":\n        if (gap < 2.75 && (o.state === S.BLOCK || hostileSwing) && intent(0.68))\n          this.theaterPlan("back", 0.30, "Shield Bash", false, false);\n        else if (punish && gap < 3.3) this.theaterPlan("chase", 0.26, "Rising Slash", false, false);\n        break;\n      case "vesper":\n        if (gap < 2.8 && !punish && intent(0.78))\n          this.theaterPlan("back", 0.26, "combo3", false, false);\n        else if (punish && gap < 4.1) this.theaterPlan("chase", 0.24, "combo3", false, true);\n        break;\n      case "garrick":\n        if (gap < 3.2 && (hostileSwing || o.state === S.BLOCK) && intent(0.80))\n          this.theaterPlan("back", 0.35, "charge", false, false);\n        else if (punish && gap < 3.6) this.theaterPlan("chase", 0.32, "Titan Cleave", false, false);\n        break;\n      case "kaede":\n        if (hostileSwing && gap < 2.7 && intent(0.85))\n          this.theaterPlan("circle", 0.14, "Counter Stance", false, false);\n        else if (punish && gap < 3.1) this.theaterPlan("chase", 0.26, "Thousand Cuts", false, false);\n        else if (gap < 2.8 && o.state === S.BLOCK) this.theaterPlan("circle", 0.34, "charge");\n        break;\n      case "ember":\n        if (gap < 5.0 && (chased || hostileSwing || caution) && intent(0.85))\n          this.theaterPlan("back", 0.36, "Fireball Volley", gap < 2.7, gap < 2.3);\n        else if (gap > 3.7 && punish) this.theaterPlan("circle", 0.25, "charge");\n        break;\n      case "marina":\n        if (gap < 4.4 && (chased || caution) && intent(0.80))\n          this.theaterPlan("back", 0.34, "Tidal Ring", false, gap < 2.1);\n        else if (gap < 2.6 && hostileSwing) this.theaterPlan("circle", 0.23, "Bubble Ward");\n        break;\n      case "nyx":\n        // Signature: leap backwards, bait pursuit, then teleport back with Smoke Step.\n        if (gap < 3.55 && this.theaterKey(f, "Smoke Step") &&\n            (chased || hostileSwing || o.state === S.IDLE) && intent(0.93))\n          this.theaterPlan("back", 0.44, "Smoke Step", true, false);\n        else if (punish && gap < 3.8) this.theaterPlan("chase", 0.22, "Phantom Rush", false, true);\n        break;\n      case "rook":\n        // Rook hates dead air and uses real forward dashes to keep punches flowing.\n        if (gap > 1.85 && gap < 5.3 && intent(0.90))\n          this.theaterPlan("chase", 0.29, "Rush", false, gap > 2.7);\n        else if (gap < 2.2 && o.state === S.BLOCK && intent(0.50))\n          this.theaterPlan("back", 0.18, "combo4");\n        break;\n      case "gale":\n        if (gap < 4.4 && intent(0.80))\n          this.theaterPlan(gap > 2.5 ? "chase" : "circle", 0.41,\n            "Wind Step", true, gap > 3.5);\n        break;\n      case "bob":\n        if (gap < 5.0 && (chased || caution || o.state === S.IDLE) && intent(0.90))\n          this.theaterPlan("back", 0.35, "Land Mine", gap < 2.5, gap < 2.0);\n        else if (gap > 3.3) this.theaterPlan("circle", 0.27, "Paralyze Bomb");\n        break;\n      case "kira":\n        // The opposite of Nyx: advance immediately after knockback/recovery.\n        if (gap > 1.7 && gap < 6.8 && intent(0.96))\n          this.theaterPlan("chase", 0.36, punish ? "combo4" : "Cyclone Kick",\n            false, f.dashCd <= 0 && gap > 2.65);\n        else if (gap < 2.5 && punish) this.theaterPlan("chase", 0.19, "combo4");\n        break;\n      case "raven":\n        if (gap < 4.0 && (chased || hostileSwing || caution) && intent(0.88))\n          this.theaterPlan("back", 0.27, "Blink", false, false);\n        else if (gap > 3.1 && punish) this.theaterPlan("circle", 0.23, "Thunderstorm");\n        break;\n      case "ash":\n        if (gap < 5.1 && (chased || hostileSwing || caution) && intent(0.88))\n          this.theaterPlan("back", 0.37, "Hunter\'s Snare", gap < 3.2, gap < 2.4);\n        else if (gap > 3.5 && punish) this.theaterPlan("circle", 0.20, "charge");\n        break;\n      case "veyr":\n        if (hostileSwing && gap < 2.7 && intent(0.79))\n          this.theaterPlan("circle", 0.14, "Death Feint");\n        else if (gap > 1.9 && gap < 4.6 && intent(0.88))\n          this.theaterPlan("chase", 0.26, f.bloodFestivalT > 0 ? "combo4" : "Blood Festival",\n            false, f.dashCd <= 0 && gap > 3);\n        break;\n      case "zarek":\n        if (punish && gap < 4.0) this.theaterPlan("chase", 0.27, "Phantom Spiral", false, gap > 2.9);\n        else if (o.state === S.BLOCK && gap < 3.2) this.theaterPlan("circle", 0.31, "Serpent Wheel");\n        break;\n      case "kaizen":\n        // Remain at chain range: retreat from fists, then hook escaping prey.\n        if (gap < 2.2 && (hostileSwing || chased) && intent(0.86))\n          this.theaterPlan("back", 0.33, "Predator\'s Hook", false, false);\n        else if (gap > 2.5 && gap < 4.7 && !hostileSwing && intent(0.68))\n          this.theaterPlan("circle", 0.26, "Predator\'s Hook");\n        else if (punish && gap < 3.6) this.theaterPlan("chase", 0.22, "Thousand Cuts: Death Spiral");\n        break;\n      case "nesa":\n        if (gap < 3.0 && hostileSwing && intent(0.83))\n          this.theaterPlan("circle", 0.26, "Pink Heart Smash");\n        else if (gap > 2.7 && gap < 6.3 && intent(0.83))\n          this.theaterPlan("chase", 0.31, "Upsie Daisie", false, gap > 4.5);\n        else if (gap < 2.8 && (punish || o.state === S.BLOCK))\n          this.theaterPlan("circle", 0.20, "Pink Heart Smash");\n        break;\n    }\n  }\n\n  /** Follow through after the movement rather than selecting a random unrelated skill.\n   * When the equipped move is unavailable or out of range, regular offense resumes.\n   */\n  private theaterOffense(f: Fighter, o: Fighter): boolean {\n    if (f.stage || !this.theaterFollow || this.theaterFollowT <= 0) return false;\n    if (this.theaterT > 0) return true; // first actually finish the bait / chase movement\n    if (f.state !== S.IDLE || this.blockHold > 0 || this.blockWait >= 0 ||\n        this.comboParryTarget > this.threats.now() || this.queue.length || this.hold > 0) return false;\n    const gap = f.root.position.clone().setY(0)\n      .distanceTo(o.root.position.clone().setY(0));\n    let follow = this.theaterFollow;\n    const finish = () => { this.theaterFollow = ""; this.theaterFollowT = 0; };\n    // Don\'t spin in empty air; wait briefly for the baited enemy to reach attack range.\n    if (follow.startsWith("combo")) {\n      const reach = (f.attacks.l1?.reach || 1.8) + 0.33;\n      if (gap > reach && gap < reach + 3.0 && f.onGround &&\n          ["vesper", "rook", "kira", "veyr", "zarek"].includes(f.look.name.toLowerCase())) {\n        // Re-enter a combo at REAL dash speed, rather than swinging at empty air.\n        const to = o.root.position.clone().sub(f.root.position).setY(0);\n        const safe = this.theaterDirection(f, o, to);\n        f.intent.move.copy(safe);\n        if (f.dashCd <= 0 && gap > reach + 0.7) f.intent.dash.copy(safe);\n        return true;\n      }\n      if (gap > reach || this.theaterComboCd > 0) return false;\n      const max = Math.max(1, Math.min(this.p.combo,\n        Number(follow.replace("combo", "")) || 2,\n        Object.keys(f.attacks).filter(k => /^l\\d+$/.test(k)).length));\n      for (let i = 0; i < max; i++) this.queue.push([i === 0 ? 0 : 0.18, 0.065]);\n      this.theaterComboCd = rand(0.65, 1.0);\n      finish();\n      return true;\n    }\n    if (follow === "charge") {\n      const longRange = RANGED.has(f.kit) || f.kit === "bomb";\n      if (!longRange && gap > (f.attacks.heavy?.reach || 2.3) + 0.4) return false;\n      this.queue = [[0, HOLD_T + rand(0.35, 0.66)]];\n      finish();\n      return true;\n    }\n    const key = this.theaterKey(f, follow);\n    if (!key) { finish(); return false; }\n    const a = f.attacks[key];\n    const isBlink = a.type === "blink";\n    const inRange = isBlink ? (a.mode === "behind" ? gap < 5.3 : gap < 6.4) :\n      a.name === "Upsie Daisie" ? gap <= Math.min(6.55, a.reach + a.lunge * 0.31) :\n      a.type === "melee" || a.type === "phantom" ?\n        gap <= Math.max(a.reach + Math.min(1.15, a.lunge * 0.19), a.type === "phantom" ? 4.2 : 1.8) :\n      a.type === "strike" && a.at === "self" ? gap <= a.radius + 0.35 :\n      a.type === "mine" ? gap < 5.0 :\n      a.type === "projectile" || a.type === "lob" ? gap < 9.5 : true;\n    if (!inRange) {\n      if (a.type === "melee" && gap < Math.max(5.0, a.reach + 2.7) && f.onGround &&\n          ["aster", "vesper", "rook", "kira", "zarek", "gale", "nesa"].includes(f.look.name.toLowerCase())) {\n        const safe = this.theaterDirection(f, o,\n          o.root.position.clone().sub(f.root.position).setY(0));\n        f.intent.move.copy(safe);\n        if (f.dashCd <= 0 && gap > a.reach + 1.0) f.intent.dash.copy(safe);\n        return true;\n      }\n      return false;\n    }\n    // A failed feint/counter is punishable. Don\'t cast it if nobody is attacking.\n    if (a.mode === "blood_feint" || a.mode === "counter") {\n      if (o.state !== S.ATTACK || o.atkPhase !== 0) return false;\n    }\n    if (a.mode === "blood_festival" && gap > 3.4) return false;\n    f.intent.skill = key;\n    this.skillCd = rand(this.p.skill[0], this.p.skill[1]);\n    finish();\n    return true;\n  }\n'

def patch_ai(text: str) -> str:
    if VERSION in text:
        return text
    if PREVIOUS_VERSION not in text:
        raise PatchError("Install FightRoyale Smart AI 17 first (the earlier combined installer); no files changed.")
    # Keep all earlier AI code, including Nesa's arena-edge dodges and
    # the late Upsie Daisie chase tuning. Only add a higher-level plan layer.
    s = once(text,
        "  constructor(private threats: Threats, level: number) {",
        METHODS + "\n  constructor(private threats: Threats, level: number) {",
        "insert personality sequence methods")
    s = once(s,
        "    if (!f.stage) { this.dodge(f); this.position(f, o, dt); this.tacticalFootwork(f, o, dt); }",
        "    if (!f.stage) { this.dodge(f); this.position(f, o, dt); this.tacticalFootwork(f, o, dt); this.theaterFootwork(f, o, dt); }",
        "enable movement planner")
    s = once(s,
        "    if (!this.aiAirTap) this.offense(f, o, dt);",
        "    if (!this.aiAirTap && !this.theaterOffense(f, o)) this.offense(f, o, dt);",
        "enable signature follow-up planner")
    return s

def save(root: Path, new: str) -> None:
    src = root / "src/game/ai.ts"
    backup = root / ".ai_personality_v2_backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    original = backup / "src/game/ai.ts"
    original.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(src, original)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                 dir=src.parent, delete=False) as f:
        f.write(new)
        tmp = Path(f.name)
    try:
        os.replace(tmp, src)
    finally:
        if tmp.exists(): tmp.unlink()
    print("[OK] Original backed up in:", backup)
    print("[OK] Updated:", src)

def main() -> None:
    parser = argparse.ArgumentParser(description="Fight Royale 17-fighter AI Personality 2.0 update")
    parser.add_argument("project", nargs="?", help="Fight Royale web directory")
    parser.add_argument("--check", action="store_true", help="Validate source without changing files")
    args = parser.parse_args()
    root = project_root(args.project)
    src = root / "src/game/ai.ts"
    current = src.read_text(encoding="utf-8")
    updated = patch_ai(current)
    print("Fight Royale project:", root)
    if updated == current:
        print("[OK] AI Personality 2.0 is already installed; no changes made.")
        return
    if args.check:
        print("[CHECK] All anchors found; patch is ready. No files changed.")
        return
    save(root, updated)
    print("[DONE] All 17 CPU personalities have dynamic movement and signature follow-ups.")
    print("[NOTE] No skill cooldown, damage, hitbox, or player controls were changed.")
    print("Run: npx tsc --noEmit -p .  then  npm run dev")

if __name__ == "__main__":
    try:
        main()
    except (PatchError, OSError, ValueError) as exc:
        print("INSTALL ERROR:", exc, file=sys.stderr)
        sys.exit(1)
