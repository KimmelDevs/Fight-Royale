#!/usr/bin/env python3
"""Fight Royale Nov-06 latest-source installer.

Adds: continuous multi-hit skills across parries/clashes, one-use faster shields
following successful parries, CPU combo-defense awareness, Aster Judgment 3D
greatblade, and Ember's staged Final Ignition gathering animation.

Copy beside web/package.json then run: py install_combat_continuity_aster_ember_v3.py
Always validates all patches in memory before changing any files. Creates backups.
"""
from __future__ import annotations
import re, shutil, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
FILES = ('src/game/fighter.ts', 'src/game/game.ts', 'src/game/ai.ts',
         'src/game/kits.ts', 'src/game/model.ts')
MARK = 'CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06'


def one(s: str, old: str, new: str, label: str, count: int=1) -> str:
    found=s.count(old)
    if found != count:
        raise ValueError(f'{label}: expected {count} occurrence(s) of {old[:100]!r}, found {found}')
    return s.replace(old,new)


def function_span(s: str, start: str, end: str, label: str):
    assert s.count(start)==1, f'{label}: start marker missing or repeated'
    after=s.find(start)
    b=s.find(end,after+len(start))
    if b<0: raise ValueError(f'{label}: end marker missing')
    return after,b


def fighter(s: str):
    n='fighter.ts'
    # Export a single authoritative definition for game physics + CPU (named animation styles only).
    before='export enum S { IDLE, ATTACK, CHARGE, BLOCK, HITSTUN, STAGGER, KO, WIN }'
    s=one(s,before,'''/** Long, individually-timed attacks keep their choreography after parries/clashes.
 * Basic light chains and single-hit skills intentionally keep ordinary reactions. */
export const CONTINUOUS_STYLES = new Set([
  "sickle_carrion", "glaive_cyclone", "glaive_serpent", "glaive_phantom", "glaive_infinite",
  "chain_razor_cyclone", "chain_death_spiral", "chain_carousel", "chain_return",
  "cyclone_kick_v2", "iron_tempest", "phantom_rush",
]);

'''+before,n)
    s=one(s,'  private guardDelay = 0;', '''  private guardDelay = 0;
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
  }''',n)
    s=one(s,'    this.stateT += dt;', '''    // A successful parry pauses a persistent combo for exactly 0.20 seconds;
    // its delayed arena hits are shifted by the same amount in Game.
    const advancing = this.state === S.ATTACK && this.comboPauseT > 0
      ? Math.max(0, dt - this.comboPauseT) : dt;
    this.comboPauseT = Math.max(0, this.comboPauseT - dt);
    this.stateT += advancing;''',n)
    s=one(s,'    this.atkPhase = 0;\n    this.buffered = false;\n    this.swingSerial++;', '''    this.atkPhase = 0;
    this.buffered = false;
    this.comboDamageMult = 1;
    this.comboPauseT = 0;
    this.swingSerial++;''',n)
    s=one(s,'    if (this.state === S.BLOCK) {\n      if (this.stateT <= this.parryWindow', '''    // Guard is not instantly active while the shield is still being raised.
    if (this.state === S.BLOCK && this.stateT >= this.shieldRaise) {
      if (this.stateT - this.shieldRaise <= this.parryWindow''',n)
    s=one(s,'        this.model.flash("#99e6ff", 0.15);\n        return "parry";', '''        this.model.flash("#99e6ff", 0.15);
        // Reward applies to the NEXT shield raise, once only; never stack it.
        this.nextShieldFast = true;
        return "parry";''',n)
    s=one(s,'  clashRecoil() {\n    if (this.meteorFistArmor)', '''  clashRecoil() {
    if (this.isContinuousComboActive()) {
      // Clash does not interrupt the remaining hits or pause their timeline.
      this.comboDamageMult = Math.max(0.35, this.comboDamageMult * 0.95);
      this.model.recoil = Math.max(this.model.recoil, 0.24);
      return;
    }
    if (this.meteorFistArmor)''',n)
    s=one(s,'  private setState(s: S) { this.state = s; this.stateT = 0; this.poseOverride = ""; }', '''  private setState(s: S) {
    if (s === S.BLOCK && this.state !== S.BLOCK) {
      this.shieldRaise = this.nextShieldFast ? 0.05 : 0.10;
      this.nextShieldFast = false;
    }
    this.state = s; this.stateT = 0; this.poseOverride = "";
  }''',n)
    # ensure shield bonus resets on new game/KO (but not on next block)
    s=one(s,'  ko() {\n    this.judgmentT = 0;', '''  ko() {
    this.nextShieldFast = false; this.shieldRaise = 0.10;
    this.comboPauseT = 0; this.comboDamageMult = 1;
    this.judgmentT = 0;''',n)
    # snapshot to animate remote position (append, keep original offsets untouched)
    s=one(s,'+this.chainBindT.toFixed(2), +this.judgmentT.toFixed(2)];',
         '+this.chainBindT.toFixed(2), +this.judgmentT.toFixed(2), +this.comboDamageMult.toFixed(3), +this.comboPauseT.toFixed(2)];',n)
    s=one(s,'      this.judgmentT = s[38] ?? 0; // ASTER_EMBER_LATEST_20261106: append only, preserve Kaizen\'s snapshot indices',
         '''      this.judgmentT = s[38] ?? 0; // ASTER_EMBER_LATEST_20261106: preserve older fields
      this.comboDamageMult = s[39] ?? 1;
      this.comboPauseT = s[40] ?? 0;''',n)
    return s


