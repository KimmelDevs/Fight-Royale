#!/usr/bin/env python3
"""ZEPHYR V21 — visible full-body choreography, genuine end-rod handoffs, neutral F switching.

  python install_zephyr_v21_body_grip_fix.py
  python install_zephyr_v21_body_grip_fix.py "C:\\path\\to\\fight-royale\\web"

Upgrade ONLY after install_zephyr_v20_switch_split.py. Validates every anchor in memory
before writing. Timestamped backups. No network, combat, database or git changes.

DEBUG: src/game/model.ts -> const ZEPHYR_GRIP_DEBUG = true;
BODY: src/game/vrm.ts -> const ZEPHYR_BODY_TUNING = {...};
GRIPS: src/game/model.ts -> GRIP_TIMELINE[move][mode].
"""
from __future__ import annotations
import datetime
import pathlib
import shutil
import sys

MARK='ZEPHYR_BODY_GRIP_V21'
files=('src/game/model.ts','src/game/vrm.ts','src/game/fighter.ts','src/game/game.ts')

TIMELINE = '// ZEPHYR_BODY_GRIP_V21 — AUTHORITATIVE timelines; the old V19 variant\n// overrides have been replaced, so they cannot silently force middle-rod grips.\n// 0=STAFF, 1=SPLIT, 2=WHIP, 3=FOLDED. All times are 0..1 of dragonProgress.\ntype DragonGripEvent = { t: number; R: string | null; L: string | null };\nconst GRIP_TIMELINE: Record<string, DragonGripEvent[][]> = {\n  idle: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  l1: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  l2: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  l3: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  l4: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  l5: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  heavy: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  z: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  x: [\n    [ {t:0,R:"middle:mid",L:"upper:near"}, {t:0.46,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.48,R:"upper:far",L:"lower:near"}, {t:0.82,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.55,R:"lower:mid",L:null}, {t:0.85,R:"upper:near",L:null} ],\n    [ {t:0,R:"upper:near",L:null}, {t:0.45,R:"lower:near",L:null}, {t:0.84,R:"upper:near",L:null} ]\n  ],\n  c: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  v: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  switch: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  split_r: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:far",L:"lower:near"}, {t:0.2,R:null,L:"lower:mid"}, {t:0.46,R:"upper:mid",L:"lower:mid"}, {t:0.69,R:"upper:far",L:null}, {t:0.85,R:"upper:far",L:"lower:near"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  split_l: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:near",L:"lower:far"}, {t:0.18,R:"upper:mid",L:"lower:far"}, {t:0.42,R:"upper:mid",L:null}, {t:0.63,R:"upper:far",L:"lower:mid"}, {t:0.83,R:"upper:near",L:"lower:far"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n  show_tristaff: [\n    [ {t:0,R:"middle:mid",L:"middle:low"}, {t:0.22,R:"upper:near",L:"middle:low"}, {t:0.39,R:null,L:"upper:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.75,R:"upper:near",L:"lower:near"}, {t:0.9,R:"middle:high",L:"lower:near"} ],\n    [ {t:0,R:"upper:mid",L:"lower:mid"}, {t:0.23,R:null,L:"lower:near"}, {t:0.43,R:"upper:far",L:"lower:near"}, {t:0.57,R:"upper:mid",L:null}, {t:0.77,R:"upper:near",L:"lower:far"}, {t:0.92,R:"upper:mid",L:"lower:mid"} ],\n    [ {t:0,R:"lower:near",L:null}, {t:0.22,R:"lower:mid",L:null}, {t:0.38,R:null,L:"upper:near"}, {t:0.57,R:"upper:far",L:null}, {t:0.73,R:null,L:"lower:mid"}, {t:0.88,R:"upper:near",L:null} ],\n    [ {t:0,R:"middle:mid",L:null}, {t:0.19,R:"upper:near",L:null}, {t:0.37,R:null,L:"lower:near"}, {t:0.57,R:"lower:mid",L:null}, {t:0.74,R:null,L:"upper:near"}, {t:0.9,R:"middle:mid",L:null} ]\n  ],\n};\n// Do not restore the obsolete DRAGON_VARIANT_GRIPS map; V21\'s source of truth\n// for every attack variant is GRIP_TIMELINE[move][mode].\n\n'
BODY_TUNING = "// ZEPHYR_BODY_GRIP_V21 — edit these values to adjust Zephyr's FINAL VRM body layer.\n// Radians for rotations, metres for steps/drops. No combat state is changed.\nconst ZEPHYR_BODY_TUNING = {\n  torsoYaw: .42,       // chest winds against the hips during crossing cuts\n  chestLead: .19,      // upperChest follows the weapon first\n  hipYaw: .23,         // hips rotate later, counter-balancing the shoulders\n  hipLag: 9.0,         // lower = more inertia on the pelvis\n  spineLag: 15.0,      // spring-like torso follow-through\n  torsoPitch: .13,     // anticipation lean on windup, drive on contact\n  torsoRoll: .10,      // weight into the striking side\n  hipSway: .080,       // visible lateral weight transfer (metres)\n  hipDrop: .072,       // body lowers during windup (metres)\n  kneeBend: .32,       // additional knee load on attacks (radians)\n  footStep: .30,       // alternating leg swing for advancing strikes (radians)\n  footPivot: .25,      // spin/wheel pivot angle\n  footIKOverride: .65, // 0 = old foot leveling; 1 = stronger artistic pivots\n  headTilt: .14,       // glance into the weapon's leading hand\n  angularInfluence: .13,\n  idleBodyWeight: .22, // quiet breathing/idle figure-eight\n} as const;\n"
BODY_FIELDS = '  // ZEPHYR_BODY_GRIP_V21: inputs are derived from the already synced pose/mode.\n  tristaffBodyPose = "idle";\n  tristaffBodyProgress = 0;\n  tristaffBodyMode = 0;\n  tristaffStrikeHand: "r"|"l"|"" = "";\n  tristaffAngularVelocity = 0;\n  private zephyrChestYaw = 0;\n  private zephyrHipYaw = 0;\n  private zephyrBodyQ = new THREE.Quaternion();\n  private zephyrBodyE = new THREE.Euler(0,0,0,"YXZ");\n'
BODY_METHOD = '  /** ZEPHYR_BODY_GRIP_V21: FINAL additive layer applied AFTER base limb/foot smoothing\n   * and BEFORE weapon hand IK. Runs after locomotion and pose-table layers, then the\n   * solved hands and hair/spring physics see the resulting transformed skeleton. */\n  private applyZephyrBody(dt: number, m: MotionInfo) {\n    const H=this.vrm.humanoid;\n    const get=(name:VRMHumanBoneName)=>H.getNormalizedBoneNode(name);\n    const p=THREE.MathUtils.clamp(this.tristaffBodyProgress,0,1);\n    const name=this.tristaffBodyPose;\n    const showcase=name==="show_tristaff";\n    const attack=showcase||/^zd/.test(name)||this.tristaffStrikeHand!=="";\n    const wheel=/zd4|zdz|zdc|zdv/.test(name)||showcase;\n    const wind=name.endsWith("_w")||/zd[hx]_w/.test(name);\n    const sign=this.tristaffStrikeHand==="l"?-1:this.tristaffStrikeHand==="r"?1:\n      /zd2|zd4/.test(name)?-1:1;\n    // Attack peaks across the strike; windups preload the hips and knees.\n    const attackEnvelope=attack?(0.38+0.62*Math.sin(Math.PI*Math.max(.04,p))):0;\n    const idleEnvelope=attack?0:ZEPHYR_BODY_TUNING.idleBodyWeight;\n    const energy=attackEnvelope+idleEnvelope;\n    const pulse=wind?-0.65:1;\n    const spin=wheel?Math.sin(p*Math.PI*2*(name==="zdc_s"?2:1)):0;\n    const angular=THREE.MathUtils.clamp(this.tristaffAngularVelocity,-5,5)*ZEPHYR_BODY_TUNING.angularInfluence;\n    const goalYaw=sign*ZEPHYR_BODY_TUNING.torsoYaw*energy*pulse+spin*.16+angular*.08;\n    const goalHip=-sign*ZEPHYR_BODY_TUNING.hipYaw*energy*pulse+spin*.12;\n    this.zephyrChestYaw=THREE.MathUtils.damp(this.zephyrChestYaw,goalYaw,ZEPHYR_BODY_TUNING.spineLag,dt);\n    this.zephyrHipYaw=THREE.MathUtils.damp(this.zephyrHipYaw,goalHip,ZEPHYR_BODY_TUNING.hipLag,dt);\n    const add=(name:VRMHumanBoneName,x:number,y:number,z:number)=>{\n      const b=get(name);if(!b)return;\n      b.quaternion.multiply(this.zephyrBodyQ.setFromEuler(this.zephyrBodyE.set(x,y,z,"YXZ")));\n      b.updateMatrixWorld(true);\n    };\n    const bend=energy*ZEPHYR_BODY_TUNING.kneeBend*(wind?1.25:.72);\n    add("spine",ZEPHYR_BODY_TUNING.torsoPitch*energy*(wind?-1:0.45),this.zephyrChestYaw*.52,\n      sign*ZEPHYR_BODY_TUNING.torsoRoll*energy);\n    add("chest",0,this.zephyrChestYaw*.37,-sign*.045*energy);\n    add("upperChest",0,this.zephyrChestYaw*.27,-sign*ZEPHYR_BODY_TUNING.chestLead*energy);\n    add("head",-.035*energy,-sign*.055*energy,sign*ZEPHYR_BODY_TUNING.headTilt*energy);\n    const hips=get("hips");\n    if(hips){\n      hips.position.x+=sign*ZEPHYR_BODY_TUNING.hipSway*energy/this.scale;\n      hips.position.y-=ZEPHYR_BODY_TUNING.hipDrop*energy*(wind?1.1:.48)/this.scale;\n      add("hips",.025*energy,this.zephyrHipYaw,-sign*.05*energy);\n    }\n    // Explicit pivot/step layering AFTER regular leg rotation and foot leveling.\n    const stride=wheel?Math.sin(p*Math.PI*4)*ZEPHYR_BODY_TUNING.footStep:\n      ZEPHYR_BODY_TUNING.footStep*energy*(wind?-.45:.75);\n    const pivot=(wheel?(Math.sin(p*Math.PI*2)*1.25):sign*.36)*\n      ZEPHYR_BODY_TUNING.footPivot*energy;\n    for(const side of ["left","right"] as const){\n      const sideSign=side==="left"?1:-1;\n      const lead=sideSign*sign;\n      add(`${side}UpperLeg` as VRMHumanBoneName,lead*stride-bend*.18,lead*pivot*.18,lead*.055*energy);\n      add(`${side}LowerLeg` as VRMHumanBoneName,bend*(lead>0?.85:1.12),0,0);\n      add(`${side}Foot` as VRMHumanBoneName,\n        -lead*stride*.34*ZEPHYR_BODY_TUNING.footIKOverride,\n        lead*pivot*ZEPHYR_BODY_TUNING.footIKOverride,\n        lead*.07*energy*ZEPHYR_BODY_TUNING.footIKOverride);\n    }\n    // Recompute the transformed bone hierarchy before the two-hand IK pass.\n    this.vrm.scene.updateMatrixWorld(true);\n  }\n\n'
DEBUG = '// ZEPHYR_BODY_GRIP_V21: set to true to diagnose holder, socket IK and catch events.\n// Logs only when a grip changes, plus one audit for every move/mode at spawn.\nconst ZEPHYR_GRIP_DEBUG = false;\nconst ZEPHYR_V21_MODES = ["STAFF","SPLIT","WHIP","FOLDED"] as const;\nfunction auditZephyrGrips() {\n  if(!ZEPHYR_GRIP_DEBUG) return;\n  const moves=["idle","l1","l2","l3","l4","l5","heavy","z","x","c","v","switch","split_r","split_l","show_tristaff"];\n  for(const move of moves)for(let mode=0;mode<4;mode++){\n    const timeline=GRIP_TIMELINE[move]?.[mode] ?? [];\n    const seq=timeline.map(e=>`${e.t.toFixed(2)} R:${e.R??"FREE"} L:${e.L??"FREE"}`).join(" | ");\n    console.info(`[ZEPHYR GRIP] ${move} / ${ZEPHYR_V21_MODES[mode]}: ${seq}`);\n    if(!timeline.some(e=>[e.R,e.L].some(x=>x!==null&&/^(upper|lower):/.test(x))))\n      console.warn(`[ZEPHYR GRIP] ${move}/${mode} only holds the middle rod!`);\n    if(move!=="x"&&!timeline.some(e=>e.R===null||e.L===null))\n      console.warn(`[ZEPHYR GRIP] ${move}/${mode}: no release/re-catch event!`);\n  }\n}\n'


