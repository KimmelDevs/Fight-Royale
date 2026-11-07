#!/usr/bin/env python3
"""Fight Royale: Roxy Frostwing + spellbook complete rework.
Requires Roxy and apply_roxy_manual_summons_birds.py (v2).
Safe preflight, atomic-ish: writes only after every patch has matched, keeps backups.
"""
from pathlib import Path
from datetime import datetime
import re, sys

ROOT=Path.cwd()
NAMES=['src/game/kits.ts','src/game/game.ts','src/game/fighter.ts','src/game/status.ts','src/game/model.ts','src/game/mobs.ts']
try:
    original={n:(ROOT/n).read_text(encoding='utf-8') for n in NAMES}
except OSError as e:
    sys.exit(f'INSTALLATION FAILED: {e}. Run inside web/. No files changed.')
patched=original.copy()
K,G,F,S,M,B=NAMES
MARK='ROXY_FROSTWING_SPELLBOOK_V3_20261108'
if MARK in original[G]:
    print('Already installed; no files changed.')
    sys.exit(0)
if 'ROXY_MANUAL_SUMMONS_BIRD_V2_20261108' not in original[G]:
    sys.exit('INSTALLATION FAILED: Install apply_roxy_manual_summons_birds.py first. No files changed.')

def one(n,a,b):
    count=patched[n].count(a)
    if count!=1: raise ValueError(f'{n}: expected 1 anchor, got {count}: {a[:100]!r}')
    patched[n]=patched[n].replace(a,b,1)

def region(n,start,end,repl):
    x=patched[n]; begin=x.find(start)
    if begin<0 or x.count(start)!=1: raise ValueError(f'{n}: missing/duplicate start {start[:85]}')
    finish=x.find(end,begin+len(start))
    if finish<0: raise ValueError(f'{n}: missing end {end[:85]}')
    patched[n]=x[:begin]+repl+x[finish:]

