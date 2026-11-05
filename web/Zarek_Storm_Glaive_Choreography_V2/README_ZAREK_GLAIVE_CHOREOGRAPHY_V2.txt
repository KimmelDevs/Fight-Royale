ZAREK - STORM GLAIVE CHOREOGRAPHY V2
====================================

This is an animation/weapon-visual upgrade for the Zarek character already installed in Fight Royale.
Nyx remains Zarek's temporary VRM. It does not edit Nyx herself.

What changed
------------
* Basic 1: forward blade-tip thrust, torso and hands extend together.
* Basic 2: reverse-end diagonal strike with opposing torso twist.
* Basic 3: rising figure-eight cut, with low-to-high rotation.
* Basic 4: committed pivoting crosscut; visibly stronger than the first three hits.
* Each move now has distinctive wind-up and strike silhouettes, different weapon orientations, quicker attack snaps and restrained recoveries.
* Actual glaive pivots in the right-hand mount; the left-hand IK follows that same shaft.
* Faster VRM polearm-hand response; no more greatsword-like lag on Zarek.
* Slightly thinner, pointed blade silhouettes, keeping the existing overall style.
* Body-turn accents use the game's existing replicated yaw field (online-friendly).

UNCHANGED: basic damage, reach/hitboxes, cooldowns, clash rules, Clash Momentum,
Z/X/C/V skill logic, other character balance, Nyx VRM asset, Supabase data.

Install
-------
1. Make sure original Zarek character installer has already been run.
2. Extract install_zarek_choreography_v2.py.
3. Put the Python file in Fight-Royale/web/ beside package.json.
4. Open PowerShell there and run:

    py install_zarek_choreography_v2.py
    npx tsc --noEmit
    npm run dev

The installer creates timestamped backups beside each modified .ts file and stops
with an error instead of guessing if expected code is missing.

Changed files
-------------
src/game/kits.ts
src/game/fighter.ts
src/game/model.ts
src/game/vrm.ts

No Supabase migration. No character icon changes. No new VRM file needed.

Test sequence
-------------
- Do all 4 basic attacks and watch the transition from thrust to reverse-end
  to rising figure-eight to wide finishing crosscut.
- Check her right/left hands both stay on the glaive with Nyx's VRM.
- Test a basic attack vs an enemy weapon; standard clashes must still work.
- Test Z/X/C special animations and online matches.

Validation: installer tested against original Zarek V1 and a Kaizen-installed
project copy. All changed TypeScript files passed syntax parsing. A full Next.js
build and live combat were not run in this environment.

Research inspiration (stylized animation, not literal martial arts instruction)
--------------------------------------------------------------------------
IWUF competitive Wushu Taolu: https://iwuf.org/en/sport-wushu/competitive-wushu/taolu/
WushuOntario staff moves: https://wushuontario.ca/?page_id=2462
Still Mind Martial Arts bo combinations: https://stillmindmartialarts.com/portfolio/17-basic-bo-combinations-kobudo-kihon/
Game animation principles: https://www.gamedeveloper.com/production/the-12-principles-of-animation-in-video-games
