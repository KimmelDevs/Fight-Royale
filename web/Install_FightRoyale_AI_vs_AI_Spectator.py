#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale: add offline 1v1 CPU vs CPU spectator mode.

Run in the web folder:
    python Install_FightRoyale_AI_vs_AI_Spectator.py
or pass its path.  --check validates the patch without writing.

Changes only App.tsx, GameView.tsx, game.ts, and adds WatchSelect.tsx.
Makes timestamped backups of existing files; safe to run a second time.
No character, AI, damage, balance, or skill data is changed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

MARK = 'FIGHT_ROYALE_CPU_VS_CPU_SPECTATOR_V1'

WATCH_SELECT = '''"use client";
// FIGHT_ROYALE_CPU_VS_CPU_SPECTATOR_V1
import { useState } from "react";
import { CHARACTERS } from "@/game/roster";
import { LEVELS } from "@/game/ai";
import { CardRow, Showcase, RANDOM } from "./Select";

const COLORS = ["#6fcf7f", "#5fa8e3", "#f2994a", "#e8534a"];
const nameOf = (i: number) => i === RANDOM ? "Random fighter" : CHARACTERS[i]?.look.name ?? "Unknown";

/** Two CPU fighters, selectable difficulty, no player slot, no unlock requirement. */
export default function WatchSelect({ onBack, onStart }: {
  onBack: () => void;
  onStart: (left: number, right: number, difficulty: number) => void;
}) {
  const [active, setActive] = useState<0 | 1>(0);
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(1);
  const [difficulty, setDifficulty] = useState(1);
  const chosen = active === 0 ? left : right;

  const start = () => {
    const ids = CHARACTERS.map((_, i) => i);
    const a = left === RANDOM ? ids[Math.floor(Math.random() * ids.length)] : left;
    const choices = ids.filter((i) => i !== a);
    const b = right === RANDOM ? choices[Math.floor(Math.random() * choices.length)] : right;
    onStart(a, b, difficulty);
  };

  return (
    <div className="select">
      <Showcase index={chosen} />
      <div className="header">
        <h1 style={{ color: "#ffe08a" }}>CPU VS CPU · SPECTATOR</h1>
        <div className="sub">Pick two fighters, choose AI difficulty, then watch a best-of-three duel. No player controls required.</div>
      </div>
      <div className="panel" style={{ width: "min(730px, 94vw)", margin: "0 auto", padding: 14 }}>
        <h2>Choose the matchup</h2>
        <div className="row two" style={{ gap: 10, alignItems: "stretch" }}>
          <button type="button" className={"big" + (active === 0 ? " blue" : " ghost")}
            onClick={() => setActive(0)} style={{ flex: 1, minWidth: 0, padding: "13px 8px" }}>
            <span style={{ display: "block", fontSize: 11, opacity: 0.8 }}>CPU 1 · BLUE</span>
            {nameOf(left)} {active === 0 ? "✓" : ""}
          </button>
          <button type="button" className={"big" + (active === 1 ? " gold" : " ghost")}
            onClick={() => setActive(1)} style={{ flex: 1, minWidth: 0, padding: "13px 8px" }}>
            <span style={{ display: "block", fontSize: 11, opacity: 0.8 }}>CPU 2 · RED</span>
            {nameOf(right)} {active === 1 ? "✓" : ""}
          </button>
        </div>
        <div className="small" style={{ marginTop: 8 }}>Select {active === 0 ? "CPU 1" : "CPU 2"} from the fighter cards below. Any fighter is allowed in offline spectator mode.</div>
      </div>
      <div className="bottom">
        <CardRow current={chosen} allowRandom showLocks={false}
          onPick={(i) => active === 0 ? setLeft(i) : setRight(i)} />
        <div className="actions">
          <div className="levels">
            <span>Both CPUs · AI difficulty</span>
            <div>
              {LEVELS.map((l, i) => (
                <button key={l} className={"lvl" + (i === difficulty ? " on" : "")}
                  style={{ ["--c" as any]: COLORS[i] ?? "#e8534a" }} onClick={() => setDifficulty(i)}>{l}</button>
              ))}
            </div>
          </div>
          <div className="row">
            <button className="big ghost" onClick={onBack}>&lt; BACK</button>
            <button className="big gold" onClick={start}>WATCH FIGHT!</button>
          </div>
        </div>
      </div>
    </div>
  );
}
'''


class PatchError(RuntimeError):
    pass


def one(s: str, old: str, new: str, desc: str) -> str:
    n = s.count(old)
    if n != 1:
        raise PatchError(f'{desc}: expected one anchor, got {n}; files may differ from supported Fight Royale source')
    return s.replace(old, new, 1)


