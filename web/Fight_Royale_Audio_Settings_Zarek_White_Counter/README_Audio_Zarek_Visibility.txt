Fight Royale — Independent Audio Volumes + White Zarek Clash Counter
==================================================================

INSTALL
1. Copy install_audio_zarek_visibility.py into your web/ project folder,
   beside package.json.
2. In PowerShell, from the web/ folder, run:
      py install_audio_zarek_visibility.py
      npx tsc --noEmit
      npm run dev

CHANGES
- src/game/sound.ts: independent music, general effects, and combat feedback
  (clash, parry, block, guard break) volume buses.
- src/ui/Settings.tsx: Music, Sound Effects, Clashes & Parries, Master sliders.
- src/ui/GameView.tsx: Zarek's Clash Counter text becomes white with a
  black shadow so the value and basic-attack speed are easier to see.

HOW TO TEST
- Set Music to 0% and Clashes & Parries to 100%; a weapon clash should
  still sound normal.
- Lower Sound Effects; clash/parry audio should be unaffected.
- Lower Clashes & Parries; those effects should become quieter.
- Lower Master to change every volume together.
- Check Zarek's counter directly below the guard bar. The background,
  count, +20%-per-clash speed boost, and round reset are not changed.

NOTES
- Saves settings in your existing fr-volume localStorage setting.
- The combat feedback slider defaults to 100% for players with older saved
  settings; master volume still affects it.
- Creates timestamped .bak copies of changed files. Don't git add backups.
- Re-running the installer is safe; no duplicate settings or HUD styling.
- The installer preflights all target files before modifying any of them.
  If your local files have diverged from the code available in this chat,
  it stops safely and you should provide src/game/sound.ts,
  src/ui/Settings.tsx, and src/ui/GameView.tsx for a tailored fix.
