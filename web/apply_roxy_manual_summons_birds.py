#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path.cwd()
FILES = [ROOT / 'src/game/kits.ts', ROOT / 'src/game/game.ts', ROOT / 'src/game/fighter.ts']
for p in FILES:
    if not p.is_file():
        sys.exit(f'Missing {p}. Run this inside web/. No files changed.')

old = {p: p.read_text(encoding='utf-8') for p in FILES}
new = dict(old)

def replace_once(path: Path, old_text: str, new_text: str):
    src = new[path]
    count = src.count(old_text)
    if count != 1:
        raise RuntimeError(f'{path.name}: expected 1 exact match for patch block, found {count}. No files changed.')
    new[path] = src.replace(old_text, new_text, 1)

def insert_once(path: Path, anchor: str, block: str, before=False):
    src = new[path]
    count = src.count(anchor)
    if count != 1:
        raise RuntimeError(f'{path.name}: expected 1 anchor match, found {count}: {anchor[:70]!r}. No files changed.')
    new[path] = src.replace(anchor, (block + '\n' + anchor) if before else (anchor + '\n' + block), 1)

kits = ROOT / 'src/game/kits.ts'
game = ROOT / 'src/game/game.ts'
fighter = ROOT / 'src/game/fighter.ts'

if 'ROXY_SNOW_PUPPET_MASTER_V1' not in old[kits] or 'ROXY_SNOW_PUPPET_MASTER_V1' not in old[game]:
    sys.exit('Roxy frost kit not found. Install Roxy first, then run this updater. No files changed.')
if 'ROXY_MANUAL_SUMMONS_BIRD_V2_20261108' in old[game]:
    sys.exit('Roxy manual summons update already installed. No changes needed.')

old_frost_block = '''  // ROXY_SNOW_PUPPET_MASTER_V1: the snow summons are persistent arena objects, not generic circle FX.
  if (element === "frost") {
    t.heavy = a({ type: "projectile", wind: 0.22, active: 0.05, recover: 0.5, dmg: 170, guard: 47, knock: 4.5, stun: 0.48, heavy: true,
      speed: 12, size: 1.7, style: "bolt", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Snowglass Shield", desc: "Create a protective ice shield for 2 seconds in PvP (4 seconds in survival).", cd: 11,
      type: "buff", mode: "ward", duration: 4, wind: 0.12, recover: 0.28, pose_w: "mh_w", pose_s: "m3_s" });
    t.x = a({ name: "Frost Marionette", desc: "Summon one snow puppet that chases an enemy and bursts, freezing on a successful hit.", cd: 9,
      type: "snow_puppet", style: "freeze", wind: 0.26, recover: 0.42, dmg: 77, guard: 24, knock: 0.9, stun: 0.2,
      count: 1, speed: 3.8, radius: 0.95, duration: 5.5, effect: "paralyze", effect_t: 1.35,
      pose_w: "m2_w", pose_s: "m2_s" });
    t.c = a({ name: "Glacier Meteor", desc: "A large ice meteor falls onto the marked position, damaging and slowing anyone caught beneath it.", cd: 15,
      type: "strike", style: "meteor", wind: 0.36, recover: 0.65, dmg: 245, guard: 65, knock: 5.5, stun: 0.65,
      heavy: true, delay: 0.85, radius: 2.1, effect: "slow", effect_t: 2.0, effect_p: 0.65,
      pose_w: "mh_w", pose_s: "mh_s" });
    return t;
  }'''

