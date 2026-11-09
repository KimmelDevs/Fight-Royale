#!/usr/bin/env python3
'''Fight Royale — Renji V3.3 Blunt Impact choreography upgrade.

Targets a COMPLETE existing Renji Eclipse V3.2. Does not change the grips,
Aster VRM, damage, Guard, Read, Iron Reflection, or other characters.

    python install_renji_blunt_impact_v33.py --dry-run
    python install_renji_blunt_impact_v33.py
    npx tsc --noEmit -p .

Sources: src/game/kits.ts, model.ts, game.ts.
Sound choice is based on ORIGINAL Sound List filenames found under public/sfx/,
including either category subfolders or flat copies. Missing sounds safely fall
back to the existing MATCH_SOUNDS registry; no new 404s.
The patch does not embed or redistribute any MP3.
'''
from __future__ import annotations
import argparse, os, re, json, tempfile
from pathlib import Path
from datetime import datetime

MARK = "RENJI_BLUNT_IMPACT_V33"
FILES = ("src/game/kits.ts", "src/game/model.ts", "src/game/game.ts")

# These are existing names copied exactly from SOUND_LIST(2).txt, without .mp3.
SOUND_CHOICES = {
 "light": ("fight/body_punch_quick_hit", "hit_blunt"),
 "mid": ("fight/impact_of_a_strong_punch", "hit_blunt2"),
 "heavy": ("fight/metal_hammer_hit", "hit_heavy"),
 "finale": ("fight/impact_big", "hit_big"),
 "mechanism": ("misc/mechanical_tool_click", "click"),
 "pivot": ("fight/boot_stomp_on_mud_surface", "land"),
 "parry": ("fight/hitting_metal_armor", "parry"),
}

class Rewriter:
 def __init__(self,data): self.d=data
 def one(self, file, before, after):
  n=self.d[file].count(before)
  if n!=1: raise RuntimeError(f"{file}: expected 1 anchor, found {n}: {before[:96]!r}")
  self.d[file]=self.d[file].replace(before,after,1)
 def span(self,file,start,end,body):
  t=self.d[file]
  if t.count(start)!=1 or t.count(end)!=1 or t.find(end,t.find(start))<0:
   raise RuntimeError(f"{file}: missing/ambiguous span: {start[:88]}")
  a=t.index(start); b=t.index(end,a)
  self.d[file]=t[:a]+body+t[b:]

