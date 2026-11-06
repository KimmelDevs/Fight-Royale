#!/usr/bin/env python3
# Fight Royale victory highlight installer; Python 3.9+ standard library only
import sys, os, argparse, re, shutil, tempfile, base64, zlib
from pathlib import Path
from datetime import datetime

TAG = "FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1"
POSE_B64 = "eNqFWG1v20YS/u5fMTBQnOVKMl8l2YbvkMv52gBpUyRBisIwjBW5kghRXGKXlOz28t9vZndJkSKpfmhjcV/nmZlnntmbG/jvh59+/vry+dMf7z4+vnz78P7rp89/vPyMHz/SwJeXb+7Fzcms3z4/fnn89eu7rx8+/Yrjd7BPVMnSicjSN4g2TLKo4BJyobi6h0jslqwAVbBCAZMcyqwQZbTh8fQi2eVCFlC85Rz+gt9wwRi+8ciH77CSYgeX05ttUqjL+4uLm+treHzNJVcq2eO0VIg8ydbH8yaKpzwqgGUxXigqhHwzV4CVkFBsOPDXRBW05tvnX25yKSIel5KlIJP1FK5vLvirvs2qzKIiERnQYTzDe+MPuttVxnb8Di2RuMkYFI9EFqs7yMrdkssxLJnCYWPFTsT496W50yX8Dy7tnS7hof48MrPhrwtAmDKFSOCo3Rd+gCvaBR4eHhqr/wXhNIA7CKbz0X29Li9T3OcBfmHFZqqS7KqAa/CnQWOKOnCen04Jp05jSpqs6AK9p7pT18Nj3ePsSORvOPtqf6d9NjL/wMM/4Wn/5DyPYf/k6v97z8+Nm1qbH7TVALi/End6sysCcKo/jMaw4Sxufqffo7Few+TuRTbH9Adag85vj5gvjXXp6bq0Wpd21qV2XcrX7VH9AdfRv/J0oDptk+Tq5e0OzH76xxi2Gef2E/2JwD5Np9P69zNC/OSMAeHDPb4fYVulopSV93boPXds/2avV7gAvTkBZ+o7I/SqN52NGm7diDT+u6XoXrPSMSvVISmiDeiQR5d8FAcu3+Mtr0Yj67gIf8Hln5jR28s7II5I1qXkE56sNwXEolymfLJOGWYr2ltgPhWHRKZjwJ03mEToTkzQlGUFj2HFeTHV2wLkJgTwxk/O1JkhGFN3Dj/SPwu8oo7jMUxoTMeVWUPhQUvoe6CH3ZBwPM7QQaKnoLGhgWuGG+rcoVP8hT7Fax3iN8/QwWQu5jv6Yp45anZyTmqvsgjNlt7xHJq+oLVeeLp1aremYT2jMUGHnN3V8+0Ed/F8b8fstbxQD53eyYQfTtGwhfewlJxt7xuO3CaSGT9+yvgEdyRmJV6DBPkaGOZjGmOmoHdBJUgQ2yTa9riMTnZrK/UvDbVzW0HQ4zQc9rXBwx5zwgbeQajtbvojdHoNbzrjNjTjAe0UHHewsIdehWowgDsZZmb4JzOkneF72tiQAlWnLM0m28hrjh6bOzhGKdnYQlOBvgQZiHNM2OjwvCL8aP7I3LjlyR5HMkwtaTz5pSglJpnaJOi7ySqRRAZciiQCxdKy4IMpR8b62hknqaUjV+PQ6yePkoisxARrIjA3W3odt+n87u6WNrxO0M11dAR1tNceqVLF6WSCO6sCwrntIrfoy4E9V3mF3XuZ7BSSVlxypH51EDK2oBkCYwgrkzmxPOTJXgzQl6Ei79bw1+xILQRKB93AkN1wFtwa3vLCJm8FJt/8eQfdKl49b4ifjGN8fbAfdvA9Mo1/iq9f5xtB38FyzaREhjBg/oSjhcFww1fFGNZSlFmMxK82okxjLhXqqVQcauUmWaL6w9PzKpAIMb+D4a2tDcMgzkwiBj05Gsw6GFpGHYpQ1/CSqR+dOHPDfiY5A+uRwP0+XLeMx9yg+oElsUDZmTKkY5loqUuqmQEhGUt26I9Jg5BnOMZthGQLS6eyqxdFZzoLtWxwmigG3jEiTsrlORSJ0PXCcCgMwwqvTr0Larj60OJUwSp5gr2HEjLi1EOAKnc7VEcI1ipFjQNizyWZ3g/Z4qgoKqppxJzOWFOhBlgxMFi7zbR1Z3W5Ok1b73zeuhXQfjPsGqXMqCZL4B1QdgwbGFvsHxFLlGBwYNSyqTyhhuiGurXVysTFOUC8xWkMTQw+vXk3t+TV4i7jeN+A0DSxYWE4oPNmR81wGjCD8eKdjZfs7bWif6EU8lPM1mvNTthAZiAybtPtQFmu1VA/SRne922OeS3eX3Tz7IzwuTWg+S3ULPxD4eEZVGeVmjlBJxhCx2+hc0JlXg9eUghL8f8Wr1z+QxFEk+KAtLTCZtvQeAzY/+sGPOtPL/fWiNkOIWl+70XFM0IraAktzxSFoCszalLtBGcFme9bjxl8u+qwLTRayAS99S+1NP17kmGDQ10Rl/R68JYmakMUPSnEROtp5G56liDE+rPN2OXNjixSI+R6A5RjJWQzbDy/Trb+WmbViiaPoCOo6opPnUvX4qVYWtm5EYcdyzAY+GueCnqvMT5Cu7FcCVJPcqdQR8W8v4OoOjjPGBy0QiLo0K9f068WVf0dn0mjRRMPzWIuxXo/HKZ3W7R6N1rj9pOHZHueVT7H7hkBMDwaJ2wtMiTWIwoiRzrBZfo9Kmfp7izNGhx0C9Xg2XDA866JkzZl+LPadb3GhrazormzWSf8TV/ieT09gVs1Zr3FhqmNgeSdjDaaIXLJI2QFLVAsr0qecpp9pitxDaUFQU8OOO6A033NgHNreleVBEa8hcPyzjsSadCp+ybkvHDA9D1/s9rjPyU6X6EcTlGjRaa0jCk40q2q+muEJWZa+6okRVXMiwEkfNsJd3Jj0qdNbAdlnhycYIhOjWAw1s47tdg2sIsqOHrfFdzFaZ3xw0GZqzu6szI3+bNKpvcblmSm7KJAyUie2K6hTqjBkKmTZ1DnNjA6U4VDv/fBaKjeNArp/G9eI0xszbtVpYVKzFesTAujZEvs6/nx5Vth/hQIkX6kkaJqU8usSFLKL+ymeMSJhRksscUVW65fxge7gx60WvxiFcuk/ULV6iut44Omb7/jf6Y8yAIiTPmlNAGv352x17bNn3kiFGVBJmZrzZBYRegZHvWFhEikWELphR5b8JwrsiNZ9b2WV2+V9v5PzjNMHqqs0adeH9/D6/fRghg+pOdQVF+j+4uj8Kw3cBbVZw3dk/sMP+qNnd4dEbECw9Y+smIHOqrwQM+VMoP8/uL7xf8BEDbJJw=="

