#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nesa V5 — loadout-safe Heart Smash charges, no 3s High Striker stun,
spinning aerial charge, half-duration charge spins, and upright leg posture.

Apply AFTER Nesa Heart Smash V4 (and with or without the No-Foot-Heaviness updater).
Use `python .\\Install_Nesa_V5_Fixes.py` from the Fight Royale web folder.
No third-party Python libraries. Originals are backed up before any writes.
--check validates the full patch without editing; reruns do not duplicate edits.
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

MARKER = "NESA_V5_LOADOUT_AIR_SPIN_UPRIGHT"
FILES = ["src/game/kits.ts", "src/game/fighter.ts", "src/game/game.ts", "src/game/model.ts", "src/game/vrm.ts"]

class PatchError(Exception):
    pass

def once(s: str, old: str, new: str, label: str) -> str:
    n = s.count(old)
    if n != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {n}. Nothing was changed.")
    return s.replace(old, new, 1)

def root_at(spec: str | None) -> Path:
    p = Path(spec).expanduser().resolve() if spec else Path.cwd().resolve()
    for root in (p, p / "web"):
        if all((root / x).is_file() for x in ("src/game/roster.ts", "src/game/fighter.ts", "src/game/kits.ts")):
            return root
    if not spec:
        try:
            import tkinter as tk
            from tkinter import filedialog
            app = tk.Tk()
            app.withdraw()
            folder = filedialog.askdirectory(title="Select Fight Royale web folder")
            app.destroy()
            if folder:
                return root_at(folder)
        except Exception:
            pass
    raise PatchError("Select the Fight Royale web folder, containing src/game/fighter.ts")


def patch_kits(s: str) -> str:
    old = 'desc: "Carnival smash: a stunning bonk, 4x hammer growth, then a second overwhelming blow.", cd: 26, type: "strike", at: "self", wind: 0.66, active: 2.20, recover: 0.90, dmg: 145, guard: 85, knock: 12.5, stun: 3.0, heavy: true, radius: 3.50, style: "nesa_high_striker"'
    new = 'desc: "Carnival strength-test double smash: first bonk, a 4x heart hammer, then an enormous second blow. No long stun.", cd: 26, type: "strike", at: "self", wind: 0.66, active: 2.20, recover: 0.90, dmg: 145, guard: 85, knock: 12.5, stun: 0.26, heavy: true, radius: 3.50, style: "nesa_high_striker"'
    s = once(s, old, new, "remove High Striker 3s stun data")
    old_idle = '  // Hammer weight pulls Nesa\'s shoulders down; bent knees and a forward torso counterbalance it.\n  idle: K(P([0.30, -0.24, 0.06], [-0.16, 0.18, 0], [-1.12, -0.27, -0.18], [-0.10, 0, 0], [-1.14, 0.21, 0.18], [-0.10, 0, 0], [-0.47, 0, 0.12], [0.30, 0, -0.12], -0.21), 0.50, 0.42),'
    new_idle = '  // NESA_V5_LOADOUT_AIR_SPIN_UPRIGHT: Nesa STANDS on straight, relaxed legs; the hammer weight pulls at her shoulders and wrists, not her knees.\n  idle: P([0.11, -0.20, 0.03], [-0.04, 0.13, 0], [-1.04, -0.29, -0.15], [-0.16, 0, 0], [-1.03, 0.21, 0.14], [-0.16, 0, 0], [-0.06, 0, 0.05], [0.06, 0, -0.05], 0.0),'
    s = once(s, old_idle, new_idle, "upright idle stance")
    old_charge = '  charge: K(P([-0.24, -0.38, 0], [0.09, 0.28, 0], [-2.6, -0.35, -0.12], [0.7, 0, 0], [-2.44, -0.25, 0.12], [0.65, 0, 0], [-0.66, 0, 0.1], [0.54, 0, -0.1], -0.28), 0.6, 0.55),'
    new_charge = '  charge: K(P([-0.13, -0.38, 0], [0.06, 0.28, 0], [-2.6, -0.35, -0.12], [0.7, 0, 0], [-2.44, -0.25, 0.12], [0.65, 0, 0], [-0.15, 0, 0.08], [0.14, 0, -0.08], -0.075), 0.12, 0.13),'
    s = once(s, old_charge, new_charge, "upright charge stance")
    return s


