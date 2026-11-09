#!/usr/bin/env python3
"""Fight Royale — RENJI ECLIPSE V3 (upgrade existing Counter Fist V2).

Run from fight-royale/web:
  python install_renji_eclipse_v3.py --dry-run
  python install_renji_eclipse_v3.py
  npx tsc --noEmit -p .

Only changes Renji-related sections of roster/kits/model/game/fighter/presentation.
- Corrected perpendicular-tonfa grips through both VRM palms, shaft aligned to forearm.
- Dark-element mechanical concealed forms: short chain, hook, guard ring, telescoping rod.
- Distinct 7 / 2 / 8-beat collision-checked Z/C/V choreography, directional counters.
- Violet ink-like VFX, readable parry catch/cross/redirect; keeps existing X/Read logic.
- Backups use .txt so TypeScript cannot mistake them for source files.
- In-memory preflight, --dry-run, staged writes, rollback and double-install guard.

This tool does NOT modify Aster's VRM, other fighter kits, or sound files.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import json
import os
import re
import shutil
import sys
import tempfile

MARK = 'RENJI_ECLIPSE_V3'
FILES = [
    'src/game/roster.ts', 'src/game/kits.ts', 'src/game/model.ts',
    'src/game/game.ts', 'src/game/fighter.ts', 'src/game/presentation.ts',
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
          '// RENJI_ECLIPSE_V3 — yellow hair, Aster VRM placeholder, original dark tonfa transformations.')


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
    pose_add = '''  // RENJI_ECLIPSE_V3 — staggered weapon beats; hands stay on short perpendicular grips.
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
    p.after(f,'  private renjiTonfas: THREE.Group[] = [];\n', '''  // RENJI_ECLIPSE_V3 — all concealed parts remain attached to their proper tonfas.
  // Visual state derives from the already-replicated pose; no new net fields.
  private renjiMechanisms: { chain: THREE.Group; hook: THREE.Group;
    ring: THREE.Group; extend: THREE.Group; tip: THREE.Group }[] = [];
''')
    new_build='''  private buildRenjiTonfas() {
    // RENJI_ECLIPSE_V3. The SHORT perpendicular T-handle passes through the fist;
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
      const grip=mesh(root,cyl(.030,.030,.235,12),this.tn("#24222D"),[0,-.015,-.008],[Math.PI/2,0,0]);
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
    new_multi='''  // RENJI_ECLIPSE_V3 — unequal contact beats, mechanical forms, real hit tests.
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
    body='''  // RENJI_ECLIPSE_V3 — visible short-grip guard and concealed-form reveal poses.
  renji: {
    ready:{torso:[.18,-.20,.03],head:[-.13,.14,0],arm_r:[-1.42,.26,-.39],arm_l:[-1.45,-.25,.41],leg_l:[-.39,-.13,.18],leg_r:[.33,.10,-.18],hips_y:-.18,knee:[.42,.39]},
    wind:{torso:[.27,-.48,.07],head:[-.08,.26,0],arm_r:[-1.75,.45,-.38],arm_l:[-1.68,-.36,.42],leg_l:[-.53,-.07,.17],leg_r:[.48,.11,-.21],hips_y:-.25,knee:[.52,.47]},
    move:{torso:[.22,.38,-.06],head:[-.15,-.17,0],arm_r:[-2.12,-.12,-.34],arm_l:[-1.80,.34,.43],leg_l:[-.64,-.07,.18],leg_r:[.56,.11,-.18],hips_y:-.20,knee:[.43,.39]},
    hero:{torso:[.22,-.11,0],head:[-.14,.09,0],arm_r:[-1.72,.30,-.44],arm_l:[-1.70,-.29,.43],leg_l:[-.34,-.14,.20],leg_r:[.32,.11,-.20],hips_y:-.18,knee:[.47,.45]},
    win:{torso:[.08,.11,.03],head:[-.17,.06,0],arm_r:[-2.02,.18,-.40],arm_l:[-2.03,-.18,.44],leg_l:[-.34,-.10,.18],leg_r:[.32,.14,-.20],hips_y:-.18,knee:[.38,.39]},tempo:1.24 },
'''
    p.span(f,a,b,body)


def validate_post(p):
    for file,text in p.d.items():
        if file.endswith('model.ts'):
            assert 'this.vrmRig.grip.left = true' in text
            assert 'this.updateRenjiTonfas(dt, actionPose)' in text
        if file.endswith('kits.ts'):
            assert text.index('const K = (p: Pose') < text.index('const RENJI_TONFA:')
        if file.endswith('roster.ts'):
            assert 'kit: "tonfa", element: "dark"' in text
        if MARK not in text: raise RuntimeError(f'{file}: missing V3 marker after preflight')


def create(root, dry):
    if not (root/'src/game/fighter.ts').is_file():
        raise RuntimeError('Run from Fight Royale web/ folder with src/game/ present')
    data={}; original={}
    for name in FILES:
        target=root/name
        raw=target.read_bytes()
        original[name]=raw
        data[name]=raw.decode('utf-8-sig')
    for name in FILES:
        if MARK in data[name]: raise RuntimeError('Renji Eclipse V3 already installed; refusing repeat installation')
        if 'RENJI_COUNTER_FIST_V2' not in data[name]: raise RuntimeError(f'{name}: Renji V2 not found; refusing unsafe update')
    p=Patch(data)
    patch_roster(p)
    patch_kits(p)
    patch_model(p)
    patch_game(p)
    patch_fighter(p)
    patch_presentation(p)
    # Add a unique marker in fighter for safety and version tracking.
    p.before('src/game/fighter.ts','  renjiRead = 0;', '  // RENJI_ECLIPSE_V3 — perfect-parry attack-cancel retained.\n')
    validate_post(p)
    print(f'{MARK}: preflight passed for {len(FILES)} source files')
    print('  Tonfas: short T-grips in BOTH palms; long shafts along forearms')
    print('  Dark: concealed chain, hook, guard-ring, telescoping shaft')
    print('  Z 7 beats, C 2 beats, V 8 beats, all ordinary melee checks')
    print('  X 15s automatic parry and 30s Read decay preserved')
    if dry:
        print('DRY RUN — no changes written')
        return
    backup=root/'scripts'/'backups'/('renji_eclipse_v3_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True,exist_ok=False)
    temps=[]; changed=[]
    try:
        (backup/'manifest.json').write_text(json.dumps({'installer':MARK,'files':FILES},indent=2),encoding='utf-8')
        for name in FILES:
            dst=backup/(name.replace('/','__')+'.txt')
            dst.write_bytes(original[name])
        for name in FILES:
            path=root/name
            raw=original[name]
            out=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+p.d[name].encode('utf-8')
            fd,filename=tempfile.mkstemp(prefix='.renji_v3_',suffix='.tmp',dir=path.parent)
            with os.fdopen(fd,'wb') as fp:
                fp.write(out); fp.flush(); os.fsync(fp.fileno())
            temps.append((path,Path(filename)))
        for path,tmp in temps:
            os.replace(tmp,path);changed.append(path)
    except BaseException:
        for path in reversed(changed):
            orig=next(original[n] for n in FILES if root/n==path)
            path.write_bytes(orig)
        raise
    finally:
        for _,tmp in temps: tmp.unlink(missing_ok=True)
    print('Installed Renji Eclipse V3. Backups:',backup)
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
