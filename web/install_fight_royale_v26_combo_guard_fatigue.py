#!/usr/bin/env python3
'''Fight Royale V26 — Zephyr + Nythera + Guard Fatigue + AI.

Install on the V25 Zephyr game. Keeps move damage, reach, base attack definitions,
AI, projectile interception, controls, F modes, and networking intact.
Adds +0.20x attack speed per active Dragon Rhythm stack (max +0.60x).
Nythera: 3 airborne cuts, Dreadfall 1.48x cap. All fighters: Guard Fatigue, reactive CPU.

Run from fight-royale/web:
    python install_fight_royale_v26_combo_guard_fatigue.py
Or supply the web folder as the first argument.

Safety: exact anchor checks in memory, seven-file timestamped backups, atomic writes,
refuses duplicate installation, no automatic Git or SQL changes.
'''
from __future__ import annotations
import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

MARK = "ZEPHYR_V26_COMBO_ANTICLIP"
MODEL_CONSTANTS = '// ZEPHYR_V26_COMBO_ANTICLIP: PURELY VISUAL. No changes to Attack, melee or networking.\n// Turn this on to see torso/head exclusion volumes, elbow/wrist points and warnings.\nconst ZEPHYR_ANTICLIP_DEBUG = false;\nconst ZEPHYR_ANTICLIP_TUNING = {\n  torsoRadius: 0.23, headRadius: 0.175, rodClearance: 0.055,\n  handMinDistance: 0.29, wristMinSide: 0.14,\n  elbowOut: 0.72, elbowDown: -0.50, wristFront: 0.22,\n  rootFront: 0.29, rootClampStep: 0.065,\n  stanceSmooth: 15, attackSmooth: 18, rodAngularLimit: 2.80,\n  debugEveryFrames: 45,\n} as const;\ntype ZephyrPoint = [number,number,number];\ntype ZephyrStance = {\n  holder: "RIGHT"|"LEFT"|"BOTH"|"FREE";\n  R: string|null; L: string|null;\n  pos: ZephyrPoint; rot: ZephyrPoint; loose: [number,number];\n};\n// The weapon root is positioned in the BODY frame (fighter faces +Z).\n// loose: desired upper/lower joint angles in radians. Tunable for each carry state.\nconst WEAPON_STANCE: ZephyrStance[][] = [\n  [ // STAFF — diagonal, forward of chest; rear grip near hip.\n    {holder:"BOTH",R:"middle:low",L:"middle:high",pos:[-.06,1.04,.39],rot:[1.12,-.25,.22],loose:[0,0]},\n    {holder:"BOTH",R:"middle:low",L:"middle:high",pos:[-.09,1.03,.41],rot:[1.24,-.21,.15],loose:[0,0]},\n    {holder:"BOTH",R:"middle:low",L:"middle:high",pos:[-.02,1.13,.43],rot:[1.32,-.05,.10],loose:[0,0]},\n    {holder:"BOTH",R:"middle:low",L:"middle:high",pos:[-.08,1.03,.50],rot:[1.02,-.19,.22],loose:[0,0]},\n  ],\n  [ // SPLIT — outer rods at hips; lower-middle rod hangs between them.\n    {holder:"BOTH",R:"upper:mid",L:"lower:mid",pos:[0,.86,.45],rot:[1.61,0,.05],loose:[1.28,-1.28]},\n    {holder:"BOTH",R:"upper:mid",L:"lower:mid",pos:[0,.82,.48],rot:[1.53,0,0],loose:[1.25,-1.25]},\n    {holder:"BOTH",R:"upper:mid",L:"lower:mid",pos:[0,1.02,.46],rot:[1.31,0,0],loose:[1.16,-1.16]},\n    {holder:"BOTH",R:"upper:mid",L:"lower:mid",pos:[0,.83,.54],rot:[1.78,0,.04],loose:[1.44,-1.44]},\n  ],\n  [ // WHIP — low side hold, two freely trailing rods.\n    {holder:"RIGHT",R:"lower:far",L:null,pos:[-.42,.84,.34],rot:[1.94,.18,-.33],loose:[-.94,1.11]},\n    {holder:"RIGHT",R:"lower:far",L:null,pos:[-.47,.77,.39],rot:[2.02,.15,-.34],loose:[-1.06,1.20]},\n    {holder:"RIGHT",R:"lower:far",L:null,pos:[-.43,.99,.38],rot:[1.68,.12,-.26],loose:[-.80,1.07]},\n    {holder:"RIGHT",R:"lower:far",L:null,pos:[-.53,.76,.50],rot:[2.14,.24,-.30],loose:[-1.25,1.33]},\n  ],\n  [ // FOLDED — three rods close together by right shoulder.\n    {holder:"RIGHT",R:"middle:mid",L:null,pos:[-.36,1.22,.36],rot:[.34,-.13,.12],loose:[2.60,-2.60]},\n    {holder:"RIGHT",R:"middle:mid",L:null,pos:[-.38,1.18,.39],rot:[.47,-.10,.12],loose:[2.55,-2.55]},\n    {holder:"RIGHT",R:"middle:mid",L:null,pos:[-.28,1.33,.40],rot:[.24,-.08,.05],loose:[2.65,-2.65]},\n    {holder:"RIGHT",R:"middle:mid",L:null,pos:[-.40,1.16,.51],rot:[.69,-.14,.13],loose:[2.68,-2.68]},\n  ],\n];\n// Idle/walk/block/charge index. Attack paths reuse their end point as the next\n// attack\'s start point, so the combo has continuous follow-through by construction.\nconst ZEPHYR_COMBO_PATH_V26: {pos:ZephyrPoint[];rot:ZephyrPoint[]}[] = [\n  {pos:[[-.27,1.11,.44],[.23,1.05,.48],[-.21,1.08,.49],[.25,1.07,.49],[-.19,1.15,.46],[.07,.92,.58],[-.22,1.41,.43],[.19,.87,.62]],\n   rot:[[1.28,-.31,-.17],[1.10,.39,.13],[1.31,-.31,-.11],[1.16,.39,.16],[1.35,-.34,-.12],[1.38,.15,.09],[.43,-.17,.14],[1.66,.26,-.11]]},\n  {pos:[[-.32,.92,.45],[.28,.92,.47],[-.29,.93,.46],[.26,.92,.49],[-.31,.98,.48],[.28,.94,.54],[-.27,1.24,.46],[.26,.91,.56]],\n   rot:[[1.72,-.23,-.35],[1.51,.32,.28],[1.77,-.27,-.25],[1.48,.28,.30],[1.71,-.26,-.30],[1.50,.24,.25],[1.29,-.23,-.09],[1.56,.27,.24]]},\n  {pos:[[-.42,.90,.42],[.36,1.02,.51],[-.36,.99,.51],[.42,1.03,.51],[-.37,1.08,.50],[.44,1.06,.55],[-.39,1.35,.50],[.32,.91,.63]],\n   rot:[[1.98,-.48,-.25],[1.66,.52,.29],[2.08,-.45,-.29],[1.73,.47,.31],[1.96,-.46,-.25],[1.66,.41,.32],[.90,-.18,-.19],[2.02,.32,.20]]},\n  {pos:[[-.33,1.17,.41],[.16,1.17,.44],[-.27,1.18,.47],[.15,1.18,.48],[-.25,1.19,.47],[.12,1.10,.54],[-.31,1.34,.48],[.22,1.12,.54]],\n   rot:[[.35,-.13,.15],[.45,.22,.23],[.37,-.22,.12],[.46,.20,.18],[.34,-.22,.14],[.39,.16,.18],[.11,-.13,.08],[.61,.23,.21]]},\n];\n// Separate grip histories for ALL 24 basic/heavy+mode cases. null means RELEASE.\n// Each l1..l5 has a different sequence. lN\'s final event equals l(N+1)\'s first.\nconst ZEPHYR_COMBO_GRIPS_V26: Record<string, DragonGripEvent[][]> = {\n  l1:[\n    [{t:0,R:"middle:low",L:"middle:high"},{t:.30,R:"upper:near",L:"middle:low"},{t:.50,R:null,L:"upper:near"},{t:.76,R:"upper:far",L:"middle:high"},{t:1,R:"upper:near",L:"middle:high"}],\n    [{t:0,R:"upper:mid",L:"lower:mid"},{t:.28,R:"upper:far",L:"lower:mid"},{t:.54,R:null,L:"lower:near"},{t:.82,R:"upper:near",L:"lower:far"},{t:1,R:"upper:near",L:"lower:far"}],\n    [{t:0,R:"lower:far",L:null},{t:.25,R:"lower:mid",L:null},{t:.49,R:null,L:"upper:near"},{t:.75,R:"lower:near",L:null},{t:1,R:"lower:near",L:null}],\n    [{t:0,R:"middle:mid",L:null},{t:.27,R:"upper:near",L:null},{t:.52,R:null,L:"lower:near"},{t:.81,R:"upper:near",L:null},{t:1,R:"upper:near",L:null}],\n  ],\n  l2:[\n    [{t:0,R:"upper:near",L:"middle:high"},{t:.27,R:null,L:"upper:mid"},{t:.56,R:"lower:near",L:"upper:far"},{t:.79,R:"lower:mid",L:"upper:mid"},{t:1,R:"lower:near",L:"upper:mid"}],\n    [{t:0,R:"upper:near",L:"lower:far"},{t:.28,R:"upper:mid",L:"lower:mid"},{t:.55,R:"upper:far",L:null},{t:.82,R:"upper:far",L:"lower:near"},{t:1,R:"upper:far",L:"lower:near"}],\n    [{t:0,R:"lower:near",L:null},{t:.27,R:null,L:"upper:mid"},{t:.53,R:"upper:near",L:"upper:far"},{t:.80,R:"upper:mid",L:null},{t:1,R:"upper:mid",L:null}],\n    [{t:0,R:"upper:near",L:null},{t:.25,R:"upper:far",L:null},{t:.50,R:null,L:"lower:near"},{t:.78,R:"middle:mid",L:null},{t:1,R:"middle:mid",L:null}],\n  ],\n  l3:[\n    [{t:0,R:"lower:near",L:"upper:mid"},{t:.27,R:"lower:far",L:null},{t:.54,R:"upper:near",L:null},{t:.79,R:"upper:near",L:"middle:mid"},{t:1,R:"upper:near",L:"middle:mid"}],\n    [{t:0,R:"upper:far",L:"lower:near"},{t:.29,R:null,L:"lower:far"},{t:.53,R:"upper:near",L:"lower:mid"},{t:.80,R:"upper:mid",L:"lower:far"},{t:1,R:"upper:mid",L:"lower:far"}],\n    [{t:0,R:"upper:mid",L:null},{t:.27,R:"upper:far",L:null},{t:.51,R:null,L:"lower:near"},{t:.79,R:"lower:mid",L:null},{t:1,R:"lower:mid",L:null}],\n    [{t:0,R:"middle:mid",L:null},{t:.28,R:"lower:near",L:null},{t:.51,R:null,L:"upper:near"},{t:.79,R:"upper:mid",L:null},{t:1,R:"upper:mid",L:null}],\n  ],\n  l4:[\n    [{t:0,R:"upper:near",L:"middle:mid"},{t:.27,R:null,L:"lower:near"},{t:.53,R:"lower:mid",L:"upper:far"},{t:.80,R:"lower:far",L:"upper:near"},{t:1,R:"lower:mid",L:"upper:near"}],\n    [{t:0,R:"upper:mid",L:"lower:far"},{t:.26,R:"upper:far",L:null},{t:.53,R:"upper:near",L:"lower:near"},{t:.78,R:"upper:far",L:"lower:mid"},{t:1,R:"upper:far",L:"lower:mid"}],\n    [{t:0,R:"lower:mid",L:null},{t:.26,R:null,L:"upper:near"},{t:.55,R:"lower:far",L:null},{t:.79,R:"lower:near",L:null},{t:1,R:"lower:near",L:null}],\n    [{t:0,R:"upper:mid",L:null},{t:.27,R:"upper:far",L:null},{t:.53,R:null,L:"lower:near"},{t:.80,R:"middle:low",L:null},{t:1,R:"middle:low",L:null}],\n  ],\n  l5:[\n    [{t:0,R:"lower:mid",L:"upper:near"},{t:.29,R:"lower:far",L:null},{t:.53,R:"middle:mid",L:"lower:near"},{t:.79,R:"upper:near",L:"lower:mid"},{t:1,R:"middle:low",L:"middle:high"}],\n    [{t:0,R:"upper:far",L:"lower:mid"},{t:.28,R:null,L:"lower:far"},{t:.52,R:"upper:mid",L:"lower:near"},{t:.79,R:"upper:far",L:"lower:far"},{t:1,R:"upper:mid",L:"lower:mid"}],\n    [{t:0,R:"lower:near",L:null},{t:.29,R:"lower:far",L:null},{t:.55,R:null,L:"upper:mid"},{t:.82,R:"lower:mid",L:null},{t:1,R:"lower:far",L:null}],\n    [{t:0,R:"middle:low",L:null},{t:.28,R:"upper:near",L:null},{t:.52,R:null,L:"lower:near"},{t:.80,R:"middle:mid",L:null},{t:1,R:"middle:mid",L:null}],\n  ],\n  heavy:[\n    [{t:0,R:"middle:low",L:"middle:high"},{t:.23,R:"upper:near",L:"middle:low"},{t:.52,R:null,L:"upper:far"},{t:.79,R:"upper:near",L:"lower:near"},{t:1,R:"middle:low",L:"middle:high"}],\n    [{t:0,R:"upper:mid",L:"lower:mid"},{t:.26,R:"upper:far",L:null},{t:.52,R:"upper:near",L:"lower:far"},{t:.80,R:null,L:"lower:near"},{t:1,R:"upper:mid",L:"lower:mid"}],\n    [{t:0,R:"lower:far",L:null},{t:.25,R:"lower:near",L:null},{t:.49,R:null,L:"upper:far"},{t:.79,R:"lower:mid",L:null},{t:1,R:"lower:far",L:null}],\n    [{t:0,R:"middle:mid",L:null},{t:.24,R:"upper:near",L:null},{t:.50,R:null,L:"lower:far"},{t:.80,R:"middle:mid",L:null},{t:1,R:"middle:mid",L:null}],\n  ],\n};\n'
RIG_CONSTANTS = "// ZEPHYR_V26_COMBO_ANTICLIP — only Zephyr's visual VRM skeleton, never combat.\nconst ZEPHYR_ARM_TUNING_V26 = {\n  torsoRadius: .22, wristClearance: .055, headRadius: .175,\n  targetFront: .24, minHands: .28, sideClear: .13,\n  elbowOut: .80, elbowDown: -.56, wristLimit: 1.55,\n  maxShoulderYaw: 1.15, clipFade: 18,\n} as const;\n// Distinct additions on top of the shared P(...) base poses; rows STAFF, SPLIT,\n// WHIP, FOLDED; columns l1..l5, heavy. Rotations in radians.\nconst ZEPHYR_COMBO_BODY_V26: {yaw:number;hip:number;step:number;lead:number;armR:number;armL:number}[][] = [\n  [\n    {yaw:.23,hip:-.10,step:.22,lead:1,armR:-.15,armL:.12},\n    {yaw:.24,hip:-.11,step:.26,lead:-1,armR:.13,armL:-.16},\n    {yaw:.29,hip:-.15,step:.26,lead:1,armR:-.21,armL:.09},\n    {yaw:.32,hip:-.14,step:.32,lead:-1,armR:.12,armL:-.18},\n    {yaw:.37,hip:-.19,step:.35,lead:1,armR:-.24,armL:.12},\n    {yaw:.35,hip:-.18,step:.31,lead:1,armR:-.19,armL:.13},\n  ],\n  [\n    {yaw:.17,hip:-.08,step:.27,lead:1,armR:-.18,armL:.17},\n    {yaw:.18,hip:-.08,step:.29,lead:-1,armR:.15,armL:-.18},\n    {yaw:.22,hip:-.10,step:.27,lead:1,armR:-.20,armL:.15},\n    {yaw:.23,hip:-.11,step:.31,lead:-1,armR:.15,armL:-.21},\n    {yaw:.29,hip:-.14,step:.33,lead:1,armR:-.23,armL:.18},\n    {yaw:.27,hip:-.13,step:.26,lead:1,armR:-.21,armL:.19},\n  ],\n  [\n    {yaw:.28,hip:-.14,step:.25,lead:1,armR:-.22,armL:.08},\n    {yaw:.30,hip:-.14,step:.29,lead:-1,armR:.15,armL:-.22},\n    {yaw:.35,hip:-.18,step:.31,lead:1,armR:-.25,armL:.10},\n    {yaw:.36,hip:-.20,step:.37,lead:-1,armR:.13,armL:-.26},\n    {yaw:.40,hip:-.22,step:.39,lead:1,armR:-.27,armL:.12},\n    {yaw:.41,hip:-.23,step:.34,lead:1,armR:-.27,armL:.08},\n  ],\n  [\n    {yaw:.15,hip:-.07,step:.18,lead:1,armR:-.11,armL:.12},\n    {yaw:.17,hip:-.08,step:.18,lead:-1,armR:.13,armL:-.12},\n    {yaw:.20,hip:-.09,step:.22,lead:1,armR:-.15,armL:.14},\n    {yaw:.21,hip:-.10,step:.24,lead:-1,armR:.12,armL:-.15},\n    {yaw:.25,hip:-.11,step:.24,lead:1,armR:-.16,armL:.15},\n    {yaw:.27,hip:-.12,step:.27,lead:1,armR:-.16,armL:.12},\n  ],\n];\n"


