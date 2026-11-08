#!/usr/bin/env python3
"""Nythera V3: Six-hit faster scythe chain + controlled crescent trails.
Run from Fight Royale web/ after Nythera V2; includes no VRM files.
Idempotent preflight, .bak backups, atomic replacement and rollback.
Changes only game/kits.ts, fighter.ts, model.ts, game.ts, fx.ts.
"""
from __future__ import annotations
import argparse, os, shutil, sys, tempfile
from pathlib import Path
from datetime import datetime

MARK = 'NYTHERA_SIX_HIT_REAPER_TRAILS_V3_20261108'
FILES = [f'src/game/{n}.ts' for n in ['kits','fighter','model','game','fx']]

def patch(original: dict[str, str]) -> dict[str, str]:
    t = original.copy()
    def one(path, old, new):
        count = t[path].count(old)
        if count != 1:
            raise ValueError(f'{path}: expected 1 matching anchor, found {count}: {old[:130]!r}')
        t[path] = t[path].replace(old, new, 1)
    K,F,M,G,X = FILES
    if 'NYTHERA_GRAVITY_REAPER_INSTALL_V1' not in t[K] or 'NYTHERA_REAPER_SCYTHE_HARVESTER_AI_V2' not in t[M]:
        raise ValueError('Install Nythera V1 and V2 first; the current source does not match.')
    one(K, '  scythe: { hp: 2200, guard: 76, move: 3.72, walk: 3.02, parry: 0.19, jump: 8.0 },',
        '  scythe: { hp: 2200, guard: 84, move: 3.72, walk: 3.02, parry: 0.19, jump: 8.0 },')
    one(K, '/** NYTHERA_GRAVITY_REAPER_INSTALL_V1 — four-beat curved basic string, one-handle scythe.',
        f'/** {MARK} — six-beat curved basic string, one-handle scythe.')
    one(K, '    l1: a({ name: "Open Crescent", wind: 0.14, active: 0.08, recover: 0.19,\n      dmg: 56, guard: 14, reach: 2.40, lunge: 2.2, knock: 0.55, stun: 0.15,',
        '    l1: a({ name: "Open Crescent", wind: 0.105, active: 0.08, recover: 0.145,\n      dmg: 60, guard: 14, reach: 2.40, lunge: 2.2, knock: 0.38, stun: 0.15,')
    one(K, '    l2: a({ name: "Reverse Veil", wind: 0.15, active: 0.08, recover: 0.20,\n      dmg: 60, guard: 15, reach: 2.42, lunge: 2.1, knock: 0.58, stun: 0.16,',
        '    l2: a({ name: "Reverse Veil", wind: 0.11, active: 0.08, recover: 0.15,\n      dmg: 64, guard: 15, reach: 2.42, lunge: 2.1, knock: 0.42, stun: 0.16,')
    one(K, '    l3: a({ name: "Sky Hook", wind: 0.17, active: 0.08, recover: 0.21,\n      dmg: 68, guard: 17, reach: 2.48, lunge: 2.3, knock: 0.8, stun: 0.18,',
        '    l3: a({ name: "Sky Hook", wind: 0.115, active: 0.08, recover: 0.17,\n      dmg: 70, guard: 17, reach: 2.48, lunge: 2.3, knock: 0.55, stun: 0.18,')
    one(K, '''    l4: a({ name: "Orbit Bloom", wind: 0.21, active: 0.11, recover: 0.36,
      dmg: 90, guard: 23, reach: 2.52, lunge: 2.4, knock: 2.5, stun: 0.32,
      style: "gravity_bloom", pose_w: "gr4_w", pose_s: "gr4_s" }),''',
        '''    // Nythera V3: the original heavy fourth hit becomes a flowing setup,
    // followed by a reverse hook and a committed crescent finisher.
    l4: a({ name: "Orbit Bloom", wind: 0.125, active: 0.10, recover: 0.18,
      dmg: 78, guard: 19, reach: 2.52, lunge: 2.4, knock: 0.58, stun: 0.19,
      style: "gravity_bloom", pose_w: "gr4_w", pose_s: "gr4_s", next: "l5" }),
    l5: a({ name: "Reversal Hook", wind: 0.13, active: 0.09, recover: 0.18,
      dmg: 78, guard: 20, reach: 2.54, lunge: 2.25, knock: 0.55, stun: 0.18,
      style: "gravity_crescent", pose_w: "gr5_w", pose_s: "gr5_s", next: "l6" }),
    l6: a({ name: "Eclipse Reap", wind: 0.17, active: 0.11, recover: 0.29,
      dmg: 108, guard: 28, reach: 2.56, lunge: 2.50, knock: 2.65, stun: 0.32,
      style: "gravity_bloom", pose_w: "gr6_w", pose_s: "gr6_s" }),''')
    one(K, '      cd: 7.0, wind: 0.23, active: 0.10, recover: 0.38,',
        '      cd: 7.0, wind: 0.20, active: 0.10, recover: 0.34,')
    one(K, '      cd: 10.0, wind: 0.29, active: 0.11, recover: 0.46,',
        '      cd: 10.0, wind: 0.25, active: 0.11, recover: 0.42,')

    # Dreadfall was ~27% slower than Moonfloat. V3 makes both readable but responsive.
    one(F, '      if (/^l[1-4]$/.test(id)) {\n        const speed = heavyGravity ? 1.13 : 0.89;',
        '      if (/^l[1-6]$/.test(id)) {\n        // NYTHERA_SIX_HIT_REAPER_TRAILS_V3_20261108: real attack timing, not pose-only speed.\n        const speed = heavyGravity ? 0.95 : 0.79;')
    one(F, '      this.kit === "hammer" ? "#ff53b9" : look.glow,\n      this.kit === "hammer" ? 0.25 : 0.16);',
        '      this.kit === "hammer" ? "#ff53b9" : this.kit === "scythe" ? "#b996ff" : look.glow,\n      this.kit === "hammer" ? 0.25 : this.kit === "scythe" ? 0.24 : 0.16);')
    one(F, '''          } else if (this.atkPhase === 0) { p = a.pose_w; sp = this.gravityMode === "heavy" ? 15 : 22; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = this.gravityMode === "heavy" ? 39 : 55; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.64) { p = a.pose_s; sp = 18; }
          else { p = "idle"; sp = 13; }''',
        '''          } else if (this.atkPhase === 0) { p = a.pose_w; sp = this.gravityMode === "heavy" ? 24 : 32; }
          else if (this.atkPhase === 1) { p = a.pose_s; sp = this.gravityMode === "heavy" ? 64 : 85; }
          else if (this.stateT < a.wind + a.active + a.recover * 0.72) { p = a.pose_s; sp = 30; }
          else { p = "idle"; sp = 23; }''')

    # V3 poses are inserted immediately before the existing scythe heavy pose.
    one(K, '''  grh_w: P([-0.22,-0.48,-0.08]''', '''  // V3 reaper chain: reverse hooked cut across the body, then a wide final reaping lunge.
  gr5_w: P([0.11,0.74,0.05],[-0.04,-0.43,0],[-1.36,0.91,0.12],[0.39,0,0.24],[-1.18,0.66,0.15],[0.27,0,-0.13],[-0.39,0,0.11],[0.41,0,-0.09],-0.12),
  gr5_s: P([0.23,-0.76,-0.07],[-0.11,0.47,0],[-1.56,-0.95,-0.13],[0.10,0,-0.43],[-1.41,-0.70,0.20],[0.10,0,-0.28],[-0.52,0,0.12],[0.46,0,-0.08],-0.16),
  gr6_w: P([-0.22,-0.90,0.04],[0.11,0.52,0],[-2.03,-1.05,-0.18],[0.46,0,-0.15],[-1.92,-0.81,0.16],[0.32,0,-0.11],[-0.62,0,0.15],[0.50,0,-0.11],-0.19),
  gr6_s: P([0.41,1.08,0.08],[-0.18,-0.60,0],[-0.70,1.10,-0.14],[0.07,0,0.54],[-0.89,0.95,0.17],[0.06,0,0.36],[-0.83,0,0.16],[0.59,0,-0.10],-0.23),
  grh_w: P([-0.22,-0.48,-0.08]''')
    one(M, '        grh_w: [2.20,-0.32,0.20], grh_s: [0.74,0.53,-0.12],',
        '        gr5_w: [1.15,0.73,0.38], gr5_s: [2.18,-0.79,-0.35],\n        gr6_w: [2.12,-0.80,0.27], gr6_s: [0.72,0.95,-0.42],\n        grh_w: [2.20,-0.32,0.20], grh_s: [0.74,0.53,-0.12],')
    one(M, '          gr4_s: 1, grz_s: 1, grc_s: 1,',
        '          gr4_s: 1, gr6_s: 1, grz_s: 1, grc_s: 1,')

    # One new network-replicated FX type; runs on host and guests.
    one(G, '      case "zenithFang": fx.zenithFang(v3(a[0]), v3(a[1]), a[2] ?? 0); break;',
        '      case "zenithFang": fx.zenithFang(v3(a[0]), v3(a[1]), a[2] ?? 0); break;\n      case "nytheraCrescent": fx.nytheraCrescent(v3(a[0]), a[1] ?? 0, a[2] ?? 0, a[3] ?? false); break;')
    one(G, '    this.fxp("slashes", tip, col);\n    this.fxp("flash", tip, light ? "#dbc7ff" : "#9d5cea", light ? 0.22 : 0.36, 0.12, 0.72);',
        '''    // NYTHERA_SIX_HIT_REAPER_TRAILS_V3_20261108 — blade-following ribbon,
    // clear side changes and deeper Dreadfall finishes. No expanded hitboxes.
    const basic = /^l[1-6]$/.test(a.id);
    if (basic || a.type === "melee") {
      const beat = basic ? Math.min(6, Math.max(1, Number(a.id.substring(1)))) : 3;
      this.fxp("nytheraCrescent", f.chest(), f.root.rotation.y, beat, !light);
      if (basic) this.snd(beat === 6 ? "swing_heavy" : "swing2", light ? 0.40 : 0.53);
    }
    this.fxp("slashes", tip, col);
    this.fxp("flash", tip, light ? "#dbc7ff" : "#9d5cea", light ? 0.25 : 0.37, 0.12, 0.75);''')
    one(G, '    if (a.heavy || a.id === "l4" || a.id === "x")',
        '    if (a.heavy || a.id === "l6" || a.id === "x")')

    one(X, '  slashes(pos: THREE.Vector3, color: string) {', '''  /** NYTHERA_SIX_HIT_REAPER_TRAILS_V3_20261108 — sharp, flowing crescent ribbon.
   * Purely visual; weapon collision remains the normal melee path.
   * Beat controls alternating direction / rise; heavier Dreadfall has a deeper purple wake.
   */
  nytheraCrescent(center: THREE.Vector3, yaw: number, beat = 1, heavy = false) {
    const duration = heavy ? 0.32 : 0.24;
    const segments = 28;
    const r = beat === 6 ? 1.13 : beat === 4 ? 0.95 : 0.82;
    const reversed = beat % 2 === 0;
    const yBias = beat === 3 ? 0.18 : beat === 5 ? -0.13 : 0;
    const geo = new THREE.BufferGeometry();
    const pos: number[] = [];
    const colors: number[] = [];
    const c1 = new THREE.Color(heavy ? "#793bd0" : "#a784ff");
    const c2 = new THREE.Color(heavy ? "#d8a5ff" : "#dcf8ff");
    for (let i = 0; i < segments; i++) {
      const verts: {x:number,y:number,z:number,c:THREE.Color}[] = [];
      for (let j=0; j<2; j++) {
        const u = (i+j)/segments;
        const theta = -1.35 + u*2.70;
        const x = (reversed ? -1 : 1) * Math.sin(theta)*r;
        const y = Math.cos(theta)*(r*0.58) + yBias + (beat === 2 ? u*0.35 : beat === 4 ? -u*0.22 : 0);
        const zz = 0.36 + 0.20 * Math.cos(theta);
        const width = 0.025 + 0.095 * Math.pow(Math.sin(Math.PI*u), 1.2);
        verts.push({x,y,z:zz,c:c2});
        verts.push({x,y:y-width,z:zz-0.025,c:c1});
      }
      const tri = [verts[0],verts[1],verts[2],verts[1],verts[3],verts[2]];
      for(const p of tri) {
        pos.push(p.x,p.y,p.z);
        colors.push(p.c.r,p.c.g,p.c.b);
      }
    }
    geo.setAttribute("position",new THREE.Float32BufferAttribute(pos,3));
    geo.setAttribute("color",new THREE.Float32BufferAttribute(colors,3));
    geo.computeVertexNormals();
    const mat = new THREE.MeshBasicMaterial({ vertexColors:true, transparent:true,
      opacity:heavy?0.86:0.78, blending:THREE.AdditiveBlending,
      side:THREE.DoubleSide,depthWrite:false });
    const mesh = new THREE.Mesh(geo,mat);
    (mesh as any).ownsMat = true;
    mesh.position.copy(center).add(new THREE.Vector3(0,0.02,0));
    mesh.rotation.y = yaw;
    mesh.frustumCulled = false;
    let time = 0;
    this.add(mesh,(dt)=>{
      time += dt;
      const u = Math.min(1,time/duration);
      mat.opacity = (heavy ? 0.86 : 0.78)*Math.pow(1-u,1.5);
      mesh.scale.setScalar(1 + 0.17*u);
      if (time >= duration) geo.dispose();
      return time < duration;
    });
  }

  slashes(pos: THREE.Vector3, color: string) {''')
    return t


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', nargs='?', default='.')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    root = Path(args.project).resolve()
    try:
        original = {f: (root/f).read_text(encoding='utf-8-sig') for f in FILES}
    except OSError as exc:
        sys.exit(f'ERROR: Missing game files. Run inside web/ or pass its path. {exc}')
    if MARK in original[FILES[0]]:
        print('Nythera V3 is already installed. No changes needed.')
        return
    try:
        updated = patch(original)
    except ValueError as exc:
        sys.exit(f'PREFLIGHT ERROR: {exc}. No files changed.')
    if args.dry_run:
        print('DRY RUN OK: Nythera V3 six-hit scythe combo + crescent trails compatible. No files changed.')
        return
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    backups = {}
    try:
        for name in FILES:
            p = root/name
            bak = p.with_name(p.name+f'.before_nythera_v3_{stamp}.bak')
            shutil.copy2(p,bak)
            backups[name]=bak
        for name in FILES:
            path=root/name
            fd,tmp=tempfile.mkstemp(prefix=f'.{path.name}.nytherav3.',suffix='.tmp',dir=path.parent)
            try:
                with os.fdopen(fd,'w',encoding='utf-8',newline='') as out:
                    out.write(updated[name])
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
            print('Updated:',name)
    except Exception as exc:
        for name,bak in backups.items():
            try: shutil.copy2(bak,root/name)
            except OSError: pass
        sys.exit(f'WRITE ERROR: {exc}. Automatic rollback attempted.')
    print('Nythera V3 installed. Six-hit chain, quicker scythe basic and Z/X, crescent ribbons + longer blade trail.')
    print('Run: npx tsc --noEmit -p . && npm run build')

if __name__=='__main__':
    main()