class PatchError(Exception): pass

def once(src, needle, replacement, label):
    c = src.count(needle)
    if c != 1: raise PatchError(f"{label}: expected 1 anchor, found {c}. No files changed.")
    return src.replace(needle, replacement, 1)

def patch_preview(s):
    s = once(s, 'import type { Look } from "./roster";',
        'import type { Look } from "./roster";\nimport { presentationPose } from "./presentation";', 'preview import')
    s = once(s, '  private pose = "win";', '  private pose = "idle";\n  private mode: "select" | "victory" = "select";\n  private lookName = "";', 'preview pose')
    s = once(s, '  setLook(look: Look | null) {',
        '  setMode(mode: "select" | "victory") { this.mode = mode; this.poseT = 0; }\n\n  setLook(look: Look | null) {', 'preview setMode')
    s = once(s, '    if (!look) return;', '    if (!look) return;\n    this.lookName = look.name;', 'preview look')
    s = once(s, '    this.pose = "win";', '    this.pose = "idle";', 'preview reset')
    s = once(s, '      if (this.pose === "win" && this.poseT > 1.1) this.pose = "idle";\n      this.model.blend(this.poses[this.pose], dt, 6);',
        '      // Unique, looping VRM-compatible presentation; visual only.\n      this.model.glaivePose = this.lookName.toLowerCase() === "zarek" ? "show_baton" : "idle";\n      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt, 9);', 'preview animation')
    return '// '+TAG+'\n'+s

