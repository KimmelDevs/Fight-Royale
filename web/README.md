# Fight Royale (web)

Anime cel-shaded arena fighter that runs in the browser: duels vs CPU, solo survival, and
online co-op survival / PvP duels with friends. Built with Next.js + three.js.

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Deploy to Vercel

Either:

- **CLI:** run `npx vercel` inside this `web` folder and follow the prompts, or
- **GitHub:** push the repo, import it on vercel.com, and set **Root Directory** to `web`.

No environment variables or servers are needed.

## How online play works

The host's browser runs the match; friends join with the 5-letter room code. Browsers connect
directly over WebRTC using PeerJS, whose free public broker (0.peerjs.com) only introduces the
players. Nothing to host besides the static site.

Limits: a few strict networks (some corporate or mobile carriers) block direct WebRTC
connections; those players can't join without a TURN relay.

## Combat rules (for balancing)

All numbers live in code; the tables in **Balance reference** below are generated from it.

**Damage.** A hit deals the attack's `Dmg` x the attacker's power:
- **Charged attack** (`heavy`): hold attack for 0.22 s to start charging; power grows to **1.5x** at full charge (0.9 s).
- **Crits**: 20% base chance (+ Assassin emblem), **x1.6** damage.
- **Fighter emblem** adds damage %, **Berserk** buff (greatsword V) is **x1.2** for 6 s.
- Survival perks stack on top (+20% damage, crit, lifesteal...).

**Timing.** Every attack has three phases: **wind** (startup, can be read and blocked), **active** (the hit lands at the start of this window), **recover** (endlag). Lower total time = faster / safer. Tap attacks chain into the next `l` step if you tap again during recovery (combo window 0.45 s).

**Defense.**
- **Block** (hold right click): the hit's `Guard dmg` is taken from your **guard** bar instead of HP, plus a small push back. Guard refills at 30/s after 1 s without blocking.
- **Guard break**: if guard hits 0 you take 40% of the damage and are **staggered for 0.85 s**.
- **Parry**: a block started within the kit's **parry window** before the hit takes no guard damage, restores 20 guard and **staggers the attacker for 0.95 s**.
- **Clash**: two melee hits that meet at the same moment knock both fighters back.

