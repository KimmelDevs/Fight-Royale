Fight Royale — Enemy CPU Dodge vs. Nesa + Kira Three Air Kicks
=============================================================

1) Copy Install_Nesa_Dodge_Kira_3AirKicks.py into your Fight Royale "web" folder.
2) In PowerShell, from the web folder run:

   python .\Install_Nesa_Dodge_Kira_3AirKicks.py

3) Verify the project's TypeScript and launch:

   npx tsc --noEmit -p .
   npm run dev

Changes:
* ENEMY CPU (all AI characters when fighting Nesa): reacts to hammer swing
  telegraphs, can dash to the side or retreat, avoids repeatedly blocking
  Nesa's high-chip swings. Easy/Normal/Hard/Master differ in dodge frequency.
  Dodge uses the game's existing cooldown and invulnerability rules.
* KIRA (kicks kit): can tap Attack up to three times in one jump. The next
  kick may be buffered by clicking before the previous kick finishes.
  Each kick uses a real melee hitbox, can be blocked or clashed, but cannot
  be perfect-parried. Three distinct right/left/turning aerial poses.
* Nesa V6 1:0.75 charge spins, damage, stats, skills, Weight Passive and
  other fighter kits remain unchanged.

Options:
   python .\Install_Nesa_Dodge_Kira_3AirKicks.py --check
   python .\Install_Nesa_Dodge_Kira_3AirKicks.py "C:\path\to\fight-royale\web"

Backup folder: web\.combat_ai_installer_backups\<timestamp>\
Repeat runs do not duplicate the patch.

Validation: dry-run and install on source fixtures, repeat install, and
TypeScript syntax parser check. Browser/gameplay behavior still requires
in-game validation.
