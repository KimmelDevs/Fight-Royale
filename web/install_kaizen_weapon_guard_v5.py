#!/usr/bin/env python3
"""Kaizen V5: detailed forked chain dagger, thin-link rig and spinning guard.
Designed for Kaizen/Zarek V4 Exact-Source Fix. Safely preflights before writing.
"""
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "src/game/model.ts"
GAME = ROOT / "src/game/game.ts"

BUILD = r'''
  private buildChainblade() {
    // KAIZEN_WEAPON_V5: compact forked spear-knife, dark red grip, individually sized links.
    // Off-hand holds the free end; the blade flies independently in the other hand.
    const anchorGrip = pivot(this.hand_l, [0, -0.055, 0], [PI / 2, 0, 0]);
    mesh(anchorGrip, cyl(0.025, 0.028, 0.19, 12), this.tn("#36202b"));
    mesh(anchorGrip, cyl(0.037, 0.033, 0.018, 12), this.tn("#c69c52"), [0, 0.09, 0]);
    mesh(anchorGrip, sphere(0.027, 12), this.tn("#a8aab2"), [0, -0.103, 0]);
    this.chainAnchor = pivot(anchorGrip, [0, 0.113, 0]);

    // Thin, correctly proportioned steel chain. No scaling links along their length.
    const darkSteel = this.tn("#30343d");
    const chainHighlight = this.tn("#7b808b");
    for (let i = 0; i < 72; i++) {
      const link = pivot(this);
      mesh(link, torus(0.016, 0.034), darkSteel, [0, 0, 0],
        [i % 2 ? PI / 2 : 0, 0, 0], [0.80, 1.16, 0.85]);
      mesh(link, torus(0.017, 0.030), chainHighlight, [0, 0, 0.003],
        [i % 2 ? PI / 2 : 0, 0, 0], [0.75, 1.13, 0.8]);
      link.visible = false;
      this.chainLinks.push(link);
    }

    // All weapon details belong to a single rigid blade group.
    this.chainBlade = pivot(this, [0, 1.11, 0.24]);
    const grip = this.tn("#681d2e");
    const bright = this.tn("#e1e4e8");
    const dark = this.tn("#6b7381");
    const brass = this.tn("#cba864");
    mesh(this.chainBlade, cyl(0.028, 0.030, 0.34, 14), grip, [0, -0.02, 0]);
    // Diagonal-looking handle wrappings and a chain-link connection at the pommel.
    for (let i = 0; i < 7; i++) {
      const y = -0.165 + i * 0.045;
      mesh(this.chainBlade, torus(0.027, 0.034), this.tn("#9b3d4c"),
        [0, y, 0], [PI / 2, 0, 0], [0.89, 0.32, 1.02]);
    }
    mesh(this.chainBlade, cyl(0.043, 0.039, 0.032, 14), brass, [0, 0.169, 0]);
    mesh(this.chainBlade, cyl(0.037, 0.037, 0.031, 14), brass, [0, -0.197, 0]);
    mesh(this.chainBlade, sphere(0.025, 12), dark, [0, -0.224, 0]);
    mesh(this.chainBlade, box(0.19, 0.025, 0.062), brass, [0, 0.196, 0]);
    mesh(this.chainBlade, sphere(0.024, 12), this.gem(), [0, 0.201, 0.036]);

    // An asymmetric, forked polished blade (no thick bevels or oversized side tines).
    const shape = new THREE.Shape();
    shape.moveTo(-0.073, 0.214);
    shape.lineTo(0.080, 0.214);
    shape.lineTo(0.111, 0.305);
    shape.lineTo(0.104, 0.482);
    shape.lineTo(0.071, 0.607); // short tine
    shape.lineTo(0.039, 0.564);
    shape.lineTo(0.054, 0.433);
    shape.lineTo(-0.024, 0.466); // inner gap
    shape.lineTo(-0.101, 0.718); // long fine tip
    shape.lineTo(-0.130, 0.682);
    shape.lineTo(-0.081, 0.390);
    shape.lineTo(-0.150, 0.295);
    shape.closePath();
    const daggerGeo = new THREE.ExtrudeGeometry(shape, {
      depth: 0.012, bevelEnabled: true, bevelThickness: 0.003,
      bevelSize: 0.002, bevelSegments: 2,
    });
    daggerGeo.translate(0, 0, -0.006);
    mesh(this.chainBlade, daggerGeo, bright);
    // Separate narrow central ridge makes the steel appear faceted, not like a paddle.
    const ridge = new THREE.Shape();
    ridge.moveTo(-0.052, 0.257);
    ridge.lineTo(0.033, 0.256);
    ridge.lineTo(0.028, 0.407);
    ridge.lineTo(-0.070, 0.625);
    ridge.lineTo(-0.049, 0.400);
    ridge.closePath();
    const ridgeGeo = new THREE.ExtrudeGeometry(ridge, { depth: 0.005, bevelEnabled: false });
    ridgeGeo.translate(0, 0, 0.010);
    mesh(this.chainBlade, ridgeGeo, dark);
    // Fine edge highlight along the long tine.
    const edgePath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.147, 0.300, 0.014),
      new THREE.Vector3(-0.079, 0.391, 0.014),
      new THREE.Vector3(-0.129, 0.681, 0.014),
      new THREE.Vector3(-0.101, 0.716, 0.014),
    ]);
    mesh(this.chainBlade, new THREE.TubeGeometry(edgePath, 22, 0.0035, 4, false), bright);
    for (const yy of [0.272, 0.317])
      mesh(this.chainBlade, sphere(0.009, 8), brass, [0.018, yy, 0.018]);
    this.bladeBase = pivot(this.chainBlade, [0, 0.21, 0]);
    this.bladeTip = pivot(this.chainBlade, [-0.10, 0.72, 0]);
    this.castPoint = this.bladeTip;
    this.shieldNode = anchorGrip;

    // Thin chains wrapped around an enemy during X/V binding, not giant hoops.
    for (let i = 0; i < 28; i++) {
      const node = pivot(this);
      mesh(node, torus(0.014, 0.030), darkSteel, [0, 0, 0],
        [i % 2 ? PI / 2 : 0, 0, 0], [0.83, 1.11, 0.88]);
      node.visible = false;
      this.chainWrap.push(node);
    }
    for (let i = 0; i < 2; i++) {
      const mat = new THREE.MeshBasicMaterial({ color: i ? 0xf4bec7 : 0xff5a69,
        transparent: true, opacity: i ? 0.08 : 0.16, depthWrite: false, side: THREE.DoubleSide });
      const ghost = new THREE.Mesh(daggerGeo, mat);
      ghost.visible = false;
      ghost.userData.fill = true;
      this.add(ghost);
      this.chainGhosts.push(ghost);
    }
  }

  /** V5: free-moving forked blade; thin chain follows a real curve without stretched links. */
'''