POSE_BLOCK = "  // RENJI_BLUNT_IMPACT_V33 — CHOREOGRAPHY: fixed stance, alternating chamber, genuine knee bend.\n  // P's 9 actual arguments include wrist rotations between arm and leg vectors.\n  rnz1_s:K(P([.15,.28,-.02],[-.08,-.18,0],[-1.83,-.15,-.08],[.24,0,.06],[-.66,-.40,.42],[.24,0,-.06],[-.37,-.04,.03],[.43,.03,-.03],-.17),.38,.40),\n  rnz2_s:K(P([.19,-.42,.03],[-.08,.24,0],[-.69,.37,-.47],[.24,0,.06],[-1.93,.11,.05],[.24,0,-.06],[-.44,-.03,.02],[.42,.04,-.03],-.20),.39,.38),\n  rnz3_s:K(P([.23,.57,-.05],[-.12,-.32,0],[-1.60,.69,-.12],[.24,0,.06],[-.55,-.37,.45],[.24,0,-.06],[-.56,-.03,.02],[.48,.01,-.04],-.23),.50,.41),\n  rnz4_s:K(P([.43,-.59,.04],[-.17,.26,0],[-.67,.24,-.48],[.24,0,.06],[-1.56,-.57,.11],[.24,0,-.06],[-.47,-.01,.03],[.49,.03,-.02],-.22),.52,.48),\n  rnz5_s:K(P([.22,.62,-.04],[-.09,-.36,0],[-1.49,.76,-.24],[.24,0,.06],[-.62,-.39,.43],[.24,0,-.06],[-.64,-.01,.02],[.48,.01,-.02],-.24),.55,.43),\n  rnz6_s:K(P([.22,-.63,.05],[-.12,.34,0],[-.64,.35,-.52],[.24,0,.06],[-1.82,-.17,.08],[.24,0,-.06],[-.46,-.03,.02],[.54,.03,-.03],-.20),.44,.49),\n  rnz7_s:K(P([.47,.18,-.06],[-.22,-.14,0],[-.77,.30,-.44],[.24,0,.06],[-1.20,-.33,.31],[.24,0,-.06],[.31,-.02,.02],[-1.52,.02,-.02],-.23),.53,1.76),\n  rnc1_s:K(P([.27,-.78,-.09],[-.09,.39,0],[-.72,.25,-.45],[.24,0,.06],[-1.72,-.45,.18],[.24,0,-.06],[-.61,-.02,.05],[.52,.02,-.03],-.28),.56,.38),\n  rnc2_s:K(P([.47,.69,.06],[-.14,-.34,0],[-1.56,.48,-.24],[.24,0,.06],[-.66,-.25,.45],[.24,0,-.06],[-.37,-.02,.03],[.58,.03,-.03],-.22),.43,.61),\n  rnv1_s:K(P([.19,.36,-.03],[-.10,-.17,0],[-1.88,-.14,-.04],[.24,0,.06],[-.61,-.32,.45],[.24,0,-.06],[-.44,-.02,.03],[.46,.03,-.03],-.18),.39,.42),\n  rnv2_s:K(P([.21,-.46,.04],[-.11,.22,0],[-.60,.32,-.48],[.24,0,.06],[-1.91,.08,.06],[.24,0,-.06],[-.46,-.04,.03],[.46,.03,-.02],-.22),.42,.45),\n  rnv3_s:K(P([.46,.60,-.08],[-.14,-.33,0],[-1.62,.53,-.21],[.24,0,.06],[-.62,-.25,.39],[.24,0,-.06],[-.57,-.03,.02],[.49,.04,-.02],-.26),.56,.44),\n  rnv4_s:K(P([.49,-.24,.05],[-.16,.13,0],[-.62,.28,-.39],[.24,0,.06],[-1.14,-.33,.31],[.24,0,-.06],[-1.51,-.03,.02],[.32,.03,-.02],-.23),1.73,.49),\n  rnv5_s:K(P([.57,-.65,.05],[-.22,.34,0],[-1.92,.31,-.15],[.24,0,.06],[-.75,-.28,.39],[.24,0,-.06],[-.68,-.02,.02],[.52,.03,-.02],-.30),.58,.52),\n  rnv6_s:K(P([.31,.72,-.08],[-.10,-.35,0],[-.67,.27,-.41],[.24,0,.06],[-1.67,-.56,.02],[.24,0,-.06],[-.51,-.02,.03],[.56,.03,-.02],-.23),.49,.53),\n  rnv7_s:K(P([.41,.17,-.03],[-.13,-.14,0],[-1.96,-.03,.04],[.24,0,.06],[-.69,-.24,.41],[.24,0,-.06],[-.66,-.01,.02],[.51,.04,-.02],-.29),.57,.51),\n  rnv8_s:K(P([.65,-.27,.02],[-.23,.14,0],[-1.84,-.03,-.16],[.24,0,.06],[-1.82,.06,.17],[.24,0,-.06],[-.80,-.01,.02],[.61,.02,-.03],-.33),.66,.65),\n  rn_counter_side:K(P([.34,.61,-.06],[-.08,-.27,0],[-1.65,.30,-.12],[.24,0,.06],[-.62,-.37,.45],[.24,0,-.06],[-.54,-.02,.02],[.49,.04,-.02],-.24),.51,.47),\n  rn_counter_over:K(P([.53,-.28,.03],[-.13,.12,0],[-1.68,.16,-.28],[.24,0,.06],[-.75,-.32,.42],[.24,0,-.06],[-.70,-.02,.02],[.49,.04,-.02],-.28),.62,.53),\n  rn_counter_low:K(P([.32,.25,-.07],[-.20,-.15,0],[-.74,.30,-.45],[.24,0,.06],[-1.25,-.25,.33],[.24,0,-.06],[.27,-.02,.02],[-1.39,.02,-.01],-.23),.39,1.67),\n  rn_counter_thrust:K(P([.33,-.61,.04],[-.12,.30,0],[-.57,.32,-.40],[.24,0,.06],[-1.86,-.04,.06],[.24,0,-.06],[-.53,-.03,.02],[.50,.03,-.02],-.25),.49,.53),\n  rn_counter_projectile:K(P([.28,.44,-.03],[-.12,-.22,0],[-1.85,.06,-.10],[.24,0,.06],[-.63,-.26,.41],[.24,0,-.06],[-.49,-.02,.03],[.45,.03,-.02],-.21),.44,.45),\n  rn_counter_side_2:K(P([.36,-.52,.04],[-.12,.30,0],[-.57,.22,-.45],[.24,0,.06],[-1.62,-.32,.11],[.24,0,-.06],[-.45,-.02,.02],[.54,.03,-.03],-.22),.45,.52),\n  rn_counter_side_3:K(P([.51,.58,-.07],[-.16,-.22,0],[-1.49,.54,-.23],[.24,0,.06],[-.60,-.32,.35],[.24,0,-.06],[-.63,-.03,.02],[.50,.03,-.03],-.27),.57,.49),\n  rn_counter_over_2:K(P([.42,.39,-.04],[-.13,-.25,0],[-1.89,-.12,.03],[.24,0,.06],[-.58,-.22,.34],[.24,0,-.06],[-.46,-.03,.02],[.47,.03,-.02],-.25),.47,.48),\n  rn_counter_over_3:K(P([.46,-.49,.03],[-.14,.22,0],[-.56,.23,-.39],[.24,0,.06],[-1.85,-.23,.08],[.24,0,-.06],[-.58,-.02,.02],[.51,.03,-.02],-.27),.52,.48),\n  rn_counter_low_2:K(P([.24,-.42,.04],[-.15,.20,0],[-.53,.23,-.44],[.24,0,.06],[-1.89,.09,.03],[.24,0,-.06],[-.47,-.02,.03],[.47,.03,-.02],-.19),.44,.47),\n  rn_counter_low_3:K(P([.47,.40,-.06],[-.16,-.17,0],[-1.51,.51,-.19],[.24,0,.06],[-.63,-.24,.41],[.24,0,-.06],[-.58,-.02,.02],[.47,.03,-.02],-.25),.55,.46),\n  rn_counter_thrust_2:K(P([.43,.55,-.06],[-.13,-.28,0],[-1.69,.45,-.17],[.24,0,.06],[-.55,-.30,.44],[.24,0,-.06],[-.60,-.02,.02],[.49,.03,-.02],-.26),.57,.43),\n  rn_counter_thrust_3:K(P([.47,-.44,.03],[-.14,.22,0],[-.65,.27,-.43],[.24,0,.06],[-1.87,-.18,.09],[.24,0,-.06],[-.51,-.02,.03],[.53,.03,-.02],-.22),.46,.54),\n  rn_counter_projectile_2:K(P([.35,-.50,.04],[-.12,.27,0],[-.58,.32,-.40],[.24,0,.06],[-1.75,.08,.02],[.24,0,-.06],[-.50,-.02,.02],[.49,.03,-.02],-.24),.45,.49),\n  rn_counter_projectile_3:K(P([.55,.57,-.07],[-.16,-.30,0],[-1.69,.48,-.16],[.24,0,.06],[-.61,-.30,.42],[.24,0,-.06],[-.63,-.02,.03],[.52,.03,-.02],-.29),.60,.53),\n  rn_insight_w:K(P([.46,-.58,.03],[-.10,.33,0],[-.65,.33,-.50],[.24,0,.06],[-.76,-.36,.44],[.24,0,-.06],[-.65,-.02,.03],[.49,.03,-.02],-.29),.58,.52),\n  rn_insight_s:K(P([.65,.38,-.05],[-.22,-.18,0],[-1.89,.16,-.08],[.24,0,.06],[-1.82,-.12,.09],[.24,0,-.06],[-.76,-.02,.02],[.61,.03,-.02],-.33),.67,.61),\n"

