"use client";
import { useEffect, useRef, useState } from "react";
import type { Net } from "@/game/net";
import { CHARACTERS } from "@/game/roster";
import type { GameConfig, PlayerSlot } from "@/game/game";
import { RANKS, cpuLevel, loadRank, rankIcon, rankLabel, rankScore, type RankState } from "@/game/rank";
import { account } from "@/lib/account";
import { Matchmaker, type Seeker } from "@/lib/matchmaking";
import { CardRow, EmblemPicker, InfoPanel, Showcase } from "./Select";
import { Icon } from "./icons";

/** CPU fallback offered after this long in the queue. */
const CPU_AFTER = 20000;

/** Rank emblem, name and the stars of the current tier. */
export function RankBadge({ st, size = 72 }: { st: RankState; size?: number }) {
  const d = RANKS[st.r];
  const mythic = d.stars === 0;
  return (
    <div className="rank-badge">
      <Icon src={rankIcon(st.r)} alt={d.name} size={size} fallback={<i style={{ background: d.color, width: size, height: size, borderRadius: "50%", display: "inline-block" }} />} />
      <div>
        <b style={{ color: d.color }}>{rankLabel(st)}</b>
        <div className="stars">
          {mythic ? <span className="mythic-stars"><img src="/icons/ranks/star.webp" alt="" /> x {st.s}</span>
            : Array.from({ length: d.stars }, (_, i) => (
              <img key={i} src={i < st.s ? "/icons/ranks/star.webp" : "/icons/ranks/star_empty.webp"} alt={i < st.s ? "star" : "empty star"} />
            ))}
        </div>
      </div>
    </div>
  );
}

export default function Ranked({ name, onBack, onShop, onStart }: {
  name: string;
  onBack: () => void;
  onShop: () => void;
  onStart: (cfg: GameConfig, net: Net | null) => void;
}) {
  const firstOwned = Math.max(0, CHARACTERS.findIndex((c) => account.owns(c.id)));
  const [myChar, setMyChar] = useState(firstOwned);
  const [st, setSt] = useState<RankState>(() => loadRank());
  const [searching, setSearching] = useState(false);
  const [status, setStatus] = useState("");
  const [waited, setWaited] = useState(0);
  const [offline, setOffline] = useState("");
  const mm = useRef<Matchmaker | null>(null);
  const started = useRef(false);
  const charRef = useRef(myChar);
  charRef.current = myChar;

  useEffect(() => { setSt(loadRank()); return () => { mm.current?.cancel(); }; }, []);

  const locked = !account.owns(CHARACTERS[myChar].id);
  const me = (peer: string): PlayerSlot => ({ peer, name, char: charRef.current, team: 0, ...account.matchKit(charRef.current) });

  const vsCpu = () => {
    mm.current?.cancel();
    const pool = CHARACTERS.map((_, i) => i).filter((i) => i !== charRef.current);
    const cpu = pool[Math.floor(Math.random() * pool.length)];
    onStart({ mode: "duel", role: "offline", players: [me("local")], localPeer: "local", cpuChar: cpu, difficulty: cpuLevel(st), ranked: true }, null);
  };

  /** Matched: the host waits for the guest's fighter, then starts the duel for both. */
  const matched = (net: Net, opp: Seeker) => {
    setStatus(`Matched with ${opp.name}!`);
    if (net.role === "host") {
      net.onMessage = (from, msg) => {
        if (msg.t !== "hello" || started.current) return;
        const guest: PlayerSlot = { peer: from, name: String(msg.name).slice(0, 16), char: msg.char ?? 0, team: 1, loadout: msg.loadout, emblem: msg.emblem };
        const players = [me(net.myId), guest];
        started.current = true;
        net.broadcast({ t: "start", cfg: { mode: "duel", players, ranked: true } });
        onStart({ mode: "duel", role: "host", players, localPeer: net.myId, ranked: true }, net);
      };
    } else {
      net.onMessage = (_from, msg) => {
        if (msg.t !== "start" || started.current) return;
        started.current = true;
        clearInterval(hello);
        onStart({ ...msg.cfg, role: "client", localPeer: net.myId, ranked: true }, net);
      };
      // Say hello until the host starts (the first one can arrive before the host listens).
      const send = () => net.send({ t: "hello", name, char: charRef.current, ...account.matchKit(charRef.current) });
      send();
      const hello = setInterval(send, 1000);
      net.onLeave = () => { clearInterval(hello); setStatus("The opponent left. Search again."); setSearching(false); };
    }
  };

  const find = () => {
    setOffline("");
    setSearching(true);
    setWaited(0);
    setStatus("Joining the queue...");
    const m = new Matchmaker(name, rankScore(st));
    mm.current = m;
    m.onStatus = (text, ms) => { setStatus(text); setWaited(ms); };
    m.onMatched = matched;
    m.onOffline = (reason) => { setOffline(reason); setStatus(""); };
    m.start();
  };

  const cancel = () => { mm.current?.cancel(); mm.current = null; setSearching(false); setStatus(""); };

  const d = RANKS[st.r];
  return (
    <div className="select">
      <Showcase index={myChar} />
      <div className="header">
        <h1>RANKED</h1>
        <div className="sub">1v1 duels. Win to earn stars, fill a tier's stars to rank up. Matched with players near your rank.</div>
      </div>
      <div className="panel lobby-panel">
        <RankBadge st={st} />
        <div className="small">
          {st.wins}W {st.losses}L{st.wins + st.losses > 0 ? ` (${Math.round((100 * st.wins) / (st.wins + st.losses))}%)` : ""}
          {st.streak >= 2 ? ` - ${st.streak} win streak` : ""}
          {d.protect ? ` - ${d.name} is protected: losses don't cost stars` : ""}
        </div>
        <h3>Ladder</h3>
        <div className="rank-ladder">
          {RANKS.map((r, i) => (
            <div key={r.id} className={"rung" + (i === st.r ? " on" : "")} title={r.stars ? `${r.tiers} tiers x ${r.stars} stars` : "Unlimited stars"}>
              <Icon src={rankIcon(i)} alt={r.name} size={34} fallback={<i style={{ background: r.color }} />} />
              <span style={{ color: r.color }}>{r.name}</span>
            </div>
          ))}
        </div>
        <h3>Your emblem</h3>
        <EmblemPicker compact />
        {searching && (
          <div className="queue">
            <div className="spinner" />
            <div>
              <b>{status}</b>
              <div className="small">{Math.floor(waited / 1000)}s in queue</div>
            </div>
          </div>
        )}
        {offline && <div className="error">{offline} You can still play a ranked match against the CPU.</div>}
        <InfoPanel index={myChar} editable />
      </div>
      <div className="bottom">
        <CardRow current={myChar} onPick={(i) => !searching && setMyChar(i)} showLocks />
        <div className="actions">
          <div className="row">
            <button className="big ghost" onClick={() => { cancel(); onBack(); }}>&lt; BACK</button>
            {locked ? <button className="big gold" onClick={onShop}>UNLOCK IN SHOP</button>
              : searching ? (
                <>
                  {waited >= CPU_AFTER && <button className="big blue" onClick={vsCpu}>FIGHT CPU</button>}
                  <button className="big ghost" onClick={cancel}>CANCEL</button>
                </>
              ) : (
                <>
                  <button className="big gold" onClick={find}>FIND MATCH</button>
                  {offline && <button className="big blue" onClick={vsCpu}>RANKED VS CPU</button>}
                </>
              )}
          </div>
        </div>
      </div>
    </div>
  );
}
