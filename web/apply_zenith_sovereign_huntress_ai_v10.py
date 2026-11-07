#!/usr/bin/env python3
"""Fight Royale — Zenith V10 FINAL: sovereign spear/twin AI + 14-weapon V.

Run from fight-royale/web, after Zenith V9. Only edits three source files:
  src/game/ai.ts, src/game/game.ts, src/game/kits.ts

Idempotent, strict preflight, timestamped .bak files and rollback on write errors.
Does not edit Zarek, sword damage, basics, Magnetic Charge, catch/CC immunity,
V cooldown, projectile networking, or existing thrown-spear rules.
"""
from pathlib import Path
from datetime import datetime
import os
import shutil
import sys
import tempfile

ROOT = Path.cwd()
A, G, K = 'src/game/ai.ts', 'src/game/game.ts', 'src/game/kits.ts'
FILES = (A, G, K)
MARK = 'ZENITH_SOVEREIGN_HUNTRESS_V10_20261108'
try:
    before = {f: (ROOT / f).read_text(encoding='utf-8') for f in FILES}
except OSError as e:
    sys.exit(f'ERROR: Run this from your web/ folder. {e}. No changes made.')
if MARK in before[A]:
    print('Zenith V10 is already installed. No files changed.')
    sys.exit(0)
if ('ZENITH_PHANTOM_FANG_MAGNETIC_CHARGE_V9_20261108' not in before[K]
    or 'zenithMagneticChargeT' not in before[A]
    or 'private zenithArsenal(f:Fighter,a:Attack)' not in before[G]):
    sys.exit('PREFLIGHT ERROR: Zenith V9 source is required. No files changed.')

after = before.copy()

def once(path, anchor, replacement):
    count = after[path].count(anchor)
    if count != 1:
        raise ValueError(f'{path}: unique preflight anchor matched {count} times: {anchor[:120]!r}')
    after[path] = after[path].replace(anchor, replacement, 1)

