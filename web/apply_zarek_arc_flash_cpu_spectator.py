#!/usr/bin/env python3
"""Fight Royale: restore Zarek V name (Arc Flash) + CPU-vs-CPU two-side cooldown/passive HUD.

Usage (from your game's web folder):
    python apply_zarek_arc_flash_cpu_spectator.py
or:
    python apply_zarek_arc_flash_cpu_spectator.py C:/path/to/web

Only touches src/game/kits.ts, src/game/ai.ts, src/game/game.ts,
src/ui/GameView.tsx, and src/app/globals.css. It backs up files automatically.
Requires the fourth-skill update, and preserves Zarek's current dash behavior.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

TAG = 'ZAREK_ARC_FLASH_CPU_SPECTATOR_COOLDOWNS_20261107_V1'
FILES = {
    'src/game/kits.ts': 'kits',
    'src/game/ai.ts': 'ai',
    'src/game/game.ts': 'game',
    'src/ui/GameView.tsx': 'view',
    'src/app/globals.css': 'css',
}


def once(src: str, old: str, new: str, label: str) -> str:
    amount = src.count(old)
    if amount != 1:
        raise RuntimeError(f'{label}: expected one matching code block but found {amount}. Nothing changed.')
    return src.replace(old, new, 1)


def patch_kits(s: str) -> str:
    if TAG in s: return s
    s = once(s, 'case "glaive":\n      return a({ name: "Thunderclap Flash",',
             'case "glaive":\n      return a({ name: "Arc Flash",',
             'Restore original V name, retain glaive_thunderflash style')
    return f'// {TAG}\n' + s


def patch_ai(s: str) -> str:
    if TAG in s: return s
    s = once(s, 'if (name === "Thunderclap Flash") points += distance > 2.4 && distance < 9.5 ? 2.6 : -0.9;',
             'if (name === "Arc Flash") points += distance > 2.4 && distance < 9.5 ? 2.6 : -0.9;',
             'Keep Zarek dash AI selection under restored name')
    return f'// {TAG}\n' + s


SPECTATOR_DETAILS = '''    // CPU VS CPU: read both fighters, not just the local HUD's fighter.
    // Timers come from their authoritative live cooldowns, including Master AI's V.
    const spectatorDetail = (f: Fighter | null, rival: Fighter | null) => {
      if (!f) return null;
      const slots = ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])].map((key) => {
        const a = !f.onGround && f.attacks[key + "_air"] ? f.attacks[key + "_air"] : f.attacks[key];
        let cd = Math.max(0, f.cooldowns[key] ?? 0);
        let max = Math.max(0.01, f.attacks[key].cd * f.cdMult);
        if (f.kit === "hammer" && a.style === "nesa_heart_slam") {
          cd = f.nesaCCharges > 0 ? 0 : f.nesaCRechargeT;
          max = Math.max(0.01, 7.5 * f.cdMult);
        }
        if (f.kit === "chainblade" && f.chainBindT > 0) {
          if (key === "z" || key === "x") cd = 0;
          else cd = Math.max(cd, f.chainBindT);
        }
        if (f.bloodFestivalT > 0) cd = Math.max(cd, f.bloodFestivalT);
        return { key, icon: a.id, cd, max };
      });
      const passives: Array<{ label: string; value: string }> = [];
      if (f.look.name === "Zarek") {
        passives.push({ label: "CLASH", value: `${f.clashMomentum} · ${Math.min(2, 1 + Math.min(5, f.clashMomentum) * 0.2).toFixed(1)}×` });
      }
      if (f.look.name === "Garrick") {
        passives.push({ label: "RESOLVE", value: `${f.garrickResolve}/3` });
      }
      if (f.kit === "sickle") {
        passives.push({ label: f.bloodFrenzyT > 0 ? "FRENZY" : "BLOODLUST",
          value: f.bloodFrenzyT > 0 ? `${f.bloodFrenzyT.toFixed(1)}s` : `${Math.round(f.bloodlust)}/100` });
        if (f.bloodFestivalT > 0) passives.push({ label: "FESTIVAL", value: `${f.bloodFestivalT.toFixed(1)}s` });
      }
      if (f.kit === "hammer") passives.push({ label: "HEARTS", value: `${f.nesaCCharges}/3` });
      if (f.kit === "bomb") passives.push({ label: "MINES", value: `${f.bobMineCharges}/4` });
      if (f.look.name === "Aster" && rival && rival.status.stacks("weaken") > 0)
        passives.push({ label: "WEAKEN", value: `×${rival.status.stacks("weaken")}/5` });
      if (f.kit === "chainblade" && f.chainBindT > 0)
        passives.push({ label: "BIND", value: `${f.chainBindT.toFixed(1)}s` });
      if (f.perfectDodgeCounterT > 0)
        passives.push({ label: "RIPOSTE", value: `${f.perfectDodgeCounterT.toFixed(1)}s` });
      if (f.nyxShadowBoostT > 0)
        passives.push({ label: "SHADOW", value: `${f.nyxShadowBoostT.toFixed(1)}s` });
      if (f.rageT > 0) passives.push({ label: "DMG BUFF", value: `${f.rageT.toFixed(1)}s` });
      if (f.judgmentT > 0) passives.push({ label: "BUFF", value: `${f.judgmentT.toFixed(1)}s` });
      return { slots, passives, kit: f.kit, element: f.look.element, glow: f.look.glow };
    };
'''


def patch_game(s: str) -> str:
    if TAG in s: return s
    if 'FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER' not in s:
        raise RuntimeError('Game missing earlier fourth-skill update. Apply apply_fourth_skill_roster.py first.')
    s = once(s, '    const info = (f: Fighter) => ({', SPECTATOR_DETAILS + '    const info = (f: Fighter) => ({',
             'Insert live spectator info builder into Game.hud')
    s = once(s, '      other: other ? { ...info(other), tag: isCpu(other.owner) ? `CPU - ${LEVELS[this.cfg.difficulty ?? 1]}` : "" } : null,',
             '      other: other ? { ...info(other), tag: isCpu(other.owner) ? `CPU - ${LEVELS[this.cfg.difficulty ?? 1]}` : "" } : null,\n'
             '      spectatorSkills: this.cfg.spectator && !this.plat\n'
             '        ? { left: spectatorDetail(me, other), right: spectatorDetail(other, me) } : null,',
             'Expose both duelists skill timers and passives to spectator HUD')
    return f'// {TAG}\n' + s


SPECTATOR_COMPONENT = '''/** CPU-only compact column: skill icons, keys and countdowns, never skill names. */
function CpuSpectatorSkills({ data, side }: {
  data: NonNullable<NonNullable<Hud["spectatorSkills"]>["left"]>;
  side: "left" | "right";
}) {
  return (
    <section className={`cpu-spectator-column ${side}`} aria-label={`${side === "left" ? "CPU 1" : "CPU 2"} cooldowns and passives`}>
      <div className="cpu-spectator-heading">SKILL COOLDOWNS</div>
      <div className="cpu-spectator-slots">
        {data.slots.map((slot) => (
          <div className="cpu-spectator-skill" key={slot.key}>
            <Icon src={skillIcon(data.kit, data.element, slot.icon)} alt={`${slot.key.toUpperCase()} icon`} size={25} />
            <b>{slot.key.toUpperCase()}</b>
            <strong className={slot.cd <= 0.05 ? "ready" : "waiting"}>
              {slot.cd <= 0.05 ? "0.0s" : `${slot.cd.toFixed(1)}s`}
            </strong>
          </div>
        ))}
      </div>
      <div className="cpu-spectator-heading passive">PASSIVE</div>
      {data.passives.length ? data.passives.map((p, idx) => (
        <div className="cpu-spectator-passive" key={`${p.label}-${idx}`}>
          <span>{p.label}</span><b>{p.value}</b>
        </div>
      )) : <div className="cpu-spectator-empty">No active stacks</div>}
    </section>
  );
}

'''


def patch_view(s: str) -> str:
    if TAG in s: return s
    if 'const SKILL_ACTION: Record<string, Action>' not in s:
        raise RuntimeError('GameView missing fourth-skill HUD update. Apply apply_fourth_skill_roster.py first.')
    s = once(s, 'export default function GameView({ cfg, net, onExit, matchId, bet, team }: {',
             SPECTATOR_COMPONENT + 'export default function GameView({ cfg, net, onExit, matchId, bet, team }: {',
             'Insert reusable CPU spectator column component')
    s = once(s, '          {hud.mode === "team" && (\n            <div className="team foes">',
             '''          {cfg.spectator && !hud.plat && hud.spectatorSkills?.left && (
            <CpuSpectatorSkills data={hud.spectatorSkills.left} side="left" />
          )}
          {cfg.spectator && !hud.plat && hud.spectatorSkills?.right && (
            <CpuSpectatorSkills data={hud.spectatorSkills.right} side="right" />
          )}
          {hud.mode === "team" && (
            <div className="team foes">''',
             'Place both spectator columns beside player health indicators')
    return f'// {TAG}\n' + s


CSS_BLOCK = '''
/* CPU vs CPU observer HUD: compact independent left/right timers with real passive counters. */
.cpu-spectator-column {
  position: absolute;
  top: 124px;
  width: clamp(136px, 15vw, 188px);
  padding: 9px 10px;
  border: 1px solid rgba(173, 212, 255, .43);
  border-radius: 11px;
  background: rgba(8, 18, 40, .77);
  backdrop-filter: blur(5px);
  color: #f8faff;
  z-index: 4;
  text-align: left;
  text-shadow: 0 1px 2px #000;
  font-variant-numeric: tabular-nums;
}
.cpu-spectator-column.left { left: 24px; border-left: 3px solid #75bcff; }
.cpu-spectator-column.right { right: 24px; border-right: 3px solid #ff9c98; }
.cpu-spectator-heading {
  font-weight: 850;
  font-size: 10px;
  color: #dce9ff;
  letter-spacing: .065em;
  margin-bottom: 7px;
}
.cpu-spectator-heading.passive {
  margin: 8px 0 4px;
  padding-top: 7px;
  border-top: 1px solid rgba(230, 239, 255, .23);
}
.cpu-spectator-slots { display: flex; flex-direction: column; gap: 4px; }
.cpu-spectator-skill { display: grid; grid-template-columns: 25px 16px 1fr; gap: 5px; align-items: center; font-size: 12px; }
.cpu-spectator-skill > b { font-size: 11px; color: #d8e1fd; }
.cpu-spectator-skill > strong { justify-self: end; font-size: 12px; }
.cpu-spectator-skill .ready { color: #aaf0ac; }
.cpu-spectator-skill .waiting { color: #ffe28e; }
.cpu-spectator-passive { display: flex; gap: 6px; justify-content: space-between; align-items: baseline; font-size: 10px; padding: 2px 0; }
.cpu-spectator-passive > span { color: #aec4e7; }
.cpu-spectator-passive > b { color: #fff1be; font-size: 11px; white-space: nowrap; }
.cpu-spectator-empty { font-size: 10px; color: #b8c6da; }
@media (max-width: 650px) {
  .cpu-spectator-column { top: 116px; width: 115px; padding: 6px 5px; }
  .cpu-spectator-column.left { left: 6px; }
  .cpu-spectator-column.right { right: 6px; }
  .cpu-spectator-heading { font-size: 8px; }
  .cpu-spectator-skill { grid-template-columns: 22px 12px 1fr; gap: 3px; font-size: 10px; }
  .cpu-spectator-skill > b, .cpu-spectator-skill > strong { font-size: 10px; }
  .cpu-spectator-passive { font-size: 9px; }
  .cpu-spectator-passive > b { font-size: 9px; }
}
'''


def patch_css(s: str) -> str:
    if TAG in s: return s
    return f'/* {TAG} */\n' + s + '\n' + CSS_BLOCK


def find_root(path: Path) -> Path:
    for p in (path, path / 'web'):
        if all((p / rel).is_file() for rel in FILES): return p
    raise RuntimeError('Could not locate a web project with src/game/kits.ts and src/ui/GameView.tsx.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', nargs='?', default='.', help='Web game folder or its parent')
    args = parser.parse_args()
    try:
        root = find_root(Path(args.project).expanduser().resolve())
        patches = {'kits': patch_kits, 'ai': patch_ai, 'game': patch_game, 'view': patch_view, 'css': patch_css}
        changes: list[tuple[Path, str]] = []
        for rel, kind in FILES.items():
            path = root / rel
            old = path.read_text(encoding='utf-8')
            new = patches[kind](old)
            if old != new:
                changes.append((path, new))
        if not changes:
            print('Already installed: Arc Flash + CPU spectator columns.')
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for path, _ in changes:
            shutil.copy2(path, path.with_name(f'{path.name}.before_cpu_columns_{stamp}.bak'))
        for path, new in changes:
            path.write_text(new, encoding='utf-8')
        print('Updated:', ', '.join(str(p.relative_to(root)) for p, _ in changes))
        print('Restored Zarek V name: Arc Flash (dash animation, damage and hit mechanics unchanged).')
        print('CPU vs CPU: both sides now show Z/X/C/(Master V) live skill cooldowns and passives.')
        print('Backups saved beside changed files. This installer is safe to run again.')
        return 0
    except (OSError, RuntimeError) as ex:
        print(f'Patch could not be applied: {ex}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
