#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale | Aster tank balance ONLY — Judgment untouched.

Standalone, safe installer: no libraries, ZIP, internet, or existing installers needed.
Run: python Install_Aster_Balance.py [PATH_TO_GAME] [--dry-run]
The game directory must contain src/game/{fighter,roster}.ts.
Only modifies Aster (knight with light element). Judgment logic, duration, damage, descriptions, and other character abilities are not edited. Previous patches remain intact.
Creates backup copies at .aster_backups/<timestamp>/ before updating.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import shutil
import sys
import tempfile

MARKER = "ASTER_TANK_ONLY_V2_20261107"


def once(text: str, before: str, after: str, path: str) -> str:
    count = text.count(before)
    if count != 1:
        raise ValueError(f"{path}: expected exactly one matching section, found {count}. "
                         "Nothing has been installed. Your game version may differ.")
    return text.replace(before, after, 1)


def patch_fighter(text: str) -> str:
    filename = "fighter.ts"
    if MARKER in text:
        return text
    text = once(text,
        "    this.maxHp = st.hp; this.maxGuard = st.guard; this.moveSpeed = st.move; this.walkSpeed = st.walk;",
        "    this.maxHp = st.hp; this.maxGuard = st.guard; this.moveSpeed = st.move; this.walkSpeed = st.walk;\n"
        "    // Aster only: +12% HP (2500 -> 2800), +25% shield guard (100 -> 125).\n"
        "    if (this.kit === \"knight\" && look.element === \"light\") {\n"
        "      this.maxHp *= 1.12;\n"
        "      this.maxGuard *= 1.25;\n"
        "    }", filename)
    text = once(text,
        "    this.atkPower *= this.dmgMult * (this.rageT > 0 ? RAGE_MULT : 1) * this.status.dmgMult();",
        "    this.atkPower *= this.dmgMult * (this.rageT > 0 ? RAGE_MULT : 1) * this.status.dmgMult();\n"
        "    // Aster deals 15% less damage from all attacks. Judgment mechanics remain unchanged.\n"
        "    if (this.kit === \"knight\" && this.look.element === \"light\") this.atkPower *= 0.85;", filename)
    text = once(text,
        "    let dmg = a.dmg * power;",
        "    let dmg = a.dmg * power;\n"
        "    // Aster's armor reduces incoming HP damage by 10%, including guard breaks.\n"
        "    if (this.kit === \"knight\" && this.look.element === \"light\") dmg *= 0.90;", filename)
    return "// " + MARKER + "\n" + text


def patch_roster(text: str) -> str:
    filename = "roster.ts"
    if MARKER in text:
        return text
    text = once(text,
        '  { id: "aster", title: "Azure Knight", role: "Knight - Sword & Shield",\n'
        '    desc: "A steady guardian. Big guard, heavy sword swings, a shield that shrugs off blows.",\n'
        '    stats: { power: 4, speed: 3, range: 2, defense: 5 },',
        '  { id: "aster", title: "Azure Knight", role: "Knight - Sword & Shield",\n'
        '    desc: "A tough frontline guardian with reinforced guard and armor, trading damage for endurance.",\n'
        '    stats: { power: 3, speed: 3, range: 2, defense: 5 },', filename)
    return "// " + MARKER + "\n" + text


PATCHES = {
    "fighter.ts": patch_fighter,
    "roster.ts": patch_roster,
}


def find_project(cli_path: str | None) -> Path:
    candidates = []
    if cli_path:
        candidates.append(Path(cli_path).expanduser())
    else:
        candidates.extend((Path.cwd(), Path(__file__).resolve().parent))
    for root in candidates:
        if all((root / "src" / "game" / name).is_file() for name in PATCHES):
            return root.resolve()
    if cli_path:
        raise FileNotFoundError("Selected folder does not contain src/game/*.ts. Select the game project root.")
    try:
        from tkinter import Tk, filedialog
        ui = Tk()
        ui.withdraw()
        ui.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Select your Fight Royale project folder (contains src)")
        ui.destroy()
    except Exception:
        folder = None
    if not folder:
        folder = input("Full path to Fight Royale folder (contains src): ").strip().strip('"')
    root = Path(folder).expanduser()
    if not all((root / "src" / "game" / name).is_file() for name in PATCHES):
        raise FileNotFoundError("Project not found. Select the top-level folder containing src/game.")
    return root.resolve()


def atomic_write(path: Path, content: bytes) -> None:
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def install(root: Path, dry_run: bool = False) -> tuple[list[str], Path | None]:
    # Validate every patch before changing a single file.
    changes: dict[Path, tuple[bytes, bytes]] = {}
    for name, patcher in PATCHES.items():
        path = root / "src" / "game" / name
        old = path.read_bytes()
        if old.startswith(b"\xef\xbb\xbf"):
            raise ValueError(f"{name}: UTF-8 BOM not supported safely; no files changed.")
        decoded = old.decode("utf-8")
        original_crlf = "\r\n" in decoded
        normalized = decoded.replace("\r\n", "\n")
        patched = patcher(normalized)
        updated = (patched.replace("\n", "\r\n") if original_crlf else patched).encode("utf-8")
        if updated != old:
            changes[path] = (old, updated)
    if not changes or dry_run:
        return [p.name for p in changes], None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = root / ".aster_backups" / stamp
    backup.mkdir(parents=True, exist_ok=False)
    for path, (old, _) in changes.items():
        target = backup / path.name
        target.write_bytes(old)
    written = []
    try:
        for path, (_, updated) in changes.items():
            atomic_write(path, updated)
            written.append(path)
    except Exception:
        for path in reversed(written):
            atomic_write(path, changes[path][0])
        raise
    return [p.name for p in changes], backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", help="Fight Royale project root")
    parser.add_argument("--dry-run", action="store_true", help="Check compatibility without writing files")
    args = parser.parse_args()
    try:
        root = find_project(args.project)
        changed, backup = install(root, args.dry_run)
    except Exception as exc:
        print("\nERROR:", exc)
        print("Installation stopped. If files were changed, they were restored automatically.")
        return 1
    print("\nFight Royale: Aster tank rebalance (Judgment UNCHANGED)")
    print("Project:", root)
    if not changed:
        print("Already installed. No files changed.")
    elif args.dry_run:
        print("Compatible (dry run only). Would update:", ", ".join(changed))
    else:
        print("Updated:", ", ".join(changed))
        print("Backups:", backup)
        print("Aster: 2800 HP (+12%), 125 guard (+25%), -15% outgoing damage, -10% incoming direct damage.")
        print("Judgment: existing behavior, duration, and skill code left unchanged.")
        print("Other knights and characters are unchanged. Restart the dev server to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
