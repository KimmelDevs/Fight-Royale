// Combat VFX: sparks, droplets, flashes, rings, water effects, lightning, meteors, ground
// markers, floating damage numbers (DOM overlay) and blade trails. Everything self-expires.
import * as THREE from "three";
import * as M from "./mat";

type Updater = (dt: number) => boolean; // return false when finished

const tmpM = new THREE.Matrix4();
const tmpQ = new THREE.Quaternion();
const tmpS = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);

const BOX = new THREE.BoxGeometry(0.014, 0.09, 0.014);
const DROP = new THREE.SphereGeometry(0.07, 8, 4);
const SPH = new THREE.SphereGeometry(1, 16, 8);
// Billboard geometry: these impacts burst AT weapon contact, including in midair.
const CLASH_HALO = new THREE.RingGeometry(0.80, 1.0, 40);
const clashStreakShape = new THREE.Shape();
clashStreakShape.moveTo(-1.0, -0.065);
clashStreakShape.lineTo(-0.08, -0.035);
clashStreakShape.lineTo(1.04, 0);
clashStreakShape.lineTo(-0.08, 0.035);
clashStreakShape.lineTo(-1.0, 0.065);
clashStreakShape.closePath();
const CLASH_STREAK = new THREE.ShapeGeometry(clashStreakShape);
const RING = new THREE.TorusGeometry(0.95, 0.05, 6, 48).rotateX(Math.PI / 2);
const WRING = new THREE.TorusGeometry(0.91, 0.09, 8, 48).rotateX(Math.PI / 2);
const GEY = new THREE.CylinderGeometry(0.08, 0.22, 1, 16).translate(0, 0.5, 0);
const DISC = new THREE.CylinderGeometry(1, 1, 0.01, 40);
const ROCK = new THREE.DodecahedronGeometry(0.07, 0);
const MOTE = new THREE.OctahedronGeometry(0.03, 0);
const rockMats = ["#8a6a48", "#6e5a46", "#a08060", "#5c4a3a"].map((c) => new THREE.MeshLambertMaterial({ color: c }));
const moteMats = new Map<string, THREE.Material>();
const dustMat = new THREE.MeshBasicMaterial({ color: "#b89a74", transparent: true, opacity: 0.45, depthWrite: false });

export class Fx {
  scene: THREE.Scene;
  camera: THREE.Camera;
  overlay: HTMLElement | null;
  private items: Updater[] = [];
  private numbers: { el: HTMLDivElement; pos: THREE.Vector3; t: number }[] = [];

  constructor(scene: THREE.Scene, camera: THREE.Camera, overlay: HTMLElement | null) {
    this.scene = scene;
    this.camera = camera;
    this.overlay = overlay;
  }

  update(dt: number, realDt: number, w: number, h: number) {
    this.items = this.items.filter((u) => u(dt));
    const p = new THREE.Vector3();
    this.numbers = this.numbers.filter((n) => {
      n.t += realDt;
      const rise = Math.min(n.t / 0.8, 1);
      p.copy(n.pos).add(new THREE.Vector3(0, 0.55 * (1 - (1 - rise) * (1 - rise)), 0)).project(this.camera);
      const pop = n.t < 0.09 ? 0.4 + (n.t / 0.09) * 0.75 : n.t < 0.17 ? 1.15 - ((n.t - 0.09) / 0.08) * 0.15 : 1;
      const alpha = n.t < 0.85 ? 1 : 1 - (n.t - 0.85) / 0.25;
      n.el.style.transform = `translate(${(p.x * 0.5 + 0.5) * w}px, ${(-p.y * 0.5 + 0.5) * h}px) translate(-50%, -50%) scale(${pop})`;
      n.el.style.opacity = String(Math.max(alpha, 0));
      n.el.style.display = p.z > 1 ? "none" : "block";
      if (n.t > 1.1) { n.el.remove(); return false; }
      return true;
    });
  }

  clear() {
    this.items.forEach((u) => u(999));
    this.items = [];
    this.numbers.forEach((n) => n.el.remove());
    this.numbers = [];
  }

