#!/usr/bin/env python3
"""Fight Royale: Raigo V6 short axe grip + counter-loop fix + Marina Ward nerf.

From your `web` folder:
    python fix_raigo_axe_handle_parry_marina.py --dry-run
    python fix_raigo_axe_handle_parry_marina.py
    npx tsc --noEmit -p .

No third-party Python dependencies. Preserves Zephyr's V6 +15% staff size,
Raigo's V6 chain length / thin links, and combat hitboxes.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys
import tempfile

MARK = 'RAIGO_V6_AXE_GRIP_PARRY_WARD_FIX_20261109'


class PatchError(Exception):
    pass


def swap(src: str, old: str, new: str, desc: str, *, optional_done=False) -> str:
    count = src.count(old)
    if count == 1:
        return src.replace(old, new, 1)
    if count == 0 and optional_done and new in src:
        return src
    raise PatchError(f'{desc}: expected exactly one source anchor, found {count}. No source files changed.')


def patch_model(s: str) -> str:
    if 'RAIGO_IRON_BASTION_V6' not in s or 'RAIGO_V6_CHAIN_LENGTH' not in s:
        raise PatchError('model.ts: Raigo V6 weapon code not found. Run Raigo V6 first.')
    if 'ZEPHYR_TRISTAFF_SIZE_V24.globalScale * 1.15' not in s:
        raise PatchError('model.ts: expected Zephyr V6 +15% visual scale not found; stop to avoid changing incompatible build.')
    if 'torus(.016875,.0309375)' not in s:
        raise PatchError('model.ts: Raigo V6 25%-thinner chain geometry is not present.')

    s = swap(s,
        '  private raigoAxeAttach: THREE.Object3D | null = null;',
        '  private raigoAxeAttach: THREE.Object3D | null = null;\n'
        '  // RAIGO_AXE_GRIP_FIX: real grip point on the short forged axe handle.\n'
        '  private raigoAxeGrip: THREE.Object3D | null = null;',
        'axe grip field')

    s = swap(s,
        '''    // Thin forged socket connects the head directly to the very first chain link.
    mesh(head,cyl(.067,.075,.22,12),dark,[-.015,-.14,0]);
    mesh(head,torus(.054,.077),bronze,[-.015,-.235,0],[PI/2,0,0]);''',
        '''    // RAIGO_AXE_GRIP_FIX: a SHORT functional one-hand axe handle.
    // Handle is part of the .75-scaled head; NO second disconnected weapon.
    // Local Y is the grip axis; the chain starts at the lower butt ring.
    mesh(head,cyl(.058,.065,.15,12),bronze,[-.015,-.15,0]);
    mesh(head,cyl(.045,.052,.62,12),dark,[-.015,-.47,0]);
    mesh(head,cyl(.054,.054,.14,12),iron,[-.015,-.45,0]); // wrapped hand grip
    mesh(head,torus(.053,.069),bronze,[-.015,-.73,0],[PI/2,0,0]);''',
        'Raigo short axe handle geometry')

    s = swap(s,
        '''    this.raigoAxeAttach=pivot(head,[-.015,-.28,0]);
    this.bladeBase=pivot(head,[.08,.02,0]);''',
        '''    // 0.75 head scaling makes grip offset -0.375 in axe-root coordinates.
    // The axe root follows the right hand so the grip, NOT the head, is held.
    this.raigoAxeGrip=pivot(axe,[-.01125,-.375,0]);
    this.raigoAxeAttach=pivot(head,[-.015,-.79,0]); // chain connected to handle BUTT
    this.bladeBase=pivot(head,[.08,.02,0]);''',
        'Raigo physical chain attachment and grip')

    s = swap(s,
        '''    if(this.raigoGripMode===0) {
      if(t<.27) out.copy(a).lerp(r,t/.27);
      else if(t<.72) out.copy(r).lerp(l,(t-.27)/.45);
      else out.copy(l).lerp(b,(t-.72)/.28);
    } else {
      const g=this.raigoGripMode===3?l:r;
      const at=this.raigoGripMode===2?.17:this.raigoGripMode===3?.83:.50;
      if(t<at) out.copy(a).lerp(g,t/at);
      else out.copy(g).lerp(b,(t-at)/(1-at));
    }''',
        '''    if(this.raigoGripMode===0) {
      // Right hand holds the short AXE HAFT. Only LEFT hand guides the chain.
      // Never route the chain through the right fist holding the handle.
      if(t<.58) out.copy(a).lerp(l,t/.58);
      else out.copy(l).lerp(b,(t-.58)/.42);
    } else if(this.raigoGripMode===2) {
      // Right hand holds axe; ball is released to whip from the handle butt.
      out.copy(a).lerp(b,t);
    } else {
      // Free axe end: hold chain midpoint or near the iron ball.
      const g=this.raigoGripMode===3?l:r;
      const at=this.raigoGripMode===3?.83:.50;
      if(t<at) out.copy(a).lerp(g,t/at);
      else out.copy(g).lerp(b,(t-at)/(1-at));
    }''',
        'continuous chain follows axe-handle grip')

    s = swap(s,
        '''    if(!axe||!ball||!this.raigoAxeAttach||!this.raigoBallAttach) return;''',
        '''    if(!axe||!ball||!this.raigoAxeAttach||!this.raigoBallAttach||!this.raigoAxeGrip) return;''',
        'Raigo grip availability')

    # Preserve independent axe/ball inertia while the axe is RELEASED; only
    # parent/attach by a positional constraint while the right hand holds it.
    s = swap(s,
        '''    this.raigoAxeReady=this.raigoIntegrateEnd(axe,this.raigoAxeDesired,axeGrip,
      axeLimit,this.raigoAxeWorld,this.raigoAxeWorldPrev,this.raigoAxeReady,step,striking);
    this.raigoBallInitialized=this.raigoIntegrateEnd(ball,this.raigoDesired,ballGrip,
      ballLimit,this.raigoWorldTip,this.raigoWorldPrevTip,this.raigoBallInitialized,step,striking);
    // One more length constraint between the actual TWO endpoints.
    this.raigoDelta.subVectors(ball.position,axe.position);
    const apart=this.raigoDelta.length();
    if(apart>RAIGO_V6_CHAIN_LENGTH) {
      ball.position.copy(axe.position).addScaledVector(this.raigoDelta,RAIGO_V6_CHAIN_LENGTH/apart);
      ball.updateWorldMatrix(true,false);
      ball.getWorldPosition(this.raigoWorldTip);
    }
    // Axe end physically spins too, instead of being pinned to the fist.
    const spin=striking?Math.sin(beatP*Math.PI)*1.05:.10*Math.sin(this.t*.8);
    const aX=pose==="idle"?.2:pose==="block"?.8:1.3+spin;
    this.raigoQuat.setFromEuler(this.raigoEuler.set(aX,.2+sx*.32,cz*.26,"YXZ"));
    axe.quaternion.slerp(this.raigoQuat,1-Math.exp(-(striking?36:11)*step));
    ball.rotation.x+=step*(striking?8:.35);
    ball.rotation.z+=step*(striking?10:.28);''',
        '''    // RAIGO_AXE_GRIP_FIX: right hand grips the axe's short shaft in idle,
    // block, charge, and axe-led strikes. It is FREE on released-chain beats.
    const holdingAxe=this.raigoGripMode===0||this.raigoGripMode===2;
    const spin=striking?Math.sin(beatP*Math.PI)*1.05:.10*Math.sin(this.t*.8);
    const aX=holdingAxe ?
      (pose==="idle"?.045:pose==="block"?.14:pose==="charge"?-.17:.12+spin*.48) :
      1.3+spin;
    this.raigoQuat.setFromEuler(this.raigoEuler.set(aX,
      holdingAxe?.08+sx*(striking?.19:.04):.2+sx*.32,
      holdingAxe?cz*(striking?.16:.025):cz*.26,"YXZ"));
    axe.quaternion.slerp(this.raigoQuat,1-Math.exp(-(holdingAxe?32:11)*step));
    if(holdingAxe) {
      // Reused vector and exact grip alignment: local grip transformed by the
      // axe quaternion is offset from the RIGHT VRM hand. Axe head stands UP.
      this.raigoDelta.copy(this.raigoAxeGrip.position).applyQuaternion(axe.quaternion);
      axe.position.copy(this.raigoGripR).sub(this.raigoDelta);
      axe.updateWorldMatrix(true,false);
      axe.getWorldPosition(this.raigoAxeWorld);
      this.raigoAxeWorldPrev.copy(this.raigoAxeWorld);
      this.raigoAxeReady=true; // smooth hand-release into free axe physics
    } else {
      this.raigoAxeReady=this.raigoIntegrateEnd(axe,this.raigoAxeDesired,axeGrip,
        axeLimit,this.raigoAxeWorld,this.raigoAxeWorldPrev,this.raigoAxeReady,step,striking);
    }
    this.raigoBallInitialized=this.raigoIntegrateEnd(ball,this.raigoDesired,ballGrip,
      ballLimit,this.raigoWorldTip,this.raigoWorldPrevTip,this.raigoBallInitialized,step,striking);
    // Enforce tether length using TRUE chain endpoints (handle butt -> ball lug),
    // not the visual centres of the axe and spiked ball.
    this.raigoAxeAttach.getWorldPosition(this.raigoPathP);
    this.worldToLocal(this.raigoPathP);
    this.raigoBallAttach.getWorldPosition(this.raigoPathQ);
    this.worldToLocal(this.raigoPathQ);
    this.raigoDelta.subVectors(this.raigoPathQ,this.raigoPathP);
    const apart=this.raigoDelta.length();
    if(apart>RAIGO_V6_CHAIN_LENGTH) {
      ball.position.addScaledVector(this.raigoDelta,-(apart-RAIGO_V6_CHAIN_LENGTH)/apart);
      ball.updateWorldMatrix(true,false);
      ball.getWorldPosition(this.raigoWorldTip);
    }
    ball.rotation.x+=step*(striking?8:.35);
    ball.rotation.z+=step*(striking?10:.28);''',
        'Raigo upright hand-held axe and free-release physics')
    return s


def patch_combat(s: dict[str, str]) -> None:
    kits=s['kits.ts']
    kits=swap(kits,
        '    style: "parry_counter",\n    next: "",\n    no_parry: false,',
        '    style: "parry_counter",\n    next: "",\n    no_parry: true,',
        'non-recursive parry riposte',optional_done=True)
    kits=swap(kits,
        '    desc: "A fast one-hit riposte unlocked briefly after a successful parry.",',
        '    desc: "A fast one-hit riposte after a parry. Blockable and dodgeable, but cannot be parried again.",',
        'riposte description',optional_done=True)
    kits=swap(kits,
        't.z = a({ name: "Bubble Ward", desc: "A protective water bubble lasting 8 seconds in all modes.", cd: 13, type: "buff", mode: "ward", duration: 8,',
        't.z = a({ name: "Bubble Ward", desc: "A 5-second water bubble reducing incoming HP damage by 50%. Damage can still defeat Marina.", cd: 17, type: "buff", mode: "ward", duration: 5,',
        'Marina Bubble Ward 5s/17s',optional_done=True)
    s['kits.ts']=kits

    fighter=s['fighter.ts']
    fighter=swap(fighter,
        '    // V28: Marina\'s eight-second Water Ward absorbs 80% rather than all\n'
        '    // incoming HP damage. Other wards retain their previous full protection.',
        '    // PARRY_RIPOSTE_MARINA_WARD_FIX: Marina\'s shorter Water Ward absorbs 50%\n'
        '    // of incoming HP damage; other wards retain their original behavior.',
        'Marina Ward comment',optional_done=True)
    fighter=swap(fighter,
        '      this.lastDamage = Math.max(0, dmg * 0.20);',
        '      this.lastDamage = Math.max(0, dmg * 0.50);',
        'Marina actual damage reduction',optional_done=True)
    fighter=swap(fighter,
        '    const parryableContinuous = attacker instanceof Fighter && attacker.isContinuousComboActive() &&\n'
        '      a.style !== "nesa_heart_slam";',
        '    const parryableContinuous = attacker instanceof Fighter && attacker.isContinuousComboActive() &&\n'
        '      a.style !== "nesa_heart_slam" && a.style !== "parry_counter";',
        'continuous parry exception',optional_done=True)
    s['fighter.ts']=fighter

    game=s['game.ts']
    game=swap(game,
        '      // Marina Z is intentionally the full eight-second ward, even in PvP.',
        '      // Marina Z now uses the shorter 5-second ward in every mode; other wards unchanged.',
        'Marina Ward comment in game.ts',optional_done=True)
    s['game.ts']=game


def prepare(root:Path):
    names=['model.ts','kits.ts','fighter.ts','game.ts']
    paths={n:root/'src'/'game'/n for n in names}
    original={}
    data={}
    for n,p in paths.items():
        if not p.is_file(): raise PatchError(f'Missing file: {p}')
        raw=p.read_bytes()
        try: decoded=raw.decode('utf-8-sig')
        except UnicodeDecodeError as exc: raise PatchError(f'{p} is not UTF-8: {exc}') from exc
        if MARK in decoded: raise PatchError('Already installed; refusing to apply twice.')
        original[n]=raw
        data[n]=decoded.replace('\r\n','\n')
    data['model.ts']=patch_model(data['model.ts'])
    patch_combat(data)
    result={}
    for n in names:
        value='// '+MARK+'\n'+data[n]
        nl='\r\n' if b'\r\n' in original[n] else '\n'
        value=value.replace('\n',nl)
        result[n]=(b'\xef\xbb\xbf' if original[n].startswith(b'\xef\xbb\xbf') else b'')+value.encode('utf-8')
    return paths,original,result


def install(root:Path,dry:bool):
    paths,raw,updates=prepare(root)  # all anchors checked, no writes yet
    print('Raigo V6 axe handle + parry-loop fix + Marina Ward nerf')
    print(f'Project: {root}')
    print('Changes: upright short-handled axe, chain fixed to butt, free release moves;')
    print('         non-recursive parry riposte; Marina Ward 5s, 50%, 17s cooldown.')
    print('Preserved: 3.05 chain length, smaller Raigo links, Zephyr +15% visible staff.')
    if dry:
        print('DRY RUN PASSED — nothing written.')
        return
    folder=root/'scripts'/'backups'/('raigo_axe_grip_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(parents=True,exist_ok=False)
    staged={}; committed=[]
    try:
        for n,path in paths.items(): shutil.copy2(path,folder/n)
        for n,path in paths.items():
            with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.raigo_grip_',suffix='.tmp',delete=False) as f:
                f.write(updates[n]); staged[n]=Path(f.name)
        for n,path in paths.items():
            staged[n].replace(path); committed.append(n)
        print('Installed. Backup folder:',folder)
        print('Run: npx tsc --noEmit -p .')
    except Exception as exc:
        for n in reversed(committed):
            try: paths[n].write_bytes(raw[n])
            except OSError as err: print(f'ROLLBACK ERROR ({n}): {err}',file=sys.stderr)
        raise PatchError(f'Write failed; rollback attempted; backup retained: {exc}') from exc
    finally:
        for p in staged.values(): p.unlink(missing_ok=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent,
                    help='web folder (default: folder containing this script)')
    args=ap.parse_args()
    try: install(args.root.resolve(),args.dry_run)
    except (PatchError,OSError) as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 1
    return 0

if __name__=='__main__': raise SystemExit(main())
