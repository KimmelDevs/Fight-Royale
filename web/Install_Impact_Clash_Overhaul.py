#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale — Impact & Clash Overhaul (standalone Python installer).

Adds dramatic 3D impact rays, layered clash shocks, parry/guard-break feedback,
subtle screen flashes/camera punch, and a cinematic KO flash. Does NOT change
HP, damage, skills, or Zarek's Clash Momentum award rules.

Usage:
  python Install_Impact_Clash_Overhaul.py
  python Install_Impact_Clash_Overhaul.py "C:\\path\\to\\Fight-Royale"
  python Install_Impact_Clash_Overhaul.py "C:\\path\\to\\Fight-Royale" --dry-run

Requires Python 3.9+. No extra packages or downloads. Backs up files first.
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile

MARKER = 'FIGHT_ROYALE_IMPACT_CLASH_OVERHAUL_V1'
FILES = ('src/game/game.ts', 'src/game/fx.ts')

# Extra world-space impact shock: orient to active camera so it reads in both
# 3D duels and platform brawls. Shared geometry, small fixed mesh budget.
NEW_3D_FX = r'''  /** IMPACT_OVERHAUL_V1: short-lived anime impact spokes, concentric halos,
   * and directional fragments. Rendered at the actual hit position. */
  impactBurst(pos: THREE.Vector3, color: string, power = 1, kind = "hit") {
    const weight = Math.max(0.4, Math.min(power, 2.4));
    const isClash = kind === "clash" || kind === "projectile";
    const group = new THREE.Group();
    group.position.copy(pos);
    const faded: { material: THREE.MeshBasicMaterial; alpha: number }[] = [];
    const mat = (hex: string, alpha: number) => {
      const m = new THREE.MeshBasicMaterial({ color: hex, transparent: true, opacity: alpha,
        depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
      faded.push({ material: m, alpha });
      return m;
    };
    const ringA = new THREE.Mesh(CLASH_HALO, mat("#ffffff", 0.96));
    const ringB = new THREE.Mesh(CLASH_HALO, mat(color, 0.85));
    group.add(ringA, ringB);
    const core = new THREE.Mesh(SPH, mat("#fffbea", 0.83));
    group.add(core);
    const spokes = new THREE.Group();
    const count = kind === "finish" ? 12 : isClash ? 10 : 7;
    for (let i = 0; i < count; i++) {
      const spike = new THREE.Mesh(CLASH_STREAK, mat(i % 3 === 0 ? "#ffffff" : color,
        i % 3 === 0 ? 0.92 : 0.76));
      spike.rotation.z = i * Math.PI * 2 / count + 0.14;
      spike.position.set(Math.cos(spike.rotation.z) * 0.3, Math.sin(spike.rotation.z) * 0.3, 0);
      spike.scale.set(0.85 + (i % 3) * 0.17, 0.85, 1);
      spokes.add(spike);
    }
    group.add(spokes);
    // Each spawned material belongs to this effect; shared geometry is never disposed.
    group.traverse((obj) => { if ((obj as THREE.Mesh).isMesh) (obj as any).ownsMat = true; });
    const duration = kind === "finish" ? 0.40 : isClash ? 0.32 : 0.22;
    let t = 0;
    this.add(group, (dt) => {
      t += dt;
      const f = Math.min(t / duration, 1);
      group.quaternion.copy(this.camera.quaternion);
      const ease = 1 - Math.pow(1 - f, 3);
      const fading = Math.pow(1 - f, 1.6);
      ringA.scale.setScalar(weight * (0.15 + 1.45 * ease));
      ringB.scale.setScalar(weight * (0.08 + 1.95 * ease));
      ringB.rotation.z = f * 0.26;
      spokes.scale.setScalar(weight * (0.8 + 0.5 * ease));
      spokes.rotation.z = f * 0.23;
      core.scale.setScalar(weight * Math.max(0.04, 0.18 - f * 0.14));
      for (const item of faded) item.material.opacity = item.alpha * fading;
      return t < duration;
    });
    // Existing regular-hit sparks stay in place. Only powerful impacts get extras,
    // limiting overdraw during fast continuous combos.
    if (weight >= 1) {
      this.sparks(pos, "#ffffff", isClash || kind === "finish" ? 14 : 8, 8 * weight);
      this.sparks(pos, color, isClash || kind === "finish" ? 14 : 9, 6 * weight);
    }
  }

  /** Real-time (not hitstop-scaled) screen flash; throttle multihit spam. */
  screenImpact(kind: string, color: string, power = 1) {
    if (typeof document === "undefined" || !document.body) return;
    const now = performance.now();
    if (kind !== "finish" && now - this.lastScreenImpact < 90) return;
    this.lastScreenImpact = now;
    const strength = Math.max(0.2, Math.min(power, 1.2));
    const life = kind === "finish" ? 0.34 : kind === "parry" ? 0.19 : 0.14;
    const el = document.createElement("div");
    el.setAttribute("aria-hidden", "true");
    el.style.position = "fixed";
    el.style.inset = "0";
    el.style.zIndex = "999";
    el.style.pointerEvents = "none";
    if (kind === "finish") {
      // The dark outer frame and white center mimic an anime finishing impact.
      el.style.background = "radial-gradient(ellipse at 50% 46%, rgba(255,255,255,0.94) 0%, rgba(255,255,255,0.68) 19%, rgba(0,0,0,0.10) 44%, rgba(0,0,0,0.83) 100%)";
    } else {
      el.style.background = `radial-gradient(ellipse at 50% 48%, rgba(255,255,255,0.65) 0%, ${color}30 29%, transparent 65%)`;
      el.style.boxShadow = `inset 0 0 110px 22px ${color}55`;
    }
    el.style.opacity = "0";
    document.body.appendChild(el);
    this.screenFlashes.push({ el, elapsed: 0, duration: life, strength });
    // Prevent too many overlapping DOM nodes during very rapid multi-hit skills.
    while (this.screenFlashes.length > 3) this.screenFlashes.shift()!.el.remove();
  }

'''

