#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update Nesa Heart Hammer with Weight Passive, revised moves, and new ultimate.

This updater first runs the bundled base Nesa installer (icons + kit + model hooks),
then patches Nesa's gameplay to the requested latest version:
- revised basic attack string
- Upsie Daisie = hammer plant + lever kick with better reach
- GIGA BONK tuned
- new bonus ultimate: Heartbreaker High Striker
- Weight Passive: late swings are uninterruptible and crush block into chip damage

Run:
  python Install_Nesa_Weight_Passive_Update.py
or
  python Install_Nesa_Weight_Passive_Update.py "C:\\path\\to\\Fight-Royale\\web"
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE_INSTALLER = HERE / "Install_Nesa_Heart_Hammer_Fixed.py"
VERSION = "NESA_WEIGHT_PASSIVE_UPDATE_V1"

FILES = [
    "src/game/kits.ts",
    "src/game/fighter.ts",
    "src/game/ai.ts",
    "src/game/game.ts",
]

NEW_HAMMER_ATTACKS = '''function hammer(): Record<string, Attack> {
  return {
    // NESA_WEIGHT_PASSIVE_V1: once a hammer move is roughly 60% complete,
    // the rest of the swing becomes super-armored and crushes blocks into chip damage.
    l1: a({ name: "Heart Hook", desc: "Wide opening horizontal swing.", wind: 0.23, active: 0.10, recover: 0.24, dmg: 94, guard: 24, reach: 2.35, lunge: 1.8, knock: 2.4, stun: 0.30, pose_w: "l1_w", pose_s: "l1_s", next: "l2" }),
    l2: a({ name: "Reverse Crush", desc: "Reverse swing that keeps the hammer momentum flowing.", wind: 0.23, active: 0.10, recover: 0.25, dmg: 102, guard: 26, reach: 2.4, lunge: 1.9, knock: 2.8, stun: 0.32, pose_w: "l2_w", pose_s: "l2_s", next: "l3" }),
    l3: a({ name: "Overhead Spin", desc: "A turning overhead hammer strike.", wind: 0.29, active: 0.12, recover: 0.30, dmg: 118, guard: 30, reach: 2.45, lunge: 1.55, knock: 3.5, stun: 0.40, pose_w: "l3_w", pose_s: "l3_s", next: "l4" }),
    l4: a({ name: "Heartquake", desc: "Massive ground slam finisher with a shockwave.", type: "strike", at: "self", wind: 0.34, active: 0.16, recover: 0.42, dmg: 150, guard: 38, knock: 5.8, stun: 0.54, heavy: true, delay: 0.06, radius: 2.35, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
    heavy: a({ name: "Heart Upper", desc: "Hold to charge a devastating uppercut that launches enemies.", wind: 0.30, active: 0.13, recover: 0.58, dmg: 205, guard: 56, reach: 2.3, lunge: 2.1, knock: 7.1, stun: 0.78, heavy: true, self_jump: 4.8, pose_w: "charge", pose_s: "heavy_s" }),
    z: a({ name: "Side Swipe", desc: "A powerful sideways heart-hammer swing with crushing knockback. Blocking reduces damage, but never fully stops it.", cd: 7, wind: 0.22, active: 0.12, recover: 0.42, dmg: 165, guard: 64, reach: 2.55, lunge: 1.5, knock: 8.2, stun: 0.62, heavy: true, pose_w: "nx_w", pose_s: "nx_s" }),
    x: a({ name: "Upsie Daisie", desc: "Plant the hammer, hold it like a lever, and fling yourself into a flying side kick while the hammer follows.", cd: 9, wind: 0.20, active: 0.18, recover: 0.46, dmg: 152, guard: 32, reach: 2.35, lunge: 7.2, knock: 5.6, stun: 0.50, heavy: true, self_jump: 6.5, pose_w: "kick_w", pose_s: "kick_s" }),
    c: a({ name: "GIGA BONK!", desc: "She struggles up with the weight, hops with the hammer, then crashes down with a huge shockwave.", cd: 18, type: "strike", at: "self", mode: "leap", self_jump: 7.8, wind: 0.54, active: 0.18, recover: 0.82, dmg: 300, guard: 86, knock: 9.2, stun: 1.05, heavy: true, radius: 3.15, style: "slam", pose_w: "charge", pose_s: "heavy_s" }),
  };
}
'''

