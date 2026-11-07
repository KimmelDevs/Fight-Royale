// FOURTH_SKILL_V_MASTER_AI_TWO_ROW_ROSTER_20261107_V1
// Player account: either a Supabase account (progress saved in the cloud, all changes go
// through server functions that enforce prices and caps) or a guest wallet kept in this
// browser's localStorage, so the game stays fully playable without signing up.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import {
  CHARACTER_PRICE, EMBLEM_MAX, emblemCost, guestProfile, START_CHARACTERS, type Profile,
} from "@/game/economy";
import { CHARACTERS } from "@/game/roster";

import { SUPABASE_URL as URL_, SUPABASE_ANON_KEY as KEY } from "./config";
const GUEST_KEY = "fr-guest-profile";

export const supabase: SupabaseClient | null = URL_ && KEY
  ? createClient(URL_, KEY, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: "pkce" } })
  : null;

type Listener = () => void;

class Account {
  signedIn = false;
  email = "";
  profile: Profile = guestProfile();
  ready = false;
  /** Signed in but the cloud profile hasn't arrived (or failed): don't show guest data. */
  loading = false;
  loadError = "";
  /** Bumped on every sign-in / sign-out so late replies from an old session are dropped. */
  private gen = 0;
  private listeners = new Set<Listener>();

  constructor() {
    if (typeof window === "undefined") return;
    this.loadGuest();
    if (!supabase) { this.ready = true; return; }
    // The listener fires INITIAL_SESSION on load with the session saved in localStorage.
    // Never await Supabase calls inside it (supabase-js holds an auth lock there and the
    // nested call deadlocks, which left the page looking signed out after a refresh).
    supabase.auth.onAuthStateChange((_e, session) => { setTimeout(() => this.onSession(session), 0); });
  }

  subscribe(l: Listener) { this.listeners.add(l); return () => { this.listeners.delete(l); }; }
  private emit() { this.listeners.forEach((l) => l()); }

  private async onSession(session: any) {
    const email = session?.user?.email ?? "";
    if (session && this.signedIn && this.email === email && this.ready && !this.loadError) return; // token refresh
    if (!session && !this.signedIn && this.ready) return;
    const gen = ++this.gen;
    this.signedIn = !!session;
    this.email = email;
    if (session) {
      // Never show the guest wallet as if it were the account while the profile loads.
      this.profile = { ...guestProfile(), gold: 0, diamonds: 0, characters: [], username: email.split("@")[0] || "Player" };
      this.loading = true;
      this.loadError = "";
      this.ready = true;
      this.emit();
      await this.refresh(gen);
      this.cleanAuthUrl();
    } else {
      this.loading = false;
      this.loadError = "";
      this.loadGuest();
    }
    this.ready = true;
    this.emit();
  }

  /** Google sign-in returns with ?code=...; drop it from the address bar once used. */
  private cleanAuthUrl() {
    try {
      const u = new URL(window.location.href);
      if (u.searchParams.has("code") || u.hash.includes("access_token")) window.history.replaceState(null, "", u.pathname);
    } catch {}
  }

  private loadGuest() {
    try {
      const raw = localStorage.getItem(GUEST_KEY);
      this.profile = raw ? { ...guestProfile(), ...JSON.parse(raw) } : guestProfile();
      this.profile.characters = [...new Set([...START_CHARACTERS, ...this.profile.characters])];
    } catch { this.profile = guestProfile(); }
  }

  private saveGuest() {
    try { localStorage.setItem(GUEST_KEY, JSON.stringify(this.profile)); } catch {}
    this.emit();
  }

  private setProfile(row: any, gen = this.gen) {
    if (!row || gen !== this.gen || !this.signedIn) return; // stale reply from an older session
    this.profile = {
      username: row.username ?? "Player", gold: Number(row.gold), diamonds: Number(row.diamonds),
      characters: row.characters ?? [], skills: row.skills ?? [], loadouts: row.loadouts ?? {},
      emblems: row.emblems ?? {}, emblem: row.emblem ?? "fighter",
    };
    this.emit();
  }

  async refresh(gen = this.gen) {
    if (!supabase || !this.signedIn) return;
    // my_profile also re-applies admin unlocks; fall back to a plain read if it isn't deployed.
    let { data, error } = await supabase.rpc("my_profile");
    if (error || !data) ({ data, error } = await supabase.from("profiles").select("*").maybeSingle());
    if (gen !== this.gen) return;
    this.loading = false;
    if (error || !data) {
      this.loadError = error ? `Couldn't load your profile: ${error.message}` : "Your profile wasn't found. Try signing out and in again.";
      this.emit();
      return;
    }
    this.loadError = "";
    this.setProfile(data, gen);
    supabase.rpc("refund_stale_bets").then(({ data: d }) => d && this.setProfile(d, gen));
  }

  /** Calls a server function and adopts the profile row it returns. Throws its message. */
  private async rpc(name: string, args: Record<string, any> = {}) {
    const { data, error } = await supabase!.rpc(name, args);
    if (error) throw new Error(error.message);
    this.setProfile(data);
  }

  // --- auth ------------------------------------------------------------------------
  async signUp(email: string, password: string, username: string) {
    if (!supabase) throw new Error("Accounts are not configured");
    const { data, error } = await supabase.auth.signUp({ email: email.trim(), password, options: { data: { username } } });
    if (error) throw new Error(error.message);
    if (data.session) await this.onSession(data.session);
    return !data.session; // true = check your email to confirm
  }

