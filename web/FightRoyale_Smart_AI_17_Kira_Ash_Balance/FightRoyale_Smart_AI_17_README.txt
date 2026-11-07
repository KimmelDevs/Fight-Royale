FIGHT ROYALE — SMARTER AI PERSONALITIES FOR ALL 17 FIGHTERS
+ Kira Phantom Step 16-second cooldown
+ Ash basic and charged attack damage nerf

INSTALL (Python 3.10+; no additional Python packages required)
1. Extract this ZIP into your Fight Royale web folder (where package.json exists).
2. Open PowerShell in the web folder.
3. Optional, verify source compatibility before modifying any files:
   python .\Install_FightRoyale_17_Smart_AI_Kira_Ash_Balance.py --check
4. Install:
   python .\Install_FightRoyale_17_Smart_AI_Kira_Ash_Balance.py
5. Type-check and launch:
   npx tsc --noEmit -p .
   npm run dev

ALTERNATIVELY, pass the web folder path as the script's positional argument.

CHANGES
- All 17: distinct AI styles (Aster, Vesper, Garrick, Kaede, Ember,
  Marina, Nyx, Rook, Gale, Bob, Kira, Raven, Ash, Veyr, Zarek,
  Kaizen, Nesa). Personalized skill choices, charge/basic mixtures,
  whiff/recovery punishes, and different footwork and bait habits.
- Nesa: prioritize long-reaching kick and reserve heart charges for real openings.
  Existing enemy dodge logic against Nesa and her giant-hammer follow-up is kept.
- Kaizen: use Predator's Hook at chain range, Death Spiral to punish recovery,
  and build close-range combo pressure.
- Kira: Phantom Step cooldown changed from 12 seconds to 16 seconds.
- Ash: basic arrows 60->48, 62->50, triple-arrow projectile 46->37 EACH;
  charged piercing arrow 260->195. Arrow Rain, Hunter's Snare, Leap Back,
  and bonus skill damage are unchanged.

MODIFIED FILES
  src/game/ai.ts
  src/game/kits.ts

SAFE BEHAVIOR
- Does not replace the whole ai.ts with an old snapshot.
- Leaves CPU-vs-CPU spectator mode, Nesa V6 spin, Nesa anti-hammer AI,
  Kira's mobile triple aerial kicks, and all other fighter abilities unchanged.
- Backups made in web/.smart_ai17_backups/<timestamp>/
- Running the installer again does not duplicate the patch.
- If code anchors or unexpected current damage values don't match, the installer
  exits rather than guessing and potentially overwriting your custom changes.

TEST RESULTS
- Fresh installation against reconstructed source with recent Nesa, Kira,
  and spectator patches: PASS.
- Second installation: PASS (no duplicate updates).
- TypeScript parser / transpileModule checks (ai.ts, kits.ts, fighter.ts,
  model.ts, game.ts): PASS.
- Full npm typecheck and actual CPU-vs-CPU matches: not executed in this environment.

Tip: Watch several spectator matches at different difficulties to tune the personalities.