def game(s: str):
    n='game.ts'
    s=one(s,'  private timers: { t: number; fn: () => void }[] = [];',
    '''  // CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: optional tagged timers can be shifted by parry.
  private timers: { t: number; fn: () => void; owner?: Fighter; serial?: number }[] = [];''',n)
    s=one(s,'  later(delay: number, fn: () => void) { this.timers.push({ t: this.time + delay, fn }); }',
    '''  later(delay: number, fn: () => void) { this.timers.push({ t: this.time + delay, fn }); }
  /** Follow-up hits keep their owner/serial so parry can delay the ENTIRE remaining sequence. */
  private laterCombo(f: Fighter, delay: number, fn: () => void) {
    this.timers.push({ t: this.time + delay + f.comboPauseT, fn, owner: f, serial: f.swingSerial });
  }
  private delayComboFollowups(f: Fighter, delay: number) {
    for (const timer of this.timers) {
      if (timer.owner === f && timer.serial === f.swingSerial) timer.t += delay;
    }
  }''',n)
    # Replace only tagged scheduled hits inside named functions. Never modify binds or world timers.
    named=[('  private carrionSweep(', '  /** ZAREK_CYCLONE_V3', 'carrion'),
           ('  private stormGlaiveSwing(', '  private chainRazorCyclone(', 'glaive'),
           ('  private chainRazorCyclone(', '  private chainDeathSpiral(', 'razor'),
           ('  private chainDeathSpiral(', '  /** KAIZEN_SERPENT_SLAM_V10', 'death spiral'),
           ('  private chainbladeCarousel(', '  private melee(', 'carousel'),
           ('  private cycloneKick(', '  /** Garrick X:', 'kicks'),
           ('  private ironTempest(', '  /** Area attack(', 'tempest'),
           ('  private phantom(', '  private blink(', 'phantom')]
    # validate source landmarks first, then modify blocks in descending order to preserve indices
    spans=[(*function_span(s,a,b,label),label) for a,b,label in named]
    for start,end,label in sorted(spans,reverse=True):
        part=s[start:end]
        if 'this.later(' not in part: raise ValueError(n+': no scheduled hits in '+label)
        part=part.replace('this.later(', 'this.laterCombo(f, ')
        s=s[:start]+part+s[end:]
    s=one(s, '        this.later(0.18, () => {', '        this.laterCombo(f, 0.18, () => {',n)
    # Combat penalty only affects strike DAMAGE, not guard drain / knock / hit status.
    s=one(s,'    const result = d.receiveHit(attacker, a, power);', '''    // Includes Zarek's launch/finisher (their style labels differ from the base skill).
    const scaledAttack = attacker instanceof Fighter && attacker.isContinuousComboActive() &&
      !ranged && attacker.comboDamageMult < 1
      ? { ...a, dmg: a.dmg * attacker.comboDamageMult } : a;
    const result = d.receiveHit(attacker, scaledAttack, power);''',n)
    s=one(s,'''      case "parry":
        if (a.parry_stun && attacker instanceof Fighter) {
          // Weakness (Gale): a parried skill leaves him stunned.
          attacker.stagger(a.parry_stun);
          this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)), "STUNNED", "#ffe066", 1.1);
        } else if (!ranged && attacker instanceof Fighter) attacker.stagger(0.95);''',
    '''      case "parry":
        if (!ranged && attacker instanceof Fighter && attacker.onComboParried()) {
          this.delayComboFollowups(attacker, 0.20);
          this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)),
            "COMBO -10% • +0.2s", "#b8eaff", 0.82);
        } else if (a.parry_stun && attacker instanceof Fighter) {
          // Single-hit vulnerability (Gale, etc.) remains as it was.
          attacker.stagger(a.parry_stun);
          this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)), "STUNNED", "#ffe066", 1.1);
        } else if (!ranged && attacker instanceof Fighter) attacker.stagger(0.95);''',n)
    # Continuous clashes do not introduce any extra global hit-stop.
    s=one(s, '        this.hitStop(0.09);\n        break;\n      }\n      case "hit":',
      '        if (!(attacker instanceof Fighter && attacker.isContinuousComboActive())) this.hitStop(0.09);\n        break;\n      }\n      case "hit":', n)
    s=one(s, '    this.hitStop(0.13);\n  }\n\n  // --- mob attacks',
      '    if (!a.isContinuousComboActive() && !b.isContinuousComboActive()) this.hitStop(0.13);\n  }\n\n  // --- mob attacks', n)
    # Replace in-GAME Aster/Ember visuals using latest source (already installed previous gameplay)
    s=one(s,'  private emberBeams: { visual: THREE.Group; ttl: number; max: number }[] = [];',
    '''  private emberBeams: { visual: THREE.Group; ttl: number; max: number }[] = [];
  /** Animated sparks flowing from consumed ground fire/burns into the staff. */
  private emberGather: { mesh: THREE.Mesh; from: THREE.Vector3; ownerId: number;
    progress: number; duration: number; offset: number }[] = [];
  private emberCharge: { ownerId: number; mesh: THREE.Mesh; ttl: number; max: number }[] = [];''',n)
    s=one(s,'    this.emberBeams = [];\n    this.timers = [];',
    '''    this.emberBeams = [];
    for (const g of this.emberGather) this.scene.remove(g.mesh);
    this.emberGather = [];
    for (const o of this.emberCharge) this.scene.remove(o.mesh);
    this.emberCharge = [];
    this.timers = [];''',n)
    s=one(s,'      case "emberConsume": this.emberConsumeVisual(a[0], v3(a[1]), a[2]); break;',
    '''      case "emberConsume": this.emberConsumeVisual(a[0], v3(a[1]), a[2]); break;
      case "emberGather": this.emberGatherVisual(v3(a[0]), a[1], a[2]); break;
      case "emberCharge": this.emberChargeVisual(a[0], a[1]); break;''',n)
    # Improve existing Judgment strike: animated layers + visual title, no damage changes.
    s=one(s,'      this.fxp("sparks", sword, "#f0e9a3", 42, 6);',
    '''      this.fxp("sparks", sword, "#f0e9a3", 70, 9);
      this.fxp("sparks", f.model.shieldNode.getWorldPosition(new THREE.Vector3()), "#c4e8ff", 40, 7);
      this.fxp("flash", f.chest(), "#d6efff", 1.1, 0.24, 0.85);
      this.fxp("ring", sword, "#c6eeff", 1.35, 0.24, 0.85);''',n)
    # Change Ember patch consume into animated streams, omit when removing an old patch to meet cap.
    old='''  private emberConsumeVisual(ownerId: number, center: THREE.Vector3, radius: number) {
    this.emberPatches = this.emberPatches.filter(p => {
      if (p.ownerId !== ownerId || p.pos.distanceTo(center) > radius) return true;
      this.scene.remove(p.visual);
      return false;
    });
  }
'''
    new='''  private emberConsumeVisual(ownerId: number, center: THREE.Vector3, radius: number) {
    this.emberPatches = this.emberPatches.filter(p => {
      if (p.ownerId !== ownerId || p.pos.distanceTo(center) > radius) return true;
      if (radius > 0.1) this.emberGatherVisual(p.pos.clone(), ownerId, 11);
      this.scene.remove(p.visual);
      return false;
    });
  }

  /** Each consumed flame produces individual moving embers, not instantaneous light rays. */
  private emberGatherVisual(from: THREE.Vector3, ownerId: number, count = 8) {
    for (let i = 0; i < count; i++) {
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.035 + Math.random() * 0.04, 6, 5),
        new THREE.MeshBasicMaterial({ color: i % 4 === 0 ? "#fffbd4" : i % 3 === 0 ? "#ffc04e" : "#ff672d" }));
      const origin = from.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.9,
        Math.random() * 0.30, (Math.random() - 0.5) * 0.9));
      mesh.position.copy(origin);
      this.scene.add(mesh);
      this.emberGather.push({ mesh, from: origin, ownerId, progress: -i * 0.045,
        duration: 0.58, offset: Math.random() * Math.PI * 2 });
    }
  }

  private emberChargeVisual(ownerId: number, ttl = 0.64) {
    const fighter = this.entities.get(ownerId);
    if (!(fighter instanceof Fighter)) return;
    const mat = new THREE.MeshBasicMaterial({ color: "#fff9e5", transparent: true, opacity: 0.95, depthWrite: false });
    const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.18, 14, 12), mat);
    fighter.model.castPoint.add(sphere);
    this.emberCharge.push({ ownerId, mesh: sphere, ttl, max: ttl });
  }
'''
    s=one(s,old,new,n)
    s=one(s,'  private updateEmberFire(dt: number) {\n    for (const b of this.emberBeams)',
    '''  private updateEmberFire(dt: number) {
    for (const p of this.emberGather) {
      p.progress += dt / p.duration;
      if (p.progress >= 1) { this.scene.remove(p.mesh); continue; }
      if (p.progress < 0) continue;
      const caster = this.entities.get(p.ownerId);
      const target = caster instanceof Fighter
        ? caster.model.castPoint.getWorldPosition(new THREE.Vector3())
        : p.from.clone().add(new THREE.Vector3(0, 1.5, 0));
      const u = Math.max(0, Math.min(1, p.progress));
      const ease = u * u * (3 - 2 * u);
      p.mesh.position.copy(p.from).lerp(target, ease);
      p.mesh.position.y += Math.sin(Math.PI * u) * 0.70;
      p.mesh.position.x += Math.sin(u * Math.PI * 5 + p.offset) * 0.22 * (1 - u);
      p.mesh.position.z += Math.cos(u * Math.PI * 5 + p.offset) * 0.22 * (1 - u);
      p.mesh.scale.setScalar(Math.max(0.12, 1 - u * 0.70));
    }
    this.emberGather = this.emberGather.filter(p => p.progress < 1);
    for (const orb of this.emberCharge) {
      orb.ttl -= dt;
      const t = 1 - Math.max(0, orb.ttl) / orb.max;
      orb.mesh.scale.setScalar(0.3 + 1.0 * Math.sin(Math.PI * t));
      if (orb.ttl <= 0) orb.mesh.parent?.remove(orb.mesh);
    }
    this.emberCharge = this.emberCharge.filter(o => o.ttl > 0);
    for (const b of this.emberBeams)''',n)
    # Rewrite casting function to stage visual gathering and delayed hit.
    start,end=function_span(s, '  private castEmberIgnition(f: Fighter, a: Attack) {', '  /** Teleport behind the target', n+' emberIgnition')
    rewritten='''  private castEmberIgnition(f: Fighter, a: Attack) {
    // The cast is authoritative. Consume buffs/patches now; release the beam only
    // after animated embers have visibly travelled to the staff tip.
    const round = this.round, serial = f.swingSerial;
    const pos = f.root.position.clone();
    const burned = this.enemiesOf(f).filter((e): e is Fighter | Mob =>
      (e instanceof Fighter || e instanceof Mob) && !e.isDown() &&
      e.root.position.distanceTo(pos) <= 9 && e.status.has("burn"));
    const patches = this.emberPatches.filter(p => p.ownerId === f.id && p.pos.distanceTo(pos) <= 9);
    const bonus = Math.min(5, patches.length) * 55 + Math.min(4, burned.length) * 45;
    this.fxp("emberCharge", f.id, 0.64);
    if (patches.length) this.fxp("emberConsume", f.id, pos, 9);
    for (const enemy of burned) {
      this.fxp("emberGather", enemy.chest(), f.id, 9);
      enemy.status.consume("burn");
    }
    this.fxp("ring", pos, "#ff9b40", 2.0, 0.32, 0.90);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)),
      `GATHERING FLAMES +${bonus}`, "#ffe4a0", 0.9);
    this.snd("fireball", 0.60);
    this.later(0.60, () => {
      if (round !== this.round || f.isDown() || f.swingSerial !== serial) return;
      const start = f.model.castPoint.getWorldPosition(new THREE.Vector3());
      const toward = f.opponent && !f.opponent.isDown()
        ? f.opponent.chest().sub(start).normalize()
        : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
      const end = start.clone().addScaledVector(toward, 11);
      this.fxp("emberBeam", start, end);
      this.fxp("flash", start, "#fffdf0", 1.4, 0.27, 1.0);
      this.fxp("sparks", start, "#ffcf63", 72, 9);
      this.fxp("ring", f.root.position.clone(), "#ffd3a1", 2.5, 0.35, 0.9);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)),
        `FINAL IGNITION +${bonus}`, "#fff5bf", 1.05);
      this.snd("fireball", 1.0);
      const beamHit: Attack = { ...a, type: "strike", dmg: 320 + bonus,
        guard: 75, knock: 7, stun: 0.75, heavy: true,
        effect: "burn", effect_t: 4, effect_p: 30, no_parry: true };
      for (const enemy of this.enemiesOf(f)) {
        const rel = enemy.chest().sub(start);
        const projection = rel.dot(toward);
        if (projection < 0 || projection > 11) continue;
        const off = rel.addScaledVector(toward, -projection).length();
        if (off > 0.8 + enemy.radius) continue;
        this.applyHit(f, enemy, beamHit, f.atkPower, enemy.chest(), toward, true);
      }
    });
  }

'''
    s=s[:start]+rewritten+s[end:]
    return s


