#!/usr/bin/env python3
"""Zarek Storm Glaive V1. Run from Fight-Royale/web. Safe, anchor-checked patch; backups created."""
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path.cwd()
FILES = [
    'src/game/roster.ts', 'src/game/kits.ts', 'src/game/model.ts',
    'src/game/vrm.ts', 'src/game/fighter.ts', 'src/game/game.ts', 'src/ui/Select.tsx', 'src/ui/GameView.tsx',
]
if not (ROOT / 'package.json').exists() or not (ROOT / 'src/game/game.ts').exists():
    sys.exit('Run this script from your web folder (beside package.json).')
orig = {p:(ROOT/p).read_text(encoding='utf-8') for p in FILES}
if 'ZAREK_STORM_V1' in orig['src/game/roster.ts']:
    print('Zarek Storm Glaive V1 is already installed. No files changed.')
    sys.exit(0)
patch = dict(orig)
def rep(file, old, new):
    s = patch[file]
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f'Cannot safely patch {file}: expected exactly one anchor, found {n}: {old[:80]!r}')
    patch[file] = s.replace(old, new, 1)

# New roster entry appended so existing character indexes and saves do not move.
rep('src/game/roster.ts', '\n];\n\nexport function resolveEnemy', '''
  // ZAREK_STORM_V1 — temporary Nyx VRM, unique female glaive kit and storm animations.
  { id: "zarek", title: "Storm Glaive", role: "Duelist - Double-Ended Glaive",
    desc: "A lightning duelist who builds Clash Momentum by meeting enemy blades head-on. Charged momentum empowers her spinning glaive attacks.",
    stats: { power: 4, speed: 4, range: 4, defense: 3 },
    look: { name: "Zarek", body: "f", vrm: "nyx", kit: "glaive", element: "storm", outfit: "assassin", style: "ponytail", hat: "none",
      hair: "#c8d7eb", hair_shade: "#6f93c5", iris_top: "#2d74d8", iris_bottom: "#a5f0ff", eye_dark: "#11284c",
      tunic: "#17273f", band: "#326ba4", pants: "#10192c", boots: "#17253a", metal: "#cbdcec", trim: "#8bdfff",
      cape: "#192c4d", cape_bottom: "#356dc1", glow: "#62cfff", shield: "#183a5a", emblem: "#c7faff" } },
];

export function resolveEnemy''')

# Gameplay configuration, including universal air-combat kit support.
rep('src/game/kits.ts', '  sickle: { hp: 1950, guard: 62, move: 4.5, walk: 3.55, parry: 0.20, jump: 8.2 },', '''  sickle: { hp: 1950, guard: 62, move: 4.5, walk: 3.55, parry: 0.20, jump: 8.2 },
  glaive: { hp: 2250, guard: 88, move: 4.0, walk: 3.15, parry: 0.19, jump: 7.7 },''')
rep('src/game/kits.ts', '    sickle: sickle,', '    sickle: sickle,\n    glaive: glaive,')
rep('src/game/kits.ts', '    case "sickle":\n      return a({ name: "Carrion Sweep",', '''    case "glaive":
      return a({ name: "Arc Flash", desc: "An electrified reverse-end sweep. Gains more stagger pressure than a normal light strike.", cd: 9,
        type: "melee", wind: 0.17, active: 0.12, recover: 0.40, dmg: 115, guard: 32, reach: 2.35,
        knock: 3.4, stun: 0.37, style: "glaive_arc", pose_w: "gl4_w", pose_s: "gl4_s" });
    case "sickle":
      return a({ name: "Carrion Sweep",''')
