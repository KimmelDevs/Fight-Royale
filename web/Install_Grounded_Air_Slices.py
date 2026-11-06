#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale — Grounded Air Slices (replaces Aerial Juggles if present).

Double-click or run `python Install_Grounded_Air_Slices.py`, pick the project
folder containing src/game. Python 3.9+; no dependencies.

- Normal jump then left-click: ONE natural air swing per jump.
- The swing aims down, level, or up at the opponent's relative elevation.
- Hit direction and weapon pose agree; no auto-chase, launch combo or slam.
- Keeps ground knockback, floor knockdown/wakeup, character skills and balance.
- If previous aerial juggle installer is present, precisely reverses only its
  inserted sections (without reverting newer unrelated changes).
- Safe dry-run, timestamped backups, and repeat-install protection.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import os
import shutil
import sys
import tempfile

TAG = "FIGHT_ROYALE_GROUNDED_AIR_SLICES_V1"
OLD_JUGGLE_TAG = "FIGHT_ROYALE_AERIAL_JUGGLE_V1_NOV07"
NEEDS = "FIGHT_ROYALE_WEIGHTED_KNOCKDOWN_WAKEUP_V1"
FILES = ("src/game/fighter.ts", "src/game/game.ts", "src/game/ai.ts")

class PatchError(RuntimeError):
    pass

def once(s: str, old: str, new: str, title: str) -> str:
    count = s.count(old)
    if count != 1:
        raise PatchError(f"{title}: expected 1 exact match, found {count}. No changes made.")
    return s.replace(old, new, 1)

