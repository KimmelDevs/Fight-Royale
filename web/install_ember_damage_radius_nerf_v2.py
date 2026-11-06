#!/usr/bin/env python3
"""Fight Royale — Ember-only damage nerf + smaller charged-basic explosion/fire.

Run beside web/package.json:
  py install_ember_damage_radius_nerf_v2.py

Targets Ember gameplay after the Aster/Ember Final Ignition update (Combat V3).
Compatible with Ember Fire AI V1 (smaller patches) and the pre-avoidance radius
numbers. Leaves other characters, Veyr, Zarek, Aster, and AI untouched.

All validation runs before any file is changed. Timestamped backups are created.
Idempotent: a repeat run makes no changes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
GAME = 'src/game/game.ts'
KITS = 'src/game/kits.ts'
MARK = 'EMBER_DAMAGE_RADIUS_NERF_V2_20261106'


def exact_one(src: str, before: str, after: str, where: str) -> str:
    found = src.count(before)
    if found != 1:
        raise ValueError(f'{where}: expected one anchor {before[:110]!r}, found {found}')
    return src.replace(before, after, 1)


def one_regex(src: str, pattern: str, repl, where: str, flags: int = 0) -> str:
    new, n = re.subn(pattern, repl, src, flags=flags)
    if n != 1:
        raise ValueError(f'{where}: expected one match for {pattern[:115]!r}, found {n}')
    return new


def patch_kits(src: str) -> str:
    where = KITS
    if MARK in src:
        return src

    # Only fire mage basic projectiles get the reduction. Raven/Marina unchanged.
    src = exact_one(src,
        '  const t: Record<string, Attack> = {\n    l1: a({ type: "projectile",',
        f'  // {MARK}: Ember basic projectiles deal 15% less damage.\n'
        '  if (element === "fire") mul = 0.85;\n'
        '  const t: Record<string, Attack> = {\n    l1: a({ type: "projectile",',
        where)

    # Restrict replacements to Ember's own skill branch; no other mage is changed.
    before, branch, after = src.partition('  if (element === "fire") {\n')
    if not after:
        raise ValueError(f'{where}: Ember mage branch not found')
    ember, sep, rest = after.partition('  } else if (element === "electric") {')
    if not sep:
        raise ValueError(f'{where}: end of Ember mage branch not found')

    def skill(ident: str, damage: int, radius: float | None = None) -> None:
        nonlocal ember
        pat = rf'(    t\.{re.escape(ident)} = a\(\{{[^\n]*?\bdmg: )\d+('
        # no need for a complicated field scanner: each Ember skill is one line
        pat += r'[^\n]*\}\);)'
        m = re.search(pat, ember)
        if not m:
            raise ValueError(f'{where}: Ember {ident} skill definition not found')
        line = m.group(0)
        new_line = re.sub(r'\bdmg: \d+', f'dmg: {damage}', line, count=1)
        if radius is not None:
            if not re.search(r'\bradius: [\d.]+', new_line):
                raise ValueError(f'{where}: Ember {ident} radius missing')
            new_line = re.sub(r'\bradius: [\d.]+', f'radius: {radius:g}', new_line, count=1)
        ember = exact_one(ember, line, new_line, where + ':' + ident)

    skill('heavy', 155, 1.05)  # was 210 damage, 1.60 blast radius
    skill('z', 95)            # was 120
    skill('x', 31)            # was 40, each of five projectiles
    skill('c', 215)           # was 290
    src = before + '  if (element === "fire") {\n' + ember + sep + rest

    # 4s burn from Ember skills now ticks at 20/s (was 30/s), no changes to Vesper.
    src = one_regex(src,
        r'(\bfire: \["burn", 4, )30(, \["z", "x", "c", "v"\]\],)',
        r'\g<1>20\g<2>', where)
    return src


def patch_game(src: str) -> str:
    where = GAME
    if MARK in src:
        return src

    # Ground fire radius: only charged heavy, not Meteor. Compatible with either
    # new Ember avoidance patch or the earlier original fire-patch radii.
    radius = re.compile(r'(this\.spawnEmberPatch\(f, at, a\.id === "c" \? )([\d.]+)( : )([\d.]+)(\);)')
    matches = list(radius.finditer(src))
    if len(matches) != 1:
        raise ValueError(f'{where}: expected one Ember patch-radius call; found {len(matches)}')
    m = matches[0]
    meteor, heavy = float(m.group(2)), float(m.group(4))
    if not (0.5 <= meteor <= 2.5 and 0.7 <= heavy <= 1.6):
        raise ValueError(f'{where}: unexpected patch radii Meteor={meteor} Heavy={heavy}; no changes')
    src = src[:m.start()] + (m.group(1) + m.group(2) + m.group(3) + '0.65' + m.group(5)) + src[m.end():]

    # Passive ground fire ticks once per second. 26 -> 13 on-hit damage,
    # 18 -> 10 burn damage/s; no repeated stun or other hit reactions.
    src = one_regex(src,
        r'(id: "ember_ground", type: "strike",\s*\n\s*dmg: )26(, guard: 5, knock: 0, stun: 0, heavy: false,\s*\n\s*effect: "burn", effect_t: 3, effect_p: )18(, no_parry: true)',
        r'\g<1>13\g<2>10\g<3>', where)

    # Absolute Combustion has the same gathering and delayed beam animation but
    # lower base burst and stack bonuses (no other kit is affected).
    src = one_regex(src,
        r'(const bonus = Math\.min\(5, patches\.length\) \* )55( \+ Math\.min\(4, burned\.length\) \* )45(;)',
        r'\g<1>30\g<2>25\g<3>', where)
    src = one_regex(src,
        r'(const beamHit: Attack = \{ \.\.\.a, type: "strike", dmg: )320( \+ bonus,)',
        r'\g<1>240\g<2>', where)
    src = one_regex(src,
        r'(const beamHit: Attack = \{[^}]*?effect: "burn", effect_t: 4, effect_p: )30(, no_parry: true \};)',
        r'\g<1>20\g<2>', where, re.DOTALL)
    return '// ' + MARK + '\n' + src


def main() -> int:
    if not (ROOT / 'package.json').is_file():
        print('ERROR: put the installer in your web folder beside package.json', file=sys.stderr)
        return 1
    paths = {rel: ROOT / rel for rel in (KITS, GAME)}
    for rel, p in paths.items():
        if not p.is_file():
            print(f'ERROR: missing {rel}', file=sys.stderr)
            return 1
    original = {rel: p.read_text(encoding='utf-8') for rel, p in paths.items()}
    if all(MARK in original[rel] for rel in paths):
        print('Already installed. No changes made.'); return 0
    if any(MARK in original[rel] for rel in paths):
        print('ERROR: incomplete previous installation detected; no changes made', file=sys.stderr)
        return 1
    try:
        patched = {KITS: patch_kits(original[KITS]), GAME: patch_game(original[GAME])}
        if MARK not in patched[KITS] or MARK not in patched[GAME]:
            raise ValueError('Missing installation markers')
    except (ValueError, KeyError) as exc:
        print(f'ERROR: preflight stopped: {exc}. No files changed.', file=sys.stderr)
        return 1

    # Write backups and temporary files only after validation of BOTH files.
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    tmps = {}
    try:
        for rel, p in paths.items():
            backup = p.with_name(f'{p.name}.before_ember_damage_nerf_v2_{stamp}.bak')
            backup.write_text(original[rel], encoding='utf-8')
            temp = p.with_name(p.name + '.ember_nerf_tmp')
            temp.write_text(patched[rel], encoding='utf-8')
            tmps[rel] = (temp, backup)
        for rel, p in paths.items():
            tmps[rel][0].replace(p)
            print(f'PATCH {rel} (backup: {tmps[rel][1].name})')
    except OSError as exc:
        print(f'ERROR writing files: {exc}; backups are available', file=sys.stderr)
        return 1
    print('DONE. Ember-only damage nerf and smaller charged-heavy explosion/ground fire. Meteor fire radius unchanged.')
    print('Check: npx tsc --noEmit; npm run build; npm run dev')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