UPDATE = r'''
  private updateChainblade(dt: number) {
    const blade = this.chainBlade, anchor = this.chainAnchor;
    if (!blade || !anchor || !this.chainLinks.length) return;
    this.updateMatrixWorld(true);
    const start = this.worldToLocal(anchor.getWorldPosition(new THREE.Vector3()));
    const handR = this.worldToLocal(this.hand_r.getWorldPosition(new THREE.Vector3()));
    const pose = this.chainPose;
    if (pose !== this.chainPrevPose) { this.chainPoseClock = 0; this.chainPrevPose = pose; }
    else this.chainPoseClock += dt;
    const t = this.chainPoseClock;
    const blocking = pose === "block";
    const orbit = /^(?:cbx|cbz|cbc)/.test(pose);
    const strike = pose.endsWith("_s");
    const attack = /^(?:cb[1-5]_|cbh_|cbz_|cbv_|cbc_|cbx)/.test(pose);
    const bound = this.chainBindTargetWorld !== null;
    const bindCenter = bound ? this.worldToLocal(this.chainBindTargetWorld!.clone()) : null;
    this.chainOrbit += dt * (blocking ? 15 : orbit ? (strike ? 20 : 11) : attack ? 8 : 1.4);

    let goal = handR.clone().add(new THREE.Vector3(0, 0.08, 0.16));
    if (bindCenter) {
      goal = bindCenter.clone().add(new THREE.Vector3(0.05, 0.13, 0.02));
    } else if (blocking) {
      // Continuous rotating guard that stays tight to the torso.
      goal.set(Math.sin(this.chainOrbit) * 0.77,
        1.10 + Math.sin(this.chainOrbit * 2) * 0.09,
        0.18 + Math.cos(this.chainOrbit) * 0.69);
    } else if (orbit) {
      const r = strike ? 1.85 : 1.12;
      goal.set(Math.sin(this.chainOrbit) * r,
        1.14 + Math.sin(this.chainOrbit * 2) * 0.13,
        Math.cos(this.chainOrbit) * r * 0.83 + 0.22);
    } else if (pose.startsWith("cbh") || pose.startsWith("cbv")) {
      const power = strike ? Math.min(1, t * 4.8) : 0.2;
      const travel = Math.sin(Math.PI * power) * 2.55;
      goal.set(start.x + Math.sin(t * 9) * 0.16, 1.25, start.z + 0.45 + travel);
    } else if (/^cb[1-5]_[ws]$/.test(pose)) {
      const n = Number(pose[2]), sign = n % 2 ? 1 : -1;
      const angle = (n % 2 ? -1 : 1) + sign * (strike ? Math.min(1, t / 0.24) * PI * 1.16 : -0.2);
      const r = strike ? 1.46 : 0.76;
      goal.set(Math.sin(angle) * r, 1.14 + Math.cos(angle + n) * 0.25,
        Math.cos(angle) * r * 0.77 + 0.2);
    }
    blade.position.lerp(goal, 1 - Math.exp(-(bound ? 38 : blocking ? 36 : attack ? 26 : 17) * dt));
    const end = blade.position.clone();

    // During guard the blade goes around Kaizen, and the chain follows the preceding arc.
    // During attacks a slack quadratic produces natural whiplash.
    const curve = blocking ? new THREE.CatmullRomCurve3([
      start,
      new THREE.Vector3(Math.sin(this.chainOrbit - 1.05) * 0.63, 1.08,
        0.16 + Math.cos(this.chainOrbit - 1.05) * 0.60),
      new THREE.Vector3(Math.sin(this.chainOrbit - 0.48) * 0.76, 1.13,
        0.16 + Math.cos(this.chainOrbit - 0.48) * 0.66),
      end,
    ], false, "centripetal", 0.5) : new THREE.QuadraticBezierCurve3(
      start,
      start.clone().lerp(end, 0.5).add(new THREE.Vector3(
        Math.sin(this.chainOrbit) * (orbit ? 0.34 : 0.10),
        bound ? 0.02 : attack ? 0.06 : -0.23,
        Math.cos(this.chainOrbit) * (orbit ? 0.31 : 0.09))),
      end,
    );

    // Maintain original link shape and thickness at every reach; add/hide links instead
    // of stretching them (the cause of the giant chain in V4).
    const length = curve.getLength();
    const visibleCount = THREE.MathUtils.clamp(Math.ceil(length / 0.047), 8, this.chainLinks.length);
    const up = new THREE.Vector3(0, 1, 0);
    for (let i = 0; i < this.chainLinks.length; i++) {
      const link = this.chainLinks[i];
      link.visible = i < visibleCount;
      if (!link.visible) continue;
      const u = (i + 0.5) / visibleCount;
      link.position.copy(curve.getPoint(u));
      const tan = curve.getTangent(u).normalize();
      if (tan.lengthSq() > 0.0001) link.quaternion.setFromUnitVectors(up, tan);
      link.rotateY((i % 2) * PI / 2);
      link.scale.setScalar(1); // never widen a link with distance
    }
    // Smaller enemy wraps: two tight overlapping chain loops at chest height.
    for (let i = 0; i < this.chainWrap.length; i++) {
      const link = this.chainWrap[i];
      link.visible = !!bindCenter;
      if (!bindCenter) continue;
      const angle = (i % 14) * TAU / 14;
      const layer = i < 14 ? -0.13 : 0.13;
      link.position.copy(bindCenter).add(new THREE.Vector3(
        Math.sin(angle) * 0.32, layer + Math.sin(angle * 2) * 0.04,
        Math.cos(angle) * 0.32));
      link.rotation.set(0.1 * Math.cos(angle), angle + PI / 2, 0);
    }
    const tangent = blocking
      ? new THREE.Vector3(Math.cos(this.chainOrbit), 0, -Math.sin(this.chainOrbit)).normalize()
      : end.clone().sub(curve.getPoint(0.86)).normalize();
    if (tangent.lengthSq() > 0.01)
      blade.quaternion.slerp(new THREE.Quaternion().setFromUnitVectors(up, tangent),
        1 - Math.exp(-(blocking ? 30 : 18) * dt));
    let prev: THREE.Object3D = blade;
    for (let i = 0; i < this.chainGhosts.length; i++) {
      const ghost = this.chainGhosts[i];
      ghost.visible = !bound && (blocking || (attack && (strike || orbit)));
      ghost.position.lerp(prev.position, 1 - Math.exp(-(i ? 10 : 17) * dt));
      ghost.quaternion.slerp(prev.quaternion, 1 - Math.exp(-16 * dt));
      ghost.scale.setScalar(i ? 0.85 : 0.95);
      prev = ghost;
    }
  }
'''

