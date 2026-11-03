// Playable fighter. A brain (local input, AI, or a remote player's inputs) fills `intent`
// every frame:
//   attack tap (release < HOLD_T)  -> normal attack, chains into the kit's combo
//   attack hold, then release      -> charged attack (stronger the longer it charged)
//   block hold                     -> block; the first parryWindow seconds parry
//   jump                           -> jump (dodges ground strikes and low projectiles)
//   skill "z" / "x" / "c"          -> skill, if off cooldown
// The arena gets `onSwing` when an attack reaches its active frame and resolves its effect.
// On network clients the fighter is a puppet: it only mirrors state sent by the host.
import * as THREE from "three";
import { FighterModel } from "./model";
import { Trail } from "./fx";
import * as Kits from "./kits";
import type { Attack, Pose } from "./kits";
import type { Look } from "./roster";

export enum S { IDLE, ATTACK, CHARGE, BLOCK, HITSTUN, STAGGER, KO, WIN }

export const HOLD_T = 0.22;
export const CHARGE_MAX = 0.9;
const ENGAGE = 1.45;
const MIN_DIST = 0.95;
const GRAVITY = 22;
const GUARD_REGEN = 30;

export interface Intent { attack: boolean; block: boolean; jump: boolean; skill: string; move: THREE.Vector3 }
export interface Brain { think(f: Fighter, dt: number): void }

/** Anything that can be hit: fighters and mobs. */
export interface Entity {
  id: number; kind: string; team: number; root: THREE.Group;
  hp: number; maxHp: number; radius: number; lastDamage: number; lastCrit: boolean;
  isDown(): boolean; chest(): THREE.Vector3; airborne(): boolean;
  receiveHit(attacker: Entity | null, a: Attack, power: number): string;
  update(dt: number): void;
}

export class Fighter implements Entity {
  id = 0;
  kind = "fighter";
  team = 0;
  root = new THREE.Group();
  look: Look;
  charIndex: number;
  kit: string;
  model: FighterModel;
  trail: Trail;
  brain: Brain | null = null;
  opponent: Entity | null = null;
  autoApproach = false;
  viewBias = 0;
  arenaRadius = 7;
  puppet = false;
  /** Network peer id that controls this fighter ("" = host / local). */
  owner = "";

  intent: Intent = { attack: false, block: false, jump: false, skill: "", move: new THREE.Vector3() };

  maxHp: number; maxGuard: number; moveSpeed: number; walkSpeed: number; parryWindow: number; jumpV: number;
  attacks: Record<string, Attack>;
  poses: Record<string, Pose>;
  radius = 0.35;

  state = S.IDLE;
  stateT = 0;
  hp: number;
  guard: number;
  atk: Attack | null = null;
  atkId = "";
  atkPhase = 0;
  atkPower = 1;
  swingSerial = 0;
  lastDamage = 0;
  lastCrit = false;
  cooldowns: Record<string, number> = { z: 0, x: 0, c: 0 };
  onGround = true;
  velY = 0;
  wardT = 0;
  counterT = 0;
  invulnT = 0;

  // Survival perks.
  dmgMult = 1;
  cdMult = 1;
  critChance = 0.2;
  lifesteal = 0;

  poseName = "idle";
  poseSpeed = 14;

  onSwing: (f: Fighter) => void = () => {};
  onKo: (f: Fighter) => void = () => {};
  onLanded: (f: Fighter) => void = () => {};

  private stun = 0;
  private stunPose = "hit";
  private comboNext = "l1";
  private comboTimer = 0;
  private buffered = false;
  private atkPrev = false;
  private jumpPrev = false;
  private holding = false;
  private holdT = 0;
  private guardDelay = 0;
  private knock = 0;
  private netPos = new THREE.Vector3();
  private netRot = 0;

