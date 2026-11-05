#!/usr/bin/env python3
"""Fight Royale: Kaizen guard recharge 0.5x + non-parry melee guard clashes.

Compatible with Kaizen V5, V6 and V7. Installs only in the main web project.
No dependency on exact Kaizen bind method names. Preflights every edit before writing.
"""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
FIGHTER = ROOT / 'src/game/fighter.ts'
GAME = ROOT / 'src/game/game.ts'
MARKER = 'KAIZEN_GUARD_CLASH_V8'


def once(src: str, old: str, new: str, where: str) -> str:
    count = src.count(old)
    if count != 1:
        raise RuntimeError(f'Preflight: {where} anchor matched {count} times, expected 1. No files changed. Upload your current fighter.ts and game.ts for a tailored patch.')
    return src.replace(old, new, 1)


def patch_fighter(src: str) -> str:
    # Guard regeneration is affected only for chainblade (Kaizen). Everyone else stays at 30/s.
    src = once(src,
        'if (this.guardDelay <= 0) this.guard = Math.min(this.guard + GUARD_REGEN * dt, this.maxGuard);',
        '''if (this.guardDelay <= 0) {
        // KAIZEN_GUARD_CLASH_V8: Kaizen regenerates guard at half the usual rate.
        const guardRegen = this.kit === "chainblade" ? GUARD_REGEN * 0.5 : GUARD_REGEN;
        this.guard = Math.min(this.guard + guardRegen * dt, this.maxGuard);
      }''', 'fighter.ts guard regeneration')

    # This branch occurs AFTER the standard perfect-parry check and AFTER ordinary
    # guard drain / guard-break. It is therefore a physical clash only when a parry
    # didn't happen and the guard was not broken. Projectiles keep normal blocks.
    src = once(src,
        '''      this.knock = a.knock * 0.5;
      this.model.recoil = 0.7;
      return "blocked";''',
        '''      // KAIZEN_GUARD_CLASH_V8: the spinning chain catches incoming melee weapons.
      // Parry (above) and guard break (above) retain priority; projectiles still block.
      if (this.kit === "chainblade" && attacker instanceof Fighter && a.type === "melee") {
        this.knock = Math.min(a.knock * 0.12, 0.5);
        this.model.recoil = 0.85;
        return "kaizen_guard_clash";
      }
      this.knock = a.knock * 0.5;
      this.model.recoil = 0.7;
      return "blocked";''', 'fighter.ts defended melee collision')
    return src


def patch_game(src: str) -> str:
    src = once(src,
        '''    switch (result) {
      case "hit": case "crit": case "ko": {''',
        '''    switch (result) {
      case "kaizen_guard_clash": {
        // KAIZEN_GUARD_CLASH_V8: successful spinning-block contact clashes with a
        // melee attack. The attacker recoils; Kaizen remains guarding. Guard was
        // already drained in receiveHit(), so enough pressure can still break it.
        if (attacker instanceof Fighter) {
          // A clash against Kaizen's rotating chain counts as a real weapon clash
          // for Zarek's round-based Clash Counter.
          if (attacker.kit === "glaive") {
            attacker.clashMomentum += 1;
            this.fxp("num", attacker.chest().add(new THREE.Vector3(0, 0.9, 0)),
              `CLASH ${attacker.clashMomentum} • ${Math.min(2, 1 + Math.min(5, attacker.clashMomentum) * .2).toFixed(1)}x BASIC SPD`,
              "#a6efff", 0.8);
            this.fxp("lightning", attacker.chest(), "#6acfff");
          }
          attacker.clashRecoil();
        }
        this.snd("clash", 0.9);
        this.fxp("sparks", shieldPos, "#fff0c2", 38, 8);
        this.fxp("sparks", shieldPos, "#d65a6e", 12, 5);
        this.fxp("flash", shieldPos, "#ffe0b0", 0.46, 0.15, 0.85);
        this.fxp("ring", shieldPos, "#ffe0b0", 1.7, 0.25, 0.8);
        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.5, 0)),
          "CLASH!", "#ffe08a", 1.1);
        this.add_trauma(0.3);
        this.hitStop(0.09);
        break;
      }
      case "hit": case "crit": case "ko": {''', 'game.ts applyHit switch')
    return src


def main():
    for path in [FIGHTER, GAME]:
        if not path.exists():
            raise RuntimeError(f'Missing {path.relative_to(ROOT)}. Put this installer beside web/package.json.')
    originals = {FIGHTER: FIGHTER.read_text(encoding='utf-8'), GAME: GAME.read_text(encoding='utf-8')}
    already = [MARKER in text for text in originals.values()]
    if all(already):
        print('Kaizen Guard Clash V8 is already installed. No files changed.')
        return
    if any(already):
        raise RuntimeError('Partial V8 installation detected; no files changed. Share fighter.ts and game.ts to reconcile.')
    if 'KAIZEN_WEAPON_V5' not in originals[GAME] or 'chainblade' not in originals[FIGHTER]:
        raise RuntimeError('Kaizen V5 spinning guard is missing in current source. Install that first; no files changed.')
    # Full preflight in memory first — failure here cannot modify disk.
    changes = {FIGHTER: patch_fighter(originals[FIGHTER]), GAME: patch_game(originals[GAME])}
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    for path, new_text in changes.items():
        backup = path.with_name(f'{path.name}.before-kaizen-v8-{stamp}.bak')
        shutil.copy2(path, backup)
        path.write_text(new_text, encoding='utf-8')
        print('PATCH', path.relative_to(ROOT))
        print('BACKUP', backup.relative_to(ROOT))
    print('DONE: Kaizen 0.5x guard regeneration and defensive melee clashes; parries retained.')
    print('Test: npx tsc --noEmit; npm run dev')


if __name__ == '__main__':
    main()
