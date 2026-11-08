// BALANCE_KIRA_KAEDE_PATTERN_AI_AIR_ICON_20261107_V1
// KAIZEN_PARRY_SPIN_SLOW_REVERSE_V10
// FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V2
// FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V1
// NESA_HEART_SMASH_V4
// FIGHT_ROYALE_ZAREK_PROPORTIONATE_GLAIVE_V1
// FIGHT_ROYALE_SIGNATURE_POSES_V2
// FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1
// MELEE_PROJECTILE_SPRINT_V1_NOV06
// CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06
// Procedural cel-shaded fighter. Faces +Z. Right hand (-X side) holds the main weapon.
// `look` (see roster.ts) picks the outfit, hair style, hat, weapon and colors.
// Posed by blend() every frame with joint rotations from a pose (see kits.ts).
import * as THREE from "three";
import * as M from "./mat";
import { coneSheet, strand } from "./meshgen";
import type { Look } from "./roster";
import type { Pose } from "./kits";
import { loadVrm, VrmRig } from "./vrm";

// ZENITH_QIANG_CHOREOGRAPHY_V8_20261108 — EDIT THESE CONSTANTS TO TUNE THE VISUAL FEEL.
// These are cosmetic world-space/pose offsets ONLY. No gameplay movement, hitboxes or attack timings.
const ZENITH_V8_MOTION = {
  stanceDepth: 0.045,        // meters of visual knee/hip drop on committed strikes
  stepDistance: 0.082,       // meters of MODEL-only alternating lead-foot weight shift
  lungeStep: 0.19,          // extra MODEL-only drive on the fifth thrust
  windupSeconds: 0.085,     // slow, readable spear retraction/anticipation
  snapSeconds: 0.088,       // rapid tip acceleration when the attack becomes active
  overshootSeconds: 0.052,  // short follow-through past the line
  settleSeconds: 0.14,      // controlled retract / ready position
  poseEntrySeconds: 0.048,  // blend continuity when switching attack keys
  tipArc: 1.0,              // 0=straight shortcut, 1=full rising/sweeping tip curves
  spearFlower: 0.045,       // small circular redirect between attacks (radians)
  idleFigureEight: 0.044,   // subtle idle tip orbit, NOT a spinning staff
  idleBob: 0.022,           // idle tip vertical sway (meters)
  walkCounterSway: 0.065,   // spear tip moves opposite the stepping leg
  leadGripGuard: 0.32,      // lead hand is 32 cm toward the spearhead from rear grip
  leadGripExtension: 0.12,  // slides toward the rear hand while thrusting
  torsoYaw: 0.24,          // torso rotation driving the blow (radians)
  hipYaw: 0.12,            // pelvic follow-through (radians)
  thrustOvershoot: 0.032,  // meters of extra tip drive just after the snap
} as const;

const PI = Math.PI;
const TAU = PI * 2;
const SKIN = "#ffe9df";
const SKIN_SHADE = new THREE.Color(1.0, 0.82, 0.82);
const METAL_SHADE = new THREE.Color(0.62, 0.66, 0.85);
const BROWN = "#5a3a2a";
const PEARL = "#fff8ee";
const HEAD_R = 0.19;
const HIP = 0.84;
/** Weapon size on VRoid bodies relative to the chibi-sized originals. */
const VRM_WEAPON_SCALE = 0.68;
const CAP_C = new THREE.Vector3(0, 0.035, -0.035);
const JOINTS = ["torso", "head", "arm_r", "hand_r", "arm_l", "hand_l", "leg_l", "leg_r"] as const;

/** Body-type proportions applied on top of the shared rig (multipliers). */
const BODY = {
  m: { height: 1.05, shoulder: 1.12, torso: 1.1, hip: 0.94, limb: 1.12, head: 0.9, bust: false },
  f: { height: 0.97, shoulder: 0.9, torso: 0.92, hip: 1.1, limb: 0.9, head: 0.95, bust: true },
};

type V3 = [number, number, number];
const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
const _up = new THREE.Vector3(0, 1, 0);
const col = (c: string) => new THREE.Color(c);

const geoCache = new Map<string, THREE.BufferGeometry>();
function cached(key: string, make: () => THREE.BufferGeometry) {
  let g = geoCache.get(key);
  if (!g) { g = make(); geoCache.set(key, g); }
  return g;
}
export const sphere = (r: number, seg = 24) => cached(`s${r}|${seg}`, () => new THREE.SphereGeometry(r, seg, Math.max(4, seg / 2)));
export const cyl = (t: number, b: number, h: number, seg = 20) => cached(`c${t}|${b}|${h}|${seg}`, () => new THREE.CylinderGeometry(t, b, h, seg, 1));
export const cap = (r: number, h: number) => cached(`p${r}|${h}`, () => new THREE.CapsuleGeometry(r, Math.max(h - 2 * r, 0.001), 6, 16));
export const box = (x: number, y: number, z: number) => cached(`b${x}|${y}|${z}`, () => new THREE.BoxGeometry(x, y, z));
export const torus = (inner: number, outer: number) =>
  cached(`t${inner}|${outer}`, () => new THREE.TorusGeometry((inner + outer) / 2, (outer - inner) / 2, 8, 32).rotateX(PI / 2));

export function pivot(parent: THREE.Object3D, pos: V3 | THREE.Vector3 = [0, 0, 0], rot: V3 = [0, 0, 0]): THREE.Group {
  const g = new THREE.Group();
  g.rotation.order = "YXZ";
  if (Array.isArray(pos)) g.position.set(...pos); else g.position.copy(pos);
  g.rotation.set(...rot);
  parent.add(g);
  return g;
}

/** Adds a mesh (and its outline shell when the material pair has one). */
export function mesh(parent: THREE.Object3D, geo: THREE.BufferGeometry, mat: M.MatPair | THREE.Material,
  pos: V3 | THREE.Vector3 = [0, 0, 0], rot: V3 = [0, 0, 0], scl: V3 = [1, 1, 1]): THREE.Mesh {
  const pair = (mat as M.MatPair).fill ? (mat as M.MatPair) : { fill: mat as THREE.Material, outline: null };
  const m = new THREE.Mesh(geo, pair.fill);
  m.rotation.order = "YXZ";
  if (Array.isArray(pos)) m.position.set(...pos); else m.position.copy(pos);
  m.rotation.set(...rot);
  m.scale.set(...scl);
  m.castShadow = !(pair.fill as any).transparent;
  m.userData.fill = true;
  if (pair.outline) {
    const o = new THREE.Mesh(geo, pair.outline);
    o.userData.outline = true;
    m.add(o);
  }
  parent.add(m);
  return m;
}

const flashMats = new Map<string, THREE.MeshBasicMaterial>();

export class FighterModel extends THREE.Group {
  look: Look;
  kit: string;
  hips!: THREE.Group; torso!: THREE.Group; head!: THREE.Group;
  arm_l!: THREE.Group; arm_r!: THREE.Group; hand_l!: THREE.Group; hand_r!: THREE.Group;
  leg_l!: THREE.Group; leg_r!: THREE.Group; skirt!: THREE.Group; cape!: THREE.Group;
  bladeBase!: THREE.Object3D; bladeTip!: THREE.Object3D; shieldNode!: THREE.Object3D; castPoint!: THREE.Object3D;
  hairSway: THREE.Group[] = [];
  /** Two-handed weapons: the left hand is pulled onto this point of the grip every frame. */
  private gripL: THREE.Object3D | null = null;
  private roxyFloatingBook: THREE.Group | null = null;
  private roxyOpenPalm = 0;
  private glaivePivot: THREE.Group | null = null;
  // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — purely visual, synced via Fighter.snapshot.
  gravityHeavy = false;
  private gravityHalo: THREE.Group | null = null;
  private gravityScythe: THREE.Group | null = null;
  // NYTHERA_SHOWCASE_SPIN_TOSS_V3 — cosmetic duplicate used only in character preview.
  private gravityPreviewFlyer: THREE.Group | null = null;
  private gravityShowFlying = false;
  private gravityShowLaunchP = new THREE.Vector3();
  private gravityShowLaunchQ = new THREE.Quaternion();
  private gravityShowLaunchScale = new THREE.Vector3(1,1,1);
  private gravityShowEclipse: THREE.Mesh | null = null;
  private gravityShowTrails: THREE.Group | null = null;
  scytheBeat = 0;
  // ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108: one-handed metal weapons only while spear is flying.
  // ZENITH_FORWARD_SPEAR_IK_V7_20261108 — root-mounted, target-directed spear.
  private zenithSpearGrip: THREE.Object3D | null = null;
  private zenithSpearRightGrip: THREE.Object3D | null = null;
  private zenithSpearInHand = true;
  // ZENITH_QIANG_CHOREOGRAPHY_V8_20261108 — visual timing (never replicated; reconstructs from pose keys).
  private zenithV8Pose = "";
  private zenithV8PoseAge = 0;
  private zenithV8FromPosition = new THREE.Vector3();
  private zenithV8FromRotation = new THREE.Quaternion();
  private zenithTwinBlades: THREE.Group[] = [];
  private zenithTwinBases: THREE.Object3D[] = [];
  private zenithTwinTips: THREE.Object3D[] = [];
  private zenithSpearBase: THREE.Object3D | null = null;
  private zenithSpearTip: THREE.Object3D | null = null;
  private zenithCatchAura: THREE.Group | null = null;
  zenithCatchShieldT = 0;
  zenithCatchRecoilT = 0;
  /** Nesa's heart hammer root, isolated so the carnival finisher can grow it 4x. */
  private nesaHammerPivot: THREE.Group | null = null;
  nesaHammerScale = 1;
  nesaSpinHorizontal = 0;
  parryCounterSpin = 0;
  /** ASTER_EMBER_LATEST_20261106: extra sword forged from his shield. */
  private judgmentSword: THREE.Group | null = null;
  private judgmentOldSword: THREE.Object3D[] = [];
  glaivePose = "idle"; // ZAREK_GLAIVE_CHOREO_V2: current attack key from the fighter
  // Only used by presentation visuals; combat abilities, reach and momentum untouched.
  presentationT = 0;
  presentationMode: "select" | "victory" = "select";
  /** KAIZEN_CHAIN_SPIN_V2 — separate flying blade, with links on a curved chain. */
  private chainLinks: THREE.Group[] = [];
  private chainAnchor: THREE.Group | null = null;
  private chainBlade: THREE.Group | null = null;
  private chainGhosts: THREE.Mesh[] = [];
  private chainWrap: THREE.Group[] = [];
  /** World-space center of a bound victim; received through online snapshots too. */
  chainBindTargetWorld: THREE.Vector3 | null = null;
  private chainPoseClock = 0;
  private chainPrevPose = "";
  private chainOrbit = 0;
  // Host/player and multiplayer visual sync; never changes collision geometry.
  kaizenSpinSpeed = 1;
  kaizenSpinDirection = 1;
  kaizenSpinActive = false;
  chainPose = "idle";
  chainFuryT = 0;
  chainExtended = false;
  /** Right foot tip, for kick trails. */
  footR: THREE.Group | null = null;
  walk = 0;
  recoil = 0;
  charge = 0;
  /** Bow draw 0..1 (string pulled back to the anchor). */
  draw = 0;
  /** Extra knee bend from the pose (smoothed). */
  private knee: [number, number] = [0, 0];
  private bowPivot: THREE.Group | null = null;
  /** Katana blade retracts into the visible left-hip scabbard during Kaede C. */
  katanaSheathProgress = 0;
  private katanaBladePivot: THREE.Group | null = null;
  private katanaSheathAmount = 0;
  private bowString: THREE.Mesh[] | null = null;
  private bowArrow: THREE.Group | null = null;
  private bowNockTop: THREE.Vector3 | null = null;
  private bowNockBot: THREE.Vector3 | null = null;
  /** Attacking, charging, blocking or reeling (set by the fighter each frame). */
  combat = false;
  /** Reeling from a hit (hitstun / stagger). */
  hurt = false;
  /** Active seconds of Veyr's Blood Festival, set by the Fighter each frame. */
  bloodFestivalT = 0;
  private festivalAura: THREE.Group[] = [];
  private festivalDrops: { node: THREE.Mesh; base: THREE.Vector3; seed: number }[] = [];

  private joints: Record<string, THREE.Group> = {};
  /** Procedural body meshes (hidden once a VRM body is attached) and the VRM rig. */
  private bodyMeshes: THREE.Object3D[] = [];
  private vrmRig: VrmRig | null = null;
  private disposed = false;
  /** Resolves once the final body is showing (VRM attached, or it failed / timed out). */
  ready: Promise<void> = Promise.resolve();
  loading = false;
  private cur: Record<string, THREE.Vector3> = {};
  private hipsY = 0;
  private t = Math.random() * 10;
  private walkPhase = 0;
  private hairMat!: M.MatPair;
  private faceMat!: THREE.ShaderMaterial;
  private glowMat!: THREE.MeshBasicMaterial;
  private glowBase = new THREE.Color();
  private barrier: THREE.Object3D | null = null;
  private flashT = 0;
  private blinkWait = 2;
  private blinkT = -1;
  private falling = 0;

  constructor(look: Look) {
    super();
    this.look = look;
    this.kit = look.kit;
    this.rotation.order = "YXZ";
    this.hairMat = M.toon(look.hair, { shade: look.hair_shade, width: 0.0045 });
    this.glowBase.set(look.glow);
    this.glowMat = M.glow(look.glow);

    this.hips = pivot(this, [0, HIP, 0]);
    const outfit = look.outfit;
    if (outfit === "mage") {
      this.mageLegs(); this.mageSkirt(); this.mageTorso(); this.mageArms();
    } else if (outfit === "assassin" || outfit === "samurai" || outfit === "brawler" || outfit === "martial") {
      this.lightLegs(); this.lightLower(); this.lightTorso(); this.lightArms();
    } else {
      this.knightLegs(); this.knightSkirt(); this.knightTorso(); this.knightArms();
    }
    this.buildHead();
    const before = new Set<THREE.Object3D>();
    this.traverse((o) => { if ((o as THREE.Mesh).isMesh) before.add(o); });
    switch (look.kit) {
      case "mage": this.look.element === "frost" ? this.buildRoxySpellbook() : this.buildStaff(); break;
      case "sickle": this.buildSickles(); break;
      case "scythe": this.buildGravityScythe(); break;
      case "glaive": this.buildGlaive(); break;
      case "chainblade": this.buildChainblade(); break;
      case "assassin": this.buildDaggers(); break;
      case "greatsword": this.buildGreatsword(); break;
      case "hammer": this.buildHammer(); break;
      case "katana": this.buildKatana(); break;
      case "bow": this.buildBow(); break;
      case "knuckles": this.buildKnuckles(); break;
      case "wind": this.buildWind(); break;
      case "bomb": this.buildBomb(); break;
      case "kicks": this.buildKicks(); break;
      default: this.buildSword(); this.buildShield();
    }
    if (this.kit === "knight" && this.look.element === "light") this.buildJudgmentSword();
    const weapons = new Set<THREE.Object3D>();
    this.traverse((o) => { if ((o as THREE.Mesh).isMesh && !before.has(o)) weapons.add(o); });
    this.applyBody();
    this.traverse((o) => { if ((o as THREE.Mesh).isMesh && !weapons.has(o) && !o.userData.outline) this.bodyMeshes.push(o); });
    if (look.vrm) {
      // Stay hidden while the VRoid body loads instead of flashing the old body; give up
      // after 20 s and show the procedural body (the VRM still swaps in if it arrives later).
      this.loading = true;
      this.visible = false;
      const load = loadVrm(look.vrm).then((v) => this.attachVrm(v)).catch((e) => console.warn("VRM body", e));
      this.ready = Promise.race([load, new Promise<void>((r) => setTimeout(r, 20000))]).then(() => {
        this.loading = false;
        this.visible = true;
      });
    }
    this.joints = { torso: this.torso, head: this.head, arm_r: this.arm_r, hand_r: this.hand_r,
      arm_l: this.arm_l, hand_l: this.hand_l, leg_l: this.leg_l, leg_r: this.leg_r };
    for (const j of JOINTS) this.cur[j] = new THREE.Vector3();
  }

  /**
   * Reshapes the shared rig: chest and shoulder width, hip width, limb thickness, head size,
   * overall height, plus a slight bust for female bodies. Weapons keep their size.
   */
  private applyBody() {
    const B = BODY[this.look.body === "m" ? "m" : "f"];
    this.scale.setScalar(B.height);
    for (const c of this.torso.children) {
      if (!(c as THREE.Mesh).isMesh) continue;
      c.scale.x *= B.torso;
      c.scale.z *= B.torso;
      c.position.x *= B.shoulder;
    }
    for (const a of [this.arm_l, this.arm_r]) {
      a.position.x *= B.shoulder;
      a.scale.set(B.limb, 1, B.limb);
    }
    // Undo the arm thickness on the hands so held weapons keep their shape.
    for (const h of [this.hand_l, this.hand_r]) h.scale.set(1 / B.limb, 1, 1 / B.limb);
    for (const l of [this.leg_l, this.leg_r]) {
      l.position.x *= B.hip;
      l.scale.set(B.limb, 1, B.limb);
    }
    this.skirt.scale.x *= B.hip;
    this.skirt.scale.z *= B.hip;
    this.head.scale.setScalar(B.head);
    if (B.bust) {
      const o = this.look.outfit;
      const top = o === "knight" ? this.metal() : o === "mage" ? this.tn(this.look.band) : this.tn(this.look.tunic);
      mesh(this.torso, sphere(0.07, 20), top, [0, 0.2, 0.095], [0, 0, 0], [1.45, 0.62, 0.62]);
    }
  }

  // --- material shortcuts -------------------------------------------------------
  private tn(c: string, outline = true, rim = 0.3) { return M.toon(c, { outline, rim }); }
  private metal() { return M.toon(this.look.metal, { rim: 0.7, shade: METAL_SHADE }); }
  private skin() { return M.toon(SKIN, { rim: 0.2, shade: SKIN_SHADE }); }
  private gem() {
    const g = col(this.look.glow);
    return M.toon(this.look.glow, { outline: false, rim: 0.6, emission: new THREE.Color(g.r * 0.35, g.g * 0.35, g.b * 0.35) });
  }

  private bow(parent: THREE.Object3D, pos: V3, s = 1, rot: V3 = [0, 0, 0]) {
    const b = pivot(parent, pos, rot);
    b.scale.setScalar(s);
    for (const side of [1, -1]) {
      mesh(b, sphere(0.04, 12), this.tn(this.look.tunic), [0.04 * side, 0, 0], [0, 0, 0.5 * side], [1.2, 0.75, 0.45]);
      mesh(b, box(0.018, 0.06, 0.006), this.tn(this.look.tunic), [0.015 * side, -0.035, 0], [0, 0, 0.35 * side]);
    }
    mesh(b, sphere(0.018, 12), this.tn(this.look.trim), [0, 0, 0.012]);
  }

  private strand(parent: THREE.Object3D, p0: THREE.Vector3, p1: THREE.Vector3, p2: THREE.Vector3, w: number, t: number, sway = false) {
    const g = strand(p0, p1, p2, w, t, CAP_C);
    if (sway) {
      const pv = pivot(parent, p0);
      mesh(pv, g, this.hairMat, p0.clone().negate());
      this.hairSway.push(pv);
    } else mesh(parent, g, this.hairMat);
  }

  private backCape(length: number, a0: number, topR: number, bottomR: number, tailLen: number, wind = 0.03) {
    const tails = (a: number) => tailLen * Math.pow(Math.abs(a - PI) / (PI - a0), 2);
    this.cape = pivot(this.torso, [0, 0.29, -0.03]);
    mesh(this.cape, coneSheet(topR, bottomR, length, a0, TAU - a0, 32, 10, 0, 0, tails), M.cloth(this.look.cape, {
      bottom: this.look.cape_bottom, pattern: this.look.trim, patternStrength: 0.9, patternV: 0.74,
      patternFreq: 3, trimBottom: 0.03, trimSides: 0.015, wind, trim: this.look.trim,
    }));
  }

  private hand(parent: THREE.Object3D, color: string): THREE.Group {
    const h = pivot(parent, [0, -0.38, 0]);
    mesh(h, sphere(0.033, 14), M.toon(color, { rim: 0.2, shade: color === SKIN ? SKIN_SHADE : M.DEFAULT_SHADE }), [0, 0, 0], [0, 0, 0], [0.92, 1.1, 0.8]);
    return h;
  }

  // --- knight / warrior -----------------------------------------------------------
  private knightLegs() {
    const L = this.look;
    for (const side of [1, -1]) {
      const leg = pivot(this.hips, [0.08 * side, 0, 0]);
      mesh(leg, cap(0.05, 0.76), this.tn(L.pants), [0, -0.37, 0]);
      mesh(leg, cyl(0.058, 0.062, 0.36, 16), this.tn(L.boots), [0, -0.66, 0]);
      mesh(leg, box(0.075, 0.26, 0.03), this.metal(), [0, -0.6, 0.052]);
      mesh(leg, sphere(0.045, 14), this.metal(), [0, -0.42, 0.045], [0, 0, 0], [1, 0.9, 0.6]);
      mesh(leg, sphere(0.012, 8), this.gem(), [0, -0.42, 0.075]);
      mesh(leg, torus(0.058, 0.068), this.tn(L.trim), [0, -0.48, 0], [0, 0, 0], [1, 0.6, 1]);
      mesh(leg, box(0.11, 0.06, 0.09), this.metal(), [0, -0.785, 0.07]);
      mesh(leg, box(0.12, 0.035, 0.2), this.tn(L.pants), [0, -0.822, 0.03]);
      if (side > 0) this.leg_l = leg; else this.leg_r = leg;
    }
  }

