ZAREK V3 — INFINITE CRESCENT UNPARRYABLE PATCH
===============================================
This adds no_parry: true to the C — Infinite Crescent attack in
src/game/kits.ts. The game's existing stormGlaiveSwing() copies the
base C attack into each of its eight staged attacks, so the setting
applies to the entire ultimate, including the launcher and finisher.

- Perfect parries do not stop Infinite Crescent.
- Ordinary blocking and guard break still work.
- Weapon clashes still work.
- The AI's existing no_parry detection prevents it from attempting
  last-moment parries on this attack.
- This uses the game's standard no_parry flag, which also disables
  the defender's separate counter state against this attack.
- No damage, cooldown, visuals, VRM, or other fighter is changed.

INSTALL:
1. Make sure Zarek V3 Cyclone kit is already installed.
2. Copy install_zarek_unparryable_ultimate.py into web/ beside package.json.
3. From PowerShell in that folder run:
   py install_zarek_unparryable_ultimate.py
   npx tsc --noEmit
   npm run dev
4. Test versus an AI or player: early guard should BLOCK, attacks can
   still CLASH, perfectly timed guard should BLOCK rather than PARRY.

The installer preserves backups of kits.ts and can be run twice safely.
