"use client";
// FIGHT_ROYALE_CPU_VS_CPU_SPECTATOR_V1
import { useState } from "react";
import { CHARACTERS } from "@/game/roster";
import { LEVELS } from "@/game/ai";
import { CardRow, Showcase, RANDOM } from "./Select";

const COLORS = ["#6fcf7f", "#5fa8e3", "#f2994a", "#e8534a"];
const nameOf = (i: number) => i === RANDOM ? "Random fighter" : CHARACTERS[i]?.look.name ?? "Unknown";

/** Two CPU fighters, selectable difficulty, no player slot, no unlock requirement. */
export default function WatchSelect({ onBack, onStart }: {
  onBack: () => void;
  onStart: (left: number, right: number, difficulty: number) => void;
}) {
  const [active, setActive] = useState<0 | 1>(0);
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(1);
  const [difficulty, setDifficulty] = useState(1);
  const chosen = active === 0 ? left : right;

  const start = () => {
    const ids = CHARACTERS.map((_, i) => i);
    const a = left === RANDOM ? ids[Math.floor(Math.random() * ids.length)] : left;
    const choices = ids.filter((i) => i !== a);
    const b = right === RANDOM ? choices[Math.floor(Math.random() * choices.length)] : right;
    onStart(a, b, difficulty);
  };

  return (
    <div className="select">
      <Showcase index={chosen} />
      <div className="header">
        <h1 style={{ color: "#ffe08a" }}>CPU VS CPU · SPECTATOR</h1>
        <div className="sub">Pick two fighters, choose AI difficulty, then watch a best-of-three duel. No player controls required.</div>
      </div>
      <div className="panel" style={{ width: "min(730px, 94vw)", margin: "0 auto", padding: 14 }}>
        <h2>Choose the matchup</h2>
        <div className="row two" style={{ gap: 10, alignItems: "stretch" }}>
          <button type="button" className={"big" + (active === 0 ? " blue" : " ghost")}
            onClick={() => setActive(0)} style={{ flex: 1, minWidth: 0, padding: "13px 8px" }}>
            <span style={{ display: "block", fontSize: 11, opacity: 0.8 }}>CPU 1 · BLUE</span>
            {nameOf(left)} {active === 0 ? "✓" : ""}
          </button>
          <button type="button" className={"big" + (active === 1 ? " gold" : " ghost")}
            onClick={() => setActive(1)} style={{ flex: 1, minWidth: 0, padding: "13px 8px" }}>
            <span style={{ display: "block", fontSize: 11, opacity: 0.8 }}>CPU 2 · RED</span>
            {nameOf(right)} {active === 1 ? "✓" : ""}
          </button>
        </div>
        <div className="small" style={{ marginTop: 8 }}>Select {active === 0 ? "CPU 1" : "CPU 2"} from the fighter cards below. Any fighter is allowed in offline spectator mode.</div>
      </div>
      <div className="bottom">
        <CardRow current={chosen} allowRandom showLocks={false}
          onPick={(i) => active === 0 ? setLeft(i) : setRight(i)} />
        <div className="actions">
          <div className="levels">
            <span>Both CPUs · AI difficulty</span>
            <div>
              {LEVELS.map((l, i) => (
                <button key={l} className={"lvl" + (i === difficulty ? " on" : "")}
                  style={{ ["--c" as any]: COLORS[i] ?? "#e8534a" }} onClick={() => setDifficulty(i)}>{l}</button>
              ))}
            </div>
          </div>
          <div className="row">
            <button className="big ghost" onClick={onBack}>&lt; BACK</button>
            <button className="big gold" onClick={start}>WATCH FIGHT!</button>
          </div>
        </div>
      </div>
    </div>
  );
}
