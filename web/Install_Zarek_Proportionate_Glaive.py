#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale: Zarek glaive-size + effective-range balance installer.

Zarek's screenshot shows a double-ended glaive disproportionately larger than her
VRoid body. This patch addresses BOTH the visible weapon and real hit distance:
  * Visible double-glaive length: about 29% shorter on VRoid bodies
    (about 22% shorter on the procedural fallback body).
  * All grounded melee hit ranges: -18%, including Arc Flash.
  * Forward attack lunges: -20%.
  * Infinite Crescent's separately created hits: -18% reach.
  * Phantom Spiral's long-distance pass-through: 4.60 -> 3.85.
  * AI Zarek now picks more appropriate distances for her shorter melee kit.

Unchanged: damage, defense, HP, attack timings, cooldowns, skill effects,
Clash Momentum awards, weapon-vs-projectile interactions, Perfect Dodge,
Judgment, and every other fighter.

If you previously installed Install_Zarek_Range_Nerf.py, this recognizes that
nerf and ONLY adds the smaller weapon visuals. It never double-nerfs the range.

Run:       python Install_Zarek_Proportionate_Glaive.py
Or:        python Install_Zarek_Proportionate_Glaive.py "C:\\path\\to\\Fight-Royale"
Check only: python Install_Zarek_Proportionate_Glaive.py "C:\\path\\to\\Fight-Royale" --dry-run

Needs standard Python 3.9+. Creates automatic, timestamped backups in
.clash_backups/ and will not apply the same changes twice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile

VISUAL_MARKER = "FIGHT_ROYALE_ZAREK_PROPORTIONATE_GLAIVE_V1"
RANGE_MARKER = "FIGHT_ROYALE_ZAREK_EFFECTIVE_RANGE_NERF_V1"
FILES = (
    "src/game/model.ts",
    "src/game/kits.ts",
    "src/game/game.ts",
    "src/game/ai.ts",
)


def exact_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one matching code section; found {count}. "
            "No game files were changed. This code version may be different."
        )
    return source.replace(old, new, 1)


def inside(source: str, start_mark: str, end_mark: str,
           old: str, new: str, label: str) -> str:
    start = source.find(start_mark)
    if start < 0 or source.find(start_mark, start + len(start_mark)) >= 0:
        raise RuntimeError(f"{label}: missing or duplicate method start; no changes made.")
    end = source.find(end_mark, start + len(start_mark))
    if end < 0:
        raise RuntimeError(f"{label}: missing method end; no changes made.")
    middle = exact_once(source[start:end], old, new, label)
    return source[:start] + middle + source[end:]


def model_update(source: str) -> str:
    if VISUAL_MARKER in source:
        return source
    # Scale the entire staff group (shaft, blades, glow, and both grip markers).
    # Scaling the group instead of just the mesh geometry keeps the left hand
    # attached correctly and makes bladeTip track the new physical dimensions.
    source = inside(
        source,
        "  private buildGlaive() {",
        "  private buildChainblade() {",
        "    this.glaivePivot = staff;\n",
        "    this.glaivePivot = staff;\n"
        "    // ZAREK_PROPORTIONATE_GLAIVE_V1: shorten shaft, blades, tip, and offhand grip together.\n"
        "    // -22% on procedural bodies; the VRoid hand mount is adjusted separately below.\n"
        "    staff.scale.setScalar(0.78);\n",
        "Shorter visible glaive and anchored grip"
    )
    source = exact_once(
        source,
        'const weaponScale = this.kit === "glaive" ? 0.95 : VRM_WEAPON_SCALE;',
        'const weaponScale = this.kit === "glaive" ? 0.87 : VRM_WEAPON_SCALE; '
        '// ZAREK_PROPORTIONATE_GLAIVE_V1: total VRoid weapon length about -29%',
        "Zarek VRoid-specific weapon scale"
    )
    return f"// {VISUAL_MARKER}\n" + source


def kits_update(source: str) -> str:
    if RANGE_MARKER in source:
        # An older standalone range-nerf installer already did this exactly.
        return source
    add = '''  // ZAREK_EFFECTIVE_RANGE_NERF_V1: hitboxes now match the smaller double-ended glaive.
  // Only grounded melee attack data for Zarek is changed: no damage or passive changes.
  if (kit === "glaive") {
    for (const key of ["l1", "l2", "l3", "l4", "l5", "heavy", "z", "x", "c", "v"]) {
      const move = t[key];
      if (!move || move.type !== "melee") continue;
      move.reach = Math.round(move.reach * 0.82 * 100) / 100; // -18% hit reach
      move.lunge = Math.round(move.lunge * 0.80 * 100) / 100; // -20% forward travel
    }
  }
'''
    source = inside(
        source,
        'export function attacks(kit: string, element: string): Record<string, Attack> {',
        '/** Which skills carry each element',
        '  t.v = bonusSkill(kit, element);\n',
        '  t.v = bonusSkill(kit, element);\n' + add,
        'Zarek authoritative melee reach and lunge'
    )
    return f"// {RANGE_MARKER}\n" + source


