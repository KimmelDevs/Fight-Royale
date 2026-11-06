// CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06
// Playable fighter. A brain (local input, AI, or a remote player's inputs) fills `intent`
// every frame:
//   attack tap (release < HOLD_T)  -> normal attack, chains into the kit's combo
//   attack hold, then release      -> charged attack (stronger the longer it charged)
//   block hold                     -> block; the first parryWindow seconds parry
//   jump                           -> jump (dodges ground strikes and low projectiles)
//   skill "z" / "x" / "c"          -> skill, if off cooldown
// The arena gets `onSwing` when an attack reaches its active frame and resolves its effect.
// On network clients the fighter is a puppet: it only mirrors state sent by the host.
// With a `stage` set (duel / team modes) it plays as a side-view platform fighter: moves on
// the X axis, double jumps, lands on platforms, and takes damage % instead of losing HP. The
// higher the %, the farther hits launch it; flying past the blast zone costs a stock.
import { StatusSet, type StatusKind } from "./status";
import * as THREE from "three";
import { FighterModel } from "./model";
import { Trail } from "./fx";
import * as Kits from "./kits";
import type { Attack, Pose } from "./kits";
import type { Look } from "./roster";
import { emblemBonus, DEFAULT_LOADOUT } from "./economy";

/** Long, individually-timed attacks keep their choreography after parries/clashes.
 * Basic light chains and single-hit skills intentionally keep ordinary reactions. */
export const CONTINUOUS_STYLES = new Set([
  "sickle_carrion", "glaive_cyclone", "glaive_serpent", "glaive_phantom", "glaive_infinite",
  "chain_razor_cyclone", "chain_death_spiral", "chain_carousel", "chain_return",
  "cyclone_kick_v2", "iron_tempest", "phantom_rush",
]);

export enum S { IDLE, ATTACK, CHARGE, BLOCK, HITSTUN, STAGGER, KO, WIN }

export const HOLD_T = 0.22;
export const CHARGE_MAX = 0.9;
const ENGAGE = 1.45;
const MIN_DIST = 0.95;
const GRAVITY = 22;
const GUARD_REGEN = 30;

/** One-way platforms (solid = main stage: can't drop through, has side walls). */
export interface Plat { x0: number; x1: number; y: number; solid: boolean }
export interface Stage { plats: Plat[]; blast: { l: number; r: number; b: number; t: number }; respawn: THREE.Vector3 }
export const STOCKS = 3;
/** After a ranged combo's last hit, normal attacks rest this long (per kit). */
export const RANGED_COMBO_REST: Record<string, number> = { mage: 1.2, bow: 1.3, bomb: 1.2 };
/** Berserk (rage buff) damage multiplier. */
export const RAGE_MULT = 1.2;
/** Re-stuns within this window are shortened (diminishing returns). */
const STUN_DR_WINDOW = 3;
const STUN_DR = 0.6;
const PCT_PER_DMG = 0.07;

export interface Intent { attack: boolean; block: boolean; jump: boolean; skill: string; skillHeld?: string; skillMove?: THREE.Vector3; move: THREE.Vector3; dash: THREE.Vector3 }
export const DASH_CD = 3;
const DASH_T = 0.3;
const DASH_SPEED = 14;
export interface Brain { think(f: Fighter, dt: number): void }

/** Anything that can be hit: fighters and mobs. */
export interface Entity {
  id: number; kind: string; team: number; root: THREE.Group;
  hp: number; maxHp: number; radius: number; lastDamage: number; lastCrit: boolean;
  isDown(): boolean; chest(): THREE.Vector3; airborne(): boolean;
  receiveHit(attacker: Entity | null, a: Attack, power: number): string;
  update(dt: number): void;
}

export class Fighter implements Entity {
  id = 0;
  kind = "fighter";
  team = 0;
  root = new THREE.Group();
  look: Look;
  charIndex: number;
  kit: string;
  model: FighterModel;
  trail: Trail;
  brain: Brain | null = null;
  opponent: Entity | null = null;
  autoApproach = false;
  viewBias = 0;
  arenaRadius = 7;
  puppet = false;
  /** Network peer id that controls this fighter ("" = host / local). */
  owner = "";

  intent: Intent = { attack: false, block: false, jump: false, skill: "", move: new THREE.Vector3(), dash: new THREE.Vector3() };
  dashCd = 0;
  private dashT = 0;
  private dashDir = new THREE.Vector3();
  onDash: (f: Fighter) => void = () => {};

  maxHp: number; maxGuard: number; moveSpeed: number; walkSpeed: number; parryWindow: number; jumpV: number;
  attacks: Record<string, Attack>;
  poses: Record<string, Pose>;
  radius = 0.35;

  state = S.IDLE;
  stateT = 0;
  hp: number;
  guard: number;
  atk: Attack | null = null;
  atkId = "";
  atkPhase = 0;
  atkPower = 1;
  swingSerial = 0;
  lastDamage = 0;
  lastCrit = false;
  cooldowns: Record<string, number> = { z: 0, x: 0, c: 0 };
  /** After a ranged combo's last hit, normal attacks rest this long (stops shot spam). */
  atkLock = 0;
  private clock = 0;
  private stunSrc = "";
  private lastStunAt = -99;
  private stunChain = 0;
  onGround = true;
  velY = 0;
  wardT = 0;
  counterT = 0;
  invulnT = 0;

  // Survival perks.
  dmgMult = 1;
  cdMult = 1;
  critChance = 0.2;
  lifesteal = 0;

  poseName = "idle";
  poseSpeed = 14;

  onSwing: (f: Fighter) => void = () => {};
  onKo: (f: Fighter) => void = () => {};
  /** Status effects (burn, poison, paralyze...). Damage-over-time ticks queue in `dots` for the game. */
  status = new StatusSet();
  dots: { kind: StatusKind; dmg: number; src: unknown }[] = [];
  onLanded: (f: Fighter) => void = () => {};

  private stun = 0;
  private leapVel = new THREE.Vector3();
  private stunPose = "hit";
  private comboNext = "l1";
  private comboTimer = 0;
  private buffered = false;
  private atkPrev = false;
  /** SWORD_AND_CYCLONE_V1: sync Kira spin and sword torso follow-through. */
  private cycloneSpin = 0;
  private bladeSwingYaw = 0;
  /** Visual-only full-body turn for Garrick Iron Tempest (host-synced). */
  private tempestSpin = 0;
  // AIR_COMBAT_V1: launcher follow-up and one defensive air recovery per airtime.
  airChaseT = 0;
  private airChaseUsed = false;
  private airChaseTarget: Entity | null = null;
  private airChaseMoveT = 0;
  private airChaseDir = new THREE.Vector3();
  private airRecoverUsed = false;
  private airRecoverPrev = false;
  private airHoldT = 0;
  private airHeavyDone = false;
  // Space then Click within 0.22s still counts as a grounded anti-air chord.
  private airStartT = 99;
  private jumpPrev = false;
  private holding = false;
  private holdT = 0;
  private guardDelay = 0;
  /** Normal shield takes 0.10s to rise; the first re-raise after a successful parry is 0.05s. */
  shieldRaise = 0.10;
  nextShieldFast = false;
  /** Only ongoing multi-hit specials accumulate these parry/clash penalties. */
  comboDamageMult = 1;
  comboPauseT = 0;
  isContinuousComboActive() {
    return this.state === S.ATTACK && !!this.atk &&
      (CONTINUOUS_STYLES.has(this.atk.style) || (this.atk.type === "phantom" && this.atk.repeat > 1));
  }
  /** Returns false for ordinary single-hit attacks (their normal stagger is preserved). */
  onComboParried(): boolean {
    if (!this.isContinuousComboActive()) return false;
    this.comboDamageMult = Math.max(0.35, this.comboDamageMult * 0.90);
    this.comboPauseT += 0.20;
    this.model.recoil = Math.max(this.model.recoil, 0.30);
    return true;
  }
  private knock = 0;
  private netPos = new THREE.Vector3();
  private netRot = 0;

  // Platform-fighter state.
  stage: Stage | null = null;
  pct = 0;
  stocks = STOCKS;
  /** Off screen after a blast-zone KO, waiting to respawn. */
  out = false;
  vx = 0;
  facing = 1;
  lane = 0;
  onBlast: (f: Fighter) => void = () => {};
  private airJumps = 1;
  /** Arena double jump (wind kit): jumps used in the current air time. */
  private airJump = 0;
  /** Time left in the double-jump wind-ride pose. */
  private airJumpT = 0;
  onAirJump: (f: Fighter) => void = () => {};
  /** Bomber: a powder keg is out on the field (the skill becomes its trigger). */
  barrelOut = false;
  barrelPos = new THREE.Vector3();
  /** Pressing the keg's skill while it is out asks the arena to detonate it. */
  onTrigger: (f: Fighter) => void = () => {};
  /** Blood Hunter: steering recast and 0.30s feint window. */
  sickleOut = false;
  bloodFeintT = 0;
  clashMomentum = 0; // KAIZEN_BIND_ZAREK_COUNTER_V4: unlimited round clash count (legacy network field name).
  chainFuryT = 0; // legacy field retained for existing snapshots/weapon code.
  // KAIZEN_DIRECTIONAL_V3: direction is relative to facing at skill-press, never hard-coded WASD.
  chainSkillDir: "forward" | "backward" | "left" | "right" | "neutral" = "neutral";
  chainHookTarget: Entity | null = null;
  chainHookT = 0;
  /** Immobilizes both fighters until a new forward/back input or the 4 second timeout. */
  chainBindTarget: Fighter | null = null;
  chainBoundBy: Fighter | null = null;
  chainBindT = 0;
  chainBindKind: "x" | "v" | "" = "";
  chainChoiceArmed = false;
  // KAIZEN_BIND_FOLLOWUP_V7: after selecting Z/X, both remain bound until the action finishes.
  chainBindFinishT = 0;
  chainResolveDirection: "forward" | "backward" | "" = "";
  // KAIZEN_SERPENT_SLAM_V10: authoritative animation begins at the actual victim position.
  chainBindFinishDuration = 0;
  chainBindStartPos = new THREE.Vector3();
  onChainBindResolve: (f: Fighter, dir: "forward" | "backward", kind: "x" | "v") => void = () => {};
  bloodlust = 0;
  bloodFrenzyT = 0;
  /** Blood Festival: stun-immune, but damageable and all skills disabled until expiration. */
  bloodFestivalT = 0;
  onSickleRecast: (f: Fighter) => void = () => {};
  /** Super armor only while Rook is performing Meteor Fist (wind-up, leap, landing recovery). */
  private get meteorFistArmor(): boolean {
    return this.kit === "knuckles" && this.state === S.ATTACK && this.atk?.name === "Meteor Fist";
  }

