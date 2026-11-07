#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale: AI understands 2-second guard recovery, actual swing timing,
non-parryable moves, and defensive spacing. AI-only decision changes plus a
read-only Fighter getter; no stat, damage, or cooldown changes.

Usage:
    python Install_FightRoyale_AI_Guard_Timing_Parry_V1.py
    python Install_FightRoyale_AI_Guard_Timing_Parry_V1.py "C:\\path\\to\\fight-royale\\web"
    python Install_FightRoyale_AI_Guard_Timing_Parry_V1.py --check

Requires the existing 2-second guard regeneration patch and AI Personality 2.0.
Backups: web/.fightroyale_ai_defense_backups/<timestamp>/.
Python 3.9+, no third-party packages.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

VERSION = "FIGHT_ROYALE_AI_GUARD_TIMING_PARRY_V1_20261107"
FILES = ("src/game/ai.ts", "src/game/fighter.ts")

class PatchError(RuntimeError):
    pass


def replace_one(src: str, old: str, new: str, tag: str) -> str:
    n = src.count(old)
    if n != 1:
        raise PatchError(f"{tag}: source anchor expected once, found {n}. Your game may have changed; nothing was written.")
    return src.replace(old, new, 1)


def replace_between(src: str, start: str, end: str, new: str, tag: str) -> str:
    a = src.find(start)
    b = src.find(end, a + len(start)) if a != -1 else -1
    if a < 0 or b < 0:
        raise PatchError(f"{tag}: cannot locate existing method boundaries; nothing was written.")
    if src.count(start) != 1:
        raise PatchError(f"{tag}: method marker is ambiguous.")
    return src[:a] + new + src[b:]


SMART_AI_FIELDS = '''  // FIGHT_ROYALE_AI_GUARD_TIMING_PARRY_V1_20261107
  // Real dash and positioning, never artificial invulnerability or free guard.
  private defensiveEvadeT = 0;
  private defensiveEvadeDash = false;
  private defensiveEvadeDir = new THREE.Vector3();

'''

SMART_AI_HELPERS = '''  /** Match Fighter.receiveHit: a non-parryable basic/special, or Veyr Festival.
   * Continuous specials remain parryable when the engine explicitly allows them.
   * No AI-only exception is granted; a clash remains a normal clash.
   */
  private cannotParryEnemy(o: Fighter): boolean {
    const a = o.atk;
    return !!a && ((o.kit === "sickle" && o.bloodFestivalT > 0 && a.type === "melee") ||
      (!!a.no_parry && !o.isContinuousComboActive()));
  }

  /** Start a real movement/dash defense, not a guaranteed dodge.
   * The arena and dash cooldown continue to decide if the escape succeeds.
   */
  private planDefensiveEvade(f: Fighter, o: Fighter, eta: number, dash: boolean) {
    if (f.isDown() || (f.state !== S.IDLE && f.state !== S.BLOCK && f.state !== S.CHARGE)) return;
    this.defensiveEvadeT = Math.max(0.24, Math.min(0.46, eta + 0.20));
    this.defensiveEvadeDash = dash && f.dashCd <= 0 && f.onGround;
    const plan = this.nesaSafeEscape(f, o, false, this.defensiveEvadeDash);
    this.defensiveEvadeDir.copy(plan.dir);
    this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
    this.comboParryTarget = -1;
    this.queue = []; this.hold = 0;
  }

  /** Damage resets guard recovery to two seconds. Don't waste a low guard bar
   * by holding shield while waiting for it to refill. Prefer safe spacing.
   */
  private respectGuardRecovery(f: Fighter, o: Fighter) {
    if (f.isDown() || f.stage || f.state !== S.IDLE ||
        f.guardRegenRemaining <= 0.04 || f.guard >= f.maxGuard * 0.46 ||
        this.defensiveEvadeT > 0) return;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    if (gap > 4.4 || this.hasPunishWindow(o)) return;
    // A committed block against an actual imminent hit is still legal; do not
    // forcibly turn it off. Merely avoid standing still with no pressure.
    if (this.blockHold > 0 || this.blockWait >= 0) return;
    const away = this.nesaSafeEscape(f, o, false, false).dir;
    f.intent.move.copy(away);
  }

  private applyDefensiveEvade(f: Fighter, o: Fighter, dt: number): boolean {
    if (this.defensiveEvadeT <= 0) return false;
    this.defensiveEvadeT = Math.max(0, this.defensiveEvadeT - dt);
    if (f.isDown() || ![S.IDLE, S.BLOCK, S.CHARGE].includes(f.state)) {
      this.defensiveEvadeT = 0; return false;
    }
    // Re-evaluate escape at the edge; otherwise the CPU may dodge into a wall.
    const plan = this.nesaSafeEscape(f, o, false, this.defensiveEvadeDash);
    const escape = f.stage
      ? new THREE.Vector3(Math.sign(plan.dir.x) || f.facing, 0, 0)
      : plan.dir;
    this.defensiveEvadeDir.copy(escape);
    f.intent.move.copy(escape);
    f.intent.block = false;
    f.intent.attack = false;
    if (this.defensiveEvadeDash && f.dashCd <= 0 && f.onGround) {
      f.intent.dash.copy(escape);
      this.defensiveEvadeDash = false;
    }
    this.blockWait = -1; this.blockHold = 0;
    return true;
  }

'''

