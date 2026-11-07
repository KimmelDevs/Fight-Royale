// AI_CHARACTER_FIGHTING_STYLES_V1_20261108
// AI_ADVANCED_FOOTWORK_V1_20261108
// AI_ROOK_NESA_KIRA_MERGED_V1_20261108
//AI_PROJECTILE_CLASH_IQ_V1_20261108
//AI_AERIAL_COMBAT_INTELLIGENCE_V1_20261108
// AI_ENEMY_COOLDOWN_MEMORY_V1_20261107
// KAIZEN_V_SERPENT_DIRECTION_AI_20261107_V1
// BALANCE_KIRA_KAEDE_PATTERN_AI_AIR_ICON_20261107_V1
// COMBAT_IQ_HITCONFIRM_WHIFF_BAIT_V1_20261107
// AI_EFFECTIVE_RANGE_KAIZEN_AIR_HOOK_20261107_V1
// ZAREK_ARC_FLASH_CPU_SPECTATOR_COOLDOWNS_20261107_V1
// FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1
// MARINA_RAVEN_ZAREK_BOB_ABILITIES_20261107_V1
// FIGHT_ROYALE_BULLET_SWORDPLAY_GARRICK_RESOLVE_V1
// KAIZEN_SPIN_HIT_RELIABILITY_V9
// FIGHT_ROYALE_KAIZEN_MOBILE_SPIN_V8
// FIGHT_ROYALE_GARRICK_BOB_KAIZEN_ROOK_V7
// FIGHT_ROYALE_ZAREK_CPU_SHIELD_RECOVERY_V2
// FIGHT_ROYALE_NYX_CAMERA_CONTINUOUS_DODGE_20261107_V1
// FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V2
// FIGHT_ROYALE_AI_DEFENSE_AGGRESSION_REPAIR_V2
// FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V1
// FIGHT_ROYALE_GROUNDED_AIR_SLICES_V1
// FIGHT_ROYALE_ZAREK_EFFECTIVE_RANGE_NERF_V1
// EMBER_IGNITION_GUARD_AI_V1_NOV07
// ENEMY_PROJECTILE_CLASH_AI_V1_NOV06
// MELEE_PROJECTILE_SPRINT_V1_NOV06
// EMBER_GROUND_HAZARD_AI_V1_NOV06
// CONTINUOUS_PARRY_AI_V4_NOV06
// CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06
// ROXY_MASTER_SKILLS_MAGE_BASIC_COUNTERS_V6_20261108: Roxy combat planning and one-projectile mage parry counters.
// Duel CPU. Presses the same virtual buttons a player would, with human-ish reaction times:
// reacts once per enemy swing / projectile / ground marker (block, parry, jump, sidestep),
// keeps its preferred range (ranged kits kite), and picks attacks and skills when idle.
// NESA_ZENITH_AGGRESSIVE_AI_V8_20261108: V1/V2 low-HP logic removed, Nesa/Zenith tactics updated.
import * as THREE from "three";
import { Fighter, S, HOLD_T, type Brain } from "./fighter";

export const LEVELS = ["Easy", "Normal", "Hard", "Master"];
const PRESETS = [
  { block: 0.2, parry: 0.0, jump: 0.1, react: [0.3, 0.5], think: 1.8, skill: [3.5, 6.0], combo: 2 },
  { block: 0.38, parry: 0.06, jump: 0.22, react: [0.18, 0.34], think: 1.25, skill: [2.0, 3.8], combo: 3 },
  { block: 0.5, parry: 0.14, jump: 0.3, react: [0.12, 0.26], think: 1.0, skill: [1.2, 2.6], combo: 4 },
  { block: 0.65, parry: 0.3, jump: 0.45, react: [0.08, 0.16], think: 0.7, skill: [0.8, 1.6], combo: 5 },
];

export interface Threats {
  projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number; team?: number; style?: string; size?: number; atkType?: string; heavy?: boolean }[];
  /** Real telegraphed damage circles, not guessed from enemy animation. */
  fields(f: Fighter): { id: number; center: THREE.Vector3; radius: number }[];
  strikes(): {
    target: any; land: number; id: number;
    center?: THREE.Vector3; radius?: number; caster?: Fighter;
    followsCaster?: boolean; style?: string;
  }[];
  /** Beam warnings appear only after Ember really begins gathering flames. */
  ignitions(f: Fighter): { caster: Fighter; land: number; id: number }[];
  /** Authoritative scheduled hit timestamps for an active continuous combo. */
  comboHits(attacker: Fighter): number[];
  /** Live enemy Ember fire patches; friendly flames are filtered out by Game. */
  firePatches(f: Fighter): { pos: THREE.Vector3; radius: number }[];
  now(): number;
  /** Zenith can reason about the polarity she actually applied to this opponent. */
  magneticMark?(self: Fighter, enemy: Fighter): -1 | 0 | 1;
}

const rand = (a: number, b: number) => a + Math.random() * (b - a);
const RANGED = new Set(["mage", "bow", "bomb"]);

// Removed: low-health retreat / last-stand personality overrides.

// AI_ADVANCED_FOOTWORK: movement choices are made in short plans, not every
// frame. Reaction delays and imperfect reads scale with the selected difficulty.
// Even Master uses normal move input, finite turn speed and the arena boundary.
const ADVANCED_FOOTWORK = [
  { read: 0.12, react: [0.54, 0.85], orbit: 0.10, flank: 0,    corner: 0 },
  { read: 0.54, react: [0.37, 0.60], orbit: 0.55, flank: 0.16, corner: 0.22 },
  { read: 0.79, react: [0.23, 0.40], orbit: 0.82, flank: 0.56, corner: 0.63 },
  { read: 0.96, react: [0.12, 0.24], orbit: 0.97, flank: 0.88, corner: 0.88 },
] as const;


// AI_PROJECTILE_CLASH_IQ: incoming shots are seen once each, never rerolled
// per frame. A read is an imperfect estimate of a physical mid-flight clash.
const PROJECTILE_CLASH_IQ = [
  { notice: 0.10, reaction: [0.34, 0.54], tolerance: 0.34, reserve: 0.82 },
  { notice: 0.43, reaction: [0.23, 0.37], tolerance: 0.26, reserve: 0.66 },
  { notice: 0.72, reaction: [0.13, 0.24], tolerance: 0.18, reserve: 0.42 },
  { notice: 0.91, reaction: [0.060, 0.135], tolerance: 0.11, reserve: 0.22 },
] as const;
type CounterfireRead = { reactAt: number; wants: boolean; spent: boolean };


// Aerial reads use sampled, *visible* position changes, not enemy future inputs.
// Detection is rolled once per jump; reactions take real time. All choices are
// subject to the existing Fighter jump / attack / cooldown / collision rules.
const AERIAL_IQ = [
  { notice: 0.14, react: [0.40, 0.67], landReact: [0.34, 0.50],
    jump: 0.10, strike: 2.2, uncertainty: 1.20 },
  { notice: 0.46, react: [0.27, 0.46], landReact: [0.24, 0.38],
    jump: 0.32, strike: 4.2, uncertainty: 0.70 },
  { notice: 0.76, react: [0.16, 0.30], landReact: [0.14, 0.25],
    jump: 0.61, strike: 7.0, uncertainty: 0.34 },
  { notice: 0.93, react: [0.09, 0.18], landReact: [0.085, 0.16],
    jump: 0.82, strike: 10.5, uncertainty: 0.17 },
] as const;


// Enemy cooldowns are *estimated* from witnessed casts, never read from
// opponent.cooldowns. Variance and recognition delay prevent psychic CPU plays.
const ENEMY_CD_IQ = [
  { observe: 0.00, error: 0.00, react: [0.0, 0.0] }, // Easy: no tracking
  { observe: 0.70, error: 0.30, react: [0.40, 0.73] }, // Normal: big skills only
  { observe: 0.86, error: 0.17, react: [0.24, 0.42] }, // Hard: most threatening skills
  { observe: 0.96, error: 0.09, react: [0.12, 0.24] }, // Master: all cast skills
] as const;

type EnemyCooldownMemory = {
  slot: string; castAt: number; observedAt: number;
  predictedReadyAt: number; nominalCd: number; threat: number;
};


// COMBAT_IQ: Easy seldom recognizes openings, Master is perceptive, not psychic.
// All reads are visible fighter state (active swings, HP/guard changes, recovery).
const COMBAT_IQ = [
  { combo: 0.13, punish: 0.10, bait: 0.00, react: [0.45, 0.70], feintCd: [8.0, 11.0] },
  { combo: 0.43, punish: 0.39, bait: 0.10, react: [0.27, 0.44], feintCd: [6.5, 9.0] },
  { combo: 0.74, punish: 0.73, bait: 0.27, react: [0.15, 0.27], feintCd: [5.0, 7.0] },
  { combo: 0.92, punish: 0.90, bait: 0.48, react: [0.09, 0.17], feintCd: [3.8, 6.0] },
] as const;


// SMART_AI_PERSONALITIES_17_FINAL_V2_20261107
// SMART_AI_PERSONALITIES_17_FINAL_V1 — 17 unique fighting styles; AI inputs only.
// This does not rewrite fighter damage/animations. Spectator and reactive dodges remain.
// Profile keys match roster Look.name, so two knights and the three mages differ.
type FightStyle = {
  range: number; heavy: number; combo: number; bait: number; pressure: number;
  skillBias: readonly [number, number, number];
};
const FIGHT_STYLES: Readonly<Record<string, FightStyle>> = {
  aster: { range: 1.70, heavy: 0.26, combo: 0.65, bait: 0.52, pressure: 0.42, skillBias: [1.5, 1.0, 0.8] },
  vesper: { range: 1.55, heavy: 0.18, combo: 0.94, bait: 0.18, pressure: 0.90, skillBias: [1.0, 1.35, 0.9] },
  garrick: { range: 2.40, heavy: 0.45, combo: 0.42, bait: 0.70, pressure: 0.30, skillBias: [0.95, 1.2, 1.3] },
  kaede: { range: 1.92, heavy: 0.34, combo: 0.77, bait: 0.65, pressure: 0.50, skillBias: [1.75, 0.8, 1.0] },
  ember: { range: 5.50, heavy: 0.36, combo: 0.45, bait: 0.20, pressure: 0.26, skillBias: [0.8, 1.3, 1.3] },
  marina: { range: 5.25, heavy: 0.27, combo: 0.42, bait: 0.24, pressure: 0.25, skillBias: [1.5, 1.25, 0.9] },
  nyx: { range: 1.53, heavy: 0.17, combo: 0.90, bait: 0.62, pressure: 0.85, skillBias: [1.4, 0.9, 1.25] },
  rook: { range: 1.35, heavy: 0.16, combo: 0.98, bait: 0.12, pressure: 1.00, skillBias: [1.3, 0.75, 1.3] },
  gale: { range: 1.67, heavy: 0.23, combo: 0.82, bait: 0.55, pressure: 0.73, skillBias: [0.85, 1.4, 1.1] },
  bob: { range: 5.20, heavy: 0.27, combo: 0.44, bait: 0.45, pressure: 0.16, skillBias: [1.3, 1.1, 1.4] },
  kira: { range: 1.68, heavy: 0.15, combo: 0.96, bait: 0.59, pressure: 0.90, skillBias: [1.35, 1.1, 1.2] },
  raven: { range: 5.75, heavy: 0.40, combo: 0.47, bait: 0.20, pressure: 0.30, skillBias: [1.4, 1.25, 1.35] },
  ash: { range: 6.20, heavy: 0.50, combo: 0.40, bait: 0.44, pressure: 0.19, skillBias: [1.5, 1.0, 1.4] },
  veyr: { range: 1.59, heavy: 0.15, combo: 0.98, bait: 0.68, pressure: 0.94, skillBias: [1.0, 1.35, 1.5] },
  zarek: { range: 2.10, heavy: 0.30, combo: 0.91, bait: 0.35, pressure: 0.86, skillBias: [1.3, 1.2, 1.45] },
  kaizen: { range: 2.65, heavy: 0.33, combo: 0.78, bait: 0.51, pressure: 0.71, skillBias: [1.2, 1.45, 1.15] },
  nesa: { range: 2.38, heavy: 0.43, combo: 0.64, bait: 0.62, pressure: 0.52, skillBias: [1.05, 1.15, 1.2] },
  roxy: { range: 5.45, heavy: 0.36, combo: 0.52, bait: 0.24, pressure: 0.32, skillBias: [1.45, 1.60, 1.20] },
  zenith: { range: 2.20, heavy: 0.30, combo: 0.90, bait: 0.34, pressure: 0.92, skillBias: [1.15, 1.65, 1.10] },
};

// CHARACTER_STYLES_V1: existing FIGHT_STYLES already holds base preferences.
// Add short-lived, observable tactical plans; never grant AI-only statistics.
// Each fighter has a distinct identity and unique mix of plans / V restraint.
type PersonalityRole =
  "counter" | "duelist" | "juggernaut" | "riposte" | "artillery" |
  "support" | "ambush" | "rush" | "skirmish" | "trapper" |
  "kickboxer" | "controller" | "sniper" | "executioner" |
  "glaive" | "grappler" | "bruiser";
type PersonalityPlan = "none" | "pressure" | "probe" | "reset";
type PersonalityProfile = {
  role: PersonalityRole;
  pressure: number; probe: number; reset: number;
  vReserve: number; spacing: number;
};
const CHARACTER_PERSONALITY: Readonly<Record<string, PersonalityProfile>> = {
  // pressure / probe / reset are relative tactical weights, not fixed chance per frame.
  aster:   { role: "counter",      pressure: 0.60, probe: 1.12, reset: 0.54, vReserve: 0.70, spacing:  0.05 },
  vesper:  { role: "duelist",     pressure: 1.35, probe: 0.68, reset: 0.34, vReserve: 0.65, spacing: -0.13 },
  garrick: { role: "juggernaut",  pressure: 1.13, probe: 0.66, reset: 0.24, vReserve: 0.62, spacing:  0.12 },
  kaede:   { role: "riposte",     pressure: 0.67, probe: 1.28, reset: 0.57, vReserve: 0.82, spacing:  0.18 },
  ember:   { role: "artillery",   pressure: 0.45, probe: 1.08, reset: 0.88, vReserve: 0.54, spacing:  0.30 },
  marina:  { role: "support",     pressure: 0.37, probe: 0.91, reset: 1.24, vReserve: 0.45, spacing:  0.27 },
  nyx:     { role: "ambush",      pressure: 1.04, probe: 1.01, reset: 0.50, vReserve: 0.92, spacing: -0.22 },
  rook:    { role: "rush",        pressure: 1.83, probe: 0.36, reset: 0.17, vReserve: 0.35, spacing: -0.32 },
  gale:    { role: "skirmish",    pressure: 1.02, probe: 1.04, reset: 0.47, vReserve: 0.65, spacing: -0.04 },
  bob:     { role: "trapper",     pressure: 0.37, probe: 1.43, reset: 0.96, vReserve: 0.67, spacing:  0.38 },
  kira:    { role: "kickboxer",   pressure: 1.36, probe: 0.88, reset: 0.33, vReserve: 1.25, spacing: -0.14 },
  raven:   { role: "controller",  pressure: 0.46, probe: 1.30, reset: 1.04, vReserve: 0.61, spacing:  0.35 },
  ash:     { role: "sniper",      pressure: 0.35, probe: 1.02, reset: 1.42, vReserve: 0.80, spacing:  0.43 },
  veyr:    { role: "executioner", pressure: 1.53, probe: 0.67, reset: 0.29, vReserve: 0.75, spacing: -0.24 },
  zarek:   { role: "glaive",      pressure: 1.34, probe: 0.79, reset: 0.34, vReserve: 0.64, spacing: -0.08 },
  kaizen:  { role: "grappler",    pressure: 0.97, probe: 1.22, reset: 0.39, vReserve: 0.78, spacing:  0.10 },
  nesa:    { role: "bruiser",     pressure: 1.03, probe: 1.04, reset: 0.45, vReserve: 0.85, spacing:  0.19 },
  roxy:    { role: "controller",  pressure: 0.60, probe: 1.16, reset: 0.90, vReserve: 0.52, spacing:  0.26 },
  zenith:  { role: "glaive", pressure: 1.42, probe: 0.95, reset: 0.35, vReserve: 0.92, spacing: -0.04 },
};
// Difficulty affects how often bots make informed, committed personality reads.
const CHARACTER_IQ = [
  { read: 0.17, gap: [1.8, 2.5], strength: 0.16 },
  { read: 0.46, gap: [1.25, 1.9], strength: 0.43 },
  { read: 0.79, gap: [0.93, 1.42], strength: 0.73 },
  { read: 0.96, gap: [0.68, 1.06], strength: 1.00 },
] as const;

export class AiBrain implements Brain {
  private p = PRESETS[1];
  private queue: [number, number][] = [];
  private hold = 0;
  private blockWait = -1;
  private blockDur = 0;
  private blockHold = 0;
  private jumpWait = -1;
  private sideT = 0;
  private sideSign = 1;
  private strafeT = 0;
  private thinkCd = 1;
  // AIR_COMBAT_V1: CPUs also learn to contest the air and chase successful launches.
  // AI_AERIAL_COMBAT_INTELLIGENCE: one observation/choice per real jump.
  private aerialEnemy: Fighter | null = null;
  private aerialWasUp = false;
  private aerialHasVelocity = false;
  private aerialSeenAt = -1;
  private aerialLastPos = new THREE.Vector3();
  private aerialVelocity = new THREE.Vector3();
  private aerialLandingSpot = new THREE.Vector3();
  private aerialLandingEta = 99;
  private aerialReactAt = 0;
  private aerialLandedReactAt = 0;
  private aerialLandedUntil = 0;
  private aerialNotice = false;
  private aerialJumpChosen = false;
  private aerialJumpSpent = false;
  private aerialLandingSpent = false;
  private aerialNoise = new THREE.Vector3();

  // AI_PROJECTILE_CLASH_IQ: an independent, per-shot decision memory.
  private counterfireEnemy: Fighter | null = null;
  private counterfireReads = new Map<number, CounterfireRead>();
  private counterfireRecoveryUntil = 0;

  // Seen Rook Meteor Fist casts: choose once per jump, not once per frame.
  private rookMeteorSerial = -1;
  private rookMeteorWants = false;
  private rookMeteorReactAt = -1;

  private antiAirCd = 0;
  private aiAirTap = false;
  private airSliceCd = 0;
  private skillCd = 2;
  private seenSwing = -1;
  private seenCharge = false;
  private seen = new Set<number>();
  // SKILL_ZONE_DODGES_V1: one human-timed choice per real ground warning.
  private strikeDecisions = new Map<number, { reactAt: number; evade: boolean; side: number }>();
  private staticFieldChoices = new Map<number, { reactAt: number; evade: boolean }>();
  // KAIZEN_PREDATOR_HOOK_V9: use the second X press instead of waiting for WASD.
  private chainDecisionT = 0;
  // Cache one direction per V bind: don't reroll an animation choice every frame.
  private chainVFollowup: "z" | "x" | "" = "";
  private chainVAlternate = false;
  // EMBER_GROUND_HAZARD_AI_V1_NOV06: bias the detour to one side until clear.
  private fireAvoidSide = 1;
  private fireAvoidKey = "";
  // CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: track the active enemy combo through all beats.
  private comboThreatSerial = -1;
  // CONTINUOUS_PARRY_AI_V4_NOV06: a planned parry attempt is tied to a real combo beat.
  private comboParrySerial = -1;
  private comboParryTarget = -1;
  private comboParryExamined = -1;
  private comboParryReleased = false;
  private ignitionChoices = new Map<number, boolean>();
  // FIGHT_ROYALE_HEAVY_EVADE_DASH_JUMP_V3: one real defensive choice per swing.
  private heavyEscapeSerial = -1;
  private heavyEscapeReactT = 0;
  private heavyEscapeUsed = false;
  // A shield decision tied to a REAL swing, not a permanent turtle mode.
  private zarekGuardSwing = -1;
  private zarekGuardReact = 0;
  private zarekGuardHold = 0;
  private zarekGuardWants = false;
  private zarekGuardPredictCd = 1.3;
  private zarekGuardSeenShots = new Set<number>();

  // Continuous attacks: react to a real incoming beat, not to every animation frame.
  private lastUndodgeableCombo = -1;
  private continuousDodgeReaction = 0;
  private continuousDodgeDone = false;
  // FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V2: CPUs deliberately use and defend counters.
  private counterSeen = false;
  private counterWant = false;
  private counterReactT = 0;
  private incomingCounterSeen = -1;
  private incomingCounterReactT = 0;
  private incomingCounterEvade = false;
  // Personality's brief feints and reposition decisions use ordinary movement inputs.
  private tacticsT = 0;
  private tacticsDir = 1;
  private tacticsCd = 0;
  // EFFECTIVE_RANGE_AWARENESS: choices use the fighter's REAL reach and ready skills.
  // Do not grant AI extra attack range: this only steers its regular movement.
  // COMBAT IQ — situational reads, never direct damage, cooldown edits or teleports.
  // PATTERN_AI_V1: observable habits within a short window. Never reads hidden inputs.
  private patternEnemyId = -1;
  private patternSawSwing = -1;
  private patternWasBlocking = false;
  private patternProjectiles: number[] = [];
  private patternMelee: number[] = [];
  private patternGuard: number[] = [];
  private patternDecisionCd = 2.0;
  private patternReadAt = -1;
  private patternPending: "none" | "ranged" | "melee" | "guard" = "none";
  private patternMode: "none" | "ranged" | "melee" | "guard" = "none";
  private patternModeT = 0;
  private patternOrbitSign = Math.random() < 0.5 ? -1 : 1;

  /** Learning only from observed swing animations and shield raises; no enemy cooldown reads. */
  private observePatterns(f: Fighter, o: Fighter, dt: number) {
    const now = this.threats.now();
    if (this.patternEnemyId !== o.id) {
      this.patternEnemyId = o.id;
      this.patternSawSwing = -1;
      this.patternWasBlocking = false;
      this.patternProjectiles = []; this.patternMelee = []; this.patternGuard = [];
      this.patternMode = "none"; this.patternPending = "none";
      this.patternModeT = 0; this.patternDecisionCd = 2.0;
    }
    const window = 10.0;
    this.patternProjectiles = this.patternProjectiles.filter(t => now - t <= window);
    this.patternMelee = this.patternMelee.filter(t => now - t <= window);
    this.patternGuard = this.patternGuard.filter(t => now - t <= window);
    if (o.state === S.ATTACK && o.atk && o.swingSerial !== this.patternSawSwing) {
      this.patternSawSwing = o.swingSerial;
      const a = o.atk;
      if (["projectile", "lob", "barrel"].includes(a.type))
        this.patternProjectiles.push(now);
      else if (a.type === "melee" || a.type === "phantom")
        this.patternMelee.push(now);
    }
    const blocking = o.state === S.BLOCK;
    if (blocking && !this.patternWasBlocking && o.stateT < 0.32)
      this.patternGuard.push(now);
    this.patternWasBlocking = blocking;
    this.patternModeT = Math.max(0, this.patternModeT - dt);
    this.patternDecisionCd = Math.max(0, this.patternDecisionCd - dt);
    if (this.patternModeT <= 0) this.patternMode = "none";
    const learn = [0, 0.35, 0.68, 0.87][this.iqLevel];
    if (learn <= 0 || f.isDown() || o.isDown() || this.patternDecisionCd > 0) return;
    if (this.patternPending !== "none") {
      if (now < this.patternReadAt) return;
      if (Math.random() < learn) {
        this.patternMode = this.patternPending;
        this.patternModeT = [0, 0.65, 1.1, 1.55][this.iqLevel];
        this.patternOrbitSign = Math.random() < 0.5 ? -1 : 1;
      }
      this.patternPending = "none";
      this.patternDecisionCd = [7.5, 6.0, 4.8, 3.7][this.iqLevel];
      return;
    }
    // Require three distinct events in ten seconds; ties favor the more immediate threat.
    const shots = this.patternProjectiles.length;
    const melee = this.patternMelee.length;
    const guard = this.patternGuard.length;
    const most = Math.max(shots, melee, guard);
    if (most < 3) return;
    this.patternPending = shots === most ? "ranged" : melee === most ? "melee" : "guard";
    this.patternReadAt = now + [1, 0.48, 0.26, 0.16][this.iqLevel];
  }

  /** Footwork adaptation; emergency dodges, hit-confirm, blocking, and cooldowns win. */
  private patternFootwork(f: Fighter, o: Fighter): boolean {
    if (this.patternMode === "none" || this.patternModeT <= 0 || f.isDown() ||
        f.stage || !f.onGround || f.state !== S.IDLE || f.intent.skill ||
        f.intent.block || f.intent.dash.lengthSq() > 0.01 ||
        this.blockWait >= 0 || this.blockHold > 0 || this.sideT > 0 ||
        this.threats.firePatches(f).length > 0 || this.comboParryTarget > this.threats.now())
      return false;
    const delta = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = delta.length();
    if (gap < 0.02) return false;
    const toward = delta.divideScalar(gap);
    const flank = new THREE.Vector3(-toward.z, 0, toward.x).multiplyScalar(this.patternOrbitSign);
    let desired: THREE.Vector3 | null = null;
    if (this.patternMode === "ranged" && gap > 2.35) {
      // Repeated ranged attacks: close diagonally instead of walking straight in.
      desired = toward.clone().multiplyScalar(0.72).addScaledVector(flank, 0.68);
    } else if (this.patternMode === "melee" && gap < (o.attacks.l1?.reach ?? 1.7) + 0.35) {
      // Repeated light rushes: circle outside the enemy weapon's real reach.
      desired = toward.clone().multiplyScalar(-0.64).addScaledVector(flank, 0.72);
    } else if (this.patternMode === "guard" && o.state === S.BLOCK && gap < 2.7) {
      // Frequent shielding: don't mindlessly swing into guard; bait a release.
      desired = toward.clone().multiplyScalar(gap < 1.6 ? -0.8 : -0.15).addScaledVector(flank, 0.8);
    }
    if (!desired || desired.lengthSq() < 0.01) return false;
    desired.normalize();
    // Arena boundary: reverse orbit before choosing an impossible step.
    const next = f.root.position.clone().setY(0).addScaledVector(desired, 1.1);
    if (next.length() > f.arenaRadius - f.radius - 0.25) {
      desired.addScaledVector(flank, -1.8).normalize();
      if (f.root.position.clone().setY(0).addScaledVector(desired, 1.1).length() >
          f.arenaRadius - f.radius - 0.25) return false;
    }
    f.intent.move.copy(desired);
    f.intent.attack = false;
    return true;
  }

  // AI_ENEMY_COOLDOWN_MEMORY_V1: only skills this brain observed are tracked.
  private cdEnemy: Fighter | null = null;
  private cdEnemySwing = -1;
  private cdEnemyMemory = new Map<string, EnemyCooldownMemory>();

  private iqLevel = 1;
  private iqEnemySerial = -1;
  private iqEnemySawActive = false;
  private iqEnemyAllActiveOutside = true;
  private iqEnemyMyHp = 0;
  private iqEnemyMyGuard = 0;
  private iqEnemyWhiffEvaluated = false;
  private iqWhiffSerial = -1;
  private iqWhiffReactAt = -1;
  private iqWhiffExpires = -1;
  private iqWhiffSpent = false;
  private iqOwnSerial = -1;
  private iqOwnTargetHp = 0;
  private iqOwnHitConfirmed = false;
  private iqOwnHitAt = -1;
  private iqOwnFollowWanted = false;
  private iqOwnSkillWanted = false;
  private iqOwnFollowSpent = false;
  private iqBaitCd = rand(3.2, 6.0);
  private iqBaitPhase: "none" | "step" | "retreat" = "none";
  private iqBaitT = 0;
  private iqBaitSide = 1;
  private iqLastEnemySwing = -1;