def exactly(src: str, old: str, new: str, target: str, expected: int = 1) -> str:
    count = src.count(old)
    if count != expected:
        raise RuntimeError(f"{target}: expected {expected} matching anchor(s), found {count}: {old[:85]!r}")
    return src.replace(old, new, expected)


def block_between(src: str, opening: str, closing: str, replacement: str, target: str) -> str:
    if src.count(opening) != 1 or src.count(closing) != 1:
        raise RuntimeError(f"{target}: missing or ambiguous V25 anchors: {opening[:65]!r} / {closing[:65]!r}")
    a = src.index(opening)
    b = src.index(closing, a + len(opening))
    if b <= a:
        raise RuntimeError(f"{target}: malformed block anchors")
    return src[:a] + replacement + "\n" + src[b:]


def patch_model(src: str) -> str:
    f = "src/game/model.ts"
    src = exactly(src, "const DRAGON_STAFF_ROTATIONS: Record<string,[number,number,number]> = {",
                  MODEL_CONSTANTS + "\nconst DRAGON_STAFF_ROTATIONS: Record<string,[number,number,number]> = {", f)
    # The game already has a grip timeline with duplicate generic l1..heavy events.
    # Override them with the V26 distinctive event histories, leaving skill timelines alone.
    src = exactly(src,
        '    const timeline=GRIP_TIMELINE[key]?.[mode] ?? GRIP_TIMELINE.idle[mode];',
        '''    const basicKey=key==="split_r"?"l1":key==="split_l"?"l2":key;
    const timeline=ZEPHYR_COMBO_GRIPS_V26[basicKey]?.[mode] ??
      GRIP_TIMELINE[key]?.[mode] ?? GRIP_TIMELINE.idle[mode];''', f)
    src = exactly(src, 'if (ZEPHYR_GRIP_DEBUG) {\n      const logKey=',
                  'if (ZEPHYR_GRIP_DEBUG || ZEPHYR_ANTICLIP_DEBUG) {\n      const logKey=', f)
    # Keep the existing skill Z/X/C/V choreography but replace basic/heavy spinning.
    opening='    // Strike poses stay shared; rod/chain configuration and socket timelines vary by mode.\n'
    closing='    // Release gives both chain hinges an angular impulse so the free rods swing through.\n'
    src=block_between(src,opening,closing, r'''    // V26: l1..l5 and heavy have separate BODY-FRAME paths per mode.
    // The last point of an attack is literally the first point of the next light.
    const comboIndex=/^l[1-5]$/.test(basicKey)?Number(basicKey[1])-1:
      basicKey==="heavy"?5:-1;
    const path=ZEPHYR_COMBO_PATH_V26[mode];
    const combo=comboIndex>=0 && !inSwitch && !show;
    const wind=pose.endsWith("_w");
    const phaseT=wind?(.05+.30*p):(.35+.65*p);
    const stage=THREE.MathUtils.smoothstep(phaseT,0,1);
    const stanceState=pose==="block"?2:pose==="charge"?3:
      this.walk>.12?1:0;
    const stance=WEAPON_STANCE[mode][stanceState];
    const fromStance=WEAPON_STANCE[this.dragonPreviousMode][stanceState];
    const tween=(a:number,b:number,t:number)=>THREE.MathUtils.lerp(a,b,t);
    // Stances interpolate across F: no teleport or rigid snap when modes change.
    const stancePos=this.dragonTmpS.set(
      tween(fromStance.pos[0],stance.pos[0],modeBlend),
      tween(fromStance.pos[1],stance.pos[1],modeBlend),
      tween(fromStance.pos[2],stance.pos[2],modeBlend));
    if(combo){
      const a=path.pos[comboIndex===5?6:comboIndex];
      const b=path.pos[comboIndex===5?7:comboIndex+1];
      stancePos.set(tween(a[0],b[0],stage),tween(a[1],b[1],stage),
        tween(a[2],b[2],stage));
    }
    // The body remains in +Z foreground; preserve room for the real hands to reach.
    const attackRate=1-Math.exp(-ZEPHYR_ANTICLIP_TUNING.attackSmooth*Math.min(dt,.05));
    root.position.lerp(stancePos,attackRate);
    const b=DRAGON_STAFF_ROTATIONS[pose]??DRAGON_STAFF_ROTATIONS.idle;
    const baseSpin=show?phase*Math.PI*1.8:key==="c"?p*Math.PI*8:
      key==="z"?p*Math.PI*6:key==="v"?p*Math.PI*8:
      combo?0:key==="idle"?Math.sin(this.t*1.5)*.24:p*.65;
    const spin=mode===1&&key==="split_r"?p*Math.PI*.38:
      mode===1&&key==="split_l"?-p*Math.PI*.38:
      mode===2&&!combo&&key!=="idle"&&!show?baseSpin*1.28:baseSpin;
    if(combo){
      const a=path.rot[comboIndex===5?6:comboIndex];
      const b=path.rot[comboIndex===5?7:comboIndex+1];
      this.dragonTmpEuler.set(tween(a[0],b[0],stage),
        tween(a[1],b[1],stage),tween(a[2],b[2],stage),"YXZ");
    }else if(key==="idle"||pose==="block"||pose==="charge"){
      this.dragonTmpEuler.set(tween(fromStance.rot[0],stance.rot[0],modeBlend),
        tween(fromStance.rot[1],stance.rot[1],modeBlend),
        tween(fromStance.rot[2],stance.rot[2],modeBlend),"YXZ");
    }else this.dragonTmpEuler.set(b[0],b[1],b[2],"YXZ");
    this.dragonTargetQ.setFromEuler(this.dragonTmpEuler);
    this.dragonSpinQ.setFromAxisAngle(this.dragonAxisZ,spin);
    this.dragonTargetQ.multiply(this.dragonSpinQ);
    const palm=right||left||"middle:mid";
    const flourish=Math.sin(modeBlend*PI)*.65*(1-modeBlend);
    this.dragonSpinQ.setFromAxisAngle(this.dragonAxisY,
      (DRAGON_SOCKET_PALM[palm]??0)+Math.sin(spin*.5)*.15+flourish);
    this.dragonTargetQ.multiply(this.dragonSpinQ);''',f)
    # Standby stance sockets replace idle middle-only rotations while keeping light attacks on V26 timeline.
    src=exactly(src,
        '    let right=current.R, left=current.L;\n    const toss=',
        '''    let right=current.R, left=current.L;
    if(key==="idle" && !show && !inSwitch && pose!=="idle"){
      const still=WEAPON_STANCE[mode][pose==="block"?2:pose==="charge"?3:0];
      right=still.R;left=still.L;
    }
    const toss=''',f)
    # Stance loose rods are actually used, no frozen pole in split/whip/folded.
    src=exactly(src,
        '      const oldZ=shape(this.dragonPreviousMode),newZ=shape(mode);',
        '''      const stanceOld=WEAPON_STANCE[this.dragonPreviousMode][stanceState];
      const stanceNew=WEAPON_STANCE[mode][stanceState];
      const oldZ=combo||key!=="idle"?shape(this.dragonPreviousMode):stanceOld.loose[i];
      const newZ=combo||key!=="idle"?shape(mode):stanceNew.loose[i];''',f)
    src=exactly(src,
        '    if(this.vrmRig){\n      this.vrmRig.gripL=this.gripL;',
        '''    if(this.vrmRig){
      this.vrmRig.tristaffDebug=ZEPHYR_ANTICLIP_DEBUG;
      this.vrmRig.gripL=this.gripL;''',f)
    # After IK, keep visible geometry outside the torso/head and render debug volumes.
    src=exactly(src,
        '    root.updateMatrixWorld(true);\n  }\n\n  /** ZAREK_STORM_V1:',
        '''    root.updateMatrixWorld(true);
    this.enforceDragonClearance(dt);
  }

  // V26: visual-only rod avoidance after VRM IK and after socket alignment.
  // Samples all three rigid rods against the hip-to-chest capsule and head sphere.
  private enforceDragonClearance(dt:number){
    const root=this.dragonRoot,vrm=this.vrmRig?.vrm;
    if(!root||!vrm)return;
    const visualBasic=/^zd[1-5]_|^zdh_|^idle$|^block$|^charge$/.test(this.dragonPose);
    if(!visualBasic)return; // special behind-the-back skills may intentionally bypass.
    const bone=(n:"hips"|"chest"|"head")=>vrm.humanoid.getNormalizedBoneNode(n);
    const hp=bone("hips"),ch=bone("chest"),hd=bone("head");
    if(!hp||!ch||!hd)return;
    this.updateMatrixWorld(true);
    this.worldToLocal(hp.getWorldPosition(this.dragonClipHip));
    this.worldToLocal(ch.getWorldPosition(this.dragonClipChest));
    this.worldToLocal(hd.getWorldPosition(this.dragonClipHead));
    this.dragonClipAxis.copy(this.dragonClipChest).sub(this.dragonClipHip);
    const d2=Math.max(.0001,this.dragonClipAxis.lengthSq());
    let correction=0,penetrations=0;
    const R=ZEPHYR_TRISTAFF_SIZE_V24.endHalfLength;
    for(let i=0;i<3;i++){
      const rod=i===0?root:this.dragonRods[i-1];if(!rod)continue;
      const low=i===0?-ZEPHYR_TRISTAFF_SIZE_V24.middleHalfLength:0;
      const high=i===0?ZEPHYR_TRISTAFF_SIZE_V24.middleHalfLength:
        (i===1?2*R:-2*R);
      for(let j=0;j<4;j++){
        this.dragonClipSample.set(0,low+(high-low)*j/3,0);
        this.worldToLocal(rod.localToWorld(this.dragonClipSample));
        const t=THREE.MathUtils.clamp(this.dragonClipCheck.copy(this.dragonClipSample)
          .sub(this.dragonClipHip).dot(this.dragonClipAxis)/d2,0,1);
        const nearest=this.dragonClipCheck.copy(this.dragonClipHip).addScaledVector(this.dragonClipAxis,t);
        const torsoDistance=this.dragonClipSample.distanceTo(nearest);
        const headDistance=this.dragonClipSample.distanceTo(this.dragonClipHead);
        const needed=Math.max(0,
          ZEPHYR_ANTICLIP_TUNING.torsoRadius+ZEPHYR_ANTICLIP_TUNING.rodClearance-torsoDistance,
          ZEPHYR_ANTICLIP_TUNING.headRadius+ZEPHYR_ANTICLIP_TUNING.rodClearance-headDistance);
        if(needed>.001){correction=Math.max(correction,needed);penetrations++;}
      }
    }
    if(correction>0){
      root.position.z+=Math.min(correction,ZEPHYR_ANTICLIP_TUNING.rootClampStep);
      // Slight yaw relief rather than an uncontrolled root rotation through the chest.
      root.rotation.y+=THREE.MathUtils.clamp(root.position.x*.04,-.026,.026);
      root.updateMatrixWorld(true);
    }
    if(ZEPHYR_ANTICLIP_DEBUG){
      this.drawDragonDebug(penetrations);
      this.dragonClipFrames++;
      if(penetrations && this.dragonClipFrames%ZEPHYR_ANTICLIP_TUNING.debugEveryFrames===0)
        console.warn(`[Zephyr V26] rod/body overlap corrected: ${penetrations} sample(s), ${this.dragonPose}, mode=${this.dragonMode}`);
    }
  }

  private drawDragonDebug(collisionCount:number){
    const vrm=this.vrmRig?.vrm;if(!vrm)return;
    if(!this.dragonClipViz){
      const g=new THREE.Group();g.name="ZEPHYR_V26_DEBUG_ONLY";
      const material=new THREE.MeshBasicMaterial({color:0x00ffee,wireframe:true,depthTest:false});
      const red=new THREE.MeshBasicMaterial({color:0xff3355,wireframe:true,depthTest:false});
      const torso=new THREE.Mesh(new THREE.CapsuleGeometry(1,1,4,8),material);
      const head=new THREE.Mesh(new THREE.SphereGeometry(1,10,7),red);
      g.add(torso,head);
      for(let i=0;i<4;i++)g.add(new THREE.Mesh(new THREE.SphereGeometry(.045,8,6),material));
      this.add(g);this.dragonClipViz=g;
    }
    const vis=this.dragonClipViz,torso=vis.children[0] as THREE.Mesh,head=vis.children[1] as THREE.Mesh;
    torso.position.copy(this.dragonClipHip).add(this.dragonClipChest).multiplyScalar(.5);
    torso.scale.set(ZEPHYR_ANTICLIP_TUNING.torsoRadius,
      Math.max(.05,this.dragonClipChest.distanceTo(this.dragonClipHip))*.5,
      ZEPHYR_ANTICLIP_TUNING.torsoRadius);
    head.position.copy(this.dragonClipHead);
    head.scale.setScalar(ZEPHYR_ANTICLIP_TUNING.headRadius);
    const names=["leftHand","rightHand","leftLowerArm","rightLowerArm"] as const;
    for(let i=0;i<names.length;i++){
      const n=vrm.humanoid.getNormalizedBoneNode(names[i]);
      if(n)this.worldToLocal(n.getWorldPosition((vis.children[i+2] as THREE.Object3D).position));
    }
    (torso.material as THREE.MeshBasicMaterial).color.setHex(collisionCount?0xff9911:0x00ffee);
  }

  /** ZAREK_STORM_V1:''',f)
    # Add cached objects to model fields (no per-frame allocations for new clearance math).
    src=exactly(src,
        '  private dragonBodyPrevQ = new THREE.Quaternion();',
        '''  private dragonClipHip = new THREE.Vector3();
  private dragonClipChest = new THREE.Vector3();
  private dragonClipHead = new THREE.Vector3();
  private dragonClipAxis = new THREE.Vector3();
  private dragonClipSample = new THREE.Vector3();
  private dragonClipCheck = new THREE.Vector3();
  private dragonClipViz: THREE.Group | null = null;
  private dragonClipFrames = 0;
  private dragonBodyPrevQ = new THREE.Quaternion();''',f)
    return src