def ai(s: str):
    n='ai.ts'
    s=one(s,'  private chainDecisionT = 0;',
    '''  private chainDecisionT = 0;
  // CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: track the active enemy combo through all beats.
  private comboThreatSerial = -1;''',n)
    s=one(s,'    this.react(f, o);\n    if (!f.stage)', '''    this.react(f, o);
    this.defendLongCombo(f, o);
    if (!f.stage)''',n)
    s=one(s,'  private dodge(f: Fighter) {',
    '''  /** CPUs no longer assume that a parry or clash ends a multi-hit special. */
  private defendLongCombo(f: Fighter, o: Fighter) {
    if (!o.isContinuousComboActive()) { this.comboThreatSerial = -1; return; }
    const a = o.atk!;
    const remaining = Math.max(0.15, a.wind + a.active + a.recover - o.stateT + o.comboPauseT);
    const close = f.root.position.distanceTo(o.root.position) <= Math.max(3.0, a.reach + 0.7);
    if (!close || f.state === S.KO) return;
    // A successful first parry only softens later hits. Keep the shield raised.
    if (this.blockWait >= 0) this.blockDur = Math.max(this.blockDur, remaining + 0.15);
    if (this.blockHold > 0) this.blockHold = Math.max(this.blockHold, remaining + 0.10);
    if (this.comboThreatSerial !== o.swingSerial) {
      this.comboThreatSerial = o.swingSerial;
      // If missed the first telegraph, higher-level CPUs can still prepare for later beats.
      if (this.blockWait < 0 && this.blockHold <= 0 && f.state === S.IDLE &&
          Math.random() < this.p.block * 0.70) {
        this.schedule(0, Math.min(1.95, remaining + 0.10));
      }
    }
  }

  private dodge(f: Fighter) {''',n)
    s=one(s, '      if (r < this.p.parry) this.schedule(Math.max(tth - 0.07, 0), 0.3);',
    '''      // Shield needs real raise time; after a parry, the next raise is twice as fast.
      const raise = f.nextShieldFast ? 0.05 : 0.10;
      if (r < this.p.parry) this.schedule(Math.max(tth - raise - 0.03, 0),
        o.isContinuousComboActive() ? Math.max(0.35, o.atk.wind + o.atk.active + o.atk.recover) : 0.3);''',n)
    s=one(s,'      else if (r < this.p.parry + bc) this.schedule(rand(this.p.react[0], this.p.react[1]) * 0.6, tth + 0.45);',
    '''      else if (r < this.p.parry + bc) this.schedule(rand(this.p.react[0], this.p.react[1]) * 0.45,
        o.isContinuousComboActive() ? Math.max(0.5, o.atk.wind + o.atk.active + o.atk.recover) : tth + 0.45);''',n)
    return s


