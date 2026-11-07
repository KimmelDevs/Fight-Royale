#!/usr/bin/env python3
"""Fight Royale V6: Gale aerial smash AI restored, Ash guard nerf, Kaede nerf,
Nyx charged-buff nerf, AI heavy evasion,
guard buffs for Aster/Vesper/Garrick, optional Kaizen VRM model swap.

Run in the Fight Royale web folder:
  python Install_FightRoyale_Combined_Balance_Kaede_Ash_Gale_V6.py
  python Install_FightRoyale_Combined_Balance_Kaede_Ash_Gale_V6.py --check
  python Install_FightRoyale_Combined_Balance_Kaede_Ash_Gale_V6.py --kaizen "kaizen_optimized_768.vrm"

Gale: CPU actively plans jump-to-smash sequences using aerial X/C/Z when
ready and in actual range. It prioritizes live self-dive attacks over random
ground-skill choices, without canceling urgent blocks/dodges.

Pre-existing Nyx Smoke Step boost: normal light attacks 2.0x; charged heavy and
skills 1.2x. This script does not reapply or change the Smoke Step ability itself.

CPU: when a heavy/continuous attack would break guard and cannot be clashed,
attempt a real legal dash or a backward jump if dash is on cooldown.
No artificial i-frames or perfect reactions. Preserves previous aggression.

Guard: Aster and Vesper 2x normal guard, Garrick 1.5x normal guard (before emblems).
Kaede: Thousand Cuts locks movement, dash and other attacks while casting;
if all first three slices miss HP damage, the remaining four vanish.
Ash: charged arrow guard damage reduced 50% (60 to 30), HP damage unchanged.
Kaizen: if kaizen_optimized_768.vrm is supplied or found nearby, installs it as
public/models/kaizen.vrm and points only Kaizen's roster entry at that VRM.

All edits are backed up; installation is safe to repeat. Standard-library only.
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
from pathlib import Path
import shutil
import sys
import tempfile

TAG = "FIGHT_ROYALE_KAEDE_CUTS_GUARD_NYX_AI_KAIZEN_ASH_GALE_V6"
FILES = ("fighter.ts", "ai.ts", "game.ts", "kits.ts")

class PatchError(Exception):
    pass

def once(s: str, old: str, new: str, why: str) -> str:
    count = s.count(old)
    if count != 1:
        raise PatchError(f"{why}: expected exactly one matching source anchor, found {count}.")
    return s.replace(old, new, 1)

def project_root(path: str | None) -> Path:
    if path:
        candidates = [Path(path).expanduser().resolve()]
    else:
        here = Path.cwd().resolve()
        candidates = [here, here / 'web', here.parent, here.parent / 'web', here.parent.parent]
    for base in candidates:
        if all((base / 'src' / 'game' / f).is_file() for f in FILES):
            return base
    raise PatchError('Game not found. Place the .py file in your web folder, or pass the game folder as the first argument.')

def patch_ash_kits(s: str) -> tuple[str, list[str]]:
    """Nerf *only* bow (Ash) charged-arrow guard damage from 60 to 30.

    The heavy attack has a physical hitbox and projectile handler already; their
    guard cost is read from this move's `guard` property. Leave `dmg` alone.
    """
    marker = 'FIGHT_ROYALE_ASH_CHARGE_GUARD_HALF_V5'
    if marker in s:
        return s, []
    start = s.find('function bow(): Record<string, Attack> {')
    if start < 0:
        raise PatchError('Ash heavy guard nerf: cannot find the bow kit.')
    end = s.find('\n}', start)
    if end < 0:
        raise PatchError('Ash heavy guard nerf: malformed bow kit.')
    block = s[start:end]
    target = 'heavy: a({ type: "projectile", wind:'
    if block.count(target) != 1:
        raise PatchError('Ash heavy guard nerf: bow charged attack changed unexpectedly.')
    import re
    # Permit already adjusted bow damage from previous balance patches.
    pattern = r'(heavy: a\(\{ type: "projectile",[^\n]*?\bdmg:\s*\d+(?:\.\d+)?\s*,\s*guard:\s*)(60|30)(\s*,)'
    matches = list(re.finditer(pattern, block))
    if len(matches) != 1:
        raise PatchError('Ash heavy guard nerf: expected charged-arrow guard of 60 or 30; no edits were made.')
    old_guard = matches[0].group(2)
    if old_guard == '30':
        return s, []
    new_block = re.sub(pattern, lambda m: m.group(1)+'30'+m.group(3), block, count=1)
    new_block = '// ' + marker + ': Ash heavy charged-arrow guard 60 -> 30, HP damage unchanged.\n' + new_block
    return s[:start] + new_block + s[end:], ['Ash charged arrow shield damage -50% (60 -> 30); HP damage unchanged']


def patch_fighter(s: str) -> tuple[str,list[str]]:
    changes = []
    if 'FIGHT_ROYALE_GUARD_CAPACITY_AVG_2X_1P5X_V3' not in s:
        anchor = '    this.parryWindow = st.parry; this.jumpV = st.jump;'
        ins = '''    // FIGHT_ROYALE_GUARD_CAPACITY_AVG_2X_1P5X_V3
    // Apply relative to ORIGINAL kit guard, not the older Aster +25% adjustment.
    // Keep emblem effects below so they scale the new base guard normally.
    if (look.name === "Aster" || look.name === "Vesper") this.maxGuard = st.guard * 2.0;
    else if (look.name === "Garrick") this.maxGuard = st.guard * 1.5;
'''
        s = once(s, anchor, ins + anchor, 'max guard starting values')
        changes.append('Aster/Vesper 2x, Garrick 1.5x guard')

    if 'FIGHT_ROYALE_NYX_SMOKE_HEAVY_1P2_V3' not in s:
        # The Smoke Step boost comes from Cinematic / Nyx Buff V2.
        if 'nyxShadowBoostT' in s:
            # Keep x2 on ordinary light attacks, but charged heavy is x1.2 like a skill.
            basics = [
                'const isBasic = /^(l[1-9]\\d*|air_l[1-9]\\d*|heavy|pc)$/.test(id);',
                'const isBasic = /^(l[1-9]\\d*|air_l[1-9]\\d*|heavy|pc)$/.test(id);',
            ]
            before = basics[0]
            after = 'const isBasic = /^(l[1-9]\\d*|air_l[1-9]\\d*|pc)$/.test(id);'
            s = once(s, before, after, 'Nyx basic attack boost selection')
            s = once(s, 'if (chosen && (isBasic || isSkill)) {',
                     'if (chosen && (isBasic || isSkill || id === "heavy")) {',
                     'Nyx charged heavy consumes only x1.2')
            # Add anchor as an inline note to preserve idempotence.
            s = once(s, after, after + '\n      // FIGHT_ROYALE_NYX_SMOKE_HEAVY_1P2_V3: charged heavy is x1.2, never x2.', 'Nyx marker')
            changes.append('Nyx charged attack x1.2; normal basics remain x2')
        else:
            print('[INFO] Nyx Smoke Step buff not detected. Skipping nerf; install the existing camera/Nyx Smoke Step update first.')
    kaede_text, kaede_changes = patch_kaede_fighter(s)
    return kaede_text, changes + kaede_changes

EVADE_FIELDS = '''  // FIGHT_ROYALE_HEAVY_EVADE_DASH_JUMP_V3: one real defensive choice per swing.
  private heavyEscapeSerial = -1;
  private heavyEscapeReactT = 0;
  private heavyEscapeUsed = false;

'''

EVADE_METHOD = '''  /** Last-resort heavy evasion. Keep offense when shielding or clashing works.
   * Only legal movement inputs are used; no free dash, teleport or invulnerability.
   */
  private evadeUnsafeHeavy(f: Fighter, o: Fighter, dt: number): boolean {
    const a = o.atk;
    const dangerous = o.state === S.ATTACK && !!a &&
      (a.heavy || (o.isContinuousComboActive() && a.dmg >= 50));
    if (!dangerous || !a) {
      this.heavyEscapeSerial = -1;
      this.heavyEscapeUsed = false;
      return false;
    }
    if (f.isDown() || !f.onGround ||
        ![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(f.state)) return false;

    const distance = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    const dangerRange = a.type === "strike" ? Math.max(1.6, a.radius) + 0.55 :
      Math.max(1.4, a.reach + Math.min(Math.max(0, a.lunge) * 0.12, 0.8)) + 0.55;
    if (distance > dangerRange) return false;

    if (this.heavyEscapeSerial !== o.swingSerial) {
      this.heavyEscapeSerial = o.swingSerial;
      this.heavyEscapeUsed = false;
      this.heavyEscapeReactT = Math.max(this.p.react[0],
        this.p.react[0] + Math.random() * (this.p.react[1] - this.p.react[0]));
    }
    if (this.heavyEscapeUsed) return false;
    this.heavyEscapeReactT = Math.max(0, this.heavyEscapeReactT - dt);
    if (this.heavyEscapeReactT > 0) return false;

    // For a repeated sequence, use the next scheduled hit time when available.
    const hits = o.isContinuousComboActive()
      ? this.threats.comboHits(o).filter(t => t >= this.threats.now() - 0.03)
        .sort((x, y) => x - y) : [];
    const eta = hits.length ? hits[0] - this.threats.now() :
      Math.max(0, a.wind - o.stateT);
    if (eta > 0.38) return false;

    const shieldUp = f.state === S.BLOCK && f.stateT >= f.shieldRaise;
    const canRaise = (f.state === S.IDLE || f.state === S.BLOCK) &&
      eta >= (f.nextShieldFast ? 0.01 : 0.10) + 0.045;
    const shieldCost = Math.max(a.guard * (a.heavy ? 1.28 : 1.10), 18);
    const wouldCrushShield = o.kit === "hammer" && a.heavy;
    const canBlock = (shieldUp || canRaise) && f.guard > shieldCost && !wouldCrushShield;
    const myLight = f.attacks.l1;
    const canClash = !!myLight && myLight.type === "melee" &&
      ((f.state === S.ATTACK && f.atk?.type === "melee" && f.atkPhase === 1) ||
       (f.state === S.IDLE && distance <= myLight.reach + 0.18 &&
        myLight.wind + 0.055 < eta));
    if (canBlock || canClash) return false;

    const away = f.root.position.clone().sub(o.root.position).setY(0);
    if (away.lengthSq() < 0.001) away.set(f.id % 2 ? 1 : -1, 0, 0);
    away.normalize();
    const back = f.stage ? new THREE.Vector3(Math.sign(away.x) || -f.facing, 0, 0) : away;
    // Check actual stage edges / arena radius before issuing movement.
    const destination = f.root.position.clone().setY(0).addScaledVector(back, 2.4);
    if (f.stage) {
      const main = f.stage.plats[0];
      if (!main || destination.x < main.x0 + 0.65 || destination.x > main.x1 - 0.65)
        return false;
    } else if (destination.length() > f.arenaRadius - f.radius - 0.12) return false;

    const canDash = f.dashCd <= 0 && !f.dashing() &&
      (f.kit !== "hammer" || f.state !== S.ATTACK);
    if (canDash) {
      f.intent.dash.copy(back);
      f.intent.move.copy(back);
    } else if (f.state === S.IDLE || f.state === S.BLOCK) {
      // Dash on cooldown: ordinary backward jump + air movement, not instant invulnerability.
      f.intent.jump = true;
      f.intent.move.copy(back);
    } else return false;
    f.intent.block = false;
    f.intent.attack = false;
    f.intent.skill = "";
    this.heavyEscapeUsed = true;
    // Do not erase attack queues, ready skill timers, or character-specific footwork.
    return true;
  }

'''

def patch_ai(s: str) -> tuple[str,list[str]]:
    if 'FIGHT_ROYALE_HEAVY_EVADE_DASH_JUMP_V3' in s:
        return s, []
    if '  private ignitionChoices = new Map<number, boolean>();' in s:
        s = once(s, '  private ignitionChoices = new Map<number, boolean>();',
                 '  private ignitionChoices = new Map<number, boolean>();\n' + EVADE_FIELDS.rstrip('\n'), 'heavy evade fields')
    else:
        # Almost every recent AI contains this field, but handle those with a simpler brain.
        s = once(s, 'export class AiBrain implements Brain {',
                 'export class AiBrain implements Brain {\n' + EVADE_FIELDS.rstrip('\n'), 'heavy evade fields')
    s = once(s, '  constructor(private threats: Threats, level: number) {',
             EVADE_METHOD + '  constructor(private threats: Threats, level: number) {', 'heavy evade helper')
    # Insert after other early safety checks, but before old reactive defense and offense.
    prior = '    if (this.dodgeUnsafeContinuous(f, o, dt)) return;'
    if prior in s:
        s = once(s, prior, prior + '\n    if (this.evadeUnsafeHeavy(f, o, dt)) return;', 'heavy dodge decision')
    else:
        s = once(s, '    if (!o || o.isDown()) return;',
                 '    if (!o || o.isDown()) return;\n    if (this.evadeUnsafeHeavy(f, o, dt)) return;',
                 'heavy dodge decision')
    return s, ['AI heavy-hit dash + backward-jump fallback']


GALE_SMASH_MARK = "FIGHT_ROYALE_GALE_SMASH_PRIORITY_V6"

GALE_SMASH_OLD = '''  private jumpPulse = false;
  private airPlan = -1;
  private airDouble = false;

  /** Wind kit: now and then jump (sometimes double jump) and come down with an air skill. */
  private airDive(f: Fighter, o: Fighter, dt: number) {
    const ready = ["z", "x", "c"].filter((k) => f.attacks[k + "_air"] && f.cooldowns[k] <= 0);
    if (f.onGround) {
      this.airPlan = -1;
      const dist = f.root.position.distanceTo(o.root.position);
      if (f.state === S.IDLE && ready.length && dist < 6 && Math.random() < dt * 0.5) {
        f.intent.jump = true;
        this.airPlan = 0.3 + Math.random() * 0.25;
        this.airDouble = Math.random() < 0.5;
      }
      return;
    }
    if (this.airPlan < 0) return;
    this.airPlan -= dt;
    if (this.airDouble && this.airPlan < 0.15 && f.velY < 2) { f.intent.jump = true; this.airDouble = false; this.airPlan += 0.3; }
    if (this.airPlan <= 0 && ready.length) {
      f.intent.skill = ready[Math.floor(Math.random() * ready.length)];
      this.airPlan = -1;
    }
  }
'''

GALE_SMASH_NEW = '''  private jumpPulse = false;
  // FIGHT_ROYALE_GALE_SMASH_PRIORITY_V6: deliberate air-to-ground smash planning.
  private galeSmashKey = "";
  private galeSmashDelay = 0;
  private galeSmashNext = 0.35;

  /** Gale's aerial X/C/Z are actual dive ground-smashes, not normal ground casts.
   * Only plan while a smash is ready, the enemy is in reach, and no shield defense
   * is already pending. Use ordinary jump/skill buttons, preserving all cooldowns.
   */
  private airDive(f: Fighter, o: Fighter, dt: number): boolean {
    this.galeSmashNext = Math.max(0, this.galeSmashNext - dt);
    if (f.isDown() || o.isDown()) { this.galeSmashKey = ""; return false; }
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    // Falling Star can chase farther; the other smashes need a nearby landing.
    const limits: Record<string, number> = { x: 6.0, c: 3.7, z: 2.9 };
    if (f.onGround) {
      this.galeSmashKey = ""; // clear any plan that ended by landing
      if (this.galeSmashNext > 0 || f.state !== S.IDLE || f.dashing() ||
          f.intent.block || this.blockHold > 0 || this.blockWait >= 0 ||
          f.intent.dash.lengthSq() > 0.01 || gap < 1.15) return false;
      // Only genuinely ready air variants qualify. Never launch just to waste Z/X/C.
      const choices = ["x", "c", "z"].filter((key) =>
        !!f.attacks[key + "_air"] && f.attacks[key + "_air"].mode === "dive" &&
        (f.cooldowns[key] ?? 1) <= 0 && gap <= limits[key]);
      if (!choices.length) return false;
      // Prioritize X's targeted crash, then C's whirlwind ground smash, then Z.
      // This intentionally does NOT spend a ready grounded skill first.
      const key = choices.includes("x") && (gap > 3.4 || Math.random() < 0.55)
        ? "x" : choices.includes("c") && Math.random() < 0.70
        ? "c" : choices.includes("z") ? "z" : choices[0];
      this.galeSmashKey = key;
      this.galeSmashDelay = 0.23 + Math.random() * 0.13;
      this.galeSmashNext = this.p.react[0] + 0.35 + Math.random() * 0.45;
      this.queue = []; this.hold = 0;
      f.intent.block = false;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.jump = true;
      return true;
    }
    if (!this.galeSmashKey) return false;
    if ((f.cooldowns[this.galeSmashKey] ?? 1) > 0 ||
        !f.attacks[this.galeSmashKey + "_air"]) {
      this.galeSmashKey = "";
      return false;
    }
    // A knockback, an interrupt or another real action cancels the pending plan.
    if (f.state !== S.IDLE && f.state !== S.BLOCK) {
      this.galeSmashKey = "";
      return false;
    }
    this.galeSmashDelay -= dt;
    f.intent.jump = false; // release the jump button after taking off
    f.intent.attack = false;
    f.intent.block = false;
    this.queue = []; this.hold = 0;
    const selected = this.galeSmashKey;
    if (this.galeSmashDelay <= 0 || f.velY <= 0) {
      // Don't magically extend reach if a target fled during the leap.
      if (gap <= limits[selected] + 0.55) {
        f.intent.skill = selected; // Fighter chooses the legitimate _air version
        this.galeSmashKey = "";
      } else if (this.galeSmashDelay < -0.32) {
        this.galeSmashKey = ""; // no invalid cross-map homing smash
      }
    }
    return true;
  }
'''

def patch_gale_ai(s: str) -> tuple[str, list[str]]:
    if GALE_SMASH_MARK in s:
        return s, []
    s = once(s, GALE_SMASH_OLD, GALE_SMASH_NEW, 'Gale smash planner replacement')
    s = once(s, '    if (f.kit === "wind" && !f.stage) this.airDive(f, o, dt);\n',
             '', 'remove old Gale smash call after offense')
    anchor = '    this.aiAirTap = false;\n'
    s = once(s, anchor,
             anchor + '    if (f.kit === "wind" && !f.stage && this.airDive(f, o, dt)) return;\n',
             'put Gale smash plan before offensive ground skills')
    return s, ['Gale CPU prioritizes legitimate jump-to-smash X/C/Z air attacks']


patch_ai_v5 = patch_ai

def patch_ai(s: str) -> tuple[str, list[str]]:
    s, notes = patch_ai_v5(s)
    s, notes_gale = patch_gale_ai(s)
    return s, notes + notes_gale


# Kaede Thousand Cuts (seven strike pulses): the first three must deal at least
# one actual HP hit, and the caster must be planted for the entire cast.
KAEDE_TAG = "FIGHT_ROYALE_KAEDE_THOUSAND_CUTS_LOCK_MISS3_V4"


def patch_kaede_fighter(s: str) -> tuple[str, list[str]]:
    if KAEDE_TAG in s:
        return s, []
    method_anchor = '  private readDash() {'
    # Some versions use a different return annotation; match exact current source.
    if method_anchor not in s:
        method_anchor = '  private readDash(): void {'
    helper = '''  // FIGHT_ROYALE_KAEDE_THOUSAND_CUTS_LOCK_MISS3_V4
  isKaedeThousandCutsCasting(): boolean {
    return this.kit === "katana" && this.state === S.ATTACK && !!this.atk &&
      this.atk.name === "Thousand Cuts" && this.atk.style === "slashes";
  }
  /** Called only after the THIRD unsuccessful slice on the authoritative host. */
  cancelKaedeThousandCuts() {
    if (!this.isKaedeThousandCutsCasting()) return;
    this.atk = null;
    this.atkId = "";
    this.atkPhase = 0;
    this.buffered = false;
    this.holding = false;
    this.poseOverride = "";
    this.setState(S.IDLE);
    this.model.recoil = Math.max(this.model.recoil, 0.2);
  }

'''
    s = once(s, method_anchor, helper + method_anchor, 'Kaede Thousand Cuts helpers')
    # Prevent dash cancellation of the committed casting animation.
    s = once(s, '    const d = this.intent.dash;\n',
             '    if (this.isKaedeThousandCutsCasting()) return; // committed, immobile cast\n    const d = this.intent.dash;\n',
             'Kaede dash lock')
    # Inputs still update their held-state, but cannot buffer another basic attack.
    atk_anchor = '    this.atkPrev = on;\n'
    s = once(s, atk_anchor,
             atk_anchor + '    if (this.isKaedeThousandCutsCasting()) { this.holding = false; return; }\n',
             'Kaede basic attack lock')
    s = once(s, '  private readSkill() {\n',
             '  private readSkill() {\n    if (this.isKaedeThousandCutsCasting()) return;\n',
             'Kaede other-skill lock')
    # Keep the cast going through all seven delayed hits, regardless of the
    # ordinary short default strike animation duration.
    s = once(s, '    this.atk = this.attacks[id];\n',
             '    this.atk = this.attacks[id];\n'
             '    if (this.kit === "katana" && this.atk?.name === "Thousand Cuts" && this.atk.style === "slashes") {\n'
             '      this.atk = { ...this.atk, lunge: 0, recover: Math.max(this.atk.recover,\n'
             '        this.atk.delay + Math.max(0, this.atk.repeat - 1) * this.atk.interval + 0.23) };\n'
             '      this.dashT = 0; this.holding = false; this.velY = Math.min(0, this.velY);\n'
             '      this.vx = 0; // stop lingering platform momentum at the start of casting\n'
             '    }\n',
             'Kaede complete cast duration')
    # 3D move: do not follow target, auto-lunge, steer, or dash mid-cast.
    s = once(s, '  private move(dt: number) {\n',
             '  private move(dt: number) {\n'
             '    if (this.isKaedeThousandCutsCasting()) {\n'
             '      this.model.walk = 0; this.model.rotation.y = this.viewBias; return;\n'
             '    }\n', 'Kaede arena movement lock')
    # Stage mode: set horizontal velocity zero even when the attack started at speed.
    s = once(s, '  private movePlat(dt: number) {\n',
             '  private movePlat(dt: number) {\n'
             '    if (this.isKaedeThousandCutsCasting()) {\n'
             '      this.vx = 0; this.model.walk = 0; return;\n'
             '    }\n', 'Kaede brawl movement lock')
    return s, ['Kaede Thousand Cuts rooted cast, no dash/attack/skill cancels']


def patch_kaede_game(s: str) -> tuple[str, list[str]]:
    if KAEDE_TAG in s:
        return s, []
    anchor = '''  private runStrike(f: Fighter, a: Attack, power: number) {
    const round = this.round;
    const color = f.look.glow;
    const one = (i: number) => {
      if (round !== this.round || f.isDown()) return;
'''
    expanded = '''  private runStrike(f: Fighter, a: Attack, power: number) {
    const round = this.round;
    const color = f.look.glow;
    // FIGHT_ROYALE_KAEDE_THOUSAND_CUTS_LOCK_MISS3_V4
    // If none of the FIRST THREE slices causes an actual HP hit, the rest vanish.
    // Guarded, parried, dodged and whiffed slices all count as misses.
    const kaedeCuts = f.kit === "katana" && a.name === "Thousand Cuts" && a.style === "slashes";
    const kaedeSerial = f.swingSerial;
    let firstThreeConnected = false;
    // The area stays where the target was when Kaede started Thousand Cuts.
    // Dodging out of that area must remain possible; no automatic slice-by-slice tracking.
    const kaedeCenter = kaedeCuts
      ? (f.opponent ?? f).root.position.clone() : null;
    const one = (i: number) => {
      if (round !== this.round || f.isDown()) return;
      if (kaedeCuts && (f.swingSerial !== kaedeSerial || !f.isKaedeThousandCutsCasting())) return;
'''
    s = once(s, anchor, expanded, 'Kaede strike chain setup')
    s = once(s, '''      const src: Entity = a.at === "self" || !f.opponent ? f : f.opponent;
      const center = this.plat ? src.root.position.clone() : src.root.position.clone().setY(0);''', '''      const src: Entity = a.at === "self" || !f.opponent ? f : f.opponent;
      const center = kaedeCenter
        ? (this.plat ? kaedeCenter.clone() : kaedeCenter.clone().setY(0))
        : (this.plat ? src.root.position.clone() : src.root.position.clone().setY(0));''', 'Kaede fixed strike position')
    old = '''        if (round !== this.round) return;
        const at = a.at === "self" ? (this.plat ? f.root.position.clone() : f.root.position.clone().setY(0)) : center;
'''
    new = '''        if (round !== this.round) return;
        if (kaedeCuts && (f.swingSerial !== kaedeSerial || !f.isKaedeThousandCutsCasting())) return;
        const at = a.at === "self" ? (this.plat ? f.root.position.clone() : f.root.position.clone().setY(0)) : center;
'''
    s = once(s, old, new, 'Kaede cancel stale scheduled slices')
    old = '''        for (const d of this.enemiesOf(f)) {
          const to = d.root.position.clone().sub(at);
          const dy = Math.abs(to.y);
          to.setY(0);
          if (to.length() <= a.radius + d.radius * 0.5 && (this.plat ? dy < 1.6 : !d.airborne())) {
            const dir = to.length() > 0.05 ? to.normalize() : d.root.position.clone().sub(f.root.position).setY(0).normalize();
            this.applyHit(f, d, a, power, d.chest(), dir, true);
          } else if (d instanceof Fighter && to.length() <= a.radius + 1) {
            this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.8, 0)), "DODGE", "#c9d3e6", 0.7);
          }
        }
        for (const t of [...this.traps]) if (t.kind === "barrel" && t.team !== f.team && t.pos.distanceTo(at) <= a.radius + 0.4) this.detonate(t);
        if (i + 1 < a.repeat) one(i + 1);
'''
    new = '''        let realDamageThisSlice = false;
        for (const d of this.enemiesOf(f)) {
          const to = d.root.position.clone().sub(at);
          const dy = Math.abs(to.y);
          to.setY(0);
          if (to.length() <= a.radius + d.radius * 0.5 && (this.plat ? dy < 1.6 : !d.airborne())) {
            const dir = to.length() > 0.05 ? to.normalize() : d.root.position.clone().sub(f.root.position).setY(0).normalize();
            const outcome = this.applyHit(f, d, a, power, d.chest(), dir, true);
            if (kaedeCuts && (outcome === "hit" || outcome === "crit" || outcome === "ko"))
              realDamageThisSlice = true;
          } else if (d instanceof Fighter && to.length() <= a.radius + 1) {
            this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.8, 0)), "DODGE", "#c9d3e6", 0.7);
          }
        }
        if (kaedeCuts && i < 3 && realDamageThisSlice) firstThreeConnected = true;
        if (kaedeCuts && i === 2 && !firstThreeConnected) {
          // Stop before scheduling slice 4. A vanished attack cannot produce phantom hits.
          f.cancelKaedeThousandCuts();
          this.fxp("smoke", at.clone(), "#e9a5bb");
          this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.7, 0)),
            "THOUSAND CUTS MISSED", "#ffa6bd", 0.88);
          return;
        }
        for (const t of [...this.traps]) if (t.kind === "barrel" && t.team !== f.team && t.pos.distanceTo(at) <= a.radius + 0.4) this.detonate(t);
        if (i + 1 < a.repeat) one(i + 1);
'''
    s = once(s, old, new, 'Kaede third-slice miss cancellation')
    return s, ['Kaede Thousand Cuts: stop after first three slices miss HP damage']


def patch_roster(s: str) -> tuple[str,list[str]]:
    if 'FIGHT_ROYALE_KAIZEN_VRM_REPLACEMENT_V3' in s:
        return s, []
    old = 'look: { name: "Kaizen", body: "m", vrm: "garrick", kit: "chainblade"'
    new = 'look: { name: "Kaizen", body: "m", vrm: "kaizen", kit: "chainblade"'
    if old not in s:
        if new in s:
            return s, []
        raise PatchError('Kaizen roster entry differs from expected source. Not replacing any other character.')
    s = once(s, old, new, 'Kaizen VRM registration')
    # No global source marker needed; idempotence checks the named entry.
    return s, ['Kaizen now uses kaizen.vrm instead of Garrick']

def find_vrm(root: Path, explicit: str | None) -> Path | None:
    if explicit:
        file = Path(explicit).expanduser().resolve()
        if not file.is_file():
            raise PatchError(f'VRM input file does not exist: {file}')
        return file
    choices = [
        root / 'public/models/kaizen.vrm',
        root / 'kaizen_optimized_768.vrm',
        root / 'kaizen.vrm',
        Path(__file__).resolve().parent / 'kaizen_optimized_768.vrm',
        Path(__file__).resolve().parent / 'kaizen.vrm',
        Path.cwd() / 'kaizen_optimized_768.vrm',
        Path.cwd() / 'kaizen.vrm',
        Path.home() / 'Downloads/kaizen_optimized_768.vrm',
        Path.home() / 'Downloads/kaizen.vrm',
    ]
    return next((p for p in choices if p.is_file()), None)

def atomic_bytes(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('project', nargs='?', help='Project root, if not running from the web folder')
    ap.add_argument('--kaizen', metavar='PATH', help='Path to optimized or raw Kaizen .vrm file')
    ap.add_argument('--check', action='store_true', help='Only check compatibility; do not write')
    args = ap.parse_args()
    try:
        root = project_root(args.project)
        g = root / 'src' / 'game'
        target_roster = g / 'roster.ts'
        scripts = {g / 'fighter.ts': patch_fighter, g / 'ai.ts': patch_ai,
                   g / 'game.ts': patch_kaede_game, g / 'kits.ts': patch_ash_kits}
        vrm = find_vrm(root, args.kaizen)
        if vrm is not None and target_roster.is_file():
            scripts[target_roster] = patch_roster
        changes = {}
        messages = []
        for path, fn in scripts.items():
            raw = path.read_bytes()
            t = raw.decode('utf-8-sig')
            newline = '\r\n' if '\r\n' in t else '\n'
            update, labels = fn(t.replace('\r\n', '\n'))
            result = update.replace('\n', newline).encode('utf-8')
            if raw.startswith(b'\xef\xbb\xbf'):
                result = b'\xef\xbb\xbf' + result
            if result != raw:
                changes[path] = (raw, result)
                messages.extend(labels)
        dest = root / 'public' / 'models' / 'kaizen.vrm'
        new_vrm_data = None
        if vrm is not None:
            new_vrm_data = vrm.read_bytes()
            if new_vrm_data[:4] != b'glTF':
                raise PatchError('Kaizen asset is not a valid binary glTF / VRM file.')
            if dest.is_file() and dest.read_bytes() == new_vrm_data:
                new_vrm_data = None
        if args.check:
            print('[CHECK] Compatible. Planned source updates:', ', '.join(p.name for p in changes) or 'none')
            print('[CHECK] Kaizen:', str(vrm) if vrm else 'no .vrm supplied; Kaizen swap will be skipped')
            return 0
        if not changes and new_vrm_data is None:
            print('[OK] Already installed, no changes required.')
            if vrm is None: print('[INFO] Kaizen model not found. Place kaizen_optimized_768.vrm alongside the installer and run it again.')
            return 0
        stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup = root / '.fight_royale_v6_backups' / stamp
        backup.mkdir(parents=True, exist_ok=False)
        originals = {}
        for path, (raw, _) in changes.items():
            rel = path.relative_to(root)
            bak = backup / rel
            bak.parent.mkdir(parents=True, exist_ok=True)
            bak.write_bytes(raw)
            originals[path] = raw
        if new_vrm_data is not None and dest.is_file():
            bak = backup / 'public/models/kaizen.vrm'
            bak.parent.mkdir(parents=True, exist_ok=True)
            old = dest.read_bytes()
            bak.write_bytes(old)
            originals[dest] = old
        elif new_vrm_data is not None:
            originals[dest] = None
        installed = []
        try:
            for path, (_, value) in changes.items():
                atomic_bytes(path, value)
                installed.append(path)
            if new_vrm_data is not None:
                atomic_bytes(dest, new_vrm_data)
                installed.append(dest)
        except Exception:
            for path in reversed(installed):
                old = originals.get(path)
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_bytes(path, old)
            raise
        print('[DONE] Fight Royale V6 update installed.')
        for m in messages: print('  - ' + m)
        if new_vrm_data is not None: print('  - Kaizen VRM copied to public/models/kaizen.vrm')
        if vrm is None: print('[INFO] Kaizen not switched: put kaizen_optimized_768.vrm next to this script and run again.')
        print('Backups:', backup)
        print('Validate: npx tsc --noEmit -p .')
        return 0
    except Exception as exc:
        print('[ERROR]', exc)
        print('No partial changes are left behind if a write failed.')
        return 1

if __name__ == '__main__':
    sys.exit(main())