def patch_rig(src: str) -> str:
    f = "src/game/vrm.ts"
    src=exactly(src, "export class VrmRig {", RIG_CONSTANTS+"\nexport class VrmRig {", f)
    src=exactly(src, '  tristaff = false;',
        '''  tristaff = false;
  tristaffDebug = false;
  private zephyrAimRight=new THREE.Vector3();
  private zephyrAimLeft=new THREE.Vector3();
  private zephyrTorsoMid=new THREE.Vector3();
  private zephyrHeadMid=new THREE.Vector3();
  private zephyrAimDiff=new THREE.Vector3();
  private zephyrClipFrames=0;''',f)
    # Enhanced torso and per-mode dedicated shoulder/leg path after the existing base layer.
    src=exactly(src,
        '    // Recompute the transformed bone hierarchy before the two-hand IK pass.\n    this.vrm.scene.updateMatrixWorld(true);',
        '''    // V26: mode-specific basic/heavy body poses, additive AFTER locomotion.
    // The 24 samples are deliberately unique. Skills keep their current body poses.
    const which=/^zd([1-5])_[ws]$/.exec(name);
    const heavy=/^zdh_[ws]$/.test(name);
    const index=which?Number(which[1])-1:heavy?5:-1;
    if(index>=0){
      const tune=ZEPHYR_COMBO_BODY_V26[Math.min(3,this.tristaffBodyMode)][index];
      const onset=name.endsWith("_w")?-.62:1;
      const stress=(.35+.65*Math.sin(Math.PI*Math.max(.01,p)))*onset;
      const toward=tune.lead;
      add("spine",.04*stress,tune.yaw*toward*stress,.015*stress);
      add("chest",.025*stress,tune.yaw*.43*toward*stress,0);
      add("hips",-.015*stress,tune.hip*toward*stress,0);
      add("rightShoulder",-.015*stress,0,-tune.armR*.15*stress);
      add("leftShoulder",-.015*stress,0,tune.armL*.15*stress);
      // This is arm POSE motion, not a target override; held hands are solved by IK next.
      add("rightUpperArm",tune.armR*stress,-toward*.055*stress,-.06*stress);
      add("leftUpperArm",tune.armL*stress,toward*.055*stress,.06*stress);
      add("rightUpperLeg",-tune.step*toward*.57*stress,0,-.045*stress);
      add("leftUpperLeg",tune.step*toward*.57*stress,0,.045*stress);
      add("rightFoot",tune.step*toward*.16*stress,0,0);
      add("leftFoot",-tune.step*toward*.16*stress,0,0);
    }
    // Recompute the transformed bone hierarchy before the two-hand IK pass.
    this.vrm.scene.updateMatrixWorld(true);''',f)
    # Replace Zephyr's grip IK with collision-aware wrist and elbow targets.
    opening='  private tristaffHands(setNow: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {\n'
    closing='  private zenithSpearHands(setNow: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {\n'
    new=r'''  private tristaffHands(setNow: (b: THREE.Object3D | null, q: THREE.Quaternion) => void) {
    const root=this.j.root,h=this.vrm.humanoid;
    root.updateMatrixWorld(true);
    const chest=h.getNormalizedBoneNode("chest"),hips=h.getNormalizedBoneNode("hips");
    if(chest&&hips){
      root.worldToLocal(chest.getWorldPosition(this.zephyrTorsoMid));
      root.worldToLocal(hips.getWorldPosition(this.zephyrHeadMid));
      this.zephyrTorsoMid.add(this.zephyrHeadMid).multiplyScalar(.5);
    }else this.zephyrTorsoMid.set(0,1.05,0);
    // First gather both targets, so minimum separation is independent of IK order.
    const goal=(side:"right"|"left",socket:THREE.Object3D|null,out:THREE.Vector3)=>{
      if(!socket){out.set(side==="right"?-.29:.29,1.02,.34);return;}
      root.worldToLocal(socket.getWorldPosition(out));
      const x=out.x-this.zephyrTorsoMid.x;
      const z=out.z-this.zephyrTorsoMid.z;
      const d=Math.sqrt(x*x+z*z);
      const min=ZEPHYR_ARM_TUNING_V26.torsoRadius+ZEPHYR_ARM_TUNING_V26.wristClearance;
      // Shortest outward radial correction with preference for the facing plane.
      if(d<min){
        if(d>.001){out.x=this.zephyrTorsoMid.x+x*min/d;out.z=this.zephyrTorsoMid.z+z*min/d;}
        else out.z=this.zephyrTorsoMid.z+min;
      }
      // The shoulder line stays uncrossed except intentional special move passes.
      const special=/^zd[zxcv]|show_tristaff/.test(this.tristaffBodyPose);
      if(!special){
        out.x=side==="right"?Math.min(out.x,this.zephyrTorsoMid.x-ZEPHYR_ARM_TUNING_V26.sideClear):
          Math.max(out.x,this.zephyrTorsoMid.x+ZEPHYR_ARM_TUNING_V26.sideClear);
        out.z=Math.max(out.z,this.zephyrTorsoMid.z+ZEPHYR_ARM_TUNING_V26.targetFront);
      }
    };
    goal("right",this.gripR,this.zephyrAimRight);
    goal("left",this.gripL,this.zephyrAimLeft);
    if(this.gripR&&this.gripL){
      const dist=this.zephyrAimDiff.copy(this.zephyrAimRight).sub(this.zephyrAimLeft).length();
      if(dist<ZEPHYR_ARM_TUNING_V26.minHands){
        const half=(ZEPHYR_ARM_TUNING_V26.minHands-dist)*.5;
        this.zephyrAimRight.x-=half;
        this.zephyrAimLeft.x+=half;
      }
    }
    const drive=(side:"left"|"right",grip:THREE.Object3D|null,target:THREE.Vector3)=>{
      const w=THREE.MathUtils.clamp(this.tristaffGripWeight[side],0,1);
      if(!grip||w<.01)return;
      const pole=side==="left"?_v2.set(ZEPHYR_ARM_TUNING_V26.elbowOut,
        ZEPHYR_ARM_TUNING_V26.elbowDown,-.23):
        _v2.set(-ZEPHYR_ARM_TUNING_V26.elbowOut,ZEPHYR_ARM_TUNING_V26.elbowDown,-.23);
      const apply=(bone:THREE.Object3D|null,quat:THREE.Quaternion)=>{
        if(!bone)return;
        this.tristaffGripQ.copy(quatIn(root,bone,this.tristaffGripBaseQ)).slerp(quat,w);
        // Clamp wrist and shoulder to avoid twisting into the chest.
        if(bone.parent){
          const name=this.nameOf.get(bone)??"";
          if(name.endsWith("Hand")||name.endsWith("UpperArm")){
            const parentQ=quatIn(root,bone.parent,this.tristaffWristParentQ);
            const local=this.tristaffWristLocalQ.copy(parentQ).invert().multiply(this.tristaffGripQ);
            const e=this.tristaffWristEuler.setFromQuaternion(local,"YXZ");
            const limit=name.endsWith("Hand")?ZEPHYR_ARM_TUNING_V26.wristLimit:
              ZEPHYR_ARM_TUNING_V26.maxShoulderYaw;
            e.y=THREE.MathUtils.clamp(e.y,-limit,limit);
            if(name.endsWith("Hand")){
              e.x=THREE.MathUtils.clamp(e.x,-limit,limit);
              e.z=THREE.MathUtils.clamp(e.z,-limit,limit);
            }
            this.tristaffGripQ.copy(parentQ).multiply(local.setFromEuler(e));
          }
        }
        setNow(bone,this.tristaffGripQ);
      };
      this.solveArm(side,target,pole,apply);
      // Post-IK self-check: warn if a wrist/elbow or hand pair intersects the torso.
      const wrist=h.getNormalizedBoneNode(`${side}Hand`);
      const elbow=h.getNormalizedBoneNode(`${side}LowerArm`);
      if(wrist&&elbow){
        root.worldToLocal(wrist.getWorldPosition(this.zephyrAimDiff));
        const badW=this.zephyrAimDiff.distanceTo(this.zephyrTorsoMid)<ZEPHYR_ARM_TUNING_V26.torsoRadius;
        root.worldToLocal(elbow.getWorldPosition(this.zephyrAimDiff));
        const badE=this.zephyrAimDiff.distanceTo(this.zephyrTorsoMid)<ZEPHYR_ARM_TUNING_V26.torsoRadius;
        if(badW||badE){
          target.z+=ZEPHYR_ARM_TUNING_V26.wristClearance;
          target.x+=side==="right"?-.07:.07;
          this.solveArm(side,target,pole,apply);
          if(this.tristaffDebug&&this.zephyrClipFrames%45===0)
            console.warn(`[Zephyr V26] ${side} ${badW?"wrist":"elbow"} inside torso — IK readjusted`);
        }
      }
    };
    drive("left",this.gripL,this.zephyrAimLeft);
    drive("right",this.gripR,this.zephyrAimRight);
    this.zephyrClipFrames++;
  }

'''
    src=block_between(src,opening,closing,new,f)
    return src