  private add(obj: THREE.Object3D, u: Updater) {
    this.scene.add(obj);
    this.items.push((dt) => {
      const alive = u(dt);
      if (!alive) {
        this.scene.remove(obj);
        obj.traverse((o) => { const m = o as THREE.Mesh; if (m.isMesh && (m as any).ownsMat) (m.material as THREE.Material).dispose(); });
      }
      return alive;
    });
  }

  /** Instanced burst of small pieces flying out under gravity. */
  private burst(pos: THREE.Vector3, geo: THREE.BufferGeometry, mat: THREE.Material, amount: number,
    speed: number, dir: THREE.Vector3 | null, spread: number, gravity: number, life: number, scale: number, align: boolean) {
    const inst = new THREE.InstancedMesh(geo, mat, amount);
    inst.frustumCulled = false;
    const vel: THREE.Vector3[] = [], p: THREE.Vector3[] = [];
    const base = dir && dir.lengthSq() > 0 ? dir.clone().normalize() : null;
    for (let i = 0; i < amount; i++) {
      let d = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
      if (base) d = base.clone().add(d.multiplyScalar(spread)).normalize();
      else if (spread < 1) d = new THREE.Vector3(d.x * spread, 1, d.z * spread).normalize();
      vel.push(d.multiplyScalar(speed * (0.5 + Math.random() * 0.5)));
      p.push(pos.clone());
    }
    const sizes = Array.from({ length: amount }, () => scale * (0.5 + Math.random() * 0.7));
    let t = 0;
    this.add(inst, (dt) => {
      t += dt;
      const f = 1 - t / life;
      for (let i = 0; i < amount; i++) {
        vel[i].y -= gravity * dt;
        vel[i].multiplyScalar(Math.max(1 - 3 * dt, 0));
        p[i].addScaledVector(vel[i], dt);
        if (align && vel[i].lengthSq() > 1e-4) tmpQ.setFromUnitVectors(UP, tmpS.copy(vel[i]).normalize());
        else tmpQ.identity();
        tmpS.setScalar(Math.max(f, 0) * sizes[i]);
        tmpM.compose(p[i], tmpQ, tmpS);
        inst.setMatrixAt(i, tmpM);
      }
      inst.instanceMatrix.needsUpdate = true;
      return t < life;
    });
  }

  sparks(pos: THREE.Vector3, color: string, amount = 20, speed = 7, dir: THREE.Vector3 | null = null) {
    this.burst(pos, BOX, new THREE.MeshBasicMaterial({ color }), amount, speed, dir, dir ? 0.7 : 1, 9, 0.35, 1, true);
  }

  splash(pos: THREE.Vector3, amount = 16, size = 1, color = "#3a8cff") {
    this.burst(pos, DROP, M.additive(color, 0.85), amount, 5 * size, null, 0.6, 15, 0.8, size, false);
  }

  /** Earth: chunky rocks thrown up, a dust cloud and a ground crack ring. */
  rocks(pos: THREE.Vector3, amount = 16, power = 1) {
    const g = new THREE.Vector3(pos.x, Math.max(pos.y, 0.05), pos.z);
    for (let k = 0; k < 2; k++) {
      this.burst(g, ROCK, rockMats[(Math.random() * rockMats.length) | 0], Math.ceil(amount / 2), 6.5 * power, UP, 0.75, 20, 0.95, 1.5 * power, false);
    }
    this.burst(g, SPH, dustMat, 9, 2.2 * power, UP, 1.4, -0.6, 1.0, 0.32 * power, false);
    this.ring(g, "#6a4a2a", 1.5 * power, 0.45, 0.85);
    this.flash(g.clone().setY(g.y + 0.25), "#c8a070", 0.6 * power, 0.2, 0.5);
  }

