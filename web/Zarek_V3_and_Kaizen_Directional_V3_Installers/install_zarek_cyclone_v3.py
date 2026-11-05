#!/usr/bin/env python3
"""Zarek V3: Cyclone Fang / Serpent Wheel / Phantom Spiral / Infinite Crescent.
Run from web/ after Zarek V1; compatible with Zarek Choreography V2 and Kaizen.
No other character's attacks, movement or VRM files are replaced.
"""
from pathlib import Path
from datetime import datetime
import sys
ROOT = Path.cwd()
K='src/game/kits.ts'; F='src/game/fighter.ts'; G='src/game/game.ts'; M='src/game/model.ts'; U='src/ui/Select.tsx'; A='src/game/ai.ts'
FILES=[K,F,G,M,U,A]
if not (ROOT/'package.json').exists() or not (ROOT/G).exists():
    sys.exit('Run from your web folder (beside package.json).')
orig={p:(ROOT/p).read_text(encoding='utf-8') for p in FILES}
if 'ZAREK_CYCLONE_V3' in orig[K]:
    print('Zarek Cyclone V3 is already installed; nothing changed.')
    sys.exit(0)
if 'function glaive(): Record<string, Attack>' not in orig[K] or 'private stormGlaiveSwing' not in orig[G]:
    sys.exit('Zarek V1 is not installed, or game.ts differs from the supported versions. No files changed.')
if 'ZAREK_GLAIVE_CHOREO_V2' not in orig[F] or 'glaivePivot' not in orig[M]:
    sys.exit('Install Zarek Choreography V2 first, then run this V3 installer. No files changed.')
patch=orig.copy()
def rep(p,old,new):
    n=patch[p].count(old)
    if n!=1: raise RuntimeError(f'Cannot safely update {p}: expected one anchor, found {n}: {old[:110]!r}')
    patch[p]=patch[p].replace(old,new,1)

