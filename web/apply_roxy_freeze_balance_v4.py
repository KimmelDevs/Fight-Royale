#!/usr/bin/env python3
"""Fight Royale — Roxy V4: true freeze immunity and slow, floating book, facing birds,
V Frostwing / C Glacier Meteor, shattering basic-projectile clashes, visible freeze FX.
Requires Roxy V3 (apply_roxy_frostwing_spellbook_v3.py).
Run in web/ (containing src/game/). No package installs. Backups before changes.
"""
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path.cwd()
NAMES = ['src/game/status.ts', 'src/game/fighter.ts', 'src/game/kits.ts', 'src/game/game.ts', 'src/game/model.ts', 'src/game/mobs.ts', 'src/ui/Select.tsx']
try:
    old = {name: (ROOT/name).read_text(encoding='utf-8') for name in NAMES}
except OSError as exc:
    sys.exit(f'ERROR: {exc}. Run the script from web/. No changes made.')
new = old.copy()
S, F, K, G, M, B, U = NAMES
MARK = 'ROXY_FLOATING_BOOK_FROSTWING_FREEZE_V4_20261108'
if MARK in old[G]:
    print('Roxy V4 already installed. Nothing changed.')
    sys.exit(0)
if 'ROXY_FROSTWING_SPELLBOOK_V3_20261108' not in old[G]:
    sys.exit('ERROR: Install Roxy V3 first. No changes made.')

def one(path, source, replacement):
    count = new[path].count(source)
    if count != 1:
        raise RuntimeError(f'{path}: expected one anchor, found {count}: {source[:95]!r}. No files changed.')
    new[path] = new[path].replace(source, replacement, 1)

def append_before(path, anchor, block):
    one(path, anchor, block + '\n' + anchor)

