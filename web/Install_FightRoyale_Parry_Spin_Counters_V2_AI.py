#!/usr/bin/env python3
"""
Fight Royale: FLASHY SPIN COUNTERS V2 + AGGRESSIVE COUNTER-SMART CPU (ALL fighters).

Self-contained V2 updater. Installs V1 prerequisites automatically if missing.
Also repairs the passive AI regression from Smart AI Defense V1 in place.
After a successful parry, a brief window opens; tapping basic attack performs a
fast spin/riposte unique to that fighter kit. CPU fighters also use it.

What this patch does
- Adds a universal hidden basic attack key `pc` (parry counter) for every kit.
- Successful parries now arm a short counter window on the defender.
- Basic attack during that window immediately casts the counter.
- AI will use the counter when in range.
- The old heavy parry stun is removed; attackers instead recoil briefly.
- Adds visual spin/turn overlays in the model for each kit.

Usage
  python Install_FightRoyale_Parry_Spin_Counters_V2_AI.py
  python Install_FightRoyale_Parry_Spin_Counters_V2_AI.py --check

Place this file in your Fight Royale project root (or inside the web folder) and run it.
No extra packages required.
"""
from __future__ import annotations
import argparse
import datetime as _dt
import re
import shutil
import sys
from pathlib import Path

MARKER = "FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V1"
V2_MARKER = "FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V2"
FILES = ["kits.ts", "fighter.ts", "model.ts", "ai.ts", "game.ts"]

class PatchError(RuntimeError):
    pass


def info(msg: str):
    print(msg)


def find_root(start: Path) -> Path:
    cands = [
        start,
        start / "web",
        start.parent,
        start.parent / "web",
        start.parent.parent,
        start.parent.parent / "web",
    ]
    for c in cands:
        if all((c / "src" / "game" / f).exists() for f in FILES):
            return c
    # broader fallback search
    for base in [start, *start.parents]:
        for p in [base, *base.iterdir()] if base.exists() and base.is_dir() else [base]:
            g = p / "src" / "game"
            if g.is_dir() and all((g / f).exists() for f in FILES):
                return p
    raise PatchError("Could not find project root containing src/game/{kits,fighter,model,ai,game}.ts")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8", newline="\n")


def backup(paths: list[Path]) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    bak = paths[0].parents[2] / f"backup_{V2_MARKER}_{stamp}"
    bak.mkdir(parents=True, exist_ok=False)
    for p in paths:
        rel = p.relative_to(paths[0].parents[2])
        dst = bak / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
    return bak


def insert_after(text: str, needle: str, insert: str, why: str) -> str:
    if insert.strip() in text:
        return text
    i = text.find(needle)
    if i < 0:
        raise PatchError(f"Could not find anchor for {why}")
    i += len(needle)
    return text[:i] + insert + text[i:]


def replace_once(text: str, old: str, new: str, why: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise PatchError(f"Could not find exact text for {why}")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, repl: str, why: str, flags: int = 0) -> str:
    if repl in text:
        return text
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        raise PatchError(f"Could not patch {why}")
    return new


def patch_kits(text: str) -> str:
    if MARKER in text:
        return text
    helper = r'''

// FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V1
function parryCounterAttack(kit: string, base: Record<string, Attack>): Attack {
  const light = base.l1 ?? DEFAULT as Attack;
  const heavy = base.heavy ?? light;
  const poses: Record<string, [string, string]> = {
    knight: [heavy.pose_w, heavy.pose_s],
    greatsword: [heavy.pose_w, heavy.pose_s],
    hammer: [heavy.pose_w, heavy.pose_s],
    katana: [heavy.pose_w, heavy.pose_s],
    bow: [base.z?.pose_w ?? light.pose_w, base.z?.pose_s ?? light.pose_s],
    mage: [base.z?.pose_w ?? light.pose_w, base.z?.pose_s ?? light.pose_s],
    knuckles: [heavy.pose_w, heavy.pose_s],
    kicks: [base.l2?.pose_w ?? light.pose_w, base.l2?.pose_s ?? light.pose_s],
    wind: [base.z?.pose_w ?? heavy.pose_w, base.z?.pose_s ?? heavy.pose_s],
    sickle: [heavy.pose_w, heavy.pose_s],
    chainblade: [heavy.pose_w, heavy.pose_s],
    glaive: [heavy.pose_w, heavy.pose_s],
    bomb: [base.z?.pose_w ?? light.pose_w, base.z?.pose_s ?? light.pose_s],
    assassin: [base.l2?.pose_w ?? light.pose_w, base.l2?.pose_s ?? light.pose_s],
  };
  const names: Record<string, string> = {
    knight: "Shield Riposte",
    greatsword: "Iron Reversal",
    hammer: "Heartbreaker Spin",
    katana: "Flash Recut",
    bow: "Snap Shot",
    mage: "Spell Reversal",
    knuckles: "Body Blow Return",
    kicks: "Whiplash Heel",
    wind: "Gale Wheel",
    sickle: "Crimson Counter",
    chainblade: "Chain Whiplash",
    glaive: "Tempest Return",
    bomb: "Spark Rebound",
    assassin: "Shadow Reversal",
  };
  const reach: Record<string, number> = {
    knight: 1.95, greatsword: 2.20, hammer: 2.35, katana: 2.00,
    bow: 1.90, mage: 2.00, knuckles: 1.60, kicks: 1.85,
    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40,
    bomb: 1.85, assassin: 1.85,
  };
  const lunge: Record<string, number> = {
    knight: 1.5, greatsword: 1.25, hammer: 1.35, katana: 1.8,
    bow: 1.2, mage: 1.15, knuckles: 1.65, kicks: 1.95,
    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8,
    bomb: 1.25, assassin: 2.2,
  };
  const knock: Record<string, number> = {
    knight: 4.2, greatsword: 4.9, hammer: 5.1, katana: 4.1,
    bow: 3.6, mage: 3.8, knuckles: 3.8, kicks: 4.0,
    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8,
    bomb: 3.8, assassin: 4.1,
  };
  const pose = poses[kit] ?? [light.pose_w, light.pose_s];
  return a({
    name: names[kit] ?? "Parry Counter",
    desc: "A fast one-hit riposte unlocked briefly after a successful parry.",
    wind: 0.40, active: 0.08, recover: 0.34,
    dmg: Math.round(light.dmg * 0.85 + heavy.dmg * 0.55),
    guard: Math.round(Math.max(light.guard, heavy.guard) * 0.95),
    reach: reach[kit] ?? Math.max(light.reach, 1.9),
    lunge: lunge[kit] ?? Math.max(light.lunge, 1.2),
    knock: knock[kit] ?? Math.max(light.knock, 3.1),
    stun: 0.22,
    heavy: true,
    pose_w: pose[0],
    pose_s: pose[1],
    style: "parry_counter",
    next: "",
    no_parry: false,
    parry_stun: 0,
  });
}
'''
    text = insert_after(text, 'const a = (d: Partial<Attack>): Attack => ({ ...DEFAULT, id: "", element: "", ...d }) as Attack;', helper, 'parry counter helper')

    anchor = '  // ZAREK_EFFECTIVE_RANGE_NERF_V1: hitboxes now match the smaller double-ended glaive.'
    if anchor in text and '  t.pc = parryCounterAttack(kit, t);\n' not in text:
        text = text.replace(anchor, '  t.pc = parryCounterAttack(kit, t);\n' + anchor, 1)
    elif '  t.v = bonusSkill(kit, element);' in text and '  t.pc = parryCounterAttack(kit, t);' not in text:
        text = text.replace('  t.v = bonusSkill(kit, element);', '  t.v = bonusSkill(kit, element);\n  t.pc = parryCounterAttack(kit, t);', 1)
    else:
        raise PatchError('Could not place kits parry counter attack assignment')
    return text