# Replace Zarek's attack table only; no roster / other kit data altered.
start=patch[K].index('function glaive(): Record<string, Attack> {')
end=patch[K].index('\nfunction sickle()',start)
kit='''// ZAREK_CYCLONE_V3 — clash-focused acrobatic double-blade choreography.
function glaive(): Record<string, Attack> {
  return {
    l1: a({ name: "Cyclone Fang 1", wind: 0.11, active: 0.09, recover: 0.19, dmg: 58, guard: 16, reach: 2.25, lunge: 2.7, knock: 1.0, stun: 0.22, pose_w: "gl1_w", pose_s: "gl1_s", next: "l2" }),
    l2: a({ name: "Cyclone Fang 2", wind: 0.12, active: 0.09, recover: 0.18, dmg: 64, guard: 17, reach: 2.30, lunge: 2.8, knock: 1.0, stun: 0.23, pose_w: "gl2_w", pose_s: "gl2_s", next: "l3" }),
    l3: a({ name: "Cyclone Fang 3", wind: 0.10, active: 0.10, recover: 0.20, dmg: 69, guard: 18, reach: 2.28, lunge: 2.7, knock: 1.2, stun: 0.24, pose_w: "gl3_w", pose_s: "gl3_s", next: "l4" }),
    l4: a({ name: "Cyclone Fang 4", wind: 0.17, active: 0.11, recover: 0.23, dmg: 74, guard: 20, reach: 2.35, lunge: 2.4, knock: 1.6, stun: 0.27, pose_w: "gl4_w", pose_s: "gl4_s", next: "l5" }),
    l5: a({ name: "Cyclone Fang Finisher", desc: "Overhead turning slash. Hold the fifth attack to extend it into three more rotations.",
      wind: 0.17, active: 0.56, recover: 0.33, dmg: 104, guard: 29, reach: 2.4, lunge: 1.7, knock: 3.5, stun: 0.38,
      style: "glaive_cyclone", pose_w: "gl5_w", pose_s: "gl5_s" }),
    heavy: a({ name: "Split Current", wind: 0.35, active: 0.14, recover: 0.55, dmg: 165, guard: 48, reach: 2.6, lunge: 2.5, knock: 5, stun: 0.52, heavy: true, pose_w: "glh_w", pose_s: "glh_s" }),
    z: a({ name: "Serpent Wheel", desc: "Five revolving blade passes while stepping forward. Cannot be parried, but can be blocked or clashed. Dash-cancel or Space+Attack launcher-cancel.",
      cd: 8, wind: 0.14, active: 1.08, recover: 0.40, dmg: 33, guard: 11, reach: 2.15, lunge: 3.1, knock: 0.5, stun: 0.12,
      no_parry: true, style: "glaive_serpent", pose_w: "glz_w", pose_s: "glz_s" }),
    x: a({ name: "Phantom Spiral", desc: "Slide through the target, cutting once on approach and once after a 180-degree reverse strike. Can be blocked, parried and clashed.",
      cd: 9, wind: 0.13, active: 0.43, recover: 0.39, dmg: 85, guard: 24, reach: 2.4, lunge: 1.4, knock: 2.0, stun: 0.27,
      style: "glaive_phantom", pose_w: "glx_w", pose_s: "glx_turn" }),
    c: a({ name: "Infinite Crescent", desc: "Seven accelerating crescent cuts, an upward launcher, then an aerial cross-slash. A confirmed finisher hit triggers cinematic sparks and brief hit-stop.",
      cd: 20, wind: 0.30, active: 1.78, recover: 0.70, dmg: 44, guard: 15, reach: 2.35, lunge: 1.2,
      knock: 0.6, stun: 0.21, heavy: false, style: "glaive_infinite", pose_w: "glc_w", pose_s: "glc_s" }),
  };
}
'''
patch[K]=patch[K][:start]+kit+patch[K][end:]
# add three new poses using the established two-handed rig and Nyx VRM.
anchor='  glh_w: P('
pos=patch[K].index(anchor,patch[K].index('const GLAIVE: Record<string, Pose> = {'))
patch[K]=patch[K][:pos]+'''  gl5_w: P([-0.12, 0.76, -0.06], [-0.06, -0.52, 0], [-2.40, 0.62, -0.22], [0.35, 0, 0], [-2.18, 0.34, 0.16], [0.20, 0, 0], [-0.54, 0, 0.1], [0.48, 0, -0.1], -0.19),
  gl5_s: P([0.29, -0.84, 0.04], [-0.13, 0.57, 0], [-1.18, -1.18, -0.17], [0.18, 0, 0], [-1.46, -0.74, 0.21], [0.13, 0, 0], [-0.62, 0, 0.11], [0.40, 0, -0.1], -0.17),
  glx_turn: P([0.32, 0.88, 0.06], [-0.18, -0.67, 0], [-1.61, 1.07, 0.12], [0.20, 0, 0], [-1.87, 0.77, -0.17], [0.12, 0, 0], [-0.62, 0, 0.08], [0.48, 0, -0.1], -0.16),
  glc_launch: P([-0.27, -0.48, 0.06], [0.12, 0.27, 0], [-2.17, -0.42, -0.06], [0.24, 0, 0], [-1.99, -0.52, 0.11], [0.16, 0, 0], [-0.32, 0, 0.13], [0.31, 0, -0.09], -0.10),
  glc_finish: P([-0.26, 0.77, -0.05], [0.11, -0.52, 0], [-1.54, 0.85, -0.12], [0.22, 0, 0], [-1.79, 0.61, 0.23], [0.16, 0, 0], [-0.97, 0, 0.14], [0.18, 0, -0.09], -0.19),
'''+patch[K][pos:]

# Fifth basic can be started by holding down the final click after the 4th strike.
# Prevent the usual charge-heavy path from swallowing the held fifth hit.
rep(F,'    if (pressed) { this.holding = true; this.holdT = 0; }', '''    if (pressed && this.kit === "glaive" && this.state === S.ATTACK &&
        this.atkId === "l4" && this.atk?.next === "l5") this.buffered = true;
    if (pressed) { this.holding = true; this.holdT = 0; }''')
