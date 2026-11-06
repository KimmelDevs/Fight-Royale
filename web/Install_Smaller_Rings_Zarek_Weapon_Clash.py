#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale: 50% smaller COMBAT CIRCLES + restore Zarek weapon-clash Momentum.

Works over either the Impact & Clash Overhaul alone or with the Compact Impact
Effects update. It edits only src/game/game.ts and src/game/fx.ts.

  python Install_Smaller_Rings_Zarek_Weapon_Clash.py
  python Install_Smaller_Rings_Zarek_Weapon_Clash.py "C:\\Games\\Fight-Royale"
  python Install_Smaller_Rings_Zarek_Weapon_Clash.py "C:\\Games\\Fight-Royale" --dry-run

Changes:
- Halves the actual radius of the billboard clash halo and both impact halos.
- Halves the ground ring radii produced by actual weapon clashes, parries,
  heavy hits, and Kaizen chain-guard clashes. These are visuals, not hitboxes.
- A true melee-weapon-vs-melee-weapon clash gives Zarek +1 Clash Momentum.
  Both CPU/player Zarek work; blocks/parries do not award it.
- A melee swing destroying a non-bomb projectile still awards +1 as before.
- All other VFX (sparks, flashes, camera, hitstop) and abilities stay untouched.

All files are checked before editing. Backups saved in .clash_backups/.
Re-running is safe. No packages or internet needed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile

MARKER = "FIGHT_ROYALE_SMALLER_COMBAT_RINGS_ZAREK_WEAPON_CLASH_V1"
OVERHAUL_MARKER = "FIGHT_ROYALE_IMPACT_CLASH_OVERHAUL_V1"
ZAREK_PROJECTILE_MARKER = "ZAREK_PROJECTILE_DESTROY_ONLY_V2_NOV07"
FILES = ("src/game/game.ts", "src/game/fx.ts")


def once(source: str, old: str, new: str, reason: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{reason}: expected one matching code block; found {count}. "
                           "Your game uses different code; no files were changed.")
    return source.replace(old, new, 1)


def in_section(source: str, begin: str, end: str, old: str, new: str, reason: str) -> str:
    start = source.find(begin)
    if start < 0 or source.find(begin, start + len(begin)) >= 0:
        raise RuntimeError(f"{reason}: could not uniquely identify the combat method.")
    stop = source.find(end, start + len(begin))
    if stop < 0:
        raise RuntimeError(f"{reason}: could not identify the end of the combat method.")
    return source[:start] + once(source[start:stop], old, new, reason) + source[stop:]


def patch_fx(source: str) -> str:
    if MARKER in source:
        return source
    if OVERHAUL_MARKER not in source:
        raise RuntimeError("fx.ts: install the Impact & Clash Overhaul first.")

    # The previous compact update scales entire groups, but it did not change
    # individual ground ring radii. Reduce the CIRCLES themselves as requested.
    # Multiplying halo scale rather than whole groups preserves spark/streak sizes.
    source = in_section(
        source, '  clashBurst(pos: THREE.Vector3', '  /** IMPACT_OVERHAUL_V1:',
        '      halo.scale.setScalar(size * (0.15 + 1.25 * (1 - (1 - progress) ** 3)));',
        '      halo.scale.setScalar(size * 0.5 * (0.15 + 1.25 * (1 - (1 - progress) ** 3)));'
        ' // SMALLER_COMBAT_RINGS_V1', 'clash circle radius')
    source = in_section(
        source, '  impactBurst(pos: THREE.Vector3', '  /** Real-time (not hitstop-scaled)',
        '      ringA.scale.setScalar(weight * (0.15 + 1.45 * ease));',
        '      ringA.scale.setScalar(weight * 0.5 * (0.15 + 1.45 * ease));'
        ' // SMALLER_COMBAT_RINGS_V1', 'white impact circle radius')
    source = in_section(
        source, '  impactBurst(pos: THREE.Vector3', '  /** Real-time (not hitstop-scaled)',
        '      ringB.scale.setScalar(weight * (0.08 + 1.95 * ease));',
        '      ringB.scale.setScalar(weight * 0.5 * (0.08 + 1.95 * ease));'
        ' // SMALLER_COMBAT_RINGS_V1', 'colored impact circle radius')
    return f'// {MARKER}\n' + source


