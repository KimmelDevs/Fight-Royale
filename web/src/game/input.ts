// Keyboard + mouse state, mapped through the player's key bindings (keys.ts). Defaults: left
// mouse attacks, right mouse blocks, WASD moves relative to the camera, Space jumps, Z/X/C
// cast skills. Any action can be bound to a key or a mouse button.
import * as THREE from "three";
import { actionFor, type Action } from "./keys";

export interface RawInput { attack: boolean; block: boolean; jump: boolean; skill: string; mx: number; mz: number }

const SKILL_KEY: Partial<Record<Action, string>> = { skill1: "z", skill2: "x", skill3: "c" };

export class Input {
  /** Pressed codes: keyboard codes and "Mouse0".."Mouse4". */
  private down = new Set<string>();
  private skills: string[] = [];
  private el: HTMLElement | null = null;

  private press(code: string, on: boolean) {
    if (on && !this.down.has(code)) {
      const a = actionFor(code);
      const s = a && SKILL_KEY[a];
      if (s) this.skills.push(s);
    }
    if (on) this.down.add(code); else this.down.delete(code);
  }

  private onKey = (e: KeyboardEvent) => {
    if ((e.target as HTMLElement)?.tagName === "INPUT") return;
    this.press(e.code, e.type === "keydown");
    if (e.type === "keydown" && actionFor(e.code) && (e.code === "Space" || e.code.startsWith("Arrow") || e.code === "Tab")) e.preventDefault();
  };
  private onMouse = (e: MouseEvent) => {
    this.press("Mouse" + e.button, true);
    e.preventDefault();
  };
  private onUp = (e: MouseEvent) => { this.press("Mouse" + e.button, false); };
  private noMenu = (e: Event) => e.preventDefault();
  private onBlur = () => { this.down.clear(); };

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

  private held(a: Action) {
    for (const c of this.down) if (actionFor(c) === a) return true;
    return false;
  }

  /** Reads this frame's input; movement is converted to a world direction using the camera. */
  read(camera: THREE.Camera): RawInput {
    let x = 0, y = 0;
    if (this.held("right")) x += 1;
    if (this.held("left")) x -= 1;
    if (this.held("up")) y += 1;
    if (this.held("down")) y -= 1;
    let mx = 0, mz = 0;
    if (x || y) {
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      const fwd = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 2).negate();
      right.y = 0; fwd.y = 0;
      right.normalize(); fwd.normalize();
      const m = right.multiplyScalar(x).addScaledVector(fwd, y).normalize();
      mx = m.x; mz = m.z;
    }
    return { attack: this.held("attack"), block: this.held("block"), jump: this.held("jump"), skill: this.skills.shift() ?? "", mx, mz };
  }
}
