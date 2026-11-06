// FIGHT_ROYALE_VICTORY_HIGHLIGHTS_V1
// FIGHT_ROYALE_PRESENTATION_V1: visual-only character poses; combat stats are untouched.
import type { Pose, Vec3 } from "./kits";

/** Expressive, looping character-select and victory poses for the existing VRM/procedural rig. */
export function presentationPose(name: string, seconds: number, base: Pose, mode: "select" | "victory" = "select"): Pose {
  const t = seconds % (mode === "victory" ? 5.4 : 4.7);
  const pulse = Math.sin(t * 3.4);
  const sweep = Math.sin(t * 5.0);
  const lift = mode === "victory" ? 1.12 : 1;
  const copy = (v: Vec3): Vec3 => [v[0], v[1], v[2]];
  const p: Pose = {
    torso: copy(base.torso), head: copy(base.head),
    arm_r: copy(base.arm_r), hand_r: copy(base.hand_r),
    arm_l: copy(base.arm_l), hand_l: copy(base.hand_l),
    leg_l: copy(base.leg_l), leg_r: copy(base.leg_r),
    hips_y: base.hips_y, knee: base.knee ? [...base.knee] : [0, 0],
  };
  const flour = Math.min(1, Math.max(0, (t - 0.30) * 2.6));
  const hold = Math.min(1, Math.max(0, (t - 1.1) * 2.0));
  switch (name.toLowerCase()) {
    case "zarek": // Figure-eight double-glaive baton twirl, with steady planted feet.
      p.torso = [0.06, 0.17 + 0.18 * sweep, -0.06];
      p.head = [-0.04, -0.15, 0];
      p.arm_r = [-1.15 - 0.36 * pulse, 0.38 + 0.2 * sweep, -0.3];
      p.hand_r = [0.30, 0.12, -0.16];
      p.arm_l = [-0.85 + 0.22 * pulse, -0.18, 0.25];
      p.hand_l = [0.38, 0, 0.2];
      p.leg_l = [-0.23, 0, 0.18]; p.leg_r = [0.25, 0, -0.16];
      p.hips_y = -0.065; break;
    case "kira": // One-leg chamber into a held, high side kick.
      p.torso = [-0.11, -0.18, -0.11 - 0.09 * pulse];
      p.head = [0.03, 0.2, 0];
      p.arm_r = [-1.05, 0.12, -0.45]; p.hand_r = [0.50, 0, -0.16];
      p.arm_l = [-0.95, -0.14, 0.4]; p.hand_l = [0.52, 0, 0.14];
      p.leg_l = [-0.11, 0, 0.13];
      p.leg_r = [-0.32 - 0.58 * flour, 0.03, -0.20 - 0.70 * hold];
      p.knee = [0.12, 0.75 + 0.36 * (1 - hold)]; p.hips_y = -0.06; break;
    case "aster": // Sturdy shield-first heroic salute.
      p.torso = [0.06, -0.13, 0]; p.head = [-0.08, 0.11, 0];
      p.arm_r = [-2.38 - 0.15 * flour, 0.07, -0.12]; p.hand_r = [0.06, 0, 0];
      p.arm_l = [-1.05, -0.27, 0.24]; p.leg_l = [-0.18, 0, 0.08]; p.leg_r = [0.16, 0, -0.09]; p.hips_y = -0.085; break;
    case "vesper": // Crimson duel: sword salute with a sharp hip pivot.
      p.torso = [0.04, -0.29 + 0.16 * sweep, 0.07]; p.head = [-0.04, 0.17, 0];
      p.arm_r = [-1.95 - 0.25 * pulse, 0.41, -0.37]; p.hand_r = [0.1, 0, 0.22];
      p.arm_l = [-0.87, -0.34, 0.35]; p.leg_l = [-0.23, 0, 0.13]; p.leg_r = [0.3, 0, -0.18]; break;
    case "garrick": // Greatsword heft, grounded shoulders, slow victory raise.
      p.torso = [0.22, 0.17, -0.03]; p.head = [-0.09, -0.06, 0];
      p.arm_r = [-1.60 - 0.4 * flour, 0.03, -0.46]; p.hand_r = [0.25, 0, 0];
      p.arm_l = [-1.15, 0.1, 0.38]; p.hips_y = -0.15;
      p.leg_l = [-0.3, 0, 0.13]; p.leg_r = [0.35, 0, -0.13]; break;
    case "kaede": // Iaido, blade rises from a low draw.
      p.torso = [0.09, -0.25 + 0.1 * sweep, 0]; p.head = [0, 0.1, 0];
      p.arm_r = [-0.65 - 1.0 * flour, 0.42, -0.18]; p.hand_r = [0.35, 0, 0];
      p.arm_l = [-0.45, -0.5, 0.35]; p.leg_l = [-0.25, 0, 0.1]; p.leg_r = [0.24, 0, -0.1]; break;
    case "ember": // Fire sorceress summons a flame overhead.
      p.torso = [0.08, -0.15, 0.08]; p.head = [-0.17, 0.05, 0];
      p.arm_r = [-2.4 + 0.11 * pulse, 0.16, -0.16]; p.hand_r = [0.12, 0, 0.22];
      p.arm_l = [-1.42, -0.3, 0.38]; p.hand_l = [0.06, 0.3, 0]; break;
    case "marina": // Elegant water spiral / staff sweep.
      p.torso = [0.08, -0.28 + 0.1 * sweep, -0.08];
      p.arm_r = [-1.75 - 0.2 * pulse, 0.45, -0.36]; p.arm_l = [-1.2, -0.3, 0.5];
      p.head = [-0.06, 0.2, 0]; p.leg_l = [-0.2, 0, 0.1]; p.leg_r = [0.22, 0, -0.1]; break;
    case "nyx": // Crossed daggers, then one blade whips high.
      p.torso = [0.24, -0.35 + 0.12 * sweep, 0.08]; p.head = [0, 0.2, 0];
      p.arm_r = [-1.9 - 0.23 * pulse, 0.48, -0.22];
      p.arm_l = [-1.25, -0.6, 0.14]; p.leg_l = [-0.4, 0, 0.1]; p.leg_r = [0.32, 0, -0.1]; p.hips_y = -0.12; break;
    case "rook": // Boxer's one-two, fist raised at the end.
      p.torso = [0.19, 0.18 + 0.1 * sweep, 0.03];
      p.arm_r = [-1.22 - 0.48 * flour, 0.27, -0.42]; p.hand_r = [0.5, 0, -0.08];
      p.arm_l = [-1.33, -0.35, 0.48]; p.hand_l = [0.5, 0, 0.08]; p.hips_y = -0.14; break;
    case "gale": // Wind fighter: stylish low-to-high rising fist.
      p.torso = [0.07, -0.26 + 0.11 * sweep, 0.12];
      p.arm_r = [-2.5 + 0.3 * pulse, 0.23, -0.36];
      p.arm_l = [-1.14, -0.2, 0.34]; p.leg_r = [0.13, 0, -0.25]; break;
    case "bob": // Showman's explosive flourish, both arms wide.
      p.torso = [-0.04, -0.12 + 0.14 * sweep, 0.04]; p.head = [-0.13, 0.05, 0.07];
      p.arm_r = [-1.1 - 0.28 * pulse, 0.08, -1.1];
      p.arm_l = [-1.1 + 0.28 * pulse, -0.08, 1.1]; break;
    case "raven": // Witch's staff diagonal flourish, open casting palm.
      p.torso = [0.08, -0.22 + 0.09 * sweep, -0.05];
      p.arm_r = [-2.16 + 0.23 * pulse, 0.36, -0.25];
      p.arm_l = [-1.52, -0.4, 0.66]; p.hand_l = [0.12, 0.22, 0]; p.head = [-0.1, 0.12, 0]; break;
    case "ash": // Archer's precise draw, then release salute.
      p.torso = [0.15, -0.44 + 0.11 * sweep, 0.01];
      p.arm_r = [-1.36, 0.76, -0.28]; p.hand_r = [0.45, 0.15, 0];
      p.arm_l = [-1.2, -0.6, 0.48]; p.head = [-0.05, 0.25, 0]; break;
    case "veyr": // Dual sickles crossed, stalks into a predatory silhouette.
      p.torso = [0.35, 0.12 + 0.14 * sweep, -0.08]; p.head = [-0.05, -0.18, 0.04];
      p.arm_r = [-1.26, 0.32, -0.7]; p.arm_l = [-1.3, -0.28, 0.66];
      p.hips_y = -0.18; p.leg_l = [-0.35, 0, 0.13]; p.leg_r = [0.27, 0, -0.13]; break;
    case "kaizen": // Chainblade spin / shoulder flourish.
      p.torso = [0.15, 0.22 + 0.1 * sweep, 0]; p.head = [-0.05, -0.12, 0];
      p.arm_r = [-1.53 - 0.36 * pulse, 0.38, -0.42]; p.hand_r = [0.32, 0, -0.17];
      p.arm_l = [-0.95, -0.16, 0.47]; p.hips_y = -0.1; break;
    default: // Future characters retain a hero salute until they receive a bespoke pose.
      p.torso = [0.09, 0.1 * sweep, 0]; p.arm_r = [-2.1, 0.2, -0.2];
      p.arm_l = [-0.8, 0, 0.4]; break;
  }
  // Short celebratory lift on victory, without changing positions or collision shapes.
  if (mode === "victory") {
    p.arm_r[0] -= 0.14 * lift * Math.sin(Math.min(t, 1.5) * 1.9);
    p.head[0] -= 0.08;
    p.torso[1] += 0.10 * Math.sin(Math.min(1, t / 1.1) * 1.6);
  }
  return p;
}