**Hit reactions.** `Stun` = how long the target can't act. `Knock` = push-back speed. `heavy` / `staggers` attacks put the target in the longer stagger state.
- **One stun per skill**: a multi-hit skill (Thousand Cuts, Hundred Kicks, Whirlwind...) stuns once; later ticks only deal damage.
- **Diminishing stun**: each new stun within 3 s of the last is **x0.6** shorter (0.3 s, then 0.18 s, ... minimum 0.1 s), so no fighter can be stun-locked.
- **Status effects** (`src/game/status.ts`): element skills leave an effect on a clean hit (not when blocked, parried or absorbed). The power number is damage per second, or a multiplier.
  - **Burn** (Ember: all skills; Vesper: Blade Wave, Judgment): 4 s of fire damage.
  - **Poison** (Nyx: Shuriken Fan, Phantom Rush, Venom Fan): 10 dmg/s for 6 s, stacks up to 3 times (each blade adds a stack).
  - **Bleed** (Kaede: Crescent Wind, Thousand Cuts, Iaido Flash; Ash: Arrow Rain, Hunter's Snare): 4 s, x1.5 while the target is moving.
  - **Paralyze** (Raven: Chain Lightning, Thunderstorm, Static Field): 2.5 s at 60% speed, jolted (0.25 s interrupt) every second.
  - **Slow** (Marina: Tidal Ring, Ocean Requiem; Garrick: Ground Slam, Titan Cleave): move speed x0.6 / x0.65.
  - **Weaken** (Aster: Blade Wave, Judgment): deals x0.8 damage for 4 s.
  - Reapplying refreshes the duration. Effects end on KO and also work on survival mobs (damage-over-time kills still give gold).
- **Shield Bash** (knights) stuns for 1 s.

**Skills.** Z / X / C (any 3 of the kit's 4, V is unlocked in the Shop) each have a cooldown (`CD`). The Mage emblem shortens cooldowns. Skill types:
- **melee**: hits everything in front within `reach`.
- **projectile**: `count` shots with `spread`, `speed`; `pierces` goes through enemies.
- **strike**: area hit at the target (or around you) after a telegraph `delay`, possibly repeated. Jumping avoids ground strikes.
- **buff**: ward (absorb all hits; **2 s in PvP**, full duration in survival), heal (**16% HP in PvP**, 25% in survival), rage (+20% dmg), counter stance (auto-counter the next hit for 180 dmg).
- **blink**: teleport behind the enemy or back away.

**Ranged rest.** After the last hit of the tap combo, normal attacks rest **1.2 s (mage)** / **1.3 s (bow)** (shown on the ATK slot).

**Dash.** Double-tap a direction: 0.3 s dash, **0.15 s** of invulnerability at the start, **3 s** cooldown.

**Platform Brawl (hidden for now).** Damage becomes %: `% = Dmg x 0.07`. Launch speed = `2.5 + Knock x 0.5 + % x (0.06 + hit% x 0.006)`, so knockback grows with % taken. 3 stocks.

**Economy.** Win a duel or team battle: +250 gold. Survival pays per kill (slime 2 ... golem boss 150, elites x2).

## Code map

- `src/game/kits.ts` - stats, attacks, skills and poses per class (**tune damage/cooldowns here**, then `npm run balance`)
- `src/game/roster.ts` - the 17 characters, their looks (hair/eye colors) and which VRoid model they use
- `src/game/vrm.ts` - VRoid (VRM) bodies: retargeting, natural motion, IK for shields and two-handed weapons
- `src/game/economy.ts` - prices, rewards, starting fighters, emblems
- `src/game/model.ts` - procedural cel-shaded character models
- `src/game/mobs.ts` - survival enemies, boss, and wave composition
- `src/game/game.ts` - match rules, combat resolution, waves, perks, network sync, camera
- `src/game/ai.ts` - duel CPU with 4 difficulty levels
- `src/game/net.ts` - PeerJS host/join
- `src/ui/` - React menus, character select, lobby and HUD

## Balance reference

<!-- BALANCE:START -->
_Generated from the game code by `npm run balance` — edit the code, then re-run; don't edit these tables by hand._

### Characters

| Fighter | Title | Role | Kit | Element | Body | Hair | Hair shade | Eyes (top / bottom) | Glow | Starter |
|---|---|---|---|---|---|---|---|---|---|---|
| Aster | Azure Knight | Knight - Sword & Shield | knight | light | male | `#e6edf8` | `#b3c2f2` | `#1c6fd1` / `#7fe3ff` | `#66d9ff` | yes |
| Vesper | Crimson Duelist | Knight - Sword & Shield | knight | flame | female | `#c22a3e` | `#bf9ed1` | `#a3122b` / `#ffb347` | `#ff7333` | - |
| Garrick | Iron Vanguard | Warrior - Greatsword | greatsword | earth | male | `#c98a4b` | `#c7a9a6` | `#5b3d1e` / `#e0b064` | `#ffcc59` | yes |
| Kaede | Moonlit Blade | Samurai - Katana | katana | moon | female | `#1f2235` | `#a9a6d6` | `#b3243a` / `#ff9aa8` | `#ff5a73` | - |
| Ember | Flame Witch | Mage - Fire | mage | fire | female | `#ff7448` | `#d99eb3` | `#c0392b` / `#ffd166` | `#ff8026` | yes |
| Marina | Tide Sorceress | Mage - Water | mage | water | female | `#8cc3f0` | `#adbdf2` | `#1f6fd0` / `#73dcf5` | `#59bfff` | - |
| Nyx | Shadow Blade | Assassin - Twin Daggers | assassin | shadow | female | `#3a3550` | `#b3a8e6` | `#7b2cbf` / `#e0aaff` | `#bf66ff` | - |
| Rook | Iron Fist | Brawler - Knuckles | knuckles | force | male | `#ff8a3d` | `#e0a6a6` | `#b34a12` / `#ffd27a` | `#ffbf4d` | - |
| Kira | Tempest Kicker | Martial Artist - Kicks | kicks | chi | female | `#2a2420` | `#b8a8c8` | `#16736b` / `#7af0d6` | `#4dffd2` | - |
| Raven | Hex Weaver | Mage - Electric | mage | electric | female | `#2a2a3a` | `#a8a8c8` | `#1aa874` / `#5dffc0` | `#5dffc0` | - |
| Ash | Crimson Hunter | Archer - Longbow | bow | blood | male | `#b8bcc8` | `#a8a8c0` | `#b01a2a` / `#ff7a7a` | `#ff4d4d` | - |

### Kit stats (shared by every fighter on that kit)

| Kit | HP | Guard | Run speed | Walk speed | Parry window (s) | Jump | Fighters | Light combo dmg | Combo time (s) | Combo DPS | Charged dmg (x1.5 at full) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| knight | 2500 | 100 | 3.2 | 2.6 | 0.16 | 7 | Aster, Vesper | 244 | 1.63 | 150 | 190 -> 285 |
| greatsword | 2750 | 120 | 2.9 | 2.3 | 0.14 | 6.5 | Garrick | 420 | 2.56 | 164 | 320 -> 480 |
| katana | 2200 | 80 | 3.8 | 3 | 0.2 | 7.5 | Kaede | 243 | 1.32 | 184 | 230 -> 345 |
| mage | 2100 | 80 | 3.4 | 2.6 | 0.16 | 7 | Ember, Marina, Raven | 241 | 1.67 | 144 | 210 -> 315 |
| assassin | 2000 | 60 | 4.2 | 3.4 | 0.22 | 8.2 | Nyx | 219 | 1.54 | 142 | 170 -> 255 |
| knuckles | 2300 | 90 | 4 | 3.2 | 0.2 | 8 | Rook | 290 | 1.67 | 174 | 220 -> 330 |
| kicks | 2300 | 85 | 4.1 | 3.2 | 0.2 | 8.6 | Kira | 279 | 1.69 | 165 | 230 -> 345 |
| bow | 2000 | 60 | 3.6 | 2.6 | 0.16 | 7.5 | Ash | 260 | 1.51 | 172 | 260 -> 390 |

### Normal attacks per kit

`l1`..`l5` = tap combo (chains while you keep tapping), `heavy` = hold-to-charge (up to 1.5x damage at full charge).

#### knight

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | melee | 62 | 18 | 0.14 / 0.08 / 0.24 | 2 | 0.32 | - | reach 1.75, lunge 2.4 |
| l2 | - | melee | 70 | 20 | 0.12 / 0.08 / 0.26 | 2 | 0.32 | - | reach 1.75, lunge 2.2 |
| l3 | - | melee | 112 | 30 | 0.2 / 0.09 / 0.42 | 4.5 | 0.5 | - | reach 1.85, lunge 3 |
| heavy | - | melee | 190 | 55 | 0.12 / 0.1 / 0.5 | 6 | 0.7 | - | reach 2, lunge 5, heavy |

#### greatsword

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | melee | 110 | 32 | 0.26 / 0.1 / 0.38 | 3 | 0.42 | - | reach 2.2, lunge 2 |
| l2 | - | melee | 120 | 34 | 0.24 / 0.1 / 0.4 | 3 | 0.42 | - | reach 2.2, lunge 2 |
| l3 | - | melee | 190 | 50 | 0.36 / 0.12 / 0.6 | 6 | 0.6 | - | reach 2.3, lunge 2.5, staggers |
| heavy | - | melee | 320 | 80 | 0.18 / 0.14 / 0.7 | 8 | 0.9 | - | reach 2.5, lunge 4, heavy |

#### katana

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | melee | 64 | 18 | 0.1 / 0.07 / 0.2 | 1.6 | 0.3 | - | reach 1.85, lunge 3 |
| l2 | - | melee | 69 | 18 | 0.1 / 0.07 / 0.2 | 1.6 | 0.3 | - | reach 1.85, lunge 3 |
| l3 | - | melee | 110 | 30 | 0.14 / 0.08 / 0.36 | 4 | 0.5 | - | reach 1.95, lunge 3.5 |
| heavy | - | melee | 230 | 55 | 0.16 / 0.14 / 0.5 | 5 | 0.75 | - | reach 2.2, lunge 8, heavy |

#### mage

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | projectile | 55 | 15 | 0.16 / 0.05 / 0.26 | 1.6 | 0.28 | - | 1 x proj, speed 15 |
| l2 | - | projectile | 60 | 15 | 0.16 / 0.05 / 0.28 | 1.8 | 0.3 | - | 1 x proj, speed 15 |
| l3 | - | projectile | 42 | 14 | 0.24 / 0.05 / 0.42 | 3 | 0.4 | - | 3 x proj, speed 15, spread 0.22 rad |
| heavy | - | strike | 210 | 60 | 0.15 / 0.05 / 0.55 | 6 | 0.7 | - | at target, radius 1.6, lands after 0.5s, heavy |

#### assassin

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | melee | 41 | 10 | 0.08 / 0.06 / 0.16 | 1.2 | 0.26 | - | reach 1.55, lunge 3 |
| l2 | - | melee | 41 | 10 | 0.08 / 0.06 / 0.16 | 1.2 | 0.26 | - | reach 1.55, lunge 3 |
| l3 | - | melee | 51 | 12 | 0.1 / 0.06 / 0.18 | 1.5 | 0.28 | - | reach 1.7, lunge 4 |
| l4 | - | melee | 86 | 22 | 0.16 / 0.08 / 0.36 | 4 | 0.45 | - | reach 1.7, lunge 3 |
| heavy | - | melee | 170 | 45 | 0.12 / 0.16 / 0.5 | 5 | 0.7 | - | reach 2, lunge 7, heavy |

#### knuckles

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | melee | 40 | 10 | 0.06 / 0.05 / 0.12 | 1 | 0.24 | - | reach 1.35, lunge 3 |
| l2 | - | melee | 40 | 10 | 0.06 / 0.05 / 0.12 | 1 | 0.24 | - | reach 1.35, lunge 3 |
| l3 | - | melee | 55 | 14 | 0.09 / 0.06 / 0.16 | 1.4 | 0.28 | - | reach 1.4, lunge 3 |
| l4 | - | melee | 60 | 16 | 0.1 / 0.06 / 0.18 | 1.6 | 0.3 | - | reach 1.4, lunge 2.5 |
| l5 | - | melee | 95 | 26 | 0.14 / 0.08 / 0.34 | 4 | 0.45 | - | reach 1.5, lunge 4 |
| heavy | - | melee | 220 | 55 | 0.14 / 0.12 / 0.5 | 6 | 0.8 | - | reach 1.6, lunge 3, self-launch 5, heavy |

#### kicks

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | melee | 46 | 12 | 0.08 / 0.06 / 0.16 | 1.2 | 0.26 | - | reach 1.65, lunge 3 |
| l2 | - | melee | 56 | 14 | 0.1 / 0.07 / 0.18 | 1.6 | 0.28 | - | reach 1.75, lunge 3 |
| l3 | - | melee | 72 | 18 | 0.12 / 0.08 / 0.2 | 2.2 | 0.32 | - | reach 1.85, lunge 3.5 |
| l4 | - | melee | 105 | 30 | 0.18 / 0.08 / 0.38 | 4.5 | 0.5 | - | reach 1.8, lunge 2.5, staggers |
| heavy | - | melee | 230 | 55 | 0.12 / 0.16 / 0.5 | 6.5 | 0.8 | - | reach 2, lunge 7, self-launch 4, heavy |

#### bow

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| l1 | - | projectile | 60 | 14 | 0.16 / 0.05 / 0.22 | 1.4 | 0.28 | - | 1 x proj, speed 28 |
| l2 | - | projectile | 62 | 14 | 0.16 / 0.05 / 0.22 | 1.4 | 0.28 | - | 1 x proj, speed 28 |
| l3 | - | projectile | 46 | 12 | 0.22 / 0.05 / 0.38 | 2.5 | 0.35 | - | 3 x proj, speed 28, spread 0.12 rad |
| heavy | - | projectile | 260 | 60 | 0.1 / 0.05 / 0.5 | 6 | 0.7 | - | 1 x proj, speed 42, pierces, heavy |

### Skills per fighter

Z / X / C are the default loadout; V is the locked bonus skill (unlock: 2000 gold or 100 diamonds). Any 3 of the 4 can be slotted.

#### Aster (knight, light)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Shield Bash | melee | 55 | 60 | 0.12 / 0.08 / 0.35 | 3 | 1 | 5s | reach 1.5, lunge 4, staggers |
| X | Rising Slash | melee | 115 | 30 | 0.1 / 0.1 / 0.4 | 4 | 0.55 | 6s | reach 1.9, lunge 2, self-launch 6.5 |
| C | Blade Wave | projectile | 140 | 40 | 0.22 / 0.05 / 0.45 | 5 | 0.6 | 9s | 1 x proj, speed 17, pierces, **weaken** 4s (0.8), heavy |
| V | Judgment | strike | 220 | 60 | 0.2 / 0.08 / 0.5 | 5 | 0.7 | 10s | at target, radius 1.6, lands after 0.5s, **weaken** 4s (0.8), heavy |

#### Vesper (knight, flame)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Shield Bash | melee | 55 | 60 | 0.12 / 0.08 / 0.35 | 3 | 1 | 5s | reach 1.5, lunge 4, staggers |
| X | Rising Slash | melee | 115 | 30 | 0.1 / 0.1 / 0.4 | 4 | 0.55 | 6s | reach 1.9, lunge 2, self-launch 6.5 |
| C | Blade Wave | projectile | 140 | 40 | 0.22 / 0.05 / 0.45 | 5 | 0.6 | 9s | 1 x proj, speed 17, pierces, **burn** 4s (25), heavy |
| V | Judgment | strike | 220 | 60 | 0.2 / 0.08 / 0.5 | 5 | 0.7 | 10s | at target, radius 1.6, lands after 0.5s, **burn** 4s (25), heavy |

#### Garrick (greatsword, earth)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Ground Slam | strike | 150 | 50 | 0.3 / 0.08 / 0.5 | 7 | 0.6 | 6s | around self, radius 2.6, lands after 0.05s, **slow** 2.5s (0.65) |
| X | Whirlwind | strike | 60 | 20 | 0.12 / 0.08 / 0.4 | 2 | 0.3 | 7s | around self, radius 2.1, lands after 0.05s, x4 every 0.18s |
| C | Titan Cleave | strike | 340 | 90 | 0.4 / 0.08 / 0.7 | 9 | 1 | 12s | at target, radius 2, lands after 0.55s, **slow** 2.5s (0.65), heavy |
| V | Berserk | buff | - | - | 0.2 / 0.08 / 0.4 | - | - | 14s | rage 6s |

#### Kaede (katana, moon)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Counter Stance | buff | - | - | 0.04 / 0.08 / 0.9 | - | - | 6s | counter 0.9s |
| X | Crescent Wind | projectile | 120 | 30 | 0.14 / 0.08 / 0.35 | 3 | 0.45 | 6s | 1 x proj, speed 20, pierces, **bleed** 4s (20) |
| C | Thousand Cuts | strike | 48 | 12 | 0.2 / 0.08 / 0.6 | 1 | 0.3 | 11s | at target, radius 1.5, lands after 0.3s, x7 every 0.07s, **bleed** 4s (20) |
| V | Iaido Flash | melee | 200 | 50 | 0.08 / 0.16 / 0.45 | 5 | 0.7 | 8s | reach 2.2, lunge 18, **bleed** 4s (20), heavy |

#### Ember (mage, fire)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Flame Burst | strike | 120 | 40 | 0.12 / 0.08 / 0.4 | 7 | 0.5 | 6s | around self, radius 2.3, lands after 0.05s, **burn** 4s (30) |
| X | Fireball Volley | projectile | 40 | 12 | 0.2 / 0.08 / 0.4 | 2 | 0.32 | 7s | 5 x proj, speed 16, spread 0.45 rad, **burn** 4s (30) |
| C | Meteor | strike | 290 | 80 | 0.3 / 0.08 / 0.6 | 8 | 0.9 | 12s | at target, radius 2.1, lands after 0.9s, **burn** 4s (30), heavy |
| V | Inferno Ring | strike | 165 | 45 | 0.15 / 0.08 / 0.45 | 6 | 0.5 | 9s | around self, radius 2.8, lands after 0.1s, **burn** 4s (30) |

#### Marina (mage, water)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Bubble Ward | buff | - | - | 0.1 / 0.08 / 0.25 | - | - | 10s | ward 4s |
| X | Tidal Ring | strike | 105 | 35 | 0.14 / 0.08 / 0.45 | 7 | 0.5 | 7s | around self, radius 2.7, lands after 0.1s, **slow** 3s (0.6) |
| C | Ocean Requiem | strike | 270 | 80 | 0.35 / 0.08 / 0.6 | 8 | 0.9 | 12s | at target, radius 2.4, lands after 0.8s, **slow** 3s (0.6), heavy |
| V | Healing Rain | buff | - | - | 0.2 / 0.08 / 0.4 | - | - | 14s | heal 0.25s |

#### Nyx (assassin, shadow)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Smoke Step | blink | - | - | 0.06 / 0.08 / 0.12 | - | - | 5s | blink behind |
| X | Shuriken Fan | projectile | 48 | 14 | 0.12 / 0.08 / 0.3 | 1.5 | 0.35 | 6s | 3 x proj, speed 22, spread 0.3 rad, **poison** 6s (10) |
| C | Phantom Rush | melee | 260 | 70 | 0.18 / 0.18 / 0.55 | 6 | 0.9 | 10s | reach 2.2, lunge 16, **poison** 6s (10), heavy, staggers |
| V | Venom Fan | projectile | 42 | 12 | 0.12 / 0.08 / 0.3 | 1.2 | 0.3 | 7s | 5 x proj, speed 24, spread 0.5 rad, **poison** 6s (10) |

#### Rook (knuckles, force)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Rush | melee | 120 | 35 | 0.08 / 0.2 / 0.4 | 3 | 0.7 | 5s | reach 1.6, lunge 14, staggers |
| X | Shockwave Punch | projectile | 110 | 30 | 0.14 / 0.08 / 0.35 | 5 | 0.5 | 6s | 1 x proj, speed 18 |
| C | Meteor Fist | strike | 300 | 80 | 0.22 / 0.08 / 0.6 | 8 | 0.9 | 11s | around self, radius 2.5, lands after 0.02s, self-launch 9, heavy |
| V | Iron Body | buff | - | - | 0.1 / 0.08 / 0.25 | - | - | 13s | ward 2.5s |

#### Kira (kicks, chi)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Cyclone Kick | strike | 65 | 20 | 0.08 / 0.08 / 0.4 | 3 | 0.3 | 6s | around self, radius 2, lands after 0.05s, x3 every 0.15s |
| X | Crescent Gale | projectile | 110 | 30 | 0.14 / 0.08 / 0.35 | 3 | 0.45 | 6s | 1 x proj, speed 20, pierces |
| C | Hundred Kicks | strike | 40 | 10 | 0.15 / 0.08 / 0.6 | 0.8 | 0.3 | 10s | at target, radius 1.5, lands after 0.2s, x8 every 0.06s |
| V | Dragon Ascent | melee | 170 | 40 | 0.08 / 0.12 / 0.4 | 5 | 0.7 | 8s | reach 1.9, lunge 3, self-launch 8, staggers |

#### Raven (mage, electric)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Blink | blink | - | - | 0.04 / 0.08 / 0.15 | - | - | 4s | blink back |
| X | Chain Lightning | projectile | 90 | 25 | 0.14 / 0.08 / 0.35 | 1 | 0.75 | 6s | 1 x proj, speed 42, **paralyze** 2.5s |
| C | Thunderstorm | strike | 110 | 35 | 0.3 / 0.08 / 0.6 | 3 | 0.6 | 12s | at target, radius 1.25, lands after 0.45s, x3 every 0.35s, **paralyze** 2.5s, heavy |
| V | Static Field | strike | 75 | 22 | 0.12 / 0.08 / 0.5 | 2 | 0.5 | 10s | around self, radius 2.2, lands after 0.15s, x3 every 0.25s, **paralyze** 2.5s |

#### Ash (bow, blood)

| Key | Name | Type | Dmg | Guard dmg | Wind / active / recover (s) | Knock | Stun (s) | CD | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Z | Leap Back | blink | - | - | 0.04 / 0.08 / 0.12 | - | - | 4s | blink back |
| X | Arrow Rain | strike | 80 | 20 | 0.22 / 0.08 / 0.4 | 2 | 0.35 | 8s | at target, radius 1.8, lands after 0.7s, x3 every 0.25s, **bleed** 4s (22) |
| C | Hunter's Snare | projectile | 100 | 30 | 0.2 / 0.08 / 0.4 | 0.5 | 1.6 | 10s | 1 x proj, speed 32, **bleed** 4s (22), staggers |
| V | Piercing Volley | projectile | 55 | 14 | 0.2 / 0.08 / 0.4 | 2 | 0.3 | 9s | 5 x proj, speed 32, spread 0.25 rad, pierces |

### Emblems

| Emblem | Level 1 | Level 5 | Level 10 |
|---|---|---|---|
| Fighter | +2% damage | +10% damage | +20% damage |
| Tank | +3% HP and guard | +15% HP and guard | +30% HP and guard |
| Assassin | +1.5% critical chance | +7.5% critical chance | +15.0% critical chance |
| Mage | Skills recharge 2% faster | Skills recharge 10% faster | Skills recharge 20% faster |
| Swift | +1.5% move speed | +7.5% move speed | +15.0% move speed |

Unlocking a fighter costs 5000 gold or 250 diamonds.
<!-- BALANCE:END -->
