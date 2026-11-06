"use client";
import { useEffect, useState } from "react";
import { Sound } from "@/game/sound";
import { ACTIONS, RESERVED, bind, bindings, keyLabel, loadBindings, onBindingsChange, resetBindings, type Action } from "@/game/keys";

/** Re-renders when key bindings change. */
export function useBindings() {
  const [, setN] = useState(0);
  useEffect(() => { const off = onBindingsChange(() => setN((n) => n + 1)); loadBindings(); return off; }, []);
  return bindings();
}

export default function Settings({ onBack }: { onBack: () => void }) {
  const b = useBindings();
  const [wait, setWait] = useState<{ action: Action; slot: 0 | 1 } | null>(null);
  const [msg, setMsg] = useState("");
  const [vol, setVol] = useState({ ...Sound.vol });

  // While waiting, the next key or mouse button becomes the binding (Esc cancels).
  useEffect(() => {
    if (!wait) return;
    const take = (code: string) => {
      if (code === "Escape") { setWait(null); return; }
      if (RESERVED.has(code)) { setMsg(`${keyLabel(code)} is reserved (Esc pauses, R is rematch).`); return; }
      bind(wait.action, wait.slot, code);
      setMsg("");
      setWait(null);
    };
    const onKey = (e: KeyboardEvent) => { e.preventDefault(); e.stopPropagation(); take(e.code); };
    const onMouse = (e: MouseEvent) => { e.preventDefault(); take("Mouse" + e.button); };
    const noMenu = (e: Event) => e.preventDefault();
    // Let the click that opened the prompt finish before listening for mouse buttons.
    const t = setTimeout(() => window.addEventListener("mousedown", onMouse, true), 50);
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("contextmenu", noMenu, true);
    return () => {
      clearTimeout(t);
      window.removeEventListener("keydown", onKey, true);
      window.removeEventListener("mousedown", onMouse, true);
      setTimeout(() => window.removeEventListener("contextmenu", noMenu, true), 0);
    };
  }, [wait]);

  return (
    <div className="menu">
      <div className="menu-card settings">
        <h1 className="logo small">AUDIO SETTINGS</h1>
        {/* INDEPENDENT_AUDIO_UI_V1 */}
        <p className="tag">Music changes only background tracks. Clashes, parries, blocks, and guard breaks have their own slider. Master changes everything.</p>
        <div className="volumes">
          {([["music", "Music"], ["sfx", "Sound Effects"], ["combat", "Clashes & Parries"], ["master", "Master"]] as const).map(([k, label]) => (
            <label key={k} className="vol-row">
              <span className="act">{label}</span>
              <input type="range" min={0} max={100} value={Math.round(vol[k] * 100)}
                aria-label={`${label} volume`}
                onChange={(e) => { Sound.setVolume(k, +e.target.value / 100); setVol({ ...Sound.vol }); }}
                onPointerUp={() => {
                  if (k === "sfx") Sound.play("hit_blade", 0.8);
                  if (k === "combat") Sound.play("clash", 0.85, 0);
                }} />
              <em>{Math.round(vol[k] * 100)}%</em>
            </label>
          ))}
        </div>
        <h1 className="logo small">CONTROLS</h1>
        <p className="tag">Click a slot, then press a key or mouse button. Esc cancels. Each action can have two inputs.</p>
        <div className="binds">
          {ACTIONS.map((a) => (
            <div key={a.id} className="bind-row">
              <span className="act">{a.label}</span>
              {([0, 1] as const).map((slot) => {
                const listening = wait?.action === a.id && wait.slot === slot;
                const code = b[a.id][slot];
                return (
                  <span key={slot} className="slotwrap">
                    <button className={"slot" + (listening ? " listening" : "") + (code ? "" : " empty")}
                      onClick={() => { setMsg(""); setWait({ action: a.id, slot }); }}>
                      {listening ? "Press a key..." : keyLabel(code)}
                    </button>
                    {code && !listening && <button className="clear" title="Clear" onClick={() => bind(a.id, slot, "")}>x</button>}
                  </span>
                );
              })}
            </div>
          ))}
        </div>
        {msg && <div className="error">{msg}</div>}
        <p className="note">Esc always pauses a match and R starts a rematch. Bindings are saved in this browser.</p>
        <div className="row two">
          <button className="big ghost" onClick={() => { resetBindings(); setWait(null); setMsg("Controls reset to defaults."); }}>Reset defaults</button>
          <button className="big gold" onClick={onBack}>Done</button>
        </div>
      </div>
    </div>
  );
}
