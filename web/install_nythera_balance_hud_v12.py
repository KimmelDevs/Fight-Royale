#!/usr/bin/env python3
"""Fight Royale V12 -- restore compact CPU-vs-CPU HUD, rebalance Nythera.

Put in fight-royale/web and run:
    python install_nythera_balance_hud_v12.py
Or pass a path to the web directory as the first argument.

Standalone stdlib-only patch, designed for V10/V11. It preserves Nythera's
four air slices, gravity symbol, blade shape, and V11 AI. Creates .bak files.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys

TAG = 'NYTHERA_BALANCE_CPU_COMPACT_V12'

COMPACT_CPU = '''// NYTHERA_BALANCE_CPU_COMPACT_V12 -- restored pre-V10 compact CPU spectator HUD.
// Keep real live skill timers and passive counters, without descriptions.
function CpuSpectatorSkills({ data, side }: {
  data: NonNullable<NonNullable<Hud["spectatorSkills"]>["left"]>;
  side: "left" | "right";
}) {
  return (
    <section className={`cpu-spectator-column ${side}`} aria-label={`${side === "left" ? "CPU 1" : "CPU 2"} cooldowns and passives`}>
      <div className="cpu-spectator-heading">SKILL COOLDOWNS</div>
      <div className="cpu-spectator-slots">
        {data.slots.map((slot) => (
          <div className="cpu-spectator-skill" key={slot.key} title={slot.name}>
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
        <div className="cpu-spectator-passive" key={`${p.label}-${idx}`} title={p.desc || p.label}>
          <span>{p.label}</span><b>{p.value}</b>
        </div>
      )) : <div className="cpu-spectator-empty">No active stacks</div>}
    </section>
  );
}

'''


def once(s: str, old: str, new: str, what: str) -> str:
    n = s.count(old)
    if n != 1:
        raise ValueError(f'{what}: expected one source anchor, got {n}: {old[:85]!r}')
    return s.replace(old, new, 1)


def patch_view(s: str) -> str:
    if TAG in s:
        return s
    old_start = '/** CPU spectator: full skill names, explanations, live cooldowns and passive descriptions. */'
    old_end = '\nexport default function GameView('
    if old_start not in s:
        if 'function CpuSpectatorSkills(' in s and 'className="cpu-spectator-skill"' in s:
            return s  # Already uses compact layout; no changes required.
        raise ValueError('GameView.tsx: did not find V10 full-detail CPU spectator HUD')
    if s.count(old_start) != 1 or s.count(old_end) != 1:
        raise ValueError('GameView.tsx: spectator boundary not unique')
    a = s.index(old_start)
    b = s.index(old_end, a)
    s = s[:a] + COMPACT_CPU + s[b:]
    # Keep in-game player/opponent passive counters; these still render normally.
    s = once(s,
        'const speed = Math.min(2.4, 1 + stacks * 0.10);',
        'const speed = Math.min(1.7, 1 + stacks * 0.05);',
        'Dreadfall meter speed')
    s = once(s,
        'title="Dreadfall Tempo: every real damaging hit in Dreadfall earns +0.10x attack speed. Caps at 2.40x, persists through stance switches, resets next round. Block/parry/clash deny stacks."',
        'title="Dreadfall Tempo: every real damaging hit in Dreadfall earns +0.05x attack speed. Caps at 1.70x, persists through stance switches, resets next round. Block/parry/clash deny stacks."',
        'Dreadfall meter tooltip')
    return s


def patch_css(s: str) -> str:
    if TAG in s:
        return s
    block = '.cpu-spectator-column { top: 142px; width: clamp(224px, 25vw, 340px);'
    if block not in s:
        # The old, compact CSS already applies.
        if '.cpu-spectator-skill {' in s:
            return s
        raise ValueError('globals.css: neither old compact CSS nor V10 override found')
    if s.count(block) != 1:
        raise ValueError('globals.css: duplicate V10 spectator styles')
    a = s.index(block)
    mobile = '@media (max-width: 650px) {'
    m = s.find(mobile, a)
    if m < 0:
        raise ValueError('globals.css: missing V10 mobile override')
    # Match this CSS block's braces so we don't swallow unrelated rules.
    opening = s.index('{', m)
    depth = 1
    i = opening + 1
    while depth and i < len(s):
        if s[i] == '{': depth += 1
        elif s[i] == '}': depth -= 1
        i += 1
    if depth:
        raise ValueError('globals.css: unbalanced V10 mobile override')
    old_mobile = s[m:i]
    preserved = [line for line in old_mobile.splitlines() if line.lstrip().startswith(('.fr-passive-readouts', '.fr-passive-row', '.fr-passive-content'))]
    if len(preserved) != 3:
        raise ValueError('globals.css: cannot safely keep all 3 mobile passive-counter rules')
    replacement = '/* ' + TAG + ': compact spectator sizing restored; dark non-spectator passive counters retained. */\n'
    replacement += '@media (max-width: 650px) {\n' + '\n'.join(preserved) + '\n}'
    return s[:a] + replacement + s[i:]


def patch_fighter(s: str) -> str:
    if TAG in s:
        return s
    old = 'nytheraAttackSpeed(): number { return Math.min(2.4, 1 + Math.min(14, this.nytheraDreadfallHits) * 0.10); }'
    new = 'nytheraAttackSpeed(): number { return Math.min(1.7, 1 + Math.min(14, this.nytheraDreadfallHits) * 0.05); } // ' + TAG
    s = once(s, old, new, 'Nythera runtime Dreadfall speed')
    s = once(s,
        '// NYTHERA_AERIAL_DREADFALL_V9: +0.10x each real Dreadfall hit, capped at 2.40x for this round.',
        '// NYTHERA_AERIAL_DREADFALL_V9: V12 balance: +0.05x each real Dreadfall hit, capped at 1.70x for this round.',
        'Dreadfall speed declaration comment')
    s = once(s,
        '// Stored for the rest of the round, in either stance; caps at 2.40x.',
        '// Stored for the rest of the round, in either stance; caps at 1.70x.',
        'Dreadfall duration comment')
    return s


def patch_game(s: str) -> str:
    if TAG in s:
        return s
    # One authoritative damage scaling point: catches ordinary cuts, airborne
    # strikes, three-cut skill sequences, ultimate beats, and gravity collapse.
    # Only scythe-owned strikes are affected, never generic damage or DOT.
    s = once(s,
        '    const sentenceMult = heavySentence ? 1 + marks * 0.08 : 1;\n'
        '    const result = d.receiveHit(attacker, zenithAttack, (riposte ? power * 1.15 : power) * sentenceMult);',
        '    // ' + TAG + ': Dreadfall consumes marks for +5% each (max +25%).\n'
        '    const sentenceMult = heavySentence ? 1 + marks * 0.05 : 1;\n'
        '    // Match all Nythera attacks, including scheduled Z/X/V beats.\n'
        '    // The original attack data and visual contact events remain untouched.\n'
        '    const nytheraBasic = /^l[1-6]$/.test(a.id) || /^air_l[1-4]$/.test(a.id) || a.id === "heavy";\n'
        '    const balancedAttack = gravityOwner && a.dmg > 0\n'
        '      ? { ...zenithAttack, dmg: zenithAttack.dmg * (nytheraBasic ? 0.90 : 0.80) }\n'
        '      : zenithAttack;\n'
        '    const result = d.receiveHit(attacker, balancedAttack, (riposte ? power * 1.15 : power) * sentenceMult);',
        'All Nythera hit damage and Orbit bonus')
    s = once(s,
        'desc: "Orbit Marks last 25s; damaging Dreadfall strikes gain +0.10× attack speed, max 2.40× for the round. Can chain four air slices."',
        'desc: "Orbit Marks last 25s; Dreadfall strikes gain +0.05× attack speed, max 1.70× for the round. Four air slices remain. Base scythe attacks: −10% damage; skills: −20%."',
        'CPU passive detail text')
    return s


def find_web() -> Path:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1]).expanduser().resolve()
        if (path / 'src/game/game.ts').exists():
            return path
        raise FileNotFoundError(f'Not a Fight Royale web folder: {path}')
    here = Path(__file__).resolve().parent
    for path in (here, Path.cwd(), here / 'web', Path.cwd() / 'web'):
        if (path / 'src/game/game.ts').is_file() and (path / 'src/ui/GameView.tsx').is_file():
            return path.resolve()
    raise FileNotFoundError('Place installer in fight-royale/web, or pass the web folder path')


def main() -> int:
    try:
        web = find_web()
        jobs = [
            ('src/ui/GameView.tsx', patch_view),
            ('src/app/globals.css', patch_css),
            ('src/game/fighter.ts', patch_fighter),
            ('src/game/game.ts', patch_game),
        ]
        updates = []
        # Validate *everything* before touching any files.
        for rel, fn in jobs:
            p = web / rel
            if not p.is_file():
                raise FileNotFoundError(rel)
            old = p.read_text(encoding='utf-8')
            new = fn(old)
            if old != new:
                updates.append((p, rel, old, new))
        if not updates:
            print('Already installed / compact layout already present. No files changed.')
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        staged = []
        done = []
        try:
            for p, rel, old, new in updates:
                backup = p.with_name(f'{p.name}.before_{TAG}_{stamp}.bak')
                temp = p.with_name(f'{p.name}.{TAG}.tmp')
                backup.write_text(old, encoding='utf-8')
                temp.write_text(new, encoding='utf-8')
                staged.append((p, backup, temp, rel))
            for p, backup, temp, rel in staged:
                os.replace(temp, p)
                done.append((p, backup))
                print('UPDATED:', rel)
        except Exception:
            for p, backup in reversed(done):
                shutil.copy2(backup, p)
            raise
        finally:
            for p, backup, temp, rel in staged:
                if temp.exists():
                    temp.unlink()
        print('\nSUCCESS -- Nythera V12 + CPU spectator HUD restored')
        print('  Dreadfall: +0.05x per confirmed hit, max 1.70x at 14 hits (round only).')
        print('  Scythe basic/heavy/aerial: -10% damage; skills: -20% damage.')
        print('  Dreadfall Orbit Mark bonus: +5% each, five-mark cap (+25%).')
        print('  CPU vs CPU: original compact cooldown/passive columns, no long descriptions.')
        print('  Preserved: V11 Nythera AI, gravity icon, 10% shorter blade, four aerial slices.')
        print('  Backups stored beside each changed file.')
        print('Run: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as err:
        print('ERROR:', err)
        print('Installer validates anchors before writing; inspect your source/patch version.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
