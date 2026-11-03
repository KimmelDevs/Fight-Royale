"use client";
import { useEffect, useState } from "react";
import Select from "./Select";
import Lobby from "./Lobby";
import GameView from "./GameView";
import type { GameConfig } from "@/game/game";
import type { Net } from "@/game/net";

type Screen =
  | { s: "menu" }
  | { s: "select"; purpose: "duel" | "survival" }
  | { s: "online" }
  | { s: "game"; cfg: GameConfig; net: Net | null };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ s: "menu" });
  const [name, setName] = useState("Player");

  useEffect(() => {
    try { const n = localStorage.getItem("fr-name"); if (n) setName(n); } catch {}
  }, []);
  const saveName = (n: string) => {
    setName(n);
    try { localStorage.setItem("fr-name", n); } catch {}
  };

  if (screen.s === "select") {
    return (
      <Select
        purpose={screen.purpose}
        onBack={() => setScreen({ s: "menu" })}
        onDone={(player, cpu, difficulty) => {
          const me = { peer: "local", name, char: player };
          const cfg: GameConfig = screen.purpose === "duel"
            ? { mode: "duel", role: "offline", players: [me], localPeer: "local", cpuChar: cpu, difficulty }
            : { mode: "survival", role: "offline", players: [me], localPeer: "local" };
          setScreen({ s: "game", cfg, net: null });
        }}
      />
    );
  }
  if (screen.s === "online") {
    return <Lobby name={name} onBack={() => setScreen({ s: "menu" })} onStart={(cfg, net) => setScreen({ s: "game", cfg, net })} />;
  }
  if (screen.s === "game") {
    return <GameView cfg={screen.cfg} net={screen.net} onExit={() => { screen.net?.close(); setScreen({ s: "menu" }); }} />;
  }

  return (
    <div className="menu">
      <div className="menu-card">
        <h1 className="logo">FIGHT ROYALE</h1>
        <p className="tag">Anime arena battles in your browser</p>
        <label className="name">
          <span>Your name</span>
          <input value={name} maxLength={14} onChange={(e) => saveName(e.target.value)} />
        </label>
        <button className="big gold" onClick={() => setScreen({ s: "select", purpose: "duel" })}>Duel vs CPU</button>
        <button className="big" onClick={() => setScreen({ s: "select", purpose: "survival" })}>Survival (solo)</button>
        <button className="big blue" onClick={() => setScreen({ s: "online" })}>Play Online with Friends</button>
        <div className="controls">
          <b>Controls</b>
          <span>WASD move</span><span>Space jump</span>
          <span>Left click: attack (tap) / charged attack (hold)</span>
          <span>Right click: block (block just before a hit to PARRY)</span>
          <span>Z X C skills</span><span>Esc: leave match</span>
        </div>
      </div>
    </div>
  );
}
