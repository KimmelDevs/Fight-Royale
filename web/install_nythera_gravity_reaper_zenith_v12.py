#!/usr/bin/env python3
"""
NYTHERA — GRAVITY REAPER | Fight Royale one-file installer
Rebased and installation-tested against the user's latest src.zip snapshot
with Zenith V12 / Phantom Fang and spear IK already installed.

Usage (Windows PowerShell, from the Fight Royale `web` directory):
    python install_nythera_gravity_reaper_zenith_v12.py
or:
    python install_nythera_gravity_reaper_zenith_v12.py "C:\\path\\to\\Fight-Royale\\web"

- Changes are staged in memory; mandatory anchors checked before anything is written.
- Existing source files are backed up to .nythera-backups/<timestamp>/ before modification.
- Will not install over a previous Nythera installation or silently overwrite unrelated edits.
- Uses existing public/models/aster.vrm; the actual scythe is generated in three.js.
- Supabase migration is created but never executed by this installer.
- Running this program NEVER uploads, pushes, or applies a database migration.
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

MARK = "NYTHERA_GRAVITY_REAPER_INSTALL_V1"
changes: dict[str, str] = {}


def replace(rel: str, old: str, new: str, *, count: int = 1) -> None:
    current = changes[rel]
    actual = current.count(old)
    if actual != count:
        raise RuntimeError(f"{rel}: expected {count} occurrence(s) of anchor, found {actual}: {old[:130]!r}")
    changes[rel] = current.replace(old, new, count)


def append_block(rel: str, anchor: str, block: str) -> None:
    replace(rel, anchor, block + anchor)


def prepare(base: Path) -> None:
    rels = [
        "src/game/roster.ts", "src/game/kits.ts", "src/game/model.ts",
        "src/game/fighter.ts", "src/game/game.ts", "src/game/input.ts",
        "src/game/ai.ts", "src/ui/GameView.tsx", "src/game/preview.ts",
        "src/game/presentation.ts", "src/ui/Select.tsx",
    ]
    for rel in rels:
        p = base / rel
        if not p.is_file():
            raise RuntimeError(f"Missing {p}. Pass the Fight Royale 'web' folder, not src/ or repo root.")
        changes[rel] = p.read_text(encoding="utf-8-sig")
        if MARK in changes[rel] or 'id: "nythera"' in changes[rel]:
            raise RuntimeError(f"Nythera or this installer already appears in {rel}. Aborting to avoid a duplicate installation.")
    if not (base / "public/models/aster.vrm").is_file():
        raise RuntimeError("Missing public/models/aster.vrm: the requested temporary model must exist.")


def build_patches() -> None:
    # ----- ROSTER -----
    append_block("src/game/roster.ts", "\n];\n\nexport function resolveEnemy", r'''
  // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — intentionally uses Aster VRM temporarily.
  { id: "nythera", title: "Gravity Reaper", role: "Duelist - Eclipsed Mourning Scythe",
    desc: "Moonfloat dances lift the enemy; Dreadfall crushes Orbit Marks. F switches gravity. Scythe executions reward confirmed aerial combos, not unavoidable grabs.",
    stats: { power: 4, speed: 4, range: 4, defense: 2 },
    look: { name: "Nythera", body: "f", vrm: "aster", kit: "scythe", element: "gravity", outfit: "assassin", style: "long", hat: "none",
      hair: "#cbbce5", hair_shade: "#53466b", iris_top: "#763cd3", iris_bottom: "#d9bbff", eye_dark: "#1b1233",
      tunic: "#21192e", band: "#5f3996", pants: "#171324", boots: "#191628", metal: "#c6c3da", trim: "#b899ed",
      cape: "#2a2140", cape_bottom: "#7853a8", glow: "#a977f4", shield: "#242037", emblem: "#dac1ff" } },
''')

    # ----- KITS -----
    rel = "src/game/kits.ts"
    replace(rel, "  hammer: { hp: 2650, guard: 110, move: 3.05, walk: 2.45, parry: 0.15, jump: 7.0 },",
        "  hammer: { hp: 2650, guard: 110, move: 3.05, walk: 2.45, parry: 0.15, jump: 7.0 },\n"
        "  // NYTHERA_GRAVITY_REAPER_INSTALL_V1\n"
        "  scythe: { hp: 2200, guard: 76, move: 3.72, walk: 3.02, parry: 0.19, jump: 8.0 },")
    replace(rel, "    glaive: glaive,\n    bomb: bomb,", "    glaive: glaive,\n    scythe: gravityScythe,\n    bomb: bomb,")
    replace(rel, '    case "glaive":\n      return a({ name: "Arc Flash"', r'''    case "scythe":
      return a({ name: "Black Star Requiem", desc: "Draw an eclipse, lift only enemies caught by a real opening hit, then cut a falling star through them. Final crush can be dodged after recovery.",
        cd: 48, type: "melee", wind: 0.47, active: 1.10, recover: 0.68,
        dmg: 35, guard: 14, reach: 2.75, knock: 1, stun: 0.18, style: "gravity_requiem",
        pose_w: "grv_w", pose_s: "grv_float", heavy: false });
    case "glaive":
      return a({ name: "Arc Flash"''')
    replace(rel, "    glaive: [heavy.pose_w, heavy.pose_s],", "    glaive: [heavy.pose_w, heavy.pose_s],\n    scythe: [heavy.pose_w, heavy.pose_s],")
    replace(rel, '    glaive: "Thunderwheel",', '    glaive: "Thunderwheel",\n    scythe: "Eclipse Reversal",')
    replace(rel, '    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40,',
        '    wind: 2.00, sickle: 1.95, chainblade: 2.35, glaive: 2.40, scythe: 2.45,')
    replace(rel, '    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8,',
        '    wind: 1.85, sickle: 1.9, chainblade: 1.55, glaive: 1.8, scythe: 1.8,')
    replace(rel, '    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8,',
        '    wind: 4.2, sickle: 4.0, chainblade: 4.5, glaive: 4.8, scythe: 4.3,')
    append_block(rel, "function bomb(): Record<string, Attack> {", r'''
/** NYTHERA_GRAVITY_REAPER_INSTALL_V1 — four-beat curved basic string, one-handle scythe.
 * Mode-specific damage, types, and poses are resolved in Fighter.startAttack. */
function gravityScythe(): Record<string, Attack> {
  return {
    l1: a({ name: "Open Crescent", wind: 0.14, active: 0.08, recover: 0.19,
      dmg: 56, guard: 14, reach: 2.40, lunge: 2.2, knock: 0.55, stun: 0.15,
      style: "gravity_crescent", pose_w: "gr1_w", pose_s: "gr1_s", next: "l2" }),
    l2: a({ name: "Reverse Veil", wind: 0.15, active: 0.08, recover: 0.20,
      dmg: 60, guard: 15, reach: 2.42, lunge: 2.1, knock: 0.58, stun: 0.16,
      style: "gravity_crescent", pose_w: "gr2_w", pose_s: "gr2_s", next: "l3" }),
    l3: a({ name: "Sky Hook", wind: 0.17, active: 0.08, recover: 0.21,
      dmg: 68, guard: 17, reach: 2.48, lunge: 2.3, knock: 0.8, stun: 0.18,
      style: "gravity_crescent", pose_w: "gr3_w", pose_s: "gr3_s", next: "l4" }),
    l4: a({ name: "Orbit Bloom", wind: 0.21, active: 0.11, recover: 0.36,
      dmg: 90, guard: 23, reach: 2.52, lunge: 2.4, knock: 2.5, stun: 0.32,
      style: "gravity_bloom", pose_w: "gr4_w", pose_s: "gr4_s" }),
    heavy: a({ name: "Grave Descent", wind: 0.25, active: 0.10, recover: 0.58,
      dmg: 148, guard: 42, reach: 2.53, lunge: 3.15, knock: 4.4, stun: 0.46, heavy: true,
      style: "gravity_grave", pose_w: "grh_w", pose_s: "grh_s" }),
    z: a({ name: "Crescent Snare", desc: "Moonfloat: a curving hook pulls on a confirmed hit and adds Orbit Mark. Dreadfall: a slower guard-crushing hook consumes marks.",
      cd: 7.0, wind: 0.23, active: 0.10, recover: 0.38,
      dmg: 100, guard: 25, reach: 2.7, lunge: 2.5, knock: 0.85, stun: 0.24,
      style: "gravity_snare", pose_w: "grz_w", pose_s: "grz_s" }),
    x: a({ name: "Zero-G Ascension", desc: "Moonfloat: launch and pursue on a confirmed hit. Dreadfall: overhead scythe strike. Dreadfall X in midair is a landing crush.",
      cd: 10.0, wind: 0.29, active: 0.11, recover: 0.46,
      dmg: 114, guard: 30, reach: 2.64, lunge: 2.9, knock: 1.4, stun: 0.32,
      style: "gravity_ascend", pose_w: "grx_w", pose_s: "grx_s" }),
    x_air: a({ name: "Mass Descent", desc: "Dreadfall only: descend toward the enemy with the scythe, then crash down in an avoidable circle.",
      cd: 10.0, type: "strike", at: "self", mode: "dive", speed: 24,
      wind: 0.11, active: 0.12, recover: 0.51,
      dmg: 158, guard: 49, radius: 2.10, lunge: 7.0, knock: 5.8, stun: 0.51, heavy: true,
      style: "gravity_meteor", pose_w: "grx_air_w", pose_s: "grx_air_s" }),
    c: a({ name: "Event Horizon", desc: "Moonfloat: summon a small, escapable pulling field for 2.6s. Dreadfall: collapse an active field for area damage or make a short-range burst.",
      cd: 15.0, type: "buff", mode: "gravity_well", wind: 0.36, active: 0.10, recover: 0.52,
      dmg: 0, radius: 2.8, style: "gravity_well", pose_w: "grc_w", pose_s: "grc_s" }),
  };
}

''')
    # Gravity scythe pose table. Rotation convention follows existing P() poses.
    append_block(rel, "const CHAINBLADE: Record<string, Pose> = {", r'''
// NYTHERA_GRAVITY_REAPER_INSTALL_V1 — choreography: gather → suspend → sentence.
// Unlike glaives, these swings are single long arcs with two-hand grips and a settled foot plant.
const GRAVITY_SCYTHE: Record<string, Pose> = {
  ...GLAIVE,
  idle: P([0.025,-0.24,0.01],[0.0,0.20,0.01],[-0.89,-0.06,-0.16],[0.20,0,-0.12],[-0.97,0.18,0.20],[0.17,0,0.10],[-0.22,0,0.12],[0.27,0,-0.10],-0.06),
  block: P([0.13,-0.09,0],[0,0.06,0],[-1.37,0.14,-0.19],[0.22,0,-0.10],[-1.42,-0.16,0.23],[0.18,0,0.08],[-0.40,0,0.13],[0.41,0,-0.11],-0.12),
  jump: P([-0.10,-0.06,0.03],[0.04,0.09,0],[-0.88,0.10,-0.26],[0.15,0,-0.13],[-1.08,-0.12,0.25],[0.12,0,0.12],[-0.68,0,0.15],[-0.45,0,-0.13],0.03),
  gr1_w: P([0.11,-0.69,-0.07],[0,0.39,0],[-0.86,-0.74,-0.23],[0.26,0,-0.20],[-1.04,-0.47,0.18],[0.16,0,0.14],[-0.35,0,0.10],[0.40,0,-0.08],-0.09),
  gr1_s: P([0.16,0.70,0.06],[-0.04,-0.35,0],[-1.41,0.79,-0.15],[0.12,0,0.38],[-1.32,0.61,0.25],[0.08,0,0.16],[-0.45,0,0.12],[0.40,0,-0.07],-0.11),
  gr2_w: P([0.10,0.68,0.03],[0,-0.34,0],[-1.32,0.84,0.12],[0.23,0,0.22],[-1.25,0.70,0.13],[0.18,0,0.06],[-0.28,0,0.12],[0.34,0,-0.10],-0.09),
  gr2_s: P([0.18,-0.78,-0.05],[-0.09,0.48,0],[-1.28,-0.92,-0.12],[0.06,0,-0.34],[-1.43,-0.76,0.20],[0.06,0,-0.14],[-0.48,0,0.14],[0.44,0,-0.09],-0.12),
  gr3_w: P([0.29,-0.48,-0.03],[-0.16,0.32,0],[-0.66,-0.71,-0.37],[0.45,0,-0.30],[-0.85,-0.47,0.26],[0.32,0,0.04],[-0.62,0,0.10],[0.58,0,-0.07],-0.18),
  gr3_s: P([-0.23,0.31,0.05],[0.14,-0.10,0],[-2.53,0.30,-0.12],[0.18,0,0.12],[-2.28,0.27,0.11],[0.14,0,0.08],[-0.52,0,0.14],[0.36,0,-0.11],-0.12),
  gr4_w: P([0.08,-1.02,0],[0,0.58,0],[-1.04,-1.06,-0.16],[0.35,0,-0.24],[-1.17,-0.83,0.20],[0.28,0,-0.12],[-0.47,0,0.12],[0.46,0,-0.09],-0.16),
  gr4_s: P([0.18,1.08,0.06],[-0.09,-0.66,0],[-1.72,1.03,-0.04],[0.06,0,0.46],[-1.77,0.81,0.24],[0.07,0,0.29],[-0.68,0,0.13],[0.49,0,-0.11],-0.15),
  grh_w: P([-0.22,-0.48,-0.08],[0.14,0.31,0],[-2.60,-0.24,-0.17],[0.56,0,-0.06],[-2.47,-0.29,0.16],[0.43,0,0.06],[-0.55,0,0.16],[0.53,0,-0.12],-0.20),
  grh_s: P([0.51,0.34,0.10],[-0.24,-0.19,0],[-0.61,0.42,-0.29],[0.18,0,0.14],[-0.73,0.23,0.22],[0.13,0,-0.10],[-0.84,0,0.16],[0.62,0,-0.11],-0.26),
  grz_w: P([0.10,-0.77,-0.09],[-0.02,0.46,0],[-1.22,-1.06,-0.23],[0.55,0,-0.29],[-1.14,-0.68,0.15],[0.29,0,-0.19],[-0.43,0,0.12],[0.43,0,-0.10],-0.13),
  grz_s: P([0.27,0.78,0.06],[-0.12,-0.48,0],[-1.18,0.91,-0.36],[0.12,0,0.45],[-1.17,0.54,0.26],[0.08,0,0.25],[-0.63,0,0.13],[0.49,0,-0.12],-0.16),
  grx_w: P([0.45,-0.56,-0.07],[-0.15,0.36,0],[-0.69,-0.67,-0.48],[0.40,0,-0.34],[-0.86,-0.31,0.32],[0.21,0,0.05],[-0.79,0,0.15],[0.59,0,-0.10],-0.26),
  grx_s: P([-0.34,0.48,0.04],[0.17,-0.17,0],[-2.70,0.40,-0.18],[0.15,0,0.08],[-2.41,0.34,0.14],[0.11,0,0.14],[-0.66,0,0.13],[0.20,0,-0.09],-0.08),
  grx_air_w: P([-0.28,-0.13,0],[0.09,0.06,0],[-2.27,-0.21,-0.30],[0.26,0,-0.10],[-2.28,0.18,0.13],[0.14,0,0.05],[-1.12,0,0.11],[-0.96,0,-0.08],0.02),
  grx_air_s: P([0.58,0.13,0.05],[-0.29,-0.05,0],[-0.60,0.22,-0.25],[0.11,0,0.05],[-0.64,0.19,0.17],[0.09,0,-0.05],[-0.88,0,0.13],[0.69,0,-0.08],-0.25),
  grc_w: P([-0.12,-0.59,0.02],[0.08,0.27,0],[-1.68,-0.46,-0.26],[0.44,0,0.05],[-1.52,-0.38,0.20],[0.31,0,-0.06],[-0.46,0,0.12],[0.44,0,-0.09],-0.13),
  grc_s: P([0.24,0.43,0.02],[-0.12,-0.18,0],[-1.10,0.49,-0.36],[0.18,0,0.15],[-1.26,0.45,0.24],[0.16,0,0.11],[-0.62,0,0.12],[0.51,0,-0.09],-0.17),
  grv_w: P([-0.22,-0.29,-0.01],[0.13,0.10,0],[-2.60,-0.16,-0.10],[0.31,0,-0.08],[-2.52,0.14,0.08],[0.23,0,0.06],[-0.59,0,0.12],[0.50,0,-0.09],-0.17),
  grv_float: P([-0.13,0.14,0.03],[0.16,-0.07,0],[-2.24,0.21,-0.30],[0.24,0,-0.02],[-1.89,-0.23,0.36],[0.16,0,0.10],[-0.87,0,0.15],[-0.79,0,-0.11],0.05),
  grv_finish: P([0.59,0.54,0.08],[-0.27,-0.32,0],[-0.55,0.74,-0.29],[0.12,0,0.30],[-0.77,0.51,0.13],[0.08,0,0.12],[-0.91,0,0.15],[0.68,0,-0.09],-0.28),
};

''')
    # The exact anchor exists at TABLES near end.
    replace(rel, "  bow: BOW,\n  knuckles: KNUCKLES,", "  bow: BOW,\n  scythe: GRAVITY_SCYTHE,\n  knuckles: KNUCKLES,")

    # ----- INPUT: F is a special fifth command for scythe only, no global rebinding -----
    rel = "src/game/input.ts"
    replace(rel, "      if (s) this.skills.push(s);", "      if (s) this.skills.push(s);\n"
        "      // NYTHERA_GRAVITY_REAPER_INSTALL_V1: F is an optional stance skill,\n"
        "      // ignored by non-scythe fighters; ordinary remapped keys take precedence.\n"
        '      if (code === "KeyF" && !a) this.skills.push("f");')

    # ----- FIGHTER STATE + MODE + CHOREOGRAPHY -----
    rel = "src/game/fighter.ts"
    replace(rel, "  onSwing: (f: Fighter) => void = () => {};", r'''  // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — host-owned gravity state.
  gravityMode: "light" | "heavy" = "light";
  gravitySwitchCd = 0;
  gravityFloatT = 0; // short real aerial hangtime; opponent can still act / air-recover.
  onGravityShift: (f: Fighter) => void = () => {};
  onSwing: (f: Fighter) => void = () => {};''')
    replace(rel, "    for (const k in this.cooldowns) this.cooldowns[k] = Math.max(this.cooldowns[k] - dt, 0);",
        "    for (const k in this.cooldowns) this.cooldowns[k] = Math.max(this.cooldowns[k] - dt, 0);\n"
        "    this.gravitySwitchCd = Math.max(0, this.gravitySwitchCd - dt);\n"
        "    this.gravityFloatT = Math.max(0, this.gravityFloatT - dt);\n"
        '    this.model.gravityHeavy = this.kit === "scythe" && this.gravityMode === "heavy";')
    # switch during an animation, but don't grant instant invulnerability or reset attacks
    replace(rel, '    if (!k || !["z", "x", "c", "v"].includes(k)) return;', r'''    // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — same F input for local, host and AI.
    if (k === "f" && this.kit === "scythe") {
      if (this.gravitySwitchCd <= 0 && ![S.HITSTUN, S.STAGGER, S.KO, S.WIN, S.KNOCKDOWN].includes(this.state) &&
          !this.chainBoundBy && !this.status.has("freeze")) {
        this.gravityMode = this.gravityMode === "light" ? "heavy" : "light";
        this.gravitySwitchCd = 1.50;
        this.model.gravityHeavy = this.gravityMode === "heavy";
        this.model.recoil = this.gravityMode === "heavy" ? 0.36 : 0.18;
        this.onGravityShift(this);
      }
      return;
    }
    if (!k || !["z", "x", "c", "v"].includes(k)) return;''')
    # variant X in air: light jumps/strikes, heavy dashes down
    replace(rel, "    this.atk = this.attacks[id];\n    if (this.kit === \"hammer\"", r'''    this.atk = this.attacks[id];
    // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — clone each attack, never mutate its shared kit table.
    if (this.kit === "scythe" && this.atk) {
      const heavyGravity = this.gravityMode === "heavy";
      this.atk = { ...this.atk };
      if (/^l[1-4]$/.test(id)) {
        const speed = heavyGravity ? 1.13 : 0.89;
        this.atk.wind *= speed; this.atk.recover *= speed;
        if (heavyGravity) {
          this.atk.dmg *= 1.14; this.atk.guard *= 1.30;
          this.atk.knock *= 1.17;
        }
      }
      if (id === "heavy" && heavyGravity) {
        this.atk.dmg = 174; this.atk.guard = 60;
        this.atk.wind = 0.33; this.atk.knock = 6.0;
      }
      if (id === "z" && heavyGravity) {
        this.atk = { ...this.atk, name: "Crescent Sentence", dmg: 138, guard: 54,
          wind: 0.33, recover: 0.47, knock: 4.3, heavy: true,
          pose_w: "grh_w", pose_s: "grz_s", style: "gravity_sentence" };
      }
      if (id === "x" && heavyGravity) {
        this.atk = { ...this.atk, name: "Mass Cleaver", dmg: 160, guard: 53,
          wind: 0.31, recover: 0.53, knock: 4.9, heavy: true,
          pose_w: "grh_w", pose_s: "grh_s", style: "gravity_crush" };
      }
      if (id === "x_air" && !heavyGravity) {
        this.atk = { ...this.atk, type: "melee", mode: "", name: "Airborne Crescent",
          style: "gravity_ascend", wind: 0.16, active: 0.09, recover: 0.34,
          dmg: 105, guard: 24, reach: 2.4, knock: 1.0, stun: 0.25, heavy: false,
          pose_w: "grx_air_w", pose_s: "grx_s" };
      }
      if (id === "c" && heavyGravity) {
        this.atk = { ...this.atk, name: "Event Collapse", mode: "gravity_collapse",
          style: "gravity_collapse", wind: 0.34, recover: 0.58 };
      }
    }
    if (this.kit === "hammer"''')
    # movement both 3D and brawl uses factor; apply to actual velocities rather than base permanently
    replace(rel, "    if (this.state === S.IDLE && this.autoApproach && this.brain && o && !o.isDown() && dist > ENGAGE) { v = this.walkSpeed *",
        "    if (this.state === S.IDLE && this.autoApproach && this.brain && o && !o.isDown() && dist > ENGAGE) { v = this.walkSpeed * this.gravityMoveFactor() *")
    replace(rel, 'this.moveSpeed * (this.bloodFrenzyT > 0 ? 1.15 : 1) *',
        'this.moveSpeed * this.gravityMoveFactor() * (this.bloodFrenzyT > 0 ? 1.15 : 1) *')
    replace(rel, "    this.velY -= GRAVITY * dt;\n    this.root.position.y += this.velY * dt;",
        "    this.velY -= GRAVITY * (this.gravityFloatT > 0 ? 0.42 :\n"
        '      this.kit === "scythe" && this.gravityMode === "light" ? 0.78 : 1) * dt;\n'
        "    this.root.position.y += this.velY * dt;")
    replace(rel, "  private move(dt: number) {", r'''  private gravityMoveFactor(): number {
    if (this.kit !== "scythe") return 1;
    return this.gravityMode === "light" ? 1.15 : 0.86;
  }
  private move(dt: number) {''')
    # platform movement
    replace(rel, 'mx * this.moveSpeed * (this.state === S.CHARGE ? 0.3 : 1.55)',
        'mx * this.moveSpeed * this.gravityMoveFactor() * (this.state === S.CHARGE ? 0.3 : 1.55)')
    replace(rel, 'mx * this.walkSpeed * 0.85', 'mx * this.walkSpeed * this.gravityMoveFactor() * 0.85')
    # dedicated choreography / moving weapon while remaining two handed
    replace(rel, "        if (this.poseOverride) { p = this.poseOverride; sp = 40; break; }", r'''        if (this.poseOverride) { p = this.poseOverride; sp = 40; break; }
        // NYTHERA_GRAVITY_REAPER_INSTALL_V1: anticipation → cut → measured follow-through.
        if (this.kit === "scythe" && a) {
          const elapsed = this.stateT - a.wind;
          if (a.style === "gravity_requiem") {
            p = elapsed < 0 ? "grv_w" : elapsed < 0.50 ? "grv_float" : "grv_finish";
            sp = elapsed < 0 ? 18 : elapsed < 0.50 ? 23 : 49;
          } else if (a.mode === "dive" && this.atkPhase === 1) {
            p = "grx_air_w"; sp = 17;
          } else if (this.atkPhase === 0) { p = a.pose_w; sp = this.gravityMode === "heavy" ? 15 : 22; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = this.gravityMode === "heavy" ? 39 : 55; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.64) { p = a.pose_s; sp = 18; }
          else { p = "idle"; sp = 13; }
          break;
        }''')
    # Append after Zenith V12 field #59; do not overwrite existing snapshot slots.
    # Nythera fields occupy slots 60, 61, and 62 for host/client consistency.
    replace(rel, '+this.zenithMagneticChargeT.toFixed(2)];',
        '+this.zenithMagneticChargeT.toFixed(2), this.gravityMode === "heavy" ? 1 : 0, +this.gravitySwitchCd.toFixed(2), +this.gravityFloatT.toFixed(2)];')
    replace(rel, "    this.frostShieldT = s.length > 55 ? s[55] : 0;",
        '    this.frostShieldT = s.length > 55 ? s[55] : 0;\n'
        '    this.gravityMode = s.length > 60 && s[60] === 1 ? "heavy" : "light";\n'
        '    this.gravitySwitchCd = s.length > 61 ? s[61] : 0;\n'
        '    this.gravityFloatT = s.length > 62 ? s[62] : 0;\n'
        '    this.model.gravityHeavy = this.kit === "scythe" && this.gravityMode === "heavy";')
    replace(rel, "    for (const key in this.cooldowns) this.cooldowns[key] = Math.max(this.cooldowns[key] - dt, 0);",
        "    for (const key in this.cooldowns) this.cooldowns[key] = Math.max(this.cooldowns[key] - dt, 0);\n"
        '    this.model.gravityHeavy = this.kit === "scythe" && this.gravityMode === "heavy";')

    # ----- MODEL: custom crescent blade, eclipse rings, grip and readable arc -----
    rel = "src/game/model.ts"
    replace(rel, '  private glaivePivot: THREE.Group | null = null;',
        '  private glaivePivot: THREE.Group | null = null;\n'
        '  // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — purely visual, synced via Fighter.snapshot.\n'
        '  gravityHeavy = false;\n'
        '  private gravityHalo: THREE.Group | null = null;\n'
        '  private gravityScythe: THREE.Group | null = null;')
    replace(rel, '      case "sickle": this.buildSickles(); break;',
        '      case "sickle": this.buildSickles(); break;\n'
        '      case "scythe": this.buildGravityScythe(); break;')
    append_block(rel, "  /** ZAREK_STORM_V1: double-ended conductive glaive; meshes follow the VRM's hands. */", r'''
  /** NYTHERA_GRAVITY_REAPER_INSTALL_V1 — Eclipsed Mourning, not a reused sickle.
   * The crescent is an extruded Bezier steel blade with a separate glowing cutting rim.
   * Right hand holds shaft, left hand IK is anchored lower on the same grip. */
  private buildGravityScythe() {
    const scythe = pivot(this.hand_r, [0, 0, 0], [PI / 2, 0, 0]);
    scythe.name = "Eclipsed Mourning — Nythera";
    scythe.scale.setScalar(0.95);
    this.gravityScythe = scythe;
    const dark = this.tn("#161528"), steel = this.tn("#d3d4e4");
    const edgeSteel = this.tn("#eeeaff"), gold = this.tn("#ac8ac8");
    mesh(scythe, cyl(0.019, 0.021, 1.87, 12), dark, [0,-0.04,0]);
    mesh(scythe, cyl(0.025, 0.025, 0.59, 12), this.tn("#403653"), [0,-0.15,0]);
    for (const y of [-0.40,-0.18,0.02,0.22,0.74]) {
      mesh(scythe, torus(0.023,0.029), gold, [0,y,0], [PI/2,0,0]);
    }
    // A slim secondary ferrule keeps the hooked metal silhouette readable.
    mesh(scythe, cyl(0.047, 0.029, 0.19, 12), steel, [0,0.76,0]);
    const shape = new THREE.Shape();
    shape.moveTo(-0.02, 0.73);
    shape.bezierCurveTo(-0.38, 0.99, -0.76, 1.17, -0.95, 1.67);
    shape.bezierCurveTo(-0.84, 1.56, -0.69, 1.51, -0.55, 1.48);
    shape.bezierCurveTo(-0.35, 1.42, -0.22, 1.21, -0.13, 1.04);
    shape.bezierCurveTo(-0.09, 0.91, -0.05, 0.82, -0.02, 0.73);
    shape.closePath();
    const geo = new THREE.ExtrudeGeometry(shape, { depth:0.033, bevelEnabled:true,
      bevelThickness:0.008, bevelSize:0.008, bevelSegments:2, curveSegments:22 });
    geo.translate(0,0,-0.0165);
    mesh(scythe, geo, steel);
    // Polished hooked cutting edge is visibly thinner than the whole blade.
    const edgeCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.035,0.76,0.034), new THREE.Vector3(-0.33,1.00,0.034),
      new THREE.Vector3(-0.64,1.25,0.034), new THREE.Vector3(-0.95,1.67,0.034)]);
    mesh(scythe, new THREE.TubeGeometry(edgeCurve, 26, 0.009, 5, false), edgeSteel);
    const rear = pivot(scythe,[0,-0.94,0]);
    mesh(rear, sphere(0.068,16), gold, [0,0,0],[0,0,0],[1,1.2,0.62]);
    mesh(rear, sphere(0.038,12), this.gem(), [0,-0.014,0]);
    const collar = pivot(scythe,[0,0.82,0]);
    mesh(collar,sphere(0.080,16),this.gem());
    mesh(collar,sphere(0.034,12),this.glowMat,[0,0,0.06]);
    this.gravityHalo = collar;
    for (let i=0;i<2;i++) {
      const ring = pivot(collar,[0,0,0], [i ? PI/2.8 : PI/10, 0, i ? 0.7 : 0.1]);
      mesh(ring, new THREE.TorusGeometry(0.15+i*0.045, 0.007, 6, 48), this.glowMat);
    }
    this.gripL = pivot(scythe,[0,-0.29,0]);
    // Use cutting-edge positions for native trails, melee contact and weapon clash.
    this.bladeBase = pivot(scythe,[-0.18,0.98,0]);
    this.bladeTip = pivot(scythe,[-0.94,1.64,0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = scythe;
  }

''')
    replace(rel, '    this.glowMat.color.copy(this.glowBase).lerp(', r'''    if (this.gravityScythe) {
      // Weapon vibrates gently in Moonfloat, then visually locks in Dreadfall.
      this.gravityScythe.rotation.z = Math.sin(this.t * 2.25) * (this.gravityHeavy ? 0.006 : 0.022);
      if (this.gravityHalo) {
        this.gravityHalo.rotation.y += dt * (this.gravityHeavy ? 0.52 : 1.9);
        this.gravityHalo.scale.setScalar(this.gravityHeavy ? 0.82 : 1.12 + Math.sin(this.t*3.3)*0.055);
      }
      if (!this.combat && this.walk < 0.12) {
        this.hips.position.y += this.gravityHeavy ? -0.022 : 0.020 + Math.sin(this.t*1.9)*0.009;
        this.torso.rotation.y += Math.sin(this.t*1.35)*0.012;
      }
      if (this.gravityHeavy && this.walk > 0.05) this.hips.position.y -= 0.018;
    }
    this.glowMat.color.copy(this.glowBase).lerp(''')
    replace(rel, '    this.vrmRig.glaive = this.kit === "glaive";',
        '    this.vrmRig.glaive = this.kit === "glaive" || this.kit === "scythe";')
    replace(rel, 'this.kit === "glaive" ? 0.24 : this.kit === "sickle" ?',
        'this.kit === "glaive" ? 0.24 : this.kit === "scythe" ? 0.21 : this.kit === "sickle" ?')
    replace(rel, 'this.kit === "chainblade" ? 0.58 : this.kit === "glaive" ? 0.4 : 1;',
        'this.kit === "chainblade" ? 0.58 : this.kit === "glaive" ? 0.4 : this.kit === "scythe" ? 0.50 : 1;')
    replace(rel, 'this.kit === "glaive" ? 0.87 : VRM_WEAPON_SCALE;',
        'this.kit === "glaive" ? 0.87 : this.kit === "scythe" ? 0.82 : VRM_WEAPON_SCALE;')

    # ----- AI: intentional mode choice without affecting AI design for other fighters -----
    rel = "src/game/ai.ts"
    replace(rel, '    if (!o || o.isDown()) return;\n    this.observeAerialOpponent(f, o);', r'''    if (!o || o.isDown()) return;
    // NYTHERA_GRAVITY_REAPER_INSTALL_V1 — AI builds marks in Light,
    // switches to Heavy only near a confirmed punish window, then floats to chase.
    if (f.kit === "scythe" && f.gravitySwitchCd <= 0 && f.state === S.IDLE &&
        !f.intent.skill && !f.intent.attack && !f.intent.block) {
      const dist = f.root.position.distanceTo(o.root.position);
      const closePunish = dist < 2.55 && (o.stunRemaining > 0.13 ||
        o.state === S.STAGGER || o.state === S.ATTACK && o.atkPhase === 2);
      if (f.gravityMode === "light" && closePunish) f.intent.skill = "f";
      if (f.gravityMode === "heavy" && dist > 3.25) f.intent.skill = "f";
    }
    this.observeAerialOpponent(f, o);''')

    # ----- HUD -----
    rel = "src/game/game.ts"
    replace(rel, '      chainBindKind: f.chainBindKind, frostShardStacks:',
        '      chainBindKind: f.chainBindKind, gravityMode: f.gravityMode, gravitySwitchCd: f.gravitySwitchCd, frostShardStacks:')
    replace(rel, '      if (f.kit === "hammer") passives.push({ label: "HEARTS",',
        '      if (f.kit === "scythe") passives.push({ label: "GRAVITY", value: f.gravityMode === "light" ? "MOONFLOAT" : "DREADFALL" });\n'
        '      if (f.kit === "hammer") passives.push({ label: "HEARTS",')
    rel = "src/ui/GameView.tsx"
    replace(rel, '          {!cfg.spectator && <div className="skills">', r'''          {/* NYTHERA_GRAVITY_REAPER_INSTALL_V1 — readable mode, not a fifth purchased skill. */}
          {me?.id === "nythera" && !cfg.spectator && <div style={{
            position: "absolute", bottom: 142, left: "50%", transform: "translateX(-50%)",
            border: "1px solid #a977f4", background: "rgba(16,9,29,.80)",
            borderRadius: 18, padding: "6px 16px", color: "#e6d2ff",
            fontWeight: 800, fontSize: 12, zIndex: 5, whiteSpace: "nowrap",
          }}>
            {me.gravityMode === "heavy" ? "◈ DREADFALL — HEAVY" : "◌ MOONFLOAT — LIGHT"}
            <span style={{ opacity: .70, marginLeft: 12 }}>
              {me.gravitySwitchCd > 0 ? `F ${me.gravitySwitchCd.toFixed(1)}s` : "F to switch"}
            </span>
          </div>}
          {!cfg.spectator && <div className="skills">''')


def game_patches() -> None:
    rel = "src/game/game.ts"
    replace(rel, "  private remoteBrains = new Map<string, RemoteBrain>();", r'''  // NYTHERA_GRAVITY_REAPER_INSTALL_V1: separate marks for every caster and victim.
  private gravityMarks = new Map<string, { stacks: number; expires: number }>();
  private gravityWells: { owner: Fighter; center: THREE.Vector3; left: number; pulse: number }[] = [];
  private remoteBrains = new Map<string, RemoteBrain>();''')
    replace(rel, "  private clearAll() {\n    for (const e of this.entities.values())", r'''  private clearAll() {
    this.gravityMarks.clear();
    this.gravityWells = [];
    for (const e of this.entities.values())''')
    replace(rel, '    f.onSwing = (x) => this.onSwing(x);', r'''    f.onSwing = (x) => this.onSwing(x);
    f.onGravityShift = (x) => {
      this.fxp("ring", x.root.position.clone().add(new THREE.Vector3(0, 0.22, 0)),
        x.gravityMode === "heavy" ? "#62309c" : "#c9aaff", 1.65, 0.28, 0.92);
      this.fxp("sparks", x.model.bladeTip.getWorldPosition(new THREE.Vector3()),
        x.gravityMode === "heavy" ? "#ac69fa" : "#d8c1ff", 20, 4);
      this.fxp("flash", x.chest(), "#b18af5", 0.34, 0.16, 0.65);
      this.fxp("num", x.chest().add(new THREE.Vector3(0, 0.80, 0)),
        x.gravityMode === "heavy" ? "DREADFALL" : "MOONFLOAT", "#dbbcff", 0.85);
      this.snd(x.gravityMode === "heavy" ? "slam" : "teleport", 0.40);
    };''')
    replace(rel, '    this.updateRoxyFreezeVisuals(dt);', '    this.updateRoxyFreezeVisuals(dt);\n    if (this.cfg.role !== "client") this.updateGravityWells(dt);')
    replace(rel, '  private onSwing(f: Fighter) {', r'''  /** NYTHERA_GRAVITY_REAPER_INSTALL_V1 — persistent escapeable well, 0 damage by itself. */
  private updateGravityWells(dt: number) {
    for (const w of this.gravityWells) {
      w.left -= dt;
      w.pulse -= dt;
      if (w.left <= 0 || w.owner.isDown()) continue;
      if (w.pulse <= 0) {
        w.pulse = 0.40;
        const pos = w.center.clone().add(new THREE.Vector3(0,0.10,0));
        this.fxp("ring", pos, "#9963e6", 2.9, 0.45, 0.53);
        this.fxp("motes", pos.clone().add(new THREE.Vector3(0,0.8,0)), "#bda0f5", 9);
      }
      for (const d of this.enemiesOf(w.owner)) {
        if (d.isDown()) continue;
        const towards = w.center.clone().sub(d.root.position).setY(0);
        const dist = towards.length();
        if (dist < 0.35 || dist > 3.0 || Math.abs(d.root.position.y - w.center.y) > 2.0) continue;
        // Gradual position nudges remain escapable by sprint, dash and normal steering.
        if (d instanceof Fighter && (d.dashing() || d.invulnT > 0 || d.knockedDown())) continue;
        const pull = Math.min(0.65 * dt, Math.max(0, dist - 0.75));
        if (pull > 0) d.root.position.addScaledVector(towards.normalize(), pull);
      }
    }
    this.gravityWells = this.gravityWells.filter(w => w.left > 0 && !w.owner.isDown());
  }

  /** Switch-aware skill choreography. Damage always goes through normal hit resolution. */
  private nytheraSwing(f: Fighter, a: Attack): boolean {
    if (f.kit !== "scythe") return false;
    const tip = f.model.bladeTip.getWorldPosition(new THREE.Vector3());
    const light = f.gravityMode === "light";
    const col = light ? "#be9dff" : "#8141c9";
    if (a.style === "gravity_well") {
      const toward = new THREE.Vector3(Math.sin(f.root.rotation.y),0,Math.cos(f.root.rotation.y));
      const center = f.root.position.clone().addScaledVector(toward, 1.7);
      center.y = f.root.position.y;
      this.gravityWells = this.gravityWells.filter(w => w.owner !== f);
      this.gravityWells.push({ owner:f, center, left:2.6, pulse:0 });
      this.fxp("ring", center, "#d3b8ff", 3.1, 0.41, 0.82);
      this.fxp("orb", center.clone().add(new THREE.Vector3(0, 0.8, 0)), 0.42);
      this.snd("cast", 0.62);
      return true;
    }
    if (a.style === "gravity_collapse") {
      const well = this.gravityWells.find(w => w.owner === f && w.left > 0);
      const center = well ? well.center.clone() : f.root.position.clone().addScaledVector(
        new THREE.Vector3(Math.sin(f.root.rotation.y),0,Math.cos(f.root.rotation.y)), 1.35);
      this.gravityWells = this.gravityWells.filter(w => w !== well);
      const round = this.round, serial = f.swingSerial;
      this.fxp("ring", center.clone().add(new THREE.Vector3(0,0.3,0)), "#46266f", 3.0, 0.26, 0.92);
      this.snd("sci_fi_gear_turn", 0.65);
      this.laterCombo(f, 0.20, () => {
        if (round !== this.round || f.isDown() || f.swingSerial !== serial) return;
        const radius = well ? 2.95 : 2.25;
        this.fxp("ring", center, "#bc84ff", radius * 1.25, 0.28, 0.92);
        this.fxp("rocks", center, 18, 0.9);
        this.fxp("flash", center.clone().add(new THREE.Vector3(0, 0.65, 0)), "#e7d3ff", 0.8, 0.13, 0.82);
        this.snd("slam", 0.78);
        this.add_trauma(0.28);
        const shock: Attack = { ...a, type:"strike", dmg:160, guard:54,
          knock:5.2, stun:0.44, heavy:true, radius, style:"gravity_collapse" };
        for (const d of this.enemiesOf(f)) {
          const delta = d.root.position.clone().sub(center);
          const dy = Math.abs(delta.y); delta.y = 0;
          if (delta.length() > radius + d.radius * 0.4 || dy > 1.85) continue;
          this.applyHit(f, d, shock, f.atkPower, d.chest(), delta.lengthSq() > 0.01
            ? delta.normalize() : new THREE.Vector3(0,0,1), true);
        }
      });
      return true;
    }
    if (a.style === "gravity_requiem") {
      const round = this.round, serial = f.swingSerial;
      const hitTargets: Entity[] = [];
      const near = f.root.position.clone();
      this.fxp("ring", near.clone().add(new THREE.Vector3(0, 1.4, 0)), "#aa78e2", 3.7, 0.40, 0.96);
      this.fxp("orb", near.clone().add(new THREE.Vector3(0, 3.0, 0)), 0.48);
      this.fxp("motes", near.clone().add(new THREE.Vector3(0, 1.5, 0)), "#b38bf8", 36);
      this.snd("teleport", 0.73);
      // The opening is blockable/parryable; a defended opponent is NEVER lifted.
      for (const d of this.enemiesOf(f)) {
        const to = d.root.position.clone().sub(f.root.position); const dy = Math.abs(to.y); to.y = 0;
        if (to.length() > 2.8 + d.radius*0.5 || dy > 1.5) continue;
        const dir = to.lengthSq() > 0.01 ? to.normalize() : new THREE.Vector3(0,0,1);
        const result = this.applyHit(f, d, a, f.atkPower, d.chest(), dir, false);
        if (["hit", "crit"].includes(result)) {
          hitTargets.push(d);
          if (d instanceof Fighter && !d.stage && !d.isDown()) {
            d.onGround = false; d.velY = Math.max(d.velY, 6.2); d.gravityFloatT = 0.70;
          }
        }
      }
      if (hitTargets.length === 0) return true;
      // Nythera takes the high line of the choreography. This is NOT a teleport or invuln.
      if (!f.stage) { f.onGround = false; f.velY = Math.max(f.velY, 6.8); }
      this.laterCombo(f, 0.37, () => {
        if (round !== this.round || f.isDown() || f.swingSerial !== serial) return;
        f.poseOverride = "grv_float";
        this.fxp("ring", f.chest(), "#debdff", 2.4, 0.26, 0.86);
        this.fxp("sparks", f.model.bladeTip.getWorldPosition(new THREE.Vector3()), "#dbc7ff", 25, 4);
        for (const d of hitTargets) {
          if (d.isDown() || d.root.position.distanceTo(f.root.position) > 5.0) continue;
          const follow: Attack = {...a, dmg:55, guard:15, stun:0.13, knock:0.4};
          const dir = d.root.position.clone().sub(f.root.position).setY(0).normalize();
          this.applyHit(f, d, follow, f.atkPower, d.chest(), dir, false);
        }
      });
      this.laterCombo(f, 0.84, () => {
        if (round !== this.round || f.isDown() || f.swingSerial !== serial) return;
        f.poseOverride = "grv_finish";
        f.velY = -Math.max(13, Math.abs(f.velY));
        const impact = f.root.position.clone().setY(this.plat ? f.root.position.y : 0);
        this.fxp("ring", impact, "#6a2ba4", 4.1, 0.44, 0.98);
        this.fxp("flash", impact.clone().add(new THREE.Vector3(0,0.7,0)), "#f1ddff", 1.4, 0.18, 0.9);
        this.fxp("rocks", impact, 30, 1.4);
        this.fxp("sparks", impact.clone().add(new THREE.Vector3(0,1,0)), "#b388ff", 45, 7);
        this.snd("dramatic_metal_explosion_impact", 0.78);
        this.add_trauma(0.55);
        const final: Attack = {...a, dmg:200, guard:55, knock:8.2, stun:0.55, heavy:true};
        for (const d of hitTargets) {
          if (d.isDown()) continue;
          const diff = d.root.position.clone().sub(impact);
          const dy = Math.abs(diff.y); diff.y = 0;
          if (diff.length() > 4.1 + d.radius*0.4 || dy > 4.4) continue;
          this.applyHit(f, d, final, f.atkPower, d.chest(),
            diff.lengthSq() > 0.01 ? diff.normalize() : new THREE.Vector3(0,0,1), false);
        }
      });
      return true;
    }
    this.fxp("slashes", tip, col);
    this.fxp("flash", tip, light ? "#dbc7ff" : "#9d5cea", light ? 0.22 : 0.36, 0.12, 0.72);
    if (a.heavy || a.id === "l4" || a.id === "x")
      this.fxp("ring", tip, col, light ? 0.78 : 1.13, 0.23, 0.75);
    if (a.style === "gravity_meteor") {
      const origin = f.root.position.clone().setY(this.plat ? f.root.position.y : 0);
      this.fxp("ring", origin, "#7b3db9", 2.4, 0.28, 0.92);
      this.fxp("rocks", origin, 17, 0.8); this.add_trauma(0.30);
      this.snd("slam", 0.68);
      // Dive has already landed via Fighter.attackStep; use the normal area hit routine.
      this.runStrike(f, {...a, delay:0.02}, f.atkPower);
      return true;
    }
    // Snap to the real impact point. Every cut is still parryable and clashable.
    this.melee(f, a);
    return true;
  }

  private onSwing(f: Fighter) {''')
    replace(rel, '    this.swingSound(f, a);\n    if (f.look.element === "metal"',
        '    this.swingSound(f, a);\n'
        '    if (this.nytheraSwing(f, a)) return;\n'
        '    if (f.look.element === "metal"')
    # applyHit: mark stacks and mode bonus granted only for real unblocked damage
    replace(rel, '    const result = d.receiveHit(attacker, zenithAttack, riposte ? power * 1.15 : power);', r'''    const gravityOwner = attacker instanceof Fighter && attacker.kit === "scythe" ? attacker : null;
    const markKey = gravityOwner ? `${gravityOwner.id}:${d.id}` : "";
    const mark = gravityOwner ? this.gravityMarks.get(markKey) : undefined;
    const marks = mark && mark.expires > this.time ? mark.stacks : 0;
    const heavySentence = !!gravityOwner && gravityOwner.gravityMode === "heavy" &&
      a.dmg > 0 && a.style !== "gravity_well" && a.style !== "gravity_requiem";
    const sentenceMult = heavySentence ? 1 + marks * 0.08 : 1;
    const result = d.receiveHit(attacker, zenithAttack, (riposte ? power * 1.15 : power) * sentenceMult);
    // Each real Moonfloat hit earns ONE mark; miss, block, parry, clash do not.
    if (gravityOwner && ["hit", "crit"].includes(result) && a.dmg > 0) {
      if (heavySentence) {
        this.gravityMarks.delete(markKey);
        if (marks > 0) {
          this.fxp("ring", d.chest(), "#8250d9", 0.72 + marks * 0.24, 0.25, 0.76);
          this.fxp("num", d.chest().add(new THREE.Vector3(0,0.73,0)),
            `ORBIT BURST ×${marks}`, "#ddb5ff", 0.70);
        }
      } else if (gravityOwner.gravityMode === "light" && a.style !== "gravity_requiem") {
        const n = Math.min(3, marks + 1);
        this.gravityMarks.set(markKey, { stacks:n, expires:this.time + 4 });
        this.fxp("ring", d.chest(), "#b68ef7", 0.41 + n*0.14, 0.18, 0.58);
        if (n === 3) this.fxp("num", d.chest().add(new THREE.Vector3(0,0.69,0)),
          "ORBIT x3", "#d9c0ff", 0.66);
      }
      if (d instanceof Fighter && !d.stage && !d.isDown()) {
        if (a.style === "gravity_ascend" ||
            (a.style === "gravity_snare" && marks >= 2)) {
          d.onGround = false;
          d.velY = Math.max(d.velY, a.style === "gravity_ascend" ? 6.5 : 4.6);
          d.gravityFloatT = a.style === "gravity_ascend" ? 0.65 : 0.43;
          if (a.style === "gravity_ascend") {
            gravityOwner.onGround = false;
            gravityOwner.velY = Math.max(gravityOwner.velY, 6.1);
          }
          this.fxp("ring", d.root.position.clone(), "#ceb2ff", 1.25, 0.23, 0.73);
          this.fxp("sparks", d.chest(), "#d5baff", 20, 3.9, [0,1,0]);
        } else if (a.style === "gravity_snare") {
          // A short hook pull only on a confirmed hit; no guaranteed long stun.
          const to = gravityOwner.root.position.clone().sub(d.root.position).setY(0);
          const dist = to.length();
          if (dist > 1.15) d.root.position.addScaledVector(to.normalize(), Math.min(0.78, dist - 1.15));
        }
      }
    }''')


def choreography_patches() -> None:
    """Selection-only weapon detach/throw/catch; separate combat scythe wrist choreography."""
    rel = "src/game/model.ts"
    replace(rel, "  private gravityScythe: THREE.Group | null = null;", r'''  private gravityScythe: THREE.Group | null = null;
  // NYTHERA_SHOWCASE_SPIN_TOSS_V3 — cosmetic duplicate used only in character preview.
  private gravityPreviewFlyer: THREE.Group | null = null;
  private gravityShowFlying = false;
  private gravityShowLaunchP = new THREE.Vector3();
  private gravityShowLaunchQ = new THREE.Quaternion();
  private gravityShowLaunchScale = new THREE.Vector3(1,1,1);
  private gravityShowEclipse: THREE.Mesh | null = null;
  private gravityShowTrails: THREE.Group | null = null;
  scytheBeat = 0;''')

    replace(rel, '    if (this.look.element === "metal" && this.zenithSpearRightGrip &&', r'''    // NYTHERA_SHOWCASE_SPIN_TOSS_V3 — offhand releases for presentation spins/toss only.
    const tShow = this.presentationT;
    const oneHandFlourish = (tShow >= 0.78 && tShow < 1.22) ||
      (tShow >= 2.34 && tShow < 3.13) ||
      (tShow >= 5.69 && tShow < 6.24);
    const airborneWeapon = tShow >= 3.13 && tShow < 5.52;
    const noScytheGrip = this.kit === "scythe" && this.glaivePose === "nythera_show" &&
      this.presentationMode === "select" && (oneHandFlourish || airborneWeapon);
    if (this.vrmRig && this.kit === "scythe") this.vrmRig.gripL = noScytheGrip ? null : this.gripL;
    if (this.look.element === "metal" && this.zenithSpearRightGrip &&''')
    replace(rel, '    } else if (this.gripL) this.reachGrip();',
        '    } else if (this.gripL && !noScytheGrip) this.reachGrip();')

    replace(rel, r'''      // Weapon vibrates gently in Moonfloat, then visually locks in Dreadfall.
      this.gravityScythe.rotation.z = Math.sin(this.t * 2.25) * (this.gravityHeavy ? 0.006 : 0.022);''', r'''      // NYTHERA_SHOWCASE_SPIN_TOSS_V3: actual scythe transforms now match body beats.
      // Handheld rotations only: preview's thrown copy has no gameplay collider.
      const scytheAngles: Record<string, [number,number,number]> = {
        idle: [PI/2,-0.12,0.09], block: [1.83,-0.15,-0.16],
        gr1_w: [1.88,-0.64,-0.28], gr1_s: [0.85,0.76,0.31],
        gr2_w: [1.13,0.68,0.35], gr2_s: [2.13,-0.84,-0.29],
        gr3_w: [2.13,-0.60,-0.43], gr3_s: [0.67,0.40,0.28],
        gr4_w: [1.86,-0.74,0.30], gr4_s: [1.16,0.86,-0.35],
        grh_w: [2.20,-0.32,0.20], grh_s: [0.74,0.53,-0.12],
        grz_w: [1.93,-0.69,-0.25], grz_s: [0.91,0.84,0.30],
        grx_w: [2.20,-0.63,-0.37], grx_s: [0.59,0.31,0.22],
        grx_air_w: [2.23,0.08,-0.23], grx_air_s: [0.75,0.55,0.12],
        grc_w: [1.88,-0.31,0.11], grc_s: [1.26,0.51,0.22],
        grv_w: [2.31,0.13,0.09], grv_float: [1.89,0.24,-0.13],
        grv_finish: [0.51,0.69,0.18],
      };
      const a = scytheAngles[this.glaivePose] ?? scytheAngles.idle;
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...a, "YXZ"));
      if (this.glaivePose === "nythera_show") {
        const t = this.presentationT;
        // Four full figure-eight/overhead spins before the throw, three after catch.
        // All segments end at whole revolutions so the weapon doesn't visually snap.
        const ease = (x:number,lo:number,hi:number) => THREE.MathUtils.smoothstep(x,lo,hi);
        const forwardSpin = 2*Math.PI*(
          ease(t,0.65,1.20) + ease(t,1.23,1.66) +
          ease(t,1.69,2.22) + ease(t,2.32,3.08));
        const returnSpin = 2*Math.PI*(
          ease(t,5.66,6.14) + ease(t,6.16,6.62) + ease(t,6.65,7.21));
        const spin = forwardSpin + returnSpin;
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),spin));
        // Rolling the long shaft completes the wrist-led figure-eight silhouette.
        const flourish = ((t>=0.65 && t<3.12) || (t>=5.65 && t<7.23)) ? 1 : 0;
        // Crossing figure-eight planes, alternating front/back shaft planes, not
        // just a flat propeller spin. The scythe remains visible edge-on in motion.
        const plane = Math.sin(t * 7.7) * 0.46 * flourish;
        const roll = Math.sin(t * 11.2) * 0.29 * flourish;
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),plane));
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),roll));
      } else {
        // The weapon itself, not only the body, performs circular finishers.
        // Each spin ends at a whole revolution so pose changes have no pop.
        const combatTurns: Record<string,number> = {
          gr4_s: 1, grz_s: 1, grc_s: 1,
          grv_float: 2, grv_finish: 2,
        };
        const count = combatTurns[this.glaivePose] ?? 0;
        if (count > 0) {
          const w = this.scytheBeat * this.scytheBeat * (3-2*this.scytheBeat);
          q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),
            w * count * Math.PI * 2));
          q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),
            Math.sin(w*Math.PI*2)*0.32));
        }
      }
      this.gravityScythe.quaternion.slerp(q,1-Math.exp(-(this.glaivePose.endsWith("_s") ? 40 : 22)*dt));''')

    # Add a public per-frame preview-only visual method; never used by fighter/hit code.
    append_block(rel, "  /** Aims the left arm (shoulder to hand along local -Y) at the weapon's grip point. */", r'''
  /** NYTHERA_SHOWCASE_SPIN_TOSS_V3 — pure character-select choreography.
   * The held scythe stays on its original right-hand pivot / IK grip.  During the throw,
   * an uncollidable duplicate performs multiple full 3D revolutions and then interpolates
   * exactly into the current hand transform for a snap-free catch. */
  animateNytheraShowcase(phase: number, dt: number) {
    const held = this.gravityScythe;
    if (!held || this.kit !== "scythe") return;
    if (!this.gravityPreviewFlyer) {
      const flyer = held.clone(true);
      flyer.name = "Nythera selection-only flying scythe";
      flyer.visible = false;
      // Clone is visual only: no blade point, collision, hitbox or combat attachment.
      this.add(flyer);
      this.gravityPreviewFlyer = flyer;
      const eclipse = new THREE.Mesh(new THREE.TorusGeometry(0.78,0.014,8,72),
        new THREE.MeshBasicMaterial({color:"#bd83ff",transparent:true,opacity:0,depthWrite:false}));
      eclipse.position.set(0,1.22,-0.28);
      eclipse.rotation.x = 0.20;
      eclipse.visible = true;
      this.add(eclipse);
      this.gravityShowEclipse = eclipse;
      // Slim geometric crescents trail her spins, never opaque VFX smoke.
      // Local to the selection model and never registered with combat FX.
      const trails = new THREE.Group();
      for (const [i,r] of [0.66,0.90,1.15].entries()) {
        const mat = new THREE.MeshBasicMaterial({color:i===0?"#d4b5ff":"#8d62cf",
          transparent:true,opacity:0,depthWrite:false,side:THREE.DoubleSide});
        trails.add(new THREE.Mesh(new THREE.TorusGeometry(r,0.007,5,52,
          Math.PI*(i===1?1.42:1.10)),mat));
      }
      this.add(trails);
      this.gravityShowTrails = trails;
    }
    const flyer = this.gravityPreviewFlyer!;
    const flyStart = 3.13, flyEnd = 5.52;
    const flying = phase >= flyStart && phase < flyEnd;
    this.updateMatrixWorld(true);
    const rootWorld = this.getWorldQuaternion(new THREE.Quaternion());
    const inRoot = (o: THREE.Object3D) => this.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const gripP = inRoot(held);
    const gripQ = rootWorld.clone().invert().multiply(held.getWorldQuaternion(new THREE.Quaternion()));
    const gripS = held.getWorldScale(new THREE.Vector3()).divide(this.getWorldScale(new THREE.Vector3()));
    if (flying && !this.gravityShowFlying) {
      this.gravityShowLaunchP.copy(gripP);
      this.gravityShowLaunchQ.copy(gripQ);
      this.gravityShowLaunchScale.copy(gripS);
    }
    this.gravityShowFlying = flying;
    held.visible = !flying;
    flyer.visible = flying;
    if (flying) {
      const u = THREE.MathUtils.clamp((phase-flyStart)/(flyEnd-flyStart),0,1);
      const smooth = u*u*(3-2*u);
      const lift = Math.sin(Math.PI*u);
      // An airborne figure-eight, not a linear boomerang. Ends precisely at the hand.
      flyer.position.copy(this.gravityShowLaunchP).lerp(gripP,smooth);
      flyer.position.x -= Math.sin(u*Math.PI*2)*lift*0.66;
      flyer.position.y += lift*0.44 + Math.sin(u*Math.PI*4)*lift*0.08;
      flyer.position.z += lift*0.16;
      flyer.quaternion.copy(this.gravityShowLaunchQ).slerp(gripQ,smooth);
      flyer.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(
        new THREE.Vector3(0,0,1),u*Math.PI*8));  // 4 forward somersaults
      flyer.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(
        new THREE.Vector3(0,1,0),u*Math.PI*4));  // 2 shaft rolls
      flyer.scale.copy(this.gravityShowLaunchScale).lerp(gripS,smooth);
    }
    if (this.gravityShowEclipse) {
      const ring = this.gravityShowEclipse;
      const late = THREE.MathUtils.smoothstep(phase,6.90,7.32) *
        (1-THREE.MathUtils.smoothstep(phase,8.18,9.07));
      (ring.material as THREE.MeshBasicMaterial).opacity = 0.44*late + 0.10*(flying?1:0);
      ring.scale.setScalar(0.76 + 0.38*late);
      ring.rotation.z += dt*(flying ? 2.6 : 0.65);
      // Subtle pulse at the exact catch: visibly sells the impact into her palm.
      const catchPulse = Math.exp(-Math.pow((phase-5.58)/0.16,2));
      (ring.material as THREE.MeshBasicMaterial).opacity = Math.min(0.82,
        (ring.material as THREE.MeshBasicMaterial).opacity + 0.32*catchPulse);
    }
    if (this.gravityShowTrails) {
      const trails = this.gravityShowTrails;
      const spinWindow = (phase>=0.69 && phase<3.13) ||
        (phase>=5.57 && phase<7.32);
      trails.visible = spinWindow || flying;
      const center = flying ? flyer.position : gripP;
      trails.position.copy(center);
      trails.position.y += flying ? 0.20 : 0.38;
      trails.rotation.set(0.30 + Math.sin(phase*8)*0.17,
        Math.sin(phase*4.4)*0.35, phase*3.8);
      for (let i=0; i<trails.children.length; i++) {
        const arc = trails.children[i] as THREE.Mesh;
        (arc.material as THREE.MeshBasicMaterial).opacity =
          trails.visible ? (0.17 - i*0.034) * (flying ? 0.75 : 1) : 0;
        arc.rotation.z = i*1.77 + Math.sin(phase*6+i)*0.14;
      }
    }
  }

''')

    # Give live attacks / victory poses the relevant scythe rotation, not the fixed idle pose.
    rel = "src/game/fighter.ts"
    replace(rel, 'this.model.glaivePose = this.kit === "glaive" ? (this.state === S.WIN ? "show_baton" : this.poseName) : "idle";',
      'this.model.glaivePose = this.kit === "scythe" ? this.poseName : this.kit === "glaive" ? (this.state === S.WIN ? "show_baton" : this.poseName) : "idle";', count=2)

    # Single animation progress value drives whole-turn weapon motion in active
    # attacks without adding any new hitbox, collision, or net snapshot fields.
    rel = "src/game/fighter.ts"
    replace(rel, "    this.computePose();\n    this.model.bloodFestivalT =", r'''    this.computePose();
    this.model.scytheBeat = this.kit === "scythe" && this.state === S.ATTACK && this.atk
      ? THREE.MathUtils.clamp((this.stateT-this.atk.wind) /
          Math.max(0.01,this.atk.active + this.atk.recover*0.65),0,1) : 0;
    this.model.bloodFestivalT =''')

    # Display highlight after selecting Nythera, distinct from other 6.2 second loops.
    rel = "src/game/preview.ts"
    replace(rel, '    this.poses = Kits.poses(look.kit);', r'''    // NYTHERA_SHOWCASE_SPIN_TOSS_V3: widen framing so the whole overhead scythe stays visible.
    this.camera.position.set(0, look.kit === "scythe" ? 1.42 : 1.25,
      look.kit === "scythe" ? 5.80 : 4.6);
    this.camera.lookAt(0, look.kit === "scythe" ? 1.12 : 0.95, 0);
    this.poses = Kits.poses(look.kit);''')
    replace(rel, '''      const phase = this.mode === "victory" ? this.poseT : this.poseT % 6.2;
      const who = this.lookName.toLowerCase();''', '''      const who = this.lookName.toLowerCase();
      const phase = this.mode === "victory" ? this.poseT :
        this.poseT % (who === "nythera" ? 10.2 : 6.2);''')
    replace(rel, 'this.model.glaivePose = who === "zarek" ? "show_baton" : "idle";',
      'this.model.glaivePose = who === "nythera" ? "nythera_show" : who === "zarek" ? "show_baton" : "idle";')
    replace(rel, '      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt, 11);', r'''      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt,
        who === "nythera" ? 20 : 11);
      if (who === "nythera") {
        // Two distinct pirouettes support the shaft spins, but the throw/catch is weapon-only.
        const ease = (a:number,b:number) => THREE.MathUtils.smoothstep(phase,a,b);
        this.model.rotation.y = 2*Math.PI*(ease(1.21,2.25)+ease(6.14,6.95));
        if (this.mode === "select") this.model.animateNytheraShowcase(phase,dt);
        else {
          // A mode change during an airborne throw must restore the held weapon.
          this.model.rotation.y = 0;
          this.model.animateNytheraShowcase(8.5,dt);
        }
      } else this.model.rotation.y = 0;''')

    # Only Nythera gets long, fast 3D selection choreography instead of the generic four poses.
    rel = "src/game/presentation.ts"
    append_block(rel, '/** Entirely cosmetic; all poses use the same normalized VRM/procedural joints as combat. */', r'''
// NYTHERA_SHOWCASE_SPIN_TOSS_V3: scripted full-body rhythm aligned to the scythe's
// independent throw/catch window in FighterModel.animateNytheraShowcase().
const NYTHERA_SHOWCASE: Array<[number,Beat]> = [
  [0.00, {torso:[.04,-.23,.03],head:[-.06,.15,0],arm_r:[-1.12,.23,-.23],arm_l:[-1.19,-.15,.33],leg_l:[-.25,0,.13],leg_r:[.18,0,-.12],hips_y:-.055,knee:[.18,.16]}],
  [.53, {torso:[.23,-.57,.09],head:[.02,.37,-.04],arm_r:[-.72,-.63,-.37],arm_l:[-1.12,-.33,.48],leg_l:[-.44,0,.16],leg_r:[.38,0,-.16],hips_y:-.14,knee:[.38,.26]}],
  [1.07,{torso:[-.11,.47,-.09],head:[-.10,-.29,.04],arm_r:[-2.25,.68,-.17],arm_l:[-1.78,.35,.32],leg_l:[-.35,0,.10],leg_r:[.48,0,-.18],hips_y:-.03,knee:[.2,.14]}],
  [1.50,{torso:[.16,-.63,.11],head:[-.03,.25,-.03],arm_r:[-.84,-.75,-.43],arm_l:[-.94,-.4,.42],leg_l:[-.40,.03,.18],leg_r:[.34,-.04,-.12],hips_y:-.10,knee:[.31,.29]}],
  [1.95,{torso:[-.17,.61,-.10],head:[-.15,-.33,.06],arm_r:[-2.65,.22,-.15],arm_l:[-2.24,.27,.25],leg_l:[-.16,.02,.18],leg_r:[.38,0,-.12],hips_y:-.035,knee:[.20,.14]}],
  [2.42,{torso:[.25,-.87,.09],head:[.03,.46,-.03],arm_r:[-.92,-.8,-.49],arm_l:[-.91,-.58,.40],leg_l:[-.53,.02,.16],leg_r:[.56,-.02,-.14],hips_y:-.16,knee:[.42,.36]}],
  [3.04,{torso:[-.22,.48,-.02],head:[-.16,-.1,0],arm_r:[-2.72,.24,-.18],arm_l:[-1.82,.18,.25],leg_l:[-.31,0,.13],leg_r:[.43,0,-.14],hips_y:-.04,knee:[.14,.18]}],
  [3.35,{torso:[-.10,.25,.01],head:[-.26,-.07,0],arm_r:[-2.47,.16,-.24],hand_r:[-.28,0,-.04],arm_l:[-1.70,-.30,.54],hand_l:[.14,.1,.09],leg_l:[-.31,0,.13],leg_r:[.40,0,-.11],hips_y:-.02,knee:[.12,.16]}],
  [4.08,{torso:[-.10,-.37,-.06],head:[-.32,.21,.06],arm_r:[-1.26,.47,-.48],hand_r:[-.25,0,.08],arm_l:[-2.26,-.06,.49],hand_l:[.28,0,.14],leg_l:[-.27,0,.12],leg_r:[.23,0,-.11],hips_y:0.035,knee:[.10,.08]}],
  [4.75,{torso:[.08,.50,.06],head:[-.29,-.28,0],arm_r:[-2.05,-.25,-.30],hand_r:[.28,0,-.02],arm_l:[-1.95,.33,.31],leg_l:[-.32,0,.14],leg_r:[.45,0,-.12],hips_y:.02,knee:[.12,.09]}],
  [5.52,{torso:[.20,-.30,.03],head:[-.16,.17,0],arm_r:[-1.69,.39,-.26],hand_r:[.24,0,.04],arm_l:[-1.48,-.35,.40],leg_l:[-.32,0,.14],leg_r:[.40,0,-.13],hips_y:-.085,knee:[.23,.23]}],
  [5.94,{torso:[.24,-.62,.09],head:[.04,.31,0],arm_r:[-.95,-.73,-.33],arm_l:[-1.22,-.40,.36],leg_l:[-.46,0,.18],leg_r:[.41,0,-.15],hips_y:-.12,knee:[.34,.28]}],
  [6.34,{torso:[-.17,.56,-.11],head:[-.14,-.17,0],arm_r:[-2.45,.50,-.16],arm_l:[-1.73,.30,.28],leg_l:[-.34,0,.12],leg_r:[.48,0,-.18],hips_y:-.025,knee:[.15,.12]}],
  [6.77,{torso:[.19,-.73,.08],head:[.02,.36,0],arm_r:[-1.08,-.58,-.46],arm_l:[-1.15,-.34,.47],leg_l:[-.46,0,.18],leg_r:[.46,0,-.16],hips_y:-.16,knee:[.41,.37]}],
  [7.30,{torso:[.37,.19,.10],head:[-.25,-.05,0],arm_r:[-.63,.44,-.41],hand_r:[.22,0,.24],arm_l:[-1.05,.16,.41],leg_l:[-.59,0,.17],leg_r:[.51,0,-.13],hips_y:-.23,knee:[.48,.33]}],
  [7.86,{torso:[.02,-.12,.03],head:[-.17,.19,-.02],arm_r:[-1.69,.18,-.30],arm_l:[-1.22,-.19,.28],leg_l:[-.27,0,.14],leg_r:[.22,0,-.12],hips_y:-.062,knee:[.21,.18]}],
  [8.64,{torso:[.02,-.12,.03],head:[-.17,.19,-.02],arm_r:[-1.69,.18,-.30],arm_l:[-1.22,-.19,.28],leg_l:[-.27,0,.14],leg_r:[.22,0,-.12],hips_y:-.062,knee:[.21,.18]}],
  [9.67,{torso:[.04,-.23,.03],head:[-.06,.15,0],arm_r:[-1.12,.23,-.23],arm_l:[-1.19,-.15,.33],leg_l:[-.25,0,.13],leg_r:[.18,0,-.12],hips_y:-.055,knee:[.18,.16]}],
  [10.20,{torso:[.04,-.23,.03],head:[-.06,.15,0],arm_r:[-1.12,.23,-.23],arm_l:[-1.19,-.15,.33],leg_l:[-.25,0,.13],leg_r:[.18,0,-.12],hips_y:-.055,knee:[.18,.16]}],
];
function nytheraPresentation(seconds:number,base:Pose,mode:"select"|"victory"):Pose {
  const t=mode==="victory"? Math.min(Math.max(seconds,0),8.0):((seconds%10.2)+10.2)%10.2;
  let i=0;
  while (i<NYTHERA_SHOWCASE.length-2 && t>NYTHERA_SHOWCASE[i+1][0]) i++;
  const p=NYTHERA_SHOWCASE[i],n=NYTHERA_SHOWCASE[i+1];
  const u=Math.max(0,Math.min(1,(t-p[0])/(n[0]-p[0])));
  const pose=between(filled(base,p[1]),filled(base,n[1]),u);
  pose.head[1]+=Math.sin(seconds*1.5)*0.012;
  pose.torso[0]+=Math.sin(seconds*2.5)*0.007;
  return pose;
}

''')
    replace(rel, '  const entry = C[name.toLowerCase()];', r'''  if (name.toLowerCase() === "nythera") return nytheraPresentation(seconds,base,mode);
  const entry = C[name.toLowerCase()];''')

    # Controls line explaining the extra F toggle in the character-selection info panel.
    rel = "src/ui/Select.tsx"
    replace(rel, '  sickle: "Tap: 4-hit dual-sickle combo',
      '  scythe: "Tap: 4 sweeping scythe cuts - Hold: overhead cleave - F: Moonfloat / Dreadfall toggle - Z: Crescent Snare - X: Zero-G Ascension / Mass Cleaver - C: Event Horizon / Collapse - V: Black Star Requiem",\n  sickle: "Tap: 4-hit dual-sickle combo')

def write_sql_and_icons(base: Path, backup: Path) -> None:
    # New migration, no database side effects. Current roster plus Nythera and earlier legacy IDs.
    dst = base / "supabase/migrations/20261108090000_add_nythera_gravity_reaper.sql"
    if dst.exists():
        raise RuntimeError(f"Migration already exists: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    sql = '''-- NYTHERA_GRAVITY_REAPER_INSTALL_V1 -- optional; apply with `npx supabase db push`.
-- Merge any custom character IDs into these allowlists before applying.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash',
    'veyr','zarek','kaizen','nesa','roxy','zenith','nythera',
    'volta','sylva','leon','sakura','yuki','bruno'
  ])
$$;
CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
  SELECT ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash',
    'veyr','zarek','kaizen','nesa','roxy','zenith','nythera'
  ]::text[]
$$;
'''
    dst.write_text(sql, encoding="utf-8")
    # Optional Pillow art; without Pillow use established game icons as temporary placeholders.
    icons = {"chars/nythera.webp":"chars/aster.webp",
             "skills/scythe-z.webp":"skills/sickle-z.webp",
             "skills/scythe-x.webp":"skills/glaive-x.webp",
             "skills/scythe-c.webp":"skills/glaive-c.webp",
             "skills/scythe-v.webp":"skills/glaive-v.webp"}
    try:
        from PIL import Image, ImageDraw
        import math
    except ImportError:
        for dest, src in icons.items():
            original = base / "public/icons" / src
            target = base / "public/icons" / dest
            if original.exists() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
        print("  Icons: copied temporary fallback WebP icons (install Pillow for custom placeholders).")
        return
    for i, dest in enumerate(icons):
        target = base / "public/icons" / dest
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        sz = 256
        im = Image.new("RGBA", (sz,sz), (7, 7, 23, 255))
        d = ImageDraw.Draw(im)
        d.ellipse((11,11,245,245), fill=(19,13,40,255), outline=(201,157,247,255), width=8)
        # Orbit halos + tiny space motes; icon 0 is a stylized scythe portrait emblem.
        for r in (62,91):
            d.arc((128-r,128-r,128+r,128+r), 15, 310, fill=(163,96+i*10,245,235), width=5)
        d.line((132,70,132,199), fill=(229,217,247,255), width=8)
        d.arc((80,50,225,186), 196, 315, fill=(231,222,248,255), width=16)
        d.ellipse((122,58,145,80), fill=(171,84,243,255))
        for a in range(7):
            x = 128 + 100 * math.cos(a * 2*math.pi/7 + i)
            y = 128 + 100 * math.sin(a * 2*math.pi/7 + i)
            d.ellipse((x-2,y-2,x+2,y+2),fill=(220,190,250,255))
        im.save(target, "WEBP", quality=91)
    print("  Icons: generated temporary violet scythe emblems (replace with final character art later).")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Nythera into Fight Royale (source edition)")
    parser.add_argument("web_folder", nargs="?", default=".", help="Path to Fight Royale web folder")
    parser.add_argument("--dry-run", action="store_true", help="Check all patch anchors without writing files")
    args = parser.parse_args()
    base = Path(args.web_folder).expanduser().resolve()
    print(f"NYTHERA — GRAVITY REAPER | target: {base}")
    try:
        prepare(base)
        build_patches()
        game_patches()
        choreography_patches()
        if args.dry_run:
            print("OK — every source anchor matched, no files were changed.")
            for key in changes: print("   ", key)
            return 0
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = base / ".nythera-backups" / stamp
        # Check migration/assets before touching source; migration is not applied automatically.
        migration = base / "supabase/migrations/20261108090000_add_nythera_gravity_reaper.sql"
        if migration.exists():
            raise RuntimeError(f"Migration exists: {migration}; refusing duplicate installation.")
        for rel in changes:
            source = base / rel
            destination = backup / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        print(f"  Backups saved: {backup}")
        for rel, content in changes.items():
            (base / rel).write_text(content, encoding="utf-8")
            print("  Updated:", rel)
        write_sql_and_icons(base, backup)
        print("\nINSTALLED. Aster's VRM is referenced directly (no duplicate model file).")
        print("  Fight controls: F toggle Moonfloat/Dreadfall; Z hook; X lift/crush; C well/collapse; V eclipse finisher (if unlocked).")
        print("  Test: npx tsc --noEmit -p .  &&  npm run build")
        print("  SQL: new migration created; apply manually if using signed-in shop.")
        return 0
    except Exception as ex:
        print(f"\nERROR — {ex}", file=sys.stderr)
        print("No changes were written if this was an anchor or preflight failure.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
