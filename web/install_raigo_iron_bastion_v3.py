#!/usr/bin/env python3
"""RAIGO — IRON BASTION | Fight Royale one-file installer, Python 3 stdlib only.

USAGE:  python install_raigo_iron_bastion.py
        python install_raigo_iron_bastion.py "C:/path/to/fight-royale/web"

Preflights every source anchor before writing; backups go to .raigo-backups/TIMESTAMP.
Original fighter builds untouched. Temporary VRM = Garrick. Includes a SQL migration to
review/apply separately. Compatible with the supplied base and earlier Nythera/Zephyr patches.
"""
from __future__ import annotations
import datetime, pathlib, re, shutil, sys

MARK = 'RAIGO_IRON_BASTION_V1'
T: dict[str,str] = {}

def rep(path: str, old: str, new: str, count: int = 1):
    src=T[path]; n=src.count(old)
    if n != count:
        raise RuntimeError(f'{path}: expected {count} occurrence(s) of {old[:100]!r}, found {n} (no changes written)')
    T[path] = src.replace(old,new,count)

def before(path: str, anchor: str, txt: str): rep(path,anchor,txt+anchor)

def add_roster():
    f='src/game/roster.ts'
    before(f,'\n];\n\nexport function resolveEnemy', '''  // RAIGO_IRON_BASTION_V1: placeholder Garrick VRM, original dual weapon animations.
  { id: "raigo", title: "Iron Bastion", role: "Warrior - Chained Axe & Flail",
    desc: "A mid-range iron weapon master. Keep the spiked ball in motion, catch incoming attacks with the chain, then spend Momentum on a crushing axe-and-flail finish.",
    stats: { power: 5, speed: 2, range: 4, defense: 4 },
    look: { name: "Raigo", body: "m", vrm: "garrick", kit: "axeflail", element: "iron", outfit: "knight", style: "short", hat: "none",
      hair: "#292b30", hair_shade: "#66676c", iris_top: "#ba7a30", iris_bottom: "#f2ca79", eye_dark: "#332416",
      tunic: "#343c3b", band: "#6c7863", pants: "#22292b", boots: "#292c30", metal: "#b4b7ba", trim: "#c9a86b",
      cape: "#343e3d", cape_bottom: "#566654", glow: "#e3af69", shield: "#464844", emblem: "#e8c58b" } },
''')

def add_kits():
    f='src/game/kits.ts'
    before(f,'  hammer: { hp: 2650, guard: 110, move: 3.05, walk: 2.45, parry: 0.15, jump: 7.0 },',
           '  // RAIGO_IRON_BASTION_V1: mid-range powerhouse, punishable up close.\n  axeflail: { hp: 2500, guard: 100, move: 3.30, walk: 2.60, parry: 0.20, jump: 6.8 },\n')
    rep(f,'    glaive: glaive,','    glaive: glaive,\n    axeflail: axeFlail,')
    rep(f,'    glaive: [heavy.pose_w, heavy.pose_s],','    glaive: [heavy.pose_w, heavy.pose_s],\n    axeflail: [heavy.pose_w, heavy.pose_s],')
    rep(f,'    glaive: "Thunderwheel",','    glaive: "Thunderwheel",\n    axeflail: "Chain Breaker",')
    rep(f,'    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40,',
          '    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40, axeflail: 3.6,')
    rep(f,'    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8,',
          '    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8, axeflail: 0.55,')
    rep(f,'    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8,',
          '    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8, axeflail: 5.5,')
    before(f,'    case "chainblade":\n      return a({ name: "Serpent Bind"', '''    case "axeflail":
      return a({ name: "Twin Judgment", desc: "Throw the axe and flail around opposite sides, then draw them together in five independently defendable impacts. The final convergence consumes full Chain Momentum for bonus power.",
        cd: 43, wind: 0.48, active: 1.58, recover: 0.82, dmg: 51, guard: 19, reach: 4.2,
        knock: 0.9, stun: 0.16, style: "raigo_twinned", pose_w: "rgv_w", pose_s: "rgv_s" });
''')
    before(f,'function sickle(): Record<string, Attack> {', '''/** RAIGO_IRON_BASTION_V1: axe works inside, ball outside; proper per-hit defense checks. */
function axeFlail(): Record<string, Attack> {
  return {
    l1: a({ name:"Iron Entry", wind:.18, active:.09, recover:.24, dmg:57, guard:18,
      reach:2.30, lunge:1.6, knock:.8, stun:.18, style:"raigo_axe", pose_w:"rg1_w", pose_s:"rg1_s", next:"l2" }),
    l2: a({ name:"Outer Orbit", wind:.18, active:.11, recover:.28, dmg:75, guard:24,
      reach:3.65, lunge:.75, knock:1.8, stun:.25, style:"raigo_ball", pose_w:"rg2_w", pose_s:"rg2_s", next:"l3" }),
    l3: a({ name:"Axe Return", wind:.19, active:.11, recover:.29, dmg:69, guard:22,
      reach:2.55, lunge:1.2, knock:1.2, stun:.23, style:"raigo_axe", pose_w:"rg3_w", pose_s:"rg3_s", next:"l4" }),
    l4: a({ name:"Iron Cross", wind:.28, active:.15, recover:.47, dmg:106, guard:35,
      reach:3.8, lunge:1.0, knock:4, stun:.41, style:"raigo_ball", pose_w:"rg4_w", pose_s:"rg4_s" }),
    heavy: a({ name:"Crushing Verdict", wind:.39, active:.15, recover:.66, dmg:180, guard:63,
      reach:3.9, lunge:.75, knock:6.8, stun:.60, heavy:true, style:"raigo_execute", pose_w:"rgh_w", pose_s:"rgh_s" }),
    z: a({ name:"Iron Comet", desc:"Overhead ball orbit, a long-range release and a chain-assisted return. Three separate blockable/parryable impacts; the last clean hit reels the enemy in.",
      cd:9, wind:.30, active:1.0, recover:.49, dmg:57, guard:22, reach:4.7, lunge:.35,
      knock:.9, stun:.18, style:"raigo_comet", pose_w:"rgz_w", pose_s:"rgz_s" }),
    x: a({ name:"Chain Reversal", desc:"Brace both weapons in a 0.36s counter stance. Successfully catching an attack redirects the flail into a counterattack; missing the read leaves recovery.",
      cd:11, type:"buff", mode:"counter", duration:.36, wind:.04, active:.04, recover:.60,
      style:"raigo_counter", pose_w:"rgx_w", pose_s:"rgx_s" }),
    c: a({ name:"Iron Tempest", desc:"Alternate axe and spiked-ball attacks across five timed angles. Each contact can be blocked, parried, clashed, or dodged.",
      cd:17, wind:.32, active:1.42, recover:.60, dmg:49, guard:17,
      reach:3.9, lunge:.55, knock:.8, stun:.14, style:"raigo_tempest", pose_w:"rgc_w", pose_s:"rgc_s" }),
  };
}

''')
    before(f,'const CHAINBLADE: Record<string, Pose> = {', '''// RAIGO_IRON_BASTION_V1: rooted, shoulder-driven axe and left-handed flail.
// Weapon itself supplies continuous ball orbit while these keyframes control footwork/arms.
const AXE_FLAIL: Record<string, Pose> = {
  ...GLAIVE,
  idle:P([.15,-.29,0],[-.07,.20,0],[-.69,.19,-.27],[.37,.02,-.10],[-.92,-.26,.32],[.33,0,.12],[-.27,0,.16],[.24,0,-.16],-.13),
  block:P([.28,-.12,0],[-.03,.12,0],[-1.31,.20,-.33],[.46,0,-.12],[-1.48,-.33,.39],[.37,0,.06],[-.49,0,.18],[.43,0,-.15],-.22),
  charge:P([.30,-.46,0],[.02,.29,0],[-1.78,.39,-.25],[.54,0,-.12],[-1.27,-.30,.34],[.42,0,.1],[-.56,0,.16],[.5,0,-.13],-.18),
  rg1_w:P([.17,-.66,.04],[0,.38,0],[-1.66,-.50,-.42],[.58,0,-.20],[-1.06,-.29,.41],[.48,0,.13],[-.48,0,.14],[.41,0,-.13],-.18),
  rg1_s:P([.25,.50,-.06],[-.11,-.25,0],[-.91,.59,-.38],[.17,0,.18],[-1.37,.22,.37],[.31,0,.1],[-.58,0,.18],[.49,0,-.15],-.20),
  rg2_w:P([.14,.60,.04],[-.05,-.36,0],[-1.12,.31,-.31],[.4,0,-.17],[-2.04,-.48,.40],[.47,0,.15],[-.52,0,.15],[.5,0,-.13],-.16),
  rg2_s:P([.17,-.59,-.06],[-.07,.38,0],[-1.43,-.12,-.27],[.31,0,.13],[-1.50,.55,.41],[.18,0,.28],[-.48,0,.18],[.48,0,-.16],-.17),
  rg3_w:P([.25,.55,.02],[-.05,-.25,0],[-1.90,.49,-.38],[.58,0,-.04],[-1.25,.31,.33],[.24,0,.1],[-.51,0,.2],[.39,0,-.17],-.17),
  rg3_s:P([.32,-.49,-.04],[-.07,.27,0],[-.60,-.51,-.42],[.20,0,.28],[-1.12,-.25,.39],[.28,0,.17],[-.59,0,.16],[.56,0,-.16],-.23),
  rg4_w:P([-.10,-.62,.04],[.1,.38,0],[-2.33,-.36,-.36],[.62,0,-.12],[-2.28,.29,.32],[.52,0,.17],[-.57,0,.14],[.40,0,-.14],-.16),
  rg4_s:P([.47,.40,0],[-.20,-.13,0],[-.89,.54,-.37],[.19,0,.29],[-1.08,-.42,.31],[.26,0,.1],[-.76,0,.15],[.61,0,-.17],-.26),
  rgh_w:P([-.23,-.40,0],[.08,.26,0],[-2.62,.31,-.23],[.49,0,-.07],[-2.22,-.31,.3],[.44,0,.13],[-.57,0,.15],[.36,0,-.17],-.15),
  rgh_s:P([.55,.27,0],[-.24,-.08,0],[-.61,.31,-.41],[.2,0,.31],[-.83,-.18,.41],[.2,0,.18],[-.74,0,.17],[.63,0,-.16],-.27),
  rgz_w:P([.07,-.30,0],[.02,.30,0],[-.99,.17,-.33],[.4,0,-.13],[-2.43,-.17,.35],[.57,0,.15],[-.39,0,.17],[.37,0,-.14],-.12),
  rgz_s:P([.13,.31,0],[-.13,-.26,0],[-1.40,.36,-.31],[.22,0,.24],[-1.74,.50,.34],[.38,0,.14],[-.51,0,.15],[.48,0,-.15],-.17),
  rgx_w:P([.32,-.19,0],[-.06,.15,0],[-1.27,.15,-.31],[.37,0,-.16],[-1.48,-.31,.38],[.38,0,.16],[-.57,0,.18],[.50,0,-.17],-.22),
  rgx_s:P([.17,.37,0],[-.10,-.14,0],[-1.25,.44,-.28],[.34,0,.22],[-1.64,.31,.35],[.38,0,.1],[-.62,0,.17],[.55,0,-.13],-.19),
  rgc_w:P([.18,-.63,0],[.03,.25,0],[-1.81,-.21,-.39],[.47,0,-.14],[-1.73,-.37,.41],[.42,0,.12],[-.52,0,.19],[.47,0,-.15],-.18),
  rgc_s:P([.22,.67,0],[-.13,-.28,0],[-1.37,.68,-.38],[.22,0,.29],[-1.61,.49,.42],[.19,0,.24],[-.60,0,.16],[.54,0,-.15],-.22),
  rgv_w:P([-.22,-.41,0],[.12,.21,0],[-2.50,-.33,-.33],[.51,0,-.07],[-2.34,.25,.38],[.55,0,.11],[-.62,0,.12],[.39,0,-.14],-.17),
  rgv_s:P([.44,.51,0],[-.18,-.18,0],[-1.01,.52,-.35],[.22,0,.31],[-1.13,-.42,.46],[.23,0,.19],[-.71,0,.15],[.54,0,-.16],-.24),
};

''')
    rep(f,'  glaive: GLAIVE,','  glaive: GLAIVE,\n  axeflail: AXE_FLAIL,')

