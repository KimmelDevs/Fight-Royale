// Status effects that skills leave on whoever they hit (fighters and survival mobs).
//   burn     - fire damage over time
//   poison   - weaker damage over time that lasts longer and stacks up to 3 times
//   bleed    - damage over time, stronger while the target keeps moving
//   paralyze - slowed, and jolted (interrupted) every second
//   slow     - moves slower
//   weaken   - deals less damage
// The host runs them; online clients only see which ones are active (a bitmask in snapshots).

export type StatusKind = "burn" | "poison" | "bleed" | "paralyze" | "slow" | "weaken";

export const STATUS: Record<StatusKind, { label: string; color: string; bit: number; text: (t: number, p: number) => string }> = {
  burn: { label: "BURN", color: "#ff7a2e", bit: 1, text: (t, p) => `Burn: ${p} dmg/s for ${t}s` },
  poison: { label: "POISON", color: "#8ee05a", bit: 2, text: (t, p) => `Poison: ${p} dmg/s for ${t}s, stacks x3` },
  bleed: { label: "BLEED", color: "#e0303e", bit: 4, text: (t, p) => `Bleed: ${p} dmg/s for ${t}s (x1.5 while moving)` },
  paralyze: { label: "PARALYZED", color: "#ffe066", bit: 8, text: (t) => `Paralyze: ${t}s (slowed, jolted every second)` },
  slow: { label: "SLOWED", color: "#7fc8ff", bit: 16, text: (t, p) => `Slow: -${Math.round((1 - p) * 100)}% speed for ${t}s` },
  weaken: { label: "WEAKENED", color: "#fff2b0", bit: 32, text: (t, p) => `Weaken: -${Math.round((1 - p) * 100)}% damage for ${t}s` },
};

const DOT_TICK = 0.5;
const POISON_STACKS = 3;
const JOLT_EVERY = 1.0;
const PARALYZE_SPEED = 0.6;

interface Active { t: number; p: number; stacks: number; tick: number; jolt: number }

export class StatusSet {
  private m = new Map<StatusKind, Active>();
  /** Bitmask of active effects (also set directly on online puppets). */
  mask = 0;
  /** Who applied the most recent effect (credited for damage-over-time kills). */
  src: unknown = null;

  apply(kind: StatusKind, t: number, p: number, src: unknown = null) {
    if (src) this.src = src;
    const cur = this.m.get(kind);
    if (cur) {
      cur.t = Math.max(cur.t, t);
      if (kind === "poison") cur.stacks = Math.min(cur.stacks + 1, POISON_STACKS);
      else cur.p = kind === "slow" || kind === "weaken" ? Math.min(cur.p, p) : Math.max(cur.p, p);
    } else {
      this.m.set(kind, { t, p, stacks: 1, tick: DOT_TICK, jolt: JOLT_EVERY * 0.5 });
    }
    this.syncMask();
  }

  has(kind: StatusKind) { return (this.mask & STATUS[kind].bit) !== 0; }
  clear() { this.m.clear(); this.mask = 0; this.src = null; }

  /** Movement multiplier (slow, paralyze). */
  speedMult() {
    let k = 1;
    const s = this.m.get("slow");
    if (s) k *= s.p;
    if (this.m.has("paralyze")) k *= PARALYZE_SPEED;
    return k;
  }

  /** Outgoing damage multiplier (weaken). */
  dmgMult() { return this.m.get("weaken")?.p ?? 1; }

  /**
   * Advance timers. Returns damage-over-time ticks and whether a paralyze jolt fires this frame.
   * `moving` makes bleed hit harder.
   */
  tick(dt: number, moving: boolean): { dots: { kind: StatusKind; dmg: number }[]; jolt: boolean } {
    const dots: { kind: StatusKind; dmg: number }[] = [];
    let jolt = false;
    for (const [kind, s] of this.m) {
      s.t -= dt;
      if (kind === "burn" || kind === "poison" || kind === "bleed") {
        s.tick -= dt;
        if (s.tick <= 0) {
          s.tick += DOT_TICK;
          const mult = kind === "poison" ? s.stacks : kind === "bleed" && moving ? 1.5 : 1;
          dots.push({ kind, dmg: s.p * DOT_TICK * mult });
        }
      } else if (kind === "paralyze") {
        s.jolt -= dt;
        if (s.jolt <= 0) { s.jolt += JOLT_EVERY; jolt = true; }
      }
      if (s.t <= 0) this.m.delete(kind);
    }
    this.syncMask();
    return { dots, jolt };
  }

  kinds(): StatusKind[] {
    return (Object.keys(STATUS) as StatusKind[]).filter((k) => this.has(k));
  }

  private syncMask() {
    let b = 0;
    for (const k of this.m.keys()) b |= STATUS[k].bit;
    this.mask = b;
  }
}
