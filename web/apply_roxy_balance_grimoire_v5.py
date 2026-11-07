#!/usr/bin/env python3
"""Fight Royale Roxy V5 — gameplay balance, palm-hover grimoire, visible Frostbite HUD.
Requires apply_roxy_freeze_balance_v4.py already installed.
Run inside the web folder. Preflights all edits before writing and backs up changed files.
"""
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path.cwd()
FILES = ['src/game/kits.ts', 'src/game/model.ts', 'src/game/game.ts',
         'src/game/fighter.ts', 'src/ui/GameView.tsx']
try:
    original = {name: (ROOT/name).read_text(encoding='utf-8') for name in FILES}
except OSError as error:
    sys.exit(f'ERROR: {error}. Run inside web/. No files changed.')
new = original.copy()
K, M, G, F, U = FILES
MARK = 'ROXY_BALANCE_GRIMOIRE_FROSTBITE_V5_20261108'
if MARK in original[G]:
    print('Already installed (Roxy V5). No changes made.')
    sys.exit(0)
if 'ROXY_FLOATING_BOOK_FROSTWING_FREEZE_V4_20261108' not in original[G]:
    sys.exit('ERROR: Install Roxy V4 first (apply_roxy_freeze_balance_v4.py). No files changed.')


def exact(path, anchor, value):
    count = new[path].count(anchor)
    if count != 1:
        raise ValueError(f'{path}: expected 1 anchor, got {count}: {anchor[:110]!r}')
    new[path] = new[path].replace(anchor, value, 1)

