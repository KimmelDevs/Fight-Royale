// FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1
"use client";
import { useEffect, useRef, useState } from "react";
import { CHARACTERS } from "@/game/roster";
import * as Kits from "@/game/kits";
import { LEVELS } from "@/game/ai";
import { Preview } from "@/game/preview";
import { account, useAccount } from "@/lib/account";
import { CHARACTER_PRICE, EMBLEMS, EMBLEM_MAX } from "@/game/economy";
import { Icon, skillIcon, charIcon, emblemIcon } from "./icons";

const CONTROLS: Record<string, string> = {
  knight: "Tap: 3-hit sword combo  -  Hold: charged slash  -  Block: shield",
  mage: "Tap: 3-cast spell combo  -  Hold: charged spell  -  Block: magic barrier",
  glaive: "Tap: Cyclone Fang 5-hit combo  -  Hold the 5th hit: extra spins  -  Z: Serpent Wheel (no parry, dash/launcher cancel)  -  X: Phantom Spiral dash  -  C: Infinite Crescent  -  Real clashes build Momentum",
  sickle: "Tap: 4-hit dual-sickle combo  -  Hold: Crossbite heavy slash  -  Z: Predator Dash  -  X: Blood Vortex  -  C: Reaper's Frenzy",
  assassin: "Tap: 4-hit dagger flurry  -  Hold: dash strike  -  Block: dagger guard (wide parry)",
  chainblade: "Tap: 4 close sword cuts  -  Hold: Chainbreaker extended lash  -  Z: Chain Snare pull  -  X: Rending Orbit  -  C: Unbound Drive (5s)  -  V: Razor Recall",
  greatsword: "Tap: 3 heavy cleaves  -  Hold: spinning mega-slash  -  Block: blade guard",
  katana: "Tap: 3 swift cuts  -  Hold: iaido dash slash  -  Block: blade guard (wide parry)",
  bow: "Tap: 3 arrows (third is a spread)  -  Hold: piercing power shot  -  Block: arm guard",
  kicks: "Tap: 4-kick combo (snap, roundhouse, high spin, axe)  -  Hold: flying kick  -  Block: arm guard (wide parry)",
  knuckles: "Tap: 5-hit punch combo  -  Hold: rising uppercut  -  Block: forearm guard (wide parry)",
  bomb: "Tap: 3 lobbed firecrackers  -  Hold: big bomb  -  Block: arms up  -  Powder Keg: press its key again to detonate",
  wind: "Tap: 3-hit wind punches  -  Hold: gale palm blast  -  Jump twice to double jump  -  Skills in the air dive and smash the ground",
};
const LEVEL_COLORS = ["#6fcf7f", "#5fa8e3", "#f2994a", "#e8534a"];
export const RANDOM = -1;
const lum = (hex: string) => { const n = parseInt(hex.slice(1), 16); return (0.3 * (n >> 16) + 0.59 * ((n >> 8) & 255) + 0.11 * (n & 255)) / 255; };

/** Turntable preview + info panel for roster index `i` (or RANDOM). */
export function Showcase({ index }: { index: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const prev = useRef<Preview | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    prev.current = new Preview(ref.current!);
    prev.current.onLoading = setLoading;
    let down = false, lastX = 0;
    const el = ref.current!;
    const md = (e: PointerEvent) => { down = true; lastX = e.clientX; };
    const mu = () => { down = false; };
    const mm = (e: PointerEvent) => { if (down && prev.current) { prev.current.drag += (e.clientX - lastX) * 0.01; lastX = e.clientX; } };
    el.addEventListener("pointerdown", md);
    window.addEventListener("pointerup", mu);
    window.addEventListener("pointermove", mm);
    return () => {
      el.removeEventListener("pointerdown", md);
      window.removeEventListener("pointerup", mu);
      window.removeEventListener("pointermove", mm);
      prev.current?.dispose();
    };
  }, []);
  useEffect(() => { prev.current?.setLook(index >= 0 ? CHARACTERS[index].look : null); }, [index]);
  return (
    <div className="showcase">
      <canvas ref={ref} className="preview" />
      {index === RANDOM && <div className="question">?</div>}
      {loading && index !== RANDOM && <div className="model-loading">Loading model...</div>}
    </div>
  );
}

