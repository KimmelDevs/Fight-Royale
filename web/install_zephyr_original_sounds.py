#!/usr/bin/env python3
"""Zephyr — original-filename SFX integration for Fight Royale.

Run from the project's web/ directory, or place this script in web/ and run it.

    python install_zephyr_original_sounds.py --dry-run
    python install_zephyr_original_sounds.py

Compatible with the 2026-11-08 source snapshot uploaded in this conversation.
Uses the original MP3 filenames in public/sfx/ (no audio renames or copies).
If you kept the category directories under sfx/, those paths are supported too.

Changes only:
  src/game/sound.ts   — playback length and preload registration
  src/game/game.ts    — Zephyr's per-action combat sounds
  src/game/preview.ts — timed selection choreography sounds

Preflight checks the source anchors in memory. Changes are staged before being
written; originals are backed up and a write failure triggers rollback.
"""

from __future__ import annotations
import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile

TAG = "ZEPHYR_ORIGINAL_SOUND_PACK_V1_20261109"
# (folder in original sound library, unmodified filename)
SOUND_FILES = {
    "spin": ("transitions", "spacey_swish_spin.mp3"),
    "strike": ("fight", "fast_whip_strike.mp3"),
    "catch": ("bunker", "gear_fast_lock_tap.mp3"),
    "throw": ("transitions", "throw_hard_wind_woosh.mp3"),
    "counter": ("fight", "metal_impact_whip.mp3"),
    "cyclone": ("transitions", "long_sweeping_air_swoosh.mp3"),
    "finisher": ("fight", "cinematic_whoosh_deep_impact.mp3"),
}

class PatchError(RuntimeError):
    pass

def replace_once(source: str, old: str, new: str, file: str) -> str:
    amount = source.count(old)
    if amount != 1:
        raise PatchError(f"{file}: expected 1 match but found {amount}: {old[:120]!r}")
    return source.replace(old, new, 1)

def locate_web() -> Path:
    options = (Path.cwd(), Path(__file__).resolve().parent,
               Path.cwd() / "web", Path(__file__).resolve().parent / "web")
    for base in options:
        if (base / "src/game/game.ts").is_file() and (base / "src/game/sound.ts").is_file():
            return base.resolve()
    raise PatchError("Cannot find web/src/game/game.ts. Place this installer inside your Fight Royale web folder and run it there.")

def sound_names(web: Path) -> tuple[dict[str,str], list[str]]:
    ids = {}
    missing = []
    for key, (folder, filename) in SOUND_FILES.items():
        if (web / "public/sfx" / filename).is_file():
            ids[key] = filename[:-4]
        elif (web / "public/sfx" / folder / filename).is_file():
            ids[key] = f"{folder}/{filename[:-4]}"
        else:
            # Default to files copied directly into the sfx root.
            ids[key] = filename[:-4]
            missing.append(filename)
    return ids, missing

