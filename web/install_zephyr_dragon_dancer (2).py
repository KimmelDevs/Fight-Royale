#!/usr/bin/env python3
"""ZEPHYR DRAGON DANCER — full V18 installer, four weapon modes and weighted grip IK.

Grip map (rod:socket; dash means free hand). Mode-specific timelines below:
  Idle          R middle:mid        L -- (alternates briefly to L upper:near)
  l1 Entry      R middle:low        L --
  l2 Backwind   R --                L lower:near
  l3 Eight      R middle:mid        L --
  l4 Orbit      R middle:high      -> L upper:mid at mid-spin
  l5 Verdict    R middle:low        L lower:far
  Heavy         R middle:mid        L upper:near on the slam
  Z Serpent     R middle:mid       <-> L upper:near on each revolution
  X Reversal    R middle:mid        L -- (folded into Z)
  C Cyclone     R middle:mid       <-> L upper:mid (5 passes, brief releases)
  V Ninefold    R middle:mid       <-> L lower:near (9 passes)
  Showcase      R/L alternate; both free for flying toss, recatch at 6.24s.


From the web folder: python install_zephyr_dragon_dancer.py
Or pass your web directory as the first argument.

Targets V16, V17 or a compatible V16 project with Zephyr already installed.
The fully populated GRIP_TIMELINE[move][mode] is readable below.
Creates timestamped backups; validates anchors before writing; does not push Git changes
or run the optional SQL migration. Preserves all existing fighter snapshot fields.
"""
from __future__ import annotations

import datetime as datetime
import pathlib
import re
import shutil
import sys

MARK = 'ZEPHYR_DRAGON_DANCER_V1'
changes: dict[str, str] = {}

# V18 combat tuning. Set every value to 1.00 for visual-only modes.
DRAGON_MODE_TUNING = (
    dict(reach=1.00, wind=1.00, recover=1.00, guard=1.00, block=1.15, parry=1.15, counter=1.00),
    dict(reach=.88, wind=.85, recover=.88, guard=1.00, block=1.00, parry=1.00, counter=1.00),
    dict(reach=1.18, wind=1.08, recover=1.00, guard=1.00, block=.80, parry=.90, counter=1.00),
    dict(reach=.80, wind=.82, recover=.80, guard=1.00, block=1.00, parry=1.00, counter=1.25),
)


def patch(path: str, old: str, new: str, occurrences: int = 1):
    src = changes[path]
    hits = src.count(old)
    if hits != occurrences:
        raise RuntimeError(f'{path}: incompatible source: expected {occurrences} instance(s) of {old[:95]!r}, got {hits}. No files changed.')
    changes[path] = src.replace(old, new, occurrences)


def before(path: str, anchor: str, block: str):
    patch(path, anchor, block + anchor)


def add_kits():
    f = 'src/game/kits.ts'
    patch(f, '  glaive: { hp: 2250, guard: 88, move: 4.0, walk: 3.15, parry: 0.19, jump: 7.7 },',
          '  glaive: { hp: 2250, guard: 88, move: 4.0, walk: 3.15, parry: 0.19, jump: 7.7 },\n'
          '  // ZEPHYR_DRAGON_DANCER_V1\n  tristaff: { hp: 2225, guard: 82, move: 3.90, walk: 3.05, parry: 0.205, jump: 7.9 },')
    patch(f, '    glaive: glaive,', '    glaive: glaive,\n    tristaff: dragonStaff,')
    patch(f, '    glaive: [heavy.pose_w, heavy.pose_s],', '    glaive: [heavy.pose_w, heavy.pose_s],\n    tristaff: [heavy.pose_w, heavy.pose_s],')
    patch(f, '    glaive: "Thunderwheel",', '    glaive: "Thunderwheel",\n    tristaff: "Dragon\'s Answer",')
    patch(f, '    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40,',
          '    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40, tristaff: 2.25,')
    patch(f, '    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8,',
          '    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8, tristaff: 2.0,')
    patch(f, '    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8,',
          '    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8, tristaff: 4.3,')
    before(f, '    case "glaive":\n      return a({ name: "Arc Flash"', '''    // ZEPHYR_DRAGON_DANCER_V1 — nine distinct real melee contacts, not one unblockable animation.
    case "tristaff":
      return a({ name: "Ninefold Dragon", desc: "Nine independently timed three-section staff hits, alternating grips and an aerial finish. Each can be dodged, blocked, parried and clashed.",
        cd: 42, type: "melee", wind: 0.40, active: 1.90, recover: 0.75,
        dmg: 33, guard: 11, reach: 2.36, lunge: 1.8, knock: 0.65, stun: 0.13,
        style: "zephyr_ninefold", pose_w: "zdv_w", pose_s: "zdv_s" });
''')
    before(f, 'function sickle(): Record<string, Attack> {', '''/** ZEPHYR_DRAGON_DANCER_V1 — realistic folded, extended and spinning staff actions. */
function dragonStaff(): Record<string, Attack> {
  return {
    l1: a({ name: "Dragon Entry", wind: 0.13, active: 0.075, recover: 0.18,
      dmg: 48, guard: 14, reach: 2.09, lunge: 2.35, knock: 0.50, stun: 0.17,
      style: "zephyr_staff", pose_w: "zd1_w", pose_s: "zd1_s", next: "l2" }),
    l2: a({ name: "Backwind Catch", wind: 0.15, active: 0.08, recover: 0.19,
      dmg: 55, guard: 15, reach: 2.10, lunge: 2.0, knock: 0.58, stun: 0.18,
      style: "zephyr_staff", pose_w: "zd2_w", pose_s: "zd2_s", next: "l3" }),
    l3: a({ name: "Underarm Eight", wind: 0.15, active: 0.085, recover: 0.20,
      dmg: 61, guard: 17, reach: 2.16, lunge: 2.15, knock: 0.68, stun: 0.21,
      style: "zephyr_staff", pose_w: "zd3_w", pose_s: "zd3_s", next: "l4" }),
    l4: a({ name: "Orbit Wheel", wind: 0.19, active: 0.12, recover: 0.24,
      dmg: 71, guard: 20, reach: 2.26, lunge: 2.25, knock: 1.4, stun: 0.25,
      style: "zephyr_staff", pose_w: "zd4_w", pose_s: "zd4_s", next: "l5" }),
    l5: a({ name: "Twin-End Verdict", wind: 0.23, active: 0.10, recover: 0.43,
      dmg: 105, guard: 32, reach: 2.28, lunge: 2.15, knock: 4.0, stun: 0.40,
      style: "zephyr_finisher", pose_w: "zd5_w", pose_s: "zd5_s" }),
    heavy: a({ name: "Dragon Tail Break", wind: 0.29, active: 0.13, recover: 0.53,
      dmg: 166, guard: 52, reach: 2.52, lunge: 2.25, knock: 5.1, stun: 0.51, heavy: true,
      style: "zephyr_finisher", pose_w: "zdh_w", pose_s: "zdh_s" }),
    z: a({ name: "Serpent Wheel", desc: "Two overhead revolutions and a sweeping third strike; three independently defendable hits.",
      cd: 8, wind: 0.19, active: 0.59, recover: 0.41,
      dmg: 51, guard: 17, reach: 2.35, lunge: 2.6, knock: 0.75, stun: 0.17,
      style: "zephyr_serpent", pose_w: "zdz_w", pose_s: "zdz_s" }),
    x: a({ name: "Dragon Reversal", desc: "Fold the staff and brace for a 0.34s automatic counter. If hit by a parryable attack, neutralize it and counterattack. Failed reads leave recovery.",
      cd: 10, type: "buff", mode: "counter", duration: 0.34, wind: 0.04, active: 0.04, recover: 0.53,
      style: "zephyr_reversal", pose_w: "zdx_w", pose_s: "zdx_s" }),
    c: a({ name: "Heavenly Cyclone", desc: "Five transitioning staff grips: waist, shoulder, overhead, reverse and advancing finisher. Each contact remains blockable, parryable and clashable.",
      cd: 17, type: "melee", wind: 0.29, active: 1.18, recover: 0.57,
      dmg: 49, guard: 16, reach: 2.42, lunge: 1.8, knock: 0.7, stun: 0.16,
      style: "zephyr_cyclone", pose_w: "zdc_w", pose_s: "zdc_s" }),
  };
}

''')
    before(f, 'const CHAINBLADE: Record<string, Pose> = {', '''// ZEPHYR_DRAGON_DANCER_V1: stance -> cross-body -> figure-eight -> back catch -> pole vault finish.
const DRAGON_STAFF: Record<string, Pose> = {
  ...GLAIVE,
  idle: P([.07,-.27,.02],[-.05,.20,0],[-.87,.33,-.31],[.2,.04,-.13],[-1.03,-.20,.28],[.22,-.02,.10],[-.23,0,.20],[.28,0,-.17],-.10),
  block: P([.19,-.07,0],[-.02,.08,0],[-1.35,.22,-.24],[.38,0,-.12],[-1.43,-.27,.24],[.34,0,.12],[-.49,0,.17],[.47,0,-.15],-.17),
  charge: P([.21,-.44,.03],[.04,.28,0],[-1.29,.55,-.31],[.32,0,-.18],[-1.09,-.26,.37],[.22,0,.06],[-.44,0,.16],[.50,0,-.16],-.14),
  zd1_w: P([.13,-.60,.05],[0,.37,0],[-.95,-.64,-.20],[.3,0,-.24],[-1.04,-.45,.24],[.32,0,.06],[-.39,0,.18],[.37,0,-.13],-.12),
  zd1_s: P([.21,.49,-.04],[-.04,-.24,0],[-1.54,.38,-.27],[.12,0,.26],[-1.37,.30,.18],[.16,0,.1],[-.48,0,.14],[.39,0,-.15],-.13),
  zd2_w: P([.13,.55,.02],[-.05,-.28,0],[-1.18,.72,-.42],[.25,0,-.19],[-.91,.23,.32],[.20,0,.12],[-.24,0,.12],[.4,0,-.15],-.11),
  zd2_s: P([.19,-.60,-.03],[-.04,.38,0],[-1.62,-.62,-.24],[.16,0,.24],[-1.19,-.42,.28],[.19,0,-.07],[-.45,0,.14],[.43,0,-.1],-.14),
  zd3_w: P([.24,-.52,-.10],[-.06,.33,0],[-1.29,-.33,-.59],[.57,0,-.19],[-.89,-.28,.44],[.21,0,.04],[-.45,0,.17],[.37,0,-.12],-.17),
  zd3_s: P([.03,.62,.1],[-.02,-.28,0],[-2.00,.45,-.18],[.12,0,.39],[-1.40,.18,.31],[.12,0,.06],[-.50,0,.15],[.46,0,-.11],-.11),
  zd4_w: P([.12,-.92,0],[0,.40,0],[-1.10,-.71,-.36],[.56,0,-.19],[-1.04,-.63,.40],[.26,0,-.12],[-.51,0,.13],[.43,0,-.12],-.15),
  zd4_s: P([.08,1.02,.02],[0,-.55,0],[-1.93,.83,-.23],[.17,0,.44],[-1.57,.66,.29],[.10,0,.31],[-.62,0,.15],[.47,0,-.14],-.13),
  zd5_w: P([-.22,-.39,.04],[.13,.17,0],[-2.57,-.2,-.23],[.42,0,-.04],[-2.19,-.09,.17],[.3,0,.06],[-.73,0,.10],[.27,0,-.10],-.10),
  zd5_s: P([.43,.36,0],[-.23,-.11,0],[-.72,.37,-.37],[.13,0,.18],[-.92,.24,.24],[.13,0,.06],[-.77,0,.14],[.65,0,-.16],-.23),
  zdh_w: P([-.17,-.47,.02],[.13,.24,0],[-2.20,-.36,-.29],[.4,0,-.13],[-1.86,-.24,.23],[.34,0,.08],[-.65,0,.14],[.41,0,-.15],-.17),
  zdh_s: P([.45,.44,.05],[-.21,-.19,0],[-.79,.44,-.43],[.15,0,.28],[-1.14,.34,.31],[.16,0,.12],[-.80,0,.15],[.59,0,-.15],-.21),
  zdz_w: P([.07,-.56,0],[0,.37,0],[-1.67,-.38,-.22],[.50,0,-.26],[-1.57,-.22,.37],[.38,0,.07],[-.46,0,.14],[.44,0,-.13],-.12),
  zdz_s: P([.10,.69,0],[-.1,-.29,0],[-1.87,.72,-.25],[.2,0,.35],[-1.62,.44,.29],[.22,0,.17],[-.51,0,.14],[.45,0,-.16],-.14),
  zdx_w: P([.29,-.16,0],[-.06,.08,0],[-1.40,.35,-.35],[.34,0,-.22],[-1.47,-.36,.34],[.31,0,.15],[-.69,0,.14],[.61,0,-.16],-.20),
  zdx_s: P([.09,.27,0],[-.11,-.03,0],[-1.34,-.48,-.25],[.27,0,.09],[-1.59,.37,.38],[.2,0,.1],[-.49,0,.13],[.55,0,-.18],-.17),
  zdc_w: P([.1,-.75,0],[0,.25,0],[-1.49,-.55,-.38],[.40,0,-.16],[-1.33,-.47,.43],[.24,0,.12],[-.45,0,.16],[.43,0,-.15],-.13),
  zdc_s: P([.12,.72,0],[-.08,-.26,0],[-1.67,.61,-.36],[.25,0,.40],[-1.59,.38,.31],[.17,0,.14],[-.61,0,.14],[.52,0,-.15],-.15),
  zdv_w: P([-.12,-.48,0],[.07,.18,0],[-2.37,-.3,-.31],[.36,0,-.13],[-2.11,-.14,.28],[.24,0,.13],[-.56,0,.14],[.45,0,-.15],-.14),
  zdv_s: P([.20,.53,0],[-.14,-.16,0],[-1.95,.53,-.32],[.29,0,.30],[-1.71,.46,.28],[.19,0,.20],[-.67,0,.15],[.59,0,-.16],-.18),
  zdv_finish: P([.52,.30,0],[-.19,-.08,0],[-.55,.47,-.25],[.11,0,.16],[-.84,.31,.28],[.10,0,.10],[-.83,0,.13],[.59,0,-.13],-.22),
};

''')
    patch(f, '  glaive: GLAIVE,', '  glaive: GLAIVE,\n  tristaff: DRAGON_STAFF,')