try:
    # Zenith has her own identity, not the same clash-momentum personality as Zarek.
    once(A,
        '  zenith: { range: 2.20, heavy: 0.30, combo: 0.90, bait: 0.34, pressure: 0.92, skillBias: [1.15, 1.65, 1.10] },',
        '  zenith: { range: 2.10, heavy: 0.12, combo: 0.98, bait: 0.25, pressure: 1.00, skillBias: [1.45, 1.35, 1.10] },')
    once(A,
        '  zenith:  { role: "glaive", pressure: 1.42, probe: 0.95, reset: 0.35, vReserve: 0.92, spacing: -0.04 },',
        '  zenith:  { role: "duelist", pressure: 1.85, probe: 0.63, reset: 0.17, vReserve: 0.89, spacing: -0.16 },')

    # Separate special-move brain: reads only current observable states, equipped
    # cooldowns, spear presence, buff duration, and opponent animations/recovery.
    # All skill use is still enacted by legal f.intent.skill buttons.
    once(A, '  private zenithSkillNextAt = 0;', '''  // ZENITH_SOVEREIGN_HUNTRESS_V10_20261108
  // Three-phase signature: Measure with spear -> Release spear to engage with
  // fast blades -> Reclaim spear for the protected magnetic-catch reset.
  // Tunable AI parameters (seconds and arena meters; NOT new combat stats).
  private readonly zenithTactics = {
    spearGuard: 2.05, twinRange: 1.54, throwMin: 2.65, throwMax: 8.25,
    twinMinTime: 0.85, twinPreferTime: 1.35, twinMaxTime: 2.32,
    xRange: 2.62, vMin: 2.85, vMax: 7.40,
  };
  private zenithTwinSwings = 0;
  private zenithTwinLastSerial = -1;
  private zenithOrbitSide = Math.random() > 0.5 ? 1 : -1;
  private zenithOrbitRefreshAt = 0;

  private zenithV10SkillPlan(f: Fighter, o: Fighter): boolean {
    if (f.kit !== "glaive" || f.look.element !== "metal" || f.isDown() || o.isDown()) return false;
    const now = this.threats.now();
    if (this.zenithEnemyId !== o.id) {
      this.zenithEnemyId = o.id;
      this.zenithSpearWasOut = false;
      this.zenithSpearObservedAt = -1;
      this.zenithTwinLastSerial = -1;
      this.zenithTwinSwings = 0;
      this.zenithSkillNextAt = now + 0.25;
    }
    if (f.zenithSpearOut !== this.zenithSpearWasOut) {
      this.zenithSpearWasOut = f.zenithSpearOut;
      this.zenithSpearObservedAt = f.zenithSpearOut ? now : -1;
      this.zenithTwinSwings = 0;
      this.zenithTwinLastSerial = -1;
    }
    if (f.zenithSpearOut && f.state === S.ATTACK && /^l[1-5]$/.test(f.atkId) &&
        f.swingSerial !== this.zenithTwinLastSerial) {
      this.zenithTwinLastSerial = f.swingSerial;
      this.zenithTwinSwings++;
    }
    // Catch recoil must finish. Emergency defenses and genuine attack commitments
    // win over scripted personality choices. No cheating through skill cooldowns.
    if (!f.onGround || f.chainBindT > 0 || f.chainBoundBy ||
        f.zenithCatchRecoilT > 0.08 || f.status.has("freeze") ||
        now < this.zenithSkillNextAt || f.intent.skill || f.intent.attack ||
        f.intent.dash.lengthSq() > 0.01 || f.intent.block ||
        this.blockWait >= 0 || this.blockHold > 0 ||
        this.comboParryTarget > now || this.projectileSwordCommit > 0) return false;
    const free = f.state === S.IDLE || f.state === S.BLOCK || f.state === S.CHARGE ||
      (f.state === S.ATTACK && f.atkPhase === 2 && !!f.atk);
    if (!free) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const enemyRecovery = this.hasPunishWindow(o) || o.state === S.HITSTUN ||
      o.state === S.STAGGER;
    const enemyPreparing = o.state === S.ATTACK && o.atkPhase === 0 &&
      gap < (o.atk?.reach ?? 2) + 0.8;
    const guardWeak = o.guard < o.maxGuard * 0.37;
    const ready = (key: "z" | "x" | "c" | "v") => !!f.attacks[key] &&
      (f.cooldowns[key] ?? 1) <= 0 && (key !== "v" || f.bonusSkillUnlocked);
    let key: "z" | "x" | "c" | "v" | "" = "";
    const t = this.zenithTactics;
    if (f.zenithSpearOut) {
      const sinceThrow = now - (this.zenithSpearObservedAt >= 0 ? this.zenithSpearObservedAt : now);
      // Aerial spear phase is intentionally aggressive, not passive waiting.
      // X uses the legal twin-blade version when the main spear is absent.
      if (!enemyPreparing && ready("x") && gap < t.xRange && gap > 0.55 &&
          (enemyRecovery || guardWeak || this.zenithTwinSwings > 0)) {
        key = "x";
      } else if (!enemyPreparing && ready("c") && f.zenithMagneticChargeT <= 0 &&
          sinceThrow < t.twinMinTime && gap > 2.1) {
        key = "c"; // Charge the blades without instantly calling the spear back.
      } else if (sinceThrow >= t.twinMinTime &&
          ((gap > 4.3 && sinceThrow > t.twinPreferTime) ||
           (this.zenithTwinSwings >= 3 && sinceThrow > t.twinPreferTime && gap > 2.0) ||
           sinceThrow > t.twinMaxTime)) {
        // Z recast is specifically allowed by Fighter while the spear is away,
        // EVEN when Z is on cooldown. It returns on its ordinary flight path.
        key = "z";
      }
    } else {
      // C starts the duel: get to Magnetic Charge before entering melee.
      if (!enemyPreparing && ready("c") && f.zenithMagneticChargeT <= 0 &&
          (gap < 6.9 || enemyRecovery)) {
        key = "c";
      } else if (!enemyPreparing && ready("v") && gap >= t.vMin && gap <= t.vMax &&
          (enemyRecovery || (guardWeak && o.state === S.BLOCK)) &&
          this.iqLevel >= 1) {
        key = "v"; // 53s V reserved for an observable opening, not wasted at random.
      } else if (!enemyPreparing && ready("x") && gap > 0.70 && gap < t.xRange &&
          (enemyRecovery || guardWeak || (f.zenithMagneticChargeT > 0 && this.iqLevel >= 2))) {
        key = "x";
      } else if (!enemyPreparing && ready("z") && gap >= t.throwMin && gap <= t.throwMax &&
          (enemyRecovery || f.zenithMagneticChargeT > 0 || gap > 4.5 || o.state === S.BLOCK)) {
        key = "z"; // Open a two-weapon phase, not an instant recall gimmick.
      }
    }
    // A missed tactical read has a real reaction delay, especially on Easy.
    this.zenithSkillNextAt = now + [0.92, 0.64, 0.38, 0.23][this.iqLevel];
    if (!key || Math.random() > [0.27, 0.57, 0.82, 0.95][this.iqLevel]) return false;
    this.queue = [];
    this.hold = 0;
    f.intent.attack = false;
    f.intent.skill = key;
    return true;
  }

  /** Zenith footwork: spear-tip measure vs blade-entry pressure.
   * Only ordinary movement; respects emergency actions, walls and ground hazards.
   */
  private zenithV10Footwork(f: Fighter, o: Fighter) {
    if (f.kit !== "glaive" || f.look.element !== "metal" || f.isDown() || o.isDown() ||
        !f.onGround || f.state !== S.IDLE || f.intent.skill || f.intent.attack ||
        f.intent.block || f.intent.jump || f.intent.dash.lengthSq() > 0.01 ||
        this.queue.length || this.hold > 0 || this.blockWait >= 0 ||
        this.blockHold > 0 || this.sideT > 0 || this.projectileSwordCommit > 0 ||
        this.comboParryTarget > this.threats.now()) return;
    const delta = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = delta.length();
    if (gap < 0.10) return;
    const toward = delta.divideScalar(gap);
    if (o.state === S.ATTACK && o.atkPhase === 0 && o.atk?.type === "melee" &&
        gap < o.atk.reach + 0.9) return; // let reactive defense handle the threat
    const now = this.threats.now();
    if (now > this.zenithOrbitRefreshAt) {
      this.zenithOrbitRefreshAt = now + [1.85, 1.45, 1.17, 0.93][this.iqLevel];
      if (Math.random() < 0.28) this.zenithOrbitSide *= -1;
    }
    const side = new THREE.Vector3(-toward.z, 0, toward.x)
      .multiplyScalar(this.zenithOrbitSide);
    const ideal = f.zenithSpearOut ? this.zenithTactics.twinRange :
      this.zenithTactics.spearGuard;
    const dir = new THREE.Vector3();
    if (gap > ideal + 0.35) dir.copy(toward).addScaledVector(side, 0.25);
    else if (gap < 0.98 && !f.zenithSpearOut)
      dir.copy(side).addScaledVector(toward, -0.28); // redirect, never corner-hide
    else dir.copy(side).addScaledVector(toward, gap > ideal ? 0.32 : -0.10);
    if (dir.lengthSq() < 0.01) return;
    dir.normalize();
    if (f.stage) {
      const main = f.stage.plats[0];
      if (!main || f.root.position.x + dir.x * 0.65 < main.x0 + 0.55 ||
          f.root.position.x + dir.x * 0.65 > main.x1 - 0.55) return;
      dir.z = 0;
    } else {
      const future = f.root.position.clone().addScaledVector(dir, 0.82).setY(0);
      if (future.length() > f.arenaRadius - f.radius - 0.45) {
        // Turn inward instead of forcing circle-stalling around the arena edge.
        dir.copy(f.root.position).setY(0).negate();
        if (dir.lengthSq() < 0.01) return;
        dir.normalize();
      }
    }
    f.intent.move.copy(dir).multiplyScalar(f.zenithSpearOut ? 0.94 : 0.79);
  }

  private zenithSkillNextAt = 0;''')

    # Existing V9 planner kept intact for rollback, but V10 is used exclusively
    # for Zenith. Only a one-line change; no huge replacement of ai.ts.
    once(A, '  private zenithSkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {',
        '  private zenithSkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {\n    if (f.kit === "glaive" && f.look.element === "metal") return this.zenithV10SkillPlan(f, o);')
    once(A, '      this.advancedFootwork(f, o, dt);\n      this.avoidFireGround(f);',
        '      this.advancedFootwork(f, o, dt);\n      this.zenithV10Footwork(f, o);\n      this.avoidFireGround(f);')

    # Sword vs spear have different actual effective basic hitboxes. Tune AI
    # position to them, not the old Zarek-distance + equipped projectile bias.
    once(A, '    // Keep a comfortable band, rather than alternating forward/back each frame.',
        '''    if (f.kit === "glaive" && f.look.element === "metal")
      ideal = f.zenithSpearOut ? 1.54 : 2.05;
    // Keep a comfortable band, rather than alternating forward/back each frame.''')

    # Fast basics and Phantom Fang should actually be used, rather than a Master
    # bot wasting its 20s attack-speed buff on ordinary charged attacks.
    once(A, '  // Veyr\'s festival specifically favors sustained lights and real guard pressure.',
        '''  // V10 Zenith: use charged basics much less often during a 3x/4x
  // Magnetic Charge window. Let her natural hit-confirm system reach Phantom Fang.
  if (id === "zenith" && (f.zenithMagneticChargeT > 0 || f.zenithSpearOut))
    heavyChance = Math.min(0.14, heavyChance * 0.28);
  // Veyr's festival specifically favors sustained lights and real guard pressure.''')
    once(A, '  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge',
        '''  if (punish) this.thinkCd *= 0.45; // uses an observed recovery, not foreknowledge
  if (id === "zenith") this.thinkCd *= f.zenithSpearOut ? 0.46 :
    f.zenithMagneticChargeT > 0 ? 0.62 : 0.78;''')

    # V should be committed to real setups, while the chosen V10 planner takes
    # priority; generic scoring is the fallback but may not burn V at random.
    once(A, '        if (name === "Sovereign Arsenal") points += punish && distance < 7.5 ? 1.8 : -0.1;',
        '''        if (name === "Sovereign Arsenal") {
          if (f.zenithSpearOut || distance < 2.85 || distance > 7.4 ||
              !(punish || (o.state === S.BLOCK && o.guard < o.maxGuard * 0.37))) viable = false;
          points += punish ? 3.0 : 0.4;
        }''')

    # Kit description only: no cooldown/hitbox stats are changed by V10.
    once(K,
        'desc: "Summon six magnetic spear constructs for dodgeable directional strikes, ending in one heavy rail spear.",',
        'desc: "Summon twelve magnetic spears in two waves, then two heavy rail spears. Fourteen weapons total; split damage, dodgeable strikes.",')

    # V was 6 regular + 1 finisher. V10 is 12 regular + 2 finishers.
    # Preserve total nominal damage, stagger/guard pressure and overall duration.
    once(G, '    for(let i=0;i<7;i++) this.later(0.30+i*0.22,()=>{',
        '''    // ZENITH_SOVEREIGN_HUNTRESS_V10_20261108 — 2x V weapon count:
    // 12 smaller strikes and two rail finishers. Identical total base health
    // damage budget: 12*18+2*48 = 6*36+96 = 312 (not 624).
    for(let i=0;i<14;i++) this.later(0.30+i*0.11,()=>{''')
    once(G, '''      const angle=(i%6)*Math.PI/3+0.18;
      const center=target.root.position.clone();
      const origin = i===6 ? f.chest() : center.clone().add(new THREE.Vector3(Math.sin(angle)*4.2,1.1,Math.cos(angle)*4.2));
      const toward=center.clone().add(new THREE.Vector3(0,1,0)).sub(origin);
      const power=i===6?1.28:1;
      const part={...a,id:i===6?"v_final":`v${i}`,style:"zenith_construct",dmg:i===6?96:36,
        knock:i===6?5.3:0.9,stun:i===6?0.45:0.15,heavy:i===6,pierce:false,
        size:i===6?1.05:0.64};
      const p=this.spawnProjectile(f,f.team,part,f.atkPower*power,origin,toward.normalize().multiplyScalar(i===6?26:17),
        "zenith_construct","metal",part.size,"#b0c6dc",false,target);
      p.life=1.25;
      this.fxp("flash",origin,"#d0deef",0.075,0.085,0.5);
      if (i===6) this.snd("dramatic_metal_explosion_impact", 0.62);''',
        '''      const finisher = i >= 12;
      const angle=(i%12)*Math.PI/6+0.18;
      const center=target.root.position.clone();
      const origin = finisher ? f.chest().add(new THREE.Vector3(i===12?-0.38:0.38,0.18,0))
        : center.clone().add(new THREE.Vector3(Math.sin(angle)*4.2,1.1,Math.cos(angle)*4.2));
      const toward=center.clone().add(new THREE.Vector3(0,1,0)).sub(origin);
      const power=finisher?1.28:1;
      const part={...a,id:finisher?`v_final_${i}`:`v${i}`,style:"zenith_construct",dmg:finisher?48:18,
        guard:a.guard*0.5,knock:finisher?2.65:0.45,
        stun:finisher?0.225:0.075,heavy:i===13,pierce:false,
        size:finisher?1.05:0.64};
      const p=this.spawnProjectile(f,f.team,part,f.atkPower*power,origin,toward.normalize().multiplyScalar(finisher?26:17),
        "zenith_construct","metal",part.size,"#b0c6dc",false,target);
      p.life=1.25;
      this.fxp("flash",origin,"#d0deef",0.045,0.065,0.32);
      if (i===13) this.snd("dramatic_metal_explosion_impact", 0.62);''')