  /** Light: small glowing motes that drift upward and fade. */
  motes(pos: THREE.Vector3, color: string, amount = 4) {
    let mat = moteMats.get(color);
    if (!mat) { mat = M.additive(color, 0.95); moteMats.set(color, mat); }
    this.burst(pos, MOTE, mat, amount, 1.1, UP, 1.2, -1.2, 0.7, 2.2, false);
  }

  embers(pos: THREE.Vector3, color: string, amount = 20) {
    this.burst(pos, DROP, M.additive(color, 0.9), amount, 3, new THREE.Vector3(0, 1, 0), 0.8, -2, 0.7, 0.4, false);
  }

  /** Bright crossed-blade starburst + expanding shock ring at a 3D collision point.
   * Faces the camera so both players see it, even when weapons meet in the air. */
  clashBurst(pos: THREE.Vector3, color: string, size = 1) {
    const root = new THREE.Group();
    root.position.copy(pos);
    const mats: Array<{ mat: THREE.MeshBasicMaterial; opacity: number }> = [];
    const material = (tint: string, opacity: number) => {
      const mat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity,
        depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
      mats.push({ mat, opacity });
      return mat;
    };
    const halo = new THREE.Mesh(CLASH_HALO, material(color, 0.92));
    root.add(halo);
    const streaks = new THREE.Group();
    for (const [angle, tint, opacity] of [
      [-Math.PI / 5, "#ffffff", 1], [Math.PI / 3.2, color, 0.92],
      [Math.PI * 0.7, "#fff5d5", 0.75],
    ] as [number, string, number][]) {
      const streak = new THREE.Mesh(CLASH_STREAK, material(tint, opacity));
      streak.rotation.z = angle;
      streaks.add(streak);
    }
    root.add(streaks);
    const core = new THREE.Mesh(SPH, material("#ffffff", 0.86));
    root.add(core);
    let t = 0;
    this.add(root, (dt) => {
      t += dt;
      const progress = Math.min(t / 0.26, 1);
      const fade = Math.pow(1 - progress, 1.4);
      root.quaternion.copy(this.camera.quaternion);
      halo.scale.setScalar(size * (0.15 + 1.25 * (1 - (1 - progress) ** 3)));
      streaks.scale.setScalar(size * (1.15 - 0.25 * progress));
      streaks.rotation.z = progress * 0.18;
      core.scale.setScalar(size * (0.17 - progress * 0.11));
      for (const item of mats) item.mat.opacity = item.opacity * fade;
      return t < 0.26;
    });
    // The shared geometry is kept, but each individual effect material is freed.
    for (const mesh of [halo, core, ...streaks.children]) (mesh as any).ownsMat = true;
  }

  flash(pos: THREE.Vector3, color: string, size = 0.5, dur = 0.14, opacity = 0.8) {
    const mat = M.additive(color, opacity);
    const m = new THREE.Mesh(SPH, mat);
    (m as any).ownsMat = true;
    m.position.copy(pos);
    let t = 0;
    this.add(m, (dt) => {
      t += dt;
      const f = Math.min(t / dur, 1);
      m.scale.setScalar(size * (0.3 + 0.7 * (1 - (1 - f) * (1 - f))));
      mat.opacity = opacity * (1 - f);
      return t < dur;
    });
  }

  ring(pos: THREE.Vector3, color: string, radius = 2, dur = 0.35, opacity = 0.9) {
    const mat = M.additive(color, opacity);
    const m = new THREE.Mesh(RING, mat);
    (m as any).ownsMat = true;
    m.position.set(pos.x, 0.05, pos.z);
    let t = 0;
    this.add(m, (dt) => {
      t += dt;
      const f = Math.min(t / dur, 1);
      const e = 1 - Math.pow(1 - f, 3);
      m.scale.set(0.2 + (radius - 0.2) * e, 0.3, 0.2 + (radius - 0.2) * e);
      mat.opacity = opacity * (1 - f);
      return t < dur;
    });
  }