def add_ai():
    f='src/game/ai.ts'
    before(f,'  zarek: { range: 2.10, heavy: 0.30, combo: 0.91, bait: 0.35, pressure: 0.86, skillBias: [1.3, 1.2, 1.45] },',
       '  // RAIGO_IRON_BASTION_V1: hold midrange, guard against rushdown, punish approach.\n  raigo: { range: 3.35, heavy: 0.30, combo: 0.73, bait: 0.69, pressure: 0.55, skillBias: [1.35, 1.60, 1.22] },\n')

def add_fighter():
    f='src/game/fighter.ts'
    rep(f,'  // ZENITH_IRON_SOVEREIGN_V1_20261108 — pure game-side spear state.', '''  // RAIGO_IRON_BASTION_V1 — host-owned momentum; client receives snapshot.
  raigoMomentum = 0;
  raigoMomentumT = 0;
  private raigoLastAward = "";
  earnRaigoMomentum(token: string) {
    if (this.kit !== "axeflail" || this.isDown() || token === this.raigoLastAward) return;
    this.raigoLastAward = token;
    this.raigoMomentum = Math.min(3, this.raigoMomentum + 1);
    this.raigoMomentumT = 5.0;
  }
  consumeRaigoMomentum() {
    if (this.raigoMomentum !== 3) return false;
    this.raigoMomentum = 0;
    this.raigoMomentumT = 0;
    return true;
  }
  // ZENITH_IRON_SOVEREIGN_V1_20261108 — pure game-side spear state.''')
    before(f,'    this.frostShieldT = Math.max(0, this.frostShieldT - dt);', '''    if (this.kit === "axeflail" && this.raigoMomentum > 0) {
      this.raigoMomentumT = Math.max(0, this.raigoMomentumT - dt);
      if (this.raigoMomentumT === 0) this.raigoMomentum = 0;
    }
''')
    # Replicate two appended fields with dynamically chosen indices, preserving previous installs.
    src=T[f]
    m=re.search(r'(?m)^\s*\+this\.frostShieldT\.toFixed\(2\)(?:, this\.dragonRhythm, \+this\.dragonRhythmT\.toFixed\(2\))?(?:, this\.gravityMode[^;]*?)?\];',src)
    if m is None:
        # Nythera may already have appended its state; append at the end of snapshot line.
        old=re.search(r'(?m)^\s*\+this\.kaizenSpinSpeed\.toFixed\(2\).*?\];',src)
        if old is None: raise RuntimeError('fighter.ts: snapshot layout is unfamiliar')
        rep(f,old.group(0),old.group(0)[:-2]+', this.raigoMomentum, +this.raigoMomentumT.toFixed(2)];')
    else:
        rep(f,m.group(0),m.group(0)[:-2]+', this.raigoMomentum, +this.raigoMomentumT.toFixed(2)];')
    # Correct index must be number of fields in latest snapshot, not last applied migration.
    snap_before=src[src.index('  snapshot(): any[] {'):src.index('  applySnapshot(s: any[]) {')]
    snap_line=snap_before[snap_before.index('return [')+8:snap_before.index('];',snap_before.index('return ['))]
    # Field counting using commas at top level (the snapshot has no array nesting).
    depth=0;fields=1
    for char in snap_line:
        if char in '([{':depth+=1
        elif char in ')]}':depth-=1
        elif char==',' and depth==0:fields+=1
    offset=fields
    before(f,'    this.hp = s[8];', f'''    // RAIGO_IRON_BASTION_V1: appended without modifying existing network positions.
    this.raigoMomentum = s.length > {offset} ? s[{offset}] : 0;
    this.raigoMomentumT = s.length > {offset+1} ? s[{offset+1}] : 0;
''')
    # Both live update and puppet update send their current attack pose to the weapon.
    # Preserve the existing Nythera/scythe or default glaive pose routing.
    pose_lines=[line for line in T[f].splitlines() if 'this.model.glaivePose = this.kit' in line]
    if len(pose_lines)!=2: raise RuntimeError('fighter.ts: unknown weapon-pose routing')
    for line in set(pose_lines):
        rep(f,line, line+'\n    this.model.raigoPose = this.kit === "axeflail" ? (this.state === S.WIN ? "raigo_show" : this.poseName) : "idle";\n    this.model.raigoProgress = this.kit === "axeflail" && this.atk ? Math.max(0, Math.min(1, (this.stateT - this.atk.wind)/Math.max(.08,this.atk.active))) : 0;',pose_lines.count(line))
    before(f,'        // NYX_SHADOW_COMBAT_AIR_2_V1: fast dagger contact, compact recover, no wide robotic arms.', '''        // RAIGO_IRON_BASTION_V1: alternating real axe+ball grip silhouettes.
        if (this.kit === "axeflail" && a) {
          if (["raigo_comet","raigo_tempest","raigo_twinned"].includes(a.style)) {
            const elapsed=this.stateT-a.wind;
            const beats=a.style==="raigo_comet" ? ["rgz_s","rg2_s","rgz_s"] :
              a.style==="raigo_tempest" ? ["rg1_s","rg2_s","rg3_s","rg2_s","rg4_s"] :
              ["rgv_s","rg2_s","rg3_s","rg4_s","rgh_s"];
            const count=beats.length;
            p=elapsed<0 ? a.pose_w : beats[Math.min(count-1,Math.floor(elapsed/Math.max(.08,a.active/count)))];
            sp=elapsed<0 ? 19 : 49;
          } else if (this.atkPhase === 0) { p=a.pose_w; sp=20; }
          else if (this.atkPhase === 1) { p=a.pose_s; sp=52; }
          else if (this.stateT<a.wind+a.active+a.recover*.72) { p=a.pose_s; sp=17; }
          else { p="idle"; sp=11; }
          break;
        }
''')

def add_game():
    f='src/game/game.ts'
    rep(f,'    this.swingSound(f, a);', '''    this.swingSound(f, a);
    // RAIGO_IRON_BASTION_V1 — true melee collisions on each individual weapon pass.
    if (f.kit === "axeflail") {
      const tip=f.model.raigoFlailTip?.getWorldPosition(new THREE.Vector3()) ?? f.chest();
      this.fxp("sparks",tip,"#e5b46d",a.style==="raigo_execute"?21:10,4.5);
      if (["raigo_comet","raigo_tempest","raigo_twinned"].includes(a.style)) {
        this.raigoSequenceSwing(f,a); return;
      }
      if (a.type === "melee") { this.melee(f,a); return; }
    }
''')
    before(f,'  private melee(f: Fighter, a: Attack): boolean {', '''  /** RAIGO_IRON_BASTION_V1: collision stays with the existing guard/parry/clash pipeline. */
  private raigoSequenceSwing(f: Fighter, a: Attack) {
    const count=a.style==="raigo_comet"?3:a.style==="raigo_tempest"?5:5;
    const step=a.active/count;
    const serial=f.swingSerial, round=this.round;
    for (let i=0; i<count; i++) this.laterCombo(f,i*step,()=>{
      if (round!==this.round || f.isDown() || f.swingSerial!==serial ||
        f.state!==S.ATTACK || f.atk?.style!==a.style) return;
      const last=i===count-1;
      const isAxe=a.style!=="raigo_comet" && i%2===0;
      const attack: Attack={...a, id:`${a.id}_${i+1}`,
        style:a.style==="raigo_twinned" && last?"raigo_execute":
          a.style==="raigo_comet" && last?"raigo_comet_pull":
          isAxe?"raigo_axe":"raigo_ball",
        dmg:last ? a.dmg*1.75 : a.dmg*(i%2===0?.90:1.0),
        guard:last ? a.guard*1.8 : a.guard,
        knock:last ? (a.id==="v"?6.0:3.0) : 0.65,
        stun:last ? .38 : .12,
        reach:isAxe && !last?2.65:a.reach, heavy:false,
      };
      f.model.raigoBeat=i;
      const tip=f.model.raigoFlailTip?.getWorldPosition(new THREE.Vector3()) ?? f.chest();
      this.fxp("slashes",tip,"#e3bb86");
      this.fxp("sparks",tip,last?"#fff0ca":"#b7a27d",last?25:12,last?6:3);
      if(last) this.fxp("ring",f.chest(),"#e0a85c",1.1,.18,.65);
      this.melee(f,attack);
    });
  }

''')
    # Prevent spiked-ball clipping at point blank, axe remains efficient in close.
    before(f,'      const hitPos = d.chest().addScaledVector(dir, -0.15);', '''      // RAIGO_IRON_BASTION_V1: a swinging flail has an actual blind spot near the body.
      if (f.kit === "axeflail" && (a.style==="raigo_ball" || a.style==="raigo_comet_pull") && dist<1.42) continue;
''')
    before(f,'      if (f.kit === "chainblade" && a.style === "chain_predator_hook" &&', '''      // A clean third hit briefly reels the target inward, but never through block/parry.
      if (f.kit === "axeflail" && a.style === "raigo_comet_pull" &&
          (result === "hit" || result === "crit") && d instanceof Fighter) {
        const toward=f.root.position.clone().sub(d.root.position).setY(0);
        const amount=Math.min(.9,Math.max(0,toward.length()-2.0));
        if (toward.lengthSq()>1e-5 && amount>0) {
          const dest=d.root.position.clone().addScaledVector(toward.normalize(),amount);
          if (d.stage) dest.x=THREE.MathUtils.clamp(dest.x,d.stage.blast.l+1,d.stage.blast.r-1);
          else { const radius=Math.hypot(dest.x,dest.z); if(radius>d.arenaRadius-.4) {
            const s=(d.arenaRadius-.4)/radius; dest.x*=s; dest.z*=s;
          }}
          d.root.position.copy(dest);
          this.fxp("ring",d.chest(),"#efb870",.75,.16,.70);
        }
      }
''')
    # Momentum from actual confirmed hits, once per attack pulse; finisher only consumes on contact.
    hit_line=next((line for line in T[f].splitlines() if 'const result = d.receiveHit(attacker, zenithAttack,' in line),None)
    if hit_line is None: raise RuntimeError('game.ts: hit-resolution call changed')
    before(f,hit_line, '''    // RAIGO_IRON_BASTION_V1: empower only confirmed heavy hits, don't consume on whiff.
    const raigoEmpowered=attacker instanceof Fighter && attacker.kit === "axeflail" &&
      attacker.raigoMomentum===3 && (a.style==="raigo_execute" || a.id==="heavy");
    const raigoAttack=raigoEmpowered ? {...zenithAttack,dmg:zenithAttack.dmg*1.28,
      guard:zenithAttack.guard*1.25,knock:zenithAttack.knock*1.15} : zenithAttack;
''')
    rep(f,hit_line, hit_line.replace('zenithAttack,','raigoAttack,') + '''
    if (attacker instanceof Fighter && attacker.kit === "axeflail" &&
        (result === "hit" || result === "crit" || result === "ko")) {
      if (raigoEmpowered) {
        attacker.consumeRaigoMomentum();
        this.fxp("ring",d.chest(),"#fff1b5",1.55,.24,.83);
        this.fxp("num",d.chest().add(new THREE.Vector3(0,.75,0)),"IRON VERDICT","#ffe5ad",.78);
      } else if (!a.id.startsWith("v_")) {
        // The ultimate cannot charge its own final empowered hit for free.
        attacker.earnRaigoMomentum(`${attacker.swingSerial}:${a.id}`);
      }
    }
''')
    rep(f,'      case "parry": {\n        const df = d as Fighter;', '''      case "parry": {
        const df = d as Fighter;
        if (df.kit === "axeflail") {
          df.earnRaigoMomentum(`parry:${this.time.toFixed(3)}`);
          this.fxp("sparks",df.chest(),"#f4c982",20,5);
        }''')
    rep(f,'      case "counter": {\n        const df = d as Fighter;', '''      case "counter": {
        const df = d as Fighter;
        if (df.kit === "axeflail") {
          df.earnRaigoMomentum(`counter:${this.time.toFixed(3)}`);
          this.fxp("ring",df.chest(),"#f3c47e",1.1,.22,.72);
        }''')
    rep(f,'    for (const fighter of [a, b]) this.awardZarekClash(fighter);', '''    for (const fighter of [a, b]) {
      this.awardZarekClash(fighter);
      if (fighter.kit === "axeflail") fighter.earnRaigoMomentum(`clash:${this.time.toFixed(3)}`);
    }''') if '    for (const fighter of [a, b]) this.awardZarekClash(fighter);' in T[f] else before(f,'      this.awardZarekClash(fighter);','      if (fighter.kit === "axeflail") fighter.earnRaigoMomentum(`clash:${this.time.toFixed(3)}`);\n')
    before(f,'      if (f.kit === "hammer") passives.push({ label: "HEARTS",',
          '      if (f.kit === "axeflail") passives.push({ label: "MOMENTUM", value: `${f.raigoMomentum}/3 · ${f.raigoMomentumT.toFixed(1)}s` });\n')
    rep(f,'chainBindKind: f.chainBindKind,', 'chainBindKind: f.chainBindKind, raigoMomentum: f.raigoMomentum, raigoMomentumT: f.raigoMomentumT,')