rep('src/game/kits.ts', 'function sickle(): Record<string, Attack> {', '''// ZAREK_STORM_V1 — weapon clashes award Momentum; ability effects are host-controlled.
function glaive(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.12, active: 0.09, recover: 0.19, dmg: 65, guard: 17, reach: 2.25, lunge: 2.8, knock: 1.2, stun: 0.24, pose_w: "gl1_w", pose_s: "gl1_s", next: "l2" }),
    l2: a({ wind: 0.12, active: 0.09, recover: 0.20, dmg: 70, guard: 18, reach: 2.25, lunge: 2.9, knock: 1.3, stun: 0.25, pose_w: "gl2_w", pose_s: "gl2_s", next: "l3" }),
    l3: a({ wind: 0.15, active: 0.10, recover: 0.23, dmg: 78, guard: 21, reach: 2.3, lunge: 2.8, knock: 1.6, stun: 0.28, pose_w: "gl3_w", pose_s: "gl3_s", next: "l4" }),
    l4: a({ wind: 0.22, active: 0.12, recover: 0.40, dmg: 95, guard: 27, reach: 2.4, lunge: 2.0, knock: 3.5, stun: 0.38, pose_w: "gl4_w", pose_s: "gl4_s" }),
    heavy: a({ wind: 0.35, active: 0.14, recover: 0.55, dmg: 165, guard: 48, reach: 2.6, lunge: 2.5, knock: 5.0, stun: 0.52, heavy: true, pose_w: "glh_w", pose_s: "glh_s" }),
    z: a({ name: "Flash Reversal", desc: "Sidestep and sweep. Real weapon clashes during this move award 2 Clash Momentum instead of 1.",
      cd: 6, wind: 0.13, active: 0.13, recover: 0.36, dmg: 85, guard: 26, reach: 2.3, knock: 2.0, stun: 0.28,
      style: "glaive_reversal", pose_w: "glz_w", pose_s: "glz_s" }),
    x: a({ name: "Thunder Barrage", desc: "Five individually animated glaive strikes. Spend 1 Clash Momentum to amplify the final strike.",
      cd: 10, wind: 0.17, active: 0.76, recover: 0.39, dmg: 42, guard: 14, reach: 2.2, knock: 0.8, stun: 0.18,
      style: "glaive_barrage", pose_w: "glx_w", pose_s: "gl1_s" }),
    c: a({ name: "Heaven's Judgment", desc: "Three sweeping lightning slashes. At 3 Clash Momentum, spend all stacks for a final electric shockwave.",
      cd: 20, wind: 0.28, active: 0.84, recover: 0.54, dmg: 90, guard: 26, reach: 2.55,
      knock: 1.3, stun: 0.30, heavy: true, style: "glaive_judgment", pose_w: "glc_w", pose_s: "glc_s" }),
  };
}

function sickle(): Record<string, Attack> {''')
rep('src/game/kits.ts', '    sickle: ["Sickle Pursuit", 40, 2.15, "vr1_w", "vr3_s"],', '    sickle: ["Sickle Pursuit", 40, 2.15, "vr1_w", "vr3_s"],\n    glaive: ["Storm Lift", 43, 2.35, "gl3_w", "gl3_s"],')
rep('src/game/kits.ts', 'const fast = ["assassin", "sickle", "katana", "kicks", "wind"].includes(kit);', 'const fast = ["assassin", "sickle", "glaive", "katana", "kicks", "wind"].includes(kit);')
# Distinct attack poses; left arm hand IK stays on the staff grip when using a VRM.
rep('src/game/kits.ts', 'const TABLES: Record<string, Record<string, Pose>> = {', '''// Storm Glaive: coordinated two-hand weapon cuts, a bladed stance, and wide reverse sweeps.
const GLAIVE: Record<string, Pose> = {
  ...twoHanded(KNIGHT),
  idle: P([0.04, -0.22, 0], [0, 0.2, 0], [-0.62, 0.17, -0.3], [-0.1, 0, 0.2], [-0.76, 0.52, 0.1], [0, 0, 0], [-0.2, 0, 0.06], [0.25, 0, -0.06], -0.045),
  block: P([0.12, 0, 0], [0.03, 0, 0], [-1.12, 0.3, -0.15], [0.14, 0, 0], [-1.0, -0.3, 0.2], [0, 0, 0], [-0.35, 0, 0.06], [0.35, 0, -0.06], -0.08),
  gl1_w: P([0.06, -0.72, 0], [0, 0.56, 0], [-1.3, -1.05, -0.16], [0.62, 0, 0], [-1.4, -0.48, 0.15], [0.4, 0, 0], [-0.3, 0, 0.08], [0.34, 0, -0.08], -0.08),
  gl1_s: P([0.13, 0.62, 0], [0, -0.45, 0], [-1.6, 1.0, -0.1], [0.18, 0, 0], [-1.55, 0.65, 0.18], [0.15, 0, 0], [-0.4, 0, 0.08], [0.42, 0, -0.08], -0.11),
  gl2_w: P([0.12, 0.62, 0], [0, -0.48, 0], [-1.6, 1.1, 0.08], [0.24, 0, 0], [-1.55, 0.68, 0.1], [0.15, 0, 0], [-0.4, 0, 0.08], [0.35, 0, -0.08], -0.11),
  gl2_s: P([0.08, -0.75, 0], [0, 0.62, 0], [-1.45, -1.2, -0.18], [0.12, 0, 0], [-1.35, -0.66, 0.2], [0.2, 0, 0], [-0.43, 0, 0.08], [0.35, 0, -0.08], -0.12),
  gl3_w: P([-0.16, -0.26, 0], [-0.02, 0.3, 0], [-2.4, -0.65, -0.16], [0.36, 0, 0], [-2.2, -0.22, 0.1], [0.24, 0, 0], [-0.5, 0, 0.1], [0.35, 0, -0.08], -0.1),
  gl3_s: P([0.05, 0.5, 0], [0, -0.3, 0], [-1.05, 0.6, -0.1], [0.22, 0, 0], [-1.15, 0.25, 0.2], [0.18, 0, 0], [-0.46, 0, 0.08], [0.4, 0, -0.08], -0.1),
  gl4_w: P([0.19, 0.85, 0], [0, -0.5, 0], [-1.72, 1.2, 0], [0.6, 0, 0], [-1.8, 0.55, 0.15], [0.32, 0, 0], [-0.46, 0, 0.08], [0.39, 0, -0.08], -0.14),
  gl4_s: P([0.32, -0.8, 0], [-0.12, 0.5, 0], [-1.3, -1.15, -0.1], [0.18, 0, 0], [-1.4, -0.7, 0.15], [0.16, 0, 0], [-0.6, 0, 0.08], [0.45, 0, -0.08], -0.16),
  glh_w: P([-0.07, -0.8, 0], [0.05, 0.63, 0], [-2.7, -0.66, -0.06], [0.75, 0, 0], [-2.65, -0.12, 0.14], [0.48, 0, 0], [-0.55, 0, 0.12], [0.38, 0, -0.09], -0.15),
  glh_s: P([0.36, 0.95, 0], [-0.14, -0.62, 0], [-0.8, 1.3, 0], [0.22, 0, 0], [-1.05, 0.75, 0.16], [0.18, 0, 0], [-0.6, 0, 0.1], [0.48, 0, -0.1], -0.18),
  glz_w: P([0.25, -0.76, -0.08], [-0.1, 0.6, 0], [-0.8, -0.8, -0.3], [0.3, 0, 0], [-1.05, -0.3, 0.3], [0.2, 0, 0], [-0.6, 0, 0.1], [0.6, 0, -0.1], -0.14),
  glz_s: P([0.15, 0.87, 0], [-0.12, -0.6, 0], [-1.65, 1.1, -0.13], [0.3, 0, 0], [-1.6, 0.7, 0.15], [0.2, 0, 0], [-0.55, 0, 0.1], [0.5, 0, -0.1], -0.15),
  glx_w: P([-0.06, 0.05, 0], [0, 0.05, 0], [-1.0, 0.6, -0.4], [0.5, 0, 0], [-1.1, 0.1, 0.4], [0.1, 0, 0], [-0.45, 0, 0.1], [0.4, 0, -0.1], -0.09),
  glc_w: P([-0.12, -0.55, 0], [0.04, 0.47, 0], [-2.5, -0.66, -0.04], [0.8, 0, 0], [-2.3, -0.2, 0.12], [0.4, 0, 0], [-0.55, 0, 0.11], [0.52, 0, -0.1], -0.18),
  glc_s: P([0.31, 0.68, 0], [-0.15, -0.45, 0], [-1.05, 1.1, -0.08], [0.2, 0, 0], [-1.2, 0.48, 0.14], [0.16, 0, 0], [-0.58, 0, 0.1], [0.49, 0, -0.1], -0.18),
  charge: P([-0.06, -0.7, 0], [0, 0.48, 0], [-2.4, -0.7, -0.15], [0.8, 0, 0], [-2.4, -0.2, 0.1], [0.4, 0, 0], [-0.5, 0, 0.1], [0.4, 0, -0.1], -0.12),
};

const TABLES: Record<string, Record<string, Pose>> = {''')
rep('src/game/kits.ts', '  sickle: SICKLE,', '  sickle: SICKLE,\n  glaive: GLAIVE,')

