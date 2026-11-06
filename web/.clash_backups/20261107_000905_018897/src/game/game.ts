// MELEE_PROJECTILE_SPRINT_V1_NOV06
// EMBER_DAMAGE_RADIUS_NERF_V2_20261106
// EMBER_GROUND_HAZARD_AI_V1_NOV06
// CONTINUOUS_PARRY_AI_V4_NOV06
// CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06
// The running match. Owns the renderer, scene, entities and rules for all modes:
//   duel     - 1v1 in the 3D arena, vs CPU (offline) or vs a friend (online)
//   brawl    - 1v1 side-view platform fight (damage %, 3 stocks, blast zones), CPU or friend
//   team     - 2v2 / 3v3 / 4v4 in the 3D arena
//   survival - 1-4 players vs roguelike waves of mobs, a boss every 5 waves, perks between waves
// Networking is host-authoritative: the host (or offline player) simulates everything and
// streams snapshots + effect events; guests send inputs and render puppets.
import * as THREE from "three";
import * as M from "./mat";
import { Fx } from "./fx";
import { Fighter, S, STOCKS, RANGED_COMBO_REST, DASH_CD, type Entity, type Brain, type Stage } from "./fighter";
import { Mob, waveRoster, MOB_TYPES, type MobHost } from "./mobs";
import { AiBrain, LEVELS, type Threats } from "./ai";
import { CHARACTERS } from "./roster";
import { MOB_GOLD, WIN_GOLD } from "./economy";
import * as Kits from "./kits";
import type { Attack } from "./kits";
import { STATUS, type StatusKind } from "./status";
import { Sound, MATCH_SOUNDS } from "./sound";
import { Input, type RawInput } from "./input";
import type { Net, Msg } from "./net";

export interface PlayerSlot {
  peer: string; name: string; char: number;
  /** Which 3 of the character's 4 skills go on Z/X/C. */
  loadout?: string[];
  emblem?: { id: string; level: number };
  /** Team mode only: 0 or 1. */
  team?: number;
}
export interface GameConfig {
  mode: "duel" | "brawl" | "survival" | "team";
  role: "offline" | "host" | "client";
  players: PlayerSlot[];
  localPeer: string;
  cpuChar?: number;
  difficulty?: number;
  /** Guest who joined a match already in progress (asks the host for a full sync). */
  late?: boolean;
  /** Ranked duel: the result moves the local player's rank stars. */
  ranked?: boolean;
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
  | { type: "over"; text: string; sub: string; color: string }
  | { type: "reward"; reason: "duel" | "team" | "survival"; gold: number }
  | { type: "result"; winner: number };

const v3 = (a: any) => a instanceof THREE.Vector3 ? a : new THREE.Vector3(a.x ?? a[0], a.y ?? a[1], a.z ?? a[2]);
const DUEL_RADIUS = 7;
const SURVIVAL_RADIUS = 11;

/** The floating stage for duel and team fights: a main island plus three soft platforms. */
/** Platform Brawl is hidden from menus for now (the mode itself still works). */
export const SHOW_BRAWL = false;

export const STAGE: Stage = {
  plats: [
    { x0: -7.5, x1: 7.5, y: 0, solid: true },
    { x0: -5.6, x1: -2.4, y: 2.4, solid: false },
    { x0: 2.4, x1: 5.6, y: 2.4, solid: false },
    { x0: -1.6, x1: 1.6, y: 4.6, solid: false },
  ],
  blast: { l: -17, r: 17, b: -9, t: 15 },
  respawn: new THREE.Vector3(0, 7.5, 0),
};

class LocalBrain implements Brain {
  constructor(private game: Game) {}
  think(f: Fighter) { applyRaw(f, this.game.localInput); }
}

class RemoteBrain implements Brain {
  last: RawInput = { attack: false, block: false, jump: false, skill: "", mx: 0, mz: 0 };
  skills: Array<{ key: string; mx: number; mz: number }> = [];
  dashes: [number, number][] = [];
  think(f: Fighter) {
    applyRaw(f, { ...this.last, dx: 0, dz: 0 });
    const nextSkill = this.skills.shift();
    f.intent.skill = nextSkill?.key ?? "";
    if (nextSkill) {
      if (!f.intent.skillMove) f.intent.skillMove = new THREE.Vector3();
      f.intent.skillMove.set(nextSkill.mx, 0, nextSkill.mz);
    }
    const d = this.dashes.shift();
    if (d) f.intent.dash.set(d[0], 0, d[1]);
  }
}

function applyRaw(f: Fighter, r: RawInput) {
  f.intent.attack = r.attack;
  f.intent.block = r.block;
  f.intent.jump = r.jump;
  f.intent.sprint = !!r.sprint; // Shift + move, also relayed to online hosts
  if (r.skill) {
    f.intent.skill = r.skill;
    if (!f.intent.skillMove) f.intent.skillMove = new THREE.Vector3();
    f.intent.skillMove.set(r.mx, 0, r.mz);
  }
  f.intent.skillHeld = r.skillHeld ?? "";
  f.intent.move.set(r.mx, 0, r.mz);
  if (r.dx || r.dz) f.intent.dash.set(r.dx ?? 0, 0, r.dz ?? 0);
}

/** CPU-controlled slots: "cpu" (duel opponent) and "cpu-1", "cpu-2"... (team battles). */
export const isCpu = (peer: string) => peer === "cpu" || peer.startsWith("cpu-");

/** Flying spell or thrown weapon. Host projectiles hit; guest copies are visual only. */
class Projectile {
  id: number;
  group = new THREE.Group();
  spin = new THREE.Group();
  vel: THREE.Vector3;
  life = 2.2;
  hitIds = new Set<number>();
  done = false;
  /** Blood Hunter steering metadata. The host is authoritative. */
  age = 0;
  steering = false;
  steered = false;
  returnTo: Fighter | null = null;
  finalBlade = false;
  /** Downward pull (m/s^2) for thrown bombs; 0 = straight flight. */
  gravity = 0;
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

/** A temporary three-second ring of spinning blood scythes. */
interface BloodFestival {
  id: number; owner: Fighter | null; team: number;
  center: THREE.Vector3; radius: number; time: number; age: number;
  visual: THREE.Group; blades: THREE.Group[];
  captured: Set<number>; contact: Map<number, number>;
}

/** Purely rendered blade ring: enemy confinement is performed by the host, not meshes. */
function makeBloodFestivalVisual(radius: number): { visual: THREE.Group; blades: THREE.Group[] } {
  const visual = new THREE.Group();
  const red = new THREE.MeshBasicMaterial({ color: "#fc4465", side: THREE.DoubleSide, transparent: true, opacity: 0.92, depthWrite: false });
  const steel = new THREE.MeshBasicMaterial({ color: "#ffe1e9", side: THREE.DoubleSide, transparent: true, opacity: 0.94, depthWrite: false });
  const ringMat = new THREE.MeshBasicMaterial({ color: "#b81943", transparent: true, opacity: 0.78, depthWrite: false });
  const floor = new THREE.Mesh(new THREE.RingGeometry(radius - 0.09, radius + 0.09, 72), ringMat);
  floor.rotation.x = -Math.PI / 2; floor.position.y = 0.045; visual.add(floor);
  const inner = new THREE.Mesh(new THREE.TorusGeometry(radius - 0.38, 0.025, 5, 72), red);
  inner.rotation.x = Math.PI / 2; inner.position.y = 0.09; visual.add(inner);
  const bladeShape = new THREE.Shape();
  bladeShape.moveTo(-0.22, 0.03);
  bladeShape.bezierCurveTo(-0.12, 0.53, 0.42, 0.77, 0.60, 0.61);
  bladeShape.quadraticCurveTo(0.34, 0.64, 0.19, 0.35);
  bladeShape.quadraticCurveTo(0.02, 0.21, -0.22, 0.03);
  const bladeGeo = new THREE.ShapeGeometry(bladeShape, 16);
  const edgeShape = new THREE.Shape();
  edgeShape.moveTo(0.19, 0.35);
  edgeShape.quadraticCurveTo(0.39, 0.69, 0.60, 0.61);
  edgeShape.quadraticCurveTo(0.41, 0.55, 0.19, 0.35);
  const edgeGeo = new THREE.ShapeGeometry(edgeShape, 10);
  const blades: THREE.Group[] = [];
  for (let i = 0; i < 14; i++) {
    const b = new THREE.Group();
    const blade = new THREE.Mesh(bladeGeo, red);
    const edge = new THREE.Mesh(edgeGeo, steel);
    edge.position.z = 0.008;
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.017, 0.020, 0.58, 6), ringMat);
    pole.position.set(-0.18, -0.19, 0);
    pole.rotation.z = -0.25;
    b.add(pole, blade, edge);
    b.scale.setScalar(1.1);
    visual.add(b); blades.push(b);
  }
  return { visual, blades };
}

const BOMB_GRAVITY = 16;

/** A mine or powder keg on the field. */
interface Trap {
  id: number; kind: "mine" | "barrel"; owner: Fighter | null; team: number; atk: Attack; power: number;
  pos: THREE.Vector3; mesh: THREE.Group; arm: number; life: number; t: number;
}

function buildTrap(kind: string, color: string): THREE.Group {
  const g = new THREE.Group();
  if (kind === "mine") {
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.28, 0.07, 16), new THREE.MeshLambertMaterial({ color: "#3a3d44" }));
    disc.position.y = 0.035;
    g.add(disc);
    const light = new THREE.Mesh(new THREE.SphereGeometry(0.05, 10, 6), new THREE.MeshBasicMaterial({ color: "#ff3b3b" }));
    light.position.y = 0.09;
    light.name = "light";
    g.add(light);
  } else {
    const wood = new THREE.MeshLambertMaterial({ color: "#8a5a32" });
    const band = new THREE.MeshLambertMaterial({ color: "#5a5a66" });
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.95, 20), wood);
    body.position.y = 0.475;
    g.add(body);
    for (const y of [0.12, 0.475, 0.83]) {
      const r = new THREE.Mesh(new THREE.TorusGeometry(0.43, 0.025, 6, 24), band);
      r.rotation.x = Math.PI / 2;
      r.position.y = y;
      g.add(r);
    }
    const fuse = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.22, 6), new THREE.MeshLambertMaterial({ color: "#c9a46a" }));
    fuse.position.set(0.1, 1.05, 0);
    fuse.rotation.z = -0.4;
    g.add(fuse);
    const spark = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 6), new THREE.MeshBasicMaterial({ color }));
    spark.position.set(0.16, 1.15, 0);
    spark.name = "light";
    g.add(spark);
  }
  return g;
}

/** Mines blink faster once armed; a keg's fuse spark flickers. */
function animateTrap(t: Trap, dt: number) {
  const light = t.mesh.getObjectByName("light");
  if (!light) return;
  const rate = t.kind === "mine" ? (t.arm > 0 ? 2 : 6) : 14;
  light.visible = Math.sin(t.t * rate * Math.PI) > (t.kind === "mine" ? 0 : -0.6);
  if (t.kind === "barrel") light.scale.setScalar(0.8 + Math.random() * 0.5);
}