  constructor(look: Look, charIndex: number) {
    this.look = look;
    this.charIndex = charIndex;
    this.kit = look.kit;
    const st = Kits.STATS[this.kit];
    this.maxHp = st.hp; this.maxGuard = st.guard; this.moveSpeed = st.move; this.walkSpeed = st.walk;
    this.parryWindow = st.parry; this.jumpV = st.jump;
    this.hp = this.maxHp;
    this.guard = this.maxGuard;
    this.attacks = Kits.attacks(this.kit, look.element);
    this.poses = Kits.poses(this.kit);
    this.root.rotation.order = "YXZ";
    this.model = new FighterModel(look);
    this.root.add(this.model);
    this.trail = new Trail(this.model.bladeBase, this.model.bladeTip, look.glow);
  }

  isDown() { return this.state === S.KO; }
  chest() { return this.root.position.clone().add(new THREE.Vector3(0, 1.1, 0)); }
  airborne() { return !this.onGround && this.root.position.y > 0.7; }

  update(dt: number) {
    if (this.puppet) { this.updatePuppet(dt); return; }
    const it = this.intent;
    it.attack = false; it.block = false; it.jump = false; it.skill = ""; it.move.set(0, 0, 0);
    if (this.brain && this.state !== S.KO && this.state !== S.WIN) this.brain.think(this, dt);
    if (!this.onGround) it.block = false;
    this.stateT += dt;
    for (const k in this.cooldowns) this.cooldowns[k] = Math.max(this.cooldowns[k] - dt, 0);
    this.wardT = Math.max(this.wardT - dt, 0);
    this.counterT = Math.max(this.counterT - dt, 0);
    this.invulnT = Math.max(this.invulnT - dt, 0);
    this.readAttack(dt);
    this.readJump();
    this.readSkill();

    switch (this.state) {
      case S.IDLE:
        this.comboTimer -= dt;
        if (this.comboTimer <= 0) this.comboNext = "l1";
        if (it.block) this.setState(S.BLOCK);
        break;
      case S.ATTACK: this.attackStep(); break;
      case S.CHARGE:
        if (it.block) { this.holding = false; this.setState(S.BLOCK); }
        else if (this.stateT >= CHARGE_MAX) { this.holding = false; this.startAttack("heavy"); }
        break;
      case S.BLOCK: if (!it.block) this.setState(S.IDLE); break;
      case S.HITSTUN:
      case S.STAGGER: if (this.stateT >= this.stun) this.setState(S.IDLE); break;
    }

    this.move(dt);
    this.vertical(dt);
    if (this.state !== S.BLOCK) {
      this.guardDelay -= dt;
      if (this.guardDelay <= 0) this.guard = Math.min(this.guard + GUARD_REGEN * dt, this.maxGuard);
    }
    const a = this.atk;
    this.trail.emitting = this.state === S.ATTACK && !!a && a.type === "melee" &&
      (this.atkPhase === 1 || (this.atkPhase === 0 && this.stateT > a.wind * 0.6) || (this.atkPhase === 2 && this.stateT < a.wind + a.active + 0.05));
    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");
    this.model.charge = this.state === S.CHARGE ? Math.min(this.stateT / CHARGE_MAX, 1) : Math.max(this.model.charge - dt * 4, 0);
    this.computePose();
    this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
    this.trail.update(dt);
  }

  // --- input -> actions ---------------------------------------------------------
  private readAttack(dt: number) {
    const on = this.intent.attack;
    const pressed = on && !this.atkPrev;
    const released = !on && this.atkPrev;
    this.atkPrev = on;
    if ([S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state)) { this.holding = false; return; }
    if (pressed) { this.holding = true; this.holdT = 0; }
    if (this.holding) {
      this.holdT += dt;
      if (this.holdT >= HOLD_T && this.state === S.IDLE && !this.intent.block) this.setState(S.CHARGE);
    }
    if (released && this.holding) {
      this.holding = false;
      if (this.state === S.CHARGE) this.startAttack("heavy");
      else if (this.holdT < HOLD_T) this.requestLight();
    }
  }

