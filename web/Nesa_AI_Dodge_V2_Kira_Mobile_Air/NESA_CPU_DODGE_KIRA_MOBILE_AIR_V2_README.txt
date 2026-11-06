FIGHT ROYALE — NESA ENEMY-DODGE + KIRA MOBILE AIR-KICKS PATCH V2

This is a small updater for your EXISTING installation of:
  Install_Nesa_Dodge_Kira_3AirKicks.py
It does not reinstall or change Nesa's damage, 1:0.75 charge spin,
skills, cooldowns, visuals, or Weight Passive.

WHAT IT FIXES
* Enemies no longer keep trying to dash backwards through the circular arena wall.
* Enemy CPUs evaluate several escape directions and choose one that will actually
  move them within the arena, including sidesteps around Nesa.
* Nesa's attack ranges are estimated from the real hammer hitboxes and her
  approach/lunge, not just the small opening swing.
* Heartbreaker High Striker is treated as two separate threats. The CPU saves
  its dash for the delayed giant-hammer finish instead of using it on the small bonk.
* Difficulty-scaled evasion and normal dash cooldowns are preserved.
* Kira can steer during all three aerial kicks. CPU Kira also closes distance
  while airborne. Movement uses standard speed and grants no free invulnerability.

INSTALL (Windows PowerShell)
1. Extract this ZIP into the Fight Royale web folder.
2. In that folder run:
       python .\Install_Nesa_AI_Range_Kira_Mobile_Air_V2.py
3. Verify and start:
       npx tsc --noEmit -p .
       npm run dev

Check without modifying files:
       python .\Install_Nesa_AI_Range_Kira_Mobile_Air_V2.py --check

The updater automatically backs up the original ai.ts and fighter.ts in
  .combat_ai_installer_backups/
It is safe to re-run: subsequent runs do not duplicate changes.

VALIDATION
Tested on a copy of the game's updated source with the previous Kira/Nesa patch.
Installer dry run, installation, repeat run and TypeScript syntax checks passed.
In-browser AI behavior and full TypeScript type-checking still require local testing.
