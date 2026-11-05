// VRM bodies (VRoid Studio exports). The procedural rig in model.ts keeps animating every
// frame; VrmRig copies its joint rotations onto the VRM's normalized humanoid bones, so every
// existing pose, attack and skill drives the VRM. three-vrm then updates spring bones (hair,
// skirt physics) and expressions (blinking).
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils, type VRM, type VRMHumanBoneName } from "@pixiv/three-vrm";

const files = new Map<string, Promise<ArrayBuffer>>();

/** Starts downloading a VRM file so it's in memory before anyone picks the fighter. */
export function prefetchVrm(id: string) {
  if (!files.has(id)) files.set(id, fetch(`/models/${id}.vrm`).then((r) => { if (!r.ok) throw new Error(`${id}.vrm: ${r.status}`); return r.arrayBuffer(); }));
  files.get(id)!.catch(() => files.delete(id));
}

/** Loads /models/<id>.vrm (file cached; each fighter gets its own parsed copy). */
export async function loadVrm(id: string): Promise<VRM> {
  let f = files.get(id);
  if (!f) { f = fetch(`/models/${id}.vrm`).then((r) => { if (!r.ok) throw new Error(`${id}.vrm: ${r.status}`); return r.arrayBuffer(); }); files.set(id, f); }
  const buf = await f;
  const loader = new GLTFLoader();
  loader.register((p) => new VRMLoaderPlugin(p));
  const gltf = await loader.parseAsync(buf.slice(0), "");
  const vrm = gltf.userData.vrm as VRM;
  VRMUtils.removeUnnecessaryVertices(gltf.scene);
  VRMUtils.combineSkeletons(gltf.scene);
  VRMUtils.rotateVRM0(vrm); // VRM 0.x faces -Z; the game faces +Z
  vrm.scene.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    m.frustumCulled = false;
    m.castShadow = true;
    m.userData.fill = true; // white hit flash like the procedural meshes
    // Color management is off game-wide: use texels as authored (no sRGB decode).
    for (const mat of Array.isArray(m.material) ? m.material : [m.material]) {
      for (const v of Object.values(mat as any)) if ((v as THREE.Texture)?.isTexture) (v as THREE.Texture).colorSpace = THREE.NoColorSpace;
      const u = (mat as any).uniforms;
      if (u) for (const k in u) if (u[k]?.value?.isTexture) u[k].value.colorSpace = THREE.NoColorSpace;
      mat.needsUpdate = true;
    }
  });
  return vrm;
}

export interface RigJoints {
  root: THREE.Object3D; hips: THREE.Object3D; torso: THREE.Object3D; head: THREE.Object3D;
  arm_l: THREE.Object3D; hand_l: THREE.Object3D; arm_r: THREE.Object3D; hand_r: THREE.Object3D;
  leg_l: THREE.Object3D; leg_r: THREE.Object3D;
}

interface Link { joint: THREE.Object3D; bone: THREE.Object3D; rest: THREE.Quaternion; cal: THREE.Quaternion }

const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _inv = new THREE.Quaternion();
const _v = new THREE.Vector3(), _v2 = new THREE.Vector3();
const _e = new THREE.Euler();
const TAU = Math.PI * 2;
const D = (deg: number) => (deg * Math.PI) / 180;
const rx = (a: number) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), a);
const rz = (a: number) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), a);

/** What the procedural model is doing, for the natural-motion layer. */
export interface MotionInfo { t: number; walk: number; phase: number; crouch: number; combat?: boolean; hurt?: boolean; draw?: number; knee?: [number, number] }

/** Per-bone follow-through speed (1/s): lower = more lag and overlap. */
const RATE: Partial<Record<VRMHumanBoneName, number>> = {
  spine: 16, chest: 12, upperChest: 10, neck: 12, head: 10,
  leftShoulder: 10, rightShoulder: 10, leftUpperArm: 22, rightUpperArm: 22, leftLowerArm: 18, rightLowerArm: 18,
  leftHand: 20, rightHand: 20, leftUpperLeg: 26, rightUpperLeg: 26, leftLowerLeg: 22, rightLowerLeg: 22, leftFoot: 22, rightFoot: 22,
};
/**
 * Motion style. "light" (graceful): contrapposto, hip sway, expressive head. "heavy"
 * (armored warrior): wide braced stance, bent knees, lowered hips, forward torso, squared
 * shoulders, chin down, quiet pelvis, restrained secondary motion.
 */
export const STYLES = {
  light: { stance: 0, toeOut: D(4), knee: D(5), drop: 0, lean: 0, chin: 0, shoulderUp: 0, elbowOut: 0,
    hipSway: 0.03, hipRoll: D(4), contra: D(3), relaxKnee: D(14), headTilt: D(3), headYaw: D(7),
    breath: 1, armSwing: D(16), walkRoll: D(3), walkYaw: D(5) },
  heavy: { stance: D(14), toeOut: D(12), knee: D(18), drop: 0.07, lean: D(6), chin: D(5), shoulderUp: D(4), elbowOut: D(12),
    hipSway: 0.008, hipRoll: D(0.8), contra: D(0.6), relaxKnee: D(3), headTilt: D(0.5), headYaw: D(4),
    breath: 0.5, armSwing: D(9), walkRoll: D(1.2), walkYaw: D(2.5) },
};
export type MotionStyle = keyof typeof STYLES;
const FINGERS = ["Index", "Middle", "Ring", "Little"] as const;
const SEGS = ["Proximal", "Intermediate", "Distal"] as const;

