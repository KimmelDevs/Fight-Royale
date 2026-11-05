#!/usr/bin/env python3
"""Kaizen V10: mobile X hook with X-recast pull, plus cinematic Serpent Bind V slams.

V10 preserves existing guard V8, Zarek, smaller blade, and the rest of the roster.
Accepts V7/V8 or V9 sources. For V7/V8, automatically preflights and applies
V9's X hook changes in memory before the V10 changes. No partial file writes.
"""
from pathlib import Path
from datetime import datetime
import shutil
import importlib.util

ROOT = Path(__file__).resolve().parent
F = ROOT / 'src/game/fighter.ts'
G = ROOT / 'src/game/game.ts'
K = ROOT / 'src/game/kits.ts'
A = ROOT / 'src/game/ai.ts'
U = ROOT / 'src/ui/GameView.tsx'
FILES = {'fighter':F,'game':G,'kits':K,'ai':A,'ui':U}
MARK = 'KAIZEN_SERPENT_SLAM_V10'
V9 = 'KAIZEN_PREDATOR_HOOK_V9'

def once(text, old, new, name):
    n = text.count(old)
    if n != 1: raise RuntimeError(f'Preflight in {name}: expected anchor once, got {n}. No files changed. Share current game.ts and fighter.ts for a targeted fix.')
    return text.replace(old, new, 1)

def between(text, start, end, new, name):
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError(f'Preflight in {name}: cannot locate stable function boundaries. No files changed.')
    a = text.index(start); b=text.index(end,a+len(start))
    if b <= a: raise RuntimeError(f'Preflight in {name}: function markers reversed.')
    return text[:a] + new + text[b:]