def patch_fighter(s: str) -> str:
    s = once(s,
        '      this.cooldowns.c = this.nesaCCharges > 0 ? 0 : this.nesaCRechargeT;\n      if (this.intent.skill !== "c") this.nesaCArmed = true;',
        '''      // NESA_V5_LOADOUT_AIR_SPIN_UPRIGHT: charges belong to Pink Heart Smash,
      // wherever the loadout equips it (Z / X / C), never to the C key itself.
      const heartSlot = ["z", "x", "c"].find(k => this.attacks[k]?.style === "nesa_heart_slam");
      if (heartSlot) this.cooldowns[heartSlot] = this.nesaCCharges > 0 ? 0 : this.nesaCRechargeT;
      if (!this.intent.skill || this.attacks[this.intent.skill]?.style !== "nesa_heart_slam") this.nesaCArmed = true;''',
        "move heart-charge cooldown to real loadout slot")
    s = once(s,
        '    if (this.kit === "hammer" && k === "c" &&\n        (!this.nesaCArmed || this.nesaCCharges <= 0)) return;',
        '    if (this.kit === "hammer" && this.attacks[k]?.style === "nesa_heart_slam" &&\n        (!this.nesaCArmed || this.nesaCCharges <= 0)) return;',
        "only Heart Smash checks stored charges")
    s = once(s,
        '''    if (this.kit === "hammer" && k === "c") {
      this.nesaCArmed = false;
      if (this.nesaCCharges === 3) this.nesaCRechargeT = 7.5 * this.cdMult;
      this.nesaCCharges--;
      this.cooldowns.c = this.nesaCCharges > 0 ? 0 : this.nesaCRechargeT;
    } else this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 : this.attacks[k].cd * this.cdMult;''',
        '''    if (this.kit === "hammer" && this.attacks[k]?.style === "nesa_heart_slam") {
      this.nesaCArmed = false;
      if (this.nesaCCharges === 3) this.nesaCRechargeT = 7.5 * this.cdMult;
      this.nesaCCharges--;
      this.cooldowns[k] = this.nesaCCharges > 0 ? 0 : this.nesaCRechargeT;
    } else this.cooldowns[k] = this.attacks[k].type === "barrel" ? 0.6 : this.attacks[k].cd * this.cdMult;''',
        "only Pink Heart Smash consumes charges")
    s = once(s,
        '''      if (this.atkId === "c") {
        this.nesaCCharges = Math.min(3, this.nesaCCharges + 1);
        if (this.nesaCCharges === 3) this.nesaCRechargeT = 0;
        this.cooldowns.c = 0;
      }''',
        '''      if (a.style === "nesa_heart_slam") {
        this.nesaCCharges = Math.min(3, this.nesaCCharges + 1);
        if (this.nesaCCharges === 3) this.nesaCRechargeT = 0;
        this.cooldowns[this.atkId] = 0;
      }''',
        "block-cancel refunds only Heart Smash")
    s = once(s,
        '''        if (this.kit === "hammer" && this.atkId === "c") {
          this.nesaCCharges = Math.min(3, this.nesaCCharges + 1);
          if (this.nesaCCharges === 3) this.nesaCRechargeT = 0;
          this.cooldowns.c = 0;
        }''',
        '''        if (this.kit === "hammer" && this.atk?.style === "nesa_heart_slam") {
          this.nesaCCharges = Math.min(3, this.nesaCCharges + 1);
          if (this.nesaCCharges === 3) this.nesaCRechargeT = 0;
          this.cooldowns[this.atkId] = 0;
        }''',
        "dash-cancel refunds only Heart Smash")
    # Loadout also moves Upsie Daisie, so its armor/pose/kick motion must follow skill NAME.
    s = once(s,
        '    return this.atkId === "x" || this.atkPhase >= 1;',
        '    return this.atk.name === "Upsie Daisie" || this.atkPhase >= 1;',
        "kick armor follows loadout slot")
    s = once(s,
        '(this.atkId === "x" || this.atkPhase !== 0 || !this.atk || this.stateT >= this.atk.wind)) return;',
        '(this.atk?.name === "Upsie Daisie" || this.atkPhase !== 0 || !this.atk || this.stateT >= this.atk.wind)) return;',
        "kick dash immunity follows skill")
    s = once(s,
        'if (this.kit === "hammer" && this.atkId === "x") {\n        // The pole is braced before the kick launches, not after.',
        'if (this.kit === "hammer" && a.name === "Upsie Daisie") {\n        // The pole is braced before the kick launches, not after.',
        "kick takeoff follows skill")
    s = once(s,
        '} else if (this.kit === "hammer" && this.atkId === "x") {\n        // Plant during wind-up;',
        '} else if (this.kit === "hammer" && this.atk?.name === "Upsie Daisie") {\n        // Plant during wind-up;',
        "kick movement follows skill")
    s = once(s,
        '!(this.kit === "hammer" && id === "x")) {',
        '!(this.kit === "hammer" && this.atk.name === "Upsie Daisie")) {',
        "kick no instant jump follows skill")
    s = once(s,
        'if (this.kit === "hammer" && this.atkId !== "x" && this.atkPhase === 0 &&',
        'if (this.kit === "hammer" && a.name !== "Upsie Daisie" && this.atkPhase === 0 &&',
        "kick not block-cancellable regardless of slot")
    # Half the actual time spinning for a given ground charge; do not change other fighters.
    s = once(s,
        '      const spin = 0.34 + (held - HOLD_T) * 0.77;',
        '      const spin = (0.34 + (held - HOLD_T) * 0.77) * 0.50; // Nesa V5: hold:spin conversion 1:0.5',
        "half ground charge spin duration")
    # Charged aerial hammer now ACTUALLY spins and hits during its shortened active time.
    s = once(s,
        '''      this.atk = { ...this.atk, type: "melee", wind: 0.11, active: 0.15,
        recover: 0.30, dmg: 84 + 122 * ratio, knock: 3.8 + 5.0 * ratio,
        guard: 23 + 25 * ratio, reach: 2.40, lunge: 0.5,
        stun: 0.27 + ratio * 0.34, heavy: ratio >= 0.65,
        no_parry: true, next: "" };''',
        '''      // NESA V5: the jump release is a REAL horizontal weapon spin, not a slice.
      // 1s earned spin becomes 0.5s, as on the ground; shorter hold = fewer revolutions.
      const airSpin = (0.34 + ratio * 0.76) * 0.50;
      this.atk = { ...this.atk, type: "melee", wind: 0.11, active: airSpin,
        recover: 0.30, dmg: 44 + 9 * ratio, knock: 3.8 + 3.4 * ratio,
        guard: 23 + 13 * ratio, reach: 2.55, lunge: 0.5,
        stun: 0.20 + ratio * 0.22, heavy: false,
        style: "nesa_air_spin", no_parry: true, next: "" };''',
        "aerial hammer spin scaling and hit data")
    s = once(s,
        'if (attack?.style === "nesa_spin" && this.stateT >= attack.wind &&',
        'if ((attack?.style === "nesa_spin" || attack?.style === "nesa_air_spin") && this.stateT >= attack.wind &&',
        "body spin for ground AND air charge")
    s = once(s,
        'this.model.nesaSpinHorizontal = attack?.style === "nesa_spin" ?',
        'this.model.nesaSpinHorizontal = (attack?.style === "nesa_spin" || attack?.style === "nesa_air_spin") ?',
        "horizontal hammer spin for ground AND air")
    s = once(s,
        '          if (a.style === "nesa_spin") {',
        '          if (a.style === "nesa_spin" || a.style === "nesa_air_spin") {',
        "same cinematic air/ground spin animation")
    return s


