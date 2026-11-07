// Survival enemies: data table, procedural toon models and simple per-type AI.
// The arena owns combat resolution; mobs ask it to hit, shoot or drop area attacks.
import { StatusSet, type StatusKind } from "./status";
import * as THREE from "three";
import * as M from "./mat";
import { mesh, pivot, sphere, cyl, cap, box } from "./model";
import { coneSheet } from "./meshgen";
import type { Entity } from "./fighter";
import type { Attack } from "./kits";

export interface MobType {
  name: string; hp: number; speed: number; dmg: number; attack: string; range: number; wind: number; cd: number;
  radius: number; cost: number; fly?: number; keep?: number; projSpeed?: number; style?: string; color: string;
  armor?: boolean; boss?: boolean;
}

export const MOB_TYPES: Record<string, MobType> = {
  slime: { name: "Slime", hp: 180, speed: 2.2, dmg: 45, attack: "contact", range: 0.95, wind: 0.25, cd: 1.0, radius: 0.5, cost: 1, color: "#59d96a" },
  bat: { name: "Bat", hp: 90, speed: 5.2, dmg: 30, attack: "contact", range: 0.8, wind: 0.2, cd: 1.3, radius: 0.35, cost: 1, fly: 1.4, color: "#5a3f7a" },
  goblin: { name: "Goblin", hp: 260, speed: 3.0, dmg: 65, attack: "melee", range: 1.45, wind: 0.42, cd: 1.5, radius: 0.4, cost: 2, color: "#7cbf4a" },
  archer: { name: "Skeleton Archer", hp: 200, speed: 2.4, dmg: 55, attack: "ranged", range: 11, keep: 6, wind: 0.6, cd: 2.4, projSpeed: 15, style: "arrow", radius: 0.4, cost: 2, color: "#ece6d6" },
  imp: { name: "Fire Imp", hp: 210, speed: 3.4, dmg: 60, attack: "ranged", range: 10, keep: 5, wind: 0.5, cd: 2.2, projSpeed: 12, style: "bolt", radius: 0.4, cost: 3, fly: 1.5, color: "#ff5a3d" },
  wraith: { name: "Wraith", hp: 330, speed: 2.8, dmg: 85, attack: "blink", range: 1.6, wind: 0.45, cd: 3.2, radius: 0.45, cost: 3, color: "#6a4fa8" },
  brute: { name: "Ogre Brute", hp: 1150, speed: 1.8, dmg: 160, attack: "slam", range: 2.4, wind: 0.95, cd: 3.4, radius: 0.85, cost: 6, armor: true, color: "#8a7f9e" },
  golem: { name: "Ancient Golem", hp: 9000, speed: 1.7, dmg: 190, attack: "boss", range: 3.2, wind: 0.9, cd: 2.4, radius: 1.3, cost: 0, armor: true, boss: true, color: "#8c7a66" },
};

export interface MobHost {
  mobHit(mob: Mob, target: Entity, dmg: number, knock: number, stun: number): void;
  mobShoot(mob: Mob, target: Entity, spread?: number): void;
  mobStrike(mob: Mob, center: THREE.Vector3, radius: number, delay: number, dmg: number, style: string): void;
  mobSummon(mob: Mob, type: string, count: number): void;
  nearestPlayer(from: THREE.Vector3): Entity | null;
}

enum MS { CHASE, WIND, RECOVER, FLINCH, DEAD }

export class Mob implements Entity {
  id = 0;
  kind = "mob";
  team = 1;
  root = new THREE.Group();
  type: string;
  def: MobType;
  hp: number;
  maxHp: number;
  dmg: number;
  radius: number;
  elite: boolean;
  lastDamage = 0;
  lastCrit = false;
  puppet = false;
  host: MobHost | null = null;
  /** Status effects; damage-over-time ticks queue in `dots` for the game. */
  status = new StatusSet();
  dots: { kind: StatusKind; dmg: number; src: unknown }[] = [];

