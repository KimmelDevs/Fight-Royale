#!/usr/bin/env python3
"""Fight Royale — cinematic special camera, Nyx boost, smarter continuous dodges, and Zarek CPU block fix.

Install into the web folder (or project root):
    python Install_FightRoyale_Cinematic_Nyx_Buff_Zarek_Guard_V2.py
Preview/check without changing files:
    python Install_FightRoyale_Cinematic_Nyx_Buff_Zarek_Guard_V2.py --check

Changes only src/game/{fighter,game,ai}.ts. No external Python modules.
The installer checks every source anchor before writing and backs up the originals.
"""
from __future__ import annotations
import argparse
import datetime
from pathlib import Path
import shutil
import sys

MARK = "FIGHT_ROYALE_NYX_CAMERA_CONTINUOUS_DODGE_20261107_V1"
FILES = ("fighter.ts", "game.ts", "ai.ts")
ZAREK_MARK = "FIGHT_ROYALE_ZAREK_CPU_SHIELD_RECOVERY_V2"

class PatchError(Exception):
    pass


def one(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}. "
                         "No files were changed. Please upload your current source if this persists.")
    return s.replace(old, new, 1)


def find_project() -> Path:
    cwd = Path.cwd().resolve()
    folders = []
    for p in (cwd, *list(cwd.parents)[:3]):
        folders.extend((p, p / 'web'))
    for p in folders:
        if all((p / 'src' / 'game' / file).is_file() for file in FILES):
            return p
    raise PatchError('Place this Python file in the Fight Royale web folder, then run it there. '
                     'Could not find src/game/fighter.ts, game.ts, ai.ts.')


def fighter(s: str) -> str:
    if MARK in s:
        return s
    s = one(s, '  perfectDodgeCounterT = 0; // one successful melee riposte, expires after 0.95s',
        '  perfectDodgeCounterT = 0; // one successful melee riposte, expires after 0.95s\n'
        '  /** NYX_SMOKE_BOOST: armed only once Smoke Step actually teleports. */\n'
        '  nyxShadowBoostT = 0;', 'Nyx buff timer field')

    s = one(s, '    this.perfectDodgeCounterT = Math.max(0, this.perfectDodgeCounterT - dt);',
        '    this.perfectDodgeCounterT = Math.max(0, this.perfectDodgeCounterT - dt);\n'
        '    this.nyxShadowBoostT = Math.max(0, this.nyxShadowBoostT - dt);', 'Nyx buff clock')

    # Reuse the fully calculated damage multiplier, not raw attack tables: this
    # naturally works for multi-hit skills, Aster's passives, and range effects.
    s = one(s, '    this.atkId = id;\n    this.atk = this.attacks[id];', '''    // NYX_SMOKE_BOOST: next offensive move only. An ordinary l1..l4, air light,
    // charged heavy or basic parry-riposte gets x2. A damaging skill gets x1.2.
    // Smoke Step itself and non-damaging skills cannot consume the reward.
    if (this.kit === "assassin" && this.nyxShadowBoostT > 0) {
      const chosen = this.attacks[id];
      const isBasic = /^(l[1-9]\\d*|air_l[1-9]\\d*|heavy|pc)$/.test(id);
      const isSkill = /^(z|x|c|v)(?:_air)?$/.test(id) && !!chosen && chosen.dmg > 0 &&
        chosen.type !== "buff" && chosen.type !== "blink";
      if (chosen && (isBasic || isSkill)) {
        this.atkPower *= isBasic ? 2.0 : 1.2;
        this.nyxShadowBoostT = 0;
        this.model.flash(isBasic ? "#b05eff" : "#b1aaff", 0.20);
      }
    }
    this.atkId = id;
    this.atk = this.attacks[id];''', 'Nyx boost consumption on real attack start')

    # On KO/revival clear reward; avoid granting boost to new rounds.
    s = one(s, '  revive(frac: number) {', '  revive(frac: number) {\n    this.nyxShadowBoostT = 0;', 'Nyx revive reset')
    s = one(s, '  ko() {', '  ko() {\n    this.nyxShadowBoostT = 0;', 'Nyx KO reset')
    return '// ' + MARK + '\n' + s


