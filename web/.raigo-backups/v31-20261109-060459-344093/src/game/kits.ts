// ROXY_V7_5PCT_LIGHT_CHARGED_BIRD_NO_WIND_20261108: Roxy-only 5% light/charged/bird buff.
// AI_ROOK_NESA_KIRA_MERGED_V1_20261108
// BALANCE_KIRA_KAEDE_PATTERN_AI_AIR_ICON_20261107_V1
// AI_EFFECTIVE_RANGE_KAIZEN_AIR_HOOK_20261107_V1
// ZAREK_ARC_FLASH_CPU_SPECTATOR_COOLDOWNS_20261107_V1
// ASTER_WEAKEN_50S_5_STACKS_V1_20261107
// MARINA_RAVEN_ZAREK_BOB_ABILITIES_20261107_V1
// FIGHT_ROYALE_BULLET_SWORDPLAY_GARRICK_RESOLVE_V1
// FIGHT_ROYALE_KAIZEN_MOBILE_SPIN_V8
// FIGHT_ROYALE_GARRICK_BOB_KAIZEN_ROOK_V7
// FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V2
// NESA_HEART_SMASH_V4
// FIGHT_ROYALE_ZAREK_EFFECTIVE_RANGE_NERF_V1
// CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06
// GARRICK_RANGE_WALK_V2
// SWORD_AND_CYCLONE_V1
// Per-class combat data: stats, attack/skill tables and pose tables.
// `type` picks how the arena resolves an attack:
//   melee      - timed hit check in front of the attacker (hits every enemy in the arc)
//   projectile - flying bolts / arrows (count, spread, speed, size, style, pierce)
//   strike     - area hit at the target or self after `delay`, `repeat` times
//   buff       - self effect (ward absorbs hits, counter auto-parries and strikes back)
//   blink      - instant reposition (back / behind)
//   phantom    - teleport behind the target and strike, `repeat` times `interval` apart
//   lob        - a bomb thrown in an arc (lands at the target after `delay` s) that explodes in
//                `radius` on landing or on hitting someone; `repeat` > 1 splits into a cluster
//   mine       - planted at the feet; arms after 0.5 s and blows up when an enemy steps on it
//   barrel     - a powder keg set down in front; press the skill again to detonate it (an enemy
//                hitting the keg sets it off too). The cooldown starts when it explodes.
// A skill key with an "_air" twin (e.g. z_air) uses the twin when cast in the air.
// mode "dive": dive from the air to the ground (`speed` down, up to `lunge` toward the target)
// and the strike lands where the fighter hits the ground.

import { STATUS, type StatusKind } from "./status";

export type Vec3 = [number, number, number];
export interface Pose {
  torso: Vec3; head: Vec3; arm_r: Vec3; hand_r: Vec3; arm_l: Vec3; hand_l: Vec3;
  leg_l: Vec3; leg_r: Vec3; hips_y: number;
  /** Extra knee bend [left, right] in radians (kick chamber / recoil); VRoid legs only. */
  knee?: [number, number];
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
  /** Can be blocked but never parried (or countered). */
  no_parry: boolean;
  /** If this attack is parried, the attacker is stunned this many seconds (a weakness). */
  parry_stun: number;
  // ZEPHYR_DRAGON_VARIANTS_V19: only populated for Zephyr's resolved attacks.
  hits?: number;
  dragonPull?: number; dragonCounterPull?: number; dragonSidestep?: number;
  dragonCounterDamage?: number; dragonArmor?: boolean; dragonBehind?: boolean; dragonArcCos?: number;
  dragonRhythmOnHit?: boolean; dragonStep?: number; dragonLaunch?: number;
  dragonEvenDmg?: number; dragonOddDmg?: number; dragonLastDmg?: number;
  dragonLastGuard?: number; dragonLastKnock?: number; dragonLastStun?: number;
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
  wind: { hp: 2200, guard: 80, move: 4.1, walk: 3.3, parry: 0.2, jump: 8.4 },
  sickle: { hp: 1950, guard: 62, move: 4.5, walk: 3.55, parry: 0.20, jump: 8.2 },
  glaive: { hp: 2250, guard: 88, move: 4.0, walk: 3.15, parry: 0.19, jump: 7.7 },
  // ZEPHYR_DRAGON_DANCER_V1
  // ZEPHYR_FULL_BALANCE_RHYTHM_V25: 2225 * 1.20 = 2670 HP, unchanged guard.
  tristaff: { hp: 2670, guard: 82, move: 3.90, walk: 3.05, parry: 0.205, jump: 7.9 },
  bomb: { hp: 2100, guard: 70, move: 3.5, walk: 2.8, parry: 0.16, jump: 7.0 },
  chainblade: { hp: 2450, guard: 100, move: 3.55, walk: 2.75, parry: 0.16, jump: 7.0 },
  hammer: { hp: 2650, guard: 110, move: 3.05, walk: 2.45, parry: 0.15, jump: 7.0 },
  // NYTHERA_GRAVITY_REAPER_INSTALL_V1
  scythe: { hp: 2200, guard: 84, move: 3.72, walk: 3.02, parry: 0.19, jump: 8.0 },
};

const DEFAULT: Omit<Attack, "id" | "element"> = {
  type: "melee", wind: 0.14, active: 0.08, recover: 0.3, dmg: 60, guard: 20,
  reach: 1.75, lunge: 0, knock: 2, stun: 0.32, heavy: false,
  pose_w: "l1_w", pose_s: "l1_s", next: "",
  speed: 15, size: 1, count: 1, spread: 0, style: "bolt", pierce: false,
  at: "target", delay: 0.4, radius: 1.5, repeat: 1, interval: 0.3,
  stagger: false, self_jump: 0, mode: "", duration: 0,
  cd: 0, name: "", desc: "",
  effect: "", effect_t: 0, effect_p: 0, no_parry: false, parry_stun: 0,
};

const a = (d: Partial<Attack>): Attack => ({ ...DEFAULT, id: "", element: "", ...d }) as Attack;

// FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V1
function parryCounterAttack(kit: string, element: string, base: Record<string, Attack>): Attack {
  const light = base.l1 ?? DEFAULT as Attack;
  const heavy = base.heavy ?? light;
  const poses: Record<string, [string, string]> = {
    knight: [heavy.pose_w, heavy.pose_s],
    greatsword: [heavy.pose_w, heavy.pose_s],
    hammer: [heavy.pose_w, heavy.pose_s],
    katana: [heavy.pose_w, heavy.pose_s],
    bow: [base.z?.pose_w ?? light.pose_w, base.z?.pose_s ?? light.pose_s],
    mage: [base.z?.pose_w ?? light.pose_w, base.z?.pose_s ?? light.pose_s],
    knuckles: [heavy.pose_w, heavy.pose_s],
    kicks: [base.l2?.pose_w ?? light.pose_w, base.l2?.pose_s ?? light.pose_s],
    wind: [base.z?.pose_w ?? heavy.pose_w, base.z?.pose_s ?? heavy.pose_s],
    sickle: [heavy.pose_w, heavy.pose_s],
    chainblade: [heavy.pose_w, heavy.pose_s],
    glaive: [heavy.pose_w, heavy.pose_s],
    tristaff: [heavy.pose_w, heavy.pose_s],
    scythe: [heavy.pose_w, heavy.pose_s],
    bomb: [base.z?.pose_w ?? light.pose_w, base.z?.pose_s ?? light.pose_s],
    assassin: [base.l2?.pose_w ?? light.pose_w, base.l2?.pose_s ?? light.pose_s],
  };
  const names: Record<string, string> = {
    knight: "Royal Crescent",
    greatsword: "Titan's Reversal",
    hammer: "Heartbreaker Twirl",
    katana: "Sakura Reversal",
    bow: "Scarlet Revolver",
    mage: "Spell Reversal",
    knuckles: "Iron Tornado",
    kicks: "Cyclone Roundhouse",
    wind: "Tempest Reversal",
    sickle: "Reaper's Waltz",
    chainblade: "Chain Cyclone",
    glaive: "Thunderwheel",
    tristaff: "Dragon's Answer",
    scythe: "Eclipse Reversal",
    bomb: "Firecracker Spin",
    assassin: "Shadow Carousel",
  };
  const reach: Record<string, number> = {
    knight: 1.95, greatsword: 2.20, hammer: 2.35, katana: 2.00,
    bow: 1.90, mage: 2.00, knuckles: 1.60, kicks: 1.85,
    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40, tristaff: 2.25, scythe: 2.45,
    bomb: 1.85, assassin: 1.85,
  };
  const lunge: Record<string, number> = {
    knight: 1.5, greatsword: 1.25, hammer: 1.35, katana: 1.8,
    bow: 1.2, mage: 1.15, knuckles: 1.65, kicks: 1.95,
    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8, tristaff: 2.0, scythe: 1.8,
    bomb: 1.25, assassin: 2.2,
  };
  const knock: Record<string, number> = {
    knight: 4.2, greatsword: 4.9, hammer: 5.1, katana: 4.1,
    bow: 3.6, mage: 3.8, knuckles: 3.8, kicks: 4.0,
    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8, tristaff: 4.3, scythe: 4.3,
    bomb: 3.8, assassin: 4.1,
  };
  const pose = poses[kit] ?? [light.pose_w, light.pose_s];
  return a({
    name: kit === "mage" ? (element === "fire" ? "Inferno Twirl" :
      element === "water" ? "Tidal Pirouette" : "Witch's Spiral") :
      kit === "knight" && element !== "light" ? "Crimson Waltz" :
      (names[kit] ?? "Parry Counter"),
    desc: "A fast one-hit riposte unlocked briefly after a successful parry.",
    wind: 0.40, active: 0.08, recover: 0.38,
    dmg: Math.round((light.dmg * 0.85 + heavy.dmg * 0.55) * 1.24),
    guard: Math.round(Math.max(light.guard, heavy.guard) * 1.12),
    reach: reach[kit] ?? Math.max(light.reach, 1.9),
    lunge: lunge[kit] ?? Math.max(light.lunge, 1.2),
    knock: knock[kit] ?? Math.max(light.knock, 3.1),
    stun: 0.22,
    heavy: true,
    pose_w: pose[0],
    pose_s: pose[1],
    style: "parry_counter",
    next: "",
    no_parry: false,
    parry_stun: 0,
  });
}


/** Normal attacks keyed l1.. plus "heavy" (charged), and skills keyed z/x/c. */
export function attacks(kit: string, element: string): Record<string, Attack> {
  const t: Record<string, Attack> = ({
    mage: () => mage(element),
    assassin: assassin,
    greatsword: greatsword,
    hammer: hammer,
    katana: katana,
    bow: bow,
    knuckles: knuckles,
    wind: wind,
    sickle: sickle,
    chainblade: chainblade,
    glaive: glaive,
    tristaff: dragonStaff,
    scythe: gravityScythe,
    bomb: bomb,
    kicks: kicks,
  } as Record<string, () => Record<string, Attack>>)[kit]?.() ?? knight();
  // AIR_COMBAT_V1: shared air commands keep each kit's existing Z/X/C untouched.
  Object.assign(t, airCombatMoves(kit, element, t));
  t.v = bonusSkill(kit, element);
  // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108: compact weapon, dedicated spear poses, exact SFX path mapping.
// ZENITH_SINGLE_SPEAR_FLAT_SFX_V3_20261108: one spearhead, flat /sfx/*.mp3 paths.
  // ZENITH_SOVEREIGN_METAL_BLOOM_V12_20261108 — protected V windup; 17+14 spears.
  // ZENITH_MAGNETIC_CHARGE_24X_V12_20261108 — C caps basic speed at 2.4x.
  // ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108
  // Zenith tempo: each real damaging hit grants +0.01x action speed for 5s (14 stacks max).
  // Current max at 14 stacks: 1.14x spear, 2.14x twin blades. C is a dash attack.
  // l5 spear Phantom Fang splits a single finisher into five contact windows.
  // ZENITH_IRON_SOVEREIGN_V1_20261108: Metal spear kit is independent of Zarek.
  if (kit === "glaive" && element === "metal") {
    const base = (key: string, value: Partial<Attack>) => { t[key] = a(value); };
    const combo: [number, number, string, string][] = [
      [43, 0.14, "zn1_w", "zn1_s"], [46, 0.14, "zn2_w", "zn2_s"],
      [49, 0.15, "zn3_w", "zn3_s"], [51, 0.16, "zn4_w", "zn4_s"],
      [68, 0.24, "zn5_w", "zn5_s"] ];
    for (let i=0;i<5;i++) base(`l${i+1}`, { name: `Steel Fang ${i+1}`, type: "melee",
      wind: 0.085 + 0.014 * i, active: 0.075, recover: combo[i][1],
      dmg: Math.round(combo[i][0] * 0.75 * 100) / 100, guard: 13+i*2, /* ZENITH_BASIC_DMG_25P_V8 */ reach: 2.14, lunge: 2.35, knock: i===4?3.0:0.65,
      stun: i===4?0.32:0.16, style: "zenith_basic", pose_w: combo[i][2], pose_s: combo[i][3],
      next: i<4?`l${i+2}`:"" });
    // A true multi-hit l5 needs enough active time to play five rapid thrusts.
    // Phantom Fang now totals 51 damage (-25% from 68); guard damage 21 is split, not multiplied.
    t.l5.name = "Phantom Fang";
    t.l5.active = 0.40;
    t.l5.recover = 0.12;
    base("heavy", { name: "Magnetic Lance", type: "projectile", wind: 0.44, recover: 0.47,
      dmg: 100, guard: 35, knock: 3.0, stun: 0.35, heavy: true, speed: 23, size: 0.88, pierce: true,
      style: "zenith_heavy", pose_w: "znh_w", pose_s: "znh_s" });
    base("z", { name: "Rail Spear", desc: "Throw your spear in a piercing metal line (Negative). Press Z again to recall through foes. If not recalled, it returns automatically.",
      cd: 12, type: "projectile", wind: 0.19, recover: 0.29, dmg: 92, guard: 25,
      knock: 2.5, stun: 0.40, speed: 24, size: 1.06, pierce: true,
      style: "zenith_rail", pose_w: "znz_w", pose_s: "znz_s" });
    base("x", { name: "Phantom Spear Barrage", desc: "Five fast held thrusts, then three independently flying spear thrusts while Zenith can reposition.",
      cd: 10, type: "melee", wind: 0.12, active: 0.75, recover: 0.33,
      dmg: 25, guard: 9, reach: 2.35, knock: 0.35, stun: 0.13,
      style: "zenith_barrage", pose_w: "znx_w", pose_s: "znx_s" });
    base("c", { name: "Spearstep", desc: "Surge forward with a silver spear thrust. A real dash strike that can be dodged, blocked, parried or clashed. Each successful hit grants +0.01x speed for 5s (14 stacks max).",
      cd: 11, type: "melee", mode: "", wind: 0.16, active: 0.22, recover: 0.38,
      dmg: 110, guard: 34, reach: 2.63, lunge: 16, knock: 4.2, stun: 0.45,
      style: "zenith_dash", pose_w: "znz_w", pose_s: "znz_s" });
    base("v", { name: "Sovereign Arsenal", desc: "17 protective bloom spears erupt during cast; 12 elegant directional spears and 2 guided rail finishers follow.",
      cd: 53, type: "projectile", wind: 0.55, active: 1.35, recover: 0.70,
      dmg: 43, guard: 15, knock: 1.4, stun: 0.18, speed: 17, size: 1.2,
      style: "zenith_arsenal", pose_w: "znv_w", pose_s: "znv_s" });
  }
  // ASTER_KNIGHT_COMBAT_ANIM_V2: only animation pose keys change, never skill values.
  if (kit === "knight" && element === "light") {
    const asterMoves: Record<string, [string, string]> = {
      heavy: ["aster_heavy_w", "aster_heavy_s"],
      z: ["aster_bash_w", "aster_bash_s"],
      x: ["aster_rise_w", "aster_rise_s"],
      c: ["aster_wave_w", "aster_wave_s"],
      v: ["aster_judgment", "aster_judgment"],
    };
    for (const [key, [wind, swing]] of Object.entries(asterMoves)) {
      if (t[key]) { t[key].pose_w = wind; t[key].pose_s = swing; }
    }
  }
  // NESA_MOMENTUM_V3: every hammer blow carries weight through ordinary blocks;
  // perfect parries are disabled for this kit, but dodges still beat the attack.
  if (kit === "hammer") for (const move of Object.values(t)) {
    if (move.dmg > 0) move.no_parry = true;
  }
  t.pc = parryCounterAttack(kit, element, t);
  if (kit === "mage") {
    // Roxy/Ember/Raven/Marina: after a legitimate parry, launch ONE regular
    // basic projectile. It is not a spin/AOE and still clashes and can be dodged.
    const basic = t.l1;
    t.pc = { ...basic, name: "Arcane Riposte", desc: "On a successful parry, cast one ordinary basic projectile.",
      type: "projectile", wind: 0.16, active: 0.05, recover: 0.30,
      dmg: basic.dmg, guard: basic.guard, knock: basic.knock, stun: basic.stun,
      heavy: false, count: 1, spread: 0, next: "", pierce: false,
      pose_w: basic.pose_w, pose_s: basic.pose_s };
  }
  if (kit === "glaive" && element === "metal") {
    t.pc = { ...t.l2, name: "Iron Reversal", desc: "A perfect parry opens the guard for a fast magnetic counter-thrust.",
      id: "pc", type: "melee", style: "zenith_basic", wind: 0.12, active: 0.08, recover: 0.29,
      dmg: 70, guard: 20, knock: 1.4, stun: 0.28, next: "", pose_w: "zn2_w", pose_s: "zn2_s" };
  }
  // FIGHT_ROYALE_V29_PARRY_ORBIT_GUARD: parry riposte windup 0.40s for all kits before speed bonuses.
  // Actual attack windup becomes 0.24–0.45s after passive/fatigue modifiers.
  if (t.pc) t.pc.wind = 0.40;
  // BULLET_SWORDPLAY_V1: Aster's X now sweeps forward instead of jumping.
  // Keep its existing name, damage and cooldown; each Weaken stack reduces outgoing damage 20% multiplicatively for 50s, up to x5.
  if (kit === "knight" && element === "light" && t.x?.name === "Rising Slash") {
    t.x.self_jump = 0;
    t.x.wind = 0.18;
    t.x.active = 0.12;
    t.x.recover = 0.40;
    t.x.reach = 2.25;
    t.x.lunge = 4.4;
    t.x.style = "aster_forward_sweep";
    t.x.pose_w = "aster_sweep_low_w";
    t.x.pose_s = "aster_sweep_low_s";
    t.x.effect = "weaken";
    t.x.effect_t = 50;
    t.x.effect_p = 0.80;
    t.x.desc = "Crouch low, advance, and sweep the blade forward. A hit adds Weaken (50s, max 5 stacks). Each stack reduces enemy outgoing damage by 20% multiplicatively. Another Weaken hit refreshes all stacks.";
  }
  // FIGHT_ROYALE_GARRICK_BOB_KAIZEN_ROOK_V7: targeted kit changes.
  if (kit === "knuckles") {
    // Five light punches only. Charged punch, parry counter and all Z/X/C/V untouched.
    for (const key of ["l1", "l2", "l3", "l4", "l5"]) {
      if (t[key]) t[key].dmg = Math.round(t[key].dmg * 1.25 * 100) / 100;
    }
  }
  if (kit === "chainblade") {
    // Four skills (including the optional V); no extra multiplier at cast time.
    for (const key of ["z", "x", "c", "v"]) if (t[key]) t[key].cd += 3;
  }
  if (kit === "greatsword") {
    if (t.z?.name === "Ground Slam") {
      t.z.stagger = true; // nearby shockwave now causes an actual short stagger
      t.z.desc = "Plant the greatsword for a close shockwave that staggers foes, clears weak projectiles, and braces against damage during startup.";
    }
    if (t.x?.name === "Iron Tempest") {
      t.x.desc = "Three successive advancing greatsword cuts: short slash, deeper diagonal cut, then a lunging finisher. Steer slightly between swings.";
    }
    if (t.c?.name === "Titan Cleave") {
      t.c.desc = "Rock spikes erupt beneath the enemy. If they hit, press the same skill again to rush forward and finish with an overhead strike.";
    }
    t.garrick_follow = a({
      name: "Titan Cleave", desc: "Follow-up overhead strike after a confirmed eruption hit.",
      type: "melee", wind: 0.68, active: 0.09, recover: 0.45,
      dmg: 125, guard: 36, reach: 2.65, lunge: 0, knock: 5.0,
      stun: 0.46, heavy: true, pose_w: "charge", pose_s: "heavy_s",
      style: "garrick_rush_finish", next: "",
    });
  }
  if (kit === "bomb" && t.z?.type === "mine") {
    t.z.desc = "Four stored mine charges (one recharges every 8s); place at most two active mines. Damage unchanged.";
  }
  // ZAREK_EFFECTIVE_RANGE_NERF_V1: hitboxes now match the smaller double-ended glaive.
  // Only grounded melee attack data for Zarek is changed: no damage or passive changes.
  if (kit === "glaive") {
    for (const key of ["l1", "l2", "l3", "l4", "l5", "heavy", "z", "x", "c", "v"]) {
      const move = t[key];
      if (!move || move.type !== "melee") continue;
      move.reach = Math.round(move.reach * 0.82 * 100) / 100; // -18% hit reach
      move.lunge = Math.round(move.lunge * 0.80 * 100) / 100; // -20% forward travel
    }
  }
  // Kaizen's spins now have intentional walking footwork.
  if (kit === "chainblade") {
    if (t.z?.style === "chain_razor_cyclone")
      t.z.desc = "Spin the chainblade while walking/steering toward your foe. Hold Z to extend the spinning attack.";
    if (t.c?.style === "chain_death_spiral")
      t.c.desc = "Walk during the contracting chain whirlwind; each slash follows Kaizen's live position before an overhead finisher.";
  }
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
  fire: ["burn", 4, 20, ["z", "x", "c", "v"]],        // Ember
  flame: ["burn", 4, 25, ["c", "v"]],                 // Vesper: Blade Wave, Judgment
  light: ["weaken", 50, 0.8, ["x", "c"]],             // Aster: Rising Slash / low sweep + Blade Wave (Judgment is a self-buff)
  electric: ["paralyze", 2.5, 0, ["x", "c", "v"]],    // Raven
  water: ["slow", 3, 0.6, ["z", "x", "c"]],           // Marina
  shadow: ["poison", 6, 10, ["x", "c", "v"]],         // Nyx: Shuriken Fan, Phantom Rush, Venom Fan
  moon: ["bleed", 4, 20, ["x", "c", "v"]],            // Kaede
  blood: ["bleed", 4, 22, ["x", "c"]],                // Ash: Arrow Rain, Hunter's Snare
  venom: ["poison", 4, 8, ["l1", "l2", "l3", "l4", "heavy", "z", "v"]], // Blood Hunter: slashes + thrown sickle poison; final blade consumes it
  earth: ["slow", 2.5, 0.65, ["z", "c"]],             // Garrick: Ground Slam, Titan Cleave
};

