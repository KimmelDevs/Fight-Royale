#!/usr/bin/env python3
"""Kaizen Chainblade V3: directional Serpent Bind / Predator Hook, full new kit.
Run beside package.json in the web project, after Kaizen V1/V2.
Fails safely if anchors no longer match. Patches first in memory; then backs up and writes.
"""
from pathlib import Path
from datetime import datetime
import sys
ROOT = Path.cwd()
PATHS = ['src/game/kits.ts','src/game/fighter.ts','src/game/game.ts','src/game/input.ts','src/game/model.ts']
data = {}
for f in PATHS:
    p=ROOT/f
    if not p.exists(): raise RuntimeError(f'Missing {p}; run from web/ beside package.json')
    data[f]=p.read_text(encoding='utf-8')
if 'KAIZEN_DIRECTIONAL_V3' in data['src/game/game.ts']:
    print('Kaizen directional V3 already installed; no changes made.')
    sys.exit(0)

def replace(f, old, new, n=1):
    t=data[f]; count=t.count(old)
    if count != n: raise RuntimeError(f'Cannot safely patch {f}: anchor found {count} times (expected {n}): {old[:110]!r}')
    data[f]=t.replace(old,new,n)

k='src/game/kits.ts'
start=data[k].index('function chainblade(): Record<string, Attack> {')
end=data[k].index('\nfunction greatsword()',start)
new_kit='''// KAIZEN_DIRECTIONAL_V3 — five chainblade hits and four entirely new specials.
function chainblade(): Record<string, Attack> {
  return {
    l1: a({ name: "Dancing Fang 1", wind: 0.16, active: 0.10, recover: 0.25, dmg: 69, guard: 20, reach: 2.12, lunge: 2.0, knock: 1.2, stun: 0.24, style: "chain_basic", pose_w: "cb1_w", pose_s: "cb1_s", next: "l2" }),
    l2: a({ name: "Dancing Fang 2", wind: 0.17, active: 0.10, recover: 0.26, dmg: 73, guard: 21, reach: 2.2, lunge: 2.0, knock: 1.2, stun: 0.25, style: "chain_basic", pose_w: "cb2_w", pose_s: "cb2_s", next: "l3" }),
    l3: a({ name: "Dancing Fang 3", wind: 0.20, active: 0.11, recover: 0.29, dmg: 77, guard: 23, reach: 2.4, lunge: 1.8, knock: 1.5, stun: 0.27, style: "chain_basic", pose_w: "cb3_w", pose_s: "cb3_s", next: "l4" }),
    l4: a({ name: "Dancing Fang 4", wind: 0.25, active: 0.12, recover: 0.31, dmg: 90, guard: 28, reach: 2.8, lunge: 1.6, knock: 1.8, stun: 0.32, style: "chain_basic", pose_w: "cb4_w", pose_s: "cb4_s", next: "l5" }),
    l5: a({ name: "Dancing Fang Return", wind: 0.24, active: 0.24, recover: 0.55, dmg: 112, guard: 36, reach: 3.0, lunge: 1.2, knock: 3.8, stun: 0.40, heavy: true, style: "chain_return", pose_w: "cb5_w", pose_s: "cb5_s" }),
    heavy: a({ name: "Chainbreaker", wind: 0.35, active: 0.17, recover: 0.67, dmg: 185, guard: 51, reach: 3.0, lunge: 1.2, knock: 5.6, stun: 0.56, heavy: true, style: "chain_heavy", pose_w: "cbh_w", pose_s: "cbh_s" }),
    z: a({ name: "Razor Cyclone", desc: "Spin the chained blade around Kaizen. Hold the skill to extend the spin and its range (max 1.6 seconds).", cd: 8, wind: 0.20, active: 1.65, recover: 0.38, dmg: 28, guard: 11, reach: 2.2, stun: 0.15, style: "chain_razor_cyclone", pose_w: "cbz_w", pose_s: "cbz_s" }),
    x: a({ name: "Predator's Hook", desc: "Hook a target, then recast with FORWARD to rush toward them or BACKWARD to pull them to you. Defaults to pull.", cd: 10, wind: 0.22, active: 0.13, recover: 0.45, dmg: 75, guard: 24, reach: 3.4, stun: 0.28, style: "chain_predator_hook", pose_w: "cbh_w", pose_s: "cbh_s" }),
    c: a({ name: "Thousand Cuts: Death Spiral", desc: "A contracting circle of chain slashes ending in an overhead strike. Escape before the circle closes.", cd: 22, wind: 0.38, active: 1.85, recover: 0.68, dmg: 42, guard: 12, radius: 4.2, style: "chain_death_spiral", pose_w: "cbc_w", pose_s: "cbc_s" }),
  };
}
'''
data[k]=data[k][:start]+new_kit+data[k][end:]
old='''    case "chainblade":
      return a({ name: "Razor Recall", desc: "Snap the chainblade outward and whip it back. Long reach but a punishable recovery.", cd: 10,
        wind: 0.27, active: 0.13, recover: 0.55, dmg: 135, guard: 33, reach: 3.2, knock: 3.0, stun: 0.37,
        style: "chain_recall", pose_w: "cbv_w", pose_s: "cbv_s" });'''