def add_model():
    f='src/game/model.ts'
    rep(f,'  private glaivePivot: THREE.Group | null = null;', '''  private glaivePivot: THREE.Group | null = null;
  // RAIGO_IRON_BASTION_V1 — physically separate hand grips, articulated ball and curved links.
  private raigoAxe: THREE.Group | null = null;
  private raigoBallOrbit: THREE.Group | null = null;
  raigoFlailTip: THREE.Object3D | null = null;
  private raigoChainFrom: THREE.Object3D | null = null;
  private raigoLinks: THREE.Mesh[] = [];
  private raigoAngle = 0;
  private raigoRadius = .72;
  private raigoLastPose = "";
  private raigoSwingT = 0;
  raigoPose = "idle";
  raigoProgress = 0;
  raigoBeat = 0;''')
    rep(f,'      case "glaive": this.buildGlaive(); break;', '      case "glaive": this.buildGlaive(); break;\n      case "axeflail": this.buildRaigoAxeFlail(); break;')
    before(f,'  private buildGlaive() {', '''  /** RAIGO_IRON_BASTION_V1: one full steel axe in the right hand, one freely swinging
   * spiked ball controlled from the left wrist. Decorative chain is rooted in the fighter,
   * never deforms or stretches the weapon meshes. Hit tests remain server-authoritative. */
  private buildRaigoAxeFlail() {
    const steel=this.tn("#b9bdbf"), edge=this.tn("#e7e0cc"), iron=this.tn("#31383a"),
      bronze=this.tn("#be9158"), dark=this.tn("#42494b");
    const axe=pivot(this.hand_r,[0,0,0],[PI/2,0,0]);
    this.raigoAxe=axe;
    mesh(axe,cyl(.038,.045,1.36,10),dark,[0,.36,0]);
    mesh(axe,cyl(.051,.050,.38,10),iron,[0,.18,0]);
    for(const y of [-.18,.15,.50,.89]) mesh(axe,torus(.04,.055),bronze,[0,y,0],[PI/2,0,0]);
    const head=pivot(axe,[0,.93,0]);
    mesh(head,box(.24,.26,.13),iron,[.025,0,0]);
    const outline=new THREE.Shape();
    outline.moveTo(.03,.20);outline.lineTo(.19,.36);
    outline.bezierCurveTo(.46,.30,.61,.15,.67,.06);
    outline.bezierCurveTo(.50,-.04,.48,-.19,.50,-.34);
    outline.lineTo(.20,-.22);outline.lineTo(.03,-.17);outline.closePath();
    const blade=new THREE.ExtrudeGeometry(outline,{depth:.055,bevelEnabled:true,bevelSize:.019,bevelThickness:.015,bevelSegments:1,steps:1});
    mesh(head,blade,steel,[0,0,-.027]);
    // Bright sharpened rim follows the cutting crescent, not the entire blade.
    const glint=pivot(head,[.02,.015,.05]);
    for(let j=0;j<4;j++) {
      const x=.37+j*.055, y=.25-j*.115;
      mesh(glint,box(.09,.018,.015),edge,[x,y,0],[0,0,-.25-j*.20]);
    }
    mesh(head,cyl(.13,.13,.10,8),bronze,[.04,0,0],[PI/2,0,0]);
    mesh(head,sphere(.065,10),iron,[.04,0,.095]);
    const from=pivot(axe,[0,-.29,0]);
    mesh(axe,sphere(.060,12),bronze,[0,-.29,0]);
    this.raigoChainFrom=from;
    this.bladeBase=pivot(axe,[0,.75,0]);
    this.bladeTip=pivot(head,[.54,.04,0]);
    // Flail is independent: left hand can circle as right hand winds up the axe.
    const ballOrbit=pivot(this.hand_l,[0,.02,0]);
    this.raigoBallOrbit=ballOrbit;
    const ball=pivot(ballOrbit,[0,1.14,0]);
    this.raigoFlailTip=ball;
    mesh(ball,sphere(.195,20),iron);
    mesh(ball,sphere(.174,20),steel);
    for(let n=0;n<12;n++) {
      const a=(n+.5)*PI*2/12;
      const y=(n%3-1)*.105;
      const axis=new THREE.Vector3(Math.cos(a),y*1.6,Math.sin(a)).normalize();
      const point=axis.clone().multiplyScalar(.18);
      const spike=mesh(ball,new THREE.ConeGeometry(.061,.18,7),dark,point);
      spike.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),axis);
    }
    mesh(ball,sphere(.078,12),bronze,[0,.17,0]);
    // Segment joints stay connected every rendered frame, including selection camera.
    for(let i=0;i<24;i++) {
      const link=mesh(this,cyl(.014,.014,1,7),i%2?steel:dark);
      link.castShadow=false;
      this.raigoLinks.push(link);
    }
    this.castPoint=ball;
    this.shieldNode=axe;
  }

  /** Animated chain links are visual-only; a curved Bezier connects ACTUAL world-space
   * axe and ball endpoints. Rotation phase continues across combo hits rather than resetting. */
  private updateRaigoWeapon(dt:number) {
    if(!this.raigoAxe || !this.raigoBallOrbit || !this.raigoFlailTip || !this.raigoChainFrom) return;
    const pose=this.raigoPose;
    const show=pose==="raigo_show";
    const phase=((this.presentationT%9.6)+9.6)%9.6;
    if(pose!==this.raigoLastPose) {this.raigoLastPose=pose;this.raigoSwingT=0;}
    else this.raigoSwingT+=dt;
    const release=show && phase>5.2 && phase<7.6;
    const ballAttack=show || /^rg[24]_s$/.test(pose) || ["rgz_s","rgc_s","rgv_s","rgh_s"].includes(pose);
    const rate=ballAttack?(show?9.7:12.0):pose.endsWith("_w")?4.6:1.8;
    this.raigoAngle+=Math.min(dt,.05)*rate;
    const radius=show?(phase<1.2?.68:phase<5.2?1.50:phase<7.6?2.28:.83):
      ballAttack?2.05:pose.endsWith("_w")?1.28:.76;
    this.raigoRadius=THREE.MathUtils.damp(this.raigoRadius,radius,show?8:12,dt);
    const x=show?(phase<3.8 ? -.85 : phase<6.9 ? -1.52 : -1.05):
      ballAttack? -1.48 : pose.endsWith("_w")?-.68:-.98;
    const z=show?(phase<3.8?.32:phase<6.9?.82:.12):ballAttack?.8:.13;
    this.raigoBallOrbit.rotation.x=THREE.MathUtils.damp(this.raigoBallOrbit.rotation.x,
      x+Math.sin(this.raigoAngle)*.41,18,dt);
    this.raigoBallOrbit.rotation.y=THREE.MathUtils.damp(this.raigoBallOrbit.rotation.y,
      z+Math.cos(this.raigoAngle*.75)*.48,14,dt);
    this.raigoBallOrbit.rotation.z=THREE.MathUtils.damp(this.raigoBallOrbit.rotation.z,
      Math.sin(this.raigoAngle)*.85,17,dt);
    this.raigoFlailTip.position.y=THREE.MathUtils.damp(this.raigoFlailTip.position.y,
      this.raigoRadius,11,dt);
    // Heavy axle rotates in the hand. Trailing flail continues its swing independently.
    const axeAngles: Record<string,[number,number,number]>={
      idle:[PI/2,.10,-.15],block:[1.24,.35,.28],
      rg1_w:[2.10,-.50,-.26],rg1_s:[.65,.55,.29],
      rg2_w:[1.45,.22,-.20],rg2_s:[1.24,-.36,.26],
      rg3_w:[2.26,.48,-.18],rg3_s:[.67,-.58,.33],
      rg4_w:[2.40,-.27,-.24],rg4_s:[.65,.51,.31],
      rgh_w:[2.64,-.27,-.10],rgh_s:[.48,.29,.20],
      rgz_w:[1.80,-.33,-.14],rgz_s:[1.19,.28,.14],
      rgx_w:[1.34,-.22,-.10],rgx_s:[.91,.22,.23],
      rgc_w:[2.15,-.36,-.17],rgc_s:[.85,.42,.28],
      rgv_w:[2.57,-.35,-.13],rgv_s:[.70,.51,.29],
    };
    const a=axeAngles[pose]??axeAngles.idle;
    const target=new THREE.Quaternion().setFromEuler(new THREE.Euler(a[0],a[1],a[2],"YXZ"));
    if(show) target.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),
      phase<3.2? Math.sin(phase*5)*.52 : phase<7.5? Math.sin(phase*8)*.7:0));
    this.raigoAxe.quaternion.slerp(target,1-Math.exp(-(ballAttack?21:11)*dt));
    // For selection, a genuine spinning ball never vanishes or detaches from its chain.
    this.updateMatrixWorld(true);
    const start=this.worldToLocal(this.raigoChainFrom.getWorldPosition(new THREE.Vector3()));
    const end=this.worldToLocal(this.raigoFlailTip.getWorldPosition(new THREE.Vector3()));
    const mid=start.clone().lerp(end,.5);
    const delta=end.clone().sub(start);
    mid.y-=Math.min(.46,delta.length()*.16)*(release?.35:1);
    mid.x+=Math.sin(this.raigoAngle-.45)*(show?.18:.09);
    const up=new THREE.Vector3(0,1,0);
    const n=this.raigoLinks.length;
    const path=(u:number)=>start.clone().multiplyScalar((1-u)*(1-u))
      .addScaledVector(mid,2*u*(1-u)).addScaledVector(end,u*u);
    for(let i=0;i<n;i++) {
      const p=path(i/n),q=path((i+1)/n);
      const d=q.sub(p),len=d.length();
      const link=this.raigoLinks[i];
      link.position.copy(p).addScaledVector(d,.5);
      link.quaternion.setFromUnitVectors(up,d.normalize());
      link.scale.set(1,len,1);
    }
  }

''')
    # Chain must update *after* the skeleton has moved for the frame.
    before(f,'    if (this.kit === "chainblade") this.updateChainblade(dt);', '    if (this.kit === "axeflail") this.updateRaigoWeapon(dt);\n')
    # Special VRM consideration: two hands independently grip handles, not same shaft.
    rep(f,'this.kit === "sickle" ? 0.18', 'this.kit === "axeflail" ? 0.24 : this.kit === "sickle" ? 0.18')
    rep(f,'this.kit === "sickle" ? "feral"', 'this.kit === "axeflail" ? "heavy" : this.kit === "sickle" ? "feral"')
    rep(f,' : VRM_WEAPON_SCALE; // ZAREK_PROPORTIONATE_GLAIVE_V1',
        ' : this.kit === "axeflail" ? 0.83 : VRM_WEAPON_SCALE; // ZAREK_PROPORTIONATE_GLAIVE_V1')

