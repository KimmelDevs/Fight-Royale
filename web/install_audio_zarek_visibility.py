#!/usr/bin/env python3
"""Fight Royale: independent audio volume controls + white Zarek Clash Counter.

Run from the project web folder (alongside package.json):
    py install_audio_zarek_visibility.py

Safely preflights both target files before modifying either of them, creates backups,
and refuses unexpected source versions instead of silently overwriting changes.
"""
from pathlib import Path
from datetime import datetime
import os
import sys
import re

ROOT = Path(__file__).resolve().parent
SOUND = ROOT / "src/game/sound.ts"
SETTINGS = ROOT / "src/ui/Settings.tsx"
GAMEVIEW = ROOT / "src/ui/GameView.tsx"
ZAREK_MARKER = "ZAREK_WHITE_COUNTER_V1"
MARKER = "// INDEPENDENT_AUDIO_BUSES_V1"


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"Cannot safely patch {label}: expected 1 matching code block, found {n}.")
    return text.replace(old, new, 1)


def patch_sound(s):
    if MARKER in s:
        return s
    s = replace_once(s,
        'interface Volumes { master: number; sfx: number; music: number }',
        '''// INDEPENDENT_AUDIO_BUSES_V1
// Music uses HTMLAudioElement; general SFX and combat feedback use separate Web Audio buses.
interface Volumes { master: number; sfx: number; music: number; combat: number }
const COMBAT_SOUNDS = new Set(["clash", "parry", "block", "guard_break"]);''',
        "sound.ts volume type")
    s = replace_once(s,
        'vol: Volumes = { master: 0.8, sfx: 0.9, music: 0.45 };',
        'vol: Volumes = { master: 0.8, sfx: 0.9, music: 0.45, combat: 1 };',
        "sound.ts default volumes")
    s = replace_once(s,
        '  private out: GainNode | null = null;',
        '  private out: GainNode | null = null;\n  private combatOut: GainNode | null = null;',
        "sound.ts output fields")
    s = replace_once(s,
        '''    this.out.gain.value = this.vol.master * this.vol.sfx;
    this.out.connect(this.ctx.destination);
    return this.ctx;''',
        '''    this.out.gain.value = this.vol.master * this.vol.sfx;
    this.out.connect(this.ctx.destination);
    this.combatOut = this.ctx.createGain();
    this.combatOut.gain.value = this.vol.master * this.vol.combat;
    this.combatOut.connect(this.ctx.destination);
    return this.ctx;''',
        "sound.ts audio graph")
    s = replace_once(s,
        '''    if (!name || this.vol.master * this.vol.sfx <= 0) return;
    const now = performance.now();''',
        '''    const combat = COMBAT_SOUNDS.has(name);
    if (!name || this.vol.master * (combat ? this.vol.combat : this.vol.sfx) <= 0) return;
    const now = performance.now();''',
        "sound.ts effect routing check")
    s = replace_once(s,
        '''      if (!buf || !this.out) return;
      const src = ctx.createBufferSource();''',
        '''      const bus = combat ? this.combatOut : this.out;
      if (!buf || !bus) return;
      const src = ctx.createBufferSource();''',
        "sound.ts output choice")
    s = replace_once(s,
        '      src.connect(g).connect(this.out);',
        '      src.connect(g).connect(bus);',
        "sound.ts connect")
    s = replace_once(s,
        '''    if (this.out) this.out.gain.value = this.vol.master * this.vol.sfx;
    this.fade();''',
        '''    if (this.out) this.out.gain.value = this.vol.master * this.vol.sfx;
    if (this.combatOut) this.combatOut.gain.value = this.vol.master * this.vol.combat;
    this.fade();''',
        "sound.ts live updates")
    return s


