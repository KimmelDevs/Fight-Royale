// Ranked ladder: 9 ranks, each split into tiers that fill with stars.
// Win a ranked match: +1 star (+1 bonus on every 3rd win in a row). Fill a tier's stars and win
// again to promote. Lose: -1 star; at 0 stars you drop a tier (Bronze and Silver never lose
// stars). Mythic has no tiers: stars just keep counting.
// Progress is saved per browser (localStorage).

export interface RankDef { id: string; name: string; tiers: number; stars: number; protect?: boolean; color: string }

export const RANKS: RankDef[] = [
  { id: "bronze", name: "Bronze", tiers: 3, stars: 3, protect: true, color: "#c98a52" },
  { id: "silver", name: "Silver", tiers: 3, stars: 3, protect: true, color: "#c9d3e6" },
  { id: "gold", name: "Gold", tiers: 3, stars: 4, color: "#ffd34d" },
  { id: "platinum", name: "Platinum", tiers: 4, stars: 4, color: "#7fe0d0" },
  { id: "diamond", name: "Diamond", tiers: 4, stars: 5, color: "#8fd0ff" },
  { id: "master", name: "Master", tiers: 5, stars: 5, color: "#b98cff" },
  { id: "grandmaster", name: "Grandmaster", tiers: 5, stars: 5, color: "#ff7b7b" },
  { id: "legend", name: "Legend", tiers: 5, stars: 5, color: "#ffb347" },
  { id: "mythic", name: "Mythic", tiers: 1, stars: 0, color: "#ff8af0" },
];
const MYTHIC = RANKS.length - 1;
const ROMAN = ["I", "II", "III", "IV", "V"];
const STORE = "fr-rank";

/** rank index, tier (0 = lowest, e.g. Gold III), stars in the tier, plus stats. */
export interface RankState { r: number; t: number; s: number; wins: number; losses: number; streak: number; best: number }

export const freshRank = (): RankState => ({ r: 0, t: 0, s: 0, wins: 0, losses: 0, streak: 0, best: 0 });

export function loadRank(): RankState {
  try {
    const raw = localStorage.getItem(STORE);
    if (raw) return { ...freshRank(), ...JSON.parse(raw) };
  } catch {}
  return freshRank();
}

export function saveRank(st: RankState) {
  try { localStorage.setItem(STORE, JSON.stringify(st)); } catch {}
}

/** "Gold II", "Mythic". Tier I is the highest tier of a rank. */
export function rankLabel(st: RankState) {
  const d = RANKS[st.r];
  return st.r === MYTHIC ? d.name : `${d.name} ${ROMAN[d.tiers - 1 - st.t]}`;
}

/** One number for matchmaking: every star counts the same across the ladder. */
export function rankScore(st: RankState) {
  let total = 0;
  for (let i = 0; i < st.r; i++) total += RANKS[i].tiers * (RANKS[i].stars + 1);
  return total + st.t * (RANKS[st.r].stars + 1) + st.s;
}

/** CPU difficulty (0 Easy .. 3 Master) for a ranked match against the CPU. */
export function cpuLevel(st: RankState) { return st.r <= 1 ? 0 : st.r <= 3 ? 1 : st.r <= 5 ? 2 : 3; }

export interface RankChange { before: RankState; after: RankState; delta: number; note: string }

/** Apply a ranked result and save it. */
export function applyResult(won: boolean): RankChange {
  const before = loadRank();
  const st = { ...before };
  let delta = 0;
  let note = "";
  if (won) {
    st.wins++;
    st.streak = Math.max(st.streak, 0) + 1;
    delta = 1 + (st.streak % 3 === 0 ? 1 : 0);
    if (delta > 1) note = `${st.streak} wins in a row: bonus star!`;
    for (let i = 0; i < delta; i++) addStar(st);
  } else {
    st.losses++;
    st.streak = Math.min(st.streak, 0) - 1;
    if (RANKS[st.r].protect) note = `${RANKS[st.r].name} is protected: no star lost`;
    else { delta = -1; loseStar(st); }
  }
  if (st.r > before.r || (st.r === before.r && st.t > before.t)) note = `Promoted to ${rankLabel(st)}!`;
  else if (st.r < before.r || (st.r === before.r && st.t < before.t)) note = `Dropped to ${rankLabel(st)}`;
  st.best = Math.max(st.best, rankScore(st));
  saveRank(st);
  return { before, after: st, delta, note };
}

function addStar(st: RankState) {
  const d = RANKS[st.r];
  if (st.r === MYTHIC) { st.s++; return; }
  if (st.s < d.stars) { st.s++; return; }
  // Full tier: this win promotes, arriving with one star.
  if (st.t < d.tiers - 1) { st.t++; st.s = 1; }
  else { st.r++; st.t = 0; st.s = st.r === MYTHIC ? 0 : 1; }
}

function loseStar(st: RankState) {
  if (st.s > 0) { st.s--; return; }
  if (st.r === MYTHIC) { st.r--; st.t = RANKS[st.r].tiers - 1; st.s = RANKS[st.r].stars - 1; return; }
  if (st.t > 0) { st.t--; st.s = RANKS[st.r].stars - 1; return; }
  if (st.r > 0 && !RANKS[st.r - 1].protect) { st.r--; st.t = RANKS[st.r].tiers - 1; st.s = RANKS[st.r].stars - 1; }
}

export const rankIcon = (r: number) => `/icons/ranks/${RANKS[r].id}.webp`;
