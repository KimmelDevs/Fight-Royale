// Duel CPU. Presses the same virtual buttons a player would, with human-ish reaction times:
// reacts once per enemy swing / projectile / ground marker (block, parry, jump, sidestep),
// keeps its preferred range (ranged kits kite), and picks attacks and skills when idle.
import * as THREE from "three";
import { Fighter, S, HOLD_T, type Brain } from "./fighter";

export const LEVELS = ["Easy", "Normal", "Hard", "Master"];
const PRESETS = [
  { block: 0.2, parry: 0.0, jump: 0.1, react: [0.3, 0.5], think: 1.8, skill: [3.5, 6.0], combo: 2 },
  { block: 0.38, parry: 0.06, jump: 0.22, react: [0.18, 0.34], think: 1.25, skill: [2.0, 3.8], combo: 3 },
  { block: 0.5, parry: 0.14, jump: 0.3, react: [0.12, 0.26], think: 1.0, skill: [1.2, 2.6], combo: 4 },
  { block: 0.65, parry: 0.3, jump: 0.45, react: [0.08, 0.16], think: 0.7, skill: [0.8, 1.6], combo: 5 },
];

export interface Threats {
  projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number }[];
  strikes(): { target: any; land: number; id: number }[];
  now(): number;
}

const rand = (a: number, b: number) => a + Math.random() * (b - a);
const RANGED = new Set(["mage", "bow"]);

export class AiBrain implements Brain {
  private p = PRESETS[1];
  private queue: [number, number][] = [];
  private hold = 0;
  private blockWait = -1;
  private blockDur = 0;
  private blockHold = 0;
  private jumpWait = -1;
  private sideT = 0;
  private sideSign = 1;
  private strafeT = 0;
  private thinkCd = 1;
  private skillCd = 2;
  private seenSwing = -1;
  private seenCharge = false;
  private seen = new Set<number>();

  constructor(private threats: Threats, level: number) {
    this.p = PRESETS[Math.max(0, Math.min(level, PRESETS.length - 1))];
  }

  think(f: Fighter, dt: number) {
    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    if (f.stage) { if (this.platform(f, o, dt)) return; }
    this.react(f, o);
    if (!f.stage) { this.dodge(f); this.position(f, o, dt); }
    this.offense(f, o, dt);
    if (f.kit === "wind" && !f.stage) this.airDive(f, o, dt);
    if (this.jumpWait >= 0) { this.jumpWait -= dt; if (this.jumpWait < 0) { this.jumpPulse = !this.jumpPulse; f.intent.jump = true; } }
    if (this.blockWait >= 0) { this.blockWait -= dt; if (this.blockWait < 0) this.blockHold = this.blockDur; }
    if (this.blockHold > 0) {
      this.blockHold -= dt;
      f.intent.block = true;
      this.queue = [];
      this.hold = 0;
      return;
    }
    if (this.hold > 0) {
      this.hold -= dt;
      f.intent.attack = this.hold > 0;
    } else if (this.queue.length) {
      this.queue[0][0] -= dt;
      if (this.queue[0][0] <= 0) { this.hold = this.queue[0][1]; this.queue.shift(); f.intent.attack = true; }
    }
  }

  private jumpPulse = false;
  private airPlan = -1;
  private airDouble = false;

  /** Wind kit: now and then jump (sometimes double jump) and come down with an air skill. */
  private airDive(f: Fighter, o: Fighter, dt: number) {
    const ready = ["z", "x", "c"].filter((k) => f.attacks[k + "_air"] && f.cooldowns[k] <= 0);
    if (f.onGround) {
      this.airPlan = -1;
      const dist = f.root.position.distanceTo(o.root.position);
      if (f.state === S.IDLE && ready.length && dist < 6 && Math.random() < dt * 0.5) {
        f.intent.jump = true;
        this.airPlan = 0.3 + Math.random() * 0.25;
        this.airDouble = Math.random() < 0.5;
      }
      return;
    }
    if (this.airPlan < 0) return;
    this.airPlan -= dt;
    if (this.airDouble && this.airPlan < 0.15 && f.velY < 2) { f.intent.jump = true; this.airDouble = false; this.airPlan += 0.3; }
    if (this.airPlan <= 0 && ready.length) {
      f.intent.skill = ready[Math.floor(Math.random() * ready.length)];
      this.airPlan = -1;
    }
  }
  private hopCd = 0;