# Programmatic two-ended weapon, steel tips and two-handed hilt.
rep('src/game/model.ts', '      case "sickle": this.buildSickles(); break;', '      case "sickle": this.buildSickles(); break;\n      case "glaive": this.buildGlaive(); break;')
rep('src/game/model.ts', '  private buildSword() {', '''  /** ZAREK_STORM_V1: double-ended conductive glaive; meshes follow the VRM's hands. */
  private buildGlaive() {
    const staff = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    mesh(staff, cyl(0.019, 0.022, 1.53, 12), this.tn("#233449"));
    mesh(staff, cyl(0.028, 0.028, 0.42, 12), this.tn("#101a2a"), [0, 0, 0]);
    for (const s of [-1, 1]) {
      mesh(staff, cyl(0.047, 0.035, 0.12, 12), this.tn(this.look.trim), [0, s * 0.73, 0]);
      // Broad at the base, narrow at the end: thin diamond-edged blade, not a round club.
      const outline = new THREE.Shape();
      outline.moveTo(-0.045, s * 0.72);
      outline.lineTo(-0.093, s * 0.89);
      outline.lineTo(-0.067, s * 1.10);
      outline.lineTo(0, s * 1.31);
      outline.lineTo(0.075, s * 1.10);
      outline.lineTo(0.095, s * 0.89);
      outline.lineTo(0.047, s * 0.72);
      outline.closePath();
      const blade = new THREE.ExtrudeGeometry(outline, { depth: 0.014, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.006, bevelSegments: 1 });
      blade.translate(0, 0, -0.007);
      mesh(staff, blade, this.steel());
      mesh(staff, box(0.014, 0.30, 0.02), this.glowMat, [0, s * 1.04, 0.013]);
      mesh(staff, sphere(0.035, 12), this.gem(), [0, s * 0.82, 0]);
    }
    for (const y of [-0.32, -0.18, 0.18, 0.32]) mesh(staff, torus(0.029, 0.039), this.tn(this.look.trim), [0, y, 0], [PI / 2, 0, 0], [1, 0.35, 1]);
    this.gripL = pivot(staff, [0, -0.29, 0]);
    this.bladeBase = pivot(staff, [0, 0.78, 0]);
    this.bladeTip = pivot(staff, [0, 1.32, 0]);
    this.shieldNode = staff;
    this.castPoint = this.bladeTip;
  }

  private buildSword() {''')