try:
    # Freeze: no repeated freeze, 4 seconds immunity after thawing; automatic 2-second slow.
    one(S, '  private m = new Map<StatusKind, Active>();', '''  private m = new Map<StatusKind, Active>();
  // ROXY_FLOATING_BOOK_FROSTWING_FREEZE_V4_20261108: immunity starts AFTER thawing.
  private freezeImmuneT = 0;
  freezeImmunityRemaining() { return this.freezeImmuneT; }''')
    one(S, '  apply(kind: StatusKind, t: number, p: number, src: unknown = null) {\n    if (src) this.src = src;', '''  apply(kind: StatusKind, t: number, p: number, src: unknown = null): boolean {
    // Incoming Freeze may damage, but cannot refresh, chain, or bypass thaw immunity.
    if (kind === "freeze" && (this.m.has("freeze") || this.freezeImmuneT > 0)) return false;
    if (src) this.src = src;''')
    one(S, '''    this.syncMask();
  }

  has(kind: StatusKind)''', '''    this.syncMask();
    return true;
  }

  has(kind: StatusKind)''')
    one(S, '  clear() { this.m.clear(); this.mask = 0; this.src = null; }', '  clear() { this.m.clear(); this.mask = 0; this.src = null; this.freezeImmuneT = 0; }')
    one(S, '  /** Movement multiplier (slow, paralyze). */', '''  /** Slow also affects attack animation and the casting/wind-up of skills. */
  actionSpeedMult() {
    if (this.m.has("freeze")) return 0;
    return this.m.get("slow")?.p ?? 1;
  }

  /** Movement multiplier (slow, paralyze). */''')
    one(S, '''  slow: { label: "SLOWED", color: "#7fc8ff", bit: 16, text: (t, p) => `Slow: -${Math.round((1 - p) * 100)}% speed for ${t}s` },''', '''  slow: { label: "SLOWED", color: "#7fc8ff", bit: 16, text: (t, p) => `Slow: -${Math.round((1 - p) * 100)}% movement, attack and cast speed for ${t}s` },''')
    one(S, '''    const dots: { kind: StatusKind; dmg: number }[] = [];
    let jolt = false;
    for (const [kind, s] of this.m) {''', '''    const dots: { kind: StatusKind; dmg: number }[] = [];
    let jolt = false;
    let thawed = false;
    this.freezeImmuneT = Math.max(0, this.freezeImmuneT - dt);
    for (const [kind, s] of this.m) {''')
    one(S, '''      if (s.t <= 0) this.m.delete(kind);
    }
    this.syncMask();''', '''      if (s.t <= 0) {
        this.m.delete(kind);
        if (kind === "freeze") thawed = true;
      }
    }
    if (thawed) {
      // 4s total re-freeze lockout, beginning at thaw; 2s of 35% slow.
      this.freezeImmuneT = 4.0;
      this.apply("slow", 2.0, 0.65, this.src);
    }
    this.syncMask();''')

    # All fighter action animations (normal attacks and skill casts) follow active Slow even mid-animation.
    one(F, '''    this.stateT += advancing * (slowedKaizenSpin ? this.kaizenSpinSpeed : 1);''', '''    // Roxy Freeze V4: Slow changes combat clocks, not cooldown timers or hitstun recovery.
    const frostActionScale = (this.state === S.ATTACK || this.state === S.CHARGE)
      ? this.status.actionSpeedMult() : 1;
    this.stateT += advancing * (slowedKaizenSpin ? this.kaizenSpinSpeed : 1) * frostActionScale;''')
    # Slow should also impact survival enemy windup and attack tempo.
    one(B, '    this.stateT += dt;\n    this.cdT -= dt;', '    this.stateT += dt * this.status.actionSpeedMult();\n    this.cdT -= dt * this.status.actionSpeedMult();')
    # Improve passive accounting: ignore freeze-immune targets, avoid false FROZEN labels.
    one(G, '''      if (attacker.frostShardStacks === 0) {
        d.status.apply("freeze", 2, 0, attacker);
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.85, 0)), "FROZEN 2s", "#c5f6ff", 0.9);
        this.fxp("motes", d.chest(), "#cef6ff", 15);
      } else {''', '''      if (attacker.frostShardStacks === 0) {
        // Four real successful hits earn a Freeze attempt; immunity rejects it.
        if (d.status.apply("freeze", 2, 0, attacker)) this.roxyFreezeBurst(d);
        else this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.65, 0)), "ICE RESIST", "#b6e8fb", 0.55);
      } else {''')
    # X auto-freeze is applied in Fighter.receiveHit; show floating text on transition only.
    one(G, '''    if (d instanceof Fighter && attacker) d.setImpactSource(attacker.root.position);
    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);''', '''    if (d instanceof Fighter && attacker) d.setImpactSource(attacker.root.position);
    const wasFrozen = (d instanceof Fighter || d instanceof Mob) && d.status.has("freeze");
    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);
    if (a.effect === "freeze" && !wasFrozen && (d instanceof Fighter || d instanceof Mob) &&
        d.status.has("freeze") && ["hit", "crit", "ko"].includes(result)) this.roxyFreezeBurst(d);''')
    # FX: persistent low-cost translucent ice around frozen fighters/mobs, plus text on first freeze.
    one(G, '  private frostAegisVisuals = new Map<number, THREE.Group>();', '''  private frostAegisVisuals = new Map<number, THREE.Group>();
  private roxyFrozenVisuals = new Map<number, THREE.Group>();''')
    one(G, '''    for (const x of this.frostAegisVisuals.values()) this.scene.remove(x);
    this.frostAegisVisuals.clear();''', '''    for (const x of this.frostAegisVisuals.values()) this.scene.remove(x);
    this.frostAegisVisuals.clear();
    for (const x of this.roxyFrozenVisuals.values()) {
      this.scene.remove(x);
      x.traverse(obj => { const m = obj as THREE.Mesh; if (m.isMesh) { m.geometry.dispose();
        for (const mat of Array.isArray(m.material) ? m.material : [m.material]) mat.dispose(); } });
    }
    this.roxyFrozenVisuals.clear();''')
    one(G, '    this.statusFx(dt);', '    this.statusFx(dt);\n    this.updateRoxyFreezeVisuals(dt);')
    append_before(G, '  private statusT = new Map<Entity, number>();', '''  // Roxy Freeze V4: frozen effect is synced via StatusSet bitmask and reuses its meshes.
  private roxyFreezeBurst(e: Fighter | Mob) {
    const at = e.chest();
    this.fxp("num", at.clone().add(new THREE.Vector3(0, 0.70, 0)), "FROZEN", "#e0faff", 1.0);
    this.fxp("flash", at, "#d6f8ff", 0.6, 0.18, 0.8);
    this.fxp("motes", at, "#ddfcff", 20);
    this.fxp("ring", e.root.position.clone(), "#aceeff", 1.15, 0.30, 0.9);
  }

  private updateRoxyFreezeVisuals(dt: number) {
    const alive = new Set<number>();
    for (const e of [...this.fighters, ...this.mobs] as (Fighter | Mob)[]) {
      if (!e.status.has("freeze") || e.isDown() || !e.root.visible) continue;
      alive.add(e.id);
      let g = this.roxyFrozenVisuals.get(e.id);
      if (!g) {
        g = new THREE.Group();
        const ice = new THREE.MeshPhongMaterial({ color: "#c5f6ff", emissive: "#3c87bf",
          emissiveIntensity: 0.24, transparent: true, opacity: 0.36, shininess: 90,
          depthWrite: false, flatShading: true, side: THREE.DoubleSide });
        const core = new THREE.Mesh(new THREE.CylinderGeometry(0.43, 0.57, 1.6, 7, 2), ice);
        core.position.y = 0.89;
        g.add(core);
        const shardMat = new THREE.MeshPhongMaterial({ color: "#defbff", transparent: true,
          opacity: 0.70, depthWrite: false, shininess: 110 });
        for (let i = 0; i < 7; i++) {
          const a = i * Math.PI * 2 / 7;
          const shard = new THREE.Mesh(new THREE.OctahedronGeometry(0.26, 0), shardMat.clone());
          shard.scale.set(0.52, 1.9 + (i % 3) * 0.25, 0.50);
          shard.position.set(Math.cos(a) * 0.51, 0.33 + (i % 2) * 0.10, Math.sin(a) * 0.51);
          g.add(shard);
        }
        this.scene.add(g);
        this.roxyFrozenVisuals.set(e.id, g);
      }
      g.position.copy(e.root.position);
      g.rotation.y += dt * 0.22;
    }
    for (const [id, g] of this.roxyFrozenVisuals) if (!alive.has(id)) {
      const ent = this.entities.get(id);
      if (ent && (ent instanceof Fighter || ent instanceof Mob) && ent.status.has("slow"))
        this.fxp("num", ent.chest().add(new THREE.Vector3(0, 0.6, 0)), "THAWED - SLOW", "#a8deff", 0.69);
      this.scene.remove(g);
      g.traverse(obj => { const m = obj as THREE.Mesh; if (m.isMesh) { m.geometry.dispose();
        for (const mat of Array.isArray(m.material) ? m.material : [m.material]) mat.dispose(); } });
      this.roxyFrozenVisuals.delete(id);
    }
  }
''')
    one(G, '''          else if (k === "slow") this.fx.motes(feet.clone().add(jitter().setY(0)), col, 2);''', '''          else if (k === "freeze") { this.fx.motes(c.clone().add(jitter()), col, 4); this.fx.sparks(c, col, 2, 1.4); }
          else if (k === "slow") this.fx.motes(feet.clone().add(jitter().setY(0)), col, 2);''')

    # Swap C back to meteor; V is three Frostwing birds; no more resource-heavy fighter cloning.
    one(K, '''      if (element === "frost") return a({ name: "Mirror of Winter", desc: "Create an icy blue clone of the enemy fighter, with 25% of their maximum HP. The clone fights on your side until destroyed.",
        cd: 28, type: "ice_clone", wind: 0.45, recover: 0.60, pose_w: "mh_w", pose_s: "m3_s" });''', '''      if (element === "frost") return a({ name: "Frostwing Choir", desc: "Summon 3 stationary Frostwings. Each keeps facing an enemy and fires one ice shard every 2 seconds for 25 seconds.",
        cd: 25, type: "snow_puppet", style: "bird", wind: 0.35, recover: 0.45,
        dmg: 26, guard: 8, knock: 0.55, stun: 0.08, count: 3, speed: 0, radius: 0.7, duration: 25,
        pose_w: "mh_w", pose_s: "m3_s" });''')
    one(K, '''    t.c = a({ name: "Frostwing Choir", desc: "Summon 3 stationary Frostwing birds. Each fires 1 frost shard every 2 seconds for 25 seconds. Successful shard hits build Frostbite stacks.",
      cd: 25, type: "snow_puppet", style: "bird", wind: 0.35, recover: 0.45,
      dmg: 26, guard: 8, knock: 0.55, stun: 0.08, count: 3, speed: 0, radius: 0.7, duration: 25,
      pose_w: "mh_w", pose_s: "m3_s" });''', '''    t.c = a({ name: "Glacier Meteor", desc: "A huge icy meteor falls on the marked enemy position, damaging and slowing enemies in the impact area.",
      cd: 15, type: "strike", style: "meteor", wind: 0.36, recover: 0.65, dmg: 245, guard: 65, knock: 5.5, stun: 0.65,
      heavy: true, delay: 0.85, radius: 2.1, effect: "slow", effect_t: 2.0, effect_p: 0.65,
      pose_w: "mh_w", pose_s: "mh_s" });''')
    one(G, '''    this.updateIceClones(dt);''', '''    // Ice clone removed from Roxy's V: no fighter models spawned for her ultimate.''')
    one(G, '''      case "ice_clone": this.spawnIceClone(f); break;''', '''      // Ice clone superseded by lightweight stationary Frostwing summons.''')
    # Frostwing remains stationary but rotates toward opponent continuously, smoothly.
    one(G, '''        p.mesh.position.copy(p.home).add(new THREE.Vector3(0, Math.sin(p.age * 3 + p.slot) * 0.08, 0));
        p.shotCd = Math.max(0, p.shotCd - dt);''', '''        p.mesh.position.copy(p.home).add(new THREE.Vector3(0, Math.sin(p.age * 3 + p.slot) * 0.08, 0));
        if (target) {
          const look = target.chest().sub(p.pos);
          look.y = 0;
          if (look.lengthSq() > 0.001) {
            const yaw = Math.atan2(look.x, look.z);
            const turn = Math.atan2(Math.sin(yaw - p.mesh.rotation.y), Math.cos(yaw - p.mesh.rotation.y));
            p.mesh.rotation.y += turn * (1 - Math.exp(-10 * dt));
          }
        }
        p.shotCd = Math.max(0, p.shotCd - dt);''')

    # The book now floats next to Roxy's upper torso rather than mounting to the hand or head.
    one(M, '''  private gripL: THREE.Object3D | null = null;''', '''  private gripL: THREE.Object3D | null = null;
  private roxyFloatingBook: THREE.Group | null = null;''')
    one(M, '''    const b = pivot(this.hand_r, [0, 0.19, 0.22], [0.1, -0.22, 0.30]);''', '''    // Floating grimoire, not a gun: torso-mounted keeps it from following the casting hand.
    // Local -X is her right side; the book hovers beside her shoulder, spine upright.
    const b = pivot(this.torso, [-0.62, 0.20, 0.43], [-0.08, -0.28, 0.10]);
    this.roxyFloatingBook = b;''')
    one(M, '''    this.t += dt;
    // 0.64 = ordinary walking;''', '''    this.t += dt;
    if (this.roxyFloatingBook) {
      this.roxyFloatingBook.position.y = 0.20 + Math.sin(this.t * 2.4) * 0.042;
      this.roxyFloatingBook.rotation.y = -0.28 + Math.sin(this.t * 1.7) * 0.11;
      this.roxyFloatingBook.rotation.z = 0.10 + Math.sin(this.t * 2.1) * 0.035;
    }
    // 0.64 = ordinary walking;''')

    # Roxy's basic 1/2/3 are frost shard projectiles, each participates in the
    # existing swept projectile-vs-projectile collision solver and always shatters on impact.
    one(K, '''  if (element === "frost") {
    t.heavy = a({ name: "Seeking Frost",''', '''  if (element === "frost") {
    // All light bolts are individually destructible projectiles. No piercing or homing.
    for (const key of ["l1", "l2", "l3"]) {
      t[key] = { ...t[key], style: "frost_shard", pierce: false, size: 0.82 };
    }
    t.heavy = a({ name: "Seeking Frost",''')
    one(G, '''    if (!bombA && !bombB) {
      if (sa > sb * 1.75) { winner = a; loser = b; }
      else if (sb > sa * 1.75) { winner = b; loser = a; }
    }''', '''    // Roxy light basics are fragile: opposing projectiles shatter them on contact,
    // including against weak shots. All other projectile strengths remain unchanged.
    const roxyLight = (p: Projectile) => p.style === "frost_shard" &&
      (p.atk?.id === "l1" || p.atk?.id === "l2" || p.atk?.id === "l3");
    if (!bombA && !bombB && !roxyLight(a) && !roxyLight(b)) {
      if (sa > sb * 1.75) { winner = a; loser = b; }
      else if (sb > sa * 1.75) { winner = b; loser = a; }
    }''')

    # In-game preparation screen should describe the actual reworked ability slots.
    one(U, 'Tap: ice bolts - Hold: charged ice spell - Z: Snowglass Shield - X: Freezing Puppet - C: Glacier Meteor - V: Three slowing puppets',
        'Tap: breakable ice shards - Hold: 4 gently homing shards - Z: 4-hit ice shield - X: Auto-freezing Snowpuff - C: Glacier Meteor - V: 3 stationary Frostwings (25s)')

    # Keep readme marker in game file only (idempotence guard).
    one(G, '// ROXY_MANUAL_SUMMONS_BIRD_V2_20261108 — manual frost summons with handcrafted procedural meshes.',
        '// ' + MARK + '\n// ROXY_MANUAL_SUMMONS_BIRD_V2_20261108 — manual frost summons with handcrafted procedural meshes.')

except Exception as exc:
    sys.exit(f'INSTALLATION ABORTED: {exc}')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
changed = [name for name in NAMES if new[name] != old[name]]
for name in changed:
    p = ROOT / name
    backup = p.with_name(p.name + f'.before_roxy_v4_{stamp}.bak')
    backup.write_text(old[name], encoding='utf-8')
    p.write_text(new[name], encoding='utf-8')
    print(f'PATCH {name} (backup {backup.name})')
print('DONE: Roxy V4 installed. Frostwing = V; Glacier Meteor = C; book floats near shoulder; 2s Freeze -> 2s Slow, 4s re-freeze immunity.')
print('Test with: npx tsc --noEmit -p . && npm run build')