/** Skills are fixed: the purchased fourth skill gets its own V button. No on/off toggles. */
function SkillSummary({ index }: { index: number }) {
  const acc = useAccount();
  const ch = CHARACTERS[index];
  const atks = Kits.attacks(ch.look.kit, ch.look.element);
  const canV = acc.ownsSkill(ch.id);
  return (
    <div className="skill-summary">
      {(["z", "x", "c", "v"] as const).map((k) => (
        <div key={k} className={"skill-summary-row" + (k === "v" && !canV ? " locked" : "")}>
          <Icon src={skillIcon(ch.look.kit, ch.look.element, k)} alt={atks[k].name} size={32} />
          <span><b>[{k.toUpperCase()}] {atks[k].name}</b><small>{k === "v" && !canV
            ? acc.signedIn ? "LOCKED - Buy in the Shop" : "LOCKED - Sign in and buy in the Shop"
            : `${atks[k].cd}s cooldown${k === "v" ? " - UNLOCKED" : ""}`}</small></span>
        </div>
      ))}
    </div>
  );
}

/** Pick the emblem to bring into the match (upgrades happen in the Emblems shop). */
export function EmblemPicker({ onChange, compact }: { onChange?: () => void; compact?: boolean }) {
  const acc = useAccount();
  const [msg, setMsg] = useState("");
  const pick = async (id: string) => {
    setMsg("");
    try { await account.setEmblem(id); onChange?.(); } catch (e: any) { setMsg(e.message); }
  };
  return (
    <div className={"emblem-pick" + (compact ? " compact" : "")}>
      {EMBLEMS.map((e) => {
        const lvl = acc.emblemLevel(e.id);
        const on = acc.profile.emblem === e.id;
        return (
          <button key={e.id} className={"em" + (on ? " on" : "")} onClick={() => pick(e.id)} title={e.desc(lvl)}>
            <Icon src={emblemIcon(e.id)} alt={e.name} size={compact ? 30 : 40} />
            <span><b>{e.name}</b><em>Lv {lvl}/{EMBLEM_MAX}</em>{!compact && <small>{e.desc(lvl)}</small>}</span>
          </button>
        );
      })}
      {msg && <div className="error">{msg}</div>}
    </div>
  );
}

/** Last step before a match: emblem and fixed skills for the chosen fighter. */
export function PreparePanel({ index }: { index: number }) {
  const ch = CHARACTERS[index];
  return (
    <div className="panel prep">
      <h2>Prepare</h2>
      <div className="title">{ch.look.name} - {ch.title}</div>
      <h3>Emblem</h3>
      <EmblemPicker />
      <h3>Skills</h3>
      <SkillSummary index={index} />
      <p className="small">Z / X / C are always available. Unlock V in the Shop while signed in.</p>
    </div>
  );
}