def patch_model(s):
    needle = '      const a = angles[this.glaivePose] ?? angles.idle;\n      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));'
    rep = '''      const a = angles[this.glaivePose] ?? angles.idle;
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));
      // Show-only double-glaive baton spin, rotating about an axis perpendicular to the pole.
      if (this.glaivePose === "show_baton") {
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), this.t * 9.5));
      }'''
    s = once(s, needle, rep, 'model baton visual')
    return '// '+TAG+'\n'+s

def patch_fighter(s):
    s = once(s, 'import * as Kits from "./kits";', 'import * as Kits from "./kits";\nimport { presentationPose } from "./presentation";', 'fighter import')
    needle = '    this.model.glaivePose = this.kit === "glaive" ? this.poseName : "idle";'
    if s.count(needle) != 2: raise PatchError('fighter glaive: expected 2 rig update sites')
    s = s.replace(needle, '    this.model.glaivePose = this.kit === "glaive" ? (this.state === S.WIN ? "show_baton" : this.poseName) : "idle";')
    needle = '    this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);'
    if s.count(needle) != 2: raise PatchError('fighter blend: expected host + puppet rig update sites')
    s = s.replace(needle, '''    this.model.blend(this.state === S.WIN
      ? presentationPose(this.look.name, this.stateT, this.poses.idle, "victory")
      : (this.poses[this.poseName] ?? this.poses.idle), dt, this.poseSpeed);''')
    return '// '+TAG+'\n'+s

def patch_game(s):
    old = '  | { type: "result"; winner: number };'
    s = once(s, old, old[:-1]+'''
  | { type: "highlights"; summary: MatchHighlights };''', 'game UiEvent')
    s = once(s, 'const v3 = (a: any)', '''export interface HighlightFighter {
  name: string; peer: string; team: number; glow: string;
  totalDamage: number; hits: number; bestCombo: number; clashes: number; perfectDodges: number;
}
export interface MatchHighlights {
  fighters: HighlightFighter[];
  finisher: { fighter: string; move: string; damage: number } | null;
}

const v3 = (a: any)''', 'game highlight types')
    s = once(s, '  onEvent: (e: UiEvent) => void = () => {};',
      '''  onEvent: (e: UiEvent) => void = () => {};
  // Per-series statistics; remain across rounds, reset on rematch.
  private highlightRecords = new Map<string, HighlightFighter & { combo: number; lastHit: number }>();
  private highlightFinisher: MatchHighlights["finisher"] = null;
  private highlightKey(f: Fighter) { return `${f.team}:${f.owner}:${f.look.name}`; }
  private highlightRecord(f: Fighter) {
    const key = this.highlightKey(f);
    let rec = this.highlightRecords.get(key);
    if (!rec) {
      rec = { name: f.look.name, peer: f.owner, team: f.team, glow: f.look.glow,
        totalDamage: 0, hits: 0, bestCombo: 0, clashes: 0, perfectDodges: 0,
        combo: 0, lastHit: -999 };
      this.highlightRecords.set(key, rec);
    }
    return rec;
  }
  private highlightHit(f: Fighter, a: Attack, damage: number, isKo: boolean) {
    const r = this.highlightRecord(f);
    r.hits++;
    r.totalDamage += Math.max(0, damage);
    r.combo = this.time - r.lastHit <= 1.65 ? r.combo + 1 : 1;
    r.lastHit = this.time;
    r.bestCombo = Math.max(r.bestCombo, r.combo);
    if (isKo) this.highlightFinisher = { fighter: f.look.name,
      move: a.name || (a.heavy ? "Heavy Strike" : a.id.startsWith("l") ? "Light Combo" : a.id.replace(/_/g, " ")),
      damage: Math.round(Math.max(0, damage)) };
  }
  private matchHighlights(): MatchHighlights {
    const fighters = [...this.highlightRecords.values()].map(({ combo, lastHit, ...r }) => ({
      ...r, totalDamage: Math.round(r.totalDamage) }));
    return { fighters, finisher: this.highlightFinisher };
  }''', 'game recorder props')
    s = once(s, '    f.owner = slot.peer;\n    f.puppet = this.cfg.role === "client";',
      '    f.owner = slot.peer;\n    this.highlightRecord(f);\n    f.puppet = this.cfg.role === "client";', 'game init fighter score')
    s = once(s, '    this.matchWins = [0, 0];\n    this.emit(["roundScore", 0, 0]);',
      '    this.matchWins = [0, 0];\n    this.highlightRecords.clear();\n    this.highlightFinisher = null;\n    this.emit(["roundScore", 0, 0]);', 'game rematch reset')
    s = once(s, '      case "hit": case "crit": case "ko": {\n        const crit = d.lastCrit;',
      '''      case "hit": case "crit": case "ko": {
        if (attacker instanceof Fighter) this.highlightHit(attacker, a, d.lastDamage, result === "ko");
        const crit = d.lastCrit;''', 'game record damage')
    s = once(s, '      case "perfect_dodge": {\n        const defender = d as Fighter;',
      '''      case "perfect_dodge": {
        const defender = d as Fighter;
        this.highlightRecord(defender).perfectDodges++;''', 'game dodge counting')
    s = once(s, '    const bomb = !!p.atk && (p.atk.type === "lob" || p.style === "bomb");',
      '    const bomb = !!p.atk && (p.atk.type === "lob" || p.style === "bomb");\n    if (!bomb) this.highlightRecord(defender).clashes++;', 'game projectile clash')
    s = once(s, '  private onBlast(f: Fighter) {',
      '  private onBlast(f: Fighter) {\n    // An arena ring-out has no recorded damaging finishing move.\n    if (f.stocks <= 1) this.highlightFinisher = null;', 'game brawl ringout')
    s = once(s, '  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {',
      '''  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {
    this.highlightRecord(a).clashes++;
    this.highlightRecord(b).clashes++;''', 'game weapon clash')
    s = once(s, '''  private over(text: string, sub: string, color: string) {
    this.onEvent({ type: "over", text, sub, color });''',
      '''  private over(text: string, sub: string, color: string) {
    const summary = this.matchHighlights();
    this.onEvent({ type: "highlights", summary });
    this.emit(["highlights", summary]);
    this.onEvent({ type: "over", text, sub, color });''', 'game results summary')
    s = once(s, '      case "over": this.onEvent({ type: "over", text: ev[1], sub: ev[2], color: ev[3] }); break;',
      '      case "highlights": this.onEvent({ type: "highlights", summary: ev[1] as MatchHighlights }); break;\n      case "over": this.onEvent({ type: "over", text: ev[1], sub: ev[2], color: ev[3] }); break;', 'game network result')
    return '// '+TAG+'\n'+s

