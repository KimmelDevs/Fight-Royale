#!/usr/bin/env python3
"""Kaizen Predator's Hook V9: X to bind, move freely, X again to pull.

Requirements: Kaizen/Zarek exact-source V4, V6, V7. V8 defense patch supported.
Does not touch Serpent Bind (V), Zarek, guard regeneration, or spinning defense.
Preflights every source edit in memory BEFORE writing any file; creates backups.
"""
from pathlib import Path
from datetime import datetime
import shutil
import re

ROOT = Path(__file__).resolve().parent
FILES = {
    'fighter': ROOT/'src/game/fighter.ts',
    'game': ROOT/'src/game/game.ts',
    'kits': ROOT/'src/game/kits.ts',
    'ai': ROOT/'src/game/ai.ts',
    'ui': ROOT/'src/ui/GameView.tsx',
}
MARKER = 'KAIZEN_PREDATOR_HOOK_V9'

def once(s,old,new,desc):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'Preflight failed: {desc}: expected one anchor, found {n}. No files changed. Upload the current game, fighter, and AI files for a targeted patch.')
    return s.replace(old,new,1)

def between(s,left,right,insert,desc):
    nleft=s.count(left); nright=s.count(right)
    if nleft!=1 or nright!=1: raise RuntimeError(f'Preflight failed: {desc} markers ({nleft},{nright}). No files changed.')
    a=s.index(left); b=s.index(right,a)
    if b<=a: raise RuntimeError(f'Preflight failed: {desc} incorrect marker order. No files changed.')
    return s[:a]+insert+s[b:]

def fighter(s):
    # Replace only the chain-bind processing loop and its early return: V remains its prior Z/X selection.
    prefix = '    if (this.chainBindTarget && this.chainBindT > 0) {\n'
    suffix = '    this.model.chainBindTargetWorld = null;\n    this.readAttack(dt);'
    s=between(s,prefix,suffix,'''    // KAIZEN_PREDATOR_HOOK_V9: X bind allows Kaizen to walk, but locks other attacks/skills.
    // X recast pulls the victim toward Kaizen; Serpent Bind (V) keeps Z/X throws.
    if (this.chainBindTarget && this.chainBindT > 0) {
      const hook = this.chainBindKind === "x";
      if (this.chainBindFinishT > 0) {
        this.intent.skill = "";
        this.chainBindFinishT = Math.max(0, this.chainBindFinishT - dt);
        this.chainBindT = this.chainBindFinishT;
        if (this.chainBindFinishT === 0) this.releaseChainBind();
      } else {
        this.chainBindT = Math.max(0, this.chainBindT - dt);
        const choice = this.intent.skill;
        if (!choice) this.chainChoiceArmed = true;
        else if (this.chainChoiceArmed && (hook ? choice === "x" : choice === "z" || choice === "x")) {
          const direction = hook || choice === "x" ? "backward" : "forward";
          const kind = this.chainBindKind as "x" | "v";
          this.chainChoiceArmed = false;
          this.chainResolveDirection = direction;
          this.chainBindFinishT = hook ? 0.40 : direction === "forward" ? 0.85 : 0.48;
          this.chainBindT = this.chainBindFinishT;
          this.intent.skill = ""; // recast is consumed, NEVER cast another ordinary X
          this.onChainBindResolve(this, direction, kind);
        }
        if (this.chainBindT === 0) this.releaseChainBind();
      }
    }
    const hookOwner = this.chainBindT > 0 && this.chainBindTarget !== null && this.chainBindKind === "x";
    const boundOwner = this.chainBoundBy && this.chainBoundBy.chainBindT > 0 ? this.chainBoundBy : null;
    if (hookOwner) {
      // Kaizen walks normally while the target is tethered, but can't cast, attack, dodge,
      // jump or parry for free. The model continues to draw a chain to the victim.
      this.intent.skill = ""; this.intent.attack = false;
      this.intent.block = false; this.intent.jump = false;
      this.vx = 0; this.knock = 0; this.dashT = 0;
      if (this.state !== S.IDLE) this.setState(S.IDLE);
      if (this.stage) { this.movePlat(dt); this.verticalPlat(dt); }
      else { this.move(dt); this.vertical(dt); }
      this.poseName = "cbh_s";
      this.model.chainPose = "cbh_s";
      this.model.chainBindTargetWorld = this.chainBindTarget!.chest();
      this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, 13);
      this.trail.update(dt);
      return;
    }
    // The bound opponent stays still until the recast. During the 0.4s pull, the
    // host smoothly draws them toward Kaizen (never moves Kaizen automatically).
    if (boundOwner && boundOwner.chainBindKind === "x") {
      this.vx = 0; this.velY = 0; this.knock = 0; this.dashT = 0;
      this.airChaseMoveT = 0;
      if (boundOwner.chainBindFinishT > 0) {
        const toward = boundOwner.root.position.clone().sub(this.root.position).setY(0);
        const dist = toward.length();
        const amount = Math.min(Math.max(0, dist - 1.25), 17 * dt);
        if (amount > 0.001) {
          this.root.position.addScaledVector(toward.multiplyScalar(1 / dist), amount);
          if (this.stage) {
            this.root.position.x = THREE.MathUtils.clamp(this.root.position.x,
              this.stage.blast.l + 1, this.stage.blast.r - 1);
          } else {
            const radial = Math.hypot(this.root.position.x, this.root.position.z);
            if (radial > this.arenaRadius) {
              this.root.position.x *= this.arenaRadius / radial;
              this.root.position.z *= this.arenaRadius / radial;
            }
          }
        }
      }
      this.model.walk = 0; this.trail.emitting = false;
      this.poseName = "hit";
      this.model.blend(this.poses.hit ?? this.poses.idle, dt, 13);
      this.trail.update(dt);
      return;
    }
    // Serpent Bind (V) keeps its original decision and animation locks.
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
''', 'V7 binding tick')
    # Since the moment X connects is within an attack sequence, finish it to allow regular
    # locomotion while bound. Starting the V bind is unchanged.
    s=once(s,
'''    this.model.chainBindTargetWorld = victim.chest();
  }

  releaseChainBind()''',
'''    this.model.chainBindTargetWorld = victim.chest();
    if (kind === "x" && this.state === S.ATTACK) {
      this.finishAttack();
      this.setState(S.IDLE);
    }
  }

  releaseChainBind()''', 'X bind start state')
    # Keep model weapon aimed on remote clients / normal animation; no special snap needed.
    return s

