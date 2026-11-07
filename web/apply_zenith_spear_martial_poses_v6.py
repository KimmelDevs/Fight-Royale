#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import shutil, sys

ROOT = Path.cwd()
CANDIDATES = [ROOT / 'game/kits.ts', ROOT / 'src/game/kits.ts']
KIT = next((p for p in CANDIDATES if p.is_file()), None)
if not KIT:
    sys.exit('Could not find game/kits.ts or src/game/kits.ts. Run this inside your web project root. No files changed.')

src = KIT.read_text(encoding='utf-8')
MARK = 'ZENITH_SPEAR_MARTIAL_POSES_V6_20261108'
if MARK in src:
    print('Zenith spear martial poses V6 already installed. No changes needed.')
    sys.exit(0)

start_anchor = '// ZENITH_SPEAR_ANIMATION_AUDIO_V2_20261108'
end_anchor = 'const CHAINBLADE: Record<string, Pose> = {'
if start_anchor not in src or end_anchor not in src:
    sys.exit('Expected Zenith pose block anchors not found in kits.ts. No files changed.')

start = src.index(start_anchor)
end = src.index(end_anchor, start)

new_block = '''// ZENITH_SPEAR_MARTIAL_POSES_V6_20261108 — spear-specific guards and thrust choreography
// inspired by traditional long-spear handling: rear hand near the hip, front hand guiding the shaft,
// long linear thrusts, lower stances, clearer javelin-like throw, and less double-glaive reading.
const ZENITH: Record<string, Pose> = {
  ...GLAIVE,
  // Neutral long-spear guard: rear hand near the hip, lead hand extended, spear line presented forward.
  idle: P([0.01,-0.12,0], [-0.01,0.10,0], [-0.92,-0.04,-0.30], [0.16,0,0.06], [-0.58,-0.62,0.20], [0.08,0,0.02], [-0.26,0,0.08], [0.30,0,-0.08], -0.07),
  // Middle guard / check: shaft braced diagonally across the body, ready to intercept or thrust.
  block: P([0.10,-0.05,0], [0.02,0.04,0], [-1.10,0.08,-0.28], [0.13,0,0.06], [-0.86,-0.50,0.26], [0.10,0,0.02], [-0.36,0,0.08], [0.40,0,-0.08], -0.09),

  // 1) Long straight thrust from rear-loaded guard.
  zn1_w: P([0.08,-0.36,0], [0,0.22,0], [-1.26,-0.26,-0.28], [0.24,0,0.06], [-0.72,-0.82,0.18], [0.10,0,0.02], [-0.34,0,0.08], [0.29,0,-0.07], -0.10),
  zn1_s: P([0.22,0.18,0], [0,-0.12,0], [-1.72,0.02,-0.22], [0.04,0,0.06], [-1.06,-0.58,0.18], [0.05,0,0.02], [-0.54,0,0.09], [0.43,0,-0.08], -0.13),

  // 2) Rising redirect into another front-blade thrust.
  zn2_w: P([0.12,0.28,0.02], [0,-0.22,0], [-1.03,0.32,-0.10], [0.20,0,0.14], [-0.60,-0.44,0.36], [0.08,0,0.02], [-0.23,0,0.09], [0.34,0,-0.07], -0.09),
  zn2_s: P([0.22,-0.14,0], [0,0.14,0], [-1.60,-0.10,-0.17], [0.05,0,0.10], [-1.05,-0.36,0.24], [0.06,0,0.02], [-0.45,0,0.10], [0.36,0,-0.09], -0.12),

  // 3) Compact retraction then horizontal spear-line drive.
  zn3_w: P([0.05,-0.28,-0.03], [0,0.20,0], [-0.98,-0.56,-0.34], [0.18,0,-0.04], [-0.62,-0.72,0.18], [0.10,0,0.02], [-0.33,0,0.11], [0.36,0,-0.07], -0.10),
  zn3_s: P([0.18,0.20,0], [0,-0.17,0], [-1.46,-0.18,-0.30], [0.04,0,-0.02], [-0.96,-0.64,0.20], [0.04,0,0.02], [-0.51,0,0.10], [0.42,0,-0.08], -0.13),

  // 4) Low spear cut / leg-level re-aim with front blade still leading.
  zn4_w: P([0.10,0.20,0], [0,-0.18,0], [-0.82,0.04,-0.36], [0.20,0,0.05], [-0.78,-0.36,0.28], [0.12,0,-0.02], [-0.27,0,0.10], [0.31,0,-0.07], -0.09),
  zn4_s: P([0.19,-0.18,0.03], [0,0.15,0], [-1.42,-0.20,-0.28], [0.04,0,0.05], [-1.08,-0.50,0.16], [0.05,0,-0.02], [-0.53,0,0.11], [0.45,0,-0.08], -0.13),

  // 5) Finisher: committed lunge with the rear hand driving through the shaft.
  zn5_w: P([-0.02,-0.46,0], [0.02,0.30,0], [-1.18,-0.42,-0.32], [0.30,0,0.03], [-0.86,-0.76,0.22], [0.13,0,0.02], [-0.50,0,0.12], [0.30,0,-0.08], -0.13),
  zn5_s: P([0.30,0.34,0], [-0.08,-0.18,0], [-1.86,-0.06,-0.30], [0.04,0,0.03], [-1.18,-0.66,0.20], [0.04,0,0.02], [-0.73,0,0.13], [0.52,0,-0.09], -0.18),

  // Charged attack: pop a summoned spear overhead, then drive the throwing arm forward.
  znh_w: P([-0.02,-0.14,0], [0.02,0.12,0], [-2.28,-0.04,-0.42], [0.14,0,0.04], [-0.62,-0.26,0.46], [0.12,0,0.02], [-0.18,0,0.08], [0.17,0,-0.08], -0.07),
  znh_s: P([0.26,0.08,0], [-0.06,-0.04,0], [-0.62,0.18,-0.12], [0.04,0,0.02], [-1.68,-0.18,0.14], [0.06,0,0.02], [-0.63,0,0.12], [0.46,0,-0.09], -0.14),

  // Z Rail Spear: clear javelin-like cockback and release, not a broad glaive slash.
  znz_w: P([0.02,-0.24,0], [0,0.18,0], [-2.02,-0.32,-0.58], [0.42,0,0.10], [-0.74,-0.24,0.34], [0.14,0,0.02], [-0.40,0,0.09], [0.34,0,-0.08], -0.12),
  znz_s: P([0.30,0.20,0], [-0.10,-0.10,0], [-0.60,0.02,-0.08], [0.04,0,0.02], [-1.76,-0.10,0.22], [0.08,0,0.02], [-0.67,0,0.10], [0.48,0,-0.10], -0.17),

  // X Barrage: fast spear-line pressure while still clearly using a long spear.
  znx_w: P([0.08,-0.22,0], [0,0.16,0], [-1.00,-0.30,-0.30], [0.22,0,0.06], [-0.68,-0.62,0.22], [0.10,0,0.02], [-0.40,0,0.09], [0.38,0,-0.08], -0.10),
  znx_s: P([0.18,0.10,0], [0,-0.06,0], [-1.42,-0.06,-0.24], [0.06,0,0.05], [-0.98,-0.44,0.20], [0.06,0,0.02], [-0.56,0,0.10], [0.42,0,-0.09], -0.12),

  // C Magnetic Dominion: open off-hand command gesture while the spear remains visually secondary.
  znc_w: P([0.04,-0.10,0], [0,0.08,0], [-0.50,-0.18,-0.74], [0.16,0,0.12], [-1.22,-0.32,0.12], [0.18,0,0.02], [-0.30,0,0.07], [0.31,0,-0.08], -0.06),
  znc_s: P([0.14,0.14,0], [0,-0.10,0], [-0.58,0.18,-0.92], [0.08,0,0.12], [-1.20,-0.02,0.16], [0.12,0,0.02], [-0.42,0,0.10], [0.38,0,-0.09], -0.08),

  // V Sovereign Arsenal: one arm high to command constructs, spear arm balanced low.
  znv_w: P([-0.08,-0.06,0], [0,0.08,0], [-2.36,-0.02,-0.30], [0.14,0,0.04], [-1.00,-0.42,0.26], [0.14,0,0.02], [-0.46,0,0.12], [0.43,0,-0.08], -0.10),
  znv_s: P([0.16,0.12,0], [0,-0.10,0], [-2.54,0.10,-0.22], [0.08,0,0.04], [-0.60,-0.12,0.20], [0.10,0,0.02], [-0.54,0,0.09], [0.49,0,-0.09], -0.10),
};

'''

new_src = src[:start] + new_block + src[end:]

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = KIT.with_name(KIT.name + f'.before_zenith_pose_v6_{stamp}.bak')
shutil.copy2(KIT, backup)
KIT.write_text(new_src, encoding='utf-8')
print(f'Updated: {KIT}')
print(f'Backup: {backup.name}')
print('Zenith V6 installed: spear-martial pose set with more authentic long-spear guards, thrusts, and throw posture.')
