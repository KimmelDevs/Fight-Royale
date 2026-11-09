#!/usr/bin/env python3
"""Fight Royale — RENJI: THE COUNTER FIST V2.

Usage from fight-royale/web:
  python install_renji_counter_fist.py --dry-run
  python install_renji_counter_fist.py

Adds a yellow-haired tonfa specialist, using Aster's VRM until renji.vrm exists.
Instant attack-cancel to animated auto-parry, fail-closed anchors; text backups (so tsc never compiles backups),
staged atomic writes with rollback, repeat-install protection.
No third-party Python packages. Will not touch other characters or sound files.
"""
from __future__ import annotations
import argparse
import base64
import io
import zipfile
import zlib
import datetime
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile

MARK = "RENJI_COUNTER_FIST_V2"
FILES = ["src/game/roster.ts", "src/game/kits.ts", "src/game/fighter.ts",
         "src/game/game.ts", "src/game/model.ts", "src/game/ai.ts",
         "src/game/presentation.ts"]

class Patcher:
    def __init__(self, src): self.data = src
    def once(self, file, old, new):
        n = self.data[file].count(old)
        if n != 1:
            raise RuntimeError(f"{file}: expected one anchor, found {n}: {old[:100]!r}")
        self.data[file] = self.data[file].replace(old, new, 1)
    def before(self, file, anchor, code): self.once(file, anchor, code + anchor)
    def after(self, file, anchor, code): self.once(file, anchor, anchor + code)


def add_roster(p):
    f="src/game/roster.ts"
    p.before(f,'  { id: "aster", title: "Azure Knight"', '''  // RENJI_COUNTER_FIST_V2 — temporary Aster male VRM, unique yellow-haired tonfa kit.
  { id: "renji", title: "The Counter Fist", role: "Martial Artist - Twin Tonfas",
    desc: "Perfectly reads attacks and unleashes directional tonfa counters. Iron Reflection automatically perfect-parries every incoming hit for 15 seconds.",
    stats: { power: 4, speed: 5, range: 1, defense: 3 },
    look: { name: "Renji", body: "m", vrm: "aster", kit: "tonfa", element: "physical", outfit: "martial", style: "short", hat: "none",
      hair: "#FFD438", hair_shade: "#BB850E", iris_top: "#EDAE2F", iris_bottom: "#FFE27F", eye_dark: "#51350A",
      tunic: "#19252E", band: "#F6BF40", pants: "#17212C", boots: "#1B242D", metal: "#9BA6B1", trim: "#EFC755",
      cape: "#213D40", cape_bottom: "#315A60", glow: "#F9D76D", shield: "#1B3236", emblem: "#FFD75F" } },
''')


def add_kits(p):
    f="src/game/kits.ts"
    p.before(f,'  knuckles: { hp:', '  // RENJI_COUNTER_FIST_V2: fast close-range counter specialist.\n  tonfa: { hp: 2100, guard: 78, move: 4.30, walk: 3.45, parry: 0.21, jump: 8.1 },\n')
    p.before(f,'    knuckles: [heavy.pose_w, heavy.pose_s],','    tonfa: [heavy.pose_w, heavy.pose_s],\n')
    p.before(f,'    knuckles: "Iron Tornado",','    tonfa: "Read & Reversal",\n')
    # These maps can have intermediate entries from Raigo/Zephyr patches: append at end of relevant kit row instead.
    for line_prefix, item in [('    wind: 2.00,', 'tonfa: 1.92'),
                              ('    wind: 1.85,', 'tonfa: 1.75'),
                              ('    wind: 4.2,', 'tonfa: 4.20')]:
        source=p.data[f]; rows=[m for m in re.finditer(r'^\s*wind:\s*'+re.escape(line_prefix.split(': ')[1])+r'.*$', source, re.M)]
        # select a row containing multiple kit keys (not just any attack fields)
        rows=[m for m in rows if 'glaive:' in m.group() and 'sickle:' in m.group()]
        if len(rows)!=1: raise RuntimeError(f'{f}: cannot locate {line_prefix} riposte tuning row')
        row=rows[0].group(); revised=row.rstrip() + f' {item},'
        if row.rstrip().endswith(','): revised=row.rstrip() + f' {item},'
        p.once(f,row,revised)
    p.after(f, '    knuckles: knuckles,\n', '    tonfa: tonfaMoves,\n')
    p.before(f,'    case "knuckles":\n', '''    case "tonfa":
      return a({ name: "Final Verdict: Eightfold", desc: "Eight timed tonfa, elbow and knee contacts. All eight use ordinary collision, guard and dodge checks.",
        cd: 43, wind: 0.29, active: 1.40, recover: 0.64, dmg: 35, guard: 12, reach: 1.98,
        knock: 0.50, stun: 0.15, style: "renji_eightfold", pose_w: "rnv_w", pose_s: "rnv_s" });
''')
    p.before(f,'function knuckles(): Record<string, Attack> {', '''/** RENJI_COUNTER_FIST_V2: no magical ranged hits; each hit uses real melee collision. */
function tonfaMoves(): Record<string, Attack> {
  return {
    l1: a({ name:"Guard-Line Jab", wind:.095,active:.075,recover:.13,dmg:41,guard:12,reach:1.76,lunge:2.1,knock:.32,stun:.14,style:"renji_tonfa",pose_w:"rn1_w",pose_s:"rn1_s",next:"l2" }),
    l2: a({ name:"Reverse-Grip Snap", wind:.105,active:.075,recover:.14,dmg:45,guard:13,reach:1.79,lunge:2.0,knock:.42,stun:.15,style:"renji_tonfa",pose_w:"rn2_w",pose_s:"rn2_s",next:"l3" }),
    l3: a({ name:"Shoulder Elbow", wind:.12,active:.075,recover:.15,dmg:49,guard:14,reach:1.70,lunge:1.7,knock:.55,stun:.18,style:"renji_elbow",pose_w:"rn3_w",pose_s:"rn3_s",next:"l4" }),
    l4: a({ name:"Intercepting Knee", wind:.14,active:.085,recover:.17,dmg:54,guard:16,reach:1.73,lunge:1.6,knock:.72,stun:.19,style:"renji_knee",pose_w:"rn4_w",pose_s:"rn4_s",next:"l5" }),
    l5: a({ name:"Cross-Tonfa Verdict", wind:.17,active:.095,recover:.31,dmg:89,guard:26,reach:1.89,lunge:1.7,knock:3.1,stun:.32,style:"renji_tonfa",pose_w:"rn5_w",pose_s:"rn5_s" }),
    heavy:a({ name:"Guard-Crushing Backfist",wind:.31,active:.12,recover:.52,dmg:152,guard:47,reach:1.91,lunge:1.2,knock:4.6,stun:.43,heavy:true,style:"renji_tonfa",pose_w:"rnh_w",pose_s:"rnh_s" }),
    z:a({ name:"Hundred Fangs",desc:"Six separately defendable tonfa and elbow strikes, ending in a rising knee.",cd:9,wind:.15,active:.93,recover:.42,dmg:26,guard:9,reach:1.90,lunge:2.7,knock:.4,stun:.11,style:"renji_hundred",pose_w:"rnz_w",pose_s:"rnz_s" }),
    x:a({ name:"Iron Reflection",desc:"For 15 seconds, Guard is disabled but every incoming attack is automatically perfect-parried. Base 30s cooldown, reduced 5% per Read stack at activation.",cd:30,type:"buff",mode:"renji_reflection",duration:15,wind:.08,active:.05,recover:.19,pose_w:"rnx_w",pose_s:"rnx_s" }),
    c:a({ name:"Blindside Step",desc:"Fast grounded pivot into two real close-range tonfa strikes. Not a teleport.",cd:12,wind:.15,active:.40,recover:.34,dmg:50,guard:17,reach:1.97,lunge:4.1,knock:1.3,stun:.19,style:"renji_blindside",pose_w:"rnc_w",pose_s:"rnc_s" }),
  };
}

''')
    p.after(f,'  t.pc = parryCounterAttack(kit, element, t);\n', '''  if (kit === "tonfa") {
    // Riposte is a real directional 3-hit combo, with optional 3-Read finisher.
    t.pc = { ...t.pc, name:"Counter Route", desc:"Directional three-hit elbow/tonfa/knee sequence after a perfect parry.",
      style:"renji_riposte",wind:.25,active:.55,recover:.29,dmg:114,guard:35,reach:1.94,
      no_parry:true,pose_w:"rnpc_w",pose_s:"rnpc_s",next:"" };
  }
''')
    p.once(f, '  if (t.pc) t.pc.wind = 0.40;', '  if (t.pc) t.pc.wind = kit === "tonfa" ? 0.25 : 0.40;')
    # Normalized pose entries and leg stability; no reliance on other fighters' pose keys.
    p.before(f,'const KNUCKLES: Record<string, Pose> = {', '''// RENJI_COUNTER_FIST_V2: defensive footwork, hip-driven elbows and spring-loaded knees.
const RENJI_TONFA: Record<string, Pose> = {
  ...COMMON,
  idle: K(P([.10,-.18,.03],[-.07,.17,0],[-1.18,.28,-.32],[.30,.15,-.10],[-1.20,-.25,.34],[.31,-.11,.12],[-.26,-.12,.19],[.23,.11,-.19],-.14),.35,.29),
  block: K(P([.17,-.10,0],[-.12,.13,0],[-1.53,.26,-.38],[.46,.08,.12],[-1.56,-.24,.42],[.45,0,-.12],[-.32,-.12,.20],[.30,.12,-.19],-.16),.39,.39),
  charge:K(P([.26,-.43,.03],[-.04,.2,0],[-1.82,.34,-.45],[.50,0,.1],[-1.61,-.28,.39],[.38,0,-.13],[-.48,-.07,.19],[.43,.09,-.16],-.19),.5,.48),
  rn_cancel_left:K(P([.28,-.52,.09],[-.12,.22,.02],[-1.31,.45,-.58],[.48,.01,.25],[-1.89,-.39,.52],[.54,0,-.22],[-.54,-.16,.22],[.31,.14,-.21],-.21),.54,.46),
  rn_cancel_right:K(P([.29,.50,-.06],[-.12,-.19,0],[-1.96,.33,-.49],[.49,0,.22],[-1.29,-.50,.40],[.31,-.01,-.27],[-.31,-.17,.20],[.57,.09,-.22],-.20),.46,.51),
  rn_cancel_cross:K(P([.26,.02,0],[-.08,.04,0],[-1.87,.33,-.42],[.55,0,.28],[-1.87,-.32,.42],[.55,0,-.28],[-.42,-.13,.20],[.41,.13,-.20],-.20),.51,.47),
  rn_parry_cross:K(P([.22,-.25,.05],[-.11,.18,0],[-1.98,.44,-.45],[.53,.06,.38],[-1.95,-.42,.43],[.51,-.02,-.35],[-.57,-.13,.19],[.46,.13,-.19],-.21),.55,.43),
  rn_parry_redirect:K(P([.20,.24,-.04],[-.12,-.2,0],[-1.44,-.59,-.43],[.40,0,.20],[-1.73,.29,.46],[.41,0,-.20],[-.48,-.11,.17],[.37,.11,-.20],-.19),.46,.37),
  rn1_w:K(P([.18,-.44,.04],[-.06,.24,0],[-.73,.49,-.39],[.41,0,-.12],[-1.42,-.28,.42],[.41,0,.1],[-.40,-.07,.19],[.29,.05,-.19],-.19),.40,.35),
  rn1_s:K(P([.25,.38,-.06],[-.1,-.18,0],[-1.84,-.33,-.36],[.26,0,.12],[-1.18,-.19,.35],[.33,0,-.12],[-.50,-.04,.16],[.39,.08,-.19],-.16),.34,.37),
  rn2_w:K(P([.15,.43,.04],[-.05,-.3,0],[-1.23,.28,-.44],[.38,0,.14],[-.70,-.52,.45],[.37,0,-.14],[-.35,-.08,.20],[.33,.05,-.16],-.14),.39,.40),
  rn2_s:K(P([.23,-.51,-.06],[-.1,.35,0],[-1.19,.24,-.41],[.25,0,-.1],[-1.96,.44,.31],[.20,0,.12],[-.53,-.08,.19],[.44,.09,-.16],-.19),.41,.42),
  rn3_w:K(P([.32,-.57,.06],[-.05,.32,0],[-1.12,-.20,-.31],[.28,0,-.16],[-1.45,-.42,.49],[.42,0,.04],[-.48,-.11,.16],[.43,.12,-.17],-.25),.44,.45),
  rn3_s:K(P([.32,.43,-.04],[-.15,-.21,0],[-1.55,.60,-.10],[.43,0,.24],[-1.33,.09,.34],[.24,0,-.1],[-.68,-.05,.15],[.58,.08,-.20],-.21),.47,.35),
  rn4_w:K(P([.18,-.23,.04],[-.06,.12,0],[-1.51,.24,-.32],[.42,0,.17],[-1.44,-.24,.37],[.39,0,-.14],[-.28,0,.19],[-.82,.06,-.30],-.24),.3,1.10),
  rn4_s:K(P([-.04,.25,-.04],[-.1,-.1,0],[-1.18,.26,-.30],[.34,0,.12],[-1.25,-.32,.39],[.36,0,-.14],[-.32,0,.20],[-1.41,.06,-.31],-.11),.24,.13),
  rn5_w:K(P([.30,-.67,.06],[-.05,.41,0],[-1.92,.24,-.36],[.43,0,.17],[-1.84,-.34,.39],[.38,0,-.13],[-.53,-.14,.16],[.42,.12,-.17],-.23),.56,.48),
  rn5_s:K(P([.37,.47,-.03],[-.22,-.19,0],[-1.40,.52,-.35],[.16,0,.12],[-1.44,-.45,.32],[.17,0,-.12],[-.68,-.07,.16],[.57,.11,-.18],-.24),.50,.46),
  rnh_w:K(P([.30,-.67,.05],[0,.32,0],[-2.35,.33,-.4],[.49,0,.12],[-2.18,-.28,.36],[.51,0,-.08],[-.57,-.13,.21],[.49,.12,-.18],-.24),.53,.50),
  rnh_s:K(P([.51,.39,-.04],[-.2,-.10,0],[-1.02,.41,-.36],[.13,0,.17],[-1.09,-.21,.31],[.22,0,-.09],[-.75,-.08,.16],[.66,.11,-.21],-.29),.60,.55),
  rnz_w:K(P([.17,-.41,.04],[-.07,.18,0],[-1.57,.41,-.40],[.48,0,.14],[-1.55,-.40,.40],[.49,0,-.12],[-.38,-.10,.2],[.33,.13,-.20],-.20),.47,.42),
  rnz_s:K(P([.30,.25,-.02],[-.17,-.11,0],[-1.65,.41,-.27],[.25,0,.15],[-1.42,-.28,.36],[.24,0,-.09],[-.62,-.08,.19],[.52,.07,-.18],-.19),.46,.51),
  rnx_w:K(P([.18,-.15,0],[-.1,.12,0],[-2.03,.33,-.41],[.55,0,.25],[-2.04,-.33,.41],[.55,0,-.25],[-.44,-.13,.19],[.39,.12,-.19],-.24),.59,.52),
  rnx_s:K(P([.13,.15,0],[-.12,.04,0],[-1.51,.24,-.37],[.44,0,.13],[-1.52,-.24,.37],[.45,0,-.14],[-.38,-.09,.21],[.35,.11,-.18],-.17),.42,.42),
  rnc_w:K(P([.34,-.65,.11],[-.1,.32,0],[-1.14,.42,-.40],[.41,0,.18],[-1.62,-.23,.34],[.44,0,-.13],[-.80,-.10,.18],[.29,.10,-.24],-.31),.66,.50),
  rnc_s:K(P([.11,.70,-.09],[-.15,-.26,0],[-1.84,.21,-.32],[.21,0,.17],[-1.20,-.36,.36],[.30,0,-.14],[-.51,-.11,.22],[.61,.14,-.17],-.19),.38,.37),
  rnpc_w:K(P([.19,-.34,.05],[-.09,.28,0],[-1.86,.24,-.36],[.50,0,.19],[-1.72,-.30,.40],[.51,0,-.16],[-.55,-.13,.19],[.49,.11,-.19],-.23),.52,.46),
  rnpc_s:K(P([.28,.38,-.04],[-.17,-.18,0],[-1.50,.46,-.33],[.22,0,.14],[-1.52,-.25,.37],[.24,0,-.11],[-.61,-.11,.17],[.55,.13,-.17],-.22),.42,.38),
  rnv_w:K(P([.21,-.65,.04],[-.03,.31,0],[-2.16,.27,-.37],[.41,0,.16],[-1.84,-.32,.41],[.43,0,-.13],[-.57,-.12,.18],[.41,.12,-.19],-.21),.55,.47),
  rnv_s:K(P([.40,.42,-.06],[-.13,-.14,0],[-1.52,.60,-.29],[.23,0,.13],[-1.26,-.37,.32],[.23,0,-.1],[-.75,-.07,.19],[.62,.10,-.21],-.26),.57,.51),
};

''')
    p.after(f,'  knuckles: KNUCKLES,\n','  tonfa: RENJI_TONFA,\n')


def add_fighter(p):
    f='src/game/fighter.ts'
    p.before(f,'  parryRecoilT = 0;', '''  // RENJI_COUNTER_FIST_V2 — combat-state-owned Read and perfect-parry form.
  renjiRead = 0;
  renjiReadDecayT = 30;
  renjiReflectT = 0;
  renjiParryFxT = 0;
  renjiCounterRoute = 0; // 0 side, 1 overhead, 2 low, 3 thrust, 4 projectile
  private renjiLastReadToken = "";
  private renjiLastParryToken = "";
  private renjiCancelPose = "rn_cancel_cross";
  /** Called synchronously from receiveHit, before the parry result is returned.
   * Cancel the interrupted strike and invalidate every pending arena hit by serial.
   * The next model blend drives a visible catch -> cross -> redirect animation. */
  renjiInterceptAttack(attacker: Entity, a: Attack) {
    if (this.kit !== "tonfa") return;
    const token = attacker instanceof Fighter
      ? `${attacker.id}:${attacker.swingSerial}`
      : `${attacker.id}:${Math.floor(this.clock * 2)}`;
    if (this.renjiLastParryToken === token) return; // one animation per incoming swing
    this.renjiLastParryToken = token;
    if (this.state === S.ATTACK || this.state === S.CHARGE) {
      const source = this.atkId;
      this.renjiCancelPose = /^l[135]$/.test(source) || source === "z" ? "rn_cancel_left"
        : /^l[24]$/.test(source) || source === "c" ? "rn_cancel_right"
        : "rn_cancel_cross";
      this.swingSerial++; // invalidate delayed onSwing + all queued multi-hit pulses
      this.atk = null;
      this.atkId = "";
      this.atkPhase = 0;
      this.buffered = false;
      this.holding = false;
      this.comboNext = "l1";
      this.comboTimer = 0;
      this.comboPauseT = 0;
      this.trail.emitting = false;
      this.model.charge = 0;
      this.intent.attack = false;
      this.intent.skill = "";
      this.setState(S.IDLE); // returns the arms to pose blending, not a hit-stun
      this.renjiParryFxT = Math.max(this.renjiParryFxT, 0.40);
    } else {
      this.renjiCancelPose = "rn_cancel_cross";
      this.renjiParryFxT = Math.max(this.renjiParryFxT, 0.27);
    }
    this.model.recoil = Math.max(this.model.recoil, 0.42);
  }
  renjiAwardRead(attacker: Entity | null, a: Attack) {
    if (this.kit !== "tonfa") return;
    // One stack per actual swing, not per multi-hit sub-ID. Mob hits are throttled.
    const token = attacker instanceof Fighter ? `${attacker.id}:${attacker.swingSerial}` : `${attacker?.id ?? "unknown"}:${Math.floor(this.clock * 2)}`;
    if (this.renjiLastReadToken !== token) {
      this.renjiLastReadToken = token;
      this.renjiRead = Math.min(3, this.renjiRead + 1);
      this.renjiReadDecayT = 30;
      this.renjiParryFxT = Math.max(this.renjiParryFxT, 0.23);
    }
    if (a.type === "projectile") this.renjiCounterRoute = 4;
    else if (/low|sweep|trip|ankle|slide/i.test(a.name + " " + a.style)) this.renjiCounterRoute = 2;
    else if (/thrust|pierc|stab|lance|spear/i.test(a.name + " " + a.style)) this.renjiCounterRoute = 3;
    else if (/heavy|overhead|smash|slam|cleave|upper/i.test(a.name + " " + a.style) || a.heavy) this.renjiCounterRoute = 1;
    else this.renjiCounterRoute = 0;
  }
  renjiRecoilSeconds() { return 0.30 + this.renjiRead * (0.40 / 3); }
  renjiSpendRead() { if (this.renjiRead === 3) { this.renjiRead = 0; this.renjiReadDecayT = 30; return true; } return false; }
''')
    p.after(f, '    this.counterT = Math.max(this.counterT - dt, 0);\n', '''    if (this.kit === "tonfa") {
      this.renjiReflectT = Math.max(0, this.renjiReflectT - dt);
      this.renjiParryFxT = Math.max(0, this.renjiParryFxT - dt);
      if (this.renjiRead > 0) {
        this.renjiReadDecayT -= dt;
        if (this.renjiReadDecayT <= 0) {
          this.renjiRead--;
          this.renjiReadDecayT += 30; // one stack per thirty seconds, not all at once
        }
      } else this.renjiReadDecayT = 30;
    }
''')
    p.before(f,'    if (this.kit==="tristaff" && this.dragonMode===1) {', '''    // RENJI: Guard input is disabled throughout Iron Reflection (player AND CPU).
    // The actual automatic parry happens in receiveHit(), independent of guard.
    if (this.kit === "tonfa" && this.renjiReflectT > 0) {
      it.block = false;
      if (this.state === S.BLOCK) this.setState(S.IDLE);
    }
    // Finish the physical catch before another input can restart an attack.
    // A short ~0.18s input lock is cosmetic; the full reflection lasts 15s.
    if (this.kit === "tonfa" && this.renjiParryFxT > 0.22) {
      it.attack = false;
      it.skill = "";
      it.skillHeld = "";
    }
''')
    p.before(f,'    if (this.invulnT > 0) {', '''    // RENJI_COUNTER_FIST_V2: all real incoming hits become perfect parries during X.
    // This catches projectiles/heavies and no_parry skills; standing idle is sufficient.
    if (this.kit === "tonfa" && this.renjiReflectT > 0 &&
        attacker && attacker.team !== this.team && a.dmg > 0) {
      this.renjiInterceptAttack(attacker, a); // attacks ACTUALLY end on perfect parry
      this.model.flash("#ffe780", 0.17);
      return "parry";
    }
''')
    p.before(f, '    // Standardize the parry counter windup from the already-scaled timing.','''    // Renji's riposte has four independent counter routes and cannot start a parry loop.
    if (this.kit === "tonfa" && id === "pc" && this.atk) {
      this.atk = { ...this.atk, no_parry:true, style:"renji_riposte" };
      this.atk.pose_w = "rnpc_w";
      this.atk.pose_s = ["rnpc_s","rn5_s","rn4_s","rn3_s","rn2_s"][this.renjiCounterRoute] ?? "rnpc_s";
    }
''')
    p.once(f, '    } else this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 :\n', '''    } else this.cooldowns[k] = this.kit === "tonfa" && k === "x"
      ? this.attacks.x.cd * this.cdMult * (1 - 0.05 * this.renjiRead)
      : this.attacks[k].type === "barrel" ? 0.6 :
''')
    p.before(f,'    this.poseName = p;\n    this.poseSpeed = sp;', '''    if (this.kit === "tonfa" && this.renjiParryFxT > 0 &&
        ![S.KO,S.KNOCKDOWN,S.HITSTUN,S.STAGGER,S.WIN].includes(this.state)) {
      p = this.renjiParryFxT > 0.29 ? this.renjiCancelPose
        : this.renjiParryFxT > 0.14 ? "rn_parry_cross" : "rn_parry_redirect";
      sp = this.renjiParryFxT > 0.29 ? 112 : this.renjiParryFxT > 0.14 ? 100 : 76;
    }
''')
    # Both active and remote model blend should receive the cosmetic parry pulse.
    anchor='    this.model.blend(this.state === S.WIN\n'
    # Matches two occurrences (update and puppet); insert in each once.
    if p.data[f].count(anchor)!=2: raise RuntimeError('fighter.ts: expected two model blend blocks')
    p.data[f] = p.data[f].replace(anchor,'    this.model.renjiParryT = this.kit === "tonfa" ? this.renjiParryFxT : 0;\n'+anchor)
    # Revive/KO resets only Renji's new temporary state.
    reset='    this.renjiRead = 0; this.renjiReadDecayT = 30; this.renjiReflectT = 0; this.renjiParryFxT = 0; this.renjiLastReadToken = ""; this.renjiLastParryToken = ""; this.renjiCancelPose = "rn_cancel_cross";\n'
    anchor='    this.parryRecoilT = 0; this.parryCounterPendingDepth = 0; this.parryCounterDepth = 0; this.counterVisualRemote = false;'
    if p.data[f].count(anchor)!=2: raise RuntimeError('fighter.ts: expected two round-reset anchors')
    p.data[f]=p.data[f].replace(anchor,reset+anchor)
    # Append network fields to tail without shifting ANY existing field offsets.
    start=p.data[f].index('  snapshot(): any[] {'); stop=p.data[f].index('  applySnapshot(s: any[]) {', start)
    section=p.data[f][start:stop]
    match=re.search(r'return\s*\[([\s\S]*?)\];',section)
    if not match: raise RuntimeError('fighter.ts: cannot locate snapshot array')
    expr=match.group(1)
    # Count top-level comma delimiters. This supports V6 appendices and TS calls.
    depth=0; quote=None; escaped=False; commas=0
    for ch in expr:
        if quote:
            if escaped: escaped=False
            elif ch=='\\': escaped=True
            elif ch==quote: quote=None
        elif ch in "\"'`": quote=ch
        elif ch in '([{': depth+=1
        elif ch in ')]}': depth-=1
        elif ch==',' and depth==0: commas+=1
    count=commas+1
    last=expr.rstrip(); trailing=expr[len(last):]
    injected=last+f',\n      this.renjiRead, +this.renjiReadDecayT.toFixed(2), +this.renjiReflectT.toFixed(2), +this.renjiParryFxT.toFixed(2)'+trailing
    newsection=section.replace(match.group(1),injected,1)
    p.once(f, section, newsection)
    # Restrict to applySnapshot() body; the same dragon assignment appears elsewhere.
    ix=p.data[f].index('  applySnapshot(s: any[]) {')
    tail=p.data[f][ix:]
    anchor='    this.model.dragonMode=this.dragonMode;'
    assert anchor in tail
    p.once(f,tail,tail.replace(anchor, f'''    // RENJI: appended snapshot fields, preserving all older indices.
    this.renjiRead = s.length > {count} ? s[{count}] : 0;
    this.renjiReadDecayT = s.length > {count+1} ? s[{count+1}] : 30;
    this.renjiReflectT = s.length > {count+2} ? s[{count+2}] : 0;
    this.renjiParryFxT = s.length > {count+3} ? s[{count+3}] : 0;
''' + anchor, 1))


def add_game(p):
    f='src/game/game.ts'
    p.before(f, '    } else if (a.mode === "counter") {', '''    } else if (a.mode === "renji_reflection" && f.kit === "tonfa") {
      f.renjiReflectT = a.duration;
      f.renjiParryFxT = Math.max(f.renjiParryFxT, 0.22);
      this.fxp("flash", f.chest(), "#ffd65b", 0.85, 0.24, 0.9);
      this.fxp("ring", f.root.position.clone(), "#fff0a3", 1.15, 0.22, 0.9);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.85, 0)), "IRON REFLECTION 15s", "#ffe589", 0.85);
''')
    p.before(f, '        df.recoverFromParry();', '''        // RENJI: calculate recoil from PRE-hit Read, then earn at most one per swing.
        const renjiRecoil = df.kit === "tonfa" ? df.renjiRecoilSeconds() : 0.50;
        if (df.kit === "tonfa") {
          df.renjiAwardRead(attacker, a);
          this.fxp("flash", df.chest(), "#ffe186", 0.48, 0.12, 0.9);
          this.fxp("sparks", shieldPos, "#fff6b0", 44, 8);
          this.fxp("num", df.chest().add(new THREE.Vector3(0, 0.65, 0)),
            `READ ${df.renjiRead}/3`, "#ffe498", 0.72);
        }
''')
    p.once(f, '              attacker.applyParryRecoil(0.50);', '              attacker.applyParryRecoil(renjiRecoil);')
    p.once(f, '          df.armParryCounter(attacker, attacker.atkId === "pc" ? attacker.parryCounterDepth + 1 : 0);',
      '''          // Auto-perfect-parry still defends against a riposte, but cannot start a new counter loop.
          if (!(df.kit === "tonfa" && (a.style === "renji_riposte_hit" || a.id === "renji_insight")))
            df.armParryCounter(attacker, attacker.atkId === "pc" ? attacker.parryCounterDepth + 1 : 0);''')
    p.before(f,'    switch (a.type) {\n', '''    // RENJI: real multi-contact attacks resolve at their own animation beats.
    if (f.kit === "tonfa" && ["renji_hundred","renji_blindside","renji_eightfold","renji_riposte"].includes(a.style)) {
      this.renjiMulti(f, a); return;
    }
''')
    p.before(f,'  private melee(f: Fighter, a: Attack): boolean {', '''  // RENJI_COUNTER_FIST_V2 — every contact is separately dodged, blocked, clashed or hit.
  private renjiMulti(f: Fighter, a: Attack) {
    const round = this.round, serial = f.swingSerial;
    const riposte = a.style === "renji_riposte";
    const count = riposte ? 3 : a.style === "renji_hundred" ? 6 : a.style === "renji_eightfold" ? 8 : 2;
    const interval = a.active / Math.max(1, count);
    const route = f.renjiCounterRoute;
    const poseList = riposte ? [
        ["rn2_s","rn3_s","rn5_s"],  // side attack: deflect -> elbow -> tonfa
        ["rn_parry_cross","rn4_s","rn5_s"], // overhead: catch -> knee -> rising finish
        ["rn4_s","rn1_s","rn5_s"], // low: lift -> jab -> downward tonfa
        ["rn_parry_redirect","rn3_s","rn2_s"], // thrust: trap -> elbow -> reverse
        ["rn_parry_cross","rn2_s","rn5_s"], // projectile -> close-range reply
      ][Math.min(4,Math.max(0,route))] :
      ["rn1_s","rn2_s","rn3_s","rn4_s","rn5_s","rnh_s","rnv_s","rn5_s"];
    for(let i=0;i<count;i++) this.laterCombo(f, Math.min(a.active-0.01,interval*(i+0.42)), () => {
      if (round !== this.round || f.isDown() || f.state !== S.ATTACK || f.swingSerial !== serial) return;
      const last = i===count-1;
      f.poseOverride = poseList[i % poseList.length];
      const pulse: Attack = { ...a, id:`${a.id}_rn${i}`, style: riposte ? "renji_riposte_hit" : "renji_pulse",
        dmg: riposte ? [36,37,41][i] : a.dmg,
        guard: riposte ? [10,12,13][i] : a.guard,
        knock: last ? (riposte ? 2.8 : a.style==="renji_eightfold" ? 4.2 : 2.1) : 0.18,
        stun: last ? 0.26 : 0.09, heavy: last && a.style==="renji_eightfold",
        no_parry: riposte };
      const connected=this.melee(f,pulse);
      this.fxp("slashes", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), last ? "#fff1aa" : "#f6ce6b");
      if (riposte && last && connected && f.renjiSpendRead()) {
        // The 3-stack bonus is an extra, independently dodgeable finisher.
        this.laterCombo(f, 0.08, () => {
          if (round !== this.round || f.isDown() || f.swingSerial !== serial || f.state!==S.ATTACK) return;
          f.poseOverride="rnh_s";
          this.melee(f,{...a,id:"renji_insight",style:"renji_pulse",dmg:65,guard:24,
            reach:1.95,knock:4.1,stun:0.35,no_parry:true});
          this.fxp("sparks", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), "#fff2a0", 35, 7);
        });
      }
    });
  }

''')
    p.before(f,'      if (f.kit === "tristaff") passives.push(','''      if (f.kit === "tonfa") passives.push({ label:"READ", value:`${f.renjiRead}/3 · ${f.renjiReadDecayT.toFixed(0)}s` + (f.renjiReflectT > 0 ? ` · REFLECT ${f.renjiReflectT.toFixed(1)}s` : ""),
        desc:"Perfect parries grant Read, max 3. Lose only one stack every 30 seconds without a new stack. X lasts 15s, auto-perfect-parries every incoming hit, disables Guard, and cools down 5% faster per Read stack (30s base). Recoil is 0.30–0.70s.", icon:"/icons/passives/renji.webp" });
''')


def add_model(p):
    f='src/game/model.ts'
    p.before(f,'  private gripL: THREE.Object3D | null = null;', '''  // RENJI_COUNTER_FIST_V2: compact real tonfas held with their perpendicular grips.
  renjiParryT = 0;
  private renjiTonfas: THREE.Group[] = [];
''')
    p.before(f,'      case "knuckles": this.buildKnuckles(); break;', '''      case "tonfa": this.buildRenjiTonfas(); break;
''')
    p.before(f,'  private buildKnuckles() {', '''  private buildRenjiTonfas() {
    // Two independent weapons; the long side lies alongside each forearm.
    for (let i=0;i<2;i++) {
      const hand = i===0 ? this.hand_r : this.hand_l;
      const root = pivot(hand, [0,-0.065,0.035]);
      mesh(root, cyl(0.024,0.028,0.51,10), this.tn("#343d42"), [0,0.145,0]);
      mesh(root, cyl(0.028,0.035,0.21,10), this.tn("#25292c"), [0,-0.05,0.095], [PI/2,0,0]);
      mesh(root, cyl(0.038,0.041,0.026,12), this.metal(), [0,-0.055,0.205], [PI/2,0,0]);
      for (const y of [0.335,0.37]) mesh(root, torus(0.026,0.036), this.tn(this.look.trim), [0,y,0], [PI/2,0,0]);
      mesh(root, cyl(0.017,0.031,0.055,9), this.metal(), [0,0.414,0]);
      this.renjiTonfas.push(root);
    }
    this.bladeBase=this.renjiTonfas[0];
    this.bladeTip=pivot(this.renjiTonfas[0],[0,.415,0]);
    this.castPoint=this.bladeTip;
    this.shieldNode=this.hand_l;
  }

''')
    p.before(f,'    if (this.bowPivot) this.updateBow();', '''    // Brief wrist catch, elbow retraction and tonfa flick on successful parries.
    if (this.renjiTonfas.length === 2) {
      const snap = THREE.MathUtils.clamp(this.renjiParryT / 0.40,0,1);
      const flip = Math.sin((1-snap)*Math.PI);
      this.renjiTonfas[0].rotation.z = THREE.MathUtils.damp(this.renjiTonfas[0].rotation.z, -0.68*flip, 34, dt);
      this.renjiTonfas[1].rotation.z = THREE.MathUtils.damp(this.renjiTonfas[1].rotation.z, 0.68*flip, 34, dt);
      this.renjiTonfas[0].rotation.x = THREE.MathUtils.damp(this.renjiTonfas[0].rotation.x, 0.27*flip, 31, dt);
      this.renjiTonfas[1].rotation.x = THREE.MathUtils.damp(this.renjiTonfas[1].rotation.x, 0.27*flip, 31, dt);
    }
''')
    p.before(f,'    this.vrmRig = new VrmRig(vrm, {', '''    // Renji only: yellow hair and amber eyes on a CLONED material.
    // Aster retains his original appearance even when both fight in one match.
    if (this.kit === "tonfa" && this.look.vrm === "aster") {
      vrm.scene.traverse(node => {
        if (!(node instanceof THREE.Mesh)) return;
        const recolor = (m: THREE.Material): THREE.Material => {
          const n = m.name.toLowerCase();
          if (!n.includes("_hair") && !n.includes("eyeiris")) return m;
          const clone = m.clone() as THREE.Material & { color?: THREE.Color };
          clone.color?.set(n.includes("hair") ? "#ffd438" : "#edae2f");
          return clone;
        };
        node.material = Array.isArray(node.material) ? node.material.map(recolor) : recolor(node.material);
      });
    }
''')
    p.before(f,'    if (this.kit === "knuckles") { this.vrmRig.boxer = true;', '''    if (this.kit === "tonfa") { this.vrmRig.boxer = true; this.vrmRig.bladed = 0.70; this.vrmRig.style = "light"; }
''')


def add_ai(p):
    f='src/game/ai.ts'
    p.once(f,'      viable = a.mode === "frost_aegis" ?',
      '''      viable = a.mode === "renji_reflection"
        ? f.renjiReflectT <= 0 && ((attackComing && distance < 3.0) || close)
        : a.mode === "frost_aegis" ?''')
    p.before(f,'  aster: { range:', '''  // RENJI_COUNTER_FIST_V2 — patient close-range reader, stronger at punishing recoveries.
  renji: { range: 1.53, heavy: 0.19, combo: 0.90, bait: 0.77, pressure: 0.62, skillBias: [1.25, 1.85, 1.30] },
''')
    p.before(f,'      case "aster":\n        if (name === "Shield Bash")', '''      case "renji":
        // Read the opponent, activate reflection before a committed enemy skill,
        // and take fast punishes only at honest tonfa range.
        if (name === "Iron Reflection") points += f.renjiReflectT > 0 ? -5.0 :
          (attackComing && distance < 3.0 ? 3.6 : close ? 1.4 : 0.18);
        if (name === "Hundred Fangs") points += punish && close ? 2.7 : close ? 0.45 : -0.4;
        if (name === "Blindside Step") points += attackComing && close ? 2.4 : distance > 1.5 && distance < 3.1 ? 1.1 : 0.2;
        break;
''')


def add_presentation(p):
    f='src/game/presentation.ts'
    p.before(f,'  aster: { // Massive armored', '''  // RENJI_COUNTER_FIST_V2 — tightly chambered tonfa guard, lightning intercept and cross-arm pose.
  renji: {
    ready:{torso:[.15,-.24,.04],head:[-.10,.14,0],arm_r:[-1.24,.24,-.38],arm_l:[-1.27,-.24,.40],leg_l:[-.26,-.13,.18],leg_r:[.28,.11,-.18],hips_y:-.15,knee:[.37,.32]},
    wind:{torso:[.25,-.53,.09],head:[.02,.30,0],arm_r:[-1.82,.48,-.44],arm_l:[-1.45,-.38,.47],leg_l:[-.55,-.08,.15],leg_r:[.45,.13,-.21],hips_y:-.23,knee:[.55,.42]},
    move:{torso:[.16,.42,-.07],head:[-.14,-.18,0],arm_r:[-2.18,-.19,-.31],arm_l:[-1.78,.34,.43],leg_l:[-.67,-.09,.14],leg_r:[.55,.10,-.20],hips_y:-.16,knee:[.40,.34]},
    hero:{torso:[.21,-.08,0],head:[-.13,.07,0],arm_r:[-1.67,.38,-.45],arm_l:[-1.70,-.32,.42],leg_l:[-.34,-.13,.19],leg_r:[.31,.12,-.18],hips_y:-.18,knee:[.46,.42]},
    win:{torso:[.05,.08,0],head:[-.16,.08,0],arm_r:[-2.12,.22,-.44],arm_l:[-2.1,-.25,.43],leg_l:[-.27,-.12,.20],leg_r:[.28,.14,-.20],hips_y:-.14,knee:[.33,.34]},tempo:1.26 },
''')


# Embedded temporary character/passive/skill art: no external files required.
# Each file is a small 256x256 WebP. Will NEVER overwrite the user's custom icons.
RENJI_ICON_ARCHIVE_B85 = (
    'c-mZ>Q*b2;(5++Jnb@}NOq@(?+jg>JPwa_p+niVv+ctN+@A>b`#j09WU0wayU8`R{6?sS~EU^F4A)$?dfs-_ZB^Maj|Cs2%p0kIky^R@*'
    'jhU098;hB>iK`ontA(Sj4YQYpsk5rAw6x)WgIZGJDw-<1q^kebiM?RC;PhbNVBo@RIMEX1WMo)Bo<~R_p_;+W_t{yD#6g&E4sT+QxJH4s'
    'Uw<C0fT-Uj=YhuFt1J0efa3SG*ST|}3sC#_Jt*<b?>ph^^m)!xq!@Je5e&fn_WB<C{P|wL(RbWu+;1ZC0xAdEfoMKbZtOmI-km;;PDQpp'
    'g8}^Cmmt83)0)-G?i%X5(;MiWxD(J}1e?DM*a%$zga?U&NI<J=kRYQ9*zfNjfMcR#P{L>3_wXj$sgon1_9N4pWl5y}QQ~!VV|NB*{nZD8'
    'f81^A*V-vCN(C{4NWO+&9v}SfEN*5If#uhLQ@{`?6jb;vzkhktf8qP{G2jOB^Y(+}Eq_)dvH$p$=b?WK^)3Ge^iHzVKN7hA#Q{<SrF@|t'
    'i*z`ZfX+cNAf^Y*&$$oSkNR8CF~BC!w>LiU3IGDiekFr0EJeqO4f=KG=-cU{AT{OA{4OMCwf(3vl_@1>ixsb{?LRg@xX%S396WDa5(W`o'
    ';h9i+tElN3s)IJ&q_vnU!b9fkZqh(J$y?PR-b7If`B%97BC)-23{iI$KrhtqOl1o7pANh@1b8V$UjALLan{e%$}=dfAzIIwasAyU<6AV1'
    'px56O-2eVwp>aA~>*4mm_D9(_v=mQ0_Bq}s#1j^l;YDsKP;>>I4#XP!4_~`-{}ErQO>`&<J2cWVp(s++Q*9~%dhxJ~w-wN_YFsF90BZ;('
    'EO?dL$!(2#0z7}2*>O4FZKqZNgV~B8<a9hTZwwF=e-mO@4X&8u_D~-9#ud4!XotId^v|Oz;PUc+*F=O3rvSGF&tkcL{RTL%ZXZu6=O6cq'
    'rL|3O6aN@Y)#Pb}R2o*}?$eLcwV?=zY-)|aIKoR?bds7e=FJ$!LYN<^zq-Td;dqM=DIl?Ej$*}q7nj=L!E34x#NV#*Bi}tmP8aE}{fYs@'
    'O~;lVp06NtZk(>rB+g1WJiwQ2Y-YK(f@g-4!IWp2=}4%wUZ}i94kzf8+_`sG=?*0Ie|9VD{t6T+zXD^|`H4h*x%Y8GlpOIaVTmN6B{?jW'
    '=USgM>4o1f#6eX0Fxq73mY9w~JNCdnD+HVo4`c*fo}6nUN*KBYH%@NT7-w4MvQAP#cpx*C=-yBl{Jio$+~E9iaU8)T1x=VJmDEK&X%!gN'
    'Sbb$)zy<T&<?nihr#0WDBE-s{VYxTlz}NNVa&Ww-C3+0u!hy$!z+(IFYJd_W?s3#0AwHPvxGcEy%ur!av{riH5+|xdmwk>mZ${B%d-!We'
    'QZR5`BTmx?$efLJq@vX(<Y1J3mq*QmMFtdP#GPKR^U9^Ba4XWITXPO8ro(!P+rUP>DBf9juDM51xARvzRf^T{4aTFT)w86$!r4iAOP<4#'
    'lyBx}4bjMKgbe!nHVdOJl{#DJ^PA>J!Xkly-djSpzC^;Hh0v-#?B2UF2I{3d56tR*8GLZcdD{shDPwMGIJEQpFiaJojlrQAYU#vWh6%Nc'
    'AxQYk0C|uq(>Ox4DJE@l(5($6G6`qqJIORY>+AJi8X)H}wrwn{ld71FZLc7`Aeg2UHCb}ec}xvm->gO<2e4CQC;$MWC>atds8(SU7`Gj&'
    'e_T;Zo<nl^Vb$09Yh!ho*wyRb1(7^;*JYfjx3hMMoz8;Ib`ZIcq}JsCgy_|8GhP085QM{ny$VEV&W@DGtkjI)r+Ia_MQV1A5Z>;PW4-N)'
    '5puFzSEZ8(>G=<X?Y0)j#^d2yPQ+H~4J0**4cc|n_V@k5QUF1E1SO3u){aY(iu2uD{8UblJ|Ccx+ZC`XFyG;6i!e}DphW-^L@!rjD?VFf'
    '$QQ!`-<;{ToCT9iqkA$}B`i@OlZ<9Km#uB?gef`j#~<)e7c~3rxS1m>GEM#rwWdU|Ws6r!ZC9q8vmrq;P4I(aOqw`+5Pj1?qH)=gCB&lc'
    '`JQjM^@j%5UojI_<$rBF4Q8bZRs<TGC<nzy)w1_$422cPO-m)}D3b8>c0w|#U|`>%SAn$gV=K}Ycd<3i@k-|-I8Oog;I%CTzm^cduKV5('
    '7mK08KPoi7Lq%4ez0d7-?ljS@EZeh>)=oW8EYGcRHTvwU_<<8zNUI8lP3bUcJ|k6uL1sbS1t7C1#bi%gG0jmHg}O}65BJ!QVgS;&zhn@U'
    'M?GE|5#%wjtxwVNS3V~lAD-$DQ)g`NeTA)2-A2+)8*NwvKPV+Q0r%9PATyK_LDB4T!Gj{g*7dRs;4g2@HkC80@ERh%J%c|msA{3=F{hrv'
    'e>wTZ%?R9eqc7!y^yGzRX}^XjcVL{t@mzVPD9*^O%MIPepcBNaKQ(PG{fDQQl&pem<1=Y^um+8*Thcqqa(JSfiFjxz!zi0ZTe$hlp5G`>'
    'E(N`@AdsQX=GgAuma3un{ot*C{gzl1CSYI`AxAMOzMG24&n-_b)$W7DKOy|BSLKqYzU8zD3t~?Gs_-35%>nrN69`2>i?2k{6BSh{*4%EM'
    'Sbn_XXUt(<-(6ZF$Qom1l|DXaRR_F2@~F}Rh%KJO4le#WWg}#Wu`->E7*vk<u*}1CWaaz>>QV^5-OMCYQSQj+f<N7O_wi15GfMvnDeZV}'
    'XloXaYA^q%aW|F*V9+?_Bh*_o_w0fL@p3@wTm|F^RM*bHFdw~RrQYdd>3JG>yrvS|$Pv^F`o$f`mMUNGr`w$u0lv;3-r{*1QLqhaC|R!K'
    '-NXzD@f$EeNn{xtD$Oj>g!)t~rg7D{>p+ulh7R0Gdq#`4?ypF{tNpMHoylV-pN>uC&~Q`9T!Sy?vk)i33O49@Xt^Jpd!A=yI$Th=ddv71'
    '4f}^7e`94Asds}h8Ei?JAcG@+iP`z(;ZT}8Yg7-r=V^bb51l$EIZGG?i8dkEIPmNBI$}Um%0U<*70_S~oasICF=}hFf3WP$ivin7gP8uY'
    'cw#;DKAIle)d|174#J<!JE4UVh7i<|Hv008?qdF|>^0x=L49<+Cn_6&H+x?k`XP4K69g^wg`K-?-)OMR%IvVh-a5Ln%V+d<uNM;3Z<>MJ'
    'G<ZkId(Mf9Bd$Q93l{LyyCrQ}db0-I?~x~dk*Rn&PsS{nM?z&c?j0soKG3v8<lSd`HBf{<s(2X0L9E>^gjQ7qlaN9eq1zANkd(ok3GRo<'
    'c&ZJd&mp5<#pf;<oZ|s25V+1w#dGLpl8EZ2wYq-CR&m20kp=C$*NS<6f5;+N+iF!kvLVNW0CB~7On)OlWI)1u`B_`LGz-mvh6tnYdUpZ$'
    'N*sp#%W`-ZqyfF3-gy-Gn3>smF@Q~msHs?SQ=qQ>`Lu1`^N`TSRsn-N^m%bbG;&5)mCg|z^Cp!oEbRGS)QN_GU)N!8x{ckIbe;b^8$v;H'
    'xc0M->w6jrE}hX3RhHQF>cvL-nM*e3uWZ=Gu`n3wIqEmZn<1ST{tOX!u($Lg5pn^Gi88-WY+tIP()}Caq-#pwb{}BDs1!*kI8_^~nl&<z'
    'x!R!McfNDaTOb6jF@I~Z5oFL%HDBTR#KtPp8`mvGc?9^cEMrK?rWHe%v1ZS%_LO!0KS`Mxwb@Fb8G-S(Yy8WYn|^NV?_5{0s-Oey!A_h;'
    'FpmHuM=6Dw-0Z7DI2PX3zGAd1me=c^NVdYg80`WBv63GD9RIvD_3^)=YHAp8&1nfxDfVWeV`+f}L5#|yHgch%F;8~vfz9SK@EOUJ4>p~8'
    'Y(Y7$HD7bFA@z!_twpx>OQ|j2SY9$|s$V7vQ&(Z8<g{px-H}HMs4nhM7ko}MO)aJP5lW@7W1zhvu5>NCHtcT0ou6lE<!K`@EWp(lC~2j`'
    'b2XCBPI3!5nEvtEJiqQJ^L_Hq9uhwf5Qe)mqz6lhzfpS`!9>OBdrL*igi4o#n==$Nj-!~U<wH2W;kDUMu<@0w^@FD0A#B`>dSD|=KQgw1'
    'F!1M`K43FdeqgLd6ZcvhRQI%R(Kb8~H0R-DXu%jG!d0|z=nYF(4<`(z!Pw=SPDVyAKPapf+6&dcM(mDwG&2fL7tboyWR^3UVz}XdY3UHK'
    'YC;{+yEbg*rZeK~!RBb?2NF4=$2*U+^-5zn;WPP~VY<G+h!p;v(-<%p>u_q&iSkpN-LP*TJ0DwEs%ZUc!CJPv5b-8LTT$47*0y6P+^EVd'
    'xc%5X)(U>2<<X{%`Q7Igs1u>U+|}-2a(rt*k@MhvuqyudpCQxB*FR9LrW$dK*K$_5qy?1AsIF+O6)hRu)=21Xz~#wID2qaUdfOf5)V0;F'
    'beXqwUzGavG_~qRFDL)Hu$Tj{CL>LelP0`aCT?d=2Zvc<y7>kCjRWaEJH*BXDJ;CQNi9$m>?*a80fVSkN4$=8K4aJb#}5kAyU)DSAj{8l'
    'k&rxUk}#@H!Z~}P%KEpTCq=r>iz^oJPjiDLX4O-}&p9qOCOo=6@POBa>n7^dZvOl1uUAQV*!qbLqq;{!F4PT37OG{X;N{w0>&Kz?N2q16'
    'YjvIP{(;_(7Ipc#MndKbrN0I7)RhE4g?ji2)pL|EkL^w0TE%a|th`96V2C4)-i3xjbhG5AFw-;KvfmrB!hz)*Q&7M3B)h~zGb3WDUlNHg'
    '#nldl=g(Y@i8UQ(|2!Hr;ScDh&Oc5RE23KM74;W8lYnaD(+j`hYV+fA5(|lL?P52p4Mnc#K;C<K?>U2q1IAC^|DZ~1UIR8V?41;LAJpHl'
    'FdROW8Cpu@myo(x!0k%3ODFd_)JevKvyyU?_P1a-e!FYM414Uhx~#T%_8P@Tp=I9zVTu*GjttyS+8)KV;SR=lr*Z!o7C;8$R`&~7PCHc`'
    'W~Xrk-LBnjWl-7;!gu<bPxO%7?Qlizp{X9=$P0QZec@3=nmf$jXy~!awp^Q`>kH}3S{k%rT&!|o)m|gH8<D~bmfB}k+h4%&=cn;Wt6ea9'
    '!Q#spA_@80Mhw!{%DOg575_vQ==9GkkqN%^$$ia)O0zGVWn}Zq)>c)RBiQE|*w@A>`xKO)2@K${%=zUgiYfBzvi;j@a#k%f;|cI|=x!WG'
    'd~TsJS-&cVv+1W_F)vR$3T*AM-G2?nlv_~sQC1>cG%GPGvzlZ|jvBzkO#@25v^uAsAaY5=wy(XWeHn#j(LKmL@FNYp9%_-zthq@DYkHa>'
    '_Jx;Dl7p}N7>2iYIxip~179++hKO8i@DxsUAnw_uXel)SB81^545n%Qzv?gp%5``6nD+gxm9FMVE-3v@<z3XKa8W5ZsM*X9<+YnkS!)i('
    '(svygWyc(+Dh9B6Ij9ob^mGgVxjg5Xg}|JVtt?KG&m}zwv8*hzwXq}-;eTE`+h@VsTqaDLz<w;<*W2{S6-IU7VV3bm@V)XgFGI}W=Cn>G'
    ';|~kw`ULN)^{}C0DgdU9e@q~yE7XmIcyb@#@N^m^rZPzV4fo1I!yt$FEnt8j{Fn+WzlDpvdy1MZWpOQTFc(@Qkz^e`yvT~gy#x;KQJ`#y'
    'U{7S`?9nnt_hf<!wH`4ihL*64hjVrgxpf4?5z%M6f9;$|!Y4X~p}@~0ot@A_)HjBnykSIHOGPLc?osWj`YPNOrbV~A%?@T5krSl$gxc?r'
    '>e@vJ8o#~;BRuU?BI1r8tj-Ja`s;K(!w4DmJ|(=RTx?m;s^EK(QT>(0F9pu|oEMs)HYI5zX12SXqWq_X`g#gAqkPDn^)4pEf~)45<)um@'
    'O7nsi38%Ax7rqTbY&BkzGB#uAL`S<l``oH4!gT-e`OM%*V*#o@-bsz?pQhH+gWfcrL80FtsOsb<`dKt#z)nVyAHQ}CO!@xSvfN*o@ie)p'
    'Wvvg?3CBt{VvzqbF2)bqCcy+yw7`v)tVKE-?pDKI0*7U1qRXC-@`<kPN<!z=i00DADB$%{o}7;2AahxB5jmCO+$<Kj-K6lK-{Wav_;I#m'
    'm9mpug*J;(p#%s)_x>vyj$bUTIkeB9LzmaeoXR>Qa+GTe$?3GYpa-yBQ-3O4MWeLGI97LHwldYJ#nLiQ<vfBHjZmsy0CcX5Ino)zk+g9q'
    'mfuA#>g{tkUK2uONHdS${-I_o42+sb^LZ!}u^)lyN4LjV-;jDmDRP07&Xr=zLIGe<jEL-~R;ffGRmb*yzy8V5U8m~g^vG2Yys;+&Hs-3y'
    '@7|$Bj$`p$|57a;qk)pAgEWC<aTO)|#|*ufRksJpx{!puF4^)|#_kSK)&qouq!NOv!6oPpfU#Bqns7qYNW8qv_!=2KWOK)`poC@8ANIU^'
    'mzE<=BI+C$$Wph{oac0UoQg!AJiNBGu>Ku>y?%<5_<Oxo40;pz#b7$~Lk3&L$Aq?fiHe4b89K;eNhs1%35^uGm7i))i1Q0`sM1V8EvahJ'
    '9t`*8n2u;3^Ufhz*`kXwlW%HoFt3l_T~rIejfANtD)qUk|F;Qrf&|@x(SLT>D>0~~QzFfP&#^T;=snHyO>r#w%=^aPGKVJ;#g5V*^&vv`'
    'F{%|5uLY6ZmEi`e6|Yvgj%;PC)={>Q?xMh_)MELQl-PJ&75qf4z4O>yz>K`8{(kuTHy4}hiaAGjW=w%d{P|<zt>=Fy6O;Sf%bD!3yA`@|'
    'zTHdhaV{D;Ks+TW0yJ6bu`EgH#fuS;68%x7S<ZiQ-3coGY9UpbAfQ+xxx3?+1{?fD2Edb9<5;RXT+N>*N}H$_=Eu+5#aKxs-)Ozh(Q`0L'
    '{q)+_8Nn;7TrYzND=ny<YN^e{jf%>py}_HmBoxDcyp6ox`UgFf+{bNVtYr6*00pUmpS(Y%CVX*s?0z+A^3UR)IgILe?N>WZ`S`@34taeA'
    'W<v<mb9Y@o1&tpi6-7VM3w2BftNwsf5-GXLk|}>Z!&{p@v20tKz~uH^)4!DOp$u!@+?CqcF7lZYJF|H)qZOptPHrP(@C$?$#b{Ji_s<$b'
    'TUw<P-BVkt*|y%(nT=h=>3D_SvnZl*G|-@8{<XQ?&+g_qN)bNqNK$%Y**c{p)o7*pdy6%wiH1k^#|H6qb!>4B6&8~O-!s3PbJF*#jf1iT'
    'k;sD3YIxYzVf&<pC;|RfNw9QA2n&F5qZaru=~W{1gfq0eK?`jL-vb3lQX5~X2y@WVYM^15kpUhxtCC(UB~hQW-Yq>|{-`+~pmDwlE{RiK'
    '(_EOyNAu5qC>a!r<#Ba;tgUclr0d7NJ|6F;brlJ|E9Ukc3eFT|rvdA==OTLlGmoD<&QmEf!Z2{>;7ST<C%VL=dLy`^rFd7EgOW|1raQUv'
    'MZ?%|Op@VDF6IqdONP*W&2RfS=*AY$4!jn;Km^aISC$#kkH8D^GRxHIDHs@^ghK|q-5;in<NqT;x;>wlV(|h&&;g<(Y->|G%%6E$i+c@v'
    '9@~|JU5k^!h0mY4rs5}$`-CVkUs8H)g`K<g4WOGn-DPX_E^H>O%IPPbGi!#43GY7szA{I;oOWkoBrFk|1Dp1XhgP=tRzZ?-&IfNHXEK9N'
    'Grl{LJJrEj7*c1mPln;wGDj%^rSY6ua|1)o1d8y@Rf$!vWPld84tiYkcBQad9`Gsi+m7i;N$I<AU^ZKrM~RPqNq!%CH~a@#-*$>M+v(-f'
    'TwdFO5+W!C7i;ZidFROD4MAjY*`Ge0pzM%Xal^`sB|jM48N8DViKxB+P_V+b9+%tR{$U=Gz;pozDFZD~tbB1@VR4M^2M@cAm1v8a{_EM='
    'sW4y-s_S4_8Vu}jGbmKY($x+J{-43*s%t{tA?~|bYwTW^4_31S6}7=6yg?;Rl4+$k@~*FKiachW{E+%nk7E+<9pXi=QA;0`fDrw2LVDJd'
    'Ufn2SR2tfM9qi7j9pUTJuO?N?T`RP6{dq3~45=(*^@=DN1f)7E_DVZ=M;b-&iuqK;{1tZZ2%#hvVbAQRmlpAIEiDy!m6$<YzFe<{bdoiv'
    'G0wR1<xe&OohlO0(V*jASl|0ta>TNLWW#Qj1h67^c@oWsz@~#>;t;9T>3ZX`Ay+rs7PDOscj1x^^8}r}nw6N*?5j>tU&i?RHtG=$=~k)*'
    '^pcGmw8Y=PdoBmRQ4D!rS5twa5`hAOzMO%H2iG_X^>ZDR)sh!9*CtNsx7llUeNOYJY(L5r+M<wWV=oHc*}OzkB4QP`{g$(Xf9Sgd@PuPn'
    'lO3yJ9oAVMa_1y*2qtZD$6)h!HfQd8IGrVaX2yva+ZWBIFdreXMGGahN`9w*IqWJXyVkuKT~^=cJbd4*3nB^crTh`tu7b<dH5la_MVmA$'
    '3L9Myfbaw4%)pPL|8x*uvvz;|g>p~J>jjZ^AMjIE+*!MkjDEQDTy&5XgC%$+QA53rlyjHM@uv}<Y$9$yf}LfRX1F1?B@rP34G9x^Dv#@>'
    '-5-~>-)JvE<Eg4mp0AHOeYlOy0^Yh0QY=maCrlxOR80!RHLdd`m0TY8ktmcA|AwR^vUpU0ci#cdwst7C%X0xWQb0N(%}R{dR>Nes_vVTz'
    'WpKq+4}1J!^Acy_oDhP)Ou_Bkh&BE0BqA{s&krRhEt3G$e<lenUImST1<lGOg~k^sL}C_B{71z7CXqe)5Fg!H>u4dE^yM#o`rfanr0^1G'
    '<nO05(=!;S<SFym&Jb!9Y$SvVdlO}<dOYJI3d*5s*GKhNKX~c6{cV1^^ub+Sd3r4l4R!-=#_qzH(JEu23`$|@W1-ROG}Jc?zdbkEc~euL'
    'xobV(fN$$}0oFr5opE8IF&$?}#*4{+)1V)HUAV`1ZKkiESjonFqGM;a3ENAF=qWy#2B|GuVIjS4UQjcG_#Xel0jr|g`}ow_nn6jM&|{!G'
    '5s@(ao+lDgQ#vBC7-CjjXitfF8jXnrcl=EU(Y6lMy+oC(1mEukOKyoeGGy}P4H=%Y9zF$QpfOr%M#9q6*@<CueJJM+?%abbY;)P2Uz(ip'
    'g4>MU!0;QT`yQj#gdDdgly07cVeRfy#(}L0B{YAdZsV_t+ERfJMX`O|6k7xS;m#ljGTif+Wegne^t_SW5j94pU^qix2cs1cCn}DNXiZ_1'
    'w{bVmOGI;mr2T+b2tf_P0af}`t%#Z1`(-11v_s2eJKZO`(_W1NIGPmZO(?rX6(ZW%ZrVRjl0XFJjl-~pvINe0!zk}@Hcad;>S)(iwok3g'
    'Du+s(BY`?j<mu(H%ps4Imjzv>xXRC;lDgCsT@Eo5^XStE@u80KClP62J8on?RKOpXfwp0g$W<g!_-YcXOB+C)p9Jlr(KLeas%+bzu&C<z'
    'vDO^lfq2ESh*~Dxxkhpis_d8VQBeruWgho3UZ#CN*6K)QLe=1#c}y4}q$8#mOTq(Z@u>y2V`4rC2kk@6{U+Uync!+w!>#A5^xwRoyFAmz'
    'OuWn-libcayDn<W10GO)rS<AdZfY%3J$pmWaCYi#59?bTZw%m-R{M9v+LwL*Db--&J(lEK4Uc`E^%g$%&g+|;2Er7;qoifCN?<=NFEPo`'
    'I>cm3W99=jee3iHxm3RmaU!boi{>I|Q6aR+Zdu0+%U=!0kum#xI-C#kv=h=A|KK=o&un_^@XeUPxI|d=#Oa4Q{1|9Q@d`-$Y~*>T8Xt{n'
    '8%<%#^e<8WkrBdu9?j-<2SyPo(Cu`>_H#LXX@pzg(=S~|*r{$d*rnsZP}?;NTx5RD+Q?bZtOq03(aWzol>7JJc)}w3%$aPm(_#Nq;sLKk'
    '@Ob4t`xZ?wfw)O!&L*0%?vT*y+T3MW!crM{dOJbRlLy+0j$Fp8mSG5=GW^|BXXhdd=-$+_>kG&{MMkcF^x8hQ&zqo#HY44|H>g3cwsfqu'
    '`^1CgJUel8iV%w*;#8G5PiT%g5iaLGfM3#K9U}SAJ-#Id_xXQ%Ud2A^i4$pLcdVCAjK^5z)JoN<P7WjD+1c)c6kt#$>d}ebF&x_klA!55'
    '@jn9cbsG;~P|%UT8688Y<W&7Zdzl=MJuU6#;zn>J?4z56wAL|Pt4F$ywC5ENnvmrFY<3V=5Ig-@&_9~adjj@s%OAZs-6sblqt<W#w9Cr{'
    '4pOcjXd^E2(^>I9^UrasKr1S+e27?2sLiil3J3u&7KvWBo9butG5<XMT8;zGPM1!c9qd#)s@hPnH~d7<>y9yy{_lsIP2_)1nL+a5`rWsh'
    '+`fGG(qqrk$YGc2ZN2n-YQl((&UsR`b{{tFfIgN&2@f;Mo0;(oiOs9@iG`#@-6r7CN-GJIl9@C0RwM6%`}u9^;^xs!9nVv7x4NpiEXy%u'
    'DKsI*f+2E8q5ajz{jHh5KveZ)N^*`uNYX6~L8`K32x`H>HAUd?KBvi-G7!ixFQd64y@d5b20o?w)2c)5*3!@$b5b2QOh!P|W23e2A~k9K'
    ';fD)|b$@XI;FZtUsFdQ?&nlVtwBJ(c1Vio^rCI%sx=Y)I+Pt+?shf?sieLNdND*Le^kHl4sFo)AB4VWgD2~YRc4P^(0Q5WDL?=Ok|Cs4M'
    'y(#z9iaFgOwD2dBq5r#<W=yqyF>`PxyOs<8+@e28#O|_ymxp3Dt6+75yTwDPxttAXwa0D0{*`JybF~Wj3EHSB?eI~&ke9Uc3%0*uQyP;|'
    '%Vi#X5z9?Xf0Ga&m0l9CtF3AD&bHv@Udb67@4t-ma$MQMZ9A}E&?A2B^N(>w;SOM1z8?V@%=nIwS(6W5kfN%d&zjLCdX~yGu?EGfpG%-)'
    'g)u(mT+MPsM&M=-6Cw}Qibo$N<ej=BC3s|84ZvKIcS4oT@@Aa`So<(0)iADnQE{!IyM=#W{QX^tC=Iw%5%3T?`bTnJ>o8Cn)}BXb_{rjJ'
    '(ciq+u(_Pb%Qqn0ug$2ATL248yG$LR`*0;O@cVNQu}G3|#m2a30ig6NWSE7JeW-`?wHke(lj4iT*8Xer4WsEYmGLZytOuU2%>5<EOrW-V'
    'd;ck|)GZl<3Y)vw8hK+Ub%$XN_2J)*oF+Rsdgw}$<UUrt((b$uZoC!ALSM}51Yw`OCx0M~h~?m+7{)G14aLwTtm#Dwc7s$i(QwvH{3R!G'
    '5mW$kax{95+Uy-NY~ry!l$UW6C5gppANl^^yMTelui~wp`b<p4>s(t$T|a1RBm~(MunVc-!(=HD{Jz=NoR}fEjTL4acwMGj;py6&m|y%e'
    '?UcjFBZaK!eT&&1kG-fZIK-=1%T^_6P=v7;TDAy~ims#`RxLq0p$dJbUh1|JA}#vPc%pcPLHuM?^<=DA8=eIukem=v&d{r_%Q~HYlXv?>'
    'zj*n*s>!X3)xf>_opULZ%u+|CzwOl|5Ukycp1XO^e0F5Qo}5-b)X=F)qKD%2r4hJwJFLsS<4w*Zy^qkHM<#{b2TF@t#Qk?ST2C}S5?0iR'
    'i%{q!gHQGFDvTm)Qo$Bvr}E&2WJ<%?y@<8Wwf>Zm!)o47af9|eBWy8sD4;<Jy@4iC?fztDC9H899XO7E;)VVWeqhz_T!le>bBI4~bK^&r'
    'Lcr#YkXdlLV}hXJQg3DP^AE+TUxT*b(0-iMj{Fl#x{gyu{J^&q739O%yploCc&2S7FW-ar=4HQ_V%sgn{h2IlW#b*CKI!TEv4VGA5506-'
    'nMS|IiIf=<5LZ-=Wcav>3rxx7Rw)~m*w<4Ig%EejsnUm3*eTARYM1OPeml=j$HuR2Fa}bCa9H3kJO$*R_#dNmva<=rD&fp=a2h|3I5V7b'
    'ss>WY8lJ`j?z4yuN~~v(*?fvc7(7&yHpU4Baxor7$oqpJOW(q{;d7pSSLl#&kWMuWOR)=6@OH9w0!F~3xdYdaKB|Ew(q$^AB^fL(hucTy'
    'mgPd~@HSZ7cOKsvn$o{b!LY|YHmvwb>E{EQ?FTCIDnyiF1Zv>zozp87upHnYV$TYGTKcf*`H|S*+|F}(ECkCR!l<3wmDyiTw7>NtQO{{$'
    'a4A$kJKa6E+@;zSV2?;TsxxCUx@N6Tn?)0B%&fHwiNLG3^?O>tx`J)~q8hvUCVaAZ{tdGj0>@H`o{zdOVtN?~WQqSLu=z?-os<k~1og$%'
    'fv}9)n(<sPXs;6B>>W_Vz9%duCgfN&;+J5NU2k$V6)2aPzH<ZTPO$r;eWj$UDm#7}RvOapg#3&@13lc`9H+45fTr<BRh7X$Rv?})n+{p6'
    'SE-CgM6(2@@HB{({x2>R^bT?>o1(&9V<(M&^CT6LUiF)6MRCJ|GLFO?QfU?7a`#WFaU)+Ez~sn1nQGDD9yCc@WSjU<v?6rY*)r742LrIb'
    '`O7fCL8)S1;iZ1n5X6WXp8VSM5aD2>SX&H9$>_9q%jnSAgs#gC)wqRJP3UJVS8AXNRUYfk;nzY{oY-X9evU8tgNb~hlDSock!+~|5WdgO'
    'A|IRr)|H6ac)4aw7URTaX2AQ~t)bVs+^<%>AyZphS|PQ?f1_!lQ)+4t9SI>v*(|;mgP$sMiz(7yUH{el8jJSK)gbv@^lib|9#!i?=V{VW'
    'i%2UTG}Ui0IA*X`bx%Dng3vh|-B{G`y-7=zmc@8~;=cOmAmEmGYtnY<VazTHCB97EFJl*kg!t{a6zj5d{4zmbI*~Ww>t3GTeg?NW{RSVn'
    'O=Y*xE=><BOvDax`Pk$ro0By`n$imc1nq(11Ucga`}yF-%bMfUd8t|sF&uXm>3!B8AJE9TuEzU(KdZI4K<6cfe;ehbrtb0W6a-QCQGf-u'
    'Z1oF4Lwy77{*SLnQ_FkQ5LtuK<EpE<+~cJz`!iXPy?rBeoh(DRI;ts+AQ;?x(~o%ZNBV`NUOqA3lFkThm~&zINxH2brH$*Xe%TE_CHI^8'
    '^E^Chj)oZi$u?FR9R$)gUAGiBgfTlkNYf=kUF<_huvZURA|bH42+xR~4pfENTW-T|W83i$qkWB`(Hzqo@mfqWNYuKE1dRCnU^5RJeN$HR'
    'Gaw#|>tS~{DP7px4-1^<NAXu*fyK=o?2-&1@xiXm2JcSLI8W(R2iWCHo?D8rq4gq-k!fqar1*qfSFVH059}{1g)C#B!F@VwrFWj#t8y2('
    '*bZC@OzG8(qir4wj>3$D*ZF~V+{B8RX77GLYalC{<<hjoXC-)uY#31~!Euf9FPe)!IJ+6Ij4eVES=<52&vz-jt9;emkLWly;qzD!?sN{F'
    'IJw(nA@;tP3=-AW?gLc=TV*@XE>(*<IR`psf@1Hytc077`&9ydr~n}l<M0RG0-1!I+xBb-6H8;D>SoIM>B&+n8W=fQcO|IHgFL7b6ZJcG'
    '$uZzXk5h2djjU&#>S|0^?wuZ`${4y0aY_h6T>>ezIn7Nfhwf8CaxOc=D%Qm1+YGjDT0&AR8=IgNti}pQ#+pUz%j1tywBRV=51$(HG04O8'
    'yWwshEZdPJ&QmQB#7f=tSFC7;12EGlpxlMpZrZU?A40e)fnqOBUx^YUzoa?%A1qj;ZOaMVYR?Cq*_;QAG8}6QmGYul#SJFTeUh;}<Uq3A'
    '#D=@T5KcAI0LQ~2SZD7_y4mNFz*E{}8!NNts6!GCZE<PG>z*n^@5V{JI28+el9kcBc3Ml3#)Cw)SqTNM5g?*e{XrJPTvU8eAKXBNKCZ<-'
    'j#-~l5V_oq1Ilf!Z7w#`yWs*Nwi?7gC}qF8PnHIUe=@T7K%8J$$LORX&j44VmCc9@jRI(yM1L=KzOgtK{Xt(Lrdb^eDQpOI@&Y@?^GuFc'
    '!V?@fu2^9PHyXw-Ubu0yk=L`DTk*jx1xnv3hxKpODjSSZYAJi1uc^WCuDu2rG73=?RaTHc&l}r`rn;y<v9)?;`C?+4#rLa!(2#dP+QZC>'
    '7klXCudJR75!eLcOU@<5ph@C$Yi$F`4QL-)?gE~ZueX-(Fgdj0Uz>d!WhM`A2ux&~g`}4pC~xW&hh>j=M($Iw-vu$-9Lp_Od8#;e2b1f@'
    'x!7|eay6Y1WLkzpjq-VP+yPWo*F;0x+)Q}SDCwgGM$;cE*Q~I@%IfLYd8X`_Ds-QRSY$zgFlrcdhZ=n3ZjPUNF!hMh;nKTjj9Me|FGRS_'
    'P6SJ1+T?=<(w#tfu=9t_R>DV@3t9Ooqwf{*E4fnn;z7i*?Q<)V5TTbpVoq2}buYV6aOaO(k+<aFbN1=N9s(saOS|01!y=#7NYeK&%G1Ie'
    'g(mMNt<#yx^XK0Py&McKx&XxVY4g*10X4=S<YVB7od*XL)@|S42tf6LdY?8j_nNgf;}DWSiIN_d#`~@;ShA3xTH9<zYpFt4O0W41VIwZt'
    'dVC>S(#%YvI2vz!P{~qe2FCNYj)z(#c!q!0whO1}y(YNelN4ANA9A{KFp-t+Ye-C*t*I`)a1fVITmrH=%uX<z6~eDo)8&HfYjeh$UcTTy'
    'aCBt9EPCmQS)HCc#Yw?1rPmI>MSZ;{i`foXDDczQePml@A8k?ZU&mWv4cS+95wDPSs}IX<)9UYI)JlAYhiMytmEnZHMa9N5>OYd+aj#fN'
    '$o^4@unbl)HeESCh{`DN<K$an3|^WxANVLZRsIS+Xzj9|V8tQ!d&1qU6lU3YT0deOE{^IXjXrCKlFsz2%lTntPAGUR#UsIW{p)X5Dnc1j'
    'c5StYngV>A^E3HB+Y#p!-JwB><?5=bmNlOQIi=DawF6!UmIZ>~_<172<D62dO*g4HwJb&TsQqS~(X+d5D{U`5qH-t`C&LQ>YOGeL8)QvL'
    'yx-T0{W6#6)$9{51vC&cU-nvpfkNC>aS<yfZQ5Cpb-`;0>K3(Wo|4LUglWu1rpP#dg~p4B)_U_{RD81dK`DLeWB}o?n-V-lkwXl9Vtm!Q'
    'W{_vQNuNK3m+_Dc`4T-+Gy@;1WAjdVtI%OKp9+1XPh|<xt^^2M$I)%5%xmO0#jin8qV<rI2D<hnM}z>lvCq)|GOw8MxWb-=H&0ToO2|R1'
    'zVZx)mH)J%5v$A7cjV!MX;18KG3#+QpLLtzCXRum7v85GezmXItu-P(c_Fk_VCmq=R_8}=C`S&ovpJ%|^P+}T$(}_L@&wuF&atDmnYn4c'
    'YNOOyu4U~@IX)LD*T>ExL>V@f1oT0>^=J}c-(EVyx_2Tt#h;CHOe+N{MMWj+_tzA6&M1i(w|V8{%}t|BAFNWsKN7Hfj(_TqeaDHYGa}K;'
    'AOo#nY>_&Yj~<_Wkku5xh`<`VHAv6ry{fuTPuM4f;L$jKSC4dqy|Ye~<lnFT33R77Cts~nYH;1&c9hA`vU;e)QWu5eXLdOYDcn19sz`up'
    'Ep~Zv*Ya;O^<0yoQSf2hw6QTZ&b;ff=h2F1wt<<fe%S`=h!FqFW~;gbFT!L>q!`t~>eb!n_4m96x>Ji7`(Ag_vz4tN9J!FFlb-0d!iyt5'
    'u=B0gk{C))h9WOmqdWV+>K?MLG<jk+Mu|F3UBJGro=b}`0|!sjnu|rL;+}&iSR`m;niM9uS4mse0(<hTr6qrQZ{7)b*CpTDa$|r+;v#O3'
    't7AgR&h+0#;zy$9t(r;F`jrac-!%2;zde&uydr-wf_SX6uc{6oGtnKM0Ai?$Z=M~U`@Mc8rVxLkUA@P0gW;8?@E5=;8*%VO(VEps+>O2}'
    '2u=;t0z=r6ig($jD{K9hfZN2^3^Zp>a%Ti2FJJZiN0UyUquaAkoE$b$KgW5EF75DjTknMgu>`u{J1a%vaJEBrPMjfMv^zxtXtV(*5unmD'
    'qzu>ZEcTaDm<HqGs!8($FKOM|R!djyg}(@foXiT~M`_15W~ft0^T#cFQ`{uT|8P)4WC*AF*LUq^`Zyo6`b}JKvJv3?7lYt4t;lUI^?-Bs'
    'JAi!jVAK?=VtQAik($Ie^l(|(+)?($#IK`woFzXS3vdCBf9_5Sq=CfQ2Y8Bup-FV+hr5??Poa~eUyJWHolSyaxuHKAp*Dt@KnuRVOXO&8'
    'MuaA%&;#%&neXBTr!CY)B9#=FMlZR_lOI!@=6^RCX6M9eh+eo)jD~6(h*S^44M&=+T);%(RmIlI-v&=%43+jGIigjRLvi=q9aMVHmhzyh'
    'K!N|Zhk%^+k3DE4=Mbjyl0^`m7zv<$OWq=54;`=2kM(=$ejvaaLMI#1{qc4LuW_zBV^t{SFYNM+a6Yq7ibldCl8GMDl_(unwzBnbz^3Y('
    'HTOH;Vil#Ii5*9fkFMT(E#W&x1MH01C{duk^U)E4s=s<}vk7-fwrMoeY_;->0a@qFC{vEKB4*YBB2C5laJb!}EXdVg@@R~a!E#W3k#}(m'
    'OPPnvO+QAWS8!?pg5K2aFq$oY9jr0sqDAN{NlEGVx<~w8og7X-yx6}^nLh^D?kJ4!ThKTTmzR7qTll-b|IOARw|-^_UNXSu(fX+3ZK()C'
    'Wm8*0i=O^sZw&ia`tPU<e5S?9%3mgWPwVBcgR<Qe-SyUQCrP-JFZkjtYMC%B7Z~1RJJen47cXg9J<jxa*>N-0$-m<5&WC5d{Cp#0imGLE'
    '!y$T^>>4RHC>O+Kw(Eyw?Sm{sOA_NI*zTK;W9LD+F4j=TFe1MPrGlpVPT4i^k`zvwmhJc+h%7&(q#$333Ky=zZn*gi8&eX%5^>ZAyw#_('
    'Q=kcuK7&V&`iE9<rX1I}fg2Xv>Qx8o-esH<4I#6TdXObj+_QEN@As3M=rLL1Ucnkj__S;9uA}=qu`6eFIOAZ{82()a1I_R(8vmp&Sstm='
    'kD!rvr#IA0n>0Px7p;R%@D67@`5q-Y35CkTSd7UYazKwu)TwZRJ=ckTpLLcu*%oj*)NU3*3!RWa!_<5BtF&pFGL=#>V*)P2ZCtAagf;S('
    'P)Q1y*Syw=xS?>IJdRPDUuFwquuK4l=Q4Zg9<z^ZMy5w^|Cw9AKXv=N127_*SoSpCC#aBox&$#Ks{)rAs7g^iuRgkIPx=9rzuXpHov#Az'
    'UE1kc=pZp-6(Q&9akKHz(m->mEXL`oaH4k8`eECS$Hl#(j^7=rs8HtwWwvvCE-C)(SI!rVnhI7Z`*f#uB)_0_HmuK8mOEw6HRez=$?cfT'
    ')@HDCKH^9iqfD+)5V|OuSe>KG_vj6arwj<@bw@~73YY|th+%|%qVOA;!O6MSDH6`{I3+}uoYE{Rj6UY%Npyr!L>-gg_#=1%<)8_U$UW7K'
    'ZqUHRdzV_S9IOfO5yL%kTYj#DN<y<6ILJ2gO1CA}E?iyk5XV^{7Z-~QLa*1iXN)p<oCz==krN+^V=2x3m*qj3UBqQHa>@bf<|7A`GI$$E'
    '_|!~}B*eXQ>}Chkh~0UAUT|``wrS?O4fF8QN*y3fm9*dB4rslc%A*grtRjs`8{)(hDMH7Ug(cW3<_Z30`<#^r(*E-z_tiXYXfvpi4vB;A'
    'rp#PKqCrn#!)SB8M29|NIalWq<LZ{CO=$PonJ9iTd2H~S`B)$P9T-jsgVXMN!=i#8J?ib-VZmDdum<$A_Z;nt8vXr<$ZzN<I>Qja6NB>;'
    'jzfW4+R}M~zR+1N#U)bT@dlU<ao@@J>pEb*qo08i*|{4_mB)QB%O(w?QW(OJLlJ8jd)s8Rn&rdat-)^UjN!O*;{$yrcNiWgKzZtn(9;+D'
    'B+KP>?GPGMS6*I5Eqk?7XIdnGXTG|nC^_{pZDx3wP_Ca7nTr><!kBW1D5g{V?{DD|p0{PI=ZfKS=VU$`(c(v{DEacRU~BL?e0(b*7J6|U'
    '8d*QBf-~$9+R-ft#=qg_Zh?Z|vG;k_oZ<|ke4v?ycIWdh7N!sM_SMIJW6LgLud#pat9%aq{SGf&hEN0wbA5bFW)zl4h%hhJX#4ys!#+(M'
    'Lw@-Ix$%rP<H!8ex%pppq!zjkanp-mS&Psiy`Sz|!+a}%`ARXZwamZcDC^^aIc=sAt{_+q?G_Rf-Reh0Pmz)}MBcbM#PRb9c7LoQc6=a6'
    'H0B84P7NTwT*>uwk7(r7AleYIk${&V3Ii?>454jgTAS`VoiH=jg3AY3@ekrdyjFBn7Fgojn9W66i?HZ3DwNJYuQ(<GxW!VG>;X)d7=Z;~'
    'U@HF)ptYseJ@U#02KGND{r>?iXA?I!8&8Y>pV7MezZk8f|6#O-{tu&t^}iV{oUH2#Qb?#4FtbH2P~N5f@pk_`@DuhLFb#rz{<(GA9;o>}'
    '0UG{1)f;8{zFcS??-v6}eeD7hKJ!8U$qlgdp7;3(g8gW}&7X(8>pvzr1+{}}L95?Z2h~frK#>o_0ze%g5LEl^_1zD0%DH{st=%~X3;|-k'
    'ie4eVTfbRAURAdZfE%j@ktd@^qjw<}fHUaCKL?}&viYz9Q5-41^Sl~;3lEUI2#JcEyXXL#zbh|66M+72eUSYP_~Tqh{-)5B8*sz0LWJnU'
    '>fPuXa3FF8h<Hc*It>tR=oRfJ{TBN+`)I%JKk*`T2LF6~Z+|zs&F=&qd<%VOoWstNbiiKTeu~WG>pQ`a=)XXGhkqk}!@ed=?3S^d1D*hd'
    'AeRro_2m=b5%erF3i$H|_igYM`UQGLeaLS%66gngjeS3T&;||yfMThaR~L(uxq$)ws@GgwH$K5>B=^fJj4k%e(w6;wC#}K*&kW+5Yfl+)'
    '$+1^hFgaoyM-q4E_Dco3<#QOhkqn6R4fP*i5O>nBUv5sqA>WO05cG57(!Ns{`H=zQ3VjcaC0QF~biH~`Rr2#Q84o;tm9?F<+cWjwczo=^'
    '0UM=S8$1c0VisiSZBC<ykh`ux_4~=zh}J|f7lQM&6(?x9;5rztZ}~2dEXdbMIOoTNd`O@%+EXT_=O;IHLV(?7En|!M#C5}&tt~41V<B3C'
    'kITM_76EKK#V5}!1G<&7h|Da<pBOphbSGNG2<oPk!_l2aofdNZ0}A%4dmyq`w9TYFh>bc=72bpLW&!+uUV0iBBHf-sYg93mQlI<tFp*qs'
    '#>r#wbHBEuy~cWsA=%#X7jgC7-!|x~G_Zo1`igke#J;~ttQwJt%VVaPS8|WsBVCMr+4C`Z)aqYewx+%`V>#w=|L%!^t%{P)!SSlYB(7$D'
    'A;NGekw(-6jgICx<4AtrOB9lduGzL#=$?nTug1`KSdl%eag?w(mrSlSt;*WLMUcs$re|j^$<-NLX>?8%I$OCC;EDv*_%vOZEjA#x58(~)'
    'J<n*DAG@SE0gqw)Ee)akY!>=jUvbUg+hOgTVJ$ON_R}eNeXUzC#;Bm2^&<0uVs=uL#?>+~8#qyWL>|CMN8M`=;eY$XczAOnc>U9fx$U4$'
    '9ruDy2{PcH<is0@Lzgz(pp)eBD_OmB;MMgo7uf;Avh0Jsusm~OhdQFXOjrEoFxKAO^H)?U=cEF}1Z?9cEMA_OnFk~NF2c4xQ>2?rQO`%Z'
    '>FL-BEwX4?wUjNh_NA!Ndqg#9U*-$34sTWXgk_?iQw!<3?<LZ*%F13qQ7-Z%xIodNr8PsS___*1A3s&AzBsmim&8)MVWhx>aRouPo)Ac>'
    'GWzSNV`g#Z{n8(RNS1j|ZIL-f$jPah{cE`9On1z*Ul#05bfDA;Cj93Li*D<WzO@X4q-EV-iG@h(*T++^a{6dL2<T77jEF8@Kub&8^h$s4'
    '^Hx{YpQ?tOJ*RlF=ZN1mtI4h7H{TDgSmX2}27`OQht{J!b(FYkc<0y4_XNz1VKVQLy5BP6cGzyo?+5_(>mqj={!wGUv%6&UH{y;d`Ni?_'
    '$y7JIT*>N-roFnd2czm6_|0Ic$0mBTy^8jtz~ai=2ZJHpv}g3L`KS0Lz`A`aFwkaxyD03#)RPj*ma_bg>`tgtKcI%UA~aYBdTskFU~FiM'
    'Q4=xP2+po@<z=Pfg92Lpqj&>=b?g3%M_?P+{y>E34wJ{ILc#h9pV%iz)Z6TLu^KmsXfT}Bn4H7sf8=1H%IPG;@wo1SkG*CWezUQYRk=st'
    '2)L=5(JY6LvZT-fO30q|d7FQui4Iv)Nj=q}Xp2Rw;F1;F0w}jaTL;!}L67noHi7A^x*3D2Y3g}AK@O{QqfzW<#`@XNe5O%FHs4vE$gsbO'
    'JVuN$t*UL2tGw3sR3DM6-B;$e1{1<3l*Hh+UyOqmjTV1HvwUhF63wOpwtu=h38h52qsZIG!^Y_@RfMi)SuzppGC=MsCUxtGf_;PTyz1a_'
    '#%p~_q7tv>l$`rUJ{P&Sr;SRmrDx2w51eG!;T*qO9dPzn@i$<OMi)&imR!^#`Z__}m=p^~xJ6$y(4zmK+q-ygmfu?i^+nqdtTe&s72=+m'
    'vCkTbP6E7LZW7`J;!b-Q^h|WR0sV7P?JwwWcK8{=Yo@A+vjZ$Icu@xlFI5{4=L<%>DnEo6g3yYD+A?)qW^Wa-S2zUP#Z&hn1Z00TCGYu?'
    'lrxwRA>r+i8%;h^-)5HxhKgwC*dzqpkX18Lgt3zU<a>NWZ<><n0QNpH!^iw+w_ZaHrvpGP%{a)eNa?4=g5a$xc3yDb2PfYLHBt{Lw9Vxp'
    'CYTl+Ux0byt@QAnb5;5RSGPGm`7aE@6?oyh6fGMUn4O;mv|zN}UlOSjgtgk{2F_2vcxeN74zjoJq4!Dk<ow*?>w0B|vAw(0DFb-b<>P0&'
    'EyKLRJLGOF1iU}0Ry0)~Kj)|6{BlkPwd8{nL!H#BJ7*`&?Nt!xZC1NeYq6sO@Nv3>F;)(L<CyX#g|Xz%scE+(CCbirLstJtm>bpWIt*Tv'
    '3YQ8=AO*{JP#LVIw6eKD;xDnQvl>*_+jDP1rP~Y5fy)H%vP5KfT^k??UC&qzU|q$T^}n{p8eN@qI13E3m?0ZjRZh1a9=awA`vXy&{0nGb'
    'PZ8OfFb7$n5PY%titVaL=)Fp3xBd7aC&m@Y^eyxJLLyFIuIfVM*T-{y#|E^*bq)`^`+RDF^^hlXJkgAbjwazuc{-0LL_<~Gq+jdh5&Qym'
    '0Gg~B2PNL>r}%_;zzWapw`%;^i{ZDE9~rhG@{b($ETHG~e&=1vq@WG2RiEk^nq8Dv-o-k@63-ag#x>4Ehp|8S@@S5t2#eC@NV{z24@Zq|'
    'jqt+J_D9b@<-*su)U1Yt^#sFF+U2i?mpD%!xs1?x2)Jn1U)$Gb^mQ<<n_YKG@4zQ5SC9ua?_qY9f4+8R$*~1)c=AZZ>%?!nw!b922di-@'
    'dk=l9u7CI3&Z|8UYzP-+M<F*cc3(p0|4_m`h~joQs)YPZlYcRFf?68DE-B21xS`m?iFN@#g$K{gcjJnATj>&_{IbTQB@wgj8VEXKz-4bO'
    'c`lRQB|_k*o5=oic590!R`sS<Zx%vGxH8bMOQ`!(4;`pSeC%N2^gekXzC%;=HoRk$eEK)>r{bvo8uX}GgA!=T*>Ug8`<0g|$})G%9P~|b'
    'Q?^5O;EYGs`*7WaO+r4P3z*Cr4d->Wd?*|;E5N5GnvwONPRT6#5ngLnHrsFx4@NstIchj=TyT{%f(at=+@5G=`;f-@nKL21J4dCn{^gm5'
    '4CD|;aUUC->|92k@$?mzkp|Bfh)v_g5TlsQOWi;3;o$PFh}Su@T_do=IK7o;TgbyrcVBSSYdqV9x4P2)$7~$JA+E?I(47i)*%J9mZW^=z'
    '@xRD=rx;%tAN+HyGq$ZWwr$(CZQHhO+qP|c&e-O6-`{Sso9zFhcfD%b=4sMTo~-Jrs|-~94G6u9zL+OMjgU`0sNUVde?el#M`t7ye(&y`'
    'x>dK>g?gZ>-MzM?6D;nPHqd%^q|kZ!t>GVg9`p=>8V>_oxh<6VU`Mz>cFvYyCaDWQ#*ja!9tZ6({Xykh%hFuBBUbH?%h(1!+-^d`9pTJI'
    'cQD#&_f-Y#(>|pL3#;^YxV3%@)XrUgr-QAz1+RBUupsU^BYQP*g|-WdLti&^qd|rUzUw=B8}Gq^Rm2RYO%r}L2pk22n)$zf%;Lp+{xRX4'
    '9*5PjjA}xRSLJw#?*wwSMd_V-p86k}z~k`s3aeUL>aZf>Hw)<?@A(QQt}lqNJEdtZ<dkfgsN=z+kZa1&yz|b@lZ<A!87S_uGtw}mmAK?B'
    '@p3uz>$h^=U^#^OyoA%ch8=xqoCFe2-n_d6G-_{(B?Q6g8h1}CWk=nH8A$V#VxV$v_n4zaE&ryf5RZ|hx2#g<08D#QKma?N`nb<WeZXXP'
    '>&g;xSq+P^z=QQ1gT>32TQ~Lf_@ThdnKaiT$zW7bL|@@tI+<4@3e?}&cIb*0Jk=vgY!gQ31VjLI;_N#w%!r7EVf=&TJW$l~a)kZpMq1Y}'
    'mHKt|ymC{Mi<E+q@~juaE_wInOCz4?@VjGV#E@_Zs;GY%u}<zqm!b8*PPFA3vh6%@2`rcTTQ;u3%RkB-|4qG&gqK`aj;Zph?SN3{I3Tw&'
    '<^=F_lF7H8d$9DofuIECQd8?(JoPNNkL4nLI2rO@WTpHIcDj~s6S=>c^8B;#N5_19o3Q_)8|W%A8AJJZjgpRGLi-cZxhRsE%1iMB?n4gj'
    'G+53JMb1%h+L7Z_NdIS%-yt_L)`y@N&a7WiZIk2t)Q>Q-)KEYM@^Z!4u4gZ?J8E_t9@ZF*UStjJj&Q_&__LkP-SL%P3-q`8uPTWFB1>z4'
    '%S7B5SU_^_U7X$c*~iA^JL>hIb5HuT^<;gK1lk88fns@zb{@&c;XbXo2cQiE+C&yA`lZ$xc$2s!9jf`n0?r~lhinoY43wgbgW>vIfYobI'
    '8AS?tvaexjwk*g)5F1P1P30n1isuS?b4*mWuS=audJh?<DmV<Jn7;uL#kBjuR^=+<zQ4b4X>fzs@h0TFG=t=wuq#xG7#htBy1g}{o0Z9}'
    '=lnT#s$zFn;??9=nxg!rzC#r#V0fXoL_Z-RO*p8@H1zVC@-MI$X*Z<kpli|x%rV0;W)KK5DFA*Os4juK0<vWfaWZ<FIHO1vhPpr&o4+$u'
    'pH(ZIO(>#EsyAeUy}@RjQj(BJ*D*+(!pEM2Ca{Z5)p#~~z<oM#rfyh)IdqAhakrp94*vY-n=s+z;WA<DF`On`-6JCEVF=rPSS8H;i#rT>'
    'rVBeWH(hb`adBlG+LI^pvEr@Z16pX!g7H0$3?i-rnM!)G#Z6`p*7Ey1Pu^h)m413|O_F5HWjLeJDur##WU9_7315TQ3iio;_liLZo7st{'
    'O9au!foLDi_2JKmRnuYgTzAwSS$y_$TOl(jwxT^NDt&D>b<!Tx@3pxDx57%_&Uh39?D3a}^DAv<{7y(9O8cuD@etoUH^Wii?KP3_IT$C-'
    'TaOy}#X&VD@|HKo8?OHL=f*aN(LxdM2-g9NUwNq7zCk~s`i)LbhN+@v#)n`nvZLirXLSQuDLxIt^gw}uE@G0F0wTZ;qm)x!yd?zeqkjoV'
    '!1Za$VlfPwOVIc$priP2y1dO@9$ef`wVY`0RYOvLRBMaG$sY^bM~t({nDRt}!oO9R6uE;TC~N=jGG|(rt629E`j-r=5%EzuN|JAJDq!yG'
    'Bke`Gx24vl_Y%k#8J64vSr|r0XL8aJ-&c+gziEj`$alg!yU!rul|MT(_A*yxP=f{Gcs>n%azBD!91AcqfqYz2r55AJn`pNKM1`G?C!5!J'
    'ofT-CXJ?+_m;eB9WzNaITIjvF)HS|bk@})k&Hl_cSR2dGfIFsxC0JUU@PG~(F%h*7GEp6No{l*m&WXC%&Bz;VISg<OvGp_>U0|PbDSiut'
    'IPQlIsGpn!+6=ykpOud}Qm`wYKk|u%BQ9O=h^`|DAji0&!LpKv_4Dk?Lss$e1-FWtFH~^dsO{9!^E_nx@M7OyvWS_E)oA+ceegIozng5Z'
    '3Td^v<^nPhLt9#@4Vz+kWo&%$$0<~KwZXtQe)+L;%sKgB!cK!)zr_klE-eEWR%6YO4J0cIe&tz}<a->)gfz^I>OC4rQ$@q*CpovciD$eO'
    'g$i@JE+pNfsq7tgQN6<dE!~Td%e#>zJ=v{~t@|a1Cl+Ouabyj3u`pe8#Sw-P)8EtX6lq10v;4rz{-}pWhj0=E#*0Phr!-w`e2StL?Cc3}'
    'fyIjTVU$6(Amp6g4<5$L`i7ma3ZtipBjc%YdX8mS`GTf&A{E|SJ!s^SSjGgvytfH>q`R^6=h#@id%XkR60_>>H~~GPppkTmB5?a@MTa|q'
    'NYo94USA}nmtLAR)S*@vT0VK0weP<d;18dRy;eK&<~E^WF^0jy?&$>`cE0wx(H=SD)g;L5QWGAZHZwY*LYd_J7BIPE6qo((X6s4lALEh3'
    'r#V^y;lF5{R_1V#@(c?L!S?%JV*HG6)s<DpEyr~+QylZLq{|}M+&7r``p9y)*E`aTI<0XaT@JsunRH^1@ywL1IP&#2IJhST!NI`~`Kubl'
    'g$lBG){3hQ1c>7Zq_*$~^ZVd4eax`JKS`4}+R~k@0zg1O!0=1->%<`HY8DJ7YswZ2Jw}#;kJ!w@<PT79j2DjX!6yCVT5Q1%Mw42)FGc=H'
    '^IBbu`Ln;0;J!+aQd|DWw8o!HcE&nC7beT{HFZr1Qn@T3z!X6SP847t@Y99-J5<jX8d*$L4!CHl0%~`*^{4DmT7GDy7=R@lECz;ksegWI'
    'AIq$8!UvS9KS3UCu(6(7ITN_coQcS|LtrN@YFg+fBv)~+-pcPVIcqpEW#fWL?^i_{H_KXoJjWKhhW7fvTtN#V3QEu^L4PRm1aYYbC7`<6'
    'bj|YCiV3lB9u$W|Q-igY(|j00Lzq@&?f1Mexd&(;W>Hxvu&6>>qC*$+_6_hR5a`3^629RY2jyT}23zsiUSs>VGGe=brmAzf-@xA&a7;K0'
    '&|G}Z6I$bC$scQn$-u880RftwofxN0`R|K7x4>-trd4`2kxS%Ehpt5Bv*yF(Fvjzf+1mk4ASIJheNkjyYCLc8;yTl5SazL)$#KcBRCOgb'
    '=mtZj{)DAn;nP~>Z8ql=3ZxY$d{$@w3a8asyHW+oasN@Yvqqq@0{q)&_H2%-guwplI+clh=A#Y?i7(xl+dnEcBZzzA2)Vh**kVA@C7ZZx'
    'LhT^VWU)~5@&|s_<Mu(uS~a20KuMT+Nf35eJ>5r-ZDesi9DV@f<``a((J(`cDDS~be<EF+pKucP$a&&~3=Q_SgTjSbM!c`CUJ*Gx#5jz)'
    '6Ohf)PL-M=8bvl`S50|$yi`!uyJbE;kB=YXp13`Ttz185V*M*}XmkUr4jSrbIAHM_=HFHy*HsbQNNZ^uEzKaS$~b_<vPw3R>wvYOc^k&P'
    'H5G2zkelFk;Yzv3L#;Ocv38Ep@PDGmT&m4o!dSAU;x35>nwQ~x#7ruJ@K}DKz2-X5=X+Jho_j&*b9Nt><x8WBzxLnTeL9FZzcC463DCWF'
    'vXXvmE$86bDx^^_Dk8!5_0CilFjB%Q!;U`Tf8C9*%@mP+RnW;_EnXo6>-1y<9J8O@%ox+x>)a|$g6ihn;`>}K^D7M1X@H8VCcpc5!N-W@'
    'TQ2NO3nX@{-dFn9fWP<V)O}Aa$UnWd*dz^hIRaJKw$&n=iJ=wq9y~M9tLbxa#EH>#9A80&*$2_r_*d<97l%0pk_r-+d34qV5|R?ruCM%I'
    'q!|iEGF(uimVxn%ffu4QXjWECo3FUrW<d1xEu@Gj*PL;;^@9Qtgb5Tw0aHf$a_Sd1%uwSlrj_8PHil1#>+NkBX&kZ~Xiyla1P9}9|EE!e'
    '2=eADB)SvNha9k*@Y0`HiN0W9cJeDyYH!_J^%a6V^efIOFM7-#3fOxgpnv||@sfO&%sQqxt^qhg^EcJtPd>gfZ!|hjQ-qj!S@d3eT&7AH'
    'gQTY{3Qs=n-l4e)ELdiiuTiyU^`j>!rI9J+_VU6KS^2fiIasRTXQmcf`pqME=;Fi6yz4N2<EG{M!rUA+9Gs?F9cD-SKI_ERs1gFL(yic?'
    'Ekn{WNYizb-YGlUp`XmXeO<3&ij)LtlsrJU;{xBiME%V#5kw_tWD`o`zP>Vi<F@q)q=(VnuZ?=nL7fq5le%50qW_-ZBzE$knPn-lkB4`G'
    'pQ%SgLq9o%6Y~CX;Q2`J`dC{!W+!IZih&?Sj?8`2MOD!WB1<*32}(p7^|iYLU;_p3a{8PknJ@Eb{(gJP^saaVPS0J1b9j|kj|Kl4DD$zp'
    'Vqw>x&e4&9Gd9oX)h&mS-c_5I9CBglOyN5qoC2$mH^4#S`7XBC&!12+dMv~(_?G+nw%bp3@J82aHsdFPNAJszOEiU!&?IbpmuO&Cm8HEd'
    '`__;+?%byyWMkdM`Olm0Rn30m<;!OAD7Q(XLv?O^m`zJy`@DEjLSKYCc7G_8V6slTUtz?e=<Y2c<2gYR*MkD4#ip@<0#k7AhkXKuK9338'
    'RWuwV-0Vf2H-8p8NulvqSRcIl!rogXpug7q7bgI)aZIF~#>MI%UXEf_PYIaUEJV#mXI)%q!z}b$xtk@>mCg~zt^-O2f5v!uW;P9Q&x`Q|'
    'h~L@GUE{k_2M<ZPw%Akm7L+M^?+Y>v^JIvCrBjpO>cHl~ItT5nT`w~Q2qKbnfZ$j2dK+Su7x==7_PPwp72d89<v+h08?!WR#)P{8BJvG+'
    '^s2O?=X0xXw{x{hRRVr#$+h6hl_=#ak%g#bbwOj_fvk*qi~n9(V^1(c`UEoUhvDy*+|~~u2y2stZ^VrnMEdK8=?dLQ_9GaoKI2xXi**Pb'
    '^xMG%#e3wmPc}GGz^eI+;;5xlvx9GV;I^|zkKz-@92(07i(Jt7P|~h(_`FRXSYHM+s+}z>^^a`VO3ET~Suj~OrCtvvykcQLhxI05qixR)'
    '2zD`La4?{@D@`fJbf)e0Zl9kl;}Hryqxda7^E%dw@DSG}uM9moHb634Hinb15iQ=15@B+x5hZEC4!xtSP5$-SuW~Hg`+1Pf|8Bq9d>I@J'
    ';qqe-_kc*%|CbE%u5E|CAxkomtG}DyvBXl;KJV*?+4tvM#yb9Po@4}F#cK$1DYlD%KN<_PM7<;YulR~*g8(_AV9;CJi<kw_aIvLv+mAkN'
    '8@Dkm7m$AJ;uVS1I{b=9>Eq4vo+#gl7;Ua%>xYOGHDu0lPG0jLklB)dJCFr-dR`|r0ML1#K}Xd1yH3l`Y>u<VQD4HFQ?q=FA9z)rd7GrH'
    'S<6rnA|>){8onP!2k%=v(I^2Nf!)S0y$?rdNZ!xGjbh%*rF*xDqWdHK^uPn~9}gripM+KnrV#^)>_ey2)fmnLrR&iJp$pa)Gmp)N@@SRd'
    '#Hw2E&5!<6Nx_nw(nfUG2A_lJdZ*I8#$@&7pyk_bN~rr_=sUM!Egd1}S~@5BB!kU56)%y;V;G_hDgBG0Ka~*yf0ym1peu;SXtelOjT{B7'
    'BZG!8(CnF$k$!A_r5l1PnOA;ev5T+aF^F=Usa8|n7*mp-+B4p_OUGz0Fe;F9qMg*GPDRJCJ2nh$YeGk@iSRCy;bN6(<G_SP?Yl`|V<VZ9'
    '=iu~R-6a$ggd-V<qu-w|;X)+wSJF(uL+>1Aof}u!Fa{Jjh>dP_co6<_z<=cJ5zestGm?~n_|ZD3tfHr^#y%T-L_N6Tk7$X@ot4Vmo>;%+'
    'tdGfyogUVy*ZHxAgBEL$sU&72PJf?M6)L1Y=%tREbG_OtRHUXRL&o&vQcgPHRg0|0S_QonNZ@+K+fK5TSvR;%JhU`4);F18WIMu18mF&%'
    'zIO<WWAbS*<rnsmO=U>bdrSo%m{e5ZUGMP-rbeEM+RZjFe<J;x`|2bSy)NcWS|Asq%0z%!OnGWByx^^O684oG=proZt$hte*R~@q{QOWc'
    '_`4uS(6lcZt_s>lEwx8J0H9{;;)r~UdQ7*r<&neyK&kkWBii38h+O@#hotofl*HfUh-(VuRHvt`H@PR69P~SAQ8BlCe`<YDz0dnnz4GwT'
    'BL-^SoI9Djvk8DD4(4pR%JI2vo@ir&{RSq!d5~)GT#r`~_X%T@+hITltD{<h5y600V;aqBYMk&#@A#=?=`X)4#}4q|EneY<M$hmDt>?k~'
    'I5dHfs*VMxHOWW*u4DYPq54og&R(_EQUe=@;KmLoWNYqFB5mOKFdm;cL%lzk&T>f+3Z`M7<mkcHu!cdbg7ys5;|F}=$V+o_oPK__3ybtK'
    'Ksk@1EPtg}_eyCg$Z2tFjPMZAXxWKj06;C>XSg)|JJMQ)I?aRg6--0@u}kym6UBG?aDA}M_W2^oy;_ax(9OW<S(*X^kTY9>dBxE+7X&^b'
    'ZZ;#T7w#*HJjajRgrZHP1S1Vsw1>o=<LbFj`S^hvH_VtIwT*-O>*gJKTEuFN8+>IV9Y}QKNQr9|z<#n9`+pw#bM(hjiDz{$)wF(<@2<k2'
    'XBv42-5fBJtma4dO5Q<TC7$h~2)fZ}Ghw{-;;H^RfFnvEmsCe?Fg$)9j_0$dK%?Jp0KdW>9fut_3I%oKJi&H@hc8p_>)^GjU+y)@Yg20d'
    'QyBh^bYLP%ts@>39eB`4GSbQ)P5YSRH<63H3cn#4C|!e^>C~HBx!t??AY{t5OLX9mnXxts6q*+B2|GA&jQlw)icJowtU9t)n)%``HfOz('
    'X>;agy}y5VlB|Hb$%QUnEhY=Inn);3R>scx2{N%c4*2}|<vgMo7tnGapskF^EWkj6Gwq&Ci&VL%eGJJ|lr9Bz-0y_*=x>wO&+0Es_-ua('
    'c@{^FpM0kobKWM0#$~&^Hr859ENn#0-INZUu1&t;=DczEPGlc`ePuMTXjJ3|^?j(iHS5Pv-f@}4l-;mpQ!E~R(_&`a{!>(N%6q^hmc7m='
    'c-(QNn6x5Q;fFeaG#C&yPLX6;lTU`sJwF(?HsM~l%j+&g!i)|^Aj^3Kut(zfhvIApW^@APHTh$1rMZYffqec5HF_o#2SaNMsgC;>PX^fl'
    'N|zzjwp)CeS6ddOvy4(Mu1(W9=<-MJ9(ugXtY}^sm3hh7^iPiu&WMwf<Sb<_z!n<m=Z@A17==m*agd&}bZ1CGF7!iYa*0#j9m|12DrfBE'
    '$!FBM?M_dvH${rPFS*>skCnF+-de0Cn~QT8(hH*po%AZB@Kj3u+rVZ5ShSnyR9ZC_8?t79BJZ(*%PrtMdk`T~CLbUG<qHh;rNb=K54-BV'
    '`CtqGgaYWISq=JApKy;Hf*kkufKK5$KKhz(5><nt5D_^^`mbg%jP_>c>Ex8WlGILo8j*1o*$|u6FBVct-RCRFynf~mg8dAi-0u`chw+7~'
    'fQ+vD-R4d@Q}R1#AnYp@Qx<~DC9J96+2mJ+8EZ{lMUo9KEH?0ryVZRJp?xaP?r(27(Q=-u*~u^(;I$_jaoX0~f_2hOw0D+U`6)XGa~hG2'
    'XIi6CTj={Q#0Vr#*4`?0v4NywUv;fPj{rL2LiyJ}QE0~I&X(-TI@?*pjay<Gi!CamVl$iY6ma_U^MMK*pij-~z#)1Owe`c+vd8l!oW$AE'
    'qzb<+RE711b{{L?Qkfjy{En)Eau)f3IaO9<O2N2UDYE)5f2-z$Fm_pH$$MN&qY^1tX3@FnP1<YZhk{q8!9UojtkZ}S-7oS-<aG)HzPg&U'
    'N26=<6vbLz2$#O!&v3`*D1p?ESlXtXQQFx_&O5q!C8i3&8`c+o*Uo1@Zdz*td!GZl%@oryEBsw*^APuPZ+oRjB==n`2WsQqyfzx46@`qi'
    'J#>fZ66e#)dL*F7GZ<35q-iyuB4=0!RCwI=9OH-I7A!fr#FNJ2M-2FB1{A2ZA#Fg7d&CU78C`TP@Un@@DhRu{5&7~Z&V@%75l~8V1vqh`'
    '++fb|6v^`6Uif`m-9>DgI(wYK!vr08=lzqifAkoCj`J=mA%H`^i4Q+Ih-aNCWhL};8~fA<sd5RRI=c2znW_t{;g|3;OkMYa2(z5$6fuCG'
    'w~i-!_3vngOG<<AM1+3MdPS)}g#j5jRS_YZpV>{t;K)LuAJQ`rsZ-M}!u}bZ%(w9<c}f5j+l0CF?BRm<Y<QC9F<rv1o5;rzyb{xOO3&DI'
    '>CTT$_|0JEzi(e>0<lQfNhheJFFv=nB+5%$xC2h9_o2expE*tLOXP#`HjTrA*+DaM1QdQZXSWl(E7L4&KBs7%YFu0O$VRG$RUGygo7Jjg'
    '#ag|%;^6VN&4<o9u6x_$V%;es7|P7%69WZC){t9@#;AXdONlY4F=vwxHyV5dipADS{#&VZ7d?X~UPa2dD;bTSmmgYY*^GS}#%VqcvMW8c'
    'U;JjjJpPJhp7Y0dC<v=*JOKw(Rex_prtYZd7SYzB6@k?q_7et%MyO_ob6Pb~KZJHYu786YvNEr~0yykUVJ>`;FRxf73*&3}PI27#CEfT<'
    'pUfx%nTI+RG!3?R?1z>TEs4E4{9pbkC-pk!-Ve}$h0k^IxJ368-vzJOBVVlm0hOUje&xaxSIih`7CZDIyXgcTP)Zo_SFJjo%e$1HcyvH`'
    '*QmPGcAAky%}3s@`1}*VyUIF*0<W~6(B-3~pfsu7e9I?3GFjv1z7{We=PVj&vXm&e{1?b3JGJ+9o2ITY#3=@NfFwEK`D;Fe)L<)c+_T*T'
    'cYvq_jwT?%NfM3%`ygMUIDg*q5Eaw**HnpN;JshrN#?MO)Uzfy`9QqMjQ*qh1i1KVjeJVcYB`B~=#<ZK{@~UWWpPPiXo9TK?2qSkGS9NF'
    'x9zbLdT-uxlvi^EEFOwonD}nLIu*B{;~8hK8}I66isL5WFF7bropzX*##KI%ew?M{QhUl8MO<-iT{7}{y+nGvD|ED}l`QIk9ik}i?SVco'
    'w_DIm>iWC9Iv8*&@ky!;gsk+pIQM=>F33oVxvuby{9-;{*?hzH4JmKpq}5ohISCr)Lzs5W$vn(#<Lc}M8rDd?hy`ZF>jnw0;jC+_uU#C)'
    '%8`*UG*_I*rh`7946?>8&z#A9r<RB%E0J#!%SMZ4Dfton834}j%Dw)4ggbpWc982tyM=2q8*-r+Uh@cFx&?2Rx$bO!g+VF1O{m0dzWnc*'
    '0c(pOMOt$ULj?rwQ}^Yn_%9zRuSs%hcZq(l5=)CbAkf=}Il?eHU1KLU<!@PqE;k->5;RVhs1(fTS!kr(m2PhU8D|}3O82?$QL#AA!DAjH'
    '3TC_(<Uh9IqN4R5NFo7>+OFL(&{@=uq-iTGVniCC3D;?mK019!yuH`!Im4JKs2J~d=(U^Rd`E4_96*lg4JKbe35mxRHI4usIwGpmJJmyu'
    'NxI{NfGn{*1Cbmxtu`AK!d*n?;eu{Zj0=IBSxHfj)hXFJ4JESslt9}`L6jn-{G;Ur?!YZ+6muPzLk5`W*je-079B(6IAkYdyfR>Wu_sWc'
    'V-E@=x33QSZ&<6vZH_>)R7O4F2MfW%sxY*)Ya3*)#%DY*3V-^6R)4DFsec7a&gX|^lpO@~$nL@=6naovB^MwH1BiGIsnv}iEig-J#l{9k'
    'G3F)Xk)Iy_xT^q$h;C|~yBERirp4k3Bdqj1yvsS?Z3x*Z)VX3E^hI5Csz+2V<jX(|2Mzk*PjWx3JoE9feqSOs*3gsln&#986mjZH;FD1Y'
    'V|Fxp4(V_ddSN9vg~h8@CCr#tWO^nCF!+N7<f2Cn$G|(`0j`;}{{-;(ya<YJ3>tX5Zy~NE-oMOgO2o#>{c_OXyIL~JRHC(p@0_(i9`*u>'
    '9(dSfNZ+g(D>S%BA@vwJlYHp;q^Jc|l{x4GaYAjS;kGp2h&D^!HLxq9!#dY!U3L#>I|gKY>_INuCgx@3!~-vNS+=t#N=xYkYLn}}X2`v('
    'ZYzmLspaXSyaxXI+^C7l<(J7m!~cnNV#6!86Wo4baA0Iy-^sO^ASfXQzKWcp83CpDO>r=bWu~PFZr#W>NrZ@HsaqwL2q${_B@hg`*Q#H3'
    'lh>?KY;YAztxV#P*SZir`8|2?=+t1O!`#0$Eg3$RT<;h7diUq2oWs`LnwyfP#=j)*0UgP)wS<Sqf0gAu1mOJOFayxYaA(d)!;Kpr1Kp9|'
    'eB$w<=PCr~Sr)ukZ)5vBhiabmVi=i5wmk8wnsqlH67mhbaJzS;HET^yr>^D8-vpl2>2pXz*&1)TW|u~!1O~4H=D^UBY%RNRue3ZPY)lpJ'
    'sSf6W$XNx?QUMEPsK^tUtC2ZQI>B<6PTA=h5UtW10YD&HOUcUlF$yvpVlrA#fwy{!Am=_;`y|BM!)vpW=gDlR8KWuepVf%!2pck|yGilJ'
    '%0h0wY*x8}Q?&?r9nQ};Ot*Hi*sa3(yX7W$V1{1ym6$nG&dYyrv0rtv*6!(^H}Q>%AqW_re>J?;I_VW1sq0?hG^MRQ|M@sGL(Un#Q{q7Q'
    'c_a5l?CzO%3KMeocQhl#fb5{8t<5IBhVj?$q-9)laJHTUwMjjP)bNE9)@s^=i#7|9vz~$E`w!Y4?jb7w@WaP5*~RD73)REWek>L+#J~80'
    'EB{9Kp<t*m;;$cUz~K}sTa2D$GnPcDrrVTrvely)i_b%lexYo(HCM7&?q`rR52mi@9|J3}EAyoyh(h_gh}<@MZYLcWO<!!L`$Vd2*ZyE)'
    'k~R%%<(W%o{JNpS0U^Uw3R{?>D`8L~N<RISZ(Q0vTZlu|=JbL143l)-`0zltj#<a!?8ZKcV~uPiv(=B?1+pF7JigWA|GdB5ccTMF-8r%~'
    'CPkHT9MxA&B4m`DCixX(=e|crg%eNsy#`K6xCEz{&%Q8Zw`cLb1Qr;8S2zLRB2MEZ$49C~ilZFvI$9GYu7eE6v`^M*%OltQ{d&RUD!%4`'
    'bFXtdRqqU^#*kWU|738fS8BrAOP*aeotj&uj8Z|6MvlJ(x|d>mr^c#!+iR6)*6D4Bf7Yd%T#={$)~?JxNjO{+9f&{}u@)da{1MUn=g48A'
    'n(eT>6E;*W0!@XmtACS+lf<y?2#tQLKZLyUV278v<H^_`g8p)s|AX{wym?-3+?Ae2&=g~5Q7K)7p&Qe|v?HqB804^ayOv$un>qqNakH{y'
    ';-zAt!k=>>dVD*+yKJd`N^k4cKE2hZ`8BwXt8p=X<E-ZA_{`ecb;x38+M%W2aJgiPAX<fx6skLY_+Nphw@;r<nHooE)j_`qx6-+ougCLn'
    '*wWU~{aKwjAMJ)M#Bz7PsWBd>!PYRJ?;T@^#VLIK<a}_1n3U;UZrZG*C)o0yQ^axptROFg!E#hKOKqHc9FJ09%m@Zw8{(oZsAU6T`{c4-'
    'pbiiq4)x>IK*eXHoHWtc5j(i{`*$a?BB;GS6%l`HtBuQ8*AVJhB(!PLYzcm@n6h*ynpKfyM%d>T{;U?TFE$m{K>q3M#u;oY(Weq!?Ou-&'
    'QsC<Zx?PpCijNIR<D*K%#8IKnSW1<u?i8QC5718O?3x-wE(d$>TXk5mQhB-b9pFTND2De#zrAY=!aDBovg;Nnw(*t;4H+gFT_gLjJN6MH'
    '>=e9EsMzeGuc2j(x1&%*9Ha(zg+Nx_a&pLRiJ$47Yh`^SwAkyv!LQXRjxGNAJqKDbT*%vP-fQSxya@wl*fMN#wa}r<68Z-Q&_x_%I4Fft'
    'El$c_1-z+K{mY0Z1By#vovptJKli(bHDElO<z+tTC({%LWD!|`Ksauu6}LYr9AKG+aAtzrL56RAj{Uwq_-V1;bkevUEazU~PRBJb{4Nr2'
    '=xK+fgVwD{jhcJ8g{v~UPt^{h9u(_LKI9guK-?cG2Js|xyDGk%z0Jy@Lp0E2@DGZ2tZhF_PlgPaHl3pyV@yQg^pkTV0dK?>=EmgD-Fah?'
    'hHi3jWX<;E58+g{a?Ri88(`JNES^?@cN7{{%RcA76^wJr+dTO5p;wmtK@S1=3Vq^~RvqYj>sxO$6s8z56`hW<xrt0wLs!qZJ2K8I1JS%|'
    'Muvy8`c<C{9@y}G9GduwAT2kjAC-lIw~Q8w+^i-JbEz9ASRr)|q+k@WHu!|HHymulmwI#cu&j5_5*#eJK5{91{Oh=`2jf^cLq7jwWYeO*'
    'kUPLt3Y|e~Latb#KeD+{0uTBt5na*Ra^1$>QrRsW#kkLH9`Y{nF(r@Rb#K>|m~WazQ>5CKI*z0T{zH3YXaAJaIBf8>suv;P&w=1;Ctvca'
    'v`0cBpfm~0&5xjQCGo;vt6_#%^cz{m#+4-0{-Ydi*%)x<AZF=&ofCRTiYV$Ki&)>OYghycqm7-&+ZJ6nC2dgg4+Pg-crrpJ(O8fWN^_nz'
    'Ep5;XfBl2p?`TwE4!KZ6st)jj`|#-F=;d=C8KE(ZZ9V67{cAb(hmyqaj3o65-fj-U7TNqx;uGP^6B~=%KoQ|jud@aPJ!BrcU=ZxJ3q2PP'
    'deg$83O4hl-Dx8h>bQU;Cc<t@H|8yC<#iv2=lW_BOhdHUjWbne&kHZK+zjC)@FlL(bSN${5QN2;aW8*wj88b~T&|u}-?zP&yh(L42j9Y='
    'V93rKN;J_d4@U`kaQDQcn&k5K$OrewX|VScLE31tF>=Tdx?4Mbl|Hx$St7p<rNY@t!_?_eu7EA{S$&I5Y%QG=94<`oghot97A>sX%ikJI'
    'Pa)^-7ebcNRQ6z{C6Ad`7+9W`Y0>%{$IK5k@nt0hIVE|d0BfiRd+nfbIT1pwsxe*5I$mp0T2j^a-n+L8L_?LjVus>A_TEb(I{j$x5KXAO'
    'W`rv$2cw4N*hrsHEBJ$lM2ADW{x<4gmMvCRa-2b*gJ(<#I-hDJNGSy~f^84ybkTGR0O7e=u~FdMpLNy>HIcNW95qRvSCmB%TR}TKhf~#F'
    'lH$E7XAOyuC6OuSX|*>R!%rUE$FASqeKuB5^~rUJBn-c9zmj#h;?Oo4?<8{dl8A_;&glRrkD?mL>XXN>`OXF|p2_fD9DX*$U1rLEXroo{'
    'fSrv$LWdcBt|3mll#!sTsCBGOh*L^!LMTl6I;-=UPA`rZ>T}$dTBWsQ92cd5<S4FIql(H=>x6P?c=V;M3o+s)`No8k3g4RT@yl#$rC}Uo'
    '7-*%hi&@edkVU8TmYQ{6PLo5{J8FLv|2TUpX-drxc{GP+op24S%qe=8I8^$X_5RN1z(uIyzk2+o(~E1v`n{k}_ALr|*SaS!-Du{kZrDrt'
    'Dv50NySY;i5N*F_v*bkzd2&#=9uJXZ3rNRlA!4K5L<v;kdKU9C)69#3sKO)Q|7RVK9CmrtkG6#7Z;aAnNA{kF&AWAwO}8rG`Bq$Av<gB{'
    'Az)AQLIPkixm-TT<s_ZzM$2bVV>NL97yO#N4(GX2S9H8_K?NxMQOc?5UsRM1-QJ7f*QYSU^0)-%>De)Olm}b$LiHqZt0A`rmbeedot9iE'
    'ub^}lmoxM7<rth#IZpj04f@}Q5+uRA6L8X|94+?5Iw*k^Bp$h3_>(J4h$;k@8MF(CnbN#Kq$(vLw$pwi5Lfj-Xh0XlMBwUQ5S_Mp{c(oJ'
    '0s>hEZbg^2z?DN2zLxk2sa_~Hh1tgDVgib!3Eg2OW<yQlNp%Q^r{HFSK0$Ge$YuE%oVllwx9<fIEIz{8feS#64xU{v(hlfQ0LlOgmTH<w'
    '?r=yH`_?=c^KVH5La`UjKsOyV0Z`~|vzH~Z(%569-qjC3B;e$hlCQcas{Z_t^uk6)vrxm*DstC*I^e+eZCmIlM8RO(=*i=XbfcXUFE`S>'
    'VgQ=?rs2!%+o=E@r1%UmrR-8^XI=Nn!M#=Li{$2E_$nRf3j{@kd{AG_PBbDaIwk5x>ePpge;DXm8_Jr$ewSm*TE*7+)X9icU6y!Ym8|a('
    'A=jh0g^GHT6CnK3Idaw49^dnz)b<Wtpk-NV?gE&h1`&1zJD<#pvrz7%y`$u9@z|;v?{T-jrc!lKw?;TI{@`iV^m-hqP|;H~EdX7OZ4R)g'
    'EUz*FB5@Zkvs!=4mcziC1TxZO?x6@rbt6$zcJfHPC0hTn2X%G`qj>Np#G3tX;wn8}spx;?LsZ&4&rlR0Pm|nLQ#@O|hBQ}TY~+Ta7|9^v'
    '*E`f|AoEKJm-=O}j}iaiP~8=7+YQO1b9zU4uW^D6eD#066lfR|zy5aPE~17*d|}mCPf-I!f0GeWUJ>(hUz5AAz(B(A|A#w7K;M;1UA2^F'
    '-;K(-20~*V#;3y$Zbrf>K8bKf?pW(1LE%hGF?+@pF|FwNz3_u?6iC5q<?KODp(JL#AS5<B3*$eou3q?wI$)D~1l$#dgBiuMiI)uil9v3c'
    'k&D`Oy%gZz_8Z`TlL;p0m;BQzi-kE7kS9fSO4$Z%=iIiEL3LgU^h!#!P0A)2sq3s|h^vj@V^(9R7TSz!Pm5@t#p4{!(#j{#*~kJiw_z;Y'
    '@Gx!2&!&n(O!)t!#`gPNmXSGufc_W%2Q}twZE0iUOz&cEXJ$z2_5V_1Fr5D%HTKH^1f($be>i(xjy@BDg0%vfAPDkzULBn7c7N?(kDvC>'
    '03cqdckA1K_5W{bY<&uW(JTK)y-+{Vul~3GtNo;Xrv8cGt~b)p2B7+}`3(F`{~`Wqf6Je=&)?q%r~*jdT7U6>`hVyR^q2YD16qHT-vDRQ'
    'U+M4hM*HW08NbDEAb)WH79e_ce1rWBbmPw_{YU=K-aNr0zkMHqzZL%npyM6?ClPRU4Gb7w0R_m*@h$Q?e+a(L-}-m(@9`hM*?Vqp+h6@&'
    'brIaqE7QmOX8*{)^6${k^!M^_`A^-4ukLTvPhgz*Px24=83Q7IYL36N>J|FU`wD;gzY%WdKlBqdn_dEMfj^W#x*z<1@<Hge0p35y2aq4*'
    'Z}hME$NbE{>3~YW{BQ7&|E+twe3}1+e+)qM%lP%r_w?u4xBNZ-8NiIs%Qx!x-2d%O<|hj9>+=7YeceWDetGi#r)lKz2YDPR<Mwe`#-tH('
    '*u-IdmwuFKCGgio8WyRGWIuy>`*BgqB~DS=z7ti%I$Ry|25MP2`@`EKkO3Lb+7rE+hzRU;?&+Hu_;5^ITXb?b6RSwuJv)|8Vs^=gX4a?8'
    'y-ZLKPgUH<-!*w}7dUw)?`-iu!7$pyX2DHeL3Xv#d*Dgjvb@8*JqMErbP3P?g*A%SPSVds0b^384eeB67X9~dOb`~+wG)t|cr|s-*3r0C'
    'b|^c2zBZ71+9_>!=({>e@$3mjktun`S#`xrq*}ttsFAW49z%4}2-#z2d9=_$qLVJaAOTn;p_5Wm|D(rtqNu=gH~g0P4_o6I2?LN>kpk_4'
    'CD|xyNid0JECveX7>6xr6w#pGDB)s|v1r;t5$rh(qYfrOrq<*r23d-T{}#|dHu~q~-y!K4Z@pzH5Vm(x%dq>Yjj`8%#Z~k*eM%vL0d}V='
    'B2CXn*@d&bkfhQT@u?N6?rW_=3*5xSrtlkHA5Ux`oUrK3gI~w49{e10F0nIRE|yEOdLqM0Oik$9W0JhpA0!gD#V`^=T0E<U#rsj|+C5kb'
    'H~P7JmQEC(y*R{hVe@gPE!>*E%#xyi&(OPSc2=66jqE@*Yv5K#M={<><9IH?^~s)1{_&7>8mIZq5Gttj1rKie;}FYzb^;$#Tu3mVM;x-e'
    'r=BDA2KKJUdVJ_;LwvQtyNg@tgJ&U~yonLaw!)XyA85>Oy`=9|(0W9K(&AF>C+pQgN9nkCAO+cSFUlLNHuJY%r32IvGKqAPG6+vktFYLK'
    '-0vgz>ik2xs(IQ~bCLC`9Px~4EyJRxP%>HVkZxJLc*KA2cJ|c(A`G24#m$3r20}3Thnn=Qm0cC;8)h656N7cbvOBDzgiy4_C?4TTHwE~@'
    '{1RKY+(E5bqMq`Cp?7q2S$kPKS&tavq6<|Q)va0qi}n|c9{_|JRrA4F0$|6<kAxq{JZ75%7v~O$fK)u=p4*e%y4ww;#=mYpFVQ^vgGW$t'
    'R0)(jHrd3JNe19;yb^6zum1^Uq_&QbzfbDuVJTAlb%M=bByJ>+p1Mymte|;#w4|RVRw&kHOhU0Qk&_Z*WH)qHY%ljg?JGi2>gQKp;24`Z'
    'VgR=9vp|@dTr$C?2Njk2Z@*@LtaJ-{h^8rxRO*tZ>XeYk0)i-&^y}+HwC5ZPE~@xeq2(Z?P<ma$F4Y^n!Tdxj%>r+n$Buh3+||VVS=nuZ'
    'q95prd~h!P+zng3|M`4X0w29pL8^P!x*4{{<NGI_0AY8}tMRV6Emi+|WcN2LVVh#b_ZP_|^7i)%XS71~n-kc|7=!M#03nSgq_gdZdlnZM'
    '*Tx$r(7K0BqDM<@cAvGBO25^+$b#N()w|~+`cXMg?&cgUnM@|eAEmk;W^ny&)gpeBm6NB(-!O0s)CivaiJm0CS3Qs~|6wWy0Je7a>Mu`#'
    'A55v*x#EW)NZ_J8;f@vr?;+59!Xx%bg)D>(Joh4`aGV(IO2C-*!=|y92b0n^1`jkIuvS&wxFEHIGD@T{vMeG&{yV`HQ{=7rRpM_IrkH+#'
    '+o)~@blH?Y@<sG(y>J5%hM@TPzG>gBLQEu+4`}}95B7~WVb&oLF>=(t-3Yek3Yr$3<pG#OU^CqMTpX7dbI>sp3K214XlycO(irT&K!8`o'
    'QPb!3EZk)M$D^JMok_3w7p~|Sux@Nn3t{Gl+%?QgBX61OfCa(zH3GRJD^a9Awk04yG|#I{AZ0LnGeYLFEl-i+09zJ||8}gn)kvz?X_5u4'
    'f!pST<(khQwDB<Ufm6;YJiAIX=+>w$(!LCiq}o2-7A%8%vMrAIoo$|UZRxooj@A9bcIsRDOgm@a9C&uwGWdbpKV>(I>3v94rh#xlp656g'
    'Vhby%nH{S??<?8SuN>I0j9wt2<JYT}&s!k_#KGLG^cGd?Hg)_a5y$DZ%bx+ZQ@jgN&SjuqbB58?P;9f~kJ0C-$%oJ7R{?XPw(fM=>~T}c'
    '-VU&oQ(Q2<bTeUf18!{QVrA2NdiTTX!jxNBM$Kftg;1`;wz+4?2(?bw?AV4k^gDbSNTPe)RrUu(Eu7<43f}aM2(`l(ot?4jULtywGsACg'
    'G`0pMM76u<fGH55=^lD$dM<F)Z#UMK5BbA*{w{!zxbV_J{q7(EN_;+A$%f``gAIraFW1OPk#ZbM3d&JSjnHGV^FXY(eL+D}PTO*r0-7OM'
    'UW|z^xrAwl>##!myI;bz1YLBQ`GB-|l7k3=Wy&ZUc_*x=m^tz1%#d7i?t}h9`0K^;J4AoEEAbMai|1)n7o(GmJn_m|;v{@?5>J-PJ*q-g'
    'c#ZhaS&O4jGx^pMp~N`N$>H?DsC6cWjUB6Y<rK%juvXZ39V{pJKUN<{{lJF6116t&gHh)Ls+zivE8m#VmxwJ86VkG23L{PUfzevOyG8-f'
    '5hHL<Oh>T1q+N)txMGE;v(+%78lvJmz5g{FeXu4O(QL_1JU_zqyFT~A9X|DR=Afqb{zY#%pl)nn{?DN;Exc>Y!Ns0B&xnZj#wI$xPHWmW'
    '-)Xs$0xJ}3_0q^|<~neKaea?~u~d~N_ifATn`LUg;*g6oq}n1<=!bFhVLm8~E3-k;)N3|7E1Xoiza+Z>iio7S2&5xFT*iFPn`&`|@*3N8'
    'Cihi4>`*_xnSzC~?AhO)y~pzuImTzjjxSu;WO_@;6?54-;OL^nH);R*X70?feH&;-y$giCR^@<#Z+#!hb*bU+_5gRddiiwo2#swaXG$Y?'
    'p}uaz)*CwdOyTfP3hz>EhYHgu!&OTP_hP%u_%}3))4Kf_Ef$(eBA^5x?VaR&#79I1UnDgScIah2&f&{A%`XofJ#=bM!&^PxIG<7atauL3'
    'Qbx_`8od~49NVyfc?3j>^WI;`ijAS|?xXr#PRR`w>SO(fXW1x=A+Pse@Dz$9xZX!wK-VudoFsQVs=?Ux;_Cx9<;12UE_@hC^tL&Z6)Z)u'
    '7RK8wk>Rq-kG9HAu8WUC5eS+hdS^HyS@m<eMn48)KEyO}1`8W+!O_@HO{DF|7mN7suX;Yi&zrbVSao%o-WQn60?6y-9)d=%Xbxo@d8p+g'
    '^OM}8&2#e9T@ima<=$plyuNTR$e$hOGV^|p4+-tihqNN*CWUp<y;G$e8h9S&C?{01;~SP{9h{{Mq@@5qj83T>#q37YRF0w%F1&bt!Z)eH'
    '0GiB-FX_Qi4>6fC!Esim$F`&!a;i8ls0k{+D+k!GiMs7n75;&w6{kEnnuCJADeW#9wwe_qb7aTmRCtIZ=HHZA>fK_<5wz5`{$CjR4T$JP'
    'V}Oo-xSlsl9_aSOMGr5w)V*JORPsrg3eZo`gIuZ&UozfM=MXY7jO^Yq*MKQp`PY4l7B;6WwjCkW=s!q7k;5x$vBexS6*<ZN$$xP~Cf$}b'
    '*3Npck(o3E^g8)#5|*6dOFR@sL2Fe1z+X$^W6;-eU?`Ir1Q7GYEB3CNQs+Rb6qi_v@14Rx7tiXq4JJFZqQj`X0a(ttWlM?s`NCsK8|JU&'
    '=3S##?Hv4SF;j)({D|nrfu^y39Lpe5kiWnN>G*xm-FnyI_tV^Lu!BlVC(Aa4t`PJ17QI2~`%xZ7>y06)5QdlVYn-$oST>Z$GOo&kQEV0Z'
    '^W_{j>GVtKZMvF|mMW*!_mLq_WC4tmWQ1MMLOsgEAj_}z0U<X6vEP-qZx$mUJe|Cq2vc!CgJ%j2r^sZfRUsImq&Lwn#~QIw+Ax#4O&pvy'
    'n_eGpqZ|=zSA*b4gC^0Hz%te}NDO4AQ_HIW(YtJEWVLyhT|0qaa-~K$jCV<6@8mWCbJG|vxKS0^>>1J4s&~^>g}xqsXT(~sRZH(}!S|~T'
    'gY^Z9NumNWt-H7U3Gl^ITh~y<-{slgObH0*M<h<Nbidie&b#A;0_{HuMDZm<!vd>Yt<%3oEKk(?EB;l9nm@m8?%e`-gKsC;dqzD5COSL~'
    'm@@^>*GgM{IqclTyp)C?X|+hA`u+fNX*g;6$WsNl#K|9TTm$rQHZsMj46bpR3Q~kUGa}@0R}3dLaaAaS0Lg>B6~)gQt_^oB`rv(U9e$cd'
    ';M}LO)S1+vHK_<Ae8&w*%mkHY5-t}%?+@}ffF46Rg<CFL+|4ag!HqK=dT+lGKjPGKNCGR~a`#(@6e6OvM;2VkKkaJ7^+QUMDhwHb|Jao#'
    'ck{nQQm?o^KP0P0V1<q6@4-bgx$$TNa0m{9{YNa%%fV<;5XMxyU?Irbco9j_YYF2M{c8^6#Kws#;{}0^g%x`>6aud*1A@ERm%%gk!Vqj7'
    'mEgjGx0b|7)jI%vqyrXg*0nqe4+QyBltj)hat0@1*17_g$|sTOzLSn@M@sKy(?y8dL_2EfiqqD$E~7$(V<9}CGaT9@64kXuV6k6alrMGX'
    '-MpjKXWL4}l)n<JOlqJL)$`OJ6d`DYf9myc@XX@(E3su$$X&b&NmrT59}tcMZI~A506@CGYMbJKtdP?}s2jrbNjSGjAV(`e39r1xDrKPo'
    '#?RkOjX%+C%I34PX|L3eh?<7OhvgpnjzWYMUvuN;mbK2}bU$Ii-;n)DCp`3{Fyg!!$Wt%X{>H|C74E+9%S)logo7U;RyuK_N**UYzGoBi'
    'a~PfpF+`)Zs8Dg+Wx)qaq6_2MVdKb@FO#9atxh6q`r!-g43N+&QQ%O@q!&O13$Q<ayKn=lTEKjVto3YTKX*~}i@5+5m#rGh`;D>k1h#wh'
    'NQaERUh<{q8&*dtQ=n!Pv)(dGy$SU7%)IMz32*eGc+qQ+UYGA$GbGt7CoP}!i#GG@KOio{C8Y7rR?*hB&4g!{^>s7G`PpmYLi38Lwh}O<'
    'pS6<-6^u&$rGW8{a7c(|ts)B+tow-460nsO_AHqj4)Qljeht##D%6T??LXaBTdZb2;rX3W4m1cb={!vLZb7kK-|a?7&6ZK@KRP*5+KX&-'
    '`vFmmR58>T^XEMRv^oK=LVshiMu}j`u>nM)#=1$mf1<b1J1s1Sx~q3a=wKd)(q%*v$zP$oHC&y0m_L!5NK4hO5$xZedv^Oi?pWD1DvmS7'
    '1#sY~{c94yv|e3DCwz<h{Db`Pl&y3xxtScvW{%uivo4(WFGaapY(Rl+<k|)`ELbHC3^QzBx@_1Uc_rzs3Z<sgZ<^ie-i>~a`Xnf8$e$$A'
    '#V(fK=*v~bPw6jZWr#T1j5t_EItLiUt<L<G9a{%GpW}>>+3rYRYd0mlLQ8jktxti#$A<H&dq)$X(@F9;&+Apm;n$nOh09w|V?jp+{%L(9'
    'i*}Xz7m1QV773bmKsS<WUoxR~UjBis-Yzc5o11CJPeHAN8sO7SGykezNsFJ{hQE=HVxc}psm*z=l|SKz_m34OCTG6ZA;4s6h`@ohtIC0x'
    'yJwsXFB`NM502ib9?8eRFoAyBi;e>c=fFZ@)I?LT-k}e^!B6l5YB5n~6F+o0|4ntg2ks+<<RS<IobK3IVqN5v5Gx5<5t1g^hFlIM@a+g*'
    '1r;Hf3yYMP3K<KE7fWZG6?p+Be}jizvTWeah@^!EulXGXG4N|%b`!y(uRsU~#!?$sV9I{a_pw5PwY6!$A<gyLiTOMbQ8`FG-fqI&z2cu>'
    '#l*AV$S?S&IVRBr0yCAokGuE6L&V{+Y9KRZ^$E{&xD1TjMD$ioCG7L>pw%g$hK6e+*2_qg0eWyD47zcv#t~1>0$P$h%L#93E)R$_nRubd'
    '5phQa<gcZnf?$93qT|x(Jcva?`XkbtgfFVdny{FJ;p4&Keuf$Fu(Ed6l+%n%V+|l1bcM~%ot|!w(Xmn*4F^9E2jfk~kgWW<JF=nic&)O('
    'J*DWWQc3bLo?UioUZ?61CiTM_u;ZUo=YWME%R~lacYH=>Uo_mu8AIsgLF~Ky;)mXiNe;rNY^`RME0OeRClQb?o_W?rtH|`8B|Y^dJ|B)r'
    'cA6ejJXQ>Oq5Z)t-Yy6R${xFxJrtrXyyA+=|2xZPy!<%dyR#e%<Ah4O;fF8KL(i1y+<K)ZJd{XGx&OT^(m~QVUd(aVZ@vW9n%WvysV@sl'
    'dIikP@-G2MWu=CQam4ygr~cAmMhYR8L`~{fQKH#tS~mvIx4?0>AN)nDc%IMN;#Ft8^AUAqTR9ZxMn;$Qd!-_m97W~h*9Z^)Jw3ntTT#7R'
    '<iAoY9^!kg&i04X$sSJeXRi^LwR;UcE5`JBUN?m7xfp51X)mIVs)A9?HJMZRx~B$G$gX!|y1c!<r^e!a-|e|i>W`$fcD-_<F5K1PTg{>h'
    '5RguO<(byItsvssY_H_WAF1BvkG~G0!{=qwJGi9c)~gyfd0Jw(lqwa+N7RgU5%MXyuklzWlUj5iKBXl5XhCxMQ5-+8DbM3O&FK5JPE4U|'
    's3W3+HMwz*A8#tzRnI2E(F^VW7hmVlqzeOt*RgHew(Xfawr$(CZQHhuJ9li`w(;gm7D+0LEV`=yKtFY!#i>rwG=)d>k6M15N87t27Y}oU'
    '+BvII2qY@NWKf>F3!gdX#@%DVh*{CL_8b*4uSr{EmYd6ik}_E(>QwfdPUdK1<T(L4j#PV(+HJ@{#N?}S!yDdJ-z?9u7s=Ux@wg{rb*=9p'
    'd?~2xCqUj7sl_%(mldXAG&~3fhZphGtyp{=AYw7NO}oj<_^xvFki8dPtp7!}{1|)%bq29wQg20JtElru{3V#z$gYgVHHhji?@>@z;z*k@'
    '&)F9A<-usPjONOQdO}?0%bCWo9|py-oRDi8YDJpzOC>J&^%v^LSF*UHd8bT%FY7F6tDj+~NxX{hQ9*bCX6$RKaj*}}vK(?wkZkRBH-j@Y'
    'rmRUw2RSfNA3|??x*tQ=lj#ot`uoJwGd1vc=}5rIhaIcR|00&wGk7i-A-@9^U*U4Tu%~2cU=H*TDJ+a+eYT#H7{L&xbj-Trsf4Ijk>Mt?'
    '$uQC2YhVAlY)Z5-I%aK04R~|UOq>`FRYGgs5dUaidEW3I)b4$_<PsB#*HFoD`Z&VBX)FCX`}B66E0!?%ZG2&~gKv`l`jc?R*%hxX>{8rn'
    '`Y1md5pOu{Ur*5$pq%&VLP6U<!PY7Nv{TDmgD8Dh8n3BBG;_^Iy+)Q962je;M`#m1twBmA)8fhDktxg7ak{g@$-6g)tP&GZ0$J2w$#&)k'
    '2ri~};hEAD)S*|Y4cO>%%h*_WT1%qh3M9@d52aAgUKAT~b|RJvy(O~zK~5k_p$+8~yuaJ2RQ$bz+Mm%qO*sHW!^hu^*-XCH6je~<%#<L3'
    '_PJG7%?@>owaoQg^QRh01tvgVTD82v?eJ@@P!(=6Ml*<1M)6^7oHbA)5dVn%wprQ858fvWkGGN<Z~N0@1rt+Wo!WjpL*wo#^&O$7i(Dh@'
    'V!_i>_)>}3L#O!s=K6<v9syC*5dEV)M*D<ZkzD_{D#<0CKsg)&1iIo?1q0WK=JRGpf#Kxo+iSvi>fzhla~`DyJCvru*}C+=J);Cql$jX='
    '(H#u*C3ox8w0ke<^V3WrKe;RZ>`^p3G1M^!bUO`dNvSvpym*^?QPp9985s`=$*dxajgnl{F@R6<$f}FyK=>cyIvr`V7i?RYN7<MapErmw'
    'pRlmCTi1DE3BQ7@bb4L$;6DF8QjFecITnGhVXx$*j`Cc_mWJz`Q!{BrRMv|{YhvXEAIOnUvW#{U1XJK5ZY>6C(WLae$M2gifB`)Q$JyT='
    'bJ}gm&RF~u&15t@jfr>xY_Vl%YS#*%o-W0bAaC3%K-x=2A#BxXKX8Z~vImZt^+Z655)_$Lk{Z$@Bl5nd8IS`14(qAjJimibnV^V&5I}87'
    'u}jB~NiCR~MNC@Y1vhYo2Ey22dwsl2rAC?oX65&O?v9~%xSS|HL)AMWEFtlpVW|_8yJN9BN@KJf6ZeIiW?7N>j#xDbxKPTc$n6a*Sp)-+'
    'BtA@Wqz+4<12GGs0QZo2Z*pTnF^3h>tK~NXY8V%*s|AfWUlu7O%e*Ub;NWqu1Iy-q-C`$sO_K4L6Wtfo`O~vQwh2NPlgK?wx66++2bk3i'
    '=8>IOx?~?*6R)bSf_ZIJ%>Fb2)ZFSDJYuN0eof;nV;@YH1!v`(RI15uK-*BTj&y{nFu2Wm&>NssfW2&dTQ<Ov4Z^6G?#DVtmr^&S!2q`4'
    '9^b{bki%qno?1N;_#c=BaJD>@TdJRW_+W0VqM@?FJZO>OJKtu1c=%J&<Ft~~OOGkCKT_~6bUA;%X%+po;IzUZ7L7pn4Di9!6ol4#EH!|O'
    'KYPtV$sK?Ck@Q;<UC+Id$K$Il&94&erUVz~mzG{9w((aKnq{6EMQUaNo>`{Y5Fa){0#nXuTAqWgZ~>{##<!ULFRL<CYtQ&8@n>eZTwQpq'
    '$~vG+T#Gox*?O>pw=eF5YWR9RKKfu5Iv{I_we4(qFfa7|r&UgJ0r>gu<Uku(FL@=JhE#duFF?Kne|>6c9H(USeiBDqS)~JG+@@#-l6uUf'
    'fLB4%yd2?b_3=PpwN(p~6Qx1HDQSl>Uiq)qVO%&N79%Un@ue?TG?B5pWq)qlcN_I3q@zzu+1cj%dNl<Sf*J{Go&Z&+DKb1jQOW=i%x0e6'
    '^DGn7U4m1Nm(<0izoWZ+(2Pb!$WLmsDSFb><gG^xUccf&BD~!Ie*O*Y0=ttXKLR|g7;4i*zryJGhCIi%g6at;eV~gx=}mHF?b`C6fU{)8'
    'NND$E+|7gmZ?}sJZCug$+nAe<jW#XuL|nA%^ux4%qmW*#IX)GqP5qWd*8aCIP65%zMcuc3v0pE}0>-J6KTNjW&^)2>66F5HyTYH#@E_l)'
    '`X5P)6ThY{&&dl8g@nO~QfM2i3JIfMI4xByWFBd?qiqFa#Z?9OX1O$*hm&6kDmWW)<8Do{9d)&dc-2v88O2;I18bR3ddG*bB@)9Pm>~h8'
    'Y*ba_b@q57EPA<y3MpZ~@)nERA63ac5J|NmcwZQzb>8}A2X`9lt8A5=l3^f!Dfvm>i(mo}O@SXj!?^aQu-L7Y4rgtlPQQe!TN8D31+bC-'
    '%YN)HKpB>w4>ig?yF$y>#;n~xX1rHoY+<0brNL!|sQ6D=&pU8F&Q5pzz&Q24eR~BG42trzpn-9}ZL>Iy`-oj4HQ{A3=29fv#*=D33ebdC'
    'wuCm{mZC%Bs%fFkMIAC#h~dLR^k_Z@t<@cbVGCt2FN&GosEPPG;p=aH#BfMi0ae`Y4|B;;$d87T+0Nt~x~LTZ6(!IlPpT?-3qr|<L;HUv'
    'vWZHaW_)U$rEuue;Kh08U7GOR;Wr~$c}xV+7myzVf9UNfN&BU`_Mraxwom<hY}ifxv_(t`<-GT<O|~x_4XpNv=I=-yAkNXy|9k&30J6HI'
    '*+WC6q6gJe53?6a^`+3R^|}kFf}i?)D-f7HTmJ@nCmXq<Dw@dC7TfAav_I?9u-0{kLZ69C#loO4&=GRz(UN$6Gh$dTy>v74r9gp^(cvYD'
    '50&FWyMPOZ@{Xpe(|7B3CAHq<$Wf{uJ4R%xVPZlj%`rA`_@QtJr3dY118V4ZUiMNd?;@!K6UU~eDxAJd_{W|@0(B+3B*7<_wNgsqeyffC'
    'i?utCrfEPpKay-SBOfaos~tD6`wxGdjB$87T6w5{ED%kjUC91u+U3vDpK0w$<1fXgyM*savZ(q;m`4I7Y(!EAFPijkyIeFMkFp*ir`l6~'
    'RE0CAQCgWAT&PiKFkagAWcr<mcKLNm3;n-$jF7!)8!dYx%Lj=QQi4?~EZGv5%0;dqUtN;iLoqbY?B0Q|O-$w@a?^M(n}}V`b_i$c7jfr$'
    'D<2lg`B!t+KAgB2(WS?T?!V<XP^!GD`qkN6Ix9FAx{ul%7>nZ-c0Vy}F=kKgJSF_qpL^LqzNvoFsI;^NxntsRDAaspPPc~}rP&+{0mb`3'
    'sJwMYJ3)JLMxH9sK>Y)xQ~4>^2KDO9eoZ5l$~TrerF&dHqMLwQ((~0(J{z}89Vw2Yu<5FH0&C+4D!nhd0<yVwL%)DRlp6q;K5B=cTL=6}'
    '{G7h3M$9!sjgOv$01*8ijsW7$j&0H@rY6EHUCjN)J%93PMYwKAVwnCPnX;NBs*3<=%mjEUDg_FlRRyJ?uBNWR#$DJ=%~2!~e<w<yT!##8'
    'JL(s+Kd65;&)_hR7KYwZVi}CLz{fp6%d(i~l1<!|L=p%en*7;m!v2ZT8<PBN<cHdoGmTRS)yZy2)U)3=L{G<$@GcyczEc54zkf*wvgKP2'
    '3r7<>u#NOqIk|l}3;!@jHg1KP_M=b!S1NmV$$oqVfv97r%Q&QjQQH5AAA%M2F_JY6nSaKaKX`4f-QjDaUk8w*Y5touC`5$Y&Z~X^GGe*K'
    'PLEFi7%C2Vi9cvJ)KGoOoPQauY>I!AdovxdCsh#cyH?wg_*5ZpWH_X$WkzoQ#ZZYfX(`RG&8>)QElpwh-9ezGX-tLotoPFNVAbEJ8|_X>'
    'pVgcyxj%y~&>B}-t?=(++%aWfyZ((I$*hf>Pk3;>K^OKevb7Y2gtE)Y*yf-7PSMhYfn*XT8C|>$<b9-43rPnNjAI2e^E1DG0~O;;8FLba'
    '#SSJYhbTCa56Va-(=-zyRsz%OX?K47)Rge&lp&>r87D@s@1$Cg0ohhJNYZ88>b%3+9W{<FJxe>MnmEel#KIP7MZW6jX>P)m2wmK`8p#El'
    '67X98DYmdTSL*O;C~pw`iod~>whj0d4F*@;l2(feZ}IFfL}2E@caItt{GiI9P(g*_gT|Z*`0I5^C(?SfEi!BujHcP&XLym1`za=*8PJ1u'
    'icxO1OE$3~cIT{RIZA7clnR`jam;Y^fj)@pwfirrO?4XdwKs1|*s$DzQ{m?FjMln!Fd6vE>1YX8;_dhpLWkjRKA&3A9^-H^Fn6SPu;Ke4'
    'EE*~z5^npz1LZo~&MU>5o|sl813A8DZ1@aO*LjO14)}gL!PK|3_g(k7PdA5OkO+(_4bPcG!K-riN5&SlJ|`3rw3@tRm+RKs=<UPnH$otZ'
    'GIGFnC!Hh6o!#ZS%k!?uSPKGO?1@*d&7^^8F63E2^OYEy|GoL?PNOUayQMtq*Quop(fAloJX0?7Ex*>xATbM}VB@FXV0de8p16rEly+kz'
    '`WG@y3S}v!D~GN*_*4-eB?V%D#1Z1-xmi&Is?^Tu_p(nhIfn&H%_zlFoL<yKq-MV2DFys$XZU(()76c*{5R^u)qbBPx~l)wLkXC5>Lp;b'
    'XJMP_K^{`1rX!>Zq^vcP8C_bLL9{*XBy^jHJiFEtTBnbO*$HK#Iw-_mo1h*{Db>H!LrL(PNQpuP4P?;-2XutH{=~<!ZrzuT2oqLR+;6JH'
    'nlOiF2o3<Y?FhD(74L?sqeTRnCZ#0Pkxqn{w+n%iwqOxSqXv<UIPQ_I{B{}zMqEtaQ{MW=KjX+)7GaARy11CsB9A77!fOGQ2A%ibQ5VF2'
    'Cmx*sPqr*ct|^Gg)UWy_7A}3W1j3~VeW?2>3EQ)R5kdyWb<>h|NuoI{k`@IkGepr#F0v?H42wspnw$8r3@=d>eFM^E0IkTFXr3K0Ig;p='
    '&%cjIOt;?{A&d=UOv4}#;fzUGu0Mr)oT~*U5#Y?J)gnH>LF3g$+N^=7tZ({8oMW{Z3)&_ruYU`;%v0f{1A<ieHlirM)yeHPc?JQVxp@u5'
    'EKY?CciCJFii~D)(gPRG>x7q{LLYZSbu*B0I3&zgJOrRCyuiK@Tr*!_507i%D38P9rPA?Kz@HpSbWZspDHcN-MnQ(YqeAS^q)%D_fvo5-'
    '$rEj^h(<fYMm)@0nD<le!B$KH>wcz)tea>RH)1<m1WB?wgl{mIMruQx6Pdl%6&Ot6f#r5_$85$tWBrK8B3;WHQ6y_GR6_1d)1q&Q8e2%5'
    '_0CcF#xx-|l?I>ny=>aYyd#TlB<az6I_DDy0=+2qdYTvZ;E7*4E;nMQvxc_xYP@ht_hMiy%cCv(&_Vdc1=<EX8g~=QDVXu38?6UeG#+!!'
    'Q|&L3X-1bHgE=`NN$@=F?^Rl@!sJlRPm_2IAmgVyXTSd0?OLO~G_lZC1g(Za(YtL6tJGvt?V|J-UWu78(jOR8(cdhdURYn}=rDVK6*Wq<'
    '=8%zBu#Dsc+0Du65);1gwBrfSSuTQuqs1A1477U}fdo6fbO@z!kC<pB<@zckPB7mvQMz&0AHlIDHx8wqZ`E+7wvRWnc`+~$Ix;wCL}|fc'
    'BA1O8h{pzHjei#ODaG|`xz^wmwB+ard4&H}Fa|zgcipE0qe<p~Y@ut8aZJuB=XRlZ$e-Gcxd^Flv}f<-&V%y3$w^s+AnAYrwwZ`}sVeLU'
    'WigdE^NP)OVP24xQW!NR?ZD`7bSj&U5bJrpMNN9GH^GX&Oo{%6+VD0c7+S8q8x%nPC~Vy|YSyN8$a}f_iRh5PelAxbG(5kwBQ0<oD0I*{'
    '1Wm6VLg@0&ya7y`xH>X<N9i^Wx%QmdI|L)vR6#NO_{8OLH?qWrH(}V{7o#rm6+cdz;T`)JfN3qRva+L;3_*<<o>i=L+x`fk#6nbd;hOF*'
    '<@>TOPK{IOX8)O>3{HYX$oV4KWmR4F8q-u8Vs6lTNRaiNGUu~937L@g28JqViCM-5Txe+#Oa*WKoENB{EgycTL82obW0oQtLhOsLYl<*o'
    'hU#J2M{nQ~QCuqO;(0=-Y?(M-JNpSeGqI3!t?&IqrVdh?wH1tn6`Pr~c^Ny6tlv|g6UIvMHVAX`c0y_klF!W8m#7D$%v4TI*2k(<cP^YE'
    '%l)o0d_WJY%Ze*Dajl>HD2pUH{P>$^V(}yvUCNB1ok`9SXE<$=%8<DHoL$2DT{yS(`y3y&JI(9%2+MAQOy@c=Cp&D@gTs}Kn}Y*CB`g-i'
    '|EBl{i2qvxFi|ZKmr;95{KsmwaAG)(n1K~bOChm>lYs`Hu6(e2_?<WQ!`|(yBkeI~f$piBm>qSk+2l+hOH4*34@5mN-D};pWRamjY!I@t'
    'A8j|OO=nL2?^DdMMVOe_zk`UM+^e~=$tV-J+LUP_?`v{$pE}_n9cG_vQ5G=P1WKp*b%~=l*z<a4e^>YHax(7mCz{@XC{9#&K6@d>f8J#v'
    'KtA==Z97nip^qr0ZI7}Eoi&0^{K=Ak?AKqTVb7q8!e~Ispp+0U<9X%sko88TaNMaRvIN7+$aD_^fE_(7T0FuCV=O0R-M*_dG0P-O5i-O-'
    '3^A=5JT@j7Tv!Z4{l{>hO$RslPgr<!l9YRhLm&!RVL%ZcN^~dVW<K9DfqgNA{)BPslZy~RXH07L{Y@7TWa$mZTm2JrysjGT8vadV3&rTr'
    'A$}nj9de^XlaCF2X^=m`%=HYNZc^t&KRZ(CC2;~^@E*$t9HX$>OU&$p^u~S$^@ohuluKP#|ADXF<VCh8r|1x#H;Oyg%5$bvf_u{@c$KTQ'
    'DIbJBt)QWmwZW10W;A5gx0Aun+9RH)3Zt;2V$*J5$Du(r#(eqjT#RLKy!iG@KJX@jOXW`9p^m`P2r{7WJ6mq?xk?~#ZQ3NB_p8Fqlzge^'
    'U``{L3d#e?-tURVKT6mS5iOG!&VqlBS?;}FFy5WjC<o4}QXJL`EhD40?qu9GP%7qFfwK3D+y4olICJB0iX+CQ9GAPoi`&TZdUusyR`6{q'
    'q+w$1Hj1@oYph}ILh0$T+dq@jr~9QMeqpJsX#;^1+T+d2Xf#_CFD%1n=wK+J68ovW%v1cnbe+H~9K|C10E$JOI`?jKXjP>F>2`e6qM#G6'
    'K%3O8w|wgWni4#|z#YXn^}9O#5;m?;ikuC((m6lxf#}}~-rsleJDyN4{%PDnkaJ?@*yM9%aScQ>BM;t)2G~*+qi9fSdT}l-w0C22%}OmU'
    'tC$Vu!Dv7`^z`Kx=UIXlZp^vlJg9Hc@0DE1w44&?pAtfcZE7Tg*ntYo@dRo5Z~k4NFD)|@H8vqr*Wt%vGy-PvP@;icb_)aKseOETR3|lR'
    'i~HYoVbn|aRzB9knCgAiA^8H3b0g`CVsxX~L*HV5I&+i!_X)N#mQc@UDz+ke7Ja0pogv0^x7AyTO{ZdG7aznHWrNNfJ(B9dV0d?12`Lp;'
    'X@sPmywDwl_&0-wT{T2opU=T2Qe)74<bN9Y`c2GZKdM7M0i^lxM3nZx-%*OrO}#^!IT*4-+=ITbPjQW`MU%Z%yOlrzNS6Jo6<E^l40;q`'
    'EZ$^%n<WX2(i}iD?XT-l+C~ZmjSJ?lPD#C5Tm`x4cr)@mdy2L5xl%L*mJZ&*)5z+2TK%CUu2`q_E?3CNy>`8poU@Wq8(zDrS4o~8^lVy8'
    'kYBABU84?2pw~y6zxzf${Dkk5^0ZKHYXc6$sxT0*2j$PlyXxa`E9g<zo72VaD*qAv>!kz7?untK&m}geiO|)bT1l!qN_76GV#Us<UpZ^Z'
    'DY~{ldeIxq5RAhZiz$B@CLr04Gn;h#J!rGq5cNU5!VSh+NS-+tYPeZ*FlG&olZkT2f5WW7U1~1BbjpF5kWCnbr(@hn1Hp^o=S8o3j<tj1'
    'Kk^L$Rd_BYFr=6kh#WX{dl!Zkpzw=i>lw8!P^C0hb=4RV<0IUsRxGJ~56Ue30w$6@7Fu7UDsL+`0p*I;!_+v4Z%<S10$K25j_+US!&NFD'
    'g3Lt0t6Idg&8EPayyurO&2m^{2ZlQ}oUo_a!B*gh9>TAoTNPYGiFut_^HmrmnVqz@1pi8#`4FhQw$j3xZ&R$z2b2*IXr4JL&3|V#ivMx9'
    '?^fFOul5>R$Tw{cDt#_&T5d4$`auV@Rz^+9z8?V|<&(u@k7h9D9~at=$^v@*nwNlyZ<jI$76snO^BEk)t44kD(WHXDce0Mf$j&;J6v(~@'
    'FPf3b(=qDKVOlz=^I@9&E^12k)<45rYrw(^Cf{yNS;NSs$BwhjLp>~0J!Z9?n`HtlMB{s2oi$l6^r+Z1M5tFUNjd7VwPF<PEeIU~t~Arn'
    '-6gZTrDHYAM{d&)UzynRy1QNGSzaQtNh-IE@q=-+SHi;yaq|)+yC=A(50jm5Jh*Uv{1qQMOpOQ~&xGv;BENc(3IoW@9FF-;2_~!Y?P$0X'
    'J#`9$>FXHx-|3D{JrW9fbk&J!CUr~O?KBWezLu%$PX96o6Y0Xfr*H}3$~R<`mBWTeUOb6h9I#jWBWdMfG)DgUIjM+2UoylJ+U!4GM~r0='
    '=9q)k>4!-w?ug8{JPxTC6A%Huuuefk&RW^Wef#%Uz_-ACa&?D2r3>h8M0!!nrM7IEl=@+%fnJ0=O<V$JJHgO<=&1qYA<yaqEqv<ve#bf2'
    'dN2>HkqruE@MXt)qeaPvjV=T|cuF`!6!ZYD-w(y(rd~ECh0G8OpBz43xmp5$0naF3piMv&`PHz=)e;<=KoJw1LR4d!Q0)z=M_&BnIPelt'
    '(g7_MNm>0Z`Kw)uvFq@3$r31p<#OUcL=Ude6~)39`obgoVoP8TX<B5g-Q(0#*LwB!27(Ut)MHVnswu3cX>nm_7HobKQqPx{^4wr@cTcpR'
    '@d<B{(#ZpQrtK4tz?M5cXxV@q^pp(jM3ugRCjT%sdNniz39IxN<Qr^)q5SXfk#&jEtc^@*dK$ag7=w6oPfX$NqcuBy{{VMS>Icz5r(A!a'
    '^k_7^L)3Nn;PIvr%Q&N-7fA|{zU1gUnD3H-cINF-Z}moUTLLAQF)nd^c`O57?<OQqMzKmU+S(Vt)@UKIWp03LV6TM=(-P88cA&0)Wt43l'
    'DTu&VDv)BmlYLjBu9S$0tIUTm$AD60aR($(RKzJKVfZ}s=qi8MTMM^kdoXSQ^x<KlN5u~0!47X^xJmk^0VPZow+};EWxMvOtW3C`=R$vf'
    '%BG1sQXMGJy^OwtDAmq#DEfX6#5itxDb5yo$#0gMb+H(5`b>(2RHW*d(zG|N;NAd?n5>Z^oMp`dXF$^g?dvZE)lll`0RMGWZ>U|DChu1s'
    '7|U^yOaEp={Y{cD@G<yd>wN#h6KBNk-fYuk8G0`~tc;WhB*QzqE{U}X3*+S1CQVNRoejd0^8T4x<lqP}*BZY(hy0P#vB>WZ1Pb3FQ3LEO'
    '0+(l2X6KQ&U69g1VEY$0SXJ4Imbm>ni}KV-5Si!rr?Y|q^zC2f!e-O~_jr3f-i6YwoKhRIF@k*x?Oua3?bx7cl53utgQrdsh7s5j3swpu'
    '0dFqQHi9=poTw(q>)p1}83&pRWf69+b#;d&yN^gM!h|CYq`0l^xh`=dSL+6j!&28L_S$T;yJ9FXb5*&un&X|N-KS%tOz9P86vKZ<ots~7'
    'YnexWIaj(G@Z)VS&OcZ(Gse06qP65g>w8x~z@_&&pwMCx8Jkf}tlQqS8L0tuVZ=i~*@eAhlnOOIZui1n7jr`iIgukVc38O6_fxZ#*s7E2'
    'V|SsE=EdTkIH-81xTG2u+T7`!`^KdTkAnEMjo+lZv<yU`Xatn2Cc^q?ZGET*AEkLZ>M8agA#^ntR7y3n^^QBkY@u{CySnfMAMYb6XOWdv'
    '$pO6|M>%S@HMnI=){&)7Mx_KL!+n1XB;Y6q6EZet`wOhGSjk~M+Q?x%er+Az3Pe;kr+IL1?cyUYe?RH>S67iy)im2c)Yo(=SL(Eu?%(Z!'
    'Vcqrg{h6P(^7J7WaFrtdG6uf8TIT3Vf7Xi&r*rI1m(<7!jL*2EYBw&@eg2BEm)Oz`Y*?a2y0w{eMZgnnCWRVkjI@fa@gYn4cbAJCbsq22'
    'Bda;H`Fegt^-eeMQX?V@F5DufCg7Kin3vsY3oz=3V@&Rk@U`bF7*a+-am6KR%y(G{T8{Yyhn|l{v-HibXNf0cO_NFt@4G1XqB1nkbC7f;'
    'P5HI$l3a#8OQv5rDN(|`K0rQHZ6^lS)4E<zxV_K$yXxwuLP_*d9K5xJZ7|AWyTXp$9McEWS^chGn&_ftVu5+=nW-#I(V_Axwnu=)yLlT{'
    'LL%VaMC#&n!-Pgd<xPq6HT#}rseo+_M0-*rT98YTsT%tTcY;2uJujfis6XDYIeoX5u`WuGe`r4obhPl6?hYsSa?}=7oBVJd_uftMnyeRf'
    'a5%8q_1ij$3kByDsfff{Hap@QOhxa$tB1*CKUA*kfWuTXj|74!5$s4STxiMf5nDC(W(Zzp)QISnJFm9jHPqtPjm=-baaVY!Xk%n`RXea~'
    'pL?`5i|h-{-fBUO_=b2tAD_FTvJ+UxCfO0;)2j;Ua@ZCqxOMP-)PF0!C>P5=7gc|lN><$%T^xU@u$8!uE|+->Pn+C}^ZIkmi_6GbwaiP@'
    'KyFfSR?fUDnBs(#lz)Q2f#N(H6rRhVdju<nk4{5e1<?-2mV?{o*I>g-n$dLG(~;h7$cHP97+_S8A$`Rmy+j7{F!@W+N=ugG^=<ov9_6<J'
    '6{h<&5ei)*vZ!~GyU#_U&N-|Ofky{Wuih*!$hUd*{F*EFb9Rd3j>2;s{(b$4MQwdLwef)M9IHV7*>h28CFhZ+yKzQSrb5Xq_c3SLg>G=G'
    'sc_r_HVkfn7EMQL9WW*^SH|6+99n!7@LU;OL=&&qfogn1D-{Gd@pbBh{_bn14ho7{(NH-Qbx^XOE2pg~3g}jJk?paiVh(Pe9N5%z+)xuO'
    'u55^a;+y^}CjT?Ocwk>|`;nW=)?=xknhdM0=St#3XJM1|=UEtIO5zlxz<j<`#a1`G+v1=}2=Rd~j37^lDr+kZazxt(BOz(qvkky_9+5&4'
    'G+C;J9WA?Vh1;lt+-y`g9>D@{c!zMOb_T6E`L7+${^xS%(HPlxZRgO2UBRo3Reo>aGt|WH`X5hk>}A?qTds6qYd}M7%|As}61nsD4+XpV'
    'yBKu_qZlgi*S#-B!Lij9pSX$i+<akqVnzovEMfYLw4y`zcBoBK#x|XGr}t?s#D953EngN^UfF1q=a!83Tk^1^&@OVgPr%yaCAAQtQQeuc'
    'VI@u|pAU@9XoTx8{f>}q^g7D%rVd1HUNp%avYNcJ{s$(3yXAuheE9IqWVcpJ?CWWO->qh=V<G7Qnm{|QNR>4{ftM^<q?d-el%*0#^~ETy'
    '-_YcCx-F4E$d3tRe~TqUw3#A^U8^Ah*)$4OqxrlYIK|aFGIk&5&J}PS$s0aMpu|e)UPk(YwmXb;=ZvoLZdsx2r~wTf(rrk>S1xQru4p5w'
    'Q^op>%3l=!W*yI5T%-m1s>I+z!9!Y%LpjyF5fZkFrN{$}RqrXbwClb`D4T0I{Y&>9q(0#~bYryOna0%}O%r&JXPGh|8GyaS|Md1z0b9Ku'
    '5OO0@twGa@DmE_gTR0<)lil#k6fsd!U3LM{C%60*T1IzPg@j#`K3qcsmykGJ&~GW?^q(^M9y;ncr!mhLsyr?Ig+TzVAZ%AY5IsEUaouId'
    '#xMkO_g!69s4D&sCDkf}bWoB3H-mXf?3a1wAfhr$L`#Xh2<UGUrsk^%=Ow=mQis}y<^7<qkzE0t)gW(qih}c>q8wui?{!+BcrubG*vuBO'
    '$G1WfHyf5lwnBrpzSDp=0Jnh)tJ*L*emWxD`wDM*v}xZ)Uzz-%ECmpw`r(hveow{?cjde-yG198o&53wM4IE1Ze=?m?hKs-imZ-QCJqMF'
    '*Q-kN*T2nII?CCKfIz;$UiBQlsM#DhwLS93zpv|gy$e_PdRi)8NrUn$F)hdj^~PqFkyRi_|F2Kkh%5OYgaHBl&-wrRl%D_Fr*!50KR%`9'
    'e|zHG|Ls$X6cZDpeF>obFQ3wQj0F&Q^?I`N_6>R6@!GHn$h1eioaoxw{+$G5d{6uZka)Mu6pRlD1C)NIzB{fHW(*zyhy3yW*#LuE;BU$Q'
    'X;WSgoDaMK;@;a{gik?V-hTH!8ukFc0m^%u0ha*tH_>0%?~b3l7eOGwWx&6Hg>S%n-Ye2G=x@xg0idI$;oD&=A;jQv;9Ai37d*g3@cRoW'
    ';OPYj(6D4MaeElh0|@x30{{audOc<dRsdRWtP2Ac*}1+JHxY+`+TTNeD}R*Vsb9emfkuHHf1v@qUyWbhua29&cg8J$!9mcEy_da5!QBAo'
    'fi*89Z`voDThMR7SHLIWuAoPd7_fLR{)%Wwcpk6`*Z~B5&wU#Hh5!UV3SI-+1vUjm0F(fOZ-Y<5O@~H>(}ESiUO)tZ9x(Tv008_J_~{P;'
    'Tz--VbOV0#-kiuC=2rU)BRz=YHms|7$bP|b{vJXOoj>dfDa11h3houCcs~eZiQ6`see$jsAMES2^1N1NmQRnQTtCFV+<#A;N+K~r6gc$L'
    'c<^u6C=*7{#nOwwkQP{@i^+6<fV)!Hs`?kb{L95Z$=*={*Q{`g?wdO(<S)fZ7Y5|7W=$1E9-HG5exlz=n3Nue3p{aMzd+u!b)6imI~nf?'
    'Q9wo6F%H0RXg&cHYR6w@#ZeYi^{+ox)0qmC<b4dJ)SR5l*mX{}9!-|vC-cEx1=NZTpvh;WrUf2EGEs-ZE#w|30VBD)8)bhf$PgRg9RC$#'
    '(ct8S$Dg>6pT?$|iqT;%d)@*s5*^Yi<K7bi>!{65-~52#HUB=aCppK4ljgmAH2rtRnjvX1gN6*Y!jQA{VO0w!D}tGnINGyU2N?ef80!xp'
    'a2lW^f$Lw~R4{dO-Z!+QivB)@BC>>5Nj!MDR$oeLLCLg>pH~08cm{i!xV{WfQ_xL;JOS&gsFwAdT(@uNsBha#>MFDFEe6V!tu*ORJxBlr'
    'Gsq=@TV-uAI|_l8j0Z;KR1@a#u3LEtG-*`TYR_jDZ^JIqdditKsm)^d<JN^cNw4R5)m%S}Q9@%qXp$I-pC%egHmrsP{I$uap#3+9sI{*<'
    '|8V-Fp~VN1*;{nQPIY{i*`|Mp7o3iP9>DluwLWnq4FYyBZh<LENeGX#f>mSo_Bc*K7+B6kPFYsgmMu9lALIEpK|_sAZaNIs>k!M9x50^U'
    'y@!;teu@d_#5YcsH)S{9I1?HG@N4-bWjfPQ{1TgMTfs#v`n5w$g`90v6F-^(%@7Y>xRumAHtJ3c4`hzMF>VH%yCY!nBy|Q`p3pBA@w_Oo'
    'obs(0j^M|*cg%THJkSaHI7wE}dKw_aVCg<(SoLqudb~~99n%ARAMMHo|0r^K^u$mFR{%|n97Dn;255N7MDVlp72XuaIyEvNwnrD!lbXcJ'
    'zuVZkQRQyCO$(NL7>ECDi&`eIPaDGX0sXWt2>J3OZXp4wA3Hf-Sznt9HYJwO*NDQ0Hvo83Ztkkv9%3`$Ot%kvI?*@^9!s)(d)OqHLO~5I'
    '6wwCp5$#C(=f@~inP!q(?ss)|p%T_#gZlYu@0>qn+f!M>*TK^t97jJ*(&-$};^;Vj-`h4BW&+p8CP%*AF{NSKxVap6W4qeiLSUWKiQkW<'
    'TwH)eHz_wda73Z&jnS)wiJh%)aN=XRXb&hFRX%}`|KY0sIG8N^h)m=SrcNU(Ur}<YEY|eki*ShbW9R0$9_XSNIk$doSlVipmuxz*QR-Ps'
    '-CMcn-tSdhe@T<RyHEYV@XJnMlt8=@Jh}EQj{4!@i|R!v3A(ZtwOiMO6ClA0sgoMw%)cAD<qtO$H8wiGVA7Ktf6rVa&vzsk{ipV7(r27M'
    'Pwv$%T6u54n{l0jv>eWYh602sz~Oew1+7J?^jvnJs?DYGq8M(LL|vOut-lhew(~h;WuvnU0DZ*beGR28xUYjvySem3rCNHr)94q_uZD9F'
    'L99B*BSGP8I*{GWdS{J%?fCs$I|l$@i+yl)rZ2aKX20bTKgu`0BXW}cnjY7*oyE$L(B7L!ZPuk}i=WvDW`$j7)vf_y`On0!$;vXYOw{}~'
    '-Sb1p>c}CfgdIVfhBB+XO1ZM_E;(eD@y!Bebu|wY%1D34V7+u$4WmorPIc9ul;XYf=+WlmPBEu}{@1rZEd>novf0bqGE$p(yV=0y6)&<M'
    'hmjap-5A3g!hA32NQR){8`5NX=lK;v${;$RDuF3OwwGkueGZ9mM(j)_ie^O~$5K^Xih#|Oxt>AXPVZXqKH}qkUaT?((oqi9Wl_#kG-?0I'
    '5B*EkYi3z9!jTFuwUf@uCP)H3dhh7}3P8n_K0p}apyo^%(6M{H;S(EgO|Ld<qDRJeF)(!zjH5{otp_<H$j5-tzZCYhv(Z`r#vp*;;i@NM'
    'j7MlxAvD}fdfdn^!2E<PYl6xrIbxXlW3%wHd-5w!Z3l(-t&vz`@Ppm*p%KpEFtBUY_omNPsM#AIZP)`Mq6U31W<tOa-yPFrx9Tyx=Lrvf'
    'PMPhebtcXU7k~oC>;M^gWJ(i^PA)L&k+JFpe2dlAH`y0(=r$h_<bbqhPAgQ`5)e_)fP7B)Sk0-ZjM#nAm(Pcx8S}k*&3PGoDK14$84W&6'
    'gdMdSP)y`#H4m;h<`2Do(8a9sy*9DbavUW&I!Vndl4FK4@|Lur;ScI8ON#^0=&)OKsfrPhJg!c`HsT&tAnXh;dIfL)Cw^3v(N&La%-2FE'
    'ErVJFS{6l6y)J5y;ri`h=uaD7Dcam(<HO$^4}mE)MZ@jc#nf(4f6A)SxnuxWmtVSbi5pnxq7;&zyAk+=mSsS3#Qq<}-}iC;MdU*&a8=fa'
    'R}NVA)HOQ6Re|O3Ki$xej(P{uDP_Z0EUx>!r=F$icy9V82$XoC{C2I<vdVC>H9M}t)1xBmCpExfyrADD7gaNddT(i&X=zerynJf(yNA2o'
    '(JYd(H#oz!i4E8c8hmh)HdtZO2-aPlHS9%Ib(|ge3cMxPLjIS&TeZk^rTKQ<;CeP!Y>@|&@~Vfz?t=Gjz;yMGQF_B6e~k_$!nA45OT9x*'
    'yo9U1N3R17^HF0wu(sK`Tq>aNv_eSbouLo}&)x&HE?<y2{q}Z-k<l?b@jX24ObfC0`c!iS&OSt0B@~Bo34zyIxl4@@fw&C3YmH(m<)PM3'
    '`Ci@?rhxF_w#4NgVNXX@tH{qG7(y*^lxKU_7QE?kR*{(Wi`hGXToJPWHPBw_)n?V|dcDjCQ})l9+PqUAXw3bBde78?1Ye#Kxc>0gxV;!!'
    '<o%ue7j{115YrLvI4yD2rIPGd@z8!%D!0fo91Lya=eRWiUdURlZcSy<%A-{})>d~tmpP04>J@AsVzmi!clKa6^zLsSF4Nl9j%%V=9<1aM'
    '(tI|meAS44(IEe4l*A9+g@U1tWCVDt<!pm?F_7o$2ez{m9OD&fKopNu>)hbb<t-R~9acd^T-wr`Cfqn)IbTHkj=l!uvQl!0+7L&^!)6?l'
    'M*S3CJrKN21-nc1p*Vts`1v=Kr#j8nXu57Sc6!Ke1J9>Wf<!?6S5eZPrLT*!pIs<oM%Uq?zi1a5=5pb&8pc67WvQ@s_sri)<nx7=sUmSQ'
    'qWM4RG*@I$;|aMo`41xSI_ah_VWScoDSdI!e;)9ivN)Mm`6Fqc%j+>@gXXOMytPo7BM(>Y4iNTn3J~W&o^KN3kXy6@#SgOBRC6E2D>zC5'
    'n=`29vjwnm$ZjXC<?6XTgB`5d$|0RDm@t@Mf&Hbr2b%6^jYxhhdKm70%2&iF18MjCF#e2Zce>3tVz@YrZX8LS)-DUO|4L9qksC4xGzV4-'
    'eI)Z}4-3cdw~x1mmY)<qM^MMhKe_=I7<-;1{jHl%ljv30n#{<~M-<!@wvow1Q4OnJAL~S8nnRG8myFSr@tV|3JlCZ(7VpIS8)qhUbcbLj'
    'p#WHY!V7OZ-UF;e<1ux*<qarno*F_4&h9-zwsEcsj-UfVgYn+Pm|3dgZUXqN3jS#$t=OqDLXN7wKJacTsw$U`eU$J$(}RbpET>2We^*}w'
    '(+1^@ypa9|#dulk>E(iQrol&84K(u=;!?Vkm2)A#GmvRcYEQ=|<8lx1OL86=LpmeXXhD;bYoz8uRQKuEgu*Nn)HUdxPLGkqSmFZDZQP4K'
    '#gNI4flbD7$l1_-o3D6jw%^^d)A?*eZyt80t_d?%cZ@Q{p0J@yph8k*f-f8|xQd-ha^36HILReUwu!gpua*3jT)^4nUa>ooUNCO4n366@'
    '0-NJUSm=hjlXfd=Zdw9+IKyNIzs*atc%N#>#+%5D6NjaH>l|gBsZJt-loK(pN^;=PiZgOjAQk&uV^ZQHK7urKI=t@tLf*TeKQntqANmdF'
    'wY{ijo|v*iV$MjBNB(f5!nm|x@258FEZjRL<iVzQ*(>H$6oftFUQ%i59jyq;EiJ#Bi-%FfEsHgaZ&W-0V1X`H65lt1hYYctu~ylWLCn43'
    'Da;g*g|?)(J-kGk%1i279MLX+JJ90NRQdf3ELNz{9tKY8SnUvBoC2k!75aoLpgp&X%iZQ<ZGDs<F86p0w>5=Y95X&$>6t@Zu#}lOgQ3X6'
    'e)ln>D~wtX(G$?nK-wPhq0l|PMP#&N@{_jWH%XBtc<=ii@mrmt?mb+scIH<Y8HP5Ap68PUQgmnK9}VxW0zVP=F--Ao{Ql~1gB+XVN!^X3'
    ';CawG07p}Iow*n?J(ymV1c|8=c$MC4?i}35R*uEmc;@oyq^ELIbu;ugIN^XAuzy`cBzZI<&pjc4zmuflZ?)FJww{kae<mAt@MO?yNrwUj'
    'zFoU%85o@OV30JVHC@JD&&^|S$;N|HD@WI5=Y;P-{w2s8tHOQv9NzmK9uce3V~&|UTnKWh;(J)kzB(s)1hB_19~2-o<WxxWY0Z9*wn1_g'
    'KSEqIfOquyfj4QWbusxYlQ$%PU!^!Cip2QmlQIFz%->04zjrKC?xk(cm+K&|pV({;^P@Q#s3aWGdFF6D27>nfa>l}yIEjLJwIKRf*|p3T'
    'k}}_FiZh;r2lg{~5)a@eY90xJ$Vk4{AUITVQlobcZiuP0;YiL14ds5DY~1w|Y@+dWpUMfJy(4=<w;ax_N1u0NHQ|u~vx7DoxL=)BBI`?4'
    'hE4kliS~u)XRBj`buu&Jb5uedvTq8oWkP&O=|#IiA@*gXb^CLS{*BO7u;RZEC9sL26$!)uZ*zbrc36wE8vG4;6r}q8cX9hILiCH&Yvqx)'
    '(n#24g~}Cqrra^}$A%Nn&Kc*&{CeP}PDLt{XW2EI?`{3gs1NgK0s~&&ONxP)^h9q~7}-P)$2oV{eeHBXFN4%ji<q>%lm%$>Z0=6WGd=D0'
    'svq1g`lQ@FrtEHDci}ozeV{#k#WLKKT`YOzY1vk^w*Y#g2GjkA>0Es?t4PP0C46k8N{zSG)Izv``yUONDuQYTV^J3P4l+Khb4Yf|?e0k2'
    '^<fkZmfg933GPE^cLk5_q+s60<hVgQyPC)6Q=A7+;M_Iv+F$xm0xSL1jq)JQPg*q4D-_(1GCaWyTSD)~#(+;GsmG;_?!cN^)|T-g;KZ=v'
    '8kh%{`5qK0EK0uzIe+AlvDWsdIr?A0)zx<PA6PJuM}mEjvubn0W4LgwdTEb8>>W6;O;%|*O&!TXD-Nw&9_`R3TQ2&|Au5qph3yOee~GM?'
    'r;n>eOeySzY*vsigP7wFU0YkWwv=El`OX1DXz^X$s$2fjyKrLQXf2~sRW-7D!(cr&N2ufxY=R4+z3;XVQuDJfqrm}~UZSq1Oc@|sH;|B)'
    '{Px;eeR?XiH)^?}(U+7=eIhxbz`5Q5_o??5?pn~#8skU#eSvdEs_Hl$_u`LDWiapcUchltI<?0N)CkX~X5$<YE?A~F)GNV9ktycYNmce2'
    '`8acI1N#eWbzSZR;gjvwSbLWCdiD<Fu*k3wic;rwcG#mHI%yhnb@MiDCUO;riVPPoaCI_I?=kbTa~9>dO_-NLnxK5&rhXDqb2+4=41*BN'
    'G>Vi&y-zJ)5*J>p_f~GoRyS^i3aE@OcP@8{r62|}2sB%aqg`3jB!NpsH}&*IVr8SHJ8#@P;x|(|Da+<seRgL&lfWN6f4OyL7pKo@grT$P'
    'a}P8Y3Y+w!&|XozRTmJ5BtS)|H!Fjg&3vaBJcnCT6|878zpx_WQ+h&7U=f%(6|8%|e%kVFh1hAE9q|Y^_bkB-4tx0-c_7)C?1wdpdT2it'
    '%@5yNg%0(tV){9cnP8&8nU}{fo4AWoT~4wyvZY!)m&Q~eAQk%p8A|hqX-K<gl{1AngY>H2wOTi8YrDiqWk*$k!_wUE(4<ofiVA6>yj{A8'
    'mo`n4#t6b7byvrs?#h>8Zy=Y`)rJx1cxoBKg5<=~cGWLxFwAG;8sI*UQ^i}8`D@UbQluiO);Ld##vj)Ardmj2P<yaL6CAx0w;P5}F6|+H'
    'Y^G$v7{1y)U>GTyI?}0fJs`qNJgEn~u7JA7opzHBM;_yT5%lj;*ALN1I`FEkKEIcrDwHdOv-GD&oHxjj!BBD3Wy-e}mlYF{$M-L+tBQKd'
    '5<h%2mYlJimdYHF2cn*TULft03ZbmSQLgvQL=yJws5t(SDXKN%D+Uw8{BF@PQS#=u9QANpa!X>yb}n|qK~xj_!ao05zG|l}?t?En{jU-x'
    'e>Tdenyk>^IE)5GYU;d>3SoB*pRXrYJly#9W=&dIx0-$g_>Typkxjo#EpnNEAIx{q2rsx<T8Vu06x=>a5gQ48eBzmtYTZ6zB2O}aZSY;Y'
    '<80C+k-68xRnF54isM%RLa>d)O4Y=mPZ7(O6st#$SJ(5Twh2!iDJqYGIoAE&yXe?{9_J|-cnAdd@zJ%$s|HoHjPA4$yEZ-bnb}gDdaaQ}'
    '^Pbzfjqbbp(qEf)1-62>&A`NFZ}3dW6Dzu=+c24246+jAruq!MKGyuNkwZ%HY6~8s|CGC;c%>T?^P9rQ4xv;;xZ8{=md$F2NoXxyPx-a1'
    'JPPiL@hR!f6M%q*{N8n(!+;@%*hjBqXz`{E-0T4`49ZAv>f2Ws8FOOy4fTo-GCZJ@#q%e%Qt!?+%hJAzH`6eHfGhC+EJ1PFtB)W^`KPq2'
    'RSUNf7feYf{8~;>;UtvSRJF6DjRrDP{e^0{>WxlQWxy^*T<63^l>M3~h*<G1cVgZ%1FNz#IZzWLLWADhG#zpSo800ywx`&+jQ_!jRBMG%'
    's9wq!8>kD<Do$h|PGgqrK+9+})ok*PDfOSY`Nta5S85Co34U%0j1t^G9j~aHwQJ$qOOe&DW4hWFP}1q~LkSvRqo9--=9mD-{Cmc?$t3L?'
    'wz2HXv_dtOkF@dQKyYbm_-`c8XeT?_Kmq!(``Xr(>01RsU`=+eY?t>c`75aTSYgpef?r-Ph{^_)W5zE@q`bi{={hsD@%!t(g${KQ$V(hf'
    'I@TC@{i+VMd92!I4PeDi>&*l#ep<5cyWB=x-UI;7Yv5T%Ok-0pt2~Ng^Su%=ORglY{PO06ZnPP3WDPDMwAcj(^|IZ5HK-GTxLb-}$Ll3U'
    'en0TbSc86BN0~vi0ZqenXVK04?D7IZyKF3ZYgq0>W?Hkwq*aqX#BfoRj%b%s)X3Gte@UzN?rUY&>h2^H{_YIUJ>d$hYN>lIssS<J2I2-G'
    '2mtOPZnN{hpXuW~*1)A=HKO=t+JdR<m3>L>-WDA?5OaOv=1MxFz&f5y0=anK{wZPJYL2Fj_yN}Spx}gfM}GuH9aKbRQtZ#>n`@tNIExGU'
    'RU>2^u=FQaoaswe!=@Vv_ytDYaW0ZmCDa%<x5lTF+p6qy2Klq5$c>hFBm<?7+mNQ(ZP-GxqI{k5)>q=vV#k<`TcAS}zhKQdH|CbJ8Q2B8'
    'C27P_h|F{azRWetU+=kTN@n8>vu@ak!t)d9>%biEuE!Za$cHQ}gk)?b%YB5nGtVR^z@2boQIGZ~1jfr_`|rS4#VW+*tMY_a1orBH*7XmC'
    '+yRDxESRyDTnJXLzDKZF-}v?+uoy{iKZ;^j&hTZDoE8i~Ar_H8V8m1$@~qgiRJO8`gZG8?G7(H<7n|9CfL=-Gj8D9}Ad|wcW=WP6A7^)S'
    'RdKz1(F-X)BFh9PubXeVgRYM9{7+aQ(xw5kPUQY~f4itmTaoDuB)R3qv`>&=*Ojm-|L;Z^nSb<PIEv~MrnOk`evU7xqvUq^PQZpynX=l)'
    '$8G*+1Q&^Kq&zdsE7#-F)E8}RcbHX`AF!Cq=q}!xF42XH`}e!^b-;V3A{6_^yXjMnqt!fI4Oeb)4Vmh_DB$6{LHzXC+7;?<80&rKW)Y!l'
    'U0hFo+wkVI%6LX?c{1D46?X!bTPEh=JGtnAg6?cV53;;tzeO(%iZ!a&r(X2M?Rf|Xl9xwW!M)x$KOIZbJUIw#06_iw9UZSF8-l!;&H-7k'
    'Fcv_V6%_689k@wa1YH00m2@XuP8I7dP*;{bY8pqN@^d@;>Zp`A$T-G_S<xqvpS;67?4nToE6HpYfWE~;9b@}xSKSjOjA1~aC5^Z7DeeaU'
    '8>RcA>fudf-NYss5DYlxTQE_OvBrK9RwqAA9b4}-Jqw}1n@%qZmEc-bV3sNycIuhZt#;B%!nN+ihR?a__Qv?_A%7dkA_d54+{aRGND8DB'
    'p5J_L`}ijmCP1<4Y@lHckZ)`&5&P)pCq{vJf-1N5OmMat_z!vnMW6Hyc>@n^T`>g{(lT8_*A}}UG;7v+*5B}0p3h3Z*F3S&BK*0#k36_x'
    '0794@o6RI{t{zJt>Zh$oxxEXe6&LL0pyiB8{HHXyyyck8G|x2<aN3JVqA#Ro1%)x41QU9)^YOWt_|t*`KEM))2M8Aa6xM5#kvP)l#y5P*'
    'ELv0cI8SFeONMt5ipsLSYd|3-rsfW1WoS8gVwc=~Vs%YwCV%;{kie&$Z1}1G+!%>hkqF1`)hrnLLR==op8A}#@`}vro;%LHV~*<g)v@e?'
    'z)V{HE|Ndnm5mhMv+}xsd2{RJge2R9)F_M&bM{K>R=b-KdMKic8>B+zz)u-abfFi^?uw7U6UN=Si?2NPBfpMy<#&JYIsf7zSP~mCTR*R;'
    'x3UbfESIrQWk*Lc#eE`he)M74zkkIl(r$D`tNQhL&dW{tq;yjO*@AjPh3U@OItvG1ldKRP^k0GAML2o1(hz}SLiQm%F!BbI0%;eNN%@AR'
    '%Kbx8q<Q#49)bA7I)*-A&C{$JvtX5EG5J@L?|%?>4^5T;ijsiKwr$(CZM(W`+qT(d+qTtZ+qSLq?w!TFh}q08^B?5qi$qfHYf<BRlSZf4'
    '=QS=olDf6!@sd_~{o8|>$TqKd{a48BK8KAalxR8ixrvog=A-+q`Ywo$d~g6P*M=WyQ(W|svj6wHAVl+<_Ymm^%yaRtg)kA=<;RhC`$K-='
    'EQkpjH_I?3nrXIEZrWUTpp`^~kv|P@i-IA>HIhR9+uv=$Euz#X5N&+`aih`vABa@&Es1$cMUO8V_vf#Mszme?$&w2sWzQt!ikAmR@QlmJ'
    '|5A}aH&7v-2`i1%J(kGX6~dB;wde6bH@NHMXf9LVd<;%gHdOWJy<BBtwe$zeWo;O)y+)aP?M{>txj)k_^HiP)^{QNSvGhGrMbic6W@G1+'
    '=eI_94N|oJ1nUbZA(0~8>a}E=u1DgzjIiJJD0l6F!So@A^w{7#?I(?H2H14EbHduD>c~~KpCn62zRL^n1~NqLzvE~!(4q_oI>Q$;pRNjj'
    'G#XKnqtu_&FbhCPQ^a90pl)>F*}v@^e*d1465zQM|8TU~ZR=9H@3$Oid&VuJP1C&e(P7rFF5lqmDFSykY%e-Ue`|yRb~fP8VQEVZ=5Tb_'
    'OAUMcp2Fz#Jamdbo6m;1S>)4FdD!beL0WJP_`6|Nd|RT5Q)x?2iz#FzxOp5vXBNE{YGLK=pWc=`@Zb$iDIk$xdG8QWYHOmp@}Vt3#81H%'
    'zU-BH__FEL2gd*$)?(SZ?u`zlF6G)<F*WxB&c2ww2eII_uQc5|yx^|muSx->5?HuG^8&Ii)?J9R5<_QRNj`c7(`WOiIOCsv$FIlQ<{eSV'
    'G8$-rqKA-g`)xGGQFq9Ns8d)`mvo(40|^!phChdmIG2&PUL|@fNjXDD?vq=wZA^!{SrNMvmhXac0ctY+`q-WcJSx}2Qfx^;)xsHfWC(xr'
    'OGL)GVQhy8A0K@s+CSxj&UWq>nFss7Bk{rQmZg&i^Dw>B!7|N)bGB}3fu7SOZ(sgs?OV?}?_l-v4YqvY>@Zi?xRs$e$RhgO1~sHTS>z`o'
    '`OJnQ`k%_<4T=T0wdDj4%an?jMjO2q85^hyvLAkTK#n9C#sNJlDA@wtc}lvrkRn1JZJFHWa@sUfx(CB<5>$7}v4Cb{x#bil!f|?G(`5@a'
    '{4K5_-c=al`m{&Q5kH%^=8`muj67ow5|a_)0m6N`+(D*s)VK5|Hd}hCmL&VqyiDDvo``IRv%uzI7kHag<5BJ*{nxqbkdkX?D2Lw=9&6D4'
    '!biNtwNErj{F-ZIUspD8rmsEq7uR57(lh$6Nxn2o`xqTiE)@|4(Pqkc+QT{fBT&*bn%Z9ucRekqE?c$uNlcdsA|~IimK(!`v;AKRsE`)`'
    'ZHnOOTeQ$Mh>GuG%<fq`_p1}a&X}QvA8&V+ROFAYuaV^Vs1zc1b2(A9B!1)rJ|Q<R`N#kj#F3L?@1T9WF#~>6-%V%%WSOdP+!I_~<4*f7'
    'SbvE-lw5Zs3a9x&X6C99bzY3AOO4v_1*@BT(O;gUO9zvG43mkyP6ny1D-olpJZ3g<@TER$6FecPgE-^hMP0&LFjq7CdRk|XPCiQcy+uz0'
    's|t?jP+<@EUew}XAupSVZ1qET<EZipcp-6BGH|?$4Kj6DK^(9jRoV?tSsf0ctoOc}R$anp_%leV89ja{YJ<d%GQ1QYrj#k6f#0ZNeVlb='
    'QbplP+-FZ{GsY4`PRR%Q^G4aVn>IXMvq2Mcb}e@|XL1^d@mNZw*~$hU?KY(%GIvS^p^bZ<%`RnB<xNTZSGC^Q2ng&F{YzmV7IPMX+XF$v'
    '#g*HchQTWe{4YZFjpC2*c80*ts&sl<M7#Y7*H2X5KG5HL@nA|w|Nblp{c|~emQem%>CqrryNZS{;)bMgKc^umw83KKisSskTwadBm;dF0'
    '?^;w|@5gIIl6eb(pk-Yedw%4J$@G@apDa=3C!<x!?pxWVUr^^lx)%<fe?4i+K?NL?ek>E;(>l|n`QsHx&NtwNOSsgWeYYEh6qISx{P!t7'
    '8)>C0bMm@8qIND>O3lFXl{oh&+C1TFgN2-D5s?jrAa$S`WTJRaJz0^<g!2Y&dv}W!il1H?QaWkEh#5@!1$WzP>UD`+Y|xXn7(V8bBM4~Q'
    'D$79i2<w6-Sz0zT*}_R8*K<1Dg0U@Jg#u$=D({SWhT{vz_KNYb$6O-LjO*wRP{p}<m)catj(S=Jh%&Gi9BkzQ8y6u-)*FByEKhI7XhW5c'
    'zoXN)K*>Ts0!Cfs8$o3`uX)3}<U_sw0)xzw`F0R;yM;T8?6@1G#=+cQSFABqWeGYd)J<^^vleVTohD)kiSXgg%7xTVS}P!CiQ7tM=Kz8='
    'zm$inG)8sSm<YT6t6BQA7oC}_&hjIGz=yDqy(ry3P>}Y{r)QS>j}$fWMA}^zJzu~g9?69wr5<xc?A6PiGc3e$vPZp#xo_%Dx;?chp|Scr'
    '???5X(^Z1*INGnRh`+`gM{ZsU;Og(bE*B_+t%~SdTg4bTx<_jv(sZ|w$NJH+aD~S!L%FU@a7jH*IQ&CuN$jZ55mU`0_h5J#)@-d8+^D4M'
    'oSju{jnm4gg8d)7%I1;BMl+Ya)Utx@hV2VVp802y+bPJpJv5+lciYqu)*oFC@COeS_Mc^SfxT%QO*D)Zcl0MV25EEDVOQ(Lhe0hxPba1v'
    '9m9E0n~nv$_CBVRm}vp*!zE*sQn0*X{EUsd$dWY+dDrbZWDaHw$R3A>fvi?l>Ro}yv(zGdCTzu)=q%8^>WS7sLikvF7^N<C#=$7AnH%%0'
    'XT|)f__(AWwezh_Z{jPkGKFiD<-T6td*nDD1s=NM-`>Aoi0-2YYlevJW8iux+m-gxZusT>(>yNgJH7uDYfn$5F>6gR->Lf*Y3zRHN6qNI'
    'tT9rox%M@`^U9?e^%G`bQuMCy;@7O^y^4Y2RS6<+5R8Q15J$?5B_a04&f4fInsiW+fAyTCo^0+gb~3O<x~`m}H~#$LGHluTs~9I~ugNm!'
    'ITN->_L}e#VZXZNQ1{dh3MRcN22`(L+PXPri2MFiTNENE1~womWp9yX-Lh6JfaSo8JFpImIcd8edl^<m$7y1g(?O97b0kp@6Tr9Es9M-5'
    '@}(ar1W~9*l_Wepm)H)*j`F1+u9Ms>dzBua+uJ__;x2>W?b=krg-aJ@n{e~@)QBXT9AXBo{QRxXp@a@AKI>IRxZ{~dY027`{ZE;iTrlCN'
    'XvOjCs#tG*sJ6i}Q~u9maGX{KQ_J3t+m;?gTps&hca}X66?=iifU(gsYh;>18*rmcnWmZt^oZ(iLsvwPWsQ#8`QtOmMG60ZOSV;WLMd;W'
    'O`&U_`+YbRZcnFppcgUqBp#y-Pk(2`n(T?hU92sij3c<A9O{+Oa!ANt7JM3JXjVRslQ8(zy-~z@?{{+;Zpk)5$&nBoSvFEkE~osM`@orf'
    'K#qI27-m6@y7&@12oF#lkf0L>s0O&OYq$wYrBVI<g0*VU`RfiDWORR3Fhu7k%Gyx{$$VO)J(sWu(&b8rBZRd0UKEuWhJKkn=Bv<Fj)dGE'
    '2!;EZf)&t)3eX4uM+NjJD3feySRN2Ri(m6w0h>}UgGR}d>9;16(nODIdvips;zl7sMRJf751}6k8_?2;c<|n-KPEsGQlZ8UTL(fxE1Zp3'
    'A<GIn>M{*7!yzhxd^)fF>`HHBb2)zKyDD4Zc#h+P9}gaF@z=o#x2u;TZ`#ZHFS4aB=dW1~3G;$~Zp}z1?zZG`s@a|ePu16|$A=NISF=<#'
    'q;PhcR4q>0WZVP);0L|4*Z~PIWxKpz>mAtiahP_(H7$74ybv!D``L@&vA|8<t#u?avPiL#ZuZdmmoXe3`DP1*Wwo8WxF`bR4Fm8{weP#v'
    'kD(Sq#v#=`19lOJg~Gf(^gyjTIhQZ6MKSl~PN$LUU4YDY<w*>o6hqrAutwvXz6lR1`@6B1Z_+3J)baOmcW3_`?=2wgV^kXA#vpUV8_3s!'
    'iQ0{Qo6T7#sKMybRIa2)>ZJ^z{E-2P)NCg&(}`SN1u-{i{FffG1KY33)~jncRt$a+D%?hF^p1I*@CVKb6PSdA=!V=oxhTP$E)<_Bqa%5#'
    '>soQnejRIy65E*^E@8wyxQ?lFs3}>du0v0?w3<JggJf4GMy4dHc9WowAO4q95R7g=Ss!ZtFJqd^vXuhYiHlt(zhW-B5%|Ixn^Uu2%QXrx'
    '#i&Zbf`gb=VBIOH^s@|bz1wlG5+4X_%B~RF>;yhO$)`WboYqj$I#40JDRZHwap9zTdd04pE#J&dq->POBbQRCyskaxH2cqO4{2v&S+R8Q'
    'lCHf)wrD`|=G<FnPk-!HPPHM_rUJ7Of4s7xj<ibpE5wNHazudZzAw(5Iq0o_(7GG?<p|O8uLX|fUdTT+T*<rOl4>nmfn%Ouge2}g{+}&+'
    'uw%&+X#7A47>IXSb`}e-H*j}yE3r)1iDZ`+1s|z8_*OtCcXmz-713whCndtw(hXPHALA!uuZ<3i#Sf&s5=BXlIMYfb_Bu}j$DdEV+fDw{'
    'e9dbAPVVxsC9bWH!*SGLZw{>Em`iXB8}+Hifvz<dm|=hOCZj2S)9pcjsiZ7(cOnL41$-(~_`mXbp8G_w%~}jiIk`ZG>MrDd^F&nr<>Df}'
    'TIy<A^7>#QEuL`zMs1D~)i|r%Rc^t$*b4f7a-uj)^4DZm0#`E+=|bOma5or@xtNd$O%~b$dXOFX(-2p~f4<_>|H_^JO)#zzxwPkAEk!Om'
    '*NfMv*Cnfi$?6~^FsheVBtvKaXBVok!g!@g@tv@JQrj`*#9iZ9H*i5}Sc=K4@O$#>p%UV!mWrNrMf*83|6pfk73d7XX$npWe;}%rx@+}V'
    '056WVs>JqQ_%U61VG_$Q*mqG4TIx46gcTt%4f)>N1cdbG`uv94ymwKO^XphN%cd0ya_4oc9@6y(R-SWfv=Z-rQ0zbW0X6DtUNAy-qF*5u'
    '-73egMW>7_SbLtC<;4VihKMt*J@ybfhU(ZK*yhGK?w&2Pd(_F;4{5S}P!YbqHPi_eZxf5krqmDmNR|YVjT}DHp@i(h=35mSq1N|58*^zJ'
    '^;M;d^q1YjifrQen-5We>S6bJ7d)Ge$<}m@IC&PLydmpMfxT_b=1?&7J9zqO)=?Im!_s?mZgpxkP(#s~Hos9SO5<nrM&MP+f(nIh-j7Ug'
    'Uw^we)6gyQF9h6EX+Uh<HDNAdOP6=Rca2C=iFM5<RR+khsVi|!eO+EZgssFq#QtfRKWn#q4%d-`p@QcZF3ba`pY>knklVJT%acYHjCzPo'
    'ed_<Zy9AE}-{X<P+0fx01%q_){^U2v^$_1JKdU?>ht84Jt=unoAftXNPO3j7Q6gO@HGcGFKBCaQrAIsAG-00W>3Mrof`<pg*cGQC*IUBq'
    'J_c0;9>zUmZYs1=<RA4yr_sFwUlvHc9DHZLPAIDe&o0G9NxxiVLMI-j6{3qdDcZYdyLN2CgT?z>Nvm4Cr>EE6sh}*o)!o;|*EZg&C<|3T'
    'rKTtdvql?`kz|Zn{=s)-uB{2bp)SqQ59n_ElWDDr`)M=vaUJw&5vgq5WA1Xv)Qm5@>D(aPY<b5TksOA)qjzDl_w|Zl2C?9Zzhj~9;eVd9'
    'MXMEwGD|&@;pMb(uT{I&SK+rh((u)*udbNW2P5yHaz4t^SYUW37{wQxmx)1CBqM>r)>iL<kBO4e3EFu8Vr{m*!!JPM7{~YPn%;kc%@lZ{'
    'Jk;(0lN+43hH`Hn55*^!Gn=p_!q+m504n~`O!@oCCee4-@z#RnLKMle%UZk7=n)tr^HP07b6lpr#$ULiEeX`{v_Cg&DgqXQ#e6m<)(V()'
    'RED~>>SNv(t^a9tA=4(y!7p1yp9+$v@>;Fkcl88ps6yBQz|VYrhd1u34lD93M?ikjM4_-N#wE{;Yt#rUZm1OZE@qEnA|TdbDeptwKy!ii'
    'g%D<V*!eIPrXe|zUU6x`*ImDHS72g$;{$;1daPO;Md%To5|CtX6}C$C)#nzpo7`sIUsM5)JIax>YW@fM!uc;U@~!x+nTBVNVs&xkaG1;r'
    'W2t>s^~5gA>n>QhfX;7AKe7tzQ_s9*+hsGq!inu!+Nj+LtwM4I?!cvGJ&JvQAHh(h+#hJswWoqB>IoFs>+7J~fov+t11ryLl3lBfOv{Te'
    '!<U5iQ3c6<^MCKOX6MUD0}9_ZJ_Tpl0p)QaC<G@Ly%ttH-~4<JZrgt^o(TA{Rr{SI_T*AYr}n5p&I~5r|Lu4<_;lcPr9>4_<!FTC?ozo%'
    '7#48WP{f<{aO38NR+$EWFO+ir8<|YnO=E@4a#zj*<j<E}r<O0&<8>X@Uq6<MDx6wdjY~{kEoM?zFcD%7urYgKDY6SrTmNuxjvjtp(QMz-'
    'z{)t(?~>)(gy%0#g}Q}}C`_?5a7*$)zTR8`+}n2a!9%Ax&d>&hV^U&?uDjYhPYvaH{t3e>A)lo>!aF)qMlN`rz37*=KC-l;_03qWS{POq'
    '1=L`53EYT0WoE-CYF2A}rGqnLErwPbOeqXsHBc<xr4d5ys#npN0eD&+OE$4K`~Rwb=uq<FQ?BB_yKi#qRC$D{*mH%e{LGTe*_HcuyPl!('
    'Pjd~_?QY^$KBH39TL9E7s&G*tB9u%7*a6vgnxTMPa-Wy9*AJ95>weU6j^z3jKMG#Y4IC78iKuki@SKJfi%P3cC@Aq_V_*i5$&|?U^Dl!!'
    'l9+&z^K4@bj6}j0?#BS`kzxwm@jp-oTY2-c1rKtK&k4Mr737G-1FXP_6Sbm}Uygq<w1qGGa$|_FN&@{EJl&o`m{L>H-}ESh#0+N79GJXB'
    'MPAE!+aR+VWivEtiH3TjJz+rGgZ&5C4dlE*IDN2UQaj<r6w)MXnvplT|4ocCvGy?2;J-wViqmvAEUCp!);GsRT&!#V^M8U1;5@~=!snuz'
    '9u&yh{V@o+Ryn?EYGv&*f*aV$dXy~TLi%){`-B76pVwvjr|WQWCVmgT|Nhv_GMT8=WxE~((z!nxCce<g_4_E?xxbqYe+qD88il@{c+*l3'
    'Hp1`dWl7rm`ch)gWZ;HXjV?*~QD4`--YV(cE>5ErbFUC{^*3K>UO_CuLUIs9Q{0%=X)qJOdp##a)l5D3tBz%@a>DZhqTN;+xt>UmBnZ*&'
    'aFe8)NRrs)?ME^FzFx`q+D#2>xi$$MPP0CUj(QXRORCuP%cVa#J5iI8og~f`4~18xZK__MlEPnM;^O3sP}G2-RZV7fpd&TXF>;c(2CPh='
    '5tpAKMltzslU4JLlznf(K`U>``_>sXYpb;1rp>Tx08`M3`nlUHs5@|&r!iMHkOY2D(g*hkGcfo1z3PPLmen7@F<5ajw&-FIM>D7KhsvI-'
    'kFn@sD+9&sj)9-)@Izt<AA^s<4RlFAjNY&*LXP5z(jb}Oy2KoBdhB<T?XfPHb1<<u(R>5<Z+7Pn0}ZqWG0>V!l$ppT>NX^J{6q20(k%8a'
    'U9JoTKzU@wncLH!S;6r^;W3nG*zjIC+ySY6Gw#+14jS0+>sa~`Yf!7x3eu%Av-BsBQf$J1h}hd{rif_3gmJyiQ%`<cBxms6pItL~rwP{}'
    'W&Fe3G|?i>1vWj@0)=WYl_PIW+OBZO#mgo9_JAtAPzAyE@J`hlO^GmB!aPuY1^9F}#Kg;x@^)rgWumPstkQK!g>OK%ve)iWjyxukUwM3V'
    '@N8?}T1tc|uNQE%q*X^H(l~Z1KrdxuKm|NYHg-Zrnv`Js^l0ciqJw-(Bf#p;SRLI%7MFsv0iRN-PZOb@NV}%6RKxI2%nt^8dZa;yglj5&'
    'k*PRpfxUxfZXpQ7WEbEDhF=BSV&|p%xv9*>-BV+>Qx+){9&?S}^>bIlfEVOKPfh{Pf!}Q0=lluArbqi193<NZtCREwGhQEfP{iK}K?me^'
    'M~VaY+HHWP(_$kY_xv-2dxer+zK8!p$-GE(ak&2upztYAIVONFK42sS!IrKD?}%s}1vLFWi?cypf+TL--wXUgX%C+@by)Vix~WB)6D*aI'
    'n|H}EG+H~j{<H;_6Dj;n%9{XDsz+dudG=J>^0)*39CMGJl49?HmqvIRZW4^{*Eo9dhb!cBIb^I|-w1}6BF@WloEArt5#H9)*i<R>BD7$n'
    '$+mGrcDRW1ce-fi2zwj+1sZw3#4~t7`q&87`eat3eAAwAr_8Ny8_qT9+~oHptn;;ylyms8z{D4Sw4s7(){wn1#<CNAjsNpdvmv_EyvdiG'
    'vxdk*7`;&4@3+SUj@Ny5&JbWK?`kGl;R*))VI>wdnZydT35z@%fuLG!X`NIJq8S8hgLh_Ww(=9~l;p`?bF@@mPU+Dfa85!Xy)T(@YTq#0'
    'LVksGfj-#Dpt5NL3JLjxMN@n9S~j=8^|;5$LJLt=A1AZTe=s{N*bdyrgC?g%zUL7fBzr6YMNMPcC+MOH1Cmc1zX*HNjs_Ix>@BUAeuVN%'
    'I%Yd{^?|Afy^t5AztzJ9M@zzBH>_7mbA(J~ucDMgp?FKQ^VetDkK1!j7fX3b&uW;l#qah<P+_1Tu<(#6)U?DnuMqsxCjjW=$PEOXF9T+b'
    '3jZ|;G!65-w4?!E%;8sxo+c85Vv|!C`_xoj$t<d6&X?YjC1miRjsbD~UK@r<ptKXQR6bv=NL^z|$Uz%NbR^;6^$*!`tk%?BE=ren@+4+Y'
    'f<{<8<N2rvrE*5r+n1EMQb^9Di<@n}Ew`LcJQ%Ign^?_hHOjsZ!`gjGI#_)|&27A?9Np2dBy}>KfN&<7S320cFJ;QeC#XS`WgClznqROZ'
    'w*~(*`3iT?7$~g3V*DA?zx0ZGhG9W49n;?{EWt|qesd@O1nv7rfqON6f<I-wg@<Nkq*0NnlEZJ^wo3}K&d6P;X3Nnr+aQ%eL0D37G(0D{'
    '{>fMh=j{eKVYCOAu5cqbZCau$@R+o4JBYY#R6ER%Bp2JcN<y|_MyOij*O71`$p2V!FHcIGcGItWhQs}aXP8D6n{JmNuDhDwT4RX^04OE{'
    '+u3$>f_)OD*qbSbj8mcbG^4!tP!PuOusr@&jLsa2&$(IGlrc9-p=us<tHkjKFUH<p(bwVRI7cgty=b=V6x65d0r|IQ=7n?=797f6jEh$h'
    'o5E##C}0`QWvq)#R>!>eyAf}$+t9lK+TgN9%Mi!`M=>lq@ShX|P$vr3atbV2Ll@<qu=&7V4Jl`pF$}JJT*S+0-`gKWe2C^h`-#b3wTS}r'
    '*Yx1aN7{J0^4-<d6U!0fJLSwYD6w6(g$5~@-O@b?L3XLQJocQsTTBW{agGH~c&U?Csi9LFR>z<{U$?!se5Vl7FFygLM}J0UJp7N`CgY!0'
    '`S4AUbX_}m(5%D1!bv)w-<BBsfi?SZIcm8lCM8_9fSBB7!9PE*7w#pm91^n4ZnexmJL+yX)s3c55oK1vmO;_d)Px^Sjk{(b)0Ca-rxC-p'
    'cd_+W<!z>-?_M>Z-<+XD#ke4VMPo=Kei7K<ziy1+R<vIm+g$#D?YCX)u>u#tW?o>Z*%LE*WU<)jd;~nN6n@MWm+d-W*#ke}CB<O-LmL5U'
    'w0HMrJ7v$=vF>3__tbYrp*42vDqrXc-!0yrvGMu4QKv<)RtI|=selpwgY8M7E&*a%?%YUmfubk1->jV9-2Ek>bJ<8&SM7B(JOJYbx}6bv'
    'N>=77H`8W8Tc`r>HuAPeXXA)>@o?#rxzfqt1@;pjHm^yidLbAb<{xH@%itk%cRgWJLg^?J5gMjHw2P3}C8rf%;B4^u1-}Dk3q=!uU|U)c'
    'k_?!toeIT5R&DN&(Yz9vu^(U@BuTUD*Y>ftV>^J`r+1xb{C+?YobzLG019W6JcPwhr=q8ZjVdAS;3m7;#*vOGAo~@?<eKsUr<xEcYq@Qx'
    'PR_-JRm$AmnvIpO2%Kghre|<`MP*udEwd>7G-D~-DSiOSo@bczQ+>(lz-`k5NBTjJ6MrZoz#yz$dZiH(q)H*L1SV?XNJUN6(P&x@n-f&F'
    'S$Hh)Tvxl7L|}QvVC$m`SFanBUHLH}nioaKj*7Qo8xY4XU~OkA{({XC<tK^9$BU%*VZ>9r(gG1bT~tpk8@*8FuAF(a9ljBSjNM|DwT<1v'
    'o_XJSpnVemSJX^NPBWCs@YLC&yA$ClGwxv}I%$ntSgH7XEy_-r7@pzXJ$>SbJT?uDJ2}ibBhyIyG4lk#Tcb~ozp=CSKC_?S#!tYF1Rol6'
    '8&1{UW<_kLNO+Fpkj@uzEG5<lC>|6hRcFaBMUL|JfEnFYIYNt5MjEDgALU%TZA)4YBZ^UnquLHwweCVADU=&HvX^l;^XSiSsd`H@H3UJI'
    'u7uzhCGUnr(B$y-<Lv(yH!3=@(c*PCgL%dG{kgrza=Q!pB5RA<ar)B<%(9-MCBe^uG*s2k<hRUctEmMER%>Eu?>SmEk@Bw=B&k8BOu-j)'
    'Vg9P^>Y=*ehQ_&ifpb8`6?<1%-!f$<Wn;b6+%d&9rxEeliC_H&cH)uOcT$#3V%PRi^^b7<KcF421?YiCx4~q%he(%ulrm*?{~D(dQh=LA'
    '^B6ssQkfM`QBh;YpswwO_7pcC_EY@E;Y1Qf6ir2RqCyA-UWFwP(ElTM)q5JjfyDn)#Q%SC*W~}o-FLD7mAlvf$@i=OD|gW%|0{Pfa9^4J'
    'D|Z>cXs2;3k(ln%zEi&|J`x)MI$t|KF|QscZ_)btrzyvP@_^dkl@G!v)StU|M6-Z$z`Vcv4{!kduk7#Im*A(vhG9hhR=!VvXI?=-HNXxq'
    '`fKtAI6eBB`<i>syAJ3Fl>Q{W1N~<FA_6R`*BTOT^BXX4B7Ot(>bD(260QO+0k#6*{Y8MV|8sr1w+sr<loq7vW%Lq$&%fJi1$6pP{tCY$'
    'ZVS=|wE85T5jM{#{0hG2Kjm-qy9)3H7y@{|A)|jA_=N)qe&v5fALpK66CAvsz+a!P0?q<@{VxI0AHcVQ#e&?s`-F>veF3B2OTRDA9zOx#'
    'f|>xoTks#oZ^>`Lhk#6g?A}Vi0f73q{0(!9@!ar8@FpM;Ao}I@3jN*v3HWBbH$3V82*?2d0PS}s06=H|jsrm8s=tvCFhA-<uSeSTLC#@Q'
    '*NBO)ab~4Bf}Z>CTabC+X((>ErNsJvRYMH4tp-lv-{&{Su^jTIQ}2DtgpDJ=YL;a)onXSFGg4mzSVfHfW67(eM!jTqm%gHE#<04>t6k+^'
    'hxFy?51Ip+;2=M2Ka45PrmgT+@yPn4ne+1eu-miuJLc<|S#v|{Oaa5GbDpv!hc#QSHj`8exco=&l`P}5rh%ckav{0$FM6}+1sZ<p`#FPN'
    'rmON!<H4`?V>LZ}VPC@~Ez~5e=@oxDB`wKPe@LclnFN2MXmM#@Ce8H)0*T}DK5k*9bX5oqgG0td&8vDQyC6TdrChagJxorNRyxakcRs@5'
    'N4%S_EV;mXA|!$FC6H}2-KD}tJKb>4L9;(#U$%9G^&wR6x-)N@z>b-ncyaLg0EWan_#xWqTkm57wqL7PSM?|J9<Gv#nO8V`g6WEV3}LzU'
    '(@gENaez>Bon||lmUFZTJed9SS8A&3)Osk6T_gllbAC)>C*W0{bS&b@2hax9XcmnJgdxBlLKvND>pZITgJ<FPXRQTM@m4QX@E-|za!DC-'
    'n(~sxirIk@jCTe$#WBBa)fXb&eecMb#&NhlPZ{3>YH$K9<4!AgzC$SMu+QWPwB()%`RF3@23x`!!A~Z3d>&4zIpt=%Q!hD@WM_WPgug5Z'
    '^3+<X>FUQYbbyuJj2CkmR^^uaImb_era&J}Zou)?MLW8u3+ef5=f;8L(yKiE<`G+YBy!HlC=Q$=uy|#$U7dR03;37KfnTBH>6_}Xon6c^'
    '3mN_=g<AETHB2<t`eUCXD7%ZuBw_R=r{4r^v79xisL!KL<DWjJ_^SBjYqB+XQMy%Zw!>z*y5i!`7S*?nIf^<bNt54|v3Ru5fpvYf9J+4U'
    'dGWSE2kiVN(nN6~F6pN?a>?Ml#3Qd5v^{pcyw3i!F?y=QR7{IJxY~Mgfz9geMv#?N(9j}CZBmVT1kujouYg0gYOd<>M(cxet=S7nqgJ=s'
    'ajHRU`Cu;5x{&>)BXsYF)3zow%5iZ-MaKqU-s-t`UzrNJ&S%{!PTdvEUzRfQ-}Kco><SSzOuQH&JP!!3J(7pK)}fXF>+W)WF7clSql4`W'
    '+tecB@kl`Cy-MnRIxBD7<-C2$R#^_J8Ly?@<NCfP=HlaPS9Icc?MLQVQ=uO}T&8y`)U^cPNS&9~q0`!QDBc|3<TbZ>8uu~X^3}f=j^HWA'
    'gz`rSARb0X&dGi2!=ADTCWukTao5LdF5c**<SOAfSZCY34X&MVX^ler)Pl_UVqoqavw`bt2{W9;wHHr1xv-(KFwEfh_!fO{N&$3+n#%2V'
    'h=E(To0#dNI{y%&tDPFaEOew9eyG6XfRTWp?V7!=Iq;y=mi~*sg-4&*Ze=IAPs5MR!F>x8dFQQez?Y#<442vWud3!sJ0C%#C%>i11?0H5'
    '2p5a3VMoL~iJgkbhQJANA;ln;;sX&F_(nbL#^s#Hfp!KEY<%I6YWZB$RxaKHMK0>{9dZF}kq6F~7hHhLilR5><8NVd>>JPBWNiiht?m94'
    '?!br65__&u0_E?NEPj{v*``zJ&UX>vNkg`kDNympO8U4`tx9|WGtYV>QN=|;_XxwpFAE;J#=F(_2GJlD00nr?)f%wR#|ZfSbMvoU%r;|j'
    '%IADlvsAu2niWabcRB&gk@GnnlcHj^HOu3tjcRXxTJQ?LV*N(h0Uy;b!?o%`nX_J4;+>v8L1c$RuvInb=0f;riQu~bo8SBn4DiP05-Y}@'
    'Z*p1V`i;ID*TsiRkMF=}D#$Ga^b2@o6nk_T?3_l@YN{o#N@^RVd+UH>mVrK?jZiSCBdj<2kl4tt6}(|qt$RzlwC1cfjSafNRG0Au1P7S$'
    '(Js8En?|9k&%F4|Q0Rb5LFZPx;A23B?48j`NJA?Km_2LR3`Ti<DEoANIv!WwH20(@0v_{gP`={{I7we_A+AxJEGp|Peq4lBF>$=TO$zN_'
    ')<(YRJ!$3u*3uSfhc^sy-p%6YiGN@(qpU1zlYgh!$W{4QXuF-?z;+1TkhF%&XFBb@#qAwE!y1l!5xgDAsng+5^4Jnv{Y6xP<tAbtv2t%&'
    'voX5kt`g)$wh#%w*WP3wS+m@Np!fWd9ctD>Dn|&Ad1JLZzj``>-dM_(2D`UEV)jBuMK_v(O=ddLT7NGo%ws?j))?93dS(h#>CjwP8UP5;'
    'we6Q@ajEGsc$CpL&wuDJb=e~33p`C;K8N>SZ?AzL{|u?M6C3w$DN(4c76~+YoR-#Kfx6X8L9tJBHA&wHPIlu6T$Hua3_0aVXNJSJ8_RXO'
    'Shvk?ocx=>^SyG`STYXbHCdq7_;>#y*S@2_`jSBOB_qh~c$)uWcrGmeci$%Cy<wbQe%N|;$OKMH>Te(>%UuNHG+E#GM`E#rc4eTma_o?Z'
    '@&WpxOv0+6bRO!fstQPER~r^5SCSs)bJSR3U;%$ctNt?T^bqY`j)+#$5wGUcrbn?_YcWF;QPk<wH4LOZ_d{17FMos10H!+ZkTf(Xc<nl4'
    '1gw_QWt`Ev;=%^1bA?A^^6vEb9Q$j)-}sl~y=1)R!P_=G8c+EuRn#}qtBI_I$?6}N1W`D}ytC!7q24i5DtvA;(b@+K?tnvt^8priVu^3q'
    '!<2{cPBi$8xfg6;2B>9$zU4mgaVZ~g)QL`qTM)a3Wfl_V0j7XGsuVase&K^p6m7lzlLt&b&qVEwX_*Gti`kim_SL-OnWR70+(!fOb*4z<'
    '60(zr&dawgQias}=n0KacMPmH*wm;Px3Q+TSxHs`k+Xc<)IzE^a-RG@`dhTNL^!ie0dcJDF8aS|B=WzHV5m}4(VI>&+2Q!!c@oc|?6DdI'
    'P{-wudWPd<A22LGSM%(lmPZRPzJQ>GbrYl$cvP&@cWfq0VApxCH!81$0mWp2YX+tWpsBQlep0b%U%Tgn;oA4ZJhP5)xl~a<%!(~=An@Qy'
    'jnb3qIj{qMu##$m=6g*o)*wV@I3KUXGGy70`<2i+ejn6L$vAbhcmY-<e4mPdQ@L^d`985(1U#c&L=&db*9=P^f2rK#O2jTzbwof!{a?f3'
    ')kLT0xkab)WtbkrC-9sN=MLEY_pzGg)MtG5H33Jx%}|&DK&H4E3CIHvL!zRq5B5Q>_gW~tD08v1J>#cOu|FRO{fd4i8G1RlCM(3CtQ!TL'
    'alr>{iMX@#WDdZ1%)+wQa7W29tPqY|RDCPwuO;DeVOvDN>zJwuHI;;l)bLyYe4BquEvbv~zAc>9*rMXN+$|1=p+6e~zkjgwS#Z&Vp7xKP'
    '#O|HAZ4dCTfbgB{d;)P;6kMa`ah9?66~5S5`lOTzKZG1gn|VX`4+5vIrO+DLxo3Kh;~{F3(Y8~dx&IaIU6#%M+PqUTjB1tj)NLMTj2;hX'
    '%hbq4CL@S?^WL${@PnVnEn$v7`qpkFndhy|EHfx-ozSxH_EXZ7V!S2tH0ORZk=DAAP!)?PpGwfwxs#-4;0PCTHK&)eE>pkps_GA6?97m5'
    't*Zu@VT!ikIEPTm8iZOi5q!&0#o+mPnLs2dWZf%SZ2V_5Ag{$Hc=PKLSe`jq+^R}p4tp|SjS(<tmq@^7HM`XFk>>Vxb~c9soLEmKv~s6h'
    'Gstcx00=9UKR=T6^Z~cnwO*8b*#29zwON}bK`bwirgwNfGV_#itF6NlV_tmN<t}Ok_BMXl8QcXznA@{1>6@p@z=^uLh5txhnhpF&*h4NU'
    '8;cA)2an~8UfOl1)X2Hm!(Z=Xp5s3fB=dD}zGz2Z(xq}ITL1ck%Uk4lKjIGR`AAX07s*mXcGL)m3F^?MeYHY#7A4wyE-l#aoPzJO*@k9N'
    'w;gUQ&P+j+eR;h}W7O4=PRB&M(Fcdl9S?Z;qNlxX7<zaA-VaILk1Ry6FG}bf0MS`xzklx0r)Nx@qyjLOaKx!1b3uLP01C<~d!d6oXJw9c'
    'T0nY2E!D#H;Nh?bB06?}g!CnCmVMqPj_kb|&zq87IPPSsG47MyQsaRdiG5?5YcZv(k@q3u*x8IQ<z7CMy~|F{3NL$Ps=8TbOoCRu#~I?}'
    '+jTxNuniXqi!WE5h&|X0A(l60_w?=2j~{T?ur32&!5JrMN-+o;IgTzcF+*%0u1*4mn2|fwZ0E58(Bem~IyDQGnz&60-&Gj$*ksEG*9!@n'
    'Co$C_V`GfL#>8{iV&3f_4>C~lU<m3}rh?+ZDS)qhl`o19Jnh<3)hl@uFs%u1^BlrH<w_24?Jyz~k-IrSBLoDu4n%PzPWA+#cH_E%Dpb_)'
    'ce45*?y{9^!nbO!($K-7wWXpZprVgBY)cA<(af5EN=?Ug*>UFg6>r_rdL9=zO;5(}N}NXuiOr6X-YeI$TQU%k3z9pk1ecu1`zLCuGr6|4'
    'Pe3(5IO+GLZhP{`9wSj&_&S;@e7TQrbmZxy1n*+h^j}|Kjn8s+(X96iDg>xMYl~#><kxM}_2mWxD>Jq{RMw+%Eggb<na+3|@tkuJF<xNF'
    'Zs2=fRl#%!5A+glX`!79f#&M_q#+6Ll?g)U3C=}W0q)a;71^G3mki3`7QXsR<Ov*J%mla75-Z*I|HR(z5}q_u8EtfXtT(1lEtQnJH0c9_'
    '+xIyZDWb2Lb!!8QGMK7N=}&Sh4b^xP3dt#E9b&^#_!If8LWIq(Tuu_Pp#c~U>A`X_vz&5DI4yoH-CCm7D5x{}B+iGhXXMODC*^*{n}{Z*'
    'ZUl)ATpcu1MDKEJnS#+@JV6~aPW>A~F0`qD?}|w(j*AbKDhjuMgsJK}4EqGhUTd;2LjnN<vqSy7=4};_cBcDVMAVQjQ<j`Y9>ghvzxn~P'
    '3-Z!-c*`9`iCw~s_^Zc!a)-flrLAb&6Fk%A-T?#(vkj_r3oU+CFo@EUPWsg|lirl48U4JviWCcRt3BaXms`1)z!k~P4%baxQTRi1QYrF)'
    '0_}BM<vxZx7Lm;Js|w=rIZ-#@OY=Y5A7dVp_GtXP$Pmn)Rd^5uX<l+wY@w?l8eLWehtdfnTP1;#Wgiy;74oAT2iGvJn?;d#w60%g_4J|3'
    '!=ylFyfu*<MIizN88l}$pJE@5zO?ipeX*Gd0$&_)wG!$&d%__^POo~D@)3PNS}T+{n-p83iDR)*lk^J(39sO=P(M(7p+p^oA|gCr?=F>i'
    'fvQ&(-_QI&t>nM*fuY;;O@};%Ra-DUO*t%W?eZXvg^uf8V1JOAz#jP?jjOVr!(xC!@e!>vUmo@r%QY6|FOcgZ#3}j^iNzxM#}h<xQTy<n'
    'pYUbW_@g4_>o$Q-lMQN(^(2C6{OuEvj}6D+td!jP5eGf&xd$_ySb^Qr^Uourj#9k`XRlSAxSf~rQ6hypxfB18H7b_oCA-UYeMt^Of!^D`'
    'a!1~-nf+<6Y9IprT;g>%XD9$|T~i>2LQLbBzO-Nt@oiVU10^VSSsSOeRIBrik()EY<GD5J#zGSjPW;hba(s5rfTebQB{?P=!`;Snm?c}q'
    '8=wqhFlEkRAGbqJ8W7RpBlYrlOa~gYv!}dLZ%uoPuAJl_W)eQwiRZX(tT_~ysXrVbZyLHONYhh%JfS%k`mw$lLvV1^OE#F@4#k|V>o5g|'
    'Y8-wy+bgG)1Raqx6DTrC!%&Av#-%s$Kd|(Iu1q_K75Ety!v@m9nLhL<>!|IYp)?6!PbdTX5{m1d%XH_zIN1~jf^D;MEB`w{0b&63Ok|U8'
    '&)_AcW;MhzFsYIzg0(>oN@1F}YkfwcdBJ_Oi!klJr6k!}pen>md?j2Y6j-hrgL!QyB{9{S+wtZ*z<nB|6e>g3ya6doW~F(i)ePTxG46Z*'
    'fTL;@Ozoi>v;0y_!{b&&`T|H&!b6N#u{OQPmJriYD3kL-V%5m{C4~Kj*?C6_roW9;^EpA%clLQQ*$BLuYcUF!sg$r~URS}?PV7;Sl#drH'
    '`(P7;>JVg;C1qtQ3$viicFZYBTH0VF&f1@7c7?QERbHTF>~Pq;3#IbXvf)IV(VfzU^KpAe>!&;?wH$e@YaiFkCd1PNAOvxKF0@4&55k@s'
    'E<+de#r5Lv%?+#^(poPW<I%#2v_uqe^vy#1xR3%Ki%oUbjjJ>$zYYjbQ{R2vHN+m^v1d`8R^kp)T|!vT3xb7L<6JDTtC<k;T|d}bu~pH@'
    'sJCw+J1BPIzHDOD7frnobY>ec-iA^uVlGT=+Q+$|5%z5?Bn*rw@W`U#Tg%UrKl)FaQr5R=k-;@APjl2wZ$BE2$4Y}6xu4buQNtTtOeaH_'
    '%mg!IodRDj6aya9(x_wMVm%?hfazW_#jGhTf%+4+NHvtnG*G^M^JN!0+3z}y2jGvDa8$oir$+E!lm>lzQxtOx#AZ~nhatJd?IR=GX&NeW'
    '7c?B#T@HhsT%&A@A0lS%*M!qJq>*LJeOdS%kZ_UP;ixvlMi3rYOqtf4%V9h5ooy9VknWD%QK~Qg(z?tai09B5fq;T94e5P%Xz~cR0|TSB'
    'A3*MHBEB&0rY`6z-FgHL$yzkH5SD|^d|n!r>0m^CO_f$UH}M^ZOl~zhD>?`=XtW(1%;4$&)?7f7lX5_d><z{CrJacW3x6_oeUGklPwIS&'
    '7`J@VJgjo=XJ$Ck>}WZ!ZQXp_Q-S#8ajysao{coH5wfoCbK{x1e03kObC7F{<qTC?EA8x2l1l4a$B$i-L6M;zNJ=QRPYQ8s*D8;{B#`}%'
    '$m){0q+%V&B1{+JGFrM&;N7U&)7x07s6&J-DPwzGGj_I$y?X)HP441Dnl7PTVIND)nBNZ7e9ft{w~q*UQ$*ZtU<|)lGi5<H#=j#Y<kKJ1'
    '3-|e(j8_pbEh}B7d3A*9@#mn<Qk1NZhU5@w3XGl+Bd%G^3I&r4<-2R0eyf}{ra=8Sq<g8RU792JH5f__eu~5j_fwCY(K+c*Z-ri)XRSV!'
    'gPd0Db4-!eK>Ft!rDkP*F5>2wbFM<|8Hd*I-6qD%B#MEcZvd~xS2gjbWZu}Q{ol8a;9#1hIgIWrmWWP4NexLL@e}8(HPyt-BQrgsl>V{q'
    'sC15}dfuqUi*mV_*aqRKL?co0wZ+{fEe+4jI_!73gBF^zU0CQ}=q7DnXNaTzVD{AL&=`Dep;FKxgJdEkW=GDJ7QUnOay5}1`}p0{N%7s)'
    'qSQf?@wh-bcci{R#6-H~*rKGs^DAQ!88LLAM$0{9cN+u10*)>vTv!aJmgtuG7h1UpLFW#6k4KHQpir74qmX>Y`5UOUEt&WrHp{bzm%bXt'
    'Gf?U8bmWnq;btOooCy^;o?{6X*yE;mwlBZE&7UQ~FEe~#Io8uO&57b{tAn8Z!ScQ5P??^gA^rU|yPRlpkZHSFAg|ELL#u0UUDBBY9<Tdh'
    'i~t4+7K#U@mdztr=c{|)9)yr0T|O}-cwI6bV_Sjvad|J00zvdIotaiJ)rEW50?+hI>SE)uv8iXdFYT8kv19x@|0rE`dOQ7EG^S>oy23rH'
    '{Z!6NUU}p*F1l>^uiCt=5pN1mSC)Z4(XbKgi{4HMt25cMAzB0GSwCl5cj8H71xST)!`#qu*QN6uOGz#nN`se&>#$as7_Fg1V9hwY7-W%x'
    '2(XH;N;tAl-jv{)J6v(tjQOk*eGu(w*1x8^>|koO(wGEK{qYCX#qO=aPTz(k@?O#~<c;I{=_Zxud0=_tzy+COXJtTx&YoNQvZ;%O=(HNm'
    'L&5;THEE)^<*jMXips3<OgBTqY^s-clZ)R6s*KEdH?OO59huMUV~yZxwV$p7?}+Xl&TnSCsO?%R9XIMa!S7Z(#T6%d(%>HRC=ilO&S_pG'
    'sf<cb1}8VL1@#3<=$gtNQWnTkOzmz%>b4N4?g-#Z{Tug<{Cju<Ye!$z4dsB`UgRE8ui=H{cq~%(A|P=6unYp`Wc{r+aGU&%-Hox*nOxN1'
    '`U@<tBEhOfkAV>(?IPjDwQ%Fx(a+AA&ZM~B{J}M;Y7#ikk|CnfZT$XRu_dN?tlT04kQAOa6UknttfZ00<yU;sR!FjT{d(A1RYU4j3_R`+'
    'a=AE={fS<$2EE2I)<AdOsIGjgHYSKH$+udzOrgD+l6S#ufpk4NTrIQQh__|m6X4b+7|9D-?XnvnYRaMP0_NpAvSh#@TE;D}L$$*DbLY;y'
    '$QiFQZzw@Twx={=<6GW#Bw1xW6szt2hTafv_vodI=Si0($GNAEJ`c|T5D(c1O5M6V$<g+tzi!zy+6#K+7LllNayt{wdnudDaTFD=t5Vn7'
    '-xG-KxDNzl6A*UEZ2o}G=Pu{$&5kN|l9$GX4kE75W$Pz?E$1-MMO9HO7ccNh{MlSYEV<jsJMUj!wL;ZiNKt%dRr)p6Zjy{HWUSGj`xW5Z'
    'jQMg^eQp|TqS9S-jxbgc!tc?U9F=h)Jtuz3+*;ARtRN7&JPZ>>5sZ5EChQAs?7I0SnhMAV4;$!76Dp>fDE=SM$F7i(;`2%OVwwx<lBj^|'
    'AZYBIU=B!2yjNWsk8iewaQ<>O2uU&z?V$q6)HgO)Fdvv976fm*(UvB9QWvr9H~KS|JtO#_Dw6<%tEMrZP2A+;6h`bu@_*DRMh=>?n)3V5'
    ';W&L?P3t?-*zr4~%r6wYGO8D*s<AiKLAX5V5C0q{_~7M$@OyGn{k=i}ulY9UYP&I*WxrYh*SOHQF2DFLrQ2ES)#WPnK=?y<#v$KWFrog*'
    'D}f>h^ULG>CM=C}_jZIq@5pt-dy$QES)$>b+(dr0>neiTm?(P+uU@wsK-)~i{@J<aK3t=EoPcim7g0Y3c<Dr`6XBdi#S!i$pd-rUUr~Ri'
    't7u=vMrvG7=04v2DRf5SpMS;pYH(B>K8U|7WoZiET9<1ajv{O`mF{RcuQe)?tX`x<iM{WV5H@%f;tX9m)sChALVz;jJzuZ|b^0CjV^AmK'
    'R@BTrnlPD&05fTP9Qkc{b=Oa+c|}-HnQX_yuWxKLCmjdNE8bU5fQsuc0b&NIof;6?q|8;V=#dN&&=$FO-`{^0iCtZ??@D{v2YEDCPh^vJ'
    'sHIQ_RxLy2ZvwK|?f9otr+c2-@5$ft`!dn&mgI8axlB**Pc|;>t@#=6g4-|z1V{Rp2R!8-w#dFVEINetXQ%sqQZmUy=QV=i@EhEzdTk>@'
    'eMC2P8vB=g0A|WC(2vhZ-yiuRX6HX+`O*w46s1nzgqNDAUmOT;4k<Fc10y1vv?Ud&ZT5ZWLnJnLTg?&}ikj}fwiEWJP{Ke<Nc4H12zj$u'
    '7FaCFju-uo)BzhVU;~!&Sq}N@`<ktT^=a%%q~inbMKmvYN5?;!x`^c2&wsmElzyu4*Ljt`&F!`ABN!d&(Vv{z!C6KT_y*xL28XiLfI?3V'
    '54?ZpG}s`0s!uL${+Ydub#cdZSE~9-##>92_ZNYal6+aANkE*%3R#Z%^m$DVsEY2ADrL8P1Sx)@ZhH2wjkfJ2;YXC(lCWDA0BOSvIK+Q>'
    '<2GDGj-0~?hFrp&1&4{X$Ou0*=?%+99J$$w{`&IX1%6Q|j8oT3eV{HK4^|vB1d0CO1NsGr5U!k<5BX={;#N5_(W3|4UUOdVwIGU`3Xc^C'
    'FN@(}7Ju5h$QbQF6~{jry6&@y%$G+l1pW9d!;Hy>p|dsjTex0~ydckQm#z<+SmA$O*5fq{z3x3~DNB!p^d;QKpdB~2CGvw;dl{#a=!^aa'
    'f82GacVJxeOyB#+=|}RiPsc_=EB!NDs@4e6?JhP($TI3Dg?S}cQX|tH;vC7GU@vb!;-8w4LKtFJ4K4ktL;pGDF70B5U?9h+d+=XPlNhB#'
    '3;#!emz|}oD^7oUz-VpH=sB<ZoXnk=ZrT$kn;gZBfsQ-EJ<HU*TF=XC1=h8Jh;j@^4NQ)Yx*dLEl0kLnZ!ePWA!x2eJKD|oor%$tt7^xW'
    'M1A^KJ*Ox?2=|v%hSLSGD1<g`DO(nCw;n=e#K{6g@ty0kD>5TMK{HTo<}^8v15HJH0V(We#9qE`(T4y9W*8CADNs}6PN|Yz+Wkd1iY`t7'
    ')6}H|x)H%g!asVlc<fty%XNPQ6qsE1x6%ER7<PEMBqH4x83y&)0Yb)sLr`|ojA;G$Dcjgr8EWX<ji)B5^85fdkyZFIm-|vw;cN2UNz$3I'
    '5yGrHr%U8W?!c#_fc4-KA;%rNtBR%<T2tZv%M|iePGHCpz|UEqKLkwclrOk%56t6ICr!oICToW|Id@!R-r7gHatd*5oxO0S|7j+3=I<&*'
    '@o};|aDu^JJ}N4;(;vIsf3?6IrU<!4n4ufu087ecQ??mI1$X#u^>}wY9oD{Q!jWLv{=&l|kUOi#(j(r4K(6>Wi2UQ>4$pKnas9~8z-}3X'
    '?`07ah%hlyhso?_U@E$aajnCp{Xc}<Gn6h0kS*Z0?LKYW_GufZZQHhO+qP}nwryMgyV0AqCYh{OC6(-;cJf(#9PeD7T5pyp4U1r~=F%Is'
    'ec~f|@`RHLsWxzel2PjjGjV9YPAZ#23&R(-+U!cSLUmmEUKx%{a?EZ18;0k+BT?Zv>vChvn2OYox0b)@G8y;*OtsQgL`v5_o~n&tKpLe%'
    '?nupYEA%$nIN&WXZL4SqXukhklUSXYYYtULU8QSp(Xenx(x<9jjKn-b6-Och(zp~-Id%ZRX2=M%*fS*C$z4rxfF`z4uKVrXU^Mz<hMUa;'
    '$*wR;EUWI4$eHaU32X1hwxxwf*wpiSE2bb{JGr=tLG4U5u2EmrPWd^Gt$t4BCF%~7)z!$y$Z}JpO|ROb6sS?fKul<%4T&ZqEl6}6>1+11'
    'y3qk!+|!6$4dYj==~cC?<%SIp%dg&|G43TYBsa{56u-uD`(XYfaMz>HllMhSMG6tR+EWX@M{cTrSMdDrQd`w8)%wjqaOuZVj7Ym`V?iJ$'
    'fy-#(!+WIr&dw%367#^z2dMKFM4SS6@_lPRzwYjZA3id_x*9T^5POWLzckal7YqgC79XvjGlk&n3OTA)8kmx=wzCF0uJEGEF4*S`5KeG$'
    '62cEb%iY6Qgn9R~5!@8TA);NWb(HCMbCQdsfX*RVgdq`2l{tH&@7alL^-#YONSVzREylTdEmOT!!`IytJpEjf2q-&)otLW3cvGlR1UiA!'
    ')<2^6%UQt?YJ?IDeY#>urdT=0Q$46WN;)>%=*0VM#A{tmoxlA%zlP2tAh%C;UAcC>S}5k<nsjoYW6qzBDALSxE37b3*Zb9I{%Bwo=6Pf9'
    'RPgpLeykQCFNsXIms3VIT@H^G41oram!Gb$34)?Wjt*kbVd<GhTT-hg1CHu%kOaM&UaMw|*F{dsd(#?}<lNvZkg*atCXf<M@VZRB3eZ+y'
    'jNMPQR0sZ-lKdfew$evY-Po5Y)UfHBsEH&;D$l&hn6{qHTHF*^i>eb2sr7i2p`=dsTHZOWEJZ;vxeeraf77E_OY&bXf!w)MpIxi6Ifd!f'
    '{2d?YI=r8`fS%s%hBbeIkA&GBm6pyi#RHAjdOr7uLMAz$A(mybf<SOJpzudb6Iz)(180lOH4wk^8RAkaZVxnR0UwATRu&RWo>be69jSgg'
    'G_em&L$n4g5_kr1GDELcniG3_4`MsjC#fr&zq9@7A+Kv)xiV78(pSO<NJ?D2>zjGfb2m<+?8~^ij^KN5s(Y*W$0Kmj>MSZ9STcD}PyFP0'
    'A28$U*Aiwg8wfz-O|xk<UAgPk?dighn;V?L9yex>-hTw2VrR0vb5<IX#x4nNFGofMv+O?fuj*|CebL~<a>-`HSxkAQX(5pBVJ24tnpvaH'
    'MLh~u-6AImt~Da&OaA@ouQt@Hq>Uv)|6>sFBvmY;Z?ePbo8tV_7Ir3HWbcOP(*AF}z;gMYF9OTUJ(3-?I`PA!^iTYDyMrk}&7P-ITNZ^V'
    '3NZD4>XfC*`1YZ9!s`L9mhC^3f*dyh;=go>2oRa}<Pm6wo9gB&E53W)3r3O;I2J0GT$;Hbad1iIG?`=m!cLkv+U_?F#?25W4kLLW+w6P%'
    'h28~qOchqTj4Pw3XkhBVnpfHc=VrkX1RlVhC<E#)D^iNf!d|5zA=MHOY3gzcGM+8cL@*z%t~cv$<}8=yek`fJlzHK*X<T+_xfw3wD|U=='
    'AC);}5+9q(TXcQ_7xNdgf`x(T7VJh)2PZDT$X$Zhz%5Bi^-k#oVmG|&sk&BUqq6!DGe=aXzVVw+)C`)K9uD;ga3}~oK??_!a7>1ARiuYc'
    '=tdQqQ?MAWe1XRavEh9k$uvY)*_xI2BG>T*&FUGUZ?H-e)ig3-`+Zeg-H7;7264zNeYNkI0%xkKi)5H>aCybD_L#VWMk0q4p~PmyH#$jm'
    'X&au@P2Lug{Sj%=_+%joyVR2o#T!OLyg+4!JaD8tyhwvI(T7c8`~vyREA=JME4d&{sal9YX287NdwE|@dFYdFUclv!KmB}fpTPqfEsZ7)'
    '9-t~@eUKm-pS7m+7!X|lz5sk6zxt!gREGDG2)ISK;1NeLyEja8wm<qV_J><P{5-ut*LR?yrw@})^bZ=~;|2#t&mv?#P-DT`H5kfCqinM1'
    '!aopM{56|pTA?1>acKjJzkqYe^C)wy%zf9_C;Eje6Nzl1(+W>4*ko(jzMW4&FxHH(H=yF$bSKa;>>(eo1z+G-G?(QIT>1I<zWUi2mp1mA'
    ';Wc^YD{noC;Lkfqv`H260o%IjyPst`t}p8L{QYK##(Lt1`Z%?1^;WvOKp_eQCASIY!s7UD@*GM!G0PxgjJs`d1#2I?2mpCDc9#(FJt1kb'
    ')@oG+Nt;P=Glni>=5q13Q~i8<E-sWII44-NEOLKP<jE2zJpMtrk=ulQj^XgV+uYQ}Gje{oDQA~_=Ky?+%d*}ytuk6!rPdt=o^msc4vodp'
    'f5u>taPc0BJqrAZ&u#wzE|3G#o{m2v>%sVPy=$M_wACvPY~KdwtRr~11?~|2%jf6xNoVCCb|7L{Lyp|#Hk(*f6={%9kF+Xy+S$lV2BQY~'
    'o0P&=J7-XY5B6ZL?Nfrbnd@+M-*48ZC6BfTrt{*%U|B&9>d0aA)T7V0cDFy2+;=lbP}5_4x$W#!!0w2rD~;+X!CQsE6BxiTJZ+12pOQ^U'
    '=b3-#vEBp%_!i{86Bu>_4as%-MTXQI0I`Fpp()Ziy`|Sw%)~fyiA6Pn1HP`Z%sQo=q5NB@O~k)JniJp0qRG$#Ttd89T8A^gHV2T|H0q&F'
    'HlofT#7bO_$;v|gpdOyiy4iU1n9W!UOpEJ+@yrQDy%h%S7_y$wE$Egoh+)xAM+Pr!sV&2uZni!cu(!dQ_73(O#7O#^*<&Kv`wR0}kGOp3'
    '>;wkTQnv%4_rO_w<zVHK^{4z39dBlSz6+gHd~8TfaQ|cd0(?r1MB#caP}%%uKyLbtG<4c!_HzHnky@<(`hhu%Kmsi^^skTW2;5nxR=Kw2'
    '$O9Vo%`gT@G#UjGBvJL7L<T=viBwPy{~nmBArF)wr<N4)c%ct8X=x(h`ZqUP&Ah>IdR}JvuMp&3j6#I6O0p~`a~kcWK(RzET2rpl@h-DB'
    'g8a66a7dr!L;V=nNq(g^S;FJL&cMvpVm9x0+G(HSujFeBNhL;yzFrLbG5DuiesB*_8o{I=Mi5zso0zz_pI6-zd{UFf2_ozXC*ucFEYH=y'
    '2&hVPNCoxd<eKW+@P_z9?vY;4EvK<|@=P%67zSi_r|N6T)}k<T6yH3B@|W(mbu!uH>{TkrSO7UjyIA$0eN_#8<_ZlN;O5X4gFLRNQ2G;D'
    'jBmCipXsD(Bj9!#=Az5*yu&JVKhyAc6zO3)ND}UoCfSs~pswh;a~p9Fu!b%eyPuXyzf5>71u`ZRiP6EUuRNDqxgUik=cBJ`%>x$E{|b@s'
    '^4d{CAk)2jDsXJ1YLT&@XBYc|jdILnaT?0R5a$Lr`4pGnlkdntZcP1A$g;Wg=TZ7qyLDB?M4YSe=qnoF9x<)XH68jFa3i8ixQq`9v#&64'
    'jNuqUiEL_)?01L*U5b8>1p+GTfN3UGQ<n4jYqBbm@Nm0*^X<1NR^prTk`(%%vyzs5QXM7t#Wdfahzy4?r=p_p|GY`H9#sSqd$QULiL?-8'
    '4~f2a8d@yh<{2-vM|@Hd7}R%((3fvNS6sko^n7H)(_@D;K<&dqJJKrG`8?f$kQ4UK1nL83SZUrgzG0q>z-mwNmmC#Y4`g{diS8Idz=4fG'
    '`aOT_%sI@Y!0THOw>JE{axJ}Q#LJuaIJ~XWuP+~v<CgS)nJ8I=RE(pXi4Yb(K9g3svxNVSIz(CGzxX(2I8g{oLM_mOp~4Gk;=DBF1k5R1'
    'W4Z+(svYuXB}&r>`9DUMJYVG_2U{Ys)j{_*XtBBzC1C|h@(+#?V;B{Oj<#ReF^rcoanO#nuLVJ(o;iu03!+50nD6?bPvgXiwsT3^pLDvJ'
    'Kje!@T}JZvpF+Aoziea_!`a~WQmIlor$R2;vk9CI(5=BULbh+=6bC&xt@tfntb8eBaDBso{8sr2eNS_l8b8h<A-a5%+x>8|Vp{FGQRjH<'
    '=Vr$KnzkEdzy7TPDutVAbbEF8xz-Bc@-a$Xdw!wyeKu5EXtfVT_Xh9htPXte_;_qW=+@NS^T(%F8_~|U(=ZEEb-c7o$$_r@g4XP7+92S!'
    'projgHDQWZ=zQsqJG4YroW`hr71t8TT3v)Np!s>u*Ej!Ylalc2*WOclCKORwveH!KUo~*zdK_VvJ|dw=Qs^xLqxYJweqHM{Ic=cY-p$||'
    '3m1GroQt5F8j0vOi5QYfsy=3%i3}KXF6E=di07i%H;mz{!3=&2wM1svfZw~G|I7_&?1O7W8(lq9|8vJD`$26N#Lb(m;5}m^L_rxrBRTLQ'
    '3G|j!p&7lX*dxsBHL}8l0Z#mnG{VirNt@_d`fkF(aPuVMW#-_D46IDdDfXS}2?YQQ%qcb#??v04k$4f=r!YtVp~)N~KeZ`wX+mfyzg1@z'
    '1W6rR`WBF*>%p?JYXaFA{z)8{uxt76Pzwt0yosG*kC_&H_QunnQgyZO=E5z<RB;aXtu=hAE*fsj`<wI#oT<K-AL2sdgu)uMjnEbEbq4*S'
    '_P8$ubmyI$4fGHFBiW_eZ3y|w>AMcv-xAWYK_OZsfRMWvgMpN2<CRetJ)E;PR%(Zb@d&(cmI32xaeBYQ)v)N4pylodnz1sn=QHS4cApl^'
    '(L>S{bK1U;-Lu06^{alxz?F~A1`0n2_<*1w+oilZu52%R@NMb4OY;PU0eUGG%r4F4G3G%oXaR9~mK-OGN?la?NvSfj2D6#4dBb(7v(8oE'
    'rt$za3`@2`ErZ0Wq=rV;b5(mpYy)7Ee;4EfyL9WU?_evE!ck^6uHVG5{d-yiw(|ozXiqKw3MsLsqZX-RD3~ku0<<Aea6phoKnXf8)}h6<'
    '@qMo1s4x107cF>=3bd8D=qWUno2g&5M7afV;7bTkhq@yJvkoJXSc}ubcXJ(ocRG5O<^1wWz1THl`$S3N&EB#UI&$(u`q{7~Rv)z8MW&~v'
    'PSro94(>Ez6T`AD_xA{AKgS}7>;6b=1bBA5c_|cZSAeqDZJ=$$#bYP>YB|aSjlg#EZD@MtalNCy@kOuuK<XH0^fQCwmkp)tOwH<k@lI_x'
    'f6j5Kmo8(NqI`g*%7+68<UPz>Kx=7cAllKadFEXYCD}|gkRzcy;=mar!kBajv-bE4nVxAh4hksj$tG`dR$ieEI#|{I0G+4XFSMkrQMOU{'
    'PLsuW2sb654(E0Jwqvg=7TD$ra<oH{^Sbmwn>W%rS$qc4z{uIc@C7Z{1o~U(P1?8sb>|Chw9eQ_C&toyr5M*4q=cS&bgUrKcEYfkNN8xo'
    '_~{m23cRMJ0pEs`WJv*NsTh+hq8#61fs?C%UYr(q@WMza+JjYgu`7+=dI_E>!`R~`Dj!QqoGe!LJaX(+k#Ytdn(P2WLl*Ng*(X;2EL@e!'
    '4GM{kY(TpPJ_vc1g8HxtRq4tGz;pBciC*?0zf4K1sDO6K<Y1VciJ9$O&yi8Z#oA?ef;Db)XB+pXib9DUWRPca)fCgi%0u58t9=T2;KPZX'
    'i5gmlvd%*5vrYQ*-JeMuQ&ILa6icK+@&=KFeOfhIvtrCw^QM)*zE%*$=h(q`;8e4!@axo~M)NcNeGeG!D%JDjnaI2qVqO=%1T%g7a{W`s'
    'hH~chc~v_XS45s5tlUiX^1<;9Aw^ANr)q7@wB=gzlLZ#pyG41zC<OWan@K}kGE!P=YlukEt#lW<!C<4&&0S*9Y4~4JpK<VUvpKIiWI_@b'
    '=in%H+WS+PS$LY2rM&3L7R4hh?#2zT@@x*-eo|Gvy%#NnSKu4lBer}(P`tWfMaC|WA!q(OLlMF|KK~jHk<wsos?PHS`{V;e{)OnWx>^Z|'
    '!ToJ~5t344T(uecWE){QUfh@XZ-Zk;?kfz3R~L{r(G3;xmhtjVaLwW6TO2|tWuMK_2FgsWQmsPs*ae?&H;LNq`8aFpoqcRCXj?RkO^Qa$'
    '*wlF--=h++CSJ&txh;J@T<zV-G~<j2b@Ox;>EUl>L;O|G`hF6lkm-<O_!9->+QpJu)pz%b-#1o*UCCFad~es9)B$|xc}`eND>PqbaBd}$'
    '7&topKy@g6Th187adnFjsFu^4w=?uDtrI)wB-pcDCs?#KVD=-zovq>78@<eA;?EZ~Nh0<+WUt(V;@Zs07h^esKg+J2(v4+LXQK5jNVR4u'
    ';6t=f&*G<R2*bZL9D)%T+b4AGXP?Tw=H+s-U#N<&P78c)!h3KvUO1Y}(pO*%WsZE7lW0tmk9UT>6Q&CPo7*Qtb91!@P?LfrTyn%3khl3a'
    'K8>?reWR%xPD*eAjIT<><0SQWR9f*^sn5q^(~^da(CbeUpcsDd7e`Ms#e5fLikhW5i>DA%+7`+>DN2qNo+sF#GipdzHI&XKqWr}%p=9yL'
    'W6RWZ+A0z$;vZ91`g6bzLKONt8O-V0ep;RM#%wOFz+iu+sbMZ?-DnyUsncE#dD{)XR2mA)gW@p>++L`P;cWhuokJ9-aQFjiAcr)Ps)uIf'
    's2@S|Fn?fS-`>5jRWnh8KU|_rZdJ+W`j19u>_4y}l6PV|S{+k-9HlQdY0P+gUrSs^){XnG9%|QydZuktq(MUNc|RQQ>%7>g_FyCsZ$gbL'
    'I$IUbgTk?E2eVR1hs;yV;K_S67%y3W1dLIzsv-ZxiF^9lq`AuMB4I5N%T0w+Rd0!F?0GQnRWAIF;u($05z@HvaCv2Vi_cgpCT42xpnIzC'
    'h&4;}&tBX25;A=3tVp}^QXq^^zysC(gR3G-187M$9xUlo9^pWFcf9x9)LIM<!Uq1mWFGP^M)x`p>7vSoOMxRH4JU0LOD#nS&$%V^hcrX6'
    'XdT0j>f+d;_oI}(pl+tcB%gxJ@Kz=3F3S4YoRizw9~8GfrnDQE^r}n#+08k*XO`ik&aZIsW*n<uMF>IUzMC#+3+huw3RzI9_3T^OZ=1~S'
    'Sme=SeDD-ilo8|6Q;5j(<**dW`$bybnNd=J2j_Ny^`F;cqZ3TMKk1G3ebl&H1U2IWGpb%%iHKhOd4^S&0%%a2viV~R`R95PQX4KR%=9(e'
    'p*EB2<`q;xhIy_8@tkF89ipONR0U`seYs$$)JsM~*7@|R8PL5>nf~oE_hAkDh*rgjWV!W51{j-fS_qn5YdC=kd8rLxZC!pY!;x#*f67#w'
    'AXHe85naE`Eu1>CX0T$%JmBTXg3<@BWggZL=L=Cys90AB@?k*ebDdfun17q3XPhZY8K%=;eh%JYMI}E$me}jJpUgXRzu$kx14glGic?5n'
    '=ra4u=KhqV@(Jo=^=<|>CtU44SJB{m53(`v6|0zFORO3HcG`0)sfO;AB`WFOH6m*I_D81Pv{P>v_AE@x%m@DLW|^A4H{Qeoc=${?#T_j&'
    '48OHsSc+qiTuu!Z&%K*+{j@iWE%`PLF^cI+uMBjPN3jPIs3-rcw6v4e+02joFYl$_RLOZ85{gs5{S-zZ=%nul8$3VDBf~a`!#^SNaOj(o'
    '3OKor)8LLD*T4q}p;)yp@`RM}*16oru>-5VAsFJ+6;JQQQnAoiRi3dSFm>Ydy7#pzL_By#wq)n7WlG<9!qDkalLUEp`<x!D?05%Q_0ZF$'
    'NG<+}o6x=00uy9x*gS(@n<@)xZGYsGO<Pb5%gkWe((kq}Dp=Q97c?aak87!B2#&CTE{1W+r1wM1j}xw5{ToC{K~0T6<eN+DXi%=H1NNxu'
    '>puuXd!(W#Tz#9B>8Hm@XK=M5qPBQElt>>7oC;M#Mo1hvp*}busj5)MATl#DgLBInLjemKe3OCpC@Bi2Rdv+kFo>8DNP092Ap-sDAxx>Y'
    'ZHv!#c1=I1wBxtQ%8*Y~42+&#M=FC8WGysAgA6?i*+z<<4NANO<L3$}eF83@xX8&_eEib<+hJaLhRqDS)2nc3gaYwQ=pxE@c#!XN{F`*q'
    'b&S{z+Rlwy;lHQDMusFpdh1bLii1b_3NCjdtIb@7rGBtl`rJWNPguLh4Ur|y%#bMr&eS`Hsz^!D7L_0pa(7i_QRrzO7jw3%c72@<&fMwn'
    'bLcgk1G3$5PX8bq&`q12l6CBCa6#eg^r$((RzhyP?FVKKcCZi*X)M<}1DO#h70i!f!ht8HTAhiOyl(u4z-xPc_e{Kuh(Rn3dMG@wLq$uX'
    '6mAk`S<<&)3EY)#$!Qy@6Dg?DGZAv}iGSW5F3LETy%sn0sI%IfB+%PT;EzDlYok;C;GxEkm*1tuB2M3|YdVn4aNRo{=`xj2@PpCq<q7T3'
    'a=izv9457;=%ak^v1&py7)K3v*pgRnX|4JUyrr=$zE~kQYy=<Iq&Jjik)CZl@l}hqC8r}Ke`W;*PF}_=Xv2t&#PbCwgb2%{v7C#=-={&h'
    'C2L%SuHIjRj(TWQsF11^7J4b-rMYYIE{%tzJcom&LD!3w*;Z|ug;cl#zZ^KeQG{H==<wu2M!H|(?d`sSp`StOG*gRhJ*lk~5YOezok;0&'
    'nBI7BO4#)nD*z=7VpTmT8UZD+UN{Qoxoul;4K7Y`Ouu(gY*p}oBnLdZOtNr|8kmO*U=G<tB?#oJULxO`=Zkg^gm)44q}%s@6XH-isJWWt'
    'UwA}{7>s+q$k$GQG968aEP{j<ly=^E7s@I9t8>Cj@!7MeE!*^PEimaZc?&Tj2uM36N^mfoz#3K_2Ytq3#8HjP1U9@xW9H<r-ae59JA9E?'
    '=V^6iYI>nvYa$<n*m?>!S#_HrPqhh|HD<0(EE@$Lc>nHlf%OHh&f_6f2}E{7s!spSA!GopEv=?Y%4S1VcWjM04a^nqh}-=e=v>8fwzBK?'
    'bQG9F$I0KEiD&6SJNGBG-g#w1z2=~r#qXrodDeR(1>rnEpDexr?EO4_f>=e0^S75Tv4mZgY2b{f$Nyuj9i+Ap3DLf#E~4Tna;^r&pPW(K'
    '>+c(DNwGHKyT_n()jJ~UDeQJj0XOMGfBm-ys1FqzNj5T<6Qu!bBqW66Arg-0=5QZZGsI*U;@@5c`}V;wK{6JN2faG<GnObAx9I*q2<}%~'
    'vY6N!(>8k48qgh15O0uq%J&ssPDLUt0klWLHoC~DRy)(w8U|SigBgZ>Whad+HF1<x0E7c{O^dj2_PX4>a?MX|D`jwN;?rPlVz)}634KF4'
    '+Ve{?YPVm!N5ebOXt-@5>)jQ{FszVZ-%^Iw?I}1$m&KA<r%VQ-*SDud!qAwoCl$=&w<5K2R9saX;MTwBn^2(O%DDEx3`2R%XM>W`{^3Kg'
    'iy(svPitb06ze3k_R2NZB9ym>ySqjltc+rV=&Sl!?ah|h$80`k5#Iz~@kwYoP}u9oTMc(+XTzgzm8D6;a%w<`bG2nG$9+T`>ni87BeMj<'
    '6KqSw1s0gBM*7faXTIsb<r)Y27=Go2U?QPDht{ODn8dn~HeE|U1ci;2e}y<ox5TQCdH^*hxf{)Vg#KuZw2W4<(Ii`L$`-XR_)zAj@KZU('
    '-c0pRovtHCRml((y{yXZb|L=0ZyW;ahyD4Fd7c?Y*TeV?ioCwwih^uNN{O;$<ecio4222{-7Ka^(^0S#HiAH`m0?PO>_}n8$bWCqqP(fZ'
    '-;Z-=bfl#laz3_2`k$@KP(uJZZw<H!(-8`OxDs5`YoEsYdYz{;)x>(IxgTYHuwMtHE;r&&Y7P2@5iu4C9xCSO^@kQl6qr|MVRZIu3Y{uq'
    'b6?@I=B1kwX$-Y-p2w;CeSH-Zv%3!a4>sn=2B$5>qjg|(VTkIh7qf8F)eH|lDze-1j7-K_3TW}NoBeLIRF~MV=QU+3JsXkW_75{qp@3yP'
    '^Mc7suzwC{zLz92w1#G6X>QSsgWcH)@H0kV)st}znb&X^-_s&3E>KeeawO@qK_wG9cyw`Y6|$O+hyTDJR4je?j}OxF;~{IZRQ@<6t?WTS'
    '#s`cXR)|vK=4c@Q4o_kvti-U+tNmz_x~yHIht0*-tsC5_?8;AfuqnSv`0hv<q&`%%s$Oi#SpZ+6__4<lAjkJYPLP>B%=Vuv^FUpnz5UUB'
    '77EuxcehN}F>4#18o1Lz@fOx8g~E}!oBz~1BysHZM(WF^KvX^$hE2xpeE^ti>q`zp%GyVmbkLSzBI>N{3#^-Pg76hZ&CpGU+$7s;&&7kQ'
    'SlFxv+@2~6z_I<VjsmmZX9!3zOR-nOjQMmy)!|^MOhugPH~0RlciU&aWUW8pzcg1=8$w!|ihAsAY7qSRaG#@Fw>-H*f=vE1Z**iDaIeQ4'
    'ReuT9DC=c0^~u)&8ma;!>FNqL6Kkq3XzuCIlv=f{w>vLM)O)nCxszc!2c@|gP-LPU>ed?!^%Tm=D8m8Sa3<mrMLu5?N_!3?hXh8+HBH!I'
    '_|KS+6`lTS=3paajx{J$YxHE^TB&|vg2}zdFs|Y~uwJ=nOVoi0Ak<XO_rP1;=bb=DyZer|fxz+z&`$iF(AquyP$+`P8+wy=ncqQl^St&S'
    'B1t$}8=^XX<jo`7XwmW;$<qWKZ{*s+nl04<o-oL14aVgwbNa`bYu5O}A2Jwz2MMM<zE4?Vi&gtsa(E6XO9D6KTW`m(;WvqlhL98$dA?b}'
    '!Ul1A$ZN)R>zIcVSUdeCP>|<rPl5+=(N_ZV*D4OJb4K-*e6pml@ndld(L>-X;^@d?sfesanPeMAJj4pTnBJW%#r~@luC;T6zpz~JGRU54'
    'N*EpM$7$ac-r<S+)dv28aeolW$=w6I`+DGr9Bd7B%4kk2^YrzT#M6ll&gf1YywCRxIGOljck$s$-Q%My-hDS7tCRVR9-QK{iyl<B@E?}<'
    'O+a%a`uAl#dW%|&CB@@$F0n)iaz_`pE3Btfl-))756*Rj`);XZyp=Uwb#d-x_{*0|xMA_Y+=cS2O-UZ`#jt{y!rR5s?pcs%a}1lGt@oa{'
    'N41j+c<T&0#bV3D=h(bGq<3;d7r#vP3G?Y9&z&Wy*<mzH{9F40DbViMleuwpiQCwz*HgP<N>thPq(R{QkBLM5cS;BY`n~W>*h^BQUr+Tz'
    'meue+y;O(U!_z^$q`$}*9~g@H#MyIZ<?J2a<!PxD&VI-7#0r+0v<XuYYgL^~RUqJ6=8-U+Jt+N^vAU+2$g7@dGuFM2?X*JTa>5~ar1H4;'
    'vn8g>5fyFF-JA#(ckB0+>mDXU2Y;j@J^G!XGWQg}tS2%zkQ9u7RmkEZmlG<{ifWJrlF1^rH;B%%>0NBpxzU{%9ItkCkbE<2Y6W>N)_5nZ'
    'jHSxN7}!p=-@&7|21dqkH2`i!?6Tb=9?{#fpz2DrBwMqq!R=$&eFQEVT9L_)P4BT4<T}d^tXSG~eD3)2f#m+jjB{<%6Sr!qMk^9fLwC4E'
    'LT5Q*mcSrrhF-=Eh~%Qy9AQJLM3hKDS|X9L&Kq{<Z^yx3=;JsRNpU;RsMqjI&2^LY^~J{#9zInEb-`cv$f!^m+^{0?V=`jWS7@-Z2}JtB'
    'tCQcLqlAXZ2!o;txLThnZcuTv@QS<oF6|hV-iEI>^YZ+1xUFOw=3YM>IZ;V_vgCTW#+2v8pr{!iiPO>4C8%o5nJQ1YB0)s+#J%Eu`eD4a'
    'GL<?*iZbc>;XH;nbiWHZY^Ri8VxHavCJp9b?6~!|!|jijg%Qn^Zc>|l?4k0IGw10#+Skfn;lhivZxubFv6l9c2j$1$tt^L!K%&1v$AI(t'
    'n4u|)B>IhonR)?i-VFH?myl4W>q_NZ#;CD$(90HnQZ4r3L)^Bh2rr$=N|7@!u=SX*vpLX;*J$yq5k6rgpqxATO-_WXo>A;b*n*s=+MIV='
    'N0j*`o=WWd&USil+0}J)bFL7Z)}!D9LtJ<AS~R~Kj;vkRwrrAIYb`EjVJePRWX();bdhlNn%?GH^&1jH6|ZPwnCVs;@Zy<GpwxU@f&S8i'
    'aBSSJ7d5*5K1UD#<%1o+n320&fn{ed$;XNo73E3&g-BFo;*SkFa+4{(uFIn3#P!!oQulPpEKFKOOMI(nt>hU4p{26c|5K4aT1(^EO5Xc}'
    'tX<ak0V#s26DZX0n789;f>ZoiuW_$>u=}siCT|S0X{jvGQj3ZIFm@5cYBYum*1m!k(;SZ*m1CtqvSs*aILSn}uY;BtUKoVFtqlx_WBH2D'
    '$R;qT?laA8KM*^OlumDaY0X5G>G8t;f9ommlIej8EdOm;{x3bn_5bTB5-k6tr||wa&-ee2o`Mk}OiV<a{O6UD5)`Z%$S94^jzPqC=NI-h'
    '=&|jLAjq@mPToVH(RblhS=HChm*>OnQ~oCJ*zXyT@(KN0_NjNGHbro-cPg;&72t>TEBHJ1CGhFD*%y4bKIfvh*?0Zv|6BKS24MJP_|ik&'
    'Tk|^rD7?}AB7Touzx6{t>D>!_`xx~E_5k}?_I-OE_#Sv;`^f{$zWxDtj)gx7-ugcJ@&JScKR$m24gi45vJ>%VM7>{&U!$+Fn>=&B0-u`S'
    'm0Pl6{`nT!5BY6|8Gy-8-S^x#{EwSYZ!@2uAIY!MuhFC1V^usZuy4vw+V|LL*!x~+N2f99_ubdpr@$;hEa1|eV;=Go^S@&R`+ki4>3v0j'
    'wcn&Ck}bV+z_H)8Uo?Q@%j6aMyY6%Eo8eC22=ELj0{{R=cV+;)c7p9V0RHJ-jR0WgpshiZ$X%>P^@Iu7Yj7ecpGR?)OBGMZOI1e=0>Wbl'
    'vW6fsU=iuAWKX}iJjpkI%&2S6wHz^apM85FW%_s0NM}CVL|{95&Cl-`su3>N&K-+UXgKsJ7c!YOwlyj#Dy1^ai#a5^qpZxrjZ@@eG*85m'
    '*ZUIZ$xn`@=Tqz~13fwifZPJHS%0~!^YIjacGGeM2X6{&4;~>>KW%?fJ3Y;JMyx^vCP5=|Rv}JDt34kBY;hls2~gRIe&JB_Bwfw+RYNiv'
    '`%4;S3D(70#6pP9YZ#CFxc-5Gh%B|DKs$eVK1WK(;%x!o&pGvG?_@)d6V(YAKf^Uvi?cj-UZ)Vt1m?>;UXmOPZdzt`utUNn=sXm*`y%am'
    'QatHX?i$twk6E)4ooCmIwpbV#<<cpyhZ%|`RJ@W8v=9+d`YZQ2lAsi7^gYI6Pb&Z1ijrI?xlpehjk>6Xh&mb&JrfQAO<_<CPe%X-BU<F-'
    '<k{+x0CLchvotTHW>Lbauf11rTr)*-Z7T!a$AuBiTz1Mlv3WJsy+?0@7)8&OZJoGWDfp(=Q!NP^t7gV4i5>&v8n<FO2kYUw3rvY6f|=o`'
    '&>UIo8VIQWQwqgr;!sQ3i&!rv1xq#EhCeM50x!}&EQ!)@L~Cc>R9g+l5-TY4*;ilUnm&0^YaENZLzhW#-r7hx&u}5hr$oXY+2c~FcN#!t'
    'z??Zw2Wht!=FBzK+vY!IjqT@olK7%2szLdh`vHl$kK&x1^;pcGOYP9mL&6L$@$aJcw&e5Y%#+nLS`hJsm3xVy=nJ$oIPQ-pL9UVZrgOi|'
    'ZHr|=ZCIQjLv#R|GdzZu6+2GzoUV)}*L!AYt=By-jD5hJh30yJlS?IZPPjAT5noTUFRH$ZjBtO2sXpobvH5OyRtx|YQMmM2T>TvkoaVw9'
    'X>k=!FSdbUFkmZ{aAgcwG5LM`p(yd;J7(LyN}takcW0+{+*Y#C!MZaWNG>Xdc>{r~jMa0wZN!dF(FR9!<;icpP;A-OAXTvz2LbIEvhOFD'
    'zWB4Opo{6W93DkBFzgfz$fsa5TbRk3>hR#iLv5@Gx~ABN7)}srDC8?vgPu2~0{FGB^yWV4Qsp}OSp1uPcDYScB@O=UhSf5_FEV>tbjwu2'
    'EQN22elCyniTFZI0=s7SjB;ruh(o5b%x32E{%?oF>Hh9$n_z8>_o!FH4x@-867YCtu1LUG^RCTH7aP0?Tp%w21tn0dp-&J@;3@Ra#XgZL'
    'b+fJ9!?Bfhbhf6nM~M?J@76iIlnc&e_ZQq4>t4GkRFte%Oz3p;Cu&wi$>6!PCF%L1`QA?1=C~^ixMSy=*uTYa0_<1W&&-iOE0nk+@hPyb'
    'rtkWhNhJznyEJF3%c~1#5g(;xu1sn6`HJ;I=+T(5RoNgQA|C95Y7AOr&6?0XTrNMU1OUMPd9LwtZw;ymZEE9TdzJp|G|-A+6Tu@n94CfW'
    '<59qt^_CX@9o`AOKBAoEw-g*AX0bJ>wxfs}@}k&iaO^=&z6Xm*pMQoLMU|z7J8cBu00-Bdyn}S=ihm<LN;!D2E+b+rlP_<<_knjS00`(8'
    'aPN+aqaxbA%yRT<zDF`=xW`E3T;O>V_qTmh_!UeQ{me!G$t<)YCX7*DuQL<QAh%=m%!b<fJ9J@ilDF@LXFnXkzhqyP4uw_5o7gf1-*83}'
    '32b8jn}JAel_K2~fb@@^1*UOde4O>90SOHoz)zBO*(Q{x%Uk~Eco_Q6R%ANzZMV7K3}tQ<T@b}r^IDX%lj8TV1JGIQz<JPkRT}6BGwOZw'
    'V%vs2VYp(+rj=i6>9biz2JI?WiVvBzq>Mz;BigwSsn6Q*WIDU3B`W^Q*H5cm0H;9s(^J+9wV*lyVwoE2p5}rBR3{h;XNuu_h-1(6y#f*<'
    'X>=@IQ6_v{c!^51`15A_9<RPm!Gve^z49dju{;YG!R~$hn;HFGufs+c?~UX&FCKHw8R}%9{tI9sU7eaAUzR;d4u|&K0n57s%&Y&#!qV%{'
    'K3oMqp|9RHdYTe3ukUKaL|d{Jtgp(?mJ0nVQ;7#o@*32Ovk8*K^Xx~{i$7PNR6kbqZJ@Js!A*W^xI`$M{q}g&VQ$qafdgrRlU@G_!+77q'
    'jBea`!gUa}_d@bJg@3W2zw~x_Rof|cL%r@pT92tzofLjpY#--L!?iuW%2>;`vBTAoS`_Q8zE7xmBT`p0g>)8Vz*R(*9;qaQ^e(Tqz(DqS'
    'e*Twp@^}ZZ7eDo=k6?EsBPy)07oB~I0IEB}2&~!L^q-$Mjp*EM4#D4=l2t6j5S;2aCR=cMl1lU01^2a^oFJ>NQ8RlHEg|I9N3tWU!yX&n'
    'ZoCXIE}{LE+D`0_zpa>VTBK~JKn{HG-q8`gMCd$>WwfLhD4&+S-LPgjoXrc1!vk*W$5s8Sy*C3OTjU&VqDgd!HkI7^t%HZfd1CD#HcVHr'
    'Pz?o|^qICEPG2lStrS#+aDLW#2BEDZh{Jf}6Ei!q!{_rsN+lwM3n190yJQ>XRVl@07KKsF#xfe?T}vgZ@gP6%fx<?{DaNzADZa-Je`#w8'
    'mWWPd9SZ?uGLY<FUftw=d6=uw24O(&>qaRUn?syrR;vB9-8qz;gz1f6y$WJXo6>n}Hte>Y_UUX>M&B*u4IqNe2%IsPW*8#1uh+O1YGD=x'
    'Y#+9OWe`FY>F$ftW3p4NN_yt=MW<a>R(+$B9G_0eu)ysNRcTZ5vhos%uOyeYf`z((wc&6Nb<a9V^3)=PLEBMA4Wi&2GmO&`V_dtn<?R~S'
    'x3k$#?ek-EpZtLa3~+g=eYGm&!HvBE>0B*HAsvA$X`7F^mf4(~DI30mc$NEvHw>73Rz_fSJnDOye60?#z@)mempVMR9aI4s_(88c(<u#{'
    '>5c-M==M+U9)r4C7&j1AskO{m7QbQIk<?N$x7O4qE1zKHUtABvv~+;*uJko^4=fG7@n1<}gev*X&ewcwP0kj-6nTdV*dzjoSqnD3mkP=x'
    '9UN77>)#lw-I|UKE`34@hfUl|hw7)>>AKXAZZUELv;9AKC%84K&n>!pz!Nddv=nzldg4a!KI(YIx#j8yE@+uT-@Pr9_25%aatOR9PgU^y'
    'eKS!2qm3T|kEcl)&N^}peqj|ZD#ED@V-H40eh2dFOabjWJO+VNRPV#jNHTLfmDJjzSoDJj^uF?N&2gdEDN{~Gp%O2beY6^&&P*0)lAcDU'
    'THf&qD#SKX&=ICJuhv<&Y@adeUQg*&5;i59Wn8O<ttiAT|23bGO9^Oa;U|}y1K|&xXcTcBSeHpKF*b{bS>#;-K%kpo7DqUGZ)t}7;poL$'
    'mM^Pyl9nU9OC2G6s~?Q6Y|km?+v<Qw6yxr=E{?3e((Y=QzU<L}8((No=GL(Slx?c$$?+AQ*=tWT5`LyX)`@MzBmIvS?xS#_<~@XI(=P24'
    '-@;Fha3AjnIw|tr-OjMOfAHz$FZhyC`N6)Ah239ERBeI{m%@q&aKqH3xG54%w<!tEvT&rxEfX;!1p!nlo*2==Q)WcDBq{-^U%9{qp^1nT'
    '<9z~ob5qAcqN<wDpLr}WYuY2z>S$7=-sfR{<l?h#%Nc2#RwmiF%3|rX8!IJwo+>d*I=0n(5qW9d=zmV_^kI$3Bqo26O@zM6-zr0cq9=>_'
    '=nbt}vv?Rid`!H~8psux8!B6l{tmnRj6a@bqq5;HP5W)V>)@zlP!m?ohX8PiGe{FA3f*CRO_hN7)%dTc%?z6Q$IjH0G*lJrg|xNOsMcg`'
    'lU+Y#6Ei~bamZU`O|Sy{F0$|i!aS_$p^hNZYH$cuSkE~eaCFo+I6k7%5-NU<OpNb^A~QMAAy_m_TMNSHf2`W)iWQfA)>FEz#8)G}-;Sr-'
    ')<)wp|Ima>$yqPaD92HZw3(_EIkY#tA4mC^Y8F~h!1v-hy0xvcwL(8dHpTwcb~gO12s6)}!^?AWhvjP7HTmVyhNQ*_v)C#tyzG714;rE8'
    '^I2^w6)Mt}WIFB8bA`;=@>k1pC4ke?PIoDsiaOjb|4!A%>5%Ed=49SRP<Nr-LK&KCYO)1$O%{Mrmi^k0yc9iIFu$P!BU*>;XG;nDXz6kS'
    '?c(tDl8)xnSZ}t=iIoY{XaAVei<O#|8VJ|G+{B7ZseDV576d?)PA$+|OiaZQ_)Sx(gCDJ)l!SsdFp^<AO&YwwC*o&Sxo=&FYG{K&^;MPU'
    'kTSbx3QF1A{`4l9pfz=*a{)PfL0<mjvH2`zcIkBw&A?kW^^^>aX5?})dvH3OHsq|w`0r`#(cbSXgmLatO$K${Ps}{Zx;Z-AJ>@=JTIm6)'
    '(hyJ);U(FCdr1glc4HnD=BO!ky-#aN2|C`6FJ>zT^<^72sf|$b@n_wS@w5r8wwFXDjap|oQ<j0yRFhud=6^L)qWC5}WVDjP&Ukq6oY?0}'
    '8BncNI!Huu9~)xRnr0Wu)v;O75{mGxjF!1GJ*G=NZLPsQa<67Uw4e1!TM`mrzRgQAG65Z9Crru~&C`d%jgv(`vC>J3of#_VcfPh2UMa(K'
    '@Q)xX`<BaPZyf00AF3DfQB$iyzlkDB!WZbiKcD|&l6dQ`6Qi*A$~9;0D#9Gt@x}?WRO?%pd!s3q{k(>AY%%KWP#z$@<aoa?((Bfe9x4lU'
    'kd(7>ER0Dctw5zHl^sHPmY`*g;m$8B>8(Hlg^jX;?oh$X8a<)MuoZS}1JV~NNQ*on+=;4!yM51W-g_s|qSBZe4`;Z%|F1XR*g}oPnaS3$'
    'sVK-D&ItQ)3mF&(CHdfDdNqhb?;Aaw+?SC@in)A9hS|OsT?ibgY>toE&{5_gil_cbE(d0EwyH|u+~q2=VN>@b?kEqk+6+-eg4(pJLU}pO'
    'x4N;;I$$bfm9`)D_VOBE$pZ(;cmP{0l!cd$#Qj9{Z)CAlNRANxo&=B;amR>0Ht4Y1-t*JQY{}n9$QbF~J<;-Fp2}4jgVgKujs5%LvGFjn'
    'LkpeRYlMA<BLvVW_O>cN@ZKUC*m#@^VE_Y?DVqf}e%_l0gws@-&<Kb*WRJiB1Qz$C=z5gzpW~h(Iv%IIbmN+h>vJhitXMY7tJ*r3WnE<T'
    '8QRCs->S!Rm|FOLqWXY3adX7@B5O|bLa)qF`Ve`ejRS^J`<AP@nHpwdk9mv~FW4UoMacS3j8X>ttYmlBR-38`oz%%sG>pc+3s~@{Ft3~E'
    'o7Sf5Ocez1U!s8ckQ~lgJXs;)YR)uRng~?={5!t?VjC3-j634Z-4VmbkDp3g8h}HKd~s3BI$|~Q#VW~?rH*>B;y0Z?_zkqCle%Qv4K$v('
    'Jj*_lSJdNU=Bt+9BC-M;Ng;P&@wWi?eMVHn{+f|sqSw%t(ppCEKHqaF@9CZRi>Y)Kg5h@ZQaLBiqJ^)CbwL*0Hr}bx+D3!}KKJ|HQnjjA'
    '9)Z85cV>EgGb08X#s0_ZJ&#2-#Qy|NkA5$a;N+4K!qG}5)3)UyNCo73Ez?<xWMET{;lXp`;(bmYyJw;%=K&S=;s^9PmN(7!*UM4HIyCLz'
    'a7dflUjys=TI>nmaZO1yVmCI8pD><!T<f^}Cw+z7KWaNxHJ~c=en3+Eb}`qg0-TNTNG78I)%K3mbmJ&Wq`!<d@c9-tDUjR>eHF4tqt#(D'
    'A-yY4wWzMT(5-|Rx~PCUn>fNc<6toPJ3Ca+DEK%Ch>JFHk>i;|p0K8kwQIo~Z?$3(IuGTw!W?d3^+6L3pa+ZT@b;HJ@POm+AOwyXQd|v1'
    'v0cXG0IiAmUCW6A(3r=i?!xb#Uf0pd3cSj5Vh~DVFcF~Ae6dWM5j4@B#K%luLgDYg**XF$xTSC{E%c+Gq7FP;w<8_>dNp&7fiXFo;0xd<'
    'AV8WnM_w>si2`@twT)TDdu<*<>}a=QgyazPgfDi#v~z=oCl9AcVkj7+aEChlIu+W?1+kzi*wFE0xj*)$X-}FXGYD3Y2|+svb8q3IL8e~t'
    'cghts2CjGtnSfxS6>(zfjX%LJtBv$!*ssX)($)NT#BLmK|K1g1lM9{vRhmjSPWHiE907Ko#~bL<VS|X+_-<lx-FYdjdbbY^`Rf_JB&4O#'
    'RH8xZDutQm3yi;OjbKpzZkp;2^|)30uYFA&y(@t+iHGTFB@0hpf4l3G)B4ruAtw$j&t+Yf&jyHmMJ+Nwc%0mpofM>Gukc@2YBM>Yo9N2)'
    'ukO%n4BrL1dSpPZh`AZKcxk?`aQayS8$!Hu{)0(bF?tq%4=(MGVz!@@uWor^-A0mT0xag^sGUJWB<%({0s!UWIaO|-x9heW8Z-HNtE5~c'
    'zToQdi_G3nJ*Ug9{;w`OF4gBggvoG{9jc!dCy<X?0!cnwk;21NY^En%(&8LpR)=sXa1~3aSjU?_XXU}(K}$Fz)FzJe;SR<l)J+x<j4AHV'
    'dk<H6u#53N-U6#CYznff4*@Mt@ga;EMqGnrRVo0~&fFS%ZMnZnBnV(ZL|jh4J3?KZdW{fvlZ;=bjq><~u@9I|j~0o`Y>OO`y+h5Z+=&6-'
    'H(XwCz{d1llG<f3ZQH<{qgeI&?I)#T*N0FVid=H#hmy~>R|os|339PsE5Rlh#YF5zl)qir%q(R?F#ZpxvN{OIu`ArD<x;xP&5@*lodjaE'
    'zu}|9<o-qWJ|$h&=t^<sD?`${R8l7>vf>Jf9ueteH&vf*Q5=7sDp&7$+^6(be2>D`>OIx3NObN~Idmv2U<Fj*p#8Y!I`bz<*AlhU&H?%m'
    'Nl}RCXu~PB6L|gI7KED{w4z^@kGmb|tI8;p4>wXMJ<boSJhu?~R_$E`B&oo1YT1CCemtSjG*QI$%FiWp*)M%%*=u!au6p)NbI0p?LJ5yI'
    'A;j3^yPeGv&2baHhTNJ~6Q_`Z3}sjYvmcLg=t*mxJR367l3Cx8A!GA6K5~<0Q6f*!XFp9Cl4J!xF;}h$EP+5F(BGaADArmzIGMqSVRW~-'
    'qFgllebRMs7)BszJgd4=s#X*+1Gx{jE8#(5NL;ih4h0GneliQSX!m`t2Eu?3qG5oLG<Oy$d!lkmw&xY6KzDiqVat<S<?{HiC+jQvLy%&?'
    'Yh*(oFbCaOs8!1AK2{Ez2E)P2_51}iRB~SJdKc8o8J|Y<rk-coRb<!M(U>TysPEJMgvE%`!ti+U!G0C6Y&(Vzt85CD?ZKLeua6(QR2}3|'
    'QVMR7oIatZaS$+6elWXZBwyV@cNs3B&OuWw;#d@jVCT#qt5Iw&l9!a;%^D&yIm5x2-@w}Won60)0N_%4sknpfAkMrmFyBMFHr8hAgV?y~'
    '>Av?_dTgqaTM)MGv*-w`V?9z-n%fAR>n^oN99rJ5^!u>>y+OQjlU8+rv1W2kYE?NUO#r18&^H+2fIQRM>@Q3@h9b4e=?-Jx_yTb3(3~+3'
    '(aLh}te~%>AroFPadZ#q0@!3WXq&I|5$#&_t%$n`)kABV?Dy>Gnv>d{C6RDiCNN4b+2|Vof#aX6<wEF#penME-XW%bOb?~%T_p{pQA^vm'
    'Xttd)eSNZKs$fJAzu#5a4|b`40-h>I&5&Omq8o5)jPKB=h((Vo2&ro5J?Mi&wqE0B2{2s8Ug_(hrZ{)~0k4@}@IF9KIOW+*FL)jyxFl)W'
    '8%mAz`6-JkM8{Qi?mep{=^%6pc(Qx0X8CNI^ZKfU8LEc8`7Aw`0i~rr7>}(bJ%h*O+FF*2Hd$0AQ+R|CxV{{AmOasUyT5seqPtbVm01W+'
    '0&K+X!0dU`AO4&0@4XJG!rE^yR`KM9<-}B(hmn2E5m=I@d~*i645+3{s+{oWH$Z|^J~i2@yqKkfLgw<_-qa+Q92P3BC*}Dty=ST10^^^w'
    'WR{2gPw;XND!ahO6s&NbQjqsys+x5(NBJTH_iZQx0j3UYds4R1S3`68tug}fToxBp*Y3E<g&Cl+a>5}vy8V2A#>?L1orRTjU(jk^Y@2cz'
    'si&rGJfHw$d_;(f>ADyK`s!#&?c>8b(N6Z(%`K(<$dbruMqN6#L8AioKQ73H$3e^8t?QQ8W5a5Mio2++^?Owo2<5Vd?F*Q<W;X{IvAVvi'
    'dT~z+L^~$`JcMOPyYKMX^BhvGea@JN2^JgSyAthT57?1pf=Hu*A06|HJxH?1KP`5OVh}?zs)%gOG=)p!${*msln1!N<Y?F|dbG%wVX*j+'
    'IB!8bZE^T2rpePpT-SpH@+wyCf0`oNu#~|tp1T$vbMDdxo7mdm`5KX5^!~tK(e-PtwbLsuj0cisD%Ww=>W+gRF}3jb(MCh+v3#${WcnYZ'
    'I-eHzZ2rvAukmw3ck)D#FY(q!PsnTg=p;omdu6`XZ)kKRgKA+`gwVs|PlGht5Bs)>)Lk>b>uv%6-Zo*=(Br9Ax2}lr5kb(~`W1Bjrc&1-'
    'Dxi0^z-gfF$@Vsr9u$c3&@eCUbk``s5)b&aCdVT=Q2xVZ!0M!3j8gjES6E)=hiN$XF3_i5`Asa^wybtY`3sF#exiK98F+K5t`OWjt|g0|'
    'g`p_EL2;E=Q&j7G(}0!&Ys;1_<@pa$!Rc~p6ZmK^0g(n>Y3OIM-<T<j&RQCqs^T)7UzuO-{%KhGJy*-z5+l+|hf)w|5$;p0NYns4v9%il'
    'QhX5i725Ic7fie6x6zs;NBUG|vhJM$EcCk=R!rfnRTEn_3Q_1uPO@sBT=WZ6`{*Dsk&kR2iVXVq^mCi(#Tci%9WRo#=0vs0XZH_!VraDC'
    'o3_23Yb0*uqtiX&|10dSg5prpHUJOq5FkKsm*5QUF2NzV6J*d~a0#x1L-4@~9^4&*TW}2!+}$NW{&W7Dtv$81+g)#8bv;*o)m3kO`a<Hn'
    '2j1O_!b@CcY+x2}fusCwjlmX9`C{MsMn;S0@0D5`K_`PqEF1;{zh%jR!8qq}ZXWD(?UI%=lwOoy4m5Hno=n2-mwmE-b_f<iWk#NbXUQ?}'
    'CQJk1byiP*&U_SPd3MWpJ~hQ}O3@d+rTEY;l+euA@@l8!UGPY|z(sSs4sAMVP8q-p9LStcd>628#F`dG{CZ($>RnnJ8Op^hc{BSB_Ytpv'
    'YKS}bqPOMrlp1ZWZt4P%)hOh;){<0F@y25ai8vA-Q^-00fe77As3es5SFBYrLN{*DKv?wyCPI3Y)2i@o8BSLz>+z748wY*kK5K<SPQOMP'
    'T+J`KHx&<sY@A7jev>lc?Nv!F36X%P-g*>F-3(P{*`spbJ?{rXr-h$iqKD)$6@4=<34+{)EZX-AcHv2&;Xkyi6j8sMYiY_gKB<I6owNI`'
    'l>|mP!el!cly7SaFr<sX1l-<94YyBAS`#1vO*+DiLUUjFu+Ym2l)%lTb{MBrO8uNFg-mvdUDZh&^}6fh(8vBhH%!5=CFFT66IdcJCu=)H'
    'N~P?mYeL!`)7Rax!VjZ^nZK*euaAbME16HqpsEd~a{}0d5d{>*W|JZwG#A8mtLjCQJA-Cvxnu#vhaV?&L|!VS&28%W)Af|gi0xG7rTe<S'
    '$ez7?z8+J?h@#NdW#=mrSC<m=K)KRVmt{98Z;9>B)HS0tdM8x|tPiFJ1OX1lni(jEd31bt^XA%-;Fm5?&xk)0ZHMUl_yp^y%{ty<Pt+wO'
    'f#}dqG=ZjrE=>mCf=I6oanb^kd}<v+2os#+m1nqmOvJ>&UZFd$W6{u5Z%q^AcLU0>n}@=v*#Q=&^!>YQ3$gKFEorNxzA3zWkT{isADo)I'
    'MR}Ci@i63#V|v_yw-*ORj~B_3a!exMU8jqX^v5w<wp{zDq&{wZ%t)mg@2)}b9g>>TXpN_|!oY@Vw?vE5KJCw6`?uC>IjpW8GKPo!+B!Lt'
    'n?6polGL!*5S@?m!0yb$>!LznOi%tEZ`_VJ_zE_z>UMi`We?!m<erU%1@8+xR!7yMm?5h<qMV|gCcVwvrsPWCI<DDNnp7Ol22>a!t8IF{'
    'i$C_zg?O$6y<a0n$n|t<lDB-GxDZqw`44DdzVkiV#xK*cqS<eg<4{kr-Axf5f3!>X>qt?{XBWNEvp0+57_9UcPc{Tcab^efA<2y~>A5$h'
    '&m!RLG~+N6x@ZMoDcpBKot?ge!ChhVI$b}97mqS6k&Y@zL{Io2ir&0BX_h=x+g9YgEzU7|&)$rMjTT0~F_A|tuSdU6vFMP)G+wWBW3MwQ'
    'mhRMdq!Yy8Y2FtDZXy_#aLs=~Ac67$XzZQ}VE$-pI1@xbD6-}ezIJj!HGp&!e;X6Lmgc%7i}OfIAReP^d4uE$fmLFAw7B`&k;f7gvmp#z'
    'xqj=@Y(MWA=?oISu9Y$MPG8|SQ98v;oHaotHKYDum}96eEP|a{dT00;Imx)uHNwcCJM)b}l{d+tbuQJ%=$24XdGo~};prhXRd3CiKk)=B'
    'R4zKe{iObNy)WOVN4_K2eZZFJtnKVw!P69Lew5o1R_PjG!BUWb(+DP?I&5JE%19OuQL`ql98r3(JwP$ZS?gRLr)c)0>f_uT>c1yPQSD<U'
    'e~bh@3r7>|(L~53DoZtve0VBwOy=O*lcGhzR@hlgz39-?|G5u>@q7)mHi{UbJ4+-Gi6P9WM>Ji=1-8L>hl`i5f7nl0J#=hGSE|11(Ih7J'
    'Nx@jdgq|DB2yeX|tVoK-I(8NxdhXX)>XvNQK?W^~#cKG!-<{RAxNn|WfCrjxT5o;CMN})<JjLL@i!bB(K{_hA<dSH8FBBTm0=4!0cX0ip'
    'uCm5l4=`AtgBn2dd}@QxZ#-|V#I~610I?4kQc%xNmFA6Ie6xP|8%39co+`En6hf4o#%GcIMhI6nBzw%;hNyDLA+8(c@54Sa5g-{yGhn_V'
    '7}LF%j?5`c#2$Mb8a<`fJ}QJ9&^&}DY{V?4O!2_~Vo>8g+aQW~OcAZGXDl@-d}RqwBZ3?Js=rHR80Uy%cssWUP$sZ@S~9lwEqUn|>Jtt?'
    ';Xl{D2SssNXTo`WBW1_|z@_<b6lZTch`J*C8@-z72*Y0Vz&=%RqTW9^<tQB1zK-pfx=Tsoqi4{KYuJdlVQy*iwEX}jx5#3E<YK4FPyAv='
    'QoCY7xG@HgFyEQ|N0sWvg+pshDDvqVc660ip2n}iR>y$_N!=kbvfU+O->G>ev1Tx?Nka;)!=Q$88oGKA>3bL3t~m`AXp)`pEfT!f0LgiA'
    'ipst}t#3#U-zTqa!iXIkvj$~nhwlb<N9{v_%O<e5v<U-(@yA0{s=k-=LJL%rXcm)r<D&%deA;Q%=%+JhLr8}bw!~B(Ebp*2&CbAe!mJzH'
    'iFio6+-#&TTm@snDs-ePoj%EV#!Q_ZylVPV00_1vi_F<XLf5$gS|D*(lTDs&wK=VMhW%O~K6-V!5)}tiZoku-edxWZt^jfU3n%PGTywY1'
    '`P({6xY%uS6JqU^^Sx5pSl~d*ld2i`G@Kz_dfgu3GO0TQ^^{WC^eJ<n74Y<mUa)-7_G$<a7%rX^0P4}nZl_!^f7w43csZ)eGo3oU!-J3f'
    'qzS4-TWmUco5hUj#uigb#0~?RFRd()`?(2@**mw*^GE_O<eKx6kj-8$<iY6W>-JlQ0gR^z2Fvf?yeV<AfN}qLpwOzGKK#Wj%rUU8D<$?p'
    '#Tlfxrq1F-a^SR?iqJnv*UZYB!8#H-d4>8o^Ng0slyu*-J$<7{Q`KD?Hrc%@@s%RgWKhU+$V=i^E{21qQ%FfmZA;`)r6gEtvM%WZm)h(J'
    'eb&OZE<nC1-Z#|!u_S)qn3h;M>8r03rx?ECVhSRqYGcjYGL5Zc!Y?c1VQR<SHjL;+{5iT5-b&_h)6jUS#wmNa0d1)H7Ox^X&Pz`w)quN5'
    'I7SIcP}vxp=2c_)^@$hJVmZA>!Zk9VXsz7hHcJMMsN2Oo<TfUgrdMV99r%aJn&a*JrOtK4y{KV0szMDE8O4ckEXJXT{J7MRC)JOzTO=wL'
    'y)ZHpI8v4R>gT{xG{KN=x~I>R<m@wb0mZb*P<<nE8%1Vg1;<0WouSnGb@@~zZIQU;6wY*t0kpSo*P+0YB)mE{U2o?s60vC<EOw3f=ff>H'
    'Ax06-82feiH6^=?<AJdqxm{XPVDXROfUq{f-mL6~KWqV6P3Y<$_dRypYMPhKzt+xiL65oOSnWRx;aXzhYyycA6o6mDJ=xzGS(25xmsWY2'
    'h-520xJq!+<Qb%B<3z%8Zpyt%-ivGxjzN8VS!$6D`F#-(be~`oa^g~4#-)IzwZbpo1dCc_r&#^}FuLT^$*X4(6CVPV7#HoOOfK6<N0CfZ'
    '%la1p5xkXd-@7Z`P^oBc)5|07yyJ3lx@W`NjQ86<1;2zMWf$App0_J7mpb&bY<!W?4^(x=Iof2xc{d)Bf3I)u(z~SUr;zQxS(`iQx4#Vq'
    'lL&Qx>^iwdtba05dIvwVhPZv5d@{T2)qto9S;A-g={U*~(}M6zWo+o~M9h0r;WxcdZ-)wgMNgbM48fj~n%a)&LE|v?4U6By9*+cfyH*?M'
    'k<kwxi@xZwo!yC_$P#xYxPdLKI+KN`cylGVUb+Ku=?~qawWtggg%S(syGyn86Z@C>>`Y>AKxPF6=tIE;z;Oid^G$ANjdN&{izpMc1u*Lz'
    'frM3(MYEwMeT!t&6205_@BeO{$)_ASAbG#2v$J*vpjFe8R!o|DKs+RFjxc`pb3g^;k*y9KY)kfC^y^FQW=A`I<UNY&(<b_0p|*QY6xQ0!'
    'hTzJ(VU_A2ApoxxCf0!-7)bw`7#2cmd0Q8;2z$vl#Pg|3GvuirX1PW!mz+)RGIU=-^&NGRB)*UZey**o1Zy8gFPeY@b|BiUHKa-9hOTxr'
    'PKE)MLVIhZ&-y&v&cJ};n5l#Fa^xwYPZmZioR$bdEJD$)JF3p)vo7ni?|0`X$e|jaX7Pml&(?eRH+`!@la4!DCNR%3&OUq1wEUrV4V1&)'
    '8zs5JPBaK=D1DyjK564f$vkG0=yy6)<@?FB@`Bt3WrBb?w>1ir^j}0I7%T}q0BM_x@0?5LzC0{dO^`(k9e&;At=rj%k@T8dN%eKN9xGi7'
    'Kpe@yAuCg5qDwJ~gS|eQLB~mLSkxcFL9epF=eOe6=X#~>O7W{%Nf%bjGmX`&nx(M3X>pxiO!8cu4|MW5AvdH%BY^8k)p>SR!r(VAiW)L#'
    'xw9>UTJ+EYi*9;~l3D`#(y5s>*V3h8%`t@$#^5c%TSCW?8xNB_$M5vO$XTZLVRp_gqq3`6K67m!hS=p^v3cJnU|@m18m+%{MODAPImwd6'
    'epV!YM#8kONbNEX1*MN4d&T$n@?PYe(5S<+{7M3}GMosA&iO|_3|1xI0o4PjNkEuQYh}Qagq9}~&2CNRX=3^Y<cr{>-_^%?kgF+gb|kkO'
    'jk3ilzd1^bK2f`ZlHR03r71bk0y4~v&x=%-<<mf<qd8l`xqbeJVxKT3p>&?z+&u1x8NA`L$FC${`Pq{!1F{l!H+Y+I{9aq>efgMEvp%L3'
    'r}E@?Qj<u@^ucP6P#Qo24MWjwvn%jrqtjPhvDGKz!KVf^o8BnqPI?kUc7tJl$Q4R)j_(j8`^*3AEVLG!U$G=-bfK=x_(7K-{bjD~wLZH)'
    '<Fu?u|7m^)krm;sox=L|hQ^0j)J_Z^pv2cChoW4a{Vo)?u_ry106672J3Ytb;GmMGP`x%3azQ+2W#eGb<vRwwbg6W<rGtj~OEEpf9ad7m'
    'p*Z-Pn<q;|cm5+s(zza{?*STOQ{N7O_l`G4Y(ra1Z|`mf5Wb)p)@<Be%FOoWyBeS$PxF`VD+Jf_4p`9RIsSZz?4VeGt*yjT?o-u`_WSMq'
    'V=k(3tep{_XK(Z_*usbEhd{V7+u4u^U)(xhkIr9jZ|7U3Mw&ZT^^{L(h+e>CYoRDI!{s^pO_4Zf#pI**MlwvafQZivkQ29UCH`iwn}I6@'
    '7_q>|WV!gqHlH;n+z5C1s0m^DVEf+escm5_@+vpbY}kZt46*>-oT(GPpiJ_NMi*FlW;mVX@-E^@7Y&r@b+R!g$d3c8;;+n4vJT`OqE=Ua'
    'Hh!Mw02U>cC9o`HdR9VOxIO_pP=OwLe^fP&P;9$@l2J2+AEdZxEQY6|1rt?&XP2G{51%1bbN5*S)r5t_4GGOslP0N;VzJ>+e;?Rm&Wi(M'
    'W5wx?f4LhPrNwszE8x#mz)My==i)w`sU~w#5DH85^XD`Y<~jDn+SX!%xlWg?lP9rOtmCg2qS;W;qyo1BA=*f{G@=4S*l6Px5^FaGC3^hU'
    'c7L$&H?$5qS}Wd+nnH>FI?SUvFD!DY@=<X5;Rbrp`fCF2n3JO$B@Z*Lyb!Yt)d?Q?%cw=pS~lE{q1#tE{m(6+=v?`Jw;|H`NDG6$k|^<!'
    '0Ml{Mr<LD%N*8$&HdTDnyyf0Y85H#iV2&I-WaE(4gWDE0Qe)Q=u+MRHzJ1;T#$XV?-7{r>m&Tl;fz6YQ?#tG4lVu3(K2s57a)6_rhuGX&'
    'H>F-4`C$%cO~nItA8vi@#GC;d`YqaN*Zc^)sdJ{<dKAedz9heXf`sTiV0kJlI!zhG5<FA@nPe~Qj9Q50E%@UJ>IP#`j$aS-^PI07mdkpY'
    'OO3_VG_zAnKIP(i5$+l>7v^`771y3RzhW~J?Uv)(qu}6UxiRw-S4Wj1a{`F0zp46S5RsLhs?LC5Ba4s;bJvLvQ@!NqNecvfm8uUJhHEE@'
    'TRNBtR$AC#pb6pEw{Ord>ErO@5)V3*9}Q4#@M#z*gp62tM@y7`o;tSXRn_&0SJC!p8h8PF2C=x|WlZZkx5UeU^W*kW3#4~hit1by(|(WC'
    'J(#t>mT7W`C~R-xLI9`>c)O&;G%l;X=BhemfNbOlgOt%Ms$NJQnM?oYGH7d(T(b4^<D!Sg>9r63+w)J*7u!FR+c>d^uHmd7m}kwc;Z!q='
    'WEVNzV?sg}jc&)Gt#(4I-23Hl$VN8~VF>AK-16z>r4oZ$R>E1j0|SnhK`iWg?t-qBh?tzc^e<;HWY{NKF0Qa;iJNC7O~HkTRuRg$Ii7uX'
    'Z!sH6SBdJ6gRR+7VOT+-hz$)N3eE}^^A&tjL5<D1lEf-3qW&A5iESN^^38<!dJz@6!bA^F$lk$4UK>u_9qGzRbWd?#gi6DZ(wC8maYaf{'
    'BZQXjEIHnfq6W<KnI9q9)$66xAW@G;7s;x3JLy28t4S2tQ*~>duDo0dZXY!}SvE8)LCE**xsy1iki8FFGXY@lUD)xL)lo|9X5G+kiMpfF'
    'ZsI`7FZr5n=#lyZ?MlgjuF>J$Z-S9^ev+%gk0|rAYC^Hl`4l^>25dk2OaDMsuJx0RFRp`pQf!HOl>|4P8<s!f=_5wH>PAp<R)jjQOq;AF'
    ';soQpzVq{>2d0noICs4BEm0u0qCnu|+?u~Xk}*N)FZP#Kpv*qLb+bp-71#_^!iTff<jHJ`IlYP*H$g&ndbYTlcyxhmyf<U={>hO7(>8R)'
    'o2Fj=1{Bh}OR2vXD4zJtHr^+6QOHB$dMQD(#C8`ElRea8s)bQguMm89qNEZfAQTbXOLIKezJ3mA&ooY_XV+w|w?<>i4a`r8X^TxG-1p^t'
    '5^DnNp^l^nnF)2Z90#FRHqNEtp(Wdsh6y~f_c3M$bCpRSB9R`#(pD1j2YN=RyCzZH3KpAk;BI*Ab(;mB0+2y9+QS|{y!en$tG2(<dr2L2'
    '-%oEt_b?VK`5Yr>FXRm6*SsA_PBgF|@b2%I;2!$dqH_I1wG#`vYp;joP}?w$-f}VxRdim?vfQI`Q!55>>tNAg3xMLVD#bqeB&BN?M>8UL'
    'Ttdr2ae|Ro6i4^frWUf(Y8&R>9=W`DhiL=b94Lnnxj6X*?K)zGXSK-yt9UFs`XsSe(gZm|hRTeXd<H-0iF$L4QU^RTKWY%P@k)sQrnB82'
    '$Z?Z&5Y$PR99hK^AHF)jO8w-Y{nd|K_5fa7;1k`m#Ec%|RhUmasbmO=4Yjz#+l|ZCOM+;_Vy)j6N9F9a(RDS4{l`qB2Ys_9y%2TQP-8Gh'
    'nO(W{<kOcx3;HU3{bVJ5Y8VGpPzaaTzY2YN`<t;hg?`kY)-MO$b<30Qy2MBOC!pJ(Ij*qSTPDk{(ERfd2;lQno?&vWVqOrA3~`GSK2%H)'
    'q#`;<-Tq~QP{W+QNp}xggg?v@&15)8rTEQF#*&)e)+kCq+l<*}!(wx~DGaOPkv@^MuG5!uYGd^m;w9T+aBSsJd?2k41lS#0%pq#pZMyqT'
    '9o2FHM|k{D?>(8Ys0*D~*cq<$!KC0liS0@Z_jxv)GN)<dB|7_i4B9+EL*t`xCqD+_mYmpy=~}fg_l5)HkG}a4Zr1*38Q>%4U{B%py)NLZ'
    '9h*}W!e&nCry@twK$T+ZUri>hrNDr0Ow^d=m4a$-WYk<h_@_4&(jyHL33BNZt&uy+mF*m_(^*%HEImEHk*t4p%H40c#+Qz*2~x3z-No(V'
    'XUnQLE!@dl5c>2Ru?EfbWAgtxw(?NBOn@9Kk{6blG>m<e)ncxMOd$hC*U02C5K@J8IW&``{8D~$7j;Y6`|>B(l*Q`sdrVqcY;n}|{6wzP'
    'uO#D%cqN!cA)E{H7Nfkhl#g!gv`m*9myb2;xdq?pJH^n1kH`cp85!PSVjWqD;La)x51WO_M#tVsd!pWaS8`YoNQ56_)by>7?#9zH|Kug|'
    'b4vF%3IzT^=cz>&xz-(Y+2Md$xNaMSuoFhtNc-7AP+{0^)kHTwpD+NbVbNEAV!#nEp64+#P-AlFs}|Ebftg!KF{Vl~6mc*RKBfDa2hmko'
    '4zB(F)7T$Jnpfp;TFI!Gs#e2W7vs1qI&ztQs=wPfaPV&t{?*4Zc9Mg)<^=%$4msdot1t-g&vuT5jk${}hl>^1&i4PSIsc?qKeqQj{Kfno'
    's(+*MdH+E{%w1h=J*@tlw%+YFizf&G{GET-7VZCAZOG?8YBi+t#=gP;z~A|Ijj`yzX<q+P`{xMge`%W=|9c?xKec~WqW+~(GQj=Mf|R-v'
    '67t`-k^kD$Z~#E1{$B^+{{Vg=h$;'
)

def make_icon_bytes():
    data=zlib.decompress(base64.b85decode(RENJI_ICON_ARCHIVE_B85))
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        paths=package.namelist()
        if len(paths)!=6 or not all(p.startswith("public/icons/") and p.endswith(".webp") for p in paths):
            raise RuntimeError("Bundled Renji icon manifest is invalid")
        return {path:package.read(path) for path in paths}


def execute(web: pathlib.Path, dry: bool):
    files={}
    for rel in FILES:
        path=web/rel
        if not path.is_file(): raise RuntimeError(f"Required source missing: {path}")
        files[rel]=path.read_text(encoding="utf-8")
    if any(MARK in content for content in files.values()):
        raise RuntimeError("Renji is already installed. Refusing double-install.")
    patch=Patcher(dict(files))
    add_roster(patch); add_kits(patch); add_fighter(patch)
    add_game(patch); add_model(patch); add_ai(patch); add_presentation(patch)
    icon_blobs = {rel:blob for rel,blob in make_icon_bytes().items() if not (web/rel).exists()}
    # Preflight happens entirely in RAM. Ensure all files actually changed.
    for rel in FILES:
        if patch.data[rel]==files[rel]: raise RuntimeError(f"No change to {rel}")
    print(f"{MARK}: preflight passed for {len(FILES)} source files, {len(icon_blobs)} new icons")
    print("Aster VRM placeholder; only Renji hair/eyes tinted gold; original Aster unchanged.")
    print("Read: one stack decays per 30s; X auto-parry: 15s; cooldown: 30s × (1 − 0.05 × Read).")
    print("Auto-parry interrupts current attack and visibly transitions through catch / cross / redirect.")
    if dry:
        print("DRY RUN — no files modified.")
        return
    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup=web/"scripts"/"backups"/f"renji_{stamp}"
    backup.mkdir(parents=True,exist_ok=False)
    stages=[]; written=[]
    try:
        for rel in FILES:
            dest=web/rel
            bak=backup/(rel.replace("/","__")+".txt")  # tsc doesn't compile our backups
            shutil.copy2(dest,bak)
            fd,temp=tempfile.mkstemp(prefix=".renji_stage_",suffix=".tmp",dir=dest.parent)
            with os.fdopen(fd,"w",encoding="utf-8",newline="") as out: out.write(patch.data[rel])
            stages.append((dest,pathlib.Path(temp),bak))
        # Stage new icons alongside source text. Do not overwrite existing custom icons.
        for rel,blob in icon_blobs.items():
            dest=web/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            fd,temp=tempfile.mkstemp(prefix=".renji_icon_",suffix=".tmp",dir=dest.parent)
            with os.fdopen(fd,"wb") as out: out.write(blob)
            stages.append((dest,pathlib.Path(temp),None))
        (backup/"manifest.json").write_text(json.dumps({"marker":MARK,"files":FILES,
            "new_icons":list(icon_blobs)},indent=2),encoding="utf-8")
        for dest,temp,bak in stages:
            if bak is None and dest.exists():
                raise RuntimeError(f"Icon appeared during installation; refusing overwrite: {dest}")
            os.replace(temp,dest)
            written.append((dest,bak))
    except Exception:
        for dest,bak in reversed(written):
            if bak is None: dest.unlink(missing_ok=True)
            else: shutil.copy2(bak,dest)
        raise
    finally:
        for _,temp,_ in stages:
            if temp.exists(): temp.unlink()
    print(f"Installed {MARK}. Backup: {backup}")
    print("Now run: npx tsc --noEmit -p .")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("web_dir",nargs="?",default=".",help="Fight Royale web root (default current folder)")
    parser.add_argument("--dry-run",action="store_true",help="Validate without writing files")
    args=parser.parse_args()
    try: execute(pathlib.Path(args.web_dir).resolve(),args.dry_run)
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        sys.exit(1)

if __name__=="__main__": main()