def patch_game(s: str) -> str:
    s = once(s,
        '        if (me.kit === "hammer" && k === "c") return {',
        '        if (me.kit === "hammer" && a.style === "nesa_heart_slam") return {',
        "only Pink Heart Smash displays charge counter")
    s = once(s,
        '''      if (d instanceof Fighter && (hit === "hit" || hit === "crit")) {
        d.stagger(3.0); // exactly 3 s from the first connected blow (not normal stun DR)
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.75, 0)), "STUN 3s", "#ffd1e5", 0.92);
      }''',
        '''      if (hit === "hit" || hit === "crit") {
        // NESA_V5_LOADOUT_AIR_SPIN_UPRIGHT: no 3-second stun on High Striker.
        // Keep the ordinary short hit reaction and the 4x follow-up spectacle.
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.75, 0)), "BONK!", "#ffd1e5", 0.84);
      }''',
        "remove forced 3s first-hit stun")
    s = once(s, 'stun: 0.30, heavy: false, no_parry: true, reach: 2.65',
                'stun: 0.18, heavy: false, no_parry: true, reach: 2.65',
                "short ordinary reaction on High Striker opening hit")
    s = once(s, 'knock: 13.2, stun: 1.05, heavy: true, no_parry: true',
                'knock: 13.2, stun: 0.18, heavy: true, no_parry: true',
                "short ordinary reaction on High Striker finishing hit")
    s = once(s,
        '    const beats = Math.max(2, Math.ceil(total / 0.205));',
        '    const beats = Math.max(1, Math.ceil(total / 0.205)); // V5: 1:0.5 spin duration gives fewer REAL hits',
        "let half-charge spins use one revolution")
    s = once(s,
        '          f.swingSerial !== serial || f.atk?.style !== "nesa_spin") return;',
        '          f.swingSerial !== serial || (f.atk?.style !== "nesa_spin" && f.atk?.style !== "nesa_air_spin")) return;',
        "allow timed aerial spin hit windows")
    s = once(s,
        '''      const strike: Attack = { ...a,
        dmg: last ? a.dmg * 1.75 : a.dmg, guard: last ? 40 : 13,
        knock: last ? 7.8 + beats * 0.30 : 1.15,
        stun: last ? 0.67 : 0.18, heavy: last,
        no_parry: true, reach: 2.65 };''',
        '''      const strike: Attack = { ...a,
        dmg: last ? a.dmg * 1.75 : a.dmg, guard: last ? 40 : 13,
        knock: last ? (a.style === "nesa_air_spin" ? 5.5 + beats * 0.32 : 7.8 + beats * 0.30) : 1.15,
        stun: last ? 0.54 : 0.16, heavy: last,
        no_parry: true, reach: 2.65 };''',
        "balance air spinning finisher knockback")
    s = once(s,
        '    if (f.kit === "hammer" && a.style === "nesa_spin") {',
        '    if (f.kit === "hammer" && (a.style === "nesa_spin" || a.style === "nesa_air_spin")) {',
        "route air spin to real timed spin hits")
    s = once(s,
        '    if (f.kit === "hammer" && f.atkId === "x") {',
        '    if (f.kit === "hammer" && a.name === "Upsie Daisie") {',
        "route kick regardless of equipped loadout key")
    s = once(s,
        '          f.state !== S.ATTACK || f.atkId !== "x") return;',
        '          f.state !== S.ATTACK || f.atk?.name !== "Upsie Daisie") return;',
        "kick delayed collision regardless of loadout key")
    s = s.replace('  /** Carnival high striker: hit -> real 3s stun -> grow hammer 4x -> giant finishing blow. */',
                  '  /** Carnival high striker: opening bonk -> grow hammer 4x -> giant finishing blow; no long stun. */')
    return s