NEW_FX_FIELDS = '''  // Impact & Clash Overhaul: screen flashes run on real time through hitstop.
  private screenFlashes: { el: HTMLDivElement; elapsed: number; duration: number; strength: number }[] = [];
  private lastScreenImpact = -1e9;
'''

NEW_FX_UPDATE = '''    // Update in real time: flashes shouldn't remain on screen during hitstop.
    this.screenFlashes = this.screenFlashes.filter((flash) => {
      flash.elapsed += realDt;
      const f = Math.min(flash.elapsed / flash.duration, 1);
      const appear = Math.min(1, f / 0.13);
      flash.el.style.opacity = String(flash.strength * appear * Math.pow(1 - f, 2.3));
      if (f >= 1) { flash.el.remove(); return false; }
      return true;
    });
'''


def change_once(text: str, needle: str, replacement: str, file: str, description: str) -> str:
    n = text.count(needle)
    if n != 1:
        raise RuntimeError(f'{file}: cannot safely locate {description} (found {n} matches). '
                           'No files have been changed. Please use your latest project files.')
    return text.replace(needle, replacement, 1)


def patch_fx(text: str) -> str:
    if MARKER in text:
        return text
    name = 'fx.ts'
    if 'clashBurst(pos: THREE.Vector3' not in text or 'const CLASH_STREAK' not in text:
        raise RuntimeError('fx.ts is missing the earlier clash effects; no files changed.')
    text = change_once(text,
        '  private numbers: { el: HTMLDivElement; pos: THREE.Vector3; t: number }[] = [];',
        '  private numbers: { el: HTMLDivElement; pos: THREE.Vector3; t: number }[] = [];\n'+NEW_FX_FIELDS.rstrip('\n'),
        name, 'Fx screen flash state')
    text = change_once(text,
        '    const p = new THREE.Vector3();\n    this.numbers = this.numbers.filter((n) => {',
        NEW_FX_UPDATE+'    const p = new THREE.Vector3();\n    this.numbers = this.numbers.filter((n) => {',
        name, 'Fx.update')
    text = change_once(text,
        '    this.numbers = [];\n  }\n\n  private add(',
        '    this.numbers = [];\n    for (const flash of this.screenFlashes) flash.el.remove();\n    this.screenFlashes = [];\n  }\n\n  private add(',
        name, 'Fx.clear cleanup')
    # Sparks allocate unique mats; this effect-heavy release must also free them.
    text = change_once(text,
        '    speed: number, dir: THREE.Vector3 | null, spread: number, gravity: number, life: number, scale: number, align: boolean) {\n    const inst = new THREE.InstancedMesh(geo, mat, amount);',
        '    speed: number, dir: THREE.Vector3 | null, spread: number, gravity: number, life: number, scale: number, align: boolean, ownMat = false) {\n    const inst = new THREE.InstancedMesh(geo, mat, amount);\n    if (ownMat) (inst as any).ownsMat = true;',
        name, 'temporary spark material cleanup')
    text = change_once(text,
        'this.burst(pos, BOX, new THREE.MeshBasicMaterial({ color }), amount, speed, dir, dir ? 0.7 : 1, 9, 0.35, 1, true);',
        'this.burst(pos, BOX, new THREE.MeshBasicMaterial({ color }), amount, speed, dir, dir ? 0.7 : 1, 9, 0.35, 1, true, true);',
        name, 'spark material ownership')
    text = change_once(text,
        '  flash(pos: THREE.Vector3, color: string, size = 0.5, dur = 0.14, opacity = 0.8) {',
        NEW_3D_FX+'  flash(pos: THREE.Vector3, color: string, size = 0.5, dur = 0.14, opacity = 0.8) {',
        name, 'new effects')
    return '// '+MARKER+'\n'+text