def add_presentation():
    f='src/game/preview.ts'
    # Independent selection phase, doesn't overwrite existing Nythera / Zephyr selection.
    if 'const phase = this.mode === "victory" ? this.poseT : this.poseT % 6.2;' in T[f]:
        rep(f,'const phase = this.mode === "victory" ? this.poseT : this.poseT % 6.2;',
            'const phase = this.mode === "victory" ? this.poseT : this.poseT % (this.lookName.toLowerCase() === "raigo" ? 9.6 : 6.2);')
    elif 'this.poseT % (who === "nythera" ?' in T[f]:
        rep(f,'this.poseT % (who === "nythera" ?',
            'this.poseT % (who === "raigo" ? 9.6 : who === "nythera" ?')
    elif 'this.poseT % (this.lookName.toLowerCase() === "zephyr" ?' in T[f]:
        rep(f,'this.poseT % (this.lookName.toLowerCase() === "zephyr" ?',
            'this.poseT % (this.lookName.toLowerCase() === "raigo" ? 9.6 : this.lookName.toLowerCase() === "zephyr" ?')
    else:
        raise RuntimeError('preview.ts: unknown selection animation cycle; no files written')
    before(f,'      // Kaizen: a controlled chain orbit,', '''      this.model.raigoPose = who === "raigo" ? "raigo_show" : "idle";
''')
    f='src/game/presentation.ts'
    before(f,'/** Entirely cosmetic; all poses use the same normalized VRM/procedural joints as combat. */', '''// RAIGO_IRON_BASTION_V1: axe and flail are independently moving during presentation.
function raigoShow(seconds:number, base:Pose, mode:"select"|"victory"):Pose {
  const t=mode==="select"?((seconds%9.6)+9.6)%9.6:Math.min(seconds,8.6);
  const beats: Array<[number,Beat]> = [
    [0,{torso:[.17,-.20,0],arm_r:[-.80,.17,-.34],arm_l:[-.95,-.23,.32],hips_y:-.14}],
    [1.1,{torso:[.12,-.52,.03],arm_r:[-1.45,.32,-.41],arm_l:[-1.70,-.37,.38],hips_y:-.17}],
    [2.4,{torso:[-.09,.40,.07],arm_r:[-1.82,.46,-.30],arm_l:[-2.43,.10,.27],hips_y:-.10}],
    [3.5,{torso:[.24,-.37,-.05],arm_r:[-1.50,-.20,-.52],arm_l:[-2.50,.15,.32],hips_y:-.19}],
    [4.6,{torso:[.11,.42,.02],arm_r:[-2.22,.34,-.22],arm_l:[-1.74,-.43,.36],hips_y:-.11}],
    [5.5,{torso:[-.16,-.52,.07],arm_r:[-2.63,-.35,-.29],arm_l:[-2.12,.28,.46],hips_y:-.09}],
    [6.65,{torso:[.18,.54,-.04],arm_r:[-1.90,.45,-.47],arm_l:[-1.52,-.58,.33],hips_y:-.13}],
    [7.6,{torso:[.51,.28,0],arm_r:[-.75,.36,-.40],arm_l:[-.99,-.11,.35],leg_l:[-.52,0,.13],leg_r:[.37,0,-.17],hips_y:-.26,knee:[.49,.46]}],
    [8.6,{torso:[.18,-.20,0],arm_r:[-.80,.17,-.34],arm_l:[-.95,-.23,.32],hips_y:-.14}],
    [9.6,{torso:[.17,-.20,0],arm_r:[-.80,.17,-.34],arm_l:[-.95,-.23,.32],hips_y:-.14}],
  ];
  let i=0;while(i<beats.length-2&&t>beats[i+1][0])i++;
  const lo=beats[i],hi=beats[i+1],u=Math.max(0,Math.min(1,(t-lo[0])/Math.max(.001,hi[0]-lo[0])));
  return between(filled(base,lo[1]),filled(base,hi[1]),u);
}

''')
    rep(f,'  const entry = C[name.toLowerCase()];',
          '  if (name.toLowerCase() === "raigo") return raigoShow(seconds,base,mode);\n  const entry = C[name.toLowerCase()];')

def sql_file():
    return '''-- RAIGO_IRON_BASTION_V1: review after existing migrations; do not apply automatically.
-- Extends the character validation list WITHOUT removing existing roster entries.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina','volta','sylva',
    'nyx','rook','gale','bob','kira','raven','ash','veyr','zarek','kaizen',
    'nesa','roxy','zenith','nythera','zephyr','raigo','leon','sakura','yuki','bruno'
  ]);
$$;
CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
  SELECT ARRAY[
    'aster','vesper','garrick','kaede','ember','marina','nyx','rook','gale',
    'bob','kira','raven','ash','veyr','zarek','kaizen','nesa','roxy',
    'zenith','nythera','zephyr','raigo'
  ]::text[];
$$;
'''

