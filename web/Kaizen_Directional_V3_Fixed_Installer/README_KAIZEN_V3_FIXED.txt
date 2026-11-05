KAIZEN V3 — FIX FOR "isOrbit anchor found 0"

The old V3 installer assumes Kaizen Chain Spin V2 has already been applied.
This ZIP includes a safe wrapper that handles V2 automatically when needed.

INSTRUCTIONS
1. Extract ALL THREE .py files into your Fight Royale web/ directory beside package.json.
2. From PowerShell inside web/, run:
     py install_kaizen_v3_fixed.py
     npx tsc --noEmit
     npm run dev
3. Test Kaizen Z/X/C/V offline before multiplayer.

IMPORTANT
- Run ONLY install_kaizen_v3_fixed.py (not the other two).
- It preflights both installers in a temporary copy before editing your actual game.
- It creates named backups beside each changed TypeScript file.
- Running it again if V3 is installed makes no changes.
- Previous failed V3 run should have left files unchanged, because the original installer
  only writes after all its patches succeed.
- If your live files have been manually edited or diverged, the preflight may still fail.
  In that case do not force changes; share src/game/model.ts and its error log.
- It does not touch your other game balances, Supabase or VRM assets.