def replace_exact(s: str, old: str, new: str, path: str, count: int=1) -> str:
    hits=s.count(old)
    if hits!=count:raise RuntimeError(f'{path}: incompatible anchor (expected {count}, found {hits}): {old[:110]!r}')
    return s.replace(old,new,count)


def replace_section(s: str, start: str, end: str, new: str, path: str) -> str:
    if s.count(start)!=1 or s.count(end)!=1:
        raise RuntimeError(f'{path}: unexpected section markers, refusing partial install')
    a=s.index(start);b=s.index(end)
    if a>=b:raise RuntimeError(f'{path}: section markers reversed')
    return s[:a]+new+s[b:]


def upgrade(changes:dict[str,str]) -> None:
    m='src/game/model.ts';r='src/game/vrm.ts';f='src/game/fighter.ts';g='src/game/game.ts'
    src=changes[m]
    # Replace old central-only grip tables AND V19 overrides. The new timelines are authoritative.
    src=replace_section(src,'type DragonGripEvent = { t:', '// Socket-palm alignment;',TIMELINE,m)
    src=replace_exact(src,'const DRAGON_STAFF_ROTATIONS: Record<string,[number,number,number]> = {',
         DEBUG+'\nconst DRAGON_STAFF_ROTATIONS: Record<string,[number,number,number]> = {',m)
    src=replace_exact(src,'  private dragonJointVel = [0,0,0,0,0,0];',
         '  private dragonJointVel = [0,0,0,0,0,0];\n'
         '  private dragonLastGripDebug = "";\n'
         '  private dragonPreviousGrip = "";\n'
         '  private dragonWasAudited = false;\n'
         '  private dragonBodyPrevQ = new THREE.Quaternion();\n'
         '  private dragonBodyVelocity = 0;\n'
         '  private dragonBodyInitialized = false;',m)
    src=replace_exact(src,'    this.dragonRoot = root;\n    const lacquer',
         '    this.dragonRoot = root;\n    if (ZEPHYR_GRIP_DEBUG && !this.dragonWasAudited) { auditZephyrGrips(); this.dragonWasAudited=true; }\n    const lacquer',m)
    src=replace_exact(src,'    const p=show?',
         '    let p=show?',m)
    src=replace_exact(src,'const timeline=DRAGON_VARIANT_GRIPS[`${mode}:${key}`] ?? GRIP_TIMELINE[key]?.[mode] ?? GRIP_TIMELINE.idle[mode];',
         'if(key==="idle"&&!show&&!inSwitch) p=((this.t*.45)%1+1)%1;\n    const timeline=GRIP_TIMELINE[key]?.[mode] ?? GRIP_TIMELINE.idle[mode];',m)
    src=replace_exact(src,'    this.dragonHands.right=right;this.dragonHands.left=left;', """    this.dragonHands.right=right;this.dragonHands.left=left;
    // Log changing sockets, not every frame; no extra state is networked.
    if (ZEPHYR_GRIP_DEBUG) {
      const logKey=`${mode}:${key}:${right}:${left}:${this.dragonHolder}`;
      if (logKey!==this.dragonLastGripDebug){
        console.info(`[ZEPHYR ${ZEPHYR_V21_MODES[mode]} ${key}] `+
          `R=${right??"FREE"} (${this.dragonGripW.right.toFixed(2)}) `+
          `L=${left??"FREE"} (${this.dragonGripW.left.toFixed(2)}) holder=${this.dragonHolder}`);
        this.dragonLastGripDebug=logKey;
      }
    }""",m)
    # Physical weapon follows actual holder hand, including transfer to outer rod.
    src=replace_exact(src,'    this.dragonTargetQ.multiply(this.dragonSpinQ);\n    root.quaternion.slerp(', """    this.dragonTargetQ.multiply(this.dragonSpinQ);
    // Release gives both chain hinges an angular impulse so the free rods swing through.
    const nextGrip=`${right??""}/${left??""}`;
    if(nextGrip!==this.dragonPreviousGrip){
      this.dragonJointVel[0]=THREE.MathUtils.clamp(this.dragonJointVel[0]+(right?.startsWith("upper") ? .35 : -.25),-3.5,3.5);
      this.dragonJointVel[3]=THREE.MathUtils.clamp(this.dragonJointVel[3]+(left?.startsWith("lower") ? -.35 : .25),-3.5,3.5);
      this.dragonPreviousGrip=nextGrip;
    }
    root.quaternion.slerp(""",m)
    # Reuse the final VrmRig IK. Avoid doubled joint spring integration.
    anchor='    this.vrmRig?.update(dt, { t: this.t, walk: this.walk, phase: this.walkPhase, crouch: this.hipsY, combat: this.combat, hurt: this.hurt, draw: this.draw, knee: this.knee, pose: actionPose });'
    src=replace_exact(src,anchor,"""    if (this.kit === "tristaff" && this.vrmRig) {
      // The normalized skeleton's body layer is applied after all regular poses and foot leveling.
      this.vrmRig.tristaffBodyPose=this.dragonModeBlend<1 ? "zdz_s" : this.dragonPose;
      this.vrmRig.tristaffBodyProgress=this.dragonPose==="show_tristaff" ? ((this.presentationT%2.25)/2.25) :
        this.dragonModeBlend<1 ? this.dragonModeBlend : this.dragonProgress;
      this.vrmRig.tristaffBodyMode=this.dragonMode;
      this.vrmRig.tristaffStrikeHand=this.dragonStrikeHand;
      if (this.dragonRoot) {
        this.dragonRoot.getWorldQuaternion(this.dragonTmpQ);
        if (this.dragonBodyInitialized) {
          const a=this.dragonBodyPrevQ.angleTo(this.dragonTmpQ);
          this.dragonBodyVelocity=THREE.MathUtils.damp(this.dragonBodyVelocity,
            Math.min(6,a/Math.max(.009,dt)),12,dt);
        } else this.dragonBodyInitialized=true;
        this.dragonBodyPrevQ.copy(this.dragonTmpQ);
      }
      this.vrmRig.tristaffAngularVelocity=this.dragonBodyVelocity;
    }
"""+anchor+"""
    if (this.kit === "tristaff") this.finishDragonGripAfterIK(dt);""",m)
    # End-of-frame correction against the actual final VRM hand instead of stale procedural hand.
    anchor='  /** ZAREK_STORM_V1: double-ended conductive glaive; meshes follow the VRM\'s hands. */'
    src=replace_exact(src,anchor,"""  // ZEPHYR_BODY_GRIP_V21: after VrmRig.update() has positioned BOTH real hands,
  // correct the detached weapon against the final hand pose instead of the previous-frame rig.
  // Blend rather than snap, and do not alter any hitbox or attack parameter.
  private finishDragonGripAfterIK(dt:number){
    const root=this.dragonRoot;
    if(!root||!this.vrmRig)return;
    const side=this.dragonHands.right?"right":this.dragonHands.left?"left":null;
    if(!side)return; // FREE toss
    const socketName=side==="right"?this.dragonHands.right:this.dragonHands.left;
    const socket=socketName?this.dragonSockets[socketName]:null;
    const hand=this.vrmRig.vrm.humanoid.getNormalizedBoneNode(side==="right"?"rightHand":"leftHand");
    if(!socket||!hand)return;
    this.updateMatrixWorld(true);
    this.worldToLocal(hand.getWorldPosition(this.dragonHandWorld));
    this.worldToLocal(socket.getWorldPosition(this.dragonSocketWorld));
    const correction=1-Math.exp(-Math.min(.05,dt)/.095);
    root.position.addScaledVector(this.dragonHandWorld.sub(this.dragonSocketWorld),correction);
    root.updateMatrixWorld(true);
  }

"""+anchor,m)
    # Refuse any silent direct-hand weapon parenting regression.
    if 'const root = pivot(this); // ZEPHYR_DRAGON_MODE_V18 independent from hand bones' not in src:
        raise RuntimeError('model.ts: Zephyr weapon is no longer independently mounted')
    changes[m]=src

    src=changes[r]
    src=replace_exact(src,'export class VrmRig {',BODY_TUNING+'\nexport class VrmRig {',r)
    src=replace_exact(src,'  tristaffGripWeight = {left:0,right:1};',
                      '  tristaffGripWeight = {left:0,right:1};\n'+BODY_FIELDS,r)
    src=replace_exact(src,'  private tristaffHands(setNow:', BODY_METHOD+'  private tristaffHands(setNow:',r)
    src=replace_exact(src,'    if (this.tristaff) this.tristaffHands(setNow);', """    if (this.tristaff) {
      this.applyZephyrBody(dt,m);  // AFTER base hips, torso, locomotion and foot IK layers.
      this.tristaffHands(setNow);  // Solve hand sockets on the newly turned skeleton.
    }""",r)
    changes[r]=src

    src=changes[f]
    src=replace_exact(src,'        this.model.flash(["#bcf4dc","#f4b3ac","#ffcc77","#a3c9ff"][this.dragonMode],.25);',
           '        // ZEPHYR_BODY_GRIP_V21: no colored mode-switch flash; physical weapon flourish only.',f)
    changes[f]=src

    src=changes[g]
    src=replace_section(src,'    const color=["#c3fff0","#ffacb8","#edc67b","#d5bcff"][mode];',
          '    if(base.dmg<=0)return;',
          '    // V21: no color-coded trails, spark bursts or flash when F is pressed.\n'
          '    // Rod pose and mode label show the stance; real melee impacts retain their normal effects.\n',g)
    src=replace_exact(src,'      this.fxp("slashes",p,color);\n      this.fxp("sparks",p,color,mode===1?10:14,3.3);\n',
          '      // Intentionally no switch-specific colored FX.\n',g)
    # No unused local p after removing colored effects.
    src=replace_exact(src,'      const p=f.model.bladeTip.getWorldPosition(new THREE.Vector3());\n      // Intentionally no switch-specific colored FX.\n',
          '      // Intentionally no switch-specific colored FX.\n',g)
    changes[g]=src