new_frost_block = '''  // ROXY_MANUAL_SUMMONS_BIRD_V2_20261108: manual-command frost summons.
  if (element === "frost") {
    t.heavy = a({ type: "projectile", wind: 0.22, active: 0.05, recover: 0.5, dmg: 170, guard: 47, knock: 4.5, stun: 0.48, heavy: true,
      speed: 12, size: 1.7, style: "bolt", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Snowglass Shield", desc: "Create a protective ice shield for 7 seconds.", cd: 11,
      type: "buff", mode: "ward", duration: 7, wind: 0.12, recover: 0.28, pose_w: "mh_w", pose_s: "m3_s" });
    t.x = a({ name: "Frost Marionette", desc: "Summon a light-blue snow marionette. Press X again to command it to rush and freeze the enemy.", cd: 9,
      type: "snow_puppet", style: "freeze", wind: 0.26, recover: 0.42, dmg: 77, guard: 24, knock: 0.9, stun: 0.2,
      count: 1, speed: 4.2, radius: 0.95, duration: 9.5, effect: "paralyze", effect_t: 1.35,
      pose_w: "m2_w", pose_s: "m2_s" });
    t.c = a({ name: "Glacier Meteor", desc: "A large ice meteor falls onto the marked position, damaging and slowing anyone caught beneath it.", cd: 15,
      type: "strike", style: "meteor", wind: 0.36, recover: 0.65, dmg: 245, guard: 65, knock: 5.5, stun: 0.65,
      heavy: true, delay: 0.85, radius: 2.1, effect: "slow", effect_t: 2.0, effect_p: 0.65,
      pose_w: "mh_w", pose_s: "mh_s" });
    return t;
  }'''
replace_once(kits, old_frost_block, new_frost_block)

old_bonus = '''      if (element === "frost") return a({ name: "Snowfall Parade", desc: "Summon three snow puppets. Each chases an enemy and explodes in slowing frost (no freezing).", cd: 17,
        type: "snow_puppet", style: "slow", wind: 0.30, recover: 0.45, dmg: 58, guard: 16, knock: 1.2, stun: 0.1,
        count: 3, speed: 3.0, radius: 1.05, duration: 5.0, effect: "slow", effect_t: 2.8, effect_p: 0.55,
        pose_w: "mh_w", pose_s: "m3_s" });'''
new_bonus = '''      if (element === "frost") return a({ name: "Snowfall Parade", desc: "Summon three white snowbirds that wait for your command. Press V again to release one bird; each bird fires an ice shard every 3 seconds for 5 shots, then disappears.", cd: 17,
        type: "snow_puppet", style: "bird", wind: 0.30, recover: 0.45, dmg: 38, guard: 12, knock: 1.8, stun: 0.18,
        count: 3, speed: 5.1, radius: 1.0, duration: 16.0, effect: "slow", effect_t: 1.4, effect_p: 0.45,
        pose_w: "mh_w", pose_s: "m3_s" });'''
replace_once(kits, old_bonus, new_bonus)

insert_once(fighter, '  onTrigger: (f: Fighter) => void = () => {};', '  onSnowCommand: (f: Fighter, key: string) => boolean = () => false;')
insert_once(fighter, '    if (this.kit === "hammer" && this.attacks[k]?.style === "nesa_heart_slam" &&\n        (!this.nesaCArmed || this.nesaCCharges <= 0)) return;', '''    if (this.look.element === "frost" && this.attacks[k]?.type === "snow_puppet") {
      if (![S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state) && this.onSnowCommand(this, k)) return;
    }''', before=False)

