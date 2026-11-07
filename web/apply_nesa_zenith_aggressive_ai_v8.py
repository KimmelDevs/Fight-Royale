#!/usr/bin/env python3
"""Fight Royale: remove V1/V2 low-HP retreat AI, smarter Nesa/Zenith,
blockable (unparryable) Heart Smash. Requires Zenith installer and Nesa V patch.
Run from the web/ project directory. All edits preflight before writing.
"""
from pathlib import Path
from datetime import datetime
import sys

ROOT=Path.cwd()
A='src/game/ai.ts'; K='src/game/kits.ts'; G='src/game/game.ts'; F='src/game/fighter.ts'
NAMES=[A,K,G,F]
TAG='NESA_ZENITH_AGGRESSIVE_AI_V8_20261108'
try:
    old={p:(ROOT/p).read_text(encoding='utf-8') for p in NAMES}
except OSError as e:
    sys.exit(f'ERROR: {e}. Run this installer in your web/ folder. No files modified.')
if TAG in old[A]:
    print('Already installed. No files modified.')
    sys.exit(0)
if 'ZENITH_IRON_SOVEREIGN_V1_20261108' not in old[K] or 'NESA_FORWARD_HEART_PARRY_V_20261108' not in old[F]:
    sys.exit('PREFLIGHT ERROR: Install fixed Zenith and Nesa Heartbreaker V installers first. No files modified.')
new=old.copy()
def once(p,anchor,replacement):
    n=new[p].count(anchor)
    if n!=1: raise ValueError(f'{p}: expected exactly 1 match, found {n}: {anchor[:95]!r}')
    new[p]=new[p].replace(anchor,replacement,1)
def section(p,left,right,replacement):
    s=new[p]; i=s.find(left)
    if i<0 or s.count(left)!=1: raise ValueError(f'{p}: cannot locate unique start {left[:90]!r}')
    j=s.find(right,i+len(left))
    if j<0: raise ValueError(f'{p}: cannot find end {right[:90]!r}')
    new[p]=s[:i]+replacement+s[j:]
