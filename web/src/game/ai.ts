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

  constructor(private threats: Threats, level: number) {
    this.p = PRESETS[Math.max(0, Math.min(level, PRESETS.length - 1))];
  }

  think(f: Fighter, dt: number) {
    const o = f.opponent as Fighter | null;
    if (!o || o.isDown()) return;
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
    if (f.stage) { if (this.platform(f, o, dt)) return; }
    this.react(f, o);
    this.defendLongCombo(f, o);
    if (!f.stage) { this.dodge(f); this.position(f, o, dt); }
    // Run after normal chase/strafe choices, so fire can veto a dangerous route.
    this.avoidFireGround(f);
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
    if (!f.stage && !f.onGround && f.state === S.IDLE && !f.airSliceUsed &&
        flatGap < f.attacks.air_l1.reach + 0.20 &&
        Math.abs(o.chest().y - f.chest().y) < 2.1 && this.airSliceCd <= 0 &&
        Math.random() < dt * 7.0) {
      this.aiAirTap = true;
      this.airSliceCd = rand(0.55, 0.85);
      this.queue = [];
      this.hold = 0;
    }
    if (!this.aiAirTap) this.offense(f, o, dt);
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

  private trySkill(f: Fighter, key: string, force = false) {
    if (f.cooldowns[key] > 0) return false;
    if (!force && Math.random() > 0.5) return false;
    f.intent.skill = key;
    return true;
  }

  private offense(f: Fighter, o: Fighter, dt: number) {
    if (f.state !== S.IDLE || this.queue.length || this.hold > 0 || this.blockHold > 0 ||
        this.comboParryTarget > this.threats.now()) return;
    const dist = f.root.position.distanceTo(o.root.position);
    if (f.guard <= f.maxGuard * 0.32 && f.onGround && f.attacks.l1?.type === "melee" &&
      o.state === S.ATTACK && o.atk?.type === "melee" && o.atkPhase === 0 &&
      dist < f.attacks.l1.reach + 0.35) {
      // The normal light attack will clash if its active frames overlap the enemy swing.
      this.queue.push([0, 0.06]);
      return;
    }
    if (f.stage && Math.abs(o.root.position.y - f.root.position.y) > 1.4 && !RANGED.has(f.kit)) return;
    const ranged = RANGED.has(f.kit);
    const reach = ranged ? 9 : f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks" ? 1.7 : f.kit === "greatsword" ? 2.3 : f.kit === "hammer" ? 2.45 : f.kit === "glaive" ? 1.62 : 1.9;
    this.skillCd -= dt;
    if (this.skillCd <= 0) {
      this.skillCd = rand(this.p.skill[0], this.p.skill[1]);
      for (const key of ["c", "x", "z"].sort(() => Math.random() - 0.5)) {
        const a = f.attacks[key];
        let ok = true;
        if (a.type === "melee") ok = dist < a.reach + (f.kit === "glaive" ? 0.85 : 1.5);
        else if (a.type === "strike") ok = a.at !== "self" || dist < a.radius;
        else if (a.type === "buff") ok = a.mode === "counter" ? dist < 2.5 : f.hp < f.maxHp * 0.7;
        else if (a.type === "blink") ok = (a.mode === "behind" && dist < 6) || (a.mode === "back" && dist < 2.5);
        else if (a.type === "mine") ok = dist < 4.5;
        else if (a.type === "lob") ok = dist < 9;
        else if (a.type === "barrel") ok = !f.barrelOut && dist < 6;
        if (ok && this.trySkill(f, key)) return;
      }
    }
    if (dist > reach) return;
    if (o.state === S.STAGGER) this.thinkCd = 0;
    this.thinkCd -= dt;
    if (this.thinkCd > 0) return;
    this.thinkCd = (f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks" ? rand(0.5, 1.1) : rand(0.7, 1.6)) * this.p.think;
    const heavy = o.state === S.STAGGER ? 0.5 : o.state === S.BLOCK ? 0.45 : 0.22;
    if (Math.random() < heavy) this.queue.push([0, HOLD_T + rand(0.3, 0.65)]);
    else {
      const maxHits = Math.min(this.p.combo, Object.keys(f.attacks).filter((k) => k.startsWith("l")).length);
      const hits = 1 + Math.floor(Math.random() * maxHits);
      for (let i = 0; i < hits; i++) this.queue.push([i === 0 ? 0 : 0.14, 0.06]);
    }
  }
}
