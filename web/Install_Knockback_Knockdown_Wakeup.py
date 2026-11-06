#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale - Weapon Knockback + Knockdown/Wake-up (foundation for aerial juggles).

Run: python Install_Knockback_Knockdown_Wakeup.py
     python Install_Knockback_Knockdown_Wakeup.py "C:\\My Games\\Fight-Royale"
     python Install_Knockback_Knockdown_Wakeup.py "C:\\My Games\\Fight-Royale" --check

Changes to normal 3D combat only:
  - Directional pushback on damage, blocks, guard breaks and weapon clashes.
  - Greatswords have the highest melee push; Aster's Judgment-form sword is
    notably stronger than his usual sword; faster/lighter weapons push less.
  - Powerful grounded melee hits can knock a fighter DOWN. They automatically
    stand up with a visible recovery pose, a short post-recovery safety window,
    and a cooldown against immediate repeat knockdowns.
  - Knockdown never counts as KO. Stage/platform knockback stays as originally
    implemented, and all damage, Judgment duration and Zarek passive rules stay.
  - Works on host/offline/CPU and animates on network guests via snapshots.

Makes timestamped source backups in .knockdown_backups. Never edits files until
ALL anchors have been verified; supports repeat runs without stacking patches.
Requires Python 3.9+; no additional packages.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

TAG = "FIGHT_ROYALE_WEIGHTED_KNOCKDOWN_WAKEUP_V1"
FILES = ("src/game/fighter.ts", "src/game/game.ts")

class PatchError(RuntimeError):
    pass


def once(src: str, old: str, new: str, label: str) -> str:
    n = src.count(old)
    if n != 1:
        raise PatchError(f"{label}: expected 1 matching code section, found {n}. No files changed.")
    return src.replace(old, new, 1)


def within(src: str, begin: str, end: str, old: str, new: str, label: str) -> str:
    p = src.find(begin)
    q = src.find(end, p + len(begin)) if p >= 0 else -1
    if p < 0 or q < 0 or src.find(begin, p + len(begin)) >= 0:
        raise PatchError(f"{label}: cannot uniquely locate the original method. No files changed.")
    return src[:p] + once(src[p:q], old, new, label) + src[q:]