/** Short stat lines for a skill: stun time and status effect, for tooltips and skill lists. */
export function skillTags(a: Attack): string[] {
  const out: string[] = [];
  if (a.type !== "buff" && a.type !== "blink" && a.dmg > 0 && a.stun >= 0.5) out.push(`Stun ${a.stun}s`);
  if (a.no_parry) out.push("Blockable, can't be parried");
  if (a.type === "lob" || a.type === "mine" || a.type === "barrel") out.push(`Blast radius ${a.radius} m (hurts you and allies too: half damage)`);
  if (a.parry_stun) out.push(`Weakness: if parried, you're stunned ${a.parry_stun}s`);
  const info = STATUS[a.effect as StatusKind];
  if (info) out.push(info.text(a.effect_t, a.effect_p));
  return out;
}

/** Each kit's locked bonus skill ("v"): unlock it in the shop, then slot it into the loadout. */
function bonusSkill(kit: string, element: string): Attack {
  switch (kit) {
    case "mage":
      // ASTER_EMBER_LATEST_20261106: fire is consumed to amplify the beam.
      if (element === "frost") return a({ name: "Frostwing Choir", desc: "Summon 3 stationary Frostwings. Each keeps facing an enemy and fires one ice shard every 2 seconds for 25 seconds.",
        cd: 52, type: "snow_puppet", style: "bird", wind: 0.35, recover: 0.45,
        dmg: 15.75, guard: 8, knock: 0.55, stun: 0.08, count: 3, speed: 0, radius: 0.7, duration: 25,
        pose_w: "mh_w", pose_s: "m3_s" });
      if (element === "fire") return a({ name: "Absolute Combustion",
        desc: "Condense nearby fire patches and active burns into a white-hot beam. Each consumed patch and burn amplifies the damage.",
        cd: 16, type: "buff", mode: "ember_ignition", wind: 0.50, active: 0.06,
        recover: 0.80, pose_w: "ember_ignite_w", pose_s: "ember_ignite_s" });
      if (element === "electric") return a({ name: "Static Field", desc: "Create a medium-sized electric circle for 5s. Enemies inside are continuously slowed and periodically jolted by paralysis; allies are unaffected.", cd: 13, type: "buff", mode: "static_field", duration: 5, radius: 3.0, wind: 0.22, recover: 0.45, pose_w: "mh_w", pose_s: "m3_s" });
      return a({ name: "Healing Water", desc: "Create a 5s healing water pool. You and allies standing inside recover 3.5% max HP every 0.6s (up to 28% per cast).", cd: 15, type: "buff", mode: "healing_water", duration: 5, radius: 2.6, wind: 0.24, recover: 0.45, pose_w: "mh_w", pose_s: "m3_s" });
    case "assassin":
      return a({ name: "Venom Fan", desc: "A wide spray of five poisoned blades.", cd: 7, type: "projectile", wind: 0.12, recover: 0.3, dmg: 42, guard: 12, knock: 1.2, stun: 0.3, speed: 24, count: 5, spread: 0.5, style: "shuriken", pose_w: "as1_w", pose_s: "as1_s" });
    case "chainblade":
      return a({ name: "Serpent Bind", desc: "Bind an opponent with your chain for up to 4 seconds. Press Z to reel them in, lift them, and smash them side to side; X lifts and swings them over Kaizen before a heavy behind-the-back slam. Both stay locked until the finisher ends.", cd: 13,
        wind: 0.29, active: 0.12, recover: 0.62, dmg: 85, guard: 29, reach: 2.9, knock: 1.0, stun: 0.55,
        style: "chain_serpent_bind", pose_w: "cbv_w", pose_s: "cbv_s" });
    case "greatsword":
      return a({ name: "Berserk", desc: "Deal 20% more damage for 6 seconds.", cd: 14, type: "buff", mode: "rage", duration: 6, wind: 0.2, recover: 0.4, pose_w: "charge", pose_s: "win" });
    case "hammer":
      // NESA_FORWARD_HEART_PARRY_V_20261108: first a vertical swing with an honest parry window.
      return a({ name: "Heartbreaker High Striker",
        desc: "A vertical hammer counter-swing that parries one incoming attack. A successful parry stuns the attacker and unlocks the 4x giant hammer finishing blow. If no parry occurs, no giant hammer appears and 40% of this skill's cooldown is refunded.",
        cd: 26, type: "strike", at: "self", wind: 0.24, active: 2.15, recover: 0.55,
        dmg: 145, guard: 85, knock: 12.5, stun: 0.26, heavy: true,
        radius: 3.50, style: "nesa_high_striker", pose_w: "nesa_parry_w", pose_s: "nesa_parry_s" });
    case "katana":
      return a({ name: "Iaido Flash", desc: "An instant cross-arena draw cut.", cd: 8, wind: 0.08, active: 0.16, recover: 0.45, dmg: 200, guard: 50, reach: 2.2, lunge: 18, knock: 5, stun: 0.7, heavy: true, pose_w: "charge", pose_s: "heavy_s" });
    case "bow":
      return a({ name: "Piercing Volley", desc: "Five arrows that fly through every enemy in line.", cd: 9, type: "projectile", wind: 0.2, recover: 0.4, dmg: 55, guard: 14, knock: 2, stun: 0.3, speed: 32, count: 5, spread: 0.25, style: "arrow", pierce: true, pose_w: "bow_w", pose_s: "bow_s" });
    case "scythe":
      return a({ name: "Black Star Requiem", desc: "A graceful four-beat eclipse dance ending in a falling-star scythe cut. All beats play even on miss, block, parry or clash; each hit can be defended, clashed or dodged independently.",
        cd: 43, type: "melee", wind: 0.36, active: 1.04, recover: 0.53,
        dmg: 40, guard: 15, reach: 2.90, knock: 1, stun: 0.18, style: "gravity_requiem",
        pose_w: "grv_w", pose_s: "grv_float", heavy: false });
    // ZEPHYR_DRAGON_DANCER_V1 — nine distinct real melee contacts, not one unblockable animation.
    case "tristaff":
      return a({ name: "Ninefold Dragon", desc: "Nine independently timed three-section staff hits, alternating grips and an aerial finish. Each can be dodged, blocked, parried and clashed.",
        cd: 42, type: "melee", wind: 0.40, active: 1.90, recover: 0.75,
        dmg: 33, guard: 11, reach: 2.36, lunge: 1.8, knock: 0.65, stun: 0.13,
        style: "zephyr_ninefold", pose_w: "zdv_w", pose_s: "zdv_s" });
    case "glaive":
      return a({ name: "Arc Flash", desc: "A lightning-fast straight-line glaive draw dash, inspired by an anime thunder swordsman. Travels during the active window and cuts at the end; can be blocked, parried or clashed.", cd: 12,
        type: "melee", wind: 0.13, active: 0.21, recover: 0.48, dmg: 190, guard: 49, reach: 2.35, lunge: 38,
        knock: 5.2, stun: 0.60, heavy: true, style: "glaive_thunderflash", pose_w: "glx_w", pose_s: "glx_turn" });
    case "sickle":
      // VEYR_BLOODLUST_CARRION_V7: five separate sickle strikes; REAL melee collisions may clash.
      return a({ name: "Carrion Sweep", desc: "Five rapid alternating sickle cuts with a vicious crosscut finisher. Each cut can clash, be blocked, or be parried; no automatic clash is forced.",
        cd: 12, type: "melee", wind: 0.16, active: 0.72, recover: 0.30,
        dmg: 18, guard: 5, reach: 1.94, lunge: 2.2, knock: 0.25, stun: 0.10,
        style: "sickle_carrion", pose_w: "vrv_w", pose_s: "vrv1_s" });
    case "bomb":
      return a({ name: "Cluster Bomb", desc: "Throw a striped four-pod cluster canister. Its orange warning circle marks the full spread before the four blasts land.", cd: 10, type: "lob", wind: 0.2, recover: 0.4, dmg: 80, guard: 22, knock: 4, stun: 0.45, delay: 0.85, radius: 1.5, repeat: 4, interval: 0.12, style: "clusterbomb", size: 1.65, pose_w: "throw_w", pose_s: "throw_s" });
    case "wind":
      return a({ name: "Gust Barrage", desc: "Three wind blades fly out in a fan.", cd: 7, parry_stun: 1.5, type: "projectile", wind: 0.14, recover: 0.35, dmg: 60, guard: 16, knock: 2, stun: 0.35, speed: 22, count: 3, spread: 0.25, size: 1.2, style: "wave", pierce: true, pose_w: "w2_w", pose_s: "w2_s" });
    case "knuckles":
      return a({ name: "Iron Body", desc: "Shrug off every hit for 2.5 seconds.", cd: 13, type: "buff", mode: "ward", duration: 2.5, wind: 0.1, recover: 0.25, pose_w: "block", pose_s: "block" });
    case "kicks":
      return a({ name: "Hundred Kicks", desc: "Visible, immobile casting pose with six phantom strikes. Casting duration reduced by 25%, damage remains 30 per hit. Still vulnerable to attacks.", cd: 10, type: "strike", wind: 0.1125, active: 0.06, recover: 0.45, dmg: 30, guard: 10, knock: 0.8, stun: 0.3, delay: 0.15, radius: 1.5, repeat: 6, interval: 0.045, style: "slashes", pose_w: "kira_hundred_cast_w", pose_s: "kira_hundred_cast_s" });
    default:
      if (element === "light") return a({ name: "Judgment",
        desc: "Raise your sword, receive harmless lightning, and merge your sword and shield for 10s. Defense converts to power, missing HP adds damage, and health drains while blocking weakens. While Judgment is active, sword attacks are 1.5x faster and successful blade hits add 1 Weaken stack (50s, max 5).",
        cd: 16, type: "buff", mode: "judgment", duration: 10,
        wind: 0.62, active: 0.06, recover: 0.30,
        pose_w: "judgment_raise", pose_s: "judgment_raise" });
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
  // EMBER_DAMAGE_RADIUS_NERF_V2_20261106: Ember basic projectiles deal 15% less damage.
  if (element === "fire") mul = 0.85;
  const t: Record<string, Attack> = {
    l1: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.26, dmg: 55 * mul, guard: 15, knock: 1.6, stun: 0.28, speed, pose_w: "m1_w", pose_s: "m1_s", next: "l2" }),
    l2: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.28, dmg: 60 * mul, guard: 15, knock: 1.8, stun: 0.3, speed, pose_w: "m2_w", pose_s: "m2_s", next: "l3" }),
    l3: a({ type: "projectile", wind: 0.24, active: 0.05, recover: 0.42, dmg: 42 * mul, guard: 14, knock: 3, stun: 0.4, speed, count: 3, spread: 0.22, pose_w: "m3_w", pose_s: "m3_s" }),
  };
  // ROXY_FROSTWING_SPELLBOOK_V3_20261108: Roxy's 4-button spellbook kit.
  if (element === "frost") {
    // All light bolts are individually destructible projectiles. No piercing or homing.
    for (const key of ["l1", "l2", "l3"]) {
      t[key] = { ...t[key], dmg: Math.round(t[key].dmg * 0.75) * 1.05, style: "frost_shard", pierce: false, size: 0.82 }; // ROXY V5: 25% less light damage
    }
    t.heavy = a({ name: "Seeking Frost", type: "projectile", wind: 0.24, active: 0.05, recover: 0.55,
      dmg: 42, guard: 16, knock: 1.2, stun: 0.16, speed: 13.0, size: 0.85, count: 4, spread: 0.33,
      style: "frost_shard", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Snowglass Aegis", desc: "Four orbiting ice crystals. Each incoming damaging hit destroys one shard and deals zero damage; lasts up to 7 seconds.",
      cd: 13, type: "buff", mode: "frost_aegis", duration: 7, wind: 0.13, recover: 0.25, pose_w: "mh_w", pose_s: "m3_s" });
    t.x = a({ name: "Frost Marionette", desc: "Summon a light-blue snow marionette that automatically rushes an enemy and FREEZES it for 2 seconds on contact.",
      cd: 10, type: "snow_puppet", style: "freeze", wind: 0.26, recover: 0.42,
      dmg: 46, guard: 20, knock: 0.7, stun: 0.08, count: 1, speed: 4.5, radius: 0.9, duration: 8.5,
      effect: "freeze", effect_t: 2.0, pose_w: "m2_w", pose_s: "m2_s" });
    t.c = a({ name: "Glacier Meteor", desc: "A huge icy meteor falls on the marked enemy position, damaging and slowing enemies in the impact area.",
      cd: 15, type: "strike", style: "meteor", wind: 0.36, recover: 0.65, dmg: 160, guard: 65, knock: 5.5, stun: 0.65,
      heavy: true, delay: 0.85, radius: 2.1, effect: "slow", effect_t: 2.0, effect_p: 0.65,
      pose_w: "mh_w", pose_s: "mh_s" });
    return t;
  }

  if (element === "fire") {
    // Charged basic (heavy) leaves a 20-second fire patch at its impact.
    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.55, dmg: 155, guard: 60, knock: 6, stun: 0.7, heavy: true, delay: 0.5, radius: 1.05, style: "explosion", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Flame Burst", desc: "Erupt in flames, blasting anyone close away.", cd: 6, type: "strike", at: "self", wind: 0.12, recover: 0.4, dmg: 95, guard: 40, knock: 7, stun: 0.5, delay: 0.05, radius: 2.3, style: "explosion", pose_w: "mh_w", pose_s: "m3_s" });
    t.x = a({ name: "Fireball Volley", desc: "Hurl a fan of five fireballs.", cd: 7, type: "projectile", wind: 0.2, recover: 0.4, dmg: 31, guard: 12, knock: 2, speed: 16, count: 5, spread: 0.45, pose_w: "m3_w", pose_s: "m3_s" });
    t.c = a({ name: "Meteor", desc: "Call a meteor down on the enemy's position. Impact leaves burning ground for 20s.", cd: 12, type: "strike", wind: 0.3, recover: 0.6, dmg: 215, guard: 80, knock: 8, stun: 0.9, heavy: true, delay: 0.9, radius: 2.1, style: "meteor", pose_w: "mh_w", pose_s: "mh_s" });
  } else if (element === "electric") {
    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.5, dmg: 185, guard: 55, knock: 4, stun: 0.8, heavy: true, delay: 0.35, radius: 1.3, style: "lightning", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Blink", desc: "Flash backward out of danger.", cd: 4, type: "blink", mode: "back", wind: 0.04, recover: 0.15, pose_w: "m1_w", pose_s: "m1_s" });
    t.x = a({ name: "Chain Lightning", desc: "A near-instant bolt that locks the target in place.", cd: 6, type: "projectile", wind: 0.14, recover: 0.35, dmg: 90, guard: 25, knock: 1, stun: 0.75, speed: 42, size: 1.3, pose_w: "m2_w", pose_s: "m2_s" });
    t.c = a({ name: "Thunderstorm", desc: "Three lightning strikes hunt the enemy.", cd: 12, type: "strike", wind: 0.3, recover: 0.6, dmg: 110, guard: 35, knock: 3, stun: 0.6, heavy: true, delay: 0.45, radius: 1.25, repeat: 3, interval: 0.35, style: "lightning", pose_w: "mh_w", pose_s: "mh_s" });
  } else {
    t.heavy = a({ type: "projectile", wind: 0.15, active: 0.05, recover: 0.55, dmg: 190, guard: 60, knock: 7, stun: 0.7, heavy: true, speed: 9, size: 2.4, pierce: true, pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Bubble Ward", desc: "A protective water bubble lasting 8 seconds in all modes.", cd: 13, type: "buff", mode: "ward", duration: 8, wind: 0.1, recover: 0.25, pose_w: "mh_w", pose_s: "m3_s" });
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
    heavy: a({ wind: 0.12, active: 0.16, recover: 0.5, dmg: 170, guard: 45, reach: 2, lunge: 7, knock: 5, stun: 0.7, heavy: true, pose_w: "nyx_heavy_w", pose_s: "nyx_heavy_s" }),
    z: a({ name: "Smoke Step", desc: "Vanish and reappear behind the enemy.", cd: 5, type: "blink", mode: "behind", wind: 0.06, recover: 0.12, pose_w: "nyx_smoke_w", pose_s: "nyx_smoke_s" }),
    x: a({ name: "Shuriken Fan", desc: "Throw three spinning shuriken.", cd: 6, type: "projectile", wind: 0.12, recover: 0.3, dmg: 48, guard: 14, knock: 1.5, stun: 0.35, speed: 22, count: 3, spread: 0.3, style: "shuriken", pose_w: "nyx_throw_w", pose_s: "nyx_throw_s" }),
    c: a({ name: "Phantom Rush", desc: "A blinding dash that cuts through the enemy.", cd: 10, wind: 0.18, active: 0.18, recover: 0.55, dmg: 260, guard: 70, reach: 2.2, lunge: 16, knock: 6, stun: 0.9, heavy: true, stagger: true, pose_w: "nyx_rush_w", pose_s: "nyx_rush_s" }),
  };
}

// KAIZEN_CHAINBLADE_V1 — compact sword combo; the extended chain is powerful but slower.
// KAIZEN_DIRECTIONAL_V3 — five chainblade hits and four entirely new specials.
function chainblade(): Record<string, Attack> {
  return {
    l1: a({ name: "Dancing Fang 1", wind: 0.16, active: 0.10, recover: 0.25, dmg: 69, guard: 20, reach: 2.12, lunge: 2.0, knock: 1.2, stun: 0.24, style: "chain_basic", pose_w: "cb1_w", pose_s: "cb1_s", next: "l2" }),
    l2: a({ name: "Dancing Fang 2", wind: 0.17, active: 0.10, recover: 0.26, dmg: 73, guard: 21, reach: 2.2, lunge: 2.0, knock: 1.2, stun: 0.25, style: "chain_basic", pose_w: "cb2_w", pose_s: "cb2_s", next: "l3" }),
    l3: a({ name: "Dancing Fang 3", wind: 0.20, active: 0.11, recover: 0.29, dmg: 77, guard: 23, reach: 2.4, lunge: 1.8, knock: 1.5, stun: 0.27, style: "chain_basic", pose_w: "cb3_w", pose_s: "cb3_s", next: "l4" }),
    l4: a({ name: "Dancing Fang 4", wind: 0.25, active: 0.12, recover: 0.31, dmg: 90, guard: 28, reach: 2.8, lunge: 1.6, knock: 1.8, stun: 0.32, style: "chain_basic", pose_w: "cb4_w", pose_s: "cb4_s", next: "l5" }),
    l5: a({ name: "Dancing Fang Return", wind: 0.24, active: 0.24, recover: 0.55, dmg: 112, guard: 36, reach: 3.0, lunge: 1.2, knock: 3.8, stun: 0.40, heavy: true, style: "chain_return", pose_w: "cb5_w", pose_s: "cb5_s" }),
    heavy: a({ name: "Chainbreaker", wind: 0.35, active: 0.17, recover: 0.67, dmg: 185, guard: 51, reach: 3.0, lunge: 1.2, knock: 5.6, stun: 0.56, heavy: true, style: "chain_heavy", pose_w: "cbh_w", pose_s: "cbh_s" }),
    z: a({ name: "Razor Cyclone", desc: "Spin the chained blade around Kaizen. Hold the skill to extend the spin and its range (max 1.6 seconds).", cd: 8, wind: 0.20, active: 1.65, recover: 0.38, dmg: 28, guard: 11, reach: 2.2, stun: 0.15, style: "chain_razor_cyclone", pose_w: "cbz_w", pose_s: "cbz_s" }),
    x: a({ name: "Predator's Hook", desc: "Throw a long chain to bind one enemy in place for up to 4 seconds. Kaizen may move, but other attacks and skills are locked. Press X again to pull the victim toward you. Blocking or a clash prevents the bind.", cd: 10, wind: 0.22, active: 0.13, recover: 0.45, dmg: 75, guard: 24, reach: 4.8, stun: 0.28, style: "chain_predator_hook", pose_w: "cbh_w", pose_s: "cbh_s" }),
    // Air X is the same Predator's Hook, not a new skill or a second cooldown.
    // Fighter.readSkill() automatically selects x_air when airborne.
    x_air: a({ name: "Predator's Hook", desc: "Midair X: cast the chain at an enemy above or below. A hit binds; press X again to pull. Shares X cooldown.", cd: 10, wind: 0.22, active: 0.13, recover: 0.45, dmg: 75, guard: 24, reach: 4.8, stun: 0.28, style: "chain_predator_hook", pose_w: "cbh_w", pose_s: "cbh_s" }),
    c: a({ name: "Thousand Cuts: Death Spiral", desc: "A contracting circle of chain slashes ending in an overhead strike. Escape before the circle closes.", cd: 22, wind: 0.38, active: 1.85, recover: 0.68, dmg: 42, guard: 12, radius: 4.2, style: "chain_death_spiral", pose_w: "cbc_w", pose_s: "cbc_s" }),
  };
}

function greatsword(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.30, active: 0.14, recover: 0.38, dmg: 110, guard: 32, reach: 2.55, lunge: 2, knock: 3, stun: 0.42, next: "l2" }),
    l2: a({ wind: 0.29, active: 0.14, recover: 0.40, dmg: 120, guard: 34, reach: 2.60, lunge: 2, knock: 3, stun: 0.42, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ wind: 0.40, active: 0.17, recover: 0.60, dmg: 190, guard: 50, reach: 2.70, lunge: 2.5, knock: 6, stun: 0.6, stagger: true, pose_w: "l3_w", pose_s: "l3_s" }),
    heavy: a({ wind: 0.24, active: 0.18, recover: 0.72, dmg: 320, guard: 80, reach: 2.90, lunge: 4, knock: 8, stun: 0.9, heavy: true, pose_w: "charge", pose_s: "heavy_s" }),
    z: a({ name: "Ground Slam", desc: "Smash the earth, knocking back everyone nearby.", cd: 6, type: "strike", at: "self", wind: 0.3, recover: 0.5, dmg: 150, guard: 50, knock: 7, stun: 0.6, delay: 0.05, radius: 2.6, style: "slam", pose_w: "l3_w", pose_s: "l3_s" }),
    x: a({ name: "Iron Tempest", desc: "Brace, carve two wide turning sweeps, then unleash a crushing horizontal cleave. The upper arc can catch jumping enemies. Block or parry to counter it.", cd: 9, type: "strike", at: "self", wind: 0.28, active: 0.86, recover: 0.48, dmg: 70, guard: 22, knock: 1.1, stun: 0.16, delay: 0.04, radius: 2.80, repeat: 3, interval: 0.30, lunge: 1.1, style: "iron_tempest", pose_w: "charge", pose_s: "heavy_s" }),
    c: a({ name: "Titan Cleave", desc: "A colossal downward cleave that splits the ground ahead.", cd: 12, type: "strike", wind: 0.4, recover: 0.7, dmg: 340, guard: 90, knock: 9, stun: 1.0, heavy: true, delay: 0.55, radius: 2.0, style: "cleave", pose_w: "l3_w", pose_s: "l3_s" }),
  };
}