REACT = '''  /** Watch the opponent's ACTUAL current attack animation. A fast wind-up
   * may be too short for the CPU's human-scale reaction + shield raise.
   * Unparryable moves never get a planned parry; low-guard CPU conserves guard
   * during its 2-second no-regeneration window.
   */
  private react(f: Fighter, o: Fighter) {
    if (o.state === S.ATTACK && o.atkPhase === 0 && o.atk?.type === "melee" &&
        o.swingSerial !== this.seenSwing) {
      if ([S.HITSTUN, S.STAGGER, S.KNOCKDOWN, S.WAKEUP].includes(f.state)) return;
      const a = o.atk;
      const eta = Math.max(0, a.wind - o.stateT);
      const reaction = rand(this.p.react[0], this.p.react[1]);
      const raise = f.nextShieldFast ? 0.01 : 0.10;
      const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
      const attackRange = a.reach + Math.min(Math.max(a.lunge, 0) * 0.13, 0.95) + 0.45;
      if (gap > attackRange + Math.min(eta * 2, 0.8)) return;
      this.seenSwing = o.swingSerial;
      const cannotParry = this.cannotParryEnemy(o);
      const recovering = f.guardRegenRemaining > 0.08;
      const guardLow = f.guard < f.maxGuard * 0.36;
      const guardBreakRisk = f.guard < Math.max(16, a.guard * 1.15);
      const timelyParry = !cannotParry && eta >= reaction + raise + 0.035;
      const timelyBlock = eta >= reaction + raise;
      const mayDash = f.dashCd <= 0 && f.onGround &&
        [S.IDLE, S.BLOCK, S.CHARGE].includes(f.state);
      const mayClash = f.state === S.IDLE && f.onGround &&
        f.attacks.l1?.type === "melee" &&
        gap < f.attacks.l1.reach + 0.32 &&
        eta + 0.07 >= f.attacks.l1.wind;
      const vulnerableGuard = guardLow || guardBreakRisk || (recovering && f.guard < f.maxGuard * 0.50);
      const decision = Math.random();

      // Zarek genuinely contests blade hits to build his existing Clash Momentum.
      if (f.kit === "glaive" && mayClash &&
          this.seenClashSwing !== o.swingSerial &&
          decision < this.p.block * (f.clashMomentum < 3 ? 0.55 : 0.29)) {
        this.seenClashSwing = o.swingSerial;
        this.blockWait = -1; this.blockHold = 0;
        this.queue = [[0, 0.065]]; this.hold = 0;
        return;
      }
      // Against a fast or unparryable attack, dodging is more useful than a
      // shield raise that cannot become a parry before the hit lands.
      const preferEvade = cannotParry || vulnerableGuard || !timelyParry;
      const evadeChance = cannotParry ? 0.46 + this.p.block * 0.55 :
        vulnerableGuard ? 0.42 + this.p.block * 0.53 : 0.20 + this.p.jump * 0.34;
      if (preferEvade && decision < evadeChance &&
          eta >= reaction * 0.80 &&
          (mayDash || (f.onGround && eta > reaction + 0.09))) {
        this.planDefensiveEvade(f, o, eta,
          mayDash && (vulnerableGuard || cannotParry || eta < reaction + raise));
        return;
      }
      if (vulnerableGuard && mayClash && decision < Math.min(0.9, evadeChance + 0.21)) {
        this.blockWait = -1; this.blockHold = 0;
        this.queue = [[0, 0.07]]; this.hold = 0;
        return;
      }
      // Fast attacks do not become artificially parryable. A normal block
      // can still work if its shield is raised early enough.
      if (!timelyParry && !timelyBlock) {
        // Fast attacks may beat this CPU's natural reaction; no perfect reflexes.
        if (eta >= reaction * 0.80 && mayDash && Math.random() < this.p.block)
          this.planDefensiveEvade(f, o, eta, true);
        else if (eta >= reaction * 0.80) {
          this.sideT = 0.20; this.sideSign = Math.random() < 0.5 ? 1 : -1;
        }
        return;
      }
      const blockDuration = Math.max(0.18, Math.min(o.isContinuousComboActive() ? 0.92 : 0.45,
        eta + a.active + 0.11));
      if (timelyParry && decision < this.p.parry &&
          !(vulnerableGuard && decision < this.p.parry * 0.28)) {
        // Shield is raised immediately before the true strike, not at attack start.
        this.schedule(Math.max(reaction, eta - raise - 0.03), 0.22);
      } else if (f.guard > Math.max(13, a.guard * 0.55)) {
        this.schedule(reaction, blockDuration);
      } else if (mayDash) {
        this.planDefensiveEvade(f, o, eta, true);
      }
      return;
    }

    // Charged attacks have a variable hold time: don't blindly shield for
    // 1.4 seconds before their actual release. Watch for the real swing.
    const charging = o.state === S.CHARGE;
    if (charging && !this.seenCharge) {
      this.seenCharge = true;
      const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
      if (gap < 3.4 && f.guardRegenRemaining > 0 &&
          f.guard < f.maxGuard * 0.50 && Math.random() < 0.48) {
        this.planDefensiveEvade(f, o, 0.35, false);
      }
    } else if (!charging) this.seenCharge = false;
  }

'''


