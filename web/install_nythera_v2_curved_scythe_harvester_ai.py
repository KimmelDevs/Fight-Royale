#!/usr/bin/env python3
"""Fight Royale — Nythera V2: sharper hooked reaper scythe + Harvester AI.

Run from fight-royale/web AFTER installing Nythera V1:
    python install_nythera_v2_curved_scythe_harvester_ai.py --dry-run
    python install_nythera_v2_curved_scythe_harvester_ai.py

Only edits src/game/model.ts and src/game/ai.ts.
Preflight checks, timestamped backups, atomic writes, rollback and idempotence.
No damage/cooldown/CC changes. Zenith/Zarek unchanged.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import os
import shutil
import sys
import tempfile

MARK = 'NYTHERA_REAPER_SCYTHE_HARVESTER_AI_V2_20261108'
MODEL = 'src/game/model.ts'
AI = 'src/game/ai.ts'
FILES = (MODEL, AI)


def once(buf: dict[str, str], path: str, anchor: str, replacement: str) -> None:
    count = buf[path].count(anchor)
    if count != 1:
        raise ValueError(f'{path}: expected exactly one preflight anchor, found {count}: {anchor[:100]!r}')
    buf[path] = buf[path].replace(anchor, replacement, 1)


def assemble(before: dict[str, str]) -> dict[str, str]:
    after = before.copy()
    if 'NYTHERA_GRAVITY_REAPER_INSTALL_V1' not in after[MODEL] or 'buildGravityScythe()' not in after[MODEL]:
        raise ValueError('Nythera V1 model not detected; install Nythera first')
    if 'gravityMode' not in after[AI] or 'private zenithV10Footwork(' not in after[AI]:
        raise ValueError('Nythera V1 with Zenith V12-era AI is required')

    # MODEL: only the Nythera-specific scythe shape and its actual visual markers.
    # The new blade is violet steel with a cool, sharpened silver-blue edge.
    once(after, MODEL,
        '    const dark = this.tn("#161528"), steel = this.tn("#d3d4e4");\n    const edgeSteel = this.tn("#eeeaff"), gold = this.tn("#ac8ac8");',
        '    const dark = this.tn("#181229"), steel = this.tn("#b79cdb");\n    const edgeSteel = this.tn("#c8ecff"), gold = this.tn("#d090d6");')
    once(after, MODEL, '''    shape.moveTo(-0.02, 0.73);
    shape.bezierCurveTo(-0.38, 0.99, -0.76, 1.17, -0.95, 1.67);
    shape.bezierCurveTo(-0.84, 1.56, -0.69, 1.51, -0.55, 1.48);
    shape.bezierCurveTo(-0.35, 1.42, -0.22, 1.21, -0.13, 1.04);
    shape.bezierCurveTo(-0.09, 0.91, -0.05, 0.82, -0.02, 0.73);
    shape.closePath();''', '''    // NYTHERA_REAPER_SCYTHE_HARVESTER_AI_V2_20261108
    // Back of the blade climbs high, then sweeps outward to a needle-sharp
    // hooked beak; concave lower edge is much thinner than Nythera V1.
    // This is a single blade, never a double-sided polearm.
    shape.moveTo(-0.024, 0.755);
    shape.bezierCurveTo(-0.20, 1.045, -0.36, 1.48, -0.60, 1.615);
    shape.bezierCurveTo(-0.88, 1.755, -1.17, 1.69, -1.365, 1.465);
    shape.bezierCurveTo(-1.09, 1.575, -0.83, 1.585, -0.64, 1.465);
    shape.bezierCurveTo(-0.39, 1.335, -0.24, 0.98, -0.024, 0.755);
    shape.closePath();''')
    once(after, MODEL,
        '''const geo = new THREE.ExtrudeGeometry(shape, { depth:0.033, bevelEnabled:true,
      bevelThickness:0.008, bevelSize:0.008, bevelSegments:2, curveSegments:22 });
    geo.translate(0,0,-0.0165);''',
        '''const geo = new THREE.ExtrudeGeometry(shape, { depth:0.021, bevelEnabled:true,
      bevelThickness:0.0045, bevelSize:0.003, bevelSegments:2, curveSegments:32 });
    geo.translate(0,0,-0.0105);''')
    once(after, MODEL,
        '''    const edgeCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.035,0.76,0.034), new THREE.Vector3(-0.33,1.00,0.034),
      new THREE.Vector3(-0.64,1.25,0.034), new THREE.Vector3(-0.95,1.67,0.034)]);
    mesh(scythe, new THREE.TubeGeometry(edgeCurve, 26, 0.009, 5, false), edgeSteel);''',
        '''    const edgeCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.06,0.83,0.015), new THREE.Vector3(-0.37,1.29,0.015),
      new THREE.Vector3(-0.68,1.49,0.015), new THREE.Vector3(-1.02,1.55,0.015),
      new THREE.Vector3(-1.365,1.465,0.015)]);
    mesh(scythe, new THREE.TubeGeometry(edgeCurve, 34, 0.0058, 5, false), edgeSteel);
    // Fine violet spine inlay, kept behind the silver cutting edge.
    const spineCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.13,0.91,0.014), new THREE.Vector3(-0.35,1.41,0.014),
      new THREE.Vector3(-0.66,1.61,0.014), new THREE.Vector3(-1.02,1.60,0.014)]);
    mesh(scythe, new THREE.TubeGeometry(spineCurve, 25, 0.004, 5, false), gold);''')
    once(after, MODEL,
        '''    this.bladeBase = pivot(scythe,[-0.18,0.98,0]);
    this.bladeTip = pivot(scythe,[-0.94,1.64,0]);''',
        '''    this.bladeBase = pivot(scythe,[-0.26,1.10,0]);
    this.bladeTip = pivot(scythe,[-1.36,1.465,0]);''')

    # AI: distinct profile so normals/spacing have a purpose before advanced planning.
    once(after, AI,
        '  zenith: { range: 2.10, heavy: 0.12, combo: 0.98, bait: 0.25, pressure: 1.00, skillBias: [1.45, 1.35, 1.10] },',
        '''  zenith: { range: 2.10, heavy: 0.12, combo: 0.98, bait: 0.25, pressure: 1.00, skillBias: [1.45, 1.35, 1.10] },
  // Nythera: orbit at the rim of a reaping arc; chain lights in Moonfloat,
  // then commit to Dreadfall once she observes real contact/recovery.
  nythera: { range: 2.31, heavy: 0.20, combo: 0.93, bait: 0.39, pressure: 0.84, skillBias: [1.28, 1.22, 0.74] },''')
    once(after, AI,
        '  zenith:  { role: "duelist", pressure: 1.85, probe: 0.63, reset: 0.17, vReserve: 0.89, spacing: -0.16 },',
        '''  zenith:  { role: "duelist", pressure: 1.85, probe: 0.63, reset: 0.17, vReserve: 0.89, spacing: -0.16 },
  nythera: { role: "duelist", pressure: 1.37, probe: 0.84, reset: 0.30, vReserve: 1.07, spacing: 0.07 },''')

    # Add the personal combat brain beside other character-specific planners.
    once(after, AI,
        '  private zenithSkillNextAt = 0;',
        '''  // NYTHERA_REAPER_SCYTHE_HARVESTER_AI_V2_20261108
  // "Orbit Harvester": Moonfloat gather -> airborne hook -> Dreadfall sentence.
  // Only reads the observable HP, locations, attacks and real own cooldowns.
  // It never reads the private Arena gravity-mark map or predicts player inputs.
  private nytheraOpponent: Fighter | null = null;
  private nytheraSeenHp = -1;
  private nytheraRecentContacts = 0;
  private nytheraLastContactAt = -100;
  private nytheraNextPlanAt = 0;
  private nytheraLastStanceAt = -100;
  private nytheraOrbitDir = 1;
  private nytheraOrbitFlipAt = 0;

  private nytheraV2Observe(o: Fighter): void {
    const now = this.threats.now();
    if (this.nytheraOpponent !== o) {
      this.nytheraOpponent = o;
      this.nytheraSeenHp = o.hp;
      this.nytheraRecentContacts = 0;
      this.nytheraLastContactAt = -100;
    }
    // Actual HP drops are evidence of contact, not hidden mark knowledge.
    if (o.hp < this.nytheraSeenHp - 0.4 && now - this.nytheraLastContactAt > 0.16) {
      if (now - this.nytheraLastContactAt > 3.8) this.nytheraRecentContacts = 0;
      this.nytheraRecentContacts = Math.min(4, this.nytheraRecentContacts + 1);
      this.nytheraLastContactAt = now;
    }
    this.nytheraSeenHp = o.hp;
    if (now - this.nytheraLastContactAt > 3.8) this.nytheraRecentContacts = 0;
  }

  private nytheraV2Plan(f: Fighter, o: Fighter): boolean {
    if (f.kit !== "scythe" || f.isDown() || o.isDown()) return false;
    const now = this.threats.now();
    if (now < this.nytheraNextPlanAt || f.intent.skill || f.intent.attack || f.intent.block ||
        f.intent.dash.lengthSq() > 0.01 || this.blockWait >= 0 || this.blockHold > 0 ||
        this.comboParryTarget > now || f.chainBoundBy || f.status.has("freeze")) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const verticalGap = Math.abs(o.root.position.y - f.root.position.y);
    const punish = this.hasPunishWindow(o) || o.stunRemaining > 0.18 ||
      o.state === S.STAGGER || o.state === S.HITSTUN;
    const threat = o.state === S.ATTACK && o.atkPhase <= 1 && !!o.atk &&
      gap < (o.atk.reach || 2.0) + 0.55;
    const ready = (k: "z" | "x" | "c" | "v") => !!f.attacks[k] &&
      (f.cooldowns[k] ?? 1) <= 0 && (k !== "v" || f.bonusSkillUnlocked);
    const act = (key: "z" | "x" | "c" | "v" | "f") => {
      this.queue = []; this.hold = 0;
      f.intent.attack = false;
      f.intent.skill = key;
      this.nytheraNextPlanAt = now + [0.96, 0.65, 0.38, 0.22][this.iqLevel];
      if (key === "f") {
        this.nytheraLastStanceAt = now;
        this.nytheraRecentContacts = 0;
      }
      return true;
    };

    // Aerial chase is a legal air-basic, not a teleport or forced enemy launch.
    if (!f.onGround) {
      if (f.gravityMode === "light" && f.state === S.IDLE &&
          o.root.position.y > 0.40 && gap < 2.15 && verticalGap < 1.55 &&
          this.iqLevel >= 1 && Math.random() < [0.08,0.38,0.67,0.86][this.iqLevel]) {
        this.queue = []; this.hold = 0;
        f.intent.attack = true;
        this.nytheraNextPlanAt = now + 0.43;
        return true;
      }
      if (f.gravityMode === "heavy" && f.state === S.IDLE && ready("x") &&
          gap < 2.5 && o.root.position.y < f.root.position.y &&
          Math.random() < [0.10,0.30,0.55,0.78][this.iqLevel]) return act("x");
      return false;
    }

    const free = f.state === S.IDLE || f.state === S.BLOCK ||
      (f.state === S.ATTACK && f.atkPhase === 2 && !!f.atk &&
       f.stateT >= f.atk.wind + f.atk.active + 0.08);
    if (!free || threat || verticalGap > 1.9) return false;

    // F is a real stance input. Mode swaps occur after observable setups,
    // not every time the opponent wobbles. Minimum 2.6s between decisions.
    const canShift = f.gravitySwitchCd <= 0 && now - this.nytheraLastStanceAt > 2.6;
    if (canShift && f.gravityMode === "light" && gap < 3.05 &&
        (this.nytheraRecentContacts >= 2 ||
          (this.nytheraRecentContacts >= 1 && punish && gap < 2.65))) {
      return act("f");
    }
    if (canShift && f.gravityMode === "heavy" &&
        (gap > 3.65 ||
         (now - this.nytheraLastStanceAt > 5.8 && !punish &&
          now - this.nytheraLastContactAt > 3.2))) {
      return act("f");
    }

    // CPU difficulty affects the chance to recognize an opening.
    if (Math.random() > [0.32, 0.56, 0.78, 0.94][this.iqLevel]) return false;
    if (f.gravityMode === "light") {
      // Moonfloat: catch an approach with Z, lift a recovering enemy with X,
      // or prepare Event Horizon to cut off a predictable rush lane.
      if (ready("x") && gap > 0.85 && gap < 2.54 &&
          (punish || (o.state === S.BLOCK && o.guard < o.maxGuard * 0.44))) return act("x");
      if (ready("z") && gap >= 1.35 && gap < 3.03 &&
          (punish || o.state === S.BLOCK || gap > 2.35)) return act("z");
      if (ready("c") && gap > 1.9 && gap < 3.55 &&
          (punish || o.state === S.IDLE) && this.iqLevel >= 1) return act("c");
      if (ready("v") && punish && gap < 2.65 && gap > 0.80 && this.iqLevel >= 2) return act("v");
    } else {
      // Dreadfall: spend a genuine punish window on execution instead of
      // waiting at range, or break a defending enemy's guard with a hook.
      if (ready("v") && punish && gap > 0.70 && gap < 2.75 && this.iqLevel >= 2) return act("v");
      if (ready("x") && gap < 2.62 && gap > 0.65 &&
          (punish || o.guard < o.maxGuard * 0.48)) return act("x");
      if (ready("z") && gap >= 1.18 && gap < 2.90 &&
          (punish || o.state === S.BLOCK)) return act("z");
      if (ready("c") && gap < 2.15 && gap > 0.50 && punish) return act("c");
    }
    this.nytheraNextPlanAt = now + [0.45,0.32,0.22,0.14][this.iqLevel];
    return false;
  }

  private nytheraV2Footwork(f: Fighter, o: Fighter): void {
    if (f.kit !== "scythe" || f.isDown() || o.isDown() || !f.onGround ||
        f.state !== S.IDLE || f.intent.skill || f.intent.attack || f.intent.block ||
        f.intent.dash.lengthSq() > 0.01 || this.blockWait >= 0 || this.blockHold > 0 ||
        this.comboParryTarget > this.threats.now() || this.queue.length > 0 || this.hold > 0) return;
    const toward = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = toward.length();
    if (gap < 0.10) return;
    toward.divideScalar(gap);
    if (o.state === S.ATTACK && o.atkPhase === 0 && o.atk?.type === "melee" &&
        gap < o.atk.reach + 0.65) return;
    const now = this.threats.now();
    if (now > this.nytheraOrbitFlipAt) {
      this.nytheraOrbitFlipAt = now + [2.0,1.62,1.25,1.0][this.iqLevel];
      if (Math.random() < 0.26) this.nytheraOrbitDir *= -1;
    }
    const side = new THREE.Vector3(-toward.z,0,toward.x).multiplyScalar(this.nytheraOrbitDir);
    const band = f.gravityMode === "light" ? 2.27 : 1.94;
    const steer = new THREE.Vector3();
    if (gap > band + 0.35) steer.copy(toward).addScaledVector(side,0.30);
    else if (gap < 1.03) steer.copy(side).addScaledVector(toward,-0.18);
    else steer.copy(side).addScaledVector(toward, gap > band ? 0.24 : -0.06);
    if (steer.lengthSq() < 0.001) return;
    steer.normalize();
    const future = f.root.position.clone().addScaledVector(steer,0.83).setY(0);
    if (future.length() > f.arenaRadius - f.radius - 0.40) {
      steer.copy(f.root.position).setY(0).negate();
      if (steer.lengthSq() < 0.001) return;
      steer.normalize();
    }
    f.intent.move.copy(steer).multiplyScalar(f.gravityMode === "light" ? 0.82 : 0.91);
  }

  private zenithSkillNextAt = 0;''')

    # Retire V1's naive spam toggle (it would race the V2 planner).
    once(after, AI,
        '''    // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — AI builds marks in Light,
    // switches to Heavy only near a confirmed punish window, then floats to chase.
    if (f.kit === "scythe" && f.gravitySwitchCd <= 0 && f.state === S.IDLE &&
        !f.intent.skill && !f.intent.attack && !f.intent.block) {
      const dist = f.root.position.distanceTo(o.root.position);
      const closePunish = dist < 2.55 && (o.stunRemaining > 0.13 ||
        o.state === S.STAGGER || o.state === S.ATTACK && o.atkPhase === 2);
      if (f.gravityMode === "light" && closePunish) f.intent.skill = "f";
      if (f.gravityMode === "heavy" && dist > 3.25) f.intent.skill = "f";
    }''',
        '''    // V2 Nythera measures actual damage and recovery; her dedicated planner
    // selects F and skills later, AFTER emergency block/dodge logic has run.
    if (f.kit === "scythe") this.nytheraV2Observe(o);''')
    once(after, AI,
        '''    const landedActed = !this.aiAirTap && !f.intent.skill &&
      this.aerialLandingPunish(f, o);
    // Roxy's kit plan runs BEFORE normal combo/pattern reads starve her skills.''',
        '''    const landedActed = !this.aiAirTap && !f.intent.skill &&
      this.aerialLandingPunish(f, o);
    // Nythera's three-phase Harvester AI gets first use of actual neutral openings.
    // Returning after a planned action keeps generic AI from overwriting F/Z/X/C/V.
    if (!landedActed && !this.aiAirTap && !f.intent.skill && this.nytheraV2Plan(f, o)) return;
    // Roxy's kit plan runs BEFORE normal combo/pattern reads starve her skills.''')
    once(after, AI,
        '''      this.advancedFootwork(f, o, dt);
      this.zenithV10Footwork(f, o);
      this.avoidFireGround(f);''',
        '''      this.advancedFootwork(f, o, dt);
      this.zenithV10Footwork(f, o);
      this.nytheraV2Footwork(f, o);
      this.avoidFireGround(f);''')
    once(after, AI,
        '''    if (f.look.element === "metal" && f.kit === "glaive") return false;''',
        '''    if (f.look.element === "metal" && f.kit === "glaive") return false;
    if (f.kit === "scythe") return false; // Nythera has her own cooldown-aware planner.''')
    once(after, AI,
        '''if (id !== "zenith" && skill && (punish || Math.random() < 0.80) && this.trySkill(f, skill, true)) return;''',
        '''if (id !== "zenith" && id !== "nythera" && skill &&
        (punish || Math.random() < 0.80) && this.trySkill(f, skill, true)) return;''')
    return after


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('web', nargs='?', default='.', help='fight-royale/web folder')
    parser.add_argument('--dry-run', action='store_true', help='Check all anchors without writing anything')
    args = parser.parse_args()
    root = Path(args.web).resolve()
    try:
        before = {p: (root / p).read_text(encoding='utf-8-sig') for p in FILES}
    except OSError as exc:
        sys.exit(f'ERROR: Run from fight-royale/web (or provide its path): {exc}')
    if MARK in before[MODEL] or MARK in before[AI]:
        if MARK in before[MODEL] and MARK in before[AI]:
            print('Nythera V2 already installed. No changes needed.')
            return
        sys.exit('PREFLIGHT ERROR: Partial V2 marker detected. Restore backup before retrying.')
    try:
        after = assemble(before)
    except ValueError as exc:
        sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')
    if args.dry_run:
        print('DRY RUN OK: Nythera V2 scythe model and AI anchors all match. No files changed.')
        return
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backups: dict[str, Path] = {}
    try:
        for p in FILES:
            source = root / p
            backup = source.with_name(f'{source.name}.before_nythera_v2_{stamp}.bak')
            shutil.copy2(source, backup)
            backups[p] = backup
        for p in FILES:
            dest = root / p
            handle, temp_path = tempfile.mkstemp(prefix=f'.{dest.name}.nytherav2.', suffix='.tmp', dir=dest.parent)
            try:
                with os.fdopen(handle, 'w', encoding='utf-8', newline='') as f:
                    f.write(after[p])
                os.replace(temp_path, dest)
                print('Updated:', p)
            finally:
                if os.path.exists(temp_path): os.unlink(temp_path)
    except Exception as exc:
        for p, backup in backups.items():
            try: shutil.copy2(backup, root / p)
            except OSError: pass
        sys.exit(f'WRITE ERROR: {exc}. Rollback attempted; backups preserved.')
    print('\nNythera V2 installed: sharply hooked crescent scythe + personal Orbit Harvester AI.')
    print('AI phases: Moonfloat mark pressure / air pursuit -> Dreadfall punish -> return to Moonfloat.')
    print('Unchanged: skill stats, damage, cooldowns, gravity mode mechanics, Zenith V12, Zarek.')
    print('Verify: npx tsc --noEmit -p .  &&  npm run build')


if __name__ == '__main__':
    main()
