#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale – Nesa Heart Hammer complete installer (latest AI compatible).

Install Nesa's unique hammer kit and heart weapon, portrait and skills icons.
Run with: python Install_Nesa_Heart_Hammer.py
Or: python Install_Nesa_Heart_Hammer.py "C:\\path\\Fight-Royale\\web"
Option: --check (validate patch without writing)
Supports original project and earlier Nesa installer. Never overwrites your VRM.
Source backups in web/.nesa_installer_backups/. Python 3.9+, no pip packages.
"""
from pathlib import Path
from datetime import datetime
import argparse
import base64
import os
import shutil
import sys
import tempfile

VERSION = "NESA_HEART_HAMMER_V3_LATEST_AI"

class PatchError(RuntimeError):
    pass

def fail(msg):
    raise PatchError(msg)

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        fail(f"{label}: expected exactly one code anchor, found {n}")
    return text.replace(old, new, 1)

def patch_roster(text: str) -> str:
    anchor = "];\n\nexport function resolveEnemy(player: number, pick: number): number {"
    insert = """  // NESA_HAMMER_V1 - based on the provided pink/brown VRoid look.
  { id: "nesa", title: "Hammer Princess", role: "Bruiser - Giant Hammer",
    desc: "A deceptively cute hammer fighter who uses heavy momentum, launching kicks and crushing shockwaves to bully dodgers and blockers alike.",
    stats: { power: 5, speed: 2, range: 3, defense: 4 },
    look: { name: "Nesa", body: "f", vrm: "nesa", kit: "hammer", element: "force", outfit: "knight", style: "long", hat: "none",
      hair: "#5a3427", hair_shade: "#b78368", iris_top: "#6f4a39", iris_bottom: "#b69072", eye_dark: "#2c1a15",
      tunic: "#f1d0da", band: "#c17696", pants: "#6d4956", boots: "#5a3541", metal: "#d9d1dd", trim: "#ffb3d0",
      cape: "#8e617b", cape_bottom: "#f5c3d7", glow: "#ffd5e5", shield: "#6f5361", emblem: "#ffd5ea" } },
];

