#!/usr/bin/env python3
"""Fight Royale: fixed Z/X/C skills + purchased V, Master-only AI V, 2-row scroll roster.

Place in the web folder and run: python apply_fourth_skill_roster.py
Or provide the path explicitly: python apply_fourth_skill_roster.py C:/path/to/web
No third-party Python dependencies. Takes timestamped backups before writing.
Works with the earlier Marina/Raven/Zarek/Bob and projectile-clash patches.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

TAG = "FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1"


def replace(s: str, old: str, new: str, desc: str) -> str:
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f"{desc}: expected 1 exact code anchor, found {count}. Nothing has been written.")
    return s.replace(old, new, 1)


def patch_account(s: str) -> str:
    s = replace(s, '  CHARACTER_PRICE, SKILL_PRICE, EMBLEM_MAX, emblemCost, guestProfile, START_CHARACTERS, type Profile,',
        '  CHARACTER_PRICE, EMBLEM_MAX, emblemCost, guestProfile, START_CHARACTERS, type Profile,',
        'account cleanup unused price import')
    s = replace(s,
        '  ownsSkill(charId: string) { return this.profile.skills.includes(charId); }',
        '  /** Fourth skills require a real signed-in purchase; old guest purchases never count. */\n'
        '  ownsSkill(charId: string) { return this.signedIn && !this.loading && !this.loadError && this.profile.skills.includes(charId); }',
        'account purchase ownership')
    s = replace(s,
        '  loadout(charId: string) { return this.profile.loadouts[charId] ?? ["z", "x", "c"]; }',
        '  /** Legacy custom loadouts are intentionally ignored: Z/X/C are always the core skills. */\n'
        '  loadout(_charId: string) { return ["z", "x", "c"]; }',
        'account fixed default loadout')
    start = '''  async buySkill(charId: string, currency: "gold" | "diamonds") {
    if (this.signedIn) return this.rpc("buy_skill", { p_char: charId, p_currency: currency });
    if (currency !== "gold") throw new Error("Sign in to use diamonds");
    if (this.profile.gold < SKILL_PRICE.gold) throw new Error("not enough gold");
    this.profile.gold -= SKILL_PRICE.gold;
    this.profile.skills = [...this.profile.skills, charId];
    this.saveGuest();
  }'''
    s = replace(s, start, '''  async buySkill(charId: string, currency: "gold" | "diamonds") {
    if (!this.signedIn || this.loading || this.loadError)
      throw new Error("Sign in and load your account to unlock fourth skills");
    return this.rpc("buy_skill", { p_char: charId, p_currency: currency });
  }''', 'account guest V buying blocked')
    s = replace(s,
        '    return { loadout: this.loadout(id), emblem: { id: this.profile.emblem, level: this.emblemLevel(this.profile.emblem) } };',
        '    return { loadout: ["z", "x", "c"], bonusSkillUnlocked: this.ownsSkill(id), emblem: { id: this.profile.emblem, level: this.emblemLevel(this.profile.emblem) } };',
        'account match V flag')
    return s


def patch_shop(s: str) -> str:
    s = replace(s,
        '                {owned ? <em>Unlocked - equip it in character select</em> : (',
        '                {owned ? <em>Unlocked - use the V key in battle</em> : !acc.signedIn ? (\n'
        '                  <button className="buy" onClick={onAccount}>Sign in to unlock V</button>\n'
        '                ) : (',
        'shop V purchased display / guests')
    return s


def patch_keys(s: str) -> str:
    s = replace(s,
        '"skill1" | "skill2" | "skill3";',
        '"skill1" | "skill2" | "skill3" | "skill4";',
        'keys action type')
    s = replace(s,
        '  { id: "skill3", label: "Skill 3" },',
        '  { id: "skill3", label: "Skill 3" },\n  { id: "skill4", label: "Skill 4 (unlocked V)" },',
        'keys action listing')
    s = replace(s,
        '  skill3: ["KeyC", ""],',
        '  skill3: ["KeyC", ""],\n  skill4: ["KeyV", ""],',
        'keys V default')
    return s


def patch_input(s: str) -> str:
    return replace(s,
        'const SKILL_KEY: Partial<Record<Action, string>> = { skill1: "z", skill2: "x", skill3: "c" };',
        'const SKILL_KEY: Partial<Record<Action, string>> = { skill1: "z", skill2: "x", skill3: "c", skill4: "v" };',
        'input V hotkey')


def patch_fighter(s: str) -> str:
    s = replace(s,
        '  cooldowns: Record<string, number> = { z: 0, x: 0, c: 0 };',
        '  cooldowns: Record<string, number> = { z: 0, x: 0, c: 0, v: 0 };\n'
        '  /** Game-controlled: purchased account V or Master CPU only. Never enabled for guests. */\n'
        '  bonusSkillUnlocked = false;',
        'fighter cooldown and V flag')
    s = replace(s, '''  /**
   * `loadout` picks which 3 of the kit's 4 skills sit on Z/X/C; `emblem` applies its stat bonus.
   */
  constructor(look: Look, charIndex: number, loadout: string[] = DEFAULT_LOADOUT, emblem?: { id: string; level: number }) {''',
        '''  /** Core skills never remap. V is independent, requiring a match-scoped unlock. */
  constructor(look: Look, charIndex: number, _loadout: string[] = DEFAULT_LOADOUT,
    emblem?: { id: string; level: number }, bonusSkillUnlocked = false) {
    this.bonusSkillUnlocked = bonusSkillUnlocked;''',
        'fighter independent V constructor')
    s = replace(s, '''    const pool = { z: this.attacks.z, x: this.attacks.x, c: this.attacks.c, v: this.attacks.v } as Record<string, Attack>;
    const slots = loadout.length === 3 && new Set(loadout).size === 3 && loadout.every((k) => pool[k]) ? loadout : DEFAULT_LOADOUT;
    const airPool = { z: this.attacks.z_air, x: this.attacks.x_air, c: this.attacks.c_air, v: this.attacks.v_air } as Record<string, Attack | undefined>;
    ["z", "x", "c"].forEach((key, i) => {
      this.attacks[key] = pool[slots[i]];
      // The air version follows the skill wherever the loadout puts it.
      const air = airPool[slots[i]];
      if (air) this.attacks[key + "_air"] = air; else delete this.attacks[key + "_air"];
    });
''',
        '''    // Keep Kits.attacks' original Z, X, C and V definitions, including air variants.
    // Previously saved 3-of-4 loadouts are ignored rather than remapping V to another key.
''',
        'fighter remove old 3-skill selection logic')
    s = replace(s,
        '    const k = this.intent.skill;\n    if (!k) return;',
        '    const k = this.intent.skill;\n    if (!k || !["z", "x", "c", "v"].includes(k)) return;\n'
        '    // Prevent key spoofing, old remapped skills and online requests from using locked V.\n'
        '    if (k === "v" && !this.bonusSkillUnlocked) return;',
        'fighter combat-verified V gate')
    s = replace(s,
        '      +this.kaizenSpinSpeed.toFixed(2), this.kaizenSpinDirection, this.garrickResolve];',
        '      +this.kaizenSpinSpeed.toFixed(2), this.kaizenSpinDirection, this.garrickResolve, +this.cooldowns.v.toFixed(2)];',
        'fighter snapshot V cooldown')
    s = replace(s,
        '    this.cooldowns.z = s[14]; this.cooldowns.x = s[15]; this.cooldowns.c = s[16];',
        '    this.cooldowns.z = s[14]; this.cooldowns.x = s[15]; this.cooldowns.c = s[16];\n'
        '    this.cooldowns.v = s.length > 52 ? s[52] : 0;',
        'fighter remote V cooldown')
    return s


def patch_game(s: str) -> str:
    s = replace(s, 'import { CHARACTERS } from "./roster";',
        'import { CHARACTERS } from "./roster";\nimport { account } from "@/lib/account";',
        'game local account verification')
    s = replace(s,
        '  /** Which 3 of the character\'s 4 skills go on Z/X/C. */\n  loadout?: string[];',
        '  /** Legacy, ignored by the fighter: Z/X/C are now fixed. */\n  loadout?: string[];\n'
        '  /** Match-scoped fourth-skill entitlement; independent of Z/X/C. */\n  bonusSkillUnlocked?: boolean;',
        'game PlayerSlot V type')
    s = replace(s,
        '    const f = new Fighter(CHARACTERS[slot.char].look, slot.char, slot.loadout, slot.emblem);',
        '    const mayUseV = isCpu(slot.peer) ? this.cfg.difficulty === 3\n'
        '      : slot.peer === this.cfg.localPeer && this.cfg.role !== "client"\n'
        '        ? account.ownsSkill(CHARACTERS[slot.char].id)\n'
        '        : slot.bonusSkillUnlocked === true;\n'
        '    const f = new Fighter(CHARACTERS[slot.char].look, slot.char, slot.loadout, slot.emblem, mayUseV);',
        'game Master AI exclusive V')
    s = replace(s,
        'rotY, slot.loadout ?? null, slot.emblem ?? null]);',
        'rotY, slot.loadout ?? null, slot.emblem ?? null, f.bonusSkillUnlocked]);',
        'game replicated spawn V permission')
    s = replace(s,
        '    const slot: PlayerSlot = { peer, name: String(msg.name ?? "Player").slice(0, 16), char: msg.char ?? 0, loadout: msg.loadout, emblem: msg.emblem };',
        '    const slot: PlayerSlot = { peer, name: String(msg.name ?? "Player").slice(0, 16), char: msg.char ?? 0, loadout: msg.loadout, emblem: msg.emblem, bonusSkillUnlocked: msg.bonusSkillUnlocked === true };',
        'game late join fourth skill')
    s = replace(s,
        'f.root.rotation.y, s?.loadout ?? null, s?.emblem ?? null]);',
        'f.root.rotation.y, s?.loadout ?? null, s?.emblem ?? null, f.bonusSkillUnlocked]);',
        'game initial-state V permission')
    s = replace(s,
        'loadout: ev[9] ?? undefined, emblem: ev[10] ?? undefined }, ev[3]',
        'loadout: ev[9] ?? undefined, emblem: ev[10] ?? undefined, bonusSkillUnlocked: ev[11] === true }, ev[3]',
        'game remote spawn V permission')
    s = replace(s,
        '      skills: me ? ["z", "x", "c"].map((k) => {',
        '      skills: me ? ["z", "x", "c", ...(me.bonusSkillUnlocked ? ["v"] : [])].map((k) => {',
        'game V HUD slot')
    return s


def patch_ai(s: str) -> str:
    s = replace(s,
        '  for (const key of ["z", "x", "c"]) {\n    const a = f.attacks[key];',
        '  for (const key of ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]) {\n    const a = f.attacks[key];',
        'Master AI skill evaluation includes V')
    s = replace(s,
        '    let points = profile.skillBias[key === "z" ? 0 : key === "x" ? 1 : 2];',
        '    let points = key === "v" ? 1.55 : profile.skillBias[key === "z" ? 0 : key === "x" ? 1 : 2];',
        'AI V bias')
    s = replace(s,
        '      viable = a.mode === "counter" || a.mode === "blood_feint"\n        ? attackComing && close\n        : a.mode === "ward" ? close || f.hp < f.maxHp * 0.55\n        : a.mode === "blood_festival" ? distance < 3.4\n        : f.hp < f.maxHp * 0.72;',
        '      viable = a.mode === "counter" || a.mode === "blood_feint"\n        ? attackComing && close\n        : a.mode === "ward" ? close || f.hp < f.maxHp * 0.55\n        : a.mode === "blood_festival" ? distance < 3.4\n        : a.mode === "healing_water" ? f.hp < f.maxHp * 0.82\n        : a.mode === "static_field" ? distance < a.radius + 0.4\n        : f.hp < f.maxHp * 0.72;',
        'AI V buff behavior for Marina/Raven')
    s = replace(s,
        '    const ready = ["z", "x", "c"].filter(k =>',
        '    const ready = ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])].filter(k =>',
        'AI proactive V scans')
    # The V move may be chosen by personalizedSkill and also by theatrical skill identity.
    s = replace(s,
        '    const key = ["z", "x", "c"].find(k =>\n      f.attacks[k]?.name === name && (f.cooldowns[k] ?? 1) <= 0);',
        '    const key = ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])].find(k =>\n      f.attacks[k]?.name === name && (f.cooldowns[k] ?? 1) <= 0);',
        'AI theatrical V move lookup')
    return s


def patch_select(s: str) -> str:
    start = s.index('/**\n * Pick which 3 of the 4 skills go on Z / X / C.')
    end = s.index('/** Pick the emblem to bring into the match', start)
    old = s[start:end]
    new = '''/** Skills are fixed: the purchased fourth skill gets its own V button. No on/off toggles. */
function SkillSummary({ index }: { index: number }) {
  const acc = useAccount();
  const ch = CHARACTERS[index];
  const atks = Kits.attacks(ch.look.kit, ch.look.element);
  const canV = acc.ownsSkill(ch.id);
  return (
    <div className="skill-summary">
      {(["z", "x", "c", "v"] as const).map((k) => (
        <div key={k} className={"skill-summary-row" + (k === "v" && !canV ? " locked" : "")}>
          <Icon src={skillIcon(ch.look.kit, ch.look.element, k)} alt={atks[k].name} size={32} />
          <span><b>[{k.toUpperCase()}] {atks[k].name}</b><small>{k === "v" && !canV
            ? acc.signedIn ? "LOCKED - Buy in the Shop" : "LOCKED - Sign in and buy in the Shop"
            : `${atks[k].cd}s cooldown${k === "v" ? " - UNLOCKED" : ""}`}</small></span>
        </div>
      ))}
    </div>
  );
}

'''
    if s.count(old) != 1: raise RuntimeError('select skill editor locating failed')
    s = s[:start] + new + s[end:]
    s = replace(s,
        '/** Last step before a match: emblem and skill loadout for the chosen fighter. */',
        '/** Last step before a match: emblem and fixed skills for the chosen fighter. */',
        'selection prepare caption')
    s = replace(s,
        '      <LoadoutEditor index={index} />',
        '      <SkillSummary index={index} />',
        'selection prepare static skills')
    s = replace(s,
        '      <p className="small">Upgrade emblems and unlock bonus skills in the Shop.</p>',
        '      <p className="small">Z / X / C are always available. Unlock V in the Shop while signed in.</p>',
        'selection prepare explanation')
    # Do not build a different Z/X/C loadout for the inspect panel.
    s = replace(s,
        '        const slots = editable && acc.owns(ch.id) ? acc.loadout(ch.id) : ["z", "x", "c"];\n        return ["Z", "X", "C"].map((key, i) => {',
        '        const slots = ["z", "x", "c", "v"];\n        return ["Z", "X", "C", "V"].map((key, i) => {',
        'selection InfoPanel fourth ability')
    s = replace(s,
        '          return <div key={key} className="skill"><b>[{key}] {a.name}</b> - {a.desc} <em>({a.cd}s)</em>',
        '          return <div key={key} className="skill"><b>[{key}] {a.name}</b>{key === "V" && !acc.ownsSkill(ch.id) ? " - LOCKED (Shop, sign-in required)" : ` - ${a.desc}`} <em>({a.cd}s)</em>',
        'selection locked V description')
    s = replace(s,
        '      {editable && acc.owns(ch.id) && <LoadoutEditor index={index} />}',
        '      {editable && acc.owns(ch.id) && <div className="small">Skills are fixed to Z / X / C / V; V requires a signed-in purchase.</div>}',
        'selection editor removal')
    s = replace(s,
        '          : step === prepStep ? "Pick your emblem and which 3 skills to bring. Enter: fight."',
        '          : step === prepStep ? "Pick your emblem. Z/X/C are fixed; V unlocks after purchase. Enter: fight."',
        'selection prep intro')
    s = replace(s,
        '  const acc = useAccount();\n  return (\n    <div className="cards">',
        '''  const acc = useAccount();
  const gridRef = useRef<HTMLDivElement>(null);
  // Keyboard selection stays visible when the user moves beyond the first two rows.
  useEffect(() => {
    const grid = gridRef.current;
    const selected = grid?.querySelector<HTMLButtonElement>(".card.on");
    if (!grid || !selected) return;
    const top = selected.offsetTop, bottom = top + selected.offsetHeight;
    if (top < grid.scrollTop) grid.scrollTop = top;
    else if (bottom > grid.scrollTop + grid.clientHeight)
      grid.scrollTop = bottom - grid.clientHeight;
  }, [current]);
  return (
    <div className="cards" ref={gridRef}>''',
        'auto-scroll selected character')
    return s


def patch_gameview(s: str) -> str:
    s = replace(s,
        'const SKILL_ACTION: Record<string, Action> = { z: "skill1", x: "skill2", c: "skill3" };',
        'const SKILL_ACTION: Record<string, Action> = { z: "skill1", x: "skill2", c: "skill3", v: "skill4" };',
        'HUD V key mapping')
    old = '${label("skill1")} ${label("skill2")} ${label("skill3")} skills'
    new = '${label("skill1")} ${label("skill2")} ${label("skill3")} skills${hud.skills.some(s => s.key === "v") ? ` - ${label("skill4")} bonus V` : ""}'
    if s.count(old) != 2: raise RuntimeError(f'HUD hint anchors: expected 2 found {s.count(old)}')
    s = s.replace(old, new)
    return s


def patch_app(s: str) -> str:
    return replace(s,
        '          <span>{label("skill1")} {label("skill2")} {label("skill3")} skills</span><span>Esc: pause</span>',
        '          <span>{label("skill1")} {label("skill2")} {label("skill3")} core skills; {label("skill4")} unlocked 4th skill</span><span>Esc: pause</span>',
        'home controls V key')


def patch_lobby(s: str) -> str:
    s = replace(s,
        'list.push({ peer: from, name: String(msg.name).slice(0, 16), char: msg.char ?? 0, team: t0 <= t1 ? 0 : 1, loadout: msg.loadout, emblem: msg.emblem });',
        'list.push({ peer: from, name: String(msg.name).slice(0, 16), char: msg.char ?? 0, team: t0 <= t1 ? 0 : 1, loadout: msg.loadout, emblem: msg.emblem, bonusSkillUnlocked: msg.bonusSkillUnlocked === true });',
        'lobby peer join V entitlement')
    s = replace(s,
        'else if (msg.t === "pick") update(from, { char: msg.char, loadout: msg.loadout, emblem: msg.emblem });',
        'else if (msg.t === "pick") update(from, { char: msg.char, loadout: msg.loadout, emblem: msg.emblem, bonusSkillUnlocked: msg.bonusSkillUnlocked === true });',
        'lobby peer switch character V entitlement')
    return s


def patch_ranked(s: str) -> str:
    return replace(s,
        'loadout: msg.loadout, emblem: msg.emblem };',
        'loadout: msg.loadout, emblem: msg.emblem, bonusSkillUnlocked: msg.bonusSkillUnlocked === true };',
        'ranked peer join V entitlement')


def patch_css(s: str) -> str:
    css = r'''
/* FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1
   Two visible rows and a vertical scrollbar; more fighters remain selectable. */
.cards {
  display: grid;
  position: relative;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  grid-auto-rows: 96px;
  gap: 6px;
  flex: 0 1 670px;
  width: min(70%, 670px);
  max-width: min(70%, 670px);
  height: 202px;
  max-height: 202px;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: #e6c26e rgba(12, 22, 52, .45);
  padding: 2px 7px 2px 2px;
  align-content: start;
}
.cards::-webkit-scrollbar { width: 9px; }
.cards::-webkit-scrollbar-thumb { background: #e6c26e; border-radius: 12px; }
.cards::-webkit-scrollbar-track { background: rgba(12, 22, 52, .45); border-radius: 12px; }
.cards .card { width: 100%; height: 96px; min-height: 0; box-sizing: border-box; }
.skill-summary { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
.skill-summary-row { display: flex; align-items: center; gap: 7px; padding: 7px;
  border: 1px solid rgba(255,255,255,.25); border-radius: 9px; background: rgba(255,255,255,.055); }
.skill-summary-row.locked { opacity: .58; }
.skill-summary-row > span { display: flex; flex-direction: column; min-width: 0; }
.skill-summary-row b { font-size: 12px; }
.skill-summary-row small { color: #ffe08a; font-size: 11px; }
@media (max-width: 800px) {
  .cards { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); grid-auto-rows: 92px;
    width: 100%; max-width: 100%; height: 194px; max-height: 194px; overflow-y: auto; overflow-x: hidden; }
  .cards .card { width: 100%; height: 92px; min-height: 0; flex: auto; }
  .panel { bottom: 280px; max-height: 26vh; }
  .skill-summary { grid-template-columns: 1fr; }
}
@media (max-width: 430px) {
  .cards { grid-template-columns: repeat(3, minmax(0,1fr)); }
  .actions .row { gap: 4px; }
}
'''
    return s + '\n' + css

PATCHES = {
    'src/lib/account.ts': patch_account,
    'src/ui/Shop.tsx': patch_shop,
    'src/game/keys.ts': patch_keys,
    'src/game/input.ts': patch_input,
    'src/game/fighter.ts': patch_fighter,
    'src/game/game.ts': patch_game,
    'src/game/ai.ts': patch_ai,
    'src/ui/Select.tsx': patch_select,
    'src/ui/GameView.tsx': patch_gameview,
    'src/ui/App.tsx': patch_app,
    'src/ui/Lobby.tsx': patch_lobby,
    'src/ui/Ranked.tsx': patch_ranked,
    'src/app/globals.css': patch_css,
}


def locate(path: Path) -> Path:
    for root in [path, path / 'web', path.parent / 'web']:
        if (root.joinpath('src/game/fighter.ts').is_file() and root.joinpath('src/ui/Select.tsx').is_file()):
            return root
    raise RuntimeError('Cannot find the game web folder. Run from web or pass a path to web.')


def apply(root: Path):
    root = locate(root)
    changes = {}
    applied = []
    for relative, transform in PATCHES.items():
        p = root / relative
        if not p.is_file(): raise RuntimeError(f'Missing required file: {p}')
        old = p.read_text(encoding='utf-8')
        if TAG in old:
            applied.append(relative)
            continue
        new = transform(old)
        if new == old: raise RuntimeError(f'Nothing changed in {relative}')
        if relative != 'src/app/globals.css':
            new = '// ' + TAG + '\n' + new
        changes[p] = new
    if applied and changes:
        raise RuntimeError('Found a partially installed update. Restore backups first: ' + ', '.join(applied))
    if not changes:
        print('Already installed: ' + TAG)
        return
    # Atomic validation in memory: nothing is written if any expected anchor is missing.
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for p in changes:
        backup = p.with_name(p.name + f'.before_fourth_skill_{stamp}.bak')
        shutil.copy2(p, backup)
    for p, new in changes.items():
        p.write_text(new, encoding='utf-8')
        print('Updated:', p.relative_to(root))
    print(f'Done. Updated {len(changes)} files. Original files backed up with .before_fourth_skill_{stamp}.bak')
    print('V = fourth skill for signed-in purchasers only; Master AI receives V. Roster is 2 rows with vertical scroll.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('web', nargs='?', default='.', help='Path to your web project folder')
    args = parser.parse_args()
    try: apply(Path(args.web).expanduser().resolve())
    except Exception as e:
        print('ERROR:', e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__': main()
