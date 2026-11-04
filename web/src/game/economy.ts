// Economy rules shared by the UI, the match and (mirrored in SQL) the server.
// Keep these numbers in sync with supabase/migrations/*_economy.sql.

export const START_CHARACTERS = ["aster", "ember", "garrick"];
export const CHARACTER_PRICE = { gold: 5000, diamonds: 250 };
export const SKILL_PRICE = { gold: 2000, diamonds: 100 };
export const WIN_GOLD = 250;
export const MAX_BET = 5000;
export const AD_DIAMONDS = 5;
export const ADS_PER_DAY = 10;

/** Gold per kill in survival; elites pay double. */
export const MOB_GOLD: Record<string, number> = {
  slime: 2, bat: 2, goblin: 4, archer: 4, imp: 6, wraith: 6, brute: 12, golem: 150,
};

export const DIAMOND_PACKS = [
  { id: "small", diamonds: 100, price: "$0.99" },
  { id: "medium", diamonds: 550, price: "$4.99" },
  { id: "large", diamonds: 1200, price: "$9.99" },
];

export interface EmblemBonus { dmg: number; hp: number; guard: number; crit: number; cd: number; speed: number }

/** Emblem sets, like MLBB: equip one, upgrade it with gold (max level 10). */
export const EMBLEMS: { id: string; name: string; desc: (lvl: number) => string; bonus: (lvl: number) => Partial<EmblemBonus> }[] = [
  { id: "fighter", name: "Fighter", desc: (l) => `+${2 * l}% damage`, bonus: (l) => ({ dmg: 0.02 * l }) },
  { id: "tank", name: "Tank", desc: (l) => `+${3 * l}% HP and guard`, bonus: (l) => ({ hp: 0.03 * l, guard: 0.03 * l }) },
  { id: "assassin", name: "Assassin", desc: (l) => `+${(1.5 * l).toFixed(1)}% critical chance`, bonus: (l) => ({ crit: 0.015 * l }) },
  { id: "mage", name: "Mage", desc: (l) => `Skills recharge ${2 * l}% faster`, bonus: (l) => ({ cd: 0.02 * l }) },
  { id: "swift", name: "Swift", desc: (l) => `+${(1.5 * l).toFixed(1)}% move speed`, bonus: (l) => ({ speed: 0.015 * l }) },
];
export const EMBLEM_MAX = 10;
export const emblemCost = (level: number) => 300 * level;

export function emblemBonus(id: string, level: number): EmblemBonus {
  const e = EMBLEMS.find((x) => x.id === id) ?? EMBLEMS[0];
  return { dmg: 0, hp: 0, guard: 0, crit: 0, cd: 0, speed: 0, ...e.bonus(Math.max(1, Math.min(level, EMBLEM_MAX))) };
}

export const DEFAULT_LOADOUT = ["z", "x", "c"];

export interface Profile {
  username: string;
  gold: number;
  diamonds: number;
  characters: string[];
  skills: string[];
  loadouts: Record<string, string[]>;
  emblems: Record<string, number>;
  emblem: string;
}

export const guestProfile = (): Profile => ({
  username: "Guest", gold: 0, diamonds: 0, characters: [...START_CHARACTERS], skills: [],
  loadouts: {}, emblems: {}, emblem: "fighter",
});