def patch_fighter(text: str) -> str:
    if MARKER in text:
        return text
    text = insert_after(text,
        '  perfectDodgeCounterT = 0; // one successful melee riposte, expires after 0.95s\n',
        '  parryCounterT = 0; // brief follow-up window after a successful parry\n  private parryCounterTarget: Entity | null = null;\n',
        'parry counter fields')

    text = insert_after(text,
        '  private tempestSpin = 0;\n',
        '  /** Visual-only spin amount for the new universal parry counter. */\n  private parryCounterSpin = 0;\n',
        'parry counter spin field')

    method_block = r'''
  armParryCounter(target: Entity | null) {
    this.parryCounterT = 0.75;
    this.parryCounterTarget = target && target.team !== this.team && !target.isDown() ? target : null;
  }
  hasParryCounterReady() { return this.parryCounterT > 0; }
  parryCounterReach() { return (this.attacks.pc ?? this.attacks.l1).reach; }
  private actionPoseTag() {
    if (this.atkId === "pc" && this.atk?.style === "parry_counter")
      return `pc_${this.kit}_${this.atkPhase === 0 ? "w" : "s"}`;
    return this.poseName;
  }
'''
    text = insert_after(text, '  private knock = 0;\n', method_block, 'parry counter methods')

    text = replace_once(text,
        '    this.perfectDodgeCounterT = Math.max(0, this.perfectDodgeCounterT - dt);\n',
        '    this.perfectDodgeCounterT = Math.max(0, this.perfectDodgeCounterT - dt);\n    this.parryCounterT = Math.max(0, this.parryCounterT - dt);\n',
        'parry counter timer')

    text = replace_once(text,
        '  private requestLight() {\n    if (this.state === S.IDLE || this.state === S.BLOCK) this.startAttack(this.comboTimer > 0 ? this.comboNext : "l1");\n    else if (this.state === S.ATTACK && this.atk && this.atk.next) this.buffered = true;\n  }\n',
        '  private requestLight() {\n    if (this.parryCounterT > 0 && this.onGround && (this.state === S.IDLE || this.state === S.BLOCK)) {\n      this.startAttack("pc");\n      return;\n    }\n    if (this.state === S.IDLE || this.state === S.BLOCK) this.startAttack(this.comboTimer > 0 ? this.comboNext : "l1");\n    else if (this.state === S.ATTACK && this.atk && this.atk.next) this.buffered = true;\n  }\n',
        'requestLight parry counter')

    text = replace_once(text,
        '    if (pressed && this.kit === "glaive" && this.state === S.ATTACK &&\n        this.atkId === "l4" && this.atk?.next === "l5") this.buffered = true;\n',
        '    if (pressed && this.kit === "glaive" && this.state === S.ATTACK &&\n        this.atkId === "l4" && this.atk?.next === "l5") this.buffered = true;\n    if (pressed && this.parryCounterT > 0 && this.onGround && (this.state === S.IDLE || this.state === S.BLOCK)) {\n      this.holding = false;\n      this.startAttack("pc");\n      return;\n    }\n',
        'readAttack parry counter')

    text = insert_after(text,
        '  private startAttack(id: string) {\n',
        '    if (id === "pc" && this.parryCounterTarget && !this.parryCounterTarget.isDown()) {\n      const aim = this.parryCounterTarget.root.position.clone().sub(this.root.position);\n      if (this.stage) {\n        const dx = Math.sign(aim.x);\n        if (dx) this.facing = dx;\n      } else if (aim.lengthSq() > 0.0001) {\n        this.root.rotation.y = Math.atan2(aim.x, aim.z);\n      }\n    }\n',
        'startAttack counter facing')

    text = replace_once(text,
        '    this.atk = this.attacks[id];\n',
        '    this.atk = this.attacks[id];\n    if (id === "pc") { this.parryCounterT = 0; this.parryCounterTarget = null; }\n',
        'startAttack consume counter window')

    # calculate model spin and push it to the model
    text = replace_once(text,
        '    this.cycloneSpin = cycloneActive ? Math.PI * 4 * (cyclonePhase * cyclonePhase * (3 - 2 * cyclonePhase)) : 0;\n',
        '    this.cycloneSpin = cycloneActive ? Math.PI * 4 * (cyclonePhase * cyclonePhase * (3 - 2 * cyclonePhase)) : 0;\n    const parryCounterActive = this.state === S.ATTACK && this.atkId === "pc" && this.atk?.style === "parry_counter";\n    const parryCounterPhase = parryCounterActive ? Math.max(0, Math.min(1, this.stateT / Math.max((this.atk?.wind ?? 0.4) + (this.atk?.active ?? 0.08), 0.01))) : 0;\n    this.parryCounterSpin = parryCounterActive ? Math.PI * 2 * (parryCounterPhase * parryCounterPhase * (3 - 2 * parryCounterPhase)) : 0;\n    this.model.parryCounterSpin = this.parryCounterSpin;\n',
        'counter spin calc')

    text = text.replace(', this.poseName);', ', this.actionPoseTag());')

    # clear ready-state on revive / ko
    revive_pat = r'(  revive\(frac: number\) \{[\s\S]*?    this\.model\.nesaSpinHorizontal = 0;\n)'
    revive_add = r'\1    this.parryCounterT = 0; this.parryCounterTarget = null; this.parryCounterSpin = 0;\n    this.model.parryCounterSpin = 0;\n'
    text = sub_once(text, revive_pat, revive_add, 'revive parry-counter reset', flags=re.M)
    ko_pat = r'(  ko\(\) \{[\s\S]*?    this\.model\.nesaSpinHorizontal = 0;\n)'
    ko_add = r'\1    this.parryCounterT = 0; this.parryCounterTarget = null; this.parryCounterSpin = 0;\n    this.model.parryCounterSpin = 0;\n'
    text = sub_once(text, ko_pat, ko_add, 'ko parry-counter reset', flags=re.M)

    # Append marker near file header.
    if MARKER not in text:
        text = '// ' + MARKER + '\n' + text
    return text