def patch_game(text: str) -> str:
    if MARKER in text:
        return text
    name = 'game.ts'
    required = ('private finishMeleeProjectile(', 'case "kaizen_guard_clash":',
                'case "guard_break":', 'private clash(', 'case "clashBurst":')
    for needle in required:
        if needle not in text:
            raise RuntimeError(f'game.ts is missing {needle}; no files changed.')
    text = change_once(text, '  private shakeT = 0;',
        '  private shakeT = 0;\n  private impactCameraPunch = 0;', name, 'camera punch state')
    text = change_once(text,
        '      case "clashBurst": fx.clashBurst(v3(a[0]), a[1], a[2]); break;',
        '      case "clashBurst": fx.clashBurst(v3(a[0]), a[1], a[2]); break;\n'
        '      case "impactBurst": fx.impactBurst(v3(a[0]), a[1], a[2], a[3]); break;\n'
        '      case "impactFrame":\n'
        '        fx.screenImpact(a[0], a[1], a[2]);\n'
        '        if (a[0] === "clash" || a[0] === "finish" || a[0] === "guardbreak")\n'
        '          Sound.play("hit_big", a[0] === "finish" ? 0.48 : 0.23);\n'
        '        this.impactCameraPunch = Math.max(this.impactCameraPunch, Math.min(a[2] ?? 0.7, 1.2));\n'
        '        break;',
        name, 'networked effect handling')
    # Existing hitstop can be overridden by smaller hits on the same frame; preserve
    # a cinematic KO freeze rather than allowing ordinary later hits to cancel it.
    text = change_once(text,
        '    this.timeScale = scale;\n    this.stopUntil = performance.now() + dur * 1000;',
        '    const now = performance.now();\n'
        '    if (this.stopUntil <= now) {\n'
        '      this.timeScale = scale;\n'
        '      this.stopUntil = now + dur * 1000;\n'
        '    } else {\n'
        '      this.timeScale = Math.min(this.timeScale, scale);\n'
        '      this.stopUntil = Math.max(this.stopUntil, now + dur * 1000);\n'
        '    }', name, 'hitstop preservation')
    text = change_once(text,
        '    cam.rotateZ(0.04 * sh * Math.sin(this.shakeT * 1.1));',
        '    cam.rotateZ(0.04 * sh * Math.sin(this.shakeT * 1.1));\n'
        '    // Brief visual camera punch; never moves character hitboxes or changes damage.\n'
        '    this.impactCameraPunch = Math.max(0, this.impactCameraPunch - dt * 6.5);\n'
        '    if (this.impactCameraPunch > 0) {\n'
        '      cam.position.lerp(look, Math.min(0.095, this.impactCameraPunch * 0.065));\n'
        '    }', name, 'camera impact punch')
    text = change_once(text,
        '    const bomb = !!p.atk && (p.atk.type === "lob" || p.style === "bomb");',
        '    const bomb = !!p.atk && (p.atk.type === "lob" || p.style === "bomb");\n'
        '    this.fxp("impactBurst", contact, defender.look.glow, bomb ? 1.55 : 1.35, "projectile");\n'
        '    this.fxp("impactFrame", "projectile", defender.look.glow, bomb ? 0.75 : 0.55);',
        name, 'melee projectile clashes')
    # Visual additions after result is known; this code never modifies damage or awards stacks.
    text = change_once(text,
        '      case "kaizen_guard_clash": {',
        '      case "kaizen_guard_clash": {\n'
        '        this.fxp("impactBurst", shieldPos, "#ffedbc", 1.65, "clash");\n'
        '        this.fxp("impactFrame", "clash", "#ffe8b0", 0.75);',
        name, 'chainblade guard clash')
    text = change_once(text,
        '        this.hitSound(attacker, a, crit);',
        '        this.hitSound(attacker, a, crit);\n'
        '        // Full-screen finish only for duel fighters and bosses, not every survival mob.\n'
        '        const cinematicKo = result === "ko" && (d instanceof Fighter || (d instanceof Mob && d.def.boss));\n'
        '        if (!ranged || a.heavy || crit || result === "ko")\n'
        '          this.fxp("impactBurst", hitPos, glow, cinematicKo ? 2.0 : heavy || crit ? 1.25 : 0.65,\n'
        '            cinematicKo ? "finish" : heavy || crit ? "heavy" : "hit");\n'
        '        if (cinematicKo) this.fxp("impactFrame", "finish", glow, 1.0);\n'
        '        else if (heavy || crit) this.fxp("impactFrame", "heavy", glow, crit ? 0.75 : 0.58);',
        name, 'hits, criticals and finishing blows')
    # Case labels can have a trailing { in some earlier installers; both forms work.
    text = change_once(text, '      case "blocked":',
        '      case "blocked":\n'
        '        if (ranged && a.type === "projectile")\n'
        '          this.fxp("impactBurst", shieldPos, "#a9e8ff", 0.88, "block");\n'
        '        else if (!ranged && a.type === "melee")\n'
        '          this.fxp("impactBurst", shieldPos, "#ffe19c", 0.76, "block");',
        name, 'block feedback')
    text = change_once(text, '      case "parry":',
        '      case "parry":\n'
        '        this.fxp("impactBurst", shieldPos, "#b9f5ff", 1.65, "clash");\n'
        '        this.fxp("impactFrame", "parry", "#b9f5ff", 0.72);',
        name, 'parry feedback')
    text = change_once(text, '      case "guard_break":',
        '      case "guard_break":\n'
        '        this.fxp("impactBurst", hitPos, "#ff9f43", 1.65, "clash");\n'
        '        this.fxp("impactFrame", "guardbreak", "#ff9f43", 0.85);',
        name, 'guard break feedback')
    text = change_once(text,
        '  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {',
        '  private clash(a: Fighter, b: Fighter, pos: THREE.Vector3) {\n'
        '    this.fxp("impactBurst", pos, "#ffedb7", 1.95, "clash");\n'
        '    this.fxp("impactFrame", "clash", "#ffe5a2", 0.80);',
        name, 'real weapon clashes')
    text = change_once(text,
        '  private onBlast(f: Fighter) {',
        '  private onBlast(f: Fighter) {\n'
        '    this.fxp("impactFrame", "finish", f.look.glow, 0.85);',
        name, 'blast-zone finisher')
    return '// '+MARKER+'\n'+text

