"use client";
import { useEffect, useRef, useState } from "react";
import { Net } from "@/game/net";
import { CHARACTERS } from "@/game/roster";
import type { GameConfig, PlayerSlot } from "@/game/game";
import { CardRow, InfoPanel, Showcase } from "./Select";

type Mode = "survival" | "duel";

export default function Lobby({ name, onBack, onStart }: {
  name: string;
  onBack: () => void;
  onStart: (cfg: GameConfig, net: Net) => void;
}) {
  const [net, setNet] = useState<Net | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [players, setPlayers] = useState<PlayerSlot[]>([]);
  const [mode, setMode] = useState<Mode>("survival");
  const [myChar, setMyChar] = useState(0);
  const started = useRef(false);
  const playersRef = useRef<PlayerSlot[]>([]);
  const modeRef = useRef<Mode>("survival");
  playersRef.current = players;
  modeRef.current = mode;

  // Leave the room if the lobby closes without starting a match.
  useEffect(() => () => { if (!started.current) netRef.current?.close(); }, []);
  const netRef = useRef<Net | null>(null);

  const host = async () => {
    setBusy("Creating room...");
    setError("");
    try {
      const n = await Net.host();
      netRef.current = n;
      const me: PlayerSlot = { peer: n.myId, name, char: myChar };
      setPlayers([me]);
      const sync = (list: PlayerSlot[]) => { setPlayers(list); n.broadcast({ t: "lobby", players: list, mode: modeRef.current }); };
      n.onMessage = (from, msg) => {
        const list = [...playersRef.current];
        if (msg.t === "hello") {
          if (list.length >= 4) return;
          list.push({ peer: from, name: String(msg.name).slice(0, 14), char: msg.char ?? 0 });
          sync(list);
        } else if (msg.t === "pick") {
          sync(list.map((p) => (p.peer === from ? { ...p, char: msg.char } : p)));
        }
      };
      n.onLeave = (peer) => sync(playersRef.current.filter((p) => p.peer !== peer));
      setNet(n);
    } catch (e: any) {
      setError(e.message ?? String(e));
    }
    setBusy("");
  };

  const join = async () => {
    if (!joinCode.trim()) return;
    setBusy("Connecting...");
    setError("");
    try {
      const n = await Net.join(joinCode);
      netRef.current = n;
      n.onMessage = (_from, msg) => {
        if (msg.t === "lobby") { setPlayers(msg.players); setMode(msg.mode); }
        else if (msg.t === "start") {
          started.current = true;
          onStart({ ...msg.cfg, role: "client", localPeer: n.myId }, n);
        }
      };
      n.onLeave = () => { setError("The host closed the room."); setNet(null); };
      n.send({ t: "hello", name, char: myChar });
      setNet(n);
    } catch (e: any) {
      setError(e.message ?? String(e));
    }
    setBusy("");
  };

  const pick = (i: number) => {
    setMyChar(i);
    if (!net) return;
    if (net.role === "host") {
      const list = players.map((p) => (p.peer === net.myId ? { ...p, char: i } : p));
      setPlayers(list);
      net.broadcast({ t: "lobby", players: list, mode });
    } else net.send({ t: "pick", char: i });
  };

  const changeMode = (m: Mode) => {
    setMode(m);
    net?.broadcast({ t: "lobby", players, mode: m });
  };

  const canStart = net?.role === "host" && (mode === "survival" ? players.length >= 1 : players.length === 2);
  const start = () => {
    if (!net || !canStart) return;
    const cfg: GameConfig = { mode, role: "host", players, localPeer: net.myId };
    net.broadcast({ t: "start", cfg: { mode, players } });
    started.current = true;
    onStart(cfg, net);
  };

  if (!net) {
    return (
      <div className="menu">
        <div className="menu-card">
          <h1 className="logo small">PLAY ONLINE</h1>
          <p className="tag">Co-op survival (up to 4) or a 1v1 duel with a friend. Peer-to-peer, no account needed.</p>
          <button className="big gold" disabled={!!busy} onClick={host}>Host a room</button>
          <div className="join">
            <input placeholder="ROOM CODE" value={joinCode} maxLength={5} onChange={(e) => setJoinCode(e.target.value.toUpperCase())} onKeyDown={(e) => e.key === "Enter" && join()} />
            <button className="big blue" disabled={!!busy} onClick={join}>Join</button>
          </div>
          {busy && <div className="note">{busy}</div>}
          {error && <div className="error">{error}</div>}
          <button className="big ghost" onClick={onBack}>&lt; Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="select">
      <Showcase index={myChar} />
      <div className="header">
        <h1>ROOM <span className="code">{net.code}</span></h1>
        <div className="sub">{net.role === "host" ? "Share this code with friends. Pick your fighter below." : "Connected. Pick your fighter and wait for the host to start."}</div>
      </div>
      <div className="panel lobby-panel">
        <h3>Mode</h3>
        <div className="row">
          {(["survival", "duel"] as Mode[]).map((m) => (
            <button key={m} className={"lvl" + (mode === m ? " on" : "")} style={{ ["--c" as any]: m === "survival" ? "#6fcf7f" : "#e8534a" }}
              disabled={net.role !== "host"} onClick={() => changeMode(m)}>{m === "survival" ? "Co-op Survival" : "Duel (PvP)"}</button>
          ))}
        </div>
        <h3>Players ({players.length}/{mode === "duel" ? 2 : 4})</h3>
        {players.map((p) => (
          <div key={p.peer} className="player">
            <i style={{ background: CHARACTERS[p.char].look.glow }} />
            <b>{p.name}{p.peer === net.myId ? " (you)" : ""}</b>
            <span>{CHARACTERS[p.char].look.name}</span>
          </div>
        ))}
        {mode === "duel" && players.length > 2 && <div className="error">Duel needs exactly 2 players.</div>}
        {error && <div className="error">{error}</div>}
        <InfoPanel index={myChar} />
      </div>
      <div className="bottom">
        <CardRow current={myChar} onPick={pick} />
        <div className="actions">
          <div className="row">
            <button className="big ghost" onClick={() => { net.close(); setNet(null); setPlayers([]); }}>&lt; LEAVE</button>
            {net.role === "host" ? (
              <button className="big gold" disabled={!canStart} onClick={start}>START</button>
            ) : (
              <button className="big ghost" disabled>Waiting...</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
