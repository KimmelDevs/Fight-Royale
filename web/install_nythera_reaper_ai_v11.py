#!/usr/bin/env python3
"""Fight Royale V11: Nythera combat AI, in-world gravity stance icons, 10% shorter scythe blade.

Usage: python install_nythera_reaper_ai_v11.py [path/to/fight-royale/web]
Requires the V9+ Nythera source (V10 recommended), no pip packages.
Creates timestamped .bak backups and replaces only src/game/ai.ts and src/game/model.ts.
"""
from pathlib import Path
from datetime import datetime
import os
import shutil
import sys

PATCH = 'NYTHERA_REAPER_AI_STANCE_BLADE_V11'

NEW_PLAN = '''  // NYTHERA_REAPER_AI_STANCE_BLADE_V11: use skills and move instead of passively
  // re-blocking Zenith. Reads only public opponent animations, distance and HP.
  private nytheraV2Plan(f: Fighter, o: Fighter): boolean {
    if (f.kit !== "scythe" || f.isDown() || o.isDown()) return false;
    const now = this.threats.now();
    if (now < this.nytheraNextPlanAt || f.intent.skill || f.intent.attack ||
        f.intent.dash.lengthSq() > 0.01 || f.chainBoundBy ||
        f.status.has("freeze") || f.atkLock > 0) return false;
    const gap = f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0));
    const dy = Math.abs(o.root.position.y - f.root.position.y);
    const a = o.atk;
    const danger = o.state === S.ATTACK && o.atkPhase === 1 && !!a &&
      a.type === "melee" && gap < a.reach + 0.25;
    const windup = o.state === S.ATTACK && o.atkPhase === 0 && !!a &&
      a.type === "melee" && gap < a.reach + 0.30;
    const punish = this.hasPunishWindow(o) || o.stunRemaining > 0.15 ||
      o.state === S.HITSTUN || o.state === S.STAGGER;
    const ready = (k: "z" | "x" | "c" | "v") => !!f.attacks[k] &&
      (f.cooldowns[k] ?? 1) <= 0 && (k !== "v" || f.bonusSkillUnlocked);
    const act = (k: "z" | "x" | "c" | "v" | "f") => {
      this.queue = []; this.hold = 0; this.blockWait = -1;
      this.blockHold = 0; this.comboParryTarget = -1;
      f.intent.block = false; f.intent.attack = false;
      f.intent.skill = k;
      this.nytheraActionCycle++;
      this.nytheraNextPlanAt = now + [0.64, 0.39, 0.24, 0.15][this.iqLevel];
      if (k === "f") {
        this.nytheraLastStanceAt = now;
        this.nytheraRecentContacts = 0;
      }
      return true;
    };
    // The dedicated aerial follow-up lives in the real attack-tap path below.
    // X in Dreadfall is an air dive; it still needs a real opening.
    if (!f.onGround) {
      if (!danger && f.gravityMode === "heavy" && f.state === S.IDLE &&
          ready("x") && gap < 2.4 && o.root.position.y < f.root.position.y - 0.20 &&
          this.iqLevel >= 2 && Math.random() < 0.30) return act("x");
      return false;
    }
    const free = f.state === S.IDLE || f.state === S.BLOCK ||
      (f.state === S.ATTACK && f.atkPhase === 2 && !!f.atk &&
       f.stateT >= f.atk.wind + f.atk.active + 0.04);
    if (!free || dy > 1.65) return false;
    // Respect a live blade or an observed parry read; never gain free i-frames.
    if (danger || (windup && gap < 1.20 && !punish)) return false;
    // Old anti-Zenith guard plans can survive into *neutral*. Do not let them
    // deny every legal offensive input when there is no current threat.
    if (f.state === S.IDLE || f.state === S.BLOCK) {
      this.blockWait = -1; this.blockHold = 0;
      this.comboParryTarget = -1; f.intent.block = false;
    }
    const canShift = f.gravitySwitchCd <= 0 && now - this.nytheraLastStanceAt > 2.3;
    // Light gravity gathers marks; heavy gravity converts them to damage/tempo.
    if (canShift && f.gravityMode === "light" && gap < 3.10 &&
        (this.nytheraRecentContacts >= 2 ||
         (this.nytheraRecentContacts >= 1 && punish) ||
         (now - this.nytheraLastStanceAt > 8 && gap < 2.05))) return act("f");
    // Dreadfall already earns round-long speed, so do not switch away every
    // time the enemy briefly retreats; close in with the weapon instead.
    if (canShift && f.gravityMode === "heavy" && gap > 4.15 &&
        now - this.nytheraLastContactAt > 3.5) return act("f");
    const guarding = o.state === S.BLOCK;
    // Only use the ultimate in actual range: its separate strikes remain
    // parryable, blockable and clashable even if the first swing misses.
    if (ready("v") && gap > 0.85 && gap < 2.60 && dy < 1.0 &&
        (punish || (guarding && o.guard < o.maxGuard * 0.48) ||
         (this.iqLevel >= 2 && this.nytheraActionCycle % 6 === 4)) &&
        Math.random() < [0.05, 0.25, 0.56, 0.76][this.iqLevel]) return act("v");
    if (f.gravityMode === "light") {
      // Actually cast Event Horizon to cut off an approaching or retreating foe.
      if (ready("c") && gap >= 2.15 && gap <= 3.80 && dy < 1.25 &&
          (o.state === S.IDLE || punish || guarding) &&
          Math.random() < [0.15, 0.50, 0.72, 0.88][this.iqLevel]) return act("c");
      // Alternate hook and launch; don't require a hit-confirm on the previous cut.
      if (ready("z") && gap > 0.85 && gap <= 2.92 &&
          (gap > 1.65 || guarding || punish || this.nytheraActionCycle % 3 === 1))
        return act("z");
      if (ready("x") && gap > 0.78 && gap <= 2.62 &&
          (punish || guarding || this.nytheraActionCycle % 2 === 0)) return act("x");
    } else {
      // Heavy stance aggressively cashes marks and builds Dreadfall speed.
      if (ready("x") && gap > 0.75 && gap <= 2.58 &&
          (punish || guarding || this.nytheraActionCycle % 3 === 0)) return act("x");
      if (ready("z") && gap > 0.82 && gap <= 2.80 &&
          (punish || guarding || this.nytheraActionCycle % 2 === 1)) return act("z");
      if (ready("c") && gap <= 2.15 && gap > 0.55 &&
          (punish || guarding) && this.iqLevel >= 1) return act("c");
    }
    // Melee basics are vital for generating marks, Dreadfall tempo, and combo
    // pressure. A missed skill opportunity is not a reason to stand in place.
    if (f.state === S.IDLE && gap > 0.38 && gap <= 2.52 && dy < 1.25 &&
        (punish || guarding || Math.random() < [0.34, 0.69, 0.86, 0.95][this.iqLevel])) {
      this.queue = []; this.hold = 0;
      this.blockWait = -1; this.blockHold = 0; this.comboParryTarget = -1;
      f.intent.block = false; f.intent.attack = true;
      this.nytheraActionCycle++;
      this.nytheraNextPlanAt = now + [0.42, 0.28, 0.19, 0.125][this.iqLevel];
      return true;
    }
    // No free attack at out-of-range targets; footwork will close the gap.
    this.nytheraNextPlanAt = now + [0.28, 0.20, 0.14, 0.11][this.iqLevel];
    return false;
  }

'''