def patch_fighter(src: str) -> str:
    f = "src/game/fighter.ts"
    # Runtime tuning lives with the existing 25s Rhythm duration.
    src=exactly(src,
        '  rhythmSeconds: 25,\n  damageTakenMult: 0.80,',
        '  rhythmSeconds: 25,\n  attackSpeedPerStack: 0.20, // V26: +20% attack speed per active Rhythm stack, max 3.\n  damageTakenMult: 0.80,',f)
    # Apply the speed to each committed cloned attack, before the 3-stack finisher
    # consumes its stacks. Do not mutate the base Kit attacks.
    speed_hook = '''    // ZEPHYR_RHYTHM_ATTACK_SPEED_V26 — earned Rhythm accelerates basics AND skills.
    // Applied at attack commitment: gaining a stack mid-combo accelerates the next
    // attack, not an already scheduled contact. Finisher speed is calculated before
    // consuming 3 stacks. Mode bonuses still apply; cooldowns stay unchanged.
    if (this.kit === "tristaff" && this.atk) {
      const stacks = Math.max(0, Math.min(3, this.dragonRhythm));
      const speed = 1 + stacks * ZEPHYR_PASSIVE_TUNING.attackSpeedPerStack;
      this.atk = { ...this.atk,
        wind: this.atk.wind / speed,
        active: this.atk.active / speed,
        recover: this.atk.recover / speed };
    }
'''
    anchor = '    // ZEPHYR_DRAGON_DANCER_V1: spend earned rhythm on next committed finisher.'
    src=exactly(src,anchor,speed_hook+anchor,f)
    return src