def main()->int:
    base=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '.').expanduser().resolve()
    print('ZEPHYR V21 — BODY, GRIPS, NEUTRAL SWITCH |',base)
    changes={}
    try:
        for name in files:
            path=base/name
            if not path.is_file():raise RuntimeError('Missing '+name+'; run inside the web folder')
            src=path.read_text(encoding='utf-8-sig')
            if MARK in src:raise RuntimeError('V21 already installed in '+name+'; refusing repeat installation')
            if 'ZEPHYR_DRAGON_DANCER_V1' not in src and name in ('src/game/model.ts','src/game/fighter.ts'):
                raise RuntimeError(name+': Zephyr missing. Install V20 first.')
            if name=='src/game/model.ts' and 'ZEPHYR_DRAGON_SWITCH_SPLIT_V20' not in src:
                raise RuntimeError('V20 weapon/mode patch missing in model.ts. Install V20 first.')
            changes[name]=src
        upgrade(changes) # All anchors checked BEFORE writing files.
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup=base/'.zephyr-backups'/('v21-'+stamp)
        for name in files:
            dst=backup/name;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(base/name,dst)
        for name in files:
            (base/name).write_text(changes[name],encoding='utf-8')
            print('  updated',name)
        print('\nComplete. Backup:',backup)
        print('Debug: src/game/model.ts -> ZEPHYR_GRIP_DEBUG = true')
        print('Body tuning: src/game/vrm.ts -> ZEPHYR_BODY_TUNING')
        print('Grip timing: src/game/model.ts -> GRIP_TIMELINE')
        print('Now run: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