def patch_fighter(s: str) -> str:
    if VERSION in s:
        return s
    if 'FIGHT_ROYALE_GUARD_REGEN_DAMAGE_DELAY_V1' not in s:
        raise PatchError('2-second guard recovery patch is missing. Install Install_FightRoyale_Guard_Regen_2s.py first.')
    return replace_one(s, '  private guardDelay = 0;\n',
        '  private guardDelay = 0;\n'
        f'  // {VERSION}: expose only the real remaining regeneration wait to CPU logic.\n'
        '  get guardRegenRemaining(): number { return Math.max(0, this.guardDelay); }\n',
        'Read-only guard recovery timer')


def patch_ai(s: str) -> str:
    if VERSION in s:
        return s
    if 'AI_PERSONALITY_THEATER_2_V1' not in s or 'private veyrFestivalPressure' not in s:
        raise PatchError('Existing AI Personality 2.0 / Veyr active-skill AI is missing. Install those first.')
    s = replace_one(s, '  private nesaGiantEvadeChosen = false;\n',
        '  private nesaGiantEvadeChosen = false;\n\n' + SMART_AI_FIELDS,
        'AI defense state')
    s = replace_one(s, '  private react(f: Fighter, o: Fighter) {\n',
        '  private react(f: Fighter, o: Fighter) {\n', 'React marker')  # assert once
    s = replace_between(s, '  private react(f: Fighter, o: Fighter) {\n',
        '  /** A continuous combo does not stop at the first successful parry or block. */', REACT, 'Real attack timing')
    s = replace_one(s, '  /** A continuous combo does not stop at the first successful parry or block. */',
        SMART_AI_HELPERS + '  /** A continuous combo does not stop at the first successful parry or block. */',
        'Defense helpers')
    s = replace_one(s,
        '    if ((festival || this.p.parry === 0) && this.blockWait < 0 && this.blockHold <= 0)\n'
        '      this.schedule(0, Math.min(1.8, Math.max(0.3, a.wind + a.active + a.recover)));',
        '    if ((festival || this.cannotParryEnemy(o) || this.p.parry === 0) &&\n'
        '        this.blockWait < 0 && this.blockHold <= 0) {\n'
        '      // Avoid stationary empty-shield spam during the real regen delay.\n'
        '      if (f.guardRegenRemaining > 0 && f.guard < f.maxGuard * 0.36 && f.dashCd <= 0)\n'
        '        this.planDefensiveEvade(f, o, Math.max(0.25, a.wind - o.stateT), true);\n'
        '      else if (f.guard > Math.max(12, a.guard * 0.48))\n'
        '        this.schedule(0, Math.min(1.25, Math.max(0.27, a.wind + a.active)));\n'
        '    }',
        'Conserve shield during continuous offense')
    s = replace_one(s,
        '        if (beat < now + raise + 0.075) continue;',
        '        // CPU must perceive the beat, then raise its shield.\n'
        '        if (beat < now + this.p.react[0] + raise + 0.035) continue;',
        'Continuous parry reaction speed')
    s = replace_one(s, '    if (!active || festival || this.p.parry <= 0 || f.isDown()) {',
        '    if (!active || festival || this.cannotParryEnemy(o) || this.p.parry <= 0 || f.isDown()) {',
        'Do not re-parry truly nonparryable continuous attacks')
    s = replace_one(s,
        '    if (!f.stage) { this.dodge(f); this.position(f, o, dt); this.tacticalFootwork(f, o, dt); this.theaterFootwork(f, o, dt); }',
        '    if (!f.stage) {\n'
        '      this.dodge(f); this.position(f, o, dt);\n'
        '      this.tacticalFootwork(f, o, dt); this.theaterFootwork(f, o, dt);\n'
        '      this.respectGuardRecovery(f, o);\n'
        '    }',
        'Guard recovery footwork')
    s = replace_one(s,
        '    if (!f.stage && this.evadeNesa(f, o, dt)) return;\n    this.antiAirCd =',
        '    if (!f.stage && this.evadeNesa(f, o, dt)) return;\n'
        '    const escapingDefense = this.applyDefensiveEvade(f, o, dt);\n'
        '    this.antiAirCd =',
        'Apply reaction-based evasion')
    s = replace_one(s,
        '    if (!this.aiAirTap && !this.readySkillOpportunity(f, o, dt) &&\n',
        '    if (!escapingDefense && !this.aiAirTap && !this.readySkillOpportunity(f, o, dt) &&\n',
        'Do not attack during defensive retreat')
    s = replace_one(s,
        '    if (this.aiAirTap) {\n      f.intent.jump = false;',
        '    if (this.aiAirTap && !escapingDefense) {\n      f.intent.jump = false;',
        'Do not override an actual escape with an air tap')
    s = replace_one(s,
        '    if (this.retimeComboParry(f, o)) return;\n',
        '    if (!escapingDefense && this.retimeComboParry(f, o)) return;\n',
        'Do not parry while escaping')
    s = replace_one(s,
        '    if (this.blockHold > 0) {\n      this.blockHold -= dt;',
        '    if (this.blockHold > 0 && !escapingDefense) {\n      this.blockHold -= dt;',
        'Do not hold block during defensive evasion')
    s = replace_one(s,
        '      else if (r < this.p.jump + this.p.block) this.schedule(Math.min(Math.max(eta - 0.2, 0), this.p.react[1]), eta + 0.2);',
        '      else if (r < this.p.jump + this.p.block) {\n'
        '        if (f.guardRegenRemaining > 0.05 && f.guard < f.maxGuard * 0.33 && f.onGround)\n'
        '          this.planDefensiveEvade(f, f.opponent as Fighter, eta, f.dashCd <= 0);\n'
        '        else this.schedule(Math.min(Math.max(eta - 0.2, 0), this.p.react[1]), eta + 0.2);\n'
        '      }',
        'Do not sacrifice empty guard to projectiles')
    return s