def patch_game(src: str, sound: dict[str,str]) -> str:
    def sid(key: str) -> str: return '"' + sound[key] + '"'
    branch = f'''    // {TAG}: Zephyr uses original MP3 names, not renamed aliases.
    if (f.kit === "tristaff") {{
      if (a.style === "zephyr_reversal") this.snd({sid("catch")}, 0.40);
      else if (a.style === "zephyr_cyclone" || a.style === "zephyr_ninefold") this.snd({sid("spin")}, 0.41);
      else if (a.style === "zephyr_serpent" || a.style === "zephyr_twin_fang") this.snd({sid("cyclone")}, 0.38);
      else if (a.heavy || a.id === "heavy") this.snd({sid("throw")}, 0.55);
      else this.snd({sid("strike")}, 0.53);
      return;
    }}
'''
    src = replace_once(src, '  private swingSound(f: Fighter, a: Attack) {\n',
        '  private swingSound(f: Fighter, a: Attack) {\n'+branch, 'game.ts (swingSound)')
    impact = f'''    // {TAG}: real contact only, leaving normal blocks/parries/clashes intact.
    if (attacker instanceof Fighter && attacker.kit === "tristaff") {{
      const finalBeat = /_(?:5|9)$/.test(a.id) &&
        (a.style === "zephyr_cyclone" || a.style === "zephyr_ninefold");
      this.snd(a.heavy || finalBeat ? {sid("finisher")} : {sid("counter")},
        a.heavy || finalBeat ? 0.64 : 0.53);
      if (crit) this.snd("crit", 0.40);
      return;
    }}
'''
    src = replace_once(src, '  private hitSound(attacker: Entity | null, a: Attack, crit: boolean) {\n',
        '  private hitSound(attacker: Entity | null, a: Attack, crit: boolean) {\n'+impact, 'game.ts (hitSound)')
    # One staff-grip sound for a real F mode switch, not each damaging pulse.
    anchor = '  private zephyrSwitchFlourish(f:Fighter) {\n    if(f.kit!=="tristaff"||f.puppet)return;\n'
    src = replace_once(src, anchor, anchor + f'    this.snd({sid("catch")}, 0.38); // {TAG}\n', 'game.ts (switch)')
    # Per-combo attack sounds fired at genuine active beat timings, not at skill button press.
    anchor = '''      if (last) this.fxp("ring", tip, "#8cf2d3", 0.9, 0.19, 0.72);
      this.melee(f, hit);
'''
    added = f'''      if (last) this.fxp("ring", tip, "#8cf2d3", 0.9, 0.19, 0.72);
      // {TAG}: sound follows each REAL scheduled hit, not merely a long animation.
      if (i > 0) this.snd(last ? {sid("finisher")} :
        i % 3 === 0 ? {sid("spin")} : {sid("strike")}, last ? 0.52 : 0.31);
      this.melee(f, hit);
'''
    src = replace_once(src, anchor, added, 'game.ts (combo beats)')
    # Cue the precision catch of a successful defensive parry/counter.
    anchor = '''        if (df.kit === "tristaff") {
          df.earnDragonRhythm();
'''
    if src.count(anchor) != 2:
        raise PatchError(f'game.ts (defense): expected 2 parry/counter anchors, found {src.count(anchor)}')
    first = src.index(anchor)
    second = src.index(anchor, first+len(anchor))
    src = src[:second] + src[second:].replace(anchor, anchor + f'          this.snd({sid("counter")}, 0.51); // {TAG} successful counter\n',1)
    src = src[:first] + src[first:].replace(anchor, anchor + f'          this.snd({sid("catch")}, 0.42); // {TAG} timed parry\n',1)
    return src

def patch_preview(src: str, sound: dict[str,str]) -> str:
    def sid(key: str) -> str: return '"' + sound[key] + '"'
    src = replace_once(src, 'import { FighterModel } from "./model";\n',
        'import { FighterModel } from "./model";\nimport { Sound } from "./sound"; // '+TAG+'\n', 'preview.ts (import)')
    preload = '    if (look.kit === "tristaff") Sound.preload([' + ', '.join('"'+sound[k]+'"' for k in sound) + ']);\n'
    src = replace_once(src, '    this.lookName = look.name;\n',
        '    this.lookName = look.name;\n' + preload, 'preview.ts (preload)')
    # Only plays when the current preview is Zephyr; cycles smoothly across the 9-second loop.
    insertion = f'''  // {TAG}: original-filename sound cues for the 9-second preview choreography.
  private zephyrShowSound(previous: number, current: number) {{
    if (this.mode !== "select" || this.lookName.toLowerCase() !== "zephyr" ||
        document.visibilityState === "hidden" || current - previous > 0.20) return;
    const cues: ReadonlyArray<readonly [number, string, number]> = [
      [0.45, {sid("spin")}, 0.31],
      [1.16, {sid("strike")}, 0.27],
      [2.60, {sid("spin")}, 0.30],
      [3.74, {sid("cyclone")}, 0.28],
      [4.54, {sid("throw")}, 0.42],
      [6.25, {sid("catch")}, 0.43],
      [7.08, {sid("spin")}, 0.28],
      [7.62, {sid("finisher")}, 0.43],
    ];
    const start = Math.floor(previous / 9);
    const end = Math.floor(current / 9);
    for (let cycle = start; cycle <= end; cycle++) {{
      for (const [moment, name, volume] of cues) {{
        const event = cycle * 9 + moment;
        if (previous < event && current >= event) Sound.play(name, volume, 0.02);
      }}
    }}
  }}

'''
    src = replace_once(src, '  private tick(dt: number) {\n', insertion+'  private tick(dt: number) {\n', 'preview.ts (method)')
    src = replace_once(src, '    if (this.model) {\n      this.poseT += dt;\n',
        '    if (this.model) {\n      const previousPresentationTime = this.poseT;\n      this.poseT += dt;\n      this.zephyrShowSound(previousPresentationTime, this.poseT);\n', 'preview.ts (tick)')
    return src