  /** Observe actual active attacks and health changes; no knowledge of player input.
   * HP changes confirm contact, guard damage disproves a clean whiff. For a
   * clean whiff we must have seen the enemy OUT of range/arc for its full active
   * animation, not just seen an attack go into recovery.
   */
  /** Record a publicly visible Z/X/C/V cast one time per swing. Never inspect
   * the opponent's private cooldown state, upcoming input, or skill queue.
   * Air variants share their normal button's cooldown.
   */
  private observeEnemyCooldown(o: Fighter) {
    if (o !== this.cdEnemy) {
      this.cdEnemy = o;
      this.cdEnemySwing = -1;
      this.cdEnemyMemory.clear();
    }
    if (this.iqLevel === 0 || o.state !== S.ATTACK || !o.atk ||
        o.swingSerial === this.cdEnemySwing) return;
    this.cdEnemySwing = o.swingSerial;
    const match = /^(z|x|c|v)(?:_air)?$/.exec(o.atkId);
    if (!match) return; // Basics, parry counters and special recasts are not skills.
    const slot = match[1];
    const attack = o.attacks[slot] ?? o.atk;
    const cd = attack.cd;
    // Barrel detonation and other recasts do not behave like ordinary cooldowns.
    if (!Number.isFinite(cd) || cd < 1 || attack.type === "barrel") return;
    const major = slot === "v" || cd >= 15 ||
      (attack.dmg >= 155 && cd >= 11) ||
      (attack.repeat >= 3 && cd >= 11);
    if (this.iqLevel === 1 && !major) return;
    if (this.iqLevel === 2 && !major && cd < 8) return;
    const profile = ENEMY_CD_IQ[this.iqLevel];
    if (Math.random() > profile.observe) return; // A missed observation stays missed.
    const now = this.threats.now();
    // Nominal kit CD is visible game knowledge, but perks/charges and temporary
    // modifiers can make the estimate wrong. No o.cooldowns or o.cdMult reads.
    const predicted = cd * (1 + rand(-profile.error, profile.error));
    const power = attack.dmg * Math.min(2.4, Math.sqrt(Math.max(1, attack.repeat)));
    const threat = THREE.MathUtils.clamp(
      0.34 + cd / 46 + power / 630 + (slot === "v" ? 0.18 : 0) +
      (attack.type === "buff" && ["counter", "ward", "static_field", "blood_festival"].includes(attack.mode) ? 0.2 : 0),
      0.28, 1.00);
    this.cdEnemyMemory.set(slot, {
      slot, castAt: now,
      observedAt: now + rand(profile.react[0], profile.react[1]),
      predictedReadyAt: now + predicted,
      nominalCd: cd, threat,
    });
  }

  /** Estimate an offensive window after a visible cast. As the predicted
   * cooldown nears zero, become a little more cautious. Unknown slots remain
   * unknown; a timer that has probably expired never grants free safety.
   */
  private enemyCooldownRead(o: Fighter): { pressure: number; caution: number } {
    if (this.iqLevel === 0 || this.cdEnemy !== o) return { pressure: 0, caution: 0 };
    const now = this.threats.now();
    let pressure = 0, caution = 0;
    for (const [key, memory] of this.cdEnemyMemory) {
      const left = memory.predictedReadyAt - now;
      if (left < -2.0) {
        this.cdEnemyMemory.delete(key); // forget stale estimates
        continue;
      }
      if (now < memory.observedAt) continue;
      // A cast may still be active; memory never tells us to run into it.
      if (left > Math.max(2.1, memory.nominalCd * 0.18)) {
        const confidence = THREE.MathUtils.clamp(
          (left - 1.5) / Math.max(3, memory.nominalCd * 0.28), 0, 1);
        pressure = Math.max(pressure, memory.threat * confidence);
      } else if (left >= -1.4) {
        const soon = 1 - Math.min(1, Math.abs(left - 0.30) / 2.4);
        caution = Math.max(caution, memory.threat * Math.max(0.22, soon));
      }
    }
    // Positioning/offense modifiers are deliberately modest, even on Master.
    const intelligence = [0, 0.45, 0.74, 1.0][this.iqLevel];
    return { pressure: pressure * intelligence, caution: caution * intelligence };
  }

  private iqObserve(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (o.state === S.ATTACK && o.atk && o.swingSerial !== this.iqEnemySerial) {
      this.iqEnemySerial = o.swingSerial;
      this.iqEnemySawActive = false;
      this.iqEnemyAllActiveOutside = true;
      this.iqEnemyMyHp = f.hp;
      this.iqEnemyMyGuard = f.guard;
      this.iqEnemyWhiffEvaluated = false;
      if (this.iqBaitPhase === "step" && o.atkPhase === 0) {
        this.iqBaitPhase = "retreat";
        this.iqBaitT = Math.min(this.iqBaitT + 0.18, 0.46);
      }
      this.iqLastEnemySwing = o.swingSerial;
    }
    if (o.state === S.ATTACK && o.atk && o.swingSerial === this.iqEnemySerial) {
      if (o.atkPhase === 1 && (o.atk.type === "melee" || o.atk.type === "phantom")) {
        this.iqEnemySawActive = true;
        const flat = o.root.position.clone().sub(f.root.position).setY(0);
        const gap = flat.length();
        const toward = f.root.position.clone().sub(o.root.position).setY(0);
        const facing = new THREE.Vector3(Math.sin(o.root.rotation.y), 0, Math.cos(o.root.rotation.y));
        const inArc = toward.lengthSq() < 0.001 || facing.dot(toward.normalize()) > 0.15;
        // Conservative: only a clearly missed swing qualifies, no presumed free punishes.
        const outside = gap > o.atk.reach + f.radius + 0.20 || !inArc;
        this.iqEnemyAllActiveOutside = this.iqEnemyAllActiveOutside && outside;
      }
      if (o.atkPhase === 2 && !this.iqEnemyWhiffEvaluated) {
        this.iqEnemyWhiffEvaluated = true;
        const remaining = o.atk.wind + o.atk.active + o.atk.recover - o.stateT;
        const simpleMelee = o.atk.type === "melee" && o.atk.repeat <= 1 &&
          !["chain_razor_cyclone", "chain_death_spiral", "nesa_spin", "nesa_air_spin"].includes(o.atk.style);
        const didNotConnect = f.hp >= this.iqEnemyMyHp - 0.1 &&
          f.guard >= this.iqEnemyMyGuard - 0.1;
        const profile = COMBAT_IQ[this.iqLevel];
        if (simpleMelee && this.iqEnemySawActive && this.iqEnemyAllActiveOutside &&
            didNotConnect && remaining > profile.react[0] + 0.10 &&
            Math.random() < profile.punish) {
          this.iqWhiffSerial = o.swingSerial;
          this.iqWhiffReactAt = now + rand(profile.react[0], profile.react[1]);
          this.iqWhiffExpires = now + Math.max(0, remaining - 0.03);
          this.iqWhiffSpent = false;
        }
      }
    }
    // A hit-confirm only uses an observed HP loss after this fighter attacked.
    // An opponent holding BLOCK with guard loss does not count as a confirmed hit.
    if (f.state === S.ATTACK && f.atk && f.swingSerial !== this.iqOwnSerial) {
      this.iqOwnSerial = f.swingSerial;
      this.iqOwnTargetHp = o.hp;
      this.iqOwnHitConfirmed = false;
      this.iqOwnHitAt = -1;
      this.iqOwnFollowWanted = false;
      this.iqOwnSkillWanted = false;
      this.iqOwnFollowSpent = false;
    }
    if (f.state === S.ATTACK && f.atk && f.swingSerial === this.iqOwnSerial &&
        f.atkPhase >= 1 && !this.iqOwnHitConfirmed &&
        o.hp < this.iqOwnTargetHp - 0.5 &&
        // A status-effect damage tick alone is not a reliable combo confirm.
        (o.state === S.HITSTUN || o.state === S.STAGGER || o.state === S.KNOCKDOWN)) {
      this.iqOwnHitConfirmed = true;
      this.iqOwnHitAt = now;
      // Roll once per connected swing, never reroll every frame until success.
      this.iqOwnFollowWanted = Math.random() < COMBAT_IQ[this.iqLevel].combo;
      this.iqOwnSkillWanted = Math.random() < COMBAT_IQ[this.iqLevel].combo * 0.55;
    }
  }