BADGE_METHOD = '''
  // NYTHERA_REAPER_AI_STANCE_BLADE_V11: compact in-world mode symbols, not a
  // fixed-screen HUD. Both local and remote fighters use synced gravityHeavy.
  private buildGravityStanceBadges() {
    if (typeof document === "undefined") return;
    const make = (heavy: boolean): THREE.Sprite => {
      const canvas = document.createElement("canvas");
      canvas.width = 128; canvas.height = 128;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas unavailable for gravity badge");
      ctx.beginPath(); ctx.arc(64, 64, 54, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(6,7,18,0.91)"; ctx.fill();
      ctx.lineWidth = 7; ctx.strokeStyle = heavy ? "#c78aff" : "#91e4ff"; ctx.stroke();
      ctx.lineJoin = "round"; ctx.lineCap = "round";
      if (heavy) {
        // Purple falling-weight glyph: three downward strokes.
        ctx.strokeStyle = "#f2d8ff"; ctx.lineWidth = 9;
        ctx.beginPath(); ctx.moveTo(64,25); ctx.lineTo(64,82);
        ctx.moveTo(38,61); ctx.lineTo(64,88); ctx.lineTo(90,61); ctx.stroke();
        ctx.fillStyle = "#d9a6ff";
        ctx.beginPath(); ctx.moveTo(40,96); ctx.lineTo(88,96);
        ctx.lineTo(79,105); ctx.lineTo(49,105); ctx.closePath(); ctx.fill();
      } else {
        // Pale crescent moon = Moonfloat / light gravity.
        ctx.fillStyle = "#dbf7ff";
        ctx.beginPath(); ctx.arc(60,62,29,-1.12,2.05,false);
        ctx.quadraticCurveTo(91,84,82,33); ctx.closePath(); ctx.fill();
        ctx.fillStyle = "#9bdeff";
        ctx.beginPath(); ctx.arc(89,87,5,0,Math.PI*2); ctx.fill();
      }
      const tex = new THREE.CanvasTexture(canvas);
      tex.colorSpace = THREE.SRGBColorSpace;
      const mat = new THREE.SpriteMaterial({map: tex, transparent: true,
        depthWrite: false, depthTest: true, toneMapped: false});
      const sprite = new THREE.Sprite(mat);
      sprite.name = heavy ? "Nythera Dreadfall icon" : "Nythera Moonfloat icon";
      sprite.position.set(0, 2.13, 0);
      sprite.scale.set(0.38, 0.38, 1);
      sprite.renderOrder = 4;
      this.add(sprite);
      this.gravityStanceBadges.push(sprite);
      return sprite;
    };
    make(false); make(true);
  }

'''


