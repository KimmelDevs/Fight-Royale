#!/usr/bin/env python3
'''Fight Royale: Signature Poses V2 — 16-character presentation-only upgrade.

Requires the earlier Victory Animations & Match Highlights update.
Usage: python Install_Signature_Poses_V2.py [project_directory] [--check]
'''
import argparse
import base64
import os
import shutil
import sys
import zlib
from datetime import datetime
from pathlib import Path

TAG = 'FIGHT_ROYALE_SIGNATURE_POSES_V2'
PREV = 'FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1'
POSE_DATA = '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'

class PatchError(Exception):
    pass

def one(src: str, old: str, new: str, label: str) -> str:
    n = src.count(old)
    if n != 1:
        raise PatchError(f'{label}: expected 1 code location, found {n}. Nothing changed.')
    return src.replace(old,new,1)

def patch_preview(src):
    old='''      this.model.glaivePose = this.lookName.toLowerCase() === "zarek" ? "show_baton" : "idle";
      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt, 9);'''
    new='''      // Distinct showcase timing, independent of live combat/skill logic.
      const phase = this.mode === "victory" ? this.poseT : this.poseT % 6.2;
      const who = this.lookName.toLowerCase();
      this.model.presentationT = phase;
      this.model.presentationMode = this.mode;
      this.model.glaivePose = who === "zarek" ? "show_baton" : "idle";
      // Kaizen: a controlled chain orbit, not an unrelated giant VFX circle.
      this.model.chainPose = who === "kaizen" && phase >= 0.55 && phase <= 2.30 ? "cbz_w" : "idle";
      // Ash: nock and pull a real bow string, then release at the flourish.
      this.model.draw = who === "ash" && phase >= 0.55 && phase < 1.35
        ? Math.min(1, (phase - 0.55) / 0.32) : 0;
      this.model.blend(presentationPose(this.lookName, this.poseT, this.poses.idle, this.mode), dt, 11);'''
    return '// '+TAG+'\n'+one(src,old,new,'selection preview choreography')

def patch_model(src):
    src=one(src,'  glaivePose = "idle"; // ZAREK_GLAIVE_CHOREO_V2: current attack key from the fighter',
        '''  glaivePose = "idle"; // ZAREK_GLAIVE_CHOREO_V2: current attack key from the fighter
  // Only used by presentation visuals; combat abilities, reach and momentum untouched.
  presentationT = 0;
  presentationMode: "select" | "victory" = "select";''','model presentation clock')
    old='''      // Show-only double-glaive baton spin, rotating about an axis perpendicular to the pole.
      if (this.glaivePose === "show_baton") {
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), this.t * 9.5));
      }'''
    new='''      // Choreographed Zarek baton flourish: two smooth rotations, then a readable hold.
      // Never used by an attack; the visual's weapon mount still follows both hands.
      if (this.glaivePose === "show_baton") {
        const phase = this.presentationMode === "select" ? this.presentationT % 6.2 : this.presentationT;
        const turn = THREE.MathUtils.smoothstep(phase, 0.55, 1.53) * (Math.PI * 4)
          + THREE.MathUtils.smoothstep(phase, 1.53, 2.29) * (Math.PI * 2)
          + (this.presentationMode === "select"
            ? THREE.MathUtils.smoothstep(phase, 4.19, 5.36) * (Math.PI * 2) : 0);
        q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), turn));
      }'''
    return '// '+TAG+'\n'+one(src,old,new,'Zarek presentation-only weapon spin')

