#!/usr/bin/env python3
"""Fight Royale — RENJI ECLIPSE V3.1 (upgrade existing Counter Fist V2).

Run from fight-royale/web:
  python install_renji_eclipse_v31.py --dry-run
  python install_renji_eclipse_v31.py
  npx tsc --noEmit -p .

Only changes Renji-related sections of roster/kits/model/game/fighter/presentation/ai.
- Corrected perpendicular-tonfa grips through both VRM palms, shaft aligned to forearm.
- Dark-element mechanical concealed forms: short chain, hook, guard ring, telescoping rod.
- Distinct 7 / 2 / 8-beat collision-checked Z/C/V choreography, directional counters.
- Violet ink-like VFX, readable parry catch/cross/redirect; keeps existing X/Read logic.
- Backups use .txt so TypeScript cannot mistake them for source files.
- In-memory preflight, --dry-run, staged writes, rollback and double-install guard.

This tool does NOT modify Aster's VRM, other fighter kits, or sound files.
Renji AI is updated to recognize renamed skills. The V2 STOCK icons are violet-tinted
only when their exact hashes match, so custom icons are untouched.
The per-beat pose already travels as poseName in the V2 snapshot (no network changes).
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import json
import base64
import hashlib
import io
import zipfile
import zlib
import os
import sys
import tempfile

MARK = 'RENJI_ECLIPSE_V31'
FILES = [
    'src/game/roster.ts', 'src/game/kits.ts', 'src/game/model.ts',
    'src/game/game.ts', 'src/game/fighter.ts', 'src/game/presentation.ts',
    'src/game/ai.ts',
]

class Patch:
    def __init__(self, data): self.d = data
    def one(self, path, old, new):
        n = self.d[path].count(old)
        if n != 1: raise RuntimeError(f'{path}: expected one source anchor, found {n}: {old[:130]!r}')
        self.d[path] = self.d[path].replace(old, new, 1)
    def before(self, path, anchor, body): self.one(path, anchor, body+anchor)
    def after(self, path, anchor, body): self.one(path, anchor, anchor+body)
    def span(self, path, start, end, body):
        t=self.d[path]
        if t.count(start)!=1 or t.count(end)!=1: raise RuntimeError(f'{path}: cannot uniquely find code region: {start[:80]}')
        a=t.index(start); b=t.index(end,a)
        self.d[path]=t[:a]+body+t[b:]



def patch_ai(p):
    f='src/game/ai.ts'
    # Skill names have subtitles in Eclipse V3.1. Match only the owned name prefix.
    p.one(f,'if (name === "Iron Reflection")', 'if (name.startsWith("Iron Reflection"))')
    p.one(f,'if (name === "Hundred Fangs")', 'if (name.startsWith("Hundred Fangs"))')
    p.one(f,'if (name === "Blindside Step")', 'if (name.startsWith("Blindside Step"))')
    p.one(f,'// RENJI_COUNTER_FIST_V2 — patient',
          '// RENJI_ECLIPSE_V31 — patient')

def patch_roster(p):
    f='src/game/roster.ts'
    p.one(f,
        'look: { name: "Renji", body: "m", vrm: "aster", kit: "tonfa", element: "physical",',
        'look: { name: "Renji", body: "m", vrm: "aster", kit: "tonfa", element: "dark",')
    p.one(f,
        'desc: "Perfectly reads attacks and unleashes directional tonfa counters. Iron Reflection automatically perfect-parries every incoming hit for 15 seconds.",',
        'desc: "Dark-element counter fighter. Concealed chain, hook, guard-ring and telescoping tonfas amplify close-range directional counters. Iron Reflection automatically perfect-parries for 15 seconds.",')
    # Only dark VFX and costumes — keep yellow hair and gold eyes.
    p.one(f,'cape: "#213D40", cape_bottom: "#315A60", glow: "#F9D76D", shield: "#1B3236", emblem: "#FFD75F" } },',
          'cape: "#171123", cape_bottom: "#34204E", glow: "#9452D8", shield: "#1B1530", emblem: "#C49BFF" } },')
    p.one(f,'// RENJI_COUNTER_FIST_V2 — temporary Aster male VRM, unique yellow-haired tonfa kit.',
          '// RENJI_ECLIPSE_V31 — yellow hair, Aster VRM placeholder, original dark tonfa transformations.')


def patch_kits(p):
    f='src/game/kits.ts'
    p.one(f, 'name: "Final Verdict: Eightfold", desc: "Eight timed tonfa, elbow and knee contacts. All eight use ordinary collision, guard and dodge checks.",',
          'name: "Final Verdict: Eightfold", desc: "Eight real close-range contacts with a mechanical black-iron staff extension, rotating guard-ring and retracting hooked tip; no teleport or phantom hit.",')
    p.one(f,'cd: 43, wind: 0.29, active: 1.40, recover: 0.64, dmg: 35, guard: 12, reach: 1.98,',
          'cd: 43, wind: 0.34, active: 1.72, recover: 0.68, dmg: 35, guard: 12, reach: 2.08,')
    p.one(f,'name:"Hundred Fangs",desc:"Six separately defendable tonfa and elbow strikes, ending in a rising knee.",cd:9,wind:.15,active:.93,recover:.42,dmg:26,guard:9,reach:1.90,lunge:2.7,knock:.4,stun:.11,style:"renji_hundred",',
          'name:"Hundred Fangs: Black Thread",desc:"Six close-range tonfa and elbow strikes, chain reveal on the fifth beat, then a rising knee (seven real contacts).",cd:9,wind:.18,active:1.02,recover:.45,dmg:25,guard:9,reach:1.98,lunge:2.5,knock:.4,stun:.11,style:"renji_hundred",')
    p.one(f,'name:"Blindside Step",desc:"Fast grounded pivot into two real close-range tonfa strikes. Not a teleport.",cd:12,wind:.15,active:.40,recover:.34,dmg:50,guard:17,reach:1.97,lunge:4.1,knock:1.3,stun:.19,style:"renji_blindside",',
          'name:"Blindside Step: Night Talon",desc:"A visible grounded sidestep, hooked left-tonfa trap and right elbow strike. Both contacts must be in true melee reach.",cd:12,wind:.18,active:.46,recover:.35,dmg:52,guard:18,reach:2.03,lunge:3.65,knock:1.3,stun:.19,style:"renji_blindside",')
    p.one(f,'name:"Iron Reflection",desc:"For 15 seconds, Guard is disabled but every incoming attack is automatically perfect-parried. Base 30s cooldown, reduced 5% per Read stack at activation.",',
          'name:"Iron Reflection: Eclipse Guard",desc:"For 15 seconds, Guard is disabled and every incoming attack is automatically perfect-parried; hidden tonfa rings deploy on contact. 30s base cooldown, minus 5% per Read stack.",')
    # V3 adds pose keys to the already existing pose table. No new public Pose type.
    pose_add = '''  // RENJI_ECLIPSE_V31 — staggered weapon beats; hands stay on short perpendicular grips.
  rnz1_s:K(P([.21,.25,-.04],[-.11,-.12,0],[-1.96,-.18,-.34],[.13,0,.02],[-1.41,-.14,.34],[.26,0,-.07],[-.45,-.08,.20],[.36,.11,-.19],-.20),.42,.34),
  rnz2_s:K(P([.25,-.36,.05],[-.11,.20,0],[-1.39,.24,-.35],[.28,0,-.08],[-2.04,.24,.31],[.11,0,.08],[-.50,-.12,.17],[.46,.08,-.15],-.22),.33,.44),
  rnz3_s:K(P([.28,.43,-.04],[-.14,-.23,0],[-1.65,.37,-.12],[.12,0,.06],[-1.40,-.30,.35],[.25,0,-.09],[-.63,-.08,.18],[.53,.10,-.22],-.24),.46,.40),
  rnz4_s:K(P([.28,-.50,.05],[-.12,.25,0],[-1.24,-.22,-.34],[.20,0,-.1],[-1.98,.35,.34],[.09,0,.08],[-.49,-.07,.16],[.51,.09,-.15],-.18),.48,.43),
  rnz5_s:K(P([.38,.33,-.11],[-.14,-.10,0],[-2.04,.52,-.32],[.22,0,.08],[-1.50,-.45,.29],[.33,0,-.12],[-.65,-.06,.20],[.51,.10,-.18],-.25),.55,.49),
  rnz6_s:K(P([.22,-.45,.04],[-.09,.30,0],[-1.22,.34,-.25],[.22,0,-.11],[-1.91,-.36,.39],[.20,0,.11],[-.47,-.09,.19],[.50,.08,-.19],-.17),.44,.40),
  rnz7_s:K(P([-.08,.23,-.04],[-.19,-.08,0],[-1.26,.30,-.28],[.26,0,.05],[-1.48,-.35,.39],[.26,0,-.04],[-.19,-.03,.18],[-1.40,.07,-.33],-.12),.25,.16),
  rnc1_s:K(P([.30,.66,-.12],[-.10,-.24,0],[-1.82,.42,-.38],[.25,0,.08],[-1.46,-.27,.34],[.20,0,-.10],[-.68,-.11,.20],[.51,.16,-.20],-.25),.53,.45),
  rnc2_s:K(P([.19,-.48,.05],[-.12,.23,0],[-2.04,-.13,-.29],[.16,0,.07],[-1.40,.20,.40],[.28,0,-.14],[-.50,-.07,.17],[.45,.11,-.22],-.18),.42,.46),
  rnv1_s:K(P([.28,.40,-.05],[-.12,-.19,0],[-2.00,.35,-.30],[.15,0,.07],[-1.36,-.21,.37],[.22,0,-.08],[-.61,-.07,.15],[.49,.11,-.18],-.24),.49,.44),
  rnv2_s:K(P([.24,-.47,.02],[-.10,.25,0],[-1.36,.33,-.31],[.21,0,-.13],[-1.97,.27,.34],[.13,0,.08],[-.47,-.10,.18],[.51,.09,-.14],-.20),.43,.50),
  rnv3_s:K(P([.33,.37,-.08],[-.12,-.12,0],[-1.92,.51,-.30],[.17,0,.09],[-1.51,-.43,.31],[.26,0,-.11],[-.68,-.12,.19],[.56,.13,-.18],-.24),.58,.45),
  rnv4_s:K(P([-.08,.18,-.02],[-.13,-.14,0],[-1.10,.22,-.33],[.25,0,.08],[-1.30,-.16,.38],[.26,0,-.10],[-.25,-.06,.19],[-1.34,.08,-.30],-.15),.31,.17),
  rnv5_s:K(P([.42,-.52,.07],[-.08,.29,0],[-2.12,.35,-.31],[.23,0,.10],[-1.86,-.28,.38],[.21,0,-.10],[-.65,-.07,.21],[.47,.12,-.18],-.26),.54,.53),
  rnv6_s:K(P([.35,.43,-.06],[-.16,-.16,0],[-1.58,.46,-.27],[.10,0,.10],[-1.43,-.33,.29],[.20,0,-.10],[-.73,-.07,.22],[.58,.10,-.17],-.27),.53,.52),
  rnv7_s:K(P([.48,-.33,.06],[-.13,.20,0],[-1.83,.42,-.23],[.19,0,.08],[-1.79,-.28,.29],[.23,0,-.08],[-.64,-.05,.16],[.57,.10,-.18],-.23),.56,.51),
  rnv8_s:K(P([.52,.39,-.05],[-.19,-.08,0],[-1.14,.49,-.36],[.13,0,.14],[-1.22,-.31,.35],[.21,0,-.13],[-.72,-.08,.15],[.65,.10,-.22],-.29),.64,.58),
  rn_counter_side:K(P([.20,.43,-.04],[-.10,-.20,0],[-1.76,.46,-.33],[.24,0,.11],[-1.42,-.28,.37],[.26,0,-.08],[-.60,-.08,.19],[.45,.09,-.18],-.23),.44,.47),
  rn_counter_over:K(P([.29,-.18,.03],[-.09,.11,0],[-2.20,.31,-.35],[.48,0,.22],[-2.10,-.25,.41],[.49,0,-.22],[-.45,-.08,.18],[.48,.10,-.18],-.26),.58,.55),
  rn_counter_low:K(P([-.04,.20,-.03],[-.10,-.12,0],[-1.24,.26,-.30],[.35,0,.07],[-1.48,-.32,.36],[.32,0,-.07],[-.15,-.03,.15],[-1.18,.07,-.32],-.12),.24,.18),
  rn_counter_thrust:K(P([.25,-.39,.06],[-.09,.20,0],[-1.65,.44,-.40],[.38,0,.12],[-1.90,-.33,.37],[.30,0,-.12],[-.55,-.08,.19],[.45,.10,-.18],-.23),.53,.46),
  rn_counter_projectile:K(P([.23,.21,-.02],[-.10,-.12,0],[-1.99,.42,-.34],[.45,0,.17],[-1.68,-.32,.39],[.46,0,-.16],[-.49,-.07,.16],[.43,.10,-.17],-.20),.48,.43),
  rn_insight_s:K(P([.48,.43,-.07],[-.19,-.12,0],[-1.15,.59,-.29],[.12,0,.15],[-1.28,-.49,.34],[.18,0,-.10],[-.74,-.12,.19],[.65,.14,-.23],-.29),.62,.57),
'''
    p.before(f,'  rnv_s:K(P(',pose_add)
    # Also fix the known V2 TS2448 issue if the user has not installed the separate K fix.
    t=p.d[f]
    if 'const K = (p: Pose, l: number, r: number): Pose' not in t:
        raise RuntimeError('kits.ts: original knee helper K missing')
    if t.index('const K = (p: Pose') > t.index('const RENJI_TONFA:'):
        helper='/** Adds knee bend to a pose. */\nconst K = (p: Pose, l: number, r: number): Pose => ({ ...p, knee: [l, r] });\n'
        p.one(f,helper,'')
        p.before(f,'const RENJI_TONFA: Record<string, Pose> = {',helper)


def patch_model(p):
    f='src/game/model.ts'
    p.after(f,'  private renjiTonfas: THREE.Group[] = [];\n', '''  // RENJI_ECLIPSE_V31 — all concealed parts remain attached to their proper tonfas.
  // Visual state derives from the already-replicated pose; no new net fields.
  private renjiMechanisms: { chain: THREE.Group; hook: THREE.Group;
    ring: THREE.Group; extend: THREE.Group; tip: THREE.Group }[] = [];
''')
    new_build='''  private buildRenjiTonfas() {
    // RENJI_ECLIPSE_V31. The SHORT perpendicular T-handle passes through the fist;
    // the long shaft runs UP the forearm, not forward like a baton. The VRM grips
    // this cross-handle instead of holding the shaft like a sword.
    for (let i=0;i<2;i++) {
      const hand = i===0 ? this.hand_r : this.hand_l;
      const sign = i===0 ? -1 : 1;
      const root = pivot(hand, [sign*0.012,-0.017,0.014]);
      // Traditional tonfa shaft: short striking nose below hand, long protective
      // section toward elbow. Metal caps are restrained for a readable silhouette.
      mesh(root, cyl(.027,.029,.53,12),this.tn("#292635"),[0,.145,-.105]);
      mesh(root, cyl(.030,.032,.15,12),this.tn("#575267"),[0,.385,-.105]);
      mesh(root, cyl(.032,.034,.07,12),this.tn("#7B7294"),[0,-.099,-.105]);
      // This cylinder crosses the PALM at z≈0. Its front end attaches to the long shaft.
      mesh(root,cyl(.030,.030,.235,12),this.tn("#24222D"),[0,-.015,-.008],[Math.PI/2,0,0]);
      mesh(root,cyl(.038,.039,.019,12),this.tn("#ACA1BD"),[0,-.015,.099],[Math.PI/2,0,0]);
      mesh(root,cyl(.037,.039,.02,12),this.tn("#ACA1BD"),[0,-.015,-.119],[Math.PI/2,0,0]);
      for(let j=0;j<4;j++) mesh(root,torus(.031,.038),this.tn("#55506D"),[0,.02+j*.038,-.105]);
      // Mechanical forms fold inside the LONG shaft and unfold from its far end.
      const chain=pivot(root,[0,.419,-.105]);
      for(let j=0;j<5;j++) mesh(chain,torus(.009,.019),this.tn("#A393B7"),[0,.029+j*.044,0],
        [j%2?Math.PI/2:0,0,0]);
      const hook=pivot(root,[0,.369,-.105]);
      mesh(hook,cyl(.002,.030,.15,9),this.tn("#8D83A8"),[sign*.07,.075,0],[0,0,-sign*.63]);
      mesh(hook,cyl(.001,.024,.095,9),this.tn("#C4B3ED"),[sign*.126,.154,0],[0,0,-sign*.92]);
      const ring=pivot(root,[0,.305,-.105]);
      mesh(ring,torus(.071,.086),this.tn("#ADA1C7"),[0,0,0],[Math.PI/2,0,0]);
      for (let j=0;j<4;j++) {
        const angle=j*Math.PI/2;
        mesh(ring,cyl(0,.024,.07,7),this.tn("#A090B2"),
          [Math.cos(angle)*.082,0,Math.sin(angle)*.082],[0,0,-angle]);
      }
      const extend=pivot(root,[0,.412,-.105]);
      mesh(extend,cyl(.018,.023,.34,10),this.tn("#B2A8C4"),[0,.17,0]);
      mesh(extend,cyl(0,.031,.08,9),this.tn("#E8D7FF"),[0,.378,0]);
      const tip=pivot(root,[0,.412,-.105]);
      chain.scale.setScalar(.001); hook.scale.setScalar(.001);
      ring.scale.setScalar(.001); extend.scale.y=.001;
      this.renjiTonfas.push(root);
      this.renjiMechanisms.push({chain,hook,ring,extend,tip});
    }
    this.bladeBase=this.renjiTonfas[0];
    this.bladeTip=this.renjiMechanisms[0].tip;
    this.castPoint=this.bladeTip;
    this.shieldNode=this.hand_l;
  }

  private updateRenjiTonfas(dt: number, pose: string) {
    if(this.renjiTonfas.length!==2 || this.renjiMechanisms.length!==2) return;
    // Timed reveal, contact, and retraction all ease from the *current* pose.
    const z=/^rnz[1-7]_s$/.test(pose) || pose==="rnz_s";
    const c=/^rnc[12]_s$/.test(pose) || pose==="rnc_s";
    const v=/^rnv[1-8]_s$/.test(pose) || pose==="rnv_s";
    const counter=/^rn_counter_/.test(pose) || pose.startsWith("rn_parry") || pose.startsWith("rn_cancel");
    const guard=pose==="block" || pose==="rnx_w" || pose==="rnx_s" || this.renjiParryT>.02;
    const chainWant=z && /rnz[4567]_s/.test(pose) ? 1 : 0;
    const hookWant=c || pose==="rn_counter_thrust" ? 1 : 0;
    const ringWant=guard || pose==="rn_counter_over" || (v && /rnv[357]_s/.test(pose)) ? 1 : 0;
    const extendWant=v && /rnv[678]_s/.test(pose) || pose==="rnh_s" ? 1 : 0;
    const k=1-Math.exp(-Math.max(0,Math.min(dt,.10))*24);
    const p=Math.min(1,this.renjiParryT/.4);
    const flash=Math.sin(Math.PI*p);
    for(let i=0;i<2;i++) {
      const s=i===0 ? -1:1, mechanism=this.renjiMechanisms[i], weapon=this.renjiTonfas[i];
      const sideChain=chainWant && i===0 ? 1:0;
      const sideHook=hookWant && i===1 ? 1:0;
      const sideExtend=extendWant && i===0 ? 1:0;
      const sideRing=ringWant ? 1:0;
      const scale=(g:THREE.Object3D,target:number)=>{
        const want=.001+Math.max(0,target)*.999;
        const next=THREE.MathUtils.lerp(g.scale.x,want,k);
        g.scale.setScalar(next);
      };
      scale(mechanism.chain,sideChain);
      scale(mechanism.hook,sideHook);
      scale(mechanism.ring,sideRing);
      mechanism.extend.scale.y=THREE.MathUtils.lerp(mechanism.extend.scale.y,.001+sideExtend*.999,k);
      // Tip tracks the extended shaft's REAL end, including interpolation and retraction.
      // The spear's visible tip cone is at y=.378 inside the scaled extend group.
      mechanism.tip.position.y=.412 + .378*mechanism.extend.scale.y;
      // Wrist snap without rotating the tonfa into a sword grip. Crossed guard
      // and chain flick keep the rod visually in front of the forearm.
      const zag=z && i===0 ? -.20 : c && i===1 ? .21 : 0;
      const twist=counter ? s*.31*flash : 0;
      weapon.rotation.z=THREE.MathUtils.damp(weapon.rotation.z,zag+twist,26,dt);
      weapon.rotation.x=THREE.MathUtils.damp(weapon.rotation.x,guard?-.14:0,24,dt);
      weapon.rotation.y=THREE.MathUtils.damp(weapon.rotation.y,guard?s*.12:0,22,dt);
    }
    // The hit FX follows the tonfa currently leading the contact, including
    // the off-hand hook and knee-follow-up; no invisible standalone hit source.
    const left = /^rn(z[246]|c1|v[2468]|2|4|_counter_thrust)/.test(pose);
    this.bladeTip=this.renjiMechanisms[left?1:0].tip;
    this.castPoint=this.bladeTip;
  }

'''
    p.span(f,'  private buildRenjiTonfas() {','  private buildKnuckles() {',new_build)
    old='''    // Brief wrist catch, elbow retraction and tonfa flick on successful parries.
    if (this.renjiTonfas.length === 2) {
      const snap = THREE.MathUtils.clamp(this.renjiParryT / 0.40,0,1);
      const flip = Math.sin((1-snap)*Math.PI);
      this.renjiTonfas[0].rotation.z = THREE.MathUtils.damp(this.renjiTonfas[0].rotation.z, -0.68*flip, 34, dt);
      this.renjiTonfas[1].rotation.z = THREE.MathUtils.damp(this.renjiTonfas[1].rotation.z, 0.68*flip, 34, dt);
      this.renjiTonfas[0].rotation.x = THREE.MathUtils.damp(this.renjiTonfas[0].rotation.x, 0.27*flip, 31, dt);
      this.renjiTonfas[1].rotation.x = THREE.MathUtils.damp(this.renjiTonfas[1].rotation.x, 0.27*flip, 31, dt);
    }
'''
    p.one(f,old,'    if (this.kit === "tonfa") this.updateRenjiTonfas(dt, actionPose);\n')
    p.one(f,'if (this.kit === "tonfa") { this.vrmRig.boxer = true; this.vrmRig.bladed = 0.70; this.vrmRig.style = "light"; }',
      '''if (this.kit === "tonfa") {
      this.vrmRig.boxer = true;
      this.vrmRig.bladed = 0.35; // squared close-guard, not two-handed sword stance
      this.vrmRig.style = "light";
      this.vrmRig.grip.left = true;  // V2 left fist was OPEN despite holding a tonfa
      this.vrmRig.grip.right = true; // both palms curl around perpendicular T-grips
    }''')


def patch_game(p):
    f='src/game/game.ts'
    new_multi='''  // RENJI_ECLIPSE_V31 — unequal contact beats, mechanical forms, real hit tests.
  private renjiMulti(f: Fighter, a: Attack) {
    const round=this.round, serial=f.swingSerial;
    const riposte=a.style==="renji_riposte", z=a.style==="renji_hundred";
    const c=a.style==="renji_blindside", v=a.style==="renji_eightfold";
    const beatFractions=riposte?[.17,.48,.85]:z?[.08,.19,.30,.43,.56,.73,.92]:
      c?[.32,.79]:v?[.08,.20,.32,.45,.57,.68,.82,.95]:[.45];
    const routes=[
      ["rn_counter_side","rn3_s","rn5_s"],
      ["rn_counter_over","rn4_s","rn5_s"],
      ["rn_counter_low","rn1_s","rn5_s"],
      ["rn_counter_thrust","rn3_s","rn2_s"],
      ["rn_counter_projectile","rn2_s","rn5_s"],
    ];
    const selected=routes[Math.max(0,Math.min(4,f.renjiCounterRoute))];
    // A grounded foot pivot leaves an ultra-brief dark afterimage at the
    // departure point. This is purely visual and does NOT move/teleport root.
    if(c) this.fxp("dodgeGhost",f.root.position.clone(),"#58318E",f.root.rotation.y);
    const poses=riposte?selected:z?
      ["rnz1_s","rnz2_s","rnz3_s","rnz4_s","rnz5_s","rnz6_s","rnz7_s"]:
      c?["rnc1_s","rnc2_s"]:
      ["rnv1_s","rnv2_s","rnv3_s","rnv4_s","rnv5_s","rnv6_s","rnv7_s","rnv8_s"];
    for(let i=0;i<beatFractions.length;i++) {
      // Move the hands before the contact frame so concealed parts physically
      // slide out instead of appearing on the same frame damage resolves.
      this.laterCombo(f,Math.max(.015,a.active*beatFractions[i]-.085),()=>{
        if(round!==this.round||f.isDown()||f.state!==S.ATTACK||f.swingSerial!==serial)return;
        f.poseOverride=poses[i];
        if((z&&i===4)||(c&&i===0)||(v&&(i===4||i===5)))
          this.snd("swing2",.25); // mechanical reveal beat, before impact
      });
      this.laterCombo(f,a.active*beatFractions[i],()=>{
      if(round!==this.round||f.isDown()||f.state!==S.ATTACK||f.swingSerial!==serial) return;
      f.poseOverride=poses[i];
      const last=i===beatFractions.length-1;
      const pulse:Attack={...a,id:`${a.id}_rn${i}`,style:riposte?"renji_riposte_hit":"renji_pulse",
        dmg:riposte?[36,37,41][i]:z&&last?36:a.dmg,
        guard:riposte?[10,12,13][i]:a.guard,
        reach:Math.min(a.reach,c?2.03:v?2.08:1.98),
        knock:last?(riposte?2.8:v?4.2:z?2.5:1.8):.18,
        stun:last?.27:.09,heavy:last&&v,no_parry:riposte};
      const hit=this.melee(f,pulse); // actual game-range, height, facing + defense
      const point=f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      if(i===0||i===3||last){
        this.fxp("slashes",point,last?"#E8D7FF":"#8E51D6");
        this.fxp("sparks",point,last?"#D9C4FF":"#6939A0",last?23:9,last?5:2.5);
      }
      if(i===3&&v)this.fxp("smoke",point,"#27173D");
      if(last){this.fxp("ring",point,"#58318E",v?1.05:.62,.16,.55);
        this.snd(v?"swing_heavy":"swing2",v?.64:.39);}
      else if(i===0||i===4)this.snd("swing2",.30);
      if(riposte&&last&&hit&&f.renjiSpendRead()) {
        this.laterCombo(f,.085,()=>{
          if(round!==this.round||f.isDown()||f.swingSerial!==serial||f.state!==S.ATTACK)return;
          f.poseOverride="rn_insight_s";
          const bonus=this.melee(f,{...a,id:"renji_insight",style:"renji_pulse",dmg:65,guard:24,
            reach:1.95,knock:4.1,stun:.35,no_parry:true});
          const pt=f.model.bladeTip.getWorldPosition(new THREE.Vector3());
          this.fxp("slashes",pt,"#E8D7FF");
          if(bonus)this.fxp("smoke",pt,"#28143F");
          this.fxp("sparks",pt,"#E8D7FF",31,7);
        });
      }
      });
    }
  }

'''
    p.span(f,'  // RENJI_COUNTER_FIST_V2 — every contact is separately dodged, blocked, clashed or hit.','  private melee(f: Fighter, a: Attack): boolean {',new_multi)
    p.one(f,'this.fxp("flash", f.chest(), "#ffd65b", 0.85, 0.24, 0.9);','this.fxp("flash", f.chest(), "#9452D8", 0.40, 0.17, 0.65);')
    p.one(f,'this.fxp("ring", f.root.position.clone(), "#fff0a3", 1.15, 0.22, 0.9);','this.fxp("ring", f.root.position.clone(), "#58318E", 0.95, 0.20, 0.55);')
    p.one(f,'this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)), "IRON REFLECTION 15s", "#ffe589", 0.85);',
          'this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)), "IRON REFLECTION", "#CBA5FF", 0.65);')
    p.one(f,'this.fxp("flash", df.chest(), "#ffe186", 0.48, 0.12, 0.9);','this.fxp("flash", df.chest(), "#9B56E8", 0.32, 0.11, 0.65);')
    p.one(f,'this.fxp("sparks", shieldPos, "#fff6b0", 44, 8);','this.fxp("sparks", shieldPos, "#E8D7FF", 30, 5);')
    p.one(f,'`READ ${df.renjiRead}/3`, "#ffe498", 0.72);','`READ ${df.renjiRead}/3`, "#D7B8FF", 0.64);')
    # True weapon clashes and perfect-dodge events also give Read. Each is deduped by enemy swing.
    p.before(f,'      this.awardZarekClash(fighter);', '''      if(fighter.kit==="tonfa") {
        const enemy=fighter===a?b:a;
        if(enemy.atk)fighter.renjiAwardRead(enemy,enemy.atk);
      }
''')
    p.before(f,'        this.highlightRecord(defender).perfectDodges++;', '''        if(defender.kit==="tonfa") defender.renjiAwardRead(attacker,a);
''')


def patch_fighter(p):
    f='src/game/fighter.ts'
    p.one(f,'this.model.flash("#ffe780", 0.17);','this.model.flash("#8E51D6", 0.14);')
    # Retain attack-cancel -> catch -> crossed intercept -> redirect and avoid
    # repeated counter loops. V2's Read timing, auto parry, and recoil stay intact.


def patch_presentation(p):
    f='src/game/presentation.ts'
    a='  // RENJI_COUNTER_FIST_V2 — tightly chambered tonfa guard, lightning intercept and cross-arm pose.\n'
    b='  aster: { // Massive armored'
    if p.d[f].count(a)!=1 or p.d[f].count(b)!=1:
        raise RuntimeError('presentation.ts: Renji showcase anchors changed')
    body='''  // RENJI_ECLIPSE_V31 — visible short-grip guard and concealed-form reveal poses.
  renji: {
    ready:{torso:[.18,-.20,.03],head:[-.13,.14,0],arm_r:[-1.42,.26,-.39],arm_l:[-1.45,-.25,.41],leg_l:[-.39,-.13,.18],leg_r:[.33,.10,-.18],hips_y:-.18,knee:[.42,.39]},
    wind:{torso:[.27,-.48,.07],head:[-.08,.26,0],arm_r:[-1.75,.45,-.38],arm_l:[-1.68,-.36,.42],leg_l:[-.53,-.07,.17],leg_r:[.48,.11,-.21],hips_y:-.25,knee:[.52,.47]},
    move:{torso:[.22,.38,-.06],head:[-.15,-.17,0],arm_r:[-2.12,-.12,-.34],arm_l:[-1.80,.34,.43],leg_l:[-.64,-.07,.18],leg_r:[.56,.11,-.18],hips_y:-.20,knee:[.43,.39]},
    hero:{torso:[.22,-.11,0],head:[-.14,.09,0],arm_r:[-1.72,.30,-.44],arm_l:[-1.70,-.29,.43],leg_l:[-.34,-.14,.20],leg_r:[.32,.11,-.20],hips_y:-.18,knee:[.47,.45]},
    win:{torso:[.08,.11,.03],head:[-.17,.06,0],arm_r:[-2.02,.18,-.40],arm_l:[-2.03,-.18,.44],leg_l:[-.34,-.10,.18],leg_r:[.32,.14,-.20],hips_y:-.18,knee:[.38,.39]},tempo:1.24 },
'''
    p.span(f,a,b,body)


def validate_post(p):

    # Compile-risk checks from peer review: these identifiers MUST exist in V2 sources.
    model=p.d['src/game/model.ts']; game=p.d['src/game/game.ts']
    if 'blend(pose: Pose, dt: number, speed: number, actionPose = "")' not in model:
        raise RuntimeError('model.ts: blend(actionPose) is not in scope; upgrade refused')
    for required in ('this.vrmRig.grip.left', 'this.vrmRig.grip.right'):
        if required not in model: raise RuntimeError(f'model.ts: missing VRM hand grip property: {required}')
    for required in ('case "smoke":', 'case "dodgeGhost":', 'this.snd("swing2"', 'this.snd("swing_heavy"'):
        if required not in game: raise RuntimeError(f'game.ts: required effect/sound hook missing: {required}')
    if 'private clash(a: Fighter, b: Fighter, pos: THREE.Vector3)' not in game:
        raise RuntimeError('game.ts: clash(a,b) fighter-scope changed; cannot safely add Read')
    if 'for (const fighter of [a, b])' not in game:
        raise RuntimeError('game.ts: expected weapon-clash loop missing')
    if 'this.poseName = p;' not in p.d['src/game/fighter.ts'] or 'this.poseName, this.poseSpeed' not in p.d['src/game/fighter.ts']:
        raise RuntimeError('fighter.ts: combo pose replication changed; remote reveals cannot be verified')
    if 'const grip=mesh(root,cyl(.030,.030,.235,12)' in model:
        raise RuntimeError('model.ts: unused tonfa-grip local left in output')
    if 'mechanism.tip.position.y=.412 + .378*mechanism.extend.scale.y;' not in model:
        raise RuntimeError('model.ts: telescoping FX tip not synchronized')
    ai=p.d['src/game/ai.ts']
    for skill in ('Iron Reflection','Hundred Fangs','Blindside Step'):
        if f'name.startsWith("{skill}")' not in ai:
            raise RuntimeError(f'ai.ts: Renji skill score no longer matches {skill}')
    for file,text in p.d.items():
        if file.endswith('model.ts'):
            if 'this.vrmRig.grip.left = true' not in text or 'this.updateRenjiTonfas(dt, actionPose)' not in text:
                raise RuntimeError('model.ts: Renji hand grip or update call missing')
        if file.endswith('kits.ts'):
            if text.index('const K = (p: Pose') > text.index('const RENJI_TONFA:'):
                raise RuntimeError('kits.ts: knee helper K must be declared before Renji poses')
        if file.endswith('roster.ts'):
            if 'kit: "tonfa", element: "dark"' not in text:
                raise RuntimeError('roster.ts: Dark element not applied')
        if MARK not in text: raise RuntimeError(f'{file}: missing V3.1 marker after preflight')



# Only replace the five V2 STOCK skill/passive icons if exact SHA256 matches; preserve custom art and portrait.
STOCK_ICON_SHA256 = {
    'public/icons/passives/renji.webp': '6bc7f98a46706ce76bc7dd30ad177e65d475c6f3dd7ce834da51f0ea8641105f',
    'public/icons/skills/tonfa-z.webp': 'a8cf17edff30cbf772369435fdcb58cec427a56e560d3d71a7ebd3f9896e4fa5',
    'public/icons/skills/tonfa-x.webp': '9b055b0ff80879e4237b619c40adc1cc9922f995e11a3954fc07c697d79e4b1d',
    'public/icons/skills/tonfa-c.webp': 'c0d3211ffc9d54ddadd26eb36049ada0c7f3bd29e6aab8ceb121bf6246826fa3',
    'public/icons/skills/tonfa-v.webp': '0957113671572208f82b35591ba5c10780fc87b14b97f6b3c31044bef5631798',
}
ECLIPSE_ICON_ARCHIVE_B85 = (
    'c-m~+Q*b4K)+ONBwr$(CZQDl2cG7XDV{~lWwr$&X&iU`1d6=21dDvB}cGY^@wckD!d2k2}5D*X;kOx{@Lja$>p)xB7h}?gM<Ud;%'
    'PcsKwb7os}XD4@N7gKk4+h3OM%x;!WcD77jmS!%Xa;z=0YO+#NV*e><ONyyzsqm0+{U@uGgXDtJfq;U53i0B^h?9~2!+~uPAps9>'
    '0x|dD2&%nmz6u!oCcch322R)beMapOUjtkEsDLXzic7=~0T|zj&vUQF+rpE8neQ&3*XPY`+>_V$-F;slP=t7}FFmLUumNy?HSR!u'
    'BNho->stUEe4PM9{2G9;K=^g;PwY=&An=J_<_DtBQ_vWAA9(4{8n_GC1TKEy|0Do`*PuY))>P=&3ww|AJ#bf;=+j1U4zPC1UDP|r'
    'Df9uomA?~Y_OtO0{HgN?H1>$}kpZLub&pS>JfML=Kl(q;@4#K>XCO|`$g|%t_!IM!{u=#2WU%pk-$>BJs|g?*nEvTJJ?8{01Qr3u'
    '0Mh&9A3?9eAA9?P9m2q`yr1(|wVzVpV?v4rGSgm-uVJ6qcfQMRmVjWa{i?GTC8=KP%Dq~URt~|-j^xwag#XW}yz;^hs4HQ-AaUp('
    '92=k_33le&ZQwRyB_LCkx>9|S#ZNUgF`C<K8sAhoWg*k}BJ$O*86X1Q5X(-VJ*4e9=hg(z1#uG4xbI?)N@V>}!RH-99DcllyoJj>'
    '_A+9%YHw;ey;IFu9nM4$V!^oOrLNqSFMpzaj{^4=Ju#s~6Wlp3dvF{}@Dyjexga(A)^3uV&?791CI##6gR>p9N;WG^4GP)XLtZZd'
    '67XANzRy|cGUO&MQNyzABE`Yw(b@>1iM>X?qVet%%q~ka<b`Wxez#o-QOo4{IE-0j%SR5<<<s1~D*c`dhHSjX$rpCmm=k~3_Vo_7'
    'rWdvZ6;%-=)=ayuDWM&0BxH2pz?l{3kQRs`t@Ur@*9|0O^HS3=hYzgM#st?J>Bb6G;xDc(qz$dYst}DJ3}dL(c63WS@HBhRgBqPN'
    'e5Uwd(BqP~Oyj3tS3eog<@(?nYMQ>X`QJXzvOpV;`V>)g&bQ6(K2YOL7Hi|HlT4>yp9qgp-hj<OG_+4*W+O_?-^iXoy*nr|)(FnU'
    'A4pzb%TNloV9<DRpB$i&%d(&%SQzx;-Ri!I_FgRLn>kc*_4aIj*44Y#;WNWGbt<@ucq>e^ap!sk&otE@Q=x#+RF?-DQ&wn9H-^7Y'
    'tOr73Te?Lx(sjtbqCzhhD>jUo_;nut;kY2o$iI#4){gT|MYq!mxcOu(QY8Q{<x*<s;X?{b$}}Q6=Dwu;34${#yOMAGE8Cf=vxn3x'
    'ot>$mo{ssqr35@-jazX+N|M8!klE{+AFv_8f7C!<kqM;T2h8Y<=(%5D{il4Vy3TP2qLU&jQr`N~GAb^UYLinQXtP&@SX$n*CZrla'
    'l2?9oC%fp0WGuy=C<gff#(-u4!g&^q{h&{EgbCZ@g~e}{oU2fh3PmYV_4B74Lt5?4ZMUD_D?3&ALAkM-0D4-8TE9)0W|tRiOs2U('
    'rIM)%Q4s{UzAEgdtrvt9>sLfsOkI_TYuLM;;1}7qi{kk_w>O&k2+7Ppt+Jr4dJDH$>g<z>aDP1t=GZ(XcF>0jl-U>*=~^lgLZhJH'
    '`OkRj|1RO7qin+w#hrFau86DjK-Hn@CQUCq)o^rSuIhdrd=5eVLmi=IV$!i!QWCn2m&oRB{Ig+4hh~K9@cAMiBAzwlbK<NU{ksxn'
    '?090cHKcbxvA9qexR6YF0GN+=N5i!fFJJvgCQsfMzJpoC8`hZYauV$*ewHZHHGQRcOJOOQrX%ret?_MwkGfEHLZWjWH|HhPx~3UO'
    'N9J`?uSa{PBL9{%t)ue-$Q=6UGx<GLKeWQFcN9FnGG2}eH)}!fW|RMF3<d!JzX=ati2dRh_3y<R6F?8|Z$+xbHx=mMmvL))HvB7M'
    'T<nxfQ(!*a^dNeehfbto#w>(D$o#ln3A<e*ux#P{f{wDHL2uagRcD$LVu;MC+F*K*?M}-uZcGMO^oKXEuqRWOd-tMAbVuqEzJtz&'
    '4KJ1rXe23aSaAzKT4aPe2l$ti$s*P^wWV_amLZhh)EYzn^Xf*LG=+y^U5AV2@NTy#3=i@G6tP4f?R84nm+j^6%;KgBG*b+~w6dGb'
    'Jd?&q(7b9cx(>u2UF#W_cazx)-R5a}@zZ}&y*`o}?M}TI3(tCUwWfsvrJ#!+Z#c9tJFcjLo2iGS;PsI$QPqzy`H7LU14*F`-Rc1V'
    ';+n(I=B`sTGn3Cit==4}BBz%Wat7I_m=-IkrpqlccQ+ihMly{%o$mM{w-GhLCGV*8Ol6CaOy|Cbk*Cb|C%~kS5jtp8K5Lj|BH%lK'
    'xvp5x>BYzQF!FI^jD+ZQgWz7jLw~0r&Dw&Nv3epXAm8GSd8Co*IL+JI%bk!q&ReOXSWwAk);;bDt-a=jy6iJH6?CnBpA))ih3L@}'
    'hK){HS^FHiX^w|xi)YFSgzLJe(mGs|pcf-sGdbI^K+tx-7?kU|l?KGQe{vF0EM1u&>68N`(>rDLDGKg~Cct{f;a~|jGawSYif?85'
    'D`~H~nZCFw;)Z<<Iq>7k>Of~i<~}*S(gzrY4oE=?pNM(lb}?H1CHhMy%-adp>eh`8>hF(V^x!P&@6mWVb#~as@2x9AA?%dMCD;Kd'
    '{e4iusS^Jb05&8^2WW>;PuxtNeg@%oL@9)LD8B8_A7-Ppyvd-nft;S81icS6GV@7^?sE}O2KU&c*wcb!)d60IMRF>$_fBtrBdLXM'
    'nEl7zY=fb8TCwQGlWv*6TPMakz<g{e*b<blj6PaHPR~(asRjS`Txw=oNl;llc;&ZELaA1NPjX4FkOrP1oae|caV%0DhdOdQ(e_9_'
    'k%1rl)!Jyu_8;7F!+xVDL5RH=$51rR1jNu#-|+6t#=fFgqTmGj61mmaUgp15vo4=vjNIph>39)<rE&ZMehTspoL*b4?fyS)6LF70'
    '#Ztrcl^xQ>S+TV6JtqwGvh_FtbFAo<dLKN-^50Ab?z(Go4c0_zOi43EjzIA(&>0;3(ph`VHOa0Tbola~sVwk9ZO090QrMq^DBNmc'
    '$4zjKq2ZkC61S3k88iuslfWAy;|U_9{jVcVZFce<IShh;N>#^<HfJG)hH~#1(Rrne1BDL71aHdu4gz-QP0pjEGOS;y<y^rDSP(gV'
    'y;==%io0$L8`Xc~VBfGhI-hz%n>$O~NSgkh@yeG@Kw-BJ%#{_!cR)%S^_sXCp@Z)YRTT=0j6}2P^PcxA_W}%M_;U9SpM4s)y`_;j'
    '>r<!->A5zO4o4b9$LeXwGsmq3t(Z8Gnh(T;%0X9p9A_?8o$m7KIvG$wJJW)P|D01ijz-$$7WFNs=MtOAYrnzjZ}R`jr{MD1Y`q?5'
    'eL1MOWU($Kex6x9&~_u`<ohFbDK<p(OAa+*q{o+z?&}6Xn;jqhtN`$3${a~Cp$3+Z<q8TPQu_&ca1}+Q$`Y0?3mgReT|4!&1+L?_'
    '7v+cic!SQl7<VXJb{`FYb!B&*4fi`LxLDBvjU!Lxf>2ah-MSW$zugzw8I}HB>kx9xnSb<W9rnQ>Hg8}hm1m7#{U!_M=HcA2Vn^#Z'
    ';6SPO@>QBmIH1GxBL`v(2M7Wieo=sepf};xmXCb??jl71eKNR{93d%$Ja?02qH(v}6z5hcj@vT}5eK^?Jr7J)uXEYQXS{fqj;7~Y'
    '{&faY{nNDaJ#R6$;7OoHa%*pJx{(4luWyh@14#KRp(r8m9F-2~PpB3@;+e}K`!@6{kKE`&(PQK%j>YtdY+vbIa$aTr`8{GSgMa{l'
    'L4BHWl*9<IzyrUNlL+wk3rr6;@2y!e@TN!o;(-vDOxi2=aFf`(Tlk|T$cujQuZkB|$4k~0ZkG+(zVzMXnKk$*4Sa0fBaT<Ic#!vx'
    'PSL%wL3gFK{eVasOE?l4Gc0;}P1(a~LTn2|W-EM^udKPJ7mo!|Z8}y1s}9meRgRwi1~Ur^P$+l??qD9|PNLm}dbfC;Aie6)(47nW'
    'hs^Cb+l4fl8CI4Xdc&zig$vlW-c=B5+3TF5MSsqvsp5%uI9NB=!5+L%MlvX7hAed|edML9N1_)0;I_6hJhspp!N5t2xzLe#`r-X*'
    'xJW2sFA8h@j?*T=qZTdC_Ilgf3+h4ZuGF8(Vqv*A+Qvm07r@0;PvfdK@%z$-t9(39cz$dyO7?c7ec-xfk=f-I*M9DM;4*?IzMHM|'
    'F;(%JyX*${ZwwX#-&9?8@hG>KO19&^BXd__a6ykA{q`K2)QI9Ft`)0x3XDPD;f)^iR;!^wIK~zseSj=m;DHh|#_i)`E<JlaEk_{u'
    '@NTLvha0T?4<xsXCE(kE9_R6TbHL*IyTg%ngNYd~(c!i#*05%RVrm;|3PGB48u4kRqUFX*y&L|D-#6sA8m69Kvd}U5MJVVx{^9CZ'
    '24@3-Y1HVP{^Uguz76SM$Qim~vKcHg7T{SASmH<(#Kos#+y^U92`cT7gyQJMk~2A?>AaJxffHaubzMubNMa7L+yiP+bG|?G>S11W'
    'RGhi71d*~a5-NoJ*0<{+)e<xRVtYZNc>(!hI8kR5mpcD=oTRp=rn=j0N)(%_%jC<Ykcom9rlDI|WPprx$9Ff?bmsrA`$K%p7m5jj'
    '$~$icKJaQj9u-;h31l}^f#r?P)kApX*)*I8J@Uq_+2Fx(bVyubABC8f!#%S0rIyo*xxk(Ho3}uSG6$gF$0Sk@VMa47XZyEhD{#r~'
    '#c0}wEeC4+4Q{%;(=e;9p7uEmVY&r-8oisiA}oV_=ejvc>CsHJR$2qsve}rMg}*>h6dLi)WZ7jYoBHiJGV!IfTY2-v0_-(a?H*?+'
    '&9vFqItc59{O#Qr2u-5@;+nd<&J^Z7f}5r6GgIO(|2f`om1<PLzM%!Bt!hYq)BctEkU5NIlUZ+r6=QXZ-ziMA;E3j$%`zyc#{=q{'
    '{-k9+efo_6#Dy_jJd>)oo<%2+-!*_9-nwVQ$MS=@<G_DlQaT~|ri|fyFxi90E#c1d`OzQtb?nUAh`@cvO43PGRV`w9clNp?lJs+C'
    'q+Vi_izoxvbrgH2W5A?9sEFGYfYj#ysOco!hOA#+>JPaPGqf6~7*1BD>Y1{g|FMmn(`D2no=_iW=Kln8^dT1?ERkHOn-fo>_dE+G'
    's#DE?sUS}UKX1-rh$MBa`vr}DI##Ra=lx)B@H<T9zaEB>JKtMH$c@wDWMzYqX(!+3H|roU&DjfxlLCb0AM0ao@kXApXkb8dBVQAr'
    'SUASq;n<<q^*}y6+a@XucdKEe^q2&a82C;<A3$)TyrZD_wbvI!H4ZxIqo<hJ=Gwtxflo8&3nr7BkYRn5V8Z+LKcbCxK(D@WY!<_6'
    '@(aaayPwhQP=&taTLbOl)w3F+C`9wfN8$K6+`G-lp~Vi0)V=qp%DY6ACbPyADu+%@HKbK9H>JB=7Xtln{GaQDzE;U!cABRsqW7IK'
    'PrF71);7$9!gNO^Lx&5OoW}~Z{0b{XKz_80{wH=xoJ|9L9bbm!zo!<4pZN>XXX{SXp14|G`IIaR-I!B(yQO_rB^j=D258*R-)5SH'
    'dOy;$Ds;=IiUBrvDI;q$V$LK5_Q0F0t)cA3t@!}9<Fg4NFmaLW+K$pl(fC7T90n!m3V)-}`GgAXAvf8cZ7GHt%X^6HOo$h@3=NpP'
    '%FUCxN+Iiw*DYxR92I=8&ohJ6I}5giU=WbK5W1YwJ$l(MvB7J~G||NVEc+mq7iP(5UGU^|rIqkgxpO$xhn0+y<GU~#p{s(gYvmkH'
    '#1@g%Eq}1!5kzcIf(;xPyvmEjLb}GTCOAiE)YQl!w9sHWc5qe_dX0#ZlQaEJCS;gu`;C)VOiffgn0~9@p@05#$0HPMxed&eT4Fx}'
    '4%+0aE^-ezd}PqI48G#i;u}jx3W0>tD<WWyHJ#}oER<2+sU-{~s2@XUFUNg)Ex3+sQ?nA?{IfqK(w-hS$4@!Viz^|F+rJi~eEw|Y'
    'TXY`5oujn}U2hY#v|mI|y3WM1!Fe*cT>P%mHum*nV~AC>NLOKGUS8n3t5uVj{vDoNRveU)ACBpg$`+0^Ti#QnH;1;9vONx39A)o!'
    'z}hF~Ym!rF2<0%EYG-&r5E#!8j8fz=+-Skh9cmJ3YXsqp-eZP46R`JBOdZlTZ*}2ZJeA;_;@hYx-!;-|wT^pJUrepHxK6fDd`Fb}'
    '4vQ{?<zT{(DWe3iw)FnFuK}1*#5k8vygt&j-9^zr`}cQFE{Vb!#82=nQhYvj&;TgrOS0P<US-8gX)m*{M^JraK9a4U{WL4E{h)yH'
    'l;YdAQh(iF`~t&}Oz}4oQ>OHJ8yxHc*L}hM%0S)D-HqG4ggCkT4-xMGt1J8^Wi9UaZXK9*8dlu;Kk~oFzUX_4N`r<KC)u#Ygjx5g'
    '0Y~#D5Al+x=|0vi)OR`}qi`boa3SU{RqTN70y|W@*IqT&g;UwdQnT7amu)WN0*96oMprrxOV+|Zz{k4JB3y}R5HzywC{_$OuR%iI'
    'H+(jDawas$o<kZvQ=N1clZjJxpxZ9TX9f)zR8;}SRhzoMTyq-lq&?a;@jy1kr>WyikRv@J=((~pNUAFg`Jz(_imlcf2k%;WMgXs('
    'UNMM|{Wk)<fT&QNROm_Ez|OlDCy<q~9(!k6vfQp&_@*$DHw4%~teF0_74Z*T=OPuut(fIbOj~%Oa$rx4s-oH!Q(9$9>TWH0pJl-a'
    'l#@rFzbQOi9v;(-CBT9e@T%pL#qYT^@q$?CUO+12A+IGi{yAi1&irgk+bO3-riHFL{^Mo+-is)#aP!yvZ;$V?RpfR6WX5r-+0vEa'
    '8_|%HA%iicC|?=5Nlrno<XWyg#K4z^G5cIL5a3$w#ILm<csXMJuA_gl?0ccsX%Xmp%6C;a{&IXRR#UUp;d(t0(oAwRDL$tP%ptWf'
    'Sy?0#)-<PDz51N?^f4V_vSN6F5|wGgYTwhXpD;#3FN?Cc>HUjCd`N8EaqZer?-YiqU{6~gQ7YaLS<AyiqhbtHa~k!@KVc|)O8zxp'
    'qKMYa(4iP@jqX``atY@=@We5t*Iqj7r&0^NS=0|n9#n5;pwc<r?EFWgfyLhNX;?P*OCYkbR3rGHqZk`kvyQZIHD(M5@kpc&7#H0L'
    'EbuD{y<`jlY~S7G1($bKZXSF7UJD~$ZzWIXd81o{v&oIVLiXJj{C4}5mSr(DF6P)}2Y(v})o_-KD3RkBDc)>5eia14$o;Uw8f8(}'
    '{7Q)e)9;VDE1!=g!q_161JfgoAD{r4`)siv!y#GY9f9O|LOTH_9B>#{aG+%%GjRG>>;_5`Y@~G?_&1iu`==j&Kf9`91Gxc-aMn_0'
    '_oNC-;%HOD$am-RJk|Bf2t&;`hn=NtLLS01qnk48EyoW@3!jaIrk!)Dod`F1Gl{pfD!>=j>*yX8^r#d(6;VbU|3c2gU@xLM_Yq-;'
    'bmbUS#LuM?Jl{*KRy=|QLGR{m1u51fv;!^{k^Ud#c6RsV;w2mvsJc6WfCp*#+NNZ1Mcc6s=viJD*-Co0egMyWm`3eseS7Uo>tVpZ'
    '?+7YW|E_`D;<2NDYsn}SJM*|0b~SB?l8W_zIH%LkrX-N(goby1Oub4sIqk+^OQjhF+-7{%+_Ay@W*}~RbZlUygCRi<2uB)^y|4A}'
    'tP#M&v=&#rWVa7n?`z0+B{o9+i=l?7`=8VZ4*WA{4|>bmSKXQk?f`<#NDLU4U=x|`(N#L}TVDF<I^1t?p#a4$5yM#QgyG*Pw6(eZ'
    'uh5n{x^r5pAO%5;*XusT>T=|~gP82=_E1$lnHq>Te^oj?8QsO?Cdk=eO_+HOEj1><i{FQx@3bh%S^1d54#+jmvB^Bkx?SwXAp=S;'
    '?<YMC;||#|eJN1;^nKszP#@HEDD=n~g%V8Hj$yVihm_5W^ivVV_XTiSU^~PQh_N?=Qp&fkN&U>X_npk=5xPI>2er8E&csuUPpPcO'
    'KgvJYWsi`EKg2ql-OsDhbJVPqhs1_1hq^84Uve_Zyh0JWfakG+N|^UvTxmjo1*gUlqx&f~%fhSOwy$%YWD05HJoxO`$%hvJA3?>`'
    '@%%}+;;!;^N?7cAX5L^(=X7T|8%ZYZ+A>-zN)X}8e9x9u&QKC0w!RGRHP)0oi)0l<tL`C{V}O8j#Wj_rwVgqg^HYAO`+VL)iCGMx'
    '9{W10d6vdPpCIF!-Gdehe>n^c|M=PVHuq2`DH=L_bM2{q`d{-G4IjLWhIu7&XN8?>pUvr)+-1Y-HGe47xetVLj4LLr*J@uVz3OXC'
    'oaP7z?+y3Fh2Q%JFFq3o>~wtDG9~`-v<4$J7Y4|5P-{+jIgJqo&XY+2!TCKu65e|Ks1W2n#=5xsa%X?F1Npx9nSB>EIigO{$?a@N'
    '+Ei@po%>7dWc8WwKivqrx2PH~9DIhLmHRT9dHkSF7230oXjSScL(Ym#fgALyqUq3^HY`g0qC##rDD|SQ<4IZwP0U%Nc+PtWBU_9C'
    'P;3oo$pDxUwz$(m**=ZyHlC?Kf3VDNb1d`iHhazO#N)}byg?rkfF?dFG8G<|(?^}gYCWVWr$r1e21Hf2PBk#i`j2tVV$wGfv#-VW'
    '=gw4Lqqq=s5VmPXSrCl{y-j6O5wEj_#TxVb=cJ}@&hHIva7gq>2e9b$$0yb+PosvijIW&XIPlNgv|#54ApBpq$Fn??-SOvkt{RHC'
    'Rqe@OMgifqxh}*~Q58V!hYy7^B?2jn|HxPc&qF46d$N&Ssz_RUwN+j5kYWRNJoFLTZAjieEGX=6NB+rtCnMnxy|%>p?vNwi&wx)_'
    'Q5I*xmT9GK;X918=*rcB?Lm+Di^q%l4u=m>2Gn&1EoyK7m^s!A<owuQy_kGsw?R~S&ioMCsLWULczbGY7`0lUIee%w&~NMdLmU0G'
    '&DYp-w5V!^ihULdJrgxwPL|mS6Ysx8@u43o#KYrSJ<`$oa7(%~_~T=<9kVwM=N{!H&5V*#zl(7?*dtF5)i~k^4img06y7Bgk-DhN'
    'D)hB{EY(W)1M$~5;4HNV600C7hn9cpX>L@$u9E_h26cDWAs!ff#gYbqFQ*mtHGz3Cre}<LH$9kLuiy($ae^SMoO=)OzW?3^q6gNk'
    'hKnzjxKI}gXT&g*PQtA^_;<`qdB11Yhd$Ct_3(~wDMR6!+K@qhuDNbDAgYxB9Zq``NsqiRV*3LSfhJs1OxZXUwS&y<z;I=*OT<LB'
    'gziY!xR__nU>P~;I6w7r4XAWNaQH9nPIj%bb$@6~;rHh6{AAvw@}y|+I1yd2$q|xw8~4UwN$;&0<&IR)-2s~2?Jrc&-7y7iG&AM7'
    'DY6IMaNE45L#T!^25Y+AdGkdOHGe;MPH`;WwyWhVOGi&@=_q7DIc(*LIbrkF?eFDJDyas@SKUw)m2KC(m((t8#&uE6CPG=GoMCCG'
    '&|(IRf>h^8P?5uyJ)*gSW%1D^G_d1`*&`E{$)kMpQEjRdS=L#*dFu4HOimu*Twcul9L_X96cM1NXAfqff@-I)g_RMibNEC>HSLBt'
    '4U_YQyg5PR<ui(j8TzH*3#pi8J@_AFD7*FLujbv;oFukAV@Fnuq+H3+T*IeJ2v<Z8dH{;!P5a0=<8U<Q2S;5^0bTOGQrt60sjw2U'
    '!IW}p00iP$W|FkF&=kT)J10{ysje=gnjvbbPAa7B`U~;i8m9PZ!qU;7ipO~9uME4P_P{QD)|ITlflo_hDjNIQgC<N(wMBMo&-d&r'
    'yk%3#t|N*RfsvX=tGu~$TMS-$<VxAW7|C>oOW|J5_1PevFHWUBq~DWyAW0@o{?tNV#=U=CY0QMt^R4NpC6>4qZ=4&VUY0TGV6X$3'
    'D9AQhK&8$V--^Z0KPj{!a{3PUs}co+Wc;#){V4*arRfVMA!40f1cuk0tC)FsSBwB&BmuXw$UP@(zk`2vo)k6Y_7u#pNR7&|wzZqc'
    '-h~1#!ZdRZ5h$COC5>MG4UEEu1N`wgQuoTTZs$sH_m#_P-~av^qrF+<|3sozp!HvZaoAPtI?X2_bh2>LJ?8rd>l!@wc<mn&c3}H~'
    '#M?ImH&+23g~8<cCmiTwepBoE<IW)kpz&?4`@@0&go6;zm4|*(!5zvLlM0R`errHc{auV#&XZ@Ywec%B_ZQ0ExKy!8cflGAP?@MR'
    'N+n1e4oTAzD{`wPcL|W4b~nY&?VEKvaB_l<=ihKF?)N<htB-LYgU0v7;_5Y8VVtQQv515&ipIlguN^972SM6H=$Ym7oe|#a1^5Rp'
    't$M_mv4PBz`8oj&)4NT8q=rxQGXcLXV8@JYYqS37Jm%CAjMQ<vS2AG(Zsu1P$!=6VQgcK%|JS3_NQz3n`1WEa2`fNPweuYZWdU^W'
    'NdiP{)v19-PayOeQE%yHJn^;VZhWN8W&8WjJ@jc>ITU^f^QL<y^O<<SqMh6U&N$@rAsVJzE^0q)9sUzk>bg6JpD+<ND^3P5T^#vD'
    '0JM(kTmh^rUt7h;^8B?Wp3Y7j6TZljz3aiPO<1u9?zLa>Y7RFP7mlm_b&4pMZ^SvXRU&jXWEBnNUzrTcscysR1fbKles;J?E7R7T'
    '@F3<}?NU+s4uT<@h;>5tCum-dB<l?*G6gpXXpFf3X^`Oy0CSXyrl}{_61nxD``P1MebN6;<bwPO3D-7QTp!Cv&$+XL6+A~w{AJkd'
    'sNua6A0B*N9{%<&hnMx>#60rpUt16gN4zCaYVOBFWUF+h5nk2mWO=X)h4cC>z_E>+Enk@qQ6Nsrd#Gd;HQbm8ziAw~_v#U~KHYfM'
    '43YYSGU->OQn$)nQdId7IiJEd+dmS^Djeh6h#Jq;P&~SF9@!*MP}#2$Td&>gf&!GMniknyNKIw#m!rWEFv$M5OBlJSd$HsX`Jd;b'
    '=WYo6Lm5$ZZawDHoukl0f_~bR8&s@%^_?shMvT)AD;y{4wVUvlr`srvo0s0lBG?zM0QiI*{32vLC{Zk-d+!9@%Y3+=gUhvrGsZr`'
    'AB4LlpQW8U^Ji2BlQzk{WVGpy*Ue@3W38b|n;K2~SHk|VP*p^SB??z(2%HWifeP^Z9m*8D2qqRSbV^D8G0@$a)&2F3%h?Y_o&EH%'
    '6*S*JaHU!e7wItHsz?^+P@t|W2vGodc%ZZ_dtmNQsl`f>L=<}MMh@3Zt!iGBzn797)ro)}?LT)!wS}t}c<U-yqgRU;R_{F0|LaY@'
    'J_Yp%NjG+uZIAiqFg&;JqFxJ}bO9lk|5^I8G@&Bh;}fzG1AVQXYb(R?PQf7^j5H^nF<L7o%^BM6TwZ-4sexlW9bjxIOy!Bs)To2='
    '2G+JMFcr~^xjt|I$1Pi@z-BOH(ezdD=Jnz54FRQ6B^pZFx#yB$z_9*m<LB4EVM_Kz58YjAP0*HTvA49S3*~Yp>B%a8|C<h@5aX>='
    's?!_o<c3itc9Y#u#NwTme$o^=+?dhLipLw;+r0~(;3P`jD6?7|GZAp0w-^?SIE?3IqN{^DY-LagSwWkgkYHD!ttC$k6uE1cNA4$#'
    'WLa9uYo~Mp;RgCPhITXzZ3MkEd=(#mus8*ETo24eG#2JQ!zh}NtwJr<>i08*J}$yuoZN|ePMY1xY+wHZbF11VFHzv&8J<84+x=|D'
    '=(`9S77E4=_RgZAxiBN=C9=S%z44Js>FP}X5)3vvy+UM|DoJ!+=3jn8?qt?>(3CC5B%%Y&VQKy=t(BI|q9quDu1e?=`urdZ+!DBG'
    'Xky=v5gt`AP~MPiqKNWwK|?eMxvf~1eE}a&?aKFYz9|S}#Rhb@m|<4R1D63Al8Z9p9h2T2O35rFq;dkhe+<TB%B|M;d)G^L6bX!0'
    '3;})&t1%BQ+u=+UCW);Vu{WJ8M@Xeo?In4-A+tBr{Jlof@Pd2TTY@-zeY9`*d|Ld!y9^Xr$-<D8RrLo_=t&Y<W#@T(V;^U4+eUcD'
    'DyNsi2x7MfTp_Gx7)}v)mUAf}Zgc*99Nj~CMf|-uAE_vxE40i}F}F9F2v|DV4`uF_-pFWUHUZ1*tu4r@vpa~m$1tV2e(u#ba-Z+t'
    '3vLDf!>j$9@SJc>x-W9p(o;e}Q~hVzFNssDAmY4i@6z!?Qil(f-MSwblR}U$`X{E$t}>w1s6}hvUp)nD;NR1>qiN7UULtA$M+Iq@'
    'A+m$y{2m&ry8XVS=aS3GpRul49yXAUt;_@l32w8LJM(7qU}E7*#par6aZ7f+Eqx?Xmj{UF9~-`xrW`XlK>&lPvjP9`B*4g98v2-R'
    'B+!QwhTqFQL4@wUP11G~x8kz#*d=F;S|WF2V6NT0vdI`GR$R@wIZ@VFWVyg&AOCuhu`Vh@@v^lm{*B#KHWjhI(5<nQD)7W6(p5#h'
    'Ig-t+y}mp8lC72I4PeJF)tf~%;x)#Oo-d|NI841l@yYd;C(rHbLRw&BR%ZEY+t8&Suqevfwp4`0)KQJ`IE}F>OwlT}YD|QzlB69^'
    'k)g5zrHcZJ_mVdIe!MAda<vth&~f4yU}?HCwq|;KjxC?!m~@`!0Kc#8A6+2(MNmY0&eN}emZB;idF5AM<3R_lWcLE22Lp)MBe?na'
    '`t?xdpFJp%z!iEo*ZX8K65M2Axr{Ejp}`<@Xtmg3ANc^^0fTu%AYNU_<KSWW^(lkOVJkZkNYga?a@SBa`5oV$kTFlmwAPdIU1_vw'
    '<>pako*&mCUR$0vzy^a5njvow0s<Bm6@hEq?NR|#=Wev?-7u&4lG&cwae0Dc@%ugte`Ftrwr}0~1yLfBm>Z#sC>;iDF4q2$y)B6Q'
    'Mn%jB=po?`bKuJUCvI>6m4ZMj)^+(0xXT^96fK975YI*GH+N=!ZwR;#v;t8fx_3;?5r+`(#?Kk6z@;XRV22J|u5umAtpeY!bHVEl'
    'GSH%`<e-Zdq%?5}KQdIU+AT*f3X#tXvGm0`q7yrlj9Kwm{MTHf-|m^*wo@)6pWe#Qb;uG4Ws*4guo)NG8=e>p?=@PBPfGL!%j`WD'
    'g~mFe4cRkU!)!sS>N8%wh1@^)A^L{Y(_MF!$w@8dJDQ$PV5P#esm^huf81pfE_G}ARb+?TUKd<(OWCAgcaQ@@O=o5ZQytlpkL>dP'
    '4tT!$q*hPIBg7$eV3;%mF|&W|<nPCzzqS+foiV=%Y<=%2>D8NHb|f9ppyG>=4%)p-aiicr^TE@38#!^AN>}rshAgTxlR0xYbk>@W'
    'eS@OIlm-9RQt(-*m{9n{9Qijoycka?`dYO&qWtdD_xAYoSK>Y}q&UQEHTgIsd$`Q3axs3TQ#n~nFQsL`L$bHE_2qz`#_bG9iYN5&'
    'itWbZ6KRAu`&G-%+Rf#4i^bC<q(GV}_REt)-3jUPF{62!9Nco?NBt?~#CY7Q8s(0eD^4|$_mTOMD@A1wk_88E<u^QJx-La_QQscj'
    'y(gt7WcK?AxM$JA%`pQhHpTP_JW}%MfGW6qjtoUSB~k*c-1P6U!hWLts?P*4shDb$QbZoV`ZB&4y!aEVt6>l2v?mD!aZidA^G7U)'
    '5AcX4P%~b%uj-bkAJa!h^#p#IVsqfxMP~UPBMy0StVSU!Az_^5rz4ga(JyibnHRj8{Q@kmfB6D29uJXIv{E_YD_(gIO03d63=C*('
    '1t-oI(N6gXBG(S;%7tjfnKctiPJK+ALWL-CiCfZYE0|#9NsXkzip1j%R+G8ZEbG*U_SKDN(QCC!4GBJ<>xOA9+T<0t^ce8e2euR?'
    'c@&NyFLdygbg}%{fP={;`=ov^XKwjETj~>?WQJ7IJ;kC8ZW{B6tk|a1W|eAbB&iZiy=qCMi2~@tnb#_#Jbm=VmN3aAajvZs7aDR='
    'ET$2af9{uygPijY?{Do`9x!*oPR&a~*DsRd3e8<YznR#>Ya<Vr>w>f{P`91AtV|`H7OTiDZ6mv#$AUZnLDV;1mI;{7a&0uhz`uVr'
    'J>q<n$A$KkNkc`|yX;s9VV>htUHCRO2N9EZ{x0xD-&&pX47}MHbcK|Sy9jA$#BljW$ZiJ=L(uKbpwLu52lqdC1x>OjlD78=$N-A#'
    'Jm(Tzi#4Tg46km}Eyc<Lh4Fi`(4)QyM)+VI>6%_yzT2K})_UeBOXeKlYO#eZSG%Q){3NqLkWGF^{Vms9+`$prabkI3M_4WLD{Eup'
    '(U{V{!k=O-=zaSP2w*P$rrW@fFofYf!zJoyOMQ~T)n+(ar|bj{FfxmZ&P75=cf}D5t-Q|3_@ZhnfJyRq`E$7(w5&Q+>!B5wl^f7>'
    'B*grX@|B`Anf<Q9jhl57$cqi!<1s!fL>p5_@-|H-?q!JJLdoy<yn?I;{nD%LQl~{mzUHJzNmt2REmVdinIzG>mPWE7;Olj-C|s0b'
    'p8SIuNW>E8)2@xz5oY{5is=at_MbHQYzJl!6;yqe+7gFfEDdsoi{}fO{9!Y9L&f*Rzv!_WO#uAC>B#&fieB>YHns9l3A`9!)+F@='
    'vGUY7RUILH+`vN&Rz?)8oap0w{(aU2&wO{NX5boLjeHo?04i|d?$H@XDy~TtJh?c%|Ic0%p1-?R1#Afi0U-kal>r#qMC$==mtmn('
    '*9|E}a7&(j7iCZpsE!M<W+$V`!TWOk8kKEmX;oXzIX?dxOA{^jIzy4GqpHz{s&+<EN2r^;8?G35#NVB<%5cgbfB%Ltg*!>1u&QA^'
    'P)gYzO37ruh42>e$1l%~Ghkr)=)*_%qc{|`_z$}@9A1i|fp*S`+V_h`N{g1pCd+K{nYl|)S&}-e^9KIWE^r2qX7Bw=k&z}jyZml@'
    '(umBiu*@ej+dlsiB<gQRPdzngOX)6EHp4&y)Tz;1RwAn*+kuhpMQ>skF0B+{e6Gc`v`D0&(^r>7=7}AMqz3ci$?j3Uii@Cxlo*Te'
    'wqS@j+h_)cPISqk#DfUFNK?8F3x}gv)ulU#&3$%;)t?jk1PqJ;W10LpMAY;~WtQk~?<Q0my9Qz9&a{snZep<c<DP*Q@zBac(a}+3'
    'C__#NXt8pp&FmM7o`YaJJ%Vhsp7Dst3>^_ULjA+$4jns977!~FLV)<K>X3b1Rsb|tY#Ii}v1~iF(nYQXX#M4Vr82syuCUg^hY%|q'
    'PgWae9yu@D<A4nRp5c>&^piLlPdvWU3lNL%%pzM{$b_>zqy^=kCtW(Vf~PSTpjya$du*Vb+TyR#&+&oFGW$X#U&1I12sZA?^iP-8'
    'IzrRo8?rV#J(4+!EBBaFj^8lQ?PhixQ;uEIL6Ex+8$WbSXmeO^DM0yoj6c{jY=m_5dfk#S7E|f1Rh=_*i4SmM%D3c^9@F<ZVz8*_'
    'DjH%;j3~*%Wh9-&4fj*2hO&ZhU9Plac0gK8y^@bvc8_EP(v|;}^&U8<15YQ5Ev+g|oSR(3auT*BGsS(2RDx=?DztN+%<@5kt&Fu;'
    '8P*^RZG02`g#<lO493yP&!2RgfiRLMtGcXxGM{fAXXXR-jfIe=E^wc43JPem*ch;=BjiUZr!U78E?$#I!_6N{7ocATLNYu{=OARN'
    '!7XBH&_<wXB3S5aLL)e!a)+)~kVmkpB7JnVO{jWjD5(5&kbS9lES5Q{du~5lSjbkw;CrOA62MW!QYiZUu?+n!3R__|bmBf##({R*'
    'aEVpEvVnHuc8;@8<T_qa63Sk-U#I~jGpL!$8)_;Vq-0x1?b|QxW+Nsi5_jEFH&p+(B#%+U9ikr6zz|Jz4x~O;|8d}hCsfDxM_4Q5'
    'r?ZJ|o=&XN_sAsDbmk}#_D^<tDx{BbqEtbs=3MnAFOAETujQYVL!?M>D4iLfzYSf?-@g%4GDxV}P4vt)O4QcCEh7|y#erq?o7q=~'
    'R9T3ezQ%|(^z-smQL2*8p}#I{6iSxH@%}6NLM6?}lk_)Y4@}}qe1Oa*@HFxPr`_S?nZ7~R7FXe#5LIq}>XhG=kAg7n8=W)8Yr`N{'
    'aP4^1J>UowzMU)_`s$HKY(PXWBeP7Zy&0F00@n6(Vd-}f{&rueJ2Fkhub@FD)R?g|!IdlXULrl-f%=4T8LQ(kVYNM!;d_h(Kd&u8'
    'OD#w;(sbp2E)yQ=2*`#8ruO4;`XKjJypxF@gZ9su3X^`5Ua&sa5HEao%3v_&p{urOj^C7n9iug>r?g4<hpdVyN|o3l$qO<ZO6XF!'
    'P1|IP*bTA{CR{jdv6^3Re05f*{tG>Vhqr%uUy#UFf07~KiMx@Q@w=Vb)`j=gP$_y<+EzO}JS3lB+eSh`&RYQm$fU>+pz57dVnlr&'
    's}S5BbAk%_)HP#Ky|O@QCjn?aIx-Jz-H?&rA)|`sne_R7CcM*GRpp&;C-ctgG_pCd4Ri9C!F36=;}Fs;kL^`0N^(|cL*Rc4z|%sI'
    '5fz2}(yAt@lV|lmZ)@=aa9FF0)Usvg0h|e(nitzZ8gc5Nserp#sKPpM)oL~3ltj6q@DifZ=qkCp<gb;#iL}%CiOZ)c<GYZU+L0LJ'
    '-|W*)=FuA|djzfI2Sh1&U6`0&%|fjca2zhuE>U5ep4B2aqhixfxm!D1BC%h{Ek4?oK49kumF!1;cHwsVbx>od_7nHbNnc57UQb2E'
    '^P&&465+9d=w)HSAS(Y4#%Q|Gb3EY$0omvL|6mMvds_zwcV-V~Co5A%-~Wv<_Bn|s|BEr!IsXsFnEp>rYWlx0M(lqv2F4`k^M5f0'
    ')L9K9t4{BIw}SI{pjDuZ|J-U&DbVcu<EQM^`Gh;Q2mO@yxUVj#0dNM;e>Fe3`!asp9R{)id%xd5K>^s`ML*WB`ICwNh|hjBgY1Eh'
    '?^XBkpNa25Kfud?$Dm2TieC;;8gRCb{Q>+S{@HCO8W9TF>mtfF?hr;WZX<3pn(qUA33;V_4FYa{-d?}n%sYb?c8`I!Z^E-cTi=53'
    'pzE<KU<2R)VDobhSn4I#2`n&938Dewe`ErPU-J`3ZGXgm@;=i)l<$qZh0g*7Py1Hp+M!R{wy|e`uir2|UN1-c&>wqm#P31J0c(Aw'
    'z%_v1PtfgNn{sK;H82sV`Uw9$_j&i7e=oEfIM(MO{1t@puJ+Rb1i1B&6TtyD&){q^*L4pHL$a@$mI`(*_G|R*J{ZW}i7$a~szR`('
    'uJ61sMddGr02vTNbg=`+G+0pDs9dX(7Eh(wCIDt2i9Eo3!5QzxLPTKKL&k}B-<xCn%BKCtP$mM^$^{KQc>VpCFHNz!_#QC98ACB}'
    '+#@T^pJ3AX=KbbV8oI@cags{YkbDJjls8%$Zv8PyzjyLzxS$$f4lG?C_B0IRb|xHg5FBW_jDExC(GT8MLV_?Z=#%xUcv@wBjP`|l'
    'Qd7=*v4><>_p*c@wi;8UiD{#P+n2P)#$SucU4CS|j}x%>a`wi4kt3;FnLhRa)GEg|xCywq`8}aC$EfB<PwLAwJsXTA#hQWJ9Ov=K'
    '^Mrd=FcYV`UXu?ZE?1fVi_lky(`)V?;~+ryE@t0LB7(Z%DE8$fY6b0bpstGH?n5s3=0Q(u_wC+_C=>h07++ROq8<`Rij!W5O2Wvx'
    'VZwRjy9qbWNcCrYHQqA-30VgFFg>uS;G-JkZ2txh6m~kiHro7B;v$Mm&lmT62yg8KV>y4PrGEACb~j}0Y@TX{*jTq=&ayXOyW30I'
    'O){#>H6~(vc|ffN0l*R<NfuXStlo5m;H7-Ealq0#^)=$jaE#+-W$(?r2NY4X;GbHlp_Rv^Q59Ha$^Z0m0sc&8UwN07&=+_iue>1*'
    '$lFeVRUm*QwZM!aEVFh?Z1UZ+ZAk4o;vqct#50hM3tn+vy}B`^jKl9R46uBYh#8joJtzs0lyvh54+E{wKv4BC!ZG-2V5&I!jxlPv'
    ';gUBn2znp!ge4$sa;YZE=M*(Uh+c{*^DhHtxr4j<*Y=);DH0-W`d2=VF3Tj0{5qKe=j{9^o_8u8Sz|LVnSM1Pd}qX!jeLnmG9*^-'
    '!<@SfjVVv>1N6THwemuCPKi2aDOxQnPuGc{F6D;i5~7Dn0q`@yprKnEU56rK@Ui;+2b%5B!Njn#Py>z{Vjvj5BO<iXL_EG4JVa**'
    'e(r_NXpMAu4ZRMWU@|{wNh~@&>H4)vb$%+9ohM$NFy*`VaUyo3lJVc8l5b_H$Us&+A&bJ2+At*SS{vo;;lYuEzR1_Fl4#>o(`0JS'
    'tDo4D@}MbST8oB_VO@qZ{uJ!1D~2dy(Y@+A$i`+!Qc;xDC9@?YT?*Z|pid@J5AvLRMF*h7-4IgP;D_V_hX=C0_AIlek>jbbxExlP'
    'vFNe5qc=CZk;FhKe`S}dZj84=WSLj3I>1js>^qaL8;c|%*_lC`OMf4BEgpD@&pqp23rQ6Ukf7y_iRH_y=mh+b`nKlQz}tO;%`Yi@'
    '<%52OkNHQcWLjjC1E-M*fq=r(vu{hs9V-L}^*}`HPfJzze5XNIl3(yYZ-6X`b+IMo1nOnNR!vrU-Np#PwI&@a-Qw9E6KZwLg$izF'
    '&bOvx49++NR)hCOzO!!H{MeE@q?^Z|XR`(2q<(neTh>ZvY$tTz+Ij!>q=YLs{Hi~X*&-kS;8oCc3Z~$d+>vj~?7925emgs~`%fsT'
    'mHvEa)Y}@bM#*(9L+<=z%FuD^-G}~|hviYk!5hWnXd+AxG7$;aGtE&q?_kaBq`<$Hls$OtZD_NEU`2AU?$af}fa>|0e})xlj$aRG'
    'Qdq}Wpzi3)Z-Uqc9o>HgRbHDT2d_@A)ABFIFJ2ws?^mtNN69Lf3cr!Vw(0Q3As*g8UdO4*cMLokA;3JBImn^Ibg~?-i}221OX)1a'
    'rzB@npcA**;zCE^T|cM8Df7|No+@~5s%<5&X?yY=S@;s7fH^;G4s!p%SabFRq&cMN6?I|15ATFya)GwZ7l*?Z3-P8qRknU=6U(}1'
    '1cMB}kgTkMgY9wpZ#8Y9TD!U4Ugkf9mJlB>5d8;mp}US-e8Y}>E4V4uT%3wQR7c&v9=ZYDP0wG~W92>zeeLL!VU``N8w_eo*^-Kg'
    'VEa=_0W5UH1JuUU?D71lmJ-!+)?4=pwO!+C{uq<J!IsCy@5d*8u=X&Of=PAkrAAW#R>qlYKysVum8!hoUw82p{Jf>4^AHQ7&=}GA'
    'ru!EH3{5-Zm1!hq43-g>DUT=&UsFoLP2Rm;_6zTDw5Ku(8vmg$DZGf{2#>rqI?JSj9OhVFcQ}$t0q7wQ=}o$Nl<T%Py*U=kG*@rs'
    '9fV!09^hmeoDy?2^u0}Ngy{^PNpum~fCU^>#eke&$7x}G$&zPGJXqm3V`GBn5mPf!iW#;8wG<@!?8$u~Fxd{iH-u+7Osq38UGu_c'
    '0g}R<zyH%y{@i?HDGm(hpN~`~dO_>&-gR=c1Lp!Sa})l<rO}Vi!{D4;(@QDU(9)~Dta|XQQFa!skjrBTWhf$KrHrIe(vg(lOWo0-'
    '1j2h!NJG&90x~uRp*X=le^880X)tL~ek5?06SYP}`B93_%0W?xr*yIZb$2uD+b7i|a~ZIS=T(`efz+{-1la}jyp5z79@vQ5;W+G?'
    '?H(Jc!uj;cvv%&_dik&n(Uq6r=Vf#bPpv(fMf$1{lPi}GG1?m{UBOwo(fV~^ecmc8evbxYKUb{n1Fyf~iSSy^i}1&M-f{;$vQF35'
    'Utii?lBUIU<?{2Xa^w8e2RQc<`IE{~N&!`2jAa_9Bf1Mj&AF&N_Y9+D636RpbzxCdh-!YLBw?zInjn5>Q@TsIih*ER{`X?}3uf@o'
    '#Sif_1l7W_^vKEsO#PlS3(5^*_im<jDdLE5t%9BCH+$<w?0##Cb$EX`gtb<hdZ&(WWkt1>^gO33>la|i<NBH#YM{>%1g<Muo6rj^'
    'CuhFZErODHMfEyPZYped_N}1*!03+H!Fr?>7RA0T%D6a>cEXQ5fQx5q1sq`wQOaFM5!F{3$Gyfj_wJu>b=g2~uuDV5;zepRF3B#r'
    'sGMwQXHG!^rzR8vvKC;Z#Up~pAr9V#;b#!GS$${!I^trD2WxY4lb?shCJdG|`kTeYX^cCcSm39-G5+>8ZoL<hB3x?&i@~*4_a_$I'
    'MjQ5K0ed!7d$xPPrGP81GHvl_VI2L-*<C7`8}z_HUk`siXTXi=K`b34Ta@D$ycB9|#xqGCoVwHFNK?m7{Yh?(CJCv-lRqDvm&+i|'
    'p$x5PLj#%IY-ili9>rTSYp-(T3f;>y<U8C7TkA=;x~7nICWa4u2m^ETVpdS?c{&Ui*#5N{^dvp)Y!qtRp+cj6C8)5=ZsH`+t5HFL'
    'Z)JEFcAB%)e9DE8Mp<U_@vsM?g%|o1ww3H(+zDhO=&FV>PxG2jaTl5-NlM`ys<W)QN1Z12q3Djsb|WwO64*XiU#-az%dt*<|7d1a'
    'T=hf$DffO!Vj(l;E9Xl3Gib*~tB7HdHP!u-fGSJ+wBk{eD0SMg2()o&#(+R9z0!c`I(!CMDAdx#DgS4v-hOL>*{xkO6dq}B4qSZ_'
    '<=_6D_@Rk;Q9qI`N9r4Y4dLdmp6u<<^V1T$M7KQ5fHh2ziHebK_HeR_0HcRy-4lBdWmQaX-ujYt7IIK)N+nZG%t@-x^E878PaOSL'
    '(v}d*IZqTr0WOF$MbeHEu{i>PTF~v8qj+RGnx~R;7gTYxpv@%vbzI$&9FSz)620k(weSNjLu>xpb@7-JrOHof?OJ4vKB|01V|t^R'
    'D{GsQrxlBmJ*V;7@u!j}#a99qVl$ZTF6dfj2!}+WGDsLNdsACbMq)_Jz!^j!6?Sj`8BOx5bJ{WG<3{6=U=?jmeJK3!Pm#7dovJ2G'
    'Krd*1s8H|-fCF~C(IOHQ3a>}tdG!ogu_zy4N;dpXa+0y-eQs}=QJX=>g7ZjwPdj-IO{dT0R%?hq=UaIS?A62c=w5-@7`F}VEbbKw'
    'QbdPHw^Axl)nAru`=)3@CfI$?Lg8*KH8k>iMl-OzK{tGy+?p6%`eO4bZyO_YOle(55Z0&r3b1su30Z|b<!f)NsY<#-f!>GvqP7bp'
    'GIBxWglbtlY-}1oQ!T9VJmY|6*7K$A2XD(etu7)ODMSZ-)txv=$dw8aUwz`G@#ghJ;!Hf$?N8~Ynk*R1H@AhhxsQp^`})JDtD$>B'
    '%w`nYHr1&$1R<r)=#I>VETQ;<;Mg?2d_9E2%(6tT<}K3BOL5jXnL<c3fi)_-`44Ysj#c|!wxQg72xh_S)j$e@Md6h;WFV}~iy|NF'
    '!qXgPpc^c5R#Y6@s;VnAS#C_4Uuj6i@kavm_WbW?gKctQ@+C7*YRF}Hl2q~(Ehy!?chsWeUU%a##3BM7QIOEF*H4+FFC|Yl3KYI>'
    'Njb!mr2_EXHDK7R;YiYd?YVQI!DiVeyA+OqMPtH)m>^ht!W0xe-rP##)mt}2ykcwp-zYW(Ob+y{nG{z$&2I-;U;IDXE@|=W{!xKh'
    'e=aKF-*a+QVori#>)QIt_V1PQT}n?#Q*Ln(ecyi?M%Qao34UI%XyT1Rz{#X=kTv?-?>2%1z|{YTuzLv3gaOtC9NTs>v2EM7IkD}0'
    '6Wg|J+nU(6GqIg~_dj(Px9V)}uJ>L2cJ<<^=J5p+L~>XFMVZC+R&aMV)!@`Knes%O*{3<`*`+|7&UHF$eDlM$h)7aSguKpADTW*('
    'By!JTPyQMGEtF95CSn4FAi7UmwLqINVSDOlgaS|00*7bho1Awx;qYnY{?i#^vfX&THECU?y@!x<J!KXcGp^=gKNP<HpnSiy59uMR'
    'xhw_$@;T}_XMbTCZbMcAWpgB+cpxhq!nwn@!ds{xa>vqZt=udn`eQ9IuZ@HrdOC%Z5wS+5Cf?y!Z&<wqAB><D5kuQaH5Td|6oW_V'
    '7gxR@AMmpeT}O02JP_kq9uqzVlZl5d`E%dhjyjvHFBO(IL<I&~7V_bu9;Wu^h{9az0e(2$`4{WDgfu$B!z(w13ox6D4v74)x6h4V'
    'S~;})L82z!w_$}%V%x@vfj;H>Hrt!XW~ARV51;%Zb09D>UAvyoK2DJm%I#*nx?+8m5glbs3S)TOeJ^<BXDipwG8OZ3Ikr9hUUNR$'
    '1#h>iBafgt&Z(C1ykAm4gC=mZp?=%KrQzhTIR0!)BI>~8yG#G1ssl!%(W-0ZhMJ(Exx&X-vUVlGf8|4o7hzb#X){^XjN|i3DCy|L'
    'V2T~(_-J1|TxrW@u?U<KN?oUJ62Vc*VvsXTmeDYKez)AsP)+8VdDvq<gt#dWc;f${DNy1jNIm1l;CL^CujEZuKw%9Xuee<-ni#cx'
    '=Z1{^yET$t+tYU+9@>=p*P=mX5cwma#@rC#?f<GHG=Zc!n8zmxW3505(BhCPz#giZqc?VF@miGI__Ex!M!LRjkCSl<L~Jepha0dN'
    'j|-BESR0<iOhD>zpynd3M<_nR3&zMLhWU>Vz|~+fueLmVhEFp~QF`tjd^&=IYUC`@+Q%vnrT=;r;L6q9P{VWK8~QeLvmtw+fx@^K'
    'Y>MC?g4Fgpa=!h0m-{T!Xl(t?^vYIKJ~PKU?{-x=E_1d{Rx@vfkKL?5lW6gcpO{G7vE+gBwa4QEmlXXHF7ACroj)|a1%io<#Fmk5'
    'nb%@T*HfOdgMB)X)0;5wDeVK~=cV8UFdFOTr-e;WbLg(aXG4RxZ$<B@>PI(ilbIpICP-a3V#~VV_(<sa`{aD<oZ;j`4!W+yB6U61'
    'XNI!3eSB-kK>Fz5qIS}j#avH<>!wHHK$3HQ4h;WaQyl!^Gc|`-+14(2_##{8LhGaaUscW@`Dew;`MwPJ63zA1Go+&K)y0IYr=|;n'
    '?^EZ#iuc}D5%qey$)uXR$Pw~p?+WRox3GJFZTCU}k0CCxP_XBQt(^D|MB{M}7|S?yoRWjPr8j7O@{ZsGVTL;;o(!)~pqI>Pc(J&S'
    '{<NHY`+y0&va^eO_R*)*<l^rZW(jVldNnO#8Vp}7E^;EH_A03QtGqPg*C)dMWG^IUNdwF7QGDk|&9~P+u2<1j$fy_}*qZxcKhX>f'
    'kp_lB5>aL566-rO+roLi8*w?7p=xC|y0^Y1E_j?J*0m+VIyULLN}t5Xug%e3jtv$L$Xk(xt|Tr5TQO1-=b`NFR+}%Rim_ocCs;5y'
    'K$ovB-`C1lh1{tz%8EJ%M{KiK5a-HdPanC_lJOxWaA;_k5E`cC%|f^iCVrzNSQv=@x-&3H4kJ^TH!ClMVZH<G6Z`hno*+(Zi{S~5'
    'G*Rsdkna^V><E`$tLwYVoXnnZ9Ko8i5b6UQyfY}qVgJ^$<C{;Jx$%8jyNbFssdq+&5N2(FP=4+na-8`T;@PInr!oQj5Gb<gA2i?w'
    'wQ7(+T%h&9<$|dUL0gvc7x5IT45$g<&Cm{td&!cr31N8~#nb!9c<uJnGJSl#hTJH5@9g<ATRL9EkL|H#04BQUy$VtH$V*H967w7>'
    '7+4>Z%3Y(Mf2;qk$q}Wu6CRJe$d(VMivS`n^)fH(qo6Ql{<D+Hd<}zeUKd)3cU8$4qJF#@+i+kQ$~_t8v(41K(VGAd@jm8X2R_!5'
    '?Zdc}Y)l|R-Dc=i%4UwTNg5j;p7gKTl<?r6cQg1tBirh4u0fGYYb!>8bthS)=(6lr)^<Lz2)mvex-*tLFnvZ)RnK;+og<9Xx*ph7'
    'p${>ym)nY}J9DbIp84z4>Rq5HMh(L$8~r2}JVOuEZu{xD3RjkTVqEvRsBY@EPgc@K%E7vnPxcP&H8q0tF|;#F<*19l;#4wTCmWTL'
    '&O1(F0D0^Xu2f#5NmE-LkH}JA@ExVKm1cIg=&HE$(3Vl9!(vW1*ohHO6928ILqv`_!9b9x-s9$Xq%{@3AI-3j<wuTh2Wam(mQL^V'
    '-A#-J(~d{H4EU>I4_b^5Ary11+`aW%Ov_}XrcIl+rQM&d-Ifiik7jAB-4ebNv9~e#VnLZ@l;{3D7MuK0$~g1P-W#W1*YwD~D3=%;'
    '{({_W7R;N;+oS7EfQ=ydW><T1Iyiqd4(%-~?VGX{s*$N@cewEXCdRMoy71@lbXAt@rLY`@xeFjlse8!3+9?xSwAUc6hG1wB0cPut'
    'aKo@*>=iU|RJw5Z;XaZt1Qd|9{0{2$EsF)fwO9y_B1{%7AtO8w-8jPBytDJTg)ORIJ~n{h0Q0|Oq-o|Cw1=)+#P7XP6Q#Y1?3t6d'
    'q6dYFyR-UnSkeEzVx{!{Aown;AWZBIJ-O9Q?^qs>*kYFcU95>b?!CFZXaHC71L^&ygY|@pYhAZjSk5yx>O4eyyv;b$Om{S5epBRd'
    '=ypnIJTMYNo-V}{F;Pp10C<?`TfHt0>9@n}ZS#<9A6Jx@^LO3a>NpIt)<R*q^oJ&KmWz}BzF`MZHym3AMTZWWr)8u-`VDM}bqv5z'
    '2Y*j9p(ao-n`SEH&MWX&-v!Pg4S(lgv1<I*S9gJK4iCbnE<Yf!PM?!7r5=S%L=$q_=eqi>C^d@xpa=0nXj>ChJ!KMr_4+UtHqc}v'
    '&mqv9u{q+%od(rM5QEjUlw#K7lYH#0Wp-_S(|`Yme%`!mtJnOR=cf44bt|*hw!{Sd;$4zrJ+}Up%}3H<lLYWr>WwXc9-OS6+Zfk6'
    'uKt}iYP4m@7Qd4PW!en=J=Nr|;W{?9tX9E46M}dG1Dx@#V`=_p6iqM)jH_O&G%QPdwqcGMZ|@Y!KSO~?^fkH<sTYrwVa7K<?%wUl'
    'q~6yUE+Y75dk9{Bnanuy7CSyK7!g>4a23y+cR>Nh5d*cP<P}eLJCqS*vvs%|cw=TtcQN`hjQUdpCuWPAMlu<ZZXR;rlIuwUjjlK^'
    'u(T>JZ$pA0>bbafhFpl62qUbEDulsyPd^DPZ3H4_pWI1>nyRJM;~GB-xD5OVC|HqKEEE-UhzP!;osN^q)P2!NdIb}BU3dXsaK*h2'
    'kDc;KF7zGxRcR$g52UkhXm$#hl>KcX_|INCpNr@(nsLM46a_LrD8H$nJay4FrItm4)*V%<ChMtq&%`Oa0kCyt9umZ`&RJJDE5bp&'
    'nR1Kytf*cmCIi2yb2%V(UBKS0y#>sc6(ZJn2?I3ny^wiWoHIg94gSu3dfXsQ{jHk>fABCC?3!GFr&nM4_oMbkQJxH!>iXgRgE%GE'
    'jFtX-ObLPNM@FMOE6&vP=DKQ%=k`qp!RnJ)`c0nU^h&i&oe?$;Pg?|f0O2>Q_8_WqU|r7RaGWKy>Z_I?+G!j7X?9Sh&+iN2?4{c;'
    '?P~3@;ra>+<VH}FhD7(w{6Jt~Z(I7QzvrIcZ<TjZ&}%m{$sZ_M(sYmYtF7n!a@N36Ellt(f4uBVJ0b>V>}~+ZTDUP&)Po%8Yw>RB'
    'yUN%Ps+BLlA)8m@y9f1+ZWYG3cc)}P8t4Fy7MOU67Q$Xtlm38!AW6V89|}ijb09~*!GOb2@3YN_{1-f-PlX0Cu*I8a-?Q=BzU#%W'
    'eFp&kXm7{fFHiVUgu}4IijW<r>=b$Q4}|+k>*<OQt<xmfBt}GvSX#!_+Ud+qA(h95U0tkS&WzWp5e2T3O>dCI@_?9+ZoC4t{CrNq'
    'N${?yRF9a0pY^zh=ZxFXd*j8j&;rZnVN6=~Inr~v{J!ye+0oa(rs<<|gRKvr_`>fNT5R^5KhcF{ATirR+?ngdIlonR0=?KJ%xgRY'
    '>8OfP>^As)XL~qoJ>LXD*uh!jy~a1cfu++$8<bm-T1Nbe;Zc0rt1FelF@^ju5blC>D?T&Myv(yS<?KBV)mNla&I@N=dD8z`Vhnqm'
    'aQ2gy(Llb7a+TWiv=y{O)6YY(mY5+&0<208+$28S1)4zp^Tl`znO`RqNvp&_G5@$A9*J^1ocMlilImHE?Wz1vcUj8ERVFT-Fu{}='
    '>TxJH=qj$b#<-KNx!BFJYS0g70bg#IZZOt%$ZZ?HBjLvfTycjJ8o>$li+QhLvkDaFR{lt`pxM7tWR+~w^}ow0F42X0C2gWrf(+?F'
    '<WZ)pQ~rq(=_@?G`)U=#mpqJG^smZ{hh+CSPRW_Lf>XVTKhoajp&u>k8BsHN0q;@ih+X=pQVKhOrEP2t3!#CtztN`%;^L<5^@Xmn'
    '5=LB_jd3Um%XW-smH{v$!i=~W?E3-z&I1kmvDp*+4*`Ep;+pZD?1QGcOB#EIjO|(xvNwU<wK^6wigC>o-&IT4$`$gw-rF4rF7cKz'
    'yLO7sZ+U&P#lO<xhJXN!f0;MFv$(8l^9a>S5+=SB()TMa49NSFx?R80yJAMoEUc<4=Re8F>;j@>ZkOo0TBDX<7M|}N+8|L7N5mi7'
    'bI7Ju^>HAGoecE&_M1#BL>a<07vf~xZU%GFtYtxRZPpho*mvEYVhc;o`aeli(pWf!MggEz6!exIuTlAFwiD>YJPp|$OA{kK*^ad='
    'sORq6B`j+Y&W!<<v^sc$StODMSJ}@hcQ^W~bXPWxBxi5sNSMVg*fENLPRIM-&W!$-!%tuCQ;!P)R{ZcO53tMpL9nq6R4ON9TV8OC'
    '8h72dQpri)BniMLwlb#kzBAT4up-0km0A|^=~Ysw>nXy|5Oi1XpcOTxHy5)TE$UIWCn~D#EhX77A@zyJvxnmh6V(2rFH2ugm0*bd'
    '6zt6ERCWGr&$NQYnqQuGfEE{)pK=ZoPciryH@<C8ROSud5Cxpw-3XA4fsJbcxR1D|Pp0bSgvl19+%SDf4Dcq%mL2XT6Aje(SpRqO'
    '@2_37NwimMM;F<dwc&ipG}Sf<A)n!qiyjHN$*ie3|Ku|Zp|<df+4KbL+CRRTW>7HKWKG`?*}6T`<q1@G-+E}`Xo~{kVbczzy1VjL'
    'NHCU39E!y`-MT@BXjRitbDf+ovs3wvbNg|U>72&tYObI##P+A+*V>kvQ{(sAx|v#^ocgqOHD-3%TQfkK5-s6QV{5*KxtES26n1bG'
    'VNG)TuE}lz^6sL880uRs`CC<UVx&8s<nkLXh2KHNdwEK`+5RB5)b?isT(CN3GVVithQE0K=w}s>*fQ^_85$;>qU>T{r5^m&9dY*7'
    ';0pFhkzZ@6M(K4?wn4-snt5s0A-AXXu5MELbyj{OA-e<8wABFrtd^Az!Z`hsk#-R)lM@|8>RF-Dd5CJsS)gSAp<KgB5%~<1^)a$<'
    'V49mq@c!0|la)Q1m?>1@x>B^g!Nc+8TrFRlCFy!aR+(H`1_^A`f@N;@M<nh`e`t{t`I=Lw=*M+d6iIA!u*mNkc6g%vzCv4t1s`1k'
    'T4okBLiDpIpr2*HJR;H4$%Ala{pu^OqfbjVrW4OAdy87Wl`kp2s^;z+w6E|1J%;Q$lT<W!DP}8quF$C__%<q9VJkXkkkF=w>f~hj'
    '^mSQw`x_u@6duVjKN7p=%(wQsfud19Jnif-lo0=#I|UITisQ0S5XdtF=3!2nH~$M*IEXD9I)~4lB-?ZFjvb<$Y+<ur_aTu*43ZBE'
    '=Qz+_CA=$N8<5CC*yIm(4V?YM01SQn=hFJ)eiW1AqpG0dfUrBZOh8{-IhimbY`c}hjJlqckkripI2Di#;X#G_{L8tcPB|%fl*nZ~'
    'h6A!u>VH!+RC0P%Vbi4y`!D!$uEp2QCF7440@g#>>iMT&B&tZKj8oBpxjT%3TK&p$pykOr<JTNX1%!$l`pP>2Lz7IkuQ;}gff>1E'
    'GW<C&P?sSciRYJpm@}5~x$dv8$vKL6aN}E|t73Zayvym+6FTfJs|!&`O$o)3wPjT#LQ^Bc%-6;WLv}ipv|Ni|(LPl|mG8t&EfQVz'
    'f4X#$LY0$HRkx!^$GIc>C-={u^1!2arJu|u_kV%9_W70%z#dn$5DWw0$iO3w5GwWP3Ij>EeN>pR>fTs97@x6nidIz2L;@m#&{$$c'
    'RzOC-{BFKLgIBv)eT3`TtIde{v;l{bbN{!h(fhsa0AL=;qii@5lP<!r6l?Ur%Q6<=Dsvh7TIs?_YHe$b9K0ZDJ$&q;bVk3uz!B}z'
    'y29OPf-+;kb0e`Eo~h($GvE&qd55ozn~pQ8M92(U>^pCgd3`DEx(%j2fcyXxJsn@L#^QLs*b+=5hw*_bx7ls0qp&jOnOoZx&@Ime'
    'RP@6wPG4`;nHG$am}W2lxBufc1a%5{lJ82Rt`e%^&=uFPXC<XFn+1UZmBPI68QXKA5DdR25LQtIRR#ucN_@kH<fB~ltU1R;Hz2bQ'
    '=dwSIf@{SEKD%FPTtG^WdQZy3ELF<<vI`J)gQu+W8X^C9bth}qzPYz_w=nt#C$>s-1OP@TO64NLDfP{@(M8OVwdf-BvdtdVK`aVR'
    'C4d=j@Ieydqs3l%j_X^YBt=49s%s~4CX#iwEpAwthk5d}ER8yFwVb5p-Ek3E2He(^(ema4P`kH0d|pQ1F6_o`Zm~3c6in_v5tlc2'
    'SfS?&`MYR6b4v@Y9mR?!EI+nz18;ZLQHtTWj?(Vigz94u6Kkn~><%{^Dz$HPf~U)e>WihbLsh#?EJr<Xl<Av9J~KvE2xH!h?=fw?'
    '47W{F&;&e{dAe|QUyH?)#r0IKpwS4!s9wxr5x88;wuFCC3q>}NJ<c)te+}QkRk)@+j9s;qCiYaUd0~pfs=3|~peaNT&z7h0rzx=H'
    'Y1scY-x{iQw<Jf>iEFk@DU(gq^E;}Do^pFMfNSeBT)$_ChFuwxXtyX4h8o*4{}xQZWt3w7djNbR3cvGCn;RhR6b<dd#aBdbiu)<R'
    'kfRVbOxigwT<iN)Z;t!M`H)R4T2S0jsfuf#7)w_miMDs%>O<a#KL>Nswq7HH8fV`1la>tOQn=O%8IsNyBaG*^+-1Q@YhtM@Qo*S3'
    'FTZFb91?cWJ9?+d9%g5;zIb5h!$a}FP&QMsvas^tj;sLw&@)!IAI!UGJmB?f_e=Q`Z%86bw+=zo639)C6c2wglslpC)=#LX9uB0t'
    'FkHGSGJ+y8bs3TLzb41SHNC&u@YCn}_Dz1!d>G57ggn%D>t4f==cBM9`8&Vok}c><Dl(4AvyAv_T~9vFB1ulJhyFh2#(DpWv-?!t'
    'iTm9bK*S~T@tOoR3FG2S*a6-t5*1yH&$SJYi6%&)pihU+NhLf&r}gz(3qP-ZSaM;8mZ3wfxpa{u&KAVZBhEVB^z6S=Uvno^H`!lm'
    'tS&|wYqC(|?|@dO$B#Xfz#`Yx6F>UH<YbHJAT~?XbUAJ7O1ybMDljN+LC&<#9r48_Tr&2_9E*9Ib~xZ8R-}bF3Dw<VM(e`*@MMLf'
    'jfF^RJ6eHdTeC-D)S*1T>>qB4fa<$^_~7I2n>wBedi_~{xeQtD#zeBdpQGM8{nY$#SP4shCW28&fmLB<8S*uo{MC8mq&~@1HR~+n'
    'M6^-u?FOMIe*;v@Vyi=P-Zd~t#V**VVfXTc$ozGZLlATskzRtK<uPpCOUUAF%o2Io_Ar|_CDudgBLkico~NS)HI;RQGf?4DJ%^Mo'
    'ytOoGVP=eH(CusOojy^+kkCvB2pgaa+0-aj##v+@_8kPjrxAJHhd`Nq3z2NZ`ug^PBHb=(Ym65^l6Rd0@62e&6x=<3Oa4`2fJ-y;'
    ';ZJQK`Odj}1cNYDc!Uvaj^Agve0nPLj42cQjL6Y=fCLqWJ`$_zj<s09s=CuHGnQ$Fj!0p1m~Cb=&}f<~=~n30CRPt_#b8!{d^1T%'
    'n@7UY0h?C9DziaU>+J6V`dyLWSdly2M5&cw4?7pf6e9LIgnMBtncHh2LgOMs&hQ?o*!5I(%wnj`FW+MBdDmQ5L#5TB!V-o<o^wPK'
    'l{HQs>qx=ZojaP)^;Du^$;NDkZn3L3%Ne8i-zmtqqZSE0EyV&Nw-Ru>l(nyhMxZ{Od@ED_`7moh;fYR6S6=NtdZ{vMnOA&Smo|xX'
    'j^QN)-E=Ct;+3_;yF9^4u$*UnGL(2T!23-NVhA$;Wj(%>rUUf7>8)}(%wCr?bm{Z5F_d6v^1gG5Dxt58Um>}SsTcFp$gGqSL+-D+'
    'g0>~5OQWjj&hew-vOsjp_gCIXS!Y}eCjQ;fG8xXZ;~G{3oE>#OTEaFAy!=P8$^-GQ<lA8njw+uz90(@lM^+)8N_1)lP3(fX6~MM%'
    'UPSlM<42y-xVXOL`a7**{!ZyREu3+h6yzn>m&lHmYY4!AR_fkdm7swOi2)!qWY~oozWw`E0usFD?iw;iwu&5BQSz@$|G$|FtC9RA'
    'Z;~d5F+(qFKGjj9sCN%9E|A!I8Ey5&!KH+~?I{$yk;1hVaCCX4aniiweDH!uo0-CqI94);AUgXHbI)X74)tV;(IxAI%Aj@oFwN5!'
    '?7go9$oJ+3f$Ow)5U%aLg7|ge9o5`|f$Idr^eFyEMBbg7w@~q~44!LUrSZ%HG;#9Zsr=TR36`mz<O4e*Yai&2m6mbajQXGay<RzA'
    'Ymyl_@JI(A!#|nxO9~mwehVnv&p5Ic_=B6*d%!h04DCf8Y^1?6!6w~pUYX_Izeb=YGAAJmLrJKMu9?}AmUJm7#ZIlYXoatw-8wa>'
    'u=YjRpVxHgtaWOSH7oOPM4#RQhNH6cro8%OM%hz8kSDq3sM%NMotmvIrBcmlhu@Bb$2w&<QSp>5WM(lQ`)0boC9}W0yhJbKO8#ZQ'
    'uNpsiwWZLx;b=$?Q9t<r`NTXGXKP~?#xU!iivsmEMln@oWo&%yn9&~ZO99yG+MP>OVFSu_XBb2y(L9OmEPt~<sqZ0(<&bxf!y}qZ'
    'Tr2?_TE#h-K2S!3z315PQA_7fht;;kkQ4In_*r9dr?NGILrqqC_2ilmTQ+{1pJoYa=PfoG1-^9Z_S1)T7yD|m6G7eMEOy$VgIvV('
    'tp+L|64WGrOR$iSsO^A;O?SHAn`JX5&mZg&xLSXOMbE5lVr!;helv>8#J5Ki|90EVgIHVDE<Ca${8+i?bv`}|@d+IfE9O86=V9{W'
    'S4XsEZ{2F7=jkIV{8uT%nW`J{Pz4YS{Rd16N)sjbkGPtO64gjSK2RflkL(UEJ<Ozgqjseq0mFcit`~Kq$k$3|O`ukjh;Qo&V731O'
    '>T*+=!jcTFDz&tNNi3AUm(i53vIZ&D!1aAavnnVUpfjudsQ!lKIa&so5(0oqton1eE7qjBKPW?D=KQ_3kwi9RG#_sg8h6@SY;}Y|'
    'zxQ@bx!G2`V3E%TFU<iNlMTnW46mTLZfyBYJo3M>nhF15+yf2>_!MGKN(s{kEk7^Iq12*DS64GnX=JWb;~Zj8$j#blbDwtCeV6*S'
    'Wc>9tQ27w0;mkQ7yu`-!ANk@H2j%v>yGIK9k3dYY(~2ovfAdDA1hmW3vJfjgdCPp!od`F$ec8n0X88dAMLmiex{b>@T1w2T54JLd'
    'HvXzJc+a1@7-m-Va?1K$X{k<wd$X_4`1xn!p0E7Z%6#1nqW9vwPp=@C;6~h5*$#oV0Bx-y(p4C+;I%#*8;OE?ij-`QksPq`L(RC8'
    '4*-xWgzH}s01CQfU}^`uG?I3-A+GUc9i_qfkhnQooy0wPJ`!}(x}K}&Gefu=PsO&|Ryj&-h3&eRap~SZY}UaHT5<f{U<?E1>P>*W'
    'khQU_n-86_N&9=$2ouC?2nuhS$$wP64kF&k$SiF^+9h|7m!6E#SG?0&z*y+xADzi|$$w=G*%;Vjd=4`)xEE0mEO-2AF20GXb&Ns5'
    'loJ$v7&C<-n!TyF?OjSpu2w`R%TSunEOc~zqsHNsHqt)A$;-KpJ=CUXdJSiTHJZl5rx9&cA<qzj5pETxe`gTLhXqipFi=IU)_#~X'
    '_2eRelM1`=A_K>%b|y{hch-oY{nZ|(H{#6Yr{c|mNty7Oi8g&OpF1mt>1jF&1Sd+#e~_vjAVq#W%hN~e-4oL4S#e9mN?wF?QB-{K'
    'PG5)65xc^~ujNFM_<K{TS3JP)Rd!c8`$+xA&{~hJ9dx=W&I$^42OhiYyA1GpYZhoWyKdbeRi}&--CMdI7E)un7?3s-L6dOtlrk&`'
    '>h32d0oRqIR@!z!t5UKbNbNN{$Zy86Hw6*_+-^BkOwZhcmYm@<!EkY>@3Vc*VFh7fdKpfAm2_@2{y6JfP!ie&4L$~+Le^_q)(~g4'
    'AMi~R(XXy<cKx7Xm8#E<&_5qBOqVw4(wRS}e^t>`Iqj4Sp0KS9|G-P7;Vvtfl1~)aS@T*yI=B41LZO{e?RbtJ@qHS9AJ>&9q3{y{'
    'H;Qs8Dc*8x>`_q}0eWbn6jYeF_jF>K!sM4x1p>sZPNJbTj%BN(zCj$3w542Vy;zx<crx!@@eARSm}!Y%pB0k()){RCIgxax92?ie'
    'K0EVySRh=)N3?AtI9aM(nZE?N9C?sfkca1uNs?u!%}#UUyg-2-4G6!R<lremyTX|4k!#T|B0tK{)eZ!-!pXjk_Z=0Vodx&QYqBoc'
    '8v2-qgY?@vn@5o3TgV>j&tyrzJiMfFLL}=v?Dn{nlw<e@o_I0uU#1>qaX5deJ-Ux)iLoe+{a6XVccwAdauQ@@q=u!gE>HYfT<KCu'
    'gBGwk^uZ5f4gaPNLgqJ`GSC&tHaDw?qyiMbE{n?$ihupg8>T_Yxfg=$F2LU+fvwuL@Y4HFeb-t0)UG{LJQoce-~Ed*(t2?#yI&mE'
    'sWSS!Yv;8mcsrw)*29HVDa>Jhq`BCAA8Z`zQl9+QCAu0nXEZR>8hH%qo!mbO@|q9#Y|x~7<{3vHRuvpMw%1)FJl}aGpe|I6Ib!LS'
    '5P8y(o?Yu;So7Z_U=lcx63wZ7Q>sza{Kr;_#-S|=le@0cK2*7-Iby=7D7&`94S!x@N5d9F3865UuKldJ0$));;&Fm`wdYflRTLom'
    '<^3v!-3DJO>wi<apLX`9Nu}jM8>IcyvDQi!MM&7zEk_ginahUHP!EaONfzqC*_f;BHecB-IZ6uEs<>A&*MO%hnFl)QW13IKT9Qz)'
    'O(mCC<6Sd=Xe}dAFU?BB8Cx#{^Yw3$?T^q1Cn!z^<uk4x`7E!Y`>YU5wDIA+@u)Uiz(E5`vW4S$?a|vd6|-wcv3!UwZ_wX<O9+hO'
    '7v_c9Xs(ScDAjBOdKW~+2R%p&RGssLH~C$aqMG-{dkP|GLgAb+?|^O4ekJ$wzOT4EPC+TrY_VicYi3fra@&r_`RUHct8@vPI<?8N'
    'n6!;+U4kitT0%P<MvA1<xEqmf`&ad<W(So#4|J(;Bs}UFHM$7)s1T%X!j!jNXwRRCb&^Awb%GGRFoCrKSk_I$zWj*s=t58=DgB2V'
    'Y?^!aD7r`Wk_jTdS%SBW4@C1QG(-w^9VMM3*goA()5edRwf2Qiea0GdDX@u4qVV5V(!2v-I_@qV_ChX<5I_2Fz6&}RhB7$T(mBf@'
    '7+@NQfg>r|aSMlJWMUS>bv9Gx>wMVPsxO|Q*oZ{c)uyFTrkYI*;^5mOPr<JO66oK$LVGkr>nFF=fh{Zi>FJqTe3QJ|v1-V`#(0FQ'
    '1f$wjcs0Qq<NzgaHB_$anpWFY)F1BqnUo$?r-~DJ5IQ*O#H_Ut>mjG?=9hBN1q^a5d%xZJyFFD#j>98zd_H!r@_yY!84K>-I;O!+'
    '?tqLjXagL{fsT-eE0<pkrlXF*3TjXMf<qLrZ^tisvqO0oYYEHV+h$yS@COwwc@+t-@G@Suf0rRnq5iIEQ_-24QM7<mg5L5Bbj`nk'
    'b$SbZv4KIxbsQjAp6s^`LfLjepRb~?)2ToHa;!AbC|A1}KHj=w|8XGLMe#-or1`JOv1u(N5ilBPCkJTL3#$A5j0y`oaM3E5-zvyz'
    '$sqotcSCsApIGqE^p&-`@mEscRvjAV+J%|*i}5rwuP#r?a9{$flheH>YF2afe}$nj?p2Q&=T&a~tS=pyh$`)Be$4D!x`q<*PGeXX'
    'VaD~ONo4C>*pjQM;cu~{j93K-$Dv8a^Ha?)aK1zW+n$?zASZw&Te7gApn-$ci5ck+YB1*rVcD1+O1hF$h8<59nNrhXi%D%Zhfz<D'
    '@ab&9#cSs>hS5ct*%gNM*hm8!Bt7=2NegPbxE*e0!`=b!N}$%hiC(JdyNha%MVmTo@KbG0>ORpT-XN}rox(J_x`McQ63IN0i*KcH'
    't^BMJP+3G?`l!vtp=+~5_07L9B(VjFpAbQ5W`fFP;OZ(7D^g=7Qkg2C$#B++v)WrMK!vqDB%9Le4okbDnCX9(P%hwWXm+?^gD05)'
    'a<HfomfXC@>oo6qz)H5%P+gJR?RKMTqpl@X3(At~hO8F-k8kMa4t<^BP)x^MgILF2h(n|HmIqo7GN}?tOi3N?4v-k6&=~?wkn?hm'
    'u447w`c#`F+1*<Q&!N8vAmT9ks#Pbg`My65yDJJxJ2%c#_<wZuW(@~ef7uZx)$%T5-MZDkYlap%x8i*97IKmwqnX?Z*#v~1`;r6P'
    '{H`dZl88-l$J{NTk~Ka$AKOc2fBaJ4R|jFaC?vWyg*&NL?cRi&lbi+|3vbs1O;}KJ1}Ut0ls{Uj0jBWoLI$?A{_(ol%yCQ2_x1Nt'
    'AI)Ys&AX9RLJU)#Y5!;(Y}dna1~_#!JtvGW!noXXj5sy)c|~U?E_Wmri~`0=XRCzJ1E4tB*96So6LUU2<s)dvo7D3&e>15R*F7E#'
    'b;yifuSzVv9!H>SfY4{WfW1{B7g1XGGX=%2FQu*DvBVBY*%_GHB-GgUg9Kri>RfU6Cpr{Ek`|oTI5nPiiI#FoCLW*udBC$3ax+Bu'
    'g?OKMOMXV8DL7O!bTN%Yp+XskA$o7OGqr9+e^0T{breqWmm}D)j1dA<UIlV^4TG(!@&pnf*(&0Z)MnqY4-r5pg{9?D9sE>u6AUxl'
    'Qz$XA)szt}8?lpt)l_I_&;N(sFYKbB{8tWUs%w{jJIeneV%$w5CC;26Aa<PpKO*M!e~FkKXY$1V5V7B!|Br}i|5r12{BI(Ld9iXw'
    '0v^%=Vmitp6muEzAc+4tcU^xxHy!Hwk^ZVQBeVgq?NfidTo$S|todR2;QDmD1|;V*0p|csKNB~OPo7^&PRNIVX`wB^Z=k^^)4l&i'
    '_B8a>>-AiZ*1OQ=tvm59;P40gD+C}7lmi|$yw0nAF#QN=8GR9V3c&+Ah}(DPguVbie0@B7?}Xn{J$tu+bOAKMHK5}wgWv6uk+l%Z'
    'x8tkSBlMl)Gw_C=_&NUq@@?&*{{gTCZ~(G)y#GNy1FZJX0R6w$?n|C5Pj9!OKZsxUUVu6Izkn-uf(6J=$X9?nz|@bqKO;~A*!<0P'
    'lHV3T-#-P|15*9uzqDVWzn4G9zx5voE&j~<-G1VJAAEznsecCo-vGb=hllNYFN;6QWc~0g6{3Rq!khfY+ncLadO2hI;{5WjHzlgH'
    '9^~yvZTrU_5X|dwElbLVbX^Ct@Ifx?=%62VdD@cwU2b9)Kg5jkTJp31y}FfgIw9XwH+x`!_dX<OBIC!lDqI(2%jB?J38g62)b?8P'
    '1hMzkszGtue84X7eS|pBaml`(1_cYNQx!(h8F}nFYpTO~!yG6h0X@dcy0fq0_C+P}o`X`pH^Drw;Ns-;?1Y2wbsF1Gfkah|-AZn5'
    's=2>Jc2Og%(|7{QjReXO2yRbF5r^^RnP7uF3R;UF+P_5%_UGU_g{g;I<%AD7sFN`mzHptixLi+K%#B@dL5Kk55V}U5sTaQ!t#ItF'
    ')A25qbA|y7wb$9V!U)J5;oCK;FMb<p^UbK5oRx(A*{Q(5RQ^{61ZIG9_;ffL3@4efVtLD`ncBNsZ>gGNt4}@KJyp%gPlV#Kz*Iog'
    'uN}gc^DbXzA}*be=l@V6R)Qol7|2n~v(VM(6&^Vebr?pSV^!b)s6(O0l%e`N)~(?}QFMZtXIXnf7Z}V!W#HK?nZi6lZH?R5A(&tx'
    '8ehBk4-cEP@=>6z9$DSwE_2Sg*o$cIu%d3J2TVbg?<Tz79a(m(8G&Eh*W6b8+!<BP*_+@S$`A45)EYKkb*i}}Qtb#-MUAbp(9juh'
    '^Mq@Y;OcI{K;X>Y^(90yJ_nvMj`!1VY$<IS!5vnbYSm~kG}npavhqj4BEh?84TYzP*QUy)lVIz9)^o`*&v|CIq8G>O1XNElxdL}r'
    'zKq^w4(Qa-)bzb41)FJiUk}{=gffSNAC(h>8W*Yz065tZ@W^fru{XN)*V7yan&O)QzeLg?;4S2gdFoiHs@l+u3gqaSH4Zjq0;+O9'
    'n}ZZifq0+pwHbB3RbmYX7G(9PlKWGH?VmGdn&UFsgFb8#Chd&BUql!FJp{uAtItc}lX(O-S#-$TXd#p=Cy58Nbs}b1aW~Ig3X?Sj'
    '_qnTU214YN1kS$u8$T0|U=AXEp6D&@I8v-^Imeh!<ZF5qR5wno0`!M!T7$|s7L9@8{Ly(WPXbPF(spZK%+hCaq1#iSM95;GrgJB-'
    '*pK?AENI|HR}SsG4bs^i#C!r{c30lJb=7HH1j5ddQqSHvU}%oNFvGPuNyho5%LBpmwQfF0{vm*`^SN-*xcxWss1kC!(u;mbK#R2j'
    'wYwVS7d$SO1)?0^WWM+XWd%WX4t$|8w-_3POaR{t3yXro{M07&8d!X?2d(Y|PyfwSPX+^2oO0_jZ67+Mg1IY+BjO(GMrky{m5-@W'
    'HsLdJze))dZxj!fsctmy+Dn%1+PFS=VZT?3S|Na1mLL+BXYk}wlI%xWicutOh%$*P>NhMC>c7NqLSNuJ`MH?Cm@ys~EyvqPjezD<'
    '<mL-Jgk-eS9q96bg=t1BVT1|6ob8S5>E@dy=BY9$CGk%0Bq7gN`L(6RlAsRP`Pga<cMNxk4Ci}A4Ufm!r#WBh^}!M!YfO5kxwZIP'
    '_Vw6z6;G$i@s5`8_J2Fz2dH;D`7|~8B|Xc`1=-Vg!6tsa!pi^8D=zMMhF0AmWm5NNm1*qX;On$u%=c2f5B8Y|HKy)<7cviVjUOvk'
    'mB1DAuLd8LH%p={tgkAw0U-prbKgt_vn@MT^8J{*-IQxkUDzIH0}uTs=Kf#FG(Ub)S4&#YliHfd3f;KX4oExB(+t?=7$L6Jm;Ct2'
    'YJ@Uvfp|%oq|yNrEtbW9>88p)P~7yd$`*tPe3`%HS9;k%VGLnsU04gTwaoWw7B{Y;a=)&lYwI1y8^l~jhbphXMdAh@FblDiKZvWa'
    'CK%E+qX#qRI*v#6(Wq5}FU`5gzG<?RA;;II)F8==x_o8w!FtVviVLpfCAL+Azz|r`p<BT3!ppZ)&mYo_PLLZt8j+Zfi70N!(w~2<'
    'NHBV?ev-z~_miJPC?T1zw@ay2+#1(ryiNa%^tk?lLYC}Nbe!6cw2C%@!%0~p3B4e;a<8x(-S+m4AzorTCj!SFdyg~h8vNKF)0=6n'
    'iMr=QQWSPvr&Dcur=~HT|Jz#r)8)XJ5*vQE`B<MDrzu^>9gRYJx?3-{mj23mMnt>gdaH&^+{uTMIVa{53*fhwaEqE88ubd^4vh$|'
    'Bg(_;D>#X8uEZvRgvX=%&9#D83H{o+e~%6i(81OscqVwIaJRw9rX~|nVG{$_!?BX6MeWr{7DqwAcqaf?r`I<2Sy@1@Hiwq-fq6=)'
    'MHOlJBMU;?fka<*xKy=0@Lzu8e*kM(G`%9>EC0M!^vG-%)uz7A){b}@7m>ddTP>JD2PP<VDl_>Yl_|4dzOLC2LO!=)^q8(?5hfG)'
    'bxbKHfYO2*2q~&GPiw)qI$LkKpKiXqN43_u)Ayn!IPkly+rNSuDk1KQ=P)L`PKHeJzI}2C==bEBl^(MaII9)>6I>G>b6eH0Ch>}y'
    '9^G-F;+IrjM(*!x&`q$H@wmbRC<|%Tz_!-GkU|CZ)Qo~5M*$uWdoIz0cbc8YNp0bM>u=bcmH8sP0$yuc46e6`;WfE(zy~y9iW8Tz'
    'qyDsVomi;wdiam=@%AEi{*~>9L*KH_Sh{7P==QEwbuYf}yvjojjq5o=#A<0Dd0T(K;A^NXa{CC#36Qoz1sb_oFxhh8;>261p-@;?'
    '%$o;~VjYb&{aA6jrxx7EJvG9bhpwxhzHD5LxCscw3>)7d8h`gGemmk=+mM>^)khOe@1>o`1BlMJRY8s`*`Wm(DRI>jIgsnWRPB$O'
    '+5VuP)Ea_5Grp|I$7cdX-+nh>bF1ZHWdSDXYq+3hci_TfF0P(4=FwVcaj{Vo7Q9_|c4PK0-iN9B+>AqTFPTNto3I+1uoY_E=VkB3'
    '`(~=x>KVL+9c_M@5XR!Qz!j*p2dccEk5waLszByNo7=bjcq}eG+K;MiD=Yev*PZsZ&YO9>D`!H;CbO(8PHCsrXc)BBTLUo4d7s^;'
    '&Q_tDw`fTymJI2f6`)W9SRlqeRg_bvg7;4U*8Gi!@KW|jopR6Oz@dXo{-opOs^@L_3A+T!jcn^?4i_LW!)8*@L+(JEk?XC4^&7sf'
    'XjmoWOP}*uoh4=0FX$w)D@7{1EtNhkiS+d1@vx3r1V{S|PTg_@T&=|`Z9SXUW~|{jtBsHZX-QVeEM3FG!yfYM>iZ<C^_{v3Z%x7{'
    'RDFx(d#%{Cs)GVDh@U^q26Aj?Eh-l9?V{Yt;S)<3KzYXIY4R?K*9z}9K#bmSCN39Y{~dvSxU{Y$W4azd#blGn=Y9+<pZg+kR~kK;'
    'DVWt~%lX5QOE+XfQ}o>l)bnrdn%Kj{B&K0%0~g%1%p(m^-*UD3-&n+1Am$+Zidf%um35enBfW}=DBgMLF5UidZ{Zl#`zNzlN$^<s'
    '*%G?s!ST3O-$qfkv8lCXzs@?0!)(U$rf#7LSPPmzpijrg87j#8N-$*_k<UD1bfP9xNyNxnvMvuHa-SIdfReC;AaI{vRlpcf3KU3v'
    'OFNk9ZcXPm8K-HM7H2<wYJ&-pH67JwHH;IEH>hHk%#{V~<P~Nwa=_hEp+{TVTxs(+-C_T=;5Z2MJ<c?Nw~h<8Sa;af3i~q?XQX2%'
    '{s|}F0?+BelK%3IVpqQ1fhOGOaR!YgDWGV#xYWQJWt>H1hX4bo+htlNIOS2ywhPUle&dwWV2tph_-|PfqgVnmU;}KKsPk^r=bXqH'
    'eoX*%YtzhN4<VDY`?>M~1~91WxQoK)_kDoP|2T#TF}t%^o3e3q%0q4_25-E{L{~!wqdj#=@ysPB{Pn5w{fIvk64$ppVIG-~#bQmk'
    'vhQzyK#qWtGt3DMDmHye!$Q`+HW*+Q%tl-uiB}RlIfKj>`Td8so|cIWRwptajM}wNke8dE03GH@g(ftBCJdqQ*UvmnCHC=}gVu<M'
    'GT}+<3eJBKsmpRM<bA)E)9Ygm+>p*0Lh$OGHKV^t<(SU_MERxfemEYBoN%1!xr5=MTZx92*{OU8HJLmL1fL=@bl+)fZ4-8R*HD>b'
    '9j@hZcmq!iCb#Jv%~h=RN&9A_?X?Ms+I(0;yAj}<;*NOg)14XcTYG{{ys?2pA&+E8^KU%?%7inheR|~EA+zZhkAjqFsCw0XF`*-t'
    'r!gpq1f#k%9WOixHAm|_o2WUlSY=|!+B6<7>G%f)*xh(On8pq2F!rr7v$}}?^GJ&t`~205BA<>RYHG62VtP_|l%Fcx5}9#leKo^A'
    'gbbT=C4i_SQyrI>4ZYLfg2>s^cvJP@%U6F8Cbcj3BIC^WZ>x}s0b4Qza!(JO^_9;Y4M}CjAbqbczpJLNL{=8_;ty_a{CC4Db%Fo%'
    'GS=;Izuq)t2F!(SXM^NG3p4Y1?@<b^s!IfkxL)*a7>(3Oi0Qyuk4H5Pv~5^dI|7a7B6zaM`g%nP!#~yu6d}#n$s(F^_Rdpib!wZH'
    ')<U3aMdXHmHWut4vV-(AhUcB)wQB^UBxGDXkAyr5H@?-LuP19}sVC2>{{i}QqrLL*@m1MVXTx`zC&i|zcERX#YEpFl9~a1QTJKUa'
    '%Wc?Dy}*W#=k1lSZs3vzI*ZyLX|SK;Bu?_Ly;PE;AqZ{=@?ZMiFe1XE`FE5}wPUx(Ezt2L-O;@`6+7hcUQxjE)*_*!Hlry0ew_nU'
    'a9iuhta0I|86R4H!&_%*>oKaWHOYaZDHYythpHH5WI&9(8MQ@y^m_h&fP2BG>HRjimJ<uXo>Mzba$CirxzN;h3%`0|8NGnE2uL3z'
    'TmfDM-Bw(O<YUl_Oh2C~c*kXwt*x~EaD<wr?}}(T<?(?4{&K#1qZu}STEfzMvyXWQyt6MRF*ePI=Nwej0Cn<o7RKdstdUG?qv>25'
    '0VT7<g#1%f*#u~3*1(U>P~!56NpSS{-KywO&R#RL5AE_S47@2_+14{bS<)XxdmVL2rESAgmWx?&{O+>~4=mTXm|>3R-wl2l*=whX'
    'wRzv(0*rmgR0;e?@92!lfh~=!C82vkp7Nx;->HP59i#pJdv|DV3K*wbUE`OUu|Q616G~mW)rITn?CU2!L~RQ^Fe#yXW~SE$LxE_='
    'K`y@p**9E(RMZE?xA(*it@(64)_L~vID4THthj8qtR0T&oPr|!^Gl0;HyAzSc7qclXQdtiD+FnNqj6X{Pl+GLK=g=54vDw8!dbPG'
    'G=A#?GMfqcoZfP>(`;Hq$2H}={N7XMYE%U4A++>dnQU~+J$hg9sXj)<h6bxI$Rf?H@hdW8wC|s7*Vjj1w_FKiIz}vs5IWE#e8do0'
    '{Fj#}a{6gZ%I@n60%RTlSG!SDU(UY}svz)qLO+Go%3^RKnhjZ<k_bI`sMnP2GigK%NPN0YV}a=nPHWY|1J4R#1x%fpYIoDD;Jqt@'
    'oeQr+T9v1>4jWS;q!gjb(`~cl?Y5&1W`R79DD_e7D~Q2xUG6!k+AuuQ9IF2BHvliAnP;X9C={1OCF?h8hU}c>%#w_E%Ze}J?F?&@'
    'Rx&(cyh<iQLRExXU|)!Y(1_2&wC2N8vnh=DsIVtsK27dRt3vWvHWZZ$;UbcR8$A66?y3DE138RM^7h7b^1{B@57=vB&1`kh_OeF('
    't(;qy16}Ew_%*Y&M2^D7@c_=i#hJ;w*r$lZ{qv5q66Mv!0F#QugD{(O<u=-%4rp{+u$>ImDxc0rS?D;qh}K{QeE)t&ZQ3F{C=v|u'
    'qp2BV#QTlkPTE;pOl-iTbjuHFKg+GtZE70(daDM`)AihvXL=;|V;kLQ6fpAV--s3R#!y&Hjysew_dt}c<MgVFy>NX~fISF-R1E5j'
    'qc>)?1s+no1{>?%S$;uN9scGt1na{fU!`fdi^u34Hoq1elV3`%e~WALh<d5x;I(XUiai-8R6B=$L)B~Qm6jUkU0E64rr1?f2EA)S'
    'ly>RpOEY&`18gUFIpDqY?(C2+-*=gPmz+*=yC`^6K0bFi!WTT{>Q~#NF{U=Agnv-?8%LkzGI92D&!YCy$~@?0V?KSU_y(xFzx~{b'
    'QS|y)%o)mZ#ijc?Spte8bvja_;>N&O4a@HqQ|dtY`ZhZOze`K4*^`8X;3t`za?PMbIh9ROLyZv|uor(Q+4$hO_k)FZ`6GX3LqTks'
    'u`XRk;1hqKm0HcJ`(xy8Sy`2j?3YErhQTkZD@Brl9qsfUCc<ghSC3G)El#TONRmt=X{ZCT4=J8(P#B_8igzLNcmDE?U&nGHZU=X>'
    'H=&`_wyGQff;KU7iSj#{If)bPN9Yk{!z?!g44C!aTBoi8_IPU_6ppK#-qm7JAaoFlvAj~qi3B`8q!)Wg^2uz-*LN@@bg)+6y+GDl'
    'X4P-0E`UwuL}XaXM;}6>Fy>_t?yk4@$cK+mtt<AShg#XyQ=J6W0dy%n*9qBDoM9E|^%&_|XUPlH%`Vk;PB5WAmhf6S>Ek;AZX-+q'
    'L-g}jgK*tHzCFA4));uGZ2R)$zSPpD9}&M#=uvo>-^zF2=$90&Dm14(wXLz}B(dqK&&QMz4X~g;cM`=WA2@>AN&?eG1`Vkw1~ipU'
    '5MtoG{qujaqk0E>7)9Y2$}M&;)EeO?#w7+6)w(EZ5kwB)7cFkmB9G`8<vq!m579ihIwQjQb~8VD#f}5x3we_(O%@V(wt0Bpz*v@5'
    'P~AEP&!gB-!f!_l26@4S0C$MW&HY@LfwSpE2Zl&4DzVJ{LGYTl*A@5aj7e+R3yKHQ!*q%ecy*P@GdGyIV%+8xmo@~yRPF;Up`$i+'
    'jK(@zfz{k^cA;b<@Fi!WVE%x35`82%BZx#2o_C433m9UWZ|WktC`mtB@T`}e1tNR9F^+Q{g8SD-kTadqEd97nQKl|hFRd%pQvY%}'
    '3>E~?@VckA;y_=GnIIw4Q*Klg82G9eDgEy`Lf^)SJlX=#L#BtR=mT;$Yv$|3*Pq#^4*SwIQE=Rx!6({3&!^C#`0X|<aSlC6myDv2'
    '1UJkBP*@v`?SZ!r*}SXpD$^B7%kMFf_0IP4<!s!zfzWaM@NE3?D#vWsY;nA5kv^mBH_^W9?mzUaEy7C`xDzHto(<y%5gPhvq+(-x'
    'iy_>fQN0adU%n%CzB~Pbj+^Ch%e7ah#al+hq0VtChH*wXWnJBt&LuVWx#RJ03%GmtFYnQ*)uaI?_86UC^SVClpU<Y4SQ=Y3b8jb^'
    'xueo;a=Ra^XsBgGMQXA*rpf`L_DHLIHgNEH?>$OF<~`68c#JH+PP0gofrr&>am|h+o$T-;gm4y1unE>#iHu4}nXSF`h#%<*>vrAQ'
    'um&2^YtQ$!NN@PT9K%f%mDorT5o6apLkuc&jG@I+ABG;$O{Unuzn0YhpljP{xt__%ORgd!tNX!Ya?#$EsiqwK*haI;z&l1sO3i!I'
    'LBnN)Z9>`dHC_&c=`U0h+Ust=sXRJVV<}P|B1D9ob6NwJk_e-pL*>M=tMMwS%2YXOXMn1i9|0<@%@8(ttf0-SC*eJw*nAIaipH5`'
    'D?Vyc5$|ZK$tIBePkEKmQIW78@nQpEVMxhUGEP^fT%s$!ZZA*w7epaVHtNKL*?&b*WsPTUzVWHn?hU23GT&L4g>rXvd5->Y?9mH('
    'B}@z49!H%n&l?L8L4<GiLl(iC$-T4^W~B&3UuJ=xtvL!=o+z7OcAW@Jy3kwO6K~!Gr+!KWoHw^mC-h7cacGEPX^ylf(xxp_O!}T-'
    'T<tP`M;Q??eO`Ae!S<<IjV>dz(38$RCQsNu_3e0tw=39LLiHnr@g5UUsaG?L{ljz(ICGql9hH%<nZ1qw&?L=O#j{og!-FkYjTQw3'
    'P>w0(aGOlRbSYWXxT?+61<bO?kl2Oe`^W8XM*2)6!`6ymk1|tnf=0SE{~yBbA-WcTF#>RG+qP}nwr$&bv2ELSa-$c$*tTu6f4k{9'
    '-E=q0S<WoJkVGpcoKn$$pz9Ley1>-`*o%cAq`Q_f_ZtiWX3$+9_;Eh^Y)(is5=6$q=kg?}9DO}gZldJ$d_lSyoClxJdPB3}=(SfX'
    'u#~A?BQvs8L%V*auu&x<T2$)M-RqOC2qX#&MDu+Jb^-nlU1QnJU|9E?^Lhoq8<8_pk(ZAT^IS+ykr28|36{=;F6CzXwA%)5nKIyZ'
    'zkYKL+FuhH#KbZ0VXv5|&NA`RBuCP~^r9pC*begr25l9k_3H7vtLF2dI`FAj3}4U5{@HoH&KgBE?FsxEF{*O-p>bE#4yZ9+r&dJy'
    '6eSO5UV(7`2=q7|e#M#XEbufp#)?CQ`Jy9kZB#u6M`!Y-fd_4MN!sj7q8%PhciMxdKy-m8u0x8o43ev1Y@~`ZQxXU15?tTTZa@+%'
    't)k%p2iQ>Q@salbJ{qbsikLi?gK)t;u}NsftfMUc`mz~2mH8)y&3<+|AxLooes^v@LlLR~%g{(V?&g;*qf_Jar)3%(=8XF*2Rahk'
    'E}(}gN&R(?UKESbR1U?Y5*@q!AeMs19C6*h%*G2hQJK`0HSQ$eGpLYGs5Q;e`7kTbX|sJwySOV@c@9+noCxp{#bGI>MP!I&rCnc@'
    'eHWSBtodHn9JccZM0mz%xJp@!?4XkpI({T`%y_qp=7rOKx^VPz)3*bOT7m!8_??<N14UA@-fsAO0{x&Pl!D53F~?$<7$9IWg}egl'
    'V~M_;HYg^X5r>3T2?ftNVz9f&a+XAC1a5T{t`=@c=gxOEm$O)I8vWd@cja#wh6MILT{4Q(j?uuY%lkhRN#Vbk75RSNlExUlSANe='
    'LgC^K5>kQxq*VLWKcx41?_4UI^+N5M#Krl`k2QIOLd3jVtQ<~1fLa)^MFo)KXG+09Xd8==7W*X5!`AY=afM_)h%w!NUy;c={}pr_'
    '4aZ$eJGD>8$(Gjf>WSeh5Bf*D)!0zXxpP_N)}#)(N2_wgYS4b(=O;>XhZe0F`qeyuo`}NRNGlE1g8Y8;1k%hy=&C_qj;5wekoFut'
    'f4CqYzC_thamEfOC(*dF9^b+FZ61zG8`E)Q3kNf6yN(s^{4BK{_z%_^=2vKglTX4%7F$awM}*`l&h$u|h3Vq>60)1bsTn89@hZ0b'
    'UROF|!~1&@+!@zMA3p$Jp#wYa)go?cXi-MP@@Rg=cmMOf4+fXj-4n^F1={wn&*tFQ5|VhED3K~nDEg|*Xq>wRbD_WS)yU^j6X303'
    'sU?J#x<W#!Q*nQF8N~B4Z|tHn-?y?cs7OF8@-#We=y@jLQCO4YrDgKrr_%D*73Io@Eavfg?tyU-#?*0Y3GwHtpZn~ugK<l0(|oml'
    '(GWfh)ZqKdPcJ&B6Uq8M6|-8zU+Sxn?hgaJcdT52xekpgwJ7h4lqPq_6hJCgcTt5ttFE{H3*G}RE`f}SkRey73Bc%q;E$|TuJq1}'
    '*)%{{;>8*s{@x%Ryddyp^8hzXPMUEl0hy2R{;opj8bH!{8BUV%R7Vmz+HJeCeRT0?dZ@*9h;1Mu2wkmxAB$#zPN0&qTVrlU1Doe@'
    'mVSxP6qYI-8wk+;n@5WBqWwB|p(a%ScZ+6L#MX0h3nT_e^EV|zdh8gtW(DDyw0rzs1_E)JQNn7-Pi-)zA%WqKPkvl8XMJct8Y8k%'
    'Byloj#t)aA4zv!pD*iB%ANE2%-%W9(bT(vU^D^xG=QB}}2$KQo2~;1_EPX%MvMA1^aHK;q?*>7U;IxU4_hyy#Ita%&7Jr19&Om9k'
    'y?xp@%{@7KL<J2|hFG!L98v8W7T#D~<fdz^9V@noJFXsEV*JA6x>2SJow+E$B4$MHSRVvoD2)81wEXLx7dg`iKnSH){T8O-3~Wwy'
    'z0w8x`(u~y5%>~(75vo>BIxKo==YnCP#$c)4QZKLWIRJPIL5<ecaxvuBl_VqX&YHMZQQbk20)&0;PR;xQ)b!vJ?O}zBP$LK+-*7$'
    'OhPsg?fU7{(f4c(gi?Cyro~?D9@G1iT}g8u#({~*iKi5tbPHv!duyR-KBIj7J<Zo500usGd}&>86SM@?W9azT;NPMxkMKVu><s7Z'
    '(=^vfM4Q1wB}}5pM_htIW>R2H#+2Tm>irs?{dM1wVF9Iyzv4)X&-GLWn)_MO+SheoNVb;OI(}7(<F#~KLAykJX0`#}DE7+RF1agx'
    'k)^7_6|!G+(6!Ez*Hp~9p!`T>*E|vGKm1sHkzAs1=mr}qZh^=U-9%8@w6+jXmx{_VL!|fHqJSlCFuwBT`-$Jbc2<d^Wz8ElV<A%k'
    '^O0&N_7R4db_Z=4JG0zerjuqY8XDM9p0bz~$@=$hf~cTR6{mU}mk)$z_K9Rs63*-h$Qqu3?BFTs26|(92faAAftU>sFkl=&N`vZ&'
    '9@)|CsoxU&b-b0IiM`lm55>v`VdRYGQk<R!4iv{<;8H$$KA1PT6#Ob_R=GwO7>@oFhLGzM2dcJ%yx#8Tgf#HFI6yCdB4}jXnvQtR'
    'Rv~-*%wsEtST}+feMF)0Zdz!j8jhz)x=+C5Dzd@^x*AL)RYtjm5Gp2F7X2dhUBy@ak=~Tn@&rIR)4tVfPo@iD>XRKp-@i`aka!sk'
    'd5U<^WB^G-N-z&jhsodGCx2jK_8SDzb&rO~0X5sIyJ_^W|Cy2QJzYXHGsqU%DalI4ZOX@=V4czrsono<!Bc!BKJ<N{q4ETG%Dq~H'
    '%(hN;y->q(W>2Y{=o&1m%LAbyu72)A#TaK$c9*>MqFY(<B{`*uFg;<8e^{E2<1)a`J^_O^Z7S$>1;ht!eltwPWb(BUMZ^6e1Dd7u'
    '1EDYK=SB5tV08v6PWmpr%DYZ57u<Fv+FJKY`E41v8Dg_1bsNI%aLOKL8L_(ha}Vx;GUJ+1f2a$s*{D=W;u#EuM>BUEZxF!1f_k1V'
    ')`bCW{*2bbKTzBS;W+V5QH!PUVoy5`gDa*Ta^*vnfRZwTEDLg<%%U>{=WH|O(Ek>j3=goVmLD8c41Fzpx_GW#y5KjBC2XYP5Qo?g'
    '=&H3|ugf)6MH-=+6IpAx^Uly|r-@PI$MT;no7M-l-faC0QHuA}NHYP&7~(BWfv^AW)K<fSA3<X>+5D+j%Ob8;r1F-wCYAN$$Y7ix'
    '%b8fpw*eL{aI<U)jR_QQ^tUyH%blzECStu0@&8?hN7>@+d5NWn_~S`Cab_c<u;+<5cYl#>g&TvO;9MlhB;6jim8%mfXcvi$pS8Ve'
    'D>^U(?>J2O@b=@+c6gKNqWA`(B81q<iI@xx*9^M2(KTwPNivjxCOrr<0Ul_-&pAdeqON}N{=x-y+`dqGUKC-(Y)dkfM~e)v%F{P-'
    '{%Ap?RF;-D?URdj0IJ!T3tDei3ojmWRY+vr;`WRza5i>F1vCd(tU)LyO3F84t{PyA=vrTUsc1!z==lJPl%P};T{CGEE|;%x!%Cky'
    '<a7%f%u~GF72m^@aiF&_SGGk0hk?klqS(zI>0Qs>(6z3E%V4beGh=TEb_MgNG$xqMMpo}-5t=U00)1Z#e&K^37me5@I;Iaw7tk<C'
    'kJHp+y+Q4a8O1p7G!Tz2T9&0b6eBY*N(<tq9Rr3f53oUhRe3V?%+0rKhPbb7id6W8KF~^ym;uP2Kl)oxA_qE528?<)UEdZmIkj<V'
    'PRtmh**Rt7IR+FmKxSr(SOlmg>tVsL;5}&QvIqB>1YG=jMx<1r9vQqdZhaeEIg%C_YJne!Y=o^8fsSzPWKXU-ZjfCtzDEKGle~i0'
    'i9u)Fs_BS)7FnXl`E_JC?ANF=<H-h~pD$|>bQUcx7i7yQF3F@tFL0#l_9e(X%*-hm@Lnr;u#->R;@8rG)>xFh8@@~*W@RpAxmf-#'
    '$l>Z(Ok?j$331{!lS>(99&i;)-z*7i%pr|&qh2|)-o(p6)V<&f-+g)rD<X1l_|u9trBd{`U}4$P-^dYEK(v+Bh$2QTv44Gu5h?I7'
    'Nd?syWJ$dPq$Dib6DD)oQ-zn+fT#+__o?;>P19Mw|0EiQWn_`<tcQagFI;p~{XsO5-<Y-6>_%2E=e+KL4*yx^3go_F+XbWyt`|=&'
    ')HGXjxqr@95`C_qqS%sYm%)?YD`4`H5oM>--eVHemwnT&Hm`P4E3%ZFn4?;p>g#z6Y}$6GHbFYJ*z#XL+Iw3&8Q7zb-#z2w3~*gM'
    'tE5onqwD|#yF$XomFv^k$T8^^?*@3OTVbi)y(V6<-^J)Ytj^9cWAMgg3U_1bvEpM4FZD#;_n8b;t0wSaOM)X^fw*{|;>KCci>YXz'
    '><b5EK(2zFkN{FAFFf6f23G0%sB#thq9M`2>Vw=PDjR21_z<jFF(M1rU44Wmo|X}cL|x`&vv#6oR~isS`f}=jB+PE<&{XV12Dc`Z'
    '<{E|;T~Nv0L4+;?;YVn^h)OE*dx)%Klnjug!+iZ1@c}c{yH?+D%S&nq__(sxxIR&e<s3xRwq`NpReyC}{xPI<G(#^Q0&>{NLy8XM'
    '2`;0Wtb-%Dw$Gr0?MB^h+;*+zOJ8vW3RO%mgPQnq=U8%k^S<yS+37>W7O<GgoL<MDnr|w(Z31oz{a|BgGyG=|>A|7Db5uuoY-6cn'
    'wNzzHH-`q$qHcs5=VLkCO>|c3Rx(=PtvHjj)Q}Gw@9qg7bQa7ya<Wjzc<kLruZHiSwh+tm@K#QEXIdtf3ntugwUP=9h^^RteQxaE'
    '3R3K85-mM)q}#{n^CGJR#Il_ehE*FC_s!ok+R344sb9#_K#C9rUCY1u4|!C_+YzOe?z!D9yCyS%tw~@|l^CoND?sMy3Zz#)W|I7?'
    '=W92dN=}p^TOet%wsW?DW+%iFnX0s+{~CjQl(4Gbf=_C7a)sx`;(gauT!l?sHe1j6V!L<5XUXGc%Z_jA{*dXVYF7$%+`Ae38(dm<'
    'ng{IkOp=^DM&$Q?-u=A-Ic8jJkd{P{H16)nBj^t!emz8dO*(tB(9=9>iXGz3=sTNH{OhZ2oe)DX?W>W$=B9wwf7_bDjRp}!4(kH3'
    '?{@_myqwC1>=BR`9@RzM6KE~V7}}HPVz~a$NBxB}?fS6OKGZNGY*DwceKOJkqY1GA!pre_Ve*yFv8I0?&xD?yt#ZNM84Kk>85qC$'
    'nhICJj$wc`ehVhDnq*pTEK_o=Ou3lVByXqVSdJYY#J`(J3*N_vxP|srM%nwen_wNB<>NjCDb%lX(A3L@wX_X%Y8b0W8_@OFXZKPV'
    'h_}^=UAo4_GGK{s>g<B)>_GTr3N&gzhOSdcKZXbQj+JGWO>Q@Sj#D3p!eIpww>W;)PXSkO=9ggKdRx7YtN!hLCkmp!S{Y~kf|*#Z'
    '!`<IfeX;j$>%1`}^5szdx=5#UZT=4Vn}Tg`)NXt(9Zy)GG@7IxF;3pL)hw~JcF0^DfS=#O4TQJTYvIQ@jcE2}CGYkSl4#uDd`3($'
    'IT_p;Lz@sLYpXByjfJL1R4t<GVw;6GQb)3F{Jk)JxNEU^JD$qLQ(crrx7=<3Nde>%%DUf{i?bO5*wZI1^zTcM6YMX&iQ<%G|Cw50'
    'xxt=oY<vC8-jb|Q>wS?>+KfI)4smh3!<BTshiM7Rt5Ndmo%F4pUM8pKDKZrps}m+gx=SDgEKK!E00UMvZj0|jRUSGiDWiP|ZrGRp'
    '3B}7w<=`wxn|~6I##)5vK6$y^^E^TZo^^TE@F6pf;3q7uLN@cTgkCMw929Jfy(tKjGUxdbEp%6UHQF`0FK_&AXY4~<?NzB?JK!-@'
    '3*#_q#{9zSGlb-601eKr-s7}^s1BXb%k(ZlaHc7C;QE|0^|4_;f9keUdOi$Fc1QBCRH&ln>UmMOP!FVU&Q!LO{V2bHaCNnf-wTza'
    '^maaaBDMQ@Iq_9K>?{F?h=c3tAG<`>s#{#y&<?`ftRl*pE1&k2OR^z0#9A23mGcH!o{f3)>G{v&><roLR+goyP>>n+<66boUm&xP'
    'hi9WM;FoY#??!d*W%23<B;Fh);z`dL-XAgy9(3hEN-&y+Pr%gM{4xkLysw#V`M{SPaQor<z=!;ZF7}!ry*c!3_NH?9(_3?auF^T?'
    ')bj{JQrWHB^|jxJ3W)p;BLivk{XAr{6V{{T<Es`Ac_l&fbQk=_LV>bxl2OSGhzWgb;P_O&&<{s&<#&D%PZ+k)!5}no(NH+zD6D@t'
    'chg%az9_rM8p`p!kfbL)Joo*Ptc--x5G}*?btYuD45j73o&{({<V>DK^OB0r;`{Fm=Zyqr;;XGlyG$4JyW;=x$Q?vX`KQI?-&2$I'
    'DhX2NzOQ`*dU**A5_j&etL3!%U`mvsc?aVud>nnS78?z>m#f{Uc|O#j){Ea|mE|c##%<>}!bQ3Bo7VI%jQktCiU>bS4ISo8%{^cC'
    'eq^P+^a+7Ry9ekhC(DNz`^b)q_Iy5m(P1@=GffK3Cky((AXmqM3x)Dv>}&2t2`-At;p29_cS+lb6faxDS{@IwYqCpq5RP!nOnpN;'
    'RX^-g%>f0|=I-3jJ3*9Vk+k_vOM>VLS*s^WHpxPOAw@1xx8;t-Hm>1>yH?ip)~QoNa^3aFAXXURr+Q=Miz7x&t<b!;b3xrmL$qLD'
    '?uSSfv$@yx!Jyac-#ZZ4TM7hshc!Bw2jEQ<)>m{O&kYl#D-ht0ieV*J`IlK26ZF&r=ged0)ELqP`;L){q*iKPVB2sze3(3f!m#MA'
    'szXWz*LgHB??OYmPlm;w4NGF;8e)Hm3gRB(es>xH`vNZyzFnK-8u4$FxG)oRja_^VV%pBVE-7_I+naDK{Fp?Xo5{OT^GvVL6v8Xy'
    '94q5rIT&}Fb=>J>Oj(6FjK3X`C6Bc=B97_QmwQF-lONI)ST%fs*F=w!RJ6#)HX@@|^~MH?#*aeSQ^hjb30vBlG4w+*l+eOWYV=WB'
    'jy3SGhgNM5FiPdci>1@Aq|_8Y_>F-LjFGi6nCT(xO{oecX*iSWSk0@(m<t>yBbYrS%JjhlQ~UuluH}2mjnjz_KlGNgPl88+XSJIx'
    'J^IZP$ZWF<^4vQFd=0}8StD_@e^1c4x`0KFuNl_S>2Z}u%zu0(kZyJ_^zm%&_0;)*w%J?CZ1Jc@cynkJ!Y*N2*)f+-EnO@1a%rv+'
    'zq38ek#Jg=81By4W^@4OP|B2?f2Z6l*SMS`jk^H<j+jr(2q<Qc&Bk1lh`>J>{6!0-Sm#>1?dI@&8)&|>KCNwfpvhI@s;-^LMiCwu'
    '>#`uc;&?P!=ZG-~(|OwvD=9E$Y<>ctC3<dYcvYd^NVhJrmqv?c*8}}60$~tq&%n<jN6M3^8CGZ$i#JSa{7JzdJ6U9vRFD-7RF17d'
    'sIu?pd0*W}TG^-z-N?;pMsQbDDr1B@1(??1_vp6P=rJ`e(OsR27%|KHUk?7UZJs6(58?@%ajwNtzPt1zR|UMLJ8LMDX?S`}GQ^rX'
    'alrOZWbVy*qpd(=oe)5wkb&s$!H#Mp8r^`Aq5V9gT~+RAnUL8!*@V%Zo|@QS9&L*UvFA~b56NArSMtO>FC^|8`a^pzH;6K@LK3P4'
    'kNq~HmpR06Z{vKTQeblQ+6vWfp+p<*ptCXZjj~b0TR&v)sPBSvmVv0e2}84?I$g>e+((7Qt=qcWjK}Ht!@zEviPHi)k9q^!`fzau'
    'R*hKxFzt9lHk3^ZQtueTNUw*qO<I>}D0p$2CK%%kEZ@!D1+{pr$68;Bomtxa5L%FFG_xUGv!sL57Gi-?ps68BS{)f+L}-jQ@J*v%'
    '4I=^depr%Cha@)0<Rkg%Rd}$kf-nf%vMB_a2=(l_zO@IWQ(nwC`hPHWdg4jf{&Pz+jH%6GTCTy@U8V%4Y4uDpVnPYE*H2A3^68Hm'
    'D;ENU(P4FjEK1BiSkuc{{Jma33t2xJP-Prk7LXnF-`^JTLrd)1i7=GaRktG-z2p>5_983^)E;r7jA^k0q`}h7g25k|P;U!<+nX9Z'
    '_hmp*m5`bzy!p&m=*aF0mzrJr(`J{;M<5(_^vbLZLL#sQVM*-mnf`H*#e2s@|LT80kt9P4sC?ZAL9Ay_z=3m?%K0O|d2G9{YTTG;'
    'Kz-Gp00~VGZG=am6`EkS{uOPN&y=K}><fIfesi@@$Q8RK9g(J|uP*2s_hUzx{kU^I`sq;#`81hQ!7Nky8LOpkU_TN*B<U>%n62sf'
    '3?IC?816+TiOze{Q1T>-&-+)jU@icCwVf_S&XU~dScesBd6eqFIb5Hi9DcnYjjP7x^+v~FX@0hO$NAfiuX~+PQRl&?5&st6|Dlvb'
    'lt-P<4jhJga_Kk#l)ikycD<}2oGz+sC?~qBX1+CV+r6t<J7ua&8+oRrqiePh#x=&-i;>P~HYdR_n~_|Dp-YM-E~&ac#uowvUNM(4'
    'ZC3`|(M?m?Qx)IeJ&`NG>N<^PX@vs7Ym1vXe`U%89jx*4>w61`wP8l)@S1C{q}_N|#)d4l)>Q|Op*@sw<ToV2RCsxZoUpw{KWGJ4'
    '1@bPgE0E|m4LNdR+jX{uD3#f5q6PtT5;R}RPC=+dt{o1G@@{pyYY&x*&MhY`5He@ZALPFrNmS!B_wASH5?A>iolMhp^))jW`WjzT'
    'zqGpt&a)09r{za2_LjP=S~+CyYpo%n;AI-%M~ovy;Apg;rN7UQ?uTc6*k~IJ%_E3)jy2sjk=?l`6s{{b*^ozk_)=^?e%li~me*OD'
    'qh;o<9`cPZ&W{VUmyk-XGaE9PEJ%#xUZ|NSofTf@Z<K5{avm>ocvz9dX!9nNV`hvRY=-XcpKeZjmVu6ddg12owbUg$RW<#6lU?EJ'
    'QHEzmyRVkIz1KpUDg7gkoA7BjtVmW3m)^P-aE;r}HDI%QgJfzO+dy>?YI{$r4*XAOt9-=#MqWq8nI#R|7U7p)YpjPTZmgx*^O!3U'
    '`AI{uC+@_CugOv1=cr^2OGyGRNh{5RKIHKPw{wL6pz~9^q=!JkShJxP2RLc5C*GSgi}exi+0SY{mRaoay7e;MWf3d|xA)-)Tt%v&'
    '17nI{f?LoGiH$yilF83FW-Z9WvE<5f%k{0UH(Ees<vR~IUNy*?l_3XFGf*FBe%jf@FFzk3ULl@p_2@pC>rBNZ`)LsgT>&EPZ1oN-'
    'mr{9xp!vqn4#`-*Jm38~>N#nmk&}cdSYG2PTm;s{06!C9ktlyKDYNLGWMsh`SLX{O?>cf22jZ|CN&B1@bp&O9)uJ?jXFKGprI_+F'
    '!eFwUaamfgOR=V;Ted^>9MS)YMP#`<_#IK|i2{RQ%Q%++U7Lkl#MugpFK+c;$KP``_~iM!1R)?BP5qF{orehb-H0a6^~!@-LXuWW'
    'Tu#k<^8Bq*fgzhB8&89*#M!N&no9-+^iFhPMAv>W1*mzlWcrrIf<ECZx_qB@<IOG}?G(!ae#-&Cq!!enQuj^7*uXnvO&o4U7zpmP'
    '&W`sM;E_g+)RhLw)+0ejzjH)j^p3XpBW;lg;%Xafd()JKn&>K7Rg1O|(?{FCZxJcUll*mS!$GbTnB4!=Ro|-ec2^sV%2g>9%_?&l'
    '2BbHR?34gcKqVquB1G<=De`N%)gEd?pb9t-R6G^z!{A?)VAY<OrCLOI9xbXgC$Cm`+?J`Gn&L}{-@^9puS}I?-gN&_3m<ro@G0VK'
    '>vf^>$ZW@oc!=@B^^Ka%?KyV3h|*SxP>?(ifq}gJoVqkf%j6ZU?`cVmzkp(+jm4Zv=uXo2jl457{J!*E800zm@Wz{W1dRT}nD)k3'
    'O5)V|5Nc%7I;4Z&p08;P$8(6kI}o$n5i}jLliy}RgPj8jB>&rU$GI}e6`l3muoMF=Otu6mk`Bh^8*ZE*ueX;{hc^`@e+LJQuzPOk'
    'I)N1coP|5QONK|&HiXUyph5;eTrQoPsaZG&3)k>KIG8_0D}Y40*Si+&RoGbqS}#CvK^QPFBP=S5nlu7ogY~!ZaJ{6xYNq251F)9@'
    '9L#-BcMLd+jDY?RR||_M0w@Uq0Z9n`e_YM<f4CYDq|jUce{(efq5tJ-EdR-K1OLm_Frq|Bh>6iJ`}qEctC_ZO(eFwLivF;^cs>-I'
    '*mQp9-0r>-ZV0CKQM+qiT2?ir|Fr!aei|M#PVPSSp97Ktl76$kUtfREVBZ`c8Q%=o`&R>IzodMYzk8p-zYV`4ei~kOUVkqHZ2+r*'
    'A<ytXF+ZZex1TeMjv|O#37Ws3yWNIxf$jZm1)qJA{W|@hFM*G?qYYVxabJKZ&6)lJ{<fdZ8`lDXxi*1!%#GcJK)dg?uZ7R&Z_RH+'
    '2rrNy;jfaf+vC#{%bxma!0r_0=4}0M_0RWb&yV4ukF~yyZ_uyg&+{+sqvopapyF!((Pwa=^e^_$>X+q-=fdxE!F&I7VCVPY%j5^*'
    'JK`7N(eJ8X$S?iR$S>vR?+0N(!tc-duj}vEXY0>I;IBwYWd4$UI>!L@#PFu@9b=CRIq*M<qxNaoV1JYT-yhVL*#WKA&u0$Jpj2(('
    'b>pIs`FeKh?U&m49u{oy(t>4KPJ4r7K`fKS?E~eF9$&)=dVIv}^K}Pif5xO!Dw8t|;#1meBOu_865I$>!Y1zdx7V5+g|gj*SHlnB'
    '+j3;S`r(G;qgx~oyzTv^q}Q2QfxJQXQoiG|HBMsY=45^^r~T4Pq-w&+b!)!Q^_;`10R)ZE7m*Vd_@wtEB95^1t7219qFcJgZYi`|'
    'J0AVy%|YYDF4CBx5z;`tD5d(3_3LcR`+s!0+L5y$ftVK=p(O=o>pWO^zjs*011EQtKID6`&)%;m$(rv28IJGs2&DpOzbDiMo03VS'
    'I@T=n{9mx7v)vQ4ypyKgM?Qk^W!jws!Dt{c+3pZcA(Fob_fi8vTaDg=Xf1xaL{4pSQzl4kQGvt}Fv}2BIhxZ32S5L^n4_%`f0YI`'
    '17A~bBqHU+2dWJ??lvI!q3ROib9AZ;MT7o+6*zp@qoF9$0y6hBGQOq7`XweC<R#jOWnqhaO5xJVNJ4}8bEnn8x`0%<a~eVVLKHLD'
    ')9;$i5Id7l^J&{<MLh2ICn{1N0LIKL>FCnIMsZV$3syWFB%XmGAiNPUZ#LQc+xTQ4%6dEPR2l3Pv*W0AN8|{Z0{`hj(!~Gw?~qp6'
    'ES1lhFrV>XU8nrbx`_8%WY$PI3ygP$X=<|8Ox+@+`!)h#R182r9Wrek)@mMQakM=S-3#}h+GL2c`XCRUk?hsr>@YdN^osjzQtaJh'
    'fH7uQ4S(Jn?$B3AVY?T{x-Pb;sy$iTd>rUKKX0nkE!P<aq_IE2Rir7vdwqR7)CH$1jxrJu=gzX~;WagmQXQlbj9NxM3m_mY2>EIM'
    '8#ZkuX`t!T==YsDZomONEyb2|P!y{X@(yzIhyhpc0||p2;ubXYBL+%~Ia>}{9ac3^<H>d(!@F3Zp*4Mdr>>)N+@cZFF~^**<cApp'
    'f7eNhtHFcP%t<Jr<E7(r8~2zdvAU@P%I0fSwQF{I<s%Scw?4P9Xx|3OIN5_9N(UN3A)U&hLT=n^i|f-J`wR0;@jjoFPw0LrgRk6n'
    '*B{E@hJ+gC2jsScHEA{Xe3AY><;p4TTe|R5tv`wxK8<vTqr&kkFj3iLzPJifMSBUpP~{QGc1w2YA4fEsfC>U97Q8if5aQS3Z8Bfa'
    'TfT*{)g-{O9M%!MTo+<}if5pHgXDG+9-fp7A>Y<J0&@`L_k@{esdBZE-v28M`Gz7sQl9NQWVHDb;?>(q62(p4tQy2qj<ka0!z5@J'
    'Xz2>gBwxXBcw7!jTYO0vK{Yw@tcsv~!UoeM$mQIBzcB?*=$p(TQ}z?gp8feFs)7BuVec6zy#OnS3Yv&AJU5>t`=+@Ek)@5~ly5(`'
    'qs2N&J;evJc~vg^m)q(PerB09r=gWPG&1>;ViX4i|LGg~d&u$ka|z6yO+Idq>v~4u7KPadzH19ILxwr!`BiY4Z2(E%*jE7Gt+=uX'
    '*OOq`<8ouGjB<Qs3$a&}w+JtW=0XPq$3SuvBO$2%!}7;OBt^;g>$~p{Yxqyz?XAwtD#AVem8zSoOH@OtD(&j%f19^2{4I6S$=1>;'
    '=SH2$-g0M4$V0Zn2jfaxwp{^*i-t6>VSSPqj<vWa^}4w^KBBvz?500zZKWhiPOgLG3ihRqjTe$F+UH42N!M$(m+Aux3do699?^$0'
    'c#mnXJDxW1JbFwxniR?HpSIcJV*!G*k!`G{W=>~frNw-@4rX@@(GICIF0Bl%L#dX#Co%<FyvmNBy9vWqx((ZC+@WrJU>Qi{fJELd'
    ';RVGa{vhpjjh|eQP68%{$y7ea)1I2hIygjmjK0EA+a`z7#<i(pS6)E`x<FrpF}&?O#{CyNzK2FccX2D>ge7~Hktp!JKl$-f!wu7i'
    'u(sSB6}xM6XCA4kiMS{`9nKCGOQBu)Kt(pS2WGns=gUYVr-0!NfyNLVWXPBgj^*{Ss%sP8*EYz`e?x6B4ON)_GH0U5za1ilq1;)w'
    '=rkRAuIaH~K&Ckl&m{um{-$4w9u?jj<UgMlBz;C_JE(U|80WiAedRSV48Uj}JflEdV>{n2jr%kSrpRF)b-ZMVA%-2P-~SwtF<YOC'
    'A15Vh)-{2fSk1)_T{Q`aWoJPfCHqH_a7iW~RTFW6UDAX<o9jpKV73(P5$$<g(}<#fn)Qdo(aiLxy?WhLKFp|c-UCvR@BNnwYyp4@'
    '7yW$Hzl<ADIIj%v+*?$JHwCGt;95$Coc;1O?uaMA$5QBmh>pf=1f2(+cME4&*vcA2IH4$b{5T%=H(=V2iH4{DYK)?cgyh3^{{7U`'
    'CU-xVaSG?$9V4k5{e5Lz3`46uA!6jrVdNKF?-iOTazqS-EPsZ&u-2hip?KNbkcYk$a!C_f_tP-UmBDAk+>G8639KdJ_KvOCY+YZs'
    '{<Jt2?eL8(k8VYVfGDHfu)AY{12%WqVpXE6_Z><6#yjhpQ$KN;of}eTgW3zKhW^WFzB*gi3q>#ml0;L4?c||H4O*Td<d`<NL-}U9'
    '7~1yHJ_dvci|^dJQJ&e3oy?pwb!$b`f*BMjKm&E?7X4hQBxR(G(<`~iC%<F#hrlCMMa2%^Gi=jYa?&Fv&Kykp%b707?u$ATW;H$a'
    '(1O6yxksr@c90H4-2W6lnOPkIMlcs!7y2hIZHz_Do!>}nx}+P_g94yG-z)5FlDs1JSMOttl9)mlL{7#;j^Aep;_6<bzrgw?wdLd9'
    'lZbil4=zULfE#{o+y1$PcrMQ`!L(<wJ7#G@^R{ct2Gi@Kq=TV1LO@RhbN5@=U2uhw<ZsuLvlBUcvnhSh<{>^6BaF0yGPh|W!1Kqp'
    'V>lv0Z?J!>%7f*NKTgCL%|7cx%>O>Iw)khcP(Y@gn*H$xS-1li^6-;8Xstd&TTDTL7M|F0avT9U+T>rZf$t0EWnQie${?(0&$ARZ'
    'GKoMaXS|QfkqIqiyK9>Pm`kp7jj_PtjcB0!VC|DzTpNO=vtItjG`KJ|I~qme4AL1nYq|wZhifmMiLn4zZkaBJNJ++y`3TN4EEQkM'
    'pgc!O5F~XBB$g~fxp=Nwn*pynT7I4aT$|@}a33NVuE<Ap0!rpp+1a|R#w05nM~mMjk(SIR`nkX9l+&Hd>-aM{Awv^07<e|D=w$nC'
    'pHq!u=rFMRr7ihRu>%yC>DCNU?EuX+?jaepdIMCSa8*iO!H)4&orB33yjE7RG+HVMO=R}`Hw#^5zKT%G#kwwKgY8J+f^Ysebf7@r'
    'a2kd3Zw%QNCgI(Y_sBiVO8adoNeoab{fs9EhhdW}s=ecdF>4SR$U0_?I@z>rz&Ry;@2S?GzL}yFMgiouoD~d9N=M{?l8w=3f-LRh'
    '9+R>H(QOpx2>dLNe^m>-37IH326<)VB!|!Va>%`GLL8Whld{fhvV3?+`(M;X-%a<smYPm<)Rlx?=lK|ZF-lL`^%cr9!)%2Lb*q0u'
    '%1jq`IA9xg)naZ~+Feh;B)_v7a9kr)53t1VHpRor9%tcnplX%$E-amb>+-$NYf(D@`#d*YQyx!@9Eb9%e$A{19<m31Zaf}V@3)G5'
    'dRPaP9ngmU$E{OtkkU$~2eMpFw5kWvyw1XFP<7Um{%k1R7T*jPY_;|UG^}9)-D|~`iu%p4U3?S<AS(BF#43BD<a{7v*}Icr_+>K?'
    '!)^x6k!ntN;pt^r3i2V2@vTM^np&euNw9G5%jj^55bYirTH5J(?hJo^uo&mi=oqk%=yL~3JU$o3OjYv?&HZyOtd>uOBipbIvCQjz'
    'g{UiBk-b|7i__ICh-0xM%@l;EdT)(fN$E6cq#(yi&7Wm~Vgy3z(}dOD91{xhM`9co2(1zioZY<g`E5_T1%?Avs}}<@sDS>Uc$%Ks'
    '9yykRHT(Sv)LQkt)T{dwv?>ylrvu>Odgmq~VnE%}HORjOPh*XjWr#~xC1qVCOw*l@)vP<s>4t}?#ILgVS{UX~H|#iYwxsyY(kJ1^'
    'E)$@06Auo_X)#^jZyeXga)_`YSI!yKJ?BTyAAtUt6+XB8Zq^);%2e6arxz$XqF5&2V+TE<6Q{h|uFiJ!-y&7g=I87ME(l$yzLCrY'
    'L!=W@(=!TH>~IeXrJZTxR;cGJ{}_1*vIsEqZ%(SU(Z7^z^=It89mZ#v@|w+wNQ@yEu+=vj@fqR>yQdL7!5W=rzrY!vT_Br;#Y}#K'
    '9f}v>KpT}l&<4X<!h=h6=;AAPw;AW!hxv-dS&WQG4oxM~?C|Ukl>~tF*mmtNTj8%6G45)=^c?e;P-71fyXii2K=;tBGg+1`g{;zW'
    'aNCCkV-ol7zaOc$%n?`vC;av_MAEkZGg*z)&^MZDhBqE3%KJ#u=gK*2;Lin#VzPj2Gm5-wVeVIi9Y=$NKYlI8gSH(tX~E}l-Dh;u'
    'ax@o;Qyn4M($g9G`R3ceDa08^ASmCB#<sE^PEmhSHxP3ar{S67%b*!1%|tnB{q(k8ks`#Jm*{}}@(}Y9F=9nkxC-0Hu8`R>y%}CE'
    ';I!(pu8e#7?z<X}NrqfWphD%iX39H%s%=#M-Atd%!_zlAXQu)@x%>p{4hoxy4@6{@8rdo5Po4Aq?f$&K=0)6trn{ma&rF63{_2b}'
    'QKGDR00fWErJvNBgRT$UhE3>x6!xeQBWV;kB6OYZ8oo~MKv?zzU5WfLAh~ECI>&#jAX($##ojIj8fT;PjqWOl{S3>l!ph&t`M?^L'
    '>c+_X+d*z3lr=P$7QTO5Q7CUGY=Tw?e3Mp6Zh!*tnU^eWpt^x1ond+CYUJDt$_^aKzCO$X%4^IXpN)@!|3x@hadcZF2}S7;X#@Sw'
    'KH%fO5%Zb!LCf9>VCYCzTP%!x{*IZ;qmlz{640}Jp0jCdA7t9&<oe7d_N=l9&llN2?%}V6t+3DR($f-n^H?6a=7kpp(MbKuGNYdp'
    'EbO!Wys5}!V}-33?IbOzX#&fP9RKx9Lb$%A^z)ElA%ycxl;~AHu&jo=IAzbQo0nTvT2YpDn!M1CC>aMLqfD5B1J!6?qdtS!n?RnQ'
    'C1=8Wa|~JnrX((Q{+#i1exJkz`axr@_z@ATb6q9qJ@+V+5X}mJ+^v!Cskcw%)E(NzX)qD#E(SYxsHiOo2@=*<-D;pkN;wOFcN^ni'
    '{8!g*V$^U$;gTN8cCiDGA{gHe0rh9TM<?>C4pvnQHJ@brp~89r1OlyperraM{>AWnIijUtd$N$7-Fw`QBJG5?@kK~AU2q<p@GHm3'
    '-!dB_E}_V2jCiDa62azvvXXulqJII*=R1N&v_05dz*^-JKT{!=9=7EA2e4NqG(#7PVC`hXGe}qpheW?c9`IM_L1yquofz3B6cm1J'
    '=NBXwsJoN%kV1P?K|5TZeIiT$Pu@U0*vb7bt)%tu?pdUY)^@>~<iXftBdE=6Ql*+Y%@4^Lh_Y#%og^<<I8Gx4DXwMOjIerzGU98S'
    'C>k)WnnCSHLDt8pT$bu{+B`ZJ8maC1%^4Bg#VR?-ebSO+w2tk*9K%)xd^Jhzr>pO;m<kUGW(D@?25xe@Ut(^5CR{+Y3OfNF_9(Y4'
    'IP{5!!e{BuS`2e1lhrT`G2?)-QTofki1CQ$=y|DXs+wy=Bc}#fZNI-ukR`wDe7N<TBTCpnozN|4OyI3?HzF*cK*&FzdfWIm9?M=}'
    'Suh$5>A2m}L*bnZ&YysoHIJ(sy&0!h2q#OUk)dOvXL$G_dMqsB)*uDt^@Z`$pxAHHI@wlREC9#;p;HplW2N?>d3~VYf4aOl8D=RR'
    'KD5x1n^TL7MpgFJu<cvmD(T-pEcQoF45wM^373%Rl~lx_f8O#|GcQrOqb&!E=jW##y_&Oy^KF$IN%|fdP3&dCZ>?W~2M*%dKX2tr'
    'F#csOtc>M_E@Nf^&={<X94ein!v{b^-<Y2lz3&6e<6Y?BV)*$mJ9bJ3ML{^@z(~X;EaPo;`wMW^mtsv6Gg!D55$@F41y3IOP86W='
    '9!uuai{k2!C13x9p$2+Y*AEf$ZXfrukRF#3JV2PxHrp+ybsXP;*e_kU2gSSDN(P8ZT&W3{6upFw2T7nQBG`stjxJ1%FDt;Afr)+k'
    'w#txcx7d5y(r<{LOHoHdekd;Z<#9E`dE1)ArQrOtQoEYBz_3E<_VY3JO!SE4|13l{^HD8IMaH4;xTGkTa_ayEBV3chlur)OWt^RM'
    'gSP60kFN9e6F)`P96LSd;~e4fv6NF2aPvH|BEs~mOcPe_Fj^RClp;edX{Pj+LH*2W&-{z{U|kn)4FAuW93VyL7;}iV4oL0vbwx*h'
    'Z5P3L7hfuRC`yfkjl5H=x|K*?wf^m@cBc)tu`cr&VQcbxr0@TxQyj~k;Qzc~B}}{g*W<%Gc5Q#A@FCrFC6n;1n57UJ_AAYP)A1w1'
    '8LW~qLg^J5Cxe1}{%SNU5)bN;z0^~5>IDd+pKv|GU^-EJVCEjY@tN>^9B}7>{sb$u<~J#z&%PFwATu*EBm91?GKQ4%JVltdO>(77'
    'f`KBOaI{EiFE}uZjz-?jKBBJJ-UTTJ<<L9t#Nl4r&a*CJBgUF?^9+_ahqlb<lJ5bzaBgIAPreS}g<2W5MPNXqEE9Dfam^<#<2%W|'
    'Ng>a+0}D6XR-ZO4)uR`(23Rw+_P6MNej&8Vlg<?RXR#U_hq`CRt<2kK5!7^jvs~_ja{~*8_K>MBe=Rw<-;U2p6}`*&&`z7epOQgk'
    'I6-#V3dm6#&#N^&#F$++KaUWSFVIZ6LTvN{x%;qI%W_MR*=NWEy%liUzNkqF9BUrN&r9QKA?ycg&h`fSt-jm5mWFr=4u~Z+a^>)C'
    '7HU`_d5mT~qKT0<m3FB(<q2msEC#8xfXy6C?$O9!-yWx`ghkt2mCIBfr!U!T96_Cl`~CAi*_LK*V!Y0t^_8|3AL)KCDAPPRzQx26'
    'mS_d=dK!EuLH@PSN;%tY60+lg0&=b_ch0|PQaLpDYpVmZyYFh4&>ybmO~bA({~W~39<GVLfcCai+W`rv{19p6JxZ=8Wly+~1Zg*Y'
    '=hJXYj?@uh<u3(K!?NG9Aw*t>zq(w80EVlG{A7{NO!n;=&5tR~u#l%P(odl|oY<$wOteEK^r}?}7}w$>9*4r=+KyX{o{=8t0@P0Y'
    'mKBixelcK?lum*wGnU<!2mhjNFF~B>wfsHkkdiPMVaZ*_?<>R{Np2<ABfb=kEo6Al?xYJWi_PeWaT|G862N%PFu6I7GVtrc77pn8'
    'Fc|x4>$$En`C5lH5$1>L6>}f2n=`N)jaQ;p`$+Gysw+@^vvS-Q%?t*?tLmjU^9i5Pu$;(m47&}!f|m5dX0wAwKo#7*M~<N$i3vBC'
    '^>5Z%+4djOJiMIP{RR{Ef{eNFE~0+jLKF}VVccZFtb~B%WjKj-$Y%GgkBW^LMUP2TD~#>Dj0^|(+Hw=lyQRNWY*}+SdJ%gm=qWui'
    'znvO_WFnPqz(V*Ul)`$yL{jI4Mvm6*6^EGAWHeM}uj*os&S%(is;ym@^C(TOC6yAkQT0ehGhzq`Kw+}D6R=76?Yf<no5y!?oQqn5'
    'mM07k^g>u96rmvxARaAZ6TIAx-m!gO3;eUs2IAdG3!8j}2t~edNZFZvos4Swu`&<-4bO4K$p@pb##EGL^x#EVGGxh8MK;mrRr_*)'
    '+H<DmI4q<x9VlSWXj<n&<kLWmfeC6xxTt!cAdfPVr>eBh+<lycjjdE26Yv(hU)kD?h=gX3a`^}85c}r(v=+BIK!BLtoXpbylvYs|'
    '7yaz6&-&B0<sKW94n6r+D;6(09AZfD)Td3Q3Ih$+6h(R%yL7-U^zc?<%r2=U&dh^#LqC=bqkGy@i=$HCC^`AjNd&?E0u=?AXI?}z'
    'MXD&^g=qL!FXT+Mb--s2v2os}DlWpTGQU*{K%Mn{_h9b6Pi+bfgSQu959iZ3>{c^Wa_=zwyi(w;n#7*kmP>otp7ZNt#WQ&xtnS-G'
    'K@AaOyqW5Hr^eIT*F4AyKQBdQ`2kH3uojVHsv;b_G6?aPEUe1NOXGV{Q$iNs>t#coCj&W5bbK@*4KUVPsfA-B^Te1#iqidc4dJ%o'
    '^a-TSaexaKzjB3k>$&*SmM{A_CKB=1f2~38moProe(uNp>Ui7gp{8C9suwR6<A2-i@Yi=1norevs(Jj_2FdRklFMc#cAE^{COEjA'
    'CC5a~<+{jtWdw5?hu^fM>7;7vyPQs=)+G4sFJu_3sXWZ?OrndkHmp1iV{BAE)-y#vFHHygV{;KKT}!;Znp=kvq7)4Q<i7r=ke%nC'
    'CMfb}SI2>}W>#maXr@lQPFr)k3DTRhZeaBhALg1@#_mjTqAEYFdb8Kx#>EPyNik{xsanZn*g|n6ZdW$mt{TPGhTg)WGC&VY_z;KK'
    'iSp2{&Y|Gy<Aaur(jV5~c(pKzYOlYRtL`%dpw1GWXV)k-5v`71voi~OG$o<mgwZMRRMa21^RW0tw`lqJj7vfR59%ul0)*{(dX35#'
    'IrY3x8$pZ^WGn{qDk?^uksqGIzihAy3T3`3f*dT^J;iA!PC%-gHbx(?K6;G=pkVDEe=aj$a7`GxeND{%%k0Uo`zp505@;skCRb|p'
    '?ShByx4>fuIY4NiZs$to;#AmJ5)?%{4+XBQr+a$p+i?j+1-%&Qngz5s1itzLH*H&LPEJ^ZKxYlwT?8?3C0*`TJ4+Y<nmLW((TpFA'
    'j#*^oi#gVjLQo#6*Jw7k6cRuRYW*YRWO<s|$fzEJHp2$;BHJE0!ovZ}D4{$S0ow6CLG3SZCHdAiP*seH&w_8>4Hv!aR2Dp4X<2;%'
    '5{n@tF+ts4`fHk=kf^jh+1(|}C*^uSB-r-k9v*&@tu1i_o8yTu)}4H$cM<>Z4^|ISAE%>pq9%s}L9EZ{A?;Veueg)MLr*1~!9Y-S'
    'x-E!^Oq=$a<niO$hN<ApJE?mo%5-w0L&ToqNPCC0K6}4tun1^N6#gKNQ+V<B(sEI8f@_17(Nn%jOzK|I(`?NUsI1Q-XYW@KDIZR5'
    'BxxqEP|0_fF1zf`u6)fm<N0B7F%~zbEY}Cfzq`uAKRyRQx6Bgkj?@=GCnyX`AKSj5$9~y*AOygq3;Y(QBAxQ*x0!ajO-Si7W?DBk'
    '&CcPW-I0GYB_qKV)_y5sj7Z<)EIW#7PZ&wuKinDWN@eDRpPSh&JKg=eY8>n2%Pn(;PCgb#Nn{oBmk?%)-4L|sRL>D=j$6j2EZ_n7'
    'L;<<kiF0+Umwg?nuy>K9BS0hS&arLqOkz|ZRfHiL7*<t{g$IVEo1vsEy=7X{Ot^4Q0+X!cFh=_oaBDrjj1%^8k91(`A7`CB%5LKF'
    'TXuaHu#EM`bWq`o#ir>t(BDk7L!%o6{VX`U;C)w^ZgWC9j?Q5|3OMw|vvbnJVNZt3)-SCsDi-y;geKcK7GDS;81}jl3Sz(EbrD?&'
    'Irb)zx*&iP-pSJlLv*n@WevZq3nbg7r0e*s^+sfT&!DlV)WE~!?jaK=`J+WZR$+U2Sd8<ND0ePfY@&d)Qvg}WVccT%g)&}8<dj3c'
    'bw1X3l^uzE(MUPS*Ecy@AgL_cHp2IDIoC=in+W1uKwrHpk)r#+z@$Ii5IF6tHaHRo0I}4*Fz(mu>K>vnZ0hbHsXebA8EymkVRh@}'
    '*hQcT3gpJQd=s=)_VGExQv(VoIB4-(=AtDO(v5bx%uczdiVu*}V0-H}(qv+ls!L&aB6!*-7c+{sk7L^7-%SfYI$+?6My*Sdx&6(N'
    'ALJCPo@Q?Ki>IA4GV?G?gE;(7kII-d?0{Xqn$CDT^n31rHD0OXLYW7hAC{F=c`Q?CYr=PlOI)+0x*qGf1@&k6^X^~CQ<pF@NB*sC'
    'oVYqpgmIHWedVBO@+?=SU0jGke-X}SaR1ac(wOSo>oe+frU~vaWPm{Y(W=!cqa9t?^xTf&oL4Zdd_^Vy%SEy>sY@sKmY>P4u)NUp'
    'xtz`IaibO`6X(IPNiAm%fw*P;)2dT`^1ZufX36T6oCzCnJ$lO@1-HpRg7>I8uK^=4;#BuP!o)p|VH46To$Uwi_n^ho?Y-(;?W0yT'
    '8Iiv*+B4o91Ho{6zXHpN%LCtZXeEa)Vqw14l6l93j_GWsh(E(&>gTI~77=U8^)*iWk08d<mbokbV<ILKEE{ax0U^~=&@DOvuH7*k'
    'Z)GCK-gmR<JB_-!Z&Cy1hhq)1sd)6}d)`*4>eaFn_a#J(V{*K3uk{MWUj8I@sk!XDSy5Spaas&Va12()U{rZ)Zl593jA)!Gv*O?n'
    'eg?hXeppWLAtf51-?jTI`QI3r6^byK&6b8QsAH-TpK@Hd{WdJ6#>Awf*z;<aT632sM5ObWIul)QcVJDb^7D@pAa;e#aU7euRq<>b'
    'vEQ;xfp^|A;BLlT1W^|$2y;v~xMGDI?7WzGsmn3<y3QVE^;m<jKcZbaS&M&13Bg^bl0*tJbm5KSvX|h4963>&m3Qpcu$+<OD0cY1'
    'Gf!W3=zk$ln&bOySP%V%uV-L6l|1y+JSw{0KLyMJcSw(qU~RZ!BW=C3VbTo#bvpPe#%!@E%v-U0_Mm=dH4VI@1)V9!+HI&F)P?w?'
    'cL8m6`2uC*ugqGx-#$#Zd7hDwDNhUB+-Lp{Q96Xen(6L<eSBSK3yS?16?N6xZ&GpNYthChEtEe^<Omy&B2d%nm%y(56RvTtNtVF%'
    'c8hn_sKOljMp|jSdm1Tdin1kF==cRxNa61k5LfeL2|z1{)W@wH-FeIR={$qyKjChCNe7yve=1EmI8fBP(0|8FZSz7?TRFV09b$bc'
    'w5Ie)Zd{!A=7C-#WWb*WviPceX7@>S-$E17o3JbwZ>qr+P=Ko^p1*phy?T2l2W&7*E=S;2L1AtU)A-n(SvMpZ`RnG+hE|SpegI?5'
    '&2Y<T5PqH}I?vDm8ZQO+eG;nqB^Sd*C1#CmRmu+OzH=B`f2#+@|13MsC%vX=%Z4#1_pJfAvslks4;oPW%8#%%b}5+PNw-!}KOUf!'
    '9`HF_?R*}#aNN|wGIYl6k9O6U{)@1Ch!KVXwglR?ZQHhO+qP}nw*9qj+qP}nJ^#xrCV89LRcc+isnxm8>h|UPKeOex?HNwoY7shp'
    'wxqyH`*F;SN(OeWJA%fJ-Mn`tDpt|w*Rb>TPre}ulrhx8Qb@zoRb+O1v0Vw*dQ(E+sdjP7Tm}f(FJdVli(QS>$e-@i*0<>54RKPi'
    'L7S$k?1>HFjQ*e5!vO+I)Wj9_@(HyOsUh`co9QjY@vF619Jri!l&US)6ohb3sTNNet($FYYbwL|e*E$A(0U<jl+L!G#f)VDVN>|l'
    'Y`dVOjc6s^{&}Jy&XpC<G&KD{sUZn9j{y;ONQLfx57rLq|KQw^fW=245K#$WZH4zs0E8_0O4rXgWT3yrPN{o<fMm5*2N|Dmo%Dm4'
    '8mm5C%fXz1@mESoCk`8J{*uZNGTVH4&VsyuZB7x>jl@Q=fihgVc`^QwwY%XK`odzbE2${tlWk<v$7$s3)dF})BM?<KPAU%O)Ul#x'
    'IaN7Tdx7Tx5qLZ`2ZL}TU+BYK%%9n`CkZhey1Kb$^Zh2c!&$tV3<kCizEHt?dh3=TIY_~Qhi<86_7_P4>m8M}kP`r8)Hy{SXM8nX'
    'g>$M~kA>ZH>wdYte6TQs{9MzwUaj=6k{ro0rk?AtH~grwRQfnILw*v7r9y&BDmQpYD+c19rMq)369Zt=lbme4*c<FaRLI=fy3642'
    'XLJkqEDOQmcc|o*I5f3rSpqWJ`IZd_BH@u9B#Jyu4s*%`)CWU(-rkE7C60YEdOF<0poN@;Q(_4Thm(obMy{i;5x~#wMGe2n5qqJ9'
    'GCNdPi##MYtRzYqSxuc;3xoJmX<PZ@AvskI3YRi<k-mxWQXzgedeqUzTvTKTDwt$t+4ot2LZ+P-2|8_oM);wNc|Vt*Do4<v1n@a0'
    '{u$woC{*syG<NX;Ilbh;9xQI^#<8bj;;C|-KLT^O{bI!2dE;{>f#^IuJktrQb2-oMB)DmaawyJ1i#kOC4Hok%jI-~ovo!)0!FWK@'
    '$s1KR$0)FZ$RQgwj&fRG)1p05M5b3CM3lPg=kzfeW_B0W%OGEUy#rYS^NyK@i^01uW4p}sp4-Ni;PK_20PHX9+(An9XZPZn44I2e'
    'ar%FSAt(U6-ho@aUt%oCp|#H*?Iw`mff5bDj)};z!mG%6rX!E1hQ>5YqIu$n0Qa!}geNAzIUA3pg&}+f#NJv|-M#oix4AnT8m^_d'
    '^Pn8@rQFY)*vH*a&))D0Cjlhr*iq~rL^5Pit~d@zBO_^;*>2|d$L6Y78$ml*qYpk%V3(kyw0~mffDFyZ+d<NnQA<gY(2v+&wSSXK'
    'Qg3jp$k{&?hk59dNmiJ3G{81m!D+RgmJy_EtRq&mIk1|dn@O<-vO{V|w8`fO6bqpJj(8Z;Ya>j*FeekEp>4HrS7>f#MmdO_57g8E'
    '$I*GSy|ARp0LjI*!_edMu78V7l8jJe?w>KM-3!?)51jzBV4yFCwQhdE3}1)erRD~O$7gBY?4fYrTKzMoD}0;K${xZRBmQ35k$%Jg'
    '$6iFd-Pi3`*ppap-ip<&P~-iDZsZ16tARsxWSHdtvv;uKB{o;_1@WZ>s>O<k>4pu$gOLrC(Lecg|EbG)WH5nuJ*-bLy!DNwKO9Ui'
    'SL;`~^vzXlgg~T45WjdJfB#2297Y5?T4KQSbug6U5EEY<9gy}@{Unon!uUz`lcddE8dFdNY^bp(Ewmg8$m4|~S0O1BtCyGU6uj?o'
    'r<DfVV-gACp``lp32sU<Z?L$n(w&gqGL0Ko{k7_)>ViKEt-GUhWivOsWs|Bd^Jzl61uBG^m{Oxg*14A1zJYVTN<@PPcK|X;DI_Xr'
    'D;{XQtT%GzA0u0OO4|W$$qux>J4BAdH?rcx8GZ$cfEjNvGueLVk-@Cj7y(5Rhq1*US_G1o&dj&3hC>=fn)<<k(CRc_iYpati^dxN'
    'gnmN4zci>N&Wl&BW4w7py~~+Y*ZJjcd*E)i2c(8YEfgGI<L}ucuYF1pfokYX=PHkr+U1C^whN0Caa+lkZBSN`rwex%g#s5cuV$n+'
    '3?VoyYbTC|*`__1Smr3|>DOOgDl=g^os3g@<VXH0f{hCF_ijTPltp_o`MY%t>^vC{yO^iokBple{VtKD$dwGkzTb&gltH5xgBNpt'
    'r)8jPb?A6Mrfk||M@b}dZavPDD@`etxHT`54lfzAOwsBr^c_87|9d(xpu2<NhNA(2I(HAxnsw;h=?J-NeFXrjzl3(!l>GD4M4%>8'
    'VSQ@re8#b}6N*3|TY>8#Jd?>=uYMdBin^VQ<CuR}d+1l(jb9SJ&-mIAzEJq;df~zlA@<7bj2KfNq<;k?6m&5!KabYRGEOki+3h35'
    'd8fTw<1~2Q#duNH%qzlBY;8lsnr8FM-<F3F|7LsA@c0fp%)u%&eZyjgpJ_@Jy}#6vVXN7kb)P2;gJ0Npqkzb8gZ{4RVc1B7Ph%m1'
    'FB;)T4&UHg_zKC32mz02L-4c8%s&qA|6C&d)L>{dg599oS;t#7gu>H9MRm0EY`vc;oYQMjHtI>~wRqW~PVS*f%HcV1z+DMRG`Z)_'
    'Euq9SWIdQP-iCJWhjgNP4^Z^44wAF`+2JKfDk-{#(cfvRRn42Hc@fZn+NZe0Li@cz?=Hjfo~_$R_jEjVUm6-tW6q69A8b!!Ba2&i'
    'aL}8v^(11cX?jk=Asues#>qT{-%#WiQqY&h^8mDB=R<{MV7I^NzCR1fY9RMU5I42~$}2(4XwW;9%F=9ef)Zs8t5_=Wu=c7AH_Pj('
    'j4Tk#BmXL@HvJNhwtetCEb<+N@pM1qI{)%f9QAH%WSY-hk7@qHaZ5B{<XJtW#cRdgvtMrk98Wib0QbkYlaJ*2VY<Jelm*_#0B;lS'
    '%ItGM(4UHKc!D|d=Qh<2ysz7B(X&Lp4XKFEs@%^-YlsS)V51pJ;1N}%B%3?rO{lLnJreq`@p1!g1l<*%77rpJ(np~>QaxM;?=vkN'
    'Tel-{v-!aj8rpFx5iz5F@7yq&d2Zr0R)2rO_Iay>g)xe`urN=QDH6s~5)!7s(O;66h&fUDOFkwx$Y(a-b?Iv|n1gEvA?t@JOwX3K'
    'd<-DT&q+W2Cr7Q+ayti_8swD`d~m%}rIp_4+v*emsVE}T4xS6;Z2@RdF127?uG6M?fC$ee@Sl3KTly*49dkF&h8vOexRW_cgf>$#'
    'V7=t}_iyV3OWYty(d+&lQW2B*zQrXJF)Jw<pCtzg@IrNbGjw@x{N5dxZw<f>2$WJ@g!Gb^hcO+Kqnrt;tV!{CD%*^QKL%r6El*&g'
    'i;5u_899&9Tfxw`)`0&>*tJEBO|c?Sfi)-9*?k2>)WRm_pTL!{EzM~Lj#tFJ^n!u$q?MKSL%p>a{0BzhdHLlZs#vFGu}27Rsxk~='
    'D#qu%#r^U=<-mI}dB74V@<3j<^NXrVvW=HPiP#YYbDM>t_P-;j^*^*x;#6voMU8PoEJl)EHneubB^eGHT!g(GXMQW<he{W(P4b)?'
    '>R&{NbCZzBwARdaqhTJ$RGhw3JMM94U{sQ;n{S1o<tCm2*^%_<6D;YD+SX$d8@o$Y6-7*n!(M07)736DF(e1>Ng)|&_C$KoIs{q{'
    'a2Rn(CY!9K;YjJKI#VZ@DGRO<VvLG3x$dUmuC57M_>`Qj{C2Uwyz?U3sLho=IZZOcNQETU$@SRGQmrdJ9=*Z`@=2a{5_{<1MIQ%-'
    '+Fqyp%SrIBZ7{_<YEzFoq2@QZyYum<^fkLJ+MtgDta{HM4`g>%c{7+4CjLY`&cq52ysu-vv>mVhr^ui8j)~g3!4kG4f4)!}hbh$x'
    'DZ%+=Z7FqW+MA8x04Xgi_<*g-4e{M(@uJ-A3r<knxh|bRcUyWceSMBlG?wYJWw3kpT|XGG7FY|3wde^nVGn$Mrw@&Knp4%i91Cga'
    'o~a|+uU5*e#{+K=Xd*Ph0GPD(9sR&kCaXAo*;DKT8x1(X7ZJwtX?jT%KWQ7{mu41?`qceC_`yB>H@lh8X~J`mTBJK0<D4Q-yIHAQ'
    'i98eE0{{yXotp^x>%T7gkP;;Vs}+^kbGEaSWVb<kWz_7KG?dUtTj%;4D)@1&M|e3XEJf8dLF6#F)?!RXgVb%*Qg7CPhR2AIvJo-k'
    '^OjMojeW%{PH6sic!dL`mV_ATJ)sa+x})SmNh7ZdNWR7$WOi=z+Z1Ac^ljq7P=0chJ`<KSP^_%}FLmALF^;iqzYK_Y^nIymp#|#@'
    'T^;X_o$0d+@!%gECBXn+u>4~=H0EPkL)InN9k@zh0W%7MWYdlrgw8E6YSSx5;eu`ngzZ5m^Y{+lAyG)B?+Zpn{aWrJij?Ga{x{92'
    'dxE-D#3DzsM>tE%DZH9Vb|>8JVGj*Gd{z-s<u%j-yHDP1`dfMA6-sK3A~x!E2j|#;&$&;Ifgm9%a$RPDI(n1Js@ueUHKEr#qhZ6X'
    'CZjfZgxF~=^fqu#Qh!KCW?vTR1Js*fZ_nKk;>g>Z4XU6>Q5rlhfyM|yxDRyE9Abn{N=hrFQ`KsaSrosKF=2F}V78wFIEt99^pIZ6'
    'G3%zs#3~4&PiryO{4>)wOx-IUb|Yr5hr+OUF+dmQ*bk6BnYO9=^tVy1rRlv-2hz$R4Vskzp~^;lIFFogcHV$epEA$JrZTclgnEjy'
    '`{!>!v0R$9sCAbURzlBK=$o?{5?iuXA9xopgQRYOHU~rEwb?e`2j+_|(Rgb}$m6>*rUc*_Sf*E5dtUi`AfoCQ<35`kjOl@43b`X0'
    'RB&=Kt99ptqgjTJF1gPZb})(!=d8>3<s6jMlBNdz%<%YEU_niDH{$4Hvv3#w>6g6nX*3|8P#1dN3;)$^^+j^Sra7=mp`FMJd+Do('
    'kccG^3(K1KZic7JROam}yfwV#(^8B3H9XF&WY6JDT?;MBo_-{~*z_~bfqfq=(zwffQ#?WQsGm`?2!y>oYw+jvgew}2(F<IU1)<Dp'
    '{He<Z<*j+uVVV=NGGmyko6{Rn;`21^d_nhb47M~(qhk2bV>(m2L!{17$EuOlSYV3RBJ|0)jS#gYaHFwN^7_IB;^`}9bW{{UP8Hv}'
    '%^;io7P08nswVWcfjYT=LG|V>^RlCk4H)W|AZzR;KUGL|Tegu&m@2+Gsl10n{)p6%Aj8rEVLlEZeZJ~iccY~No6HnB>$5bIZ>}%D'
    'HaR2vZD_MO8`xa~5$?>O<MydGE;5~lI17_6+?YhILr^evalh6(_69W$za<Rr8jJ1Ts)JmRd6_D@RH(*TQ6H1L0?fty+bt9`MRr-K'
    '4##EfgLL9t$((rsqrn1texU^gFP<;)fsDN_M;ysOYU~Ua!MT3NmCzhvc??s2X))FbhJURA|4?O^?I~3yts=i&Mwh1gfG$emWAY6U'
    'yDx}vDBJP=dRqyd72=mo<uHYHz3E{q=uk)eplB@wDhb8DW${<@y460#vH#YLp$WdBHzp>L3A8<&)d~sHV3=E_^Xjgrxr`E8`3O{Z'
    '>^2&oNz#bB-V(484)*G_wO-ul{*Ar7=2-Cxxj!GlRXi%wwGaDh7Z%Vl9cm4^w!IwA(vbU@c5!5_#>Nd6rTa*$0H7H>?`^>hh<q1$'
    'O=1qgxPq7|8;=3->a}|<4$G#i0|_BJn7$+_Mz%$n9bNek<s;)CXu~`=7D06LCAcmHYIo|Ig3tx^4-Tp6TiYWkD{Lwx3pXsc;pdFl'
    'l&e15TyC6sC7qwzm2Kle+6J!8?p>`~KZEOK$u&ET*hnFQ3rb9SX70Tw8-jP|!k44VBIA|Lv5@bC)+!WSdG<aWiZ`4j)+jjHPbKwU'
    '8u&My5_Kw3%F8K7cpi2z&)wJG-Pv=QKU#mcd6WwxL^u~uA6`xN?m?tKG|Q9eDWT7&Qt6z3o$T?pR0+X=fyxy|9+1y{<=>nhn~VB>'
    'cvfv-a6clVJ?lN@cVERH5?Z^xGAJnRy)$FLHQH=U_{3At@}ObT)hHwNWZ4I~9POOU`2U+DJ%U%YQjo%p&hyEAQgSM62jDvIRt(pL'
    '>5oGiuB0=Io!(@b$4_tZK;&hAd9%`>CN}F!5fu9@?xw=ZNrdC_E&7gWOW2HXCfW<$)s@B+HS(o!i5`TLm?p&}-VL-j(}YDJQjd&x'
    'c=i8zv;l*T-UO@KdyOW5X#zWpRJ%bgE*Q&AxqAz5s=vd&qL!xU1fe20xszxGQKt?-0ZHEp8}el;Qc0ow+6wgQ&*<?YH#lf|M$8R3'
    'U9}v1-ZQnTyNzAzzE+;lJz_6)leYl2+1b#TplZ)#b%;vf#3K>FZgPMnYcRh1d=4TgoOks_iZaTwL1eKE@w1MUf#H~+u)Ge=INzIG'
    'c)uVs=>!iW2eO?wX+I+OoBJEiVg0`F?>UO7u6r=nrij9fCHKh5_^oh{ZlU0l8b9HJO3+{!=MJhiPT$(0<Bz+_eTyt_Nn1;G02Wsu'
    'mV^M(mZL>_yNB<a8+ofP$Q1A;O*~U6&IqYMap#&+67o9vIRMaQ%HK-lFH3?)Y!mKB+jB58s7L%TtQY9Q?YJd=X{;h~;YuW;t2K6J'
    'W@SkBiv`bt7$!OTaV}ykzc#=(7Jfl{{lK3tph%lSQEVoL{J<p2(SGs^ujJiiG>oi32%LxF6g>~v3oTs%-Udp}5&fFwg>b+>*tXxg'
    'w(gcYJA7vPT&1T9RetddcMyM(Cc=8Ooyw%C$WhU#$@xUwx?FycWmEq4*a_uJuxLDl)b=|z9lL7U4Vwvc$`zOGS(FhO8>;XR0PM`G'
    '%9w=5f$>Y^Jxw*;Z%_#kVJ7oAPgiaasJDg-3MqS;&0w6)0m?nJbS8BqWU-YilV?nt{Q7I!Z<0Y^=%jt>G2G?E835^$Y(fjC0E!hL'
    '@g_tdf8(~q%#jZJ+97J2WVR&Y^~9Pnw)y%FkVnV>0_tpLMkA|0a=P#u?L7dw+?Q!~Xr#q(<KjQMu5)A_YcCWcQLbiyyRPHlKz;NM'
    'lnOV*sac%Te%quKO9=rZJ>-?<h(crzt~EZnPE_wEyz1rLQ$o%N(FDyum-Ctbj_O#&#rIY!(mJ>ioGiU`Z}GAr*Bvyx?T&4;zF9~S'
    'VD8@d!xfzOoK{j?;*tm%=4chy)dtS)*n5Fs+NHC1Yzv2@?<Q2EmAq{dEv(FR7li(#wesNDIvnqAt}D$_k)9f?ib^fqgFr7k31@cb'
    'HMo%-?Msn6SP9Sp9pSU9dSl<Le!@+3j|pS7gBDWMUt@G5<7AIV>8@&CW0%OvVx7lETAIn$n7UGL*B4}Ltvfn{z>Ip@i=<y{IDE|r'
    '^^Gj$l@UGIb0l!+*yhY4oow(==y4k$Aq4|1^HVQWKyP@j_IhU_4lE5!W}8S;uE4}}e72(zU5;tdOD?wCzHlmB*^M<YyqD)L6PU%Z'
    '6bn(3WuukVA7pQ0t58^p>1VIg$57Y0ag#lJbJWw7*bR!wW2-yPem16o_r6R9FmpP5ub*l^Nkt5YmzJdwK0k!Fw!Gc53EkR<WNHF?'
    'EDp|SeUg;w{pnM^TWI*9G|tz_rG8L{TQbX~g^*Yd@7O0~vm-g)a9pr$o7<Ckb~x6R<nFFA2`jb~O2#F^<mW7l&~2phPgR-iVIbqw'
    'gI!4Gj|_%X0x~&`NT*STm`>G3dB4@pI9q)Cq%I4Wx0>YS!!;yvX0JDTQ63~Eq3uf@uC}bmC68;h)fWZZ+CPJ=n^}?hyc9Bj43+5V'
    'mhtka_&gvq5}WZAS)z$~JVNq0SHT&I4fxIKA}&xmvTdT;i=9fs!Qtozko(dE<HIP(Q^I_)9J@Ow+4(~$aG8ZhsG`e>U|^<*2p=39'
    'OR&JI4!^W1+Wf>*{Pi12Y6IAs+zU*jY*JATK5>kxoEvi19>$T;^McQC`I1nqx&i#5uW!{M&$NeV2qIWy>eRhsi|kDIv;2y@aMCqS'
    '62TkmR~W{2rfUTXk6i3?&??UKBY6^<;E~d3VZCy}2okMt`D+uWhItEz(x5RO#0dXbKeAp{HB}WzG;9wTLV^GVVc@LcGSNKYHo*O5'
    'KYnZjxd#_%2lQkiNfU9jqR~l4uYw%N>*~^luwk_aWhv)}1)(H?vAWDE`2M+Zmv&+HFKCm2{QT!Gdy#>Rk|<vtMx|V=3TGd%44-4*'
    'Dt(TvRRbSWZL!@nukIc83_z-sm>9Zs#x2+X7I~uRpuvHd{%t1OiMufQjWsvn&}0Le3C)F6e%dmzQncpdJ7VgYb<m3?Izp~Gr^Cs3'
    'b@WvXI@TVIV#iy`whdjNS*xKfmf-wg`yvI$s=lGgESM1~q|}Qi>1or=f?T1xd_NfP0IEb+&)BkAr)Qe!CoVlqd8g<{eG*wP)&dts'
    '#W>3xj|-B%c5MEDTcI7Ht$u>?W5%j3iVSzz`pan5^R6)oK8AW==OGwA8N(xm(x`n&A~mRoh4>UJO{e=-xsIw7{Lg`ZS!2kUjF3N='
    'Ie-`vqua*+qyAGbg9=e_5N8mqj66Kld$cuRSFS3Rq|gbv>TF(>fqrg=Kur?(xlm(ioCOJ%XCb-^>&I48NBw)nH;LG^eO>Kix;-}z'
    '6&=wjclXIc_qnY3YYkGKMCL?t{b{<2A~}8U>tgH0A-C_S86Q}`xm7T~fhG0Me~9gC_$0rpY{XU*{a5Db@!7+iINd6>*3cqxuJAkB'
    'CIe@P2N!Ud9_i_V&+NvEUbcM9r|fb{%ra^+*4k!d{R6-LmpKVzw>I33y^8t0EE=7x^(j9X_wg^&_Q^^3va-I7D-u3K*W!Ey)W#?i'
    '`@o`;5&l+)=~NG$;}_qS-LGcpP+!NUTEAeQlms04Mqzrfrw@RuXMKiOeW3~oS?VGm^d6sOvw(M5F`ILn4<OQE019zs+*rl`tK7S6'
    'NR$!qDU&20pHAVyc>_=X*EBX-3WI65$4YS4_fi0QyB)KDtSC=<8Z+G>BJ!<JPs-D8bwwaS&j?0DUuA<Tg5^vh{;Syb7X-8t8=tdt'
    'D{bEvDhj`28Zy9Pn)s!lTt(f|UwxQdMtjYj>Xl{JHpY~$!h8W8*G%IqKg)3U*y8J3qGMRC8@AtaLC0LWr7nf|%YJ;-%3S4Z6#$yt'
    '7jC3znh`&?COhoToyN>exz#&?ap#~iu-_rW=t;K_t%yIlQr6;2-(*U}w98$CSO>rr6Z4vV!IsGi<E3PaKL8YznzXAUclDVg@auhi'
    'mc;r~LVz<ocsDInJ&yBt9{!lBuSN<8UNB-ZnttBPFBmv`{=}bn%o^170Z6*#^aR(MICt(f!fZK6i*?ZTqM%<auT{SXOJ&h6V_@&|'
    'T-$KM?R-g7wIIUT&&#*a!#hq1WI&v_VJpKG{!PDG)p!6!lsNFg2dh9J&>f7yi$Q!}?6T0|5}SgU$lGr7F{{V(Yt;u=D1L(G94x-M'
    'b%ZL|2-}AY4YBP?NsG6KKI_==QwLHGgeKD1X)m3_r}<eBVG}@Kv2u~vv(F-0kRc6RTVXXW!qwiu!ko54a&!MSAjrJm60ygV@dIcU'
    'Hg<m#!daETF8Ahp{cqTbUjE95$@1NP5pitr0+*|R!A81-A@z!ACt|jtBH|%%d#?-qRIlgnQpEGQ&u$tXcVmO;5w}I=H5CGfxHF|R'
    'BU7`7hqk1htri(R-8@UeNDX*h1+jY;Do(-77&@vkTpv?|w{tAMSG-uA&GN8L94x#xUoW92L+!w_cv^FbsH2cGY`9hH`?j)F%G&??'
    'N@m3a4!*#uXT3;Zz*Vl;36-%NTFt;oh#OnmP@OOaq0z<w^^gN~&J5f%!WC{@6U*Oi+rU}$-(NL$k>AlKAJBl*Q{4s8?9Ucua~yb_'
    'iqpzrh7mEVkn73gaiU&KKa3}1RW@1E9#hF}N)SpvhI&jh$gjGB*q~q99r5jNJ2RG;7=F|J)<BtVm4h^ptv$-i;y8cOONM_Gq}t}6'
    's_keSVaQbBsJ||K>L=jqca|b-8@xiyq<oO<5xzd5>W`ysNS%}l1{1tJ2zH?#Fe~jgFjPtrAU{C=-}C}5K{l97&l8d27SJD!eX*%@'
    'B&y4Zev)zj`Yn?~zRT6T=g0heAVM+OJbKqzv5nONHu~tFi@--@HpBnc2qO38yH)A`+tUC4Gy=E(Tb`>xUpN0h8i54;|I-L~{+ki%'
    '|95#V%4RDJ0dPnY;5wWDagW~q+|bW}Ux&}OhJLZ{>+j5$<)ipdcu_9m>D*CYj(_d%+%NlU+gbTn-<5ufKXsp&|MVN+FX?yj&)I9;'
    'Gk?n-6n_KXWp}^7-XHH*@}1%@@hk8S{@a~G{AvDq-`^{m7lPlZm#yE?H{I{f?}87EKmG5+U-UZg-|q*$wST31!>{q<U32on?zY$0'
    'x&2aK--GJw)3g32zjYs@KZw8eo;`s61b?c3-go|Y)6ppaf9ap;pX5j3Z~8&49VdW4-%s1i+wWemc%3(ZzwjUUpZ7QXN&Mp9v;WuM'
    '(yzsr#Siv({xAN+9zgySf35%Y@5itCU-~D09=#EMyZ<lmEWhdBU#`0&spewE`(T!+8&yml6dpHKR4?V5#@ZPkKU(&o-w(s@J%Yti'
    '%JxQUXI|j;&(E0z;!ag{P?}_d>3&ut7*4lo-*(KJzyC2rBTSyX2L^+%NZ3&xcnV8gYjpgD)Jpsu!l36$<?)LIT@%7i)8FHC(wUG?'
    'v_bbvKKlr;^v@p<T8;Y@33$S)9b{N|?tqUTLV>t+88tHRZR~W_Dhk5E89pBb>!2s4M--#q?vJJRQ5H)z?d5)f_8P$Rz@;`DN^HA`'
    'O_su97LI$pBqPmULn560Uv{N>)chc1qC^Ob;8?mnDy<f;-rV`J=;x7}6N@UeRf2iw!l~+A+DrQtktgK@ItX1;)2^LsT!BF87E$$3'
    '<P6Au2ADyeIn1Ut)5kYW;Q)nus+PHgQgURBP_c{2j+i=SyPwLmec*Soncp<c&dGck2#`w{!o28-r~p^CelcBfkfr)1mPEH}wFcoj'
    '<uh<)4+zJ>XfDA5TJG`VeG<G_z7eW;#UxH8pdoO)1!*k5=K;%1>IoU-=XYhn;GD$V47-+>>6R>KBSL}tht%8t&A)3R-h0vkM-fep'
    'afcQIiS-=|?UIQ%DjEz$*1{-lwtCgj6y4Tiu0{}tZpz~{KkK1+{W0hdkZ=!LRc8wOOtXM#3Z|}eB3HmA0FT+=cjal+KC^LUv=i-A'
    '<R9>VlXA*23BZt>R;Bf3#T0|q|Hu>PHhEPPQo|?N=qnleok{!NB>&L1?|j<jzAzE$e>hzW<`=Jni(w8~GMBd>S@b6q>9FcN@!J6}'
    'OAUvG_*PfsXQfhKlUu;ukZd<xbP*hviu`Yu-02;pQMt-N$kOVK!vc$IgJMKN%Zujo&HGSR?vwH$iD{+TrIll2fw7_re3mp}juv3w'
    '@Wc6f>E2_Trgv#fdSnn!sv~0nB&A6=z{3Tw2@b`PlK3z_tSz)rn^kQO`4)Hnye=<cK^jv+64t7US`L)YH+ocejf-ZIDFF#cV-pI!'
    '$O-R+^oSam%e<dUG7N#yc*S$@;e0*I3~|al+`2(}bYuy4)r6Hj<ASf_hFjcIk-)8@wyxUg+=>j0c2gYDz5RemL=*sf2|DiRUIk?N'
    'Zkwp>Y@F@@D&8{(4XGbZKh*J;#NWu-zR?6CYTwAH>1i=wn3UVL563bO-K(VWBQi*H9D1&w008PYQ<p&LtO#+B#WSByT8h*EJwJ0!'
    'o0ySQ;EDG5KjvYWD_aehDr-kk>S{Uzl?t0!bE4xB7^}<?946C4DzsV1he7`1HHGm#q8?J{fgzOdUrm?q0?I}BNQ!Rx5bpYouhSsg'
    'l<2Xv)wcH5*!yAF|NDDnky~M2eEwzbbjQ^wi~~IbE%=jXgR<fal2x<4_t<nHOtJPl(q2X3tAgmk9<}inP}3YyE)r%rzq6j&HvrIP'
    'M9ItGqrsjiG$rc%`*IVLJ*!MOs;-Jgw*&czj+U1mnFZ!5#Qb3sB**$62Ou?D{UQdgIOu&e<(Q9yTwki|a~f{bkJrD}=*Q0|<ZVw='
    '-rLZouAhk0VVlV_$EKM$NR!vf0<c6a`s=#0!p&*r9&9%sGBp_I1f7eE2js@P&aU4`$!0ajcSI@;OyF?aB3d7pqD*oF8fESKJq@w8'
    '37S-x9d^?mrQwp5<t$nqM;jz*N3>9;;t2P-*Q#e*aQa?b&di$#@MkC3eGsUyl6wJf@;DAZ<SV8IL~28|NCleKkTFnx4OYV){<>E}'
    'p#`HaxIEQ9cya37TjbQ71+r$=FjTkFvx(KPs#c6G=Nr+~WhUkyYrHOmB(`q~@)`>ZQd!P!r_unCL`rn~ugm4x!tQm|fOK5ZTWm>7'
    'F(?aO&f|=NC3$Dc=xU!1Mh<OT4dR!Ip7YmDVymWRVuuxs+MROLRPfyU`Sk@H$%9|e<-*pVR6w8}L{FE_y)77Pg2ashwOukBg{@5M'
    'Sc~Fg89?l<IeY=lG{`9pO0!%-=0M1br#%oQt!4l^X(vtQeG3q!<WzkGhA`8@UN>ZFKnM%oqw~-cO1ne#L#ggJpH=Z>0`BB<a|t3X'
    '!bq^U^J}|+Bh!Mp5VE}BcrO?2cr=3R*aue4BnqT!v9ifXlna!w>W<XJk(o+g{7*)!?a!xxQ?InJ+7||bYzQ@GKKSlfdY|=NoS0MS'
    'yggzCsAS4#<xKk@279u`Fk>@$Qt)1&Q-$|W#h%#3fIT(pih_eftfSdLeg~~`IdrN*oi*6`2WwWh-r6D9{^k7BYCJ)k<YdS~5&i`)'
    'WygDvd7_HyOe^tlJLkir4SYJi)Q|jA>sIQVFw6^ZM<FultStEzm>X_-$Z9=v8Mfu_?qp}4hbR|GG0#Ex1UU^uy7pF>ywEC^51DFP'
    '<9r;%>$xS3v{7;=_h;Tjy4fb>aj{t<M1JF7nKOcd;#7Kb0>qK;!UAcq3UHj&M4r4*^B*6ltT)>!d2zxFoM68U2{nsQT!*G{Ds5G*'
    '!rQr77LtWEP_@hRz4%kKV$FlVt|cgp_x6N~cOTA6kI>(FR(g#&Um-$a08(%T<U-BHTWzn);FHN(+M`xGMcS1)C$9Iw>(=zT4w^AQ'
    'W?HDb1^K$i@#|Kp&H+S32K4Etzav9+eW0_vc~)U`DK}bK<k>YK*sxSz3aTj5mhSR7K=F8O&tS04=lAoHlwYpiAy-z{9syL8>X%K?'
    'XhNLCYv(N!0m`ppP>Yb!_J@WU`MZZk|4EHH2y(jtL?dGl<iu;4C??bw_fIwkT*$tr-jIhfZbWt|hD%gk#|PNckE2N4Aw`HJ=Bn2d'
    'u2esZWZxL4ucX?v$UChCpr0j%bN$#KbTKthU_Yj0`mZA-cAuVj(2`5QCsePUT)dq{fX;d9bh0t@Fus$4A51x<gP4F)IUDO}BxiO+'
    '(cErV;xTi?1b21ekqMnfe)sbkKF-P*WdO9@qUk%*8|-%2oG7z!3az6FXC#AOR@+l)lH{Xum#5jiBuH@`qziE=imzj+b~#8};ucKh'
    '3iidySrr|$iJA3I{*kW+<-RL1%W%$Yp-3brkQbXXJv-!l!ddS^*r@Rq9IHSATYjykQ;LpORY>#gcNUH^Kd$*$qE-?9zr!=958z<n'
    '0X{yPPzzt<DL$PWZG|e8z3-;$KO5{!ZB?lP=?%bK@vMQKgWdw~jpQ9CFCJGcXl}(}(&5~o@#JYfQ7|rceHe#)(7UiV1GKHN$Jr)@'
    'y*b01mUzAI$*Xtr<*E>djj=FgGQ&%WJ{i858|xRyGN-+6FF-WlW&!Ah!_=x*t2*8Fn}UQqem9J_V`^;?Txj293QpS>Cgmv_Fnt=K'
    'BI=~Ud38Q6WHto9U!h!{6hic0=Sf!BB2?5os!pBkHNZlHlaW7m`Bgi^dL#m%SWqjW+cVi^o^hyeb5c<y4HdaXy(V&^ZN!?ck@EP+'
    'oupXc{>60I0mE>sDG8h~-f-1<T;$?3^^A_-h#}x7O?T3CwQ~q`Q5wR=%@cyQFodEoo;~$3SW)GwHS#&)@zt$vU-OZ%$*Dy)YCQ-4'
    'unXN8sbHLId3~5#`94Er8ipMzj!|l-lUr#l7t@`tX37U?XXT2I8;(fXmS?R1#xolSJwQ2zejMSfp?EPD>$LW<zui32OX$ALR%nYR'
    'k?e|bW(Y7lME_=m_qFm84Tp7{1Iiy=Io9z4==BGejtHb3yW(&aj9<@9TWF0G9`Brppyb8eg2oTJi=7qT^Vr9BM!6#Bbn)C^FIUW?'
    '&v=M?X^6JZuM42|mXE^NliPk9CPfL}{qjYI=mq8QKC2sf+DBdRV}oS5z@a;&5#)3a`49uC;1vPF*I|Q^Hm!Emw$w*8dyyMoxoY9T'
    '#xnWR&rsM~KC)z<_gVeJx@r$O{}1(pop<R`LB`Fov3s7~t8e3fVv`;#F+z|y;}H^iRia7dvp>gl87V+HKEZ;11dJhCKC&D-zgsB='
    'rYDH6fNpMEtf@Ia;|R%0W4hAx%eKMdJC?m;CCjzgShbUSb!*9~I~sYD%KTRqbn_|QZ@Pdxuv3@28+AKC&fZO72s*!F-6cG@j2tuT'
    '%HIe}I0Qtal>?9A6jF8E>qnlq#mv~Z_0{7o6ch-kp=L5+{EFOx0X-t%Tz{D<v+gnlMzH|_L`KANHJ6*@+bSb}@st=3qRe)=@`!)L'
    '-%45_MF059zfzH4v%z1smHeEi8GIRHvIok$XY&7QAipd?l!snt*IglyQSb;$P4~*X{At4WY&()L;zKFE@~cMB9<Lk3gyAs=alNt>'
    ')?ENF%t?YWU@g~kqx5;h;SHOslV+*3h>;pRzRce2=0ob`bc-6N$ce8Ka(nyR{!9Uk{5eZUBd_u)fMEn5OH6;<Fm7pU3EPgklbR{t'
    'hg@OTqfJSk6uMHAC?;lHeZnD=wom6u_PJJI1U4*rYFs`ASM-UHY61ksiDW-GcYb*;LB1)_n3*oC@4ap}-Ec(u!nx<9p^y(7=tQ)B'
    'M=!~0`CPk#KC1+6GB%Jf6!h%CNEIn9k)?oA@`8Bq5E+ew2FPV)lL@I|CJbWFUl^P*E#`iN>=?vpdCG`NhE{RlrLT-p-l?c9*YLEg'
    'x`=u|<cGy-dx{Cx(^aQCkq?4vgx-sdz3x1|ecK1=)QqW%7Q0nRc^TXmh@cn%^WUI0dd?kZS1`V2OPRPa!A3S<*=LJ$(l~w5lkln|'
    '&jb*D|9RT!U?n{1=5sKkuLQS)7o~CvsvA0%8sJv`9k{tD`^~fyO#!L_d;ou1I$2%*S!_-KveJ|)!m8V7XjTlk-hQgC6<lxn@nw^o'
    ')LsY7Y3$hGXi%^)c&LBWuAC8BhK?&a+bitm3&yUfG8d@R%&z5d-$YD`6N{nSGcG(30I7(BJPVtb)NXo3wEA}6xlwqB7L69I3%?bv'
    'UyuVX0^Pc6c5B21_{d;?JpJNh;2s!)x|GCX^jU-y&=ahhfrHe+SzBxwziwhoK7mDX>C0Wq7xNv@EdKitOrfE4el>EtzV=yy*-*Z*'
    'upIE4b7k>LQ2UE|b=6DuWg1}PabKf~_P)7JFNa4XsWj#6FkyHGr%ko5YoKv&E5edZ54>*JPkR~`c>T<%%G;#8u$rW>&VyEczko>4'
    '7~tItox${3&;voymO%0&7%bcdkDUY(oJEzVS#_JB9b%OFe)O|0FLhzmZG)P7X%{W>Rp!&aDvGX)%pPN^4VRJUC6OR#IujIO78Eay'
    'sF-7>kBV$d8a>ieIGM|Zr^Hz1Hqv3o*4XxD<wRaBwzX9$K<u&7wVFFVR6IXf*|m3|QB3ybg2OYEDoI1k;rNB2Xh5oec?oO38)plc'
    'APX?Ml=e56(?AFsloQ|Z7B_QLw&x(@3*5Gy!q~;XWtI@tn;Vqli+b~s32iV*I6qUIXCFCl_+2<gnDWxmCW^+|`NxcMF=0CGPSdh('
    'n2{L^%(lklv5AU7x<(93ZrZ$5Bzl+$SG%{N^01*un@W*YSdY5F<0`$<`I>T~)*lT3cRty&?OBVMRX{m|4UmoxhcJpHyJG9Y&g8v-'
    ')k!c7W^!*iDA>|!KnYPim(y}q?$BkTU~_NPK^chx-UXDE6RE7&x+&n<{tyP|_U6NJ0u==FdsNFT=QH^0#)wVOWp|Fh`5n*;Vb#uD'
    'UTQaK`pvZ5I+vDIQixw5;s8}+qcN+Ew)o0`^&>#?>|{p)eI$%ibO`D+kaXGs2TSv!p-R<C=s+ocOn$@6EYO#-S^nk&wmTe##>2>+'
    '^Szz(sC5yFb3f_OTl*`UeGiT23DW&|Y9*znf!i(iqz7+WGzwUyiAPLsakxGnwoGhD-1YGRdK%<pp;vZ19<=|0^Pu3R@v)}Lz|7Bs'
    'jS&2$ET5g3!>o*7M?I4<{&Mc|DT|D_<vMLf15Ni33aKA^w>9<i7Pox5z2hG+zm|#aDzTzw`G+Cz#f?lv|G_rXO?(65nCpa86p~Z7'
    'PBer?beu5ki)_6ocs_o9h9O6+F9l$K?Fgc@_tp~t*ZR<+R`4x@y>lDff$u7R>1>!lN4~a+myX}}Ys_yADBQ4`iH#C1I#3}KfkNBF'
    'kl_?C%zEE!Ra2OjNM^MwtC}~$J-NF?6LpXup|+O<ZGeHWgl-?lE_bq37CSqUpBo+i=NlKi?t$dsWYtGpQT^Xn`RjoWrG%Y7mi&j8'
    '0nUr>ojba-VwbdW>1^#vh$I&?$c&1LmMFcDGlYU6uoVSIX0uWD70LbU6-OUu6`~Mgrx<<FEGBVEWAGQ<!aVjU9IW$<_6wiiGR1$R'
    '-aD}cEN}n$IYM9Wb0B`()8&NwRCku?8a9M#l+i1xF$*IwkYBw^-D|ne${CfL03F!tSSJ{2l4l2Wp=`fj>C1P`yq2?c+ON=N>r9o|'
    'JCOsWE&&a)z&XGYW=kmuwFW?L3c*?zCiE)N88YwG%20LJYHoZ2==~UoExffdci$<J57Y=DXPOWegJ6Swt+cfmCJa7(+A_%POjeE*'
    'gbMmfl3FX>@5t9$H}OgT&P+O{b`wNRKN`VXA9g4K>W~^Q^c)iosr<k$)N>OHkCJhSz5NPbJpl}vSkYTVPH~xOi0t%x{Va2O9v#_Z'
    'x`GzVWa|&f!|9=+lYVhAnH?^!2pZ~Ch`G+S&BgB<!I2j=>hH%e;NSSS6ky31KEHv*a>@b_r>y2m!!ceyE4-3+!CHR=)C6=-l$xbC'
    'H*diCh#{s&C~hkZrv!D<(ILGd;Hv@y!R(s0xgn7d$o(SjnO(~5cj#pUz>Xu(_G9_+kwft9$8Qt<eYxybJj?r?@c>)=K>1Gg@=6s_'
    'YiF%S$$z~oyvXxteU(Ca7BfNHZn64g^&%y9W*y()?Hfqy<4uTlot=&@h>Tly#LktVntW0h0Dc6Kd5YtK1o7SQt)Sfdbv|~vT_@LQ'
    '4dj~wjP;pOP+EB5WuK6iI}O1)E2?blK`OWM_L*s<=OM_F^k(kC96X}K8MIp9!{N5`)$MrFnYVy8OU6iLg4=c{<ULukU8V?G{?S;Y'
    '3jE{`d(W;O<NqT<1{hjU@%>BXw&i&dWi)d=h#8hXH_P-|l!v`C8+S5I;a8}QLG+SBV2Z8GBvAv{0cntLj^rCOtgF<JV%B0hyXhSf'
    'p#w(ycRayPTF?6@VQ;#})i^=$r?FWSl<2zbvp)9pU`H(>Zr}a^ebe`=wZaw~rd@zcn>mZkPy(ZWjzro>DAew2m?~#ohr%sZnboB<'
    '{xdkZ3h4`Ys1`ObITL0n`tRi+185ym*7hW4qK;PBnXc2iJFqLxoAxkOaD@+Gyh_9oGGw7yOf0HxWDrz_wOslq{6>@2_*OMdZO_BU'
    '^7>tM3eFgmSPGhOx3eYxr&>obzarV7UK}$js}S-TI~Hfc*o@_w*g=`~5Q=;Z_>|wf7-vHl0(I&!ueT?vxfzoP$B>K-gOs;4YH)lp'
    'D@I9_lFs2CHpD|%rRN5giO2?zbhOcIco)1|h)na1zoCp|sfM7XIremp>3Qiz<kKCl>`vkZ*JM`(-4uvj>$qyzipb1`PUlxG9|&Jw'
    'X@KO4xHz?0z~0vg35k2bDeMf<l?8M6FAiNBtPr0?tY#tNGX2DPHYWmYrUXwaI)tw3hKG6hU>w^72NdzKaR_=yoJu&<DMjBU)g*o2'
    '$7+eo+(4T64Yp_dv@fI{myHnZky~gRn`8vQ_!wKIJdw4EQokraKJ6$v1Q3Vs-ygX3Nl99x)~ff#8KKw-BnDcL@Q)!kQ2738SP3s%'
    '&f%0;8dRJ73by;SMn08A;!J&FWrl-dBKZ|n{<n12cN#vGFQWHp;W-7;?XRFwW=<?Lx=)!A+|@gaMv_g}lLp5sZ#^T#2U14*UqOgS'
    'A#Ukb+ug`}cJEClp-95??5~Orf4@b-?0$i0heyAf2Hu$QMI-=MUFejsK2$p-ro0tZg@sRxxNL>mxbOF`%IJZ)M>U;V?ueFO^U#Z6'
    'j2hfqoyf{12@E#-9sF3sVV*-tRRPOyjg5lc_{iFiDxO-z{sLTsX{j`gZ=~_I5OIZu1dfHN{z}8!&v~VI4;5Xh*9-2<Pj@+NU&6FW'
    'CtWJ2WDXwQoT3&EIG4OPimEz<=`Kz=e}m~y+RFMW7IWWyd9fW&KxoQbBoS`0T-?*r=pSa@RyhD#{)p6H$5Z26$+)k#u;o)RZi4!}'
    '@_#u4i`kg>wz)3mZW+bQop-pa><%_k?!6~x#ixl@NC2BpHT?;XZ`?vLt;;8_;vvmx!_xM>wW}ZGjyehVzH>feW#Z>Dy=oq7vNE8v'
    'Isi2eBlx)>kWVDbvnW@NCQn>r1k^F=F3;sZ@4lWD`z>CLrgX*IQ3Zffa!v#^`N+oL3Q%&{+%Rdt+)<l6V{#aR&?wCuvjFWb&Up)k'
    '((~o~C0>6M>ulZ{wa`3dBwC0l+2i$byH!N~fvq(_Ypp<ioGJTVq7e+HaXj*kZcYb@DS*RaQ*>w+Jsxn6(=c*$M&BtXD;$<D@9>0C'
    '&0hH355{;|LR4k01*H_|*0)D)I8L}0;P1+JI64qKrYqiEBG3&Pm!nr-yBN2B5mGU&^l#@K+!Ft=xO7_6t0)V0nAE{nH>V5rVHa%&'
    '`x0Rm+Q1_~3Bnf^U$Bl?zx8+Jdrx^59Q)8Ae6TrqRJGEjdlsgxo&_2SGn<cw+9{9{>&O=*-S||T;K0YX#Nlz7g*+TRK3w#9u1WN%'
    '<|x`2?!QyVi*@mlTQTa`%H#`7^>wkV@)@xDV)wXg&KdU*d|*7%7%N<yK+CV<KBnw}Tsw9X9u5HSjheF<zG%Vw(bxtFw0<DhuT4Z3'
    'QSOG1*V%H)_NaP@l`p$9v!@bk)9U&|niG{gc>g?!tmZKF#x{}P?y>xAE?VDu7P04s$&YoO{_tTpmS`v+&7tD@SGts)=F$FXQ=7nQ'
    'W1sSmK%Yr1zE)hIXIsC`4k<XobtmAm{jnfjhc$$~QeOz>X5S@bPDBQ<?Gydsa=TIm_6f^BaU{lLNN6O5tR+%j8BuD4&QFE4hGKO('
    'lx1iG<x*$y8t5%UMu*xb;8@&UVN>sWOjb-`HnqEl3Qwv%OA_7x3FIu*7-Z6gjoT8v9tysY-e<W8FFvk9`VZ6wiOVTYcZYwC{VTb1'
    '*@qx;j2&2CeAuf=SGg3i$5l~|ujZaE2@zj-;mDR&&b=bxc48jfgR2dl<W~nDSMEuS*>(@b=(Ksa->JU7s)3%63(Ue@xgvy-$D+~r'
    'Nw&oxb1`lc3yP+3^&#-{djMmzKSKv5A@=m_56pARX3X9HS6yw`+McRqVI7tVaN@ya7fXzt0vc!JuMU9{#J`>gy(j<)>eo^WqhZXG'
    'CB1>%ob=%7euoyQx~=4F9iUH1RsQkZCH+0YuEW&?<bpVKD!>nQ1zz~@2VWmVG%eD+#Cj^KwLn96^EH~@5q|7va#IbV6X6zVnchzf'
    'kj8|kjNVA*NK!1B_Y&ZtQ+kzlGqy@{)H~pPuc&G{V&TT7l+tBmouQYm$>x)9kJ4viBOQVn^wC!SJf84x8MtQk8fz+F$wqnz%9pRA'
    'WFG(Cu9$RP)vIJFT$v)MAUDdQ$Vvs=Ni?X6l4KC-tAf~@rqZithmuead&z-U=cgSw)n{}C<5qoa?@J5}hKL1Ja*n&eS3Wz=FF7!X'
    'mxW}=eII2RF0(x?N$ZZ5OP!kHUdF+l6{m8WM9!m$L|MJxFQD-w5YO4A2lP`fu~O#5P`x?xIEB!)7neCFLTVI5$mN3(4-7{kT}@FQ'
    '@vb_z*0hYl=Xq!YRr09U1UbO68$dc5vz+^(3E<=M964LEinkz}`W1<OW$*Ui&~z@O`PKGa%ig5dzlv2=?x(_=SN_oV>B{cn4rm)d'
    '9Zjf1A6<YPpMT(&Y=GHud%BmEfvZGAZ#!wa413oSY8$)u`Lk|Q%@)c)WFpdacAxucsb31<T0hHcv+<$Ct{Cw^rN2Duj1n7fDo{VO'
    'JnDO4OA5|ex*<mk%HMZOhf`>J1R^UIsxxE))Hqg9;rw@VD6|P+9<LQ&6bh>@4RzJ^ewA7)KbUwWTfcQr8m3C7rPz{#>WQ6`8ihUp'
    '*{;D5qvpAV7<c=E$`v}()49rykDz`MInD)Dr8dXz4xgr|*68=<@x6`d$p=PCPCl7OFxLtFcOj}ey6)xWQEgG7Yx7$#<Iq-ob0D8C'
    'x;GntfCPFZ7Dt`>Z?{<e7*931sk<UOG94vg!7%#iR=q=pog{Kq=B{0Q=>?AQ00QP8uuh`U-2NkjqLh%Ka5>jviCqnyXMbtbIK@Jn'
    '88)E!TH^g^x^4xT{)O=soCrJ`wsi>oGKv4v;e#3Xu4i~Lmx|+7IrDtF=T@4<p|(eg9tFdfNH0R!AspmnqUhv=SAcQ<q&{<sdY&rl'
    'F*1%8(3f}(%>IGL0zl~wril}uifAYHh|YNQ>FhwKcRvmWYJ-y8ujSqGS*)~~B36`_<X6NwS0|s!r+N{gH<n?i2kHIYlbKIZ1b4M}'
    'laS@uv-l5V;b&O+$F{b)7Lv8g_k6_d-gM6#Sx(fZ>V=(TLdsBz_<Z>!yoljMQldomdgW9CV9(WF(X}^MTezO`a&P1unGj}Tg8qv9'
    'gBMR_1E&g%hzQw(RggBrVj_5Gr01mZ2^k4QR>F?OUB@-&;p}_qePgA2^Q@s?B)s7Ie$^hpa*B&d_*NoY0DN#5NSxW>!+mw<s%ngR'
    'g`)J`dZf?96KY#gkkbN!_rmwXI6hw51pRewL>vob<Lq<r)>oGNw>V>gkcR@MlVWeT6FPf4-<<6Ws~4hK8rYPw&)Ed?Sqf8q-UT>5'
    '94IL{RSbrWNdPC@LgCtE$d?!1NF|snsOZoCTcxVeTAjp{;tvc+gFaetMI+kB@(wKQutcG>a4mUZ;!EW_m7qq-ygVT1l~P~yGOWNd'
    'GA1M%;Y=l#Sod>VnfeIvnyFgF%}>PB1jOL+yK}|JXpw)(+oLo>Q`<gAQ*UcU6Bv<vbJtO~;W&Mi{HD|J-iBIz-ypvqp6D7+m%-ce'
    'EA;RFMd%X(_zqcLJAcB6<?-wL>MH$-BE9;N#6i)Hv*wK%3;0(?r2m(wsyX`G$C~&N-q+=FEoZs&bU+Jy?fMe)SwanD<({_c{}gs!'
    'K}{&y8V-igK}0~RD1?q6y*KHggf7w|NN<}iC1~iO35bAHLy;Pqw5Sk}-kV617BKWqC{n^b``)>;XPh(Vto6F)d-$KfHGdHX(g-T@'
    '>?h#?Q$4kReJ!>x(>n%jtEq|MdGj1CG?n#0JG?5aF%qzHso_>li4_K>4V1i9e3;v-I&)}hXL)!ih`f~Rd6CbvD%xdht$*?%vEr1D'
    '1#muT;7S~zIe4s6^i2?WVIDHf1gl$Qt1HfZ+X8St9^~Lp@R-Sd|0rizoyM&``iGB~Xg{H(L+MqbDjrAJGH*8`Z(-xE=OZmn%FWE_'
    '_7BTeWxA=JD@Zk9f#epX@zh{&%W57o)qe1KXe&b$PxjEG-J9)omuJXSpq&O<jrwcv**3%A<h}}2#C@)nwkYgoiu+YhTl!H1L}~e~'
    '-PT`in&2sqmQoOK#ciADfQK9K(#j>&1Zq)K*!bQhv*@H;qN;Dsy{aRU>^rxLlhK#loAc8Lg=Z-dG;;4gK37~%C+Z`>dFB%m6-byy'
    '+eIu-i4?)iPh8`*ZKN<e1dftm7?L!biP%Yp68w`oI0&CsSYut?joQY>h?GD%$EHahRo16jAnZ<q@J#BVTOJ2)YwL6hMcPKAxpd5W'
    'lKyIiX?JbwNPv7t5_J9CfuI`H?T}T~h6YADns3->@yGIhvPfg474CZ@Sit@fII$V8?u@)7Uq)$!akAegAha-b_RR$i$l<Sn{BR|S'
    '7rkukh*RnP*$YMq?FUQc63BzW?PiRM#e74GzJy>lHlV}w(orrUjdP+pT~X&w*-UIJ`{olRNk|s7B5wWcBZ-g~;`@|AWIa+X;6A5+'
    'SCK{M@KO`3om8hBOHoI2qk&V&VSF+*vb6k{1_ig=;IT>0<w%IKFKM?Zi_KcT;t^0;M*gTgk7`Mfl;r&jrTMGd;}G7<=Q2-nKy7B}'
    'D*M5kT6u2+NByTp-vw^3WD5rxF)dBEYutdfse%qEk9}B7c6U634GAYS3b9m5yruU&s6#=ssa_6(nY8&Em7<J$poXX?b1^M#7Yoz;'
    '8TlZS&2cW-dGH*vw)%BYYR(~33s_cbCe^nzze>)p#tL?~WHWN`2j(}Od7t2BtFNOHPg2Fty)i%V%ijezS#)rxc`E!DdO&B0r3S7)'
    '%g|~uxM>?YtNJGGjjIWTsOwr#zJg)SEfVokhC$4;6d^sdd!OC*#<ONw4X);|OFU5X?+JA7wMm;d*dr`+Sy>s}?`Yu46%9bNwpalc'
    'UtZ>k61Xf(fb6L@*dZXkEa*HSL@rAwW`f`K%ZOgrJwhbLGhrWU^~uH1&_QCC<Yv}-Pdl`mdY^2Y%FpZz)qYtcJoT&_5eNL*A8);<'
    'e4(_nqtey;7%1PU_nO;GHD}767}%=iY?rL^ITVZzE~O8UlN-Y7I0P54?PUb|?r;DrT3?t3q<d$!Q$J-)VX1U%57CWgT>A<2YodKL'
    '^syW<x*Hx}^ZH5MD`I76HTf@x8A3NDnVrm2U=7v8FBXYa5(xhS4Pku308;v$w~*CLv=he0_httt`BA5WxoyFA>!!d}hK#H>@97>h'
    '$ME1^=(|Yw&S+AN_#h|YxOAD)&@LW$#M@&lO53z@i=M)Gi;9gyo3J@{BFLHXjm~=J4<-#(Ylv5S85Bl*OD{Wl11fMVk3=Hcq?4SA'
    'UczFq?-7IiChvK<4=U-rQ1RxWJ5U#?yFPO-gviUc-CWr|X|=E>Jsan;72Me1?=w{2U@UA7U4Qz_98W#9px<&RD6bKbmqaORv@~$N'
    'O9PXquMP9lyq{WsOyUE(mB=@084Z#HUvI4c+`QkuIDl`$U_DxI*QYqitd72#?PsN3`8Dk-?%kN<5T>anEMc3dXwz!IyT5aX$>`;5'
    'TS?p;#i55^A>X){Gp}H5sW!vNYC>z3PAB#7bb^_mL-R7*{;{J$x7+d!F#}y*^Ttcss~8k&Xw%M{8g?Ty4$(+EUA8?`uN#H%eLykU'
    'a%fDg{o6lp;aKM2^reJBvmUHJkgQhB%f8eMp6hqwD}EC$RE!c_(VzX9A2$jue|>sVcR)caS=?xpX_VlLDX)s|OlwW4e)~96To6}k'
    'iM<tVEkjbN*V{%Pwxn5ZePI0+CoL2oVXM!WlzDJfO7TcaAd=lznG47Evqni#;RWnHft03u_pkU*`0<30Gl*`y5MHnF{S!cY;mH?U'
    '1*nknq<-V!SpZD%@XWr|A!$4ElO*u)<(z%FL<A5cyPSGpS(rqKFP?v&YfNXA7mkP>0c3=W&Ehzfsqki*6xY6Ry3#Nu)1ceCPtyRJ'
    'dk34kteallRaXkRO?lX_9^asu$x`nQ9@M<}xwhwUX5;_3t6rM<M{J+xyR!Rs2crHVjQcQ5zg7iYT_W`JLR#QZhpn>M7}tQ?*26kN'
    '%-GABkIh^+dDwvYWa-GM6Jq3@PA*9N0cnh@K`O;@UlE$EDkkv+sdws#v&titn)G^0zMNnhT8-;!9sagT`p_!wf>}v(h3Go=ti}n8'
    'CfqqX{XIrC*`4xh<JrQG6^U`M>o*8rplE?aI!l9x?1R(zSq}S?&v}RZiH0^dprTE0cxCDAC1I_34<!aEH%c6`WI52F*EMfcI9@=A'
    'b_I)RW@6@+$<<fw`V;9{O{+`hXdgd<4FCR0bnxAjxx(TOqP-TS1aG~hl*_=PkDHw8_P<!{pHJX2v$}c_@7U3c-VIoo8X^2b?GfZ2'
    'fS1LSm5B5*LwI>WgL;VFf*f4lDlZhdT+qOb5s|@Bohat9&Rv;Jb4M9Bbr(w?a&AODRpj0YV*TMz&h43t7AFQ@nM;wUD0KH}R?cij'
    'Eq9u&JqvwC_M1kvgrPTz<n9zQkPJP%K)z4evvu9KxdeVE$zc?Sp&HGs$EF{Dl$7jXNx0Uw3#IoC={UwLroSi8J|FeIeU+@8qv_H#'
    '6gosyt#0l{wKMZNqW_s9I?Fodo)EXRCZmIZF(nK$P(w<>5Q-J+&OFid^fBO(eIhk6N!RY4xE1m|+}Ba^X|SW#{m1^l&xNzecuXW6'
    '(wu>0l+QHxQ3LLD25L=1rOO{aFf3gK7BHx2*6uE%RQa^ws!M^=7hmGyC!*t(#x`+2zvs=`yIO<9<O{A_FTG3Wo5z4NX$tf8@*#8g'
    'owqz#A{RgmW8JX>%NIUmgixYLscC3gpx;9cli)Ntj$6t%mz{OmN7GL|7%tYxaq~Jd{!EabK@ShmkCwNyIVJ_WI5P!j4AKcEdo8TL'
    'mS$`m9$`l;l&JTHnbH2pws2JwQY;Yqd8@2zL+Mp_*GKWKo+pS6W3=#qaO#X_w@>~cm!S&LVQ$lEMAWbBOPvN9#Wysc`4Y6nzwUtf'
    'IymQkI3I<X$&GNvQ&BtFS@m5lOt`m2ejxAp&f#a8Ad`ZxRKHl-mI3!sjtpS({W`B{d?jni`Y()l+dK@vT+z)&t!u##hA6parY#Ll'
    'YlOKB@xSUdAsxmOHW=@Bs*NtVjnCMSfMkyFUr`_ZFNLGkPug8$6YhHe@9{4#ByD^_ISu4%@T;MFpvm$vkB`;r-C0FC)@WUnOV<`k'
    '9^b}Ui9VzW3u$^Mc4}iOC!YM>Y(-HgEBLFd=79N5Y(I6Yp*jGHvP03}|AKcgJ;-W$q*cjaw<Jlp%Q+ia$Lqi4*0LUwdzCgK=1<Ir'
    '-!G?ygqi|Z^AQ=%EUSdXo%NAXr_v1R{BeA48Q*xM<lV^g!PLtT&FkRwy$_5*yV+oApY3pO6(b*(^BU6IUVFM`62+)=FS6v+2eOng'
    '7<F-esm>DPqKRxjT&=P+yr`&n<ouY}w{0rvo`@~rHfdgGCr}`$V7)2FQd7rAIVvNd()BH?ifzE@Rr!HwZ#iZDi5|0}U`ru71-Vr;'
    'vY6=jbN+-v1T;lamh+8#IL$jX$qMmhMfoIwgb#Zx&*LmWUorTmQ!)x{KU9~jM}Mz#Np->u>bRWG?wxHXtc+B{&V9RHeX9Z~=2mH('
    '7!IiKqcNT4yye~57%L10EQ59)BF+joB7ZZ4I}oj%v&~w++B36O<#nTTDHvp-pnpNPZfH|g#oej)*$FoY(s-&ns^3G9xL9s=MAVaj'
    'sw^ziZ$7^pVt7Q7Bf#R_Q(;;#pkLa9ry_q6I|#kL03{djUZm^i@OU75(8P5+F8zNkQt{ll`ypG&0AI!ZS1rosR@Q)@A$riI&Ebk#'
    'F{+57WMo(U<davbsde2bk!i`^%aly@(Eg>iDs72a-nB)(mn(T$v)ti9{cFT3p87W2=gPWT&&5TCzg6RqYTS|F8wR(apcNFaKz=q`'
    ';c}n1k!3nK7;)G$4lJ|3I?aC-mRsPn(34$w*<96MINru`+#zQk>^Gf6*{~kt@_-}bNU!<fehl8u{dLaIbB#7F+CjnoOOq6MYTR-Q'
    'QF6@z#R*Ed7arT^axXFGEQ0ie2T@ytbtkOr30G}?@$+T>(F$+i@AfE>qZjkE;dx&rH)~s9I|(_@YRMulc<%fhR#oc>_*=;*x<L>8'
    'N6IJ2xmiO*0RUam|C93nf8a!bKNWp1TVG$700&<Y9|uoYm;Y7t|D@GzSa{$h0e~gRKWT}g|4H}{{<k!lPn|{HQUHLv)St8(r~gC?'
    '{I|3}%MkyeLG%85HR7MNKc5-?q3taE_typkJrK#?*PwrG^uLmZ)BGLx{{UP<j%@'
 )

def stock_icon_updates(root: Path):
    content=zlib.decompress(base64.b85decode(ECLIPSE_ICON_ARCHIVE_B85))
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        result={}
        if set(z.namelist())!=set(STOCK_ICON_SHA256):
            raise RuntimeError('Embedded violet icon archive manifest mismatch')
        for rel, digest in STOCK_ICON_SHA256.items():
            dest=root/rel
            if not dest.is_file():
                continue  # V2 supplies stock icons; missing assets handled separately, not overwritten.
            old=dest.read_bytes()
            if hashlib.sha256(old).hexdigest()==digest:
                result[rel]=z.read(rel)
        return result

def create(root, dry):
    if not (root/'src/game/fighter.ts').is_file():
        raise RuntimeError('Run from Fight Royale web/ folder with src/game/ present')
    data={}; original={}
    for name in FILES:
        target=root/name
        raw=target.read_bytes()
        original[name]=raw
        data[name]=raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    for name in FILES:
        if MARK in data[name]: raise RuntimeError('Renji Eclipse V3.1 already installed; refusing repeat installation')
        if 'RENJI_COUNTER_FIST_V2' not in data[name]: raise RuntimeError(f'{name}: Renji V2 not found; refusing unsafe update')
    p=Patch(data)
    patch_roster(p)
    patch_kits(p)
    patch_model(p)
    patch_game(p)
    patch_fighter(p)
    patch_presentation(p)
    patch_ai(p)
    # Add a unique marker in fighter for safety and version tracking.
    p.before('src/game/fighter.ts','  renjiRead = 0;', '  // RENJI_ECLIPSE_V31 — perfect-parry attack-cancel retained.\n')
    validate_post(p)
    icon_updates=stock_icon_updates(root)
    print(f'{len(icon_updates)} unmodified V2 stock icons eligible for violet recoloring; custom icons preserved')
    print(f'{MARK}: preflight passed for {len(FILES)} source files')
    print('  Tonfas: short T-grips in BOTH palms; long shafts along forearms')
    print('  Dark: concealed chain, hook, guard-ring, telescoping shaft')
    print('  Z 7 beats, C 2 beats, V 8 beats, all ordinary melee checks')
    print('  X 15s automatic parry and 30s Read decay preserved')
    print('  Renji AI recognizes renamed skills; extending rod updates hit FX tip; V parry recoil cancels remaining contacts')
    if dry:
        print('DRY RUN — no changes written')
        return
    backup=root/'scripts'/'backups'/('renji_eclipse_v31_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True,exist_ok=False)
    temps=[]; changed=[]
    changes={root/n:p.d[n].encode("utf-8") for n in FILES}
    for rel,blob in icon_updates.items():changes[root/rel]=blob
    original_paths={root/n:original[n] for n in FILES}
    for rel in icon_updates:original_paths[root/rel]=(root/rel).read_bytes()
    try:
        (backup/'manifest.json').write_text(json.dumps({'installer':MARK,'files':FILES,'updated_stock_icons':list(icon_updates)},indent=2),encoding='utf-8')
        for name in FILES:
            dst=backup/(name.replace('/','__')+'.txt')
            dst.write_bytes(original[name])
        for rel in icon_updates:
            dst=backup/(rel.replace('/','__'))
            dst.write_bytes(original_paths[root/rel])
        for path,raw_output in changes.items():
            raw=original_paths[path]
            out=(b'\xef\xbb\xbf' if path.suffix=='.ts' and raw.startswith(b'\xef\xbb\xbf') else b'')+raw_output
            fd,filename=tempfile.mkstemp(prefix='.renji_v31_',suffix='.tmp',dir=path.parent)
            with os.fdopen(fd,'wb') as fp:
                fp.write(out); fp.flush(); os.fsync(fp.fileno())
            temps.append((path,Path(filename)))
        for path,tmp in temps:
            os.replace(tmp,path);changed.append(path)
    except BaseException:
        for path in reversed(changed):
            path.write_bytes(original_paths[path])
        raise
    finally:
        for _,tmp in temps: tmp.unlink(missing_ok=True)
    print('Installed Renji Eclipse V3.1. Backups:',backup)
    print('Now run: npx tsc --noEmit -p .')


def main():
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--dry-run',action='store_true')
    args.add_argument('web_dir',nargs='?',default='.')
    a=args.parse_args()
    create(Path(a.web_dir).resolve(),a.dry_run)

if __name__=='__main__':
    try: main()
    except Exception as error:
        print('ERROR:',error,file=sys.stderr);sys.exit(1)
