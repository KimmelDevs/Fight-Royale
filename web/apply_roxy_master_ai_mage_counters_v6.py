#!/usr/bin/env python3
"""Fight Royale: Roxy AI skill intelligence + real basic-projectile mage ripostes.

Run from the web/ folder AFTER Roxy V5. Modifies src/game/ai.ts,
src/game/kits.ts, src/game/fighter.ts and src/game/model.ts; backs them up before writing.
Honours real cooldowns, V unlock, casting animation and CPU difficulty.
"""
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path.cwd()
PATHS = ['src/game/ai.ts', 'src/game/kits.ts', 'src/game/fighter.ts', 'src/game/model.ts']
try:
    old = {p: (ROOT / p).read_text(encoding='utf-8') for p in PATHS}
except OSError as err:
    sys.exit(f'ERROR: {err}. Run this inside web/. No files changed.')
AI, KITS, FIGHTER, MODEL = PATHS
MARK = 'ROXY_MASTER_SKILLS_MAGE_BASIC_COUNTERS_V6_20261108'
if MARK in old[AI]:
    print('Roxy AI V6 already installed. No changes needed.')
    sys.exit(0)
if 'ROXY_BALANCE_GRIMOIRE_FROSTBITE_V5_20261108' not in (ROOT/'src/game/game.ts').read_text(encoding='utf-8'):
    sys.exit('ERROR: Roxy V5 is required. Install the Roxy V5 balance/grimoire update first. No files changed.')
if 'frost_aegis' not in old[KITS] or 'Frost Marionette' not in old[KITS] or 'Frostwing Choir' not in old[KITS]:
    sys.exit('ERROR: Could not find Roxy V5 frost kit. No files changed.')
new = old.copy()

def replace_once(path: str, before: str, after: str) -> None:
    n = new[path].count(before)
    if n != 1:
        raise RuntimeError(f'{path}: expected one source anchor, found {n}: {before[:100]!r}. No files changed.')
    new[path] = new[path].replace(before, after, 1)