function hammer(): Record<string, Attack> {
  return {
    // NESA_MOMENTUM_V3: longer weighty casts, fast impact frames, higher knockback.
    l1: a({ name: "Heart Hook", desc: "Heavy horizontal opener; deliberate pull, fast contact.", wind: 0.43, active: 0.095, recover: 0.21, dmg: 97, guard: 28, reach: 2.43, lunge: 1.9, knock: 3.1, stun: 0.29, pose_w: "l1_w", pose_s: "l1_s", next: "l2" }),
    l2: a({ name: "Reverse Crush", desc: "Uses the first hit's momentum to swing back while stepping forward.", wind: 0.45, active: 0.095, recover: 0.22, dmg: 107, guard: 30, reach: 2.53, lunge: 2.35, knock: 3.7, stun: 0.32, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ name: "Overhead Spin", desc: "A staggered-foot pivot into a quick overhead strike.", wind: 0.50, active: 0.10, recover: 0.24, dmg: 129, guard: 35, reach: 2.64, lunge: 2.65, knock: 4.5, stun: 0.38, pose_w: "l3_w", pose_s: "l3_s", next: "l4" }),
    l4: a({ name: "Heartquake", desc: "Fourth hit: massive shockwave ground slam.", type: "strike", at: "self", wind: 0.57, active: 0.14, recover: 0.44, dmg: 178, guard: 47, reach: 2.55, lunge: 3.25, knock: 8.6, stun: 0.72, heavy: true, delay: 0.06, radius: 2.55, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
    heavy: a({ name: "Momentum Cyclone", desc: "Hold left-click to control spin duration; each turn hits, the final turn launches.", wind: 0.45, active: 0.48, recover: 0.43, dmg: 36, guard: 15, reach: 2.58, lunge: 2.10, knock: 1.5, stun: 0.20, heavy: false, style: "nesa_spin", pose_w: "charge", pose_s: "l3_s" }),
    z: a({ name: "Side Swipe", desc: "Huge sideways strike. Block reduces damage but cannot nullify its push.", cd: 7, wind: 0.36, active: 0.11, recover: 0.42, dmg: 180, guard: 72, reach: 2.69, lunge: 1.75, knock: 9.6, stun: 0.70, heavy: true, pose_w: "nx_w", pose_s: "nx_s" }),
    x: a({ name: "Upsie Daisie", desc: "Plant the hammer as a pole, keep a firm grip, then swing sideways into a long-reaching flying kick.", cd: 9, wind: 0.40, active: 0.16, recover: 0.50, dmg: 170, guard: 36, reach: 2.62, lunge: 7.8, knock: 7.3, stun: 0.57, heavy: true, self_jump: 6.6, pose_w: "kick_w", pose_s: "kick_s" }),
    c: a({ name: "Pink Heart Smash", desc: "Three forward heart-smash charges. Regular blocking negates HP damage (unless guard breaks); cannot be parried. Dodge or guard the telegraphed impact.",
      cd: 7.5, type: "strike", at: "self", wind: 0.36, active: 0.13, recover: 0.36,
      dmg: 156, guard: 42, knock: 7.4, stun: 0.56, heavy: true, no_parry: true,
      delay: 0.035, radius: 2.72, style: "nesa_heart_slam", pose_w: "charge", pose_s: "heavy_s" }),
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
    c: a({ name: "Thousand Cuts", desc: "Kaede slides her katana into its sheath, then seven blinding cuts strike the marked area.", cd: 11, type: "strike", wind: 0.2, recover: 0.6, dmg: 48, guard: 12, knock: 1, stun: 0.3, delay: 0.3, radius: 1.5, repeat: 7, interval: 0.07, style: "slashes", pose_w: "kaede_sheathe_w", pose_s: "kaede_sheathe_s" }),
  };
}

// FIGHT_ROYALE_ASH_CHARGE_GUARD_HALF_V5: Ash heavy charged-arrow guard 60 -> 30, HP damage unchanged.
function bow(): Record<string, Attack> {
  return {
    l1: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.22, dmg: 48, guard: 14, knock: 1.4, stun: 0.28, speed: 28, style: "arrow", pose_w: "bow_w", pose_s: "bow_s", next: "l2" }),
    l2: a({ type: "projectile", wind: 0.16, active: 0.05, recover: 0.22, dmg: 50, guard: 14, knock: 1.4, stun: 0.28, speed: 28, style: "arrow", pose_w: "bow_w", pose_s: "bow_s", next: "l3" }),
    l3: a({ type: "projectile", wind: 0.22, active: 0.05, recover: 0.38, dmg: 37, guard: 12, knock: 2.5, stun: 0.35, speed: 28, count: 3, spread: 0.12, style: "arrow", pose_w: "bow_w", pose_s: "bow_s" }),
    heavy: a({ type: "projectile", wind: 0.1, active: 0.05, recover: 0.5, dmg: 195, guard: 30, knock: 6, stun: 0.7, heavy: true, speed: 42, size: 1.7, style: "arrow", pierce: true, pose_w: "bow_w", pose_s: "bow_s" }),
    z: a({ name: "Leap Back", desc: "Spring away to open distance.", cd: 4, type: "blink", mode: "back", wind: 0.04, recover: 0.12, pose_w: "jump", pose_s: "jump" }),
    x: a({ name: "Arrow Rain", desc: "A volley falls on the target area three times.", cd: 8, type: "strike", wind: 0.22, recover: 0.4, dmg: 80, guard: 20, knock: 2, stun: 0.35, delay: 0.7, radius: 1.8, repeat: 3, interval: 0.25, style: "arrows", pose_w: "rain_w", pose_s: "rain_s" }),
    c: a({ name: "Hunter's Snare", desc: "A barbed arrow that pins the target in place.", cd: 10, type: "projectile", wind: 0.2, recover: 0.4, dmg: 100, guard: 30, knock: 0.5, stun: 1.6, stagger: true, speed: 32, size: 1.3, style: "arrow", pose_w: "bow_w", pose_s: "bow_s" }),
  };
}

/** Bomber: lobs firecrackers, plants mines, throws a paralyzing bomb and parks a powder keg. */

// BLOOD_HUNTER_V2 — Veyr's pressure-and-punish kit. High single-target skill expression.
// ZAREK_STORM_V1 — weapon clashes award Momentum; ability effects are host-controlled.
// ZAREK_CYCLONE_V3 — clash-focused acrobatic double-blade choreography.
function glaive(): Record<string, Attack> {
  // ZAREK_WEAPON_RANGE_MATCH_V1_NOV06: visible blade and active combat reach are calibrated together.
  return {
    l1: a({ name: "Cyclone Fang 1", wind: 0.11, active: 0.09, recover: 0.19, dmg: 58, guard: 16, reach: 2.05, lunge: 2.7, knock: 1.0, stun: 0.22, pose_w: "gl1_w", pose_s: "gl1_s", next: "l2" }),
    l2: a({ name: "Cyclone Fang 2", wind: 0.12, active: 0.09, recover: 0.18, dmg: 64, guard: 17, reach: 2.1, lunge: 2.8, knock: 1.0, stun: 0.23, pose_w: "gl2_w", pose_s: "gl2_s", next: "l3" }),
    l3: a({ name: "Cyclone Fang 3", wind: 0.10, active: 0.10, recover: 0.20, dmg: 69, guard: 18, reach: 2.08, lunge: 2.7, knock: 1.2, stun: 0.24, pose_w: "gl3_w", pose_s: "gl3_s", next: "l4" }),
    l4: a({ name: "Cyclone Fang 4", wind: 0.17, active: 0.11, recover: 0.23, dmg: 74, guard: 20, reach: 2.12, lunge: 2.4, knock: 1.6, stun: 0.27, pose_w: "gl4_w", pose_s: "gl4_s", next: "l5" }),
    l5: a({ name: "Cyclone Fang Finisher", desc: "Overhead turning slash. Hold the fifth attack to extend it into three more rotations.",
      wind: 0.17, active: 0.56, recover: 0.33, dmg: 104, guard: 29, reach: 2.18, lunge: 1.7, knock: 3.5, stun: 0.38,
      style: "glaive_cyclone", pose_w: "gl5_w", pose_s: "gl5_s" }),
    heavy: a({ name: "Split Current", wind: 0.35, active: 0.14, recover: 0.55, dmg: 165, guard: 48, reach: 2.34, lunge: 2.5, knock: 5, stun: 0.52, heavy: true, pose_w: "glh_w", pose_s: "glh_s" }),
    z: a({ name: "Serpent Wheel", desc: "Five revolving blade passes while stepping forward. Cannot be parried, but can be blocked or clashed. Dash-cancel or Space+Attack launcher-cancel.",
      cd: 8, wind: 0.14, active: 1.08, recover: 0.40, dmg: 33, guard: 11, reach: 2.06, lunge: 3.1, knock: 0.5, stun: 0.12,
      no_parry: true, style: "glaive_serpent", pose_w: "glz_w", pose_s: "glz_s" }),
    x: a({ name: "Phantom Spiral", desc: "Slide through the target, cutting once on approach and once after a 180-degree reverse strike. Can be blocked, parried and clashed.",
      cd: 9, wind: 0.13, active: 0.43, recover: 0.39, dmg: 85, guard: 24, reach: 2.18, lunge: 1.4, knock: 2.0, stun: 0.27,
      style: "glaive_phantom", pose_w: "glx_w", pose_s: "glx_turn" }),
    c: a({ name: "Infinite Crescent", desc: "Seven accelerating crescent cuts, an upward launcher, then an aerial cross-slash. A confirmed finisher hit triggers cinematic sparks and brief hit-stop. Cannot be parried; blocking and clashes still work.",
      cd: 20, wind: 0.30, active: 1.78, recover: 0.70, dmg: 44, guard: 15, reach: 2.18, lunge: 1.2,
      knock: 0.6, stun: 0.21, heavy: false, no_parry: true, style: "glaive_infinite", pose_w: "glc_w", pose_s: "glc_s" }),
  };
}

/** ZEPHYR_DRAGON_DANCER_V1 — realistic folded, extended and spinning staff actions. */
function dragonStaff(): Record<string, Attack> {
  return {
    l1: a({ name: "Dragon Entry", wind: 0.13, active: 0.075, recover: 0.18,
      dmg: 48, guard: 14, reach: 2.09, lunge: 2.35, knock: 0.50, stun: 0.17,
      style: "zephyr_staff", pose_w: "zd1_w", pose_s: "zd1_s", next: "l2" }),
    l2: a({ name: "Backwind Catch", wind: 0.15, active: 0.08, recover: 0.19,
      dmg: 55, guard: 15, reach: 2.10, lunge: 2.0, knock: 0.58, stun: 0.18,
      style: "zephyr_staff", pose_w: "zd2_w", pose_s: "zd2_s", next: "l3" }),
    l3: a({ name: "Underarm Eight", wind: 0.15, active: 0.085, recover: 0.20,
      dmg: 61, guard: 17, reach: 2.16, lunge: 2.15, knock: 0.68, stun: 0.21,
      style: "zephyr_staff", pose_w: "zd3_w", pose_s: "zd3_s", next: "l4" }),
    l4: a({ name: "Orbit Wheel", wind: 0.19, active: 0.12, recover: 0.24,
      dmg: 71, guard: 20, reach: 2.26, lunge: 2.25, knock: 1.4, stun: 0.25,
      style: "zephyr_staff", pose_w: "zd4_w", pose_s: "zd4_s", next: "l5" }),
    l5: a({ name: "Twin-End Verdict", wind: 0.23, active: 0.10, recover: 0.43,
      dmg: 105, guard: 32, reach: 2.28, lunge: 2.15, knock: 4.0, stun: 0.40,
      style: "zephyr_finisher", pose_w: "zd5_w", pose_s: "zd5_s" }),
    heavy: a({ name: "Dragon Tail Break", wind: 0.29, active: 0.13, recover: 0.53,
      dmg: 166, guard: 52, reach: 2.52, lunge: 2.25, knock: 5.1, stun: 0.51, heavy: true,
      style: "zephyr_finisher", pose_w: "zdh_w", pose_s: "zdh_s" }),
    z: a({ name: "Serpent Wheel", desc: "Two overhead revolutions and a sweeping third strike; three independently defendable hits.",
      cd: 8, wind: 0.19, active: 0.59, recover: 0.41,
      dmg: 51, guard: 17, reach: 2.35, lunge: 2.6, knock: 0.75, stun: 0.17,
      style: "zephyr_serpent", pose_w: "zdz_w", pose_s: "zdz_s" }),
    x: a({ name: "Dragon Reversal", desc: "Fold the staff and brace for a 0.34s automatic counter. If hit by a parryable attack, neutralize it and counterattack. Failed reads leave recovery.",
      cd: 10, type: "buff", mode: "counter", duration: 0.34, wind: 0.04, active: 0.04, recover: 0.53,
      style: "zephyr_reversal", pose_w: "zdx_w", pose_s: "zdx_s" }),
    c: a({ name: "Heavenly Cyclone", desc: "Five transitioning staff grips: waist, shoulder, overhead, reverse and advancing finisher. Each contact remains blockable, parryable and clashable.",
      cd: 17, type: "melee", wind: 0.29, active: 1.18, recover: 0.57,
      dmg: 49, guard: 16, reach: 2.42, lunge: 1.8, knock: 0.7, stun: 0.16,
      style: "zephyr_cyclone", pose_w: "zdc_w", pose_s: "zdc_s" }),
  };
}

function sickle(): Record<string, Attack> {
  return {
    // Basic attacks are deliberately stronger than the original 29/31/37/48.
    l1: a({ wind: 0.085, active: 0.065, recover: 0.17, dmg: 46, guard: 11, reach: 1.65, lunge: 3.2, knock: 0.9, stun: 0.20, pose_w: "vr1_w", pose_s: "vr1_s", next: "l2" }),
    l2: a({ wind: 0.085, active: 0.065, recover: 0.17, dmg: 50, guard: 11, reach: 1.65, lunge: 3.2, knock: 1.1, stun: 0.21, pose_w: "vr2_w", pose_s: "vr2_s", next: "l3" }),
    l3: a({ wind: 0.12, active: 0.07, recover: 0.22, dmg: 57, guard: 14, reach: 1.7, lunge: 3.8, knock: 1.4, stun: 0.23, pose_w: "vr3_w", pose_s: "vr3_s", next: "l4" }),
    l4: a({ wind: 0.18, active: 0.09, recover: 0.38, dmg: 72, guard: 20, reach: 1.8, lunge: 3.2, knock: 3, stun: 0.36, pose_w: "vr4_w", pose_s: "vr4_s" }),
    heavy: a({ wind: 0.42, active: 0.10, recover: 0.54, dmg: 100, guard: 30, reach: 2.05, lunge: 4.3, knock: 3, stun: 0.4, heavy: true, pose_w: "vrh_w", pose_s: "vrh_s" }),
    // BLOOD_FESTIVAL_V3 — Crimson Execution replaces the former Blood Sickle skill.
    z: a({ name: "Crimson Execution", desc: "Three curved blood blades; the final blade consumes poison for +15 damage per stack.", cd: 12, type: "projectile", wind: 0.30, recover: 0.54, dmg: 45, guard: 14, knock: 1.8, stun: 0.22, speed: 14, count: 3, spread: 0.58, size: 1.2, style: "bloodcrescent", pose_w: "vrc_w", pose_s: "vrc_s" }),
    x: a({ name: "Death Feint", desc: "A 0.30s counter window. If struck, slip past the attacker and counter-cut. A failed feint leaves you open.", cd: 10, type: "buff", mode: "blood_feint", duration: 0.30, wind: 0.08, active: 0.04, recover: 0.55, pose_w: "vrx_w", pose_s: "vrx_s" }),
    c: a({ name: "Blood Festival", desc: "Teleport beside a target and surround enemies with orbiting blood scythes for 8 seconds. The rim pushes enemies inward. Veyr ignores stuns but can still take damage or be blocked/clashed; his special skills are locked. Light attacks deal +35% damage and 3x normal guard damage. Bloodlust fills only from landed attacks; no free Blood Frenzy on cast.", cd: 29, type: "buff", mode: "blood_festival", duration: 8, radius: 3.5, wind: 0.26, active: 0.05, recover: 0.24, pose_w: "vrc_w", pose_s: "vrc_s" }),
  };
}



/** NYTHERA_SIX_HIT_REAPER_TRAILS_V3_20261108 — six-beat curved basic string, one-handle scythe.
 * Mode-specific damage, types, and poses are resolved in Fighter.startAttack. */