def add_roster():
    f='src/game/roster.ts'
    before(f, '\n];\n\nexport function resolveEnemy', '''  // ZEPHYR_DRAGON_DANCER_V1 — Garrick VRM temporary; replace with your own zephyr.vrm later.
  { id: "zephyr", title: "Dragon Dancer", role: "Martial Artist - Three-Section Staff",
    desc: "Technical staff master. Master five flowing grips, counter with Dragon Reversal and earn Rhythm through real catches, parries and clashes.",
    stats: { power: 4, speed: 4, range: 3, defense: 3 },
    look: { name: "Zephyr", body: "m", vrm: "garrick", kit: "tristaff", element: "dragon", outfit: "martial", style: "short", hat: "none",
      hair: "#263f45", hair_shade: "#76939a", iris_top: "#1e8c7e", iris_bottom: "#b6ffe2", eye_dark: "#113034",
      tunic: "#203a43", band: "#85bba5", pants: "#19242e", boots: "#202936", metal: "#e0e8df", trim: "#d5be82",
      cape: "#274a53", cape_bottom: "#84c7ae", glow: "#78eed0", shield: "#243e48", emblem: "#e8d9a0" } },
''')


def add_fighter():
    f='src/game/fighter.ts'
    patch(f,'  onSwing: (f: Fighter) => void = () => {};', '''  // ZEPHYR_DRAGON_DANCER_V1 — stacks earned only on confirmed hits, parries, and clashes.
  dragonRhythm = 0;
  dragonRhythmT = 0;
  private dragonRhythmSerial = -1;
  earnDragonRhythm(serial = -1) {
    if (this.kit !== "tristaff" || this.isDown()) return;
    // One stack per light attack even if it hits multiple fighters or mobs.
    if (serial >= 0 && this.dragonRhythmSerial === serial) return;
    if (serial >= 0) this.dragonRhythmSerial = serial;
    this.dragonRhythm = Math.min(3, this.dragonRhythm + 1);
    this.dragonRhythmT = 7;
  }
  onSwing: (f: Fighter) => void = () => {};''')
    patch(f, '    this.parryCounterT = Math.max(0, this.parryCounterT - dt);', '''    // ZEPHYR_DRAGON_DANCER_V1
    this.dragonRhythmT = Math.max(0, this.dragonRhythmT - dt);
    if (this.dragonRhythmT <= 0) this.dragonRhythm = 0;
    this.parryCounterT = Math.max(0, this.parryCounterT - dt);''')
    before(f, '    if (this.kit === "hammer" && this.atk?.style === "nesa_high_striker")', '''    // ZEPHYR_DRAGON_DANCER_V1: spend earned rhythm on next committed finisher.
    if (this.kit === "tristaff" && this.atk && this.dragonRhythm >= 3 &&
        ["l5", "heavy", "c", "v", "pc"].includes(id)) {
      this.atk = { ...this.atk, dmg: this.atk.dmg * 1.18, guard: this.atk.guard * 1.17 };
      this.dragonRhythm = 0;
      this.dragonRhythmT = 0;
      this.model.flash("#9fffe1", 0.28);
    }
''')
    pose_anchor = '    this.model.glaivePose = this.kit === "glaive" ? (this.state === S.WIN ? "show_baton" : this.poseName) : "idle";'
    if pose_anchor not in changes[f]:
        pose_anchor = '    this.model.glaivePose = this.kit === "scythe" ? this.poseName : this.kit === "glaive" ? (this.state === S.WIN ? "show_baton" : this.poseName) : "idle";'
    patch(f, pose_anchor, '''    this.model.dragonPose = this.kit === "tristaff" ? (this.state === S.WIN ? "show_tristaff" : this.poseName) : "idle";
    this.model.dragonProgress = this.state === S.ATTACK && this.atk ?
      Math.max(0, Math.min(1, this.stateT / Math.max(0.01, this.atk.wind + this.atk.active))) : 0;
'''+pose_anchor, 2)
    # V16 / Passive Roster V10 snapshots use slots 0..82 already. Append only,
    # leaving Zenith, Nythera, and every other passive's network indices intact.
    patch(f,
          '      this.passiveEmberPatches]; // PASSIVE_ROSTER_V10: optional appended snapshot fields',
          '      this.passiveEmberPatches, this.dragonRhythm, +this.dragonRhythmT.toFixed(2)]; // PASSIVE_ROSTER_V10: optional appended snapshot fields')
    patch(f,
          '    this.passiveEmberPatches = s[82] ?? 0;',
          '    this.passiveEmberPatches = s[82] ?? 0;\n'
          '    this.dragonRhythm = s.length > 83 ? s[83] : 0;\n'
          '    this.dragonRhythmT = s.length > 84 ? s[84] : 0;')


def add_game():
    f='src/game/game.ts'
    before(f, '    const a = f.atk!;\n    this.swingSound(f, a);', '''    // ZEPHYR_DRAGON_DANCER_V1: each swing has a real combat hitbox.
''')
    patch(f, '    this.swingSound(f, a);', '''    this.swingSound(f, a);
    if (f.kit === "tristaff") {
      const p = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", p, "#76eed1");
      this.fxp("sparks", p, "#b9ffe8", 12, 4.1);
      if (["zephyr_serpent", "zephyr_cyclone", "zephyr_ninefold"].includes(a.style)) {
        this.zephyrComboSwing(f, a); return;
      }
      if (a.type === "melee") { this.melee(f, a); return; }
    }
''')
    before(f, '  private melee(f: Fighter, a: Attack): boolean {', '''  // ZEPHYR_DRAGON_DANCER_V1 — single contact for each weapon pass, with a serial-bound
  // timer to stop post-interrupt phantom damage. Normal melee() resolves parries and blocks.
  private zephyrComboSwing(f: Fighter, a: Attack) {
    const count = a.style === "zephyr_serpent" ? 3 : a.style === "zephyr_cyclone" ? 5 : 9;
    const tick = a.active / count;
    const round = this.round, serial = f.swingSerial;
    for (let i = 0; i < count; i++) this.laterCombo(f, i * tick, () => {
      if (round !== this.round || f.isDown() || f.swingSerial !== serial ||
          f.state !== S.ATTACK || f.atk?.style !== a.style) return;
      const last = i === count - 1;
      const hit: Attack = { ...a, id: `${a.id}_${i+1}`,
        dmg: last ? a.dmg * 1.75 : a.dmg * (i % 2 === 0 ? 0.80 : 0.94),
        guard: last ? a.guard * 1.7 : a.guard,
        knock: last ? 4.2 : 0.6, stun: last ? 0.39 : 0.12,
        heavy: false, reach: a.reach + (last ? 0.12 : 0),
      };
      f.model.dragonProgress = (i + 1) / count;
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", tip, i % 2 ? "#aafbe8" : "#5ed9bd");
      this.fxp("sparks", tip, "#dcffec", last ? 25 : 10, last ? 6 : 3);
      if (last) this.fxp("ring", tip, "#8cf2d3", 0.9, 0.19, 0.72);
      this.melee(f, hit);
    });
  }

''')
    result_anchor = next((line for line in changes[f].splitlines()
                          if 'const result = d.receiveHit(attacker, balancedAttack,' in line), None)
    if result_anchor is None: raise RuntimeError('game.ts missing hit resolution anchor')
    patch(f, result_anchor, result_anchor + '''
    // ZEPHYR_DRAGON_DANCER_V1: count actual impacts, not misses / block spam.
    if (attacker instanceof Fighter && attacker.kit === "tristaff" &&
        ["hit", "crit", "ko"].includes(result) &&
        (attacker.atkId === "l2" || attacker.atkId === "l3" || attacker.atkId === "l5" || attacker.atkId === "pc")) {
      attacker.earnDragonRhythm(attacker.swingSerial);
      this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.87, 0)),
        `RHYTHM ${attacker.dragonRhythm}/3`, "#b7ffe3", 0.61);
    }''')
    patch(f, '      case "parry": {\n        const df = d as Fighter;', '''      case "parry": {
        const df = d as Fighter;
        if (df.kit === "tristaff") {
          df.earnDragonRhythm();
          this.fxp("num", df.chest().add(new THREE.Vector3(0, 0.82, 0)),
            `DRAGON RHYTHM ${df.dragonRhythm}/3`, "#98f3d5", 0.7);
        }''')
    patch(f, '      case "counter": {\n        const df = d as Fighter;', '''      case "counter": {
        const df = d as Fighter;
        if (df.kit === "tristaff") {
          df.earnDragonRhythm();
          this.fxp("ring", df.chest(), "#76eed1", 0.74, 0.18, 0.71);
          this.fxp("num", df.chest().add(new THREE.Vector3(0, .85, 0)),
            `DRAGON COUNTER ${df.dragonRhythm}/3`, "#c7ffeb", .8);
        }''')
    patch(f, '      this.awardZarekClash(fighter);\n      if (fighter.kit === "hammer"',
          '      this.awardZarekClash(fighter);\n      if (fighter.kit === "tristaff") fighter.earnDragonRhythm();\n      if (fighter.kit === "hammer"')
    patch(f, '      if (f.kit === "hammer") passives.push({ label: "HEARTS",', '''      if (f.kit === "tristaff") passives.push({ label: "RHYTHM", value: `${f.dragonRhythm}/3 · ${f.dragonRhythmT.toFixed(1)}s` });
      if (f.kit === "hammer") passives.push({ label: "HEARTS",''')
    patch(f, 'chainBindKind: f.chainBindKind,', 'chainBindKind: f.chainBindKind, dragonRhythm: f.dragonRhythm, dragonRhythmT: f.dragonRhythmT,')


def add_ai():
    f='src/game/ai.ts'
    patch(f, '  zarek: { range: 2.10, heavy: 0.30, combo: 0.91, bait: 0.35, pressure: 0.86, skillBias: [1.3, 1.2, 1.45] },',
          '  zarek: { range: 2.10, heavy: 0.30, combo: 0.91, bait: 0.35, pressure: 0.86, skillBias: [1.3, 1.2, 1.45] },\n'
          '  // ZEPHYR_DRAGON_DANCER_V1: aggressive counter-based three-section staff duelist.\n'
          '  zephyr: { range: 2.15, heavy: 0.20, combo: 0.96, bait: 0.58, pressure: 0.78, skillBias: [1.35, 1.75, 1.1] },')


