#!/usr/bin/env python3
"""Install Nesa's heart hammer character, icons, and optimized VRM.

Keep this script beside Install_Nesa_Heart_Hammer_Fixed.py and nesa_optimized.vrm.
Run:
  python Install_Nesa_Complete.py
or
  python Install_Nesa_Complete.py "C:\\path\\to\\Fight-Royale\\web"
Use --check to validate the game patch and assets without modifying the project.

The fixed code/icons installer creates backups for game changes. This wrapper also
backs up any existing nesa.vrm before replacing it. No pip packages required.
"""
from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime

HERE = Path(__file__).resolve().parent
MODEL_SRC = HERE / "nesa_optimized.vrm"
CHILD = HERE / "Install_Nesa_Heart_Hammer_Fixed.py"


def sha256(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def get_root(spec: str | None):
    if spec:
        root = Path(spec).expanduser().resolve()
        candidates = (root, root / "web")
    else:
        root = Path.cwd()
        candidates = (root, root / "web")
        if not any((x / "src/game/roster.ts").is_file() for x in candidates):
            try:
                import tkinter as tk
                from tkinter import filedialog
                app = tk.Tk()
                app.withdraw()
                folder = filedialog.askdirectory(title="Select Fight Royale folder")
                app.destroy()
                if folder:
                    root = Path(folder).resolve()
                    candidates = (root, root / "web")
            except Exception:
                pass
    for c in candidates:
        if (c / "src/game/roster.ts").is_file() and (c / "src/game/model.ts").is_file():
            return c
    raise RuntimeError("Could not find the Fight Royale web project (src/game/roster.ts).")


def main():
    parser = argparse.ArgumentParser(description="Install Nesa complete heart-hammer character plus optimized VRM")
    parser.add_argument("project", nargs="?", help="Path to Fight Royale repo root or web folder")
    parser.add_argument("--check", action="store_true", help="Validate without installing")
    args = parser.parse_args()
    for asset in (MODEL_SRC, CHILD):
        if not asset.is_file():
            raise RuntimeError(f"Missing {asset.name}. Keep all three package files together.")
    root = get_root(args.project)
    print(f"Fight Royale project: {root}")
    print(f"Optimized Nesa VRM: {MODEL_SRC.stat().st_size/1024/1024:.2f} MiB")
    cmd = [sys.executable, str(CHILD), str(root)]
    if args.check:
        cmd.append("--check")
    subprocess.run(cmd, check=True)
    dest = root / "public/models/nesa.vrm"
    if dest.is_file() and sha256(dest) == sha256(MODEL_SRC):
        print("[OK] Nesa model is already up to date")
        return
    if args.check:
        print(f"[CHECK] Would install optimized VRM into {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        bdir = root / ".nesa_installer_backups" / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_previous_vrm")
        bdir.mkdir(parents=True)
        backup = bdir / "nesa.vrm"
        shutil.copy2(dest, backup)
        print(f"[BACKUP] Previous VRM saved to {backup}")
    tmp = dest.with_suffix(".vrm.tmp")
    try:
        shutil.copy2(MODEL_SRC, tmp)
        tmp.replace(dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    print("[OK] Optimized Nesa model installed in public/models/nesa.vrm")
    print("[DONE] Nesa code, heart icons and model installed. Next: npx tsc --noEmit -p .")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
