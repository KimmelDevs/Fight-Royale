KAIZEN V10 — PREDATOR'S HOOK + SERPENT SLAM
============================================

INSTALL (from your fight-royale/web folder)
1. Extract BOTH Python files from the ZIP to the same main web/ folder:
   - install_kaizen_hook_serpent_v10.py    (RUN THIS)
   - install_kaizen_hook_recast_v9.py      (dependency; do NOT run separately)
2. Open PowerShell in web/ (the folder with package.json).
3. Run:
      py install_kaizen_hook_serpent_v10.py
      npx tsc --noEmit
      npm run dev

The installer detects your V7/V8 bind system and includes the missing V9 X-hook
update automatically. If V9 is already installed it only updates Serpent Bind.
The installer preflights all changes in memory before writing, backs up every
modified file, and won't double-install when rerun.

PREDATOR'S HOOK (X)
- X throws an extended chain and binds an opponent in place for up to 4 sec.
- Kaizen can still walk while the opponent is tethered.
- All other skills and attack actions are locked during this bind.
- Press X AGAIN to pull the opponent smoothly toward Kaizen.
- The hook unbinds if not recast within 4 seconds.
- CPU Kaizen will approach the bound target and automatically recast X.

SERPENT BIND (V — bonus skill)
- Initial V hit binds the target; blocking and clashes still prevent the bind.
- 4 sec to select a follow-up. Both fighters are locked while waiting.
- Press Z: reel-in, lift, slam left, slam right, and a strong forward finish.
- Press X: reel-in, lift, swing over Kaizen, slam back, and finish behind.
- Each follow-up takes about 1.85 seconds, with three impact beats.
- Opponent stays chain-bound and unable to move until choreography ends.
- Opponent is restored upright at the end. Knockouts end the sequence safely.
- Initial V damage: 85. Three follow-up hits: 24 / 32 / 80 damage, before
  other damage modifiers. Serpent Bind cooldown stays unchanged.

PRESERVED
- Chain length, thin links, blade size, rotating guard contact damage
- Kaizen V8 guard regen and defensive clashes
- Zarek Clash Counter and her skill kit
- Other roster members, best-of-three rounds, and Supabase purchases

CODE CHANGES
- src/game/fighter.ts     chain/animation state, hit reactions, victim path
- src/game/game.ts        three scheduled impact events and sound/FX
- src/game/kits.ts        updated Serpent Bind description
- If V9 is missing: src/game/ai.ts and src/ui/GameView.tsx are also patched,
  along with game/fighter/kits for the X-recast / AI behavior.

Important: This patch was syntax-checked on saved project copies with and
without V9 installed, not run in a live match on your computer. If an anchor
check fails, stop and upload your current source files for a targeted fix.
