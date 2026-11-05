#!/usr/bin/env python3
"""Kaizen — Chainblade Berserker V1. Run from Fight-Royale/web.
Validates ALL exact anchors before modifying any file. Saves timestamped backups.
Preserves existing Garrick, Zarek, Veyr, Bob, and air-combat changes.
"""
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path.cwd()
FILES = ['src/game/roster.ts', 'src/game/kits.ts', 'src/game/model.ts',
         'src/game/vrm.ts', 'src/game/fighter.ts', 'src/game/game.ts',
         'src/ui/Select.tsx']
if not (ROOT / 'package.json').exists() or not (ROOT / 'src/game/game.ts').exists():
    sys.exit('Please run this script inside your web folder (beside package.json).')
original = {p: (ROOT/p).read_text(encoding='utf-8') for p in FILES}
if 'KAIZEN_CHAINBLADE_V1' in original['src/game/roster.ts']:
    print('Kaizen Chainblade V1 is already installed. No files modified.')
    sys.exit(0)
patched = dict(original)
def rep(file, old, new):
    source = patched[file]
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'Patch aborted BEFORE changing files: {file}: expected one anchor, got {count}: {old[:90]!r}')
    patched[file] = source.replace(old, new, 1)

# Append only. Never reorder existing characters, which would break saved picks.
rep('src/game/roster.ts', '\n];\n\nexport function resolveEnemy', '''
  // KAIZEN_CHAINBLADE_V1 — uses Garrick's male VRM until kaizen.vrm is ready.
  { id: "kaizen", title: "Chainblade Berserker", role: "Berserker - Segmented Sword",
    desc: "Switches from precise close sword cuts to unpredictable long chainblade arcs. Hook enemies, lash around their guard, and unleash a short frenzy.",
    stats: { power: 5, speed: 3, range: 4, defense: 3 },
    look: { name: "Kaizen", body: "m", vrm: "garrick", kit: "chainblade", element: "chain", outfit: "knight", style: "short", hat: "none",
      hair: "#231f29", hair_shade: "#716570", iris_top: "#9d282a", iris_bottom: "#ff895c", eye_dark: "#2c0910",
      tunic: "#332831", band: "#6e3034", pants: "#221e25", boots: "#352b30", metal: "#adb2bd", trim: "#b88f7b",
      cape: "#4e242a", cape_bottom: "#8e3039", glow: "#ff5b63", shield: "#3b242b", emblem: "#ffa5a0" } },
];

export function resolveEnemy''')

# Kit, cooldowns, and attack data. No indiscriminate 4m hitboxes.
rep('src/game/kits.ts', '  bomb: { hp: 2100, guard: 70, move: 3.5, walk: 2.8, parry: 0.16, jump: 7.0 },',
'''  bomb: { hp: 2100, guard: 70, move: 3.5, walk: 2.8, parry: 0.16, jump: 7.0 },
  chainblade: { hp: 2450, guard: 100, move: 3.55, walk: 2.75, parry: 0.16, jump: 7.0 },''')
rep('src/game/kits.ts', '    sickle: sickle,', '    sickle: sickle,\n    chainblade: chainblade,')
rep('src/game/kits.ts', '    case "greatsword":\n      return a({ name: "Berserk",', '''    case "chainblade":
      return a({ name: "Razor Recall", desc: "Snap the chainblade outward and whip it back. Long reach but a punishable recovery.", cd: 10,
        wind: 0.27, active: 0.13, recover: 0.55, dmg: 135, guard: 33, reach: 3.2, knock: 3.0, stun: 0.37,
        style: "chain_recall", pose_w: "cbv_w", pose_s: "cbv_s" });
    case "greatsword":
      return a({ name: "Berserk",''')