  state = MS.CHASE;
  stateT = 0;
  private cdT = 1 + Math.random();
  private target: Entity | null = null;
  private knockV = new THREE.Vector3();
  private body!: THREE.Group;
  private armR: THREE.Group | null = null;
  private armL: THREE.Group | null = null;
  private wings: THREE.Group[] = [];
  private t = Math.random() * 10;
  private flashT = 0;
  private bossStep = 0;
  private summoned = false;
  private windStarted = false;
  private strafe = Math.random() < 0.5 ? 1 : -1;
  private netPos = new THREE.Vector3();
  private netRot = 0;
  dead = false;
  deathT = 0;

  /** HP scale it was spawned with (sent to late joiners). */
  hpMult = 1;
  constructor(type: string, hpMult = 1, dmgMult = 1, elite = false) {
    this.type = type;
    this.def = MOB_TYPES[type];
    this.elite = elite;
    this.hpMult = hpMult;
    this.maxHp = this.def.hp * hpMult * (elite ? 2.2 : 1);
    this.hp = this.maxHp;
    this.dmg = this.def.dmg * dmgMult * (elite ? 1.3 : 1);
    this.radius = this.def.radius * (elite ? 1.25 : 1);
    this.root.rotation.order = "YXZ";
    this.build();
    if (elite) this.body.scale.multiplyScalar(1.25);
  }

  isDown() { return this.dead; }
  chest() { return this.root.position.clone().add(new THREE.Vector3(0, (this.def.fly ?? 0) + this.radius * 1.4, 0)); }
  airborne() { return false; }

