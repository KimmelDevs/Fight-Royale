// Player account: either a Supabase account (progress saved in the cloud, all changes go
// through server functions that enforce prices and caps) or a guest wallet kept in this
// browser's localStorage, so the game stays fully playable without signing up.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import {
  CHARACTER_PRICE, SKILL_PRICE, EMBLEM_MAX, emblemCost, guestProfile, type Profile,
} from "@/game/economy";
import { CHARACTERS } from "@/game/roster";

import { SUPABASE_URL as URL_, SUPABASE_ANON_KEY as KEY } from "./config";
const GUEST_KEY = "fr-guest-profile";

export const supabase: SupabaseClient | null = URL_ && KEY ? createClient(URL_, KEY) : null;

type Listener = () => void;

class Account {
  signedIn = false;
  email = "";
  profile: Profile = guestProfile();
  ready = false;
  private listeners = new Set<Listener>();

  constructor() {
    if (typeof window === "undefined") return;
    this.loadGuest();
    if (!supabase) { this.ready = true; return; }
    supabase.auth.getSession().then(({ data }) => this.onSession(data.session));
    supabase.auth.onAuthStateChange((_e, session) => this.onSession(session));
  }

  subscribe(l: Listener) { this.listeners.add(l); return () => { this.listeners.delete(l); }; }
  private emit() { this.listeners.forEach((l) => l()); }

  private async onSession(session: any) {
    this.signedIn = !!session;
    this.email = session?.user?.email ?? "";
    if (session) await this.refresh();
    else this.loadGuest();
    this.ready = true;
    this.emit();
  }

  private loadGuest() {
    try {
      const raw = localStorage.getItem(GUEST_KEY);
      this.profile = raw ? { ...guestProfile(), ...JSON.parse(raw) } : guestProfile();
    } catch { this.profile = guestProfile(); }
  }

  private saveGuest() {
    try { localStorage.setItem(GUEST_KEY, JSON.stringify(this.profile)); } catch {}
    this.emit();
  }

  private setProfile(row: any) {
    if (!row) return;
    this.profile = {
      username: row.username ?? "Player", gold: Number(row.gold), diamonds: Number(row.diamonds),
      characters: row.characters ?? [], skills: row.skills ?? [], loadouts: row.loadouts ?? {},
      emblems: row.emblems ?? {}, emblem: row.emblem ?? "fighter",
    };
    this.emit();
  }

  async refresh() {
    if (!supabase || !this.signedIn) return;
    const { data } = await supabase.from("profiles").select("*").single();
    this.setProfile(data);
    supabase.rpc("refund_stale_bets").then(({ data: d }) => d && this.setProfile(d));
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
    const { data, error } = await supabase.auth.signUp({ email, password, options: { data: { username } } });
    if (error) throw new Error(error.message);
    return !data.session; // true = check your email to confirm
  }

  async signIn(email: string, password: string) {
    if (!supabase) throw new Error("Accounts are not configured");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message);
  }

  async signOut() { await supabase?.auth.signOut(); }

  // --- ownership ---------------------------------------------------------------------
  owns(charId: string) { return this.profile.characters.includes(charId); }
  ownsSkill(charId: string) { return this.profile.skills.includes(charId); }
  emblemLevel(id: string) { return this.profile.emblems[id] ?? 1; }
  loadout(charId: string) { return this.profile.loadouts[charId] ?? ["z", "x", "c"]; }

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
    if (this.signedIn) return this.rpc("buy_skill", { p_char: charId, p_currency: currency });
    if (currency !== "gold") throw new Error("Sign in to use diamonds");
    if (this.profile.gold < SKILL_PRICE.gold) throw new Error("not enough gold");
    this.profile.gold -= SKILL_PRICE.gold;
    this.profile.skills = [...this.profile.skills, charId];
    this.saveGuest();
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
    return { loadout: this.loadout(id), emblem: { id: this.profile.emblem, level: this.emblemLevel(this.profile.emblem) } };
  }
}

export const account = new Account();

/** Re-renders the component whenever the account or profile changes. */
export function useAccount() {
  const [, setN] = useState(0);
  useEffect(() => account.subscribe(() => setN((n) => n + 1)), []);
  return account;
}