def add_model():
    f='src/game/model.ts'
    patch(f, '  private glaivePivot: THREE.Group | null = null;', '''  private glaivePivot: THREE.Group | null = null;
  // ZEPHYR_DRAGON_DANCER_V1: actual connected sections, each on an animated joint.
  private dragonRoot: THREE.Group | null = null;
  private dragonUpper: THREE.Group | null = null;
  private dragonLower: THREE.Group | null = null;
  private dragonGhost: THREE.Group | null = null;
  private dragonGhostUpper: THREE.Group | null = null;
  private dragonGhostLower: THREE.Group | null = null;
  private dragonThrowStart = new THREE.Vector3();
  private dragonThrowQuat = new THREE.Quaternion();
  private dragonThrowScale = new THREE.Vector3(1, 1, 1);
  private dragonWasTossed = false;
  private dragonUpperV = 0;
  private dragonLowerV = 0;
  dragonPose = "idle";
  dragonProgress = 0;''')
    patch(f, '      case "glaive": this.buildGlaive(); break;', '      case "glaive": this.buildGlaive(); break;\n      case "tristaff": this.buildDragonStaff(); break;')
    before(f, '  /** ZAREK_STORM_V1: double-ended conductive glaive; meshes follow the VRM\'s hands. */', '''  /** ZEPHYR_DRAGON_DANCER_V1: three rigid rods and two visible moving connectors.
   * Segment pivots are animated with spring-damped angular velocity, never stretched.
   * Clones are presentation-only; all combat collisions still come from melee(). */
  private buildDragonStaff() {
    const root = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    root.name = "zephyrMiddleGrip";
    this.dragonRoot = root;
    const dark = this.tn("#253e44"), silver = this.steel(), gold = this.tn("#d1b782");
    const wrap = this.tn("#508477");
    mesh(root, cyl(0.025, 0.026, 0.71, 10), dark);
    for (const y of [-0.25, 0, 0.25]) mesh(root, cyl(0.032, 0.032, 0.08, 10), wrap, [0,y,0]);
    for (const y of [-.355,.355]) {
      mesh(root, sphere(.043, 12), gold, [0,y,0]);
      mesh(root, torus(.032,.045), silver, [0,y,0], [PI/2,0,0]);
    }
    const upper = pivot(root, [0, .357, 0]);
    const lower = pivot(root, [0, -.357, 0]);
    upper.name = "zephyrUpperLink"; lower.name = "zephyrLowerLink";
    this.dragonUpper = upper; this.dragonLower = lower;
    mesh(upper, cyl(.023,.026,.68,10), dark, [0,.34,0]);
    mesh(lower, cyl(.026,.023,.68,10), dark, [0,-.34,0]);
    for (const [node, sign] of [[upper,1],[lower,-1]] as const) {
      mesh(node, cyl(.041,.029,.145,12), silver, [0,sign*.67,0]);
      mesh(node, cyl(.048,.045,.045,10), gold, [0,sign*.74,0]);
      for (const y of [.24,.5]) mesh(node, torus(.027,.037), gold, [0,sign*y,0], [PI/2,0,0]);
    }
    // IK follows the middle handle. It releases during selection toss only.
    this.gripL = pivot(root, [0,-.20,0]);
    this.bladeBase = pivot(root, [0,.35,0]);
    this.bladeTip = pivot(upper, [0,.75,0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = root;
    // Duplicated display-only staff, hidden outside an actual selection toss.
    this.dragonGhost = root.clone(true);
    this.dragonGhost.name = "zephyrTossedDisplayOnly";
    this.dragonGhostUpper = this.dragonGhost.getObjectByName("zephyrUpperLink") as THREE.Group;
    this.dragonGhostLower = this.dragonGhost.getObjectByName("zephyrLowerLink") as THREE.Group;
    this.dragonGhost.visible = false;
    this.add(this.dragonGhost);
  }

  private updateDragonStaff(dt: number) {
    if (!this.dragonRoot || !this.dragonUpper || !this.dragonLower) return;
    const show = this.dragonPose === "show_tristaff";
    const phase = show ? ((this.presentationT % 9) + 9) % 9 : 0;
    // Real three-joint choreography: low arm pass, overhead, figure-eight, catch.
    const base: Record<string, [number,number,number]> = {
      idle:[PI/2,-.16,.10], block:[1.53,.08,.21],
      zd1_w:[1.45,-.6,-.32], zd1_s:[1.12,.48,.24],
      zd2_w:[1.87,.5,.33], zd2_s:[1.23,-.56,-.39],
      zd3_w:[1.33,-.47,-.36], zd3_s:[1.71,.51,.38],
      zd4_w:[1.80,-.67,.44], zd4_s:[1.10,.70,-.47],
      zd5_w:[2.28,-.27,.17], zd5_s:[.68,.29,-.12],
      zdh_w:[2.11,-.29,.14], zdh_s:[.82,.35,-.20],
      zdz_w:[1.93,-.4,.15], zdz_s:[1.33,.38,-.21],
      zdx_w:[1.54,-.11,.15], zdx_s:[1.26,.22,-.19],
      zdc_w:[1.75,-.52,.22], zdc_s:[1.32,.59,-.34],
      zdv_w:[2.03,-.31,.08], zdv_s:[1.16,.53,-.28],
      zdv_finish:[.7,.28,-.19],
    };
    const a=base[this.dragonPose] ?? base.idle;
    const rot=new THREE.Euler(a[0],a[1],a[2],"YXZ");
    const q=new THREE.Quaternion().setFromEuler(rot);
    const spinMove=/^zd[1-5]_s$/.test(this.dragonPose) ||
      ["zdz_s","zdc_s","zdv_s"].includes(this.dragonPose);
    if (spinMove) {
      const cycles=this.dragonPose==="zdc_s" ? 2 : this.dragonPose==="zdv_s" ? 3 : 1;
      const sweep=this.dragonProgress * PI*2*cycles;
      // Alternating shoulder paths create full figure-eights, not a rigid spin-in-place.
      q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),sweep));
      q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),Math.sin(sweep)*.28));
    }
    if (show) {
      const turn=phase<3 ? THREE.MathUtils.smoothstep(phase,.55,3)*PI*8 :
        phase<4.45 ? PI*8+THREE.MathUtils.smoothstep(phase,3,4.45)*PI*4 :
        phase<6.6 ? PI*12 : PI*12+THREE.MathUtils.smoothstep(phase,6.6,7.65)*PI*4;
      q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),turn));
      q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),Math.sin(turn*.5)*.30));
    }
    this.dragonRoot.quaternion.slerp(q,1-Math.exp(-27*dt));
    // Flexible connectors: damped second-order angular motion, independent for both rods.
    const swing=show ? Math.sin(phase*8.4)*.8 : spinMove ? Math.sin(this.dragonProgress*PI*4)*.52 :
      this.dragonPose.endsWith("_w") ? -.34 : this.dragonPose.endsWith("_s") ? .39 : .12;
    const targetUp = swing*.85;
    const targetLo = -swing*.72;
    this.dragonUpperV += (targetUp-this.dragonUpper.rotation.z)*dt*125;
    this.dragonLowerV += (targetLo-this.dragonLower.rotation.z)*dt*115;
    this.dragonUpperV *= Math.exp(-13*dt);
    this.dragonLowerV *= Math.exp(-13*dt);
    this.dragonUpper.rotation.z += this.dragonUpperV*dt;
    this.dragonLower.rotation.z += this.dragonLowerV*dt;
    this.dragonUpper.rotation.z = THREE.MathUtils.clamp(this.dragonUpper.rotation.z,-1.32,1.32);
    this.dragonLower.rotation.z = THREE.MathUtils.clamp(this.dragonLower.rotation.z,-1.32,1.32);
    this.dragonUpper.rotation.x = show ? Math.sin(phase*9)*.17 : .07*Math.sin(this.t*9);
    this.dragonLower.rotation.x = show ? -.15*Math.sin(phase*9+.4) : -.06*Math.sin(this.t*8);
    // A genuine presentation toss: hide hand-held mesh, show a detached copy in the air.
    // This is cosmetic and cannot hit anyone or alter fighter networking.
    const toss=show && phase>=4.52 && phase<6.24;
    if (toss && this.dragonGhost) {
      if (!this.dragonWasTossed) {
        this.updateMatrixWorld(true);
        this.dragonThrowStart.copy(this.worldToLocal(this.dragonRoot.getWorldPosition(new THREE.Vector3())));
        const wq=this.dragonRoot.getWorldQuaternion(new THREE.Quaternion());
        this.dragonThrowQuat.copy(this.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(wq));
        const ws=this.dragonRoot.getWorldScale(new THREE.Vector3());
        const ms=this.getWorldScale(new THREE.Vector3());
        this.dragonThrowScale.set(ws.x/ms.x,ws.y/ms.y,ws.z/ms.z);
        this.dragonWasTossed=true;
      }
      const u=(phase-4.52)/(6.24-4.52);
      this.dragonRoot.visible=false;
      this.dragonGhost.visible=true;
      this.dragonGhost.position.copy(this.dragonThrowStart).add(new THREE.Vector3(Math.sin(u*PI)*.15,Math.sin(u*PI)*.93,-.08*Math.sin(u*PI)));
      this.dragonGhost.quaternion.copy(this.dragonThrowQuat).multiply(
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),u*PI*6));
      this.dragonGhost.scale.copy(this.dragonThrowScale);
      if (this.dragonGhostUpper) this.dragonGhostUpper.rotation.copy(this.dragonUpper.rotation);
      if (this.dragonGhostLower) this.dragonGhostLower.rotation.copy(this.dragonLower.rotation);
    } else {
      this.dragonRoot.visible=true;
      if (this.dragonGhost) this.dragonGhost.visible=false;
      this.dragonWasTossed=false;
    }
    if (this.vrmRig && this.gripL) {
      this.vrmRig.gripL = show && phase>=4.1 && phase<6.33 ? null : this.gripL;
    }
  }

''')
    if '    if (this.gripL) this.reachGrip();\n    this.vrmRig?.update(dt' in changes[f]:
        patch(f, '    if (this.gripL) this.reachGrip();\n    this.vrmRig?.update(dt', '''    if (this.kit === "tristaff") this.updateDragonStaff(dt);
    if (this.gripL && !(this.kit === "tristaff" && this.dragonPose === "show_tristaff" &&
        this.presentationT % 9 > 4.1 && this.presentationT % 9 < 6.33)) this.reachGrip();
    this.vrmRig?.update(dt''')
    else:
        patch(f, '    if (this.vrmRig && this.kit === "scythe") this.vrmRig.gripL = noScytheGrip ? null : this.gripL;',
              '    if (this.kit === "tristaff") this.updateDragonStaff(dt);\n'
              '    if (this.vrmRig && this.kit === "scythe") this.vrmRig.gripL = noScytheGrip ? null : this.gripL;')
        patch(f, '    } else if (this.gripL && !noScytheGrip) this.reachGrip();',
              '    } else if (this.gripL && !noScytheGrip && !(this.kit === "tristaff" && this.dragonPose === "show_tristaff" &&\n'
              '        this.presentationT % 9 > 4.1 && this.presentationT % 9 < 6.33)) this.reachGrip();')
    patch(f, 'this.kit === "sickle" ? 0.18', 'this.kit === "tristaff" ? 0.20 : this.kit === "sickle" ? 0.18')
    patch(f, 'this.kit === "sickle" ? "feral"', 'this.kit === "tristaff" ? "storm" : this.kit === "sickle" ? "feral"')
    patch(f, 'this.kit === "glaive" ? 0.4 :', 'this.kit === "glaive" ? 0.4 : this.kit === "tristaff" ? 0.36 :')
    patch(f, ': VRM_WEAPON_SCALE; // ZAREK_PROPORTIONATE_GLAIVE_V1', ': this.kit === "tristaff" ? 0.79 : VRM_WEAPON_SCALE; // ZAREK_PROPORTIONATE_GLAIVE_V1')


def add_preview():
    f='src/game/preview.ts'
    if 'this.poseT % 6.2;' in changes[f]:
        patch(f, 'const phase = this.mode === "victory" ? this.poseT : this.poseT % 6.2;',
              'const phase = this.mode === "victory" ? this.poseT : this.poseT % (this.lookName.toLowerCase() === "zephyr" ? 9 : 6.2);')
    else:
        patch(f, 'this.poseT % (who === "nythera" ? 10.2 : 6.2);',
              'this.poseT % (who === "nythera" ? 10.2 : who === "zephyr" ? 9 : 6.2);')
    if 'this.model.glaivePose = who === "nythera"' in changes[f]:
        patch(f, 'this.model.glaivePose = who === "nythera" ? "nythera_show" : who === "zarek" ? "show_baton" : "idle";',
              'this.model.glaivePose = who === "nythera" ? "nythera_show" : who === "zarek" ? "show_baton" : "idle";\n'
              '      this.model.dragonPose = who === "zephyr" ? "show_tristaff" : "idle";')
        patch(f, 'who === "nythera" ? 20 : 11);', 'who === "nythera" ? 20 : who === "zephyr" ? 19 : 11);')
    else:
        patch(f, '      this.model.glaivePose = who === "zarek" ? "show_baton" : "idle";',
              '      this.model.glaivePose = who === "zarek" ? "show_baton" : "idle";\n'
              '      this.model.dragonPose = who === "zephyr" ? "show_tristaff" : "idle";')
        patch(f, '      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt, 11);',
              '      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt,\n'
              '        who === "zephyr" ? 19 : 11);')
    f='src/game/presentation.ts'
    before(f, '/** Entirely cosmetic; all poses use the same normalized VRM/procedural joints as combat. */', '''// ZEPHYR_DRAGON_DANCER_V1 — nine-second showcase in readable beats.
function zephyrPresentation(seconds: number, base: Pose, mode: "select" | "victory"): Pose {
  const t = mode === "select" ? ((seconds%9)+9)%9 : Math.min(seconds, 7.9);
  const beats: Array<[number, Beat]> = [
    [0, { torso:[.1,-.29,0],head:[-.08,.18,0],arm_r:[-.88,.32,-.31],arm_l:[-1.05,-.2,.31],hips_y:-.10 }],
    [.6, { torso:[.13,-.46,.04],arm_r:[-1.28,.28,-.32],arm_l:[-1.15,-.32,.3],hips_y:-.13 }],
    [1.6, { torso:[.05,.64,.08],arm_r:[-1.7,.5,-.38],arm_l:[-1.4,.18,.39],hips_y:-.10 }],
    [2.5, { torso:[.09,-.69,-.08],arm_r:[-1.78,-.33,-.44],arm_l:[-1.11,-.39,.5],hips_y:-.13 }],
    [3.4, { torso:[-.1,.34,.10],arm_r:[-2.48,.23,-.24],arm_l:[-1.68,-.12,.39],hips_y:-.04 }],
    [4.4, { torso:[-.19,-.25,0],arm_r:[-2.67,.12,-.16],arm_l:[-.68,-.36,.49],hips_y:-.07 }],
    [4.55, { torso:[-.11,-.31,0],arm_r:[-2.46,.18,-.20],arm_l:[-.55,-.23,.45],hips_y:-.06 }],
    [5.30, { torso:[.13,.48,.05],arm_r:[-.75,.46,-.32],arm_l:[-1.18,-.22,.31],leg_l:[-.58,0,.10],leg_r:[-.98,0,-.14],hips_y:.06 }],
    [6.20, { torso:[-.03,.31,-.04],arm_r:[-2.50,.24,-.19],arm_l:[-1.34,-.31,.39],hips_y:-.09 }],
    [6.60, { torso:[.08,-.38,0],arm_r:[-1.41,.32,-.28],arm_l:[-1.29,-.3,.28],hips_y:-.10 }],
    [7.6, { torso:[.35,.14,0],arm_r:[-.82,.18,-.48],arm_l:[-1.48,-.15,.35],leg_l:[-.53,0,.16],leg_r:[.47,0,-.14],hips_y:-.20,knee:[.47,.40] }],
    [8.38, { torso:[.08,-.25,0],arm_r:[-.86,.29,-.33],arm_l:[-.97,-.25,.31],hips_y:-.1 }],
    [9, { torso:[.1,-.29,0],arm_r:[-.88,.32,-.31],arm_l:[-1.05,-.2,.31],hips_y:-.10 }],
  ];
  let i=0; while(i<beats.length-2 && t>beats[i+1][0]) i++;
  const lo=beats[i],hi=beats[i+1];
  const u=Math.max(0,Math.min(1,(t-lo[0])/Math.max(.001,hi[0]-lo[0])));
  return between(filled(base,lo[1]),filled(base,hi[1]),u);
}

''')
    patch(f, '  const entry = C[name.toLowerCase()];',
          '  if (name.toLowerCase() === "zephyr") return zephyrPresentation(seconds,base,mode);\n  const entry = C[name.toLowerCase()];')


