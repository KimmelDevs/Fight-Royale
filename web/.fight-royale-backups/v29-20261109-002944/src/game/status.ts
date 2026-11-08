// PASSIVE_ROSTER_V10 — roster-wide passives, readable HUD and CPU visibility.
// ASTER_WEAKEN_50S_5_STACKS_V1_20261107
// Status effects that skills leave on whoever they hit (fighters and survival mobs).
//   burn     - fire damage over time
//   poison   - weaker damage over time that lasts longer and stacks up to 3 times
//   bleed    - damage over time, stronger while the target keeps moving
//   paralyze - slowed, and jolted (interrupted) every second
//   slow     - moves slower
//   weaken   - deals less damage
// The host runs them; online clients only see which ones are active (a bitmask in snapshots).

export type StatusKind = "burn" | "poison" | "bleed" | "paralyze" | "slow" | "weaken" | "freeze";

export const STATUS: Record<StatusKind, { label: string; color: string; bit: number; text: (t: number, p: number) => string }> = {
  burn: { label: "BURN", color: "#ff7a2e", bit: 1, text: (t, p) => `Burn: ${p} dmg/s for ${t}s` },
  poison: { label: "POISON", color: "#8ee05a", bit: 2, text: (t, p) => `Poison: ${p} dmg/s for ${t}s, stacks x3` },
  bleed: { label: "BLEED", color: "#e0303e", bit: 4, text: (t, p) => `Bleed: ${p} dmg/s per stack for ${t}s (Zenith skills only: up to x2; x1.5 while moving)` },
  paralyze: { label: "PARALYZED", color: "#ffe066", bit: 8, text: (t) => `Paralyze: ${t}s (22% slowed, jolted every 1.6s; 4s immunity after recovery)` },
  slow: { label: "SLOWED", color: "#7fc8ff", bit: 16, text: (t, p) => `Slow: -${Math.round((1 - p) * 100)}% movement, attack and cast speed for ${t}s` },
  freeze: { label: "FROZEN", color: "#c5f7ff", bit: 64, text: (t) => `Freeze: immobilized and unable to attack for ${t}s` },
  weaken: { label: "WEAKENED", color: "#fff2b0", bit: 32, text: (t, p) => `Weaken: -${Math.round((1 - p) * 100)}% outgoing damage per stack (multiplicative); up to 5 stacks (${Math.round((1 - Math.pow(p, 5)) * 100)}% max). Lasts ${t}s; each hit adds a stack and refreshes the timer.` },
};

const DOT_TICK = 0.5;
const POISON_STACKS = 3;
const ZENITH_BLEED_MAX_STACKS = 2; // ZENITH_BLEED_SKILL_ONLY_AI_V15
const WEAKEN_STACKS = 5;
const JOLT_EVERY = 1.6; // V10: softened jolt frequency
const PARALYZE_SPEED = 0.78; // V10: 22% slow instead of 40%

interface Active { t: number; p: number; stacks: number; tick: number; jolt: number }

export class StatusSet {
  private m = new Map<StatusKind, Active>();
  // ZENITH_TWIN_BLADES_CATCH_CHOREO_V5_20261108: reject new CC at the status-entry point.
  private ccImmuneT = 0;
  grantCcImmunity(t: number) { this.ccImmuneT = Math.max(this.ccImmuneT, t); }
  // ROXY_FLOATING_BOOK_FROSTWING_FREEZE_V4_20261108: immunity starts AFTER thawing.
  private freezeImmuneT = 0;
  private paralyzeImmuneT = 0;
  paralyzeImmunityRemaining() { return this.paralyzeImmuneT; }
  freezeImmunityRemaining() { return this.freezeImmuneT; }
  /** Bitmask of active effects (also set directly on online puppets). */
  mask = 0;
  /** Who applied the most recent effect (credited for damage-over-time kills). */
  src: unknown = null;

