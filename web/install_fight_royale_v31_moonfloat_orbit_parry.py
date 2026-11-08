#!/usr/bin/env python3
"""Fight Royale V31: Moonfloat Orbit slow and 20% max-guard recovery per parry.

Run in the Fight Royale web folder:
    python install_fight_royale_v31_moonfloat_orbit_parry.py
Or:
    python install_fight_royale_v31_moonfloat_orbit_parry.py "C:/path/to/fight-royale/web"

Requires V29 (V30 optional). No other packages, Git, SQL, or remote operations.
All code anchors are verified in memory BEFORE writing; backups are made first.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import shutil
import sys

MARK = "FIGHT_ROYALE_V31_MOONFLOAT_ORBIT_PARRY"
FILES = (
    "src/game/fighter.ts", "src/game/game.ts", "src/game/ai.ts",
    "src/game/roster.ts", "src/ui/GameView.tsx",
)


def apply_changes(source: dict[str, str]) -> dict[str, str]:
    out = dict(source)

    def replace(file: str, old: str, new: str, count: int = 1) -> None:
        existing = out[file]
        actual = existing.count(old)
        if actual != count:
            raise RuntimeError(
                f"{file}: expected {count} exact anchor(s), found {actual}: {old[:100]!r}. "
                "Nothing was changed; upload your current src if this patch needs adaptation."
            )
        out[file] = existing.replace(old, new, count)

    f = "src/game/fighter.ts"
    replace(f,
        'const NYTHERA_V26_TUNING = { maxAirSlices: 3, speedCap: 1.48, orbitCap: 6 } as const;',
        '// ' + MARK + ': each visible Moonfloat mark lowers target attack and guard-raise speed by 5%.\n'
        'export const NYTHERA_ORBIT_SLOW_TUNING = {\n'
        '  perMark: 0.05,\n'
        '  maxMarks: 6,\n'
        '} as const;\n'
        'const NYTHERA_V26_TUNING = { maxAirSlices: 3, speedCap: 1.48, orbitCap: 6 } as const;')
    replace(f,
        '  orbitDisplayStacks = 0;\n  orbitDisplayT = 0;',
        '  orbitDisplayStacks = 0;\n  orbitDisplayT = 0;\n'
        '  /** Live opponent debuff. Computed from the existing synced Orbit count; no new snapshot data. */\n'
        '  orbitSlowMultiplier(): number {\n'
        '    const marks = this.orbitDisplayT > 0\n'
        '      ? Math.max(0, Math.min(NYTHERA_ORBIT_SLOW_TUNING.maxMarks, this.orbitDisplayStacks)) : 0;\n'
        '    return 1 - NYTHERA_ORBIT_SLOW_TUNING.perMark * marks;\n'
        '  }')
    replace(f,
        '  /** A true parry relieves one fatigue stack and restores 10% max guard. */\n'
        '  recoverFromParry() {\n'
        '    this.guard = Math.min(this.maxGuard, this.guard + this.maxGuard * 0.10);',
        '  /** A true parry relieves one fatigue stack and restores 20% max guard (once). */\n'
        '  recoverFromParry() {\n'
        '    this.guard = Math.min(this.maxGuard, this.guard + this.maxGuard * 0.20);')
    replace(f,
        '    return special * 0.70;\n  }',
        '    // Orbit Marks slow the defender\'s ability to raise the shield.\n'
        '    // 6 marks => 0.70x guard-raise speed => ~1.43x startup duration.\n'
        '    return special * 0.70 / this.orbitSlowMultiplier();\n  }')
    replace(f,
        '    // Standardize the parry counter windup from the already-scaled timing.',
        '    // ' + MARK + ': apply Moonfloat slow once, after passive boosts and Guard Fatigue.\n'
        '    // Attack and skill windup/active/recovery slow; cooldowns stay unchanged.\n'
        '    if (this.atk && this.orbitDisplayT > 0 && this.orbitDisplayStacks > 0) {\n'
        '      const orbitSpeed = this.orbitSlowMultiplier();\n'
        '      this.atk = { ...this.atk,\n'
        '        wind: this.atk.wind / orbitSpeed,\n'
        '        active: this.atk.active / orbitSpeed,\n'
        '        recover: this.atk.recover / orbitSpeed };\n'
        '    }\n'
        '    // Standardize the parry counter windup from the already-scaled timing.')

    f = "src/game/game.ts"
    replace(f,
        'df.recoverFromParry(); // FIGHT_ROYALE_V29_PARRY_ORBIT_GUARD: +10% max guard, -1 fatigue',
        'df.recoverFromParry(); // ' + MARK + ': +20% max guard, -1 fatigue (once per parry)')
    replace(f,
        'Successful parries remove 1 stack and recover 10% maximum guard.',
        'Successful parries remove 1 stack and recover 20% maximum guard.')
    replace(f,
        'desc: "Moonfloat damaging hits build up to six Orbit Marks (25s). Each damaging Dreadfall hit consumes one mark to earn one speed stack.",',
        'desc: "Moonfloat damage adds Orbit Marks (max 6, 25s). Each mark slows the marked fighter\'s attack and shield-raise speed by 5% (up to 30%). Dreadfall damaging hits consume one mark to gain one speed stack.",')
    replace(f,
        'desc: "Moonfloat damaging hits build up to 6 Orbit Marks lasting 25s. Each damaging Dreadfall hit consumes 1 mark for +0.05× speed (up to 1.48×). Without marks, no speed is gained. Three aerial slices. Base attacks: −10% damage; skills: −20%."',
        'desc: "Moonfloat damaging hits build up to 6 Orbit Marks (25s), each slowing enemy attack/guard-raise speed by 5%. Each damaging Dreadfall hit spends 1 Orb for +0.05× speed (up to 1.48×); without Orbs, no speed gain. Three aerial slices. Base attacks: −10% damage; skills: −20%."')

    f = "src/game/ai.ts"
    replace(f,
        '    // V29: only switch to Dreadfall if the target already carries Moonfloat marks.\n'
        '    // Do not camp Dreadfall when the target has nothing left to consume.\n'
        '    const orbit = o.orbitDisplayT > 0 ? o.orbitDisplayStacks : 0;\n'
        '    if (canShift && f.gravityMode === "light" && orbit >= (punish ? 1 : 2) &&\n'
        '        gap < 3.10) return act("f");',
        '    // ' + MARK + ': Moonfloat stays in light stance to build a meaningful slow.\n'
        '    // Spend only when 4+ marks are banked, or 2+ during a real punish opening.\n'
        '    // With no marks, heavy mode never grants extra Dreadfall speed.\n'
        '    const orbit = o.orbitDisplayT > 0 ? o.orbitDisplayStacks : 0;\n'
        '    if (canShift && f.gravityMode === "light" && orbit >= (punish ? 2 : 4) &&\n'
        '        gap < 3.10) return act("f");')

    f = "src/game/roster.ts"
    replace(f,
        'desc: "Moonfloat dances lift the enemy; Dreadfall crushes Orbit Marks. F switches gravity. Scythe executions reward confirmed aerial combos, not unavoidable grabs.",',
        'desc: "Moonfloat hits apply up to 6 Orbit Marks, each slowing enemy attacks and shield raising by 5%. Dreadfall spends one Orb per damaging hit to build attack speed. F switches gravity; scythe attacks remain defendable.",')

    f = "src/ui/GameView.tsx"
    replace(f,
        'title="Nythera Orbit Marks: 25s on contact, consumed by Dreadfall\'s successful scythe strikes"',
        'title="Moonfloat: each Orbit Mark slows enemy attacks and guard raising 5% (up to 30%, 25s); Dreadfall spends one mark per damaging hit"')

    return out


def main() -> int:
    base = Path(sys.argv[1] if len(sys.argv) > 1 else '.').expanduser().resolve()
    print('FIGHT ROYALE V31 — MOONFLOAT ORB SLOW + 20% PARRY GUARD |', base)
    written: list[str] = []
    backups: dict[str, Path] = {}
    try:
        original: dict[str, str] = {}
        for rel in FILES:
            dest = base / rel
            if not dest.is_file():
                raise RuntimeError(f'Missing {rel}; run from Fight Royale/web')
            original[rel] = dest.read_text(encoding='utf-8-sig')
        if any(MARK in data for data in original.values()):
            raise RuntimeError('V31 appears to be installed already; no files changed.')
        if 'FIGHT_ROYALE_V29_PARRY_ORBIT_GUARD' not in original['src/game/fighter.ts']:
            raise RuntimeError('V29 source is required before installing V31; no files changed.')
        updated = apply_changes(original)  # all anchor checks in memory, before any writes
        changed = [rel for rel in FILES if updated[rel] != original[rel]]
        if len(changed) != len(FILES):
            raise RuntimeError('Not every required file was updated; no files changed.')
        ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_dir = base / '.fight-royale-backups' / ('v31-' + ts)
        for rel in changed:
            backup = backup_dir / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(base / rel, backup)
            backups[rel] = backup
        try:
            for rel in changed:
                (base / rel).write_text(updated[rel], encoding='utf-8')
                written.append(rel)
                print('  updated', rel)
        except Exception:
            for rel in written:
                shutil.copy2(backups[rel], base / rel)
            raise
        print('\nInstalled. Backups:', backup_dir)
        print('Next: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as e:
        print('ERROR:', e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