rep(F,'(this.state === S.IDLE || this.state === S.BLOCK)) {\n        this.holding = false;\n        this.airStartT = 99;', '''(this.state === S.IDLE || this.state === S.BLOCK ||
           (this.kit === "glaive" && this.state === S.ATTACK &&
            this.atk?.style === "glaive_serpent" && this.atkPhase === 1))) {
        this.holding = false;
        this.airStartT = 99;''')
# Different timed poses make the turns visible on the character, not merely FX circles.
rep(F,'        // ZAREK_GLAIVE_CHOREO_V2: readable windup, fast weapon contact, controlled follow-through.', '''        // ZAREK_CYCLONE_V3: true successive poses for serpent, slide reversal and ultimate.
        if (this.kit === "glaive" && a?.style === "glaive_serpent") {
          const elapsed = this.stateT - a.wind;
          if (elapsed < 0) { p = "glz_w"; sp = 27; }
          else { p = ["glz_s", "gl3_s", "gl2_s", "gl4_s", "glz_s"][Math.min(4, Math.floor(elapsed / 0.21))]; sp = 43; }
          break;
        }
        if (this.kit === "glaive" && a?.style === "glaive_phantom") {
          p = this.stateT < a.wind ? "glx_w" : this.stateT < a.wind + 0.19 ? "gl2_s" : "glx_turn"; sp = 46;
          break;
        }
        if (this.kit === "glaive" && a?.style === "glaive_infinite") {
          const elapsed = this.stateT - a.wind;
          p = elapsed < 0 ? "glc_w" : elapsed < 1.43 ? ["gl1_s", "gl2_s", "gl3_s", "gl4_s", "gl2_s", "gl3_s", "glc_launch"][Math.min(6, Math.floor(elapsed / 0.215))] : "glc_finish";
          sp = elapsed < 0 ? 22 : 55;
          break;
        }
        // ZAREK_GLAIVE_CHOREO_V2: readable windup, fast weapon contact, controlled follow-through.''')
# Reuse previous per-pose actual glaive rotations, add the new poses, and use
# weapon-space rotation for the looping attacks (not a frozen paddle).
rep(M,'        glh_w: [2.00, -0.50, 0.22], glh_s: [0.93, 0.68, -0.26],', '''        gl5_w: [2.12, 0.53, 0.32], gl5_s: [1.18, -0.97, -0.42],
        glx_turn: [1.95, -0.90, -0.33], glc_launch: [2.28, -0.32, -0.20], glc_finish: [0.85, 0.90, 0.35],
        glh_w: [2.00, -0.50, 0.22], glh_s: [0.93, 0.68, -0.26],''')
rep(M,'      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));', '''      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));
      // Live figure-eight spin around the weapon shaft (kept local so both hands follow).
      if (this.glaivePose === "glz_s" || this.glaivePose === "gl3_s" ||
          this.glaivePose === "glc_launch") {
        const roll = Math.sin(this.t * 19) * 0.38;
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), roll));
      }''')
