#!/usr/bin/env python3
"""ZEPHYR DRAGON DANCER — one-file Fight Royale installer (Python 3, no dependencies).

From the web folder: python install_zephyr_dragon_dancer.py
Or pass your web directory as the first argument.

Creates timestamped backups; checks patch anchors in memory before writing; does not push
Git changes or run the optional SQL migration. Can install alongside Nythera.
"""
from __future__ import annotations

import datetime as datetime
import pathlib
import re
import shutil
import sys

MARK = 'ZEPHYR_DRAGON_DANCER_V1'
changes: dict[str, str] = {}


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
    # Always append only after the existing snapshot fields, including Nythera if present.
    if '+this.gravityFloatT.toFixed(2)];' in changes[f]:
        patch(f, '+this.gravityFloatT.toFixed(2)];', '+this.gravityFloatT.toFixed(2), this.dragonRhythm, +this.dragonRhythmT.toFixed(2)];')
        patch(f, '    this.hp = s[8];',
              '    this.dragonRhythm = s.length > 59 ? s[59] : 0;\n'
              '    this.dragonRhythmT = s.length > 60 ? s[60] : 0;\n'
              '    this.hp = s[8];')
    else:
        patch(f, '+this.frostShieldT.toFixed(2)];', '+this.frostShieldT.toFixed(2), this.dragonRhythm, +this.dragonRhythmT.toFixed(2)];')
        patch(f, '    this.frostShieldT = s.length > 55 ? s[55] : 0;',
              '    this.frostShieldT = s.length > 55 ? s[55] : 0;\n'
              '    this.dragonRhythm = s.length > 56 ? s[56] : 0;\n'
              '    this.dragonRhythmT = s.length > 57 ? s[57] : 0;')


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
                          if 'const result = d.receiveHit(attacker, zenithAttack,' in line), None)
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
    patch(f, '    for (const fighter of [a, b]) this.awardZarekClash(fighter);', '''    for (const fighter of [a, b]) {
      this.awardZarekClash(fighter);
      if (fighter.kit === "tristaff") fighter.earnDragonRhythm();
    }''')
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
        patch(f, '    if (this.gripL && !noScytheGrip) this.reachGrip();',
              '    if (this.gripL && !noScytheGrip && !(this.kit === "tristaff" && this.dragonPose === "show_tristaff" &&\n'
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


def main() -> int:
    base=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '.').expanduser().resolve()
    required=['src/game/roster.ts','src/game/kits.ts','src/game/model.ts','src/game/fighter.ts',
              'src/game/game.ts','src/game/ai.ts','src/game/preview.ts','src/game/presentation.ts','src/ui/GameView.tsx']
    print('ZEPHYR — DRAGON DANCER | target:',base)
    try:
        for rel in required:
            p=base/rel
            if not p.is_file(): raise RuntimeError(f'Missing {rel}; run from your Fight Royale web folder')
            s=p.read_text(encoding='utf-8-sig')
            if MARK in s or 'id: "zephyr"' in s: raise RuntimeError(f'Zephyr already installed in {rel}. No files modified.')
            changes[rel]=s
        if not (base/'public/models/garrick.vrm').is_file():
            raise RuntimeError('Missing public/models/garrick.vrm for temporary male model.')
        if (base/'supabase/migrations/20261108220000_add_zephyr_dragon_dancer.sql').exists():
            raise RuntimeError('Zephyr migration already exists; no files changed.')
        add_roster();add_kits();add_fighter();add_game();add_ai();add_model();add_preview();add_hud()
        # Every patch above was checked before any destination changes were written.
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup=base/'.zephyr-backups'/stamp
        for rel in required:
            (backup/rel).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(base/rel,backup/rel)
        for rel in required:
            (base/rel).write_text(changes[rel],encoding='utf-8')
            print('  updated',rel)
        make_sql(base,backup)
        print('\nInstalled. Run: npx tsc --noEmit -p . && npm run dev')
        print('Temporary VRM: Garrick. Selection flourish: 9-second staff spins, toss and catch.')
        print('Backup folder:',backup)
        print('Database migration created but NOT applied. No automatic git operations.')
        return 0
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
