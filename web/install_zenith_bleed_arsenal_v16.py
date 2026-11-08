#!/usr/bin/env python3
"""Fight Royale V16 — V15 Bleed/AI fix + persistent Zenith spear volley.

Requirements: Fight Royale V14 or V15 source.
Run: python install_zenith_bleed_arsenal_v16.py [path/to/fight-royale/web]
No additional Python packages. Validates all anchors before touching any file;
creates per-file backups, commits atomically, and safely skips repeat installs.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

TAG = "ZENITH_BLEED_SKILL_ONLY_AI_V15"
TAG16 = "ZENITH_COMMITTED_SPEAR_VOLLEY_V16"


def replace_once(data: str, old: str, new: str, context: str) -> str:
    count = data.count(old)
    if count != 1:
        raise ValueError(f"{context}: expected one anchor, found {count}: {old[:100]!r}")
    return data.replace(old, new, 1)


def patch_status(data: str) -> str:
    if TAG in data:
        return data
    data = replace_once(
        data,
        '  bleed: { label: "BLEED", color: "#e0303e", bit: 4, text: (t, p) => `Bleed: ${p} dmg/s per stack for ${t}s (Zenith: up to x5; x1.5 while moving)` },',
        '  bleed: { label: "BLEED", color: "#e0303e", bit: 4, text: (t, p) => `Bleed: ${p} dmg/s per stack for ${t}s (Zenith skills only: up to x2; x1.5 while moving)` },',
        'Bleed status description',
    )
    data = replace_once(data, 'const POISON_STACKS = 3;',
                        'const POISON_STACKS = 3;\nconst ZENITH_BLEED_MAX_STACKS = 2; // ' + TAG,
                        'Bleed cap declaration')
    data = replace_once(data, '      cur.stacks = Math.min(5, cur.stacks + 1);',
                        '      cur.stacks = Math.min(ZENITH_BLEED_MAX_STACKS, cur.stacks + 1);',
                        'Bleed reapplication cap')
    return data


def patch_game(data: str) -> str:
    if TAG in data:
        return data
    old = '''    // ZENITH_TEMPO_01X_5S_V7: +0.01x speed and one BLEED stack per
    // successful physical/projectile contact. Guard, parry, clash and DOT ticks
    // never grant stacks. Bleed caps at x5 and refreshes for 5s on reapplication.
    if (attacker instanceof Fighter && attacker.kit === "glaive" &&
        attacker.look.element === "metal" && a.dmg > 0 &&
        (result === "hit" || result === "crit" || result === "ko")) {
      attacker.zenithTempoStacks = Math.min(14, attacker.zenithTempoStacks + 1);
      attacker.zenithMagneticChargeT = 5;
      if (result !== "ko" && (d instanceof Fighter || d instanceof Mob)) {
        const n = d.status.applyStackingBleed(5, 5, attacker);
        if (d instanceof Fighter) d.bleedDisplayStacks = n;
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.9, 0)),
          `BLEED ×${n}/5`, "#ff566a", 0.55);
        if (n === 5) this.fxp("motes", d.chest(), "#ff647a", 10);
      }
    }'''
    new = '''    // ZENITH_BLEED_SKILL_ONLY_AI_V15: ALL successful damaging contacts keep
    // earning Tempo, but only her Z/X/C/V *skill* strikes apply Bleed (max 2).
    // In particular: l1-l5, Phantom Fang, heavy, and parry counters do not bleed.
    // Resolve outcomes first: blocked, parried and clashed strikes never count.
    if (attacker instanceof Fighter && attacker.kit === "glaive" &&
        attacker.look.element === "metal" && a.dmg > 0 &&
        (result === "hit" || result === "crit" || result === "ko")) {
      attacker.zenithTempoStacks = Math.min(14, attacker.zenithTempoStacks + 1);
      attacker.zenithMagneticChargeT = 5;
      // Generated X/V projectiles carry 'zenith_construct'; X melee beats
      // carry 'zenith_barrage' or 'zenith_twin'. Z and C have dedicated styles.
      const zenithSkillBleed = a.style === "zenith_rail" ||
        a.style === "zenith_barrage" || a.style === "zenith_twin" ||
        a.style === "zenith_dash" || a.style === "zenith_arsenal" ||
        a.style === "zenith_construct";
      if (zenithSkillBleed && result !== "ko" &&
          (d instanceof Fighter || d instanceof Mob)) {
        const n = d.status.applyStackingBleed(5, 5, attacker);
        if (d instanceof Fighter) d.bleedDisplayStacks = n;
        this.fxp("num", d.chest().add(new THREE.Vector3(0, 0.9, 0)),
          `BLEED ×${n}/2`, "#ff566a", 0.55);
        if (n === 2) this.fxp("motes", d.chest(), "#ff647a", 10);
      }
    }'''
    data = replace_once(data, old, new, 'Zenith damage-triggered Tempo and Bleed')
    # A stale display counter may exceed the new cap in a network snapshot.
    data = replace_once(
        data,
        'bleedStacks: f.status.has("bleed") ? Math.max(f.status.stacks("bleed"), f.bleedDisplayStacks) : 0,',
        'bleedStacks: f.status.has("bleed") ? Math.min(2, Math.max(f.status.stacks("bleed"), f.bleedDisplayStacks)) : 0,',
        'Zenith Bleed opponent status readout',
    )
    return data


def patch_ui(data: str) -> str:
    if TAG in data:
        return data
    # Applies to player and opponent counters, not the compact spectator layout.
    expected = 'bleedStacks}/5'
    if data.count(expected) != 2:
        raise ValueError(f"Bleed HUD: expected 2 counter caps, got {data.count(expected)}")
    data = data.replace(expected, 'bleedStacks}/2')
    # Comment marker inside TypeScript (safe to read on next run).
    data += '\n// ' + TAG + ': player and enemy Bleed counters show max 2.\n'
    return data


def patch_ai(data: str) -> str:
    if TAG in data:
        return data
    # This early return held block and cleared all offense EVERY frame of Zenith
    # Tempo, causing CPU opponents to stop fighting until the 5s timer ran out.
    old = '''    // ZENITH_TEMPO_GUARD_STALL_V8: the public Tempo bar makes this a visible,
    // counterable strategy. Keep an ordinary guard up to deny successful hits
    // until the real 5s timer expires. Never grant invulnerability/extra guard.
    // At low guard, disengage using actual movement/dash rules to avoid a break.
    const visibleTempo = o.zenithTempoStacks > 0 && o.zenithMagneticChargeT > 0;
    if (visibleTempo && f.kit !== "scythe" && canInput && !f.dashing() && gap < 3.85) {
      const guardLow = f.guard < f.maxGuard * (charged ? 0.47 : 0.39);
      this.queue = []; this.hold = 0;
      this.blockWait = -1; this.blockHold = 0;
      f.intent.attack = false;
      f.intent.skill = "";
      if (guardLow) {
        const escape = safeDirection(relative.clone().addScaledVector(side, 0.43).normalize());
        f.intent.block = false;
        f.intent.move.copy(escape);
        if (f.dashCd <= 0) f.intent.dash.copy(escape);
      } else {
        f.intent.block = true;
        const kite = safeDirection(relative.clone().multiplyScalar(0.70)
          .addScaledVector(side, 0.38).normalize());
        f.intent.move.copy(kite).multiplyScalar(0.54);
      }
      return true;
    }'''
    new = '''    // ZENITH_BLEED_SKILL_ONLY_AI_V15: Tempo is NOT an incoming attack.
    // Previous code forced continuous guarding until Tempo expired, which
    // prevented CPU opponents from swinging or casting any offensive skill.
    // Now guard/parry/dash only for OBSERVED spear swings below, then punish
    // real recovery or run the normal AI offense even while Tempo is active.
    // No extra reaction speed, free parries, damage or cooldown advantage.
    const visibleTempo = o.zenithTempoStacks > 0 && o.zenithMagneticChargeT > 0;
    // Tempo tightens actual swing defense but never vetoes counterattacking.
    // Keeping it in the condition means no fake knowledge of future inputs.'''
    data = replace_once(data, old, new, 'Endless Tempo guard against Zenith')
    # Make Tempo matter only when an actual melee windup is visible; otherwise
    # allow normal offense. Existing skill defenses and recover punish remain.
    data = replace_once(
        data,
        '        this.antiZenithGuardUntil = now + (charged ? 0.37 : 0.30);',
        '        this.antiZenithGuardUntil = now + (charged || visibleTempo ? 0.34 : 0.30);',
        'Observed swing guard window',
    )
    # Full-stack Bleed targeting used to bias Zenith toward X / movement.
    # The new 2-stack maximum is skill-only; basics still generate Tempo.
    for oldline, newline in [
        ('// a legitimate combo, earn 5 Bleed stacks, then refresh the 5s tempo.',
         '// a legitimate combo, earn Tempo with basics and up to 2 Bleed stacks from skills.'),
        ('activeTempo && bleed < 5 && this.zenithTwinSwings >= 1',
         'activeTempo && bleed < 2 && this.zenithTwinSwings >= 1'),
        ('activeTempo && !guarding && bleed < 5',
         'activeTempo && !guarding && bleed < 2'),
        ('urgent || bleeding < 5', 'urgent || bleeding < 2'),
        ('// slow charging while preserving occasional guard-break attempts.',
         '// slow charging while preserving occasional guard-break attempts.'),
        ('// Zenith: landed light hits build 0.01x tempo (5s) and x5 Bleed; prefer them to',
         '// Zenith: landed basics build +0.01x Tempo (5s); ONLY skills inflict x2 Bleed; prefer basics to'),
    ]:
        if oldline != newline:
            data = replace_once(data, oldline, newline, 'Zenith AI skill Bleed priorities')
    return data


def patch_game_v16(data: str) -> str:
    """Keep Zenith's committed V spear volleys going after hit-stun."""
    if TAG16 in data:
        return data
    data = replace_once(data,
        '      if (za.style === "zenith_arsenal") { this.zenithArsenal(f, za); return; }',
        '''      // ZENITH_COMMITTED_SPEAR_VOLLEY_V16: the first physical bloom spear
      // commits V. Timed follow-ups survive hit-stun or knockback.
      if (za.style === "zenith_arsenal") {
        if (this.zenithV16Committed.get(f) !== f.swingSerial)
          this.zenithArsenal(f, za);
        return;
      }''',
        'V onSwing duplicate prevention')
    data = replace_once(data,
        '  private zenithV12Seen = new WeakMap<Fighter, number>();',
        '''  private zenithV12Seen = new WeakMap<Fighter, number>();
  private zenithV16Committed = new WeakMap<Fighter, number>(); // ''' + TAG16,
        'Committed-volley map')
    data = replace_once(data,
        '''      const pivot = f.chest();
      // One restrained magnetic halo instead of an opaque blast of particles.''',
        '''      const pivot = f.chest();
      // Snapshot the launching weapon, timing, and anchor. Getting hit will
      // not move the origin or delete spears that already began firing.
      const castAtk: Attack = { ...f.atk! };
      const castYaw = f.root.rotation.y;
      const castPower = f.atkPower;
      const windupLeft = Math.max(0, castAtk.wind - f.stateT);
      // One restrained magnetic halo instead of an opaque blast of particles.''',
        'V cast snapshot')
    data = replace_once(data,
        '''          if (round !== this.round || f.isDown() || f.swingSerial !== serial ||
              f.state !== S.ATTACK || f.atk?.style !== "zenith_arsenal") return;
          const original = f.atk;
          const radius = outer ? 1.02 : 0.70;
          const origin = f.chest().add(new THREE.Vector3(''',
        '''          // Before the FIRST bloom spear, interruption cancels V.
          // Once a real spear launches, the rest are independent of Zenith.
          if (round !== this.round) return;
          if (this.zenithV16Committed.get(f) !== serial &&
              (f.isDown() || f.swingSerial !== serial ||
               f.state !== S.ATTACK || f.atk?.style !== "zenith_arsenal")) return;
          if (this.zenithV16Committed.get(f) !== serial) {
            this.zenithV16Committed.set(f, serial);
            // Preserve original cast timing and launch even after stagger.
            this.later(Math.max(0, windupLeft - delay), () => {
              if (round !== this.round) return;
              this.zenithArsenal(f, castAtk, pivot.clone(), castYaw, castPower);
            });
          }
          const original = castAtk;
          const radius = outer ? 1.02 : 0.70;
          const origin = pivot.clone().add(new THREE.Vector3(''',
        'V windup spear interruption')
    data = replace_once(data,
        '  private zenithArsenal(f:Fighter,a:Attack) {',
        '''  private zenithArsenal(f:Fighter,a:Attack,
    originAtCast?: THREE.Vector3, yawAtCast?: number, powerAtCast?: number) {''',
        'V barrage anchored signature')
    data = replace_once(data,
        '''    const round=this.round;
    const tempo=f.zenithAttackSpeed();
    const target=f.opponent&&!f.opponent.isDown()?f.opponent:this.enemiesOf(f)[0]??null;
    if(!target) return;
    const point=target.root.position.clone();''',
        '''    const round=this.round;
    const tempo=f.zenithAttackSpeed();
    const target=f.opponent&&!f.opponent.isDown()?f.opponent:this.enemiesOf(f)[0]??null;
    if(!target) return;
    const fixedOrigin = originAtCast?.clone() ?? f.chest();
    const fixedYaw = yawAtCast ?? f.root.rotation.y;
    const fixedPower = powerAtCast ?? f.atkPower;
    const point=target.root.position.clone();''',
        'Snapshot of committed V barrage')
    data = replace_once(data,
        '''      if (round !== this.round || f.isDown() || target.isDown()) return;
      const right = new THREE.Vector3(Math.cos(f.root.rotation.y), 0,
        -Math.sin(f.root.rotation.y));
      const from = f.chest().addScaledVector(right, j === 0 ? -0.36 : 0.36)''',
        '''      if (round !== this.round || target.isDown()) return;
      const right = new THREE.Vector3(Math.cos(fixedYaw), 0,
        -Math.sin(fixedYaw));
      const from = fixedOrigin.clone().addScaledVector(right, j === 0 ? -0.36 : 0.36)''',
        'V rail telegraph anchor')
    data = replace_once(data,
        '''      if(this.round!==round||f.isDown())return;
      const finisher = i >= 12;''',
        '''      if(this.round!==round)return; // committed volleys survive hit-stun, even if owner KO'd
      const finisher = i >= 12;''',
        'V committed shot launch guard')
    data = replace_once(data,
        '''      const finisherRight = new THREE.Vector3(Math.cos(f.root.rotation.y), 0,
        -Math.sin(f.root.rotation.y));
      const origin = finisher ? f.chest().addScaledVector(finisherRight,''',
        '''      const finisherRight = new THREE.Vector3(Math.cos(fixedYaw), 0,
        -Math.sin(fixedYaw));
      const origin = finisher ? fixedOrigin.clone().addScaledVector(finisherRight,''',
        'V spear displacement independence')
    data = replace_once(data,
        '''      const p=this.spawnProjectile(f,f.team,part,f.atkPower*power,origin,toward.normalize().multiplyScalar(finisher?26:17),''',
        '''      const p=this.spawnProjectile(f,f.team,part,fixedPower*power,origin,toward.normalize().multiplyScalar(finisher?26:17),''',
        'V damage power snapshot')
    return data


