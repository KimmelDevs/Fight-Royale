#!/usr/bin/env python3
"""Zenith — The Iron Sovereign. Fixed UI preflight, single-file additive installer for Fight Royale /web.
Requires the modern game with glaive, V skills, the character-style AI and Roxy.
Uses Zarek's existing VRM (no model download). Creates timestamped backups.
"""
from pathlib import Path
from datetime import datetime
import sys

root = Path.cwd()
paths = ['src/game/roster.ts', 'src/game/kits.ts', 'src/game/fighter.ts',
         'src/game/model.ts', 'src/game/game.ts', 'src/game/ai.ts', 'src/ui/Select.tsx']
try:
    originals = {x: (root/x).read_text(encoding='utf-8') for x in paths}
except OSError as err:
    sys.exit(f'Run from your web folder; source missing: {err}')
R,K,F,M,G,A,U=paths
s=originals.copy()
MARK='ZENITH_IRON_SOVEREIGN_V1_20261108'
if MARK in s[G]:
    print('Zenith already installed. No files changed.'); sys.exit(0)
if 'id: "zenith"' in s[R]:
    sys.exit('A Zenith entry already exists without this patch marker. No files changed.')

def one(file, old, new):
    hits=s[file].count(old)
    if hits != 1: raise ValueError(f'{file}: expected one matching anchor; found {hits}: {old[:100]}')
    s[file]=s[file].replace(old,new,1)

def before(file, old, text): one(file,old,text+'\n'+old)
def after(file, old, text): one(file,old,old+'\n'+text)