def root_from(raw: str | None) -> Path:
    p = Path(raw).expanduser().resolve() if raw else Path.cwd().resolve()
    for candidate in (p, p / 'web'):
        if all((candidate / x).is_file() for x in FILES):
            return candidate
    raise PatchError('Fight Royale web folder not found. Run from web or pass the web path.')


def main() -> None:
    parser = argparse.ArgumentParser(description='Smart AI defense: guard recovery, attack speed, no-parry attacks')
    parser.add_argument('project', nargs='?')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = root_from(args.project)
    originals = {rel: (root / rel).read_text(encoding='utf-8') for rel in FILES}
    changes = {
        'src/game/fighter.ts': patch_fighter(originals['src/game/fighter.ts']),
        'src/game/ai.ts': patch_ai(originals['src/game/ai.ts']),
    }
    changed = [p for p in FILES if originals[p] != changes[p]]
    if not changed:
        print('[OK] Smart AI guard timing/parry update already installed.')
        return
    if args.check:
        print('[CHECK PASSED]', ', '.join(changed))
        return
    backup = root / '.fightroyale_ai_defense_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True, exist_ok=False)
    for rel in changed:
        b = backup / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, b)
    # All anchors validated before first write, and backups already exist.
    for rel in changed:
        dst = root / rel
        tmp_name = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=dst.parent, delete=False) as h:
                tmp_name = h.name
                h.write(changes[rel])
            os.replace(tmp_name, dst)
        finally:
            if tmp_name and os.path.exists(tmp_name):
                os.unlink(tmp_name)
    print('[DONE] Smart AI now understands 2-second guard recovery, true swing timing, and no-parry attacks.')
    print('Files:', ', '.join(changed))
    print('Backup:', backup)
    print('No character damage, cooldowns, regeneration rates, or abilities were changed.')
    print('Next: npx tsc --noEmit -p .  &&  npm run dev')


if __name__ == '__main__':
    try:
        main()
    except (OSError, UnicodeError, PatchError) as e:
        print('[INSTALL ERROR]', e, file=sys.stderr)
        sys.exit(1)