def game(s: str) -> str:
    if MARK in s:
        return s
    s = one(s, '  private impactCameraPunch = 0;', '''  private impactCameraPunch = 0;
  // Skill cinematics are camera-only (no time scaling, teleport or collision edits).
  private specialCameraSeen = new Map<number, number>();
  private specialCameraT = 0;
  private specialCameraCaster: Fighter | null = null;
'''.rstrip(), 'cinematic camera state')

    # Buff is armed when Smoke Step resolves, not on cast-button input: an interrupted
    # teleport does not grant it. Only the assassin's own Z, not another blink.
    s = one(s, '    f.teleport(to);\n    this.fxp("smoke", f.root.position.clone(), f.look.glow);', '''    f.teleport(to);
    this.fxp("smoke", f.root.position.clone(), f.look.glow);
    if (f.kit === "assassin" && f.atkId === "z" && a.name === "Smoke Step") {
      f.nyxShadowBoostT = 10.0;
      this.fxp("ring", f.chest(), "#af7cff", 0.84, 0.30, 0.72);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.70, 0)),
        "SHADOW EMPOWERED", "#d3a3ff", 0.90);
    }''', 'Nyx Smoke Step boost arming')

    # Special focus starts when an attack is actually cast, even for a quick blink.
    # Camera zoom is a gentle FOV pulse using the existing camera; aspect/spectator
    # modes continue to share the same framing and controls.
    s = one(s, '    const cam = this.camera;\n    let goal: THREE.Vector3, look: THREE.Vector3;', '''    const cam = this.camera;
    // Watch the authoritative attack id + swing serial so casts pulse once each.
    // Nyx Smoke Step (Z) and Zarek's X get a short, soft anime camera punch.
    for (const actor of this.fighters) {
      if (actor.state !== S.ATTACK ||
          !((actor.kit === "assassin" && actor.atkId === "z") ||
            (actor.kit === "glaive" && actor.atkId === "x"))) continue;
      if (this.specialCameraSeen.get(actor.id) === actor.swingSerial) continue;
      this.specialCameraSeen.set(actor.id, actor.swingSerial);
      this.specialCameraCaster = actor;
      this.specialCameraT = 0.46;
    }
    this.specialCameraT = Math.max(0, this.specialCameraT - dt);
    const cinematicFov = this.specialCameraT > 0 ? 46.8 : 50;
    const oldFov = cam.fov;
    cam.fov = THREE.MathUtils.damp(cam.fov, cinematicFov,
      this.specialCameraT > 0 ? 16 : 9, dt);
    if (Math.abs(cam.fov - oldFov) > 0.0001) cam.updateProjectionMatrix();
    let goal: THREE.Vector3, look: THREE.Vector3;''', 'camera activation/FOV pulse')

    # Small shift in looking point to emphasize casting fighter; never enough to
    # push an opponent completely off frame in a duel.
    s = one(s, '    cam.position.lerp(goal, k);\n    cam.lookAt(look);', '''    cam.position.lerp(goal, k);
    if (this.specialCameraT > 0 && this.specialCameraCaster &&
        !this.specialCameraCaster.isDown()) {
      const casterFocus = this.specialCameraCaster.chest();
      const focusWeight = this.plat ? 0.10 : this.cfg.mode === "duel" ? 0.14 : 0.20;
      look.lerp(casterFocus, focusWeight * Math.min(1, this.specialCameraT * 5));
    }
    cam.lookAt(look);''', 'camera focus ease')
    return '// ' + MARK + '\n' + s