def patch_model(text: str) -> str:
    if MARKER in text:
        return text
    text = insert_after(text,
        '  nesaSpinHorizontal = 0;\n',
        '  parryCounterSpin = 0;\n',
        'model parry counter spin field')

    overlay = r'''
    if (actionPose.startsWith("pc_")) {
      const phase = THREE.MathUtils.clamp(Math.abs(this.parryCounterSpin) / (Math.PI * 2), 0, 1);
      const turn = this.parryCounterSpin;
      const snap = Math.sin(phase * Math.PI);
      switch (this.kit) {
        case "knight":
          this.torso.rotation.y += turn * 0.18;
          this.torso.rotation.x += 0.06 * snap;
          this.arm_r.rotation.x += 0.22 + 0.08 * snap;
          this.arm_r.rotation.z -= 0.16;
          this.hand_r.rotation.z -= 0.22;
          this.arm_l.rotation.x -= 0.10;
          this.cape.rotation.z += Math.sin(turn) * 0.10;
          break;
        case "greatsword":
          this.torso.rotation.y += turn * 0.22;
          this.torso.rotation.x += 0.08 * snap;
          this.arm_r.rotation.x += 0.24;
          this.arm_l.rotation.x += 0.18;
          this.hand_r.rotation.z -= 0.26;
          break;
        case "hammer":
          this.torso.rotation.y += turn * 0.23;
          this.torso.rotation.x += 0.10 * snap;
          this.arm_r.rotation.x += 0.26;
          this.arm_l.rotation.x += 0.16;
          this.hand_r.rotation.z -= 0.20;
          this.cape.rotation.z += Math.sin(turn) * 0.06;
          break;
        case "katana":
          this.torso.rotation.y += turn * 0.21;
          this.torso.rotation.x += 0.03 * snap;
          this.arm_r.rotation.x += 0.18;
          this.hand_r.rotation.z -= 0.28;
          this.arm_l.rotation.x -= 0.05;
          break;
        case "assassin":
          this.torso.rotation.y += turn * 0.28;
          this.torso.rotation.x += 0.05 * snap;
          this.head.rotation.y -= turn * 0.10;
          this.arm_r.rotation.x += 0.12;
          this.arm_l.rotation.z += 0.18;
          break;
        case "knuckles":
          this.torso.rotation.y += turn * 0.30;
          this.torso.rotation.x += 0.04 * snap;
          this.arm_r.rotation.x += 0.20;
          this.arm_l.rotation.x += 0.12;
          this.arm_r.rotation.z -= 0.10;
          this.arm_l.rotation.z += 0.10;
          break;
        case "kicks":
          this.torso.rotation.y += turn * 0.55;
          this.torso.rotation.x += 0.05 * snap;
          this.leg_r.rotation.x -= 0.30 * snap;
          this.leg_r.rotation.z -= 0.24;
          this.leg_l.rotation.x += 0.12;
          this.arm_r.rotation.z -= 0.18;
          this.arm_l.rotation.z += 0.18;
          break;
        case "wind":
          this.torso.rotation.y += turn * 0.33;
          this.torso.rotation.x += 0.04 * snap;
          this.arm_r.rotation.x += 0.12;
          this.arm_l.rotation.x += 0.08;
          this.head.rotation.y -= turn * 0.06;
          break;
        case "sickle":
          this.torso.rotation.y += turn * 0.24;
          this.torso.rotation.x += 0.05 * snap;
          this.arm_r.rotation.x += 0.18;
          this.hand_r.rotation.z -= 0.24;
          this.arm_l.rotation.x -= 0.04;
          break;
        case "chainblade":
          this.torso.rotation.y += turn * 0.23;
          this.torso.rotation.x += 0.06 * snap;
          this.arm_r.rotation.x += 0.18;
          this.arm_l.rotation.x += 0.10;
          this.hand_r.rotation.z -= 0.18;
          break;
        case "glaive":
          this.torso.rotation.y += turn * 0.22;
          this.torso.rotation.x += 0.05 * snap;
          this.arm_r.rotation.x += 0.16;
          this.arm_l.rotation.x += 0.08;
          if (this.glaivePivot) this.glaivePivot.rotation.z += Math.sin(turn) * 0.10;
          break;
        case "mage":
          this.torso.rotation.y += turn * 0.16;
          this.torso.rotation.x += 0.02 * snap;
          this.arm_r.rotation.x += 0.10;
          this.hand_r.rotation.z -= 0.20;
          this.arm_l.rotation.z += 0.08;
          break;
        case "bow":
          this.torso.rotation.y += turn * 0.18;
          this.torso.rotation.x += 0.02 * snap;
          this.arm_r.rotation.x += 0.06;
          this.arm_l.rotation.x += 0.10;
          this.head.rotation.y -= turn * 0.08;
          break;
        case "bomb":
          this.torso.rotation.y += turn * 0.17;
          this.torso.rotation.x += 0.03 * snap;
          this.arm_r.rotation.x += 0.12;
          this.arm_l.rotation.z += 0.10;
          break;
      }
    }
'''
    text = insert_after(text,
        '    this.hips.position.y += Math.abs(s) * 0.018 * running;\n',
        overlay,
        'parry counter visual overlay')
    text = '// ' + MARKER + '\n' + text
    return text


def patch_ai(text: str) -> str:
    if MARKER in text:
        return text
    block = r'''
    if (f.hasParryCounterReady() && [S.IDLE, S.BLOCK].includes(f.state)) {
      const gap = f.root.position.clone().setY(0)
        .distanceTo(o.root.position.clone().setY(0));
      if (gap <= f.parryCounterReach() + 0.75) {
        f.intent.move.set(0, 0, 0);
        f.intent.block = false;
        f.intent.attack = true;
        this.queue = [];
        this.hold = 0;
        return;
      }
    }
'''
    text = insert_after(text, '    const o = f.opponent as Fighter | null;\n    if (!o || o.isDown()) return;\n', block, 'AI parry counter usage')
    text = '// ' + MARKER + '\n' + text
    return text


