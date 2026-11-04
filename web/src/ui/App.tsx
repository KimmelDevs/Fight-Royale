"use client";
import { useEffect, useState } from "react";
import Select from "./Select";
import Lobby from "./Lobby";
import GameView from "./GameView";
import AccountScreen, { Wallet } from "./Account";
import Shop from "./Shop";
import type { GameConfig } from "@/game/game";
import type { Net } from "@/game/net";
import { account, useAccount } from "@/lib/account";

type Screen =
  | { s: "menu" }
  | { s: "select"; purpose: "duel" | "brawl" | "survival" }
  | { s: "online" }
  | { s: "account" }
  | { s: "shop"; tab?: "fighters" | "skills" | "emblems" | "diamonds" }
  | { s: "game"; cfg: GameConfig; net: Net | null; matchId?: string; bet?: number; team?: number };

export default function App() {
  const acc = useAccount();
  const [screen, setScreen] = useState<Screen>({ s: "menu" });
  const [guestName, setGuestName] = useState("Player");

  useEffect(() => {
    try { const n = localStorage.getItem("fr-name"); if (n) setGuestName(n); } catch {}
    const q = new URLSearchParams(window.location.search).get("purchase");
    if (q) { setScreen({ s: "shop", tab: "diamonds" }); account.refresh(); window.history.replaceState(null, "", "/"); }
  }, []);
  const saveName = (n: string) => {
    setGuestName(n);
    try { localStorage.setItem("fr-name", n); } catch {}
  };
  const name = acc.signedIn ? acc.profile.username : guestName;
  const toMenu = () => setScreen({ s: "menu" });

  if (screen.s === "select") {
    return (
      <Select
        purpose={screen.purpose}
        onBack={toMenu}
        onShop={() => setScreen({ s: "shop" })}
        onDone={(player, cpu, difficulty) => {
          const me = { peer: "local", name, char: player, ...account.matchKit(player) };
          const cfg: GameConfig = screen.purpose !== "survival"
            ? { mode: screen.purpose, role: "offline", players: [me], localPeer: "local", cpuChar: cpu, difficulty }
            : { mode: "survival", role: "offline", players: [me], localPeer: "local" };
          setScreen({ s: "game", cfg, net: null });
        }}
      />
    );
  }
  if (screen.s === "online") {
    return <Lobby name={name} onBack={toMenu} onShop={() => setScreen({ s: "shop" })}
      onStart={(cfg, net, matchId, bet, team) => setScreen({ s: "game", cfg, net, matchId, bet, team })} />;
  }
  if (screen.s === "account") return <AccountScreen onBack={toMenu} />;
  if (screen.s === "shop") return <Shop start={screen.tab} onBack={toMenu} onAccount={() => setScreen({ s: "account" })} />;
  if (screen.s === "game") {
    return <GameView cfg={screen.cfg} net={screen.net} matchId={screen.matchId} bet={screen.bet} team={screen.team}
      onExit={() => { screen.net?.close(); toMenu(); }} />;
  }

  return (
    <div className="menu">
      <div className="menu-card">
        <Wallet onAccount={() => setScreen({ s: "account" })} />
        <h1 className="logo">FIGHT ROYALE</h1>
        <p className="tag">Anime arena battles in your browser</p>
        {!acc.signedIn && (
          <label className="name">
            <span>Guest name</span>
            <input value={guestName} maxLength={14} onChange={(e) => saveName(e.target.value)} />
          </label>
        )}
        <button className="big gold" onClick={() => setScreen({ s: "select", purpose: "duel" })}>Duel vs CPU</button>
        <button className="big brawl" onClick={() => setScreen({ s: "select", purpose: "brawl" })}>Platform Brawl vs CPU</button>
        <button className="big" onClick={() => setScreen({ s: "select", purpose: "survival" })}>Survival (solo)</button>
        <button className="big blue" onClick={() => setScreen({ s: "online" })}>Play Online with Friends</button>
        <div className="row two">
          <button className="big ghost" onClick={() => setScreen({ s: "shop" })}>Shop</button>
          <button className="big ghost" onClick={() => setScreen({ s: "shop", tab: "emblems" })}>Emblems</button>
        </div>
        <div className="controls">
          <b>Controls</b>
          <span>WASD move</span><span>Space jump</span>
          <span>Left click: attack (tap) / charged attack (hold)</span>
          <span>Right click: block (block just before a hit to PARRY)</span>
          <span>Z X C skills</span><span>Esc: leave match</span>
          <span>Win a 1v1: +250 gold. Survival: gold for every mob.</span>
        </div>
      </div>
    </div>
  );
}
