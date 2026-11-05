// The playable cast. Each entry's `look` drives both the model (colors, hair, hat, outfit,
// weapon) and the combat kit.

export interface Look {
  name: string; kit: string; element: string; outfit: string; style: string; hat: string;
  hair: string; hair_shade: string; iris_top: string; iris_bottom: string; eye_dark: string;
  tunic: string; band: string; pants: string; boots: string; metal: string; trim: string;
  cape: string; cape_bottom: string; glow: string; shield: string; emblem: string;
  /** Body type: "m" or "f" (proportions, eye size). */
  body?: "m" | "f";
  /** VRoid VRM body in /models/<vrm>.vrm; replaces the procedural body once loaded. */
  vrm?: string;
  ears?: boolean; cloak?: boolean;
}

export interface Character {
  id: string; title: string; role: string; desc: string;
  stats: { power: number; speed: number; range: number; defense: number };
  look: Look;
}

export const CHARACTERS: Character[] = [
  { id: "aster", title: "Azure Knight", role: "Knight - Sword & Shield",
    desc: "A steady guardian. Big guard, heavy sword swings, a shield that shrugs off blows.",
    stats: { power: 4, speed: 3, range: 2, defense: 5 },
    look: { name: "Aster", body: "m", vrm: "aster", kit: "knight", element: "light", outfit: "knight", style: "short", hat: "none",
      hair: "#e6edf8", hair_shade: "#b3c2f2", iris_top: "#1c6fd1", iris_bottom: "#7fe3ff", eye_dark: "#152a5e",
      tunic: "#2b4fa8", band: "#f4f6ff", pants: "#1d2442", boots: "#5a3a2a", metal: "#d5deef", trim: "#e6c26e",
      cape: "#3d6fd6", cape_bottom: "#9fd8ff", glow: "#66d9ff", shield: "#2b4fa8", emblem: "#f4f6ff" } },
  { id: "vesper", title: "Crimson Duelist", role: "Knight - Sword & Shield",
    desc: "A ruthless duelist who trades a little defense for relentless pressure.",
    stats: { power: 5, speed: 3, range: 2, defense: 4 },
    look: { name: "Vesper", body: "f", vrm: "vesper", kit: "knight", element: "flame", outfit: "knight", style: "ponytail", hat: "none",
      hair: "#c22a3e", hair_shade: "#bf9ed1", iris_top: "#a3122b", iris_bottom: "#ffb347", eye_dark: "#3a0d18",
      tunic: "#8f1d2c", band: "#221827", pants: "#221827", boots: "#3a2420", metal: "#4a4256", trim: "#e6b45c",
      cape: "#221827", cape_bottom: "#8f1d2c", glow: "#ff7333", shield: "#221827", emblem: "#c4283c" } },
  { id: "garrick", title: "Iron Vanguard", role: "Warrior - Greatsword",
    desc: "Swings a slab of steel. Slow, but every hit lands like a falling tower.",
    stats: { power: 5, speed: 2, range: 3, defense: 5 },
    look: { name: "Garrick", body: "m", vrm: "garrick", kit: "greatsword", element: "earth", outfit: "knight", style: "short", hat: "none",
      hair: "#c98a4b", hair_shade: "#c7a9a6", iris_top: "#5b3d1e", iris_bottom: "#e0b064", eye_dark: "#2a1a0e",
      tunic: "#3f5a3a", band: "#e9e2cf", pants: "#2b2a24", boots: "#4a3423", metal: "#b8bcc8", trim: "#d4a64a",
      cape: "#6b8f4e", cape_bottom: "#c6d98a", glow: "#ffcc59", shield: "#3f5a3a", emblem: "#e9e2cf" } },
  { id: "kaede", title: "Moonlit Blade", role: "Samurai - Katana",
    desc: "Lightning-quick draws, a counter stance that punishes, and a storm of cuts.",
    stats: { power: 4, speed: 4, range: 3, defense: 3 },
    look: { name: "Kaede", body: "f", vrm: "kaede", kit: "katana", element: "moon", outfit: "samurai", style: "ponytail", hat: "none",
      hair: "#1f2235", hair_shade: "#a9a6d6", iris_top: "#b3243a", iris_bottom: "#ff9aa8", eye_dark: "#2a0d16",
      tunic: "#f2efe8", band: "#b3243a", pants: "#1f2235", boots: "#1f2235", metal: "#cfd4e6", trim: "#e6c26e",
      cape: "#2a2d4a", cape_bottom: "#4a5080", glow: "#ff5a73", shield: "#2a2d4a", emblem: "#b3243a" } },
  { id: "ember", title: "Flame Witch", role: "Mage - Fire",
    desc: "Fireballs at range, explosive charged blasts, and a meteor to end the fight.",
    stats: { power: 5, speed: 3, range: 5, defense: 2 },
    look: { name: "Ember", body: "f", vrm: "ember", kit: "mage", element: "fire", outfit: "mage", style: "twintails", hat: "witch",
      hair: "#ff7448", hair_shade: "#d99eb3", iris_top: "#c0392b", iris_bottom: "#ffd166", eye_dark: "#4a1410",
      tunic: "#7a1f1f", band: "#fff2e0", pants: "#2a1414", boots: "#3a1a12", metal: "#c9b8a6", trim: "#e6c26e",
      cape: "#c0392b", cape_bottom: "#ffb347", glow: "#ff8026", shield: "#7a1f1f", emblem: "#c0392b" } },
  { id: "marina", title: "Tide Sorceress", role: "Mage - Water",
    desc: "Controls space with water: bubble wards, geyser rings, and a crushing ocean sphere.",
    stats: { power: 4, speed: 3, range: 5, defense: 3 },
    look: { name: "Marina", body: "f", vrm: "marina", kit: "mage", element: "water", outfit: "mage", style: "bob", hat: "beret",
      hair: "#8cc3f0", hair_shade: "#adbdf2", iris_top: "#1f6fd0", iris_bottom: "#73dcf5", eye_dark: "#1a2a66",
      tunic: "#23307a", band: "#f6f7ff", pants: "#f6f7ff", boots: "#23307a", metal: "#d5deef", trim: "#e6c26e",
      cape: "#4f97dc", cape_bottom: "#a3e6f0", glow: "#59bfff", shield: "#23307a", emblem: "#23307a" } },
  { id: "nyx", title: "Shadow Blade", role: "Assassin - Twin Daggers",
    desc: "Blinding speed and a four-hit flurry. Fragile, but almost impossible to pin down.",
    stats: { power: 4, speed: 5, range: 2, defense: 1 },
    look: { name: "Nyx", body: "f", vrm: "nyx", kit: "assassin", element: "shadow", outfit: "assassin", style: "ponytail", hat: "hood",
      hair: "#3a3550", hair_shade: "#b3a8e6", iris_top: "#7b2cbf", iris_bottom: "#e0aaff", eye_dark: "#1d1030",
      tunic: "#1f1b2e", band: "#6b3fa0", pants: "#17141f", boots: "#17141f", metal: "#8f8aa8", trim: "#c9a7ff",
      cape: "#6b3fa0", cape_bottom: "#b38cff", glow: "#bf66ff", shield: "#1f1b2e", emblem: "#c9a7ff" } },
  { id: "rook", title: "Iron Fist", role: "Brawler - Knuckles",
    desc: "Closes the gap and never stops punching. Five-hit combos and a crater-making slam.",
    stats: { power: 4, speed: 5, range: 1, defense: 3 },
    look: { name: "Rook", body: "m", vrm: "rook", kit: "knuckles", element: "force", outfit: "brawler", style: "short", hat: "none",
      hair: "#ff8a3d", hair_shade: "#e0a6a6", iris_top: "#b34a12", iris_bottom: "#ffd27a", eye_dark: "#331405",
      tunic: "#c8312c", band: "#f5d06b", pants: "#2a2a33", boots: "#2a2a33", metal: "#e0c066", trim: "#f5d06b",
      cape: "#c8312c", cape_bottom: "#ff8a3d", glow: "#ffbf4d", shield: "#c8312c", emblem: "#f5d06b" } },
  { id: "gale", title: "Wind Dancer", role: "Brawler - Wind",
    desc: "Fights on the wind. Quick wind punches on the ground; in the air every skill becomes a dive that smashes the ground. Double jumps.",
    stats: { power: 4, speed: 5, range: 2, defense: 2 },
    look: { name: "Gale", body: "m", vrm: "gale", kit: "wind", element: "wind", outfit: "brawler", style: "short", hat: "none",
      hair: "#2f7fd8", hair_shade: "#9fc8f0", iris_top: "#1f6fb0", iris_bottom: "#8fe8ff", eye_dark: "#0e2a44",
      tunic: "#7ad6c8", band: "#8a5a3a", pants: "#1e1e24", boots: "#1e1e24", metal: "#c8e8e0", trim: "#bff7e8",
      cape: "#7ad6c8", cape_bottom: "#9dffdc", glow: "#7dffd6", shield: "#7ad6c8", emblem: "#bff7e8" } },
  { id: "bob", title: "Mad Bomber", role: "Bomber - Explosives",
    desc: "Lobs firecrackers, plants mines and parks a powder keg he can blow up whenever he likes. Keep your distance from his traps.",
    stats: { power: 4, speed: 2, range: 4, defense: 2 },
    look: { name: "Bob", body: "m", vrm: "bob", kit: "bomb", element: "blast", outfit: "brawler", style: "short", hat: "none",
      hair: "#3a2a1a", hair_shade: "#b89a7a", iris_top: "#b34a12", iris_bottom: "#ffb347", eye_dark: "#331405",
      tunic: "#c8641e", band: "#2a2a30", pants: "#2a2a30", boots: "#2a2a30", metal: "#9a9aa8", trim: "#ffb347",
      cape: "#c8641e", cape_bottom: "#ffb347", glow: "#ff9a3d", shield: "#c8641e", emblem: "#ffb347" } },
  { id: "kira", title: "Tempest Kicker", role: "Martial Artist - Kicks",
    desc: "Fights with her legs: snap kicks, roundhouses, an axe kick and a flying kick, all lightning fast.",
    stats: { power: 4, speed: 5, range: 2, defense: 3 },
    look: { name: "Kira", body: "f", vrm: "kira", kit: "kicks", element: "chi", outfit: "martial", style: "ponytail", hat: "headband",
      hair: "#2a2420", hair_shade: "#b8a8c8", iris_top: "#16736b", iris_bottom: "#7af0d6", eye_dark: "#0e2a28",
      tunic: "#f2f0ea", band: "#1f6f6b", pants: "#22313a", boots: "#e9d8c8", metal: "#c9d6d6", trim: "#e6c26e",
      cape: "#1f6f6b", cape_bottom: "#4dbfae", glow: "#4dffd2", shield: "#22313a", emblem: "#1f6f6b" } },
  { id: "raven", title: "Hex Weaver", role: "Mage - Electric",
    desc: "A dark witch who bends green lightning to her will.",
    stats: { power: 5, speed: 3, range: 5, defense: 2 },
    look: { name: "Raven", body: "f", vrm: "raven", kit: "mage", element: "electric", outfit: "mage", style: "bob", hat: "witch",
      hair: "#2a2a3a", hair_shade: "#a8a8c8", iris_top: "#1aa874", iris_bottom: "#5dffc0", eye_dark: "#0a2a1a",
      tunic: "#1a1a2a", band: "#e8e8f0", pants: "#1a1a2a", boots: "#1a1a2a", metal: "#c8c8d8", trim: "#9a7aff",
      cape: "#3a2a5a", cape_bottom: "#3dffb0", glow: "#5dffc0", shield: "#1a1a2a", emblem: "#3a2a5a" } },
  { id: "ash", title: "Crimson Hunter", role: "Archer - Longbow",
    desc: "A silent hunter in grey whose arrows never miss twice.",
    stats: { power: 5, speed: 4, range: 5, defense: 1 },
    look: { name: "Ash", body: "m", vrm: "ash", kit: "bow", element: "blood", outfit: "assassin", style: "short", hat: "none", cloak: true,
      hair: "#b8bcc8", hair_shade: "#a8a8c0", iris_top: "#b01a2a", iris_bottom: "#ff7a7a", eye_dark: "#2a0508",
      tunic: "#2a2a30", band: "#8a1a24", pants: "#1e1e24", boots: "#1e1e24", metal: "#a8a8b8", trim: "#c8343e",
      cape: "#3a3a44", cape_bottom: "#8a2a2a", glow: "#ff4d4d", shield: "#2a2a30", emblem: "#c8343e" } },
];

export function resolveEnemy(player: number, pick: number): number {
  if (pick >= 0) return pick;
  const choices = CHARACTERS.map((_, i) => i).filter((i) => i !== player);
  return choices[Math.floor(Math.random() * choices.length)];
}
