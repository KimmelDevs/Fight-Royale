#!/usr/bin/env python3
"""Fight Royale V29: parry speed/guard rewards, fatigue, weaken, Nythera, guard startup.

Run inside the Fight Royale web folder:
    python install_fight_royale_v29_parry_orbit_guard.py
Or supply the web folder as the first argument. Requires V28.

Safety: source anchors checked BEFORE any writes, backups saved, no Git/SQL/npm actions.
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import sys

MARK = "FIGHT_ROYALE_V29_PARRY_ORBIT_GUARD"
FILES = ("src/game/fighter.ts", "src/game/game.ts", "src/game/ai.ts",
         "src/game/kits.ts", "src/game/status.ts", "src/ui/GameView.tsx")


def edit(source: dict[str, str]) -> dict[str, str]:
    result = dict(source)

    def patch(file: str, old: str, new: str, n: int = 1) -> None:
        src = result[file]
        actual = src.count(old)
        if actual != n:
            raise ValueError(f"{file}: expected {n} occurrence(s), found {actual}: {old[:130]!r}")
        result[file] = src.replace(old, new, n)

    f = "src/game/fighter.ts"
    patch(f, "const NYTHERA_V26_TUNING = { maxAirSlices: 3, speedCap: 1.48 } as const;",
          "// " + MARK + ": 6 Orbit Marks, 1-per-hit spending, unchanged Dreadfall cap.\n"
          "const NYTHERA_V26_TUNING = { maxAirSlices: 3, speedCap: 1.48, orbitCap: 6 } as const;")
    patch(f, "// Unlimited stacks; effective speed has a safety floor to avoid zero timelines.\n"
             "export const GUARD_FATIGUE_TUNING = {\n"
             "  speedLostPerStack: 0.02,\n"
             "  decaySecondsPerStack: 3.0,\n"
             "  minSpeed: 0.20,\n} as const;",
          "// Max 10 stacks; applied AFTER all attack/passive speed bonuses, multiplicatively.\n"
          "export const GUARD_FATIGUE_TUNING = {\n"
          "  speedLostPerStack: 0.02,\n"
          "  maxStacks: 10,\n"
          "  decaySecondsPerStack: 3.0,\n"
          "  minSpeed: 0.80,\n} as const;")
    patch(f, "    this.guardFatigueStacks += 1; // intentionally unlimited",
          "    this.guardFatigueStacks = Math.min(GUARD_FATIGUE_TUNING.maxStacks, this.guardFatigueStacks + 1);")
    patch(f, "  private tickGuardFatigue(dt: number) {\n    if (this.guardFatigueStacks <= 0)",
          "  /** A true parry relieves one fatigue stack and restores 10% max guard. */\n"
          "  recoverFromParry() {\n"
          "    this.guard = Math.min(this.maxGuard, this.guard + this.maxGuard * 0.10);\n"
          "    this.guardFatigueStacks = Math.max(0, this.guardFatigueStacks - 1);\n"
          "    if (!this.guardFatigueStacks) this.guardFatigueDecayT = GUARD_FATIGUE_TUNING.decaySecondsPerStack;\n"
          "  }\n"
          "  private tickGuardFatigue(dt: number) {\n"
          "    this.guardFatigueStacks = Math.min(GUARD_FATIGUE_TUNING.maxStacks, this.guardFatigueStacks);\n"
          "    if (this.guardFatigueStacks <= 0)")
    patch(f, "this.guardFatigueStacks = s.length > 86 ? Math.max(0, s[86]) : 0;",
          "this.guardFatigueStacks = s.length > 86 ? Math.min(GUARD_FATIGUE_TUNING.maxStacks, Math.max(0, s[86])) : 0;")
    # Keep all passive/mode speed multipliers, but apply fatigue AFTER them, and only once.
    patch(f, "    // GUARD_FATIGUE_V26: finalized, kit-specific attack. Applies to both\n"
             "    // basics and Z/X/C/V wind/active/recovery, but NEVER to cooldown duration.\n"
             "    // 0.20x speed is a technical floor; stacks themselves remain uncapped.",
          "    // " + MARK + ": multiply fully boosted attack speed by (1-0.02*stacks).\n"
          "    // After all passives, modes, and kit modifiers; never alter cooldowns.")
    patch(f, "    this.atkPhase = 0;\n    this.buffered = false;\n    this.comboDamageMult = 1;",
          "    // Standardize the parry counter windup from the already-scaled timing.\n"
          "    // Only windup is clamped; parry timing, damage, active and recovery remain unchanged.\n"
          "    if (id === \"pc\" && this.atk) {\n"
          "      this.atk.wind = Math.max(0.24, Math.min(0.45, this.atk.wind));\n"
          "      this.atk.active = this.attacks.pc.active;\n"
          "      this.atk.recover = this.attacks.pc.recover;\n"
          "    }\n"
          "    this.atkPhase = 0;\n    this.buffered = false;\n    this.comboDamageMult = 1;")
    # Standard shield timing function is shared by players and CPU; preserve Aster/Staff priorities.
    patch(f, "  shieldRaise = 0.10;\n  nextShieldFast = false;",
          "  shieldRaise = 0.10;\n  nextShieldFast = false;\n"
          "  /** All heroes raise shields 30% sooner; existing Aster/Staff benefits remain. */\n"
          "  guardStartupSeconds(): number {\n"
          "    const special = this.kit === \"tristaff\" && this.dragonMode === 0\n"
          "      ? DRAGON_MODE_TUNING[0].staffShieldRaise\n"
          "      : this.nextShieldFast ? 0.01 : this.look.name === \"Aster\" ? 0.05 : 0.10;\n"
          "    return special * 0.70;\n"
          "  }")
    patch(f, "      this.shieldRaise = this.kit===\"tristaff\" && this.dragonMode===0\n"
             "        ? DRAGON_MODE_TUNING[0].staffShieldRaise\n"
             "        : (this.nextShieldFast ? 0.01 : (this.look.name === \"Aster\" ? 0.05 : 0.10)); // V28 shield 50% faster",
          "      this.shieldRaise = this.guardStartupSeconds(); // " + MARK + ": 30% quicker for everyone")
    # Remove the old fixed +15 and +20 guard on parry. Parry results are rewarded once in game.ts.
    patch(f, "        this.guard = Math.min(this.maxGuard, this.guard + 15);\n        return \"parry\";",
          "        return \"parry\";")
    patch(f, "        this.guard = Math.min(this.guard + 20, this.maxGuard);\n        this.model.flash(\"#99e6ff\", 0.15);",
          "        this.model.flash(\"#99e6ff\", 0.15);")

    f = "src/game/kits.ts"
    # Normalize current 0.16 mage and 0.12 Zenith special counter base to the same 0.4.
    patch(f, "  // BULLET_SWORDPLAY_V1: Aster's X now sweeps forward instead of jumping.",
          "  // " + MARK + ": parry riposte windup 0.40s for all kits before speed bonuses.\n"
          "  // Actual attack windup becomes 0.24–0.45s after passive/fatigue modifiers.\n"
          "  if (t.pc) t.pc.wind = 0.40;\n"
          "  // BULLET_SWORDPLAY_V1: Aster's X now sweeps forward instead of jumping.")

    f = "src/game/status.ts"
    patch(f, "const WEAKEN_STACKS = 5;", "const WEAKEN_STACKS = 3; // " + MARK)
    patch(f, "up to 5 stacks (${Math.round((1 - Math.pow(p, 5)) * 100)}% max)",
          "up to 3 stacks (${Math.round((1 - Math.pow(p, 3)) * 100)}% max)")

    f = "src/game/game.ts"
    patch(f, "    const sentenceMult = heavySentence ? 1 + marks * 0.05 : 1;",
          "    // " + MARK + ": a Dreadfall damaging hit spends only ONE stored mark.\n"
          "    const sentenceMult = heavySentence && marks > 0 ? 1.05 : 1;")
    start = "    if (gravityOwner && gravityDamage && gravityOwner.gravityMode === \"heavy\" && a.dmg > 0) {"
    end = "      if (gravityDamage && d instanceof Fighter && !d.stage && !d.isDown()) {"
    src = result[f]
    if src.count(start) != 1 or src.count(end) < 1:
        raise ValueError("game.ts: missing unique Nythera Orb contact anchors")
    beg = src.index(start)
    finish = src.index(end, beg)
    original = src[beg:finish]
    # Replace just the pre-launch/grab portion; preserve follow-up movement/skill VFX below.
    replacement = '''    // FIGHT_ROYALE_V29_PARRY_ORBIT_GUARD: Moonfloat = build, Dreadfall = spend.
    // No speed on unmarked targets, miss, parry, clash or block.
    if (gravityOwner && gravityDamage && a.dmg > 0) {
      if (gravityOwner.gravityMode === "light") {
        const n = Math.min(6, marks + 1);
        this.gravityMarks.set(markKey, { stacks: n, expires: this.time + 25 });
        if (d instanceof Fighter) { d.orbitDisplayStacks = n; d.orbitDisplayT = 25; }
        this.fxp("ring", d.chest(), "#b68ef7", 0.41 + n * 0.14, 0.18, 0.58);
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.72, 0)),
          `◈ ORBIT ${n}/6`, "#ddc0ff", 0.59);
        this.fxp("motes", d.chest(), "#dbb7ff", 7 + n * 3);
      } else if (marks > 0) {
        const remaining = marks - 1;
        if (remaining) this.gravityMarks.set(markKey, { stacks: remaining, expires: mark!.expires });
        else this.gravityMarks.delete(markKey);
        if (d instanceof Fighter) {
          d.orbitDisplayStacks = remaining;
          d.orbitDisplayT = remaining ? Math.max(0, mark!.expires - this.time) : 0;
        }
        gravityOwner.nytheraDreadfallHits = Math.min(14, gravityOwner.nytheraDreadfallHits + 1);
        const speed = gravityOwner.nytheraAttackSpeed();
        this.fxp("num", gravityOwner.chest().add(new THREE.Vector3(0, 0.80, 0)),
          `DREADFALL ${gravityOwner.nytheraDreadfallHits}/14 · ${speed.toFixed(2)}×`, "#d9b0ff", 0.56);
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.73, 0)),
          `ORBIT ${remaining}/6`, "#ddb5ff", 0.56);
      }
    }
    if (gravityOwner && gravityDamage && a.dmg > 0) {
'''
    result[f] = result[f].replace(original, replacement, 1)
    patch(f, '    const gravityContact = gravityDamage || result === "blocked";\n', '')
    patch(f, "      case \"parry\": {\n        const df = d as Fighter;",
          "      case \"parry\": {\n        const df = d as Fighter;\n"
          "        df.recoverFromParry(); // " + MARK + ": +10% max guard, -1 fatigue")
    # HUD source values - limit the overlay to counters, keep full descriptions as hover text.
    patch(f, "value: `${f.guardFatigueStacks} stacks · ${f.guardFatigueSpeed().toFixed(2)}× · ${f.guardFatigueDecayT.toFixed(1)}s`,",
          "value: `${f.guardFatigueStacks}/10`,")
    patch(f, 'desc: "Every blocked or parried hit (including guard break) slows the attacker by 2%. No stack cap; 1 stack fades every 3s without another defended hit. Attack and skill animation speed only; cooldowns unchanged."',
          'desc: "Each defended hit adds 1 fatigue (max 10), slowing total boosted attack speed by 2% per stack. Successful parries remove 1 stack and recover 10% maximum guard. Decays by 1 every 3 seconds without another defended hit."')
    patch(f, '${rival.orbitDisplayStacks}/5 · ${rival.orbitDisplayT.toFixed(1)}s', '${rival.orbitDisplayStacks}/6 · ${rival.orbitDisplayT.toFixed(1)}s')
    patch(f, ' : "0/5" });', ' : "0/6" });')
    patch(f, 'value: `${f.orbitDisplayStacks}/5 · ${f.orbitDisplayT.toFixed(1)}s`,',
          'value: `${f.orbitDisplayStacks}/6 · ${f.orbitDisplayT.toFixed(1)}s`,')
    patch(f, 'desc: "Nythera\'s Orbit Marks on this fighter. Each Moonfloat contact builds a mark (max 5); 25s duration.",',
          'desc: "Moonfloat damaging hits build up to six Orbit Marks (25s). Each damaging Dreadfall hit consumes one mark to earn one speed stack.",')
    patch(f, 'passives.push({ label: "WEAKEN", value: `×${rival.status.stacks("weaken")}/5` });',
          'passives.push({ label: "WEAKEN", value: `×${rival.status.stacks("weaken")}/3` });')
    patch(f, '`${(f.passiveGuard * 0.5).toFixed(1)} stacks · +${Math.round(f.passiveGuard * 0.5 * 5)}% DEF · +${Math.round((f.passiveKnightSpeed() - 1) * 100)}% Judgment SPD`,',
          '`${(f.passiveGuard * 0.5).toFixed(1)}`,')
    patch(f, '"Parry +1 stack; block +0.5. Each stack boosts defense 5%; shield skills and Judgment gain 1% speed per stack. No stack cap; lasts the whole match."',
          '"Parry +1 stack; block +0.5. Each stack boosts defense 2.5%; shield skills and Judgment gain speed. No cap; persists for the whole match."')
    patch(f, '`${(f.passiveGuard * 0.5).toFixed(1)} stacks · ${f.passiveDamageMult().toFixed(2)}× DMG`',
          '`${(f.passiveGuard * 0.5).toFixed(1)}`')
    patch(f, '`${f.nytheraDreadfallHits}/14 · ${rival?.orbitDisplayStacks ?? 0}/5 Orbit`',
          '`${f.nytheraDreadfallHits}/14 · ${rival?.orbitDisplayStacks ?? 0}/6 Orbit`')
    patch(f, 'desc: "Orbit Marks last 25s; Dreadfall starts at 0.80× and gains +0.05× per damaging hit, max 1.48× for this round. Three air slices per jump. Base scythe attacks: −10% damage; skills: −20%."',
          'desc: "Moonfloat damaging hits build up to 6 Orbit Marks lasting 25s. Each damaging Dreadfall hit consumes 1 mark for +0.05× speed (up to 1.48×). Without marks, no speed is gained. Three aerial slices. Base attacks: −10% damage; skills: −20%."')

    f = "src/ui/GameView.tsx"
    # Client HUD description remains a hover title. Remove technical stat strings from compact counters.
    patch(f, 'function PassiveHUD({ list, right = false }: { list?: PassiveReadout[]; right?: boolean }) {',
          '''function compactPassiveCount(label: string, value: string): string {
  // V29: show only stack/counter values in combat panels, not damage/speed math.
  // Keep non-numeric stance names (MOONFLOAT, STAFF, etc.) visible.
  if (label === "GRAVITY") return value;
  const first = value.match(/^\\s*[×+]?\\d+(?:\\.\\d+)?(?:\\s*\\/\\s*\\d+)?/);
  return first ? first[0].trim() : value.split(" · ")[0];
}
function PassiveHUD({ list, right = false }: { list?: PassiveReadout[]; right?: boolean }) {''')
    patch(f, '<strong>{p.label}</strong><b>{p.value}</b>',
          '<strong>{p.label}</strong><b>{compactPassiveCount(p.label, p.value)}</b>')
    patch(f, '<span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>{p.icon && <Icon src={p.icon} alt="Fatigue icon" size={18} fallback={<span>🛡️</span>} />}{p.label}</span><b>{p.value}</b>',
          '<span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>{p.icon && <Icon src={p.icon} alt="Passive icon" size={18} fallback={<span>🛡️</span>} />}{p.label}</span><b>{compactPassiveCount(p.label, p.value)}</b>')
    patch(f, 'const n = seconds > 0 ? Math.max(0, Math.min(5, Math.floor(stacks))) : 0;',
          'const n = seconds > 0 ? Math.max(0, Math.min(6, Math.floor(stacks))) : 0;')
    patch(f, 'Orbit Marks ${n} of 5', 'Orbit Marks ${n} of 6')
    patch(f, 'Array.from({ length: 5 }, (_, i)', 'Array.from({ length: 6 }, (_, i)')
    patch(f, '"0/5"', '"0/6"')
    patch(f, '  const speed = Math.min(1.50, 0.80 + stacks * 0.05); // NYTHERA_ZENITH_LOWER_CAPS_V14',
          '  const speed = Math.min(1.48, 0.80 + stacks * 0.05); // V29 current Dreadfall cap')

    f = "src/game/ai.ts"
    # CPU guard estimates use the actual updated timer, including existing special bonuses.
    patch(f, 'f.kit==="tristaff" && f.dragonMode===0 ? DRAGON_MODE_TUNING[0].staffShieldRaise :\n          (f.nextShieldFast ? 0.01 : 0.10)',
          'f.guardStartupSeconds()')
    patch(f, 'f.kit==="tristaff" && f.dragonMode===0 ?\n      DRAGON_MODE_TUNING[0].staffShieldRaise : (f.nextShieldFast ? 0.01 : 0.10)',
          'f.guardStartupSeconds()', 4)
    patch(f, '(f.nextShieldFast ? 0.01 : 0.10)', 'f.guardStartupSeconds()', 1)
    patch(f, '(f.nextShieldFast ? 0.05 : 0.14)', '(f.guardStartupSeconds() + 0.04)')
    # Mark-aware stance switches, based on the existing authoritative opponent mirror.
    patch(f, '''    if (canShift && f.gravityMode === "light" && gap < 3.10 &&
        (this.nytheraRecentContacts >= 2 ||
         (this.nytheraRecentContacts >= 1 && punish) ||
         (now - this.nytheraLastStanceAt > 8 && gap < 2.05))) return act("f");
    // Dreadfall already earns round-long speed, so do not switch away every
    // time the enemy briefly retreats; close in with the weapon instead.
    if (canShift && f.gravityMode === "heavy" && gap > 4.15 &&
        now - this.nytheraLastContactAt > 3.5) return act("f");''',
          '''    // V29: only switch to Dreadfall if the target already carries Moonfloat marks.
    // Do not camp Dreadfall when the target has nothing left to consume.
    const orbit = o.orbitDisplayT > 0 ? o.orbitDisplayStacks : 0;
    if (canShift && f.gravityMode === "light" && orbit >= (punish ? 1 : 2) &&
        gap < 3.10) return act("f");
    if (canShift && f.gravityMode === "heavy" && orbit <= 0) return act("f");
    if (canShift && f.gravityMode === "heavy" && gap > 4.15 &&
        now - this.nytheraLastContactAt > 3.5) return act("f");''')

    return result


def main() -> int:
    base = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    print("FIGHT ROYALE V29 — PARRY / ORBITS / GUARD |", base)
    try:
        content = {}
        for rel in FILES:
            path = base / rel
            if not path.is_file():
                raise RuntimeError(f"Missing {rel}. Run from your fight-royale/web folder.")
            content[rel] = path.read_text(encoding="utf-8-sig")
        if any(MARK in s for s in content.values()):
            raise RuntimeError("V29 appears to be installed already; no files changed.")
        if "GUARD_FATIGUE_HUD_V28" not in content["src/game/game.ts"]:
            raise RuntimeError("V28 base required: Guard Fatigue HUD marker missing. No files changed.")
        updated = edit(content)  # All anchors verified in memory before writing.
        modified = [rel for rel in FILES if updated[rel] != content[rel]]
        if len(modified) != len(FILES):
            raise RuntimeError("Unexpected missing modifications; no files changed.")
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = base / ".fight-royale-backups" / ("v29-" + stamp)
        for rel in modified:
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(base / rel, dest)
        try:
            for rel in modified:
                (base / rel).write_text(updated[rel], encoding="utf-8")
                print("  updated", rel)
        except Exception:
            for rel in modified:
                shutil.copy2(backup / rel, base / rel)
            raise
        print("Installed. Backup:", backup)
        print("Next: npx tsc --noEmit -p . && npm run dev")
        return 0
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