rep('src/game/kits.ts', 'function greatsword(): Record<string, Attack> {', '''// KAIZEN_CHAINBLADE_V1 — compact sword combo; the extended chain is powerful but slower.
function chainblade(): Record<string, Attack> {
  return {
    l1: a({ wind: 0.17, active: 0.10, recover: 0.26, dmg: 76, guard: 21, reach: 2.05, lunge: 2.15, knock: 1.6, stun: 0.29, style: "chain_basic", pose_w: "cb1_w", pose_s: "cb1_s", next: "l2" }),
    l2: a({ wind: 0.18, active: 0.10, recover: 0.29, dmg: 82, guard: 22, reach: 2.1, lunge: 2.05, knock: 1.8, stun: 0.31, style: "chain_basic", pose_w: "cb2_w", pose_s: "cb2_s", next: "l3" }),
    l3: a({ wind: 0.22, active: 0.12, recover: 0.34, dmg: 94, guard: 26, reach: 2.2, lunge: 2.05, knock: 2.3, stun: 0.34, style: "chain_basic", pose_w: "cb3_w", pose_s: "cb3_s", next: "l4" }),
    l4: a({ wind: 0.30, active: 0.15, recover: 0.48, dmg: 116, guard: 35, reach: 2.35, lunge: 1.8, knock: 4.5, stun: 0.48, style: "chain_basic", pose_w: "cb4_w", pose_s: "cb4_s" }),
    heavy: a({ name: "Chainbreaker", desc: "Unfurl the segmented sword into a heavy, long-reach lash. Readable startup.", wind: 0.4, active: 0.16, recover: 0.67, dmg: 185, guard: 51, reach: 3.05, lunge: 1.3, knock: 5.6, stun: 0.56, heavy: true,
      style: "chain_heavy", pose_w: "cbh_w", pose_s: "cbh_s" }),
    z: a({ name: "Chain Snare", desc: "Hook a target at mid range and yank them closer on an actual HP hit. Blocks and clashes prevent the pull.", cd: 7,
      wind: 0.24, active: 0.14, recover: 0.46, dmg: 100, guard: 28, reach: 3.0, knock: 0.8, stun: 0.40,
      style: "chain_hook", pose_w: "cbz_w", pose_s: "cbz_s" }),
    x: a({ name: "Rending Orbit", desc: "Three distinct sweeping chainblade cuts that can be blocked, parried, or clashed with individually.", cd: 11,
      wind: 0.25, active: 0.68, recover: 0.5, dmg: 65, guard: 17, reach: 2.85, knock: 1.0, stun: 0.23,
      style: "chain_carousel", pose_w: "cbx_w", pose_s: "cbx1_s" }),
    c: a({ name: "Unbound Drive", desc: "For 5 seconds, the sword partially unfolds: 20% more damage and extra reach on basics. Still blockable and parryable.", cd: 18,
      type: "buff", mode: "rage", duration: 5, wind: 0.26, recover: 0.45, style: "chain_unbound", pose_w: "cbc_w", pose_s: "cbc_s" }),
  };
}

function greatsword(): Record<string, Attack> {''')
# The common air system gets his own anti-air, not Gale's exclusive downward dives.
if '    glaive: ["Storm Lift", 43, 2.35, "gl3_w", "gl3_s"],' in patched['src/game/kits.ts']:
    rep('src/game/kits.ts', '    glaive: ["Storm Lift", 43, 2.35, "gl3_w", "gl3_s"],',
        '    glaive: ["Storm Lift", 43, 2.35, "gl3_w", "gl3_s"],\n    chainblade: ["Chain Lift", 48, 2.30, "cb3_w", "cb3_s"],')
else:
    rep('src/game/kits.ts', '    sickle: ["Sickle Pursuit", 40, 2.15, "vr1_w", "vr3_s"],',
        '    sickle: ["Sickle Pursuit", 40, 2.15, "vr1_w", "vr3_s"],\n    chainblade: ["Chain Lift", 48, 2.30, "cb3_w", "cb3_s"],')