def patch_game(text: str) -> str:
    if MARKER in text:
        return text
    repl = r'''      case "parry": {
        const df = d as Fighter;
        this.fxp("impactBurst", shieldPos, "#b9f5ff", 1.65, "clash");
        this.fxp("impactFrame", "parry", "#b9f5ff", 0.72);
        if (attacker instanceof Fighter) {
          if (attacker.onComboParried()) {
            this.delayComboFollowups(attacker, 0.20);
            this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)),
              "COMBO -10% • +0.2s", "#b8eaff", 0.82);
          }
          if (!ranged) attacker.stagger(0.50);
          else attacker.model.recoil = Math.max(attacker.model.recoil, 0.35);
          df.armParryCounter(attacker);
          this.fxp("num", df.chest().add(new THREE.Vector3(0, 0.95, 0)),
            "COUNTER READY", "#ffd0f5", 0.95);
        } else if (!ranged && attacker instanceof Mob) attacker.receiveHit(d, { ...a, dmg: 0, knock: 4 }, 0);
        this.snd("parry", 0.9);
        if (!ranged && a.type === "melee")
          this.fxp("clashBurst", shieldPos, "#aee9ff", 1.15);
        this.fxp("sparks", shieldPos, "#aee9ff", 40, 9);
        this.fxp("flash", shieldPos, "#b3f2ff", 0.5, 0.2, 0.9);
        this.fxp("ring", shieldPos, "#b3f2ff", 0.8, 0.35, 0.9);
        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.5, 0)), "PARRY!", "#8fe6ff", 1.4);
        this.add_trauma(0.28);
        this.hitStop(0.08, 0.10);
        break;
      }
\2'''
    text = sub_once(text, r'(\s*case "parry":\s*[\s\S]*?\n\s*break;\n)(\s*case "counter":)', repl, 'game parry resolution', flags=re.M)
    text = '// ' + MARKER + '\n' + text
    return text



def patch_v2_kits(text: str) -> str:
    if V2_MARKER in text:
        return text
    # Unique names for kit-sharing fighters (Aster/Vesper and the three mages).
    text = replace_once(text,
        'function parryCounterAttack(kit: string, base: Record<string, Attack>): Attack {',
        'function parryCounterAttack(kit: string, element: string, base: Record<string, Attack>): Attack {',
        'element-specific counter names')
    text = replace_once(text,
        '  t.pc = parryCounterAttack(kit, t);',
        '  t.pc = parryCounterAttack(kit, element, t);',
        'element argument')
    names = {
        'Shield Riposte': 'Royal Crescent',
        'Iron Reversal': "Titan's Reversal",
        'Heartbreaker Spin': 'Heartbreaker Twirl',
        'Flash Recut': 'Sakura Reversal',
        'Snap Shot': 'Scarlet Revolver',
        'Body Blow Return': 'Iron Tornado',
        'Whiplash Heel': 'Cyclone Roundhouse',
        'Gale Wheel': 'Tempest Reversal',
        'Crimson Counter': "Reaper's Waltz",
        'Chain Whiplash': 'Chain Cyclone',
        'Tempest Return': 'Thunderwheel',
        'Spark Rebound': 'Firecracker Spin',
        'Shadow Reversal': 'Shadow Carousel',
    }
    for old_name, new_name in names.items():
        text = replace_once(text, f'"{old_name}"', f'"{new_name}"', f'{new_name} title')
    name_expression = """    name: kit === "mage" ? (element === "fire" ? "Inferno Twirl" :
      element === "water" ? "Tidal Pirouette" : "Witch's Spiral") :
      kit === "knight" && element !== "light" ? "Crimson Waltz" :
      (names[kit] ?? "Parry Counter"),"""
    text = replace_once(text,
        '    name: names[kit] ?? "Parry Counter",',
        name_expression,
        'unique 17 fighter names')
    # Damage is stronger than V1, but one hit, one event, normal guard/parry/dodge.
    text = replace_once(text,
        '    dmg: Math.round(light.dmg * 0.85 + heavy.dmg * 0.55),',
        '    dmg: Math.round((light.dmg * 0.85 + heavy.dmg * 0.55) * 1.24),',
        'counter damage strength')
    text = replace_once(text,
        '    guard: Math.round(Math.max(light.guard, heavy.guard) * 0.95),',
        '    guard: Math.round(Math.max(light.guard, heavy.guard) * 1.12),',
        'counter guard strength')
    # Keep the hit exactly 0.40 sec from cast, with a non-spammable recovery.
    text = replace_once(text,
        '    wind: 0.40, active: 0.08, recover: 0.34,',
        '    wind: 0.40, active: 0.08, recover: 0.38,',
        'counter recovery')
    return '// ' + V2_MARKER + '\n' + text