# Five primary tuning controls — edit these values in the generated game.ts:
# Z_LEAD, V_LEAD, HITSTOP_FRAMES, SHAKE, SOUND_GAIN.
FEEL = r'''// RENJI_BLUNT_IMPACT_V33 — five independent, tweakable feel controls.
const RENJI_BLUNT_FEEL_V33 = {
  Z_LEAD: 0.040,
  V_LEAD: 0.085,
  HITSTOP_FRAMES: [1.5, 3, 5, 8], // light, elbow/knee, finisher, V/Read finale at 60fps
  SHAKE: [0.06, 0.11, 0.19, 0.32],
  SOUND_GAIN: 0.54,
} as const;
'''

MULTI = r'''  // RENJI_BLUNT_IMPACT_V33 — radial impacts, distinct limbs, real melee collision.
  // Source sound names are embedded by the installer; no slash or blade sound plays.
  private renjiBluntTier(a: Attack): number {
    if (a.id === "renji_insight" || (a.style === "renji_pulse" && a.heavy)) return 3;
    const idx = Number(/_rn(\d+)$/.exec(a.id)?.[1] ?? -1);
    if ((a.id.startsWith("z") && idx === 6) || (a.id.startsWith("c") && idx === 1) ||
        (a.style === "renji_riposte_hit" && idx === 2)) return 2;
    if (idx === 2 || idx === 3 || idx === 4 || idx === 5) return 1;
    if (a.id === "heavy" || a.id === "l5") return 2;
    if (a.id === "l3" || a.id === "l4") return 1;
    return 0;
  }

  private renjiBluntFX(f: Fighter, tier: number) {
    // Called ONLY after melee() confirmed actual HP damage. 20ms after pose blend.
    const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
    const color = tier >= 2 ? "#E8D7FF" : tier === 1 ? "#8E51D6" : "#58318E";
    const count = [6, 12, 22, 36][tier];
    const reach = [1.4, 2.4, 4.1, 5.7][tier];
    this.fxp("sparks", p, color, count, reach);
    this.fxp("flash", p, tier > 1 ? "#E8D7FF" : "#8E51D6",
      [0.09, 0.15, 0.22, 0.29][tier], [0.065, 0.080, 0.105, 0.145][tier], 0.58);
    if (tier >= 1) this.fxp("ring", p, color,
      [0.0, 0.27, 0.56, 0.94][tier], [0.0, 0.13, 0.18, 0.25][tier], 0.52);
    if (tier >= 2) this.fxp("smoke", p, "#27173D");
  }

  private renjiMulti(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    const riposte = a.style === "renji_riposte", z = a.style === "renji_hundred";
    const c = a.style === "renji_blindside", v = a.style === "renji_eightfold";
    // Unequal spacing: V pauses after knee #4 before accelerating to the finale.
    const beats = riposte ? [.17,.48,.85] : z ? [.075,.18,.29,.425,.565,.73,.925] :
      c ? [.32,.81] : v ? [.08,.18,.28,.40,.59,.70,.82,.96] : [.45];
    const routes = [
      ["rn_counter_side", "rn_counter_side_2", "rn_counter_side_3"],
      ["rn_counter_over", "rn_counter_over_2", "rn_counter_over_3"],
      ["rn_counter_low", "rn_counter_low_2", "rn_counter_low_3"],
      ["rn_counter_thrust", "rn_counter_thrust_2", "rn_counter_thrust_3"],
      ["rn_counter_projectile", "rn_counter_projectile_2", "rn_counter_projectile_3"],
    ];
    const poses = riposte ? routes[Math.max(0,Math.min(4,f.renjiCounterRoute))] :
      z ? ["rnz1_s", "rnz2_s", "rnz3_s", "rnz4_s", "rnz5_s", "rnz6_s", "rnz7_s"] :
      c ? ["rnc1_s", "rnc2_s"] :
      ["rnv1_s", "rnv2_s", "rnv3_s", "rnv4_s", "rnv5_s", "rnv6_s", "rnv7_s", "rnv8_s"];
    if (c) {
      this.fxp("dodgeGhost", f.root.position.clone(), "#58318E", f.root.rotation.y);
      this.snd(RENJI_BLUNT_AUDIO_V33.pivot, 0.28);
    }
    for (let i=0; i<beats.length; i++) {
      const lead = z ? RENJI_BLUNT_FEEL_V33.Z_LEAD : v ? RENJI_BLUNT_FEEL_V33.V_LEAD : .060;
      this.laterCombo(f, Math.max(.012,a.active*beats[i]-lead),()=>{
        if(round!==this.round||f.isDown()||f.state!==S.ATTACK||f.parryRecoilT>0||f.swingSerial!==serial) return;
        f.poseOverride=poses[i];
        if ((z&&i===4)||(c&&i===0)||(v&&(i===4||i===5)))
          this.snd(RENJI_BLUNT_AUDIO_V33.mechanism, 0.32);
      });
      this.laterCombo(f,a.active*beats[i],()=>{
        if(round!==this.round||f.isDown()||f.state!==S.ATTACK||f.parryRecoilT>0||f.swingSerial!==serial) return;
        f.poseOverride=poses[i];
        const last = i===beats.length-1;
        // All damage/guard/reach values are kept as in V3.2. Knock/stun are tuned
        // only for light-vs-middle contact readability; final knock is preserved.
        const tier = last ? v ? 3 : 2 : (i===2||i===3||i===4||i===5)?1:0;
        const pulse:Attack={...a,id:`${a.id}_rn${i}`,style:riposte?"renji_riposte_hit":"renji_pulse",
          dmg:riposte?[36,37,41][i]:z&&last?36:a.dmg,
          guard:riposte?[10,12,13][i]:a.guard,
          reach:Math.min(a.reach,c?2.03:v?2.08:1.98),
          knock:last?(riposte?2.8:v?4.2:z?2.5:1.8):tier===1?.42:.24,
          stun:last?.27:tier===1?.12:.10,heavy:last&&v,no_parry:riposte};
        const hit=this.melee(f,pulse);
        if(hit && last) f.model.recoil=Math.max(f.model.recoil,v?.19:.11); // visual-only impact nudge
        if(hit) this.laterCombo(f,.020,()=>{
          if(round!==this.round||f.isDown()||f.swingSerial!==serial||
             f.state!==S.ATTACK||f.parryRecoilT>0||f.poseOverride!==poses[i]) return;
          this.renjiBluntFX(f,tier);
        });
        if(riposte&&last&&hit&&f.renjiSpendRead()) {
          // Bonus has a visible anticipation, not an instant effect/phantom hit.
          this.laterCombo(f,.008,()=>{
            if(round===this.round&&!f.isDown()&&f.swingSerial===serial&&f.state===S.ATTACK)
              f.poseOverride="rn_insight_w";
          });
          this.laterCombo(f,.055,()=>{
            if(round!==this.round||f.isDown()||f.swingSerial!==serial||
               f.state!==S.ATTACK||f.parryRecoilT>0)return;
            f.poseOverride="rn_insight_s";
            const bonus=this.melee(f,{...a,id:"renji_insight",style:"renji_pulse",dmg:65,guard:24,
              reach:1.95,knock:4.1,stun:.35,no_parry:true});
            if(bonus){
              f.model.recoil=Math.max(f.model.recoil,.20);
              this.laterCombo(f,.020,()=>{
                if(round!==this.round||f.isDown()||f.swingSerial!==serial||
                   f.state!==S.ATTACK||f.parryRecoilT>0||f.poseOverride!=="rn_insight_s")return;
                this.renjiBluntFX(f,3);
              });
            }
          });
        }
      });
    }
  }

'''


