# Fight Royale – how to keep building it yourself

This guide explains how the web game works and how to change it without help: adding a new VRoid
character, shrinking models, making weapons, changing how fighters move, balancing skills,
and deploying. `README.md` holds the combat rules and the generated balance tables. This file
explains the *how*.

---

## 1. Everyday commands

Run these from the `web` folder.

```bash
npm install            # once, after cloning
npm run dev            # play locally at http://localhost:3000
npx tsc --noEmit -p .  # type-check (do this before every commit)
npm run build          # production build (what Vercel runs)
npm run balance        # regenerate the balance tables inside README.md
```

**Deploying:** Vercel watches the GitHub repo `KimmelDevs/Fight-Royale`, branch `main`, root
folder `web`. Every `git push` to `main` redeploys https://fight-royale-r87m.vercel.app within a
couple of minutes. Nothing else is needed.

```bash
git add -A web/src web/public web/scripts web/README.md web/README2.md
git commit -m "What you changed"
git push origin main
```

Do not commit `.env.local` or the `art/` folder (raw models and reference pictures), and do not
commit the stray `*.webp.import` files. Godot creates those when it opens the folder.

---

## 2. Where everything lives

| File | What it does |
|---|---|
| `src/game/roster.ts` | The fighters: id, name, title, description, stats bars, and `look` (body, **vrm file**, kit, element, colors). |
| `src/game/kits.ts` | Combat data per weapon kit: HP/guard/speed (`STATS`), every attack and skill, element status effects (`ELEMENT_EFFECT`), and **all the poses**. |
| `src/game/fighter.ts` | One fighter's brain-agnostic logic: states (idle, attack, charge, block, stun, KO), combos, dash, getting hit, stun rules, status effects. |
| `src/game/game.ts` | The match: arena, camera, spawning, attack resolution (melee, projectiles, area strikes, buffs, teleports, Phantom Step), hit effects, rounds, survival waves, HUD data, online sync. |
| `src/game/model.ts` | The 3D character: the old procedural body, **all weapons** (`build*` functions), the bow string, and loading the VRoid model. |
| `src/game/vrm.ts` | `VrmRig`: copies poses onto the VRoid skeleton and adds natural motion (breathing, soft elbows and knees, weight shift), plus the special modes (shield, staff, two-handed sword, boxer, archer) and arm IK. |
| `src/game/status.ts` | Burn, poison, bleed, paralyze, slow, weaken. |
| `src/game/ai.ts` | CPU opponents (Easy/Normal/Hard/Master presets). |
| `src/game/mobs.ts` | Survival enemies and waves. |
| `src/game/fx.ts` | Sparks, flashes, rings, rocks, embers, lightning, damage numbers. |
| `src/game/economy.ts` | Prices, starting characters, gold rewards, emblems. |
| `src/game/net.ts` | Online play (PeerJS, browser to browser, the host runs the match). |
| `src/lib/account.ts` | Guest save (browser localStorage) and Supabase accounts. |
| `src/ui/*.tsx` | Screens: menu (`App`), character select / prepare / loadout (`Select`), in-game HUD (`GameView`), `Shop`, `Lobby`, `Settings`. |
| `public/models/*.vrm` | The shrunk VRoid characters the game loads. |
| `public/icons/` | Character, skill, emblem and currency icons (`.webp`). |
| `scripts/shrink_vrm.py` | The model shrinker (see section 4). |
| `scripts/balance-doc.ts` | Writes the balance tables into `README.md` (`npm run balance`). |
| `supabase/migrations/` | Database changes for accounts, shop and economy. |

---

## 3. Adding or replacing a VRoid character (step by step)

1. **Make the character in VRoid Studio**, then use *Export → Export as VRM*. Either VRM version
   works. Keep the default humanoid bones.
2. **Shrink it** (from the `web` folder; needs Python with Pillow: `pip install pillow`):
   ```bash
   python scripts/shrink_vrm.py "C:\path\to\MyFighter.vrm" public/models/myid.vrm 1024
   ```
   The file name must be the character's id in lowercase.
