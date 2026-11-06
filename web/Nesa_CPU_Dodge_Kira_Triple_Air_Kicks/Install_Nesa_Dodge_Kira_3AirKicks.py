#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale focused combat AI update.

* Enemy CPUs learn to *dodge Nesa*, rather than standing and blocking her
  armored hammer swings. Reaction chance/timing scales with AI difficulty.
* Kira can perform three independently connected aerial kicks per jump,
  with buffered clicks and different leg poses. They cannot be parried,
  but remain fully blockable and can clash with other melee attacks.
* Nothing changes Nesa's damage, cooldowns, Weight Passive, V6 charge
  duration, hammer, C charges, or other fighters' kits.

Run from Fight Royale's ``web`` directory:
    python Install_Nesa_Dodge_Kira_3AirKicks.py
Or pass the path to ``web`` as an argument.
Use ``--check`` to dry-run without changing files.
Backups live in ``web/.combat_ai_installer_backups``.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse
import os
import shutil
import sys
import tempfile

VERSION = "NESA_DODGE_KIRA_AIR_3_V1"
MARK = "NESA_DODGE_KIRA_AIR_3_V1"
FILES = ("src/game/ai.ts", "src/game/fighter.ts")

class PatchError(Exception):
    pass

def replace_once(text: str, old: str, new: str, label: str) -> str:
    found = text.count(old)
    if found != 1:
        raise PatchError(f"{label}: expected one anchor, found {found}")
    return text.replace(old, new, 1)


def project_root(spec: str | None):
    p = Path(spec).expanduser().resolve() if spec else Path.cwd()
    for q in (p, p / "web"):
        if (q / FILES[0]).is_file() and (q / FILES[1]).is_file():
            return q
    raise PatchError("Fight Royale 'web' folder not found. Run there or pass its folder path.")

AI_FIELDS = '''  // NESA_DODGE_KIRA_AIR_3_V1: dodge Nesa's dangerous hammer swings rather than merely guarding them.
  private nesaThreatSerial = -1;
  private nesaEvadeChosen = false;
  private nesaEvadeUsed = false;
  private nesaEvadeTrigger = 0;
  private nesaRetreatT = 0;
  private nesaDodgeSide = 1;
  private nesaRetreatDir = new THREE.Vector3();
'''

AI_METHOD = '''  /** NESA_DODGE_KIRA_AIR_3_V1: react to a *real* enemy hammer telegraph, not hidden hit data.
   * Each swing gets one difficulty-scaled dodge decision. A successful dodge
   * uses the ordinary dash input/cooldown and movement, with no AI-only i-frames.
   * It supersedes a pending block because Nesa's Weight Passive deals chip damage.
   * If the dash is cooling down, retreat normally instead of getting a free dodge.
   */
  private evadeNesa(f: Fighter, o: Fighter, dt: number): boolean {
    this.nesaRetreatT = Math.max(0, this.nesaRetreatT - dt);
    if (this.nesaRetreatT > 0 &&
        (f.state === S.IDLE || f.state === S.BLOCK) && !f.isDown()) {
      f.intent.move.copy(this.nesaRetreatDir);
      f.intent.block = false;
      f.intent.attack = false;
      f.intent.skill = "";
      return true;
    }
    const a = o.atk;
    if (o.kit !== "hammer" || o.state !== S.ATTACK || !a || f.isDown() ||
        (f.state !== S.IDLE && f.state !== S.BLOCK && f.state !== S.CHARGE)) return false;
    const flat = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = flat.length();
    const radius = a.type === "strike" ? Math.max(a.radius, 2.0) + 0.50 :
      Math.max(2.4, a.reach + Math.min(a.lunge * 0.28, 0.7)) + 0.42;
    if (gap > radius || Math.abs(o.root.position.y - f.root.position.y) > 2.1) return false;
    if (this.nesaThreatSerial !== o.swingSerial) {
      this.nesaThreatSerial = o.swingSerial;
      this.nesaEvadeUsed = false;
      // Easy ~37%, Normal ~58%, Hard ~72%, Master ~90%.
      this.nesaEvadeChosen = Math.random() < Math.min(0.94, 0.13 + this.p.block * 1.18);
      // Dash near the swing's contact time, not instantly at the first animation frame.
      const lead = 0.105 + this.p.react[1] * 0.28 + Math.random() * 0.025;
      this.nesaEvadeTrigger = Math.max(0.045, a.wind - lead);
      this.nesaDodgeSide = Math.random() < 0.5 ? -1 : 1;
    }
    if (!this.nesaEvadeChosen || this.nesaEvadeUsed || o.stateT < this.nesaEvadeTrigger ||
        o.stateT > a.wind + Math.min(a.active, 0.45)) return false;
    this.nesaEvadeUsed = true;
    const away = gap > 0.01 ? flat.multiplyScalar(-1 / gap) :
      new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y)).negate();
    const side = new THREE.Vector3(-away.z, 0, away.x).multiplyScalar(this.nesaDodgeSide);
    // Circle slams are best escaped radially; directional swings are sidestepped.
    const area = a.type === "strike" || a.style === "nesa_spin" ||
      a.style === "nesa_air_spin" || a.style === "nesa_high_striker";
    const escape = area ? away.addScaledVector(side, 0.38) :
      side.addScaledVector(away, 0.65);
    escape.normalize();
    this.nesaRetreatDir.copy(escape);
    this.nesaRetreatT = area ? 0.56 : 0.38;
    // Reset any shield/parry choice made for this same telegraph.
    this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
    this.queue = []; this.hold = 0;
    f.intent.attack = false;
    f.intent.skill = "";
    f.intent.block = false;
    f.intent.move.copy(escape);
    // Uses the real dash ability; on cooldown the CPU only walks out of range.
    if (f.dashCd <= 0 && (f.state === S.IDLE || f.state === S.BLOCK || f.state === S.CHARGE))
      f.intent.dash.copy(escape);
    return true;
  }

'''