  /** Platform-fight movement. Returns true when busy recovering (skip everything else). */
  private platform(f: Fighter, o: Fighter, dt: number): boolean {
    const st = f.stage!;
    const main = st.plats[0];
    const p = f.root.position;
    const press = () => { this.jumpPulse = !this.jumpPulse; f.intent.jump = this.jumpPulse; };
    // Recovery: off stage or below it -> drift home and jump.
    const offstage = p.x < main.x0 + 0.2 || p.x > main.x1 - 0.2 || p.y < main.y - 0.2;
    if (!f.onGround && offstage && (f.state === S.IDLE || f.state === S.ATTACK)) {
      f.intent.move.set(Math.sign(-p.x) || 1, 0, 0);
      if (f.velY < 1.5) {
        press();
        if (p.y < main.y - 1.5) for (const k of ["x", "z", "c"]) if (f.attacks[k].self_jump > 0 && f.cooldowns[k] <= 0) { f.intent.skill = k; break; }
      }
      return true;
    }
    if (o.out) { f.intent.move.set(Math.sign(-p.x) * (Math.abs(p.x) > 3 ? 1 : 0), 0, 0); return true; }
    const dx = o.root.position.x - p.x;
    const dy = o.root.position.y - p.y;
    const ranged = RANGED.has(f.kit);
    const want = ranged ? 5 : f.kit === "greatsword" ? 1.6 : 1.25;
    let mx = 0;
    if (Math.abs(dx) > want + 0.4) mx = Math.sign(dx);
    else if (ranged && Math.abs(dx) < 3) mx = -Math.sign(dx);
    // Don't walk off the main stage edge on purpose.
    if (f.onGround && mx && (p.x + mx * 0.6 < main.x0 + 0.6 || p.x + mx * 0.6 > main.x1 - 0.6)) mx = 0;
    f.intent.move.set(mx, 0, 0);
    this.hopCd -= dt;
    if (f.onGround && dy > 1.6 && Math.abs(dx) < 4 && this.hopCd <= 0) { press(); this.hopCd = 0.6; }
    else if (!f.onGround && dy > 1.2 && f.velY < 0.5 && this.hopCd <= 0) { press(); this.hopCd = 0.6; }
    else if (f.onGround && dy < -1.2 && p.y > 0.5 && Math.abs(dx) < 4) f.intent.move.z = 1; // drop through
    // Hop over incoming projectiles.
    for (const pr of this.threats.projectiles()) {
      if (pr.target !== f || this.seen.has(pr.id)) continue;
      this.seen.add(pr.id);
      if (Math.random() < this.p.jump + 0.15 && f.onGround) this.jumpWait = Math.max(f.chest().distanceTo(pr.pos) / Math.max(pr.vel.length(), 0.1) - 0.25, 0);
    }
    return false;
  }

  private schedule(wait: number, dur: number) {
    if (this.blockHold > 0 || this.blockWait >= 0) return;
    this.blockWait = wait;
    this.blockDur = dur;
  }

  private react(f: Fighter, o: Fighter) {
    if (o.state === S.ATTACK && o.atkPhase === 0 && o.atk?.type === "melee" && o.swingSerial !== this.seenSwing) {
      this.seenSwing = o.swingSerial;
      if (f.state === S.HITSTUN || f.state === S.STAGGER) return;
      const tth = o.atk.wind - o.stateT;
      const r = Math.random();
      const bc = this.p.block * (o.atk.heavy ? 0.75 : 1);
      if (r < this.p.parry) this.schedule(Math.max(tth - 0.07, 0), 0.3);
      else if (r < this.p.parry + bc) this.schedule(rand(this.p.react[0], this.p.react[1]) * 0.6, tth + 0.45);
      else if (r < this.p.parry + bc + 0.15) this.trySkill(f, "z", true);
    }
    const charging = o.state === S.CHARGE;
    if (charging && !this.seenCharge) {
      this.seenCharge = true;
      if (Math.random() < 0.45) this.schedule(rand(this.p.react[0], this.p.react[1]), 1.4);
    } else if (!charging) this.seenCharge = false;
  }