function gravityScythe(): Record<string, Attack> {
  return {
    // Six flowing, alternating cuts with a quick natural animation reset.
    l1: a({ name: "Open Crescent", wind: 0.085, active: 0.08, recover: 0.115,
      dmg: 65, guard: 15, reach: 2.40, lunge: 2.35, knock: 0.38, stun: 0.15,
      style: "gravity_crescent", pose_w: "gr1_w", pose_s: "gr1_s", next: "l2" }),
    l2: a({ name: "Reverse Veil", wind: 0.09, active: 0.08, recover: 0.120,
      dmg: 69, guard: 16, reach: 2.42, lunge: 2.25, knock: 0.42, stun: 0.16,
      style: "gravity_crescent", pose_w: "gr2_w", pose_s: "gr2_s", next: "l3" }),
    l3: a({ name: "Sky Hook", wind: 0.10, active: 0.08, recover: 0.13,
      dmg: 76, guard: 17, reach: 2.48, lunge: 2.40, knock: 0.55, stun: 0.18,
      style: "gravity_crescent", pose_w: "gr3_w", pose_s: "gr3_s", next: "l4" }),
    l4: a({ name: "Orbit Bloom", wind: 0.105, active: 0.09, recover: 0.145,
      dmg: 83, guard: 19, reach: 2.52, lunge: 2.50, knock: 0.58, stun: 0.19,
      style: "gravity_bloom", pose_w: "gr4_w", pose_s: "gr4_s", next: "l5" }),
    l5: a({ name: "Reversal Hook", wind: 0.11, active: 0.09, recover: 0.15,
      dmg: 84, guard: 21, reach: 2.54, lunge: 2.30, knock: 0.55, stun: 0.18,
      style: "gravity_crescent", pose_w: "gr5_w", pose_s: "gr5_s", next: "l6" }),
    l6: a({ name: "Eclipse Reap", wind: 0.145, active: 0.11, recover: 0.24,
      dmg: 120, guard: 30, reach: 2.56, lunge: 2.60, knock: 2.65, stun: 0.32,
      style: "gravity_bloom", pose_w: "gr6_w", pose_s: "gr6_s" }),
    heavy: a({ name: "Grave Descent", wind: 0.24, active: 0.10, recover: 0.52,
      dmg: 155, guard: 44, reach: 2.53, lunge: 3.15, knock: 4.4, stun: 0.46, heavy: true,
      style: "gravity_grave", pose_w: "grh_w", pose_s: "grh_s" }),
    z: a({ name: "Crescent Snare", desc: "Three elegant alternating hooked scythe cuts. Each beat can be dodged, blocked, parried, or clashed; no hit-confirm required. Moonfloat pulls on successful cuts; Dreadfall consumes Orbit Marks on damage.",
      cd: 6.5, wind: 0.15, active: 0.45, recover: 0.25,
      dmg: 45, guard: 12, reach: 2.68, lunge: 2.6, knock: 0.75, stun: 0.18,
      style: "gravity_snare", pose_w: "grz_w", pose_s: "grz_s" }),
    x: a({ name: "Zero-G Ascension", desc: "Three rapid, rising scythe arcs that continue even if the first is defended or misses. Moonfloat lifts on a real hit; Dreadfall cleaves with three heavy cuts. Each beat uses ordinary melee defenses.",
      cd: 9.0, wind: 0.18, active: 0.54, recover: 0.28,
      dmg: 49, guard: 13, reach: 2.68, lunge: 2.95, knock: 1.2, stun: 0.21,
      style: "gravity_ascend", pose_w: "grx_w", pose_s: "grx_s" }),
    x_air: a({ name: "Mass Descent", desc: "Dreadfall only: descend with the scythe and crash down in an avoidable circle.",
      cd: 10.0, type: "strike", at: "self", mode: "dive", speed: 24,
      wind: 0.11, active: 0.12, recover: 0.51,
      dmg: 158, guard: 49, radius: 2.10, lunge: 7.0, knock: 5.8, stun: 0.51, heavy: true,
      style: "gravity_meteor", pose_w: "grx_air_w", pose_s: "grx_air_s" }),
    c: a({ name: "Event Horizon", desc: "Moonfloat: summon an escapable pulling field for 2.6s. Dreadfall: collapse the field after a visible warning. The shock can be defended or evaded.",
      cd: 14.0, type: "buff", mode: "gravity_well", wind: 0.32, active: 0.10, recover: 0.43,
      dmg: 0, radius: 2.8, style: "gravity_well", pose_w: "grc_w", pose_s: "grc_s" }),
  };
}

function bomb(): Record<string, Attack> {
  return {
    l1: a({
      type: "lob",
      wind: 0.22, active: 0.05, recover: 0.36,
      dmg: 35, guard: 10, knock: 1.3, stun: 0.2,
      delay: 0.65, radius: 0.8,
      style: "bomb", size: 0.7,
      pose_w: "throw_w", pose_s: "throw_s", next: "l2"
    }),

    l2: a({
      type: "lob",
      wind: 0.22, active: 0.05, recover: 0.38,
      dmg: 40, guard: 10, knock: 1.5, stun: 0.2,
      delay: 0.65, radius: 0.8,
      style: "bomb", size: 0.7,
      pose_w: "throw_w", pose_s: "throw_s", next: "l3"
    }),

    l3: a({
      type: "lob",
      wind: 0.3, active: 0.05, recover: 0.5,
      dmg: 28, guard: 8, knock: 2, stun: 0.25,
      delay: 0.7, radius: 0.8,
      count: 3, spread: 0.35,
      style: "bomb", size: 0.6,
      pose_w: "throw_w", pose_s: "throw_s"
    }),

    heavy: a({
      type: "lob",
      wind: 0.3, active: 0.05, recover: 0.7,
      dmg: 150, guard: 40, knock: 5, stun: 0.5,
      heavy: true, delay: 1.0, radius: 1.5,
      style: "bomb", size: 1.8,
      pose_w: "throw_w", pose_s: "throw_s"
    }),

    z: a({
      name: "Land Mine",
      desc: "Plant a mine at your feet. It arms after half a second and blows up when an enemy steps on it (3 at most).",
      cd: 8, type: "mine",
      wind: 0.18, recover: 0.3,
      dmg: 110, guard: 30, knock: 4, stun: 0.5,
      radius: 1.2,
      pose_w: "plant_w", pose_s: "plant_s"
    }),

    x: a({
      name: "Paralyze Bomb",
      desc: "Lob a crackling bomb that paralyzes enemies in the blast.",
      cd: 11, type: "lob",
      wind: 0.22, recover: 0.45,
      dmg: 65, guard: 20, knock: 1.5, stun: 0.3,
      delay: 0.65, radius: 1.5,
      style: "bomb", size: 1.3,
      effect: "paralyze", effect_t: 1.5,
      pose_w: "throw_w", pose_s: "throw_s"
    }),

    c: a({
      name: "Powder Keg",
      desc: "Set down a powder keg, then press again to detonate it. An enemy hitting the keg sets it off too.",
      cd: 18, type: "barrel",
      wind: 0.3, recover: 0.5,
      dmg: 200, guard: 55, knock: 6, stun: 0.7,
      heavy: true, radius: 2.0,
      pose_w: "barrel_w", pose_s: "barrel_s"
    }),
  };
}


/**
 * Wind dancer. Grounded skills are plain and quick (a wind punch, a short dash, a rising
 * whirlwind); cast in the air, each one becomes a dive that smashes into the ground.
 * Can double jump.
 */
function wind(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.1, active: 0.06, recover: 0.14, dmg: 46, guard: 12, reach: 1.55, lunge: 3, knock: 1.2, stun: 0.26, pose_w: "w1_w", pose_s: "w1_s", next: "l2" }),
    l2: a({ wind: 0.1, active: 0.06, recover: 0.16, dmg: 50, guard: 12, reach: 1.55, lunge: 3, knock: 1.4, stun: 0.28, pose_w: "w2_w", pose_s: "w2_s", next: "l3" }),
    l3: a({ wind: 0.17, active: 0.08, recover: 0.34, dmg: 80, guard: 22, reach: 1.7, lunge: 4, knock: 4.5, stun: 0.45, pose_w: "w3_w", pose_s: "w3_s" }),
    heavy: a({ type: "projectile", wind: 0.12, active: 0.05, recover: 0.5, dmg: 200, guard: 55, knock: 6, stun: 0.7, heavy: true, speed: 18, size: 1.7, style: "shock", pierce: true, pose_w: "w3_w", pose_s: "w3_s" }),
    z: a({ parry_stun: 1.5, name: "Gale Fist", desc: "A straight punch wrapped in wind.", cd: 4, wind: 0.14, active: 0.08, recover: 0.3, dmg: 110, guard: 30, reach: 1.9, lunge: 4, knock: 5, stun: 0.5, pose_w: "w1_w", pose_s: "w1_s" }),
    z_air: a({ parry_stun: 1.5, name: "Downburst", desc: "In the air: plunge straight down and smash the ground.", cd: 4, type: "strike", at: "self", mode: "dive", speed: 26, lunge: 2, wind: 0.08, recover: 0.4, dmg: 130, guard: 35, knock: 6, stun: 0.6, delay: 0.02, radius: 2.2, style: "slam", pose_w: "slam_air", pose_s: "slam_s" }),
    x: a({ parry_stun: 1.5, name: "Wind Step", desc: "A quick short dash that strikes anyone in the way.", cd: 5, wind: 0.1, active: 0.16, recover: 0.3, dmg: 90, guard: 25, reach: 1.6, lunge: 15, knock: 3, stun: 0.4, pose_w: "wd_w", pose_s: "wd_s" }),
    x_air: a({ parry_stun: 1.5, name: "Falling Star", desc: "In the air: dive at the enemy and crash down fist-first.", cd: 5, type: "strike", at: "self", mode: "dive", speed: 22, lunge: 11, wind: 0.06, recover: 0.45, dmg: 160, guard: 40, knock: 6, stun: 0.8, heavy: true, delay: 0.02, radius: 1.8, style: "slam", pose_w: "slam_air", pose_s: "slam_s" }),
    c: a({ parry_stun: 1.5, name: "Tornado Rise", desc: "A rising uppercut inside a whirlwind that hits all around you three times and lifts you into the air.", cd: 15, type: "strike", at: "self", self_jump: 9, wind: 0.08, recover: 0.4, dmg: 60, guard: 20, knock: 3, stun: 0.6, delay: 0.03, radius: 2.0, repeat: 3, interval: 0.14, style: "spin", pose_w: "kh_w", pose_s: "rise" }),
    c_air: a({ parry_stun: 1.5, name: "Hurricane Crash", desc: "In the air: crash down inside a hurricane that slams everyone around three times.", cd: 15, type: "strike", at: "self", mode: "dive", speed: 28, lunge: 4, wind: 0.1, recover: 0.6, dmg: 80, guard: 30, knock: 7, stun: 1.0, heavy: true, delay: 0.02, radius: 3.0, repeat: 3, interval: 0.18, style: "slam", pose_w: "slam_air", pose_s: "slam_s" }),
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
    c: a({ name: "Meteor Fist", desc: "Leap at the enemy and smash the ground on landing. Super armor during the entire move: immune to stun, stagger, paralysis, slow and knockback, but still takes damage.", cd: 11, type: "strike", at: "self", mode: "leap", self_jump: 9, wind: 0.22, recover: 0.6, dmg: 300, guard: 80, knock: 8, stun: 0.9, heavy: true, delay: 0.02, radius: 2.5, style: "slam", pose_w: "slam_w", pose_s: "slam_s" }),
  };
}

function kicks(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.08, active: 0.06, recover: 0.16, dmg: 46, guard: 12, reach: 1.65, lunge: 3, knock: 1.2, stun: 0.26, pose_w: "kk1_w", pose_s: "kk1_s", next: "l2" }),
    l2: a({ wind: 0.1, active: 0.07, recover: 0.18, dmg: 56, guard: 14, reach: 1.75, lunge: 3, knock: 1.6, stun: 0.28, pose_w: "kk2_w", pose_s: "kk2_s", next: "l3" }),
    l3: a({ wind: 0.12, active: 0.08, recover: 0.2, dmg: 72, guard: 18, reach: 1.85, lunge: 3.5, knock: 2.2, stun: 0.32, pose_w: "kk3_w", pose_s: "kk3_s", next: "l4" }),
    l4: a({ wind: 0.18, active: 0.08, recover: 0.38, dmg: 105, guard: 30, reach: 1.8, lunge: 2.5, knock: 4.5, stun: 0.5, stagger: true, pose_w: "kk4_w", pose_s: "kk4_s" }),
    heavy: a({ wind: 0.12, active: 0.16, recover: 0.5, dmg: 230, guard: 55, reach: 2.0, lunge: 7, knock: 6.5, stun: 0.8, heavy: true, self_jump: 4, pose_w: "charge", pose_s: "fly_s" }),
    z: a({ name: "Cyclone Kick", desc: "Three real rotating heel kicks with alternating legs and a final knock-away. Each kick can be guarded or parried.", cd: 6, type: "strike", at: "self", wind: 0.18, active: 0.57, recover: 0.40, dmg: 65, guard: 20, knock: 3, stun: 0.3, delay: 0.03, radius: 2.0, repeat: 3, interval: 0.19, style: "cyclone_kick_v2", pose_w: "cy1_w", pose_s: "cy1_s" }),
    x: a({ name: "Crescent Gale", desc: "A kick so fast it launches a cutting wind across the arena.", cd: 6, type: "projectile", wind: 0.14, recover: 0.35, dmg: 110, guard: 30, knock: 3, stun: 0.45, speed: 20, size: 1.4, style: "wave", pierce: true, pose_w: "kk2_w", pose_s: "kk2_s" }),
    c: a({ name: "Phantom Step", desc: "Vanish and reappear behind the enemy for a kick, three times. The first kick stuns for 2 seconds, holding them for the rest.", cd: 16, type: "phantom", wind: 0.12, active: 0.05, recover: 1.35, dmg: 115, guard: 30, knock: 1.2, stun: 2.0, stagger: true, heavy: true, repeat: 3, interval: 0.5, no_parry: true, pose_w: "kk1_w", pose_s: "kk3_s" }),
  };
}

