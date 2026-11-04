// VRM bodies (VRoid Studio exports). The procedural rig in model.ts keeps animating every
// frame; VrmRig copies its joint rotations onto the VRM's normalized humanoid bones, so every
// existing pose, attack and skill drives the VRM. three-vrm then updates spring bones (hair,
// skirt physics) and expressions (blinking).
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils, type VRM, type VRMHumanBoneName } from "@pixiv/three-vrm";

const files = new Map<string, Promise<ArrayBuffer>>();

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

/** What the procedural model is doing, for the natural-motion layer. */
export interface MotionInfo { t: number; walk: number; phase: number; crouch: number }

/** Rotation of `o` in `root`'s frame. */
function quatIn(root: THREE.Object3D, o: THREE.Object3D, out: THREE.Quaternion) {
  root.getWorldQuaternion(_inv).invert();
  return out.copy(_inv).multiply(o.getWorldQuaternion(_q2));
}

export class VrmRig {
  readonly vrm: VRM;
  private links: Link[] = [];
  private byJoint: Record<"torso" | "head" | "arm_l" | "hand_l" | "arm_r" | "hand_r" | "leg_l" | "leg_r", Link> = {} as any;
  private headQ = new THREE.Quaternion();
  private first = true;
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
    const B = (n: VRMHumanBoneName) => vrm.humanoid.getNormalizedBoneNode(n);
    root.updateMatrixWorld(true);
    const t = m.t, walk = m.walk, idle = 1 - walk, ph = m.phase;
    const breath = Math.sin(t * TAU / 3.8);
    const shift = Math.sin(t * TAU / 5.2 + 0.7);
    const look = Math.sin(t * TAU / 6.1 + 1.9);
    const crouch = Math.max(0, -m.crouch);

    // Hips: bob / crouch from the rig, idle weight shift, walk yaw + roll.
    if (this.hipsBone) {
      this.hipsBone.position.copy(this.hipsBoneRest).addScaledVector(_v.copy(j.hips.position).sub(this.hipsRest), 1 / this.scale);
      this.hipsBone.position.x += (shift * 0.018 * idle) / this.scale;
      this.hipsBone.quaternion.setFromEuler(_e.set(0, Math.sin(ph) * D(4) * walk, (Math.sin(ph) * D(3) * walk + shift * D(1.5) * idle), "YXZ"));
      this.hipsBone.updateMatrixWorld(true);
    }
    const deltaOf = (joint: THREE.Object3D, rest: THREE.Quaternion) => quatIn(root, joint, new THREE.Quaternion()).multiply(_q2.copy(rest).invert());
    const set = (b: THREE.Object3D | null, target: THREE.Quaternion) => {
      if (!b) return;
      const parentQ = quatIn(root, b.parent!, new THREE.Quaternion()).invert();
      b.quaternion.copy(parentQ.multiply(target));
      b.updateMatrixWorld(true);
    };
    const setLocal = (b: THREE.Object3D | null, x: number, y: number, z: number) => {
      if (!b) return;
      b.quaternion.setFromEuler(_e.set(x, y, z, "XYZ"));
      b.updateMatrixWorld(true);
    };
    const L = this.byJoint;

    // Torso: spread the rig's single torso rotation over spine / chest / upperChest, with
    // breathing on the chest and a walk counter-twist.
    const T = deltaOf(j.torso, L.torso.rest);
    const counter = new THREE.Quaternion().setFromEuler(_e.set(0, -Math.sin(ph) * D(4) * walk, 0));
    const I = new THREE.Quaternion();
    set(B("spine"), I.clone().slerp(T, 0.5));
    set(B("chest"), I.clone().slerp(T, 0.8).multiply(counter).multiply(rx(breath * D(1))));
    set(B("upperChest"), T.clone().multiply(counter).multiply(rx(breath * D(1.2))));

    // Head: neck takes 40%, head finishes, with a slow look-around and a little lag.
    const H = deltaOf(j.head, L.head.rest).multiply(new THREE.Quaternion().setFromEuler(_e.set(D(2) * idle * look * 0.5, D(3) * idle * look, 0)));
    this.headQ.slerp(H, this.first ? 1 : 1 - Math.exp(-22 * dt));
    const chestNow = quatIn(root, B("upperChest") ?? B("chest") ?? B("spine")!, new THREE.Quaternion());
    set(B("neck"), chestNow.clone().slerp(this.headQ, 0.4));
    set(B("head"), this.headQ);

    // Shoulders: relaxed and rising slightly with each breath.
    setLocal(B("leftShoulder"), 0, 0, -D(4) - breath * D(1.2));
    setLocal(B("rightShoulder"), 0, 0, D(4) + breath * D(1.2));

    // Arms: rig rotation (T-pose calibrated), walk swing opposite the legs, soft elbows that
    // bend more as the arm rises.
    for (const side of ["left", "right"] as const) {
      const lk = side === "left" ? L.arm_l : L.arm_r, hk = side === "left" ? L.hand_l : L.hand_r;
      const sgn = side === "left" ? 1 : -1;
      const swing = rx(-Math.sin(ph) * sgn * D(side === "left" ? 16 : 8) * walk);
      const target = swing.multiply(deltaOf(lk.joint, lk.rest)).multiply(lk.cal);
      set(B(`${side}UpperArm`), target);
      const dir = new THREE.Vector3(sgn, 0, 0).applyQuaternion(target);
      const elev = dir.angleTo(new THREE.Vector3(0, -1, 0));
      const flex = Math.min(D(16) + elev * 0.3 + Math.sin(t * TAU / 3.8 + 1) * D(2) * idle, D(75));
      // Forearm bends toward the front of the arm (around the arm's local Y).
      setLocal(B(`${side}LowerArm`), 0, -sgn * flex, 0);
      set(B(`${side}Hand`), deltaOf(hk.joint, hk.rest).multiply(hk.cal));
    }

    // Legs: rig rotation, soft knees that flex through the walk cycle and when crouching,
    // feet kept level with the ground.
    for (const side of ["left", "right"] as const) {
      const lk = side === "left" ? L.leg_l : L.leg_r;
      set(B(`${side}UpperLeg`), deltaOf(lk.joint, lk.rest));
      const cyc = 0.5 + 0.5 * Math.sin(ph + (side === "left" ? 1.2 : 1.2 + Math.PI));
      const knee = D(6) + walk * (D(10) + D(28) * cyc) + Math.min(crouch * D(260), D(55)) + (side === "left" ? shift : -shift) * D(2) * idle;
      setLocal(B(`${side}LowerLeg`), knee, 0, 0);
      const foot = B(`${side}Foot`);
      if (foot) {
        const parentQ = quatIn(root, foot.parent!, new THREE.Quaternion());
        set(foot, parentQ.clone().slerp(I, 0.75));
      }
    }
    this.first = false;

    vrm.update(dt);
    this.pinHand(j.hand_r, j.arm_r, "rightHand", "rightLowerArm");
    this.pinHand(j.hand_l, j.arm_l, "leftHand", "leftLowerArm");
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