old_snow_block = '''// ROXY_SNOW_PUPPET_MASTER_V1 — persistent snow summons (host-controlled, guest visuals only).
interface SnowPuppet {
  id: number; owner: Fighter | null; team: number; atk: Attack | null; power: number;
  pos: THREE.Vector3; targetId: number; life: number; age: number;
  mesh: THREE.Group; mode: "freeze" | "slow";
}

function buildSnowPuppetMesh(mode: "freeze" | "slow"): THREE.Group {
  const g = new THREE.Group();
  const snow = new THREE.MeshLambertMaterial({ color: "#edfaff" });
  const shadow = new THREE.MeshLambertMaterial({ color: "#b9d9ee" });
  const ice = new THREE.MeshLambertMaterial({ color: mode === "freeze" ? "#6ac9ff" : "#9fe1ee" });
  const ink = new THREE.MeshBasicMaterial({ color: "#1d446c" });
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.36, 14, 10), snow);
  body.position.y = 0.39;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.25, 14, 10), snow);
  head.position.y = 0.94;
  const waist = new THREE.Mesh(new THREE.TorusGeometry(0.29, 0.048, 7, 18), ice);
  waist.rotation.x = Math.PI / 2;
  waist.position.y = 0.60;
  g.add(body, head, waist);
  for (const side of [-1, 1]) {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.046, 8, 6), ink);
    eye.position.set(side * 0.10, 0.99, 0.22);
    const arm = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.46, 6), shadow);
    arm.position.set(side * 0.38, 0.65, 0);
    arm.rotation.z = side * 1.1;
    g.add(eye, arm);
  }
  const crown = new THREE.Mesh(new THREE.ConeGeometry(mode === "freeze" ? 0.23 : 0.18, 0.37, 5), ice);
  crown.position.y = 1.31;
  g.add(crown);
  const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.10, 0), ice);
  gem.position.set(0, 0.79, 0.32);
  g.add(gem);
  const aura = new THREE.Mesh(new THREE.TorusGeometry(0.43, 0.025, 5, 28), new THREE.MeshBasicMaterial({ color: "#8ddcff", transparent: true, opacity: 0.65 }));
  aura.rotation.x = Math.PI / 2;
  aura.position.y = 0.09;
  g.add(aura);
  g.scale.setScalar(mode === "freeze" ? 1.0 : 0.82);
  return g;
}
'''
new_snow_block = '''// ROXY_MANUAL_SUMMONS_BIRD_V2_20261108 — manual frost summons with handcrafted procedural meshes.
interface SnowPuppet {
  id: number; owner: Fighter | null; team: number; atk: Attack | null; power: number;
  pos: THREE.Vector3; home: THREE.Vector3; targetId: number; life: number; age: number;
  mesh: THREE.Group; mode: "freeze" | "bird"; state: "idle" | "rush" | "attack";
  shotsLeft: number; shotCd: number; slot: number;
}

function buildSnowPuppetMesh(): THREE.Group {
  const g = new THREE.Group();
  const snow = new THREE.MeshLambertMaterial({ color: "#f8fcff" });
  const ice = new THREE.MeshLambertMaterial({ color: "#a7e8ff" });
  const soft = new THREE.MeshLambertMaterial({ color: "#dff5ff" });
  const eye = new THREE.MeshBasicMaterial({ color: "#d59cff" });
  const outline = new THREE.MeshBasicMaterial({ color: "#7ab6ff", transparent: true, opacity: 0.75 });

  const body = new THREE.Mesh(new THREE.SphereGeometry(0.28, 14, 10), snow);
  body.position.y = 0.38;
  body.scale.set(1.0, 1.1, 0.9);
  const belly = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 8), soft);
  belly.position.set(0, 0.29, 0.16);
  belly.scale.set(1.0, 1.0, 0.55);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.26, 14, 10), snow);
  head.position.y = 0.92;
  head.scale.set(1.05, 0.98, 0.95);
  const earL = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 8), snow);
  const earR = earL.clone();
  earL.position.set(-0.13, 1.14, -0.02); earR.position.set(0.13, 1.14, -0.02);
  const eyeL = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 6), eye);
  const eyeR = eyeL.clone();
  eyeL.position.set(-0.08, 0.96, 0.21); eyeR.position.set(0.08, 0.96, 0.21);
  const armL = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.18, 4, 8), snow);
  const armR = armL.clone();
  armL.position.set(-0.18, 0.50, 0.07); armR.position.set(0.18, 0.50, 0.07);
  armL.rotation.z = 0.55; armR.rotation.z = -0.55;
  const legL = new THREE.Mesh(new THREE.SphereGeometry(0.10, 10, 8), soft);
  const legR = legL.clone();
  legL.position.set(-0.10, 0.04, 0.05); legR.position.set(0.10, 0.04, 0.05);
  legL.scale.set(1.2, 0.8, 1.45); legR.scale.copy(legL.scale);
  const swirl = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.022, 7, 28, Math.PI * 1.2), outline);
  swirl.position.set(0.24, 0.66, 0.1); swirl.rotation.set(0.15, 0.25, 0.9);
  const swirl2 = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.018, 7, 24, Math.PI * 1.2), outline);
  swirl2.position.set(-0.25, 0.63, -0.05); swirl2.rotation.set(-0.05, -0.35, -0.8);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.43, 0.02, 6, 24), new THREE.MeshBasicMaterial({ color: "#bdf0ff", transparent: true, opacity: 0.7 }));
  ring.rotation.x = Math.PI / 2; ring.position.y = 0.06;
  g.add(body, belly, head, earL, earR, eyeL, eyeR, armL, armR, legL, legR, swirl, swirl2, ring);
  return g;
}

function buildSnowBirdMesh(): THREE.Group {
  const g = new THREE.Group();
  const white = new THREE.MeshLambertMaterial({ color: "#ffffff" });
  const brown = new THREE.MeshLambertMaterial({ color: "#b88963" });
  const dark = new THREE.MeshLambertMaterial({ color: "#283142" });
  const ice = new THREE.MeshLambertMaterial({ color: "#dffbff" });
  const beak = new THREE.MeshLambertMaterial({ color: "#e6b65d" });
  const glow = new THREE.MeshBasicMaterial({ color: "#e9ffff", transparent: true, opacity: 0.65 });

  const body = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 10), white);
  body.scale.set(1.6, 0.95, 1.0);
  body.position.set(0, 1.02, 0);
  const neck = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.18, 4, 8), brown);
  neck.position.set(-0.22, 1.05, 0.02); neck.rotation.z = -0.75;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.11, 12, 8), white);
  head.position.set(-0.34, 1.06, 0.04);
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.07, 10, 8), brown);
  cap.position.set(-0.37, 1.10, 0.04); cap.scale.set(1.0, 0.7, 1.0);
  const beakMesh = new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.12, 6), beak);
  beakMesh.position.set(-0.48, 1.04, 0.04); beakMesh.rotation.z = Math.PI / 2;
  const wingL = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.05, 0.22), white);
  const wingR = wingL.clone();
  wingL.position.set(0.03, 1.08, 0.24); wingR.position.set(0.03, 1.08, -0.24);
  wingL.rotation.z = 0.28; wingR.rotation.z = -0.28;
  const tipL = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.035, 0.18), dark);
  const tipR = tipL.clone();
  tipL.position.set(0.22, 1.08, 0.26); tipR.position.set(0.22, 1.08, -0.26);
  tipL.rotation.z = 0.28; tipR.rotation.z = -0.28;
  const tail = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.04, 0.12), ice);
  tail.position.set(0.33, 1.0, 0); tail.rotation.z = 0.15;
  const eyeDot = new THREE.Mesh(new THREE.SphereGeometry(0.016, 6, 5), new THREE.MeshBasicMaterial({ color: "#171f2d" }));
  eyeDot.position.set(-0.38, 1.07, 0.11);
  const eyeDot2 = eyeDot.clone(); eyeDot2.position.z = -0.03;
  const halo = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.014, 5, 24), glow);
  halo.rotation.x = Math.PI / 2; halo.position.y = 0.76;
  g.add(body, neck, head, cap, beakMesh, wingL, wingR, tipL, tipR, tail, eyeDot, eyeDot2, halo);
  return g;
}
'''
replace_once(game, old_snow_block, new_snow_block)

