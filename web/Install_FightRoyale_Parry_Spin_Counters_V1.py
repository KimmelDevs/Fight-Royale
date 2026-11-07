#!/usr/bin/env python3
"""
Fight Royale: universal parry spin counters (all fighters / all kits).

Installs a new one-hit parry counter follow-up for every fighter.
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
  python Install_FightRoyale_Parry_Spin_Counters_V1.py
  python Install_FightRoyale_Parry_Spin_Counters_V1.py --check

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
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = paths[0].parents[2] / f"backup_{MARKER}_{stamp}"
    bak.mkdir(parents=True, exist_ok=True)
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


def patch_all(root: Path, check_only: bool = False):
    g = root / 'src' / 'game'
    paths = [g / f for f in FILES]
    original = {p.name: read(p) for p in paths}
    if all(MARKER in t for t in original.values()):
        info('[OK] Parry Spin Counters V1 already installed.')
        return

    patched = {}
    patched['kits.ts'] = patch_kits(original['kits.ts'])
    patched['fighter.ts'] = patch_fighter(original['fighter.ts'])
    patched['model.ts'] = patch_model(original['model.ts'])
    patched['ai.ts'] = patch_ai(original['ai.ts'])
    patched['game.ts'] = patch_game(original['game.ts'])

    if check_only:
        info('[CHECK] Patch can be applied successfully.')
        return

    bak = backup(paths)
    for p in paths:
        write(p, patched[p.name])
    info(f'[DONE] Installed Parry Spin Counters V1. Backups saved to: {bak}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Install Fight Royale parry spin counters for all fighters')
    ap.add_argument('--check', action='store_true', help='validate anchors only, do not write files')
    args = ap.parse_args()
    try:
        root = find_root(Path.cwd())
        info(f'[ROOT] {root}')
        patch_all(root, check_only=args.check)
    except PatchError as e:
        print(f'[ERROR] {e}')
        sys.exit(1)
