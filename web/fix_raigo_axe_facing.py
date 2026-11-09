#!/usr/bin/env python3
"""Fight Royale — Raigo axe cutting-edge direction fix.

Place in the fight-royale/web folder:
    python fix_raigo_axe_facing.py --dry-run
    python fix_raigo_axe_facing.py
    npx tsc --noEmit -p .

Also accepts --root PATH. Python standard library only.

The blade was drawn along +X in the axe head's own coordinates, whereas the
fighter attacks along local +Z. Rotate the head around the UP (shaft) axis,
not the fighter root or the free-body physics group. This works for the player
and CPU/enemy alike, without special-casing opponent orientation. The edge
FX/hit-tip and chain butt attachment are head children, and follow the turn.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

MARKER = "RAIGO_AXE_FACE_FORWARD_V1"
MODEL_REL = Path("src/game/model.ts")


class PatchError(Exception):
    pass


def preflight(source: str) -> tuple[str, bool]:
    if MARKER in source:
        raise PatchError("Already installed: Raigo axe facing fix was found. No changes made.")
    if "RAIGO_IRON_BASTION_V6" not in source or "RAIGO_V6_CHAIN_LENGTH" not in source:
        raise PatchError("Expected Raigo V6 weapon not found in model.ts. No changes made.")
    if source.count("  private buildRaigoAxeFlail() {") != 1:
        raise PatchError("Missing or duplicated Raigo weapon build method.")
    # Anchor is unique to Raigo. No edits to other weapons or opponent facing.
    old = "    const head=pivot(axe);\n    head.scale.setScalar(.75);"
    if source.count(old) != 1:
        raise PatchError(f"Raigo axe head anchor not unique (found {source.count(old)}).")
    new = ("    const head=pivot(axe);\n"
           "    head.scale.setScalar(.75);\n"
           "    // RAIGO_AXE_FACE_FORWARD_V1: cutting edge is drawn along +X; fighter forward is +Z.\n"
           "    // Turn HEAD only about the short handle's Y axis: no handedness or enemy-side flip.\n"
           "    // Tip, axe butt/chain anchor, and sharp edge outline rotate with this head.\n"
           "    head.rotation.y=-PI/2;")
    result = source.replace(old, new, 1)

    # The short-handle grip was introduced in the later Raigo/Marina patch.
    # Rotate its point with the head to keep the right hand precisely aligned
    # with the handle, without altering the full-chain length or tether physics.
    old_grip = "    this.raigoAxeGrip=pivot(axe,[-.01125,-.375,0]);"
    has_grip = "RAIGO_AXE_GRIP_FIX" in source
    if has_grip:
        if result.count(old_grip) != 1:
            raise PatchError("Raigo axe grip variant found but its grip pivot anchor changed; refusing an unsafe partial edit.")
        result = result.replace(old_grip,
              "    this.raigoAxeGrip=pivot(axe,[0,-.375,-.01125]); // " + MARKER + ": grip follows rotated handle", 1)

    # Preserve the structural requirements of the chain weapon.
    for guard in ("this.raigoAxeAttach=", "this.bladeTip=pivot(head", "this.raigoAxeTip=this.bladeTip", "this.raigoFlailTip=ball"):
        if guard not in result:
            raise PatchError(f"Raigo model no longer has required anchor: {guard}")
    return result, has_grip


def install(root: Path, dry_run: bool) -> None:
    path = root / MODEL_REL
    if not path.is_file():
        raise PatchError(f"Could not find {path}. Put this installer in the web folder or use --root.")
    original = path.read_bytes()
    bom = b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b""
    try:
        source = original.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise PatchError(f"model.ts is not UTF-8: {exc}") from exc
    updated, grip_version = preflight(source)
    newline = "\r\n" if b"\r\n" in original else "\n"
    target_bytes = bom + updated.replace("\n", newline).encode("utf-8")
    print("RAIGO AXE FACE FIX | target:", root)
    print("Effect: axe cutting edge faces forward (+Z) rather than toward the body.")
    print("Preserves: full chain, free-end physics, reach, stats, other characters.")
    if grip_version:
        print("Detected: short axe handle; its VRM hand-grip point will stay aligned.")
    if dry_run:
        print("DRY RUN PASS — all required anchors found; no files changed.")
        return

    # Store backups with a .bak suffix rather than a .ts suffix so even a broad
    # tsconfig include pattern cannot accidentally compile them.
    backup_dir = root / ".raigo-backups" / ("axe-face-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / "model.ts.bak"
    shutil.copy2(path, backup)

    stage: Path | None = None
    committed = False
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".raigo-face-", suffix=".tmp", delete=False) as tmp:
            tmp.write(target_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            stage = Path(tmp.name)
        # Don't overwrite an independently changed version after our preflight.
        if path.read_bytes() != original:
            raise PatchError("model.ts changed after preflight; nothing overwritten.")
        os.replace(stage, path)
        committed = True
        print("SUCCESS — Raigo axe now points forward for both player and enemy.")
        print("Backup:", backup)
        print("Next: npx tsc --noEmit -p .  &&  npm run dev")
    except Exception as exc:
        if committed:
            try:
                shutil.copy2(backup, path)
            except OSError as rollback_exc:
                raise PatchError(f"Patch failed and rollback failed! Use backup {backup}: {rollback_exc}") from exc
        raise
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Fight Royale web folder; default current working directory")
    args = parser.parse_args()
    try:
        install(args.root.expanduser().resolve(), args.dry_run)
        return 0
    except (PatchError, OSError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