rep('src/game/kits.ts', 'const fast = ["assassin", "sickle",', 'const fast = ["chainblade", "assassin", "sickle",')
# Dedicated poses: right arm handles the slash, left-hand IK follows the hilt.
rep('src/game/kits.ts', 'const TABLES: Record<string, Record<string, Pose>> = {', '''const CHAINBLADE: Record<string, Pose> = {
  ...twoHanded(KNIGHT),
  idle: P([0.08, -0.12, 0], [-0.02, 0.1, 0], [-1.08, 0.22, -0.12], [-0.35, 0, 0], [-1.0, 0.52, 0.12], [-0.34, 0, 0], [-0.15, 0, 0.05], [0.15, 0, -0.05], -0.07),
  cb1_w: P([0.15, -0.8, -0.06], [-0.08, 0.55, 0], [-1.05, -1.1, -0.2], [0.65, 0, 0], [-1.2, -0.7, 0.1], [0.45, 0, 0], [-0.38, 0, 0.07], [0.34, 0, -0.06], -0.12),
  cb1_s: P([0.28, 0.7, 0.08], [-0.13, -0.45, 0], [-1.5, 0.92, 0], [0.26, 0, 0], [-1.5, 1.1, 0.1], [0.22, 0, 0], [-0.54, 0, 0.09], [0.44, 0, -0.08], -0.16),
  cb2_w: P([0.17, 0.7, 0.07], [-0.06, -0.5, 0], [-1.25, 1.06, 0], [0.44, 0, 0], [-1.4, 1.26, 0.2], [0.3, 0, 0], [-0.39, 0, 0.07], [0.36, 0, -0.07], -0.13),
  cb2_s: P([0.28, -0.68, -0.08], [-0.12, 0.45, 0], [-1.56, -0.92, -0.02], [0.2, 0, 0], [-1.58, -0.63, 0.2], [0.18, 0, 0], [-0.55, 0, 0.09], [0.44, 0, -0.08], -0.16),
  cb3_w: P([-0.12, -0.35, 0], [0.06, 0.2, 0], [-2.4, -0.45, -0.1], [0.62, 0, 0], [-2.25, -0.2, 0.17], [0.5, 0, 0], [-0.35, 0, 0.08], [0.32, 0, -0.07], -0.12),
  cb3_s: P([0.38, 0.3, 0.08], [-0.18, -0.2, 0], [-0.9, 0.58, 0], [0.23, 0, 0], [-1.05, 0.78, 0.18], [0.2, 0, 0], [-0.6, 0, 0.1], [0.5, 0, -0.09], -0.22),
  cb4_w: P([0.19, 0.87, 0.07], [-0.07, -0.5, 0], [-1.7, 1.15, 0.1], [0.52, 0, 0], [-1.6, 1.3, 0.16], [0.42, 0, 0], [-0.44, 0, 0.08], [0.4, 0, -0.07], -0.16),
  cb4_s: P([0.38, -0.95, -0.1], [-0.16, 0.58, 0], [-1.5, -1.2, -0.05], [0.1, 0, 0], [-1.55, -0.9, 0.2], [0.1, 0, 0], [-0.65, 0, 0.1], [0.5, 0, -0.1], -0.20),
  cbh_w: P([0.15, -1.02, -0.08], [0, 0.62, 0], [-1.17, -1.32, -0.2], [0.72, 0, 0], [-1.08, -1.08, 0.22], [0.6, 0, 0], [-0.53, 0, 0.1], [0.46, 0, -0.08], -0.19),
  cbh_s: P([0.45, 1.06, 0.1], [-0.22, -0.6, 0], [-1.5, 1.2, -0.12], [0.2, 0, 0], [-1.4, 1.48, 0.15], [0.15, 0, 0], [-0.73, 0, 0.1], [0.58, 0, -0.09], -0.23),
  cbz_w: P([0.12, -0.4, 0], [0, 0.25, 0], [-1.2, -0.5, -0.24], [0.8, 0, 0], [-1.22, -0.14, 0.25], [0.35, 0, 0], [-0.4, 0, 0.08], [0.35, 0, -0.07], -0.14),
  cbz_s: P([0.34, 0.15, 0], [-0.1, -0.1, 0], [-1.44, 0.04, -0.13], [0.1, 0, 0], [-1.4, 0.23, 0.17], [0.1, 0, 0], [-0.7, 0, 0.09], [0.52, 0, -0.08], -0.21),
  cbx_w: P([0.1, -0.76, 0], [0, 0.55, 0], [-1.15, -0.95, -0.1], [0.62, 0, 0], [-1.3, -0.57, 0.18], [0.5, 0, 0], [-0.45, 0, 0.08], [0.42, 0, -0.08], -0.16),
  cbx1_s: P([0.32, 0.85, 0.03], [-0.18, -0.48, 0], [-1.36, 1.02, 0], [0.25, 0, 0], [-1.26, 1.28, 0.15], [0.22, 0, 0], [-0.61, 0, 0.1], [0.48, 0, -0.08], -0.21),
  cbx2_s: P([0.25, -0.95, -0.06], [-0.12, 0.5, 0], [-1.48, -1.06, -0.1], [0.25, 0, 0], [-1.5, -0.78, 0.15], [0.2, 0, 0], [-0.5, 0, 0.09], [0.5, 0, -0.08], -0.22),
  cbx3_s: P([0.4, 0.75, 0.08], [-0.2, -0.4, 0], [-1.23, 0.98, 0], [0.2, 0, 0], [-1.23, 1.3, 0.12], [0.2, 0, 0], [-0.68, 0, 0.1], [0.55, 0, -0.09], -0.24),
  cbc_w: P([0.05, -0.55, 0], [0, 0.4, 0], [-1.6, -0.55, 0.0], [0.4, 0, 0], [-1.6, -0.1, 0.2], [0.3, 0, 0], [-0.52, 0, 0.08], [0.45, 0, -0.08], -0.14),
  cbc_s: P([-0.05, 0.2, 0], [-0.1, -0.1, 0], [-2.2, 0.12, -0.08], [0.9, 0, 0], [-2.1, 0.55, 0.16], [0.8, 0, 0], [-0.55, 0, 0.08], [0.45, 0, -0.08], -0.16),
  cbv_w: P([0.1, -0.8, 0], [0, 0.5, 0], [-1.43, -0.95, 0], [0.6, 0, 0], [-1.45, -0.62, 0.16], [0.45, 0, 0], [-0.46, 0, 0.08], [0.42, 0, -0.08], -0.15),
  cbv_s: P([0.35, 0.86, 0], [-0.16, -0.5, 0], [-1.38, 0.98, 0], [0.1, 0, 0], [-1.35, 1.25, 0.12], [0.08, 0, 0], [-0.62, 0, 0.1], [0.49, 0, -0.08], -0.20),
};

const TABLES: Record<string, Record<string, Pose>> = {''')
if '  greatsword: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },' in patched['src/game/kits.ts']:
    rep('src/game/kits.ts', '  greatsword: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },',
        '  greatsword: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },\n  chainblade: CHAINBLADE,')