3. **Point the fighter at it** in `src/game/roster.ts`. Add `vrm: "myid"` to its `look`:
   ```ts
   look: { name: "Kira", body: "f", vrm: "kira", kit: "kicks", element: "chi", ... }
   ```
   - `body` is `"m"` or `"f"`. It also picks the motion style: `"m"` is heavy and braced, `"f"`
     is light and graceful.
   - `kit` picks the weapon, the move set and the poses: `knight`, `greatsword`, `katana`,
     `mage`, `bow`, `assassin`, `knuckles` or `kicks`.
   - `element` picks the colors and effects: `light`, `flame`, `fire`, `earth`, `moon`,
     `water`, `electric`, `shadow`, `blood`, `force` or `chi`.
4. **Credit the artist.** The VRoid models' license requires credit. Edit the credits line in
   `src/ui/App.tsx` (search for `models by Fruit`).
5. **Icon:** put a square `.webp` in `public/icons/chars/myid.webp`.
6. **New fighter (not a replacement)?** Also add it to `CHARACTERS` in `roster.ts`. If people
   should be able to buy it with an account, add its id to the character list in a new
   Supabase migration (copy `supabase/migrations/20261104000000_more_characters.sql`).
7. `npm run dev`, pick the fighter (locked fighters can still be previewed and picked as the
   CPU opponent), check the weapon sits in the hand, then type-check, commit and push.

---

## 4. Shrinking models

VRoid exports are 14–17 MB, mostly 2048 px textures. That is too heavy for a browser game.
`scripts/shrink_vrm.py` makes them smaller without touching the mesh, the skeleton, the spring
bones (hair and skirt physics), the MToon materials or the expressions:

- every texture larger than the limit (1024 px by default) is resized to fit the limit,
  keeping its aspect ratio;
- the thumbnail is reduced to 256 px;
- the images are re-encoded with optimization, and the file's binary buffer is repacked.

**Every character was shrunk exactly once, all at 1024 px.** That is 11 models, one pass each
(Raven's and Aster's first versions were replaced by newer VRMs, and each new file was shrunk
once). Sizes:

| Character | Original | Shrunk (in `public/models`) |
|---|---|---|
| Aster | – | 11.1 MB |
| Vesper | – | 9.9 MB |
| Garrick | – | 9.4 MB |
| Kaede | – | 11.0 MB |
| Ember | – | 10.1 MB |
| Raven | – | 10.8 MB |
| Rook | 14.8 MB | 9.5 MB |
| Nyx | 16.4 MB | 10.8 MB |
| Ash | 16.4 MB | 9.8 MB |
| Kira | 14.3 MB | 9.2 MB |
| Marina | 17.2 MB | 10.4 MB |

The originals of the first six weren't recorded. The shrinker typically saves about 35–40%.

**Don't shrink a file twice.** Always shrink from the original VRoid export. If a model must
load faster, use 768 instead of 1024 (`... public/models/myid.vrm 768`). Below 768, faces and
eyes start to look blurry.

---

## 5. How the weapons are made

There are no weapon model files. Every weapon is built in code from simple three.js shapes
(boxes, cylinders, spheres, cones) in `src/game/model.ts`:

| Kit | Builder | Notes |
|---|---|---|
| knight | `buildSword()` + `buildHeaterShield()` | Heater shield made from a custom shape; on VRoid fighters it is held at a guard spot by arm IK (`shieldArm` in `vrm.ts`). |
| greatsword | `buildGreatsword()` | Two-handed: the left hand is pulled onto the grip (`gripL`), and the sword rests on the shoulder when idle (`restSword`). |
| katana | `buildKatana()` | Two-handed like the greatsword. |
| mage | `buildStaff()` | The staff swings on a spring so it feels heavy (`staff` mode). |
| bow | `buildBow()` | A recurve longbow built from tapered curved segments, plus a string that follows the drawing hand and an arrow that appears while drawing (`updateBow`). |
| assassin | `buildDaggers()` | One dagger per hand. |
| knuckles | `buildKnuckles()` | Metal knuckles on both fists. |
| kicks | `buildKicks()` | Glowing ankle wraps; the swing trail follows the right foot. No hand weapon. |