def patch_settings(s):
    if '<!-- INDEPENDENT_AUDIO_UI_V1 -->' in s or '{/* INDEPENDENT_AUDIO_UI_V1 */}' in s:
        return s
    s = replace_once(s,
        '''        <h1 className="logo small">SOUND</h1>
        <div className="volumes">
          {([["master", "Master"], ["music", "Music"], ["sfx", "Effects"]] as const).map(([k, label]) => (
            <label key={k} className="vol-row">
              <span className="act">{label}</span>
              <input type="range" min={0} max={100} value={Math.round(vol[k] * 100)}
                onChange={(e) => { Sound.setVolume(k, +e.target.value / 100); setVol({ ...Sound.vol }); }}
                onMouseUp={() => k === "sfx" && Sound.play("hit_blade", 0.8)} />
              <em>{Math.round(vol[k] * 100)}%</em>
            </label>
          ))}
        </div>''',
        '''        <h1 className="logo small">AUDIO SETTINGS</h1>
        {/* INDEPENDENT_AUDIO_UI_V1 */}
        <p className="tag">Music changes only background tracks. Clashes, parries, blocks, and guard breaks have their own slider. Master changes everything.</p>
        <div className="volumes">
          {([["music", "Music"], ["sfx", "Sound Effects"], ["combat", "Clashes & Parries"], ["master", "Master"]] as const).map(([k, label]) => (
            <label key={k} className="vol-row">
              <span className="act">{label}</span>
              <input type="range" min={0} max={100} value={Math.round(vol[k] * 100)}
                aria-label={`${label} volume`}
                onChange={(e) => { Sound.setVolume(k, +e.target.value / 100); setVol({ ...Sound.vol }); }}
                onPointerUp={() => {
                  if (k === "sfx") Sound.play("hit_blade", 0.8);
                  if (k === "combat") Sound.play("clash", 0.85, 0);
                }} />
              <em>{Math.round(vol[k] * 100)}%</em>
            </label>
          ))}
        </div>''',
        "Settings.tsx sound sliders")
    return s



def patch_zarek_counter(s):
    """Improve ONLY the visibility of Zarek's HUD Clash Counter."""
    if ZAREK_MARKER in s:
        return s
    # Supports both the older 'Clash Momentum' HUD and the current Clash Counter.
    # Neither the counter value nor its underlying attack-speed mechanics are changed.
    match = re.search(r'\{me\.id\s*===\s*[\"\']zarek[\"\']\s*&&\s*\(', s)
    if not match:
        raise RuntimeError("Could not find Zarek's HUD in src/ui/GameView.tsx; no files changed. Upload that file for a compatible patch.")
    start = match.start()
    fragment = s[start:start+500]
    color = re.search(r'color\s*:\s*[\"\']#[0-9A-Fa-f]{6}[\"\']', fragment)
    if not color:
        raise RuntimeError("Zarek's HUD color format has changed; no files changed. Upload src/ui/GameView.tsx for a compatible patch.")
    a, b = start + color.start(), start + color.end()
    # Adding a shadow increases visibility even when the guard bar is bright.
    s = s[:a] + 'color: "#ffffff", textShadow: "0 1px 3px rgba(0, 0, 0, 0.95)"' + s[b:]
    s = s[:start] + '{/* ZAREK_WHITE_COUNTER_V1 */}\n              ' + s[start:]
    return s


def main():
    try:
        if not (ROOT / "package.json").is_file():
            raise RuntimeError("Place this file directly inside the web folder, next to package.json.")
        # Normalize newlines for safe text matching, restore original style on write.
        paths = (SOUND, SETTINGS, GAMEVIEW)
        raw = {p: p.read_bytes() for p in paths}
        crlf = {p: b"\r\n" in raw[p] for p in paths}
        old = {p: raw[p].decode("utf-8").replace("\r\n", "\n") for p in paths}
        new = {SOUND: patch_sound(old[SOUND]), SETTINGS: patch_settings(old[SETTINGS]),
               GAMEVIEW: patch_zarek_counter(old[GAMEVIEW])}
        changes = [p for p in paths if old[p] != new[p]]
        if not changes:
            print("Already installed; nothing to change.")
            return
        # Never half-patch one file from an unfamiliar revision.
        if (MARKER in old[SOUND] and '{/* INDEPENDENT_AUDIO_UI_V1 */}' not in old[SETTINGS]):
            raise RuntimeError("sound.ts is already modified but Settings.tsx is not. Restore consistent files before patching.")
        if ('{/* INDEPENDENT_AUDIO_UI_V1 */}' in old[SETTINGS]) and MARKER not in old[SOUND]:
            raise RuntimeError("Settings.tsx is already modified but sound.ts is not. Restore consistent files before patching.")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backups = {}
        for p in changes:
            backup = p.with_name(p.name + f".before_audio_{stamp}.bak")
            backup.write_bytes(raw[p])
            backups[p] = backup
        for p in changes:
            tmp = p.with_name(p.name + ".audio_patch_tmp")
            modified = new[p].replace("\n", "\r\n") if crlf[p] else new[p]
            tmp.write_bytes(modified.encode("utf-8"))
            os.replace(tmp, p)
            print(f"PATCH {p.relative_to(ROOT)} (backup: {backups[p].name})")
        print("DONE. Music, Effects, and Clashes/Parries are independently adjustable.")
        print("Zarek's Clash Counter is now bright white with a dark shadow; gameplay remains unchanged.")
        print("Run `npx tsc --noEmit` then `npm run dev`.")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
