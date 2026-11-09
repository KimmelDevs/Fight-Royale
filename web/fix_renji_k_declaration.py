#!/usr/bin/env python3
"""Fight Royale / Renji V2 — fix TS2448: K used before declaration.

Moves the EXISTING knee-bend helper ahead of RENJI_TONFA in src/game/kits.ts.
No gameplay logic, balance, or animation values are changed.

Usage (from the Fight Royale web/ folder):
    python fix_renji_k_declaration.py --dry-run
    python fix_renji_k_declaration.py
    npx tsc --noEmit -p .

Backups use .txt extension so tsconfig cannot accidentally compile them.
"""

from __future__ import annotations

import argparse
import datetime
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


RENJI_ANCHOR = re.compile(r"(?m)^const RENJI_TONFA: Record<string, Pose> = \{")
# Move the single original declaration (and its comment), rather than defining a
# competing K or stripping knee bends from any of Renji's 30 poses.
K_HELPER = re.compile(
    r"(?m)^[ \t]*/\*\* Adds knee bend to a pose\. \*/[ \t]*\r?\n"
    r"[ \t]*const K[ \t]*=[ \t]*\(p: Pose, l: number, r: number\): Pose"
    r"[ \t]*=>[ \t]*\(\{[ \t]*\.\.\.p,[ \t]*knee:[ \t]*\[l, r\][ \t]*\}\);[ \t]*\r?\n"
)
K_DECL = re.compile(r"(?m)^[ \t]*const K[ \t]*=")
POSE_DECL = re.compile(r"(?m)^const P[ \t]*=")


def prepare(before: str) -> tuple[str, bool]:
    renji = list(RENJI_ANCHOR.finditer(before))
    helpers = list(K_HELPER.finditer(before))
    k_decls = list(K_DECL.finditer(before))
    pose = list(POSE_DECL.finditer(before))

    if len(renji) != 1:
        raise RuntimeError(f"Expected exactly one Renji pose table; found {len(renji)}. No files changed.")
    if len(k_decls) != 1 or len(helpers) != 1:
        raise RuntimeError("Couldn't safely identify exactly one original K knee helper. No files changed.")
    if len(pose) != 1 or pose[0].start() >= renji[0].start():
        raise RuntimeError("Pose helper P is not defined before Renji poses. Refusing an unsafe change.")

    if helpers[0].start() < renji[0].start():
        return before, False  # Already fixed; intentionally idempotent.

    chunk = helpers[0].group(0)
    without = before[:helpers[0].start()] + before[helpers[0].end():]
    insertion = RENJI_ANCHOR.search(without)
    if not insertion:
        raise RuntimeError("Renji pose table disappeared during preflight.")
    after = without[:insertion.start()] + chunk + without[insertion.start():]
    if not (after.index("const K =") < after.index("const RENJI_TONFA:")):
        raise RuntimeError("Post-patch helper order check failed.")
    if after.count(chunk) != 1:
        raise RuntimeError("Post-patch helper count check failed.")
    return after, True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("web_dir", nargs="?", default=".", help="Fight Royale web folder (default current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Check anchors without editing files")
    args = parser.parse_args()

    root = Path(args.web_dir).expanduser().resolve()
    target = root / "src" / "game" / "kits.ts"
    if not target.is_file():
        raise RuntimeError(f"Source not found: {target}. Run from the web/ directory.")

    raw = target.read_bytes()
    text = raw.decode("utf-8-sig")
    after, changed = prepare(text)
    if not changed:
        print("Renji K declaration is already in the correct position; no changes required.")
        return
    print("Preflight passed: move the existing K helper ahead of RENJI_TONFA in src/game/kits.ts.")
    if args.dry_run:
        print("DRY RUN — no files modified.")
        return

    backup_dir = root / "scripts" / "backups" / (
        "renji_k_fix_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    )
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / "kits.ts.txt"  # .txt is excluded from TypeScript compilation
    shutil.copy2(target, backup)

    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    output = bom + after.encode("utf-8")
    temp_file: Path | None = None
    try:
        handle, name = tempfile.mkstemp(prefix=".renji_k_", suffix=".tmp", dir=target.parent)
        temp_file = Path(name)
        with os.fdopen(handle, "wb") as out:
            out.write(output)
            out.flush()
            os.fsync(out.fileno())
        # No writes occurred until all anchors had passed validation.
        os.replace(temp_file, target)
        temp_file = None
    except BaseException:
        shutil.copy2(backup, target)
        raise
    finally:
        if temp_file is not None:
            temp_file.unlink(missing_ok=True)

    print("Fixed src/game/kits.ts: K is now declared before Renji animation poses.")
    print("Backup:", backup)
    print("Run: npx tsc --noEmit -p .")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("ERROR:", error, file=sys.stderr)
        sys.exit(1)