def patch_fighter(s: str) -> str:
    if TAG in s:
        return s
    # Append enum members to preserve IDs for all pre-existing animation states.
    s = once(s,
        'export enum S { IDLE, ATTACK, CHARGE, BLOCK, HITSTUN, STAGGER, KO, WIN }',
        'export enum S { IDLE, ATTACK, CHARGE, BLOCK, HITSTUN, STAGGER, KO, WIN, KNOCKDOWN, WAKEUP }',
        'append states without renumbering existing states')
    s = once(s,
        '  private knock = 0;\n',
        '''  private knock = 0;
  // WEIGHTED_KNOCKDOWN: physical shove follows the ACTUAL impact source,
  // not whichever enemy the AI happens to target next.
  private knockAway = new THREE.Vector3(0, 0, 1);
  private knockdownLockT = 0;
  private readonly knockdownHold = 0.82;
  private readonly wakeupDuration = 0.38;
  /** Knockdown is NOT a KO: the fighter automatically recovers. */
  knockedDown() { return this.state === S.KNOCKDOWN || this.state === S.WAKEUP; }
  /** Called from combat resolution BEFORE the hit is processed. */
  setImpactSource(from: THREE.Vector3) {
    const away = this.root.position.clone().sub(from).setY(0);
    if (away.lengthSq() > 0.0001) this.knockAway.copy(away.normalize());
  }
  /** Clash recoil strength depends on the opponent's weapon, not damage. */
  weightedClashPush(strength: number) {
    if (!this.stage && !this.meteorFistArmor && !this.knockedDown())
      this.knock = this.state === S.HITSTUN && this.stunPose === "clash"
        ? Math.min(8, strength) : Math.max(this.knock, Math.min(8, strength));
  }
  private beginKnockdown() {
    // No knockdown during airborne juggles, binds, or armored specials.
    this.knockdownLockT = 2.3;
    this.holding = false; this.buffered = false;
    this.atk = null; this.atkId = ""; this.atkPhase = 0;
    this.dashT = 0; this.perfectDodgeT = 0;
    this.airChaseT = 0; this.airChaseMoveT = 0;
    this.comboPauseT = 0;
    this.setState(S.KNOCKDOWN);
    this.model.fall();
    this.model.recoil = Math.max(this.model.recoil, 0.6);
  }
''', 'new recoil and knockdown state')
    s = once(s,
        '    this.clock += dt;\n',
        '    this.clock += dt;\n    this.knockdownLockT = Math.max(0, this.knockdownLockT - dt);\n',
        'knockdown repeat prevention timer')
    s = once(s,
        '''      case S.HITSTUN:
      case S.STAGGER: if (this.stateT >= this.stun) this.setState(S.IDLE); break;
''',
        '''      case S.HITSTUN:
      case S.STAGGER: if (this.stateT >= this.stun) this.setState(S.IDLE); break;
      case S.KNOCKDOWN:
        if (this.stateT >= this.knockdownHold) this.setState(S.WAKEUP);
        break;
      case S.WAKEUP:
        if (this.stateT >= this.wakeupDuration) {
          this.model.standUp();
          this.invulnT = Math.max(this.invulnT, 0.24);
          this.setState(S.IDLE);
        }
        break;
''', 'ground knockdown and standing recovery transitions')
    # Transform model tilt across wake-up, with both procedural and VRM rigs.
    s = once(s,
        '''    this.bowDraw(dt);
    this.trail.update(dt);
  }

  /** Archer: the string comes back''',
        '''    // Pull the model upright smoothly rather than snapping back to standing.
    if (this.state === S.WAKEUP) {
      const t = THREE.MathUtils.clamp(this.stateT / this.wakeupDuration, 0, 1);
      const eased = t * t * (3 - 2 * t);
      this.model.rotation.x = -1.45 * (1 - eased);
    }
    this.bowDraw(dt);
    this.trail.update(dt);
  }

  /** Archer: the string comes back''', 'smooth wakeup on host and AI')
    # Stop using opponent direction for incoming knockback. Preserve attack lunges,
    # steering, bounds, and collision spacing.
    s = within(s, '  private move(dt: number) {', '  private vertical(dt: number) {',
        '''    this.knock = Math.max(this.knock - 14 * dt, 0);
    v -= this.knock;
''',
        '''    const recoilSpeed = this.knock;
    this.knock = Math.max(this.knock - 13 * dt, 0);
''', 'separate recoil from forward approach')
    s = within(s, '  private move(dt: number) {', '  private vertical(dt: number) {',
        '''    pos.addScaledVector(dir, v * dt);
''',
        '''    pos.addScaledVector(dir, v * dt);
    // Directional collision impulse. Gravity and regular forward movement still work.
    if (recoilSpeed > 0) pos.addScaledVector(this.knockAway, recoilSpeed * dt);
''', 'apply world-space knockback')
    s = within(s, '  receiveHit(attacker: Entity | null, a: Attack, power: number): string {',
        '  stagger(d: number)',
        '''    if (this.state === S.KO) return "none";
''',
        '''    if (this.state === S.KO) return "none";
    // Grounded knockdown and standing recovery cannot be chained indefinitely.
    // They remain alive; do not mark these states as KO / remove them from the match.
    if (this.knockedDown()) return "miss";
''', 'wakeup protection and knockdown immunity')
    s = within(s, '  receiveHit(attacker: Entity | null, a: Attack, power: number): string {',
        '  stagger(d: number)',
        '''    // ASTER_EMBER_LATEST_20261106: no repetitive hitstun from passive ground fire.
    if (a.id === "ember_ground") return this.lastCrit ? "crit" : "hit";
''',
        '''    // ASTER_EMBER_LATEST_20261106: no repetitive hitstun from passive ground fire.
    if (a.id === "ember_ground") return this.lastCrit ? "crit" : "hit";
    // A heavy physical hit may cause a recoverable floor knockdown. Skills that
    // already control airborne victims, active binds, superarmor, and platform
    // fighter launches intentionally keep their established rules.
    const strongGroundHit = this.onGround && !this.stage && !this.meteorFistArmor &&
      this.bloodFestivalT <= 0 && this.knockdownLockT <= 0 &&
      !this.chainBoundBy && !this.chainBindTarget &&
      a.type === "melee" && a.knock >= 5.3 && (a.heavy || a.stagger);
    if (strongGroundHit) {
      this.beginKnockdown();
      return this.lastCrit ? "crit" : "hit";
    }
''', 'strong melee knockdown trigger')
    s = once(s,
        '  stagger(d: number) { if (this.bloodFestivalT > 0 || this.meteorFistArmor) return;',
        '  stagger(d: number) { if (this.knockedDown() || this.bloodFestivalT > 0 || this.meteorFistArmor) return;',
        'no regular stun override while down')
    s = once(s,
        '''    this.model.standUp();
    this.setState(S.IDLE);
  }

  heal(amount: number)''',
        '''    this.model.standUp();
    this.knock = 0; this.knockdownLockT = 0;
    this.setState(S.IDLE);
  }

  heal(amount: number)''', 'reset down state on round revive')
    s = within(s, '  private computePose() {', '  // --- networking',
        '''      case S.KO: p = "down"; sp = 10; break;''',
        '''      case S.KO: p = "down"; sp = 10; break;
      case S.KNOCKDOWN: p = "down"; sp = 18; break;
      case S.WAKEUP: p = "rise"; sp = 14; break;''', 'down and wake-up poses')
    s = within(s, '  snapshot(): any[] {', '  applySnapshot(s: any[]) {',
        '''+this.comboPauseT.toFixed(2)];''',
        '''+this.comboPauseT.toFixed(2), +this.stateT.toFixed(3)];''', 'network state phase to animate recovery')
    s = within(s, '  applySnapshot(s: any[]) {', '  private updatePuppet(dt: number) {',
        '''    this.poseSpeed = s[7];
''',
        '''    this.poseSpeed = s[7];
    if (s.length > 41) this.stateT = s[41];
''', 'network state elapsed time')
    s = within(s, '  applySnapshot(s: any[]) {', '  private updatePuppet(dt: number) {',
        '''    if (this.state === S.KO && prev !== S.KO) this.model.fall();
    if (this.state !== S.KO && prev === S.KO) this.model.standUp();''',
        '''    if (this.state === S.KO && prev !== S.KO) this.model.fall();
    if (this.state !== S.KO && prev === S.KO) this.model.standUp();
    if (this.state === S.KNOCKDOWN && prev !== S.KNOCKDOWN) this.model.fall();
    if ((prev === S.WAKEUP || prev === S.KNOCKDOWN) &&
        this.state !== S.WAKEUP && this.state !== S.KNOCKDOWN) this.model.standUp();''',
        'network knockdown presentation transition')
    # Clients use synced states and poses, not client-side physics decisions.
    s = within(s, '  private updatePuppet(dt: number) {', '\n}\n',
        '''    this.bowDraw(dt);
    this.trail.update(dt);''',
        '''    if (this.state === S.WAKEUP) {
      const t = THREE.MathUtils.clamp(this.stateT / this.wakeupDuration, 0, 1);
      this.model.rotation.x = -1.45 * (1 - t * t * (3 - 2 * t));
    }
    this.bowDraw(dt);
    this.trail.update(dt);''', 'network wake-up tilt')
    return '// ' + TAG + '\n' + s