try:
    # A NEW CHARACTER, not a reskin of Zarek; both share one cached VRM.
    before(R, '\n];\n\nexport function resolveEnemy(', '''  // ZENITH_IRON_SOVEREIGN_V1_20261108 — borrows Zarek's VRM until Zenith receives her own.
  { id: "zenith", title: "The Iron Sovereign", role: "Duelist - Magnetic Double Spear",
    desc: "A rapid spear martial artist who commands her double-ended weapon from afar. Opposite magnetic marks attract; matching ones repel.",
    stats: { power: 4, speed: 5, range: 4, defense: 3 },
    look: { name: "Zenith", body: "f", vrm: "zarek", kit: "glaive", element: "metal", outfit: "assassin", style: "ponytail", hat: "none",
      hair: "#d8e1ec", hair_shade: "#7891b0", iris_top: "#7388ae", iris_bottom: "#c3e6ff", eye_dark: "#1a294a",
      tunic: "#18243b", band: "#304b70", pants: "#151b2c", boots: "#16233a", metal: "#d3dde9", trim: "#7899ce",
      cape: "#202d48", cape_bottom: "#425a85", glow: "#8dbce3", shield: "#22364f", emblem: "#c5d8f1" } },''')

    # All Zenith entries explicitly override Zarek's glaive table.
    after(K,'  t.v = bonusSkill(kit, element);', '''  // ZENITH_IRON_SOVEREIGN_V1_20261108: Metal spear kit is independent of Zarek.
  if (kit === "glaive" && element === "metal") {
    const base = (key: string, value: Partial<Attack>) => { t[key] = a(value); };
    const combo: [number, number, string, string][] = [
      [48, 0.14, "gl1_w", "gl1_s"], [51, 0.14, "gl2_w", "gl2_s"],
      [54, 0.15, "gl3_w", "gl3_s"], [57, 0.16, "gl4_w", "gl4_s"],
      [76, 0.24, "gl5_w", "gl5_s"] ];
    for (let i=0;i<5;i++) base(`l${i+1}`, { name: `Steel Fang ${i+1}`, type: "melee",
      wind: 0.085 + 0.014 * i, active: 0.075, recover: combo[i][1],
      dmg: combo[i][0], guard: 13+i*2, reach: 2.14, lunge: 2.35, knock: i===4?3.0:0.65,
      stun: i===4?0.32:0.16, style: "zenith_basic", pose_w: combo[i][2], pose_s: combo[i][3],
      next: i<4?`l${i+2}`:"" });
    base("heavy", { name: "Magnetic Lance", type: "projectile", wind: 0.28, recover: 0.56,
      dmg: 113, guard: 35, knock: 3.0, stun: 0.35, heavy: true, speed: 23, size: 1.5, pierce: true,
      style: "zenith_heavy", pose_w: "glh_w", pose_s: "glh_s" });
    base("z", { name: "Rail Spear", desc: "Throw your spear in a piercing metal line (Negative). Press Z again to recall through foes. If not recalled, it returns automatically.",
      cd: 12, type: "projectile", wind: 0.19, recover: 0.29, dmg: 104, guard: 25,
      knock: 3.2, stun: 0.27, speed: 24, size: 1.8, pierce: true,
      style: "zenith_rail", pose_w: "glz_w", pose_s: "glz_s" });
    base("x", { name: "Phantom Spear Barrage", desc: "Five fast held thrusts, then three independently flying spear thrusts while Zenith can reposition.",
      cd: 10, type: "melee", wind: 0.12, active: 0.75, recover: 0.33,
      dmg: 29, guard: 9, reach: 2.35, knock: 0.35, stun: 0.13,
      style: "zenith_barrage", pose_w: "glx_w", pose_s: "glz_s" });
    base("c", { name: "Magnetic Dominion", desc: "Tap to draw a positively marked enemy toward you, hold to repel nearby foes. With your spear thrown, zip toward its magnetic anchor instead.",
      cd: 14, type: "buff", mode: "zenith_magnet", wind: 0.12, active: 0.08, recover: 0.36,
      radius: 4.5, pose_w: "glc_w", pose_s: "glc_s" });
    base("v", { name: "Sovereign Arsenal", desc: "Summon six magnetic spear constructs for dodgeable directional strikes, ending in one heavy rail spear.",
      cd: 53, type: "projectile", wind: 0.55, active: 1.35, recover: 0.70,
      dmg: 49, guard: 15, knock: 1.4, stun: 0.18, speed: 17, size: 1.2,
      style: "zenith_arsenal", pose_w: "glc_w", pose_s: "glc_s" });
  }''')

    # Character select must not advertise Zarek's storm abilities for Metal.
    # Match the stable frost conditional, NOT Roxy's frequently changing tooltip text.
    # This keeps the current text completely unchanged and adds Zenith's tooltip first.
    one(U, 'ch.look.element === "frost" ?',
       'ch.look.element === "metal" ? "Tap: 5-hit Steel Fang - Hold: Magnetic Lance - Z: Rail Spear (press Z to recall) - X: Phantom Barrage - C: Magnetic Dominion (hold to repel) - V: Sovereign Arsenal" : ch.look.element === "frost" ?')

    # Avoid accidentally awarding Storm Glaive's unique clash stacks to Zenith.
    one(G,'    if (f.kit !== "glaive") return;\n    f.clashMomentum += 1;',
          '    if (f.kit !== "glaive" || f.look.element === "metal") return;\n    f.clashMomentum += 1;')

    # Fighter state and recast callback. Poses/attacks remain the normal animation code.
    after(F,'  onSwing: (f: Fighter) => void = () => {};', '''  // ZENITH_IRON_SOVEREIGN_V1_20261108 — pure game-side spear state.
  zenithSpearOut = false;
  zenithSpearAnchor = new THREE.Vector3();
  zenithMagnetCharges = 0;
  zenithDominionRepel = false;
  onZenithRecall: (f: Fighter) => void = () => {};''')
    before(F,'    // Garrick C second press: legal ONLY after the first eruption really hit.', '''    // A second Z recalls the SAME spear without ignoring the original cooldown.
    if (this.look.element === "metal" && this.zenithSpearOut && k === "z") {
      if (![S.HITSTUN,S.STAGGER,S.KO,S.WIN].includes(this.state)) this.onZenithRecall(this);
      return;
    }''')
    before(F,'    this.startAttack(!this.onGround && this.attacks[k + "_air"] ? k + "_air" : k);',
       '''    if (this.look.element === "metal" && k === "c") this.zenithDominionRepel = this.intent.skillHeld === "c";''')

    # Metal weapon: an actual double-edged silver spear with dark-blue trim, no crimson or storm palette.
    before(M,'    const staff = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);',
       '''    // Metal uses the same hand rig, new material palette and a longer leaner spear.
    const zenithMetal = this.look.element === "metal";''')
    one(M,'    staff.scale.setScalar(0.78);', '    staff.scale.setScalar(zenithMetal ? 0.86 : 0.78);')
    one(M,'mesh(staff, cyl(0.019, 0.022, 1.53, 12), this.tn("#233449"));',
       'mesh(staff, cyl(0.019, 0.022, 1.53, 12), this.tn(zenithMetal ? "#8795ac" : "#233449"));')
    one(M,'mesh(staff, cyl(0.028, 0.028, 0.42, 12), this.tn("#101a2a"), [0, 0, 0]);',
       'mesh(staff, cyl(0.028, 0.028, 0.42, 12), this.tn(zenithMetal ? "#263955" : "#101a2a"), [0, 0, 0]);')
    after(M,'    this.glaivePivot = staff;', '''    if (zenithMetal) staff.name = "zenithMagneticSpear";''')
    before(M,'  /** KAIZEN_BIND_ZAREK_COUNTER_V4: forked short blade', '''  /** The game hides the held metal spear when its projectile is flying. */
  setZenithSpearHeld(held: boolean) {
    if (this.look.element === "metal" && this.glaivePivot) this.glaivePivot.visible = held;
  }
''')

    # A small but distinct 3D projectile with polished iron and pointed double tips.
    before(G,'  if (style === "clusterbomb") {', '''  // ZENITH_IRON_SOVEREIGN_V1_20261108 — metal spear, not a lightning bolt.
  if (style === "zenith_rail" || style === "zenith_heavy" || style === "zenith_construct") {
    const steel = new THREE.MeshLambertMaterial({ color: "#c7d1de" });
    const ink = new THREE.MeshLambertMaterial({ color: "#263e61" });
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.035*size,0.035*size,0.95*size,10), ink);
    core.rotation.x = Math.PI/2; g.add(core);
    for (const side of [-1,1]) {
      const tip = new THREE.Mesh(new THREE.ConeGeometry(0.12*size,0.48*size,6), steel);
      tip.rotation.x = side*Math.PI/2; tip.position.z=side*0.66*size; g.add(tip);
      const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.055*size,0.055*size,0.09*size,8), steel);
      collar.rotation.x=Math.PI/2; collar.position.z=side*0.44*size; g.add(collar);
    }
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.085*size,0), glow);
    g.add(gem);
    return;
  }''')

    # Combat and networked rethrow state, no extra timers / expensive new skinned actors.
    after(G,'    f.onSwing = (x) => this.onSwing(x);',
      '    f.onZenithRecall = (x) => this.zenithRecall(x);')
    before(G,'    const a = f.atk!;\n    this.swingSound(f, a);', '''    if (f.look.element === "metal") {
      const za = f.atk!;
      if (za.style === "zenith_rail") { this.zenithLaunch(f, za); return; }
      if (za.style === "zenith_barrage") { this.zenithBarrage(f, za); return; }
      if (za.style === "zenith_arsenal") { this.zenithArsenal(f, za); return; }
    }''')
    before(G,'      case "buff": this.applyBuff(f, a); break;',
        '''      case "buff": if (a.mode === "zenith_magnet") this.zenithDominion(f,a); else this.applyBuff(f,a); break;''')
    # Above creates duplicate case buff; substitute instead since case order matters.
    one(G,'      case "buff": this.applyBuff(f, a); break;', '')

    # One attack-level hit hook: positive/negative marks only on landed damage.
    after(G,'    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);', '''    // Polarity applies on confirmed hits (not on dodges, shields, blocks or parries).
    if (attacker instanceof Fighter && attacker.look.element === "metal" &&
        (result === "hit" || result === "crit" || result === "ko") &&
        (a.style === "zenith_basic" || a.style === "zenith_rail" ||
         a.style === "zenith_heavy" || a.style === "zenith_construct" || a.style === "zenith_barrage")) {
      const sign = (a.style === "zenith_rail" || a.style === "zenith_heavy" || a.style === "zenith_construct") ? -1 : 1;
      this.zenithMarks.set(d.id, { sign, ttl: 7, team: attacker.team });
      this.fxp("num", d.chest().add(new THREE.Vector3(0,0.83,0)), sign > 0 ? "MAGNET +" : "MAGNET -", sign > 0 ? "#a1c8ff" : "#dce3ef", 0.54);
    }''')
    after(G,'  projectiles: Projectile[] = [];',
      '''  private zenithMarks = new Map<number, {sign: number; ttl: number; team: number}>();''')
    # avoid changing old core timers: update map when projectiles updated.
    before(G,'  private updateProjectiles(dt: number) {', '''  // ZENITH_IRON_SOVEREIGN_V1_20261108: metallic field physics, bounded displacements.
  private zenithLaunch(f: Fighter, a: Attack) {
    // One independently simulated spear, which can be slashed/parried/clashed.
    if (f.zenithSpearOut) return;
    const origin = f.chest();
    const target = f.opponent && !f.opponent.isDown() ? f.opponent : this.enemiesOf(f)[0] ?? null;
    const aim = target ? target.chest().sub(origin) : new THREE.Vector3(Math.sin(f.root.rotation.y),0,Math.cos(f.root.rotation.y));
    const speed = Math.max(19,a.speed);
    const p = this.spawnProjectile(f,f.team,a,f.atkPower,origin,aim.normalize().multiplyScalar(speed),
      "zenith_rail","metal",a.size,"#b6d4ee",true,target);
    p.life=3.2;
    f.zenithSpearOut=true;
    f.zenithSpearAnchor.copy(p.pos);
    f.model.setZenithSpearHeld(false);
    this.fxp("flash",origin,"#acbfd9",0.38,0.14,0.72);
  }
  private zenithRecall(f: Fighter) {
    const p=this.projectiles.find(x=>!x.done && x.style==="zenith_rail" && x.shooter===f);
    if (!p || p.returnTo) return;
    p.returnTo=f; p.hitIds.clear(); p.life=Math.max(p.life,0.85);
    if (this.cfg.role!=="client") this.emit(["zenithRecall",p.id,f.id]);
    this.fxp("ring",p.pos.clone(),"#b1cae6",0.85,0.16,0.65);
  }
  private zenithDominion(f: Fighter, a: Attack) {
    const owned = this.projectiles.find(p=>!p.done && p.shooter===f && p.style==="zenith_rail");
    if (owned) {
      const start=f.root.position.clone();
      const to=owned.pos.clone().sub(start);
      if (!this.plat) to.y=0;
      const dist=to.length();
      if (dist>0.75) {
        const amt=Math.min(3.1,dist-0.75);
        const dest=start.addScaledVector(to.normalize(),amt);
        if (!this.plat) {
          const radial=Math.hypot(dest.x,dest.z);
          if (radial>f.arenaRadius-0.5) dest.multiplyScalar((f.arenaRadius-0.5)/radial);
        } else dest.x=THREE.MathUtils.clamp(dest.x,STAGE.blast.l+1.5,STAGE.blast.r-1.5);
        f.teleport(dest);
        this.fxp("ring",f.chest(),"#a4bedb",0.85,0.23,0.74);
      }
      return;
    }
    const foes=this.enemiesOf(f).filter(e=>!e.isDown());
    const hold=f.zenithDominionRepel;
    for (const e of foes) {
      const offset=e.root.position.clone().sub(f.root.position).setY(0);
      const dist=offset.length();
      const mark=this.zenithMarks.get(e.id);
      if (dist<0.35 || dist>(hold?3.5:5.3) || (!hold && (!mark || mark.team!==f.team))) continue;
      // A negative charge repels on a tap; positive attracts. Holding always repels.
      const repel=hold || (mark?.sign === -1 && mark.team === f.team);
      const amt=(repel?1.15:Math.min(1.4,Math.max(0,dist-1.2)))*(1+0.16*f.zenithMagnetCharges);
      const dir=offset.normalize();
      const dest=e.root.position.clone().addScaledVector(dir,repel?amt:-amt);
      if (!this.plat) {
        const radius=(e instanceof Fighter?e.arenaRadius:11)-0.4;
        const flat=Math.hypot(dest.x,dest.z);
        if (flat>radius) {dest.x*=radius/flat;dest.z*=radius/flat;}
      } else dest.x=THREE.MathUtils.clamp(dest.x,STAGE.blast.l+1.5,STAGE.blast.r-1.5);
      // Short displacement only: not a guaranteed bind, no stun.
      e.root.position.x=dest.x;
      if (!this.plat) e.root.position.z=dest.z;
      this.fxp("ring",e.chest(),repel?"#c3d0e3":"#869fc8",0.85,0.20,0.58);
    }
    f.zenithMagnetCharges = 0;
    this.fxp("motes",f.chest(),"#a6bddc",17);
  }
  private zenithBarrage(f: Fighter,a:Attack) {
    const round=this.round;
    // Five standard, blockable/parryable melee checks in a short tempo.
    for(let i=0;i<5;i++) this.later(0.10*i,()=>{
      if(this.round!==round || f.isDown())return;
      this.melee(f,{...a,id:`zx${i}`,style:"zenith_barrage",dmg:29,knock:i===4?1.8:0.3,stun:0.13});
      this.fxp("sparks",f.model.bladeTip.getWorldPosition(new THREE.Vector3()),"#a6c8de",10,4);
    });
    // Independent extra thrusts: their projectile objects keep flying if she dodges.
    for(let i=0;i<3;i++) this.later(0.68+i*0.17,()=>{
      if(this.round!==round || f.isDown()) return;
      const origin=f.chest().add(new THREE.Vector3((i-1)*0.3,0.25,0));
      const target=f.opponent && !f.opponent.isDown()? f.opponent:this.enemiesOf(f)[0]??null;
      const aim=target?target.chest().sub(origin):new THREE.Vector3(Math.sin(f.root.rotation.y),0,Math.cos(f.root.rotation.y));
      const part={...a,id:`zxfloat${i}`,type:"projectile",style:"zenith_construct",dmg:32,pierce:false,heavy:false,speed:20,size:0.85};
      this.spawnProjectile(f,f.team,part,f.atkPower,origin,aim.normalize().multiplyScalar(20),"zenith_construct","metal",0.85,"#a5bfe0",false,target);
    });
  }
  private zenithArsenal(f:Fighter,a:Attack) {
    const round=this.round;
    const target=f.opponent&&!f.opponent.isDown()?f.opponent:this.enemiesOf(f)[0]??null;
    if(!target) return;
    const point=target.root.position.clone();
    // Visible, dodgeable open: attack directions are committed before each shot.
    this.fxp("ring",point.clone(),"#a6bcd6",2.7,0.52,0.55);
    this.fxp("motes",point.clone().add(new THREE.Vector3(0,1,0)),"#b5cbdd",22);
    for(let i=0;i<7;i++) this.later(0.30+i*0.22,()=>{
      if(this.round!==round||f.isDown())return;
      const angle=(i%6)*Math.PI/3+0.18;
      const center=target.root.position.clone();
      const origin = i===6 ? f.chest() : center.clone().add(new THREE.Vector3(Math.sin(angle)*4.2,1.1,Math.cos(angle)*4.2));
      const toward=center.clone().add(new THREE.Vector3(0,1,0)).sub(origin);
      const power=i===6?1.28:1;
      const part={...a,id:i===6?"v_final":`v${i}`,style:"zenith_construct",dmg:i===6?112:42,
        knock:i===6?5.3:0.9,stun:i===6?0.45:0.15,heavy:i===6,pierce:false,
        size:i===6?2.0:1.0};
      const p=this.spawnProjectile(f,f.team,part,f.atkPower*power,origin,toward.normalize().multiplyScalar(i===6?26:17),
        "zenith_construct","metal",part.size,"#b0c6dc",false,target);
      p.life=1.25;
      this.fxp("flash",origin,"#d0deef",0.16,0.1,0.8);
    });
  }
''')

    before(G,'      if (p.gravity) { p.vel.y -= p.gravity * dt; p.spin.rotation.x += dt * 9; }',
       '''      if (p.style === "zenith_rail" && p.shooter instanceof Fighter) {
        const owner=p.shooter;
        // Outbound -> short magnetic anchor -> return, never an infinite spear.
        if (!p.returnTo && p.age > 1.50) { p.returnTo=owner; p.hitIds.clear(); }
        if (p.returnTo) {
          const aim=owner.chest().sub(p.pos);
          if (aim.length()<0.82) {
            p.done=true; owner.zenithSpearOut=false;
            owner.model.setZenithSpearHeld(true);
            this.fxp("flash",owner.chest(),"#a5c1dc",0.25,0.1,0.7);
          } else p.vel.copy(aim.normalize().multiplyScalar(25));
        } else if (p.age>0.38) p.vel.set(0,0,0);
        owner.zenithSpearAnchor.copy(p.pos);
        if (p.done) continue;
      }''')
    # Avoid departing from arena radius and life expiry leaving Zenith permanently unarmed.
    before(G,'    for (const p of this.projectiles) if (p.done) {',
       '''    for (const p of this.projectiles) if (p.done && p.style === "zenith_rail" && p.shooter instanceof Fighter) {
      p.shooter.zenithSpearOut=false;
      p.shooter.model.setZenithSpearHeld(true);
    }''')
    # Tick polarity independently from damage so old marks cannot persist forever.
    before(G,'    // First move ALL projectiles, then resolve shot-on-shot collisions before',
       '''    for (const [id, mark] of this.zenithMarks) {
      mark.ttl -= dt;
      if (mark.ttl <= 0) this.zenithMarks.delete(id);
    }''')
    # In 1v1 basic strikes when spear absent, the actor is still capable of light attacks but weaker.
    before(G,'    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);',
      '''    // Do not mutate shared Attack objects or permanently weaken future swings.
    const zenithAttack = attacker instanceof Fighter && attacker.look.element === "metal" &&
      attacker.zenithSpearOut && a.type === "melee" && /^l\\d+$/.test(a.id)
      ? { ...weightedAttack, dmg: weightedAttack.dmg * 0.57, reach: weightedAttack.reach * 0.72 }
      : weightedAttack;''')
    # Momentum state local even when AI parries regular shots; feedback only.
    after(G,'    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);',
      '''    if (d instanceof Fighter && d.look.element === "metal" && result === "parry" && a.type === "projectile") {
      d.zenithMagnetCharges = Math.min(3,d.zenithMagnetCharges+1);
      this.fxp("num",d.chest().add(new THREE.Vector3(0,0.8,0)),`MAGNETIC CHARGE ${d.zenithMagnetCharges}/3`,"#a0bbde",0.65);
    }''')
    one(G,'    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);',
       '    const result = d.receiveHit(attacker, zenithAttack, riposte ? power * 1.15 : power);')
    # Event for client recap of recast direction.
    before(G,'      case "projEnd": {', '''      case "zenithRecall": {
        const p=this.projectiles.find(q=>q.id===ev[1]);
        if (p) {p.returnTo=this.entities.get(ev[2]) as Fighter || null; p.hitIds.clear();}
        break;
      }''')

    # Iron Reversal replaces Zarek's cyclone parry counter with one accurate thrust.
    before(K,'  // BULLET_SWORDPLAY_V1: Aster', '''  if (kit === "glaive" && element === "metal") {
    t.pc = { ...t.l2, name: "Iron Reversal", desc: "A perfect parry opens the guard for a fast magnetic counter-thrust.",
      id: "pc", type: "melee", style: "zenith_basic", wind: 0.12, active: 0.08, recover: 0.29,
      dmg: 70, guard: 20, knock: 1.4, stun: 0.28, next: "", pose_w: "gl2_w", pose_s: "gl2_s" };
  }''')

    # AI knows Zenith as a fast glaive fighter, not an absent fighter.
    after(A,'  roxy: { range: 5.45, heavy: 0.36, combo: 0.52, bait: 0.24, pressure: 0.32, skillBias: [1.45, 1.60, 1.20] },',
      '  zenith: { range: 2.20, heavy: 0.30, combo: 0.90, bait: 0.34, pressure: 0.92, skillBias: [1.15, 1.65, 1.10] },')
    after(A,'  roxy:    { role: "controller",  pressure: 0.60, probe: 1.16, reset: 0.90, vReserve: 0.52, spacing:  0.26 },',
      '  zenith:  { role: "glaive", pressure: 1.42, probe: 0.95, reset: 0.35, vReserve: 0.92, spacing: -0.04 },')
    before(A,'      case "roxy":', '''      case "zenith":
        if (name === "Rail Spear") points += distance > 3.0 && !f.zenithSpearOut ? 2.3 : -1.0;
        if (name === "Phantom Spear Barrage") points += punish && close ? 2.3 : 0.2;
        if (name === "Magnetic Dominion") points += f.zenithSpearOut ? 2.5 : distance < 4.5 ? 1.5 : 0.0;
        if (name === "Sovereign Arsenal") points += punish && distance < 7.5 ? 1.8 : -0.1;
        break;''')

    # Zenith's own skill polling runs ahead of generic AI offense, never bypasses legal cooldowns.
    before(A,'  private roxySkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {', '''  private zenithSkillNextAt = 0;
  private zenithSkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {
    if (f.look.element !== "metal" || f.kit !== "glaive" || f.isDown() || o.isDown()) return false;
    if (f.chainBindT > 0 || !f.onGround || f.status.has("freeze")) return false;
    const now = this.threats.now();
    if (now < this.zenithSkillNextAt) return false;
    const free = f.state === S.IDLE || f.state === S.BLOCK ||
      (f.state === S.ATTACK && f.atkPhase === 2 && f.atk &&
       f.stateT > f.atk.wind + f.atk.active + 0.08);
    if (!free) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const ready = (key: "z"|"x"|"c"|"v") => !!f.attacks[key] &&
      (f.cooldowns[key] ?? 1) <= 0 && (key !== "v" || f.bonusSkillUnlocked);
    let key: "z"|"x"|"c"|"v"|"" = "";
    if (f.zenithSpearOut) {
      // Return after a short tactical pause; C can pull Zenith toward the anchor.
      if (ready("c") && gap > 3.0 && gap < 8.0) key="c";
      else if (gap < 4.0 || this.iqLevel >= 2) key="z"; // legal repeat key, even while on cooldown
    } else if (ready("v") && gap >= 3.0 && gap < 7.0 && (o.state === S.HITSTUN || o.state === S.STAGGER)) key="v";
    else if (ready("x") && gap < 2.8 && !o.isDown()) key="x";
    else if (ready("c") && gap > 1.8 && gap < 4.9 && o.state !== S.BLOCK) key="c";
    else if (ready("z") && gap > 2.6 && gap < 9.0) key="z";
    if (!key) { this.zenithSkillNextAt=now+0.35; return false; }
    const recognition = [0.22,0.53,0.81,0.96][this.iqLevel] ?? 0.55;
    this.zenithSkillNextAt=now+[1.1,0.72,0.43,0.25][this.iqLevel];
    if (Math.random() > recognition) return false;
    f.intent.skill=key;
    return true;
  }
''')
    one(A, '''    const iqActed = !survivalActed && !landedActed && !roxyActed && !this.aiAirTap && !f.intent.skill &&''',
       '''    const zenithActed = !survivalActed && !landedActed && !roxyActed && !this.aiAirTap && !f.intent.skill &&
      this.zenithSkillOpportunity(f, o, dt);
    const iqActed = !survivalActed && !landedActed && !roxyActed && !zenithActed && !this.aiAirTap && !f.intent.skill &&''')
    one(A, '    const patternActed = !survivalActed && !landedActed && !roxyActed && !iqActed && !this.aiAirTap && !f.intent.skill &&',
       '    const patternActed = !survivalActed && !landedActed && !roxyActed && !zenithActed && !iqActed && !this.aiAirTap && !f.intent.skill &&')
    one(A, '    if (!survivalActed && !landedActed && !roxyActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&',
       '    if (!survivalActed && !landedActed && !roxyActed && !zenithActed && !this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&')

except Exception as e:
    sys.exit(f'PREFLIGHT ERROR: {e}. No files changed.')

# Only after EVERY anchor succeeds.
stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
for name in paths:
    if s[name]!=originals[name]:
        target=root/name
        backup=target.with_name(target.name+f'.before_zenith_{stamp}.bak')
        backup.write_text(originals[name],encoding='utf-8')
        target.write_text(s[name],encoding='utf-8')
        print(f'PATCH {name} | backup {backup.name}')
print('DONE: Zenith — The Iron Sovereign. Zarek VRM reused, no new VRM necessary.')
print('Run: npx tsc --noEmit -p . && npm run build')
print('NOTE: Run the separate Supabase migration to list Zenith for signed-in shop accounts.')