def replace_unique(src: str, old: str, new: str, field: str) -> str:
    count = src.count(old)
    if count != 1:
        raise ValueError(f'{field}: expected exactly one anchor, found {count}: {old[:110]!r}')
    return src.replace(old, new, 1)


def patch_ai(src: str) -> str:
    if PATCH in src:
        print('  ai.ts already patched')
        return src
    if 'private nytheraV2Plan(' not in src or 'private antiZenithDuel(' not in src:
        raise ValueError('AI does not contain the Nythera V9/V10 planner / anti-Zenith routines')
    src = replace_unique(src,
        '  private nytheraOrbitDir = 1;',
        '  private nytheraActionCycle = 0; // '+PATCH+'\n  private nytheraOrbitDir = 1;', 'AI planner state')
    start = '  private nytheraV2Plan(f: Fighter, o: Fighter): boolean {'
    end = '  private nytheraV2Footwork(f: Fighter, o: Fighter): void {'
    if src.count(start) != 1 or src.count(end) != 1:
        raise ValueError('Nythera planner anchors are not unique')
    a = src.index(start); b = src.index(end, a)
    src = src[:a] + NEW_PLAN + src[b:]
    src = replace_unique(src,
        '    if (visibleTempo && canInput && !f.dashing() && gap < 3.85) {',
        '    if (visibleTempo && f.kit !== "scythe" && canInput && !f.dashing() && gap < 3.85) {',
        'Stop endless anti-Zenith defense for Nythera')
    src = replace_unique(src,
        '    const band = f.gravityMode === "light" ? 2.27 : 1.94;',
        '    const band = f.gravityMode === "light" ? 1.82 : 1.72; // V11: close far enough to actually hit',
        'Scythe footwork optimal band')
    src = replace_unique(src,
        '    if (!f.stage && (f.kit === "kicks" || f.kit === "assassin") &&',
        '    if (!f.stage && (f.kit === "kicks" || f.kit === "assassin" || f.kit === "scythe") &&',
        'Airborne approach')
    src = replace_unique(src,
        '(f.kit === "kicks" ? /^air_l[1-3]$/.test(f.atkId) : /^air_l[1-2]$/.test(f.atkId))) {',
        '(f.kit === "kicks" ? /^air_l[1-3]$/.test(f.atkId) :\n          f.kit === "scythe" ? /^air_l[1-4]$/.test(f.atkId) : /^air_l[1-2]$/.test(f.atkId))) {',
        'Four-slice air pursuit')
    src = replace_unique(src,
        '        this.aerialAirStrikeChance(o, dt)) {\n      this.aiAirTap = true;',
        '        (f.kit === "scythe" ?\n          Math.random() < [0.20, 0.55, 0.82, 0.96][this.iqLevel] :\n          this.aerialAirStrikeChance(o, dt))) {\n      this.aiAirTap = true;',
        'Reliable Nythera air taps')
    src = replace_unique(src,
        '      this.airSliceCd = f.kit === "kicks" || f.kit === "assassin" || f.kit === "scythe"\n        ? rand(0.17, 0.24) : rand(0.55, 0.85);',
        '      this.airSliceCd = f.kit === "scythe" ? rand(0.085, 0.115) :\n        f.kit === "kicks" || f.kit === "assassin" ? rand(0.17, 0.24) :\n        rand(0.55, 0.85);',
        'Air follow-up beat timing')
    return src


