#!/usr/bin/env python3
"""ZEPHYR V25 COMPLETE — V24 resize, modes, Split click combo, AI, HP/resilience, 25s Rhythm and live HUD.

Run in fight-royale/web:
    python install_zephyr_v25_complete_balance.py
Or pass the web folder:
    python install_zephyr_v25_complete_balance.py C:\\path\\to\\fight-royale\\web

Upgrades Zephyr V20+ with the V24 detached-weapon resize (unless already
installed), mode buffs, smarter mode-aware AI, and a fix for the player-vs-CPU
mode readout. No changes to other heroes, input, networking layout, SQL, or unrelated passives.
This version includes Zephyr Rhythm timer and the new resilience passive.

The detached weapon root needs its OWN scale: the old `tristaff ? 0.79`
scaled hand pivots but did not scale Zephyr's detached weapon geometry.

Tuning: after installation, edit ZEPHYR_TRISTAFF_SIZE_V24 in model.ts,
and DRAGON_MODE_TUNING in fighter.ts for mode-specific effects.
* globalScale: real weapon hierarchy scale, default 0.68
* middleHalfLength/endHalfLength: half a rod, default 0.27 => 0.54 each
* chainGap: end-to-end distance before metal end-cap overhang, default 0.20
  (the exposed gap after caps and scaling is approximately 0.08–0.09 units)
* shaftRadius, wrapRadius, ferrule*/lip*/ring*: thinner rod fittings
* chainLinkOuter: slightly enlarged link loops so four links connect visibly
* fighter.ts -> ZEPHYR_PASSIVE_TUNING.rhythmSeconds = 25 (refreshes on gain)
* fighter.ts -> ZEPHYR_PASSIVE_TUNING.damageTakenMult = 0.80
* kits.ts -> STATS.tristaff.hp = 2670 (20% more than 2225)
* fighter.ts -> DRAGON_MODE_TUNING[1].splitClickSpeedCap = 2.00
* fighter.ts -> DRAGON_MODE_TUNING[1].splitAlternateSpeedMult = 0.37
* roster.ts -> Zephyr's in-menu passive explanation (not the battle HUD)

Safety: validates every anchor in memory, creates a timestamped backup,
restores the original file on write failure, refuses duplicate installation.
Does not run git, npm or database migrations.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import re
import shutil
import sys

MARK = "ZEPHYR_TRISTAFF_PROPORTIONS_V24"
SOURCE = Path("src/game/model.ts")
ROSTER = Path("src/game/roster.ts")

# The table is put in model.ts as a single, editable source of dimensions.
TUNING_TABLE = '''// ZEPHYR_TRISTAFF_PROPORTIONS_V24 — visual-only; edit these values to resize the sanjiekun.
// Unlike the procedural hand pivot, the real three-rod weapon is a detached root.
const ZEPHYR_TRISTAFF_SIZE_V24 = {
  globalScale: 0.68,           // Scale the ACTUAL detached root and its cosmetic toss clone.
  middleHalfLength: 0.27,      // Middle rod length = 0.54, formerly 0.65.
  endHalfLength: 0.27,         // Each end rod length = 0.54, formerly 0.67.
  shaftRadius: 0.02465,        // 15% thinner than 0.029.
  wrapRadius: 0.02805,         // 15% thinner than 0.033.
  wrapLength: 0.02975,
  ferruleTopRadius: 0.03910,   // 15% thinner than 0.046.
  ferruleBottomRadius: 0.03570,
  ferruleLength: 0.05950,
  lipTopRadius: 0.04165,
  lipBottomRadius: 0.03910,
  lipLength: 0.01530,
  ringInnerRadius: 0.03060,
  ringOuterRadius: 0.03910,
  chainGap: 0.20,              // 4 links; cap-to-cap clear space ~= 0.08-0.09 after scale.
  chainLinkInner: 0.008,
  chainLinkOuter: 0.027,      // Adjacent links overlap slightly instead of floating apart.
} as const;

'''


def replace_once(source: str, old: str, new: str, context: str) -> str:
    n = source.count(old)
    if n != 1:
        raise RuntimeError(
            f"{context}: expected exactly 1 matching anchor, found {n}: {old[:90]!r}. "
            "No files changed; upload your latest src/game/model.ts for adaptation."
        )
    return source.replace(old, new, 1)


def update_model(source: str) -> str:
    if MARK in source:
        raise RuntimeError("Zephyr V24 is already installed. No files changed.")
    if "ZEPHYR_DRAGON_DANCER_V1" not in source or "ZEPHYR_BODY_GRIP_V21" not in source:
        raise RuntimeError("Expected Zephyr V21+ weapon/grip code. Install V21 first.")

    # Place the tuning table near the common weapon settings, NOT inside a class.
    anchor = 'const VRM_WEAPON_SCALE = 0.68;'
    source = replace_once(source, anchor, anchor + '\n' + TUNING_TABLE, "size tuning table")

    begin_marker = '  private buildDragonStaff() {'
    end_marker = '\n  /** Spring integration;'
    if source.count(begin_marker) != 1 or source.count(end_marker) != 1:
        raise RuntimeError("Unable to isolate buildDragonStaff(). No files changed.")
    begin = source.index(begin_marker)
    end = source.index(end_marker, begin)
    part = source[begin:end]
    if 'const root = pivot(this);' not in part or 'this.dragonGhost = root.clone(true);' not in part:
        raise RuntimeError("Unexpected weapon hierarchy (not a detached V21 root). No files changed.")

    # Retain every existing socket name, chain joint name, and outermost blade-tip pointer.
    modifications = (
        ('    root.name = "zephyrMiddleGrip";',
         '    root.name = "zephyrMiddleGrip";\n'
         '    // V24: the previous 0.79 adjusted only hand pivots, NOT this detached mesh.\n'
         '    root.scale.setScalar(ZEPHYR_TRISTAFF_SIZE_V24.globalScale);',
         'scale actual weapon root'),
        ('      const r = name === "middle" ? .325 : .335;',
         '      const r = name === "middle" ? ZEPHYR_TRISTAFF_SIZE_V24.middleHalfLength :\n'
         '        ZEPHYR_TRISTAFF_SIZE_V24.endHalfLength;', 'shorten three rods'),
        ('      mesh(rod, cyl(.029,.029,r*2,12), lacquer, [0,c,0]);',
         '      mesh(rod, cyl(ZEPHYR_TRISTAFF_SIZE_V24.shaftRadius,\n'
         '        ZEPHYR_TRISTAFF_SIZE_V24.shaftRadius,r*2,12), lacquer, [0,c,0]);',
         'thin rigid shafts'),
        ('        const y = name === "middle" ? -.22+i*.11 : sign*(.11+i*.11);',
         '        // Wraps follow each shorter rod rather than extending past its ends.\n'
         '        const y = name === "middle" ? (-.80+i*.40)*r : sign*(.36+i*.36)*r;',
         'redistribute grip wraps'),
        ('        mesh(rod, cyl(.033,.033,.035,12), i%2 ? black : red, [0,y,0]);',
         '        mesh(rod, cyl(ZEPHYR_TRISTAFF_SIZE_V24.wrapRadius,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.wrapRadius,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.wrapLength,12), i%2 ? black : red, [0,y,0]);',
         'thin grip wraps'),
        ('        mesh(rod, cyl(.046,.042,.070,12), darkMetal, [0,y,0]);',
         '        mesh(rod, cyl(ZEPHYR_TRISTAFF_SIZE_V24.ferruleTopRadius,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.ferruleBottomRadius,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.ferruleLength,12), darkMetal, [0,y,0]);',
         'thin metal end caps'),
        ('        mesh(rod, cyl(.049,.046,.018,12), ferrule, [0,y+Math.sign(y||sign)*.029,0]);',
         '        mesh(rod, cyl(ZEPHYR_TRISTAFF_SIZE_V24.lipTopRadius,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.lipBottomRadius,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.lipLength,12), ferrule,\n'
         '          [0,y+Math.sign(y||sign)*ZEPHYR_TRISTAFF_SIZE_V24.ferruleLength*.415,0]);',
         'thin metal lips'),
        ('        mesh(rod, torus(.036,.046), red, [0,y-Math.sign(y||sign)*.048,0]);',
         '        mesh(rod, torus(ZEPHYR_TRISTAFF_SIZE_V24.ringInnerRadius,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.ringOuterRadius), red,\n'
         '          [0,y-Math.sign(y||sign)*ZEPHYR_TRISTAFF_SIZE_V24.ferruleLength*.686,0]);',
         'thin decorative rings'),
        ('      const hinge = pivot(root, [0, sign*.325, 0]);',
         '      const hinge = pivot(root, [0, sign*ZEPHYR_TRISTAFF_SIZE_V24.middleHalfLength, 0]);',
         'position chain at new middle-rod ends'),
        ('      // Exactly four overlapping metal links, 0.13 metres between rod ends.',
         '      // Exactly four linked rings bridge the larger, visible chain gap.\n'
         '      // The endpoints are separated by `chainGap`, including the cap overhang.',
         'chain comment'),
        ('        const link = pivot(prev, [0, sign*(k===0 ? .01625 : .0325), 0]);',
         '        const link = pivot(prev, [0, sign*(k===0 ?\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.chainGap/8 :\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.chainGap/4), 0]);',
         'link spacing'),
        ('        mesh(link, torus(.008,.022), ferrule, [0,0,0], [k%2 ? PI/2 : 0,0,k%2 ? PI/2 : 0]);',
         '        mesh(link, torus(ZEPHYR_TRISTAFF_SIZE_V24.chainLinkInner,\n'
         '          ZEPHYR_TRISTAFF_SIZE_V24.chainLinkOuter), ferrule,\n'
         '          [0,0,0], [k%2 ? PI/2 : 0,0,k%2 ? PI/2 : 0]);',
         'visible linked chains'),
        ('      // Final half-link completes a real 0.13-unit gap.',
         '      // Final half-link joins the far rod, preserving the visible chain gap.',
         'last link comment'),
        ('      const end = pivot(prev,[0,sign*.01625,0]);',
         '      const end = pivot(prev,[0,sign*ZEPHYR_TRISTAFF_SIZE_V24.chainGap/8,0]);',
         'end rod hinge offset'),
    )
    for old, new, label in modifications:
        part = replace_once(part, old, new, label)

    if 'this.bladeTip = this.dragonSockets["upper:far"];' not in part:
        raise RuntimeError('Missing preserved weapon-tip socket; no files changed.')
    if 'this.dragonGhost = root.clone(true);' not in part:
        raise RuntimeError('Missing cosmetic toss clone; no files changed.')
    source = source[:begin] + part + source[end:]

    # Keep procedural hand-pivot scale consistent with the smaller weapon. The
    # real *detached* geometry is scaled above; these are different hierarchies.
    old = 'this.kit === "tristaff" ? 0.79 : VRM_WEAPON_SCALE;'
    new = 'this.kit === "tristaff" ? ZEPHYR_TRISTAFF_SIZE_V24.globalScale : VRM_WEAPON_SCALE;'
    source = replace_once(source, old, new, 'tristaff hand-pivot scale')
    assert MARK in source
    return source



# ZEPHYR_V25_MODE_BALANCE: all new numbers are in the game\'s existing
# DRAGON_MODE_TUNING table after installation, not hidden in game logic.
VERSION = 'ZEPHYR_MODE_BALANCE_V25'
FILE_SET = ('src/game/model.ts', 'src/game/fighter.ts', 'src/game/kits.ts',
            'src/game/game.ts', 'src/game/ai.ts', 'src/ui/GameView.tsx',
            'src/game/roster.ts')


def req(s: str, old: str, new: str, what: str) -> str:
    return replace_once(s, old, new, what)


def patch_fighter(s: str) -> str:
    if VERSION in s:
        raise RuntimeError('V25 already installed; refusing to apply twice.')
    if 'ZEPHYR_DRAGON_SWITCH_SPLIT_V20' not in s or 'DRAGON_MODE_TUNING' not in s:
        raise RuntimeError('Need Zephyr V20+ fighter code before installing V25.')
    # Place every balance parameter in the existing mode table, one row each.
    s=req(s, 'splitExitInvuln: 0.00 }, // STAFF',
          'splitExitInvuln: 0.00, staffShieldRaise: 0.012, staffChargedGuardMult: 2.00 }, // STAFF',
          'Staff shield and charged guard tuning')
    s=req(s, 'splitExitInvuln: 0.00 }, // WHIP',
          'splitExitInvuln: 0.00, whipArcDot: -0.45, whipVisualArcMult: 1.35 }, // WHIP',
          'Whip arc tuning')
    s=req(s, 'splitExitInvuln: 0.00 }, // FOLDED',
          'splitExitInvuln: 0.00, foldedAttackSpeed: 1.50 }, // FOLDED',
          'Folded speed tuning')
    s=req(s,
          '  const result={...selected, reach:selected.reach*m.reach, guard:selected.guard*m.guard};',
          '''  const result={...selected, reach:selected.reach*m.reach, guard:selected.guard*m.guard};
  // ZEPHYR_MODE_BALANCE_V25: 2x guard pressure only on STAFF charged heavy.
  if (safeMode===0 && attack.id==="heavy")
    result.guard *= DRAGON_MODE_TUNING[0].staffChargedGuardMult;
  // Whip hits use the wider real melee sector; C retains its own behind-the-back coverage.
  if (safeMode===2) result.dragonArcDot=DRAGON_MODE_TUNING[2].whipArcDot;''',
          'mode resolved attacks')
    s=req(s,
          '  if (result.style==="zephyr_reversal") result.duration*=m.counter;',
          '''  // Folded is 1.5x total animation speed on basics, heavy, Z/X/C and V.
  // Apply AFTER the mode's normal startup/recovery multipliers; cooldowns and
  // special counter duration remain untouched.
  if (safeMode===3) {
    const speed=DRAGON_MODE_TUNING[3].foldedAttackSpeed;
    result.wind/=speed; result.active/=speed; result.recover/=speed;
  }
  if (result.style==="zephyr_reversal") result.duration*=m.counter;''',
          'Folded attack-speed multiplier')
    s=req(s,
          '      this.shieldRaise = this.nextShieldFast ? 0.01 : 0.10;',
          '''      // ZEPHYR_MODE_BALANCE_V25: STAFF can raise guard nearly instantly.
      this.shieldRaise = this.kit==="tristaff" && this.dragonMode===0
        ? DRAGON_MODE_TUNING[0].staffShieldRaise
        : (this.nextShieldFast ? 0.01 : 0.10);''',
          'mode-specific guard raise')
    # The new marker lives on an already-modified line, so no duplicate apply.
    if VERSION not in s:
        raise RuntimeError('Fighter version marker not inserted.')
    return s


def patch_kits(s: str) -> str:
    if 'dragonArcDot?: number' in s:
        raise RuntimeError('Whip arc field appears already installed.')
    return req(s,
       '  dragonCounterDamage?: number; dragonArmor?: boolean; dragonBehind?: boolean;',
       '  dragonCounterDamage?: number; dragonArmor?: boolean; dragonBehind?: boolean;\n'
       '  /** ZEPHYR_MODE_BALANCE_V25: forward-cone threshold, lower = wider. */\n'
       '  dragonArcDot?: number;',
       'optional whip arc attack field')


def patch_game(s: str) -> str:
    # This is not a parry bypass. Defender parries still nullify damage, earn
    # normal counter rewards, and slow multi-hit followups; only Zephyr's
    # parry-specific self recoil is skipped in SPLIT mode.
    s=req(s,
       '          if (!ranged && a.type === "melee") attacker.applyParryRecoil(0.50);\n          else attacker.model.recoil = Math.max(attacker.model.recoil, 0.35);',
       '''          // ZEPHYR_MODE_BALANCE_V25: SPLIT is a committed no-guard offense.
          // A successful enemy parry still works, but does not apply attacker recoil.
          if (!ranged && a.type === "melee") {
            if (!(attacker.kit==="tristaff" && attacker.dragonMode===1))
              attacker.applyParryRecoil(0.50);
          } else attacker.model.recoil = Math.max(attacker.model.recoil, 0.35);''',
       'SPLIT parry recoil')
    s=req(s,
       '(dist > 0.6 && dir.dot(fwd) < (a.dragonBehind ? -1 : antiAir ? -0.08 : 0.15))) continue;',
       '(dist > 0.6 && dir.dot(fwd) < (a.dragonBehind ? -1 :\n'
       '            a.dragonArcDot !== undefined ? a.dragonArcDot : antiAir ? -0.08 : 0.15))) continue;',
       'actual WHIP melee width')
    # V25 HUD FIX: The React HUD reads me.dragonMode, but Game.hud().info()
    # previously omitted it, so every player-vs-CPU display fell back to STAFF.
    # This is a *local UI field*, not an additional network snapshot field.
    s=req(s,
       'chainBindKind: f.chainBindKind, dragonRhythm: f.dragonRhythm, dragonRhythmT: f.dragonRhythmT, gravityMode: f.gravityMode, gravitySwitchCd: f.gravitySwitchCd,',
       'chainBindKind: f.chainBindKind, dragonRhythm: f.dragonRhythm, dragonRhythmT: f.dragonRhythmT, dragonMode: f.dragonMode, dragonModeCd: f.dragonModeCd, gravityMode: f.gravityMode, gravitySwitchCd: f.gravitySwitchCd, // ZEPHYR_MODE_HUD_SYNC_V25',
       'player-versus-CPU live mode field')
    return s


def patch_model(s: str) -> str:
    # This complements the real melee arc (the visible rod/chains swing wider).
    s=req(s,
       '    const spin=show?phase*Math.PI*1.8:key==="c"?p*Math.PI*8:',
       '''    // ZEPHYR_MODE_BALANCE_V25: widen WHIP's actual visual swing, not only its hit cone.
    const baseSpin=show?phase*Math.PI*1.8:key==="c"?p*Math.PI*8:''',
       'Whip visual arc start')
    s=req(s,
       'key==="l3"||key==="l4"?p*Math.PI*2.4:key==="idle"?Math.sin(this.t*1.5)*.35:p*.85;',
       '''key==="l3"||key==="l4"?p*Math.PI*2.4:key==="idle"?Math.sin(this.t*1.5)*.35:p*.85;
    const spin=mode===2 && key!=="idle" && !show
      ? baseSpin*1.35 : baseSpin;''',
       'Whip visual arc factor')
    s=req(s, 'if(mode===2)targetZ+=sign*.28*Math.sin(this.t*6+spin*.7+i);',
       'if(mode===2)targetZ+=sign*.40*Math.sin(this.t*6+spin*.7+i);',
       'Whip chain reach and overswing')
    return s


def patch_ai(s: str) -> str:
    if VERSION in s:
        raise RuntimeError('AI V25 already installed.')
    s=req(s,
       'import { Fighter, S, HOLD_T, type Brain } from "./fighter";',
       'import { Fighter, S, HOLD_T, DRAGON_MODE_TUNING, type Brain } from "./fighter";',
       'AI references existing mode table')
    # Keep staff's REAL faster startup consistent with AI calculations.
    s=req(s,
       '(f.nextShieldFast ? 0.01 : 0.10) + 0.035;',
       '(f.kit==="tristaff" && f.dragonMode===0 ? DRAGON_MODE_TUNING[0].staffShieldRaise :\n'
       '          (f.nextShieldFast ? 0.01 : 0.10)) + 0.035;',
       'AI shield readiness estimate')
    old='const raise = f.nextShieldFast ? 0.01 : 0.10;'
    hits=s.count(old)
    if hits<3 or hits>8:
        raise RuntimeError(f'AI shield raise anchor changed (found {hits}); no files changed.')
    new='const raise = f.kit==="tristaff" && f.dragonMode===0 ?\n      DRAGON_MODE_TUNING[0].staffShieldRaise : (f.nextShieldFast ? 0.01 : 0.10);'
    s=s.replace(old,new)
    # Keep behavior deliberate, not a per-frame guard spam loop.
    anchor='  // ZEPHYR_DRAGON_SWITCH_SPLIT_V20: close-range Split pressure uses alternate'
    block='''  // ZEPHYR_MODE_BALANCE_V25: genuine mode-aware decisions, normal inputs only.
  private zephyrV25ModeCombat(f:Fighter,o:Fighter):boolean {
    if(f.kit!=="tristaff" || f.isDown() || f.state!==S.IDLE || f.atkLock>0)return false;
    const dist=f.root.position.distanceTo(o.root.position);
    const incoming=o.state===S.ATTACK && o.atk?.type==="melee" &&
      o.atkPhase===0 && (o.atk.wind-o.stateT)>0.025;
    if(f.dragonMode===0){
      // Lightning-fast STAFF guard is worthwhile against observed windups.
      if(incoming && dist<(o.atk?.reach??2)+0.25 && f.guard>f.maxGuard*.25 &&
         !f.intent.skill && !f.intent.attack){
        f.intent.block=true; return true;
      }
      // The charged staff is for already-low guard; don't spam it into full guard.
      if(o.state===S.BLOCK && o.guard<o.maxGuard*.42 && dist<2.42 &&
         this.queue.length===0 && !f.intent.block){
        this.queue.push([0,HOLD_T+0.43]); return true;
      }
    }
    if(f.dragonMode===2 && !incoming && dist>1.85 && dist<3.05 &&
       f.cooldowns.z<=0 && o.state!==S.STAGGER && !f.intent.block &&
       !f.intent.skill && this.skillCd<=0.25){
      // Whip's new wide arc can punish sidestepping opponents.
      f.intent.skill="z"; this.skillCd=1.0; return true;
    }
    if(f.dragonMode===3 && dist<1.87 &&
       (o.state===S.STAGGER || o.state===S.HITSTUN ||
         (o.state===S.ATTACK && o.atkPhase===2)) &&
       !f.intent.skill && !f.intent.block){
      // Use actual 1.5x Folded basics to punish visible recovery.
      f.intent.attack=true; return true;
    }
    return false;
  }

'''
    s=req(s,anchor,block+anchor,'mode-aware AI combat')
    s=req(s,
       '    const danger=gap<1.45 && o.state===S.ATTACK && o.atkPhase===0;\n    const desired=gap>3.0?2:gap>1.75?0:danger?3:1;',
       '''    // Prefer fast STAFF defense against visible threats and 2x guard pressure
    // when an opponent is close to a guard break; Folded can punish recovery.
    const danger=gap<2.25 && o.state===S.ATTACK && o.atkPhase===0;
    const guardBreak=gap<2.45 && o.state===S.BLOCK && o.guard<o.maxGuard*.42;
    const punish=gap<1.80 && (o.state===S.HITSTUN || o.state===S.STAGGER ||
      (o.state===S.ATTACK && o.atkPhase===2));
    const desired=gap>2.85?2:danger||guardBreak?0:punish?3:gap>1.85?0:1;''',
       'adaptive Zephyr mode choice')
    s=req(s,'    this.zephyrModeCooldown=1.10;',
       '    this.zephyrModeCooldown=1.55; // ZEPHYR_MODE_BALANCE_V25: avoid flicker',
       'AI mode hysteresis')
    s=req(s,'    if (this.zephyrSplitPlan(f,o)) return;',
       '    if (this.zephyrV25ModeCombat(f,o)) return;\n    if (this.zephyrSplitPlan(f,o)) return;',
       'AI mode action priority')
    s=req(s,
       '  const reach = style ? (RANGED.has(f.kit) ? 9 : style.range + 0.24)',
       '  const reach = f.kit==="tristaff" && f.dragonMode===2 ? 3.12 :\n'
       '    f.kit==="tristaff" && f.dragonMode===3 ? 1.93 :\n'
       '    style ? (RANGED.has(f.kit) ? 9 : style.range + 0.24)',
       'AI uses relevant mode reach')
    s=req(s,
       '  // Zenith: landed basics build +0.01x Tempo (5s); ONLY skills inflict x2 Bleed;',
       '''  // ZEPHYR_MODE_BALANCE_V25: use charged staff for weakened guards.
  if (id==="zephyr" && f.dragonMode===0 && blocked &&
      o.guard<o.maxGuard*.45) heavyChance=Math.max(heavyChance,.72);
  if (id==="zephyr" && f.dragonMode===3 && punish)
      heavyChance=Math.min(heavyChance,.20); // fast Folded light punish
  // Zenith: landed basics build +0.01x Tempo (5s); ONLY skills inflict x2 Bleed;''',
       'AI guardbreak and fast punish attack selection')
    return s


def patch_view(s: str) -> str:
    # The existing black HUD box already displays mode. Use its typed
    # live feed instead of an any-cast and the fallback 0 (STAFF).
    if 'MODE: ${["STAFF","SPLIT","WHIP","FOLDED"][(me as any).dragonMode ?? 0]}' not in s:
        raise RuntimeError('Missing Zephyr player mode label in GameView.tsx; no files changed.')
    if s.count('(me as any).dragonMode') != 2:
        raise RuntimeError('Unexpected Zephyr HUD mode references; no files changed.')
    s=s.replace('(me as any).dragonMode ?? 0', 'me.dragonMode', 1)
    s=s.replace('(me as any).dragonMode === 1', 'me.dragonMode === 1', 1)
    # Type comes from Game.hud().info() after patch_game(), so TypeScript will
    # catch future breaks instead of silently showing an incorrect fallback.
    return s


# ZEPHYR_V25_COMPLETE: incremental changes layered on top of the already
# preflight-validated V24 + V25 basic mode patch. Each edit is anchor checked.
FULL_VERSION = "ZEPHYR_FULL_BALANCE_RHYTHM_V25"


def patch_extra_fighter(s: str) -> str:
    if FULL_VERSION in s:
        raise RuntimeError('Zephyr V25 complete already installed. No files modified.')
    s = req(s,
        '  dragonRhythm = 0;\n  dragonRhythmT = 0;',
        '''  // ZEPHYR_FULL_BALANCE_RHYTHM_V25: values change only Zephyr, not the entire roster.
  // The three Rhythm stacks time out 25 seconds after the latest gain.
  dragonRhythm = 0;
  dragonRhythmT = 0;''',
        'Zephyr passive marker')
    s = req(s, '    this.dragonRhythmT = 7;',
            '    this.dragonRhythmT = ZEPHYR_PASSIVE_TUNING.rhythmSeconds;',
            '25 second Rhythm timer reset')
    s = req(s,
        '// ZEPHYR_DRAGON_VARIANTS_V19 — editable per-mode attacks.',
        '''// ZEPHYR_FULL_BALANCE_RHYTHM_V25: short-rebound sanjiekun gives additional
// survivability. Values are constants so HP/DR can be independently tuned.
export const ZEPHYR_PASSIVE_TUNING = {
  rhythmSeconds: 25,
  damageTakenMult: 0.80, // 20% less incoming HP damage
} as const;

// ZEPHYR_DRAGON_VARIANTS_V19 — editable per-mode attacks.''',
        'passive tuning constant')
    s = req(s,
        'splitAlternateSpeedMult: 0.77, splitExitInvuln: 0.08 }, // SPLIT',
        'splitAlternateSpeedMult: 0.37, splitClickSpeedCap: 2.00, splitExitInvuln: 0.08 }, // SPLIT',
        'Split alternation speed cap tuning')
    # A Split strike always comes from a human/CPU click, never a timer-generated extra hit.
    s = req(s,
        '  private dragonSplitQueued: "r"|"l"|""="";\n  private dragonSplitStrike(hand: "r"|"l") {\n    this.dragonSplitQueued="";\n    this.holding=false; this.atkPrev=false;\n    this.startAttack(hand==="r"?"split_r":"split_l");\n  }',
        '''  private dragonSplitQueued: "r"|"l"|""="";
  private dragonSplitLastStart = -99;
  /** Normal unboosted Split hit cycle; the minimum interval is half when alternating. */
  private dragonSplitMinInterval(hand: "r"|"l"): number {
    const base = DRAGON_VARIANTS[1].split_r!;
    const m = DRAGON_MODE_TUNING[1];
    const total = (base.wind ?? 0.12)*m.wind + (base.active ?? 0.07) +
      (base.recover ?? 0.19)*m.recover;
    const alternating = !!this.dragonLastHand && this.dragonLastHand !== hand;
    return total / (alternating ? m.splitClickSpeedCap : 1);
  }
  private dragonSplitStrike(hand: "r"|"l") {
    this.dragonSplitQueued="";
    this.holding=false; this.atkPrev=false;
    this.dragonSplitLastStart=this.clock;
    // Each click starts one real melee contact. The interval guard in attackStep
    // prevents skipping more than half the ordinary Split attack cycle.
    this.startAttack(hand==="r"?"split_r":"split_l");
  }''',
        'Split click timing state')
    s = req(s,
        '''      if(splitPressed && !this.chainBoundBy && this.parryRecoilT<=0 && this.atkLock<=0) {
        if(this.state===S.IDLE||this.state===S.BLOCK)
          this.dragonSplitStrike(hand);
        else if(this.state===S.ATTACK) this.dragonSplitQueued=hand;
      }''',
        '''      if(splitPressed && !this.chainBoundBy && this.parryRecoilT<=0 && this.atkLock<=0) {
        if((this.state===S.IDLE||this.state===S.BLOCK) &&
           this.clock-this.dragonSplitLastStart>=this.dragonSplitMinInterval(hand))
          this.dragonSplitStrike(hand);
        else if(this.state===S.ATTACK) this.dragonSplitQueued=hand;
      }''',
        'Split click input buffering')
    s = req(s,
        '''    if(this.kit==="tristaff" && this.dragonMode===1 && this.dragonSplitQueued &&
       this.state===S.ATTACK && this.stateT>=w+ac+0.025) {
      const hand=this.dragonSplitQueued;
      this.dragonSplitStrike(hand);return;
    }''',
        '''    // ZEPHYR_FULL_BALANCE_RHYTHM_V25: input driven; no phantom auto-combos.
    // Contact on the earlier swing must resolve first. Alternating hands allows
    // a maximum 2x base cadence, repeating a hand uses the normal full cycle.
    if(this.kit==="tristaff" && this.dragonMode===1 && this.dragonSplitQueued &&
       this.state===S.ATTACK && this.stateT>=w+ac &&
       this.clock-this.dragonSplitLastStart>=this.dragonSplitMinInterval(this.dragonSplitQueued)) {
      const hand=this.dragonSplitQueued;
      this.dragonSplitStrike(hand);return;
    }''',
        'queued Split attack timing')
    # Existing alternating multiplier remains, but is now 0.37 instead of 0.77.
    # This drives actual wind/recovery, not an automatic extra strike.
    s = req(s,
        '''    let dmg = a.dmg * power;
    if(this.kit==="tristaff"&&this.dragonMode===1)
      dmg*=DRAGON_MODE_TUNING[1].splitDamageTakenMult;''',
        '''    let dmg = a.dmg * power;
    // Sanjiekun resilience: the fighter has learned to absorb the three rods'
    // rebounds. SPLIT's +10% exposure is still applied on top (0.8 * 1.1).
    if(this.kit==="tristaff") dmg*=ZEPHYR_PASSIVE_TUNING.damageTakenMult;
    if(this.kit==="tristaff"&&this.dragonMode===1)
      dmg*=DRAGON_MODE_TUNING[1].splitDamageTakenMult;''',
        'Zephyr only damage reduction')
    # DOT hits do not pass through receiveHit; reduce separately for consistency.
    s = req(s,
        '''    for (const d of st.dots) {
      this.hp = Math.max(this.hp - d.dmg, 0);''',
        '''    for (const d of st.dots) {
      const dotDamage=this.kit==="tristaff" ?
        d.dmg*ZEPHYR_PASSIVE_TUNING.damageTakenMult*
        (this.dragonMode===1?DRAGON_MODE_TUNING[1].splitDamageTakenMult:1) : d.dmg;
      this.hp = Math.max(this.hp - dotDamage, 0);''',
        'Zephyr DOT damage reduction')
    # display the actual reduced DOT for Zephyr to keep visual floating numbers truthful
    s = req(s,
        '      if (d.dmg > 0) this.guardDelay = GUARD_REGEN_DAMAGE_DELAY;\n      this.dots.push({ ...d, src: this.status.src });',
        '      if (dotDamage > 0) this.guardDelay = GUARD_REGEN_DAMAGE_DELAY;\n      this.dots.push({ ...d, dmg: dotDamage, src: this.status.src });',
        'correct DOT visual damage')
    return s


def patch_extra_kits(s: str) -> str:
    return req(s,
        '  tristaff: { hp: 2225, guard: 82, move: 3.90, walk: 3.05, parry: 0.205, jump: 7.9 },',
        '  // ZEPHYR_FULL_BALANCE_RHYTHM_V25: 2225 * 1.20 = 2670 HP, unchanged guard.\n'
        '  tristaff: { hp: 2670, guard: 82, move: 3.90, walk: 3.05, parry: 0.205, jump: 7.9 },',
        '20 percent HP buff')


def patch_extra_model(s: str) -> str:
    # Drive noticeably mirrored left and right arm arcs instead of sharing the
    # same rod spin in the separate two-click hand strikes.
    s = req(s,
        '''    const spin=mode===2 && key!=="idle" && !show
      ? baseSpin*1.35 : baseSpin;''',
        '''    // Split click attacks have clearly opposing crossing sweeps. Body motion
    // gets its sign from dragonStrikeHand in the existing additive VRM layer.
    const spin=mode===1 && key==="split_r" ? p*Math.PI*1.42 :
      mode===1 && key==="split_l" ? -p*Math.PI*1.42 :
      mode===2 && key!=="idle" && !show ? baseSpin*1.35 : baseSpin;''',
        'opposing Split weapon sweeps')
    return s


def patch_extra_ai(s: str) -> str:
    # During SPLIT, plan alternating clicks even while the previous strike is
    # recovering; the fighter's own 2x timing gate decides the transition.
    s = req(s,
        '''    if(f.kit!=="tristaff"||f.dragonMode!==1||f.state!==S.IDLE)return false;''',
        '''    if(f.kit!=="tristaff"||f.dragonMode!==1||
       (f.state!==S.IDLE && !(f.state===S.ATTACK &&
         (f.atkId==="split_r" || f.atkId==="split_l"))))return false;''',
        'Split AI can queue next alternating click')
    return s


def patch_extra_view(s: str) -> str:
    s = req(s,
        '''                  {` DRAGON RHYTHM ${(me as any).dragonRhythm ?? 0}/3  ·  MODE: ${["STAFF","SPLIT","WHIP","FOLDED"][me.dragonMode]}${me.dragonMode === 1 ? "  ·  NO GUARD" : ""}`}''',
        '''                  {` DRAGON RHYTHM ${(me as any).dragonRhythm ?? 0}/3 · ${((me as any).dragonRhythmT ?? 0).toFixed(0)}s  ·  MODE: ${["STAFF","SPLIT","WHIP","FOLDED"][me.dragonMode]}${me.dragonMode === 1 ? "  ·  NO GUARD" : ""}`}''',
        'show live Rhythm timer; no narrative in battle HUD')
    return s


def patch_extra_roster(s: str) -> str:
    s = req(s,
        '    desc: "Technical staff master. Master five flowing grips, counter with Dragon Reversal and earn Rhythm through real catches, parries and clashes.",',
        '''    desc: "Dragon Rhythm: successful catches, parries, clashes and special strikes earn up to 3 stacks for 25 seconds (refreshed on gain). A lifetime of controlling a rebounding three-section staff—even being struck by his own weapon—gives Zephyr +20% HP and 20% less incoming damage. SPLIT gives up normal guard and takes slightly more damage. Rhythm strengthens his next finisher.",''',
        'Zephyr passive details only on roster info, not battle HUD')
    s = req(s,
        '    stats: { power: 4, speed: 4, range: 3, defense: 3 },\n    look: { name: "Zephyr",',
        '    stats: { power: 4, speed: 4, range: 3, defense: 4 },\n    look: { name: "Zephyr",',
        'Zephyr defensive stat indicator')
    return s


def main() -> int:
    base=Path(sys.argv[1] if len(sys.argv)>1 else '.').expanduser().resolve()
    print('ZEPHYR V25 COMPLETE — V24 + MODES + CLICK SPLIT + RESILIENCE + RHYTHM |',base)
    try:
        original={}
        for rel in (*FILE_SET,'src/game/roster.ts'):
            file=base/rel
            if not file.is_file():
                raise RuntimeError(f'Missing {rel}; run from fight-royale/web')
            original[rel]=file.read_text(encoding='utf-8-sig')
        if not re.search(r'id\s*:\s*[\'\"]zephyr[\'\"]',original['src/game/roster.ts']):
            raise RuntimeError('Zephyr is not installed; install the character before V25.')
        if VERSION in original['src/game/fighter.ts']:
            raise RuntimeError('V25 already installed. No files changed.')
        # Preflight EVERY patch in memory before writing ANY file.
        updated={}
        model=original['src/game/model.ts']
        if MARK not in model:
            model=update_model(model)
        updated['src/game/model.ts']=patch_extra_model(patch_model(model))
        updated['src/game/fighter.ts']=patch_extra_fighter(patch_fighter(original['src/game/fighter.ts']))
        updated['src/game/kits.ts']=patch_extra_kits(patch_kits(original['src/game/kits.ts']))
        updated['src/game/game.ts']=patch_game(original['src/game/game.ts'])
        updated['src/game/ai.ts']=patch_extra_ai(patch_ai(original['src/game/ai.ts']))
        updated['src/ui/GameView.tsx']=patch_extra_view(patch_view(original['src/ui/GameView.tsx']))
        updated['src/game/roster.ts']=patch_extra_roster(original['src/game/roster.ts'])
        changed={rel:out for rel,out in updated.items() if out!=original[rel]}
        if not changed:
            print('Nothing to change.');return 0
        stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup=base/'.zephyr-backups'/('v25-'+stamp)
        for rel in changed:
            target=backup/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(base/rel,target)
        written=[]
        try:
            for rel,content in changed.items():
                target=base/rel
                tmp=target.with_name(target.name+'.zephyr-v25-tmp')
                try:
                    tmp.write_text(content,encoding='utf-8')
                    tmp.replace(target)
                finally:
                    tmp.unlink(missing_ok=True)
                written.append(rel)
                print('  updated',rel)
        except Exception:
            for rel in written:shutil.copy2(backup/rel,base/rel)
            raise
        print('  - V24: shorter/slimmer detached weapon, larger visible chain gaps')
        print('  - SPLIT: enemy parry still works; Zephyr does not take extra parry recoil')
        print('  - STAFF: 0.012s shield raise, heavy charged attack 2x guard damage')
        print('  - WHIP: wider actual attack arc plus matching rod/chain sweeps')
        print('  - FOLDED: 1.5x windup, active and recovery speed; cooldown unchanged')
        print('  - AI: adapt stance selection, guardbreaks, defense and punishes')
        print('  - HUD: live mode, Split NO GUARD, 25s Rhythm timer')
        print('  - PASSIVE: +20% HP, 20% less incoming HP/DOT damage; 25s Rhythm stacks')
        print('  - SPLIT: alternating clicks up to 2x normal tempo, left/right arcs')
        print('  tuning: fighter.ts -> DRAGON_MODE_TUNING')
        print('  backup:',backup)
        print('Next: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
