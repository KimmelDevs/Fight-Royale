#!/usr/bin/env python3
"""Fight Royale: Kaizen 10% parried spin, Kira V rework, Kaede C sheath,
Kaizen air-X icon fallback, and observed-opponent AI pattern recognition.

Usage from the game's web folder:
    python apply_character_balance_pattern_ai.py
or pass the web folder explicitly:
    python apply_character_balance_pattern_ai.py "C:/path/to/web"

No dependencies. Preflight-checks every source file, creates timestamped backups,
and refuses unknown code layouts without modifying anything. Safe to rerun.
Requires the earlier Combat IQ update for pattern recognition integration.
"""
from __future__ import annotations
import argparse
import datetime
from pathlib import Path
import sys

TAG = "BALANCE_KIRA_KAEDE_PATTERN_AI_AIR_ICON_20261107_V1"
FILES = [
    'src/game/fighter.ts',
    'src/game/model.ts',
    'src/game/kits.ts',
    'src/game/game.ts',
    'src/game/ai.ts',
    'src/ui/icons.tsx',
]

def replace_one(s: str, before: str, after: str, reason: str) -> str:
    count = s.count(before)
    if count != 1:
        raise ValueError(f"{reason}: expected exactly one source anchor; found {count}. No files changed.")
    return s.replace(before, after, 1)


def fighter_patch(s: str) -> str:
    s = replace_one(s,
        '  // The first perfect parry drops a circular skill to 1/4 speed.\n  // Subsequent parries flip direction, without slowing below that floor.',
        '  // A perfect parry drops either circular skill to 10% speed.\n  // Further parries reverse direction but do not slow it below 10%.',
        'Kaizen spin comment')
    s = replace_one(s, 'this.kaizenSpinSpeed = 0.25;', 'this.kaizenSpinSpeed = 0.10;', 'Kaizen spin speed')
    anchor = '''  isKaedeThousandCutsCasting(): boolean {
    return this.kit === "katana" && this.state === S.ATTACK && !!this.atk &&
      this.atk.name === "Thousand Cuts" && this.atk.style === "slashes";
  }'''
    s = replace_one(s, anchor, anchor + '''
  /** Kira's Hundred Kicks is an immobile hidden casting stance, not a kick animation.
   * The authoritative fighter root remains hittable (invisible != invulnerable).
   */
  isKiraHundredKicksCasting(): boolean {
    return this.kit === "kicks" && this.state === S.ATTACK &&
      this.atkId === "v" && this.atk?.name === "Hundred Kicks";
  }
  /** Hide render model only, leaving root and server hitboxes intact. */
  private updateKiraCastVisual() {
    if (this.kit !== "kicks" || this.model.loading) return;
    const casting = this.puppet
      ? this.state === S.ATTACK && this.poseName.startsWith("kira_hundred_cast_")
      : this.isKiraHundredKicksCasting();
    this.model.visible = !casting;
  }
  /** Compute sheathing progress locally or from networked attack pose. */
  private updateKaedeSheathVisual() {
    if (this.kit !== "katana") return;
    const casting = this.puppet
      ? this.state === S.ATTACK && this.poseName.startsWith("kaede_sheathe_")
      : this.isKaedeThousandCutsCasting();
    this.model.katanaSheathProgress = casting
      ? Math.min(1, Math.max(0, this.stateT / 0.25)) : 0;
  }''', 'Kira/Kaede cast helpers')
    # Ensure no input can cancel Kira's V while it is casting.
    s = replace_one(s,
        '''  private readDash() {
    if (this.chainBindT > 0''',
        '''  private readDash() {
    if (this.isKiraHundredKicksCasting()) return;
    if (this.chainBindT > 0''', 'Kira dash lock')
    s = replace_one(s,
        '''    if (this.isKaedeThousandCutsCasting()) { this.holding = false; return; }
    if ([S.HITSTUN''',
        '''    if (this.isKaedeThousandCutsCasting() || this.isKiraHundredKicksCasting()) {
      this.holding = false; return;
    }
    if ([S.HITSTUN''', 'Kira attack lock')
    s = replace_one(s,
        '''  private readSkill() {
    if (this.isKaedeThousandCutsCasting()) return;''',
        '''  private readSkill() {
    if (this.isKaedeThousandCutsCasting() || this.isKiraHundredKicksCasting()) return;''',
        'Kira skill lock')
    s = replace_one(s,
        '''  private move(dt: number) {
    if (this.isKaedeThousandCutsCasting()) {''',
        '''  private move(dt: number) {
    if (this.isKiraHundredKicksCasting()) {
      this.model.walk = 0; this.model.rotation.y = this.viewBias; return;
    }
    if (this.isKaedeThousandCutsCasting()) {''', 'Kira arena movement lock')
    s = replace_one(s,
        '''  private movePlat(dt: number) {
    if (this.isKaedeThousandCutsCasting()) {''',
        '''  private movePlat(dt: number) {
    if (this.isKiraHundredKicksCasting()) {
      this.vx = 0; this.model.walk = 0; return;
    }
    if (this.isKaedeThousandCutsCasting()) {''', 'Kira platform movement lock')
    # There are exactly two pose-blend sites: authoritative and remote puppet.
    before = '    this.model.blend(this.state === S.WIN\n      ? presentationPose'
    if s.count(before) != 2:
        raise ValueError(f'local + puppet visual anchors: expected 2, got {s.count(before)}')
    s = s.replace(before,
        '    this.updateKiraCastVisual();\n    this.updateKaedeSheathVisual();\n' + before, 2)
    return s


