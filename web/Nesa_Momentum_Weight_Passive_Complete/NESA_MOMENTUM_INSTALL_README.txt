FIGHT ROYALE - NESA MOMENTUM + WEIGHT PASSIVE COMBINED INSTALLER
===============================================================

INSTALL
1. Extract the entire ZIP into your Fight Royale 'web' folder.
   Keep Install_Nesa_Momentum_Complete.py, the two support .py files,
   the nesa_momentum_assets folder, and nesa_optimized.vrm together.
2. In PowerShell, inside the web folder, run:
   python .\Install_Nesa_Momentum_Complete.py
   Or:
   py .\Install_Nesa_Momentum_Complete.py
3. Run:
   npx tsc --noEmit -p .
   npm run dev

WHAT IT ADDS
- Installs Nesa herself if she is not yet installed; also installs Weight Passive.
- Weight Passive: she still loses HP on hits, but when a swing commits after
  most of its windup, damage or clashes do not cancel it. Blocking a late hammer
  hit prevents 50% of HP damage but still causes knockback (no perfect-parry
  nullification). Dodging still avoids the hit.
- Basic combo: slow heavy windups and very fast contact animations, heavier
  knockback, short follow-up steps to close the distance after each hit.
- Ground charged attack: Momentum Cyclone. Hold and release left mouse to spin.
  Longer hold (up to about 1.75 seconds) creates longer spin (about 0.34-1.52 s)
  with more individual hammer contacts. No aerial juggle or automatic chase.
- Charged aerial attack: while in the air, HOLD left mouse to charge (up to
  0.88 seconds), release to strike toward opponent position. Damage and knockback
  increase with the charge. Auto-releases if Nesa is close to landing.
- Upsie Daisie X: braces the hammer on the ground and then uses it as a lever
  for a flying horizontal kick. The hit check waits until the active kick frame,
  so the move has a useful effective range without a gigantic hitbox.
- GIGA BONK C: a powerful leap-and-slam.
- Heartbreaker High Striker (bonus skill V): a first connected hit stuns a
  fighter for 3 seconds, then Nesa's heart hammer grows to 4x and delivers a
  second giant carnival-smash shockwave. Blocking mitigates damage; dodging
  still avoids the hit. The 3-second stun requires the first strike to connect.
- Five refreshed Nesa icons and optimized 1024px VRM (only copied if missing).

SAFETY
- Backups are created in web/.nesa_installer_backups/ before changes.
- Your existing public/models/nesa.vrm is never overwritten.
- Re-running the main installer does not double apply combat changes.
- Other fighters' existing balance, kits, cooldowns, and mechanics are preserved.
- Tested against the FightRoyale_Source.zip supplied on 2026-11-07;
  TypeScript syntax checked. Browser gameplay/VRM choreography still needs testing.
