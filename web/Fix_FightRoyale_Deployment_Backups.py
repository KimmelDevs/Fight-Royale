#!/usr/bin/env python3
"""Fix Fight Royale / Next.js deployment type errors caused by installer backups.

Run from the web folder:
    python Fix_FightRoyale_Deployment_Backups.py

This utility:
  1. Moves root-level installer backup directories *outside* the Git repository.
     No backups are deleted.
  2. Untracks those directories from Git (if Git is available).
  3. Ignores future installer backup directories in .gitignore.
  4. Excludes those directories from TypeScript's broad **/*.ts include pattern.

Does NOT edit any combat code under src/ and does not make a Git commit.
If you have other staged Git changes, those are left untouched.
Requires Python 3.9+, no third-party packages.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

IGNORE_BLOCK = """# Fight Royale generated installer backups (never deploy)
backup_*/
backup-*/
*_backups/
.*_backups/
"""
EXCLUDE_PATTERNS = [
    "backup_*", "**/backup_*", "backup-*", "**/backup-*",
    "*_backups", "**/*_backups", ".*_backups", "**/.*_backups",
]


def backup_name(name: str) -> bool:
    low = name.lower()
    return low.startswith(("backup_", "backup-")) or low.endswith("_backups") or low.endswith("-backups")


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(["git", *args], cwd=str(root), text=True,
                              capture_output=True, check=False, encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None


def find_web(cwd: Path) -> Path:
    for folder in [cwd, cwd / "web", cwd.parent / "web", cwd.parent]:
        if (folder / "tsconfig.json").is_file() and (folder / "src" / "game").is_dir():
            return folder.resolve()
    raise RuntimeError("Cannot locate Fight Royale web folder. Run the script inside your web folder.")


def git_root(web: Path) -> Path | None:
    r = run_git(web, "rev-parse", "--show-toplevel")
    if r and r.returncode == 0:
        result = Path(r.stdout.strip()).resolve()
        if result.is_dir() and (result == web or result in web.parents):
            return result
    return None


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(1, 10000):
        candidate = path.with_name(f"{path.name}_{i}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"No free destination name near {path}")


def update_tsconfig(web: Path) -> bool:
    path = web / "tsconfig.json"
    source = path.read_text(encoding="utf-8-sig")
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError:
        print("[WARN] tsconfig.json contains comments/non-JSON syntax. Not rewriting it; backups are still moved.")
        return False
    previous = parsed.get("exclude", [])
    if not isinstance(previous, list):
        print("[WARN] Unexpected tsconfig exclude setting; leaving tsconfig unchanged.")
        return False
    added = [part for part in EXCLUDE_PATTERNS if part not in previous]
    if not added:
        print("[OK] tsconfig.json already excludes installer backups.")
        return False

    pattern = re.compile(r'(\"exclude\"\s*:\s*)\[([^\]]*)\]')
    match = pattern.search(source)
    if match:
        entries = json.dumps(previous + added, ensure_ascii=False)
        # Only replace the exclude array, preserving the rest of the file's style.
        updated = source[:match.start()] + match.group(1) + entries + source[match.end():]
    else:
        parsed["exclude"] = previous + added
        updated = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"[OK] Updated tsconfig.json with {len(added)} backup exclusions.")
    return True


def update_gitignore(web: Path) -> bool:
    path = web / ".gitignore"
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    needed = [p for p in IGNORE_BLOCK.splitlines() if p and not p.startswith("#") and p not in current.splitlines()]
    if not needed:
        print("[OK] .gitignore already excludes installer backups.")
        return False
    block = ("\n" if current and not current.endswith("\n") else "") + "\n" + IGNORE_BLOCK
    path.write_text(current + block, encoding="utf-8", newline="\n")
    print("[OK] Updated .gitignore to prevent future backup folders being committed.")
    return True


def main() -> int:
    web = find_web(Path.cwd().resolve())
    repo = git_root(web)
    # This folder is outside the repo, even when the git root is FightRoyale's parent.
    base = (repo.parent if repo else web.parent) / "FightRoyale_Installer_Backups"
    print("[PROJECT]", web)
    print("[GIT ROOT]", repo if repo else "not found")
    print("[BACKUP DESTINATION]", base)
    folders = sorted((p for p in web.iterdir() if p.is_dir() and backup_name(p.name)), key=lambda p: p.name)
    if not folders:
        print("[INFO] No installer backup folders found directly under web.")
    moves = []
    failures = []
    for original in folders:
        target = unique_destination(base / web.name / original.name)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(original), str(target))
            print(f"[MOVED] {original.name}  ->  {target}")
            moves.append((original, target))
            if repo:
                rel = original.relative_to(repo).as_posix()
                # Removing from the index only: the backup itself is preserved outside the repo.
                tracked = run_git(repo, "ls-files", "--", rel)
                if tracked and tracked.returncode == 0 and tracked.stdout.strip():
                    removed = run_git(repo, "rm", "-r", "-f", "--cached", "--", rel)
                    if removed and removed.returncode == 0:
                        print(f"[GIT] Removed tracked backup from the Git index: {rel}")
                    else:
                        print(f"[WARN] Could not untrack {rel}: {removed.stderr.strip() if removed else 'git unavailable'}")
        except Exception as exc:
            print(f"[ERROR] Could not move {original}: {exc}")
            failures.append(original)

    # Exclusion also protects future backups even if the user reruns an old installer.
    update_tsconfig(web)
    update_gitignore(web)
    print()
    print(f"[RESULT] {len(moves)} backup folder(s) moved. {len(failures)} error(s). Source code unchanged.")
    print("[NEXT] Run: npx tsc --noEmit -p .")
    print("[NEXT] Run: npm run build")
    print("[NEXT] Commit and push the removed backup folders, tsconfig.json, and .gitignore changes.")
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("[ERROR]", exc)
        sys.exit(1)