def kits_patch(s: str) -> str:
    s = replace_one(s,
        '''    c: a({ name: "Thousand Cuts", desc: "Seven blinding slashes rip through the target area.", cd: 11, type: "strike", wind: 0.2, recover: 0.6, dmg: 48, guard: 12, knock: 1, stun: 0.3, delay: 0.3, radius: 1.5, repeat: 7, interval: 0.07, style: "slashes", pose_w: "charge", pose_s: "heavy_s" }),''',
        '''    c: a({ name: "Thousand Cuts", desc: "Kaede slides her katana into its sheath, then seven blinding cuts strike the marked area.", cd: 11, type: "strike", wind: 0.2, recover: 0.6, dmg: 48, guard: 12, knock: 1, stun: 0.3, delay: 0.3, radius: 1.5, repeat: 7, interval: 0.07, style: "slashes", pose_w: "kaede_sheathe_w", pose_s: "kaede_sheathe_s" }),''', 'Kaede C pose and description')
    s = replace_one(s,
        '''return a({ name: "Hundred Kicks", desc: "Blitz the target with a storm of eight rapid kicks.", cd: 10, type: "strike", wind: 0.15, recover: 0.6, dmg: 40, guard: 10, knock: 0.8, stun: 0.3, delay: 0.2, radius: 1.5, repeat: 8, interval: 0.06, style: "slashes", pose_w: "kk1_w", pose_s: "kk1_s" });''',
        '''return a({ name: "Hundred Kicks", desc: "Stand completely still and vanish while casting eight phantom strikes. Damage reduced by 25%. Can be interrupted and hit while invisible.", cd: 10, type: "strike", wind: 0.15, recover: 0.6, dmg: 30, guard: 10, knock: 0.8, stun: 0.3, delay: 0.2, radius: 1.5, repeat: 8, interval: 0.06, style: "slashes", pose_w: "kira_hundred_cast_w", pose_s: "kira_hundred_cast_s" });''', 'Kira V damage and no-kick pose')
    s = replace_one(s, '''  katana: twoHanded(KNIGHT),''', '''  katana: {
    ...twoHanded(KNIGHT),
    // Kaede C: right hand slides the blade toward left-hip scabbard; left hand steadies it.
    // Feet remain planted and shoulders settle as the blade goes home.
    kaede_sheathe_w: P([0.18, -0.34, 0.10], [-0.13, 0.24, 0.03],
      [0.32, -0.62, -0.62], [0.24, 0.10, 0.34], [-0.50, 0.50, 0.38],
      [-0.22, -0.10, -0.22], [-0.18, 0, 0.11], [0.17, 0, -0.11], -0.055),
    kaede_sheathe_s: P([0.07, -0.20, 0.02], [-0.12, 0.14, 0],
      [0.62, -0.78, -0.49], [0.30, 0.08, 0.36], [-0.64, 0.48, 0.33],
      [-0.32, -0.16, -0.24], [-0.12, 0, 0.11], [0.14, 0, -0.11], -0.055),
  },''', 'Kaede C distinct animated poses')
    s = replace_one(s, '''  kicks: KICKS,''', '''  kicks: {
    ...KICKS,
    kira_hundred_cast_w: K(P([0.04, 0.12, 0], [0.02, -0.06, 0],
      [-0.45, 0.28, -0.34], [0, 0, 0], [-0.45, -0.28, 0.34], [0, 0, 0],
      [-0.12, 0, 0.10], [0.12, 0, -0.10], -0.04), 0.10, 0.10),
    kira_hundred_cast_s: K(P([0, 0, 0], [-0.02, 0, 0],
      [-0.42, 0.12, -0.24], [0, 0, 0], [-0.42, -0.12, 0.24], [0, 0, 0],
      [-0.10, 0, 0.09], [0.10, 0, -0.09], -0.04), 0.07, 0.07),
  },''', 'Kira V stationary casting poses')
    return s


