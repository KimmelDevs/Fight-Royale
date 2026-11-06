#!/usr/bin/env python3
"""Fight Royale — Continuous Combo Parry AI V4 (2026-11-06).

For Fight Royale after install_combat_continuity_aster_ember_v3.py.
Place next to web/package.json and run:
    py install_continuous_parry_ai_v4.py

Changes:
* CPU anticipates every scheduled multi-hit beat and re-raises its shield to parry.
* Parryable ongoing combo hits, including Zarek's formerly no_parry-marked
  extended special sequences, can be parried without canceling the combo.
* Veyr Blood Festival's explicit parry immunity remains intact.
* Successful parry reduces NEXT shield raise time by 90%: 0.10s -> 0.01s.
* Continuous-combo parries keep dramatic slow-mo sparks, and the existing
  +0.20s interruption / 10% subsequent damage penalty (clash unchanged).

All preflight validation runs before any file is changed. Each change has a backup.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import shutil, sys

ROOT = Path(__file__).resolve().parent
FILES = ('src/game/ai.ts', 'src/game/fighter.ts', 'src/game/game.ts')
MARK = 'CONTINUOUS_PARRY_AI_V4_NOV06'
V3 = 'CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06'


def one(s: str, before: str, after: str, label: str, count: int = 1) -> str:
    n = s.count(before)
    if n != count:
        raise ValueError(f'{label}: expected {count} occurrence(s) of {before[:110]!r}, found {n}')
    return s.replace(before, after)


def span(s: str, start: str, end: str, label: str) -> tuple[int, int]:
    if s.count(start) != 1:
        raise ValueError(f'{label}: function start missing or repeated')
    a = s.index(start)
    b = s.find(end, a + len(start))
    if b == -1:
        raise ValueError(f'{label}: function end missing')
    return a, b


def patch_fighter(s: str) -> str:
    n = 'fighter.ts'
    s = one(s,
        '  /** Normal shield takes 0.10s to rise; the first re-raise after a successful parry is 0.05s. */',
        '  /** Successful parry makes the NEXT shield raise 90% faster (0.10s to 0.01s). */', n)
    s = one(s,
        '      this.shieldRaise = this.nextShieldFast ? 0.05 : 0.10;',
        '      this.shieldRaise = this.nextShieldFast ? 0.01 : 0.10;', n)
    s = one(s,
        '''    if (this.state === S.BLOCK && this.stateT >= this.shieldRaise) {
      if (this.stateT - this.shieldRaise <= this.parryWindow && !a.no_parry && !festivalUnparryable) {''',
        '''    // Extended combos can be parried to soften their following strikes, even
    // if the move was once flagged no_parry. Blood Festival's dedicated immunity
    // remains intact; unrelated single-hit no_parry moves stay unparryable.
    const parryableContinuous = attacker instanceof Fighter && attacker.isContinuousComboActive();
    if (this.state === S.BLOCK && this.stateT >= this.shieldRaise) {
      if (this.stateT - this.shieldRaise <= this.parryWindow &&
          (!a.no_parry || parryableContinuous) && !festivalUnparryable) {''', n)
    return s


def patch_game(s: str) -> str:
    n = 'game.ts'
    s = one(s,
        '''    strikes: () => this.strikeMarks,
    now: () => this.time,''',
        '''    strikes: () => this.strikeMarks,
    // Give the CPU real upcoming per-hit timestamps (not just a single combo telegraph).
    // The animation is still authoritative: no hit/parry outcomes are fabricated.
    comboHits: (attacker: Fighter) => this.timers
      .filter(t => t.owner === attacker && t.serial === attacker.swingSerial && t.t > this.time)
      .map(t => t.t).sort((a, b) => a - b),
    now: () => this.time,''', n)
    s = one(s,
        '        this.hitStop(0.35, 0.3);\n        break;\n      case "counter": {',
        '''        // Keep the classic dramatic PARRY slow motion, slightly stronger for
        // continuing combos. Stun never replaces the +0.20s combo continuation.
        this.hitStop(attacker instanceof Fighter && attacker.isContinuousComboActive() ? 0.46 : 0.35,
          attacker instanceof Fighter && attacker.isContinuousComboActive() ? 0.17 : 0.30);
        break;
      case "counter": {''', n)
    return s


def patch_ai(s: str) -> str:
    n = 'ai.ts'
    s = one(s,
        '''export interface Threats {
  projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number }[];
  strikes(): { target: any; land: number; id: number }[];
  now(): number;
}''',
        '''export interface Threats {
  projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number }[];
  strikes(): { target: any; land: number; id: number }[];
  /** Authoritative scheduled hit timestamps for an active continuous combo. */
  comboHits(attacker: Fighter): number[];
  now(): number;
}''', n)
    s = one(s, '  private comboThreatSerial = -1;',
        '''  private comboThreatSerial = -1;
  // CONTINUOUS_PARRY_AI_V4_NOV06: a planned parry attempt is tied to a real combo beat.
  private comboParrySerial = -1;
  private comboParryTarget = -1;
  private comboParryExamined = -1;
  private comboParryReleased = false;''', n)
    s = one(s,
        '''    if (this.blockWait >= 0) { this.blockWait -= dt; if (this.blockWait < 0) this.blockHold = this.blockDur; }''',
        '''    // A parry requires a *new* shield raise. Simply holding through the whole
    // combo results in blocks because the parry window expires after the first hit.
    if (this.retimeComboParry(f, o)) return;
    if (this.blockWait >= 0) { this.blockWait -= dt; if (this.blockWait < 0) this.blockHold = this.blockDur; }''', n)
    s = one(s,
        '''      if (festival || o.atk?.no_parry) {''',
        '''      if (festival || (o.atk?.no_parry && !o.isContinuousComboActive())) {''', n)
    s = one(s,
        '''      // Shield needs real raise time; after a parry, the next raise is twice as fast.
      const raise = f.nextShieldFast ? 0.05 : 0.10;''',
        '''      // Shield must finish rising before contact; successful parry makes the next 90% faster.
      const raise = f.nextShieldFast ? 0.01 : 0.10;''', n)
    a,b=span(s, '  /** CPUs no longer assume that a parry or clash ends a multi-hit special. */', '  private dodge(f: Fighter) {', n)
    s=s[:a]+'''  /** A continuous combo does not stop at the first successful parry or block. */
  private defendLongCombo(f: Fighter, o: Fighter) {
    if (!o.isContinuousComboActive()) { this.comboThreatSerial = -1; return; }
    if (this.comboThreatSerial === o.swingSerial) return;
    this.comboThreatSerial = o.swingSerial;
    const a = o.atk!;
    const distance = f.root.position.distanceTo(o.root.position);
    if (distance > Math.max(3.1, a.reach + 0.75) || f.state !== S.IDLE) return;
    // Fall back to a conventional block if parrying is unavailable or the CPU
    // is not skilled enough to risk timed deflections. Do not lock guard forever.
    const festival = o.kit === "sickle" && o.bloodFestivalT > 0;
    if ((festival || this.p.parry === 0) && this.blockWait < 0 && this.blockHold <= 0)
      this.schedule(0, Math.min(1.8, Math.max(0.3, a.wind + a.active + a.recover)));
  }

  /** Re-raise the shield just before *each real scheduled combo hit*.
   * Normal raise 100ms; the single-use parry reward shortens that to 10ms.
   * This is a true input-timing choice: Fighter.receiveHit still determines
   * whether contact parries, blocks, misses, or breaks guard. */
  private retimeComboParry(f: Fighter, o: Fighter): boolean {
    const active = o.isContinuousComboActive();
    const festival = o.kit === "sickle" && o.bloodFestivalT > 0;
    if (!active || festival || this.p.parry <= 0 || f.isDown()) {
      this.comboParrySerial = -1;
      this.comboParryTarget = -1;
      this.comboParryExamined = -1;
      this.comboParryReleased = false;
      return false;
    }
    const a = o.atk!;
    if (f.root.position.distanceTo(o.root.position) > Math.max(3.1, a.reach + 0.75)) return false;
    if (f.state !== S.IDLE && f.state !== S.BLOCK) return false;
    if (o.swingSerial !== this.comboParrySerial) {
      this.comboParrySerial = o.swingSerial;
      this.comboParryTarget = -1;
      this.comboParryExamined = -1;
      this.comboParryReleased = false;
    }
    const now = this.threats.now();
    if (this.comboParryTarget >= 0 && now > this.comboParryTarget + 0.04) {
      this.comboParryTarget = -1;
      this.comboParryReleased = false;
    }
    const raise = f.nextShieldFast ? 0.01 : 0.10;
    if (this.comboParryTarget < 0) {
      // Give Hard/Master a meaningful chance on *every new hit beat*.
      // Easy still blocks; Normal tries occasionally without perfect reaction.
      const chance = Math.min(0.88, 0.20 + this.p.parry * 2.2);
      for (const beat of this.threats.comboHits(o)) {
        if (beat > now + 0.9) break;
        if (beat <= this.comboParryExamined + 0.035) continue;
        if (beat < now + raise + 0.075) continue;
        this.comboParryExamined = beat;
        if (Math.random() < chance) {
          this.comboParryTarget = beat;
          this.comboParryReleased = false;
          break;
        }
      }
    }
    if (this.comboParryTarget < 0) return false;
    const eta = this.comboParryTarget - now;
    const desired = raise + 0.033; // shield reaches parry state just before the blade hits
    if (eta > desired + 0.073) return false;
    // Stop old block schedules. They made the shield stay raised, so late combo
    // contacts could only be blocked rather than parried.
    this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
    this.queue = []; this.hold = 0;
    if (f.state === S.BLOCK && !this.comboParryReleased) {
      // One frame with no shield input is necessary to reset the parry window.
      this.comboParryReleased = true;
      f.intent.block = false;
      return true;
    }
    if (eta <= desired + 0.020 && (f.state === S.IDLE || f.state === S.BLOCK)) {
      f.intent.block = true;
      // Mark the new shield raise as started; otherwise on the next frame the
      // AI would mistake its own newly-raised shield for an old held block and
      // release again, losing the parry window before the strike arrives.
      this.comboParryReleased = true;
      return true;
    }
    f.intent.block = false;
    return true;
  }

'''+s[b:]
    s = one(s,
        '''    if (f.state !== S.IDLE || this.queue.length || this.hold > 0 || this.blockHold > 0) return;''',
        '''    if (f.state !== S.IDLE || this.queue.length || this.hold > 0 || this.blockHold > 0 ||
        this.comboParryTarget > this.threats.now()) return;''', n)
    return s


def main() -> int:
    if not (ROOT / 'package.json').exists() or any(not (ROOT / name).exists() for name in FILES):
        print('ERROR: Put this script in your web folder beside package.json and src/game/', file=sys.stderr)
        return 1
    current = {rel: (ROOT / rel).read_text(encoding='utf-8') for rel in FILES}
    if all(MARK in text for text in current.values()):
        print('Already installed (V4). No changes.'); return 0
    if any(MARK in text for text in current.values()):
        print('ERROR: A partial V4 install was detected. No files changed.',file=sys.stderr); return 1
    if any(V3 not in text for text in current.values()):
        print('ERROR: Install the Combat V3 installer before V4. No files changed.',file=sys.stderr); return 1
    try:
        patched = {'src/game/ai.ts': patch_ai(current['src/game/ai.ts']),
                   'src/game/fighter.ts': patch_fighter(current['src/game/fighter.ts']),
                   'src/game/game.ts': patch_game(current['src/game/game.ts'])}
        patched = {rel: '// '+MARK+'\n'+text for rel,text in patched.items()}
    except Exception as ex:
        print('ERROR preflight:',str(ex),'\nNo files changed.',file=sys.stderr)
        return 1
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for rel in FILES:
        dest = ROOT / rel
        backup = dest.with_name(dest.name + f'.before_parry_ai_v4_{stamp}.bak')
        shutil.copy2(dest,backup)
        temp = dest.with_name(dest.name+'.parryv4tmp')
        temp.write_text(patched[rel],encoding='utf-8')
        temp.replace(dest)
        print(f'PATCH {rel} — backup {backup.name}')
    print('DONE: CPU timed re-parries; continuous combos parryable without stagger; +0.20s/-10% after parry; dramatic hit-stop; next shield raise 0.01s (90% faster).')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