except ValueError as err:
    sys.exit(f'PREFLIGHT ERROR: {err}. No files changed.')

# Review-grade preflight safety: source count and preexisting files are checked
# BEFORE backups/atomic installation. Backups are not discarded upon success.
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backups = {}
try:
    for path in FILES:
        src = ROOT / path
        backup = src.with_name(src.name + f'.before_zenith_v10_{stamp}.bak')
        shutil.copy2(src, backup)
        backups[path] = backup
    for path in FILES:
        dest = ROOT / path
        fd, tmp = tempfile.mkstemp(prefix=f'.{dest.name}.zenithv10.', suffix='.tmp', dir=dest.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as out:
                out.write(after[path])
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        print('Updated:', path)
except Exception as err:
    for path, backup in backups.items():
        try: shutil.copy2(backup, ROOT / path)
        except OSError: pass
    sys.exit(f'WRITE ERROR: {err}. Attempted automatic rollback.')

print('\nZenith V10 installed: personal Measure / Release / Reclaim AI, 14-weapon Sovereign Arsenal.')
print('V has 12 regular + 2 finisher spears; nominal total base damage unchanged (312).')
print('Magnetic Charge, Phantom Fang, twins, catch shield, Zarek and all other abilities are preserved.')
print('Run: npx tsc --noEmit -p . && npm run build')
