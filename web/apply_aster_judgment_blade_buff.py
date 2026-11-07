#!/usr/bin/env python3
"""Fight Royale: Aster Judgment Blade 1.5x sword speed + Weaken on hit.

Place this installer inside the Fight Royale web/ directory and execute:
    python apply_aster_judgment_blade_buff.py

Only touches src/game/fighter.ts and src/game/kits.ts. Compatible with the
50-second/5-stack Weaken system. No dependencies; includes backups.
"""

from __future__ import annotations
import re
import sys
from datetime import datetime
from pathlib import Path

MARKER = "ASTER_JUDGMENT_BLADE_SPEED_WEAKEN_V1_20261108"

# This block is inserted into Fighter.startAttack AFTER the attack instance is
# chosen and any character-specific adjustments, BEFORE the attack starts.
# Existing sword skills with Weaken retain one single effect per successful hit.
FIGHTER_BLOCK = '''    // ASTER_JUDGMENT_BLADE_SPEED_WEAKEN_V1_20261108
    // During Judgment, every real blade swing/cut executes at 1.5x speed.
    // Clone the active attack only: do not permanently speed up the kit data,
    // change cooldowns, or affect shield bashes and non-Aster characters.
    // Successful hits use the existing 50s, max-5-stack Weaken status system.
    if (this.kit === "knight" && this.look.element === "light" &&
        this.judgmentT > 0 && this.atk &&
        (/^(?:l\\d+|air_l\\d+|heavy|air_heavy|pc)$/.test(id) || id === "x" || id === "c")) {
      const judgmentSpeed = 1.5;
      this.atk = {
        ...this.atk,
        wind: this.atk.wind / judgmentSpeed,
        active: this.atk.active / judgmentSpeed,
        recover: this.atk.recover / judgmentSpeed,
        // This is one application on confirmed damage, not another application
        // layered over the X/C skills which already apply Weaken normally.
        effect: "weaken", effect_t: 50, effect_p: 0.8,
      };
    }
'''

FIGHTER_ANCHOR = '''    this.atkPhase = 0;
    this.buffered = false;
    this.comboDamageMult = 1;'''

# Only modify the specifically matched light-element Judgment buff description.
JUDGMENT_DESC_RE = re.compile(
    r'(if \(element === "light"\) return a\(\{ name: "Judgment",\s*\n\s*desc: ")([^"\n]*)(",\s*\n\s*cd: 16, type: "buff", mode: "judgment", duration: 10,)'
)


def patch_fighter(src: str) -> tuple[str, bool]:
    if MARKER in src:
        if FIGHTER_BLOCK.strip() not in src:
            raise RuntimeError("Fighter marker found but its code differs; refusing partial installation")
        return src, False
    hits = src.count(FIGHTER_ANCHOR)
    if hits != 1:
        raise RuntimeError(f"Could not find unique attack initialization anchor in fighter.ts (found {hits})")
    if 'this.judgmentT > 0' not in src or 'this.atk = this.attacks[id]' not in src:
        raise RuntimeError("Missing expected Aster Judgment or attack-data code in fighter.ts")
    # Confirm insertion target is inside startAttack, not an unrelated function.
    loc = src.index(FIGHTER_ANCHOR)
    start = src.rfind('private startAttack(id: string)', 0, loc)
    end = src.find('private attackStep()', start)
    if start < 0 or end < loc:
        raise RuntimeError("Attack-initialization anchor is not inside Fighter.startAttack")
    return src.replace(FIGHTER_ANCHOR, FIGHTER_BLOCK + FIGHTER_ANCHOR, 1), True


def patch_kits(src: str) -> tuple[str, bool]:
    matches = list(JUDGMENT_DESC_RE.finditer(src))
    if len(matches) != 1:
        raise RuntimeError(f"Could not locate unique Aster Judgment skill description (found {len(matches)})")
    m = matches[0]
    extra = " While Judgment is active, sword attacks are 1.5x faster and successful blade hits add 1 Weaken stack (50s, max 5)."
    desc = m.group(2)
    if "sword attacks are 1.5x faster" in desc:
        return src, False
    # No change to the game data, only the user-facing tooltip/description.
    updated = src[:m.start(2)] + desc.rstrip() + extra + src[m.end(2):]
    return updated, True


def main() -> int:
    root = Path(__file__).resolve().parent
    if not (root / "src/game/fighter.ts").exists() and (root / "web/src/game/fighter.ts").exists():
        root = root / "web"
    paths = [root / "src/game/fighter.ts", root / "src/game/kits.ts"]
    for path in paths:
        if not path.is_file():
            print(f"INSTALLATION FAILED: Missing {path}. Put this script inside your web folder.", file=sys.stderr)
            return 1
    try:
        original = {p: p.read_text(encoding="utf-8-sig") for p in paths}
        fighter, fighter_changed = patch_fighter(original[paths[0]])
        kits, kits_changed = patch_kits(original[paths[1]])
        proposed = {paths[0]: fighter, paths[1]: kits}
    except Exception as exc:
        print(f"INSTALLATION FAILED: {exc}. No files were changed.", file=sys.stderr)
        return 1
    changed = [p for p in paths if proposed[p] != original[p]]
    if not changed:
        print("Already installed; no changes needed.")
        return 0
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backups = {}
    try:
        # Make backups for *both* changed files before writing either one.
        for p in changed:
            backup = p.with_name(f"{p.name}.before_aster_judgment_{stamp}.bak")
            backup.write_text(original[p], encoding="utf-8")
            backups[p] = backup
        for p in changed:
            p.write_text(proposed[p], encoding="utf-8")
    except Exception as exc:
        for p in changed:
            if p in backups:
                try:
                    p.write_text(original[p], encoding="utf-8")
                except OSError:
                    pass
        print(f"INSTALLATION FAILED: {exc}. Original files were restored where possible.", file=sys.stderr)
        return 1
    print("ASTER JUDGMENT BUFF INSTALLED")
    print(" - Judgment blade attacks: 1.5x speed (wind-up, active frames, recovery)")
    print(" - Successful blade hits: +1 Weaken stack (50s refresh, max 5)")
    print(" - Shield Bash, damage, skill cooldowns and normal Judgment duration: unchanged")
    for p in changed:
        print(f" Updated: {p.relative_to(root)}")
        print(f" Backup:  {backups[p].name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