def game(s):
    start='    if (kind === "x") {\n'
    end='    } else if (dir === "forward") {\n'
    new='''    if (kind === "x") {
      // KAIZEN_PREDATOR_HOOK_V9: X recast starts a smooth pull (handled in the
      // restrained fighter's tick). Do not instantly teleport the target.
      this.fxp("slashes", d.chest(), "#ff637a");
      this.fxp("sparks", d.chest(), "#ff92a2", 18, 4);
      this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.8, 0)),
        "CHAIN PULL", "#ffb2bb", 0.85);
'''
    s=between(s,start,end,new,'X recast effect')
    # Don't cancel X lock in HUD; show locked Z/C, X becomes a recast.
    old='''        if (me.kit === "chainblade" && me.chainBindT > 0 && (k === "z" || k === "x"))
          return { key: k, id: k === "z" ? "forward" : "backward", name: k === "z" ? "Forward" : "Backward", cd: 0, max: 1 };'''
    new='''        // KAIZEN_PREDATOR_HOOK_V9: only X can resolve Predator's Hook. All
        // other skills are locked until pull or timeout; V still uses Z/X.
        if (me.kit === "chainblade" && me.chainBindT > 0 && me.chainBindKind === "x") {
          if (k === "x") return { key: k, id: "backward", name: "PULL (X)", cd: 0, max: 1 };
          return { key: k, id: a.id, name: a.name + " (Locked)", cd: me.chainBindT, max: 4 };
        }
        if (me.kit === "chainblade" && me.chainBindT > 0 && (k === "z" || k === "x"))
          return { key: k, id: k === "z" ? "forward" : "backward", name: k === "z" ? "Forward" : "Backward", cd: 0, max: 1 };'''
    s=once(s,old,new,'skill HUD display')
    s=once(s,'clashMomentum: f.clashMomentum, chainBindT: f.chainBindT }); // KAIZEN_BIND_ZX_V6',
'''clashMomentum: f.clashMomentum, chainBindT: f.chainBindT,
      chainBindKind: f.chainBindKind }); // KAIZEN_PREDATOR_HOOK_V9''','HUD bound kind')
    # Make chain anchor obvious along the cast: FX arc along the outbound segment.
    old='''        f.beginChainBind(d, 'x');
        this.fxp("ring", d.chest(), "#ff607d", 0.75, 0.25, 0.7);'''
    new='''        f.beginChainBind(d, 'x');
        // The long tether becomes visible on contact; wraps follow the victim.
        this.fxp("ring", d.chest(), "#ff607d", 0.75, 0.25, 0.7);
        this.fxp("slashes", d.chest(), "#ff7188");'''
    s=once(s,old,new,'X hit feedback')
    return s

