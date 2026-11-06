NESA / FIGHT ROYALE - COMPLETE FIXED INSTALLER
===========================================

This package was prepared and dry-run tested against your uploaded FightRoyale_Source.zip.
It fixes the previous "ai reach: expected exactly one code anchor" failure.
It preserves Zarek's separate 1.62m AI-range rule.

HOW TO INSTALL (Windows PowerShell)

1. Extract this entire ZIP into a folder. Keep the three files together.
2. Open PowerShell in your Fight Royale web folder.
3. Run the Python installer with an explicit path to your web folder:

   python "C:\PATH\TO\EXTRACTED\Install_Nesa_Complete_Fixed.py" .

   Or, copy ALL 3 files from this ZIP directly into the web folder
   then run:

   python .\Install_Nesa_Complete_Fixed.py

4. Test:

   npx tsc --noEmit -p .
   npm run dev

Files included:
  Install_Nesa_Complete_Fixed.py       - entry-point installer, automatically installs model
  Install_Nesa_Heart_Hammer_Fixed.py   - game code + heart icon installer
  nesa_optimized.vrm                  - Nesa model, optimized at max 1024 px texture

This applies Nesa without changing your other fighters' existing moves,
with all changes backed up in .nesa_installer_backups.
Run a second time safely; it is idempotent.
Dry-run with --check to preview changes.

Nesa abilities:
  Basic: 4-hit heavy combo; Heavy: rising hammer uppercut
  Z: Side Swipe (50% HP damage through a successful non-parry block, knockback)
  X: Upsie Daisie (lever-assisted flying kick)
  C: GIGA BONK! (jump + shockwave slam)
  V: Roundabout Crash (bonus skill)

NOTE: Exact gameplay interactions and display must still be tested in your browser.