# V26 game-wide speed floor is technical, not a limit on earned fatigue stacks.
# Without a floor, 50 blocked hits would make speed zero and divide-by-zero
# the attack timeline; 100+ would reverse the animation clock.
# It is safe to change these numbers, but keep minSpeed > 0.
GUARD_FATIGUE_TUNING_TS = """// GUARD_FATIGUE_V26 — affects the attacker on REAL block/parry contacts.
// Unlimited stacks; effective speed has a safety floor to avoid zero timelines.
export const GUARD_FATIGUE_TUNING = {
  speedLostPerStack: 0.02,
  decaySecondsPerStack: 3.0,
  minSpeed: 0.20,
} as const;
"""


def patch_nythera_and_fatigue_fighter(src: str) -> str:
    f='src/game/fighter.ts'
    # Insert tunables at the top of the module; preserve V25 movement and combat.
    src=exactly(src, '// ZEPHYR_DRAGON_MODE_V18 — all combat-mode numbers in one editable table.',
        '''// NYTHERA_AIR_SPEED_BALANCE_V26: only Nythera; Kira and Nyx are unchanged.
const NYTHERA_V26_TUNING = { maxAirSlices: 3, speedCap: 1.48 } as const;
''' + GUARD_FATIGUE_TUNING_TS +
        '// ZEPHYR_DRAGON_MODE_V18 — all combat-mode numbers in one editable table.', f)
    src=exactly(src,'return Math.min(1.50, 0.80 + stacks * 0.05);',
                'return Math.min(NYTHERA_V26_TUNING.speedCap, 0.80 + stacks * 0.05);',f)
    src=exactly(src,'// NYTHERA_ZENITH_LOWER_CAPS_V14: flat -0.20x speed at ALL stacks; maximum 1.50x.',
                '// NYTHERA_AIR_SPEED_BALANCE_V26: starts 0.80x, earns +0.05x per hit, caps at 1.48x.',f)
    src=exactly(src,'four graceful arcs per jump, never four auto-hits',
                'three graceful arcs per jump, never three auto-hits',f)
    src=exactly(src,'const names = ["Lunar Sweep", "Veil Reversal", "Falling Crescent", "Eclipse Petal"];',
                'const names = ["Lunar Sweep", "Veil Reversal", "Falling Crescent"];',f)
    # Last hit still gets the previously earned finisher feel but one fewer contact.
    src=exactly(src,'const damage = [34, 37, 40, 52];', 'const damage = [34, 37, 52];',f)
    src=exactly(src,'this.attacks[n === 4 ? "air_l3" : key]', 'this.attacks[key]',f)
    src=exactly(src,'Air scythe cut ${n}/4', 'Air scythe cut ${n}/3',f)
    src=exactly(src,'Four alternating two-hand scythe arcs', 'Three alternating two-hand scythe arcs',f)
    src=exactly(src,'const winds = ["gr1_w", "gr2_w", "gr3_w", "gr6_w"];',
                'const winds = ["gr1_w", "gr2_w", "gr3_w"];',f)
    src=exactly(src,'const slashes = ["gr1_s", "gr2_s", "gr3_s", "gr6_s"];',
                'const slashes = ["gr1_s", "gr2_s", "gr3_s"];',f)
    assert src.count('for (let n = 1; n <= 4; n++)') == 2
    src=src.replace('for (let n = 1; n <= 4; n++)',
        'for (let n = 1; n <= NYTHERA_V26_TUNING.maxAirSlices; n++)')
    # No other kit uses these n===4 checks.
    assert src.count('n === 4') >= 5
    src=src.replace('n === 4','n === 3')
    src=exactly(src,'this.nytheraAirSlices = Math.min(4, this.nytheraAirSlices + 1)',
        'this.nytheraAirSlices = Math.min(NYTHERA_V26_TUNING.maxAirSlices, this.nytheraAirSlices + 1)',f)
    assert src.count('this.nytheraAirSlices >= 4') == 2
    src=src.replace('this.nytheraAirSlices >= 4', 'this.nytheraAirSlices >= NYTHERA_V26_TUNING.maxAirSlices')
    assert src.count('this.nytheraAirSlices < 4') == 2
    src=src.replace('this.nytheraAirSlices < 4', 'this.nytheraAirSlices < NYTHERA_V26_TUNING.maxAirSlices')
    assert src.count('/^air_l[1-4]$/') == 2 and src.count('/^air_l[2-4]$/') == 1
    src=src.replace('/^air_l[1-4]$/','/^air_l[1-3]$/').replace('/^air_l[2-4]$/','/^air_l[2-3]$/')
    src=exactly(src, 'Math.min(4, Number(this.atkId.slice(-1)) || 1)',
                'Math.min(NYTHERA_V26_TUNING.maxAirSlices, Number(this.atkId.slice(-1)) || 1)',f)
    # At the class level, the fatigue timer counts down only while a defender
    # hasn't blocked/parried; stacks have no cap (not capped at 14 etc).
    src=exactly(src,'  dragonRhythm = 0;', '''  // GUARD_FATIGUE_V26: anyone attacking into a guard loses tempo.
  guardFatigueStacks = 0;
  guardFatigueDecayT = GUARD_FATIGUE_TUNING.decaySecondsPerStack;
  guardFatigueSpeed() {
    return Math.max(GUARD_FATIGUE_TUNING.minSpeed,
      1 - this.guardFatigueStacks * GUARD_FATIGUE_TUNING.speedLostPerStack);
  }
  applyGuardFatigue() {
    if (this.isDown()) return;
    this.guardFatigueStacks += 1; // intentionally unlimited
    this.guardFatigueDecayT = GUARD_FATIGUE_TUNING.decaySecondsPerStack;
  }
  private tickGuardFatigue(dt: number) {
    if (this.guardFatigueStacks <= 0) {
      this.guardFatigueStacks = 0;
      this.guardFatigueDecayT = GUARD_FATIGUE_TUNING.decaySecondsPerStack;
      return;
    }
    this.guardFatigueDecayT -= dt;
    while (this.guardFatigueStacks > 0 && this.guardFatigueDecayT <= 0) {
      this.guardFatigueStacks -= 1;
      this.guardFatigueDecayT += GUARD_FATIGUE_TUNING.decaySecondsPerStack;
    }
    if (this.guardFatigueStacks <= 0)
      this.guardFatigueDecayT = GUARD_FATIGUE_TUNING.decaySecondsPerStack;
  }
  dragonRhythm = 0;''', f)
    src=exactly(src,'    this.parryCounterT = Math.max(0, this.parryCounterT - dt);',
                '    this.tickGuardFatigue(dt);\n    this.parryCounterT = Math.max(0, this.parryCounterT - dt);',f)
    # After all mode/kit/special changes, before attack is committed/serial incremented.
    src=exactly(src,'    this.atkPhase = 0;\n    this.buffered = false;\n    this.comboDamageMult = 1;', '''    // GUARD_FATIGUE_V26: finalized, kit-specific attack. Applies to both
    // basics and Z/X/C/V wind/active/recovery, but NEVER to cooldown duration.
    // 0.20x speed is a technical floor; stacks themselves remain uncapped.
    if (this.atk && this.guardFatigueStacks > 0) {
      const speed = this.guardFatigueSpeed();
      this.atk = { ...this.atk,
        wind: this.atk.wind / speed,
        active: this.atk.active / speed,
        recover: this.atk.recover / speed };
    }
    this.atkPhase = 0;
    this.buffered = false;
    this.comboDamageMult = 1;''',f)
    src=exactly(src,'    this.nytheraDreadfallHits = 0; // new round: wipe Dreadfall speed progress',
                '''    this.nytheraDreadfallHits = 0; // new round: wipe Dreadfall speed progress
    this.guardFatigueStacks = 0; // round reset; match-long Aster/Vesper passives unaffected
    this.guardFatigueDecayT = GUARD_FATIGUE_TUNING.decaySecondsPerStack;''',f)
    # Optional network tail; older game snapshots still parse without it.
    src=exactly(src,'this.dragonMode]; // PASSIVE_ROSTER_V10: optional appended snapshot fields',
       '''this.dragonMode,
      this.guardFatigueStacks, +this.guardFatigueDecayT.toFixed(2)]; // GUARD_FATIGUE_V26: optional tail, indices 86-87''',f)
    src=exactly(src,'    this.dragonMode = s.length > 85 ? Math.max(0,Math.min(3,s[85])) : 0;',
       '''    this.dragonMode = s.length > 85 ? Math.max(0,Math.min(3,s[85])) : 0;
    this.guardFatigueStacks = s.length > 86 ? Math.max(0, s[86]) : 0;
    this.guardFatigueDecayT = s.length > 87 ? s[87] : GUARD_FATIGUE_TUNING.decaySecondsPerStack;''',f)
    return src