  private knightSkirt() {
    this.skirt = pivot(this.hips, [0, 0.04, 0]);
    mesh(this.skirt, coneSheet(0.11, 0.28, 0.3, 0, TAU, 40, 5), M.cloth(this.look.tunic, {
      pattern: this.look.band, patternStrength: 1, patternV: 0.68, patternFreq: 3, patternFill: 1, trimBottom: 0.06, trim: this.look.trim,
    }));
  }

  private knightTorso() {
    const L = this.look;
    this.torso = pivot(this.hips, [0, 0.05, 0]);
    const big = this.kit === "greatsword" || this.kit === "hammer";
    mesh(this.torso, cyl(0.095, 0.11, 0.3), this.tn(L.tunic), [0, 0.14, 0]);
    mesh(this.torso, sphere(0.125, 24), this.metal(), [0, 0.17, 0.035], [0, 0, 0], [1, 0.95, 0.72]);
    mesh(this.torso, torus(0.1, 0.112), this.tn(L.trim, false), [0, 0.08, 0.03], [0.25, 0, 0], [1.05, 0.5, 0.9]);
    mesh(this.torso, sphere(0.02, 12), this.gem(), [0, 0.2, 0.125], [0, 0, 0], [0.8, 1.2, 0.6]);
    mesh(this.torso, torus(0.108, 0.13), this.tn(BROWN), [0, -0.01, 0], [0.1, 0, 0], [1, 0.7, 1]);
    mesh(this.torso, box(0.04, 0.034, 0.012), this.tn(L.trim), [0, -0.01, 0.128]);
    mesh(this.torso, coneSheet(0.048, 0.072, 0.08, 0, TAU, 24, 2), M.cloth(L.band, { trimBottom: 0.2, trim: L.trim }), [0, 0.38, 0]);
    mesh(this.torso, cyl(0.034, 0.036, 0.08), this.skin(), [0, 0.36, 0]);
    const pr = big ? 0.095 : 0.078;
    mesh(this.torso, sphere(pr, 18), this.metal(), [-0.14, 0.27, 0], [0, 0, 0.3], [1.15, 0.75, 1.05]);
    mesh(this.torso, torus(pr - 0.003, pr + 0.01), this.tn(L.trim), [-0.15, 0.255, 0], [0, 0, 0.3], [1.1, 0.5, 1]);
    mesh(this.torso, sphere(big ? 0.09 : 0.062, 16), this.metal(), [0.135, 0.27, 0], [0, 0, -0.3], [1.1, 0.7, 1]);
    this.backCape(0.62, 2.0, 0.14, 0.34, 0.18);
  }

  private knightArms() {
    for (const side of [1, -1]) {
      const a = pivot(this.torso, [0.135 * side, 0.25, 0]);
      mesh(a, cap(0.031, 0.36), this.tn(this.look.band), [0, -0.18, 0]);
      mesh(a, cyl(0.042, 0.036, 0.16, 14), this.metal(), [0, -0.29, 0]);
      mesh(a, torus(0.036, 0.048), this.tn(this.look.trim), [0, -0.21, 0], [0, 0, 0], [1, 0.6, 1]);
      const h = this.hand(a, this.look.pants);
      if (side > 0) { this.arm_l = a; this.hand_l = h; } else { this.arm_r = a; this.hand_r = h; }
    }
  }

  // --- mage -------------------------------------------------------------------------
  private mageLegs() {
    const L = this.look;
    for (const side of [1, -1]) {
      const leg = pivot(this.hips, [0.075 * side, 0, 0]);
      mesh(leg, cap(0.05, 0.76), this.tn(L.pants), [0, -0.37, 0]);
      mesh(leg, cyl(0.055, 0.055, 0.025), this.tn(L.trim), [0, -0.13, 0]);
      this.bow(leg, [0, -0.15, 0.05], 0.55);
      mesh(leg, cyl(0.058, 0.06, 0.24, 16), this.tn(L.boots), [0, -0.7, 0.005]);
      mesh(leg, cyl(0.078, 0.07, 0.07, 16), this.tn(L.band), [0, -0.585, 0]);
      mesh(leg, box(0.11, 0.06, 0.09), this.tn(L.band), [0, -0.785, 0.07]);
      mesh(leg, box(0.12, 0.035, 0.2), this.tn(L.boots), [0, -0.822, 0.03]);
      mesh(leg, sphere(0.014, 10), this.gem(), [0, -0.585, 0.08]);
      if (side > 0) this.leg_l = leg; else this.leg_r = leg;
    }
  }

  private mageSkirt() {
    const L = this.look;
    this.skirt = pivot(this.hips, [0, 0.04, 0]);
    mesh(this.skirt, coneSheet(0.2, 0.33, 0.1, 0, TAU, 56, 3, 0.02, 22), M.cloth(L.cape_bottom), [0, -0.15, 0]);
    mesh(this.skirt, coneSheet(0.105, 0.31, 0.26, 0, TAU, 48, 6, 0.012, 14), M.cloth(L.band, {
      pattern: L.emblem, patternStrength: 1, patternV: 0.6, patternFreq: 5, patternFill: 1, trimBottom: 0.07, trim: L.trim,
    }));
  }

  private mageTorso() {
    const L = this.look;
    this.torso = pivot(this.hips, [0, 0.05, 0]);
    mesh(this.torso, cyl(0.09, 0.105, 0.3), this.tn(L.band), [0, 0.14, 0]);
    mesh(this.torso, cyl(0.106, 0.109, 0.11), this.tn(L.tunic), [0, 0.05, 0]);
    for (const y of [0.105, -0.005]) mesh(this.torso, torus(0.1, 0.112), this.tn(L.trim, false), [0, y, 0], [0, 0, 0], [1, 0.4, 1]);
    mesh(this.torso, torus(0.105, 0.127), this.tn(BROWN), [0, -0.015, 0], [0.1, 0, 0], [1, 0.7, 1]);
    mesh(this.torso, sphere(0.034, 16), M.water(L.glow, 0.8, 1.3), [-0.12, -0.075, 0.075]);
    mesh(this.torso, coneSheet(0.075, 0.235, 0.15, 0, TAU, 40, 4, 0.006, 12), M.cloth(L.tunic, { trimBottom: 0.14, trim: L.trim }), [0, 0.31, 0]);
    mesh(this.torso, coneSheet(0.04, 0.066, 0.05, 0, TAU, 24, 2, 0.01, 16), M.cloth(L.band), [0, 0.36, 0]);
    for (const side of [1, -1]) this.bow(this.torso, [0.15 * side, 0.21, 0.09], 1.2, [0, 0.5 * side, 0]);
    for (let i = 0; i < 3; i++) mesh(this.torso, sphere(0.03, 12), this.tn(L.band), [0, 0.235 - i * 0.03, 0.105 - i * 0.002], [0, 0, 0], [1.1 - i * 0.15, 0.6, 0.45]);
    this.bow(this.torso, [0, 0.272, 0.12], 1);
    mesh(this.torso, sphere(0.02, 12), this.gem(), [0, 0.258, 0.142], [0, 0, 0], [0.8, 1.2, 0.6]);
    mesh(this.torso, cyl(0.032, 0.034, 0.08), this.skin(), [0, 0.36, 0]);
    this.backCape(0.6, 1.75, 0.13, 0.4, 0.22, 0.035);
  }

  private mageArms() {
    const L = this.look;
    for (const side of [1, -1]) {
      const a = pivot(this.torso, [0.125 * side, 0.25, 0]);
      mesh(a, sphere(0.033, 14), this.skin());
      mesh(a, cap(0.027, 0.36), this.skin(), [0, -0.18, 0]);
      mesh(a, coneSheet(0.036, 0.115, 0.27, 0, TAU, 28, 4, 0.012, 9), M.cloth(L.band, {
        bottom: "#" + col(L.band).lerp(col(L.cape_bottom), 0.35).getHexString(), trimBottom: 0.07, trim: L.trim,
      }), [0, -0.07, 0]);
      const h = this.hand(a, SKIN);
      if (side > 0) { this.arm_l = a; this.hand_l = h; } else { this.arm_r = a; this.hand_r = h; }
    }
  }

  // --- light outfits: assassin, samurai, brawler, ranger ------------------------------
  private lightLegs() {
    const L = this.look;
    for (const side of [1, -1]) {
      const leg = pivot(this.hips, [0.075 * side, 0, 0]);
      mesh(leg, cap(L.outfit === "martial" ? 0.056 : 0.048, 0.76), this.tn(L.pants), [0, -0.37, 0]);
      if (side < 0) this.footR = pivot(leg, [0, -0.8, 0.08]);
      for (let i = 0; i < 4; i++) mesh(leg, torus(0.044, 0.056), this.tn(L.band), [0, -0.5 - i * 0.055, 0], [0.25 * (i % 2 ? -1 : 1), 0, 0], [1, 0.6, 1]);
      mesh(leg, box(0.1, 0.05, 0.18), this.tn(L.boots), [0, -0.8, 0.03]);
      if (L.outfit === "assassin") mesh(leg, box(0.012, 0.18, 0.04), this.metal(), [0.055 * side, -0.25, 0]);
      if (side > 0) this.leg_l = leg; else this.leg_r = leg;
    }
  }

  private lightLower() {
    const L = this.look;
    this.skirt = pivot(this.hips, [0, 0.04, 0]);
    if (L.outfit === "martial") {
      mesh(this.skirt, cyl(0.112, 0.118, 0.07, 20), this.tn(L.band), [0, 0.0, 0]);
      for (const s of [1, -1]) mesh(this.skirt, box(0.035, 0.22, 0.01), this.tn(L.band), [0.06 * s, -0.12, 0.115], [-0.12, 0, 0.12 * s]);
      return;
    }
    if (L.outfit === "samurai") {
      // Wide pleated hakama.
      mesh(this.skirt, coneSheet(0.11, 0.33, 0.6, 0, TAU, 40, 6, 0.01, 12), M.cloth(L.cape, {
        bottom: L.cape_bottom, pattern: L.cape_bottom, patternStrength: 0.4, patternV: 0.3, patternFreq: 8, trimBottom: 0.03, trim: L.trim,
      }));
      return;
    }
    for (const a0 of [-0.7, PI - 0.7]) {
      mesh(this.skirt, coneSheet(0.11, 0.2, L.outfit === "brawler" ? 0.18 : 0.34, a0, a0 + 1.4, 12, 5), M.cloth(L.tunic, {
        bottom: L.band, trimBottom: 0.05, trimSides: 0.04, trim: L.trim,
      }));
    }
    mesh(this.skirt, cyl(0.11, 0.12, 0.08, 20), this.tn(L.pants), [0, -0.02, 0]);
  }

  private lightTorso() {
    const L = this.look;
    this.torso = pivot(this.hips, [0, 0.05, 0]);
    mesh(this.torso, cyl(0.088, 0.1, 0.3), this.tn(L.tunic), [0, 0.14, 0]);
    if (L.outfit === "samurai" || L.outfit === "martial") {
      // Kimono / gi: crossed collar and a thick belt.
      for (const side of [1, -1]) mesh(this.torso, box(0.03, 0.2, 0.01), this.tn(L.band), [0.03 * side, 0.2, 0.093], [-0.1, 0, 0.45 * side]);
      mesh(this.torso, cyl(0.104, 0.104, 0.07, 20), this.tn(L.band), [0, 0.0, 0]);
      mesh(this.torso, box(0.06, 0.05, 0.03), this.tn(L.band), [0.06, -0.01, -0.1]);
    } else {
      mesh(this.torso, torus(0.1, 0.118), this.tn(L.band), [0, 0.15, 0], [0, 0, 0.6], [1, 1.6, 0.95]);
      mesh(this.torso, torus(0.1, 0.122), this.tn(BROWN), [0, -0.01, 0], [0.1, 0, 0], [1, 0.7, 1]);
      for (const x of [0.08, -0.08]) mesh(this.torso, box(0.05, 0.05, 0.03), this.tn(BROWN), [x, -0.04, 0.09]);
      mesh(this.torso, box(0.03, 0.03, 0.01), this.tn(L.trim), [0, -0.01, 0.122], [0, 0, PI / 4]);
    }
    mesh(this.torso, cyl(0.032, 0.034, 0.08), this.skin(), [0, 0.36, 0]);
    if (L.cloak) {
      this.backCape(0.62, 1.9, 0.13, 0.36, 0.16, 0.03);
      // Quiver across the back.
      const q = pivot(this.torso, [0.07, 0.17, -0.13], [0.15, 0, 0.5]);
      mesh(q, cyl(0.04, 0.035, 0.32, 12), this.tn(BROWN));
      for (let i = 0; i < 3; i++) mesh(q, box(0.025, 0.06, 0.005), this.tn(L.band, false), [(i - 1) * 0.02, 0.19, 0]);
    } else {
      // Scarf at the neck; its long tails act as the cape.
      const scarfColor = L.outfit === "brawler" ? L.cape : L.band;
      mesh(this.torso, coneSheet(0.062, 0.1, 0.09, 0, TAU, 24, 2, 0.008, 10), M.cloth(scarfColor), [0, 0.37, 0]);
      this.cape = pivot(this.torso, [0, 0.32, -0.08]);
      const scarf = M.toon(scarfColor, { rim: 0.3 });
      for (const side of [1, -1]) {
        mesh(this.cape, strand(v(0.03 * side, 0, 0), v(0.08 * side, -0.1, -0.25), v(0.12 * side, -0.55, -0.32), 0.06, 0.012, v(0, 0, 0.3)), scarf);
      }
    }
    if (L.outfit === "assassin") mesh(this.torso, sphere(0.06, 14), this.metal(), [-0.13, 0.27, 0], [0, 0, 0.3], [1, 0.7, 1]);
  }

  private lightArms() {
    const L = this.look;
    for (const side of [1, -1]) {
      const a = pivot(this.torso, [0.125 * side, 0.25, 0]);
      if (L.outfit === "samurai") {
        mesh(a, cap(0.029, 0.36), this.skin(), [0, -0.18, 0]);
        mesh(a, coneSheet(0.04, 0.1, 0.24, 0, TAU, 24, 3), M.cloth(L.tunic, { trimBottom: 0.08, trim: L.band }), [0, -0.02, 0]);
      } else if (L.outfit === "martial") {
        mesh(a, cyl(0.045, 0.05, 0.12, 14), this.tn(L.tunic), [0, -0.04, 0]);
        mesh(a, cap(0.029, 0.36), this.skin(), [0, -0.18, 0]);
        for (let i = 0; i < 3; i++) mesh(a, torus(0.029, 0.039), this.tn(L.band), [0, -0.26 - i * 0.035, 0], [0, 0, 0], [1, 0.7, 1]);
      } else if (L.outfit === "brawler") {
        mesh(a, sphere(0.04, 12), this.tn(L.tunic));
        mesh(a, cap(0.03, 0.36), this.skin(), [0, -0.18, 0]);
        for (let i = 0; i < 3; i++) mesh(a, torus(0.03, 0.04), this.tn(L.band), [0, -0.22 - i * 0.04, 0], [0, 0, 0], [1, 0.7, 1]);
      } else {
        mesh(a, cap(0.029, 0.36), this.tn(L.tunic), [0, -0.18, 0]);
        mesh(a, cyl(0.038, 0.034, 0.14, 12), this.metal(), [0, -0.3, 0]);
        mesh(a, torus(0.034, 0.044), this.tn(L.band), [0, -0.23, 0], [0, 0, 0], [1, 0.6, 1]);
      }
      const h = this.hand(a, L.outfit === "assassin" ? L.pants : SKIN);
      if (side > 0) { this.arm_l = a; this.hand_l = h; } else { this.arm_r = a; this.hand_r = h; }
    }
  }

  // --- head, hair, hats ----------------------------------------------------------------
  private buildHead() {
    const L = this.look;
    this.head = pivot(this.torso, [0, 0.37, 0]);
    this.head.scale.setScalar(0.92);
    const hc = pivot(this.head, [0, HEAD_R, 0]);
    this.faceMat = M.face(SKIN, L);
    mesh(hc, sphere(HEAD_R, 40), { fill: this.faceMat, outline: M.outlineMat("#ffc8bb") }, [0, 0, 0], [0, 0, 0], [1, 0.98, 0.97]);
    mesh(hc, sphere(0.205, 32), this.hairMat, CAP_C);
    const hl = col(L.hair).lerp(new THREE.Color(1, 1, 1), 0.45);
    mesh(hc, torus(0.188, 0.207), M.toon("#" + hl.getHexString(), { outline: false, rim: 0 }), [0, 0.085, -0.035], [-0.15, 0, 0], [1, 0.35, 1]);
    if (L.ears) {
      for (const side of [1, -1]) mesh(hc, cyl(0, 0.03, 0.12, 8), this.skin(), [0.2 * side, 0.0, -0.01], [0, 0, -1.1 * side], [1, 1, 0.45]);
    }
    switch (L.style) {
      case "ponytail": this.hairPonytail(hc); break;
      case "bob": this.hairBob(hc); break;
      case "twintails": this.hairTwintails(hc); break;
      default: this.hairShort(hc);
    }
    switch (L.hat) {
      case "beret": this.hatBeret(hc); break;
      case "witch": this.hatWitch(hc); break;
      case "goggles": this.hatGoggles(hc); break;
      case "hood": this.hatHood(hc); break;
      case "headband": this.hatHeadband(hc); break;
    }
  }

  private bangs(hc: THREE.Object3D, tips: number[], sweep: number) {
    tips.forEach((y, k) => {
      const x = -0.15 + (0.3 * k) / (tips.length - 1);
      const tx = Math.min(Math.max(x + sweep, -0.17), 0.17);
      const root = CAP_C.clone().add(v(x * 0.6, 0.75, 0.62).normalize().multiplyScalar(0.2));
      const tip = v(tx, y, Math.sqrt(Math.max(0.19 * 0.19 - tx * tx - y * y, 0))).normalize().multiplyScalar(0.2);
      const mid = CAP_C.clone().add(root.clone().add(tip).multiplyScalar(0.5).sub(CAP_C).normalize().multiplyScalar(0.236));
      this.strand(hc, root, mid, tip, 0.036, 0.015);
    });
  }

  private sideLocks(hc: THREE.Object3D, length: number) {
    for (const s of [1, -1]) this.strand(hc, v(0.15 * s, 0.1, 0.11), v(0.21 * s, -0.03, 0.11), v(0.19 * s, -0.05 - length, 0.08), 0.04, 0.016, true);
  }

  private hairShort(hc: THREE.Object3D) {
    mesh(hc, sphere(0.18, 28), this.hairMat, [0, -0.03, -0.07], [0, 0, 0], [1.05, 0.78, 0.92]);
    this.bangs(hc, [0.08, 0.045, 0.07, 0.035, 0.065, 0.04, 0.085], 0);
    this.sideLocks(hc, 0.07);
    for (let i = 0; i < 9; i++) {
      const a = 1.4 + ((TAU - 2.8) * i) / 8;
      const d = v(Math.sin(a), 0, Math.cos(a));
      this.strand(hc, CAP_C.clone().addScaledVector(d, 0.15).add(v(0, 0.12, 0)), CAP_C.clone().addScaledVector(d, 0.23),
        CAP_C.clone().addScaledVector(d, 0.28).add(v(0, -0.1, 0)), 0.06, 0.02, true);
    }
    for (const a of [PI - 0.9, PI - 0.3, PI + 0.4, PI + 1.0]) {
      const d = v(Math.sin(a), 0, Math.cos(a));
      this.strand(hc, CAP_C.clone().addScaledVector(d, 0.05).add(v(0, 0.19, 0)), CAP_C.clone().addScaledVector(d, 0.15).add(v(0, 0.26, 0)),
        CAP_C.clone().addScaledVector(d, 0.26).add(v(0, 0.2, 0)), 0.045, 0.016);
    }
  }

  private hairBob(hc: THREE.Object3D) {
    mesh(hc, sphere(0.19, 28), this.hairMat, [0, -0.07, -0.06], [0, 0, 0], [1.08, 0.85, 0.95]);
    this.bangs(hc, [0.06, 0.025, 0.045, 0.005, 0.03, -0.005, 0.04, 0.02, 0.06], 0);
    this.sideLocks(hc, 0.17);
    for (let i = 0; i < 11; i++) {
      const a = 1.35 + ((TAU - 2.7) * i) / 10;
      const d = v(Math.sin(a), 0, Math.cos(a));
      const f = 0.02 * Math.sin(i * 2.3);
      this.strand(hc, CAP_C.clone().addScaledVector(d, 0.16).add(v(0, 0.1, 0)), CAP_C.clone().addScaledVector(d, 0.235).add(v(0, -0.06, 0)),
        CAP_C.clone().addScaledVector(d, 0.27 + f).add(v(0, -0.19 + f, 0)), 0.065, 0.022, true);
    }
  }

