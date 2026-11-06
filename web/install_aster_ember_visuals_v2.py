#!/usr/bin/env python3
"""Install Aster Judgment visual upgrade + Ember Final Ignition gather visuals.

Place this beside web/package.json and run:
  py install_aster_ember_visuals_v2.py

This installer targets the user's 2026-11-06 latest source snapshot (pre-Aster/Ember patch)
and applies both the gameplay changes and the newer visual polish in one pass.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import shutil, sys

ROOT = Path(__file__).resolve().parent
FILES = ['src/game/kits.ts', 'src/game/fighter.ts', 'src/game/model.ts', 'src/game/game.ts']
MARK = 'ASTER_EMBER_VISUALS_V2_20261106'


def replace_once(s: str, old: str, new: str, name: str, count: int = 1) -> str:
    c = s.count(old)
    if c != count:
        raise RuntimeError(f'{name}: expected {count} occurrence(s) of {old[:110]!r}, found {c}. No files changed.')
    return s.replace(old, new)


def patch_kits(s: str) -> str:
    n = 'src/game/kits.ts'
    s = replace_once(s,
        '      if (element === "fire") return a({ name: "Inferno Ring", desc: "A ring of fire erupts around you.", cd: 9, type: "strike", at: "self", wind: 0.15, recover: 0.45, dmg: 165, guard: 45, knock: 6, stun: 0.5, delay: 0.1, radius: 2.8, style: "explosion", pose_w: "mh_w", pose_s: "m3_s" });',
        '''      // ASTER_EMBER_VISUALS_V2_20261106: Ember V gathers existing flames into a beam.
      if (element === "fire") return a({ name: "Absolute Combustion — Final Ignition",
        desc: "Gather nearby ground fire and active burns into a tiny white-hot sphere, then release a devastating beam.",
        cd: 16, type: "buff", mode: "ember_ignition", wind: 0.55, active: 0.06, recover: 0.64,
        pose_w: "mh_w", pose_s: "mh_s" });''', n)
    s = replace_once(s,
        '    default:\n      return a({ name: "Judgment",',
        '''    default:
      if (element === "light") return a({ name: "Judgment",
        desc: "Raise your sword, receive harmless lightning, and merge your shield into a holy lightning greatblade for 10s.",
        cd: 16, type: "buff", mode: "judgment", duration: 10,
        wind: 0.62, active: 0.06, recover: 0.30, pose_w: "judgment_raise", pose_s: "judgment_raise" });
      return a({ name: "Judgment",''', n)
    s = replace_once(s, 'const ASTER_SWINGS: Record<string, Pose> = {',
        '''const ASTER_SWINGS: Record<string, Pose> = {
  // ASTER_EMBER_VISUALS_V2_20261106: vertical sword-up casting pose.
  judgment_raise: P([-0.08, 0, -0.02], [-0.22, 0, 0], [-2.95, -0.12, 0.04], [0.1, 0, 0], [-0.32, 0.14, 0.48], [0, 0, -0.2], [-0.35, 0, 0.13], [0.31, 0, -0.13], -0.06),''', n)
    s = replace_once(s, '    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.55, dmg: 210,',
        '    // ASTER_EMBER_VISUALS_V2_20261106: charged basic creates a 20s fire patch.\n    t.heavy = a({ type: "strike", wind: 0.15, active: 0.05, recover: 0.55, dmg: 210,', n)
    s = replace_once(s, '    t.c = a({ name: "Meteor", desc: "Call a meteor down on the enemy\'s position.",',
        '    // ASTER_EMBER_VISUALS_V2_20261106: Meteor also creates a 20s fire patch.\n    t.c = a({ name: "Meteor", desc: "Call a meteor down on the enemy\'s position.",', n)
    return s


def patch_fighter(s: str) -> str:
    n = 'src/game/fighter.ts'
    s = replace_once(s, '  rageT = 0;',
        '''  rageT = 0;
  /** ASTER_EMBER_VISUALS_V2_20261106: Aster Judgment transformation timer. */
  judgmentT = 0;''', n)
    s = replace_once(s, '    this.rageT = Math.max(this.rageT - dt, 0);',
        '''    this.rageT = Math.max(this.rageT - dt, 0);
    if (this.judgmentT > 0) {
      this.judgmentT = Math.max(0, this.judgmentT - dt);
      this.hp = Math.max(1, this.hp - this.maxHp * 0.012 * dt);
    }''', n)
    s = replace_once(s, '    this.atkPower *= this.dmgMult * (this.rageT > 0 ? RAGE_MULT : 1) * this.status.dmgMult();',
        '''    this.atkPower *= this.dmgMult * (this.rageT > 0 ? RAGE_MULT : 1) * this.status.dmgMult();
    if (this.kit === "knight" && this.look.element === "light" && this.judgmentT > 0) {
      const defenseToOffense = Math.min(0.45, this.maxGuard / 100 * 0.35);
      const missingLifeBonus = Math.max(0, 1 - this.hp / Math.max(1, this.maxHp)) * 0.20;
      this.atkPower *= (1 + defenseToOffense + missingLifeBonus);
    }''', n)
    # Preserve current Veyr guard nerf by only multiplying if Judgment is active.
    s = s.replace('festivalGuardTriple ? 2 / 1.35 : 1);', 'festivalGuardTriple ? 2 / 1.35 : 1) * (this.judgmentT > 0 ? 1.5 : 1);')
    s = replace_once(s, '    // Stun rules: one stun per skill use (multi-hit skills don\'t re-stun every tick), and',
        '''    // ASTER_EMBER_VISUALS_V2_20261106: passive fire patches do not repeatedly hit-stun.
    if (a.id === "ember_ground") return this.lastCrit ? "crit" : "hit";
    // Stun rules: one stun per skill use (multi-hit skills don't re-stun every tick), and''', n)
    s = replace_once(s, '    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");',
        '''    this.model.setBarrier(this.state === S.BLOCK && this.kit === "mage");
    this.model.setJudgment(this.kit === "knight" && this.look.element === "light" && this.judgmentT > 0);''', n, 2)
    # append snapshot field safely
    snap_old = 'this.chainBindTarget ? +this.chainBindTarget.chest().z.toFixed(2) : null, +this.chainBindT.toFixed(2)];'
    snap_new = 'this.chainBindTarget ? +this.chainBindTarget.chest().z.toFixed(2) : null, +this.chainBindT.toFixed(2), +this.judgmentT.toFixed(2)];'
    s = replace_once(s, snap_old, snap_new, n)
    restore_old = '      this.chainBindT = s[37] ?? 0; // KAIZEN_BIND_ZX_V6: remote HUD follow-ups'
    restore_new = restore_old + '\n      this.judgmentT = s[38] ?? 0; // ASTER_EMBER_VISUALS_V2_20261106'
    s = replace_once(s, restore_old, restore_new, n)
    s = replace_once(s, '    this.chainFuryT = 0;\n    this.clashMomentum = 0;',
        '''    this.chainFuryT = 0;
    this.judgmentT = 0; this.model.setJudgment(false);
    this.clashMomentum = 0;''', n)
    s = replace_once(s, '  ko() {\n    this.releaseChainBind();',
        '''  ko() {
    this.judgmentT = 0; this.model.setJudgment(false);
    this.releaseChainBind();''', n)
    return s


def patch_model(s: str) -> str:
    n = 'src/game/model.ts'
    s = replace_once(s, '  private glaivePivot: THREE.Group | null = null;',
        '''  private glaivePivot: THREE.Group | null = null;
  /** ASTER_EMBER_VISUALS_V2_20261106: holy lightning greatblade assembled from shield parts. */
  private judgmentSword: THREE.Group | null = null;
  private judgmentOldSword: THREE.Object3D[] = [];''', n)
    s = replace_once(s, '      default: this.buildSword(); this.buildShield();\n    }',
        '''      default: this.buildSword(); this.buildShield();
    }
    if (this.kit === "knight" && this.look.element === "light") this.buildJudgmentSword();''', n)
    s = replace_once(s, '  private buildShield() {',
        '''  /** ASTER_EMBER_VISUALS_V2_20261106: forged shield-sword used during Judgment. */
  private buildJudgmentSword() {
    const grip = this.bladeBase.parent;
    if (!grip) return;
    this.judgmentOldSword = grip.children.filter(c => c !== this.bladeBase && c !== this.bladeTip);
    const weapon = pivot(grip);
    // core greatblade silhouette
    mesh(weapon, box(0.18, 1.28, 0.075), this.steel(), [0, 0.82, 0]);
    mesh(weapon, cyl(0, 0.09, 0.34, 4), this.steel(), [0, 1.60, 0], [0, 0, PI / 4], [1.18, 1, 0.6]);
    mesh(weapon, box(0.03, 1.42, 0.08), this.glowMat, [0, 0.80, 0.028]);
    mesh(weapon, box(0.78, 0.085, 0.15), this.tn(this.look.trim), [0, 0.24, 0]);
    mesh(weapon, box(0.34, 0.40, 0.18), this.tn(this.look.shield), [0, 0.34, 0]);
    // shield plates latched onto the sides of the blade
    for (const side of [-1, 1]) {
      mesh(weapon, box(0.20, 0.44, 0.07), this.tn(this.look.shield), [side * 0.30, 0.42, 0], [0, 0, side * 0.48]);
      mesh(weapon, box(0.15, 0.32, 0.06), this.tn(this.look.trim), [side * 0.23, 0.70, 0], [0, 0, side * 0.24]);
      mesh(weapon, box(0.03, 0.48, 0.08), this.glowMat, [side * 0.19, 0.50, 0.055], [0, 0, side * 0.38]);
      mesh(weapon, sphere(0.042, 10), this.gem(), [side * 0.37, 0.25, 0.045]);
    }
    // lightning core + pommel flare
    mesh(weapon, sphere(0.09, 12), this.gem(), [0, 0.31, 0.09]);
    mesh(weapon, box(0.07, 0.24, 0.12), this.tn(this.look.trim), [0, -0.02, 0]);
    mesh(weapon, cyl(0.06, 0.02, 0.16, 6), this.gem(), [0, -0.16, 0], [0, 0, PI / 6]);
    weapon.visible = false;
    this.judgmentSword = weapon;
  }

  setJudgment(on: boolean) {
    if (!this.judgmentSword) return;
    this.judgmentSword.visible = on;
    for (const part of this.judgmentOldSword) part.visible = !on;
    this.shieldNode.visible = !on;
    this.bladeTip.position.y = on ? 1.72 : 1.05;
    if (this.vrmRig) this.vrmRig.shield = !on;
  }

  private buildShield() {''', n)
    return s


def patch_game(s: str) -> str:
    n = 'src/game/game.ts'
    s = replace_once(s, '  private kaizenGuardContacts = new WeakMap<Fighter, WeakMap<Entity, number>>();',
        '''  private kaizenGuardContacts = new WeakMap<Fighter, WeakMap<Entity, number>>();
  // ASTER_EMBER_VISUALS_V2_20261106: persistent Ember ground fire + brief beam meshes.
  private emberPatches: { ownerId: number; pos: THREE.Vector3; radius: number; ttl: number; tick: number; visual: THREE.Group }[] = [];
  private emberBeams: { visual: THREE.Group; ttl: number; max: number }[] = [];''', n)
    s = replace_once(s, '    this.bloodFestivals = [];\n    this.timers = [];',
        '''    this.bloodFestivals = [];
    for (const p of this.emberPatches) this.scene.remove(p.visual);
    this.emberPatches = [];
    for (const b of this.emberBeams) this.scene.remove(b.visual);
    this.emberBeams = [];
    this.timers = [];''', n)
    s = replace_once(s, '    this.updateBloodFestivals(dt);',
        '''    this.updateBloodFestivals(dt);
    this.updateEmberFire(dt);''', n)
    s = replace_once(s, '      case "bubble": { const e = this.entities.get(a[0]); if (e) fx.bubble(e.root, a[1]); break; }',
        '''      case "bubble": { const e = this.entities.get(a[0]); if (e) fx.bubble(e.root, a[1]); break; }
      case "emberPatch": this.emberPatchVisual(a[0], v3(a[1]), a[2], a[3]); break;
      case "emberConsume": this.emberConsumeVisual(a[0], v3(a[1]), a[2]); break;
      case "emberBeam": this.emberBeamVisual(v3(a[0]), v3(a[1])); break;''', n)
    s = replace_once(s, '        this.impactFx(a, at, color, a.radius);',
        '''        this.impactFx(a, at, color, a.radius);
        if (f.look.element === "fire" && f.kit === "mage" && (a.id === "heavy" || a.id === "c") && i === 0) {
          this.spawnEmberPatch(f, at, a.id === "c" ? 2.1 : 1.45);
        }''', n)
    s = replace_once(s,
        '    this.snd(a.mode === "heal" ? "heal" : a.mode === "rage" ? "rage" : "ward", 0.7);',
        '''    this.snd(a.mode === "heal" ? "heal" : a.mode === "rage" ? "rage"
      : a.mode === "judgment" ? "cast" : a.mode === "ember_ignition" ? "fireball" : "ward", 0.7);''', n)
    s = replace_once(s, '    } else if (a.mode === "blood_festival") {\n      this.startBloodFestival(f, a);',
        '''    } else if (a.mode === "judgment" && f.kit === "knight" && f.look.element === "light") {
      f.judgmentT = a.duration;
      f.guard = Math.min(f.guard, f.maxGuard * 0.5);
      f.model.setJudgment(true);
      const sword = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("lightning", sword, "#d8eaff");
      this.fxp("flash", sword, "#fff5c2", 1.6, 0.34, 1.0);
      this.fxp("sparks", sword, "#f0e9a3", 56, 6);
      this.fxp("ring", f.root.position.clone(), "#ffe7a3", 2.0, 0.46, 0.9);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 1, 0)), "JUDGMENT", "#ffefac", 1.15);
    } else if (a.mode === "ember_ignition" && f.kit === "mage" && f.look.element === "fire") {
      this.castEmberIgnition(f, a);
    } else if (a.mode === "blood_festival") {
      this.startBloodFestival(f, a);''', n)
    anchor = '  /** Teleport behind the target and kick, `repeat` times `interval` apart (alternating sides). */'
    insert = '''  /** ASTER_EMBER_VISUALS_V2_20261106: fire persists 20s and can be gathered by Final Ignition. */
  private spawnEmberPatch(owner: Fighter, pos: THREE.Vector3, radius: number) {
    const own = this.emberPatches.filter(p => p.ownerId === owner.id);
    if (own.length >= 5) this.fxp("emberConsume", owner.id, own[0].pos.clone(), 0.01);
    this.fxp("emberPatch", owner.id, pos.clone(), radius, 20);
  }

  private emberPatchVisual(ownerId: number, pos: THREE.Vector3, radius: number, ttl: number) {
    const root = new THREE.Group();
    root.position.copy(pos).y += 0.045;
    const pool = new THREE.Mesh(new THREE.CircleGeometry(radius * 0.88, 32),
      new THREE.MeshBasicMaterial({ color: "#ff601c", side: THREE.DoubleSide, transparent: true, opacity: 0.34, depthWrite: false }));
    pool.rotation.x = -Math.PI / 2;
    root.add(pool);
    const edge = new THREE.Mesh(new THREE.RingGeometry(radius * 0.82, radius, 32),
      new THREE.MeshBasicMaterial({ color: "#ffcc55", side: THREE.DoubleSide, transparent: true, opacity: 0.74, depthWrite: false }));
    edge.rotation.x = -Math.PI / 2;
    edge.position.y = 0.018;
    root.add(edge);
    this.scene.add(root);
    this.emberPatches.push({ ownerId, pos: pos.clone(), radius, ttl, tick: 1, visual: root });
  }

  /** Flames visibly stream up from each patch toward the caster like a ritual charge-up. */
  private emberConsumeVisual(ownerId: number, center: THREE.Vector3, radius: number) {
    this.emberPatches = this.emberPatches.filter(p => {
      if (p.ownerId !== ownerId || p.pos.distanceTo(center) > radius) return true;
      const start = p.pos.clone().add(new THREE.Vector3(0, 0.08, 0));
      const streams = 7;
      for (let i = 0; i < streams; i++) {
        const t = i / Math.max(1, streams - 1);
        const from = start.clone().add(new THREE.Vector3((Math.random() - 0.5) * p.radius * 0.5, 0, (Math.random() - 0.5) * p.radius * 0.5));
        const to = center.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.18, 1.25 + t * 0.35, (Math.random() - 0.5) * 0.18));
        this.emberBeamVisual(from, to, 0.12 + Math.random() * 0.04, "#ff9c32", "#fff3c9", 0.28);
      }
      this.scene.remove(p.visual);
      return false;
    });
  }

  private emberBeamVisual(from: THREE.Vector3, to: THREE.Vector3, shellR = 0.35, shellColor = "#ff8f33", coreColor = "#fff9d9", ttl = 0.38) {
    const length = Math.max(0.1, from.distanceTo(to));
    const direction = to.clone().sub(from).normalize();
    const root = new THREE.Group();
    root.position.copy(from).add(to).multiplyScalar(0.5);
    root.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
    const shell = new THREE.Mesh(new THREE.CylinderGeometry(shellR, shellR * 1.18, length, 14, 1, true),
      new THREE.MeshBasicMaterial({ color: shellColor, transparent: true, opacity: 0.55, depthWrite: false, side: THREE.DoubleSide }));
    const core = new THREE.Mesh(new THREE.CylinderGeometry(shellR * 0.40, shellR * 0.64, length, 12, 1, true),
      new THREE.MeshBasicMaterial({ color: coreColor, transparent: true, opacity: 0.95, depthWrite: false, side: THREE.DoubleSide }));
    root.add(shell, core);
    this.scene.add(root);
    this.emberBeams.push({ visual: root, ttl, max: ttl });
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
        const height = Math.abs(diff.y); diff.y = 0;
        if (diff.length() > p.radius + enemy.radius * 0.3 || height > 1.5) continue;
        const fire: Attack = { ...owner.attacks.heavy, id: "ember_ground", type: "strike", dmg: 26, guard: 5, knock: 0, stun: 0, heavy: false, effect: "burn", effect_t: 3, effect_p: 18, no_parry: true };
        const dir = diff.lengthSq() > 0.01 ? diff.normalize() : new THREE.Vector3(0, 0, 1);
        this.applyHit(owner, enemy, fire, 1, enemy.chest(), dir, true);
      }
    }
    this.emberPatches = this.emberPatches.filter(p => p.ttl > 0);
  }

  private castEmberIgnition(f: Fighter, a: Attack) {
    const pos = f.root.position.clone();
    const burned = this.enemiesOf(f).filter((e): e is Fighter | Mob =>
      (e instanceof Fighter || e instanceof Mob) && !e.isDown() && e.root.position.distanceTo(pos) <= 9 && e.status.has("burn"));
    const patches = this.emberPatches.filter(p => p.ownerId === f.id && p.pos.distanceTo(pos) <= 9);
    const consumedPatches = patches.length;
    const consumedBurns = burned.length;
    const start = f.model.castPoint.getWorldPosition(new THREE.Vector3());
    const orb = start.clone().add(new THREE.Vector3(0, 0.15, 0));
    if (consumedPatches) this.fxp("emberConsume", f.id, pos, 9);
    for (const enemy of burned) {
      const from = enemy.chest();
      this.emberBeamVisual(from, orb, 0.10, "#ff7130", "#ffe3b0", 0.24);
      enemy.status.consume("burn");
    }
    const bonus = Math.min(5, consumedPatches) * 55 + Math.min(4, consumedBurns) * 45;
    // tiny white-hot sphere gathers at the staff tip before release
    this.fxp("flash", orb, "#fffef0", 0.95, 0.26, 1.0);
    this.fxp("sparks", orb, "#ffcf63", 60, 7);
    this.fxp("ring", f.root.position.clone(), "#ffb55e", 1.4, 0.28, 0.8);
    const toward = f.opponent && !f.opponent.isDown() ? f.opponent.chest().sub(start).normalize() : new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
    const end = start.clone().addScaledVector(toward, 11);
    this.emberBeamVisual(start, end, 0.42, "#ff8f33", "#fff9d9", 0.40);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), `FINAL IGNITION +${bonus}`, "#fff1b1", 1.1);
    this.snd("fireball", 0.95);
    const beamHit: Attack = { ...a, type: "strike", dmg: 320 + bonus, guard: 75, knock: 7, stun: 0.75, heavy: true, effect: "burn", effect_t: 4, effect_p: 30, no_parry: true };
    for (const enemy of this.enemiesOf(f)) {
      const rel = enemy.chest().sub(start);
      const projection = rel.dot(toward);
      if (projection < 0 || projection > 11) continue;
      const off = rel.addScaledVector(toward, -projection).length();
      if (off > 0.8 + enemy.radius) continue;
      this.applyHit(f, enemy, beamHit, f.atkPower, enemy.chest(), toward, true);
    }
  }

'''
    s = replace_once(s, anchor, insert + anchor, n)
    return s


def main() -> int:
    if not (ROOT / 'package.json').exists():
        print('ERROR: put this Python file inside your web folder beside package.json', file=sys.stderr)
        return 1
    for rel in FILES:
        if not (ROOT / rel).exists():
            print(f'ERROR: missing {rel}', file=sys.stderr)
            return 1
    originals = {rel: (ROOT / rel).read_text(encoding='utf-8') for rel in FILES}
    if all(MARK in originals[r] for r in FILES):
        print('Already installed. Nothing changed.'); return 0
    if any(MARK in originals[r] for r in FILES):
        print('ERROR: partial installation markers found. Restore backups first.', file=sys.stderr); return 1
    try:
        patched = {
            'src/game/kits.ts': patch_kits(originals['src/game/kits.ts']),
            'src/game/fighter.ts': patch_fighter(originals['src/game/fighter.ts']),
            'src/game/model.ts': patch_model(originals['src/game/model.ts']),
            'src/game/game.ts': patch_game(originals['src/game/game.ts']),
        }
        for k in patched:
            patched[k] = '// ' + MARK + '\n' + patched[k]
    except Exception as e:
        print('ERROR:', e, file=sys.stderr)
        return 1
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for rel in FILES:
        p = ROOT / rel
        backup = p.with_name(p.name + f'.before_aster_ember_visuals_v2_{stamp}.bak')
        shutil.copy2(p, backup)
        p.write_text(patched[rel], encoding='utf-8')
        print(f'PATCH {rel} (backup: {backup.name})')
    print('DONE. Aster Judgment now has a bigger fused lightning greatblade, and Ember Final Ignition visually gathers fire patches and burns into a white-hot sphere before releasing the beam.')
    print('Run: npx tsc --noEmit && npm run build && npm run dev')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