insert_once(game, '    f.onTrigger = (x) => {', '    f.onSnowCommand = (x, key) => this.commandSnowSummon(x, key);', before=True)

old_methods = '''  // ROXY_SNOW_PUPPET_MASTER_V1: spawn, move, and resolve real snow minions. Never damage allies.
  private disposeSnowPuppet(p: SnowPuppet) {
    this.scene.remove(p.mesh);
    p.mesh.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.geometry.dispose();
      for (const mat of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) mat.dispose();
    });
  }

  private makeSnowPuppet(id: number, owner: Fighter | null, team: number, atk: Attack | null,
      power: number, pos: THREE.Vector3, targetId: number, mode: "freeze" | "slow", duration: number) {
    if (this.snowPuppets.some(p => p.id === id)) return;
    const mesh = buildSnowPuppetMesh(mode);
    mesh.position.copy(pos);
    this.scene.add(mesh);
    this.snowPuppets.push({ id, owner, team, atk, power, pos, targetId, mode, life: duration, age: 0, mesh });
  }

  private summonSnowPuppets(f: Fighter, a: Attack) {
    const target = f.opponent && !f.opponent.isDown() ? f.opponent : this.enemiesOf(f)[0];
    const forward = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const right = new THREE.Vector3(forward.z, 0, -forward.x);
    for (let i = 0; i < a.count; i++) {
      const offset = i - (a.count - 1) / 2;
      const pos = f.root.position.clone().addScaledVector(forward, 1.05).addScaledVector(right, this.plat ? 0 : offset * 1.05);
      if (!this.plat) pos.y = 0; // Ground-level even when the opponent is airborne.
      const id = this.nextId++;
      const mode: "freeze" | "slow" = a.style === "freeze" ? "freeze" : "slow";
      this.makeSnowPuppet(id, f, f.team, a, f.atkPower, pos, target?.id ?? -1, mode, a.duration);
      this.emit(["snowPuppet", id, f.id, f.team, pos.toArray(), target?.id ?? -1, mode, a.duration]);
      this.fxp("motes", pos.clone().add(new THREE.Vector3(0, 0.7, 0)), "#d6f8ff", 11);
    }
    this.snd("splash", 0.55);
  }

  private finishSnowPuppet(p: SnowPuppet, exploded: boolean) {
    if (!this.snowPuppets.includes(p)) return;
    if (exploded && this.cfg.role !== "client" && p.owner && p.atk) {
      const mid = p.pos.clone().add(new THREE.Vector3(0, 0.7, 0));
      this.fxp("explosion", mid, p.mode === "freeze" ? "#72caff" : "#a6eaff", p.atk.radius);
      this.fxp("motes", mid, "#e3f9ff", 18);
      this.fxp("ring", mid, "#b3ebff", p.atk.radius, 0.25, 0.75);
      for (const d of this.enemiesOf(p.owner)) {
        const to = d.root.position.clone().sub(p.pos);
        const height = Math.abs(to.y);
        to.y = 0;
        if (to.length() > p.atk.radius + d.radius * 0.5 || (this.plat && height > 1.6)) continue;
        if (!this.plat && d.airborne()) continue;
        const dir = to.lengthSq() > 0.0001 ? to.normalize() : new THREE.Vector3(1, 0, 0);
        // Standard receiveHit handles guarding, parrying, wards and status resistance.
        this.applyHit(p.owner, d, p.atk, p.power, d.chest(), dir, true);
      }
    }
    this.disposeSnowPuppet(p);
    this.snowPuppets = this.snowPuppets.filter(x => x !== p);
    if (this.cfg.role !== "client") this.emit(["snowPuppetEnd", p.id]);
  }

  private updateSnowPuppets(dt: number) {
    for (const p of [...this.snowPuppets]) {
      p.life -= dt;
      p.age += dt;
      if (this.cfg.role !== "client" && (!p.owner || p.owner.isDown() || this.roundOver)) {
        this.finishSnowPuppet(p, false);
        continue;
      }
      let target = this.entities.get(p.targetId);
      if (!target || target.isDown() || target.team === p.team) {
        target = p.owner ? this.enemiesOf(p.owner)[0] : undefined;
        if (target) p.targetId = target.id;
      }
      if (target) {
        const delta = target.root.position.clone().sub(p.pos);
        if (!this.plat) delta.y = 0;
        const distance = delta.length();
        const speed = p.atk?.speed ?? (p.mode === "freeze" ? 3.8 : 3.0);
        if (distance > 0.05) {
          const direction = delta.multiplyScalar(1 / distance);
          p.pos.addScaledVector(direction, Math.min(Math.max(0, distance - 0.45), speed * dt));
          p.mesh.rotation.y = Math.atan2(direction.x, direction.z);
        }
        // On contact, this puppet explodes exactly once. Other puppets are independent.
        if (this.cfg.role !== "client" && distance < 0.95) {
          this.finishSnowPuppet(p, true);
          continue;
        }
      }
      p.mesh.position.copy(p.pos).add(new THREE.Vector3(0, Math.sin(p.age * 7 + p.id) * 0.06, 0));
      if (p.life <= 0) this.finishSnowPuppet(p, this.cfg.role !== "client");
    }
  }
'''
new_methods = '''  // ROXY_MANUAL_SUMMONS_BIRD_V2_20261108: manual-command frost summons. Never damage allies.
  private disposeSnowPuppet(p: SnowPuppet) {
    this.scene.remove(p.mesh);
    p.mesh.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.geometry.dispose();
      for (const mat of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) mat.dispose();
    });
  }

  private makeSnowPuppet(id: number, owner: Fighter | null, team: number, atk: Attack | null,
      power: number, pos: THREE.Vector3, targetId: number, mode: "freeze" | "bird", duration: number,
      state: "idle" | "rush" | "attack" = "idle", shotsLeft = 0, slot = 0) {
    if (this.snowPuppets.some(p => p.id === id)) return;
    const mesh = mode === "bird" ? buildSnowBirdMesh() : buildSnowPuppetMesh();
    mesh.position.copy(pos);
    this.scene.add(mesh);
    this.snowPuppets.push({ id, owner, team, atk, power, pos, home: pos.clone(), targetId, mode, life: duration, age: 0, mesh, state, shotsLeft, shotCd: 0.6, slot });
  }

  private commandSnowSummon(f: Fighter, key: string): boolean {
    const mode: "freeze" | "bird" = key === "v" ? "bird" : "freeze";
    const owned = this.snowPuppets.filter(p => p.owner === f && p.mode === mode);
    if (!owned.length) return false;
    const idle = owned.find(p => p.state === "idle");
    if (!idle) return true;
    const target = f.opponent && !f.opponent.isDown() ? f.opponent : this.enemiesOf(f)[0] ?? null;
    idle.targetId = target?.id ?? -1;
    idle.state = mode === "bird" ? "attack" : "rush";
    idle.shotCd = 0.1;
    if (this.cfg.role !== "client") this.emit(["snowPuppetCmd", idle.id, idle.state, idle.targetId, idle.shotsLeft]);
    this.fxp("flash", idle.pos.clone().add(new THREE.Vector3(0, mode === "bird" ? 0.95 : 0.6, 0)), "#ebffff", 0.28, 0.12, 0.8);
    this.fxp("motes", idle.pos.clone().add(new THREE.Vector3(0, 0.7, 0)), "#dcfbff", mode === "bird" ? 8 : 12);
    this.snd(mode === "bird" ? "dash" : "splash", 0.5);
    return true;
  }

  private summonSnowPuppets(f: Fighter, a: Attack) {
    const mode: "freeze" | "bird" = a.style === "bird" ? "bird" : "freeze";
    const already = this.snowPuppets.some(p => p.owner === f && p.mode === mode);
    if (already) return;
    const target = f.opponent && !f.opponent.isDown() ? f.opponent : this.enemiesOf(f)[0] ?? null;
    const forward = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const right = new THREE.Vector3(forward.z, 0, -forward.x);
    if (mode === "bird") {
      for (let i = 0; i < a.count; i++) {
        const offset = i - (a.count - 1) / 2;
        const pos = f.root.position.clone().addScaledVector(forward, 0.55).addScaledVector(right, offset * 0.8).add(new THREE.Vector3(0, 1.6 + Math.abs(offset) * 0.15, 0));
        const id = this.nextId++;
        this.makeSnowPuppet(id, f, f.team, a, f.atkPower, pos, target?.id ?? -1, "bird", Math.max(16, a.duration), "idle", 5, i);
        this.emit(["snowPuppet", id, f.id, f.team, pos.toArray(), target?.id ?? -1, "bird", Math.max(16, a.duration), "idle", 5, i]);
        this.fxp("motes", pos.clone(), "#f7ffff", 10);
      }
      this.snd("wind", 0.45);
      return;
    }
    const pos = f.root.position.clone().addScaledVector(forward, 0.95);
    if (!this.plat) pos.y = 0;
    const id = this.nextId++;
    this.makeSnowPuppet(id, f, f.team, a, f.atkPower, pos, target?.id ?? -1, "freeze", a.duration, "idle", 0, 0);
    this.emit(["snowPuppet", id, f.id, f.team, pos.toArray(), target?.id ?? -1, "freeze", a.duration, "idle", 0, 0]);
    this.fxp("motes", pos.clone().add(new THREE.Vector3(0, 0.7, 0)), "#d6f8ff", 13);
    this.snd("splash", 0.55);
  }

  private fireSnowBirdShard(p: SnowPuppet, target: Entity | null) {
    if (!p.owner || !p.atk || !target) return;
    const origin = p.pos.clone().add(new THREE.Vector3(0, 0.08, 0));
    const aim = target.chest().sub(origin);
    const dir = aim.lengthSq() > 0.0001 ? aim.normalize() : new THREE.Vector3(1, 0, 0);
    const shard: Attack = { ...p.atk, type: "projectile", style: "bolt", dmg: p.atk.dmg, guard: p.atk.guard, knock: p.atk.knock,
      stun: p.atk.stun, speed: 12.5, size: 0.68, count: 1, spread: 0, pierce: false, heavy: false,
      effect: p.atk.effect || "slow", effect_t: p.atk.effect_t || 1.4, effect_p: p.atk.effect_p || 0.45 };
    this.spawnProjectile(p.owner, p.team, shard, p.power, origin, dir.multiplyScalar(shard.speed), "bolt", "frost", shard.size, "#e8ffff", false, target);
    this.fxp("flash", origin, "#f5ffff", 0.18, 0.08, 0.8);
    this.fxp("motes", origin, "#dbfdff", 7);
    this.snd("dagger", 0.35);
  }

  private finishSnowPuppet(p: SnowPuppet, exploded: boolean) {
    if (!this.snowPuppets.includes(p)) return;
    if (p.mode === "freeze" && exploded && this.cfg.role !== "client" && p.owner && p.atk) {
      const mid = p.pos.clone().add(new THREE.Vector3(0, 0.7, 0));
      this.fxp("explosion", mid, "#8fe3ff", p.atk.radius);
      this.fxp("motes", mid, "#e3f9ff", 18);
      this.fxp("ring", mid, "#b3ebff", p.atk.radius, 0.25, 0.75);
      for (const d of this.enemiesOf(p.owner)) {
        const to = d.root.position.clone().sub(p.pos);
        const height = Math.abs(to.y);
        to.y = 0;
        if (to.length() > p.atk.radius + d.radius * 0.5 || (this.plat && height > 1.6)) continue;
        if (!this.plat && d.airborne()) continue;
        const dir = to.lengthSq() > 0.0001 ? to.normalize() : new THREE.Vector3(1, 0, 0);
        this.applyHit(p.owner, d, p.atk, p.power, d.chest(), dir, true);
      }
    } else {
      this.fxp("motes", p.pos.clone().add(new THREE.Vector3(0, p.mode === "bird" ? 1.0 : 0.5, 0)), p.mode === "bird" ? "#f6ffff" : "#dcf9ff", p.mode === "bird" ? 10 : 8);
    }
    this.disposeSnowPuppet(p);
    this.snowPuppets = this.snowPuppets.filter(x => x !== p);
    if (this.cfg.role !== "client") this.emit(["snowPuppetEnd", p.id]);
  }

  private updateSnowPuppets(dt: number) {
    for (const p of [...this.snowPuppets]) {
      p.life -= dt;
      p.age += dt;
      if (this.cfg.role !== "client" && (!p.owner || p.owner.isDown() || this.roundOver)) {
        this.finishSnowPuppet(p, false);
        continue;
      }
      let target = this.entities.get(p.targetId);
      if (!target || target.isDown() || target.team === p.team) {
        target = p.owner ? this.enemiesOf(p.owner)[0] : undefined;
        if (target) p.targetId = target.id;
      }
      if (p.mode === "freeze") {
        if (p.state === "rush" && target) {
          const delta = target.root.position.clone().sub(p.pos);
          if (!this.plat) delta.y = 0;
          const distance = delta.length();
          const speed = p.atk?.speed ?? 4.2;
          if (distance > 0.05) {
            const direction = delta.multiplyScalar(1 / distance);
            p.pos.addScaledVector(direction, Math.min(Math.max(0, distance - 0.45), speed * dt));
            p.mesh.rotation.y = Math.atan2(direction.x, direction.z);
          }
          if (this.cfg.role !== "client" && distance < 0.95) {
            this.finishSnowPuppet(p, true);
            continue;
          }
        } else {
          p.pos.lerp(p.home, Math.min(1, dt * 6));
          p.mesh.rotation.y += dt * 0.8;
        }
        p.mesh.position.copy(p.pos).add(new THREE.Vector3(0, Math.sin(p.age * 5 + p.id) * 0.05, 0));
      } else {
        const ownerPos = p.owner ? p.owner.root.position : p.home;
        let desired = p.home.clone();
        if (p.state === "idle") {
          const ang = p.age * 0.9 + p.slot * (Math.PI * 2 / 3);
          desired = ownerPos.clone().add(new THREE.Vector3(Math.cos(ang) * 0.85, 1.55 + Math.sin(p.age * 2 + p.slot) * 0.18, Math.sin(ang) * 0.85));
        } else if (target) {
          const ang = p.slot * 1.35 + p.age * 0.35;
          desired = target.root.position.clone().add(new THREE.Vector3(Math.cos(ang) * 0.95, 1.55, Math.sin(ang) * 0.95));
          p.shotCd -= dt;
          if (this.cfg.role !== "client" && p.shotsLeft > 0 && p.shotCd <= 0) {
            this.fireSnowBirdShard(p, target);
            p.shotsLeft -= 1;
            p.shotCd = 3.0;
            if (p.shotsLeft <= 0) {
              this.finishSnowPuppet(p, false);
              continue;
            }
          }
        }
        const delta = desired.sub(p.pos);
        const dist = delta.length();
        if (dist > 0.01) {
          const dir = delta.multiplyScalar(1 / dist);
          p.pos.addScaledVector(dir, Math.min(dist, (p.atk?.speed ?? 5.1) * dt));
          p.mesh.rotation.y = Math.atan2(dir.x, dir.z);
        }
        p.mesh.position.copy(p.pos).add(new THREE.Vector3(0, Math.sin(p.age * 8 + p.slot) * 0.03, 0));
      }
      if (p.life <= 0) this.finishSnowPuppet(p, false);
    }
  }
'''
replace_once(game, old_methods, new_methods)

