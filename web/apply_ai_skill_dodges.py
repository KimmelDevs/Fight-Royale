#!/usr/bin/env python3
"""Fight Royale CPU skill dodges for Ocean Requiem, Thunderstorm, Meteor etc.
Run from the project folder, or pass your project path on the command line:
    python apply_ai_skill_dodges.py "C:/your/project/web"
This modifies only ai.ts and game.ts, with backups, and no new Python packages.
"""
from pathlib import Path
import argparse
import shutil
import sys

parser = argparse.ArgumentParser(description="Install skill-zone AI dodges in Fight Royale")
parser.add_argument("project", nargs="?", default=".", help="Path to your project or web folder")
args = parser.parse_args()
base = Path(args.project).expanduser().resolve()
options = [base / "src" / "game", base / "web" / "src" / "game", base / "game", base]
root = next((p for p in options if (p / "ai.ts").is_file() and (p / "game.ts").is_file()), None)
if root is None:
    sys.exit(f"Cannot find src/game/ai.ts and game.ts under {base}.\n"
             'Usage: python apply_ai_skill_dodges.py "C:/your/project/web"')
aip, gamep = root / "ai.ts", root / "game.ts"
ai, game = aip.read_text(encoding="utf-8"), gamep.read_text(encoding="utf-8")
already_ai = "SKILL_ZONE_DODGES_V1" in ai
already_game = 'followsCaster: a.at === "self"' in game
if already_ai and already_game:
    sys.exit("Already installed, no changes needed.")
if already_ai or already_game:
    sys.exit("One source appears partially patched; restore both backups before rerunning.")

def swap(before, after, text, label):
 count=text.count(before)
 if count != 1: raise RuntimeError(f'{label}: expected 1 match, found {count}')
 return text.replace(before,after)

ai=swap('''  strikes(): { target: any; land: number; id: number }[];''','''  /** Real telegraphed damage circles, not guessed from enemy animation. */
  strikes(): {
    target: any; land: number; id: number;
    center?: THREE.Vector3; radius?: number; caster?: Fighter;
    followsCaster?: boolean; style?: string;
  }[];''',ai,'Threats signature')
ai=swap('''  private seen = new Set<number>();''','''  private seen = new Set<number>();
  // SKILL_ZONE_DODGES_V1: one human-timed choice per real ground warning.
  private strikeDecisions = new Map<number, { reactAt: number; evade: boolean; side: number }>();''',ai,'decisions field')
ai=swap('''    if (!o || o.isDown()) return;
    if (this.avoidKaizenSpinGuard(f, o, dt)) return;''','''    if (!o || o.isDown()) return;
    // Marked ground impacts outrank defensive guard plans and ordinary offense.
    if (this.evadeGroundStrikes(f)) return;
    if (this.avoidKaizenSpinGuard(f, o, dt)) return;''',ai,'call')
ai=swap('''    if (!dangerous || !a) {
      this.heavyEscapeSerial = -1;''','''    // Target-locked area strikes are defended using their real marked impact
    // position instead. Running away from the caster is often the wrong direction.
    if (a?.type === "strike") return false;
    if (!dangerous || !a) {
      this.heavyEscapeSerial = -1;''',ai,'generic heavy bypass')