def patch_ui(s):
    s = once(s, 'import { Game, type GameConfig, type Perk, type UiEvent } from "@/game/game";',
      'import { Game, type GameConfig, type Perk, type UiEvent, type MatchHighlights } from "@/game/game";\nimport { CHARACTERS } from "@/game/roster";\nimport { Preview } from "@/game/preview";', 'ui imports')
    s = once(s, 'function StatusChips({ list, right }:', '''// A second, lightweight 3D camera for the winning fighter's signature celebration.
function WinnerPreview({ index }: { index: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const view = new Preview(canvas.current!);
    view.setMode("victory");
    view.setLook(CHARACTERS[index].look);
    return () => view.dispose();
  }, [index]);
  return <canvas ref={canvas} className="victory-character-canvas" />;
}

function StatusChips({ list, right }:''', 'ui win preview')
    s = once(s, '  const [over, setOver] = useState<{ text: string; sub: string; color: string } | null>(null);',
      '''  const [over, setOver] = useState<{ text: string; sub: string; color: string } | null>(null);
  const [highlights, setHighlights] = useState<MatchHighlights | null>(null);
  const [winnerChar, setWinnerChar] = useState<number | null>(null);''', 'ui summary state')
    old = '''      } else if (e.type === "result" && cfg.ranked) {
        rankResult(e.winner === (g.local?.team ?? 0));
      } else if (e.type === "result" && betPlaced) {
        account.reportResult(matchId!, e.winner).then(() => toast(e.winner === team ? "Bet won! Pot paid out." : "Bet settled."));
      }'''
    new = '''      } else if (e.type === "highlights") {
        setHighlights(e.summary);
      } else if (e.type === "result") {
        const winningFighter = g.fighters.find((f) => f.team === e.winner && !f.isDown())
          ?? g.fighters.find((f) => f.team === e.winner);
        setWinnerChar(winningFighter?.charIndex ?? null);
        if (cfg.ranked) rankResult(e.winner === (g.local?.team ?? 0));
        if (betPlaced) account.reportResult(matchId!, e.winner).then(() => toast(e.winner === team ? "Bet won! Pot paid out." : "Bet settled."));
      }'''
    s = once(s, old, new, 'ui result event')
    s = once(s, 'if (e.code === "KeyR" && g.canRestart) { setOver(null); setRankChange(null); rankDone.current = false; g.restart(); }',
      'if (e.code === "KeyR" && g.canRestart) { setOver(null); setHighlights(null); setWinnerChar(null); setRankChange(null); rankDone.current = false; g.restart(); }', 'ui R reset')
    s = once(s, 'const rematch = () => { setOver(null); setPerks(null); setRankChange(null); rankDone.current = false; game.current?.restart(); };',
      'const rematch = () => { setOver(null); setHighlights(null); setWinnerChar(null); setPerks(null); setRankChange(null); rankDone.current = false; game.current?.restart(); };', 'ui rematch reset')
    s = once(s, '''          {rankChange && (
            <div className="rank-result">''',
      '''          {!lost && (winnerChar !== null || highlights) && (
            <div className="match-highlights-layout">
              {winnerChar !== null && <div className="victory-character">
                <WinnerPreview index={winnerChar} />
                <b>{CHARACTERS[winnerChar]?.look.name ?? "Winner"}</b>
                <span>VICTORY POSE</span>
              </div>}
              {highlights && <div className="match-highlights">
                <div className="highlight-heading">MATCH HIGHLIGHTS</div>
                <div className="highlight-finisher">
                  <span>FINISHING MOVE</span>
                  <b>{highlights.finisher ? `${highlights.finisher.fighter} · ${highlights.finisher.move}` : "Final blow / ring-out"}</b>
                  {highlights.finisher && <em>{highlights.finisher.damage} damage</em>}
                </div>
                <div className="highlight-fighters">
                  {highlights.fighters.map((f, i) => <div className="highlight-fighter" key={`${f.peer}-${f.team}-${i}`}>
                    <strong style={{ color: f.glow }}>{f.name}{f.peer === cfg.localPeer ? " · YOU" : ""}</strong>
                    <div><span>Biggest combo</span><b>{f.bestCombo} hits</b></div>
                    <div><span>Successful clashes</span><b>{f.clashes}</b></div>
                    <div><span>Perfect dodges</span><b>{f.perfectDodges}</b></div>
                    <div><span>Damage dealt</span><b>{f.totalDamage}</b></div>
                  </div>)}
                </div>
              </div>}
            </div>
          )}
          {rankChange && (
            <div className="rank-result">''', 'ui highlight display')
    return '// '+TAG+'\n'+s