def game_update(source: str) -> str:
    if RANGE_MARKER in source:
        return source
    start = '  private stormGlaiveSwing(f: Fighter, a: Attack) {'
    end = '  /** KAIZEN_CHAINBLADE_V1:'
    source = inside(
        source, start, end,
        '            reach: final ? 2.34 : 2.18,',
        '            reach: final ? 1.92 : 1.79, // ZAREK_EFFECTIVE_RANGE_NERF_V1 (-18%)',
        'Infinite Crescent final and multi-hit reach'
    )
    source = inside(
        source, start, end,
        '        if (length > 0.2 && length < 4.6) {',
        '        if (length > 0.2 && length < 3.85) { // ZAREK_EFFECTIVE_RANGE_NERF_V1',
        'Phantom Spiral long-distance entry'
    )
    return f"// {RANGE_MARKER}\n" + source


def ai_update(source: str) -> str:
    if RANGE_MARKER in source:
        return source
    start = '  private offense(f: Fighter, o: Fighter, dt: number) {'
    end = '\n  }\n}'
    source = inside(
        source, start, end,
        ' : f.kit === "greatsword" ? 2.3 : 1.9;',
        ' : f.kit === "greatsword" ? 2.3 : f.kit === "glaive" ? 1.62 : 1.9;',
        'AI Zarek basic melee distance'
    )
    source = inside(
        source, start, end,
        '        if (a.type === "melee") ok = dist < a.reach + 1.5;',
        '        if (a.type === "melee") ok = dist < a.reach + (f.kit === "glaive" ? 0.85 : 1.5);',
        'AI Zarek skill approach distance'
    )
    return f"// {RANGE_MARKER}\n" + source


UPDATES = dict(zip(FILES, (model_update, kits_update, game_update, ai_update)))


def select_root(value: str | None) -> Path:
    candidates = [Path(value).expanduser()] if value else [Path.cwd(), Path(__file__).resolve().parent]
    for root in candidates:
        if all((root / rel).is_file() for rel in FILES):
            return root.resolve()
    if value:
        raise RuntimeError("Select your Fight Royale project folder (containing src/game/model.ts).")
    chosen = ''
    try:
        from tkinter import Tk, filedialog
        win = Tk()
        win.withdraw()
        win.attributes('-topmost', True)
        chosen = filedialog.askdirectory(title="Choose the Fight Royale folder (contains src)")
        win.destroy()
    except Exception:
        pass
    if not chosen:
        try:
            chosen = input('Fight Royale project folder path: ').strip().strip('"')
        except (OSError, EOFError):
            pass
    if not chosen:
        raise RuntimeError("No project folder selected.")
    root = Path(chosen).expanduser().resolve()
    missing = [rel for rel in FILES if not (root / rel).is_file()]
    if missing:
        raise RuntimeError("Selected folder is missing: " + ", ".join(missing))
    return root


def atomic_write(path: Path, data: bytes) -> None:
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.zarek_install_', dir=path.parent, delete=False) as f:
            tmp = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def install(root: Path, dry_run: bool = False) -> tuple[list[str], Path | None]:
    pending: dict[Path, tuple[bytes, bytes]] = {}
    # Validate ALL source edits before touching any real project file.
    for rel in FILES:
        file = root / rel
        before = file.read_bytes()
        bom = b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b''
        source = before[len(bom):].decode('utf-8')
        crlf = source.count('\r\n') > source.count('\n') / 2
        source = source.replace('\r\n', '\n').replace('\r', '\n')
        edited = UPDATES[rel](source)
        if crlf:
            edited = edited.replace('\n', '\r\n')
        after = bom + edited.encode('utf-8')
        if before != after:
            pending[file] = before, after

    names = [str(path.relative_to(root)) for path in pending]
    if dry_run or not pending:
        return names, None

    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_zarek_proportion'
    backup_dir = root / '.clash_backups' / stamp
    # Full backups before first edit; never overwrite backups from previous patches.
    for path, (before, _) in pending.items():
        dest = backup_dir / path.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(before)

    written: list[Path] = []
    try:
        for path, (_, after) in pending.items():
            atomic_write(path, after)
            written.append(path)
    except Exception:
        for path in reversed(written):
            atomic_write(path, pending[path][0])
        raise
    return names, backup_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project', nargs='?', help='Fight Royale root directory')
    ap.add_argument('--dry-run', action='store_true', help='check changes; do not modify the project')
    args = ap.parse_args()
    print('\n=== Fight Royale: Zarek Proportionate Glaive ===\n')
    try:
        root = select_root(args.project)
        changes, backups = install(root, args.dry_run)
        if not changes:
            print('Already installed. No changes needed.')
        elif args.dry_run:
            print('Compatibility OK. These files would change:')
            for rel in changes: print('  -', rel)
        else:
            print('Update installed successfully. Updated:')
            for rel in changes: print('  -', rel)
            print('Backups:', backups)
            print('Zarek: VRoid glaive ~29% shorter; melee reach -18%; lunges -20%.')
        print('Damage, skills, Judgment, projectile destruction, and Clash Momentum unchanged.')
        return 0
    except (OSError, UnicodeError, RuntimeError) as exc:
        print('INSTALL STOPPED:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    code = main()
    if len(sys.argv) == 1 and sys.stdin.isatty():
        try:
            input('\nPress Enter to close...')
        except (OSError, EOFError):
            pass
    raise SystemExit(code)