  waveRing(pos: THREE.Vector3, radius: number, dur: number, color = "#2680ff") {
    const mat = M.water(color, 0.7, 1.4);
    const m = new THREE.Mesh(WRING, mat);
    (m as any).ownsMat = true;
    m.position.set(pos.x, 0.05, pos.z);
    let t = 0;
    this.add(m, (dt) => {
      t += dt;
      const f = Math.min(t / dur, 1);
      const e = 1 - Math.pow(1 - f, 3);
      m.scale.set(0.2 + (radius - 0.2) * e, 4, 0.2 + (radius - 0.2) * e);
      mat.uniforms.alphaMult.value = 1 - f * f;
      return t < dur;
    });
  }

  geyser(pos: THREE.Vector3, height: number, delay = 0, color = "#2680ff") {
    const mat = M.water(color, 0.75, 1.5);
    const m = new THREE.Mesh(GEY, mat);
    (m as any).ownsMat = true;
    m.position.set(pos.x, 0, pos.z);
    m.visible = false;
    let t = -delay;
    let popped = false;
    this.add(m, (dt) => {
      t += dt;
      if (t < 0) return true;
      if (!popped) { popped = true; m.visible = true; this.splash(m.position.clone().add(new THREE.Vector3(0, 0.1, 0)), 10, 0.8, color); }
      if (t < 0.2) {
        const f = t / 0.2;
        const back = 1 + 2.7 * Math.pow(f - 1, 3) + 1.7 * Math.pow(f - 1, 2);
        m.scale.set(1, Math.max(height * back, 0.01), 1);
      } else {
        const f = Math.min((t - 0.2) / 0.35, 1);
        m.scale.set(1 - 0.6 * f, height * (1 - 0.85 * f), 1 - 0.6 * f);
        mat.uniforms.alphaMult.value = 1 - f;
      }
      return t < 0.55;
    });
  }

  lightning(pos: THREE.Vector3, color: string) {
    const root = new THREE.Group();
    const core = M.additive("#fff8c0", 1);
    const halo = M.additive(color, 0.6);
    const top = pos.clone().add(new THREE.Vector3((Math.random() - 0.5) * 1.2, 9, (Math.random() - 0.5) * 1.2));
    let prev = top.clone();
    for (let i = 0; i < 9; i++) {
      const t = (i + 1) / 9;
      let next = top.clone().lerp(pos, t).add(new THREE.Vector3((Math.random() - 0.5) * 0.7, 0, (Math.random() - 0.5) * 0.7).multiplyScalar(1 - t * 0.8));
      if (i === 8) next = pos.clone();
      for (const [w, mat] of [[0.05, core], [0.16, halo]] as [number, THREE.Material][]) {
        const seg = new THREE.Mesh(new THREE.BoxGeometry(w, prev.distanceTo(next), w), mat);
        seg.position.copy(prev).add(next).multiplyScalar(0.5);
        seg.quaternion.setFromUnitVectors(UP, next.clone().sub(prev).normalize());
        root.add(seg);
      }
      prev = next;
    }
    let t = 0;
    this.add(root, (dt) => {
      t += dt;
      root.visible = !(t > 0.07 && t < 0.11);
      return t < 0.19;
    });
  }

  /** Pulsing ground marker where an area attack will land. */
  telegraph(pos: THREE.Vector3, color: string, radius: number, dur: number) {
    const g = new THREE.Group();
    g.position.set(pos.x, 0.03, pos.z);
    const dm = M.additive(color, 0.22);
    const disc = new THREE.Mesh(DISC, dm);
    disc.scale.set(radius, 1, radius);
    g.add(disc);
    const rm = M.additive(color, 0.9);
    const rim = new THREE.Mesh(RING, rm);
    rim.scale.set(radius, 0.4, radius);
    g.add(rim);
    let t = 0;
    this.add(g, (dt) => {
      t += dt;
      dm.opacity = 0.18 + 0.27 * (0.5 + 0.5 * Math.sin(t * 20));
      return t < dur;
    });
  }

