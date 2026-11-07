// FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1
"use client";
import { useEffect, useRef, useState } from "react";
import { Net } from "@/game/net";
import { CHARACTERS } from "@/game/roster";
import { SHOW_BRAWL, type GameConfig, type PlayerSlot } from "@/game/game";
import { MAX_BET } from "@/game/economy";
import { account, useAccount } from "@/lib/account";
import { CardRow, EmblemPicker, InfoPanel, Showcase } from "./Select";
import { Icon, charIcon } from "./icons";

type Mode = "survival" | "duel" | "brawl" | "team";
type LobbySlot = PlayerSlot & { bet?: number; ready?: boolean };

const MAX_PLAYERS: Record<Mode, number> = { survival: 4, duel: 2, brawl: 2, team: 8 };
const TEAM_COLORS = ["#5fa8ff", "#ff6b6b"];

export default function Lobby({ name, onBack, onStart, onShop }: {
  name: string;
  onBack: () => void;
  onShop: () => void;
  onStart: (cfg: GameConfig, net: Net, matchId?: string, bet?: number, team?: number) => void;
}) {
  const acc = useAccount();
  const [net, setNet] = useState<Net | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [players, setPlayers] = useState<LobbySlot[]>([]);
  const [mode, setMode] = useState<Mode>("survival");
  const firstOwned = Math.max(0, CHARACTERS.findIndex((c) => account.owns(c.id)));
  const [myChar, setMyChar] = useState(firstOwned);
  const [bet, setBet] = useState(0);
  const started = useRef(false);
  const netRef = useRef<Net | null>(null);
  const playersRef = useRef<LobbySlot[]>([]);
  const modeRef = useRef<Mode>("survival");
  playersRef.current = players;
  modeRef.current = mode;

  // Leave the room if the lobby closes without starting a match.
  useEffect(() => () => { if (!started.current) netRef.current?.close(); }, []);

  const kit = (char: number) => account.matchKit(char);

  const host = async () => {
    setBusy("Creating room...");
    setError("");
    try {
      const n = await Net.host();
      netRef.current = n;
      setPlayers([{ peer: n.myId, name, char: myChar, team: 0, ...kit(myChar) }]);
      const sync = (list: LobbySlot[]) => { setPlayers(list); n.broadcast({ t: "lobby", players: list, mode: modeRef.current }); };
      const update = (from: string, patch: Partial<LobbySlot>) =>
        sync(playersRef.current.map((p) => (p.peer === from ? { ...p, ...patch } : p)));
      n.onMessage = (from, msg) => {
        if (msg.t === "hello") {
          const list = [...playersRef.current];
          if (list.length >= 8 || list.some((p) => p.peer === from)) return;
          const t0 = list.filter((p) => p.team === 0).length, t1 = list.length - t0;
          list.push({ peer: from, name: String(msg.name).slice(0, 16), char: msg.char ?? 0, team: t0 <= t1 ? 0 : 1, loadout: msg.loadout, emblem: msg.emblem, bonusSkillUnlocked: msg.bonusSkillUnlocked === true });
          sync(list);
        } else if (msg.t === "pick") update(from, { char: msg.char, loadout: msg.loadout, emblem: msg.emblem, bonusSkillUnlocked: msg.bonusSkillUnlocked === true });
        else if (msg.t === "team") update(from, { team: msg.team === 1 ? 1 : 0 });
        else if (msg.t === "bet") update(from, { bet: Math.max(0, Math.min(MAX_BET, Math.floor(msg.amount) || 0)) });
        else if (msg.t === "ready") update(from, { ready: !!msg.v });
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
        else if (msg.t === "busy") { setError(msg.reason ?? "That match is already running."); }
        else if (msg.t === "start") {
          started.current = true;
          const me = (msg.cfg.players as LobbySlot[]).find((p) => p.peer === n.myId);
          onStart({ ...msg.cfg, role: "client", localPeer: n.myId, late: !!msg.late }, n, msg.matchId, me?.bet, me?.team);
        }
      };
      n.onLeave = () => { setError("The host closed the room."); setNet(null); };
      n.send({ t: "hello", name, char: myChar, ...kit(myChar) });
      setNet(n);
    } catch (e: any) {
      setError(e.message ?? String(e));
    }
    setBusy("");
  };

  const patchMe = (patch: Partial<LobbySlot>, msg: { t: string; [k: string]: any }) => {
    if (!net) return;
    if (net.role === "host") {
      const list = players.map((p) => (p.peer === net.myId ? { ...p, ...patch } : p));
      setPlayers(list);
      net.broadcast({ t: "lobby", players: list, mode });
    } else net.send(msg);
  };

  const pick = (i: number) => {
    setMyChar(i);
    if (!account.owns(CHARACTERS[i].id)) return;
    patchMe({ char: i, ...kit(i) }, { t: "pick", char: i, ...kit(i) });
  };
  const pickTeam = (t: number) => patchMe({ team: t }, { t: "team", team: t });
  const changeBet = (v: number) => {
    const amount = Math.max(0, Math.min(MAX_BET, acc.profile.gold, Math.floor(v) || 0));
    setBet(amount);
    patchMe({ bet: amount }, { t: "bet", amount });
  };

  const changeMode = (m: Mode) => {
    setMode(m);
    net?.broadcast({ t: "lobby", players, mode: m });
  };

  const teamCounts = [0, 1].map((t) => players.filter((p) => p.team === t).length);
  const valid = mode === "survival" ? players.length >= 1 && players.length <= 4
    : mode === "duel" || mode === "brawl" ? players.length === 2
    : players.length >= 2 && teamCounts[0] >= 1 && teamCounts[1] >= 1 && Math.max(...teamCounts) <= 4;
  const notReady = players.filter((p) => p.peer !== net?.myId && !p.ready);
  const canStart = net?.role === "host" && valid && notReady.length === 0;
  const me = players.find((p) => p.peer === net?.myId);
  const toggleReady = () => patchMe({ ready: !me?.ready }, { t: "ready", v: !me?.ready });
  const myCharLocked = !acc.owns(CHARACTERS[myChar].id);

  const start = () => {
    if (!net || !canStart) return;
    const matchId = `${net.code}-${Date.now().toString(36)}`;
    const slots: PlayerSlot[] = players.map(({ bet: _b, ready: _r, ...p }, i) => ({ ...p, team: mode === "team" ? p.team ?? i % 2 : undefined }));
    net.broadcast({ t: "start", cfg: { mode, players: players.map((p, i) => ({ ...p, team: slots[i].team })) }, matchId });
    started.current = true;
    onStart({ mode, role: "host", players: slots, localPeer: net.myId }, net, matchId, me?.bet, me?.team);
  };

  if (!net) {
    return (
      <div className="menu">
        <div className="menu-card">
          <h1 className="logo small">PLAY ONLINE</h1>
          <p className="tag">Co-op survival (up to 4), a 1v1 duel, or team battles from 2v2 to 4v4. Peer-to-peer, no server needed. You can join a survival run that has already started.</p>
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
          {(["survival", "duel", "brawl", "team"] as Mode[]).filter((m) => SHOW_BRAWL || m !== "brawl").map((m) => (
            <button key={m} className={"lvl" + (mode === m ? " on" : "")} style={{ ["--c" as any]: m === "survival" ? "#6fcf7f" : m === "duel" ? "#e8534a" : m === "brawl" ? "#ffb347" : "#5fa8ff" }}
              disabled={net.role !== "host"} onClick={() => changeMode(m)}>{m === "survival" ? "Co-op Survival" : m === "duel" ? "Duel (1v1)" : m === "brawl" ? "Platform Brawl" : "Team Battle"}</button>
          ))}
        </div>
        {mode === "team" && (
          <>
            <h3>Your team</h3>
            <div className="row">
              {[0, 1].map((t) => (
                <button key={t} className={"lvl" + (me?.team === t ? " on" : "")} style={{ ["--c" as any]: TEAM_COLORS[t] }} onClick={() => pickTeam(t)}>
                  {t === 0 ? "Blue" : "Red"} ({teamCounts[t]}/4)
                </button>
              ))}
            </div>
            <h3>Gold bet</h3>
            {acc.signedIn ? (
              <div className="row bet">
                <input type="number" min={0} max={MAX_BET} step={50} value={bet} onChange={(e) => changeBet(+e.target.value)} />
                <span className="small">Winners split the pot. You have {acc.profile.gold} gold.</span>
              </div>
            ) : <div className="small">Sign in to bet gold on team battles.</div>}
          </>
        )}
        <h3>Your emblem</h3>
        <EmblemPicker compact onChange={() => patchMe({ ...kit(myChar) }, { t: "pick", char: myChar, ...kit(myChar) })} />
        <h3>Players ({players.length}/{MAX_PLAYERS[mode]})</h3>
        {players.map((p) => (
          <div key={p.peer} className="player" style={mode === "team" ? { borderLeft: `4px solid ${TEAM_COLORS[p.team ?? 0]}` } : {}}>
            <Icon src={charIcon(CHARACTERS[p.char].id)} alt={CHARACTERS[p.char].look.name} size={30} fallback={<i style={{ background: CHARACTERS[p.char].look.glow }} />} />
            <b>{p.name}{p.peer === net.myId ? " (you)" : ""}</b>
            {p.peer === players[0]?.peer ? <em className="tagchip host">HOST</em>
              : <em className={"tagchip" + (p.ready ? " ready" : "")}>{p.ready ? "READY" : "not ready"}</em>}
            {mode === "team" && !!p.bet && <em className="betchip">{p.bet} gold</em>}
            <span>{CHARACTERS[p.char].look.name}</span>
          </div>
        ))}
        {valid && notReady.length > 0 && net.role === "host" && <div className="note">Waiting for {notReady.map((p) => p.name).join(", ")} to press Ready.</div>}
        {!valid && <div className="error">{mode === "duel" || mode === "brawl" ? "Duel and Brawl need exactly 2 players." : mode === "team" ? "Team battle needs at least 1 player per team, max 4 per team." : "Survival is up to 4 players."}</div>}
        {error && <div className="error">{error}</div>}
        <InfoPanel index={myChar} editable />
      </div>
      <div className="bottom">
        <CardRow current={myChar} onPick={pick} showLocks />
        <div className="actions">
          <div className="row">
            <button className="big ghost" onClick={() => { net.close(); setNet(null); setPlayers([]); }}>&lt; LEAVE</button>
            {myCharLocked ? <button className="big gold" onClick={onShop}>UNLOCK IN SHOP</button>
              : net.role === "host" ? <button className="big gold" disabled={!canStart} onClick={start}>START</button>
              : <button className={"big " + (me?.ready ? "ghost" : "gold")} onClick={toggleReady}>{me?.ready ? "NOT READY" : "READY"}</button>}
          </div>
        </div>
      </div>
    </div>
  );
}
