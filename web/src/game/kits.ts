// Per-class combat data: stats, attack/skill tables and pose tables.
// `type` picks how the arena resolves an attack:
//   melee      - timed hit check in front of the attacker (hits every enemy in the arc)
//   projectile - flying bolts / arrows (count, spread, speed, size, style, pierce)
//   strike     - area hit at the target or self after `delay`, `repeat` times
//   buff       - self effect (ward absorbs hits, counter auto-parries and strikes back)
//   blink      - instant reposition (back / behind)

import { STATUS, type StatusKind } from "./status";

export type Vec3 = [number, number, number];
export interface Pose {
  torso: Vec3; head: Vec3; arm_r: Vec3; hand_r: Vec3; arm_l: Vec3; hand_l: Vec3;
  leg_l: Vec3; leg_r: Vec3; hips_y: number;
}

export interface Attack {
  id: string; type: string; wind: number; active: number; recover: number; dmg: number; guard: number;
  reach: number; lunge: number; knock: number; stun: number; heavy: boolean;
  pose_w: string; pose_s: string; next: string;
  speed: number; size: number; count: number; spread: number; style: string; pierce: boolean;
  at: string; delay: number; radius: number; repeat: number; interval: number;
  stagger: boolean; self_jump: number; mode: string; duration: number;
  cd: number; name: string; desc: string; element: string;
  /** Status effect left on hit (see status.ts): kind, duration (s) and power (dmg/s or multiplier). */
  effect: string; effect_t: number; effect_p: number;
}

export const STATS: Record<string, { hp: number; guard: number; move: number; walk: number; parry: number; jump: number }> = {
  knight: { hp: 2500, guard: 100, move: 3.2, walk: 2.6, parry: 0.16, jump: 7.0 },
  mage: { hp: 2100, guard: 80, move: 3.4, walk: 2.6, parry: 0.16, jump: 7.0 },
  assassin: { hp: 2000, guard: 60, move: 4.2, walk: 3.4, parry: 0.22, jump: 8.2 },
  greatsword: { hp: 2750, guard: 120, move: 2.9, walk: 2.3, parry: 0.14, jump: 6.5 },
  katana: { hp: 2200, guard: 80, move: 3.8, walk: 3.0, parry: 0.2, jump: 7.5 },
  bow: { hp: 2000, guard: 60, move: 3.6, walk: 2.6, parry: 0.16, jump: 7.5 },
  knuckles: { hp: 2300, guard: 90, move: 4.0, walk: 3.2, parry: 0.2, jump: 8.0 },
  kicks: { hp: 2300, guard: 85, move: 4.1, walk: 3.2, parry: 0.2, jump: 8.6 },
};

const DEFAULT: Omit<Attack, "id" | "element"> = {
  type: "melee", wind: 0.14, active: 0.08, recover: 0.3, dmg: 60, guard: 20,
  reach: 1.75, lunge: 0, knock: 2, stun: 0.32, heavy: false,
  pose_w: "l1_w", pose_s: "l1_s", next: "",
  speed: 15, size: 1, count: 1, spread: 0, style: "bolt", pierce: false,
  at: "target", delay: 0.4, radius: 1.5, repeat: 1, interval: 0.3,
  stagger: false, self_jump: 0, mode: "", duration: 0,
  cd: 0, name: "", desc: "",
  effect: "", effect_t: 0, effect_p: 0,
};

const a = (d: Partial<Attack>): Attack => ({ ...DEFAULT, id: "", element: "", ...d }) as Attack;

/** Normal attacks keyed l1.. plus "heavy" (charged), and skills keyed z/x/c. */
export function attacks(kit: string, element: string): Record<string, Attack> {
  const t: Record<string, Attack> = ({
    mage: () => mage(element),
    assassin: assassin,
    greatsword: greatsword,
    katana: katana,
    bow: bow,
    knuckles: knuckles,
    kicks: kicks,
  } as Record<string, () => Record<string, Attack>>)[kit]?.() ?? knight();
  t.v = bonusSkill(kit, element);
  for (const k of Object.keys(t)) {
    t[k].element = element;
    t[k].id = k;
  }
  const fx = ELEMENT_EFFECT[element];
  if (fx) for (const k of fx[3]) {
    const s = t[k];
    if (s && s.type !== "buff" && s.type !== "blink" && s.dmg > 0) { s.effect = fx[0]; s.effect_t = fx[1]; s.effect_p = fx[2]; }
  }
  return t;
}

/** Which skills carry each element's status effect: [kind, seconds, power, skill keys]. */
const ELEMENT_EFFECT: Record<string, [StatusKind, number, number, string[]]> = {
  fire: ["burn", 4, 30, ["z", "x", "c", "v"]],        // Ember
  flame: ["burn", 4, 25, ["c", "v"]],                 // Vesper: Blade Wave, Judgment
  light: ["weaken", 4, 0.8, ["c", "v"]],              // Aster: Blade Wave, Judgment
  electric: ["paralyze", 2.5, 0, ["x", "c", "v"]],    // Raven
  water: ["slow", 3, 0.6, ["z", "x", "c"]],           // Marina
  shadow: ["poison", 6, 10, ["x", "c", "v"]],         // Nyx: Shuriken Fan, Phantom Rush, Venom Fan
  moon: ["bleed", 4, 20, ["x", "c", "v"]],            // Kaede
  blood: ["bleed", 4, 22, ["x", "c"]],                // Ash: Arrow Rain, Hunter's Snare
  earth: ["slow", 2.5, 0.65, ["z", "c"]],             // Garrick: Ground Slam, Titan Cleave
};

/** Short stat lines for a skill: stun time and status effect, for tooltips and skill lists. */
export function skillTags(a: Attack): string[] {
  const out: string[] = [];
  if (a.type !== "buff" && a.type !== "blink" && a.dmg > 0 && a.stun >= 0.5) out.push(`Stun ${a.stun}s`);
  const info = STATUS[a.effect as StatusKind];
  if (info) out.push(info.text(a.effect_t, a.effect_p));
  return out;
}

