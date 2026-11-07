FIGHT ROYALE — GLOBAL GUARD REGEN NERF
======================================

Change:
- ALL fighters' guard (shield) regenerates only after 2.0 continuous seconds
  without taking damage. Any new blocked hit or direct HP hit resets this timer.
- Damage over time (such as burn) also resets the 2-second timer.
- Guard still does not regenerate while the fighter is holding block.
- The delay timer runs even while blocking, so lowering the shield after the
  required two damage-free seconds permits guard regen immediately.
- Perfect parries and dodges that take no damage do not reset the timer.
- Existing guard regeneration speeds are unchanged (Kaizen remains at half
  the standard regeneration rate).
- Existing attack damage, HP, skills, AI, cooldowns, spectator mode untouched.

INSTALL
-------
1. Extract the ZIP into the Fight Royale 'web' folder.
2. Open a terminal inside 'web'.
3. Run:

   python Install_FightRoyale_Guard_Regen_2s.py

4. Optional verification:

   npx tsc --noEmit -p .
   npm run dev

You may pass the web folder path as an argument if running from elsewhere.
Use --check to validate compatibility without modifying any files.

This installer modifies only src/game/fighter.ts and stores the original file
under web/.fightroyale_guard_backups/<timestamp>/src/game/fighter.ts.
It is safe to run again: a second run detects the installed marker and skips.

TESTS
-----
Validated patch matching on two stages of the user's Fight Royale sources,
installer run and repeat run, and TypeScript transpiler syntax checks.
Not tested in live browser matches. Test in-game to confirm combat feel.
