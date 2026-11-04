// Regenerates the "Balance reference" section of README.md from the live game data
// (roster.ts, kits.ts, economy.ts), so the tables always match the code.
// Run: npm run balance
import { readFileSync, writeFileSync } from "node:fs";
import { CHARACTERS } from "../src/game/roster";
import * as Kits from "../src/game/kits";
import type { Attack } from "../src/game/kits";
import { EMBLEMS, START_CHARACTERS, CHARACTER_PRICE, SKILL_PRICE } from "../src/game/economy";

const README = new URL("../README.md", import.meta.url);
const START = "<!-- BALANCE:START -->";
const END = "<!-- BALANCE:END -->";

const n = (v: number, d = 2) => {
  if (Number.isInteger(v)) return String(v);
  const t = v.toFixed(d);
  return t.includes(".") ? t.replace(/0+$/, "").replace(/\.$/, "") : t;
};
const kits = [...new Set(CHARACTERS.map((c) => c.look.kit))];

/** Short "special" notes for an attack (only the fields that matter for its type). */
function extra(a: Attack): string {
  const x: string[] = [];
  if (a.type === "projectile") {
    x.push(`${a.count} x proj, speed ${n(a.speed)}`);
    if (a.spread) x.push(`spread ${n(a.spread)} rad`);
    if (a.pierce) x.push("pierces");
  }
  if (a.type === "strike") {
    x.push(`${a.at === "self" ? "around self" : "at target"}, radius ${n(a.radius)}, lands after ${n(a.delay)}s`);
    if (a.repeat > 1) x.push(`x${a.repeat} every ${n(a.interval)}s`);
  }
  if (a.type === "buff") x.push(`${a.mode}${a.duration ? ` ${n(a.duration)}s` : ""}`);
  if (a.type === "blink") x.push(`blink ${a.mode}`);
  if (a.type === "melee") x.push(`reach ${n(a.reach)}`);
  if (a.lunge) x.push(`lunge ${n(a.lunge)}`);
  if (a.self_jump) x.push(`self-launch ${n(a.self_jump)}`);
  if (a.heavy) x.push("heavy");
  if (a.stagger) x.push("staggers");
  return x.join(", ");
}

const row = (key: string, a: Attack) => {
  const hits = a.type !== "buff" && a.type !== "blink"; // buffs and blinks deal no damage
  const v = (x: number) => (hits ? n(x) : "-");
  return `| ${key} | ${a.name || "-"} | ${a.type} | ${v(a.dmg)} | ${v(a.guard)} | ${n(a.wind)} / ${n(a.active)} / ${n(a.recover)} | ${v(a.knock)} | ${v(a.stun)} | ${a.cd ? n(a.cd) + "s" : "-"} | ${extra(a)} |`;
};
const HEAD = "| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |\n|---|---|---|---|---|---|---|---|---|---|";

const out: string[] = [];
out.push(START);
out.push("_Generated from the game code by `npm run balance` — edit the code, then re-run; don't edit these tables by hand._\n");

// ---- Characters
out.push("### Characters\n");
out.push("| Fighter | Title | Role | Kit | Element | Body | Hair | Hair shade | Eyes (top / bottom) | Glow | Starter |");
out.push("|---|---|---|---|---|---|---|---|---|---|---|");
for (const c of CHARACTERS) {
  const L = c.look;
  out.push(`| ${L.name} | ${c.title} | ${c.role} | ${L.kit} | ${L.element} | ${L.body === "m" ? "male" : "female"} | \`${L.hair}\` | \`${L.hair_shade}\` | \`${L.iris_top}\` / \`${L.iris_bottom}\` | \`${L.glow}\` | ${START_CHARACTERS.includes(c.id) ? "yes" : "-"} |`);
}

// ---- Kit stats
out.push("\n### Kit stats (shared by every fighter on that kit)\n");
out.push("| Kit | HP | Guard | Run speed | Walk speed | Parry window (s) | Jump | Fighters | Light combo dmg | Combo time (s) | Combo DPS | Charged dmg (x1.5 at full) |");
out.push("|---|---|---|---|---|---|---|---|---|---|---|---|");
for (const k of kits) {
  const st = Kits.STATS[k];
  const any = CHARACTERS.find((c) => c.look.kit === k)!;
  const at = Kits.attacks(k, any.look.element);
  const lights = Object.keys(at).filter((x) => /^l\d$/.test(x)).sort();
  const dmg = lights.reduce((s, x) => s + at[x].dmg * Math.max(at[x].count, 1), 0);
  const time = lights.reduce((s, x) => s + at[x].wind + at[x].active + at[x].recover, 0);
  const who = CHARACTERS.filter((c) => c.look.kit === k).map((c) => c.look.name).join(", ");
  out.push(`| ${k} | ${st.hp} | ${st.guard} | ${n(st.move)} | ${n(st.walk)} | ${n(st.parry)} | ${n(st.jump)} | ${who} | ${n(dmg, 0)} | ${n(time)} | ${n(dmg / time, 0)} | ${n(at.heavy.dmg)} -> ${n(at.heavy.dmg * 1.5, 0)} |`);
}

// ---- Normal attacks per kit
out.push("\n### Normal attacks per kit\n");
out.push("`l1`..`l5` = tap combo (chains while you keep tapping), `heavy` = hold-to-charge (up to 1.5x damage at full charge).\n");
for (const k of kits) {
  const any = CHARACTERS.find((c) => c.look.kit === k)!;
  const at = Kits.attacks(k, any.look.element);
  out.push(`#### ${k}\n`);
  out.push(HEAD);
  for (const key of [...Object.keys(at).filter((x) => /^l\d$/.test(x)).sort(), "heavy"]) out.push(row(key, at[key]));
  out.push("");
}

// ---- Skills per character
out.push("### Skills per fighter\n");
out.push(`Z / X / C are the default loadout; V is the locked bonus skill (unlock: ${SKILL_PRICE.gold} gold or ${SKILL_PRICE.diamonds} diamonds). Any 3 of the 4 can be slotted.\n`);
for (const c of CHARACTERS) {
  const at = Kits.attacks(c.look.kit, c.look.element);
  out.push(`#### ${c.look.name} (${c.look.kit}, ${c.look.element})\n`);
  out.push(HEAD);
  for (const key of ["z", "x", "c", "v"]) out.push(row(key.toUpperCase(), at[key]));
  out.push("");
}

// ---- Emblems
out.push("### Emblems\n");
out.push("| Emblem | Level 1 | Level 5 | Level 10 |\n|---|---|---|---|");
for (const e of EMBLEMS) out.push(`| ${e.name} | ${e.desc(1)} | ${e.desc(5)} | ${e.desc(10)} |`);
out.push(`\nUnlocking a fighter costs ${CHARACTER_PRICE.gold} gold or ${CHARACTER_PRICE.diamonds} diamonds.`);
out.push(END);

const md = readFileSync(README, "utf8");
const block = out.join("\n");
const next = md.includes(START) ? md.replace(new RegExp(`${START}[\\s\\S]*?${END}`), block) : md.trimEnd() + "\n\n" + block + "\n";
writeFileSync(README, next);
console.log("README balance section updated:", CHARACTERS.length, "fighters,", kits.length, "kits");
