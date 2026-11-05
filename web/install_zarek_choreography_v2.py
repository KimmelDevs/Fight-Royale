#!/usr/bin/env python3
"""Zarek Storm Glaive v2: staff-informed choreography and responsive two-hand VRM motion.
Run from web/ after the original Zarek installer. Does not rebalance damage, cooldowns, or reach.
"""
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path.cwd()
TARGETS = ['src/game/kits.ts','src/game/fighter.ts','src/game/model.ts','src/game/vrm.ts']
if not (ROOT/'package.json').exists() or not (ROOT/'src/game/game.ts').exists():
    sys.exit('Run from your Fight-Royale/web folder beside package.json.')
original = {p: (ROOT/p).read_text(encoding='utf-8') for p in TARGETS}
if 'ZAREK_GLAIVE_CHOREO_V2' in original['src/game/model.ts']:
    print('Zarek choreography V2 already installed. No changes needed.')
    sys.exit(0)
if 'const GLAIVE: Record<string, Pose>' not in original['src/game/kits.ts']:
    sys.exit('Zarek V1 is not installed (GLAIVE poses missing). Install Zarek first.')
patched = dict(original)
def rep(p,old,new):
    n=patched[p].count(old)
    if n != 1:
        raise RuntimeError(f'Patch stopped safely: expected exactly one anchor in {p}, found {n}: {old[:75]!r}')
    patched[p]=patched[p].replace(old,new,1)

# 4 distinct weapons actions: straight tip stab, reverse-end diagonal cut,
# upward figure-eight, and a two-handed planted-pivot finisher. Only visual pose values.
k='src/game/kits.ts'
start=patched[k].index('const GLAIVE: Record<string, Pose> = {')
end=patched[k].index('\n};',start)+3
block=patched[k][start:end]
lines=block.splitlines(keepends=True)
values={
'  idle:': '  idle: P([0.02, -0.20, 0.02], [0, 0.20, 0], [-0.70, 0.12, -0.23], [-0.08, 0, 0.15], [-0.82, 0.46, 0.1], [0, 0, 0], [-0.22, 0, 0.05], [0.25, 0, -0.06], -0.045),\n',
'  gl1_w:': '  gl1_w: P([0.10, -0.44, -0.06], [0, 0.36, 0], [-1.14, -0.72, -0.30], [0.46, 0, 0], [-1.30, -0.31, 0.22], [0.20, 0, 0], [-0.38, 0, 0.07], [0.22, 0, -0.08], -0.09),\n',
'  gl1_s:': '  gl1_s: P([0.16, 0.22, 0.03], [0, -0.14, 0], [-1.36, 0.32, -0.12], [0.08, 0, 0], [-1.48, 0.20, 0.17], [0.02, 0, 0], [-0.40, 0, 0.06], [0.44, 0, -0.05], -0.10),\n',
'  gl2_w:': '  gl2_w: P([0.12, 0.60, 0.07], [0, -0.42, 0], [-1.54, 0.68, 0.20], [0.15, 0, 0], [-1.37, 0.84, 0.26], [0.06, 0, 0], [-0.12, 0, 0.11], [0.43, 0, -0.10], -0.10),\n',
'  gl2_s:': '  gl2_s: P([0.05, -0.66, -0.10], [0, 0.44, 0], [-1.00, -0.86, -0.37], [0.07, 0, 0], [-1.62, -0.38, -0.24], [0.18, 0, 0], [-0.39, 0, 0.10], [0.18, 0, -0.10], -0.14),\n',
'  gl3_w:': '  gl3_w: P([-0.18, -0.38, 0.12], [0, 0.30, 0], [-2.35, -0.78, 0.16], [0.44, 0, 0], [-2.05, -0.34, -0.16], [0.22, 0, 0], [-0.35, 0, 0.14], [0.29, 0, -0.07], -0.13),\n',
'  gl3_s:': '  gl3_s: P([0.04, 0.58, -0.12], [0, -0.42, 0], [-0.88, 0.62, 0.14], [0.08, 0, 0], [-1.05, 0.34, -0.22], [0.06, 0, 0], [-0.41, 0, 0.10], [0.43, 0, -0.07], -0.10),\n',
'  gl4_w:': '  gl4_w: P([0.12, 0.92, 0.12], [0, -0.63, 0], [-1.94, 1.05, 0.16], [0.58, 0, 0], [-1.86, 0.66, -0.10], [0.26, 0, 0], [-0.42, 0, 0.11], [0.39, 0, -0.11], -0.17),\n',
'  gl4_s:': '  gl4_s: P([0.24, -1.04, -0.08], [-0.14, 0.66, 0], [-1.22, -1.16, -0.12], [0.10, 0, 0], [-1.48, -0.86, 0.27], [0.12, 0, 0], [-0.58, 0, 0.08], [0.42, 0, -0.11], -0.16),\n',
}
seen=set(); newlines=[]
for line in lines:
    key=next((x for x in values if line.startswith(x)),None)
    if key:
        if key in seen: raise RuntimeError('duplicate GLAIVE pose')
        seen.add(key); newlines.append(values[key])
    else: newlines.append(line)
if seen != set(values):
    raise RuntimeError('Zarek V1 pose set changed; cannot patch safely: '+repr(set(values)-seen))
patched[k] = patched[k][:start]+''.join(newlines)+patched[k][end:]

# Drive the attack with visually different phase timing, not the generic paddle-like swing.
f='src/game/fighter.ts'
rep(f,'        if (a?.style === "cyclone_kick_v2") {', '''        // ZAREK_GLAIVE_CHOREO_V2: readable windup, fast weapon contact, controlled follow-through.
        if (this.kit === "glaive" && a?.type === "melee") {
          if (this.atkPhase === 0) { p = a.pose_w; sp = 23; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = 66; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.8) { p = a.pose_s; sp = 18; }
          else { p = "idle"; sp = 13; }
          break;
        }
        if (a?.style === "cyclone_kick_v2") {''')
