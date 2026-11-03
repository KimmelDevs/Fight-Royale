// The running match. Owns the renderer, scene, entities and rules for both modes:
//   duel     - 1v1, vs CPU (offline) or vs a friend (online)
//   survival - 1-4 players vs roguelike waves of mobs, a boss every 5 waves, perks between waves
// Networking is host-authoritative: the host (or offline player) simulates everything and
// streams snapshots + effect events; guests send inputs and render puppets.
import * as THREE from "three";
import * as M from "./mat";
import { Fx } from "./fx";
import { Fighter, S, type Entity, type Brain } from "./fighter";
import { Mob, waveRoster, MOB_TYPES, type MobHost } from "./mobs";
import { AiBrain, LEVELS, type Threats } from "./ai";
import { CHARACTERS } from "./roster";
import * as Kits from "./kits";
import type { Attack } from "./kits";
import { Input, type RawInput } from "./input";
import type { Net, Msg } from "./net";

export interface PlayerSlot { peer: string; name: string; char: number }
export interface GameConfig {
  mode: "duel" | "survival";
  role: "offline" | "host" | "client";
  players: PlayerSlot[];
  localPeer: string;
  cpuChar?: number;
  difficulty?: number;
}

export interface Perk { id: string; name: string; desc: string }
export const PERKS: Perk[] = [
  { id: "power", name: "Sharpened Edge", desc: "+20% damage" },
  { id: "vital", name: "Vitality", desc: "+25% max HP, fully healed" },
  { id: "leech", name: "Vampiric", desc: "Heal 6% of damage you deal" },
  { id: "haste", name: "Quick Hands", desc: "Skills recharge 20% faster" },
  { id: "crit", name: "Keen Eye", desc: "+12% critical hit chance" },
  { id: "swift", name: "Fleet Foot", desc: "+15% move speed" },
  { id: "guard", name: "Iron Will", desc: "+40% guard, faster parries" },
  { id: "heal", name: "Second Wind", desc: "Heal to full right now" },
];

export type UiEvent =
  | { type: "banner"; text: string; color: string; sub?: string; hold?: number }
  | { type: "perks"; options: Perk[] }
  | { type: "over"; text: string; sub: string; color: string };

const v3 = (a: any) => a instanceof THREE.Vector3 ? a : new THREE.Vector3(a.x ?? a[0], a.y ?? a[1], a.z ?? a[2]);
const DUEL_RADIUS = 7;
const SURVIVAL_RADIUS = 11;

class LocalBrain implements Brain {
  constructor(private game: Game) {}
  think(f: Fighter) { applyRaw(f, this.game.localInput); }
}

class RemoteBrain implements Brain {
  last: RawInput = { attack: false, block: false, jump: false, skill: "", mx: 0, mz: 0 };
  skills: string[] = [];
  think(f: Fighter) {
    applyRaw(f, this.last);
    f.intent.skill = this.skills.shift() ?? "";
  }
}

function applyRaw(f: Fighter, r: RawInput) {
  f.intent.attack = r.attack;
  f.intent.block = r.block;
  f.intent.jump = r.jump;
  if (r.skill) f.intent.skill = r.skill;
  f.intent.move.set(r.mx, 0, r.mz);
}

/** Flying spell or thrown weapon. Host projectiles hit; guest copies are visual only. */
class Projectile {
  id: number;
  group = new THREE.Group();
  spin = new THREE.Group();
  vel: THREE.Vector3;
  life = 2.2;
  hitIds = new Set<number>();
  done = false;
  constructor(id: number, public shooter: Entity | null, public team: number, public atk: Attack | null,
    public power: number, pos: THREE.Vector3, vel: THREE.Vector3, public style: string, element: string,
    public size: number, public color: string, public pierce: boolean, public visualOnly: boolean, public target: Entity | null) {
    this.id = id;
    this.vel = vel;
    this.group.position.copy(pos);
    this.group.lookAt(pos.clone().add(vel));
    this.group.add(this.spin);
    buildProjectile(this.spin, style, element, size, color);
  }
  get pos() { return this.group.position; }
}

function buildProjectile(g: THREE.Group, style: string, element: string, size: number, color: string) {
  const glow = new THREE.MeshBasicMaterial({ color });
  if (style === "arrow") {
    const shaft = new THREE.Mesh(new THREE.BoxGeometry(0.02 * size, 0.02 * size, 0.7 * size), new THREE.MeshBasicMaterial({ color: "#f4e6c0" }));
    g.add(shaft);
    const head = new THREE.Mesh(new THREE.ConeGeometry(0.04 * size, 0.14 * size, 4), glow);
    head.rotation.x = Math.PI / 2;
    head.position.z = 0.4 * size;
    g.add(head);
    const fl = new THREE.Mesh(new THREE.BoxGeometry(0.08 * size, 0.005, 0.12 * size), M.additive(color, 0.8));
    fl.position.z = -0.3 * size;
    g.add(fl);
    return;
  }
  if (style === "shuriken") {
    const st = new THREE.MeshBasicMaterial({ color: "#dcd6f0" });
    for (let i = 0; i < 2; i++) {
      const b = new THREE.Mesh(new THREE.BoxGeometry(0.34 * size, 0.012, 0.06 * size), st);
      b.rotation.y = (i * Math.PI) / 2;
      g.add(b);
    }
    g.add(new THREE.Mesh(new THREE.SphereGeometry(0.035 * size, 8, 4), glow));
    return;
  }
  if (style === "wave" || style === "shock") {
    const m = M.additive(color, 0.85);
    const arc = new THREE.Mesh(new THREE.TorusGeometry(0.5 * size, 0.05 * size, 6, 24, Math.PI * 0.9), m);
    arc.rotation.set(Math.PI / 2, 0, Math.PI * 0.05 + (style === "shock" ? 0 : 0));
    if (style === "shock") arc.rotation.set(0, 0, Math.PI * 0.55);
    g.add(arc);
    const core = new THREE.Mesh(new THREE.SphereGeometry(0.08 * size, 10, 6), M.additive("#ffffff", 0.8));
    core.scale.set(style === "shock" ? 1 : 5, style === "shock" ? 5 : 0.4, 0.6);
    g.add(core);
    return;
  }
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.1 * size, 12, 8), new THREE.MeshBasicMaterial({ color: element === "electric" ? "#fff6a0" : color }));
  if (element === "electric") core.scale.set(0.7, 0.7, 2.6);
  g.add(core);
  g.add(new THREE.Mesh(new THREE.SphereGeometry(0.17 * size, 14, 8), M.water(color, 0.55, 1.6)));
}