/** Each kit's locked bonus skill ("v"): unlock it in the shop, then slot it into the loadout. */
function bonusSkill(kit: string, element: string): Attack {
  switch (kit) {
    case "mage":
      if (element === "fire") return a({ name: "Inferno Ring", desc: "A ring of fire erupts around you.", cd: 9, type: "strike", at: "self", wind: 0.15, recover: 0.45, dmg: 165, guard: 45, knock: 6, stun: 0.5, delay: 0.1, radius: 2.8, style: "explosion", pose_w: "mh_w", pose_s: "m3_s" });
      if (element === "electric") return a({ name: "Static Field", desc: "Three lightning bolts strike all around you.", cd: 10, type: "strike", at: "self", wind: 0.12, recover: 0.5, dmg: 75, guard: 22, knock: 2, stun: 0.5, delay: 0.15, radius: 2.2, repeat: 3, interval: 0.25, style: "lightning", pose_w: "mh_w", pose_s: "m3_s" });
      return a({ name: "Healing Rain", desc: "Restore 16% of your HP (25% in survival).", cd: 14, type: "buff", mode: "heal", duration: 0.25, wind: 0.2, recover: 0.4, pose_w: "mh_w", pose_s: "m3_s" });
    case "assassin":
      return a({ name: "Venom Fan", desc: "A wide spray of five poisoned blades.", cd: 7, type: "projectile", wind: 0.12, recover: 0.3, dmg: 42, guard: 12, knock: 1.2, stun: 0.3, speed: 24, count: 5, spread: 0.5, style: "shuriken", pose_w: "as1_w", pose_s: "as1_s" });
    case "greatsword":
      return a({ name: "Berserk", desc: "Deal 20% more damage for 6 seconds.", cd: 14, type: "buff", mode: "rage", duration: 6, wind: 0.2, recover: 0.4, pose_w: "charge", pose_s: "win" });
    case "katana":
      return a({ name: "Iaido Flash", desc: "An instant cross-arena draw cut.", cd: 8, wind: 0.08, active: 0.16, recover: 0.45, dmg: 200, guard: 50, reach: 2.2, lunge: 18, knock: 5, stun: 0.7, heavy: true, pose_w: "charge", pose_s: "heavy_s" });
    case "bow":
      return a({ name: "Piercing Volley", desc: "Five arrows that fly through every enemy in line.", cd: 9, type: "projectile", wind: 0.2, recover: 0.4, dmg: 55, guard: 14, knock: 2, stun: 0.3, speed: 32, count: 5, spread: 0.25, style: "arrow", pierce: true, pose_w: "bow_w", pose_s: "bow_s" });
    case "knuckles":
      return a({ name: "Iron Body", desc: "Shrug off every hit for 2.5 seconds.", cd: 13, type: "buff", mode: "ward", duration: 2.5, wind: 0.1, recover: 0.25, pose_w: "block", pose_s: "block" });
    case "kicks":
      return a({ name: "Dragon Ascent", desc: "A soaring rising kick that launches you skyward.", cd: 8, wind: 0.08, active: 0.12, recover: 0.4, dmg: 170, guard: 40, reach: 1.9, lunge: 3, knock: 5, stun: 0.7, stagger: true, self_jump: 8, pose_w: "kk4_w", pose_s: "fly_s" });
    default:
      return a({ name: "Judgment", desc: "A pillar of holy light crashes onto the enemy.", cd: 10, type: "strike", wind: 0.2, recover: 0.5, dmg: 220, guard: 60, knock: 5, stun: 0.7, heavy: true, delay: 0.5, radius: 1.6, style: "lightning", pose_w: "l3_w", pose_s: "l3_s" });
  }
}

function knight(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.14, recover: 0.24, dmg: 62, guard: 18, lunge: 2.4, next: "l2" }),
    l2: a({ wind: 0.12, recover: 0.26, dmg: 70, lunge: 2.2, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ wind: 0.2, active: 0.09, recover: 0.42, dmg: 112, guard: 30, reach: 1.85, lunge: 3, knock: 4.5, stun: 0.5, pose_w: "l3_w", pose_s: "l3_s" }),
    heavy: a({ wind: 0.12, active: 0.1, recover: 0.5, dmg: 190, guard: 55, reach: 2, lunge: 5, knock: 6, stun: 0.7, heavy: true, pose_w: "charge", pose_s: "heavy_s" }),
    z: a({ name: "Shield Bash", desc: "Ram the shield forward. Staggers and crushes guard.", cd: 5,
      wind: 0.12, recover: 0.35, dmg: 55, guard: 60, reach: 1.5, lunge: 4, knock: 3, stagger: true, stun: 1.0, pose_w: "block", pose_s: "bash" }),
    x: a({ name: "Rising Slash", desc: "Leap upward with a soaring cut.", cd: 6,
      wind: 0.1, active: 0.1, recover: 0.4, dmg: 115, guard: 30, reach: 1.9, lunge: 2, knock: 4, stun: 0.55, self_jump: 6.5, pose_w: "charge", pose_s: "rise" }),
    c: a({ name: "Blade Wave", desc: "Fling a crescent of light across the arena.", cd: 9,
      type: "projectile", wind: 0.22, active: 0.05, recover: 0.45, dmg: 140, guard: 40, knock: 5, stun: 0.6, heavy: true,
      speed: 17, size: 1.8, style: "wave", pierce: true, pose_w: "l3_w", pose_s: "l3_s" }),
  };
}