anim_anchor = '    this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);\n    this.bowDraw(dt);'
if patched[f].count(anim_anchor) != 2:
    raise RuntimeError('Expected two fighter model.blend() sites (host and client puppet).')
patched[f] = patched[f].replace(anim_anchor, """    this.model.glaivePose = this.kit === "glaive" ? this.poseName : "idle";
    this.model.blend(this.poses[this.poseName] ?? this.poses.idle, dt, this.poseSpeed);
    this.bowDraw(dt);""")
# Distinct body turns sync with already-replicated bladeSwingYaw; stays purely visual.
rep(f, '''      ((this.kit === "greatsword") || (this.kit === "knight" && this.look.element === "light"));''', '''      ((this.kit === "greatsword") || (this.kit === "glaive") || (this.kit === "knight" && this.look.element === "light"));''')
rep(f, 'this.kit === "greatsword" ? 0.48 : 0.27', 'this.kit === "greatsword" ? 0.48 : this.kit === "glaive" ? (this.atkId === "l4" ? 0.44 : 0.29) : 0.27')

# Fast hand and weapon response: the existing two-hand rig damps every polearm swing like a huge sword.
v='src/game/vrm.ts'
rep(v, '  restSword = false;', '  restSword = false;\n  glaive = false; // ZAREK_GLAIVE_CHOREO_V2: quicker, agile polearm hand alignment')
rep(v, 'else this.swordQ.slerp(target, 1 - Math.exp(-(combat ? 11 : 6) * dt));',
'''else this.swordQ.slerp(target, 1 - Math.exp(-(this.glaive ? (combat ? 28 : 17) : (combat ? 11 : 6)) * dt));''')

# Model-level tilt transforms the actual blade and left-hand grip, not just an FX circle.
m='src/game/model.ts'
rep(m, '  private gripL: THREE.Object3D | null = null;', '''  private gripL: THREE.Object3D | null = null;
  private glaivePivot: THREE.Group | null = null;
  glaivePose = "idle"; // ZAREK_GLAIVE_CHOREO_V2: current attack key from the fighter''')
rep(m, '    const staff = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);',
'''    const staff = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    this.glaivePivot = staff;''')
rep(m, '    if (this.gripL) this.reachGrip();', '''    // Different actual polearm arcs: direct thrust, reverse-end slash, figure-eight rise,
    // and pivot cleave. All rotations are local to the weapon: one motion path for VRM and
    // procedural character, and the left-hand IK follows the same physical shaft.
    if (this.glaivePivot) {
      const angles: Record<string, [number, number, number]> = {
        idle: [PI / 2, 0, 0], block: [PI / 2, -0.17, -0.08],
        gl1_w: [1.48, -0.53, -0.16], gl1_s: [0.89, 0.21, 0.14],
        gl2_w: [1.80, 0.64, 0.35], gl2_s: [1.34, -0.83, -0.30],
        gl3_w: [2.17, -0.58, -0.16], gl3_s: [0.92, 0.78, 0.22],
        gl4_w: [1.44, 0.70, 0.50], gl4_s: [2.08, -0.73, -0.45],
        glh_w: [2.00, -0.50, 0.22], glh_s: [0.93, 0.68, -0.26],
        glz_w: [1.64, -0.46, -0.28], glz_s: [1.05, 0.70, 0.26],
        glx_w: [1.35, -0.36, 0.14], glc_w: [2.00, -0.58, -0.10],
        glc_s: [0.93, 0.72, 0.22],
      };
      const a = angles[this.glaivePose] ?? angles.idle;
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));
      const rate = this.glaivePose.endsWith("_s") ? 38 : 19;
      this.glaivePivot.quaternion.slerp(q, 1 - Math.exp(-rate * dt));
    }
    if (this.gripL) this.reachGrip();''')
# Narrow the blade silhouette so each end reads as a sharp polearm, not a paddle.
rep(m, '      outline.moveTo(-0.045, s * 0.72);\n      outline.lineTo(-0.093, s * 0.89);\n      outline.lineTo(-0.067, s * 1.10);\n      outline.lineTo(0, s * 1.31);\n      outline.lineTo(0.075, s * 1.10);\n      outline.lineTo(0.095, s * 0.89);\n      outline.lineTo(0.047, s * 0.72);', '      outline.moveTo(-0.026, s * 0.72);\n      outline.lineTo(-0.062, s * 0.91);\n      outline.lineTo(-0.042, s * 1.13);\n      outline.lineTo(0, s * 1.38);\n      outline.lineTo(0.042, s * 1.13);\n      outline.lineTo(0.062, s * 0.91);\n      outline.lineTo(0.026, s * 0.72);')
rep(m, '    this.bladeTip = pivot(staff, [0, 1.32, 0]);', '    this.bladeTip = pivot(staff, [0, 1.38, 0]);')
rep(m,'    this.vrmRig.staff = this.kit === "mage";', '''    this.vrmRig.staff = this.kit === "mage";
    this.vrmRig.glaive = this.kit === "glaive";''')

# Write only after all anchor checks pass.
backup_stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
for p in TARGETS:
    src=ROOT/p
    backup=src.with_name(src.name+f'.zarek-choreo-v2-backup-{backup_stamp}')
    backup.write_text(original[p],encoding='utf-8')
    src.write_text(patched[p],encoding='utf-8')
    print('PATCH',p)
print('DONE: Zarek choreography V2 installed. Backups created; no skill damage, reach or cooldown changed.')
