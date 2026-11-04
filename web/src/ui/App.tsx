"use client";
import { useEffect, useState } from "react";
import Select from "./Select";
import Lobby from "./Lobby";
import GameView from "./GameView";
import AccountScreen, { Wallet } from "./Account";
import Shop from "./Shop";
import Settings, { useBindings } from "./Settings";
import { label } from "@/game/keys";
import { CHARACTERS } from "@/game/roster";
import { SHOW_BRAWL, type GameConfig } from "@/game/game";
import type { Net } from "@/game/net";
import { account, useAccount } from "@/lib/account";

type Screen =
  | { s: "menu" }
  | { s: "select"; purpose: "duel" | "brawl" | "survival" | "team" }
  | { s: "online" }
  | { s: "account" }
  | { s: "settings" }
  | { s: "shop"; tab?: "fighters" | "skills" | "emblems" | "diamonds" }
  | { s: "game"; cfg: GameConfig; net: Net | null; matchId?: string; bet?: number; team?: number };

export default function App() {
  const acc = useAccount();
  useBindings();
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
        onDone={(player, cpu, difficulty, teamSize) => {
          const me = { peer: "local", name, char: player, ...account.matchKit(player) };
          if (screen.purpose === "team") {
            // You + CPU allies on Blue vs a CPU team on Red; fighters drawn without repeats when possible.
            const n = teamSize ?? 3;
            const pool = CHARACTERS.map((_, i) => i).filter((i) => i !== player).sort(() => Math.random() - 0.5);
            const slots = [{ ...me, team: 0 }];
            for (let i = 0; i < n * 2 - 1; i++) {
              const char = pool[i % pool.length];
              slots.push({ peer: `cpu-${i + 1}`, name: CHARACTERS[char].look.name, char, team: i < n - 1 ? 0 : 1 } as any);
            }
            setScreen({ s: "game", cfg: { mode: "team", role: "offline", players: slots, localPeer: "local", difficulty }, net: null });
            return;
          }
          const cfg: GameConfig = screen.purpose !== "survival"
            ? { mode: screen.purpose, role: "offline", players: [me], localPeer: "local", cpuChar: cpu, difficulty }
            : { mode: "survival", role: "offline", players: [me], localPeer: "local" };
          setScreen({ s: "game", cfg, net: null });
        }}
      />
    );
  }
  if (screen.s === "settings") return <Settings onBack={toMenu} />;
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
        {SHOW_BRAWL && <button className="big brawl" onClick={() => setScreen({ s: "select", purpose: "brawl" })}>Platform Brawl vs CPU</button>}
        <button className="big blue" onClick={() => setScreen({ s: "select", purpose: "team" })}>Team Battle vs CPU (2v2 - 4v4)</button>
        <button className="big" onClick={() => setScreen({ s: "select", purpose: "survival" })}>Survival (solo)</button>
        <button className="big blue" onClick={() => setScreen({ s: "online" })}>Play Online with Friends</button>
        <div className="row two">
          <button className="big ghost" onClick={() => setScreen({ s: "shop" })}>Shop</button>
          <button className="big ghost" onClick={() => setScreen({ s: "shop", tab: "emblems" })}>Emblems</button>
        </div>
        <button className="big ghost" onClick={() => setScreen({ s: "settings" })}>Settings: Controls</button>
        <div className="controls">
          <b>Controls</b>
          <span>{label("up")} {label("left")} {label("down")} {label("right")} move</span><span>{label("jump")} jump</span><span>Double-tap a direction: dash (3 s cooldown)</span>
          <span>{label("attack")}: attack (tap) / charged attack (hold)</span>
          <span>{label("block")}: block (block just before a hit to PARRY)</span>
          <span>{label("skill1")} {label("skill2")} {label("skill3")} skills</span><span>Esc: pause</span>
          <span>Win a 1v1: +250 gold. Survival: gold for every mob.</span>
        </div>
        <p className="credits">3D characters made with VRoid Studio. Raven model by Fruit.</p>
      </div>
    </div>
  );
}