  // --- models -------------------------------------------------------------------
  private build() {
    this.body = pivot(this.root);
    const c = this.def.color;
    const T = (col: string, rim = 0.3) => M.toon(col, { rim });
    const eyes = (parent: THREE.Object3D, y: number, z: number, x: number, r: number, color = "#1a1020") => {
      for (const s of [1, -1]) mesh(parent, sphere(r, 10), M.toon(color, { outline: false }), [x * s, y, z]);
    };
    switch (this.type) {
      case "slime": {
        mesh(this.body, sphere(0.45, 24), M.water(c, 0.8, 1.2), [0, 0.38, 0], [0, 0, 0], [1, 0.8, 1]);
        mesh(this.body, sphere(0.3, 16), M.toon("#2f8f40", { outline: false }), [0, 0.3, 0], [0, 0, 0], [1, 0.75, 1]);
        eyes(this.body, 0.48, 0.37, 0.13, 0.055);
        for (const s of [1, -1]) mesh(this.body, sphere(0.018, 8), M.glow("#ffffff"), [0.115 * s, 0.505, 0.42]);
        break;
      }
      case "bat": {
        const fly = this.def.fly!;
        mesh(this.body, sphere(0.17, 16), T(c), [0, fly, 0]);
        for (const s of [1, -1]) mesh(this.body, cyl(0, 0.05, 0.12, 6), T(c), [0.09 * s, fly + 0.16, 0]);
        eyes(this.body, fly + 0.04, 0.14, 0.06, 0.03, "#ff3344");
        for (const s of [1, -1]) {
          const w = pivot(this.body, [0.12 * s, fly + 0.02, 0]);
          mesh(w, box(0.42, 0.015, 0.24), T("#3a2850"), [0.21 * s, 0, 0]);
          this.wings.push(w);
        }
        break;
      }
      case "goblin": {
        for (const s of [1, -1]) mesh(this.body, cap(0.05, 0.42), T(c), [0.08 * s, 0.22, 0]);
        mesh(this.body, box(0.26, 0.12, 0.2), T("#6b4a2a"), [0, 0.45, 0]);
        mesh(this.body, cap(0.13, 0.36), T(c), [0, 0.62, 0]);
        mesh(this.body, sphere(0.17, 20), T(c), [0, 0.95, 0.02]);
        for (const s of [1, -1]) mesh(this.body, cyl(0, 0.05, 0.24, 6), T(c), [0.19 * s, 1.0, 0], [0, 0, -1.2 * s]);
        eyes(this.body, 0.98, 0.15, 0.06, 0.03, "#ffd23a");
        mesh(this.body, sphere(0.035, 8), T("#5fa83a"), [0, 0.93, 0.18]);
        this.armR = pivot(this.body, [-0.16, 0.76, 0]);
        mesh(this.armR, cap(0.04, 0.32), T(c), [0, -0.14, 0]);
        mesh(this.armR, cyl(0.03, 0.05, 0.45, 8), T("#7a5230"), [0, -0.3, 0.2], [1.4, 0, 0]);
        mesh(this.armR, sphere(0.08, 10), T("#7a5230"), [0, -0.33, 0.43]);
        this.armL = pivot(this.body, [0.16, 0.76, 0]);
        mesh(this.armL, cap(0.04, 0.32), T(c), [0, -0.14, 0]);
        break;
      }
      case "archer": {
        for (const s of [1, -1]) mesh(this.body, cap(0.03, 0.6), T(c), [0.08 * s, 0.3, 0]);
        mesh(this.body, cyl(0.1, 0.07, 0.32, 10), T(c), [0, 0.8, 0]);
        for (let i = 0; i < 3; i++) mesh(this.body, box(0.24, 0.02, 0.14), T(c), [0, 0.72 + i * 0.07, 0.01]);
        mesh(this.body, cap(0.025, 0.25), T(c), [0, 0.55, 0]);
        mesh(this.body, sphere(0.15, 18), T(c), [0, 1.1, 0]);
        eyes(this.body, 1.11, 0.12, 0.05, 0.035, "#200810");
        for (const s of [1, -1]) mesh(this.body, sphere(0.012, 6), M.glow("#ff5a3a"), [0.05 * s, 1.11, 0.145]);
        this.armR = pivot(this.body, [-0.14, 0.92, 0]);
        mesh(this.armR, cap(0.022, 0.4), T(c), [0, -0.18, 0]);
        this.armL = pivot(this.body, [0.14, 0.92, 0]);
        mesh(this.armL, cap(0.022, 0.4), T(c), [0, -0.18, 0]);
        const bow = pivot(this.armL, [0, -0.36, 0]);
        mesh(bow, cyl(0.012, 0.012, 0.8, 6), T("#5a3a2a"), [0, 0.05, 0], [PI2, 0, 0]);
        break;
      }
      case "imp": {
        const fly = this.def.fly!;
        mesh(this.body, sphere(0.2, 18), T(c), [0, fly, 0], [0, 0, 0], [1, 1.15, 0.9]);
        mesh(this.body, sphere(0.15, 16), T(c), [0, fly + 0.3, 0.02]);
        for (const s of [1, -1]) mesh(this.body, cyl(0, 0.035, 0.14, 6), T("#3a1010"), [0.08 * s, fly + 0.45, 0], [0, 0, -0.4 * s]);
        eyes(this.body, fly + 0.32, 0.13, 0.05, 0.03, "#ffe14d");
        mesh(this.body, cyl(0.01, 0.025, 0.4, 6), T(c), [0, fly - 0.25, -0.15], [-0.8, 0, 0]);
        for (const s of [1, -1]) {
          const w = pivot(this.body, [0.15 * s, fly + 0.12, -0.08]);
          mesh(w, box(0.36, 0.012, 0.22), T("#7a1f1f"), [0.18 * s, 0, 0]);
          this.wings.push(w);
        }
        this.armR = pivot(this.body, [-0.18, fly + 0.08, 0]);
        mesh(this.armR, cap(0.03, 0.2), T(c), [0, -0.08, 0]);
        mesh(this.armR, sphere(0.06, 10), M.glow("#ffb347"), [0, -0.2, 0.02]);
        break;
      }
      case "wraith": {
        mesh(this.body, coneSheet(0.12, 0.42, 1.1, 0, Math.PI * 2, 28, 6, 0.04, 9), M.cloth(c, { bottom: "#1c1430", trimBottom: 0.04, trim: "#b38cff", wind: 0.05 }), [0, 1.35, 0]);
        mesh(this.body, sphere(0.19, 18), T("#2a2040"), [0, 1.42, 0]);
        for (const s of [1, -1]) mesh(this.body, sphere(0.03, 8), M.glow("#b3f0ff"), [0.065 * s, 1.43, 0.16]);
        this.armR = pivot(this.body, [-0.2, 1.2, 0]);
        mesh(this.armR, cap(0.04, 0.4), T(c), [0, -0.18, 0]);
        const sc = pivot(this.armR, [0, -0.36, 0], [PI2, 0, 0]);
        mesh(sc, cyl(0.014, 0.014, 1.3, 8), T("#3a3046"), [0, 0.3, 0]);
        mesh(sc, box(0.5, 0.06, 0.015), M.toon("#dfe6ff", { rim: 0.8 }), [0.22, 0.92, 0], [0, 0, -0.35]);
        break;
      }
      case "brute": {
        for (const s of [1, -1]) mesh(this.body, cap(0.13, 0.6), T(c), [0.2 * s, 0.32, 0]);
        mesh(this.body, sphere(0.52, 24), T(c), [0, 1.0, 0], [0, 0, 0], [1.1, 1, 0.9]);
        mesh(this.body, cyl(0.45, 0.5, 0.2, 18), T("#5a3a2a"), [0, 0.6, 0]);
        mesh(this.body, sphere(0.2, 16), T(c), [0, 1.55, 0.18]);
        eyes(this.body, 1.6, 0.36, 0.07, 0.035, "#ffcc33");
        for (const s of [1, -1]) mesh(this.body, cyl(0, 0.03, 0.12, 6), T("#f4eed8"), [0.08 * s, 1.47, 0.34], [-0.4, 0, 0]);
        for (const s of [1, -1]) {
          const arm = pivot(this.body, [0.55 * s, 1.25, 0]);
          mesh(arm, cap(0.13, 0.75), T(c), [0, -0.34, 0]);
          mesh(arm, sphere(0.2, 16), T(c), [0, -0.78, 0.04]);
          if (s > 0) this.armL = arm; else this.armR = arm;
        }
        break;
      }
      case "golem": {
        const rock = T(c, 0.4);
        const dark = T("#5e5044");
        for (const s of [1, -1]) mesh(this.body, box(0.5, 1.0, 0.55), dark, [0.45 * s, 0.5, 0]);
        mesh(this.body, box(1.5, 1.3, 1.0), rock, [0, 1.6, 0]);
        mesh(this.body, box(0.7, 0.55, 0.6), rock, [0, 2.55, 0.1]);
        mesh(this.body, sphere(0.22, 16), M.glow("#ff9a3d"), [0, 1.7, 0.5]);
        for (const s of [1, -1]) mesh(this.body, box(0.12, 0.08, 0.05), M.glow("#ffcf6a"), [0.16 * s, 2.6, 0.41]);
        for (let i = 0; i < 4; i++) mesh(this.body, box(0.3, 0.25, 0.3), dark, [Math.sin(i * 1.7) * 0.6, 2.0 + Math.cos(i) * 0.3, -0.45], [i, i * 0.5, 0]);
        for (const s of [1, -1]) {
          const arm = pivot(this.body, [1.0 * s, 2.05, 0]);
          mesh(arm, box(0.45, 1.0, 0.45), dark, [0, -0.5, 0]);
          mesh(arm, box(0.65, 0.6, 0.65), rock, [0, -1.2, 0.1]);
          if (s > 0) this.armL = arm; else this.armR = arm;
        }
        break;
      }
    }
  }

