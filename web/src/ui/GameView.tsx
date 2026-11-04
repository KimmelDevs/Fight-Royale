"use client";
import { useEffect, useRef, useState } from "react";
import { label, type Action } from "@/game/keys";
const SKILL_ACTION: Record<string, Action> = { z: "skill1", x: "skill2", c: "skill3" };
import { Game, type GameConfig, type Perk, type UiEvent } from "@/game/game";
import type { Net } from "@/game/net";
import { account } from "@/lib/account";
import { Icon, skillIcon, charIcon } from "./icons";

type Hud = ReturnType<Game["hud"]>;

function Bar({ v, color, right }: { v: number; color: string; right?: boolean }) {
  return (
    <div className="bar">
      <div style={{ width: `${Math.max(0, Math.min(1, v)) * 100}%`, background: color, marginLeft: right ? "auto" : 0 }} />
    </div>
  );
}

export default function GameView({ cfg, net, onExit, matchId, bet, team }: {
  cfg: GameConfig; net: Net | null; onExit: () => void; matchId?: string; bet?: number; team?: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const game = useRef<Game | null>(null);
  const [hud, setHud] = useState<Hud | null>(null);
  const [banner, setBanner] = useState<{ text: string; color: string; sub?: string; key: number } | null>(null);
  const [perks, setPerks] = useState<Perk[] | null>(null);
  const [over, setOver] = useState<{ text: string; sub: string; color: string } | null>(null);
  const [lost, setLost] = useState(false);
  const [toasts, setToasts] = useState<{ id: number; text: string }[]>([]);
  const toast = (text: string) => {
    const id = Math.random();
    setToasts((t) => [...t, { id, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3000);
  };

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
      else if (e.type === "reward") {
        account.claimReward(e.reason, e.gold).then((got) => {
          if (got > 0) toast(`+${got} gold`);
          else if (account.signedIn) toast("Reward limit reached for now");
        });
      } else if (e.type === "result" && betPlaced) {
        account.reportResult(matchId!, e.winner).then(() => toast(e.winner === team ? "Bet won! Pot paid out." : "Bet settled."));
      }
    };
    // Stake the gold bet once, when the match starts.
    let betPlaced = false;
    if (matchId && bet && bet > 0 && team !== undefined) {
      account.placeBet(matchId, team, bet).then((ok) => { betPlaced = ok; toast(ok ? `Bet ${bet} gold on your team` : "Bet not placed"); });
    }
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
          {hud.plat && (
            <div className="brawl-hud">
              {hud.all.map((f, i) => (
                <div key={i} className={"bcard" + (f.me ? " me" : "") + (f.down ? " down" : "")} style={{ ["--c" as any]: f.glow }}>
                  <Icon src={charIcon(f.id)} alt={f.name} size={52} />
                  <div className="binfo">
                    <b>{f.name}{f.cpu ? " (CPU)" : ""}</b>
                    <div className="pct" style={{ color: pctColor(f.pct) }}>{f.down ? "OUT" : f.out ? "--" : `${Math.floor(f.pct)}%`}</div>
                    <div className="stocks">{Array.from({ length: 3 }, (_, k) => <i key={k} className={k < f.stocks ? "on" : ""} />)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {me && !hud.plat && (
            <div className="hp left">
              <div className="nm"><Icon src={charIcon(me.id)} alt={me.name} size={44} />{me.name}</div>
              <Bar v={me.hp / me.maxHp} color="#7fd65b" />
              <div className="guard"><Bar v={me.guard / me.maxGuard} color={me.guard / me.maxGuard > 0.25 ? "#f2c94c" : "#ff7043"} /></div>
              <div className="num">{Math.ceil(me.hp)} / {Math.round(me.maxHp)}</div>
            </div>
          )}
          {other && !hud.plat && (
            <div className="hp right">
              <div className="nm">{other.name}{other.tag ? `  (${other.tag})` : ""}<Icon src={charIcon(other.id)} alt={other.name} size={44} /></div>
              <Bar v={other.hp / other.maxHp} color="#e8534a" right />
              <div className="guard"><Bar v={other.guard / other.maxGuard} color="#f2c94c" right /></div>
            </div>
          )}
          {hud.mode === "team" && (
            <div className="team foes">
              {hud.foes.map((t, i) => (
                <div key={i} className={"mate" + (t.down ? " down" : "")}>
                  <Icon src={charIcon(t.id)} alt={t.name} size={26} fallback={<i style={{ background: t.glow }} />} /><b>{t.name}</b>
                  <Bar v={t.hp / t.maxHp} color="#e8534a" />
                </div>
              ))}
            </div>
          )}
          {hud.mode === "team" && (
            <div className="team">
              {hud.team.map((t, i) => (
                <div key={i} className={"mate" + (t.down ? " down" : "")}>
                  <Icon src={charIcon(t.id)} alt={t.name} size={26} fallback={<i style={{ background: t.glow }} />} /><b>{t.name}</b>
                  <Bar v={t.hp / t.maxHp} color="#7fd65b" />
                </div>
              ))}
            </div>
          )}
          {hud.mode === "survival" && (
            <>
              <div className="wave">WAVE {hud.wave}<span>{hud.kills} kills  -  {hud.mobs} enemies left</span></div>
              <div className="team">
                {hud.team.map((t, i) => (
                  <div key={i} className={"mate" + (t.down ? " down" : "")}>
                    <Icon src={charIcon(t.id)} alt={t.name} size={26} fallback={<i style={{ background: t.glow }} />} /><b>{t.name}</b>
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
            {hud.dash && (
              <div className={"sk atk" + (hud.dash.t > 0.05 ? " locked" : "")}>
                <div className="icon" style={{ borderColor: me?.glow }}>
                  <div className="atk-glyph dash-glyph">DASH</div>
                  <div className="cool" style={{ height: `${Math.min(hud.dash.t / hud.dash.max, 1) * 100}%` }} />
                  <b>2x</b>
                  {hud.dash.t > 0.05 && <em>{hud.dash.t.toFixed(1)}</em>}
                </div>
                <span>Dash</span>
              </div>
            )}
            {hud.atkLock && (
              <div className={"sk atk" + (hud.atkLock.t > 0.05 ? " locked" : "")}>
                <div className="icon" style={{ borderColor: me?.glow }}>
                  <div className="atk-glyph">ATK</div>
                  <div className="cool" style={{ height: `${Math.min(hud.atkLock.t / hud.atkLock.max, 1) * 100}%` }} />
                  <b>{label("attack").replace(" click", "")}</b>
                  {hud.atkLock.t > 0.05 && <em>{hud.atkLock.t.toFixed(1)}</em>}
                </div>
                <span>{hud.atkLock.t > 0.05 ? "Reloading" : "Attack"}</span>
              </div>
            )}
            {hud.skills.map((s) => (
              <div key={s.key} className="sk">
                <div className="icon" style={{ borderColor: me?.glow }}>
                  <Icon src={skillIcon(hud.kit, hud.element, s.id)} alt={s.name} size={60} />
                  <div className="cool" style={{ height: `${Math.min(s.cd / Math.max(s.max, 0.01), 1) * 100}%` }} />
                  <b>{label(SKILL_ACTION[s.key])}</b>
                  {s.cd > 0.05 && <em>{s.cd.toFixed(1)}</em>}
                </div>
                <span>{s.name}</span>
              </div>
            ))}
          </div>
          <div className="hint">{hud?.plat
            ? `${label("left")}/${label("right")} move - ${label("up")} or ${label("jump")} jump (twice to double jump) - ${label("down")} drop / fast fall - ${label("attack")} attack (hold = charged) - ${label("block")} shield - ${label("skill1")} ${label("skill2")} ${label("skill3")} skills - Esc leave`
            : `${label("up")}${label("left")}${label("down")}${label("right")} move - ${label("jump")} jump - ${label("attack")} attack (hold = charged) - ${label("block")} block - ${label("skill1")} ${label("skill2")} ${label("skill3")} skills - Esc leave`}</div>
        </div>
      )}
      <div className="toasts">{toasts.map((t) => <div key={t.id} className="toast">{t.text}</div>)}</div>
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
            {hud?.canRestart && !lost && <button className="big gold" onClick={rematch}>{cfg.mode === "survival" ? "Try Again" : "Rematch"}</button>}
            <button className="big ghost" onClick={onExit}>Menu</button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Damage % turns from white through yellow and orange to deep red as it climbs. */
function pctColor(p: number) {
  const t = Math.min(p / 150, 1);
  const r = 255, g = Math.round(255 - 200 * t), b = Math.round(255 - 235 * Math.min(t * 1.6, 1));
  return `rgb(${r},${g},${b})`;
}