else:
    rep('src/game/kits.ts', '  greatsword: twoHanded(KNIGHT),',
        '  greatsword: twoHanded(KNIGHT),\n  chainblade: CHAINBLADE,')

# Procedural, actually articulated weapon: compact -> 7 separated blade plates attached by links.
rep('src/game/model.ts', '  private gripL: THREE.Object3D | null = null;', '''  private gripL: THREE.Object3D | null = null;
  /** KAIZEN_CHAINBLADE_V1 — animated linked sword, independent of Garrick's weapon. */
  private chainLinks: THREE.Group[] = [];
  private chainBridges: THREE.Group[] = [];
  private chainLengthBlend = 0;
  chainFuryT = 0;
  chainExtended = false;''')
if 'case "glaive": this.buildGlaive(); break;' in patched['src/game/model.ts']:
    rep('src/game/model.ts', '      case "glaive": this.buildGlaive(); break;',
        '      case "glaive": this.buildGlaive(); break;\n      case "chainblade": this.buildChainblade(); break;')
else:
    rep('src/game/model.ts', '      case "sickle": this.buildSickles(); break;',
        '      case "sickle": this.buildSickles(); break;\n      case "chainblade": this.buildChainblade(); break;')
rep('src/game/model.ts', '  private buildSword() {', '''  /** KAIZEN_CHAINBLADE_V1: metal plates connected into one unfolding blade. */
  private buildChainblade() {
    const mount = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    mesh(mount, cyl(0.042, 0.046, 0.58, 12), this.tn("#28252d"), [0, 0.02, 0]);
    for (const y of [-0.22, -0.11, 0.09, 0.18])
      mesh(mount, torus(0.043, 0.054), this.tn(this.look.trim), [0, y, 0], [PI / 2, 0, 0], [1, 0.45, 1]);
    mesh(mount, box(0.22, 0.055, 0.065), this.metal(), [0, 0.28, 0]);
    mesh(mount, sphere(0.036, 12), this.gem(), [0, 0.285, 0.06]);
    const steel = this.steel();
    const dark = this.tn("#38343d");
    for (let i = 0; i < 7; i++) {
      const unit = pivot(mount, [0, 0.43 + i * 0.165, 0]);
      // Sharpened diamond plate (not a fat round cylinder).
      const shape = new THREE.Shape();
      const half = 0.108 - i * 0.008;
      shape.moveTo(0, -0.095);
      shape.lineTo(half * 0.7, -0.07);
      shape.lineTo(half, 0.016);
      shape.lineTo(half * 0.72, 0.07);
      shape.lineTo(0, 0.113);
      shape.lineTo(-half * 0.72, 0.07);
      shape.lineTo(-half, 0.016);
      shape.lineTo(-half * 0.7, -0.07);
      shape.closePath();
      const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.016, bevelEnabled: true, bevelThickness: 0.004, bevelSize: 0.003, bevelSegments: 1 });
      geo.translate(0, 0, -0.008);
      mesh(unit, geo, steel);
      mesh(unit, box(0.018, 0.135, 0.019), this.glowMat, [0, 0.005, 0.014]);
      mesh(unit, sphere(0.026, 10), dark, [0, -0.071, 0]);
      mesh(unit, sphere(0.015, 10), this.gem(), [0, -0.071, 0.028]);
      this.chainLinks.push(unit);
      if (i > 0) {
        const bridge = pivot(mount, [0, 0.43 + (i - 0.5) * 0.165, 0]);
        mesh(bridge, cyl(0.021, 0.021, 1, 8), dark);
        mesh(bridge, cyl(0.008, 0.008, 1, 6), this.glowMat);
        this.chainBridges.push(bridge);
      }
    }
    // Tip dynamically tracks the final physical plate in blend(); effects follow it too.
    this.bladeBase = pivot(mount, [0, 0.43, 0]);
    this.bladeTip = pivot(mount, [0, 1.55, 0]);
    mesh(this.chainLinks[6], new THREE.ConeGeometry(0.045, 0.16, 5), this.steel(), [0, 0.17, 0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = mount;
    this.gripL = pivot(mount, [0, -0.1, 0]);
  }

  private updateChainblade(dt: number) {
    if (!this.chainLinks.length) return;
    const dest = this.chainExtended ? 1 : this.chainFuryT > 0 ? 0.46 : 0;
    this.chainLengthBlend += (dest - this.chainLengthBlend) * (1 - Math.exp(-17 * dt));
    const amount = this.chainLengthBlend;
    const coords: THREE.Vector3[] = [];
    for (let i = 0; i < this.chainLinks.length; i++) {
      const k = i / 6;
      const p = new THREE.Vector3(
        Math.sin(this.t * 13 - i * 0.65) * 0.14 * amount * k,
        0.43 + i * (0.165 + 0.17 * amount),
        Math.cos(this.t * 11 - i * 0.8) * 0.11 * amount * k);
      coords.push(p);
      this.chainLinks[i].position.copy(p);
      this.chainLinks[i].rotation.z = amount * 0.22 * Math.sin(this.t * 12 - i * 0.65);
      this.chainLinks[i].rotation.x = amount * 0.16 * Math.cos(this.t * 10 - i * 0.7);
    }
    const up = new THREE.Vector3(0, 1, 0);
    for (let i = 1; i < coords.length; i++) {
      const d = coords[i].clone().sub(coords[i - 1]);
      const bridge = this.chainBridges[i - 1];
      bridge.position.copy(coords[i]).add(coords[i - 1]).multiplyScalar(0.5);
      bridge.quaternion.setFromUnitVectors(up, d.clone().normalize());
      bridge.scale.set(1, Math.max(0.04, d.length()), 1);
    }
    this.bladeTip.position.copy(coords[6]).add(new THREE.Vector3(0, 0.23, 0));
  }

  private buildSword() {''')