  explosion(pos: THREE.Vector3, color: string, radius: number) {
    const c = new THREE.Vector3(pos.x, 0.6, pos.z);
    this.flash(c, "#ffbf59", radius * 0.4, 0.2, 0.7);
    this.flash(c, color, radius * 0.6, 0.3, 0.45);
    this.sparks(c, color, 50, 9);
    this.sparks(c, "#ffe680", 30, 6, new THREE.Vector3(0, 1, 0));
    this.embers(c, color, 24);
    this.ring(pos, color, radius * 1.4, 0.4);
  }

  meteor(pos: THREE.Vector3, color: string, dur: number) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.55, 16, 8), new THREE.MeshBasicMaterial({ color }));
    const start = pos.clone().add(new THREE.Vector3(-3, 10, -1.5));
    const end = new THREE.Vector3(pos.x, 0.4, pos.z);
    let t = 0, emit = 0;
    this.add(m, (dt) => {
      t += dt;
      const f = Math.min(t / dur, 1);
      m.position.lerpVectors(start, end, f * f);
      emit -= dt;
      if (emit <= 0) { emit = 0.04; this.embers(m.position.clone(), "#ff9933", 4); }
      return t < dur;
    });
  }

  smoke(pos: THREE.Vector3, color: string) {
    const c = pos.clone().add(new THREE.Vector3(0, 0.9, 0));
    this.flash(c, color, 0.7, 0.25, 0.6);
    this.sparks(c, color, 26, 4);
  }

  /** Big charging water sphere that grows above `pos`, then slams down after `dur`. */
  bigOrb(pos: THREE.Vector3, dur: number, color = "#1460ff") {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(SPH, M.water(color, 0.85, 1.6)));
    const inner = new THREE.Mesh(SPH, M.water("#99f2ff", 1, 2.2));
    inner.scale.setScalar(0.55);
    g.add(inner);
    const top = pos.clone().add(new THREE.Vector3(0, 4, 0));
    const low = pos.clone().add(new THREE.Vector3(0, 0.6, 0));
    let t = 0;
    this.add(g, (dt) => {
      t += dt;
      const f = t / dur;
      if (f < 0.7) { g.position.copy(top); g.scale.setScalar(0.1 + 1.0 * Math.min(f / 0.7, 1)); }
      else { g.position.lerpVectors(top, low, Math.pow((f - 0.7) / 0.3, 2)); }
      g.rotation.y += dt * 3;
      return t < dur;
    });
  }

  /** Translucent bubble that follows `target` for `dur` seconds, then pops. */
  bubble(target: THREE.Object3D, dur: number, color = "#59b3ff") {
    const mat = M.water(color, 0.15, 1.25);
    const m = new THREE.Mesh(SPH, mat);
    (m as any).ownsMat = true;
    let t = 0;
    this.add(m, (dt) => {
      t += dt;
      m.position.copy(target.position).add(new THREE.Vector3(0, 0.88, 0));
      const pop = Math.min(t / 0.3, 1);
      const w = 1 + 0.035 * Math.sin(t * 5);
      m.scale.set(w * pop, (2 - w) * pop, w * pop);
      if (t >= dur) this.splash(m.position.clone(), 30, 1.4, color);
      return t < dur && target.parent !== null;
    });
  }

  /** Quick crossing slash streaks (Thousand Cuts). */
  slashes(pos: THREE.Vector3, color: string) {
    const g = new THREE.Group();
    g.position.set(pos.x, 1.0, pos.z);
    const mat = M.additive(color, 1);
    for (let i = 0; i < 2; i++) {
      const s = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.03, 0.03), mat);
      s.rotation.set(Math.random() * 3, Math.random() * 3, Math.random() * 3);
      g.add(s);
    }
    let t = 0;
    this.add(g, (dt) => {
      t += dt;
      mat.opacity = 1 - t / 0.16;
      g.scale.setScalar(0.6 + t * 3);
      return t < 0.16;
    });
  }

  /** Arrows falling into the target area over `dur` seconds. */
  arrowRain(pos: THREE.Vector3, radius: number, dur: number, color: string) {
    const g = new THREE.Group();
    const mat = new THREE.MeshBasicMaterial({ color: "#f4e6c0" });
    const tip = new THREE.MeshBasicMaterial({ color });
    const arrows: { m: THREE.Group; t0: number; to: THREE.Vector3 }[] = [];
    for (let i = 0; i < 14; i++) {
      const a = new THREE.Group();
      const shaft = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.7, 0.02), mat);
      a.add(shaft);
      const h = new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.12, 4), tip);
      h.position.y = -0.4;
      h.rotation.x = Math.PI;
      a.add(h);
      const r = Math.sqrt(Math.random()) * radius;
      const th = Math.random() * Math.PI * 2;
      const to = new THREE.Vector3(pos.x + Math.cos(th) * r, 0.3, pos.z + Math.sin(th) * r);
      arrows.push({ m: a, t0: Math.random() * dur * 0.6 + dur * 0.3, to });
      a.visible = false;
      g.add(a);
    }
    let t = 0;
    this.add(g, (dt) => {
      t += dt;
      for (const a of arrows) {
        const f = (t - (a.t0 - 0.25)) / 0.25;
        a.m.visible = f > 0 && f < 1.6;
        a.m.position.set(a.to.x, a.to.y + Math.max(1 - f, 0) * 8, a.to.z);
      }
      return t < dur + 0.4;
    });
  }

  number(pos: THREE.Vector3, text: string, color: string, size = 1) {
    if (!this.overlay) return;
    const el = document.createElement("div");
    el.className = "dmg";
    el.textContent = text;
    el.style.color = color;
    el.style.fontSize = `${Math.round(24 * size)}px`;
    this.overlay.appendChild(el);
    this.numbers.push({ el, pos: pos.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.3, 0, 0)), t: 0 });
  }
}