def audio_mapping(root:Path):
 out={}; present=[]; absent=[]
 for key,(original,fallback) in SOUND_CHOICES.items():
  # Keep category path when copied that way; otherwise honor a flat copy.
  candidates=(original,original.rsplit('/',1)[-1])
  found=next((c for c in candidates if (root/'public'/'sfx'/(c+'.mp3')).is_file()),None)
  out[key]=found or fallback
  (present if found else absent).append((key,found or original))
 return out,present,absent

def generate(root,old, chosen):
 p=Rewriter(dict(old)); kits='src/game/kits.ts'; model='src/game/model.ts'; game='src/game/game.ts'
 # Rename in-place; AI's existing startsWith prefixes remain valid.
 p.one(kits,'name:"Hundred Fangs: Black Thread",desc:"Six close-range tonfa and elbow strikes, chain reveal on the fifth beat, then a rising knee (seven real contacts)."',
   'name:"Hundred Fangs: Hollow Impact",desc:"Six staggered blunt tonfa and elbow contacts, then a grounded rising knee. The short chain deploys as a trapping weight."')
 p.one(kits,'name:"Blindside Step: Night Talon",desc:"A visible grounded sidestep, hooked left-tonfa trap and right elbow strike. Both contacts must be in true melee reach."',
   'name:"Blindside Step: Breaker Pivot",desc:"Grounded boxing pivot, left tonfa bar trap, then a compact right elbow; both hits must connect through melee range."')
 p.one(kits,'name: "Final Verdict: Eightfold", desc: "Eight real close-range contacts with a mechanical black-iron staff extension, rotating guard-ring and retracting hooked tip; no teleport or phantom hit."',
   'name: "Final Verdict: Eightfold", desc: "Eight differently timed blunt contacts, hidden guard ring and capped extending tonfa; every impact uses real melee collision."')
 p.span(kits,
  '  // RENJI_ECLIPSE_V32 — staggered weapon beats; hands stay on short perpendicular grips.\n',
  '  rnv_s:K(P(',POSE_BLOCK)
 # No grip-orientation changes. Only replace pointed parts with blunt, rounded ends.
 p.one(model,'mesh(hook,cyl(.002,.030,.15,9),this.tn("#8D83A8"),[sign*.07,.075,0],[0,0,-sign*.63]);',
       'mesh(hook,cyl(.024,.024,.15,10),this.tn("#8D83A8"),[sign*.07,.075,0],[0,0,-sign*.63]);')
 p.one(model,'mesh(hook,cyl(.001,.024,.095,9),this.tn("#C4B3ED"),[sign*.126,.154,0],[0,0,-sign*.92]);',
       'mesh(hook,cyl(.025,.025,.095,10),this.tn("#C4B3ED"),[sign*.126,.154,0],[0,0,-sign*.92]);')
 p.one(model,'mesh(extend,cyl(0,.031,.08,9),this.tn("#E8D7FF"),[0,.378,0]);',
       'mesh(extend,new THREE.SphereGeometry(.030,12,9),this.tn("#E8D7FF"),[0,.378,0]);')
 p.one(model,'mesh(ring,cyl(0,.024,.07,7),this.tn("#A090B2"),',
       'mesh(ring,cyl(.018,.018,.07,9),this.tn("#A090B2"),')
 p.one(model,'// RENJI_ECLIPSE_V32 — all concealed parts remain attached to their proper tonfas.',
       '// RENJI_BLUNT_IMPACT_V33 — hidden blunt bars, capped staff, unchanged tonfa grip orientation.')

 audio_ts='const RENJI_BLUNT_AUDIO_V33 = {\n'+''.join(f'  {k}: {json.dumps(v)},\n' for k,v in chosen.items())+'} as const;\n'
 p.one(game,'export class Game implements MobHost {',FEEL+'\n'+audio_ts+'\nexport class Game implements MobHost {')
 p.span(game,'  // RENJI_ECLIPSE_V32 — unequal contact beats, mechanical forms, real hit tests.\n',
        '  private melee(f: Fighter, a: Attack): boolean {', MULTI)
 # Existing hitSound treats tonfas as sword blades. Intercept Renji before generic routing.
 p.one(game,'    const heavy = a.heavy;\n    let name = "hit_blunt";',
       '''    if (attacker instanceof Fighter && attacker.kit === "tonfa") {
      const t = this.renjiBluntTier(a);
      const name = t === 3 ? RENJI_BLUNT_AUDIO_V33.finale : t === 2 ? RENJI_BLUNT_AUDIO_V33.heavy :
        t === 1 ? RENJI_BLUNT_AUDIO_V33.mid : RENJI_BLUNT_AUDIO_V33.light;
      this.snd(name, RENJI_BLUNT_FEEL_V33.SOUND_GAIN * (t === 3 ? 1.35 : t === 2 ? 1.1 : 1));
      if (crit) this.snd("crit", 0.28);
      return;
    }
    const heavy = a.heavy;
    let name = "hit_blunt";''')
 # Scope impact freeze/trauma exclusively to actual damaging Renji hits.
 p.one(game,'this.add_trauma((a.heavy ? 0.5 : heavy ? 0.3 : 0.18) * big);\n        this.hitStop(a.heavy ? 0.11 : heavy ? 0.07 : 0.045);',
       '''const renjiTier = attacker instanceof Fighter && attacker.kit === "tonfa" ?
          this.renjiBluntTier(a) : -1;
        this.add_trauma((renjiTier >= 0 ? RENJI_BLUNT_FEEL_V33.SHAKE[renjiTier] :
          a.heavy ? 0.5 : heavy ? 0.3 : 0.18) * big);
        this.hitStop(renjiTier >= 0 ? RENJI_BLUNT_FEEL_V33.HITSTOP_FRAMES[renjiTier] / 60 :
          a.heavy ? 0.11 : heavy ? 0.07 : 0.045);''')
 # Avoid duplicate generic sword swishes during Renji's startAttack.
 p.one(game,'      if (f.kit === "knuckles" || f.kit === "kicks") this.snd(heavy ? "swing_heavy" : "whoosh_light", 0.7);',
       '      if (f.kit === "tonfa") this.snd("whoosh_light", 0.28);\n      else if (f.kit === "knuckles" || f.kit === "kicks") this.snd(heavy ? "swing_heavy" : "whoosh_light", 0.7);')
 # Replace the parry sound only when defending Renji, keep standard parry for others.
 p.one(game,'        this.snd("parry", 0.9);\n        if (!ranged && a.type === "melee")',
       '        this.snd(df.kit === "tonfa" ? RENJI_BLUNT_AUDIO_V33.parry : "parry", 0.9);\n        if (!ranged && a.type === "melee")')
 # Preload only audio paths physically found by installer, plus fallback registry handled normally.
 # The first close-range impact must not go silent during decode, even on fallback.
 p.one(game,'    Sound.preload(MATCH_SOUNDS);',
       '    Sound.preload(MATCH_SOUNDS);\n    Sound.preload('+json.dumps(sorted(set(chosen.values())))+'); // RENJI_BLUNT_IMPACT_V33')
 return p.d