def kits(s):
    old='''x: a({ name: "Predator's Hook", desc: "Chain-lock an enemy and freeze both fighters. Release movement, then press FORWARD to rush to them or BACKWARD to pull them closer. Releases after 4 seconds.", cd: 10, wind: 0.22, active: 0.13, recover: 0.45, dmg: 75, guard: 24, reach: 3.4, stun: 0.28, style: "chain_predator_hook"'''
    new='''x: a({ name: "Predator's Hook", desc: "Throw a long chain to bind one enemy in place for up to 4 seconds. Kaizen may move, but other attacks and skills are locked. Press X again to pull the victim toward you. Blocking or a clash prevents the bind.", cd: 10, wind: 0.22, active: 0.13, recover: 0.45, dmg: 75, guard: 24, reach: 4.8, stun: 0.28, style: "chain_predator_hook"'''
    return once(s,old,new,'Predator Hook reach and description')

def ai(s):
    old='''  private seen = new Set<number>();
'''
    s=once(s,old,'''  private seen = new Set<number>();
  // KAIZEN_PREDATOR_HOOK_V9: use the second X press instead of waiting for WASD.
  private chainDecisionT = 0;
''','AI decision state')
    old='''    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    if (f.stage) { if (this.platform(f, o, dt)) return; }
'''
    new='''    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    // During X binding, decide when to yank. AI can step nearer while the enemy is held.
    // During V, choose Z/X as before. Neither fighter casts ordinary skills in this state.
    if (f.chainBindTarget && f.chainBindT > 0) {
      this.chainDecisionT += dt;
      const target = f.chainBindTarget;
      if (f.chainBindKind === "x" && f.chainBindFinishT <= 0) {
        const move = target.root.position.clone().sub(f.root.position).setY(0);
        if (move.length() > 2.3) {
          move.normalize();
          f.intent.move.copy(f.stage ? new THREE.Vector3(Math.sign(move.x), 0, 0) : move);
        }
      }
      if (f.chainBindFinishT <= 0 && f.chainChoiceArmed && this.chainDecisionT >= 0.7) {
        f.intent.skill = f.chainBindKind === "x" ? "x" : Math.random() < 0.5 ? "z" : "x";
      }
      return;
    }
    this.chainDecisionT = 0;
    if (f.chainBoundBy && f.chainBoundBy.chainBindT > 0) return;
    if (f.stage) { if (this.platform(f, o, dt)) return; }
'''
    return once(s,old,new,'AI bind branch')

def ui(s):
    old='''                  <Icon src={hud.kit === "chainblade" && (hud.me?.chainBindT ?? 0) > 0 &&
                    (s.key === "z" || s.key === "x")
                      ? `/icons/skills/kaizen-${s.key === "z" ? "forward" : "backward"}.webp`
                      : skillIcon(hud.kit, hud.element, s.id)} alt={s.name} size={60} /> {/* KAIZEN_BIND_ZX_V6 */}'''
    new='''                  <Icon src={hud.kit === "chainblade" && (hud.me?.chainBindT ?? 0) > 0 &&
                    (hud.me?.chainBindKind === "x" ? s.key === "x" : (s.key === "z" || s.key === "x"))
                      ? `/icons/skills/kaizen-${s.key === "z" ? "forward" : "backward"}.webp`
                      : skillIcon(hud.kit, hud.element, s.id)} alt={s.name} size={60} /> {/* KAIZEN_PREDATOR_HOOK_V9 */}'''
    return once(s,old,new,'bind icons')

PATCHES={'fighter':fighter,'game':game,'kits':kits,'ai':ai,'ui':ui}

def main():
    for name,path in FILES.items():
        if not path.is_file(): raise RuntimeError(f'Missing {path.relative_to(ROOT)}. Put this script inside web/ alongside package.json.')
    original={name:p.read_text('utf-8') for name,p in FILES.items()}
    if all(MARKER in t for t in original.values()):
        print('V9 is already installed. No changes made.'); return
    if any(MARKER in t for t in original.values()):
        raise RuntimeError('Partial V9 installation detected. No changes made; share current project files.')
    if 'KAIZEN_BIND_FOLLOWUP_V7' not in original['fighter']:
        raise RuntimeError('Kaizen V7 bind follow-up is required. No changes made.')
    # All transformations and anchor checks complete before touching a single file.
    output={name:PATCHES[name](text) for name,text in original.items()}
    timestamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    for name,path in FILES.items():
        backup=path.with_name(path.name+f'.before-kaizen-hook-v9-{timestamp}.bak')
        shutil.copy2(path,backup)
        path.write_text(output[name],encoding='utf-8')
        print('PATCH',path.relative_to(ROOT),'(backup:',backup.name+')')
    print('DONE: X binds enemy while Kaizen can move; X recast pulls target; all other skills locked.')
    print('Run: npx tsc --noEmit; npm run dev')

if __name__=='__main__': main()
