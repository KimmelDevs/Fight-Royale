KAIZEN — CHAINBLADE V3 (DIRECTIONAL REWORK)
=================================================
Install prerequisites: Kaizen V1 + Kaizen Chain Spin V2. Works with or without Zarek V3 installed.

1. Extract install_kaizen_directional_v3.py into fight-royale/web/ beside package.json.
2. Open PowerShell in that directory.
3. Run:
    py install_kaizen_directional_v3.py
    npx tsc --noEmit
    npm run dev
4. Test offline vs a CPU first, then test online host + guest. The installer creates timestamped
   .kaizen-v3-backup-* copies of every TypeScript file it modifies; do not commit these backups.

NEW KIT
  BASIC — Dancing Fang: five attacks: side slash, reverse, low sweep, overhead throw,
          and a return hit. Last attack has a separate 45-damage return hit.
  Z — Razor Cyclone: rotating chain cuts. Hold Z (or rebound Skill 1 button) for
      optional extended beats and expanding radius. Up to 1.6 seconds active.
  X — Predator's Hook: hook on hit; recast within 2 seconds to choose pull direction.
  C — Thousand Cuts: Death Spiral: 7 contracting slash pulses then overhead finisher.
      Opponents outside the shrinking radius can avoid later hits.
  V — Serpent Bind (bonus shop skill): catches one target for directional follow-up.

DIRECTIONAL CONTROLS (FACING-RELATIVE, NOT HARDCODED WASD)
  Example with default keyboard and fighter facing RIGHT in side-view:
    D + V: FORWARD launch, then force down and follow-up hit
    A + V: BACKWARD flip over Kaizen to his rear
    D + X (second press): Kaizen moves toward hooked target
    A + X (second press): Enemy is pulled toward Kaizen
  Facing LEFT swaps the keys. If there is no direction on X recast, default is pull.
  In full 3D arena, movement relative to current facing additionally supports
    LEFT + V: throw target to Kaizen's left
    RIGHT + V: throw target to Kaizen's right
  NOTE: The platform mode runs in a 2D plane; it has only left/right world movement.
  Consequently 3D lateral side-throws are meaningful only in arena mode. In platform
  mode W/S retain their normal jump/drop behavior rather than inventing a third axis.

Important:
- This uses the player's configured movement bindings (not literal W/A/S/D keycodes).
- Movement direction is captured at the moment of skill activation/recast.
- Predator's Hook needs TWO key presses: hit first, then choose forward/backward on recast.
- All HP-hit-only throws and pulls can be stopped by a successful block or parry;
  the move does not automatically succeed through shields.
- No Supabase migration is needed. Kaizen ID and shop registration are unchanged.
- Game mechanics are authored and syntax-checked on saved project copies, NOT fully tested
  in a running multiplayer match. Test controller bindings and gameplay before deployment.

ZAREK (OPTIONAL)
  The separate install_zarek_cyclone_v3.py is included because the earlier request was
  to rework Zarek too. It replaces her Z/X/C and 5-hit basic combo. Install Zarek V3
  first if you want that update, then Kaizen V3. Each script is independent.