export class Game implements MobHost {
  cfg: GameConfig;
  net: Net | null;
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(50, 1, 0.1, 300);
  fx: Fx;
  input = new Input();
  localInput: RawInput = { attack: false, block: false, jump: false, skill: "", mx: 0, mz: 0 };
  onEvent: (e: UiEvent) => void = () => {};

  fighters: Fighter[] = [];
  mobs: Mob[] = [];
  entities = new Map<number, Entity>();
  projectiles: Projectile[] = [];
  local: Fighter | null = null;

  private sun = new THREE.DirectionalLight(0xffffff, 1.9);
  private timers: { t: number; fn: () => void }[] = [];
  private time = 0;
  private timeScale = 1;
  private stopUntil = 0;
  private stopScale = 1;
  private trauma = 0;
  private shakeT = 0;
  private nextId = 1;
  private events: any[] = [];
  private snapT = 0;
  private sendT = 0;
  private raf = 0;
  private worker: Worker | null = null;
  private lastRaf = 0;
  private last = 0;
  private remoteBrains = new Map<string, RemoteBrain>();
  private strikeMarks: { target: any; land: number; id: number }[] = [];
  private round = 0;
  roundOver = false;
  canRestart = false;

  // Survival state.
  wave = 0;
  kills = 0;
  phase = "intro";
  private toSpawn: { type: string; elite: boolean }[] = [];
  private spawnT = 0;
  private perkWait = new Map<string, Perk[]>();
  private perkDeadline = 0;

  constructor(canvas: HTMLCanvasElement, overlay: HTMLElement, cfg: GameConfig, net: Net | null) {
    this.cfg = cfg;
    this.net = net;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.fx = new Fx(this.scene, this.camera, overlay);
    this.buildWorld();
    this.input.attach(canvas);
    if (net) net.onMessage = (from, msg) => this.onNet(from, msg);
    this.resize();
    window.addEventListener("resize", this.resize);
    (window as any).__game = this; // handy for debugging from the console
  }

  private resize = () => {
    const c = this.renderer.domElement;
    const w = c.clientWidth || window.innerWidth, h = c.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  };