def patch_game_both(data: str) -> str:
    # One installer works on V14 (apply V15+V16) and V15 (V16 only).
    return patch_game_v16(patch_game(data))


def find_web() -> Path:
    if len(sys.argv) > 2:
        raise ValueError('Usage: python install_zenith_bleed_arsenal_v16.py [web folder]')
    here = Path(__file__).resolve().parent
    options = [Path(sys.argv[1]).expanduser().resolve()] if len(sys.argv) == 2 else [
        here, Path.cwd(), here / 'web', Path.cwd() / 'web'
    ]
    for folder in options:
        if (folder / 'src/game/game.ts').is_file() and (folder / 'src/game/ai.ts').is_file():
            return folder.resolve()
    raise FileNotFoundError('Run from fight-royale/web, or pass the web folder as an argument.')


def main() -> int:
    try:
        root = find_web()
        targets: list[tuple[str, Callable[[str], str]]] = [
            ('src/game/status.ts', patch_status),
            ('src/game/game.ts', patch_game_both),
            ('src/game/ai.ts', patch_ai),
            ('src/ui/GameView.tsx', patch_ui),
        ]
        # Don't allow installing V15 before the user's confirmed V14 balance.
        fighter = (root / 'src/game/fighter.ts').read_text(encoding='utf-8')
        if 'NYTHERA_ZENITH_LOWER_CAPS_V14' not in fighter:
            raise ValueError('V14 speed balance not detected. Install V14 first.')
        updates = []
        for rel, patch in targets:
            dest = root / rel
            before = dest.read_text(encoding='utf-8')
            after = patch(before)
            if before != after:
                updates.append((rel, dest, before, after))
        if not updates:
            print('V16 already installed; nothing to change.')
            return 0
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        staged = []
        committed = []
        try:
            for rel, dest, before, after in updates:
                backup = dest.with_name(f'{dest.name}.before_{TAG16}_{stamp}.bak')
                temp = dest.with_name(f'{dest.name}.{TAG16}.tmp')
                backup.write_text(before, encoding='utf-8')
                temp.write_text(after, encoding='utf-8')
                staged.append((rel, dest, backup, temp))
            for rel, dest, backup, temp in staged:
                os.replace(temp, dest)
                committed.append((dest, backup))
                print('UPDATED:', rel)
        except Exception:
            for dest, backup in reversed(committed):
                shutil.copy2(backup, dest)
            raise
        finally:
            for _, _, _, temp in staged:
                if temp.exists():
                    temp.unlink()
        print('\nV16 installed successfully')
        print('  Zenith BLEED: maximum 2 stacks, only Z/X/C/V skill damage applies it.')
        print('  Zenith Tempo: +0.01x per successful hit, expires 5s after last hit (unchanged).')
        print('  Opponent CPUs: react to actual attacks and counterattack during active Tempo.')
        print('  Zenith AI: updated Bleed skill priorities to the 2-stack cap.')
        print('  First launched bloom spear commits the V volley and remaining spear launches.')
        print('  Zenith getting hit no longer cancels committed spear shots.')
        print('  No homing, automatic hits, damage changes, or CPU HUD changes.')
        print('  V14 speed caps and other heroes are unchanged.')
        print('  Type-check: npx tsc --noEmit -p .')
        return 0
    except Exception as exc:
        print('ERROR:', exc)
        print('All modifications are validated before writing. No changes if validation fails.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
