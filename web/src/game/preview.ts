// Turntable preview for the character select screen.
import * as THREE from "three";
import * as M from "./mat";
import { FighterModel } from "./model";
import * as Kits from "./kits";
import type { Look } from "./roster";

export class Preview {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
  private stand = new THREE.Group();
  private model: FighterModel | null = null;
  private poses: Record<string, Kits.Pose> = {};
  private pose = "win";
  private poseT = 0;
  private spin = 0;
  private raf = 0;
  private last = performance.now();
  drag = 0;

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

  setLook(look: Look | null) {
    if (this.model) this.stand.remove(this.model);
    this.model = null;
    if (!look) return;
    this.model = new FighterModel(look);
    this.model.traverse((o) => { if ((o as THREE.Mesh).isMesh) o.castShadow = !(o as any).userData.outline; });
    this.stand.add(this.model);
    this.poses = Kits.poses(look.kit);
    this.pose = "win";
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
      if (this.pose === "win" && this.poseT > 1.1) this.pose = "idle";
      this.model.blend(this.poses[this.pose], dt, 6);
    }
    M.updateLight(this.camera);
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.renderer.dispose();
  }
}