def patch_fighter(src):
    # Animate target position and body rotation from a single host-driven sequence timer.
    src=once(src,
        '  chainResolveDirection: "forward" | "backward" | "" = "";',
        '''  chainResolveDirection: "forward" | "backward" | "" = "";
  // KAIZEN_SERPENT_SLAM_V10: authoritative animation begins at the actual victim position.
  chainBindFinishDuration = 0;
  chainBindStartPos = new THREE.Vector3();''', 'fighter.ts bind properties')
    src=once(src,
        '''          this.chainBindFinishT = hook ? 0.40 : direction === "forward" ? 0.85 : 0.48;
          this.chainBindT = this.chainBindFinishT;''',
        '''          // Serpent Bind: a full reel-in, lift, three-impact throw sequence.
          // X hook is still a short single yank, with free movement while bound.
          this.chainBindFinishT = hook ? 0.40 : 1.85;
          this.chainBindFinishDuration = this.chainBindFinishT;
          this.chainBindStartPos.copy(this.chainBindTarget.root.position);
          this.chainBindT = this.chainBindFinishT;''', 'fighter.ts move selection')

    src=once(src,
'''    // Serpent Bind (V) keeps its original decision and animation locks.
    if (this.chainBindT > 0 || boundOwner) {
      const launchingVictim = !!boundOwner &&
        boundOwner.chainBindFinishT > 0 &&
        boundOwner.chainBindKind === "v" &&
        boundOwner.chainResolveDirection === "forward";
      this.vx = 0;
      if (!launchingVictim) this.velY = 0;
      this.knock = 0; this.dashT = 0;
      this.airChaseMoveT = 0; this.model.walk = 0; this.trail.emitting = false;
      this.model.chainPose = this.kit === "chainblade" ? "cbv_s" : "idle";
      this.model.chainBindTargetWorld = this.chainBindTarget?.chest() ?? null;
      this.poseName = this.kit === "chainblade" ? "cbv_s" : "hit";
      this.poseSpeed = 13;
      this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
      if (launchingVictim) {
        if (this.stage) this.verticalPlat(dt);
        else this.vertical(dt);
      }
      this.trail.update(dt);
      return;
    }
''',
'''    // KAIZEN_SERPENT_SLAM_V10: Keep the chain locked for the ENTIRE animation,
    // drive the victim through alternating slams, and freeze all regular controls.
    if (this.chainBindT > 0 || boundOwner) {
      this.vx = 0; this.velY = 0; this.knock = 0; this.dashT = 0;
      this.airChaseMoveT = 0; this.model.walk = 0; this.trail.emitting = false;
      this.intent.attack = false; this.intent.skill = ""; this.intent.jump = false;
      this.model.chainBindTargetWorld = this.chainBindTarget?.chest() ?? null;
      if (boundOwner && boundOwner.chainBindKind === "v" && boundOwner.chainBindFinishT > 0) {
        this.animateSerpentBound(boundOwner, dt);
      } else if (this.chainBindTarget && this.chainBindKind === "v" && this.chainBindFinishT > 0) {
        const t = this.chainBindFinishDuration - this.chainBindFinishT;
        this.poseName = t < 0.26 ? "cbh_s" : t < 0.59 ? "cbv_s" :
          t < 0.95 ? "cbx1_s" : t < 1.27 ? "cbx2_s" : "cbx3_s";
        this.model.chainPose = this.poseName;
        this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, 34);
      } else {
        this.poseName = this.kit === "chainblade" ? "cbv_s" : "hit";
        this.model.chainPose = this.poseName;
        this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, 16);
      }
      this.trail.update(dt);
      return;
    }
''', 'fighter.ts V bind animation branch')

    # Append method before existing bind direction function.
    src=once(src,
'''  private chainRelativeDirection(): "forward" | "backward" | "left" | "right" | "neutral" {''',
'''  /** KAIZEN_SERPENT_SLAM_V10: animated grappling, no instant teleports. */
  private animateSerpentBound(owner: Fighter, dt: number) {
    const t = Math.max(0, owner.chainBindFinishDuration - owner.chainBindFinishT);
    const forward = owner.stage ? new THREE.Vector3(owner.facing, 0, 0) :
      new THREE.Vector3(Math.sin(owner.root.rotation.y), 0, Math.cos(owner.root.rotation.y));
    // Side view: use the combat line instead of shoving fighters into invisible depth.
    const side = owner.stage ? forward.clone() : new THREE.Vector3(forward.z, 0, -forward.x);
    const origin = owner.root.position;
    const back = owner.chainResolveDirection === "backward";
    // Each pose: [time, forward offset, sideways offset, vertical lift, body tilt].
    const frames: number[][] = back ? [
      [0.23, 1.05, 0, 0.18, 0],
      [0.47, 0.20, 0, 1.65, 0.55],
      [0.72, -0.90, 0.50, 0.04, 0.88],
      [0.90, -0.20, 0.0, 1.10, -0.50],
      [1.15, -1.05, -0.50, 0.04, -0.90],
      [1.34, -0.10, 0, 1.50, 0.30],
      [1.65, -1.25, 0, 0.05, -0.80],
      [1.85, -1.35, 0, 0.05, 0]
    ] : [
      [0.23, 1.08, 0, 0.18, 0],
      [0.46, 0.90, 0, 1.72, -0.45],
      [0.71, 0.78, -0.90, 0.05, -0.95],
      [0.88, 0.80, -0.15, 1.16, 0.48],
      [1.17, 0.88, 0.90, 0.05, 0.95],
      [1.36, 0.90, 0, 1.62, -0.40],
      [1.65, 1.03, 0, 0.05, 0.75],
      [1.85, 1.10, 0, 0.05, 0]
    ];
    const from = [0, 0, 0, 0, 0];
    let prev = from, next = frames[0], prevT = 0;
    if (t > frames[0][0]) {
      for (let i = 0; i < frames.length; i++) {
        if (t <= frames[i][0] || i === frames.length - 1) {
          next = frames[i];
          prev = i === 0 ? from : frames[i - 1];
          prevT = i === 0 ? 0 : frames[i - 1][0];
          break;
        }
      }
    }
    const u0 = THREE.MathUtils.clamp((t - prevT) / Math.max(0.001, next[0] - prevT), 0, 1);
    const u = u0 * u0 * (3 - 2 * u0); // eased acceleration/recoil
    const value = (i: number) => THREE.MathUtils.lerp(prev[i], next[i], u);
    // First segment reels the victim from exactly where the bind caught them.
    const p = origin.clone().addScaledVector(forward, value(1)).addScaledVector(side, value(2));
    p.y += value(3);
    if (t < frames[0][0]) p.lerpVectors(owner.chainBindStartPos, p, u);
    if (this.stage) {
      p.x = THREE.MathUtils.clamp(p.x, this.stage.blast.l + 1, this.stage.blast.r - 1);
      p.z = owner.root.position.z;
    } else {
      const radial = Math.hypot(p.x, p.z);
      if (radial > this.arenaRadius) { p.x *= this.arenaRadius / radial; p.z *= this.arenaRadius / radial; }
    }
    this.root.position.copy(p);
    this.root.rotation.z = value(4); // visible flips as the chain whips the body around
    this.onGround = false;
    this.poseName = t < 0.45 ? "hit" : t < 1.35 ? "stagger" : "hit";
    this.model.blend(this.poses[this.poseName] ?? this.poses.hit ?? this.poses.idle, dt, 28);
  }

  private chainRelativeDirection(): "forward" | "backward" | "left" | "right" | "neutral" {''', 'fighter.ts animated binding method')
    src=once(src,
'''    this.chainBindFinishT = 0;
    this.chainResolveDirection = "";
    victim.chainBoundBy = this;''',
'''    this.chainBindFinishT = 0;
    this.chainBindFinishDuration = 0;
    this.chainBindStartPos.copy(victim.root.position);
    this.chainResolveDirection = "";
    victim.chainBoundBy = this;''', 'fighter.ts begin bind reset')
    src=once(src,
'''    if (victim && victim.chainBoundBy === this) victim.chainBoundBy = null;''',
'''    if (victim && victim.chainBoundBy === this) {
      victim.chainBoundBy = null;
      victim.root.rotation.z = 0; // restore upright posture after the cinematic
    }''', 'fighter.ts release visual reset')
    src=once(src,
'''    this.chainBindFinishT = 0;
    this.chainResolveDirection = "";
    // KAIZEN_BIND_FOLLOWUP_V7''',
'''    this.chainBindFinishT = 0;
    this.chainBindFinishDuration = 0;
    this.chainResolveDirection = "";
    // KAIZEN_BIND_FOLLOWUP_V7''', 'fighter.ts finish reset')
    return src