AI_THINK_OLD = '''    // Run after normal chase/strafe choices, so fire can veto a dangerous route.
    this.avoidFireGround(f);
    this.antiAirCd = Math.max(0, this.antiAirCd - dt);'''
AI_THINK_NEW = '''    // Run after normal chase/strafe choices, so fire can veto a dangerous route.
    this.avoidFireGround(f);
    // NESA_DODGE_KIRA_AIR_3_V1: opponent dodges Nesa's real wind-up; leave
    // Nesa's own AI and every fighter's damage, guard and parry rules untouched.
    if (!f.stage && this.evadeNesa(f, o, dt)) return;
    this.antiAirCd = Math.max(0, this.antiAirCd - dt);'''

AI_KIRA_OLD = '''    if (!f.stage && !f.onGround && f.state === S.IDLE && !f.airSliceUsed &&
        flatGap < f.attacks.air_l1.reach + 0.20 &&'''
AI_KIRA_NEW = '''    if (!f.stage && !f.onGround &&
        (f.state === S.IDLE || (f.kit === "kicks" && f.state === S.ATTACK && /^air_l[1-3]$/.test(f.atkId))) &&
        !f.airSliceUsed &&
        flatGap < f.attacks.air_l1.reach + 0.20 &&'''

AI_KIRA_CD_OLD = '''      this.airSliceCd = rand(0.55, 0.85);'''
AI_KIRA_CD_NEW = '''      this.airSliceCd = f.kit === "kicks" ? rand(0.17, 0.24) : rand(0.55, 0.85);'''

FIGHTER_FIELDS = '''  // NESA_DODGE_KIRA_AIR_3_V1: Kira may deliver three separately timed air kicks per jump.
  private kiraAirKicks = 0;
  private kiraAirBuffered = false;
'''

FIGHTER_AIR_CONSTRUCTOR_ANCHOR = '''    this.root.rotation.order = "YXZ";'''
FIGHTER_AIR_CONSTRUCTOR = '''    // NESA_DODGE_KIRA_AIR_3_V1: Kira's three aerial kicks are standard melee hits:
    // the shield blocks them and overlapping attacks clash; perfect parry does not.
    if (this.kit === "kicks") {
      for (let i = 1; i <= 3; i++) {
        const key = `air_l${i}`;
        const original = this.attacks[key];
        this.attacks[key] = { ...original, type: "melee", no_parry: true,
          wind: 0.075, active: 0.085, recover: i === 3 ? 0.18 : 0.105,
          reach: 2.0 + 0.08 * (i - 1), lunge: 0,
          knock: i === 3 ? 2.1 : 0.8, heavy: false, stagger: false, next: "" };
      }
    }
    this.root.rotation.order = "YXZ";'''

FIGHTER_TRY_AIR_OLD = '''  private tryAirSlice() {
    if (this.onGround || this.airSliceUsed || this.atkLock > 0 ||
        (this.state !== S.IDLE && this.state !== S.BLOCK)) return;
    this.airSliceUsed = true;
    this.airSliceQueued = false;
    this.airSliceAngle = this.airAimAtOpponent();
    this.holding = false;
    this.startAttack("air_l1");
  }
'''
FIGHTER_TRY_AIR_NEW = '''  private tryAirSlice() {
    if (this.onGround || this.airSliceUsed || this.atkLock > 0 ||
        (this.state !== S.IDLE && this.state !== S.BLOCK)) return;
    // NESA_DODGE_KIRA_AIR_3_V1: 3 taps / connected kicks for Kira, one for others.
    if (this.kit === "kicks") this.kiraAirKicks = Math.min(3, this.kiraAirKicks + 1);
    this.airSliceUsed = this.kit !== "kicks" || this.kiraAirKicks >= 3;
    this.kiraAirBuffered = false;
    this.airSliceQueued = false;
    this.airSliceAngle = this.airAimAtOpponent();
    this.holding = false;
    this.startAttack(this.kit === "kicks" ? `air_l${this.kiraAirKicks}` : "air_l1");
  }
'''

