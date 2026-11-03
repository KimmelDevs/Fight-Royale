// Peer-to-peer networking over WebRTC (PeerJS). The host's browser runs the simulation;
// guests connect with a short room code. PeerJS's free public broker only introduces the
// peers, so no game server is needed (works from a static Vercel deploy).
import type { DataConnection, Peer as PeerType } from "peerjs";

const PREFIX = "fightroyale-";

export type Msg = { t: string; [k: string]: any };

export class Net {
  role: "host" | "client";
  code = "";
  myId = "";
  onMessage: (from: string, msg: Msg) => void = () => {};
  onLeave: (peer: string) => void = () => {};
  onJoin: (peer: string) => void = () => {};
  onError: (err: string) => void = () => {};
  private peer: PeerType | null = null;
  private conns = new Map<string, DataConnection>();
  private host: DataConnection | null = null;

  private constructor(role: "host" | "client") {
    this.role = role;
  }

  static async host(): Promise<Net> {
    const { Peer } = await import("peerjs");
    const n = new Net("host");
    for (let attempt = 0; attempt < 4; attempt++) {
      const code = Math.random().toString(36).slice(2, 7).toUpperCase();
      try {
        await new Promise<void>((resolve, reject) => {
          const p = new Peer(PREFIX + code, { debug: 1 });
          p.on("open", (id) => { n.peer = p; n.myId = id; n.code = code; resolve(); });
          p.on("error", (e: any) => { if (!n.peer) { p.destroy(); reject(e); } else n.onError(String(e?.type ?? e)); });
        });
        break;
      } catch (e: any) {
        if (e?.type !== "unavailable-id" || attempt === 3) throw new Error(`Could not create room: ${e?.type ?? e}`);
      }
    }
    n.peer!.on("connection", (c) => {
      c.on("open", () => { n.conns.set(c.peer, c); n.onJoin(c.peer); });
      c.on("data", (d) => n.onMessage(c.peer, d as Msg));
      c.on("close", () => { n.conns.delete(c.peer); n.onLeave(c.peer); });
    });
    return n;
  }

  static async join(code: string): Promise<Net> {
    const { Peer } = await import("peerjs");
    const n = new Net("client");
    n.code = code.trim().toUpperCase();
    await new Promise<void>((resolve, reject) => {
      const p = new Peer({ debug: 1 });
      p.on("error", (e: any) => { const m = e?.type === "peer-unavailable" ? "Room not found" : String(e?.type ?? e); if (!n.host) reject(new Error(m)); else n.onError(m); });
      p.on("open", (id) => {
        n.peer = p;
        n.myId = id;
        const c = p.connect(PREFIX + n.code, { reliable: true, serialization: "json" });
        const timer = setTimeout(() => reject(new Error("Timed out connecting to host")), 12000);
        c.on("open", () => { clearTimeout(timer); n.host = c; resolve(); });
        c.on("data", (d) => n.onMessage(c.peer, d as Msg));
        c.on("close", () => n.onLeave("host"));
      });
    });
    return n;
  }

  /** Guest -> host. */
  send(msg: Msg) { if (this.host?.open) this.host.send(msg); }
  /** Host -> every guest. */
  broadcast(msg: Msg) { for (const c of this.conns.values()) if (c.open) c.send(msg); }
  sendTo(peer: string, msg: Msg) { const c = this.conns.get(peer); if (c?.open) c.send(msg); }
  peers() { return [...this.conns.keys()]; }

  close() {
    this.conns.forEach((c) => c.close());
    this.host?.close();
    this.peer?.destroy();
    this.conns.clear();
  }
}