export function InfoPanel({ index, editable }: { index: number; editable?: boolean }) {
  const acc = useAccount();
  if (index === RANDOM) {
    return (
      <div className="panel">
        <h2>Random</h2>
        <div className="title">A surprise opponent</div>
        <p>The CPU picks any fighter except yours when the match starts.</p>
      </div>
    );
  }
  const ch = CHARACTERS[index];
  const atks = Kits.attacks(ch.look.kit, ch.look.element);
  return (
    <div className="panel">
      <h2>{ch.look.name}</h2>
      <div className="title">{ch.title}</div>
      <div className="role">{ch.role}</div>
      <p>{ch.desc}</p>
      <div className="stats">
        {(["power", "speed", "range", "defense"] as const).map((s) => (
          <div key={s} className="stat">
            <span>{s}</span>
            {Array.from({ length: 5 }, (_, p) => <i key={p} style={{ background: p < ch.stats[s] ? ch.look.glow : "rgba(255,255,255,.15)" }} />)}
          </div>
        ))}
      </div>
      <div className="small">{ch.look.element === "metal" ? "Tap: 5-hit Steel Fang - Hold: Magnetic Lance - Z: Rail Spear (press Z to recall) - X: Phantom Barrage - C: Magnetic Dominion (hold to repel) - V: Sovereign Arsenal" : ch.look.element === "frost" ? "Tap: breakable ice shards - Hold: 4 gently homing shards - Z: 4-hit ice shield - X: Auto-freezing Snowpuff - C: Glacier Meteor - V: 3 stationary Frostwings (25s)" : CONTROLS[ch.look.kit]}</div>
      <div className="small">HP {Kits.STATS[ch.look.kit].hp}</div>
      {(() => {
        const slots = ["z", "x", "c", "v"];
        return ["Z", "X", "C", "V"].map((key, i) => {
          const a = atks[slots[i]];
          const tags = Kits.skillTags(a);
          const air = atks[slots[i] + "_air"];
          return <div key={key} className="skill"><b>[{key}] {a.name}</b>{key === "V" && !acc.ownsSkill(ch.id) ? " - LOCKED (Shop, sign-in required)" : ` - ${a.desc}`} <em>({a.cd}s)</em>
            {tags.length > 0 && <small className="tags">{tags.join(" - ")}</small>}
            {air && <small className="tags air">In the air: {air.name} - {air.desc.replace(/^In the air: /, "")}</small>}</div>;
        });
      })()}
      {editable && acc.owns(ch.id) && <div className="small">Skills are fixed to Z / X / C / V; V requires a signed-in purchase.</div>}
      {editable && !acc.owns(ch.id) && (
        <div className="locknote">Locked - unlock for {CHARACTER_PRICE.gold} gold or {CHARACTER_PRICE.diamonds} diamonds in the Shop.</div>
      )}
    </div>
  );
}

export function CardRow({ current, onPick, allowRandom, showLocks }: { current: number; onPick: (i: number) => void; allowRandom?: boolean; showLocks?: boolean }) {
  const acc = useAccount();
  const gridRef = useRef<HTMLDivElement>(null);
  // Keyboard selection stays visible when the user moves beyond the first two rows.
  useEffect(() => {
    const grid = gridRef.current;
    const selected = grid?.querySelector<HTMLButtonElement>(".card.on");
    if (!grid || !selected) return;
    const top = selected.offsetTop, bottom = top + selected.offsetHeight;
    if (top < grid.scrollTop) grid.scrollTop = top;
    else if (bottom > grid.scrollTop + grid.clientHeight)
      grid.scrollTop = bottom - grid.clientHeight;
  }, [current]);
  return (
    <div className="cards" ref={gridRef}>
      {CHARACTERS.map((ch, i) => ({ ch, i }))
        .sort((a, b) => Number(acc.owns(b.ch.id)) - Number(acc.owns(a.ch.id)))
        .map(({ ch, i }) => (
        <button key={ch.id} tabIndex={-1} onMouseDown={(e) => e.preventDefault()} className={"card" + (i === current ? " on" : "")} style={{ background: lum(ch.look.tunic) > 0.7 ? ch.look.cape : ch.look.tunic }} onClick={() => onPick(i)}>
          <Icon src={charIcon(ch.id)} alt={ch.look.name} size={40} />
          <b>{ch.look.name}</b>
          <span>{ch.role.split(" - ")[1] ?? ch.role}</span>
          {showLocks && !acc.owns(ch.id) && <i className="lock">LOCKED</i>}
        </button>
      ))}
      {allowRandom && (
        <button tabIndex={-1} onMouseDown={(e) => e.preventDefault()} className={"card" + (current === RANDOM ? " on" : "")} style={{ background: "#4a4f66" }} onClick={() => onPick(RANDOM)}>
          <Icon src={charIcon("random")} alt="Random" size={40} />
          <b>Random</b>
        </button>
      )}
    </div>
  );
}

