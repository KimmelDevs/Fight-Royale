VEY R — BLOOD FESTIVAL AIRBORNE TARGET FIX
==========================================

FIXES
When Blood Festival targets an airborne enemy, the ring of scythes can
spawn at their jump height. This happens because game.ts uses the target's
current position.y as the 3D arena's center.

This patch keeps the enemy's X/Z location but grounds the arena at y=0
in 3D modes. In platform brawl, it uses the top of the platform below
that enemy, when one exists, so the blades aren't suspended above it.

INSTALL
1. Extract install_veyr_festival_ground_fix.py from the ZIP.
2. Copy it into the main fight-royale/web folder (beside package.json).
3. Run from that folder in PowerShell:
       py install_veyr_festival_ground_fix.py
4. Start or restart your game:
       npm run dev
5. Test: Jump with the enemy, cast Veyr's C Blood Festival, confirm
   the scythes appear on the ground instead of following the enemy's height.

SCOPE
- Modifies ONLY src/game/game.ts.
- Creates a timestamped .festival-ground-backup copy of game.ts.
- Safe to run twice: second run reports ALREADY FIXED.
- Compatible with V3, V4, V5, or V6 Blood Festival code.
- Preserves the 6-second active duration, V4 cooldown, Bloodlust,
  lifesteal, basic attack buff, 3x guard damage, block/clash/parry logic,
  AI changes and other character skills.
- No Supabase migration or icons needed.

If script stops with an ERROR, do not force it. Share your current
src/game/game.ts to adapt the patch to your customized version.