def patch_nythera_and_fatigue_game(src: str) -> str:
    f='src/game/game.ts'
    src=exactly(src,'const aerial = /^air_l[1-4]$/.test(a.id);',
                'const aerial = /^air_l[1-3]$/.test(a.id);',f)
    src=exactly(src,'aerial ? Math.max(1, Math.min(4, Number(a.id.slice(-1)))) : 3;',
                'aerial ? Math.max(1, Math.min(3, Number(a.id.slice(-1)))) : 3;',f)
    src=exactly(src,'Four airy crescent ribbons', 'Three airy crescent ribbons',f)
    assert src.count('beat === 4')==4
    src=src.replace('beat === 4','beat === 3')
    src=exactly(src,'/^air_l[1-4]$/.test(a.id) || a.id === "heavy"',
                '/^air_l[1-3]$/.test(a.id) || a.id === "heavy"',f)
    src=exactly(src,'max 1.50× for this round. Four air slices remain.',
                'max 1.48× for this round. Three air slices per jump.',f)
    # Insert only after actual attack resolution, not animation-start guesses.
    src=exactly(src,'    // ZEPHYR_DRAGON_DANCER_V1: count actual impacts, not misses / block spam.',
    '''    // GUARD_FATIGUE_V26: real defended contact penalizes the *attacker*.
    // Each separate hit of a multi-hit move counts; dodges/clashes and misses do not.
    // Guard breaks also count because they were blocked contacts.
    if (attacker instanceof Fighter && d instanceof Fighter &&
        (result === "blocked" || result === "parry" || result === "guard_break"))
      attacker.applyGuardFatigue();
    // ZEPHYR_DRAGON_DANCER_V1: count actual impacts, not misses / block spam.''',f)
    src=exactly(src,'      if (f.kit === "tristaff") passives.push({ label: "RHYTHM",',
       '''      if (f.guardFatigueStacks > 0)
        passives.push({ label: "GUARD FATIGUE",
          value: `${f.guardFatigueStacks} stacks · ${f.guardFatigueSpeed().toFixed(2)}× · ${f.guardFatigueDecayT.toFixed(1)}s`,
          desc: "Every blocked or parried hit (including guard break) slows the attacker by 2%. No stack cap; 1 stack fades every 3s without another defended hit. Attack and skill animation speed only; cooldowns unchanged." });
      if (f.kit === "tristaff") passives.push({ label: "RHYTHM",''',f)
    # Player-vs-CPU black HUD uses the already populated passives; no layout changes.
    return src


