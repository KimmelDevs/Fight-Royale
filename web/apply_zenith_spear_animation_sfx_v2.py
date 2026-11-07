#!/usr/bin/env python3
"""Zenith Iron Sovereign: slim metal spear, dedicated poses, compact skills, matched sounds.
Run from Fight Royale/web after install_zenith_iron_sovereign_fixed.py.
Requires SOUND_LIST.txt's selected MP3 files copied into public/sfx/ (exact subfolders).
Preflight checks every edit before any write; timestamped backups; idempotent.
"""
from pathlib import Path
from datetime import datetime
import sys, shutil

R = Path.cwd()
F = 'src/game/fighter.ts'
K = 'src/game/kits.ts'
G = 'src/game/game.ts'
M = 'src/game/model.ts'
V = 'src/game/vrm.ts'
FILES = [F,K,G,M,V]
TAG = 'ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108'
try:
    old = {p:(R/p).read_text(encoding='utf-8') for p in FILES}
except OSError as exc:
    sys.exit(f'ERROR: Run in the web project directory. {exc}. No files changed.')
if TAG in old[K]:
    print('Zenith spear animation & audio V2 already installed; nothing changed.')
    sys.exit(0)
if 'ZENITH_IRON_SOVEREIGN_V1_20261108' not in old[K] or 'zenithMagneticSpear' not in old[M]:
    sys.exit('PREFLIGHT ERROR: install the fixed Zenith character first. Nothing changed.')
new = old.copy()
def one(path,anchor,repl):
    n = new[path].count(anchor)
    if n != 1:
        raise ValueError(f'{path}: preflight anchor expected once, found {n}: {anchor[:85]!r}')
    new[path] = new[path].replace(anchor,repl,1)
def section(path,left,right,repl):
    s=new[path]; i=s.find(left)
    if i<0 or s.count(left)!=1: raise ValueError(f'{path}: start section missing/duplicate: {left[:75]!r}')
    j=s.find(right,i+len(left))
    if j<0: raise ValueError(f'{path}: end section missing: {right[:75]!r}')
    new[path]=s[:i]+repl+s[j:]