  private hairPonytail(hc: THREE.Object3D) {
    mesh(hc, sphere(0.185, 28), this.hairMat, [0, -0.05, -0.06], [0, 0, 0], [1.05, 0.85, 0.95]);
    this.bangs(hc, [0.05, 0.03, 0.01, -0.005, 0.01, 0.03, 0.05, 0.07], 0.04);
    this.sideLocks(hc, 0.22);
    const tie = v(0, 0.13, -0.21);
    mesh(hc, torus(0.022, 0.04), this.tn(this.look.trim), tie, [PI / 2 + 0.5, 0, 0]);
    const tail = pivot(hc, tie);
    this.hairSway.push(tail);
    for (let i = 0; i < 5; i++) {
      const sx = (i - 2) * 0.025;
      mesh(tail, strand(v(sx * 0.5, 0, 0), v(sx, 0.02, -0.2), v(sx * 1.6, -0.48 + Math.abs(sx) * 2, -0.2), 0.06, 0.03, v(0, 0, 0.3)), this.hairMat);
    }
  }

  private hairTwintails(hc: THREE.Object3D) {
    mesh(hc, sphere(0.185, 28), this.hairMat, [0, -0.05, -0.06], [0, 0, 0], [1.05, 0.82, 0.95]);
    this.bangs(hc, [0.06, 0.03, 0.05, 0.015, 0.04, 0.02, 0.06], 0);
    this.sideLocks(hc, 0.12);
    for (const s of [1, -1]) {
      const tie = v(0.17 * s, 0.1, -0.1);
      mesh(hc, sphere(0.03, 12), this.tn(this.look.trim), tie);
      const tail = pivot(hc, tie);
      this.hairSway.push(tail);
      for (let i = 0; i < 3; i++) {
        const sz = (i - 1) * 0.03;
        mesh(tail, strand(v(0, 0, sz), v(0.12 * s, -0.05, sz - 0.05), v(0.1 * s, -0.55, sz - 0.08), 0.06, 0.03, v(-0.2 * s, 0, 0.1)), this.hairMat);
      }
    }
  }

  private hatBeret(hc: THREE.Object3D) {
    const L = this.look;
    const b = pivot(hc, [0.02, 0.155, -0.03], [-0.2, 0, -0.22]);
    mesh(b, cyl(0.18, 0.185, 0.04, 28), this.tn(L.tunic));
    mesh(b, torus(0.176, 0.193), this.tn(L.trim), [0, -0.02, 0], [0, 0, 0], [1, 0.5, 1]);
    mesh(b, sphere(0.225, 28), this.tn(L.band), [0, 0.04, -0.015], [0, 0, 0], [1, 0.33, 1]);
    mesh(b, box(0.07, 0.016, 0.01), this.tn(L.trim), [0, 0.012, 0.19]);
    this.bow(b, [0.165, 0, 0.08], 1.1, [0, 1.1, 0]);
    mesh(b, sphere(0.038, 14), this.tn(PEARL), [0.19, -0.005, 0.085], [0, 1.1, 0], [1, 0.85, 0.4]);
    for (let i = 0; i < 2; i++) mesh(b, sphere(0.012, 8), this.tn(PEARL, false), [0.195, -0.05 - i * 0.032, 0.1]);
    mesh(b, sphere(0.014, 10), this.gem(), [0.195, -0.12, 0.1], [0, 0, 0], [0.8, 1.4, 0.8]);
  }

  private hatWitch(hc: THREE.Object3D) {
    const L = this.look;
    const h = pivot(hc, [0, 0.17, -0.03], [-0.12, 0, 0.08]);
    mesh(h, cyl(0.34, 0.34, 0.018, 36), this.tn(L.tunic));
    mesh(h, cyl(0.07, 0.18, 0.26, 24), this.tn(L.tunic), [0, 0.13, 0]);
    mesh(h, cyl(0.182, 0.186, 0.05, 24), this.tn(L.trim), [0, 0.03, 0]);
    const tip = pivot(h, [0, 0.25, 0], [-0.9, 0, 0.2]);
    mesh(tip, cyl(0, 0.072, 0.2, 16), this.tn(L.tunic), [0, 0.09, 0]);
    mesh(h, sphere(0.024, 12), this.gem(), [0, 0.03, 0.185], [0, 0, 0], [1, 1, 0.6]);
  }

  private hatGoggles(hc: THREE.Object3D) {
    const L = this.look;
    const g = pivot(hc, [0, 0.12, 0], [-0.35, 0, 0]);
    mesh(g, torus(0.2, 0.216), this.tn(L.pants), [0, 0, 0], [0, 0, 0], [1, 1.6, 1]);
    for (const s of [1, -1]) {
      const lens = pivot(g, [0.065 * s, 0, 0.195], [PI / 2, 0, 0]);
      mesh(lens, cyl(0.05, 0.05, 0.035, 18), this.tn(L.trim));
      mesh(lens, cyl(0.04, 0.04, 0.04, 18), this.glowMat, [0, 0.002, 0]);
    }
    mesh(hc, box(0.012, 0.06, 0.01), this.tn(L.trim), [-0.12, 0.03, 0.16], [0, -0.5, 0.5]);
    mesh(hc, box(0.012, 0.05, 0.01), this.tn(L.trim), [-0.135, 0, 0.155], [0, -0.5, -0.4]);
  }

  private hatHood(hc: THREE.Object3D) {
    const L = this.look;
    mesh(hc, sphere(0.228, 32), M.toon(L.tunic, { rim: 0.35 }), [0, 0.045, -0.065]);
    mesh(hc, torus(0.19, 0.21), this.tn(L.band), [0, 0.03, 0.035], [PI / 2 - 0.25, 0, 0], [1, 1, 1.15]);
    mesh(hc, coneSheet(0.193, 0.12, 0.13, 0, TAU, 32, 3), M.cloth(L.band, { bottom: L.tunic }), [0, -0.055, 0]);
  }

  private hatHeadband(hc: THREE.Object3D) {
    const L = this.look;
    mesh(hc, torus(0.2, 0.216), this.tn(L.band), [0, 0.085, -0.02], [-0.2, 0, 0], [1, 1.5, 1]);
    const knot = pivot(hc, [0, 0.11, -0.21]);
    mesh(knot, sphere(0.022, 10), this.tn(L.band));
    this.hairSway.push(knot);
    for (const s of [1, -1]) mesh(knot, strand(v(0, 0, 0), v(0.06 * s, -0.08, -0.1), v(0.1 * s, -0.3, -0.12), 0.025, 0.006, v(0, 0, 0.3)), this.tn(L.band));
  }

  // --- weapons -----------------------------------------------------------------------
  private steel() { return M.toon("#eef3ff", { rim: 0.8, shade: METAL_SHADE }); }