  /** Legal, ready damaging skills only. No free V on Easy/Normal/Hard CPUs.
   * In particular, no defensive buffs, counters or mines masquerade as punishes.
   */
  private iqFollowSkill(f: Fighter, o: Fighter, gap: number, remaining: number): string | null {
    let best: string | null = null;
    let bestScore = -1e5;
    for (const key of ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]) {
      const a = f.attacks[key];
      if (!a || (f.cooldowns[key] ?? 1) > 0 || a.dmg <= 0 ||
          (f.kit === "sickle" && f.bloodFestivalT > 0) ||
          (a.style === "nesa_heart_slam" && f.nesaCCharges <= 0)) continue;
      if (a.wind + 0.035 >= remaining) continue;
      let inRange = false;
      if (a.type === "melee" || a.type === "phantom")
        inRange = gap <= a.reach + Math.min(0.45, a.lunge * 0.08);
      else if (a.type === "strike")
        inRange = a.at !== "self" || gap <= a.radius + 0.12;
      else if (a.type === "projectile")
        inRange = gap <= 8.5 && gap / Math.max(0.1, a.speed) + a.wind < remaining;
      // Lob, mine, blast-zone, blink and buffs are deliberately not guaranteed combos.
      if (!inRange) continue;
      const score = a.dmg / 95 + a.stun * 0.85 - a.wind * 1.8 -
        (a.type === "projectile" ? gap * 0.11 : 0) +
        (a.effect ? 0.36 : 0) + rand(-0.12, 0.12);
      if (score > bestScore) { best = key; bestScore = score; }
    }
    return best;
  }

  /** Timed pressure reacts to confirmed contact, verified whiffs, and baited
   * approaches. All actions are normal intent movement/buttons, never special AI hits.
   * Returns true only when taking an offensive input or holding a feint movement.
   */
  private combatIQAction(f: Fighter, o: Fighter, dt: number): boolean {
    const profile = COMBAT_IQ[this.iqLevel];
    const now = this.threats.now();
    this.iqBaitCd = Math.max(0, this.iqBaitCd - dt);
    if (f.isDown() || o.isDown() || f.chainBindT > 0 || f.chainBoundBy ||
        this.blockWait >= 0 || this.blockHold > 0 || this.sideT > 0 ||
        f.intent.block || f.intent.dash.lengthSq() > 0.01 ||
        this.comboParryTarget > now ||
        (f.kit === "sickle" && f.bloodFestivalT > 0)) {
      this.iqBaitPhase = "none";
      return false;
    }
    const delta = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = delta.length();
    if (gap < 0.01) return false;
    const toward = delta.divideScalar(gap);
    const free = f.state === S.IDLE || (f.state === S.ATTACK && f.atkPhase === 2);

    // Hit-confirmed light string: buffer precisely one next click through the
    // existing Fighter.requestLight combo system. Do not blindly mash full combos.
    if (f.state === S.ATTACK && f.atk && /^l\d+$/.test(f.atkId) &&
        !!f.atk.next && this.iqOwnHitConfirmed && this.iqOwnFollowWanted &&
        !this.iqOwnFollowSpent && f.atkPhase >= 1 && f.onGround &&
        gap <= (f.attacks[f.atk.next]?.reach ?? f.atk.reach) + 0.40) {
      this.iqOwnFollowSpent = true;
      this.queue = [[0, 0.060]];
      this.hold = 0;
      this.theaterFollow = "";
      this.theaterFollowT = 0;
      return true;
    }
    // If an attack connects but ends the light string, link to a *ready* skill
    // only if there is actual time to cast before the target can recover.
    if (f.state === S.ATTACK && f.atk && !f.atk.next &&
        this.iqOwnHitConfirmed && this.iqOwnSkillWanted &&
        !this.iqOwnFollowSpent && f.atkPhase === 2 &&
        (o.state === S.HITSTUN || o.state === S.STAGGER)) {
      const left = Math.max(0, o.stunRemaining);
      const key = this.iqFollowSkill(f, o, gap, left);
      if (key) {
        f.intent.skill = key;
        this.queue = []; this.hold = 0;
        this.iqOwnFollowSpent = true;
        this.skillCd = Math.max(this.skillCd, 0.24);
        return true;
      }
    }

    // Whiff punish: only a swing visibly missed in its whole active window;
    // respect reaction delay, opponent remaining recovery and our real attack windup.
    if (!this.iqWhiffSpent && this.iqWhiffSerial === o.swingSerial &&
        now >= this.iqWhiffReactAt && now < this.iqWhiffExpires &&
        o.state === S.ATTACK && o.atkPhase === 2 && free) {
      const left = Math.min(this.iqWhiffExpires - now,
        o.atk ? o.atk.wind + o.atk.active + o.atk.recover - o.stateT : 0);
      const key = this.iqFollowSkill(f, o, gap, left);
      if (key) {
        f.intent.skill = key;
        this.queue = []; this.hold = 0;
        this.iqWhiffSpent = true;
        this.iqBaitPhase = "none";
        this.theaterFollow = "";
        this.theaterFollowT = 0;
        this.skillCd = Math.max(this.skillCd, 0.22);
        return true;
      }
      const light = f.attacks.l1;
      if (f.state === S.IDLE && light && gap <= light.reach + 0.18 &&
          light.wind + 0.055 < left && f.atkLock <= 0) {
        this.queue = [[0, 0.062]]; this.hold = 0;
        this.iqWhiffSpent = true;
        this.iqBaitPhase = "none";
        this.theaterFollow = "";
        this.theaterFollowT = 0;
        return true;
      }
      if (f.state === S.IDLE && light && f.onGround && gap <= light.reach + 1.6 &&
          left > light.wind + 0.24 && this.threats.firePatches(f).length === 0) {
        f.intent.move.copy(this.theaterDirection(f, o, toward));
        // Real movement only: close in for a punish, no teleport or free dash.
        return true;
      }
    }

    // Fake a short approach then pull out of the enemy's range. On success the
    // observed swing may create a whiff window. No attack or guard input is faked.
    if (this.iqBaitPhase !== "none") {
      if (!f.onGround || f.state !== S.IDLE || f.stage ||
          this.threats.firePatches(f).length > 0) {
        this.iqBaitPhase = "none";
        return false;
      }
      this.iqBaitT = Math.max(0, this.iqBaitT - dt);
      if (this.iqBaitPhase === "step" && (o.state === S.ATTACK || this.iqBaitT <= 0)) {
        this.iqBaitPhase = "retreat";
        this.iqBaitT = rand(0.24, 0.41);
      }
      if (this.iqBaitPhase === "retreat" && this.iqBaitT <= 0) {
        this.iqBaitPhase = "none";
        return false;
      }
      const tangent = new THREE.Vector3(-toward.z, 0, toward.x);
      const preferred = this.iqBaitPhase === "step" ?
        toward.clone().addScaledVector(tangent, this.iqBaitSide * 0.16) :
        toward.clone().negate().addScaledVector(tangent, this.iqBaitSide * 0.56);
      // Never override a real warning/dodge, including nearby active attack arcs.
      if (o.state === S.ATTACK && o.atkPhase === 1 && o.atk &&
          gap <= o.atk.reach + f.radius + 0.5) return false;
      f.intent.move.copy(this.theaterDirection(f, o, preferred));
      return true;
    }
    if (profile.bait <= 0 || this.iqBaitCd > 0 || f.stage || !f.onGround ||
        f.state !== S.IDLE || o.state !== S.IDLE || RANGED.has(f.kit) ||
        this.queue.length > 0 || this.hold > 0 ||
        this.threats.firePatches(f).length > 0 ||
        this.theaterT > 0 || this.theaterFollow || this.tacticsT > 0) return false;
    const enemyReach = o.attacks.l1?.reach ?? 1.75;
    if (gap < enemyReach + 0.18 || gap > enemyReach + 1.55 ||
        Math.random() >= profile.bait * (FIGHT_STYLES[f.look.name.toLowerCase()]?.bait ?? 0.5)) {
      this.iqBaitCd = rand(profile.feintCd[0], profile.feintCd[1]);
      return false;
    }
    this.iqBaitCd = rand(profile.feintCd[0], profile.feintCd[1]);
    this.iqBaitPhase = "step";
    this.iqBaitT = rand(0.16, 0.31);
    this.iqBaitSide = Math.random() < 0.5 ? -1 : 1;
    f.intent.move.copy(this.theaterDirection(f, o, toward));
    return true;
  }

  // ADVANCED_FOOTWORK: one grounded steering plan per read; no instant turn or teleport.
  private advancedEnemy: Fighter | null = null;
  private advancedMode: "none" | "escape" | "orbit" | "flank" | "corner" = "none";
  private advancedPlanUntil = 0;
  private advancedRetryAt = 0;
  private advancedSide = Math.random() < 0.5 ? -1 : 1;
  private advancedLastDir = new THREE.Vector3();
  private advancedSampleAt = -1;
  private advancedSamplePos = new THREE.Vector3();

  // V8: no automatic low-health retreat, recover, heal, or edge stalling.

  private rangeOrbitCd = 0;
  private rangeOrbitSign = Math.random() < 0.5 ? -1 : 1;

  private effectiveRangeBand(f: Fighter, o: Fighter): { ideal: number; near: number; far: number } {
    const style = FIGHT_STYLES[f.look.name.toLowerCase()];
    const basicReach = Math.max(1.1, f.attacks.l1?.reach ?? 1.7);
    const enemyReach = Math.max(1.1, o.attacks.l1?.reach ?? 1.7);
    const ranged = RANGED.has(f.kit);
    // Melee fighters normally work near the outer half of their weapon reach,
    // not standing on the opponent's feet. Short-armed brawlers must close in.
    let ideal = ranged ? (style?.range ?? 5.3) :
      Math.max(1.06, Math.min(basicReach - 0.18, (style?.range ?? basicReach) * 0.94));
    if (!ranged) {
      if (basicReach > enemyReach + 0.45) ideal = Math.min(basicReach - 0.16, ideal + 0.22);
      if (basicReach < enemyReach - 0.5) ideal = Math.max(1.08, ideal - 0.23);
      // Temporarily fight at a real ready skill's range. As soon as it is used,
      // go back to weapon range. This makes projectile-capable melee fighters
      // alternate between zoning and sword pressure rather than face-hugging.
      const vAvailable = "bonusSkillUnlocked" in f && f.bonusSkillUnlocked === true;
      const keys = ["z", "x", "c", ...(vAvailable ? ["v"] : [])];
      for (const key of keys) {
        const a = f.attacks[key];
        if (!a || (f.cooldowns[key] ?? 1) > 0 || f.chainBindT > 0) continue;
        if (a.style === "chain_predator_hook" && o.state !== S.BLOCK) {
          ideal = Math.max(ideal, Math.min(3.85, a.reach - 0.78));
        } else if (a.type === "projectile" && a.speed > 0) {
          ideal = Math.max(ideal, Math.min(4.75, basicReach + 2.0));
        } else if (a.type === "strike" && a.at === "self" && a.radius > basicReach + 0.65) {
          ideal = Math.max(ideal, Math.min(3.25, a.radius - 0.66));
        } else if ((a.type === "melee" || a.type === "phantom") && a.reach > basicReach + 1.0) {
          ideal = Math.max(ideal, Math.min(3.8, a.reach - 0.7));
        }
      }
    }
    // Keep a comfortable band, rather than alternating forward/back each frame.
    ideal = THREE.MathUtils.clamp(ideal, 1.05, ranged ? 6.35 : 5.0);
    const margin = ranged ? 0.7 : Math.max(0.28, Math.min(0.48, ideal * 0.13));
    return { ideal, near: Math.max(0.9, ideal - margin), far: ideal + margin };
  }


  private seenClashSwing = -1;
  // NESA_DODGE_KIRA_AIR_3_V1: dodge Nesa's dangerous hammer swings rather than merely guarding them.
  private nesaThreatSerial = -1;
  private nesaEvadeChosen = false;
  private nesaHeartBlockChosen = false;
  private nesaEvadeUsed = false;
  private nesaEvadeTrigger = 0;
  private nesaRetreatT = 0;
  private nesaDodgeSide = 1;
  private nesaRetreatDir = new THREE.Vector3();
  // NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: independently plan the later giant smash.
  private nesaGiantEvadeUsed = false;
  private nesaGiantEvadeChosen = false;




  // AI_PERSONALITY_THEATER_2_V1 — distinct movement + follow-up decisions for all 17.
  // Deliberately uses only ordinary controls: move, jump, dash, attack, equipped skill.
  // Enemy defense, cooldowns, hit tests, and arena bounds remain authoritative.
  // CHARACTER_STYLES_V1: single tactical decision per short observation window.
  private personaEnemy: Fighter | null = null;
  private personaNextAt = -1;
  private personaMode: PersonalityPlan = "none";

  private theaterCd = rand(0.9, 2.1);
  private theaterT = 0;
  private theaterMode: "none" | "back" | "circle" | "chase" = "none";
  private theaterFollow = "";
  private theaterFollowT = 0;
  private theaterJump = false;
  private theaterDash = false;
  private theaterSide = 1;
  private theaterLastGap = 99;
  private theaterComboCd = 0;
  private theaterLastTargetSwing = -1;

  /** Named skills are looked up AFTER loadout remapping; missing skills never fire. */
  private theaterKey(f: Fighter, name: string): string | null {
    const key = ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])].find(k =>
      f.attacks[k]?.name === name && (f.cooldowns[k] ?? 1) <= 0);
    if (!key) return null;
    const a = f.attacks[key];
    if (f.kit === "sickle" && f.bloodFestivalT > 0) return null;
    if (a.style === "nesa_heart_slam" && f.nesaCCharges <= 0) return null;
    return key;
  }

  private theaterPlan(mode: "back" | "circle" | "chase", t: number,
      follow: string, jump = false, dash = false) {
    this.theaterMode = mode;
    this.theaterT = t;
    this.theaterFollow = follow;
    this.theaterFollowT = t + 1.65;
    this.theaterJump = jump;
    this.theaterDash = dash;
    this.theaterSide = Math.random() < 0.5 ? -1 : 1;
    // Don't finish an old preplanned combo after deciding to disengage.
    this.queue = [];
    this.hold = 0;
    this.tacticsT = 0;
  }

  /** Find a useful movement direction that actually fits inside the circular arena.
   * This is a steering choice, not a teleport. Projectile/fire avoidance runs later.
   */
  private theaterDirection(f: Fighter, o: Fighter, preference: THREE.Vector3): THREE.Vector3 {
    const at = f.root.position.clone().setY(0);
    const toward = o.root.position.clone().sub(at).setY(0);
    if (toward.lengthSq() < 0.001) toward.set(0, 0, 1);
    toward.normalize();
    const lateral = new THREE.Vector3(-toward.z, 0, toward.x);
    const center = at.clone().negate();
    if (center.lengthSq() > 0.001) center.normalize();
    const target = preference.lengthSq() > 0.001 ? preference.clone().normalize() : toward;
    const choices = [
      target.clone(),
      target.clone().addScaledVector(lateral, 0.75).normalize(),
      target.clone().addScaledVector(lateral, -0.75).normalize(),
      lateral.clone(), lateral.clone().negate(),
      target.clone().addScaledVector(center, 0.8).normalize(),
      center.clone(),
    ];
    const cap = Math.max(1.5, f.arenaRadius - f.radius - 0.28);
    const ahead = f.dashCd <= 0 && f.onGround ? 3.3 : 1.15;
    let best = target, score = -Infinity;
    for (const dir of choices) {
      if (dir.lengthSq() < 0.001) continue;
      const dest = at.clone().addScaledVector(dir, ahead);
      if (dest.length() > cap) dest.setLength(cap);
      const displacement = dest.clone().sub(at);
      const actual = displacement.length();
      const alignment = actual > 0.001 ? displacement.normalize().dot(target) : -1;
      const value = alignment * 2.1 + actual * 0.44 - (actual < ahead * 0.28 ? 2.2 : 0);
      if (value > score) { score = value; best = dir; }
    }
    return best.clone().normalize();
  }

  /** Start recognizable mini-sequences: step away, entice a miss, then come back
   * with the fighter's real equipped move. Low HP changes temperament by class.
   */
  private theaterFootwork(f: Fighter, o: Fighter, dt: number) {
    if (f.stage || f.isDown()) return;
    const id = f.look.name.toLowerCase();
    const style = FIGHT_STYLES[id];
    if (!style) return;
    const delta = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = delta.length();
    if (gap < 0.01) return;
    const toward = delta.divideScalar(gap);
    const lateral = new THREE.Vector3(-toward.z, 0, toward.x);
    const punish = this.hasPunishWindow(o);
    const hostileSwing = o.state === S.ATTACK && o.atkPhase === 0 &&
      !!o.atk && o.atk.type === "melee" && gap < o.atk.reach + 0.95;
    const chased = gap < this.theaterLastGap - 0.06;
    this.theaterLastGap = gap;
    this.theaterComboCd = Math.max(0, this.theaterComboCd - dt);
    this.theaterCd = Math.max(0, this.theaterCd - dt);
    this.theaterFollowT = Math.max(0, this.theaterFollowT - dt);
    if (this.theaterFollowT <= 0) this.theaterFollow = "";

    // Existing projectile evasions, Nesa dodge, parry, and hazard reactions outrank
    // voluntary showmanship. Never cancel an already committed attack to perform it.
    const free = f.state === S.IDLE || f.state === S.BLOCK;
    if (this.theaterMode !== "none" && this.theaterT > 0) {
      this.theaterT = Math.max(0, this.theaterT - dt);
      if (free && this.sideT <= 0 && this.blockWait < 0 && this.blockHold <= 0) {
        const spacing = this.effectiveRangeBand(f, o);
        const preferred = this.theaterMode === "back" ?
          (gap > spacing.far + 0.25 ? lateral.clone().multiplyScalar(this.theaterSide) :
            toward.clone().negate().addScaledVector(lateral, this.theaterSide * 0.3)) :
          this.theaterMode === "circle" ? lateral.clone().multiplyScalar(this.theaterSide)
            .addScaledVector(toward, gap > spacing.ideal ? 0.27 : -0.15) :
          gap <= spacing.near ? lateral.clone().multiplyScalar(this.theaterSide).addScaledVector(toward, -0.2) : toward;
        const safe = this.theaterDirection(f, o, preferred);
        f.intent.move.copy(safe);
        if (this.theaterJump && f.onGround) {
          f.intent.jump = true;
          this.theaterJump = false;
        }
        if (this.theaterDash && f.onGround && f.dashCd <= 0 &&
            f.state === S.IDLE && this.theaterT > 0.10) {
          f.intent.dash.copy(safe);
          this.theaterDash = false;
        }
      }
      if (this.theaterT <= 0) this.theaterMode = "none";
      return;
    }
    this.theaterMode = "none";
    if (!free || !f.onGround || this.sideT > 0 || this.blockHold > 0 ||
        this.blockWait >= 0 || this.theaterCd > 0 || this.theaterFollow) return;

    const hp = f.hp / Math.max(f.maxHp, 1);
    // Characters with low health aren't all cowards: Kira/Rook/Veyr keep pushing.
    const aggressive = id === "kira" || id === "rook" || id === "veyr";
    const caution = hp < 0.35 && !aggressive;
    const intensity = 0.65 + this.p.block * 0.65;
    const intent = (prob: number) => Math.random() < prob * intensity;
    // A little randomness is desirable, but the follow-up itself is deliberate.
    this.theaterCd = rand(1.35, 3.05) * this.p.think;
    switch (id) {
      case "aster":
        if (gap < 2.75 && (o.state === S.BLOCK || hostileSwing) && intent(0.68))
          this.theaterPlan("back", 0.30, "Shield Bash", false, false);
        else if (punish && gap < 3.3) this.theaterPlan("chase", 0.26, "Rising Slash", false, false);
        break;
      case "vesper":
        if (gap < 2.8 && !punish && intent(0.78))
          this.theaterPlan("back", 0.26, "combo3", false, false);
        else if (punish && gap < 4.1) this.theaterPlan("chase", 0.24, "combo3", false, true);
        break;
      case "garrick":
        if (gap < 3.2 && (hostileSwing || o.state === S.BLOCK) && intent(0.80))
          this.theaterPlan("back", 0.35, "charge", false, false);
        else if (punish && gap < 3.6) this.theaterPlan("chase", 0.32, "Titan Cleave", false, false);
        break;
      case "kaede":
        if (hostileSwing && gap < 2.7 && intent(0.85))
          this.theaterPlan("circle", 0.14, "Counter Stance", false, false);
        else if (punish && gap < 3.1) this.theaterPlan("chase", 0.26, "Thousand Cuts", false, false);
        else if (gap < 2.8 && o.state === S.BLOCK) this.theaterPlan("circle", 0.34, "charge");
        break;
      case "ember":
        if (gap < 5.0 && (chased || hostileSwing || caution) && intent(0.85))
          this.theaterPlan("back", 0.36, "Fireball Volley", gap < 2.7, gap < 2.3);
        else if (gap > 3.7 && punish) this.theaterPlan("circle", 0.25, "charge");
        break;
      case "marina":
        if (gap < 4.4 && (chased || caution) && intent(0.80))
          this.theaterPlan("back", 0.34, "Tidal Ring", false, gap < 2.1);
        else if (gap < 2.6 && hostileSwing) this.theaterPlan("circle", 0.23, "Bubble Ward");
        break;
      case "nyx":
        // Signature: leap backwards, bait pursuit, then teleport back with Smoke Step.
        if (gap < 3.55 && this.theaterKey(f, "Smoke Step") &&
            (chased || hostileSwing || o.state === S.IDLE) && intent(0.93))
          this.theaterPlan("back", 0.44, "Smoke Step", true, false);
        else if (punish && gap < 3.8) this.theaterPlan("chase", 0.22, "Phantom Rush", false, true);
        break;
      case "rook":
        // Rook hates dead air and uses real forward dashes to keep punches flowing.
        if (gap > 1.85 && gap < 5.3 && intent(0.90))
          this.theaterPlan("chase", 0.29, "Rush", false, gap > 2.7);
        else if (gap < 2.2 && o.state === S.BLOCK && intent(0.50))
          this.theaterPlan("back", 0.18, "combo4");
        break;
      case "gale":
        if (gap < 4.4 && intent(0.80))
          this.theaterPlan(gap > 2.5 ? "chase" : "circle", 0.41,
            "Wind Step", true, gap > 3.5);
        break;
      case "bob":
        if (gap < 5.0 && (chased || caution || o.state === S.IDLE) && intent(0.90))
          this.theaterPlan("back", 0.35, "Land Mine", gap < 2.5, gap < 2.0);
        else if (gap > 3.3) this.theaterPlan("circle", 0.27, "Paralyze Bomb");
        break;
      case "kira":
        // The opposite of Nyx: advance immediately after knockback/recovery.
        if (gap > 1.7 && gap < 6.8 && intent(0.96))
          this.theaterPlan("chase", 0.36, punish ? "combo4" : "Cyclone Kick",
            false, f.dashCd <= 0 && gap > 2.65);
        else if (gap < 2.5 && punish) this.theaterPlan("chase", 0.19, "combo4");
        break;
      case "raven":
        if (gap < 4.0 && (chased || hostileSwing || caution) && intent(0.88))
          this.theaterPlan("back", 0.27, "Blink", false, false);
        else if (gap > 3.1 && punish) this.theaterPlan("circle", 0.23, "Thunderstorm");
        break;
      case "ash":
        if (gap < 5.1 && (chased || hostileSwing || caution) && intent(0.88))
          this.theaterPlan("back", 0.37, "Hunter's Snare", gap < 3.2, gap < 2.4);
        else if (gap > 3.5 && punish) this.theaterPlan("circle", 0.20, "charge");
        break;
      case "veyr":
        if (hostileSwing && gap < 2.7 && intent(0.79))
          this.theaterPlan("circle", 0.14, "Death Feint");
        else if (gap > 1.9 && gap < 4.6 && intent(0.88))
          this.theaterPlan("chase", 0.26, f.bloodFestivalT > 0 ? "combo4" : "Blood Festival",
            false, f.dashCd <= 0 && gap > 3);
        break;
      case "zarek":
        if (punish && gap < 4.0) this.theaterPlan("chase", 0.27, "Phantom Spiral", false, gap > 2.9);
        else if (o.state === S.BLOCK && gap < 3.2) this.theaterPlan("circle", 0.31, "Serpent Wheel");
        break;
      case "kaizen":
        // Remain at chain range: retreat from fists, then hook escaping prey.
        if (gap < 2.2 && (hostileSwing || chased) && intent(0.86))
          this.theaterPlan("back", 0.33, "Predator's Hook", false, false);
        else if (gap > 2.5 && gap < 4.7 && !hostileSwing && intent(0.68))
          this.theaterPlan("circle", 0.26, "Predator's Hook");
        else if (punish && gap < 3.6) this.theaterPlan("chase", 0.22, "Thousand Cuts: Death Spiral");
        break;
      case "nesa":
        if (gap < 3.0 && hostileSwing && intent(0.83))
          this.theaterPlan("circle", 0.26, "Pink Heart Smash");
        else if (gap > 2.7 && gap < 4.2 && intent(0.83))
          this.theaterPlan("chase", 0.31, "Upsie Daisie", false, gap > 4.5);
        else if (gap < 2.8 && (punish || o.state === S.BLOCK))
          this.theaterPlan("circle", 0.20, "Pink Heart Smash");
        break;
    }
  }

  /** Follow through after the movement rather than selecting a random unrelated skill.
   * When the equipped move is unavailable or out of range, regular offense resumes.
   */
  private theaterOffense(f: Fighter, o: Fighter): boolean {
    if (f.stage || !this.theaterFollow || this.theaterFollowT <= 0) return false;
    if (this.theaterT > 0) return true; // first actually finish the bait / chase movement
    if (f.state !== S.IDLE || this.blockHold > 0 || this.blockWait >= 0 ||
        this.comboParryTarget > this.threats.now() || this.queue.length || this.hold > 0) return false;
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    let follow = this.theaterFollow;
    const finish = () => { this.theaterFollow = ""; this.theaterFollowT = 0; };
    // Don't spin in empty air; wait briefly for the baited enemy to reach attack range.
    if (follow.startsWith("combo")) {
      const reach = (f.attacks.l1?.reach || 1.8) + 0.33;
      if (gap > reach && gap < reach + 3.0 && f.onGround &&
          ["vesper", "rook", "kira", "veyr", "zarek"].includes(f.look.name.toLowerCase())) {
        // Re-enter a combo at REAL dash speed, rather than swinging at empty air.
        const to = o.root.position.clone().sub(f.root.position).setY(0);
        const safe = this.theaterDirection(f, o, to);
        f.intent.move.copy(safe);
        if (f.dashCd <= 0 && gap > reach + 0.7) f.intent.dash.copy(safe);
        return true;
      }
      if (gap > reach || this.theaterComboCd > 0) return false;
      const max = Math.max(1, Math.min(this.p.combo,
        Number(follow.replace("combo", "")) || 2,
        Object.keys(f.attacks).filter(k => /^l\d+$/.test(k)).length));
      for (let i = 0; i < max; i++) this.queue.push([i === 0 ? 0 : 0.18, 0.065]);
      this.theaterComboCd = rand(0.65, 1.0);
      finish();
      return true;
    }
    if (follow === "charge") {
      const longRange = RANGED.has(f.kit) || f.kit === "bomb";
      if (!longRange && gap > (f.attacks.heavy?.reach || 2.3) + 0.4) return false;
      this.queue = [[0, HOLD_T + rand(0.35, 0.66)]];
      finish();
      return true;
    }
    const key = this.theaterKey(f, follow);
    if (!key) { finish(); return false; }
    const a = f.attacks[key];
    const isBlink = a.type === "blink";
    const inRange = isBlink ? (a.mode === "behind" ? gap < 5.3 : gap < 6.4) :
      a.name === "Upsie Daisie" ? gap <= Math.min(3.35, a.reach + 0.72) :
      a.type === "melee" || a.type === "phantom" ?
        gap <= Math.max(a.reach + Math.min(1.15, a.lunge * 0.19), a.type === "phantom" ? 4.2 : 1.8) :
      a.type === "strike" && a.at === "self" ? gap <= a.radius + 0.35 :
      a.type === "mine" ? gap < 5.0 :
      a.type === "projectile" || a.type === "lob" ? gap < 9.5 : true;
    if (!inRange) {
      if (a.type === "melee" && gap < Math.max(5.0, a.reach + 2.7) && f.onGround &&
          ["aster", "vesper", "rook", "kira", "zarek", "gale", "nesa"].includes(f.look.name.toLowerCase())) {
        const safe = this.theaterDirection(f, o,
          o.root.position.clone().sub(f.root.position).setY(0));
        f.intent.move.copy(safe);
        if (f.dashCd <= 0 && gap > a.reach + 1.0) f.intent.dash.copy(safe);
        return true;
      }
      return false;
    }
    // A failed feint/counter is punishable. Don't cast it if nobody is attacking.
    if (a.mode === "blood_feint" || a.mode === "counter") {
      if (o.state !== S.ATTACK || o.atkPhase !== 0) return false;
    }
    if (a.mode === "blood_festival" && gap > 3.4) return false;
    f.intent.skill = key;
    this.skillCd = rand(this.p.skill[0], this.p.skill[1]);
    finish();
    return true;
  }

  // VEYR_FESTIVAL_RELENTLESS_AI_V1_20261107
  // During Blood Festival, stop parry / shield planning and keep the four-hit
  // light string moving. Real input taps only: animation, cooldowns, guard and
  // collision remain completely unchanged. No AI-only attack-speed buff.
  private festivalTapDown = false;
  private festivalTapSwing = -1;

  private veyrFestivalPressure(f: Fighter, o: Fighter, dt: number): boolean {
    if (f.kit !== "sickle" || f.bloodFestivalT <= 0 || f.isDown()) {
      this.festivalTapDown = false;
      this.festivalTapSwing = -1;
      return false;
    }

    // Undo old defensive decisions made before the ultimate began. Without
    // these resets the older reactive AI keeps Veyr shield-locked for seconds.
    this.blockWait = -1;
    this.blockDur = 0;
    this.blockHold = 0;
    this.comboParryTarget = -1;
    this.comboParryReleased = false;
    this.queue = [];
    this.hold = 0;
    this.jumpWait = -1;
    this.sideT = 0;
    this.tacticsT = 0;
    this.theaterT = 0;
    this.theaterMode = "none";
    this.theaterFollow = "";
    this.theaterFollowT = 0;

    // Blood Festival locks Veyr's other skills. Do not waste time trying them.
    f.intent.block = false;
    f.intent.skill = "";
    f.intent.jump = false;
    f.intent.attack = false;

    const to = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = to.length();
    if (gap > 0.001) to.divideScalar(gap);
    const reach = f.attacks.l1?.reach ?? 1.65;

    // Move forward rather than retreat to block. Normal arena clamps, dash
    // cooldown and sprint movement continue to apply (no teleport/bonus speed).
    if (gap > reach * 0.79 && gap > 0.05) {
      if (f.stage) f.intent.move.set(Math.sign(to.x), 0, 0);
      else f.intent.move.copy(to);
      if (f.onGround && f.state === S.IDLE && gap > 3.1 && gap < 8 && f.dashCd <= 0) {
        f.intent.dash.copy(f.intent.move);
      }
      f.intent.sprint = f.onGround && f.state === S.IDLE && gap > 2.5;
    } else {
      f.intent.move.set(0, 0, 0);
      f.intent.sprint = false;
    }
    // Keep the pursuit while making safe detours around ground fire; this
    // helper only adjusts movement, never raises a shield.
    this.avoidFireGround(f);

    // A real light tap requires one pressed frame and a released frame.
    // Fighter buffers a follow-up only after the previous light has started;
    // one tap per swingSerial prevents spamming several inputs too early.
    if (this.festivalTapDown) {
      this.festivalTapDown = false;
      return true;
    }
    const start = f.onGround && (f.state === S.IDLE || f.state === S.BLOCK) &&
      gap <= reach + 0.28;
    const next = f.onGround && f.state === S.ATTACK &&
      /^l[1-3]$/.test(f.atkId) && !!f.atk?.next &&
      f.stateT >= f.atk.wind + 0.015 &&
      this.festivalTapSwing !== f.swingSerial && gap <= reach + 1.1;
    if (start || next) {
      f.intent.attack = true;
      this.festivalTapDown = true;
      this.festivalTapSwing = f.swingSerial;
    }
    return true;
  }

  // AI_READY_SKILLS_VEYR_FESTIVAL_V1_20261107
  // Check actual equipped cooldowns frequently instead of waiting seconds
  // between idle decisions. Still uses the fighter's normal skill inputs.
  private readySkillPoll = 0;
  // Roxy uses a short, difficulty-scaled plan that is evaluated before
  // ordinary attack IQ can keep her locked into endless light-attack queues.
  private nesaVThreat = -1;
  private nesaVReactAt = 0;
  private nesaVChose = false;
  private nesaVUsed = false;
  private roxySkillReadAt = 0;
  private roxyTarget = -1;

  /** Roxy's actual kit is not a generic melee skill set:
   * Z is four-charge damage prevention, X is an automatic FREEZE summon,
   * C is targeted meteor, and Master-only V is stationary Frostwing artillery.
   * Samples visible opportunities and issues ONE legal skill press. No free
   * cooldowns, HP, hits, extra summons or fourth-skill unlocks.
   */
  // Zenith isn't Zarek. She makes distinct in-hand, thrown-spear, and recall plans.
  private nesaTimedVParry(f: Fighter, o: Fighter): boolean {
    if (f.kit !== "hammer" || !f.bonusSkillUnlocked || f.isDown() || o.isDown() ||
        !f.onGround || f.status.has("freeze") ||
        !f.attacks.v || f.attacks.v.style !== "nesa_high_striker" ||
        (f.cooldowns.v ?? 1) > 0 || ![S.IDLE,S.BLOCK,S.CHARGE].includes(f.state)) return false;
    const now = this.threats.now();
    const dist = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const current = o.atk;
    const meleeIncoming = o.state === S.ATTACK && !!current && current.type === "melee" &&
      (!current.no_parry || o.isContinuousComboActive()) &&
      o.atkPhase === 0 && dist < (current.reach || 1.7) + 0.6;
    const shot = this.threats.projectiles().find(pr => pr.target === f && pr.team !== f.team &&
      pr.pos.distanceTo(f.chest()) < 7.5);
    const shotETA = shot ? this.projectileTimeToContact(f, shot) : 99;
    const actionableShot = !!shot && shotETA > 0.14 && shotETA < 0.62;
    if (!meleeIncoming && !actionableShot) return false;
    const serial = meleeIncoming ? o.id * 100000 + o.swingSerial : shot!.id * -1;
    if (serial !== this.nesaVThreat) {
      this.nesaVThreat = serial;
      this.nesaVUsed = false;
      this.nesaVChose = Math.random() < [0.13,0.40,0.72,0.90][this.iqLevel];
      this.nesaVReactAt = now + [0.26,0.19,0.11,0.065][this.iqLevel] + Math.random()*0.05;
    }
    if (!this.nesaVChose || this.nesaVUsed || now < this.nesaVReactAt) return false;
    const eta = meleeIncoming ? Math.max(0, current!.wind - o.stateT) : shotETA;
    if (eta < 0.13 || eta > 0.70) return false; // swing's actual 0.10..0.79 parry window
    this.nesaVUsed = true;
    this.queue=[]; this.hold=0; this.blockWait=-1; this.blockHold=0;
    f.intent.block=false; f.intent.attack=false; f.intent.skill="v";
    return true;
  }

  private zenithSkillNextAt = 0;
  private zenithSpearObservedAt = -1;
  private zenithSpearWasOut = false;
  private zenithEnemyId = -1;
  private zenithSkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {
    if (f.look.element !== "metal" || f.kit !== "glaive" || f.isDown() || o.isDown()) return false;
    const now = this.threats.now();
    if (this.zenithEnemyId !== o.id || now < this.zenithSkillNextAt - 120) {
      this.zenithEnemyId = o.id; this.zenithSpearWasOut = false;
      this.zenithSpearObservedAt = -1; this.zenithSkillNextAt = now + 0.20;
    }
    if (f.zenithSpearOut && !this.zenithSpearWasOut) this.zenithSpearObservedAt = now;
    this.zenithSpearWasOut = f.zenithSpearOut;
    if (f.chainBindT > 0 || !f.onGround || f.status.has("freeze") ||
        now < this.zenithSkillNextAt || f.intent.skill) return false;
    const free = f.state === S.IDLE || f.state === S.BLOCK || f.state === S.CHARGE ||
      (f.state === S.ATTACK && f.atkPhase === 2 && !!f.atk);
    if (!free) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const marked = this.threats.magneticMark?.(f, o) ?? 0;
    const ready = (key: "z"|"x"|"c"|"v") => !!f.attacks[key] &&
      (f.cooldowns[key] ?? 1) <= 0 && (key !== "v" || f.bonusSkillUnlocked);
    const pressure = o.state === S.HITSTUN || o.state === S.STAGGER || this.hasPunishWindow(o);
    const opportunity = [0.24, 0.54, 0.79, 0.94][this.iqLevel];
    let key: "z"|"x"|"c"|"v"|"" = "";
    if (f.zenithSpearOut) {
      const held = now - Math.max(0, this.zenithSpearObservedAt);
      const anchorDist = f.zenithSpearAnchor.clone().setY(0).distanceTo(f.root.position.clone().setY(0));
      // Don't instantly recall every Z! Attack from two positions or reposition by C first.
      if (ready("c") && anchorDist > 2.3 && gap > 2.1 && gap < 8 &&
          (marked === -1 || anchorDist > 4.2) && held > 0.36) key = "c";
      else if (held > (this.iqLevel >= 2 ? 1.0 : 1.5) &&
          (gap < 3.3 || held > 2.4 || anchorDist > 7.5)) key = "z";
    } else if (ready("v") && gap >= 2.3 && gap < 7.3 && pressure && this.iqLevel >= 2) {
      key = "v";
    } else if (ready("c") && marked === 1 && gap >= 2.3 && gap <= 5.2 &&
          (ready("x") || pressure || gap >= 3.5)) {
      // Positive -> attract into close-range rapid thrusts.
      key = "c";
    } else if (ready("x") && gap > 0.65 && gap < 2.8 &&
          (pressure || marked === 1 || this.iqLevel >= 2)) {
      key = "x";
    } else if (ready("z") && gap >= 3.5 && gap <= 9.2 &&
          (marked !== -1 || pressure)) {
      key = "z";
    } else if (ready("c") && marked === -1 && gap < 2.5 && !f.stage) {
      // Negative -> repel as a defensive reset (normal cooldown and collision still apply).
      f.intent.skillHeld = "c"; key = "c";
    } else if (ready("x") && gap < 2.5 && pressure) {
      key = "x";
    }
    if (!key) { this.zenithSkillNextAt=now+0.20; return false; }
    this.zenithSkillNextAt=now+[1.1,0.74,0.45,0.27][this.iqLevel];
    if (Math.random() > opportunity) return false;
    f.intent.skill=key;
    f.intent.attack=false;
    this.queue=[]; this.hold=0;
    return true;
  }

  private roxySkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {
    if (f.look.element !== "frost" || f.kit !== "mage" || f.isDown() || o.isDown()) return false;
    if (!f.attacks.z || f.attacks.z.mode !== "frost_aegis") return false;
    if (this.roxyTarget !== o.id) {
      this.roxyTarget = o.id;
      this.roxySkillReadAt = this.threats.now() + [1.25, 0.82, 0.48, 0.20][this.iqLevel];
    }
    const now = this.threats.now();
    if (now < this.roxySkillReadAt || !f.onGround || f.status.has("freeze")) return false;
    const castingFree = f.state === S.IDLE || f.state === S.BLOCK ||
      (f.state === S.ATTACK && f.atkPhase === 2 && !!f.atk &&
        f.stateT >= f.atk.wind + f.atk.active + 0.07);
    if (!castingFree || f.chainBoundBy || f.chainBindT > 0 ||
        this.blockHold > 0 || this.blockWait >= 0 ||
        this.comboParryTarget > now || this.projectileSwordCommit > 0) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const nearHit = o.state === S.ATTACK && o.atkPhase <= 1;
    const danger = nearHit && (o.atk?.type === "melee" ?
      gap < (o.atk.reach + 1.0) : gap < 8.5);
    const projectileDanger = this.threats.projectiles().some(p =>
      p.team !== f.team && (p.target === f || p.target?.id === f.id) &&
      p.pos.distanceToSquared(f.chest()) < 75);
    const punish = this.hasPunishWindow(o);
    const frozen = o.status.has("freeze");
    const freezeReady = !frozen && o.status.freezeImmunityRemaining() <= 0;
    const ready = (key: "z" | "x" | "c" | "v") =>
      !!f.attacks[key] && (f.cooldowns[key] ?? 1) <= 0 &&
      (key !== "v" || f.bonusSkillUnlocked);
    const choices: { key: "z" | "x" | "c" | "v"; score: number }[] = [];
    // Protect a real incoming hit, or pre-shield when injured and close enough.
    if (ready("z") && (f.frostShieldCharges <= 0 || f.frostShieldT <= 0) &&
        (danger || projectileDanger || (gap < 6.5 && f.hp < f.maxHp * 0.78)))
      choices.push({ key: "z", score: danger || projectileDanger ? 4.7 : 2.75 });
    // Snowpuff won't waste a freeze during the explicit post-thaw immunity.
    if (ready("x") && freezeReady && gap > 0.8 && gap < 7.8 &&
        (!nearHit || gap >= 2.7))
      choices.push({ key: "x", score: punish ? 3.25 : 2.25 });
    // A frozen, immobile enemy is an ideal meteor target. It is still a legal
    // delayed strike; the enemy may dodge if thawed before impact.
    if (ready("c") && gap < 10.2 && (!danger || gap > 3.1))
      choices.push({ key: "c", score: frozen ? 4.15 : punish ? 3.5 :
        o.state === S.BLOCK ? 2.25 : gap < 7.0 ? 1.65 : 0.75 });
    // Frostwing has a 52-second cooldown: save it for a usable ranged setup.
    if (ready("v") && gap > 2.65 && gap < 9.3 && !danger)
      choices.push({ key: "v", score: frozen || punish ? 3.0 :
        gap > 4.0 && gap < 7.7 ? 2.55 : 1.10 });
    if (!choices.length) {
      this.roxySkillReadAt = now + [0.95, 0.53, 0.30, 0.17][this.iqLevel];
      return false;
    }
    // Difficulty determines recognition and planning interval, NOT legality.
    const notice = [0.28, 0.58, 0.83, 0.97][this.iqLevel];
    this.roxySkillReadAt = now + [1.75, 1.05, 0.64, 0.35][this.iqLevel] *
      (0.85 + Math.random() * 0.30);
    if (Math.random() > notice) return false;
    choices.sort((a, b) => b.score - a.score);
    const choice = this.iqLevel === 0 && choices.length > 1 && Math.random() < 0.36
      ? choices[1] : choices[0];
    if (choice.score < 1.35) return false;
    // Threats, telegraphs and true parry-counter windows already ran first.
    this.queue = []; this.hold = 0;
    this.theaterT = 0; this.theaterMode = "none";
    this.theaterFollow = ""; this.theaterFollowT = 0;
    this.tacticsT = 0;
    f.intent.attack = false;
    f.intent.block = false;
    f.intent.skill = choice.key;
    this.skillCd = Math.max(this.skillCd, 0.5);
    this.readySkillPoll = 0.28;
    return true;
  }

  private readySkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {
    this.readySkillPoll = Math.max(0, this.readySkillPoll - dt);
    if (f.look.element === "metal" && f.kit === "glaive") return false;
    if (this.readySkillPoll > 0 || f.isDown()) return false;
    // Veyr cannot cast skills during Blood Festival. His light combo takes over.
    if (f.kit === "sickle" && f.bloodFestivalT > 0) return false;
    const free = f.state === S.IDLE || f.state === S.BLOCK ||
      (f.state === S.ATTACK && f.atkPhase === 2 && !!f.atk &&
        f.stateT >= f.atk.wind + f.atk.active + 0.07);
    if (!free || !f.onGround) return false;
    // Planned defensive reads still take priority over opportunistic attacks.
    if (this.blockHold > 0 || this.blockWait >= 0 ||
        this.comboParryTarget > this.threats.now()) return false;
    const distance = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    const ready = ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])].filter(k =>
      !!f.attacks[k] && (f.cooldowns[k] ?? 1) <= 0 &&
      !(f.attacks[k].style === "nesa_heart_slam" &&
        f.nesaCCharges <= 0));
    if (!ready.length) return false;

    // The existing 17 personalized profiles handle range and tactical conditions.
    // Never spend a counter on an idle target, a smash outside range, etc.
    const key = this.personalizedSkill(f, o, distance);
    if (!key || !ready.includes(key)) return false;
    const a = f.attacks[key];
    const imminent = o.state === S.ATTACK && o.atkPhase === 1 &&
      !!o.atk && o.atk.type === "melee" &&
      distance < o.atk.reach + 0.25;
    // Don't blindly wind up a ranged spell into an active nearby hitbox.
    if (imminent && (a.type === "projectile" || a.type === "lob" ||
        (a.type === "strike" && a.wind > 0.3))) return false;

    // Favor usable skills over queued light taps, but the Fighter still enforces
    // animation recovery, state checks, cooldowns, and actual collision.
    this.queue = [];
    this.hold = 0;
    this.theaterT = 0;
    this.theaterMode = "none";
    this.theaterFollow = "";
    this.theaterFollowT = 0;
    this.tacticsT = 0;
    f.intent.attack = false;
    f.intent.block = false;
    f.intent.skill = key;
    this.readySkillPoll = 0.18;
    this.skillCd = Math.max(this.skillCd, 0.25);
    return true;
  }


  /** Read actual parry rewards, not an AI-only counter move or free hit. */
  private spinCounterResponse(f: Fighter, o: Fighter, dt: number): boolean {
    if (!f.hasParryCounterReady()) {
      this.counterSeen = false;
      this.counterWant = false;
      this.counterReactT = 0;
      return false;
    }
    if (!this.counterSeen) {
      this.counterSeen = true;
      // Personality and difficulty affect whether a CPU confidently commits.
      const fighter = f.look.name.toLowerCase();
      const bold = ["kira", "nyx", "vesper", "rook", "zarek", "veyr", "kaizen", "nesa"].includes(fighter);
      const caution = f.guard < f.maxGuard * 0.20;
      const chance = this.p.parry <= 0 ? 0.35 : this.p.parry < 0.10 ? 0.64 :
        this.p.parry < 0.20 ? 0.83 : 0.97;
      this.counterWant = Math.random() < Math.min(0.98, chance + (bold ? 0.08 : 0) - (caution ? 0.10 : 0));
      this.counterReactT = rand(this.p.react[0], this.p.react[1]) * (bold ? 0.42 : 0.58);
    }
    this.counterReactT = Math.max(0, this.counterReactT - dt);
    if (!this.counterWant || this.counterReactT > 0 || !f.onGround ||
        (f.state !== S.BLOCK && f.state !== S.IDLE)) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    if (gap > f.parryCounterReach() + 0.55) {
      // The defender can chase but cannot spawn a hit outside its actual reach.
      if (gap < f.parryCounterReach() + 2.4 && f.state === S.IDLE) {
        const dir = o.root.position.clone().sub(f.root.position).setY(0).normalize();
        if (f.stage) dir.set(Math.sign(dir.x), 0, 0);
        f.intent.move.copy(dir);
      }
      return false;
    }
    if (o.invulnT > 0 || o.knockedDown()) return false;
    // Shared exact action as player LMB: respect real state, recoil and cast rules.
    if (!f.tryParryCounter()) return false;
    this.queue = []; this.hold = 0;
    this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
    this.comboParryTarget = -1;
    this.theaterFollow = "";
    this.theaterT = 0;
    f.intent.block = false;
    f.intent.attack = false; // no stuck attack held for the next animation
    f.intent.skill = "";
    f.intent.move.set(0, 0, 0);
    this.counterWant = false;
    return true;
  }

  /** Recognize an enemy spin counter's 0.4s wind-up and take real defensive action. */
  private counterThreatDefense(f: Fighter, o: Fighter, dt: number): boolean {
    const a = o.atk;
    if (o.state !== S.ATTACK || o.atkId !== "pc" || a?.style !== "parry_counter") {
      this.incomingCounterSeen = -1;
      return false;
    }
    if (o.swingSerial !== this.incomingCounterSeen) {
      this.incomingCounterSeen = o.swingSerial;
      this.incomingCounterReactT = rand(this.p.react[0], this.p.react[1]);
      this.incomingCounterEvade = Math.random() < (0.22 + this.p.block * 0.55);
    }
    this.incomingCounterReactT -= dt;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const eta = a.wind - o.stateT;
    if (eta <= 0 || this.incomingCounterReactT > 0 ||
        gap > a.reach + 0.60 || f.isDown() || !f.onGround ||
        ![S.IDLE, S.BLOCK].includes(f.state)) return false;
    const away = f.root.position.clone().sub(o.root.position).setY(0);
    if (away.lengthSq() < 0.0001) away.set(f.id % 2 ? 1 : -1, 0, 0);
    away.normalize();
    if (f.stage) away.set(Math.sign(away.x) || 1, 0, 0);
    if (this.incomingCounterEvade && f.dashCd <= 0 && eta > 0.10) {
      const at = f.root.position.clone().setY(0);
      let dir = away;
      if (!f.stage) {
        const flank = new THREE.Vector3(-away.z, 0, away.x);
        const cap = Math.max(1.0, f.arenaRadius - f.radius - 0.24);
        const tryFlank = at.clone().addScaledVector(flank, 2.8).length() < cap ? flank : flank.negate();
        if (at.clone().addScaledVector(tryFlank, 2.8).length() < cap) dir = tryFlank;
      }
      f.intent.dash.copy(dir);
      f.intent.move.copy(dir);
      f.intent.block = false;
    } else {
      // Shield if there is time, never invoke an impossible instant parry.
      f.intent.block = true;
      f.intent.move.set(0, 0, 0);
    }
    this.blockWait = -1; this.blockHold = 0;
    this.queue = []; this.hold = 0;
    f.intent.skill = "";
    f.intent.attack = false;
    return true;
  }


  /** Last-resort dodge for genuinely unsafe continuous attacks. Never grants i-frames
   * directly: issues the ordinary dash input with normal cooldown and state checks.
   * Clashes and affordable blocks are preferred; attacking never gets cancelled unless
   * a real dodge can be executed. Skill pressure resumes on the next frame.
   */
  private dodgeUnsafeContinuous(f: Fighter, o: Fighter, dt: number): boolean {
    const atk = o.atk;
    if (o.state !== S.ATTACK || !atk || !o.isContinuousComboActive() ||
        (o.atkPhase === 2 && o.stateT >= atk.wind + atk.active)) {
      this.lastUndodgeableCombo = -1;
      this.continuousDodgeDone = false;
      return false;
    }
    // Only react to threatening distance and the next legitimate hit beat.
    const distance = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    const reach = atk.type === "strike" ? Math.max(atk.radius, 1.6) :
      Math.max(1.5, atk.reach + Math.min(Math.max(atk.lunge, 0) * 0.12, 0.65));
    if (distance > reach + 0.65) return false;
    if (this.lastUndodgeableCombo !== o.swingSerial) {
      this.lastUndodgeableCombo = o.swingSerial;
      this.continuousDodgeReaction = rand(this.p.react[0], this.p.react[1]);
      this.continuousDodgeDone = false;
    }
    this.continuousDodgeReaction = Math.max(0, this.continuousDodgeReaction - dt);
    if (this.continuousDodgeDone || this.continuousDodgeReaction > 0) return false;
    if (f.isDown() || !f.onGround || f.dashing() ||
        ![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(f.state)) return false;

    // Upcoming combo time is authoritative when the arena schedules repeat hits.
    const upcoming = this.threats.comboHits(o)
      .filter(t => t >= this.threats.now() - 0.025).sort((x, y) => x - y);
    const eta = upcoming.length ? upcoming[0] - this.threats.now() :
      Math.max(0, atk.wind - o.stateT);
    if (eta > 0.48) return false; // too early; avoid panic dodges

    const shieldReady = f.state === S.BLOCK && f.stateT >= f.shieldRaise;
    const shieldCanRaise = [S.IDLE, S.BLOCK].includes(f.state) &&
      eta >= (f.nextShieldFast ? 0.01 : 0.10) + 0.035;
    const guardNeed = Math.max(12, atk.guard * (atk.heavy ? 1.25 : 1.05));
    const canAffordBlock = f.guard > guardNeed && (shieldReady || shieldCanRaise);
    const myLight = f.attacks.l1;
    const canClash = myLight?.type === "melee" &&
      ((f.state === S.ATTACK && f.atk?.type === "melee" && f.atkPhase <= 1) ||
       (f.state === S.IDLE && myLight.wind + 0.05 <= eta &&
        distance <= myLight.reach + 0.20));
    // Skip if existing good defense is still viable. Only exceptional threats
    // should override the normal aggressive personality / ready-skill logic.
    if (canAffordBlock || canClash) return false;

    const canDash = f.dashCd <= 0 && !f.knockedDown() &&
      (f.kit !== "hammer" || f.state !== S.ATTACK);
    if (!canDash) return false; // no fake dodges or permanent defensive lockdown
    // Choose a reachable safe direction inside the real arena boundaries.
    const away = f.root.position.clone().sub(o.root.position).setY(0);
    if (away.lengthSq() < 0.0001) away.set(f.id % 2 ? 1 : -1, 0, 0);
    away.normalize();
    const candidates = f.stage ? [
      new THREE.Vector3(Math.sign(away.x) || f.facing, 0, 0),
      new THREE.Vector3(-(Math.sign(away.x) || f.facing), 0, 0),
    ] : [
      away.clone(),
      new THREE.Vector3(-away.z, 0, away.x),
      new THREE.Vector3(away.z, 0, -away.x),
    ];
    const origin = f.root.position.clone().setY(0);
    let best: THREE.Vector3 | null = null;
    let score = -Infinity;
    for (const dir of candidates) {
      const dest = origin.clone().addScaledVector(dir, 2.5);
      if (f.stage) {
        const main = f.stage.plats[0];
        if (!main || dest.x < main.x0 + 0.7 || dest.x > main.x1 - 0.7) continue;
      } else if (dest.length() > f.arenaRadius - f.radius - 0.22) continue;
      const separation = dest.distanceTo(o.root.position.clone().setY(0));
      const value = separation + (dir.dot(away) > 0.6 ? 0.15 : 0);
      if (value > score) { score = value; best = dir; }
    }
    if (!best) return false;
    f.intent.dash.copy(best);
    f.intent.move.copy(best);
    f.intent.block = false;
    f.intent.attack = false;
    f.intent.skill = "";
    // Commit only to one true dash per enemy swing. No repeated queue cancellation.
    this.continuousDodgeDone = true;
    this.blockHold = 0;
    this.blockWait = -1;
    return true;
  }


  /** Zarek sometimes missed all blocks because pressure/skill logic overrode a
   * queued shield raise. Commit to the normal block input for one LEGITIMATE threat.
   * No free parry, unlimited shield or attack/skill lock; he remains aggressive.
   */
  private zarekShieldResponse(f: Fighter, o: Fighter, dt: number): boolean {
    if (f.kit !== "glaive") return false;
    this.zarekGuardPredictCd = Math.max(0, this.zarekGuardPredictCd - dt);
    if (f.isDown() || !f.onGround ||
        (f.state !== S.IDLE && f.state !== S.BLOCK)) {
      this.zarekGuardHold = 0;
      return false;
    }
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));

    const commitGuard = (duration: number): boolean => {
      this.zarekGuardHold = Math.max(this.zarekGuardHold, duration);
      f.intent.block = true;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.sprint = false;
      f.intent.move.set(0, 0, 0);
      // Ordinary shield raise is still 0.10s (or the earned 90% faster raise).
      // Do not let pressure/counter queues issue a basic during this guard.
      this.blockWait = -1;
      this.blockHold = 0;
      this.blockDur = 0;
      this.comboParryTarget = -1;
      this.queue = [];
      this.hold = 0;
      return true;
    };

    if (this.zarekGuardHold > 0) {
      this.zarekGuardHold = Math.max(0, this.zarekGuardHold - dt);
      if (f.guard > Math.max(5, f.maxGuard * 0.09)) {
        return commitGuard(0);
      }
      this.zarekGuardHold = 0;
    }
    if (f.guard <= Math.max(f.maxGuard * 0.28, 18)) return false;
    // Projectiles deserve real shielding too: Zarek's old pressure plan often
    // started a glaive combo instead of raising guard for the incoming shot.
    // This reads existing real projectiles; it does not predict nonexistent ones.
    for (const shot of this.threats.projectiles()) {
      if (shot.target !== f || this.zarekGuardSeenShots.has(shot.id)) continue;
      const approaching = shot.pos.clone().sub(f.chest()).dot(shot.vel) < 0;
      const eta = f.chest().distanceTo(shot.pos) /
        Math.max(1.0, shot.vel.length());
      if (!approaching || eta < (f.nextShieldFast ? 0.05 : 0.14) ||
          eta > 0.64 || f.guard <= f.maxGuard * 0.37) continue;
      this.zarekGuardSeenShots.add(shot.id);
      if (this.zarekGuardSeenShots.size > 150) this.zarekGuardSeenShots.clear();
      if (Math.random() < 0.22 + this.p.block * 0.82)
        return commitGuard(Math.min(0.80, eta + 0.19));
    }
    const a = o.atk;
    const nearby = gap < 2.75;

    // Anticipatory guard against a plainly visible long charge, or a short
    // read during close-range neutral. This covers fast 0.1s combos that cannot
    // be reacted to AFTER the blade starts moving.
    if (this.zarekGuardPredictCd <= 0 && nearby &&
        (o.state === S.CHARGE || o.state === S.IDLE) &&
        f.guard > f.maxGuard * 0.61 &&
        Math.random() < dt * (o.state === S.CHARGE ? 3.2 : 0.68) *
          (0.65 + this.p.block)) {
      this.zarekGuardPredictCd = o.state === S.CHARGE ? 1.35 : 2.2;
      return commitGuard(o.state === S.CHARGE ? 0.42 : 0.24);
    }
    if (o.state !== S.ATTACK || !a || a.dmg <= 0 ||
        (a.type !== "melee" && a.type !== "strike")) return false;
    const range = a.type === "strike" ? Math.max(a.radius, 1.65) :
      a.reach + Math.min(Math.max(0, a.lunge) * 0.13, 0.80);
    if (gap > range + 0.48) return false;
    if (o.swingSerial !== this.zarekGuardSwing) {
      this.zarekGuardSwing = o.swingSerial;
      this.zarekGuardReact = rand(this.p.react[0], this.p.react[1]) * 0.64;
      const usefulGuard = f.guard >= Math.max(f.maxGuard * 0.32,
        a.guard * (o.isContinuousComboActive() ? 2.0 : 1.25));
      this.zarekGuardWants = usefulGuard &&
        Math.random() < Math.min(0.91, 0.46 + this.p.block * 0.64);
    }
    if (!this.zarekGuardWants) return false;
    this.zarekGuardReact = Math.max(0, this.zarekGuardReact - dt);
    if (this.zarekGuardReact > 0) return false;

    // Contact may come from a multi-hit beat; block those instead of assuming
    // another parry can be raised instantly. Shield/guard damage stays real.
    const eta = a.type === "strike" ? Math.max(0, a.wind - o.stateT + a.delay) :
      Math.max(0, a.wind - o.stateT);
    const remain = a.wind + a.active - o.stateT;
    if (remain < -0.15 && !o.isContinuousComboActive()) return false;
    const shieldReady = f.state === S.BLOCK && f.stateT >= f.shieldRaise;
    const raise = f.nextShieldFast ? 0.01 : 0.10;
    if (!shieldReady && eta + (o.isContinuousComboActive() ? 0.22 : 0.035) < raise) return false;

    this.zarekGuardWants = false;
    const holdTime = o.isContinuousComboActive()
      ? Math.min(1.25, Math.max(0.28, remain + 0.20))
      : Math.min(0.65, Math.max(0.24, remain + 0.20));
    return commitGuard(holdTime);
  }

  /** Last-resort heavy evasion. Keep offense when shielding or clashing works.
   * Only legal movement inputs are used; no free dash, teleport or invulnerability.
   */
  private evadeUnsafeHeavy(f: Fighter, o: Fighter, dt: number): boolean {
    const a = o.atk;
    const dangerous = o.state === S.ATTACK && !!a &&
      !(o.atkPhase === 2 && o.stateT >= a.wind + a.active) &&
      (a.heavy || (o.isContinuousComboActive() && a.dmg >= 50));
    // Target-locked area strikes are defended using their real marked impact
    // position instead. Running away from the caster is often the wrong direction.
    if (a?.type === "strike") return false;
    if (!dangerous || !a) {
      this.heavyEscapeSerial = -1;
      this.heavyEscapeUsed = false;
      return false;
    }
    if (f.isDown() || !f.onGround ||
        ![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(f.state)) return false;

    const distance = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    const dangerRange = a.type === "strike" ? Math.max(1.6, a.radius) + 0.55 :
      Math.max(1.4, a.reach + Math.min(Math.max(0, a.lunge) * 0.12, 0.8)) + 0.55;
    if (distance > dangerRange) return false;

    if (this.heavyEscapeSerial !== o.swingSerial) {
      this.heavyEscapeSerial = o.swingSerial;
      this.heavyEscapeUsed = false;
      this.heavyEscapeReactT = Math.max(this.p.react[0],
        this.p.react[0] + Math.random() * (this.p.react[1] - this.p.react[0]));
    }
    if (this.heavyEscapeUsed) return false;
    this.heavyEscapeReactT = Math.max(0, this.heavyEscapeReactT - dt);
    if (this.heavyEscapeReactT > 0) return false;

    // For a repeated sequence, use the next scheduled hit time when available.
    const hits = o.isContinuousComboActive()
      ? this.threats.comboHits(o).filter(t => t >= this.threats.now() - 0.03)
        .sort((x, y) => x - y) : [];
    const eta = hits.length ? hits[0] - this.threats.now() :
      Math.max(0, a.wind - o.stateT);
    if (eta > 0.38) return false;

    const shieldUp = f.state === S.BLOCK && f.stateT >= f.shieldRaise;
    const canRaise = (f.state === S.IDLE || f.state === S.BLOCK) &&
      eta >= (f.nextShieldFast ? 0.01 : 0.10) + 0.045;
    const shieldCost = Math.max(a.guard * (a.heavy ? 1.28 : 1.10), 18);
    const wouldCrushShield = o.kit === "hammer" && a.heavy;
    const canBlock = (shieldUp || canRaise) && f.guard > shieldCost && !wouldCrushShield;
    const myLight = f.attacks.l1;
    const canClash = !!myLight && myLight.type === "melee" &&
      ((f.state === S.ATTACK && f.atk?.type === "melee" && f.atkPhase === 1) ||
       (f.state === S.IDLE && distance <= myLight.reach + 0.18 &&
        myLight.wind + 0.055 < eta));
    if (canBlock || canClash) return false;

    const away = f.root.position.clone().sub(o.root.position).setY(0);
    if (away.lengthSq() < 0.001) away.set(f.id % 2 ? 1 : -1, 0, 0);
    away.normalize();
    const back = f.stage ? new THREE.Vector3(Math.sign(away.x) || -f.facing, 0, 0) : away;
    // Check actual stage edges / arena radius before issuing movement.
    const destination = f.root.position.clone().setY(0).addScaledVector(back, 2.4);
    if (f.stage) {
      const main = f.stage.plats[0];
      if (!main || destination.x < main.x0 + 0.65 || destination.x > main.x1 - 0.65)
        return false;
    } else if (destination.length() > f.arenaRadius - f.radius - 0.12) return false;

    const canDash = f.dashCd <= 0 && !f.dashing() &&
      (f.kit !== "hammer" || f.state !== S.ATTACK);
    if (canDash) {
      f.intent.dash.copy(back);
      f.intent.move.copy(back);
    } else if (f.state === S.IDLE || f.state === S.BLOCK) {
      // Dash on cooldown: ordinary backward jump + air movement, not instant invulnerability.
      f.intent.jump = true;
      f.intent.move.copy(back);
    } else return false;
    f.intent.block = false;
    f.intent.attack = false;
    f.intent.skill = "";
    this.heavyEscapeUsed = true;
    // Do not erase attack queues, ready skill timers, or character-specific footwork.
    return true;
  }

  // V7: Kaizen's shield causes REAL 16 HP contact damage every 0.45 s in its
  // physical radius. Move outside that radius, then return when he drops guard.
  private kaizenGuardReact = -1;
  private kaizenGuardDashUsed = false;
  private avoidKaizenSpinGuard(f: Fighter, o: Fighter, dt: number): boolean {
    const dangerous = o.kit === "chainblade" && o.state === S.BLOCK &&
      o.guard > 0 && !o.isDown() && !o.chainBindT;
    if (!dangerous) {
      this.kaizenGuardReact = -1;
      this.kaizenGuardDashUsed = false;
      return false;
    }
    if (f.isDown() || !f.onGround ||
        (f.state !== S.IDLE && f.state !== S.BLOCK)) return false;
    const away = f.root.position.clone().sub(o.root.position).setY(0);
    const gap = away.length();
    if (gap > 1.85 || gap < 0.01) {
      if (gap > 1.85) this.kaizenGuardDashUsed = false;
      return false;
    }
    if (this.kaizenGuardReact < 0)
      this.kaizenGuardReact = this.p.react[0] + Math.random() * (this.p.react[1] - this.p.react[0]);
    this.kaizenGuardReact = Math.max(0, this.kaizenGuardReact - dt);
    if (this.kaizenGuardReact > 0) return false;
    away.normalize();
    // Do not run into arena walls while trying to escape.
    if (f.stage) {
      const main = f.stage.plats[0];
      if (!main || f.root.position.x + away.x * 1.0 < main.x0 + 0.65 ||
          f.root.position.x + away.x * 1.0 > main.x1 - 0.65) return false;
      away.set(Math.sign(away.x) || -f.facing, 0, 0);
    } else if (f.root.position.clone().setY(0).addScaledVector(away, 1.0).length() >= f.arenaRadius - 0.2) {
      const side = new THREE.Vector3(-away.z, 0, away.x);
      if (f.root.position.clone().setY(0).addScaledVector(side, 1).length() >= f.arenaRadius - 0.2)
        side.negate();
      if (f.root.position.clone().setY(0).addScaledVector(side, 1).length() >= f.arenaRadius - 0.2)
        return false;
      away.copy(side);
    }
    f.intent.move.copy(away);
    f.intent.block = false;
    f.intent.sprint = false;
    // One real dash per guard encounter, and only when dangerously close.
    if (!this.kaizenGuardDashUsed && gap < 1.42 && f.dashCd <= 0 && !f.dashing()) {
      f.intent.dash.copy(away);
      this.kaizenGuardDashUsed = true;
    }
    // Cancel a stale shield-hold decision only while in the damaging contact area.
    this.blockWait = -1;
    this.blockHold = 0;
    return true;
  }

  constructor(private threats: Threats, level: number) {
    this.iqLevel = Math.max(0, Math.min(Math.floor(Number.isFinite(level) ? level : 1), PRESETS.length - 1));
    this.p = PRESETS[this.iqLevel];
  }

  /** The leap itself is a visible warning: the scheduled ground strike marker
   * only appears on touchdown, too late to finish raising a shield. Hold
   * the NORMAL block button before touchdown, never grant fake invulnerability.
   */
  private defendRookMeteor(f: Fighter, o: Fighter): boolean {
    const a = o.atk;
    if (o.kit !== "knuckles" || o.state !== S.ATTACK ||
        a?.name !== "Meteor Fist" || o.atkPhase === 2) return false;
    if (f.isDown() || !f.onGround || f.stage || o.stage ||
        f.chainBoundBy || f.chainBindTarget) return false;
    const now = this.threats.now();
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    // The attack leap homes toward its real opponent, so it can close a gap.
    if (gap > 7.0 || o.opponent !== f) return false;
    if (o.swingSerial !== this.rookMeteorSerial) {
      this.rookMeteorSerial = o.swingSerial;
      const chance = [0.22, 0.52, 0.82, 0.995][this.iqLevel];
      this.rookMeteorWants = Math.random() < chance;
      const min = [0.32, 0.21, 0.12, 0.035][this.iqLevel];
      const max = [0.48, 0.33, 0.20, 0.065][this.iqLevel];
      this.rookMeteorReactAt = now + rand(min, max);
    }
    if (!this.rookMeteorWants || now < this.rookMeteorReactAt) return false;
    const guardCost = a.guard * (f.judgmentT > 0 ? 1.5 : 1);
    if (f.guard > guardCost + 8 &&
        (f.state === S.IDLE || f.state === S.BLOCK)) {
      // Early regular guard works when the landing marker is too late.
      this.queue = []; this.hold = 0;
      this.blockWait = -1; this.blockHold = 0;
      f.intent.block = true;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.jump = false;
      f.intent.move.set(0, 0, 0);
      f.intent.dash.set(0, 0, 0);
      return true;
    }
    // A depleted shield must not be treated as protection. Normal dash still
    // obeys its cooldown and invulnerability timing; no guaranteed escape.
    if (f.state === S.IDLE && f.dashCd <= 0 && !f.dashing() &&
        (o.atkPhase === 1 || o.stateT > a.wind * 0.5)) {
      const away = f.root.position.clone().sub(o.root.position).setY(0);
      if (away.lengthSq() < 0.01) away.set(f.id % 2 ? 1 : -1, 0, 0);
      away.normalize();
      const destination = f.root.position.clone().setY(0).addScaledVector(away, 3.4);
      if (destination.length() >= f.arenaRadius - 0.4)
        away.set(-away.z, 0, away.x);
      f.intent.dash.copy(away);
      f.intent.move.copy(away);
      f.intent.block = false;
      f.intent.attack = false;
      f.intent.skill = "";
      return true;
    }
    return false;
  }

  /** Kaizen's V Serpent Bind has TWO existing legal follow-ups:
   * Z = Serpent Lift (forward), X = Serpent Overthrow (backward).
   * Consider arena boundaries, then alternate where both throws are safe.
   */
  private chooseSerpentVFollowup(f: Fighter): "z" | "x" {
    const heading = f.stage
      ? new THREE.Vector3(f.facing, 0, 0)
      : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const roomAt = (distance: number): number => {
      const p = f.root.position.clone().addScaledVector(heading, distance);
      if (f.stage) return Math.min(p.x - (f.stage.blast.l + 1), f.stage.blast.r - 1 - p.x);
      return f.arenaRadius - Math.hypot(p.x, p.z);
    };
    // The full animated victim trajectories end about +1.10m and -1.35m.
    const frontRoom = Math.min(roomAt(1.10), roomAt(0.80));
    const backRoom = Math.min(roomAt(-1.35), roomAt(-0.90));
    let forward: boolean;
    if (frontRoom < 0.65 && backRoom > frontRoom + 0.30) forward = false;
    else if (backRoom < 0.65 && frontRoom > backRoom + 0.30) forward = true;
    else if (Math.abs(frontRoom - backRoom) > 0.75) forward = frontRoom > backRoom;
    else forward = this.chainVAlternate;
    this.chainVAlternate = !this.chainVAlternate;
    return forward ? "z" : "x";
  }

  /** Handle an active bind before ordinary defense returns can skip the recast.
   * Uses only normal input, respects the real chain-choice arming and delay.
   */
  private handleKaizenBindFollowup(f: Fighter, dt: number): boolean {
    if (!f.chainBindTarget || f.chainBindT <= 0) {
      this.chainDecisionT = 0;
      this.chainVFollowup = "";
      return false;
    }
    this.chainDecisionT += dt;
    f.intent.attack = false;
    f.intent.block = false;
    const target = f.chainBindTarget;
    if (f.chainBindKind === "x" && f.chainBindFinishT <= 0) {
      const move = target.root.position.clone().sub(f.root.position).setY(0);
      if (move.length() > 2.3) {
        move.normalize();
        f.intent.move.copy(f.stage ? new THREE.Vector3(Math.sign(move.x), 0, 0) : move);
      }
    } else if (f.chainBindKind === "v" && !this.chainVFollowup) {
      this.chainVFollowup = this.chooseSerpentVFollowup(f);
    }
    if (f.chainBindFinishT <= 0 && f.chainChoiceArmed && this.chainDecisionT >= 0.48) {
      f.intent.skill = f.chainBindKind === "x" ? "x" : this.chainVFollowup;
    }
    return true;
  }

  think(f: Fighter, dt: number) {
    // KAIZEN_SPIN_HIT_RELIABILITY_V9: unlike LocalBrain, AiBrain does not
    // receive a held Z key. Keep it virtually held for the full active spin.
    // This does not bypass cooldowns, change the skill duration, or affect players.
    if (f.kit === "chainblade" && f.state === S.ATTACK &&
        f.atk?.style === "chain_razor_cyclone") f.intent.skillHeld = "z";
    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    this.observeAerialOpponent(f, o);
    this.observeEnemyCooldown(o);
    if (this.defendRookMeteor(f, o)) return;
    this.observeCounterfire(f, o);
    // An active grab locks both fighters. Commit to Z/X before other tactics.
    if (this.handleKaizenBindFollowup(f, dt)) return;
    this.iqObserve(f, o);
    this.observePatterns(f, o, dt);
    this.personalityRead(f, o); // sample tactics; does not send an input
    // Marked ground impacts outrank defensive guard plans and ordinary offense.
    if (this.evadeGroundStrikes(f)) return;
    if (this.evadeStaticField(f)) return;
    if (this.avoidKaizenSpinGuard(f, o, dt)) return;
    if (this.dodgeUnsafeContinuous(f, o, dt)) return;
    if (this.evadeUnsafeHeavy(f, o, dt)) return;

    if (this.spinCounterResponse(f, o, dt)) return;
    if (this.counterThreatDefense(f, o, dt)) return;
    if (this.zarekShieldResponse(f, o, dt)) return;
    if (f.chainBoundBy && f.chainBoundBy.chainBindT > 0) return;
    // A real approaching attack gives Nesa time to wind up her timed V counter.
    if (this.nesaTimedVParry(f, o)) return;
    // During Blood Festival Veyr chases with basics rather than blocking.
    if (this.veyrFestivalPressure(f, o, dt)) return;
    if (f.stage) { if (this.platform(f, o, dt)) return; }
    this.react(f, o);
    this.defendLongCombo(f, o);
    if (this.projectileCounterfire(f, o)) return;
    if (!f.stage) {
      this.projectileSwordCommit = Math.max(0, this.projectileSwordCommit - dt);
      this.dodge(f);
      this.position(f, o, dt);
      if (this.projectileSwordCommit <= 0) {
        this.tacticalFootwork(f, o, dt);
        this.theaterFootwork(f, o, dt);
      }
    }
    // NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: Kira can reposition between air kicks.
    // Use the same directional input and capped movement available to the player.
    // NYX_SHADOW_COMBAT_AIR_2_V1: airborne dagger pursuit uses normal steering.
    if (!f.stage && (f.kit === "kicks" || f.kit === "assassin") &&
        !f.onGround && f.state === S.ATTACK &&
        (f.kit === "kicks" ? /^air_l[1-3]$/.test(f.atkId) : /^air_l[1-2]$/.test(f.atkId))) {
      const toward = o.root.position.clone().sub(f.root.position).setY(0);
      const distance = toward.length();
      if (distance > 1.1) f.intent.move.copy(toward.divideScalar(distance));
      else if (distance > 0.01) {
        const around = new THREE.Vector3(-toward.z, 0, toward.x).normalize();
        f.intent.move.copy(around).multiplyScalar(0.55);
      }
    }
    // Chase carefully during spinning Z/C without overriding dodge or fire safety.
    this.kaizenSpinAdvance(f, o);
    this.aerialFootwork(f, o);
    // Run after normal chase/strafe choices, so fire can veto a dangerous route.
    this.avoidFireGround(f);
    // NESA_DODGE_KIRA_AIR_3_V1: opponent dodges Nesa's real wind-up; leave
    // Nesa's own AI and every fighter's damage, guard and parry rules untouched.
    if (!f.stage && this.evadeNesa(f, o, dt)) return;
    this.antiAirCd = Math.max(0, this.antiAirCd - dt);
    this.airSliceCd = Math.max(0, this.airSliceCd - dt);
    this.aiAirTap = false;
    if (f.kit === "wind" && !f.stage && this.airDive(f, o, dt)) return;
    // A cautious jump-in occasionally replaces the old automatic uppercut launcher.
    // Airborne CPUs swing toward an opponent's current elevation, just like players.
    const flatGap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    if (!f.stage && f.onGround && f.state === S.IDLE && !RANGED.has(f.kit) &&
        this.antiAirCd <= 0 && flatGap > 0.65 && flatGap < 2.3 &&
        (this.shouldAerialJump(f, o, flatGap) ||
          (o.onGround && Math.random() < dt * 0.12))) {
      f.intent.jump = true;
      this.antiAirCd = rand(2.2, 3.8);
    }
    if (!f.stage && !f.onGround &&
        (f.state === S.IDLE || (f.state === S.ATTACK &&
          (f.kit === "kicks" ? /^air_l[1-3]$/.test(f.atkId) :
            f.kit === "assassin" && f.atkId === "air_l1"))) &&
        !f.airSliceUsed &&
        flatGap < f.attacks.air_l1.reach + 0.20 &&
        Math.abs(o.chest().y - f.chest().y) < 2.1 && this.airSliceCd <= 0 &&
        this.aerialAirStrikeChance(o, dt)) {
      this.aiAirTap = true;
      this.airSliceCd = f.kit === "kicks" || f.kit === "assassin" ? rand(0.17, 0.24) : rand(0.55, 0.85);
      this.queue = [];
      this.hold = 0;
    }
    // KAIZEN_AIR_X: use legitimate X key while airborne if the real hook can reach.
    const airHook = f.kit === "chainblade" && !f.stage && !f.onGround &&
      f.state === S.IDLE && f.attacks.x_air?.style === "chain_predator_hook" &&
      (f.cooldowns.x ?? 1) <= 0 && !f.chainBindT && o.state !== S.BLOCK &&
      flatGap > 1.3 && flatGap <= f.attacks.x_air.reach - 0.4 &&
      Math.abs(o.root.position.y - f.root.position.y) <= 2.7;
    if (!this.aiAirTap && airHook && this.skillCd <= 0) {
      f.intent.skill = "x";
      this.skillCd = rand(this.p.skill[0], this.p.skill[1]);
    }
    // Combat IQ runs after emergency dodges and ordinary footwork, before
    // opportunistic skills, scripted personality follow-ups and random offense.
    const landedActed = !this.aiAirTap && !f.intent.skill &&
      this.aerialLandingPunish(f, o);
    // Roxy's kit plan runs BEFORE normal combo/pattern reads starve her skills.
    const roxyActed = !landedActed && !this.aiAirTap && !f.intent.skill &&
      this.roxySkillOpportunity(f, o, dt);
    const zenithActed = !landedActed && !roxyActed && !this.aiAirTap && !f.intent.skill &&
      this.zenithSkillOpportunity(f, o, dt);
    const iqActed = !landedActed && !roxyActed && !zenithActed && !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.combatIQAction(f, o, dt);
    const patternActed = !landedActed && !roxyActed && !zenithActed && !iqActed && !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.patternFootwork(f, o);
    if (!landedActed && !roxyActed && !zenithActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&
        this.projectileSwordCommit <= 0 &&
        !this.readySkillOpportunity(f, o, dt) && !this.theaterOffense(f, o))
      this.offense(f, o, dt);
    // AI_ADVANCED_FOOTWORK: positioning refinement only after combat decisions.
    // Fire avoidance stays last so later pattern IQ never steers into fire.
    if (!f.stage) {
      this.advancedFootwork(f, o, dt);
      this.avoidFireGround(f);
    }
    // Sprint to close long gaps. A direction aimed at retreat/evade is not sprinted.
    // This uses the same run animations as player Shift movement.
    const chase = o.root.position.clone().sub(f.root.position).setY(0);
    const travel = f.intent.move.clone().setY(0);
    f.intent.sprint = f.state === S.IDLE && f.onGround && chase.lengthSq() > 25 &&
      travel.lengthSq() > 0.12 && travel.normalize().dot(chase.normalize()) > 0.75 &&
      !f.intent.block;
    // Bomber: set off the keg when the enemy walks near it.
    if (f.barrelOut && o.root.position.clone().setY(0).distanceTo(f.barrelPos) < 3) {
      const k = ["z", "x", "c"].find((key) => f.attacks[key].type === "barrel");
      if (k && Math.random() < dt * 6) f.intent.skill = k;
    }
    if (this.jumpWait >= 0) { this.jumpWait -= dt; if (this.jumpWait < 0) { this.jumpPulse = !this.jumpPulse; f.intent.jump = true; } }
    // A parry requires a *new* shield raise. Simply holding through the whole
    // combo results in blocks because the parry window expires after the first hit.
    if (this.retimeComboParry(f, o)) return;
    if (this.blockWait >= 0) { this.blockWait -= dt; if (this.blockWait < 0) this.blockHold = this.blockDur; }
    if (this.blockHold > 0) {
      this.blockHold -= dt;
      f.intent.block = true;
      this.queue = [];
      this.hold = 0;
      return;
    }
    if (this.aiAirTap) {
      f.intent.jump = false; // an air slash is just left-click, not Space+Click
      f.intent.attack = true;
      return;
    }
    if (this.hold > 0) {
      this.hold -= dt;
      f.intent.attack = this.hold > 0;
    } else if (this.queue.length) {
      this.queue[0][0] -= dt;
      if (this.queue[0][0] <= 0) { this.hold = this.queue[0][1]; this.queue.shift(); f.intent.attack = true; }
    }
  }

  /** NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: choose an escape that remains inside
   * the real arena. A blocked radial retreat loses to a viable tangential route.
   * Test projected destination, not just angle to the hammer wielder.
   */
  private nesaSafeEscape(f: Fighter, o: Fighter, radial: boolean, allowDash: boolean): { dir: THREE.Vector3; gain: number } {
    const at = f.root.position.clone().setY(0);
    const from = o.root.position.clone().setY(0);
    const away = at.clone().sub(from);
    const originalDist = away.length();
    if (originalDist > 0.001) away.divideScalar(originalDist);
    else away.set(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const side = new THREE.Vector3(-away.z, 0, away.x);
    const towardCenter = at.clone().negate().setY(0);
    if (towardCenter.lengthSq() > 0.001) towardCenter.normalize();
    const dirs = [
      away, side.clone(), side.clone().negate(),
      away.clone().addScaledVector(side, 0.95),
      away.clone().addScaledVector(side, -0.95),
      side.clone().addScaledVector(towardCenter, 0.85),
      side.clone().negate().addScaledVector(towardCenter, 0.85),
      towardCenter,
    ];
    const cap = Math.max(1.5, f.arenaRadius - f.radius - 0.20);
    const dashAvailable = allowDash && f.dashCd <= 0 && f.onGround;
    const lookAhead = dashAvailable ? 3.65 : Math.max(1.10, f.moveSpeed * 0.48);
    const facing = new THREE.Vector3(Math.sin(o.root.rotation.y), 0, Math.cos(o.root.rotation.y));
    const fire = this.threats.firePatches(f);
    let bestScore = -1e10;
    let best = away.clone();
    let gain = -1;
    for (const candidate of dirs) {
      if (candidate.lengthSq() < 0.0001) continue;
      const dir = candidate.normalize();
      const projected = at.clone().addScaledVector(dir, lookAhead);
      const radialDistance = projected.length();
      if (radialDistance > cap) projected.multiplyScalar(cap / radialDistance);
      const actualMove = projected.distanceTo(at);
      const resultingDistance = projected.distanceTo(from);
      const actualGain = resultingDistance - originalDist;
      const delta = projected.clone().sub(from);
      const lateral = Math.abs(delta.x * facing.z - delta.z * facing.x);
      // Radial AoE needs maximum distance; ordinary strikes can also escape their arc.
      let score = resultingDistance + (radial ? 0 : lateral * 0.20) + actualMove * 0.18;
      if (actualGain < 0) score += actualGain * 2.8;
      // Wall clipping makes a direction ineffective even if it points away.
      if (actualMove < lookAhead * 0.30) score -= 2.5;
      if (projected.length() > cap - 0.08) score -= 0.14;
      // Avoid accidentally escaping a hammer into Ember's persistent floor flames.
      for (const patch of fire) {
        if (Math.abs(patch.pos.y - f.root.position.y) > 1.55) continue;
        const dist = Math.hypot(projected.x - patch.pos.x, projected.z - patch.pos.z);
        if (dist < patch.radius + f.radius * 0.3 + 0.12)
          score -= 4 + (patch.radius - dist) * 2;
      }
      if (score > bestScore) { bestScore = score; best.copy(dir); gain = actualGain; }
    }
    return { dir: best, gain };
  }

  /** NESA_AI_EDGE_GIANT_KIRA_AIR_MOVE_V2: use visible wind-ups and real hit radii.
   * Heartbreaker's first bonk and giant follow-up are different threats, so a
   * dodge of the little hammer does NOT consume the dodge for the giant hammer.
   */
  private evadeNesa(f: Fighter, o: Fighter, dt: number): boolean {
    const a = o.atk;
    const active = o.kit === "hammer" && o.state === S.ATTACK && !!a && !f.isDown();
    if (!active) { this.nesaRetreatT = 0; return false; }
    // Do not override moves that the fighter cannot cancel into a real dash.
    const available = f.state === S.IDLE || f.state === S.BLOCK || f.state === S.CHARGE;
    if (!available) { this.nesaRetreatT = 0; return false; }
    // NESA_FORWARD_HEART_PARRY_V_20261108: parry sweep itself is not a damaging area.
    if (a!.style === "nesa_high_striker" && !o.nesaHighStrikerParried) {
      this.nesaRetreatT = 0;
      return false;
    }
    const giant = a!.style === "nesa_high_striker";
    const spin = a!.style === "nesa_spin" || a!.style === "nesa_air_spin";
    const heart = a!.style === "nesa_heart_slam";
    const area = giant || spin || heart || a!.type === "strike";
    // Avoid a C heart smash only if its forward-facing danger zone reaches us.
    const heartDir = new THREE.Vector3(Math.sin(o.root.rotation.y), 0, Math.cos(o.root.rotation.y));
    const fromNesa = f.root.position.clone().sub(o.root.position).setY(0);
    if (heart && fromNesa.dot(heartDir) <= 0.12) { this.nesaRetreatT = 0; return false; }
    const heartCenter = o.root.position.clone().addScaledVector(heartDir, 2.05).setY(0);
    const gap = f.root.position.clone().setY(0).distanceTo(heart ? heartCenter : o.root.position.clone().setY(0));
    // Actual source hitboxes: first high-striker bonk reaches 2.65, giant 3.6.
    // Normal hammer attacks may advance during the telegraphed wind-up.
    const firstRadius = giant ? 2.65 + f.radius * 0.45 + 0.22 :
      spin ? 2.80 + f.radius * 0.5 + 0.70 :
      area ? Math.max(2.4, a!.radius) + f.radius * 0.45 + 0.45 :
      a!.reach + f.radius * 0.5 + Math.min(1.25, a!.lunge * 0.33) + 0.32;
    const bigRadius = 3.60 + f.radius * 0.4 + 0.55;

    if (this.nesaThreatSerial !== o.swingSerial) {
      this.nesaThreatSerial = o.swingSerial;
      this.nesaEvadeUsed = false;
      this.nesaGiantEvadeUsed = false;
      // Keep difficulty scaling: easy is less consistent, master more alert.
      this.nesaEvadeChosen = Math.random() < Math.min(0.94, 0.13 + this.p.block * 1.18);
      // C is blockable (never parryable). Some bots guard instead of fleeing.
      this.nesaHeartBlockChosen = heart && f.guard > a!.guard * 1.35 &&
        Math.random() < [0.20, 0.37, 0.48, 0.62][this.iqLevel];
      this.nesaGiantEvadeChosen = Math.random() < Math.min(0.97, 0.38 + this.p.block * 0.88);
      const lead = 0.105 + this.p.react[1] * 0.28 + Math.random() * 0.025;
      this.nesaEvadeTrigger = Math.max(0.04, a!.wind - lead);
      this.nesaRetreatT = 0;
    }
    const t = o.stateT;
    // Raise guard before the visible hammer impact. Holding guard isn't a perfect parry:
    // nesa_heart_slam is explicitly no_parry, so regular guard drains guard only.
    if (heart && this.nesaHeartBlockChosen && gap < firstRadius + 0.35 &&
        t >= Math.max(0.05, a!.wind - 0.31) && t < a!.wind + 0.16) {
      this.nesaRetreatT = 0;
      this.blockWait=-1; this.blockHold=0; this.blockDur=0;
      this.queue=[]; this.hold=0;
      f.intent.attack=false; f.intent.skill=""; f.intent.dash.set(0,0,0);
      f.intent.move.set(0,0,0); f.intent.block=true;
      return true;
    }
    const giantImpact = a!.wind + 1.78; // conditional giant, only after confirmed V parry
    const giantDue = giant && !this.nesaGiantEvadeUsed && this.nesaGiantEvadeChosen &&
      gap < bigRadius + 0.65 &&
      t >= giantImpact - (0.44 + this.p.react[1] * 0.15) &&
      t < giantImpact + 0.08;
    const firstDue = !giant && !this.nesaEvadeUsed && this.nesaEvadeChosen &&
      gap < firstRadius + 0.65 && t >= this.nesaEvadeTrigger &&
      t < a!.wind + (spin ? Math.max(0.26, a!.active - 0.08) : 0.18);

    if (giantDue || firstDue) {
      if (giantDue) this.nesaGiantEvadeUsed = true;
      else this.nesaEvadeUsed = true;
      const radial = giantDue || area;
      // Heartbreaker has a giant second hit: conserve the 6-second dash for it.
      const useDash = f.dashCd <= 0 && f.onGround && (!giant || giantDue);
      const plan = this.nesaSafeEscape(f, o, radial, useDash);
      this.nesaRetreatDir.copy(plan.dir);
      // Leave the danger in one burst; do not blindly walk backwards at the wall.
      this.nesaRetreatT = giantDue ? 0.48 : radial ? 0.42 : 0.33;
      // Remove an earlier planned shield/parry, not the target's real combat rules.
      this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
      this.queue = []; this.hold = 0;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.block = false;
      f.intent.move.copy(plan.dir);
      // A genuine dash is only available when its real cooldown allows it.
      if (useDash) f.intent.dash.copy(plan.dir);
      else if (plan.gain < 0.30 && (giantDue || area) && f.onGround) {
        // If trapped against the boundary, guarding is better than stuck retreat.
        f.intent.block = true;
      }
      return true;
    }

    if (this.nesaRetreatT > 0 &&
        ((giant && t < giantImpact + 0.15 && gap < bigRadius + 1.0) ||
         (t < a!.wind + (spin ? a!.active : 0.30) && gap < firstRadius + 0.85))) {
      this.nesaRetreatT = Math.max(0, this.nesaRetreatT - dt);
      // Replan every frame, so changing position / boundary never pins the CPU.
      const radial = area;
      const allowDash = !giant || t >= giantImpact - 0.55;
      const plan = this.nesaSafeEscape(f, o, radial, allowDash);
      this.nesaRetreatDir.copy(plan.dir);
      f.intent.move.copy(plan.dir);
      f.intent.block = false;
      f.intent.attack = false;
      f.intent.skill = "";
      return true;
    }
    this.nesaRetreatT = 0;
    return false;
  }

  private jumpPulse = false;
  // FIGHT_ROYALE_GALE_SMASH_PRIORITY_V6: deliberate air-to-ground smash planning.
  private galeSmashKey = "";
  private galeSmashDelay = 0;
  private galeSmashNext = 0.35;

  /** Gale's aerial X/C/Z are actual dive ground-smashes, not normal ground casts.
   * Only plan while a smash is ready, the enemy is in reach, and no shield defense
   * is already pending. Use ordinary jump/skill buttons, preserving all cooldowns.
   */
  /** Track a real airborne target by sampling its position as frames pass.
   * Opponent velY and private attack cooldowns are intentionally NOT read.
   * Sudden teleports, knockback, and a new opponent invalidate stale samples.
   */
  private observeAerialOpponent(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (o !== this.aerialEnemy) {
      this.aerialEnemy = o;
      this.aerialWasUp = false;
      this.aerialHasVelocity = false;
      this.aerialSeenAt = -1;
      this.aerialLandedUntil = 0;
      this.aerialLandingSpent = false;
    }
    if (f.stage || o.stage || o.isDown()) {
      this.aerialWasUp = false;
      this.aerialLandedUntil = 0;
      return;
    }
    if (o.onGround) {
      if (this.aerialWasUp) {
        this.aerialWasUp = false;
        const profile = AERIAL_IQ[this.iqLevel];
        this.aerialLandedReactAt = now + rand(profile.landReact[0], profile.landReact[1]);
        this.aerialLandedUntil = now + 0.62;
        this.aerialLandingSpent = false;
        this.aerialHasVelocity = false;
      }
      return;
    }
    if (!this.aerialWasUp) {
      const profile = AERIAL_IQ[this.iqLevel];
      this.aerialWasUp = true;
      this.aerialSeenAt = now;
      this.aerialLastPos.copy(o.root.position);
      this.aerialVelocity.set(0, 0, 0);
      this.aerialLandingSpot.copy(o.root.position).setY(0);
      this.aerialLandingEta = 99;
      this.aerialHasVelocity = false;
      this.aerialNotice = Math.random() < profile.notice;
      this.aerialReactAt = now + rand(profile.react[0], profile.react[1]);
      this.aerialJumpChosen = Math.random() < profile.jump;
      this.aerialJumpSpent = false;
      this.aerialLandingSpent = false;
      // Imprecise per-jump aim. Do not reroll random noise every animation frame.
      const angle = rand(-Math.PI, Math.PI);
      this.aerialNoise.set(Math.cos(angle), 0, Math.sin(angle))
        .multiplyScalar(rand(0.25, 1) * profile.uncertainty);
      return;
    }
    const elapsed = now - this.aerialSeenAt;
    if (elapsed <= 0.012) return;
    const pos = o.root.position;
    const delta = pos.clone().sub(this.aerialLastPos);
    // Teleports / frame stalls should not produce absurd perfect predictions.
    if (elapsed > 0.25 || delta.length() > Math.max(2.7, 28 * elapsed)) {
      this.aerialHasVelocity = false;
    } else {
      const measured = delta.divideScalar(elapsed);
      if (Math.abs(measured.y) <= 25 && measured.length() <= 28) {
        this.aerialVelocity.lerp(measured, this.aerialHasVelocity ? 0.65 : 1);
        this.aerialHasVelocity = true;
      }
    }
    this.aerialSeenAt = now;
    this.aerialLastPos.copy(pos);
    if (!this.aerialHasVelocity) {
      this.aerialLandingEta = 99;
      return;
    }
    // Arena 3D gravity is 22m/s^2. Solve a ballistic landing estimate from
    // observed height and sampled vertical displacement, not a future position.
    const g = 22;
    const vy = this.aerialVelocity.y;
    const height = Math.max(0, pos.y);
    const t = (vy + Math.sqrt(vy * vy + 2 * g * height)) / g;
    this.aerialLandingEta = THREE.MathUtils.clamp(t, 0, 2.25);
    const lead = Math.min(t, 0.85); // err against over-leading distant jumpers
    const vx = THREE.MathUtils.clamp(this.aerialVelocity.x, -5.5, 5.5);
    const vz = THREE.MathUtils.clamp(this.aerialVelocity.z, -5.5, 5.5);
    this.aerialLandingSpot.set(
      pos.x + vx * lead + this.aerialNoise.x,
      0,
      pos.z + vz * lead + this.aerialNoise.z,
    );
    const radius = Math.max(1, f.arenaRadius - 0.55);
    const flat = this.aerialLandingSpot.length();
    if (flat > radius) this.aerialLandingSpot.multiplyScalar(radius / flat);
  }

  /** Approach the estimated touchdown position, not a magically known target.
   * Normal combat footwork remains the default. Hazard avoidance runs after
   * this method, so active fire patches can still veto an unsafe route.
   */
  private aerialFootwork(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (!this.aerialNotice || !this.aerialWasUp || now < this.aerialReactAt ||
        f.stage || o.stage || f.isDown() || f.state !== S.IDLE ||
        f.intent.block || this.blockHold > 0 || this.blockWait >= 0 ||
        f.intent.dash.lengthSq() > 0.01 || this.projectileSwordCommit > 0 ||
        f.chainBindTarget || f.chainBoundBy || this.iqBaitPhase !== "none") return;
    const target = this.aerialHasVelocity && this.aerialLandingEta < 1.25
      ? this.aerialLandingSpot : o.root.position;
    const toward = target.clone().sub(f.root.position).setY(0);
    const gap = toward.length();
    if (gap < 0.10) return;
    const airReach = f.attacks.air_l1?.reach ?? f.attacks.l1?.reach ?? 1.7;
    // A melee fighter should take a position inside actual weapon range.
    // Ranged fighters preserve room to cast, instead of dashing face-first.
    const preferred = RANGED.has(f.kit) ? 4.5 : Math.max(1.05, airReach * 0.77);
    if (gap > preferred + 0.38 && gap < 9.5) {
      f.intent.move.copy(this.theaterDirection(f, o, toward));
    } else if (!RANGED.has(f.kit) && gap < 0.82) {
      f.intent.move.copy(this.theaterDirection(f, o, toward.negate())).multiplyScalar(0.36);
    }
  }

  /** A planned counter-jump is allowed only in normal 3D arena mode.
   * No auto-launches/teleports: Fighter still processes a normal Space press.
   */
  private shouldAerialJump(f: Fighter, o: Fighter, gap: number): boolean {
    if (!this.aerialNotice || !this.aerialJumpChosen || this.aerialJumpSpent ||
        !this.aerialWasUp || !this.aerialHasVelocity ||
        this.threats.now() < this.aerialReactAt || f.stage || o.stage ||
        f.intent.block || f.intent.dash.lengthSq() > 0.01 ||
        this.blockHold > 0 || this.blockWait >= 0 ||
        this.projectileSwordCommit > 0 || this.threats.firePatches(f).some(p =>
          f.root.position.distanceTo(p.pos) < p.radius + 0.5) ||
        this.aerialLandingEta < 0.34 || this.aerialLandingEta > 1.25 ||
        o.root.position.y < 0.85 || o.root.position.y > 3.4 ||
        gap > Math.max(2.6, (f.attacks.air_l1?.reach ?? 1.9) + 0.75)) return false;
    this.aerialJumpSpent = true;
    return true;
  }

  /** Small post-touchdown attack opportunity. The target gets no forced stun,
   * and the fighter must already be in legitimate basic attack range.
   */
  private aerialLandingPunish(f: Fighter, o: Fighter): boolean {
    const now = this.threats.now();
    if (!this.aerialNotice || this.aerialLandingSpent || !o.onGround ||
        now < this.aerialLandedReactAt || now > this.aerialLandedUntil ||
        !f.onGround || f.stage || o.stage || f.state !== S.IDLE ||
        f.atkLock > 0 || f.intent.skill || f.intent.block ||
        this.blockHold > 0 || this.queue.length || this.hold > 0 ||
        this.projectileSwordCommit > 0 || RANGED.has(f.kit)) return false;
    const basic = f.attacks.l1;
    if (!basic || basic.type !== "melee") return false;
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    if (gap > basic.reach + 0.10) return false;
    // A landing in an active attack is not a safe punish by itself.
    if (o.state === S.ATTACK && o.atkPhase < 2 && o.atk?.type === "melee") return false;
    this.aerialLandingSpent = true;
    this.queue = [[0, 0.065]];
    this.hold = 0;
    return true;
  }

  private aerialAirStrikeChance(o: Fighter, dt: number): boolean {
    // Even when a jump wasn't recognized, the CPU may react to a target
    // it can presently reach. Timing depends on difficulty, not frame rate.
    const profile = AERIAL_IQ[this.iqLevel];
    const speed = !o.onGround && this.aerialNotice &&
      this.threats.now() >= this.aerialReactAt ? profile.strike * 1.2 : profile.strike;
    return Math.random() < 1 - Math.exp(-Math.max(0, dt) * speed);
  }

  private airDive(f: Fighter, o: Fighter, dt: number): boolean {
    this.galeSmashNext = Math.max(0, this.galeSmashNext - dt);
    if (f.isDown() || o.isDown()) { this.galeSmashKey = ""; return false; }
    const gap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    // Falling Star can chase farther; the other smashes need a nearby landing.
    const limits: Record<string, number> = { x: 6.0, c: 3.7, z: 2.9 };
    if (f.onGround) {
      this.galeSmashKey = ""; // clear any plan that ended by landing
      if (this.galeSmashNext > 0 || f.state !== S.IDLE || f.dashing() ||
          f.intent.block || this.blockHold > 0 || this.blockWait >= 0 ||
          f.intent.dash.lengthSq() > 0.01 || gap < 1.15) return false;
      // Only genuinely ready air variants qualify. Never launch just to waste Z/X/C.
      const choices = ["x", "c", "z"].filter((key) =>
        !!f.attacks[key + "_air"] && f.attacks[key + "_air"].mode === "dive" &&
        (f.cooldowns[key] ?? 1) <= 0 && gap <= limits[key]);
      if (!choices.length) return false;
      // Prioritize X's targeted crash, then C's whirlwind ground smash, then Z.
      // This intentionally does NOT spend a ready grounded skill first.
      const key = choices.includes("x") && (gap > 3.4 || Math.random() < 0.55)
        ? "x" : choices.includes("c") && Math.random() < 0.70
        ? "c" : choices.includes("z") ? "z" : choices[0];
      this.galeSmashKey = key;
      this.galeSmashDelay = 0.23 + Math.random() * 0.13;
      this.galeSmashNext = this.p.react[0] + 0.35 + Math.random() * 0.45;
      this.queue = []; this.hold = 0;
      f.intent.block = false;
      f.intent.attack = false;
      f.intent.skill = "";
      f.intent.jump = true;
      return true;
    }
    if (!this.galeSmashKey) return false;
    if ((f.cooldowns[this.galeSmashKey] ?? 1) > 0 ||
        !f.attacks[this.galeSmashKey + "_air"]) {
      this.galeSmashKey = "";
      return false;
    }
    // A knockback, an interrupt or another real action cancels the pending plan.
    if (f.state !== S.IDLE && f.state !== S.BLOCK) {
      this.galeSmashKey = "";
      return false;
    }
    this.galeSmashDelay -= dt;
    f.intent.jump = false; // release the jump button after taking off
    f.intent.attack = false;
    f.intent.block = false;
    this.queue = []; this.hold = 0;
    const selected = this.galeSmashKey;
    if (this.galeSmashDelay <= 0 || f.velY <= 0) {
      // Don't magically extend reach if a target fled during the leap.
      if (gap <= limits[selected] + 0.55) {
        f.intent.skill = selected; // Fighter chooses the legitimate _air version
        this.galeSmashKey = "";
      } else if (this.galeSmashDelay < -0.32) {
        this.galeSmashKey = ""; // no invalid cross-map homing smash
      }
    }
    return true;
  }
  private hopCd = 0;

  /** Platform-fight movement. Returns true when busy recovering (skip everything else). */
  private platform(f: Fighter, o: Fighter, dt: number): boolean {
    const st = f.stage!;
    const main = st.plats[0];
    const p = f.root.position;
    const press = () => { this.jumpPulse = !this.jumpPulse; f.intent.jump = this.jumpPulse; };
    // Recovery: off stage or below it -> drift home and jump.
    const offstage = p.x < main.x0 + 0.2 || p.x > main.x1 - 0.2 || p.y < main.y - 0.2;
    if (!f.onGround && offstage && (f.state === S.IDLE || f.state === S.ATTACK)) {
      f.intent.move.set(Math.sign(-p.x) || 1, 0, 0);
      if (f.velY < 1.5) {
        press();
        if (p.y < main.y - 1.5) for (const k of ["x", "z", "c"]) if (f.attacks[k].self_jump > 0 && f.cooldowns[k] <= 0) { f.intent.skill = k; break; }
      }
      return true;
    }
    if (o.out) { f.intent.move.set(Math.sign(-p.x) * (Math.abs(p.x) > 3 ? 1 : 0), 0, 0); return true; }
    const dx = o.root.position.x - p.x;
    const dy = o.root.position.y - p.y;
    const ranged = RANGED.has(f.kit);
    const want = ranged ? 5 : f.kit === "greatsword" ? 1.6 : f.kit === "hammer" ? 1.75 : 1.25;
    let mx = 0;
    if (Math.abs(dx) > want + 0.4) mx = Math.sign(dx);
    else if (ranged && Math.abs(dx) < 3) mx = -Math.sign(dx);
    // Don't walk off the main stage edge on purpose.
    if (f.onGround && mx && (p.x + mx * 0.6 < main.x0 + 0.6 || p.x + mx * 0.6 > main.x1 - 0.6)) mx = 0;
    f.intent.move.set(mx, 0, 0);
    this.hopCd -= dt;
    if (f.onGround && dy > 1.6 && Math.abs(dx) < 4 && this.hopCd <= 0) { press(); this.hopCd = 0.6; }
    else if (!f.onGround && dy > 1.2 && f.velY < 0.5 && this.hopCd <= 0) { press(); this.hopCd = 0.6; }
    else if (f.onGround && dy < -1.2 && p.y > 0.5 && Math.abs(dx) < 4) f.intent.move.z = 1; // drop through
    // Hop over incoming projectiles.
    for (const pr of this.threats.projectiles()) {
      if (pr.target !== f || this.seen.has(pr.id)) continue;
      if (this.tryProjectileClash(f, pr)) { this.seen.add(pr.id); continue; }
      this.seen.add(pr.id);
      if (Math.random() < this.p.jump + 0.15 && f.onGround) this.jumpWait = Math.max(f.chest().distanceTo(pr.pos) / Math.max(pr.vel.length(), 0.1) - 0.25, 0);
    }
    return false;
  }

  /** Raise guard in time for Ember's real delayed beam. The shield must have
   * finished raising at impact; no special AI-only immunity is granted.
   * A non-parryable beam therefore resolves as an ordinary costly block. */
  private defendIgnition(f: Fighter): boolean {
    const now = this.threats.now();
    for (const warning of this.threats.ignitions(f)) {
      const caster = warning.caster;
      const eta = warning.land - now;
      if (eta <= 0 || eta > 0.75) continue;
      // Mirror the beam's target-line calculation; don't guard a shot aimed elsewhere.
      const from = caster.model.castPoint.getWorldPosition(new THREE.Vector3());
      const target = caster.opponent && !caster.opponent.isDown()
        ? caster.opponent.chest() : from.clone().add(new THREE.Vector3(
          Math.sin(caster.root.rotation.y), 0, Math.cos(caster.root.rotation.y)));
      const direction = target.sub(from).normalize();
      const relative = f.chest().sub(from);
      const ahead = relative.dot(direction);
      const lateral = relative.addScaledVector(direction, -ahead).length();
      if (ahead < -0.2 || ahead > 11.4 || lateral > 1.45 + f.radius) continue;
      if (!this.ignitionChoices.has(warning.id)) {
        // Higher difficulties respond more reliably, but a compromised guard
        // or an attack already committed still makes the beam dangerous.
        const chance = this.p.block < 0.3 ? 0.40 : this.p.block < 0.45 ? 0.70
          : this.p.block < 0.6 ? 0.90 : 0.98;
        this.ignitionChoices.set(warning.id, Math.random() < chance);
        if (this.ignitionChoices.size > 48) this.ignitionChoices.clear();
      }
      if (!this.ignitionChoices.get(warning.id) || eta > 0.58) continue;
      if (f.state !== S.IDLE && f.state !== S.BLOCK) continue;
      this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
      this.queue = []; this.hold = 0; this.jumpWait = -1;
      f.intent.attack = false; f.intent.skill = ""; f.intent.jump = false;
      f.intent.block = true;
      f.intent.move.set(0, 0, 0);
      f.intent.sprint = false;
      return true;
    }
    return false;
  }

  private schedule(wait: number, dur: number) {
    if (this.blockHold > 0 || this.blockWait >= 0) return;
    this.blockWait = wait;
    this.blockDur = dur;
  }

  private react(f: Fighter, o: Fighter) {
    if (o.state === S.ATTACK && o.atkPhase === 0 && o.atk?.type === "melee" && o.swingSerial !== this.seenSwing) {
      this.seenSwing = o.swingSerial;
      if (f.state === S.HITSTUN || f.state === S.STAGGER) return;
      const tth = o.atk.wind - o.stateT;
      const r = Math.random();
      const bc = this.p.block * (o.atk.heavy ? 0.75 : 1);
      const festival = o.kit === "sickle" && o.bloodFestivalT > 0;
      const guardLow = f.guard <= f.maxGuard * 0.32;
      const dist = f.root.position.distanceTo(o.root.position);
      const canClash = f.state === S.IDLE && f.onGround && f.attacks.l1?.type === "melee" &&
        dist < (f.attacks.l1.reach + 0.35);
      // Zarek deliberately meets a real enemy blade occasionally to earn Clash Momentum.
      // Unlike a forced clash this is a normal light input with genuine wind-up timing.
      if (f.kit === "glaive" && f.look.element !== "metal" && f.onGround && f.state === S.IDLE &&
          o.atk?.type === "melee" && !o.atk.no_parry &&
          dist < f.attacks.l1.reach + 0.15 && tth >= f.attacks.l1.wind * 0.50 &&
          this.seenClashSwing !== o.swingSerial &&
          Math.random() < this.p.block * (f.clashMomentum < 3 ? 0.58 : 0.33)) {
        this.seenClashSwing = o.swingSerial;
        this.blockWait = -1; this.blockHold = 0;
        this.queue = [[0, 0.065]]; this.hold = 0;
        return;
      }
      // Guard critical / recently guard-broken: a timed attack can CLASH with a melee
      // swing. A fully staggered fighter must recover before trying. No special AI-only clash.
      if (guardLow && canClash) {
        this.blockWait = -1; this.blockHold = 0;
        this.queue = [[0, 0.06]]; this.hold = 0;
        return;
      }
      if (festival || (o.atk?.no_parry && !o.isContinuousComboActive())) {
        // Perfect parry cannot stop Veyr's festival melee. Block EARLY (regular guard),
        // or evade when guard cannot sustain a block. Clashes remain valid.
        if (!guardLow && f.onGround) this.schedule(0, Math.max(tth + 0.42, 0.48));
        else if (!canClash) { this.sideT = 0.30; this.sideSign = Math.random() < 0.5 ? -1 : 1; }
        return;
      }
      // Shield must finish rising before contact; successful parry makes the next 90% faster.
      const raise = f.nextShieldFast ? 0.01 : 0.10;
      if (r < this.p.parry) this.schedule(Math.max(tth - raise - 0.03, 0),
        o.isContinuousComboActive() ? Math.max(0.35, o.atk.wind + o.atk.active + o.atk.recover) : 0.3);
      else if (r < this.p.parry + bc) this.schedule(rand(this.p.react[0], this.p.react[1]) * 0.45,
        o.isContinuousComboActive() ? Math.max(0.5, o.atk.wind + o.atk.active + o.atk.recover) : tth + 0.45);
      else if (r < this.p.parry + bc + 0.15 && f.look.element !== "metal") this.trySkill(f, "z", true);
    }
    const charging = o.state === S.CHARGE;
    if (charging && !this.seenCharge) {
      this.seenCharge = true;
      if (Math.random() < 0.45) this.schedule(rand(this.p.react[0], this.p.react[1]), 1.4);
    } else if (!charging) this.seenCharge = false;
  }

  /** A continuous combo does not stop at the first successful parry or block. */
  private defendLongCombo(f: Fighter, o: Fighter) {
    if (!o.isContinuousComboActive()) { this.comboThreatSerial = -1; return; }
    if (this.comboThreatSerial === o.swingSerial) return;
    this.comboThreatSerial = o.swingSerial;
    const a = o.atk!;
    const distance = f.root.position.distanceTo(o.root.position);
    if (distance > Math.max(3.1, a.reach + 0.75) || f.state !== S.IDLE) return;
    // Fall back to a conventional block if parrying is unavailable or the CPU
    // is not skilled enough to risk timed deflections. Do not lock guard forever.
    const festival = o.kit === "sickle" && o.bloodFestivalT > 0;
    if ((festival || this.p.parry === 0) && this.blockWait < 0 && this.blockHold <= 0)
      this.schedule(0, Math.min(1.8, Math.max(0.3, a.wind + a.active + a.recover)));
  }

  /** Re-raise the shield just before *each real scheduled combo hit*.
   * Normal raise 100ms; the single-use parry reward shortens that to 10ms.
   * This is a true input-timing choice: Fighter.receiveHit still determines
   * whether contact parries, blocks, misses, or breaks guard. */
  private retimeComboParry(f: Fighter, o: Fighter): boolean {
    const active = o.isContinuousComboActive();
    const festival = o.kit === "sickle" && o.bloodFestivalT > 0;
    if (!active || festival || this.p.parry <= 0 || f.isDown()) {
      this.comboParrySerial = -1;
      this.comboParryTarget = -1;
      this.comboParryExamined = -1;
      this.comboParryReleased = false;
      return false;
    }
    const a = o.atk!;
    if (f.root.position.distanceTo(o.root.position) > Math.max(3.1, a.reach + 0.75)) return false;
    if (f.state !== S.IDLE && f.state !== S.BLOCK) return false;
    if (o.swingSerial !== this.comboParrySerial) {
      this.comboParrySerial = o.swingSerial;
      this.comboParryTarget = -1;
      this.comboParryExamined = -1;
      this.comboParryReleased = false;
    }
    const now = this.threats.now();
    if (this.comboParryTarget >= 0 && now > this.comboParryTarget + 0.04) {
      this.comboParryTarget = -1;
      this.comboParryReleased = false;
    }
    const raise = f.nextShieldFast ? 0.01 : 0.10;
    if (this.comboParryTarget < 0) {
      // Give Hard/Master a meaningful chance on *every new hit beat*.
      // Easy still blocks; Normal tries occasionally without perfect reaction.
      const chance = Math.min(0.88, 0.20 + this.p.parry * 2.2);
      for (const beat of this.threats.comboHits(o)) {
        if (beat > now + 0.9) break;
        if (beat <= this.comboParryExamined + 0.035) continue;
        if (beat < now + raise + 0.075) continue;
        this.comboParryExamined = beat;
        if (Math.random() < chance) {
          this.comboParryTarget = beat;
          this.comboParryReleased = false;
          break;
        }
      }
    }
    if (this.comboParryTarget < 0) return false;
    const eta = this.comboParryTarget - now;
    const desired = raise + 0.033; // shield reaches parry state just before the blade hits
    if (eta > desired + 0.073) return false;
    // Stop old block schedules. They made the shield stay raised, so late combo
    // contacts could only be blocked rather than parried.
    this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
    this.queue = []; this.hold = 0;
    if (f.state === S.BLOCK && !this.comboParryReleased) {
      // One frame with no shield input is necessary to reset the parry window.
      this.comboParryReleased = true;
      f.intent.block = false;
      return true;
    }
    if (eta <= desired + 0.020 && (f.state === S.IDLE || f.state === S.BLOCK)) {
      f.intent.block = true;
      // Mark the new shield raise as started; otherwise on the next frame the
      // AI would mistake its own newly-raised shield for an old held block and
      // release again, losing the parry window before the strike arrives.
      this.comboParryReleased = true;
      return true;
    }
    f.intent.block = false;
    return true;
  }

  /** Observe only projectiles already in the arena. No future inputs,
   * target cooldowns, or hidden opponent abilities are inspected.
   */
  private observeCounterfire(f: Fighter, o: Fighter) {
    if (this.counterfireEnemy !== o) {
      this.counterfireEnemy = o;
      this.counterfireReads.clear();
      this.counterfireRecoveryUntil = 0;
    }
    const now = this.threats.now();
    const shots = this.threats.projectiles();
    const living = new Set<number>();
    const readyShot = (f.attacks.l1?.type === "projectile" && f.atkLock <= 0) ||
      ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]
        .some(k => f.attacks[k]?.type === "projectile" && (f.cooldowns[k] ?? 1) <= 0);
    for (const p of shots) {
      living.add(p.id);
      if (this.counterfireReads.has(p.id)) continue;
      if (!readyShot || p.target !== f || (p.team !== undefined && p.team === f.team) ||
          p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb") continue;
      const eta = this.projectileTimeToContact(f, p);
      if (eta < 0.18 || eta > 1.75) continue;
      const profile = PROJECTILE_CLASH_IQ[this.iqLevel];
      this.counterfireReads.set(p.id, {
        reactAt: now + rand(profile.reaction[0], profile.reaction[1]),
        wants: Math.random() < profile.notice, spent: false,
      });
    }
    for (const id of this.counterfireReads.keys()) {
      if (!living.has(id)) this.counterfireReads.delete(id);
    }
    if (this.counterfireReads.size > 180) this.counterfireReads.clear();
  }

  /** Closest approach for an actually fired shot vs a moving hostile shot.
   * Game.fireProjectiles aims at the fighter's current opponent, so we forecast
   * that SAME aim and spread, not an impossible AI-only aimed projectile.
   * Real game projectile collision detection determines the eventual result.
   */
  private predictCounterfireCollision(f: Fighter, o: Fighter,
    p: ReturnType<Threats["projectiles"]>[number],
    a: Fighter["attacks"][string]): { time: number; miss: number } | null {
    if (a.type !== "projectile" || a.speed <= 0 ||
        p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb") return null;
    const eta = this.projectileTimeToContact(f, p);
    if (eta >= 999) return null;
    const origin = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const toward = o.chest().sub(origin);
    if (toward.lengthSq() < 0.05) return null;
    const aim = toward.normalize();
    // Conservative input and animation-frame overhead. Attack wind remains real.
    const launch = Math.max(0.025, a.wind) + 0.025;
    if (launch >= eta - 0.055) return null;
    const offsets = Math.max(1, Math.min(7, a.count));
    const profile = PROJECTILE_CLASH_IQ[this.iqLevel];
    let best: { time: number; miss: number } | null = null;
    for (let i = 0; i < offsets; i++) {
      const angle = offsets === 1 ? 0 : -a.spread + 2 * a.spread * i / (offsets - 1);
      const ownVel = aim.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), angle)
        .multiplyScalar(a.speed);
      const incomingAtLaunch = p.pos.clone().addScaledVector(p.vel, launch);
      const separation = origin.clone().sub(incomingAtLaunch);
      const relativeVel = ownVel.sub(p.vel);
      const speedSq = relativeVel.lengthSq();
      if (speedSq < 1.0) continue;
      const afterLaunch = -separation.dot(relativeVel) / speedSq;
      if (afterLaunch < 0.015 || afterLaunch > 1.10) continue;
      const collisionTime = launch + afterLaunch;
      // An interception after the shot reaches this fighter isn't defensive.
      if (collisionTime > eta - 0.025) continue;
      const miss = separation.addScaledVector(relativeVel, afterLaunch).length();
      const ownRadius = Math.max(0.14, Math.min(0.48, a.size *
        (a.style === "wave" || a.style === "shock" ? 0.37 : 0.23)));
      const theirSize = p.size ?? 1;
      const theirRadius = Math.max(0.14, Math.min(0.48, theirSize *
        (p.style === "wave" || p.style === "shock" ? 0.37 : 0.23)));
      // Difficulty uncertainty is a *stricter* collision requirement for easier
      // bots, not a fake enlargement of the real collision hitboxes.
      const believable = ownRadius + theirRadius - profile.tolerance;
      if (miss > Math.max(0.09, believable)) continue;
      if (!best || miss < best.miss) best = { time: collisionTime, miss };
    }
    return best;
  }

  /** Try ONE legal action per observed shot. Ordinary dodge/parry handling
   * takes over whenever the timing, angle or real attack availability fails.
   */
  private projectileCounterfire(f: Fighter, o: Fighter): boolean {
    const now = this.threats.now();
    if (now < this.counterfireRecoveryUntil || f.isDown() || o.isDown() ||
        f.state !== S.IDLE || !f.onGround || f.atkLock > 0 ||
        f.chainBindT > 0 || f.chainBoundBy || f.dashing() ||
        f.intent.block || f.intent.skill || f.intent.dash.lengthSq() > 0.01 ||
        this.blockWait >= 0 || this.blockHold > 0 || this.queue.length > 0 ||
        this.hold > 0 || this.projectileSwordCommit > 0 ||
        this.comboParryTarget > now ||
        (f.kit === "sickle" && f.bloodFestivalT > 0) ||
        this.threats.firePatches(f).some(p =>
          f.root.position.distanceTo(p.pos) < p.radius + 0.35)) return false;
    const profile = PROJECTILE_CLASH_IQ[this.iqLevel];
    let best: { shot: number; key: string; score: number } | null = null;
    for (const p of this.threats.projectiles()) {
      const read = this.counterfireReads.get(p.id);
      if (!read?.wants || read.spent || now < read.reactAt || p.target !== f ||
          p.atkType === "lob" || p.style === "bomb" || p.style === "clusterbomb" ||
          (p.team !== undefined && p.team === f.team)) continue;
      const eta = this.projectileTimeToContact(f, p);
      if (eta <= 0.10 || eta > 1.50) continue;
      const heavyIncoming = p.heavy === true || (p.size ?? 1) > 1.65;
      const keys = ["l1", "z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])];
      for (const key of keys) {
        const a = f.attacks[key];
        if (!a || a.type !== "projectile" ||
            (key !== "l1" && (f.cooldowns[key] ?? 1) > 0)) continue;
        const forecast = this.predictCounterfireCollision(f, o, p, a);
        if (!forecast) continue;
        // Avoid wasting an expensive skill if a free normal projectile is a
        // plausible intercept. High-strength shots can justify a heavier reply.
        const strongReply = a.heavy || a.pierce || a.dmg >= 95;
        if (heavyIncoming && !strongReply && this.iqLevel >= 2) continue;
        const expenditure = key === "l1" ? 0 :
          a.cd * (1.2 - profile.reserve) * 0.55;
        const score = (heavyIncoming && strongReply ? 4.8 : 0) +
          (key === "l1" ? 5.4 : 1.2) - expenditure - forecast.miss * 3 -
          forecast.time * 0.3;
        if (!best || score > best.score) best = { shot: p.id, key, score };
      }
    }
    if (!best) return false;
    const choice = best;
    const read = this.counterfireReads.get(choice.shot);
    if (read) read.spent = true;
    this.counterfireRecoveryUntil = now + (choice.key === "l1" ? 0.32 : 0.48);
    // Ordinary Fighter inputs only. These go through the normal attack windup,
    // cooldown, hit tests and Game.resolveProjectileClashes.
    this.queue = [];
    this.hold = 0;
    this.blockWait = -1;
    f.intent.block = false;
    f.intent.move.set(0, 0, 0);
    f.intent.sprint = false;
    if (choice.key === "l1") f.intent.attack = true;
    else {
      f.intent.attack = false;
      f.intent.skill = choice.key;
      this.skillCd = Math.max(this.skillCd, 0.27);
    }
    return true;
  }

  // Predict the actual crossing time of the projectile through the fighter's chest.
  // Sword collisions are ALWAYS Game.meleeCatchesProjectile; no fake hits or parries.
  private projectileTimeToContact(f: Fighter, pr: ReturnType<Threats["projectiles"]>[number]): number {
    const toward = f.chest().sub(pr.pos);
    const speedSq = pr.vel.lengthSq();
    if (speedSq <= 4) return 999;
    const eta = toward.dot(pr.vel) / speedSq;
    if (eta <= 0 || eta > 2.0) return 999;
    const nearest = pr.pos.clone().addScaledVector(pr.vel, eta);
    if (nearest.distanceTo(f.chest()) > 1.2 + f.radius) return 999;
    return eta;
  }

  private projectileSwordCommit = 0;

  /** A real basic sword tap can slice a shot only during the weapon's active frames.
   * We schedule the real tap/release so the blade arrives at the predicted shot. */
  private tryProjectileClash(f: Fighter, pr: ReturnType<Threats["projectiles"]>[number]): boolean {
    const a = f.attacks.l1;
    if (pr.target !== f || f.state !== S.IDLE || !f.onGround || a?.type !== "melee" ||
        f.atkLock > 0 || this.queue.length || this.hold > 0 || this.projectileSwordCommit > 0 ||
        this.blockHold > 0 || this.blockWait >= 0 || f.intent.block) return false;
    const eta = this.projectileTimeToContact(f, pr);
    const attackContact = 0.07 + a.wind + a.active * 0.35;
    if (eta < attackContact - 0.025 || eta > attackContact + 0.075) return false;
    const intercept = pr.pos.clone().addScaledVector(pr.vel, attackContact).sub(f.chest());
    if (Math.abs(intercept.y) > 1.0) return false;
    intercept.y = 0;
    if (intercept.length() > a.reach + 0.2) return false;
    const enemy = f.opponent;
    if (enemy && !enemy.isDown()) {
      const dir = enemy.root.position.clone().sub(f.root.position).setY(0);
      if (dir.lengthSq() > 0.001 && intercept.lengthSq() > 0.2 &&
          intercept.clone().normalize().dot(dir.normalize()) < -0.25) return false;
    }
    const skill = f.look.name.toLowerCase() === "garrick" ? 0.16 : 0;
    if (Math.random() > Math.min(0.94, 0.30 + this.p.block * 0.72 + skill)) return false;
    // Never give an instant unearned slice: use an ordinary basic input pulse.
    this.queue = [[0, 0.065]];
    this.hold = 0;
    this.projectileSwordCommit = 0.38;
    this.blockWait = -1;
    f.intent.skill = "";
    return true;
  }

  /** Timed parry input; blocks remain the normal game mechanic. A late or
   * unparryable shot will block or hit exactly as it did previously. */
  private tryProjectileParry(f: Fighter, pr: ReturnType<Threats["projectiles"]>[number]): boolean {
    if (f.state !== S.IDLE || !f.onGround || f.guard < f.maxGuard * 0.26 ||
        this.blockHold > 0 || this.blockWait >= 0 || this.projectileSwordCommit > 0) return false;
    const eta = this.projectileTimeToContact(f, pr);
    const raise = f.nextShieldFast ? 0.01 : 0.10;
    if (eta < raise + 0.035 || eta > raise + Math.min(f.parryWindow * 0.9, 0.22)) return false;
    if (Math.random() > this.p.parry * 2.0 + (f.look.name === "Garrick" ? 0.15 : 0.08)) return false;
    this.blockWait = 0;
    this.blockDur = Math.max(0.20, eta + 0.13);
    this.queue = [];
    this.hold = 0;
    f.intent.skill = "";
    return true;
  }

  /** Do not stand in Raven's hostile persistent paralysis ring.
   * Reaction is sampled once on entering range; skill and dash cooldowns are real.
   */
  private evadeStaticField(f: Fighter): boolean {
    const pools = this.threats.fields(f);
    const live = new Set(pools.map(p => p.id));
    for (const id of this.staticFieldChoices.keys()) if (!live.has(id)) this.staticFieldChoices.delete(id);
    if (f.isDown() || !f.onGround || f.dashing() || (f.state !== S.IDLE && f.state !== S.BLOCK)) return false;
    const now = this.threats.now();
    const here = f.root.position.clone().setY(0);
    const threat = pools.find(p => {
      if (Math.abs(p.center.y - f.root.position.y) > 1.6) return false;
      return here.distanceTo(p.center.clone().setY(0)) < p.radius + f.radius * 0.25;
    });
    if (!threat) return false;
    let decision = this.staticFieldChoices.get(threat.id);
    if (!decision) {
      decision = { reactAt: now + rand(this.p.react[0], this.p.react[1]),
        evade: Math.random() < Math.min(0.95, 0.43 + this.p.block * 0.70) };
      this.staticFieldChoices.set(threat.id, decision);
    }
    if (!decision.evade || now < decision.reactAt) return false;
    const away = here.sub(threat.center.clone().setY(0));
    if (away.lengthSq() < 0.005) away.set(f.id % 2 ? 1 : -1, 0, 0);
    away.normalize();
    if (f.stage) away.set(Math.sign(away.x) || (f.id % 2 ? 1 : -1), 0, 0);
    else {
      const r = f.arenaRadius - 0.5;
      const end = f.root.position.clone().setY(0).addScaledVector(away, 3);
      if (end.length() >= r) away.set(-away.z, 0, away.x);
    }
    this.queue = [];
    this.blockWait = -1;
    this.blockHold = 0;
    f.intent.block = false;
    f.intent.attack = false;
    f.intent.skill = "";
    f.intent.move.copy(away);
    if (f.dashCd <= 0 && f.root.position.distanceTo(threat.center) < threat.radius * 0.82)
      f.intent.dash.copy(away);
    return true;
  }

  /** Evade REAL telegraphed strike areas (Ocean Requiem, Thunderstorm,
   * Meteor, Tidal Ring, Arrow Rain, ground slams and other strike skills).
   * A choice is made once per actual warning and respects difficulty, reaction
   * times, walk speed, dash cooldown, arena edges and existing flame hazards.
   * There are no extra i-frames, teleports or forced successful dodges.
   */
  private evadeGroundStrikes(f: Fighter): boolean {
    const now = this.threats.now();
    const marks = this.threats.strikes();
    const live = new Set(marks.map(m => m.id));
    for (const id of this.strikeDecisions.keys()) {
      if (!live.has(id)) this.strikeDecisions.delete(id);
    }
    if (f.isDown() || !f.onGround || f.dashing() ||
        ![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(f.state) ||
        f.isKaedeThousandCutsCasting()) return false;
    type Zone = { id: number; center: THREE.Vector3; radius: number; eta: number;
      style: string; decision: { reactAt: number; evade: boolean; side: number } };
    const here = f.root.position.clone().setY(0);
    const zones: Zone[] = [];
    for (const m of marks) {
      if (!m.center || !m.radius || m.radius <= 0 || m.land <= now) continue;
      if (m.caster && (m.caster.team === f.team || m.caster.isDown())) continue;
      if (m.style === "nesa_heart_slam") continue; // handled at windup by evadeNesa: dodge OR block
      // The circle around a caster follows that caster until its actual impact.
      const center = (m.followsCaster && m.caster ? m.caster.root.position : m.center).clone();
      if (Math.abs(center.y - f.root.position.y) > 1.55) continue;
      center.y = 0;
      const eta = m.land - now;
      if (eta > 1.45) continue;
      const radius = m.radius + f.radius * 0.5 + 0.16;
      // If far from the circle, keep fighting instead of panic-dodging.
      if (here.distanceTo(center) > radius + Math.min(1.0, f.moveSpeed * eta)) continue;
      let decision = this.strikeDecisions.get(m.id);
      if (!decision) {
        const major = m.style === "requiem" || m.style === "lightning" ||
          m.style === "meteor" || m.style === "arrows" || m.style === "clusterbomb";
        const chance = this.p.block < 0.3 ? (major ? 0.33 : 0.22) :
          this.p.block < 0.45 ? (major ? 0.60 : 0.45) :
          this.p.block < 0.6 ? (major ? 0.78 : 0.64) :
          (major ? 0.91 : 0.82);
        decision = {
          reactAt: now + rand(this.p.react[0] * 0.65, this.p.react[1] * 0.90),
          evade: Math.random() < chance,
          side: Math.random() < 0.5 ? -1 : 1,
        };
        this.strikeDecisions.set(m.id, decision);
      }
      zones.push({ id: m.id, center, radius, eta, style: m.style || "", decision });
    }
    const imminent = zones.filter(z => z.decision.evade && now >= z.decision.reactAt &&
      z.eta > 0.015 && here.distanceTo(z.center) < z.radius + 0.45)
      .sort((a, b) => a.eta - b.eta);
    if (!imminent.length) return false;
    const primary = imminent[0];
    const fromCenter = here.clone().sub(primary.center);
    if (fromCenter.lengthSq() < 0.0001) fromCenter.set(f.id % 2 ? 1 : -1, 0, 0);
    fromCenter.normalize();
    const flank = new THREE.Vector3(-fromCenter.z, 0, fromCenter.x)
      .multiplyScalar(primary.decision.side);
    const candidates = [
      fromCenter, fromCenter.clone().addScaledVector(flank, 0.65).normalize(),
      fromCenter.clone().addScaledVector(flank, -0.65).normalize(),
      flank, flank.clone().negate(),
      fromCenter.clone().negate().addScaledVector(flank, 0.6).normalize(),
    ];
    // A single marked Thunderstorm hit can be escaped by walking if the AI
    // reacts early enough. Reserve a real 3-second dash for the larger circles.
    const steer = f.state === S.IDLE ? 1 : f.state === S.BLOCK ? 0.50 :
      f.state === S.CHARGE ? 0.4 : 0;
    const canDash = f.dashCd <= 0 &&
      (f.kit !== "hammer" || f.state !== S.ATTACK ||
        (f.atkPhase === 0 && !!f.atk && f.stateT < f.atk.wind));
    const walkDist = f.moveSpeed * steer * Math.max(0, primary.eta - 0.045);
    const patches = this.threats.firePatches(f);
    const main = f.stage?.plats[0];
    const destination = (dir: THREE.Vector3, distance: number) => {
      const end = here.clone().addScaledVector(dir, distance);
      if (main) end.x = THREE.MathUtils.clamp(end.x, main.x0 + 0.65, main.x1 - 0.65);
      else {
        const max = f.arenaRadius - Math.max(0.17, f.radius * 0.15);
        const d = end.length();
        if (d > max) end.multiplyScalar(max / d);
      }
      return end;
    };
    const score = (end: THREE.Vector3) => {
      let result = 0;
      // Value escaping multiple overlapping circles, not just the first one.
      for (const zone of zones) {
        const clearance = end.distanceTo(zone.center) - zone.radius;
        const importance = zone.id === primary.id ? 2.8 :
          zone.eta <= primary.eta + 0.27 ? 1.2 : 0.45;
        result += importance * THREE.MathUtils.clamp(clearance, -3, 0.65);
      }
      for (const fire of patches) {
        if (Math.abs(fire.pos.y - f.root.position.y) > 1.55) continue;
        const gap = end.distanceTo(fire.pos.clone().setY(0));
        const safe = fire.radius + f.radius * 0.3 + 0.2;
        if (gap < safe) result -= (safe - gap + 0.2) * 5;
      }
      // Prefer a real escape path over a direction blocked by the arena wall.
      result += Math.min(end.distanceTo(here), 2.6) * 0.15;
      return result;
    };
    let bestWalk = candidates[0], bestWalkScore = -Infinity;
    let bestDash = candidates[0], bestDashScore = -Infinity;
    for (const raw of candidates) {
      const dir = main ? new THREE.Vector3(Math.sign(raw.x) || (f.id % 2 ? 1 : -1), 0, 0) : raw;
      const walk = score(destination(dir, walkDist));
      if (walk > bestWalkScore) { bestWalkScore = walk; bestWalk = dir; }
      if (canDash) {
        // A normal dash moves 14 units/s for 0.30s; use only the distance
        // available before impact when estimating whether this will escape.
        const dashDist = 14 * Math.min(0.3, primary.eta);
        const dash = score(destination(dir, dashDist + f.moveSpeed *
          Math.max(0, primary.eta - 0.3) * 0.85));
        if (dash > bestDashScore) { bestDashScore = dash; bestDash = dir; }
      }
    }
    const canWalkOut = steer > 0 && bestWalkScore >= 0.13;
    // Dodging is intentional, but not omniscient: only spend dash when ordinary
    // footwork will not safely leave the marked impact area in time.
    const useDash = canDash && (!canWalkOut ||
      (primary.eta < 0.19 && bestDashScore > bestWalkScore + 0.25)) &&
      bestDashScore > bestWalkScore + 0.10;
    if (!useDash && steer <= 0) return false;
    const dir = useDash ? bestDash : bestWalk;
    this.queue = [];
    this.hold = 0;
    this.blockWait = -1;
    this.blockHold = 0;
    this.jumpWait = -1;
    f.intent.block = false;
    f.intent.attack = false;
    f.intent.skill = "";
    f.intent.sprint = false;
    f.intent.move.copy(dir);
    if (useDash) f.intent.dash.copy(dir);
    return true;
  }

  private dodge(f: Fighter) {
    for (const p of this.threats.projectiles()) {
      if (p.target !== f || this.seen.has(p.id)) continue;
      const predicted = this.projectileTimeToContact(f, p);
      // Defer the first defensive reaction only if counterfire has
      // enough time to fire before actual collision.
      const counterRead = this.counterfireReads.get(p.id);
      if (counterRead?.wants && !counterRead.spent && predicted < 999) {
        const remaining = counterRead.reactAt - this.threats.now();
        if (remaining > 0 && remaining + 0.17 < predicted) continue;
      }
      // Do not consume the shot at spawn time. Wait for its actionable window.
      const blade = f.attacks.l1;
      const canPrepareSlice = predicted < 999 && f.state === S.IDLE && f.onGround &&
        blade?.type === "melee" && f.atkLock <= 0 &&
        this.blockHold <= 0 && this.blockWait < 0;
      // Only a fighter preparing to slice delays their usual defense decision.
      // Everyone else's existing jump/block logic stays at the same timing.
      if (canPrepareSlice && predicted > 0.07 + blade.wind + blade.active * 0.35 + 0.075) continue;
      if (this.tryProjectileClash(f, p) || this.tryProjectileParry(f, p)) {
        this.seen.add(p.id);
        continue;
      }
      this.seen.add(p.id);
      const eta = predicted < 999 ? predicted : f.chest().distanceTo(p.pos) / Math.max(p.vel.length(), 0.1);
      const r = Math.random();
      if (r < this.p.jump && f.onGround) this.jumpWait = Math.max(eta - 0.28, 0);
      else if (r < this.p.jump + this.p.block) this.schedule(Math.min(Math.max(eta - 0.2, 0), this.p.react[1]), eta + 0.2);
    }
    if (this.seen.size > 300) this.seen.clear();
  }

  /** Real walking pressure while the current spin is active; no homing. */
  private kaizenSpinAdvance(f: Fighter, o: Fighter) {
    if (f.kit !== "chainblade" || f.state !== S.ATTACK || !f.onGround ||
        !f.atk || f.atkPhase > 1 || f.isDown() || o.isDown() ||
        !["chain_razor_cyclone", "chain_death_spiral", "chain_carousel"].includes(f.atk.style) ||
        f.intent.dash.lengthSq() > 0.01 || f.intent.block) return;
    const to = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = to.length();
    const seekRange = f.atk.style === "chain_death_spiral" ? 3.1 : 2.0;
    // No auto-target lock or wall crossing; walking ends when target is close.
    if (gap < 1.35 || gap > seekRange + 2.5) return;
    const dir = to.multiplyScalar(1 / Math.max(0.001, gap));
    if (!f.stage) {
      // Do not march into active Ember fire while spinning; retreat/evade AI
      // still takes priority outside this controlled pursuit routine.
      const here = f.root.position.clone().setY(0);
      const nextStep = here.clone().addScaledVector(dir, 0.8);
      for (const patch of this.threats.firePatches(f)) {
        if (Math.abs(patch.pos.y - f.root.position.y) > 1.55) continue;
        const safe = patch.radius + f.radius * 0.3 + 0.22;
        const currentGap = here.distanceTo(patch.pos.clone().setY(0));
        const nextGap = nextStep.distanceTo(patch.pos.clone().setY(0));
        if (nextGap < safe && nextGap < currentGap - 0.05) return;
      }
    }
    if (f.stage) {
      const main = f.stage.plats[0];
      if (!main || f.root.position.x + Math.sign(dir.x) * 0.65 < main.x0 + 0.6 ||
          f.root.position.x + Math.sign(dir.x) * 0.65 > main.x1 - 0.6) return;
      f.intent.move.set(Math.sign(dir.x), 0, 0);
    } else {
      const next = f.root.position.clone().addScaledVector(dir, 0.65).setY(0);
      if (next.length() > f.arenaRadius - 0.25) return;
      f.intent.move.copy(dir);
    }
    f.intent.sprint = false;
  }

  /** Advanced 3D footwork uses existing intent.move only: no added dash,
   * attack range, i-frames, guard bypass, or privileged enemy information.
   * Scoring candidate *paths* prevents a great orbit from stepping into fire
   * or trying to walk through the circular arena wall.
   */
  private advancedFootwork(f: Fighter, o: Fighter, dt: number) {
    if (f.stage || o.stage || f.isDown() || o.isDown() || !f.onGround ||
        f.state !== S.IDLE || f.intent.block || f.intent.attack || f.intent.skill ||
        f.intent.jump || f.intent.dash.lengthSq() > 0.01 ||
        this.blockHold > 0 || this.blockWait >= 0 || this.sideT > 0 ||
        this.projectileSwordCommit > 0 || this.queue.length || this.hold > 0 ||
        this.iqBaitPhase !== "none" || this.tacticsT > 0 ||
        (this.theaterMode !== "none" && this.theaterT > 0) ||
        f.chainBindT > 0 || f.chainBoundBy) return;
    // A committed opponent attack is for dodge/block/parry AI, not voluntary
    // circling. Do not overwrite an urgent response to a visible wind-up.
    const from = f.root.position.clone().setY(0);
    const foe = o.root.position.clone().setY(0);
    const delta = foe.clone().sub(from);
    const gap = delta.length();
    if (gap < 0.08) return;
    const toward = delta.clone().divideScalar(gap);
    if (o.state === S.ATTACK && o.atkPhase === 0 &&
        o.atk?.type === "melee" && gap < o.atk.reach + 0.85) return;
    const now = this.threats.now();
    if (o !== this.advancedEnemy) {
      this.advancedEnemy = o;
      this.advancedMode = "none";
      this.advancedRetryAt = 0;
      this.advancedPlanUntil = 0;
      this.advancedLastDir.set(0, 0, 0);
      this.advancedSampleAt = now;
      this.advancedSamplePos.copy(from);
    }
    const profile = ADVANCED_FOOTWORK[this.iqLevel];
    const arena = Math.max(1.5, f.arenaRadius - f.radius - 0.32);
    const ownClearance = arena - from.length();
    const enemyClearance = arena - foe.length();
    const urgentWall = ownClearance < 1.15;
    const ranged = RANGED.has(f.kit);
    const band = this.effectiveRangeBand(f, o);
    // A small sample can detect being trapped against a wall. A change of
    // orbit direction is then deliberate instead of oscillating every frame.
    if (now - this.advancedSampleAt >= 0.52) {
      if (this.advancedLastDir.lengthSq() > 0.10 &&
          from.distanceTo(this.advancedSamplePos) < 0.16 &&
          ownClearance < 2.1 && this.iqLevel >= 2) {
        this.advancedSide *= -1;
        this.advancedPlanUntil = 0;
        this.advancedRetryAt = 0;
      }
      this.advancedSampleAt = now;
      this.advancedSamplePos.copy(from);
    }
    if (urgentWall && this.advancedMode !== "escape") {
      this.advancedMode = "escape";
      this.advancedPlanUntil = now + 0.36;
    } else if (now >= this.advancedPlanUntil) {
      if (now < this.advancedRetryAt) return;
      // Recognition happens once per short plan, not at the frame rate.
      const seen = Math.random() < profile.read;
      this.advancedRetryAt = now + rand(profile.react[0], profile.react[1]);
      this.advancedPlanUntil = this.advancedRetryAt + rand(0.36, 0.84);
      if (!seen) { this.advancedMode = "none"; return; }
      if (this.iqLevel > 0 && Math.random() < 0.24) this.advancedSide *= -1;
      if (o.state === S.BLOCK && gap < Math.max(4.0, band.far + 1.2) &&
          Math.random() < profile.flank) this.advancedMode = "flank";
      else if (enemyClearance < 2.65 && !ranged && gap < 7.6 &&
               Math.random() < profile.corner) this.advancedMode = "corner";
      else if (Math.random() < profile.orbit) this.advancedMode = "orbit";
      else this.advancedMode = "none";
    }
    if (this.advancedMode === "none") return;
    if (this.advancedMode === "flank" && o.state !== S.BLOCK) {
      this.advancedMode = "orbit";
    }
    if (this.advancedMode === "escape" && ownClearance > 2.4 &&
        now >= this.advancedPlanUntil) this.advancedMode = "orbit";

    const tangent = new THREE.Vector3(-toward.z, 0, toward.x);
    const inward = from.lengthSq() > 0.001
      ? from.clone().negate().normalize() : toward.clone();
    const desired = f.intent.move.clone().setY(0);
    if (desired.lengthSq() > 0.01) desired.normalize();
    const baseline = gap > band.far ? toward.clone() :
      gap < band.near ? toward.clone().negate() :
      tangent.clone().multiplyScalar(this.advancedSide);
    const character = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];
    const personalShift = character ? CHARACTER_IQ[this.iqLevel].strength *
      (character.spacing + (this.personaMode === "reset" ? 0.48 :
        this.personaMode === "pressure" ? -0.30 : 0.10)) : 0;
    const ideal = THREE.MathUtils.clamp(band.ideal + personalShift, 1.05, 6.4);
    const target = baseline.clone();
    if (this.advancedMode === "escape") {
      // Near the boundary, move back toward the middle with a tangential bias
      // if the foe is standing directly in the escape lane.
      target.copy(inward).multiplyScalar(1.5);
      if (gap < (o.attacks.l1?.reach ?? 1.8) + 0.5)
        target.addScaledVector(tangent, 0.75 * this.advancedSide);
    } else if (this.advancedMode === "flank") {
      // Use the observed shield's current direction, not hidden input. The
      // enemy still turns normally, so a flank is NEVER a forced backstab.
      const front = new THREE.Vector3(Math.sin(o.root.rotation.y), 0,
                                      Math.cos(o.root.rotation.y));
      const shieldSide = new THREE.Vector3(-front.z, 0, front.x)
        .multiplyScalar(this.advancedSide);
      const flankGoal = foe.clone()
        .addScaledVector(front, -ideal * 0.55)
        .addScaledVector(shieldSide, Math.max(1.15, ideal * 0.88));
      target.copy(flankGoal.sub(from));
      if (gap < band.near) target.addScaledVector(toward, -0.5);
    } else if (this.advancedMode === "corner") {
      // Approach an opponent pinned to the edge from the CENTER side, not
      // from outside the arena. Preserve range and a little orbit motion.
      const outward = foe.lengthSq() > 0.001
        ? foe.clone().normalize() : toward.clone();
      const cornerGoal = foe.clone().addScaledVector(outward, -ideal);
      const around = new THREE.Vector3(-outward.z, 0, outward.x);
      cornerGoal.addScaledVector(around, this.advancedSide * 0.25 * ideal);
      target.copy(cornerGoal.sub(from));
    } else { // orbit
      const correction = THREE.MathUtils.clamp((gap - ideal) * 0.62, -1, 1);
      target.copy(tangent).multiplyScalar(this.advancedSide * 0.85)
        .addScaledVector(toward, correction);
    }
    if (target.lengthSq() < 0.001) target.copy(baseline);
    target.normalize();

    // Test a normal walking-distance horizon, with several intermediate
    // samples. Unsafe paths are rejected instead of later corrected by a dash.
    const look = THREE.MathUtils.clamp(f.moveSpeed * 0.30, 0.85, 1.75);
    const angles = [-1.30, -0.98, -0.66, -0.34, 0, 0.34, 0.66, 0.98, 1.30];
    const options = [target.clone(), baseline.clone(), desired.clone(),
      inward.clone(), tangent.clone(), tangent.clone().negate(),
      ...angles.map(angle => new THREE.Vector3(
        target.x * Math.cos(angle) - target.z * Math.sin(angle), 0,
        target.x * Math.sin(angle) + target.z * Math.cos(angle))),
    ];
    const fires = this.threats.firePatches(f).filter(p =>
      Math.abs(p.pos.y - f.root.position.y) < 1.55);
    let best: THREE.Vector3 | null = null;
    let bestScore = -Infinity;
    for (const candidate of options) {
      if (candidate.lengthSq() < 0.001) continue;
      const dir = candidate.normalize();
      const future = from.clone().addScaledVector(dir, look);
      // No choosing a direction that will hit the wall; leaving a wall is OK.
      let unsafe = false;
      let penalty = 0;
      for (const t of [0.35, 0.7, 1.0]) {
        const p = from.clone().addScaledVector(dir, look * t);
        const extent = p.length();
        if (extent > arena + 0.015 && extent >= from.length() - 0.02) {
          unsafe = true;
          break;
        }
        if (extent > arena - 0.38) penalty += (extent - arena + 0.38) * 4.0;
        for (const fire of fires) {
          const fireGap = Math.hypot(p.x - fire.pos.x, p.z - fire.pos.z);
          const safe = fire.radius + f.radius * 0.35 + 0.30;
          if (fireGap < safe) {
            const hereGap = Math.hypot(from.x - fire.pos.x, from.z - fire.pos.z);
            // Already burning: allow walking OUT, not further into the fire.
            if (fireGap >= hereGap + 0.08) continue;
            penalty += 11 + (safe - fireGap) * 8;
          } else if (fireGap < safe + 0.35) {
            penalty += (safe + 0.35 - fireGap) * 1.5;
          }
        }
      }
      if (unsafe) continue;
      const nextGap = future.distanceTo(foe);
      const rangeGain = Math.abs(gap - ideal) - Math.abs(nextGap - ideal);
      let score = dir.dot(target) * 2.5 + rangeGain * 0.90 - penalty;
      if (desired.lengthSq() > 0.01) score += dir.dot(desired) * 0.43;
      if (this.advancedLastDir.lengthSq() > 0.1)
        score += dir.dot(this.advancedLastDir) * 0.16;
      if (this.advancedMode === "escape") {
        score += (future.length() < from.length() ? 2.5 : -2.0);
        score += dir.dot(inward) * 3.0;
      }
      if (this.advancedMode === "corner") {
        const outward = foe.lengthSq() > 0.001 ? foe.clone().normalize() : toward;
        const myCenterSide = future.clone().sub(foe).dot(outward);
        if (myCenterSide > -0.2) score -= 2.0;
      }
      if (score > bestScore) { bestScore = score; best = dir.clone(); }
    }
    if (!best) {
      // Don't walk into fire/walls if all candidate movement paths are unsafe.
      // Leave the existing movement choice to the hazard defense below.
      this.advancedLastDir.set(0, 0, 0);
      return;
    }
    // Planned movement remains ordinary fighter walking, not frame-perfect
    // strafing or free dodges. Higher AI just picks safer angles more often.
    const pace = this.advancedMode === "escape" ? 1 :
      this.advancedMode === "orbit" ? 0.68 : 0.86;
    f.intent.move.copy(best).multiplyScalar(pace);
    this.advancedLastDir.copy(best);
  }

  private position(f: Fighter, o: Fighter, dt: number) {
    const d = o.root.position.clone().sub(f.root.position);
    d.y = 0;
    const dist = d.length();
    d.divideScalar(Math.max(dist, 0.001));
    const side = new THREE.Vector3(-d.z, 0, d.x);
    if (this.sideT > 0) { this.sideT -= dt; f.intent.move.copy(side).multiplyScalar(this.sideSign); return; }
    if (RANGED.has(f.kit)) {
      this.strafeT -= dt;
      if (this.strafeT <= 0) { this.strafeT = rand(0.6, 1.4); this.sideSign = [-1, 0, 1][Math.floor(Math.random() * 3)]; }
      if (dist < 3.2) f.intent.move.copy(d).negate().addScaledVector(side, this.sideSign * 0.5);
      else if (dist > 6.5) f.intent.move.copy(d);
      else if (this.sideSign) f.intent.move.copy(side).multiplyScalar(this.sideSign * 0.6);
    }
  }

  /** Navigate around enemy ground fire without teleporting or dodging through it.
   * Samples candidate movement directions so the CPU avoids both entering a
   * burning circle and stepping into a second circle while escaping the first.
   * If already burning, it attempts to leave by the shortest safe path.
   * Does not touch shield/parry/skill input or any character damage numbers. */
  private avoidFireGround(f: Fighter) {
    if (f.isDown() || !f.onGround || (f.state !== S.IDLE && f.state !== S.BLOCK)) return;
    const patches = this.threats.firePatches(f).filter(p =>
      Math.abs(p.pos.y - f.root.position.y) < 1.55);
    if (!patches.length) { this.fireAvoidKey = ""; return; }

    const at = f.root.position.clone().setY(0);
    const desired = f.intent.move.clone().setY(0);
    const hasMove = desired.lengthSq() > 0.01;
    if (hasMove) desired.normalize();
    const look = Math.min(1.85, Math.max(0.9, f.moveSpeed * 0.36));

    // Find the hazard that is being stood in or intersects the next movement.
    // A small margin keeps the CPU's body just outside the damage boundary.
    let dangerous: { pos: THREE.Vector3; radius: number } | null = null;
    let dangerScore = -Infinity;
    for (const p of patches) {
      const dx = p.pos.x - at.x, dz = p.pos.z - at.z;
      const safe = p.radius + f.radius * 0.30 + 0.22;
      const along = hasMove ? THREE.MathUtils.clamp(dx * desired.x + dz * desired.z, 0, look) : 0;
      const close = Math.hypot(dx - desired.x * along, dz - desired.z * along);
      const here = Math.hypot(dx, dz);
      const inFire = here < safe;
      // Never hijack an existing move if it heads cleanly OUT of a fire patch.
      const escaping = inFire && hasMove && (dx * desired.x + dz * desired.z) < -0.60 * here;
      if ((!hasMove && !inFire) || (escaping && close >= here - 0.12)) continue;
      if (inFire || (hasMove && close < safe)) {
        const score = (inFire ? 3 : 1) + (safe - Math.min(close, here));
        if (score > dangerScore) { dangerScore = score; dangerous = p; }
      }
    }
    if (!dangerous) { this.fireAvoidKey = ""; return; }

    const away = new THREE.Vector3(at.x - dangerous.pos.x, 0, at.z - dangerous.pos.z);
    if (away.lengthSq() < 0.0001) {
      if (hasMove) away.copy(desired).negate();
      else away.set(f.id % 2 ? 1 : -1, 0, 0);
    }
    away.normalize();
    const tangent = new THREE.Vector3(-away.z, 0, away.x);
    const key = `${dangerous.pos.x.toFixed(2)}:${dangerous.pos.z.toFixed(2)}`;
    if (this.fireAvoidKey !== key) {
      this.fireAvoidKey = key;
      const preference = hasMove ? desired.dot(tangent) : 0;
      this.fireAvoidSide = Math.abs(preference) > 0.1 ? Math.sign(preference) : (f.id % 2 ? 1 : -1);
    }

    if (f.stage) {
      // Platform arenas are effectively one-dimensional: don't step off-stage
      // merely to dodge a ground patch, and never use z (down/drop-through).
      const main = f.stage.plats[0];
      const choices = [this.fireAvoidSide, -this.fireAvoidSide];
      let best = 0, bestScore = -Infinity;
      for (const sign of choices) {
        const x = at.x + sign * look;
        if (x < main.x0 + 0.55 || x > main.x1 - 0.55) continue;
        let score = sign * desired.x * 0.7;
        for (const p of patches) {
          const gap = Math.hypot(x - p.pos.x, at.z - p.pos.z);
          const safe = p.radius + f.radius * 0.3 + 0.22;
          if (gap < safe) score -= 10 * (safe - gap + 0.15);
        }
        if (score > bestScore) { bestScore = score; best = sign; }
      }
      if (best !== 0) f.intent.move.set(best, 0, 0);
      return;
    }

    // Prefer keeping the original path, but strongly penalize any candidate
    // that intersects fire at successive lookahead points.
    const flank = tangent.clone().multiplyScalar(this.fireAvoidSide);
    const candidates = [
      ...(hasMove ? [desired.clone()] : []),
      away.clone(), flank.clone(),
      away.clone().multiplyScalar(0.5).add(flank).normalize(),
      away.clone().addScaledVector(flank, 0.45).normalize(),
      away.clone().addScaledVector(flank, -0.45).normalize(),
      flank.clone().negate(),
      ...(hasMove ? [desired.clone().add(flank).normalize(), desired.clone().sub(flank).normalize()] : []),
    ];
    let best = candidates[0], bestScore = -Infinity;
    for (const dir of candidates) {
      let score = hasMove ? dir.dot(desired) * 1.1 : 0;
      score += dir.dot(flank) * 0.10; // stable clockwise/counterclockwise detour
      for (const distance of [0.35, 0.75, 1.25, look]) {
        const x = at.x + dir.x * distance;
        const z = at.z + dir.z * distance;
        const arenaEdge = Math.hypot(x, z) - (f.arenaRadius - 0.35);
        if (arenaEdge > 0) score -= 25 * arenaEdge;
        for (const p of patches) {
          const gap = Math.hypot(x - p.pos.x, z - p.pos.z);
          const safe = p.radius + f.radius * 0.30 + 0.22;
          if (gap < safe) score -= 7 * (safe - gap + 0.18);
          else if (gap < safe + 0.25) score -= 0.8 * (safe + 0.25 - gap);
        }
      }
      if (score > bestScore) { bestScore = score; best = dir; }
    }
    f.intent.move.copy(best);
  }

/** Range-conscious footwork. Real weapon/ready skill reach determines where to
 * stand; dodge, guard, parry, hazard and stage movement take precedence. */
  /** Fighter-specific tactical *intent*: no hidden enemy inputs or cooldowns.
   * Decisions are sampled once per plan, with longer gaps on easier settings.
   * Normal emergency dodge/parry reactions still have priority.
   */
  private personalityRead(f: Fighter, o: Fighter) {
    const now = this.threats.now();
    if (this.personaEnemy !== o) {
      this.personaEnemy = o;
      this.personaNextAt = now + rand(0.25, 0.55);
      this.personaMode = "none";
    }
    if (now < this.personaNextAt) return;
    const profile = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];
    if (!profile || f.isDown() || o.isDown()) return;
    const iq = CHARACTER_IQ[this.iqLevel];
    this.personaNextAt = now + rand(iq.gap[0], iq.gap[1]);
    if (Math.random() > iq.read) {
      this.personaMode = "none"; // a missed tactical read isn't re-rolled per frame
      return;
    }
    const gap = f.root.position.clone().setY(0).distanceTo(
      o.root.position.clone().setY(0));
    const near = gap < (o.attacks.l1?.reach ?? 1.9) + 0.50;
    const opening = this.hasPunishWindow(o);
    const blocking = o.state === S.BLOCK;
    const guardWeak = o.guard / Math.max(1, o.maxGuard) < 0.35;
    const ownGuardWeak = f.guard / Math.max(1, f.maxGuard) < 0.33;
    const lowHp = f.hp / Math.max(1, f.maxHp) < 0.38;
    const enemyStrong = o.hp / Math.max(1, o.maxHp) > 0.55;
    let pressure = profile.pressure;
    let probe = profile.probe;
    let reset = profile.reset;
    if (opening) pressure += 1.60;
    if (guardWeak && near) pressure += 0.62;
    if (blocking) probe += 0.60;
    if (ownGuardWeak) { reset += 1.00; pressure *= 0.75; }
    if (lowHp && enemyStrong) { reset += 0.54; pressure *= 0.78; }
    switch (profile.role) {
      case "counter":     if (!opening && o.state === S.IDLE) probe += 0.62; break;
      case "duelist":    if (opening) pressure += 0.50; break;
      case "juggernaut": if (blocking) pressure += 0.85; break;
      case "riposte":    if (o.state === S.ATTACK && near) probe += 0.78; break;
      case "artillery":  if (near) reset += 1.1; break;
      case "support":    if (f.hp < f.maxHp * 0.70) reset += 1.0; break;
      case "ambush":     if (opening) pressure += 0.85; else probe += 0.25; break;
      case "rush":       if (!ownGuardWeak) pressure += 0.92; break;
      case "skirmish":   if (near && !opening) probe += 0.65; break;
      case "trapper":    if (f.barrelOut) probe += 0.75; if (near) reset += 0.60; break;
      case "kickboxer":  if (opening && near) pressure += 1.0; break;
      case "controller": if (near) reset += 0.95; else probe += 0.48; break;
      case "sniper":     if (gap < 4.0) reset += 1.35; break;
      case "executioner": if (f.bloodFestivalT > 0) pressure += 3.0; break;
      case "glaive":     if (f.clashMomentum >= 2) pressure += 0.95; break;
      case "grappler":   if (gap > 1.8 && gap < 4.7 &&
          (f.cooldowns.x ?? 1) <= 0) probe += 1.1; break;
      case "bruiser":    if (f.nesaCCharges > 0 && opening) pressure += 1.0; break;
    }
    const roll = Math.random() * (pressure + probe + reset);
    this.personaMode = roll < pressure ? "pressure" :
      roll < pressure + probe ? "probe" : "reset";
  }

  /** Style-aware scoring, not a scripted cast. Real equipped keys, cooldowns,
   * block, attack recovery, range and the V unlock are still checked elsewhere.
   */
  private personalitySkillScore(f: Fighter, o: Fighter, key: string, distance: number): number {
    const profile = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];
    if (!profile) return 0;
    const a = f.attacks[key];
    if (!a) return 0;
    const strength = CHARACTER_IQ[this.iqLevel].strength;
    const opening = this.hasPunishWindow(o);
    const blocking = o.state === S.BLOCK;
    const incoming = o.state === S.ATTACK && o.atkPhase === 0;
    const ranged = a.type === "projectile" || a.type === "lob" || a.type === "strike";
    const close = distance < 3.0;
    let value = 0;
    if (this.personaMode === "pressure") {
      if (a.type === "melee" || a.type === "phantom") value += 0.37;
      if (opening) value += 0.28;
    } else if (this.personaMode === "probe") {
      if (a.type === "mine" || a.type === "barrel" || a.type === "buff") value += 0.39;
      if (opening && a.type === "melee") value += 0.15;
    } else if (this.personaMode === "reset") {
      if ((a.type === "projectile" || a.type === "lob") && distance > 3) value += 0.32;
      if (a.type === "melee" && !opening) value -= 0.50;
    }
    switch (profile.role) {
      case "counter":      if (incoming && a.type === "buff") value += 0.55; break;
      case "duelist":     if (opening && a.type === "melee") value += 0.60; break;
      case "juggernaut":  if (blocking && a.guard > 25) value += 0.64; break;
      case "riposte":     if (incoming && a.mode === "counter") value += 0.95; break;
      case "artillery":   if (ranged && distance > 3.1) value += 0.49; break;
      case "support":     if (a.mode === "healing_water" && f.hp < f.maxHp * 0.68) value += 1.0; break;
      case "ambush":      if (opening && a.lunge > 0) value += 0.66; break;
      case "rush":        if (a.lunge > 0 && distance > 1.3) value += 0.55; break;
      case "skirmish":    if (opening && a.lunge > 0) value += 0.54; break;
      case "trapper":     if ((a.type === "mine" || a.type === "barrel") && !opening) value += 0.77; break;
      case "kickboxer":   if (opening && a.type === "melee") value += 0.65; break;
      case "controller":  if (a.mode === "static_field" && close) value += 1.0; break;
      case "sniper":      if (ranged && distance > 4.0) value += 0.58; break;
      case "executioner": if (opening && a.type === "melee") value += 0.67; break;
      case "glaive":      if (f.clashMomentum >= 2 && opening) value += 0.60; break;
      case "grappler":    if (a.style === "chain_predator_hook" && distance > 2.0 &&
          distance < 4.4 && !blocking) value += 1.15; break;
      case "bruiser":     if (f.nesaCCharges > 0 && opening && close &&
          a.style === "nesa_heart_slam") value += 0.78; break;
    }
    // Most V ultimates are held for visible punish/guard-break opportunities.
    // Buffs (especially actual healing) are exempt; V is *never* unlocked here.
    if (key === "v" && a.type !== "buff" && !opening &&
        o.state !== S.HITSTUN && o.state !== S.STAGGER) {
      value -= profile.vReserve * 2.7;
      if (this.personaMode === "reset") value -= 0.42;
    }
    return value * strength;
  }

