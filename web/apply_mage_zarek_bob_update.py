#!/usr/bin/env python3
"""Fight Royale ability update — standalone installer, no external Python packages.

From your game's web folder: python apply_mage_zarek_bob_update.py
Or: python apply_mage_zarek_bob_update.py "C:/.../web"

Updates src/game/kits.ts, game.ts, ai.ts, fighter.ts; backs up originals first.
Keeps previously applied projectile-clash and skill-dodge updates intact.
"""
from __future__ import annotations
import argparse
import shutil
from datetime import datetime
from pathlib import Path
import sys

TAG = 'MARINA_RAVEN_ZAREK_BOB_ABILITIES_20261107_V1'

def replace(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected one anchor; found {n}. No files have been changed.')
    return text.replace(old, new, 1)


def patch_kits(s: str) -> str:
    s = replace(s,
        'if (element === "electric") return a({ name: "Static Field", desc: "Three lightning bolts strike all around you.", cd: 10, type: "strike", at: "self", wind: 0.12, recover: 0.5, dmg: 75, guard: 22, knock: 2, stun: 0.5, delay: 0.15, radius: 2.2, repeat: 3, interval: 0.25, style: "lightning", pose_w: "mh_w", pose_s: "m3_s" });',
        'if (element === "electric") return a({ name: "Static Field", desc: "Create a medium-sized electric circle for 5s. Enemies inside are continuously slowed and periodically jolted by paralysis; allies are unaffected.", cd: 13, type: "buff", mode: "static_field", duration: 5, radius: 3.0, wind: 0.22, recover: 0.45, pose_w: "mh_w", pose_s: "m3_s" });', 'Raven V')
    s = replace(s,
        'return a({ name: "Healing Rain", desc: "Restore 16% of your HP (25% in survival).", cd: 14, type: "buff", mode: "heal", duration: 0.25, wind: 0.2, recover: 0.4, pose_w: "mh_w", pose_s: "m3_s" });',
        'return a({ name: "Healing Water", desc: "Create a 5s healing water pool. You and allies standing inside recover 3.5% max HP every 0.6s (up to 28% per cast).", cd: 15, type: "buff", mode: "healing_water", duration: 5, radius: 2.6, wind: 0.24, recover: 0.45, pose_w: "mh_w", pose_s: "m3_s" });', 'Marina V')
    s = replace(s,
        'case "glaive":\n      return a({ name: "Arc Flash", desc: "An electrified reverse-end sweep. Gains more stagger pressure than a normal light strike.", cd: 9,\n        type: "melee", wind: 0.17, active: 0.12, recover: 0.40, dmg: 115, guard: 32, reach: 2.35,\n        knock: 3.4, stun: 0.37, style: "glaive_arc", pose_w: "gl4_w", pose_s: "gl4_s" });',
        'case "glaive":\n      return a({ name: "Thunderclap Flash", desc: "A lightning-fast straight-line glaive draw dash, inspired by an anime thunder swordsman. Travels during the active window and cuts at the end; can be blocked, parried or clashed.", cd: 12,\n        type: "melee", wind: 0.13, active: 0.21, recover: 0.48, dmg: 190, guard: 49, reach: 2.35, lunge: 38,\n        knock: 5.2, stun: 0.60, heavy: true, style: "glaive_thunderflash", pose_w: "glx_w", pose_s: "glx_turn" });', 'Zarek V')
    s = replace(s,
        'return a({ name: "Cluster Bomb", desc: "A big bomb that bursts into four blasts around where it lands.", cd: 10, type: "lob", wind: 0.2, recover: 0.4, dmg: 80, guard: 22, knock: 4, stun: 0.45, delay: 0.75, radius: 1.5, repeat: 4, interval: 0.12, style: "bomb", size: 1.6, pose_w: "throw_w", pose_s: "throw_s" });',
        'return a({ name: "Cluster Bomb", desc: "Throw a striped four-pod cluster canister. Its orange warning circle marks the full spread before the four blasts land.", cd: 10, type: "lob", wind: 0.2, recover: 0.4, dmg: 80, guard: 22, knock: 4, stun: 0.45, delay: 0.85, radius: 1.5, repeat: 4, interval: 0.12, style: "clusterbomb", size: 1.65, pose_w: "throw_w", pose_s: "throw_s" });', 'Bob V')
    s = replace(s,
        't.z = a({ name: "Bubble Ward", desc: "A bubble that absorbs every hit for 2 seconds (4 in survival).", cd: 10, type: "buff", mode: "ward", duration: 4, wind: 0.1, recover: 0.25, pose_w: "mh_w", pose_s: "m3_s" });',
        't.z = a({ name: "Bubble Ward", desc: "A protective water bubble lasting 8 seconds in all modes.", cd: 13, type: "buff", mode: "ward", duration: 8, wind: 0.1, recover: 0.25, pose_w: "mh_w", pose_s: "m3_s" });', 'Marina Z')
    return '// ' + TAG + '\n' + s


POOL_DECLARATIONS = r'''
/** MARINA_RAVEN_ZAREK_BOB_ABILITIES_20261107_V1: visible persistent support / control circles. */
interface MagicPool {
  id: number; kind: "healing_water" | "static_field"; owner: Fighter | null;
  team: number; center: THREE.Vector3; radius: number;
  time: number; age: number; nextPulse: number; visual: THREE.Group;
}

function makeMagicPoolVisual(kind: MagicPool["kind"], radius: number): THREE.Group {
  const g = new THREE.Group();
  const electric = kind === "static_field";
  const main = electric ? "#9368ff" : "#4ad9ff";
  const edge = electric ? "#e5c4ff" : "#c8fbff";
  const floor = new THREE.Mesh(new THREE.CircleGeometry(radius, 64),
    new THREE.MeshBasicMaterial({ color: main, transparent: true, opacity: electric ? 0.15 : 0.21,
      depthWrite: false, side: THREE.DoubleSide }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = 0.025;
  g.add(floor);
  for (const [r, thickness, y, tint] of [
    [radius, 0.055, 0.08, main],
    [radius * 0.80, 0.026, 0.095, edge],
    [radius * 0.47, 0.020, 0.105, main]
  ] as [number, number, number, string][]) {
    const circle = new THREE.Mesh(new THREE.TorusGeometry(r, thickness, 6, 64),
      new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.84, depthWrite: false }));
    circle.rotation.x = Math.PI / 2; circle.position.y = y; g.add(circle);
  }
  for (let i = 0; i < 12; i++) {
    const angle = i * Math.PI * 2 / 12;
    const r = radius * (electric ? 0.91 : 0.72);
    const sparkle = new THREE.Mesh(electric
      ? new THREE.OctahedronGeometry(0.065, 0)
      : new THREE.SphereGeometry(0.07, 7, 5),
      new THREE.MeshBasicMaterial({ color: i % 3 ? main : edge, transparent: true, opacity: 0.95 }));
    sparkle.position.set(Math.cos(angle) * r, electric ? 0.18 : 0.13, Math.sin(angle) * r);
    sparkle.name = "poolSpark"; g.add(sparkle);
  }
  return g;
}
'''

POOL_METHODS = r'''  /** Real host-owned fields. Visual and end events are mirrored to online guests. */
  private spawnMagicPool(f: Fighter, a: Attack) {
    const kind = a.mode as MagicPool["kind"];
    const center = f.root.position.clone();
    if (!this.plat) center.y = 0;
    const radius = a.radius;
    const id = this.nextId++;
    const visual = makeMagicPoolVisual(kind, radius);
    visual.position.copy(center);
    this.scene.add(visual);
    this.magicPools.push({ id, kind, owner: f, team: f.team, center, radius,
      time: a.duration, age: 0, nextPulse: 0.6, visual });
    this.emit(["magicPool", id, kind, center.toArray(), radius, a.duration, f.id, f.team]);
    const el = kind === "static_field";
    this.fxp("ring", center, el ? "#ac84ff" : "#65dcff", radius, 0.38, 0.82);
    this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)),
      el ? "STATIC FIELD" : "HEALING WATER", el ? "#d4a8ff" : "#7beaff", 0.88);
    this.snd(el ? "zap" : "heal", 0.7);
  }

  private updateMagicPools(dt: number) {
    for (const pool of [...this.magicPools]) {
      pool.time -= dt;
      pool.age += dt;
      pool.visual.rotation.y += dt * (pool.kind === "static_field" ? 0.42 : -0.21);
      pool.visual.scale.setScalar(1 + Math.sin(pool.age * (pool.kind === "static_field" ? 5.4 : 2.8)) * 0.012);
      for (let i = 0; i < pool.visual.children.length; i++) {
        const spark = pool.visual.children[i];
        if (spark.name !== "poolSpark") continue;
        spark.position.y = 0.14 + 0.09 * Math.sin(pool.age * 4 + i * 0.9);
      }
      if (this.cfg.role !== "client" && pool.owner && !pool.owner.isDown()) {
        pool.nextPulse -= dt;
        if (pool.nextPulse <= 0) {
          const water = pool.kind === "healing_water";
          pool.nextPulse += water ? 0.6 : 0.4;
          for (const e of this.entities.values()) {
            if (e.isDown() || (water ? e.team !== pool.team : e.team === pool.team)) continue;
            const dx = e.root.position.x - pool.center.x;
            const dz = this.plat ? 0 : e.root.position.z - pool.center.z;
            if (Math.hypot(dx, dz) > pool.radius + e.radius * 0.28 ||
                Math.abs(e.root.position.y - pool.center.y) > 1.6) continue;
            if (water) {
              if (!(e instanceof Fighter) || e.hp >= e.maxHp) continue;
              const amount = Math.min(e.maxHp - e.hp, e.maxHp * 0.035);
              e.heal(amount);
              this.fxp("splash", e.chest(), 5, 0.45, "#77e9ff");
              this.fxp("num", e.chest().add(new THREE.Vector3(0, 0.55, 0)),
                `+${Math.round(amount)}`, "#b6faff", 0.56);
            } else if (e instanceof Fighter || e instanceof Mob) {
              // Real paralysis while standing inside. Status's normal jolt timing
              // still applies; leaving the circle frees the target in <=0.75s.
              e.status.apply("paralyze", 0.75, 0, pool.owner);
              this.fxp("sparks", e.chest(), "#cda2ff", 6, 2.4);
            }
          }
        }
      }
      if (pool.time <= 0 || (this.cfg.role !== "client" && (!pool.owner || pool.owner.isDown()))) {
        this.scene.remove(pool.visual);
        this.magicPools = this.magicPools.filter(p => p !== pool);
        if (this.cfg.role !== "client") this.emit(["magicPoolEnd", pool.id]);
      }
    }
  }

'''

CLUSTER_MODEL = r'''  if (style === "clusterbomb") {
    // Bright segmented four-pod canister, intentionally NOT the round black bomb.
    const shell = new THREE.MeshLambertMaterial({ color: "#f3a72f", emissive: "#6b2500", emissiveIntensity: 0.24 });
    const dark = new THREE.MeshLambertMaterial({ color: "#32313a" });
    const stripe = new THREE.MeshBasicMaterial({ color: "#ffed75" });
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.17 * size, 0.17 * size, 0.34 * size, 8), shell);
    core.rotation.x = Math.PI / 2;
    g.add(core);
    for (const z of [-0.13, 0.13]) {
      const band = new THREE.Mesh(new THREE.CylinderGeometry(0.175 * size, 0.175 * size, 0.05 * size, 8), dark);
      band.rotation.x = Math.PI / 2; band.position.z = z * size; g.add(band);
    }
    for (let i = 0; i < 4; i++) {
      const angle = i * Math.PI / 2;
      const pod = new THREE.Mesh(new THREE.SphereGeometry(0.103 * size, 9, 7), i % 2 ? dark : shell);
      pod.position.set(Math.cos(angle) * 0.225 * size, Math.sin(angle) * 0.225 * size, 0);
      g.add(pod);
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.04 * size, 8, 5), stripe);
      eye.position.copy(pod.position).multiplyScalar(1.35);
      g.add(eye);
    }
    const beacon = new THREE.Mesh(new THREE.OctahedronGeometry(0.085 * size, 0), glow);
    beacon.position.z = 0.23 * size;
    beacon.name = "clusterBeacon";
    g.add(beacon);
    return;
  }
'''

THUNDER_METHOD = r'''  /** Zarek's fast straight-line thunder draw: real fighter motion, one timed blade hit. */
  private zarekThunderflash(f: Fighter, a: Attack) {
    const serial = f.swingSerial, round = this.round;
    const color = "#67dfff";
    const start = f.root.position.clone();
    this.fxp("flash", f.chest(), "#e8ffff", 0.92, 0.15, 0.96);
    this.fxp("ring", start, color, 1.12, 0.23, 0.86);
    this.fxp("sparks", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), color, 35, 8);
    this.snd("zap", 0.84);
    for (const t of [0.045, 0.09, 0.145, 0.185]) {
      this.laterCombo(f, t, () => {
        if (round !== this.round || f.isDown() || f.swingSerial !== serial ||
            f.state !== S.ATTACK || f.atk?.style !== "glaive_thunderflash") return;
        const spot = f.root.position.clone();
        this.fxp("slashes", spot.clone().add(new THREE.Vector3(0, 0.8, 0)), color);
        this.fxp("sparks", spot.clone().add(new THREE.Vector3(0, 0.65, 0)), "#a9f5ff", 13, 7);
        if (t === 0.185) {
          this.fxp("flash", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), "#ffffff", 0.85, 0.12, 0.95);
          this.melee(f, a); // Standard block/parry/clash hit confirmation.
          this.snd("swing_heavy", 0.78);
        }
      });
    }
  }

'''


def patch_game(s: str) -> str:
    # Add state and visual helper at stable anchors.
    s = replace(s, '  gravity = 0;\n  constructor(id: number',
        '  gravity = 0;\n  /** Actual landing-warning marker for Bob\'s cluster canister. */\n  clusterMarkId: number | null = null;\n  constructor(id: number', 'Projectile warning id')
    s = replace(s, 'const BOMB_GRAVITY = 16;', POOL_DECLARATIONS + '\nconst BOMB_GRAVITY = 16;', 'Pool visuals/types')
    s = replace(s, 'function buildProjectile(g: THREE.Group, style: string, element: string, size: number, color: string) {\n  const glow = new THREE.MeshBasicMaterial({ color });',
        'function buildProjectile(g: THREE.Group, style: string, element: string, size: number, color: string) {\n  const glow = new THREE.MeshBasicMaterial({ color });\n' + CLUSTER_MODEL.rstrip('\n'), 'Cluster model')
    s = replace(s, '  private bloodFestivals: BloodFestival[] = [];',
        '  private bloodFestivals: BloodFestival[] = [];\n  private magicPools: MagicPool[] = [];', 'Pool state')
    s = replace(s, '    this.bloodFestivals = [];\n    for (const p of this.emberPatches)',
        '    this.bloodFestivals = [];\n    for (const pool of this.magicPools) this.scene.remove(pool.visual);\n    this.magicPools = [];\n    for (const p of this.emberPatches)', 'Pool cleanup')
    s = replace(s, '    this.updateBloodFestivals(dt);\n    this.updateEmberFire(dt);',
        '    this.updateBloodFestivals(dt);\n    this.updateMagicPools(dt);\n    this.updateEmberFire(dt);', 'Pool heartbeat')
    s = replace(s, '    strikes: () => this.strikeMarks,',
        '    strikes: () => this.strikeMarks,\n    fields: (f: Fighter) => this.magicPools.filter(p => p.kind === "static_field" && p.team !== f.team && p.time > 0)\n      .map(p => ({ id: p.id, center: p.center, radius: p.radius })),', 'AI field threat feed')
    s = replace(s, '    if (f.kit === "glaive" && ["glaive_cyclone", "glaive_serpent", "glaive_phantom", "glaive_infinite"].includes(a.style)) {',
        '    if (f.kit === "glaive" && a.style === "glaive_thunderflash") {\n      this.zarekThunderflash(f, a);\n      return;\n    }\n    if (f.kit === "glaive" && ["glaive_cyclone", "glaive_serpent", "glaive_phantom", "glaive_infinite"].includes(a.style)) {', 'Zarek combat dispatch')
    s = replace(s, '  /** VEYR_BLOODLUST_CARRION_V7 — five REAL melee windows, not circular area damage. */',
        THUNDER_METHOD + '  /** VEYR_BLOODLUST_CARRION_V7 — five REAL melee windows, not circular area damage. */', 'Zarek timed attack')
    s = replace(s, '      const p = this.spawnProjectile(f, f.team, a, f.atkPower, origin, vel, "bomb", a.element, a.size, f.look.glow, false, o);\n      p.gravity = g;',
        '      const cluster = a.style === "clusterbomb";\n      const p = this.spawnProjectile(f, f.team, a, f.atkPower, origin.clone(), vel, cluster ? "clusterbomb" : "bomb", a.element, a.size, f.look.glow, false, o);\n      if (cluster) {\n        const warning = { target: o, land: this.time + T, id: this.nextId++,\n          center: land.clone(), radius: a.radius * 1.85 + 0.22, caster: f,\n          followsCaster: false, style: "clusterbomb" };\n        this.strikeMarks.push(warning);\n        p.clusterMarkId = warning.id;\n        this.fxp("tele", land.clone(), "#ff8a26", warning.radius, T);\n        this.fxp("ring", land.clone(), "#ffd173", warning.radius * 0.85, 0.35, 0.74);\n      }\n      p.gravity = g;', 'Throw distinct cluster bomb + warning')
    s = replace(s, '    for (const p of this.projectiles) if (p.done) {\n      this.scene.remove(p.group);',
        '    for (const p of this.projectiles) if (p.done) {\n      if (p.clusterMarkId !== null)\n        this.strikeMarks = this.strikeMarks.filter(m => m.id !== p.clusterMarkId);\n      this.scene.remove(p.group);', 'Remove completed warning')
    s = replace(s, '      else if (p.style === "shuriken") p.spin.rotation.y += dt * 30;',
        '      else if (p.style === "clusterbomb") {\n        p.spin.rotation.z += dt * 6;\n        const beacon = p.spin.getObjectByName("clusterBeacon");\n        if (beacon) beacon.scale.setScalar(0.8 + 0.25 * Math.sin(p.age * 24));\n      }\n      else if (p.style === "shuriken") p.spin.rotation.y += dt * 30;', 'Cluster rotating model')
    s = replace(s, '    if (a.mode === "ward") {\n      const dur = pvp ? Math.min(a.duration, 2) : a.duration;',
        '    if (a.mode === "healing_water" || a.mode === "static_field") {\n      this.spawnMagicPool(f, a);\n    } else if (a.mode === "ward") {\n      // Marina Z is intentionally the full eight-second ward, even in PvP.\n      const dur = f.kit === "mage" && f.look.element === "water" ? a.duration\n        : (pvp ? Math.min(a.duration, 2) : a.duration);', 'Marina 8s shield and pool casts')
    s = replace(s, '  private applyBuff(f: Fighter, a: Attack) {', POOL_METHODS + '  private applyBuff(f: Fighter, a: Attack) {', 'Pool simulation')
    s = replace(s, '        if (ev[2] === "bomb") { p.gravity = BOMB_GRAVITY; p.life = 3; }',
        '        if (ev[2] === "bomb" || ev[2] === "clusterbomb") { p.gravity = BOMB_GRAVITY; p.life = 3; }', 'Client bomb gravity')
    s = replace(s, '      case "bloodFestival": {',
        '      case "magicPool": {\n        const kind = ev[2] as MagicPool["kind"];\n        const center = v3(ev[3]);\n        const visual = makeMagicPoolVisual(kind, ev[4]);\n        visual.position.copy(center);\n        this.scene.add(visual);\n        this.magicPools.push({ id: ev[1], kind, center, radius: ev[4],\n          time: ev[5], age: 0, nextPulse: 0, visual, owner: null, team: ev[7] });\n        break;\n      }\n      case "magicPoolEnd": {\n        const p = this.magicPools.find(x => x.id === ev[1]);\n        if (p) { this.scene.remove(p.visual); this.magicPools = this.magicPools.filter(x => x !== p); }\n        break;\n      }\n      case "bloodFestival": {', 'Pool online events')
    return '// ' + TAG + '\n' + s


def patch_ai(s: str) -> str:
    s = replace(s, '  strikes(): {\n    target: any; land: number; id: number;',
        '  fields(f: Fighter): { id: number; center: THREE.Vector3; radius: number }[];\n  strikes(): {\n    target: any; land: number; id: number;', 'AI field interface')
    s = replace(s, '  private strikeDecisions = new Map<number, { reactAt: number; evade: boolean; side: number }>();',
        '  private strikeDecisions = new Map<number, { reactAt: number; evade: boolean; side: number }>();\n  private staticFieldChoices = new Map<number, { reactAt: number; evade: boolean }>();', 'AI field reaction state')
    s = replace(s, '    if (this.evadeGroundStrikes(f)) return;\n    if (this.avoidKaizenSpinGuard',
        '    if (this.evadeGroundStrikes(f)) return;\n    if (this.evadeStaticField(f)) return;\n    if (this.avoidKaizenSpinGuard', 'AI field priority')
    s = replace(s, '  /** Evade REAL telegraphed strike areas (Ocean Requiem, Thunderstorm,',
        r'''  /** Do not stand in Raven's hostile persistent paralysis ring.
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

  /** Evade REAL telegraphed strike areas (Ocean Requiem, Thunderstorm,''', 'AI anti-paralysis behavior')
    s = replace(s,
        'm.style === "meteor" || m.style === "arrows";',
        'm.style === "meteor" || m.style === "arrows" || m.style === "clusterbomb";', 'AI cluster major threat')
    # AI can use changed skills rationally during loadout selection (the generic routine still gates available/cooldown).
    s = replace(s, 'if (name === "Thunderstorm") points += punish ? 2.0 : 0.35;',
        'if (name === "Thunderstorm") points += punish ? 2.0 : 0.35;\n        if (name === "Static Field") points += close && (attackComing || punish) ? 3.0 : close ? 1.4 : -1;', 'Raven AI field use')
    s = replace(s, 'if (name === "Serpent Wheel") points += blocking || close ? 1.7 : 0;',
        'if (name === "Thunderclap Flash") points += distance > 2.4 && distance < 9.5 ? 2.6 : -0.9;\n        if (name === "Serpent Wheel") points += blocking || close ? 1.7 : 0;', 'Zarek AI dash use')
    s = replace(s, 'if (name === "Ocean Requiem" && punish) points += 1.2;',
        'if (name === "Ocean Requiem" && punish) points += 1.2;\n        if (name === "Healing Water") points += f.hp < f.maxHp * 0.68 ? 3.2 : f.hp < f.maxHp * 0.86 ? 1.4 : -2.5;', 'Marina AI healing use')
    s = replace(s, 'if (name === "Paralyze Bomb")', 'if (name === "Cluster Bomb" && distance > 2.2 && distance < 9.0) points += 2.0;\n        if (name === "Paralyze Bomb")', 'Bob AI cluster use') if 'if (name === "Paralyze Bomb")' in s else s
    return '// ' + TAG + '\n' + s


def patch_fighter(s: str) -> str:
    s = replace(s,
        '      } else v += this.atk.lunge;\n    }\n    // Garrick Iron Tempest:',
        '      } else if (this.kit === "glaive" && this.atk.style === "glaive_thunderflash") {\n        // Zenitsu-like real straight-line flash: no movement during preparation.\n        // 38 m/s applies only to the short active window, stops at melee contact.\n        v += this.atkPhase === 1 ? this.atk.lunge : 0;\n      } else v += this.atk.lunge;\n    }\n    // Garrick Iron Tempest:', 'Zarek dash arena movement')
    s = replace(s,
        '        target = near ? 0 : this.facing * this.atk.lunge;\n        // Arena/platform mode:',
        '        target = near ? 0 : this.facing *\n          (this.kit === "glaive" && this.atk.style === "glaive_thunderflash" && this.atkPhase !== 1\n            ? 0 : this.atk.lunge);\n        // Arena/platform mode:', 'Zarek dash stage movement')
    s = replace(s, '        if (this.kit === "glaive" && a?.style === "glaive_phantom") {',
        '        if (this.kit === "glaive" && a?.style === "glaive_thunderflash") {\n          p = this.stateT < a.wind ? "glx_w" : this.stateT < a.wind + a.active ? "glx_turn" : "gl4_s";\n          sp = this.stateT < a.wind ? 28 : 72;\n          break;\n        }\n        if (this.kit === "glaive" && a?.style === "glaive_phantom") {', 'Zarek thunder pose')
    return '// ' + TAG + '\n' + s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('web', nargs='?', default='.', help='Path to your web game directory (default: current directory)')
    args = ap.parse_args()
    base = Path(args.web).expanduser().resolve()
    if not (base / 'src/game/game.ts').exists() and (base / 'web/src/game/game.ts').exists():
        base = base / 'web'
    patches = [('kits.ts', patch_kits), ('game.ts', patch_game), ('ai.ts', patch_ai), ('fighter.ts', patch_fighter)]
    pending = {}
    if not (base / 'src/game/game.ts').exists():
        sys.exit(f'Cannot find src/game/game.ts under {base}. Run from your game web folder.')
    for name, fn in patches:
        path = base / 'src/game' / name
        old = path.read_text(encoding='utf-8')
        if TAG in old:
            print(f'Already updated: {name}')
            continue
        pending[path] = fn(old)  # Validate all anchors before touching any files.
    if not pending:
        print('All four source files already contain this update.')
        return
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    for path, new in pending.items():
        backup = path.with_name(path.name + f'.before_mage_zarek_bob_{stamp}.bak')
        shutil.copy2(path, backup)
        temp = path.with_name(path.name + '.abilityupdate.tmp')
        temp.write_text(new, encoding='utf-8')
        temp.replace(path)
        print(f'Updated {path.relative_to(base)} (backup: {backup.name})')
    print('Complete. Marina Z: 8s; Marina V: Healing Water; Raven V: Static Field; '
          'Zarek V: Thunderclap Flash; Bob V: 3D cluster canister + landing telegraph + AI response.')
    print('Host and online guests should use the same game build.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as e:
        sys.exit(f'Installer stopped safely: {e}')