  /** NYTHERA_GRAVITY_REAPER_INSTALL_V1 — Eclipsed Mourning, not a reused sickle.
   * The crescent is an extruded Bezier steel blade with a separate glowing cutting rim.
   * Right hand holds shaft, left hand IK is anchored lower on the same grip. */
  private buildGravityScythe() {
    const scythe = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    scythe.name = "Eclipsed Mourning — Nythera";
    scythe.scale.setScalar(0.95);
    this.gravityScythe = scythe;
    const dark = this.tn("#181229"), steel = this.tn("#b79cdb");
    const edgeSteel = this.tn("#c8ecff"), gold = this.tn("#d090d6");
    mesh(scythe, cyl(0.019, 0.021, 1.87, 12), dark, [0,-0.04,0]);
    mesh(scythe, cyl(0.025, 0.025, 0.59, 12), this.tn("#403653"), [0,-0.15,0]);
    for (const y of [-0.40,-0.18,0.02,0.22,0.74]) {
      mesh(scythe, torus(0.023,0.029), gold, [0,y,0], [PI/2,0,0]);
    }
    // A slim secondary ferrule keeps the hooked metal silhouette readable.
    mesh(scythe, cyl(0.047, 0.029, 0.19, 12), steel, [0,0.76,0]);
    const shape = new THREE.Shape();
    // NYTHERA_REAPER_SCYTHE_HARVESTER_AI_V2_20261108
    // Back of the blade climbs high, then sweeps outward to a needle-sharp
    // hooked beak; concave lower edge is much thinner than Nythera V1.
    // This is a single blade, never a double-sided polearm.
    shape.moveTo(-0.024, 0.755);
    shape.bezierCurveTo(-0.20, 1.045, -0.36, 1.48, -0.60, 1.615);
    shape.bezierCurveTo(-0.88, 1.755, -1.17, 1.69, -1.365, 1.465);
    shape.bezierCurveTo(-1.09, 1.575, -0.83, 1.585, -0.64, 1.465);
    shape.bezierCurveTo(-0.39, 1.335, -0.24, 0.98, -0.024, 0.755);
    shape.closePath();
    const geo = new THREE.ExtrudeGeometry(shape, { depth:0.021, bevelEnabled:true,
      bevelThickness:0.0045, bevelSize:0.003, bevelSegments:2, curveSegments:32 });
    geo.translate(0,0,-0.0105);
    mesh(scythe, geo, steel);
    // Polished hooked cutting edge is visibly thinner than the whole blade.
    const edgeCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.06,0.83,0.015), new THREE.Vector3(-0.37,1.29,0.015),
      new THREE.Vector3(-0.68,1.49,0.015), new THREE.Vector3(-1.02,1.55,0.015),
      new THREE.Vector3(-1.365,1.465,0.015)]);
    mesh(scythe, new THREE.TubeGeometry(edgeCurve, 34, 0.0058, 5, false), edgeSteel);
    // Fine violet spine inlay, kept behind the silver cutting edge.
    const spineCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.13,0.91,0.014), new THREE.Vector3(-0.35,1.41,0.014),
      new THREE.Vector3(-0.66,1.61,0.014), new THREE.Vector3(-1.02,1.60,0.014)]);
    mesh(scythe, new THREE.TubeGeometry(spineCurve, 25, 0.004, 5, false), gold);
    const rear = pivot(scythe,[0,-0.94,0]);
    mesh(rear, sphere(0.068,16), gold, [0,0,0],[0,0,0],[1,1.2,0.62]);
    mesh(rear, sphere(0.038,12), this.gem(), [0,-0.014,0]);
    const collar = pivot(scythe,[0,0.82,0]);
    mesh(collar,sphere(0.080,16),this.gem());
    mesh(collar,sphere(0.034,12),this.glowMat,[0,0,0.06]);
    this.gravityHalo = collar;
    for (let i=0;i<2;i++) {
      const ring = pivot(collar,[0,0,0], [i ? PI/2.8 : PI/10, 0, i ? 0.7 : 0.1]);
      mesh(ring, new THREE.TorusGeometry(0.15+i*0.045, 0.007, 6, 48), this.glowMat);
    }
    this.gripL = pivot(scythe,[0,-0.29,0]);
    // Use cutting-edge positions for native trails, melee contact and weapon clash.
    this.bladeBase = pivot(scythe,[-0.26,1.10,0]);
    this.bladeTip = pivot(scythe,[-1.36,1.465,0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = scythe;
  }

  /** ZAREK_STORM_V1: double-ended conductive glaive; meshes follow the VRM's hands. */
  private buildGlaive() {
    if (this.look.element === "metal") { this.buildZenithSpear(); return; }
    // Zarek's glaive remains unchanged.
    const zenithMetal = false; // Metal is handled above in buildZenithSpear().
    const staff = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    this.glaivePivot = staff;
    if (zenithMetal) staff.name = "zenithMagneticSpear";
    // ZAREK_PROPORTIONATE_GLAIVE_V1: shorten shaft, blades, tip, and offhand grip together.
    // -22% on procedural bodies; the VRoid hand mount is adjusted separately below.
    staff.scale.setScalar(zenithMetal ? 0.86 : 0.78);
    mesh(staff, cyl(0.019, 0.022, 1.53, 12), this.tn(zenithMetal ? "#8795ac" : "#233449"));
    mesh(staff, cyl(0.028, 0.028, 0.42, 12), this.tn(zenithMetal ? "#263955" : "#101a2a"), [0, 0, 0]);
    for (const s of [-1, 1]) {
      mesh(staff, cyl(0.047, 0.035, 0.12, 12), this.tn(this.look.trim), [0, s * 0.73, 0]);
      // Broad at the base, narrow at the end: thin diamond-edged blade, not a round club.
      const outline = new THREE.Shape();
      outline.moveTo(-0.026, s * 0.72);
      outline.lineTo(-0.062, s * 0.91);
      outline.lineTo(-0.042, s * 1.13);
      outline.lineTo(0, s * 1.38);
      outline.lineTo(0.042, s * 1.13);
      outline.lineTo(0.062, s * 0.91);
      outline.lineTo(0.026, s * 0.72);
      outline.closePath();
      const blade = new THREE.ExtrudeGeometry(outline, { depth: 0.014, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.006, bevelSegments: 1 });
      blade.translate(0, 0, -0.007);
      mesh(staff, blade, this.steel());
      mesh(staff, box(0.014, 0.30, 0.02), this.glowMat, [0, s * 1.04, 0.013]);
      mesh(staff, sphere(0.035, 12), this.gem(), [0, s * 0.82, 0]);
    }
    for (const y of [-0.32, -0.18, 0.18, 0.32]) mesh(staff, torus(0.029, 0.039), this.tn(this.look.trim), [0, y, 0], [PI / 2, 0, 0], [1, 0.35, 1]);
    this.gripL = pivot(staff, [0, -0.29, 0]);
    this.bladeBase = pivot(staff, [0, 0.78, 0]);
    this.bladeTip = pivot(staff, [0, 1.38, 0]);
    this.shieldNode = staff;
    this.castPoint = this.bladeTip;
  }

  // ZENITH_REFERENCE_SPEAR_V4_20261108 — ornate single-headed spear inspired by the new reference.
  // Larger leaf spearhead, gold side ornaments, blue crystal core, and a blunt rear pommel.
  private buildZenithSpear() {
    // The spear is rooted to the fighter, NOT driven by wrist roll.
    // The shaft aims in +Z, and the arms follow its two grip targets.
    const spear = pivot(this, [0, 0.98, 0.23], [PI / 2, 0, 0]);
    spear.name = "zenithRoyalSpear";
    spear.scale.setScalar(0.96);
    this.glaivePivot = spear;

    const steel = M.toon("#dfe6f0", { rim: 0.78, shade: METAL_SHADE });
    const whiteSteel = this.tn("#eef3fa");
    const navy = this.tn("#263a58");
    const dark = this.tn("#17263a");
    const gold = this.tn("#d4b27b");
    const paleGold = this.tn("#e9d4a5");
    const crystal = this.tn("#67c9ef");
    const gem = this.gem();

    // Shaft
    mesh(spear, cyl(0.0155, 0.0155, 1.78, 10), navy);
    mesh(spear, cyl(0.021, 0.021, 0.56, 10), dark, [0, -0.11, 0]);
    for (const y of [-0.33, -0.17, -0.01, 0.15]) {
      mesh(spear, torus(0.020, 0.027), gold, [0, y, 0], [PI / 2, 0, 0], [1, 0.32, 1]);
    }

    // Front assembly — broad leaf spearhead like the reference image.
    const outline = new THREE.Shape();
    outline.moveTo(-0.020, 0.78);
    outline.lineTo(-0.070, 0.94);
    outline.lineTo(-0.062, 1.10);
    outline.lineTo(-0.030, 1.24);
    outline.lineTo(0, 1.42);
    outline.lineTo(0.030, 1.24);
    outline.lineTo(0.062, 1.10);
    outline.lineTo(0.070, 0.94);
    outline.lineTo(0.020, 0.78);
    outline.closePath();
    const headGeo = new THREE.ExtrudeGeometry(outline, {
      depth: 0.016, bevelEnabled: true, bevelThickness: 0.004,
      bevelSize: 0.004, bevelSegments: 1
    });
    headGeo.translate(0, 0, -0.008);
    mesh(spear, headGeo, steel);
    mesh(spear, box(0.009, 0.46, 0.009), whiteSteel, [0, 1.05, 0.009]);
    mesh(spear, cyl(0.028, 0.026, 0.075, 10), gold, [0, 0.82, 0]);
    mesh(spear, cyl(0.025, 0.025, 0.028, 10), paleGold, [0, 0.89, 0]);

    // Decorative gold side wings near the base of the spearhead.
    for (const side of [-1, 1]) {
      const wing = new THREE.Shape();
      wing.moveTo(side * 0.018, 0.86);
      wing.lineTo(side * 0.13, 0.92);
      wing.lineTo(side * 0.17, 1.02);
      wing.lineTo(side * 0.08, 1.08);
      wing.lineTo(side * 0.028, 1.00);
      wing.closePath();
      const wingGeo = new THREE.ExtrudeGeometry(wing, {
        depth: 0.010, bevelEnabled: true, bevelThickness: 0.002,
        bevelSize: 0.002, bevelSegments: 1
      });
      wingGeo.translate(0, 0, -0.005);
      mesh(spear, wingGeo, gold);
      mesh(spear, new THREE.OctahedronGeometry(0.024, 0), crystal,
        [side * 0.108, 0.98, 0.016]);
    }

    // Oval gold body detail with inset circles like the reference weapon.
    mesh(spear, new THREE.BoxGeometry(0.105, 0.30, 0.028), gold,
      [0, 0.46, 0], [0, 0, 0], [1, 1, 0.8]);
    for (const y of [0.55, 0.46, 0.37]) {
      mesh(spear, new THREE.TorusGeometry(0.018, 0.006, 6, 16), dark,
        [0, y, 0.016], [Math.PI / 2, 0, 0]);
    }
    mesh(spear, sphere(0.024, 10), gem, [0, 0.73, 0.008]);
    mesh(spear, box(0.013, 0.16, 0.016), crystal, [0, 0.98, 0.01]);

    // Rear grip and butt — no blade, only a blunt counterweight.
    mesh(spear, cyl(0.025, 0.022, 0.11, 10), gold, [0, -0.83, 0]);
    mesh(spear, sphere(0.030, 10), paleGold, [0, -0.90, 0]);
    mesh(spear, new THREE.ConeGeometry(0.018, 0.055, 8), gold, [0, -0.96, 0], [Math.PI, 0, 0]);

    // Rear (right) hand guides from the hip; lead (left) hand sits ~32cm
    // toward the blade. The previous -0.34 target gripped behind the right hand.
    this.zenithSpearRightGrip = pivot(spear, [0, -0.02, 0]);
    this.gripL = pivot(spear, [0, 0.32, 0]);
    this.zenithSpearGrip = this.gripL;
    this.buildZenithTwinBlades();
    this.bladeBase = pivot(spear, [0, 0.80, 0]);
    this.bladeTip = pivot(spear, [0, 1.42, 0]);
    this.zenithSpearBase = this.bladeBase;
    this.zenithSpearTip = this.bladeTip;
    this.shieldNode = spear;
    this.castPoint = this.bladeTip;
  }

  /** In-flight: dual short swords; caught: one real long spear and two swords dissolve. */
  setZenithSpearHeld(held: boolean) {
    if (this.look.element !== "metal") return;
    this.zenithSpearInHand = held;
    if (this.glaivePivot) this.glaivePivot.visible = held;
    for (const blade of this.zenithTwinBlades) blade.visible = !held;
    this.gripL = held ? this.zenithSpearGrip : null;
    this.bladeBase = held ? this.zenithSpearBase ?? this.bladeBase : this.zenithTwinBases[0] ?? this.bladeBase;
    this.bladeTip = held ? this.zenithSpearTip ?? this.bladeTip : this.zenithTwinTips[0] ?? this.bladeTip;
    if (this.vrmRig) {
      this.vrmRig.gripL = held ? this.zenithSpearGrip : null;
      this.vrmRig.spearGripR = held ? this.zenithSpearRightGrip : null;
      this.vrmRig.glaive = held;
      this.vrmRig.bladed = held ? 0.4 : 0.76;
    }
  }

  /** Twin Metal Blades are prebuilt, never reconstructed per frame. */
  private buildZenithTwinBlades() {
    const steel = M.toon("#dbe8f6", { rim: 0.65, shade: METAL_SHADE });
    const blue = this.tn("#80d7ef"), gold = this.tn("#cda96d"), grip = this.tn("#1b3047");
    for (const [i, hand] of [this.hand_r, this.hand_l].entries()) {
      const sword = pivot(hand, [0, 0.04, 0.06], [PI / 2, 0, i ? -0.20 : 0.20]);
      sword.name = i ? "zenithTwinLeft" : "zenithTwinRight";
      mesh(sword, cyl(0.023, 0.025, 0.23, 10), grip, [0, -0.06, 0]);
      mesh(sword, box(0.19, 0.035, 0.065), gold, [0, 0.08, 0]);
      mesh(sword, sphere(0.029, 10), gold, [0, -0.19, 0]);
      const blade = new THREE.Shape();
      blade.moveTo(-0.045, 0.10);
      blade.lineTo(-0.073, 0.34);
      blade.lineTo(-0.031, 0.51);
      blade.lineTo(0, 0.66);
      blade.lineTo(0.031, 0.51);
      blade.lineTo(0.073, 0.34);
      blade.lineTo(0.045, 0.10);
      blade.closePath();
      const geo = new THREE.ExtrudeGeometry(blade, {depth:0.018,bevelEnabled:true,
        bevelSize:0.003,bevelThickness:0.003,bevelSegments:1});
      geo.translate(0, 0, -0.009);
      mesh(sword, geo, steel);
      mesh(sword, box(0.012, 0.33, 0.026), blue, [0, 0.34, 0.015]);
      this.zenithTwinBases.push(pivot(sword, [0, 0.12, 0]));
      this.zenithTwinTips.push(pivot(sword, [0, 0.66, 0]));
      sword.visible = false;
      this.zenithTwinBlades.push(sword);
    }
    const aura = pivot(this, [0, 0.94, 0]);
    aura.name = "zenithCatchMagneticGuard";
    const glow = new THREE.MeshBasicMaterial({color: "#83d8ff", transparent: true,
      opacity: 0.60, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide});
    const ring = mesh(aura, new THREE.TorusGeometry(0.55, 0.013, 6, 44), glow);
    ring.rotation.x = 0.35;
    const ring2 = mesh(aura, new THREE.TorusGeometry(0.47, 0.009, 6, 38), glow);
    ring2.rotation.y = 0.45;
    aura.visible = false;
    this.zenithCatchAura = aura;
  }

  /** KAIZEN_BIND_ZAREK_COUNTER_V4: forked short blade in right hand, long chain gripped by left. */

  private buildChainblade() {
    // KAIZEN_WEAPON_V5: compact forked spear-knife, dark red grip, individually sized links.
    // Off-hand holds the free end; the blade flies independently in the other hand.
    const anchorGrip = pivot(this.hand_l, [0, -0.055, 0], [PI / 2, 0, 0]);
    mesh(anchorGrip, cyl(0.025, 0.028, 0.19, 12), this.tn("#36202b"));
    mesh(anchorGrip, cyl(0.037, 0.033, 0.018, 12), this.tn("#c69c52"), [0, 0.09, 0]);
    mesh(anchorGrip, sphere(0.027, 12), this.tn("#a8aab2"), [0, -0.103, 0]);
    this.chainAnchor = pivot(anchorGrip, [0, 0.113, 0]);

    // Thin, correctly proportioned steel chain. No scaling links along their length.
    const darkSteel = this.tn("#30343d");
    const chainHighlight = this.tn("#7b808b");
    for (let i = 0; i < 72; i++) {
      const link = pivot(this);
      mesh(link, torus(0.016, 0.034), darkSteel, [0, 0, 0],
        [i % 2 ? PI / 2 : 0, 0, 0], [0.80, 1.16, 0.85]);
      mesh(link, torus(0.017, 0.030), chainHighlight, [0, 0, 0.003],
        [i % 2 ? PI / 2 : 0, 0, 0], [0.75, 1.13, 0.8]);
      link.visible = false;
      this.chainLinks.push(link);
    }

    // All weapon details belong to a single rigid blade group.
    this.chainBlade = pivot(this, [0, 1.11, 0.24]);
    const grip = this.tn("#681d2e");
    const bright = this.tn("#e1e4e8");
    const dark = this.tn("#6b7381");
    const brass = this.tn("#cba864");
    mesh(this.chainBlade, cyl(0.028, 0.030, 0.34, 14), grip, [0, -0.02, 0]);
    // Diagonal-looking handle wrappings and a chain-link connection at the pommel.
    for (let i = 0; i < 7; i++) {
      const y = -0.165 + i * 0.045;
      mesh(this.chainBlade, torus(0.027, 0.034), this.tn("#9b3d4c"),
        [0, y, 0], [PI / 2, 0, 0], [0.89, 0.32, 1.02]);
    }
    mesh(this.chainBlade, cyl(0.043, 0.039, 0.032, 14), brass, [0, 0.169, 0]);
    mesh(this.chainBlade, cyl(0.037, 0.037, 0.031, 14), brass, [0, -0.197, 0]);
    mesh(this.chainBlade, sphere(0.025, 12), dark, [0, -0.224, 0]);
    mesh(this.chainBlade, box(0.19, 0.025, 0.062), brass, [0, 0.196, 0]);
    mesh(this.chainBlade, sphere(0.024, 12), this.gem(), [0, 0.201, 0.036]);

    // An asymmetric, forked polished blade (no thick bevels or oversized side tines).
    const shape = new THREE.Shape();
    shape.moveTo(-0.073, 0.214);
    shape.lineTo(0.080, 0.214);
    shape.lineTo(0.111, 0.305);
    shape.lineTo(0.104, 0.482);
    shape.lineTo(0.071, 0.607); // short tine
    shape.lineTo(0.039, 0.564);
    shape.lineTo(0.054, 0.433);
    shape.lineTo(-0.024, 0.466); // inner gap
    shape.lineTo(-0.101, 0.718); // long fine tip
    shape.lineTo(-0.130, 0.682);
    shape.lineTo(-0.081, 0.390);
    shape.lineTo(-0.150, 0.295);
    shape.closePath();
    const daggerGeo = new THREE.ExtrudeGeometry(shape, {
      depth: 0.012, bevelEnabled: true, bevelThickness: 0.003,
      bevelSize: 0.002, bevelSegments: 2,
    });
    daggerGeo.translate(0, 0, -0.006);
    // KAIZEN_BIND_ZX_V6: resize only the blade head. Keep the chain, grip and guard as V5.
    daggerGeo.translate(0, -0.214, 0);
    daggerGeo.scale(0.72, 0.72, 1);
    daggerGeo.translate(0, 0.214, 0);
    mesh(this.chainBlade, daggerGeo, bright);
    // Separate narrow central ridge makes the steel appear faceted, not like a paddle.
    const ridge = new THREE.Shape();
    ridge.moveTo(-0.052, 0.257);
    ridge.lineTo(0.033, 0.256);
    ridge.lineTo(0.028, 0.407);
    ridge.lineTo(-0.070, 0.625);
    ridge.lineTo(-0.049, 0.400);
    ridge.closePath();
    const ridgeGeo = new THREE.ExtrudeGeometry(ridge, { depth: 0.005, bevelEnabled: false });
    ridgeGeo.translate(0, 0, 0.010);
    ridgeGeo.translate(0, -0.214, 0);
    ridgeGeo.scale(0.72, 0.72, 1);
    ridgeGeo.translate(0, 0.214, 0);
    mesh(this.chainBlade, ridgeGeo, dark);
    // Fine edge highlight along the long tine.
    const edgePath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.147, 0.300, 0.014),
      new THREE.Vector3(-0.079, 0.391, 0.014),
      new THREE.Vector3(-0.129, 0.681, 0.014),
      new THREE.Vector3(-0.101, 0.716, 0.014),
    ]);
    const edgeGeo = new THREE.TubeGeometry(edgePath, 22, 0.0035, 4, false);
    edgeGeo.translate(0, -0.214, 0);
    edgeGeo.scale(0.72, 0.72, 1);
    edgeGeo.translate(0, 0.214, 0);
    mesh(this.chainBlade, edgeGeo, bright);
    for (const yy of [0.272, 0.317])
      mesh(this.chainBlade, sphere(0.009, 8), brass, [0.018, yy, 0.018]);
    this.bladeBase = pivot(this.chainBlade, [0, 0.21, 0]);
    this.bladeTip = pivot(this.chainBlade, [-0.072, 0.578, 0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = anchorGrip;

    // Thin chains wrapped around an enemy during X/V binding, not giant hoops.
    for (let i = 0; i < 28; i++) {
      const node = pivot(this);
      mesh(node, torus(0.014, 0.030), darkSteel, [0, 0, 0],
        [i % 2 ? PI / 2 : 0, 0, 0], [0.83, 1.11, 0.88]);
      node.visible = false;
      this.chainWrap.push(node);
    }
    for (let i = 0; i < 2; i++) {
      const mat = new THREE.MeshBasicMaterial({ color: i ? 0xf4bec7 : 0xff5a69,
        transparent: true, opacity: i ? 0.08 : 0.16, depthWrite: false, side: THREE.DoubleSide });
      const ghost = new THREE.Mesh(daggerGeo, mat);
      ghost.visible = false;
      ghost.userData.fill = true;
      this.add(ghost);
      this.chainGhosts.push(ghost);
    }
  }

  /** V5: free-moving forked blade; thin chain follows a real curve without stretched links. */


  private updateChainblade(dt: number) {
    const blade = this.chainBlade, anchor = this.chainAnchor;
    if (!blade || !anchor || !this.chainLinks.length) return;
    this.updateMatrixWorld(true);
    const start = this.worldToLocal(anchor.getWorldPosition(new THREE.Vector3()));
    const handR = this.worldToLocal(this.hand_r.getWorldPosition(new THREE.Vector3()));
    const pose = this.chainPose;
    if (pose !== this.chainPrevPose) { this.chainPoseClock = 0; this.chainPrevPose = pose; }
    else this.chainPoseClock += dt * (this.kaizenSpinActive ? this.kaizenSpinSpeed : 1);
    const t = this.chainPoseClock;
    const blocking = pose === "block";
    const orbit = /^(?:cbx|cbz|cbc)/.test(pose);
    const strike = pose.endsWith("_s");
    const attack = /^(?:cb[1-5]_|cbh_|cbz_|cbv_|cbc_|cbx)/.test(pose);
    const bound = this.chainBindTargetWorld !== null;
    const bindCenter = bound ? this.worldToLocal(this.chainBindTargetWorld!.clone()) : null;
    // The counter-parried circular skill genuinely rotates in reverse and at
    // 10% speed after a perfect parry. Kaizen's normal spinning shield is NOT affected.
    const spinRate = this.kaizenSpinActive ? this.kaizenSpinSpeed : 1;
    const spinDirection = this.kaizenSpinActive ? this.kaizenSpinDirection : 1;
    this.chainOrbit += dt * (blocking ? 15 : orbit ? (strike ? 20 : 11) : attack ? 8 : 1.4)
      * spinRate * spinDirection;

    let goal = handR.clone().add(new THREE.Vector3(0, 0.08, 0.16));
    if (bindCenter) {
      goal = bindCenter.clone().add(new THREE.Vector3(0.05, 0.13, 0.02));
    } else if (blocking) {
      // Continuous rotating guard that stays tight to the torso.
      goal.set(Math.sin(this.chainOrbit) * 0.77,
        1.10 + Math.sin(this.chainOrbit * 2) * 0.09,
        0.18 + Math.cos(this.chainOrbit) * 0.69);
    } else if (orbit) {
      const r = strike ? 1.85 : 1.12;
      goal.set(Math.sin(this.chainOrbit) * r,
        1.14 + Math.sin(this.chainOrbit * 2) * 0.13,
        Math.cos(this.chainOrbit) * r * 0.83 + 0.22);
    } else if (pose.startsWith("cbh") || pose.startsWith("cbv")) {
      const power = strike ? Math.min(1, t * 4.8) : 0.2;
      const travel = Math.sin(Math.PI * power) * 2.55;
      goal.set(start.x + Math.sin(t * 9) * 0.16, 1.25, start.z + 0.45 + travel);
    } else if (/^cb[1-5]_[ws]$/.test(pose)) {
      const n = Number(pose[2]), sign = n % 2 ? 1 : -1;
      const angle = (n % 2 ? -1 : 1) + sign * (strike ? Math.min(1, t / 0.24) * PI * 1.16 : -0.2);
      const r = strike ? 1.46 : 0.76;
      goal.set(Math.sin(angle) * r, 1.14 + Math.cos(angle + n) * 0.25,
        Math.cos(angle) * r * 0.77 + 0.2);
    }
    blade.position.lerp(goal, 1 - Math.exp(-(bound ? 38 : blocking ? 36 : attack ? 26 : 17) * dt));
    const end = blade.position.clone();

    // During guard the blade goes around Kaizen, and the chain follows the preceding arc.
    // During attacks a slack quadratic produces natural whiplash.
    const curve = blocking ? new THREE.CatmullRomCurve3([
      start,
      new THREE.Vector3(Math.sin(this.chainOrbit - 1.05) * 0.63, 1.08,
        0.16 + Math.cos(this.chainOrbit - 1.05) * 0.60),
      new THREE.Vector3(Math.sin(this.chainOrbit - 0.48) * 0.76, 1.13,
        0.16 + Math.cos(this.chainOrbit - 0.48) * 0.66),
      end,
    ], false, "centripetal", 0.5) : new THREE.QuadraticBezierCurve3(
      start,
      start.clone().lerp(end, 0.5).add(new THREE.Vector3(
        Math.sin(this.chainOrbit) * (orbit ? 0.34 : 0.10),
        bound ? 0.02 : attack ? 0.06 : -0.23,
        Math.cos(this.chainOrbit) * (orbit ? 0.31 : 0.09))),
      end,
    );

    // Maintain original link shape and thickness at every reach; add/hide links instead
    // of stretching them (the cause of the giant chain in V4).
    const length = curve.getLength();
    const visibleCount = THREE.MathUtils.clamp(Math.ceil(length / 0.047), 8, this.chainLinks.length);
    const up = new THREE.Vector3(0, 1, 0);
    for (let i = 0; i < this.chainLinks.length; i++) {
      const link = this.chainLinks[i];
      link.visible = i < visibleCount;
      if (!link.visible) continue;
      const u = (i + 0.5) / visibleCount;
      link.position.copy(curve.getPoint(u));
      const tan = curve.getTangent(u).normalize();
      if (tan.lengthSq() > 0.0001) link.quaternion.setFromUnitVectors(up, tan);
      link.rotateY((i % 2) * PI / 2);
      link.scale.setScalar(1); // never widen a link with distance
    }
    // Smaller enemy wraps: two tight overlapping chain loops at chest height.
    for (let i = 0; i < this.chainWrap.length; i++) {
      const link = this.chainWrap[i];
      link.visible = !!bindCenter;
      if (!bindCenter) continue;
      const angle = (i % 14) * TAU / 14;
      const layer = i < 14 ? -0.13 : 0.13;
      link.position.copy(bindCenter).add(new THREE.Vector3(
        Math.sin(angle) * 0.32, layer + Math.sin(angle * 2) * 0.04,
        Math.cos(angle) * 0.32));
      link.rotation.set(0.1 * Math.cos(angle), angle + PI / 2, 0);
    }
    const tangent = blocking
      ? new THREE.Vector3(Math.cos(this.chainOrbit), 0, -Math.sin(this.chainOrbit)).normalize()
      : end.clone().sub(curve.getPoint(0.86)).normalize();
    if (tangent.lengthSq() > 0.01)
      blade.quaternion.slerp(new THREE.Quaternion().setFromUnitVectors(up, tangent),
        1 - Math.exp(-(blocking ? 30 : 18) * dt));
    let prev: THREE.Object3D = blade;
    for (let i = 0; i < this.chainGhosts.length; i++) {
      const ghost = this.chainGhosts[i];
      ghost.visible = !bound && (blocking || (attack && (strike || orbit)));
      ghost.position.lerp(prev.position, 1 - Math.exp(-(i ? 10 : 17) * dt));
      ghost.quaternion.slerp(prev.quaternion, 1 - Math.exp(-16 * dt));
      ghost.scale.setScalar(i ? 0.85 : 0.95);
      prev = ghost;
    }
  }


  private buildSword() {
    const s = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    mesh(s, cyl(0.016, 0.018, 0.17, 10), this.tn(BROWN));
    mesh(s, sphere(0.026, 12), this.tn(this.look.trim), [0, -0.1, 0]);
    mesh(s, box(0.21, 0.03, 0.04), this.tn(this.look.trim), [0, 0.1, 0]);
    mesh(s, sphere(0.018, 10), this.gem(), [0, 0.1, 0.022]);
    mesh(s, box(0.056, 0.84, 0.012), this.steel(), [0, 0.535, 0]);
    mesh(s, cyl(0, 0.028, 0.12, 4), this.steel(), [0, 1.015, 0], [0, 0, 0], [1, 1, 0.22]);
    mesh(s, box(0.014, 0.72, 0.016), this.glowMat, [0, 0.5, 0]);
    this.bladeBase = pivot(s, [0, 0.4, 0]);
    this.bladeTip = pivot(s, [0, 1.05, 0]);
    this.castPoint = this.bladeTip;
  }

  /** CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: ceremonial forged greatblade. */
  private buildJudgmentSword() {
    const grip = this.bladeBase.parent;
    if (!grip) return;
    this.judgmentOldSword = grip.children.filter(c => c !== this.bladeBase && c !== this.bladeTip);
    const weapon = pivot(grip);
    // Primary steel silhouette; the shield's defensive plates become the blade's ribs.
    mesh(weapon, box(0.20, 1.26, 0.075), this.steel(), [0, 0.77, 0]);
    mesh(weapon, cyl(0, 0.11, 0.45, 4), this.steel(), [0, 1.57, 0], [0, 0, PI / 4], [1.25, 1, 0.60]);
    mesh(weapon, box(0.035, 1.56, 0.095), this.glowMat, [0, 0.84, 0.035]);
    mesh(weapon, box(0.8, 0.090, 0.16), this.tn(this.look.trim), [0, 0.20, 0]);
    mesh(weapon, box(0.38, 0.42, 0.20), this.tn(this.look.shield), [0, 0.34, 0]);
    for (const side of [-1, 1]) {
      // Large detached shield-metal wing plates with gold bevels and crackling cores.
      mesh(weapon, box(0.19, 0.48, 0.075), this.tn(this.look.shield),
        [side * 0.31, 0.48, 0], [0, 0, side * 0.40]);
      mesh(weapon, box(0.12, 0.38, 0.075), this.tn(this.look.trim),
        [side * 0.235, 0.80, 0], [0, 0, side * 0.25]);
      mesh(weapon, box(0.028, 0.55, 0.09), this.glowMat,
        [side * 0.19, 0.54, 0.062], [0, 0, side * 0.38]);
      mesh(weapon, sphere(0.055, 12), this.gem(), [side * 0.36, 0.22, 0.05]);
      mesh(weapon, box(0.045, 0.30, 0.07), this.glowMat,
        [side * 0.14, 1.14, 0.065], [0, 0, side * 0.18]);
    }
    mesh(weapon, sphere(0.105, 16), this.gem(), [0, 0.35, 0.095]);
    mesh(weapon, box(0.09, 0.33, 0.15), this.tn(this.look.trim), [0, -0.01, 0]);
    mesh(weapon, sphere(0.075, 12), this.gem(), [0, -0.15, 0]);
    weapon.visible = false;
    this.judgmentSword = weapon;
  }

  /** Use the shield as the greatblade's defensive metal without leaving a second shield behind. */
  setJudgment(on: boolean) {
    if (!this.judgmentSword) return;
    this.judgmentSword.visible = on;
    for (const part of this.judgmentOldSword) part.visible = !on;
    this.shieldNode.visible = !on;
    this.bladeTip.position.y = on ? 1.76 : 1.05;
    if (this.vrmRig) this.vrmRig.shield = !on;
  }

  private buildShield() {
    const L = this.look;
    this.shieldNode = pivot(this.hand_l, [0, -0.02, 0]);
    mesh(this.shieldNode, cyl(0.29, 0.29, 0.035, 24), this.tn(L.shield));
    mesh(this.shieldNode, torus(0.275, 0.31), this.tn(L.trim), [0, 0, 0], [0, 0, 0], [1, 0.9, 1]);
    mesh(this.shieldNode, cyl(0.17, 0.17, 0.045, 4), this.tn(L.emblem), [0, -0.002, 0], [0, PI / 4, 0], [1, 1, 1.35]);
    mesh(this.shieldNode, sphere(0.07, 16), this.metal(), [0, -0.028, 0], [0, 0, 0], [1, 0.55, 1]);
    mesh(this.shieldNode, sphere(0.02, 10), this.gem(), [0, -0.064, 0]);
  }

  private buildGreatsword() {
    const L = this.look;
    const s = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    mesh(s, cyl(0.02, 0.022, 0.34, 10), this.tn(BROWN), [0, 0.02, 0]);
    mesh(s, sphere(0.034, 12), this.tn(L.trim), [0, -0.16, 0]);
    mesh(s, box(0.34, 0.05, 0.06), this.tn(L.trim), [0, 0.2, 0]);
    mesh(s, sphere(0.026, 10), this.gem(), [0, 0.2, 0.034]);
    mesh(s, box(0.15, 1.48, 0.024), this.steel(), [0, 0.97, 0]);
    mesh(s, cyl(0, 0.073, 0.23, 4), this.steel(), [0, 1.81, 0], [0, 0, 0], [1, 1, 0.2]);
    mesh(s, box(0.026, 1.30, 0.028), this.glowMat, [0, 0.93, 0]);
    this.bladeBase = pivot(s, [0, 0.5, 0]);
    this.bladeTip = pivot(s, [0, 1.86, 0]);
    this.gripL = pivot(s, [0, -0.11, 0]);
    this.shieldNode = pivot(s, [0, 0.6, 0]);
    this.castPoint = this.bladeTip;
  }

  private buildHammer() {
    // NESA_HEART_SMASH_V4: ornate carnival heart hammer. Proportions remain combat-sized.
    const h = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    this.nesaHammerPivot = h;
    // Reinforced striped shaft; top connects to the broad crosswise barrel.
    mesh(h, cyl(0.036, 0.043, 1.15, 12), this.tn("#392d42"), [0, 0.37, 0]);
    for (let i = 0; i < 8; i++)
      mesh(h, cyl(0.044, 0.044, 0.034, 12), this.tn(i % 2 ? "#f5b0d6" : "#f7d38d"), [0, -0.13 + 0.115 * i, 0]);
    mesh(h, sphere(0.067, 16), this.tn("#ffc4df"), [0, -0.25, 0]);
    mesh(h, cyl(0.078, 0.078, 0.14, 12), this.tn("#eeb772"), [0, 0.82, 0]);
    // Wide dark-rose steel barrel mounted perpendicular to the shaft.
    mesh(h, cyl(0.325, 0.325, 0.75, 20), this.tn("#56445e"), [0, 1.08, 0], [0, 0, PI / 2]);
    for (const side of [-1, 1]) {
      mesh(h, cyl(0.345, 0.345, 0.09, 20), this.tn("#ec89be"), [side * 0.28, 1.08, 0], [0, 0, PI / 2]);
      mesh(h, cyl(0.302, 0.302, 0.072, 20), this.tn("#8c698c"), [side * 0.38, 1.08, 0], [0, 0, PI / 2]);
      mesh(h, torus(0.25, 0.285), this.tn("#ffc481"), [side * 0.424, 1.08, 0], [0, PI / 2, 0]);
    }
    // Five-point golden star is only a bezel; the central motif is always HEART.
    const star = new THREE.Shape();
    for (let i = 0; i < 10; i++) {
      const a = Math.PI / 2 + i * Math.PI / 5;
      const r = i % 2 ? 0.22 : 0.36;
      const x = Math.cos(a) * r, y = Math.sin(a) * r;
      if (i === 0) star.moveTo(x, y); else star.lineTo(x, y);
    }
    star.closePath();
    const starGeo = new THREE.ExtrudeGeometry(star, { depth: 0.045, bevelEnabled: true,
      bevelSize: 0.013, bevelThickness: 0.012, bevelSegments: 2, curveSegments: 8 });
    mesh(h, starGeo, this.tn("#ffc176"), [0.44, 1.08, 0], [0, PI / 2, 0]);
    const heart = new THREE.Shape();
    heart.moveTo(0, -0.22);
    heart.bezierCurveTo(-0.12, -0.13, -0.29, 0.02, -0.23, 0.15);
    heart.bezierCurveTo(-0.16, 0.28, -0.045, 0.23, 0, 0.15);
    heart.bezierCurveTo(0.045, 0.23, 0.16, 0.28, 0.23, 0.15);
    heart.bezierCurveTo(0.29, 0.02, 0.12, -0.13, 0, -0.22);
    const gem = new THREE.ExtrudeGeometry(heart, { depth: 0.052, bevelEnabled: true,
      bevelSize: 0.023, bevelThickness: 0.027, bevelSegments: 3, curveSegments: 16 });
    mesh(h, gem, this.tn("#ff4fae"), [0.505, 1.08, 0], [0, PI / 2, 0]);
    mesh(h, gem.clone(), this.tn("#ffc9f0", false), [0.574, 1.09, 0], [0, PI / 2, 0], [0.63, 0.63, 0.38]);
    // Back face: a small rosy heart emblem on the metal cap.
    mesh(h, gem.clone(), this.tn("#ff8acf"), [-0.48, 1.08, 0], [0, -PI / 2, 0], [0.42, 0.42, 0.6]);
    mesh(h, sphere(0.09, 16), this.gem(), [0, 0.86, 0.17]);
    this.bladeBase = pivot(h, [0, 0.41, 0]);
    this.bladeTip = pivot(h, [0, 1.38, 0]);
    this.gripL = pivot(h, [0, 0.04, 0]);
    this.shieldNode = pivot(h, [0, 0.70, 0]);
    this.castPoint = this.bladeTip;
  }

  private buildKatana() {
    const L = this.look;
    const s = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    mesh(s, cyl(0.016, 0.016, 0.26, 10), this.tn(L.band), [0, -0.02, 0]);
    mesh(s, cyl(0.048, 0.048, 0.014, 16), this.tn(L.trim), [0, 0.12, 0]);
    // Keep handle in the right hand; slide the cutting blade into the scabbard
    // as the right hand reaches left hip. Default transform is identical to before.
    const blade = pivot(s, [0, 0, 0]);
    this.katanaBladePivot = blade;
    for (let i = 0; i < 3; i++) {
      mesh(blade, box(0.032, 0.34, 0.008), this.steel(), [0.004 * i * i, 0.3 + i * 0.32, 0], [0, 0, -0.025 * i]);
      mesh(blade, box(0.006, 0.32, 0.011), this.glowMat, [0.016 + 0.004 * i * i, 0.3 + i * 0.32, 0], [0, 0, -0.025 * i]);
    }
    mesh(blade, cyl(0, 0.017, 0.08, 4), this.steel(), [0.022, 1.1, 0], [0, 0, -0.1], [1, 1, 0.3]);
    this.bladeBase = pivot(blade, [0, 0.35, 0]);
    this.bladeTip = pivot(blade, [0.02, 1.12, 0]);
    this.gripL = pivot(s, [0, -0.1, 0]);
    this.shieldNode = pivot(s, [0, 0.5, 0]);
    this.castPoint = this.bladeTip;
    // Scabbard on the left hip.
    mesh(this.torso, cyl(0.022, 0.022, 0.9, 10), this.tn(L.pants), [0.15, -0.05, -0.05], [0.4, 0, 1.25]);
  }

  /**
   * Recurve longbow in the left hand. Limbs run along local +-Z (vertical when the arm points
   * forward); +Y is the archer's side. Thick riser with a leather grip and metal collars,
   * tapered limbs that curve toward the archer and flick away at the recurve tips, glowing
   * runes on the back, and a string (two segments) that the draw hand pulls back.
   */
  private buildBow() {
    const L = this.look;
    const b = pivot(this.hand_l, [0, 0, 0]);
    this.bowPivot = b;
    const wood = this.tn(L.band);
    const dark = this.tn("#2a1712");
    const metal = this.metal();
    // Riser: a solid, slightly sculpted center section.
    mesh(b, box(0.05, 0.055, 0.3), this.tn(L.tunic), [0, -0.012, 0]);
    mesh(b, cyl(0.027, 0.027, 0.13, 12), dark, [0, 0, 0], [PI / 2, 0, 0], [1, 1, 1.15]);
    for (const z of [0.075, -0.075]) mesh(b, cyl(0.031, 0.031, 0.016, 12), metal, [0, 0, z], [PI / 2, 0, 0]);
    mesh(b, box(0.03, 0.02, 0.025), metal, [0, 0.03, 0.09]); // arrow shelf
    mesh(b, sphere(0.02, 10), this.gem(), [0, -0.045, 0]);
    // Limb profile (z, y) from the riser to the tip; mirrored for the lower limb.
    const prof: [number, number][] = [[0.15, 0], [0.27, 0.026], [0.39, 0.065], [0.5, 0.105], [0.59, 0.135], [0.65, 0.14], [0.69, 0.12], [0.72, 0.09]];
    const rad = (i: number) => 0.019 - (0.011 * i) / (prof.length - 1);
    for (const sg of [1, -1]) {
      for (let i = 0; i < prof.length - 1; i++) {
        const p = v(0, prof[i][1], prof[i][0] * sg), q = v(0, prof[i + 1][1], prof[i + 1][0] * sg);
        const d = q.clone().sub(p);
        const len = d.length() + 0.004;
        const rot: V3 = [Math.atan2(d.z, d.y), 0, 0];
        mesh(b, cyl(rad(i + 1), rad(i), len, 8), wood, p.clone().add(q).multiplyScalar(0.5), rot, [1.7, 1, 0.7]);
        if (i > 0 && i < prof.length - 3) {
          const rune = mesh(b, box(0.012, len * 0.8, 0.004), this.glowMat, p.clone().add(q).multiplyScalar(0.5).add(v(0, -0.012, 0)), rot);
          rune.castShadow = false;
        }
      }
      const tip = prof[prof.length - 1];
      mesh(b, cyl(0, 0.012, 0.05, 6), this.tn(L.trim), [0, tip[1] - 0.012, (tip[0] + 0.018) * sg], [sg > 0 ? 0.6 : PI - 0.6, 0, 0]);
    }
    // String: leaves the limbs where the recurve flips; nock point follows the draw hand.
    this.bowNockTop = v(0, 0.14, 0.655);
    this.bowNockBot = v(0, 0.14, -0.655);
    const strMat = M.glow("#f4f0e0");
    this.bowString = [0, 1].map(() => {
      const m = mesh(b, cyl(0.0035, 0.0035, 1, 4), strMat);
      m.castShadow = false;
      return m;
    });
    // Nocked arrow, shown while drawing.
    const ar = pivot(b, [0, 0.14, 0]);
    mesh(ar, cyl(0.006, 0.006, 0.78, 6), this.tn(BROWN), [0, 0.39, 0]);
    mesh(ar, cyl(0, 0.018, 0.07, 6), metal, [0, 0.81, 0]);
    for (const a of [0, PI / 2]) mesh(ar, box(0.04, 0.09, 0.003), this.tn(L.trim), [0, 0.06, 0], [0, a, 0]);
    ar.visible = false;
    this.bowArrow = ar;
    this.layoutBowString(this.bowNockTop.clone().setZ(0));
    this.bladeBase = this.hand_l;
    this.bladeTip = pivot(this.hand_l, [0, -0.12, 0]);
    this.shieldNode = this.hand_l;
    this.castPoint = this.hand_l;
  }

  /** String from tip to nock to tip; the nocked arrow points from the nock past the grip. */
  private layoutBowString(nock: THREE.Vector3) {
    const seg = (m: THREE.Mesh, a: THREE.Vector3, c: THREE.Vector3) => {
      const d = c.clone().sub(a);
      m.position.copy(a).add(c).multiplyScalar(0.5);
      m.quaternion.setFromUnitVectors(_up, d.clone().normalize());
      m.scale.set(1, d.length(), 1);
    };
    seg(this.bowString![0], this.bowNockTop!, nock);
    seg(this.bowString![1], nock, this.bowNockBot!);
    const ar = this.bowArrow!;
    ar.position.copy(nock);
    ar.quaternion.setFromUnitVectors(_up, v(0, -0.05, 0).sub(nock).normalize());
  }

  /** Pull the string toward the draw hand while drawing (0..1). */
  private updateBow() {
    const b = this.bowPivot!;
    const rest = v(0, 0.14, 0);
    let nock = rest;
    if (this.draw > 0.01) {
      b.updateWorldMatrix(true, false);
      const hand = b.worldToLocal(this.hand_r.getWorldPosition(new THREE.Vector3()));
      const pull = hand.sub(rest);
      if (pull.length() > 0.85) pull.setLength(0.85);
      nock = rest.clone().addScaledVector(pull, this.draw);
    }
    this.layoutBowString(nock);
    this.bowArrow!.visible = this.draw > 0.25;
  }

  /** Blood Hunter V2: thin, razor-pointed dual sickles. Keeps existing VRM hand mounts. */
  private buildSickles() {
    const steel = M.toon("#e5e7ef", { rim: 0.95, shade: new THREE.Color("#414252") });
    const edgeSteel = M.toon("#f8faff", { rim: 0.98, shade: new THREE.Color("#a0abbc") });
    const dark = this.tn("#1d1621");
    const iron = this.tn("#52424e");
    const trim = this.tn(this.look.trim);
    const make = (hand: THREE.Object3D, side: number) => {
      const s = pivot(hand, [0, -0.025, 0.03], [PI / 2, 0, side * 0.14]);
      mesh(s, cyl(0.019, 0.023, 0.32, 10), dark, [0, 0.012, 0]);
      for (const y of [-0.12, -0.045, 0.065])
        mesh(s, cyl(0.025, 0.025, 0.009, 10), iron, [0, y, 0]);
      mesh(s, sphere(0.025, 10), trim, [0, -0.15, 0]);
      mesh(s, cyl(0.031, 0.031, 0.018, 12), trim, [0, 0.156, 0]);
      const head = pivot(s);
      head.scale.x = side;
      // Outer edge curves to a single sharp point; inside of the hook is strongly scooped.
      const outline = new THREE.Shape();
      outline.moveTo(-0.013, 0.17);
      outline.bezierCurveTo(0.10, 0.34, 0.32, 0.65, 0.61, 0.70);
      outline.quadraticCurveTo(0.72, 0.72, 0.75, 0.69); // pointed tip
      outline.quadraticCurveTo(0.65, 0.66, 0.55, 0.54);
      outline.bezierCurveTo(0.41, 0.56, 0.29, 0.43, 0.18, 0.29);
      outline.quadraticCurveTo(0.06, 0.18, -0.013, 0.17);
      const bladeGeo = new THREE.ExtrudeGeometry(outline, {
        depth: 0.012, bevelEnabled: true, bevelThickness: 0.0015,
        bevelSize: 0.0015, bevelSegments: 1, curveSegments: 24, steps: 1,
      });
      bladeGeo.translate(0, 0, -0.006);
      mesh(head, bladeGeo, steel);
      // Thin bright steel bevel along the sharpened concave edge; deliberately not a fat tube.
      const edgeLine = new THREE.CubicBezierCurve3(
        v(0.18, 0.29, 0.008), v(0.33, 0.47, 0.008),
        v(0.47, 0.56, 0.008), v(0.735, 0.686, 0.008));
      const edge = mesh(head, new THREE.TubeGeometry(edgeLine, 28, 0.003, 4, false), edgeSteel);
      edge.castShadow = false;
      // Short crimson blood channel (not a glowing neon rope covering the cutting edge).
      const channel = new THREE.CubicBezierCurve3(
        v(0.11, 0.28, 0.010), v(0.22, 0.39, 0.010),
        v(0.36, 0.56, 0.010), v(0.56, 0.61, 0.010));
      const inlay = mesh(head, new THREE.TubeGeometry(channel, 24, 0.0025, 4, false), this.glowMat);
      inlay.castShadow = false;
      // V4: glowing blood mist and crawling crimson energy on EACH blade during the ultimate.
      // All aura meshes are children of the weapon head, so they follow the VRM hands.
      const aura = pivot(head);
      const crimson = M.additive("#ff174b", 0.92);
      const hot = M.additive("#ff91aa", 0.72);
      const arc = new THREE.CatmullRomCurve3([
        v(0.12, 0.29, 0.014), v(0.24, 0.40, 0.015),
        v(0.40, 0.55, 0.015), v(0.58, 0.625, 0.015), v(0.744, 0.688, 0.015),
      ]);
      mesh(aura, new THREE.TubeGeometry(arc, 28, 0.014, 6, false), crimson).castShadow = false;
      mesh(aura, new THREE.TubeGeometry(arc, 28, 0.0045, 5, false), hot,
        [0, 0, 0.007]).castShadow = false;
      for (let i = 0; i < 7; i++) {
        const base = v(0.12 + i * 0.083, 0.29 + Math.sin((i / 6) * 1.5) * 0.32, 0.028);
        const node = mesh(aura, sphere(i % 2 ? 0.016 : 0.012, 8), i % 2 ? crimson : hot, base.toArray() as V3);
        node.castShadow = false;
        this.festivalDrops.push({ node, base, seed: i * 1.4 + (side < 0 ? 3 : 0) });
      }
      aura.visible = false;
      this.festivalAura.push(aura);
      mesh(head, sphere(0.027, 12), this.gem(), [0.05, 0.185, 0.012]);
      return { base: pivot(head, [0.12, 0.26, 0]), tip: pivot(head, [0.75, 0.69, 0]) };
    };
    const right = make(this.hand_r, 1);
    make(this.hand_l, -1);
    this.bladeBase = right.base;
    this.bladeTip = right.tip;
    this.castPoint = this.bladeTip;
    this.shieldNode = this.hand_l;
  }


  private buildDaggers() {
    const dagger = (hand: THREE.Object3D) => {
      const d = pivot(hand, [0, 0, 0], [PI / 2, 0, 0]);
      mesh(d, cyl(0.014, 0.015, 0.12, 10), this.tn(this.look.pants));
      mesh(d, box(0.09, 0.022, 0.03), this.tn(this.look.trim), [0, 0.07, 0]);
      const st = M.toon("#dcd6f0", { rim: 0.8, shade: METAL_SHADE });
      mesh(d, box(0.04, 0.3, 0.01), st, [0, 0.23, 0]);
      mesh(d, cyl(0, 0.02, 0.08, 4), st, [0, 0.42, 0], [0, 0, 0], [1, 1, 0.25]);
      mesh(d, box(0.008, 0.28, 0.013), this.glowMat, [0, 0.23, 0]);
      return d;
    };
    const r = dagger(this.hand_r);
    dagger(this.hand_l);
    this.bladeBase = pivot(r, [0, 0.12, 0]);
    this.bladeTip = pivot(r, [0, 0.46, 0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = this.hand_l;
  }

  /** Bomber: a round black bomb with a lit fuse in the right hand. */
  private buildBomb() {
    const b = pivot(this.hand_r, [0, -0.1, 0.02]);
    mesh(b, sphere(0.1, 16), this.tn("#26262e", true, 0.6));
    mesh(b, cyl(0.035, 0.035, 0.04, 10), this.metal(), [0, 0.1, 0]);
    mesh(b, cyl(0.008, 0.008, 0.07, 6), this.tn("#c9a46a"), [0.02, 0.15, 0], [0, 0, -0.5]);
    mesh(b, sphere(0.022, 8), this.glowMat, [0.04, 0.19, 0]);
    for (const h of [this.hand_r, this.hand_l]) mesh(h, torus(0.045, 0.058), this.tn(this.look.trim), [0, 0.06, 0], [PI / 2, 0, 0], [1, 1, 0.6]);
    this.bladeBase = pivot(this.hand_r, [0, 0.04, 0]);
    this.bladeTip = b;
    this.castPoint = b;
    this.shieldNode = this.hand_l;
  }

  /** Wind dancer: glowing wind wraps around both wrists; the trail follows the right fist. */
  private buildWind() {
    for (const h of [this.hand_r, this.hand_l]) {
      mesh(h, torus(0.05, 0.064), this.glowMat, [0, 0.03, 0], [PI / 2, 0, 0], [1, 1, 0.7]);
      mesh(h, torus(0.046, 0.056), this.tn(this.look.trim), [0, 0.08, 0], [PI / 2, 0, 0], [1, 1, 0.5]);
    }
    this.bladeBase = pivot(this.hand_r, [0, 0.04, 0]);
    this.bladeTip = pivot(this.hand_r, [0, -0.09, 0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = this.hand_l;
  }

  private buildKnuckles() {
    for (const h of [this.hand_r, this.hand_l]) {
      mesh(h, box(0.085, 0.08, 0.095), this.metal(), [0, -0.01, 0]);
      for (let i = 0; i < 3; i++) mesh(h, cyl(0, 0.014, 0.045, 6), this.tn(this.look.trim), [(i - 1) * 0.026, -0.06, 0.02], [PI, 0, 0]);
      mesh(h, box(0.07, 0.012, 0.1), this.glowMat, [0, -0.052, 0]);
    }
    this.bladeBase = this.hand_r;
    this.bladeTip = pivot(this.hand_r, [0, -0.1, 0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = this.hand_l;
  }

  private buildKicks() {
    // Glowing ankle wraps; the trail follows the right foot.
    for (const leg of [this.leg_l, this.leg_r]) {
      mesh(leg, torus(0.045, 0.058), this.glowMat, [0, -0.72, 0], [0, 0, 0], [1, 0.8, 1]);
      mesh(leg, torus(0.052, 0.062), this.tn(this.look.trim), [0, -0.42, 0], [0, 0, 0], [1, 0.6, 1]);
    }
    this.bladeBase = pivot(this.leg_r, [0, -0.45, 0.03]);
    this.bladeTip = this.footR ?? pivot(this.leg_r, [0, -0.8, 0.08]);
    this.castPoint = this.bladeTip;
    this.shieldNode = this.hand_l;
  }

  // ROXY_FROSTWING_SPELLBOOK_V3_20261108: three-dimensional enchanted spellbook.
  // Gold bindings, deep sapphire leather, pale layered pages and a cyan crystal crest.
  private buildRoxySpellbook() {
    const L = this.look;
    // Floating grimoire, not a gun: torso-mounted keeps it from following the casting hand.
    // Local -X is her right side; the book hovers beside her shoulder, spine upright.
    // ROXY V6: float above the actual VRM hand, NOT a fixed torso coordinate.
    // A model-root pivot avoids inheriting the hand's grip/gun rotation.
    const b = pivot(this, [0, 0, 0], [-0.46, -0.26, 0.10]);
    b.scale.setScalar(0.58);
    this.roxyFloatingBook = b;
    const cover = this.tn("#17254b"), gold = this.tn("#e5ac69"), inset = this.tn("#275e88");
    const pages = this.tn("#f1f1df"), edge = this.tn("#a5dffd");
    const back = mesh(b, box(0.53, 0.66, 0.095), cover, [0, 0, 0]);
    back.rotation.y = -0.10;
    mesh(b, box(0.49, 0.62, 0.068), pages, [0.018, 0, 0.056]);
    mesh(b, box(0.51, 0.64, 0.027), cover, [0.018, 0, 0.105]);
    for (const s of [-1, 1]) {
      mesh(b, box(0.51, 0.022, 0.023), gold, [0, s * 0.303, 0.126]);
      mesh(b, box(0.023, 0.61, 0.026), gold, [s * 0.239, 0, 0.126]);
      for (const v of [-1, 1]) mesh(b, box(0.09, 0.09, 0.032), gold, [s * 0.222, v * 0.284, 0.137]);
    }
    mesh(b, box(0.085, 0.64, 0.11), inset, [-0.25, 0, 0.0]);
    for (const y of [-0.23,-0.13,0.13,0.23]) mesh(b, box(0.087, 0.018, 0.13), gold, [-0.25,y,0]);
    const seal = pivot(b, [0.018, 0.0, 0.145], [0,0,Math.PI / 4]);
    mesh(seal, box(0.23, 0.23, 0.026), gold);
    mesh(seal, box(0.16, 0.16, 0.039), inset, [0, 0, 0.02]);
    mesh(seal, sphere(0.075, 12), this.glowMat, [0, 0, 0.06]);
    for (const a of [-1,1]) mesh(b, box(0.08, 0.018, 0.025), edge, [a * 0.11, -0.22, 0.153]);
    this.bladeBase = pivot(b, [0,0.2,0.18]);
    this.bladeTip = pivot(b, [0.0,0.33,0.20]);
    this.castPoint = pivot(b, [0.0,0.33,0.27]);
    this.shieldNode = pivot(this.hand_l, [0, -0.05, 0]);
    this.barrier = pivot(this.shieldNode);
    const disc = mesh(this.barrier, cyl(0.42, 0.42, 0.012, 32), M.water(new THREE.Color(L.glow), 0.3, 1.4));
    disc.castShadow = false;
    mesh(this.barrier, torus(0.4,0.43), M.additive(L.glow,0.9)).castShadow = false;
    this.barrier.visible = false;
  }

  private buildStaff() {
    const L = this.look;
    const s = pivot(this.hand_r, [0, 0, 0]);
    mesh(s, cyl(0.016, 0.016, 1.55, 12), this.tn(L.tunic), [0, 0.2, 0]);
    for (const y of [-0.45, -0.1, 0.3, 0.73]) mesh(s, cyl(0.022, 0.022, 0.035, 12), this.tn(L.trim), [0, y, 0]);
    mesh(s, cyl(0.034, 0.016, 0.08, 12), this.tn(L.trim), [0, 0.99, 0]);
    for (const side of [1, -1]) mesh(s, cyl(0, 0.02, 0.2, 8), this.tn(L.trim), [0.085 * side, 1.08, 0], [0, 0, -0.45 * side]);
    const orb = pivot(s, [0, 1.14, 0]);
    const g = col(L.glow);
    mesh(orb, sphere(0.085, 24), M.water(new THREE.Color(g.r * 0.4, g.g * 0.4, g.b * 0.9), 0.85, 1.7));
    mesh(orb, sphere(0.045, 16), this.glowMat);
    mesh(orb, torus(0.1, 0.118), this.tn(L.trim), [0, 0, 0], [PI / 2, 0, 0]);
    mesh(orb, cyl(0, 0.015, 0.07, 8), this.tn(L.trim), [0, 0.14, 0]);
    mesh(s, cyl(0.02, 0, 0.08, 10), this.tn(L.trim), [0, -0.6, 0]);
    this.bladeBase = pivot(s, [0, 0.75, 0]);
    this.bladeTip = orb;
    this.castPoint = orb;
    // Magic barrier on the free hand, shown only while blocking.
    this.shieldNode = pivot(this.hand_l, [0, -0.05, 0]);
    this.barrier = pivot(this.shieldNode);
    const disc = mesh(this.barrier, cyl(0.42, 0.42, 0.012, 32), M.water(new THREE.Color(g.r * 0.6, g.g * 0.6, g.b), 0.3, 1.4));
    disc.castShadow = false;
    mesh(this.barrier, torus(0.4, 0.43), M.additive(L.glow, 0.9)).castShadow = false;
    this.barrier.visible = false;
  }

  // --- posing ------------------------------------------------------------------------
  /** Exponentially blends joints toward `pose` and applies overlays (walk, breathing, cloth). */
  /** Physical spear choreography. Local +Z is the opponent-facing direction.
   * A spear is not a double glaive: keep its FRONT tip downrange and slide the
   * entire shaft through the two spaced grips during thrusts. No gameplay changes.
   */
  /**
   * Zenith V8 — phase-based, opponent-facing single-head spear choreography.
   * Only the SPEAR MESH, two existing IK grips and MODEL-ONLY procedural bones
   * move here. Fighter root, combat reach, attack windows and network stay untouched.
   * The existing V7 method is kept for recovery/debugging, but is no longer called.
   */
  private updateZenithQiangV8(dt: number) {
    if (!this.glaivePivot || !this.zenithSpearRightGrip) return;
    const cfg = ZENITH_V8_MOTION;
    const spear = this.glaivePivot;
    const pose = this.glaivePose;
    const ageStep = THREE.MathUtils.clamp(dt, 0, 0.09);
    if (pose !== this.zenithV8Pose) {
      this.zenithV8Pose = pose;
      this.zenithV8PoseAge = 0;
      this.zenithV8FromPosition.copy(spear.position);
      this.zenithV8FromRotation.copy(spear.quaternion);
    } else this.zenithV8PoseAge += ageStep;
    const age = this.zenithV8PoseAge;
    const clamp = (n: number) => THREE.MathUtils.clamp(n, 0, 1);
    const smooth = (n: number) => { const u = clamp(n); return u * u * (3 - 2 * u); };
    const snap = (n: number) => { const u = clamp(n); return 1 - Math.pow(1 - u, 4); };
    const L = (a: number, b: number, t: number) => THREE.MathUtils.lerp(a, b, t);
    const vec = (a: readonly number[]) => new THREE.Vector3(a[0], a[1], a[2]);
    const curved = (a: readonly number[], b: readonly number[], c: readonly number[], t: number) => {
      const u = 1 - t;
      return vec(a).multiplyScalar(u * u).addScaledVector(vec(b), 2 * u * t)
        .addScaledVector(vec(c), t * t);
    };

    // Summons deliberately free the hands; twin metal blades take over whenever
    // the main spear is airborne. Existing V5 weapon/catch logic is authoritative.
    const summon = /^znh_[ws]$/.test(pose) || /^znv_[ws]$/.test(pose);
    const held = this.zenithSpearInHand && !summon;
    spear.visible = held;
    const freeLead = /^znc_[ws]$/.test(pose) || /^zncatch_[ws]$/.test(pose);
    this.gripL = held && !freeLead ? this.zenithSpearGrip : null;
    if (this.vrmRig) {
      this.vrmRig.spearGripR = held ? this.zenithSpearRightGrip : null;
      this.vrmRig.gripL = this.gripL;
    }
    if (!held) {
      if (this.zenithSpearGrip) this.zenithSpearGrip.position.y = cfg.leadGripGuard;
      // No spear in hand: let the twin-blade, charge and V pose layers lead.
      this.hips.position.x = 0;
      this.hips.position.z = 0;
      this.hips.rotation.y = 0;
      return;
    }

    // Each tuple describes three distinct TIP DIRECTIONS and a winding/landing
    // offset for the ENTIRE shaft. Directions remain positive-Z: no rear blade.
    // A quadratic Bezier through the middle control makes the arc visible.
    const routes: Record<number, {
      wind: [number,number,number]; middle: [number,number,number]; hit: [number,number,number];
      back: [number,number,number]; arc: [number,number,number]; front: [number,number,number];
      twist: number;
    }> = {
      1: {wind:[-0.13,0.09,1],middle:[-0.045,0.04,1],hit:[0,0.015,1],
          back:[-0.055,0,-0.17],arc:[-0.02,0.005,0.02],front:[0.015,0.00,0.19],twist:-0.75},
      2: {wind:[0.26,-0.32,1],middle:[0.05,-0.01,1],hit:[-0.18,0.27,1],
          back:[0.14,-0.15,-0.12],arc:[0.035,-0.005,0.05],front:[-0.07,0.105,0.12],twist:0.85},
      3: {wind:[-0.38,0.10,1],middle:[0.03,0.18,1],hit:[0.33,0.08,1],
          back:[-0.19,0.045,-0.11],arc:[0.015,0.08,0.08],front:[0.20,0.03,0.09],twist:-1.0},
      4: {wind:[0.32,-0.28,1],middle:[-0.25,-0.31,1],hit:[-0.10,0.30,1],
          back:[0.12,-0.13,-0.15],arc:[-0.155,-0.14,0.04],front:[-0.06,0.12,0.12],twist:0.94},
      5: {wind:[-0.21,0.08,1],middle:[-0.08,0.015,1],hit:[0,0.01,1],
          back:[-0.09,0,-0.22],arc:[-0.04,0.008,0.09],front:[0.0,0.0,0.30],twist:-0.5},
    };

    // Base guard is a two-hand shaft line, not a rotating glaive grip.
    let tip = new THREE.Vector3(0.025, 0.13, 1);
    let offset = new THREE.Vector3(-0.095, 0.03, 0.18);
    let thrust = 0;
    let drive = 0;
    let turn = 0;
    let plant = 0;
    const light = /^zn([1-5])_([ws])$/.exec(pose);
    const isWind = light?.[2] === "w";
    const isHit = light?.[2] === "s";
    if (light) {
      const step = Number(light[1]);
      const path = routes[step];
      const sign = step % 2 === 1 ? 1 : -1; // alternate stepping feet
      if (isWind) {
        // Slow anticipation: pull weapon across and toward the rear hip.
        const a = smooth(age / cfg.windupSeconds);
        tip.lerp(vec(path.wind), a);
        offset.lerp(vec(path.back).add(new THREE.Vector3(-0.095,0.03,0.18)), a);
        const flower = cfg.spearFlower * Math.sin(Math.PI * a);
        tip.x += sign * flower;
        tip.y += flower * 0.7;
        turn = path.twist * cfg.torsoYaw * a * -0.52;
        plant = sign * cfg.stepDistance * a * 0.38;
      } else {
        // Phase 1: fast ease-out snap along a DIFFERENT tip curve for each hit.
        const p = snap(age / cfg.snapSeconds);
        const midDir = vec(path.wind).lerp(vec(path.middle), cfg.tipArc);
        const midPos = vec(path.back).lerp(vec(path.arc), cfg.tipArc);
        tip = curved(path.wind, [midDir.x,midDir.y,midDir.z], path.hit, p);
        const pathPos = curved(path.back, [midPos.x,midPos.y,midPos.z], path.front, p);
        offset.add(pathPos);
        thrust = p;
        // V9 Phantom Fang: five ultra-quick forward tip pulses, staying narrow,
        // without increasing reach, moving Fighter.root, or turning into a staff spin.
        if (step === 5) {
          const flicker = Math.sin(age * 93);
          tip.x += flicker * 0.08;
          tip.y += Math.cos(age * 93) * 0.025;
          offset.z += Math.max(0, flicker) * 0.035;
        }
        // Phase 2: tiny physical overshoot, then damped, poised recovery.
        const o = (age - cfg.snapSeconds) / cfg.overshootSeconds;
        const overshoot = o > 0 && o < 1 ? Math.sin(Math.PI * o) : 0;
        offset.z += cfg.thrustOvershoot * overshoot;
        tip.y += 0.025 * overshoot;
        const settle = smooth((age - cfg.snapSeconds - cfg.overshootSeconds) / cfg.settleSeconds);
        if (settle > 0) {
          tip.lerp(vec(path.hit).lerp(new THREE.Vector3(0.035,0.12,1),0.33), settle);
          offset.z -= (step === 5 ? 0.16 : 0.075) * settle;
        }
        drive = p * (1 - settle * 0.54);
        turn = path.twist * cfg.torsoYaw * drive;
        plant = sign * (cfg.stepDistance + (step === 5 ? cfg.lungeStep : 0)) * drive;
        thrust = p * (1 - settle * 0.85);
      }
    } else if (pose === "idle" || pose === "walk") {
      // Narrow figure-eight; never a full staff spin. Footstep sway opposes stride.
      const t = this.t;
      const calm = 1 - clamp(this.walk);
      tip.x += cfg.idleFigureEight * calm * Math.sin(t * 1.9);
      tip.y += cfg.idleFigureEight * calm * 0.55 * Math.sin(t * 3.8);
      offset.y += cfg.idleBob * calm * Math.sin(t * 1.9);
      tip.x -= Math.sin(this.walkPhase) * cfg.walkCounterSway * clamp(this.walk);
      offset.x -= Math.sin(this.walkPhase) * cfg.walkCounterSway * 0.36 * clamp(this.walk);
    } else if (pose === "block") {
      // Tip angled above the lead shoulder; diagonal shaft sweep on block entry.
      const guardSweep = Math.sin(Math.PI * smooth(age / 0.17));
      // receiveHit() already sets model.recoil on a successful block;
      // use that visual signal rather than adding any gameplay callback.
      const deflect = clamp((this.recoil - 0.10) / 0.60);
      tip.set(-0.30 + guardSweep * 0.17 + deflect * 0.15,0.55 - deflect * 0.09,0.86);
      offset.set(-0.05 + deflect * 0.045,0.16,0.13 - deflect * 0.05);
      turn = -0.09 * guardSweep;
      plant = -0.02;
    } else if (pose === "zncatch_w" || pose === "zncatch_s") {
      // Catch: pull the shaft back toward her shoulder, then absorb recoil.
      const c = smooth(age / (pose === "zncatch_w" ? 0.18 : 0.22));
      tip.set(-0.20 * (1-c),0.42 - 0.25*c,1);
      offset.set(-0.10,0.15 - 0.10*c,0.01 + 0.14*c);
      turn = -0.10*(1-c);
    } else if (pose === "znz_w" || pose === "znz_s") {
      // Javelin draw and release, with the tip always pointing downrange.
      const t = pose.endsWith("_w") ? smooth(age / 0.18) : snap(age / 0.12);
      tip.set(pose.endsWith("_w") ? -0.27 : 0.015,pose.endsWith("_w") ? 0.48 : 0.10,1);
      offset.set(-0.14,pose.endsWith("_w") ? 0.21 : 0.08,pose.endsWith("_w") ? 0.06 - 0.12*t : 0.26*t);
      turn = pose.endsWith("_w") ? -0.10*t : 0.16*t;
      plant = pose.endsWith("_s") ? cfg.stepDistance * t : 0;
    } else if (/^znx_[ws]$/.test(pose)) {
      const u = pose.endsWith("_s") ? snap(age / 0.13) : smooth(age / 0.13);
      tip.set(L(-0.20,0.10,u),L(-0.02,0.12,u),1);
      offset.z += (pose.endsWith("_s") ? 0.12 : -0.09) * u;
      turn = -0.10 + 0.17*u;
    } else if (/^znc_[ws]$/.test(pose)) {
      // The lead hand is free to command magnetic pull/repel.
      tip.set(-0.22,0.19,1);
      offset.set(-0.18,-0.02,0.11);
    } else {
      // Unrecognized utility pose: no unwanted staff spins or aggressive resets.
      tip.set(0.02,0.14,1);
    }

    // Rear-hand drive / lead-hand guide: the left hand physically slides toward
    // the rear grip during a thrust, then naturally returns along the shaft.
    const gripTravel = cfg.leadGripGuard - cfg.leadGripExtension;
    if (this.zenithSpearGrip)
      this.zenithSpearGrip.position.y = cfg.leadGripGuard - gripTravel * thrust;
    if (this.zenithSpearRightGrip) this.zenithSpearRightGrip.position.y = -0.02;

    // Point the single blade along the evaluated tip path. We deliberately do
    // NOT exponentially slerp to a static aim: path interpolation is phase based.
    tip.normalize();
    const desiredQ = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),tip);
    this.updateMatrixWorld(true);
    const torso = this.worldToLocal(this.torso.getWorldPosition(new THREE.Vector3()));
    const desiredPos = torso.add(offset);
    const entry = smooth(age / cfg.poseEntrySeconds);
    spear.position.copy(this.zenithV8FromPosition).lerp(desiredPos, entry);
    spear.quaternion.copy(this.zenithV8FromRotation).slerp(desiredQ, entry);

    // Whole-body martial transfer: model-only knee drop, side-to-side lead-foot
    // plant, pelvic torque followed by shoulders. NEVER move Fighter.root.
    const kick = Math.abs(plant);
    const sided = Math.sign(plant);
    this.hips.position.x = sided * Math.min(0.055, kick * 0.30);
    this.hips.position.z = kick; // purely animated VRM pelvis, no hitbox movement
    this.hips.position.y -= cfg.stanceDepth * Math.min(1,drive);
    this.hips.rotation.y = turn * cfg.hipYaw / Math.max(0.001,cfg.torsoYaw);
    this.torso.rotation.y += turn;
    this.torso.rotation.x += 0.035 * drive;
    this.head.rotation.y -= turn * 0.20;
    this.leg_l.rotation.x -= (sided > 0 ? 0.28 : -0.11) * Math.min(1,kick / Math.max(0.001,cfg.lungeStep));
    this.leg_r.rotation.x -= (sided < 0 ? 0.28 : -0.11) * Math.min(1,kick / Math.max(0.001,cfg.lungeStep));
  }

  private updateZenithForwardSpear(dt: number) {
    if (!this.glaivePivot || !this.zenithSpearRightGrip) return;
    const pose = this.glaivePose;
    // Overhead charged/V summons have their own lifted-arm pose. During the
    // summon the real spear disappears, while the conjured spear still flies.
    const summon = /^znh_[ws]$/.test(pose) || /^znv_[ws]$/.test(pose);
    const held = this.zenithSpearInHand && !summon;
    this.glaivePivot.visible = held;
    this.gripL = held && !/^znc_[ws]$/.test(pose) && !/^zncatch_[ws]$/.test(pose)
      ? this.zenithSpearGrip : null;
    if (this.vrmRig) {
      this.vrmRig.spearGripR = held ? this.zenithSpearRightGrip : null;
      this.vrmRig.gripL = this.gripL;
    }
    if (!held) return; // Twin blades/airborne spear keep their own animations.

    const finish = /^zn[1-5]_s$/.test(pose);
    const prepare = /^zn[1-5]_w$/.test(pose);
    const catching = pose === "zncatch_w" || pose === "zncatch_s";
    // Each strike has its own point-line: straight, rising, angled, low, lunge.
    // None flips the spear tip toward Zenith or presents a rear blade.
    const aim: Record<string, [number, number, number]> = {
      zn1_w: [-0.10, 0.13, 1], zn1_s: [0.01, 0.02, 1],
      zn2_w: [0.17, -0.16, 1], zn2_s: [-0.08, 0.20, 1],
      zn3_w: [-0.18, 0.10, 1], zn3_s: [0.15, 0.07, 1],
      zn4_w: [0.17, 0.13, 1], zn4_s: [-0.11, -0.28, 1],
      zn5_w: [-0.12, 0.19, 1], zn5_s: [0.0, -0.01, 1],
      znz_w: [-0.24, 0.48, 1], znz_s: [0.0, 0.06, 1],
      znx_w: [-0.12, 0.12, 1], znx_s: [0.05, 0.05, 1],
      znc_w: [0.13, 0.18, 1], znc_s: [0.16, 0.12, 1],
      zncatch_w: [-0.26, 0.42, 1], zncatch_s: [0.05, 0.15, 1],
      block: [0.02, 0.26, 1],
    };
    const moving = THREE.MathUtils.clamp(this.walk, 0, 1);
    const [ax, ay, az] = aim[pose] ?? [0.04, 0.12 + 0.13 * moving, 1];
    // Small rhythmic steps, not wide staff spins; root faces the target already.
    const desired = new THREE.Vector3(ax, ay, az).normalize();
    const targetQ = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), desired);
    const rate = catching ? 24 : finish ? 32 : prepare ? 18 : 14;
    const s = 1 - Math.exp(-rate * Math.min(dt, 0.1));
    this.glaivePivot.quaternion.slerp(targetQ, s);

    // Right hand ~waist-high, near body. Left hand 0.32m ahead on shaft.
    // Thrusts translate the FULL weapon along +Z so the tip travels straight.
    this.updateMatrixWorld(true);
    const torso = this.worldToLocal(this.torso.getWorldPosition(new THREE.Vector3()));
    const zShift = finish ? (pose === "zn5_s" ? 0.27 : 0.16)
      : prepare ? -0.10 : pose === "znz_w" ? -0.13 : 0;
    const yShift = pose === "zn4_s" ? -0.12 : pose === "zn2_s" ? 0.07
      : pose === "zncatch_w" ? 0.16 : 0;
    const target = torso.add(new THREE.Vector3(-0.09, 0.035 + yShift, 0.18 + zShift));
    // Catch: the returning mass pushes her shoulder back, then she settles
    // into the two-hand guard instead of snapping the spear sideways.
    if (pose === "zncatch_w") target.z -= 0.16;
    this.glaivePivot.position.lerp(target, s);
  }

  /** Align a procedural arm with a physical shaft grip for fallback bodies.
   * VRM rigs use two-bone IK independently; no staff/glaive wrist tricks.
   */
  private reachZenithGrip(side: "left" | "right", target: THREE.Object3D) {
    const arm = side === "left" ? this.arm_l : this.arm_r;
    const hand = side === "left" ? this.hand_l : this.hand_r;
    this.updateMatrixWorld(true);
    const goal = this.torso.worldToLocal(target.getWorldPosition(new THREE.Vector3()));
    const delta = goal.sub(arm.position);
    if (delta.lengthSq() < 0.0001) return;
    arm.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), delta.normalize());
    hand.rotation.set(0, 0, 0);
  }

  blend(pose: Pose, dt: number, speed: number, actionPose = "") {
    if (this.zenithCatchAura) {
      this.zenithCatchAura.visible = this.zenithCatchShieldT > 0;
      this.zenithCatchAura.rotation.y += dt * 2.5;
      this.zenithCatchAura.rotation.z = 0.10 * Math.sin(this.t * 3.2);
      this.zenithCatchAura.scale.setScalar(0.90 + 0.07 * Math.sin(this.t * 4.7));
    }
    if (this.zenithTwinBlades.length) {
      if (!this.zenithSpearInHand) {
        const left = /znt[24]_/.test(this.glaivePose);
        const side = left ? 1 : 0;
        if (this.zenithTwinBases[side]) this.bladeBase = this.zenithTwinBases[side];
        if (this.zenithTwinTips[side]) this.bladeTip = this.zenithTwinTips[side];
      }
      for (let i = 0; i < this.zenithTwinBlades.length; i++) {
        const blade = this.zenithTwinBlades[i];
        // A visible inward-cross on combo 5, otherwise compact alternating slashes.
        const crossing = this.glaivePose === "znt5_s" || this.glaivePose === "zntx_s";
        const anim = this.glaivePose.startsWith("znt") ? Math.sin(this.t * 26 + i * 2) * 0.11 : 0;
        const want = crossing ? (i === 0 ? -0.72 : 0.72) : (i === 0 ? 0.14 : -0.14) + anim;
        blade.rotation.z = THREE.MathUtils.damp(blade.rotation.z, want, 24, dt);
      }
    }
    if (this.katanaBladePivot) {
      // The hand moves to the scabbard via the Kaede-C pose; the curved blade
      // slides through the hilt into its sheathed position with smooth follow-through.
      this.katanaSheathAmount = THREE.MathUtils.damp(
        this.katanaSheathAmount, this.katanaSheathProgress, 18, dt);
      this.katanaBladePivot.position.y = -1.05 * this.katanaSheathAmount;
      this.katanaBladePivot.visible = this.katanaSheathAmount < 0.99;
    }
    if (this.nesaHammerPivot) {
      // NESA_HEART_SMASH_V4: horizontal, Beyblade-style hammer shaft during charged spin.
      const value = THREE.MathUtils.clamp(this.nesaHammerScale, 1, 4);
      const current = this.nesaHammerPivot.scale.x;
      this.nesaHammerPivot.scale.setScalar(THREE.MathUtils.damp(current, value, value > current ? 8 : 13, dt));
      const flat = THREE.MathUtils.clamp(this.nesaSpinHorizontal, 0, 1);
      this.nesaHammerPivot.rotation.z = THREE.MathUtils.damp(this.nesaHammerPivot.rotation.z,
        -Math.PI * 0.5 * flat, flat > 0 ? 28 : 15, dt);
    }
    const k = 1 - Math.exp(-speed * dt);
    for (const j of JOINTS) {
      const t = (pose as any)[j] as number[];
      this.cur[j].lerp(new THREE.Vector3(t[0], t[1], t[2]), k);
    }
    this.hipsY += (pose.hips_y - this.hipsY) * k;
    const kn = pose.knee ?? [0, 0];
    this.knee[0] += (kn[0] - this.knee[0]) * k;
    this.knee[1] += (kn[1] - this.knee[1]) * k;
    this.t += dt;
    // Book placement happens after vrmRig.update below, when the visual
    // wrist has reached its final animated location for this frame.
    // 0.64 = ordinary walking; 1 = full sprint; each kit uses its own gait rate.
    const running = THREE.MathUtils.clamp((this.walk - 0.66) / 0.34, 0, 1);
    const moving = Math.min(1, this.walk / 0.64);
    this.walkPhase += dt * (this.kit === "knight" && this.look.element === "light" ? 9.2 : (this.kit === "greatsword" || this.kit === "hammer") ? 8.5 : 11) * moving * (1 + 0.46 * running);
    const s = Math.sin(this.walkPhase);
    if (this.kit === "hammer") {
      // Weight-specific walking is handled below by short steps and shoulder lag.
      this.walkPhase += Math.sin(this.t * 1.1) * 0.0004 * moving;
    }
    this.recoil = Math.max(this.recoil - dt * 5, 0);
    this.hips.position.y = HIP + this.hipsY + Math.abs(s) * 0.03 * this.walk + Math.sin(this.t * 2.4) * 0.005;
    for (const j of JOINTS) this.joints[j].rotation.set(this.cur[j].x, this.cur[j].y, this.cur[j].z);
    this.torso.rotation.x += -this.recoil * 0.3 + Math.sin(this.t * 2.4) * 0.012;
    const stride = this.kit === "knight" && this.look.element === "light" ? 0.44 : (this.kit === "greatsword" || this.kit === "hammer") ? 0.36 : 0.55;
    this.leg_l.rotation.x += s * stride * moving * (1 + 0.34 * running);
    this.leg_r.rotation.x -= s * stride * moving * (1 + 0.34 * running);
    // Distinct full-body running pose for the procedural fallback body.
    this.torso.rotation.x += running * ((this.kit === "greatsword" || this.kit === "hammer") ? 0.08 : 0.13);
    this.arm_l.rotation.x -= s * 0.17 * running;
    this.arm_r.rotation.x += s * 0.14 * running;
    // ROXY V5: free, palm-up right hand supports the levitating grimoire.
    // Applies only to locomotion/idle; attacks, blocks and hit reactions keep original poses.
    if (this.look.element === "frost") {
      // Persistent gesture weight, unlike resetting the joint blend each frame.
      const target = !this.combat && !this.hurt && this.walk < 0.72 ? 1 : 0;
      this.roxyOpenPalm = THREE.MathUtils.damp(this.roxyOpenPalm, target, 9, dt);
      this.arm_r.rotation.x = THREE.MathUtils.lerp(this.arm_r.rotation.x, -0.95, this.roxyOpenPalm);
      this.arm_r.rotation.z = THREE.MathUtils.lerp(this.arm_r.rotation.z, -0.36, this.roxyOpenPalm);
      this.hand_r.rotation.x = THREE.MathUtils.lerp(this.hand_r.rotation.x, 1.15, this.roxyOpenPalm);
      this.hand_r.rotation.z = THREE.MathUtils.lerp(this.hand_r.rotation.z, 0.16, this.roxyOpenPalm);
    }
    this.hips.position.y += Math.abs(s) * 0.018 * running;

    if (actionPose.startsWith("pc_")) {
      const phase = THREE.MathUtils.clamp(Math.abs(this.parryCounterSpin) / (Math.PI * 2), 0, 1);
      const turn = Math.sin(this.parryCounterSpin) * 0.68;
      const snap = Math.sin(phase * Math.PI);
      switch (this.kit) {
        case "knight":
          this.torso.rotation.y += turn * 0.18;
          this.torso.rotation.x += 0.06 * snap;
          this.arm_r.rotation.x += 0.22 + 0.08 * snap;
          this.arm_r.rotation.z -= 0.16;
          this.hand_r.rotation.z -= 0.22;
          this.arm_l.rotation.x -= 0.10;
          this.cape.rotation.z += Math.sin(turn) * 0.10;
          break;
        case "greatsword":
          this.torso.rotation.y += turn * 0.22;
          this.torso.rotation.x += 0.08 * snap;
          this.arm_r.rotation.x += 0.24;
          this.arm_l.rotation.x += 0.18;
          this.hand_r.rotation.z -= 0.26;
          break;
        case "hammer":
          this.torso.rotation.y += turn * 0.23;
          this.torso.rotation.x += 0.10 * snap;
          this.arm_r.rotation.x += 0.26;
          this.arm_l.rotation.x += 0.16;
          this.hand_r.rotation.z -= 0.20;
          this.cape.rotation.z += Math.sin(turn) * 0.06;
          break;
        case "katana":
          this.torso.rotation.y += turn * 0.21;
          this.torso.rotation.x += 0.03 * snap;
          this.arm_r.rotation.x += 0.18;
          this.hand_r.rotation.z -= 0.28;
          this.arm_l.rotation.x -= 0.05;
          break;
        case "assassin":
          this.torso.rotation.y += turn * 0.28;
          this.torso.rotation.x += 0.05 * snap;
          this.head.rotation.y -= turn * 0.10;
          this.arm_r.rotation.x += 0.12;
          this.arm_l.rotation.z += 0.34;
          break;
        case "knuckles":
          this.torso.rotation.y += turn * 0.30;
          this.torso.rotation.x += 0.04 * snap;
          this.arm_r.rotation.x += 0.20;
          this.arm_l.rotation.x += 0.12;
          this.arm_r.rotation.z -= 0.10;
          this.arm_l.rotation.z += 0.10;
          break;
        case "kicks":
          this.torso.rotation.y += turn * 0.55;
          this.torso.rotation.x += 0.05 * snap;
          this.leg_r.rotation.x -= 0.30 * snap;
          this.leg_r.rotation.z -= 0.62;
          this.leg_l.rotation.x += 0.12;
          this.arm_r.rotation.z -= 0.18;
          this.arm_l.rotation.z += 0.18;
          break;
        case "wind":
          this.torso.rotation.y += turn * 0.33;
          this.torso.rotation.x += 0.04 * snap;
          this.arm_r.rotation.x += 0.12;
          this.arm_l.rotation.x += 0.08;
          this.head.rotation.y -= turn * 0.06;
          break;
        case "sickle":
          this.torso.rotation.y += turn * 0.24;
          this.torso.rotation.x += 0.05 * snap;
          this.arm_r.rotation.x += 0.18;
          this.hand_r.rotation.z -= 0.24;
          this.arm_l.rotation.x -= 0.04;
          break;
        case "chainblade":
          this.torso.rotation.y += turn * 0.23;
          this.torso.rotation.x += 0.06 * snap;
          this.arm_r.rotation.x += 0.18;
          this.arm_l.rotation.x += 0.10;
          this.hand_r.rotation.z -= 0.18;
          break;
        case "glaive":
          this.torso.rotation.y += turn * 0.22;
          this.torso.rotation.x += 0.05 * snap;
          this.arm_r.rotation.x += 0.16;
          this.arm_l.rotation.x += 0.08;
          if (this.glaivePivot) this.glaivePivot.rotation.z += Math.sin(turn) * 0.10;
          break;
        case "mage":
          this.torso.rotation.y += turn * 0.16;
          this.torso.rotation.x += 0.02 * snap;
          this.arm_r.rotation.x += 0.10;
          this.hand_r.rotation.z -= 0.20;
          this.arm_l.rotation.z += 0.08;
          break;
        case "bow":
          this.torso.rotation.y += turn * 0.18;
          this.torso.rotation.x += 0.02 * snap;
          this.arm_r.rotation.x += 0.06;
          this.arm_l.rotation.x += 0.10;
          this.head.rotation.y -= turn * 0.08;
          break;
        case "bomb":
          this.torso.rotation.y += turn * 0.17;
          this.torso.rotation.x += 0.03 * snap;
          this.arm_r.rotation.x += 0.12;
          this.arm_l.rotation.z += 0.10;
          break;
      }
    }
    if (this.kit === "knight" && this.look.element === "light") {
      // ASTER_KNIGHT_COMBAT_ANIM_V2: grounded, upright armor gait; shoulders, not hips, do the work.
      this.torso.rotation.x += 0.025 + 0.045 * running;
      this.torso.rotation.y += Math.sin(this.walkPhase) * 0.018 * moving;
      this.head.rotation.x -= 0.025;
      this.arm_l.rotation.x -= 0.045 * moving; // shield stays near the center while walking
      this.hips.position.y -= 0.008 * (1 - running);
    }
    if (this.kit === "hammer") {
      // NESA_NO_FOOT_HEAVINESS_V1:
      // keep the burden in her upper body, not in dragging heavy feet.
      this.torso.rotation.x += 0.08 + 0.10 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.04 * moving;
      this.head.rotation.x -= 0.05;
      // V5: feet and knees stay upright; weight reads only in arms and torso.
      this.hips.position.y += 0;
      // Let the legs move more naturally; the struggle should read in shoulders / arms.
      this.leg_l.rotation.x *= 0.95;
      this.leg_r.rotation.x *= 0.95;
      this.arm_l.rotation.x -= 0.06 + 0.03 * moving;
      this.arm_r.rotation.x += 0.04 + 0.02 * moving;
      this.arm_l.rotation.z -= 0.06;
      this.arm_r.rotation.z += 0.04;
    }
    // NYX_SHADOW_COMBAT_AIR_2_V1: lively side-to-side ninja footwork, not a heavy gait.
    // While moving she shifts through her shoulders; in guard she stays compact.
    if (this.kit === "assassin") {
      this.torso.rotation.x += 0.035 + 0.060 * moving;
      this.torso.rotation.y += Math.sin(this.walkPhase) * 0.045 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.018 * moving;
      this.head.rotation.y -= Math.sin(this.walkPhase) * 0.025 * moving;
      this.hips.position.y += Math.abs(Math.sin(this.walkPhase * 2)) * 0.009 * moving;
    }
    // Veyr's low stalking posture also animates the procedural fallback (no VRM yet).
    if (this.kit === "sickle") {
      const stalking = this.walk;
      this.torso.rotation.x += 0.10 + 0.14 * stalking;
      this.head.rotation.x -= 0.065;
      this.head.rotation.y += Math.sin(this.t * 1.7) * 0.026 * (1 - stalking) * (this.combat ? 0.25 : 1);
      this.leg_l.rotation.z += 0.07;
      this.leg_r.rotation.z -= 0.07;
      this.hips.position.y -= 0.035 + 0.025 * stalking;
    }

    this.cape.rotation.set(0.08 + 0.3 * this.walk + 0.3 * this.recoil + Math.sin(this.t * 2.1) * 0.03, 0, Math.sin(this.t * 1.7) * 0.03);
    this.hairSway.forEach((h, i) => { h.rotation.x = 0.1 * this.walk + 0.25 * this.recoil + Math.sin(this.t * 2 + i) * 0.05; });
    if (actionPose.startsWith("pc_")) {
      const turn = this.parryCounterSpin;
      const follow = Math.sin(Math.min(1, turn / (Math.PI * 2)) * Math.PI);
      this.cape.rotation.y += Math.sin(turn - 0.65) * 0.20 * follow;
      this.hairSway.forEach((h, i) => { h.rotation.z += Math.sin(turn - 0.35 + i * 0.42) * 0.13 * follow; });
    }
    // Different actual polearm arcs: direct thrust, reverse-end slash, figure-eight rise,
    // and pivot cleave. All rotations are local to the weapon: one motion path for VRM and
    // procedural character, and the left-hand IK follows the same physical shaft.
    if (this.glaivePivot && this.look.element === "metal" && this.zenithSpearRightGrip) {
      this.updateZenithQiangV8(dt);
    } else if (this.glaivePivot) {
      // Attack pose angles are independent of the VRM clip. Narrow wrist turns
      // produce a direct, forward thrust instead of Zarek's wide blade arcs.
      const angles: Record<string, [number, number, number]> = {
        zn1_w: [1.52,-0.17,0.03], zn1_s: [1.16,0.11,-0.06],
        zn2_w: [1.66,0.23,0.08], zn2_s: [1.20,-0.15,-0.07],
        zn3_w: [1.57,-0.13,0.08], zn3_s: [1.08,0.13,-0.04],
        zn4_w: [1.70,0.20,0.24], zn4_s: [1.16,-0.18,-0.25],
        zn5_w: [1.69,-0.24,0.05], zn5_s: [0.99,0.20,-0.10],
        znh_w: [1.79,-0.18,0.15], znh_s: [1.03,0.18,-0.08],
        znz_w: [1.76,-0.20,0.10], znz_s: [1.08,0.12,-0.08],
        znx_w: [1.52,-0.12,0.04], znx_s: [1.11,0.13,0],
        znc_w: [1.43,0.18,0.12], znc_s: [1.37,-0.16,-0.12],
        znv_w: [1.90,0.0,0.03], znv_s: [2.08,0.10,0.05],
        idle: [PI / 2, 0, 0], block: [PI / 2, -0.17, -0.08],
        gl1_w: [1.48, -0.53, -0.16], gl1_s: [0.89, 0.21, 0.14],
        gl2_w: [1.80, 0.64, 0.35], gl2_s: [1.34, -0.83, -0.30],
        gl3_w: [2.17, -0.58, -0.16], gl3_s: [0.92, 0.78, 0.22],
        gl4_w: [1.44, 0.70, 0.50], gl4_s: [2.08, -0.73, -0.45],
        gl5_w: [2.12, 0.53, 0.32], gl5_s: [1.18, -0.97, -0.42],
        glx_turn: [1.95, -0.90, -0.33], glc_launch: [2.28, -0.32, -0.20], glc_finish: [0.85, 0.90, 0.35],
        glh_w: [2.00, -0.50, 0.22], glh_s: [0.93, 0.68, -0.26],
        glz_w: [1.64, -0.46, -0.28], glz_s: [1.05, 0.70, 0.26],
        glx_w: [1.35, -0.36, 0.14], glc_w: [2.00, -0.58, -0.10],
        glc_s: [0.93, 0.72, 0.22],
      };
      const a = angles[this.glaivePose] ?? angles.idle;
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));
      // Choreographed Zarek baton flourish: two smooth rotations, then a readable hold.
      // Never used by an attack; the visual's weapon mount still follows both hands.
      if (this.glaivePose === "show_baton") {
        const phase = this.presentationMode === "select" ? this.presentationT % 6.2 : this.presentationT;
        const turn = THREE.MathUtils.smoothstep(phase, 0.55, 1.53) * (Math.PI * 4)
          + THREE.MathUtils.smoothstep(phase, 1.53, 2.29) * (Math.PI * 2)
          + (this.presentationMode === "select"
            ? THREE.MathUtils.smoothstep(phase, 4.19, 5.36) * (Math.PI * 2) : 0);
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), turn));
      }
      // Live figure-eight spin around the weapon shaft (kept local so both hands follow).
      if (this.glaivePose === "glz_s" || this.glaivePose === "gl3_s" ||
          this.glaivePose === "glc_launch") {
        const roll = Math.sin(this.t * 19) * 0.38;
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), roll));
      }
      const rate = this.glaivePose.endsWith("_s") ? 38 : 19;
      this.glaivePivot.quaternion.slerp(q, 1 - Math.exp(-rate * dt));
    }
    // NYTHERA_SHOWCASE_SPIN_TOSS_V3 — offhand releases for presentation spins/toss only.
    const tShow = this.presentationT;
    const oneHandFlourish = (tShow >= 0.78 && tShow < 1.22) ||
      (tShow >= 2.34 && tShow < 3.13) ||
      (tShow >= 5.69 && tShow < 6.24);
    const airborneWeapon = tShow >= 3.13 && tShow < 5.52;
    const noScytheGrip = this.kit === "scythe" && this.glaivePose === "nythera_show" &&
      this.presentationMode === "select" && (oneHandFlourish || airborneWeapon);
    if (this.vrmRig && this.kit === "scythe") this.vrmRig.gripL = noScytheGrip ? null : this.gripL;
    if (this.look.element === "metal" && this.zenithSpearRightGrip &&
        this.zenithSpearInHand && this.glaivePivot?.visible) {
      this.reachZenithGrip("right", this.zenithSpearRightGrip);
      if (this.gripL) this.reachZenithGrip("left", this.gripL);
    } else if (this.gripL && !noScytheGrip) this.reachGrip();
    this.vrmRig?.update(dt, { t: this.t, walk: this.walk, phase: this.walkPhase, crouch: this.hipsY, combat: this.combat, hurt: this.hurt, draw: this.draw, knee: this.knee, pose: actionPose });
    // ROXY V6: correct both procedural and VRM grimoire placement, every frame.
    if (this.roxyFloatingBook) {
      const hand = this.vrmRig?.vrm.humanoid.getNormalizedBoneNode("rightHand") ?? this.hand_r;
      const palm = this.worldToLocal(hand.getWorldPosition(new THREE.Vector3()));
      // Outside the right wrist, slightly up and forward: no intersection
      // with the forearm, face, or hat while the hand changes pose.
      const hover = 0.15 + Math.sin(this.t * 2.3) * 0.022;
      const pos = palm.add(new THREE.Vector3(-0.055, hover, 0.17));
      this.roxyFloatingBook.position.copy(pos);
      this.roxyFloatingBook.rotation.set(-0.46 + Math.sin(this.t * 1.6) * 0.035,
        -0.26 + Math.sin(this.t * 1.8) * 0.09,
        0.10 + Math.sin(this.t * 2.0) * 0.035);
    }
    if (this.bowPivot) this.updateBow();
    if (this.kit === "chainblade") this.updateChainblade(dt);
    // Visible only for the 3-second festival; client puppet uses replicated timer too.
    const festivalOn = this.kit === "sickle" && this.bloodFestivalT > 0;
    for (const [i, aura] of this.festivalAura.entries()) {
      aura.visible = festivalOn;
      if (festivalOn) aura.scale.setScalar(1 + 0.025 * Math.sin(this.t * 15 + i * 2));
    }
    if (festivalOn) for (const d of this.festivalDrops) {
      const phase = this.t * 11 + d.seed;
      d.node.position.copy(d.base).add(v(0.025 * Math.sin(phase),
        0.026 * Math.cos(phase * 0.72), 0.015 * Math.cos(phase)));
      d.node.scale.setScalar(0.65 + 0.35 * (1 + Math.sin(phase * 1.3)));
    }
    if (this.gravityScythe) {
      // NYTHERA_SHOWCASE_SPIN_TOSS_V3: actual scythe transforms now match body beats.
      // Handheld rotations only: preview's thrown copy has no gameplay collider.
      const scytheAngles: Record<string, [number,number,number]> = {
        idle: [PI/2,-0.12,0.09], block: [1.83,-0.15,-0.16],
        gr1_w: [1.88,-0.64,-0.28], gr1_s: [0.85,0.76,0.31],
        gr2_w: [1.13,0.68,0.35], gr2_s: [2.13,-0.84,-0.29],
        gr3_w: [2.13,-0.60,-0.43], gr3_s: [0.67,0.40,0.28],
        gr4_w: [1.86,-0.74,0.30], gr4_s: [1.16,0.86,-0.35],
        gr5_w: [1.15,0.73,0.38], gr5_s: [2.18,-0.79,-0.35],
        gr6_w: [2.12,-0.80,0.27], gr6_s: [0.72,0.95,-0.42],
        grh_w: [2.20,-0.32,0.20], grh_s: [0.74,0.53,-0.12],
        grz_w: [1.93,-0.69,-0.25], grz_s: [0.91,0.84,0.30],
        grx_w: [2.20,-0.63,-0.37], grx_s: [0.59,0.31,0.22],
        grx_air_w: [2.23,0.08,-0.23], grx_air_s: [0.75,0.55,0.12],
        grc_w: [1.88,-0.31,0.11], grc_s: [1.26,0.51,0.22],
        grv_w: [2.31,0.13,0.09], grv_float: [1.89,0.24,-0.13],
        grv_finish: [0.51,0.69,0.18],
      };
      const a = scytheAngles[this.glaivePose] ?? scytheAngles.idle;
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));
      if (this.glaivePose === "nythera_show") {
        const t = this.presentationT;
        // Four full figure-eight/overhead spins before the throw, three after catch.
        // All segments end at whole revolutions so the weapon doesn't visually snap.
        const ease = (x:number,lo:number,hi:number) => THREE.MathUtils.smoothstep(x,lo,hi);
        const forwardSpin = 2*Math.PI*(
          ease(t,0.65,1.20) + ease(t,1.23,1.66) +
          ease(t,1.69,2.22) + ease(t,2.32,3.08));
        const returnSpin = 2*Math.PI*(
          ease(t,5.66,6.14) + ease(t,6.16,6.62) + ease(t,6.65,7.21));
        const spin = forwardSpin + returnSpin;
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),spin));
        // Rolling the long shaft completes the wrist-led figure-eight silhouette.
        const flourish = ((t>=0.65 && t<3.12) || (t>=5.65 && t<7.23)) ? 1 : 0;
        // Crossing figure-eight planes, alternating front/back shaft planes, not
        // just a flat propeller spin. The scythe remains visible edge-on in motion.
        const plane = Math.sin(t * 7.7) * 0.46 * flourish;
        const roll = Math.sin(t * 11.2) * 0.29 * flourish;
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),plane));
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),roll));
      } else {
        // The weapon itself, not only the body, performs circular finishers.
        // Each spin ends at a whole revolution so pose changes have no pop.
        const combatTurns: Record<string,number> = {
          gr4_s: 1, gr6_s: 1, grz_s: 1, grc_s: 1,
          grv_float: 2, grv_finish: 2,
        };
        const count = combatTurns[this.glaivePose] ?? 0;
        if (count > 0) {
          const w = this.scytheBeat * this.scytheBeat * (3-2*this.scytheBeat);
          q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),
            w * count * Math.PI * 2));
          q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),
            Math.sin(w*Math.PI*2)*0.32));
        }
      }
      this.gravityScythe.quaternion.slerp(q,1-Math.exp(-(this.glaivePose.endsWith("_s") ? 40 : 22)*dt));
      if (this.gravityHalo) {
        this.gravityHalo.rotation.y += dt * (this.gravityHeavy ? 0.52 : 1.9);
        this.gravityHalo.scale.setScalar(this.gravityHeavy ? 0.82 : 1.12 + Math.sin(this.t*3.3)*0.055);
      }
      if (!this.combat && this.walk < 0.12) {
        this.hips.position.y += this.gravityHeavy ? -0.022 : 0.020 + Math.sin(this.t*1.9)*0.009;
        this.torso.rotation.y += Math.sin(this.t*1.35)*0.012;
      }
      if (this.gravityHeavy && this.walk > 0.05) this.hips.position.y -= 0.018;
    }
    this.glowMat.color.copy(this.glowBase).lerp(new THREE.Color(1, 1, 1), this.charge * (0.5 + 0.3 * Math.sin(this.t * 30)));
    this.updateBlink(dt);
    this.updateFlash(dt);
    if (this.falling > 0) {
      this.falling = Math.max(this.falling - dt, 0);
      const f = 1 - this.falling / 0.6;
      this.rotation.x = -1.45 * Math.min(1, f * f * 1.2);
    }
  }


  /** NYTHERA_SHOWCASE_SPIN_TOSS_V3 — pure character-select choreography.
   * The held scythe stays on its original right-hand pivot / IK grip.  During the throw,
   * an uncollidable duplicate performs multiple full 3D revolutions and then interpolates
   * exactly into the current hand transform for a snap-free catch. */
  animateNytheraShowcase(phase: number, dt: number) {
    const held = this.gravityScythe;
    if (!held || this.kit !== "scythe") return;
    if (!this.gravityPreviewFlyer) {
      const flyer = held.clone(true);
      flyer.name = "Nythera selection-only flying scythe";
      flyer.visible = false;
      // Clone is visual only: no blade point, collision, hitbox or combat attachment.
      this.add(flyer);
      this.gravityPreviewFlyer = flyer;
      const eclipse = new THREE.Mesh(new THREE.TorusGeometry(0.78,0.014,8,72),
        new THREE.MeshBasicMaterial({color:"#bd83ff",transparent:true,opacity:0,depthWrite:false}));
      eclipse.position.set(0,1.22,-0.28);
      eclipse.rotation.x = 0.20;
      eclipse.visible = true;
      this.add(eclipse);
      this.gravityShowEclipse = eclipse;
      // Slim geometric crescents trail her spins, never opaque VFX smoke.
      // Local to the selection model and never registered with combat FX.
      const trails = new THREE.Group();
      for (const [i,r] of [0.66,0.90,1.15].entries()) {
        const mat = new THREE.MeshBasicMaterial({color:i===0?"#d4b5ff":"#8d62cf",
          transparent:true,opacity:0,depthWrite:false,side:THREE.DoubleSide});
        trails.add(new THREE.Mesh(new THREE.TorusGeometry(r,0.007,5,52,
          Math.PI*(i===1?1.42:1.10)),mat));
      }
      this.add(trails);
      this.gravityShowTrails = trails;
    }
    const flyer = this.gravityPreviewFlyer!;
    const flyStart = 3.13, flyEnd = 5.52;
    const flying = phase >= flyStart && phase < flyEnd;
    this.updateMatrixWorld(true);
    const rootWorld = this.getWorldQuaternion(new THREE.Quaternion());
    const inRoot = (o: THREE.Object3D) => this.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const gripP = inRoot(held);
    const gripQ = rootWorld.clone().invert().multiply(held.getWorldQuaternion(new THREE.Quaternion()));
    const gripS = held.getWorldScale(new THREE.Vector3()).divide(this.getWorldScale(new THREE.Vector3()));
    if (flying && !this.gravityShowFlying) {
      this.gravityShowLaunchP.copy(gripP);
      this.gravityShowLaunchQ.copy(gripQ);
      this.gravityShowLaunchScale.copy(gripS);
    }
    this.gravityShowFlying = flying;
    held.visible = !flying;
    flyer.visible = flying;
    if (flying) {
      const u = THREE.MathUtils.clamp((phase-flyStart)/(flyEnd-flyStart),0,1);
      const smooth = u*u*(3-2*u);
      const lift = Math.sin(Math.PI*u);
      // An airborne figure-eight, not a linear boomerang. Ends precisely at the hand.
      flyer.position.copy(this.gravityShowLaunchP).lerp(gripP,smooth);
      flyer.position.x -= Math.sin(u*Math.PI*2)*lift*0.66;
      flyer.position.y += lift*0.44 + Math.sin(u*Math.PI*4)*lift*0.08;
      flyer.position.z += lift*0.16;
      flyer.quaternion.copy(this.gravityShowLaunchQ).slerp(gripQ,smooth);
      flyer.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(
        new THREE.Vector3(0,0,1),u*Math.PI*8));  // 4 forward somersaults
      flyer.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(
        new THREE.Vector3(0,1,0),u*Math.PI*4));  // 2 shaft rolls
      flyer.scale.copy(this.gravityShowLaunchScale).lerp(gripS,smooth);
    }
    if (this.gravityShowEclipse) {
      const ring = this.gravityShowEclipse;
      const late = THREE.MathUtils.smoothstep(phase,6.90,7.32) *
        (1-THREE.MathUtils.smoothstep(phase,8.18,9.07));
      (ring.material as THREE.MeshBasicMaterial).opacity = 0.44*late + 0.10*(flying?1:0);
      ring.scale.setScalar(0.76 + 0.38*late);
      ring.rotation.z += dt*(flying ? 2.6 : 0.65);
      // Subtle pulse at the exact catch: visibly sells the impact into her palm.
      const catchPulse = Math.exp(-Math.pow((phase-5.58)/0.16,2));
      (ring.material as THREE.MeshBasicMaterial).opacity = Math.min(0.82,
        (ring.material as THREE.MeshBasicMaterial).opacity + 0.32*catchPulse);
    }
    if (this.gravityShowTrails) {
      const trails = this.gravityShowTrails;
      const spinWindow = (phase>=0.69 && phase<3.13) ||
        (phase>=5.57 && phase<7.32);
      trails.visible = spinWindow || flying;
      const center = flying ? flyer.position : gripP;
      trails.position.copy(center);
      trails.position.y += flying ? 0.20 : 0.38;
      trails.rotation.set(0.30 + Math.sin(phase*8)*0.17,
        Math.sin(phase*4.4)*0.35, phase*3.8);
      for (let i=0; i<trails.children.length; i++) {
        const arc = trails.children[i] as THREE.Mesh;
        (arc.material as THREE.MeshBasicMaterial).opacity =
          trails.visible ? (0.17 - i*0.034) * (flying ? 0.75 : 1) : 0;
        arc.rotation.z = i*1.77 + Math.sin(phase*6+i)*0.14;
      }
    }
  }

  /** Aims the left arm (shoulder to hand along local -Y) at the weapon's grip point. */
  private reachGrip() {
    this.updateMatrixWorld(true);
    const grip = this.torso.worldToLocal(this.gripL!.getWorldPosition(new THREE.Vector3()));
    const dir = grip.sub(this.arm_l.position);
    if (dir.lengthSq() < 1e-6) return;
    this.arm_l.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), dir.normalize());
    this.hand_l.rotation.set(0, 0, 0);
  }

  /** Swaps the procedural body for a VRM driven by the same joints (weapons stay). */
  private attachVrm(vrm: import("@pixiv/three-vrm").VRM) {
    if (this.vrmRig || this.disposed) return;
    const JN = ["torso", "head", "arm_r", "hand_r", "arm_l", "hand_l", "leg_l", "leg_r"] as const;
    const save = JN.map((n) => this.joints[n].quaternion.clone());
    const hipsPos = this.hips.position.clone();
    const rootQ = this.quaternion.clone();
    const rootP = this.position.clone();
    JN.forEach((n) => this.joints[n].quaternion.identity());
    this.hips.position.set(0, HIP, 0);
    this.quaternion.identity();
    this.updateMatrixWorld(true);
    const box = new THREE.Box3();
    const inv = this.matrixWorld.clone().invert();
    for (const m of this.bodyMeshes) box.union(new THREE.Box3().setFromObject(m).applyMatrix4(inv));
    this.vrmRig = new VrmRig(vrm, {
      root: this, hips: this.hips, torso: this.torso, head: this.head, arm_l: this.arm_l, hand_l: this.hand_l,
      arm_r: this.arm_r, hand_r: this.hand_r, leg_l: this.leg_l, leg_r: this.leg_r,
    }, (box.max.y - Math.max(box.min.y, 0)) * 1.08);
    for (const m of this.bodyMeshes) m.visible = false;
    // Weapons were sized for the chibi bodies; scale them down to suit the VRoid proportions.
    // Left hand grips for shields, paired weapons, bows and two-handed swords; mages and
    // kickers keep it free and relaxed.
    // Roxy's fingers remain open; she summons the book rather than grabbing it.
    this.vrmRig.grip = { left: !["mage", "kicks"].includes(this.kit),
      right: this.kit !== "kicks" && this.look.element !== "frost" };
    // Staffs and bows follow the arm a lot (natural tilt); blades less, to keep swing arcs.
    this.vrmRig.followArm = this.kit === "chainblade" ? 0.14 : this.kit === "glaive" ? 0.24 : this.kit === "scythe" ? 0.21 : this.kit === "sickle" ? 0.18 : this.kit === "mage" ? 0.4 : this.kit === "bow" ? 0.5 : 0.3;
    this.vrmRig.staff = this.kit === "mage" && this.look.element !== "frost";
    this.vrmRig.glaive = this.kit === "glaive" || this.kit === "scythe";
    this.vrmRig.style = this.kit === "glaive" && this.look.element === "metal" ? "magnetic" : this.kit === "knight" && this.look.element === "light" ? "aster" : this.kit === "chainblade" ? "chainblade" : this.kit === "glaive" ? "storm" : this.kit === "sickle" ? "feral" : this.kit === "hammer" ? "nesa" : this.kit === "greatsword" ? "greatsword" : this.look.body === "m" ? "heavy" : "light";
    if (this.kit === "knight") { this.buildHeaterShield(); this.vrmRig.shield = true; }
    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = this.kit === "chainblade" ? 0.58 : this.kit === "glaive" ? 0.4 : this.kit === "scythe" ? 0.50 : 1; }
    if (this.look.element === "metal") {
      this.vrmRig.spearGripR = this.zenithSpearRightGrip;
    }
    if (["knight", "greatsword", "hammer", "katana"].includes(this.kit) && this.bladeBase.parent) {
      // A point off the blade's cutting edge (blades are wide along their local X).
      const bb = this.bladeBase.position;
      const edge = pivot(this.bladeBase.parent, [bb.x + 0.1, bb.y, bb.z]);
      this.vrmRig.blade = { base: this.bladeBase, tip: this.bladeTip, edge };
    }
    if (this.kit === "greatsword" || this.kit === "hammer") { this.vrmRig.restSword = true; this.vrmRig.grip.left = true; }
    if (this.kit === "knuckles") { this.vrmRig.boxer = true; this.vrmRig.bladed = 0.65; }
    // Kicker: relaxed, hands-free upper body; the legs do everything.
    // A longbow is about 85-90% of body height.
    if (this.kit === "bow") { this.vrmRig.archer = true; this.vrmRig.followArm = 0; this.bowPivot?.scale.setScalar(1.45); }
    // ZAREK_WEAPON_RANGE_MATCH_V1_NOV06: keep Zarek's long double-ended blade visible on VRM bodies.
    const weaponScale = this.kit === "glaive" && this.look.element === "metal" ? 0.93 : this.kit === "glaive" ? 0.87 : this.kit === "scythe" ? 0.82 : VRM_WEAPON_SCALE; // ZAREK_PROPORTIONATE_GLAIVE_V1: total VRoid weapon length about -29%
    for (const h of [this.hand_l, this.hand_r]) h.scale.multiplyScalar(weaponScale);
    JN.forEach((n, i) => this.joints[n].quaternion.copy(save[i]));
    this.hips.position.copy(hipsPos);
    this.quaternion.copy(rootQ);
    this.position.copy(rootP);
    this.updateMatrixWorld(true);
  }

  /**
   * Large heater shield for VRoid knights (covers chest to thigh) in place of the small
   * round one. Built at its final world size, compensating the weapon scale on the hand.
   */
  private buildHeaterShield() {
    const L = this.look;
    for (const c of [...this.shieldNode.children]) c.visible = false;
    const k = 1 / VRM_WEAPON_SCALE;
    const W = 0.42 * k, H = 0.66 * k;
    const heater = (w: number, h: number) => {
      const s = new THREE.Shape();
      s.moveTo(-w / 2, h * 0.42);
      s.lineTo(w / 2, h * 0.42);
      s.lineTo(w / 2, h * 0.02);
      s.quadraticCurveTo(w / 2, -h * 0.36, 0, -h * 0.58);
      s.quadraticCurveTo(-w / 2, -h * 0.36, -w / 2, h * 0.02);
      s.closePath();
      return s;
    };
    const plate = (w: number, h: number, depth: number) => {
      const g = new THREE.ExtrudeGeometry(heater(w, h), { depth, bevelEnabled: true, bevelSize: 0.01 * k, bevelThickness: 0.008 * k, bevelSegments: 2, curveSegments: 16 });
      g.translate(0, 0, -depth / 2);
      g.rotateX(-PI / 2); // face along the hand's +/-Y like the round shield; top toward -Z
      return g;
    };
    const s = pivot(this.shieldNode, [0, -0.03 * k, 0.05 * k]);
    s.rotation.y = PI; // top of the shield up when the arm is raised in guard
    mesh(s, plate(W + 0.05 * k, H + 0.05 * k, 0.02 * k), this.tn(L.trim), [0, 0.005 * k, 0]);
    mesh(s, plate(W, H, 0.035 * k), this.tn(L.shield), [0, -0.004 * k, 0]);
    mesh(s, cyl(0.12 * k, 0.12 * k, 0.045 * k, 4), this.tn(L.emblem), [0, -0.012 * k, 0.03 * k], [0, PI / 4, 0], [1, 1, 1.4]);
    mesh(s, sphere(0.05 * k, 14), this.metal(), [0, -0.03 * k, 0.03 * k], [0, 0, 0], [1, 0.5, 1]);
  }

  setBarrier(on: boolean) { if (this.barrier) this.barrier.visible = on; }

  private updateBlink(dt: number) {
    if (this.blinkT < 0) {
      this.blinkWait -= dt;
      if (this.blinkWait <= 0) this.blinkT = 0;
      return;
    }
    this.blinkT += dt / 0.14;
    this.faceMat.uniforms.blink.value = Math.sin(Math.min(this.blinkT, 1) * PI);
    this.vrmRig?.setBlink(this.faceMat.uniforms.blink.value);
    if (this.blinkT >= 1) {
      this.blinkT = -1;
      this.blinkWait = 1.8 + Math.random() * 2.7;
      this.faceMat.uniforms.blink.value = 0;
      this.vrmRig?.setBlink(0);
    }
  }

  /** Brief solid-color flash over the whole body (hit feedback). */
  flash(color = "#ffffff", duration = 0.1) {
    let fm = flashMats.get(color);
    if (!fm) { fm = new THREE.MeshBasicMaterial({ color: new THREE.Color(color) }); flashMats.set(color, fm); }
    this.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh || !m.userData.fill) return;
      if (!m.userData.orig) m.userData.orig = m.material;
      m.material = fm!;
    });
    this.flashT = duration;
  }

  private updateFlash(dt: number) {
    if (this.flashT <= 0) return;
    this.flashT -= dt;
    if (this.flashT > 0) return;
    this.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh && m.userData.orig) { m.material = m.userData.orig; m.userData.orig = null; }
    });
  }

  /** Topple backward (knocked out). */
  fall() { this.falling = 0.6; }
  standUp() { this.falling = 0; this.rotation.x = 0; }
}