export default function Select({ purpose, onBack, onDone, onShop }: {
  purpose: "duel" | "brawl" | "survival" | "team";
  onBack: () => void;
  onShop: () => void;
  onDone: (player: number, cpu?: number, difficulty?: number, teamSize?: number) => void;
}) {
  const [size, setSize] = useState(3);
  const team = purpose === "team";
  const [step, setStep] = useState(0);
  const [me, setMe] = useState(0);
  const [cpu, setCpu] = useState(RANDOM);
  const [level, setLevel] = useState(1);
  const shown = step !== 1 || purpose === "team" ? me : cpu;
  const n = CHARACTERS.length;
  const acc = useAccount();
  const myLocked = !acc.owns(CHARACTERS[me].id);

  // Steps: 0 fighter -> 1 opponent / team setup (not survival) -> last: prepare (emblem, skills).
  const prepStep = purpose === "survival" ? 1 : 2;
  const finish = () => {
    if (purpose === "survival") return onDone(me);
    if (team) return onDone(me, undefined, level, size);
    let c = cpu;
    if (c === RANDOM) { const opts = CHARACTERS.map((_, i) => i).filter((i) => i !== me); c = opts[Math.floor(Math.random() * opts.length)]; }
    onDone(me, c, level);
  };
  const next = () => (myLocked ? onShop() : step < prepStep ? setStep(step + 1) : finish());
  const back = () => (step > 0 ? setStep(step - 1) : onBack());

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.code === "ArrowLeft" || e.code === "KeyA") step === 0 ? setMe((m) => (m + n - 1) % n) : setCpu((c) => (c === RANDOM ? n - 1 : c === 0 ? RANDOM : c - 1));
      if (e.code === "ArrowRight" || e.code === "KeyD") step === 0 ? setMe((m) => (m + 1) % n) : setCpu((c) => (c === RANDOM ? 0 : c === n - 1 ? RANDOM : c + 1));
      if (e.code === "Enter") { e.preventDefault(); next(); }
      if (e.code === "Escape") back();
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });

  return (
    <div className="select">
      <Showcase index={shown} />
      <div className="header">
        <h1 style={{ color: step === 1 ? "#ffb3a8" : step === prepStep ? "#ffe08a" : "#fff" }}>{step === 0 ? "CHOOSE YOUR FIGHTER" : step === prepStep ? "PREPARE FOR BATTLE" : team ? "TEAM BATTLE VS CPU" : "CHOOSE YOUR OPPONENT"}</h1>
        <div className="sub">{step === 0 ? "Click a card or use Left / Right. Drag to rotate. Enter: next."
          : step === prepStep ? "Pick your emblem. Z/X/C are fixed; V unlocks after purchase. Enter: fight."
          : team ? `You: ${CHARACTERS[me].look.name}. CPU teammates join you against a CPU team. Pick the size and difficulty.`
          : `You: ${CHARACTERS[me].look.name}. Pick the CPU's fighter and difficulty.`}</div>
      </div>
      {step === prepStep ? <PreparePanel index={me} /> : !(team && step === 1) && <InfoPanel index={shown} editable={step === 0} />}
      <div className="bottom">
        {(step === 0 || (step === 1 && !team)) && <CardRow current={shown} onPick={(i) => (step === 0 ? setMe(i) : setCpu(i))} allowRandom={step === 1} showLocks={step === 0} />}
        <div className="actions">
          {team && step === 1 && (
            <div className="levels">
              <span>Team size</span>
              <div>
                {[2, 3, 4].map((n2) => (
                  <button key={n2} className={"lvl" + (n2 === size ? " on" : "")} style={{ ["--c" as any]: "#5fa8ff" }} onClick={() => setSize(n2)}>{n2}v{n2}</button>
                ))}
              </div>
            </div>
          )}
          {step === 1 && purpose !== "survival" && (
            <div className="levels">
              <span>CPU difficulty</span>
              <div>
                {LEVELS.map((l, i) => (
                  <button key={l} className={"lvl" + (i === level ? " on" : "")} style={{ ["--c" as any]: LEVEL_COLORS[i] }} onClick={() => setLevel(i)}>{l}</button>
                ))}
              </div>
            </div>
          )}
          <div className="row">
            <button className="big ghost" onClick={back}>&lt; BACK</button>
            <button className="big gold" onClick={next}>{myLocked ? "UNLOCK IN SHOP" : step < prepStep ? "NEXT >" : "FIGHT!"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