def patch_nythera_and_fatigue_ai(src: str) -> str:
    f='src/game/ai.ts'
    assert src.count('/^air_l[1-4]$/') == 2
    src=src.replace('/^air_l[1-4]$/','/^air_l[1-3]$/')
    # Guard adaptation runs only after real defensive reactions have priority;
    # it cannot create attacks, damage, block duration or invulnerability.
    method='''
  // GUARD_FATIGUE_V26: observable guard and fatigue only, ordinary movement.
  // Deliberately brief: no previous anti-Zenith eternal-block regression.
  private fatigueCircleT = 0;
  private fatigueCircleCd = 0;
  private fatigueSide = 1;
  private guardFatigueTactics(f: Fighter, o: Fighter, dt: number): boolean {
    this.fatigueCircleT = Math.max(0, this.fatigueCircleT - dt);
    this.fatigueCircleCd = Math.max(0, this.fatigueCircleCd - dt);
    if (f.isDown() || !f.onGround || f.state !== S.IDLE || f.stage ||
        o.isDown() || o.state !== S.BLOCK ||
        f.intent.attack || f.intent.skill || f.intent.block ||
        f.intent.dash.lengthSq() > 0.01 ||
        this.blockWait >= 0 || this.blockHold > 0 ||
        o.guard < o.maxGuard * 0.30 ||
        (o.state === S.ATTACK && o.atkPhase < 2)) {
      this.fatigueCircleT = 0;
      return false;
    }
    const danger = this.threats.projectiles().some(p => p.target === f &&
      p.pos.distanceTo(f.root.position) < 3.4);
    if (danger) { this.fatigueCircleT = 0; return false; }
    const dist = f.root.position.distanceTo(o.root.position);
    if (dist > 3.7 || RANGED.has(f.kit)) return false;
    // Easy/Normal sometimes keep pressure; Hard/Master avoid donating fatigue.
    const lowTempo = f.guardFatigueStacks >= 3;
    const shouldBait = lowTempo || (f.guardFatigueStacks >= 1 && this.iqLevel >= 2);
    if (this.fatigueCircleT <= 0 && this.fatigueCircleCd <= 0 &&
        (shouldBait || (this.iqLevel >= 2 && Math.random() < dt * 1.8))) {
      this.fatigueCircleT = lowTempo ? 0.55 : 0.36;
      this.fatigueCircleCd = lowTempo ? 1.25 : 1.70;
      this.fatigueSide = Math.random() < 0.5 ? -1 : 1;
      this.queue=[]; this.hold=0;
    }
    if (this.fatigueCircleT <= 0) return false;
    const toward = o.root.position.clone().sub(f.root.position).setY(0);
    if (toward.lengthSq() < 0.02) return false;
    toward.normalize();
    const sidestep = new THREE.Vector3(-toward.z, 0, toward.x).multiplyScalar(this.fatigueSide);
    // Reposition outside a raised shield; resume pressure on shield drop or timer end.
    f.intent.move.copy(sidestep).addScaledVector(toward, dist < 1.8 ? -0.40 : 0.10).normalize();
    f.intent.attack = false;
    return true;
  }
'''
    src=exactly(src,'  think(f: Fighter, dt: number) {',method+'  think(f: Fighter, dt: number) {',f)
    src=exactly(src,'    this.defendLongCombo(f, o);\n    if (this.projectileCounterfire(f, o)) return;',
                '    this.defendLongCombo(f, o);\n    if (this.guardFatigueTactics(f, o, dt)) return;\n    if (this.projectileCounterfire(f, o)) return;',f)
    src=exactly(src,'  if (id === "zenith" && blocked && o.guard > o.maxGuard * 0.55 &&',
                '''  // GUARD_FATIGUE_V26: all fighters probe defenses instead of endlessly
  // donating attack speed. Respect actual enemy recovery and low guard.
  if (blocked && f.guardFatigueStacks >= 2 && !punish &&
      o.guard > o.maxGuard * 0.48 &&
      Math.random() < [0.25, 0.48, 0.70, 0.86][this.iqLevel]) return;
  if (id === "zenith" && blocked && o.guard > o.maxGuard * 0.55 &&''',f)
    src=exactly(src,'  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge',
                '''  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge
  // A visibly fatigued foe recovers and swings more slowly. Press the opening,
  // but keep real reach, cooldown, attack states and anti-projectile dodges.
  if (o.guardFatigueStacks >= 5 && !blocked && !danger &&
      this.iqLevel >= 2) this.thinkCd *= 0.75;
  // Own fatigue favors careful single attacks, not spamming a protected shield.
  if (f.guardFatigueStacks >= 8 && !punish) this.thinkCd *= 1.10;''',f)
    return src