new='''    case "chainblade":
      return a({ name: "Serpent Bind", desc: "Chain grab. Forward: launch and slam. Backward: flip behind. Left/right: throw sideways. Direction follows facing, not fixed keys.", cd: 13,
        wind: 0.29, active: 0.12, recover: 0.62, dmg: 85, guard: 29, reach: 2.9, knock: 1.0, stun: 0.55,
        style: "chain_serpent_bind", pose_w: "cbv_w", pose_s: "cbv_s" });'''
replace(k,old,new)
replace(k,'''  cb4_s: P(''', '''  cb5_w: P([0.15, -0.82, -0.02], [0, 0.48, 0], [-1.4, 0.80, 0.04], [0.25, 0.04, 0.62], [-0.34, -0.62, 0.45], [0.11, 0, 0], [-0.49, 0, 0.07], [0.42, 0, -0.07], -0.15),
  cb5_s: P([0.35, 1.02, 0.06], [-0.11, -0.69, 0], [-1.78, -1.04, -0.07], [0.05, 0, -0.65], [-0.5, 0.42, 0.5], [0.16, 0, 0], [-0.49, 0, 0.11], [0.46, 0, -0.06], -0.16),
  cb4_s: P(''')

inp='src/game/input.ts'
replace(inp,'''skill: string; mx: number; mz: number; dx?: number; dz?: number''','''skill: string; mx: number; mz: number; skillHeld?: string; dx?: number; dz?: number''')
replace(inp,'''return { attack: this.held("attack"), block: this.held("block"), jump: this.held("jump"), skill: this.skills.shift() ?? "", mx, mz, dx, dz };''','''return { attack: this.held("attack"), block: this.held("block"), jump: this.held("jump"), skill: this.skills.shift() ?? "", mx, mz, skillHeld: this.held("skill1") ? "z" : "", dx, dz };''')

f='src/game/fighter.ts'
replace(f,'''skill: string; move: THREE.Vector3; dash: THREE.Vector3''','''skill: string; skillHeld?: string; skillMove?: THREE.Vector3; move: THREE.Vector3; dash: THREE.Vector3''')
replace(f,'''  chainFuryT = 0; // KAIZEN_CHAINBLADE_V1: 5s Unbound Drive, host-synced.''','''  chainFuryT = 0; // legacy field retained for existing snapshots/weapon code.
  // KAIZEN_DIRECTIONAL_V3: direction is relative to facing at skill-press, never hard-coded WASD.
  chainSkillDir: "forward" | "backward" | "left" | "right" | "neutral" = "neutral";
  chainHookTarget: Entity | null = null;
  chainHookT = 0;
  onChainHookRecast: (f: Fighter, approach: boolean) => void = () => {};''')