rep('src/game/model.ts', '    if (this.bowPivot) this.updateBow();', '    if (this.bowPivot) this.updateBow();\n    if (this.kit === "chainblade") this.updateChainblade(dt);')
if 'this.vrmRig.style = this.kit === "glaive" ? "storm" :' in patched['src/game/model.ts']:
    rep('src/game/model.ts', '    this.vrmRig.style = this.kit === "glaive" ? "storm" :',
        '    this.vrmRig.style = this.kit === "chainblade" ? "chainblade" : this.kit === "glaive" ? "storm" :')
else:
    rep('src/game/model.ts', '    this.vrmRig.style = this.kit === "sickle" ? "feral" :',
        '    this.vrmRig.style = this.kit === "chainblade" ? "chainblade" : this.kit === "sickle" ? "feral" :')
if 'this.vrmRig.followArm = this.kit === "glaive" ? 0.24 :' in patched['src/game/model.ts']:
    rep('src/game/model.ts', '    this.vrmRig.followArm = this.kit === "glaive" ? 0.24 :',
        '    this.vrmRig.followArm = this.kit === "chainblade" ? 0.22 : this.kit === "glaive" ? 0.24 :')
else:
    rep('src/game/model.ts', '    this.vrmRig.followArm = this.kit === "sickle" ? 0.18 :',
        '    this.vrmRig.followArm = this.kit === "chainblade" ? 0.22 : this.kit === "sickle" ? 0.18 :')