  private readJump() {
    const pressed = this.intent.jump && !this.jumpPrev;
    this.jumpPrev = this.intent.jump;
    if (pressed && this.onGround && (this.state === S.IDLE || this.state === S.BLOCK)) {
      this.velY = this.jumpV;
      this.onGround = false;
      if (this.state === S.BLOCK) this.setState(S.IDLE);
    }
  }

  private readSkill() {
    const k = this.intent.skill;
    if (!k || (this.cooldowns[k] ?? 1) > 0) return;
    const free = [S.IDLE, S.BLOCK, S.CHARGE].includes(this.state) || (this.state === S.ATTACK && this.atkPhase === 2);
    if (!free) return;
    this.holding = false;
    this.cooldowns[k] = this.attacks[k].cd * this.cdMult;
    this.startAttack(k);
  }

  private requestLight() {
    if (this.state === S.IDLE || this.state === S.BLOCK) this.startAttack(this.comboTimer > 0 ? this.comboNext : "l1");
    else if (this.state === S.ATTACK && this.atk && this.atk.next) this.buffered = true;
  }

  private startAttack(id: string) {
    this.atkPower = 1;
    if (id === "heavy" && this.state === S.CHARGE) this.atkPower = 1 + 0.5 * Math.min(this.stateT / CHARGE_MAX, 1);
    this.atkPower *= this.dmgMult;
    this.atkId = id;
    this.atk = this.attacks[id];
    this.atkPhase = 0;
    this.buffered = false;
    this.swingSerial++;
    if (this.atk.self_jump > 0) { this.velY = this.atk.self_jump; this.onGround = false; }
    this.setState(S.ATTACK);
  }

  private attackStep() {
    const a = this.atk!;
    const w = a.wind, ac = a.active, r = a.recover;
    if (this.atkPhase === 0 && this.stateT >= w) {
      this.atkPhase = 1;
      this.onSwing(this);
    } else if (this.atkPhase === 1 && this.stateT >= w + ac) {
      this.atkPhase = 2;
    } else if (this.atkPhase === 2) {
      if (this.buffered && a.next && this.stateT >= w + ac + Math.min(0.1, r)) this.startAttack(a.next);
      else if (this.intent.block && this.stateT >= w + ac + 0.06) { this.finishAttack(); this.setState(S.BLOCK); }
      else if (this.stateT >= w + ac + r) { this.finishAttack(); this.setState(S.IDLE); }
    }
  }

  private finishAttack() {
    const a = this.atk!;
    this.comboNext = a.next || "l1";
    this.comboTimer = a.next ? 0.45 : 0;
  }

  private setState(s: S) { this.state = s; this.stateT = 0; }

  // --- movement ---------------------------------------------------------------------
  private move(dt: number) {
    const pos = this.root.position;
    const o = this.opponent;
    let dir = new THREE.Vector3(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
    let dist = 99;
    if (o && !o.isDown()) {
      const to = o.root.position.clone().sub(pos);
      to.y = 0;
      dist = to.length();
      dir = to.divideScalar(Math.max(dist, 0.001));
    } else if (this.intent.move.lengthSq() > 0.01) {
      dir = this.intent.move.clone().normalize();
    }
    if (this.state !== S.KO) {
      const target = Math.atan2(dir.x, dir.z);
      let d = target - this.root.rotation.y;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.root.rotation.y += d * (1 - Math.exp(-12 * dt));
    }
    let v = 0;
    let walking = false;
    if (this.state === S.IDLE && this.autoApproach && o && !o.isDown() && dist > ENGAGE) { v = this.walkSpeed; walking = true; }
    if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1 && dist > MIN_DIST + 0.15) v += this.atk.lunge;
    this.knock = Math.max(this.knock - 14 * dt, 0);
    v -= this.knock;
    if (dist < MIN_DIST && v > 0) v = 0;
    pos.addScaledVector(dir, v * dt);
    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 : this.state === S.CHARGE ? 0.4 : 0;
    if (steer > 0 && this.intent.move.lengthSq() > 0.0001) {
      const step = this.intent.move.clone().normalize().multiplyScalar(this.moveSpeed * steer * dt);
      if (dist < MIN_DIST && step.dot(dir) > 0) step.addScaledVector(dir, -step.dot(dir));
      pos.add(step);
      walking = this.onGround;
    }
    if (dist < MIN_DIST * 0.9) pos.addScaledVector(dir, -(MIN_DIST * 0.9 - dist) * 0.5);
    const flat = Math.hypot(pos.x, pos.z);
    if (flat > this.arenaRadius) { pos.x *= this.arenaRadius / flat; pos.z *= this.arenaRadius / flat; }
    this.model.walk = Math.min(Math.max(this.model.walk + (walking ? 1 : -1) * dt * 6, 0), 1);
    if (this.state !== S.KO) this.model.rotation.y = this.viewBias;
  }