replace(f,'''it.attack = false; it.block = false; it.jump = false; it.skill = ""; it.move.set(0, 0, 0); it.dash.set(0, 0, 0);''','''it.attack = false; it.block = false; it.jump = false; it.skill = ""; it.skillHeld = "";
    it.skillMove?.set(0, 0, 0); it.move.set(0, 0, 0); it.dash.set(0, 0, 0);''')
replace(f,'''    this.chainFuryT = Math.max(this.chainFuryT - dt, 0);''','''    this.chainFuryT = Math.max(this.chainFuryT - dt, 0);
    this.chainHookT = Math.max(0, this.chainHookT - dt);
    if (this.chainHookT === 0) this.chainHookTarget = null;''')
replace(f,'''  private readSkill() {
    const k = this.intent.skill;
    if (!k) return;''','''  private chainRelativeDirection(): "forward" | "backward" | "left" | "right" | "neutral" {
    const m = this.intent.skillMove ?? this.intent.move;
    if (m.lengthSq() < 0.04) return "neutral";
    if (this.stage) {
      // Side-view: horizontal direction is forward/back relative to current facing.
      if (Math.abs(m.x) > 0.25) return m.x * this.facing > 0 ? "forward" : "backward";
      // Camera up/down is used for jumping/dropping in platform mode; not a side throw.
      return "neutral";
    }
    const forward = new THREE.Vector3(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
    const front = m.dot(forward), right = m.x * forward.z - m.z * forward.x;
    if (Math.abs(front) >= Math.abs(right)) return front >= 0 ? "forward" : "backward";
    return right >= 0 ? "right" : "left";
  }

  private readSkill() {
    const k = this.intent.skill;
    if (!k) return;
    // Recast the already-connected hook. Movement direction is sampled on THIS recast.
    if (this.kit === "chainblade" && k === "x" && this.chainHookT > 0 && this.chainHookTarget && !this.chainHookTarget.isDown() &&
        ![S.KO, S.WIN, S.STAGGER, S.HITSTUN].includes(this.state)) {
      const dir = this.chainRelativeDirection();
      this.onChainHookRecast(this, dir === "forward"); // backward or neutral = pull enemy
      this.chainHookT = 0;
      this.chainHookTarget = null;
      return;
    }''')
replace(f,'''    this.holding = false;
    // The keg's cooldown''','''    this.holding = false;
    if (this.kit === "chainblade") this.chainSkillDir = this.chainRelativeDirection();
    // The keg's cooldown''')

# Set required input vector from local and remote clients.
g='src/game/game.ts'
replace(g,'''  skills: string[] = [];''','''  skills: Array<{ key: string; mx: number; mz: number }> = [];''')
replace(g,'''    f.intent.skill = this.skills.shift() ?? "";''','''    const nextSkill = this.skills.shift();
    f.intent.skill = nextSkill?.key ?? "";
    if (nextSkill) {
      if (!f.intent.skillMove) f.intent.skillMove = new THREE.Vector3();
      f.intent.skillMove.set(nextSkill.mx, 0, nextSkill.mz);
    }''')
replace(g,'''  if (r.skill) f.intent.skill = r.skill;
  f.intent.move.set(r.mx, 0, r.mz);''','''  if (r.skill) {
    f.intent.skill = r.skill;
    if (!f.intent.skillMove) f.intent.skillMove = new THREE.Vector3();
    f.intent.skillMove.set(r.mx, 0, r.mz);
  }
  f.intent.skillHeld = r.skillHeld ?? "";
  f.intent.move.set(r.mx, 0, r.mz);''')
replace(g,'''if (msg.i.skill) b.skills.push(msg.i.skill);''','''if (msg.i.skill) b.skills.push({ key: msg.i.skill, mx: msg.i.mx, mz: msg.i.mz });''')
# Assign callbacks in the fighter spawn block using a stable existing callback.
replace(g,'''    f.onSwing = (x) => this.onSwing(x);''','''    f.onSwing = (x) => this.onSwing(x);
    f.onChainHookRecast = (x, toward) => this.chainHookRecast(x, toward);''')