old='''    for (const m of this.threats.strikes()) {
      if (m.target !== f || this.seen.has(m.id)) continue;
      this.seen.add(m.id);
      const eta = m.land - this.threats.now();
      if (Math.random() < 0.3 + this.p.jump) { this.sideT = Math.min(Math.max(eta, 0.3), 0.8); this.sideSign = Math.random() < 0.5 ? 1 : -1; }
      else if (Math.random() < 0.5) this.jumpWait = Math.max(eta - 0.3, 0);
    }
'''
ai=swap(old,'',ai,'old random ground warning handler')
# Insert new method before dodge()
needle='''  private dodge(f: Fighter) {'''
new='''  /** Evade REAL telegraphed strike areas (Ocean Requiem, Thunderstorm,
   * Meteor, Tidal Ring, Arrow Rain, ground slams and other strike skills).
   * A choice is made once per actual warning and respects difficulty, reaction
   * times, walk speed, dash cooldown, arena edges and existing flame hazards.
   * There are no extra i-frames, teleports or forced successful dodges.
   */
  private evadeGroundStrikes(f: Fighter): boolean {
    const now = this.threats.now();
    const marks = this.threats.strikes();
    const live = new Set(marks.map(m => m.id));
    for (const id of this.strikeDecisions.keys()) {
      if (!live.has(id)) this.strikeDecisions.delete(id);
    }
    if (f.isDown() || !f.onGround || f.dashing() ||
        ![S.IDLE, S.BLOCK, S.CHARGE, S.ATTACK].includes(f.state) ||
        f.isKaedeThousandCutsCasting()) return false;
    type Zone = { id: number; center: THREE.Vector3; radius: number; eta: number;
      style: string; decision: { reactAt: number; evade: boolean; side: number } };
    const here = f.root.position.clone().setY(0);
    const zones: Zone[] = [];
    for (const m of marks) {
      if (!m.center || !m.radius || m.radius <= 0 || m.land <= now) continue;
      if (m.caster && (m.caster.team === f.team || m.caster.isDown())) continue;
      // The circle around a caster follows that caster until its actual impact.
      const center = (m.followsCaster && m.caster ? m.caster.root.position : m.center).clone();
      if (Math.abs(center.y - f.root.position.y) > 1.55) continue;
      center.y = 0;
      const eta = m.land - now;
      if (eta > 1.45) continue;
      const radius = m.radius + f.radius * 0.5 + 0.16;
      // If far from the circle, keep fighting instead of panic-dodging.
      if (here.distanceTo(center) > radius + Math.min(1.0, f.moveSpeed * eta)) continue;
      let decision = this.strikeDecisions.get(m.id);
      if (!decision) {
        const major = m.style === "requiem" || m.style === "lightning" ||
          m.style === "meteor" || m.style === "arrows";
        const chance = this.p.block < 0.3 ? (major ? 0.33 : 0.22) :
          this.p.block < 0.45 ? (major ? 0.60 : 0.45) :
          this.p.block < 0.6 ? (major ? 0.78 : 0.64) :
          (major ? 0.91 : 0.82);
        decision = {
          reactAt: now + rand(this.p.react[0] * 0.65, this.p.react[1] * 0.90),
          evade: Math.random() < chance,
          side: Math.random() < 0.5 ? -1 : 1,
        };
        this.strikeDecisions.set(m.id, decision);
      }
      zones.push({ id: m.id, center, radius, eta, style: m.style || "", decision });
    }
    const imminent = zones.filter(z => z.decision.evade && now >= z.decision.reactAt &&
      z.eta > 0.015 && here.distanceTo(z.center) < z.radius + 0.45)
      .sort((a, b) => a.eta - b.eta);
    if (!imminent.length) return false;
    const primary = imminent[0];
    const fromCenter = here.clone().sub(primary.center);
    if (fromCenter.lengthSq() < 0.0001) fromCenter.set(f.id % 2 ? 1 : -1, 0, 0);
    fromCenter.normalize();
    const flank = new THREE.Vector3(-fromCenter.z, 0, fromCenter.x)
      .multiplyScalar(primary.decision.side);
    const candidates = [
      fromCenter, fromCenter.clone().addScaledVector(flank, 0.65).normalize(),
      fromCenter.clone().addScaledVector(flank, -0.65).normalize(),
      flank, flank.clone().negate(),
      fromCenter.clone().negate().addScaledVector(flank, 0.6).normalize(),
    ];
    // A single marked Thunderstorm hit can be escaped by walking if the AI
    // reacts early enough. Reserve a real 3-second dash for the larger circles.
    const steer = f.state === S.IDLE ? 1 : f.state === S.BLOCK ? 0.50 :
      f.state === S.CHARGE ? 0.4 : 0;
    const canDash = f.dashCd <= 0 &&
      (f.kit !== "hammer" || f.state !== S.ATTACK ||
        (f.atkPhase === 0 && !!f.atk && f.stateT < f.atk.wind));
    const walkDist = f.moveSpeed * steer * Math.max(0, primary.eta - 0.045);
    const patches = this.threats.firePatches(f);
    const main = f.stage?.plats[0];
    const destination = (dir: THREE.Vector3, distance: number) => {
      const end = here.clone().addScaledVector(dir, distance);
      if (main) end.x = THREE.MathUtils.clamp(end.x, main.x0 + 0.65, main.x1 - 0.65);
      else {
        const max = f.arenaRadius - Math.max(0.17, f.radius * 0.15);
        const d = end.length();
        if (d > max) end.multiplyScalar(max / d);
      }
      return end;
    };
    const score = (end: THREE.Vector3) => {
      let result = 0;
      // Value escaping multiple overlapping circles, not just the first one.
      for (const zone of zones) {
        const clearance = end.distanceTo(zone.center) - zone.radius;
        const importance = zone.id === primary.id ? 2.8 :
          zone.eta <= primary.eta + 0.27 ? 1.2 : 0.45;
        result += importance * THREE.MathUtils.clamp(clearance, -3, 0.65);
      }
      for (const fire of patches) {
        if (Math.abs(fire.pos.y - f.root.position.y) > 1.55) continue;
        const gap = end.distanceTo(fire.pos.clone().setY(0));
        const safe = fire.radius + f.radius * 0.3 + 0.2;
        if (gap < safe) result -= (safe - gap + 0.2) * 5;
      }
      // Prefer a real escape path over a direction blocked by the arena wall.
      result += Math.min(end.distanceTo(here), 2.6) * 0.15;
      return result;
    };
    let bestWalk = candidates[0], bestWalkScore = -Infinity;
    let bestDash = candidates[0], bestDashScore = -Infinity;
    for (const raw of candidates) {
      const dir = main ? new THREE.Vector3(Math.sign(raw.x) || (f.id % 2 ? 1 : -1), 0, 0) : raw;
      const walk = score(destination(dir, walkDist));
      if (walk > bestWalkScore) { bestWalkScore = walk; bestWalk = dir; }
      if (canDash) {
        // A normal dash moves 14 units/s for 0.30s; use only the distance
        // available before impact when estimating whether this will escape.
        const dashDist = 14 * Math.min(0.3, primary.eta);
        const dash = score(destination(dir, dashDist + f.moveSpeed *
          Math.max(0, primary.eta - 0.3) * 0.85));
        if (dash > bestDashScore) { bestDashScore = dash; bestDash = dir; }
      }
    }
    const canWalkOut = steer > 0 && bestWalkScore >= 0.13;
    // Dodging is intentional, but not omniscient: only spend dash when ordinary
    // footwork will not safely leave the marked impact area in time.
    const useDash = canDash && (!canWalkOut ||
      (primary.eta < 0.19 && bestDashScore > bestWalkScore + 0.25)) &&
      bestDashScore > bestWalkScore + 0.10;
    if (!useDash && steer <= 0) return false;
    const dir = useDash ? bestDash : bestWalk;
    this.queue = [];
    this.hold = 0;
    this.blockWait = -1;
    this.blockHold = 0;
    this.jumpWait = -1;
    f.intent.block = false;
    f.intent.attack = false;
    f.intent.skill = "";
    f.intent.sprint = false;
    f.intent.move.copy(dir);
    if (useDash) f.intent.dash.copy(dir);
    return true;
  }

'''+needle
ai=swap(needle,new,ai,'add method')