def kits(s: str):
    n='kits.ts'
    s=one(s,'        recover: 0.62, pose_w: "mh_w", pose_s: "mh_s" });',
      '        recover: 0.80, pose_w: "ember_ignite_w", pose_s: "ember_ignite_s" });',n)
    s=one(s,'const MAGE: Record<string, Pose> = {', '''const MAGE: Record<string, Pose> = {
  // CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: planted explosive-mage ritual stance, Ember only.
  ember_ignite_w: P([-0.27, 0, 0], [-0.20, 0, 0], [-2.55, -0.10, -0.14], [0.14, 0, 0], [-0.95, -0.28, 0.58], [0.17, 0, -0.45], [-0.45, 0.0, 0.16], [0.40, 0, -0.16], -0.20),
  ember_ignite_s: P([0.16, 0, 0], [0.09, 0, 0], [-1.72, 0.04, -0.15], [0.22, 0, 0], [-1.10, -0.15, 0.72], [0.10, 0, -0.42], [-0.56, 0, 0.18], [0.46, 0, -0.18], -0.24),''',n)
    return s


def model(s: str):
    n='model.ts'
    start,end=function_span(s,'  /** Larger blade that borrows its gold/metal plates from the shield design. */','  private buildShield() {',n)
    replacement='''  /** CONTINUOUS_COMBAT_ASTER_EMBER_V3_NOV06: ceremonial forged greatblade. */
  private buildJudgmentSword() {
    const grip = this.bladeBase.parent;
    if (!grip) return;
    this.judgmentOldSword = grip.children.filter(c => c !== this.bladeBase && c !== this.bladeTip);
    const weapon = pivot(grip);
    // Primary steel silhouette; the shield's defensive plates become the blade's ribs.
    mesh(weapon, box(0.20, 1.26, 0.075), this.steel(), [0, 0.77, 0]);
    mesh(weapon, cyl(0, 0.11, 0.45, 4), this.steel(), [0, 1.57, 0], [0, 0, PI / 4], [1.25, 1, 0.60]);
    mesh(weapon, box(0.035, 1.56, 0.095), this.glowMat, [0, 0.84, 0.035]);
    mesh(weapon, box(0.8, 0.090, 0.16), this.tn(this.look.trim), [0, 0.20, 0]);
    mesh(weapon, box(0.38, 0.42, 0.20), this.tn(this.look.shield), [0, 0.34, 0]);
    for (const side of [-1, 1]) {
      // Large detached shield-metal wing plates with gold bevels and crackling cores.
      mesh(weapon, box(0.19, 0.48, 0.075), this.tn(this.look.shield),
        [side * 0.31, 0.48, 0], [0, 0, side * 0.40]);
      mesh(weapon, box(0.12, 0.38, 0.075), this.tn(this.look.trim),
        [side * 0.235, 0.80, 0], [0, 0, side * 0.25]);
      mesh(weapon, box(0.028, 0.55, 0.09), this.glowMat,
        [side * 0.19, 0.54, 0.062], [0, 0, side * 0.38]);
      mesh(weapon, sphere(0.055, 12), this.gem(), [side * 0.36, 0.22, 0.05]);
      mesh(weapon, box(0.045, 0.30, 0.07), this.glowMat,
        [side * 0.14, 1.14, 0.065], [0, 0, side * 0.18]);
    }
    mesh(weapon, sphere(0.105, 16), this.gem(), [0, 0.35, 0.095]);
    mesh(weapon, box(0.09, 0.33, 0.15), this.tn(this.look.trim), [0, -0.01, 0]);
    mesh(weapon, sphere(0.075, 12), this.gem(), [0, -0.15, 0]);
    weapon.visible = false;
    this.judgmentSword = weapon;
  }

  /** Use the shield as the greatblade's defensive metal without leaving a second shield behind. */
  setJudgment(on: boolean) {
    if (!this.judgmentSword) return;
    this.judgmentSword.visible = on;
    for (const part of this.judgmentOldSword) part.visible = !on;
    this.shieldNode.visible = !on;
    this.bladeTip.position.y = on ? 1.76 : 1.05;
    if (this.vrmRig) this.vrmRig.shield = !on;
  }

'''
    return s[:start]+replacement+s[end:]


