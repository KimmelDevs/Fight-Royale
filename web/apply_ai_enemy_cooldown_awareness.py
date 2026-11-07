#!/usr/bin/env python3
"""Fight Royale AI Improvement #5: observed enemy cooldown awareness.

Run from your web project folder:
    python apply_ai_enemy_cooldown_awareness.py

Also supports: python apply_ai_enemy_cooldown_awareness.py --dry-run

Patches only src/game/ai.ts, preserves the other AI/gameplay updates, and makes a
unique timestamped backup. No dependencies beyond Python's standard library.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARK = "// AI_ENEMY_COOLDOWN_MEMORY_V1_20261107"

CONFIG = '''// Enemy cooldowns are *estimated* from witnessed casts, never read from
// opponent.cooldowns. Variance and recognition delay prevent psychic CPU plays.
const ENEMY_CD_IQ = [
  { observe: 0.00, error: 0.00, react: [0.0, 0.0] }, // Easy: no tracking
  { observe: 0.70, error: 0.30, react: [0.40, 0.73] }, // Normal: big skills only
  { observe: 0.86, error: 0.17, react: [0.24, 0.42] }, // Hard: most threatening skills
  { observe: 0.96, error: 0.09, react: [0.12, 0.24] }, // Master: all cast skills
] as const;

type EnemyCooldownMemory = {
  slot: string; castAt: number; observedAt: number;
  predictedReadyAt: number; nominalCd: number; threat: number;
};

'''

FIELDS = '''  // AI_ENEMY_COOLDOWN_MEMORY_V1: only skills this brain observed are tracked.
  private cdEnemy: Fighter | null = null;
  private cdEnemySwing = -1;
  private cdEnemyMemory = new Map<string, EnemyCooldownMemory>();

'''

METHODS = '''  /** Record a publicly visible Z/X/C/V cast one time per swing. Never inspect
   * the opponent's private cooldown state, upcoming input, or skill queue.
   * Air variants share their normal button's cooldown.
   */
  private observeEnemyCooldown(o: Fighter) {
    if (o !== this.cdEnemy) {
      this.cdEnemy = o;
      this.cdEnemySwing = -1;
      this.cdEnemyMemory.clear();
    }
    if (this.iqLevel === 0 || o.state !== S.ATTACK || !o.atk ||
        o.swingSerial === this.cdEnemySwing) return;
    this.cdEnemySwing = o.swingSerial;
    const match = /^(z|x|c|v)(?:_air)?$/.exec(o.atkId);
    if (!match) return; // Basics, parry counters and special recasts are not skills.
    const slot = match[1];
    const attack = o.attacks[slot] ?? o.atk;
    const cd = attack.cd;
    // Barrel detonation and other recasts do not behave like ordinary cooldowns.
    if (!Number.isFinite(cd) || cd < 1 || attack.type === "barrel") return;
    const major = slot === "v" || cd >= 15 ||
      (attack.dmg >= 155 && cd >= 11) ||
      (attack.repeat >= 3 && cd >= 11);
    if (this.iqLevel === 1 && !major) return;
    if (this.iqLevel === 2 && !major && cd < 8) return;
    const profile = ENEMY_CD_IQ[this.iqLevel];
    if (Math.random() > profile.observe) return; // A missed observation stays missed.
    const now = this.threats.now();
    // Nominal kit CD is visible game knowledge, but perks/charges and temporary
    // modifiers can make the estimate wrong. No o.cooldowns or o.cdMult reads.
    const predicted = cd * (1 + rand(-profile.error, profile.error));
    const power = attack.dmg * Math.min(2.4, Math.sqrt(Math.max(1, attack.repeat)));
    const threat = THREE.MathUtils.clamp(
      0.34 + cd / 46 + power / 630 + (slot === "v" ? 0.18 : 0) +
      (attack.type === "buff" && ["counter", "ward", "static_field", "blood_festival"].includes(attack.mode) ? 0.2 : 0),
      0.28, 1.00);
    this.cdEnemyMemory.set(slot, {
      slot, castAt: now,
      observedAt: now + rand(profile.react[0], profile.react[1]),
      predictedReadyAt: now + predicted,
      nominalCd: cd, threat,
    });
  }

  /** Estimate an offensive window after a visible cast. As the predicted
   * cooldown nears zero, become a little more cautious. Unknown slots remain
   * unknown; a timer that has probably expired never grants free safety.
   */
  private enemyCooldownRead(o: Fighter): { pressure: number; caution: number } {
    if (this.iqLevel === 0 || this.cdEnemy !== o) return { pressure: 0, caution: 0 };
    const now = this.threats.now();
    let pressure = 0, caution = 0;
    for (const [key, memory] of this.cdEnemyMemory) {
      const left = memory.predictedReadyAt - now;
      if (left < -2.0) {
        this.cdEnemyMemory.delete(key); // forget stale estimates
        continue;
      }
      if (now < memory.observedAt) continue;
      // A cast may still be active; memory never tells us to run into it.
      if (left > Math.max(2.1, memory.nominalCd * 0.18)) {
        const confidence = THREE.MathUtils.clamp(
          (left - 1.5) / Math.max(3, memory.nominalCd * 0.28), 0, 1);
        pressure = Math.max(pressure, memory.threat * confidence);
      } else if (left >= -1.4) {
        const soon = 1 - Math.min(1, Math.abs(left - 0.30) / 2.4);
        caution = Math.max(caution, memory.threat * Math.max(0.22, soon));
      }
    }
    // Positioning/offense modifiers are deliberately modest, even on Master.
    const intelligence = [0, 0.45, 0.74, 1.0][this.iqLevel];
    return { pressure: pressure * intelligence, caution: caution * intelligence };
  }

'''


def replace_once(source: str, old: str, new: str, what: str) -> str:
    n = source.count(old)
    if n != 1:
        raise ValueError(f"Cannot safely patch {what}: expected exactly one anchor, found {n}. "
                         "Your AI source may have changed. No files were modified.")
    return source.replace(old, new, 1)


def build(original: str) -> str:
    if MARK in original:
        return original
    result = MARK + "\n" + original
    result = replace_once(result,
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n',
        'const RANGED = new Set(["mage", "bow", "bomb"]);\n\n' + CONFIG,
        "AI cooldown configuration")
    result = replace_once(result,
        '  private iqLevel = 1;\n',
        FIELDS + '  private iqLevel = 1;\n',
        "AI observation fields")
    result = replace_once(result,
        '  private iqObserve(f: Fighter, o: Fighter) {',
        METHODS + '  private iqObserve(f: Fighter, o: Fighter) {',
        "cooldown observation methods")
    # Use early observation even when a defensive reaction or Kaizen's V bind
    # returns early. This does not alter the priority of existing defenses.
    result = replace_once(result,
        '    if (!o || o.isDown()) return;\n    // An active grab locks both fighters.',
        '    if (!o || o.isDown()) return;\n'
        '    this.observeEnemyCooldown(o);\n'
        '    // An active grab locks both fighters.',
        "AI think observation") if '    // An active grab locks both fighters.' in result else replace_once(result,
        '    if (!o || o.isDown()) return;\n    this.iqObserve(f, o);',
        '    if (!o || o.isDown()) return;\n'
        '    this.observeEnemyCooldown(o);\n    this.iqObserve(f, o);',
        "AI think observation on pre-Kaizen version")
    # Footwork modifies *preferred* spacing, never physical weapon reach.
    result = replace_once(result,
        '  const band = this.effectiveRangeBand(f, o);\n  // A threatened block can be baited',
        '  const band = this.effectiveRangeBand(f, o);\n'
        '  const cdIntel = this.enemyCooldownRead(o);\n'
        '  // Follow a known opening modestly; keep ranged kits at ranged distance.\n'
        '  const shift = THREE.MathUtils.clamp(cdIntel.pressure * (RANGED.has(f.kit) ? 0.26 : 0.48) -\n'
        '    cdIntel.caution * (RANGED.has(f.kit) ? 0.28 : 0.43), -0.43, 0.48);\n'
        '  band.ideal = Math.max(1.05, band.ideal - shift);\n'
        '  band.near = Math.max(0.88, band.near - shift);\n'
        '  band.far = Math.max(band.near + 0.24, band.far - shift);\n'
        '  // A threatened block can be baited',
        "range-aware opportunity positioning")
    # Alter *AI thinking intervals* only: never edit fighter cooldowns.
    result = replace_once(result,
        '  const blocked = o.state === S.BLOCK;\n  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&',
        '  const blocked = o.state === S.BLOCK;\n'
        '  const cdIntel = this.enemyCooldownRead(o);\n'
        '  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&',
        "offense cooldown read")
    result = replace_once(result,
        '  this.skillCd -= dt;\n  if (this.skillCd <= 0) {\n    this.skillCd = rand(this.p.skill[0], this.p.skill[1]);',
        '  this.skillCd -= dt * (1 + cdIntel.pressure * 0.38);\n'
        '  if (this.skillCd <= 0) {\n'
        '    this.skillCd = rand(this.p.skill[0], this.p.skill[1]) *\n'
        '      (1 - cdIntel.pressure * 0.22 + cdIntel.caution * 0.22);',
        "offense decision tempo")
    result = replace_once(result,
        '  if (danger && !punish && id !== "zarek" && id !== "aster" && Math.random() < 0.80) return;\n  this.thinkCd -= dt;',
        '  if (danger && !punish && id !== "zarek" && id !== "aster" && Math.random() < 0.80) return;\n'
        '  // Near predicted enemy skill return, favor movement/defense over a risky commit.\n'
        '  if (cdIntel.caution > 0.43 && !punish && o.state === S.IDLE &&\n'
        '      Math.random() < cdIntel.caution * dt * 0.90) return;\n'
        '  this.thinkCd -= dt * (1 + cdIntel.pressure * 0.30);',
        "cooldown-aware normal attacks")
    result = replace_once(result,
        '  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge',
        '  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge\n'
        '  if (!punish) this.thinkCd *= 1 + cdIntel.caution * 0.24;',
        "recovery caution")
    result = replace_once(result,
        '  const heavyChance = style ? Math.min(0.78, style.heavy +',
        '  let heavyChance = style ? Math.min(0.78, style.heavy +',
        "heavy attack probability")
    result = replace_once(result,
        '    : o.state === S.STAGGER ? 0.5 : blocked ? 0.45 : 0.22;\n  // Veyr\'s festival',
        '    : o.state === S.STAGGER ? 0.5 : blocked ? 0.45 : 0.22;\n'
        '  // Exploit learned cooldown openings; do not swing into an active cast.\n'
        '  if (o.state !== S.ATTACK) heavyChance = THREE.MathUtils.clamp(\n'
        '    heavyChance + cdIntel.pressure * 0.16 - cdIntel.caution * 0.16, 0.08, 0.80);\n'
        '  // Veyr\'s festival',
        "heavy attack opportunity")
    return result


def locate(path: str | None) -> Path:
    if path:
        supplied = Path(path).expanduser().resolve()
        candidate = supplied if supplied.is_file() else supplied / "src" / "game" / "ai.ts"
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"No src/game/ai.ts found at {supplied}")
    for root in (Path.cwd(), Path.cwd() / "web", Path(__file__).resolve().parent):
        candidate = root / "src" / "game" / "ai.ts"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("No src/game/ai.ts found. Put this installer inside your web folder, "
                            "or run with --path /path/to/web")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Check compatibility without writing files")
    parser.add_argument("--path", help="Path to web project root or directly to ai.ts")
    args = parser.parse_args()
    try:
        path = locate(args.path)
        old = path.read_text(encoding="utf-8")
        if MARK in old:
            print("Already installed; no changes needed:", path)
            return 0
        new = build(old)
        if args.dry_run:
            print("Compatible. Would update:", path)
            return 0
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = path.with_name(f"ai.ts.before_enemy_cd_iq_{stamp}.bak")
        shutil.copy2(path, backup)
        # Atomic replace so interruption never leaves half a source file.
        temp = path.with_name(".ai.cooldown_memory.tmp")
        try:
            temp.write_text(new, encoding="utf-8")
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
        print("Installed AI Improvement #5 — Enemy Cooldown Awareness")
        print("Updated:", path)
        print("Backup: ", backup)
        print("Normal remembers major observed skills; Hard most dangerous skills; Master all skill slots.")
        print("Easy remains unchanged. This patch never reads enemy cooldown timers.")
        return 0
    except (OSError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