  // --- simulation ---------------------------------------------------------------------
  update(dt: number) {
    this.t += dt;
    if (this.flashT > 0) { this.flashT -= dt; if (this.flashT <= 0) this.unflash(); }
    if (this.puppet) { this.updatePuppet(dt); return; }
    if (this.dead) { this.animate(dt); return; }
    for (const d of this.status.tick(dt, true).dots) {
      if (this.dead) break;
      this.hp = Math.max(this.hp - d.dmg, 0);
      this.dots.push({ ...d, src: this.status.src });
      if (this.hp <= 0) this.die();
    }
    if (this.dead) return;
    if (this.status.has("freeze")) {
      this.state = MS.FLINCH; this.stateT = 0;
      this.windStarted = false;
      this.animate(dt);
      return;
    }
    this.stateT += dt * this.status.actionSpeedMult();
    this.cdT -= dt * this.status.actionSpeedMult();
    const pos = this.root.position;
    this.target = this.host?.nearestPlayer(pos) ?? null;
    const tg = this.target;
    let dist = 99;
    let dir = new THREE.Vector3(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
    if (tg) {
      const to = tg.root.position.clone().sub(pos);
      to.y = 0;
      dist = to.length();
      dir = to.divideScalar(Math.max(dist, 0.001));
    }
    const face = (k = 8) => {
      let d = Math.atan2(dir.x, dir.z) - this.root.rotation.y;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.root.rotation.y += d * (1 - Math.exp(-k * dt));
    };
    pos.addScaledVector(this.knockV, dt);
    this.knockV.multiplyScalar(Math.max(1 - 6 * dt, 0));
    const d = this.def;
    switch (this.state) {
      case MS.FLINCH:
        if (this.stateT > 0.25) this.set(MS.CHASE);
        break;
      case MS.CHASE: {
        if (!tg) break;
        face();
        const reach = d.range + (tg as any).radius;
        if (d.attack === "ranged") {
          const want = d.keep ?? 5;
          const side = new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(this.strafe * 0.6);
          const mv = dist > want + 1 ? dir.clone() : dist < want - 1.5 ? dir.clone().negate() : side;
          pos.addScaledVector(mv.normalize(), d.speed * this.status.speedMult() * dt);
          if (this.cdT <= 0 && dist < d.range) this.set(MS.WIND);
          if (Math.random() < dt * 0.4) this.strafe *= -1;
        } else if (d.attack === "boss") {
          if (dist > 2.6) pos.addScaledVector(dir, d.speed * this.status.speedMult() * dt);
          if (this.cdT <= 0) this.set(MS.WIND);
        } else {
          if (dist > reach * 0.8) pos.addScaledVector(dir, d.speed * this.status.speedMult() * dt);
          if (this.cdT <= 0 && dist < reach + (d.attack === "blink" ? 6 : 0.2)) this.set(MS.WIND);
        }
        break;
      }
      case MS.WIND: {
        face(d.attack === "contact" ? 4 : 10);
        if (!this.windStarted) { this.windStarted = true; this.onWindStart(tg, dir); }
        if (d.attack === "contact" && this.stateT > d.wind * 0.6) pos.addScaledVector(dir, d.speed * 3 * dt);
        if (this.stateT >= d.wind) { this.strike(tg, dir, dist); this.set(MS.RECOVER); }
        break;
      }
      case MS.RECOVER:
        if (this.stateT > 0.45) { this.cdT = d.cd * (0.8 + Math.random() * 0.4); this.set(MS.CHASE); }
        break;
    }
    const flat = Math.hypot(pos.x, pos.z);
    const R = 11;
    if (flat > R) { pos.x *= R / flat; pos.z *= R / flat; }
    this.animate(dt);
  }

  private set(s: MS) { this.state = s; this.stateT = 0; this.windStarted = false; }

  private onWindStart(tg: Entity | null, dir: THREE.Vector3) {
    if (!tg || !this.host) return;
    const d = this.def;
    if (d.attack === "blink") {
      // Reappear just behind the target.
      const behind = tg.root.position.clone().addScaledVector(dir, 1.1);
      this.root.position.set(behind.x, 0, behind.z);
      this.root.rotation.y = Math.atan2(-dir.x, -dir.z);
    } else if (d.attack === "slam") {
      this.host.mobStrike(this, tg.root.position.clone(), 2.2 * (this.elite ? 1.2 : 1), d.wind, this.dmg, "slam");
    } else if (d.attack === "boss") {
      const step = this.bossStep++ % 4;
      if (step === 0) this.host.mobStrike(this, this.root.position.clone(), 3.6, d.wind, this.dmg, "slam");
      else if (step === 2) this.host.mobStrike(this, tg.root.position.clone(), 2.6, d.wind + 0.3, this.dmg * 1.2, "meteor");
      if (!this.summoned && this.hp < this.maxHp * 0.5) { this.summoned = true; this.host.mobSummon(this, "slime", 4); }
    }
  }

  private strike(tg: Entity | null, dir: THREE.Vector3, dist: number) {
    if (!tg || !this.host || tg.isDown()) return;
    const d = this.def;
    const reach = d.range + (tg as any).radius + 0.3;
    switch (d.attack) {
      case "contact":
      case "melee":
      case "blink": {
        const to = tg.root.position.clone().sub(this.root.position);
        to.y = 0;
        const fwd = new THREE.Vector3(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
        if (to.length() <= reach && (d.attack === "contact" || to.normalize().dot(fwd) > 0.2) && !tg.airborne())
          this.host.mobHit(this, tg, this.dmg, d.attack === "contact" ? 2 : 3, 0.3);
        break;
      }
      case "ranged":
        this.host.mobShoot(this, tg, this.elite ? 0.15 : 0);
        break;
      case "boss": {
        const step = (this.bossStep - 1) % 4;
        if (step === 1) this.host.mobShoot(this, tg, 0.35);
        if (step === 3 && dist < 4) this.host.mobHit(this, tg, this.dmg * 0.8, 6, 0.6);
        break;
      }
    }
  }

  receiveHit(_attacker: Entity | null, a: Attack, power: number): string {
    if (this.dead) return "none";
    const cc = _attacker && (_attacker as any).critChance !== undefined ? (_attacker as any).critChance : 0.2;
    this.lastCrit = Math.random() < cc;
    const dmg = a.dmg * power * (this.lastCrit ? 1.6 : 1);
    this.lastDamage = dmg;
    this.hp = Math.max(this.hp - dmg, 0);
    this.flash();
    if (_attacker) {
      const away = this.root.position.clone().sub(_attacker.root.position);
      away.y = 0;
      const resist = this.def.boss ? 0.15 : this.def.armor ? 0.4 : 1;
      this.knockV.copy(away.normalize().multiplyScalar(a.knock * 1.6 * resist));
    }
    if (this.hp <= 0) { this.die(); return "ko"; }
    if (a.effect) this.status.apply(a.effect as StatusKind, a.effect_t, a.effect_p, _attacker);
    if (!this.def.armor && (this.state !== MS.WIND || a.heavy)) this.set(MS.FLINCH);
    return this.lastCrit ? "crit" : "hit";
  }

  die() {
    this.dead = true;
    this.deathT = 0;
  }

  private flash() {
    this.flashT = 0.08;
    this.root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh || !m.userData.fill) return;
      if (!m.userData.orig) m.userData.orig = m.material;
      m.material = WHITE;
    });
  }

  private unflash() {
    this.root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh && m.userData.orig) { m.material = m.userData.orig; m.userData.orig = null; }
    });
  }

  // --- animation ----------------------------------------------------------------------
  private animate(dt: number) {
    const b = this.body;
    if (this.dead) {
      this.deathT += dt;
      const f = Math.min(this.deathT / 0.45, 1);
      b.scale.setScalar((this.elite ? 1.25 : 1) * (1 - f));
      b.position.y = (this.def.fly ? -this.def.fly * f : 0);
      return;
    }
    const wind = this.state === MS.WIND ? Math.min(this.stateT / this.def.wind, 1) : 0;
    const rec = this.state === MS.RECOVER ? 1 - Math.min(this.stateT / 0.45, 1) : 0;
    const flinch = this.state === MS.FLINCH ? 1 - this.stateT / 0.25 : 0;
    b.rotation.x = -0.35 * flinch;
    switch (this.type) {
      case "slime": {
        const hop = Math.abs(Math.sin(this.t * 6));
        b.scale.set(1 + 0.12 * (1 - hop) + 0.2 * wind, 1 - 0.15 * (1 - hop) - 0.25 * wind + 0.3 * rec, 1 + 0.12 * (1 - hop) + 0.2 * wind);
        b.position.y = 0.12 * hop;
        break;
      }
      case "bat":
      case "imp":
        for (const [i, w] of this.wings.entries()) w.rotation.z = Math.sin(this.t * (this.type === "bat" ? 22 : 12)) * 0.6 * (i ? -1 : 1);
        b.position.y = Math.sin(this.t * 3) * 0.08 - (this.type === "bat" ? 0.9 * wind : 0);
        if (this.armR) this.armR.rotation.x = -1.6 * wind + 0.8 * rec;
        break;
      default: {
        b.position.y = Math.abs(Math.sin(this.t * 7)) * 0.03;
        const swing = -2.6 * wind + 1.2 * rec;
        if (this.armR) this.armR.rotation.x = swing;
        if (this.armL) this.armL.rotation.x = this.type === "archer" ? -1.5 * (wind > 0 ? 1 : 0.3) : this.type === "brute" || this.type === "golem" ? swing : -0.2;
        if (this.type === "archer" && this.armR) this.armR.rotation.x = -1.4 * wind;
        b.rotation.x += 0.25 * rec;
      }
    }
  }

  // --- networking -----------------------------------------------------------------------
  snapshot(): any[] {
    const p = this.root.position;
    return [this.id, +p.x.toFixed(3), +p.y.toFixed(3), +p.z.toFixed(3), +this.root.rotation.y.toFixed(3),
      this.state, +this.stateT.toFixed(2), Math.round(this.hp), this.dead ? 1 : 0, this.status.mask];
  }

  applySnapshot(s: any[]) {
    this.netPos.set(s[1], s[2], s[3]);
    this.netRot = s[4];
    this.state = s[5];
    this.stateT = s[6];
    const hp = s[7];
    if (hp < this.hp) this.flash();
    this.hp = hp;
    if (s[8] === 1 && !this.dead) this.die();
    this.status.mask = s[9] ?? 0;
  }

  private updatePuppet(dt: number) {
    const k = 1 - Math.exp(-15 * dt);
    if (this.root.position.distanceTo(this.netPos) > 3) this.root.position.copy(this.netPos);
    else this.root.position.lerp(this.netPos, k);
    let d = this.netRot - this.root.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    this.root.rotation.y += d * k;
    this.stateT += dt;
    this.animate(dt);
  }
}