FIGHTER_INPUT_OLD = '''    if (!this.stage && pressed && !this.onGround) {
      this.holding = false;
      this.tryAirSlice();
      return;
    }'''
FIGHTER_INPUT_NEW = '''    if (!this.stage && pressed && !this.onGround) {
      this.holding = false;
      if (this.kit === "kicks" && this.state === S.ATTACK &&
          /^air_l[1-3]$/.test(this.atkId) && this.kiraAirKicks < 3) {
        // Queue the next click during a kick; fire it when the active contact ends.
        this.kiraAirBuffered = true;
      } else this.tryAirSlice();
      return;
    }'''

FIGHTER_ATTACK_STEP_OLD = '''  private attackStep() {
    const a = this.atk!;
    const w = a.wind, ac = a.active, r = a.recover;'''
FIGHTER_ATTACK_STEP_NEW = '''  private attackStep() {
    const a = this.atk!;
    const w = a.wind, ac = a.active, r = a.recover;
    // NESA_DODGE_KIRA_AIR_3_V1: click-buffered second/third kicks during one jump.
    // Each starts a new real attack with its own collision and clash checks.
    if (this.kit === "kicks" && this.kiraAirBuffered && !this.onGround &&
        /^air_l[1-3]$/.test(this.atkId) && this.kiraAirKicks < 3 &&
        this.stateT >= w + ac) {
      this.kiraAirBuffered = false;
      this.kiraAirKicks++;
      this.airSliceUsed = this.kiraAirKicks >= 3;
      this.airSliceAngle = this.airAimAtOpponent();
      this.startAttack(`air_l${this.kiraAirKicks}`);
      return;
    }
'''

FIGHTER_POSE_CONDITION_OLD = '    if (!this.stage && this.state === S.ATTACK && this.atkId === "air_l1") {'
FIGHTER_POSE_CONDITION_NEW = '    if (!this.stage && this.state === S.ATTACK && (this.atkId === "air_l1" || (this.kit === "kicks" && /^air_l[2-3]$/.test(this.atkId)))) {'

FIGHTER_POSE_OLD = '''      p = `air_slice_${direction}_${this.atkPhase === 0 ? "w" : "s"}`;
      sp = this.atkPhase === 0 ? 20 : 44;'''
FIGHTER_POSE_NEW = '''      if (this.kit === "kicks") {
        const number = Math.max(1, Math.min(3, Number(this.atkId.slice(-1)) || 1));
        p = `kira_air_${number}_${direction}_${this.atkPhase === 0 ? "w" : "s"}`;
      } else p = `air_slice_${direction}_${this.atkPhase === 0 ? "w" : "s"}`;
      sp = this.atkPhase === 0 ? 24 : 56;'''

FIGHTER_POSES_OLD = '''      this.poses[`air_slice_${direction}_w`] = w;
      this.poses[`air_slice_${direction}_s`] = a;
    }
  }
'''
FIGHTER_POSES_NEW = '''      this.poses[`air_slice_${direction}_w`] = w;
      this.poses[`air_slice_${direction}_s`] = a;
      if (this.kit === "kicks") {
        // Three recognizable aerial kick beats (right, left, turning heel).
        for (let n = 1; n <= 3; n++) {
          const kw = copy(w), ks = copy(a);
          if (n === 2) {
            // Opposite leg initiates the second kick, with slight waist counterturn.
            const t0 = kw.leg_r; kw.leg_r = kw.leg_l; kw.leg_l = t0;
            const t1 = ks.leg_r; ks.leg_r = ks.leg_l; ks.leg_l = t1;
            kw.torso[1] -= 0.22; ks.torso[1] += 0.24;
          } else if (n === 3) {
            kw.torso[1] += 0.35; ks.torso[1] -= 0.42;
            kw.leg_r[0] -= 0.38; ks.leg_r[0] -= 0.55;
            kw.leg_l[0] += 0.30; ks.leg_l[0] += 0.25;
          }
          this.poses[`kira_air_${n}_${direction}_w`] = kw;
          this.poses[`kira_air_${n}_${direction}_s`] = ks;
        }
      }
    }
  }
'''


