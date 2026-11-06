NESA V5 — Heartbreaker & charge balance fixes

PREREQUISITE
  Nesa Heart Smash V4 must already be installed.
  Works with or without the standalone No-Foot-Heaviness updater.
  No new VRM or icon assets needed; retains existing Nesa art and visuals.

INSTALL
  1. Extract Install_Nesa_V5_Fixes.py into your Fight Royale web folder.
  2. Open PowerShell in that folder.
  3. Optional dry run: py .\Install_Nesa_V5_Fixes.py --check
  4. Run: py .\Install_Nesa_V5_Fixes.py
  5. Validate: npx tsc --noEmit -p .
  6. Start: npm run dev

CHANGES
- Heartbreaker High Striker: no forced 3-second stun; retains its two blows and 4x hammer.
- Pink Heart Smash: three charges now track the ability, not keyboard C. Applies in Z, X or C slot.
  Heartbreaker is always on its own normal cooldown even when equipped in C.
  Skill HUD and pre-swing cancellation refunds follow the real ability too.
- Upsie Daisie: its CC immunity and lever-kick behavior follow its loadout slot.
- Ground charge: same hold time gives HALF the former actual spinning duration and fewer hits.
- Air charge: release to spin the horizontal hammer with real multiple hit windows.
  Air spin duration and damage depend on hold time, with the same 50% duration scaling.
- Idle and charge poses: stand upright with nearly straight knees; burden remains in upper body.
  Nesa gets her own upright VRM movement profile. Garrick and other fighters unchanged.

SAFETY
- Standalone Python; no pip packages.
- Creates timestamped backups in web/.nesa_installer_backups/ before changing any source.
- Reruns are idempotent (will report already installed).
- Installer patches only kits.ts, fighter.ts, game.ts, model.ts, vrm.ts.

TESTING
- Patch and idempotence checks passed on two Nesa V4 project snapshots.
- All five edited files passed TypeScript syntax parsing.
- Not an in-game or full TypeScript typecheck. Verify animation and gameplay locally.