def patch_model(s: str) -> str:
    # Minor flat-foot adjustment on the original procedural model. If the standalone
    # no-foot updater is already present, remove its remaining artificial hip drop.
    if 'NESA_NO_FOOT_HEAVINESS_V1' not in s:
        raise PatchError("Expected Nesa V4 model or standalone footwork patch. No changes made.")
    s = once(s,
        '      this.hips.position.y -= 0.012 + moving * 0.004;',
        '      // V5: feet and knees stay upright; weight reads only in arms and torso.\n      this.hips.position.y += 0;',
        "remove idle hip crouch")
    return s


def patch_vrm(s: str) -> str:
    # New light-footed, straight-knee VRM pose just for Nesa. Garrick's heavy
    # greatsword style remains entirely untouched.
    style = '''  // NESA_V5_LOADOUT_AIR_SPIN_UPRIGHT: straight legs and level hips; weighted upper body only.
  nesa: { stance: D(3), toeOut: D(4), knee: D(1.5), drop: 0, lean: D(2), chin: 0,
    shoulderUp: D(1), elbowOut: D(5), hipSway: 0.012, hipRoll: D(1), contra: D(1),
    relaxKnee: D(2), headTilt: D(1), headYaw: D(4), breath: 0.85,
    armSwing: D(9), walkRoll: D(1.4), walkYaw: D(3) },
'''
    s = once(s, '  storm: { stance:', style + '  storm: { stance:', 'add VRM Nesa upright style')
    return s