// AIR_COMBAT_V1: kit-specific anti-airs and airborne combos (never a ground smash).
// Every playable character inherits their kit's signature style; different elements
// distinguish Aster/Vesper and the three elemental mages.
function airCombatMoves(kit: string, element: string, base: Record<string, Attack>): Record<string, Attack> {
  const profiles: Record<string, [string, number, number, string, string]> = {
    knight: [element === "light" ? "Rising Shield" : "Rising Riposte", 43, 2.05, element === "light" ? "block" : "l1_w", element === "light" ? "bash" : "rise"],
    greatsword: ["Sky Cleaver", 53, 2.5, "charge", "heavy_s"],
    katana: ["Ascending Draw", 43, 2.2, "l1_w", "rise"],
    assassin: ["Dagger Lift", 35, 1.85, "as1_w", "as3_s"],
    knuckles: ["Rising Uppercut", 41, 1.9, "kh_w", "kh_s"],
    kicks: ["Skyward Kick", 42, 2.1, "kk2_w", "fly_s"],
    wind: ["Gale Uppercut", 37, 2.1, "w1_w", "rise"],
    sickle: ["Sickle Pursuit", 40, 2.15, "vr1_w", "vr3_s"],
    glaive: ["Storm Lift", 43, 2.35, "gl3_w", "gl3_s"],
    chainblade: ["Chain Lift", 48, 2.30, "cb3_w", "cb3_s"],
    mage: [element === "electric" ? "Lightning Lift" : element === "water" ? "Tidal Lift" : "Flame Lift", 33, 2.6, "mh_w", "mh_s"],
    bow: ["Rising Bowstrike", 32, 2.15, "bow_w", "bow_s"],
    bomb: ["Airburst Guard", 34, 2.2, "throw_w", "throw_s"],
  };
  const [name, dmg, reach, windPose, hitPose] = profiles[kit] ?? profiles.knight;
  const fast = ["chainblade", "assassin", "sickle", "glaive", "katana", "kicks", "wind"].includes(kit);
  const ranged = kit === "mage" || kit === "bow";
  const anti = a({
    name, desc: "Space + Attack: intercept airborne foes, then tap Space to chase a successful launcher.",
    type: "melee", wind: fast ? 0.12 : kit === "greatsword" ? 0.26 : 0.17,
    active: 0.12, recover: fast ? 0.29 : 0.39,
    dmg, guard: 20, knock: 2.2, stun: 0.33, reach, lunge: 0,
    pose_w: windPose, pose_s: hitPose,
  });
  const baseLight = base.l1;
  const blade = ranged ? "projectile" : "melee";
  const mk = (n: number, dmg: number, next: string, knock: number): Attack => a({
    name: n === 3 ? "Aerial Finisher" : `Air Strike ${n}`,
    type: blade, wind: fast ? 0.09 : 0.14, active: 0.09,
    recover: n === 3 ? 0.37 : 0.23,
    dmg, guard: n === 3 ? 18 : 12, stun: n === 3 ? 0.34 : 0.21,
    knock, reach: kit === "greatsword" ? 2.35 : 1.95, lunge: 0,
    speed: 21, size: 0.8, style: ranged ? (kit === "bow" ? "arrow" : baseLight.style) : "bolt",
    pose_w: n === 1 ? windPose : n === 2 ? (base.l2?.pose_w ?? windPose) : (base.l3?.pose_w ?? windPose),
    pose_s: n === 1 ? hitPose : n === 2 ? (base.l2?.pose_s ?? hitPose) : (base.l3?.pose_s ?? hitPose),
    next,
  });
  // Gale remains the only dive/ground-smash specialist. These finishers knock away sideways.
  return {
    anti_air: anti,
    air_l1: mk(1, fast ? 28 : 32, "air_l2", 0.8),
    air_l2: mk(2, fast ? 32 : 36, "air_l3", 1.0),
    air_l3: mk(3, fast ? 42 : 48, "", 4.0),
    air_heavy: a({ name: "Air Heavy", type: ranged ? "projectile" : "melee",
      wind: fast ? 0.15 : 0.24, active: 0.1, recover: 0.48,
      dmg: fast ? 63 : 74, guard: 25, knock: 5.2, stun: 0.38, heavy: true,
      reach, lunge: 0, speed: 23, size: 1.1,
      style: ranged ? (kit === "bow" ? "arrow" : baseLight.style) : "bolt",
      pose_w: windPose, pose_s: hitPose }),
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

// SWORD_AND_CYCLONE_V1: Aster is a practiced one-handed swordsman; shield stays near the ribs.
// These poses are exclusive to his light-element knight, not Vesper.
const ASTER_SWINGS: Record<string, Pose> = {
  // ASTER_EMBER_LATEST_20261106: Aster holds his sword straight up for Judgment.
  judgment_raise: P([-0.08, 0, -0.02], [-0.22, 0, 0], [-2.95, -0.12, 0.04], [0.1, 0, 0], [-0.32, 0.14, 0.48], [0, 0, -0.2], [-0.35, 0, 0.13], [0.31, 0, -0.13], -0.06),
  l1_w: P([0.14, -0.92, -0.04], [0, 0.75, 0], [-0.9, -1.25, -0.26], [0.68, 0, 0], [-1.22, -0.3, 0.15], [0, 0, -0.8], [-0.46, 0, 0.08], [0.36, 0, -0.07], -0.13),
  l1_s: P([0.27, 0.72, 0.08], [-0.04, -0.5, 0], [-1.7, 0.95, -0.08], [0.18, 0, 0], [-1.15, -0.22, 0.14], [0, 0, -0.8], [-0.62, 0, 0.09], [0.42, 0, -0.08], -0.15),
  l2_w: P([0.15, 0.77, 0.06], [0, -0.6, 0], [-1.6, 1.1, 0.1], [0.42, 0, 0], [-1.2, -0.25, 0.15], [0, 0, -0.8], [-0.52, 0, 0.08], [0.42, 0, -0.08], -0.13),
  l2_s: P([0.27, -0.85, -0.07], [-0.05, 0.6, 0], [-1.6, -1.15, -0.06], [0.25, 0, 0], [-1.21, -0.25, 0.15], [0, 0, -0.8], [-0.64, 0, 0.09], [0.48, 0, -0.08], -0.15),
  l3_w: P([-0.12, -0.36, 0.02], [0.06, 0.3, 0], [-2.7, -0.45, -0.08], [0.57, 0, 0], [-1.31, -0.15, 0.18], [0, 0, -0.85], [-0.42, 0, 0.09], [0.45, 0, -0.09], -0.12),
  l3_s: P([0.42, 0.38, -0.06], [-0.12, -0.26, 0], [-1.16, 0.55, -0.04], [0.2, 0, 0], [-1.3, -0.22, 0.16], [0, 0, -0.8], [-0.72, 0, 0.12], [0.52, 0, -0.09], -0.19),
  charge: P([0.16, -1.0, 0], [0, 0.85, 0], [-0.66, -1.55, -0.14], [0.85, 0, 0], [-1.4, -0.21, 0.19], [0, 0, -0.8], [-0.54, 0, 0.12], [0.47, 0, -0.1], -0.17),
  heavy_s: P([0.38, 1.02, 0.04], [-0.13, -0.76, 0], [-1.48, 1.25, -0.06], [0.2, 0, 0], [-1.28, -0.22, 0.15], [0, 0, -0.8], [-0.7, 0, 0.1], [0.5, 0, -0.1], -0.2),
};

// ASTER_KNIGHT_COMBAT_ANIM_V2: Aster-only sword/shield choreography.
// Each entry is a body pose at a timed combat phase; hitboxes and frame timing stay the same.
// Distinct chamber / release / reset; shield positioning is handled by Aster's VRM arm IK.
const ASTER_COMBAT_V2: Record<string, Pose> = {
  idle: P([0.065, -0.25, 0], [-0.025, 0.19, 0], [-0.84, -0.18, -0.16], [-0.28, 0, -0.03], [-1.12, -0.24, 0.21], [0.05, 0, -0.16], [-0.18, 0, 0.10], [0.15, 0, -0.11], -0.03),
  block: P([0.105, -0.07, -0.02], [-0.09, 0.06, 0], [-0.96, 0.20, -0.20], [-0.25, 0, 0], [-1.40, -0.42, 0.11], [0, 0, -0.1], [-0.26, 0, 0.12], [0.22, 0, -0.12], -0.062),
  aster_reset: P([0.095, -0.14, 0], [-0.025, 0.11, 0], [-1.00, -0.11, -0.12], [-0.17, 0, 0], [-1.18, -0.23, 0.18], [0, 0, -0.14], [-0.20, 0, 0.11], [0.17, 0, -0.1], -0.045),
  // Slash 1: sword comes to the right shoulder, then cuts horizontally across the body.
  l1_w: P([0.12, -0.58, -0.04], [0, 0.38, 0], [-1.18, -0.82, -0.20], [0.34, 0, 0], [-1.22, -0.20, 0.20], [0, 0, -0.12], [-0.31, 0, 0.11], [0.27, 0, -0.10], -0.063),
  l1_s: P([0.21, 0.60, 0.06], [-0.07, -0.29, 0], [-1.60, 0.75, -0.02], [-0.04, 0, 0], [-1.32, -0.15, 0.19], [0, 0, -0.08], [-0.48, 0, 0.12], [0.37, 0, -0.10], -0.092),
  // Slash 2: controlled reverse cut, shield still covering the center.
  l2_w: P([0.12, 0.55, 0.05], [0, -0.27, 0], [-1.52, 0.86, 0.05], [0.19, 0, 0], [-1.23, -0.16, 0.20], [0, 0, -0.1], [-0.30, 0, 0.12], [0.28, 0, -0.11], -0.066),
  l2_s: P([0.23, -0.62, -0.055], [-0.055, 0.36, 0], [-1.51, -0.81, -0.01], [0.04, 0, 0], [-1.35, -0.2, 0.17], [0, 0, -0.09], [-0.47, 0, 0.12], [0.34, 0, -0.1], -0.095),
  // Slash 3: overhead finisher, longer visual anticipation then heavy diagonal follow-through.
  l3_w: P([-0.075, -0.28, 0.015], [0.07, 0.18, 0], [-2.58, -0.48, -0.14], [0.43, 0, 0], [-1.36, -0.19, 0.22], [0, 0, -0.11], [-0.31, 0, 0.12], [0.30, 0, -0.11], -0.053),
  l3_s: P([0.37, 0.48, -0.05], [-0.13, -0.31, 0], [-0.91, 0.78, -0.045], [0.11, 0, 0], [-1.39, -0.22, 0.19], [0, 0, -0.08], [-0.57, 0, 0.12], [0.44, 0, -0.11], -0.13),
  // Charged slash: blade drawn behind right hip, weight transfers through front boot.
  aster_heavy_w: P([0.12, -0.83, -0.04], [0, 0.40, 0], [-0.74, -1.33, -0.16], [0.65, 0, 0], [-1.43, -0.23, 0.22], [0, 0, -0.11], [-0.39, 0, 0.12], [0.36, 0, -0.1], -0.107),
  aster_heavy_s: P([0.38, 0.92, 0.07], [-0.15, -0.47, 0], [-1.25, 1.18, -0.08], [0.10, 0, 0], [-1.43, -0.12, 0.22], [0, 0, -0.08], [-0.66, 0, 0.12], [0.53, 0, -0.10], -0.16),
  // Shield Bash: retract shield into the chest, then drive it forward with a planted step.
  aster_bash_w: P([0.07, -0.23, -0.01], [-0.035, 0.11, 0], [-0.79, 0.31, -0.25], [-0.18, 0, 0], [-1.48, -0.24, 0.12], [0, 0, -0.12], [-0.41, 0, 0.12], [0.33, 0, -0.11], -0.105),
  aster_bash_s: P([0.36, 0.18, -0.035], [-0.105, -0.14, 0], [-0.75, 0.15, -0.28], [-0.15, 0, 0], [-1.66, -0.06, 0.12], [0, 0, -0.1], [-0.66, 0, 0.12], [0.48, 0, -0.11], -0.13),
  // Rising Slash: load the sword low and drive an uppercut through the jump.
  // Aster crouches on the front leg, coils his torso, then extends the sword horizontally.
  aster_sweep_low_w: P([0.34, -0.42, 0.12], [0.05, 0.14, 0], [-0.40, -0.69, -0.16], [0.22, 0, 0], [-1.20, -0.16, 0.15], [0, 0, -0.10], [-0.72, 0, 0.10], [0.64, 0, -0.08], -0.19),
  aster_sweep_low_s: P([0.18, 0.62, -0.07], [-0.04, -0.24, 0], [-1.46, 0.67, -0.24], [0.37, 0, -0.10], [-1.15, -0.24, 0.26], [0, 0, -0.11], [-0.59, 0, 0.08], [0.51, 0, -0.07], -0.13),
  aster_rise_w: P([0.21, -0.29, 0], [-0.03, 0.25, 0], [-0.39, -0.58, -0.21], [0.44, 0, 0], [-1.3, -0.2, 0.18], [0, 0, -0.1], [-0.45, 0, 0.11], [0.39, 0, -0.09], -0.095),
  aster_rise_s: P([-0.22, 0.37, 0], [-0.14, -0.25, 0], [-2.73, 0.43, -0.13], [0.34, 0, 0], [-1.18, -0.17, 0.22], [0, 0, -0.1], [-0.59, 0, 0.09], [0.23, 0, -0.09], -0.025),
  // Blade Wave: shoulder-level coil, sharp release into a broad projecting cut.
  aster_wave_w: P([-0.025, -0.49, 0.02], [0.025, 0.32, 0], [-2.06, -0.65, -0.20], [0.30, 0, 0], [-1.27, -0.14, 0.19], [0, 0, -0.1], [-0.34, 0, 0.11], [0.30, 0, -0.1], -0.057),
  aster_wave_s: P([0.24, 0.61, -0.03], [-0.06, -0.38, 0], [-1.03, 0.98, -0.04], [0.12, 0, 0], [-1.35, -0.13, 0.22], [0, 0, -0.1], [-0.48, 0, 0.12], [0.38, 0, -0.1], -0.093),
  // Judgment: sword held straight overhead, shield set close while the buff activates.
  aster_judgment: P([-0.055, -0.04, 0], [-0.20, 0.02, 0], [-2.91, -0.09, 0.035], [0.10, 0, 0], [-1.22, -0.13, 0.19], [0, 0, -0.1], [-0.30, 0, 0.12], [0.27, 0, -0.11], -0.056),
  // Reactions: shield stays across torso as the knight absorbs the impact.
  hit: P([-0.15, 0.19, -0.03], [-0.15, -0.13, 0], [-0.79, 0.12, -0.19], [-0.13, 0, 0], [-1.38, -0.20, 0.17], [0, 0, -0.10], [0.03, 0, 0.12], [-0.07, 0, -0.12], -0.065),
  stagger: P([-0.26, 0.26, -0.04], [-0.22, -0.13, 0], [-0.64, 0.20, -0.17], [-0.10, 0, 0], [-1.34, -0.14, 0.20], [0, 0, -0.11], [0.15, 0, 0.11], [-0.15, 0, -0.1], -0.09),
  clash: P([-0.19, -0.13, 0], [-0.07, 0.1, 0], [-1.06, -0.20, -0.20], [0.11, 0, 0], [-1.45, -0.17, 0.22], [0, 0, -0.1], [-0.20, 0, 0.12], [0.15, 0, -0.11], -0.095),
};

// Slow, braced two-handed cutting arcs. The chest and feet transfer the weight;
// left hand is held to the blade grip by FighterModel / VrmRig IK.
const GARRICK_SWINGS: Record<string, Pose> = {
  idle: P([0.09, -0.24, 0], [-0.03, 0.18, 0], [-1.06, -0.17, -0.14], [-0.36, 0, 0], [-1.04, 0.17, 0.11], [-0.36, 0, 0], [-0.12, 0, 0.05], [0.12, 0, -0.05], -0.075),
  l1_w: P([0.2, -1.17, -0.12], [-0.06, 0.8, 0], [-1.18, -1.21, -0.2], [0.74, 0, 0], [-1.13, -0.88, 0.2], [0.7, 0, 0], [-0.67, 0, 0.13], [0.45, 0, -0.1], -0.22),
  l1_s: P([0.42, 0.95, 0.15], [-0.18, -0.64, 0], [-1.7, 1.1, -0.02], [0.12, 0, 0], [-1.65, 1.35, 0.18], [0.12, 0, 0], [-0.92, 0, 0.15], [0.55, 0, -0.11], -0.28),
  l2_w: P([0.21, 0.95, 0.1], [-0.08, -0.65, 0], [-1.51, 1.24, 0.1], [0.55, 0, 0], [-1.45, 1.5, 0.17], [0.52, 0, 0], [-0.72, 0, 0.13], [0.48, 0, -0.1], -0.22),
  l2_s: P([0.4, -1.04, -0.14], [-0.2, 0.65, 0], [-1.76, -1.18, -0.04], [0.13, 0, 0], [-1.72, -0.83, 0.2], [0.1, 0, 0], [-0.92, 0, 0.15], [0.58, 0, -0.11], -0.28),
  l3_w: P([-0.07, -0.52, 0], [-0.02, 0.35, 0], [-3.04, -0.45, -0.2], [0.65, 0, 0], [-3.0, -0.08, 0.18], [0.55, 0, 0], [-0.69, 0, 0.12], [0.5, 0, -0.1], -0.16),
  l3_s: P([0.57, 0.34, 0.04], [-0.28, -0.28, 0], [-0.83, 0.65, 0], [0.2, 0, 0], [-0.82, 0.98, 0.2], [0.2, 0, 0], [-1.05, 0, 0.14], [0.67, 0, -0.12], -0.36),
  charge: P([0.21, -1.2, -0.12], [-0.07, 0.74, 0], [-1.17, -1.5, -0.22], [0.67, 0, 0], [-1.15, -1.2, 0.22], [0.61, 0, 0], [-0.8, 0, 0.14], [0.6, 0, -0.12], -0.28),
  heavy_s: P([0.52, 1.11, 0.13], [-0.27, -0.64, 0], [-1.61, 1.22, -0.14], [0.16, 0, 0], [-1.56, 1.5, 0.16], [0.16, 0, 0], [-1.1, 0, 0.16], [0.73, 0, -0.12], -0.36),
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
  // CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: planted explosive-mage ritual stance, Ember only.
  ember_ignite_w: P([-0.27, 0, 0], [-0.20, 0, 0], [-2.55, -0.10, -0.14], [0.14, 0, 0], [-0.95, -0.28, 0.58], [0.17, 0, -0.45], [-0.45, 0.0, 0.16], [0.40, 0, -0.16], -0.20),
  ember_ignite_s: P([0.16, 0, 0], [0.09, 0, 0], [-1.72, 0.04, -0.15], [0.22, 0, 0], [-1.10, -0.15, 0.72], [0.10, 0, -0.42], [-0.56, 0, 0.18], [0.46, 0, -0.18], -0.24),
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

// NYX_SHADOW_COMBAT_AIR_2_V1: asymmetrical, knife-forward assassin choreography.
// Changes pose data only; existing ground damage and skill cooldowns are untouched.
const NYX_SHADOW_V1: Record<string, Pose> = {
  idle: P([0.10, -0.38, 0.02], [-0.04, 0.32, -0.03], [-0.95, -0.43, -0.24], [0.70, -0.10, -0.05], [-1.12, 0.40, 0.31], [0.58, 0.09, 0.04], [-0.26, 0.0, 0.12], [0.21, 0.0, -0.12], -0.045),
  block: P([0.12, 0.02, -0.05], [-0.08, -0.02, 0.02], [-1.35, 0.38, -0.36], [1.10, 0, 0.08], [-1.40, -0.35, 0.28], [1.08, 0, -0.10], [-0.36, 0, 0.11], [0.28, 0, -0.10], -0.075),
  jump: P([0.05, -0.18, 0], [0.04, 0.18, 0], [-1.22, -0.50, -0.32], [0.82, 0, 0], [-1.30, 0.51, 0.31], [0.85, 0, 0], [-0.73, 0, 0.10], [-0.55, 0, -0.10], -0.035),
  // Four distinct dagger cuts: right cross, left reverse, forward double stab, crossing finisher.
  as1_w: P([0.12, -0.75, -0.08], [-0.03, 0.55, 0.05], [-0.68, -1.12, -0.23], [1.03, 0.18, -0.06], [-1.11, 0.40, 0.40], [0.80, 0, 0], [-0.32, 0, 0.14], [0.30, 0, -0.12], -0.08),
  as1_s: P([0.24, 0.49, 0.08], [-0.08, -0.32, 0], [-1.41, 1.06, -0.11], [1.30, -0.14, 0], [-1.05, -0.25, 0.38], [0.62, 0, -0.05], [-0.43, 0, 0.13], [0.45, 0, -0.09], -0.095),
  as2_w: P([0.14, 0.65, 0.05], [-0.04, -0.50, 0], [-1.02, -0.18, -0.32], [0.80, 0.02, 0], [-0.60, 1.18, 0.26], [1.08, -0.12, 0.05], [-0.35, 0, 0.12], [0.28, 0, -0.10], -0.07),
  as2_s: P([0.22, -0.52, -0.06], [-0.04, 0.41, 0], [-1.04, 0.33, -0.34], [0.75, 0, 0], [-1.47, -1.04, 0.05], [1.37, 0.08, 0], [-0.40, 0, 0.10], [0.46, 0, -0.13], -0.09),
  as3_w: P([0.05, -0.20, 0], [-0.08, 0.20, 0], [-0.63, -0.45, -0.52], [1.42, 0, 0], [-0.65, 0.52, 0.48], [1.39, 0, 0], [-0.51, 0, 0.14], [0.46, 0, -0.13], -0.095),
  as3_s: P([0.31, 0.08, 0], [-0.06, -0.04, 0], [-1.63, 0.06, -0.18], [1.25, 0, 0], [-1.65, -0.08, 0.18], [1.27, 0, 0], [-0.73, 0, 0.13], [0.62, 0, -0.13], -0.13),
  as4_w: P([-0.02, -0.19, 0.01], [0.03, 0.16, 0], [-0.80, -1.16, -0.30], [1.18, 0, 0], [-0.82, 1.16, 0.30], [1.18, 0, 0], [-0.39, 0, 0.12], [0.29, 0, -0.12], -0.07),
  as4_s: P([0.38, 0.10, 0], [-0.12, -0.11, 0], [-1.59, 0.61, -0.05], [1.45, 0, 0], [-1.60, -0.59, 0.03], [1.46, 0, 0], [-0.67, 0, 0.15], [0.56, 0, -0.15], -0.15),
  // Charged dagger lunge, with the arms gathered before releasing a cross-cut.
  nyx_heavy_w: P([0.12, -0.70, -0.08], [-0.03, 0.53, 0], [-0.50, -1.15, -0.53], [1.02, 0, -0.11], [-0.53, 1.08, 0.48], [1.03, 0, 0.05], [-0.47, 0, 0.13], [0.45, 0, -0.11], -0.11),
  nyx_heavy_s: P([0.35, 0.24, 0], [-0.12, -0.17, 0], [-1.85, 0.43, -0.24], [1.47, 0, 0], [-1.83, -0.43, 0.25], [1.45, 0, 0], [-0.78, 0, 0.12], [0.65, 0, -0.12], -0.16),
  // Smoke Step: dip into the disappearance, spring out of the reappearance.
  nyx_smoke_w: P([0.42, -0.22, 0.08], [-0.24, 0.20, 0], [-0.62, -0.26, -0.53], [0.82, 0, 0], [-0.59, 0.35, 0.43], [0.79, 0, 0], [-0.68, 0, 0.16], [0.59, 0, -0.14], -0.20),
  nyx_smoke_s: P([0.12, 0.37, -0.06], [0.01, -0.27, 0], [-1.26, 0.64, -0.23], [0.78, 0, 0], [-1.21, -0.65, 0.23], [0.75, 0, 0], [-0.36, 0, 0.10], [0.35, 0, -0.09], -0.06),
  // Shuriken Fan: both forearms snap from the ribs into a wide fan throw.
  nyx_throw_w: P([0.08, -0.41, 0], [-0.05, 0.33, 0], [-0.54, -1.0, -0.33], [1.17, 0, 0], [-0.60, 0.95, 0.34], [1.14, 0, 0], [-0.29, 0, 0.13], [0.32, 0, -0.12], -0.07),
  nyx_throw_s: P([0.29, 0.11, 0], [-0.07, -0.05, 0], [-1.70, -0.52, -0.10], [1.35, 0, 0], [-1.66, 0.56, 0.13], [1.35, 0, 0], [-0.52, 0, 0.13], [0.50, 0, -0.13], -0.10),
  // Phantom Rush: low coiled posture, driving double-dagger cut, immediate compact recover.
  nyx_rush_w: P([0.49, -0.52, 0], [-0.27, 0.37, 0], [-0.31, -0.95, -0.38], [1.18, 0, 0], [-0.33, 0.90, 0.42], [1.18, 0, 0], [-0.71, 0, 0.17], [0.54, 0, -0.14], -0.19),
  nyx_rush_s: P([0.30, 0.41, -0.02], [-0.14, -0.30, 0], [-1.70, 0.71, -0.14], [1.36, 0, 0], [-1.66, -0.72, 0.15], [1.34, 0, 0], [-0.87, 0, 0.17], [0.63, 0, -0.15], -0.12),
};

// Bow in the left hand. The bow arm points at the target; the right hand draws the string.
const BOW: Record<string, Pose> = {
  // Ready: torso turned toward the target, bow low and forward, string hand by the hip,
  // front knee soft, feet staggered.
  idle: P([0.06, -0.4, 0], [0, 0.35, 0], [-0.45, 0.2, -0.3], [0, 0, 0], [-0.7, -0.15, 0.25], [0, 0, 0], [-0.3, 0, 0.1], [0.25, 0, -0.08], -0.05),
  // Bow held diagonally across the chest, knees bent.
  block: P([0.18, -0.2, 0], [0.12, 0.15, 0], [-1.05, 0.45, -0.25], [0, 0, 0], [-1.3, 0.45, 0.1], [0, 0, 0], [-0.45, 0, 0.1], [0.4, 0, -0.1], -0.13),
  // Draw: side-on, bow arm straight at the target, head turned to aim.
  bow_w: P([0.04, -0.95, 0], [0.02, 0.9, 0], [-1.55, 0.75, -0.2], [0, 0, 0], [-1.55, -0.12, 0], [0, 0, 0], [-0.4, 0, 0.1], [0.38, 0, -0.1], -0.08),
  // Release: string hand flies back past the jaw, chest opens a touch.
  bow_s: P([0.0, -0.85, 0], [0.02, 0.85, 0], [-1.2, -0.45, -0.9], [0, 0, 0], [-1.55, -0.12, 0], [0, 0, 0], [-0.4, 0, 0.1], [0.38, 0, -0.1], -0.08),
  charge: P([0.02, -1.0, 0], [0.02, 0.95, 0], [-1.5, 1.0, -0.2], [0, 0, 0], [-1.55, -0.12, 0], [0, 0, 0], [-0.5, 0, 0.12], [0.45, 0, -0.12], -0.12),
  // Sky volley: lean back, chest and bow up 65+ degrees.
  rain_w: P([-0.32, -0.5, 0], [-0.55, 0.45, 0], [-2.2, 0.5, -0.2], [0, 0, 0], [-2.55, -0.15, 0], [0, 0, 0], [-0.35, 0, 0.1], [0.4, 0, -0.1], -0.08),
  rain_s: P([-0.25, -0.45, 0], [-0.5, 0.4, 0], [-2.0, -0.4, -0.8], [0, 0, 0], [-2.5, -0.15, 0], [0, 0, 0], [-0.35, 0, 0.1], [0.4, 0, -0.1], -0.06),
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
/** Adds knee bend to a pose. */
const K = (p: Pose, l: number, r: number): Pose => ({ ...p, knee: [l, r] });
// Kicker: a relaxed, almost casual upper body (hands low and slightly behind, never a boxing
// guard), weight on the rear leg, asymmetric stance; the legs do all the work. Kicks go
// chamber (knee up, shin folded) -> snap -> recoil, arms swinging out only for balance.
const EASY_R: Vec3 = [0.3, 0.15, -0.12];
const EASY_L: Vec3 = [0.3, -0.15, 0.12];
const OUT_R: Vec3 = [-0.3, 0.2, -0.9];
const OUT_L: Vec3 = [-0.3, -0.2, 0.9];
const NO: Vec3 = [0, 0, 0];
const KICKS: Record<string, Pose> = {
  idle: K(P([-0.05, -0.3, 0], [0.1, 0.25, 0.04], EASY_R, NO, EASY_L, NO, [-0.18, 0, 0.08], [0.2, 0, -0.06], -0.04), 0.08, 0.22),
  // Leg check: knee up as a barrier, upper body calm.
  block: K(P([-0.08, -0.25, 0], [0.08, 0.2, 0], [0.1, 0.1, -0.35], NO, [0.1, -0.1, 0.35], NO, [-1.35, 0, 0.05], [0.2, 0, -0.08], -0.05), 1.75, 0.3),
  // SWORD_AND_CYCLONE_V1: actual alternate-leg turning kicks for Kira Z.
  cy1_w: K(P([-0.12, -0.72, 0], [0, 0.65, 0], OUT_R, NO, OUT_L, NO, [0.12, 0, 0], [-1.31, 0.55, 0], -0.15), 0.48, 1.55),
  cy1_s: K(P([-0.22, 0.68, 0], [0, -0.5, 0], OUT_R, NO, OUT_L, NO, [0.15, 0, 0], [-1.93, -0.75, 0], -0.12), 0.45, 0.06),
  cy2_s: K(P([-0.28, -0.74, 0], [0, 0.58, 0], OUT_R, NO, OUT_L, NO, [-1.94, 0.68, 0], [0.21, 0, 0], -0.13), 0.06, 0.45),
  cy3_s: K(P([-0.38, 0.8, -0.05], [0.1, -0.66, 0], OUT_R, NO, OUT_L, NO, [0.15, 0, 0], [-2.17, 0.85, 0.06], -0.16), 0.4, 0.02),
  // Front snap kick (right).
  kk1_w: K(P([-0.08, -0.2, 0], [0.08, 0.2, 0], EASY_R, NO, EASY_L, NO, [0.15, 0, 0.05], [-1.45, 0, -0.05], -0.05), 0.3, 1.9),
  kk1_s: K(P([-0.3, -0.2, 0], [0.15, 0.2, 0], [-0.1, 0.2, -0.6], NO, [-0.1, -0.2, 0.5], NO, [0.2, 0, 0.05], [-1.7, 0, 0], -0.08), 0.28, 0.08),
  // Roundhouse (left): hips turn over, knee folded, then whip out; arms open for balance.
  kk2_w: K(P([-0.05, -0.75, 0], [0, 0.7, 0], EASY_R, NO, OUT_L, NO, [-1.25, 1.1, 0], [0.15, 0, -0.05], -0.06), 1.7, 0.3),
  kk2_s: K(P([-0.25, 0.75, 0], [0, -0.6, 0], OUT_R, NO, OUT_L, NO, [-1.6, -0.6, 0], [0.15, 0, -0.05], -0.08), 0.12, 0.28),
  // Spinning back kick (right): head turns first, heel chambered, then driven straight back.
  kk3_w: K(P([0, 0.95, 0], [0, -0.85, 0], OUT_R, NO, EASY_L, NO, [0.1, 0, 0.05], [-1.3, -1.2, 0], -0.1), 0.45, 1.6),
  kk3_s: K(P([0.2, -0.95, 0], [0, 0.85, 0], OUT_R, NO, OUT_L, NO, [0.15, 0, 0.05], [-1.9, 0.6, 0], -0.1), 0.3, 0.05),
  // High vertical kick (left): straight leg to the sky, torso counter-leans back.
  kk4_w: K(P([-0.35, 0, 0], [-0.2, 0, 0], OUT_R, NO, EASY_L, NO, [-2.75, 0.15, 0], [0.2, 0, -0.05], -0.03), 0.08, 0.3),
  kk4_s: K(P([0.35, 0, 0], [-0.2, 0, 0], OUT_R, NO, OUT_L, NO, [-0.55, 0, 0.05], [0.3, 0, -0.05], -0.2), 0.3, 0.45),
  charge: K(P([0.35, -0.3, 0], [-0.25, 0.3, 0], [0.4, 0.1, -0.3], NO, [0.4, -0.1, 0.3], NO, [-0.75, 0, 0.1], [0.55, 0, -0.1], -0.28), 0.2, 0.25),
  // Airborne: one leg long, one folded, arms spread loose.
  fly_s: K(P([-0.4, 0.2, 0.1], [0.2, -0.1, 0], [-0.4, 0, -1.2], NO, [-0.4, 0, 1.2], NO, [-1.3, 0, 0.05], [-1.65, 0, -0.05], 0), 1.8, 0.0),
};

// Feral dual-sickle stances. Cross-body rotation is led by the chest and shoulders;
// the VRM rig adds a braced, low stance and lagging hands when a VRM is fitted.
const SICKLE: Record<string, Pose> = {
  idle: P([0.27, -0.24, 0.08], [-0.14, 0.27, -0.06], [-0.54, 0.32, -0.28], [0.28, 0.05, 0.12], [-0.82, -0.46, 0.32], [0.4, -0.06, -0.16], [-0.42, 0, 0.10], [0.36, 0, -0.1], -0.16),
  block: P([0.33, 0, 0], [-0.18, 0, 0], [-1.25, 0.55, -0.12], [0.35, 0, 0], [-1.35, -0.45, 0.12], [0.35, 0, 0], [-0.6, 0, 0.10], [0.48, 0, -0.1], -0.22),
  vr1_w: P([0.24, -0.68, 0], [-0.12, 0.55, 0], [-0.95, -1.1, -0.22], [0.55, 0, 0], [-0.62, -0.3, 0.30], [0.35, 0, 0], [-0.48, 0, 0.09], [0.38, 0, -0.08], -0.17),
  vr1_s: P([0.33, 0.5, 0], [-0.16, -0.43, 0], [-1.5, 0.92, -0.1], [0.2, 0, 0], [-0.65, -0.3, 0.30], [0.3, 0, 0], [-0.6, 0, 0.12], [0.5, 0, -0.1], -0.19),
  vr2_w: P([0.24, 0.65, 0], [-0.12, -0.58, 0], [-0.68, 0.2, -0.25], [0.4, 0, 0], [-0.9, 1.1, 0.24], [0.55, 0, 0], [-0.45, 0, 0.10], [0.4, 0, -0.10], -0.17),
  vr2_s: P([0.34, -0.5, 0], [-0.15, 0.42, 0], [-0.74, 0.25, -0.24], [0.35, 0, 0], [-1.5, -0.95, 0.1], [0.15, 0, 0], [-0.6, 0, 0.10], [0.5, 0, -0.10], -0.19),
  vr3_w: P([0.17, -0.54, -0.12], [-0.13, 0.46, 0], [-1.8, -0.88, -0.15], [0.52, 0, 0], [-1.8, 0.75, 0.19], [0.52, 0, 0], [-0.48, 0, 0.1], [0.48, 0, -0.10], -0.2),
  vr3_s: P([0.38, 0.55, 0.12], [-0.22, -0.48, 0], [-1.5, 0.7, -0.3], [0.16, 0, 0], [-1.5, -0.66, 0.28], [0.16, 0, 0], [-0.7, 0, 0.12], [0.5, 0, -0.11], -0.23),
  vr4_w: P([0.2, 0, -0.15], [-0.22, 0, 0], [-2.6, -0.3, -0.2], [0.75, 0, 0], [-2.5, 0.3, 0.2], [0.75, 0, 0], [-0.55, 0, 0.1], [0.55, 0, -0.10], -0.19),
  vr4_s: P([0.47, 0, 0.14], [-0.25, 0, 0], [-1.25, 0.65, -0.2], [0.15, 0, 0], [-1.2, -0.65, 0.2], [0.15, 0, 0], [-0.7, 0, 0.12], [0.60, 0, -0.1], -0.23),
  vrh_w: P([0.49, -0.4, 0], [-0.27, 0.36, 0], [-0.3, -0.9, -0.4], [0.8, 0, 0], [-0.3, 0.9, 0.4], [0.8, 0, 0], [-0.7, 0, 0.12], [0.6, 0, -0.1], -0.27),
  vrh_s: P([0.34, 0.4, 0.06], [-0.23, -0.35, 0], [-1.7, 0.74, 0], [0.22, 0, 0], [-1.7, -0.74, 0], [0.22, 0, 0], [-0.8, 0, 0.13], [0.7, 0, -0.13], -0.26),
  vrd_w: P([0.51, -0.34, 0], [-0.35, 0.27, 0], [0.22, 0.32, -0.47], [0.35, 0, 0], [0.26, -0.32, 0.47], [0.35, 0, 0], [-0.78, 0, 0.12], [0.64, 0, -0.12], -0.29),
  vrd_s: P([0.56, 0.23, 0], [-0.4, -0.14, 0], [-1.72, 0.28, 0.05], [0.11, 0, 0], [-1.7, -0.31, -0.05], [0.11, 0, 0], [-0.78, 0, 0.12], [0.7, 0, -0.12], -0.27),
  vrx_w: P([0.32, -0.8, -0.1], [-0.2, 0.75, 0], [-0.56, -0.88, -0.4], [0.7, 0, 0], [-0.54, 0.88, 0.4], [0.7, 0, 0], [-0.56, 0, 0.1], [0.55, 0, -0.1], -0.22),
  vrx_s: P([0.43, 0.75, 0.1], [-0.24, -0.62, 0], [-1.2, 0.85, -0.5], [0.45, 0, 0], [-1.2, -0.84, 0.5], [0.45, 0, 0], [-0.7, 0, 0.1], [0.65, 0, -0.1], -0.26),
  vrc_w: P([0.62, -0.6, 0], [-0.31, 0.55, 0], [-2.5, -0.4, -0.24], [0.6, 0, 0], [-2.46, 0.5, 0.24], [0.6, 0, 0], [-0.8, 0, 0.12], [0.7, 0, -0.12], -0.3),
  vrc_s: P([0.54, 0.6, 0], [-0.3, -0.55, 0], [-1.36, 0.8, -0.2], [0.2, 0, 0], [-1.32, -0.8, 0.2], [0.2, 0, 0], [-0.8, 0, 0.12], [0.7, 0, -0.12], -0.28),
  // VEYR_BLOODLUST_CARRION_V7: distinct alternating hand and hip rotations for each beat.
  vrv1_s: P([0.30, 0.66, -0.10], [-0.14, -0.48, 0], [-1.62, 0.88, -0.24], [0.19, 0, 0], [-0.92, -0.43, 0.30], [0.32, 0, 0], [-0.68, 0, 0.14], [0.43, 0, -0.12], -0.21),
  vrv2_s: P([0.38, -0.68, 0.12], [-0.19, 0.52, 0], [-0.94, 0.43, -0.28], [0.28, 0, 0], [-1.76, -0.94, 0.22], [0.18, 0, 0], [-0.38, 0, 0.12], [0.69, 0, -0.10], -0.22),
  vrv3_s: P([0.49, 0.52, -0.16], [-0.23, -0.38, 0], [-1.84, 0.27, -0.40], [0.42, 0, 0], [-1.98, -0.23, 0.42], [0.45, 0, 0], [-0.74, 0, 0.16], [0.57, 0, -0.15], -0.25),
  vrv4_s: P([0.31, -0.73, 0.15], [-0.13, 0.57, 0], [-2.05, 0.91, -0.35], [0.24, 0, 0], [-1.54, -0.91, 0.35], [0.24, 0, 0], [-0.47, 0, 0.14], [0.77, 0, -0.16], -0.27),
  vrv5_s: P([0.54, 0.40, 0.12], [-0.27, -0.30, 0], [-1.24, 0.86, -0.13], [0.14, 0, 0], [-1.34, -0.86, 0.13], [0.14, 0, 0], [-0.86, 0, 0.16], [0.65, 0, -0.12], -0.28),
  vrv_w: P([0.32, -0.45, -0.1], [-0.18, 0.4, 0], [-1.7, -0.65, -0.1], [0.55, 0, 0], [-1.7, 0.65, 0.1], [0.55, 0, 0], [-0.55, 0, 0.1], [0.5, 0, -0.1], -0.2),
  vrv_s: P([0.48, 0.4, 0.1], [-0.2, -0.35, 0], [-1.25, 0.8, -0.12], [0.18, 0, 0], [-1.25, -0.8, 0.12], [0.18, 0, 0], [-0.7, 0, 0.1], [0.6, 0, -0.1], -0.26),
  charge: P([0.53, -0.4, 0], [-0.3, 0.37, 0], [-0.4, -0.9, -0.4], [0.8, 0, 0], [-0.35, 0.9, 0.4], [0.8, 0, 0], [-0.65, 0, 0.12], [0.6, 0, -0.12], -0.26),
};

// Storm Glaive: coordinated two-hand weapon cuts, a bladed stance, and wide reverse sweeps.
const GLAIVE: Record<string, Pose> = {
  ...twoHanded(KNIGHT),
  idle: P([0.02, -0.20, 0.02], [0, 0.20, 0], [-0.70, 0.12, -0.23], [-0.08, 0, 0.15], [-0.82, 0.46, 0.1], [0, 0, 0], [-0.22, 0, 0.05], [0.25, 0, -0.06], -0.045),
  block: P([0.12, 0, 0], [0.03, 0, 0], [-1.12, 0.3, -0.15], [0.14, 0, 0], [-1.0, -0.3, 0.2], [0, 0, 0], [-0.35, 0, 0.06], [0.35, 0, -0.06], -0.08),
  gl1_w: P([0.10, -0.44, -0.06], [0, 0.36, 0], [-1.14, -0.72, -0.30], [0.46, 0, 0], [-1.30, -0.31, 0.22], [0.20, 0, 0], [-0.38, 0, 0.07], [0.22, 0, -0.08], -0.09),
  gl1_s: P([0.16, 0.22, 0.03], [0, -0.14, 0], [-1.36, 0.32, -0.12], [0.08, 0, 0], [-1.48, 0.20, 0.17], [0.02, 0, 0], [-0.40, 0, 0.06], [0.44, 0, -0.05], -0.10),
  gl2_w: P([0.12, 0.60, 0.07], [0, -0.42, 0], [-1.54, 0.68, 0.20], [0.15, 0, 0], [-1.37, 0.84, 0.26], [0.06, 0, 0], [-0.12, 0, 0.11], [0.43, 0, -0.10], -0.10),
  gl2_s: P([0.05, -0.66, -0.10], [0, 0.44, 0], [-1.00, -0.86, -0.37], [0.07, 0, 0], [-1.62, -0.38, -0.24], [0.18, 0, 0], [-0.39, 0, 0.10], [0.18, 0, -0.10], -0.14),
  gl3_w: P([-0.18, -0.38, 0.12], [0, 0.30, 0], [-2.35, -0.78, 0.16], [0.44, 0, 0], [-2.05, -0.34, -0.16], [0.22, 0, 0], [-0.35, 0, 0.14], [0.29, 0, -0.07], -0.13),
  gl3_s: P([0.04, 0.58, -0.12], [0, -0.42, 0], [-0.88, 0.62, 0.14], [0.08, 0, 0], [-1.05, 0.34, -0.22], [0.06, 0, 0], [-0.41, 0, 0.10], [0.43, 0, -0.07], -0.10),
  gl4_w: P([0.12, 0.92, 0.12], [0, -0.63, 0], [-1.94, 1.05, 0.16], [0.58, 0, 0], [-1.86, 0.66, -0.10], [0.26, 0, 0], [-0.42, 0, 0.11], [0.39, 0, -0.11], -0.17),
  gl4_s: P([0.24, -1.04, -0.08], [-0.14, 0.66, 0], [-1.22, -1.16, -0.12], [0.10, 0, 0], [-1.48, -0.86, 0.27], [0.12, 0, 0], [-0.58, 0, 0.08], [0.42, 0, -0.11], -0.16),
  gl5_w: P([-0.12, 0.76, -0.06], [-0.06, -0.52, 0], [-2.40, 0.62, -0.22], [0.35, 0, 0], [-2.18, 0.34, 0.16], [0.20, 0, 0], [-0.54, 0, 0.1], [0.48, 0, -0.1], -0.19),
  gl5_s: P([0.29, -0.84, 0.04], [-0.13, 0.57, 0], [-1.18, -1.18, -0.17], [0.18, 0, 0], [-1.46, -0.74, 0.21], [0.13, 0, 0], [-0.62, 0, 0.11], [0.40, 0, -0.1], -0.17),
  glx_turn: P([0.32, 0.88, 0.06], [-0.18, -0.67, 0], [-1.61, 1.07, 0.12], [0.20, 0, 0], [-1.87, 0.77, -0.17], [0.12, 0, 0], [-0.62, 0, 0.08], [0.48, 0, -0.1], -0.16),
  glc_launch: P([-0.27, -0.48, 0.06], [0.12, 0.27, 0], [-2.17, -0.42, -0.06], [0.24, 0, 0], [-1.99, -0.52, 0.11], [0.16, 0, 0], [-0.32, 0, 0.13], [0.31, 0, -0.09], -0.10),
  glc_finish: P([-0.26, 0.77, -0.05], [0.11, -0.52, 0], [-1.54, 0.85, -0.12], [0.22, 0, 0], [-1.79, 0.61, 0.23], [0.16, 0, 0], [-0.97, 0, 0.14], [0.18, 0, -0.09], -0.19),
  glh_w: P([-0.07, -0.8, 0], [0.05, 0.63, 0], [-2.7, -0.66, -0.06], [0.75, 0, 0], [-2.65, -0.12, 0.14], [0.48, 0, 0], [-0.55, 0, 0.12], [0.38, 0, -0.09], -0.15),
  glh_s: P([0.36, 0.95, 0], [-0.14, -0.62, 0], [-0.8, 1.3, 0], [0.22, 0, 0], [-1.05, 0.75, 0.16], [0.18, 0, 0], [-0.6, 0, 0.1], [0.48, 0, -0.1], -0.18),
  glz_w: P([0.25, -0.76, -0.08], [-0.1, 0.6, 0], [-0.8, -0.8, -0.3], [0.3, 0, 0], [-1.05, -0.3, 0.3], [0.2, 0, 0], [-0.6, 0, 0.1], [0.6, 0, -0.1], -0.14),
  glz_s: P([0.15, 0.87, 0], [-0.12, -0.6, 0], [-1.65, 1.1, -0.13], [0.3, 0, 0], [-1.6, 0.7, 0.15], [0.2, 0, 0], [-0.55, 0, 0.1], [0.5, 0, -0.1], -0.15),
  glx_w: P([-0.06, 0.05, 0], [0, 0.05, 0], [-1.0, 0.6, -0.4], [0.5, 0, 0], [-1.1, 0.1, 0.4], [0.1, 0, 0], [-0.45, 0, 0.1], [0.4, 0, -0.1], -0.09),
  glc_w: P([-0.12, -0.55, 0], [0.04, 0.47, 0], [-2.5, -0.66, -0.04], [0.8, 0, 0], [-2.3, -0.2, 0.12], [0.4, 0, 0], [-0.55, 0, 0.11], [0.52, 0, -0.1], -0.18),
  glc_s: P([0.31, 0.68, 0], [-0.15, -0.45, 0], [-1.05, 1.1, -0.08], [0.2, 0, 0], [-1.2, 0.48, 0.14], [0.16, 0, 0], [-0.58, 0, 0.1], [0.49, 0, -0.1], -0.18),
  charge: P([-0.06, -0.7, 0], [0, 0.48, 0], [-2.4, -0.7, -0.15], [0.8, 0, 0], [-2.4, -0.2, 0.1], [0.4, 0, 0], [-0.5, 0, 0.1], [0.4, 0, -0.1], -0.12),
};

// ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — tight thrusts, alternate rear-blade strike,
// two-hand rail throw, one-hand magnetic control and elevated arsenal summon.
  // ZENITH_V6_SAFE_RECOVERY_20261108: spear style without removing other kits.
const ZENITH: Record<string, Pose> = {
  ...GLAIVE,
  idle: P([0.01,-0.12,0], [-0.01,0.10,0], [-0.92,-0.04,-0.30], [0.16,0,0.06], [-0.58,-0.62,0.20], [0.08,0,0.02], [-0.26,0,0.08], [0.30,0,-0.08], -0.07),
  block: P([0.10,-0.05,0], [0.02,0.04,0], [-1.10,0.08,-0.28], [0.13,0,0.06], [-0.86,-0.50,0.26], [0.10,0,0.02], [-0.36,0,0.08], [0.40,0,-0.08], -0.09),
  zn1_w: P([0.08,-0.36,0], [0,0.22,0], [-1.26,-0.26,-0.28], [0.24,0,0.06], [-0.72,-0.82,0.18], [0.10,0,0.02], [-0.34,0,0.08], [0.29,0,-0.07], -0.10),
  zn1_s: P([0.22,0.18,0], [0,-0.12,0], [-1.72,0.02,-0.22], [0.04,0,0.06], [-1.06,-0.58,0.18], [0.05,0,0.02], [-0.54,0,0.09], [0.43,0,-0.08], -0.13),
  zn2_w: P([0.12,0.28,0.02], [0,-0.22,0], [-1.03,0.32,-0.10], [0.20,0,0.14], [-0.60,-0.44,0.36], [0.08,0,0.02], [-0.23,0,0.09], [0.34,0,-0.07], -0.09),
  zn2_s: P([0.22,-0.14,0], [0,0.14,0], [-1.60,-0.10,-0.17], [0.05,0,0.10], [-1.05,-0.36,0.24], [0.06,0,0.02], [-0.45,0,0.10], [0.36,0,-0.09], -0.12),
  zn3_w: P([0.05,-0.28,-0.03], [0,0.20,0], [-0.98,-0.56,-0.34], [0.18,0,-0.04], [-0.62,-0.72,0.18], [0.10,0,0.02], [-0.33,0,0.11], [0.36,0,-0.07], -0.10),
  zn3_s: P([0.18,0.20,0], [0,-0.17,0], [-1.46,-0.18,-0.30], [0.04,0,-0.02], [-0.96,-0.64,0.20], [0.04,0,0.02], [-0.51,0,0.10], [0.42,0,-0.08], -0.13),
  // Fourth thrust: short diagonal spearhead redirect, not a rear-end blade attack.
  zn4_w: P([0.10,0.20,0], [0,-0.18,0], [-0.82,0.04,-0.36], [0.20,0,0.05], [-0.78,-0.36,0.28], [0.12,0,-0.02], [-0.27,0,0.10], [0.31,0,-0.07], -0.09),
  zn4_s: P([0.19,-0.18,0.03], [0,0.15,0], [-1.42,-0.20,-0.28], [0.04,0,0.05], [-1.08,-0.50,0.16], [0.05,0,-0.02], [-0.53,0,0.11], [0.45,0,-0.08], -0.13),
  zn5_w: P([-0.02,-0.46,0], [0.02,0.30,0], [-1.18,-0.42,-0.32], [0.30,0,0.03], [-0.86,-0.76,0.22], [0.13,0,0.02], [-0.50,0,0.12], [0.30,0,-0.08], -0.13),
  zn5_s: P([0.30,0.34,0], [-0.08,-0.18,0], [-1.86,-0.06,-0.30], [0.04,0,0.03], [-1.18,-0.66,0.20], [0.04,0,0.02], [-0.73,0,0.13], [0.52,0,-0.09], -0.18),
  // Raised hand: call the physical spear above her before launching it.
  znh_w: P([-0.05,0.03,0], [-0.18,0.01,0], [-2.55,0.06,-0.32], [0.24,0,0.10], [-2.25,0.03,0.31], [0.19,0,0], [-0.31,0,0.09], [0.38,0,-0.08], -0.09),
  // Release the overhead spear, right arm extends downrange with follow-through.
  znh_s: P([0.24,0.19,0], [-0.08,-0.16,0], [-1.73,0.33,-0.10], [0.05,0,0], [-1.38,-0.24,0.20], [0.17,0,0], [-0.59,0,0.12], [0.46,0,-0.08], -0.14),
  znz_w: P([0.02,-0.24,0], [0,0.18,0], [-2.02,-0.32,-0.58], [0.42,0,0.10], [-0.74,-0.24,0.34], [0.14,0,0.02], [-0.40,0,0.09], [0.34,0,-0.08], -0.12),
  znz_s: P([0.30,0.20,0], [-0.10,-0.10,0], [-0.60,0.02,-0.08], [0.04,0,0.02], [-1.76,-0.10,0.22], [0.08,0,0.02], [-0.67,0,0.10], [0.48,0,-0.10], -0.17),
  znx_w: P([0.08,-0.22,0], [0,0.16,0], [-1.00,-0.30,-0.30], [0.22,0,0.06], [-0.68,-0.62,0.22], [0.10,0,0.02], [-0.40,0,0.09], [0.38,0,-0.08], -0.10),
  znx_s: P([0.18,0.10,0], [0,-0.06,0], [-1.42,-0.06,-0.24], [0.06,0,0.05], [-0.98,-0.44,0.20], [0.06,0,0.02], [-0.56,0,0.10], [0.42,0,-0.09], -0.12),
  // Twin blades: alternating left/right cuts, pivoting hips, then an X-shaped cross finisher.
  znt1_w: P([0.09,-0.35,0], [0,0.19,0], [-1.15,-0.58,0.2], [0.34,0,-0.20], [-1.2,0.37,-0.12], [0.3,0,0.16], [-0.29,0,0.14], [0.38,0,-0.12], -0.10),
  znt1_s: P([0.2,0.43,0], [0,-0.28,0], [-1.65,0.73,0.34], [0.14,0,-0.60], [-1.16,-0.25,-0.22], [0.26,0,0.35], [-0.61,0,0.12], [0.34,0,-0.06], -0.15),
  znt2_w: P([0.06,0.39,0], [0,-0.23,0], [-1.17,0.32,-0.1], [0.3,0,-0.25], [-1.15,-0.69,0.21], [0.31,0,0.32], [-0.22,0,0.11], [0.44,0,-0.09], -0.10),
  znt2_s: P([0.18,-0.43,0], [0,0.31,0], [-1.12,-0.31,-0.26], [0.23,0,0.15], [-1.72,0.82,-0.29], [0.11,0,0.55], [-0.36,0,0.06], [0.50,0,-0.12], -0.16),
  znt3_w: P([0.14,-0.22,0], [0,0.19,0], [-1.75,-0.55,0.12], [0.16,0,0.16], [-1.36,0.44,-0.16], [0.22,0,-0.18], [-0.42,0,0.16], [0.36,0,-0.07], -0.13),
  znt3_s: P([0.20,0.27,0], [0,-0.16,0], [-1.32,0.48,-0.27], [0.21,0,-0.55], [-1.87,-0.42,0.20], [0.11,0,0.33], [-0.62,0,0.12], [0.40,0,-0.08], -0.17),
  znt4_w: P([0.09,0.23,0], [0,-0.19,0], [-1.15,0.29,0.15], [0.29,0,0.26], [-1.44,-0.41,0.12], [0.24,0,-0.19], [-0.22,0,0.07], [0.48,0,-0.11], -0.12),
  znt4_s: P([0.24,-0.34,0], [0,0.21,0], [-1.75,-0.57,-0.12], [0.10,0,0.50], [-1.64,0.55,-0.18], [0.16,0,-0.48], [-0.63,0,0.14], [0.38,0,-0.08], -0.17),
  znt5_w: P([-0.06,-0.13,0], [0,0.13,0], [-1.17,-0.58,-0.30], [0.3,0,-0.23], [-1.18,0.58,0.30], [0.27,0,0.23], [-0.44,0,0.12], [0.43,0,-0.11], -0.10),
  znt5_s: P([0.34,0.10,0], [-0.14,0,0], [-1.75,0.17,-0.56], [0.13,0,0.57], [-1.75,-0.17,0.56], [0.13,0,-0.57], [-0.75,0,0.15], [0.55,0,-0.14], -0.19),
  zntx_s: P([0.26,0.06,0], [0,0,0], [-1.62,0.12,-0.47], [0.12,0,0.48], [-1.62,-0.12,0.47], [0.12,0,-0.48], [-0.58,0,0.14], [0.51,0,-0.11], -0.16),
  // The spear slams back into a raised palm; shoulders compress then settle.
  zncatch_w: P([-0.12,-0.17,0], [0.10,0.10,0], [-2.04,-0.36,-0.25], [0.44,0,0.35], [-1.28,0.49,0.28], [0.24,0,-0.22], [-0.45,0,0.09], [0.35,0,-0.11], -0.11),
  zncatch_s: P([0.16,0.20,0], [-0.05,-0.12,0], [-1.42,0.13,-0.12], [0.25,0,-0.12], [-1.3,-0.32,0.20], [0.18,0,0.20], [-0.42,0,0.10], [0.42,0,-0.08], -0.11),
  znc_w: P([0.04,-0.10,0], [0,0.08,0], [-0.50,-0.18,-0.74], [0.16,0,0.12], [-1.22,-0.32,0.12], [0.18,0,0.02], [-0.30,0,0.07], [0.31,0,-0.08], -0.06),
  znc_s: P([0.14,0.14,0], [0,-0.10,0], [-0.58,0.18,-0.92], [0.08,0,0.12], [-1.20,-0.02,0.16], [0.12,0,0.02], [-0.42,0,0.10], [0.38,0,-0.09], -0.08),
  znv_w: P([-0.08,-0.06,0], [0,0.08,0], [-2.36,-0.02,-0.30], [0.14,0,0.04], [-1.00,-0.42,0.26], [0.14,0,0.02], [-0.46,0,0.12], [0.43,0,-0.08], -0.10),
  znv_s: P([0.16,0.12,0], [0,-0.10,0], [-2.54,0.10,-0.22], [0.08,0,0.04], [-0.60,-0.12,0.20], [0.10,0,0.02], [-0.54,0,0.09], [0.49,0,-0.09], -0.10),
};


// NYTHERA_GRAVITY_REAPER_INSTALL_V1 — choreography: gather → suspend → sentence.
// Unlike glaives, these swings are single long arcs with two-hand grips and a settled foot plant.
const GRAVITY_SCYTHE: Record<string, Pose> = {
  ...GLAIVE,
  idle: P([0.025,-0.24,0.01],[0.0,0.20,0.01],[-0.89,-0.06,-0.16],[0.20,0,-0.12],[-0.97,0.18,0.20],[0.17,0,0.10],[-0.22,0,0.12],[0.27,0,-0.10],-0.06),
  block: P([0.13,-0.09,0],[0,0.06,0],[-1.37,0.14,-0.19],[0.22,0,-0.10],[-1.42,-0.16,0.23],[0.18,0,0.08],[-0.40,0,0.13],[0.41,0,-0.11],-0.12),
  jump: P([-0.10,-0.06,0.03],[0.04,0.09,0],[-0.88,0.10,-0.26],[0.15,0,-0.13],[-1.08,-0.12,0.25],[0.12,0,0.12],[-0.68,0,0.15],[-0.45,0,-0.13],0.03),
  gr1_w: P([0.11,-0.69,-0.07],[0,0.39,0],[-0.86,-0.74,-0.23],[0.26,0,-0.20],[-1.04,-0.47,0.18],[0.16,0,0.14],[-0.35,0,0.10],[0.40,0,-0.08],-0.09),
  gr1_s: P([0.16,0.70,0.06],[-0.04,-0.35,0],[-1.41,0.79,-0.15],[0.12,0,0.38],[-1.32,0.61,0.25],[0.08,0,0.16],[-0.45,0,0.12],[0.40,0,-0.07],-0.11),
  gr2_w: P([0.10,0.68,0.03],[0,-0.34,0],[-1.32,0.84,0.12],[0.23,0,0.22],[-1.25,0.70,0.13],[0.18,0,0.06],[-0.28,0,0.12],[0.34,0,-0.10],-0.09),
  gr2_s: P([0.18,-0.78,-0.05],[-0.09,0.48,0],[-1.28,-0.92,-0.12],[0.06,0,-0.34],[-1.43,-0.76,0.20],[0.06,0,-0.14],[-0.48,0,0.14],[0.44,0,-0.09],-0.12),
  gr3_w: P([0.29,-0.48,-0.03],[-0.16,0.32,0],[-0.66,-0.71,-0.37],[0.45,0,-0.30],[-0.85,-0.47,0.26],[0.32,0,0.04],[-0.62,0,0.10],[0.58,0,-0.07],-0.18),
  gr3_s: P([-0.23,0.31,0.05],[0.14,-0.10,0],[-2.53,0.30,-0.12],[0.18,0,0.12],[-2.28,0.27,0.11],[0.14,0,0.08],[-0.52,0,0.14],[0.36,0,-0.11],-0.12),
  gr4_w: P([0.08,-1.02,0],[0,0.58,0],[-1.04,-1.06,-0.16],[0.35,0,-0.24],[-1.17,-0.83,0.20],[0.28,0,-0.12],[-0.47,0,0.12],[0.46,0,-0.09],-0.16),
  gr4_s: P([0.18,1.08,0.06],[-0.09,-0.66,0],[-1.72,1.03,-0.04],[0.06,0,0.46],[-1.77,0.81,0.24],[0.07,0,0.29],[-0.68,0,0.13],[0.49,0,-0.11],-0.15),
  // V3 reaper chain: reverse hooked cut across the body, then a wide final reaping lunge.
  gr5_w: P([0.11,0.74,0.05],[-0.04,-0.43,0],[-1.36,0.91,0.12],[0.39,0,0.24],[-1.18,0.66,0.15],[0.27,0,-0.13],[-0.39,0,0.11],[0.41,0,-0.09],-0.12),
  gr5_s: P([0.23,-0.76,-0.07],[-0.11,0.47,0],[-1.56,-0.95,-0.13],[0.10,0,-0.43],[-1.41,-0.70,0.20],[0.10,0,-0.28],[-0.52,0,0.12],[0.46,0,-0.08],-0.16),
  gr6_w: P([-0.22,-0.90,0.04],[0.11,0.52,0],[-2.03,-1.05,-0.18],[0.46,0,-0.15],[-1.92,-0.81,0.16],[0.32,0,-0.11],[-0.62,0,0.15],[0.50,0,-0.11],-0.19),
  gr6_s: P([0.41,1.08,0.08],[-0.18,-0.60,0],[-0.70,1.10,-0.14],[0.07,0,0.54],[-0.89,0.95,0.17],[0.06,0,0.36],[-0.83,0,0.16],[0.59,0,-0.10],-0.23),
  grh_w: P([-0.22,-0.48,-0.08],[0.14,0.31,0],[-2.60,-0.24,-0.17],[0.56,0,-0.06],[-2.47,-0.29,0.16],[0.43,0,0.06],[-0.55,0,0.16],[0.53,0,-0.12],-0.20),
  grh_s: P([0.51,0.34,0.10],[-0.24,-0.19,0],[-0.61,0.42,-0.29],[0.18,0,0.14],[-0.73,0.23,0.22],[0.13,0,-0.10],[-0.84,0,0.16],[0.62,0,-0.11],-0.26),
  grz_w: P([0.10,-0.77,-0.09],[-0.02,0.46,0],[-1.22,-1.06,-0.23],[0.55,0,-0.29],[-1.14,-0.68,0.15],[0.29,0,-0.19],[-0.43,0,0.12],[0.43,0,-0.10],-0.13),
  grz_s: P([0.27,0.78,0.06],[-0.12,-0.48,0],[-1.18,0.91,-0.36],[0.12,0,0.45],[-1.17,0.54,0.26],[0.08,0,0.25],[-0.63,0,0.13],[0.49,0,-0.12],-0.16),
  grx_w: P([0.45,-0.56,-0.07],[-0.15,0.36,0],[-0.69,-0.67,-0.48],[0.40,0,-0.34],[-0.86,-0.31,0.32],[0.21,0,0.05],[-0.79,0,0.15],[0.59,0,-0.10],-0.26),
  grx_s: P([-0.34,0.48,0.04],[0.17,-0.17,0],[-2.70,0.40,-0.18],[0.15,0,0.08],[-2.41,0.34,0.14],[0.11,0,0.14],[-0.66,0,0.13],[0.20,0,-0.09],-0.08),
  grx_air_w: P([-0.28,-0.13,0],[0.09,0.06,0],[-2.27,-0.21,-0.30],[0.26,0,-0.10],[-2.28,0.18,0.13],[0.14,0,0.05],[-1.12,0,0.11],[-0.96,0,-0.08],0.02),
  grx_air_s: P([0.58,0.13,0.05],[-0.29,-0.05,0],[-0.60,0.22,-0.25],[0.11,0,0.05],[-0.64,0.19,0.17],[0.09,0,-0.05],[-0.88,0,0.13],[0.69,0,-0.08],-0.25),
  grc_w: P([-0.12,-0.59,0.02],[0.08,0.27,0],[-1.68,-0.46,-0.26],[0.44,0,0.05],[-1.52,-0.38,0.20],[0.31,0,-0.06],[-0.46,0,0.12],[0.44,0,-0.09],-0.13),
  grc_s: P([0.24,0.43,0.02],[-0.12,-0.18,0],[-1.10,0.49,-0.36],[0.18,0,0.15],[-1.26,0.45,0.24],[0.16,0,0.11],[-0.62,0,0.12],[0.51,0,-0.09],-0.17),
  grv_w: P([-0.22,-0.29,-0.01],[0.13,0.10,0],[-2.60,-0.16,-0.10],[0.31,0,-0.08],[-2.52,0.14,0.08],[0.23,0,0.06],[-0.59,0,0.12],[0.50,0,-0.09],-0.17),
  grv_float: P([-0.13,0.14,0.03],[0.16,-0.07,0],[-2.24,0.21,-0.30],[0.24,0,-0.02],[-1.89,-0.23,0.36],[0.16,0,0.10],[-0.87,0,0.15],[-0.79,0,-0.11],0.05),
  grv_finish: P([0.59,0.54,0.08],[-0.27,-0.32,0],[-0.55,0.74,-0.29],[0.12,0,0.30],[-0.77,0.51,0.13],[0.08,0,0.12],[-0.91,0,0.15],[0.68,0,-0.09],-0.28),
};

// ZEPHYR_DRAGON_DANCER_V1: stance -> cross-body -> figure-eight -> back catch -> pole vault finish.
const DRAGON_STAFF: Record<string, Pose> = {
  ...GLAIVE,
  idle: P([.07,-.27,.02],[-.05,.20,0],[-.87,.33,-.31],[.2,.04,-.13],[-1.03,-.20,.28],[.22,-.02,.10],[-.23,0,.20],[.28,0,-.17],-.10),
  block: P([.19,-.07,0],[-.02,.08,0],[-1.35,.22,-.24],[.38,0,-.12],[-1.43,-.27,.24],[.34,0,.12],[-.49,0,.17],[.47,0,-.15],-.17),
  charge: P([.21,-.44,.03],[.04,.28,0],[-1.29,.55,-.31],[.32,0,-.18],[-1.09,-.26,.37],[.22,0,.06],[-.44,0,.16],[.50,0,-.16],-.14),
  zd1_w: P([.13,-.60,.05],[0,.37,0],[-.95,-.64,-.20],[.3,0,-.24],[-1.04,-.45,.24],[.32,0,.06],[-.39,0,.18],[.37,0,-.13],-.12),
  zd1_s: P([.21,.49,-.04],[-.04,-.24,0],[-1.54,.38,-.27],[.12,0,.26],[-1.37,.30,.18],[.16,0,.1],[-.48,0,.14],[.39,0,-.15],-.13),
  zd2_w: P([.13,.55,.02],[-.05,-.28,0],[-1.18,.72,-.42],[.25,0,-.19],[-.91,.23,.32],[.20,0,.12],[-.24,0,.12],[.4,0,-.15],-.11),
  zd2_s: P([.19,-.60,-.03],[-.04,.38,0],[-1.62,-.62,-.24],[.16,0,.24],[-1.19,-.42,.28],[.19,0,-.07],[-.45,0,.14],[.43,0,-.1],-.14),
  zd3_w: P([.24,-.52,-.10],[-.06,.33,0],[-1.29,-.33,-.59],[.57,0,-.19],[-.89,-.28,.44],[.21,0,.04],[-.45,0,.17],[.37,0,-.12],-.17),
  zd3_s: P([.03,.62,.1],[-.02,-.28,0],[-2.00,.45,-.18],[.12,0,.39],[-1.40,.18,.31],[.12,0,.06],[-.50,0,.15],[.46,0,-.11],-.11),
  zd4_w: P([.12,-.92,0],[0,.40,0],[-1.10,-.71,-.36],[.56,0,-.19],[-1.04,-.63,.40],[.26,0,-.12],[-.51,0,.13],[.43,0,-.12],-.15),
  zd4_s: P([.08,1.02,.02],[0,-.55,0],[-1.93,.83,-.23],[.17,0,.44],[-1.57,.66,.29],[.10,0,.31],[-.62,0,.15],[.47,0,-.14],-.13),
  zd5_w: P([-.22,-.39,.04],[.13,.17,0],[-2.57,-.2,-.23],[.42,0,-.04],[-2.19,-.09,.17],[.3,0,.06],[-.73,0,.10],[.27,0,-.10],-.10),
  zd5_s: P([.43,.36,0],[-.23,-.11,0],[-.72,.37,-.37],[.13,0,.18],[-.92,.24,.24],[.13,0,.06],[-.77,0,.14],[.65,0,-.16],-.23),
  zdh_w: P([-.17,-.47,.02],[.13,.24,0],[-2.20,-.36,-.29],[.4,0,-.13],[-1.86,-.24,.23],[.34,0,.08],[-.65,0,.14],[.41,0,-.15],-.17),
  zdh_s: P([.45,.44,.05],[-.21,-.19,0],[-.79,.44,-.43],[.15,0,.28],[-1.14,.34,.31],[.16,0,.12],[-.80,0,.15],[.59,0,-.15],-.21),
  zdz_w: P([.07,-.56,0],[0,.37,0],[-1.67,-.38,-.22],[.50,0,-.26],[-1.57,-.22,.37],[.38,0,.07],[-.46,0,.14],[.44,0,-.13],-.12),
  zdz_s: P([.10,.69,0],[-.1,-.29,0],[-1.87,.72,-.25],[.2,0,.35],[-1.62,.44,.29],[.22,0,.17],[-.51,0,.14],[.45,0,-.16],-.14),
  zdx_w: P([.29,-.16,0],[-.06,.08,0],[-1.40,.35,-.35],[.34,0,-.22],[-1.47,-.36,.34],[.31,0,.15],[-.69,0,.14],[.61,0,-.16],-.20),
  zdx_s: P([.09,.27,0],[-.11,-.03,0],[-1.34,-.48,-.25],[.27,0,.09],[-1.59,.37,.38],[.2,0,.1],[-.49,0,.13],[.55,0,-.18],-.17),
  zdc_w: P([.1,-.75,0],[0,.25,0],[-1.49,-.55,-.38],[.40,0,-.16],[-1.33,-.47,.43],[.24,0,.12],[-.45,0,.16],[.43,0,-.15],-.13),
  zdc_s: P([.12,.72,0],[-.08,-.26,0],[-1.67,.61,-.36],[.25,0,.40],[-1.59,.38,.31],[.17,0,.14],[-.61,0,.14],[.52,0,-.15],-.15),
  zdv_w: P([-.12,-.48,0],[.07,.18,0],[-2.37,-.3,-.31],[.36,0,-.13],[-2.11,-.14,.28],[.24,0,.13],[-.56,0,.14],[.45,0,-.15],-.14),
  zdv_s: P([.20,.53,0],[-.14,-.16,0],[-1.95,.53,-.32],[.29,0,.30],[-1.71,.46,.28],[.19,0,.20],[-.67,0,.15],[.59,0,-.16],-.18),
  zdv_finish: P([.52,.30,0],[-.19,-.08,0],[-.55,.47,-.25],[.11,0,.16],[-.84,.31,.28],[.10,0,.10],[-.83,0,.13],[.59,0,-.13],-.22),
  // SANJIEKUN_VISUAL_V17: presentation-only poses; damage and hitboxes untouched.
  zd_fold: P([.12,-.17,.07],[-.08,.15,.04],[-1.36,.30,-.4],[.22,0,-.08],[-.68,-.30,.52],[0,0,.05],[-.33,0,.16],[.38,0,-.12],-.12),
  zd_catch: P([.20,.25,-.08],[-.12,-.05,.08],[-1.7,.38,-.25],[.19,0,.12],[-1.42,-.10,.31],[.21,0,.07],[-.42,0,.15],[.44,0,-.15],-.13),
  zd_handpass: P([-.07,.55,.13],[-.13,-.20,.06],[-1.13,-.22,-.32],[.18,0,.19],[-2.1,.43,.41],[.13,0,.13],[-.51,0,.19],[.34,0,-.12],-.10),
  zd_sway: P([.09,-.31,-.11],[-.07,.18,.08],[-.9,.31,-.43],[.15,0,.13],[-1.14,-.31,.39],[.24,0,.1],[-.17,0,.17],[.31,0,-.19],-.09),
};

const CHAINBLADE: Record<string, Pose> = {
  ...twoHanded(KNIGHT),
  idle: P([0.06, -0.12, 0], [-0.03, 0.1, 0], [-0.86, 0.17, -0.16], [0.25, 0, -0.2], [-0.48, -0.3, 0.40], [0.17, 0, 0.08], [-0.19, 0, 0.06], [0.19, 0, -0.06], -0.055),
  cb1_w: P([0.13, -0.68, -0.05], [-0.07, 0.4, 0], [-1.28, -0.75, -0.1], [0.65, 0, -0.35], [-0.44, 0.4, 0.52], [0.12, 0, 0], [-0.34, 0, 0.07], [0.31, 0, -0.06], -0.09),
  cb1_s: P([0.20, 0.58, 0.04], [-0.1, -0.32, 0], [-1.52, 0.8, 0.02], [0.2, 0, 0.65], [-0.5, -0.55, 0.35], [0.12, 0, 0], [-0.42, 0, 0.08], [0.4, 0, -0.08], -0.10),
  cb2_w: P([0.12, 0.65, 0.04], [-0.05, -0.41, 0], [-1.12, 0.98, 0.04], [0.4, 0, 0.4], [-0.4, -0.48, 0.37], [0.16, 0, 0], [-0.37, 0, 0.06], [0.36, 0, -0.06], -0.11),
  cb2_s: P([0.20, -0.65, -0.03], [-0.1, 0.42, 0], [-1.48, -0.9, -0.08], [0.22, 0, -0.6], [-0.54, 0.54, 0.34], [0.18, 0, 0], [-0.42, 0, 0.09], [0.38, 0, -0.07], -0.13),
  cb3_w: P([-0.09, -0.39, 0], [0.04, 0.19, 0], [-1.78, -0.55, -0.12], [0.57, 0, 0.3], [-0.5, 0.28, 0.40], [0.18, 0, 0], [-0.32, 0, 0.07], [0.3, 0, -0.08], -0.10),
  cb3_s: P([0.32, 0.46, 0.06], [-0.12, -0.24, 0], [-0.97, 0.74, 0.01], [0.24, 0, -0.58], [-0.4, -0.42, 0.53], [0.12, 0, 0], [-0.56, 0, 0.1], [0.46, 0, -0.08], -0.15),
  cb4_w: P([0.17, 0.76, 0.06], [-0.05, -0.47, 0], [-1.5, 0.94, 0.05], [0.48, 0, 0.61], [-0.42, -0.52, 0.44], [0.12, 0, 0], [-0.42, 0, 0.08], [0.37, 0, -0.08], -0.12),
  cb5_w: P([0.15, -0.82, -0.02], [0, 0.48, 0], [-1.4, 0.80, 0.04], [0.25, 0.04, 0.62], [-0.34, -0.62, 0.45], [0.11, 0, 0], [-0.49, 0, 0.07], [0.42, 0, -0.07], -0.15),
  cb5_s: P([0.35, 1.02, 0.06], [-0.11, -0.69, 0], [-1.78, -1.04, -0.07], [0.05, 0, -0.65], [-0.5, 0.42, 0.5], [0.16, 0, 0], [-0.49, 0, 0.11], [0.46, 0, -0.06], -0.16),
  cb4_s: P([0.37, -0.86, -0.06], [-0.15, 0.54, 0], [-1.43, -1.12, -0.05], [0.14, 0, -0.68], [-0.57, 0.51, 0.33], [0.15, 0, 0], [-0.62, 0, 0.10], [0.50, 0, -0.09], -0.16),
  cbh_w: P([0.15, -1.02, -0.08], [0, 0.62, 0], [-1.17, -1.32, -0.2], [0.72, 0, 0], [-1.08, -1.08, 0.22], [0.6, 0, 0], [-0.53, 0, 0.1], [0.46, 0, -0.08], -0.19),
  cbh_s: P([0.45, 1.06, 0.1], [-0.22, -0.6, 0], [-1.5, 1.2, -0.12], [0.2, 0, 0], [-1.4, 1.48, 0.15], [0.15, 0, 0], [-0.73, 0, 0.1], [0.58, 0, -0.09], -0.23),
  cbz_w: P([0.12, -0.4, 0], [0, 0.25, 0], [-1.2, -0.5, -0.24], [0.8, 0, 0], [-1.22, -0.14, 0.25], [0.35, 0, 0], [-0.4, 0, 0.08], [0.35, 0, -0.07], -0.14),
  cbz_s: P([0.34, 0.15, 0], [-0.1, -0.1, 0], [-1.44, 0.04, -0.13], [0.1, 0, 0], [-1.4, 0.23, 0.17], [0.1, 0, 0], [-0.7, 0, 0.09], [0.52, 0, -0.08], -0.21),
  cbx_w: P([0.17, -0.70, 0.02], [0, 0.50, 0], [-1.15, -0.82, -0.10], [0.6, 0, -0.4], [-0.60, 0.12, 0.55], [0.20, 0, 0], [-0.43, 0, 0.08], [0.43, 0, -0.08], -0.14),
  cbx1_s: P([0.31, 1.05, 0.03], [-0.12, -0.52, 0], [-1.47, 1.1, -0.12], [0.18, 0, 0.55], [-0.62, -0.1, 0.40], [0.12, 0, 0], [-0.60, 0, 0.10], [0.45, 0, -0.08], -0.18),
  cbx2_s: P([0.24, -1.0, -0.07], [-0.08, 0.56, 0], [-1.4, -1.15, -0.1], [0.2, 0, -0.52], [-0.52, 0.20, 0.49], [0.18, 0, 0], [-0.53, 0, 0.09], [0.46, 0, -0.08], -0.18),
  cbx3_s: P([0.38, 0.93, 0.08], [-0.14, -0.50, 0], [-1.2, 1.16, 0], [0.12, 0, 0.72], [-0.65, -0.3, 0.42], [0.2, 0, 0], [-0.61, 0, 0.1], [0.51, 0, -0.09], -0.2),
  cbc_w: P([0.05, -0.55, 0], [0, 0.4, 0], [-1.6, -0.55, 0.0], [0.4, 0, 0], [-1.6, -0.1, 0.2], [0.3, 0, 0], [-0.52, 0, 0.08], [0.45, 0, -0.08], -0.14),
  cbc_s: P([-0.05, 0.2, 0], [-0.1, -0.1, 0], [-2.2, 0.12, -0.08], [0.9, 0, 0], [-2.1, 0.55, 0.16], [0.8, 0, 0], [-0.55, 0, 0.08], [0.45, 0, -0.08], -0.16),
  cbv_w: P([0.1, -0.8, 0], [0, 0.5, 0], [-1.43, -0.95, 0], [0.6, 0, 0], [-1.45, -0.62, 0.16], [0.45, 0, 0], [-0.46, 0, 0.08], [0.42, 0, -0.08], -0.15),
  cbv_s: P([0.35, 0.86, 0], [-0.16, -0.5, 0], [-1.38, 0.98, 0], [0.1, 0, 0], [-1.35, 1.25, 0.12], [0.08, 0, 0], [-0.62, 0, 0.1], [0.49, 0, -0.08], -0.20),
};

// NESA_HEART_HAMMER_V2: weapon-weight poses, distinct from Garrick.
const NESA_SWINGS: Record<string, Pose> = {
  // NESA_FORWARD_HEART_PARRY_V_20261108: raise the hammer vertically, then sweep it downward.
  nesa_parry_w: K(P([-0.14, -0.30, 0], [0.06, 0.16, 0], [-2.65, -0.27, -0.12], [0.55, 0, 0],
    [-2.43, -0.19, 0.10], [0.50, 0, 0], [-0.30, 0, 0.08], [0.26, 0, -0.08], -0.11), 0.15, 0.19),
  nesa_parry_s: K(P([0.42, 0.14, 0], [-0.12, -0.08, 0], [-0.68, 0.42, -0.08], [0.16, 0, 0],
    [-0.81, -0.15, 0.11], [0.16, 0, 0], [-0.77, 0, 0.10], [0.51, 0, -0.09], -0.27), 0.70, 0.82),
  // NESA_V5_LOADOUT_AIR_SPIN_UPRIGHT: Nesa STANDS on straight, relaxed legs; the hammer weight pulls at her shoulders and wrists, not her knees.
  idle: P([0.11, -0.20, 0.03], [-0.04, 0.13, 0], [-1.04, -0.29, -0.15], [-0.16, 0, 0], [-1.03, 0.21, 0.14], [-0.16, 0, 0], [-0.06, 0, 0.05], [0.06, 0, -0.05], 0.0),
  l1_w: P([0.18, -1.12, -0.08], [0.04, 0.55, 0], [-1.03, -1.0, -0.20], [0.72, 0, 0], [-1.06, -0.72, 0.12], [0.65, 0, 0], [-0.56, 0, 0.13], [0.4, 0, -0.1], -0.22),
  l1_s: P([0.34, 0.96, 0.1], [-0.08, -0.55, 0], [-1.7, 1.2, -0.1], [0.12, 0, 0], [-1.52, 1.12, 0.1], [0.1, 0, 0], [-0.65, 0, 0.12], [0.45, 0, -0.08], -0.22),
  l2_w: P([0.16, 0.9, 0.09], [0, -0.48, 0], [-1.4, 1.0, 0.1], [0.42, 0, 0], [-1.2, 0.8, 0.08], [0.43, 0, 0], [-0.47, 0, 0.11], [0.36, 0, -0.09], -0.20),
  l2_s: P([0.32, -1.1, -0.1], [-0.1, 0.65, 0], [-1.6, -1.15, -0.08], [0.16, 0, 0], [-1.46, -1.05, 0.12], [0.12, 0, 0], [-0.63, 0, 0.12], [0.46, 0, -0.1], -0.24),
  l3_w: P([-0.2, -0.66, 0.05], [0.03, 0.44, 0], [-2.4, -0.45, -0.1], [0.7, 0, 0], [-2.0, -0.4, 0.12], [0.5, 0, 0], [-0.56, 0, 0.12], [0.48, 0, -0.12], -0.22),
  l3_s: P([0.35, 1.12, -0.10], [-0.13, -0.76, 0], [-1.7, 1.22, 0], [0.15, 0, 0], [-1.55, 1.0, 0.12], [0.1, 0, 0], [-0.6, 0, 0.11], [0.44, 0, -0.11], -0.23),
  charge: K(P([-0.13, -0.38, 0], [0.06, 0.28, 0], [-2.6, -0.35, -0.12], [0.7, 0, 0], [-2.44, -0.25, 0.12], [0.65, 0, 0], [-0.15, 0, 0.08], [0.14, 0, -0.08], -0.075), 0.12, 0.13),
  heavy_s: K(P([0.66, 0.18, 0], [-0.22, 0, 0], [-0.85, 0.36, 0], [0.14, 0, 0], [-0.88, -0.2, 0.1], [0.12, 0, 0], [-0.95, 0, 0.10], [0.60, 0, -0.1], -0.32), 0.85, 0.9),
  nx_w: P([0.24, 0.92, 0], [0, -0.4, 0], [-1.4, 0.98, 0], [0.4, 0, 0], [-1.36, 0.78, 0], [0.4, 0, 0], [-0.5, 0, 0.10], [0.44, 0, -0.08], -0.19),
  nx_s: P([0.36, -1.08, 0], [-0.06, 0.5, 0], [-1.45, -1.18, 0], [0.1, 0, 0], [-1.28, -1.10, 0], [0.12, 0, 0], [-0.64, 0, 0.14], [0.50, 0, -0.09], -0.22),
  // Pole planted: both hands low and forward; side kick follows while still gripping shaft.
  kick_w: K(P([0.58, -0.18, -0.05], [-0.24, 0.08, 0], [-0.52, 0.05, 0.20], [0.48, 0, 0], [-0.53, -0.16, -0.20], [0.48, 0, 0], [-0.90, 0, 0.05], [-0.36, 0, -0.07], -0.38), 1.10, 0.86),
  kick_s: K(P([-0.20, 0.06, 0.10], [0.17, -0.10, 0], [-0.70, 0.15, 0.12], [0.32, 0, 0], [-0.66, -0.14, -0.20], [0.34, 0, 0], [-1.51, 0, 0.04], [0.43, 0, -0.10], -0.02), 0.09, 0.92),
};

const TABLES: Record<string, Record<string, Pose>> = {
  knight: KNIGHT,
  mage: MAGE,
  sickle: SICKLE,
  glaive: GLAIVE,
  tristaff: DRAGON_STAFF,
  assassin: ASSASSIN,
  greatsword: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },
  hammer: { ...twoHanded(KNIGHT), ...NESA_SWINGS },
  chainblade: CHAINBLADE,
  katana: {
    ...twoHanded(KNIGHT),
    // Kaede C: right hand slides the blade toward left-hip scabbard; left hand steadies it.
    // Feet remain planted and shoulders settle as the blade goes home.
    kaede_sheathe_w: P([0.18, -0.34, 0.10], [-0.13, 0.24, 0.03],
      [0.32, -0.62, -0.62], [0.24, 0.10, 0.34], [-0.50, 0.50, 0.38],
      [-0.22, -0.10, -0.22], [-0.18, 0, 0.11], [0.17, 0, -0.11], -0.055),
    kaede_sheathe_s: P([0.07, -0.20, 0.02], [-0.12, 0.14, 0],
      [0.62, -0.78, -0.49], [0.30, 0.08, 0.36], [-0.64, 0.48, 0.33],
      [-0.32, -0.16, -0.24], [-0.12, 0, 0.11], [0.14, 0, -0.11], -0.055),
  },
  bow: BOW,
  scythe: GRAVITY_SCYTHE,
  knuckles: KNUCKLES,
  bomb: {
    // Bomb held in the right hand near the chest, left hand loose.
    idle: P([0.02, -0.3, 0], [0, 0.25, 0], [-0.7, 0.45, -0.25], [0.5, 0, 0], [-0.25, -0.15, 0.22], [0.2, 0, 0], [-0.25, 0, 0.08], [0.25, 0, -0.08], -0.04),
    block: P([0.15, 0, 0], [0.1, 0, 0], [-1.3, 0.7, 0], [0.9, 0, 0], [-1.3, -0.7, 0], [0.9, 0, 0], [-0.4, 0, 0.08], [0.4, 0, -0.08], -0.1),
    // Throw: arm cocked back over the shoulder, then the bomb is lobbed forward.
    throw_w: P([-0.1, -0.5, 0], [0, 0.45, 0], [-2.5, 0.35, -0.45], [0.6, 0, 0], [-0.9, -0.3, 0.3], [0.2, 0, 0], [-0.35, 0, 0.08], [0.35, 0, -0.08], -0.06),
    throw_s: P([0.25, 0.35, 0], [-0.05, -0.3, 0], [-1.25, 0.1, -0.1], [0.2, 0, 0], [-0.3, -0.2, 0.35], [0.2, 0, 0], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.1),
    charge: P([-0.2, -0.7, 0], [0, 0.6, 0], [-2.7, 0.4, -0.5], [0.6, 0, 0], [-1.1, -0.35, 0.35], [0.2, 0, 0], [-0.5, 0, 0.1], [0.5, 0, -0.1], -0.14),
    // Mine: crouch and set it on the ground.
    plant_w: K(P([0.5, -0.2, 0], [-0.25, 0.2, 0], [-0.6, 0.2, -0.3], [0.5, 0, 0], [-0.3, -0.1, 0.3], [0.2, 0, 0], [-0.9, 0, 0.12], [-0.2, 0, -0.08], -0.3), 0.6, 1.2),
    plant_s: K(P([0.7, -0.1, 0], [-0.35, 0.1, 0], [-0.95, 0.15, -0.15], [0.3, 0, 0], [-0.3, -0.1, 0.3], [0.2, 0, 0], [-1.0, 0, 0.12], [-0.3, 0, -0.08], -0.38), 0.7, 1.3),
    // Keg: heave it down in front with both hands.
    barrel_w: P([0.35, 0, 0], [-0.2, 0, 0], [-1.2, 0.25, -0.1], [0.6, 0, 0], [-1.2, -0.25, 0.1], [0.6, 0, 0], [-0.6, 0, 0.1], [0.5, 0, -0.1], -0.2),
    barrel_s: P([0.55, 0, 0], [-0.3, 0, 0], [-0.8, 0.2, -0.1], [0.3, 0, 0], [-0.8, -0.2, 0.1], [0.3, 0, 0], [-0.8, 0, 0.1], [0.6, 0, -0.1], -0.3),
  },
  wind: {
    ...KNUCKLES,
    // Relaxed: arms low at the sides, so any raised fist reads as an attack coming.
    idle: P([0.02, -0.3, 0], [0, 0.25, 0], [-0.2, 0.15, -0.22], [0.2, 0, 0], [-0.25, -0.15, 0.22], [0.2, 0, 0], [-0.25, 0, 0.08], [0.25, 0, -0.08], -0.05),
    // Every attack chambers first: the fist pulls back to the hip and the torso twists away.
    w1_w: P([0.05, -0.6, 0], [0, 0.55, 0], [0.45, 0.35, -0.35], [1.2, 0, 0], [-0.9, -0.3, 0.3], [0.6, 0, 0], [-0.35, 0, 0.08], [0.35, 0, -0.08], -0.08),
    w1_s: P([0.2, 0.4, 0], [-0.05, -0.35, 0], [-1.6, 0.2, 0], [0, 0, 0], [-0.4, -0.2, 0.35], [0.8, 0, 0], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.12),
    w2_w: P([0.05, 0.5, 0], [0, -0.45, 0], [-0.9, 0.3, -0.3], [0.6, 0, 0], [0.45, -0.35, 0.35], [1.2, 0, 0], [-0.35, 0, 0.08], [0.35, 0, -0.08], -0.08),
    w2_s: P([0.2, -0.45, 0], [-0.05, 0.4, 0], [-0.4, 0.2, -0.35], [0.8, 0, 0], [-1.6, -0.2, 0], [0, 0, 0], [-0.5, 0, 0.08], [0.45, 0, -0.08], -0.12),
    // Palm strike: both hands drawn back to the right hip, then pushed out together.
    w3_w: P([0.1, -0.75, 0], [0, 0.65, 0], [0.4, 0.4, -0.3], [1.1, 0, 0], [-0.2, 0.6, 0.1], [1.1, 0, 0], [-0.4, 0, 0.1], [0.4, 0, -0.1], -0.12),
    w3_s: P([0.25, 0.1, 0], [-0.1, 0, 0], [-1.55, 0.12, 0], [0, 0, 0], [-1.55, -0.12, 0], [0, 0, 0], [-0.6, 0, 0.08], [0.55, 0, -0.08], -0.16),
    // Wind Step: lean back and load both fists, then lunge through with the right.
    wd_w: P([-0.15, -0.3, 0], [0.1, 0.3, 0], [0.4, 0.3, -0.3], [1.1, 0, 0], [0.3, -0.3, 0.3], [1.1, 0, 0], [-0.5, 0, 0.1], [0.5, 0, -0.1], -0.14),
    wd_s: P([0.45, 0.2, 0], [-0.25, -0.15, 0], [-1.6, 0.15, 0], [0, 0, 0], [0.4, -0.2, 0.4], [0.6, 0, 0], [-0.8, 0, 0.08], [0.7, 0, -0.08], -0.22),
    rise: P([-0.2, 0.3, 0], [-0.25, -0.2, 0], [-2.8, 0.3, -0.2], [0.5, 0, 0], [-0.6, -0.3, 0.6], [0.4, 0, 0], [-0.9, 0, 0.06], [0.2, 0, -0.06], 0),
    // Double jump: riding a burst of wind (knees tucked, arms spread low to push off the air).
    wind_jump: K(P([0.3, 0, 0], [0.2, 0, 0], [0.35, 0, -1.15], [0, 0, 0], [0.35, 0, 1.15], [0, 0, 0], [-1.0, 0, 0.12], [-0.45, 0, -0.12], 0), 1.5, 1.15),
  },
  kicks: {
    ...KICKS,
    kira_hundred_cast_w: K(P([0.04, 0.12, 0], [0.02, -0.06, 0],
      [-0.45, 0.28, -0.34], [0, 0, 0], [-0.45, -0.28, 0.34], [0, 0, 0],
      [-0.12, 0, 0.10], [0.12, 0, -0.10], -0.04), 0.10, 0.10),
    kira_hundred_cast_s: K(P([0, 0, 0], [-0.02, 0, 0],
      [-0.42, 0.12, -0.24], [0, 0, 0], [-0.42, -0.12, 0.24], [0, 0, 0],
      [-0.10, 0, 0.09], [0.10, 0, -0.09], -0.04), 0.07, 0.07),
  },
};

export function poses(kit: string, element?: string): Record<string, Pose> {
  const t = { ...COMMON, ...(TABLES[kit] ?? KNIGHT), ...(kit === "knight" && element === "light" ? { ...ASTER_SWINGS, ...ASTER_COMBAT_V2 } : {}), ...(kit === "assassin" ? NYX_SHADOW_V1 : {}), ...(kit === "glaive" && element === "metal" ? ZENITH : {}) };
  if (!t.charge) t.charge = t.mh_w ?? t.ash_w ?? KNIGHT.charge;
  return t;
}
