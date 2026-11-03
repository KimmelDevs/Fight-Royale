"use client";
import { useEffect, useRef, useState } from "react";
import { Game, type GameConfig, type Perk, type UiEvent } from "@/game/game";
import type { Net } from "@/game/net";

type Hud = ReturnType<Game["hud"]>;

function Bar({ v, color, right }: { v: number; color: string; right?: boolean }) {
  return (
    <div className="bar">
      <div style={{ width: `${Math.max(0, Math.min(1, v)) * 100}%`, background: color, marginLeft: right ? "auto" : 0 }} />
    </div>
  );
}

export default function GameView({ cfg, net, onExit }: { cfg: GameConfig; net: Net | null; onExit: () => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const game = useRef<Game | null>(null);
  const [hud, setHud] = useState<Hud | null>(null);
  const [banner, setBanner] = useState<{ text: string; color: string; sub?: string; key: number } | null>(null);
  const [perks, setPerks] = useState<Perk[] | null>(null);
  const [over, setOver] = useState<{ text: string; sub: string; color: string } | null>(null);
  const [lost, setLost] = useState(false);

  useEffect(() => {
    const g = new Game(canvas.current!, overlay.current!, cfg, net);
    game.current = g;
    let bannerTimer: any;
    g.onEvent = (e: UiEvent) => {
      if (e.type === "banner") {
        setBanner({ text: e.text, color: e.color, sub: e.sub, key: Math.random() });
        clearTimeout(bannerTimer);
        bannerTimer = setTimeout(() => setBanner(null), ((e.hold ?? 0) + 0.7) * 1000);
      } else if (e.type === "perks") setPerks(e.options);
      else if (e.type === "over") setOver({ text: e.text, sub: e.sub, color: e.color });
    };
    if (net) {
      const prevLeave = net.onLeave;
      net.onLeave = (p) => { prevLeave(p); if (cfg.role === "client") setLost(true); };
    }
    g.start();
    const iv = setInterval(() => setHud(g.hud()), 80);
    const key = (e: KeyboardEvent) => {
      if (e.code === "Escape") onExit();
      if (e.code === "KeyR" && g.canRestart) { setOver(null); g.restart(); }
    };
    window.addEventListener("keydown", key);
    return () => {
      clearInterval(iv);
      clearTimeout(bannerTimer);
      window.removeEventListener("keydown", key);
      g.dispose();
    };
  }, []);

  const rematch = () => { setOver(null); setPerks(null); game.current?.restart(); };
  const me = hud?.me;
  const other = hud?.other;

  return (
    <div className="game">
      <canvas ref={canvas} className="stage" />
      <div ref={overlay} className="overlay" />
      {hud && (
        <div className="hud">
          {me && (
            <div className="hp left">
              <div className="nm">{me.name}</div>
              <Bar v={me.hp / me.maxHp} color="#7fd65b" />
              <div className="guard"><Bar v={me.guard / me.maxGuard} color={me.guard / me.maxGuard > 0.25 ? "#f2c94c" : "#ff7043"} /></div>
              <div className="num">{Math.ceil(me.hp)} / {Math.round(me.maxHp)}</div>
            </div>
          )}
          {other && (
            <div className="hp right">
              <div className="nm">{other.name}{other.tag ? `  (${other.tag})` : ""}</div>
              <Bar v={other.hp / other.maxHp} color="#e8534a" right />
              <div className="guard"><Bar v={other.guard / other.maxGuard} color="#f2c94c" right /></div>
            </div>
          )}
          {hud.mode === "survival" && (
            <>
              <div className="wave">WAVE {hud.wave}<span>{hud.kills} kills  -  {hud.mobs} enemies left</span></div>
              <div className="team">
                {hud.team.map((t, i) => (
                  <div key={i} className={"mate" + (t.down ? " down" : "")}>
                    <i style={{ background: t.glow }} /><b>{t.name}</b>
                    <Bar v={t.hp / t.maxHp} color="#7fd65b" />
                  </div>
                ))}
              </div>
              {hud.boss && (
                <div className="boss"><div className="nm">{hud.boss.name}</div><Bar v={hud.boss.hp / hud.boss.maxHp} color="#ff5a4d" /></div>
              )}
            </>
          )}
          <div className="skills">
            {hud.skills.map((s) => (
              <div key={s.key} className="sk">
                <div className="icon" style={{ borderColor: me?.glow }}>
                  <div className="cool" style={{ height: `${Math.min(s.cd / Math.max(s.max, 0.01), 1) * 100}%` }} />
                  <b>{s.key.toUpperCase()}</b>
                  {s.cd > 0.05 && <em>{s.cd.toFixed(1)}</em>}
                </div>
                <span>{s.name}</span>
              </div>
            ))}
          </div>
          <div className="hint">WASD move - Space jump - Left click attack (hold = charged) - Right click block - Z X C skills - Esc leave</div>
        </div>
      )}
      {banner && (
        <div key={banner.key} className="banner">
          <div className="txt" style={{ color: banner.color }}>{banner.text}</div>
          {banner.sub && <div className="bsub">{banner.sub}</div>}
        </div>
      )}
      {perks && (
        <div className="perks">
          <h2>Choose an upgrade</h2>
          <div className="row">
            {perks.map((p, i) => (
              <button key={p.id} className="perk" onClick={() => { game.current?.choosePerk(i); setPerks(null); }}>
                <b>{p.name}</b><span>{p.desc}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      {(over || lost) && (
        <div className="over">
          <div className="txt" style={{ color: over?.color ?? "#ff7b7b" }}>{lost ? "DISCONNECTED" : over!.text}</div>
          <div className="bsub">{lost ? "The host left the match." : over!.sub}</div>
          <div className="row">
            {hud?.canRestart && !lost && <button className="big gold" onClick={rematch}>{cfg.mode === "duel" ? "Rematch" : "Try Again"}</button>}
            <button className="big ghost" onClick={onExit}>Menu</button>
          </div>
        </div>
      )}
    </div>
  );
}