NEW_BONUS = '''    case "hammer":
      return a({ name: "Heartbreaker High Striker", desc: "First bonk stuns the victim, then the hammer swells huge and crashes down again like a carnival strength tester.", cd: 24, type: "strike", at: "self", wind: 0.58, active: 0.18, recover: 1.05, dmg: 220, guard: 92, knock: 9.4, stun: 3.0, heavy: true, radius: 3.8, style: "slam", repeat: 2, interval: 0.62, pose_w: "charge", pose_s: "heavy_s" });
'''

HAMMER_HELPERS = '''  private get hammerWeightArmor(): boolean {
    if (this.kit !== "hammer" || this.state !== S.ATTACK || !this.atk) return false;
    const total = Math.max(0.01, this.atk.wind + this.atk.active + this.atk.recover);
    return this.stateT >= total * 0.60;
  }

'''

OLD_GUARD_BREAK = '''        // NESA_CRUSH_BLOCK_V2: her sideways hammer deals 50% chip damage through block.
        this.lastDamage = attacker instanceof Fighter && attacker.kit === "hammer" && a.id === "z" ? dmg * 0.5 : dmg * 0.4;
        this.lastCrit = false;
        this.hp = Math.max(this.hp - this.lastDamage, 0);
        this.knock = 3.5;
        if (this.hp <= 0) { this.ko(); return "ko"; }
        if (attacker instanceof Fighter && attacker.kit === "hammer" && a.id === "z" &&
            !this.stage && this.onGround && this.bloodFestivalT <= 0 &&
            this.knockdownLockT <= 0 && !this.chainBoundBy && !this.chainBindTarget) this.beginKnockdown();
        else if (this.bloodFestivalT <= 0) this.stagger(0.85);
        this.model.flash("#ffd966", 0.18);'''

NEW_GUARD_BREAK = '''        const hammerCrush = attacker instanceof Fighter && attacker.hammerWeightArmor &&
          (a.type === "melee" || a.type === "strike");
        // NESA_WEIGHT_PASSIVE_V1: late hammer swings still hurt through block and hit harder on guard break.
        this.lastDamage = hammerCrush ? dmg * 0.55 : dmg * 0.4;
        this.lastCrit = false;
        this.hp = Math.max(this.hp - this.lastDamage, 0);
        this.knock = hammerCrush ? Math.max(4.1, a.knock * 0.62) : 3.5;
        if (this.hp <= 0) { this.ko(); return "ko"; }
        if (hammerCrush && !this.stage && this.onGround && this.bloodFestivalT <= 0 &&
            this.knockdownLockT <= 0 && !this.chainBoundBy && !this.chainBindTarget &&
            (a.heavy || a.id === "z" || a.id === "c" || a.id === "v")) this.beginKnockdown();
        else if (this.bloodFestivalT <= 0) this.stagger(0.85);
        this.model.flash("#ffd966", 0.18);'''

OLD_BLOCK_CHIP = '''      // NESA_CRUSH_BLOCK_V2: blocking her Side Swipe is never a free escape.
      if (attacker instanceof Fighter && attacker.kit === "hammer" && a.id === "z") {
        this.lastDamage = dmg * 0.5;
        this.lastCrit = false;
        this.hp = Math.max(0, this.hp - this.lastDamage);
        this.knock = Math.max(this.knock, a.knock * 0.78);
        if (this.hp <= 0) { this.ko(); return "ko"; }
        if (!this.stage && this.onGround && this.knockdownLockT <= 0 &&
            this.bloodFestivalT <= 0 && !this.chainBoundBy && !this.chainBindTarget)
          this.beginKnockdown();
        else if (!this.stage) this.stagger(0.6);
        this.model.recoil = 0.95;
        return "blocked";
      }
'''

NEW_BLOCK_CHIP = '''      // NESA_WEIGHT_PASSIVE_V1: late hammer swings crush block into chip damage.
      const hammerCrushBlock = attacker instanceof Fighter && attacker.hammerWeightArmor &&
        (a.type === "melee" || a.type === "strike");
      if (hammerCrushBlock) {
        this.lastDamage = dmg * 0.58;
        this.lastCrit = false;
        this.hp = Math.max(0, this.hp - this.lastDamage);
        this.knock = Math.max(this.knock, a.knock * 0.72);
        if (this.hp <= 0) { this.ko(); return "ko"; }
        if (!this.stage && this.onGround && this.knockdownLockT <= 0 &&
            this.bloodFestivalT <= 0 && !this.chainBoundBy && !this.chainBindTarget &&
            (a.heavy || a.id === "z" || a.id === "c" || a.id === "v"))
          this.beginKnockdown();
        else if (!this.stage && this.bloodFestivalT <= 0)
          this.stagger(Math.max(0.20, Math.min(0.45, a.stun * 0.55)));
        this.model.recoil = 0.95;
        return "blocked";
      }
'''

