"use client";
import { useState } from "react";
import { account, supabase, useAccount } from "@/lib/account";

/** Gold / diamond balance chip shown on menus. */
export function Wallet({ onAccount }: { onAccount?: () => void }) {
  const acc = useAccount();
  const p = acc.profile;
  return (
    <div className="wallet">
      <span className="gold">{p.gold.toLocaleString()} gold</span>
      <span className="dia">{p.diamonds.toLocaleString()} diamonds</span>
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