  private ground: Plat | null = null;
  private dropT = 0;
  private respawnT = 0;
  private upPrev = false;
  private downPrev = false;
  private knockFrom = 0;

  /** Damage multiplier from Berserk, while rageT > 0. */
  rageT = 0;
  /** ASTER_EMBER_LATEST_20261106: 10-second empowered sword/shield form. */
  judgmentT = 0;

  /**
   * `loadout` picks which 3 of the kit's 4 skills sit on Z/X/C; `emblem` applies its stat bonus.
   */
  constructor(look: Look, charIndex: number, loadout: string[] = DEFAULT_LOADOUT, emblem?: { id: string; level: number }) {
    this.look = look;
    this.charIndex = charIndex;
    this.kit = look.kit;
    const st = Kits.STATS[this.kit];
    this.maxHp = st.hp; this.maxGuard = st.guard; this.moveSpeed = st.move; this.walkSpeed = st.walk;
    this.parryWindow = st.parry; this.jumpV = st.jump;
    this.hp = this.maxHp;
    this.guard = this.maxGuard;
    this.attacks = Kits.attacks(this.kit, look.element);
    const pool = { z: this.attacks.z, x: this.attacks.x, c: this.attacks.c, v: this.attacks.v } as Record<string, Attack>;
    const slots = loadout.length === 3 && new Set(loadout).size === 3 && loadout.every((k) => pool[k]) ? loadout : DEFAULT_LOADOUT;
    const airPool = { z: this.attacks.z_air, x: this.attacks.x_air, c: this.attacks.c_air, v: this.attacks.v_air } as Record<string, Attack | undefined>;
    ["z", "x", "c"].forEach((key, i) => {
      this.attacks[key] = pool[slots[i]];
      // The air version follows the skill wherever the loadout puts it.
      const air = airPool[slots[i]];
      if (air) this.attacks[key + "_air"] = air; else delete this.attacks[key + "_air"];
    });
    if (emblem) {
      const b = emblemBonus(emblem.id, emblem.level);
      this.maxHp *= 1 + b.hp;
      this.maxGuard *= 1 + b.guard;
      this.dmgMult *= 1 + b.dmg;
      this.critChance += b.crit;
      this.cdMult *= 1 - b.cd;
      this.moveSpeed *= 1 + b.speed;
    }
    this.poses = Kits.poses(this.kit, this.look.element);
    this.root.rotation.order = "YXZ";
    this.model = new FighterModel(look);
    this.root.add(this.model);
    this.trail = new Trail(this.model.bladeBase, this.model.bladeTip, look.glow);
  }

  isDown() { return this.state === S.KO; }
  chest() { return this.root.position.clone().add(new THREE.Vector3(0, 1.1, 0)); }
  airborne() { return this.stage ? !this.onGround : !this.onGround && this.root.position.y > 0.7; }
  /** Stick up / down (side view: the camera looks down -Z, so "up" is -Z on the stick). */
  private up() { return -this.intent.move.z > 0.5; }
  private down() { return -this.intent.move.z < -0.5; }

