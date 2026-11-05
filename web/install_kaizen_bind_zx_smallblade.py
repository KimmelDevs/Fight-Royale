#!/usr/bin/env python3
"""Kaizen V6: Z/X bound follow-ups + smaller blade, preserves V5 spinning guard.
Install AFTER Kaizen/Zarek V4 Exact-Source Fix and Kaizen Weapon/Guard V5.
Run in the fight-royale/web folder: py install_kaizen_bind_zx_smallblade.py
"""
from pathlib import Path
import base64
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parent
STAMP = datetime.now().strftime('%Y%m%d-%H%M%S')
TARGETS = {
    'src/game/fighter.ts': None,
    'src/game/game.ts': None,
    'src/game/model.ts': None,
    'src/ui/GameView.tsx': None,
}
MARKER = 'KAIZEN_BIND_ZX_V6'


def exact(src, old, new, label):
    n=src.count(old)
    if n!=1:
        raise RuntimeError(f'Preflight failed: {label}: expected anchor once, found {n}. No files changed.')
    return src.replace(old,new,1)


def fighter(src):
    src=exact(src,
'''      const dir = this.chainRelativeDirection();
      if (dir === "neutral") this.chainChoiceArmed = true;
      else if (this.chainChoiceArmed && (dir === "forward" || dir === "backward")) {
        const kind = this.chainBindKind;
        this.onChainBindResolve(this, dir, kind as "x" | "v");
        this.releaseChainBind();
      }
''',
'''      // KAIZEN_BIND_ZX_V6: press Z to chase/launch, X to pull/throw.
      // Wait for a new skill-key press, so the original cast never auto-resolves.
      const choice = this.intent.skill;
      if (!choice) this.chainChoiceArmed = true;
      else if (this.chainChoiceArmed && (choice === "z" || choice === "x")) {
        const kind = this.chainBindKind;
        this.onChainBindResolve(this, choice === "z" ? "forward" : "backward", kind as "x" | "v");
        this.releaseChainBind();
      }
''', 'fighter.ts chain bind input')
    src=exact(src,'    // During a chain bind, WASD chooses the follow-up; skill keys are locked.',
              '    // While bound, Z/X are handled in update() before readSkill(); other skills are locked.', 'fighter.ts comment')
    src=exact(src,
          'this.chainBindTarget ? +this.chainBindTarget.chest().z.toFixed(2) : null];',
          'this.chainBindTarget ? +this.chainBindTarget.chest().z.toFixed(2) : null, +this.chainBindT.toFixed(2)];',
          'fighter.ts network snapshot')
    src=exact(src,
'''      this.model.chainBindTargetWorld = s.length >= 37 && s[34] !== null
        ? new THREE.Vector3(s[34], s[35], s[36]) : null;
''',
'''      this.model.chainBindTargetWorld = s.length >= 37 && s[34] !== null
        ? new THREE.Vector3(s[34], s[35], s[36]) : null;
      this.chainBindT = s[37] ?? 0; // KAIZEN_BIND_ZX_V6: remote HUD follow-ups
''', 'fighter.ts snapshot reader')
    return src


def model(src):
    src=exact(src,
'''    daggerGeo.translate(0, 0, -0.006);
    mesh(this.chainBlade, daggerGeo, bright);
''',
'''    daggerGeo.translate(0, 0, -0.006);
    // KAIZEN_BIND_ZX_V6: resize only the blade head. Keep the chain, grip and guard as V5.
    daggerGeo.translate(0, -0.214, 0);
    daggerGeo.scale(0.72, 0.72, 1);
    daggerGeo.translate(0, 0.214, 0);
    mesh(this.chainBlade, daggerGeo, bright);
''', 'model.ts blade geometry')
    src=exact(src,
'''    ridgeGeo.translate(0, 0, 0.010);
    mesh(this.chainBlade, ridgeGeo, dark);
''',
'''    ridgeGeo.translate(0, 0, 0.010);
    ridgeGeo.translate(0, -0.214, 0);
    ridgeGeo.scale(0.72, 0.72, 1);
    ridgeGeo.translate(0, 0.214, 0);
    mesh(this.chainBlade, ridgeGeo, dark);
''', 'model.ts ridge')
    src=exact(src,
'''    mesh(this.chainBlade, new THREE.TubeGeometry(edgePath, 22, 0.0035, 4, false), bright);
''',
'''    const edgeGeo = new THREE.TubeGeometry(edgePath, 22, 0.0035, 4, false);
    edgeGeo.translate(0, -0.214, 0);
    edgeGeo.scale(0.72, 0.72, 1);
    edgeGeo.translate(0, 0.214, 0);
    mesh(this.chainBlade, edgeGeo, bright);
''', 'model.ts edge highlight')
    src=exact(src,
'''    this.bladeTip = pivot(this.chainBlade, [-0.10, 0.72, 0]);
''',
'''    this.bladeTip = pivot(this.chainBlade, [-0.072, 0.578, 0]);
''', 'model.ts scaled blade tip')
    return src