def patch_css(s):
    return s + '''
/* FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1: compact results overlay and VRM celebration. */
.over:has(.match-highlights-layout) { background: rgba(6, 12, 32, .72); gap: 8px; padding: 14px; box-sizing: border-box; z-index: 12; overflow-y: auto; }
.over:has(.match-highlights-layout) > .txt { font-size: clamp(32px, 5vw, 58px); line-height: 1; }
.over:has(.match-highlights-layout) > .bsub { font-size: 13px; text-align: center; }
.match-highlights-layout { width: min(790px, 96vw); display: grid; grid-template-columns: minmax(170px, .8fr) minmax(280px, 1.45fr); align-items: stretch; gap: 12px; max-height: min(54vh, 410px); }
.victory-character { background: linear-gradient(145deg, rgba(56,74,130,.87), rgba(10,19,48,.9)); border: 1px solid rgba(230,194,110,.5); border-radius: 14px; position: relative; overflow: hidden; min-height: 170px; display: flex; flex-direction: column; align-items: center; }
.victory-character-canvas { width: 100%; min-height: 125px; height: 100%; flex: 1; display: block; }
.victory-character > b { position: absolute; bottom: 22px; font-size: 15px; color: #fff4d2; text-shadow: 0 1px 5px #000; }
.victory-character > span { position: absolute; bottom: 8px; font-size: 9px; letter-spacing: .17em; color: #e6c26e; }
.match-highlights { min-width: 0; overflow-y: auto; background: rgba(8,18,44,.95); border: 1px solid rgba(179,197,237,.35); border-radius: 14px; padding: 13px; color: #e7efff; }
.highlight-heading { text-align: center; font-weight: 900; letter-spacing: .14em; color: #ffe08a; font-size: 15px; margin-bottom: 9px; }
.highlight-finisher { display: flex; flex-direction: column; gap: 4px; padding: 10px 12px; background: rgba(230,194,110,.1); border-left: 3px solid #e6c26e; border-radius: 6px; }
.highlight-finisher span { color: #ffdf89; font-size: 10px; letter-spacing: .12em; font-weight: 800; }
.highlight-finisher b { color: #fff; font-size: 14px; }
.highlight-finisher em { font-size: 11px; color: #b9c6e6; }
.highlight-fighters { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px; margin-top: 10px; }
.highlight-fighter { background: rgba(47,65,111,.4); border: 1px solid rgba(170,194,255,.17); padding: 9px; border-radius: 8px; min-width: 0; }
.highlight-fighter strong { display: block; font-size: 13px; padding-bottom: 5px; overflow-wrap: anywhere; }
.highlight-fighter > div { display: flex; justify-content: space-between; gap: 8px; margin-top: 5px; font-size: 11px; }
.highlight-fighter > div span { color: #bac7e6; }
.highlight-fighter > div b { color: #fff; white-space: nowrap; }
@media (max-width: 620px) {
  .match-highlights-layout { grid-template-columns: 1fr; max-height: 50vh; overflow-y: auto; }
  .victory-character { display: none; }
  .highlight-fighters { grid-template-columns: 1fr 1fr; }
  .over:has(.match-highlights-layout) { justify-content: flex-start; padding-top: 8vh; }
}
'''