function mage(element: string): Record<string, Attack> {
  let speed = 15, mul = 1;
  if (element === "electric") { speed = 24; mul = 0.9; }
  else if (element === "water") speed = 13;
  const t: Record<string, Attack> = {
    l1: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.26, dmg: 55 * mul, guard: 15, knock: 1.6, stun: 0.28, speed, pose_w: "m1_w", pose_s: "m1_s", next: "l2" }),
    l2: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.28, dmg: 60 * mul, guard: 15, knock: 1.8, stun: 0.3, speed, pose_w: "m2_w", pose_s: "m2_s", next: "l3" }),
    l3: a({ type: "projectile", wind: 0.24, active: 0.05, recover: 0.42, dmg: 42 * mul, guard: 14, knock: 3, stun: 0.4, speed, count: 3, spread: 0.22, pose_w: "m3_w", pose_s: "m3_s" }),
  };
  if (element === "fire") {
    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.55, dmg: 210, guard: 60, knock: 6, stun: 0.7, heavy: true, delay: 0.5, radius: 1.6, style: "explosion", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Flame Burst", desc: "Erupt in flames, blasting anyone close away.", cd: 6, type: "strike", at: "self", wind: 0.12, recover: 0.4, dmg: 120, guard: 40, knock: 7, stun: 0.5, delay: 0.05, radius: 2.3, style: "explosion", pose_w: "mh_w", pose_s: "m3_s" });
    t.x = a({ name: "Fireball Volley", desc: "Hurl a fan of five fireballs.", cd: 7, type: "projectile", wind: 0.2, recover: 0.4, dmg: 40, guard: 12, knock: 2, speed: 16, count: 5, spread: 0.45, pose_w: "m3_w", pose_s: "m3_s" });
    t.c = a({ name: "Meteor", desc: "Call a meteor down on the enemy's position.", cd: 12, type: "strike", wind: 0.3, recover: 0.6, dmg: 290, guard: 80, knock: 8, stun: 0.9, heavy: true, delay: 0.9, radius: 2.1, style: "meteor", pose_w: "mh_w", pose_s: "mh_s" });
  } else if (element === "electric") {
    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.5, dmg: 185, guard: 55, knock: 4, stun: 0.8, heavy: true, delay: 0.35, radius: 1.3, style: "lightning", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Blink", desc: "Flash backward out of danger.", cd: 4, type: "blink", mode: "back", wind: 0.04, recover: 0.15, pose_w: "m1_w", pose_s: "m1_s" });
    t.x = a({ name: "Chain Lightning", desc: "A near-instant bolt that locks the target in place.", cd: 6, type: "projectile", wind: 0.14, recover: 0.35, dmg: 90, guard: 25, knock: 1, stun: 0.75, speed: 42, size: 1.3, pose_w: "m2_w", pose_s: "m2_s" });
    t.c = a({ name: "Thunderstorm", desc: "Three lightning strikes hunt the enemy.", cd: 12, type: "strike", wind: 0.3, recover: 0.6, dmg: 110, guard: 35, knock: 3, stun: 0.6, heavy: true, delay: 0.45, radius: 1.25, repeat: 3, interval: 0.35, style: "lightning", pose_w: "mh_w", pose_s: "mh_s" });
  } else {
    t.heavy = a({ type: "projectile", wind: 0.15, active: 0.05, recover: 0.55, dmg: 190, guard: 60, knock: 7, stun: 0.7, heavy: true, speed: 9, size: 2.4, pierce: true, pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Bubble Ward", desc: "A bubble that absorbs every hit for 2 seconds (4 in survival).", cd: 10, type: "buff", mode: "ward", duration: 4, wind: 0.1, recover: 0.25, pose_w: "mh_w", pose_s: "m3_s" });
    t.x = a({ name: "Tidal Ring", desc: "A ring of geysers bursts up around you.", cd: 7, type: "strike", at: "self", wind: 0.14, recover: 0.45, dmg: 105, guard: 35, knock: 7, stun: 0.5, delay: 0.1, radius: 2.7, style: "tide", pose_w: "mh_w", pose_s: "m3_s" });
    t.c = a({ name: "Ocean Requiem", desc: "Slam a colossal sphere of water onto the enemy.", cd: 12, type: "strike", wind: 0.35, recover: 0.6, dmg: 270, guard: 80, knock: 8, stun: 0.9, heavy: true, delay: 0.8, radius: 2.4, style: "requiem", pose_w: "mh_w", pose_s: "mh_s" });
  }
  return t;
}

function assassin(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.08, active: 0.06, recover: 0.16, dmg: 41, guard: 10, reach: 1.55, lunge: 3, knock: 1.2, stun: 0.26, pose_w: "as1_w", pose_s: "as1_s", next: "l2" }),
    l2: a({ wind: 0.08, active: 0.06, recover: 0.16, dmg: 41, guard: 10, reach: 1.55, lunge: 3, knock: 1.2, stun: 0.26, pose_w: "as2_w", pose_s: "as2_s", next: "l3" }),
    l3: a({ wind: 0.1, active: 0.06, recover: 0.18, dmg: 51, guard: 12, reach: 1.7, lunge: 4, knock: 1.5, stun: 0.28, pose_w: "as3_w", pose_s: "as3_s", next: "l4" }),
    l4: a({ wind: 0.16, active: 0.08, recover: 0.36, dmg: 86, guard: 22, reach: 1.7, lunge: 3, knock: 4, stun: 0.45, pose_w: "as4_w", pose_s: "as4_s" }),
    heavy: a({ wind: 0.12, active: 0.16, recover: 0.5, dmg: 170, guard: 45, reach: 2, lunge: 7, knock: 5, stun: 0.7, heavy: true, pose_w: "ash_w", pose_s: "ash_s" }),
    z: a({ name: "Smoke Step", desc: "Vanish and reappear behind the enemy.", cd: 5, type: "blink", mode: "behind", wind: 0.06, recover: 0.12, pose_w: "ash_w", pose_s: "idle" }),
    x: a({ name: "Shuriken Fan", desc: "Throw three spinning shuriken.", cd: 6, type: "projectile", wind: 0.12, recover: 0.3, dmg: 48, guard: 14, knock: 1.5, stun: 0.35, speed: 22, count: 3, spread: 0.3, style: "shuriken", pose_w: "as1_w", pose_s: "as1_s" }),
    c: a({ name: "Phantom Rush", desc: "A blinding dash that cuts through the enemy.", cd: 10, wind: 0.18, active: 0.18, recover: 0.55, dmg: 260, guard: 70, reach: 2.2, lunge: 16, knock: 6, stun: 0.9, heavy: true, stagger: true, pose_w: "ash_w", pose_s: "ash_s" }),
  };
}

function greatsword(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.26, active: 0.1, recover: 0.38, dmg: 110, guard: 32, reach: 2.2, lunge: 2, knock: 3, stun: 0.42, next: "l2" }),
    l2: a({ wind: 0.24, active: 0.1, recover: 0.4, dmg: 120, guard: 34, reach: 2.2, lunge: 2, knock: 3, stun: 0.42, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ wind: 0.36, active: 0.12, recover: 0.6, dmg: 190, guard: 50, reach: 2.3, lunge: 2.5, knock: 6, stun: 0.6, stagger: true, pose_w: "l3_w", pose_s: "l3_s" }),
    heavy: a({ wind: 0.18, active: 0.14, recover: 0.7, dmg: 320, guard: 80, reach: 2.5, lunge: 4, knock: 8, stun: 0.9, heavy: true, pose_w: "charge", pose_s: "heavy_s" }),
    z: a({ name: "Ground Slam", desc: "Smash the earth, knocking back everyone nearby.", cd: 6, type: "strike", at: "self", wind: 0.3, recover: 0.5, dmg: 150, guard: 50, knock: 7, stun: 0.6, delay: 0.05, radius: 2.6, style: "slam", pose_w: "l3_w", pose_s: "l3_s" }),
    x: a({ name: "Whirlwind", desc: "Spin with the blade out, hitting all around you four times.", cd: 7, type: "strike", at: "self", wind: 0.12, recover: 0.4, dmg: 60, guard: 20, knock: 2, stun: 0.3, delay: 0.05, radius: 2.1, repeat: 4, interval: 0.18, style: "spin", pose_w: "l1_w", pose_s: "heavy_s" }),
    c: a({ name: "Titan Cleave", desc: "A colossal downward cleave that splits the ground ahead.", cd: 12, type: "strike", wind: 0.4, recover: 0.7, dmg: 340, guard: 90, knock: 9, stun: 1.0, heavy: true, delay: 0.55, radius: 2.0, style: "cleave", pose_w: "l3_w", pose_s: "l3_s" }),
  };
}