def model_patch(s: str) -> str:
    s = replace_one(s,
        '''  private bowString: THREE.Mesh[] | null = null;''',
        '''  /** Katana blade retracts into the visible left-hip scabbard during Kaede C. */
  katanaSheathProgress = 0;
  private katanaBladePivot: THREE.Group | null = null;
  private katanaSheathAmount = 0;
  private bowString: THREE.Mesh[] | null = null;''', 'Kaede scabbard animation fields')
    before = '''    // A slight curve from three tilted segments.
    for (let i = 0; i < 3; i++) {
      mesh(s, box(0.032, 0.34, 0.008), this.steel(), [0.004 * i * i, 0.3 + i * 0.32, 0], [0, 0, -0.025 * i]);
      mesh(s, box(0.006, 0.32, 0.011), this.glowMat, [0.016 + 0.004 * i * i, 0.3 + i * 0.32, 0], [0, 0, -0.025 * i]);
    }
    mesh(s, cyl(0, 0.017, 0.08, 4), this.steel(), [0.022, 1.1, 0], [0, 0, -0.1], [1, 1, 0.3]);
    this.bladeBase = pivot(s, [0, 0.35, 0]);
    this.bladeTip = pivot(s, [0.02, 1.12, 0]);'''
    after = '''    // Keep handle in the right hand; slide the cutting blade into the scabbard
    // as the right hand reaches left hip. Default transform is identical to before.
    const blade = pivot(s, [0, 0, 0]);
    this.katanaBladePivot = blade;
    for (let i = 0; i < 3; i++) {
      mesh(blade, box(0.032, 0.34, 0.008), this.steel(), [0.004 * i * i, 0.3 + i * 0.32, 0], [0, 0, -0.025 * i]);
      mesh(blade, box(0.006, 0.32, 0.011), this.glowMat, [0.016 + 0.004 * i * i, 0.3 + i * 0.32, 0], [0, 0, -0.025 * i]);
    }
    mesh(blade, cyl(0, 0.017, 0.08, 4), this.steel(), [0.022, 1.1, 0], [0, 0, -0.1], [1, 1, 0.3]);
    this.bladeBase = pivot(blade, [0, 0.35, 0]);
    this.bladeTip = pivot(blade, [0.02, 1.12, 0]);'''
    s = replace_one(s, before, after, 'Kaede blade sheathing group')
    s = replace_one(s, "    // one quarter speed. Kaizen's normal spinning shield is NOT affected.",
        "    // 10% speed after a perfect parry. Kaizen's normal spinning shield is NOT affected.",
        'Kaizen model comment')
    s = replace_one(s,
        '''  blend(pose: Pose, dt: number, speed: number, actionPose = "") {
    if (this.nesaHammerPivot) {''',
        '''  blend(pose: Pose, dt: number, speed: number, actionPose = "") {
    if (this.katanaBladePivot) {
      // The hand moves to the scabbard via the Kaede-C pose; the curved blade
      // slides through the hilt into its sheathed position with smooth follow-through.
      this.katanaSheathAmount = THREE.MathUtils.damp(
        this.katanaSheathAmount, this.katanaSheathProgress, 18, dt);
      this.katanaBladePivot.position.y = -1.05 * this.katanaSheathAmount;
      this.katanaBladePivot.visible = this.katanaSheathAmount < 0.99;
    }
    if (this.nesaHammerPivot) {''', 'Kaede blade animation timing')
    return s