# Temporary circular navy/gold axe-and-flail icons; never overwrite custom art.
ICON_WEBP = {
    'char': (
        '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'
    ),
    'z': (
        'UklGRn4PAABXRUJQVlA4IHIPAACwOQCdASqAAIAAPlEijUQjoiEUCwboOAUEsgBk/yAujzkzZ8bb9jDHnFdB+eP/FeojzAOcX5gP'
        '2u/Z33mv9h+x3uq/wXqAf1j/e9Yt6AH7b+mp+4Pwe/2f/gfuD7X3//6wD/28KB23f2n8nfEp83/b/yy9TStwzO/W78V/bP3Q/tvt'
        '3/ZvBP4A6gX5B/JP8D+YHBHV9/z3qBexn0L/L/mpzD/Xb/Q+4B/Of6D/p/tu52igB/Lf6v/wP8p+YH0t/yv/X/vn+R/cb2j/mn+F'
        '/5/+R+AX+Rf0T/Zf3f/Hf+v/Gf//6ufZ7+2Hsz/sS5gpTW5G5U//wKq9d3ydO4QhcFGlK80HTUijFgDGjc55kFreS/wtrBzlNAey'
        'Z5nH0dhmU9Jb+fO/LYEhoeemISknxWy2DpGCNGG2jAoFHvK9yTsovuvYBvyRfw/C+QNvBJw5BmOdYeSs1cRTVwpW/KKh3azRKulP'
        'Z1lQEYav7Vn4pPV3L81/bdj7h/tqYWlXPVYjaNBD2Unx9ZDcE6QwVLMMWpBGgNgd+90xEuvdqtHU2dqBgnw0rZxKHnYmkUe3z1cA'
        'QK0I33S3MiLBfODoiaK1yWeFbAyLniQ1tnMt6ezLKRm5zn7GhirfAAD+/w1kT0mWzA1RrWiARSJCDdaenvnm2DTNdBvWCcLwBp08'
        'ylv50acv3f+Hb0KECu5kpIoVkjMHyFgGDikQaMYkRA+94oAHN2L7Y1vqZYPRBRdtpB5oGvl+uHgXBfZwm50UEmKw1Kv9XoVSkduv'
        'q0qy+XSUqP/59/lE+SZ4uql741EGhEMFiBkf/o++CuyxtQI0ItlHSSyptVX8Wn83XcvvTERmEfcmO+xLVQ9R2YQAdNwvJyDCHeUN'
        '+/vFowsdNlFV8FhlyvQjxxpRL1LRoLgfNFmHoEKogvT8GQP6NOv32mtZPi/CoiYEz17gyalrON8x1BW82MVf9uOOUDVbqFE9IpNa'
        'bSZ2JSaHt3a0g9kYq3wXrmz0VUtKiqBwIVeecvrtPTgfrrQmmeq0VodMx1UroXJRwx+pycXlofSWS8YGTbJpQfcjN/MQ4+5ViT4V'
        'lA32Xf8QO6slDTIT9HbyepbFKGZEBfd8a//4qaffBr1lP079cCd42azR9eVDu7dkAPe687OeIJJW8llDzfiJvymok4LkO4rKb9RT'
        'tMOOOoRFuTUVf/MzogE2Bi75WGoLXfZO75PCWgFYIRZY7PAmrmDaz2GZv9DSIi6nG4UaQhfyCXh7PttbWWb+KGuDwE9DQ8jY0Wyh'
        'gKIqTJnLu/Dh7ys7yZtGvVB8rxfBypIHdrUrUcZt5lc2EGGmDO13RX14goqDEeo2Os+c6++gvpdTnHHZPgGXgZDwQUxO5/XnOQAl'
        'UmaC0oIfChwy1Oq5qkGXZtmk4gGpBc7/N5K6f9EsFrA2CCrOQwneJ07lqFWtDlEM2NHdJUkLzrPJiITkSyOSd9spgAZLHSTl7Yt6'
        'VDtszn7p6xa4K/4Hhf7fTjaEOgGyo8hHGd7WqRrjnYfdrTVVkQsIn4e8WSKyuJVXylD8WS6QvNE++vq1rA0zNZttnHhoKY8K9Kb8'
        'pGTBc6SZagJw7K/f9fE18mpsNQArM8ieIfB358V2upcGwSbgrOl/o76CVHUme65tv/xlpxWpbp3U7c4YuiC+wk7etlVhqnlP0QoH'
        'DApXzYRuPK0JKKxynrIO8p0UuH50jI/w29QaZTLv7oFUsfdmRFPwqipZAZ1/2/D7Uh6UU+DsHrv5oag4uO+TZhmmra9sG3Wvahie'
        'vaP8ttTBLUOx9EEf0OhbhC8pHvEbYhdtM16s+gjnWT+G+pcvAxS8zqRpTfDngAG+zyo3GNqTJd6fq4n8m8IuFnZiPPsrfeI9wkMm'
        'qD5ePVtMIT1SYmPyqUvnd2IQU7SULr1EYc4T4M2ueOcYL/kpIWjm83tW4fWhwjEFm1MeZBWv0ZDQ/QZsSzom3VVIf53bJrJWqozF'
        'qp7JMCvA7TdgEUlKfrCu/y+fUBOC15XQQhHzBUzKVjcn92jKZ00lcMQ5Cv8lmijGXz7hHB6oqYWb/pBDuJzPjEbH6yabi7HWj/Qa'
        'U38WIjaiMmHimgQRVpq7OzgajuJ0wJ+EvmAGVeRq+Fcnq95ItuDSTmCAIB28hiQ5l2raVg2uRCP/6pMEG4aR1obazGByZNdud6qG'
        'Os7LVb8bhwI6ueOo1VO6JFfBDg1jwP9TMeYXALSBumr66iiG9v0MnUbmMVi5mJUtbdjmlMUj1KJm09euq5dokVbkw+6WF7UPfQLK'
        'TPiHrzfskZ9PDtEpP9/2yvpSregLdWCoaMKWCNvoTWlkLAbm07ddLMMro9QkfqJRJ5EL1VdkNsL2hA/IoGfIidBaGVEP8pHK9vR4'
        'KvAkamvz0UZDpInzjPZJa4N7JbPGDhtgYLFdpr7wSP6IIL0zS24qMTtKqAi56UjWGozUKFVMDff4FXiorZu7Qp+zS/muzYNMwQKy'
        'e11HsFuq6Ze3a/VzY/WFJ1Iqd7zu5j3abie517eImzXcSWWPVzw0jtWnQNDI2iseA1mUzzyy74or4RpIGj7C3Demg/g71EXZEAWS'
        'XLTiphbuEKlGNyXlG4e19T2L8PDiBCKyPf+gmiUf1sStbVvAx4TNaUyCVx1OniUdjMJ15aWYaylTDB8DiurkIMZS+p0B5rNnycU2'
        'y+ybrfw76yh6rGEL3Kc4bPKelLFXXTJQbyxYPKLlYDuGc4dV8KumErO/zV8Se99TezKsTJAAqLYk7HV9pO10kq8bjLMEGW5PQff0'
        'B/0V3GiKk6lV7fE+brAEnDN9Eb75fDX8roTlKFM38L8T9ni/yFlLReZH21Vd1Uc+H4Jvsese5z3imjUZWZ0VL/qRzO5EWZbhs8b2'
        'QSwCoA+YtSfJy3Jabsa/5mOXnsv7l2FRcffNkAZwofqY1V7KQtZPtGowlwsJugdU+y02WI3L0Z03/NJSaB0HMO922Y+z25gJGuX4'
        'wdFpm4sN/YKYAN2kPr53FxvHprQqRzEY7k7sssyuzwMCA8ObHo6kTuHGCnaFhBue0gzoiMhZ0WJsus7s1c/+ffSMql5cnLCC6mBO'
        'jhQfmYDMWL8BPwNjFxgpBkXqE+7cu3VIOlZbfnZ+zNBp+GbBj+pzgVa/kQK6TtwhvHla+ufXEl/w8Sr4fytwzmEkOfc3FOLDBRML'
        'bb/qxCq4H8jDo9xro7YVwBtcJpv5smtM452kSkqF2G/1MgvOjs0h7j1gyKJK02tZuBDl8V5+RSRXCqkQLJPOPvYtc4YA2ZYN/iUT'
        'LKyFt70riVE2X9HffQDm1L9tLmlnJNMgVhLpqxuj7NZZlGO8rqF7PLBmLzQZf+pns8KvfAS9kKK+SI+hJTXNkxxbVvId/gYOI9EO'
        '+1LnyQCh5IBsZURJjvJ2sGq3GmRXbkleabszuXp6+BIAPUOY/kO8JknOQ3Jkj1IzQ/AW73/UAtn27NCIgT+V7+xkP7JkXyhM3Jgv'
        '++pyNG+m8lQOqpGw1AMnaKCd5pzmKSD+2mA4AEin6An/4OlkhHH1f2N+vhlWlnNpVoPz7L/tGHUOXcaXNjaZc3lukyv5JTsWTcrh'
        '1YA8R1sLsMGVUFKZ7M+hkIkSA/OntrCa6uxqbYDFBLEVYJ1V7BScKMwC8oXZFxAOGOgqGIGNSgFjkn9wxOwWGMafpfy1aXiVKHzE'
        'MzA32H0G8/nZ+om6pUjHdyxhA+dtDCFeE5abmhMxKuY0d0sA02Pw5x93yri7dmegDcGWC90iloOG2B1gyluL8Ua+lMa/nMB8m3WI'
        'N5J6QZeF5RCeLmZGRHxzIvLovLdGrb+I9lYdgt8SCuQNiLz/7ZhRdi+qUE0oxrtAIefaByMOuCS6YQO0bWoueDHeXv8hq5JIHfol'
        'f4RUrQB3qJiuVtiJ9h9UYLbP/iKrmGzpR4QXyExZ0SJtnEayc0i4hNws0zseXd+ZIf2dk2aYxdSkG0I/uaxj3drH82DTQ6FhArSJ'
        'R4a9HDTaIcQbIdeksHVYZ0fvV0S2Ww0uMpVxvQygl4f97ursOHQLetIWw5Q9cSU+DPJ5a+4ExG75BhivA25ADRs9FG4mFX6aXIc8'
        '5qNe7itqgSyr4HVbwLCHZcQNndX+tcbbKDIsvurNyePDmAgojtm08dp9jUqqaXyTcHUWBpph92ZiaObL0Zt0pau44Pp/rj/VWB/b'
        'nVD6+DNe8T+6IG1kLzFWpR0b3/N2DVr7rbWTBVqL2OP3BWKgCGhv/bD3VwYqyvT8moMBcwniAjc7SuOMR3lMxpqmZ0eq19ibm79O'
        'r7B6JP4Q+5WnERpT8WQbaO3k/cnwfwX92RDm97FB2vRPoX3Tlh25ISQoE/fZar9GdADykjdW8c4ivzGZpCu/HNHTKAV7OfWetYIo'
        'H6aWyIEau2Qw/k5+Ga4HwChjAXa0A/PpV+OxndEF8Uh0iREw1zrgbNFhkBQvhvEuCEZHjwUt7LHwQEbTiPzvxugAPmcozh1phz2T'
        'rSH8G+zWT6EF0+/Xk4IHUpn6/O6qJHsZvLhFKwmAqEkwwu2zbYe7JBq0AfsZ4zl2zW3x62SANnBBv3V3c4nFgBgAaC9wxq2JzfGE'
        'strz0LIUIxnJHLKXwwFi9hzVAOPzjHq8yqokJnq4BJvetwD3SFtRoWhIZ8yMAXndcsQAentCbkdYgNgf9GXVzZAHvavbPNVZIMjn'
        '8XdmROkXar8N/kO2mZ/RUtFY2ynwY2P6yIIRWKubJmopZ3USkhspbaeGyMrO/LnKqJy0mJdG39eZ/N2FzUJo3QMTKc6bZot3O4U3'
        'gjsFqgm+wdgc0+xnSiSevh/zk3XvL86Q3fqHTRz7WY21qik6pwTjrNzao5aRgbnOjdNHX4gqpQTTUZNMW2SokUACupc6e0Ivp37T'
        'mPeirYODbI6Un0cTJ7XqgOda29RES7Z7UA6JaCwR3kPOGeEIPlfMjOC3XKHK31cyNs3nysOs3xAE7Svv0mN0MD3ef4vZgo/a0r8e'
        'fXnlbQHL2wbL45H50hJSt6TI2MjZHUa6dn76NyngNSTWhjNpTeHDz8NeVmxbNdyf7Hxnl14rzEAX2xJu+rFm8OnVS5vMPFsFWH3u'
        'Bv7SMJHqshFjrGULugb3UvjGdvmDVCO7u3D2eq5Y5RamsMDcM//yr21cKsXk5PHaW2inlXXuRX/P/ptscxw008FiJqi/+nvPbWPK'
        'Sn0uFJr4gOoinpPiqg3HkAqN3PyNs/31qMqqPM2lhiP6/5hqhSjyIBdN//cU7BQyYcsOq/S1gGd+f2wDqO9qfnrH6ajjAAAAAAA='
    ),
    'x': (
        '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'
        'XcR4DYaKauh0SmkX/JAAAA=='
    ),
    'c': (
        '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'
        'kaG6+gLYxsAAAA=='
    ),
    'v': (
        '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'
    ),
}

def install_icons(root:pathlib.Path):
    import base64
    for key,value in ICON_WEBP.items():
        rel = pathlib.Path("public/icons/chars/raigo.webp" if key == "char" else f"public/icons/skills/axeflail-{key}.webp")
        dst=root/rel
        if dst.exists():
            print("  kept existing icon",rel)
            continue
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(base64.b64decode("".join(value)))
        print("  + icon",rel)

# V2 upgrades one-file V1, or installs V1 and upgrades its generated sources in memory.
# Python stdlib only. The project is not modified until every anchor has passed.
V2_MARK = 'RAIGO_IRON_BASTION_V2'

def v2_rep(path: str, old: str, new: str, count: int = 1):
    got = T[path].count(old)
    if got != count:
        raise RuntimeError(f'{path}: V2 expected {count} occurrence(s) of {old[:90]!r}, got {got}; nothing written')
    T[path] = T[path].replace(old, new, count)