HAMMER_UNINTERRUPT = '''    if (this.hammerWeightArmor) {
      // NESA_WEIGHT_PASSIVE_V1: once her swing is committed, Nesa still takes damage,
      // but the weight keeps the attack going instead of letting hitstun cancel it.
      this.knock = Math.min(this.knock, 1.4);
      this.model.recoil = Math.max(this.model.recoil, 0.36);
      return this.lastCrit ? "crit" : "hit";
    }
'''

CLASH_PATCH_OLD = '''  clashRecoil() {
    if (this.isContinuousComboActive()) {'''

CLASH_PATCH_NEW = '''  clashRecoil() {
    if (this.hammerWeightArmor) {
      // NESA_WEIGHT_PASSIVE_V1: late hammer swings power through clashes.
      this.model.recoil = Math.max(this.model.recoil, 0.32);
      this.knock = Math.max(this.knock, 1.4);
      return;
    }
    if (this.isContinuousComboActive()) {'''

class PatchError(RuntimeError):
    pass

def fail(msg: str):
    raise PatchError(msg)

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly one code anchor, found {count}")
    return text.replace(old, new, 1)

def find_root(spec: str | None) -> Path:
    if spec:
        p = Path(spec).expanduser().resolve()
    else:
        p = Path.cwd()
    for q in (p, p / 'web'):
        if (q / 'src/game/roster.ts').is_file() and (q / 'src/game/kits.ts').is_file():
            return q
    fail('Fight Royale folder not found. Run from the web folder, or pass the project folder as an argument.')

def backup_and_write(root: Path, modifications: dict[str, bytes]):
    if not modifications:
        print('[OK] Nesa weight-passive update already installed.')
        return
    backup = root / '.nesa_installer_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True, exist_ok=False)
    for rel in modifications:
        src = root / rel
        if src.exists():
            dst = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    written: list[str] = []
    try:
        for rel, data in modifications.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tf:
                tf.write(data)
                temp_path = Path(tf.name)
            os.replace(temp_path, dest)
            written.append(rel)
    except Exception:
        for rel in written:
            dest = root / rel
            bak = backup / rel
            if bak.exists():
                shutil.copy2(bak, dest)
            elif dest.exists():
                dest.unlink()
        raise
    print('[OK] Weight-passive update installed. Backup:', backup)

def patch_kits(text: str) -> str:
    s = text.find('function hammer(): Record<string, Attack> {')
    e = text.find('function katana(): Record<string, Attack> {', s)
    if s < 0 or e < 0:
        fail('Could not locate Nesa hammer attacks in kits.ts. Run the base Nesa installer first.')
    text = text[:s] + NEW_HAMMER_ATTACKS + '\n' + text[e:]

    bs = text.find('function bonusSkill(')
    if bs < 0:
        fail('Could not locate bonusSkill() in kits.ts')
    s = text.find('    case "hammer":', bs)
    e = text.find('    case "katana":', s)
    if s < 0 or e < 0:
        fail('Could not locate Nesa hammer bonus skill in kits.ts')
    text = text[:s] + NEW_BONUS + text[e:]
    return text

def patch_fighter(text: str) -> str:
    if 'private get hammerWeightArmor()' not in text:
        text = replace_once(text, '  private ground: Plat | null = null;', HAMMER_HELPERS + '  private ground: Plat | null = null;', 'insert hammer weight helpers')
    if 'NESA_CRUSH_BLOCK_V2' in text:
        text = replace_once(text, OLD_GUARD_BREAK, NEW_GUARD_BREAK, 'replace old hammer guard-break chip')
        text = replace_once(text, OLD_BLOCK_CHIP, NEW_BLOCK_CHIP, 'replace old hammer block chip')
    else:
        # Already updated? leave as-is if our newer marker exists.
        if 'NESA_WEIGHT_PASSIVE_V1' not in text:
            fail('Could not locate old Nesa block-crush patch in fighter.ts')
    if 'late-swing uninterruptible armor' not in text and HAMMER_UNINTERRUPT not in text:
        text = replace_once(text,
            '    // ASTER_EMBER_LATEST_20261106: no repetitive hitstun from passive ground fire.',
            HAMMER_UNINTERRUPT + '    // ASTER_EMBER_LATEST_20261106: no repetitive hitstun from passive ground fire.',
            'insert uninterruptible hammer passive')
    if 'late hammer swings power through clashes' not in text:
        text = replace_once(text, CLASH_PATCH_OLD, CLASH_PATCH_NEW, 'insert clash armor')
    return text