GUARD = r'''
  /** KAIZEN_WEAPON_V5: close-range spinning guard, host-authoritative. */
  private updateKaizenSpinGuard() {
    for (const f of this.fighters) {
      if (f.kit !== "chainblade" || f.state !== S.BLOCK || f.guard <= 0 ||
          f.isDown() || !f.root.visible || f.chainBindT > 0 ||
          (f.chainBoundBy && f.chainBoundBy.chainBindT > 0)) continue;
      let cooldowns = this.kaizenGuardContacts.get(f);
      if (!cooldowns) {
        cooldowns = new WeakMap<Entity, number>();
        this.kaizenGuardContacts.set(f, cooldowns);
      }
      for (const enemy of this.enemiesOf(f)) {
        if (!enemy.root.visible || enemy.isDown()) continue;
        const delta = enemy.root.position.clone().sub(f.root.position);
        if (Math.abs(delta.y) > 1.05) continue;
        delta.y = 0;
        if (delta.length() > 0.92 + enemy.radius) continue;
        if (this.time < (cooldowns.get(enemy) ?? -Infinity)) continue;
        cooldowns.set(enemy, this.time + 0.45); // limited damage; no rapid hitlock
        const dir = delta.lengthSq() > 0.001 ? delta.normalize() :
          new THREE.Vector3(Math.sin(f.root.rotation.y), 0, Math.cos(f.root.rotation.y));
        const attack: Attack = {
          ...f.attacks.l1,
          id: "kaizen_guard_spin", style: "kaizen_guard_spin", type: "melee",
          dmg: 16, guard: 9, knock: 0.35, stun: 0.05, heavy: false,
          no_parry: true, effect: "", effect_t: 0, effect_p: 0,
        };
        // Damage is never automatic through a normal block. HP is deducted only
        // if the standard hit pipeline returns a hit; guard break still works.
        const outcome = this.applyHit(f, enemy, attack, 1, enemy.chest(), dir, false);
        if (outcome === "hit" || outcome === "crit" || outcome === "ko")
          this.fxp("slashes", enemy.chest(), "#e8667c");
      }
    }
  }

'''


