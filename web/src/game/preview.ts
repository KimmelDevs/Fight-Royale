// FIGHT_ROYALE_SIGNATURE_POSES_V2
// FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1
// Turntable preview for the character select screen.
import * as THREE from "three";
import * as M from "./mat";
import { FighterModel } from "./model";
import * as Kits from "./kits";
import type { Look } from "./roster";
import { presentationPose } from "./presentation";

export class Preview {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
  private stand = new THREE.Group();
  private model: FighterModel | null = null;
  private poses: Record<string, Kits.Pose> = {};
  private pose = "idle";
  private mode: "select" | "victory" = "select";
  private lookName = "";
  private poseT = 0;
  private spin = 0;
  private raf = 0;
  private last = performance.now();
  drag = 0;
  /** Called with true while the shown fighter's 3D model is still loading. */
  onLoading: (loading: boolean) => void = () => {};

  constructor(private canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.scene.add(new THREE.HemisphereLight("#e6f0ff", "#b8d0b0", 1.2));
    const sun = new THREE.DirectionalLight(0xffffff, 1.9);
    sun.position.copy(M.LIGHT_DIR).multiplyScalar(10);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    this.scene.add(sun);
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.95, 0.12, 48), new THREE.MeshLambertMaterial({ color: "#eef2fb" }));
    disc.position.y = -0.06;
    disc.receiveShadow = true;
    this.stand.add(disc);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.93, 0.045, 6, 64).rotateX(Math.PI / 2), new THREE.MeshBasicMaterial({ color: "#e6c26e" }));
    ring.scale.y = 0.4;
    this.stand.add(ring);
    this.scene.add(this.stand);
    this.camera.position.set(0, 1.25, 4.6);
    this.camera.lookAt(0, 0.95, 0);
    const loop = (now: number) => {
      this.raf = requestAnimationFrame(loop);
      const dt = Math.min((now - this.last) / 1000, 0.05);
      this.last = now;
      this.tick(dt);
    };
    this.raf = requestAnimationFrame(loop);
  }

  setMode(mode: "select" | "victory") { this.mode = mode; this.poseT = 0; }

  setLook(look: Look | null) {
    if (this.model) this.stand.remove(this.model);
    this.model = null;
    if (!look) return;
    this.lookName = look.name;
    const model = new FighterModel(look);
    this.model = model;
    this.onLoading(model.loading);
    model.ready.then(() => { if (this.model === model) this.onLoading(false); });
    this.model.traverse((o) => { if ((o as THREE.Mesh).isMesh) o.castShadow = !(o as any).userData.outline; });
    this.stand.add(this.model);
    this.poses = Kits.poses(look.kit);
    this.pose = "idle";
    this.poseT = 0;
  }

  private tick(dt: number) {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    if (this.canvas.width !== Math.floor(w * this.renderer.getPixelRatio())) {
      this.renderer.setSize(w, h, false);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
    }
    M.timeU.value += dt;
    this.spin += dt * 0.25 + this.drag;
    this.drag = 0;
    this.stand.rotation.y = Math.sin(this.spin) * 0.6;
    if (this.model) {
      this.poseT += dt;
      // Unique, looping VRM-compatible presentation; visual only.
      // Distinct showcase timing, independent of live combat/skill logic.
      const phase = this.mode === "victory" ? this.poseT : this.poseT % 6.2;
      const who = this.lookName.toLowerCase();
      this.model.presentationT = phase;
      this.model.presentationMode = this.mode;
      this.model.glaivePose = who === "zarek" ? "show_baton" : "idle";
      // Kaizen: a controlled chain orbit, not an unrelated giant VFX circle.
      this.model.chainPose = who === "kaizen" && phase >= 0.55 && phase <= 2.30 ? "cbz_w" : "idle";
      // Ash: nock and pull a real bow string, then release at the flourish.
      this.model.draw = who === "ash" && phase >= 0.55 && phase < 1.35
        ? Math.min(1, (phase - 0.55) / 0.32) : 0;
      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt, 11);
    }
    M.updateLight(this.camera);
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.renderer.dispose();
  }
}