# Exact reverse edits recorded from the original Aerial Juggles installer.
# They are applied only when the previous installer is present.
JUGGLE_REVERSE = {'ai.ts': [['  private antiAirCd = 0;\n',
            '  private antiAirCd = 0;\n  private airComboCd = 0;\n',
            'independent AI air-followup timer'],
           ['    this.antiAirCd = Math.max(0, this.antiAirCd - dt);\n',
            '    this.antiAirCd = Math.max(0, this.antiAirCd - dt);\n'
            '    this.airComboCd = Math.max(0, this.airComboCd - dt);\n',
            'AI air-followup timer tick'],
           ['    this.react(f, o);\n    this.defendLongCombo(f, o);',
            '    // AIR JUGGLE: CPUs can air-tech a real launcher; no immunity or free escape.\n'
            '    if (f.airJuggleT > 0 && f.canAirTech() && Math.random() < dt * (this.p.parry > '
            '0.1 ? 5 : 2.0)) {\n'
            '      f.intent.block = true;\n'
            '      this.queue = []; this.hold = 0;\n'
            '      return;\n'
            '    }\n'
            '    this.react(f, o);\n'
            '    this.defendLongCombo(f, o);',
            'AI air tech'],
           ['    if (f.state === S.IDLE && f.onGround && !RANGED.has(f.kit) &&\n'
            '        o.root.position.y - f.root.position.y > 0.65 &&',
            '    // Occasionally open a combo from the ground, not only against jumping foes.\n'
            '    // This is a normal Space+Attack, fully blockable/parryable by players.\n'
            '    if (f.state === S.IDLE && f.onGround && o.onGround && !RANGED.has(f.kit) &&\n'
            '        f.airChaseT <= 0 && this.antiAirCd <= 0 &&\n'
            '        f.root.position.clone().setY(0).distanceTo(o.root.position.clone().setY(0)) < '
            'f.attacks.anti_air.reach - 0.15 &&\n'
            '        Math.random() < dt * 0.27) {\n'
            '      this.aiAirTap = true;\n'
            '      this.antiAirCd = rand(2.3, 3.6);\n'
            '      this.queue = [];\n'
            '      this.hold = 0;\n'
            '    } else if (f.state === S.IDLE && f.onGround && !RANGED.has(f.kit) &&\n'
            '        o.root.position.y - f.root.position.y > 0.65 &&',
            'AI starts occasional fair launcher'],
           ['    } else if (!f.onGround && f.state === S.IDLE &&\n'
            '        f.root.position.distanceTo(o.root.position) < 2.3 && this.antiAirCd <= 0 &&\n'
            '        !RANGED.has(f.kit)) {\n'
            '      this.aiAirTap = true;\n'
            '      this.antiAirCd = rand(0.24, 0.45);\n'
            '    }',
            '    } else if (!f.onGround && (f.state === S.IDLE ||\n'
            '        (f.state === S.ATTACK && f.atkId.startsWith("air_l") && f.atkPhase === 2)) '
            '&&\n'
            '        f.root.position.distanceTo(o.root.position) < 2.4 && this.airComboCd <= 0 &&\n'
            '        !RANGED.has(f.kit)) {\n'
            '      // Prioritize legal air follow-ups; a successful combo remains capped at '
            'three.\n'
            '      if (o.airJuggleOwner === f.id && o.airJuggleT > 0 && '
            'o.canContinueAirJuggle(f.id)) {\n'
            '        this.aiAirTap = true;\n'
            '        this.airComboCd = rand(0.25, 0.34);\n'
            '      } else if (f.state === S.IDLE && o.airJuggleT <= 0 && this.antiAirCd <= 0) {\n'
            '        this.aiAirTap = true;\n'
            '        this.antiAirCd = rand(0.38, 0.60);\n'
            '        this.airComboCd = rand(0.38, 0.60);\n'
            '      }\n'
            '    }',
            'CPU midair follow-up within capped window']],
 'fighter.ts': [['  private readonly wakeupDuration = 0.38;\n',
                 '  private readonly wakeupDuration = 0.38;\n'
                 '  // AERIAL_JUGGLE_V1: only actual anti-air HP hits begin an airborne juggle.\n'
                 '  // One original launcher, three follow-up hits MAX, and a hard 2.2s limit.\n'
                 '  airJuggleOwner = -1;\n'
                 '  airJuggleT = 0;\n'
                 '  airJuggleHits = 0;\n'
                 '  private airHangT = 0;\n'
                 '  private airSlamPending = false;\n'
                 '  onJuggleSlam: (f: Fighter) => void = () => {};\n'
                 '  /** A live launcher is required; neutral jumps and normal skills cannot '
                 'juggle-loop. */\n'
                 '  beginAirJuggle(ownerId: number) {\n'
                 '    if (this.stage || !this.onGround || this.state === S.KO || '
                 'this.knockedDown() ||\n'
                 '        this.chainBoundBy || this.chainBindTarget || this.bloodFestivalT > 0) '
                 'return;\n'
                 '    this.airJuggleOwner = ownerId;\n'
                 '    this.airJuggleT = 2.2;\n'
                 '    this.airJuggleHits = 0;\n'
                 '    this.airHangT = 0.11;\n'
                 '    this.airSlamPending = false;\n'
                 '    this.velY = Math.max(this.velY, 7.8);\n'
                 '    this.onGround = false;\n'
                 '  }\n'
                 '  canContinueAirJuggle(ownerId: number): boolean {\n'
                 '    return !this.stage && this.airJuggleT > 0 && !this.onGround &&\n'
                 '      this.airJuggleOwner === ownerId && this.airJuggleHits < 3 &&\n'
                 '      !this.airSlamPending && this.state !== S.KO;\n'
                 '  }\n'
                 '  /** Prevent extra airborne hits after the capped combo has been finished. */\n'
                 '  airJuggleLocked(ownerId: number): boolean {\n'
                 '    return !this.stage && !this.onGround && this.airJuggleOwner === ownerId &&\n'
                 '      (this.airSlamPending || (this.airJuggleT > 0 && this.airJuggleHits >= '
                 '3));\n'
                 '  }\n'
                 '  /** Called only AFTER a confirmed damaging air-light or air-heavy hit. */\n'
                 '  continueAirJuggle(ownerId: number, finisher: boolean): "lift" | "slam" | "" {\n'
                 '    if (!this.canContinueAirJuggle(ownerId)) return "";\n'
                 '    this.airJuggleHits++;\n'
                 '    if (finisher || this.airJuggleHits === 3) {\n'
                 '      this.airSlamPending = true;\n'
                 '      this.airJuggleT = 0;\n'
                 '      this.airHangT = 0;\n'
                 '      this.velY = Math.min(this.velY, -10.5);\n'
                 '      return "slam";\n'
                 '    }\n'
                 '    // Brief float for readability; never reset the overall time budget.\n'
                 '    this.velY = Math.max(2.9, this.velY);\n'
                 '    this.airHangT = Math.max(this.airHangT, 0.09);\n'
                 '    return "lift";\n'
                 '  }\n'
                 '  /** Player air tech is still one-use: AI can invoke the same defense. */\n'
                 '  canAirTech() {\n'
                 '    return !this.onGround && !this.airRecoverUsed &&\n'
                 '      this.state === S.HITSTUN && this.stateT >= 0.18;\n'
                 '  }\n'
                 '  private clearAirJuggle() {\n'
                 '    this.airJuggleT = 0;\n'
                 '    this.airJuggleOwner = -1;\n'
                 '    this.airJuggleHits = 0;\n'
                 '    this.airHangT = 0;\n'
                 '    this.airSlamPending = false;\n'
                 '  }\n',
                 'air juggle state and rules'],
                ['    this.comboPauseT = 0;\n    this.setState(S.KNOCKDOWN);',
                 '    this.comboPauseT = 0;\n'
                 '    this.clearAirJuggle();\n'
                 '    this.setState(S.KNOCKDOWN);',
                 'knockdown clears juggle'],
                ['    this.knockdownLockT = Math.max(0, this.knockdownLockT - dt);\n',
                 '    this.knockdownLockT = Math.max(0, this.knockdownLockT - dt);\n'
                 '    this.airJuggleT = Math.max(0, this.airJuggleT - dt);\n'
                 '    this.airHangT = Math.max(0, this.airHangT - dt);\n',
                 'juggle timer'],
                ['    this.airRecoverUsed = true;\n'
                 '    this.invulnT = Math.max(this.invulnT, 0.16);',
                 '    this.airRecoverUsed = true;\n'
                 "    // An intentional one-use air tech breaks the opponent's juggle chain.\n"
                 '    this.clearAirJuggle();\n'
                 '    this.invulnT = Math.max(this.invulnT, 0.20);',
                 'one-use air escape interrupts combo'],
                ['    this.velY -= GRAVITY * dt;\n',
                 '    // Keep launched targets airborne momentarily for a readable chase.\n'
                 '    // The maximum is three 0.09s suspensions, never a perpetual hover.\n'
                 '    this.velY -= GRAVITY * dt * (this.airHangT > 0 ? 0.35 : 1);\n',
                 'short bounded air hang'],
                ['      this.model.recoil = 0.35;\n      this.onLanded(this);',
                 '      this.model.recoil = 0.35;\n'
                 '      const landedFromSlam = this.airSlamPending && this.state !== S.KO;\n'
                 '      if (landedFromSlam) {\n'
                 '        // Only this landing becomes a normal recoverable knockdown, not a KO.\n'
                 '        this.beginKnockdown();\n'
                 '        this.onJuggleSlam(this);\n'
                 '      } else this.clearAirJuggle();\n'
                 '      this.onLanded(this);',
                 'landed slam to down/wakeup'],
                ['    this.airChaseT = 0; this.airChaseMoveT = 0; this.airRecoverUsed = false;',
                 '    this.airChaseT = 0; this.airChaseMoveT = 0; this.airRecoverUsed = false;\n'
                 '    this.clearAirJuggle();',
                 'revive resets juggle'],
                ['    this.airChaseT = 0; this.airChaseMoveT = 0;',
                 '    this.airChaseT = 0; this.airChaseMoveT = 0;\n    this.clearAirJuggle();',
                 'KO resets juggle']],
 'game.ts': [['    f.onLanded = (x) => { this.fx.ring(x.root.position, "#ffffff", 0.8, 0.25, 0.5); '
              'this.snd("land", 0.35); };',
              '    f.onLanded = (x) => { this.fx.ring(x.root.position, "#ffffff", 0.8, 0.25, 0.5); '
              'this.snd("land", 0.35); };\n'
              '    f.onJuggleSlam = (x) => {\n'
              '      // Compact ground contact; not the large combat-ring or a gameplay hitbox.\n'
              '      this.fxp("arenaReact", x.root.position.clone(), "crack", 0.58);\n'
              '      this.fxp("smoke", x.root.position.clone(), "#d5c8b6");\n'
              '      this.fxp("ring", x.root.position.clone().add(new THREE.Vector3(0, 0.06, 0)),\n'
              '        x.look.glow, 0.82, 0.19, 0.62);\n'
              '      this.fxp("num", x.chest().add(new THREE.Vector3(0, 0.48, 0)),\n'
              '        "GROUND SLAM!", "#ffe3a5", 0.85);\n'
              '      this.snd("slam", 0.58);\n'
              '      this.add_trauma(0.17);\n'
              '      this.hitStop(0.055);\n'
              '    };',
              'slam effects on landing'],
             ['        d.velY = Math.max(d.velY, f.stage ? 7.2 : 6.6);\n'
              '        d.onGround = false;',
              '        if (d.stage) {\n'
              '          d.velY = Math.max(d.velY, 7.2);\n'
              '          d.onGround = false;\n'
              '        } else if (d.onGround) {\n'
              '          d.beginAirJuggle(f.id); // normal 3D arena: start only from ground\n'
              '        } else {\n'
              '          // Intercept someone already jumping, but do not rearm endless juggles.\n'
              '          d.velY = Math.max(d.velY, 4.4);\n'
              '        }',
              'anti-air establishes real juggle'],
             ['    if (d instanceof Fighter && attacker) '
              'd.setImpactSource(attacker.root.position);\n'
              '    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : '
              'power);',
              '    if (d instanceof Fighter && attacker) '
              'd.setImpactSource(attacker.root.position);\n'
              '    const airComboMove = attacker instanceof Fighter &&\n'
              '      (/^air_l[123]$/.test(attacker.atkId) || attacker.atkId === "air_heavy") &&\n'
              '      d instanceof Fighter && !d.stage && a.dmg > 0;\n'
              '    if (airComboMove && attacker instanceof Fighter && d instanceof Fighter &&\n'
              '        d.airJuggleLocked(attacker.id)) return "miss";\n'
              '    const result = d.receiveHit(attacker, weightedAttack, riposte ? power * 1.15 : '
              'power);',
              'enforce three-hit max before damage'],
             ['    const glow = attacker instanceof Fighter ? attacker.look.glow : attacker '
              'instanceof Mob ? attacker.def.color : "#ffffff";',
              "    // AIR JUGGLE: only real damage hits from the attacker's air moves count.\n"
              '    // Never change ordinary skill damage, clash/parry, or Judgment '
              'transformation.\n'
              '    if (airComboMove && attacker instanceof Fighter && d instanceof Fighter &&\n'
              '        (result === "hit" || result === "crit")) {\n'
              '      const finish = attacker.atkId === "air_l3" || attacker.atkId === '
              '"air_heavy";\n'
              '      const juggle = d.continueAirJuggle(attacker.id, finish);\n'
              '      if (juggle) {\n'
              '        const point = d.chest();\n'
              '        this.fxp("sparks", point, attacker.look.glow, juggle === "slam" ? 22 : 14, '
              '5);\n'
              '        this.fxp("flash", point, attacker.look.glow, 0.24, 0.12, 0.50);\n'
              '        this.fxp("num", point.clone().add(new THREE.Vector3(0, 0.45, 0)),\n'
              '          juggle === "slam" ? "AIR FINISH!" : `AIR x${d.airJuggleHits}`,\n'
              '          "#c6edff", 0.72);\n'
              '      }\n'
              '    }\n'
              '    const glow = attacker instanceof Fighter ? attacker.look.glow : attacker '
              'instanceof Mob ? attacker.def.color : "#ffffff";',
              'air juggle follow-ups and compact VFX']]}

