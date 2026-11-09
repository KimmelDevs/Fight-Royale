#!/usr/bin/env python3
"""Fight Royale — RENJI_TONFA_RIG_V34.

Fixes Renji's static, diagonally raised forearms and incorrectly angled tonfas.
Targets an already-installed Renji Eclipse V3.2 + Blunt Impact V3.3.
Changes only src/game/vrm.ts, model.ts, fighter.ts. Does not alter damage,
Read, parry rules, sounds, other characters, or the user VRM file.

  python fix_renji_tonfa_pose_grip_v34.py --dry-run
  python fix_renji_tonfa_pose_grip_v34.py
  npx tsc --noEmit -p .

Fail-closed anchors, source preflight, UTF-8/CRLF preservation, .txt backups,
atomic staged writes and rollback; refuses repeat installation.
"""
from __future__ import annotations
import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

MARK = "RENJI_TONFA_RIG_V34"
FILES = ("src/game/vrm.ts", "src/game/model.ts", "src/game/fighter.ts")


def one(src: str, before: str, after: str, file: str) -> str:
    count = src.count(before)
    if count != 1:
        raise RuntimeError(f"{file}: expected exactly one anchor, found {count}: {before[:115]!r}")
    return src.replace(before, after, 1)


def generate(src: dict[str, str]) -> dict[str, str]:
    d = dict(src)
    m = "src/game/model.ts"
    v = "src/game/vrm.ts"
    f = "src/game/fighter.ts"

    # Teach the VRM rig that Renji is a TONFA fighter, rather than using its
    # generic boxer wrist-angle -> fixed elbow formula.
    d[v] = one(d[v], "  boxer = false;",
        "  boxer = false;\n  // RENJI_TONFA_RIG_V34 — independent elbow extension/chamber for paired tonfas.\n  tonfa = false;", v)

    elbow_old = '''      const wristX = Math.abs(new THREE.Euler().setFromQuaternion(hk.joint.quaternion, "YXZ").x);
      const flex = this.boxer
        ? THREE.MathUtils.clamp(D(12) + wristX * 1.75, D(12), D(125))
        : this.shield && side === "left"
          ? D(55)
          : Math.min(D(16) + elev * 0.3 + Math.sin(t * TAU / 3.8 + 1) * D(2) * idle, D(75));'''
    elbow_new = '''      const wristX = Math.abs(new THREE.Euler().setFromQuaternion(hk.joint.quaternion, "YXZ").x);
      // RENJI_TONFA_RIG_V34 — prior generic boxer flex was nearly constant
      // because EVERY V3.3 beat uses almost the same wrist angle.  Follow the
      // actual attacking upper arm instead: one elbow straightens for the hit,
      // the other folds into a rib-level chamber.  Knees/parries keep a guard.
      const renjiPose = m.pose ?? "";
      const renjiHitPose = /^rn(?:[1-5]|z[1-7]|c[12]|v[1-8])_s$/.test(renjiPose) ||
        renjiPose === "rnh_s" || renjiPose === "rn_insight_s" ||
        /^rn_counter_/.test(renjiPose);
      const renjiKneePose = /^(?:rn4_s|rnz7_s|rnv4_s|rn_counter_low)$/.test(renjiPose);
      const renjiElbowPose = /^(?:rn3_s|rnz4_s|rnc2_s|rnv3_s|rn_counter_side_3)$/.test(renjiPose);
      const armReach = renjiHitPose && !renjiKneePose && lk.joint.rotation.x < -1.35;
      const flex = this.tonfa
        ? (armReach ? D(renjiElbowPose ? 68 : 18) :
           renjiHitPose && !renjiKneePose ? D(100) :
           renjiPose.endsWith("_w") ? D(108) : D(92))
        : this.boxer
          ? THREE.MathUtils.clamp(D(12) + wristX * 1.75, D(12), D(125))
          : this.shield && side === "left"
            ? D(55)
            : Math.min(D(16) + elev * 0.3 + Math.sin(t * TAU / 3.8 + 1) * D(2) * idle, D(75));'''
    d[v] = one(d[v], elbow_old, elbow_new, v)

    d[m] = one(d[m],
      "  private updateRenjiTonfas(dt: number, pose: string) {",
      '''  // RENJI_TONFA_RIG_V34 — reused scratch transforms, no frame-by-frame allocations.
  private readonly renjiWristWorld = new THREE.Vector3();
  private readonly renjiElbowWorld = new THREE.Vector3();
  private readonly renjiTonfaDir = new THREE.Vector3();
  private readonly renjiTonfaForward = new THREE.Vector3();
  private readonly renjiLocalAxis = new THREE.Vector3(0, 1, 0);
  private readonly renjiParentWorldQ = new THREE.Quaternion();
  private readonly renjiModelWorldQ = new THREE.Quaternion();
  private readonly renjiTonfaTargetQ = new THREE.Quaternion();

  private updateRenjiTonfas(dt: number, pose: string) {''', m)

    rotation_old = '''      // Wrist snap without rotating the tonfa into a sword grip. Crossed guard
      // and chain flick keep the rod visually in front of the forearm.
      const zag=z && i===0 ? -.20 : c && i===1 ? .21 : 0;
      const twist=counter ? s*.31*flash : 0;
      weapon.rotation.z=THREE.MathUtils.damp(weapon.rotation.z,zag+twist,26,dt);
      weapon.rotation.x=THREE.MathUtils.damp(weapon.rotation.x,guard?-.14:0,24,dt);
      weapon.rotation.y=THREE.MathUtils.damp(weapon.rotation.y,guard?s*.12:0,22,dt);'''
    rotation_new = '''      // RENJI_TONFA_RIG_V34 — align the visible shaft to the REAL elbow->wrist
      // axis on the Aster VRM.  A fixed local rotation is wrong because left and
      // right hands have different calibrated axes.  The +Y shaft points back
      // from the fist to the elbow in idle/guard, then flips toward the opponent
      // only for the tonfa that is actually landing a strike.
      if (this.vrmRig && weapon.parent) {
        const human = this.vrmRig.vrm.humanoid;
        const hand = human.getNormalizedBoneNode(i === 0 ? "rightHand" : "leftHand");
        const elbow = human.getNormalizedBoneNode(i === 0 ? "rightLowerArm" : "leftLowerArm");
        if (hand && elbow) {
          hand.getWorldPosition(this.renjiWristWorld);
          elbow.getWorldPosition(this.renjiElbowWorld);
          this.renjiTonfaDir.copy(this.renjiElbowWorld).sub(this.renjiWristWorld);
          if (this.renjiTonfaDir.lengthSq() > 1e-8) {
            this.renjiTonfaDir.normalize();
            const strikeR = /^(?:rn1_s|rn3_s|rn5_s|rnh_s|rnz[135]_s|rnc2_s|rnv[13578]_s|rn_insight_s|rn_counter_(?:side|over|projectile)(?:_3)?)$/.test(pose);
            const strikeL = /^(?:rn2_s|rn5_s|rnz[246]_s|rnc1_s|rnv[268]_s|rn_insight_s|rn_counter_(?:thrust|side_2|over_2|projectile_2))$/.test(pose);
            const striking = i === 0 ? strikeR : strikeL;
            if (striking) {
              this.getWorldQuaternion(this.renjiModelWorldQ);
              this.renjiTonfaForward.set(0, 0, 1).applyQuaternion(this.renjiModelWorldQ);
              this.renjiTonfaDir.lerp(this.renjiTonfaForward, 0.86).normalize();
            }
            this.renjiTonfaTargetQ.setFromUnitVectors(this.renjiLocalAxis, this.renjiTonfaDir);
            weapon.parent.getWorldQuaternion(this.renjiParentWorldQ).invert();
            this.renjiParentWorldQ.multiply(this.renjiTonfaTargetQ);
            weapon.quaternion.slerp(this.renjiParentWorldQ,
              1-Math.exp(-Math.max(0,Math.min(dt,.10))*(striking?45:26)));
          }
        }
      } else {
        // Preserve the procedural fallback when no VRM is loaded.
        const zag=z && i===0 ? -.20 : c && i===1 ? .21 : 0;
        const twist=counter ? s*.31*flash : 0;
        weapon.rotation.z=THREE.MathUtils.damp(weapon.rotation.z,zag+twist,26,dt);
        weapon.rotation.x=THREE.MathUtils.damp(weapon.rotation.x,guard?-.14:0,24,dt);
        weapon.rotation.y=THREE.MathUtils.damp(weapon.rotation.y,guard?s*.12:0,22,dt);
      }'''
    d[m] = one(d[m], rotation_old, rotation_new, m)
    d[m] = one(d[m],
        '      this.vrmRig.boxer = true;\n      this.vrmRig.bladed = 0.35;',
        '''      this.vrmRig.boxer = true;
      this.vrmRig.tonfa = true; // RENJI_TONFA_RIG_V34
      this.vrmRig.followArm = 0.65; // wrists follow forearm rather than fixed / pose
      this.vrmRig.bladed = 0.15;''', m)

    # Higher blend speed is only applied to Renji, keeping short Z beats readable.
    d[f] = one(d[f],
      '        if (this.poseOverride) { p = this.poseOverride; sp = 40; break; }',
      '''        if (this.poseOverride) {
          p = this.poseOverride;
          sp = this.kit === "tonfa" ? 88 : 40; // RENJI_TONFA_RIG_V34
          break;
        }
        if (this.kit === "tonfa" && a) {
          if (this.atkPhase === 0) { p = a.pose_w; sp = 38; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = 88; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.55) {
            p = a.pose_s; sp = 28;
          } else { p = "idle"; sp = 20; }
          break;
        }''', f)

    return d