def game_patch(s: str) -> str:
    s = replace_one(s, '"SPIN 25% - REVERSED CCW" : "SPIN 25% - REVERSED CW"',
        '"SPIN 10% - REVERSED CCW" : "SPIN 10% - REVERSED CW"', 'Kaizen parry popup')
    s = replace_one(s, '   * scheduled hits and Fighter.stateT at the same effective 25% tempo. */',
        '   * scheduled hits and Fighter.stateT at the same effective 10% tempo. */',
        'Kaizen timer schedule comment')
    s = replace_one(s, 'if (factor <= 1) return; // already at the 25%-speed floor',
        'if (factor <= 1) return; // already at the 10%-speed floor',
        'Kaizen timer floor comment')
    return s


def icon_patch(s: str) -> str:
    s = replace_one(s,
        '''export const skillIcon = (kit: string, element: string, key: string) =>
  `/icons/skills/${kit === "mage" ? `mage-${element}` : kit}-${key}.webp`;''',
        '''// Air attacks reuse the regular skill artwork; no missing *_air.webp requests.
export const skillIcon = (kit: string, element: string, key: string) =>
  `/icons/skills/${kit === "mage" ? `mage-${element}` : kit}-${key.replace(/_air$/, "")}.webp`;''',
        'Shared air icon fallback')
    return s