def remove_old_juggles(s: str, name: str) -> str:
    if OLD_JUGGLE_TAG not in s:
        return s
    for old, new, title in reversed(JUGGLE_REVERSE[name]):
        # Reverse one atomic edit, with strict matching so unrelated edits survive.
        s = once(s, new, old, f"Remove previous aerial juggling: {title}")
    s = once(s, f"// {OLD_JUGGLE_TAG}\\n".replace("\\n", "\n"), "", "Remove aerial-juggle marker")
    return s

def fighter_patch(s: str) -> str:
    if TAG in s: return s
    if NEEDS not in s:
        raise PatchError("Install Knockback / Knockdown / Wake-up first.")
    s = remove_old_juggles(s, "fighter.ts")
    s = once(s, '  private airHeavyDone = false;\n',
        """  private airHeavyDone = false;
  // GROUNDED_AIR_SLICES_V1: one normal attack per jump. No aerial combo or slam.
  airSliceUsed = false;
  airSliceAngle = 0; // signed pitch toward the actual target, radians
  private airSliceQueued = false;
""", "Add airborne swing state")
    s = once(s, '    this.poses = Kits.poses(this.kit, this.look.element);\n',
        """    this.poses = Kits.poses(this.kit, this.look.element);
    // Extra poses use the same procedural/VRM rig, including remote fighters.
    this.buildDirectionalAirPoses();
    this.attacks.air_l1 = { ...this.attacks.air_l1, next: "", lunge: 0,
      knock: Math.min(this.attacks.air_l1.knock, 0.8),
      heavy: false, stagger: false, recover: Math.max(this.attacks.air_l1.recover, 0.30) };
""", "Install natural airborne swing poses and knock values")
    s = once(s, """  isDown() { return this.state === S.KO; }""",
        """  // Use each kit's own windup and strike as a starting point, keeping weapon grip.
  // A downward slash visibly starts above the head and cuts toward the feet.
  private buildDirectionalAirPoses() {
    const source = (key: string) => this.poses[key] ?? this.poses.jump ?? this.poses.idle;
    const wind = source(this.attacks.air_l1.pose_w);
    const strike = source(this.attacks.air_l1.pose_s);
    const v3 = (v: [number, number, number]): [number, number, number] =>
      [v[0], v[1], v[2]];
    const copy = (p: Pose): Pose => ({
      ...p, torso: v3(p.torso), head: v3(p.head),
      arm_r: v3(p.arm_r), hand_r: v3(p.hand_r),
      arm_l: v3(p.arm_l), hand_l: v3(p.hand_l),
      leg_l: v3(p.leg_l), leg_r: v3(p.leg_r),
      knee: p.knee ? [p.knee[0], p.knee[1]] : undefined,
    });
    const ranged = this.kit === "bow" || this.kit === "mage";
    const kicks = this.kit === "kicks";
    for (const [direction, pitch] of [["down", -1], ["level", 0], ["up", 1]] as const) {
      const w = copy(wind), a = copy(strike);
      if (pitch < 0) {
        w.torso[0] -= 0.18; a.torso[0] += 0.30;
        w.head[0] += 0.12; a.head[0] += 0.19;
        if (kicks) {
          w.leg_r[0] += 0.24; a.leg_r[0] -= 1.30;
          w.leg_l[0] += 0.20; a.leg_l[0] += 0.32;
        } else if (!ranged) {
          w.arm_r[0] = Math.min(w.arm_r[0], -1.85);
          a.arm_r[0] = Math.max(a.arm_r[0], 0.37);
          w.arm_l[0] = Math.min(w.arm_l[0], -0.95);
          a.arm_l[0] += 0.27;
        }
      } else if (pitch > 0) {
        w.torso[0] += 0.09; a.torso[0] -= 0.23;
        a.head[0] -= 0.16;
        if (kicks) {
          w.leg_r[0] += 0.24; a.leg_r[0] -= 1.55;
        } else if (!ranged) {
          w.arm_r[0] = Math.max(w.arm_r[0], -0.33);
          a.arm_r[0] = Math.min(a.arm_r[0], -1.65);
          a.arm_l[0] -= 0.24;
        }
      } else {
        w.torso[1] += 0.13; a.torso[1] -= 0.27;
        if (kicks) a.leg_r[0] -= 0.75;
      }
      w.leg_l[0] -= 0.28; w.leg_r[0] += 0.19;
      a.leg_l[0] -= 0.20; a.leg_r[0] += 0.25;
      this.poses[`air_slice_${direction}_w`] = w;
      this.poses[`air_slice_${direction}_s`] = a;
    }
  }

  /** Lock aim at contact time, not the earlier button press. */
  private airAimAtOpponent(): number {
    const opponent = this.opponent;
    if (!opponent || opponent.isDown()) return 0;
    const delta = opponent.chest().sub(this.chest());
    const horizontal = Math.hypot(delta.x, delta.z);
    if (horizontal > 3.0) return 0;
    return THREE.MathUtils.clamp(Math.atan2(delta.y, Math.max(0.45, horizontal)), -1.20, 0.90);
  }

  private tryAirSlice() {
    if (this.onGround || this.airSliceUsed || this.atkLock > 0 ||
        (this.state !== S.IDLE && this.state !== S.BLOCK)) return;
    this.airSliceUsed = true;
    this.airSliceQueued = false;
    this.airSliceAngle = this.airAimAtOpponent();
    this.holding = false;
    this.startAttack("air_l1");
  }

  isDown() { return this.state === S.KO; }""", "Directional poses and aiming helper")
    start = s.index('    // AIR_COMBAT_V1: Space+Click resolves on press, no charged-heavy misfire.')
    end = s.index('    if (pressed && this.kit === "glaive"', start)
    old = s[start:end]
    new = """    // Airborne left-click is an ordinary basic swing, even without Space held.
    // No launcher, no chain, no chase jump, and no ground smash.
    if (!this.stage && pressed && this.onGround && this.intent.jump &&
        (this.state === S.IDLE || this.state === S.BLOCK)) {
      this.airSliceQueued = true; this.holding = false; return;
    }
    if (!this.stage && pressed && !this.onGround) {
      this.holding = false;
      this.tryAirSlice();
      return;
    }
"""
    s = once(s, old, new, "Replace launcher combo input with basic air click")
    s = once(s, """    // AIR_COMBAT_V1: Space+Click launches an anti-air instead of also jumping.
    // The player must release Space, then tap it again after a landed launcher to chase.
    const want = this.stage ? (this.intent.jump || this.up()) : this.intent.jump;
    const was = this.stage ? this.upPrev : this.jumpPrev;
    if (want && !was && this.airChaseT > 0 && this.airChaseTarget && !this.airChaseUsed &&
        (this.state === S.IDLE || (this.state === S.ATTACK && this.atkId === "anti_air" && this.atkPhase >= 1))) {
      this.jumpPrev = true;
      this.upPrev = true;
      this.startAirChase();
      return;
    }
    if (this.onGround && this.state === S.ATTACK && this.atkId === "anti_air") {
      this.jumpPrev = want;
      this.upPrev = want;
      return;
    }
    // An aerial Space+Click is an attack, not a second jump.
    if (!this.onGround && this.state === S.ATTACK &&
        (this.atkId.startsWith("air_l") || this.atkId === "air_heavy") && this.intent.attack) {
      this.jumpPrev = want;
      this.upPrev = want;
      return;
    }
    if (this.stage) { this.readJumpPlat(); return; }""",
        """    // In 3D arena mode Space is always a jump, never an automatic launcher.
    if (this.stage) { this.readJumpPlat(); return; }""",
        "Space now jumps normally")
    s = once(s, """      this.velY = this.jumpV;
      this.onGround = false;
      if (this.state === S.BLOCK) this.setState(S.IDLE);""",
        """      this.velY = this.jumpV;
      this.onGround = false;
      this.airSliceUsed = false;
      if (this.state === S.BLOCK) this.setState(S.IDLE);
      // Space+Click on the same frame: jump, then swing (never anti-air launch).
      if (this.airSliceQueued) this.tryAirSlice();""",
        "Support jump and click on the same frame")
    s = once(s, """    } else if (pressed && !this.onGround && this.kit === "wind" && this.airJump < 1 && this.state === S.IDLE) {
      // Double jump: a second push of wind.""",
        """    } else if (pressed && !this.onGround && this.kit === "wind" && this.airJump < 1 && this.state === S.IDLE) {
      // Double jump: a second push of wind.""",
        "Double jump retained") if False else s
    s = once(s, """    if (this.atkPhase === 0 && this.stateT >= w) {
      this.atkPhase = 1;
      this.onSwing(this);""",
        """    if (this.atkPhase === 0 && this.stateT >= w) {
      this.atkPhase = 1;
      if (!this.stage && this.atkId === "air_l1") this.airSliceAngle = this.airAimAtOpponent();
      this.onSwing(this);""",
        "Update attack angle immediately before contact")
    s = once(s, """    // AIR_COMBAT_V1: all air attacks use the same procedural / VRM pose pipeline.
    // Existing attack poses are chosen per-kit in kits.ts.
    this.poseName = p;""",
        """    // Directional air swings use real distinct poses, including for remote VRM models.
    if (!this.stage && this.state === S.ATTACK && this.atkId === "air_l1") {
      const direction = this.airSliceAngle < -0.28 ? "down" :
        this.airSliceAngle > 0.28 ? "up" : "level";
      p = `air_slice_${direction}_${this.atkPhase === 0 ? "w" : "s"}`;
      sp = this.atkPhase === 0 ? 20 : 44;
    }
    this.poseName = p;""",
        "Body and blade pose tracks opponent height")
    # Both arena and platform landing reset; platform gameplay otherwise unchanged.
    s = once(s, """      this.onGround = true;
      this.airJump = 0;""",
        """      this.onGround = true;
      this.airSliceUsed = false;
      this.airSliceQueued = false;
      this.airJump = 0;""",
        "3D landing clears air swing")
    s = once(s, """        this.onGround = true;
        this.ground = p;
        this.airJumps = 1;""",
        """        this.onGround = true;
        this.airSliceUsed = false;
        this.airSliceQueued = false;
        this.ground = p;
        this.airJumps = 1;""",
        "Platform landing clears air swing")
    s = once(s, """    this.airChaseT = 0; this.airChaseMoveT = 0; this.airRecoverUsed = false;""",
        """    this.airChaseT = 0; this.airChaseMoveT = 0; this.airRecoverUsed = false;
    this.airSliceUsed = false; this.airSliceQueued = false;""",
        "Revive clears air swing")
    s = once(s, """    this.airChaseT = 0; this.airChaseMoveT = 0;
    this.clashMomentum = 0;""",
        """    this.airChaseT = 0; this.airChaseMoveT = 0;
    this.airSliceUsed = false; this.airSliceQueued = false;
    this.clashMomentum = 0;""",
        "KO clears air swing")
    return '// ' + TAG + '\n' + s