try:
    # ----- kit abilities -----
    region(K, '  // ROXY_MANUAL_SUMMONS_BIRD_V2_20261108: manual-command frost summons.', '\n  if (element === "fire") {', '''  // ROXY_FROSTWING_SPELLBOOK_V3_20261108: Roxy's 4-button spellbook kit.
  if (element === "frost") {
    t.heavy = a({ name: "Seeking Frost", type: "projectile", wind: 0.24, active: 0.05, recover: 0.55,
      dmg: 57, guard: 16, knock: 1.2, stun: 0.16, speed: 13.0, size: 0.85, count: 4, spread: 0.33,
      style: "frost_shard", pose_w: "mh_w", pose_s: "mh_s" });
    t.z = a({ name: "Snowglass Aegis", desc: "Four orbiting ice crystals. Each incoming damaging hit destroys one shard and deals zero damage; lasts up to 7 seconds.",
      cd: 13, type: "buff", mode: "frost_aegis", duration: 7, wind: 0.13, recover: 0.25, pose_w: "mh_w", pose_s: "m3_s" });
    t.x = a({ name: "Frost Marionette", desc: "Summon a light-blue snow marionette that automatically rushes an enemy and FREEZES it for 2 seconds on contact.",
      cd: 10, type: "snow_puppet", style: "freeze", wind: 0.26, recover: 0.42,
      dmg: 65, guard: 20, knock: 0.7, stun: 0.08, count: 1, speed: 4.5, radius: 0.9, duration: 8.5,
      effect: "freeze", effect_t: 2.0, pose_w: "m2_w", pose_s: "m2_s" });
    t.c = a({ name: "Frostwing Choir", desc: "Summon 3 stationary Frostwing birds. Each fires 1 frost shard every 2 seconds for 25 seconds. Successful shard hits build Frostbite stacks.",
      cd: 25, type: "snow_puppet", style: "bird", wind: 0.35, recover: 0.45,
      dmg: 26, guard: 8, knock: 0.55, stun: 0.08, count: 3, speed: 0, radius: 0.7, duration: 25,
      pose_w: "mh_w", pose_s: "m3_s" });
    return t;
  }
''')
    region(K,'      if (element === "frost") return a({ name: "Snowfall Parade"', '      if (element === "fire") return a({ name:', '''      if (element === "frost") return a({ name: "Mirror of Winter", desc: "Create an icy blue clone of the enemy fighter, with 25% of their maximum HP. The clone fights on your side until destroyed.",
        cd: 28, type: "ice_clone", wind: 0.45, recover: 0.60, pose_w: "mh_w", pose_s: "m3_s" });
''')

    # ----- true freeze status: no periodic paralyze jolts -----
    one(S, '"paralyze" | "slow" | "weaken";', '"paralyze" | "slow" | "weaken" | "freeze";')
    one(S, '  weaken: { label: "WEAKENED",', '  freeze: { label: "FROZEN", color: "#c5f7ff", bit: 64, text: (t) => `Freeze: immobilized and unable to attack for ${t}s` },\n  weaken: { label: "WEAKENED",')
    one(S, '    if (this.m.has("paralyze")) k *= PARALYZE_SPEED;', '    if (this.m.has("paralyze")) k *= PARALYZE_SPEED;\n    if (this.m.has("freeze")) return 0;')

    # ----- fighter frost shield and passive fields -----
    one(F,'  wardT = 0;', '''  // ROXY_FROSTWING_SPELLBOOK_V3_20261108: actual 4-hit barrier and shard-hit freeze meter.
  frostShieldCharges = 0;
  frostShieldT = 0;
  frostShardStacks = 0;
  wardT = 0;''')
    one(F,'    this.wardT = Math.max(this.wardT - dt, 0);', '''    this.wardT = Math.max(this.wardT - dt, 0);
    this.frostShieldT = Math.max(0, this.frostShieldT - dt);
    if (this.frostShieldT === 0) this.frostShieldCharges = 0;''')
    one(F,'    if (this.wardT > 0) { this.model.recoil = 0.4; return "warded"; }', '''    if (this.look.element === "frost" && this.frostShieldT > 0 && this.frostShieldCharges > 0) {
      this.frostShieldCharges -= 1;
      this.model.recoil = 0.4;
      return "warded"; // zero HP AND guard damage, exactly one crystal spent per hit
    }
    if (this.wardT > 0) { this.model.recoil = 0.4; return "warded"; }''')
    one(F,'    const st = this.status.tick(dt, this.model.walk > 0.3);', '''    const st = this.status.tick(dt, this.model.walk > 0.3);
    if (this.status.has("freeze")) {
      this.intent.attack = false; this.intent.skill = ""; this.intent.block = false; this.intent.jump = false;
      this.intent.move.set(0, 0, 0); this.intent.dash.set(0, 0, 0);
      if (this.state !== S.HITSTUN) { this.stun = 2; this.setState(S.HITSTUN); }
      this.stun = Math.max(this.stun, this.stateT + 0.09);
      this.velY = 0; this.knock = 0;
    }''')
    # remove prior manual recast for X & V. They must cast only once.
    one(F, '''    if (this.look.element === "frost" && this.attacks[k]?.type === "snow_puppet") {
      if (![S.HITSTUN, S.STAGGER, S.KO, S.WIN].includes(this.state) && this.onSnowCommand(this, k)) return;
    }
''', '')

    # ----- mobs frozen can't run or fire -----
    one(B,'    if (this.dead) return;\n    this.stateT += dt;', '''    if (this.dead) return;
    if (this.status.has("freeze")) {
      this.state = MS.FLINCH; this.stateT = 0;
      this.windStarted = false;
      this.animate(dt);
      return;
    }
    this.stateT += dt;''')

    # ----- detailed book as Roxy weapon -----
    one(M,'      case "mage": this.buildStaff(); break;', '      case "mage": this.look.element === "frost" ? this.buildRoxySpellbook() : this.buildStaff(); break;')
    one(M,'    this.vrmRig.staff = this.kit === "mage";', '    this.vrmRig.staff = this.kit === "mage" && this.look.element !== "frost";')
    one(M,'  private buildStaff() {', '''  // ROXY_FROSTWING_SPELLBOOK_V3_20261108: three-dimensional enchanted spellbook.
  // Gold bindings, deep sapphire leather, pale layered pages and a cyan crystal crest.
  private buildRoxySpellbook() {
    const L = this.look;
    const b = pivot(this.hand_r, [0, 0.19, 0.22], [0.1, -0.22, 0.30]);
    const cover = this.tn("#17254b"), gold = this.tn("#e5ac69"), inset = this.tn("#275e88");
    const pages = this.tn("#f1f1df"), edge = this.tn("#a5dffd");
    const back = mesh(b, box(0.53, 0.66, 0.095), cover, [0, 0, 0]);
    back.rotation.y = -0.10;
    mesh(b, box(0.49, 0.62, 0.068), pages, [0.018, 0, 0.056]);
    mesh(b, box(0.51, 0.64, 0.027), cover, [0.018, 0, 0.105]);
    for (const s of [-1, 1]) {
      mesh(b, box(0.51, 0.022, 0.023), gold, [0, s * 0.303, 0.126]);
      mesh(b, box(0.023, 0.61, 0.026), gold, [s * 0.239, 0, 0.126]);
      for (const v of [-1, 1]) mesh(b, box(0.09, 0.09, 0.032), gold, [s * 0.222, v * 0.284, 0.137]);
    }
    mesh(b, box(0.085, 0.64, 0.11), inset, [-0.25, 0, 0.0]);
    for (const y of [-0.23,-0.13,0.13,0.23]) mesh(b, box(0.087, 0.018, 0.13), gold, [-0.25,y,0]);
    const seal = pivot(b, [0.018, 0.0, 0.145], [0,0,Math.PI / 4]);
    mesh(seal, box(0.23, 0.23, 0.026), gold);
    mesh(seal, box(0.16, 0.16, 0.039), inset, [0, 0, 0.02]);
    mesh(seal, sphere(0.075, 12), this.glowMat, [0, 0, 0.06]);
    for (const a of [-1,1]) mesh(b, box(0.08, 0.018, 0.025), edge, [a * 0.11, -0.22, 0.153]);
    this.bladeBase = pivot(b, [0,0.2,0.18]);
    this.bladeTip = pivot(b, [0.0,0.33,0.20]);
    this.castPoint = pivot(b, [0.0,0.33,0.27]);
    this.shieldNode = pivot(this.hand_l, [0, -0.05, 0]);
    this.barrier = pivot(this.shieldNode);
    const disc = mesh(this.barrier, cyl(0.42, 0.42, 0.012, 32), M.water(new THREE.Color(L.glow), 0.3, 1.4));
    disc.castShadow = false;
    mesh(this.barrier, torus(0.4,0.43), M.additive(L.glow,0.9)).castShadow = false;
    this.barrier.visible = false;
  }

  private buildStaff() {''')

    # ----- projectile visuals and homing with forward-only steering -----
    one(G,'  if (style === "clusterbomb") {', '''  if (style === "frost_shard") {
    const ice = new THREE.MeshPhongMaterial({ color: "#c6f3ff", emissive: "#4a9bd3", emissiveIntensity: 0.34,
      transparent: true, opacity: 0.94, shininess: 120, flatShading: true });
    const crystal = new THREE.Mesh(new THREE.OctahedronGeometry(0.19 * size, 0), ice);
    crystal.scale.set(0.64, 0.64, 1.85);
    g.add(crystal);
    const edge = new THREE.Mesh(new THREE.OctahedronGeometry(0.10 * size, 0), glow);
    edge.position.z = 0.16 * size; g.add(edge);
    return;
  }
  if (style === "clusterbomb") {''')
    # Change charged shard projectiles to homing metadata without using full aim-assist/U-turn.
    one(G,'      if (p.steering && p.target && !p.target.isDown() && p.age > (p.style === "bloodcrescent" ? 0.38 : 0)) {', '''      if (p.style === "frost_shard" && p.atk?.id === "heavy" && p.target && !p.target.isDown() && p.age < 0.9) {
        const toTarget = p.target.chest().sub(p.pos);
        if (toTarget.lengthSq() > 0.02 && p.vel.dot(toTarget) > 0) {
          const speed = p.vel.length();
          const forward = p.vel.clone().normalize();
          const desired = toTarget.normalize();
          const angle = forward.angleTo(desired);
          // Only a mild forward curve; no chasing once the shard has passed its target.
          if (angle < 1.05) {
            const step = Math.min(0.85 * dt, angle);
            p.vel.copy(forward.lerp(desired, angle > 0.001 ? step / angle : 0).normalize().multiplyScalar(speed));
          }
        }
      }
      if (p.steering && p.target && !p.target.isDown() && p.age > (p.style === "bloodcrescent" ? 0.38 : 0)) {''')

    # passive on actual damaging shard hits only
    one(G,'    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);', '''    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);
    if (attacker instanceof Fighter && attacker.look.element === "frost" && a.style === "frost_shard" &&
        ["hit", "crit"].includes(result) && (d instanceof Fighter || d instanceof Mob)) {
      attacker.frostShardStacks = (attacker.frostShardStacks + 1) % 4;
      if (attacker.frostShardStacks === 0) {
        d.status.apply("freeze", 2, 0, attacker);
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.85, 0)), "FROZEN 2s", "#c5f6ff", 0.9);
        this.fxp("motes", d.chest(), "#cef6ff", 15);
      } else {
        this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.72, 0)),
          `FROSTBITE ${attacker.frostShardStacks}/4`, "#c9f4ff", 0.54);
      }
    }''')

    # ----- Z gets four individual damage-absorb shards; never generic ward -----
    one(G,'    if (a.mode === "healing_water" || a.mode === "static_field") {', '''    if (a.mode === "frost_aegis") {
      f.frostShieldCharges = 4;
      f.frostShieldT = a.duration;
      this.fxp("ring", f.chest(), "#c6f5ff", 1.2, 0.25, 0.85);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "ICE SHARDS x4", "#dffbff", 0.84);
    } else if (a.mode === "healing_water" || a.mode === "static_field") {''')
    # Orbiting actual 3D shield shards updated every frame.
    one(G,'  private snowPuppets: SnowPuppet[] = [];', '''  private frostAegisVisuals = new Map<number, THREE.Group>();
  private snowPuppets: SnowPuppet[] = [];''')
    one(G,'    this.updateSnowPuppets(dt);', '    this.updateSnowPuppets(dt);\n    this.updateFrostAegis(dt);\n    this.updateIceClones(dt);')
    one(G,'    this.snowPuppets = [];', '''    this.snowPuppets = [];
    for (const x of this.frostAegisVisuals.values()) this.scene.remove(x);
    this.frostAegisVisuals.clear();
    for (const clone of [...this.iceClones]) this.finishIceClone(clone, false);''')
    # C summons bird; V clones
    one(G,'      case "snow_puppet": this.summonSnowPuppets(f, a); break;', '''      case "snow_puppet": this.summonSnowPuppets(f, a); break;
      case "ice_clone": this.spawnIceClone(f); break;''')

    # Frostwing birds - replace simple bird by feathered rig inspired by the provided frostwing.html.
    region(G,'function buildSnowBirdMesh(): THREE.Group {', '\nfunction buildTrap(kind: string, color: string): THREE.Group {', '''function buildSnowBirdMesh(): THREE.Group {
  // ROXY_FROSTWING_SPELLBOOK_V3_20261108: layered primaries, crest, tail, talons, glowing frost diamonds.
  const b = new THREE.Group();
  const white = new THREE.MeshLambertMaterial({ color: "#f8f8ff", side: THREE.DoubleSide });
  const cream = new THREE.MeshLambertMaterial({ color: "#d7b48e", side: THREE.DoubleSide });
  const black = new THREE.MeshLambertMaterial({ color: "#52566d", side: THREE.DoubleSide });
  const ice = new THREE.MeshBasicMaterial({ color: "#adf0ff", side: THREE.DoubleSide });
  const purple = new THREE.MeshLambertMaterial({ color: "#8b73d5" });
  const beakMat = new THREE.MeshLambertMaterial({ color: "#efb73f" });
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.21, 18, 14), white);
  body.position.y = 0.88; body.scale.set(0.92, 1.15, 1.27); b.add(body);
  const mantle = new THREE.Mesh(new THREE.SphereGeometry(0.18, 14, 12), cream);
  mantle.position.set(0, 1.07, -0.05); mantle.scale.set(0.82, 0.72, 0.87); b.add(mantle);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.17, 16, 12), white);
  head.position.set(0, 1.18, 0.15); b.add(head);
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.145, 14, 10), cream);
  cap.position.set(0, 1.23, 0.12); cap.scale.set(1.02,0.60,1.05); b.add(cap);
  for (const s of [-1,1]) {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.035, 10, 8), purple);
    eye.position.set(s * 0.128, 1.205, 0.235); b.add(eye);
    const glint = new THREE.Mesh(new THREE.SphereGeometry(0.012, 8, 6), ice);
    glint.position.set(s * 0.13 + 0.008, 1.216, 0.259); b.add(glint);
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.013, 0.016, 0.13, 6), black);
    leg.position.set(s*0.09,0.62,0.03); b.add(leg);
    for (let j=-1;j<=1;j++) {
      const claw = new THREE.Mesh(new THREE.ConeGeometry(0.016, 0.10, 6), black);
      claw.position.set(s*0.09+j*0.025,0.51,0.065); claw.rotation.x = Math.PI/2; b.add(claw);
    }
  }
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.047, 0.17, 7), beakMat);
  nose.rotation.x = Math.PI/2; nose.position.set(0,1.13,0.337); b.add(nose);
  const diamond = new THREE.Mesh(new THREE.OctahedronGeometry(0.085,0), ice);
  diamond.scale.set(0.75, 1.25, 0.5); diamond.position.set(0,0.91,0.21); b.add(diamond);
  for (const s of [-1,1]) {
    const wing = new THREE.Group(); wing.name = s < 0 ? "frostWingL" : "frostWingR";
    wing.position.set(s*0.16,1.05,0); b.add(wing);
    const arm = new THREE.Mesh(new THREE.SphereGeometry(0.13,12,10),white);
    arm.position.set(s*0.16,0,-0.06); arm.scale.set(2.1,0.48,0.7); wing.add(arm);
    for (let i=0;i<11;i++) {
      const length = 0.38 + (1-i/10)*0.28;
      const feather = new THREE.Mesh(new THREE.SphereGeometry(0.1,10,6), i<5?black:white);
      feather.scale.set(0.42, 0.25, length/0.2);
      feather.position.set(s*(0.22+i*0.038),0,-0.12+i*0.029);
      feather.rotation.y = s*(0.13+i*0.055); wing.add(feather);
    }
    for (let i=0;i<4;i++) {
      const covert=new THREE.Mesh(new THREE.SphereGeometry(0.095,10,7),white);
      covert.scale.set(1.25,0.35,1.35); covert.position.set(s*(0.15+i*0.12),0.035,0.0); wing.add(covert);
    }
    const wingGem=new THREE.Mesh(new THREE.OctahedronGeometry(0.064,0),ice);
    wingGem.position.set(s*0.48,0.05,-0.07); wing.add(wingGem);
  }
  for (let i=-3;i<=3;i++) {
    const tail=new THREE.Mesh(new THREE.SphereGeometry(0.11,10,6),Math.abs(i)<=1?black:white);
    tail.scale.set(0.3,0.23,3.2-Math.abs(i)*0.15);
    tail.position.set(i*0.043,0.79,-0.40); tail.rotation.y = i*0.13; b.add(tail);
  }
  for (let i=0;i<3;i++) {
    const crest=new THREE.Mesh(new THREE.ConeGeometry(0.036,0.13+i*0.03,5),white);
    crest.position.set((i-1)*0.05,1.36+i*0.02,0.06); crest.rotation.x=-0.3; b.add(crest);
  }
  return b;
}
''')

    # Frostwing stays in place; auto-fires every 2 seconds throughout 25 sec; X automatically rushes.
    one(G,'      const mode: "freeze" | "bird" = a.style === "bird" ? "bird" : "freeze";', '      const mode: "freeze" | "bird" = a.style === "bird" ? "bird" : "freeze";') if False else None
    one(G,'''        this.makeSnowPuppet(id, f, f.team, a, f.atkPower, pos, target?.id ?? -1, "bird", Math.max(16, a.duration), "idle", 5, i);''', '''        this.makeSnowPuppet(id, f, f.team, a, f.atkPower, pos, target?.id ?? -1, "bird", 25, "attack", 999, i);
        const bird = this.snowPuppets.find(p => p.id === id); if (bird) bird.shotCd = 2.0;''')
    one(G,'''        this.emit(["snowPuppet", id, f.id, f.team, pos.toArray(), target?.id ?? -1, "bird", Math.max(16, a.duration), "idle", 5, i]);''', '''        this.emit(["snowPuppet", id, f.id, f.team, pos.toArray(), target?.id ?? -1, "bird", 25, "attack", 999, i]);''')
    one(G,'''    this.makeSnowPuppet(id, f, f.team, a, f.atkPower, pos, target?.id ?? -1, "freeze", a.duration, "idle", 0, 0);''', '''    this.makeSnowPuppet(id, f, f.team, a, f.atkPower, pos, target?.id ?? -1, "freeze", a.duration, "rush", 0, 0);''')
    one(G,'''    this.emit(["snowPuppet", id, f.id, f.team, pos.toArray(), target?.id ?? -1, "freeze", a.duration, "idle", 0, 0]);''', '''    this.emit(["snowPuppet", id, f.id, f.team, pos.toArray(), target?.id ?? -1, "freeze", a.duration, "rush", 0, 0]);''')
    # passive and normal projectile damage style for bird, not existing frost-bolt.
    one(G,'      stun: p.atk.stun, speed: 12.5, size: 0.68, count: 1, spread: 0, pierce: false, heavy: false,', '''      stun: p.atk.stun, speed: 12.5, size: 0.68, count: 1, spread: 0, pierce: false, heavy: false,
      id: "bird_shard",''')
    one(G,'    this.spawnProjectile(p.owner, p.team, shard, p.power, origin, dir.multiplyScalar(shard.speed), "bolt", "frost", shard.size, "#e8ffff", false, target);', '''    shard.style = "frost_shard";
    this.spawnProjectile(p.owner, p.team, shard, p.power, origin, dir.multiplyScalar(shard.speed), "frost_shard", "frost", shard.size, "#e8ffff", false, target);''')
    region(G,'      } else {\n        const ownerPos = p.owner ? p.owner.root.position : p.home;', '\n      if (p.life <= 0) this.finishSnowPuppet(p, false);', '''      } else {
        // Frostwing holds the exact world position where it was summoned.
        // Wings animate but the bird never pursues or orbits the enemy.
        const left = p.mesh.getObjectByName("frostWingL");
        const right = p.mesh.getObjectByName("frostWingR");
        if (left) left.rotation.z = Math.sin(p.age * 9 + p.slot) * 0.43;
        if (right) right.rotation.z = -Math.sin(p.age * 9 + p.slot) * 0.43;
        p.mesh.position.copy(p.home).add(new THREE.Vector3(0, Math.sin(p.age * 3 + p.slot) * 0.08, 0));
        p.shotCd = Math.max(0, p.shotCd - dt);
        if (this.cfg.role !== "client" && p.shotCd <= 0 && target) {
          this.fireSnowBirdShard(p, target);
          p.shotCd = 2.0; // Never catch up with a rapid burst after losing a target.
        }
      }
''')

    # ----- real four floating shield visual, clone spawning -----
    helper='''  // ROXY_FROSTWING_SPELLBOOK_V3_20261108: visible 4-crystal defense orbit.
  private updateFrostAegis(_dt: number) {
    for (const f of this.fighters) {
      if (f.look.element !== "frost") continue;
      let ring = this.frostAegisVisuals.get(f.id);
      if (f.frostShieldCharges <= 0 || f.frostShieldT <= 0 || f.isDown()) {
        if (ring) { this.scene.remove(ring); this.frostAegisVisuals.delete(f.id); } continue;
      }
      if (!ring) {
        ring = new THREE.Group();
        const ice = new THREE.MeshPhongMaterial({ color: "#b7efff", emissive: "#5bc6ff", emissiveIntensity: 0.35,
          transparent: true, opacity: 0.92, flatShading: true });
        for (let i=0;i<4;i++) {
          const crystal=new THREE.Mesh(new THREE.OctahedronGeometry(0.18,0),ice);
          crystal.scale.set(0.68,1.7,0.68); ring.add(crystal);
        }
        this.scene.add(ring); this.frostAegisVisuals.set(f.id,ring);
      }
      ring.position.copy(f.root.position).add(new THREE.Vector3(0,1.35,0));
      for (let i=0;i<4;i++) {
        const sh=ring.children[i]; sh.visible=i<f.frostShieldCharges;
        const angle=this.time*2+i*Math.PI/2;
        sh.position.set(Math.cos(angle)*0.8,Math.sin(this.time*3+i)*0.09,Math.sin(angle)*0.8);
        sh.rotation.set(0,this.time+i,0.22*Math.sin(this.time*2+i));
      }
    }
  }

  private iceClones: { fighter: Fighter; ownerId: number; netTimer: number }[] = [];

  private tintIceClone(c: Fighter) {
    const apply = () => c.model.traverse(o => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      const arr = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      const tinted = arr.map(m => {
        const copy = m.clone();
        if ("color" in copy && (copy as THREE.MeshStandardMaterial).color) {
          (copy as THREE.MeshStandardMaterial).color.lerp(new THREE.Color("#72cfff"),0.68);
        }
        if ("emissive" in copy && (copy as THREE.MeshStandardMaterial).emissive) {
          (copy as THREE.MeshStandardMaterial).emissive.set("#235c96");
          (copy as THREE.MeshStandardMaterial).emissiveIntensity=0.25;
        }
        copy.transparent=true; copy.opacity=Math.min(copy.opacity ?? 1,0.80);
        return copy;
      }) as THREE.Material[];
      mesh.material = Array.isArray(mesh.material) ? tinted : tinted[0];
    });
    void c.model.ready.then(apply);
  }

  private spawnIceClone(owner: Fighter) {
    if (this.cfg.role === "client") return;
    const target=owner.opponent instanceof Fighter && !owner.opponent.isDown() ? owner.opponent :
      this.fighters.find(e => e.team !== owner.team && !e.isDown());
    if (!target) { this.fxp("num",owner.chest(),"NO FIGHTER TO MIRROR","#c1edff",0.75); return; }
    for (const existing of [...this.iceClones]) if (existing.ownerId === owner.id) this.finishIceClone(existing, true);
    const copy=new Fighter(target.look,target.charIndex,undefined,undefined,false);
    copy.id=this.nextId++; copy.team=owner.team; copy.owner="cpu-ice-clone";
    copy.maxHp=Math.max(1,target.maxHp*0.25); copy.hp=copy.maxHp;
    copy.guard=copy.maxGuard*0.5; copy.arenaRadius=owner.arenaRadius;
    copy.root.position.copy(owner.root.position).add(new THREE.Vector3(0.9,0,0.6));
    copy.root.rotation.y=owner.root.rotation.y; copy.opponent=target;
    copy.brain={think: (f: Fighter) => {
      const victim=f.opponent;
      if (!victim || victim.isDown()) return;
      const delta=victim.root.position.clone().sub(f.root.position).setY(0);
      const dist=delta.length();
      if (dist>1.55) f.intent.move.copy(delta.normalize());
      if (dist<2.10 && f.atkLock<=0) f.intent.attack=true;
      if (dist<1.25 && victim instanceof Fighter && victim.state===S.ATTACK) f.intent.block=true;
    }};
    copy.onSwing=x=>this.onSwing(x);
    copy.onKo=()=>{
      const item=this.iceClones.find(c=>c.fighter===copy);
      if (item) this.finishIceClone(item,true);
    };
    this.scene.add(copy.root,copy.trail.mesh); this.entities.set(copy.id,copy);
    this.iceClones.push({fighter:copy,ownerId:owner.id,netTimer:0});
    this.tintIceClone(copy);
    this.emit(["iceCloneSpawn", copy.id,target.charIndex,owner.team,copy.hp,copy.root.position.toArray()]);
    this.fxp("flash", copy.chest(), "#b9f5ff", 0.9, 0.25, 0.86);
  }

  private finishIceClone(item: {fighter:Fighter;ownerId:number;netTimer:number}, emit: boolean) {
    const f=item.fighter;
    this.scene.remove(f.root,f.trail.mesh); this.entities.delete(f.id);
    this.iceClones=this.iceClones.filter(c=>c!==item);
    if (emit && this.cfg.role!=="client") this.emit(["iceCloneEnd",f.id]);
  }

  private updateIceClones(dt: number) {
    for (const item of [...this.iceClones]) {
      const f=item.fighter;
      if (this.roundOver || f.isDown() || (this.cfg.role!=="client" &&
          !this.fighters.some(x=>x.id===item.ownerId && !x.isDown()))) {
        this.finishIceClone(item,true); continue;
      }
      f.update(dt);
      if (this.cfg.role!=="client") {
        item.netTimer-=dt;
        if (item.netTimer<=0) { item.netTimer=0.10; this.emit(["iceClonePose",f.id,f.snapshot()]); }
      }
    }
  }

'''
    one(G,'  private disposeSnowPuppet(p: SnowPuppet) {',helper+'  private disposeSnowPuppet(p: SnowPuppet) {')

    # replicate clone to online clients and late joiners
    one(G,'    for (const p of this.snowPuppets) ev.push(["snowPuppet",', '''    for (const c of this.iceClones) ev.push(["iceCloneSpawn", c.fighter.id, c.fighter.charIndex,
      c.fighter.team, c.fighter.hp, c.fighter.root.position.toArray()]);
    for (const p of this.snowPuppets) ev.push(["snowPuppet",''')
    one(G,'      case "snowPuppet": {', '''      case "iceCloneSpawn": {
        if (this.iceClones.some(c=>c.fighter.id===ev[1])) break;
        const look=CHARACTERS[ev[2]]?.look;
        if (!look) break;
        const f=new Fighter(look,ev[2],undefined,undefined,false);
        f.id=ev[1]; f.team=ev[3]; f.hp=ev[4]; f.maxHp=ev[4]; f.puppet=true;
        f.root.position.copy(v3(ev[5]));
        this.scene.add(f.root,f.trail.mesh); this.entities.set(f.id,f);
        this.iceClones.push({fighter:f,ownerId:-1,netTimer:0});
        this.tintIceClone(f);
        break;
      }
      case "iceClonePose": {
        const f=this.iceClones.find(c=>c.fighter.id===ev[1])?.fighter;
        if (f) f.applySnapshot(ev[2]);
        break;
      }
      case "iceCloneEnd": {
        const clone=this.iceClones.find(c=>c.fighter.id===ev[1]);
        if (clone) this.finishIceClone(clone,false);
        break;
      }
      case "snowPuppet": {''')

    # C bird and clone capability requests, overview marker
    one(G,'// ROXY_MANUAL_SUMMONS_BIRD_V2_20261108 — manual frost summons with handcrafted procedural meshes.',
        '// ROXY_MANUAL_SUMMONS_BIRD_V2_20261108 — manual frost summons with handcrafted procedural meshes.\n// ROXY_FROSTWING_SPELLBOOK_V3_20261108')

except Exception as exc:
    sys.exit(f'INSTALLATION FAILED: {exc}. No files changed.')

stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
for n in NAMES:
    if patched[n] == original[n]: continue
    p=ROOT/n
    backup=p.with_name(p.name+f'.before_roxy_frostwing_v3_{stamp}.bak')
    backup.write_text(original[n],encoding='utf-8')
    p.write_text(patched[n],encoding='utf-8')
    print(f'PATCH {n} (backup: {backup.name})')
print('DONE. Run `npx tsc --noEmit -p .` then `npm run dev`.')