How the weapons work:
- **Attachment:** weapons hang on the hand pivots (`hand_r` / `hand_l`). On VRoid fighters the
  game moves those pivots to the real VRoid hands every frame, so the weapon follows the hand.
- **Size:** the weapons were first designed for the old chibi bodies, so on VRoid fighters they
  are scaled by `VRM_WEAPON_SCALE = 0.68` (top of `model.ts`). The bow is scaled up again by
  1.45 to reach about 87% of body height.
- **Colors:** everything comes from the fighter's `look` (`band`, `trim`, `metal`, `glow`...)
  in `roster.ts`, so recoloring a weapon only needs a change there.
- **Glow:** the glowing parts use `this.glowMat`, which flashes white while charging.
- **Swing trail and hit point:** `bladeBase` / `bladeTip` mark the blade for the swing trail
  and the edge alignment. `castPoint` is where projectiles spawn.

To change a weapon, edit its `build*` function. `mesh(parent, geometry, material, position,
rotation, scale)` adds one part. Positions are in meters in the hand's frame, and rotations are
in radians.

---

## 6. How the characters move

Movement has three layers. Most changes only touch layer 1.

### Layer 1 – poses (`src/game/kits.ts`)
Every kit has a table of named poses (`KNIGHT`, `MAGE`, `BOW`, `KICKS`, ...). A pose is made by:

```ts
P(torso, head, arm_r, hand_r, arm_l, hand_l, leg_l, leg_r, hips_y)
```

- Each joint value is `[x, y, z]`, a rotation in **radians** (1 rad ≈ 57°; 90° = 1.57).
- Rotation order is YXZ.
- **Arms:** a negative `x` raises the arm forward (−1.57 points it straight ahead, −3.0 points
  it straight up). `y` swings it across or out, and `z` lifts it sideways.
- **Legs:** a negative `x` lifts the leg forward (−1.6 is a kick to hip height).
- **Torso / head:** `y` turns them. A negative torso `y` turns the left shoulder toward the
  enemy. `x` leans forward (+) or back (−).
- `hips_y` lowers the body (−0.1 is a crouch). VRoid knees bend to match.
- `K(pose, kneeLeft, kneeRight)` adds extra knee bend in radians. Kicks use it for the chamber
  (knee up, shin folded ≈ 1.6–1.9) and the snap (≈ 0.1).

Each attack in `kits.ts` names two poses: `pose_w` (wind-up) and `pose_s` (strike). The
fighter shows `pose_w` during the wind-up, then snaps to `pose_s`, then relaxes back to `idle`.
`idle`, `block` and `charge` are used by every kit.

**To adjust a stance:** change the numbers in that kit's `idle` pose, save, and the dev server
reloads. Change one joint at a time in steps of about 0.1–0.2.

### Layer 2 – blending (`fighter.ts` → `model.ts`)
`Fighter.computePose()` picks the pose name from the fighter's state. `Model.blend()` slides
the joints toward it smoothly. A higher speed number snaps faster (strikes use 40–45, idle
uses 9–14).

### Layer 3 – the VRoid skeleton (`src/game/vrm.ts`)
`VrmRig.update()` copies the blended pose onto the VRoid bones, which point a different way
than the old procedural joints, so each bone has a calibration. It then adds natural motion:

- breathing, a weight shift between the legs, head look, soft elbows that bend more as the arm
  rises, knees that follow the crouch, and feet kept flat;
- per-bone follow-through (`RATE`), so the hips move first and the arms and head lag a little;
- a motion style: `STYLES.light` (female: hip sway, relaxed) and `STYLES.heavy` (male: wider
  stance, bent knees, elbows out). Tune the numbers in `STYLES`.

Special modes are turned on per kit in `model.ts` (`attachVrm`):

| Flag | Used by | What it does |
|---|---|---|
| `shield` | knight | Shield held at a guard spot by IK, rising when blocking. |
| `gripL`, `restSword`, `bladed` | greatsword, katana | Left hand locked on the grip; sword rests on the shoulder; torso turns to keep the hands in front. |
| `staff` | mage | The staff stays mostly upright and swings on a spring. |
| `boxer` | knuckles | High guard, bounce, head weave, staggered feet. |
| `archer` | bow | Bow upright across the aim line; IK draws the string hand to the jaw. |