def patch_v2_fighter(text: str) -> str:
    if V2_MARKER in text:
        return text
    text = insert_after(text,
        '  private parryCounterTarget: Entity | null = null;\n',
        '  private parryCounterPendingDepth = 0;\n  parryCounterDepth = 0;\n'
        '  parryRecoilT = 0; // 0.5s recoil limits offense but never causes hard stun\n'
        '  private counterVisualRemote = false;\n',
        'counter chain/recoil fields')
    text = replace_once(text,
'''  armParryCounter(target: Entity | null) {
    this.parryCounterT = 0.75;
    this.parryCounterTarget = target && target.team !== this.team && !target.isDown() ? target : null;
  }
  hasParryCounterReady() { return this.parryCounterT > 0; }
  parryCounterReach() { return (this.attacks.pc ?? this.attacks.l1).reach; }
''',
'''  armParryCounter(target: Entity | null, depth = 0) {
    // Two counter-parries are enough: prevent infinite counter-on-counter loops.
    if (depth > 2) { this.parryCounterT = 0; this.parryCounterTarget = null; return; }
    this.parryCounterT = 0.75;
    this.parryCounterTarget = target && target.team !== this.team && !target.isDown() ? target : null;
    this.parryCounterPendingDepth = depth;
  }
  hasParryCounterReady() { return this.parryCounterT > 0; }
  parryCounterReach() { return (this.attacks.pc ?? this.attacks.l1).reach; }
  tryParryCounter(): boolean {
    // Same legal rules for a human basic-attack tap and an AI counter decision.
    if (!this.hasParryCounterReady() || !this.onGround || ![S.IDLE, S.BLOCK].includes(this.state) ||
        this.chainBindT > 0 || !!this.chainBoundBy || this.parryRecoilT > 0) return false;
    this.holding = false;
    this.startAttack("pc");
    return this.atkId === "pc" && this.state === S.ATTACK;
  }
  applyParryRecoil(seconds = 0.5) {
    // This is NOT S.STAGGER/HITSTUN: the attacker can evade, reposition or block.
    this.parryRecoilT = Math.max(this.parryRecoilT, seconds);
    this.model.recoil = Math.max(this.model.recoil, 0.85);
    this.holding = false;
    this.buffered = false;
    if (this.state === S.ATTACK && !this.isContinuousComboActive()) {
      this.finishAttack();
      this.setState(S.IDLE);
    }
  }
''',
        'parry counter state machine')
    text = replace_once(text,
'''  private actionPoseTag() {
    if (this.atkId === "pc" && this.atk?.style === "parry_counter")
      return `pc_${this.kit}_${this.atkPhase === 0 ? "w" : "s"}`;
    return this.poseName;
  }
''',
'''  private actionPoseTag() {
    if (this.counterVisualRemote || (this.atkId === "pc" && this.atk?.style === "parry_counter"))
      return `pc_${this.kit}_${this.stateT < 0.40 ? "w" : "s"}`;
    return this.poseName;
  }
''', 'online/host spin pose tag')
    text = insert_after(text,
        '    this.parryCounterT = Math.max(0, this.parryCounterT - dt);\n',
        '    this.parryRecoilT = Math.max(0, this.parryRecoilT - dt);\n'
        '    if (this.parryRecoilT > 0) this.model.recoil = Math.max(this.model.recoil, 0.23 + 0.35 * this.parryRecoilT);\n',
        'recoil tick')
    # Previously a held basic input or attack-lock could suppress the legal parry counter.
    text = replace_once(text,
        '    if (pressed && this.atkLock > 0) return;',
        '    if (pressed && this.atkLock > 0 && !this.hasParryCounterReady()) return;',
        'parry overrides ranged combo cooldown')
    text = insert_after(text,
        '    if (pressed && this.atkLock > 0 && !this.hasParryCounterReady()) return;\n',
        '    if (pressed && this.parryRecoilT > 0) return;\n',
        'attacker cannot immediately attack through recoil')
    text = replace_once(text,
        '  private requestLight() {\n    if (this.parryCounterT > 0 && this.onGround && (this.state === S.IDLE || this.state === S.BLOCK)) {\n      this.startAttack("pc");\n      return;\n    }',
        '  private requestLight() {\n    if (this.parryRecoilT > 0) return;\n    if (this.tryParryCounter()) return;',
        'human counter press')
    text = replace_once(text,
        '    if (pressed && this.parryCounterT > 0 && this.onGround && (this.state === S.IDLE || this.state === S.BLOCK)) {\n      this.holding = false;\n      this.startAttack("pc");\n      return;\n    }',
        '    if (pressed && this.tryParryCounter()) return;',
        'quick immediate tap counter')
    text = insert_after(text,
        '  private readSkill() {\n',
        '    if (this.parryRecoilT > 0) return;\n',
        'recoil skill lock')
    text = replace_once(text,
        '    if (id === "pc") { this.parryCounterT = 0; this.parryCounterTarget = null; }',
        '    if (id === "pc") {\n      this.parryCounterDepth = this.parryCounterPendingDepth;\n      this.parryCounterT = 0; this.parryCounterTarget = null;\n    }',
        'counter depth on cast')
    text = replace_once(text,
        'this.stateT / Math.max((this.atk?.wind ?? 0.4) + (this.atk?.active ?? 0.08), 0.01)',
        'this.stateT / Math.max(this.atk?.wind ?? 0.4, 0.01)',
        'full revolution completes at 0.4s impact')
    text = replace_once(text,
        '(attack?.style === "nesa_spin" || attack?.style === "nesa_air_spin") ?\n        THREE.MathUtils.clamp',
        '(attack?.style === "nesa_spin" || attack?.style === "nesa_air_spin" || attack?.style === "parry_counter") ?\n        THREE.MathUtils.clamp',
        'Nesa hammer levels during the riposte')
    text = replace_once(text,
        'this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw + this.nesaSpinYaw;',
        'this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw + this.nesaSpinYaw + this.parryCounterSpin;',
        'host full-body model spin')
    text = replace_once(text,
        'this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw + this.nesaSpinYaw;',
        'this.viewBias + this.tempestSpin + this.cycloneSpin + this.bladeSwingYaw + this.nesaSpinYaw + this.parryCounterSpin;',
        'puppet full-body model spin')
    # Synchronize actual spin and visual-tag to network puppets without changing old indices.
    text = replace_once(text,
        'this.nesaCCharges, +this.nesaCRechargeT.toFixed(2), +this.model.nesaSpinHorizontal.toFixed(2)];',
        'this.nesaCCharges, +this.nesaCRechargeT.toFixed(2), +this.model.nesaSpinHorizontal.toFixed(2),\n'
        '      +this.parryCounterSpin.toFixed(3), this.atkId === "pc" ? 1 : 0];',
        'host counter spin networking')
    text = insert_after(text,
        '    this.model.nesaSpinHorizontal = s.length > 46 ? s[46] : 0;\n',
        '    this.parryCounterSpin = s.length > 47 ? s[47] : 0;\n'
        '    this.model.parryCounterSpin = this.parryCounterSpin;\n'
        '    this.counterVisualRemote = s.length > 48 && s[48] === 1;\n',
        'remote counter animation networking')
    # Reset on revive and KO, no per-round carryover.
    text = text.replace('    this.model.parryCounterSpin = 0;\n',
        '    this.model.parryCounterSpin = 0;\n'
        '    this.parryRecoilT = 0; this.parryCounterPendingDepth = 0; this.parryCounterDepth = 0; this.counterVisualRemote = false;\n')
    return '// ' + V2_MARKER + '\n' + text


def patch_v2_model(text: str) -> str:
    if V2_MARKER in text:
        return text
    # V1's character-specific arm/leg poses remain in place. V2 rotates the actual
    # whole model from fighter.ts rather than only bending torso bones.
    # These local offsets add readable follow-through without new hit detection.
    text = replace_once(text,
        '      const turn = this.parryCounterSpin;',
        '      const turn = Math.sin(this.parryCounterSpin) * 0.68;',
        'small torso twist while full model spins')
    text = replace_once(text,
        '          this.leg_r.rotation.z -= 0.24;',
        '          this.leg_r.rotation.z -= 0.62;',
        'Kira full extended roundhouse')
    text = replace_once(text,
        '          this.arm_l.rotation.z += 0.18;',
        '          this.arm_l.rotation.z += 0.34;',
        'Nyx dagger crosscut')
    text = insert_after(text,
        '    this.hairSway.forEach((h, i) => { h.rotation.x = 0.1 * this.walk + 0.25 * this.recoil + Math.sin(this.t * 2 + i) * 0.05; });\n',
        '    if (actionPose.startsWith("pc_")) {\n'
        '      const turn = this.parryCounterSpin;\n'
        '      const follow = Math.sin(Math.min(1, turn / (Math.PI * 2)) * Math.PI);\n'
        '      this.cape.rotation.y += Math.sin(turn - 0.65) * 0.20 * follow;\n'
        '      this.hairSway.forEach((h, i) => { h.rotation.z += Math.sin(turn - 0.35 + i * 0.42) * 0.13 * follow; });\n'
        '    }\n',
        'hair/cape late follow-through')
    return '// ' + V2_MARKER + '\n' + text