def game_patch(s: str) -> str:
    if TAG in s: return s
    if NEEDS not in s: raise PatchError('Install Knockback / Knockdown / Wake-up first.')
    s = remove_old_juggles(s, "game.ts")
    s = once(s, """    const antiAir = f.atkId === "anti_air";
    const airCombo = f.atkId.startsWith("air_l");""",
        """    const antiAir = f.atkId === "anti_air";
    const airCombo = f.atkId.startsWith("air_l");
    const directionalAir = !f.stage && f.atkId === "air_l1";""",
        "Activate directed air hit detection")
    s = once(s, """        dy < (antiAir || airCombo || d.atkId === "anti_air" || d.atkId.startsWith("air_l") ? 1.65 : 0.8)) {""",
        """        dy < (directionalAir || d.atkId === "air_l1" ? 2.1 :
          antiAir || airCombo || d.atkId === "anti_air" || d.atkId.startsWith("air_l") ? 1.65 : 0.8)) {""",
        "Air sword clashes can occur at different elevations")
    s = once(s, """      const dir = to.clone().divideScalar(Math.max(dist, 0.001));
      if (d instanceof Fighter && this.isDuel()""",
        """      const dir = to.clone().divideScalar(Math.max(dist, 0.001));
      // Don't allow a blade clash outside the aiming direction of an air slice.
      if (directionalAir) {
        const v = d.chest().y - f.chest().y;
        const angle = Math.atan2(v, Math.max(0.45, dist));
        if (Math.hypot(Math.max(0, dist - d.radius * 0.45), v) > a.reach + 0.22 ||
            Math.abs(v) > 2.15 || Math.abs(angle - f.airSliceAngle) > 0.48 ||
            (dist > 0.6 && dir.dot(fwd) < 0.12)) continue;
      }
      if (d instanceof Fighter && this.isDuel()""",
        "Gate air weapon clashes by slice direction")
    s = once(s, """      if (dist - d.radius + 0.35 > a.reach ||
          dy > (antiAir ? 3.25 : airCombo ? 1.8 : 1.3) ||
          (dist > 0.6 && dir.dot(fwd) < (antiAir ? -0.08 : 0.15))) continue;
      const hitPos = d.chest().addScaledVector(dir, -0.15);""",
        """      if (directionalAir) {
        // A blade cuts along a real inclined swing path, not a huge vertical cylinder.
        // From above a target the swing angles DOWN; from below it angles UP.
        const deltaY = d.chest().y - f.chest().y;
        const aimToTarget = Math.atan2(deltaY, Math.max(0.45, dist));
        const trueDistance = Math.hypot(Math.max(0, dist - d.radius * 0.45), deltaY);
        if (trueDistance > a.reach + 0.22 || Math.abs(deltaY) > 2.15 ||
            Math.abs(aimToTarget - f.airSliceAngle) > 0.48 ||
            (dist > 0.6 && dir.dot(fwd) < 0.12)) continue;
      } else if (dist - d.radius + 0.35 > a.reach ||
          dy > (antiAir ? 3.25 : airCombo ? 1.8 : 1.3) ||
          (dist > 0.6 && dir.dot(fwd) < (antiAir ? -0.08 : 0.15))) continue;
      const hitPos = d.chest().addScaledVector(dir, -0.15);""",
        "Real downward / horizontal / upward melee contact")
    # Disable legacy launch on 3D arena hits, preserving any other kit-specific launch skills.
    s = once(s, """      if (antiAir && d instanceof Fighter && (result === "hit" || result === "crit")) {
        // Launcher happens only after an HP hit, never through blocks/parries/clashes.
        const wasGrounded = d.onGround;""",
        """      if (antiAir && f.stage && d instanceof Fighter && (result === "hit" || result === "crit")) {
        // Platform mode retains its legacy anti-air. 3D arena no longer uses launchers.
        const wasGrounded = d.onGround;""",
        "No forced 3D arena launcher")
    s = once(s, """      const sample = from.clone().lerp(to, i / 5).sub(center);
      const vertical = Math.abs(sample.y);""",
        """      const sample = from.clone().lerp(to, i / 5).sub(center);
      const vertical = Math.abs(sample.y);
      // Only intercept a projectile if it is inside the visible air-slash arc.
      if (!f.stage && f.atkId === "air_l1") {
        const flat = Math.hypot(sample.x, sample.z);
        const pitch = Math.atan2(sample.y, Math.max(0.45, flat));
        if (Math.abs(pitch - f.airSliceAngle) > 0.48 ||
            Math.hypot(flat, sample.y) > reach + horizontalRoom) continue;
      }""",
        "Directional projectile interception for air slices")
    return '// ' + TAG + '\n' + s