function katana(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.1, active: 0.07, recover: 0.2, dmg: 64, guard: 18, reach: 1.85, lunge: 3, knock: 1.6, stun: 0.3, next: "l2" }),
    l2: a({ wind: 0.1, active: 0.07, recover: 0.2, dmg: 69, guard: 18, reach: 1.85, lunge: 3, knock: 1.6, stun: 0.3, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ wind: 0.14, active: 0.08, recover: 0.36, dmg: 110, guard: 30, reach: 1.95, lunge: 3.5, knock: 4, stun: 0.5, pose_w: "l3_w", pose_s: "l3_s" }),
    heavy: a({ wind: 0.16, active: 0.14, recover: 0.5, dmg: 230, guard: 55, reach: 2.2, lunge: 8, knock: 5, stun: 0.75, heavy: true, pose_w: "charge", pose_s: "heavy_s" }),
    z: a({ name: "Counter Stance", desc: "Brace for a moment; the next hit is parried and punished.", cd: 6, type: "buff", mode: "counter", duration: 0.9, wind: 0.04, recover: 0.9, pose_w: "block", pose_s: "block" }),
    x: a({ name: "Crescent Wind", desc: "A cutting gust that flies through enemies.", cd: 6, type: "projectile", wind: 0.14, recover: 0.35, dmg: 120, guard: 30, knock: 3, stun: 0.45, speed: 20, size: 1.4, style: "wave", pierce: true, pose_w: "l1_w", pose_s: "l1_s" }),
    c: a({ name: "Thousand Cuts", desc: "Seven blinding slashes rip through the target area.", cd: 11, type: "strike", wind: 0.2, recover: 0.6, dmg: 48, guard: 12, knock: 1, stun: 0.3, delay: 0.3, radius: 1.5, repeat: 7, interval: 0.07, style: "slashes", pose_w: "charge", pose_s: "heavy_s" }),
  };
}

function bow(): Record<string, Attack> {
  return {
    l1: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.22, dmg: 60, guard: 14, knock: 1.4, stun: 0.28, speed: 28, style: "arrow", pose_w: "bow_w", pose_s: "bow_s", next: "l2" }),
    l2: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.22, dmg: 62, guard: 14, knock: 1.4, stun: 0.28, speed: 28, style: "arrow", pose_w: "bow_w", pose_s: "bow_s", next: "l3" }),
    l3: a({ type: "projectile", wind: 0.22, active: 0.05, recover: 0.38, dmg: 46, guard: 12, knock: 2.5, stun: 0.35, speed: 28, count: 3, spread: 0.12, style: "arrow", pose_w: "bow_w", pose_s: "bow_s" }),
    heavy: a({ type: "projectile", wind: 0.1, active: 0.05, recover: 0.5, dmg: 260, guard: 60, knock: 6, stun: 0.7, heavy: true, speed: 42, size: 1.7, style: "arrow", pierce: true, pose_w: "bow_w", pose_s: "bow_s" }),
    z: a({ name: "Leap Back", desc: "Spring away to open distance.", cd: 4, type: "blink", mode: "back", wind: 0.04, recover: 0.12, pose_w: "jump", pose_s: "jump" }),
    x: a({ name: "Arrow Rain", desc: "A volley falls on the target area three times.", cd: 8, type: "strike", wind: 0.22, recover: 0.4, dmg: 80, guard: 20, knock: 2, stun: 0.35, delay: 0.7, radius: 1.8, repeat: 3, interval: 0.25, style: "arrows", pose_w: "rain_w", pose_s: "rain_s" }),
    c: a({ name: "Hunter's Snare", desc: "A barbed arrow that pins the target in place.", cd: 10, type: "projectile", wind: 0.2, recover: 0.4, dmg: 100, guard: 30, knock: 0.5, stun: 1.6, stagger: true, speed: 32, size: 1.3, style: "arrow", pose_w: "bow_w", pose_s: "bow_s" }),
  };
}

function knuckles(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.06, active: 0.05, recover: 0.12, dmg: 40, guard: 10, reach: 1.35, lunge: 3, knock: 1, stun: 0.24, pose_w: "k1_w", pose_s: "k1_s", next: "l2" }),
    l2: a({ wind: 0.06, active: 0.05, recover: 0.12, dmg: 40, guard: 10, reach: 1.35, lunge: 3, knock: 1, stun: 0.24, pose_w: "k2_w", pose_s: "k2_s", next: "l3" }),
    l3: a({ wind: 0.09, active: 0.06, recover: 0.16, dmg: 55, guard: 14, reach: 1.4, lunge: 3, knock: 1.4, stun: 0.28, pose_w: "k3_w", pose_s: "k3_s", next: "l4" }),
    l4: a({ wind: 0.1, active: 0.06, recover: 0.18, dmg: 60, guard: 16, reach: 1.4, lunge: 2.5, knock: 1.6, stun: 0.3, pose_w: "k4_w", pose_s: "k4_s", next: "l5" }),
    l5: a({ wind: 0.14, active: 0.08, recover: 0.34, dmg: 95, guard: 26, reach: 1.5, lunge: 4, knock: 4, stun: 0.45, pose_w: "k5_w", pose_s: "k5_s" }),
    heavy: a({ wind: 0.14, active: 0.12, recover: 0.5, dmg: 220, guard: 55, reach: 1.6, lunge: 3, knock: 6, stun: 0.8, heavy: true, self_jump: 5, pose_w: "kh_w", pose_s: "kh_s" }),
    z: a({ name: "Rush", desc: "Barrel forward with a flurry that staggers.", cd: 5, wind: 0.08, active: 0.2, recover: 0.4, dmg: 120, guard: 35, reach: 1.6, lunge: 14, knock: 3, stun: 0.7, stagger: true, pose_w: "k5_w", pose_s: "k5_s" }),
    x: a({ name: "Shockwave Punch", desc: "Punch the air so hard it flies.", cd: 6, type: "projectile", wind: 0.14, recover: 0.35, dmg: 110, guard: 30, knock: 5, stun: 0.5, speed: 18, size: 1.3, style: "shock", pose_w: "k1_w", pose_s: "k1_s" }),
    c: a({ name: "Meteor Fist", desc: "Leap at the enemy and smash the ground on landing, cratering everything nearby.", cd: 11, type: "strike", at: "self", mode: "leap", self_jump: 9, wind: 0.22, recover: 0.6, dmg: 300, guard: 80, knock: 8, stun: 0.9, heavy: true, delay: 0.02, radius: 2.5, style: "slam", pose_w: "slam_w", pose_s: "slam_s" }),
  };
}