private tacticalFootwork(f: Fighter, o: Fighter, dt: number) {
  const style = FIGHT_STYLES[f.look.name.toLowerCase()];
  if (!style || f.isDown() || !f.onGround || f.state !== S.IDLE ||
      this.sideT > 0 || this.blockHold > 0 || this.blockWait >= 0 ||
      f.intent.dash.lengthSq() > 0.01) return;
  this.tacticsCd = Math.max(0, this.tacticsCd - dt);
  this.rangeOrbitCd = Math.max(0, this.rangeOrbitCd - dt);
  if (this.rangeOrbitCd <= 0) {
    this.rangeOrbitCd = rand(0.9, 1.9);
    if (Math.random() < 0.72) this.rangeOrbitSign *= -1;
  }
  const toward = o.root.position.clone().sub(f.root.position).setY(0);
  const distance = toward.length();
  if (distance < 0.05) return;
  toward.divideScalar(distance);
  const tangent = new THREE.Vector3(-toward.z, 0, toward.x);
  const punish = this.hasPunishWindow(o);
  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&
    o.atk?.type === "melee" && distance < o.atk.reach + 0.7;
  if (danger) { this.tacticsT = 0; return; }
  const band = this.effectiveRangeBand(f, o);
  const cdIntel = this.enemyCooldownRead(o);
  const persona = CHARACTER_PERSONALITY[f.look.name.toLowerCase()];
  const personaPower = CHARACTER_IQ[this.iqLevel].strength;
  // Follow a known opening modestly; keep ranged kits at ranged distance.
  const shift = THREE.MathUtils.clamp(cdIntel.pressure * (RANGED.has(f.kit) ? 0.26 : 0.48) -
    cdIntel.caution * (RANGED.has(f.kit) ? 0.28 : 0.43), -0.43, 0.48);
  const personalityShift = persona ? personaPower * (
    persona.spacing + (this.personaMode === "pressure" ? -0.30 :
      this.personaMode === "reset" ? 0.48 : this.personaMode === "probe" ? 0.14 : 0)) : 0;
  band.ideal = Math.max(1.05, band.ideal - shift + personalityShift);
  band.near = Math.max(0.88, band.near - shift + personalityShift);
  band.far = Math.max(band.near + 0.24, band.far - shift + personalityShift);
  // A threatened block can be baited, but not endlessly or beyond the arena edge.
  if (this.tacticsT <= 0 && this.tacticsCd <= 0 &&
      distance < band.far + 0.4 && !punish &&
      (o.state === S.BLOCK || (o.state === S.IDLE && distance < band.near)) &&
      Math.random() < dt * style.bait * (0.45 + this.p.block)) {
    this.tacticsT = rand(0.23, 0.44);
    this.tacticsDir = Math.random() < 0.5 ? -1 : 1;
    this.tacticsCd = rand(1.1, 2.8);
  }
  if (this.tacticsT > 0) {
    this.tacticsT = Math.max(0, this.tacticsT - dt);
    const bait = toward.clone().negate().multiplyScalar(0.6)
      .addScaledVector(tangent, this.tacticsDir * 0.8);
    f.intent.move.copy(this.theaterDirection(f, o, bait));
    return;
  }
  // Move in for an actual punish. Normal basic range remains authoritative.
  const basicReach = f.attacks.l1?.reach ?? 1.75;
  if (punish && distance > basicReach * 0.78 && distance < band.far + 1.5) {
    f.intent.move.copy(this.theaterDirection(f, o, toward));
    return;
  }
  if (distance > band.far) {
    // Stop at effective range. Sprint is still the normal distance-based AI
    // sprint; there is no teleport and the arena boundary is checked.
    f.intent.move.copy(this.theaterDirection(f, o, toward));
  } else if (distance < band.near) {
    // Backpedal/angle out when unnecessarily close, including long melee
    // weapons and chain fighters. Edge-aware steering chooses a safe orbit.
    const away = toward.clone().negate().addScaledVector(tangent, 0.32 * this.rangeOrbitSign);
    f.intent.move.copy(this.theaterDirection(f, o, away));
  } else {
    // Strafe near the chosen distance; avoid perpetual face-to-face rushing.
    const correction = THREE.MathUtils.clamp((distance - band.ideal) * 0.48, -0.26, 0.26);
    const orbit = tangent.clone().multiplyScalar(this.rangeOrbitSign)
      .addScaledVector(toward, correction);
    f.intent.move.copy(this.theaterDirection(f, o, orbit)).multiplyScalar(0.55);
  }
}