def add_hud():
    f='src/ui/GameView.tsx'
    before(f, '              {/* ZAREK_WHITE_COUNTER_V1 */}', '''              {me.id === "zephyr" && (
                <div style={{ marginTop: 6, padding: "5px 8px", background: "rgba(4,20,22,.9)",
                  border: "1px solid #69dfc5", borderRadius: 7, color: "#fff", fontSize: 12,
                  fontWeight: 800, textShadow: "0 1px 2px #000" }}>
                  <Icon src="/icons/skills/tristaff-passive.webp" alt="Dragon Rhythm" size={22} fallback={<span>◎</span>} />
                  {` DRAGON RHYTHM ${(me as any).dragonRhythm ?? 0}/3`}
                </div>
              )}
''')


def make_sql(base: pathlib.Path, backup: pathlib.Path):
    # Append-only: preserve all existing allowlisted fighters, including newer patches.
    f=base/'supabase/migrations/20261108220000_add_zephyr_dragon_dancer.sql'
    if f.exists():
        raise RuntimeError(f'{f} already exists; refusing to overwrite')
    f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text('''-- Zephyr / Dragon Dancer. Extends the installed allowlist without deleting its other IDs.
-- Review and apply this migration using your existing Supabase workflow.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina','volta','sylva',
    'nyx','rook','gale','bob','kira','raven','ash','veyr','zarek','kaizen',
    'nesa','roxy','zenith','nythera','zephyr','leon','sakura','yuki','bruno'
  ]);
$$;

-- Include Zephyr in the admin roster. Ownership of other fighters stays unchanged.
CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
  SELECT ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash','veyr','zarek','kaizen',
    'nesa','roxy','zenith','nythera','zephyr'
  ]::text[]
$$;
''',encoding='utf-8')
    print('  +',f.relative_to(base),'(review/apply separately)')


