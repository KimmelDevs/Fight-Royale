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

/** Rotation of `o` in `root`'s frame. */
function quatIn(root: THREE.Object3D, o: THREE.Object3D, out: THREE.Quaternion) {
  root.getWorldQuaternion(_inv).invert();
  return out.copy(_inv).multiply(o.getWorldQuaternion(_q2));
}

export class VrmRig {
  readonly vrm: VRM;
  private links: Link[] = [];
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
    const add = (joint: THREE.Object3D, b: THREE.Object3D | null, cal = new THREE.Quaternion()) => {
      if (b) this.links.push({ joint, bone: b, rest: quatIn(root, joint, new THREE.Quaternion()), cal });
    };
    add(j.torso, bone("spine"));
    add(j.head, bone("head"));
    add(j.arm_l, bone("leftUpperArm"), calL);
    add(j.hand_l, bone("leftHand"), calL);
    add(j.arm_r, bone("rightUpperArm"), calR);
    add(j.hand_r, bone("rightHand"), calR);
    add(j.leg_l, bone("leftUpperLeg"));
    add(j.leg_r, bone("rightUpperLeg"));
    this.hipsBone = bone("hips");
    this.hipsRest.copy(j.hips.position);
    if (this.hipsBone) this.hipsBoneRest.copy(this.hipsBone.position);
  }

  /** Copies the procedural pose onto the VRM, runs its physics, pins weapons to its hands. */
  update(dt: number) {
    const j = this.j, root = j.root;
    root.updateMatrixWorld(true);
    if (this.hipsBone) {
      // Hip bob / crouch, converted from the root's frame into VRM units.
      this.hipsBone.position.copy(this.hipsBoneRest).addScaledVector(_v.copy(j.hips.position).sub(this.hipsRest), 1 / this.scale);
    }
    for (const l of this.links) {
      const delta = quatIn(root, l.joint, _q).multiply(_q2.copy(l.rest).invert());
      const target = delta.multiply(l.cal);
      const parentQ = quatIn(root, l.bone.parent!, new THREE.Quaternion()).invert();
      l.bone.quaternion.copy(parentQ.multiply(target));
      l.bone.updateMatrixWorld(true);
    }
    this.vrm.update(dt);
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