def patch_game(s: str) -> str:
    if TAG in s:
        return s
    # The game already has per-skill 'knock'. Multiply it only for MELEE HP hits;
    # prevent the balancing change from modifying ability damage or hitbox reach.
    # stage/platform knock is left untouched by this modifier.
    s = within(s,
        '  private applyHit(attacker: Entity | null, d: Entity, a: Attack, power: number, hitPos: THREE.Vector3, dir: THREE.Vector3, ranged: boolean): string {',
        '  /** Blood Frenzy lasts five seconds:',
        '''    const result = d.receiveHit(attacker, scaledAttack, riposte ? power * 1.15 : power);''',
        '''    // WEIGHTED_KNOCKDOWN: use weapon mass for melee pushback only.
    // Attack damage, combo scaling, block/parry handling and skills stay untouched.
    let knockFactor = 1;
    if (attacker instanceof Fighter && !ranged && a.type === "melee" &&
        !(d instanceof Fighter && d.stage)) {
      switch (attacker.kit) {
        case "greatsword": knockFactor = 1.38; break; // Garrick: maximum shove
        case "knight": knockFactor = attacker.look.element === "light"
          ? (attacker.judgmentT > 0 ? 1.26 : 1.09) : 1.06; break;
        case "chainblade": knockFactor = 1.13; break;
        case "knuckles": knockFactor = 1.12; break;
        case "kicks": knockFactor = 1.08; break;
        case "katana": knockFactor = 1.06; break;
        case "glaive": knockFactor = 1.0; break;
        case "wind": knockFactor = 0.94; break;
        case "sickle": knockFactor = 0.87; break;
        case "assassin": knockFactor = 0.81; break;
        default: knockFactor = 1; break;
      }
    }
    const weightedAttack = knockFactor === 1 ? scaledAttack :
      { ...scaledAttack, knock: Math.min(9.5, scaledAttack.knock * knockFactor) };
    if (d instanceof Fighter && attacker) d.setImpactSource(attacker.root.position);
    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : power);''',
        'weight melee knockback without touching HP damage')
    s = within(s,
        '  private applyHit(attacker: Entity | null, d: Entity, a: Attack, power: number, hitPos: THREE.Vector3, dir: THREE.Vector3, ranged: boolean): string {',
        '  /** Blood Frenzy lasts five seconds:',
        '''        const crit = d.lastCrit;''',
        '''        const crit = d.lastCrit;
        // A real floor knockdown is different from KO, and remains cosmetic
        // beyond its short, automatic recovery state.
        if (d instanceof Fighter && d.state === S.KNOCKDOWN && d.stateT < 0.10) {
          this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.60, 0)),
            "KNOCKDOWN!", "#ffd18f", 0.95);
          this.fxp("smoke", d.root.position.clone(), "#c7b5a6");
        }''', 'knockdown contact feedback')
    s = within(s, '  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {',
        '  // --- mob attacks',
        '''    a.clashRecoil();
    b.clashRecoil();''',
        '''    a.setImpactSource(b.root.position);
    b.setImpactSource(a.root.position);
    a.clashRecoil();
    b.clashRecoil();
    // A heavy blade pushes a lighter opponent away more dramatically on a
    // genuine weapon clash, but clash never deals HP damage or causes knockdown.
    const clashWeight = (f: Fighter) => f.kit === "greatsword" ? 1.38
      : f.kit === "knight" && f.look.element === "light"
        ? (f.judgmentT > 0 ? 1.26 : 1.09)
      : f.kit === "chainblade" ? 1.12
      : f.kit === "assassin" ? 0.82
      : f.kit === "sickle" ? 0.87
      : f.kit === "knuckles" ? 1.12 : 1;
    a.weightedClashPush(4.0 * clashWeight(b));
    b.weightedClashPush(4.0 * clashWeight(a));''',
        'weight genuine melee weapon clashes')
    return '// ' + TAG + '\n' + s