def v2_upgrade():
    kits='src/game/kits.ts'; fighter='src/game/fighter.ts'; game='src/game/game.ts'; model='src/game/model.ts'
    v2_rep(kits,'axeflail: { hp: 2500, guard: 100, move: 3.30, walk: 2.60, parry: 0.20, jump: 6.8 }',
           'axeflail: { hp: 2375, guard: 90, move: 3.35, walk: 2.60, parry: 0.18, jump: 6.8 }')
    # 0.55 is the parry-counter LUNGE distance, not an animation speed: deliberately short.
    v2_rep(kits,'glaive: 2.40, axeflail: 3.6,','glaive: 2.40, axeflail: 3.15,')
    # Keep weapon range near the actual flail arc, and make the long-range skills a commitment.
    changes={
        'reach:2.30, lunge:1.6':'reach:2.22, lunge:1.2',
        'wind:.18, active:.11, recover:.28, dmg:75, guard:24,\n      reach:3.65, lunge:.75':'wind:.27, active:.12, recover:.34, dmg:65, guard:21,\n      reach:3.05, lunge:.35',
        'reach:2.55, lunge:1.2':'reach:2.40, lunge:1.0',
        'reach:3.8, lunge:1.0':'reach:3.15, lunge:.45',
        'reach:3.9, lunge:.75':'reach:3.20, lunge:.40',
        'cd:9, wind:.30, active:1.0, recover:.49, dmg:57, guard:22, reach:4.7, lunge:.35':'cd:10, wind:.36, active:1.05, recover:.53, dmg:55, guard:20, reach:3.45, lunge:.2',
        'reach:3.9, lunge:.55':'reach:3.2, lunge:.2',
        'cd: 43, wind: 0.48, active: 1.58, recover: 0.82, dmg: 51, guard: 19, reach: 4.2':'cd: 43, wind: 0.48, active: 1.58, recover: 0.82, dmg: 51, guard: 19, reach: 3.55',
    }
    for old,new in changes.items():v2_rep(kits,old,new)
    v2_rep(kits,'Overhead ball orbit, a long-range release and a chain-assisted return.',
           'A spinning chained-ball release followed by a chain-assisted return.')
    v2_rep(kits,'Throw the axe and flail around opposite sides, then draw them together in five independently defendable impacts.',
           'Swing the axe and launch the chained ball along opposite paths, then draw them together in five independently defendable impacts.')
    # Each performed attack can gain ONE stack even if several timed hitboxes land.
    v2_rep(game,'attacker.earnRaigoMomentum(`${attacker.swingSerial}:${a.id}`);',
           'attacker.earnRaigoMomentum(`hit:${attacker.swingSerial}`);')
    # Build the weapon-specific hitboxes with the right source and range.
    v2_rep(game,'const isAxe=a.style!=="raigo_comet" && i%2===0;', '''const isAxe=a.style==="raigo_tempest" ? (i===0 || i===2) :
        a.style==="raigo_twinned" ? (i===1 || i===3) : false;''')
    v2_rep(game,'reach:isAxe && !last?2.65:a.reach, heavy:false,', '''reach:isAxe ? 2.45 : a.reach, heavy:false,''')
    # First Twin Judgment beat now opens with a ball strike at 3.55 rather than an axe at 2.65.
    # Prevent invisible hits beyond the flail's extension, while allowing its trailing arc.
    v2_rep(game,'''      if (f.kit === "axeflail" && (a.style==="raigo_ball" || a.style==="raigo_comet_pull") && dist<1.42) continue;''', '''      if (f.kit === "axeflail" && (a.style==="raigo_ball" || a.style==="raigo_comet_pull") && dist<1.20) continue;
      if (f.kit === "axeflail" && (a.style==="raigo_ball" || a.style==="raigo_comet_pull")) {
        // Hits cannot reach farther than the actual modeled flail can extend.
        // The tip's current orbit is allowed a modest hitbox sweep tolerance.
        const ballTip = f.model.raigoFlailTip;
        if (ballTip) {
          ballTip.updateWorldMatrix(true,false);
          const ballWorld = ballTip.getWorldPosition(new THREE.Vector3());
          const visualReach = Math.hypot(ballWorld.x-f.root.position.x,ballWorld.z-f.root.position.z)+0.55;
          if (dist-d.radius > Math.min(a.reach,visualReach)) continue;
        }
      }''')
    # A smooth pull using five short, scheduled displacements (no teleport/pop).
    v2_rep(game,'''          d.root.position.copy(dest);
          this.fxp("ring",d.chest(),"#efb870",.75,.16,.70);''','''          const start=d.root.position.clone(), round=this.round;
          for (let s=1;s<=5;s++) this.laterCombo(f,s*.03,()=>{
            if (this.round!==round || d.isDown() || f.isDown()) return;
            const t=s/5, ease=t*t*(3-2*t);
            d.root.position.lerpVectors(start,dest,ease);
          });
          this.fxp("ring",d.chest(),"#efb870",.75,.16,.70);''')
    # More forceful plant and shifting legs during the meaningful poses.
    v2_rep(kits, 'rg2_s:P([.17,-.59,-.06],[-.07,.38,0],[-1.43,-.12,-.27],[.31,0,.13],[-1.50,.55,.41],[.18,0,.28],[-.48,0,.18],[.48,0,-.16],-.17)',
           'rg2_s:K(P([.28,-.74,-.09],[-.07,.42,0],[-1.43,-.12,-.27],[.31,0,.13],[-1.50,.55,.41],[.18,0,.28],[-.72,-.13,.25],[.41,.16,-.19],-.24),.62,.39)')
    v2_rep(kits, 'rg4_s:P([.47,.40,0],[-.20,-.13,0],[-.89,.54,-.37],[.19,0,.29],[-1.08,-.42,.31],[.26,0,.1],[-.76,0,.15],[.61,0,-.17],-.26)',
           'rg4_s:K(P([.57,.55,0],[-.20,-.13,0],[-.89,.54,-.37],[.19,0,.29],[-1.08,-.42,.31],[.26,0,.1],[-.83,.16,.23],[.64,-.14,-.18],-.31),.76,.51)')
    v2_rep(kits, 'rgh_w:P([-.23,-.40,0],[.08,.26,0],[-2.62,.31,-.23],[.49,0,-.07],[-2.22,-.31,.3],[.44,0,.13],[-.57,0,.15],[.36,0,-.17],-.15)',
           'rgh_w:K(P([-.34,-.50,0],[.08,.26,0],[-2.62,.31,-.23],[.49,0,-.07],[-2.22,-.31,.3],[.44,0,.13],[-.78,0,.20],[.47,0,-.22],-.29),.82,.66)')
    v2_rep(kits, 'rgh_s:P([.55,.27,0],[-.24,-.08,0],[-.61,.31,-.41],[.2,0,.31],[-.83,-.18,.41],[.2,0,.18],[-.74,0,.17],[.63,0,-.16],-.27)',
           'rgh_s:K(P([.63,.38,0],[-.24,-.08,0],[-.61,.31,-.41],[.2,0,.31],[-.83,-.18,.41],[.2,0,.18],[-.91,0,.22],[.71,0,-.18],-.35),.95,.72)')
    # Ensure a windup key is present for the charge pose and an explicit contract for animation.
    v2_rep(model,'''  private raigoBallOrbit: THREE.Group | null = null;
  raigoFlailTip: THREE.Object3D | null = null;
  private raigoChainFrom: THREE.Object3D | null = null;
  private raigoLinks: THREE.Mesh[] = [];
  private raigoAngle = 0;
  private raigoRadius = .72;
  private raigoLastPose = "";
  private raigoSwingT = 0;
  raigoPose = "idle";
  raigoProgress = 0;
  raigoBeat = 0;''', '''  private raigoBallRoot: THREE.Group | null = null;
  raigoFlailTip: THREE.Object3D | null = null;
  private raigoChainFrom: THREE.Object3D | null = null;
  private raigoLinks: THREE.Group[] = [];
  private raigoAngle = 0;
  private raigoLastPose = "";
  private raigoSwingT = 0;
  private raigoBallPrev = new THREE.Vector3();
  private raigoAnchor = new THREE.Vector3();
  private raigoDesired = new THREE.Vector3();
  private raigoOld = new THREE.Vector3();
  private raigoDelta = new THREE.Vector3();
  private raigoPathP = new THREE.Vector3();
  private raigoPathQ = new THREE.Vector3();
  private raigoMid = new THREE.Vector3();
  private raigoUp = new THREE.Vector3(0,1,0);
  private raigoBallInitialized = false;
  raigoPose = "idle";
  raigoProgress = 0;
  raigoBeat = 0;''')
    start=T[model].index('  /** RAIGO_IRON_BASTION_V1: one full steel axe')
    end=T[model].index('  private buildGlaive() {',start)
    T[model]=T[model][:start]+RAIGO_V2_MODEL+T[model][end:]
    v2_rep(model, '    if (this.kit === "axeflail") this.updateRaigoWeapon(dt);',
           '    if (this.kit === "axeflail") this.updateRaigoWeapon(dt);')
    # Announce version without modifying other characters' state.
    T[model]='// '+V2_MARK+' — articulated chained flail, constrained motion and progress-driven attacks.\n'+T[model]

RAIGO_V2_MODEL = '''  /** RAIGO_IRON_BASTION_V2: The axe belongs to the right hand. The LEFT hand grips
   * a real visible chain handle, with the ball freely animated in fighter-local space.
   * Chain rings are distinct links. No vertex buffers or meshes are created per frame. */
  private buildRaigoAxeFlail() {
    const steel=this.tn("#b8c0c7"), edge=this.tn("#f0e8d9"), iron=this.tn("#30383e"),
      bronze=this.tn("#c09a61"), dark=this.tn("#454c51");
    const axe=pivot(this.hand_r,[0,0,0],[PI/2,0,0]);
    this.raigoAxe=axe;
    mesh(axe,cyl(.043,.046,1.36,10),dark,[0,.36,0]);
    mesh(axe,cyl(.058,.050,.37,10),iron,[0,.15,0]);
    for(const y of [-.18,.15,.50,.89]) mesh(axe,torus(.04,.055),bronze,[0,y,0],[PI/2,0,0]);
    const head=pivot(axe,[0,.93,0]);
    mesh(head,box(.24,.26,.13),iron,[.025,0,0]);
    const outline=new THREE.Shape();
    outline.moveTo(.03,.20);outline.lineTo(.19,.36);
    outline.bezierCurveTo(.46,.30,.61,.15,.67,.06);
    outline.bezierCurveTo(.50,-.04,.48,-.19,.50,-.34);
    outline.lineTo(.20,-.22);outline.lineTo(.03,-.17);outline.closePath();
    const blade=new THREE.ExtrudeGeometry(outline,{depth:.055,bevelEnabled:true,bevelSize:.019,
      bevelThickness:.015,bevelSegments:1,steps:1});
    mesh(head,blade,steel,[0,0,-.027]);
    for(let j=0;j<4;j++) mesh(head,box(.09,.018,.015),edge,[.39+j*.053,.255-j*.115,.05],
      [0,0,-.25-j*.20]);
    mesh(head,cyl(.13,.13,.10,8),bronze,[.04,0,0],[PI/2,0,0]);
    this.bladeBase=pivot(axe,[0,.75,0]);
    this.bladeTip=pivot(head,[.54,.04,0]);
    mesh(axe,sphere(.058,12),bronze,[0,-.29,0]);
    // Left fist physically closes around this compact handle. The chain starts HERE.
    const handle=pivot(this.hand_l,[0,-.05,0],[PI/2,0,0]);
    mesh(handle,cyl(.041,.044,.28,12),dark,[0,.025,0]);
    for(const y of [-.08,.08]) mesh(handle,torus(.045,.058),bronze,[0,y,0],[PI/2,0,0]);
    this.raigoChainFrom=pivot(handle,[0,.178,0]);
    mesh(handle,sphere(.054,12),bronze,[0,.172,0]);
    // The ball is NOT a child of either hand and cannot bend or stretch the character arm.
    const ball=pivot(this,[0,1.15,0]);
    this.raigoBallRoot=ball;
    this.raigoFlailTip=ball;
    mesh(ball,sphere(.205,22),iron);
    // Visible plated facets outside the iron (rather than an invisible buried sphere).
    for (let n=0;n<6;n++) {
      const theta=n*TAU/6;
      mesh(ball,box(.055,.18,.023),steel,[.188*Math.cos(theta),.04,.188*Math.sin(theta)],
        [0,-theta,0]);
    }
    // Fibonacci distribution covers both poles and avoids the old equatorial band.
    for(let n=0;n<22;n++) {
      const y=1-2*(n+.5)/22;
      const r=Math.sqrt(Math.max(0,1-y*y)),az=n*2.3999632297;
      const axis=new THREE.Vector3(Math.cos(az)*r,y,Math.sin(az)*r);
      const spike=mesh(ball,new THREE.ConeGeometry(.060,.19,7),steel,
        axis.clone().multiplyScalar(.225));
      spike.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),axis);
    }
    mesh(ball,sphere(.064,12),bronze,[0,.212,0]);
    // Alternating interlocked rings, not a skinny stretched cylinder.
    for(let i=0;i<32;i++) {
      const link=pivot(this);
      mesh(link,torus(.030,.055),i%2?steel:iron,[0,0,0],[0,i%2?PI/2:0,0]);
      this.raigoLinks.push(link);
    }
    this.castPoint=ball;
    this.shieldNode=axe;
  }

  /** Verlet-like inertial endpoint driven by timed attack arcs with a hard chain-length
   * constraint; produces real continuous orbits instead of oscillating Euler angles.
   * Deliberately cinematic, not a full rigid-body simulator: gameplay hit tests stay
   * in game.ts and pass through the native block/parry/clash rules. */
  private updateRaigoWeapon(dt:number) {
    const axe=this.raigoAxe,ball=this.raigoBallRoot,grip=this.raigoChainFrom;
    if(!axe || !ball || !grip) return;
    const step=Math.min(Math.max(dt,0),.045),pose=this.raigoPose;
    const show=pose==="raigo_show";
    const phase=((this.presentationT%9.6)+9.6)%9.6;
    if(pose!==this.raigoLastPose){this.raigoLastPose=pose;this.raigoSwingT=0;}
    else this.raigoSwingT+=step;
    // Updating only the grip's ancestor matrices avoids updating the whole model twice.
    grip.updateWorldMatrix(true,false);
    this.raigoAnchor.copy(grip.getWorldPosition(this.raigoAnchor));
    this.worldToLocal(this.raigoAnchor);
    const attacking=show||pose.endsWith("_s")||pose.startsWith("rgz")||pose.startsWith("rgc")||pose.startsWith("rgv");
    const p=THREE.MathUtils.clamp(this.raigoProgress,0,1);
    const wave=show?1:Math.sin(Math.PI*(.18+.76*p));
    let extension=attacking ? 1.55+1.17*Math.max(.2,wave) : pose.endsWith("_w")||pose==="charge"?1.25:.78;
    if(show) extension=phase<1.0?.75:phase<4.9?2.25:phase<7.2?2.92:1.03;
    if(pose==="rgh_s") extension+=.15*Math.sin(Math.min(1,this.raigoSwingT/.20)*Math.PI);
    // Phase continues across attacks; opposite rotation direction for the final reverse catch.
    const spinSpeed=show?(phase<5?10.2:phase<7.2?13.7:7.3):attacking?11.6:1.5;
    this.raigoAngle+=step*spinSpeed*(show&&phase>7.2?-1:1);
    const angle=this.raigoAngle + ((pose==="rgc_s"||pose==="rgv_s"||pose==="rgz_s")?this.raigoBeat*.17:0);
    const sideSwing=pose==="rg2_s"||pose==="rg4_s"||pose==="rgc_s";
    const overhead=pose==="rgz_s"||pose==="rgv_s"||pose==="rgz_w"||show;
    const rise=overhead?.56:sideSwing?.05:-.32;
    this.raigoDesired.copy(this.raigoAnchor).add(
      this.raigoDelta.set(Math.sin(angle)*extension,
        rise+(overhead?.22:.38)*Math.cos(angle*1.03),
        Math.cos(angle)*extension));
    if(!this.raigoBallInitialized) {
      ball.position.copy(this.raigoDesired);
      this.raigoBallPrev.copy(ball.position);
      this.raigoBallInitialized=true;
    }
    // Inertial follow-through: previous position carries momentum between combo strikes.
    this.raigoOld.copy(ball.position);
    this.raigoDelta.subVectors(ball.position,this.raigoBallPrev).multiplyScalar(.68);
    ball.position.add(this.raigoDelta);
    const stiffness=attacking?36:11;
    const alpha=1-Math.exp(-stiffness*step);
    ball.position.lerp(this.raigoDesired,alpha);
    ball.position.y-=2.8*step*step;
    this.raigoBallPrev.copy(this.raigoOld);
    // A controlled long chain: the ball never moves farther than its actual tether.
    this.raigoDelta.subVectors(ball.position,this.raigoAnchor);
    const length=this.raigoDelta.length();
    if(length>3.05) ball.position.copy(this.raigoAnchor).addScaledVector(this.raigoDelta,3.05/length);
    ball.rotation.x+=step*(attacking?8:1.2);
    ball.rotation.z+=step*(attacking?11:1.3);
    const axeAngles: Record<string,[number,number,number]>={
      idle:[PI/2,.10,-.15],block:[1.24,.35,.28],charge:[2.55,-.47,-.22],
      rg1_w:[2.10,-.50,-.26],rg1_s:[.65,.55,.29],
      rg2_w:[1.45,.22,-.20],rg2_s:[1.24,-.36,.26],
      rg3_w:[2.26,.48,-.18],rg3_s:[.67,-.58,.33],
      rg4_w:[2.40,-.27,-.24],rg4_s:[.65,.51,.31],
      rgh_w:[2.64,-.27,-.10],rgh_s:[.48,.29,.20],
      rgz_w:[1.80,-.33,-.14],rgz_s:[1.19,.28,.14],
      rgx_w:[1.34,-.22,-.10],rgx_s:[.91,.22,.23],
      rgc_w:[2.15,-.36,-.17],rgc_s:[.85,.42,.28],
      rgv_w:[2.57,-.35,-.13],rgv_s:[.70,.51,.29]};
    const a=axeAngles[pose]??axeAngles.idle;
    const target=this.raigoQuat.setFromEuler(this.raigoEuler.set(a[0],a[1],a[2],"YXZ"));
    if(show) target.multiply(this.raigoSpinQuat.setFromAxisAngle(this.raigoUp,
      phase<6.8?Math.sin(phase*7.5)*.68:0));
    axe.quaternion.slerp(target,1-Math.exp(-(attacking?20:11)*step));
    // A shallow catenary with real link nodes follows the exact grip and ball endpoints.
    this.raigoMid.copy(this.raigoAnchor).lerp(ball.position,.5);
    this.raigoMid.y-=attacking?.10:.32;
    const n=this.raigoLinks.length;
    for(let i=0;i<n;i++){
      const t=i/n, u=Math.min(1,t+1/n);
      this.raigoPathP.copy(this.raigoAnchor).multiplyScalar((1-t)*(1-t))
        .addScaledVector(this.raigoMid,2*t*(1-t)).addScaledVector(ball.position,t*t);
      this.raigoPathQ.copy(this.raigoAnchor).multiplyScalar((1-u)*(1-u))
        .addScaledVector(this.raigoMid,2*u*(1-u)).addScaledVector(ball.position,u*u);
      const node=this.raigoLinks[i];
      node.position.copy(this.raigoPathP).lerp(this.raigoPathQ,.5);
      this.raigoDelta.subVectors(this.raigoPathQ,this.raigoPathP);
      // Rings alternate their facing plane, while retaining a constant link thickness.
      node.quaternion.setFromUnitVectors(this.raigoUp,this.raigoDelta.normalize());
    }
  }

'''