# -----------------------------------------------------------------------------
# SANJIEKUN_VISUAL_V17 — complete visual upgrade, safe on existing V16 or fresh.
# No modifications to the Zephyr hit resolver, snapshots, AI, cooldowns, or SQL.
# -----------------------------------------------------------------------------
VISUAL_MARK = 'SANJIEKUN_VISUAL_V17'
MODEL_VISUAL = '  /** ZEPHYR_DRAGON_DANCER_V1 · SANJIEKUN_VISUAL_V17.\n   * Actual separate metal-capped rods and two articulated four-link chains.\n   * Every part is cosmetic. Hit detection / ranges / rhythms remain in game.ts.\n   */\n  private buildDragonStaff() {\n    const root = pivot(this.hand_r);\n    root.name = "zephyrMiddleGrip";\n    this.dragonRoot = root;\n    const lacquer = this.tn("#251b20");\n    const red = this.tn("#ad2032");\n    const black = this.tn("#111016");\n    const ferrule = this.steel();\n    const darkMetal = this.tn("#4d4a55");\n    const makeSocket = (rod: THREE.Group, name: string, y: number) => {\n      const s = pivot(rod, [0, y, 0]);\n      s.name = `zephyrSocket_${name.replace(":", "_")}`;\n      this.dragonSockets[name] = s;\n      return s;\n    };\n    const makeRod = (parent: THREE.Object3D, name: "upper" | "middle" | "lower", sign: number) => {\n      const r = name === "middle" ? .325 : .335;\n      const rod = name === "middle" ? root : pivot(parent);\n      rod.name = `zephyrRod_${name}`;\n      const c = name === "middle" ? 0 : sign * r;\n      mesh(rod, cyl(.029,.029,r*2,12), lacquer, [0,c,0]);\n      // Two red spiraling wrap bands; rods stay rigid, unscaled, and separate.\n      for (let i = 0; i < 5; i++) {\n        const y = name === "middle" ? -.22+i*.11 : sign*(.11+i*.11);\n        mesh(rod, cyl(.033,.033,.035,12), i%2 ? black : red, [0,y,0]);\n      }\n      const ends = name === "middle" ? [-r,r] : [0,sign*2*r];\n      for (const y of ends) {\n        mesh(rod, cyl(.046,.042,.070,12), darkMetal, [0,y,0]);\n        mesh(rod, cyl(.049,.046,.018,12), ferrule, [0,y+Math.sign(y||sign)*.029,0]);\n        mesh(rod, torus(.036,.046), red, [0,y-Math.sign(y||sign)*.048,0]);\n      }\n      if (name === "middle") {\n        makeSocket(rod,"middle:low",-r);\n        makeSocket(rod,"middle:mid",0);\n        makeSocket(rod,"middle:high",r);\n      } else {\n        makeSocket(rod,`${name}:near`,0);\n        makeSocket(rod,`${name}:mid`,sign*r);\n        makeSocket(rod,`${name}:far`,sign*2*r);\n      }\n      return rod;\n    };\n    makeRod(root,"middle",1);\n    const buildChain = (sign: number, name: "upper"|"lower", index: number) => {\n      const hinge = pivot(root, [0, sign*.325, 0]);\n      hinge.name = `zephyrChainJoint_${name}`;\n      this.dragonHinges[index] = hinge;\n      const links: THREE.Group[] = [];\n      let prev: THREE.Group = hinge;\n      // Exactly four overlapping metal links, 0.13 metres between rod ends.\n      for (let k=0; k<4; k++) {\n        const link = pivot(prev, [0, sign*(k===0 ? .01625 : .0325), 0]);\n        link.name = `zephyrChain_${name}_${k}`;\n        mesh(link, torus(.008,.022), ferrule, [0,0,0], [k%2 ? PI/2 : 0,0,k%2 ? PI/2 : 0]);\n        links.push(link);\n        prev = link;\n      }\n      // Final half-link completes a real 0.13-unit gap.\n      const end = pivot(prev,[0,sign*.01625,0]);\n      const rod = makeRod(end,name,sign);\n      this.dragonRods[index] = rod;\n      this.dragonChains[index] = links;\n    };\n    buildChain(1,"upper",0);\n    buildChain(-1,"lower",1);\n    this.dragonHands = {left:null,right:"middle:mid"};\n    this.gripL = null;\n    this.bladeBase = this.dragonSockets["middle:high"];\n    this.bladeTip = this.dragonSockets["upper:far"];\n    this.castPoint = this.bladeTip;\n    this.shieldNode = root;\n    // Clone the COMPLETE structure (three rods, both four-link chains and sockets).\n    this.dragonGhost = root.clone(true);\n    this.dragonGhost.name = "zephyrTossedDisplayOnly";\n    this.dragonGhost.visible = false;\n    this.add(this.dragonGhost);\n  }\n\n  /** Spring integration; frame-rate independent damping and a fixed 160-degree stop. */\n  private dragonSpring(value: number, target: number, slot: number, dt: number): number {\n    const h = Math.min(.034, Math.max(0,dt));\n    const vel = this.dragonJointVel[slot];\n    const nextVel = (vel+(target-value)*150*h)*Math.exp(-17*h);\n    this.dragonJointVel[slot] = nextVel;\n    return THREE.MathUtils.clamp(value+nextVel*h,-2.77,2.77);\n  }\n\n  /** Visual-only grip swaps and independent chain dynamics, keyed by existing dragonPose.\n   * Holding hand anchors the physical rod directly. The other hand uses VRM IK.\n   * A released hand is null and its fingers relax. The free rods trail the anchor.\n   */\n  private updateDragonStaff(dt: number) {\n    const root=this.dragonRoot;\n    if (!root || !this.dragonRods[0] || !this.dragonRods[1]) return;\n    const pose=this.dragonPose;\n    const show=pose==="show_tristaff";\n    const phase=show ? ((this.presentationT%9)+9)%9 : 0;\n    const p=THREE.MathUtils.clamp(this.dragonProgress,0,1);\n    let right: string|null="middle:mid", left: string|null=null;\n    let anchor: "right"|"left"|null="right";\n    let fold=pose==="zdx_w" || pose==="zdx_s";\n    let taut=["zd5_s","zdh_s","zdz_s","zdc_s","zdv_s","zdv_finish"].includes(pose) && p>.67;\n    let spin=0;\n    const strike=pose.endsWith("_s");\n    const name=pose.slice(0,3);\n    // Socket decisions are independent of combat; only animation is affected.\n    if (pose==="idle") {\n      spin=Math.sin(this.t*1.8)*.52;\n      if (Math.sin(this.t*.75)>0.82) {left="upper:near";right=null;anchor="left";}\n    } else if (pose==="zd1_w" || pose==="zd1_s") {\n      right="middle:low"; spin=strike?p*1.15:-.35;\n    } else if (pose==="zd2_w" || pose==="zd2_s") {\n      left="lower:near";right=null;anchor="left";spin=p*.75;\n    } else if (pose==="zd3_w" || pose==="zd3_s") {\n      right="middle:mid";spin=p*PI*2;\n    } else if (pose==="zd4_w" || pose==="zd4_s") {\n      const passed=strike && p>.54;\n      anchor=passed?"left":"right";\n      right=passed?null:"middle:high";\n      left=passed?"upper:mid":null;\n      spin=p*PI*2.4;\n    } else if (pose==="zd5_w" || pose==="zd5_s") {\n      right="middle:low";left="lower:far";spin=p*1.8;\n    } else if (pose==="zdh_w" || pose==="zdh_s") {\n      right="middle:mid";left=strike&&p>.58?"upper:near":null;\n      spin=strike?p*2.9:-.7;\n    } else if (name==="zdz") {\n      const n=Math.min(2,Math.floor(p*3));\n      anchor=n%2?"left":"right";\n      right=anchor==="right"?"middle:mid":null;\n      left=anchor==="left"?"upper:near":null;\n      spin=p*PI*6;\n    } else if (name==="zdc") {\n      const n=Math.min(4,Math.floor(p*5));\n      anchor=n%2?"left":"right";\n      right=anchor==="right"?(n===4?"lower:near":"middle:mid"):null;\n      left=anchor==="left"?"upper:mid":null;\n      // Momentary release between five catches.\n      if ((p*5)%1 >.88 && n<4) {right=null;left=null;anchor=null;}\n      spin=p*PI*8;\n    } else if (name==="zdv") {\n      const n=Math.min(8,Math.floor(p*9));\n      anchor=n%2?"left":"right";\n      right=anchor==="right"?"middle:mid":null;\n      left=anchor==="left"?"lower:near":null;\n      spin=p*PI*8;\n    } else if (fold) {\n      right="middle:mid";left=null;\n    }\n    if (show) {\n      if (phase<1.35) {right="middle:low";left=null;anchor="right";}\n      else if (phase<2.50) {right=null;left="upper:near";anchor="left";}\n      else if (phase<3.65) {right="lower:near";left=null;anchor="right";}\n      else if (phase<4.52) {right=null;left="middle:mid";anchor="left";}\n      else if (phase<6.24) {right=null;left=null;anchor=null;}\n      else if (phase<7.5) {right="upper:mid";left=null;anchor="right";}\n      else {right="middle:low";left="lower:far";anchor="right";}\n      spin=phase<4.52?phase*PI*2.2:phase<6.24?0:(phase-6.24)*PI*2;\n      taut=phase>7.62;\n    }\n    const b=DRAGON_STAFF_ROTATIONS[pose]??DRAGON_STAFF_ROTATIONS.idle;\n    this.dragonTargetQ.setFromEuler(this.dragonTmpEuler.set(b[0],b[1],b[2],"YXZ"));\n    if (spin) {\n      this.dragonSpinQ.setFromAxisAngle(this.dragonAxisZ,spin);\n      this.dragonTargetQ.multiply(this.dragonSpinQ);\n      this.dragonSpinQ.setFromAxisAngle(this.dragonAxisY,Math.sin(spin*.5)*.30);\n      this.dragonTargetQ.multiply(this.dragonSpinQ);\n    }\n    root.quaternion.slerp(this.dragonTargetQ,1-Math.exp(-20*Math.min(dt,.05)));\n    // Opposite hinges flex in two axes; rotational lag + clamped swing keeps rods rigid.\n    for (let i=0; i<2; i++) {\n      const hinge=this.dragonHinges[i];\n      const rod=this.dragonRods[i];\n      const sign=i===0?1:-1;\n      if (!hinge||!rod) continue;\n      const sway=(show?Math.sin(phase*5.6+i):Math.sin(this.t*4.0+i*2.1)) * (strike?.42:.22);\n      const targetZ=fold?sign*2.62:taut?0:sign*(.49+sway+.39*Math.sin(spin*.43+i));\n      const targetX=fold?sign*.13:taut?0:sign*(.27*Math.cos(spin*.64+i)+.14*Math.sin(this.t*2.1));\n      hinge.rotation.z=this.dragonSpring(hinge.rotation.z,targetZ,i*3,dt);\n      hinge.rotation.x=this.dragonSpring(hinge.rotation.x,targetX,i*3+1,dt);\n      hinge.rotation.y=this.dragonSpring(hinge.rotation.y,.17*Math.sin(this.t*3.4+i),i*3+2,dt);\n      rod.rotation.z=THREE.MathUtils.damp(rod.rotation.z,fold?-sign*.25:taut?0:sign*.18*Math.sin(this.t*4.5+i),14,dt);\n      rod.rotation.x=THREE.MathUtils.damp(rod.rotation.x,fold?0:.12*Math.sin(this.t*3.1+i),13,dt);\n      rod.rotation.y=THREE.MathUtils.damp(rod.rotation.y,.1*Math.sin(this.t*2.4+i),11,dt);\n      const links=this.dragonChains[i];\n      for (let k=0;k<links.length;k++) {\n        const link=links[k];\n        const bend=fold?.13:taut?0:.15*Math.sin(this.t*7+i*.8+k*.65);\n        link.rotation.z=THREE.MathUtils.damp(link.rotation.z,sign*bend,21,dt);\n        link.rotation.x=THREE.MathUtils.damp(link.rotation.x,bend*.45,21,dt);\n      }\n    }\n    // Drive the entire articulated hierarchy from the socket on the currently held rod.\n    // A free/toss interval leaves the hand mounts unattached; the ghost handles flying.\n    this.dragonHands.left=left; this.dragonHands.right=right;\n    this.dragonAnchor=anchor;\n    if (!anchor && !show) {\n      // Brief releases in Heavenly Cyclone preserve world-space momentum.\n      // Neither hand falsely grips a rod during the airborne beat.\n      if (root.parent!==this) this.attach(root);\n      root.position.y += Math.sin(this.t*8.0)*.028*Math.min(dt,.05);\n      root.position.z += .075*Math.min(dt,.05);\n    }\n    if (anchor) {\n      const hand=anchor==="right"?this.hand_r:this.hand_l;\n      if (root.parent!==hand) hand.add(root);\n      const socket=this.dragonSockets[anchor==="right"?right!:left!];\n      if (socket) {\n        root.position.set(0,0,0);\n        root.updateMatrixWorld(true);\n        socket.getWorldPosition(this.dragonTmpV);\n        root.worldToLocal(this.dragonTmpV);\n        root.position.copy(this.dragonTmpV.applyQuaternion(root.quaternion).negate());\n      }\n    }\n    this.gripL=left?this.dragonSockets[left]:null;\n    const gripR=right?this.dragonSockets[right]:null;\n    this.bladeTip=this.dragonSockets[pose==="zd2_s"||pose==="zdc_s"?"lower:far":"upper:far"];\n    this.bladeBase=this.dragonSockets["middle:high"];\n    this.castPoint=this.bladeTip;\n    if (this.vrmRig) {\n      this.vrmRig.gripL=this.gripL;\n      this.vrmRig.gripR=gripR;\n      this.vrmRig.tristaffAnchor=anchor;\n      this.vrmRig.grip.left=left!==null;\n      this.vrmRig.grip.right=right!==null;\n    }\n    // Presentation toss: a complete independent clone, not individual floating rods.\n    const toss=show && phase>=4.52 && phase<6.24;\n    if (toss && this.dragonGhost) {\n      if (!this.dragonWasTossed) {\n        this.updateMatrixWorld(true);\n        root.getWorldPosition(this.dragonTmpV);\n        this.dragonThrowStart.copy(this.worldToLocal(this.dragonTmpV));\n        root.getWorldQuaternion(this.dragonTmpQ);\n        this.getWorldQuaternion(this.dragonThrowQuat).invert();\n        this.dragonThrowQuat.multiply(this.dragonTmpQ);\n        root.getWorldScale(this.dragonTmpV);\n        this.getWorldScale(this.dragonTmpS);\n        this.dragonThrowScale.set(this.dragonTmpV.x/this.dragonTmpS.x,\n          this.dragonTmpV.y/this.dragonTmpS.y,this.dragonTmpV.z/this.dragonTmpS.z);\n        this.dragonWasTossed=true;\n      }\n      const u=(phase-4.52)/1.72;\n      root.visible=false;\n      this.dragonGhost.visible=true;\n      this.dragonGhost.position.copy(this.dragonThrowStart);\n      this.dragonGhost.position.y+=Math.sin(u*PI)*.86;\n      this.dragonGhost.position.x+=Math.sin(u*PI)*.17;\n      this.dragonGhost.quaternion.copy(this.dragonThrowQuat);\n      this.dragonSpinQ.setFromAxisAngle(this.dragonAxisZ,u*PI*6);\n      this.dragonGhost.quaternion.multiply(this.dragonSpinQ);\n      this.dragonGhost.scale.copy(this.dragonThrowScale);\n      // Copy each articulated joint and chain angle to the matching ghost node.\n      for (let i=0;i<2;i++) {\n        const name=i===0?"upper":"lower";\n        const ghostHinge=this.dragonGhost.getObjectByName(`zephyrChainJoint_${name}`);\n        if (ghostHinge) ghostHinge.quaternion.copy(this.dragonHinges[i].quaternion);\n        const ghostRod=this.dragonGhost.getObjectByName(`zephyrRod_${name}`);\n        if (ghostRod) ghostRod.quaternion.copy(this.dragonRods[i].quaternion);\n        for(let k=0;k<4;k++) {\n          const gl=this.dragonGhost.getObjectByName(`zephyrChain_${name}_${k}`);\n          if(gl) gl.quaternion.copy(this.dragonChains[i][k].quaternion);\n        }\n      }\n    } else {\n      root.visible=true;\n      if(this.dragonGhost)this.dragonGhost.visible=false;\n      this.dragonWasTossed=false;\n    }\n  }\n'
MODEL_PROPERTIES = '  // ZEPHYR_DRAGON_DANCER_V1 · SANJIEKUN_VISUAL_V17 — articulated rod/chain rig.\n  private dragonRoot: THREE.Group | null = null;\n  private dragonGhost: THREE.Group | null = null;\n  private dragonRods: THREE.Group[] = [];\n  private dragonHinges: THREE.Group[] = [];\n  private dragonChains: THREE.Group[][] = [[],[]];\n  private dragonSockets: Record<string, THREE.Group> = {};\n  private dragonHands: {left: string|null; right: string|null} = {left:null,right:null};\n  private dragonAnchor: "left"|"right"|null = "right";\n  private dragonJointVel = [0,0,0,0,0,0];\n  private dragonTmpV = new THREE.Vector3();\n  private dragonTmpS = new THREE.Vector3();\n  private dragonTmpQ = new THREE.Quaternion();\n  private dragonTargetQ = new THREE.Quaternion();\n  private dragonSpinQ = new THREE.Quaternion();\n  private dragonTmpEuler = new THREE.Euler(0,0,0,"YXZ");\n  private dragonAxisY = new THREE.Vector3(0,1,0);\n  private dragonAxisZ = new THREE.Vector3(0,0,1);\n  private dragonThrowStart = new THREE.Vector3();\n  private dragonThrowQuat = new THREE.Quaternion();\n  private dragonThrowScale = new THREE.Vector3(1,1,1);\n  private dragonWasTossed = false;\n  dragonPose = "idle";\n  dragonProgress = 0;\n'
MODEL_ROTATIONS = 'const DRAGON_STAFF_ROTATIONS: Record<string,[number,number,number]> = {\n      idle:[1.55,-.19,.14],block:[1.47,.11,.16],\n      zd1_w:[1.48,-.51,-.28],zd1_s:[1.04,.47,.28],\n      zd2_w:[1.76,.41,.26],zd2_s:[1.23,-.50,-.32],\n      zd3_w:[1.35,-.47,-.32],zd3_s:[1.58,.47,.28],\n      zd4_w:[1.75,-.61,.35],zd4_s:[1.12,.62,-.41],\n      zd5_w:[2.22,-.22,.15],zd5_s:[.71,.31,-.12],\n      zdh_w:[2.14,-.25,.12],zdh_s:[.82,.38,-.18],\n      zdz_w:[1.77,-.34,.15],zdz_s:[1.25,.33,-.24],\n      zdx_w:[1.44,-.13,.13],zdx_s:[1.28,.18,-.17],\n      zdc_w:[1.70,-.45,.19],zdc_s:[1.32,.53,-.33],\n      zdv_w:[2.02,-.28,.12],zdv_s:[1.12,.51,-.25],\n      zdv_finish:[.68,.29,-.18],\n};\n'
RIG_PROPERTIES = '  /** SANJIEKUN_VISUAL_V17: generic right-hand grip, mirroring gripL. */\n  gripR: THREE.Object3D | null = null;\n  /** Enables two-rod socket IK only for Zephyr; does not alter other kits. */\n  tristaff = false;\n  tristaffAnchor: "left" | "right" | null = "right";\n'
RIG_METHOD = '  // SANJIEKUN_VISUAL_V17: the weapon is anchored on one VRM hand and never\n  // IK-solved against that same hand (would make an oscillating feedback loop).\n  // Only the opposite, explicitly gripping hand is solved to its rod socket.\n  private tristaffHands(setNow: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {\n    const root = this.j.root;\n    root.updateMatrixWorld(true);\n    if (this.gripL && this.tristaffAnchor !== "left") {\n      const point = root.worldToLocal(this.gripL.getWorldPosition(_v));\n      this.solveArm("left", point, _v2.set(.76,-.55,-.3), setNow);\n    }\n    if (this.gripR && this.tristaffAnchor !== "right") {\n      const point = root.worldToLocal(this.gripR.getWorldPosition(_v));\n      this.solveArm("right", point, _v2.set(-.76,-.55,-.3), setNow);\n    }\n  }\n\n'
PRESENTATION_VISUAL = '// ZEPHYR_DRAGON_DANCER_V1 · SANJIEKUN_VISUAL_V17 — 9-second playful linked-rod show.\nfunction zephyrPresentation(seconds: number, base: Pose, mode: "select" | "victory"): Pose {\n  const t=mode==="select"?((seconds%9)+9)%9:Math.min(seconds,8.85);\n  const beats: Array<[number,Beat]> = [\n    [0, {torso:[.08,-.35,.08],head:[-.07,.22,.05],arm_r:[-.88,.25,-.32],arm_l:[-.75,-.31,.38],leg_l:[-.22,0,.13],leg_r:[.26,0,-.14],hips_y:-.09}],\n    [.50,{torso:[.10,-.57,.13],head:[-.03,.30,-.04],arm_r:[-1.45,.53,-.26],arm_l:[-.78,-.25,.48],hips_y:-.13}],\n    [1.16,{torso:[-.07,.51,-.13],head:[-.16,-.12,.06],arm_r:[-1.75,-.22,-.18],arm_l:[-1.36,.42,.33],leg_l:[-.37,0,.13],leg_r:[.33,0,-.18],hips_y:-.05}],\n    [1.58,{torso:[.12,-.42,.11],head:[-.01,.24,-.07],arm_r:[-.68,.33,-.5],arm_l:[-1.84,-.32,.20],hips_y:-.11}],\n    [2.18,{torso:[.08,.53,-.08],head:[-.14,-.27,.06],arm_r:[-1.04,.21,-.3],arm_l:[-2.2,.35,.39],leg_l:[-.40,0,.18],leg_r:[.36,0,-.13],hips_y:-.07}],\n    [2.63,{torso:[.12,-.58,.12],head:[-.05,.36,-.02],arm_r:[-1.76,-.65,-.38],arm_l:[-1.1,-.31,.50],hips_y:-.12}],\n    [3.2,{torso:[-.10,.60,-.06],head:[-.12,-.24,.02],arm_r:[-2.07,.62,-.20],arm_l:[-.68,.23,.43],leg_l:[-.37,0,.15],leg_r:[.35,0,-.17],hips_y:-.07}],\n    [3.75,{torso:[.20,-.38,.09],head:[-.02,.3,.02],arm_r:[-1.65,.41,-.33],arm_l:[-2.28,-.29,.36],hips_y:-.12}],\n    [4.45,{torso:[-.19,-.28,0],head:[-.05,.17,0],arm_r:[-2.38,.16,-.15],arm_l:[-.55,-.46,.49],hips_y:-.07}],\n    [4.70,{torso:[-.16,-.32,.03],head:[-.22,.11,.04],arm_r:[-2.42,.14,-.19],arm_l:[-.74,-.33,.48],hips_y:-.06}],\n    [5.30,{torso:[.16,.46,.06],head:[.08,-.10,.01],arm_r:[-.62,.46,-.29],arm_l:[-1.12,-.19,.29],leg_l:[-.55,0,.08],leg_r:[-.85,0,-.09],hips_y:.05}],\n    [6.18,{torso:[.11,.19,-.06],head:[-.16,.15,.02],arm_r:[-2.37,.25,-.29],arm_l:[-1.48,-.24,.37],hips_y:-.08}],\n    [6.53,{torso:[.12,-.48,.09],head:[-.02,.30,0],arm_r:[-1.34,.35,-.35],arm_l:[-1.14,-.34,.36],hips_y:-.12}],\n    [7.08,{torso:[-.04,.52,-.13],head:[-.13,-.25,.04],arm_r:[-2.03,.36,-.39],arm_l:[-.95,.13,.41],leg_l:[-.31,0,.2],leg_r:[.33,0,-.12],hips_y:-.07}],\n    [7.63,{torso:[.39,.17,.07],head:[-.16,-.05,.02],arm_r:[-.84,.19,-.48],arm_l:[-1.56,-.14,.36],leg_l:[-.49,0,.18],leg_r:[.34,0,-.15],hips_y:-.18,knee:[.45,.38]}],\n    [8.38,{torso:[.12,-.26,.05],head:[-.08,.15,.01],arm_r:[-.91,.32,-.34],arm_l:[-1.02,-.24,.38],hips_y:-.11}],\n    [9, {torso:[.08,-.35,.08],head:[-.07,.22,.05],arm_r:[-.88,.25,-.32],arm_l:[-.75,-.31,.38],leg_l:[-.22,0,.13],leg_r:[.26,0,-.14],hips_y:-.09}],\n  ];\n  let i=0; while(i<beats.length-2 && t>beats[i+1][0])i++;\n  const lo=beats[i],hi=beats[i+1];\n  const u=Math.max(0,Math.min(1,(t-lo[0])/Math.max(.001,hi[0]-lo[0])));\n  return between(filled(base,lo[1]),filled(base,hi[1]),u);\n}\n'
ADDITIONAL_POSES = '  // SANJIEKUN_VISUAL_V17: presentation-only poses; damage and hitboxes untouched.\n  zd_fold: P([.12,-.17,.07],[-.08,.15,.04],[-1.36,.30,-.4],[.22,0,-.08],[-.68,-.30,.52],[0,0,.05],[-.33,0,.16],[.38,0,-.12],-.12),\n  zd_catch: P([.20,.25,-.08],[-.12,-.05,.08],[-1.7,.38,-.25],[.19,0,.12],[-1.42,-.10,.31],[.21,0,.07],[-.42,0,.15],[.44,0,-.15],-.13),\n  zd_handpass: P([-.07,.55,.13],[-.13,-.20,.06],[-1.13,-.22,-.32],[.18,0,.19],[-2.1,.43,.41],[.13,0,.13],[-.51,0,.19],[.34,0,-.12],-.10),\n  zd_sway: P([.09,-.31,-.11],[-.07,.18,.08],[-.9,.31,-.43],[.15,0,.13],[-1.14,-.31,.39],[.24,0,.1],[-.17,0,.17],[.31,0,-.19],-.09),\n'


