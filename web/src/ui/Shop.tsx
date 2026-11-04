"use client";
import { useState } from "react";
import { account, useAccount } from "@/lib/account";
import { adsAvailable, adsAreDemo, showRewardedAd } from "@/lib/ads";
import { CHARACTERS } from "@/game/roster";
import * as Kits from "@/game/kits";
import {
  CHARACTER_PRICE, SKILL_PRICE, DIAMOND_PACKS, EMBLEMS, EMBLEM_MAX, emblemCost, AD_DIAMONDS, ADS_PER_DAY,
} from "@/game/economy";
import { Wallet } from "./Account";
import { Icon, skillIcon, emblemIcon, Gold, Diamond } from "./icons";

type Tab = "fighters" | "skills" | "emblems" | "diamonds";

export default function Shop({ onBack, onAccount, start = "fighters" }: { onBack: () => void; onAccount: () => void; start?: Tab }) {
  const acc = useAccount();
  const [tab, setTab] = useState<Tab>(start);
  const [msg, setMsg] = useState("");
  const [adT, setAdT] = useState(0);

  const run = async (fn: () => Promise<any>, ok: string) => {
    setMsg("");
    try { await fn(); setMsg(ok); } catch (e: any) { setMsg(e.message); }
  };

  const watchAd = async () => {
    setMsg("");
    const ok = await showRewardedAd(setAdT);
    if (!ok) return setMsg("No reward: the ad didn't finish.");
    run(() => account.adReward(), `+${AD_DIAMONDS} diamonds!`);
  };

  const p = acc.profile;
  return (
    <div className="shop">
      <div className="shop-head">
        <h1>{tab === "emblems" ? "EMBLEMS" : "SHOP"}</h1>
        <Wallet onAccount={onAccount} />
      </div>
      <div className="tabs">
        {(["fighters", "skills", "emblems", "diamonds"] as Tab[]).map((t) => (
          <button key={t} className={"lvl" + (tab === t ? " on" : "")} style={{ ["--c" as any]: "#e6c26e" }} onClick={() => { setTab(t); setMsg(""); }}>
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {msg && <div className="toast">{msg}</div>}

      {tab === "fighters" && (
        <div className="grid">
          {CHARACTERS.map((ch) => {
            const owned = acc.owns(ch.id);
            return (
              <div key={ch.id} className="item" style={{ borderColor: ch.look.glow }}>
                <b>{ch.look.name}</b>
                <span>{ch.role}</span>
                {owned ? <em>Owned</em> : (
                  <div className="row">
                    <button className="buy gold" onClick={() => run(() => account.buyCharacter(ch.id, "gold"), `${ch.look.name} unlocked!`)}>{CHARACTER_PRICE.gold} gold</button>
                    <button className="buy dia" onClick={() => run(() => account.buyCharacter(ch.id, "diamonds"), `${ch.look.name} unlocked!`)}>{CHARACTER_PRICE.diamonds} diamonds</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {tab === "skills" && (
        <div className="grid">
          {CHARACTERS.map((ch) => {
            const v = Kits.attacks(ch.look.kit, ch.look.element).v;
            const owned = acc.ownsSkill(ch.id);
            return (
              <div key={ch.id} className="item" style={{ borderColor: ch.look.glow }}>
                <div className="item-head"><Icon src={skillIcon(ch.look.kit, ch.look.element, "v")} alt={v.name} size={48} /><b>{v.name}</b></div>
                <span>{ch.look.name}: {v.desc} ({v.cd}s)</span>
                {owned ? <em>Unlocked - equip it in character select</em> : (
                  <div className="row">
                    <button className="buy gold" onClick={() => run(() => account.buySkill(ch.id, "gold"), `${v.name} unlocked!`)}>{SKILL_PRICE.gold} gold</button>
                    <button className="buy dia" onClick={() => run(() => account.buySkill(ch.id, "diamonds"), `${v.name} unlocked!`)}>{SKILL_PRICE.diamonds} diamonds</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {tab === "emblems" && (
        <div className="grid">
          {EMBLEMS.map((e) => {
            const lvl = acc.emblemLevel(e.id);
            const equipped = p.emblem === e.id;
            return (
              <div key={e.id} className={"item" + (equipped ? " equipped" : "")}>
                <div className="item-head"><Icon src={emblemIcon(e.id)} alt={e.name} size={56} /><b>{e.name} <small>Lv {lvl}/{EMBLEM_MAX}</small></b></div>
                <span>Now: {e.desc(lvl)}</span>
                {lvl < EMBLEM_MAX && <span className="next">Next: {e.desc(lvl + 1)}</span>}
                <div className="row">
                  <button className="buy" disabled={equipped} onClick={() => run(() => account.setEmblem(e.id), `${e.name} emblem equipped`)}>{equipped ? "Equipped" : "Equip"}</button>
                  {lvl < EMBLEM_MAX && (
                    <button className="buy gold" onClick={() => run(() => account.upgradeEmblem(e.id), `${e.name} is now level ${lvl + 1}`)}>Upgrade: {emblemCost(lvl)} gold</button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === "diamonds" && (
        <div className="grid">
          <div className="item">
            <div className="item-head"><Diamond size={40} /><b>Watch an ad</b></div>
            <span>+{AD_DIAMONDS} diamonds, up to {ADS_PER_DAY} a day.{adsAreDemo() ? " (Test ad - real ads not set up yet.)" : ""}</span>
            {!acc.signedIn ? <button className="buy" onClick={onAccount}>Sign in to earn diamonds</button>
              : <button className="buy dia" disabled={!adsAvailable() || adT > 0} onClick={watchAd}>{adsAvailable() ? "Watch ad" : "Ads coming soon"}</button>}
          </div>
          {DIAMOND_PACKS.map((d) => (
            <div key={d.id} className="item">
              <div className="item-head"><Diamond size={40} /><b>{d.diamonds} diamonds</b></div>
              <span>Unlock fighters and skills faster.</span>
              <button className="buy dia" onClick={() => acc.signedIn ? run(() => account.buyDiamonds(d.id), "Opening checkout...") : onAccount()}>{d.price}</button>
            </div>
          ))}
        </div>
      )}

      <div className="row bottom-row">
        <button className="big ghost" onClick={onBack}>&lt; Back</button>
      </div>

      {adT > 0 && (
        <div className="ad-overlay">
          <div className="ad-box">
            <b>Test ad</b>
            <span>Your reward arrives in {adT}s</span>
          </div>
        </div>
      )}
    </div>
  );
}