try:
    # Roxy damage only — every dealing-damage skill and each light/charged projectile.
    exact(K, 't[key] = { ...t[key], style: "frost_shard", pierce: false, size: 0.82 };',
          't[key] = { ...t[key], dmg: Math.round(t[key].dmg * 0.75), style: "frost_shard", pierce: false, size: 0.82 }; // ROXY V5: 25% less light damage')
    exact(K, 'dmg: 57, guard: 16, knock: 1.2, stun: 0.16, speed: 13.0, size: 0.85, count: 4, spread: 0.33,',
          'dmg: 40, guard: 16, knock: 1.2, stun: 0.16, speed: 13.0, size: 0.85, count: 4, spread: 0.33,')
    exact(K, 'dmg: 65, guard: 20, knock: 0.7, stun: 0.08, count: 1, speed: 4.5, radius: 0.9, duration: 8.5,',
          'dmg: 46, guard: 20, knock: 0.7, stun: 0.08, count: 1, speed: 4.5, radius: 0.9, duration: 8.5,')
    exact(K, 'heavy: true, delay: 0.85, radius: 2.1, effect: "slow", effect_t: 2.0, effect_p: 0.65,',
          'heavy: true, delay: 0.85, radius: 2.1, effect: "slow", effect_t: 2.0, effect_p: 0.65,')  # sanity anchor; handle meteor value below
    # Scope the meteor to the named Roxy spell, so Ember's Meteor is unchanged.
    meteor = 'name: "Glacier Meteor", desc: "A huge icy meteor falls on the marked enemy position, damaging and slowing enemies in the impact area.",\n      cd: 15, type: "strike", style: "meteor", wind: 0.36, recover: 0.65, dmg: 245, guard: 65'
    exact(K, meteor, meteor.replace('dmg: 245', 'dmg: 160'))
    bird = 'name: "Frostwing Choir", desc: "Summon 3 stationary Frostwings. Each keeps facing an enemy and fires one ice shard every 2 seconds for 25 seconds.",\n        cd: 25, type: "snow_puppet", style: "bird", wind: 0.35, recover: 0.45,\n        dmg: 26, guard: 8'
    exact(K, bird, bird.replace('cd: 25', 'cd: 52').replace('dmg: 26', 'dmg: 15'))

    # Book floats palm-sized (62% of V4) just above the open right hand, rather than on the hat.
    exact(M, '  private roxyFloatingBook: THREE.Group | null = null;',
          '  private roxyFloatingBook: THREE.Group | null = null;\n  private roxyOpenPalm = 0;')
    exact(M, '''    const b = pivot(this.torso, [-0.62, 0.20, 0.43], [-0.08, -0.28, 0.10]);
    this.roxyFloatingBook = b;''', '''    // ROXY V5: book reduced to a small grimoire hovering above the palm, not held like a gun.
    const b = pivot(this.torso, [-0.48, -0.16, 0.57], [-0.12, -0.35, 0.08]);
    b.scale.setScalar(0.62);
    this.roxyFloatingBook = b;''')
    exact(M, '''      this.roxyFloatingBook.position.y = 0.20 + Math.sin(this.t * 2.4) * 0.042;
      this.roxyFloatingBook.rotation.y = -0.28 + Math.sin(this.t * 1.7) * 0.11;
      this.roxyFloatingBook.rotation.z = 0.10 + Math.sin(this.t * 2.1) * 0.035;''', '''      this.roxyFloatingBook.position.y = -0.16 + Math.sin(this.t * 2.3) * 0.032;
      this.roxyFloatingBook.rotation.y = -0.35 + Math.sin(this.t * 1.8) * 0.09;
      this.roxyFloatingBook.rotation.z = 0.08 + Math.sin(this.t * 2.0) * 0.045;''')
    # Book-sided gentle casting gesture; don't override active casts/hits/guard.
    exact(M, '''    this.arm_r.rotation.x += s * 0.14 * running;
    this.hips.position.y += Math.abs(s) * 0.018 * running;''', '''    this.arm_r.rotation.x += s * 0.14 * running;
    // ROXY V5: free, palm-up right hand supports the levitating grimoire.
    // Applies only to locomotion/idle; attacks, blocks and hit reactions keep original poses.
    if (this.look.element === "frost") {
      // Persistent gesture weight, unlike resetting the joint blend each frame.
      const target = !this.combat && !this.hurt && this.walk < 0.72 ? 1 : 0;
      this.roxyOpenPalm = THREE.MathUtils.damp(this.roxyOpenPalm, target, 9, dt);
      this.arm_r.rotation.x = THREE.MathUtils.lerp(this.arm_r.rotation.x, -0.95, this.roxyOpenPalm);
      this.arm_r.rotation.z = THREE.MathUtils.lerp(this.arm_r.rotation.z, -0.36, this.roxyOpenPalm);
      this.hand_r.rotation.x = THREE.MathUtils.lerp(this.hand_r.rotation.x, 1.15, this.roxyOpenPalm);
      this.hand_r.rotation.z = THREE.MathUtils.lerp(this.hand_r.rotation.z, 0.16, this.roxyOpenPalm);
    }
    this.hips.position.y += Math.abs(s) * 0.018 * running;''')
    exact(M, '''    this.vrmRig.grip = { left: !["mage", "kicks"].includes(this.kit), right: this.kit !== "kicks" };''', '''    // Roxy's fingers remain open; she summons the book rather than grabbing it.
    this.vrmRig.grip = { left: !["mage", "kicks"].includes(this.kit),
      right: this.kit !== "kicks" && this.look.element !== "frost" };''')

    # Visible passive for CPU vs CPU and the normal player HUD.
    exact(G, '      if (f.kit === "hammer") passives.push({ label: "HEARTS", value: `${f.nesaCCharges}/3` });', '''      if (f.look.element === "frost") {
        passives.push({ label: "FROSTBITE", value: `${f.frostShardStacks}/4` });
        if (f.frostShieldT > 0 && f.frostShieldCharges > 0)
          passives.push({ label: "AEGIS", value: `${f.frostShieldCharges}/4` });
      }
      if (f.kit === "hammer") passives.push({ label: "HEARTS", value: `${f.nesaCCharges}/3` });''')
    exact(G, 'chainBindKind: f.chainBindKind }); // KAIZEN_PREDATOR_HOOK_V9',
          'chainBindKind: f.chainBindKind, frostShardStacks: f.frostShardStacks, frostShieldCharges: f.frostShieldCharges, frostShieldT: f.frostShieldT }); // ROXY V5 HUD')
    # Network: show correct Frostbite stack on client controlled characters, not just offline.
    exact(F, 'this.kaizenSpinDirection, this.garrickResolve, +this.cooldowns.v.toFixed(2)];',
          'this.kaizenSpinDirection, this.garrickResolve, +this.cooldowns.v.toFixed(2), this.frostShardStacks, this.frostShieldCharges, +this.frostShieldT.toFixed(2)];')
    exact(F, '    this.garrickResolve = s.length > 51 ? s[51] : 0;', '''    this.garrickResolve = s.length > 51 ? s[51] : 0;
    // Roxy V5 fields appended; backward-compatible with older server snapshots.
    this.frostShardStacks = s.length > 53 ? s[53] : 0;
    this.frostShieldCharges = s.length > 54 ? s[54] : 0;
    this.frostShieldT = s.length > 55 ? s[55] : 0;''')

    ui_meter = '''function RoxyFrostbiteMeter({ stacks, shards, shieldT, right = false }: {
  stacks: number; shards: number; shieldT: number; right?: boolean;
}) {
  const value = Math.max(0, Math.min(3, Math.floor(stacks)));
  return (
    <div style={{ marginTop: 6, padding: "5px 8px", borderRadius: 9,
      background: "rgba(8, 31, 60, .74)", border: "1px solid rgba(132, 222, 255, .45)",
      color: "#bdeeff", fontSize: 11, fontWeight: 800,
      display: "flex", alignItems: "center", justifyContent: right ? "flex-end" : "flex-start", gap: 7 }}>
      <span style={{ letterSpacing: ".03em", whiteSpace: "nowrap" }}>❄ FROSTBITE</span>
      <div style={{ display: "flex", gap: 3 }} aria-label={`Frostbite ${value} of 4`}>
        {Array.from({ length: 4 }, (_, i) => <span key={i} style={{
          width: 10, height: 14, transform: "rotate(35deg) scale(.73)",
          background: i < value ? "#9ceaff" : "rgba(172, 221, 247, .18)",
          border: `1px solid ${i < value ? "#efffff" : "#6186a3"}`,
          boxShadow: i < value ? "0 0 6px #62ccff" : "none",
        }} />)}
      </div>
      <b style={{ fontVariantNumeric: "tabular-nums" }}>{value}/4</b>
      {shieldT > 0 && shards > 0 && <span style={{ color: "#f0fbff", whiteSpace: "nowrap" }}>◇ AEGIS {shards}/4</span>}
    </div>
  );
}

'''
    exact(U, 'function Bar({ v, color, right }: { v: number; color: string; right?: boolean }) {',
          ui_meter + 'function Bar({ v, color, right }: { v: number; color: string; right?: boolean }) {')
    exact(U, '''              <div className="guard"><Bar v={me.guard / me.maxGuard} color={me.guard / me.maxGuard > 0.25 ? "#f2c94c" : "#ff7043"} /></div>''', '''              <div className="guard"><Bar v={me.guard / me.maxGuard} color={me.guard / me.maxGuard > 0.25 ? "#f2c94c" : "#ff7043"} /></div>
              {me.id === "roxy" && <RoxyFrostbiteMeter stacks={me.frostShardStacks} shards={me.frostShieldCharges} shieldT={me.frostShieldT} />}''')
    exact(U, '''              <div className="guard"><Bar v={other.guard / other.maxGuard} color="#f2c94c" right /></div>''', '''              <div className="guard"><Bar v={other.guard / other.maxGuard} color="#f2c94c" right /></div>
              {other.id === "roxy" && <RoxyFrostbiteMeter stacks={other.frostShardStacks} shards={other.frostShieldCharges} shieldT={other.frostShieldT} right />}''')
    # V5 marker only on game.ts to guard repeat installation.
    exact(G, '// ROXY_FLOATING_BOOK_FROSTWING_FREEZE_V4_20261108', '// ROXY_FLOATING_BOOK_FROSTWING_FREEZE_V4_20261108\n// ' + MARK)
except Exception as err:
    sys.exit('INSTALLATION ABORTED: ' + str(err) + '\nNo files changed.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for name in FILES:
    if original[name] == new[name]:
        continue
    dest = ROOT / name
    backup = dest.with_name(dest.name + f'.before_roxy_v5_{stamp}.bak')
    backup.write_text(original[name], encoding='utf-8')
    dest.write_text(new[name], encoding='utf-8')
    print(f'PATCH {name} (backup: {backup.name})')
print('DONE: Roxy V5 applied. Choir V: 52s cooldown, bird shards: 15 dmg, charged shards: 40 each, X: 46 dmg, C meteor: 160 dmg, basics: -25%.')
print('Grimoire: 62% size, closer to open right palm. Frostbite HUD: 4 diamond pips + spectator passive, network synced.')
print('Next: npx tsc --noEmit -p . && npm run build')