# Game: replace V1 multi-hit handler, preserving the normal clash engine.
start=patch[G].index('  /** ZAREK_STORM_V1: separate, weapon-driven attacks; each can clash, block, or be parried. */')
end=patch[G].index('  /** KAIZEN_CHAINBLADE_V1:',start) if '  /** KAIZEN_CHAINBLADE_V1:' in patch[G][start:] else patch[G].index('  private melee(f: Fighter, a: Attack)', start)
handler='''  /** ZAREK_CYCLONE_V3: authoritative phased melee; blocks/parries/clashes use normal combat. */
  private stormGlaiveSwing(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    const alive = () => round === this.round && !f.isDown() && f.state === S.ATTACK && f.swingSerial === serial;
    const at = (i: number, part: Attack, pose: string) => {
      if (!alive()) return false;
      f.poseOverride = pose;
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", tip, f.look.glow);
      this.fxp("sparks", tip, i % 2 ? "#a5eeff" : "#4589ff", 18 + i * 4, 5);
      this.fxp("flash", tip, f.look.glow, 0.25 + i * 0.025, 0.11, 0.7);
      return this.melee(f, part); // true only when HP damage is dealt, not on block/parry.
    };
    if (a.style === "glaive_cyclone") {
      // The fifth tap is one overhead slash; holding the final click while it starts
      // adds three blade turns. A released click never triggers the extra hits.
      const extended = f.intent.attack;
      if (!extended) { at(0, a, "gl5_s"); return; }
      for (let i = 0; i < 4; i++) this.later(i * 0.13, () => {
        const part: Attack = { ...a, dmg: [38, 41, 42, 68][i], guard: [11, 11, 12, 20][i],
          knock: i === 3 ? 3.5 : 0.4, stun: i === 3 ? 0.38 : 0.12 };
        at(i, part, ["gl5_s", "gl2_s", "gl3_s", "gl5_s"][i]);
      });
      return;
    }
    if (a.style === "glaive_serpent") {
      // Five real damaging passes, one weapon-contact check per turn.
      for (let i = 0; i < 5; i++) this.later(i * 0.21, () => {
        const part: Attack = { ...a, dmg: i === 4 ? 45 : 33, guard: i === 4 ? 17 : 11,
          knock: i === 4 ? 2.2 : 0.35, stun: i === 4 ? 0.27 : 0.10,
          no_parry: true }; // still blockable and clashable
        at(i, part, ["glz_s", "gl3_s", "gl2_s", "gl4_s", "glz_s"][i]);
      });
      return;
    }
    if (a.style === "glaive_phantom") {
      at(0, { ...a, dmg: 85, guard: 22 }, "gl2_s");
      const opponent = f.opponent;
      if (opponent && !opponent.isDown()) {
        const from = f.root.position.clone();
        const across = opponent.root.position.clone().sub(from).setY(0);
        const length = across.length();
        if (length > 0.2 && length < 4.6) {
          const dest = opponent.root.position.clone().addScaledVector(across.normalize(), 0.85);
          for (let n = 1; n <= 3; n++) this.later(n * 0.055, () => {
            if (!alive()) return;
            const p = from.clone().lerp(dest, n / 3); p.y = f.root.position.y;
            if (f.stage) f.root.position.x = Math.max(f.stage.blast.l + 1.5, Math.min(f.stage.blast.r - 1.5, p.x));
            else {
              const flat = Math.hypot(p.x, p.z);
              if (flat > f.arenaRadius - 0.3) p.multiplyScalar((f.arenaRadius - 0.3) / flat);
              f.root.position.set(p.x, f.root.position.y, p.z);
            }
            this.fxp("sparks", f.chest(), "#8ceaff", 6, 3);
            if (n === 3 && opponent && !opponent.isDown()) {
              const face = opponent.root.position.clone().sub(f.root.position).setY(0);
              if (f.stage) f.facing = Math.sign(face.x) || f.facing;
              else if (face.lengthSq() > 0.001) f.root.rotation.y = Math.atan2(face.x, face.z);
            }
          });
        }
      }
      this.later(0.23, () => at(1, { ...a, dmg: 115, guard: 32, knock: 3.4, stun: 0.40 }, "glx_turn"));
      return;
    }
    if (a.style === "glaive_infinite") {
      const empowered = f.clashMomentum >= 3;
      if (empowered) f.clashMomentum -= 3;
      let connected = false;
      for (let i = 0; i < 8; i++) {
        const elapsed = [0, .26, .49, .70, .89, 1.07, 1.24, 1.55][i];
        this.later(elapsed, () => {
          if (!alive()) return;
          const launch = i === 6, final = i === 7;
          const part: Attack = { ...a,
            dmg: final ? (empowered ? 170 : 140) : launch ? 68 : [44, 42, 45, 44, 47, 48][i],
            guard: final ? 46 : launch ? 25 : 13,
            knock: final ? 5.0 : launch ? 0.7 : 0.35,
            stun: final ? .55 : launch ? .4 : .17,
            reach: final ? 2.65 : 2.4,
            style: final ? "glaive_crescent_final" : launch ? "glaive_crescent_launch" : "glaive_infinite" };
          if (final && !connected) return; // no cinematic finish on missed/blocked starter
          if (launch && f.opponent && !f.opponent.isDown()) {
            // Follow upward with the target; this is NOT Gale's ground-smash.
            f.velY = Math.max(f.velY, 4.4); f.onGround = false;
          }
          if (final && !f.onGround) f.velY = Math.min(f.velY, -3.5); // aerial crosscut, not a ground slam
          const hit = at(i, part, final ? "glc_finish" : launch ? "glc_launch" :
            ["gl1_s", "gl2_s", "gl3_s", "gl4_s", "gl2_s", "gl3_s"][i]);
          if (hit) connected = true;
          if (final && hit) {
            this.fxp("lightning", f.chest(), "#9ceaff");
            this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.8, 0)), "INFINITE CRESCENT", "#e7f8ff", .85);
            this.add_trauma(.55);
            this.hitStop(.19, .35);
          }
        });
      }
    }
  }

'''
patch[G]=patch[G][:start]+handler+patch[G][end:]
rep(G,'if (f.kit === "glaive" && (a.style === "glaive_reversal" || a.style === "glaive_barrage" || a.style === "glaive_judgment")) {', '''if (f.kit === "glaive" && ["glaive_cyclone", "glaive_serpent", "glaive_phantom", "glaive_infinite"].includes(a.style)) {''')
# Return a meaningful confirmed contact flag to gate the finisher.
rep(G,'  private melee(f: Fighter, a: Attack) {\n    // AIR_COMBAT_V1:', '  private melee(f: Fighter, a: Attack): boolean {\n    let connected = false;\n    // AIR_COMBAT_V1:')
rep(G,'        this.clash(f, d, f.root.position.clone().addScaledVector(dir, Math.min(dist * 0.5, 0.8)).add(new THREE.Vector3(0, 1.15, 0)));\n        return;', '        this.clash(f, d, f.root.position.clone().addScaledVector(dir, Math.min(dist * 0.5, 0.8)).add(new THREE.Vector3(0, 1.15, 0)));\n        return false;')
rep(G,'      const result = this.applyHit(f, d, a, f.atkPower, hitPos, dir, false);', '''      const result = this.applyHit(f, d, a, f.atkPower, hitPos, dir, false);
      if (result === "hit" || result === "crit" || result === "ko") {
        connected = true;
        if (a.style === "glaive_crescent_launch" && d instanceof Fighter) {
          d.velY = Math.max(d.velY, d.stage ? 6.2 : 5.1);
          d.onGround = false;
        }
      }''')
