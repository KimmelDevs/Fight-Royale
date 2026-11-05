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
| `scripts/slice_icons.py` | Cuts a 4x4 ChatGPT icon sheet into round WebP icons (see section 11). |
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

## 10. Sound effects and music

- **Files:** sounds live in `public/sfx/*.mp3`. They were picked from the Mixkit library in
  `Desktop\DCODE\Story Maker\sfx` and renamed to short names (`swing`, `hit_blade`, `parry`,
  `fireball`, `music_battle`, ...). The Mixkit license is free and needs no credit, but don't
  share the raw files as a sound pack.
- **Engine:** `src/game/sound.ts`. `Sound.play(name, volume)` plays an effect with a little
  pitch variation. `Sound.setMusic("menu" | "battle" | "")` crossfades the music. Volumes
  (master / music / effects) are set in Settings and saved per browser.
- **Where sounds play:**
  - In `game.ts`, `swingSound()` (attack whooshes, casts, arrows) and `hitSound()` (impacts by
    weapon type) pick the sound for each attack.
  - `runFx()` plays a sound with each big effect: explosion, lightning, meteor, rocks, waves.
  - `this.snd(name, vol)` plays a sound on every player's machine in online matches.
  - Banners, victory/defeat and gold are in `GameView.tsx`; button clicks and menu music are in
    `App.tsx`; shop buy/error is in `Shop.tsx`.
- **Changing a sound:** copy a new mp3 over the file with the same name in `public/sfx`. No
  code change is needed. **Adding one:** copy it in under a new name and call
  `Sound.play("newname")` where it should play.
- **Size:** keep effects short (under about 300 KB each). The two music tracks are the biggest
  files (~3.5 MB each) and stream instead of downloading up front.

## 11. Icons (characters, skills, emblems) – same style every time

All icons came from ChatGPT image generation. Each image is a 4x4 sheet of 16 icons, which
`scripts/slice_icons.py` cuts into round 128 px WebP files. Two things keep the style
matching: always open with the **same first prompt**, and ask for "the exact same style and
4x4 layout" in every follow-up.

