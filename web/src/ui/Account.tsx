"use client";
import { useState } from "react";
import { account, supabase, useAccount } from "@/lib/account";
import { Gold, Diamond } from "./icons";

/** Gold / diamond balance chip shown on menus. */
export function Wallet({ onAccount }: { onAccount?: () => void }) {
  const acc = useAccount();
  const p = acc.profile;
  return (
    <div className="wallet">
      <span className="gold"><Gold /> {p.gold.toLocaleString()}</span>
      <span className="dia"><Diamond /> {p.diamonds.toLocaleString()}</span>
      {onAccount && (
        <button className="chip" onClick={onAccount}>{acc.signedIn ? p.username : "Sign in"}</button>
      )}
    </div>
  );
}

export default function AccountScreen({ onBack }: { onBack: () => void }) {
  const acc = useAccount();
  const [mode, setMode] = useState<"in" | "up">("in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setMsg("");
    try {
      if (mode === "up") {
        if (!/^[A-Za-z0-9_]{2,16}$/.test(username)) throw new Error("Username: 2-16 letters, numbers or _");
        const confirm = await account.signUp(email, password, username);
        setMsg(confirm ? "Account created. Check your email to confirm it, then sign in." : "Account created!");
      } else {
        await account.signIn(email, password);
      }
    } catch (e: any) {
      setMsg(e.message);
    }
    setBusy(false);
  };

  if (acc.signedIn) {
    const p = acc.profile;
    return (
      <div className="menu">
        <div className="menu-card">
          <h1 className="logo small">{p.username}</h1>
          <p className="tag">{acc.email}</p>
          <Wallet />
          <p className="note">{p.characters.length} fighters owned. Your progress is saved to your account.</p>
          <button className="big ghost" onClick={() => account.signOut()}>Sign out</button>
          <button className="big gold" onClick={onBack}>Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="menu">
      <div className="menu-card">
        <h1 className="logo small">{mode === "in" ? "SIGN IN" : "CREATE ACCOUNT"}</h1>
        <p className="tag">An account saves your gold, fighters and emblems, and unlocks diamonds and gold bets. You can always play as a guest instead.</p>
        {!supabase && <div className="error">Accounts aren&apos;t configured on this deployment.</div>}
        <button className="big google" disabled={busy || !supabase} onClick={async () => {
          setBusy(true); setMsg("");
          try { await account.signInWithGoogle(); } catch (e: any) { setMsg(e.message); setBusy(false); }
        }}><GoogleG /> Continue with Google</button>
        <div className="or"><span>or use email</span></div>
        {mode === "up" && <input placeholder="Username" value={username} maxLength={16} onChange={(e) => setUsername(e.target.value)} />}
        <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input placeholder="Password (6+ characters)" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()} />
        <button className="big gold" disabled={busy || !supabase} onClick={submit}>{mode === "in" ? "Sign in" : "Create account"}</button>
        {msg && <div className="note">{msg}</div>}
        <button className="big ghost" onClick={() => { setMode(mode === "in" ? "up" : "in"); setMsg(""); }}>
          {mode === "in" ? "New here? Create an account" : "Have an account? Sign in"}
        </button>
        <button className="big" onClick={onBack}>Play as guest</button>
      </div>
    </div>
  );
}

function GoogleG() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true" style={{ verticalAlign: "-3px", marginRight: 8 }}>
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.1 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.1 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}