def run(root: Path, dry: bool):
    if not (root / "src/game/model.ts").is_file():
        raise RuntimeError("Run inside fight-royale/web, or supply your web directory")
    old, raw, newline, bom = {}, {}, {}, {}
    for rel in FILES:
        buf = (root / rel).read_bytes()
        raw[rel] = buf
        bom[rel] = b"\xef\xbb\xbf" if buf.startswith(b"\xef\xbb\xbf") else b""
        newline[rel] = "\r\n" if b"\r\n" in buf else "\n"
        old[rel] = buf.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    if any(MARK in value for value in old.values()):
        raise RuntimeError("V3.4 already installed; refusing to patch twice")
    if "RENJI_BLUNT_IMPACT_V33" not in old["src/game/model.ts"] or \
       "RENJI_BLUNT_IMPACT_V33" not in (root / "src/game/kits.ts").read_text(encoding="utf-8-sig"):
        raise RuntimeError("Requires Renji Blunt Impact V3.3 installed first")
    if "renjiParryT" not in old["src/game/model.ts"] or \
       "this.poseOverride" not in old["src/game/fighter.ts"]:
        raise RuntimeError("Renji pose system missing; source version unsupported")
    if "tonfa = false" in old["src/game/vrm.ts"]:
        raise RuntimeError("An existing tonfa-specific rig patch was detected; review manually")
    updated = generate(old)
    for rel in FILES:
        if MARK not in updated[rel] or updated[rel] == old[rel]:
            raise RuntimeError(f"{rel}: patch did not apply")
    print(f"{MARK}: preflight passed for {len(FILES)} files")
    print("Fix: per-beat forearm extension, real wrist/elbow tonfa alignment, faster Renji-only blend")
    if dry:
        print("DRY RUN — no files modified")
        return
    backup = root / "scripts" / "backups" / ("renji_rig_v34_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    backup.mkdir(parents=True, exist_ok=False)
    tempfiles, modified = [], []
    try:
        (backup / "manifest.json").write_text(json.dumps({"version": MARK, "files": FILES}, indent=2), encoding="utf-8")
        for rel in FILES:
            (backup / (rel.replace("/", "__") + ".txt")).write_bytes(raw[rel])
        for rel in FILES:
            path = root / rel
            blob = bom[rel] + updated[rel].replace("\n", newline[rel]).encode("utf-8")
            fd, temp = tempfile.mkstemp(prefix=".renji_v34_", suffix=".tmp", dir=path.parent)
            with os.fdopen(fd, "wb") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            tempfiles.append((path, Path(temp)))
        for path, temp in tempfiles:
            os.replace(temp, path)
            modified.append(path)
    except BaseException:
        for path in reversed(modified):
            rel = path.relative_to(root).as_posix()
            path.write_bytes(raw[rel])
        raise
    finally:
        for _, temp in tempfiles:
            temp.unlink(missing_ok=True)
    print("Installed.", "Backups:", backup)
    print("Run: npx tsc --noEmit -p . && npm run dev")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("web_dir", nargs="?", default=".")
    args = parser.parse_args()
    try:
        run(Path(args.web_dir).resolve(), args.dry_run)
    except Exception as exc:
        print("ERROR:", exc)
        raise SystemExit(1)
