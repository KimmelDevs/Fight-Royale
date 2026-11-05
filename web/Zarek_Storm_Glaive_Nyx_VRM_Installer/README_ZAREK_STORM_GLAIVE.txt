ZAREK — STORM GLAIVE V1
======================

TEMPORARY CHARACTER MODEL
Zarek is a female fighter who uses the existing public/models/nyx.vrm.
Nyx is NOT changed. Later, add public/models/zarek.vrm and edit only
Zarek's entry in src/game/roster.ts from vrm: "nyx" to vrm: "zarek".

INSTALL
1. Unzip this package.
2. Copy ONLY install_zarek_storm_glaive.py to the web/ folder that
   contains package.json. Do not overwrite your source files manually.
3. Open PowerShell there and run:

      py install_zarek_storm_glaive.py
      npx tsc --noEmit
      npm run dev

4. For signed-in shop purchases, open the included .sql file and run it
   once in Supabase > SQL Editor. Optionally also store the migration in
   web/supabase/migrations/ so the project tracks the change.
5. If the script reports a failed anchor, STOP and share that error;
   the script checks all files before writing anything.

CHANGES
- src/game/roster.ts: Zarek appended at the end of the roster
- src/game/kits.ts: independent glaive kit, moves, bonuses and poses
- src/game/model.ts: fully procedural sharp double-ended steel glaive
- src/game/vrm.ts: lighter, athletic storm combat gait and posture
- src/game/fighter.ts: Clash Momentum storage and network syncing
- src/game/game.ts: 5-stage barrage, 3-stage judgment, actual clashes
- src/ui/Select.tsx: gameplay controls description
- src/ui/GameView.tsx: visible 0-to-3 Momentum meter

ZAREK STARTING BALANCE
Health: 2250     Guard: 88
Move: 4.0        Walk: 3.15
Jump: 7.7        Parry window: 0.19s
Light combo: 65 / 70 / 78 / 95 damage
Heavy — Split Current: 165 damage
Z — Flash Reversal: 85 damage, 6s cooldown; sidestep + melee sweep
X — Thunder Barrage: five blows, 10s cooldown; consume 1 Momentum
   to empower the final blow (86 instead of 55)
C — Heaven's Judgment: three slashes 90/110/145, 20s cooldown;
   at 3 Momentum consume all for an extra 85-damage lightning pulse
Bonus V — Arc Flash: 115 damage, 9s cooldown; unlock in shop

CLASH MOMENTUM
Real clash (attacks collide): +1, up to 3 stacks.
A clash using Z / Flash Reversal: +2 instead.
Clashes, normal blocking and perfect parries remain functional.
Skills do NOT force clashes to happen; timing matters.
The host owns Momentum in online matches. Snapshots sync the meter.

TESTING NOTES
- Installer was applied to two project copies, with and without
  later Garrick animation/range changes. A second run made no edits.
- TypeScript/TSX syntax parsed successfully, and glaive skill pose
  references were checked for missing keys.
- No live match or full Next.js build was performed; test real weapon
  alignment, the combo's timing, counterplay and online sync in game.
- A unique Zarek portrait or skill icon set is not included. Missing
  icons use your existing icon fallback until custom WebP art is added.
- Backups are created next to each edited file with '.zarek-backup-...'
  suffix. Do not commit backup files to GitHub.

FUTURE CHARACTERS (NOT IN THIS INSTALL)
Lucien — Mirror Duelist
Kaizen — Chainblade Berserker