# Instead of allocating per-frame axes/quaternions for the axe, reuse fields.
RAIGO_V2_MODEL = RAIGO_V2_MODEL.replace('    const target=this.raigoQuat.setFromEuler(this.raigoEuler.set(a[0],a[1],a[2],"YXZ"));',
    '    const target=this.raigoQuat.setFromEuler(this.raigoEuler.set(a[0],a[1],a[2],"YXZ"));')
_orig_v2_upgrade = v2_upgrade

def v2_upgrade():
    # Extra fields are added before replacing the V1 method body.
    f='src/game/model.ts'
    v2_rep(f,'  private raigoBallPrev = new THREE.Vector3();', '''  private raigoBallPrev = new THREE.Vector3();
  private raigoQuat = new THREE.Quaternion();
  private raigoSpinQuat = new THREE.Quaternion();
  private raigoEuler = new THREE.Euler();''') if '  private raigoBallPrev = new THREE.Vector3();' in T.get(f,'') else None
    _orig_v2_upgrade()
    # Above V1 content had no prev field yet; add in newly written output instead.
    if '  private raigoQuat = new THREE.Quaternion();' not in T[f]:
        v2_rep(f,'  private raigoBallPrev = new THREE.Vector3();', '''  private raigoBallPrev = new THREE.Vector3();
  private raigoQuat = new THREE.Quaternion();
  private raigoSpinQuat = new THREE.Quaternion();
  private raigoEuler = new THREE.Euler();''')



# RAIGO V3: ALL patches are applied to in-memory sources before any source or asset is changed.
V3_MARK = 'RAIGO_IRON_BASTION_V3'

def v3_rep(path: str, old: str, new: str, count: int = 1):
    got = T[path].count(old)
    if got != count:
        raise RuntimeError(f'{path}: V3 expected {count} occurrence(s) of {old[:85]!r}; found {got}. No files written.')
    T[path] = T[path].replace(old, new, count)