def patch_sound(src: str, sound: dict[str,str]) -> str:
    durations = {"spin": 0.85, "strike": 0.45, "catch": 0.40,
                 "throw": 0.90, "counter": 0.65, "cyclone": 1.15, "finisher": 1.55}
    sound_len = '  // '+TAG+': short, responsive character-specific effects.\n' + ''.join(
        f'  "{sound[k]}": {durations[k]},\n' for k in durations)
    src = replace_once(src, 'const MAX_LEN: Record<string, number> = {\n',
        'const MAX_LEN: Record<string, number> = {\n'+sound_len, 'sound.ts (max lengths)')
    old = '  "ready", "fight", "victory", "defeat"];'
    new = ('  "ready", "fight", "victory", "defeat",\n'
        + ''.join(f'  "{sound[k]}", // {TAG}: {k}\n' for k in sound) + ']')
    # Python continuity: keep the original semicolon in generated TS.
    new += ';'
    src = replace_once(src, old, new, 'sound.ts (match preload)')
    return src

def atomic_write(path: Path, body: str) -> None:
    fd, temp = tempfile.mkstemp(prefix='.'+path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.remove(temp)

def main() -> int:
    ap = argparse.ArgumentParser(description="Update Zephyr sounds, keeping the original MP3 filenames.")
    ap.add_argument('--dry-run', action='store_true', help='Preflight without changing anything')
    ap.add_argument('--strict-audio', action='store_true', help='Fail if any of the seven MP3s is missing')
    args = ap.parse_args()
    try:
        web = locate_web()
        ids, missing = sound_names(web)
        print(f'Zephyr original sound integration | web: {web}')
        for key, sound_id in ids.items():
            exists = key not in [k for k, (cat, name) in SOUND_FILES.items() if name in missing]
            print(f'  {"OK" if exists else "MISSING"} {key:8s} /sfx/{sound_id}.mp3')
        if missing and args.strict_audio:
            raise PatchError('Missing sound files: '+', '.join(missing))
        targets = {
            web/'src/game/game.ts': patch_game,
            web/'src/game/preview.ts': patch_preview,
            web/'src/game/sound.ts': patch_sound,
        }
        patched, original = {}, {}
        for path, patcher in targets.items():
            old = path.read_text(encoding='utf-8')
            if TAG in old:
                raise PatchError(f'{path.relative_to(web)} already contains {TAG}; refusing to install twice.')
            patched[path] = patcher(old, ids)
            original[path] = old
        print('Preflight PASS: 3 source files match the expected Zephyr sound hooks.')
        if missing:
            print('WARNING: MP3 files were not found at those paths. Add the original files to public/sfx/ before playing.')
        if args.dry_run:
            print('Dry run: no files changed.')
            return 0
        timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
        backups = {}
        try:
            for path, old in original.items():
                backup = path.with_name(path.name+f'.before_zephyr_original_sounds_{timestamp}.bak')
                if backup.exists():
                    raise PatchError(f'Backup path exists: {backup}')
                # Backup must be fully written BEFORE patching source.
                with open(backup, 'x', encoding='utf-8', newline='') as handle:
                    handle.write(old)
                backups[path] = backup
            for path, content in patched.items():
                atomic_write(path, content)
        except Exception:
            print('Write failed: restoring originals from memory...')
            for path, old in original.items():
                atomic_write(path, old)
            raise
        print('Installed. 3 files changed; backups created:')
        for backup in backups.values(): print('  ', backup.relative_to(web))
        print('Sound filenames were not renamed or moved.')
        print('Next: npx tsc --noEmit -p . && npm run dev')
        return 0
    except (PatchError, OSError, UnicodeError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