def ai_patch(s: str) -> str:
    if TAG in s: return s
    s = remove_old_juggles(s, "ai.ts")
    s = once(s, """  private antiAirCd = 0;
  private aiAirTap = false;""",
        """  private antiAirCd = 0;
  private aiAirTap = false;
  private airSliceCd = 0;""",
        "AI separate air-slice reaction timer")
    s = once(s, """    this.antiAirCd = Math.max(0, this.antiAirCd - dt);
    this.aiAirTap = false;""",
        """    this.antiAirCd = Math.max(0, this.antiAirCd - dt);
    this.airSliceCd = Math.max(0, this.airSliceCd - dt);
    this.aiAirTap = false;""",
        "Tick AI air swing timer")
    start=s.index('    if (f.state === S.IDLE && f.onGround && !RANGED.has(f.kit) &&\n        o.root.position.y')
    end=s.index('    if (!this.aiAirTap) this.offense(f, o, dt);',start)
    old=s[start:end]
    new="""    // A cautious jump-in occasionally replaces the old automatic uppercut launcher.
    // Airborne CPUs swing toward an opponent's current elevation, just like players.
    const flatGap = f.root.position.clone().setY(0)
      .distanceTo(o.root.position.clone().setY(0));
    if (!f.stage && f.onGround && f.state === S.IDLE && !RANGED.has(f.kit) &&
        this.antiAirCd <= 0 && flatGap > 0.65 && flatGap < 2.3 &&
        Math.random() < dt * 0.24) {
      f.intent.jump = true;
      this.antiAirCd = rand(2.2, 3.8);
    }
    if (!f.stage && !f.onGround && f.state === S.IDLE && !f.airSliceUsed &&
        flatGap < f.attacks.air_l1.reach + 0.20 &&
        Math.abs(o.chest().y - f.chest().y) < 2.1 && this.airSliceCd <= 0 &&
        Math.random() < dt * 7.0) {
      this.aiAirTap = true;
      this.airSliceCd = rand(0.55, 0.85);
      this.queue = [];
      this.hold = 0;
    }
"""
    s=once(s,old,new,"AI uses natural jump and aerial slash")
    s=once(s, """    if (this.aiAirTap) {
      f.intent.jump = true;
      f.intent.attack = true;
      return;
    }
    if (f.airChaseT > 0 && f.state === S.IDLE && !RANGED.has(f.kit)) {
      // Follow up with a pure Space press, never another grounded anti-air chord.
      this.queue = [];
      this.hold = 0;
      f.intent.attack = false;
      f.intent.jump = true;
      return;
    }""",
      """    if (this.aiAirTap) {
      f.intent.jump = false; // an air slash is just left-click, not Space+Click
      f.intent.attack = true;
      return;
    }""",
      "Remove automatic aerial chase and use simple air attack")
    return '// ' + TAG + '\n' + s