def validate_pre(root, src):
 if any(MARK in s for s in src.values()):
  raise RuntimeError('Renji V3.3 already installed; refusing a double patch')
 if not all('RENJI_ECLIPSE_V32' in s for s in src.values()):
  raise RuntimeError('Requires complete Renji Eclipse V3.2; earlier or mixed versions refused')
 g=src['src/game/game.ts']; k=src['src/game/kits.ts']; m=src['src/game/model.ts']
 required={
  'game.ts':('  private renjiMulti(f: Fighter, a: Attack) {','  private melee(f: Fighter, a: Attack): boolean {',
    'case "sparks":','case "flash":','case "ring":','case "smoke":','case "dodgeGhost":','case "num":',
    'hitStop(dur: number, scale = 0.03)','add_trauma(x: number)','const hit=this.melee(f,pulse);',
    'this.fxp("slashes",point','this.fxp("slashes",pt',
    'private hitSound(attacker: Entity | null, a: Attack, crit: boolean)'),
  'kits.ts':('const RENJI_TONFA:','const K = (p: Pose','  rnz1_s:K(P(', '  rnv8_s:K(P(', '  rn_insight_s:K(P('),
  'model.ts':('private buildRenjiTonfas()','private updateRenjiTonfas(dt: number, pose: string)',
    'const hook=pivot(', 'const extend=pivot(', 'this.renjiMechanisms.push({chain,hook,ring,extend,tip})')}
 for label, strs in required.items():
  content={'game.ts':g,'kits.ts':k,'model.ts':m}[label]
  for s in strs:
   if s not in content: raise RuntimeError(f'{label}: dependency missing: {s}')
 if not (root/'src/game/fx.ts').is_file() or not (root/'src/game/sound.ts').is_file():
  raise RuntimeError('Missing fx.ts or sound.ts')
 fx=(root/'src/game/fx.ts').read_text(encoding='utf-8-sig')
 for sig in ('sparks(', 'flash(', 'ring(', 'smoke(', 'dodgeGhost('):
  if sig not in fx:raise RuntimeError(f'fx.ts: missing {sig}')
 snd=(root/'src/game/sound.ts').read_text(encoding='utf-8-sig')
 if 'fetch(`/sfx/${name}.mp3`)' not in snd or 'MATCH_SOUNDS' not in snd:
  raise RuntimeError('sound.ts: unexpected sound path resolver')

