FIGHT ROYALE — CPU PERSONALITIES 2.0 (ALL 17)
============================================

This is an additive update on top of your previously installed:
    FightRoyale_Smart_AI_17_Kira_Ash_Balance.zip

It modifies ONE FILE:
    web/src/game/ai.ts

Installation (Windows / PowerShell)
-----------------------------------
1. Extract Install_FightRoyale_AI_Personality_2_0.py into your Fight Royale web folder.
2. Open PowerShell in the web folder.
3. (Optional safety check) Run:
       python .\Install_FightRoyale_AI_Personality_2_0.py --check
4. Install:
       python .\Install_FightRoyale_AI_Personality_2_0.py
5. Validate and restart:
       npx tsc --noEmit -p .
       npm run dev

If the game folder is elsewhere, pass its directory as the first argument.
Example:
    python .\Install_FightRoyale_AI_Personality_2_0.py "C:\path\to\fight-royale\web"

The updater backs up the previous file to web/.ai_personality_v2_backups/.
Running the installer more than once is safe: it will not duplicate changes.

WHAT'S NEW
----------
- Each fighter can choose a real short combat sequence: backstep, jumpback,
  orbit, aggressive dash/chase, then an appropriate equipped skill or combo.
- Real movement inputs and skill cooldowns; no free teleports, invulnerability,
  damage boosts, or unearned attacks.
- Paths are selected with the circular arena boundary in mind.
- Recovery punishes, retreat baits, and follow-ups depend on observed enemy states.
- Human-ish variation and existing difficulty scaling are preserved.
- AI personality differences become more noticeable in CPU-vs-CPU spectator matches.

PERSONALITIES
-------------
01 Aster    Shield-bash bait and patient counterattack
02 Vesper   Backstep, then quick re-entry with light combos
03 Garrick  Space out attacks, answer missed swings with charged punishment
04 Kaede    Circle, counter, punish; pressure blocks with charged strikes
05 Ember    Backward mobility, fireball retaliation, ranged zoning
06 Marina   Escape pressure, Bubble Ward or Tidal Ring control
07 Nyx      Backward leap, bait enemy pursuit, Z/Smoke Step back into combat
08 Rook     Forward dash, Rush, persistent punching pressure
09 Gale     Jumps, orbits, Wind Step and aerial follow-ups
10 Bob      Backs off, plants mines, throws paralyzing bombs
11 Kira     Relentless forward chase, dashes back into kick range, combos
12 Raven    Backward repositioning/Blink and ranged lightning punishment
13 Ash      Backward leap, Hunter's Snare, charged-arrow punish
14 Veyr     Death Feint mind games and Blood Festival pursuit
15 Zarek    Clash Momentum pressure, angle changes and Phantom Spiral
16 Kaizen   Chain-range management, Predator's Hook and bind punishment
17 Nesa     Hammer baiting, Pink Heart Smash, Upsie Daisie chase

PRESERVED
---------
- All previously tuned damage, health, speed, guard and cooldown values.
- Kira's three aerial kicks and mobile aerial kicks.
- Nesa's improved kick chase, 1:0.75 spin scaling and arena-edge evasion AI.
- Previous 17-fighter Smart AI and spectator mode.
- Skill choices follow the equipped loadout; unavailable skills aren't forced.

Notes
-----
- Extra dramatic movement is applied to the 3D duel arena. Platform mode
  continues using its existing safe stage movement and previous Smart AI.
- This was validated on reconstructed latest-source fixtures, with a
  no-duplicate reinstall test and focused TypeScript checks.
- Full game typecheck and visual/gameplay balancing should be tested in your
  installed web project; external node_modules were not present in the test copy.
- The staged simulation uses simplified physics, not a true in-browser match.