def v3_upgrade():
    kits='src/game/kits.ts'; fighter='src/game/fighter.ts'
    game='src/game/game.ts'; model='src/game/model.ts'
    # Real utility/helper checks: these exist in the uploaded 2026-11-08 snapshot.
    for path,guard in ((kits,'const K = (p: Pose,'),(model,'const TAU = PI * 2;'),
                       (game,'  private melee(f: Fighter, a: Attack): boolean {')):
        if guard not in T[path]:raise RuntimeError(f'{path}: missing prerequisite {guard!r}; no files written')
    # The original sequence used ball/axe/ball/axe/ball hit types, but its animations did not.
    v3_rep(fighter,'["rgv_s","rg2_s","rg3_s","rg4_s","rgh_s"]',
           '["rg2_s","rg1_s","rg4_s","rg3_s","rgv_final_s"]')
    # Give its last flail blow the correct left-arm dominant full-body drive.
    v3_rep(kits,'''  rgv_s:P([.44,.51,0],[-.18,-.18,0],[-1.01,.52,-.35],[.22,0,.31],[-1.13,-.42,.46],[.23,0,.19],[-.71,0,.15],[.54,0,-.16],-.24),''','''  rgv_s:K(P([.44,.51,0],[-.18,-.18,0],[-1.01,.52,-.35],[.22,0,.31],[-1.13,-.42,.46],[.23,0,.19],[-.71,.10,.20],[.54,-.12,-.16],-.28),.58,.49),
  rgv_final_s:K(P([.62,-.28,0],[-.19,.16,0],[-.64,.22,-.38],[.24,0,.18],[-.76,.62,.40],[.17,0,.26],[-.91,.13,.25],[.74,-.15,-.20],-.34),.91,.73),''')
    # Lower body: first/third hits, the Z release and C whirl use actual planted steps.
    legs={
      'idle:P([.15,-.29,0],[-.07,.20,0],[-.69,.19,-.27],[.37,.02,-.10],[-.92,-.26,.32],[.33,0,.12],[-.27,0,.16],[.24,0,-.16],-.13)':
      'idle:K(P([.15,-.29,0],[-.07,.20,0],[-.69,.19,-.27],[.37,.02,-.10],[-.92,-.26,.32],[.33,0,.12],[-.38,-.08,.19],[.30,.09,-.19],-.18),.27,.32)',
      'rg1_w:P([.17,-.66,.04],[0,.38,0],[-1.66,-.50,-.42],[.58,0,-.20],[-1.06,-.29,.41],[.48,0,.13],[-.48,0,.14],[.41,0,-.13],-.18)':
      'rg1_w:K(P([.20,-.72,.05],[0,.38,0],[-1.66,-.50,-.42],[.58,0,-.20],[-1.06,-.29,.41],[.48,0,.13],[-.63,-.09,.22],[.48,.12,-.15],-.23),.64,.36)',
      'rg1_s:P([.25,.50,-.06],[-.11,-.25,0],[-.91,.59,-.38],[.17,0,.18],[-1.37,.22,.37],[.31,0,.1],[-.58,0,.18],[.49,0,-.15],-.20)':
      'rg1_s:K(P([.36,.65,-.07],[-.11,-.25,0],[-.91,.59,-.38],[.17,0,.18],[-1.37,.22,.37],[.31,0,.1],[-.73,.09,.23],[.61,-.11,-.20],-.27),.77,.55)',
      'rg3_w:P([.25,.55,.02],[-.05,-.25,0],[-1.90,.49,-.38],[.58,0,-.04],[-1.25,.31,.33],[.24,0,.1],[-.51,0,.2],[.39,0,-.17],-.17)':
      'rg3_w:K(P([.24,.67,.03],[-.05,-.25,0],[-1.90,.49,-.38],[.58,0,-.04],[-1.25,.31,.33],[.24,0,.1],[-.64,.13,.23],[.48,-.10,-.22],-.23),.52,.61)',
      'rg3_s:P([.32,-.49,-.04],[-.07,.27,0],[-.60,-.51,-.42],[.20,0,.28],[-1.12,-.25,.39],[.28,0,.17],[-.59,0,.16],[.56,0,-.16],-.23)':
      'rg3_s:K(P([.39,-.61,-.06],[-.07,.27,0],[-.60,-.51,-.42],[.20,0,.28],[-1.12,-.25,.39],[.28,0,.17],[-.78,-.10,.24],[.62,.13,-.19],-.29),.74,.59)',
      'rgz_s:P([.13,.31,0],[-.13,-.26,0],[-1.40,.36,-.31],[.22,0,.24],[-1.74,.50,.34],[.38,0,.14],[-.51,0,.15],[.48,0,-.15],-.17)':
      'rgz_s:K(P([.20,.44,0],[-.13,-.26,0],[-1.40,.36,-.31],[.22,0,.24],[-1.74,.50,.34],[.38,0,.14],[-.76,-.09,.23],[.58,.14,-.19],-.27),.67,.45)',
      'rgc_s:P([.22,.67,0],[-.13,-.28,0],[-1.37,.68,-.38],[.22,0,.29],[-1.61,.49,.42],[.19,0,.24],[-.60,0,.16],[.54,0,-.15],-.22)':
      'rgc_s:K(P([.35,.76,.06],[-.13,-.28,0],[-1.37,.68,-.38],[.22,0,.29],[-1.61,.49,.42],[.19,0,.24],[-.77,.17,.25],[.60,-.18,-.19],-.29),.60,.77)',
    }
    for old,new in legs.items():v3_rep(kits,old,new)
    # Let the animation reach the outer arc before first single-hit collision is resolved.
    v3_rep(game,'      if (a.type === "melee") { this.melee(f,a); return; }','''      if (a.type === "melee") {
        const serial=f.swingSerial, round=this.round;
        const delay=Math.min(.07,Math.max(.025,a.active*.50));
        this.laterCombo(f,delay,()=>{
          if(this.round!==round || f.isDown() || f.swingSerial!==serial ||
             f.state!==S.ATTACK || f.atk?.id!==a.id) return;
          this.melee(f,a);
        });
        return;
      }''')
    v3_rep(game,'this.laterCombo(f,i*step,()=>{','this.laterCombo(f,i*step+Math.min(.06,step*.32),()=>{')
    # Twin Judgment's last hit is a FLAIL execution, not an axe. Preserve its
    # Momentum-consumption bonus while using real ball reach/direction checks.
    v3_rep(game,'a.style==="raigo_twinned" && last?"raigo_execute":',
           'a.style==="raigo_twinned" && last?"raigo_ball_execute":')
    v3_rep(game,'(a.style==="raigo_execute" || a.id==="heavy")',
           '(a.style==="raigo_execute" || a.style==="raigo_ball_execute" || a.id==="heavy")')
    v3_rep(game,'(a.style==="raigo_ball" || a.style==="raigo_comet_pull")',
           '(a.style==="raigo_ball" || a.style==="raigo_comet_pull" || a.style==="raigo_ball_execute")',2)
    # Predictable strike envelope at very early contact: never more than authored reach,
    # with a modeled facing/ball-direction check to avoid hitting from behind.
    v3_rep(game,'''          const visualReach = Math.hypot(ballWorld.x-f.root.position.x,ballWorld.z-f.root.position.z)+0.55;
          if (dist-d.radius > Math.min(a.reach,visualReach)) continue;''','''          const bx=ballWorld.x-f.root.position.x, bz=ballWorld.z-f.root.position.z;
          const visible=Math.hypot(bx,bz), visualReach=visible+.43;
          // Early active-frame contacts should not be shortened by the rendered orbit lag.
          const allowed=Math.min(a.reach,Math.max(visualReach,a.reach*.85));
          if(dist-d.radius+.25>allowed) continue;
          // The ball cannot hit a target on the opposite side of its sweeping arc.
          // A wider angular tolerance allows an actual moving ball's swept volume.
          if(visible>.35 && dist>1.9 && (bx*dir.x+bz*dir.z)/visible<-.12) continue;''')
    # Time-based inertia, correct orientation/extension at each timed hit, heavier idle.
    v3_rep(model,'  private raigoBallInitialized = false;','''  private raigoBallInitialized = false;
  // Keep the previous ball positions in world space, so fighter movement doesn't carry
  // the heavy ball rigidly with the torso. These are reused, not allocated per frame.
  private raigoWorldTip = new THREE.Vector3();
  private raigoWorldPrevTip = new THREE.Vector3();''')
    v3_rep(model,'''    const attacking=show||pose.endsWith("_s")||pose.startsWith("rgz")||pose.startsWith("rgc")||pose.startsWith("rgv");''','''    const attacking=show||pose.endsWith("_s")||pose.startsWith("rgz_s")||pose.startsWith("rgc_s")||pose.startsWith("rgv_s");''')
    v3_rep(model,'''    const wave=show?1:Math.sin(Math.PI*(.18+.76*p));''','''    const pulseCount=pose==="rgz_s"?3:pose==="rgc_s"||pose==="rgv_s"||pose==="rgv_final_s"?5:1;
    const beatP=pulseCount>1?(p*pulseCount)%1:p;
    const wave=show?1:Math.sin(Math.PI*(.18+.76*beatP));''')
    v3_rep(model,'    const spinSpeed=show?(phase<5?10.2:phase<7.2?13.7:7.3):attacking?11.6:1.5;',
           '    const spinSpeed=show?(phase<5?10.2:phase<7.2?13.7:7.3):attacking?11.6:pose==="idle"?.12:1.1;')
    v3_rep(model,'''    this.raigoDesired.copy(this.raigoAnchor).add(
      this.raigoDelta.set(Math.sin(angle)*extension,
        rise+(overhead?.22:.38)*Math.cos(angle*1.03),
        Math.cos(angle)*extension));''','''    // Each impact sweeps the ball toward the front instead of leaving a hitbox
    // disconnected from an arbitrary continuously rotating idle orbit.
    const strikePose=pose.endsWith("_s") || pose==="rgh_s";
    const impulse=strikePose && !show?Math.pow(Math.sin(Math.PI*beatP),2)*.92:0;
    if(pose==="idle" || pose==="block") {
      this.raigoDesired.copy(this.raigoAnchor).add(this.raigoDelta.set(
        .13+Math.sin(this.t*1.3)*.035,-.66+Math.sin(this.t*1.7)*.024,
        .19+Math.cos(this.t*1.3)*.032));
    } else {
      this.raigoDesired.copy(this.raigoAnchor).add(this.raigoDelta.set(
        Math.sin(angle)*extension*(1-impulse),
        rise+(overhead?.22:.38)*Math.cos(angle*1.03),
        extension*(Math.cos(angle)*(1-impulse)+impulse)));
    }''')
    v3_rep(model,'''      this.raigoBallPrev.copy(ball.position);
      this.raigoBallInitialized=true;
    }
    // Inertial follow-through:''','''      this.raigoBallPrev.copy(ball.position);
      ball.updateWorldMatrix(true,false);
      ball.getWorldPosition(this.raigoWorldTip);
      this.raigoWorldPrevTip.copy(this.raigoWorldTip);
      this.raigoBallInitialized=true;
    } else {
      // Reproject previous world positions under the CURRENT root transform.
      // Dashes, knockback and root yaw now cause natural weapon lag.
      // worldToLocal mutates its argument: use scratch vectors so stored world history
      // stays world-space across the next frame as well.
      ball.position.copy(this.worldToLocal(this.raigoPathP.copy(this.raigoWorldTip)));
      this.raigoBallPrev.copy(this.worldToLocal(this.raigoPathQ.copy(this.raigoWorldPrevTip)));
    }
    // Inertial follow-through:''')
    v3_rep(model,'    this.raigoDelta.subVectors(ball.position,this.raigoBallPrev).multiplyScalar(.68);',
           '    this.raigoDelta.subVectors(ball.position,this.raigoBallPrev).multiplyScalar(Math.pow(.68,step*60));')
    v3_rep(model,'    ball.position.y-=2.8*step*step;','    // No micro-gravity nudge: the idle hang is handled by the desired trajectory.')
    v3_rep(model,'''    if(length>3.05) ball.position.copy(this.raigoAnchor).addScaledVector(this.raigoDelta,3.05/length);
    ball.rotation.x+=step*(attacking?8:1.2);''','''    if(length>3.05) ball.position.copy(this.raigoAnchor).addScaledVector(this.raigoDelta,3.05/length);
    this.raigoWorldPrevTip.copy(this.raigoWorldTip);
    ball.updateWorldMatrix(true,false);
    ball.getWorldPosition(this.raigoWorldTip);
    ball.rotation.x+=step*(attacking?8:pose==="idle"?.08:1.2);''')
    v3_rep(model,'    ball.rotation.z+=step*(attacking?11:1.3);','    ball.rotation.z+=step*(attacking?11:pose==="idle"?.07:1.3);')
    v3_rep(model,'      rgv_w:[2.57,-.35,-.13],rgv_s:[.70,.51,.29]};',
           '      rgv_w:[2.57,-.35,-.13],rgv_s:[.70,.51,.29],rgv_final_s:[.55,.24,.26]};')
    # V3 stamping allows repeat-invocation rejection and reliable future upgrades.
    T[model]='// '+V3_MARK+' — hit-aligned swings, world lag, stable idle, impact poses.\n'+T[model]

def main() -> int:
    import base64, os, tempfile
    args=[x for x in sys.argv[1:] if x != '--dry-run']
    dry='--dry-run' in sys.argv[1:]
    root=pathlib.Path(args[0] if args else '.').expanduser().resolve()
    files=['src/game/roster.ts','src/game/kits.ts','src/game/model.ts',
        'src/game/fighter.ts','src/game/game.ts','src/game/ai.ts',
        'src/game/preview.ts','src/game/presentation.ts']
    sql_rel=pathlib.Path('supabase/migrations/20261108224500_add_raigo_iron_bastion.sql')
    print('RAIGO — IRON BASTION V3 | target:',root)
    try:
        for rel in files:
            path=root/rel
            if not path.is_file():raise RuntimeError(f'Missing {rel}; run in the web folder')
            T[rel]=path.read_text(encoding='utf-8-sig')
        existing_v3=V3_MARK in T['src/game/model.ts']
        existing_v2=V2_MARK in T['src/game/model.ts']
        existing_v1=MARK in T['src/game/model.ts'] or 'id: "raigo"' in T['src/game/roster.ts']
        if existing_v3:
            print('Raigo V3 already installed; no changes made');return 1
        if existing_v1 and not (MARK in T['src/game/model.ts']):
            raise RuntimeError('Unrecognized Raigo version; cannot safely upgrade')
        if not existing_v1:
            if not (root/'public/models/garrick.vrm').is_file():raise RuntimeError('Missing Garrick VRM')
            add_roster();add_kits();add_ai();add_fighter();add_game();add_model();add_presentation()
        if not existing_v2:v2_upgrade()
        v3_upgrade()
        if dry:
            print('PASS: all V3 anchors found, preflight complete;',
                'V2 upgrade' if existing_v2 else 'V1 upgrade' if existing_v1 else 'fresh install',
                '; no files changed')
            return 0
        backup=root/'.raigo-backups'/('v3-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        new_files={}
        # Assets and optional migration only on a fresh install, never overwrite personal art.
        if not existing_v1:
            if not (root/sql_rel).exists():new_files[str(sql_rel)]=sql_file().encode('utf-8')
            for key,data in ICON_WEBP.items():
                rel=pathlib.Path('public/icons/chars/raigo.webp' if key=='char' else f'public/icons/skills/axeflail-{key}.webp')
                if not (root/rel).exists():new_files[str(rel)]=base64.b64decode(''.join(data))
        outputs={rel:T[rel].encode('utf-8') for rel in files}
        outputs.update(new_files)
        for rel in files:
            dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/rel,dest)
        staged={};changed=[]
        try:
            for rel,data in outputs.items():
                dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=dest.parent,prefix='.raigo-v3-',delete=False) as tmp:
                    tmp.write(data);staged[rel]=pathlib.Path(tmp.name)
            for rel,tmp in staged.items():
                dest=root/rel
                if rel in new_files and dest.exists():raise RuntimeError('Unexpected asset collision: '+rel)
                os.replace(tmp,dest);changed.append(rel)
            print('PASS: wrote',len(files),'source files;',len(new_files),'new optional assets')
            print('Backups:',backup)
            print('NEXT: npx tsc --noEmit -p . && npm run dev')
            print('NOT IMPLEMENTED: chain projectile deflection or fully detached axe throw; live rendering unverified.')
            return 0
        except Exception:
            for rel in reversed(changed):
                dest=root/rel
                if rel in files:shutil.copy2(backup/rel,dest)
                else:dest.unlink(missing_ok=True)
            raise
        finally:
            for tmp in staged.values():tmp.unlink(missing_ok=True)
    except Exception as exc:
        print('ERROR:',str(exc),file=sys.stderr);return 1

if __name__=='__main__':
    raise SystemExit(main())