  update(dt: number) {
    if (this.puppet) { this.updatePuppet(dt); return; }
    const it = this.intent;
    it.attack = false; it.block = false; it.jump = false; it.skill = ""; it.skillHeld = "";
    it.skillMove?.set(0, 0, 0); it.move.set(0, 0, 0); it.dash.set(0, 0, 0);
    if (this.out) { this.waitRespawn(dt); return; }
    if (this.brain && this.state !== S.KO && this.state !== S.WIN) this.brain.think(this, dt);
    // AIR_COMBAT_V1: Right Click while hit-stunned in air = one escape per airtime.
    this.tryAirRecovery();
    // Ground and airborne blocks both work; perfect parry still uses its normal timing.
    // Escaping hitstun is handled separately, once per airtime.
    // A successful parry pauses a persistent combo for exactly 0.20 seconds;
    // its delayed arena hits are shifted by the same amount in Game.
    const advancing = this.state === S.ATTACK && this.comboPauseT > 0
      ? Math.max(0, dt - this.comboPauseT) : dt;
    this.comboPauseT = Math.max(0, this.comboPauseT - dt);
    this.stateT += advancing;
    for (const k in this.cooldowns) this.cooldowns[k] = Math.max(this.cooldowns[k] - dt, 0);
    this.atkLock = Math.max(this.atkLock - dt, 0);
    this.clock += dt;
    this.dashCd = Math.max(this.dashCd - dt, 0);
    this.dashT = Math.max(this.dashT - dt, 0);
    this.readDash();
    this.wardT = Math.max(this.wardT - dt, 0);
    this.rageT = Math.max(this.rageT - dt, 0);
    if (this.judgmentT > 0) {
      this.judgmentT = Math.max(0, this.judgmentT - dt);
      // Judgment lightning is harmless; the transformation itself costs 1.2% HP/s.
      this.hp = Math.max(1, this.hp - this.maxHp * 0.012 * dt);
    }
    this.chainFuryT = Math.max(this.chainFuryT - dt, 0);
    this.chainHookT = Math.max(0, this.chainHookT - dt);
    if (this.chainHookT === 0) this.chainHookTarget = null;
    this.counterT = Math.max(this.counterT - dt, 0);
    this.bloodFeintT = Math.max(this.bloodFeintT - dt, 0);
    // VEYR_BLOODLUST_CARRION_V7: drain the Frenzy meter evenly rather than snapping from 100 to 0.
    const frenzyWasActive = this.bloodFrenzyT > 0;
    this.bloodFrenzyT = Math.max(this.bloodFrenzyT - dt, 0);
    if (this.kit === "sickle" && frenzyWasActive)
      this.bloodlust = Math.min(100, Math.max(0, 100 * this.bloodFrenzyT / 5));
    this.bloodFestivalT = Math.max(this.bloodFestivalT - dt, 0);
    this.invulnT = Math.max(this.invulnT - dt, 0);
    this.airJumpT = Math.max(this.airJumpT - dt, 0);
    this.airChaseT = Math.max(this.airChaseT - dt, 0);
    this.airChaseMoveT = Math.max(this.airChaseMoveT - dt, 0);
    this.airStartT = Math.min(99, this.airStartT + dt);
    this.tickStatus(dt);
    if (this.chainBindTarget && (this.chainBindTarget.isDown() || this.state === S.KO))
      this.releaseChainBind();
    // KAIZEN_PREDATOR_HOOK_V9: X bind allows Kaizen to walk, but locks other attacks/skills.
    // X recast pulls the victim toward Kaizen; Serpent Bind (V) keeps Z/X throws.
    if (this.chainBindTarget && this.chainBindT > 0) {
      const hook = this.chainBindKind === "x";
      if (this.chainBindFinishT > 0) {
        this.intent.skill = "";
        this.chainBindFinishT = Math.max(0, this.chainBindFinishT - dt);
        this.chainBindT = this.chainBindFinishT;
        if (this.chainBindFinishT === 0) this.releaseChainBind();
      } else {
        this.chainBindT = Math.max(0, this.chainBindT - dt);
        const choice = this.intent.skill;
        if (!choice) this.chainChoiceArmed = true;
        else if (this.chainChoiceArmed && (hook ? choice === "x" : choice === "z" || choice === "x")) {
          const direction = hook || choice === "x" ? "backward" : "forward";
          const kind = this.chainBindKind as "x" | "v";
          this.chainChoiceArmed = false;
          this.chainResolveDirection = direction;
          // Serpent Bind: a full reel-in, lift, three-impact throw sequence.
          // X hook is still a short single yank, with free movement while bound.
          this.chainBindFinishT = hook ? 0.40 : 1.85;
          this.chainBindFinishDuration = this.chainBindFinishT;
          this.chainBindStartPos.copy(this.chainBindTarget.root.position);
          this.chainBindT = this.chainBindFinishT;
          this.intent.skill = ""; // recast is consumed, NEVER cast another ordinary X
          this.onChainBindResolve(this, direction, kind);
        }
        if (this.chainBindT === 0) this.releaseChainBind();
      }
    }
    const hookOwner = this.chainBindT > 0 && this.chainBindTarget !== null && this.chainBindKind === "x";
    const boundOwner = this.chainBoundBy && this.chainBoundBy.chainBindT > 0 ? this.chainBoundBy : null;
    if (hookOwner) {
      // Kaizen walks normally while the target is tethered, but can't cast, attack, dodge,
      // jump or parry for free. The model continues to draw a chain to the victim.
      this.intent.skill = ""; this.intent.attack = false;
      this.intent.block = false; this.intent.jump = false;
      this.vx = 0; this.knock = 0; this.dashT = 0;
      if (this.state !== S.IDLE) this.setState(S.IDLE);
      if (this.stage) { this.movePlat(dt); this.verticalPlat(dt); }
      else { this.move(dt); this.vertical(dt); }
      this.poseName = "cbh_s";
      this.model.chainPose = "cbh_s";
      this.model.chainBindTargetWorld = this.chainBindTarget!.chest();
      this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, 13);
      this.trail.update(dt);
      return;
    }
    // The bound opponent stays still until the recast. During the 0.4s pull, the
    // host smoothly draws them toward Kaizen (never moves Kaizen automatically).
    if (boundOwner && boundOwner.chainBindKind === "x") {
      this.vx = 0; this.velY = 0; this.knock = 0; this.dashT = 0;
      this.airChaseMoveT = 0;
      if (boundOwner.chainBindFinishT > 0) {
        const toward = boundOwner.root.position.clone().sub(this.root.position).setY(0);
        const dist = toward.length();
        const amount = Math.min(Math.max(0, dist - 1.25), 17 * dt);
        if (amount > 0.001) {
          this.root.position.addScaledVector(toward.multiplyScalar(1 / dist), amount);
          if (this.stage) {
            this.root.position.x = THREE.MathUtils.clamp(this.root.position.x,
              this.stage.blast.l + 1, this.stage.blast.r - 1);
          } else {
            const radial = Math.hypot(this.root.position.x, this.root.position.z);
            if (radial > this.arenaRadius) {
              this.root.position.x *= this.arenaRadius / radial;
              this.root.position.z *= this.arenaRadius / radial;
            }
          }
        }
      }
      this.model.walk = 0; this.trail.emitting = false;
      this.poseName = "hit";
      this.model.blend(this.poses.hit ?? this.poses.idle, dt, 13);
      this.trail.update(dt);
      return;
    }
    // KAIZEN_SERPENT_SLAM_V10: Keep the chain locked for the ENTIRE animation,
    // drive the victim through alternating slams, and freeze all regular controls.
    if (this.chainBindT > 0 || boundOwner) {
      this.vx = 0; this.velY = 0; this.knock = 0; this.dashT = 0;
      this.airChaseMoveT = 0; this.model.walk = 0; this.trail.emitting = false;
      this.intent.attack = false; this.intent.skill = ""; this.intent.jump = false;
      this.model.chainBindTargetWorld = this.chainBindTarget?.chest() ?? null;
      if (boundOwner && boundOwner.chainBindKind === "v" && boundOwner.chainBindFinishT > 0) {
        this.animateSerpentBound(boundOwner, dt);
      } else if (this.chainBindTarget && this.chainBindKind === "v" && this.chainBindFinishT > 0) {
        const t = this.chainBindFinishDuration - this.chainBindFinishT;
        this.poseName = t < 0.26 ? "cbh_s" : t < 0.59 ? "cbv_s" :
          t < 0.95 ? "cbx1_s" : t < 1.27 ? "cbx2_s" : "cbx3_s";
        this.model.chainPose = this.poseName;
        this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, 34);
      } else {
        this.poseName = this.kit === "chainblade" ? "cbv_s" : "hit";
        this.model.chainPose = this.poseName;
        this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, 16);
      }
      this.trail.update(dt);
      return;
    }
    this.model.chainBindTargetWorld = null;
    this.readAttack(dt);
    this.readJump();
    this.readSkill();

    switch (this.state) {
      case S.IDLE:
        this.comboTimer -= dt;
        if (this.comboTimer <= 0) this.comboNext = "l1";
        if (it.block) this.setState(S.BLOCK);
        break;
      case S.ATTACK: this.attackStep(); break;
      case S.CHARGE:
        if (it.block) { this.holding = false; this.setState(S.BLOCK); }
        else if (this.stateT >= CHARGE_MAX) { this.holding = false; this.startAttack("heavy"); }
        break;
      case S.BLOCK: if (!it.block) this.setState(S.IDLE); break;
      case S.HITSTUN:
      case S.STAGGER: if (this.stateT >= this.stun) this.setState(S.IDLE); break;
    }

    if (this.stage) { this.movePlat(dt); this.verticalPlat(dt); }
    else { this.move(dt); this.vertical(dt); }
    if (this.state !== S.BLOCK) {
      this.guardDelay -= dt;
      if (this.guardDelay <= 0) {
        // KAIZEN_GUARD_CLASH_V8: Kaizen regenerates guard at half the usual rate.
        const guardRegen = this.kit === "chainblade" ? GUARD_REGEN * 0.5 : GUARD_REGEN;
        this.guard = Math.min(this.guard + guardRegen * dt, this.maxGuard);
      }
    }
    const a = this.atk;
    this.trail.emitting = this.state === S.ATTACK && !!a && (a.type === "melee" || a.style === "iron_tempest") &&
      (this.atkPhase === 1 || (this.atkPhase === 0 && this.stateT > a.wind * 0.6) || (this.atkPhase === 2 && this.stateT < a.wind + a.active + 0.05));
    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");
    this.model.setJudgment(this.kit === "knight" && this.look.element === "light" && this.judgmentT > 0);
    this.model.combat = [S.ATTACK, S.CHARGE, S.BLOCK, S.HITSTUN, S.STAGGER].includes(this.state);
    this.model.hurt = this.state === S.HITSTUN || this.state === S.STAGGER;
    this.model.charge = this.state === S.CHARGE ? Math.min(this.stateT / CHARGE_MAX, 1) : Math.max(this.model.charge - dt * 4, 0);
    // Iron Tempest: one full turn over the attack's active window.
    // Model-only rotation preserves the player-facing direction and collision tests.
    const tempestActive = this.kit === "greatsword" && this.state === S.ATTACK && this.atk?.style === "iron_tempest";
    const tempestPhase = tempestActive ? Math.max(0, Math.min(1, (this.stateT - this.atk!.wind) / this.atk!.active)) : 0;
    this.tempestSpin = tempestActive ? Math.PI * 2 * (tempestPhase * tempestPhase * (3 - 2 * tempestPhase)) : 0;
    // SWORD_AND_CYCLONE_V1: Kira turns her ENTIRE body while the feet alternate.
    const cycloneActive = this.kit === "kicks" && this.state === S.ATTACK && this.atk?.style === "cyclone_kick_v2";
    const cyclonePhase = cycloneActive ? Math.max(0, Math.min(1, (this.stateT - this.atk!.wind) / this.atk!.active)) : 0;
    this.cycloneSpin = cycloneActive ? Math.PI * 4 * (cyclonePhase * cyclonePhase * (3 - 2 * cyclonePhase)) : 0;
    // One-handed Aster and two-handed Garrick lead sword strikes with their torsos.
    // No world-facing change: hit detection and shielding remain authoritative.
    const bladeActive = this.state === S.ATTACK && this.atk?.type === "melee" &&
      ((this.kit === "greatsword") || (this.kit === "glaive") || (this.kit === "knight" && this.look.element === "light"));
    if (bladeActive) {
      const a = this.atk!;
      const progress = Math.max(0, Math.min(1, this.stateT / Math.max(a.wind + a.active, 0.01)));
      const turn = progress * progress * (3 - 2 * progress);
      const direction = this.atkId === "l2" ? -1 : 1;
      const recoveryT = Math.max(0, Math.min(1, (this.stateT - a.wind - a.active) / Math.max(0.01, a.recover)));
      const settle = 1 - recoveryT * recoveryT * (3 - 2 * recoveryT);
      this.bladeSwingYaw = direction * (this.kit === "greatsword" ? 0.48 : this.kit === "glaive" ? (this.atkId === "l4" ? 0.44 : 0.29) : 0.27) * (1 - 2 * turn) * settle;
    } else this.bladeSwingYaw = 0;
    this.model.rotation.y = this.viewBias + this.tempestSpin + + this.cycloneSpin + this.bladeSwingYaw;
    this.computePose();
    this.model.bloodFestivalT = this.kit === "sickle" ? this.bloodFestivalT : 0;
    this.model.chainFuryT = this.kit === "chainblade" ? this.chainFuryT : 0;
    this.model.chainPose = this.kit === "chainblade" ? this.poseName : "idle";
    this.model.chainExtended = this.kit === "chainblade" && (this.chainFuryT > 0 ||
      ["cbz_w", "cbz_s", "cbx_w", "cbx1_s", "cbx2_s", "cbx3_s", "cbh_w", "cbh_s", "cbv_w", "cbv_s"].includes(this.poseName));
    this.model.glaivePose = this.kit === "glaive" ? this.poseName : "idle";
    this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
    this.bowDraw(dt);
    this.trail.update(dt);
  }

  /** Archer: the string comes back during the wind-up / charge and snaps forward on release. */
  private bowDraw(dt: number) {
    if (this.kit !== "bow") return;
    const drawing = this.poseName === "bow_w" || this.poseName === "rain_w" || this.poseName === "charge";
    this.model.draw = drawing ? Math.min(this.model.draw + dt * 8, 1) : 0;
  }

  // --- input -> actions ---------------------------------------------------------
  /** Double-tapped direction: a quick burst that dodges hits (6 s cooldown). */
  private readDash() {
    if (this.chainBindT > 0 || (this.chainBoundBy && this.chainBoundBy.chainBindT > 0)) return;
    const d = this.intent.dash;
    if (d.lengthSq() < 0.01 || this.dashCd > 0) return;
    if (![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(this.state)) return; // dash cancels attacks, not hitstun
    const dir = d.clone().setY(0);
    if (this.stage) { if (Math.abs(dir.x) < 0.3) return; dir.set(Math.sign(dir.x), 0, 0); this.facing = dir.x; }
    dir.normalize();
    if (this.state !== S.IDLE) { if (this.state === S.ATTACK) this.finishAttack(); this.holding = false; this.setState(S.IDLE); }
    this.dashDir.copy(dir);
    this.dashT = DASH_T;
    this.dashCd = DASH_CD;
    this.invulnT = Math.max(this.invulnT, 0.15); // brief dodge window at the start of the dash
    this.onDash(this);
  }
  dashing() { return this.dashT > 0; }

  private readAttack(dt: number) {
    const on = this.intent.attack;
    const pressed = on && !this.atkPrev;
    const released = !on && this.atkPrev;
    this.atkPrev = on;
    if ([S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state)) { this.holding = false; return; }
    if (pressed && this.atkLock > 0) return;
    // AIR_COMBAT_V1: Space+Click resolves on press, no charged-heavy misfire.
    // Holding the airborne chord turns the strike into a heavier sideways finisher.
    if (on && this.intent.jump && !this.onGround && !this.airHeavyDone &&
        this.state === S.ATTACK && this.atkId.startsWith("air_l")) {
      this.airHoldT += dt;
      if (this.airHoldT >= 0.34 && this.atkPhase >= 1) {
        this.airHeavyDone = true;
        this.holding = false;
        this.startAttack("air_heavy");
        return;
      }
    }
    if (pressed && this.intent.jump && this.atkLock <= 0) {
      if ((this.onGround || this.airStartT < 0.22) &&
          (this.state === S.IDLE || this.state === S.BLOCK ||
           (this.kit === "glaive" && this.state === S.ATTACK &&
            this.atk?.style === "glaive_serpent" && this.atkPhase === 1))) {
        this.holding = false;
        this.airStartT = 99;
        this.startAttack("anti_air");
        return;
      }
      if (!this.onGround && (this.state === S.IDLE ||
          (this.state === S.ATTACK && this.atkId.startsWith("air_l")))) {
        this.holding = false;
        this.airHoldT = 0;
        this.airHeavyDone = false;
        this.requestAirLight();
        return;
      }
    }
    if (pressed && this.kit === "glaive" && this.state === S.ATTACK &&
        this.atkId === "l4" && this.atk?.next === "l5") this.buffered = true;
    if (pressed) { this.holding = true; this.holdT = 0; }
    if (this.holding) {
      this.holdT += dt;
      if (this.holdT >= HOLD_T && this.state === S.IDLE && !this.intent.block) this.setState(S.CHARGE);
    }
    if (released && this.holding) {
      this.holding = false;
      if (this.state === S.CHARGE) this.startAttack("heavy");
      else if (this.holdT < HOLD_T) this.requestLight();
    }
  }

  private readJump() {
    // AIR_COMBAT_V1: Space+Click launches an anti-air instead of also jumping.
    // The player must release Space, then tap it again after a landed launcher to chase.
    const want = this.stage ? (this.intent.jump || this.up()) : this.intent.jump;
    const was = this.stage ? this.upPrev : this.jumpPrev;
    if (want && !was && this.airChaseT > 0 && this.airChaseTarget && !this.airChaseUsed &&
        (this.state === S.IDLE || (this.state === S.ATTACK && this.atkId === "anti_air" && this.atkPhase >= 1))) {
      this.jumpPrev = true;
      this.upPrev = true;
      this.startAirChase();
      return;
    }
    if (this.onGround && this.state === S.ATTACK && this.atkId === "anti_air") {
      this.jumpPrev = want;
      this.upPrev = want;
      return;
    }
    // An aerial Space+Click is an attack, not a second jump.
    if (!this.onGround && this.state === S.ATTACK &&
        (this.atkId.startsWith("air_l") || this.atkId === "air_heavy") && this.intent.attack) {
      this.jumpPrev = want;
      this.upPrev = want;
      return;
    }
    if (this.stage) { this.readJumpPlat(); return; }
    const pressed = this.intent.jump && !this.jumpPrev;
    this.jumpPrev = this.intent.jump;
    if (pressed && this.onGround && (this.state === S.IDLE || this.state === S.BLOCK)) {
      this.velY = this.jumpV;
      this.onGround = false;
      if (this.state === S.BLOCK) this.setState(S.IDLE);
    } else if (pressed && !this.onGround && this.kit === "wind" && this.airJump < 1 && this.state === S.IDLE) {
      // Double jump: a second push of wind in mid-air.
      this.airJump++;
      this.airJumpT = 0.45;
      this.velY = this.jumpV * 0.75;
      this.model.recoil = 0.3;
      this.onAirJump(this);
    }
  }

  /** KAIZEN_SERPENT_SLAM_V10: animated grappling, no instant teleports. */
  private animateSerpentBound(owner: Fighter, dt: number) {
    const t = Math.max(0, owner.chainBindFinishDuration - owner.chainBindFinishT);
    const forward = owner.stage ? new THREE.Vector3(owner.facing, 0, 0) :
      new THREE.Vector3(Math.sin(owner.root.rotation.y), 0, Math.cos(owner.root.rotation.y));
    // Side view: use the combat line instead of shoving fighters into invisible depth.
    const side = owner.stage ? forward.clone() : new THREE.Vector3(forward.z, 0, -forward.x);
    const origin = owner.root.position;
    const back = owner.chainResolveDirection === "backward";
    // Each pose: [time, forward offset, sideways offset, vertical lift, body tilt].
    const frames: number[][] = back ? [
      [0.23, 1.05, 0, 0.18, 0],
      [0.47, 0.20, 0, 1.65, 0.55],
      [0.72, -0.90, 0.50, 0.04, 0.88],
      [0.90, -0.20, 0.0, 1.10, -0.50],
      [1.15, -1.05, -0.50, 0.04, -0.90],
      [1.34, -0.10, 0, 1.50, 0.30],
      [1.65, -1.25, 0, 0.05, -0.80],
      [1.85, -1.35, 0, 0.05, 0]
    ] : [
      [0.23, 1.08, 0, 0.18, 0],
      [0.46, 0.90, 0, 1.72, -0.45],
      [0.71, 0.78, -0.90, 0.05, -0.95],
      [0.88, 0.80, -0.15, 1.16, 0.48],
      [1.17, 0.88, 0.90, 0.05, 0.95],
      [1.36, 0.90, 0, 1.62, -0.40],
      [1.65, 1.03, 0, 0.05, 0.75],
      [1.85, 1.10, 0, 0.05, 0]
    ];
    const from = [0, 0, 0, 0, 0];
    let prev = from, next = frames[0], prevT = 0;
    if (t > frames[0][0]) {
      for (let i = 0; i < frames.length; i++) {
        if (t <= frames[i][0] || i === frames.length - 1) {
          next = frames[i];
          prev = i === 0 ? from : frames[i - 1];
          prevT = i === 0 ? 0 : frames[i - 1][0];
          break;
        }
      }
    }
    const u0 = THREE.MathUtils.clamp((t - prevT) / Math.max(0.001, next[0] - prevT), 0, 1);
    const u = u0 * u0 * (3 - 2 * u0); // eased acceleration/recoil
    const value = (i: number) => THREE.MathUtils.lerp(prev[i], next[i], u);
    // First segment reels the victim from exactly where the bind caught them.
    const p = origin.clone().addScaledVector(forward, value(1)).addScaledVector(side, value(2));
    p.y += value(3);
    if (t < frames[0][0]) p.lerpVectors(owner.chainBindStartPos, p, u);
    if (this.stage) {
      p.x = THREE.MathUtils.clamp(p.x, this.stage.blast.l + 1, this.stage.blast.r - 1);
      p.z = owner.root.position.z;
    } else {
      const radial = Math.hypot(p.x, p.z);
      if (radial > this.arenaRadius) { p.x *= this.arenaRadius / radial; p.z *= this.arenaRadius / radial; }
    }
    this.root.position.copy(p);
    this.root.rotation.z = value(4); // visible flips as the chain whips the body around
    this.onGround = false;
    this.poseName = t < 0.45 ? "hit" : t < 1.35 ? "stagger" : "hit";
    this.model.blend(this.poses[this.poseName] ?? this.poses.hit ?? this.poses.idle, dt, 28);
  }

  private chainRelativeDirection(): "forward" | "backward" | "left" | "right" | "neutral" {
    const m = this.intent.skillMove ?? this.intent.move;
    if (m.lengthSq() < 0.04) return "neutral";
    if (this.stage) {
      // Side-view: horizontal direction is forward/back relative to current facing.
      if (Math.abs(m.x) > 0.25) return m.x * this.facing > 0 ? "forward" : "backward";
      // Camera up/down is used for jumping/dropping in platform mode; not a side throw.
      return "neutral";
    }
    const forward = new THREE.Vector3(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
    const front = m.dot(forward), right = m.x * forward.z - m.z * forward.x;
    if (Math.abs(front) >= Math.abs(right)) return front >= 0 ? "forward" : "backward";
    return right >= 0 ? "right" : "left";
  }

  beginChainBind(victim: Fighter, kind: "x" | "v") {
    if (this.chainBindTarget || victim.chainBoundBy || victim.isDown() || this.isDown()) return;
    this.chainBindTarget = victim;
    this.chainBindKind = kind;
    this.chainBindT = 4;
    this.chainChoiceArmed = false; // require a new key press after the bind connects
    this.chainBindFinishT = 0;
    this.chainBindFinishDuration = 0;
    this.chainBindStartPos.copy(victim.root.position);
    this.chainResolveDirection = "";
    victim.chainBoundBy = this;
    this.chainHookTarget = victim;
    this.chainHookT = 0;
    this.velY = 0; this.vx = 0; this.knock = 0;
    victim.velY = 0; victim.vx = 0; victim.knock = 0;
    this.model.chainBindTargetWorld = victim.chest();
    if (kind === "x" && this.state === S.ATTACK) {
      this.finishAttack();
      this.setState(S.IDLE);
    }
  }

  releaseChainBind() {
    const victim = this.chainBindTarget;
    if (victim && victim.chainBoundBy === this) {
      victim.chainBoundBy = null;
      victim.root.rotation.z = 0; // restore upright posture after the cinematic
    }
    this.chainBindTarget = null;
    this.chainBindKind = "";
    this.chainBindT = 0;
    this.chainChoiceArmed = false;
    this.chainBindFinishT = 0;
    this.chainBindFinishDuration = 0;
    this.chainResolveDirection = "";
    // KAIZEN_BIND_FOLLOWUP_V7: prevent the selection key firing after release.
    this.intent.skill = "";
    this.model.chainBindTargetWorld = null;
    if (this.state === S.ATTACK) {
      this.finishAttack();
      this.setState(S.IDLE);
    }
  }

  private readSkill() {
    const k = this.intent.skill;
    if (!k) return;
    // While bound, Z/X are handled in update() before readSkill(); other skills are locked.
    if (this.chainBindT > 0 || (this.chainBoundBy && this.chainBoundBy.chainBindT > 0)) return;
    // C: Blood Festival shuts off ALL active skills (Z/X/C/V) for its full 6 seconds.
    if (this.kit === "sickle" && this.bloodFestivalT > 0) return;
    // Blood Sickle can be steered once after launch, regardless of cooldown.
    if (this.kit === "sickle" && this.sickleOut && this.attacks[k]?.style === "bloodsickle") {
      if (![S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state)) this.onSickleRecast(this);
      return;
    }
    // Powder keg out: the same key is the detonator (works any time you're not stunned).
    if (this.barrelOut && this.attacks[k]?.type === "barrel") {
      if (![S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state)) this.onTrigger(this);
      return;
    }
    if ((this.cooldowns[k] ?? 1) > 0) return;
    const free = [S.IDLE, S.BLOCK, S.CHARGE].includes(this.state) || (this.state === S.ATTACK && this.atkPhase === 2);
    if (!free) return;
    this.holding = false;
    if (this.kit === "chainblade") this.chainSkillDir = this.chainRelativeDirection();
    // The keg's cooldown starts when it explodes (the arena sets it).
    this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 : this.attacks[k].cd * this.cdMult;
    // Cast in the air, a skill with an air version uses it instead.
    this.startAttack(!this.onGround && this.attacks[k + "_air"] ? k + "_air" : k);
  }

  // AIR_COMBAT_V1: pressed light combos in the air, buffering the next strike.
  private requestAirLight() {
    if (this.onGround) return;
    if (this.state === S.IDLE || this.state === S.BLOCK) this.startAttack("air_l1");
    else if (this.state === S.ATTACK && this.atkId.startsWith("air_l") && this.atk?.next)
      this.buffered = true;
  }

  /** Called by the authoritative arena only after an anti-air actually connects. */
  landedAntiAir(target: Entity) {
    if (target.isDown()) return;
    this.airChaseTarget = target;
    this.airChaseT = 1.15;
    this.airChaseUsed = false;
  }

  private startAirChase() {
    const target = this.airChaseTarget;
    if (!target || target.isDown() || this.airChaseT <= 0) return;
    const toward = target.root.position.clone().sub(this.root.position).setY(0);
    if (toward.lengthSq() < 0.01) toward.set(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
    this.airChaseDir.copy(toward.normalize());
    if (this.stage) this.airChaseDir.set(Math.sign(target.root.position.x - this.root.position.x) || this.facing, 0, 0);
    this.airChaseMoveT = 0.30;
    this.velY = Math.max(this.jumpV * (this.stage ? 1.43 : 1.32),
      Math.sqrt(Math.max(0, target.root.position.y - this.root.position.y) * 2 * GRAVITY));
    this.onGround = false;
    this.ground = null;
    this.airChaseT = 0;
    this.airChaseUsed = true;
    this.holding = false;
    this.atk = null;
    this.atkId = "";
    this.setState(S.IDLE);
    this.model.recoil = 0.3;
  }

  private tryAirRecovery() {
    const pressed = this.intent.block && !this.airRecoverPrev;
    this.airRecoverPrev = this.intent.block;
    if (!pressed || this.onGround || this.airRecoverUsed || this.state !== S.HITSTUN || this.stateT < 0.18) return;
    // Deliberately one escape only: no infinite air-teching or invulnerable flight.
    this.airRecoverUsed = true;
    this.invulnT = Math.max(this.invulnT, 0.16);
    this.velY = Math.max(this.velY, 1.6);
    this.knock = 0;
    if (this.stage) this.vx = -this.facing * this.moveSpeed * 1.3;
    this.model.recoil = 0.65;
    this.setState(S.IDLE);
  }

  private requestLight() {
    if (this.state === S.IDLE || this.state === S.BLOCK) this.startAttack(this.comboTimer > 0 ? this.comboNext : "l1");
    else if (this.state === S.ATTACK && this.atk && this.atk.next) this.buffered = true;
  }

  private startAttack(id: string) {
    // Platform mode: with no direction held, turn toward a nearby foe before swinging.
    if (this.stage && Math.abs(this.intent.move.x) < 0.2 && this.opponent && !this.opponent.isDown()) {
      const dx = this.opponent.root.position.x - this.root.position.x;
      if (Math.abs(dx) < 6 && Math.abs(dx) > 0.05) this.facing = Math.sign(dx);
    }
    this.atkPower = 1;
    if (id === "heavy" && this.state === S.CHARGE) this.atkPower = 1 + 0.5 * Math.min(this.stateT / CHARGE_MAX, 1);
    this.atkPower *= this.dmgMult * (this.rageT > 0 ? RAGE_MULT : 1) * this.status.dmgMult();
    if (this.kit === "knight" && this.look.element === "light" && this.judgmentT > 0) {
      const defenseToOffense = Math.min(0.45, this.maxGuard / 100 * 0.35);
      const missingLifeBonus = Math.max(0, 1 - this.hp / Math.max(1, this.maxHp)) * 0.20;
      this.atkPower *= (1 + defenseToOffense + missingLifeBonus);
    }
    // Veyr: during the 6-second Blood Festival, his LIGHT combo hits 35% harder.
    // Heavy attacks and special skills do not receive this bonus.
    if (this.kit === "sickle" && this.bloodFestivalT > 0 && /^l\d+$/.test(id)) this.atkPower *= 1.35;
    // Unbound Drive expands BASIC reach but does not bypass blocks, parries, or clashes.
    this.atkId = id;
    this.atk = this.attacks[id];
    // AIR_COMBAT_V1: avoid missing pose names on custom character rigs.
    if (!this.atk) { this.atkId = ""; return; }
    if (this.kit === "knuckles" && this.atk?.name === "Meteor Fist") this.knock = 0;
    if (this.kit === "chainblade" && this.chainFuryT > 0 && /^l\d+$/.test(id))
      this.atk = { ...this.atk, reach: this.atk.reach + 0.32, guard: this.atk.guard * 1.12 };
    // Each real clash adds +20% light-combo speed, capped at 2x. Counter itself is uncapped.
    if (this.kit === "glaive" && /^l[1-9]$/.test(id)) {
      const speed = 1 + Math.min(this.clashMomentum, 5) * 0.20;
      this.atk = { ...this.atk, wind: this.atk.wind / speed,
        active: this.atk.active / speed, recover: this.atk.recover / speed };
    }
    if (this.kit === "sickle" && this.bloodFrenzyT > 0 && id.startsWith("l"))
      this.atk = { ...this.atk, wind: this.atk.wind * 0.88, recover: this.atk.recover * 0.88 };
    this.atkPhase = 0;
    this.buffered = false;
    this.comboDamageMult = 1;
    this.comboPauseT = 0;
    this.swingSerial++;
    if (this.atk.self_jump > 0 && this.atk.mode !== "leap") { this.velY = this.atk.self_jump * (this.stage ? 1.35 : 1); this.onGround = false; this.ground = null; }
    this.setState(S.ATTACK);
  }

  private attackStep() {
    const a = this.atk!;
    const w = a.wind, ac = a.active, r = a.recover;
    if (a.mode === "leap" || a.mode === "dive") {
      // Leap attack: wind-up crouch -> jump toward the target -> the hit lands on touchdown.
      // Dive: from the air, plunge down (toward the target) -> the hit lands on touchdown.
      if (this.atkPhase === 0 && this.stateT >= w) {
        this.atkPhase = 1;
        const o = this.opponent;
        if (a.mode === "dive") {
          this.velY = -a.speed;
          const air = Math.max(this.root.position.y / a.speed, 0.08);
          if (o && !o.isDown()) {
            const to = o.root.position.clone().sub(this.root.position).setY(0);
            const d = Math.max(to.length() - 0.9, 0);
            this.leapVel.copy(to.normalize().multiplyScalar(Math.min(d / air, a.lunge)));
          } else this.leapVel.set(0, 0, 0);
        } else {
          this.velY = a.self_jump * (this.stage ? 1.35 : 1);
          this.onGround = false;
          this.ground = null;
          const air = (2 * this.velY) / GRAVITY;
          if (o && !o.isDown()) {
            const to = o.root.position.clone().sub(this.root.position).setY(0);
            const d = Math.max(to.length() - 0.9, 0);
            this.leapVel.copy(to.normalize().multiplyScalar(Math.min(d / air, 9)));
          } else this.leapVel.set(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y)).multiplyScalar(3);
        }
        if (this.stage) this.vx = this.leapVel.x;
      } else if (this.atkPhase === 1) {
        if (this.onGround && (a.mode === "dive" || this.stateT > w + 0.1)) {
          this.atkPhase = 2;
          this.stateT = w + ac;
          this.leapVel.set(0, 0, 0);
          this.onSwing(this);
        }
      } else if (this.atkPhase === 2 && this.stateT >= w + ac + r) { this.finishAttack(); this.setState(S.IDLE); }
      return;
    }
    if (this.atkPhase === 0 && this.stateT >= w) {
      this.atkPhase = 1;
      this.onSwing(this);
    } else if (this.atkPhase === 1 && this.stateT >= w + ac) {
      this.atkPhase = 2;
    } else if (this.atkPhase === 2) {
      if (this.buffered && a.next && this.stateT >= w + ac + Math.min(0.1, r)) this.startAttack(a.next);
      else if (this.intent.block && this.stateT >= w + ac + 0.06) { this.finishAttack(); this.setState(S.BLOCK); }
      else if (this.stateT >= w + ac + r) { this.finishAttack(); this.setState(S.IDLE); }
    }
  }

  private finishAttack() {
    const a = this.atk!;
    if (/^l\d$/.test(this.atkId) && !a.next && a.type !== "melee") this.atkLock = RANGED_COMBO_REST[this.kit] ?? 1.2;
    this.comboNext = a.next || "l1";
    this.comboTimer = a.next ? 0.45 : 0;
  }

  private setState(s: S) {
    if (s === S.BLOCK && this.state !== S.BLOCK) {
      this.shieldRaise = this.nextShieldFast ? 0.05 : 0.10;
      this.nextShieldFast = false;
    }
    this.state = s; this.stateT = 0; this.poseOverride = "";
  }
  /** Pose forced by the arena during an attack (e.g. each kick of a teleport combo). */
  poseOverride = "";

  // --- movement ---------------------------------------------------------------------
  private move(dt: number) {
    const pos = this.root.position;
    const o = this.opponent;
    let dir = new THREE.Vector3(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
    let dist = 99;
    if (o && !o.isDown()) {
      const to = o.root.position.clone().sub(pos);
      to.y = 0;
      dist = to.length();
      dir = to.divideScalar(Math.max(dist, 0.001));
    } else if (this.intent.move.lengthSq() > 0.01) {
      dir = this.intent.move.clone().normalize();
    }
    if (this.state !== S.KO) {
      const target = Math.atan2(dir.x, dir.z);
      let d = target - this.root.rotation.y;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.root.rotation.y += d * (1 - Math.exp(-12 * dt));
    }
    if (this.state === S.ATTACK && (this.atk?.mode === "leap" || this.atk?.mode === "dive") && this.atkPhase === 1) {
      pos.addScaledVector(this.leapVel, dt);
      const fl = Math.hypot(pos.x, pos.z);
      if (fl > this.arenaRadius) { pos.x *= this.arenaRadius / fl; pos.z *= this.arenaRadius / fl; }
      this.model.rotation.y = this.viewBias;
      return;
    }
    if (this.airChaseMoveT > 0 && !this.onGround) {
      pos.addScaledVector(this.airChaseDir, Math.min(this.moveSpeed * 3.1, 12) * dt);
      const flat = Math.hypot(pos.x, pos.z);
      if (flat > this.arenaRadius) { pos.x *= this.arenaRadius / flat; pos.z *= this.arenaRadius / flat; }
      return;
    }
    if (this.dashT > 0) {
      pos.addScaledVector(this.dashDir, DASH_SPEED * dt);
      const fl = Math.hypot(pos.x, pos.z);
      if (fl > this.arenaRadius) { pos.x *= this.arenaRadius / fl; pos.z *= this.arenaRadius / fl; }
      if (this.state !== S.KO) this.model.rotation.y = this.viewBias;
      return;
    }
    let v = 0;
    let walking = false;
    // No brain yet = still in the READY countdown: stand still.
    if (this.state === S.IDLE && this.autoApproach && this.brain && o && !o.isDown() && dist > ENGAGE) { v = this.walkSpeed * (this.meteorFistArmor ? 1 : this.status.speedMult()); walking = true; }
    if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1 && dist > MIN_DIST + 0.15) v += this.atk.lunge;
    this.knock = Math.max(this.knock - 14 * dt, 0);
    v -= this.knock;
    if (dist < MIN_DIST && v > 0) v = 0;
    pos.addScaledVector(dir, v * dt);
    const steer = this.state === S.IDLE ? 1 : this.state === S.BLOCK ? 0.5 : this.state === S.CHARGE ? 0.4 : 0;
    if (steer > 0 && this.intent.move.lengthSq() > 0.0001) {
      const step = this.intent.move.clone().normalize().multiplyScalar(this.moveSpeed * (this.bloodFrenzyT > 0 ? 1.15 : 1) * (this.meteorFistArmor ? 1 : this.status.speedMult()) * steer * dt);
      if (dist < MIN_DIST && step.dot(dir) > 0) step.addScaledVector(dir, -step.dot(dir));
      pos.add(step);
      walking = this.onGround;
    }
    if (dist < MIN_DIST * 0.9) pos.addScaledVector(dir, -(MIN_DIST * 0.9 - dist) * 0.5);
    const flat = Math.hypot(pos.x, pos.z);
    if (flat > this.arenaRadius) { pos.x *= this.arenaRadius / flat; pos.z *= this.arenaRadius / flat; }
    this.model.walk = Math.min(Math.max(this.model.walk + (walking ? 1 : -1) * dt * 6, 0), 1);
    if (this.state !== S.KO) this.model.rotation.y = this.viewBias;
  }

  private vertical(dt: number) {
    if (this.onGround) return;
    this.velY -= GRAVITY * dt;
    this.root.position.y += this.velY * dt;
    if (this.root.position.y <= 0) {
      this.root.position.y = 0;
      this.velY = 0;
      this.onGround = true;
      this.airJump = 0;
      this.airRecoverUsed = false;
      this.airStartT = 99;
      this.airChaseMoveT = 0;
      this.model.recoil = 0.35;
      this.onLanded(this);
    }
  }

  teleport(to: THREE.Vector3) {
    if (this.stage) {
      const b = this.stage.blast;
      this.root.position.x = Math.max(b.l + 2, Math.min(b.r - 2, to.x));
      this.invulnT = 0.3;
      if (this.opponent) this.facing = Math.sign(this.opponent.root.position.x - this.root.position.x) || this.facing;
      return;
    }
    const flat = Math.hypot(to.x, to.z);
    const k = flat > this.arenaRadius ? this.arenaRadius / flat : 1;
    this.root.position.set(to.x * k, this.root.position.y, to.z * k);
    this.invulnT = 0.3;
    if (this.opponent) {
      const d = this.opponent.root.position.clone().sub(this.root.position);
      this.root.rotation.y = Math.atan2(d.x, d.z);
    }
  }

  private tickStatus(dt: number) {
    if (this.state === S.KO || this.state === S.WIN || this.stage) { this.status.clear(); return; }
    const st = this.status.tick(dt, this.model.walk > 0.3);
    for (const d of st.dots) {
      this.hp = Math.max(this.hp - d.dmg, 0);
      this.dots.push({ ...d, src: this.status.src });
      if (this.hp <= 0) { this.ko(); return; }
    }
    if (st.jolt && this.bloodFestivalT <= 0 && !this.meteorFistArmor && this.state !== S.HITSTUN && this.state !== S.STAGGER) {
      this.stun = 0.25; this.stunPose = "hit"; this.holding = false;
      this.setState(S.HITSTUN);
      this.model.flash("#ffe066", 0.12);
    }
  }

  // --- getting hit --------------------------------------------------------------------
  /** Returns "miss", "warded", "counter", "parry", "blocked", "guard_break", "hit", "crit" or "ko". */
  receiveHit(attacker: Entity | null, a: Attack, power: number): string {
    if (this.state === S.KO) return "none";
    if (this.invulnT > 0) return "miss";
    if (this.wardT > 0) { this.model.recoil = 0.4; return "warded"; }
    if (this.counterT > 0 && !a.no_parry) { this.counterT = 0; return "counter"; }
    let dmg = a.dmg * power;
    this.knockFrom = attacker ? attacker.root.position.x : this.root.position.x - this.facing;
    // Veyr's Blood Festival forbids the perfect-parry outcome against his melee swings.
    // A regular block still costs guard, and simultaneous attacks can still clash.
    const festivalUnparryable = attacker instanceof Fighter && attacker.kit === "sickle" &&
      attacker.bloodFestivalT > 0 && a.type === "melee";
    // Guard is not instantly active while the shield is still being raised.
    if (this.state === S.BLOCK && this.stateT >= this.shieldRaise) {
      if (this.stateT - this.shieldRaise <= this.parryWindow && !a.no_parry && !festivalUnparryable) {
        this.guard = Math.min(this.guard + 20, this.maxGuard);
        this.model.flash("#99e6ff", 0.15);
        // Reward applies to the NEXT shield raise, once only; never stack it.
        this.nextShieldFast = true;
        return "parry";
      }
      // Blood Festival: Veyr's blocked LIGHT sickle hits drain 3x normal guard.
      // power already includes the 1.35x Festival damage buff; cancel that ONLY
      // for guard calculation, then apply the requested 3x guard multiplier.
      // HP damage, clashes, and normal blocks otherwise behave as before.
      const festivalGuardTriple = attacker instanceof Fighter && attacker.kit === "sickle" &&
        attacker.bloodFestivalT > 0 && a.type === "melee" && /^l\d+$/.test(attacker.atkId);
      this.guard -= a.guard * power * (festivalGuardTriple ? 2 / 1.35 : 1) *
        (this.judgmentT > 0 ? 1.5 : 1); // Aster Judgment weakens defense; Veyr nerf unchanged
      this.guardDelay = 1;
      if (this.guard <= 0) {
        this.guard = 0;
        this.lastDamage = dmg * 0.4;
        this.lastCrit = false;
        this.hp = Math.max(this.hp - this.lastDamage, 0);
        this.knock = 3.5;
        if (this.hp <= 0) { this.ko(); return "ko"; }
        if (this.bloodFestivalT <= 0) this.stagger(0.85);
        this.model.flash("#ffd966", 0.18);
        return "guard_break";
      }
      // KAIZEN_GUARD_CLASH_V8: the spinning chain catches incoming melee weapons.
      // Parry (above) and guard break (above) retain priority; projectiles still block.
      if (this.kit === "chainblade" && attacker instanceof Fighter && a.type === "melee") {
        this.knock = Math.min(a.knock * 0.12, 0.5);
        this.model.recoil = 0.85;
        return "kaizen_guard_clash";
      }
      this.knock = a.knock * 0.5;
      this.model.recoil = 0.7;
      return "blocked";
    }
    const cc = attacker && (attacker as any).critChance !== undefined ? (attacker as any).critChance : 0.2;
    this.lastCrit = Math.random() < cc;
    if (this.lastCrit) dmg *= 1.6;
    if (this.stage) return this.launch(attacker, a, dmg);
    this.lastDamage = dmg;
    this.hp = Math.max(this.hp - dmg, 0);
    this.knock = this.meteorFistArmor ? 0 : a.knock;
    this.model.flash();
    if (this.hp <= 0) { this.ko(); return "ko"; }
    // Even during Blood Festival, damage and non-stunning conditions still land.
    if (a.effect && !(this.bloodFestivalT > 0 && a.effect === "paralyze") &&
        !(this.meteorFistArmor && (a.effect === "paralyze" || a.effect === "slow")))
      this.status.apply(a.effect as StatusKind, a.effect_t, a.effect_p, attacker);
    // ASTER_EMBER_LATEST_20261106: no repetitive hitstun from passive ground fire.
    if (a.id === "ember_ground") return this.lastCrit ? "crit" : "hit";
    // Stun rules: one stun per skill use (multi-hit skills don't re-stun every tick), and
    // repeated stuns within a few seconds get shorter, so nobody can be locked forever.
    const src = attacker instanceof Fighter ? `${attacker.id}:${attacker.swingSerial}` : "";
    const reeling = this.state === S.HITSTUN || this.state === S.STAGGER;
    if (src && src === this.stunSrc && reeling) return this.lastCrit ? "crit" : "hit";
    this.stunSrc = src;
    this.stunChain = this.clock - this.lastStunAt < STUN_DR_WINDOW ? this.stunChain + 1 : 0;
    this.lastStunAt = this.clock;
    const stun = Math.max(0.1, a.stun * Math.pow(STUN_DR, this.stunChain));
    if (this.bloodFestivalT <= 0 && !this.meteorFistArmor) {
      if (a.heavy || a.stagger) this.stagger(stun);
      else { this.stun = stun; this.stunPose = "hit"; this.holding = false; this.setState(S.HITSTUN); }
    }
    return this.lastCrit ? "crit" : "hit";
  }

  stagger(d: number) { if (this.bloodFestivalT > 0 || this.meteorFistArmor) return; this.stun = d; this.stunPose = "stagger"; this.holding = false; this.setState(S.STAGGER); }

  clashRecoil() {
    if (this.isContinuousComboActive()) {
      // Clash does not interrupt the remaining hits or pause their timeline.
      this.comboDamageMult = Math.max(0.35, this.comboDamageMult * 0.95);
      this.model.recoil = Math.max(this.model.recoil, 0.24);
      return;
    }
    if (this.meteorFistArmor) {
      this.model.recoil = Math.max(this.model.recoil, 0.25);
      return; // Clash counted; Meteor Fist keeps going without being crowd-controlled.
    }
    if (this.bloodFestivalT > 0) {
      // Clash still counts. Cancel the swing and give a short physical recoil,
      // without applying stun (Blood Festival's 3-second immunity).
      this.atk = null; this.atkId = ""; this.atkPhase = 0;
      this.buffered = false; this.holding = false; this.knock = 2.2;
      this.model.recoil = 1;
      this.setState(S.IDLE);
      return;
    }
    this.stun = 0.38; this.stunPose = "clash"; this.holding = false; this.knock = 4; this.model.recoil = 1;
    this.setState(S.HITSTUN);
  }

  pushBack(speed: number) { if (!this.meteorFistArmor) this.knock = Math.max(this.knock, speed); }
  win() { if (this.state !== S.KO) this.setState(S.WIN); }

  revive(frac: number) {
    this.releaseChainBind();
    if (this.chainBoundBy) this.chainBoundBy.releaseChainBind();
    this.chainBoundBy = null;
    this.airChaseT = 0; this.airChaseMoveT = 0; this.airRecoverUsed = false;
    this.hp = this.maxHp * frac;
    this.guard = this.maxGuard;
    this.chainFuryT = 0;
    this.judgmentT = 0; this.model.setJudgment(false);
    this.clashMomentum = 0;
    this.bloodlust = 0; this.bloodFrenzyT = 0; this.bloodFeintT = 0; this.sickleOut = false; this.bloodFestivalT = 0;
    this.model.standUp();
    this.setState(S.IDLE);
  }

  heal(amount: number) { this.hp = Math.min(this.hp + amount, this.maxHp); }

  ko() {
    this.nextShieldFast = false; this.shieldRaise = 0.10;
    this.comboPauseT = 0; this.comboDamageMult = 1;
    this.judgmentT = 0; this.model.setJudgment(false);
    this.releaseChainBind();
    if (this.chainBoundBy) this.chainBoundBy.releaseChainBind();
    this.chainBoundBy = null;
    this.airChaseT = 0; this.airChaseMoveT = 0;
    this.clashMomentum = 0;
    this.bloodlust = 0; this.bloodFrenzyT = 0; this.bloodFeintT = 0; this.sickleOut = false; this.bloodFestivalT = 0;
    this.status.clear();
    this.setState(S.KO);
    this.model.fall();
    this.onKo(this);
  }

  // --- platform fighter -----------------------------------------------------------------
  /** Damage % and knockback: launch speed grows with the % already taken. */
  private launch(attacker: Entity | null, a: Attack, dmg: number): string {
    const p = dmg * PCT_PER_DMG;
    this.pct = Math.min(this.pct + p, 999);
    this.lastDamage = p;
    if (this.meteorFistArmor) {
      this.model.flash();
      return this.lastCrit ? "crit" : "hit";
    }
    const speed = 2.5 + a.knock * 0.5 + this.pct * (0.06 + p * 0.006);
    let side = Math.sign(this.root.position.x - (attacker ? attacker.root.position.x : this.knockFrom));
    if (!side) side = attacker instanceof Fighter ? attacker.facing : -this.facing;
    const ang = THREE.MathUtils.degToRad(a.self_jump > 0 ? 72 : a.heavy ? 42 : 34);
    this.vx = side * speed * Math.cos(ang);
    const vy = speed * Math.sin(ang);
    if (vy > 3 || !this.onGround) { this.velY = Math.max(this.velY * 0.2, vy); this.onGround = false; this.ground = null; }
    this.model.flash();
    this.holding = false;
    this.stun = 0.18 + speed * 0.032;
    this.stunPose = speed > 9 || a.heavy ? "stagger" : "hit";
    if (this.bloodFestivalT <= 0) this.setState(S.HITSTUN);
    return this.lastCrit ? "crit" : "hit";
  }

  private readJumpPlat() {
    const want = this.intent.jump || this.up();
    const pressed = want && !this.upPrev;
    this.upPrev = want;
    if (!pressed || ![S.IDLE, S.BLOCK, S.CHARGE].includes(this.state)) return;
    if (this.onGround) {
      this.velY = this.jumpV * 1.32;
      this.onGround = false;
      this.ground = null;
      if (this.state === S.BLOCK) this.setState(S.IDLE);
    } else if (this.airJumps > 0) {
      this.airJumps--;
      this.velY = this.jumpV * 1.15;
      const mx = this.intent.move.x;
      if (Math.abs(mx) > 0.2) { this.vx = Math.sign(mx) * this.moveSpeed * 1.2; this.facing = Math.sign(mx); }
      this.model.recoil = 0.3;
    }
  }

  private movePlat(dt: number) {
    const pos = this.root.position;
    pos.z += (this.lane - pos.z) * Math.min(1, dt * 8);
    const mx = Math.abs(this.intent.move.x) > 0.2 ? Math.sign(this.intent.move.x) : 0;
    const free = this.state === S.IDLE || this.state === S.CHARGE;
    if (this.knock > 0) {
      const o = this.opponent;
      const away = Math.sign(pos.x - (o ? o.root.position.x : this.knockFrom)) || -this.facing;
      this.vx = away * this.knock * 1.3;
      this.knock = 0;
    }
    if (mx && (this.state === S.IDLE || (this.state === S.CHARGE && this.onGround))) this.facing = mx;
    let walking = false;
    if (this.onGround) {
      let target = 0;
      if (free) { target = mx * this.moveSpeed * (this.state === S.CHARGE ? 0.3 : 1.55); walking = mx !== 0; }
      if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1) {
        const o = this.opponent;
        const near = o && !o.isDown() && Math.abs(o.root.position.x - pos.x) < MIN_DIST && Math.abs(o.root.position.y - pos.y) < 1;
        target = near ? 0 : this.facing * this.atk.lunge;
      }
      const grip = this.state === S.HITSTUN || this.state === S.STAGGER ? 5 : 16;
      this.vx += (target - this.vx) * (1 - Math.exp(-grip * dt));
    } else if (this.state === S.HITSTUN || this.state === S.STAGGER) {
      this.vx *= Math.exp(-0.6 * dt);
    } else {
      const cap = this.moveSpeed * 1.35;
      if (mx) this.vx += mx * this.moveSpeed * 4 * dt;
      if (Math.abs(this.vx) > cap) this.vx *= Math.exp(-3 * dt);
      else if (!mx) this.vx *= Math.exp(-1.2 * dt);
      if (this.state === S.ATTACK && this.atk && this.atkPhase <= 1 && this.atk.lunge > 3) this.vx = this.facing * Math.max(Math.abs(this.vx), this.atk.lunge * 0.6);
    }
    if (this.dashT > 0) { this.vx = this.dashDir.x * DASH_SPEED * 1.1; if (!this.onGround) this.velY = Math.max(this.velY, 0.5); }
    if (this.airChaseMoveT > 0 && !this.onGround)
      this.vx = this.airChaseDir.x * Math.min(this.moveSpeed * 3.1, 12);
    pos.x += this.vx * dt;
    // Main stage walls: can't pass through its sides.
    for (const p of this.stage!.plats) {
      if (!p.solid || pos.y >= p.y - 0.05 || pos.y < p.y - 4) continue;
      if (pos.x > p.x0 && pos.x < p.x1) {
        pos.x = pos.x - p.x0 < p.x1 - pos.x ? p.x0 : p.x1;
        this.vx = 0;
      }
    }
    if (this.state !== S.KO) {
      const target = this.facing * Math.PI / 2;
      let d = target - this.root.rotation.y;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.root.rotation.y += d * (1 - Math.exp(-18 * dt));
      this.model.rotation.y = this.viewBias;
    }
    this.model.walk = Math.min(Math.max(this.model.walk + (walking ? 1 : -1) * dt * 6, 0), 1);
  }

  private verticalPlat(dt: number) {
    const pos = this.root.position;
    const st = this.stage!;
    const down = this.down();
    const downPressed = down && !this.downPrev;
    this.downPrev = down;
    this.dropT = Math.max(this.dropT - dt, 0);
    if (this.onGround) {
      const g = this.ground;
      if (!g || pos.x < g.x0 || pos.x > g.x1) { this.onGround = false; this.ground = null; this.velY = 0; }
      else if (downPressed && !g.solid && (this.state === S.IDLE || this.state === S.BLOCK)) {
        this.dropT = 0.3; this.onGround = false; this.ground = null; this.velY = -2; pos.y -= 0.03;
        if (this.state === S.BLOCK) this.setState(S.IDLE);
      } else { pos.y = g.y; return; }
    }
    const prevY = pos.y;
    const tumbling = this.state === S.HITSTUN || this.state === S.STAGGER;
    this.velY -= GRAVITY * dt;
    if (!tumbling) {
      if (down && this.velY < 3 && this.state === S.IDLE) this.velY = Math.min(this.velY, -15); // fast fall
      this.velY = Math.max(this.velY, -16);
    }
    pos.y += this.velY * dt;
    if (this.velY <= 0) {
      for (const p of st.plats) {
        if (pos.x < p.x0 || pos.x > p.x1 || prevY < p.y - 0.001 || pos.y > p.y) continue;
        if (!p.solid && (this.dropT > 0 || (down && this.state === S.IDLE))) continue;
        pos.y = p.y;
        this.velY = 0;
        this.onGround = true;
        this.ground = p;
        this.airJumps = 1;
        this.airRecoverUsed = false;
        this.airStartT = 99;
        this.airChaseMoveT = 0;
        this.model.recoil = 0.35;
        this.onLanded(this);
        break;
      }
    }
    const b = st.blast;
    if (pos.x < b.l || pos.x > b.r || pos.y < b.b || pos.y > b.t) this.blastOut();
  }

  private blastOut() {
    this.onBlast(this);
    this.stocks--;
    this.out = true;
    this.root.visible = false;
    this.trail.emitting = false;
    this.vx = 0; this.velY = 0; this.knock = 0;
    this.atk = null;
    this.holding = false;
    if (this.stocks <= 0) { this.ko(); return; }
    this.respawnT = 1.4;
  }

  private waitRespawn(dt: number) {
    if (this.state === S.KO) return;
    this.respawnT -= dt;
    if (this.respawnT > 0) return;
    const r = this.stage!.respawn;
    this.root.position.set(r.x + this.lane * 2, r.y, this.lane);
    this.root.visible = true;
    this.out = false;
    this.pct = 0;
    this.onGround = false;
    this.ground = null;
    this.velY = 0;
    this.airJumps = 1;
    this.airRecoverUsed = false;
    this.airChaseT = 0;
    this.airChaseMoveT = 0;
    this.invulnT = 2;
    this.guard = this.maxGuard;
    this.setState(S.IDLE);
    this.model.flash("#ffffff", 0.25);
  }

  // --- posing -------------------------------------------------------------------------
  private computePose() {
    let p = "idle", sp = 14;
    const a = this.atk;
    switch (this.state) {
      case S.IDLE:
        if (!this.onGround) {
          if (this.airJumpT > 0 && this.poses.wind_jump) { p = "wind_jump"; sp = 18; }
          else { p = "jump"; sp = 12; }
        }
        break;
      case S.BLOCK: p = "block"; sp = 30; break;
      case S.CHARGE: p = this.attacks.heavy.pose_w; sp = 10; break;
      case S.ATTACK:
        if (this.poseOverride) { p = this.poseOverride; sp = 40; break; }
        if (a?.mode === "leap" || a?.mode === "dive") {
          if (this.atkPhase === 0) { p = a.pose_w; sp = 16; }
          else if (this.atkPhase === 1) { p = "slam_air"; sp = 14; }
          else { p = a.pose_s; sp = 40; }
          break;
        }
        // VEYR_BLOODLUST_CARRION_V7: animate every slash on host and online clients.
        if (this.kit === "sickle" && a?.style === "sickle_carrion") {
          const elapsed = this.stateT - a.wind;
          p = elapsed < 0 ? "vrv_w" : ["vrv1_s", "vrv2_s", "vrv3_s", "vrv4_s", "vrv5_s"][Math.min(4, Math.floor(elapsed / 0.14))];
          sp = elapsed < 0 ? 22 : 48;
          break;
        }
        // ZAREK_CYCLONE_V3: true successive poses for serpent, slide reversal and ultimate.
        if (this.kit === "glaive" && a?.style === "glaive_serpent") {
          const elapsed = this.stateT - a.wind;
          if (elapsed < 0) { p = "glz_w"; sp = 27; }
          else { p = ["glz_s", "gl3_s", "gl2_s", "gl4_s", "glz_s"][Math.min(4, Math.floor(elapsed / 0.21))]; sp = 43; }
          break;
        }
        if (this.kit === "glaive" && a?.style === "glaive_phantom") {
          p = this.stateT < a.wind ? "glx_w" : this.stateT < a.wind + 0.19 ? "gl2_s" : "glx_turn"; sp = 46;
          break;
        }
        if (this.kit === "glaive" && a?.style === "glaive_infinite") {
          const elapsed = this.stateT - a.wind;
          p = elapsed < 0 ? "glc_w" : elapsed < 1.43 ? ["gl1_s", "gl2_s", "gl3_s", "gl4_s", "gl2_s", "gl3_s", "glc_launch"][Math.min(6, Math.floor(elapsed / 0.215))] : "glc_finish";
          sp = elapsed < 0 ? 22 : 55;
          break;
        }
        // ZAREK_GLAIVE_CHOREO_V2: readable windup, fast weapon contact, controlled follow-through.
        if (this.kit === "glaive" && a?.type === "melee") {
          if (this.atkPhase === 0) { p = a.pose_w; sp = 23; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = 66; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.8) { p = a.pose_s; sp = 18; }
          else { p = "idle"; sp = 13; }
          break;
        }
        if (a?.style === "cyclone_kick_v2") {
          const elapsed = this.stateT - a.wind;
          if (elapsed < 0) { p = "cy1_w"; sp = 24; }
          else if (elapsed < 0.19) { p = "cy1_s"; sp = 50; }
          else if (elapsed < 0.38) { p = "cy2_s"; sp = 55; }
          else { p = "cy3_s"; sp = 55; }
          break;
        }
        if (a?.style === "chain_carousel") {
          const elapsed = this.stateT - a.wind;
          if (elapsed < 0) { p = "cbx_w"; sp = 17; }
          else if (elapsed < 0.19) { p = "cbx1_s"; sp = 38; }
          else if (elapsed < 0.40) { p = "cbx2_s"; sp = 42; }
          else { p = "cbx3_s"; sp = 40; }
          break;
        }
        if (a?.style === "iron_tempest") {
          // Distinct two turning slashes and a full-body heavy horizontal finish.
          const elapsed = this.stateT - a.wind;
          if (elapsed < 0) { p = "charge"; sp = 16; }
          else if (elapsed < 0.30) { p = "l1_s"; sp = 38; }
          else if (elapsed < 0.62) { p = "l2_s"; sp = 40; }
          else { p = "heavy_s"; sp = 36; }
          break;
        }
        if (a?.type === "melee" && (this.kit === "greatsword" ||
            (this.kit === "knight" && this.look.element === "light"))) {
          const heavySword = this.kit === "greatsword";
          if (this.atkPhase === 0) { p = a.pose_w; sp = heavySword ? 13 : 24; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = heavySword ? 28 : 46; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.75) {
            p = a.pose_s; sp = heavySword ? 12 : 22;
          } else { p = "idle"; sp = heavySword ? 8 : 13; }
          break;
        }
        if (this.atkPhase === 0) { p = a!.pose_w; sp = 22; }
        else if (this.atkPhase === 1) { p = a!.pose_s; sp = 45; }
        else if (this.stateT < a!.wind + a!.active + a!.recover * 0.5) { p = a!.pose_s; sp = 20; }
        else sp = 9;
        break;
      case S.HITSTUN:
      case S.STAGGER: p = this.stunPose; sp = 28; break;
      case S.KO: p = "down"; sp = 10; break;
      case S.WIN: p = "win"; sp = 6; break;
    }
    // AIR_COMBAT_V1: all air attacks use the same procedural / VRM pose pipeline.
    // Existing attack poses are chosen per-kit in kits.ts.
    this.poseName = p;
    this.poseSpeed = sp;
  }

  // --- networking -----------------------------------------------------------------------
  /** Compact state sent from the host to clients. */
  snapshot(): any[] {
    const p = this.root.position;
    return [this.id, +p.x.toFixed(3), +p.y.toFixed(3), +p.z.toFixed(3), +this.root.rotation.y.toFixed(3),
      this.state, this.poseName, this.poseSpeed, Math.round(this.hp), Math.round(this.guard),
      +this.model.walk.toFixed(2), +this.model.charge.toFixed(2), this.trail.emitting ? 1 : 0,
      +this.model.recoil.toFixed(2), this.cooldowns.z, this.cooldowns.x, this.cooldowns.c, this.maxHp,
      +this.pct.toFixed(1), this.stocks, this.out ? 1 : 0, +this.atkLock.toFixed(2), +this.dashCd.toFixed(2), this.status.mask, this.barrelOut ? 1 : 0, Math.round(this.bloodlust), +this.bloodFrenzyT.toFixed(2), this.sickleOut ? 1 : 0, +this.bloodFestivalT.toFixed(2), +this.tempestSpin.toFixed(3), +this.cycloneSpin.toFixed(3), +this.bladeSwingYaw.toFixed(3), +this.chainFuryT.toFixed(2), this.clashMomentum, this.chainBindTarget ? +this.chainBindTarget.chest().x.toFixed(2) : null, this.chainBindTarget ? +this.chainBindTarget.chest().y.toFixed(2) : null, this.chainBindTarget ? +this.chainBindTarget.chest().z.toFixed(2) : null, +this.chainBindT.toFixed(2), +this.judgmentT.toFixed(2), +this.comboDamageMult.toFixed(3), +this.comboPauseT.toFixed(2)];
  }

  applySnapshot(s: any[]) {
    this.netPos.set(s[1], s[2], s[3]);
    this.netRot = s[4];
    const prev = this.state;
    this.state = s[5];
    this.poseName = s[6];
    this.poseSpeed = s[7];
    this.hp = s[8];
    this.guard = s[9];
    this.model.walk = s[10];
    this.model.charge = s[11];
    this.trail.emitting = s[12] === 1;
    this.model.recoil = Math.max(this.model.recoil, s[13]);
    this.cooldowns.z = s[14]; this.cooldowns.x = s[15]; this.cooldowns.c = s[16];
    this.maxHp = s[17];
    if (s.length > 18) {
      this.pct = s[18]; this.stocks = s[19]; this.atkLock = s[21] ?? 0; this.dashCd = s[22] ?? 0; this.status.mask = s[23] ?? 0; this.barrelOut = s[24] === 1; this.bloodlust = s[25] ?? 0; this.bloodFrenzyT = s[26] ?? 0; this.sickleOut = s[27] === 1; this.bloodFestivalT = s[28] ?? 0; this.clashMomentum = s[33] ?? 0; this.chainFuryT = s[32] ?? 0;
      this.model.chainBindTargetWorld = s.length >= 37 && s[34] !== null
        ? new THREE.Vector3(s[34], s[35], s[36]) : null;
      this.chainBindT = s[37] ?? 0; // KAIZEN_BIND_ZX_V6: remote HUD follow-ups
      this.judgmentT = s[38] ?? 0; // ASTER_EMBER_LATEST_20261106: preserve older fields
      this.comboDamageMult = s[39] ?? 1;
      this.comboPauseT = s[40] ?? 0;
      const out = s[20] === 1;
      if (out !== this.out) { this.out = out; this.root.visible = !out; if (!out) this.root.position.copy(this.netPos); }
    }
    this.tempestSpin = s[29] ?? 0;
    this.cycloneSpin = s[30] ?? 0;
    this.bladeSwingYaw = s[31] ?? 0;
    if (this.state === S.KO && prev !== S.KO) this.model.fall();
    if (this.state !== S.KO && prev === S.KO) this.model.standUp();
  }

  private updatePuppet(dt: number) {
    const k = 1 - Math.exp(-15 * dt);
    if (this.root.position.distanceTo(this.netPos) > 3) this.root.position.copy(this.netPos);
    else this.root.position.lerp(this.netPos, k);
    let d = this.netRot - this.root.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    this.root.rotation.y += d * k;
    for (const key in this.cooldowns) this.cooldowns[key] = Math.max(this.cooldowns[key] - dt, 0);
    this.atkLock = Math.max(this.atkLock - dt, 0);
    this.dashCd = Math.max(this.dashCd - dt, 0);
    if (this.state !== S.KO) this.model.rotation.y = this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw;
    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");
    this.model.setJudgment(this.kit === "knight" && this.look.element === "light" && this.judgmentT > 0);
    this.model.combat = [S.ATTACK, S.CHARGE, S.BLOCK, S.HITSTUN, S.STAGGER].includes(this.state);
    this.model.hurt = this.state === S.HITSTUN || this.state === S.STAGGER;
    this.model.bloodFestivalT = this.kit === "sickle" ? this.bloodFestivalT : 0;
    this.model.chainFuryT = this.kit === "chainblade" ? this.chainFuryT : 0;
    this.model.chainPose = this.kit === "chainblade" ? this.poseName : "idle";
    this.model.chainExtended = this.kit === "chainblade" && (this.chainFuryT > 0 ||
      ["cbz_w", "cbz_s", "cbx_w", "cbx1_s", "cbx2_s", "cbx3_s", "cbh_w", "cbh_s", "cbv_w", "cbv_s"].includes(this.poseName));
    this.model.glaivePose = this.kit === "glaive" ? this.poseName : "idle";
    this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
    this.bowDraw(dt);
    this.trail.update(dt);
  }
}