try:
    # Zenith-only kit animation and visible projectile radii. Damage and real melee reach unchanged.
    one(K,'''      [43, 0.14, "gl1_w", "gl1_s"], [46, 0.14, "gl2_w", "gl2_s"],
      [49, 0.15, "gl3_w", "gl3_s"], [51, 0.16, "gl4_w", "gl4_s"],
      [68, 0.24, "gl5_w", "gl5_s"] ];''', '''      [43, 0.14, "zn1_w", "zn1_s"], [46, 0.14, "zn2_w", "zn2_s"],
      [49, 0.15, "zn3_w", "zn3_s"], [51, 0.16, "zn4_w", "zn4_s"],
      [68, 0.24, "zn5_w", "zn5_s"] ];''')
    one(K, 'speed: 23, size: 1.5, pierce: true,', 'speed: 23, size: 0.88, pierce: true,')
    one(K, 'style: "zenith_heavy", pose_w: "glh_w", pose_s: "glh_s"', 'style: "zenith_heavy", pose_w: "znh_w", pose_s: "znh_s"')
    one(K, 'speed: 24, size: 1.8, pierce: true,', 'speed: 24, size: 1.06, pierce: true,')
    one(K, 'style: "zenith_rail", pose_w: "glz_w", pose_s: "glz_s"', 'style: "zenith_rail", pose_w: "znz_w", pose_s: "znz_s"')
    one(K, 'style: "zenith_barrage", pose_w: "glx_w", pose_s: "glz_s"', 'style: "zenith_barrage", pose_w: "znx_w", pose_s: "znx_s"')
    one(K, 'radius: 4.5, pose_w: "glc_w", pose_s: "glc_s"', 'radius: 4.5, pose_w: "znc_w", pose_s: "znc_s"')
    one(K, 'style: "zenith_arsenal", pose_w: "glc_w", pose_s: "glc_s"', 'style: "zenith_arsenal", pose_w: "znv_w", pose_s: "znv_s"')
    one(K, 'next: "", pose_w: "gl2_w", pose_s: "gl2_s" };', 'next: "", pose_w: "zn2_w", pose_s: "zn2_s" };')

    # A fully distinct Metal-only animation pose table: no overrides of Zarek's GLAIVE.
    one(K,'const CHAINBLADE: Record<string, Pose> = {', '''// ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — tight thrusts, alternate rear-blade strike,
// two-hand rail throw, one-hand magnetic control and elevated arsenal summon.
const ZENITH: Record<string, Pose> = {
  ...GLAIVE,
  idle: P([0.025,-0.16,0], [0.0,0.12,0], [-0.77,0.21,-0.20], [0.17,0,0.03], [-1.04,-0.28,0.14], [0.12,0,0], [-0.25,0,0.08], [0.31,0,-0.08], -0.055),
  block: P([0.09,-0.08,0], [0,0.08,0], [-1.12,0.19,-0.22], [0.16,0,0.04], [-1.17,-0.24,0.21], [0.12,0,0], [-0.39,0,0.08], [0.41,0,-0.08], -0.08),
  zn1_w: P([0.09,-0.28,0], [0,0.2,0], [-1.12,-0.36,-0.16], [0.31,0,0], [-1.19,-0.1,0.24], [0.26,0,0], [-0.33,0,0.07], [0.28,0,-0.06], -0.085),
  zn1_s: P([0.17,0.12,0], [0,-0.08,0], [-1.54,0.06,-0.11], [0.01,0,0], [-1.61,0.13,0.16], [0.05,0,0], [-0.48,0,0.08], [0.43,0,-0.07], -0.12),
  zn2_w: P([0.13,0.31,0.03], [0,-0.23,0], [-1.10,0.44,0.06], [0.32,0,0], [-1.23,0.15,0.14], [0.18,0,0], [-0.22,0,0.10], [0.34,0,-0.07], -0.095),
  zn2_s: P([0.20,-0.20,0], [0,0.14,0], [-1.60,-0.26,-0.17], [0.07,0,0], [-1.58,-0.14,0.16], [0.10,0,0], [-0.45,0,0.09], [0.36,0,-0.09], -0.12),
  zn3_w: P([0.11,-0.25,-0.03], [0,0.22,0], [-1.40,-0.24,0.14], [0.27,0,0], [-1.23,-0.43,0.12], [0.28,0,0], [-0.32,0,0.12], [0.36,0,-0.07], -0.10),
  zn3_s: P([0.19,0.27,0], [0,-0.20,0], [-1.77,0.28,0.03], [0.08,0,0], [-1.62,0.19,0.11], [0.06,0,0], [-0.53,0,0.10], [0.42,0,-0.07], -0.125),
  // Reverse-end thrust: turn wrists over, no giant overhead arc.
  zn4_w: P([0.08,0.36,0], [0,-0.27,0], [-1.13,0.18,0.11], [0.27,0,0.26], [-1.30,0.24,0.22], [0.22,0,-0.16], [-0.28,0,0.10], [0.30,0,-0.07], -0.09),
  zn4_s: P([0.17,-0.31,0.03], [0,0.24,0], [-1.69,-0.21,0.05], [0.06,0,-0.35], [-1.69,-0.27,0.13], [0.10,0,0.22], [-0.54,0,0.11], [0.45,0,-0.08], -0.13),
  zn5_w: P([0.04,-0.33,0], [0,0.28,0], [-1.28,-0.28,-0.17], [0.38,0,0], [-1.42,-0.22,0.13], [0.26,0,0], [-0.49,0,0.11], [0.30,0,-0.08], -0.12),
  zn5_s: P([0.28,0.26,0], [-0.08,-0.17,0], [-1.81,0.25,-0.08], [0.03,0,0], [-1.86,0.21,0.16], [0.03,0,0], [-0.72,0,0.13], [0.51,0,-0.09], -0.17),
  znh_w: P([-0.08,-0.42,0], [0.04,0.32,0], [-1.46,-0.4,-0.12], [0.54,0,0], [-1.57,-0.25,0.10], [0.4,0,0], [-0.48,0,0.12], [0.42,0,-0.08], -0.13),
  znh_s: P([0.21,0.24,0], [-0.07,-0.16,0], [-1.95,0.20,-0.09], [0.1,0,0], [-1.93,0.2,0.10], [0.08,0,0], [-0.67,0,0.12], [0.48,0,-0.09], -0.16),
  znz_w: P([-0.07,-0.44,0], [0,0.30,0], [-1.27,-0.56,-0.10], [0.45,0,0], [-1.47,-0.20,0.18], [0.33,0,0], [-0.50,0,0.09], [0.41,0,-0.09], -0.12),
  znz_s: P([0.22,0.32,0], [0,-0.26,0], [-2.0,0.22,-0.14], [0.08,0,0], [-1.83,0.30,0.15], [0.10,0,0], [-0.66,0,0.10], [0.47,0,-0.10], -0.17),
  znx_w: P([0.09,-0.2,0], [0,0.18,0], [-1.10,-0.32,-0.18], [0.34,0,0], [-1.26,-0.18,0.21], [0.23,0,0], [-0.42,0,0.09], [0.39,0,-0.08], -0.10),
  znx_s: P([0.17,0.12,0], [0,-0.08,0], [-1.66,0.15,-0.16], [0.08,0,0], [-1.70,0.14,0.17], [0.11,0,0], [-0.55,0,0.10], [0.42,0,-0.09], -0.12),
  znc_w: P([0.05,-0.14,0], [0,0.10,0], [-0.58,-0.37,-0.54], [0.22,0,0.11], [-1.06,-0.18,0.26], [0.25,0,0], [-0.31,0,0.07], [0.32,0,-0.08], -0.055),
  znc_s: P([0.15,0.17,0], [0,-0.13,0], [-0.72,0.23,-0.72], [0.12,0,0.12], [-1.08,0.13,0.18], [0.18,0,0], [-0.42,0,0.10], [0.38,0,-0.09], -0.08),
  znv_w: P([-0.1,-0.14,0], [0,0.10,0], [-2.20,-0.14,-0.48], [0.22,0,0], [-1.45,-0.28,0.28], [0.21,0,0], [-0.48,0,0.12], [0.45,0,-0.08], -0.11),
  znv_s: P([0.17,0.2,0], [0,-0.14,0], [-2.43,0.15,-0.38], [0.12,0,0], [-0.93,0.18,0.28], [0.16,0,0], [-0.54,0,0.09], [0.49,0,-0.09], -0.10),
};

const CHAINBLADE: Record<string, Pose> = {''')
    one(K,'...(kit === "assassin" ? NYX_SHADOW_V1 : {}) };', '...(kit === "assassin" ? NYX_SHADOW_V1 : {}), ...(kit === "glaive" && element === "metal" ? ZENITH : {}) };')

    # No giant spinning Zarek choreography for Zenith — discrete spear thrusts.
    one(F,'        // ZAREK_CYCLONE_V3: true successive poses for serpent, slide reversal and ultimate.', '''        // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — dedicated attack pose timing.
        if (this.kit === "glaive" && this.look.element === "metal" && a) {
          if (a.style === "zenith_barrage") {
            const elapsed = this.stateT - a.wind;
            p = elapsed < 0 ? "znx_w" : ["zn1_s", "zn2_s", "zn3_s", "zn4_s", "zn5_s", "znx_s"]
              [Math.min(5, Math.floor(elapsed / 0.105))];
            sp = elapsed < 0 ? 25 : 67;
          } else if (this.atkPhase === 0) { p = a.pose_w; sp = 25; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = 74; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.68) { p = a.pose_s; sp = 25; }
          else { p = "idle"; sp = 20; }
          break;
        }
        // ZAREK_CYCLONE_V3: true successive poses for serpent, slide reversal and ultimate.''')

    # Metal-specific actual sword mesh, leave Zarek's glaive unchanged.
    one(M,'    // Metal uses the same hand rig, new material palette and a longer leaner spear.\n    const zenithMetal = this.look.element === "metal";', '''    if (this.look.element === "metal") { this.buildZenithSpear(); return; }
    // Zarek's glaive remains unchanged.
    const zenithMetal = this.look.element === "metal";''')
    # After the early return, this is Zarek's branch only; avoid TS no-overlap narrowing.
    one(M, '    const zenithMetal = this.look.element === "metal";', '    const zenithMetal = false; // Metal is handled above in buildZenithSpear().')
    one(M,'  /** The game hides the held metal spear when its projectile is flying. */', '''  // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — proper compact double-point spear,
  // rather than scaling the wide thunder glaive. One continuous, narrow steel profile.
  private buildZenithSpear() {
    const spear = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    spear.name = "zenithMagneticSpear";
    spear.scale.setScalar(0.94);
    this.glaivePivot = spear;
    const steel = M.toon("#d9e1eb", { rim: 0.75, shade: METAL_SHADE });
    const navy = this.tn("#25364f");
    const silver = this.tn("#a9b4c7");
    const gold = this.tn("#caa86e");
    const core = this.tn("#7ccbe6");
    mesh(spear, cyl(0.015, 0.015, 1.72, 10), navy);
    mesh(spear, cyl(0.021, 0.021, 0.50, 10), this.tn("#1b2638"));
    for (const s of [-1, 1]) {
      // Long tapered diamond tips, but only a few centimeters across.
      const outline = new THREE.Shape();
      outline.moveTo(-0.018, s * 0.79);
      outline.lineTo(-0.052, s * 0.90);
      outline.lineTo(-0.046, s * 1.03);
      outline.lineTo(-0.026, s * 1.12);
      outline.lineTo(0, s * 1.25);
      outline.lineTo(0.026, s * 1.12);
      outline.lineTo(0.046, s * 1.03);
      outline.lineTo(0.052, s * 0.90);
      outline.lineTo(0.018, s * 0.79);
      outline.closePath();
      const geo = new THREE.ExtrudeGeometry(outline,
        { depth: 0.012, bevelEnabled: true, bevelThickness: 0.003, bevelSize: 0.003, bevelSegments: 1 });
      geo.translate(0, 0, -0.006);
      mesh(spear, geo, steel);
      mesh(spear, cyl(0.025, 0.025, 0.065, 10), silver, [0, s * 0.81, 0]);
      mesh(spear, cyl(0.023, 0.023, 0.025, 10), gold, [0, s * 0.88, 0]);
      mesh(spear, box(0.009, 0.16, 0.014), core, [0, s * 1.025, 0.008]);
      mesh(spear, sphere(0.022, 10), this.gem(), [0, s * 0.86, 0.008]);
    }
    for (const y of [-0.22, -0.12, 0.12, 0.22])
      mesh(spear, torus(0.021, 0.028), gold, [0, y, 0], [PI / 2, 0, 0], [1, 0.36, 1]);
    this.gripL = pivot(spear, [0, -0.32, 0]);
    this.bladeBase = pivot(spear, [0, 0.81, 0]);
    this.bladeTip = pivot(spear, [0, 1.25, 0]);
    this.shieldNode = spear;
    this.castPoint = this.bladeTip;
  }

  /** The game hides the held metal spear when its projectile is flying. */''')
    one(M,'    if (this.glaivePivot) {\n      const angles: Record<string, [number, number, number]> = {', '''    if (this.glaivePivot) {
      // Attack pose angles are independent of the VRM clip. Narrow wrist turns
      // produce a direct, forward thrust instead of Zarek's wide blade arcs.
      const angles: Record<string, [number, number, number]> = {
        zn1_w: [1.52,-0.17,0.03], zn1_s: [1.16,0.11,-0.06],
        zn2_w: [1.66,0.23,0.08], zn2_s: [1.20,-0.15,-0.07],
        zn3_w: [1.57,-0.13,0.08], zn3_s: [1.08,0.13,-0.04],
        zn4_w: [1.70,0.20,0.24], zn4_s: [1.16,-0.18,-0.25],
        zn5_w: [1.69,-0.24,0.05], zn5_s: [0.99,0.20,-0.10],
        znh_w: [1.79,-0.18,0.15], znh_s: [1.03,0.18,-0.08],
        znz_w: [1.76,-0.20,0.10], znz_s: [1.08,0.12,-0.08],
        znx_w: [1.52,-0.12,0.04], znx_s: [1.11,0.13,0],
        znc_w: [1.43,0.18,0.12], znc_s: [1.37,-0.16,-0.12],
        znv_w: [1.90,0.0,0.03], znv_s: [2.08,0.10,0.05],''')
    one(M,'    this.vrmRig.style = this.kit === "knight" && this.look.element === "light" ?', '    this.vrmRig.style = this.kit === "glaive" && this.look.element === "metal" ? "magnetic" : this.kit === "knight" && this.look.element === "light" ?')
    one(M,'    const weaponScale = this.kit === "glaive" ? 0.87 : VRM_WEAPON_SCALE;', '    const weaponScale = this.kit === "glaive" && this.look.element === "metal" ? 0.93 : this.kit === "glaive" ? 0.87 : VRM_WEAPON_SCALE;')

    # Character posture: stable front-foot lead, light bent knees, no full-swing torso roll.
    one(V,'  chainblade: { stance:', '''  // Zenith's agile two-handed spear stance (independent of Zarek's storm gait).
  magnetic: { stance: D(8), toeOut: D(7), knee: D(13), drop: 0.025, lean: D(5), chin: D(1.5), shoulderUp: D(1.3), elbowOut: D(5),
    hipSway: 0.005, hipRoll: D(0.5), contra: D(0.75), relaxKnee: D(4), headTilt: D(0.5), headYaw: D(4),
    breath: 0.65, armSwing: D(9), walkRoll: D(1.0), walkYaw: D(3) },
  chainblade: { stance:''')

    # Use an actual slender spear mesh for all metal projectiles. Separate from lightning.
    section(G,'  // ZENITH_IRON_SOVEREIGN_V1_20261108 — metal spear, not a lightning bolt.\n', '  if (style === "clusterbomb") {', '''  // ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108 — lean two-bladed spear projectiles.
  if (style === "zenith_rail" || style === "zenith_heavy" || style === "zenith_construct") {
    const steel = new THREE.MeshLambertMaterial({ color: "#d5e0ed" });
    const navy = new THREE.MeshLambertMaterial({ color: "#273b5a" });
    const gold = new THREE.MeshLambertMaterial({ color: "#c7ac78" });
    const scale = size;
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.017*scale,0.017*scale,1.02*scale,8),navy);
    rod.rotation.x = Math.PI/2; g.add(rod);
    for (const side of [-1,1]) {
      const blade = new THREE.Mesh(new THREE.ConeGeometry(0.063*scale,0.30*scale,4),steel);
      blade.rotation.x = side*Math.PI/2;
      blade.position.z = side*0.64*scale;
      g.add(blade);
      const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.032*scale,0.032*scale,0.055*scale,8),gold);
      collar.rotation.x = Math.PI/2;
      collar.position.z = side*0.49*scale;
      g.add(collar);
    }
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.038*scale,0),glow);
    gem.scale.set(0.8,0.8,1.25);
    g.add(gem);
    return;
  }
''')
    one(G,'const part={...a,id:`zxfloat${i}`,type:"projectile",style:"zenith_construct",dmg:28,pierce:false,heavy:false,speed:20,size:0.85};', 'const part={...a,id:`zxfloat${i}`,type:"projectile",style:"zenith_construct",dmg:28,pierce:false,heavy:false,speed:20,size:0.66};')
    one(G,'"zenith_construct","metal",0.85,"#a5bfe0",false,target);', '"zenith_construct","metal",0.66,"#a5bfe0",false,target);')
    one(G,'this.fxp("ring",point.clone(),"#a6bcd6",2.7,0.52,0.55);', 'this.fxp("ring",point.clone(),"#a6bcd6",1.85,0.52,0.45);')
    one(G,'this.fxp("motes",point.clone().add(new THREE.Vector3(0,1,0)),"#b5cbdd",22);', 'this.fxp("motes",point.clone().add(new THREE.Vector3(0,1,0)),"#b5cbdd",14);')
    one(G,'size:i===6?2.0:1.0};', 'size:i===6?1.05:0.64};')

    # Zenith never inherits the big lightning arena scars / swing flashes of Zarek.
    one(G, 'if (f.kit === "glaive" && big && f.root.position.y < 2.1)', 'if (f.kit === "glaive" && f.look.element !== "metal" && big && f.root.position.y < 2.1)')
    one(G, '    if (f.kit === "glaive" && a.type === "melee") {\n      const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());\n      this.fxp("sparks", p, "#78dcff", big ? 25 : 12, 5);\n    }', '    if (f.kit === "glaive" && a.type === "melee") {\n      const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());\n      if (f.look.element === "metal") {\n        this.fxp("sparks", p, "#b4c8df", big ? 9 : 5, 2.7);\n        this.fxp("flash", p, "#dbeafa", 0.12, 0.07, 0.42);\n      } else this.fxp("sparks", p, "#78dcff", big ? 25 : 12, 5);\n    }')

    # Sound names are the user's SOUND_LIST.txt paths MINUS .mp3 (not guessed filenames).
    # Keeping original filename subdirectories makes the game's /sfx/<name>.mp3 URL work.
    one(G,'  private swingSound(f: Fighter, a: Attack) {\n    const heavy =', '''  private swingSound(f: Fighter, a: Attack) {
    if (f.look.element === "metal" && f.kit === "glaive") {
      const sound = a.style === "zenith_rail" ? "fight/metal_arrow_fast_hit" :
        a.style === "zenith_arsenal" ? "misc/sci_fi_gear_turn" :
        a.style === "zenith_barrage" ? "transitions/metal_swish" :
        a.style === "zenith_heavy" ? "fight/metal_hit_woosh" :
        a.mode === "zenith_magnet" ? "misc/hi_tech_touch_with_magnet" :
        "fight/metal_hit_woosh";
      this.snd(sound, a.style === "zenith_arsenal" ? 0.57 : 0.46);
      return;
    }
    const heavy =''')
    one(G,'  private hitSound(attacker: Entity | null, a: Attack, crit: boolean) {\n    const heavy =', '''  private hitSound(attacker: Entity | null, a: Attack, crit: boolean) {
    if (attacker instanceof Fighter && attacker.look.element === "metal" && attacker.kit === "glaive") {
      this.snd("fight/metal_arrow_hit", 0.5);
      if (crit) this.snd("crit", 0.45);
      return;
    }
    const heavy =''')
    one(G,'    this.fxp("ring",p.pos.clone(),"#b1cae6",0.85,0.16,0.65);', '''    this.fxp("ring",p.pos.clone(),"#b1cae6",0.52,0.16,0.5);
    this.snd("misc/sci_fi_gear_turn", 0.55);''')
    one(G,'    f.zenithMagnetCharges = 0;\n    this.fxp("motes",f.chest(),"#a6bddc",17);', '''    f.zenithMagnetCharges = 0;
    this.fxp("motes",f.chest(),"#a6bddc",11);
    this.snd("misc/hi_tech_touch_with_magnet", 0.5);''')
    one(G,'      this.melee(f,{...a,id:`zx${i}`,style:"zenith_barrage",dmg:25,knock:i===4?1.8:0.3,stun:0.13});', '''      this.melee(f,{...a,id:`zx${i}`,style:"zenith_barrage",dmg:25,knock:i===4?1.8:0.3,stun:0.13});
      if (i===0 || i===2 || i===4) this.snd("transitions/metal_swish", 0.39);''')
    one(G,'      p.life=1.25;\n      this.fxp("flash",origin,"#d0deef",0.16,0.1,0.8);', '''      p.life=1.25;
      this.fxp("flash",origin,"#d0deef",0.12,0.1,0.7);
      if (i===6) this.snd("fight/dramatic_metal_explosion_impact", 0.62);''')
    # Custom skill handlers return before normal swingSound(), so play the missing cues there.
    one(G,'    f.model.setZenithSpearHeld(false);\n    this.fxp("flash",origin,"#acbfd9",0.38,0.14,0.72);', '''    f.model.setZenithSpearHeld(false);
    this.fxp("flash",origin,"#acbfd9",0.25,0.14,0.58);
    this.snd("fight/metal_arrow_fast_hit", 0.58);''')
    one(G,'  private zenithBarrage(f: Fighter,a:Attack) {\n    const round=this.round;', '''  private zenithBarrage(f: Fighter,a:Attack) {
    this.snd("fight/metal_hit_woosh", 0.44);
    const round=this.round;''')
    one(G,'  private zenithArsenal(f:Fighter,a:Attack) {\n    const round=this.round;', '''  private zenithArsenal(f:Fighter,a:Attack) {
    this.snd("misc/sci_fi_gear_turn", 0.56);
    const round=this.round;''')
    # A short custom cue for Zenith's parry-success riposte, not Zarek's spin.
    one(G,'    if (a.style === "parry_counter") {', '''    if (f.look.element === "metal" && a.id === "pc") {
      this.snd("fight/metallic_impact_with_whip", 0.56);
    }
    if (a.style === "parry_counter") {''')
    one(K,'// ZENITH_IRON_SOVEREIGN_V1_20261108: Metal spear kit is independent of Zarek.', '// ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108: compact weapon, dedicated spear poses, exact SFX path mapping.\n  // ZENITH_IRON_SOVEREIGN_V1_20261108: Metal spear kit is independent of Zarek.')
except Exception as exc:
    sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')

stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
for p in FILES:
    source=R/p
    backup=source.with_name(source.name+f'.before_zenith_spear_v2_{stamp}.bak')
    shutil.copy2(source,backup)
for p in FILES:
    (R/p).write_text(new[p],encoding='utf-8')
    print('Updated',p)
print('Zenith V2 installed. Copy exact sound files to public/sfx before starting game.')