/** Fading ribbon swept by a blade while `emitting` is on. Built in world space. */
export class Trail {
  mesh: THREE.Mesh;
  emitting = false;
  private samples: { b: THREE.Vector3; t: THREE.Vector3; age: number }[] = [];
  private geo = new THREE.BufferGeometry();
  private base: THREE.Object3D;
  private tip: THREE.Object3D;
  private color: THREE.Color;

  constructor(base: THREE.Object3D, tip: THREE.Object3D, color: string) {
    this.base = base;
    this.tip = tip;
    this.color = new THREE.Color(color);
    const mat = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    this.mesh = new THREE.Mesh(this.geo, mat);
    this.mesh.frustumCulled = false;
  }

  update(dt: number) {
    for (const s of this.samples) s.age += dt;
    while (this.samples.length && this.samples[0].age > 0.16) this.samples.shift();
    if (this.emitting) {
      const b = this.base.getWorldPosition(new THREE.Vector3());
      const t = this.tip.getWorldPosition(new THREE.Vector3());
      this.samples.push({ b, t, age: 0 });
      if (this.samples.length > 28) this.samples.shift();
    }
    const n = this.samples.length;
    if (n < 2) { this.mesh.visible = false; return; }
    this.mesh.visible = true;
    const pos = new Float32Array((n - 1) * 6 * 3);
    const colA = new Float32Array((n - 1) * 6 * 3);
    let o = 0;
    const put = (p: THREE.Vector3, a: number) => {
      pos[o] = p.x; pos[o + 1] = p.y; pos[o + 2] = p.z;
      colA[o] = this.color.r * a; colA[o + 1] = this.color.g * a; colA[o + 2] = this.color.b * a;
      o += 3;
    };
    for (let i = 0; i < n - 1; i++) {
      const s0 = this.samples[i], s1 = this.samples[i + 1];
      const a0 = Math.max(1 - s0.age / 0.16, 0), a1 = Math.max(1 - s1.age / 0.16, 0);
      put(s0.b, 0); put(s0.t, a0); put(s1.t, a1);
      put(s0.b, 0); put(s1.t, a1); put(s1.b, 0);
    }
    this.geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    this.geo.setAttribute("color", new THREE.BufferAttribute(colA, 3));
    this.geo.computeBoundingSphere();
  }
}