function kicks(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.08, active: 0.06, recover: 0.16, dmg: 46, guard: 12, reach: 1.65, lunge: 3, knock: 1.2, stun: 0.26, pose_w: "kk1_w", pose_s: "kk1_s", next: "l2" }),
    l2: a({ wind: 0.1, active: 0.07, recover: 0.18, dmg: 56, guard: 14, reach: 1.75, lunge: 3, knock: 1.6, stun: 0.28, pose_w: "kk2_w", pose_s: "kk2_s", next: "l3" }),
    l3: a({ wind: 0.12, active: 0.08, recover: 0.2, dmg: 72, guard: 18, reach: 1.85, lunge: 3.5, knock: 2.2, stun: 0.32, pose_w: "kk3_w", pose_s: "kk3_s", next: "l4" }),
    l4: a({ wind: 0.18, active: 0.08, recover: 0.38, dmg: 105, guard: 30, reach: 1.8, lunge: 2.5, knock: 4.5, stun: 0.5, stagger: true, pose_w: "kk4_w", pose_s: "kk4_s" }),
    heavy: a({ wind: 0.12, active: 0.16, recover: 0.5, dmg: 230, guard: 55, reach: 2.0, lunge: 7, knock: 6.5, stun: 0.8, heavy: true, self_jump: 4, pose_w: "charge", pose_s: "fly_s" }),
    z: a({ name: "Cyclone Kick", desc: "A spinning kick that hits everyone around you three times.", cd: 6, type: "strike", at: "self", wind: 0.08, recover: 0.4, dmg: 65, guard: 20, knock: 3, stun: 0.3, delay: 0.05, radius: 2.0, repeat: 3, interval: 0.15, style: "spin", pose_w: "kk3_w", pose_s: "kk3_s" }),
    x: a({ name: "Crescent Gale", desc: "A kick so fast it launches a cutting wind across the arena.", cd: 6, type: "projectile", wind: 0.14, recover: 0.35, dmg: 110, guard: 30, knock: 3, stun: 0.45, speed: 20, size: 1.4, style: "wave", pierce: true, pose_w: "kk2_w", pose_s: "kk2_s" }),
    c: a({ name: "Hundred Kicks", desc: "Blitz the target with a storm of eight rapid kicks.", cd: 10, type: "strike", wind: 0.15, recover: 0.6, dmg: 40, guard: 10, knock: 0.8, stun: 0.3, delay: 0.2, radius: 1.5, repeat: 8, interval: 0.06, style: "slashes", pose_w: "kk1_w", pose_s: "kk1_s" }),
  };
}

// --- poses ----------------------------------------------------------------------
// Joint rotations in radians. arm x < 0 raises the arm forward; YXZ order, so y then yaws it.

const P = (torso: Vec3, head: Vec3, arm_r: Vec3, hand_r: Vec3, arm_l: Vec3, hand_l: Vec3, leg_l: Vec3, leg_r: Vec3, hips_y: number): Pose =>
  ({ torso, head, arm_r, hand_r, arm_l, hand_l, leg_l, leg_r, hips_y });

const COMMON: Record<string, Pose> = {
  hit: P([-0.3, 0.2, 0.1], [-0.35, 0, 0], [-0.2, 0, -0.7], [0.4, 0, 0], [-0.2, 0, 0.7], [0, 0, -1.3], [0.1, 0, 0.06], [-0.2, 0, -0.06], -0.03),
  stagger: P([-0.45, 0.35, 0.15], [-0.4, 0, 0.1], [0.1, 0, -0.9], [1.0, 0, 0], [0.1, 0, 0.9], [0, 0, -1.5], [0.25, 0, 0.08], [-0.35, 0, -0.08], -0.1),
  clash: P([-0.25, -0.2, 0], [-0.15, 0.2, 0], [-1.9, -0.3, -0.3], [0.3, 0, 0], [-0.4, -0.2, 0.6], [0, 0, -1.2], [-0.1, 0, 0.06], [0.4, 0, -0.06], -0.08),
  win: P([0, 0, 0], [0.1, 0, 0], [-2.9, 0, -0.2], [0, 0, 0], [-0.1, 0, 0.4], [0, 0, -1.5], [-0.1, 0, 0.04], [0.1, 0, -0.04], 0),
  jump: P([0.15, 0, 0], [0.1, 0, 0], [-0.9, 0, -0.6], [0.5, 0, 0], [-0.9, 0, 0.6], [0, 0, -0.8], [-0.95, 0, 0.05], [-0.2, 0, -0.05], 0),
  down: P([-0.6, 0, 0], [-0.4, 0, 0], [0.2, 0, -1.2], [0.5, 0, 0], [0.2, 0, 1.2], [0, 0, -1.4], [-0.3, 0, 0.1], [0.2, 0, -0.1], -0.2),
};