PATTERN_FIELDS = '''  // PATTERN_AI_V1: observable habits within a short window. Never reads hidden inputs.
  private patternEnemyId = -1;
  private patternSawSwing = -1;
  private patternWasBlocking = false;
  private patternProjectiles: number[] = [];
  private patternMelee: number[] = [];
  private patternGuard: number[] = [];
  private patternDecisionCd = 2.0;
  private patternReadAt = -1;
  private patternPending: "none" | "ranged" | "melee" | "guard" = "none";
  private patternMode: "none" | "ranged" | "melee" | "guard" = "none";
  private patternModeT = 0;
  private patternOrbitSign = Math.random() < 0.5 ? -1 : 1;

  /** Learning only from observed swing animations and shield raises; no enemy cooldown reads. */
  private observePatterns(f: Fighter, o: Fighter, dt: number) {
    const now = this.threats.now();
    if (this.patternEnemyId !== o.id) {
      this.patternEnemyId = o.id;
      this.patternSawSwing = -1;
      this.patternWasBlocking = false;
      this.patternProjectiles = []; this.patternMelee = []; this.patternGuard = [];
      this.patternMode = "none"; this.patternPending = "none";
      this.patternModeT = 0; this.patternDecisionCd = 2.0;
    }
    const window = 10.0;
    this.patternProjectiles = this.patternProjectiles.filter(t => now - t <= window);
    this.patternMelee = this.patternMelee.filter(t => now - t <= window);
    this.patternGuard = this.patternGuard.filter(t => now - t <= window);
    if (o.state === S.ATTACK && o.atk && o.swingSerial !== this.patternSawSwing) {
      this.patternSawSwing = o.swingSerial;
      const a = o.atk;
      if (["projectile", "lob", "barrel"].includes(a.type))
        this.patternProjectiles.push(now);
      else if (a.type === "melee" || a.type === "phantom")
        this.patternMelee.push(now);
    }
    const blocking = o.state === S.BLOCK;
    if (blocking && !this.patternWasBlocking && o.stateT < 0.32)
      this.patternGuard.push(now);
    this.patternWasBlocking = blocking;
    this.patternModeT = Math.max(0, this.patternModeT - dt);
    this.patternDecisionCd = Math.max(0, this.patternDecisionCd - dt);
    if (this.patternModeT <= 0) this.patternMode = "none";
    const learn = [0, 0.35, 0.68, 0.87][this.iqLevel];
    if (learn <= 0 || f.isDown() || o.isDown() || this.patternDecisionCd > 0) return;
    if (this.patternPending !== "none") {
      if (now < this.patternReadAt) return;
      if (Math.random() < learn) {
        this.patternMode = this.patternPending;
        this.patternModeT = [0, 0.65, 1.1, 1.55][this.iqLevel];
        this.patternOrbitSign = Math.random() < 0.5 ? -1 : 1;
      }
      this.patternPending = "none";
      this.patternDecisionCd = [7.5, 6.0, 4.8, 3.7][this.iqLevel];
      return;
    }
    // Require three distinct events in ten seconds; ties favor the more immediate threat.
    const shots = this.patternProjectiles.length;
    const melee = this.patternMelee.length;
    const guard = this.patternGuard.length;
    const most = Math.max(shots, melee, guard);
    if (most < 3) return;
    this.patternPending = shots === most ? "ranged" : melee === most ? "melee" : "guard";
    this.patternReadAt = now + [1, 0.48, 0.26, 0.16][this.iqLevel];
  }

  /** Footwork adaptation; emergency dodges, hit-confirm, blocking, and cooldowns win. */
  private patternFootwork(f: Fighter, o: Fighter): boolean {
    if (this.patternMode === "none" || this.patternModeT <= 0 || f.isDown() ||
        f.stage || !f.onGround || f.state !== S.IDLE || f.intent.skill ||
        f.intent.block || f.intent.dash.lengthSq() > 0.01 ||
        this.blockWait >= 0 || this.blockHold > 0 || this.sideT > 0 ||
        this.threats.firePatches(f).length > 0 || this.comboParryTarget > this.threats.now())
      return false;
    const delta = o.root.position.clone().sub(f.root.position).setY(0);
    const gap = delta.length();
    if (gap < 0.02) return false;
    const toward = delta.divideScalar(gap);
    const flank = new THREE.Vector3(-toward.z, 0, toward.x).multiplyScalar(this.patternOrbitSign);
    let desired: THREE.Vector3 | null = null;
    if (this.patternMode === "ranged" && gap > 2.35) {
      // Repeated ranged attacks: close diagonally instead of walking straight in.
      desired = toward.clone().multiplyScalar(0.72).addScaledVector(flank, 0.68);
    } else if (this.patternMode === "melee" && gap < (o.attacks.l1?.reach ?? 1.7) + 0.35) {
      // Repeated light rushes: circle outside the enemy weapon's real reach.
      desired = toward.clone().multiplyScalar(-0.64).addScaledVector(flank, 0.72);
    } else if (this.patternMode === "guard" && o.state === S.BLOCK && gap < 2.7) {
      // Frequent shielding: don't mindlessly swing into guard; bait a release.
      desired = toward.clone().multiplyScalar(gap < 1.6 ? -0.8 : -0.15).addScaledVector(flank, 0.8);
    }
    if (!desired || desired.lengthSq() < 0.01) return false;
    desired.normalize();
    // Arena boundary: reverse orbit before choosing an impossible step.
    const next = f.root.position.clone().setY(0).addScaledVector(desired, 1.1);
    if (next.length() > f.arenaRadius - f.radius - 0.25) {
      desired.addScaledVector(flank, -1.8).normalize();
      if (f.root.position.clone().setY(0).addScaledVector(desired, 1.1).length() >
          f.arenaRadius - f.radius - 0.25) return false;
    }
    f.intent.move.copy(desired);
    f.intent.attack = false;
    return true;
  }
'''