private hasPunishWindow(o: Fighter): boolean {
  return o.state === S.STAGGER || o.state === S.HITSTUN ||
    (o.state === S.ATTACK && o.atkPhase === 2 && !!o.atk &&
      o.stateT < o.atk.wind + o.atk.active + o.atk.recover);
}

/** Score the real equipped skills by state and fighter identity.
 * Each move still uses Fighter.readSkill, normal cooldowns and hit detection. */
private personalizedSkill(f: Fighter, o: Fighter, distance: number): string | null {
  const id = f.look.name.toLowerCase();
  const profile = FIGHT_STYLES[id];
  if (!profile || (id === "veyr" && f.bloodFestivalT > 0)) return null;
  const punish = this.hasPunishWindow(o);
  const attackComing = o.state === S.ATTACK && o.atkPhase === 0;
  const close = distance < 2.65;
  const blocking = o.state === S.BLOCK;
  const scored: { key: string; points: number }[] = [];
  for (const key of ["z", "x", "c", ...(f.bonusSkillUnlocked ? ["v"] : [])]) {
    const a = f.attacks[key];
    if (!a || (f.cooldowns[key] ?? 1) > 0) continue;
    // Nesa's 3 charges follow the Pink Heart Smash skill on any equipped key.
    if (id === "nesa" && a.style === "nesa_heart_slam" && f.nesaCCharges <= 0) continue;
    let viable = true;
    let points = key === "v" ? 1.55 : profile.skillBias[key === "z" ? 0 : key === "x" ? 1 : 2];
    if (a.type === "melee" || a.type === "phantom") {
      viable = a.name === "Upsie Daisie"
        ? distance <= Math.min(3.35, a.reach + 0.72) && f.onGround
        : distance < a.reach + Math.max(0.85, a.lunge * 0.19);
      if (punish) points += 1.2;
      if (blocking && a.guard > 24) points += 0.4;
    } else if (a.type === "strike") {
      viable = a.at !== "self" || distance < a.radius + 0.40;
      if (punish) points += 0.85;
    } else if (a.type === "projectile" || a.type === "lob") {
      viable = distance < (a.type === "lob" ? 9 : 11);
      if (distance > 3.5) points += 0.45;
    } else if (a.type === "snow_puppet") {
      // Persistent summons have their own range; no fabricated melee reach.
      viable = id !== "roxy" ||
        (a.style === "bird" ? distance >= 2.6 && distance < 9.4 :
          !o.status.has("freeze") && o.status.freezeImmunityRemaining() <= 0 && distance < 7.8);
    } else if (a.type === "buff") {
      viable = a.mode === "frost_aegis" ?
        (f.frostShieldCharges <= 0 || f.frostShieldT <= 0) &&
        (f.hp < f.maxHp * 0.80 || (attackComing && distance < 6.5)) :
        a.mode === "counter" || a.mode === "blood_feint"
        ? attackComing && close
        : a.mode === "ward" ? close || f.hp < f.maxHp * 0.55
        : a.mode === "blood_festival" ? distance < 3.4
        : a.mode === "healing_water" ? f.hp < f.maxHp * 0.82
        : a.mode === "static_field" ? distance < a.radius + 0.4
        : f.hp < f.maxHp * 0.72;
    } else if (a.type === "blink") {
      viable = a.mode === "back" ? (close || attackComing) : distance < 5.5;
    } else if (a.type === "mine") viable = distance < 4.6;
    else if (a.type === "barrel") viable = !f.barrelOut && distance < 6.5;
    if (!viable) continue;
    // Actual roster-specific choices, not a skill randomly selected by key.
    const name = a.name;
    switch (id) {
      case "aster":
        if (name === "Shield Bash") points += close && (blocking || attackComing) ? 2.3 : 0.2;
        if (name === "Rising Slash") points += punish && close ? 1.2 : 0;
        break;
      case "vesper":
        if (name === "Rising Slash") points += punish && close ? 2.0 : 0.4;
        if (name === "Shield Bash" && blocking) points += 1.1;
        break;
      case "garrick":
        if (name === "Iron Tempest") points += close && punish ? 2.0 : 0.4;
        if (name === "Titan Cleave") points += punish && distance < 3.1 ? 2.4 : 0;
        if (name === "Ground Slam" && close) points += 1.2;
        break;
      case "kaede":
        if (name === "Counter Stance") points += attackComing && close ? 2.7 : 0;
        if (name === "Thousand Cuts") points += punish && close ? 1.8 : 0;
        break;
      case "ember":
        if (name === "Flame Burst") points += close ? 2.6 : -0.7;
        if (name === "Fireball Volley" && distance > 3) points += 1.1;
        if (name === "Meteor" && punish) points += 1.1;
        break;
      case "zenith":
        if (name === "Rail Spear") points += distance > 3.0 && !f.zenithSpearOut ? 2.3 : -1.0;
        if (name === "Phantom Spear Barrage") points += punish && close ? 2.3 : 0.2;
        if (name === "Magnetic Dominion") points += f.zenithSpearOut ? 2.5 : distance < 4.5 ? 1.5 : 0.0;
        if (name === "Sovereign Arsenal") points += punish && distance < 7.5 ? 1.8 : -0.1;
        break;
      case "roxy":
        if (a.mode === "frost_aegis") points += attackComing ? 3.0 : 0.2;
        if (name === "Frost Marionette") points += punish ? 2.0 : 1.2;
        if (name === "Glacier Meteor") points += o.status.has("freeze") ? 3.2 : punish ? 2.0 : 0;
        if (name === "Frostwing Choir") points += distance > 3.2 && !attackComing ? 1.8 : 0;
        break;
      case "marina":
        if (name === "Bubble Ward" && attackComing) points += 3.0;
        if (name === "Tidal Ring" && close) points += 2.0;
        if (name === "Ocean Requiem" && punish) points += 1.2;
        if (name === "Healing Water") points += f.hp < f.maxHp * 0.68 ? 3.2 : f.hp < f.maxHp * 0.86 ? 1.4 : -2.5;
        break;
      case "nyx":
        if (name === "Smoke Step" && (blocking || attackComing)) points += 2.1;
        if (name === "Phantom Rush" && punish) points += 2.6;
        break;
      case "rook":
        if (name === "Rush" && distance > 1.8) points += 1.8;
        if (name === "Meteor Fist" && close && punish) points += 2.4;
        if (name === "Shockwave Punch" && distance > 2.8) points += 1.8;
        break;
      case "gale":
        if (name === "Wind Step" && distance > 2.2) points += 2.0;
        if (name === "Tornado Rise" && close && punish) points += 2.1;
        break;
      case "bob":
        if (a.type === "mine" && distance < 4.1) points += 2.0;
        if (a.type === "barrel" && !f.barrelOut) points += 1.5;
        if (name === "Paralyze Bomb" && attackComing) points += 1.7;
        break;
      case "kira":
        if (name === "Cyclone Kick" && close) points += punish ? 2.3 : 0.75;
        if (name === "Crescent Gale") points += distance > 2.5 ? 2.1 : -0.45;
        if (name === "Phantom Step") points += punish && distance < 4.6 ? 2.7 : 0.35;
        break;
      case "raven":
        if (name === "Blink") points += close || attackComing ? 3.1 : -0.8;
        if (name === "Chain Lightning") points += distance > 2.0 && distance < 9.0 ? 1.7 : 0;
        if (name === "Thunderstorm") points += punish ? 2.0 : 0.35;
        if (name === "Static Field") points += close && (attackComing || punish) ? 3.0 : close ? 1.4 : -1;
        break;
      case "ash":
        if (name === "Leap Back") points += close || attackComing ? 3.0 : -0.4;
        if (name === "Hunter's Snare") points += !punish && distance > 2.7 ? 1.8 : 0.3;
        if (name === "Arrow Rain") points += punish && distance > 2.2 ? 2.2 : 0.3;
        break;
      case "veyr":
        if (name === "Death Feint") points += attackComing && close ? 3.4 : -0.6;
        if (name === "Blood Festival") points += close && (f.hp < f.maxHp * 0.75 || punish) ? 2.6 : 0.35;
        if (name === "Crimson Execution") points += distance > 2.3 ? 1.45 : 0.2;
        break;
      case "zarek":
        if (name === "Arc Flash") points += distance > 2.4 && distance < 9.5 ? 2.6 : -0.9;
        if (name === "Serpent Wheel") points += blocking || close ? 1.7 : 0;
        if (name === "Phantom Spiral") points += punish ? 2.5 : 0.5;
        if (name === "Infinite Crescent") points += punish || f.clashMomentum >= 3 ? 2.6 : 0.25;
        break;
      case "kaizen":
        // Hook catches exposed opponents just outside the five-hit sword string.
        if (name === "Predator's Hook") {
          if (blocking || distance < 1.45 || distance > 4.5) viable = false;
          points += !attackComing && distance > 2.45 && !blocking ? 2.25 : 0.25;
        }
        // A death spiral is strongest against recoveries, not at maximum range.
        if (name === "Thousand Cuts: Death Spiral") {
          if (distance > 3.65) viable = false;
          points += punish && distance < 3.2 ? 2.5 : close ? 0.8 : 0;
        }
        if (name === "Razor Cyclone") points += blocking || (close && punish) ? 1.95 : 0.30;
        if (name === "Serpent Bind") points += !blocking && punish && distance < 3.1 ? 2.45 : 0.25;
        break;
      case "nesa":
        // Favor the closing kick against ranged enemies, but it must still land.
        if (name === "Upsie Daisie") {
          if (distance > 3.35 || !f.onGround) viable = false;
          points += distance > 2.20 && distance < 3.25 ? 2.65 :
            attackComing && close ? 1.8 : 0.25;
        }
        // Spend a stored heart charge on a near, punishable target—not empty air.
        if (name === "Pink Heart Smash") {
          // True hit zone is in front of Nesa, centered 2.05m ahead, radius 2.72m.
          const heading = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
          const aim = o.root.position.clone().sub(f.root.position).setY(0);
          const heartCenter = f.root.position.clone().addScaledVector(heading, 2.05).setY(0);
          if (aim.dot(heading) <= 0.12 || o.root.position.clone().setY(0).distanceTo(heartCenter) > 2.72 + o.radius * 0.5) viable = false;
          points += punish || blocking ? 2.4 : distance < 3.65 ? 1.0 : 0.0;
          if (f.nesaCCharges === 1 && !punish) points -= 0.7;
        }
        if (name === "Side Swipe") points += close && blocking ? 2.0 : punish ? 1.7 : 0.1;
        // V is a defensive vertical parry now: cast against a real incoming attack,
        // never waste the giant-hammer setup on an idle opponent.
        if (name === "Heartbreaker High Striker") {
          const threatening = o.state === S.ATTACK && o.atkPhase <= 1 && !!o.atk &&
            (!o.atk.no_parry || o.isContinuousComboActive());
          if (!threatening || distance > 3.45 || distance < 0.2) viable = false;
          points += threatening && distance < 2.95 ? 4.5 : 0.0;
        }
        break;
    }
    if (!viable) continue; // real ability limits, including character-specific checks
    points += this.personalitySkillScore(f, o, key, distance);
    // The AI must occasionally choose another ability instead of being scripted.
    points += rand(-0.55, 0.55);
    scored.push({ key, points });
  }
  scored.sort((a, b) => b.points - a.points);
  return scored.length && scored[0].points >= 0.6 ? scored[0].key : null;
}

  private trySkill(f: Fighter, key: string, force = false) {
    if (f.cooldowns[key] > 0) return false;
    if (!force && Math.random() > 0.5) return false;
    f.intent.skill = key;
    return true;
  }

