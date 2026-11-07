FIGHT ROYALE — NESA UPSIE DAISIE CHASE MOBILITY (V1)

What it does
------------
* Nesa's Upsie Daisie kick now covers substantially more ground after its
  planted-hammer wind-up, making it better at catching kiting/ranged fighters.
* During the airborne kick Nesa can turn toward opponents who sidestep and can
  add a little movement-based steering in 3D arenas.
* In side-view platform stages she actively travels toward the opponent on the
  horizontal axis; existing stage walls still apply.
* The contact check happens AFTER real airborne forward movement, rather than
  right at take-off. It is still ONE hit (no extra damage ticks).
* The airborne leg has an appropriate vertical hitbox for the higher kick arc.
* Nesa's AI considers the new practical kick travel range.

Preserved exactly
-----------------
* Upsie Daisie damage: 170
* Upsie Daisie cooldown: 9 seconds
* Guard damage: 36
* Knockback: 7.3
* Stun: 0.57 (unchanged)
* Crowd-control immunity during the kick
* Planted-hammer wind-up: 0.40 seconds
* All other Nesa moves and other characters' stats
* Smart AI personalities, spectator mode, and Kira updates

Changes to mobility data
------------------------
* Active kick travel window: 0.16 -> 0.40 seconds
* Skill lunge parameter: 7.8 -> 14.2
* Contact reach: 2.62 -> 2.75
* Kick contact timing adapts to the target's distance instead of occurring
  at a fixed 0.12-second delay.

Installation (after your Smart AI / Nesa updates)
-------------------------------------------------
1. Extract Install_Nesa_Upsie_Chase_V1.py into your Fight Royale 'web' folder.
2. Open PowerShell in the web folder.
3. Run:
     python .\Install_Nesa_Upsie_Chase_V1.py
4. Check and start:
     npx tsc --noEmit -p .
     npm run dev

To validate without changing files:
     python .\Install_Nesa_Upsie_Chase_V1.py --check

If you run the installer again, it skips already-patched files.
Backups are created in web/.nesa_installer_backups/ before modifying files.

Validation
----------
Patch and repeat-install tests passed on the staged latest-game fixture.
All four modified TypeScript files passed transpile syntax diagnostics.
Actual combat/VRM motion has not been tested in a running browser game.
