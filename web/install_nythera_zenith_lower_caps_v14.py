#!/usr/bin/env python3
"""Fight Royale V14: permanent -0.20x/-0.30x base AND maximum attack speed.

Nythera (V12 base 1.00 + 0.05 per hit): 0.80 + 0.05 per hit,
    0.80x at 0 stacks -> 1.50x at 14 stacks, not 1.70x.
Zenith (V12 base 1.00 spear / 2.00 twin): 0.70 / 1.70 + 0.01 per hit,
    0.84x spear / 1.84x twin at 14 stacks, resetting after 5s.

Works on V12 or V13. Preserves other stats, cooldowns, AI and UI layout.
Run from fight-royale/web or pass the web directory as one argument.
No dependencies.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

TAG = "NYTHERA_ZENITH_LOWER_CAPS_V14"


def once(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected 1 matching source anchor, found {count}: {old[:120]!r}")
    return s.replace(old, new, 1)


def patch_fighter(s: str) -> str:
    if TAG in s:
        return s
    v13 = (
        "  // NYTHERA_ZENITH_START_SPEED_V13: 0.80x starting speed, retaining 1.70x at full 14 Dreadfall hits.\n"
        "  // The initial 0.20x penalty fades over the same 14 earned stacks.\n"
        "  nytheraAttackSpeed(): number {\n"
        "    const stacks = Math.max(0, Math.min(14, this.nytheraDreadfallHits));\n"
        "    return Math.min(1.7, 0.80 + stacks * 0.05 + 0.20 * stacks / 14);\n"
        "  }"
    )
    v12 = (
        "  nytheraAttackSpeed(): number { return Math.min(1.7, 1 + Math.min(14, this.nytheraDreadfallHits) * 0.05); } // NYTHERA_BALANCE_CPU_COMPACT_V12"
    )
    replacement = (
        f"  // {TAG}: flat -0.20x speed at ALL stacks; maximum 1.50x.\n"
        "  nytheraAttackSpeed(): number {\n"
        "    const stacks = Math.max(0, Math.min(14, this.nytheraDreadfallHits));\n"
        "    return Math.min(1.50, 0.80 + stacks * 0.05);\n"
        "  }"
    )
    if v13 in s:
        s = once(s, v13, replacement, "Nythera V13 speed")
    else:
        s = once(s, v12, replacement, "Nythera V12 speed")

    v12_zen = (
        "  zenithAttackSpeed() {\n"
        "    const bonus = Math.min(14, this.zenithTempoStacks) * 0.01;\n"
        "    return this.zenithSpearOut ? Math.min(3.4, 2 + bonus) : Math.min(2.4, 1 + bonus);\n"
        "  }"
    )
    v13_zen = (
        "  // NYTHERA_ZENITH_START_SPEED_V13: decrease spear and twin-blade starting attack speed by 0.30x.\n"
        "  zenithAttackSpeed() {\n"
        "    const bonus = Math.min(14, this.zenithTempoStacks) * 0.01;\n"
        "    return this.zenithSpearOut ? Math.min(3.4, 1.70 + bonus) : Math.min(2.4, 0.70 + bonus);\n"
        "  }"
    )
    zen_replacement = (
        f"  // {TAG}: permanent -0.30x vs the old base AND max at every stack.\n"
        "  zenithAttackSpeed() {\n"
        "    const bonus = Math.min(14, this.zenithTempoStacks) * 0.01;\n"
        "    return this.zenithSpearOut ? Math.min(1.84, 1.70 + bonus) : Math.min(0.84, 0.70 + bonus);\n"
        "  }"
    )
    if v13_zen in s:
        s = once(s, v13_zen, zen_replacement, "Zenith V13 speed")
    else:
        s = once(s, v12_zen, zen_replacement, "Zenith V12 speed")
    # Old comments may describe the V12/V13 caps and are now misleading.
    s = s.replace(
        "    // NYTHERA_ZENITH_START_SPEED_V13: 0.70-0.84x spear / 1.70-1.84x twin blades at 0-14 stacks.",
        f"    // {TAG}: 0.70-0.84x spear / 1.70-1.84x twin blades at 0-14 stacks."
    )
    return s


def patch_game(s: str) -> str:
    if TAG in s:
        return s
    old_v13 = (
        "desc: \"Orbit Marks last 25s; Dreadfall speed begins at 0.80× and grows to 1.70× over 14 damaging hits (round only). Four air slices remain. Base scythe attacks: −10% damage; skills: −20%.\""
    )
    old_v12 = (
        "desc: \"Orbit Marks last 25s; Dreadfall strikes gain +0.05× attack speed, max 1.70× for the round. Four air slices remain. Base scythe attacks: −10% damage; skills: −20%.\""
    )
    new = (
        "desc: \"Orbit Marks last 25s; Dreadfall starts at 0.80× and gains +0.05× per damaging hit, max 1.50× for this round. Four air slices remain. Base scythe attacks: −10% damage; skills: −20%.\""
    )
    s = once(s, old_v13 if old_v13 in s else old_v12, new, "Nythera passive description")
    return s + f"\n// {TAG}: speed-cap description synced with combat.\n"


def patch_view(s: str) -> str:
    if TAG in s:
        return s
    z13 = "  const speed = Math.min(blades ? 3.4 : 2.4, (blades ? 1.70 : 0.70) + count * 0.01); // NYTHERA_ZENITH_START_SPEED_V13"
    z12 = "  const speed = Math.min(blades ? 3.4 : 2.4, (blades ? 2 : 1) + count * 0.01);"
    znew = f"  const speed = Math.min(blades ? 1.84 : 0.84, (blades ? 1.70 : 0.70) + count * 0.01); // {TAG}"
    s = once(s, z13 if z13 in s else z12, znew, "Zenith HUD multiplier")

    n13 = "  const speed = Math.min(1.7, 0.80 + stacks * 0.05 + 0.20 * stacks / 14); // NYTHERA_ZENITH_START_SPEED_V13"
    n12 = "  const speed = Math.min(1.7, 1 + stacks * 0.05);"
    nnew = f"  const speed = Math.min(1.50, 0.80 + stacks * 0.05); // {TAG}"
    s = once(s, n13 if n13 in s else n12, nnew, "Nythera HUD multiplier")

    # Update tooltip/comment to agree with actual calculation.
    s = s.replace(
        "// Dreadfall starts at 0.80x and scales to 1.70x at 14 damaging hits.",
        "// Dreadfall starts at 0.80x and scales to 1.50x at 14 damaging hits."
    )
    s = s.replace(
        "// Dreadfall increases Nythera's real attack speed by 0.1x per damaging hit.",
        "// Dreadfall gives Nythera +0.05x per damaging hit, from 0.80x to 1.50x."
    )
    s = s.replace(
        'title="Dreadfall Tempo: starts at 0.80x attack speed; 14 real damaging Dreadfall hits raise it to 1.70x. Persists through stance switches, resets next round. Block/parry/clash deny stacks."',
        'title="Dreadfall Tempo: starts at 0.80x attack speed; 14 real damaging Dreadfall hits raise it to 1.50x. Persists through stance switches, resets next round. Block/parry/clash deny stacks."'
    )
    s = s.replace(
        'title="Dreadfall Tempo: every real damaging hit in Dreadfall earns +0.05x attack speed. Caps at 1.70x, persists through stance switches, resets next round. Block/parry/clash deny stacks."',
        'title="Dreadfall Tempo: starts at 0.80x; every damaging Dreadfall hit earns +0.05x speed, capped at 1.50x. Persists through stance switches; resets next round. Block/parry/clash deny stacks."'
    )
    return s


def locate_web() -> Path:
    if len(sys.argv) > 2:
        raise ValueError("Usage: python install_nythera_zenith_lower_caps_v14.py [web folder]")
    if len(sys.argv) == 2:
        roots = [Path(sys.argv[1]).expanduser().resolve()]
    else:
        here = Path(__file__).resolve().parent
        roots = [here, Path.cwd(), here / "web", Path.cwd() / "web"]
    for root in roots:
        if (root / "src/game/fighter.ts").is_file() and (root / "src/ui/GameView.tsx").is_file():
            return root.resolve()
    raise FileNotFoundError("Place this installer in fight-royale/web or pass the path to web.")


def main() -> int:
    try:
        root = locate_web()
        targets = [
            ("src/game/fighter.ts", patch_fighter),
            ("src/game/game.ts", patch_game),
            ("src/ui/GameView.tsx", patch_view),
        ]
        updates = []
        for relative, transform in targets:
            path = root / relative
            original = path.read_text(encoding="utf-8")
            revised = transform(original)
            if original != revised:
                updates.append((relative, path, original, revised))
        if not updates:
            print("V14 already installed: no changes made.")
            return 0
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        staged = []
        committed = []
        try:
            for relative, path, original, revised in updates:
                backup = path.with_name(f"{path.name}.before_{TAG}_{stamp}.bak")
                tmp = path.with_name(f"{path.name}.{TAG}.tmp")
                backup.write_text(original, encoding="utf-8")
                tmp.write_text(revised, encoding="utf-8")
                staged.append((relative, path, backup, tmp))
            for relative, path, backup, tmp in staged:
                os.replace(tmp, path)
                committed.append((path, backup))
                print("UPDATED:", relative)
        except Exception:
            for path, backup in reversed(committed):
                shutil.copy2(backup, path)
            raise
        finally:
            for _, _, _, tmp in staged:
                if tmp.exists():
                    tmp.unlink()
        print("\nV14 complete: speed reductions persist at EVERY stack, including the cap.")
        print("  Nythera: 0.80x start -> 1.50x cap after 14 Dreadfall hits (+0.05x/hit).")
        print("  Zenith spear: 0.70x start -> 0.84x after 14 hits (+0.01x/hit).")
        print("  Zenith twin: 1.70x start -> 1.84x after 14 hits (+0.01x/hit).")
        print("  Zenith still loses Tempo after 5s without a hit.")
        print("  Source backups saved beside files. Next: npx tsc --noEmit -p .")
        return 0
    except Exception as exc:
        print("ERROR:", exc)
        print("No project files were changed if validation failed. This patch targets V12 or V13.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