def patch_game(source: str) -> str:
    if MARKER in source:
        return source
    if OVERHAUL_MARKER not in source:
        raise RuntimeError("game.ts: install the Impact & Clash Overhaul first.")
    if ZAREK_PROJECTILE_MARKER not in source:
        raise RuntimeError("game.ts: install the Zarek Projectile-Only update first. "
                           "This patch preserves its block/parry restrictions.")

    # True weapon-on-weapon collisions are handled here for human and AI fighters.
    # The helper itself checks kit='glaive', so non-Zarek fighters get no stacks.
    source = in_section(
        source, '  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {',
        '  // --- mob attacks',
        '    this.fxp("impactFrame", "clash", "#ffe5a2", 0.80);',
        '    this.fxp("impactFrame", "clash", "#ffe5a2", 0.80);\n'
        '    // ZAREK_WEAPON_CLASH_MOMENTUM_V1: reward genuine opposing melee weapon contact,\n'
        '    // not passive blocks, parries, shield hits or projectile defenses.\n'
        '    for (const fighter of [a, b]) this.awardZarekClash(fighter);',
        'Zarek weapon clash passive')

    # World-space rings that look like huge circles on the GROUND are separate
    # from the impactBurst / clashBurst sprites. These four are specific impact
    # reactions; don't touch skill telegraphs, danger-zone markers or AoE ranges.
    source = in_section(
        source, '  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {',
        '  // --- mob attacks',
        '    this.fxp("ring", pos, "#ffe699", 3, 0.45, 0.9);',
        '    this.fxp("ring", pos, "#ffe699", 1.5, 0.45, 0.9);',
        'true weapon-clash ground circle')
    source = in_section(
        source, '      case "kaizen_guard_clash": {', '      case "hit": case "crit": case "ko": {',
        '        this.fxp("ring", shieldPos, "#ffe0b0", 1.7, 0.25, 0.8);',
        '        this.fxp("ring", shieldPos, "#ffe0b0", 0.85, 0.25, 0.8);',
        'Kaizen chain-guard impact circle')
    source = in_section(
        source, '      case "hit": case "crit": case "ko": {', '      case "blocked":',
        '        if (a.heavy) this.fxp("ring", hitPos, glow, 2.2, 0.35, 0.9);',
        '        if (a.heavy) this.fxp("ring", hitPos, glow, 1.1, 0.35, 0.9);',
        'heavy-hit ground circle')
    source = in_section(
        source, '      case "parry":', '      case "counter": {',
        '        this.fxp("ring", shieldPos, "#b3f2ff", 1.6, 0.35, 0.9);',
        '        this.fxp("ring", shieldPos, "#b3f2ff", 0.8, 0.35, 0.9);',
        'parry ground circle')

    # Strong constraints: no incidental award sites for blocks/parries/guard.
    if source.count('this.awardZarekClash(') != 2:
        raise RuntimeError("Unexpected Zarek Momentum award sites. No changes were made.")
    if 'if (!bomb) this.awardZarekClash(defender);' not in source:
        raise RuntimeError("Cannot find Zarek's non-bomb projectile award; stopped safely.")
    return f'// {MARKER}\n' + source


PATCHES = {'src/game/game.ts': patch_game, 'src/game/fx.ts': patch_fx}


def project_root(user_path: str | None) -> Path:
    paths = [Path(user_path).expanduser()] if user_path else [Path.cwd(), Path(__file__).resolve().parent]
    for root in paths:
        if all((root / name).is_file() for name in FILES):
            return root.resolve()
    if user_path:
        raise RuntimeError("Select the Fight Royale root folder containing src/game/game.ts and fx.ts.")
    chosen = ""
    try:
        from tkinter import Tk, filedialog
        window = Tk()
        window.withdraw()
        window.attributes('-topmost', True)
        chosen = filedialog.askdirectory(title='Select Fight Royale project folder (contains src)')
        window.destroy()
    except Exception:
        pass
    if not chosen:
        try:
            chosen = input("Fight Royale project folder (full path): ").strip().strip('"')
        except (EOFError, OSError):
            pass
    if not chosen:
        raise RuntimeError("No project folder selected.")
    root = Path(chosen).expanduser().resolve()
    if not all((root / name).is_file() for name in FILES):
        raise RuntimeError("Chosen folder is missing src/game/game.ts or fx.ts.")
    return root


def write_atomically(path: Path, data: bytes) -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.clash_patch_', delete=False) as f:
            temp_path = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def install(root: Path, dry_run: bool = False) -> tuple[list[str], Path | None]:
    changes: dict[Path, tuple[bytes, bytes]] = {}
    for relative in FILES:
        path = root / relative
        before = path.read_bytes()
        bom = b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b''
        text = before[len(bom):].decode('utf-8')
        crlf = text.count('\r\n') > text.count('\n') / 2
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')
        updated = PATCHES[relative](normalized)
        after = bom + (updated.replace('\n', '\r\n') if crlf else updated).encode('utf-8')
        if before != after:
            changes[path] = before, after
    modified = [str(p.relative_to(root)) for p in changes]
    if dry_run or not changes:
        return modified, None

    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_smaller_rings_zarek'
    backup = root / '.clash_backups' / stamp
    for path, (before, _) in changes.items():
        dest = backup / path.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(before)
    written: list[Path] = []
    try:
        for path, (_, after) in changes.items():
            write_atomically(path, after)
            written.append(path)
    except Exception:
        for path in reversed(written):
            write_atomically(path, changes[path][0])
        raise
    return modified, backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', nargs='?', help='Fight Royale project directory')
    parser.add_argument('--dry-run', action='store_true', help='check compatibility; do not write')
    args = parser.parse_args()
    print('\n=== Fight Royale: Smaller Combat Circles + Zarek Weapon Clash Fix ===\n')
    try:
        root = project_root(args.project)
        changed, backup = install(root, dry_run=args.dry_run)
    except Exception as error:
        print('ERROR:', error)
        return 1
    print('Project:', root)
    if not changed:
        print('Already installed; no changes needed.')
    elif args.dry_run:
        print('Compatible. Would update:', ', '.join(changed))
    else:
        print('Updated:', ', '.join(changed))
        print('Backups:', backup)
        print('Impact/clash circular rings: 50% smaller than the current version.')
        print('Zarek: +1 Momentum for real melee weapon clashes or destroyed non-bomb projectiles.')
        print('Blocking and parrying do not grant Momentum. Skill hitboxes are unchanged.')
        print('Restart your game/dev server, then test a weapon clash with Zarek.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
