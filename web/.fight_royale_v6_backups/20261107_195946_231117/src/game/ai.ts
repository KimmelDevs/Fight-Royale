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
// Duel CPU. Presses the same virtual buttons a player would, with human-ish reaction times:
// reacts once per enemy swing / projectile / ground marker (block, parry, jump, sidestep),
// keeps its preferred range (ranged kits kite), and picks attacks and skills when idle.
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
  projectiles(): { target: any; pos: THREE.Vector3; vel: THREE.Vector3; id: number }[];
  strikes(): { target: any; land: number; id: number }[];
  /** Beam warnings appear only after Ember really begins gathering flames. */
  ignitions(f: Fighter): { caster: Fighter; land: number; id: number }[];
  /** Authoritative scheduled hit timestamps for an active continuous combo. */
  comboHits(attacker: Fighter): number[];
  /** Live enemy Ember fire patches; friendly flames are filtered out by Game. */
  firePatches(f: Fighter): { pos: THREE.Vector3; radius: number }[];
  now(): number;
}

const rand = (a: number, b: number) => a + Math.random() * (b - a);
const RANGED = new Set(["mage", "bow", "bomb"]);

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
};

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
  private antiAirCd = 0;
  private aiAirTap = false;
  private airSliceCd = 0;
  private skillCd = 2;
  private seenSwing = -1;
  private seenCharge = false;
  private seen = new Set<number>();
  // KAIZEN_PREDATOR_HOOK_V9: use the second X press instead of waiting for WASD.
  private chainDecisionT = 0;
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
  private seenClashSwing = -1;
  // NESA_DODGE_KIRA_AIR_3_V1: dodge Nesa's dangerous hammer swings rather than merely guarding them.
  private nesaThreatSerial = -1;
  private nesaEvadeChosen = false;
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
    const key = ["z", "x", "c"].find(k =>
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
        const preferred = this.theaterMode === "back" ?
          toward.clone().negate().addScaledVector(lateral, this.theaterSide * 0.3) :
          this.theaterMode === "circle" ? lateral.clone().multiplyScalar(this.theaterSide)
            .addScaledVector(toward, gap > style.range ? 0.27 : -0.15) : toward;
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
        else if (gap > 2.7 && gap < 6.3 && intent(0.83))
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
      a.name === "Upsie Daisie" ? gap <= Math.min(6.55, a.reach + a.lunge * 0.31) :
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

  private readySkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {
    this.readySkillPoll = Math.max(0, this.readySkillPoll - dt);
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
    const ready = ["z", "x", "c"].filter(k =>
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
    if (o.state !== S.ATTACK || !atk || !o.isContinuousComboActive()) {
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

  constructor(private threats: Threats, level: number) {
    this.p = PRESETS[Math.max(0, Math.min(level, PRESETS.length - 1))];
  }

  think(f: Fighter, dt: number) {
    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
    if (this.dodgeUnsafeContinuous(f, o, dt)) return;

    if (this.spinCounterResponse(f, o, dt)) return;
    if (this.counterThreatDefense(f, o, dt)) return;
    if (this.zarekShieldResponse(f, o, dt)) return;
    // During X binding, decide when to yank. AI can step nearer while the enemy is held.
    // During V, choose Z/X as before. Neither fighter casts ordinary skills in this state.
    if (f.chainBindTarget && f.chainBindT > 0) {
      this.chainDecisionT += dt;
      const target = f.chainBindTarget;
      if (f.chainBindKind === "x" && f.chainBindFinishT <= 0) {
        const move = target.root.position.clone().sub(f.root.position).setY(0);
        if (move.length() > 2.3) {
          move.normalize();
          f.intent.move.copy(f.stage ? new THREE.Vector3(Math.sign(move.x), 0, 0) : move);
        }
      }
      if (f.chainBindFinishT <= 0 && f.chainChoiceArmed && this.chainDecisionT >= 0.7) {
        f.intent.skill = f.chainBindKind === "x" ? "x" : Math.random() < 0.5 ? "z" : "x";
      }
      return;
    }
    this.chainDecisionT = 0;
    if (f.chainBoundBy && f.chainBoundBy.chainBindT > 0) return;
    // During Blood Festival Veyr chases with basics rather than blocking.
    if (this.veyrFestivalPressure(f, o, dt)) return;
    if (f.stage) { if (this.platform(f, o, dt)) return; }
    this.react(f, o);
    this.defendLongCombo(f, o);
    if (!f.stage) { this.dodge(f); this.position(f, o, dt); this.tacticalFootwork(f, o, dt); this.theaterFootwork(f, o, dt); }
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
    // Run after normal chase/strafe choices, so fire can veto a dangerous route.
    this.avoidFireGround(f);
    // NESA_DODGE_KIRA_AIR_3_V1: opponent dodges Nesa's real wind-up; leave
    // Nesa's own AI and every fighter's damage, guard and parry rules untouched.
    if (!f.stage && this.evadeNesa(f, o, dt)) return;
    this.antiAirCd = Math.max(0, this.antiAirCd - dt);
    this.airSliceCd = Math.max(0, this.airSliceCd - dt);
    this.aiAirTap = false;
    // A cautious jump-in occasionally replaces the old automatic uppercut launcher.
    // Airborne CPUs swing toward an opponent's current elevation, just like players.
    const flatGap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    if (!f.stage && f.onGround && f.state === S.IDLE && !RANGED.has(f.kit) &&
        this.antiAirCd <= 0 && flatGap > 0.65 && flatGap < 2.3 &&
        Math.random() < dt * 0.24) {
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
        Math.random() < dt * 7.0) {
      this.aiAirTap = true;
      this.airSliceCd = f.kit === "kicks" || f.kit === "assassin" ? rand(0.17, 0.24) : rand(0.55, 0.85);
      this.queue = [];
      this.hold = 0;
    }
    if (!this.aiAirTap && !this.readySkillOpportunity(f, o, dt) &&
        !this.theaterOffense(f, o)) this.offense(f, o, dt);
    if (f.kit === "wind" && !f.stage) this.airDive(f, o, dt);
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
    const giant = a!.style === "nesa_high_striker";
    const spin = a!.style === "nesa_spin" || a!.style === "nesa_air_spin";
    const heart = a!.style === "nesa_heart_slam";
    const area = giant || spin || heart || a!.type === "strike";
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
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
      this.nesaGiantEvadeChosen = Math.random() < Math.min(0.97, 0.38 + this.p.block * 0.88);
      const lead = 0.105 + this.p.react[1] * 0.28 + Math.random() * 0.025;
      this.nesaEvadeTrigger = Math.max(0.04, a!.wind - lead);
      this.nesaRetreatT = 0;
    }
    const t = o.stateT;
    const giantImpact = a!.wind + 1.90; // actual scheduled giant-smash callback
    const giantDue = giant && !this.nesaGiantEvadeUsed && this.nesaGiantEvadeChosen &&
      gap < bigRadius + 0.65 &&
      t >= giantImpact - (0.44 + this.p.react[1] * 0.15) &&
      t < giantImpact + 0.08;
    const firstDue = !this.nesaEvadeUsed && this.nesaEvadeChosen &&
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
  private airPlan = -1;
  private airDouble = false;

  /** Wind kit: now and then jump (sometimes double jump) and come down with an air skill. */
  private airDive(f: Fighter, o: Fighter, dt: number) {
    const ready = ["z", "x", "c"].filter((k) => f.attacks[k + "_air"] && f.cooldowns[k] <= 0);
    if (f.onGround) {
      this.airPlan = -1;
      const dist = f.root.position.distanceTo(o.root.position);
      if (f.state === S.IDLE && ready.length && dist < 6 && Math.random() < dt * 0.5) {
        f.intent.jump = true;
        this.airPlan = 0.3 + Math.random() * 0.25;
        this.airDouble = Math.random() < 0.5;
      }
      return;
    }
    if (this.airPlan < 0) return;
    this.airPlan -= dt;
    if (this.airDouble && this.airPlan < 0.15 && f.velY < 2) { f.intent.jump = true; this.airDouble = false; this.airPlan += 0.3; }
    if (this.airPlan <= 0 && ready.length) {
      f.intent.skill = ready[Math.floor(Math.random() * ready.length)];
      this.airPlan = -1;
    }
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
      if (f.kit === "glaive" && f.onGround && f.state === S.IDLE &&
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
      else if (r < this.p.parry + bc + 0.15) this.trySkill(f, "z", true);
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

  /** Sometimes contest an incoming shot with a REAL light swing. Collision is still
   * decided by Game's shared weapon-vs-projectile hitbox, not by this AI prediction. */
  private tryProjectileClash(f: Fighter, pr: ReturnType<Threats["projectiles"]>[number]): boolean {
    const a = f.attacks.l1;
    if (pr.target !== f || f.state !== S.IDLE || !f.onGround || a?.type !== "melee" ||
        f.atkLock > 0 || this.queue.length > 0 || this.hold > 0 ||
        this.blockHold > 0 || this.blockWait >= 0) return false;
    const speedSq = pr.vel.lengthSq();
    if (speedSq < 4) return false;
    // Predict where the shot crosses the blade arc during light attack's active frames.
    const rel = pr.pos.clone().sub(f.chest());
    if (rel.dot(pr.vel) >= 0) return false; // flying away
    const t = THREE.MathUtils.clamp(-rel.dot(pr.vel) / speedSq,
      a.wind + 0.025, a.wind + a.active);
    if (t > 0.65) return false;
    const intercept = pr.pos.clone().addScaledVector(pr.vel, t).sub(f.chest());
    if (Math.abs(intercept.y) > 1.05) return false;
    intercept.y = 0;
    const dist = intercept.length();
    if (dist > a.reach + 0.3) return false;
    const forward = new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    if (dist > 0.65 && intercept.dot(forward) / Math.max(0.001, dist) < 0.18) return false;
    // Easy AI seldom reacts; stronger opponents favor a cinematic blade clash.
    if (Math.random() > Math.min(0.78, 0.14 + this.p.block * 0.95)) return false;
    this.queue = [[0, 0.08]];
    this.hold = 0;
    return true;
  }

  private dodge(f: Fighter) {
    for (const p of this.threats.projectiles()) {
      if (p.target !== f || this.seen.has(p.id)) continue;
      if (this.tryProjectileClash(f, p)) { this.seen.add(p.id); continue; }
      this.seen.add(p.id);
      const eta = f.chest().distanceTo(p.pos) / Math.max(p.vel.length(), 0.1);
      const r = Math.random();
      if (r < this.p.jump && f.onGround) this.jumpWait = Math.max(eta - 0.28, 0);
      else if (r < this.p.jump + this.p.block) this.schedule(Math.min(Math.max(eta - 0.2, 0), this.p.react[1]), eta + 0.2);
    }
    for (const m of this.threats.strikes()) {
      if (m.target !== f || this.seen.has(m.id)) continue;
      this.seen.add(m.id);
      const eta = m.land - this.threats.now();
      if (Math.random() < 0.3 + this.p.jump) { this.sideT = Math.min(Math.max(eta, 0.3), 0.8); this.sideSign = Math.random() < 0.5 ? 1 : -1; }
      else if (Math.random() < 0.5) this.jumpWait = Math.max(eta - 0.3, 0);
    }
    if (this.seen.size > 300) this.seen.clear();
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

/** Choose footwork without teleporting or exceeding the arena movement limits.
 * Leave projectile/hazard dodge decisions alone; terrain avoidance runs after this. */
private tacticalFootwork(f: Fighter, o: Fighter, dt: number) {
  const style = FIGHT_STYLES[f.look.name.toLowerCase()];
  if (!style || f.isDown() || !f.onGround || f.state !== S.IDLE ||
      this.sideT > 0 || this.blockHold > 0 || this.blockWait >= 0) return;
  this.tacticsCd = Math.max(0, this.tacticsCd - dt);
  const toward = o.root.position.clone().sub(f.root.position).setY(0);
  const distance = toward.length();
  if (distance < 0.05) return;
  toward.divideScalar(distance);
  const tangent = new THREE.Vector3(-toward.z, 0, toward.x);
  const punish = this.hasPunishWindow(o);
  // Never perform a deliberate bait while a real melee strike is almost active.
  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&
    o.atk?.type === "melee" && distance < o.atk.reach + 0.7;
  if (danger) { this.tacticsT = 0; return; }
  if (this.tacticsT <= 0 && this.tacticsCd <= 0 &&
      distance < style.range + 0.75 && !punish &&
      (o.state === S.BLOCK || (o.state === S.IDLE && distance < style.range - 0.28)) &&
      Math.random() < dt * style.bait * (0.45 + this.p.block)) {
    this.tacticsT = rand(0.23, 0.44);
    this.tacticsDir = Math.random() < 0.5 ? -1 : 1;
    this.tacticsCd = rand(1.1, 2.8);
  }
  if (this.tacticsT > 0) {
    this.tacticsT -= dt;
    const retreat = toward.clone().negate().multiplyScalar(0.65)
      .addScaledVector(tangent, this.tacticsDir * 0.76).normalize();
    const test = f.root.position.clone().addScaledVector(retreat, 1.1);
    // At the arena edge, replace backward drifting with a sideways orbit.
    if (Math.hypot(test.x, test.z) > f.arenaRadius - 0.55) {
      const side1 = tangent.clone().multiplyScalar(this.tacticsDir);
      const side2 = side1.clone().negate();
      const safe = [side1, side2].sort((a, b) =>
        f.root.position.clone().addScaledVector(a, 1.1).lengthSq() -
        f.root.position.clone().addScaledVector(b, 1.1).lengthSq());
      f.intent.move.copy(safe[0]);
    } else f.intent.move.copy(retreat);
    return;
  }
  // Close deliberately on a whiff rather than attacking from beyond skill range.
  if (punish && distance > style.range * 0.64 && distance < style.range + 2.2) {
    f.intent.move.copy(toward);
    return;
  }
  // Faster melee personalities actively manage spacing; ranged kits retain kiting AI.
  if (!RANGED.has(f.kit) && f.kit !== "bomb") {
    if (distance > style.range + 0.35) f.intent.move.copy(toward);
    else if (distance < style.range - 0.45 && style.bait > 0.42 && o.state === S.BLOCK)
      f.intent.move.copy(tangent).multiplyScalar(this.tacticsDir * 0.7);
  } else if (distance < style.range - 1.15 && !punish) {
    const retreat = toward.clone().negate();
    if (f.root.position.clone().addScaledVector(retreat, 0.9).length() < f.arenaRadius - 0.65)
      f.intent.move.copy(retreat);
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
  for (const key of ["z", "x", "c"]) {
    const a = f.attacks[key];
    if (!a || (f.cooldowns[key] ?? 1) > 0) continue;
    // Nesa's 3 charges follow the Pink Heart Smash skill on any equipped key.
    if (id === "nesa" && a.style === "nesa_heart_slam" && f.nesaCCharges <= 0) continue;
    let viable = true;
    let points = profile.skillBias[key === "z" ? 0 : key === "x" ? 1 : 2];
    if (a.type === "melee" || a.type === "phantom") {
      viable = distance < a.reach + Math.max(0.85, a.lunge * 0.19);
      if (punish) points += 1.2;
      if (blocking && a.guard > 24) points += 0.4;
    } else if (a.type === "strike") {
      viable = a.at !== "self" || distance < a.radius + 0.40;
      if (punish) points += 0.85;
    } else if (a.type === "projectile" || a.type === "lob") {
      viable = distance < (a.type === "lob" ? 9 : 11);
      if (distance > 3.5) points += 0.45;
    } else if (a.type === "buff") {
      viable = a.mode === "counter" || a.mode === "blood_feint"
        ? attackComing && close
        : a.mode === "ward" ? close || f.hp < f.maxHp * 0.55
        : a.mode === "blood_festival" ? distance < 3.4
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
      case "marina":
        if (name === "Bubble Ward" && attackComing) points += 3.0;
        if (name === "Tidal Ring" && close) points += 2.0;
        if (name === "Ocean Requiem" && punish) points += 1.2;
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
          if (distance > 5.65) viable = false;
          points += distance > 2.20 && distance < 5.15 ? 2.65 :
            attackComing && close ? 1.8 : 0.25;
        }
        // Spend a stored heart charge on a near, punishable target—not empty air.
        if (name === "Pink Heart Smash") {
          if (distance > 2.82) viable = false;
          points += punish || blocking ? 2.4 : distance < 2.10 ? 1.0 : 0.0;
          if (f.nesaCCharges === 1 && !punish) points -= 0.7;
        }
        if (name === "Side Swipe") points += close && blocking ? 2.0 : punish ? 1.7 : 0.1;
        // Large second bonk needs a target likely to stay in radius.
        if (name === "Heartbreaker High Striker") {
          if (distance > 3.0) viable = false;
          points += punish && distance < 2.4 ? 2.75 : 0.0;
        }
        break;
    }
    if (!viable) continue; // real ability limits, including character-specific checks
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
  const danger = o.state === S.ATTACK && o.atkPhase === 0 &&
    o.atk?.type === "melee" && distance < o.atk.reach + 0.65;
  this.skillCd -= dt;
  if (this.skillCd <= 0) {
    this.skillCd = rand(this.p.skill[0], this.p.skill[1]);
    // Festival disables all Veyr skills until it expires; pressure with basics.
    const skill = this.personalizedSkill(f, o, distance);
    if (skill && (punish || Math.random() < 0.80) && this.trySkill(f, skill, true)) return;
  }
  if (distance > reach) return;
  if (danger && !punish && id !== "zarek" && id !== "aster" && Math.random() < 0.80) return;
  this.thinkCd -= dt;
  if (this.thinkCd > 0) return;
  const fast = ["assassin", "knuckles", "kicks", "sickle", "glaive"].includes(f.kit);
  this.thinkCd = (fast ? rand(0.45, 0.96) : rand(0.7, 1.45)) * this.p.think;
  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge
  const heavyChance = style ? Math.min(0.78, style.heavy +
      (punish ? 0.14 : 0) + (blocked ? 0.28 : 0))
    : o.state === S.STAGGER ? 0.5 : blocked ? 0.45 : 0.22;
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
  // Each tap is a real input, and the Fighter checks real animation/cancel windows.
  for (let i = 0; i < count; i++)
    this.queue.push([i === 0 ? 0 : 0.14 + (fast ? 0 : 0.06), 0.06]);
}

}