try:
    # -- Remove low-health V1 and Last Stand V2, including decision overrides and dead fields.
    once(G, '// AI_LOW_HEALTH_SURVIVAL_V1_20261108\n', '')
    section(G, '    // AI_LOW_HEALTH_SURVIVAL: visible, friendly Healing Water zones; no hidden enemy info.\n',
            '    ignitions: (f: Fighter) =>', '')
    once(A, '  /** Visible friendly healing circles; only legitimate water pulse heals. */\n  healingPools?(f: Fighter): { center: THREE.Vector3; radius: number; remaining: number }[];\n', '')
    for marker in ('// AI_LOW_HEALTH_LAST_STAND_V2_20261108\n','// AI_LOW_HEALTH_SURVIVAL_V1_20261108\n'):
        once(A,marker,'')
    section(A,'// LOW_HEALTH_SURVIVAL: recognition is sampled once per planned decision, never\n',
            '// AI_ADVANCED_FOOTWORK:', '// Removed: low-health retreat / last-stand personality overrides.\n\n')
    section(A,'  // LOW_HEALTH_SURVIVAL: decisions stay committed for brief, human-like windows.\n',
            '  private rangeOrbitCd = 0;',
            '  // V8: no automatic low-health retreat, recover, heal, or edge stalling.\n\n')
    once(A,'''    // LAST_STAND_V2: run this before any early defensive returns so a real
    // parry/dodge doesn't erase observation of prolonged inactivity.
    this.observeLastStand(f, o);
''','')
    once(A,'''    // LOW_HEALTH_SURVIVAL: all immediate threat reactions already ran.
    const survivalActed = this.lowHealthSurvival(f, o);
''','')
    new[A]=new[A].replace('!survivalActed && ', '')
    # No remaining survivalActed references except 3 special footwork lines.
    once(A,'''      if (!survivalActed) {
        this.advancedFootwork(f, o, dt);
        this.lastStandFootwork(f, o);
      }
''', '''      this.advancedFootwork(f, o, dt);
''')
    section(A,'  /** Track elapsed time without damage even when an urgent dodge/parry has\n',
            '  private position(f: Fighter, o: Fighter, dt: number) {', '')
    if any(w in new[A] for w in ('survivalActed','SURVIVAL_IQ','this.lowHealthSurvival','this.lastStandFootwork','this.observeLastStand')):
        raise ValueError('Incomplete low-health AI removal')

    # -- Nesa C: explicitly flag no_parry even outside hammer-wide flag, lower guard pressure.
    once(K, '''c: a({ name: "Pink Heart Smash", desc: "Three stored charges. Smash forward to create a pink heart shockwave ahead of Nesa; opponents behind her are not hit. Charges regenerate separately.",''',
         '''c: a({ name: "Pink Heart Smash", desc: "Three forward heart-smash charges. Regular blocking negates HP damage (unless guard breaks); cannot be parried. Dodge or guard the telegraphed impact.",''')
    once(K,'''dmg: 172, guard: 57, knock: 8.7, stun: 0.62, heavy: true,
      delay: 0.035, radius: 2.72, style: "nesa_heart_slam",''',
         '''dmg: 156, guard: 42, knock: 7.4, stun: 0.56, heavy: true, no_parry: true,
      delay: 0.035, radius: 2.72, style: "nesa_heart_slam",''')
    # Prevent Nesa's general hammer armor "chip through block" override just for C.
    once(F,'''const hammerCrushBlock = attacker instanceof Fighter && attacker.hammerWeightArmor &&
        (a.type === "melee" || a.type === "strike");''',
         '''const hammerCrushBlock = attacker instanceof Fighter && attacker.hammerWeightArmor &&
        a.style !== "nesa_heart_slam" && (a.type === "melee" || a.type === "strike");''')
    # Regular guard breaks still matter. Cannot convert Nesa C into a forced parry
    # via the continuous combo exception; force this named impact to remain unparryable.
    once(F,'''const parryableContinuous = attacker instanceof Fighter && attacker.isContinuousComboActive();''',
         '''const parryableContinuous = attacker instanceof Fighter && attacker.isContinuousComboActive() &&
      a.style !== "nesa_heart_slam";''')

    # -- Zenith power nerf: moderate 10-15% hit reduction, including hardcoded spawned constructs.
    once(K,'''[48, 0.14, "gl1_w", "gl1_s"], [51, 0.14, "gl2_w", "gl2_s"],
      [54, 0.15, "gl3_w", "gl3_s"], [57, 0.16, "gl4_w", "gl4_s"],
      [76, 0.24, "gl5_w", "gl5_s"]''',
         '''[43, 0.14, "gl1_w", "gl1_s"], [46, 0.14, "gl2_w", "gl2_s"],
      [49, 0.15, "gl3_w", "gl3_s"], [51, 0.16, "gl4_w", "gl4_s"],
      [68, 0.24, "gl5_w", "gl5_s"]''')
    for before,after in (('dmg: 113, guard: 35','dmg: 100, guard: 35'),
                         ('dmg: 104, guard: 25','dmg: 92, guard: 25'),
                         ('dmg: 29, guard: 9','dmg: 25, guard: 9'),
                         ('dmg: 49, guard: 15','dmg: 43, guard: 15')):
        once(K,before,after)
    once(G,'''style:"zenith_barrage",dmg:29,knock:i===4?1.8:0.3''',
         '''style:"zenith_barrage",dmg:25,knock:i===4?1.8:0.3''')
    once(G,'''style:"zenith_construct",dmg:32,pierce:false''',
         '''style:"zenith_construct",dmg:28,pierce:false''')
    once(G,'''style:"zenith_construct",dmg:i===6?112:42,''',
         '''style:"zenith_construct",dmg:i===6?96:36,''')
    # Pull/repel displacement reduced (balance without removing mobility option).
    once(G,'''const amt=(repel?1.15:Math.min(1.4,Math.max(0,dist-1.2)))*(1+0.16*f.zenithMagnetCharges);''',
         '''const amt=(repel?1.0:Math.min(1.2,Math.max(0,dist-1.2)))*(1+0.12*f.zenithMagnetCharges);''')

    # -- expose only visible/earned polarity data to the AI, no enemy secrets.
    once(A,'''  now(): number;
}''', '''  now(): number;
  /** Zenith can reason about the polarity she actually applied to this opponent. */
  magneticMark?(self: Fighter, enemy: Fighter): -1 | 0 | 1;
}''')
    once(G,'''    strikes: () => this.strikeMarks,''', '''    magneticMark: (self: Fighter, enemy: Fighter): -1 | 0 | 1 => {
      const mark = this.zenithMarks.get(enemy.id);
      return !mark || mark.team !== self.team || mark.ttl <= 0 ? 0 : mark.sign > 0 ? 1 : -1;
    },
    strikes: () => this.strikeMarks,''')

    # -- Zenith chooses her spear-in-hand vs floating-weapon stance intentionally.
    section(A,'  private zenithSkillNextAt = 0;', '  private roxySkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {', '''  // Zenith isn't Zarek. She makes distinct in-hand, thrown-spear, and recall plans.
  private zenithSkillNextAt = 0;
  private zenithSpearObservedAt = -1;
  private zenithSpearWasOut = false;
  private zenithEnemyId = -1;
  private zenithSkillOpportunity(f: Fighter, o: Fighter, dt: number): boolean {
    if (f.look.element !== "metal" || f.kit !== "glaive" || f.isDown() || o.isDown()) return false;
    const now = this.threats.now();
    if (this.zenithEnemyId !== o.id || now < this.zenithSkillNextAt - 120) {
      this.zenithEnemyId = o.id; this.zenithSpearWasOut = false;
      this.zenithSpearObservedAt = -1; this.zenithSkillNextAt = now + 0.20;
    }
    if (f.zenithSpearOut && !this.zenithSpearWasOut) this.zenithSpearObservedAt = now;
    this.zenithSpearWasOut = f.zenithSpearOut;
    if (f.chainBindT > 0 || !f.onGround || f.status.has("freeze") ||
        now < this.zenithSkillNextAt || f.intent.skill) return false;
    const free = f.state === S.IDLE || f.state === S.BLOCK || f.state === S.CHARGE ||
      (f.state === S.ATTACK && f.atkPhase === 2 && !!f.atk);
    if (!free) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const marked = this.threats.magneticMark?.(f, o) ?? 0;
    const ready = (key: "z"|"x"|"c"|"v") => !!f.attacks[key] &&
      (f.cooldowns[key] ?? 1) <= 0 && (key !== "v" || f.bonusSkillUnlocked);
    const pressure = o.state === S.HITSTUN || o.state === S.STAGGER || this.hasPunishWindow(o);
    const opportunity = [0.24, 0.54, 0.79, 0.94][this.iqLevel];
    let key: "z"|"x"|"c"|"v"|"" = "";
    if (f.zenithSpearOut) {
      const held = now - Math.max(0, this.zenithSpearObservedAt);
      const anchorDist = f.zenithSpearAnchor.clone().setY(0).distanceTo(f.root.position.clone().setY(0));
      // Don't instantly recall every Z! Attack from two positions or reposition by C first.
      if (ready("c") && anchorDist > 2.3 && gap > 2.1 && gap < 8 &&
          (marked === -1 || anchorDist > 4.2) && held > 0.36) key = "c";
      else if (held > (this.iqLevel >= 2 ? 1.0 : 1.5) &&
          (gap < 3.3 || held > 2.4 || anchorDist > 7.5)) key = "z";
    } else if (ready("v") && gap >= 2.3 && gap < 7.3 && pressure && this.iqLevel >= 2) {
      key = "v";
    } else if (ready("c") && marked === 1 && gap >= 2.3 && gap <= 5.2 &&
          (ready("x") || pressure || gap >= 3.5)) {
      // Positive -> attract into close-range rapid thrusts.
      key = "c";
    } else if (ready("x") && gap > 0.65 && gap < 2.8 &&
          (pressure || marked === 1 || this.iqLevel >= 2)) {
      key = "x";
    } else if (ready("z") && gap >= 3.5 && gap <= 9.2 &&
          (marked !== -1 || pressure)) {
      key = "z";
    } else if (ready("c") && marked === -1 && gap < 2.5 && !f.stage) {
      // Negative -> repel as a defensive reset (normal cooldown and collision still apply).
      f.intent.skillHeld = "c"; key = "c";
    } else if (ready("x") && gap < 2.5 && pressure) {
      key = "x";
    }
    if (!key) { this.zenithSkillNextAt=now+0.20; return false; }
    this.zenithSkillNextAt=now+[1.1,0.74,0.45,0.27][this.iqLevel];
    if (Math.random() > opportunity) return false;
    f.intent.skill=key;
    f.intent.attack=false;
    this.queue=[]; this.hold=0;
    return true;
  }

''')

    # -- Nesa V real pre-impact parry decision: needs enemy's committed cast, no magic instant parry.
    once(A,'''  private roxySkillReadAt = 0;''', '''  private nesaVThreat = -1;
  private nesaVReactAt = 0;
  private nesaVChose = false;
  private nesaVUsed = false;
  private roxySkillReadAt = 0;''')
    once(A,'''    // During Blood Festival Veyr chases with basics rather than blocking.
    if (this.veyrFestivalPressure(f, o, dt)) return;''', '''    // A real approaching attack gives Nesa time to wind up her timed V counter.
    if (this.nesaTimedVParry(f, o)) return;
    // During Blood Festival Veyr chases with basics rather than blocking.
    if (this.veyrFestivalPressure(f, o, dt)) return;''')
    once(A,'''  private zenithSkillNextAt = 0;''', '''  private nesaTimedVParry(f: Fighter, o: Fighter): boolean {
    if (f.kit !== "hammer" || !f.bonusSkillUnlocked || f.isDown() || o.isDown() ||
        !f.onGround || f.status.has("freeze") ||
        !f.attacks.v || f.attacks.v.style !== "nesa_high_striker" ||
        (f.cooldowns.v ?? 1) > 0 || ![S.IDLE,S.BLOCK,S.CHARGE].includes(f.state)) return false;
    const now = this.threats.now();
    const dist = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const current = o.atk;
    const meleeIncoming = o.state === S.ATTACK && !!current && current.type === "melee" &&
      (!current.no_parry || o.isContinuousComboActive()) &&
      o.atkPhase === 0 && dist < (current.reach || 1.7) + 0.6;
    const shot = this.threats.projectiles().find(pr => pr.target === f && pr.team !== f.team &&
      pr.pos.distanceTo(f.chest()) < 7.5);
    const shotETA = shot ? this.projectileTimeToContact(f, shot) : 99;
    const actionableShot = !!shot && shotETA > 0.14 && shotETA < 0.62;
    if (!meleeIncoming && !actionableShot) return false;
    const serial = meleeIncoming ? o.id * 100000 + o.swingSerial : shot!.id * -1;
    if (serial !== this.nesaVThreat) {
      this.nesaVThreat = serial;
      this.nesaVUsed = false;
      this.nesaVChose = Math.random() < [0.13,0.40,0.72,0.90][this.iqLevel];
      this.nesaVReactAt = now + [0.26,0.19,0.11,0.065][this.iqLevel] + Math.random()*0.05;
    }
    if (!this.nesaVChose || this.nesaVUsed || now < this.nesaVReactAt) return false;
    const eta = meleeIncoming ? Math.max(0, current!.wind - o.stateT) : shotETA;
    if (eta < 0.13 || eta > 0.70) return false; // swing's actual 0.10..0.79 parry window
    this.nesaVUsed = true;
    this.queue=[]; this.hold=0; this.blockWait=-1; this.blockHold=0;
    f.intent.block=false; f.intent.attack=false; f.intent.skill="v";
    return true;
  }

  private zenithSkillNextAt = 0;''')

    # A Metal spear user must not run Zarek's Clash Momentum decisions or
    # have generic skill roulette override the separate thrown-weapon plan.
    once(A, 'if (f.kit === "glaive" && f.onGround && f.state === S.IDLE &&',
         'if (f.kit === "glaive" && f.look.element !== "metal" && f.onGround && f.state === S.IDLE &&')
    once(A, '''    this.readySkillPoll = Math.max(0, this.readySkillPoll - dt);
    if (this.readySkillPoll > 0 || f.isDown()) return false;''',
         '''    this.readySkillPoll = Math.max(0, this.readySkillPoll - dt);
    if (f.look.element === "metal" && f.kit === "glaive") return false;
    if (this.readySkillPoll > 0 || f.isDown()) return false;''')
    once(A, 'if (skill && (punish || Math.random() < 0.80) && this.trySkill(f, skill, true)) return;',
         'if (id !== "zenith" && skill && (punish || Math.random() < 0.80) && this.trySkill(f, skill, true)) return;')
    once(A, 'else if (r < this.p.parry + bc + 0.15) this.trySkill(f, "z", true);',
         'else if (r < this.p.parry + bc + 0.15 && f.look.element !== "metal") this.trySkill(f, "z", true);')

    # -- Nesa C defence: give AI a deliberate guard alternative instead of always running.
    once(A, '''  private nesaEvadeChosen = false;''', '''  private nesaEvadeChosen = false;
  private nesaHeartBlockChosen = false;''')
    once(A, '''      this.nesaEvadeChosen = Math.random() < Math.min(0.94, 0.13 + this.p.block * 1.18);''',
         '''      this.nesaEvadeChosen = Math.random() < Math.min(0.94, 0.13 + this.p.block * 1.18);
      // C is blockable (never parryable). Some bots guard instead of fleeing.
      this.nesaHeartBlockChosen = heart && f.guard > a!.guard * 1.35 &&
        Math.random() < [0.20, 0.37, 0.48, 0.62][this.iqLevel];''')
    once(A, '''    const t = o.stateT;
    const giantImpact = a!.wind + 1.78;''', '''    const t = o.stateT;
    // Raise guard before the visible hammer impact. Holding guard isn't a perfect parry:
    // nesa_heart_slam is explicitly no_parry, so regular guard drains guard only.
    if (heart && this.nesaHeartBlockChosen && gap < firstRadius + 0.35 &&
        t >= Math.max(0.05, a!.wind - 0.31) && t < a!.wind + 0.16) {
      this.nesaRetreatT = 0;
      this.blockWait=-1; this.blockHold=0; this.blockDur=0;
      this.queue=[]; this.hold=0;
      f.intent.attack=false; f.intent.skill=""; f.intent.dash.set(0,0,0);
      f.intent.move.set(0,0,0); f.intent.block=true;
      return true;
    }
    const giantImpact = a!.wind + 1.78;''')
    # Avoid duplicate decisions from ground-warning system for C; it has its own anticipatory defender.
    once(A,'''      if (m.caster && (m.caster.team === f.team || m.caster.isDown())) continue;''',
         '''      if (m.caster && (m.caster.team === f.team || m.caster.isDown())) continue;
      if (m.style === "nesa_heart_slam") continue; // handled at windup by evadeNesa: dodge OR block''')
    # Tag final output for repeat safety and versioning.
    once(A, 'import * as THREE from "three";', f'// {TAG}: V1/V2 low-HP logic removed, Nesa/Zenith tactics updated.\nimport * as THREE from "three";')
    new[A] = new[A].replace('The previous emergency dodge/parry and survival AI still have priority.',
                            'Normal emergency dodge/parry reactions still have priority.')
    if 'survivalActed' in new[A] or 'lowHealthSurvival(' in new[A]: raise ValueError('Unexpected survival remnants')
except Exception as e:
    sys.exit(f'PREFLIGHT ERROR: {e}. No files changed.')

stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
try:
    for p in NAMES:
        path=ROOT/p
        backup=path.with_name(f'{path.name}.before_nesa_zenith_ai_v8_{stamp}.bak')
        backup.write_text(old[p],encoding='utf-8')
    for p in NAMES:
        path=ROOT/p
        tmp=path.with_name(f'.{path.name}.v8.tmp')
        tmp.write_text(new[p],encoding='utf-8')
        tmp.replace(path)
        print(f'PATCH {p}')
    print('DONE: low-health retreat V1/V2 removed; Nesa V + C block defense; Zenith polarity AI + balance.')
except OSError as e:
    sys.exit(f'FILE ERROR while writing: {e}. Restore from .before_nesa_zenith_ai_v8_...bak if necessary.')