# Replace chainblade conditional in onSwing with new logic.
start=data[g].index('    if (f.kit === "chainblade") {\n', data[g].index('  private onSwing(f: Fighter)'))
end=data[g].index('    switch (a.type) {',start)
data[g]=data[g][:start]+'''    // KAIZEN_DIRECTIONAL_V3: every move has its own hit logic and chain choreography.
    if (f.kit === "chainblade") {
      if (a.style === "chain_razor_cyclone") { this.chainRazorCyclone(f, a); return; }
      if (a.style === "chain_death_spiral") { this.chainDeathSpiral(f, a); return; }
      if (a.style === "chain_serpent_bind") { this.chainSerpentBind(f, a); return; }
      if (a.style === "chain_predator_hook") {
        this.fxp("slashes", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), "#ff667c");
        this.melee(f, a); return;
      }
      if (a.style === "chain_return") {
        this.melee(f, a); // blade throw
        const round = this.round, serial = f.swingSerial;
        this.later(0.18, () => {
          if (round !== this.round || f.isDown() || f.swingSerial !== serial || f.state !== S.ATTACK) return;
          this.fxp("slashes", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), "#ff8d9e");
          this.melee(f, { ...a, dmg: 45, guard: 16, knock: 2.6, stun: 0.22, heavy: false }); // returning blade bonus
        });
        return;
      }
      if (a.type === "melee") {
        const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
        this.fxp("flash", tip, "#ff6575", a.heavy ? 0.42 : 0.22, 0.12, 0.7);
        this.fxp("sparks", tip, "#ffb4b4", a.heavy ? 20 : 10, 4);
      }
    }
'''+data[g][end:]
# Actual hook sets target on a true hit, old chain_hook remains for older definitions.
replace(g,'''      if (f.kit === "chainblade" && a.style === "chain_hook" &&
''','''      if (f.kit === "chainblade" && a.style === "chain_predator_hook" &&
          ["hit", "crit"].includes(result) && d instanceof Fighter) {
        f.chainHookTarget = d;
        f.chainHookT = 2.0;
        this.fxp("ring", d.chest(), "#ff607d", 0.75, 0.25, 0.7);
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.7, 0)), "HOOKED", "#ff8999", 0.8);
      }
      if (f.kit === "chainblade" && a.style === "chain_hook" &&
''')
# Insert helper functions before existing carousel function.
marker='''  /** KAIZEN_CHAINBLADE_V1: three independent, interruptible chain swipes. */'''
helpers='''  /** KAIZEN_DIRECTIONAL_V3: a caught target, then a FORWARD chase or BACKWARD pull. */
  private chainHookRecast(f: Fighter, approach: boolean) {
    const d = f.chainHookTarget;
    if (!d || d.isDown() || f.isDown()) return;
    const toEnemy = d.root.position.clone().sub(f.root.position).setY(0);
    if (toEnemy.lengthSq() < 0.01) return;
    const forward = toEnemy.normalize();
    if (approach) {
      const destination = d.root.position.clone().addScaledVector(forward, -1.35);
      f.teleport(destination); // safe bounds and authoritative position
      this.fxp("slashes", d.chest(), "#ff6578");
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "CHAIN CHASE", "#ffb6bb", 0.8);
    } else {
      const destination = f.root.position.clone().addScaledVector(forward, 1.5);
      if (d instanceof Fighter) {
        if (d.stage) destination.x = THREE.MathUtils.clamp(destination.x, d.stage.blast.l + 1, d.stage.blast.r - 1);
        else { const flat = Math.hypot(destination.x, destination.z); if (flat > d.arenaRadius) destination.multiplyScalar(d.arenaRadius / flat); }
        d.root.position.x = destination.x; d.root.position.z = destination.z;
        d.model.recoil = 0.5;
      }
      this.fxp("slashes", d.chest(), "#ff6578");
      this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.8, 0)), "YANK", "#ffb6bb", 0.8);
    }
  }

  /** Razor Cyclone: 4 guaranteed beats, then up to 5 extra beats while Z remains held. */
  private chainRazorCyclone(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    for (let i = 0; i < 9; i++) this.later(i * 0.18, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      if (i >= 4 && f.intent.skillHeld !== "z") return;
      const reach = 1.65 + Math.min(i, 8) * 0.10;
      const hit = { ...a, dmg: i >= 4 ? 22 : 28, guard: 8, stun: 0.10, heavy: false } as Attack;
      this.fxp("ring", f.root.position.clone().add(new THREE.Vector3(0, 1.1, 0)), "#ff5d78", reach, 0.10, 0.6);
      for (const d of this.enemiesOf(f)) {
        const diff = d.root.position.clone().sub(f.root.position).setY(0);
        if (diff.length() > reach + d.radius || Math.abs(d.root.position.y - f.root.position.y) > 1.9) continue;
        // Real opposing active attacks still create the standard weapon clash.
        if (d instanceof Fighter && this.isDuel() && d.state === S.ATTACK && d.atk?.type === "melee" && d.atkPhase === 1) {
          this.clash(f, d, f.chest()); return;
        }
        this.applyHit(f, d, hit, f.atkPower, d.chest(), diff.normalize(), false);
      }
    });
  }

  /** Death Spiral: outward opening gives enemies a dodge window before contraction. */
  private chainDeathSpiral(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial, origin = f.root.position.clone();
    const times = [0.05, 0.28, 0.51, 0.74, 0.97, 1.20, 1.43];
    for (let i = 0; i < times.length; i++) this.later(times[i], () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      const radius = Math.max(1.7, 4.2 - i * 0.40);
      this.fxp("ring", origin.clone().add(new THREE.Vector3(0, 0.8, 0)), "#fa536c", radius, 0.18, 0.9);
      this.fxp("slashes", origin.clone().add(new THREE.Vector3(Math.sin(i * 1.2) * 1.0, 1.2, Math.cos(i * 1.2))), "#ff6e83");
      f.poseOverride = ["cbx1_s", "cbx2_s", "cbx3_s"][i % 3];
      for (const d of this.enemiesOf(f)) {
        const diff = d.root.position.clone().sub(origin).setY(0);
        if (diff.length() > radius + d.radius || Math.abs(d.root.position.y - f.root.position.y) > 1.9) continue;
        this.applyHit(f, d, { ...a, dmg: 38, guard: 11, stun: 0.13, knock: 0, heavy: false }, f.atkPower, d.chest(), diff.normalize(), false);
      }
    });
    this.later(1.67, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      f.poseOverride = "cb5_s";
      this.fxp("slashes", origin.clone().add(new THREE.Vector3(0, 1.9, 0)), "#ffbbc2");
      for (const d of this.enemiesOf(f)) {
        const diff = d.root.position.clone().sub(origin).setY(0);
        if (diff.length() > 2.0 + d.radius || Math.abs(d.root.position.y - f.root.position.y) > 2.2) continue;
        this.applyHit(f, d, { ...a, dmg: 135, guard: 37, knock: 5.3, stun: 0.55, heavy: true }, f.atkPower, d.chest(), diff.normalize(), false);
      }
      this.add_trauma(0.38);
    });
  }

  /** Serpent Bind: capture movement direction at cast, never assume W is forward. */
  private chainSerpentBind(f: Fighter, a: Attack) {
    const forward = f.stage ? new THREE.Vector3(f.facing, 0, 0) :
      new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const side = new THREE.Vector3(forward.z, 0, -forward.x);
    const dir = f.chainSkillDir, round = this.round;
    for (const d of this.enemiesOf(f)) {
      const diff = d.root.position.clone().sub(f.root.position).setY(0);
      if (diff.length() > a.reach + d.radius || diff.dot(forward) < -0.6 || Math.abs(d.root.position.y - f.root.position.y) > 1.55) continue;
      const outcome = this.applyHit(f, d, a, f.atkPower, d.chest(), diff.normalize(), false);
      if (!["hit", "crit"].includes(outcome) || !(d instanceof Fighter)) continue;
      d.model.recoil = 0.65;
      if (dir === "forward") {
        d.velY = Math.max(d.velY, 7.8); d.onGround = false;
        this.fxp("num", d.chest(), "SERPENT LAUNCH", "#ffb0bc", 0.8);
        this.later(0.43, () => {
          if (round !== this.round || f.isDown() || d.isDown()) return;
          d.velY = -13; d.onGround = false;
          this.fxp("slashes", d.chest(), "#ff748b");
        });
        this.later(0.70, () => {
          if (round !== this.round || f.isDown() || d.isDown()) return;
          this.applyHit(f, d, { ...a, dmg: 92, guard: 27, knock: 2, stun: 0.46, heavy: true }, f.atkPower, d.chest(), forward, false);
          this.fxp("ring", d.root.position.clone().add(new THREE.Vector3(0, 0.12, 0)), "#ff748b", 1.15, 0.22, 0.75);
        });
      } else if (dir === "backward") {
        d.velY = Math.max(d.velY, 4.1); d.onGround = false;
        const dest = f.root.position.clone().addScaledVector(forward, -1.5);
        d.root.position.x = dest.x;
        if (!d.stage) d.root.position.z = dest.z;
        this.fxp("num", d.chest(), "BACK THROW", "#ffb0bc", 0.8);
      } else if (dir === "left" || dir === "right") {
        const s = dir === "left" ? -1 : 1;
        const step = d.stage ? new THREE.Vector3(s * 1.6, 0, 0) : side.clone().multiplyScalar(s * 1.6);
        const dest = d.root.position.clone().add(step);
        if (d.stage) dest.x = THREE.MathUtils.clamp(dest.x, d.stage.blast.l + 1, d.stage.blast.r - 1);
        else { const flat = Math.hypot(dest.x, dest.z); if (flat > d.arenaRadius) { dest.x *= d.arenaRadius / flat; dest.z *= d.arenaRadius / flat; } }
        d.root.position.x = dest.x; if (!d.stage) d.root.position.z = dest.z;
        this.fxp("num", d.chest(), dir === "left" ? "LEFT THROW" : "RIGHT THROW", "#ffb0bc", 0.8);
      } else {
        this.fxp("num", d.chest(), "SERPENT BIND", "#ffb0bc", 0.8);
      }
      this.fxp("slashes", d.chest(), "#ff788b");
      return; // Single bound target; no multi-target teleport throws.
    }
  }

'''
replace(g,marker,helpers+marker)
# Model updated to five hit chain animations and spinning Z/C.
m='src/game/model.ts'
replace(m,'''const isOrbit = pose.startsWith("cbx");''','''const isOrbit = pose.startsWith("cbx") || pose.startsWith("cbz") || pose.startsWith("cbc");''')
replace(m,'''const isAttack = /^(cb[1-4]_[ws]|cbh_[ws]|cbz_[ws]|cbv_[ws]|cbx(?:[1-3])?_[ws])$/.test(pose);''','''const isAttack = /^(cb[1-5]_[ws]|cbh_[ws]|cbc_[ws]|cbz_[ws]|cbv_[ws]|cbx(?:[1-3])?_[ws])$/.test(pose);''')
replace(m,'''/^cb[1-4]_[ws]$/.test(pose)''','''/^cb[1-5]_[ws]$/.test(pose)''')
# Write backups only after every anchor was verified.
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
for f in PATHS:
    p=ROOT/f
    backup=p.with_name(p.name + '.kaizen-v3-backup-' + stamp)
    backup.write_text(p.read_text(encoding='utf-8'),encoding='utf-8')
    p.write_text(data[f],encoding='utf-8')
    print('PATCH',f)
print('DONE: Kaizen V3. All files backed up. Re-run is safe.')
print('Note: In 2D platform mode, side throws are limited by the stage plane; forward/backward use actual facing.')