const KNIGHT: Record<string, Pose> = {
  idle: P([0.08, -0.35, 0], [0, 0.3, 0], [-0.55, -0.25, -0.25], [-0.5, 0, 0], [-0.75, -0.35, 0.2], [0, 0, -1.1], [-0.3, 0, 0.06], [0.3, 0, -0.06], -0.04),
  block: P([0.05, -0.1, 0], [0.05, 0.1, 0], [-0.3, 0, -0.35], [0.2, 0, 0], [-1.45, -0.6, 0], [0, 0, 0], [-0.4, 0, 0.08], [0.35, 0, -0.08], -0.08),
  bash: P([0.25, 0.25, 0], [0, -0.2, 0], [-0.3, 0, -0.45], [0.2, 0, 0], [-1.55, -0.1, 0], [0, 0, 0], [-0.6, 0, 0.08], [0.5, 0, -0.08], -0.14),
  rise: P([-0.2, 0.3, 0], [-0.2, -0.2, 0], [-2.8, 0.3, -0.2], [0.5, 0, 0], [-0.6, -0.3, 0.6], [0, 0, -1.2], [-0.8, 0, 0.06], [0.2, 0, -0.06], 0),
  charge: P([0.15, -1.0, 0], [0, 0.9, 0], [-0.7, -1.5, -0.3], [1.1, 0, 0], [-0.9, 0.4, 0.3], [0, 0, -1.0], [-0.45, 0, 0.1], [0.45, 0, -0.1], -0.14),
  heavy_s: P([0.25, 0.9, 0], [0, -0.7, 0], [-1.5, 1.3, 0], [1.3, 0, 0], [-0.4, -0.3, 0.6], [0, 0, -1.2], [-0.6, 0, 0.1], [0.5, 0, -0.1], -0.16),
  l1_w: P([0.05, -0.8, 0], [0, 0.7, 0], [-1.4, -1.2, 0], [1.3, 0, 0], [-0.8, -0.2, 0.3], [0, 0, -1.0], [-0.35, 0, 0.06], [0.3, 0, -0.06], -0.06),
  l1_s: P([0.12, 0.6, 0], [0, -0.5, 0], [-1.45, 1.0, 0], [1.3, 0, 0], [-0.5, -0.5, 0.4], [0, 0, -1.2], [-0.45, 0, 0.06], [0.35, 0, -0.06], -0.1),
  l2_w: P([0.05, 0.6, 0], [0, -0.5, 0], [-1.5, 1.1, 0], [1.3, 0, 0.3], [-0.5, -0.5, 0.4], [0, 0, -1.2], [-0.4, 0, 0.06], [0.3, 0, -0.06], -0.08),
  l2_s: P([0.1, -0.7, 0], [0, 0.6, 0], [-1.7, -1.1, 0], [1.3, 0, 0.3], [-0.8, -0.2, 0.3], [0, 0, -1.0], [-0.45, 0, 0.06], [0.35, 0, -0.06], -0.1),
  l3_w: P([-0.1, -0.2, 0], [0.1, 0.2, 0], [-2.9, 0, -0.1], [0.6, 0, 0], [-1.0, 0, 0.4], [0, 0, -1.0], [-0.3, 0, 0.06], [0.3, 0, -0.06], -0.02),
  l3_s: P([0.4, -0.1, 0], [-0.2, 0, 0], [-0.9, 0, -0.05], [1.2, 0, 0], [-0.6, -0.3, 0.5], [0, 0, -1.2], [-0.6, 0, 0.08], [0.5, 0, -0.08], -0.18),
};

/** Two-handed versions of the knight swings: the left hand follows the sword hand onto the hilt. */
function twoHanded(src: Record<string, Pose>): Record<string, Pose> {
  const out: Record<string, Pose> = {};
  for (const [k, p] of Object.entries(src)) {
    out[k] = { ...p, arm_l: [p.arm_r[0], p.arm_r[1] + 0.4, 0.1], hand_l: [p.hand_r[0], 0, 0] };
  }
  out.block = P([0.05, -0.2, 0], [0, 0.2, 0], [-1.25, 0.35, -0.1], [-1.3, 0, 0], [-1.25, -0.05, 0.1], [-1.3, 0, 0], [-0.4, 0, 0.08], [0.35, 0, -0.08], -0.08);
  out.idle = P([0.08, -0.3, 0], [0, 0.25, 0], [-0.8, 0.2, -0.2], [-0.6, 0, 0], [-0.8, 0.6, 0.1], [-0.6, 0, 0], [-0.3, 0, 0.06], [0.3, 0, -0.06], -0.06);
  return out;
}

// Staff in the right hand; hand_r x tilts the staff so it stays upright as the arm rises.
const MAGE: Record<string, Pose> = {
  idle: P([0.05, -0.15, 0], [0, 0.12, 0], [-0.35, 0, -0.3], [0.45, 0, 0.3], [-0.5, -0.3, 0.45], [0, 0, -0.6], [-0.15, 0, 0.05], [0.15, 0, -0.05], -0.02),
  block: P([0, -0.1, 0], [0, 0.1, 0], [-0.35, 0, -0.35], [0.5, 0, 0.3], [-1.5, -0.45, 0], [0, 0, 0], [-0.3, 0, 0.06], [0.3, 0, -0.06], -0.06),
  m1_w: P([0, 0.3, 0], [0, -0.2, 0], [-0.5, 0, -0.3], [0.6, 0, 0.3], [-1.1, 0.5, 0.5], [0, 0, -0.6], [-0.2, 0, 0.05], [0.2, 0, -0.05], -0.04),
  m1_s: P([0.05, -0.35, 0], [0, 0.3, 0], [-0.5, 0, -0.3], [0.6, 0, 0.3], [-1.55, -0.35, 0], [0, 0, 0], [-0.35, 0, 0.05], [0.3, 0, -0.05], -0.06),
  m2_w: P([0, -0.4, 0], [0, 0.35, 0], [-0.6, -0.4, -0.35], [0.6, 0, 0.3], [-0.6, -0.3, 0.5], [0, 0, -0.6], [-0.2, 0, 0.05], [0.2, 0, -0.05], -0.04),
  m2_s: P([0.08, 0.35, 0], [0, -0.3, 0], [-1.2, 0.15, -0.1], [1.3, 0, 0], [-0.5, -0.3, 0.6], [0, 0, -0.6], [-0.4, 0, 0.05], [0.35, 0, -0.05], -0.08),
  m3_w: P([-0.1, 0, 0], [-0.1, 0, 0], [-2.0, 0, -0.2], [2.0, 0, 0], [-2.2, 0, 0.3], [0, 0, -0.4], [-0.2, 0, 0.05], [0.2, 0, -0.05], -0.02),
  m3_s: P([0.2, 0, 0], [0, 0, 0], [-1.4, 0, -0.1], [1.4, 0, 0], [-1.5, 0, 0.1], [0, 0, 0], [-0.45, 0, 0.05], [0.4, 0, -0.05], -0.1),
  mh_w: P([-0.12, 0, 0], [-0.2, 0, 0], [-2.9, 0, -0.15], [2.9, 0, 0], [-1.2, -0.5, 0.6], [0, 0, -0.4], [-0.3, 0, 0.08], [0.3, 0, -0.08], -0.05),
  mh_s: P([0.22, 0, 0], [0, 0, 0], [-1.4, 0, -0.05], [1.4, 0, 0], [-0.6, 0, 0.7], [0, 0, -0.8], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.12),
};