def patch_v2_ai(text: str) -> str:
    if V2_MARKER in text:
        return text
    # Integrate into AI Personality 2.0, as well as the simpler original AI.
    text = insert_after(text,
        '  private ignitionChoices = new Map<number, boolean>();\n',
'''  // FIGHT_ROYALE_PARRY_SPIN_COUNTERS_V2: CPUs deliberately use and defend counters.
  private counterSeen = false;
  private counterWant = false;
  private counterReactT = 0;
  private incomingCounterSeen = -1;
  private incomingCounterReactT = 0;
  private incomingCounterEvade = false;
''', 'AI counter learning state')
    method = '''
  /** Read actual parry rewards, not an AI-only counter move or free hit. */
  private spinCounterResponse(f: Fighter, o: Fighter, dt: number): boolean {
    if (!f.hasParryCounterReady()) {
      this.counterSeen = false;
      this.counterWant = false;
      this.counterReactT = 0;
      return false;
    }
    if (!this.counterSeen) {
      this.counterSeen = true;
      // Personality and difficulty affect whether a CPU confidently commits.
      const fighter = f.look.name.toLowerCase();
      const bold = ["kira", "nyx", "vesper", "rook", "zarek", "veyr", "kaizen", "nesa"].includes(fighter);
      const caution = f.guard < f.maxGuard * 0.20;
      const chance = this.p.parry <= 0 ? 0.35 : this.p.parry < 0.10 ? 0.64 :
        this.p.parry < 0.20 ? 0.83 : 0.97;
      this.counterWant = Math.random() < Math.min(0.98, chance + (bold ? 0.08 : 0) - (caution ? 0.10 : 0));
      this.counterReactT = rand(this.p.react[0], this.p.react[1]) * (bold ? 0.42 : 0.58);
    }
    this.counterReactT = Math.max(0, this.counterReactT - dt);
    if (!this.counterWant || this.counterReactT > 0 || !f.onGround ||
        (f.state !== S.BLOCK && f.state !== S.IDLE)) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    if (gap > f.parryCounterReach() + 0.55) {
      // The defender can chase but cannot spawn a hit outside its actual reach.
      if (gap < f.parryCounterReach() + 2.4 && f.state === S.IDLE) {
        const dir = o.root.position.clone().sub(f.root.position).setY(0).normalize();
        if (f.stage) dir.set(Math.sign(dir.x), 0, 0);
        f.intent.move.copy(dir);
      }
      return false;
    }
    if (o.invulnT > 0 || o.knockedDown()) return false;
    // Shared exact action as player LMB: respect real state, recoil and cast rules.
    if (!f.tryParryCounter()) return false;
    this.queue = []; this.hold = 0;
    this.blockWait = -1; this.blockDur = 0; this.blockHold = 0;
    this.comboParryTarget = -1;
    this.theaterFollow = "";
    this.theaterT = 0;
    f.intent.block = false;
    f.intent.attack = false; // no stuck attack held for the next animation
    f.intent.skill = "";
    f.intent.move.set(0, 0, 0);
    this.counterWant = false;
    return true;
  }

  /** Recognize an enemy spin counter's 0.4s wind-up and take real defensive action. */
  private counterThreatDefense(f: Fighter, o: Fighter, dt: number): boolean {
    const a = o.atk;
    if (o.state !== S.ATTACK || o.atkId !== "pc" || a?.style !== "parry_counter") {
      this.incomingCounterSeen = -1;
      return false;
    }
    if (o.swingSerial !== this.incomingCounterSeen) {
      this.incomingCounterSeen = o.swingSerial;
      this.incomingCounterReactT = rand(this.p.react[0], this.p.react[1]);
      this.incomingCounterEvade = Math.random() < (0.22 + this.p.block * 0.55);
    }
    this.incomingCounterReactT -= dt;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const eta = a.wind - o.stateT;
    if (eta <= 0 || this.incomingCounterReactT > 0 ||
        gap > a.reach + 0.60 || f.isDown() || !f.onGround ||
        ![S.IDLE, S.BLOCK].includes(f.state)) return false;
    const away = f.root.position.clone().sub(o.root.position).setY(0);
    if (away.lengthSq() < 0.0001) away.set(f.id % 2 ? 1 : -1, 0, 0);
    away.normalize();
    if (f.stage) away.set(Math.sign(away.x) || 1, 0, 0);
    if (this.incomingCounterEvade && f.dashCd <= 0 && eta > 0.10) {
      const at = f.root.position.clone().setY(0);
      let dir = away;
      if (!f.stage) {
        const flank = new THREE.Vector3(-away.z, 0, away.x);
        const cap = Math.max(1.0, f.arenaRadius - f.radius - 0.24);
        const tryFlank = at.clone().addScaledVector(flank, 2.8).length() < cap ? flank : flank.negate();
        if (at.clone().addScaledVector(tryFlank, 2.8).length() < cap) dir = tryFlank;
      }
      f.intent.dash.copy(dir);
      f.intent.move.copy(dir);
      f.intent.block = false;
    } else {
      // Shield if there is time, never invoke an impossible instant parry.
      f.intent.block = true;
      f.intent.move.set(0, 0, 0);
    }
    this.blockWait = -1; this.blockHold = 0;
    this.queue = []; this.hold = 0;
    f.intent.skill = "";
    f.intent.attack = false;
    return true;
  }
'''
    # Insert methods directly before the AiBrain constructor (works on all tested builds).
    if '  constructor(private threats: Threats, level: number) {' not in text:
        raise PatchError('AI constructor anchor for counter methods not found')
    text = text.replace('  constructor(private threats: Threats, level: number) {',
                        method + '\n  constructor(private threats: Threats, level: number) {', 1)

    # V1 AI used a pressed attack flag that could stay held; remove that block.
    old = '''    if (f.hasParryCounterReady() && [S.IDLE, S.BLOCK].includes(f.state)) {
      const gap = f.root.position.clone().setY(0)
        .distanceTo(o.root.position.clone().setY(0));
      if (gap <= f.parryCounterReach() + 0.75) {
        f.intent.move.set(0, 0, 0);
        f.intent.block = false;
        f.intent.attack = true;
        this.queue = [];
        this.hold = 0;
        return;
      }
    }
'''
    if old not in text:
        raise PatchError('Could not find old V1 AI counter block')
    text = text.replace(old,
       '    if (this.spinCounterResponse(f, o, dt)) return;\n'
       '    if (this.counterThreatDefense(f, o, dt)) return;\n', 1)
    return '// ' + V2_MARKER + '\n' + text


