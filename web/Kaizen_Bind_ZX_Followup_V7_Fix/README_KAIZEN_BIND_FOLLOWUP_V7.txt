KAIZEN V7 — BIND FOLLOW-UP INPUT FIX
===================================

This fixes the issue where pressing Z or X while an enemy was chain-bound
immediately released the bind and could activate normal Z/X skills.

REQUIRES
  Kaizen Bind Z/X + Smaller Blade V6 (and its earlier V4/V5 dependencies)

INSTALL (Windows PowerShell)
  1. Extract install_kaizen_bind_followup_v7.py into your main `web` folder.
     It must sit beside package.json.
  2. Open PowerShell in `web`.
  3. Run:
        py install_kaizen_bind_followup_v7.py
        npx tsc --noEmit
        npm run dev

CONTROLS
  X or V: land a bind, trapping both fighters.
  While bound, press Z: forward follow-up.
  While bound, press X: backward follow-up.
  No selection for four seconds: bind releases automatically.
  Z/X normal skills work outside a bind.

FIXES
  - New Z/X input is consumed and never also cast as a normal skill.
  - Both fighters remain input-locked until the selected follow-up completes.
  - Predator's Hook follow-up stays bound for 0.38s.
  - Serpent Bind backward throw stays bound for 0.48s.
  - Serpent Bind forward launch/slam stays bound for 0.85s, covering its
    delayed 0.67s finishing hit; the victim can still move vertically.
  - The chains still time out after 4s if nothing is selected.
  - Only src/game/fighter.ts is modified; it creates a timestamped backup.
  - Existing V6 blade size, V5 spinning defense and Zarek are not modified.

SAFETY
  The installer checks for exact V6 anchors before making edits. If the
  preflight fails, no file is modified. Do not rerun older installers.

VALIDATION
  Tested on two saved V6 project copies; the patched file was parsed via
  TypeScript's transpiler, without syntax diagnostics. Full typechecking and
  live combat/multiplayer tests must be done in your project.