rep('src/game/model.ts', '    this.vrmRig.followArm = this.kit === "sickle" ? 0.18 :', '    this.vrmRig.followArm = this.kit === "glaive" ? 0.24 : this.kit === "sickle" ? 0.18 :')
rep('src/game/model.ts', '    this.vrmRig.style = this.kit === "sickle" ? "feral" :', '    this.vrmRig.style = this.kit === "glaive" ? "storm" : this.kit === "sickle" ? "feral" :')
rep('src/game/model.ts', '    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = 1; }', '    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = this.kit === "glaive" ? 0.4 : 1; }')

rep('src/game/vrm.ts', '  heavy: { stance: D(14),', '''  storm: { stance: D(7), toeOut: D(8), knee: D(10), drop: 0.025, lean: D(3), chin: D(1), shoulderUp: D(2), elbowOut: D(5),
    hipSway: 0.012, hipRoll: D(1.4), contra: D(1.5), relaxKnee: D(5), headTilt: D(0.8), headYaw: D(5),
    breath: 0.8, armSwing: D(12), walkRoll: D(1.6), walkYaw: D(3) },
  heavy: { stance: D(14),''')

# Client sync, match reset, and on-clash momentum (only on actual collisions).
rep('src/game/fighter.ts', '  bloodlust = 0;', '  clashMomentum = 0; // ZAREK_STORM_V1: 0..3, earned only by real melee weapon clashes.\n  bloodlust = 0;')
rep('src/game/fighter.ts', '    this.guard = this.maxGuard;\n    this.bloodlust = 0; this.bloodFrenzyT = 0;', '    this.guard = this.maxGuard;\n    this.clashMomentum = 0;\n    this.bloodlust = 0; this.bloodFrenzyT = 0;')
rep('src/game/fighter.ts', '  ko() {\n    this.airChaseT = 0; this.airChaseMoveT = 0;\n    this.bloodlust = 0;', '  ko() {\n    this.airChaseT = 0; this.airChaseMoveT = 0;\n    this.clashMomentum = 0;\n    this.bloodlust = 0;')
if '+this.bloodFestivalT.toFixed(2)];' in patch['src/game/fighter.ts']:
    rep('src/game/fighter.ts', '+this.bloodFestivalT.toFixed(2)];', '+this.bloodFestivalT.toFixed(2), this.clashMomentum];')
