#!/usr/bin/env python3
"""Fight Royale: Aster's 50s stacking Weaken (max five), with stack hit indicators.

Usage, from your game's web folder:
    python apply_aster_weaken_stacks.py
Or:
    python apply_aster_weaken_stacks.py C:/path/to/web

Changes src/game/status.ts, kits.ts, game.ts. No third-party packages required.
Creates timestamped backups before writing. Safe to run again.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

TAG = "ASTER_WEAKEN_50S_5_STACKS_V1_20261107"
FILES = ("status.ts", "kits.ts", "game.ts")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one original code block, found {count}. No files changed.")
    return source.replace(old, new, 1)


def patch_status(s: str) -> str:
    if TAG in s:
        return s
    s = replace_once(
        s,
        '  weaken: { label: "WEAKENED", color: "#fff2b0", bit: 32, text: (t, p) => `Weaken: -${Math.round((1 - p) * 100)}% damage for ${t}s` },',
        '  weaken: { label: "WEAKENED", color: "#fff2b0", bit: 32, text: (t, p) => `Weaken: -${Math.round((1 - p) * 100)}% outgoing damage per stack (multiplicative); up to 5 stacks (${Math.round((1 - Math.pow(p, 5)) * 100)}% max). Lasts ${t}s; each hit adds a stack and refreshes the timer.` },',
        "status tooltip",
    )
    s = replace_once(
        s,
        "const POISON_STACKS = 3;",
        "const POISON_STACKS = 3;\nconst WEAKEN_STACKS = 5;",
        "weaken maximum stack constant",
    )
    s = replace_once(
        s,
        '''    if (cur) {
      cur.t = Math.max(cur.t, t);
      if (kind === "poison") cur.stacks = Math.min(cur.stacks + 1, POISON_STACKS);
      else cur.p = kind === "slow" || kind === "weaken" ? Math.min(cur.p, p) : Math.max(cur.p, p);
    } else {''',
        '''    if (cur) {
      // Weaken always refreshes its entire 50s duration when another hit lands.
      cur.t = kind === "weaken" ? t : Math.max(cur.t, t);
      if (kind === "poison") cur.stacks = Math.min(cur.stacks + 1, POISON_STACKS);
      else if (kind === "weaken") {
        cur.stacks = Math.min(cur.stacks + 1, WEAKEN_STACKS);
        cur.p = Math.min(cur.p, p); // each stack uses the strongest existing reduction
      } else cur.p = kind === "slow" ? Math.min(cur.p, p) : Math.max(cur.p, p);
    } else {''',
        "stack/refresh implementation",
    )
    s = replace_once(
        s,
        '''  /** Outgoing damage multiplier (weaken). */
  dmgMult() { return this.m.get("weaken")?.p ?? 1; }''',
        '''  /** Every Weaken stack multiplies outgoing damage by the skill's power (0.8^stacks for Aster). */
  dmgMult() {
    const weaken = this.m.get("weaken");
    return weaken ? Math.pow(weaken.p, weaken.stacks) : 1;
  }''',
        "weaken damage scaling",
    )
    return f"// {TAG}\n" + s


def patch_kits(s: str) -> str:
    if TAG in s:
        return s
    s = replace_once(
        s,
        "  // Keep its existing name, damage and cooldown; Weaken reduces outgoing damage 20% for 4s.",
        "  // Keep its existing name, damage and cooldown; each Weaken stack reduces outgoing damage 20% multiplicatively for 50s, up to x5.",
        "Aster sweep note",
    )
    s = replace_once(
        s,
        '''    t.x.effect_t = 4;
    t.x.effect_p = 0.80;
    t.x.desc = "Crouch low, advance, and sweep the blade forward. A hit weakens the enemy for 4 seconds.";''',
        '''    t.x.effect_t = 50;
    t.x.effect_p = 0.80;
    t.x.desc = "Crouch low, advance, and sweep the blade forward. A hit adds Weaken (50s, max 5 stacks). Each stack reduces enemy outgoing damage by 20% multiplicatively. Another Weaken hit refreshes all stacks.";''',
        "Aster X weakened follow-ups",
    )
    s = replace_once(
        s,
        '  light: ["weaken", 4, 0.8, ["c", "v"]],              // Aster: Blade Wave, Judgment',
        '  light: ["weaken", 50, 0.8, ["x", "c"]],             // Aster: Rising Slash / low sweep + Blade Wave (Judgment is a self-buff)',
        "Aster elemental Weaken on X and C",
    )
    return f"// {TAG}\n" + s


def patch_game(s: str) -> str:
    if TAG in s:
        return s
    s = replace_once(
        s,
        '''        if (info && result !== "ko" && this.time - (this.statusLabelAt.get(d) ?? -9) > 1.2) {
          this.statusLabelAt.set(d, this.time);
          const ss: Record<string, string> = { burn: "burn", paralyze: "shock", poison: "poison", bleed: "bleed" };
          if (ss[a.effect]) this.snd(ss[a.effect], 0.6);
          this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.95, 0)), info.label, info.color, 0.85);
        }''',
        '''        // Aster's Weaken shows its current stack on every successful follow-up,
        // rather than hiding stack increases behind the usual status-text throttle.
        const weakenStack = a.effect === "weaken" && (d instanceof Fighter || d instanceof Mob)
          ? d.status.stacks("weaken") : 0;
        if (info && result !== "ko" && (weakenStack > 0 || this.time - (this.statusLabelAt.get(d) ?? -9) > 1.2)) {
          this.statusLabelAt.set(d, this.time);
          const ss: Record<string, string> = { burn: "burn", paralyze: "shock", poison: "poison", bleed: "bleed" };
          if (ss[a.effect]) this.snd(ss[a.effect], 0.6);
          const statusText = weakenStack > 0 ? `WEAKEN x${weakenStack}` : info.label;
          this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.95, 0)), statusText, info.color, 0.85);
        }''',
        "float text updates with Weaken stacks",
    )
    return f"// {TAG}\n" + s


def find_project(path: Path) -> Path:
    for root in (path, path / "web"):
        if all((root / "src" / "game" / name).is_file() for name in FILES):
            return root
    raise RuntimeError("Could not find src/game/status.ts, kits.ts and game.ts. Run from the web folder or pass the game's web folder path.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="Path to the web project (or parent folder)")
    args = parser.parse_args()
    try:
        root = find_project(Path(args.project).expanduser().resolve())
        folder = root / "src" / "game"
        patches = {"status.ts": patch_status, "kits.ts": patch_kits, "game.ts": patch_game}
        # Validate all three file transformations before changing any files.
        versions = {}
        for name, transform in patches.items():
            original = (folder / name).read_text(encoding="utf-8")
            versions[name] = (original, transform(original))
        if all(original == updated for original, updated in versions.values()):
            print("Already installed: Aster's 50-second, five-stack Weaken.")
            return 0
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        changed = [(name, before, after) for name, (before, after) in versions.items() if before != after]
        for name, _before, _after in changed:
            backup = folder / f"{name}.before_aster_weaken_{now}.bak"
            shutil.copy2(folder / name, backup)
        for name, _before, after in changed:
            (folder / name).write_text(after, encoding="utf-8")
        print(f"Installed Aster Weaken (50s, five stacks, 0.8^stacks damage multiplier) in {root}")
        print("Updated:", ", ".join(name for name, *_ in changed))
        print("Created timestamped .bak files beside the modified sources.")
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"Patch stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