  private vertical(dt: number) {
    if (this.onGround) return;
    this.velY -= GRAVITY * dt;
    this.root.position.y += this.velY * dt;
    if (this.root.position.y <= 0) {
      this.root.position.y = 0;
      this.velY = 0;
      this.onGround = true;
      this.model.recoil = 0.35;
      this.onLanded(this);
    }
  }

  teleport(to: THREE.Vector3) {
    const flat = Math.hypot(to.x, to.z);
    const k = flat > this.arenaRadius ? this.arenaRadius / flat : 1;
    this.root.position.set(to.x * k, this.root.position.y, to.z * k);
    this.invulnT = 0.3;
    if (this.opponent) {
      const d = this.opponent.root.position.clone().sub(this.root.position);
      this.root.rotation.y = Math.atan2(d.x, d.z);
    }
  }

  // --- getting hit --------------------------------------------------------------------
  /** Returns "miss", "warded", "counter", "parry", "blocked", "guard_break", "hit", "crit" or "ko". */
  receiveHit(attacker: Entity | null, a: Attack, power: number): string {
    if (this.state === S.KO) return "none";
    if (this.invulnT > 0) return "miss";
    if (this.wardT > 0) { this.model.recoil = 0.4; return "warded"; }
    if (this.counterT > 0) { this.counterT = 0; return "counter"; }
    let dmg = a.dmg * power;
    if (this.state === S.BLOCK) {
      if (this.stateT <= this.parryWindow) {
        this.guard = Math.min(this.guard + 20, this.maxGuard);
        this.model.flash("#99e6ff", 0.15);
        return "parry";
      }
      this.guard -= a.guard * power;
      this.guardDelay = 1;
      if (this.guard <= 0) {
        this.guard = 0;
        this.lastDamage = dmg * 0.4;
        this.lastCrit = false;
        this.hp = Math.max(this.hp - this.lastDamage, 0);
        this.knock = 3.5;
        if (this.hp <= 0) { this.ko(); return "ko"; }
        this.stagger(1.1);
        this.model.flash("#ffd966", 0.18);
        return "guard_break";
      }
      this.knock = a.knock * 0.5;
      this.model.recoil = 0.7;
      return "blocked";
    }
    const cc = attacker && (attacker as any).critChance !== undefined ? (attacker as any).critChance : 0.2;
    this.lastCrit = Math.random() < cc;
    if (this.lastCrit) dmg *= 1.6;
    this.lastDamage = dmg;
    this.hp = Math.max(this.hp - dmg, 0);
    this.knock = a.knock;
    this.model.flash();
    if (this.hp <= 0) { this.ko(); return "ko"; }
    if (a.heavy || a.stagger) this.stagger(a.stun);
    else { this.stun = a.stun; this.stunPose = "hit"; this.holding = false; this.setState(S.HITSTUN); }
    return this.lastCrit ? "crit" : "hit";
  }