/** Rotation of `o` in `root`'s frame. */
function quatIn(root: THREE.Object3D, o: THREE.Object3D, out: THREE.Quaternion) {
  root.getWorldQuaternion(_inv).invert();
  return out.copy(_inv).multiply(o.getWorldQuaternion(_q2));
}

export class VrmRig {
  readonly vrm: VRM;
  private links: Link[] = [];
  private byJoint: Record<"torso" | "head" | "arm_l" | "hand_l" | "arm_r" | "hand_r" | "leg_l" | "leg_r", Link> = {} as any;
  private first = true;
  /** Smoothed local rotation per bone (follow-through). */
  private smooth = new Map<THREE.Object3D, THREE.Quaternion>();
  private nameOf = new Map<THREE.Object3D, string>();
  /** Which hands hold a weapon (curl into a grip) vs hang free (relaxed curl). */
  grip = { left: false, right: true };
  /** 0 = hands keep the pose angle exactly, 1 = hands follow the forearm. */
  followArm = 0.35;
  style: MotionStyle = "light";
  /** Right hand holds a staff: heavy, upright, spring-driven instead of copying the wrist. */
  staff = false;
  /** Left hand carries a big shield that always faces front. */
  shield = false;
  /** Two-handed weapon grip point for the left hand (greatsword, katana). */
  gripL: THREE.Object3D | null = null;
  /** Rest the blade on the shoulder when not fighting (greatsword). */
  restSword = false;
  /** Fist fighter: high guard with bent elbows, staggered bladed stance, bounce and head weave. */
  boxer = false;
  /** Archer: bow held upright across the aim line, string hand drawn to the jaw by IK. */
  archer = false;
  private drawW = 0;
  /** Sword reference points (base, tip, and a point off the cutting edge) for edge alignment. */
  blade: { base: THREE.Object3D; tip: THREE.Object3D; edge: THREE.Object3D } | null = null;
  private lastTip = new THREE.Vector3();
  private hasTip = false;
  private twist = 0;
  private hurtW = 0;
  /** Extra torso yaw that keeps a two-handed sword's hands in front of the chest. */
  private followYaw = 0;
  /** 0..1 bladed (sword-side-forward) torso turn for two-handed weapons. */
  bladed = 0;
  private restW = 1;
  private swordQ = new THREE.Quaternion(0, 0, 0, 0);
  private shieldRaise = 0;
  private shieldPos = new THREE.Vector3();
  private staffDir = new THREE.Vector3();
  private staffVel = new THREE.Vector3();
  private hipsBone: THREE.Object3D | null;
  private hipsRest = new THREE.Vector3();
  private hipsBoneRest = new THREE.Vector3();
  private scale = 1;
  private j: RigJoints;

