#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale - Compact Impact & Clash effects (50%-size follow-up patch).

Requires the previously installed Impact & Clash Overhaul. Changes visuals only:
- Halves the on-screen size of both clash bursts and the overhaul's impact bursts.
- Reduces the extra overhaul spark count and travel distance by about half.
- Halves the intensity of overhaul screen flashes and new camera punch.
Preserves hitstop durations, sounds, stats, skills, damage and passive triggers.

Usage:
  python Install_Compact_Impact_Effects.py
  python Install_Compact_Impact_Effects.py "C:\\path\\to\\Fight-Royale"
  python Install_Compact_Impact_Effects.py "C:\\path\\to\\Fight-Royale" --dry-run

No Python packages required. Original files are backed up automatically.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile

MARKER = 'FIGHT_ROYALE_COMPACT_IMPACT_EFFECTS_V2'
PRIOR_MARKER = 'FIGHT_ROYALE_IMPACT_CLASH_OVERHAUL_V1'
FILES = ('src/game/fx.ts', 'src/game/game.ts')


def replace_exact(text: str, old: str, new: str, context: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{context}: expected exactly one matching code block; found {n}. '
                           'Your game may use a different script version. No changes were made.')
    return text.replace(old, new, 1)


def replace_in_section(text: str, begin: str, end: str,
                       old: str, new: str, context: str) -> str:
    start = text.find(begin)
    if start < 0 or text.find(begin, start + 1) >= 0:
        raise RuntimeError(f'{context}: could not identify method safely. No changes were made.')
    finish = text.find(end, start + len(begin))
    if finish < 0:
        raise RuntimeError(f'{context}: could not identify method end safely. No changes were made.')
    before, section, after = text[:start], text[start:finish], text[finish:]
    return before + replace_exact(section, old, new, context) + after


def patch_fx(text: str) -> str:
    if MARKER in text:
        return text
    if PRIOR_MARKER not in text:
        raise RuntimeError('fx.ts: install the original Impact & Clash Overhaul first.')

    # The earlier clash visuals were already present before the overhaul; shrink
    # these too, so doubled-up clashes do not look enormous.
    text = replace_in_section(
        text, '  clashBurst(pos: THREE.Vector3', '  /** IMPACT_OVERHAUL_V1:',
        '    root.position.copy(pos);',
        '    root.position.copy(pos);\n'
        '    root.scale.setScalar(0.5); // COMPACT_IMPACT_V2: half-size clash graphics',
        'fx.ts clashBurst scale')

    # Scale the whole impact graphic (rings, spokes, central flash) uniformly.
    text = replace_in_section(
        text, '  impactBurst(pos: THREE.Vector3', '  /** Real-time (not hitstop-scaled)',
        '    group.position.copy(pos);',
        '    group.position.copy(pos);\n'
        '    group.scale.setScalar(0.5); // COMPACT_IMPACT_V2: half-size impact graphics',
        'fx.ts impactBurst scale')

    # Also limit the spread of the extra particles, otherwise they still reach
    # the original large area even though the rings and streaks are smaller.
    text = replace_in_section(
        text, '  impactBurst(pos: THREE.Vector3', '  /** Real-time (not hitstop-scaled)',
        '      this.sparks(pos, "#ffffff", isClash || kind === "finish" ? 14 : 8, 8 * weight);\n'
        '      this.sparks(pos, color, isClash || kind === "finish" ? 14 : 9, 6 * weight);',
        '      this.sparks(pos, "#ffffff", isClash || kind === "finish" ? 7 : 4, 4 * weight);\n'
        '      this.sparks(pos, color, isClash || kind === "finish" ? 7 : 5, 3 * weight);',
        'fx.ts extra impact spark spread')

    text = replace_in_section(
        text, '  screenImpact(kind: string', '  flash(pos: THREE.Vector3',
        '    const strength = Math.max(0.2, Math.min(power, 1.2));',
        '    const strength = 0.5 * Math.max(0.2, Math.min(power, 1.2));'
        ' // COMPACT_IMPACT_V2',
        'fx.ts overlay flash strength')
    return '// ' + MARKER + '\n' + text