def replace_bounded(path: str, beginning: str, ending: str, replacement: str):
    src=changes[path]
    if src.count(beginning)!=1 or src.count(ending)!=1:
        raise RuntimeError(f'{path}: required unique region not found; refusing to modify.')
    i=src.index(beginning);j=src.index(ending)
    if j<=i: raise RuntimeError(f'{path}: invalid region order')
    changes[path]=src[:i]+replacement+src[j:]


def upgrade_zephyr_visuals():
    f='src/game/model.ts'
    replace_bounded(f,
        '  // ZEPHYR_DRAGON_DANCER_V1: actual connected sections, each on an animated joint.',
        '  // NYTHERA_GRAVITY_REAPER_INSTALL_V1', MODEL_PROPERTIES)
    replace_bounded(f,
        '  /** ZEPHYR_DRAGON_DANCER_V1: three rigid rods and two visible moving connectors.',
        '  /** ZAREK_STORM_V1: double-ended conductive glaive;', MODEL_VISUAL)
    patch(f, 'const JOINTS = ["torso", "head", "arm_r", "hand_r", "arm_l", "hand_l", "leg_l", "leg_r"] as const;',
          'const JOINTS = ["torso", "head", "arm_r", "hand_r", "arm_l", "hand_l", "leg_l", "leg_r"] as const;\n\n' + MODEL_ROTATIONS)
    # Do not run legacy left-arm sword IK against the newly movable Zephyr rod sockets.
    legacy='''    } else if (this.gripL && !noScytheGrip && !(this.kit === "tristaff" && this.dragonPose === "show_tristaff" &&
        this.presentationT % 9 > 4.1 && this.presentationT % 9 < 6.33)) this.reachGrip();'''
    revised='''    } else if (this.kit === "tristaff") {
      // SANJIEKUN_VISUAL_V17: only drive a NON-anchor hand through IK.
      if (!this.vrmRig) {
        if (this.dragonAnchor === "right" && this.gripL) this.reachZenithGrip("left",this.gripL);
        if (this.dragonAnchor === "left" && this.dragonHands.right)
          this.reachZenithGrip("right",this.dragonSockets[this.dragonHands.right]);
      }
    } else if (this.gripL && !noScytheGrip) this.reachGrip();'''
    patch(f,legacy,revised)
    patch(f, '    // Staffs and bows follow the arm a lot (natural tilt); blades less, to keep swing arcs.',
          '    if (this.kit === "tristaff") {\n      this.vrmRig.tristaff = true;\n      this.vrmRig.tristaffAnchor = "right";\n    }\n'
          '    // Staffs and bows follow the arm a lot (natural tilt); blades less, to keep swing arcs.')
    f='src/game/vrm.ts'
    patch(f,'  gripL: THREE.Object3D | null = null;', '  gripL: THREE.Object3D | null = null;\n'+RIG_PROPERTIES)
    patch(f,'    if (this.style === "magnetic" && this.spearGripR) this.zenithSpearHands(setNow);',
          '    if (this.tristaff) this.tristaffHands(setNow);\n'
          '    else if (this.style === "magnetic" && this.spearGripR) this.zenithSpearHands(setNow);')
    before(f,'  private zenithSpearHands(setNow:', RIG_METHOD)
    f='src/game/presentation.ts'
    replace_bounded(f,
        '// ZEPHYR_DRAGON_DANCER_V1 — nine-second showcase in readable beats.',
        '/** Entirely cosmetic; all poses use the same normalized VRM/procedural joints as combat. */',
        PRESENTATION_VISUAL+'\n')
    f='src/game/kits.ts'
    # Add named poses within Zephyr's DRAGON_STAFF table only.
    patch(f,'  zdv_finish: P([.52,.30,0],[-.19,-.08,0],[-.55,.47,-.25],[.11,0,.16],[-.84,.31,.28],[.10,0,.10],[-.83,0,.13],[.59,0,-.13],-.22),',
          '  zdv_finish: P([.52,.30,0],[-.19,-.08,0],[-.55,.47,-.25],[.11,0,.16],[-.84,.31,.28],[.10,0,.10],[-.83,0,.13],[.59,0,-.13],-.22),\n'+ADDITIONAL_POSES.rstrip())


def remove_kaizen_block_recoil():
    # Defending as Kaizen: no attacker-forced clash recoil or charged-attack cancel.
    f='src/game/fighter.ts'
    patch(f,'''      // KAIZEN_GUARD_CLASH_V8: the spinning chain catches incoming melee weapons.
      // Parry (above) and guard break (above) retain priority; projectiles still block.
      if (this.kit === "chainblade" && attacker instanceof Fighter && a.type === "melee") {
        this.knock = Math.min(a.knock * 0.12, 0.5);
        this.model.recoil = 0.85;
        return "kaizen_guard_clash";
      }''', '''      // KAIZEN_BLOCK_NO_RECOIL_V17: clean block, no special clash or charge interruption.
      // Normal guard damage and guard breaks still happen above.
      if (this.kit === "chainblade" && attacker instanceof Fighter && a.type === "melee") {
        this.knock = 0;
        this.model.recoil = 0.12; // small defensive animation only
        return "blocked";
      }''')
    f='src/game/game.ts'
    patch(f,'''        if (attacker instanceof Fighter) {
          // Weapon-on-weapon clashes never award projectile-destruction Momentum.
          attacker.clashRecoil();
        }''', '''        // KAIZEN_BLOCK_NO_RECOIL_V17: legacy clash visual must never cancel
        // an attacking fighter's charged move if an older path reaches here.''')
    patch(f, '        if (!ranged && attacker instanceof Fighter) attacker.model.recoil = 0.6;',
          '        if (!ranged && attacker instanceof Fighter && attacker.kit !== "chainblade" &&\n'
          '            !(d instanceof Fighter && d.kit === "chainblade")) attacker.model.recoil = 0.6;')


