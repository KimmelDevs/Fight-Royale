#!/usr/bin/env python3
"""Fight Royale — Raigo sharp-axe / slimmer-chain / midrange AI upgrade.

Place this file in web/ and run:
    python install_raigo_sharp_axe_ai.py --dry-run
    python install_raigo_sharp_axe_ai.py

Operates on existing Raigo builds (latest 2026-11-08 source). No dependencies.
Does not change attack damage, cooldowns, or physical chain tether length.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import os
import sys
import tempfile

MARK = "RAIGO_SHARP_AXE_MIDRANGE_AI_V1"

class PatchError(RuntimeError):
    pass


def replace_once(body: str, old: str, new: str, where: str) -> str:
    n = body.count(old)
    if n != 1:
        raise PatchError(f"{where}: expected 1 anchor, found {n}: {old[:125]!r}")
    return body.replace(old, new, 1)


def patch_model(src: str) -> str:
    if MARK in src:
        raise PatchError("model.ts has already received this upgrade")
    if "private buildRaigoAxeFlail()" not in src or "private updateRaigoWeapon(dt:number)" not in src:
        raise PatchError("model.ts: Raigo V2/V3 weapon builder not found; install Raigo first")
    src = replace_once(src,
        '    const steel=this.tn("#b8c0c7"), edge=this.tn("#f0e8d9"), iron=this.tn("#30383e"),',
        '    const steel=this.tn("#b8c0c7"), iron=this.tn("#30383e"),',
        'model.ts remove unused edge material')
    src = replace_once(src,
        '    this.raigoAxe=axe;\n    mesh(axe,cyl(.043,.046,1.36,10),dark,[0,.36,0]);',
        f'    this.raigoAxe=axe;\n    // {MARK}: 25% smaller axe (shaft, head, edge, grip); weapon remains in the right hand.\n    axe.scale.setScalar(.75);\n    mesh(axe,cyl(.043,.046,1.36,10),dark,[0,.36,0]);',
        'model.ts axe scale')
    before = '''    const outline=new THREE.Shape();
    outline.moveTo(.03,.20);outline.lineTo(.19,.36);
    outline.bezierCurveTo(.46,.30,.61,.15,.67,.06);
    outline.bezierCurveTo(.50,-.04,.48,-.19,.50,-.34);
    outline.lineTo(.20,-.22);outline.lineTo(.03,-.17);outline.closePath();
    const blade=new THREE.ExtrudeGeometry(outline,{depth:.055,bevelEnabled:true,bevelSize:.019,
      bevelThickness:.015,bevelSegments:1,steps:1});
    mesh(head,blade,steel,[0,0,-.027]);
    for(let j=0;j<4;j++) mesh(head,box(.09,.018,.015),edge,[.39+j*.053,.255-j*.115,.05],
      [0,0,-.25-j*.20]);'''
    after = '''    // Thin sharpened axe silhouette with a convex cutting edge, upper and lower horns.
    // Edge taper is cut into the actual extrusion; no floating glint bars.
    const outline=new THREE.Shape();
    outline.moveTo(.03,.18);outline.lineTo(.10,.36);
    outline.bezierCurveTo(.38,.40,.66,.28,.78,.04);
    outline.bezierCurveTo(.58,.02,.52,-.14,.58,-.38);
    outline.bezierCurveTo(.36,-.34,.16,-.24,.03,-.16);
    outline.closePath();
    const blade=new THREE.ExtrudeGeometry(outline,{depth:.05,bevelEnabled:false,curveSegments:24});
    // Full thickness at the spine, thinning to a fine cutting edge.
    const pos=blade.attributes.position;
    for(let i=0;i<pos.count;i++){
      const k=THREE.MathUtils.clamp(1-(pos.getX(i)-.12)/.62,.05,1);
      pos.setZ(i,(pos.getZ(i)-.025)*k);
    }
    pos.needsUpdate=true;
    blade.computeVertexNormals();
    mesh(head,blade,this.tn("#d6dce1"));
    head.add(new THREE.LineSegments(new THREE.EdgesGeometry(blade,35),
      new THREE.LineBasicMaterial({color:0xffffff})));'''
    src = replace_once(src, before, after, 'model.ts sharpened axe')
    src = replace_once(src, '    this.bladeTip=pivot(head,[.54,.04,0]);',
                           '    this.bladeTip=pivot(head,[.76,.04,0]);', 'model.ts true blade tip')
    src = replace_once(src,
        '''    // Alternating interlocked rings, not a skinny stretched cylinder.
    for(let i=0;i<32;i++) {
      const link=pivot(this);
      mesh(link,torus(.030,.055),i%2?steel:iron,[0,0,0],[0,i%2?PI/2:0,0]);''',
        '''    // 25% slimmer chain links; 44 links instead of 32 keep the chain visually connected.
    // The existing 3.05m tether is unchanged, so weapon range and gameplay stay consistent.
    for(let i=0;i<44;i++) {
      const link=pivot(this);
      mesh(link,torus(.0225,.04125),i%2?steel:iron,[0,0,0],[0,i%2?PI/2:0,0]);''',
        'model.ts chain rings')
    return src


def patch_ai(src: str) -> str:
    if MARK in src:
        raise PatchError("ai.ts has already received this upgrade")
    if 'raigo: { range: 2.90' not in src or 'private effectiveRangeBand(' not in src:
        raise PatchError("ai.ts: expected current Raigo AI layout not found")
    src = replace_once(src,
        '  // RAIGO_IRON_BASTION_V1: hold midrange, guard against rushdown, punish approach.\n  raigo: { range: 2.90, heavy: 0.30, combo: 0.73, bait: 0.69, pressure: 0.55, skillBias: [1.35, 1.60, 1.22] },',
        f'''  // {MARK}: outer-range flail controller, close axe punishment and measured counters.
  raigo: {{ range: 2.62, heavy: 0.23, combo: 0.70, bait: 0.80, pressure: 0.48, skillBias: [1.72, 2.05, 1.55] }},''',
        'ai.ts fighting style')
    src = replace_once(src,
        '"glaive" | "grappler" | "bruiser";',
        '"glaive" | "grappler" | "bruiser" | "chainwarden";',
        'ai.ts role type')
    src = replace_once(src,
        '  veyr:    { role: "executioner", pressure: 1.53, probe: 0.67, reset: 0.29, vReserve: 0.75, spacing: -0.24 },',
        '  veyr:    { role: "executioner", pressure: 1.53, probe: 0.67, reset: 0.29, vReserve: 0.75, spacing: -0.24 },\n'
        '  raigo: { role: "chainwarden", pressure: 0.88, probe: 1.48, reset: 0.58, vReserve: 1.10, spacing: 0.16 },',
        'ai.ts personality profile')
    src = replace_once(src,
        '''    if (f.kit === "glaive" && f.look.element === "metal")
      ideal = f.zenithSpearOut ? 1.54 : 2.05;
    // Keep a comfortable band, rather than alternating forward/back each frame.''',
        '''    if (f.kit === "glaive" && f.look.element === "metal")
      ideal = f.zenithSpearOut ? 1.54 : 2.05;
    if (f.kit === "axeflail") {
      // Inner axe range only when the long flail skills are cooling down.
      // Existing melee attack reach is still authoritative; this changes navigation only.
      const flailReady = ["z", "c", "v"].some(key => {
        const a = f.attacks[key];
        return a && (f.cooldowns[key] ?? 1) <= 0 &&
          ["Iron Comet", "Iron Tempest", "Twin Judgment"].includes(a.name);
      });
      ideal = flailReady ? 2.65 : 1.92;
      if (f.raigoMomentum === 3 && this.hasPunishWindow(o)) ideal = 1.95;
    }
    // Keep a comfortable band, rather than alternating forward/back each frame.''',
        'ai.ts adaptive range')
    # Add real, scripted-but-fallible theater moves without granting new reach.
    src = replace_once(src,
        '''      case "kaizen":
        // Remain at chain range: retreat from fists, then hook escaping prey.''',
        '''      case "raigo":
        // Step out of sword range, let the ball travel, then enter with the axe.
        if (hostileSwing && gap < 2.8 && this.theaterKey(f, "Chain Reversal") && intent(0.72))
          this.theaterPlan("circle", 0.17, "Chain Reversal");
        else if (gap < 2.10 && chased && this.theaterKey(f, "Iron Comet") && intent(0.76))
          this.theaterPlan("back", 0.24, "Iron Comet");
        else if (punish && gap < 3.10 && this.theaterKey(f, "Iron Tempest") && intent(0.80))
          this.theaterPlan("circle", 0.18, "Iron Tempest");
        break;
      case "kaizen":
        // Remain at chain range: retreat from fists, then hook escaping prey.''',
        'ai.ts movement personality')
    src = replace_once(src,
        '''      case "grappler":   if (gap > 1.8 && gap < 4.7 &&
          (f.cooldowns.x ?? 1) <= 0) probe += 1.1; break;''',
        '''      case "grappler":   if (gap > 1.8 && gap < 4.7 &&
          (f.cooldowns.x ?? 1) <= 0) probe += 1.1; break;
      case "chainwarden":
        if (gap < 2.0 && !opening) reset += 0.95;
        if (gap > 2.35 && gap < 3.3) probe += 0.92;
        if (f.raigoMomentum === 3 && opening) pressure += 1.15;
        break;''',
        'ai.ts personality reads')
    src = replace_once(src,
        '''      case "grappler":    if (a.style === "chain_predator_hook" && distance > 2.0 &&
          distance < 4.4 && !blocking) value += 1.15; break;''',
        '''      case "grappler":    if (a.style === "chain_predator_hook" && distance > 2.0 &&
          distance < 4.4 && !blocking) value += 1.15; break;
      case "chainwarden":
        if (a.mode === "counter" && incoming && distance < 2.8) value += 1.1;
        if (a.style === "raigo_comet" && distance > 2.15 && distance < 3.3) value += 0.65;
        if (a.style === "raigo_tempest" && opening && distance < 3.0) value += 0.75;
        if (a.style === "raigo_twinned" && f.raigoMomentum === 3 && opening) value += 1.1;
        break;''',
        'ai.ts role skills')
    src = replace_once(src,
        '''      case "kaizen":
        // Hook catches exposed opponents just outside the five-hit sword string.''',
        '''      case "raigo":
        // Use real cooldowns and opponent tells. No AI-only attacks or invisible range.
        if (name === "Chain Reversal") {
          if (!attackComing || distance > 2.65) viable = false;
          points += attackComing && distance < 2.6 ? 3.45 : -1.0;
        }
        if (name === "Iron Comet") {
          if (distance < 1.4 || distance > 3.48) viable = false;
          points += distance > 2.25 && distance < 3.25 && !blocking ? 2.15 :
            punish ? 1.5 : 0.1;
        }
        if (name === "Iron Tempest") {
          if (distance > 3.10) viable = false;
          points += punish ? 2.50 : blocking && o.guard < o.maxGuard * .52 ? 1.55 : 0.15;
        }
        if (name === "Twin Judgment") {
          if (distance < 1.35 || distance > 3.25 ||
              !(punish || o.state === S.STAGGER || o.state === S.HITSTUN ||
                (blocking && o.guard < o.maxGuard * .22))) viable = false;
          points += f.raigoMomentum === 3 ? 3.2 : punish ? 1.0 : -0.5;
        }
        break;
      case "kaizen":
        // Hook catches exposed opponents just outside the five-hit sword string.''',
        'ai.ts actual skill choices')
    src = replace_once(src,
        '''  if (distance > reach) return;
  if (danger && !punish''',
        '''  // A 3-meter ball reach must never trick the CPU into opening with a 2.22-meter axe.
  // It can still cast an actual ranged flail skill above; ordinary lights need honest range.
  if (id === "raigo" && distance > (f.attacks.l1?.reach ?? 2.22) + 0.06) return;
  if (distance > reach) return;
  if (danger && !punish''',
        'ai.ts prevent air swings')
    src = replace_once(src,
        '''  // Veyr's festival specifically favors sustained lights and real guard pressure.
  const festival = id === "veyr"''',
        '''  // Raigo only gambles on a long heavy when he has an actual punish opening.
  // Three real Momentum stacks make an axe verdict worth saving for contact.
  if (id === "raigo") heavyChance = f.raigoMomentum === 3
    ? (punish && distance < 2.16 ? 0.83 : 0.10)
    : blocked && o.guard < o.maxGuard * 0.40 ? 0.39 : 0.18;
  // Veyr's festival specifically favors sustained lights and real guard pressure.
  const festival = id === "veyr"''',
        'ai.ts momentum heavy')
    return src


def main() -> int:
    ap = argparse.ArgumentParser(description="Raigo smaller axe/chain + sharpened blade + midrange AI")
    ap.add_argument('--dry-run', action='store_true', help='Validate exact patch anchors; do not modify files')
    ap.add_argument('--root', type=Path, default=Path.cwd(), help='Fight Royale web directory (defaults to current folder)')
    args = ap.parse_args()
    root = args.root.resolve()
    paths = {'model': root/'src/game/model.ts', 'ai': root/'src/game/ai.ts'}
    for label, path in paths.items():
        if not path.is_file():
            raise PatchError(f"Missing {path}; place installer in web/ (not src/)")
    originals = {label: path.read_bytes() for label, path in paths.items()}
    text_orig = {label: b.decode('utf-8-sig').replace('\r\n', '\n') for label, b in originals.items()}
    if any(MARK in src for src in text_orig.values()):
        if all(MARK in src for src in text_orig.values()):
            raise PatchError('Raigo sharp-axe AI update is already installed. No files changed.')
        raise PatchError('Partial Raigo sharp-axe update detected. Restore backup before retrying.')
    updates = {
        'model': patch_model(text_orig['model']),
        'ai': patch_ai(text_orig['ai']),
    }
    for label in updates:
        if updates[label] == text_orig[label]:
            raise PatchError(f'No changes planned for {label}')
    if args.dry_run:
        print(f'DRY-RUN PASS — 2 source files: {root}')
        print('Axe and chain link geometry shrink 25%; thin grinded cutting edge and flush edge outline.')
        print('AI: dynamic mid-range spacing, counter timings, skill selection, and Momentum finishers.')
        print('No source files changed.')
        return 0
    backup_dir = root/'.raigo-backups'/('sharp_axe_ai_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup_dir.mkdir(parents=True, exist_ok=False)
    for label, path in paths.items():
        dst = backup_dir/path.relative_to(root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(originals[label])
    stages: dict[str, Path] = {}
    committed: list[str] = []
    try:
        for label, path in paths.items():
            with tempfile.NamedTemporaryFile('wb', delete=False, dir=path.parent, prefix='raigo_', suffix='.tmp') as tmp:
                line_style = '\r\n' if b'\r\n' in originals[label] else '\n'
                rendered = updates[label].replace('\n', line_style) if line_style != '\n' else updates[label]
                content = rendered.encode('utf-8-sig' if originals[label].startswith(b'\xef\xbb\xbf') else 'utf-8')
                tmp.write(content)
                stages[label] = Path(tmp.name)
        for label, path in paths.items():
            os.replace(stages.pop(label), path)
            committed.append(label)
    except BaseException:
        for label in committed:
            paths[label].write_bytes(originals[label])
        raise
    finally:
        for tmp in stages.values():
            try: tmp.unlink()
            except FileNotFoundError: pass
    print(f'INSTALLED {MARK} — 2 files updated')
    print(f'Backups: {backup_dir}')
    print('Next: npx tsc --noEmit -p . ; npm run dev')
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except PatchError as exc:
        print('ERROR — '+str(exc), file=sys.stderr)
        sys.exit(1)