def validate_post(src):
 g=src['src/game/game.ts'];k=src['src/game/kits.ts'];m=src['src/game/model.ts']
 if MARK not in g or MARK not in m or MARK not in k:raise RuntimeError('Post validation lost version marker')
 section=g[g.index('private renjiMulti('):g.index('private melee(f: Fighter, a: Attack): boolean')]
 if 'fxp("slashes"' in section or 'hit_blade' in section:raise RuntimeError('Renji move still uses blade VFX')
 if len(re.findall(r'rnz\d_s:K\(P\(',k))!=7:raise RuntimeError('Missing Z pose keyframe')
 if len(re.findall(r'rnv\d_s:K\(P\(',k))!=8:raise RuntimeError('Missing V pose keyframe')
 if 'RENJI_BLUNT_AUDIO_V33' not in g or 'renjiBluntTier' not in g:
  raise RuntimeError('Missing blunt sound or hit tier')

def run(root:Path, dry_run:bool):
 if not (root/'src/game/game.ts').is_file():raise RuntimeError('Run from fight-royale/web or pass web path')
 old={}; original={}; end={};bom={}
 for f in FILES:
  raw=(root/f).read_bytes();original[f]=raw
  bom[f]=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
  end[f]='\r\n' if b'\r\n' in raw else '\n'
  old[f]=raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
 validate_pre(root,old)
 chosen,present,missing=audio_mapping(root)
 new=generate(root,old,chosen)
 validate_post(new)
 print(f'{MARK}: preflight passed for {len(FILES)} files; existing V3.2 upgrade')
 for key,path in present:print(f'  Sound OK: {key} -> {path}.mp3')
 for key,path in missing:print(f'  Sound not found: {path}.mp3 (safe existing SFX fallback)')
 if dry_run:
  print('DRY RUN — no files modified');return
 back=root/'scripts'/'backups'/('renji_blunt_v33_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
 back.mkdir(parents=True,exist_ok=False)
 temps=[];changed=[]
 try:
  (back/'manifest.json').write_text(json.dumps({'version':MARK,'files':FILES,
     'sounds':chosen},indent=2),encoding='utf-8')
  for rel,raw in original.items():
   (back/(rel.replace('/','__')+'.txt')).write_bytes(raw)
  for f in FILES:
   path=root/f
   blob=bom[f]+new[f].replace('\n',end[f]).encode('utf-8')
   fd,tmp=tempfile.mkstemp(prefix='.renji_blunt_',suffix='.tmp',dir=path.parent)
   with os.fdopen(fd,'wb') as x:x.write(blob);x.flush();os.fsync(x.fileno())
   temps.append((path,Path(tmp)))
  for path,tmp in temps:os.replace(tmp,path);changed.append(path)
 except BaseException:
  for path in reversed(changed):
   rel=path.relative_to(root).as_posix();path.write_bytes(original[rel])
  raise
 finally:
  for _,tmp in temps:tmp.unlink(missing_ok=True)
 print('Renji V3.3 installed. Backup:',back)
 print('Next: npx tsc --noEmit -p . && npm run dev')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--dry-run',action='store_true')
 parser.add_argument('web_dir',nargs='?',default='.')
 args=parser.parse_args()
 try:run(Path(args.web_dir).resolve(),args.dry_run)
 except Exception as e:
  print('ERROR:',e);raise SystemExit(1)
if __name__=='__main__':main()