old_events = '''      case "snowPuppet": {
        // Guest renders a moving snowman; damage and freeze/slow are host-authoritative.
        this.makeSnowPuppet(ev[1], null, ev[3], null, 0, v3(ev[4]), ev[5], ev[6], ev[7]);
        break;
      }
      case "snowPuppetEnd": {
        const p = this.snowPuppets.find(x => x.id === ev[1]);
        if (p) this.finishSnowPuppet(p, false);
        break;
      }
'''
new_events = '''      case "snowPuppet": {
        this.makeSnowPuppet(ev[1], null, ev[3], null, 0, v3(ev[4]), ev[5], ev[6], ev[7], ev[8] ?? "idle", ev[9] ?? 0, ev[10] ?? 0);
        break;
      }
      case "snowPuppetCmd": {
        const p = this.snowPuppets.find(x => x.id === ev[1]);
        if (p) {
          p.state = ev[2] ?? p.state;
          p.targetId = ev[3] ?? p.targetId;
          p.shotsLeft = ev[4] ?? p.shotsLeft;
          p.shotCd = 0.1;
        }
        break;
      }
      case "snowPuppetEnd": {
        const p = this.snowPuppets.find(x => x.id === ev[1]);
        if (p) this.finishSnowPuppet(p, false);
        break;
      }
'''
replace_once(game, old_events, new_events)

