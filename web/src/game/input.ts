// Keyboard + mouse state. Left mouse attacks, right mouse blocks, WASD moves relative to the
// camera, Space jumps, Z/X/C cast skills.
import * as THREE from "three";

export interface RawInput { attack: boolean; block: boolean; jump: boolean; skill: string; mx: number; mz: number }

export class Input {
  private keys = new Set<string>();
  private mouse = [false, false, false];
  private skills: string[] = [];
  private el: HTMLElement | null = null;

  private onKey = (e: KeyboardEvent) => {
    if ((e.target as HTMLElement)?.tagName === "INPUT") return;
    if (e.type === "keydown") {
      if (!this.keys.has(e.code)) {
        if (e.code === "KeyZ") this.skills.push("z");
        if (e.code === "KeyX") this.skills.push("x");
        if (e.code === "KeyC") this.skills.push("c");
      }
      this.keys.add(e.code);
      if (e.code === "Space") e.preventDefault();
    } else this.keys.delete(e.code);
  };
  private onMouse = (e: MouseEvent) => {
    this.mouse[e.button] = e.type === "mousedown";
    if (e.type === "mousedown") e.preventDefault();
  };
  private onUp = (e: MouseEvent) => { this.mouse[e.button] = false; };
  private noMenu = (e: Event) => e.preventDefault();
  private onBlur = () => { this.keys.clear(); this.mouse = [false, false, false]; };

  attach(el: HTMLElement) {
    this.el = el;
    window.addEventListener("keydown", this.onKey);
    window.addEventListener("keyup", this.onKey);
    el.addEventListener("mousedown", this.onMouse);
    window.addEventListener("mouseup", this.onUp);
    el.addEventListener("contextmenu", this.noMenu);
    window.addEventListener("blur", this.onBlur);
  }

  detach() {
    window.removeEventListener("keydown", this.onKey);
    window.removeEventListener("keyup", this.onKey);
    this.el?.removeEventListener("mousedown", this.onMouse);
    window.removeEventListener("mouseup", this.onUp);
    this.el?.removeEventListener("contextmenu", this.noMenu);
    window.removeEventListener("blur", this.onBlur);
  }

  /** Reads this frame's input; movement is converted to a world direction using the camera. */
  read(camera: THREE.Camera): RawInput {
    const k = this.keys;
    let x = 0, y = 0;
    if (k.has("KeyD") || k.has("ArrowRight")) x += 1;
    if (k.has("KeyA") || k.has("ArrowLeft")) x -= 1;
    if (k.has("KeyW") || k.has("ArrowUp")) y += 1;
    if (k.has("KeyS") || k.has("ArrowDown")) y -= 1;
    let mx = 0, mz = 0;
    if (x || y) {
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      const fwd = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 2).negate();
      right.y = 0; fwd.y = 0;
      right.normalize(); fwd.normalize();
      const m = right.multiplyScalar(x).addScaledVector(fwd, y).normalize();
      mx = m.x; mz = m.z;
    }
    return { attack: this.mouse[0], block: this.mouse[2], jump: k.has("Space"), skill: this.skills.shift() ?? "", mx, mz };
  }
}