export function resolveEnemy(player: number, pick: number): number {"""
    return replace_once(text, anchor, insert, "roster nesa entry")


def patch_kits(text: str) -> str:
    text = replace_once(text,
'''    greatsword: greatsword,
    katana: katana,''',
'''    greatsword: greatsword,
    hammer: hammer,
    katana: katana,''',
"kits attack dispatch")

    text = replace_once(text,
'''    case "greatsword":
      return a({ name: "Berserk", desc: "Deal 20% more damage for 6 seconds.", cd: 14, type: "buff", mode: "rage", duration: 6, wind: 0.2, recover: 0.4, pose_w: "charge", pose_s: "win" });
    case "katana":''',
'''    case "greatsword":
      return a({ name: "Berserk", desc: "Deal 20% more damage for 6 seconds.", cd: 14, type: "buff", mode: "rage", duration: 6, wind: 0.2, recover: 0.4, pose_w: "charge", pose_s: "win" });
    case "hammer":
      return a({ name: "GIGA BONK!", desc: "She fights the weight, leaps up with the hammer and slams down with an enormous shockwave.", cd: 22, type: "strike", at: "self", mode: "leap", self_jump: 8.0, speed: 18, wind: 0.62, active: 0.20, recover: 0.90, dmg: 360, guard: 100, knock: 10, stun: 1.15, heavy: true, radius: 3.5, style: "slam", pose_w: "charge", pose_s: "heavy_s" });
    case "katana":''',
"kits bonus skill hammer")

    hammer_fn = '''function hammer(): Record<string, Attack> {
  return {
    l1: a({ name: "Bonk Step 1", wind: 0.24, active: 0.11, recover: 0.28, dmg: 105, guard: 28, reach: 2.35, lunge: 1.7, knock: 2.4, stun: 0.34, pose_w: "l1_w", pose_s: "l1_s", next: "l2" }),
    l2: a({ name: "Bonk Step 2", wind: 0.24, active: 0.11, recover: 0.30, dmg: 112, guard: 30, reach: 2.4, lunge: 1.8, knock: 2.6, stun: 0.35, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ name: "Bonk Step 3", wind: 0.30, active: 0.13, recover: 0.35, dmg: 128, guard: 34, reach: 2.45, lunge: 1.9, knock: 3.2, stun: 0.40, pose_w: "l3_w", pose_s: "l3_s", next: "l4" }),
    l4: a({ name: "Bonk Step 4", desc: "Massive slam finisher with a short shockwave.", type: "strike", at: "self", wind: 0.34, active: 0.16, recover: 0.42, dmg: 160, guard: 42, knock: 5.8, stun: 0.58, heavy: true, delay: 0.06, radius: 2.35, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
    heavy: a({ name: "Hammer Upper", desc: "Hold to charge a devastating uppercut that launches enemies.", wind: 0.28, active: 0.13, recover: 0.58, dmg: 210, guard: 58, reach: 2.35, lunge: 2.2, knock: 6.8, stun: 0.72, heavy: true, self_jump: 4.8, pose_w: "charge", pose_s: "heavy_s" }),
    z: a({ name: "Side Swipe", desc: "A brutal sideways hammer swing. Even on block it still blasts the target backward and crushes guard.", cd: 7, wind: 0.22, active: 0.12, recover: 0.44, dmg: 170, guard: 72, reach: 2.55, lunge: 1.4, knock: 8.0, stun: 0.62, heavy: true, pose_w: "l2_w", pose_s: "l2_s" }),
    x: a({ name: "Upsie Daisie", desc: "Use the hammer as a lever, fling yourself forward and up, then crash into the opponent.", cd: 9, wind: 0.18, active: 0.18, recover: 0.50, dmg: 145, guard: 34, reach: 2.1, lunge: 6.8, knock: 5.2, stun: 0.52, self_jump: 6.3, heavy: true, pose_w: "charge", pose_s: "heavy_s" }),
    c: a({ name: "Roundabout Crash", desc: "A rising spin into a compact landing shockwave.", cd: 12, type: "strike", at: "self", mode: "leap", self_jump: 6.9, speed: 15, wind: 0.32, active: 0.18, recover: 0.64, dmg: 235, guard: 68, knock: 7.2, stun: 0.86, heavy: true, radius: 2.8, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
  };
}

'''
    text = replace_once(text,
'''function katana(): Record<string, Attack> {''',
hammer_fn + '''function katana(): Record<string, Attack> {''',
"kits hammer function")

    text = replace_once(text,
'''  greatsword: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },
  chainblade: CHAINBLADE,''',
'''  greatsword: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },
  hammer: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },
  chainblade: CHAINBLADE,''',
"kits hammer poses table")

    return text


def patch_model(text: str) -> str:
    text = replace_once(text,
'''      case "greatsword": this.buildGreatsword(); break;
      case "katana": this.buildKatana(); break;''',
'''      case "greatsword": this.buildGreatsword(); break;
      case "hammer": this.buildHammer(); break;
      case "katana": this.buildKatana(); break;''',
"model hammer switch")

    text = replace_once(text, 'const big = this.kit === "greatsword";', 'const big = this.kit === "greatsword" || this.kit === "hammer";', "model big torso")
    text = replace_once(text, 'this.walkPhase += dt * (this.kit === "greatsword" ? 8.5 : 11) * moving * (1 + 0.46 * running);', 'this.walkPhase += dt * ((this.kit === "greatsword" || this.kit === "hammer") ? 8.5 : 11) * moving * (1 + 0.46 * running);', "model heavy walk phase")
    text = replace_once(text, 'const stride = this.kit === "greatsword" ? 0.36 : 0.55;', 'const stride = (this.kit === "greatsword" || this.kit === "hammer") ? 0.36 : 0.55;', "model heavy stride")
    text = replace_once(text, 'this.torso.rotation.x += running * (this.kit === "greatsword" ? 0.08 : 0.13);', 'this.torso.rotation.x += running * ((this.kit === "greatsword" || this.kit === "hammer") ? 0.08 : 0.13);', "model heavy run lean")
    text = replace_once(text,
'''    this.vrmRig.style = this.kit === "chainblade" ? "chainblade" : this.kit === "glaive" ? "storm" : this.kit === "sickle" ? "feral" : this.kit === "greatsword" ? "greatsword" : this.look.body === "m" ? "heavy" : "light";''',
'''    this.vrmRig.style = this.kit === "chainblade" ? "chainblade" : this.kit === "glaive" ? "storm" : this.kit === "sickle" ? "feral" : (this.kit === "greatsword" || this.kit === "hammer") ? "greatsword" : this.look.body === "m" ? "heavy" : "light";''',
"model vrm style")
    text = replace_once(text, 'if (["knight", "greatsword", "katana"].includes(this.kit) && this.bladeBase.parent) {', 'if (["knight", "greatsword", "hammer", "katana"].includes(this.kit) && this.bladeBase.parent) {', "model sheathe set")
    text = replace_once(text, 'if (this.kit === "greatsword") { this.vrmRig.restSword = true; this.vrmRig.grip.left = true; }', 'if (this.kit === "greatsword" || this.kit === "hammer") { this.vrmRig.restSword = true; this.vrmRig.grip.left = true; }', "model vrm left grip")

    hammer_builder = '''  private buildHammer() {
    const L = this.look;
    const h = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    mesh(h, cyl(0.022, 0.028, 0.88, 10), this.tn(BROWN), [0, 0.32, 0]);
    mesh(h, cyl(0.034, 0.034, 0.10, 10), this.tn(L.trim), [0, -0.10, 0]);
    mesh(h, sphere(0.038, 12), this.gem(), [0, -0.22, 0]);
    mesh(h, box(0.30, 0.26, 0.22), this.metal(), [0, 0.98, 0]);
    mesh(h, box(0.20, 0.42, 0.20), this.metal(), [0, 1.06, 0]);
    mesh(h, box(0.36, 0.08, 0.28), this.tn(L.trim), [0, 0.98, 0]);
    mesh(h, box(0.08, 0.36, 0.30), this.tn(L.trim), [0, 0.98, 0]);
    mesh(h, sphere(0.05, 14), this.gem(), [0.13, 0.98, 0.11]);
    mesh(h, sphere(0.05, 14), this.gem(), [-0.13, 0.98, -0.11]);
    this.bladeBase = pivot(h, [0, 0.42, 0]);
    this.bladeTip = pivot(h, [0, 1.18, 0]);
    this.gripL = pivot(h, [0, 0.04, 0]);
    this.shieldNode = pivot(h, [0, 0.74, 0]);
    this.castPoint = this.bladeTip;
  }

'''
    text = replace_once(text, '  private buildKatana() {', hammer_builder + '  private buildKatana() {', "model buildHammer function")
    return text


def patch_fighter(text: str) -> str:
    text = replace_once(text, 'const tempestActive = this.kit === "greatsword" && this.state === S.ATTACK && this.atk?.style === "iron_tempest";', 'const tempestActive = this.kit === "greatsword" && this.state === S.ATTACK && this.atk?.style === "iron_tempest";', "fighter noop anchor")
    text = replace_once(text,
'''    const bladeActive = this.state === S.ATTACK && this.atk?.type === "melee" &&
      ((this.kit === "greatsword") || (this.kit === "glaive") || (this.kit === "knight" && this.look.element === "light"));''',
'''    const bladeActive = this.state === S.ATTACK && this.atk?.type === "melee" &&
      ((this.kit === "greatsword") || (this.kit === "hammer") || (this.kit === "glaive") || (this.kit === "knight" && this.look.element === "light"));''',
"fighter bladeActive")
    text = replace_once(text, 'this.bladeSwingYaw = direction * (this.kit === "greatsword" ? 0.48 : this.kit === "glaive" ? (this.atkId === "l4" ? 0.44 : 0.29) : 0.27) * (1 - 2 * turn) * settle;', 'this.bladeSwingYaw = direction * ((this.kit === "greatsword" || this.kit === "hammer") ? 0.48 : this.kit === "glaive" ? (this.atkId === "l4" ? 0.44 : 0.29) : 0.27) * (1 - 2 * turn) * settle;', "fighter swing yaw")
    text = replace_once(text,
'''        if (a?.type === "melee" && (this.kit === "greatsword" ||
            (this.kit === "knight" && this.look.element === "light"))) {
          const heavySword = this.kit === "greatsword";''',
'''        if (a?.type === "melee" && ((this.kit === "greatsword" || this.kit === "hammer") ||
            (this.kit === "knight" && this.look.element === "light"))) {
          const heavySword = this.kit === "greatsword" || this.kit === "hammer";''',
"fighter heavy melee poses")
    return text


def patch_ai(text: str) -> str:
    # The latest AI includes Zarek's own short-range positioning rule.
    # Only change Garrick's arm of the ternary, preserve every other kit.
    old_want = 'f.kit === "greatsword" ? 1.6'
    new_want = '(f.kit === "greatsword" || f.kit === "hammer") ? 1.6'
    if new_want not in text:
        text = replace_once(text, old_want, new_want, "ai desired range")
    old_reach = 'f.kit === "greatsword" ? 2.3'
    new_reach = '(f.kit === "greatsword" || f.kit === "hammer") ? 2.3'
    if new_reach not in text:
        text = replace_once(text, old_reach, new_reach, "ai reach")
    return text


def patch_game(text: str) -> str:
    text = replace_once(text, 'else if (f.kit === "greatsword" || heavy) this.snd("swing_heavy", 0.8);', 'else if (f.kit === "greatsword" || f.kit === "hammer" || heavy) this.snd("swing_heavy", 0.8);', "game heavy sound")
    return text



# Respec the supplied first Nesa patch into the complete, playable version.
# The user's original beta did not include a hammer entry in STATS.

def patch_all(rel, src):
    if rel == 'src/game/roster.ts':
        if 'id: "nesa"' not in src:
            src = patch_roster(src)
        return src
    if rel == 'src/game/kits.ts':
        if 'hammer: hammer,' not in src:
            src = patch_kits(src)
        if '  hammer: { hp:' not in src:
            src = replace_once(src,
                '  chainblade: { hp: 2450, guard: 100, move: 3.55, walk: 2.75, parry: 0.16, jump: 7.0 },',
                '  chainblade: { hp: 2450, guard: 100, move: 3.55, walk: 2.75, parry: 0.16, jump: 7.0 },\n  hammer: { hp: 2650, guard: 110, move: 3.05, walk: 2.45, parry: 0.15, jump: 7.0 },',
                'add HP and guard stats for hammer')
        # Aster, Ember and every other existing kit are left untouched.
        p = src.find('function hammer(): Record<string, Attack> {')
        q = src.find('function katana(): Record<string, Attack> {', p)
        if p < 0 or q < 0:
            fail('could not locate Nesa hammer attacks')
        src = src[:p] + NESA_ATTACKS + src[q:]
        start = src.find('    case "hammer":', src.index('function bonusSkill('))
        finish = src.find('    case "katana":', start)
        if start < 0 or finish < 0:
            fail('could not locate Nesa bonus skill')
        src = src[:start] + NESA_BONUS + src[finish:]
        if 'const NESA_SWINGS:' not in src:
            src = replace_once(src, 'const TABLES: Record<string, Record<string, Pose>> = {', NESA_POSES + 'const TABLES: Record<string, Record<string, Pose>> = {', 'Nesa hammer poses')
        src = replace_once(src, '  hammer: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },', '  hammer: { ...twoHanded(KNIGHT), ...NESA_SWINGS },', 'hammer-specific procedural poses') if '  hammer: { ...twoHanded(KNIGHT), ...GARRICK_SWINGS },' in src else src
        return src
    if rel == 'src/game/model.ts':
        if 'private buildHammer()' not in src:
            src = patch_model(src)
        p = src.find('  private buildHammer() {')
        q = src.find('  private buildKatana() {', p)
        if p < 0 or q < 0:
            fail('cannot locate Nesa hammer model builder')
        return src[:p] + HEART_HAMMER_MODEL + src[q:]
    if rel == 'src/game/fighter.ts':
        if 'this.kit === "hammer"' not in src:
            src = patch_fighter(src)
        if 'NESA_CRUSH_BLOCK_V2' not in src:
            # Independent block chip path restricted to Nesa's Side Swipe.
            src = replace_once(src,
                '        this.lastDamage = dmg * 0.4;',
                '        // NESA_CRUSH_BLOCK_V2: her sideways hammer deals 50% chip damage through block.\n'
                '        this.lastDamage = attacker instanceof Fighter && attacker.kit === "hammer" && a.id === "z" ? dmg * 0.5 : dmg * 0.4;',
                'Nesa guard-break chip damage')
            src = replace_once(src,
                '      this.knock = a.knock * 0.5;\n      this.model.recoil = 0.7;\n      return "blocked";',
                BLOCK_CHIP,
                'Nesa block crush knockback')
            # Add guaranteed recoverable knockdown when the already-installed down/wake system exists.
            if 'private beginKnockdown()' in src and 'knockdownLockT' in src:
                src = replace_once(src,
                    '        if (this.bloodFestivalT <= 0) this.stagger(0.85);',
                    """        if (attacker instanceof Fighter && attacker.kit === "hammer" && a.id === "z" &&
            !this.stage && this.onGround && this.bloodFestivalT <= 0 &&
            this.knockdownLockT <= 0 && !this.chainBoundBy && !this.chainBindTarget) this.beginKnockdown();
        else if (this.bloodFestivalT <= 0) this.stagger(0.85);""",
                    'guard-break floor knockdown')
                src = replace_once(src,
                    '        if (!this.stage) this.stagger(0.6);',
                    """        if (!this.stage && this.onGround && this.knockdownLockT <= 0 &&
            this.bloodFestivalT <= 0 && !this.chainBoundBy && !this.chainBindTarget)
          this.beginKnockdown();
        else if (!this.stage) this.stagger(0.6);""",
                    'knockdown on blocked sideways smash')
        return src
    if rel == 'src/game/ai.ts':
        return patch_ai(src) if 'f.kit === "hammer"' not in src else src
    if rel == 'src/game/game.ts':
        if 'f.kit === "hammer"' not in src:
            src = patch_game(src)
        if 'NESA_CRUSH_BLOCK_V2' not in src:
            src = replace_once(src,
                '"BLOCK", "#c9d3e6", 0.7);',
                '(attacker instanceof Fighter && attacker.kit === "hammer" && a.id === "z" ? "CRUSH BLOCK!" : "BLOCK"), "#c9d3e6", 0.7); // NESA_CRUSH_BLOCK_V2',
                'Nesa crush block effect')
        return src
    return src

NESA_ATTACKS = '''function hammer(): Record<string, Attack> {
  return {
    // Four slow but flowing hits. Each step winds up from the previous hammer's momentum.
    l1: a({ name: "Heart Swing", wind: 0.25, active: 0.11, recover: 0.28, dmg: 100, guard: 28, reach: 2.35, lunge: 1.7, knock: 2.4, stun: 0.34, pose_w: "l1_w", pose_s: "l1_s", next: "l2" }),
    l2: a({ name: "Reverse Heart", wind: 0.25, active: 0.11, recover: 0.30, dmg: 107, guard: 31, reach: 2.4, lunge: 1.8, knock: 2.6, stun: 0.35, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ name: "Spin to Win", wind: 0.32, active: 0.14, recover: 0.34, dmg: 125, guard: 35, reach: 2.5, lunge: 1.6, knock: 3.2, stun: 0.4, pose_w: "l3_w", pose_s: "l3_s", next: "l4" }),
    l4: a({ name: "Heartquake", desc: "Final hammer hit slams the ground, sending out a short shockwave.", type: "strike", at: "self", wind: 0.37, active: 0.16, recover: 0.48, dmg: 155, guard: 43, knock: 5.8, stun: 0.56, heavy: true, delay: 0.07, radius: 2.20, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
    heavy: a({ name: "Heart Upper", desc: "A charged upward hammer swing with powerful knockback.", wind: 0.28, active: 0.14, recover: 0.65, dmg: 220, guard: 60, reach: 2.4, lunge: 1.8, knock: 7, stun: 0.78, heavy: true, self_jump: 4.4, pose_w: "charge", pose_s: "heavy_s" }),
    z: a({ name: "Side Swipe", desc: "Unstoppable horizontal swing. Blocking takes 50% damage and still causes knockback and, with the Knockdown update, a floor knockdown; dodging avoids it.", cd: 8, wind: 0.30, active: 0.13, recover: 0.52, dmg: 170, guard: 67, reach: 2.55, lunge: 1.3, knock: 8, stun: 0.62, heavy: true, pose_w: "nx_w", pose_s: "nx_s" }),
    x: a({ name: "Upsie Daisie", desc: "Plants the hammer as a lever and springs forward into a high flying kick; the hammer whips along behind.", cd: 9, wind: 0.22, active: 0.20, recover: 0.50, dmg: 150, guard: 33, reach: 2.1, lunge: 6.8, knock: 5.0, stun: 0.48, self_jump: 6.8, pose_w: "kick_w", pose_s: "kick_s" }),
    c: a({ name: "GIGA BONK!", desc: "She struggles to lift the massive heart hammer, leaps skyward and crashes it down with a huge shockwave.", cd: 22, type: "strike", at: "self", mode: "leap", self_jump: 8, wind: 0.62, active: 0.20, recover: 0.90, dmg: 355, guard: 98, knock: 10, stun: 1.1, heavy: true, radius: 3.5, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
  };
}

'''
NESA_BONUS = '''    case "hammer":
      return a({ name: "Roundabout Crash", desc: "Spin the hammer while leaping and land in a compact shockwave.", cd: 12, type: "strike", at: "self", mode: "leap", self_jump: 6.9, wind: 0.32, active: 0.18, recover: 0.64, dmg: 230, guard: 68, knock: 7.2, stun: 0.86, heavy: true, radius: 2.8, style: "slam", pose_w: "l3_w", pose_s: "heavy_s" });
'''
NESA_POSES = '''// NESA_HEART_HAMMER_V2: weapon-weight poses, distinct from Garrick.
const NESA_SWINGS: Record<string, Pose> = {
  idle: K(P([0.14, -0.2, 0], [-0.06, 0.15, 0], [-0.9, -0.18, -0.10], [-0.2, 0, 0], [-0.96, 0.13, 0.12], [-0.2, 0, 0], [-0.35, 0, 0.07], [0.18, 0, -0.06], -0.13), 0.15, 0.25),
  l1_w: P([0.18, -1.12, -0.08], [0.04, 0.55, 0], [-1.03, -1.0, -0.20], [0.72, 0, 0], [-1.06, -0.72, 0.12], [0.65, 0, 0], [-0.56, 0, 0.13], [0.4, 0, -0.1], -0.22),
  l1_s: P([0.34, 0.96, 0.1], [-0.08, -0.55, 0], [-1.7, 1.2, -0.1], [0.12, 0, 0], [-1.52, 1.12, 0.1], [0.1, 0, 0], [-0.65, 0, 0.12], [0.45, 0, -0.08], -0.22),
  l2_w: P([0.16, 0.9, 0.09], [0, -0.48, 0], [-1.4, 1.0, 0.1], [0.42, 0, 0], [-1.2, 0.8, 0.08], [0.43, 0, 0], [-0.47, 0, 0.11], [0.36, 0, -0.09], -0.20),
  l2_s: P([0.32, -1.1, -0.1], [-0.1, 0.65, 0], [-1.6, -1.15, -0.08], [0.16, 0, 0], [-1.46, -1.05, 0.12], [0.12, 0, 0], [-0.63, 0, 0.12], [0.46, 0, -0.1], -0.24),
  l3_w: P([-0.2, -0.66, 0.05], [0.03, 0.44, 0], [-2.4, -0.45, -0.1], [0.7, 0, 0], [-2.0, -0.4, 0.12], [0.5, 0, 0], [-0.56, 0, 0.12], [0.48, 0, -0.12], -0.22),
  l3_s: P([0.35, 1.12, -0.10], [-0.13, -0.76, 0], [-1.7, 1.22, 0], [0.15, 0, 0], [-1.55, 1.0, 0.12], [0.1, 0, 0], [-0.6, 0, 0.11], [0.44, 0, -0.11], -0.23),
  charge: K(P([-0.24, -0.38, 0], [0.09, 0.28, 0], [-2.6, -0.35, -0.12], [0.7, 0, 0], [-2.44, -0.25, 0.12], [0.65, 0, 0], [-0.66, 0, 0.1], [0.54, 0, -0.1], -0.28), 0.6, 0.55),
  heavy_s: K(P([0.66, 0.18, 0], [-0.22, 0, 0], [-0.85, 0.36, 0], [0.14, 0, 0], [-0.88, -0.2, 0.1], [0.12, 0, 0], [-0.95, 0, 0.10], [0.60, 0, -0.1], -0.32), 0.85, 0.9),
  nx_w: P([0.24, 0.92, 0], [0, -0.4, 0], [-1.4, 0.98, 0], [0.4, 0, 0], [-1.36, 0.78, 0], [0.4, 0, 0], [-0.5, 0, 0.10], [0.44, 0, -0.08], -0.19),
  nx_s: P([0.36, -1.08, 0], [-0.06, 0.5, 0], [-1.45, -1.18, 0], [0.1, 0, 0], [-1.28, -1.10, 0], [0.12, 0, 0], [-0.64, 0, 0.14], [0.50, 0, -0.09], -0.22),
  kick_w: K(P([0.48, -0.2, 0], [-0.16, 0.10, 0], [-0.5, 0.2, 0.1], [0.3, 0, 0], [-0.4, -0.2, -0.15], [0.4, 0, 0], [-0.65, 0, 0], [-0.35, 0, 0.06], -0.4), 1.0, 0.8),
  kick_s: K(P([-0.2, 0.1, 0], [0.14, -0.1, 0], [-0.65, 0.7, 0.18], [0.1, 0, 0], [-0.6, -0.6, -0.2], [0.1, 0, 0], [-1.42, 0, 0.02], [0.48, 0, -0.10], -0.04), 0.15, 0.85),
};

'''
HEART_HAMMER_MODEL = '''  private buildHammer() {
    const L = this.look;
    const h = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    // Two-handed striped handle and soft pink heart-shaped forged head.
    mesh(h, cyl(0.026, 0.029, 0.92, 10), this.tn("#f9b8d2"), [0, 0.31, 0]);
    for (let i = 0; i < 7; i++)
      mesh(h, cyl(0.03, 0.03, 0.035, 12), this.tn(i % 2 ? "#ffffff" : "#b57b95"), [0, -0.11 + i * 0.083, 0]);
    mesh(h, sphere(0.045, 12), this.gem(), [0, -0.19, 0]);
    mesh(h, cyl(0.066, 0.067, 0.12, 16), this.tn(L.trim), [0, 0.78, 0]);
    const heart = new THREE.Shape();
    heart.moveTo(0, -0.23);
    heart.bezierCurveTo(-0.14, -0.14, -0.34, 0.025, -0.27, 0.17);
    heart.bezierCurveTo(-0.19, 0.31, -0.045, 0.27, 0, 0.16);
    heart.bezierCurveTo(0.045, 0.27, 0.19, 0.31, 0.27, 0.17);
    heart.bezierCurveTo(0.34, 0.025, 0.14, -0.14, 0, -0.23);
    const geo = new THREE.ExtrudeGeometry(heart, {
      depth: 0.28, steps: 1, bevelEnabled: true,
      bevelThickness: 0.04, bevelSize: 0.035, bevelSegments: 3, curveSegments: 16,
    });
    const head = mesh(h, geo, this.tn("#f39abd"), [0, 1.08, -0.14]);
    head.castShadow = true;
    const inset = mesh(h, geo.clone(), this.tn("#ffcee3", false), [0, 1.08, 0.153]);
    inset.scale.set(0.78, 0.78, 0.07);
    mesh(h, sphere(0.07, 14), this.gem(), [0, 1.05, 0.19], [0, 0, 0], [1.0, 0.8, 0.5]);
    // Heart-shaped hammer has no star ornaments.
    this.bladeBase = pivot(h, [0, 0.54, 0]);
    this.bladeTip = pivot(h, [0, 1.34, 0]);
    this.gripL = pivot(h, [0, 0.05, 0]);
    this.shieldNode = pivot(h, [0, 0.76, 0]);
    this.castPoint = this.bladeTip;
  }

'''
BLOCK_CHIP = '''      // NESA_CRUSH_BLOCK_V2: blocking her Side Swipe is never a free escape.
      if (attacker instanceof Fighter && attacker.kit === "hammer" && a.id === "z") {
        this.lastDamage = dmg * 0.5;
        this.lastCrit = false;
        this.hp = Math.max(0, this.hp - this.lastDamage);
        this.knock = Math.max(this.knock, a.knock * 0.78);
        if (this.hp <= 0) { this.ko(); return "ko"; }
        if (!this.stage) this.stagger(0.6);
        this.model.recoil = 0.95;
        return "blocked";
      }
      this.knock = a.knock * 0.5;
      this.model.recoil = 0.7;
      return "blocked";'''


ICONS = {
    'chars/nesa': base64.b64decode('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'),
    'skills/hammer-z': base64.b64decode('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'),
    'skills/hammer-x': base64.b64decode('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'),
    'skills/hammer-c': base64.b64decode('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'),
    'skills/hammer-v': base64.b64decode('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'),
}

FILES = ['src/game/roster.ts', 'src/game/kits.ts', 'src/game/model.ts',
         'src/game/fighter.ts', 'src/game/ai.ts', 'src/game/game.ts']

def find_root(value):
    if value:
        p=Path(value).expanduser().resolve()
    else:
        p=Path.cwd()
    candidates=[p, p/'web']
    for q in candidates:
        if (q.joinpath('src/game/roster.ts').exists() and q.joinpath('src/game/kits.ts').exists()):
            return q
    if not value:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root=tk.Tk(); root.withdraw()
            chosen=filedialog.askdirectory(title='Select Fight Royale folder (web or project root)')
            root.destroy()
            if chosen:
                return find_root(chosen)
        except Exception:
            pass
    fail('Fight Royale folder not found. Run from the web folder, or pass the project folder as an argument.')

def main():
    ap=argparse.ArgumentParser(description='Install Nesa, heart-shaped hammer and five matching icons')
    ap.add_argument('project', nargs='?', help='web folder or repository root')
    ap.add_argument('--check', action='store_true', help='dry-run only')
    args=ap.parse_args()
    root=find_root(args.project)
    print('Fight Royale project:', root)
    modifications={}
    for rel in FILES:
        path=root/rel
        if not path.is_file(): fail('missing '+str(path))
        before=path.read_text(encoding='utf-8')
        after=patch_all(rel,before)
        if after != before: modifications[rel]=after.encode('utf-8')
    for rel,data in ICONS.items():
        dest='public/icons/'+rel+'.webp'
        if not (root/dest).exists() or (root/dest).read_bytes()!=data:
            modifications[dest]=data
    print('Files to update:',len(modifications))
    for rel in modifications: print('  ',rel)
    if not modifications:
        print('Nesa is already installed. No changes made.')
        return
    if args.check:
        print('Dry-run successful. Nothing changed.')
        return
    backup=root/'.nesa_installer_backups'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True,exist_ok=False)
    # Backup every existing file before writing any new files.
    for rel in modifications:
        source=root/rel
        if source.exists():
            dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dst)
    committed=[]
    try:
        for rel,data in modifications.items():
            dest=root/rel; dest.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as temp:
                temp.write(data); temp_path=Path(temp.name)
            os.replace(temp_path,dest)
            committed.append(rel)
    except Exception:
        for rel in committed:
            dest=root/rel; saved=backup/rel
            if saved.exists(): shutil.copy2(saved,dest)
            elif dest.exists(): dest.unlink()
        raise
    print('Nesa Heart Hammer installed. Backup: ',backup)
    if not (root/'public/models/nesa.vrm').exists():
        print('NOTE: Place your VRoid model at public/models/nesa.vrm (not included).')
    if 'private beginKnockdown()' not in (root/'src/game/fighter.ts').read_text(encoding='utf-8'):
        print('NOTE: Install the earlier Knockdown/Wake-up update to get a floor fall on Z block.')
    print('Run: npx tsc --noEmit -p .  and npm run dev')

if __name__=='__main__':
    try: main()
    except (PatchError, OSError) as exc:
        print('INSTALL FAILED:',exc)
        sys.exit(1)