PATCHERS = {
    "src/game/fighter.ts": fighter_patch,
    "src/game/game.ts": game_patch,
    "src/game/ai.ts": ai_patch,
}

def get_folder(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    try:
        import tkinter as tk
        from tkinter import filedialog
        app = tk.Tk(); app.withdraw(); app.attributes('-topmost', True)
        chosen = filedialog.askdirectory(title="Choose Fight Royale project (contains src/game)")
        app.destroy()
        if chosen:
            return Path(chosen).resolve()
    except Exception:
        pass
    typed = input("Fight Royale project folder: ").strip().strip('"')
    if not typed:
        raise PatchError("No folder selected")
    return Path(typed).expanduser().resolve()

def main() -> int:
    p = argparse.ArgumentParser(description="Install grounded directional jump slashes")
    p.add_argument("folder", nargs="?", help="Project root (contains src/game)")
    p.add_argument("--dry-run", "--check", action="store_true", help="Verify compatibility without editing")
    args = p.parse_args()
    root = get_folder(args.folder)
    original = {}
    for rel in FILES:
        path = root / rel
        if not path.is_file():
            raise PatchError(f"Missing {path}. Choose the project's ROOT folder.")
        original[rel] = path.read_text(encoding="utf-8-sig")
    old_markers = [OLD_JUGGLE_TAG in original[rel] for rel in FILES]
    if any(old_markers) and not all(old_markers):
        raise PatchError("Previous aerial-juggle update is only partially installed. Restore its missing files before proceeding.")
    installed = [TAG in original[rel] for rel in FILES]
    if all(installed):
        print("Grounded Air Slices already installed; no changes necessary.")
        return 0
    if any(installed):
        raise PatchError("Partial Grounded Air Slices installation detected; restore backups first.")
    updated = {rel: PATCHERS[rel](original[rel]) for rel in FILES}
    if args.dry_run:
        print("PASS: All 3 files compatible. No files changed.")
        if all(old_markers): print("Previous Aerial Juggles patch can be safely removed.")
        return 0
    backup = root / ".grounded_air_backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup.mkdir(parents=True, exist_ok=False)
    for rel in FILES:
        dest = backup / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dest)
    applied=[]
    try:
        for rel in FILES:
            path = root / rel
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                             prefix=path.name+".", suffix=".tmp", delete=False) as tmp:
                tmp.write(updated[rel]); tmp_path=Path(tmp.name)
            try:
                os.replace(tmp_path, path)
            finally:
                tmp_path.unlink(missing_ok=True)
            applied.append(rel)
    except Exception:
        for rel in applied:
            shutil.copy2(backup / rel, root / rel)
        raise
    print("Installed Grounded Air Slices (3 files updated).")
    if all(old_markers): print("Removed the previous aerial juggle / chase / slam patch.")
    print("Backup saved to:", backup)
    print("Controls: Space = jump; Left Click while airborne = one aimed slash per jump.")
    print("No launcher combo, no aerial juggling, no chase, no slam.")
    return 0

if __name__ == "__main__":
    try:
        code=main()
        if sys.stdin.isatty():
            input("\nPress Enter to close...")
        raise SystemExit(code)
    except (PatchError, OSError, UnicodeError) as e:
        print("ERROR:", e, file=sys.stderr)
        if sys.stdin.isatty():
            input("\nPress Enter to close...")
        raise SystemExit(1)
