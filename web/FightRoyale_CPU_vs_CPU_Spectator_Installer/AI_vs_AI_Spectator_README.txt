FIGHT ROYALE — 1v1 CPU VS CPU SPECTATOR MODE

MAIN INSTALLER:
  Install_FightRoyale_AI_vs_AI_Spectator.py

Installation (Windows PowerShell):
1. Extract the ZIP and put Install_FightRoyale_AI_vs_AI_Spectator.py in your Fight Royale web folder.
2. Open PowerShell in the web folder and run:
     python .\Install_FightRoyale_AI_vs_AI_Spectator.py
   Or pass the path explicitly:
     python .\Install_FightRoyale_AI_vs_AI_Spectator.py "C:\path\to\fight-royale\web"
3. Validate and start:
     npx tsc --noEmit -p .
     npm run dev

IN-GAME:
- Main menu > Watch CPU vs CPU (1v1)
- Click CPU 1 or CPU 2, then pick their fighter from the roster.
- Random is available for either side; all fighters can be selected for this offline spectating mode.
- Choose shared CPU difficulty and click WATCH FIGHT!
- AI fights automatically. You only control pause (Esc), rematch (R) and menu.
- Health bars, round score and results appear automatically. First fighter to win two rounds takes the match.
- No gold, rank changes or player rewards in spectator mode.

FILES PATCHED:
- src/ui/App.tsx
- src/ui/GameView.tsx
- src/game/game.ts
- src/ui/WatchSelect.tsx (new)

Backups: web/.fight_royale_spectator_backups/ <timestamp>
No game balance, fighter stats, move data, AI behavior or combat input bindings modified.
Run --check to validate changes without installing; rerunning is safe.

Tested with Fight Royale source and a Nesa AI/Kira update fixture. TypeScript syntax verified;
full Next.js build and runtime gameplay not verified in this environment.