if 'this.vrmRig.bladed = this.kit === "glaive" ? 0.4 : 1;' in patched['src/game/model.ts']:
    rep('src/game/model.ts', '    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = this.kit === "glaive" ? 0.4 : 1; }',
        '    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = this.kit === "chainblade" ? 0.58 : this.kit === "glaive" ? 0.4 : 1; }')
else:
    rep('src/game/model.ts', '    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = 1; }',
        '    if (this.gripL) { this.vrmRig.gripL = this.gripL; this.vrmRig.bladed = this.kit === "chainblade" ? 0.58 : 1; }')

# Gently braced movement, unlike Garrick's former weird staggered walk.
rep('src/game/vrm.ts', '  heavy: { stance: D(14),', '''  chainblade: { stance: D(9), toeOut: D(9), knee: D(12), drop: 0.035, lean: D(5), chin: D(3), shoulderUp: D(2), elbowOut: D(8),
    hipSway: 0.009, hipRoll: D(0.8), contra: D(0.8), relaxKnee: D(4), headTilt: D(0.5), headYaw: D(4),
    breath: 0.55, armSwing: D(10), walkRoll: D(1.2), walkYaw: D(2.4) },
  heavy: { stance: D(14),''')

# Timers + client replication. Keep Zarek's last-field clashMomentum protocol intact.
rep('src/game/fighter.ts', '  bloodlust = 0;', '''  chainFuryT = 0; // KAIZEN_CHAINBLADE_V1: 5s Unbound Drive, host-synced.
  bloodlust = 0;''')
rep('src/game/fighter.ts', '    this.rageT = Math.max(this.rageT - dt, 0);',
    '    this.rageT = Math.max(this.rageT - dt, 0);\n    this.chainFuryT = Math.max(this.chainFuryT - dt, 0);')
rep('src/game/fighter.ts', '    if (this.kit === "sickle" && this.bloodFestivalT > 0 && /^l\\d+$/.test(id)) this.atkPower *= 1.35;',
'''    if (this.kit === "sickle" && this.bloodFestivalT > 0 && /^l\\d+$/.test(id)) this.atkPower *= 1.35;
    // Unbound Drive expands BASIC reach but does not bypass blocks, parries, or clashes.''')
rep('src/game/fighter.ts', '    if (this.kit === "knuckles" && this.atk?.name === "Meteor Fist") this.knock = 0;',
'''    if (this.kit === "knuckles" && this.atk?.name === "Meteor Fist") this.knock = 0;
    if (this.kit === "chainblade" && this.chainFuryT > 0 && /^l\\d+$/.test(id))
      this.atk = { ...this.atk, reach: this.atk.reach + 0.32, guard: this.atk.guard * 1.12 };''')
# Three alternating hit poses, timed to X's actual hits.
if '        if (a?.style === "iron_tempest") {' in patched['src/game/fighter.ts']:
    rep('src/game/fighter.ts', '        if (a?.style === "iron_tempest") {', '''        if (a?.style === "chain_carousel") {
          const elapsed = this.stateT - a.wind;
          if (elapsed < 0) { p = "cbx_w"; sp = 17; }
          else if (elapsed < 0.19) { p = "cbx1_s"; sp = 38; }
          else if (elapsed < 0.40) { p = "cbx2_s"; sp = 42; }
          else { p = "cbx3_s"; sp = 40; }
          break;
        }
        if (a?.style === "iron_tempest") {''')