  stagger(d: number) { this.stun = d; this.stunPose = "stagger"; this.holding = false; this.setState(S.STAGGER); }

  clashRecoil() {
    this.stun = 0.38; this.stunPose = "clash"; this.holding = false; this.knock = 4; this.model.recoil = 1;
    this.setState(S.HITSTUN);
  }

  pushBack(speed: number) { this.knock = Math.max(this.knock, speed); }
  win() { if (this.state !== S.KO) this.setState(S.WIN); }

  revive(frac: number) {
    this.hp = this.maxHp * frac;
    this.guard = this.maxGuard;
    this.model.standUp();
    this.setState(S.IDLE);
  }

  heal(amount: number) { this.hp = Math.min(this.hp + amount, this.maxHp); }

  private ko() {
    this.setState(S.KO);
    this.model.fall();
    this.onKo(this);
  }

  // --- posing -------------------------------------------------------------------------
  private computePose() {
    let p = "idle", sp = 14;
    const a = this.atk;
    switch (this.state) {
      case S.IDLE: if (!this.onGround) { p = "jump"; sp = 12; } break;
      case S.BLOCK: p = "block"; sp = 30; break;
      case S.CHARGE: p = this.attacks.heavy.pose_w; sp = 10; break;
      case S.ATTACK:
        if (this.atkPhase === 0) { p = a!.pose_w; sp = 22; }
        else if (this.atkPhase === 1) { p = a!.pose_s; sp = 45; }
        else if (this.stateT < a!.wind + a!.active + a!.recover * 0.5) { p = a!.pose_s; sp = 20; }
        else sp = 9;
        break;
      case S.HITSTUN:
      case S.STAGGER: p = this.stunPose; sp = 28; break;
      case S.KO: p = "down"; sp = 10; break;
      case S.WIN: p = "win"; sp = 6; break;
    }
    this.poseName = p;
    this.poseSpeed = sp;
  }

  // --- networking -----------------------------------------------------------------------
  /** Compact state sent from the host to clients. */
  snapshot(): any[] {
    const p = this.root.position;
    return [this.id, +p.x.toFixed(3), +p.y.toFixed(3), +p.z.toFixed(3), +this.root.rotation.y.toFixed(3),
      this.state, this.poseName, this.poseSpeed, Math.round(this.hp), Math.round(this.guard),
      +this.model.walk.toFixed(2), +this.model.charge.toFixed(2), this.trail.emitting ? 1 : 0,
      +this.model.recoil.toFixed(2), this.cooldowns.z, this.cooldowns.x, this.cooldowns.c, this.maxHp];
  }

  applySnapshot(s: any[]) {
    this.netPos.set(s[1], s[2], s[3]);
    this.netRot = s[4];
    const prev = this.state;
    this.state = s[5];
    this.poseName = s[6];
    this.poseSpeed = s[7];
    this.hp = s[8];
    this.guard = s[9];
    this.model.walk = s[10];
    this.model.charge = s[11];
    this.trail.emitting = s[12] === 1;
    this.model.recoil = Math.max(this.model.recoil, s[13]);
    this.cooldowns.z = s[14]; this.cooldowns.x = s[15]; this.cooldowns.c = s[16];
    this.maxHp = s[17];
    if (this.state === S.KO && prev !== S.KO) this.model.fall();
    if (this.state !== S.KO && prev === S.KO) this.model.standUp();
  }

  private updatePuppet(dt: number) {
    const k = 1 - Math.exp(-15 * dt);
    if (this.root.position.distanceTo(this.netPos) > 3) this.root.position.copy(this.netPos);
    else this.root.position.lerp(this.netPos, k);
    let d = this.netRot - this.root.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    this.root.rotation.y += d * k;
    for (const key in this.cooldowns) this.cooldowns[key] = Math.max(this.cooldowns[key] - dt, 0);
    if (this.state !== S.KO) this.model.rotation.y = this.viewBias;
    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");
    this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
    this.trail.update(dt);
  }
}