game=swap('''  private strikeMarks: { target: any; land: number; id: number }[] = [];''','''  private strikeMarks: {
    target: any; land: number; id: number; center?: THREE.Vector3;
    radius?: number; caster?: Fighter; followsCaster?: boolean; style?: string;
  }[] = [];''',game,'marks declaration')
game=swap('''      const mark = { target: f.opponent, land: this.time + wait, id: this.nextId++ };''','''      const mark = {
        target: f.opponent, land: this.time + wait, id: this.nextId++,
        center: center.clone(), radius: a.radius, caster: f,
        followsCaster: a.at === "self", style: a.style,
      };''',game,'mark payload')
game=swap('''    const mark = { target: null, land: this.time + delay, id: this.nextId++ };''','''    const mark = {
      target: null, land: this.time + delay, id: this.nextId++,
      center: c.clone(), radius, style,
    };''',game,'mob mark payload')
# Back up both source files after checking all expected source fragments.
for path in (aip, gamep):
    backup = path.with_name(path.name + ".before_skill_dodge.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
aip.write_text(ai, encoding="utf-8")
gamep.write_text(game, encoding="utf-8")
print("Installed skill-zone dodges in:", root)
print("Backups: ai.ts.before_skill_dodge.bak, game.ts.before_skill_dodge.bak")