elif '+this.bladeSwingYaw.toFixed(3)];' in patch['src/game/fighter.ts']:
    rep('src/game/fighter.ts', '+this.bladeSwingYaw.toFixed(3)];', '+this.bladeSwingYaw.toFixed(3), this.clashMomentum];')
else:
    raise RuntimeError('Unknown fighter.ts snapshot layout; no files changed.')
rep('src/game/fighter.ts', 'this.bloodFestivalT = s[28] ?? 0;', 'this.bloodFestivalT = s[28] ?? 0; this.clashMomentum = s[s.length - 1] ?? 0;')

rep('src/game/game.ts', '    switch (a.type) {\n      case "projectile":', '''    if (f.kit === "glaive" && (a.style === "glaive_reversal" || a.style === "glaive_barrage" || a.style === "glaive_judgment")) {
      this.stormGlaiveSwing(f, a);
      return;
    }
    if (f.kit === "glaive" && a.type === "melee") {
      const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("sparks", p, "#78dcff", big ? 25 : 12, 5);
    }
    switch (a.type) {
      case "projectile":''')
rep('src/game/game.ts', '  private melee(f: Fighter, a: Attack) {', '''  /** ZAREK_STORM_V1: separate, weapon-driven attacks; each can clash, block, or be parried. */
  private stormGlaiveSwing(f: Fighter, a: Attack) {
    const startRound = this.round;
    const serial = f.swingSerial;
    const glow = f.look.glow;
    const at = (idx: number, part: Attack, pose: string) => {
      if (startRound !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      f.poseOverride = pose;
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", tip, glow);
      this.fxp("sparks", tip, idx % 2 === 0 ? "#9eefff" : "#438dff", 16 + idx * 4, 5);
      this.fxp("flash", tip, glow, 0.26 + idx * 0.08, 0.1, 0.6);
      this.melee(f, part); // normal attack collision, guard, and parry mechanics apply.
    };
    if (a.style === "glaive_reversal") {
      // A readable short lateral feint, NOT a teleport or free invulnerability.
      const sign = (f.swingSerial % 2) === 0 ? 1 : -1;
      const side = new THREE.Vector3(Math.cos(f.root.rotation.y), 0, -Math.sin(f.root.rotation.y));
      const nearby = f.opponent && f.opponent.root.position.distanceTo(f.root.position) < 3.5;
      if (nearby && !f.stage) {
        const next = f.root.position.clone().addScaledVector(side, sign * 0.36);
        if (Math.hypot(next.x, next.z) < 6.4) f.root.position.copy(next);
      }
      at(0, a, "glz_s");
      return;
    }
    if (a.style === "glaive_barrage") {
      const empowered = f.clashMomentum > 0;
      if (empowered) f.clashMomentum -= 1;
      const phases = ["gl1_s", "gl2_s", "gl3_s", "gl2_s", "gl4_s"];
      for (let i = 0; i < 5; i++) this.later(i * 0.14, () => {
        const hit: Attack = { ...a, dmg: i === 4 ? (empowered ? 86 : 55) : 42,
          guard: i === 4 ? 24 : 12, knock: i === 4 ? 3.1 : 0.7,
          stun: i === 4 ? 0.35 : 0.16, reach: i === 4 ? 2.4 : 2.2 };
        at(i, hit, phases[i]);
        if (i === 4 && empowered && startRound === this.round) {
          this.fxp("lightning", f.chest(), "#7fdcff");
          this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "THUNDER FINISH", "#a5ebff", 0.75);
        }
      });
      return;
    }
    if (a.style === "glaive_judgment") {
      const empowered = f.clashMomentum >= 3;
      if (empowered) f.clashMomentum -= 3;
      for (let i = 0; i < 3; i++) this.later(i * 0.28, () => {
        const hit: Attack = { ...a, dmg: [90, 110, 145][i], guard: [26, 30, 43][i],
          knock: i === 2 ? 5.2 : 1.3, stun: i === 2 ? 0.55 : 0.24,
          reach: i === 2 ? 2.65 : 2.5 };
        at(i, hit, ["gl1_s", "gl2_s", "glc_s"][i]);
        if (i === 2 && empowered && f.state === S.ATTACK && f.swingSerial === serial && startRound === this.round) {
          const pulse: Attack = { ...a, type: "strike", style: "lightning", at: "self", delay: 0.05,
            radius: 2.65, repeat: 1, dmg: 85, guard: 24, knock: 3.0, stun: 0.24 };
          this.runStrike(f, pulse, f.atkPower);
          this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "STORM BREAK", "#9deaff", 0.9);
        }
      });
    }
  }

  private melee(f: Fighter, a: Attack) {''')