# ZEPHYR_DRAGON_MODE_V18: F modes, deterministic grips, independent weapon holder.
# The existing V17 code is included above; upgrades work whether Zephyr is
# already installed or is being installed fresh over a compatible V16 base.
MODE_MARK = 'ZEPHYR_DRAGON_MODE_V18'
GRIP_TIMELINES_SOURCE = r'''
// ZEPHYR_DRAGON_MODE_V18 — socket events are normalized 0..1 of the move.
// Arrays are indexed STAFF(0), SPLIT(1), WHIP(2), FOLDED(3).
// A null socket releases that hand. A move's next catch is anticipated by 0.18 progress.
type DragonGripEvent = { t: number; R: string | null; L: string | null };
const GRIP_TIMELINE: Record<string, DragonGripEvent[][]> = {
  idle: [
    [{t:0,R:"middle:mid",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.70,R:"upper:mid",L:"lower:mid"}],
    [{t:0,R:"middle:low",L:null},{t:.75,R:"middle:mid",L:null}],
    [{t:0,R:"middle:mid",L:null}],
  ],
  l1: [
    [{t:0,R:"middle:low",L:"middle:mid"},{t:.78,R:"middle:mid",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.48,R:"upper:mid",L:"lower:far"}],
    [{t:0,R:"middle:low",L:null},{t:.45,R:"middle:mid",L:null}],
    [{t:0,R:"middle:mid",L:null},{t:.75,R:"middle:high",L:null}],
  ],
  l2: [
    [{t:0,R:"middle:mid",L:"middle:low"},{t:.64,R:"middle:high",L:"middle:low"}],
    [{t:0,R:"upper:mid",L:"lower:far"},{t:.38,R:null,L:"lower:far"},{t:.75,R:"upper:far",L:"lower:mid"}],
    [{t:0,R:"lower:near",L:null},{t:.55,R:null,L:"lower:far"}],
    [{t:0,R:"middle:mid",L:null},{t:.65,R:null,L:"upper:near"}],
  ],
  l3: [
    [{t:0,R:"middle:mid",L:"middle:low"},{t:.72,R:"middle:high",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:mid"},{t:.53,R:"upper:mid",L:"lower:far"}],
    [{t:0,R:"middle:low",L:null},{t:.56,R:"middle:high",L:null}],
    [{t:0,R:"middle:mid",L:null},{t:.5,R:"middle:low",L:null}],
  ],
  l4: [
    [{t:0,R:"middle:high",L:"middle:low"},{t:.55,R:null,L:"middle:low"},{t:.78,R:"middle:high",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.38,R:null,L:"lower:far"},{t:.62,R:"upper:mid",L:"lower:far"}],
    [{t:0,R:"middle:low",L:null},{t:.38,R:null,L:null},{t:.56,R:null,L:"upper:near"}],
    [{t:0,R:"middle:mid",L:null},{t:.46,R:null,L:"middle:mid"}],
  ],
  l5: [
    [{t:0,R:"middle:high",L:"middle:low"},{t:.79,R:"middle:mid",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.65,R:"upper:mid",L:"lower:mid"}],
    [{t:0,R:"middle:low",L:null},{t:.70,R:"middle:high",L:"lower:far"}],
    [{t:0,R:"middle:mid",L:null},{t:.73,R:"middle:low",L:null}],
  ],
  heavy: [
    [{t:0,R:"middle:low",L:"middle:high"},{t:.72,R:"middle:mid",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.65,R:"upper:mid",L:"lower:mid"}],
    [{t:0,R:"middle:low",L:null},{t:.55,R:null,L:null},{t:.73,R:"upper:near",L:"lower:near"}],
    [{t:0,R:"middle:mid",L:null},{t:.66,R:"middle:high",L:null}],
  ],
  z: [
    [{t:0,R:"middle:low",L:"middle:high"},{t:.42,R:"middle:mid",L:"middle:low"},{t:.78,R:"middle:high",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.38,R:"upper:mid",L:"lower:far"},{t:.7,R:"upper:far",L:"lower:mid"}],
    [{t:0,R:"middle:low",L:null},{t:.32,R:null,L:"lower:near"},{t:.66,R:"middle:low",L:null}],
    [{t:0,R:"middle:mid",L:null},{t:.51,R:null,L:"middle:mid"},{t:.78,R:"middle:mid",L:null}],
  ],
  x: [
    [{t:0,R:"middle:mid",L:"middle:low"},{t:.6,R:"middle:mid",L:"middle:low"}],
    [{t:0,R:"upper:mid",L:"lower:mid"},{t:.52,R:"upper:far",L:"lower:far"}],
    [{t:0,R:"middle:low",L:null},{t:.50,R:"middle:mid",L:null}],
    [{t:0,R:"middle:mid",L:null},{t:.65,R:"middle:low",L:null}],
  ],
  c: [
    [{t:0,R:"middle:low",L:"middle:high"},{t:.2,R:null,L:"middle:low"},{t:.4,R:"middle:high",L:null},{t:.6,R:null,L:"middle:low"},{t:.8,R:"middle:mid",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.2,R:null,L:"lower:far"},{t:.4,R:"upper:mid",L:null},{t:.6,R:null,L:"lower:mid"},{t:.8,R:"upper:far",L:"lower:far"}],
    [{t:0,R:"middle:low",L:null},{t:.2,R:null,L:"upper:near"},{t:.4,R:"lower:near",L:null},{t:.6,R:null,L:null},{t:.8,R:"middle:low",L:null}],
    [{t:0,R:"middle:mid",L:null},{t:.2,R:null,L:"middle:mid"},{t:.4,R:"middle:mid",L:null},{t:.6,R:null,L:"middle:low"},{t:.8,R:"middle:mid",L:null}],
  ],
  v: [
    [{t:0,R:"middle:low",L:"middle:high"},{t:.25,R:null,L:"middle:low"},{t:.52,R:"middle:high",L:null},{t:.79,R:"middle:high",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.25,R:null,L:"lower:far"},{t:.52,R:"upper:far",L:null},{t:.79,R:"upper:mid",L:"lower:mid"}],
    [{t:0,R:"middle:low",L:null},{t:.25,R:null,L:"lower:near"},{t:.52,R:"middle:low",L:null},{t:.79,R:"upper:near",L:null}],
    [{t:0,R:"middle:mid",L:null},{t:.52,R:null,L:"middle:mid"},{t:.79,R:"middle:mid",L:null}],
  ],
  show_tristaff: [
    [{t:0,R:"middle:mid",L:"middle:low"},{t:.35,R:null,L:"middle:high"},{t:.72,R:"middle:mid",L:"middle:low"}],
    [{t:0,R:"upper:far",L:"lower:far"},{t:.35,R:null,L:"lower:mid"},{t:.72,R:"upper:mid",L:"lower:far"}],
    [{t:0,R:"middle:low",L:null},{t:.35,R:null,L:"lower:near"},{t:.72,R:"middle:mid",L:null}],
    [{t:0,R:"middle:mid",L:null},{t:.35,R:null,L:"middle:mid"},{t:.72,R:"middle:mid",L:null}],
  ],
};
// Socket-palm alignment; thrust grips run along the forearm, normal grips cross palm.
const DRAGON_SOCKET_PALM: Record<string, number> = {
  "middle:low": .12, "middle:mid": 0, "middle:high": -.12,
  "upper:near": .16, "upper:mid": 0, "upper:far": -.10,
  "lower:near": -.16, "lower:mid": 0, "lower:far": .10,
};

'''
DRAGON_MODEL_METHOD = r'''
  /** ZEPHYR_DRAGON_MODE_V18: detached three-section weapon, four modes and weighted socket IK.
   * No children of either hand bone; holder changes are blended in model space.
   * All 3 rods remain rigid; chain joints flex in two axes plus a minor twist.
   */
  private updateDragonStaff(dt: number) {
    const root=this.dragonRoot;
    if (!root || this.dragonRods.length<2) return;
    const pose=this.dragonPose;
    const show=pose==="show_tristaff";
    const phase=show?((this.presentationT%9)+9)%9:0;
    const mode=show?Math.min(3,Math.floor(phase/2.25)):this.dragonMode;
    if(mode!==this.dragonLastVisualMode){
      this.dragonPreviousMode=this.dragonLastVisualMode;
      this.dragonLastVisualMode=mode;
      this.dragonModeBlend=0;
    }
    this.dragonModeBlend=Math.min(1,this.dragonModeBlend+dt/.25);
    const modeBlend=this.dragonModeBlend*this.dragonModeBlend*(3-2*this.dragonModeBlend);
    const p=show?((phase%2.25)/2.25):THREE.MathUtils.clamp(this.dragonProgress,0,1);
    const key=show?"show_tristaff":/^zd[1-5]_/.test(pose)?"l"+pose[2]:
      /^zdh/.test(pose)?"heavy":/^zdz/.test(pose)?"z":/^zdx/.test(pose)?"x":
      /^zdc/.test(pose)?"c":/^zdv/.test(pose)?"v":"idle";
    const timeline=GRIP_TIMELINE[key]?.[mode]??GRIP_TIMELINE.idle[mode];
    let current=timeline[0];
    for(const event of timeline) if(p>=event.t) current=event;
    // Predict the next catch up to ~0.2 progress units before the actual grip change.
    let upcoming: DragonGripEvent|null=null;
    for(const event of timeline) if(event.t>p){upcoming=event;break;}
    let right=current.R, left=current.L;
    const toss=show && phase>=4.52 && phase<6.24;
    if(toss){right=null;left=null;}
    const catching=upcoming&&upcoming.t-p<.18;
    const rightTarget=right??(catching?upcoming!.R:null);
    const leftTarget=left??(catching?upcoming!.L:null);
    const rightWant=right?1:rightTarget?.length?0.34:0;
    const leftWant=left?1:leftTarget?.length?0.34:0;
    const smoothGrip=(w:number,want:number)=>THREE.MathUtils.damp(w,want,want>w?25:20,dt);
    this.dragonGripW.right=smoothGrip(this.dragonGripW.right,rightWant);
    this.dragonGripW.left=smoothGrip(this.dragonGripW.left,leftWant);
    if(rightTarget)this.dragonGripHeld.right=rightTarget;
    if(leftTarget)this.dragonGripHeld.left=leftTarget;
    if(this.dragonGripW.right<.015&&!rightTarget)this.dragonGripHeld.right=null;
    if(this.dragonGripW.left<.015&&!leftTarget)this.dragonGripHeld.left=null;
    const holdR=right!==null,holdL=left!==null;
    this.dragonHolder=holdR&&holdL?"BOTH":holdR?"RIGHT":holdL?"LEFT":"FREE";
    this.dragonHands.right=right;this.dragonHands.left=left;
    this.dragonAnchor=null; // independent hierarchy; neither hand is its permanent parent.

    // Strike poses stay shared; rod/chain configuration and socket timelines vary by mode.
    const b=DRAGON_STAFF_ROTATIONS[pose]??DRAGON_STAFF_ROTATIONS.idle;
    const spin=show?phase*Math.PI*1.8:key==="c"?p*Math.PI*8:
      key==="z"?p*Math.PI*6:key==="v"?p*Math.PI*8:
      key==="l3"||key==="l4"?p*Math.PI*2.4:key==="idle"?Math.sin(this.t*1.5)*.35:p*.85;
    this.dragonTargetQ.setFromEuler(this.dragonTmpEuler.set(b[0],b[1],b[2],"YXZ"));
    this.dragonSpinQ.setFromAxisAngle(this.dragonAxisZ,spin);
    this.dragonTargetQ.multiply(this.dragonSpinQ);
    const palm=right||left||"middle:mid";
    // Every F transition gets a brief 0.25-second visual wrist flourish.
    const flourish=Math.sin(modeBlend*PI)*.65*(1-modeBlend);
    this.dragonSpinQ.setFromAxisAngle(this.dragonAxisY,
      (DRAGON_SOCKET_PALM[palm]??0)+Math.sin(spin*.5)*.22+flourish);
    this.dragonTargetQ.multiply(this.dragonSpinQ);
    root.quaternion.slerp(this.dragonTargetQ,1-Math.exp(-18*Math.min(dt,.05)));

    // Mode shape: STAFF taut, SPLIT two outward rods, WHIP trailing, FOLDED Z-fold.
    const impact=pose.endsWith("_s")&&p>.75;
    for(let i=0;i<2;i++){
      const hinge=this.dragonHinges[i],rod=this.dragonRods[i];
      if(!hinge||!rod)continue;
      const sign=i===0?1:-1;
      const shape=(m:number)=>m===0?0:m===1?sign*1.18:m===2?sign*(.65+.4*Math.sin(this.t*5+i)):sign*2.60;
      const oldZ=shape(this.dragonPreviousMode),newZ=shape(mode);
      let targetZ=THREE.MathUtils.lerp(oldZ,newZ,modeBlend);
      if(mode===0&&impact)targetZ=0;
      if(mode===1&&impact)targetZ*=.35;
      if(mode===2)targetZ+=sign*.28*Math.sin(this.t*6+spin*.7+i);
      const oldX=this.dragonPreviousMode===2?sign*.39:this.dragonPreviousMode===3?sign*.1:0;
      const newX=mode===2?sign*.39:mode===3?sign*.1:mode===1?sign*.18:0;
      const targetX=THREE.MathUtils.lerp(oldX,newX,modeBlend)+
        (mode===0?0:.09*Math.sin(spin+this.t*2+i));
      hinge.rotation.z=this.dragonSpring(hinge.rotation.z,targetZ,i*3,dt);
      hinge.rotation.x=this.dragonSpring(hinge.rotation.x,targetX,i*3+1,dt);
      hinge.rotation.y=this.dragonSpring(hinge.rotation.y,mode===3?0:.09*Math.sin(this.t*4+i),i*3+2,dt);
      rod.rotation.z=THREE.MathUtils.damp(rod.rotation.z,mode===3?-sign*.22:0,15,dt);
      rod.rotation.x=THREE.MathUtils.damp(rod.rotation.x,mode===2?.12*Math.sin(this.t*4+i):0,14,dt);
      const links=this.dragonChains[i];
      for(let k=0;k<links.length;k++){
        const link=links[k];
        const bend=(mode===0&&impact)?0:.12*Math.sin(this.t*7+i*.8+k*.65)+targetZ*.045;
        link.rotation.z=THREE.MathUtils.damp(link.rotation.z,sign*bend,20,dt);
        link.rotation.x=THREE.MathUtils.damp(link.rotation.x,bend*.45,20,dt);
      }
    }

    // Follow the holder's socket via world-to-model translation, never reparent to a hand.
    // Transfers preserve world-space position and converge in ~0.08s instead of popping.
    this.updateMatrixWorld(true);
    const holderName=right||left;
    const holderHand=right?this.hand_r:this.hand_l;
    if(holderName&&this.dragonSockets[holderName]){
      holderHand.getWorldPosition(this.dragonHandWorld);
      this.dragonSockets[holderName].getWorldPosition(this.dragonSocketWorld);
      this.worldToLocal(this.dragonHandWorld);
      this.worldToLocal(this.dragonSocketWorld);
      const alpha=1-Math.exp(-Math.min(dt,.05)/.075);
      root.position.addScaledVector(this.dragonHandWorld.sub(this.dragonSocketWorld),alpha);
    }else if(!show){
      root.position.y+=Math.sin(this.t*5)*dt*.015; // brief real release, no teleport.
    }
    this.gripL=this.dragonGripHeld.left?this.dragonSockets[this.dragonGripHeld.left]:null;
    const gripR=this.dragonGripHeld.right?this.dragonSockets[this.dragonGripHeld.right]:null;
    this.bladeTip=this.dragonSockets[mode===1||key==="l2"?"lower:far":"upper:far"];
    this.bladeBase=this.dragonSockets["middle:high"];
    this.castPoint=this.bladeTip;
    if(this.vrmRig){
      this.vrmRig.gripL=this.gripL;
      this.vrmRig.gripR=gripR;
      this.vrmRig.tristaffAnchor=null;
      this.vrmRig.tristaffGripWeight.left=this.dragonGripW.left;
      this.vrmRig.tristaffGripWeight.right=this.dragonGripW.right;
      this.vrmRig.grip.left=this.dragonGripW.left>.4;
      this.vrmRig.grip.right=this.dragonGripW.right>.4;
    }
    // Whole-hierarchy cosmetic toss; receiver starts reaching before the catch at 6.24s.
    if(toss&&this.dragonGhost){
      if(!this.dragonWasTossed){
        this.updateMatrixWorld(true);
        root.getWorldPosition(this.dragonTmpV);
        this.dragonThrowStart.copy(this.worldToLocal(this.dragonTmpV));
        root.getWorldQuaternion(this.dragonTmpQ);
        this.getWorldQuaternion(this.dragonThrowQuat).invert();
        this.dragonThrowQuat.multiply(this.dragonTmpQ);
        this.dragonWasTossed=true;
      }
      const u=(phase-4.52)/1.72;
      root.visible=false;
      this.dragonGhost.visible=true;
      this.dragonGhost.position.copy(this.dragonThrowStart);
      this.dragonGhost.position.y+=Math.sin(u*PI)*.86;
      this.dragonGhost.quaternion.copy(this.dragonThrowQuat);
      this.dragonSpinQ.setFromAxisAngle(this.dragonAxisZ,u*PI*6);
      this.dragonGhost.quaternion.multiply(this.dragonSpinQ);
      for(let i=0;i<2;i++){
        const name=i===0?"upper":"lower";
        this.dragonGhost.getObjectByName(`zephyrChainJoint_${name}`)?.quaternion.copy(this.dragonHinges[i].quaternion);
        this.dragonGhost.getObjectByName(`zephyrRod_${name}`)?.quaternion.copy(this.dragonRods[i].quaternion);
        for(let k=0;k<4;k++)this.dragonGhost.getObjectByName(`zephyrChain_${name}_${k}`)?.quaternion.copy(this.dragonChains[i][k].quaternion);
      }
    }else{
      root.visible=true;
      if(this.dragonGhost)this.dragonGhost.visible=false;
      this.dragonWasTossed=false;
    }
  }

'''


