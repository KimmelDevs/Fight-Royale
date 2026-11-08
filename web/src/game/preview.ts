// FIGHT_ROYALE_SIGNATURE_POSES_V2
// FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1
// Turntable preview for the character select screen.
import * as THREE from "three";
import * as M from "./mat";
import { FighterModel } from "./model";
import { Sound } from "./sound"; // ZEPHYR_ORIGINAL_SOUND_PACK_V1_20261109
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
    if (look.kit === "tristaff") Sound.preload(["spacey_swish_spin", "fast_whip_strike", "gear_fast_lock_tap", "throw_hard_wind_woosh", "metal_impact_whip", "long_sweeping_air_swoosh", "cinematic_whoosh_deep_impact"]);
    const model = new FighterModel(look);
    this.model = model;
    this.onLoading(model.loading);
    model.ready.then(() => { if (this.model === model) this.onLoading(false); });
    this.model.traverse((o) => { if ((o as THREE.Mesh).isMesh) o.castShadow = !(o as any).userData.outline; });
    this.stand.add(this.model);
    // NYTHERA_SHOWCASE_SPIN_TOSS_V3: widen framing so the whole overhead scythe stays visible.
    this.camera.position.set(0, look.kit === "scythe" ? 1.42 : 1.25,
      look.kit === "scythe" ? 5.80 : 4.6);
    this.camera.lookAt(0, look.kit === "scythe" ? 1.12 : 0.95, 0);
    this.poses = Kits.poses(look.kit);
    this.pose = "idle";
    this.poseT = 0;
  }

  // ZEPHYR_ORIGINAL_SOUND_PACK_V1_20261109: original-filename sound cues for the 9-second preview choreography.
  private zephyrShowSound(previous: number, current: number) {
    if (this.mode !== "select" || this.lookName.toLowerCase() !== "zephyr" ||
        document.visibilityState === "hidden" || current - previous > 0.20) return;
    const cues: ReadonlyArray<readonly [number, string, number]> = [
      [0.45, "spacey_swish_spin", 0.31],
      [1.16, "fast_whip_strike", 0.27],
      [2.60, "spacey_swish_spin", 0.30],
      [3.74, "long_sweeping_air_swoosh", 0.28],
      [4.54, "throw_hard_wind_woosh", 0.42],
      [6.25, "gear_fast_lock_tap", 0.43],
      [7.08, "spacey_swish_spin", 0.28],
      [7.62, "cinematic_whoosh_deep_impact", 0.43],
    ];
    const start = Math.floor(previous / 9);
    const end = Math.floor(current / 9);
    for (let cycle = start; cycle <= end; cycle++) {
      for (const [moment, name, volume] of cues) {
        const event = cycle * 9 + moment;
        if (previous < event && current >= event) Sound.play(name, volume, 0.02);
      }
    }
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
      const previousPresentationTime = this.poseT;
      this.poseT += dt;
      this.zephyrShowSound(previousPresentationTime, this.poseT);
      // Unique, looping VRM-compatible presentation; visual only.
      // Distinct showcase timing, independent of live combat/skill logic.
      const who = this.lookName.toLowerCase();
      const phase = this.mode === "victory" ? this.poseT :
        this.poseT % (who === "raigo" ? 9.6 : who === "nythera" ? 10.2 : who === "zephyr" ? 9 : 6.2);
      this.model.presentationT = phase;
      this.model.presentationMode = this.mode;
      this.model.glaivePose = who === "nythera" ? "nythera_show" : who === "zarek" ? "show_baton" : "idle";
      this.model.dragonMode = who === "zephyr" ? Math.min(3,Math.floor((this.poseT%9)/2.25)) : 0;
      this.model.dragonPose = who === "zephyr" ? "show_tristaff" : "idle";
      this.model.raigoPose = who === "raigo" ? "raigo_show" : "idle";
      // Kaizen: a controlled chain orbit, not an unrelated giant VFX circle.
      this.model.chainPose = who === "kaizen" && phase >= 0.55 && phase <= 2.30 ? "cbz_w" : "idle";
      // Ash: nock and pull a real bow string, then release at the flourish.
      this.model.draw = who === "ash" && phase >= 0.55 && phase < 1.35
        ? Math.min(1, (phase - 0.55) / 0.32) : 0;
      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt,
        who === "nythera" ? 20 : who === "zephyr" ? 19 : 11);
      if (who === "nythera") {
        // Two distinct pirouettes support the shaft spins, but the throw/catch is weapon-only.
        const ease = (a:number,b:number) => THREE.MathUtils.smoothstep(phase,a,b);
        this.model.rotation.y = 2*Math.PI*(ease(1.21,2.25)+ease(6.14,6.95));
        if (this.mode === "select") this.model.animateNytheraShowcase(phase,dt);
        else {
          // A mode change during an airborne throw must restore the held weapon.
          this.model.rotation.y = 0;
          this.model.animateNytheraShowcase(8.5,dt);
        }
      } else this.model.rotation.y = 0;
    }
    M.updateLight(this.camera);
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.renderer.dispose();
  }
}