  private dodge(f: Fighter) {
    for (const p of this.threats.projectiles()) {
      if (p.target !== f || this.seen.has(p.id)) continue;
      this.seen.add(p.id);
      const eta = f.chest().distanceTo(p.pos) / Math.max(p.vel.length(), 0.1);
      const r = Math.random();
      if (r < this.p.jump && f.onGround) this.jumpWait = Math.max(eta - 0.28, 0);
      else if (r < this.p.jump + this.p.block) this.schedule(Math.min(Math.max(eta - 0.2, 0), this.p.react[1]), eta + 0.2);
    }
    for (const m of this.threats.strikes()) {
      if (m.target !== f || this.seen.has(m.id)) continue;
      this.seen.add(m.id);
      const eta = m.land - this.threats.now();
      if (Math.random() < 0.3 + this.p.jump) { this.sideT = Math.min(Math.max(eta, 0.3), 0.8); this.sideSign = Math.random() < 0.5 ? 1 : -1; }
      else if (Math.random() < 0.5) this.jumpWait = Math.max(eta - 0.3, 0);
    }
    if (this.seen.size > 300) this.seen.clear();
  }

  private position(f: Fighter, o: Fighter, dt: number) {
    const d = o.root.position.clone().sub(f.root.position);
    d.y = 0;
    const dist = d.length();
    d.divideScalar(Math.max(dist, 0.001));
    const side = new THREE.Vector3(-d.z, 0, d.x);
    if (this.sideT > 0) { this.sideT -= dt; f.intent.move.copy(side).multiplyScalar(this.sideSign); return; }
    if (RANGED.has(f.kit)) {
      this.strafeT -= dt;
      if (this.strafeT <= 0) { this.strafeT = rand(0.6, 1.4); this.sideSign = [-1, 0, 1][Math.floor(Math.random() * 3)]; }
      if (dist < 3.2) f.intent.move.copy(d).negate().addScaledVector(side, this.sideSign * 0.5);
      else if (dist > 6.5) f.intent.move.copy(d);
      else if (this.sideSign) f.intent.move.copy(side).multiplyScalar(this.sideSign * 0.6);
    }
  }

  private trySkill(f: Fighter, key: string, force = false) {
    if (f.cooldowns[key] > 0) return false;
    if (!force && Math.random() > 0.5) return false;
    f.intent.skill = key;
    return true;
  }

  private offense(f: Fighter, o: Fighter, dt: number) {
    if (f.state !== S.IDLE || this.queue.length || this.hold > 0 || this.blockHold > 0) return;
    const dist = f.root.position.distanceTo(o.root.position);
    if (f.stage && Math.abs(o.root.position.y - f.root.position.y) > 1.4 && !RANGED.has(f.kit)) return;
    const ranged = RANGED.has(f.kit);
    const reach = ranged ? 9 : f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks" ? 1.7 : f.kit === "greatsword" ? 2.3 : 1.9;
    this.skillCd -= dt;
    if (this.skillCd <= 0) {
      this.skillCd = rand(this.p.skill[0], this.p.skill[1]);
      for (const key of ["c", "x", "z"].sort(() => Math.random() - 0.5)) {
        const a = f.attacks[key];
        let ok = true;
        if (a.type === "melee") ok = dist < a.reach + 1.5;
        else if (a.type === "strike") ok = a.at !== "self" || dist < a.radius;
        else if (a.type === "buff") ok = a.mode === "counter" ? dist < 2.5 : f.hp < f.maxHp * 0.7;
        else if (a.type === "blink") ok = (a.mode === "behind" && dist < 6) || (a.mode === "back" && dist < 2.5);
        if (ok && this.trySkill(f, key)) return;
      }
    }
    if (dist > reach) return;
    if (o.state === S.STAGGER) this.thinkCd = 0;
    this.thinkCd -= dt;
    if (this.thinkCd > 0) return;
    this.thinkCd = (f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks" ? rand(0.5, 1.1) : rand(0.7, 1.6)) * this.p.think;
    const heavy = o.state === S.STAGGER ? 0.5 : o.state === S.BLOCK ? 0.45 : 0.22;
    if (Math.random() < heavy) this.queue.push([0, HOLD_T + rand(0.3, 0.65)]);
    else {
      const maxHits = Math.min(this.p.combo, Object.keys(f.attacks).filter((k) => k.startsWith("l")).length);
      const hits = 1 + Math.floor(Math.random() * maxHits);
      for (let i = 0; i < hits; i++) this.queue.push([i === 0 ? 0 : 0.14, 0.06]);
    }
  }
}