PATCHES = {'src/game/fx.ts': patch_fx, 'src/game/game.ts': patch_game}


def find_project(path: str | None) -> Path:
    candidates = [Path(path).expanduser()] if path else [Path.cwd(), Path(__file__).resolve().parent]
    for candidate in candidates:
        if all((candidate / file).is_file() for file in FILES):
            return candidate.resolve()
    if path:
        raise RuntimeError('Choose the Fight Royale root folder containing src/game/game.ts and fx.ts.')
    selected = None
    try:
        from tkinter import Tk, filedialog
        ui = Tk()
        ui.withdraw()
        ui.attributes('-topmost', True)
        selected = filedialog.askdirectory(title='Choose Fight Royale folder (contains src)')
        ui.destroy()
    except Exception:
        pass
    if not selected:
        try:
            selected = input('Fight Royale project folder (full path): ').strip().strip('"')
        except (EOFError, OSError):
            selected = ''
    if not selected:
        raise RuntimeError('No folder selected.')
    root = Path(selected).expanduser().resolve()
    if not all((root / file).is_file() for file in FILES):
        raise RuntimeError('That folder does not contain src/game/game.ts and fx.ts.')
    return root


def atomic_write(file: Path, data: bytes) -> None:
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.impact_', dir=file.parent, delete=False) as tmp:
            tmp_name = tmp.name
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, file)
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)