def patch_model(src: str) -> str:
    if PATCH in src:
        print('  model.ts already patched')
        return src
    if 'private buildGravityScythe()' not in src or 'gravityHeavy = false;' not in src:
        raise ValueError('Model does not contain Nythera scythe and gravity state')
    src = replace_unique(src,
        '  private gravityScythe: THREE.Group | null = null;',
        '  private gravityScythe: THREE.Group | null = null;\n'
        '  private gravityStanceBadges: THREE.Sprite[] = []; // '+PATCH,
        'Model badge sprites')
    src = replace_unique(src,
        '    this.gravityScythe = scythe;\n    const dark =',
        '    this.gravityScythe = scythe;\n    this.buildGravityStanceBadges();\n    const dark =',
        'Initialize stance badges')
    src = replace_unique(src,
        '    // This is a single blade, never a double-sided polearm.\n    shape.moveTo(-0.024, 0.755);',
        '    // This is a single blade, never a double-sided polearm.\n'
        '    // 10% shorter blade head ONLY: original haft, grip, reach and timings stay unchanged.\n'
        '    const bladeHead = pivot(scythe, [0, 0.0755, 0]);\n'
        '    bladeHead.scale.set(0.90, 0.90, 1);\n'
        '    shape.moveTo(-0.024, 0.755);',
        'Blade-only shrink pivot')
    src = replace_unique(src, '    mesh(scythe, geo, steel);\n    // Polished hooked cutting edge',
                                '    mesh(bladeHead, geo, steel);\n    // Polished hooked cutting edge',
                                'Scythe blade mesh')
    src = replace_unique(src, '    mesh(scythe, new THREE.TubeGeometry(edgeCurve, 34, 0.0058, 5, false), edgeSteel);',
                                '    mesh(bladeHead, new THREE.TubeGeometry(edgeCurve, 34, 0.0058, 5, false), edgeSteel);',
                                'Edge profile')
    src = replace_unique(src, '    mesh(scythe, new THREE.TubeGeometry(spineCurve, 25, 0.004, 5, false), gold);',
                                '    mesh(bladeHead, new THREE.TubeGeometry(spineCurve, 25, 0.004, 5, false), gold);',
                                'Spine profile')
    src = replace_unique(src, '    this.bladeBase = pivot(scythe,[-0.26,1.10,0]);',
                                '    this.bladeBase = pivot(bladeHead,[-0.26,1.10,0]);',
                                'Trail blade base')
    src = replace_unique(src, '    this.bladeTip = pivot(scythe,[-1.36,1.465,0]);',
                                '    this.bladeTip = pivot(bladeHead,[-1.36,1.465,0]);',
                                'Trail blade tip')
    # Put method alongside scythe builder; do not modify other weapons.
    src = replace_unique(src, '  private buildGravityScythe() {',
                                BADGE_METHOD + '  private buildGravityScythe() {',
                                'Badge method declaration')
    src = replace_unique(src,
        '    if (this.gravityScythe) {\n      // NYTHERA_SHOWCASE_SPIN_TOSS_V3',
        '    if (this.gravityStanceBadges.length === 2) {\n'
        '      this.gravityStanceBadges[0].visible = !this.gravityHeavy;\n'
        '      this.gravityStanceBadges[1].visible = this.gravityHeavy;\n'
        '    }\n    if (this.gravityScythe) {\n      // NYTHERA_SHOWCASE_SPIN_TOSS_V3',
        'Sync badges with gravity mode each frame')
    return src


def root_for_input() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()
    this = Path(__file__).resolve().parent
    options = (this, this / 'web', Path.cwd(), Path.cwd() / 'web')
    for candidate in options:
        if (candidate / 'src/game/ai.ts').is_file() and (candidate / 'src/game/model.ts').is_file():
            return candidate.resolve()
    raise FileNotFoundError('Put this .py in fight-royale/web or pass the web folder path')


def main() -> int:
    try:
        root = root_for_input()
        files = ((root / 'src/game/ai.ts', patch_ai), (root / 'src/game/model.ts', patch_model))
        outputs = []
        for path, patcher in files:
            before = path.read_text(encoding='utf-8')
            after = patcher(before)
            if before != after:
                outputs.append((path, before, after))
        if not outputs:
            print('Already installed — no changes made.')
            return 0
        now = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        stages = []
        replaced = []
        try:
            for path, before, after in outputs:
                backup = path.with_name(path.name + '.before_' + PATCH + '_' + now + '.bak')
                temp = path.with_name(path.name + '.' + PATCH + '.tmp')
                backup.write_text(before, encoding='utf-8')
                temp.write_text(after, encoding='utf-8')
                stages.append((path, backup, temp))
            for path, backup, temp in stages:
                os.replace(temp, path)
                replaced.append((path, backup))
                print('UPDATED:', path.relative_to(root))
        except Exception:
            for path, backup in reversed(replaced):
                shutil.copy2(backup, path)
            raise
        finally:
            for path, backup, temp in stages:
                if temp.exists():
                    temp.unlink()
        print('\nSUCCESS — Nythera V11')
        print('  Smarter CPU: anti-Zenith counterattacks, gravity skill use, close-range combos, aerial follow-ups')
        print('  Moonfloat (cyan crescent) and Dreadfall (purple down-arrow) icons above her head')
        print('  Scythe blade only: 10% shorter. Handle, hitboxes, damage and weapon reach unchanged.')
        print('  Backups created in src/game/.')
        print('Run: npx tsc --noEmit -p . && npm run dev')
        return 0
    except Exception as exc:
        print('ERROR:', exc)
        print('No partial source patches were intentionally applied. Review the .bak backups if needed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