def main() -> int:
    if not (ROOT/'package.json').exists() or any(not (ROOT/p).exists() for p in FILES):
        print('ERROR: place script inside web/ (beside package.json and src/)',file=sys.stderr); return 1
    old={p:(ROOT/p).read_text(encoding='utf8') for p in FILES}
    if all(MARK in old[p] for p in FILES):
        print('Already installed. No changes.'); return 0
    if any(MARK in old[p] for p in FILES):
        print('ERROR: partial patch detected; restore backups before retrying.',file=sys.stderr);return 1
    if 'ASTER_EMBER_LATEST_20261106' not in old['src/game/game.ts']:
        print('ERROR: this installer expects the already-installed Aster+Ember gameplay patch from your latest ZIP.',file=sys.stderr);return 1
    patches={'src/game/fighter.ts':fighter,'src/game/game.ts':game,
             'src/game/ai.ts':ai,'src/game/kits.ts':kits,'src/game/model.ts':model}
    try:
        new={p: '// '+MARK+'\n'+patches[p](old[p]) for p in FILES}
    except Exception as e:
        print('ERROR preflight:',str(e),file=sys.stderr);return 1
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    for rel in FILES:
        dest=ROOT/rel
        backup=dest.with_name(dest.name+'.before_combat_v3_'+stamp+'.bak')
        shutil.copy2(dest,backup)
        temp=dest.with_name(dest.name+'.combat_v3_tmp')
        temp.write_text(new[rel],encoding='utf8');temp.replace(dest)
        print('PATCH',rel,'backup:',backup.name)
    print('DONE: Persistent combos (-10% parry, +0.2s; -5% clash), half-time next guard raise, smarter CPU, Aster/Ember visuals.')
    return 0

if __name__=='__main__': raise SystemExit(main())