else:
    rep('src/game/fighter.ts', '        if (this.atkPhase === 0) { p = a!.pose_w; sp = 22; }', '''        if (a?.style === "chain_carousel") {
          const elapsed = this.stateT - a.wind;
          if (elapsed < 0) { p = "cbx_w"; sp = 17; }
          else if (elapsed < 0.19) { p = "cbx1_s"; sp = 38; }
          else if (elapsed < 0.40) { p = "cbx2_s"; sp = 42; }
          else { p = "cbx3_s"; sp = 40; }
          break;
        }
        if (this.atkPhase === 0) { p = a!.pose_w; sp = 22; }''')
# The host update and client puppet both need the same visual state.
anchor = '    this.model.bloodFestivalT = this.kit === "sickle" ? this.bloodFestivalT : 0;'
if patched['src/game/fighter.ts'].count(anchor) != 2:
    raise RuntimeError('Expected two Blood Festival visual update locations in fighter.ts')
patched['src/game/fighter.ts'] = patched['src/game/fighter.ts'].replace(anchor, '''    this.model.bloodFestivalT = this.kit === "sickle" ? this.bloodFestivalT : 0;
    this.model.chainFuryT = this.kit === "chainblade" ? this.chainFuryT : 0;
    this.model.chainExtended = this.kit === "chainblade" && (this.chainFuryT > 0 ||
      ["cbz_w", "cbz_s", "cbx_w", "cbx1_s", "cbx2_s", "cbx3_s", "cbh_w", "cbh_s", "cbv_w", "cbv_s"].includes(this.poseName));''')
if '    this.guard = this.maxGuard;\n    this.clashMomentum = 0;' in patched['src/game/fighter.ts']:
    rep('src/game/fighter.ts', '    this.guard = this.maxGuard;\n    this.clashMomentum = 0;',
        '    this.guard = this.maxGuard;\n    this.chainFuryT = 0;\n    this.clashMomentum = 0;')
    anchor = '    this.clashMomentum = 0;\n    this.bloodlust = 0;'
    if patched['src/game/fighter.ts'].count(anchor) == 1:
        rep('src/game/fighter.ts', anchor,
            '    this.clashMomentum = 0; this.chainFuryT = 0;\n    this.bloodlust = 0;')
else:
    rep('src/game/fighter.ts', '    this.guard = this.maxGuard;\n    this.bloodlust = 0;',
        '    this.guard = this.maxGuard;\n    this.chainFuryT = 0;\n    this.bloodlust = 0;')
if 'this.clashMomentum];' in patched['src/game/fighter.ts']:
    rep('src/game/fighter.ts', 'this.clashMomentum];', '+this.chainFuryT.toFixed(2), this.clashMomentum];')
    rep('src/game/fighter.ts', 'this.clashMomentum = s[s.length - 1] ?? 0;',
        'this.clashMomentum = s[s.length - 1] ?? 0; this.chainFuryT = s.length >= 34 ? (s[s.length - 2] ?? 0) : 0;')
else:
    if '+this.bladeSwingYaw.toFixed(3)];' in patched['src/game/fighter.ts']:
        rep('src/game/fighter.ts', '+this.bladeSwingYaw.toFixed(3)];',
            '+this.bladeSwingYaw.toFixed(3), +this.chainFuryT.toFixed(2)];')
        ix = 32
    else:
        rep('src/game/fighter.ts', '+this.bloodFestivalT.toFixed(2)];',
            '+this.bloodFestivalT.toFixed(2), +this.chainFuryT.toFixed(2)];')
        ix = 29
    rep('src/game/fighter.ts', 'this.bloodFestivalT = s[28] ?? 0;',
        'this.bloodFestivalT = s[28] ?? 0; this.chainFuryT = s[' + str(ix) + '] ?? 0;')