def patch_ai(src: str) -> str:
    if MARK in src:
        return src
    src = replace_once(src,
        '  private ignitionChoices = new Map<number, boolean>();',
        '  private ignitionChoices = new Map<number, boolean>();\n' + AI_FIELDS,
        'AI decision fields')
    src = replace_once(src,
        '  private jumpPulse = false;',
        AI_METHOD + '  private jumpPulse = false;',
        'AI evade method')
    src = replace_once(src, AI_THINK_OLD, AI_THINK_NEW, 'AI call for Nesa evade')
    src = replace_once(src, AI_KIRA_OLD, AI_KIRA_NEW, 'AI Kira air chain detection')
    src = replace_once(src, AI_KIRA_CD_OLD, AI_KIRA_CD_NEW, 'AI Kira air combo timing')
    return src


def patch_fighter(src: str) -> str:
    if MARK in src:
        return src
    src = replace_once(src, '  airSliceAngle = 0; // signed pitch toward the actual target, radians',
        '  airSliceAngle = 0; // signed pitch toward the actual target, radians\n' + FIGHTER_FIELDS,
        'Kira air usage fields')
    src = replace_once(src, FIGHTER_AIR_CONSTRUCTOR_ANCHOR, FIGHTER_AIR_CONSTRUCTOR,
        'Kira no-parry melee attack setup')
    src = replace_once(src, FIGHTER_TRY_AIR_OLD, FIGHTER_TRY_AIR_NEW,
        'three Kira air clicks per jump')
    src = replace_once(src, FIGHTER_INPUT_OLD, FIGHTER_INPUT_NEW,
        'buffer Kira airborne click')
    src = replace_once(src, FIGHTER_ATTACK_STEP_OLD, FIGHTER_ATTACK_STEP_NEW,
        'real separate aerial hit windows')
    src = replace_once(src, FIGHTER_POSE_CONDITION_OLD, FIGHTER_POSE_CONDITION_NEW,
        'Kira airborne pose selection across all three kicks')
    src = replace_once(src, FIGHTER_POSE_OLD, FIGHTER_POSE_NEW,
        'Kira three distinct directional poses')
    src = replace_once(src, FIGHTER_POSES_OLD, FIGHTER_POSES_NEW,
        'Kira differentiated kick pose generation')
    # Reset only when beginning a NEW jump, touching down, or character reset.
    # Restrict to assignment occurrences, never the class field declaration.
    src = src.replace('      this.airSliceUsed = false;\n',
                      '      this.airSliceUsed = false; this.kiraAirKicks = 0; this.kiraAirBuffered = false;\n')
    src = src.replace('        this.airSliceUsed = false;\n',
                      '        this.airSliceUsed = false; this.kiraAirKicks = 0; this.kiraAirBuffered = false;\n')
    src = src.replace('    this.airSliceUsed = false; this.airSliceQueued = false;',
                      '    this.airSliceUsed = false; this.kiraAirKicks = 0; this.kiraAirBuffered = false; this.airSliceQueued = false;')
    return src


def apply_updates(root: Path, dry_run: bool):
    changed: dict[str, bytes] = {}
    for relative in FILES:
        file = root / relative
        original = file.read_text(encoding='utf-8')
        updated = patch_ai(original) if relative.endswith('/ai.ts') else patch_fighter(original)
        if updated != original:
            changed[relative] = updated.encode('utf-8')
    print('Fight Royale project:', root)
    for rel in changed:
        print('[UPDATE]', rel)
    if dry_run:
        print('[CHECK] Patches verified; no files changed.')
        return
    if not changed:
        print('[OK] Nesa CPU dodge + Kira three-air-kick update is already installed.')
        return
    backup_dir = root / '.combat_ai_installer_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup_dir.mkdir(parents=True, exist_ok=False)
    for relative in changed:
        existing = root / relative
        backup = backup_dir / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(existing, backup)
    written: list[str] = []
    try:
        for relative, content in changed.items():
            destination = root / relative
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
                temp.write(content)
                staged = Path(temp.name)
            os.replace(staged, destination)
            written.append(relative)
    except Exception:
        for relative in written:
            shutil.copy2(backup_dir / relative, root / relative)
        raise
    print('[DONE] CPU can dodge Nesa, and Kira has 3 blockable / clashable / unparryable air kicks.')
    print('[BACKUP]', backup_dir)
    print('Next: npx tsc --noEmit -p . ; npm run dev')


def main():
    ap = argparse.ArgumentParser(description='Fight Royale: Nesa enemy dodge + Kira three aerial kicks')
    ap.add_argument('project', nargs='?', help='Fight Royale repo root or web folder')
    ap.add_argument('--check', action='store_true', help='Dry run, no source modifications')
    args = ap.parse_args()
    apply_updates(project_root(args.project), args.check)

if __name__ == '__main__':
    try:
        main()
    except (PatchError, OSError) as exc:
        print('INSTALL FAILED:', exc)
        sys.exit(1)