def upgrade_dragon_modes():
    f='src/game/fighter.ts'
    tuning='''// ZEPHYR_DRAGON_MODE_V18 — all combat-mode numbers in one editable table.
// Mode order: STAFF, SPLIT, WHIP, FOLDED. Set every entry to 1 to disable bonuses.
export const DRAGON_MODE_TUNING = [\n'''
    names=('STAFF','SPLIT','WHIP','FOLDED')
    for name, row in zip(names,DRAGON_MODE_TUNING):
        tuning += '  { '+', '.join(f'{k}: {v:.2f}' for k,v in row.items())+' }, // '+name+'\n'
    tuning += '''] as const;
function applyDragonMode(attack: Attack, mode: number, fixedSkill: boolean): Attack {
  const m=DRAGON_MODE_TUNING[Math.max(0,Math.min(3,mode))];
  const result={...attack, reach: attack.reach*m.reach, guard: attack.guard*m.guard};
  // Z/X/C/V keep their original pulse counts and temporal hit schedule.
  if (!fixedSkill) { result.wind*=m.wind; result.recover*=m.recover; }
  if (attack.style==="zephyr_reversal") result.duration*=m.counter;
  return result;
}
\n'''
    patch(f,'export enum S {',tuning+'export enum S {')
    patch(f,'  dragonRhythm = 0;', '''  // ZEPHYR_DRAGON_MODE_V18: host-owned stance shared via F and snapshots.
  dragonMode = 0; // 0 STAFF, 1 SPLIT, 2 WHIP, 3 FOLDED
  dragonModeCd = 0;
  dragonRhythm = 0;''')
    patch(f,'    this.dragonRhythmT = Math.max(0, this.dragonRhythmT - dt);',
          '    this.dragonModeCd = Math.max(0,this.dragonModeCd-dt);\n'
          '    this.dragonRhythmT = Math.max(0, this.dragonRhythmT - dt);')
    before(f,'    // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — same F input for local, host and AI.', '''    // ZEPHYR_DRAGON_MODE_V18: F shares the current Nythera input; no key remap.
    if (k === "f" && this.kit === "tristaff") {
      const forbidden=[S.HITSTUN,S.STAGGER,S.KO,S.WIN,S.KNOCKDOWN,S.WAKEUP];
      const safeAttack=this.state!==S.ATTACK || this.atkPhase===2;
      if(this.dragonModeCd<=0 && safeAttack && !forbidden.includes(this.state) &&
          !this.chainBoundBy && !this.status.has("freeze")) {
        this.dragonMode=(this.dragonMode+1)%4;
        this.dragonModeCd=.6;
        this.model.dragonMode=this.dragonMode;
        this.model.dragonModeBlend=0;
        this.model.flash(["#bcf4dc","#f4b3ac","#ffcc77","#a3c9ff"][this.dragonMode],.25);
        // No setState(): light-attack recoveries keep their combo buffers intact.
      }
      return;
    }
''')
    before(f,'    this.atkPhase = 0;\n    this.buffered = false;\n    this.comboDamageMult = 1;', '''    // ZEPHYR_DRAGON_MODE_V18: clone for this swing only. Never mutate kit attacks.
    if(this.kit==="tristaff" && this.atk)
      this.atk=applyDragonMode(this.atk,this.dragonMode,["z","x","c","v"].includes(id));
''')
    patch(f,'this.stateT - this.shieldRaise <= this.parryWindow &&',
          'this.stateT - this.shieldRaise <= this.parryWindow *\n'
          '          (this.kit==="tristaff"?DRAGON_MODE_TUNING[this.dragonMode].parry:1) &&')
    patch(f,'        (this.judgmentT > 0 ? 1.5 : 1); // Aster Judgment weakens defense; Veyr nerf unchanged',
          '        (this.judgmentT > 0 ? 1.5 : 1) *\n'
          '        (this.kit==="tristaff"?1/DRAGON_MODE_TUNING[this.dragonMode].block:1);'
          ' // Aster Judgment weakens defense; Veyr nerf unchanged')
    patch(f,'      this.passiveEmberPatches, this.dragonRhythm, +this.dragonRhythmT.toFixed(2)];',
          '      this.passiveEmberPatches, this.dragonRhythm, +this.dragonRhythmT.toFixed(2), this.dragonMode];')
    patch(f,'    this.dragonRhythmT = s.length > 84 ? s[84] : 0;',
          '    this.dragonRhythmT = s.length > 84 ? s[84] : 0;\n'
          '    this.dragonMode = s.length > 85 ? Math.max(0,Math.min(3,s[85])) : 0;\n'
          '    this.model.dragonMode=this.dragonMode;')
    patch(f,'    this.model.dragonPose = this.kit === "tristaff" ? (this.state === S.WIN ? "show_tristaff" : this.poseName) : "idle";',
          '    this.model.dragonMode=this.dragonMode;\n'
          '    this.model.dragonPose = this.kit === "tristaff" ? (this.state === S.WIN ? "show_tristaff" : this.poseName) : "idle";',2)

    f='src/game/model.ts'
    before(f,'const DRAGON_STAFF_ROTATIONS: Record<string,[number,number,number]> = {', GRIP_TIMELINES_SOURCE+'\n')
    patch(f,'  private dragonAnchor: "left"|"right"|null = "right";', '''  private dragonAnchor: "left"|"right"|null = "right";
  // ZEPHYR_DRAGON_MODE_V18: no reparenting, smoothly weighted holder sockets.
  dragonMode = 0;
  dragonModeBlend = 1;
  private dragonLastVisualMode = 0;
  private dragonPreviousMode = 0;
  private dragonHolder: "RIGHT"|"LEFT"|"BOTH"|"FREE" = "RIGHT";
  private dragonGripW = {left:0,right:1};
  private dragonGripHeld: {left:string|null;right:string|null}={left:null,right:"middle:mid"};
  private dragonHandWorld = new THREE.Vector3();
  private dragonSocketWorld = new THREE.Vector3();''')
    patch(f,'    const root = pivot(this.hand_r);\n    root.name = "zephyrMiddleGrip";',
          '    const root = pivot(this); // ZEPHYR_DRAGON_MODE_V18 independent from hand bones\n'
          '    root.name = "zephyrMiddleGrip";')
    start='  /** Visual-only grip swaps and independent chain dynamics, keyed by existing dragonPose.'
    end='  /** ZAREK_STORM_V1: double-ended conductive glaive; meshes follow the VRM\'s hands. */'
    replace_bounded(f,start,end,DRAGON_MODEL_METHOD.rstrip()+'\n')
    # Selection uses time-driven showcase modes, no additional network data required.
    f='src/game/preview.ts'
    patch(f,'      this.model.dragonPose = who === "zephyr" ? "show_tristaff" : "idle";',
          '      this.model.dragonMode = who === "zephyr" ? Math.min(3,Math.floor((this.poseT%9)/2.25)) : 0;\n'
          '      this.model.dragonPose = who === "zephyr" ? "show_tristaff" : "idle";')

    f='src/game/vrm.ts'
    patch(f,'  tristaffAnchor: "left" | "right" | null = "right";',
          '  tristaffAnchor: "left" | "right" | null = "right";\n'
          '  // ZEPHYR_DRAGON_MODE_V18: smooth open/curl and per-arm IK influence.\n'
          '  tristaffGripWeight = {left:0,right:1};\n'
          '  private tristaffGripQ = new THREE.Quaternion();\n'
          '  private tristaffGripBaseQ = new THREE.Quaternion();\n'
          '  private tristaffWristParentQ = new THREE.Quaternion();\n'
          '  private tristaffWristLocalQ = new THREE.Quaternion();\n'
          '  private tristaffWristEuler = new THREE.Euler(0,0,0,"YXZ");')
    rig='''  // ZEPHYR_DRAGON_MODE_V18: both arms follow independent sockets using the
  // same two-bone IK. IK weight blends against the already posed arm, not a hard snap.
  private tristaffHands(setNow: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const root=this.j.root;
    root.updateMatrixWorld(true);
    const drive=(side:"left"|"right",grip:THREE.Object3D|null)=>{
      const w=THREE.MathUtils.clamp(this.tristaffGripWeight[side],0,1);
      if(!grip||w<.01)return;
      const goal=root.worldToLocal(grip.getWorldPosition(_v));
      const pole=side==="left"?_v2.set(.78,-.62,-.30):_v2.set(-.78,-.62,-.30);
      this.solveArm(side,goal,pole,(bone,quat)=>{
        if(!bone)return;
        this.tristaffGripQ.copy(quatIn(root,bone,this.tristaffGripBaseQ)).slerp(quat,w);
        // Never exceed ~100 degrees of local wrist twist relative to the forearm.
        if(this.nameOf.get(bone)?.endsWith("Hand") && bone.parent){
          const parentQ=quatIn(root,bone.parent,this.tristaffWristParentQ);
          const local=this.tristaffWristLocalQ.copy(parentQ).invert().multiply(this.tristaffGripQ);
          const e=this.tristaffWristEuler.setFromQuaternion(local,"YXZ");
          e.x=THREE.MathUtils.clamp(e.x,-1.745,1.745);
          e.y=THREE.MathUtils.clamp(e.y,-1.745,1.745);
          e.z=THREE.MathUtils.clamp(e.z,-1.745,1.745);
          this.tristaffGripQ.copy(parentQ).multiply(local.setFromEuler(e));
        }
        setNow(bone,this.tristaffGripQ);
      });
    };
    drive("left",this.gripL);
    drive("right",this.gripR);
  }

'''
    replace_bounded(f,'  // SANJIEKUN_VISUAL_V17: the weapon is anchored on one VRM hand',
                    '  private zenithSpearHands(setNow:',rig)
    # Fingers: float grip amount, preserving non-Zephyr weapon states.
    patch(f,'      const g = this.grip[side];',
          '      const g = this.tristaff ? this.tristaffGripWeight[side] : (this.grip[side] ? 1 : 0);')
    patch(f,'        const base = g ? [D(72), D(85), D(55)][si] : [D(18), D(30), D(22)][si];\n'
            '        const fan = g ? 0 : fi * D(4) + Math.sin(t * 1.3 + fi) * D(2);',
          '        const base = [D(18),D(30),D(22)][si]*(1-g)+[D(72),D(85),D(55)][si]*g;\n'
          '        const fan = (1-g)*(fi*D(4)+Math.sin(t*1.3+fi)*D(2));')
    patch(f,'      setLocal(B(`${side}ThumbProximal` as VRMHumanBoneName), 0, sgn * (g ? D(35) : D(15)), -sgn * (g ? D(25) : D(8)));\n'
            '      setLocal(B(`${side}ThumbDistal` as VRMHumanBoneName), 0, sgn * (g ? D(30) : D(10)), 0);',
          '      setLocal(B(`${side}ThumbProximal` as VRMHumanBoneName),0,sgn*(D(15)+g*D(20)),-sgn*(D(8)+g*D(17)));\n'
          '      setLocal(B(`${side}ThumbDistal` as VRMHumanBoneName),0,sgn*(D(10)+g*D(20)),0);')

    f='src/game/ai.ts'
    patch(f,'export class AiBrain implements Brain {',
          'export class AiBrain implements Brain {\n'
          '  // ZEPHYR_DRAGON_MODE_V18: mode changes spaced out, no flicker.\n'
          '  private zephyrModeCooldown=0;')
    before(f,'  think(f: Fighter, dt: number) {', '''  private zephyrModePlan(f:Fighter,o:Fighter):boolean {
    if(f.kit!=="tristaff"||this.zephyrModeCooldown>0||f.dragonModeCd>0||
       f.state!==S.IDLE||f.intent.skill||f.intent.block||f.intent.attack)return false;
    const gap=f.root.position.distanceTo(o.root.position);
    // Opponent telegraphs a close attack: fold for the strongest counter.
    const danger=gap<1.45 && o.state===S.ATTACK && o.atkPhase===0;
    const desired=gap>3.0?2:gap>1.75?0:danger?3:1;
    if(desired===f.dragonMode)return false;
    f.intent.skill="f"; // same input as a human, real 0.6s Fighter cooldown.
    this.zephyrModeCooldown=1.10;
    return true;
  }
''')
    patch(f,'  think(f: Fighter, dt: number) {',
          '  think(f: Fighter, dt: number) {\n'
          '    this.zephyrModeCooldown=Math.max(0,this.zephyrModeCooldown-dt);')
    patch(f,'    if (this.antiZenithDuel(f, o)) return;',
          '    if (this.antiZenithDuel(f, o)) return;\n'
          '    if (this.zephyrModePlan(f,o)) return;')

    f='src/ui/GameView.tsx'
    patch(f,'{` DRAGON RHYTHM ${(me as any).dragonRhythm ?? 0}/3`}',
          '{` DRAGON RHYTHM ${(me as any).dragonRhythm ?? 0}/3  ·  MODE: ${["STAFF","SPLIT","WHIP","FOLDED"][(me as any).dragonMode ?? 0]}`}' )
    f='src/game/game.ts'
    patch(f,'passives.push({ label: "RHYTHM", value: `${f.dragonRhythm}/3 · ${f.dragonRhythmT.toFixed(1)}s` });',
          'passives.push({ label: "RHYTHM", value: `${f.dragonRhythm}/3 · ${f.dragonRhythmT.toFixed(1)}s · ${["STAFF","SPLIT","WHIP","FOLDED"][f.dragonMode]}` });')


def main() -> int:
    if len(sys.argv)>2:
        print('Usage: python install_zephyr_dragon_dancer.py [web folder]',file=sys.stderr);return 1
    if len(sys.argv)==2:
        choices=[pathlib.Path(sys.argv[1]).expanduser().resolve()]
    else:
        here=pathlib.Path(__file__).resolve().parent
        choices=[pathlib.Path.cwd(),here,pathlib.Path.cwd()/'web',here/'web']
    base=next((p for p in choices if (p/'src/game/fighter.ts').is_file()),choices[0])
    required=['src/game/roster.ts','src/game/kits.ts','src/game/model.ts','src/game/fighter.ts',
              'src/game/game.ts','src/game/ai.ts','src/game/preview.ts','src/game/presentation.ts',
              'src/game/vrm.ts','src/ui/GameView.tsx']
    print('ZEPHYR DRAGON DANCER V18: 4 MODES, 9-SOCKET GRIP + KAIZEN FIX | target:',base)
    try:
        for rel in required:
            if not (base/rel).is_file():raise RuntimeError(f'Missing {rel}')
        for rel in required:changes[rel]=(base/rel).read_text(encoding='utf-8-sig')
        if MODE_MARK in changes['src/game/model.ts']:
            raise RuntimeError('Zephyr V18 already installed. Refusing repeat installation.')
        installed='id: "zephyr"' in changes['src/game/roster.ts']
        has_v17=VISUAL_MARK in changes['src/game/model.ts']
        if not has_v17:
            if installed:
                for rel in ['src/game/model.ts','src/game/kits.ts','src/game/presentation.ts']:
                    if MARK not in changes[rel]:raise RuntimeError(f'Missing V16 Zephyr code in {rel}')
            else:
                if not (base/'public/models/garrick.vrm').is_file():
                    raise RuntimeError('Missing public/models/garrick.vrm for Zephyr preview')
                migration=base/'supabase/migrations/20261108220000_add_zephyr_dragon_dancer.sql'
                if migration.exists():raise RuntimeError('Zephyr migration exists but roster missing. Check your project first.')
                add_roster();add_kits();add_fighter();add_game();add_ai();add_model();add_preview();add_hud()
            upgrade_zephyr_visuals()
            remove_kaizen_block_recoil()
        elif 'KAIZEN_BLOCK_NO_RECOIL_V17' not in changes['src/game/fighter.ts']:
            raise RuntimeError('V17 visuals exist but Kaizen fix missing; refusing incompatible upgrade.')
        # F is a shared special action already dispatched as skill="f" by input.ts.
        # Verify when source is present; do not override custom bindings.
        inp=base/'src/game/input.ts'
        if inp.exists():
            content=inp.read_text(encoding='utf-8-sig')
            if 'KeyF' not in content or 'this.skills.push("f")' not in content:
                raise RuntimeError('F binding differs from expected input.ts; no files written. Upload input.ts for adaptation.')
        upgrade_dragon_modes()
        touched=[rel for rel in required if changes[rel]!=(base/rel).read_text(encoding='utf-8-sig')]
        if not touched:raise RuntimeError('No changes generated')
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup=base/'.zephyr-backups'/(stamp+'-v18')
        for rel in touched:
            (backup/rel).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(base/rel,backup/rel)
        try:
            for rel in touched:
                (base/rel).write_text(changes[rel],encoding='utf-8')
                print(' updated',rel)
            if not installed:make_sql(base,backup)
        except Exception:
            for rel in touched:shutil.copy2(backup/rel,base/rel)
            raise
        print('Installed V18. Modes: STAFF / SPLIT / WHIP / FOLDED (F, 0.6s cooldown).')
        print('Backups:',backup)
        print('Check: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as e:
        print('ERROR:',e,file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