def one(src: str, marker: str, filename: str) -> int:
    n = src.count(marker)
    if n != 1: raise RuntimeError(f"{filename}: expected one {marker!r}, found {n}. No changes made.")
    return src.index(marker)


def prepare() -> dict[Path, str]:
    if not MODEL.is_file() or not GAME.is_file():
        raise RuntimeError("Run from your main web/ folder (beside package.json). Missing src/game/model.ts or game.ts")
    model = MODEL.read_text(encoding="utf-8")
    game = GAME.read_text(encoding="utf-8")
    if "KAIZEN_WEAPON_V5" in model and "KAIZEN_WEAPON_V5" in game:
        print("Already installed: Kaizen Weapon V5.")
        return {}
    if "chainBindTargetWorld" not in model or "chainBindT" not in game:
        raise RuntimeError("Requires Kaizen/Zarek V4 Exact-Source Fix. No changes made.")

    if "KAIZEN_WEAPON_V5" not in model:
        a = one(model, "  private buildChainblade() {", "model.ts")
        b = one(model, "  private updateChainblade(dt: number) {", "model.ts")
        c = one(model, "  private buildSword() {", "model.ts")
        if not a < b < c: raise RuntimeError("Unexpected model method order. No changes made.")
        # Leave preceding comment in place; replace both source methods together.
        model = model[:a] + BUILD + "\n" + UPDATE + "\n\n" + model[c:]

    if "KAIZEN_WEAPON_V5" not in game:
        prop_anchor = "  private bloodFestivals: BloodFestival[] = [];"
        one(game, prop_anchor, "game.ts")
        game = game.replace(prop_anchor, prop_anchor +
            "\n  private kaizenGuardContacts = new WeakMap<Fighter, WeakMap<Entity, number>>();", 1)
        frame_anchor = "    for (const f of this.fighters) f.update(dt);"
        one(game, frame_anchor, "game.ts")
        game = game.replace(frame_anchor, frame_anchor +
            "\n    if (this.cfg.role !== \"client\") this.updateKaizenSpinGuard();", 1)
        method_anchor = "  private retarget() {"
        one(game, method_anchor, "game.ts")
        game = game.replace(method_anchor, GUARD + method_anchor, 1)
    return {MODEL: model, GAME: game}


def main():
    edits = prepare()  # All validation before writing anything.
    if not edits: return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for path, result in edits.items():
        original = path.read_text(encoding="utf-8")
        if original == result: continue
        backup = path.with_name(path.name + f".kaizen-v5-backup-{stamp}")
        backup.write_text(original, encoding="utf-8")
        path.write_text(result, encoding="utf-8")
        print("PATCH", path.relative_to(ROOT), "(backup", backup.name + ")")
    print("DONE: Kaizen's forked blade, thin chain, rotating guard, and close-range guard contact installed.")
    print("Next: npx tsc --noEmit  ;  npm run dev")

if __name__ == "__main__":
    main()