def ai_patch(s: str) -> str:
    if 'COMBAT_IQ_HITCONFIRM_WHIFF_BAIT_V1_20261107' not in s:
        raise ValueError('AI requires the prior Combat IQ installer. Run apply_combat_iq_system.py first.')
    s = replace_one(s,
        '  private iqLevel = 1;', PATTERN_FIELDS + '\n  private iqLevel = 1;',
        'AI pattern learning fields and logic')
    s = replace_one(s,
        '''    this.iqObserve(f, o);
    // Marked ground impacts''',
        '''    this.iqObserve(f, o);
    this.observePatterns(f, o, dt);
    // Marked ground impacts''',
        'AI observe observed attacks')
    s = replace_one(s,
        '''    const iqActed = !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.combatIQAction(f, o, dt);
    if (!this.aiAirTap && !f.intent.skill && !iqActed &&''',
        '''    const iqActed = !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.combatIQAction(f, o, dt);
    const patternActed = !iqActed && !this.aiAirTap && !f.intent.skill &&
      this.projectileSwordCommit <= 0 && this.patternFootwork(f, o);
    if (!this.aiAirTap && !f.intent.skill && !iqActed && !patternActed &&''',
        'AI pattern footwork priority')
    return s

PATCHERS = {
    'src/game/fighter.ts': fighter_patch,
    'src/game/model.ts': model_patch,
    'src/game/kits.ts': kits_patch,
    'src/game/game.ts': game_patch,
    'src/game/ai.ts': ai_patch,
    'src/ui/icons.tsx': icon_patch,
}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_folder', nargs='?', default='.', help='Folder containing src/game and src/ui')
    args = parser.parse_args()
    root = Path(args.game_folder).expanduser().resolve()
    if not (root / 'src/game/fighter.ts').is_file() and (root / 'web/src/game/fighter.ts').is_file():
        root = root / 'web'
    changed: dict[Path, str] = {}
    try:
        for relative in FILES:
            dest = root / relative
            if not dest.is_file():
                raise FileNotFoundError(f'Missing {relative} in {root}')
            old = dest.read_text(encoding='utf-8')
            if TAG in old:
                print(f'  [already installed] {relative}')
                continue
            updated = PATCHERS[relative](old)
            if updated == old:
                raise ValueError(f'{relative}: no changes generated')
            changed[dest] = '// ' + TAG + '\n' + updated
        if not changed:
            print('Already installed; nothing changed.')
            return 0
        # No writes until ALL patch functions have passed preflight.
        stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        for dest, content in changed.items():
            backup = dest.with_name(dest.name + '.before_balance_pattern_' + stamp + '.bak')
            backup.write_bytes(dest.read_bytes())
            dest.write_text(content, encoding='utf-8')
            print(f'  [updated] {dest.relative_to(root)}   (backup: {backup.name})')
        print('\nSuccess. Kaizen 10% parried spin; Kira invisible, stationary V at 75% damage;')
        print('Kaede C sheathing animation; shared air-skill icons; learned CPU patterns.')
        return 0
    except Exception as exc:
        print(f'Patch NOT applied: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