old_sync = '    // ROXY_SNOW_PUPPET_MASTER_V1: late joiners also see currently active snow minions.\n    for (const p of this.snowPuppets) ev.push(["snowPuppet", p.id, p.owner?.id ?? -1, p.team, p.pos.toArray(), p.targetId, p.mode, p.life]);'
new_sync = '    // ROXY_MANUAL_SUMMONS_BIRD_V2_20261108: late joiners also see currently active frost summons.\n    for (const p of this.snowPuppets) ev.push(["snowPuppet", p.id, p.owner?.id ?? -1, p.team, p.pos.toArray(), p.targetId, p.mode, p.life, p.state, p.shotsLeft, p.slot]);'
replace_once(game, old_sync, new_sync)

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for p in FILES:
    if new[p] == old[p]:
        continue
    backup = p.with_name(p.name + f'.before_roxy_manual_{stamp}.bak')
    backup.write_text(old[p], encoding='utf-8')
    p.write_text(new[p], encoding='utf-8')
    print(f'PATCH {p.relative_to(ROOT)} (backup: {backup.name})')
print('DONE: Roxy manual summons update installed.')
print('Changes: Snowglass Shield 7s; X summons a light-blue idle marionette and X again commands it; V summons 3 white snowbirds and each extra V press releases one bird to attack; birds fire 1 ice shard every 3 seconds for 5 shots, then disappear.')