const PI2 = Math.PI / 2;
const WHITE = new THREE.MeshBasicMaterial({ color: "#ffffff" });

/** Builds one survival wave: a point budget spent on enemy types unlocked by wave number. */
export function waveRoster(wave: number): { type: string; elite: boolean }[] {
  const out: { type: string; elite: boolean }[] = [];
  if (wave % 5 === 0) {
    out.push({ type: "golem", elite: false });
    for (let i = 0; i < 2 + wave / 5; i++) out.push({ type: "goblin", elite: false });
    return out;
  }
  const unlocked = ["slime", "bat"];
  if (wave >= 2) unlocked.push("goblin");
  if (wave >= 3) unlocked.push("archer");
  if (wave >= 4) unlocked.push("imp", "wraith");
  if (wave >= 6) unlocked.push("brute");
  let budget = 5 + wave * 3;
  while (budget > 0) {
    const t = unlocked[Math.floor(Math.random() * unlocked.length)];
    const cost = MOB_TYPES[t].cost;
    if (cost > budget && budget < 6) { if (budget >= 1) { out.push({ type: "slime", elite: false }); budget -= 1; } continue; }
    out.push({ type: t, elite: wave >= 4 && Math.random() < 0.08 + wave * 0.01 });
    budget -= cost;
  }
  return out;
}