`solveArm(side, target, pole)` is the two-bone arm IK. Give it a point and it bends the
shoulder and elbow to reach it, with the elbow pointing toward `pole`. Use it whenever a hand
must reach a spot exactly (a shield grip, a bowstring, a two-handed handle).

### Getting stance advice
Every stance in the game came from asking ChatGPT how a real fighter of that style stands and
moves, then turning the answer into pose numbers. This prompt works well:

> I'm animating an anime-style [archer / kick fighter / greatsword knight] in a 3D fighting
> game with a humanoid skeleton (hips, spine, chest, upper chest, neck, head, shoulders,
> upper/lower arms, hands, upper/lower legs, feet). Give approximate joint angles in degrees
> for the fighting stance, each attack (wind-up and strike), block and the special move, and
> what makes it look natural instead of robotic.

Turn the degrees into radians (divide by 57.3) and put them in the matching joints of `P(...)`.
Then check the result in game and nudge the signs if a limb bends the wrong way.

---

## 7. Skills, balance and status effects

- **Attack fields** (`kits.ts`, the `Attack` interface): `dmg`, `guard` (guard damage),
  `wind` / `active` / `recover` (seconds), `reach`, `lunge`, `knock`, `stun`, `heavy`, `cd`
  (cooldown).
  - The `type` field sets how the attack works: `melee`, `projectile`, `strike` (area attack
    after `delay`, can `repeat`), `buff`, `blink` or `phantom` (teleport behind the target
    and strike, `repeat` times).
  - `no_parry: true` makes a skill blockable but not parryable.
- **Skills:** each fighter has `z`, `x`, `c` and a bonus skill `v`, bought in the shop. Players
  pick 3 of the 4 in the loadout.
- **Status effects:** `ELEMENT_EFFECT` in `kits.ts` sets which element's skills cause which
  effect. Durations and strengths are set there too. The effects themselves are in
  `status.ts`.
- **Stun rules** (in `fighter.ts`, `receiveHit`): a skill stuns only once per use, and stuns
  repeated within 3 s get 0.6× shorter.
- After changing numbers, run `npm run balance` to update the tables in `README.md`.

---

## 8. Shop, accounts and the database

- **Prices, starting fighters and rewards** are in `src/game/economy.ts`.
- **Guests** (not signed in) save to the browser, so everything works without an account.
- **Signed-in players** use Supabase. The server functions (buying, loadouts, gold) are in
  `supabase/migrations/`.
- **Two migrations have not been applied yet:** `20261105000000_admin_google.sql` and
  `20261105100000_start_garrick.sql`. Apply them before relying on accounts:
  ```bash
  npx supabase link --project-ref vyubpbffiwgepkguuypm
  npx supabase db push
  ```
- When you add a fighter or skill that accounts can buy, add a new migration file. Never edit
  one that was already applied.

---

## 9. Online play

`src/game/net.ts` connects browsers directly with PeerJS using a room code, so there is no
game server. The host's browser runs the match and sends snapshots. Each snapshot is an array
from `Fighter.snapshot()` / `Mob.snapshot()`. If you add something that other players must
see (a new bar, an effect flag), append it to the end of the snapshot array and read it in
`applySnapshot`. Old clients ignore extra values.

---

## 10. Things to know

- **License:** the VRoid models are by Fruit. Keep the credits line when you add or replace
  models.
- **Starting fighters** are Aster, Ember and Garrick (`START_CHARACTERS` in `economy.ts`). Owned fighters are shown
  first on the select screen.
- **Hidden mode:** Platform Brawl exists but is hidden (`SHOW_BRAWL = false` in `game.ts`).
- **Godot version:** the Godot port lives in a separate repo, `KimmelDevs/FightRoyaleGodot`.
  It has the models, baked bone animations, duel/team matches, the HUD, menus and the shop.
  Survival, online play, status effects and the latest web changes (bow, Kira, Phantom Step)
  are not ported yet. The web game is the complete version.
- **If something breaks after an edit:** run `npx tsc --noEmit -p .` first. It catches almost
  every mistake. Then open the browser console (F12) while playing.