  async signIn(email: string, password: string) {
    if (!supabase) throw new Error("Accounts are not configured");
    const { data, error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    if (error) throw new Error(error.message === "Invalid login credentials" ? "Wrong email or password." : error.message);
    await this.onSession(data.session);
  }

  /** Google sign-in: redirects to Google, then back to this page already signed in. */
  async signInWithGoogle() {
    if (!supabase) throw new Error("Accounts are not configured");
    const { error } = await supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo: window.location.origin } });
    if (error) throw new Error(error.message);
  }

  /** Signs out on this device right away (no network needed), back to the guest wallet. */
  async signOut() {
    if (!supabase) return;
    this.gen++;
    this.signedIn = false;
    this.email = "";
    this.loading = false;
    this.loadError = "";
    this.loadGuest();
    this.emit();
    const { error } = await supabase.auth.signOut({ scope: "local" });
    if (error) {
      // Last resort: forget the stored session so a refresh can't sign back in.
      try { Object.keys(localStorage).filter((k) => k.startsWith("sb-") && k.includes("auth")).forEach((k) => localStorage.removeItem(k)); } catch {}
    }
  }

  // --- ownership ---------------------------------------------------------------------
  owns(charId: string) {
    // Guest Mode: all current and future roster characters are playable.
    if (!this.signedIn) return true;
    // Signed-in accounts still use their purchased/unlocked characters.
    return this.profile.characters.includes(charId);
  }
  /** Fourth skills require a real signed-in purchase; old guest purchases never count. */
  ownsSkill(charId: string) { return this.signedIn && !this.loading && !this.loadError && this.profile.skills.includes(charId); }
  emblemLevel(id: string) { return this.profile.emblems[id] ?? 1; }
  /** Legacy custom loadouts are intentionally ignored: Z/X/C are always the core skills. */
  loadout(_charId: string) { return ["z", "x", "c"]; }

  /** Guests can only spend gold; diamonds need an account. */
  async buyCharacter(charId: string, currency: "gold" | "diamonds") {
    if (this.signedIn) return this.rpc("buy_character", { p_char: charId, p_currency: currency });
    if (currency !== "gold") throw new Error("Sign in to use diamonds");
    if (this.profile.gold < CHARACTER_PRICE.gold) throw new Error("not enough gold");
    this.profile.gold -= CHARACTER_PRICE.gold;
    this.profile.characters = [...this.profile.characters, charId];
    this.saveGuest();
  }

  async buySkill(charId: string, currency: "gold" | "diamonds") {
    if (!this.signedIn || this.loading || this.loadError)
      throw new Error("Sign in and load your account to unlock fourth skills");
    return this.rpc("buy_skill", { p_char: charId, p_currency: currency });
  }

  async setLoadout(charId: string, slots: string[]) {
    if (this.signedIn) return this.rpc("set_loadout", { p_char: charId, p_slots: slots });
    this.profile.loadouts = { ...this.profile.loadouts, [charId]: slots };
    this.saveGuest();
  }

  async setEmblem(id: string) {
    if (this.signedIn) return this.rpc("set_emblem", { p_emblem: id });
    this.profile.emblem = id;
    this.saveGuest();
  }

  async upgradeEmblem(id: string) {
    if (this.signedIn) return this.rpc("upgrade_emblem", { p_emblem: id });
    const lvl = this.emblemLevel(id);
    if (lvl >= EMBLEM_MAX) throw new Error("emblem at max level");
    if (this.profile.gold < emblemCost(lvl)) throw new Error("not enough gold");
    this.profile.gold -= emblemCost(lvl);
    this.profile.emblems = { ...this.profile.emblems, [id]: lvl + 1 };
    this.saveGuest();
  }

  // --- earning -----------------------------------------------------------------------
  /** Credits match gold. Accounts are capped server-side; returns the amount credited. */
  async claimReward(reason: "duel" | "team" | "survival", amount: number): Promise<number> {
    if (amount <= 0) return 0;
    if (!this.signedIn) {
      this.profile.gold += amount;
      this.saveGuest();
      return amount;
    }
    const before = this.profile.gold;
    try { await this.rpc("claim_reward", { p_reason: reason, p_amount: Math.round(amount) }); }
    catch { return 0; }
    return this.profile.gold - before;
  }

  async adReward() {
    if (!this.signedIn) throw new Error("Sign in to earn diamonds");
    return this.rpc("ad_reward");
  }

  async placeBet(matchId: string, team: number, amount: number) {
    if (!this.signedIn || amount <= 0) return false;
    try { await this.rpc("place_bet", { p_match: matchId, p_team: team, p_amount: amount }); return true; }
    catch { return false; }
  }

  async reportResult(matchId: string, winner: number) {
    if (!this.signedIn) return;
    try { await this.rpc("report_result", { p_match: matchId, p_winner: winner }); } catch {}
  }

  async buyDiamonds(pack: string) {
    if (!supabase || !this.signedIn) throw new Error("Sign in to buy diamonds");
    const { data, error } = await supabase.functions.invoke("create-checkout", { body: { pack } });
    if (error || !data?.url) throw new Error(data?.error ?? "The diamond store isn't open yet");
    window.location.href = data.url;
  }

  /** The loadout and emblem a match should use for this character. */
  matchKit(charIndex: number) {
    const id = CHARACTERS[charIndex].id;
    return { loadout: ["z", "x", "c"], bonusSkillUnlocked: this.ownsSkill(id), emblem: { id: this.profile.emblem, level: this.emblemLevel(this.profile.emblem) } };
  }
}

export const account = new Account();

/** Re-renders the component whenever the account or profile changes. */
export function useAccount() {
  const [, setN] = useState(0);
  useEffect(() => account.subscribe(() => setN((n) => n + 1)), []);
  return account;
}
