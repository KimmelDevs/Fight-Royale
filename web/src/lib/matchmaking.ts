// Ranked matchmaking without a game server.
// Everyone searching joins one Supabase Realtime presence channel and announces their rank
// score. The player who has waited longest picks the closest-ranked opponent (the allowed rank
// gap widens the longer they wait), opens a PeerJS room and sends that player the room code;
// the opponent joins it and the match runs peer-to-peer like any online duel.
import { Net } from "@/game/net";
import { supabase } from "./account";

export interface Seeker { pid: string; name: string; score: number; since: number }

const CHANNEL = "fr-ranked-queue";
const OFFER_TIMEOUT = 8000;

export class Matchmaker {
  onStatus: (text: string, waited: number) => void = () => {};
  onMatched: (net: Net, opponent: Seeker) => void = () => {};
  onOffline: (reason: string) => void = () => {};
  readonly me: Seeker;
  private channel: ReturnType<NonNullable<typeof supabase>["channel"]> | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private busy = false;
  private done = false;
  private skip = new Map<string, number>();

  constructor(name: string, score: number) {
    this.me = { pid: Math.random().toString(36).slice(2, 10), name, score, since: Date.now() };
  }

  start() {
    if (!supabase) { this.onOffline("Matchmaking needs the online service, which isn't configured."); return; }
    const ch = supabase.channel(CHANNEL, { config: { presence: { key: this.me.pid }, broadcast: { self: false } } });
    this.channel = ch;
    ch.on("broadcast", { event: "offer" }, ({ payload }) => this.onOffer(payload));
    ch.subscribe(async (status) => {
      if (this.done) return;
      if (status === "SUBSCRIBED") {
        await ch.track(this.me);
        this.timer = setInterval(() => this.tick(), 1000);
        this.tick();
      } else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") {
        this.onOffline("Couldn't reach the matchmaking service.");
      }
    });
  }

  cancel() {
    this.done = true;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    const ch = this.channel;
    this.channel = null;
    if (ch) { ch.untrack().catch(() => {}); supabase?.removeChannel(ch); }
  }

  private others(): Seeker[] {
    const state = (this.channel?.presenceState() ?? {}) as Record<string, Seeker[]>;
    return Object.values(state).flat().filter((s) => s && s.pid && s.pid !== this.me.pid);
  }

  /** Allowed rank gap (in stars) for someone who has waited `ms`: 4 stars, +1 every 4 s. */
  private static gap(ms: number) { return 4 + Math.floor(ms / 4000); }

  private tick() {
    if (this.done || this.busy) return;
    const now = Date.now();
    const waited = now - this.me.since;
    const others = this.others();
    this.onStatus(others.length ? `Searching... ${others.length} other player${others.length === 1 ? "" : "s"} in queue` : "Searching for an opponent...", waited);
    // Only the player who has waited longer makes the offer, so two players never invite each other.
    const older = (a: Seeker, b: Seeker) => a.since < b.since || (a.since === b.since && a.pid < b.pid);
    const fits = others
      .filter((o) => older(this.me, o) && (this.skip.get(o.pid) ?? 0) < now)
      .filter((o) => Math.abs(o.score - this.me.score) <= Math.max(Matchmaker.gap(waited), Matchmaker.gap(now - o.since)))
      .sort((a, b) => Math.abs(a.score - this.me.score) - Math.abs(b.score - this.me.score));
    if (fits.length) this.propose(fits[0]);
  }

  private async propose(o: Seeker) {
    this.busy = true;
    this.onStatus(`Opponent found: ${o.name}. Connecting...`, Date.now() - this.me.since);
    let net: Net | null = null;
    try {
      net = await Net.host();
      const joined = new Promise<boolean>((resolve) => {
        const t = setTimeout(() => resolve(false), OFFER_TIMEOUT);
        net!.onJoin = () => { clearTimeout(t); resolve(true); };
      });
      await this.channel?.send({ type: "broadcast", event: "offer", payload: { to: o.pid, from: this.me, code: net.code } });
      if (await joined && !this.done) {
        this.finish(net, o);
        return;
      }
    } catch {}
    net?.close();
    this.skip.set(o.pid, Date.now() + 10000);
    this.busy = false;
  }

  private async onOffer(p: { to: string; from: Seeker; code: string }) {
    if (this.done || this.busy || p?.to !== this.me.pid) return;
    this.busy = true;
    this.onStatus(`Opponent found: ${p.from.name}. Connecting...`, Date.now() - this.me.since);
    try {
      const net = await Net.join(p.code);
      if (this.done) { net.close(); return; }
      this.finish(net, p.from);
    } catch {
      this.busy = false;
    }
  }

  private finish(net: Net, o: Seeker) {
    this.cancel();
    this.onMatched(net, o);
  }
}
