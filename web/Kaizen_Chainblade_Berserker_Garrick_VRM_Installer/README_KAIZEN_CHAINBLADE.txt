KAIZEN — CHAINBLADE BERSERKER V1
================================

TEMPORARY MODEL
- Kaizen uses public/models/garrick.vrm.
- Garrick remains a completely separate character and is not edited.
- Later add public/models/kaizen.vrm, then change only Kaizen's
  vrm: "garrick" to vrm: "kaizen" in src/game/roster.ts.

INSTALL
1. Extract install_kaizen_chainblade.py from this ZIP.
2. Put install_kaizen_chainblade.py directly in your main web/ folder,
   next to package.json (NOT inside another folder).
3. Open PowerShell in that web/ directory and run:

      py install_kaizen_chainblade.py
      npx tsc --noEmit
      npm run dev

   If the installer says it cannot find an anchor, do NOT repeatedly
   rerun it or overwrite your source with an old example file.
   Send the exact error and the related current source file for patching.

4. If you use the signed-in Supabase shop, open the included SQL migration
   in a text editor, paste its content into Supabase SQL Editor, and run it.
   Alternatively manage it via your existing migration process; do not
   apply the same migration twice via different workflows without checking.
5. Test in an offline duel before committing/pushing.

ATTACKS
- Basic: four close-range steel cuts, 76/82/94/116 starting damage.
- Heavy (hold attack): CHAINBREAKER, 185 dmg, 3.05 reach, slow wind-up.
- Z: CHAIN SNARE, 100 dmg, 7s cooldown. An actual damaging hit pulls
     the enemy up to 0.9 game units. Blocking, parrying, and clashing
     prevent the pull.
- X: RENDING ORBIT, 11s cooldown. Three independent swipes for
     65/77/98 dmg, with different poses. Each can be blocked, parried,
     or clashed with using the existing combat system.
- C: UNBOUND DRIVE, 18s cooldown. For 5s gain the normal 20% rage damage
     bonus and +0.32 basic attack reach, plus a visual chain extension.
     Blocks, parries, and clashes continue to function.
- V bonus skill: RAZOR RECALL, 10s cooldown, 135 dmg, reach 3.2.

VISUALS / MOVEMENT
- A custom seven-plate chainblade with steel edges, red seams, real
  animated gaps, and link connectors. Compact for regular attacks,
  extended while lashing or during Unbound Drive.
- Kaizen uses a distinct braced VRM movement preset.
- Not a Gale-style ground-smashing character.

TECHNICAL / SAFETY
- The installer validates all text anchors before writing any files.
- Timestamped .kaizen-backup-* copies are made beside edited source files.
- Changes to existing characters and their kits are not intentionally made.
- Safe to rerun: detects Kaizen and exits without repeating edits.
- Tested on available local project copies with and without Zarek installed.
- TypeScript/TSX parsing and move-pose references checked; live game
  behavior and full npm build were NOT verified on your computer.
- You don't need a Python-generated external weapon asset; the weapon
  uses Three.js geometry created inside src/game/model.ts.

FILES CHANGED
  src/game/roster.ts
  src/game/kits.ts
  src/game/model.ts
  src/game/vrm.ts
  src/game/fighter.ts
  src/game/game.ts
  src/ui/Select.tsx

SHOP / ICONS
The SQL file is optional if you only play offline.
Kaizen's portrait and skill icons are not included in this gameplay installer.