def patch_game(src):
    start='  /** KAIZEN_BIND_ZAREK_COUNTER_V4: only a chosen forward/backward key resolves the bind. */\n'
    end='  /** Serpent Bind is a real four-second immobilization, not an immediate animation. */\n'
    replacement='''  /** KAIZEN_SERPENT_SLAM_V10: actual multi-impact chained grab, host-authoritative. */
  private resolveChainBind(f: Fighter, dir: "forward" | "backward", kind: "x" | "v") {
    const d = f.chainBindTarget;
    if (!d || d.isDown() || f.isDown()) return;
    const facing = f.stage ? new THREE.Vector3(f.facing, 0, 0) :
      new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    if (kind === "x") {
      // Predator Hook stays separate: Kaizen can walk during bind, X again pulls.
      this.fxp("slashes", d.chest(), "#ff637a");
      this.fxp("sparks", d.chest(), "#ff92a2", 18, 4);
      this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.8, 0)),
        "CHAIN PULL", "#ffb2bb", 0.85);
      return;
    }
    const round = this.round;
    const victim = d;
    const active = () => round === this.round && !f.isDown() && !victim.isDown() &&
      f.chainBindKind === "v" && f.chainBindTarget === victim && victim.chainBoundBy === f;
    this.fxp("ring", victim.chest(), "#ff687f", 0.72, 0.16, 0.7);
    this.fxp("slashes", victim.chest(), "#ff7185");
    this.fxp("num", victim.chest().add(new THREE.Vector3(0, 0.7, 0)),
      dir === "forward" ? "SERPENT LIFT" : "SERPENT OVERTHROW", "#ffb5c3", 0.9);
    const impacts = dir === "forward" ? [0.71, 1.17, 1.65] : [0.72, 1.15, 1.65];
    impacts.forEach((delay, i) => this.later(delay, () => {
      if (!active()) return;
      const finisher = i === impacts.length - 1;
      const strike = { ...f.attacks.v, dmg: [24, 32, 80][i], guard: [7, 10, 24][i],
        knock: finisher ? 2.5 : 0, stun: finisher ? 0.45 : 0.14,
        heavy: finisher, no_parry: true } as Attack;
      const pos = victim.chest();
      const direction = dir === "backward" ? facing.clone().negate() : facing;
      const result = this.applyHit(f, victim, strike, f.atkPower, pos, direction, false);
      if (result === "hit" || result === "crit" || result === "ko") {
        this.fxp("ring", victim.root.position.clone().add(new THREE.Vector3(0, 0.07, 0)),
          finisher ? "#ff8ca2" : "#ff5671", finisher ? 1.7 : 1.05, 0.20, 0.82);
        this.fxp("slashes", pos, finisher ? "#ffced8" : "#ff6b85");
        this.fxp("sparks", pos, "#ffc3cb", finisher ? 35 : 19, finisher ? 8 : 5);
        this.add_trauma(finisher ? 0.45 : 0.18);
        if (finisher) this.fxp("num", pos.clone().add(new THREE.Vector3(0, 0.65, 0)),
          "SERPENT FINISH", "#fff0f2", 0.9);
      }
      // The victim remains attached to the chain until the cinematic ends;
      // collision and ordinary physics never interrupt the grappling trajectory.
      if (!victim.isDown()) {
        victim.vx = 0; victim.velY = 0; victim.knock = 0;
      }
    }));
  }

'''
    return between(src,start,end,replacement,'game.ts V cinematic method')

