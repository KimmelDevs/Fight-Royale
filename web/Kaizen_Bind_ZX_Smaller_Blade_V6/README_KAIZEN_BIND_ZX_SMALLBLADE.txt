KAIZEN BIND CONTROLS + SMALLER BLADE V6

Targets: Your Kaizen/Zarek V4 Exact Fix with Kaizen Weapon/Guard V5.

CHANGES
- While Kaizen X or V binds an opponent: press Z for forward, X for backward.
- Z/X regain normal skill behavior when there is no bind.
- Both characters stay immobilized until selection or the 4-second timeout.
- Z forward: Kaizen approaches with X bind, launches/slams with V bind.
- X backward: pull enemy toward Kaizen with X bind, throw enemy behind with V bind.
- 28% smaller blade head and matching ridge/edge/tip. Chain, grip and spinning defense untouched.
- The skill HUD temporarily displays new Forward/Backward icons while bound.
- Online snapshots include remaining bind time so the HUD can respond on clients.

INSTALL
1. Back up/commit your current web project.
2. Copy install_kaizen_bind_zx_smallblade.py to web/, beside package.json.
3. Run: py install_kaizen_bind_zx_smallblade.py
4. Run: npx tsc --noEmit
5. Run: npm run dev

The Python script embeds the two 128x128 WebP icons; no separate icon copying is required.
Creates dated backups. Fails before editing if patch anchors are missing. Safe to rerun.
Test in-game for alignment, animation and online behavior.
