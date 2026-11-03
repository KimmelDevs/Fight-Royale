# Fight Royale (web)

Anime cel-shaded arena fighter that runs in the browser: duels vs CPU, solo survival, and
online co-op survival / PvP duels with friends. Built with Next.js + three.js.

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Deploy to Vercel

Either:

- **CLI:** run `npx vercel` inside this `web` folder and follow the prompts, or
- **GitHub:** push the repo, import it on vercel.com, and set **Root Directory** to `web`.

No environment variables or servers are needed.

## How online play works

The host's browser runs the match; friends join with the 5-letter room code. Browsers connect
directly over WebRTC using PeerJS, whose free public broker (0.peerjs.com) only introduces the
players. Nothing to host besides the static site.

Limits: a few strict networks (some corporate or mobile carriers) block direct WebRTC
connections; those players can't join without a TURN relay.

## Code map

- `src/game/kits.ts` - stats, attacks, skills and poses per class (tune damage/cooldowns here)
- `src/game/roster.ts` - the 10 characters and their looks
- `src/game/model.ts` - procedural cel-shaded character models
- `src/game/mobs.ts` - survival enemies, boss, and wave composition
- `src/game/game.ts` - match rules, combat resolution, waves, perks, network sync, camera
- `src/game/ai.ts` - duel CPU with 4 difficulty levels
- `src/game/net.ts` - PeerJS host/join
- `src/ui/` - React menus, character select, lobby and HUD