def ai(s: str) -> str:
    if MARK in s:
        return s
    s = one(s, '  private ignitionChoices = new Map<number, boolean>();', '''  private ignitionChoices = new Map<number, boolean>();
  // Continuous attacks: react to a real incoming beat, not to every animation frame.
  private lastUndodgeableCombo = -1;
  private continuousDodgeReaction = 0;
  private continuousDodgeDone = false;
'''.rstrip(), 'continuous dodge AI fields')

    method = '''
  /** Last-resort dodge for genuinely unsafe continuous attacks. Never grants i-frames
   * directly: issues the ordinary dash input with normal cooldown and state checks.
   * Clashes and affordable blocks are preferred; attacking never gets cancelled unless
   * a real dodge can be executed. Skill pressure resumes on the next frame.
   */
  private dodgeUnsafeContinuous(f: Fighter, o: Fighter, dt: number): boolean {
    const atk = o.atk;
    if (o.state !== S.ATTACK || !atk || !o.isContinuousComboActive()) {
      this.lastUndodgeableCombo = -1;
      this.continuousDodgeDone = false;
      return false;
    }
    // Only react to threatening distance and the next legitimate hit beat.
    const distance = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    const reach = atk.type === "strike" ? Math.max(atk.radius, 1.6) :
      Math.max(1.5, atk.reach + Math.min(Math.max(atk.lunge, 0) * 0.12, 0.65));
    if (distance > reach + 0.65) return false;
    if (this.lastUndodgeableCombo !== o.swingSerial) {
      this.lastUndodgeableCombo = o.swingSerial;
      this.continuousDodgeReaction = rand(this.p.react[0], this.p.react[1]);
      this.continuousDodgeDone = false;
    }
    this.continuousDodgeReaction = Math.max(0, this.continuousDodgeReaction - dt);
    if (this.continuousDodgeDone || this.continuousDodgeReaction > 0) return false;
    if (f.isDown() || !f.onGround || f.dashing() ||
        ![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(f.state)) return false;

    // Upcoming combo time is authoritative when the arena schedules repeat hits.
    const upcoming = this.threats.comboHits(o)
      .filter(t => t >= this.threats.now() - 0.025).sort((x, y) => x - y);
    const eta = upcoming.length ? upcoming[0] - this.threats.now() :
      Math.max(0, atk.wind - o.stateT);
    if (eta > 0.48) return false; // too early; avoid panic dodges

    const shieldReady = f.state === S.BLOCK && f.stateT >= f.shieldRaise;
    const shieldCanRaise = [S.IDLE, S.BLOCK].includes(f.state) &&
      eta >= (f.nextShieldFast ? 0.01 : 0.10) + 0.035;
    const guardNeed = Math.max(12, atk.guard * (atk.heavy ? 1.25 : 1.05));
    const canAffordBlock = f.guard > guardNeed && (shieldReady || shieldCanRaise);
    const myLight = f.attacks.l1;
    const canClash = myLight?.type === "melee" &&
      ((f.state === S.ATTACK && f.atk?.type === "melee" && f.atkPhase <= 1) ||
       (f.state === S.IDLE && myLight.wind + 0.05 <= eta &&
        distance <= myLight.reach + 0.20));
    // Skip if existing good defense is still viable. Only exceptional threats
    // should override the normal aggressive personality / ready-skill logic.
    if (canAffordBlock || canClash) return false;

    const canDash = f.dashCd <= 0 && !f.knockedDown() &&
      (f.kit !== "hammer" || f.state !== S.ATTACK);
    if (!canDash) return false; // no fake dodges or permanent defensive lockdown
    // Choose a reachable safe direction inside the real arena boundaries.
    const away = f.root.position.clone().sub(o.root.position).setY(0);
    if (away.lengthSq() < 0.0001) away.set(f.id % 2 ? 1 : -1, 0, 0);
    away.normalize();
    const candidates = f.stage ? [
      new THREE.Vector3(Math.sign(away.x) || f.facing, 0, 0),
      new THREE.Vector3(-(Math.sign(away.x) || f.facing), 0, 0),
    ] : [
      away.clone(),
      new THREE.Vector3(-away.z, 0, away.x),
      new THREE.Vector3(away.z, 0, -away.x),
    ];
    const origin = f.root.position.clone().setY(0);
    let best: THREE.Vector3 | null = null;
    let score = -Infinity;
    for (const dir of candidates) {
      const dest = origin.clone().addScaledVector(dir, 2.5);
      if (f.stage) {
        const main = f.stage.plats[0];
        if (!main || dest.x < main.x0 + 0.7 || dest.x > main.x1 - 0.7) continue;
      } else if (dest.length() > f.arenaRadius - f.radius - 0.22) continue;
      const separation = dest.distanceTo(o.root.position.clone().setY(0));
      const value = separation + (dir.dot(away) > 0.6 ? 0.15 : 0);
      if (value > score) { score = value; best = dir; }
    }
    if (!best) return false;
    f.intent.dash.copy(best);
    f.intent.move.copy(best);
    f.intent.block = false;
    f.intent.attack = false;
    f.intent.skill = "";
    // Commit only to one true dash per enemy swing. No repeated queue cancellation.
    this.continuousDodgeDone = true;
    this.blockHold = 0;
    this.blockWait = -1;
    return true;
  }

'''

    s = one(s, '  constructor(private threats: Threats, level: number) {',
        method + '  constructor(private threats: Threats, level: number) {',
        'dodge helper insertion')
    s = one(s, '    if (!o || o.isDown()) return;',
        '    if (!o || o.isDown()) return;\n'
        '    if (this.dodgeUnsafeContinuous(f, o, dt)) return;',
        'continuous threat at start of AI think')
    return '// ' + MARK + '\n' + s