private offense(f: Fighter, o: Fighter, dt: number) {
  if (f.state !== S.IDLE || this.queue.length || this.hold > 0 || this.blockHold > 0 ||
      this.comboParryTarget > this.threats.now()) return;
  const distance = f.root.position.distanceTo(o.root.position);
  if (f.guard <= f.maxGuard * 0.32 && f.onGround && f.attacks.l1?.type === "melee" &&
    o.state === S.ATTACK && o.atk?.type === "melee" && o.atkPhase === 0 &&
    distance < f.attacks.l1.reach + 0.35) {
    this.queue.push([0, 0.06]);
    return;
  }
  if (f.stage && Math.abs(o.root.position.y - f.root.position.y) > 1.4 && !RANGED.has(f.kit)) return;
  const id = f.look.name.toLowerCase();
  const style = FIGHT_STYLES[id];
  const reach = style ? (RANGED.has(f.kit) ? 9 : style.range + 0.24)
    : RANGED.has(f.kit) ? 9 : f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks"
      ? 1.7 : f.kit === "greatsword" ? 2.3 : f.kit === "glaive" ? 2.1 : 1.9;
  const punish = this.hasPunishWindow(o);
  const blocked = o.state === S.BLOCK;
  const cdIntel = this.enemyCooldownRead(o);
  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&
    o.atk?.type === "melee" && distance < o.atk.reach + 0.65;
  const tempo = CHARACTER_IQ[this.iqLevel].strength *
    (this.personaMode === "pressure" ? 0.19 :
      this.personaMode === "reset" ? -0.17 : 0);
  this.skillCd -= dt * (1 + cdIntel.pressure * 0.38 + tempo);
  if (this.skillCd <= 0) {
    this.skillCd = rand(this.p.skill[0], this.p.skill[1]) *
      (1 - cdIntel.pressure * 0.22 + cdIntel.caution * 0.22);
    // Festival disables all Veyr skills until it expires; pressure with basics.
    const skill = this.personalizedSkill(f, o, distance);
    if (id !== "zenith" && skill && (punish || Math.random() < 0.80) && this.trySkill(f, skill, true)) return;
  }
  if (distance > reach) return;
  if (danger && !punish && id !== "zarek" && id !== "aster" && Math.random() < 0.80) return;
  // Near predicted enemy skill return, favor movement/defense over a risky commit.
  if (cdIntel.caution > 0.43 && !punish && o.state === S.IDLE &&
      Math.random() < cdIntel.caution * dt * 0.90) return;
  this.thinkCd -= dt * (1 + cdIntel.pressure * 0.30);
  if (this.thinkCd > 0) return;
  const fast = ["assassin", "knuckles", "kicks", "sickle", "glaive"].includes(f.kit);
  this.thinkCd = (fast ? rand(0.45, 0.96) : rand(0.7, 1.45)) * this.p.think;
  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge
  if (!punish) this.thinkCd *= 1 + cdIntel.caution * 0.24;
  let heavyChance = style ? Math.min(0.78, style.heavy +
      (punish ? 0.14 : 0) + (blocked ? 0.28 : 0))
    : o.state === S.STAGGER ? 0.5 : blocked ? 0.45 : 0.22;
  // Exploit learned cooldown openings; do not swing into an active cast.
  if (o.state !== S.ATTACK) heavyChance = THREE.MathUtils.clamp(
    heavyChance + cdIntel.pressure * 0.16 - cdIntel.caution * 0.16, 0.08, 0.80);
  // CHARACTER_STYLES_V1: role-based aggression changes input choices, not stats.
  heavyChance = THREE.MathUtils.clamp(heavyChance +
    CHARACTER_IQ[this.iqLevel].strength *
    (this.personaMode === "pressure" ? 0.09 :
      this.personaMode === "probe" ? -0.06 :
      this.personaMode === "reset" ? -0.13 : 0), 0.06, 0.80);
  // Veyr's festival specifically favors sustained lights and real guard pressure.
  const festival = id === "veyr" && f.bloodFestivalT > 0;
  if (!festival && Math.random() < heavyChance) {
    this.queue.push([0, HOLD_T + rand(0.24, 0.58)]);
    return;
  }
  const allLights = Object.keys(f.attacks).filter(k => /^l\d+$/.test(k));
  const limit = Math.max(1, Math.min(this.p.combo, allLights.length));
  let count = 1 + Math.floor(Math.random() * limit);
  if (style) {
    if (punish && Math.random() < style.combo) count = limit;
    else if (blocked && Math.random() < style.bait) count = 1;
    else if (Math.random() > style.combo) count = Math.min(count, 2);
  }
  if (festival) count = limit;
  // Normal/Hard/Master: launch one opener, then wait for an actual hit-confirm
  // before buffering more attacks. Easy occasionally keeps its old basic queue.
  if (this.iqLevel >= 1 && !festival && !RANGED.has(f.kit)) count = 1;
  // Each tap is a real input, and the Fighter checks real animation/cancel windows.
  for (let i = 0; i < count; i++)
    this.queue.push([i === 0 ? 0 : 0.14 + (fast ? 0 : 0.06), 0.06]);
}

}
