// FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1
// Player key bindings. Each action has up to two inputs: a keyboard code (KeyboardEvent.code,
// e.g. "KeyW", "Space", "ArrowUp") or a mouse button ("Mouse0" left, "Mouse1" middle,
// "Mouse2" right). Saved per browser in localStorage.

export type Action = "up" | "down" | "left" | "right" | "jump" | "attack" | "block" | "skill1" | "skill2" | "skill3" | "skill4";

export const ACTIONS: { id: Action; label: string }[] = [
  { id: "up", label: "Move up / forward" },
  { id: "down", label: "Move down / back (Brawl: drop, fast fall)" },
  { id: "left", label: "Move left" },
  { id: "right", label: "Move right" },
  { id: "jump", label: "Jump" },
  { id: "attack", label: "Attack (tap) / charged attack (hold)" },
  { id: "block", label: "Block / shield" },
  { id: "skill1", label: "Skill 1" },
  { id: "skill2", label: "Skill 2" },
  { id: "skill3", label: "Skill 3" },
  { id: "skill4", label: "Skill 4 (unlocked V)" },
];

export type Bindings = Record<Action, [string, string]>;

export const DEFAULT_BINDINGS: Bindings = {
  up: ["KeyW", "ArrowUp"],
  down: ["KeyS", "ArrowDown"],
  left: ["KeyA", "ArrowLeft"],
  right: ["KeyD", "ArrowRight"],
  jump: ["Space", ""],
  attack: ["Mouse0", ""],
  block: ["Mouse2", ""],
  skill1: ["KeyZ", ""],
  skill2: ["KeyX", ""],
  skill3: ["KeyC", ""],
  skill4: ["KeyV", ""],
};

/** Keys the game reserves (leave match, rematch); they can't be bound. */
export const RESERVED = new Set(["Escape", "KeyR"]);

const STORE = "fr-keys";
// Starts at the defaults so server and first client render match; loadBindings() swaps in
// the saved set after mount (called by useBindings).
let current: Bindings = structuredClone(DEFAULT_BINDINGS);
let loaded = false;
const listeners = new Set<() => void>();

function load(): Bindings {
  const b = structuredClone(DEFAULT_BINDINGS);
  try {
    const raw = typeof localStorage !== "undefined" ? localStorage.getItem(STORE) : null;
    if (raw) {
      const saved = JSON.parse(raw);
      for (const a of ACTIONS) {
        const v = saved[a.id];
        if (Array.isArray(v)) b[a.id] = [String(v[0] ?? ""), String(v[1] ?? "")];
      }
    }
  } catch {}
  return b;
}

export function bindings(): Bindings { return current; }

export function loadBindings() {
  if (loaded) return;
  loaded = true;
  current = load();
  listeners.forEach((l) => l());
}

export function setBindings(b: Bindings) {
  current = b;
  try { localStorage.setItem(STORE, JSON.stringify(b)); } catch {}
  listeners.forEach((l) => l());
}

/** Binds `code` to one slot of an action, removing it from any other action first. */
export function bind(action: Action, slot: 0 | 1, code: string) {
  const b = structuredClone(current);
  if (code) for (const a of ACTIONS) b[a.id] = b[a.id].map((c) => (c === code ? "" : c)) as [string, string];
  b[action][slot] = code;
  setBindings(b);
}

export function resetBindings() { setBindings(structuredClone(DEFAULT_BINDINGS)); }

export function onBindingsChange(l: () => void) { listeners.add(l); return () => { listeners.delete(l); }; }

/** The action a key / mouse code triggers, if any. */
export function actionFor(code: string): Action | null {
  for (const a of ACTIONS) if (current[a.id].includes(code)) return a.id;
  return null;
}

/** Human label for a code: "W", "Space", "Left click", "Up arrow". */
export function keyLabel(code: string): string {
  if (!code) return "-";
  const named: Record<string, string> = {
    Mouse0: "Left click", Mouse1: "Middle click", Mouse2: "Right click", Mouse3: "Mouse 4", Mouse4: "Mouse 5",
    Space: "Space", ArrowUp: "Up arrow", ArrowDown: "Down arrow", ArrowLeft: "Left arrow", ArrowRight: "Right arrow",
    ShiftLeft: "Left Shift", ShiftRight: "Right Shift", ControlLeft: "Left Ctrl", ControlRight: "Right Ctrl",
    AltLeft: "Left Alt", AltRight: "Right Alt", Enter: "Enter", Tab: "Tab", Backspace: "Backspace", CapsLock: "Caps Lock",
  };
  if (named[code]) return named[code];
  if (code.startsWith("Key")) return code.slice(3);
  if (code.startsWith("Digit")) return code.slice(5);
  if (code.startsWith("Numpad")) return "Num " + code.slice(6);
  return code;
}

/** Primary label of an action ("W", "Left click"), or both joined with "/". */
export function label(action: Action, both = false): string {
  const [a, b] = current[action];
  if (both && a && b) return `${keyLabel(a)} / ${keyLabel(b)}`;
  return keyLabel(a || b);
}
