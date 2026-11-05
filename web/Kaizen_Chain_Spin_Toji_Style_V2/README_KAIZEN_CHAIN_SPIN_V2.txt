KAIZEN V2 — CHAIN-SPIN WEAPON & CHOREOGRAPHY
===========================================

WHAT THIS DOES
- Converts Kaizen's seven attached blade plates into ONE short, sharp blade tethered
  to a visible articulated chain. The chain remains attached to his right-hand grip.
- During basic combos the chained tip swings through alternating clockwise and
  counterclockwise arcs; the chain curves and follows the blade, rather than behaving
  like a stiff sword.
- X — Rending Orbit becomes the signature Toji-inspired spinning-chain animation:
  the blade circles Kaizen while the chain remains tied to his hand, with visible
  delayed blade echoes instead of a generic effect ring.
- Z / Heavy / V use coil, throw, and retract blade paths.
- Unbound Drive retains the extended chain feel; the offhand now remains free for
  balance and body movement instead of gripping the weapon like a greatsword.
- Kaizen continues to use the temporary garrick.vrm. Garrick's own kit is untouched.

INSTALL (requires the original Kaizen V1)
1. Extract install_kaizen_chain_spin_v2.py.
2. Put it directly into Fight-Royale/web beside package.json.
3. In PowerShell in that web/ directory run:

     py install_kaizen_chain_spin_v2.py
     npx tsc --noEmit
     npm run dev

4. In an offline duel, test: basic L1-L4, X, Z, Heavy, V, C, and clashes.
5. Once tested, commit the source changes, NOT .chainspin-v2-backup-* files.

MODIFIED FILES
  src/game/model.ts      (new attached chain, free blade, and spin animations)
  src/game/fighter.ts    (passes Kaizen's current pose to model, host and client)
  src/game/kits.ts       (more natural one-handed poses, same hit/damage stats)
  src/game/vrm.ts        (slightly more agile chainfighter gait)

WHAT IS UNCHANGED
- Damage, cooldowns, hitboxes, status effects, chain pull rules, and skill names.
- Veyr, Garrick, Zarek, and other fighter logic.
- Existing Supabase migration and Kaizen shop registration.
- No new models or icon files needed.

SAFE INSTALLER BEHAVIOR
- Checks all required anchors BEFORE any file is changed.
- Saves backups next to the modified .ts files.
- No duplicates when run again.
- If the script reports an anchor error, STOP and share the error; your files differ.

VALIDATION
- Checked against three saved source versions: Kaizen with Zarek, Kaizen without
  Zarek, and Kaizen alongside Zarek's animation V2.
- TypeScript parser reported no syntax errors.
- A full production build and playable VRM animation were not run in this environment.
- Further tuning may be needed for the exact VRM arm alignment and blade swing radius.

INSPIRATION
- The dynamic chain-and-dagger circling action in Toji's fight with Gojo in
  Jujutsu Kaisen. Uses original game geometry, not copyrighted model assets.