def game(src):
    src=exact(src,
        'clashMomentum: f.clashMomentum });',
        'clashMomentum: f.clashMomentum, chainBindT: f.chainBindT }); // KAIZEN_BIND_ZX_V6',
        'game.ts HUD info')
    src=exact(src,
'''        const a = !me.onGround && me.attacks[k + "_air"] ? me.attacks[k + "_air"] : me.attacks[k];
        // During Blood Festival all special skills are locked, regardless of remaining cooldown.
''',
'''        const a = !me.onGround && me.attacks[k + "_air"] ? me.attacks[k + "_air"] : me.attacks[k];
        // KAIZEN_BIND_ZX_V6: bound follow-ups have no extra cooldown and replace Z/X icons.
        if (me.kit === "chainblade" && me.chainBindT > 0 && (k === "z" || k === "x"))
          return { key: k, id: k === "z" ? "forward" : "backward", name: k === "z" ? "Forward" : "Backward", cd: 0, max: 1 };
        // During Blood Festival all special skills are locked, regardless of remaining cooldown.
''', 'game.ts bind skill display')
    return src


def view(src):
    src=exact(src,
'''                  <Icon src={skillIcon(hud.kit, hud.element, s.id)} alt={s.name} size={60} />
''',
'''                  <Icon src={hud.kit === "chainblade" && (hud.me?.chainBindT ?? 0) > 0 &&
                    (s.key === "z" || s.key === "x")
                      ? `/icons/skills/kaizen-${s.key === "z" ? "forward" : "backward"}.webp`
                      : skillIcon(hud.kit, hud.element, s.id)} alt={s.name} size={60} /> {/* KAIZEN_BIND_ZX_V6 */}
''', 'GameView.tsx bind icons')
    return src


def main():
    patchers = {'src/game/fighter.ts':fighter, 'src/game/model.ts':model,
                'src/game/game.ts':game, 'src/ui/GameView.tsx':view}
    original = {}
    updated = {}
    for name,patch in patchers.items():
        p=ROOT/name
        if not p.is_file(): raise RuntimeError(f'Missing {name}; run this from web/ folder.')
        value=p.read_text(encoding='utf-8')
        if MARKER in value:
            original[name]=value; updated[name]=value
            continue
        original[name]=value
        updated[name]=patch(value)
    count=sum(updated[k]!=original[k] for k in patchers)
    if count not in (0,len(patchers)):
        raise RuntimeError('Some V6 files were already patched and others were not. No changes made; inspect your files.')
    files = {
        'kaizen-forward.webp': base64.b64decode(FORWARD_WEBP),
        'kaizen-backward.webp': base64.b64decode(BACKWARD_WEBP)
    }
    # All changes are computed first. Backups written before edits.
    if count:
        for name in updated:
            p=ROOT/name
            backup=p.with_name(p.name+f'.kaizen-v6-backup-{STAMP}')
            shutil.copy2(p,backup)
        for name,value in updated.items():
            (ROOT/name).write_text(value,encoding='utf-8')
            print('PATCH',name)
    else: print('Kaizen V6 code is already installed; checking icons.')
    out=ROOT/'public/icons/skills'
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        (out/name).write_bytes(data)
        print('ICON',out/name)
    print('DONE: Z=forward, X=backward while bound; forked blade head 28% smaller; V5 guard unchanged.')
    print('Run: npx tsc --noEmit && npm run dev')

FORWARD_WEBP = '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'
BACKWARD_WEBP = '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'

if __name__ == '__main__':
    main()