  apply(kind: StatusKind, t: number, p: number, src: unknown = null): boolean {
    if (this.ccImmuneT > 0 && (kind === "freeze" || kind === "paralyze" || kind === "slow")) return false;
    if (kind === "paralyze" && this.paralyzeImmuneT > 0) return false;
    if (kind === "paralyze") t += 1.0; // V10: one extra second, once on application
    // Incoming Freeze may damage, but cannot refresh, chain, or bypass thaw immunity.
    if (kind === "freeze" && (this.m.has("freeze") || this.freezeImmuneT > 0)) return false;
    if (src) this.src = src;
    const cur = this.m.get(kind);
    if (cur) {
      // Weaken always refreshes its entire 50s duration when another hit lands.
      cur.t = kind === "weaken" ? t : Math.max(cur.t, t);
      if (kind === "poison") cur.stacks = Math.min(cur.stacks + 1, POISON_STACKS);
      else if (kind === "weaken") {
        cur.stacks = Math.min(cur.stacks + 1, WEAKEN_STACKS);
        cur.p = Math.min(cur.p, p); // each stack uses the strongest existing reduction
      } else cur.p = kind === "slow" ? Math.min(cur.p, p) : Math.max(cur.p, p);
    } else {
      this.m.set(kind, { t, p, stacks: 1, tick: DOT_TICK, jolt: JOLT_EVERY * 0.5 });
    }
    this.syncMask();
    return true;
  }

  /** Zenith alone can stack bleed. Other bleed sources keep their original one-stack rules. */
  applyStackingBleed(t: number, p: number, src: unknown = null): number {
    if (src) this.src = src;
    const cur = this.m.get("bleed");
    if (cur) {
      cur.stacks = Math.min(ZENITH_BLEED_MAX_STACKS, cur.stacks + 1);
      cur.t = Math.max(cur.t, t);
      cur.p = Math.max(cur.p, p);
    } else {
      this.m.set("bleed", { t, p, stacks: 1, tick: DOT_TICK, jolt: JOLT_EVERY * 0.5 });
    }
    this.syncMask();
    return this.stacks("bleed");
  }

  has(kind: StatusKind) { return (this.mask & STATUS[kind].bit) !== 0; }
  stacks(kind: StatusKind) { return this.m.get(kind)?.stacks ?? 0; }
  consume(kind: StatusKind) { const n = this.stacks(kind); this.m.delete(kind); this.syncMask(); return n; }
  clear() { this.m.clear(); this.mask = 0; this.src = null; this.freezeImmuneT = 0; this.ccImmuneT = 0; this.paralyzeImmuneT = 0; }

  /** Slow also affects attack animation and the casting/wind-up of skills. */
  actionSpeedMult() {
    if (this.m.has("freeze")) return 0;
    return this.m.get("slow")?.p ?? 1;
  }

  /** Movement multiplier (slow, paralyze). */
  speedMult() {
    let k = 1;
    const s = this.m.get("slow");
    if (s) k *= s.p;
    if (this.m.has("paralyze")) k *= PARALYZE_SPEED;
    if (this.m.has("freeze")) return 0;
    return k;
  }

  /** Every Weaken stack multiplies outgoing damage by the skill's power (0.8^stacks for Aster). */
  dmgMult() {
    const weaken = this.m.get("weaken");
    return weaken ? Math.pow(weaken.p, weaken.stacks) : 1;
  }

  /**
   * Advance timers. Returns damage-over-time ticks and whether a paralyze jolt fires this frame.
   * `moving` makes bleed hit harder.
   */
  tick(dt: number, moving: boolean): { dots: { kind: StatusKind; dmg: number }[]; jolt: boolean } {
    const dots: { kind: StatusKind; dmg: number }[] = [];
    let jolt = false;
    let thawed = false;
    let paralyzeExpired = false;
    this.freezeImmuneT = Math.max(0, this.freezeImmuneT - dt);
    this.paralyzeImmuneT = Math.max(0, this.paralyzeImmuneT - dt);
    this.ccImmuneT = Math.max(0, this.ccImmuneT - dt);
    for (const [kind, s] of this.m) {
      s.t -= dt;
      if (kind === "burn" || kind === "poison" || kind === "bleed") {
        s.tick -= dt;
        if (s.tick <= 0) {
          s.tick += DOT_TICK;
          const mult = kind === "poison" ? s.stacks :
            kind === "bleed" ? s.stacks * (moving ? 1.5 : 1) : 1;
          dots.push({ kind, dmg: s.p * DOT_TICK * mult });
        }
      } else if (kind === "paralyze") {
        s.jolt -= dt;
        if (s.jolt <= 0) { s.jolt += JOLT_EVERY; jolt = true; }
      }
      if (s.t <= 0) {
        this.m.delete(kind);
        if (kind === "freeze") thawed = true;
        if (kind === "paralyze") paralyzeExpired = true;
      }
    }
    if (paralyzeExpired) this.paralyzeImmuneT = 4; // 4s begins when paralyze ENDS
    if (thawed) {
      // 4s total re-freeze lockout, beginning at thaw; 2s of 35% slow.
      this.freezeImmuneT = 4.0;
      this.apply("slow", 2.0, 0.65, this.src);
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