def patch_fighter(src):
    old='    this.model.chainPose = this.kit === "chainblade" ? this.poseName : "idle";'
    if src.count(old) != 2:
        raise PatchError(f'Kaizen fighter rigs: expected 2 code locations, found {src.count(old)}.')
    new='''    this.model.chainPose = this.kit === "chainblade"
      ? (this.state === S.WIN && this.stateT >= 0.55 && this.stateT <= 2.30 ? "cbz_w" : this.poseName)
      : "idle";'''
    src=src.replace(old,new)
    old='    this.model.glaivePose = this.kit === "glaive" ? (this.state === S.WIN ? "show_baton" : this.poseName) : "idle";'
    if src.count(old) != 2:
        raise PatchError(f'Zarek fighter rigs: expected 2 code locations, found {src.count(old)}.')
    src=src.replace(old,'''    this.model.presentationT = this.stateT;
    this.model.presentationMode = "victory";
'''+old)
    old='''    const drawing = this.poseName === "bow_w" || this.poseName === "rain_w" || this.poseName === "charge";
    this.model.draw = drawing ? Math.min(this.model.draw + dt * 8, 1) : 0;'''
    new='''    if (this.state === S.WIN) {
      // Show-off bow draw on the victory animation, with real string/arrow motion.
      this.model.draw = this.stateT >= 0.55 && this.stateT < 1.35
        ? Math.min(1, (this.stateT - 0.55) / 0.32) : 0;
      return;
    }
    const drawing = this.poseName === "bow_w" || this.poseName === "rain_w" || this.poseName === "charge";
    this.model.draw = drawing ? Math.min(this.model.draw + dt * 8, 1) : 0;'''
    return '// '+TAG+'\n'+one(src,old,new,'Ash victory bow string')

def root_choose(folder):
    if folder:
        return Path(folder).expanduser().resolve()
    try:
        import tkinter as tk
        from tkinter import filedialog
        app=tk.Tk();app.withdraw();app.attributes('-topmost',True)
        p=filedialog.askdirectory(title='Fight Royale game project folder (contains src)')
        app.destroy()
        if p:return Path(p).resolve()
    except Exception:
        pass
    return Path(input('Project folder (containing src): ').strip().strip('"')).expanduser().resolve()

def main():
    parser=argparse.ArgumentParser(description='Install unique select/victory poses for all 16 Fight Royale fighters')
    parser.add_argument('folder',nargs='?',help='Fight Royale project folder')
    parser.add_argument('--check',action='store_true',help='Validate compatibility without changing files')
    args=parser.parse_args()
    root=root_choose(args.folder)
    targets={
        Path('src/game/presentation.ts'): lambda _: zlib.decompress(base64.b64decode(POSE_DATA)).decode('utf-8'),
        Path('src/game/preview.ts'):patch_preview,
        Path('src/game/model.ts'):patch_model,
        Path('src/game/fighter.ts'):patch_fighter,
    }
    changed={}
    for rel, patch in targets.items():
        p=root / rel
        if not p.is_file():raise PatchError(f'Cannot find {rel}. Select the project root, not src or scripts.')
        original=p.read_text(encoding='utf-8-sig')
        if TAG in original:continue
        if PREV not in original:
            raise PatchError(f'{rel} is missing the Victory Animations & Match Highlights update. Install that update first; no files changed.')
        updated=patch(original)
        if updated==original:raise PatchError(f'Unexpected unchanged result for {rel}')
        changed[rel]=(original,updated)
    if not changed:
        print('Signature Poses V2 is already installed. No changes needed.')
        return 0
    if len(changed)!=len(targets):
        raise PatchError('Only some files have the V2 update. This installer will not mix incompatible versions.')
    if args.check:
        print('Compatibility check PASSED. Would update:')
        for rel in changed:print('  '+str(rel))
        return 0
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    backup=root / '.signature_pose_backups' / stamp
    backup.mkdir(parents=True,exist_ok=True)
    completed=[]
    try:
        # Make the complete backup set before editing a single original.
        for rel in changed:
            b=backup / rel
            b.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/rel,b)
        for rel,(_,new) in changed.items():
            dest=root/rel
            temp=dest.with_name(dest.name+'.pose_v2_installing')
            temp.write_text(new,encoding='utf-8',newline='')
            os.replace(temp,dest)
            completed.append(rel)
    except Exception:
        for rel in reversed(completed):
            shutil.copy2(backup/rel,root/rel)
        raise
    print('SUCCESS! Signature Poses V2 installed for all 16 characters.')
    print('Updated: '+', '.join(str(r) for r in changed))
    print('Backups: '+str(backup))
    print('Restart your dev server to see the selection and victory animations.')
    print('No combat animation states, damage, hitboxes, cooldowns or skill balance changed.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (PatchError,OSError,UnicodeError) as e:
        print('Installation stopped safely: '+str(e),file=sys.stderr)
        sys.exit(1)