def install(root: Path, dry_run: bool) -> tuple[list[str], Path | None]:
    changes = {}
    # Validate both scripts before writing anything. Don't touch unrelated files.
    for rel in FILES:
        file = root / rel
        original = file.read_bytes()
        if original.startswith(b'\xef\xbb\xbf'):
            raise RuntimeError(f'{rel}: unexpected UTF-8 BOM; no files were changed.')
        decoded = original.decode('utf-8')
        crlf = decoded.count('\r\n') > decoded.count('\n') / 2
        normalized = decoded.replace('\r\n', '\n').replace('\r', '\n')
        patched = PATCHES[rel](normalized)
        output = (patched.replace('\n', '\r\n') if crlf else patched).encode('utf-8')
        if output != original:
            changes[file] = (original, output)
    if not changes or dry_run:
        return [str(file.relative_to(root)) for file in changes], None

    backup = root / '.clash_backups' / dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f_impact')
    for file, (original, _) in changes.items():
        destination = backup / file.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(original)
    written = []
    try:
        for file, (_, output) in changes.items():
            atomic_write(file, output)
            written.append(file)
    except Exception:
        for file in written:
            atomic_write(file, changes[file][0])
        raise
    return [str(file.relative_to(root)) for file in changes], backup


def main() -> int:
    parser = argparse.ArgumentParser(description='Fight Royale Impact & Clash Overhaul installer')
    parser.add_argument('project', nargs='?', help='path to the project root (folder containing src)')
    parser.add_argument('--dry-run', action='store_true', help='check compatibility without modifying files')
    args = parser.parse_args()
    print('\n=== Fight Royale: Impact & Clash Overhaul ===\n')
    try:
        root = find_project(args.project)
        changed, backup = install(root, args.dry_run)
    except Exception as error:
        print('ERROR:', error)
        print('If a write failed, changed files were restored. Check the backups if needed.')
        return 1
    print('Project:', root)
    if args.dry_run:
        print('Dry run compatible; would modify: ' + ', '.join(changed) if changed else 'Already up to date.')
    elif not changed:
        print('Already installed — no modifications necessary.')
    else:
        print('Updated:', ', '.join(changed))
        print('Backups:', backup)
        print('No balance, skill, or Clash Momentum rules were modified.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