function buildProjectile(g: THREE.Group, style: string, element: string, size: number, color: string) {
  const glow = new THREE.MeshBasicMaterial({ color });
  if (style === "bomb") {
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.11 * size, 12, 8), new THREE.MeshBasicMaterial({ color: "#2a2a32" }));
    g.add(body);
    const spark = new THREE.Mesh(new THREE.SphereGeometry(0.045 * size, 8, 6), glow);
    spark.position.y = 0.13 * size;
    g.add(spark);
    return;
  }
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
  if (style === "bloodsickle" || style === "bloodcrescent") {
    // Curved, cutting blade silhouette. The projectile is a separate effect mesh, not the hand weapon.
    const shape = new THREE.Shape();
    shape.moveTo(-0.31 * size, -0.15 * size);
    shape.quadraticCurveTo(-0.14 * size, 0.45 * size, 0.40 * size, 0.26 * size);
    shape.lineTo(0.49 * size, 0.12 * size);
    shape.quadraticCurveTo(0.14 * size, 0.30 * size, -0.31 * size, -0.15 * size);
    const geo = new THREE.ShapeGeometry(shape, 14);
    const blade = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: "#f4bdc7", side: THREE.DoubleSide }));
    blade.rotation.x = -0.1;
    g.add(blade);
    const arc = new THREE.Mesh(new THREE.TorusGeometry(0.33 * size, 0.013 * size, 4, 22, Math.PI * 1.2), glow);
    arc.rotation.z = -0.5;
    g.add(arc);
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
  /** Mines and powder kegs on the field (host simulates; guests only show them). */
  traps: Trap[] = [];
  /** Blood Festival arenas. Created on host and replicated as visual events on clients. */
  private bloodFestivals: BloodFestival[] = [];
  private kaizenGuardContacts = new WeakMap<Fighter, WeakMap<Entity, number>>();
  // ASTER_EMBER_LATEST_20261106: persistent Ember ground-fire visual + host damage timer.
  private emberPatches: { ownerId: number; pos: THREE.Vector3; radius: number; ttl: number;
    tick: number; visual: THREE.Group }[] = [];
  private emberBeams: { visual: THREE.Group; ttl: number; max: number }[] = [];
  /** Animated sparks flowing from consumed ground fire/burns into the staff. */
  private emberGather: { mesh: THREE.Mesh; from: THREE.Vector3; ownerId: number;
    progress: number; duration: number; offset: number }[] = [];
  private emberCharge: { ownerId: number; mesh: THREE.Mesh; ttl: number; max: number }[] = [];
  local: Fighter | null = null;

  private sun = new THREE.DirectionalLight(0xffffff, 1.9);
  /** Brawl mode is a side-view platform fight. */
  readonly plat: boolean;
  // CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: optional tagged timers can be shifted by parry.
  private timers: { t: number; fn: () => void; owner?: Fighter; serial?: number }[] = [];
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
  /** Best of three (first to two): round wins for team/player 0 and 1. */
  private matchWins: [number, number] = [0, 0];
  roundOver = false;
  canRestart = false;
  /** Pause menu open: offline matches freeze; online matches keep running but ignore your input. */
  paused = false;

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
    this.plat = cfg.mode === "brawl";
    Sound.preload(MATCH_SOUNDS);
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
    if (this.plat) { this.buildStage(); return; }
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshLambertMaterial({ map: tex }));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);
    const r = this.cfg.mode === "survival" ? SURVIVAL_RADIUS : DUEL_RADIUS;
    const ring = new THREE.Mesh(new THREE.TorusGeometry(r + 0.45, 0.07, 6, 128).rotateX(Math.PI / 2), new THREE.MeshBasicMaterial({ color: "#e6c26e" }));
    ring.scale.y = 0.2;
    this.scene.add(ring);
  }

  /** Floating island stage with soft platforms, far islands and clouds behind it. */
  private buildStage() {
    const grass = M.toon("#8fd16a", { shade: "#6fae8a" });
    const dirt = M.toon("#b07a52", { shade: "#8a6a8a" });
    const rock = M.toon("#8c8496", { shade: "#6a6688" });
    const trim = M.toon("#e6c26e", { rim: 0.6 });
    const add = (geo: THREE.BufferGeometry, mat: M.MatPair, pos: [number, number, number], shadow = true) => {
      const m = new THREE.Mesh(geo, mat.fill);
      m.position.set(...pos);
      m.receiveShadow = true;
      m.castShadow = shadow;
      if (mat.outline) m.add(new THREE.Mesh(geo, mat.outline));
      this.scene.add(m);
      return m;
    };
    const main = STAGE.plats[0];
    const w = main.x1 - main.x0;
    add(new THREE.BoxGeometry(w, 0.35, 4.2), grass, [0, -0.175, 0]);
    add(new THREE.BoxGeometry(w - 0.2, 0.9, 4), dirt, [0, -0.8, 0]);
    // Rocky underside tapering to a point.
    const under = new THREE.ConeGeometry(w * 0.48, 4.2, 7, 1);
    under.rotateX(Math.PI);
    under.scale(1, 1, 0.32);
    add(under, rock, [0, -3.2, 0]);
    for (const x of [main.x0 + 0.15, main.x1 - 0.15]) add(new THREE.BoxGeometry(0.3, 0.12, 4.25), trim, [x, 0.0, 0], false);
    for (const p of STAGE.plats.slice(1)) {
      const pw = p.x1 - p.x0;
      add(new THREE.BoxGeometry(pw, 0.16, 1.6), M.toon("#f2e6c8", { shade: "#b8a8c8" }), [(p.x0 + p.x1) / 2, p.y - 0.08, 0]);
      add(new THREE.BoxGeometry(pw, 0.06, 1.62), trim, [(p.x0 + p.x1) / 2, p.y - 0.19, 0], false);
    }
    // Distant islands and clouds.
    const far = M.toon("#9cc8a8", { outline: false, shade: "#8ab0c8" });
    const farRock = M.toon("#a8a8c0", { outline: false, shade: "#9aa0c8" });
    for (const [x, y, z, s] of [[-26, -2, -30, 4], [22, 3, -36, 5], [-8, 8, -45, 3], [34, -6, -28, 3]]) {
      add(new THREE.CylinderGeometry(s, s * 0.9, 0.8, 9), far, [x, y, z], false);
      add(new THREE.ConeGeometry(s * 0.9, s * 1.6, 9).rotateX(Math.PI), farRock, [x, y - s * 0.8 - 0.4, z], false);
    }
    const cloud = new THREE.MeshBasicMaterial({ color: "#ffffff", transparent: true, opacity: 0.85 });
    for (let i = 0; i < 14; i++) {
      const c = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8), cloud);
      c.scale.set(3 + Math.random() * 4, 1 + Math.random(), 1.5);
      c.position.set(-40 + i * 6 + Math.random() * 3, -10 + Math.random() * 6, -20 - Math.random() * 15);
      this.scene.add(c);
    }
    this.scene.fog = new THREE.Fog("#d8eeff", 40, 140);
  }

  // --- lifecycle ---------------------------------------------------------------------
  start() {
    if (this.cfg.role !== "client") this.startRound();
    else if (this.cfg.late) this.net?.send({ t: "synced" });
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
    // Rematch is a fresh best-of-three series, not another round of the old match.
    this.matchWins = [0, 0];
    this.emit(["roundScore", 0, 0]);
    this.startRound();
  }

  private clearAll() {
    for (const e of this.entities.values()) this.removeEntity(e, false);
    this.entities.clear();
    this.fighters = [];
    this.mobs = [];
    for (const p of this.projectiles) this.scene.remove(p.group);
    this.projectiles = [];
    for (const t of this.traps) this.scene.remove(t.mesh);
    this.traps = [];
    for (const festival of this.bloodFestivals) this.scene.remove(festival.visual);
    this.bloodFestivals = [];
    for (const p of this.emberPatches) this.scene.remove(p.visual);
    this.emberPatches = [];
    for (const b of this.emberBeams) this.scene.remove(b.visual);
    this.emberBeams = [];
    for (const g of this.emberGather) this.scene.remove(g.mesh);
    this.emberGather = [];
    for (const o of this.emberCharge) this.scene.remove(o.mesh);
    this.emberCharge = [];
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
    if (cfg.mode === "duel" || cfg.mode === "brawl") {
      const a = cfg.players[0];
      const b = cfg.players[1] ?? { peer: "cpu", name: "CPU", char: cfg.cpuChar ?? 0 };
      const sx = this.plat ? 3 : 2;
      const f1 = this.spawnFighter(a, 0, new THREE.Vector3(-sx, 0, 0), Math.PI / 2);
      const f2 = this.spawnFighter(b, 1, new THREE.Vector3(sx, 0, 0), -Math.PI / 2);
      if (b.peer === "cpu" && !this.plat) f2.autoApproach = !["mage", "bow", "bomb"].includes(f2.kit);
      f1.opponent = f2;
      f2.opponent = f1;

      const id = this.round;
      this.whenModelsReady(() => {
        this.banner("READY", "#ffe9a8", "", 0.6);
        this.later(1.0, () => {
          if (id !== this.round) return;
          this.banner("FIGHT!", "#ffffff", "", 0.5);
          for (const f of [f1, f2]) f.brain = this.brainFor(f);
        });
      });
    } else if (cfg.mode === "team") {
      // Two lines facing each other across the arena.
      const counts = [0, 0];
      const spawned: Fighter[] = [];
      cfg.players.forEach((p, i) => {
        const team = p.team ?? i % 2;
        const k = counts[team]++;
        const z = (k - 1.5) * 1.8;
        const f = this.spawnFighter(p, team, new THREE.Vector3(team === 0 ? -5 : 5, 0, z), team === 0 ? Math.PI / 2 : -Math.PI / 2);
        if (isCpu(p.peer)) f.autoApproach = !["mage", "bow", "bomb"].includes(f.kit);
        spawned.push(f);
      });
      const id = this.round;
      this.whenModelsReady(() => {
        this.banner("READY", "#ffe9a8", `${counts[0]} vs ${counts[1]}`, 0.6);
        this.later(1.0, () => {
          if (id !== this.round) return;
          this.banner("FIGHT!", "#ffffff", "", 0.5);
          for (const f of spawned) f.brain = this.brainFor(f);
        });
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

  /** Runs `fn` once every fighter's 3D model is showing (shows LOADING if that takes a bit). */
  private whenModelsReady(fn: () => void) {
    const id = this.round;
    let done = false;
    const t = setTimeout(() => { if (!done && id === this.round) this.banner("LOADING", "#c9d3e6", "Getting the fighters ready", 30); }, 250);
    Promise.all(this.fighters.map((f) => f.model.ready)).then(() => {
      done = true;
      clearTimeout(t);
      if (id === this.round) fn();
    });
  }

  /**
   * Light-element blades shed glowing motes: a stream while swinging, an occasional soft
   * sparkle at rest. Purely visual, so every peer runs it locally (no network events).
   */
  private moteT = new Map<Fighter, number>();
  private statusT = new Map<Entity, number>();
  private statusLabelAt = new Map<Entity, number>();

  /** Particles on anyone with an active status (runs on every machine from the synced bitmask). */
  private statusFx(dt: number) {
    for (const e of [...this.fighters, ...this.mobs] as (Fighter | Mob)[]) {
      const kinds = e.status.kinds();
      if (!kinds.length || e.isDown() || !e.root.visible) { this.statusT.delete(e); continue; }
      let t = (this.statusT.get(e) ?? 0) - dt;
      if (t <= 0) {
        t = 0.1;
        const c = e.chest();
        const feet = e.root.position.clone().add(new THREE.Vector3(0, 0.15, 0));
        const jitter = () => new THREE.Vector3((Math.random() - 0.5) * 0.5, (Math.random() - 0.5) * 0.6, (Math.random() - 0.5) * 0.5);
        for (const k of kinds) {
          const col = STATUS[k].color;
          if (k === "burn") this.fx.embers(c.clone().add(jitter()), col, 3);
          else if (k === "poison") this.fx.motes(c.clone().add(jitter()), col, 2);
          else if (k === "bleed") this.fx.embers(c.clone().add(jitter()), col, 2);
          else if (k === "paralyze") this.fx.sparks(c.clone().add(jitter()), col, 3, 3);
          else if (k === "slow") this.fx.motes(feet.clone().add(jitter().setY(0)), col, 2);
          else if (k === "weaken") this.fx.motes(c.clone().add(jitter()), col, 1);
        }
      }
      this.statusT.set(e, t);
    }
  }

  /** Host: show damage-over-time ticks and credit kills made by them. */
  private drainDots() {
    for (const e of [...this.fighters, ...this.mobs] as (Fighter | Mob)[]) {
      if (!e.dots.length) continue;
      e.dots.forEach((d, i) => {
        this.fxp("num", e.chest().add(new THREE.Vector3((Math.random() - 0.5) * 0.5, 0.25, 0)), `${Math.round(d.dmg)}`, STATUS[d.kind].color, 0.75);
        if (e instanceof Mob && e.dead && i === e.dots.length - 1) this.creditMobKill(d.src instanceof Fighter ? d.src : null, e);
      });
      e.dots.length = 0;
    }
  }

  private creditMobKill(attacker: Fighter | null, d: Mob) {
    this.kills++;
    this.snd("mob_die", 0.4);
    if (attacker) {
      const g = (MOB_GOLD[d.type] ?? 2) * (d.elite ? 2 : 1);
      this.earned.set(attacker.owner, (this.earned.get(attacker.owner) ?? 0) + g);
      if (attacker.owner === this.cfg.localPeer) this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.9, 0)), `+${g} gold`, "#ffd34d", 0.8);
    }
    this.fxp("smoke", d.root.position.clone(), d.def.color);
  }
  private bladeLight(dt: number) {
    for (const f of this.fighters) {
      if (f.look.element !== "light" || f.out || f.isDown() || !f.root.visible || !f.model.visible) continue;
      let t = (this.moteT.get(f) ?? 0) - dt;
      if (t <= 0) {
        const base = f.model.bladeBase.getWorldPosition(new THREE.Vector3());
        const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
        const at = base.lerp(tip, 0.3 + Math.random() * 0.7);
        const swinging = f.trail.emitting;
        this.fx.motes(at, Math.random() < 0.6 ? "#fff3c4" : f.look.glow, swinging ? 4 : 2);
        t = swinging ? 0.025 : 0.1 + Math.random() * 0.08;
      }
      this.moteT.set(f, t);
    }
  }

  private brainFor(f: Fighter): Brain {
    if (isCpu(f.owner)) return new AiBrain(this.threats, this.cfg.difficulty ?? 1);
    if (f.owner === this.cfg.localPeer) return new LocalBrain(this);
    let b = this.remoteBrains.get(f.owner);
    if (!b) { b = new RemoteBrain(); this.remoteBrains.set(f.owner, b); }
    return b;
  }

  private spawnFighter(slot: PlayerSlot, team: number, pos: THREE.Vector3, rotY: number, id = 0): Fighter {
    const f = new Fighter(CHARACTERS[slot.char].look, slot.char, slot.loadout, slot.emblem);
    f.id = id || this.nextId++;
    f.team = team;
    f.owner = slot.peer;
    f.puppet = this.cfg.role === "client";
    f.arenaRadius = this.cfg.mode === "survival" ? SURVIVAL_RADIUS : DUEL_RADIUS;
    if (this.plat) {
      f.stage = STAGE;
      f.stocks = STOCKS;
      f.facing = pos.x < 0 ? 1 : -1;
      f.onBlast = (x) => this.onBlast(x);
    }
    f.root.position.copy(pos);
    f.root.rotation.y = rotY;
    f.onSwing = (x) => this.onSwing(x);
    f.onChainBindResolve = (x, dir, kind) => this.resolveChainBind(x, dir, kind);
    f.onKo = (x) => this.onFighterKo(x);
    f.onLanded = (x) => { this.fx.ring(x.root.position, "#ffffff", 0.8, 0.25, 0.5); this.snd("land", 0.35); };
    f.onSickleRecast = (x) => this.recastBloodSickle(x);
    f.onTrigger = (x) => {
      const t = this.traps.find((k) => k.kind === "barrel" && k.owner === x);
      if (t) { this.snd("click", 0.8); this.detonate(t); } else x.barrelOut = false;
    };
    f.onAirJump = (x) => {
      // A burst of wind under the feet: two expanding rings like a gust platform, a flash,
      // air blasting downward and motes swirling up around him.
      const feet = x.root.position.clone();
      this.snd("dash", 0.55);
      this.fxp("flash", feet, x.look.glow, 0.25, 0.15, 0.55);
      this.fxp("ring", feet, x.look.glow, 1.1, 0.22, 0.9);
      this.fxp("ring", feet.clone().add(new THREE.Vector3(0, -0.2, 0)), "#ffffff", 1.8, 0.38, 0.6);
      this.fxp("sparks", feet, x.look.glow, 22, 5, [0, -1, 0]);
      this.fxp("motes", feet.clone().add(new THREE.Vector3(0, 0.4, 0)), x.look.glow, 12);
    };
    f.onDash = (x) => {
      this.snd("dash", 0.6);
      this.fxp("smoke", x.root.position.clone(), x.look.glow);
      this.fxp("ring", x.root.position.clone().add(new THREE.Vector3(0, 0.1, 0)), x.look.glow, 1.2, 0.2, 0.7);
    };
    this.scene.add(f.root, f.trail.mesh);
    this.fighters.push(f);
    this.entities.set(f.id, f);
    if (slot.peer === this.cfg.localPeer) this.local = f;
    this.emit(["spawnF", f.id, slot.char, team, slot.peer, slot.name, +pos.x.toFixed(2), +pos.z.toFixed(2), rotY, slot.loadout ?? null, slot.emblem ?? null]);
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
    const realDt = Math.max(0, Math.min((now - this.last) / 1000, 0.05)); // never negative
    this.last = now;
    if (this.stopUntil > 0 && now >= this.stopUntil) { this.stopUntil = 0; this.timeScale = 1; }
    const frozen = this.paused && this.cfg.role === "offline";
    const dt = frozen ? 0 : realDt * this.timeScale;
    this.localInput = this.input.read(this.camera);
    if (this.paused) this.localInput = { attack: false, block: false, jump: false, skill: "", mx: 0, mz: 0 };
    if (frozen) { if (render) { M.updateLight(this.camera); this.renderer.render(this.scene, this.camera); } return; }
    M.timeU.value += dt;

    if (this.cfg.role === "client") {
      this.sendT -= realDt;
      if (this.sendT <= 0 || this.localInput.skill || this.localInput.dx || this.localInput.dz) {
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
    if (this.cfg.role !== "client") this.updateKaizenSpinGuard();
    this.bladeLight(dt);
    for (const m of this.mobs) m.update(dt);
    this.statusFx(dt);
    this.updateProjectiles(dt);
    this.updateTraps(dt);
    this.updateBloodFestivals(dt);
    this.updateEmberFire(dt);
    if (this.cfg.role !== "client") {
      this.drainDots();
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


  /** KAIZEN_WEAPON_V5: close-range spinning guard, host-authoritative. */
  private updateKaizenSpinGuard() {
    for (const f of this.fighters) {
      if (f.kit !== "chainblade" || f.state !== S.BLOCK || f.guard <= 0 ||
          f.isDown() || !f.root.visible || f.chainBindT > 0 ||
          (f.chainBoundBy && f.chainBoundBy.chainBindT > 0)) continue;
      let cooldowns = this.kaizenGuardContacts.get(f);
      if (!cooldowns) {
        cooldowns = new WeakMap<Entity, number>();
        this.kaizenGuardContacts.set(f, cooldowns);
      }
      for (const enemy of this.enemiesOf(f)) {
        if (!enemy.root.visible || enemy.isDown()) continue;
        const delta = enemy.root.position.clone().sub(f.root.position);
        if (Math.abs(delta.y) > 1.05) continue;
        delta.y = 0;
        if (delta.length() > 0.92 + enemy.radius) continue;
        if (this.time < (cooldowns.get(enemy) ?? -Infinity)) continue;
        cooldowns.set(enemy, this.time + 0.45); // limited damage; no rapid hitlock
        const dir = delta.lengthSq() > 0.001 ? delta.normalize() :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        const attack: Attack = {
          ...f.attacks.l1,
          id: "kaizen_guard_spin", style: "kaizen_guard_spin", type: "melee",
          dmg: 16, guard: 9, knock: 0.35, stun: 0.05, heavy: false,
          no_parry: true, effect: "", effect_t: 0, effect_p: 0,
        };
        // Damage is never automatic through a normal block. HP is deducted only
        // if the standard hit pipeline returns a hit; guard break still works.
        const outcome = this.applyHit(f, enemy, attack, 1, enemy.chest(), dir, false);
        if (outcome === "hit" || outcome === "crit" || outcome === "ko")
          this.fxp("slashes", enemy.chest(), "#e8667c");
      }
    }
  }

  private retarget() {
    for (const f of this.fighters) {
      if (this.isDuel()) continue;
      let best: Entity | null = null, bd = this.cfg.mode === "team" ? 1e9 : 14;
      const foes: Entity[] = this.cfg.mode === "team" ? this.fighters.filter((o) => o.team !== f.team) : this.mobs;
      for (const m of foes) {
        if (m.isDown()) continue;
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
  /** Follow-up hits keep their owner/serial so parry can delay the ENTIRE remaining sequence. */
  private laterCombo(f: Fighter, delay: number, fn: () => void) {
    this.timers.push({ t: this.time + delay + f.comboPauseT, fn, owner: f, serial: f.swingSerial });
  }
  private delayComboFollowups(f: Fighter, delay: number) {
    for (const timer of this.timers) {
      if (timer.owner === f && timer.serial === f.swingSerial) timer.t += delay;
    }
  }

  /** Threat feed for the duel AI: incoming projectiles and pending ground strikes. */
  private threats: Threats = {
    projectiles: () => this.projectiles.filter((p) => !p.visualOnly).map((p) => ({ target: p.target, pos: p.pos, vel: p.vel, id: p.id })),
    strikes: () => this.strikeMarks,
    // Give the CPU real upcoming per-hit timestamps (not just a single combo telegraph).
    // The animation is still authoritative: no hit/parry outcomes are fabricated.
    comboHits: (attacker: Fighter) => this.timers
      .filter(t => t.owner === attacker && t.serial === attacker.swingSerial && t.t > this.time)
      .map(t => t.t).sort((a, b) => a - b),
    // Enemy burning ground is a navigational hazard for CPUs, not a blockable hit.
    // Same authoritative data drives fire damage, visuals, and AI avoidance.
    firePatches: (f: Fighter) => this.emberPatches
      .filter(p => {
        const owner = this.entities.get(p.ownerId);
        return owner instanceof Fighter && !owner.isDown() &&
          owner.team !== f.team && p.ttl > 0.15;
      })
      .map(p => ({ pos: p.pos, radius: p.radius })),
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
      case "snd": Sound.play(a[0], a[1] ?? 1); return;
      case "lightning": Sound.play("thunder", 0.8); break;
      case "explosion": Sound.play("explosion", 0.8); break;
      case "meteor": Sound.play("meteor", 0.9); break;
      case "rocks": if ((a[1] ?? 0) >= 16) Sound.play("rocks", 0.55); break;
      case "slashes": Sound.play("hit_blade2", 0.7); break;
      case "arrows": Sound.play("arrow", 0.7); break;
      case "wave": Sound.play("splash", 0.7); break;
    }
    switch (name) {
      case "motes": fx.motes(v3(a[0]), a[1], a[2]); break;
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
      case "rocks": fx.rocks(v3(a[0]), a[1], a[2]); break;
      case "num": fx.number(v3(a[0]), a[1], a[2], a[3]); break;
      case "bubble": { const e = this.entities.get(a[0]); if (e) fx.bubble(e.root, a[1]); break; }
      case "emberPatch": this.emberPatchVisual(a[0], v3(a[1]), a[2], a[3]); break;
      case "emberConsume": this.emberConsumeVisual(a[0], v3(a[1]), a[2]); break;
      case "emberGather": this.emberGatherVisual(v3(a[0]), a[1], a[2]); break;
      case "emberCharge": this.emberChargeVisual(a[0], a[1]); break;
      case "emberBeam": this.emberBeamVisual(v3(a[0]), v3(a[1])); break;
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
  /** Play a sound on every machine in the match (host and online guests). */
  private snd(name: string, vol = 1) { this.fxp("snd", name, vol); }

  /** The whoosh / cast / release sound when an attack comes out. */
  private swingSound(f: Fighter, a: Attack) {
    const heavy = a.heavy || f.atkId === "heavy";
    if (a.type === "melee") {
      if (f.kit === "knuckles" || f.kit === "kicks") this.snd(heavy ? "swing_heavy" : "whoosh_light", 0.7);
      else if (f.kit === "assassin") this.snd(heavy ? "swing2" : "dagger", 0.7);
      else if (f.kit === "greatsword" || heavy) this.snd("swing_heavy", 0.8);
      else this.snd(Math.random() < 0.5 ? "swing" : "swing2", 0.7);
    } else if (a.type === "projectile") {
      if (a.style === "arrow") this.snd("arrow", 0.7);
      else if (a.style === "shuriken") this.snd("dagger", 0.7);
      else if (f.kit === "knuckles" || f.kit === "kicks") this.snd("swing_heavy", 0.7);
      else if (a.element === "fire") this.snd("fireball", 0.6);
      else if (a.element === "electric") this.snd("zap", 0.6);
      else if (a.element === "water") this.snd("water", 0.5);
      else this.snd("cast", 0.6);
    } else if (a.type === "strike") {
      if (f.kit === "mage") this.snd(a.element === "water" ? "water" : "cast", 0.6);
      else if (a.style === "spin") this.snd("spin", 0.7);
      else this.snd("swing_heavy", 0.6);
    } else if (a.type === "blink") this.snd("teleport", 0.7);
  }

  /** The impact sound for a clean hit, by what hit it. */
  private hitSound(attacker: Entity | null, a: Attack, crit: boolean) {
    const heavy = a.heavy;
    let name = "hit_blunt";
    if (attacker instanceof Fighter) {
      const k = attacker.kit;
      if (a.type === "lob" || a.type === "mine" || a.type === "barrel") name = heavy ? "hit_big" : "hit_blunt";
      else if (a.type === "projectile" && a.style === "arrow") name = "arrow_hit";
      else if (a.type === "projectile" && k === "mage") name = a.element === "fire" ? "explosion" : a.element === "electric" ? "zap" : a.element === "water" ? "splash" : "hit_blunt";
      else if (k === "kicks") name = heavy ? "hit_big" : "hit_kick";
      else if (k === "knuckles") name = heavy ? "hit_big" : Math.random() < 0.5 ? "hit_blunt" : "hit_blunt2";
      else if (heavy) name = "hit_heavy";
      else name = Math.random() < 0.5 ? "hit_blade" : "hit_blade2";
    }
    this.snd(name, name === "explosion" ? 0.5 : 0.8);
    if (crit) this.snd("crit", 0.55);
  }

  private onSwing(f: Fighter) {
    const a = f.atk!;
    this.swingSound(f, a);
    const el = f.look.element;
    const big = ["z", "x", "c", "v", "heavy", "l3"].includes(f.atkId);
    if (el === "earth" && big && a.style !== "iron_tempest") {
      // Earth skills and heavy blows crack the ground in front of the fighter.
      const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
      this.fxp("rocks", f.root.position.clone().addScaledVector(fwd, 1.1).setY(f.root.position.y), f.atkId === "heavy" || f.atkId === "v" ? 24 : 16, f.atkId === "heavy" ? 1.35 : 1);
      this.add_trauma(f.atkId === "heavy" ? 0.4 : 0.25);
    } else if (el === "light" && a.type === "melee") {
      // Light: a bright flash and a burst of motes at the blade tip on every strike.
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("flash", tip, "#fff6c8", big ? 0.26 : 0.18, 0.14, 0.7);
      this.fxp("sparks", tip, "#fff2b0", big ? 18 : 8, 4);
    }
    if (f.kit === "sickle" && a.style === "sickle_carrion") {
      this.carrionSweep(f, a);
      return;
    }
    if (f.kit === "glaive" && ["glaive_cyclone", "glaive_serpent", "glaive_phantom", "glaive_infinite"].includes(a.style)) {
      this.stormGlaiveSwing(f, a);
      return;
    }
    if (f.kit === "glaive" && a.type === "melee") {
      const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("sparks", p, "#78dcff", big ? 25 : 12, 5);
    }
    // KAIZEN_DIRECTIONAL_V3: every move has its own hit logic and chain choreography.
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
        this.laterCombo(f, 0.18, () => {
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
    switch (a.type) {
      case "projectile":
        if (f.kit === "sickle" && a.style === "bloodcrescent") this.crimsonExecution(f, a);
        else this.fireProjectiles(f, a);
        break;
      case "strike": if (f.kit === "kicks" && a.style === "cyclone_kick_v2") this.cycloneKick(f, a, f.atkPower); else if (f.kit === "greatsword" && a.style === "iron_tempest") this.ironTempest(f, a, f.atkPower); else this.runStrike(f, a, f.atkPower); break;
      case "buff": this.applyBuff(f, a); break;
      case "blink": this.blink(f, a); break;
      case "phantom": this.phantom(f, a); break;
      case "lob": this.throwBombs(f, a); break;
      case "mine": this.plantMine(f, a); break;
      case "barrel": this.placeBarrel(f, a); break;
      default: this.melee(f, a);
    }
  }

  /** VEYR_BLOODLUST_CARRION_V7 — five REAL melee windows, not circular area damage. */
  private carrionSweep(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    const alive = () => this.round === round && f.swingSerial === serial &&
      !f.isDown() && f.state === S.ATTACK;
    const poses = ["vrv1_s", "vrv2_s", "vrv3_s", "vrv4_s", "vrv5_s"];
    const damage = [18, 20, 21, 22, 33];
    const guards = [5, 6, 6, 7, 10];
    const beat = (i: number) => {
      if (!alive()) return;
      f.poseOverride = poses[i];
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", tip, i % 2 ? "#ff799a" : "#ed315c");
      this.fxp("sparks", tip, i % 2 ? "#ffd9e4" : "#ff678c", 12 + i * 3, 5);
      this.fxp("flash", tip, "#fb3767", i === 4 ? 0.40 : 0.23, 0.12, 0.7);
      if (i > 0) this.snd(i === 4 ? "swing_heavy" : "dagger", 0.55);
      // Hit detection is the standard melee path: existing guard, parry, and clash rules apply.
      const part: Attack = { ...a, dmg: damage[i], guard: guards[i],
        knock: i === 4 ? 2.8 : 0.25, stun: i === 4 ? 0.30 : 0.10,
        heavy: false, style: "sickle_carrion" };
      this.melee(f, part);
    };
    beat(0);
    for (let i = 1; i < 5; i++) this.laterCombo(f, 0.14 * i, () => beat(i));
  }

  /** ZAREK_CYCLONE_V3: authoritative phased melee; blocks/parries/clashes use normal combat. */
  private stormGlaiveSwing(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    const alive = () => round === this.round && !f.isDown() && f.state === S.ATTACK && f.swingSerial === serial;
    const at = (i: number, part: Attack, pose: string) => {
      if (!alive()) return false;
      f.poseOverride = pose;
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", tip, f.look.glow);
      this.fxp("sparks", tip, i % 2 ? "#a5eeff" : "#4589ff", 18 + i * 4, 5);
      this.fxp("flash", tip, f.look.glow, 0.25 + i * 0.025, 0.11, 0.7);
      return this.melee(f, part); // true only when HP damage is dealt, not on block/parry.
    };
    if (a.style === "glaive_cyclone") {
      // The fifth tap is one overhead slash; holding the final click while it starts
      // adds three blade turns. A released click never triggers the extra hits.
      const extended = f.intent.attack;
      if (!extended) { at(0, a, "gl5_s"); return; }
      for (let i = 0; i < 4; i++) this.laterCombo(f, i * 0.13, () => {
        const part: Attack = { ...a, dmg: [38, 41, 42, 68][i], guard: [11, 11, 12, 20][i],
          knock: i === 3 ? 3.5 : 0.4, stun: i === 3 ? 0.38 : 0.12 };
        at(i, part, ["gl5_s", "gl2_s", "gl3_s", "gl5_s"][i]);
      });
      return;
    }
    if (a.style === "glaive_serpent") {
      // Five real damaging passes, one weapon-contact check per turn.
      for (let i = 0; i < 5; i++) this.laterCombo(f, i * 0.21, () => {
        const part: Attack = { ...a, dmg: i === 4 ? 45 : 33, guard: i === 4 ? 17 : 11,
          knock: i === 4 ? 2.2 : 0.35, stun: i === 4 ? 0.27 : 0.10,
          no_parry: true }; // still blockable and clashable
        at(i, part, ["glz_s", "gl3_s", "gl2_s", "gl4_s", "glz_s"][i]);
      });
      return;
    }
    if (a.style === "glaive_phantom") {
      at(0, { ...a, dmg: 85, guard: 22 }, "gl2_s");
      const opponent = f.opponent;
      if (opponent && !opponent.isDown()) {
        const from = f.root.position.clone();
        const across = opponent.root.position.clone().sub(from).setY(0);
        const length = across.length();
        if (length > 0.2 && length < 4.6) {
          const dest = opponent.root.position.clone().addScaledVector(across.normalize(), 0.85);
          for (let n = 1; n <= 3; n++) this.laterCombo(f, n * 0.055, () => {
            if (!alive()) return;
            const p = from.clone().lerp(dest, n / 3); p.y = f.root.position.y;
            if (f.stage) f.root.position.x = Math.max(f.stage.blast.l + 1.5, Math.min(f.stage.blast.r - 1.5, p.x));
            else {
              const flat = Math.hypot(p.x, p.z);
              if (flat > f.arenaRadius - 0.3) p.multiplyScalar((f.arenaRadius - 0.3) / flat);
              f.root.position.set(p.x, f.root.position.y, p.z);
            }
            this.fxp("sparks", f.chest(), "#8ceaff", 6, 3);
            if (n === 3 && opponent && !opponent.isDown()) {
              const face = opponent.root.position.clone().sub(f.root.position).setY(0);
              if (f.stage) f.facing = Math.sign(face.x) || f.facing;
              else if (face.lengthSq() > 0.001) f.root.rotation.y = Math.atan2(face.x, face.z);
            }
          });
        }
      }
      this.laterCombo(f, 0.23, () => at(1, { ...a, dmg: 115, guard: 32, knock: 3.4, stun: 0.40 }, "glx_turn"));
      return;
    }
    if (a.style === "glaive_infinite") {
      // Clash Counter is never consumed; the ultimate no longer uses charge stacks.
      const empowered = false;
      let connected = false;
      for (let i = 0; i < 8; i++) {
        const elapsed = [0, .26, .49, .70, .89, 1.07, 1.24, 1.55][i];
        this.laterCombo(f, elapsed, () => {
          if (!alive()) return;
          const launch = i === 6, final = i === 7;
          const part: Attack = { ...a,
            dmg: final ? (empowered ? 170 : 140) : launch ? 68 : [44, 42, 45, 44, 47, 48][i],
            guard: final ? 46 : launch ? 25 : 13,
            knock: final ? 5.0 : launch ? 0.7 : 0.35,
            stun: final ? .55 : launch ? .4 : .17,
            // ZAREK_WEAPON_RANGE_MATCH_V1_NOV06: use the same visible-length calibration as the glaive.
            reach: final ? 2.34 : 2.18,
            style: final ? "glaive_crescent_final" : launch ? "glaive_crescent_launch" : "glaive_infinite" };
          if (final && !connected) return; // no cinematic finish on missed/blocked starter
          if (launch && f.opponent && !f.opponent.isDown()) {
            // Follow upward with the target; this is NOT Gale's ground-smash.
            f.velY = Math.max(f.velY, 4.4); f.onGround = false;
          }
          if (final && !f.onGround) f.velY = Math.min(f.velY, -3.5); // aerial crosscut, not a ground slam
          const hit = at(i, part, final ? "glc_finish" : launch ? "glc_launch" :
            ["gl1_s", "gl2_s", "gl3_s", "gl4_s", "gl2_s", "gl3_s"][i]);
          if (hit) connected = true;
          if (final && hit) {
            this.fxp("lightning", f.chest(), "#9ceaff");
            this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "INFINITE CRESCENT", "#e7f8ff", .85);
            this.add_trauma(.55);
            this.hitStop(.19, .35);
          }
        });
      }
    }
  }

  /** KAIZEN_CHAINBLADE_V1: three independent, interruptible chain swipes. */
  private chainRazorCyclone(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    for (let i = 0; i < 9; i++) this.laterCombo(f, i * 0.18, () => {
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

  private chainDeathSpiral(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial, origin = f.root.position.clone();
    const times = [0.05, 0.28, 0.51, 0.74, 0.97, 1.20, 1.43];
    for (let i = 0; i < times.length; i++) this.laterCombo(f, times[i], () => {
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
    this.laterCombo(f, 1.67, () => {
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

  /** KAIZEN_SERPENT_SLAM_V10: actual multi-impact chained grab, host-authoritative. */
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
        victim.vx = 0;
        victim.velY = 0;
        
      }
    }));
  }

  /** Serpent Bind is a real four-second immobilization, not an immediate animation. */
  private chainSerpentBind(f: Fighter, a: Attack) {
    const forward = f.stage ? new THREE.Vector3(f.facing, 0, 0) :
      new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    for (const d of this.enemiesOf(f)) {
      if (!(d instanceof Fighter) || d.isDown()) continue;
      const diff = d.root.position.clone().sub(f.root.position).setY(0);
      if (diff.length() > a.reach + d.radius || diff.dot(forward) < -.60 ||
          Math.abs(d.root.position.y - f.root.position.y) > 1.55) continue;
      const outcome = this.applyHit(f, d, a, f.atkPower, d.chest(), diff.normalize(), false);
      if (!['hit','crit'].includes(outcome)) continue; // block, parry, clash still counter it
      f.beginChainBind(d, 'v');
      this.fxp("num", d.chest().add(new THREE.Vector3(0, .7, 0)), "SERPENT BIND", "#ff9eac", .8);
      return;
    }
  }

  private chainbladeCarousel(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    for (let i = 0; i < 3; i++) this.laterCombo(f, i * 0.22, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      const hit: Attack = { ...a, dmg: [65, 77, 98][i], guard: [17, 20, 28][i],
        knock: i === 2 ? 3.8 : 0.8, stun: i === 2 ? 0.39 : 0.19,
        reach: [2.7, 2.85, 3.05][i] };
      f.poseOverride = ["cbx1_s", "cbx2_s", "cbx3_s"][i];
      const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", p, i === 1 ? "#ffb4b4" : "#f54f66");
      this.fxp("sparks", p, "#ff8b91", 19 + i * 6, 5);
      this.melee(f, hit);
    });
  }

  private melee(f: Fighter, a: Attack): boolean {
    this.meleeCatchesAtSwing(f, a);
    let connected = false;
    // AIR_COMBAT_V1: launcher has a tall vertical hitbox; air combo is mid-height.
    const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const antiAir = f.atkId === "anti_air";
    const airCombo = f.atkId.startsWith("air_l");
    for (const d of this.enemiesOf(f)) {
      const to = d.root.position.clone().sub(f.root.position);
      const dy = Math.abs(to.y);
      to.y = 0;
      const dist = to.length();
      const dir = to.clone().divideScalar(Math.max(dist, 0.001));
      if (d instanceof Fighter && this.isDuel() && d.state === S.ATTACK && d.atk?.type === "melee" &&
        (d.atkPhase === 1 || (d.atkPhase === 0 && d.atk.wind - d.stateT <= 0.08)) && dist <= a.reach + (f.kit === "glaive" ? 0.12 : 0.3) &&
        dy < (antiAir || airCombo || d.atkId === "anti_air" || d.atkId.startsWith("air_l") ? 1.65 : 0.8)) {
        this.clash(f, d, f.root.position.clone().addScaledVector(dir, Math.min(dist * 0.5, 0.8)).add(new THREE.Vector3(0, 1.15, 0)));
        return false;
      }
      if (dist - d.radius + 0.35 > a.reach ||
          dy > (antiAir ? 3.25 : airCombo ? 1.8 : 1.3) ||
          (dist > 0.6 && dir.dot(fwd) < (antiAir ? -0.08 : 0.15))) continue;
      const hitPos = d.chest().addScaledVector(dir, -0.15);
      const result = this.applyHit(f, d, a, f.atkPower, hitPos, dir, false);
      if (result === "hit" || result === "crit" || result === "ko") {
        connected = true;
        if (a.style === "glaive_crescent_launch" && d instanceof Fighter) {
          d.velY = Math.max(d.velY, d.stage ? 6.2 : 5.1);
          d.onGround = false;
        }
      }
      if (f.kit === "chainblade" && a.style === "chain_predator_hook" &&
          ["hit", "crit"].includes(result) && d instanceof Fighter) {
        f.beginChainBind(d, 'x');
        // The long tether becomes visible on contact; wraps follow the victim.
        this.fxp("ring", d.chest(), "#ff607d", 0.75, 0.25, 0.7);
        this.fxp("slashes", d.chest(), "#ff7188");
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.7, 0)), "CHAIN-BOUND", "#ff8999", 0.8);
      }
      if (f.kit === "chainblade" && a.style === "chain_hook" &&
          (result === "hit" || result === "crit") && d instanceof Fighter) {
        // Pull only after a genuine HP hit; guard/parry/clash keeps its normal counterplay.
        const toward = f.root.position.clone().sub(d.root.position).setY(0);
        const amount = Math.max(0, Math.min(0.90, toward.length() - 1.35));
        if (amount > 0 && toward.lengthSq() > 1e-5) {
          const move = toward.normalize().multiplyScalar(amount);
          const dest = d.root.position.clone().add(move);
          if (d.stage) {
            dest.x = Math.max(d.stage.blast.l + 1, Math.min(d.stage.blast.r - 1, dest.x));
          } else {
            const flat = Math.hypot(dest.x, dest.z);
            if (flat > d.arenaRadius) { dest.x *= d.arenaRadius / flat; dest.z *= d.arenaRadius / flat; }
          }
          d.root.position.copy(dest);
          this.fxp("sparks", d.chest(), "#ff7885", 22, 5);
        }
      }
      if (antiAir && d instanceof Fighter && (result === "hit" || result === "crit")) {
        // Launcher happens only after an HP hit, never through blocks/parries/clashes.
        const wasGrounded = d.onGround;
        d.velY = Math.max(d.velY, f.stage ? 7.2 : 6.6);
        d.onGround = false;
        if (wasGrounded) this.fxp("ring", d.root.position.clone().add(new THREE.Vector3(0, 0.35, 0)), f.look.glow, 1.2, 0.22, 0.75);
        f.landedAntiAir(d);
        this.fxp("sparks", d.chest(), f.look.glow, 22, 6, [0, 1, 0]);
      }
    }
    // Hitting an enemy's powder keg sets it off.
    for (const t of [...this.traps]) {
      if (t.kind !== "barrel" || t.team === f.team) continue;
      const to = t.pos.clone().sub(f.root.position).setY(0);
      const dist = to.length();
      if (dist - 0.45 <= a.reach && (dist < 0.6 || to.normalize().dot(fwd) > 0.15)) this.detonate(t);
    }
    return connected;
  }

  private fireProjectiles(f: Fighter, a: Attack) {
    const origin = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const tgt = f.opponent;
    const aim = tgt ? tgt.chest().sub(origin) : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    if (!tgt) aim.y = 0;
    const base = aim.normalize();
    for (let i = 0; i < a.count; i++) {
      const off = a.count === 1 ? 0 : -a.spread + (2 * a.spread * i) / (a.count - 1);
      const blood = f.kit === "sickle" && a.style === "bloodsickle";
      const p = this.spawnProjectile(f, f.team, a, f.atkPower, origin,
        base.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), off).multiplyScalar(a.speed),
        a.style, a.element, a.size, f.look.glow, a.pierce, blood ? null : tgt);
      if (blood) { p.life = 2.0; f.sickleOut = true; }
    }
    this.fxp("flash", origin, f.look.glow, 0.25, 0.1, 0.7);
  }

  /** Recast redirects the already-thrown sickle once toward the nearest enemy within 9m. */
  private recastBloodSickle(f: Fighter) {
    const p = this.projectiles.find((x) => !x.done && x.shooter === f && x.style === "bloodsickle" && !x.steered);
    if (!p) { f.sickleOut = false; return; }
    const target = this.enemiesOf(f).filter((e) => e.root.position.distanceTo(p.pos) <= 9)
      .sort((a, b) => a.root.position.distanceToSquared(p.pos) - b.root.position.distanceToSquared(p.pos))[0];
    if (!target) { this.fxp("num", f.chest(), "NO TARGET", "#ff9ba8", 0.65); return; }
    p.steering = true; p.steered = true; p.target = target;
    this.emit(["projHunt", p.id, target.id, p.finalBlade ? 1 : 0, p.age]);
    p.life = Math.max(p.life, 1.3);
    f.sickleOut = false;
    this.fxp("flash", p.pos, "#e83d63", 0.35, 0.15, 0.8);
    this.snd("dagger", 0.6);
  }

  /** Three separately dodgeable curved blades; last consumes poison on a successful hit. */
  private crimsonExecution(f: Fighter, a: Attack) {
    const origin = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const target = f.opponent && !f.opponent.isDown() ? f.opponent :
      this.enemiesOf(f).sort((x, y) => x.root.position.distanceToSquared(origin) - y.root.position.distanceToSquared(origin))[0] ?? null;
    const forward = target ? target.chest().sub(origin).normalize() :
      new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    for (let i = 0; i < 3; i++) {
      const off = (i - 1) * 0.58;
      const vel = forward.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), off).multiplyScalar(a.speed);
      const p = this.spawnProjectile(f, f.team, a, f.atkPower, origin.clone(), vel, "bloodcrescent", a.element, a.size, "#ff496e", false, target);
      p.life = 1.8 + i * 0.12;
      p.steering = true;
      p.finalBlade = i === 2;
      // Prevent three blades from instantly piling onto a stationary enemy.
      p.age = -i * 0.14;
      this.emit(["projHunt", p.id, target?.id ?? -1, p.finalBlade ? 1 : 0, p.age]);
    }
    this.fxp("flash", origin, "#ff496e", 0.55, 0.18, 0.85);
  }

  private spawnProjectile(shooter: Entity | null, team: number, a: Attack, power: number, pos: THREE.Vector3, vel: THREE.Vector3,
    style: string, element: string, size: number, color: string, pierce: boolean, target: Entity | null): Projectile {
    const p = new Projectile(this.nextId++, shooter, team, a, power, pos, vel, style, element, size, color, pierce, false, target);
    this.scene.add(p.group);
    this.projectiles.push(p);
    this.emit(["proj", p.id, style, element, size, color, pos, vel]);
    return p;
  }

  // --- bomber -------------------------------------------------------------------------------
  /** Lob bombs in an arc that lands at the target (or ahead) after `a.delay` seconds. */
  private throwBombs(f: Fighter, a: Attack) {
    const origin = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const o = f.opponent;
    const aim = o && !o.isDown() ? o.root.position.clone().setY(0) : f.root.position.clone().addScaledVector(fwd, 5).setY(0);
    const T = Math.max(a.delay, 0.3), g = BOMB_GRAVITY;
    for (let i = 0; i < a.count; i++) {
      const off = a.count === 1 ? 0 : -a.spread + (2 * a.spread * i) / (a.count - 1);
      const to = aim.clone().sub(origin).setY(0).applyAxisAngle(new THREE.Vector3(0, 1, 0), off);
      const land = origin.clone().setY(0).add(to);
      const vel = new THREE.Vector3((land.x - origin.x) / T, (0.08 - origin.y + 0.5 * g * T * T) / T, (land.z - origin.z) / T);
      const p = this.spawnProjectile(f, f.team, a, f.atkPower, origin, vel, "bomb", a.element, a.size, f.look.glow, false, o);
      p.gravity = g;
      p.life = T + 1;
    }
    this.snd("whoosh_light", 0.6);
  }

  /** A bomb goes off at `pos`: hits enemies in `a.radius` (cluster bombs burst `repeat` times). */
  private bombBlast(owner: Entity | null, a: Attack, power: number, pos: THREE.Vector3, team: number) {
    const round = this.round;
    const one = (at: THREE.Vector3) => {
      if (round !== this.round) return;
      const g = at.clone().setY(0);
      this.fxp("explosion", g, "#ffb347", a.radius);
      this.fxp("smoke", g, "#6a5a4a");
      if (a.effect === "paralyze") { this.fxp("lightning", g, "#ffe066"); this.fxp("sparks", g.clone().setY(0.4), "#ffe066", 30, 7); }
      this.add_trauma(Math.min(0.15 + a.radius * 0.12, 0.7));
      for (const d of this.enemiesOfTeam(team)) {
        const to = d.root.position.clone().sub(g);
        const dy = Math.abs(to.y);
        to.setY(0);
        if (to.length() <= a.radius + d.radius * 0.5 && dy < 1.5) {
          const dir = to.length() > 0.05 ? to.normalize() : new THREE.Vector3(1, 0, 0);
          this.applyHit(owner, d, a, power, d.chest(), dir, true);
        }
      }
      // Bombs, mines and powder kegs cannot hurt the bomber or allies.
      for (const t of [...this.traps]) if (t.kind === "barrel" && t.team !== team && t.pos.distanceTo(g) <= a.radius + 0.4) this.detonate(t);
    };
    one(pos);
    for (let i = 1; i < a.repeat; i++) {
      const an = (i / (a.repeat - 1)) * Math.PI * 2 + Math.random();
      const at = pos.clone().add(new THREE.Vector3(Math.cos(an), 0, Math.sin(an)).multiplyScalar(a.radius * 0.9));
      this.later(a.interval * i, () => one(at));
    }
  }

  private plantMine(f: Fighter, a: Attack) {
    const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const mine = this.addTrap("mine", f, a, f.root.position.clone().addScaledVector(fwd, 0.6).setY(0));
    mine.arm = 0.5;
    mine.life = 25;
    // At most 3 mines each: the oldest one fizzles.
    const mines = this.traps.filter((t) => t.kind === "mine" && t.owner === f);
    if (mines.length > 3) this.removeTrap(mines[0], true);
    this.snd("land", 0.6);
  }

  private placeBarrel(f: Fighter, a: Attack) {
    const old = this.traps.find((t) => t.kind === "barrel" && t.owner === f);
    if (old) this.detonate(old);
    const fwd = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const keg = this.addTrap("barrel", f, a, f.root.position.clone().addScaledVector(fwd, 1.2).setY(0));
    keg.life = 25;
    f.barrelOut = true;
    f.barrelPos.copy(keg.pos);
    this.fxp("ring", keg.pos.clone(), "#c98a52", 1.4, 0.3, 0.7);
    this.snd("slam", 0.5);
  }

  private addTrap(kind: "mine" | "barrel", owner: Fighter, a: Attack, pos: THREE.Vector3): Trap {
    const t: Trap = { id: this.nextId++, kind, owner, team: owner.team, atk: a, power: owner.atkPower, pos, mesh: buildTrap(kind, owner.look.glow), arm: 0, life: 25, t: 0 };
    t.mesh.position.copy(pos);
    this.scene.add(t.mesh);
    this.traps.push(t);
    this.emit(["trap", t.id, kind, [+pos.x.toFixed(2), 0, +pos.z.toFixed(2)], owner.look.glow]);
    return t;
  }

  private removeTrap(t: Trap, fizzle = false) {
    this.scene.remove(t.mesh);
    this.traps = this.traps.filter((x) => x !== t);
    this.emit(["trapEnd", t.id]);
    if (fizzle) this.fxp("smoke", t.pos.clone(), "#8a8a8a");
    if (t.kind === "barrel" && t.owner) {
      t.owner.barrelOut = false;
      // The keg's cooldown starts now.
      for (const k of ["z", "x", "c"]) if (t.owner.attacks[k]?.type === "barrel") t.owner.cooldowns[k] = t.atk.cd * t.owner.cdMult;
    }
  }

  /** Blow up a mine or keg (a keg's blast is huge). */
  private detonate(t: Trap) {
    if (!this.traps.includes(t)) return;
    this.removeTrap(t);
    if (t.kind === "barrel") { this.fxp("rocks", t.pos.clone(), 26, 1.5); this.add_trauma(0.7); this.hitStop(0.08); }
    this.bombBlast(t.owner, t.atk, t.power, t.pos.clone(), t.team);
  }

  private updateTraps(dt: number) {
    for (const t of [...this.traps]) {
      t.t += dt;
      animateTrap(t, dt);
      if (this.cfg.role === "client") continue;
      t.life -= dt;
      if (t.kind === "mine") {
        t.arm -= dt;
        if (t.arm <= 0 && this.enemiesOfTeam(t.team).some((e) => !e.airborne() && e.root.position.clone().setY(0).distanceTo(t.pos) < 1.0 + e.radius * 0.5)) {
          this.snd("click", 0.7);
          this.detonate(t);
          continue;
        }
        if (t.life <= 0) this.removeTrap(t, true);
      } else if (t.life <= 0) this.detonate(t);
    }
  }

  /** Host-only weapon versus projectile collision. Non-bomb projectiles are destroyed;
   * Bob's lobbed explosives instead detonate at the point of weapon impact.
   * Tests projectile motion in short segments so fast shots don't tunnel through swords. */
  private meleeCatchesProjectile(p: Projectile, from: THREE.Vector3): boolean {
    if (p.done || p.visualOnly || !p.atk) return false;
    for (const f of this.fighters) {
      if (f.isDown() || f.team === p.team || f.state !== S.ATTACK || !f.atk) continue;
      const a = f.atk;
      // Only actual active melee frames can intercept projectiles, never passive guard.
      if (a.type !== "melee" || !(f.atkPhase === 1 || f.trail.emitting)) continue;
      if (this.projectileWithinSwing(f, a, from, p.pos, p.size)) {
        this.finishMeleeProjectile(p, f);
        return true;
      }
    }
    return false;
  }

  /** Called by each programmed melee hit, so multihit choreography can catch shots too. */
  private meleeCatchesAtSwing(f: Fighter, a: Attack) {
    if (this.cfg.role === "client" || a.type !== "melee") return;
    for (const p of this.projectiles) {
      if (p.done || p.visualOnly || !p.atk || p.team === f.team) continue;
      if (this.projectileWithinSwing(f, a, p.pos, p.pos, p.size)) this.finishMeleeProjectile(p, f);
    }
  }

  private projectileWithinSwing(f: Fighter, a: Attack, from: THREE.Vector3, to: THREE.Vector3, size: number): boolean {
    const center = f.root.position.clone().add(new THREE.Vector3(0, 1.12, 0));
    const forward = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const reach = Math.max(0.65, a.reach || 1.55);
    const horizontalRoom = 0.25 * size + 0.22;
    // Sample the swept projectile path; use melee's frontal cone and real attack reach.
    for (let i = 0; i <= 5; i++) {
      const sample = from.clone().lerp(to, i / 5).sub(center);
      const vertical = Math.abs(sample.y);
      if (vertical > (f.atkId === "anti_air" || f.atkId.startsWith("air_l") ? 1.9 : 0.94) + horizontalRoom) continue;
      sample.y = 0;
      const dist = sample.length();
      if (dist > reach + horizontalRoom) continue;
      // A close projectile can be hit from the side; distant ones must be in the swing arc.
      if (dist > 0.64 && sample.dot(forward) / Math.max(0.001, dist) < 0.08) continue;
      return true;
    }
    return false;
  }

  private finishMeleeProjectile(p: Projectile, defender: Fighter) {
    if (p.done) return;
    p.done = true;
    const contact = p.pos.clone();
    this.fxp("sparks", contact, defender.look.glow, 23, 6);
    this.fxp("flash", contact, "#fff4c7", 0.24, 0.13, 0.86);
    if (p.atk && (p.atk.type === "lob" || p.style === "bomb")) {
      // Preserve Bob's normal explosive damage/radius even when his bomb is struck.
      this.bombBlast(p.shooter, p.atk, p.power, contact, p.team);
      this.snd("clash", 0.7);
    } else {
      this.snd("clash", 0.55);
    }
  }

  private updateProjectiles(dt: number) {
    for (const p of this.projectiles) {
      if (p.done) continue;
      if (p.gravity) { p.vel.y -= p.gravity * dt; p.spin.rotation.x += dt * 9; }
      p.age += dt;
      if (p.steering && p.target && !p.target.isDown() && p.age > (p.style === "bloodcrescent" ? 0.38 : 0)) {
        const aim = p.target.chest().sub(p.pos);
        if (aim.lengthSq() > 0.01) {
          const speed = p.atk?.speed ?? 15;
          const turnRate = p.style === "bloodcrescent" ? 2.0 : 4.3;
          p.vel.lerp(aim.normalize().multiplyScalar(speed), Math.min(1, dt * turnRate)).normalize().multiplyScalar(speed);
        }
      }
      const beforeMelee = p.pos.clone();
      p.pos.addScaledVector(p.vel, dt);
      p.life -= dt;
      // Server/host authoritative: slash, punch or kick a hostile projectile in active frames.
      if (!p.visualOnly && this.meleeCatchesProjectile(p, beforeMelee)) continue;
      if (!p.visualOnly && p.atk) {
        const keg = this.traps.find((t) => t.kind === "barrel" && t.team !== p.team && p.pos.distanceTo(t.pos.clone().setY(0.45)) < 0.75);
        if (keg) {
          this.detonate(keg);
          if (p.atk.type === "lob") this.bombBlast(p.shooter, p.atk, p.power, p.pos.clone(), p.team);
          if (!p.pierce || p.atk.type === "lob") { p.done = true; continue; }
        }
      }
      if (!p.visualOnly && p.atk?.type === "lob") {
        const hitE = this.enemiesOfTeam(p.team).find((e) => p.pos.distanceTo(e.chest()) < 0.35 * p.size + e.radius);
        if (hitE || p.pos.y <= 0.08) {
          this.bombBlast(p.shooter, p.atk, p.power, p.pos.clone(), p.team);
          p.done = true;
          continue;
        }
      }
      if (p.style === "bloodsickle" || p.style === "bloodcrescent") p.spin.rotation.z += dt * 19;
      else if (p.style === "shuriken") p.spin.rotation.y += dt * 30;
      else if (p.style === "bolt") p.spin.rotation.z += dt * 12;
      if (!p.visualOnly && p.atk) {
        for (const e of this.enemiesOfTeam(p.team)) {
          if (p.hitIds.has(e.id)) continue;
          if (p.pos.distanceTo(e.chest()) < 0.3 * p.size + e.radius) {
            p.hitIds.add(e.id);
            const dir = p.vel.clone().setY(0).normalize();
            this.impactFx(p.atk, p.pos.clone(), p.color, 0.7);
            const stacks = p.finalBlade && (e instanceof Fighter || e instanceof Mob) ? e.status.stacks("poison") : 0;
            const atk = stacks ? { ...p.atk, dmg: p.atk.dmg + stacks * 15, effect: "" } : p.atk;
            const outcome = this.applyHit(p.shooter, e, atk, p.power, p.pos.clone(), dir, true);
            if (stacks && ["hit", "crit", "ko"].includes(outcome) && (e instanceof Fighter || e instanceof Mob)) {
              e.status.consume("poison");
              this.fxp("num", e.chest().add(new THREE.Vector3(0, 0.8, 0)), `EXECUTE +${stacks * 15}`, "#ff5072", 0.9);
            }
            if (!p.pierce) { p.done = true; break; }
          }
        }
      }
      const flat = Math.hypot(p.pos.x, p.pos.z);
      const gone = this.plat ? Math.abs(p.pos.x) > 20 || p.pos.y < -10 || this.hitsStage(p.pos) : p.pos.y < 0.05 || flat > 16;
      if (p.life <= 0 || gone) {
        if (!p.visualOnly && p.atk?.type !== "lob") this.fxp("sparks", p.pos.clone(), p.color, 8, 3);
        p.done = true;
      }
    }
    for (const p of this.projectiles) if (p.done) {
      this.scene.remove(p.group);
      if (p.shooter instanceof Fighter && p.style === "bloodsickle") p.shooter.sickleOut = false;
      if (!p.visualOnly) this.emit(["projEnd", p.id]);
    }
    this.projectiles = this.projectiles.filter((p) => !p.done);
  }

  private enemiesOfTeam(team: number): Entity[] {
    return [...this.entities.values()].filter((o) => o.team !== team && !o.isDown());
  }

  /** SWORD_AND_CYCLONE_V1: Kira's feet actually change every beat. No repeated ring FX. */
  private cycloneKick(f: Fighter, a: Attack, power: number) {
    const round = this.round;
    const serial = f.swingSerial;
    const times = [0.03, 0.22, 0.41];
    for (let i = 0; i < times.length; i++) this.laterCombo(f, times[i], () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK ||
          f.swingSerial !== serial || f.atk?.style !== "cyclone_kick_v2") return;
      const center = f.root.position.clone();
      const leg = i === 1 ? f.model.leg_l : f.model.leg_r;
      const foot = leg.localToWorld(new THREE.Vector3(0, -0.78, 0.12));
      this.fxp("slashes", foot, i === 2 ? "#c6ffef" : "#70e8d6");
      this.fxp("sparks", foot, f.look.glow, i === 2 ? 24 : 13, 5);
      this.snd(i === 2 ? "swing_heavy" : "swing", i === 2 ? 0.65 : 0.45);
      const strike: Attack = { ...a, repeat: 1, knock: i === 2 ? 4.5 : 0.9,
        stun: i === 2 ? 0.4 : 0.15, heavy: false };
      for (const d of this.enemiesOf(f)) {
        const to = d.root.position.clone().sub(center);
        const height = Math.abs(to.y);
        to.y = 0;
        const range = to.length();
        if (range > a.radius + d.radius * 0.5 || height > 1.65) continue;
        const dir = range > 0.05 ? to.divideScalar(range) :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        this.applyHit(f, d, strike, power, d.chest(), dir, false);
      }
    });
  }

  /** Garrick X: three distinct steel arcs, not an auto-repeating radial blast.
   *  The final horizontal cleave can hit a nearby airborne target, but never slams down.
   *  Each hit still goes through the ordinary block / parry / guard-break logic.
   *  Interrupted windups, parries, round changes and KOs cancel later sweeps.
   */
  private ironTempest(f: Fighter, a: Attack, power: number) {
    const round = this.round;
    const swing = f.swingSerial;
    const stages = [
      { time: 0.04, dmg: 70,  guard: 22, radius: 2.25, knock: 0.9, stun: 0.16, heavy: false, height: 1.75 },
      { time: 0.33, dmg: 90,  guard: 29, radius: 2.55, knock: 1.2, stun: 0.20, heavy: false, height: 2.75 },
      { time: 0.67, dmg: 150, guard: 50, radius: 2.80, knock: 7.0, stun: 0.62, heavy: true,  height: 2.30 },
    ];
    for (let i = 0; i < stages.length; i++) {
      const s = stages[i];
      this.laterCombo(f, s.time, () => {
        if (round !== this.round || f.isDown() || f.state !== S.ATTACK ||
            f.swingSerial !== swing || f.atk?.style !== "iron_tempest") return;
        const at = f.root.position.clone();
        const mid = at.clone().add(new THREE.Vector3(0, i === 1 ? 1.55 : 1.05, 0));
        // Tall sweeping blade trails instead of ground craters / Gale-style slams.
        const steel = i === 2 ? "#ffe2a0" : "#c5d8ff";
        this.fxp("ring", mid, steel, s.radius, 0.24, i === 2 ? 1 : 0.75);
        this.fxp("slashes", mid, steel);
        this.fxp("sparks", mid, f.look.glow, i === 2 ? 34 : 18, i === 2 ? 9 : 6);
        if (i === 2) {
          this.fxp("flash", mid, "#fff4d3", 0.8, 0.16, 0.9);
          this.add_trauma(0.28);
        }
        this.snd(i === 2 ? "swing_heavy" : "swing", i === 2 ? 0.9 : 0.55);
        const strike: Attack = { ...a, dmg: s.dmg, guard: s.guard, knock: s.knock,
          stun: s.stun, heavy: s.heavy, radius: s.radius, repeat: 1 };
        for (const d of this.enemiesOf(f)) {
          const to = d.root.position.clone().sub(at);
          const dy = Math.abs(to.y);
          to.y = 0;
          const dist = to.length();
          if (dist > s.radius + d.radius * 0.5 || dy > s.height) continue;
          const dir = dist > 0.05 ? to.divideScalar(dist) :
            new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
          this.applyHit(f, d, strike, power, d.chest(), dir, false);
        }
      });
    }
  }

  /** Area attack(s) at the target (or around the caster) after a telegraphed delay. */
  private runStrike(f: Fighter, a: Attack, power: number) {
    const round = this.round;
    const color = f.look.glow;
    const one = (i: number) => {
      if (round !== this.round || f.isDown()) return;
      const src: Entity = a.at === "self" || !f.opponent ? f : f.opponent;
      const center = this.plat ? src.root.position.clone() : src.root.position.clone().setY(0);
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
        const at = a.at === "self" ? (this.plat ? f.root.position.clone() : f.root.position.clone().setY(0)) : center;
        this.impactFx(a, at, color, a.radius);
        if (f.look.element === "fire" && f.kit === "mage" &&
            (a.id === "heavy" || a.id === "c") && i === 0) {
          // EMBER_GROUND_HAZARD_AI_V1_NOV06: smaller persistent fire circles (Meteor / charged heavy).
          this.spawnEmberPatch(f, at, a.id === "c" ? 1.25 : 0.65);
        }
        for (const d of this.enemiesOf(f)) {
          const to = d.root.position.clone().sub(at);
          const dy = Math.abs(to.y);
          to.setY(0);
          if (to.length() <= a.radius + d.radius * 0.5 && (this.plat ? dy < 1.6 : !d.airborne())) {
            const dir = to.length() > 0.05 ? to.normalize() : d.root.position.clone().sub(f.root.position).setY(0).normalize();
            this.applyHit(f, d, a, power, d.chest(), dir, true);
          } else if (d instanceof Fighter && to.length() <= a.radius + 1) {
            this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.8, 0)), "DODGE", "#c9d3e6", 0.7);
          }
        }
        for (const t of [...this.traps]) if (t.kind === "barrel" && t.team !== f.team && t.pos.distanceTo(at) <= a.radius + 0.4) this.detonate(t);
        if (i + 1 < a.repeat) one(i + 1);
      });
    };
    one(0);
  }

  private impactFx(a: Attack, pos: THREE.Vector3, color: string, radius: number) {
    const g = this.plat ? pos.clone() : pos.clone().setY(0);
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
        if (a.style === "slam") this.fxp("rocks", g, 22, 1.4);
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

  /** Host casts Blood Festival, teleports Veyr next to the target and captures nearby enemies. */
  private startBloodFestival(f: Fighter, a: Attack) {
    if (f.isDown()) return;
    const target = (f.opponent && !f.opponent.isDown() ? f.opponent : null) ??
      this.enemiesOf(f).sort((u, v) => u.root.position.distanceToSquared(f.root.position) - v.root.position.distanceToSquared(f.root.position))[0];
    if (!target) { this.fxp("num", f.chest(), "NO TARGET", "#ff9fb8", 0.75); return; }
    // Reusing the same C before expiry is already forbidden in Fighter.readSkill.
    const from = f.root.position.clone();
    const d = f.root.position.clone().sub(target.root.position).setY(0);
    if (d.lengthSq() < 0.001) d.set(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    d.normalize();
    this.fxp("smoke", from, "#9e1f43");
    f.teleport(target.root.position.clone().addScaledVector(d, 1.25));
    // Teleport only grants a tiny safety window, not 6 seconds of damage immunity.
    f.invulnT = Math.min(f.invulnT, 0.08);
    this.fxp("smoke", f.root.position.clone(), "#ed345d");
    this.snd("teleport", 0.65);
    // Anchor Blood Festival to the arena floor, never the target's jump height.
    // In 3D duel/team/survival, the ground is y=0. In platform brawl,
    // pick the highest platform directly below the target, if any.
    const festivalGroundY = this.plat
      ? STAGE.plats.reduce((ground, platform) => {
          const abovePlatform = target.root.position.y + 0.05 >= platform.y;
          const overPlatform = target.root.position.x >= platform.x0 && target.root.position.x <= platform.x1;
          return abovePlatform && overPlatform ? Math.max(ground, platform.y) : ground;
        }, 0)
      : 0;
    const center = new THREE.Vector3(
      target.root.position.x, festivalGroundY, this.plat ? 0 : target.root.position.z
    );
    const radius = a.radius > 0 ? a.radius : 3.5;
    const { visual, blades } = makeBloodFestivalVisual(radius);
    visual.position.copy(center);
    this.scene.add(visual);
    const captured = new Set(this.enemiesOf(f).filter(e => {
      const dx = e.root.position.x - center.x;
      const dz = this.plat ? 0 : e.root.position.z - center.z;
      return Math.hypot(dx, dz) < radius + 0.1;
    }).map(e => e.id));
    const id = this.nextId++;
    this.bloodFestivals.push({ id, owner: f, team: f.team, center, radius, time: a.duration, age: 0, visual, blades, captured, contact: new Map() });
    f.bloodFestivalT = a.duration;
    // VEYR_BLOODLUST_CARRION_V7: Festival doesn't fill Bloodlust or start Frenzy.
    // Landing attacks inside the arena can still build Bloodlust normally.
    this.fxp("ring", center, "#f33b65", radius, 0.45, 0.85);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "BLOOD FESTIVAL", "#ff7895", 1.0);
    this.snd("spin", 0.75);
    this.emit(["bloodFestival", id, center.toArray(), radius, a.duration, f.id, f.team]);
  }

  /** Ring rotates on every machine. Only host/offline changes enemy positions. */
  private updateBloodFestivals(dt: number) {
    for (const ring of [...this.bloodFestivals]) {
      ring.time -= dt;
      ring.age += dt;
      const spin = ring.age * 4.2;
      ring.blades.forEach((b, i) => {
        const a = spin + i * Math.PI * 2 / ring.blades.length;
        b.position.set(Math.sin(a) * ring.radius, 0.9 + 0.19 * Math.sin(ring.age * 6 + i), Math.cos(a) * ring.radius);
        b.rotation.y = a + Math.PI * 0.5;
        b.rotation.z = -0.14 * Math.sin(ring.age * 5 + i);
      });
      if (this.cfg.role !== "client" && ring.owner && !ring.owner.isDown()) {
        for (const enemy of this.enemiesOf(ring.owner)) {
          const x = enemy.root.position.x - ring.center.x;
          const z = this.plat ? 0 : enemy.root.position.z - ring.center.z;
          const dist = Math.hypot(x, z);
          // Enemies who enter the circle later become captives as they approach its blades.
          if (!ring.captured.has(enemy.id)) {
            if (dist <= ring.radius + 0.10) ring.captured.add(enemy.id);
            else continue;
          }
          const next = ring.contact.get(enemy.id) ?? 0;
          if (dist < ring.radius - 0.32 || ring.age < next) continue;
          if (dist > 0.0001) {
            // Push into the arena rather than stunning, damaging or teleporting the target.
            const pull = Math.max(0, dist - (ring.radius - 1.45));
            enemy.root.position.x -= x / dist * pull;
            if (!this.plat) enemy.root.position.z -= z / dist * pull;
          }
          ring.contact.set(enemy.id, ring.age + 0.35);
          this.fxp("slashes", enemy.root.position.clone(), "#ff3c68");
          this.fxp("ring", enemy.root.position.clone(), "#ff6080", 0.65, 0.19, 0.55);
        }
      }
      if (ring.time <= 0 || (this.cfg.role !== "client" && (!ring.owner || ring.owner.isDown()))) {
        this.scene.remove(ring.visual);
        this.bloodFestivals = this.bloodFestivals.filter(x => x !== ring);
        if (ring.owner) ring.owner.bloodFestivalT = 0;
        this.emit(["bloodFestivalEnd", ring.id]);
      }
    }
  }

  private applyBuff(f: Fighter, a: Attack) {
    // PvP versions of defensive magic are weaker than in survival.
    const pvp = this.cfg.mode !== "survival";
    this.snd(a.mode === "heal" ? "heal" : a.mode === "rage" ? "rage"
      : a.mode === "judgment" ? "cast" : a.mode === "ember_ignition" ? "fireball" : "ward", 0.7);
    if (a.mode === "ward") {
      const dur = pvp ? Math.min(a.duration, 2) : a.duration;
      f.wardT = dur;
      this.fxp("bubble", f.id, dur);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "WARD", "#8fe6ff", 0.9);
    } else if (a.mode === "heal") {
      const frac = pvp ? 0.16 : 0.25;
      f.heal(f.maxHp * frac);
      this.fxp("splash", f.chest(), 30, 1.2, "#7fe0ff");
      this.fxp("ring", f.root.position.clone(), "#9dff9a", 1.6, 0.4, 0.9);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), `+${Math.round(f.maxHp * frac)}`, "#9dff9a", 1.1);
    } else if (a.mode === "rage") {
      f.rageT = a.duration;
      this.fxp("flash", f.chest(), "#ff5a3d", 0.7, 0.3, 0.8);
      this.fxp("embers", f.chest(), "#ff7a33", 30);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "BERSERK", "#ff8a50", 1.0);
    } else if (a.mode === "judgment" && f.kit === "knight" && f.look.element === "light") {
      // Harmless lightning strike: only VFX. Health drain starts during the form.
      f.judgmentT = a.duration;
      f.guard = Math.min(f.guard, f.maxGuard * 0.5);
      f.model.setJudgment(true);
      const sword = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("lightning", sword, "#d8eaff");
      this.fxp("flash", sword, "#fff5c2", 1.4, 0.32, 0.98);
      this.fxp("sparks", sword, "#f0e9a3", 70, 9);
      this.fxp("sparks", f.model.shieldNode.getWorldPosition(new THREE.Vector3()), "#c4e8ff", 40, 7);
      this.fxp("flash", f.chest(), "#d6efff", 1.1, 0.24, 0.85);
      this.fxp("ring", sword, "#c6eeff", 1.35, 0.24, 0.85);
      this.fxp("ring", f.root.position.clone(), "#ffe7a3", 1.8, 0.42, 0.9);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 1, 0)), "JUDGMENT", "#ffefac", 1.2);
    } else if (a.mode === "ember_ignition" && f.kit === "mage" && f.look.element === "fire") {
      this.castEmberIgnition(f, a);
    } else if (a.mode === "blood_festival") {
      this.startBloodFestival(f, a);
    } else if (a.mode === "blood_feint") {
      f.counterT = Math.min(a.duration, 0.30);
      f.bloodFeintT = Math.min(a.duration, 0.30);
      this.fxp("flash", f.chest(), "#ff456f", 0.38, 0.12, 0.8);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "DEATH FEINT", "#ffb6c6", 0.7);
    } else if (a.mode === "counter") {
      f.counterT = a.duration;
      this.fxp("flash", f.chest(), f.look.glow, 0.5, 0.2, 0.6);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "COUNTER STANCE", "#ffd1da", 0.7);
    }
  }

  /** Fire patches exist for 20 seconds, damage only enemies, and replicate to online guests. */
  private spawnEmberPatch(owner: Fighter, pos: THREE.Vector3, radius: number) {
    // Cap simultaneous patches at five per player, so the arena never fills forever.
    const own = this.emberPatches.filter(p => p.ownerId === owner.id);
    if (own.length >= 5) {
      const oldest = own[0];
      this.fxp("emberConsume", owner.id, oldest.pos.clone(), 0.01);
    }
    this.fxp("emberPatch", owner.id, pos.clone(), radius, 20);
  }

  private emberPatchVisual(ownerId: number, pos: THREE.Vector3, radius: number, ttl: number) {
    const root = new THREE.Group();
    root.position.copy(pos).y += 0.045;
    const m = new THREE.MeshBasicMaterial({ color: "#ff601c", side: THREE.DoubleSide,
      transparent: true, opacity: 0.34, depthWrite: false });
    const pool = new THREE.Mesh(new THREE.CircleGeometry(radius * 0.88, 32), m);
    pool.rotation.x = -Math.PI / 2;
    root.add(pool);
    const edge = new THREE.Mesh(new THREE.RingGeometry(radius * 0.82, radius, 32),
      new THREE.MeshBasicMaterial({ color: "#ffcc55", side: THREE.DoubleSide,
        transparent: true, opacity: 0.74, depthWrite: false }));
    edge.rotation.x = -Math.PI / 2;
    edge.position.y = 0.018;
    root.add(edge);
    this.scene.add(root);
    this.emberPatches.push({ ownerId, pos: pos.clone(), radius, ttl, tick: 1, visual: root });
  }

  private emberConsumeVisual(ownerId: number, center: THREE.Vector3, radius: number) {
    this.emberPatches = this.emberPatches.filter(p => {
      if (p.ownerId !== ownerId || p.pos.distanceTo(center) > radius) return true;
      if (radius > 0.1) this.emberGatherVisual(p.pos.clone(), ownerId, 11);
      this.scene.remove(p.visual);
      return false;
    });
  }

  /** Each consumed flame produces individual moving embers, not instantaneous light rays. */
  private emberGatherVisual(from: THREE.Vector3, ownerId: number, count = 8) {
    for (let i = 0; i < count; i++) {
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.035 + Math.random() * 0.04, 6, 5),
        new THREE.MeshBasicMaterial({ color: i % 4 === 0 ? "#fffbd4" : i % 3 === 0 ? "#ffc04e" : "#ff672d" }));
      const origin = from.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.9,
        Math.random() * 0.30, (Math.random() - 0.5) * 0.9));
      mesh.position.copy(origin);
      this.scene.add(mesh);
      this.emberGather.push({ mesh, from: origin, ownerId, progress: -i * 0.045,
        duration: 0.58, offset: Math.random() * Math.PI * 2 });
    }
  }

  private emberChargeVisual(ownerId: number, ttl = 0.64) {
    const fighter = this.entities.get(ownerId);
    if (!(fighter instanceof Fighter)) return;
    const mat = new THREE.MeshBasicMaterial({ color: "#fff9e5", transparent: true, opacity: 0.95, depthWrite: false });
    const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.18, 14, 12), mat);
    fighter.model.castPoint.add(sphere);
    this.emberCharge.push({ ownerId, mesh: sphere, ttl, max: ttl });
  }

  /** Local mesh for replicated, brief white-hot ignition beam. */
  private emberBeamVisual(from: THREE.Vector3, to: THREE.Vector3) {
    const length = Math.max(0.1, from.distanceTo(to));
    const direction = to.clone().sub(from).normalize();
    const root = new THREE.Group();
    root.position.copy(from).add(to).multiplyScalar(0.5);
    root.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
    const shell = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.48, length, 14, 1, true),
      new THREE.MeshBasicMaterial({ color: "#ff8f33", transparent: true, opacity: 0.55,
        depthWrite: false, side: THREE.DoubleSide }));
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.24, length, 12, 1, true),
      new THREE.MeshBasicMaterial({ color: "#fff9d9", transparent: true, opacity: 0.95,
        depthWrite: false, side: THREE.DoubleSide }));
    root.add(shell, core);
    this.scene.add(root);
    this.emberBeams.push({ visual: root, ttl: 0.38, max: 0.38 });
  }

  private updateEmberFire(dt: number) {
    for (const p of this.emberGather) {
      p.progress += dt / p.duration;
      if (p.progress >= 1) { this.scene.remove(p.mesh); continue; }
      if (p.progress < 0) continue;
      const caster = this.entities.get(p.ownerId);
      const target = caster instanceof Fighter
        ? caster.model.castPoint.getWorldPosition(new THREE.Vector3())
        : p.from.clone().add(new THREE.Vector3(0, 1.5, 0));
      const u = Math.max(0, Math.min(1, p.progress));
      const ease = u * u * (3 - 2 * u);
      p.mesh.position.copy(p.from).lerp(target, ease);
      p.mesh.position.y += Math.sin(Math.PI * u) * 0.70;
      p.mesh.position.x += Math.sin(u * Math.PI * 5 + p.offset) * 0.22 * (1 - u);
      p.mesh.position.z += Math.cos(u * Math.PI * 5 + p.offset) * 0.22 * (1 - u);
      p.mesh.scale.setScalar(Math.max(0.12, 1 - u * 0.70));
    }
    this.emberGather = this.emberGather.filter(p => p.progress < 1);
    for (const orb of this.emberCharge) {
      orb.ttl -= dt;
      const t = 1 - Math.max(0, orb.ttl) / orb.max;
      orb.mesh.scale.setScalar(0.3 + 1.0 * Math.sin(Math.PI * t));
      if (orb.ttl <= 0) orb.mesh.parent?.remove(orb.mesh);
    }
    this.emberCharge = this.emberCharge.filter(o => o.ttl > 0);
    for (const b of this.emberBeams) {
      b.ttl -= dt;
      b.visual.scale.x = b.visual.scale.z = Math.max(0.05, b.ttl / b.max);
      if (b.ttl <= 0) this.scene.remove(b.visual);
    }
    this.emberBeams = this.emberBeams.filter(b => b.ttl > 0);
    for (const p of this.emberPatches) {
      p.ttl -= dt;
      p.visual.rotation.y += dt * 0.14;
      if (p.ttl <= 0) { this.scene.remove(p.visual); continue; }
      if (this.cfg.role === "client") continue;
      p.tick -= dt;
      if (p.tick > 0) continue;
      p.tick += 1;
      const owner = this.entities.get(p.ownerId);
      if (!(owner instanceof Fighter) || owner.isDown()) continue;
      for (const enemy of this.enemiesOf(owner)) {
        const diff = enemy.root.position.clone().sub(p.pos);
        const height = Math.abs(diff.y);
        diff.y = 0;
        if (diff.length() > p.radius + enemy.radius * 0.3 || height > 1.5) continue;
        // No stun, launch, or parry from passive ground fire.
        const fire: Attack = { ...owner.attacks.heavy, id: "ember_ground", type: "strike",
          dmg: 13, guard: 5, knock: 0, stun: 0, heavy: false,
          effect: "burn", effect_t: 3, effect_p: 10, no_parry: true };
        const dir = diff.lengthSq() > 0.01 ? diff.normalize() : new THREE.Vector3(0, 0, 1);
        this.applyHit(owner, enemy, fire, 1, enemy.chest(), dir, true);
      }
    }
    this.emberPatches = this.emberPatches.filter(p => p.ttl > 0);
  }

  private castEmberIgnition(f: Fighter, a: Attack) {
    // The cast is authoritative. Consume buffs/patches now; release the beam only
    // after animated embers have visibly travelled to the staff tip.
    const round = this.round, serial = f.swingSerial;
    const pos = f.root.position.clone();
    const burned = this.enemiesOf(f).filter((e): e is Fighter | Mob =>
      (e instanceof Fighter || e instanceof Mob) && !e.isDown() &&
      e.root.position.distanceTo(pos) <= 9 && e.status.has("burn"));
    const patches = this.emberPatches.filter(p => p.ownerId === f.id && p.pos.distanceTo(pos) <= 9);
    const bonus = Math.min(5, patches.length) * 30 + Math.min(4, burned.length) * 25;
    this.fxp("emberCharge", f.id, 0.64);
    if (patches.length) this.fxp("emberConsume", f.id, pos, 9);
    for (const enemy of burned) {
      this.fxp("emberGather", enemy.chest(), f.id, 9);
      enemy.status.consume("burn");
    }
    this.fxp("ring", pos, "#ff9b40", 2.0, 0.32, 0.90);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)),
      `GATHERING FLAMES +${bonus}`, "#ffe4a0", 0.9);
    this.snd("fireball", 0.60);
    this.later(0.60, () => {
      if (round !== this.round || f.isDown() || f.swingSerial !== serial) return;
      const start = f.model.castPoint.getWorldPosition(new THREE.Vector3());
      const toward = f.opponent && !f.opponent.isDown()
        ? f.opponent.chest().sub(start).normalize()
        : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
      const end = start.clone().addScaledVector(toward, 11);
      this.fxp("emberBeam", start, end);
      this.fxp("flash", start, "#fffdf0", 1.4, 0.27, 1.0);
      this.fxp("sparks", start, "#ffcf63", 72, 9);
      this.fxp("ring", f.root.position.clone(), "#ffd3a1", 2.5, 0.35, 0.9);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)),
        `FINAL IGNITION +${bonus}`, "#fff5bf", 1.05);
      this.snd("fireball", 1.0);
      const beamHit: Attack = { ...a, type: "strike", dmg: 240 + bonus,
        guard: 75, knock: 7, stun: 0.75, heavy: true,
        effect: "burn", effect_t: 4, effect_p: 20, no_parry: true };
      for (const enemy of this.enemiesOf(f)) {
        const rel = enemy.chest().sub(start);
        const projection = rel.dot(toward);
        if (projection < 0 || projection > 11) continue;
        const off = rel.addScaledVector(toward, -projection).length();
        if (off > 0.8 + enemy.radius) continue;
        this.applyHit(f, enemy, beamHit, f.atkPower, enemy.chest(), toward, true);
      }
    });
  }

  /** Teleport behind the target and kick, `repeat` times `interval` apart (alternating sides). */
  private phantom(f: Fighter, a: Attack) {
    const kicks = ["kk3_s", "kk2_s", "kk1_s", "kk4_s"];
    const power = f.atkPower;
    for (let i = 0; i < a.repeat; i++) this.laterCombo(f, i * a.interval, () => {
      const o = f.opponent;
      if (f.isDown() || f.state !== S.ATTACK || !o || o.isDown()) return;
      const from = f.root.position.clone();
      const d = o.root.position.clone().sub(from).setY(0);
      if (d.lengthSq() < 1e-4) d.set(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
      d.normalize();
      this.fxp("smoke", from, f.look.glow);
      this.snd("teleport", 0.7);
      f.teleport(o.root.position.clone().addScaledVector(d, 1.1));
      f.root.rotation.y = Math.atan2(-d.x, -d.z);
      f.poseOverride = kicks[i % kicks.length];
      this.fxp("smoke", f.root.position.clone(), f.look.glow);
      this.fxp("ring", f.root.position.clone().add(new THREE.Vector3(0, 0.1, 0)), f.look.glow, 1.4, 0.25, 0.8);
      this.applyHit(f, o, a, power, o.chest(), d.clone().negate(), false);
    });
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

  private applyHit(attacker: Entity | null, d: Entity, a: Attack, power: number, hitPos: THREE.Vector3, dir: THREE.Vector3, ranged: boolean): string {
    // Includes Zarek's launch/finisher (their style labels differ from the base skill).
    const scaledAttack = attacker instanceof Fighter && attacker.isContinuousComboActive() &&
      !ranged && attacker.comboDamageMult < 1
      ? { ...a, dmg: a.dmg * attacker.comboDamageMult } : a;
    const result = d.receiveHit(attacker, scaledAttack, power);
    const glow = attacker instanceof Fighter ? attacker.look.glow : attacker instanceof Mob ? attacker.def.color : "#ffffff";
    const heavy = a.heavy || a.id === "l3";
    const shieldPos = d instanceof Fighter ? d.model.shieldNode.getWorldPosition(new THREE.Vector3()) : hitPos;
    switch (result) {
      case "kaizen_guard_clash": {
        // KAIZEN_GUARD_CLASH_V8: successful spinning-block contact clashes with a
        // melee attack. The attacker recoils; Kaizen remains guarding. Guard was
        // already drained in receiveHit(), so enough pressure can still break it.
        if (attacker instanceof Fighter) {
          // A clash against Kaizen's rotating chain counts as a real weapon clash
          // for Zarek's round-based Clash Counter.
          if (attacker.kit === "glaive") {
            attacker.clashMomentum += 1;
            this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)),
              `CLASH ${attacker.clashMomentum} • ${Math.min(2, 1 + Math.min(5, attacker.clashMomentum) * .2).toFixed(1)}x BASIC SPD`,
              "#a6efff", 0.8);
            this.fxp("lightning", attacker.chest(), "#6acfff");
          }
          attacker.clashRecoil();
        }
        this.snd("clash", 0.9);
        this.fxp("sparks", shieldPos, "#fff0c2", 38, 8);
        this.fxp("sparks", shieldPos, "#d65a6e", 12, 5);
        this.fxp("flash", shieldPos, "#ffe0b0", 0.46, 0.15, 0.85);
        this.fxp("ring", shieldPos, "#ffe0b0", 1.7, 0.25, 0.8);
        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.5, 0)),
          "CLASH!", "#ffe08a", 1.1);
        this.add_trauma(0.3);
        if (!(attacker instanceof Fighter && attacker.isContinuousComboActive())) this.hitStop(0.09);
        break;
      }
      case "hit": case "crit": case "ko": {
        const crit = d.lastCrit;
        this.hitSound(attacker, a, crit);
        this.fxp("sparks", hitPos, glow, heavy ? 30 : 18, heavy ? 8 : 6, dir);
        this.fxp("flash", hitPos, glow, heavy ? 0.45 : 0.3, 0.14, 0.8);
        if (a.heavy) this.fxp("ring", hitPos, glow, 2.2, 0.35, 0.9);
        const label = this.plat && d instanceof Fighter ? `${Math.round(d.lastDamage)}%` : `${Math.round(d.lastDamage)}`;
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), `${label}${crit ? "!" : ""}`,
          d.team === (this.local?.team ?? 0) && !this.isDuel() ? "#ff7b7b" : crit ? "#ffb347" : "#ffffff", crit ? 1.5 : 1);
        if (attacker instanceof Fighter) {
          // Existing equipment lifesteal still applies. Veyr additionally drains 50%
          // of ACTUAL damaging hits while his 5-second Blood Frenzy is active.
          // This case only includes successful hits: blocked/parried/clashed hits never heal.
          const frenzyLeech = attacker.kit === "sickle" && attacker.bloodFrenzyT > 0 ? 0.50 : 0;
          const totalLeech = attacker.lifesteal + frenzyLeech;
          if (totalLeech > 0) attacker.heal(d.lastDamage * totalLeech);
          if (attacker.kit === "sickle" && !ranged) this.gainBloodlust(attacker, a.style === "sickle_carrion" ? 5 : 25); // VEYR_BLOODLUST_CARRION_V7
        }
        if (attacker instanceof Fighter && attacker.look.element === "earth") this.fxp("rocks", d.root.position.clone(), heavy ? 12 : 6, heavy ? 0.9 : 0.6);
        const big = this.isDuel() || attacker instanceof Mob ? 1 : 0.5;
        this.add_trauma((a.heavy ? 0.5 : heavy ? 0.3 : 0.18) * big);
        this.hitStop(a.heavy ? 0.11 : heavy ? 0.07 : 0.045);
        if (result === "ko" && d instanceof Mob) this.creditMobKill(attacker instanceof Fighter ? attacker : null, d);
        const info = STATUS[a.effect as StatusKind];
        if (info && result !== "ko" && this.time - (this.statusLabelAt.get(d) ?? -9) > 1.2) {
          this.statusLabelAt.set(d, this.time);
          const ss: Record<string, string> = { burn: "burn", paralyze: "shock", poison: "poison", bleed: "bleed" };
          if (ss[a.effect]) this.snd(ss[a.effect], 0.6);
          this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.95, 0)), info.label, info.color, 0.85);
        }
        break;
      }
      case "blocked":
        this.snd("block", 0.7);
        this.fxp("sparks", shieldPos, "#ffd27a", 16, 5, dir.clone().negate().add(new THREE.Vector3(0, 0.3, 0)));
        this.fxp("flash", shieldPos, "#ffd980", 0.35, 0.1, 0.6);
        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.4, 0)), "BLOCK", "#c9d3e6", 0.7);
        if (!ranged && attacker instanceof Fighter) attacker.model.recoil = 0.6;
        this.add_trauma(0.14);
        this.hitStop(0.04);
        break;
      case "parry":
        if (!ranged && attacker instanceof Fighter && attacker.onComboParried()) {
          this.delayComboFollowups(attacker, 0.20);
          this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)),
            "COMBO -10% • +0.2s", "#b8eaff", 0.82);
        } else if (a.parry_stun && attacker instanceof Fighter) {
          // Single-hit vulnerability (Gale, etc.) remains as it was.
          attacker.stagger(a.parry_stun);
          this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)), "STUNNED", "#ffe066", 1.1);
        } else if (!ranged && attacker instanceof Fighter) attacker.stagger(0.95);
        else if (!ranged && attacker instanceof Mob) attacker.receiveHit(d, { ...a, dmg: 0, knock: 4 }, 0);
        this.snd("parry", 0.9);
        this.fxp("sparks", shieldPos, "#aee9ff", 40, 9);
        this.fxp("flash", shieldPos, "#b3f2ff", 0.5, 0.2, 0.9);
        this.fxp("ring", shieldPos, "#b3f2ff", 1.6, 0.35, 0.9);
        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "PARRY!", "#8fe6ff", 1.4);
        this.add_trauma(0.4);
        // Keep the classic dramatic PARRY slow motion, slightly stronger for
        // continuing combos. Stun never replaces the +0.20s combo continuation.
        this.hitStop(attacker instanceof Fighter && attacker.isContinuousComboActive() ? 0.46 : 0.35,
          attacker instanceof Fighter && attacker.isContinuousComboActive() ? 0.17 : 0.30);
        break;
      case "counter": {
        const df = d as Fighter;
        this.fxp("num", df.chest().add(new THREE.Vector3(0, 0.6, 0)), "COUNTER!", "#ff9aa8", 1.4);
        this.fxp("slashes", (attacker ?? df).root.position.clone(), df.look.glow);
        if (attacker) {
          if (df.kit === "sickle" && df.bloodFeintT > 0) {
            df.bloodFeintT = 0;
            const d = attacker.root.position.clone().sub(df.root.position).setY(0).normalize();
            const side = new THREE.Vector3(-d.z, 0, d.x);
            const to = attacker.root.position.clone().addScaledVector(d, 0.95).addScaledVector(side, 0.45);
            this.fxp("smoke", df.root.position.clone(), "#c62a54");
            df.teleport(to);
            this.fxp("slashes", attacker.root.position.clone(), "#ff496e");
            const counter = { ...df.attacks.heavy, dmg: 95, heavy: true, stun: 0.36, no_parry: true, effect: "", knock: 2.5 } as Attack;
            this.applyHit(df, attacker, counter, df.dmgMult, attacker.chest(), d.clone().negate(), false);
          } else {
            const counter = { ...df.attacks.heavy, dmg: 180, heavy: true, stun: 0.8 } as Attack;
            this.applyHit(df, attacker, counter, df.dmgMult, attacker.chest(), dir.clone().negate(), false);
          }
        }
        break;
      }
      case "guard_break":
        this.fxp("sparks", hitPos, "#ffb347", 40, 9);
        this.fxp("flash", hitPos, "#ffb34d", 0.5, 0.2, 0.9);
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.55, 0)), "GUARD BREAK", "#ff8a50", 1.2);
        this.snd("guard_break", 0.9);
        this.add_trauma(0.55);
        this.hitStop(0.12);
        break;
      case "warded":
        this.fxp("flash", hitPos, "#80d9ff", 0.5, 0.15, 0.7);
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "ABSORBED", "#8fe6ff", 0.8);
        this.snd("ward", 0.6);
        break;
      case "miss":
        this.fxp("num", hitPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "MISS", "#c9d3e6", 0.8);
        break;
    }
    return result;
  }

  /** Blood Frenzy lasts five seconds: meter stays full and grants 50% hit lifesteal. */
  private activateBloodFrenzy(f: Fighter) {
    if (f.isDown()) return;
    f.bloodlust = 100;
    f.bloodFrenzyT = 5;
    this.fxp("flash", f.chest(), "#ff3e67", 0.8, 0.4, 1);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)), "BLOOD FRENZY", "#ff587b", 1.1);
    this.snd("rage", 0.7);
  }

  /** Veyr melee hits build Bloodlust, activating Frenzy upon reaching 100. */
  private gainBloodlust(f: Fighter, points: number) {
    if (f.bloodFrenzyT > 0 || f.isDown()) return;
    f.bloodlust = Math.min(100, f.bloodlust + points);
    if (f.bloodlust >= 100) this.activateBloodFrenzy(f);
  }

  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {
    // Actual attack-vs-attack contact ONLY. Save skill before clashRecoil clears it.
    for (const f of [a, b]) if (f.kit === "glaive") {
      f.clashMomentum += 1; // one genuine weapon clash, one round-only count
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)),
        `CLASH ${f.clashMomentum} • ${Math.min(2, 1 + Math.min(5, f.clashMomentum) * .2).toFixed(1)}x BASIC SPD`, "#a6efff", 0.8);
      this.fxp("lightning", f.chest(), "#6acfff");
    }
    // VEYR_BLOODLUST_CARRION_V7: reward a genuine Carrion Sweep weapon collision.
    if ([a, b].some(f => f.kit === "sickle" && f.atk?.style === "sickle_carrion")) {
      this.fxp("slashes", pos, "#ff527f");
      this.fxp("sparks", pos, "#ffa4bb", 22, 7);
      this.fxp("flash", pos, "#ff6088", 0.45, 0.16, 0.85);
    }
    a.clashRecoil();
    b.clashRecoil();
    this.fxp("sparks", pos, "#fff2c0", 50, 10);
    this.fxp("sparks", pos, a.look.glow, 16, 7);
    this.fxp("sparks", pos, b.look.glow, 16, 7);
    this.fxp("flash", pos, "#fff2cc", 0.55, 0.18, 0.95);
    this.fxp("ring", pos, "#ffe699", 3, 0.45, 0.9);
    this.fxp("num", pos.clone().add(new THREE.Vector3(0, 0.45, 0)), "CLASH!", "#ffe08a", 1.3);
    this.snd("clash", 1);
    this.add_trauma(0.45);
    if (!a.isContinuousComboActive() && !b.isContinuousComboActive()) this.hitStop(0.13);
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
  /** A fighter crossed the blast zone: burst at the screen edge, shake, lose a stock. */
  private onBlast(f: Fighter) {
    const b = STAGE.blast;
    const p = f.root.position;
    const at = new THREE.Vector3(Math.max(b.l + 1.5, Math.min(b.r - 1.5, p.x)), Math.max(b.b + 1.5, Math.min(b.t - 1.5, p.y)), 0);
    const dir = new THREE.Vector3(0, 0, 0).sub(at).normalize();
    this.fxp("explosion", at, f.look.glow, 2.2);
    this.fxp("sparks", at, f.look.glow, 50, 12, dir);
    this.fxp("flash", at, "#ffffff", 1.2, 0.25, 0.95);
    this.fxp("ring", at, f.look.glow, 4, 0.5, 0.9);
    this.add_trauma(0.8);
    this.hitStop(0.12, 0.15);
    if (f.stocks > 1) this.fxp("num", new THREE.Vector3(at.x * 0.7, Math.min(at.y, 8) * 0.7 + 2, 0), `${f.look.name} -1`, "#ffd1a8", 1.1);
  }

  /** Projectiles stop on the main island (from the side or below). */
  private hitsStage(p: THREE.Vector3) {
    const m = STAGE.plats[0];
    return p.x > m.x0 && p.x < m.x1 && p.y < m.y - 0.05 && p.y > m.y - 4;
  }

  /** 1v1 modes (3D duel and platform brawl). */
  private isDuel() { return this.cfg.mode === "duel" || this.cfg.mode === "brawl"; }

  /** Record a round win and synchronize the series score with online guests. */
  private awardRound(team: number): boolean {
    this.matchWins[team]++;
    this.emit(["roundScore", this.matchWins[0], this.matchWins[1]]);
    return this.matchWins[team] >= 2;
  }

  private onFighterKo(f: Fighter) {
    this.snd("ko", 0.9);
    if (this.isDuel()) {
      if (this.roundOver) return;
      this.roundOver = true;
      const winner = this.fighters.find((x) => x !== f)!;
      for (const x of this.fighters) x.brain = null;
      this.add_trauma(0.8);
      this.hitStop(0.9, 0.25);
      this.later(0.4, () => {
        winner.win();
        const matchFinished = this.awardRound(winner.team);
        const [a, b] = this.matchWins;
        const iWon = winner.owner === this.cfg.localPeer;
        const name = winner.look.name;
        if (!matchFinished) {
          this.banner(`${name.toUpperCase()} WINS ROUND ${a + b}`, "#ffe08a", `Score ${a} - ${b} | Next round coming up`, 1.8);
          this.later(2.5, () => this.startRound());
          return;
        }
        // Only the series victor earns gold and a ranked/wager result.
        if (!isCpu(winner.owner)) this.sendReward(winner.owner, "duel", WIN_GOLD);
        this.onEvent({ type: "result", winner: winner.team });
        this.emit(["result", winner.team]);
        const text = this.cfg.role === "offline" ? (iWon ? "VICTORY" : "DEFEAT") : `${name.toUpperCase()} WINS`;
        this.over(text, `Final Score: ${a} - ${b} | Press R or click Rematch`, iWon || this.cfg.role !== "offline" ? "#ffe08a" : "#ff7b7b");
        this.canRestart = true;
      });
    } else if (this.cfg.mode === "team") {
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "DOWN!", "#ff7b7b", 1.1);
      if (this.roundOver || !this.fighters.filter((x) => x.team === f.team).every((x) => x.isDown())) return;
      this.roundOver = true;
      const winner = 1 - f.team;
      for (const x of this.fighters) x.brain = null;
      this.hitStop(0.9, 0.25);
      this.later(0.5, () => {
        for (const x of this.fighters) if (x.team === winner) x.win();
        const matchFinished = this.awardRound(winner);
        const [a, b] = this.matchWins;
        const side = winner === 0 ? "Blue" : "Red";
        if (!matchFinished) {
          this.banner(`TEAM ${side.toUpperCase()} WINS ROUND ${a + b}`, "#ffe08a", `Score ${a} - ${b} | Next round coming up`, 1.8);
          this.later(2.5, () => this.startRound());
          return;
        }
        for (const x of this.fighters) if (x.team === winner && !isCpu(x.owner)) this.sendReward(x.owner, "team", WIN_GOLD);
        this.onEvent({ type: "result", winner });
        this.emit(["result", winner]);
        const mine = this.local?.team ?? 0;
        this.over(winner === mine ? "VICTORY" : "DEFEAT", `Team ${side} wins | Final Score: ${a} - ${b}`, winner === mine ? "#ffe08a" : "#ff7b7b");
        this.canRestart = true;
      });
    } else {
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "DOWN!", "#ff7b7b", 1.1);
      if (this.fighters.every((x) => x.isDown())) {
        this.payEarned();
        this.phase = "over";
        this.later(1.0, () => {
          this.over("GAME OVER", `Reached wave ${this.wave}  -  ${this.kills} kills`, "#ff7b7b");
          this.canRestart = true;
        });
      }
    }
  }

  /** Gold earned from kills this wave, per player; paid out at wave clear and game over. */
  private earned = new Map<string, number>();

  private payEarned() {
    for (const [peer, g] of this.earned) if (g > 0) this.sendReward(peer, "survival", g);
    this.earned.clear();
  }

  private sendReward(peer: string, reason: "duel" | "team" | "survival", gold: number) {
    if (peer === this.cfg.localPeer) this.onEvent({ type: "reward", reason, gold });
    else this.net?.sendTo(peer, { t: "reward", r: reason, g: gold });
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
        this.payEarned();
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
      if (msg.t === "hello") { this.lateJoin(from, msg); return; }
      if (msg.t === "synced") { this.sendSync(from); return; }
      if (msg.t === "in") {
        let b = this.remoteBrains.get(from);
        if (!b) { b = new RemoteBrain(); this.remoteBrains.set(from, b); }
        b.last = msg.i;
        if (msg.i.skill) b.skills.push({ key: msg.i.skill, mx: msg.i.mx, mz: msg.i.mz });
        if (msg.i.dx || msg.i.dz) b.dashes.push([msg.i.dx, msg.i.dz]);
      } else if (msg.t === "perk") {
        const opts = this.perkWait.get(from);
        if (opts) { this.applyPerk(from, opts[msg.i] ?? opts[0]); this.perkWait.delete(from); }
      }
      return;
    }
    if (msg.t === "sync") {
      for (const ev of msg.e) this.applyEvent(ev);
      [this.wave, this.kills, this.phase] = msg.s;
      return;
    }
    if (msg.t === "snap") {
      for (const ev of msg.e) this.applyEvent(ev);
      for (const s of msg.f) (this.entities.get(s[0]) as Fighter | undefined)?.applySnapshot?.(s);
      for (const s of msg.m) (this.entities.get(s[0]) as Mob | undefined)?.applySnapshot?.(s);
      [this.wave, this.kills, this.phase] = msg.s;
    } else if (msg.t === "perks") {
      this.onEvent({ type: "perks", options: msg.o });
    } else if (msg.t === "reward") {
      this.onEvent({ type: "reward", reason: msg.r, gold: msg.g });
    }
  }

  /** A player opened the room code mid-match: survival lets them drop in, others say busy. */
  private lateJoin(peer: string, msg: Msg) {
    const reject = (reason: string) => this.net?.sendTo(peer, { t: "busy", reason });
    if (this.cfg.mode !== "survival") return reject("That room is in the middle of a match. Try again when it ends.");
    if (this.cfg.players.some((p) => p.peer === peer)) return;
    if (this.cfg.players.length >= 4) return reject("That survival run is full (4 players).");
    const slot: PlayerSlot = { peer, name: String(msg.name ?? "Player").slice(0, 16), char: msg.char ?? 0, loadout: msg.loadout, emblem: msg.emblem };
    this.cfg.players.push(slot);
    this.net?.sendTo(peer, { t: "start", cfg: { mode: this.cfg.mode, players: this.cfg.players }, late: true });
  }

  /** The late joiner's game is up: send it everything that exists, then add its fighter. */
  private sendSync(peer: string) {
    const ev: any[] = [];
    for (const f of this.fighters) {
      const s = this.cfg.players.find((p) => p.peer === f.owner);
      ev.push(["spawnF", f.id, f.charIndex, f.team, f.owner, s?.name ?? f.look.name, +f.root.position.x.toFixed(2), +f.root.position.z.toFixed(2), f.root.rotation.y, s?.loadout ?? null, s?.emblem ?? null]);
    }
    for (const m of this.mobs) if (!m.dead) ev.push(["spawnM", m.id, m.type, m.elite ? 1 : 0, m.hpMult ?? 1, +m.root.position.x.toFixed(2), +m.root.position.z.toFixed(2)]);
    this.net?.sendTo(peer, { t: "sync", e: ev, s: [this.wave, this.kills, this.phase] });
    const slot = this.cfg.players.find((p) => p.peer === peer);
    if (!slot || this.fighters.some((f) => f.owner === peer)) return;
    const anchor = this.fighters.find((f) => !f.isDown())?.root.position ?? new THREE.Vector3();
    const f = this.spawnFighter(slot, 0, anchor.clone().add(new THREE.Vector3(1.5, 0, 1.5)), 0);
    f.invulnT = 2;
    f.brain = this.brainFor(f);
    this.fxp("smoke", f.root.position.clone(), f.look.glow);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), `${slot.name} joined!`, "#9dff9a", 1.1);
  }

  private applyEvent(ev: any[]) {
    switch (ev[0]) {
      case "reset": this.clearAll(); break;
      case "spawnF": {
        const f = this.spawnFighter({ peer: ev[4], name: ev[5], char: ev[2], loadout: ev[9] ?? undefined, emblem: ev[10] ?? undefined }, ev[3], new THREE.Vector3(ev[6], 0, ev[7]), ev[8], ev[1]);
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
        if (ev[2] === "bomb") { p.gravity = BOMB_GRAVITY; p.life = 3; }
        this.scene.add(p.group);
        this.projectiles.push(p);
        break;
      }
      case "projHunt": {
        const p = this.projectiles.find((x) => x.id === ev[1]);
        if (p) { p.target = this.entities.get(ev[2]) ?? null; p.steering = true; p.finalBlade = ev[3] === 1; p.age = ev[4] ?? p.age; }
        break;
      }
      case "bloodFestival": {
        const { visual, blades } = makeBloodFestivalVisual(ev[3]);
        const center = v3(ev[2]);
        visual.position.copy(center);
        this.scene.add(visual);
        this.bloodFestivals.push({ id: ev[1], owner: null, team: ev[6], center,
          radius: ev[3], time: ev[4], age: 0, visual, blades, captured: new Set(), contact: new Map() });
        break;
      }
      case "bloodFestivalEnd": {
        const ring = this.bloodFestivals.find(x => x.id === ev[1]);
        if (ring) { this.scene.remove(ring.visual); this.bloodFestivals = this.bloodFestivals.filter(x => x !== ring); }
        break;
      }
      case "projEnd": { const p = this.projectiles.find((x) => x.id === ev[1]); if (p) p.done = true; break; }
      case "trap": {
        const t: Trap = { id: ev[1], kind: ev[2], owner: null, team: -1, atk: null as any, power: 0, pos: v3(ev[3]), mesh: buildTrap(ev[2], ev[4]), arm: 0, life: 99, t: 0 };
        t.mesh.position.copy(t.pos);
        this.scene.add(t.mesh);
        this.traps.push(t);
        break;
      }
      case "trapEnd": {
        const t = this.traps.find((x) => x.id === ev[1]);
        if (t) { this.scene.remove(t.mesh); this.traps = this.traps.filter((x) => x !== t); }
        break;
      }
      case "banner": this.onEvent({ type: "banner", text: ev[1], color: ev[2], sub: ev[3], hold: ev[4] }); break;
      case "over": this.onEvent({ type: "over", text: ev[1], sub: ev[2], color: ev[3] }); break;
      case "result": this.onEvent({ type: "result", winner: ev[1] }); break;
      case "roundScore": this.matchWins = [ev[1], ev[2]]; break;
    }
  }

  // --- camera -------------------------------------------------------------------------------
  private updateCamera(dt: number) {
    const cam = this.camera;
    let goal: THREE.Vector3, look: THREE.Vector3;
    const me = this.local ?? this.fighters[0];
    if (!me) { cam.position.set(0, 6, 10); cam.lookAt(0, 1, 0); return; }
    if (this.plat) {
      const live = this.fighters.filter((f) => !f.out && !f.isDown());
      const pts = (live.length ? live : this.fighters).map((f) => f.root.position);
      const box = new THREE.Box3().setFromPoints(pts);
      const b = STAGE.blast;
      const cx = THREE.MathUtils.clamp((box.min.x + box.max.x) / 2, b.l + 8, b.r - 8);
      const cy = THREE.MathUtils.clamp((box.min.y + box.max.y) / 2, -1, 6);
      const spread = Math.max(box.max.x - box.min.x, (box.max.y - box.min.y) * 1.6);
      const narrow = Math.max(1, 1.5 / Math.max(this.camera.aspect, 0.3));
      const dist = THREE.MathUtils.clamp(9 + spread * 0.75, 11, 26) * narrow;
      goal = new THREE.Vector3(cx * 0.85, cy + 2.4 + dist * 0.08, dist);
      look = new THREE.Vector3(cx * 0.85, cy + 1.1, 0);
      // Turn bodies a little toward the camera so faces read.
      for (const f of this.fighters) f.viewBias = -f.facing * 0.45;
    } else if (this.cfg.mode === "duel" && this.fighters.length >= 2) {
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
    const other = this.isDuel() ? this.fighters.find((f) => f !== me) : null;
    const info = (f: Fighter) => ({ id: CHARACTERS[f.charIndex].id, name: f.look.name + (isCpu(f.owner) && f.owner !== "cpu" ? " (CPU)" : ""), hp: f.hp, maxHp: f.maxHp, guard: f.guard, maxGuard: f.maxGuard, down: f.isDown(), glow: f.look.glow,
      pct: f.pct, stocks: f.stocks, out: f.out, team: f.team, status: f.status.kinds(), bloodlust: f.bloodlust, bloodFrenzyT: f.bloodFrenzyT, bloodFestivalT: f.bloodFestivalT, clashMomentum: f.clashMomentum, chainBindT: f.chainBindT,
      chainBindKind: f.chainBindKind }); // KAIZEN_PREDATOR_HOOK_V9
    return {
      mode: this.cfg.mode,
      plat: this.plat,
      matchWins: [this.matchWins[0], this.matchWins[1]] as [number, number],
      roundLabel: this.matchWins.some((wins) => wins >= 2)
        ? "FINAL"
        : `ROUND ${this.matchWins[0] + this.matchWins[1] + 1}`,
      all: this.plat ? this.fighters.map((f) => ({ ...info(f), me: f === me, cpu: isCpu(f.owner) })) : [],
      me: me ? info(me) : null,
      other: other ? { ...info(other), tag: isCpu(other.owner) ? `CPU - ${LEVELS[this.cfg.difficulty ?? 1]}` : "" } : null,
      team: !this.isDuel() ? this.fighters.filter((f) => f !== me && f.team === me?.team).map(info) : [],
      foes: this.cfg.mode === "team" ? this.fighters.filter((f) => f.team !== me?.team).map(info) : [],
      atkLock: me && me.attacks.l1.type !== "melee" ? { t: me.atkLock, max: RANGED_COMBO_REST[me.kit] ?? 1.2 } : null,
      dash: me ? { t: me.dashCd, max: DASH_CD } : null,
      skills: me ? ["z", "x", "c"].map((k) => {
        // In the air, show the air version of a skill when it has one.
        const a = !me.onGround && me.attacks[k + "_air"] ? me.attacks[k + "_air"] : me.attacks[k];
        // KAIZEN_BIND_ZX_V6: bound follow-ups have no extra cooldown and replace Z/X icons.
        // KAIZEN_PREDATOR_HOOK_V9: only X can resolve Predator's Hook. All
        // other skills are locked until pull or timeout; V still uses Z/X.
        if (me.kit === "chainblade" && me.chainBindT > 0 && me.chainBindKind === "x") {
          if (k === "x") return { key: k, id: "backward", name: "PULL (X)", cd: 0, max: 1 };
          return { key: k, id: a.id, name: a.name + " (Locked)", cd: me.chainBindT, max: 4 };
        }
        if (me.kit === "chainblade" && me.chainBindT > 0 && (k === "z" || k === "x"))
          return { key: k, id: k === "z" ? "forward" : "backward", name: k === "z" ? "Forward" : "Backward", cd: 0, max: 1 };
        // During Blood Festival all special skills are locked, regardless of remaining cooldown.
        if (me.bloodFestivalT > 0) return { key: k, id: a.id, name: a.name + " (Locked)", cd: me.bloodFestivalT, max: 6 };
        // Powder keg out: the slot becomes its trigger.
        if (a.style === "bloodsickle" && me.sickleOut) return { key: k, id: a.id + "_redirect", name: "Redirect Sickle", cd: 0, max: 1 };
        if (a.type === "barrel" && me.barrelOut) return { key: k, id: a.id + "_trigger", name: "Detonate", cd: 0, max: 1 };
        return { key: k, id: a.id, name: a.name, cd: me.cooldowns[k], max: me.attacks[k].cd * me.cdMult };
      }) : [],
      kit: me?.kit ?? "", element: me?.look.element ?? "",
      wave: this.wave, kills: this.kills, phase: this.phase,
      mobs: this.mobs.filter((m) => !m.dead).length,
      boss: boss ? { name: boss.def.name, hp: boss.hp, maxHp: boss.maxHp } : null,
      canRestart: this.canRestart && this.cfg.role !== "client",
    };
  }
}