rep('src/game/game.ts', '  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {\n    a.clashRecoil();', '''  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {
    // Actual attack-vs-attack contact ONLY. Save skill before clashRecoil clears it.
    for (const f of [a, b]) if (f.kit === "glaive") {
      const gain = f.atk?.style === "glaive_reversal" ? 2 : 1;
      f.clashMomentum = Math.min(3, f.clashMomentum + gain);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), `MOMENTUM ${f.clashMomentum}/3`, "#a6efff", 0.8);
      this.fxp("lightning", f.chest(), "#6acfff");
    }
    a.clashRecoil();''')
rep('src/game/game.ts', 'bloodFestivalT: f.bloodFestivalT });',
    'bloodFestivalT: f.bloodFestivalT, clashMomentum: f.clashMomentum });')
rep('src/ui/GameView.tsx', '              {me.id === "veyr" && (', '''              {me.id === "zarek" && (
                <div style={{ marginTop: 8, color: "#9ce8ff", fontSize: 11 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, marginBottom: 4 }}>
                    <span>CLASH MOMENTUM</span><span>{me.clashMomentum}/3</span>
                  </div>
                  <div style={{ display: "flex", gap: 5 }}>
                    {[0, 1, 2].map((n) => (
                      <span key={n} style={{ display: "block", flex: 1, height: 7, borderRadius: 4,
                        background: n < me.clashMomentum ? "#6edcff" : "rgba(160,216,255,0.18)",
                        boxShadow: n < me.clashMomentum ? "0 0 7px #58caff" : "none" }} />
                    ))}
                  </div>
                </div>
              )}
              {me.id === "veyr" && (''')
rep('src/ui/Select.tsx', '  sickle: "Tap: 4-hit dual-sickle combo', '  glaive: "Tap: 4-hit double-glaive combo  -  Hold: Split Current  -  Real clashes build Momentum (max 3)  -  Z: reversal  -  X: barrage  -  C: lightning finisher",\n  sickle: "Tap: 4-hit dual-sickle combo')

# Full anchor validation done. Write only after EVERY patch has succeeded.
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
for file in FILES:
    if patch[file] != orig[file]:
        src = ROOT/file
        backup = src.with_name(src.name + f'.zarek-backup-{stamp}')
        backup.write_text(orig[file], encoding='utf-8')
        src.write_text(patch[file], encoding='utf-8')
        print('PATCH', file)
print('\nDONE — Zarek added using nyx.vrm; original Nyx unaffected.')
print('NEXT — npm run dev  (test skills, clashes, weapon alignment)')
print('For signed-in purchases run the included SQL migration in Supabase SQL Editor.')
