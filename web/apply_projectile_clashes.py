#!/usr/bin/env python3
"""Fight Royale: host-authoritative projectile-versus-projectile clashes.

Place this installer anywhere and run inside the project folder:
    python apply_projectile_clashes.py
or explicitly supply the location of your web game:
    python apply_projectile_clashes.py "C:/path/to/your/web"

Changes only src/game/game.ts. Makes a timestamped backup first.
No additional Python packages are required.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARKER = "PROJECTILE_VS_PROJECTILE_CLASH_V1"

METHODS = r'''  /** PROJECTILE_VS_PROJECTILE_CLASH_V1: two enemy projectiles can physically
   * collide. Uses their swept flight paths so fast arrows/lightning don't pass
   * through one another between frames. Only the host decides hit results;
   * guests receive the existing effect and projEnd network events.
   */
  private resolveProjectileClashes(previous: Map<number, THREE.Vector3>) {
    if (this.cfg.role === "client") return;
    const shots = this.projectiles.filter(p => !p.done && !p.visualOnly && !!p.atk);
    for (let i = 0; i < shots.length; i++) {
      const a = shots[i];
      if (a.done) continue;
      const aStart = previous.get(a.id) ?? a.pos;
      for (let j = i + 1; j < shots.length; j++) {
        const b = shots[j];
        if (b.done || a.done || a.team === b.team) continue;
        const bStart = previous.get(b.id) ?? b.pos;
        // Relative motion of two *moving* projectiles over this same frame.
        const separation = aStart.clone().sub(bStart);
        const relativeStep = a.pos.clone().sub(aStart)
          .sub(b.pos.clone().sub(bStart));
        const relativeLengthSq = relativeStep.lengthSq();
        const t = relativeLengthSq > 0.0000001
          ? THREE.MathUtils.clamp(-separation.dot(relativeStep) / relativeLengthSq, 0, 1)
          : 0;
        const aRadius = Math.max(0.14, Math.min(0.48, a.size *
          (a.style === "wave" || a.style === "shock" ? 0.37 : 0.23)));
        const bRadius = Math.max(0.14, Math.min(0.48, b.size *
          (b.style === "wave" || b.style === "shock" ? 0.37 : 0.23)));
        const radius = aRadius + bRadius;
        if (separation.addScaledVector(relativeStep, t).lengthSq() > radius * radius) continue;
        // Find the real in-between contact position, not either final position.
        const aHit = aStart.clone().lerp(a.pos, t);
        const bHit = bStart.clone().lerp(b.pos, t);
        const contact = aHit.add(bHit).multiplyScalar(0.5);
        this.finishProjectileClash(a, b, contact);
      }
    }
  }

  private finishProjectileClash(a: Projectile, b: Projectile, contact: THREE.Vector3) {
    if (a.done || b.done || !a.atk || !b.atk || a.team === b.team) return;
    const bombA = a.atk.type === "lob" || a.style === "bomb";
    const bombB = b.atk.type === "lob" || b.style === "bomb";
    // Most opposing shots cancel out. Clearly dominant heavy/piercing shots
    // can push through weakened, but this is never a free damage boost.
    const strength = (p: Projectile) => Math.max(1, p.atk!.dmg) *
      Math.max(0.15, p.power) * (p.atk!.heavy ? 1.24 : 1) *
      (p.pierce ? 1.17 : 1);
    const sa = strength(a), sb = strength(b);
    let winner: Projectile | null = null;
    let loser: Projectile | null = null;
    if (!bombA && !bombB) {
      if (sa > sb * 1.75) { winner = a; loser = b; }
      else if (sb > sa * 1.75) { winner = b; loser = a; }
    }
    if (winner && loser) {
      loser.done = true;
      // The winner keeps its direction, pierce, and status effects, but loses
      // attack power every time it punches through another enemy projectile.
      winner.power *= Math.max(0.60, 1 - 0.65 * (strength(loser) / strength(winner)));
    } else {
      a.done = true;
      b.done = true;
    }
    const color = new THREE.Color(a.color).lerp(new THREE.Color(b.color), 0.5).getStyle();
    const big = bombA || bombB;
    this.fxp("impactBurst", contact, color, big ? 1.6 : winner ? 1.4 : 1.15, "projectile");
    this.fxp("clashBurst", contact, color, big ? 1.4 : 1.1);
    this.fxp("sparks", contact, a.color, 13, 6);
    this.fxp("sparks", contact, b.color, 13, 6);
    this.fxp("flash", contact, "#ffffff", big ? 0.50 : 0.32, 0.12, 0.88);
    this.fxp("num", contact.clone().add(new THREE.Vector3(0, 0.44, 0)),
      big ? "BOOM CLASH!" : winner ? "BREAKTHROUGH!" : "SHOT CLASH!",
      big ? "#ffe19c" : "#d9f5ff", 0.77);
    this.snd("clash", big ? 0.85 : 0.68);
    this.add_trauma(big ? 0.27 : 0.13);
    // Projectiles hitting each other are NOT melee parries or sword clashes:
    // they do not grant Garrick Resolve or Zarek's Clash Momentum.
    if (bombA) this.bombBlast(a.shooter, a.atk, a.power, contact, a.team);
    if (bombB) this.bombBlast(b.shooter, b.atk, b.power, contact, b.team);
  }

'''

OLD_UPDATE_HEAD = '''  private updateProjectiles(dt: number) {
    for (const p of this.projectiles) {
      if (p.done) continue;
      if (p.gravity) { p.vel.y -= p.gravity * dt; p.spin.rotation.x += dt * 9; }
      p.age += dt;
      if (p.steering && p.target && !p.target.isDown() && p.age > (p.style === "bloodcrescent" ? 0.38 : 0)) {
        const aim = p.target.chest().sub(p.pos);
        if (aim.lengthSq() > 0.01) {
          const speed = p.atk?.speed ?? 15;
          const turnRate = p.style === "bloodcrescent" ? 2.0 : 4.3;
          p.vel.lerp(aim.normalize().multiplyScalar(speed), Math.min(1, dt * turnRate)).normalize().multiplyScalar(speed);
        }
      }
      const beforeMelee = p.pos.clone();
      p.pos.addScaledVector(p.vel, dt);
      p.life -= dt;
      // Server/host authoritative: slash, punch or kick a hostile projectile in active frames.
'''

NEW_UPDATE_HEAD = '''  private updateProjectiles(dt: number) {
    // First move ALL projectiles, then resolve shot-on-shot collisions before
    // individual melee, trap, or character hits. This avoids array-order bias.
    const previous = new Map<number, THREE.Vector3>();
    for (const p of this.projectiles) {
      if (p.done) continue;
      previous.set(p.id, p.pos.clone());
      if (p.gravity) { p.vel.y -= p.gravity * dt; p.spin.rotation.x += dt * 9; }
      p.age += dt;
      if (p.steering && p.target && !p.target.isDown() && p.age > (p.style === "bloodcrescent" ? 0.38 : 0)) {
        const aim = p.target.chest().sub(p.pos);
        if (aim.lengthSq() > 0.01) {
          const speed = p.atk?.speed ?? 15;
          const turnRate = p.style === "bloodcrescent" ? 2.0 : 4.3;
          p.vel.lerp(aim.normalize().multiplyScalar(speed), Math.min(1, dt * turnRate)).normalize().multiplyScalar(speed);
        }
      }
      p.pos.addScaledVector(p.vel, dt);
      p.life -= dt;
    }
    this.resolveProjectileClashes(previous);
    for (const p of this.projectiles) {
      if (p.done) continue;
      const beforeMelee = previous.get(p.id) ?? p.pos;
      // Server/host authoritative: slash, punch or kick a hostile projectile in active frames.
'''


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one location, found {count}. Your source might be a different version; no changes made.")
    return source.replace(old, new, 1)


def install(project: Path) -> int:
    base = project.expanduser().resolve()
    candidates = (
        base / "src" / "game" / "game.ts",
        base / "web" / "src" / "game" / "game.ts",
        base / "game" / "game.ts",
        base / "game.ts",
    )
    path = next((p for p in candidates if p.is_file()), None)
    if not path:
        print(f"Cannot locate src/game/game.ts beneath {base}", file=sys.stderr)
        return 1
    original = path.read_text(encoding="utf-8")
    if MARKER in original:
        print(f"Projectile-versus-projectile clashes already installed: {path}")
        return 0
    try:
        updated = replace_once(original, "  private updateProjectiles(dt: number) {\n", METHODS + "  private updateProjectiles(dt: number) {\n", "insert clash methods")
        updated = replace_once(updated, OLD_UPDATE_HEAD, NEW_UPDATE_HEAD, "split projectile movement / collision passes")
    except RuntimeError as err:
        print(f"Patch stopped safely: {err}", file=sys.stderr)
        return 2
    backup = path.with_name(path.name + ".before_projectile_clashes_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".bak")
    shutil.copy2(path, backup)
    tmp = path.with_name(path.name + ".projectile_clashes.tmp")
    try:
        tmp.write_text(updated, encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f"Installed projectile-versus-projectile clashes into {path}")
    print(f"Backup: {backup}")
    print("Behaviors: enemy shots collide; most cancel; overwhelmingly stronger shots break through weakened; Bob bombs detonate.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add projectile-versus-projectile clashes to Fight Royale")
    parser.add_argument("project", nargs="?", type=Path, default=Path("."), help="Game project folder (or the web folder itself)")
    sys.exit(install(parser.parse_args().project))