def select_root(arg):
    if arg: return Path(arg).expanduser().resolve()
    # On Windows, open a folder picker; terminal fallback works everywhere.
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        selected = filedialog.askdirectory(title='Select Fight Royale project folder (contains src)')
        root.destroy()
        if selected: return Path(selected).resolve()
    except Exception: pass
    return Path(input('Path to Fight Royale project folder: ').strip().strip('"')).expanduser().resolve()

def main():
    parser = argparse.ArgumentParser(description='Install animated roster + victory highlights into Fight Royale.')
    parser.add_argument('folder', nargs='?', help='Root folder containing src/game and src/ui')
    parser.add_argument('--check', action='store_true', help='Check patch compatibility without writing files')
    args = parser.parse_args()
    root = select_root(args.folder)
    targets = {
        Path('src/game/preview.ts'): patch_preview,
        Path('src/game/model.ts'): patch_model,
        Path('src/game/fighter.ts'): patch_fighter,
        Path('src/game/game.ts'): patch_game,
        Path('src/ui/GameView.tsx'): patch_ui,
        Path('src/app/globals.css'): patch_css,
    }
    pose = Path('src/game/presentation.ts')
    if not (root/'src/game/preview.ts').is_file() or not (root/'src/ui/GameView.tsx').is_file():
        raise PatchError('Not a Fight Royale project root. Select the folder containing src/game and src/ui.')
    updated = {}
    for rel, patch in targets.items():
        path = root / rel
        if not path.is_file(): raise PatchError(f'Missing required file: {rel}')
        raw = path.read_text(encoding='utf-8-sig')
        if TAG in raw: continue
        updated[rel] = (raw, patch(raw))
    presentation = zlib.decompress(base64.b64decode(POSE_B64)).decode('utf-8')
    if not (root/pose).exists(): updated[pose] = (None, presentation)
    elif TAG not in (root/pose).read_text(encoding='utf-8-sig'):
        raise PatchError('presentation.ts already exists and is not our version. No files changed.')
    if not updated:
        print('Already installed — no changes necessary.')
        return 0
    if args.check:
        print('Compatibility check passed; would update:', ', '.join(str(p) for p in updated))
        return 0
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = root / '.victory_highlights_backups' / stamp
    backup.mkdir(parents=True, exist_ok=True)
    completed = []
    try:
        for rel, (old, new) in updated.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if old is not None:
                bpath = backup / rel
                bpath.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, bpath)
            temp = path.with_name(path.name + '.installing')
            temp.write_text(new, encoding='utf-8', newline='')
            temp.replace(path)
            completed.append(rel)
    except Exception:
        for rel in reversed(completed):
            original = updated[rel][0]
            if original is None: (root/rel).unlink(missing_ok=True)
            else: (root/rel).write_text(original, encoding='utf-8')
        raise
    print('SUCCESS: Victory animations + match highlights installed.')
    print('Updated: ' + ', '.join(str(p) for p in updated))
    print('Original files backed up to: ' + str(backup))
    print('Restart the game dev server. No character damage, skills or cooldowns changed.')
    print('Note: Finishing moves are reported by name; this does not record gameplay video.')
    return 0

if __name__ == '__main__':
    try: sys.exit(main())
    except (PatchError, OSError, UnicodeError) as e:
        print('Installer stopped safely: ' + str(e), file=sys.stderr)
        sys.exit(1)
