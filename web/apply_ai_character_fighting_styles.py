#!/usr/bin/env python3
"""Fight Royale AI #10 — Character-Specific Fighting Styles (17 fighters).

Run in fight-royale/web:
    python apply_ai_character_fighting_styles.py --dry-run
    python apply_ai_character_fighting_styles.py

Targets the source in the user's 2026-11-08 ZIP with AI #8/#9 applied.
Requires only Python 3.9+ standard library. Edits src/game/ai.ts only.
The installer validates every anchor before writing, makes a dated backup, and
can be run twice safely. No changes to player balance, cooldowns or hitboxes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from datetime import datetime
import shutil
import sys
import re

MARK = 'AI_CHARACTER_FIGHTING_STYLES_V1_20261108'

CONFIG = '''// CHARACTER_STYLES_V1: existing FIGHT_STYLES already holds base preferences.
// Add short-lived, observable tactical plans; never grant AI-only statistics.
// Each fighter has a distinct identity and unique mix of plans / V restraint.
type PersonalityRole =
  "counter" | "duelist" | "juggernaut" | "riposte" | "artillery" |
  "support" | "ambush" | "rush" | "skirmish" | "trapper" |
  "kickboxer" | "controller" | "sniper" | "executioner" |
  "glaive" | "grappler" | "bruiser";
type PersonalityPlan = "none" | "pressure" | "probe" | "reset";
type PersonalityProfile = {
  role: PersonalityRole;
  pressure: number; probe: number; reset: number;
  vReserve: number; spacing: number;
};
const CHARACTER_PERSONALITY: Readonly<Record<string, PersonalityProfile>> = {
  // pressure / probe / reset are relative tactical weights, not fixed chance per frame.
  aster:   { role: "counter",      pressure: 0.60, probe: 1.12, reset: 0.54, vReserve: 0.70, spacing:  0.05 },
  vesper:  { role: "duelist",     pressure: 1.35, probe: 0.68, reset: 0.34, vReserve: 0.65, spacing: -0.13 },
  garrick: { role: "juggernaut",  pressure: 1.13, probe: 0.66, reset: 0.24, vReserve: 0.62, spacing:  0.12 },
  kaede:   { role: "riposte",     pressure: 0.67, probe: 1.28, reset: 0.57, vReserve: 0.82, spacing:  0.18 },
  ember:   { role: "artillery",   pressure: 0.45, probe: 1.08, reset: 0.88, vReserve: 0.54, spacing:  0.30 },
  marina:  { role: "support",     pressure: 0.37, probe: 0.91, reset: 1.24, vReserve: 0.45, spacing:  0.27 },
  nyx:     { role: "ambush",      pressure: 1.04, probe: 1.01, reset: 0.50, vReserve: 0.92, spacing: -0.22 },
  rook:    { role: "rush",        pressure: 1.83, probe: 0.36, reset: 0.17, vReserve: 0.35, spacing: -0.32 },
  gale:    { role: "skirmish",    pressure: 1.02, probe: 1.04, reset: 0.47, vReserve: 0.65, spacing: -0.04 },
  bob:     { role: "trapper",     pressure: 0.37, probe: 1.43, reset: 0.96, vReserve: 0.67, spacing:  0.38 },
  kira:    { role: "kickboxer",   pressure: 1.36, probe: 0.88, reset: 0.33, vReserve: 1.25, spacing: -0.14 },
  raven:   { role: "controller",  pressure: 0.46, probe: 1.30, reset: 1.04, vReserve: 0.61, spacing:  0.35 },
  ash:     { role: "sniper",      pressure: 0.35, probe: 1.02, reset: 1.42, vReserve: 0.80, spacing:  0.43 },
  veyr:    { role: "executioner", pressure: 1.53, probe: 0.67, reset: 0.29, vReserve: 0.75, spacing: -0.24 },
  zarek:   { role: "glaive",      pressure: 1.34, probe: 0.79, reset: 0.34, vReserve: 0.64, spacing: -0.08 },
  kaizen:  { role: "grappler",    pressure: 0.97, probe: 1.22, reset: 0.39, vReserve: 0.78, spacing:  0.10 },
  nesa:    { role: "bruiser",     pressure: 1.03, probe: 1.04, reset: 0.45, vReserve: 0.85, spacing:  0.19 },
};
// Difficulty affects how often bots make informed, committed personality reads.
const CHARACTER_IQ = [
  { read: 0.17, gap: [1.8, 2.5], strength: 0.16 },
  { read: 0.46, gap: [1.25, 1.9], strength: 0.43 },
  { read: 0.79, gap: [0.93, 1.42], strength: 0.73 },
  { read: 0.96, gap: [0.68, 1.06], strength: 1.00 },
] as const;

'''

FIELDS = '''  // CHARACTER_STYLES_V1: single tactical decision per short observation window.
  private personaEnemy: Fighter | null = null;
  private personaNextAt = -1;
  private personaMode: PersonalityPlan = "none";

'''

METHOD = '''  /** Fighter-specific tactical *intent*: no hidden enemy inputs or cooldowns.
   * Decisions are sampled once per plan, with longer gaps on easier settings.
   * The previous emergency dodge/parry and survival AI still have priority.
   */
  private personalityRead(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (this.personaEnemy !== o) {
      this.personaEnemy = o;
      this.personaNextAt = now + rand(0.25, 0.55);
      this.personaMode = "none";
    }
    if (now < this.personaNextAt) return;
    const profile = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];
    if (!profile || f.isDown() || o.isDown()) return;
    const iq = CHARACTER_IQ[this.iqLevel];
    this.personaNextAt = now + rand(iq.gap[0], iq.gap[1]);
    if (Math.random() > iq.read) {
      this.personaMode = "none"; // a missed tactical read isn't re-rolled per frame
      return;
    }
    const gap = f.root.position.clone().setY(0).distanceTo(
      o.root.position.clone().setY(0));
    const near = gap < (o.attacks.l1?.reach ?? 1.9) + 0.50;
    const opening = this.hasPunishWindow(o);
    const blocking = o.state === S.BLOCK;
    const guardWeak = o.guard / Math.max(1, o.maxGuard) < 0.35;
    const ownGuardWeak = f.guard / Math.max(1, f.maxGuard) < 0.33;
    const lowHp = f.hp / Math.max(1, f.maxHp) < 0.38;
    const enemyStrong = o.hp / Math.max(1, o.maxHp) > 0.55;
    let pressure = profile.pressure;
    let probe = profile.probe;
    let reset = profile.reset;
    if (opening) pressure += 1.60;
    if (guardWeak && near) pressure += 0.62;
    if (blocking) probe += 0.60;
    if (ownGuardWeak) { reset += 1.00; pressure *= 0.75; }
    if (lowHp && enemyStrong) { reset += 0.54; pressure *= 0.78; }
    switch (profile.role) {
      case "counter":     if (!opening && o.state === S.IDLE) probe += 0.62; break;
      case "duelist":    if (opening) pressure += 0.50; break;
      case "juggernaut": if (blocking) pressure += 0.85; break;
      case "riposte":    if (o.state === S.ATTACK && near) probe += 0.78; break;
      case "artillery":  if (near) reset += 1.1; break;
      case "support":    if (f.hp < f.maxHp * 0.70) reset += 1.0; break;
      case "ambush":     if (opening) pressure += 0.85; else probe += 0.25; break;
      case "rush":       if (!ownGuardWeak) pressure += 0.92; break;
      case "skirmish":   if (near && !opening) probe += 0.65; break;
      case "trapper":    if (f.barrelOut) probe += 0.75; if (near) reset += 0.60; break;
      case "kickboxer":  if (opening && near) pressure += 1.0; break;
      case "controller": if (near) reset += 0.95; else probe += 0.48; break;
      case "sniper":     if (gap < 4.0) reset += 1.35; break;
      case "executioner": if (f.bloodFestivalT > 0) pressure += 3.0; break;
      case "glaive":     if (f.clashMomentum >= 2) pressure += 0.95; break;
      case "grappler":   if (gap > 1.8 && gap < 4.7 &&
          (f.cooldowns.x ?? 1) <= 0) probe += 1.1; break;
      case "bruiser":    if (f.nesaCCharges > 0 && opening) pressure += 1.0; break;
    }
    const roll = Math.random() * (pressure + probe + reset);
    this.personaMode = roll < pressure ? "pressure" :
      roll < pressure + probe ? "probe" : "reset";
  }

  /** Style-aware scoring, not a scripted cast. Real equipped keys, cooldowns,
   * block, attack recovery, range and the V unlock are still checked elsewhere.
   */
  private personalitySkillScore(f: Fighter, o: Fighter, key: string, distance: number): number {
    const profile = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];
    if (!profile) return 0;
    const a = f.attacks[key];
    if (!a) return 0;
    const strength = CHARACTER_IQ[this.iqLevel].strength;
    const opening = this.hasPunishWindow(o);
    const blocking = o.state === S.BLOCK;
    const incoming = o.state === S.ATTACK && o.atkPhase === 0;
    const ranged = a.type === "projectile" || a.type === "lob" || a.type === "strike";
    const close = distance < 3.0;
    let value = 0;
    if (this.personaMode === "pressure") {
      if (a.type === "melee" || a.type === "phantom") value += 0.37;
      if (opening) value += 0.28;
    } else if (this.personaMode === "probe") {
      if (a.type === "mine" || a.type === "barrel" || a.type === "buff") value += 0.39;
      if (opening && a.type === "melee") value += 0.15;
    } else if (this.personaMode === "reset") {
      if ((a.type === "projectile" || a.type === "lob") && distance > 3) value += 0.32;
      if (a.type === "melee" && !opening) value -= 0.50;
    }
    switch (profile.role) {
      case "counter":      if (incoming && a.type === "buff") value += 0.55; break;
      case "duelist":     if (opening && a.type === "melee") value += 0.60; break;
      case "juggernaut":  if (blocking && a.guard > 25) value += 0.64; break;
      case "riposte":     if (incoming && a.mode === "counter") value += 0.95; break;
      case "artillery":   if (ranged && distance > 3.1) value += 0.49; break;
      case "support":     if (a.mode === "healing_water" && f.hp < f.maxHp * 0.68) value += 1.0; break;
      case "ambush":      if (opening && a.lunge > 0) value += 0.66; break;
      case "rush":        if (a.lunge > 0 && distance > 1.3) value += 0.55; break;
      case "skirmish":    if (opening && a.lunge > 0) value += 0.54; break;
      case "trapper":     if ((a.type === "mine" || a.type === "barrel") && !opening) value += 0.77; break;
      case "kickboxer":   if (opening && a.type === "melee") value += 0.65; break;
      case "controller":  if (a.mode === "static_field" && close) value += 1.0; break;
      case "sniper":      if (ranged && distance > 4.0) value += 0.58; break;
      case "executioner": if (opening && a.type === "melee") value += 0.67; break;
      case "glaive":      if (f.clashMomentum >= 2 && opening) value += 0.60; break;
      case "grappler":    if (a.style === "chain_predator_hook" && distance > 2.0 &&
          distance < 4.4 && !blocking) value += 1.15; break;
      case "bruiser":     if (f.nesaCCharges > 0 && opening && close &&
          a.style === "nesa_heart_slam") value += 0.78; break;
    }
    // Most V ultimates are held for visible punish/guard-break opportunities.
    // Buffs (especially actual healing) are exempt; V is *never* unlocked here.
    if (key === "v" && a.type !== "buff" && !opening &&
        o.state !== S.HITSTUN && o.state !== S.STAGGER) {
      value -= profile.vReserve * 2.7;
      if (this.personaMode === "reset") value -= 0.42;
    }
    return value * strength;
  }

'''


def replace_once(src, old, new, label):
    n=src.count(old)
    if n != 1:
        raise ValueError(f'{label}: expected exactly one code anchor; found {n}. '
                         'Source differs from the uploaded ZIP/previous AI updates.')
    return src.replace(old, new, 1)


def patch(src: str) -> str:
    # Do not leave bare update markers as executable TypeScript (previous bug).
    for marker in ('AI_PROJECTILE_CLASH_IQ_V1_20261108',
                   'AI_AERIAL_COMBAT_INTELLIGENCE_V1_20261108'):
        src = re.sub(r'(?m)^([ \t]*)' + re.escape(marker) + r'[ \t]*$',
                     r'\1// ' + marker, src)
    if MARK in src:
        return src
    if 'AI_LOW_HEALTH_SURVIVAL_V1_20261108' not in src or \
       'AI_ADVANCED_FOOTWORK_V1_20261108' not in src:
        raise ValueError('Install the Advanced Footwork (#8) and Low-Health Survival (#9) updates first.')
    src = replace_once(src, '\nexport class AiBrain implements Brain {',
                       '\n' + CONFIG + 'export class AiBrain implements Brain {',
                       'insert character personality table')
    src = replace_once(src, '  private theaterCd = rand(0.9, 2.1);',
                       FIELDS + '  private theaterCd = rand(0.9, 2.1);',
                       'insert personality plan state')
    src = replace_once(src, 'private tacticalFootwork(f: Fighter, o: Fighter, dt: number) {',
                       METHOD + 'private tacticalFootwork(f: Fighter, o: Fighter, dt: number) {',
                       'insert personality tactical logic')
    src = replace_once(src, '    this.observePatterns(f, o, dt);\n',
                       '    this.observePatterns(f, o, dt);\n'
                       '    this.personalityRead(f, o); // sample tactics; does not send an input\n',
                       'update personality based on observed opponent')
    src = replace_once(src, '    if (!viable) continue; // real ability limits, including character-specific checks\n',
                       '    if (!viable) continue; // real ability limits, including character-specific checks\n'
                       '    points += this.personalitySkillScore(f, o, key, distance);\n',
                       'personality influences valid skill ranking')
    # Movement: personality adjusts ideal range, only when no emergency defense
    # owns the input; existing arena-aware walking/obstacle code remains intact.
    src = replace_once(src,
                       '  const cdIntel = this.enemyCooldownRead(o);\n'
                       '  // Follow a known opening modestly; keep ranged kits at ranged distance.\n',
                       '  const cdIntel = this.enemyCooldownRead(o);\n'
                       '  const persona = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];\n'
                       '  const personaPower = CHARACTER_IQ[this.iqLevel].strength;\n'
                       '  // Follow a known opening modestly; keep ranged kits at ranged distance.\n',
                       'footwork personality plan')
    src = replace_once(src,
                       '  band.ideal = Math.max(1.05, band.ideal - shift);\n'
                       '  band.near = Math.max(0.88, band.near - shift);\n'
                       '  band.far = Math.max(band.near + 0.24, band.far - shift);\n',
                       '  const personalityShift = persona ? personaPower * (\n'
                       '    persona.spacing + (this.personaMode === "pressure" ? -0.30 :\n'
                       '      this.personaMode === "reset" ? 0.48 : this.personaMode === "probe" ? 0.14 : 0)) : 0;\n'
                       '  band.ideal = Math.max(1.05, band.ideal - shift + personalityShift);\n'
                       '  band.near = Math.max(0.88, band.near - shift + personalityShift);\n'
                       '  band.far = Math.max(band.near + 0.24, band.far - shift + personalityShift);\n',
                       'apply personality to effective fighting distance')
    # Advanced Footwork is the final safety-aware steering pass; let it also
    # reflect the plan without bypassing its edge/fire path evaluator.
    src = replace_once(src,
                       '    const ideal = THREE.MathUtils.clamp(band.ideal, 1.05, 6.4);\n',
                       '    const character = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];\n'
                       '    const personalShift = character ? CHARACTER_IQ[this.iqLevel].strength *\n'
                       '      (character.spacing + (this.personaMode === "reset" ? 0.48 :\n'
                       '        this.personaMode === "pressure" ? -0.30 : 0.10)) : 0;\n'
                       '    const ideal = THREE.MathUtils.clamp(band.ideal + personalShift, 1.05, 6.4);\n',
                       'reflect personality when safety-aware footwork overrides normal movement')
    # Keep existing offense cooldown awareness & combo logic, but vary pace.
    src = replace_once(src,
                       '  this.skillCd -= dt * (1 + cdIntel.pressure * 0.38);\n',
                       '  const tempo = CHARACTER_IQ[this.iqLevel].strength *\n'
                       '    (this.personaMode === "pressure" ? 0.19 :\n'
                       '      this.personaMode === "reset" ? -0.17 : 0);\n'
                       '  this.skillCd -= dt * (1 + cdIntel.pressure * 0.38 + tempo);\n',
                       'personality attack tempo')
    src = replace_once(src,
                       '  let heavyChance = style ? Math.min(0.78, style.heavy +\n',
                       '  let heavyChance = style ? Math.min(0.78, style.heavy +\n',
                       'no change to original heavy-chance anchor') if False else src
    src = replace_once(src,
                       '  // Veyr\'s festival specifically favors sustained lights and real guard pressure.\n',
                       '  // CHARACTER_STYLES_V1: role-based aggression changes input choices, not stats.\n'
                       '  heavyChance = THREE.MathUtils.clamp(heavyChance +\n'
                       '    CHARACTER_IQ[this.iqLevel].strength *\n'
                       '    (this.personaMode === "pressure" ? 0.09 :\n'
                       '      this.personaMode === "probe" ? -0.06 :\n'
                       '      this.personaMode === "reset" ? -0.13 : 0), 0.06, 0.80);\n'
                       '  // Veyr\'s festival specifically favors sustained lights and real guard pressure.\n',
                       'personality heavy attack risk')
    return '// ' + MARK + '\n' + src


def root_dir(path):
    starts = [Path(path).expanduser().resolve()] if path else [Path.cwd()]
    for st in starts:
        for p in (st, st/'web'):
            if (p/'src/game/ai.ts').is_file():
                return p
    raise FileNotFoundError('Cannot find src/game/ai.ts; run in the web folder, or use --path.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--path', help='path to web folder')
    ap.add_argument('--dry-run', action='store_true', help='check every patch anchor without writing')
    args=ap.parse_args()
    try:
        root=root_dir(args.path)
        target=root/'src/game/ai.ts'
        old=target.read_text(encoding='utf-8')
        new=patch(old)
        if new==old:
            print('Already installed; no changes made.')
            return 0
        print('Validated:', target.relative_to(root))
        if args.dry_run:
            print('DRY RUN successful. No files changed.')
            return 0
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup=target.with_name(target.name+'.before_character_styles_'+stamp+'.bak')
        shutil.copy2(target, backup)
        tmp=target.with_name('.ai_character_styles.tmp')
        try:
            tmp.write_text(new,encoding='utf-8')
            tmp.replace(target)
        except Exception:
            target.write_text(old,encoding='utf-8')
            raise
        print('Installed AI #10 — Character-Specific Fighting Styles (17 fighters).')
        print('Backup:', backup.name)
        print('Preserved AI #1–9, player stats, actual hit tests, skill unlocks and cooldowns.')
        return 0
    except Exception as e:
        print('INSTALLATION FAILED:',e,file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
