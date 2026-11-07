#!/usr/bin/env python3
"""Select Zenith's own skill icons without overwriting Zarek's glaive icons.
Run in Fight Royale web/. Safe to repeat; creates a timestamped backup.
"""
from pathlib import Path
from datetime import datetime
import sys
path=Path.cwd()/'src/ui/icons.tsx'
if not path.exists():
    sys.exit('ERROR: Run inside the web folder. src/ui/icons.tsx not found.')
s=path.read_text('utf-8')
old='kit === "mage" ? `mage-${element}` : kit'
new='kit === "mage" ? `mage-${element}` : kit === "glaive" && element === "metal" ? "glaive-metal" : kit'
if new in s:
    print('Zenith skill-icon routing is already installed.');sys.exit(0)
if s.count(old)!=1:
    sys.exit('PREFLIGHT FAILED: icon routing differs from expected source; no files changed.')
bak=path.with_name(path.name+'.before_zenith_icons_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.bak')
bak.write_text(s,'utf-8')
path.write_text(s.replace(old,new,1),'utf-8')
print(f'Zenith Metal icons routed. Backup: {bak.name}')
