// FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1
// FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1
"use client";
import { STATUS, type StatusKind } from "@/game/status";
import { Sound } from "@/game/sound";
import { applyResult, type RankChange } from "@/game/rank";
import { RankBadge } from "./Ranked";
import { useEffect, useRef, useState } from "react";
import { label, type Action } from "@/game/keys";
const SKILL_ACTION: Record<string, Action> = { z: "skill1", x: "skill2", c: "skill3", v: "skill4" };
import { Game, type GameConfig, type Perk, type UiEvent, type MatchHighlights } from "@/game/game";
import { CHARACTERS } from "@/game/roster";
import { Preview } from "@/game/preview";
import type { Net } from "@/game/net";
import { account } from "@/lib/account";
import { Icon, skillIcon, charIcon } from "./icons";

type Hud = ReturnType<Game["hud"]>;

// A second, lightweight 3D camera for the winning fighter's signature celebration.
function WinnerPreview({ index }: { index: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const view = new Preview(canvas.current!);
    view.setMode("victory");
    view.setLook(CHARACTERS[index].look);
    return () => view.dispose();
  }, [index]);
  return <canvas ref={canvas} className="victory-character-canvas" />;
}

function StatusChips({ list, right }: { list?: StatusKind[]; right?: boolean }) {
  if (!list?.length) return null;
  return (
    <div className={"status-chips" + (right ? " right" : "")}>
      {list.map((k) => <span key={k} style={{ borderColor: STATUS[k].color, color: STATUS[k].color }}>{STATUS[k].label}</span>)}
    </div>
  );
}

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
  const [highlights, setHighlights] = useState<MatchHighlights | null>(null);
  const [winnerChar, setWinnerChar] = useState<number | null>(null);
  const [rankChange, setRankChange] = useState<RankChange | null>(null);
  const rankDone = useRef(false);
  /** Ranked: apply the result once per match. */
  const rankResult = (won: boolean) => {
    if (!cfg.ranked || rankDone.current) return;
    rankDone.current = true;
    setRankChange(applyResult(won));
  };
  const [lost, setLost] = useState(false);
  const [paused, setPausedState] = useState(false);
  const setPaused = (p: boolean) => { setPausedState(p); if (game.current) game.current.paused = p; };
  const [toasts, setToasts] = useState<{ id: number; text: string }[]>([]);
  const toast = (text: string) => {
    const id = Math.random();
    setToasts((t) => [...t, { id, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3000);
  };

  useEffect(() => { Sound.setMusic("battle"); return () => Sound.setMusic("menu"); }, []);

  useEffect(() => {
    const g = new Game(canvas.current!, overlay.current!, cfg, net);
    game.current = g;
    let bannerTimer: any;
    g.onEvent = (e: UiEvent) => {
      if (e.type === "banner") {
        if (e.text === "READY") Sound.play("ready", 0.8, 0);
        else if (e.text === "FIGHT!") Sound.play("fight", 0.9, 0);
        else if (e.text.startsWith("WAVE") || e.text.startsWith("BOSS")) Sound.play("wave", 0.8, 0);
        setBanner({ text: e.text, color: e.color, sub: e.sub, key: Math.random() });
        clearTimeout(bannerTimer);
        bannerTimer = setTimeout(() => setBanner(null), ((e.hold ?? 0) + 0.7) * 1000);
      } else if (e.type === "perks") setPerks(e.options);
      else if (e.type === "over") {
        setOver({ text: e.text, sub: e.sub, color: e.color });
        Sound.play(/VICTORY|WIN|CLEAR/i.test(e.text) ? "victory" : "defeat", 0.9, 0);
      }
      else if (e.type === "reward") {
        account.claimReward(e.reason, e.gold).then((got) => {
          if (got > 0) { toast(`+${got} gold`); Sound.play("coins", 0.7, 0); }
          else if (account.signedIn) toast("Reward limit reached for now");
        });
      } else if (e.type === "highlights") {
        setHighlights(e.summary);
      } else if (e.type === "result") {
        const winningFighter = g.fighters.find((f) => f.team === e.winner && !f.isDown())
          ?? g.fighters.find((f) => f.team === e.winner);
        setWinnerChar(winningFighter?.charIndex ?? null);
        if (cfg.ranked) rankResult(e.winner === (g.local?.team ?? 0));
        if (betPlaced) account.reportResult(matchId!, e.winner).then(() => toast(e.winner === team ? "Bet won! Pot paid out." : "Bet settled."));
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
      if (e.code === "Escape") { e.preventDefault(); const p = !g.paused; g.paused = p; setPausedState(p); }
      if (e.code === "KeyR" && g.canRestart) { setOver(null); setHighlights(null); setWinnerChar(null); setRankChange(null); rankDone.current = false; g.restart(); }
    };
    window.addEventListener("keydown", key);
    return () => {
      clearInterval(iv);
      clearTimeout(bannerTimer);
      window.removeEventListener("keydown", key);
      g.dispose();
    };
  }, []);

  const rematch = () => { setOver(null); setHighlights(null); setWinnerChar(null); setPerks(null); setRankChange(null); rankDone.current = false; game.current?.restart(); };
  // FIGHT_ROYALE_CPU_VS_CPU_SPECTATOR_V1: CPU vs CPU uses a two-sided HUD without local input controls.
  const me = hud?.me;
  const other = hud?.other;

  return (
    <div className="game">
      <canvas ref={canvas} className="stage" />
      <div ref={overlay} className="overlay" />
      {hud && (
        <div className="hud">
          {hud.mode !== "survival" && (
            <div className="match-score" style={{
              position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)",
              display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
              padding: "7px 18px", borderRadius: 12, color: "#ffffff",
              background: "rgba(10, 19, 36, 0.82)", border: "1px solid rgba(255,255,255,0.25)",
              zIndex: 5, pointerEvents: "none", whiteSpace: "nowrap", textShadow: "0 1px 2px #000",
            }}>
              <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.16em", color: "#ffdf8d" }}>{cfg.spectator ? "CPU VS CPU · " : ""}{hud.roundLabel} · FIRST TO 2</span>
              <div style={{ display: "flex", alignItems: "center", gap: 14, fontWeight: 800 }}>
                <span style={{ fontSize: 10, color: "#8ccfff" }}>{cfg.spectator ? "CPU 1" : hud.mode === "team" ? "BLUE" : "P1"}</span>
                <span style={{ fontSize: 21, fontVariantNumeric: "tabular-nums" }}>{hud.matchWins[0]} - {hud.matchWins[1]}</span>
                <span style={{ fontSize: 10, color: "#ff9a9a" }}>{cfg.spectator ? "CPU 2" : hud.mode === "team" ? "RED" : "P2"}</span>
              </div>
            </div>
          )}
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
              {/* ZAREK_WHITE_COUNTER_V1 */}
              {me.id === "zarek" && (
                <div style={{ display: "flex", alignItems: "center", gap: 7,
                  marginTop: 5, color: "#ffffff", textShadow: "0 1px 3px rgba(0, 0, 0, 0.95)", fontSize: 11 }}>
                  <Icon src="/icons/skills/glaive-passive.webp" alt="Clash Counter" size={25}
                    fallback={<span style={{ fontSize: 19 }}>⚡</span>} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800 }}>
                      <span>CLASH COUNTER</span><span>{me.clashMomentum}</span>
                    </div>
                    <div style={{ fontSize: 10, opacity: .88 }}>
                      BASIC SPEED ×{Math.min(2, 1 + Math.min(5, me.clashMomentum) * .2).toFixed(1)}
                    </div>
                  </div>
                </div>
              )}
              <div className="num">{Math.ceil(me.hp)} / {Math.round(me.maxHp)}</div>
              <StatusChips list={me.status} />
              {me.id === "veyr" && (
                <div style={{ marginTop: 7, fontSize: 11, color: "#ff9cb6" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <b>{me.bloodFrenzyT > 0 ? "BLOOD FRENZY" : "BLOODLUST"}</b>
                    <span>{me.bloodFrenzyT > 0 ? `${me.bloodFrenzyT.toFixed(1)}s` : `${me.bloodlust}/100`}</span>
                  </div>
                  {/* VEYR_BLOODLUST_CARRION_V7: display the actual Bloodlust meter as Frenzy counts down. */}
                  <Bar v={me.bloodlust / 100} color="#d93965" />
                  {me.bloodFestivalT > 0 && (
                    <div style={{ color: "#ffcfda", marginTop: 5, fontWeight: 800 }}>
                      BLOOD FESTIVAL {me.bloodFestivalT.toFixed(1)}s · STUN IMMUNE · SKILLS LOCKED
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          {other && !hud.plat && (
            <div className="hp right">
              <div className="nm">{other.name}{other.tag ? `  (${other.tag})` : ""}<Icon src={charIcon(other.id)} alt={other.name} size={44} /></div>
              <Bar v={other.hp / other.maxHp} color="#e8534a" right />
              <div className="guard"><Bar v={other.guard / other.maxGuard} color="#f2c94c" right /></div>
              <StatusChips list={other.status} right />
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
          {!cfg.spectator && <div className="skills">
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
                  <Icon src={hud.kit === "chainblade" && (hud.me?.chainBindT ?? 0) > 0 &&
                    (hud.me?.chainBindKind === "x" ? s.key === "x" : (s.key === "z" || s.key === "x"))
                      ? `/icons/skills/kaizen-${s.key === "z" ? "forward" : "backward"}.webp`
                      : skillIcon(hud.kit, hud.element, s.id)} alt={s.name} size={60} /> {/* KAIZEN_PREDATOR_HOOK_V9 */}
                  <div className="cool" style={{ height: `${Math.min(s.cd / Math.max(s.max, 0.01), 1) * 100}%` }} />
                  <b>{label(SKILL_ACTION[s.key])}</b>
                  {s.cd > 0.05 && <em>{s.cd.toFixed(1)}</em>}
                </div>
                <span>{s.name}</span>
              </div>
            ))}
          </div>}
          {/* AIR_COMBAT_V1: show both keyboard chords without changing keybindings. */}
          {!cfg.spectator && <div className="hint">{hud?.plat
            ? `${label("left")}/${label("right")} move - ${label("up")} or ${label("jump")} jump (twice to double jump) - ${label("down")} drop / fast fall - ${label("attack")} attack (hold = charged) - ${label("block")} shield - ${label("skill1")} ${label("skill2")} ${label("skill3")} skills${hud.skills.some(s => s.key === "v") ? ` - ${label("skill4")} bonus V` : ""} - Space+${label("attack")} anti-air / air combo - tap ${label("jump")} after launcher to chase - hold air attack for heavy - air ${label("block")} block/recover - Esc pause`
            : `${label("up")}${label("left")}${label("down")}${label("right")} move - ${label("jump")} jump - ${label("attack")} attack (hold = charged) - ${label("block")} block - ${label("skill1")} ${label("skill2")} ${label("skill3")} skills${hud.skills.some(s => s.key === "v") ? ` - ${label("skill4")} bonus V` : ""} - Space+${label("attack")} anti-air / air combo - tap ${label("jump")} after launcher to chase - hold air attack for heavy - air ${label("block")} block/recover - Esc pause`}</div>}
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
      {paused && !over && !lost && (
        <div className="over pause">
          <div className="txt" style={{ color: "#ffe08a" }}>PAUSED</div>
          <div className="bsub">{cfg.role === "offline" ? "The match is frozen." : "Online matches keep running while this menu is open."}</div>
          <div className="row">
            <button className="big gold" onClick={() => setPaused(false)}>Resume</button>
            <button className="big ghost" onClick={onExit}>Leave match</button>
          </div>
          <div className="bsub small">Esc: resume</div>
        </div>
      )}
      {(over || lost) && (
        <div className="over">
          <div className="txt" style={{ color: over?.color ?? "#ff7b7b" }}>{lost ? "DISCONNECTED" : over!.text}</div>
          <div className="bsub">{lost ? "The host left the match." : over!.sub}</div>
          {!lost && (winnerChar !== null || highlights) && (
            <div className="match-highlights-layout">
              {winnerChar !== null && <div className="victory-character">
                <WinnerPreview index={winnerChar} />
                <b>{CHARACTERS[winnerChar]?.look.name ?? "Winner"}</b>
                <span>VICTORY POSE</span>
              </div>}
              {highlights && <div className="match-highlights">
                <div className="highlight-heading">MATCH HIGHLIGHTS</div>
                <div className="highlight-finisher">
                  <span>FINISHING MOVE</span>
                  <b>{highlights.finisher ? `${highlights.finisher.fighter} · ${highlights.finisher.move}` : "Final blow / ring-out"}</b>
                  {highlights.finisher && <em>{highlights.finisher.damage} damage</em>}
                </div>
                <div className="highlight-fighters">
                  {highlights.fighters.map((f, i) => <div className="highlight-fighter" key={`${f.peer}-${f.team}-${i}`}>
                    <strong style={{ color: f.glow }}>{f.name}{!cfg.spectator && f.peer === cfg.localPeer ? " · YOU" : ""}</strong>
                    <div><span>Biggest combo</span><b>{f.bestCombo} hits</b></div>
                    <div><span>Successful clashes</span><b>{f.clashes}</b></div>
                    <div><span>Perfect dodges</span><b>{f.perfectDodges}</b></div>
                    <div><span>Damage dealt</span><b>{f.totalDamage}</b></div>
                  </div>)}
                </div>
              </div>}
            </div>
          )}
          {rankChange && (
            <div className="rank-result">
              <RankBadge st={rankChange.after} size={64} />
              <div className={"delta" + (rankChange.delta > 0 ? " up" : rankChange.delta < 0 ? " down" : "")}>
                {rankChange.delta > 0 ? `+${rankChange.delta} star${rankChange.delta > 1 ? "s" : ""}` : rankChange.delta < 0 ? "-1 star" : "No change"}
              </div>
              {rankChange.note && <div className="small">{rankChange.note}</div>}
            </div>
          )}
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
