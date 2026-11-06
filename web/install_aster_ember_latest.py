#!/usr/bin/env python3
"""Install Aster Judgment and Ember Final Ignition for the user's 2026-11-06 source ZIP.

Put beside web/package.json and run: py install_aster_ember_latest.py
Checks every patch in memory before writing; makes timestamped .bak copies.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import shutil, sys

ROOT = Path(__file__).resolve().parent
NAMES = ('src/game/kits.ts','src/game/fighter.ts','src/game/model.ts','src/game/game.ts')
MARK = 'ASTER_EMBER_LATEST_20261106'

def change(s: str, old: str, new: str, name: str, num: int = 1) -> str:
    count = s.count(old)
    if count != num:
        raise ValueError(f'{name}: incompatible source; expected {num} occurrences of {old[:95]!r}, found {count}. Nothing changed.')
    return s.replace(old, new)

def kits(s: str):
    name = 'kits.ts'
    old = '      if (element === "fire") return a({ name: "Inferno Ring", desc: "A ring of fire erupts around you.", cd: 9, type: "strike", at: "self", wind: 0.15, recover: 0.45, dmg: 165, guard: 45, knock: 6, stun: 0.5, delay: 0.1, radius: 2.8, style: "explosion", pose_w: "mh_w", pose_s: "m3_s" });'
    new = '''      // ASTER_EMBER_LATEST_20261106: fire is consumed to amplify the beam.
      if (element === "fire") return a({ name: "Absolute Combustion — Final Ignition",
        desc: "Condense nearby fire patches and active burns into a white-hot beam. Each consumed patch and burn amplifies the damage.",
        cd: 16, type: "buff", mode: "ember_ignition", wind: 0.50, active: 0.06,
        recover: 0.62, pose_w: "mh_w", pose_s: "mh_s" });'''
    s = change(s, old, new, name)
    s = change(s, '    default:\n      return a({ name: "Judgment",', '''    default:
      if (element === "light") return a({ name: "Judgment",
        desc: "Raise your sword, receive harmless lightning, and merge your sword and shield for 10s. Defense converts to power, missing HP adds damage, and health drains while blocking weakens.",
        cd: 16, type: "buff", mode: "judgment", duration: 10,
        wind: 0.62, active: 0.06, recover: 0.30,
        pose_w: "judgment_raise", pose_s: "judgment_raise" });
      return a({ name: "Judgment",''', name)
    s = change(s, 'const ASTER_SWINGS: Record<string, Pose> = {', '''const ASTER_SWINGS: Record<string, Pose> = {
  // ASTER_EMBER_LATEST_20261106: Aster holds his sword straight up for Judgment.
  judgment_raise: P([-0.08, 0, -0.02], [-0.22, 0, 0], [-2.95, -0.12, 0.04], [0.1, 0, 0], [-0.32, 0.14, 0.48], [0, 0, -0.2], [-0.35, 0, 0.13], [0.31, 0, -0.13], -0.06),''', name)
    s = change(s, '    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.55, dmg: 210,',
      '    // Charged basic (heavy) leaves a 20-second fire patch at its impact.\n    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.55, dmg: 210,', name)
    s = change(s, '    t.c = a({ name: "Meteor", desc: "Call a meteor down on the enemy\'s position.",',
      '    t.c = a({ name: "Meteor", desc: "Call a meteor down on the enemy\'s position. Impact leaves burning ground for 20s.",', name)
    return s

def fighter(s: str):
    name = 'fighter.ts'
    s = change(s, '  rageT = 0;', '''  rageT = 0;
  /** ASTER_EMBER_LATEST_20261106: 10-second empowered sword/shield form. */
  judgmentT = 0;''', name)
    s = change(s, '    this.rageT = Math.max(this.rageT - dt, 0);', '''    this.rageT = Math.max(this.rageT - dt, 0);
    if (this.judgmentT > 0) {
      this.judgmentT = Math.max(0, this.judgmentT - dt);
      // Judgment lightning is harmless; the transformation itself costs 1.2% HP/s.
      this.hp = Math.max(1, this.hp - this.maxHp * 0.012 * dt);
    }''', name)
    s = change(s, '    this.atkPower *= this.dmgMult * (this.rageT > 0 ? RAGE_MULT : 1) * this.status.dmgMult();', '''    this.atkPower *= this.dmgMult * (this.rageT > 0 ? RAGE_MULT : 1) * this.status.dmgMult();
    if (this.kit === "knight" && this.look.element === "light" && this.judgmentT > 0) {
      const defenseToOffense = Math.min(0.45, this.maxGuard / 100 * 0.35);
      const missingLifeBonus = Math.max(0, 1 - this.hp / Math.max(1, this.maxHp)) * 0.20;
      this.atkPower *= (1 + defenseToOffense + missingLifeBonus);
    }''', name)
    s = change(s, '      this.guard -= a.guard * power * (festivalGuardTriple ? 2 / 1.35 : 1);', '''      this.guard -= a.guard * power * (festivalGuardTriple ? 2 / 1.35 : 1) *
        (this.judgmentT > 0 ? 1.5 : 1); // Aster Judgment weakens defense; Veyr nerf unchanged''', name)
    # Persistent burning ground deals damage but must not interrupt attacks every second.
    s = change(s,
      '    // Stun rules: one stun per skill use (multi-hit skills don\'t re-stun every tick), and',
      '''    // ASTER_EMBER_LATEST_20261106: no repetitive hitstun from passive ground fire.
    if (a.id === "ember_ground") return this.lastCrit ? "crit" : "hit";
    // Stun rules: one stun per skill use (multi-hit skills don't re-stun every tick), and''', name)
    s = change(s, '    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");', '''    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");
    this.model.setJudgment(this.kit === "knight" && this.look.element === "light" && this.judgmentT > 0);''', name, 2)
    s = change(s, 'this.chainBindTarget ? +this.chainBindTarget.chest().z.toFixed(2) : null, +this.chainBindT.toFixed(2)];',
      'this.chainBindTarget ? +this.chainBindTarget.chest().z.toFixed(2) : null, +this.chainBindT.toFixed(2), +this.judgmentT.toFixed(2)];', name)
    s = change(s, '      this.chainBindT = s[37] ?? 0; // KAIZEN_BIND_ZX_V6: remote HUD follow-ups', '''      this.chainBindT = s[37] ?? 0; // KAIZEN_BIND_ZX_V6: remote HUD follow-ups
      this.judgmentT = s[38] ?? 0; // ASTER_EMBER_LATEST_20261106: append only, preserve Kaizen's snapshot indices''', name)
    s = change(s, '    this.chainFuryT = 0;\n    this.clashMomentum = 0;', '''    this.chainFuryT = 0;
    this.judgmentT = 0; this.model.setJudgment(false);
    this.clashMomentum = 0;''', name)
    s = change(s, '  ko() {\n    this.releaseChainBind();', '''  ko() {
    this.judgmentT = 0; this.model.setJudgment(false);
    this.releaseChainBind();''', name)
    return s

def model(s: str):
    name = 'model.ts'
    s = change(s, '  private glaivePivot: THREE.Group | null = null;', '''  private glaivePivot: THREE.Group | null = null;
  /** ASTER_EMBER_LATEST_20261106: extra sword forged from his shield. */
  private judgmentSword: THREE.Group | null = null;
  private judgmentOldSword: THREE.Object3D[] = [];''', name)
    s = change(s, '      default: this.buildSword(); this.buildShield();\n    }', '''      default: this.buildSword(); this.buildShield();
    }
    if (this.kit === "knight" && this.look.element === "light") this.buildJudgmentSword();''', name)
    s = change(s, '  private buildShield() {', '''  /** Larger blade that borrows its gold/metal plates from the shield design. */
  private buildJudgmentSword() {
    const grip = this.bladeBase.parent;
    if (!grip) return;
    this.judgmentOldSword = grip.children.filter(c => c !== this.bladeBase && c !== this.bladeTip);
    const weapon = pivot(grip);
    mesh(weapon, box(0.15, 1.05, 0.064), this.steel(), [0, 0.69, 0]);
    mesh(weapon, cyl(0, 0.075, 0.28, 4), this.steel(), [0, 1.32, 0], [0, 0, PI / 4], [1.1, 1, 0.55]);
    mesh(weapon, box(0.022, 1.14, 0.072), this.glowMat, [0, 0.66, 0.024]);
    mesh(weapon, box(0.66, 0.075, 0.13), this.tn(this.look.trim), [0, 0.22, 0]);
    mesh(weapon, box(0.27, 0.31, 0.16), this.tn(this.look.shield), [0, 0.29, 0]);
    for (const side of [-1, 1]) {
      mesh(weapon, box(0.16, 0.32, 0.065), this.tn(this.look.shield), [side * 0.26, 0.33, 0], [0, 0, side * 0.46]);
      mesh(weapon, box(0.027, 0.33, 0.075), this.glowMat, [side * 0.16, 0.34, 0.055], [0, 0, side * 0.38]);
      mesh(weapon, sphere(0.04, 10), this.gem(), [side * 0.33, 0.22, 0.04]);
    }
    mesh(weapon, sphere(0.082, 12), this.gem(), [0, 0.25, 0.085]);
    weapon.visible = false;
    this.judgmentSword = weapon;
  }

  /** Syncs immediately on the owning client and network puppets. */
  setJudgment(on: boolean) {
    if (!this.judgmentSword) return;
    this.judgmentSword.visible = on;
    for (const part of this.judgmentOldSword) part.visible = !on;
    this.shieldNode.visible = !on;
    this.bladeTip.position.y = on ? 1.46 : 1.05;
    if (this.vrmRig) this.vrmRig.shield = !on;
  }

  private buildShield() {''', name)
    return s

def game(s: str):
    name = 'game.ts'
    s = change(s, '  private kaizenGuardContacts = new WeakMap<Fighter, WeakMap<Entity, number>>();', '''  private kaizenGuardContacts = new WeakMap<Fighter, WeakMap<Entity, number>>();
  // ASTER_EMBER_LATEST_20261106: persistent Ember ground-fire visual + host damage timer.
  private emberPatches: { ownerId: number; pos: THREE.Vector3; radius: number; ttl: number;
    tick: number; visual: THREE.Group }[] = [];
  private emberBeams: { visual: THREE.Group; ttl: number; max: number }[] = [];''', name)
    s = change(s, '    this.bloodFestivals = [];\n    this.timers = [];', '''    this.bloodFestivals = [];
    for (const p of this.emberPatches) this.scene.remove(p.visual);
    this.emberPatches = [];
    for (const b of this.emberBeams) this.scene.remove(b.visual);
    this.emberBeams = [];
    this.timers = [];''', name)
    s = change(s, '    this.updateBloodFestivals(dt);', '''    this.updateBloodFestivals(dt);
    this.updateEmberFire(dt);''', name)
    s = change(s, '      case "bubble": { const e = this.entities.get(a[0]); if (e) fx.bubble(e.root, a[1]); break; }', '''      case "bubble": { const e = this.entities.get(a[0]); if (e) fx.bubble(e.root, a[1]); break; }
      case "emberPatch": this.emberPatchVisual(a[0], v3(a[1]), a[2], a[3]); break;
      case "emberConsume": this.emberConsumeVisual(a[0], v3(a[1]), a[2]); break;
      case "emberBeam": this.emberBeamVisual(v3(a[0]), v3(a[1])); break;''', name)
    s = change(s, '    this.swingSound(f, a);', '''    this.swingSound(f, a);''', name)
    s = change(s, '        this.impactFx(a, at, color, a.radius);', '''        this.impactFx(a, at, color, a.radius);
        if (f.look.element === "fire" && f.kit === "mage" &&
            (a.id === "heavy" || a.id === "c") && i === 0) {
          this.spawnEmberPatch(f, at, a.id === "c" ? 2.1 : 1.45);
        }''', name)
    s = change(s,
      '    this.snd(a.mode === "heal" ? "heal" : a.mode === "rage" ? "rage" : "ward", 0.7);',
      '''    this.snd(a.mode === "heal" ? "heal" : a.mode === "rage" ? "rage"
      : a.mode === "judgment" ? "cast" : a.mode === "ember_ignition" ? "fireball" : "ward", 0.7);''', name)
    s = change(s, '    } else if (a.mode === "blood_festival") {\n      this.startBloodFestival(f, a);', '''    } else if (a.mode === "judgment" && f.kit === "knight" && f.look.element === "light") {
      // Harmless lightning strike: only VFX. Health drain starts during the form.
      f.judgmentT = a.duration;
      f.guard = Math.min(f.guard, f.maxGuard * 0.5);
      f.model.setJudgment(true);
      const sword = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("lightning", sword, "#d8eaff");
      this.fxp("flash", sword, "#fff5c2", 1.4, 0.32, 0.98);
      this.fxp("sparks", sword, "#f0e9a3", 42, 6);
      this.fxp("ring", f.root.position.clone(), "#ffe7a3", 1.8, 0.42, 0.9);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 1, 0)), "JUDGMENT", "#ffefac", 1.2);
    } else if (a.mode === "ember_ignition" && f.kit === "mage" && f.look.element === "fire") {
      this.castEmberIgnition(f, a);
    } else if (a.mode === "blood_festival") {
      this.startBloodFestival(f, a);''', name)
    s = change(s, '  /** Teleport behind the target and kick, `repeat` times `interval` apart (alternating sides). */', '''  /** Fire patches exist for 20 seconds, damage only enemies, and replicate to online guests. */
  private spawnEmberPatch(owner: Fighter, pos: THREE.Vector3, radius: number) {
    // Cap simultaneous patches at five per player, so the arena never fills forever.
    const own = this.emberPatches.filter(p => p.ownerId === owner.id);
    if (own.length >= 5) {
      const oldest = own[0];
      this.fxp("emberConsume", owner.id, oldest.pos.clone(), 0.01);
    }
    this.fxp("emberPatch", owner.id, pos.clone(), radius, 20);
  }

  private emberPatchVisual(ownerId: number, pos: THREE.Vector3, radius: number, ttl: number) {
    const root = new THREE.Group();
    root.position.copy(pos).y += 0.045;
    const m = new THREE.MeshBasicMaterial({ color: "#ff601c", side: THREE.DoubleSide,
      transparent: true, opacity: 0.34, depthWrite: false });
    const pool = new THREE.Mesh(new THREE.CircleGeometry(radius * 0.88, 32), m);
    pool.rotation.x = -Math.PI / 2;
    root.add(pool);
    const edge = new THREE.Mesh(new THREE.RingGeometry(radius * 0.82, radius, 32),
      new THREE.MeshBasicMaterial({ color: "#ffcc55", side: THREE.DoubleSide,
        transparent: true, opacity: 0.74, depthWrite: false }));
    edge.rotation.x = -Math.PI / 2;
    edge.position.y = 0.018;
    root.add(edge);
    this.scene.add(root);
    this.emberPatches.push({ ownerId, pos: pos.clone(), radius, ttl, tick: 1, visual: root });
  }

  private emberConsumeVisual(ownerId: number, center: THREE.Vector3, radius: number) {
    this.emberPatches = this.emberPatches.filter(p => {
      if (p.ownerId !== ownerId || p.pos.distanceTo(center) > radius) return true;
      this.scene.remove(p.visual);
      return false;
    });
  }

  /** Local mesh for replicated, brief white-hot ignition beam. */
  private emberBeamVisual(from: THREE.Vector3, to: THREE.Vector3) {
    const length = Math.max(0.1, from.distanceTo(to));
    const direction = to.clone().sub(from).normalize();
    const root = new THREE.Group();
    root.position.copy(from).add(to).multiplyScalar(0.5);
    root.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
    const shell = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.48, length, 14, 1, true),
      new THREE.MeshBasicMaterial({ color: "#ff8f33", transparent: true, opacity: 0.55,
        depthWrite: false, side: THREE.DoubleSide }));
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.24, length, 12, 1, true),
      new THREE.MeshBasicMaterial({ color: "#fff9d9", transparent: true, opacity: 0.95,
        depthWrite: false, side: THREE.DoubleSide }));
    root.add(shell, core);
    this.scene.add(root);
    this.emberBeams.push({ visual: root, ttl: 0.38, max: 0.38 });
  }

  private updateEmberFire(dt: number) {
    for (const b of this.emberBeams) {
      b.ttl -= dt;
      b.visual.scale.x = b.visual.scale.z = Math.max(0.05, b.ttl / b.max);
      if (b.ttl <= 0) this.scene.remove(b.visual);
    }
    this.emberBeams = this.emberBeams.filter(b => b.ttl > 0);
    for (const p of this.emberPatches) {
      p.ttl -= dt;
      p.visual.rotation.y += dt * 0.14;
      if (p.ttl <= 0) { this.scene.remove(p.visual); continue; }
      if (this.cfg.role === "client") continue;
      p.tick -= dt;
      if (p.tick > 0) continue;
      p.tick += 1;
      const owner = this.entities.get(p.ownerId);
      if (!(owner instanceof Fighter) || owner.isDown()) continue;
      for (const enemy of this.enemiesOf(owner)) {
        const diff = enemy.root.position.clone().sub(p.pos);
        const height = Math.abs(diff.y);
        diff.y = 0;
        if (diff.length() > p.radius + enemy.radius * 0.3 || height > 1.5) continue;
        // No stun, launch, or parry from passive ground fire.
        const fire: Attack = { ...owner.attacks.heavy, id: "ember_ground", type: "strike",
          dmg: 26, guard: 5, knock: 0, stun: 0, heavy: false,
          effect: "burn", effect_t: 3, effect_p: 18, no_parry: true };
        const dir = diff.lengthSq() > 0.01 ? diff.normalize() : new THREE.Vector3(0, 0, 1);
        this.applyHit(owner, enemy, fire, 1, enemy.chest(), dir, true);
      }
    }
    this.emberPatches = this.emberPatches.filter(p => p.ttl > 0);
  }

  private castEmberIgnition(f: Fighter, a: Attack) {
    const pos = f.root.position.clone();
    const burned = this.enemiesOf(f).filter((e): e is Fighter | Mob =>
      (e instanceof Fighter || e instanceof Mob) && !e.isDown() &&
      e.root.position.distanceTo(pos) <= 9 && e.status.has("burn"));
    const patches = this.emberPatches.filter(p => p.ownerId === f.id &&
      p.pos.distanceTo(pos) <= 9);
    const consumedPatches = patches.length;
    const consumedBurns = burned.length;
    if (consumedPatches) this.fxp("emberConsume", f.id, pos, 9);
    for (const enemy of burned) enemy.status.consume("burn");
    const bonus = Math.min(5, consumedPatches) * 55 + Math.min(4, consumedBurns) * 45;
    const start = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const toward = f.opponent && !f.opponent.isDown()
      ? f.opponent.chest().sub(start).normalize()
      : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const end = start.clone().addScaledVector(toward, 11);
    this.fxp("emberBeam", start, end);
    this.fxp("flash", start, "#fff9dc", 0.85, 0.22, 0.9);
    this.fxp("sparks", start, "#ffb84a", 38, 6);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)),
      `FINAL IGNITION +${bonus}`, "#fff1b1", 1.1);
    this.snd("fireball", 0.9);
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
  }

  /** Teleport behind the target and kick, `repeat` times `interval` apart (alternating sides). */''', name)
    return s

def main():
    paths = [ROOT / n for n in NAMES]
    if not (ROOT/'package.json').exists() or any(not p.exists() for p in paths):
        print('ERROR: put this Python script in your web/ folder beside package.json', file=sys.stderr); return 1
    data = {n:p.read_text(encoding='utf-8') for n,p in zip(NAMES,paths)}
    if all(MARK in data[n] for n in NAMES):
        print('Already installed. Nothing changed.'); return 0
    if any(MARK in data[n] for n in NAMES):
        print('ERROR: partial installation markers found. No files changed. Restore backup or send current files.',file=sys.stderr);return 1
    try:
        patched = {'src/game/kits.ts': kits(data['src/game/kits.ts']),
                   'src/game/fighter.ts': fighter(data['src/game/fighter.ts']),
                   'src/game/model.ts': model(data['src/game/model.ts']),
                   'src/game/game.ts': game(data['src/game/game.ts'])}
    except ValueError as e:
        print('ERROR preflight:',e,file=sys.stderr);return 1
    assert all(MARK in p for p in patched.values())
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for n,p in zip(NAMES, paths):
        backup = p.with_name(p.name+f'.before_aster_ember_{stamp}.bak')
        shutil.copy2(p,backup)
        temp = p.with_name(p.name+'.asterembertmp')
        temp.write_text(patched[n],encoding='utf-8'); temp.replace(p)
        print(f'PATCH {n} (backup: {backup.name})')
    print('DONE. Aster Judgment 10s/16s, Ember 20s fire ground + Final Ignition beam.')
    print('Run: npx tsc --noEmit ; npm run build')
    return 0

if __name__=='__main__': sys.exit(main())