def patch_v2_game(text: str) -> str:
    if V2_MARKER in text:
        return text
    # V1 accidentally emitted break + case on one line. Fix formatting while editing.
    text = replace_once(text, '        break;      case "parry": {',
        '        break;\n      case "parry": {', 'case parry newline')
    text = replace_once(text,
        '          if (!ranged) attacker.stagger(0.50);\n          else attacker.model.recoil = Math.max(attacker.model.recoil, 0.35);\n          df.armParryCounter(attacker);',
        '          if (!ranged && a.type === "melee") attacker.applyParryRecoil(0.50);\n'
        '          else attacker.model.recoil = Math.max(attacker.model.recoil, 0.35);\n'
        '          df.armParryCounter(attacker, attacker.atkId === "pc" ? attacker.parryCounterDepth + 1 : 0);',
        'non-stunning 0.5s recoil and counter chain cap')
    text = insert_after(text,
        '    this.swingSound(f, a);\n',
'''    if (a.style === "parry_counter") {
      // One real hit at the 0.40s contact frame, not an AOE or repeated spin ticks.
      const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
      this.fxp("slashes", tip, f.look.glow);
      this.fxp("ring", tip, f.look.glow, 0.86, 0.28, 0.78);
      this.fxp("sparks", tip, f.look.glow, 22, 6);
      this.fxp("flash", tip, f.look.glow, 0.32, 0.12, 0.78);
      this.fxp("num", f.chest().add(new THREE.Vector3(0, 0.75, 0)), "SPIN COUNTER!", f.look.glow, 0.90);
      this.snd("whoosh_light", 0.55);
      this.melee(f, a);
      return;
    }
''', 'special counter impact choreography')
    text = insert_after(text,
        '    const directionalAir = !f.stage && f.atkId === "air_l1";\n',
'''    // A visual 360 turn never means 360-degree damage or multiple targets.
    // Counter attacks select only the closest actual enemy and use normal melee tests.
    const counterTarget = a.style === "parry_counter"
      ? this.enemiesOf(f).filter(d => !d.isDown()).sort((x, y) =>
          x.root.position.distanceToSquared(f.root.position) -
          y.root.position.distanceToSquared(f.root.position))[0] ?? null : null;
''', 'only one physical opponent hit')
    melee_index = text.find('  private melee(f: Fighter, a: Attack): boolean {')
    if melee_index < 0:
        raise PatchError('Cannot locate melee attack resolver')
    before_melee, melee_body = text[:melee_index], text[melee_index:]
    melee_body = insert_after(melee_body,
        '    for (const d of this.enemiesOf(f)) {\n',
        '      if (a.style === "parry_counter" && d !== counterTarget) continue;\n',
        'only one target loop')
    text = before_melee + melee_body
    return '// ' + V2_MARKER + '\n' + text



DEFENSE_V1 = "FIGHT_ROYALE_AI_GUARD_TIMING_PARRY_V1_20261107"
DEFENSE_FIXED = "FIGHT_ROYALE_AI_DEFENSE_AGGRESSION_REPAIR_V2"
LEGACY_REACT = '  private react(f: Fighter, o: Fighter) {\n    if (o.state === S.ATTACK && o.atkPhase === 0 && o.atk?.type === "melee" && o.swingSerial !== this.seenSwing) {\n      this.seenSwing = o.swingSerial;\n      if (f.state === S.HITSTUN || f.state === S.STAGGER) return;\n      const tth = o.atk.wind - o.stateT;\n      const r = Math.random();\n      const bc = this.p.block * (o.atk.heavy ? 0.75 : 1);\n      const festival = o.kit === "sickle" && o.bloodFestivalT > 0;\n      const guardLow = f.guard <= f.maxGuard * 0.32;\n      const dist = f.root.position.distanceTo(o.root.position);\n      const canClash = f.state === S.IDLE && f.onGround && f.attacks.l1?.type === "melee" &&\n        dist < (f.attacks.l1.reach + 0.35);\n      // Zarek deliberately meets a real enemy blade occasionally to earn Clash Momentum.\n      // Unlike a forced clash this is a normal light input with genuine wind-up timing.\n      if (f.kit === "glaive" && f.onGround && f.state === S.IDLE &&\n          o.atk?.type === "melee" && !o.atk.no_parry &&\n          dist < f.attacks.l1.reach + 0.15 && tth >= f.attacks.l1.wind * 0.50 &&\n          this.seenClashSwing !== o.swingSerial &&\n          Math.random() < this.p.block * (f.clashMomentum < 3 ? 0.58 : 0.33)) {\n        this.seenClashSwing = o.swingSerial;\n        this.blockWait = -1; this.blockHold = 0;\n        this.queue = [[0, 0.065]]; this.hold = 0;\n        return;\n      }\n      // Guard critical / recently guard-broken: a timed attack can CLASH with a melee\n      // swing. A fully staggered fighter must recover before trying. No special AI-only clash.\n      if (guardLow && canClash) {\n        this.blockWait = -1; this.blockHold = 0;\n        this.queue = [[0, 0.06]]; this.hold = 0;\n        return;\n      }\n      if (festival || (o.atk?.no_parry && !o.isContinuousComboActive())) {\n        // Perfect parry cannot stop Veyr\'s festival melee. Block EARLY (regular guard),\n        // or evade when guard cannot sustain a block. Clashes remain valid.\n        if (!guardLow && f.onGround) this.schedule(0, Math.max(tth + 0.42, 0.48));\n        else if (!canClash) { this.sideT = 0.30; this.sideSign = Math.random() < 0.5 ? -1 : 1; }\n        return;\n      }\n      // Shield must finish rising before contact; successful parry makes the next 90% faster.\n      const raise = f.nextShieldFast ? 0.01 : 0.10;\n      if (r < this.p.parry) this.schedule(Math.max(tth - raise - 0.03, 0),\n        o.isContinuousComboActive() ? Math.max(0.35, o.atk.wind + o.atk.active + o.atk.recover) : 0.3);\n      else if (r < this.p.parry + bc) this.schedule(rand(this.p.react[0], this.p.react[1]) * 0.45,\n        o.isContinuousComboActive() ? Math.max(0.5, o.atk.wind + o.atk.active + o.atk.recover) : tth + 0.45);\n      else if (r < this.p.parry + bc + 0.15) this.trySkill(f, "z", true);\n    }\n    const charging = o.state === S.CHARGE;\n    if (charging && !this.seenCharge) {\n      this.seenCharge = true;\n      if (Math.random() < 0.45) this.schedule(rand(this.p.react[0], this.p.react[1]), 1.4);\n    } else if (!charging) this.seenCharge = false;\n  }\n\n'