def patch_ai(text: str) -> str:
    old_want = 'const want = ranged ? 5 : (f.kit === "greatsword" || f.kit === "hammer") ? 1.6 : 1.25;'
    new_want = 'const want = ranged ? 5 : f.kit === "greatsword" ? 1.6 : f.kit === "hammer" ? 1.75 : 1.25;'
    if old_want in text:
        text = replace_once(text, old_want, new_want, 'update hammer desired range')
    old_reach = 'const reach = ranged ? 9 : f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks" ? 1.7 : (f.kit === "greatsword" || f.kit === "hammer") ? 2.3 : f.kit === "glaive" ? 1.62 : 1.9;'
    new_reach = 'const reach = ranged ? 9 : f.kit === "assassin" || f.kit === "knuckles" || f.kit === "kicks" ? 1.7 : f.kit === "greatsword" ? 2.3 : f.kit === "hammer" ? 2.45 : f.kit === "glaive" ? 1.62 : 1.9;'
    if old_reach in text:
        text = replace_once(text, old_reach, new_reach, 'update hammer reach')
    return text

def patch_game(text: str) -> str:
    old = '        case "greatsword": knockFactor = 1.38; break; // Garrick: maximum shove'
    new = old + '\n        case "hammer": knockFactor = 1.30; break; // Nesa: giant hammer shove'
    if 'case "hammer": knockFactor = 1.30; break; // Nesa: giant hammer shove' not in text:
        text = replace_once(text, old, new, 'add hammer knock factor')
    return text

def main():
    ap = argparse.ArgumentParser(description='Install/update Nesa Heart Hammer with Weight Passive')
    ap.add_argument('project', nargs='?', help='web folder or repository root')
    ap.add_argument('--check', action='store_true', help='dry-run only')
    args = ap.parse_args()

    root = find_root(args.project)
    print('Fight Royale project:', root)
    if not BASE_INSTALLER.is_file():
        fail('Missing Install_Nesa_Heart_Hammer_Fixed.py. Keep both files together.')

    # Only invoke the base installer when Nesa is not already present.
    roster_text = (root / 'src/game/roster.ts').read_text(encoding='utf-8')
    kits_text = (root / 'src/game/kits.ts').read_text(encoding='utf-8')
    base_present = 'id: "nesa"' in roster_text and 'function hammer(): Record<string, Attack> {' in kits_text
    if not base_present:
        base_cmd = [sys.executable, str(BASE_INSTALLER), str(root)]
        if args.check:
            print('[CHECK] Base Nesa install is missing; the bundled base installer would run first.')
            base_cmd.append('--check')
        subprocess.run(base_cmd, check=True)
    else:
        print('[OK] Base Nesa install already present; skipping the old installer pass.')

    modifications: dict[str, bytes] = {}
    for rel in FILES:
        path = root / rel
        if not path.is_file():
            fail(f'Missing required file: {path}')
        before = path.read_text(encoding='utf-8')
        if rel.endswith('kits.ts'):
            after = patch_kits(before)
        elif rel.endswith('fighter.ts'):
            after = patch_fighter(before)
        elif rel.endswith('ai.ts'):
            after = patch_ai(before)
        elif rel.endswith('game.ts'):
            after = patch_game(before)
        else:
            after = before
        if after != before:
            modifications[rel] = after.encode('utf-8')

    print('Files to update:', len(modifications))
    for rel in modifications:
        print('  ', rel)
    if args.check:
        print('[CHECK] Dry-run successful. Nothing changed.')
        return
    backup_and_write(root, modifications)
    print('[DONE] Nesa now has Weight Passive, revised basics, updated Upsie Daisie, and the new carnival-style ultimate.')
    print('Run: npx tsc --noEmit -p .  and npm run dev')

if __name__ == '__main__':
    try:
        main()
    except (PatchError, OSError, subprocess.CalledProcessError) as exc:
        print('INSTALL FAILED:', exc)
        sys.exit(1)
