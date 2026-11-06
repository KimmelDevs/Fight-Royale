#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import argparse, shutil, tempfile, os, sys

class PatchError(RuntimeError):
    pass

def one(text, old, new, tag):
    c = text.count(old)
    if c != 1:
        raise PatchError(f"{tag}: expected one code anchor, found {c}")
    return text.replace(old, new, 1)

def root_at(spec: str | None) -> Path:
    p = Path(spec).expanduser().resolve() if spec else Path.cwd()
    for q in (p, p / 'web'):
        if (q / 'src/game/model.ts').is_file() and (q / 'src/game/roster.ts').is_file():
            return q
    raise PatchError('Fight Royale web folder not found. Run this in the web folder or pass the web path.')

def backup_write(root: Path, rel: str, data: bytes):
    backup = root / '.nesa_installer_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True, exist_ok=False)
    src = root / rel
    if src.exists():
        dst = backup / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    with tempfile.NamedTemporaryFile(dir=src.parent, delete=False) as tf:
        tf.write(data)
        temp = Path(tf.name)
    os.replace(temp, src)
    print('[OK] Backup:', backup)

OLD = '''    if (this.kit === "hammer") {
      this.torso.rotation.x += 0.09 + 0.12 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.045 * moving;
      this.head.rotation.x -= 0.06;
      this.hips.position.y -= 0.035 + moving * 0.014;
      this.leg_l.rotation.x *= 0.79;
      this.leg_r.rotation.x *= 0.79;
    }
'''

NEW = '''    if (this.kit === "hammer") {
      // NESA_NO_FOOT_HEAVINESS_V1:
      // keep the burden in her upper body, not in dragging heavy feet.
      this.torso.rotation.x += 0.08 + 0.10 * moving;
      this.torso.rotation.z += Math.sin(this.walkPhase * 0.5) * 0.04 * moving;
      this.head.rotation.x -= 0.05;
      this.hips.position.y -= 0.012 + moving * 0.004;
      // Let the legs move more naturally; the struggle should read in shoulders / arms.
      this.leg_l.rotation.x *= 0.95;
      this.leg_r.rotation.x *= 0.95;
      this.arm_l.rotation.x -= 0.06 + 0.03 * moving;
      this.arm_r.rotation.x += 0.04 + 0.02 * moving;
      this.arm_l.rotation.z -= 0.06;
      this.arm_r.rotation.z += 0.04;
    }
'''

def main():
    ap = argparse.ArgumentParser(description='Remove foot-heaviness from Nesa hammer walk')
    ap.add_argument('project', nargs='?', help='Fight Royale web folder')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    root = root_at(args.project)
    print('Fight Royale web project:', root)
    rel = 'src/game/model.ts'
    path = root / rel
    text = path.read_text(encoding='utf-8')
    if 'NESA_NO_FOOT_HEAVINESS_V1' in text:
        print('[OK] Nesa foot-heaviness patch already installed.')
        return
    new = one(text, OLD, NEW, 'hammer gait block')
    if args.check:
        print('[CHECK] Patch can be applied.')
        return
    backup_write(root, rel, new.encode('utf-8'))
    print('[DONE] Nesa now keeps the heavy feel in her upper body instead of her feet.')
    print('Run: npx tsc --noEmit -p .  and npm run dev')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('INSTALL FAILED:', exc)
        sys.exit(1)