# Attack logic. No auto-hit: every swipe delegates to the standard melee hit/clash resolver.
rep('src/game/game.ts', '    switch (a.type) {', '''    if (f.kit === "chainblade") {
      if (a.style === "chain_unbound") {
        f.chainFuryT = 5;
        this.fxp("flash", f.chest(), "#ff5d69", 0.62, 0.21, 0.9);
        this.fxp("sparks", f.chest(), "#ff7f83", 38, 6);
        this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.9, 0)), "UNBOUND DRIVE", "#ffb2b2", 1);
      }
      if (a.style === "chain_carousel") { this.chainbladeCarousel(f, a); return; }
      if (a.style === "chain_hook" || a.style === "chain_recall") {
        const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
        this.fxp("slashes", p, "#ff6274");
        this.fxp("sparks", p, "#ff95a0", 24, 6);
        this.melee(f, a);
        return;
      }
      if (a.type === "melee") {
        const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
        this.fxp("flash", p, "#ff6575", a.heavy ? 0.42 : 0.22, 0.12, 0.7);
        this.fxp("sparks", p, "#ffb4b4", a.heavy ? 20 : 10, 4);
      }
    }
    switch (a.type) {''')
rep('src/game/game.ts', '  private melee(f: Fighter, a: Attack) {', '''  /** KAIZEN_CHAINBLADE_V1: three independent, interruptible chain swipes. */
  private chainbladeCarousel(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    for (let i = 0; i < 3; i++) this.later(i * 0.22, () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      const hit: Attack = { ...a, dmg: [65, 77, 98][i], guard: [17, 20, 28][i],
        knock: i === 2 ? 3.8 : 0.8, stun: i === 2 ? 0.39 : 0.19,
        reach: [2.7, 2.85, 3.05][i] };
      f.poseOverride = ["cbx1_s", "cbx2_s", "cbx3_s"][i];
      const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", p, i === 1 ? "#ffb4b4" : "#f54f66");
      this.fxp("sparks", p, "#ff8b91", 19 + i * 6, 5);
      this.melee(f, hit);
    });
  }

  private melee(f: Fighter, a: Attack) {''')
rep('src/game/game.ts', '      const result = this.applyHit(f, d, a, f.atkPower, hitPos, dir, false);', '''      const result = this.applyHit(f, d, a, f.atkPower, hitPos, dir, false);
      if (f.kit === "chainblade" && a.style === "chain_hook" &&
          (result === "hit" || result === "crit") && d instanceof Fighter) {
        // Pull only after a genuine HP hit; guard/parry/clash keeps its normal counterplay.
        const toward = f.root.position.clone().sub(d.root.position).setY(0);
        const amount = Math.max(0, Math.min(0.90, toward.length() - 1.35));
        if (amount > 0 && toward.lengthSq() > 1e-5) {
          const move = toward.normalize().multiplyScalar(amount);
          const dest = d.root.position.clone().add(move);
          if (d.stage) {
            dest.x = Math.max(d.stage.blast.l + 1, Math.min(d.stage.blast.r - 1, dest.x));
          } else {
            const flat = Math.hypot(dest.x, dest.z);
            if (flat > d.arenaRadius) { dest.x *= d.arenaRadius / flat; dest.z *= d.arenaRadius / flat; }
          }
          d.root.position.copy(dest);
          this.fxp("sparks", d.chest(), "#ff7885", 22, 5);
        }
      }''')
rep('src/ui/Select.tsx', '  greatsword: "Tap: 3 heavy cleaves',
    '  chainblade: "Tap: 4 close sword cuts  -  Hold: Chainbreaker extended lash  -  Z: Chain Snare pull  -  X: Rending Orbit  -  C: Unbound Drive (5s)  -  V: Razor Recall",\n  greatsword: "Tap: 3 heavy cleaves')

# All checks passed: backups and edits only now.
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
for path in FILES:
    if patched[path] == original[path]:
        continue
    file = ROOT / path
    backup = file.with_name(file.name + f'.kaizen-backup-{stamp}')
    backup.write_text(original[path], encoding='utf-8')
    file.write_text(patched[path], encoding='utf-8')
    print('PATCH', path)
print('\nDONE: Kaizen installed with temporary garrick.vrm, custom segmented chainblade and combat kit.')
print('Test with: npx tsc --noEmit && npm run dev')
print('For signed-in shop purchases, run the Kaizen SQL migration separately.')