def choose_root(folder: str | None) -> Path:
    if folder:
        return Path(folder).expanduser().resolve()
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        chosen = filedialog.askdirectory(title="Select Fight Royale project folder (contains src/game)")
        root.destroy()
        if chosen:
            return Path(chosen).resolve()
    except Exception:
        pass
    value = input("Enter Fight Royale project folder: ").strip().strip('"')
    if not value:
        raise PatchError("No project folder was selected.")
    return Path(value).expanduser().resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description="Install weighted knockback, knockdown and wake-up system")
    ap.add_argument("folder", nargs="?", help="Fight Royale project root (contains src/game)")
    ap.add_argument("--check", "--dry-run", action="store_true", help="Validate only, write nothing")
    args = ap.parse_args()
    root = choose_root(args.folder)
    fns = {FILES[0]: patch_fighter, FILES[1]: patch_game}
    old = {}
    for rel in FILES:
        path = root / rel
        if not path.is_file():
            raise PatchError(f"Missing {path}. Select your Fight Royale project root.")
        old[rel] = path.read_text(encoding="utf-8-sig")
    installed = [TAG in old[rel] for rel in FILES]
    if all(installed):
        print("Weighted Knockback / Knockdown is already installed; no changes made.")
        return 0
    if any(installed):
        raise PatchError("Partial installation detected. Restore the two files from your backup first.")
    new = {rel: fn(old[rel]) for rel, fn in fns.items()}  # validate BOTH before any write
    if args.check:
        print("PASS: source code is compatible. Would update: " + ", ".join(FILES))
        return 0
    backup = root / ".knockdown_backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup.mkdir(parents=True, exist_ok=False)
    for rel in FILES:
        dest = backup / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dest)
    done = []
    try:
        for rel in FILES:
            dest = root / rel
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=dest.parent,
                                             prefix=dest.name + ".", suffix=".tmp", delete=False) as stream:
                stream.write(new[rel]); tmp = Path(stream.name)
            try:
                os.replace(tmp, dest)
            finally:
                tmp.unlink(missing_ok=True)
            done.append(rel)
    except Exception:
        for rel in done:
            (root / rel).write_text(old[rel], encoding="utf-8")
        raise
    print("SUCCESS: Weapon Knockback + Knockdown / Wake-up installed!")
    print("  Changes: directional hits, weapon-weighted melee clashes, knockdown recovery.")
    print("  Unchanged: weapon damage, attack range, Judgment, Clash Momentum, and skills.")
    print("  Modified: " + ", ".join(FILES))
    print("  Backups: " + str(backup))
    print("Restart the game and test heavy attacks and weapon clashes.")
    return 0

if __name__ == "__main__":
    try:
        rc = main()
    except (PatchError, OSError, UnicodeError, ValueError) as exc:
        print("Installer stopped safely: " + str(exc), file=sys.stderr)
        rc = 1
    if sys.stdin.isatty() and len(sys.argv) == 1:
        try: input("Press Enter to close...")
        except EOFError: pass
    sys.exit(rc)