def repair_guard_ai_regression(text: str) -> str:
    """Surgically undo only the over-defensive changes from Smart AI Defense V1.

    Keeps AI Personality 2.0, Veyr's Festival pressure, active skills, all 17
    fighter-specific tactics, and any later counter code. Avoids restoring an
    old whole-file backup that could discard newer character improvements.
    """
    if DEFENSE_FIXED in text or DEFENSE_V1 not in text:
        return text

    # Replace the exact 2-reaction method with the earlier successful one.
    # The V1 helper methods are deleted, not merely disabled, so the patch
    # doesn't keep suppressing offense and doesn't require extra types.
    start = text.find('  /** Watch the opponent\'s ACTUAL current attack animation.')
    end = text.find('  /** A continuous combo does not stop at the first successful parry or block. */', start)
    if start < 0 or end < 0:
        raise PatchError('Cannot identify Smart AI Defense V1 reaction section; no files changed')
    text = text[:start] + LEGACY_REACT + text[end:]

    field = '  // FIGHT_ROYALE_AI_GUARD_TIMING_PARRY_V1_20261107\n  // Real dash and positioning, never artificial invulnerability or free guard.\n  private defensiveEvadeT = 0;\n  private defensiveEvadeDash = false;\n  private defensiveEvadeDir = new THREE.Vector3();\n\n'
    if text.count(field) != 1:
        raise PatchError('Missing exact passive defense fields; no files changed')
    text = text.replace(field, '', 1)
    replace = [
      (
        '    if (!f.stage) {\n      this.dodge(f); this.position(f, o, dt);\n      this.tacticalFootwork(f, o, dt); this.theaterFootwork(f, o, dt);\n      this.respectGuardRecovery(f, o);\n    }',
        '    if (!f.stage) { this.dodge(f); this.position(f, o, dt); this.tacticalFootwork(f, o, dt); this.theaterFootwork(f, o, dt); }',
        'preserve aggressive character footwork',
      ),
      (
        '    const escapingDefense = this.applyDefensiveEvade(f, o, dt);\n', '',
        'remove perpetual dodge/escape routine',
      ),
      (
        '    if (!escapingDefense && !this.aiAirTap && !this.readySkillOpportunity(f, o, dt) &&',
        '    if (!this.aiAirTap && !this.readySkillOpportunity(f, o, dt) &&',
        'restore skill use under pressure',
      ),
      (
        '    if (!escapingDefense && this.retimeComboParry(f, o)) return;',
        '    if (this.retimeComboParry(f, o)) return;',
        'restore combo reaction cadence',
      ),
      (
        '    if (this.blockHold > 0 && !escapingDefense) {',
        '    if (this.blockHold > 0) {',
        'restore defense input timing',
      ),
      (
        '    if (this.aiAirTap && !escapingDefense) {',
        '    if (this.aiAirTap) {',
        'restore aerial offense input',
      ),
      (
        '    if ((festival || this.cannotParryEnemy(o) || this.p.parry === 0) &&\n'
        '        this.blockWait < 0 && this.blockHold <= 0) {\n'
        '      // Avoid stationary empty-shield spam during the real regen delay.\n'
        '      if (f.guardRegenRemaining > 0 && f.guard < f.maxGuard * 0.36 && f.dashCd <= 0)\n'
        '        this.planDefensiveEvade(f, o, Math.max(0.25, a.wind - o.stateT), true);\n'
        '      else if (f.guard > Math.max(12, a.guard * 0.48))\n'
        '        this.schedule(0, Math.min(1.25, Math.max(0.27, a.wind + a.active)));\n'
        '    }',
        '    if ((festival || this.p.parry === 0) && this.blockWait < 0 && this.blockHold <= 0)\n'
        '      this.schedule(0, Math.min(1.8, Math.max(0.3, a.wind + a.active + a.recover)));',
        'restore continuous combo offense defense',
      ),
      (
        '    if (!active || festival || this.cannotParryEnemy(o) || this.p.parry <= 0 || f.isDown()) {',
        '    if (!active || festival || this.p.parry <= 0 || f.isDown()) {',
        'restore continuous timing',
      ),
      (
        '        // CPU must perceive the beat, then raise its shield.\n'
        '        if (beat < now + this.p.react[0] + raise + 0.035) continue;',
        '        if (beat < now + raise + 0.075) continue;',
        'restore per-beat parry schedule',
      ),
      (
        '      else if (r < this.p.jump + this.p.block) {\n'
        '        if (f.guardRegenRemaining > 0.05 && f.guard < f.maxGuard * 0.33 && f.onGround)\n'
        '          this.planDefensiveEvade(f, f.opponent as Fighter, eta, f.dashCd <= 0);\n'
        '        else this.schedule(Math.min(Math.max(eta - 0.2, 0), this.p.react[1]), eta + 0.2);\n'
        '      }',
        '      else if (r < this.p.jump + this.p.block) this.schedule(Math.min(Math.max(eta - 0.2, 0), this.p.react[1]), eta + 0.2);',
        'restore projectile guard behavior',
      ),
    ]
    for old, new, why in replace:
        if not new:
            if text.count(old) != 1: raise PatchError(why + ': expected exactly once')
            text = text.replace(old, '', 1)
        else:
            text = replace_once(text, old, new, why)
    if 'defensiveEvadeT' in text or 'escapingDefense' in text or 'cannotParryEnemy(' in text:
        raise PatchError('Some V1 passive-defense code remains; refusing partial repair')
    return '// ' + DEFENSE_FIXED + '\n' + text

def patch_all(root: Path, check_only: bool = False):
    game_dir = root / "src" / "game"
    paths = [game_dir / fn for fn in FILES]
    original = {p.name: read(p) for p in paths}
    if all(V2_MARKER in original[p.name] for p in paths):
        fixed = repair_guard_ai_regression(original['ai.ts'])
        if fixed != original['ai.ts']:
            if check_only:
                info('[CHECK] Existing V2 can have the V1 defense regression corrected.')
                return
            bak = backup([game_dir / 'ai.ts'])
            write(game_dir / 'ai.ts', fixed)
            info('[DONE] Corrected passive AI Defense V1 without reapplying V2. Backup: ' + str(bak))
        else:
            info('[OK] Parry Spin Counters V2 already installed — no files changed.')
        return
    partial = [n for n, body in original.items() if V2_MARKER in body]
    if partial:
        raise PatchError('Partial V2 installation detected in ' + ', '.join(partial) + '; restore backups before retrying')
    v1 = {
        'kits.ts': patch_kits(original['kits.ts']),
        'fighter.ts': patch_fighter(original['fighter.ts']),
        'model.ts': patch_model(original['model.ts']),
        'ai.ts': patch_ai(original['ai.ts']),
        'game.ts': patch_game(original['game.ts']),
    }
    patched = {
        'kits.ts': patch_v2_kits(v1['kits.ts']),
        'fighter.ts': patch_v2_fighter(v1['fighter.ts']),
        'model.ts': patch_v2_model(v1['model.ts']),
        'ai.ts': patch_v2_ai(repair_guard_ai_regression(v1['ai.ts'])),
        'game.ts': patch_v2_game(v1['game.ts']),
    }
    for fn, body in patched.items():
        if V2_MARKER not in body:
            raise PatchError('Missing V2 marker in ' + fn)
    if check_only:
        info('[CHECK] Counter V2 is compatible with this project. No files changed.')
        return
    bak = backup(paths)
    for path in paths:
        write(path, patched[path.name])
    info('[DONE] Flashier, stronger parry spin counters installed for all fighters.')
    info('[DONE] CPUs now adopt and defend counters without the passive Smart Defense V1 overrides.')
    info('[BACKUP] ' + str(bak))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Fight Royale V2: flashier one-hit parry spin counters + smarter CPU usage')
    ap.add_argument('--check', action='store_true', help='check compatibility without changing any files')
    args = ap.parse_args()
    try:
        root = find_root(Path.cwd())
        info(f'[ROOT] {root}')
        patch_all(root, check_only=args.check)
    except PatchError as exc:
        print('[ERROR]', exc)
        sys.exit(1)