const ASSASSIN: Record<string, Pose> = {
  idle: P([0.25, -0.3, 0], [-0.15, 0.3, 0], [-0.9, -0.3, -0.3], [0.2, 0, 0], [-0.8, 0.5, 0.35], [0.2, 0, 0], [-0.5, 0, 0.1], [0.45, 0, -0.1], -0.12),
  block: P([0.1, 0, 0], [0, 0, 0], [-1.4, 0.55, 0], [1.0, 0, 0.6], [-1.4, -0.55, 0], [1.0, 0, -0.6], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.1),
  as1_w: P([0.2, -0.7, 0], [-0.1, 0.6, 0], [-1.3, -1.2, 0], [1.3, 0, 0], [-0.8, 0.5, 0.35], [0.2, 0, 0], [-0.5, 0, 0.1], [0.45, 0, -0.1], -0.12),
  as1_s: P([0.25, 0.5, 0], [-0.1, -0.4, 0], [-1.35, 0.9, 0], [1.3, 0, 0], [-0.8, 0.5, 0.35], [0.2, 0, 0], [-0.55, 0, 0.1], [0.5, 0, -0.1], -0.14),
  as2_w: P([0.2, 0.6, 0], [-0.1, -0.5, 0], [-0.9, -0.3, -0.3], [0.2, 0, 0], [-1.3, 1.2, 0], [1.3, 0, 0], [-0.5, 0, 0.1], [0.45, 0, -0.1], -0.12),
  as2_s: P([0.25, -0.5, 0], [-0.1, 0.4, 0], [-0.9, -0.3, -0.3], [0.2, 0, 0], [-1.35, -0.9, 0], [1.3, 0, 0], [-0.55, 0, 0.1], [0.5, 0, -0.1], -0.14),
  as3_w: P([0.1, -0.5, 0], [-0.05, 0.45, 0], [-0.9, -0.2, -0.4], [1.4, 0, 0], [-0.7, 0.5, 0.4], [0.2, 0, 0], [-0.45, 0, 0.1], [0.45, 0, -0.1], -0.12),
  as3_s: P([0.3, 0.3, 0], [-0.15, -0.25, 0], [-1.6, 0.1, 0], [1.5, 0, 0], [-0.6, 0.6, 0.5], [0.2, 0, 0], [-0.7, 0, 0.1], [0.6, 0, -0.1], -0.2),
  as4_w: P([0, 0, 0], [0, 0, 0], [-1.3, -1.4, 0], [1.3, 0, 0], [-1.3, 1.4, 0], [1.3, 0, 0], [-0.4, 0, 0.1], [0.4, 0, -0.1], -0.1),
  as4_s: P([0.3, 0, 0], [-0.1, 0, 0], [-1.4, 0.9, 0], [1.3, 0, 0], [-1.4, -0.9, 0], [1.3, 0, 0], [-0.6, 0, 0.1], [0.55, 0, -0.1], -0.18),
  ash_w: P([0.5, -0.2, 0], [-0.35, 0.2, 0], [-0.4, -0.8, -0.6], [1.2, 0, 0], [-0.4, 0.8, 0.6], [1.2, 0, 0], [-0.7, 0, 0.12], [0.6, 0, -0.12], -0.25),
  ash_s: P([0.4, 0, 0], [-0.25, 0, 0], [-1.5, 0.6, 0], [1.4, 0, 0], [-1.5, -0.6, 0], [1.4, 0, 0], [-0.8, 0, 0.12], [0.7, 0, -0.12], -0.22),
};