  /**
   * Call with the procedural joints at rest (zero rotations) and the root unrotated.
   * `height` is the procedural body height in the root's frame; the VRM is scaled to match.
   */
  constructor(vrm: VRM, j: RigJoints, height: number) {
    this.vrm = vrm;
    this.j = j;
    const root = j.root;
    root.add(vrm.scene);
    vrm.scene.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(vrm.scene);
    box.applyMatrix4(root.matrixWorld.clone().invert());
    // Keep the VRoid model's real height (VRM is in meters, 1 game unit = 1 m), undoing the
    // procedural body-type scale on the root. `height` only guards against broken files.
    const rootScale = root.getWorldScale(new THREE.Vector3()).y || 1;
    const h = box.max.y - box.min.y;
    this.scale = h > 0.8 && h < 2.6 ? 1 / rootScale : height / Math.max(h, 1e-3);
    vrm.scene.scale.setScalar(this.scale);
    vrm.scene.position.y = -box.min.y * this.scale;
    vrm.scene.updateMatrixWorld(true);

    const bone = (n: VRMHumanBoneName) => vrm.humanoid.getNormalizedBoneNode(n);
    // Normalized VRM bones rest in a T-pose; the procedural arms rest hanging down.
    const down = new THREE.Vector3(0, -1, 0);
    const calL = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), down);
    const calR = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(-1, 0, 0), down);
    const add = (k: keyof VrmRig["byJoint"], joint: THREE.Object3D, b: THREE.Object3D | null, cal = new THREE.Quaternion()) => {
      const l = { joint, bone: b ?? joint, rest: quatIn(root, joint, new THREE.Quaternion()), cal };
      this.links.push(l);
      this.byJoint[k] = l;
    };
    add("torso", j.torso, bone("spine"));
    add("head", j.head, bone("head"));
    add("arm_l", j.arm_l, bone("leftUpperArm"), calL);
    add("hand_l", j.hand_l, bone("leftHand"), calL);
    add("arm_r", j.arm_r, bone("rightUpperArm"), calR);
    add("hand_r", j.hand_r, bone("rightHand"), calR);
    add("leg_l", j.leg_l, bone("leftUpperLeg"));
    add("leg_r", j.leg_r, bone("rightUpperLeg"));
    this.hipsBone = bone("hips");
    for (const [name] of Object.entries(vrm.humanoid.humanBones)) {
      const node = bone(name as VRMHumanBoneName);
      if (node) this.nameOf.set(node, name);
    }
    this.hipsRest.copy(j.hips.position);
    if (this.hipsBone) this.hipsBoneRest.copy(this.hipsBone.position);
  }

  /**
   * Copies the procedural pose onto the VRM and layers natural motion on top (soft elbows and
   * knees, torso twist spread over the spine, head lag, breathing, weight shift, walk sway),
   * then runs VRM physics and pins weapons to its hands.
   */
  update(dt: number, m: MotionInfo) {
    const j = this.j, root = j.root, vrm = this.vrm;
    dt = Math.max(0, Math.min(dt, 0.1)); // smoothing below assumes a sane step
    const B = (n: VRMHumanBoneName) => vrm.humanoid.getNormalizedBoneNode(n);
    root.updateMatrixWorld(true);
    const t = m.t, walk = m.walk, idle = 1 - walk, ph = m.phase;
    const breath = Math.sin(t * TAU / 3.6);
    // Weight rests on one leg and slowly moves to the other (contrapposto), never centered.
    const shift = Math.tanh(Math.sin(t * TAU / 9 + 0.7) * 2.2);
    const look = Math.sin(t * TAU / 6.1 + 1.9) * 0.7 + Math.sin(t * TAU / 2.3) * 0.3;
    const crouch = Math.max(0, -m.crouch);
    const S = STYLES[this.style];

    // Hips: bob / crouch from the rig, idle weight shift, walk yaw + roll.
    if (this.hipsBone) {
      this.hipsBone.position.copy(this.hipsBoneRest).addScaledVector(_v.copy(j.hips.position).sub(this.hipsRest), 1 / this.scale);
      this.hipsBone.position.x += (shift * S.hipSway * idle) / this.scale;
      this.hipsBone.position.y += (Math.abs(Math.sin(ph)) * 0.012 * walk - S.drop) / this.scale;
      if (this.boxer) this.hipsBone.position.y += ((Math.sin(t * TAU * 2.2) * 0.5 - 0.5) * 0.04 * idle) / this.scale; // bounce on the balls of the feet
      this.hipsBone.quaternion.setFromEuler(_e.set(0, Math.sin(ph) * S.walkYaw * walk - this.bladed * D(12) + this.followYaw * 0.3, (Math.sin(ph) * S.walkRoll * walk + shift * S.hipRoll * idle), "YXZ"));
      this.hipsBone.updateMatrixWorld(true);
    }
    const deltaOf = (joint: THREE.Object3D, rest: THREE.Quaternion) => quatIn(root, joint, new THREE.Quaternion()).multiply(_q2.copy(rest).invert());
    const ease = (b: THREE.Object3D, local: THREE.Quaternion, rate = 30) => {
      let q = this.smooth.get(b);
      if (!q || this.first) { q = local.clone(); this.smooth.set(b, q); }
      else q.slerp(local, 1 - Math.exp(-rate * dt));
      b.quaternion.copy(q);
      b.updateMatrixWorld(true);
    };
    const rateOf = (b: THREE.Object3D) => RATE[this.nameOf.get(b) as VRMHumanBoneName] ?? 30;
    const set = (b: THREE.Object3D | null, target: THREE.Quaternion) => {
      if (!b) return;
      const parentQ = quatIn(root, b.parent!, new THREE.Quaternion()).invert();
      ease(b, parentQ.multiply(target), rateOf(b));
    };
    const setLocal = (b: THREE.Object3D | null, x: number, y: number, z: number) => {
      if (!b) return;
      ease(b, new THREE.Quaternion().setFromEuler(_e.set(x, y, z, "XYZ")), rateOf(b));
    };
    const L = this.byJoint;

    // Torso: spread the rig's single torso rotation over spine / chest / upperChest, with
    // breathing on the chest and a walk counter-twist.
    const T = deltaOf(j.torso, L.torso.rest);
    const counter = new THREE.Quaternion().setFromEuler(_e.set(0, -Math.sin(ph) * D(4) * walk, 0));
    const I = new THREE.Quaternion();
    // Shoulders tilt against the hips in the idle stance; lean a bit into the walk.
    const contra = new THREE.Quaternion().setFromEuler(_e.set(D(4) * walk, 0, -shift * S.contra * idle));
    // Two-handed weapons: a bladed stance, upper body turned toward the sword side so the left
    // shoulder comes forward to the grip instead of the arm reaching across the chest.
    // ...and for big swings the body turns with the sword: when the hands go more than ~35 deg
    // to the side of the chest (windups, follow-throughs), hips and torso rotate toward them.
    const blade = (k: number) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -this.bladed * D(28) * k + this.followYaw * k);
    set(B("spine"), blade(0.45).multiply(I.clone().slerp(T, 0.5)).multiply(contra).multiply(rx(S.lean)));
    set(B("chest"), blade(0.8).multiply(I.clone().slerp(T, 0.8)).multiply(counter).multiply(contra).multiply(rx(S.lean * 1.4 - breath * D(1.8) * S.breath)));
    set(B("upperChest"), blade(1).multiply(T.clone()).multiply(counter).multiply(contra).multiply(rx(S.lean * 1.1 - breath * D(2.2) * S.breath)));

    // Head: neck takes 40%, head finishes, with a slow look-around and a little lag.
    const H = deltaOf(j.head, L.head.rest).multiply(new THREE.Quaternion().setFromEuler(
      _e.set(D(3) * idle * Math.sin(t * TAU / 4.7) * S.breath + S.chin - S.lean * 1.2 + (this.boxer ? D(6) : 0),
        S.headYaw * idle * look + (this.boxer ? (Math.sin(t * 1.3) * D(5) + Math.sin(t * 2.9 + 1) * D(3)) * idle : 0),
        shift * S.headTilt * idle + (this.boxer ? Math.sin(t * 1.7) * D(3) * idle : 0))));
    const chestNow = quatIn(root, B("upperChest") ?? B("chest") ?? B("spine")!, new THREE.Quaternion());
    set(B("neck"), chestNow.clone().slerp(H, 0.4));
    set(B("head"), H);

    // Shoulders: relaxed and rising slightly with each breath.
    // Light: relaxed, dropped shoulders. Heavy: squared, slightly raised and braced.
    setLocal(B("leftShoulder"), 0, D(3) * (S.shoulderUp > 0 ? 1 : 0), -D(5) + S.shoulderUp * 2 - breath * D(1.8) * S.breath);
    setLocal(B("rightShoulder"), 0, -D(3) * (S.shoulderUp > 0 ? 1 : 0), D(5) - S.shoulderUp * 2 + breath * D(1.8) * S.breath);

    // Arms: rig rotation (T-pose calibrated), walk swing opposite the legs, soft elbows that
    // bend more as the arm rises.
    for (const side of ["left", "right"] as const) {
      const lk = side === "left" ? L.arm_l : L.arm_r, hk = side === "left" ? L.hand_l : L.hand_r;
      const sgn = side === "left" ? 1 : -1;
      const swing = rx(-Math.sin(ph) * sgn * (side === "left" ? S.armSwing : S.armSwing * 0.5) * walk)
        .multiply(rz(sgn * S.elbowOut)); // heavy: elbows held out from the body
      const target = swing.multiply(deltaOf(lk.joint, lk.rest)).multiply(lk.cal);
      set(B(`${side}UpperArm`), target);
      const dir = new THREE.Vector3(sgn, 0, 0).applyQuaternion(target);
      const elev = dir.angleTo(new THREE.Vector3(0, -1, 0));
      // A shield arm stays bent (~90 deg), holding the shield close instead of reaching out.
      if (this.shield && side === "left") this.shieldRaise = THREE.MathUtils.clamp((elev - D(45)) / D(50), 0, 1);
      // Boxer: the pose's wrist angle drives the elbow (guard ~115 deg, fists at the cheeks;
      // nearly straight at the moment a punch lands).
      const wristX = Math.abs(new THREE.Euler().setFromQuaternion(hk.joint.quaternion, "YXZ").x);
      const flex = this.boxer
        ? THREE.MathUtils.clamp(D(12) + wristX * 1.75, D(12), D(125))
        : this.shield && side === "left"
          ? D(55)
          : Math.min(D(16) + elev * 0.3 + Math.sin(t * TAU / 3.8 + 1) * D(2) * idle, D(75));
      // Forearm bends toward the front of the arm (around the arm's local Y).
      setLocal(B(`${side}LowerArm`), 0, -sgn * flex, 0);
      // Hand: blend the pose's absolute hand angle with "follow the forearm", so held weapons
      // tilt and sway with the arm instead of staying rigidly at the pose angle.
      const handAbs = deltaOf(hk.joint, hk.rest).multiply(hk.cal);
      // Direction the pose wants the held weapon to point (weapon meshes run along local +Y).
      const poseDir = new THREE.Vector3(0, 1, 0).applyQuaternion(quatIn(root, hk.joint, new THREE.Quaternion()));
      const fore = B(`${side}LowerArm`);
      const handB = B(`${side}Hand`);
      if (fore && handB) {
        const follow = quatIn(root, fore, new THREE.Quaternion()).multiply(rz(-sgn * D(10)));
        set(handB, handAbs.clone().slerp(follow, this.followArm));
        const parentRoot = quatIn(root, hk.joint.parent!, new THREE.Quaternion()).invert();
        if (this.staff && side === "right") {
          // A staff is a long, heavy pole: mostly upright, tilting toward the cast at most
          // 60 degrees, no wrist spin, and it swings on a spring (lag, slight overshoot).
          const up = new THREE.Vector3(0, 1, 0);
          const want = poseDir.clone();
          const ang = want.angleTo(up);
          if (ang > D(60)) want.lerp(up, 1 - D(60) / ang).normalize();
          want.add(new THREE.Vector3(-0.13 + Math.sin(t * 0.9) * 0.03 * idle, 0, 0.04 + Math.sin(ph) * 0.06 * walk)).normalize();
          if (this.first || this.staffDir.lengthSq() === 0) { this.staffDir.copy(want); this.staffVel.set(0, 0, 0); }
          const w = 15, zeta = 0.55;
          this.staffVel.addScaledVector(_v.copy(want).sub(this.staffDir), w * w * dt).multiplyScalar(Math.max(0, 1 - 2 * zeta * w * dt));
          this.staffDir.addScaledVector(this.staffVel, dt).normalize();
          const mount = new THREE.Quaternion().setFromUnitVectors(up, this.staffDir);
          hk.joint.quaternion.copy(parentRoot.multiply(mount));
        } else if (this.shield && side === "left") {
          // A big shield faces the front (slightly turned to cover the centerline), top up,
          // whatever the wrist does; it tips forward a little as the arm rises (blocks, bash).
          const raise = THREE.MathUtils.clamp((poseDir.z + 1) * 0.5, 0, 1);
          const basis = new THREE.Matrix4().makeBasis(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, -1), new THREE.Vector3(0, 1, 0));
          const mount = new THREE.Quaternion().setFromEuler(_e.set(D(8) * raise, -D(12), 0, "YXZ"))
            .multiply(new THREE.Quaternion().setFromRotationMatrix(basis));
          hk.joint.quaternion.copy(parentRoot.multiply(mount));
        } else {
          // Weapon mount (procedural hand) takes the VRM hand's final orientation.
          const vrmHandRoot = quatIn(root, handB, new THREE.Quaternion());
          const procRoot = vrmHandRoot.multiply(_q2.copy(hk.cal).invert()).multiply(hk.rest);
          hk.joint.quaternion.copy(parentRoot.multiply(procRoot));
        }
        hk.joint.updateMatrixWorld(true);
      }
      // Fingers: a closed grip around a weapon, a soft natural curl on a free hand.
      const g = this.grip[side];
      FINGERS.forEach((f, fi) => SEGS.forEach((seg, si) => {
        const base = g ? [D(72), D(85), D(55)][si] : [D(18), D(30), D(22)][si];
        const fan = g ? 0 : fi * D(4) + Math.sin(t * 1.3 + fi) * D(2);
        setLocal(B(`${side}${f}${seg}` as VRMHumanBoneName), 0, 0, -sgn * (base + fan));
      }));
      setLocal(B(`${side}ThumbProximal` as VRMHumanBoneName), 0, sgn * (g ? D(35) : D(15)), -sgn * (g ? D(25) : D(8)));
      setLocal(B(`${side}ThumbDistal` as VRMHumanBoneName), 0, sgn * (g ? D(30) : D(10)), 0);
    }

    // Legs: rig rotation, soft knees that flex through the walk cycle and when crouching,
    // feet kept level with the ground.
    for (const side of ["left", "right"] as const) {
      const lk = side === "left" ? L.leg_l : L.leg_r;
      const sg = side === "left" ? 1 : -1;
      const cyc = 0.5 + 0.5 * Math.sin(ph + (side === "left" ? 1.2 : 1.2 + Math.PI));
      // Idle: the leg not carrying the weight relaxes with a bent knee.
      const relaxed = Math.max(0, side === "left" ? -shift : shift);
      const load = (this.restSword && m.combat ? D(10) : 0) // knees take the sword's weight
        + (this.boxer ? (D(6) + (0.5 - Math.sin(t * TAU * 2.2) * 0.5) * D(8)) * idle : 0);
      const knee = S.knee + load + walk * (D(10) + D(30) * cyc) + Math.min(crouch * D(260), D(55)) + relaxed * S.relaxKnee * idle;
      // Wide stance (legs out, toes out) and hip flexion matching the knee bend, so a bent
      // knee lowers the body instead of kicking the foot back.
      // Boxer stagger: lead (left) foot forward, rear foot back, knees pumping with the bounce.
      const stagger = this.boxer ? (side === "left" ? -D(14) : D(10)) * (1 - walk) : 0;
      const stance = new THREE.Quaternion().setFromEuler(_e.set(-knee * 0.5 + stagger, sg * S.toeOut, sg * S.stance * (1 - 0.4 * walk), "YXZ"));
      set(B(`${side}UpperLeg`), stance.multiply(deltaOf(lk.joint, lk.rest)));
      // A leg raised for a kick drops the crouch/idle bend so the extension can go straight;
      // the pose's own knee value (chamber, recoil) is added on top.
      const lift = THREE.MathUtils.clamp(-lk.joint.rotation.x / 1.2, 0, 1);
      setLocal(B(`${side}LowerLeg`), knee * (1 - lift) + (m.knee?.[side === "left" ? 0 : 1] ?? 0), 0, 0);
      const foot = B(`${side}Foot`);
      if (foot) {
        const parentQ = quatIn(root, foot.parent!, new THREE.Quaternion());
        set(foot, parentQ.clone().slerp(I, 0.75));
      }
    }
    if (this.shield) this.shieldArm(dt, set);
    if (this.archer) this.archerArms(dt, m.draw ?? 0, set);
    const setNow = (b: THREE.Object3D | null, target: THREE.Quaternion) => {
      if (!b) return;
      const parentQ = quatIn(root, b.parent!, new THREE.Quaternion()).invert();
      ease(b, parentQ.multiply(target), 120);
    };
    this.hurtW += ((m.hurt ? 1 : 0) - this.hurtW) * (1 - Math.exp(-(m.hurt ? 18 : 6) * dt));
    if (this.gripL || this.restSword) this.heavyBlade(dt, !!m.combat, set, setNow);
    else if (this.hurtW > 0.02) this.handsForward(set);
    if (this.blade) this.edgeAlign(dt);
    if (this.bladed > 0) {
      // Where does the POSE put the sword hand around the body? Measured on the procedural rig
      // (shoulder + arm direction), which the VRM torso turn doesn't move, so no feedback loop.
      {
        const sh = root.worldToLocal(j.arm_r.getWorldPosition(new THREE.Vector3()));
        const armDir = new THREE.Vector3(0, -1, 0).applyQuaternion(quatIn(root, j.arm_r, new THREE.Quaternion()));
        const p = sh.addScaledVector(armDir, 0.55).sub(root.worldToLocal(j.torso.getWorldPosition(new THREE.Vector3())));
        const ang = Math.atan2(p.x, p.z); // angle in the root frame
        const rel = ang - this.followYaw - (-this.bladed * D(28));
        const over = rel - THREE.MathUtils.clamp(rel, -D(30), D(30));
        const want = THREE.MathUtils.clamp(this.followYaw + over, -D(100), D(100));
        this.followYaw += (want - this.followYaw) * (1 - Math.exp(-16 * dt));
        if (!m.combat) this.followYaw *= Math.exp(-4 * dt);
      }
    }
    this.first = false;

    vrm.update(dt);
    this.pinHand(j.hand_r, j.arm_r, "rightHand", "rightLowerArm");
    if (this.shield) {
      // Shield mount (procedural hand) at the guard spot.
      j.hand_l.position.copy(j.arm_l.worldToLocal(root.localToWorld(this.shieldPos.clone())));
      j.hand_l.updateMatrixWorld(true);
    } else this.pinHand(j.hand_l, j.arm_l, "leftHand", "leftLowerArm");
  }

  /**
   * Two-bone IK: bends shoulder and elbow so the hand reaches T (root frame), elbow toward
   * `pole`. The hand takes the forearm's direction.
   */
  private solveArm(side: "left" | "right", T: THREE.Vector3, pole: THREE.Vector3, set: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const root = this.j.root, h = this.vrm.humanoid;
    const up = h.getNormalizedBoneNode(`${side}UpperArm`), lo = h.getNormalizedBoneNode(`${side}LowerArm`), hand = h.getNormalizedBoneNode(`${side}Hand`);
    if (!up || !lo || !hand) return;
    const P = (o: THREE.Object3D) => root.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const S = P(up), E0 = P(lo), H0 = P(hand);
    const L1 = S.distanceTo(E0), L2 = E0.distanceTo(H0);
    const toT = T.clone().sub(S);
    const d = Math.min(Math.max(toT.length(), Math.abs(L1 - L2) + 1e-3), (L1 + L2) * 0.999);
    const dir = toT.normalize();
    const pl = pole.clone().normalize();
    const n = new THREE.Vector3().crossVectors(dir, pl).normalize();
    const a = Math.acos(THREE.MathUtils.clamp((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1, 1));
    const e = dir.clone().applyAxisAngle(n, -a);
    if (e.dot(pl) < 0) e.copy(dir).applyAxisAngle(n, a);
    const elbow = S.clone().addScaledVector(e, L1);
    const f = T.clone().sub(elbow).normalize();
    const X = new THREE.Vector3(side === "left" ? 1 : -1, 0, 0); // arm bones point outward in the T-pose
    const qUp = new THREE.Quaternion().setFromUnitVectors(X, e);
    const qLo = new THREE.Quaternion().setFromUnitVectors(e, f).multiply(qUp);
    set(up, qUp);
    set(lo, qLo);
    set(hand, qLo.clone());
  }

  /**
   * Archer. The bow stands across the aim line (limbs up, canted ~10 degrees, string toward
   * the archer), so it tips back for a sky volley. While drawing, IK pulls the string hand
   * from the nock to an anchor beside the jaw with the elbow driving back and out.
   */
  private archerArms(dt: number, draw: number, set: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const j = this.j, root = j.root, h = this.vrm.humanoid;
    const N = (n: VRMHumanBoneName) => h.getNormalizedBoneNode(n);
    const P = (o: THREE.Object3D) => root.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const shL = N("leftUpperArm"), handL = N("leftHand"), head = N("head");
    if (!shL || !handL || !head) return;
    root.updateMatrixWorld(true);
    const hl = P(handL);
    const aim = hl.clone().sub(P(shL)).normalize();
    // Bow mount: local Z (limbs) up and canted, local +Y toward the archer.
    const up = new THREE.Vector3(-0.17, 1, 0).normalize();
    const zAx = up.clone().addScaledVector(aim, -up.dot(aim)).normalize();
    const yAx = aim.clone().negate();
    const xAx = new THREE.Vector3().crossVectors(yAx, zAx).normalize();
    const mount = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(xAx, yAx, zAx));
    const parentRoot = quatIn(root, j.hand_l.parent!, new THREE.Quaternion()).invert();
    j.hand_l.quaternion.copy(parentRoot.multiply(mount));
    j.hand_l.updateMatrixWorld(true);
    // Draw: nock (on the string, in front of the bow hand) to the anchor beside the jaw.
    this.drawW += ((draw > 0.01 ? 1 : 0) - this.drawW) * (1 - Math.exp(-(draw > 0.01 ? 30 : 10) * dt));
    if (this.drawW < 0.01) return;
    const nock = hl.clone().addScaledVector(aim, -0.2);
    const anchor = P(head).add(new THREE.Vector3(-0.07, -0.09, 0.05));
    const e = draw * draw * (3 - 2 * draw);
    const target = nock.lerp(anchor, e);
    const handR = N("rightHand");
    const from = handR ? P(handR) : target;
    this.solveArm("right", from.lerp(target, this.drawW), new THREE.Vector3(-0.8, 0.15, -1), set);
  }

  /**
   * Shield arm. The shield sits at a guard spot in front of the chest and belly, a little
   * to the left (top near the chin), rising to the face only while the pose blocks; IK puts
   * the hand on the grip behind it, elbow down and out.
   */
  private shieldArm(dt: number, set: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const root = this.j.root, h = this.vrm.humanoid;
    const chest = h.getNormalizedBoneNode("upperChest") ?? h.getNormalizedBoneNode("chest");
    if (!chest) return;
    const r = this.shieldRaise;
    const want = root.worldToLocal(chest.getWorldPosition(new THREE.Vector3())).add(new THREE.Vector3(0.14 - 0.04 * r, -0.2 + 0.2 * r, 0.27 + 0.06 * r));
    if (this.shieldPos.lengthSq() === 0) this.shieldPos.copy(want);
    else this.shieldPos.lerp(want, 1 - Math.exp(-14 * dt));
    this.solveArm("left", this.shieldPos.clone().add(new THREE.Vector3(0, 0, -0.06)), new THREE.Vector3(0.6, -1, -0.35), set);
  }

  /**
   * Heavy two-handed sword: rests diagonally over the right shoulder when not fighting,
   * the blade lags behind the hands (weight), and the left hand stays locked on the grip.
   */
  private heavyBlade(dt: number, combat: boolean, set: (b: THREE.Object3D | null, q: THREE.Quaternion) => void, setNow: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const j = this.j, root = j.root, h = this.vrm.humanoid;
    const N = (n: VRMHumanBoneName) => h.getNormalizedBoneNode(n);
    const P = (o: THREE.Object3D) => root.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const chest = N("upperChest") ?? N("chest"), handR = N("rightHand");
    if (!chest || !handR) return;
    const parentRoot = () => quatIn(root, j.hand_r.parent!, new THREE.Quaternion()).invert();
    if (this.restSword) {
      this.restW += ((combat ? 0 : 1) - this.restW) * (1 - Math.exp(-(combat ? 12 : 3) * dt));
      if (this.restW > 0.01) {
        // Right hand in front of the right shoulder, blade up and back over it.
        const restPos = P(chest).add(new THREE.Vector3(-0.12, -0.06, 0.3));
        this.solveArm("right", P(handR).lerp(restPos, this.restW), new THREE.Vector3(-0.9, -0.7, 0.15), set);
        const blade = new THREE.Vector3(-0.18, 0.62, -0.76).normalize();
        const rest = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), blade);
        const now = quatIn(root, j.hand_r, new THREE.Quaternion());
        j.hand_r.quaternion.copy(parentRoot().multiply(now.slerp(rest, this.restW)));
      }
    }
    if (this.hurtW > 0.01) {
      // Hit: keep the sword up in front as a guard (hands before the chest, blade up and
      // forward) while the torso recoils, instead of flinging arms and blade behind.
      const guardPos = P(chest).add(new THREE.Vector3(-0.08, -0.16, 0.34));
      this.solveArm("right", P(handR).lerp(guardPos, this.hurtW), new THREE.Vector3(-0.9, -0.7, 0.15), set);
      const guard = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), new THREE.Vector3(-0.15, 0.75, 0.62).normalize());
      const now = quatIn(root, j.hand_r, new THREE.Quaternion());
      j.hand_r.quaternion.copy(parentRoot().multiply(now.slerp(guard, this.hurtW)));
    }
    // Weight: the blade's orientation trails the hands and settles.
    const target = quatIn(root, j.hand_r, new THREE.Quaternion());
    if (this.swordQ.lengthSq() === 0 || this.first) this.swordQ.copy(target);
    else this.swordQ.slerp(target, 1 - Math.exp(-(combat ? 11 : 6) * dt));
    j.hand_r.quaternion.copy(parentRoot().multiply(this.swordQ));
    // Mount the weapon on the VRM hand now so the grip point is where it will render.
    j.hand_r.position.copy(j.arm_r.worldToLocal(handR.getWorldPosition(new THREE.Vector3())));
    j.hand_r.updateMatrixWorld(true);
    if (this.gripL) this.solveArm("left", P(this.gripL), new THREE.Vector3(0.9, -0.6, 0.25), setNow);
  }

  /** Hit reactions: hands never end up behind or inside the torso. */
  private handsForward(set: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const root = this.j.root, h = this.vrm.humanoid;
    const chest = h.getNormalizedBoneNode("upperChest") ?? h.getNormalizedBoneNode("chest");
    if (!chest) return;
    const P = (o: THREE.Object3D) => root.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const front = P(chest).z + 0.16;
    for (const side of ["left", "right"] as const) {
      if (side === "left" && this.shield) continue; // the shield arm has its own guard
      const hand = h.getNormalizedBoneNode(`${side}Hand`);
      if (!hand) continue;
      const p = P(hand);
      if (p.z >= front) continue;
      const T = p.clone();
      T.z += (front - p.z) * this.hurtW;
      this.solveArm(side, T, new THREE.Vector3(side === "left" ? 0.8 : -0.8, -0.8, 0.1), set);
    }
  }

  /**
   * Slicing, not bludgeoning: while the blade moves fast, twist it around its own length so a
   * cutting edge (either side) leads the motion instead of the flat. Eases back when slow.
   */
  private edgeAlign(dt: number) {
    const j = this.j, root = j.root, b = this.blade!;
    j.hand_r.updateMatrixWorld(true);
    const P = (o: THREE.Object3D) => root.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const base = P(b.base), tip = P(b.tip), edge = P(b.edge);
    const axis = tip.clone().sub(base).normalize();
    let target = 0;
    if (this.hasTip && dt > 0) {
      const vel = tip.clone().sub(this.lastTip).divideScalar(dt);
      vel.addScaledVector(axis, -vel.dot(axis));
      const speed = vel.length();
      if (speed > 0.8) {
        const e = edge.sub(base);
        e.addScaledVector(axis, -e.dot(axis)).normalize();
        const want = vel.normalize();
        // Signed angle from the edge to the motion around the blade axis; double-edged, so
        // turn toward whichever edge is closer.
        let a = Math.atan2(new THREE.Vector3().crossVectors(e, want).dot(axis), e.dot(want));
        if (a > Math.PI / 2) a -= Math.PI; else if (a < -Math.PI / 2) a += Math.PI;
        target = a * THREE.MathUtils.smoothstep(speed, 0.8, 3.5);
      }
    }
    this.twist += (target - this.twist) * (1 - Math.exp(-(target !== 0 ? 22 : 6) * dt));
    this.lastTip.copy(tip);
    this.hasTip = true;
    if (Math.abs(this.twist) < 1e-4) return;
    // Rotate the weapon mount around the blade axis (root frame), about the hand.
    const mount = quatIn(root, j.hand_r, new THREE.Quaternion());
    const turned = new THREE.Quaternion().setFromAxisAngle(axis, this.twist).multiply(mount);
    const parentRoot = quatIn(root, j.hand_r.parent!, new THREE.Quaternion()).invert();
    j.hand_r.quaternion.copy(parentRoot.multiply(turned));
    j.hand_r.updateMatrixWorld(true);
  }

  /** Moves the procedural hand (weapon mount) onto the VRM palm. */
  private pinHand(hand: THREE.Object3D, arm: THREE.Object3D, h: VRMHumanBoneName, fore: VRMHumanBoneName) {
    const hb = this.vrm.humanoid.getRawBoneNode(h), fb = this.vrm.humanoid.getRawBoneNode(fore);
    if (!hb || !fb) return;
    hb.updateWorldMatrix(true, false);
    const w = hb.getWorldPosition(_v);
    const dir = _v2.copy(w).sub(fb.getWorldPosition(new THREE.Vector3())).normalize();
    w.addScaledVector(dir, 0.05 * this.j.root.getWorldScale(new THREE.Vector3()).y);
    hand.position.copy(arm.worldToLocal(w));
  }

  /** Eyelids for the blink the procedural face would do. */
  setBlink(v: number) { this.vrm.expressionManager?.setValue("blink", v); }
}
