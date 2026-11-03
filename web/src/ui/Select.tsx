"use client";
import { useEffect, useRef, useState } from "react";
import { CHARACTERS } from "@/game/roster";
import * as Kits from "@/game/kits";
import { LEVELS } from "@/game/ai";
import { Preview } from "@/game/preview";

const CONTROLS: Record<string, string> = {
  knight: "Tap: 3-hit sword combo  -  Hold: charged slash  -  Block: shield",
  mage: "Tap: 3-cast spell combo  -  Hold: charged spell  -  Block: magic barrier",
  assassin: "Tap: 4-hit dagger flurry  -  Hold: dash strike  -  Block: dagger guard (wide parry)",
  greatsword: "Tap: 3 heavy cleaves  -  Hold: spinning mega-slash  -  Block: blade guard",
  katana: "Tap: 3 swift cuts  -  Hold: iaido dash slash  -  Block: blade guard (wide parry)",
  bow: "Tap: 3 arrows (third is a spread)  -  Hold: piercing power shot  -  Block: arm guard",
  knuckles: "Tap: 5-hit punch combo  -  Hold: rising uppercut  -  Block: forearm guard (wide parry)",
};
const LEVEL_COLORS = ["#6fcf7f", "#5fa8e3", "#f2994a", "#e8534a"];
export const RANDOM = -1;
const lum = (hex: string) => { const n = parseInt(hex.slice(1), 16); return (0.3 * (n >> 16) + 0.59 * ((n >> 8) & 255) + 0.11 * (n & 255)) / 255; };

/** Turntable preview + info panel for roster index `i` (or RANDOM). */
export function Showcase({ index }: { index: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const prev = useRef<Preview | null>(null);
  useEffect(() => {
    prev.current = new Preview(ref.current!);
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
    </div>
  );
}

export function InfoPanel({ index }: { index: number }) {
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
      <div className="small">{CONTROLS[ch.look.kit]}</div>
      <div className="small">HP {Kits.STATS[ch.look.kit].hp}</div>
      {(["z", "x", "c"] as const).map((k) => (
        <div key={k} className="skill"><b>[{k.toUpperCase()}] {atks[k].name}</b> - {atks[k].desc} <em>({atks[k].cd}s)</em></div>
      ))}
    </div>
  );
}

export function CardRow({ current, onPick, allowRandom }: { current: number; onPick: (i: number) => void; allowRandom?: boolean }) {
  return (
    <div className="cards">
      {CHARACTERS.map((ch, i) => (
        <button key={ch.id} tabIndex={-1} onMouseDown={(e) => e.preventDefault()} className={"card" + (i === current ? " on" : "")} style={{ background: lum(ch.look.tunic) > 0.7 ? ch.look.cape : ch.look.tunic }} onClick={() => onPick(i)}>
          <b>{ch.look.name}</b>
          <span>{ch.role.split(" - ")[1] ?? ch.role}</span>
        </button>
      ))}
      {allowRandom && (
        <button tabIndex={-1} onMouseDown={(e) => e.preventDefault()} className={"card" + (current === RANDOM ? " on" : "")} style={{ background: "#4a4f66" }} onClick={() => onPick(RANDOM)}>
          <b>Random</b><span>?</span>
        </button>
      )}
    </div>
  );
}

export default function Select({ purpose, onBack, onDone }: {
  purpose: "duel" | "survival";
  onBack: () => void;
  onDone: (player: number, cpu?: number, difficulty?: number) => void;
}) {
  const [step, setStep] = useState(0);
  const [me, setMe] = useState(0);
  const [cpu, setCpu] = useState(RANDOM);
  const [level, setLevel] = useState(1);
  const shown = step === 0 ? me : cpu;
  const n = CHARACTERS.length;

  const finish = () => {
    if (purpose === "survival") return onDone(me);
    let c = cpu;
    if (c === RANDOM) { const opts = CHARACTERS.map((_, i) => i).filter((i) => i !== me); c = opts[Math.floor(Math.random() * opts.length)]; }
    onDone(me, c, level);
  };
  const next = () => (purpose === "duel" && step === 0 ? setStep(1) : finish());

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.code === "ArrowLeft" || e.code === "KeyA") step === 0 ? setMe((m) => (m + n - 1) % n) : setCpu((c) => (c === RANDOM ? n - 1 : c === 0 ? RANDOM : c - 1));
      if (e.code === "ArrowRight" || e.code === "KeyD") step === 0 ? setMe((m) => (m + 1) % n) : setCpu((c) => (c === RANDOM ? 0 : c === n - 1 ? RANDOM : c + 1));
      if (e.code === "Enter") { e.preventDefault(); next(); }
      if (e.code === "Escape") step === 1 ? setStep(0) : onBack();
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });

  return (
    <div className="select">
      <Showcase index={shown} />
      <div className="header">
        <h1 style={{ color: step === 1 ? "#ffb3a8" : "#fff" }}>{step === 0 ? "CHOOSE YOUR FIGHTER" : "CHOOSE YOUR OPPONENT"}</h1>
        <div className="sub">{step === 0 ? "Click a card or use Left / Right. Drag to rotate. Enter: next." : `You: ${CHARACTERS[me].look.name}. Pick the CPU's fighter and difficulty.`}</div>
      </div>
      <InfoPanel index={shown} />
      <div className="bottom">
        <CardRow current={shown} onPick={(i) => (step === 0 ? setMe(i) : setCpu(i))} allowRandom={step === 1} />
        <div className="actions">
          {step === 1 && (
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
            <button className="big ghost" onClick={() => (step === 1 ? setStep(0) : onBack())}>&lt; BACK</button>
            <button className="big gold" onClick={next}>{purpose === "duel" && step === 0 ? "NEXT >" : "FIGHT!"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