rep(G,'      if (dist - 0.45 <= a.reach && (dist < 0.6 || to.normalize().dot(fwd) > 0.15)) this.detonate(t);\n    }\n  }\n\n  private fireProjectiles', '      if (dist - 0.45 <= a.reach && (dist < 0.6 || to.normalize().dot(fwd) > 0.15)) this.detonate(t);\n    }\n    return connected;\n  }\n\n  private fireProjectiles')
# Coincident strike vs strike remains a normal clash; fix the old double-momentum bonus.
rep(G,'const gain = f.atk?.style === "glaive_reversal" ? 2 : 1;', 'const gain = 1; // ZAREK_CYCLONE_V3: one genuine clash, one Momentum stack.')
rep(U,'  glaive: "Tap: 4-hit double-glaive combo  -  Hold: Split Current  -  Real clashes build Momentum (max 3)  -  Z: reversal  -  X: barrage  -  C: lightning finisher",', '''  glaive: "Tap: Cyclone Fang 5-hit combo  -  Hold the 5th hit: extra spins  -  Z: Serpent Wheel (no parry, dash/launcher cancel)  -  X: Phantom Spiral dash  -  C: Infinite Crescent  -  Real clashes build Momentum",''')
# An unparryable move is announced to CPU defense logic too (not a forced failed parry).
rep(A,'      if (festival) {', '      if (festival || o.atk?.no_parry) {')
# All changes validated before writing so failure cannot half-install the patch.
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
for p in FILES:
    if patch[p]!=orig[p]:
        path=ROOT/p
        path.with_name(path.name+f'.zarek-cyclone-v3-backup-{stamp}').write_text(orig[p],encoding='utf-8')
        path.write_text(patch[p],encoding='utf-8')
        print('PATCH',p)
print('DONE: Zarek Cyclone V3 installed. Nyx VRM unchanged; other characters preserved.')