def patch_kits(src):
    return once(src,
'''desc: "Wrap the enemy in chains. Both fighters stand still; release movement then choose FORWARD to launch and slam or BACKWARD to throw behind. Unbinds after 4 seconds."''',
'''desc: "Bind an opponent with your chain for up to 4 seconds. Press Z to reel them in, lift them, and smash them side to side; X lifts and swings them over Kaizen before a heavy behind-the-back slam. Both stay locked until the finisher ends."''',
'kits.ts updated Serpent Bind description')

def main():
    for name,path in FILES.items():
        if not path.is_file():
            raise RuntimeError(f'Missing {path.relative_to(ROOT)}. Put this script next to package.json in web/.')
    original = {name:path.read_text('utf-8') for name,path in FILES.items()}
    v10_flags=[MARK in original[x] for x in ('fighter','game')] + ["reel them in, lift them, and smash them side to side" in original['kits']]
    if all(v10_flags):
        print('Kaizen V10 is already installed. No changes made.'); return
    if any(v10_flags):
        raise RuntimeError('Partial V10 installation detected; no files changed. Upload current source files.')
    v9_flags=[V9 in original[x] for x in ('fighter','game','ai','ui')] + ["Kaizen may move, but other attacks and skills are locked" in original['kits']]
    output=dict(original)
    if any(v9_flags) and not all(v9_flags):
        raise RuntimeError('Partial V9 installation detected. No files changed; upload current files.')
    if not all(v9_flags):
        file=ROOT/'install_kaizen_hook_recast_v9.py'
        if not file.is_file(): raise RuntimeError('Missing install_kaizen_hook_recast_v9.py. Extract BOTH Python scripts into web/. No files changed.')
        spec=importlib.util.spec_from_file_location('kaizen_hook_v9',file)
        module=importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        if 'KAIZEN_BIND_FOLLOWUP_V7' not in original['fighter']:
            raise RuntimeError('V7 bind state not present. No files changed; upload your current files.')
        output={name:module.PATCHES[name](text) for name,text in output.items()}
        print('PRECHECK: will also apply the missing V9 X-hook recast behavior')
    output['fighter']=patch_fighter(output['fighter'])
    output['game']=patch_game(output['game'])
    output['kits']=patch_kits(output['kits'])
    # Recheck files have not changed during preflight.
    if any(path.read_text('utf-8') != original[name] for name,path in FILES.items()):
        raise RuntimeError('Files changed while preparing the patch. No changes made.')
    changed=[(name,path) for name,path in FILES.items() if output[name] != original[name]]
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    for name,path in changed:
        backup=path.with_name(path.name+f'.before-kaizen-v10-{stamp}.bak')
        shutil.copy2(path,backup)
        path.write_text(output[name], encoding='utf-8')
        print('PATCH', path.relative_to(ROOT))
    print('DONE: X moves freely while holding, X recast pulls; V bind animates reel + three slams.')
    print('Test with: npx tsc --noEmit  and  npm run dev')

if __name__=='__main__': main()