### Workflow
1. In ChatGPT, open a new chat and send **prompt 1** below. It sets the style.
2. In the **same chat**, send a follow-up for the next 16 icons ("exact same style, framing and
   4x4 layout, no text"). Staying in one chat keeps the look consistent.
3. Download the image (a square PNG), then slice it. Give 16 names in reading order and use `-`
   for any cell you don't want:
   ```bash
   python scripts/slice_icons.py sheet.png public/icons chars/kira skills/kicks-c - - - - - - - - - - - - - -
   ```
4. Use the file names the game looks for:
   - Characters: `public/icons/chars/<id>.webp` (e.g. `chars/kira`).
   - Skills: `public/icons/skills/<kit>-<key>.webp` (e.g. `skills/kicks-c`).
     - Mages use their element instead of the kit: `skills/mage-fire-z`, `skills/mage-water-x`,
       `skills/mage-electric-c`.
     - The keys are `z`, `x`, `c` and `v` (`v` is the shop bonus skill).
   - Emblems: `public/icons/emblems/<id>.webp` (`fighter`, `tank`, `assassin`, `mage`, `swift`).
   - Currency and lock: `public/icons/gold.webp`, `diamond.webp`, `lock.webp`.
5. Run the game and check the select screen and the skill bar.

### The exact prompts used

**1. First sheet (skills; sets the style):**
> Generate one square image: a 4x4 grid of 16 game skill icons for an anime fantasy action game
> (Genshin Impact UI style). Exactly 4 columns and 4 rows of equal square cells. Each icon is a
> glossy painted emblem inside a dark navy circle with a thin gold rim, centered in its cell.
> Plain dark navy background between cells. No text, no letters, no numbers. Row 1 (sword
> knight, cyan holy light): 1 shield bash with impact burst, 2 rising sword slash arc upward,
> 3 glowing crescent blade wave, 4 pillar of holy light from the sky. Row 2 (fire witch, orange
> flames): 1 fire explosion burst, 2 fan of five fireballs, 3 meteor falling, 4 ring of fire.
> Row 3 (water sorceress, blue water): 1 protective water bubble, 2 ring of water geysers,
> 3 giant water sphere, 4 healing rain drops with green sparkle. Row 4 (storm mage, purple and
> yellow lightning): 1 teleport blink afterimage, 2 chain lightning bolt, 3 thunderstorm cloud
> with three bolts, 4 static electric field dome.

**2. More skills (same chat):**
> Great, same exact style and layout (4x4 grid, dark navy circles with thin gold rim, no text).
> New image with these 16 icons. Row 1 (shadow assassin, purple smoke): 1 vanishing smoke step
> with shadow silhouette, 2 three spinning shuriken, 3 dash slash with purple speed lines, 4 fan
> of poisoned green-purple daggers. Row 2 (greatsword warrior, golden earth): 1 greatsword
> smashing the ground with cracks, 2 spinning whirlwind slash, 3 giant downward cleave splitting
> the earth, 4 berserk red rage aura. Row 3 (samurai, crimson and moonlight): 1 counter stance
> katana guard with glint, 2 crescent wind blade, 3 storm of many crossing slashes, 4 instant
> iaido draw slash flash. Row 4 (ranger archer, green nature): 1 leaping backflip, 2 rain of
> arrows from the sky, 3 barbed snare arrow with vines, 4 volley of five piercing glowing arrows.

**3. Brawler, kicker, emblems, currency (same chat):**
> Perfect. One more in the exact same style and 4x4 layout, no text. Row 1 (brawler with golden
> gauntlets, orange fire): 1 charging rush of fist blows, 2 shockwave punch blast, 3 meteor fist
> crashing down into a crater, 4 iron body golden shield aura around a muscular figure. Row 2
> (martial artist kicks, teal chi energy): 1 spinning cyclone kick, 2 crescent kick launching a
> teal wind blade, 3 hundred rapid kicks blur, 4 dragon ascent flying kick with a teal dragon.
> Row 3 (emblem badges, each a heraldic emblem): 1 crossed swords (red), 2 sturdy tower shield
> (blue steel), 3 dagger with a crescent moon (purple), 4 magic staff with glowing orb (violet).
> Row 4: 1 winged boot (emerald), 2 shiny gold coin with a star, 3 brilliant cyan blue diamond
> gem, 4 golden padlock.

**4. Character portraits (same chat):**
> Now character portrait icons in the exact same 4x4 layout and frame style (dark navy circles,
> thin gold rim, no text). Each is an anime cel-shaded chibi headshot (head and shoulders,
> facing the viewer, big expressive eyes, Genshin Impact style) on a softly glowing background
> in the character's color. Row 1: 1 Aster, boy knight with silvery white spiky hair, blue eyes,
> blue and white armor with gold trim, cyan glow. 2 Vesper, girl with crimson red ponytail, red
> eyes, black and crimson armor, orange glow. 3 Garrick, young man with sandy brown spiky hair,
> amber eyes, forest green tunic and steel pauldrons, gold glow. 4 Kaede, samurai girl with
> black ponytail, crimson eyes, white kimono with red collar, pink moonlight glow. Row 2:
> 1 Ember, witch girl with orange-red twintails, amber eyes, dark red witch hat with gold band,
> fire glow. 2 Marina, girl with light blue bob hair, blue eyes, white beret with navy band and
> a seashell ornament, water glow. [...] Row 3: 1 Nyx, assassin girl with dark purple hood,
> purple mask over the mouth, violet eyes, shadow glow. 2 Rook, boy with orange spiky hair,
> amber eyes, red jacket, golden gauntlets raised, flame glow. 3 Kira, martial artist girl with
> dark ponytail, teal eyes, teal headband, white gi, teal glow. 4 a big golden question mark.
> Row 4: four empty plain dark navy circles.

`[...]` marks fighters that were removed later. The golden question mark is the "Random"
opponent icon, `chars/random`.

**5. More portraits (same chat):**
> Excellent. Six more character portraits, exact same style, framing and 4x4 layout, no text.
> Row 1: [...] 3 Raven, witch girl with black bob hair, mint green glowing eyes, black witch hat
> with violet band, black and white dress, green lightning glow. [...] Row 2: [...] 2 Ash,
> hunter boy with silver hair, red eyes, dark grey hooded cloak with crimson scarf, bow on his
> back, red glow. 3, 4: plain dark navy circles. Rows 3 and 4: plain dark navy circles.

### Templates for new icons
Open a **new chat** and send prompt 1 first so the style is set. Then send one of these
templates. Replace the words in capitals, and fill unused cells with "plain dark navy circle".

> Now character portrait icons in the exact same 4x4 layout and frame style (dark navy circles,
> thin gold rim, no text). Each is an anime cel-shaded chibi headshot (head and shoulders,
> facing the viewer, big expressive eyes, Genshin Impact style) on a softly glowing background
> in the character's color. Row 1: 1 NAME, BOY/GIRL ROLE with HAIR COLOR AND STYLE, EYE COLOR
> eyes, OUTFIT, COLOR glow. 2-4 and rows 2-4: plain dark navy circles.

> Same exact style and layout (4x4 grid, dark navy circles with thin gold rim, no text). Row 1
> (FIGHTER TYPE, COLOR ENERGY): 1 SKILL Z PICTURE, 2 SKILL X PICTURE, 3 SKILL C PICTURE,
> 4 BONUS SKILL PICTURE. Rows 2-4: plain dark navy circles.

Tips:
- Describe the **picture**, not the skill's name. Write "vanishing afterimage with a teal kick
  streak", not "Phantom Step".
- Give each fighter one color of energy.
- Keep "no text" in every prompt.
- When a fighter gets a new VRoid model, regenerate their portrait from the model's real hair
  and eye colors. The hair color table in `README.md` lists them.

**6. Rank emblems** (new chat; it works as a first prompt on its own). Sliced into
`public/icons/ranks/` as `bronze` ... `mythic`, `star`, `star_empty` and `ranked`:
> Generate one square image: a 4x4 grid of 16 game rank emblem icons for an anime fantasy action
> game (Genshin Impact UI style). Exactly 4 columns and 4 rows of equal square cells. Each icon
> is a glossy painted emblem inside a dark navy circle with a thin gold rim, centered in its
> cell. Plain dark navy background between cells. No text, no letters, no numbers. These are
> competitive rank badges that get more ornate and impressive as they go up. Row 1: 1 Bronze
> rank, simple bronze shield badge with a small sword. 2 Silver rank, polished silver shield with
> crossed swords. 3 Gold rank, gold shield with crossed swords and small wings. 4 Platinum rank,
> pale teal platinum crest with wings and a gem. Row 2: 1 Diamond rank, icy blue diamond crystal
> crest with wings. 2 Master rank, purple amethyst crest with a laurel wreath and a crown.
> 3 Grandmaster rank, crimson and gold crest with large wings and a crown. 4 Legend rank, radiant
> golden phoenix crest with flames. Row 3: 1 Mythic rank, cosmic rainbow crystal crest with a
> dragon, stars and glowing aura, the most impressive of all. 2 a single shiny gold five-pointed
> star. 3 an empty dark grey five-pointed star outline. 4 two crossed swords on a red banner, a
> ranked match symbol. Row 4: four plain dark navy circles.

Image generation needs a logged-in ChatGPT account.

**Icons worth redoing:**
- Kira's `kicks-c` (Phantom Step) still shows the old flying-kick art.
- The portraits of fighters who got VRoid models were drawn from their old designs.

## 12. Ranked mode and matchmaking

**The ladder** is in `src/game/rank.ts`, in the `RANKS` table:

| Rank | Tiers | Stars per tier | Notes |
|---|---|---|---|
| Bronze | 3 (III-I) | 3 | Protected: losses never cost stars |
| Silver | 3 | 3 | Protected |
| Gold | 3 | 4 | |
| Platinum | 4 (IV-I) | 4 | |
| Diamond | 4 | 5 | |
| Master | 5 (V-I) | 5 | |
| Grandmaster | 5 | 5 | |
| Legend | 5 | 5 | |
| Mythic | – | unlimited | Stars just keep counting |

The star rules:
- **Winning** a ranked duel gives +1 star.
- **Win streaks:** every 3rd win in a row gives a bonus star.
- **Promotion:** with the tier full, the next win moves you up a tier with 1 star.
- **Losing** costs 1 star. At 0 stars you drop a tier. You can never drop into Silver or Bronze
  once you are above them.
- To change the ladder, edit the `tiers` / `stars` numbers in `RANKS`.

**Where progress is saved:** in the browser's localStorage (`fr-rank`). It is not tied to an
account yet, so a player who clears their browser data starts over, and a determined player
could edit it. To make it server-side later:
- add a Supabase migration with rank columns and a `ranked_result` function;
- call that function from `applyResult` when the player is signed in.

**Matchmaking** is in `src/lib/matchmaking.ts` and needs no game server:
1. Each searching player joins a Supabase Realtime **presence** channel (`fr-ranked-queue`)
   with their name and rank score (`rankScore`: total stars across the ladder).
2. Every second, the player who has waited longest picks the closest-ranked opponent. The
   allowed gap starts at 4 stars and widens by 1 star every 4 seconds of waiting.
3. That player opens a PeerJS room and sends the room code to the opponent. The opponent joins,
   and the duel runs peer-to-peer like any online match (`Ranked.tsx` starts it).
4. After 20 seconds with no opponent, a **FIGHT CPU** button appears. It plays a ranked match
   against a CPU whose difficulty depends on your rank (`cpuLevel`).

Results arrive as the match's `result` event, and `GameView.tsx` applies them. A rank panel on
the victory/defeat screen shows the new rank and the stars won or lost.

To test matchmaking alone, open the game in two browser tabs and press FIND MATCH in both.

## 13. Things to know

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