def patch_model_style(s: str) -> str:
    s = once(s,
        'this.kit === "sickle" ? "feral" : (this.kit === "greatsword" || this.kit === "hammer") ? "greatsword" :',
        'this.kit === "sickle" ? "feral" : this.kit === "hammer" ? "nesa" : this.kit === "greatsword" ? "greatsword" :',
        'use Nesa-specific VRM upright style')
    return s


def main():
    parser = argparse.ArgumentParser(description="Nesa V5: High Striker no stun; loadout-safe charges; aerial spin; upright stance; half spin duration")
    parser.add_argument("project", nargs="?", help="Fight Royale web directory")
    parser.add_argument("--check", action="store_true", help="Validate patch without writing")
    args = parser.parse_args()
    root = root_at(args.project)
    print("Fight Royale project:", root)
    kits = (root / FILES[0]).read_text(encoding="utf-8")
    if MARKER in kits:
        print("[OK] Nesa V5 already installed. No duplicate edits.")
        return
    if 'NESA_HEART_SMASH_V4' not in (root / 'src/game/model.ts').read_text(encoding='utf-8'):
        raise PatchError("Requires Nesa Heart Smash V4. Install V4 before this updater.")
    mods: dict[str, bytes] = {}
    for rel in FILES:
        path = root / rel
        original = path.read_text(encoding='utf-8')
        if rel.endswith('kits.ts'):
            patched = patch_kits(original)
        elif rel.endswith('fighter.ts'):
            patched = patch_fighter(original)
        elif rel.endswith('game.ts'):
            patched = patch_game(original)
        elif rel.endswith('model.ts'):
            patched = patch_model_style(patch_model(original))
        elif rel.endswith('vrm.ts'):
            patched = patch_vrm(original)
        else:
            patched = original
        if patched != original:
            mods[rel] = patched.encode('utf-8')
    print('[CHECK]' if args.check else '[INSTALL]', len(mods), 'files to update')
    for rel in mods: print(' ', rel)
    if args.check: return
    backup = root / '.nesa_installer_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True, exist_ok=False)
    for rel in mods:
        path = root / rel
        saved = backup / rel
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, saved)
    written = []
    try:
        for rel, data in mods.items():
            path = root / rel
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                tmp.write(data)
                pending = Path(tmp.name)
            os.replace(pending, path)
            written.append(rel)
    except Exception:
        for rel in written:
            shutil.copy2(backup / rel, root / rel)
        raise
    print('[OK] Installed Nesa V5. Backup:', backup)
    print('Run: npx tsc --noEmit -p .   and   npm run dev')

if __name__ == '__main__':
    try:
        main()
    except (PatchError, OSError) as exc:
        print('INSTALL FAILED:', exc)
        sys.exit(1)