try:
    replace_once(AI, '// Duel CPU. Presses the same virtual buttons a player would, with human-ish reaction times:',
                 f'// {MARK}: Roxy combat planning and one-projectile mage parry counters.\n// Duel CPU. Presses the same virtual buttons a player would, with human-ish reaction times:')
    replace_once(AI,
        '  nesa: { range: 2.38, heavy: 0.43, combo: 0.64, bait: 0.62, pressure: 0.52, skillBias: [1.05, 1.15, 1.2] },',
        '  nesa: { range: 2.38, heavy: 0.43, combo: 0.64, bait: 0.62, pressure: 0.52, skillBias: [1.05, 1.15, 1.2] },\n'
        '  roxy: { range: 5.45, heavy: 0.36, combo: 0.52, bait: 0.24, pressure: 0.32, skillBias: [1.45, 1.60, 1.20] },')
    replace_once(AI,
        '  nesa:    { role: "bruiser",     pressure: 1.03, probe: 1.04, reset: 0.45, vReserve: 0.85, spacing:  0.19 },',
        '  nesa:    { role: "bruiser",     pressure: 1.03, probe: 1.04, reset: 0.45, vReserve: 0.85, spacing:  0.19 },\n'
        '  roxy:    { role: "controller",  pressure: 0.60, probe: 1.16, reset: 0.90, vReserve: 0.52, spacing:  0.26 },')
    replace_once(AI,
        '  private readySkillPoll = 0;',
        '''  private readySkillPoll = 0;
  // Roxy uses a short, difficulty-scaled plan that is evaluated before
  // ordinary attack IQ can keep her locked into endless light-attack queues.
  private roxySkillReadAt = 0;
  private roxyTarget = -1;''')

    method = '''  /** Roxy's actual kit is not a generic melee skill set:
   * Z is four-charge damage prevention, X is an automatic FREEZE summon,
   * C is targeted meteor, and Master-only V is stationary Frostwing artillery.
   * Samples visible opportunities and issues ONE legal skill press. No free
   * cooldowns, HP, hits, extra summons or fourth-skill unlocks.
   */
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

'''
    replace_once(AI, '  private readySkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {',
                 method + '  private readySkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {')

    old_entry = '''    const landedActed = !survivalActed && !this.aiAirTap && !f.intent.skill &&
      this.aerialLandingPunish(f, o);
    const iqActed = !survivalActed && !landedActed && !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.combatIQAction(f, o, dt);
    const patternActed = !survivalActed && !landedActed && !iqActed && !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.patternFootwork(f, o);
    if (!survivalActed && !landedActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&
        this.projectileSwordCommit <= 0 &&
        !this.readySkillOpportunity(f, o, dt) && !this.theaterOffense(f, o))'''
    new_entry = '''    const landedActed = !survivalActed && !this.aiAirTap && !f.intent.skill &&
      this.aerialLandingPunish(f, o);
    // Roxy's kit plan runs BEFORE normal combo/pattern reads starve her skills.
    const roxyActed = !survivalActed && !landedActed && !this.aiAirTap && !f.intent.skill &&
      this.roxySkillOpportunity(f, o, dt);
    const iqActed = !survivalActed && !landedActed && !roxyActed && !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.combatIQAction(f, o, dt);
    const patternActed = !survivalActed && !landedActed && !roxyActed && !iqActed && !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.patternFootwork(f, o);
    if (!survivalActed && !landedActed && !roxyActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&
        this.projectileSwordCommit <= 0 &&
        !this.readySkillOpportunity(f, o, dt) && !this.theaterOffense(f, o))'''
    replace_once(AI, old_entry, new_entry)

    # The generic skill scorer must recognize Roxy's shield/summon types too.
    replace_once(AI,
'''    } else if (a.type === "buff") {
      viable = a.mode === "counter" || a.mode === "blood_feint"
        ? attackComing && close''',
'''    } else if (a.type === "snow_puppet") {
      // Persistent summons have their own range; no fabricated melee reach.
      viable = id !== "roxy" ||
        (a.style === "bird" ? distance >= 2.6 && distance < 9.4 :
          !o.status.has("freeze") && o.status.freezeImmunityRemaining() <= 0 && distance < 7.8);
    } else if (a.type === "buff") {
      viable = a.mode === "frost_aegis" ?
        (f.frostShieldCharges <= 0 || f.frostShieldT <= 0) &&
        (f.hp < f.maxHp * 0.80 || (attackComing && distance < 6.5)) :
        a.mode === "counter" || a.mode === "blood_feint"
        ? attackComing && close''')
    replace_once(AI, '      case "marina":\n        if (name === "Bubble Ward"', '''      case "roxy":
        if (a.mode === "frost_aegis") points += attackComing ? 3.0 : 0.2;
        if (name === "Frost Marionette") points += punish ? 2.0 : 1.2;
        if (name === "Glacier Meteor") points += o.status.has("freeze") ? 3.2 : punish ? 2.0 : 0;
        if (name === "Frostwing Choir") points += distance > 3.2 && !attackComing ? 1.8 : 0;
        break;
      case "marina":
        if (name === "Bubble Ward"''')

    # The real Fighter PC is reused by human and CPU; mage PC is now one
    # ordinary elemental basic shot and does not invoke Game's melee spin hit.
    replace_once(KITS, '  t.pc = parryCounterAttack(kit, element, t);', '''  t.pc = parryCounterAttack(kit, element, t);
  if (kit === "mage") {
    // Roxy/Ember/Raven/Marina: after a legitimate parry, launch ONE regular
    // basic projectile. It is not a spin/AOE and still clashes and can be dodged.
    const basic = t.l1;
    t.pc = { ...basic, name: "Arcane Riposte", desc: "On a successful parry, cast one ordinary basic projectile.",
      type: "projectile", wind: 0.16, active: 0.05, recover: 0.30,
      dmg: basic.dmg, guard: basic.guard, knock: basic.knock, stun: basic.stun,
      heavy: false, count: 1, spread: 0, next: "", pierce: false,
      pose_w: basic.pose_w, pose_s: basic.pose_s };
  }''')
    replace_once(FIGHTER,
      '  parryCounterReach() { return (this.attacks.pc ?? this.attacks.l1).reach; }',
      '  parryCounterReach() { return this.kit === "mage" ? 10.0 : (this.attacks.pc ?? this.attacks.l1).reach; }')

    # Roxy V5 placed her book at a fixed torso offset; with the real VRM
    # this puts it in/above the head and it drifts during spells. The real
    # normalized VRM right-hand bone is the definitive visual anchor.
    # Parent the book to the model root, not to the hand or torso. At the
    # END of blend(), sample the hand after the VRM rig has updated and
    # move it to a small hover point above/outside the open palm.
    replace_once(MODEL,
      '''    // ROXY V5: book reduced to a small grimoire hovering above the palm, not held like a gun.
    const b = pivot(this.torso, [-0.48, -0.16, 0.57], [-0.12, -0.35, 0.08]);
    b.scale.setScalar(0.62);
    this.roxyFloatingBook = b;''',
      '''    // ROXY V6: float above the actual VRM hand, NOT a fixed torso coordinate.
    // A model-root pivot avoids inheriting the hand's grip/gun rotation.
    const b = pivot(this, [0, 0, 0], [-0.46, -0.26, 0.10]);
    b.scale.setScalar(0.58);
    this.roxyFloatingBook = b;''')
    replace_once(MODEL,
      '''    if (this.roxyFloatingBook) {
      this.roxyFloatingBook.position.y = -0.16 + Math.sin(this.t * 2.3) * 0.032;
      this.roxyFloatingBook.rotation.y = -0.35 + Math.sin(this.t * 1.8) * 0.09;
      this.roxyFloatingBook.rotation.z = 0.08 + Math.sin(this.t * 2.0) * 0.045;
    }''',
      '''    // Book placement happens after vrmRig.update below, when the visual
    // wrist has reached its final animated location for this frame.''')
    replace_once(MODEL,
      '    this.vrmRig?.update(dt, { t: this.t, walk: this.walk, phase: this.walkPhase, crouch: this.hipsY, combat: this.combat, hurt: this.hurt, draw: this.draw, knee: this.knee, pose: actionPose });',
      '''    this.vrmRig?.update(dt, { t: this.t, walk: this.walk, phase: this.walkPhase, crouch: this.hipsY, combat: this.combat, hurt: this.hurt, draw: this.draw, knee: this.knee, pose: actionPose });
    // ROXY V6: correct both procedural and VRM grimoire placement, every frame.
    if (this.roxyFloatingBook) {
      const hand = this.vrmRig?.vrm.humanoid.getNormalizedBoneNode("rightHand") ?? this.hand_r;
      const palm = this.worldToLocal(hand.getWorldPosition(new THREE.Vector3()));
      // Outside the right wrist, slightly up and forward: no intersection
      // with the forearm, face, or hat while the hand changes pose.
      const hover = 0.15 + Math.sin(this.t * 2.3) * 0.022;
      const pos = palm.add(new THREE.Vector3(-0.055, hover, 0.17));
      this.roxyFloatingBook.position.copy(pos);
      this.roxyFloatingBook.rotation.set(-0.46 + Math.sin(this.t * 1.6) * 0.035,
        -0.26 + Math.sin(this.t * 1.8) * 0.09,
        0.10 + Math.sin(this.t * 2.0) * 0.035);
    }''')

except Exception as err:
    sys.exit(f'PATCH PRE-FLIGHT FAILED: {err}')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for name in PATHS:
    if old[name] != new[name]:
        target = ROOT / name
        backup = target.with_name(target.name + f'.before_roxy_ai_v6_{stamp}.bak')
        backup.write_text(old[name], encoding='utf-8')
        target.write_text(new[name], encoding='utf-8')
        print(f'PATCHED {name} (backup: {backup.name})')
print('DONE: Roxy now uses Z/X/C and Master-only V tactically; mage parry counters fire one normal projectile.')
print('Grimoire fix: book floats just above the real animated VRM right palm (not a fixed torso offset).')
print('Validate: npx tsc --noEmit -p .  &&  npm run build')