def zarek_shield_repair(s: str) -> str:
    """Fixed active defense exclusively for Zarek (glaive); doesn't replace his offense."""
    if ZAREK_MARK in s:
        return s
    fields = '''  // A shield decision tied to a REAL swing, not a permanent turtle mode.
  private zarekGuardSwing = -1;
  private zarekGuardReact = 0;
  private zarekGuardHold = 0;
  private zarekGuardWants = false;
  private zarekGuardPredictCd = 1.3;
  private zarekGuardSeenShots = new Set<number>();
'''
    s = one(s, '  private ignitionChoices = new Map<number, boolean>();',
        '  private ignitionChoices = new Map<number, boolean>();\n' + fields,
        'Zarek shield AI fields')

    method = '''
  /** Zarek sometimes missed all blocks because pressure/skill logic overrode a
   * queued shield raise. Commit to the normal block input for one LEGITIMATE threat.
   * No free parry, unlimited shield or attack/skill lock; he remains aggressive.
   */
  private zarekShieldResponse(f: Fighter, o: Fighter, dt: number): boolean {
    if (f.kit !== "glaive") return false;
    this.zarekGuardPredictCd = Math.max(0, this.zarekGuardPredictCd - dt);
    if (f.isDown() || !f.onGround ||
        (f.state !== S.IDLE && f.state !== S.BLOCK)) {
      this.zarekGuardHold = 0;
      return false;
    }
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));

    const commitGuard = (duration: number): boolean => {
      this.zarekGuardHold = Math.max(this.zarekGuardHold, duration);
      f.intent.block = true;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.sprint = false;
      f.intent.move.set(0, 0, 0);
      // Ordinary shield raise is still 0.10s (or the earned 90% faster raise).
      // Do not let pressure/counter queues issue a basic during this guard.
      this.blockWait = -1;
      this.blockHold = 0;
      this.blockDur = 0;
      this.comboParryTarget = -1;
      this.queue = [];
      this.hold = 0;
      return true;
    };

    if (this.zarekGuardHold > 0) {
      this.zarekGuardHold = Math.max(0, this.zarekGuardHold - dt);
      if (f.guard > Math.max(5, f.maxGuard * 0.09)) {
        return commitGuard(0);
      }
      this.zarekGuardHold = 0;
    }
    if (f.guard <= Math.max(f.maxGuard * 0.28, 18)) return false;
    // Projectiles deserve real shielding too: Zarek's old pressure plan often
    // started a glaive combo instead of raising guard for the incoming shot.
    // This reads existing real projectiles; it does not predict nonexistent ones.
    for (const shot of this.threats.projectiles()) {
      if (shot.target !== f || this.zarekGuardSeenShots.has(shot.id)) continue;
      const approaching = shot.pos.clone().sub(f.chest()).dot(shot.vel) < 0;
      const eta = f.chest().distanceTo(shot.pos) /
        Math.max(1.0, shot.vel.length());
      if (!approaching || eta < (f.nextShieldFast ? 0.05 : 0.14) ||
          eta > 0.64 || f.guard <= f.maxGuard * 0.37) continue;
      this.zarekGuardSeenShots.add(shot.id);
      if (this.zarekGuardSeenShots.size > 150) this.zarekGuardSeenShots.clear();
      if (Math.random() < 0.22 + this.p.block * 0.82)
        return commitGuard(Math.min(0.80, eta + 0.19));
    }
    const a = o.atk;
    const nearby = gap < 2.75;

    // Anticipatory guard against a plainly visible long charge, or a short
    // read during close-range neutral. This covers fast 0.1s combos that cannot
    // be reacted to AFTER the blade starts moving.
    if (this.zarekGuardPredictCd <= 0 && nearby &&
        (o.state === S.CHARGE || o.state === S.IDLE) &&
        f.guard > f.maxGuard * 0.61 &&
        Math.random() < dt * (o.state === S.CHARGE ? 3.2 : 0.68) *
          (0.65 + this.p.block)) {
      this.zarekGuardPredictCd = o.state === S.CHARGE ? 1.35 : 2.2;
      return commitGuard(o.state === S.CHARGE ? 0.42 : 0.24);
    }
    if (o.state !== S.ATTACK || !a || a.dmg <= 0 ||
        (a.type !== "melee" && a.type !== "strike")) return false;
    const range = a.type === "strike" ? Math.max(a.radius, 1.65) :
      a.reach + Math.min(Math.max(0, a.lunge) * 0.13, 0.80);
    if (gap > range + 0.48) return false;
    if (o.swingSerial !== this.zarekGuardSwing) {
      this.zarekGuardSwing = o.swingSerial;
      this.zarekGuardReact = rand(this.p.react[0], this.p.react[1]) * 0.64;
      const usefulGuard = f.guard >= Math.max(f.maxGuard * 0.32,
        a.guard * (o.isContinuousComboActive() ? 2.0 : 1.25));
      this.zarekGuardWants = usefulGuard &&
        Math.random() < Math.min(0.91, 0.46 + this.p.block * 0.64);
    }
    if (!this.zarekGuardWants) return false;
    this.zarekGuardReact = Math.max(0, this.zarekGuardReact - dt);
    if (this.zarekGuardReact > 0) return false;

    // Contact may come from a multi-hit beat; block those instead of assuming
    // another parry can be raised instantly. Shield/guard damage stays real.
    const eta = a.type === "strike" ? Math.max(0, a.wind - o.stateT + a.delay) :
      Math.max(0, a.wind - o.stateT);
    const remain = a.wind + a.active - o.stateT;
    if (remain < -0.15 && !o.isContinuousComboActive()) return false;
    const shieldReady = f.state === S.BLOCK && f.stateT >= f.shieldRaise;
    const raise = f.nextShieldFast ? 0.01 : 0.10;
    if (!shieldReady && eta + (o.isContinuousComboActive() ? 0.22 : 0.035) < raise) return false;

    this.zarekGuardWants = false;
    const holdTime = o.isContinuousComboActive()
      ? Math.min(1.25, Math.max(0.28, remain + 0.20))
      : Math.min(0.65, Math.max(0.24, remain + 0.20));
    return commitGuard(holdTime);
  }

'''
    s = one(s, '  constructor(private threats: Threats, level: number) {',
        method + '  constructor(private threats: Threats, level: number) {',
        'Zarek shield tactics method')

    # The counter AI has priority, followed by Zarek's threat-driven shield.
    # Older AI builds without Counter V2 still work.
    if '    if (this.counterThreatDefense(f, o, dt)) return;' in s:
        anchor = '    if (this.counterThreatDefense(f, o, dt)) return;'
    elif '    if (this.dodgeUnsafeContinuous(f, o, dt)) return;' in s:
        anchor = '    if (this.dodgeUnsafeContinuous(f, o, dt)) return;'
    else:
        anchor = '    if (!o || o.isDown()) return;'
    s = one(s, anchor, anchor + '\n    if (this.zarekShieldResponse(f, o, dt)) return;',
        'Zarek shield before regular offense and skills')
    return '// ' + ZAREK_MARK + '\n' + s

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='Validate changes without writing any files')
    args = ap.parse_args()
    try:
        root = find_project()
        paths = {f: root / 'src' / 'game' / f for f in FILES}
        sources = {name: path.read_text(encoding='utf-8') for name, path in paths.items()}
        old_installs = [MARK in sources[name] for name in FILES]
        if any(old_installs) and not all(old_installs):
            raise PatchError('Partial cinematic install detected. Restore backups or upload current source; no files changed.')
        if all(old_installs) and ZAREK_MARK in sources['ai.ts']:
            print('[OK] All cinematic, Nyx, dodge and Zarek guard improvements already installed.')
            return
        if not ('AI_PERSONALITY_THEATER_2_V1' in sources['ai.ts'] or
                'FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V2' in sources['ai.ts']):
            print('[NOTE] Older AI build detected; using compatibility anchors.')
        results = sources.copy() if all(old_installs) else {
            'fighter.ts': fighter(sources['fighter.ts']),
            'game.ts': game(sources['game.ts']),
            'ai.ts': ai(sources['ai.ts']),
        }
        results['ai.ts'] = zarek_shield_repair(results['ai.ts'])
        changed = [n for n in FILES if sources[n] != results[n]]
        if args.check:
            print('[CHECK] All required source anchors matched. Would update:', ', '.join(changed))
            return
        stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        folder = root / '.fight_royale_backups' / f'cinematic_nyx_zarek_{stamp}'
        folder.mkdir(parents=True, exist_ok=False)
        for name in changed:
            path = paths[name]
            shutil.copy2(path, folder / name)
        for name in changed:
            path = paths[name]
            tmp = path.with_name(path.name + '.zarek_cinematic_tmp')
            tmp.write_text(results[name], encoding='utf-8', newline='\n')
            tmp.replace(path)
        print('[DONE] Cinematic zoom, Nyx Z boost, smarter continuous dodge, and Zarek CPU block fix installed.')
        print('[FILES]', ', '.join(changed))
        print('[BACKUPS]', folder)
        print('[NEXT] npx tsc --noEmit -p . && npm run dev')
    except (PatchError, OSError) as e:
        print('[ERROR]', e)
        sys.exit(1)

if __name__ == '__main__':
    main()