def find_root(path: str | None) -> Path:
    root = Path(path).expanduser().resolve() if path else Path.cwd()
    for candidate in (root, root / 'web'):
        if (candidate / 'src/ui/App.tsx').is_file() and (candidate / 'src/game/game.ts').is_file():
            return candidate
    raise PatchError('Could not find Fight Royale web folder. Run inside web or pass its path.')


def patch_app(s: str) -> str:
    if MARK in s:
        return s
    s = one(s, 'import Select from "./Select";', 'import Select from "./Select";\nimport WatchSelect from "./WatchSelect"; // ' + MARK, 'App import')
    s = one(s, '  | { s: "online" }', '  | { s: "watch" }\n  | { s: "online" }', 'App screen union')
    s = one(s, '  if (screen.s === "settings") return <Settings onBack={toMenu} />;', '''  if (screen.s === "watch") return <WatchSelect onBack={toMenu}
    onStart={(left, right, difficulty) => {
      const players = [left, right].map((char, i) => ({
        peer: `cpu-${i + 1}`,
        name: CHARACTERS[char].look.name,
        char,
      }));
      setScreen({ s: "game", cfg: {
        mode: "duel", role: "offline", spectator: true,
        players, localPeer: "spectator", difficulty,
      }, net: null });
    }} />;
  if (screen.s === "settings") return <Settings onBack={toMenu} />;''', 'App watch flow')
    s = one(s,
        '        <button className="big gold" onClick={() => setScreen({ s: "select", purpose: "duel" })}>Duel vs CPU</button>',
        '        <button className="big gold" onClick={() => setScreen({ s: "select", purpose: "duel" })}>Duel vs CPU</button>\n        <button className="big blue" onClick={() => setScreen({ s: "watch" })}>Watch CPU vs CPU (1v1)</button>',
        'App menu button')
    return s


def patch_game(s: str) -> str:
    if MARK in s:
        return s
    s = one(s, '  cpuChar?: number;\n  difficulty?: number;',
            '  cpuChar?: number;\n  difficulty?: number;\n  /** ' + MARK + ': both sides are CPU-driven; viewer has no fighter. */\n  spectator?: boolean;', 'GameConfig spectator flag')
    s = one(s,
        '      if (b.peer === "cpu" && !this.plat) f2.autoApproach = !["mage", "bow", "bomb"].includes(f2.kit);',
        '''      if (cfg.spectator && !this.plat) {
        // Both CPUs close distance when using melee; ranged kits preserve their spacing.
        f1.autoApproach = !["mage", "bow", "bomb"].includes(f1.kit);
        f2.autoApproach = !["mage", "bow", "bomb"].includes(f2.kit);
      } else if (b.peer === "cpu" && !this.plat) f2.autoApproach = !["mage", "bow", "bomb"].includes(f2.kit);''', 'Both CPU engagement')
    s = one(s,
        '        const text = this.cfg.role === "offline" ? (iWon ? "VICTORY" : "DEFEAT") : `${name.toUpperCase()} WINS`;',
        '        const text = this.cfg.spectator ? `${name.toUpperCase()} WINS!` : this.cfg.role === "offline" ? (iWon ? "VICTORY" : "DEFEAT") : `${name.toUpperCase()} WINS`;', 'Spectator result headline')
    s = one(s,
        '        this.over(text, `Final Score: ${a} - ${b} | Press R or click Rematch`, iWon || this.cfg.role !== "offline" ? "#ffe08a" : "#ff7b7b");',
        '        this.over(text, `Final Score: ${a} - ${b} | Press R or click Rematch`, this.cfg.spectator || iWon || this.cfg.role !== "offline" ? "#ffe08a" : "#ff7b7b");', 'Spectator result color')
    s = one(s, '    const me = this.local;\n    const boss = this.mobs.find((m) => m.def.boss && !m.dead);',
        '    const me = this.local ?? (this.cfg.spectator ? this.fighters[0] ?? null : null);\n    const boss = this.mobs.find((m) => m.def.boss && !m.dead);', 'Spectator HUD left slot')
    # Camera is already framed around both fighters even without a local participant.
    return s