  private buildWorld() {
    const sky = new THREE.Mesh(new THREE.SphereGeometry(200, 32, 16), new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false,
      uniforms: { top: { value: new THREE.Color("#6aa6ea") }, horizon: { value: new THREE.Color("#d8eeff") } },
      vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
      fragmentShader: "uniform vec3 top; uniform vec3 horizon; varying vec3 vP; void main(){ gl_FragColor = vec4(mix(horizon, top, smoothstep(0.0, 0.5, vP.y)), 1.0); }",
    }));
    this.scene.add(sky);
    this.scene.fog = new THREE.Fog("#d8eeff", 30, 110);
    this.scene.add(new THREE.HemisphereLight("#e6f0ff", "#b8d0b0", 1.2));
    this.sun.position.copy(M.LIGHT_DIR).multiplyScalar(30);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    const sc = this.sun.shadow.camera as THREE.OrthographicCamera;
    sc.left = -16; sc.right = 16; sc.top = 16; sc.bottom = -16; sc.near = 1; sc.far = 80;
    this.scene.add(this.sun, this.sun.target);

    const cvs = document.createElement("canvas");
    cvs.width = cvs.height = 128;
    const g = cvs.getContext("2d")!;
    g.fillStyle = "#a7c9a1"; g.fillRect(0, 0, 128, 128);
    g.fillStyle = "#97b994"; g.fillRect(0, 0, 128, 3); g.fillRect(0, 0, 3, 128);
    const tex = new THREE.CanvasTexture(cvs);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(100, 100);
    tex.anisotropy = 8;
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshLambertMaterial({ map: tex }));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);
    const r = this.cfg.mode === "survival" ? SURVIVAL_RADIUS : DUEL_RADIUS;
    const ring = new THREE.Mesh(new THREE.TorusGeometry(r + 0.45, 0.07, 6, 128).rotateX(Math.PI / 2), new THREE.MeshBasicMaterial({ color: "#e6c26e" }));
    ring.scale.y = 0.2;
    this.scene.add(ring);
  }

  // --- lifecycle ---------------------------------------------------------------------
  start() {
    if (this.cfg.role !== "client") this.startRound();
    this.last = performance.now();
    const loop = (now: number) => {
      this.raf = requestAnimationFrame(loop);
      this.lastRaf = performance.now();
      this.frame(now, true);
    };
    this.raf = requestAnimationFrame(loop);
    // Browsers pause requestAnimationFrame in background tabs (sometimes without setting
    // document.hidden). Whenever frames stop arriving, a worker timer keeps the
    // host's simulation (and everyone's match) running while its tab is hidden.
    if (this.cfg.role === "host") {
      const src = "setInterval(() => postMessage(0), 33);";
      this.worker = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
      this.worker.onmessage = () => { const t = performance.now(); if (t - this.lastRaf > 100) this.frame(t, false); };
    }
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.worker?.terminate();
    window.removeEventListener("resize", this.resize);
    this.input.detach();
    this.fx.clear();
    this.renderer.dispose();
  }

  restart() {
    if (this.cfg.role === "client") return;
    this.startRound();
  }

  private clearAll() {
    for (const e of this.entities.values()) this.removeEntity(e, false);
    this.entities.clear();
    this.fighters = [];
    this.mobs = [];
    for (const p of this.projectiles) this.scene.remove(p.group);
    this.projectiles = [];
    this.timers = [];
    this.strikeMarks = [];
    this.fx.clear();
    this.local = null;
  }

  private startRound() {
    this.clearAll();
    this.round++;
    this.roundOver = false;
    this.canRestart = false;
    this.timeScale = 1;
    this.emit(["reset"]);
    const cfg = this.cfg;
    if (cfg.mode === "duel") {
      const a = cfg.players[0];
      const b = cfg.players[1] ?? { peer: "cpu", name: "CPU", char: cfg.cpuChar ?? 0 };
      const f1 = this.spawnFighter(a, 0, new THREE.Vector3(-2, 0, 0), Math.PI / 2);
      const f2 = this.spawnFighter(b, 1, new THREE.Vector3(2, 0, 0), -Math.PI / 2);
      f1.opponent = f2;
      f2.opponent = f1;
      if (b.peer === "cpu") f2.autoApproach = !["mage", "bow"].includes(f2.kit);
      const id = this.round;
      this.banner("READY", "#ffe9a8", "", 0.6);
      this.later(1.0, () => {
        if (id !== this.round) return;
        this.banner("FIGHT!", "#ffffff", "", 0.5);
        for (const f of [f1, f2]) f.brain = this.brainFor(f);
      });
    } else {
      cfg.players.forEach((p, i) => {
        const a = (i / Math.max(cfg.players.length, 1)) * Math.PI * 2;
        const f = this.spawnFighter(p, 0, new THREE.Vector3(Math.sin(a) * 1.5, 0, Math.cos(a) * 1.5), 0);
        f.brain = this.brainFor(f);
      });
      this.wave = 0;
      this.kills = 0;
      this.phase = "intro";
      this.later(0.8, () => this.startWave());
    }
  }

  private brainFor(f: Fighter): Brain {
    if (f.owner === "cpu") return new AiBrain(this.threats, this.cfg.difficulty ?? 1);
    if (f.owner === this.cfg.localPeer) return new LocalBrain(this);
    let b = this.remoteBrains.get(f.owner);
    if (!b) { b = new RemoteBrain(); this.remoteBrains.set(f.owner, b); }
    return b;
  }

  private spawnFighter(slot: PlayerSlot, team: number, pos: THREE.Vector3, rotY: number, id = 0): Fighter {
    const f = new Fighter(CHARACTERS[slot.char].look, slot.char);
    f.id = id || this.nextId++;
    f.team = team;
    f.owner = slot.peer;
    f.puppet = this.cfg.role === "client";
    f.arenaRadius = this.cfg.mode === "survival" ? SURVIVAL_RADIUS : DUEL_RADIUS;
    f.root.position.copy(pos);
    f.root.rotation.y = rotY;
    f.onSwing = (x) => this.onSwing(x);
    f.onKo = (x) => this.onFighterKo(x);
    f.onLanded = (x) => this.fx.ring(x.root.position, "#ffffff", 0.8, 0.25, 0.5);
    this.scene.add(f.root, f.trail.mesh);
    this.fighters.push(f);
    this.entities.set(f.id, f);
    if (slot.peer === this.cfg.localPeer) this.local = f;
    this.emit(["spawnF", f.id, slot.char, team, slot.peer, slot.name, +pos.x.toFixed(2), +pos.z.toFixed(2), rotY]);
    return f;
  }

  private spawnMob(type: string, pos: THREE.Vector3, elite: boolean, id = 0, hpMult?: number): Mob {
    const hm = hpMult ?? 1 + 0.12 * (this.wave - 1) + 0.35 * Math.max(this.cfg.players.length - 1, 0);
    const m = new Mob(type, hm, 1 + 0.06 * (this.wave - 1), elite);
    m.id = id || this.nextId++;
    m.puppet = this.cfg.role === "client";
    m.host = this;
    m.root.position.copy(pos);
    this.scene.add(m.root);
    this.mobs.push(m);
    this.entities.set(m.id, m);
    this.emit(["spawnM", m.id, type, elite ? 1 : 0, +hm.toFixed(3), +pos.x.toFixed(2), +pos.z.toFixed(2)]);
    return m;
  }

  private removeEntity(e: Entity, emit = true) {
    this.scene.remove(e.root);
    if (e instanceof Fighter) this.scene.remove(e.trail.mesh);
    this.entities.delete(e.id);
    if (emit) this.emit(["despawn", e.id]);
  }

  // --- frame ---------------------------------------------------------------------------
  private frame(now: number, render: boolean) {
    const realDt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;
    if (this.stopUntil > 0 && now >= this.stopUntil) { this.stopUntil = 0; this.timeScale = 1; }
    const dt = realDt * this.timeScale;
    this.localInput = this.input.read(this.camera);
    M.timeU.value += dt;

    if (this.cfg.role === "client") {
      this.sendT -= realDt;
      if (this.sendT <= 0 || this.localInput.skill) {
        this.sendT = 1 / 30;
        this.net?.send({ t: "in", i: this.localInput });
      }
    }

    if (this.cfg.role !== "client") {
      this.time += dt;
      const due = this.timers.filter((t) => t.t <= this.time);
      this.timers = this.timers.filter((t) => t.t > this.time);
      for (const t of due) t.fn();
      this.retarget();
      if (this.cfg.mode === "survival") this.updateSurvival(dt);
    }
    for (const f of this.fighters) f.update(dt);
    for (const m of this.mobs) m.update(dt);
    this.updateProjectiles(dt);
    if (this.cfg.role !== "client") {
      for (const m of [...this.mobs]) {
        if (m.dead && m.deathT > 0.5) { this.removeEntity(m); this.mobs = this.mobs.filter((x) => x !== m); }
      }
    } else {
      for (const m of [...this.mobs]) {
        if (m.dead && m.deathT > 0.5) { this.scene.remove(m.root); this.entities.delete(m.id); this.mobs = this.mobs.filter((x) => x !== m); }
      }
    }
    this.updateCamera(realDt);
    this.fx.update(dt, realDt, this.renderer.domElement.clientWidth, this.renderer.domElement.clientHeight);

    if (this.cfg.role === "host") {
      this.snapT -= realDt;
      if (this.snapT <= 0) {
        this.snapT = 1 / 20;
        this.net?.broadcast({
          t: "snap", f: this.fighters.map((f) => f.snapshot()), m: this.mobs.map((m) => m.snapshot()), e: this.events,
          s: [this.wave, this.kills, this.phase],
        });
        this.events = [];
      }
    }
    if (!render) return;
    M.updateLight(this.camera);
    this.renderer.render(this.scene, this.camera);
  }

  private retarget() {
    for (const f of this.fighters) {
      if (this.cfg.mode === "duel") continue;
      let best: Entity | null = null, bd = 14;
      for (const m of this.mobs) {
        if (m.dead) continue;
        const d = m.root.position.distanceTo(f.root.position);
        if (d < bd) { bd = d; best = m; }
      }
      f.opponent = best;
    }
  }

  nearestPlayer(from: THREE.Vector3): Entity | null {
    let best: Entity | null = null, bd = 1e9;
    for (const f of this.fighters) {
      if (f.isDown()) continue;
      const d = f.root.position.distanceTo(from);
      if (d < bd) { bd = d; best = f; }
    }
    return best;
  }

  private enemiesOf(e: Entity): Entity[] {
    return [...this.entities.values()].filter((o) => o.team !== e.team && !o.isDown());
  }

  later(delay: number, fn: () => void) { this.timers.push({ t: this.time + delay, fn }); }

  /** Threat feed for the duel AI: incoming projectiles and pending ground strikes. */
  private threats: Threats = {
    projectiles: () => this.projectiles.filter((p) => !p.visualOnly).map((p) => ({ target: p.target, pos: p.pos, vel: p.vel, id: p.id })),
    strikes: () => this.strikeMarks,
    now: () => this.time,
  };

  // --- effects (replicated to guests) -------------------------------------------------
  private emit(ev: any[]) { if (this.cfg.role === "host") this.events.push(ev); }

  fxp(name: string, ...args: any[]) {
    this.runFx(name, args);
    this.emit(["fx", name, args]);
  }

  private runFx(name: string, a: any[]) {
    const fx = this.fx;
    switch (name) {
      case "sparks": fx.sparks(v3(a[0]), a[1], a[2], a[3], a[4] ? v3(a[4]) : null); break;
      case "splash": fx.splash(v3(a[0]), a[1], a[2], a[3]); break;
      case "flash": fx.flash(v3(a[0]), a[1], a[2], a[3], a[4]); break;
      case "ring": fx.ring(v3(a[0]), a[1], a[2], a[3], a[4]); break;
      case "wave": fx.waveRing(v3(a[0]), a[1], a[2]); break;
      case "geyser": fx.geyser(v3(a[0]), a[1], a[2]); break;
      case "lightning": fx.lightning(v3(a[0]), a[1]); break;
      case "tele": fx.telegraph(v3(a[0]), a[1], a[2], a[3]); break;
      case "explosion": fx.explosion(v3(a[0]), a[1], a[2]); break;
      case "meteor": fx.meteor(v3(a[0]), a[1], a[2]); break;
      case "smoke": fx.smoke(v3(a[0]), a[1]); break;
      case "orb": fx.bigOrb(v3(a[0]), a[1]); break;
      case "slashes": fx.slashes(v3(a[0]), a[1]); break;
      case "arrows": fx.arrowRain(v3(a[0]), a[1], a[2], a[3]); break;
      case "embers": fx.embers(v3(a[0]), a[1], a[2]); break;
      case "num": fx.number(v3(a[0]), a[1], a[2], a[3]); break;
      case "bubble": { const e = this.entities.get(a[0]); if (e) fx.bubble(e.root, a[1]); break; }
    }
  }

  add_trauma(x: number) { this.trauma = Math.min(this.trauma + x, 1); }

  /** Freeze-frame on impact (host / offline only; guests just render snapshots). */
  hitStop(dur: number, scale = 0.03) {
    if (this.cfg.role === "client") return;
    this.timeScale = scale;
    this.stopUntil = performance.now() + dur * 1000;
  }

  banner(text: string, color: string, sub = "", hold = 0) {
    this.onEvent({ type: "banner", text, color, sub, hold });
    this.emit(["banner", text, color, sub, hold]);
  }

  // --- attack resolution ----------------------------------------------------------------
  private onSwing(f: Fighter) {
    const a = f.atk!;
    switch (a.type) {
      case "projectile": this.fireProjectiles(f, a); break;
      case "strike": this.runStrike(f, a, f.atkPower); break;
      case "buff": this.applyBuff(f, a); break;
      case "blink": this.blink(f, a); break;
      default: this.melee(f, a);
    }
  }

  private melee(f: Fighter, a: Attack) {
    const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    for (const d of this.enemiesOf(f)) {
      const to = d.root.position.clone().sub(f.root.position);
      const dy = Math.abs(to.y);
      to.y = 0;
      const dist = to.length();
      const dir = to.clone().divideScalar(Math.max(dist, 0.001));
      if (d instanceof Fighter && this.cfg.mode === "duel" && d.state === S.ATTACK && d.atk?.type === "melee" &&
        (d.atkPhase === 1 || (d.atkPhase === 0 && d.atk.wind - d.stateT <= 0.08)) && dist <= a.reach + 0.3 && dy < 0.8) {
        this.clash(f, d, f.root.position.clone().addScaledVector(dir, Math.min(dist * 0.5, 0.8)).add(new THREE.Vector3(0, 1.15, 0)));
        return;
      }
      if (dist - d.radius + 0.35 > a.reach || dy > 1.3 || (dist > 0.6 && dir.dot(fwd) < 0.15)) continue;
      const hitPos = d.chest().addScaledVector(dir, -0.15);
      this.applyHit(f, d, a, f.atkPower, hitPos, dir, false);
    }
  }

  private fireProjectiles(f: Fighter, a: Attack) {
    const origin = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const tgt = f.opponent;
    const aim = tgt ? tgt.chest().sub(origin) : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    if (!tgt) aim.y = 0;
    const base = aim.normalize();
    for (let i = 0; i < a.count; i++) {
      const off = a.count === 1 ? 0 : -a.spread + (2 * a.spread * i) / (a.count - 1);
      this.spawnProjectile(f, f.team, a, f.atkPower, origin, base.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), off).multiplyScalar(a.speed),
        a.style, a.element, a.size, f.look.glow, a.pierce, tgt);
    }
    this.fxp("flash", origin, f.look.glow, 0.25, 0.1, 0.7);
  }

  private spawnProjectile(shooter: Entity | null, team: number, a: Attack, power: number, pos: THREE.Vector3, vel: THREE.Vector3,
    style: string, element: string, size: number, color: string, pierce: boolean, target: Entity | null) {
    const p = new Projectile(this.nextId++, shooter, team, a, power, pos, vel, style, element, size, color, pierce, false, target);
    this.scene.add(p.group);
    this.projectiles.push(p);
    this.emit(["proj", p.id, style, element, size, color, pos, vel]);
  }

  private updateProjectiles(dt: number) {
    for (const p of this.projectiles) {
      if (p.done) continue;
      p.pos.addScaledVector(p.vel, dt);
      p.life -= dt;
      if (p.style === "shuriken") p.spin.rotation.y += dt * 30;
      else if (p.style === "bolt") p.spin.rotation.z += dt * 12;
      if (!p.visualOnly && p.atk) {
        for (const e of this.enemiesOfTeam(p.team)) {
          if (p.hitIds.has(e.id)) continue;
          if (p.pos.distanceTo(e.chest()) < 0.3 * p.size + e.radius) {
            p.hitIds.add(e.id);
            const dir = p.vel.clone().setY(0).normalize();
            this.impactFx(p.atk, p.pos.clone(), p.color, 0.7);
            this.applyHit(p.shooter, e, p.atk, p.power, p.pos.clone(), dir, true);
            if (!p.pierce) { p.done = true; break; }
          }
        }
      }
      const flat = Math.hypot(p.pos.x, p.pos.z);
      if (p.life <= 0 || p.pos.y < 0.05 || flat > 16) {
        if (!p.visualOnly) this.fxp("sparks", p.pos.clone(), p.color, 8, 3);
        p.done = true;
      }
    }
    for (const p of this.projectiles) if (p.done) {
      this.scene.remove(p.group);
      if (!p.visualOnly) this.emit(["projEnd", p.id]);
    }
    this.projectiles = this.projectiles.filter((p) => !p.done);
  }

  private enemiesOfTeam(team: number): Entity[] {
    return [...this.entities.values()].filter((o) => o.team !== team && !o.isDown());
  }

  /** Area attack(s) at the target (or around the caster) after a telegraphed delay. */
  private runStrike(f: Fighter, a: Attack, power: number) {
    const round = this.round;
    const color = f.look.glow;
    const one = (i: number) => {
      if (round !== this.round || f.isDown()) return;
      const src: Entity = a.at === "self" || !f.opponent ? f : f.opponent;
      const center = src.root.position.clone().setY(0);
      const wait = i === 0 ? a.delay : a.interval;
      const mark = { target: f.opponent, land: this.time + wait, id: this.nextId++ };
      this.strikeMarks.push(mark);
      this.fxp("tele", center, color, a.radius, wait);
      if (a.style === "meteor") this.fxp("meteor", center, color, wait);
      if (a.style === "requiem") this.fxp("orb", center, wait);
      if (a.style === "arrows") this.fxp("arrows", center, a.radius, wait, color);
      this.later(wait, () => {
        this.strikeMarks = this.strikeMarks.filter((m) => m !== mark);
        if (round !== this.round) return;
        const at = a.at === "self" ? f.root.position.clone().setY(0) : center;
        this.impactFx(a, at, color, a.radius);
        for (const d of this.enemiesOf(f)) {
          const to = d.root.position.clone().sub(at).setY(0);
          if (to.length() <= a.radius + d.radius * 0.5 && !d.airborne()) {
            const dir = to.length() > 0.05 ? to.normalize() : d.root.position.clone().sub(f.root.position).setY(0).normalize();
            this.applyHit(f, d, a, power, d.chest(), dir, true);
          } else if (d instanceof Fighter && to.length() <= a.radius + 1) {
            this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.8, 0)), "DODGE", "#c9d3e6", 0.7);
          }
        }
        if (i + 1 < a.repeat) one(i + 1);
      });
    };
    one(0);
  }

  private impactFx(a: Attack, pos: THREE.Vector3, color: string, radius: number) {
    const g = pos.clone().setY(0);
    switch (a.style) {
      case "explosion":
      case "meteor":
        this.fxp("explosion", g, color, radius);
        this.add_trauma(a.style === "explosion" ? 0.35 : 0.6);
        break;
      case "lightning":
        this.fxp("lightning", g, color);
        this.fxp("flash", g.clone().setY(0.4), "#fff2b0", radius * 0.6, 0.15, 0.9);
        this.fxp("sparks", g.clone().setY(0.2), color, 30, 7, [0, 1, 0]);
        this.fxp("ring", g, color, radius * 1.3, 0.3, 0.9);
        this.add_trauma(0.3);
        break;
      case "tide":
        this.fxp("wave", g, radius * 2.2, 0.6);
        for (let i = 0; i < 8; i++) { const an = (i / 8) * Math.PI * 2; this.fxp("geyser", g.clone().add(new THREE.Vector3(Math.cos(an), 0, Math.sin(an)).multiplyScalar(radius * 0.8)), 1.8, 0.03 * i); }
        this.add_trauma(0.3);
        break;
      case "requiem":
        this.fxp("wave", g, radius * 3.5, 1.0);
        this.fxp("splash", g.clone().setY(0.3), 50, 2.2);
        for (let i = 0; i < 10; i++) { const an = (i / 10) * Math.PI * 2; this.fxp("geyser", g.clone().add(new THREE.Vector3(Math.cos(an), 0, Math.sin(an)).multiplyScalar(radius)), 2.6, 0.05); }
        this.add_trauma(0.7);
        break;
      case "slam":
      case "cleave":
        this.fxp("ring", g, color, radius * 1.3, 0.35, 0.9);
        this.fxp("ring", g, "#ffffff", radius * 0.8, 0.25, 0.6);
        this.fxp("sparks", g.clone().setY(0.2), "#d8c8a8", 40, 7, [0, 1, 0]);
        this.fxp("flash", g.clone().setY(0.3), color, radius * 0.5, 0.18, 0.6);
        this.add_trauma(a.style === "cleave" ? 0.65 : 0.45);
        break;
      case "spin":
        this.fxp("ring", g.clone().setY(1.0), color, radius, 0.2, 0.9);
        this.fxp("sparks", g.clone().setY(1.0), color, 14, 6);
        break;
      case "slashes":
        this.fxp("slashes", g, color);
        this.fxp("sparks", g.clone().setY(1.0), color, 8, 5);
        break;
      case "arrows":
        this.fxp("sparks", g.clone().setY(0.2), color, 18, 4, [0, 1, 0]);
        this.fxp("ring", g, color, radius, 0.25, 0.6);
        break;
      default:
        if (a.element === "water") this.fxp("splash", pos, 18, a.size < 2 ? 1 : 2);
        else if (a.element === "fire") { this.fxp("flash", pos, "#ff9933", 0.35 * a.size, 0.14, 0.8); this.fxp("sparks", pos, color, 16, 5); }
        else if (a.element === "electric") this.fxp("sparks", pos, "#fff2a0", 20, 8);
        else this.fxp("sparks", pos, color, 14, 5);
    }
  }

  private applyBuff(f: Fighter, a: Attack) {
    if (a.mode === "ward") {
      f.wardT = a.duration;
      this.fxp("bubble", f.id, a.duration);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "WARD", "#8fe6ff", 0.9);
    } else if (a.mode === "counter") {
      f.counterT = a.duration;
      this.fxp("flash", f.chest(), f.look.glow, 0.5, 0.2, 0.6);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "COUNTER STANCE", "#ffd1da", 0.7);
    }
  }

  private blink(f: Fighter, a: Attack) {
    const from = f.root.position.clone();
    const o = f.opponent;
    const d = o ? o.root.position.clone().sub(from).setY(0).normalize() : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    let to = from.clone().addScaledVector(d, -3);
    if (a.mode === "behind" && o) to = o.root.position.clone().addScaledVector(d, 1.3);
    this.fxp("smoke", from, f.look.glow);
    f.teleport(to);
    this.fxp("smoke", f.root.position.clone(), f.look.glow);
  }

  private applyHit(attacker: Entity | null, d: Entity, a: Attack, power: number, hitPos: THREE.Vector3, dir: THREE.Vector3, ranged: boolean) {
    const result = d.receiveHit(attacker, a, power);
    const glow = attacker instanceof Fighter ? attacker.look.glow : attacker instanceof Mob ? attacker.def.color : "#ffffff";
    const heavy = a.heavy || a.id === "l3";
    const shieldPos = d instanceof Fighter ? d.model.shieldNode.getWorldPosition(new THREE.Vector3()) : hitPos;
    switch (result) {
      case "hit": case "crit": case "ko": {
        const crit = d.lastCrit;
        this.fxp("sparks", hitPos, glow, heavy ? 30 : 18, heavy ? 8 : 6, dir);
        this.fxp("flash", hitPos, glow, heavy ? 0.45 : 0.3, 0.14, 0.8);
        if (a.heavy) this.fxp("ring", hitPos, glow, 2.2, 0.35, 0.9);
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), `${Math.round(d.lastDamage)}${crit ? "!" : ""}`,
          d.team === 0 && this.cfg.mode === "survival" ? "#ff7b7b" : crit ? "#ffb347" : "#ffffff", crit ? 1.5 : 1);
        if (attacker instanceof Fighter && attacker.lifesteal > 0) attacker.heal(d.lastDamage * attacker.lifesteal);
        const big = this.cfg.mode === "duel" || attacker instanceof Mob ? 1 : 0.5;
        this.add_trauma((a.heavy ? 0.5 : heavy ? 0.3 : 0.18) * big);
        this.hitStop(a.heavy ? 0.11 : heavy ? 0.07 : 0.045);
        if (result === "ko" && d instanceof Mob) {
          this.kills++;
          this.fxp("smoke", d.root.position.clone(), d.def.color);
        }
        break;
      }
      case "blocked":
        this.fxp("sparks", shieldPos, "#ffd27a", 16, 5, dir.clone().negate().add(new THREE.Vector3(0, 0.3, 0)));
        this.fxp("flash", shieldPos, "#ffd980", 0.35, 0.1, 0.6);
        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.4, 0)), "BLOCK", "#c9d3e6", 0.7);
        if (!ranged && attacker instanceof Fighter) attacker.model.recoil = 0.6;
        this.add_trauma(0.14);
        this.hitStop(0.04);
        break;
      case "parry":
        if (!ranged && attacker instanceof Fighter) attacker.stagger(0.95);
        else if (!ranged && attacker instanceof Mob) attacker.receiveHit(d, { ...a, dmg: 0, knock: 4 }, 0);
        this.fxp("sparks", shieldPos, "#aee9ff", 40, 9);
        this.fxp("flash", shieldPos, "#b3f2ff", 0.5, 0.2, 0.9);
        this.fxp("ring", shieldPos, "#b3f2ff", 1.6, 0.35, 0.9);
        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "PARRY!", "#8fe6ff", 1.4);
        this.add_trauma(0.4);
        this.hitStop(0.35, 0.3);
        break;
      case "counter": {
        const df = d as Fighter;
        this.fxp("num", df.chest().add(new THREE.Vector3(0, 0.6, 0)), "COUNTER!", "#ff9aa8", 1.4);
        this.fxp("slashes", (attacker ?? df).root.position.clone(), df.look.glow);
        if (attacker) {
          const counter = { ...df.attacks.heavy, dmg: 180, heavy: true, stun: 0.8 } as Attack;
          this.applyHit(df, attacker, counter, df.dmgMult, attacker.chest(), dir.clone().negate(), false);
        }
        break;
      }
      case "guard_break":
        this.fxp("sparks", hitPos, "#ffb347", 40, 9);
        this.fxp("flash", hitPos, "#ffb34d", 0.5, 0.2, 0.9);
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.55, 0)), "GUARD BREAK", "#ff8a50", 1.2);
        this.add_trauma(0.55);
        this.hitStop(0.12);
        break;
      case "warded":
        this.fxp("flash", hitPos, "#80d9ff", 0.5, 0.15, 0.7);
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "ABSORBED", "#8fe6ff", 0.8);
        break;
      case "miss":
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "MISS", "#c9d3e6", 0.8);
        break;
    }
  }

  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {
    a.clashRecoil();
    b.clashRecoil();
    this.fxp("sparks", pos, "#fff2c0", 50, 10);
    this.fxp("sparks", pos, a.look.glow, 16, 7);
    this.fxp("sparks", pos, b.look.glow, 16, 7);
    this.fxp("flash", pos, "#fff2cc", 0.55, 0.18, 0.95);
    this.fxp("ring", pos, "#ffe699", 3, 0.45, 0.9);
    this.fxp("num", pos.clone().add(new THREE.Vector3(0, 0.45, 0)), "CLASH!", "#ffe08a", 1.3);
    this.add_trauma(0.45);
    this.hitStop(0.13);
  }

  // --- mob attacks (MobHost) -------------------------------------------------------------
  private mobAttack(m: Mob, dmg: number, knock: number, stun: number, heavy = false): Attack {
    return { ...Kits.attacks("knight", "").l1, id: "mob", dmg, guard: dmg * 0.35, knock, stun, heavy, element: "" };
  }

  mobHit(m: Mob, t: Entity, dmg: number, knock: number, stun: number) {
    const dir = t.root.position.clone().sub(m.root.position).setY(0).normalize();
    this.applyHit(m, t, this.mobAttack(m, dmg, knock, stun), 1, t.chest().addScaledVector(dir, -0.2), dir, false);
  }

  mobShoot(m: Mob, t: Entity, spread = 0) {
    const d = m.def;
    const origin = m.chest();
    const base = t.chest().sub(origin).normalize();
    const count = spread > 0 ? 3 : 1;
    const a = { ...this.mobAttack(m, m.dmg, 1.5, 0.3), type: "projectile", style: d.style ?? "bolt", element: m.type === "imp" ? "fire" : "" };
    for (let i = 0; i < count; i++) {
      const off = count === 1 ? 0 : -spread + (2 * spread * i) / (count - 1);
      const color = m.type === "imp" ? "#ff7a33" : m.type === "golem" ? "#c9a27a" : "#d9d2ff";
      this.spawnProjectile(m, 1, a, 1, origin, base.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), off).multiplyScalar(d.projSpeed ?? 12),
        m.type === "golem" ? "bolt" : a.style, a.element, m.type === "golem" ? 2.2 : 1, color, false, t);
    }
  }

  mobStrike(m: Mob, center: THREE.Vector3, radius: number, delay: number, dmg: number, style: string) {
    const c = center.clone().setY(0);
    const color = style === "meteor" ? "#ff7a33" : "#ff4d4d";
    this.fxp("tele", c, color, radius, delay);
    if (style === "meteor") this.fxp("meteor", c, color, delay);
    const mark = { target: null, land: this.time + delay, id: this.nextId++ };
    this.strikeMarks.push(mark);
    const round = this.round;
    this.later(delay, () => {
      this.strikeMarks = this.strikeMarks.filter((x) => x !== mark);
      if (round !== this.round || m.dead) return;
      const a = { ...this.mobAttack(m, dmg, 6, 0.6, true), style: style === "meteor" ? "meteor" : "slam" };
      this.impactFx(a, c, color, radius);
      for (const f of this.fighters) {
        if (f.isDown()) continue;
        const to = f.root.position.clone().sub(c).setY(0);
        if (to.length() <= radius && !f.airborne()) this.applyHit(m, f, a, 1, f.chest(), to.length() > 0.05 ? to.normalize() : new THREE.Vector3(1, 0, 0), true);
      }
    });
  }

  mobSummon(m: Mob, type: string, count: number) {
    for (let i = 0; i < count; i++) {
      const an = (i / count) * Math.PI * 2;
      const p = m.root.position.clone().add(new THREE.Vector3(Math.cos(an) * 2.5, 0, Math.sin(an) * 2.5));
      this.fxp("smoke", p, MOB_TYPES[type].color);
      this.spawnMob(type, p, false);
    }
  }

  // --- rounds -----------------------------------------------------------------------------
  private onFighterKo(f: Fighter) {
    if (this.cfg.mode === "duel") {
      if (this.roundOver) return;
      this.roundOver = true;
      const winner = this.fighters.find((x) => x !== f)!;
      for (const x of this.fighters) x.brain = null;
      this.add_trauma(0.8);
      this.hitStop(0.9, 0.25);
      this.later(0.4, () => {
        winner.win();
        const iWon = winner.owner === this.cfg.localPeer;
        const name = winner.look.name;
        const text = this.cfg.role === "offline" ? (iWon ? "VICTORY" : "DEFEAT") : `${name.toUpperCase()} WINS`;
        this.over(text, this.cfg.role === "client" ? "" : "Press R or click Rematch", iWon || this.cfg.role !== "offline" ? "#ffe08a" : "#ff7b7b");
        this.canRestart = true;
      });
    } else {
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "DOWN!", "#ff7b7b", 1.1);
      if (this.fighters.every((x) => x.isDown())) {
        this.phase = "over";
        this.later(1.0, () => {
          this.over("GAME OVER", `Reached wave ${this.wave}  -  ${this.kills} kills`, "#ff7b7b");
          this.canRestart = true;
        });
      }
    }
  }

  private over(text: string, sub: string, color: string) {
    this.onEvent({ type: "over", text, sub, color });
    this.emit(["over", text, sub, color]);
  }

  private startWave() {
    this.wave++;
    this.toSpawn = waveRoster(this.wave);
    this.phase = "fight";
    this.spawnT = 1.2;
    const boss = this.wave % 5 === 0;
    this.banner(boss ? "BOSS WAVE" : `WAVE ${this.wave}`, boss ? "#ff7b7b" : "#ffe9a8", boss ? "The Ancient Golem awakens" : `${this.toSpawn.length} enemies`, 1.2);
  }

  private updateSurvival(dt: number) {
    if (this.phase === "fight") {
      this.spawnT -= dt;
      const alive = this.mobs.filter((m) => !m.dead).length;
      if (this.toSpawn.length && this.spawnT <= 0 && alive < 10 + this.cfg.players.length * 2) {
        this.spawnT = 0.7;
        const s = this.toSpawn.shift()!;
        const an = Math.random() * Math.PI * 2;
        const p = new THREE.Vector3(Math.cos(an) * 9.5, 0, Math.sin(an) * 9.5);
        this.fxp("smoke", p, MOB_TYPES[s.type].color);
        this.fxp("ring", p, MOB_TYPES[s.type].color, 1.2, 0.4, 0.8);
        this.spawnMob(s.type, p, s.elite);
      }
      if (!this.toSpawn.length && alive === 0 && this.mobs.length === 0) {
        this.phase = "perks";
        this.banner("WAVE CLEAR", "#9dff9a", "Choose an upgrade", 1.0);
        for (const f of this.fighters) {
          if (f.isDown()) f.revive(0.5);
          else f.heal(f.maxHp * 0.25);
        }
        this.perkWait.clear();
        for (const f of this.fighters) {
          const opts = [...PERKS].sort(() => Math.random() - 0.5).slice(0, 3);
          this.perkWait.set(f.owner, opts);
          if (f.owner === this.cfg.localPeer) this.onEvent({ type: "perks", options: opts });
          else this.net?.sendTo(f.owner, { t: "perks", o: opts });
        }
        this.perkDeadline = this.time + 25;
      }
    } else if (this.phase === "perks") {
      if (this.perkWait.size === 0 || this.time > this.perkDeadline) {
        for (const [peer, opts] of this.perkWait) this.applyPerk(peer, opts[0]);
        this.perkWait.clear();
        this.phase = "intro";
        this.later(1.0, () => this.startWave());
      }
    }
  }

  choosePerk(i: number) {
    if (this.cfg.role === "client") { this.net?.send({ t: "perk", i }); return; }
    const opts = this.perkWait.get(this.cfg.localPeer);
    if (opts) { this.applyPerk(this.cfg.localPeer, opts[i] ?? opts[0]); this.perkWait.delete(this.cfg.localPeer); }
  }

  private applyPerk(peer: string, p: Perk) {
    const f = this.fighters.find((x) => x.owner === peer);
    if (!f) return;
    switch (p.id) {
      case "power": f.dmgMult *= 1.2; break;
      case "vital": f.maxHp *= 1.25; f.hp = f.maxHp; break;
      case "leech": f.lifesteal += 0.06; break;
      case "haste": f.cdMult *= 0.8; break;
      case "crit": f.critChance += 0.12; break;
      case "swift": f.moveSpeed *= 1.15; break;
      case "guard": f.maxGuard *= 1.4; f.guard = f.maxGuard; f.parryWindow += 0.04; break;
      case "heal": f.hp = f.maxHp; break;
    }
    this.fxp("ring", f.root.position.clone(), "#9dff9a", 1.4, 0.4, 0.9);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), p.name, "#9dff9a", 0.9);
  }

  // --- networking -------------------------------------------------------------------------
  private onNet(from: string, msg: Msg) {
    if (this.cfg.role === "host") {
      if (msg.t === "in") {
        let b = this.remoteBrains.get(from);
        if (!b) { b = new RemoteBrain(); this.remoteBrains.set(from, b); }
        b.last = msg.i;
        if (msg.i.skill) b.skills.push(msg.i.skill);
      } else if (msg.t === "perk") {
        const opts = this.perkWait.get(from);
        if (opts) { this.applyPerk(from, opts[msg.i] ?? opts[0]); this.perkWait.delete(from); }
      }
      return;
    }
    if (msg.t === "snap") {
      for (const ev of msg.e) this.applyEvent(ev);
      for (const s of msg.f) (this.entities.get(s[0]) as Fighter | undefined)?.applySnapshot?.(s);
      for (const s of msg.m) (this.entities.get(s[0]) as Mob | undefined)?.applySnapshot?.(s);
      [this.wave, this.kills, this.phase] = msg.s;
    } else if (msg.t === "perks") {
      this.onEvent({ type: "perks", options: msg.o });
    }
  }

  private applyEvent(ev: any[]) {
    switch (ev[0]) {
      case "reset": this.clearAll(); break;
      case "spawnF": {
        const f = this.spawnFighter({ peer: ev[4], name: ev[5], char: ev[2] }, ev[3], new THREE.Vector3(ev[6], 0, ev[7]), ev[8], ev[1]);
        f.puppet = true;
        break;
      }
      case "spawnM": {
        const m = this.spawnMob(ev[2], new THREE.Vector3(ev[5], 0, ev[6]), ev[3] === 1, ev[1], ev[4]);
        m.puppet = true;
        break;
      }
      case "despawn": {
        const e = this.entities.get(ev[1]);
        if (e) {
          this.removeEntity(e, false);
          this.fighters = this.fighters.filter((x) => x !== e);
          this.mobs = this.mobs.filter((x) => x !== e);
        }
        break;
      }
      case "fx": this.runFx(ev[1], ev[2]); break;
      case "proj": {
        const p = new Projectile(ev[1], null, 0, null, 0, v3(ev[6]), v3(ev[7]), ev[2], ev[3], ev[4], ev[5], true, true, null);
        this.scene.add(p.group);
        this.projectiles.push(p);
        break;
      }
      case "projEnd": { const p = this.projectiles.find((x) => x.id === ev[1]); if (p) p.done = true; break; }
      case "banner": this.onEvent({ type: "banner", text: ev[1], color: ev[2], sub: ev[3], hold: ev[4] }); break;
      case "over": this.onEvent({ type: "over", text: ev[1], sub: ev[2], color: ev[3] }); break;
    }
  }

  // --- camera -------------------------------------------------------------------------------
  private updateCamera(dt: number) {
    const cam = this.camera;
    let goal: THREE.Vector3, look: THREE.Vector3;
    const me = this.local ?? this.fighters[0];
    if (!me) { cam.position.set(0, 6, 10); cam.lookAt(0, 1, 0); return; }
    if (this.cfg.mode === "duel" && this.fighters.length >= 2) {
      const other = this.fighters.find((f) => f !== me)!;
      const mid = me.root.position.clone().add(other.root.position).multiplyScalar(0.5);
      const d = other.root.position.clone().sub(me.root.position).setY(0);
      const sep = d.length();
      d.divideScalar(Math.max(sep, 0.01));
      const side = new THREE.Vector3(-d.z, 0, d.x);
      const lift = mid.y * 0.5;
      mid.y = 0;
      goal = mid.clone().addScaledVector(side, 3.4 + sep * 0.6).addScaledVector(d, -0.5).add(new THREE.Vector3(0, 1.45 + lift, 0));
      look = mid.clone().add(new THREE.Vector3(0, 1.0 + lift, 0));
      // Turn bodies toward the camera so faces read from the side.
      for (const f of this.fighters) {
        const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        const toCam = cam.position.clone().sub(f.root.position).setY(0).normalize();
        const ang = Math.atan2(fwd.z * toCam.x - fwd.x * toCam.z, fwd.dot(toCam));
        f.viewBias = Math.max(-0.85, Math.min(0.85, ang * 0.6));
      }
    } else {
      const p = me.root.position.clone().setY(0);
      goal = p.clone().add(new THREE.Vector3(0, 7.5, 8));
      look = p.clone().add(new THREE.Vector3(0, 1.0, 0));
    }
    const k = 1 - Math.exp(-5 * dt);
    if (cam.position.lengthSq() === 0) cam.position.copy(goal);
    cam.position.lerp(goal, k);
    cam.lookAt(look);
    this.trauma = Math.max(this.trauma - 1.4 * dt, 0);
    const sh = this.trauma * this.trauma;
    this.shakeT += dt * 32;
    cam.position.x += 0.22 * sh * Math.sin(this.shakeT * 1.7);
    cam.position.y += 0.16 * sh * Math.sin(this.shakeT * 2.3);
    cam.rotateZ(0.04 * sh * Math.sin(this.shakeT * 1.1));
    this.sun.target.position.copy(look);
    this.sun.position.copy(look).addScaledVector(M.LIGHT_DIR, 30);
  }

  // --- HUD feed -----------------------------------------------------------------------------
  hud() {
    const me = this.local;
    const boss = this.mobs.find((m) => m.def.boss && !m.dead);
    const other = this.cfg.mode === "duel" ? this.fighters.find((f) => f !== me) : null;
    const info = (f: Fighter) => ({ name: f.look.name, hp: f.hp, maxHp: f.maxHp, guard: f.guard, maxGuard: f.maxGuard, down: f.isDown(), glow: f.look.glow });
    return {
      mode: this.cfg.mode,
      me: me ? info(me) : null,
      other: other ? { ...info(other), tag: other.owner === "cpu" ? `CPU - ${LEVELS[this.cfg.difficulty ?? 1]}` : "" } : null,
      team: this.cfg.mode === "survival" ? this.fighters.filter((f) => f !== me).map(info) : [],
      skills: me ? ["z", "x", "c"].map((k) => ({ key: k, name: me.attacks[k].name, cd: me.cooldowns[k], max: me.attacks[k].cd * me.cdMult })) : [],
      wave: this.wave, kills: this.kills, phase: this.phase,
      mobs: this.mobs.filter((m) => !m.dead).length,
      boss: boss ? { name: boss.def.name, hp: boss.hp, maxHp: boss.maxHp } : null,
      canRestart: this.canRestart && this.cfg.role !== "client",
    };
  }
}