def patch_game(text: str) -> str:
    if MARKER in text:
        return text
    if PRIOR_MARKER not in text:
        raise RuntimeError('game.ts: install the original Impact & Clash Overhaul first.')

    # Leave the existing camera tracking and base screen shake alone. The new
    # overhaul-specific camera punch is the part being made less aggressive.
    text = replace_exact(
        text,
        '      cam.position.lerp(look, Math.min(0.095, this.impactCameraPunch * 0.065));',
        '      cam.position.lerp(look, Math.min(0.0475, this.impactCameraPunch * 0.0325));'
        ' // COMPACT_IMPACT_V2: half-strength camera punch',
        'game.ts impact camera punch')
    return '// ' + MARKER + '\n' + text


PATCHES = {'src/game/fx.ts': patch_fx, 'src/game/game.ts': patch_game}


def find_project(path: str | None) -> Path:
    candidates = ([Path(path).expanduser()] if path
                  else [Path.cwd(), Path(__file__).resolve().parent])
    for candidate in candidates:
        if all((candidate / file).is_file() for file in FILES):
            return candidate.resolve()
    if path:
        raise RuntimeError('Select the Fight Royale root folder containing src/game/game.ts and fx.ts.')
    folder = ''
    try:
        from tkinter import Tk, filedialog
        ui = Tk()
        ui.withdraw()
        ui.attributes('-topmost', True)
        folder = filedialog.askdirectory(title='Choose Fight Royale project folder')
        ui.destroy()
    except Exception:
        pass
    if not folder:
        try:
            folder = input('Fight Royale project folder (full path): ').strip().strip('"')
        except (EOFError, OSError):
            pass
    if not folder:
        raise RuntimeError('No project folder selected.')
    result = Path(folder).expanduser().resolve()
    if not all((result / file).is_file() for file in FILES):
        raise RuntimeError('Selected folder is missing src/game/game.ts or src/game/fx.ts.')
    return result


def atomic_write(path: Path, data: bytes) -> None:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.impact_compact_', dir=path.parent,
                                         delete=False) as temp:
            tmp_path = Path(temp.name)
            temp.write(data)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def install(root: Path, dry_run: bool = False) -> tuple[list[str], Path | None]:
    changes: dict[Path, tuple[bytes, bytes]] = {}
    # Preflight every target BEFORE writing any file.
    for relative in FILES:
        path = root / relative
        original = path.read_bytes()
        bom = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
        decoded = original[len(bom):].decode('utf-8')
        crlf = decoded.count('\r\n') > decoded.count('\n') / 2
        normalized = decoded.replace('\r\n', '\n').replace('\r', '\n')
        revised = PATCHES[relative](normalized)
        output = bom + (revised.replace('\n', '\r\n') if crlf else revised).encode('utf-8')
        if original != output:
            changes[path] = original, output

    names = [str(file.relative_to(root)) for file in changes]
    if dry_run or not changes:
        return names, None

    backup = root / '.clash_backups' / (dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_compact_effects')
    for path, (original, _output) in changes.items():
        destination = backup / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(original)

    written = []
    try:
        for path, (_original, output) in changes.items():
            atomic_write(path, output)
            written.append(path)
    except Exception:
        for path in reversed(written):
            atomic_write(path, changes[path][0])
        raise
    return names, backup


def main() -> int:
    parser = argparse.ArgumentParser(description='Reduce Fight Royale clash/impact VFX to 50%')
    parser.add_argument('project', nargs='?', help='Fight Royale root directory')
    parser.add_argument('--dry-run', action='store_true', help='check compatibility without changing files')
    args = parser.parse_args()
    print('\n=== Fight Royale - Compact Impact & Clash Effects (50%) ===\n')
    try:
        project = find_project(args.project)
        modified, backup = install(project, args.dry_run)
    except Exception as error:
        print('ERROR:', error)
        return 1
    print('Project:', project)
    if args.dry_run:
        print('Compatible; would update: ' + ', '.join(modified) if modified else 'Already installed.')
    elif not modified:
        print('Already installed - no changes needed.')
    else:
        print('Updated:', ', '.join(modified))
        print('Backups:', backup)
        print('Impact and clash graphics reduced to 50% of prior size.')
        print('Combat balance, skills, hitstop and Clash Momentum logic are unchanged.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
