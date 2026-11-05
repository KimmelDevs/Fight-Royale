KAIZEN WEAPON + ROTATING GUARD V5
=================================
Targets: Fight Royale web project AFTER Kaizen/Zarek V4 Exact-Source Fix.

INSTALL
1. Copy install_kaizen_weapon_guard_v5.py to your web/ folder alongside package.json.
2. Open PowerShell in web/ and run:
   py install_kaizen_weapon_guard_v5.py
   npx tsc --noEmit
   npm run dev
3. Test Kaizen's idle chain, basic combo, X and V binds, extended Z spin,
   and blocking next to an enemy.

FILES MODIFIED
  src/game/model.ts    — detailed forked steel spear-knife, burgundy grip,
                         72 thin chain links (shown only as needed),
                         no stretched oversized chain meshes, slimmer enemy wraps,
                         close-range chain orbit while blocking.
  src/game/game.ts     — host-authoritative close-range defensive chain contact,
                         max one touch per target every 0.45s while blocking.

GUARD CONTACT DEFAULTS
  16 nominal damage, 9 guard damage, tiny knockback, small hit reaction,
  0.92m + target radius horizontal range, up to 1.05m vertical separation.
  Can be blocked by enemies, cannot be perfectly parried. Stops when Kaizen
  releases block, loses guard, is KO'd or is in a chain bind.
  Does NOT deflect projectiles or replace Kaizen's ordinary guard mechanics.

PREVIEW / TWEAKING
  After installation, weapon dimensions are in buildChainblade() within model.ts.
  Change torus(0.016, 0.034) to make chain thinner or thicker (the difference
  between the values controls thickness). Modify 0.047 in updateChainblade()
  to change link spacing (without changing link size).
  Tweak 0.77 / 0.69 in the blocking branch for guard visual radius.
  Gameplay guard contact values are all together in updateKaizenSpinGuard()
  in game.ts (NOT in kits.ts).

PRECAUTIONS
- Backups are written next to both TS files before replacement.
- The patch validates both files before touching either one and is safe to rerun.
- Designed for the latest V4 source files supplied earlier, not arbitrary forks.
- TypeScript syntax and patch repeatability checked in a saved project copy.
  Test collision, network mode and animation visually in your own game.
- Does not change Kaizen skill damage/cooldowns or Zarek's Clash Counter.
- No Supabase migration is needed.