// Bow in the left hand. The bow arm points at the target; the right hand draws the string.
const BOW: Record<string, Pose> = {
  idle: P([0.05, -0.2, 0], [0, 0.2, 0], [-0.35, 0, -0.3], [0, 0, 0], [-0.55, -0.2, 0.35], [0, 0, 0], [-0.2, 0, 0.06], [0.2, 0, -0.06], -0.03),
  block: P([0.1, 0, 0], [0, 0, 0], [-1.4, 0.55, 0], [0, 0, 0], [-1.45, -0.4, 0], [0, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.1),
  bow_w: P([0, -0.8, 0], [0, 0.75, 0], [-1.55, 0.75, -0.2], [0, 0, 0], [-1.55, -0.2, 0], [0, 0, 0], [-0.35, 0, 0.08], [0.35, 0, -0.08], -0.06),
  bow_s: P([0, -0.8, 0], [0, 0.75, 0], [-1.25, -0.3, -0.7], [0, 0, 0], [-1.55, -0.2, 0], [0, 0, 0], [-0.35, 0, 0.08], [0.35, 0, -0.08], -0.06),
  charge: P([0, -0.85, 0], [0, 0.8, 0], [-1.5, 1.0, -0.2], [0, 0, 0], [-1.55, -0.2, 0], [0, 0, 0], [-0.45, 0, 0.1], [0.45, 0, -0.1], -0.1),
  rain_w: P([-0.25, -0.4, 0], [-0.4, 0.4, 0], [-2.2, 0.5, -0.2], [0, 0, 0], [-2.4, -0.2, 0], [0, 0, 0], [-0.3, 0, 0.08], [0.3, 0, -0.08], -0.04),
  rain_s: P([-0.25, -0.4, 0], [-0.4, 0.4, 0], [-1.8, -0.4, -0.7], [0, 0, 0], [-2.4, -0.2, 0], [0, 0, 0], [-0.3, 0, 0.08], [0.3, 0, -0.08], -0.04),
};

// Boxing guard; jabs alternate hands, a hook, an uppercut and a double straight.
const KNUCKLES: Record<string, Pose> = {
  idle: P([0.15, -0.3, 0], [-0.1, 0.3, 0], [-1.1, 0.45, -0.25], [0.6, 0, 0], [-1.15, -0.25, 0.25], [0.6, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.1),
  block: P([0.25, 0, 0], [0.15, 0, 0], [-1.75, 0.55, 0], [0.8, 0, 0], [-1.75, -0.55, 0], [0.8, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.14),
  k1_w: P([0.1, -0.45, 0], [-0.1, 0.4, 0], [-0.9, 0.2, -0.3], [0.6, 0, 0], [-1.15, -0.25, 0.25], [0.6, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.1),
  k1_s: P([0.2, 0.35, 0], [-0.1, -0.3, 0], [-1.6, 0.2, 0], [0, 0, 0], [-1.15, -0.25, 0.25], [0.6, 0, 0], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.12),
  k2_w: P([0.1, 0.3, 0], [-0.1, -0.25, 0], [-1.1, 0.45, -0.25], [0.6, 0, 0], [-0.9, -0.2, 0.3], [0.6, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.1),
  k2_s: P([0.2, -0.45, 0], [-0.1, 0.4, 0], [-1.1, 0.45, -0.25], [0.6, 0, 0], [-1.6, -0.2, 0], [0, 0, 0], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.12),
  k3_w: P([0.1, -0.7, 0], [-0.1, 0.6, 0], [-1.35, -1.2, 0], [0.6, 0, 0], [-1.15, -0.25, 0.25], [0.6, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.12),
  k3_s: P([0.2, 0.6, 0], [-0.1, -0.5, 0], [-1.45, 0.8, 0], [0.6, 0, 0], [-1.15, -0.25, 0.25], [0.6, 0, 0], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.14),
  k4_w: P([0.35, 0.2, 0], [0, -0.2, 0], [-1.1, 0.45, -0.25], [0.6, 0, 0], [-0.3, -0.1, 0.3], [1.2, 0, 0], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.2),
  k4_s: P([-0.15, -0.2, 0], [-0.2, 0.2, 0], [-1.1, 0.45, -0.25], [0.6, 0, 0], [-2.6, -0.1, 0.1], [0.2, 0, 0], [-0.45, 0, 0.08], [0.4, 0, -0.08], -0.04),
  k5_w: P([0.05, 0, 0], [0, 0, 0], [-0.8, 0.1, -0.35], [0.8, 0, 0], [-0.8, -0.1, 0.35], [0.8, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.14),
  k5_s: P([0.35, 0, 0], [-0.2, 0, 0], [-1.6, 0.15, 0], [0, 0, 0], [-1.6, -0.15, 0], [0, 0, 0], [-0.7, 0, 0.08], [0.6, 0, -0.08], -0.2),
  kh_w: P([0.5, -0.3, 0], [-0.3, 0.3, 0], [-0.3, -0.2, -0.35], [1.2, 0, 0], [-1.2, -0.25, 0.25], [0.6, 0, 0], [-0.7, 0, 0.1], [0.6, 0, -0.1], -0.28),
  kh_s: P([-0.25, 0.2, 0], [-0.35, -0.1, 0], [-2.9, 0.1, -0.1], [0, 0, 0], [-0.8, -0.3, 0.5], [0.6, 0, 0], [-0.6, 0, 0.08], [0.1, 0, -0.08], 0),
  // Meteor Fist: deep crouch, airborne with both fists overhead, then fists driven into the ground.
  slam_w: P([0.55, 0, 0], [-0.35, 0, 0], [0.5, 0.2, -0.3], [0.6, 0, 0], [0.5, -0.2, 0.3], [0.6, 0, 0], [-0.9, 0, 0.15], [-0.9, 0, -0.15], -0.32),
  slam_air: P([-0.2, 0, 0], [-0.25, 0, 0], [-2.95, 0.15, 0], [0.3, 0, 0], [-2.95, -0.15, 0], [0.3, 0, 0], [-1.1, 0, 0.1], [-0.4, 0, -0.1], 0),
  slam_s: P([0.85, 0, 0], [-0.55, 0, 0], [-0.55, 0.25, 0], [0.1, 0, 0], [-0.55, -0.25, 0], [0.1, 0, 0], [-1.0, 0, 0.2], [0.2, 0, -0.2], -0.42),
};

// Martial artist: arms stay in a high guard while the legs do the work. A leg's x < 0 lifts it
// forward; y (applied after) sweeps the raised leg sideways, for roundhouse arcs.
const GUARD_R: Vec3 = [-1.0, 0.4, -0.3];
const GUARD_L: Vec3 = [-1.1, -0.3, 0.3];
const KICKS: Record<string, Pose> = {
  idle: P([0.1, -0.35, 0], [-0.05, 0.3, 0], GUARD_R, [0.6, 0, 0], GUARD_L, [0.6, 0, 0], [-0.35, 0, 0.1], [0.35, 0, -0.1], -0.08),
  block: P([0.2, 0, 0], [0.1, 0, 0], [-1.7, 0.55, 0], [0.8, 0, 0], [-1.7, -0.55, 0], [0.8, 0, 0], [-1.3, 0, 0.05], [0.25, 0, -0.08], -0.06),
  kk1_w: P([0, -0.2, 0], [0, 0.2, 0], GUARD_R, [0.6, 0, 0], GUARD_L, [0.6, 0, 0], [0.15, 0, 0.05], [-1.6, 0, -0.05], -0.04),
  kk1_s: P([-0.3, -0.2, 0], [0.15, 0.2, 0], [-0.7, 0.2, -0.6], [0.6, 0, 0], GUARD_L, [0.6, 0, 0], [0.2, 0, 0.05], [-1.62, 0, 0], -0.1),
  kk2_w: P([0, -0.6, 0], [0, 0.6, 0], GUARD_R, [0.6, 0, 0], GUARD_L, [0.6, 0, 0], [-1.3, 1.1, 0], [0.15, 0, -0.05], -0.06),
  kk2_s: P([-0.15, 0.6, 0], [0, -0.5, 0], [-0.6, 0.2, -0.7], [0.6, 0, 0], GUARD_L, [0.6, 0, 0], [-1.5, -0.6, 0], [0.15, 0, -0.05], -0.08),
  kk3_w: P([0, 0.8, 0], [0, -0.7, 0], GUARD_R, [0.6, 0, 0], GUARD_L, [0.6, 0, 0], [0.1, 0, 0.05], [-1.4, -1.2, 0], -0.08),
  kk3_s: P([-0.2, -0.9, 0], [0, 0.8, 0], GUARD_R, [0.6, 0, 0], [-0.6, -0.2, 0.7], [0.6, 0, 0], [0.15, 0, 0.05], [-1.85, 0.6, 0], -0.1),
  kk4_w: P([-0.3, 0, 0], [-0.2, 0, 0], GUARD_R, [0.6, 0, 0], GUARD_L, [0.6, 0, 0], [-2.6, 0.15, 0], [0.2, 0, -0.05], -0.02),
  kk4_s: P([0.35, 0, 0], [-0.2, 0, 0], [-0.6, 0, -0.6], [0.6, 0, 0], [-0.6, 0, 0.6], [0.6, 0, 0], [-0.55, 0, 0.05], [0.3, 0, -0.05], -0.2),
  charge: P([0.45, -0.3, 0], [-0.3, 0.3, 0], [-0.4, -0.3, -0.5], [0.6, 0, 0], [-0.4, 0.3, 0.5], [0.6, 0, 0], [-0.75, 0, 0.1], [0.55, 0, -0.1], -0.28),
  fly_s: P([-0.35, 0, 0], [0.2, 0, 0], [-0.5, 0, -1.0], [0.6, 0, 0], [-0.5, 0, 1.0], [0.6, 0, 0], [-1.3, 0, 0.05], [-1.6, 0, -0.05], 0),
};

const TABLES: Record<string, Record<string, Pose>> = {
  knight: KNIGHT,
  mage: MAGE,
  assassin: ASSASSIN,
  greatsword: twoHanded(KNIGHT),
  katana: twoHanded(KNIGHT),
  bow: BOW,
  knuckles: KNUCKLES,
  kicks: KICKS,
};

export function poses(kit: string): Record<string, Pose> {
  const t = { ...COMMON, ...(TABLES[kit] ?? KNIGHT) };
  if (!t.charge) t.charge = t.mh_w ?? t.ash_w ?? KNIGHT.charge;
  return t;
}