def patch_nythera_hud(src: str) -> str:
    f='src/ui/GameView.tsx'
    assert src.count('1.50x')==2, 'Expected two displayed Nythera speed-cap strings'
    return src.replace('1.50x','1.48x')


def patch_roster(src: str) -> str:
    # The passive description belongs in character information, not the compact battle HUD.
    return exactly(src,
        'Rhythm strengthens his next finisher.',
        'Each active Rhythm stack grants +20% attack speed (maximum +60%). Rhythm strengthens his next finisher.',
        'src/game/roster.ts')


def main() -> int:
    base=Path(sys.argv[1] if len(sys.argv)>1 else ".").expanduser().resolve()
    print("FIGHT ROYALE V26 — ZEPHYR / NYTHERA / FATIGUE / AI | target:",base)
    required=("src/game/model.ts","src/game/vrm.ts","src/game/fighter.ts","src/game/roster.ts",
              "src/game/game.ts","src/game/ai.ts","src/ui/GameView.tsx")
    try:
        original={}
        for rel in required:
            path=base/rel
            if not path.is_file():raise RuntimeError(f"Missing {rel}; run from the web folder")
            original[rel]=path.read_text(encoding="utf-8-sig")
            if MARK in original[rel]:raise RuntimeError(f"V26 is already installed in {rel}; no files changed")
        if "ZEPHYR_MODE_BALANCE_V25" not in original["src/game/model.ts"]:
            raise RuntimeError("Expected Zephyr V25 source. Install V25 first; no changes written.")
        if "ZEPHYR_BODY_GRIP_V21" not in original["src/game/vrm.ts"]:
            raise RuntimeError("Expected V21+ VRM grip/body layer. No changes written.")
        edited={"src/game/model.ts":patch_model(original["src/game/model.ts"]),
                "src/game/vrm.ts":patch_rig(original["src/game/vrm.ts"]),
                "src/game/fighter.ts":patch_nythera_and_fatigue_fighter(patch_fighter(original["src/game/fighter.ts"])),
                "src/game/roster.ts":patch_roster(original["src/game/roster.ts"]),
                "src/game/game.ts":patch_nythera_and_fatigue_game(original["src/game/game.ts"]),
                "src/game/ai.ts":patch_nythera_and_fatigue_ai(original["src/game/ai.ts"]),
                "src/ui/GameView.tsx":patch_nythera_hud(original["src/ui/GameView.tsx"])}
        stamp=datetime.datetime.now().strftime("v26-%Y%m%d-%H%M%S")
        backup=base/".zephyr-backups"/stamp
        for rel in required:
            out=backup/rel;out.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(base/rel,out)
        written=[]
        try:
            for rel in required:
                path=base/rel
                fd,temp=tempfile.mkstemp(prefix=".zephyr-v26-",dir=path.parent,suffix=".tmp")
                try:
                    with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as h:
                        h.write(edited[rel]);h.flush();os.fsync(h.fileno())
                    os.replace(temp,path)
                finally:
                    if os.path.exists(temp):os.unlink(temp)
                written.append(rel)
                print("  updated",rel)
        except Exception:
            for rel in written:shutil.copy2(backup/rel,base/rel)
            raise
        print("Done. Backups:",backup)
        print("Debug flag: src/game/model.ts -> ZEPHYR_ANTICLIP_DEBUG")
        print("Stance/combo tuning: model.ts -> WEAPON_STANCE, ZEPHYR_COMBO_PATH_V26, ZEPHYR_ANTICLIP_TUNING")
        print("Body/arm tuning: vrm.ts -> ZEPHYR_COMBO_BODY_V26, ZEPHYR_ARM_TUNING_V26")
        print("Run: npx tsc --noEmit -p . && npm run dev")
        print("Rhythm: +0.20x attack speed/stack (1.00x to 1.60x; 25-second timer).")
        print("Passive tuning: fighter.ts -> ZEPHYR_PASSIVE_TUNING.attackSpeedPerStack")
        print("Nythera: 3 air cuts, 1.48x Dreadfall cap (from 1.50x).")
        print("Guard Fatigue: -0.02x speed per defended hit, 3s decay, no stack cap.")
        print("AI: brief shield-bait footwork, exploit fatigue, avoid spamming guard.")
        print("Tune: fighter.ts GUARD_FATIGUE_TUNING and NYTHERA_V26_TUNING")
        print("Existing cooldowns, combat hitboxes, projectile mechanics and input unchanged.")
        return 0
    except Exception as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