def patch_view(s: str) -> str:
    if MARK in s:
        return s
    s = one(s, '  const me = hud?.me;\n  const other = hud?.other;',
        '  // ' + MARK + ': CPU vs CPU uses a two-sided HUD without local input controls.\n  const me = hud?.me;\n  const other = hud?.other;', 'GameView spectator marker')
    s = one(s,
        '              <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.16em", color: "#ffdf8d" }}>{hud.roundLabel} · FIRST TO 2</span>',
        '              <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.16em", color: "#ffdf8d" }}>{cfg.spectator ? "CPU VS CPU · " : ""}{hud.roundLabel} · FIRST TO 2</span>', 'Spectator score label')
    s = one(s,
        '                <span style={{ fontSize: 10, color: "#8ccfff" }}>{hud.mode === "team" ? "BLUE" : "P1"}</span>',
        '                <span style={{ fontSize: 10, color: "#8ccfff" }}>{cfg.spectator ? "CPU 1" : hud.mode === "team" ? "BLUE" : "P1"}</span>', 'Spectator left label')
    s = one(s,
        '                <span style={{ fontSize: 10, color: "#ff9a9a" }}>{hud.mode === "team" ? "RED" : "P2"}</span>',
        '                <span style={{ fontSize: 10, color: "#ff9a9a" }}>{cfg.spectator ? "CPU 2" : hud.mode === "team" ? "RED" : "P2"}</span>', 'Spectator right label')
    s = one(s, '          <div className="skills">',
        '          {!cfg.spectator && <div className="skills">', 'Hide spectator skills')
    s = one(s, '          <div className="hint">{hud?.plat',
        '          {!cfg.spectator && <div className="hint">{hud?.plat', 'Hide spectator controls')
    # targeted close of the two blocks (avoid touching ordinary HUD elements).
    s = one(s,
        '''            ))}
          </div>
          {/* AIR_COMBAT_V1: show both keyboard chords without changing keybindings. */}''',
        '''            ))}
          </div>}
          {/* AIR_COMBAT_V1: show both keyboard chords without changing keybindings. */}''', 'Close spectator skill conditional')
    s = one(s,
        '''            : `${label("up")}${label("left")}${label("down")}${label("right")} move - ${label("jump")} jump - ${label("attack")} attack (hold = charged) - ${label("block")} block - ${label("skill1")} ${label("skill2")} ${label("skill3")} skills - Space+${label("attack")} anti-air / air combo - tap ${label("jump")} after launcher to chase - hold air attack for heavy - air ${label("block")} block/recover - Esc pause`}</div>''',
        '''            : `${label("up")}${label("left")}${label("down")}${label("right")} move - ${label("jump")} jump - ${label("attack")} attack (hold = charged) - ${label("block")} block - ${label("skill1")} ${label("skill2")} ${label("skill3")} skills - Space+${label("attack")} anti-air / air combo - tap ${label("jump")} after launcher to chase - hold air attack for heavy - air ${label("block")} block/recover - Esc pause`}</div>}''', 'Close spectator hint conditional')
    s = one(s, '{f.name}{f.peer === cfg.localPeer ? " · YOU" : ""}',
        '{f.name}{!cfg.spectator && f.peer === cfg.localPeer ? " · YOU" : ""}', 'No spectator YOU label')
    return s


FILES = {
    'src/ui/App.tsx': patch_app,
    'src/game/game.ts': patch_game,
    'src/ui/GameView.tsx': patch_view,
}


def main():
    parser = argparse.ArgumentParser(description='Install offline 1v1 CPU vs CPU spectator mode')
    parser.add_argument('project', nargs='?', help='Path to Fight Royale web folder or repository root')
    parser.add_argument('--check', action='store_true', help='Dry-run only, no writes')
    args = parser.parse_args()
    root = find_root(args.project)
    print('Fight Royale project:', root)
    changes: dict[str, bytes] = {}
    for rel, fn in FILES.items():
        file = root / rel
        if not file.is_file():
            raise PatchError(f'Missing {rel}')
        before = file.read_text(encoding='utf-8')
        after = fn(before)
        if before != after:
            changes[rel] = after.encode('utf-8')
    watch_rel = 'src/ui/WatchSelect.tsx'
    watch_path = root / watch_rel
    if watch_path.is_file():
        existing = watch_path.read_text(encoding='utf-8')
        if MARK not in existing:
            raise PatchError('WatchSelect.tsx already exists without the spectator marker. Leaving it untouched.')
    else:
        changes[watch_rel] = WATCH_SELECT.encode('utf-8')
    print('Files to update:', len(changes))
    for rel in changes:
        print(' -', rel)
    if args.check:
        print('[CHECK] Patches validated without changing files.')
        return
    if not changes:
        print('[OK] Spectator mode already installed; nothing to change.')
        return
    backup = root / '.fight_royale_spectator_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True, exist_ok=False)
    for rel in changes:
        existing = root / rel
        if existing.exists():
            dst = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(existing, dst)
    completed = []
    try:
        for rel, body in changes.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
                tmp.write(body)
                temp = Path(tmp.name)
            os.replace(temp, target)
            completed.append(rel)
    except Exception:
        for rel in completed:
            current = root / rel
            saved = backup / rel
            if saved.exists():
                shutil.copy2(saved, current)
            elif current.exists():
                current.unlink()
        raise
    print('[DONE] Watch CPU vs CPU added to the main menu.')
    print('[BACKUP]', backup)
    print('Now: npx tsc --noEmit -p . && npm run dev')


if __name__ == '__main__':
    try:
        main()
    except (OSError, PatchError) as exc:
        print('INSTALL FAILED:', exc)
        sys.exit(1)
