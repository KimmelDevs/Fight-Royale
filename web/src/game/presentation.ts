// FIGHT_ROYALE_SIGNATURE_POSES_V2
// Presentation-only choreography for the 16-character roster.
// Rig-safe procedural posing: no imported animations or combat calculations.
import type { Pose, Vec3 } from "./kits";

type Beat = Partial<Pose>;
type Choreo = { ready: Beat; wind: Beat; move: Beat; hero: Beat; win: Beat; tempo?: number };
const C: Record<string, Choreo> = {
  aster: { // Massive armored shield wall -> one formal sword salute.
    ready: { torso: [0.13,-0.09,0], head: [0.02,0.04,0], arm_r: [-0.63,0.14,-0.25], arm_l: [-1.16,-0.1,0.31], leg_l: [-0.12,-0.12,0.22],leg_r:[0.18,0.09,-0.2],hips_y:-0.11,knee:[0.27,0.25] },
    wind: { torso:[0.20,-0.25,0.01],head:[0.05,0.17,0],arm_r:[-1.24,0.08,-0.30],arm_l:[-1.4,-0.3,0.14],hips_y:-0.15,knee:[0.38,0.32] },
    move: { torso:[-0.04,0.13,-0.02],head:[-0.13,0,0],arm_r:[-2.46,0.15,-0.20],hand_r:[0.13,0,0.08],arm_l:[-1.17,-0.11,0.23],hips_y:-0.08,knee:[0.22,0.19] },
    hero: { torso:[0.08,0.07,0],head:[-0.09,0.13,0],arm_r:[-2.05,0.15,-0.15],arm_l:[-1.27,-0.18,0.16],leg_l:[-0.08,-0.13,0.19],leg_r:[0.16,0.11,-0.18],hips_y:-0.105,knee:[0.24,0.23] },
    win: { torso:[-0.05,0.09,0],head:[-0.11,0.08,0],arm_r:[-2.48,0,-0.1],arm_l:[-1.19,-0.18,0.22],leg_l:[-0.12,-0.14,0.20],leg_r:[0.17,0.1,-0.18],hips_y:-0.10,knee:[0.21,0.23] },tempo:.77 },
  vesper: { // Elegant fencing invitation -> quick rapier-like flourish -> defiant salute.
    ready:{torso:[0.06,-0.26,0.09],head:[-0.05,0.2,0],arm_r:[-0.79,0.47,-0.43],arm_l:[-0.8,-0.27,0.43],leg_l:[-0.18,0,0.14],leg_r:[0.2,0,-0.15],hips_y:-0.035,knee:[.08,.13]},
    wind:{torso:[0.12,-0.59,0.12],head:[-0.08,0.30,0],arm_r:[-1.52,0.50,-0.33],hand_r:[0.10,0.2,0.22],arm_l:[-1.03,-0.3,.46],leg_l:[-0.32,0,.18],leg_r:[.28,0,-.16],hips_y:-.065},
    move:{torso:[-0.07,0.27,-0.08],head:[0,-0.12,0],arm_r:[-2.14,-0.19,-.23],hand_r:[-.18,0,.18],arm_l:[-.91,-.25,.33],leg_l:[-.38,0,.13],leg_r:[.18,0,-.12]},
    hero:{torso:[0.02,-0.24,.08],head:[-.02,.15,-.02],arm_r:[-1.8,.43,-.26],hand_r:[.18,0,.2],arm_l:[-.62,-.4,.50],leg_l:[-.2,0,.16],leg_r:[.3,0,-.2],hips_y:-.045},
    win:{torso:[-.03,-.28,.10],head:[-.13,.13,0],arm_r:[-2.34,.31,-.25],hand_r:[.1,.15,.15],arm_l:[-.65,-.31,.49],leg_l:[-.18,0,.15],leg_r:[.28,0,-.21],hips_y:-.04} },
  garrick: { // Greatsword weight lift, controlled stomp, silent titan finish.
    ready:{torso:[.23,.06,0],head:[-.07,-.03,0],arm_r:[-.85,.02,-.43],arm_l:[-.99,-.02,.38],leg_l:[-.16,-.14,.20],leg_r:[.20,.13,-.20],hips_y:-.14,knee:[.24,.25]},
    wind:{torso:[.36,-.27,.04],head:[.04,.17,0],arm_r:[-1.78,.18,-.48],arm_l:[-1.72,.15,.48],hips_y:-.2,knee:[.37,.34]},
    move:{torso:[.02,.30,-.06],head:[-.14,-.13,0],arm_r:[-2.55,-.04,-.23],hand_r:[.19,0,0],arm_l:[-1.65,.14,.36],hips_y:-.11,knee:[.21,.23]},
    hero:{torso:[.17,.06,0],head:[-.07,.04,0],arm_r:[-1.54,.11,-.38],arm_l:[-1.26,-.1,.4],leg_l:[-.2,-.14,.22],leg_r:[.25,.13,-.20],hips_y:-.15,knee:[.24,.26]},
    win:{torso:[.08,.05,0],head:[-.13,0,0],arm_r:[-2.47,.04,-.19],arm_l:[-1.9,-.01,.23],leg_l:[-.22,-.15,.22],leg_r:[.27,.12,-.22],hips_y:-.14,knee:[.20,.21]},tempo:.72 },
  kaede: { // Hand to hilt, razor-fast iaido sweep, perfectly still finishing stance.
    ready:{torso:[.04,-.23,.02],head:[.07,.09,-.02],arm_r:[-.54,.51,-.25],hand_r:[.3,0,-.12],arm_l:[-.62,-.36,.41],leg_l:[-.24,-.08,.13],leg_r:[.23,.07,-.13],hips_y:-.06,knee:[.22,.19]},
    wind:{torso:[.17,-.48,.02],head:[-.01,.22,.02],arm_r:[-.28,.65,-.22],hand_r:[.62,0,-.12],arm_l:[-.71,-.48,.5],hips_y:-.11,knee:[.32,.28]},
    move:{torso:[-.1,.52,-.06],head:[-.07,-.18,0],arm_r:[-2.25,-.15,-.25],hand_r:[-.30,.12,.03],arm_l:[-.96,-.25,.34],leg_l:[-.35,-.03,.13],leg_r:[.31,.07,-.16],hips_y:-.055},
    hero:{torso:[.09,-.19,0],head:[-.04,.11,0],arm_r:[-.83,.24,-.22],hand_r:[.21,0,-.08],arm_l:[-.53,-.43,.36],leg_l:[-.28,-.07,.15],leg_r:[.26,.08,-.13],hips_y:-.08,knee:[.16,.21]},
    win:{torso:[.03,-.19,0],head:[-.1,.03,0],arm_r:[-.59,.52,-.2],hand_r:[.2,.1,0],arm_l:[-1.01,-.26,.29],leg_l:[-.18,-.06,.13],leg_r:[.21,.06,-.12],hips_y:-.07,knee:[.15,.18]},tempo:1.14 },
  ember: { // Smoldering staff arc and commanding free-hand conjure.
    ready:{torso:[.06,-.16,.07],head:[-.04,.11,0],arm_r:[-1.06,.21,-.29],arm_l:[-.66,-.33,.58],hand_l:[.26,0,.12],leg_l:[-.1,0,.08],leg_r:[.12,0,-.08],hips_y:-.02},
    wind:{torso:[.21,-.47,.06],head:[-.13,.31,0],arm_r:[-1.7,.35,-.34],arm_l:[-1.22,-.47,.67],hand_l:[.25,.3,.1]},
    move:{torso:[-.08,.23,-.08],head:[-.22,.02,0],arm_r:[-2.56,-.22,-.21],hand_r:[.12,0,.17],arm_l:[-2.11,-.04,.56],hand_l:[-.15,.3,.16]},
    hero:{torso:[.09,-.13,.07],head:[-.14,.11,.02],arm_r:[-2.07,.20,-.28],arm_l:[-1.53,-.3,.63],hand_l:[.18,.23,.16],hips_y:-.03},
    win:{torso:[-.09,.1,.04],head:[-.20,-.04,0],arm_r:[-2.49,.02,-.16],arm_l:[-2.2,-.12,.49],hand_l:[.11,.34,.18],hips_y:-.02} },
  marina: { // Water sorceress traces a sideways figure-eight and bows.
    ready:{torso:[.02,-.22,-.09],head:[-.04,.19,.02],arm_r:[-1.21,.39,-.26],arm_l:[-.82,-.31,.41],leg_l:[-.18,0,.1],leg_r:[.21,0,-.12],hips_y:-.035},
    wind:{torso:[.17,-.53,-.12],head:[.03,.32,-.04],arm_r:[-1.84,.49,-.53],arm_l:[-1.35,-.42,.7],leg_l:[-.27,0,.11]},
    move:{torso:[-.09,.34,.13],head:[-.16,-.08,0],arm_r:[-2.43,-.2,-.29],arm_l:[-1.86,.17,.39],hand_l:[.16,.12,.2]},
    hero:{torso:[.04,-.26,-.12],head:[-.11,.17,0],arm_r:[-1.84,.25,-.33],arm_l:[-1.36,-.47,.55],leg_l:[-.21,0,.11],leg_r:[.26,0,-.15],hips_y:-.035},
    win:{torso:[.21,-.15,-.1],head:[.08,.08,0],arm_r:[-1.55,.29,-.35],arm_l:[-1.8,-.31,.64],hand_l:[.21,.1,.22],leg_l:[-.16,0,.13],leg_r:[.2,0,-.10],hips_y:-.055} },
  nyx: { // Low vanish, crossing blades, flick up and pointed stare.
    ready:{torso:[.26,-.3,.11],head:[-.04,.17,0],arm_r:[-1.17,.53,-.23],arm_l:[-1.16,-.51,.24],leg_l:[-.33,0,.15],leg_r:[.3,0,-.16],hips_y:-.12,knee:[.31,.28]},
    wind:{torso:[.48,-.57,.05],head:[.1,.28,0],arm_r:[-.69,.71,-.28],arm_l:[-.71,-.65,.19],hips_y:-.21,knee:[.48,.43]},
    move:{torso:[-.02,.44,-.10],head:[-.19,-.17,0],arm_r:[-2.30,-.23,-.58],arm_l:[-2.13,.2,.51],hips_y:-.075,knee:[.17,.24]},
    hero:{torso:[.21,-.28,.08],head:[-.06,.17,0],arm_r:[-1.68,.41,-.26],arm_l:[-1.19,-.39,.27],leg_l:[-.37,0,.14],leg_r:[.29,0,-.16],hips_y:-.13,knee:[.27,.33]},
    win:{torso:[.13,-.3,.05],head:[-.17,.18,-.02],arm_r:[-1.85,.3,-.5],arm_l:[-1.85,-.33,.45],leg_l:[-.37,0,.15],leg_r:[.3,0,-.16],hips_y:-.1,knee:[.22,.29]} },
  rook: { // Guard -> quick one-two -> champion fist pump.
    ready:{torso:[.18,.06,.02],head:[.03,0,0],arm_r:[-1.15,.19,-.41],hand_r:[.5,0,-.12],arm_l:[-1.17,-.15,.43],hand_l:[.5,0,.1],leg_l:[-.20,-.07,.16],leg_r:[.20,.07,-.17],hips_y:-.13,knee:[.3,.28]},
    wind:{torso:[.27,-.29,0],head:[.05,.15,0],arm_r:[-.84,.19,-.38],arm_l:[-1.4,-.12,.42],hips_y:-.16,knee:[.38,.31]},
    move:{torso:[.06,.35,-.06],head:[-.14,-.15,0],arm_r:[-2.0,.04,-.16],arm_l:[-1.27,-.27,.42],hand_r:[.38,0,-.1],hips_y:-.10},
    hero:{torso:[.16,.07,.01],head:[-.07,.01,0],arm_r:[-1.31,.19,-.4],arm_l:[-1.47,-.20,.44],leg_l:[-.20,-.06,.16],leg_r:[.22,.07,-.17],hips_y:-.12,knee:[.27,.28]},
    win:{torso:[-.1,.08,0],head:[-.16,.01,0],arm_r:[-2.68,.08,-.25],hand_r:[.4,0,-.05],arm_l:[-1.38,-.18,.32],leg_l:[-.21,-.09,.17],leg_r:[.22,.07,-.18],hips_y:-.11,knee:[.23,.25]} },
  gale: { // Side-step dancer, windmill punch, skyward fist.
    ready:{torso:[.10,-.26,.13],head:[0,.14,0],arm_r:[-.75,.34,-.42],arm_l:[-1.20,-.38,.34],leg_l:[-.29,-.02,.11],leg_r:[.31,.02,-.15],hips_y:-.08,knee:[.22,.19]},
    wind:{torso:[.35,-.50,.18],head:[-.04,.22,0],arm_r:[-.45,.63,-.45],arm_l:[-1.5,-.47,.37],leg_l:[-.4,-.02,.14],leg_r:[.21,.02,-.14],hips_y:-.13},
    move:{torso:[-.19,.43,-.1],head:[-.22,-.09,0],arm_r:[-2.75,-.1,-.24],arm_l:[-.86,-.19,.39],leg_l:[-.1,0,.19],leg_r:[.40,0,-.12],hips_y:-.025},
    hero:{torso:[.08,-.28,.12],head:[-.08,.15,0],arm_r:[-1.70,.22,-.45],arm_l:[-1.3,-.30,.43],leg_l:[-.24,0,.15],leg_r:[.3,0,-.17],hips_y:-.065},
    win:{torso:[-.07,.06,.02],head:[-.17,.02,0],arm_r:[-2.7,.15,-.25],arm_l:[-.85,-.26,.39],leg_l:[-.17,0,.16],leg_r:[.31,0,-.20],hips_y:-.04} },
  bob: { // Mischievous fake throw -> both arms out -> proud showman bow.
    ready:{torso:[-.02,-.1,.06],head:[-.06,.12,.08],arm_r:[-.83,.15,-.53],arm_l:[-.77,-.18,.52],leg_l:[-.16,0,.15],leg_r:[.18,0,-.15],hips_y:-.04},
    wind:{torso:[.20,.22,-.12],head:[.09,-.07,.1],arm_r:[-.3,.42,-.81],arm_l:[-1.3,-.4,.59],hand_r:[.52,0,-.13],hips_y:-.08},
    move:{torso:[-.16,-.21,.11],head:[-.2,.15,.13],arm_r:[-2.25,.12,-.65],arm_l:[-2.12,-.11,.73],hand_r:[.22,0,-.28],hand_l:[.23,0,.25]},
    hero:{torso:[-.06,-.13,.06],head:[-.08,.12,.1],arm_r:[-1.32,.16,-.9],arm_l:[-1.25,-.16,.85],leg_l:[-.17,0,.14],leg_r:[.21,0,-.16],hips_y:-.04},
    win:{torso:[.21,-.12,.12],head:[.1,.03,.12],arm_r:[-1.44,.12,-1.03],arm_l:[-1.46,-.14,1.0],leg_l:[-.2,0,.16],leg_r:[.24,0,-.18],hips_y:-.09} },
  kira: { // Genuine kick choreography: chamber bent knee -> extended high kick -> balanced crane.
    ready:{torso:[.04,-.16,-.09],head:[-.01,.19,0],arm_r:[-.98,.18,-.40],hand_r:[.51,0,-.12],arm_l:[-1.0,-.2,.41],hand_l:[.45,0,.1],leg_l:[-.13,0,.15],leg_r:[.05,0,-.12],hips_y:-.06,knee:[.17,.16]},
    wind:{torso:[.19,-.39,-.16],head:[-.04,.27,0],arm_r:[-1.31,.18,-.47],arm_l:[-1.19,-.3,.43],leg_l:[-.25,0,.11],leg_r:[-.95,.14,-.30],hips_y:-.10,knee:[.30,1.42]},
    move:{torso:[-.16,.18,-.20],head:[-.08,-.02,0],arm_r:[-1.25,.29,-.46],arm_l:[-1.53,-.11,.50],leg_l:[-.2,0,.19],leg_r:[-1.46,.10,-.65],hips_y:-.055,knee:[.20,.12]},
    hero:{torso:[-.04,-.12,-.15],head:[-.06,.15,0],arm_r:[-1.12,.20,-.4],arm_l:[-1.23,-.16,.42],leg_l:[-.19,0,.15],leg_r:[-.87,.1,-.33],hips_y:-.05,knee:[.19,1.12]},
    win:{torso:[-.14,-.10,-.17],head:[-.09,.16,0],arm_r:[-1.17,.16,-.43],arm_l:[-1.35,-.21,.45],leg_l:[-.16,0,.2],leg_r:[-1.37,.12,-.54],hips_y:-.04,knee:[.17,.25]} },
  raven: { // Dark witch opens portal hand; a sharp staff hook becomes victory ritual.
    ready:{torso:[.09,-.2,-.05],head:[-.1,.17,0],arm_r:[-1.33,.38,-.21],arm_l:[-.75,-.35,.51],hand_l:[.19,.17,0],hips_y:-.035},
    wind:{torso:[.22,-.45,-.1],head:[.02,.28,-.05],arm_r:[-1.85,.34,-.26],arm_l:[-1.55,-.42,.74],hand_l:[.25,.33,-.04]},
    move:{torso:[-.1,.25,.08],head:[-.22,-.13,0],arm_r:[-2.54,-.19,-.22],arm_l:[-2.18,-.21,.58],hand_l:[.02,.4,.12]},
    hero:{torso:[.11,-.23,-.06],head:[-.17,.16,-.03],arm_r:[-2.13,.27,-.31],arm_l:[-1.5,-.34,.65],hand_l:[.14,.18,.08],hips_y:-.025},
    win:{torso:[-.07,.02,-.07],head:[-.22,.05,-.02],arm_r:[-2.48,.14,-.25],arm_l:[-2.36,-.19,.55],hand_l:[-.04,.32,.11]} },
  ash: { // Archer draws across shoulder; actual string + arrow move with bow.
    ready:{torso:[.10,-.32,0],head:[-.05,.24,0],arm_r:[-.82,.39,-.25],arm_l:[-1.23,-.42,.43],hand_r:[.44,0,-.1],leg_l:[-.2,0,.15],leg_r:[.21,0,-.13],hips_y:-.06},
    wind:{torso:[.12,-.56,.02],head:[-.03,.34,0],arm_r:[-1.38,.75,-.23],hand_r:[.52,.11,-.10],arm_l:[-1.59,-.61,.47],hips_y:-.08},
    move:{torso:[-.05,.15,-.02],head:[-.13,-.05,0],arm_r:[-1.79,.38,-.18],hand_r:[-.14,.05,-.06],arm_l:[-1.7,-.26,.36],hips_y:-.045},
    hero:{torso:[.10,-.28,.01],head:[-.07,.22,0],arm_r:[-1.09,.49,-.19],arm_l:[-1.39,-.39,.38],leg_l:[-.2,0,.13],leg_r:[.24,0,-.14],hips_y:-.055},
    win:{torso:[.06,-.28,0],head:[-.15,.19,0],arm_r:[-1.74,.39,-.19],arm_l:[-1.52,-.31,.41],leg_l:[-.22,0,.13],leg_r:[.22,0,-.14],hips_y:-.06} },
  veyr: { // Quiet predator's crouch, sickle scissor, low feral silhouette.
    ready:{torso:[.39,.04,-.09],head:[-.1,-.12,.03],arm_r:[-.92,.42,-.62],arm_l:[-1.03,-.4,.65],leg_l:[-.39,-.1,.17],leg_r:[.37,.1,-.15],hips_y:-.18,knee:[.43,.41]},
    wind:{torso:[.58,-.4,-.16],head:[-.06,.24,0],arm_r:[-.46,.5,-.78],arm_l:[-.5,-.49,.72],hips_y:-.25,knee:[.57,.5]},
    move:{torso:[.17,.48,.04],head:[-.2,-.17,0],arm_r:[-2.15,-.31,-.55],arm_l:[-2.07,.27,.49],hips_y:-.11,knee:[.29,.31]},
    hero:{torso:[.38,.07,-.09],head:[-.08,-.11,.05],arm_r:[-1.31,.38,-.73],arm_l:[-1.46,-.31,.67],leg_l:[-.36,-.11,.15],leg_r:[.38,.09,-.17],hips_y:-.18,knee:[.42,.41]},
    win:{torso:[.29,-.12,-.11],head:[-.16,-.14,.02],arm_r:[-1.83,.36,-.56],arm_l:[-1.83,-.4,.52],leg_l:[-.37,-.1,.18],leg_r:[.34,.12,-.18],hips_y:-.14,knee:[.37,.38]} },
  zarek: { // Grounded figure-eight double glaive spin; ending shaft across shoulder.
    ready:{torso:[.08,-.16,-.05],head:[-.06,.13,0],arm_r:[-1.11,.35,-.29],hand_r:[.34,.08,-.15],arm_l:[-.98,-.23,.29],hand_l:[.29,0,.15],leg_l:[-.18,-.08,.16],leg_r:[.23,.06,-.15],hips_y:-.08,knee:[.19,.21]},
    wind:{torso:[.17,-.39,.08],head:[.02,.23,0],arm_r:[-1.48,.48,-.36],hand_r:[.5,.08,-.17],arm_l:[-1.14,-.28,.42],hips_y:-.11,knee:[.26,.23]},
    move:{torso:[-.08,.37,-.09],head:[-.16,-.1,0],arm_r:[-2.12,-.16,-.31],hand_r:[.28,.17,-.19],arm_l:[-1.29,.24,.43],leg_l:[-.29,-.08,.13],leg_r:[.29,.05,-.17],hips_y:-.05},
    hero:{torso:[.09,-.19,-.04],head:[-.08,.12,0],arm_r:[-1.22,.36,-.35],hand_r:[.29,.12,-.08],arm_l:[-.93,-.23,.39],leg_l:[-.2,-.08,.17],leg_r:[.24,.06,-.14],hips_y:-.07},
    win:{torso:[-.03,.1,-.04],head:[-.18,-.03,0],arm_r:[-2.29,.1,-.22],hand_r:[.18,.15,-.13],arm_l:[-1.14,-.25,.38],leg_l:[-.17,-.08,.17],leg_r:[.27,.06,-.17],hips_y:-.06} },
  kaizen: { // Controlled chain guard, ferocious circling blade, victorious catch.
    ready:{torso:[.17,.1,-.02],head:[-.08,-.1,0],arm_r:[-1.01,.31,-.47],hand_r:[.29,0,-.13],arm_l:[-.93,-.21,.47],leg_l:[-.25,-.07,.21],leg_r:[.27,.08,-.21],hips_y:-.13,knee:[.24,.24]},
    wind:{torso:[.35,-.41,.03],head:[.06,.2,0],arm_r:[-1.56,.53,-.54],arm_l:[-1.33,-.34,.53],hips_y:-.2,knee:[.37,.33]},
    move:{torso:[-.15,.4,-.03],head:[-.2,-.12,0],arm_r:[-2.4,-.17,-.43],hand_r:[.16,0,-.16],arm_l:[-1.68,.14,.49],hips_y:-.08,knee:[.19,.21]},
    hero:{torso:[.2,.09,-.03],head:[-.11,-.11,0],arm_r:[-1.31,.39,-.48],arm_l:[-1.13,-.24,.46],leg_l:[-.27,-.08,.19],leg_r:[.27,.07,-.22],hips_y:-.12,knee:[.28,.24]},
    win:{torso:[-.07,.12,0],head:[-.18,0,0],arm_r:[-2.38,.08,-.31],arm_l:[-1.51,-.19,.42],leg_l:[-.26,-.09,.22],leg_r:[.27,.08,-.23],hips_y:-.11,knee:[.22,.25]} },
};

function filled(base: Pose, delta: Beat): Pose {
  const v = (p: Vec3): Vec3 => [p[0],p[1],p[2]];
  return { torso:v(delta.torso ?? base.torso), head:v(delta.head ?? base.head),
    arm_r:v(delta.arm_r ?? base.arm_r),hand_r:v(delta.hand_r ?? base.hand_r),
    arm_l:v(delta.arm_l ?? base.arm_l),hand_l:v(delta.hand_l ?? base.hand_l),
    leg_l:v(delta.leg_l ?? base.leg_l),leg_r:v(delta.leg_r ?? base.leg_r),
    hips_y:delta.hips_y ?? base.hips_y,
    knee:[...(delta.knee ?? base.knee ?? [0,0])] as [number,number] };
}
function between(a: Pose, b: Pose, u: number): Pose {
  // Smooth acceleration/deceleration for believable setup, release and settle.
  const w = u*u*(3-2*u);
  const mix = (x:number,y:number) => x+(y-x)*w;
  const v=(x:Vec3,y:Vec3):Vec3=>[mix(x[0],y[0]),mix(x[1],y[1]),mix(x[2],y[2])];
  return { torso:v(a.torso,b.torso),head:v(a.head,b.head),arm_r:v(a.arm_r,b.arm_r),
    arm_l:v(a.arm_l,b.arm_l),hand_r:v(a.hand_r,b.hand_r),hand_l:v(a.hand_l,b.hand_l),
    leg_l:v(a.leg_l,b.leg_l),leg_r:v(a.leg_r,b.leg_r),
    hips_y:mix(a.hips_y,b.hips_y),
    knee:[mix(a.knee?.[0]??0,b.knee?.[0]??0),mix(a.knee?.[1]??0,b.knee?.[1]??0)] };
}

// NYTHERA_SHOWCASE_SPIN_TOSS_V3: scripted full-body rhythm aligned to the scythe's
// independent throw/catch window in FighterModel.animateNytheraShowcase().
const NYTHERA_SHOWCASE: Array<[number,Beat]> = [
  [0.00, {torso:[.04,-.23,.03],head:[-.06,.15,0],arm_r:[-1.12,.23,-.23],arm_l:[-1.19,-.15,.33],leg_l:[-.25,0,.13],leg_r:[.18,0,-.12],hips_y:-.055,knee:[.18,.16]}],
  [.53, {torso:[.23,-.57,.09],head:[.02,.37,-.04],arm_r:[-.72,-.63,-.37],arm_l:[-1.12,-.33,.48],leg_l:[-.44,0,.16],leg_r:[.38,0,-.16],hips_y:-.14,knee:[.38,.26]}],
  [1.07,{torso:[-.11,.47,-.09],head:[-.10,-.29,.04],arm_r:[-2.25,.68,-.17],arm_l:[-1.78,.35,.32],leg_l:[-.35,0,.10],leg_r:[.48,0,-.18],hips_y:-.03,knee:[.2,.14]}],
  [1.50,{torso:[.16,-.63,.11],head:[-.03,.25,-.03],arm_r:[-.84,-.75,-.43],arm_l:[-.94,-.4,.42],leg_l:[-.40,.03,.18],leg_r:[.34,-.04,-.12],hips_y:-.10,knee:[.31,.29]}],
  [1.95,{torso:[-.17,.61,-.10],head:[-.15,-.33,.06],arm_r:[-2.65,.22,-.15],arm_l:[-2.24,.27,.25],leg_l:[-.16,.02,.18],leg_r:[.38,0,-.12],hips_y:-.035,knee:[.20,.14]}],
  [2.42,{torso:[.25,-.87,.09],head:[.03,.46,-.03],arm_r:[-.92,-.8,-.49],arm_l:[-.91,-.58,.40],leg_l:[-.53,.02,.16],leg_r:[.56,-.02,-.14],hips_y:-.16,knee:[.42,.36]}],
  [3.04,{torso:[-.22,.48,-.02],head:[-.16,-.1,0],arm_r:[-2.72,.24,-.18],arm_l:[-1.82,.18,.25],leg_l:[-.31,0,.13],leg_r:[.43,0,-.14],hips_y:-.04,knee:[.14,.18]}],
  [3.35,{torso:[-.10,.25,.01],head:[-.26,-.07,0],arm_r:[-2.47,.16,-.24],hand_r:[-.28,0,-.04],arm_l:[-1.70,-.30,.54],hand_l:[.14,.1,.09],leg_l:[-.31,0,.13],leg_r:[.40,0,-.11],hips_y:-.02,knee:[.12,.16]}],
  [4.08,{torso:[-.10,-.37,-.06],head:[-.32,.21,.06],arm_r:[-1.26,.47,-.48],hand_r:[-.25,0,.08],arm_l:[-2.26,-.06,.49],hand_l:[.28,0,.14],leg_l:[-.27,0,.12],leg_r:[.23,0,-.11],hips_y:0.035,knee:[.10,.08]}],
  [4.75,{torso:[.08,.50,.06],head:[-.29,-.28,0],arm_r:[-2.05,-.25,-.30],hand_r:[.28,0,-.02],arm_l:[-1.95,.33,.31],leg_l:[-.32,0,.14],leg_r:[.45,0,-.12],hips_y:.02,knee:[.12,.09]}],
  [5.52,{torso:[.20,-.30,.03],head:[-.16,.17,0],arm_r:[-1.69,.39,-.26],hand_r:[.24,0,.04],arm_l:[-1.48,-.35,.40],leg_l:[-.32,0,.14],leg_r:[.40,0,-.13],hips_y:-.085,knee:[.23,.23]}],
  [5.94,{torso:[.24,-.62,.09],head:[.04,.31,0],arm_r:[-.95,-.73,-.33],arm_l:[-1.22,-.40,.36],leg_l:[-.46,0,.18],leg_r:[.41,0,-.15],hips_y:-.12,knee:[.34,.28]}],
  [6.34,{torso:[-.17,.56,-.11],head:[-.14,-.17,0],arm_r:[-2.45,.50,-.16],arm_l:[-1.73,.30,.28],leg_l:[-.34,0,.12],leg_r:[.48,0,-.18],hips_y:-.025,knee:[.15,.12]}],
  [6.77,{torso:[.19,-.73,.08],head:[.02,.36,0],arm_r:[-1.08,-.58,-.46],arm_l:[-1.15,-.34,.47],leg_l:[-.46,0,.18],leg_r:[.46,0,-.16],hips_y:-.16,knee:[.41,.37]}],
  [7.30,{torso:[.37,.19,.10],head:[-.25,-.05,0],arm_r:[-.63,.44,-.41],hand_r:[.22,0,.24],arm_l:[-1.05,.16,.41],leg_l:[-.59,0,.17],leg_r:[.51,0,-.13],hips_y:-.23,knee:[.48,.33]}],
  [7.86,{torso:[.02,-.12,.03],head:[-.17,.19,-.02],arm_r:[-1.69,.18,-.30],arm_l:[-1.22,-.19,.28],leg_l:[-.27,0,.14],leg_r:[.22,0,-.12],hips_y:-.062,knee:[.21,.18]}],
  [8.64,{torso:[.02,-.12,.03],head:[-.17,.19,-.02],arm_r:[-1.69,.18,-.30],arm_l:[-1.22,-.19,.28],leg_l:[-.27,0,.14],leg_r:[.22,0,-.12],hips_y:-.062,knee:[.21,.18]}],
  [9.67,{torso:[.04,-.23,.03],head:[-.06,.15,0],arm_r:[-1.12,.23,-.23],arm_l:[-1.19,-.15,.33],leg_l:[-.25,0,.13],leg_r:[.18,0,-.12],hips_y:-.055,knee:[.18,.16]}],
  [10.20,{torso:[.04,-.23,.03],head:[-.06,.15,0],arm_r:[-1.12,.23,-.23],arm_l:[-1.19,-.15,.33],leg_l:[-.25,0,.13],leg_r:[.18,0,-.12],hips_y:-.055,knee:[.18,.16]}],
];
function nytheraPresentation(seconds:number,base:Pose,mode:"select"|"victory"):Pose {
  const t=mode==="victory"? Math.min(Math.max(seconds,0),8.0):((seconds%10.2)+10.2)%10.2;
  let i=0;
  while (i<NYTHERA_SHOWCASE.length-2 && t>NYTHERA_SHOWCASE[i+1][0]) i++;
  const p=NYTHERA_SHOWCASE[i],n=NYTHERA_SHOWCASE[i+1];
  const u=Math.max(0,Math.min(1,(t-p[0])/(n[0]-p[0])));
  const pose=between(filled(base,p[1]),filled(base,n[1]),u);
  pose.head[1]+=Math.sin(seconds*1.5)*0.012;
  pose.torso[0]+=Math.sin(seconds*2.5)*0.007;
  return pose;
}

// ZEPHYR_DRAGON_DANCER_V1 · SANJIEKUN_VISUAL_V17 — 9-second playful linked-rod show.
function zephyrPresentation(seconds: number, base: Pose, mode: "select" | "victory"): Pose {
  const t=mode==="select"?((seconds%9)+9)%9:Math.min(seconds,8.85);
  const beats: Array<[number,Beat]> = [
    [0, {torso:[.08,-.35,.08],head:[-.07,.22,.05],arm_r:[-.88,.25,-.32],arm_l:[-.75,-.31,.38],leg_l:[-.22,0,.13],leg_r:[.26,0,-.14],hips_y:-.09}],
    [.50,{torso:[.10,-.57,.13],head:[-.03,.30,-.04],arm_r:[-1.45,.53,-.26],arm_l:[-.78,-.25,.48],hips_y:-.13}],
    [1.16,{torso:[-.07,.51,-.13],head:[-.16,-.12,.06],arm_r:[-1.75,-.22,-.18],arm_l:[-1.36,.42,.33],leg_l:[-.37,0,.13],leg_r:[.33,0,-.18],hips_y:-.05}],
    [1.58,{torso:[.12,-.42,.11],head:[-.01,.24,-.07],arm_r:[-.68,.33,-.5],arm_l:[-1.84,-.32,.20],hips_y:-.11}],
    [2.18,{torso:[.08,.53,-.08],head:[-.14,-.27,.06],arm_r:[-1.04,.21,-.3],arm_l:[-2.2,.35,.39],leg_l:[-.40,0,.18],leg_r:[.36,0,-.13],hips_y:-.07}],
    [2.63,{torso:[.12,-.58,.12],head:[-.05,.36,-.02],arm_r:[-1.76,-.65,-.38],arm_l:[-1.1,-.31,.50],hips_y:-.12}],
    [3.2,{torso:[-.10,.60,-.06],head:[-.12,-.24,.02],arm_r:[-2.07,.62,-.20],arm_l:[-.68,.23,.43],leg_l:[-.37,0,.15],leg_r:[.35,0,-.17],hips_y:-.07}],
    [3.75,{torso:[.20,-.38,.09],head:[-.02,.3,.02],arm_r:[-1.65,.41,-.33],arm_l:[-2.28,-.29,.36],hips_y:-.12}],
    [4.45,{torso:[-.19,-.28,0],head:[-.05,.17,0],arm_r:[-2.38,.16,-.15],arm_l:[-.55,-.46,.49],hips_y:-.07}],
    [4.70,{torso:[-.16,-.32,.03],head:[-.22,.11,.04],arm_r:[-2.42,.14,-.19],arm_l:[-.74,-.33,.48],hips_y:-.06}],
    [5.30,{torso:[.16,.46,.06],head:[.08,-.10,.01],arm_r:[-.62,.46,-.29],arm_l:[-1.12,-.19,.29],leg_l:[-.55,0,.08],leg_r:[-.85,0,-.09],hips_y:.05}],
    [6.18,{torso:[.11,.19,-.06],head:[-.16,.15,.02],arm_r:[-2.37,.25,-.29],arm_l:[-1.48,-.24,.37],hips_y:-.08}],
    [6.53,{torso:[.12,-.48,.09],head:[-.02,.30,0],arm_r:[-1.34,.35,-.35],arm_l:[-1.14,-.34,.36],hips_y:-.12}],
    [7.08,{torso:[-.04,.52,-.13],head:[-.13,-.25,.04],arm_r:[-2.03,.36,-.39],arm_l:[-.95,.13,.41],leg_l:[-.31,0,.2],leg_r:[.33,0,-.12],hips_y:-.07}],
    [7.63,{torso:[.39,.17,.07],head:[-.16,-.05,.02],arm_r:[-.84,.19,-.48],arm_l:[-1.56,-.14,.36],leg_l:[-.49,0,.18],leg_r:[.34,0,-.15],hips_y:-.18,knee:[.45,.38]}],
    [8.38,{torso:[.12,-.26,.05],head:[-.08,.15,.01],arm_r:[-.91,.32,-.34],arm_l:[-1.02,-.24,.38],hips_y:-.11}],
    [9, {torso:[.08,-.35,.08],head:[-.07,.22,.05],arm_r:[-.88,.25,-.32],arm_l:[-.75,-.31,.38],leg_l:[-.22,0,.13],leg_r:[.26,0,-.14],hips_y:-.09}],
  ];
  let i=0; while(i<beats.length-2 && t>beats[i+1][0])i++;
  const lo=beats[i],hi=beats[i+1];
  const u=Math.max(0,Math.min(1,(t-lo[0])/Math.max(.001,hi[0]-lo[0])));
  return between(filled(base,lo[1]),filled(base,hi[1]),u);
}

// RAIGO_IRON_BASTION_V1: axe and flail are independently moving during presentation.
function raigoShow(seconds:number, base:Pose, mode:"select"|"victory"):Pose {
  const t=mode==="select"?((seconds%9.6)+9.6)%9.6:Math.min(seconds,8.6);
  const beats: Array<[number,Beat]> = [
    [0,{torso:[.17,-.20,0],arm_r:[-.80,.17,-.34],arm_l:[-.95,-.23,.32],hips_y:-.14}],
    [1.1,{torso:[.12,-.52,.03],arm_r:[-1.45,.32,-.41],arm_l:[-1.70,-.37,.38],hips_y:-.17}],
    [2.4,{torso:[-.09,.40,.07],arm_r:[-1.82,.46,-.30],arm_l:[-2.43,.10,.27],hips_y:-.10}],
    [3.5,{torso:[.24,-.37,-.05],arm_r:[-1.50,-.20,-.52],arm_l:[-2.50,.15,.32],hips_y:-.19}],
    [4.6,{torso:[.11,.42,.02],arm_r:[-2.22,.34,-.22],arm_l:[-1.74,-.43,.36],hips_y:-.11}],
    [5.5,{torso:[-.16,-.52,.07],arm_r:[-2.63,-.35,-.29],arm_l:[-2.12,.28,.46],hips_y:-.09}],
    [6.65,{torso:[.18,.54,-.04],arm_r:[-1.90,.45,-.47],arm_l:[-1.52,-.58,.33],hips_y:-.13}],
    [7.6,{torso:[.51,.28,0],arm_r:[-.75,.36,-.40],arm_l:[-.99,-.11,.35],leg_l:[-.52,0,.13],leg_r:[.37,0,-.17],hips_y:-.26,knee:[.49,.46]}],
    [8.6,{torso:[.18,-.20,0],arm_r:[-.80,.17,-.34],arm_l:[-.95,-.23,.32],hips_y:-.14}],
    [9.6,{torso:[.17,-.20,0],arm_r:[-.80,.17,-.34],arm_l:[-.95,-.23,.32],hips_y:-.14}],
  ];
  let i=0;while(i<beats.length-2&&t>beats[i+1][0])i++;
  const lo=beats[i],hi=beats[i+1],u=Math.max(0,Math.min(1,(t-lo[0])/Math.max(.001,hi[0]-lo[0])));
  return between(filled(base,lo[1]),filled(base,hi[1]),u);
}

/** Entirely cosmetic; all poses use the same normalized VRM/procedural joints as combat. */
export function presentationPose(name: string, seconds: number, base: Pose, mode: "select" | "victory" = "select"): Pose {
  if (name.toLowerCase() === "nythera") return nytheraPresentation(seconds,base,mode);
  if (name.toLowerCase() === "zephyr") return zephyrPresentation(seconds,base,mode);
  if (name.toLowerCase() === "raigo") return raigoShow(seconds,base,mode);
  const entry = C[name.toLowerCase()];
  if (!entry) { // Future roster entries still receive a respectful, animated salute.
    const p = filled(base,{ torso:[.07,.07*Math.sin(seconds),0], arm_r:[-1.6-.25*Math.sin(seconds*1.5),.1,-.2],arm_l:[-.9,0,.3] });
    return p;
  }
  const speed = entry.tempo ?? 1;
  // Victory should finish and HOLD instead of unnaturally looping a celebration.
  const t = mode === "victory" ? Math.min(Math.max(seconds*speed,0),7.5) : ((seconds*speed%6.2)+6.2)%6.2;
  const k: Array<[number, Beat]> = mode === "victory" ? [
    [0,entry.ready],[.55,entry.wind],[1.35,entry.move],[2.35,entry.win],[7.5,entry.win]
  ] : [
    [0,entry.ready],[.55,entry.wind],[1.35,entry.move],[2.35,entry.hero],
    [3.75,entry.hero],[5.4,entry.ready],[6.2,entry.ready]
  ];
  let i=0;
  while(i<k.length-2 && t>k[i+1][0]) i++;
  const from=k[i],to=k[i+1];
  const u=Math.max(0,Math.min(1,(t-from[0])/(to[0]-from[0])));
  const p=between(filled(base,from[1]),filled(base,to[1]),u);
  // Controlled breathing and head/hand overlap after the flourish. Never moves hitboxes.
  const quiet = t>2.25?1:.35;
  p.torso[0]+=Math.sin(seconds*2.2)*.008*quiet;
  p.head[1]+=Math.sin(seconds*1.05+.6)*.013*quiet;
  p.hand_l[2]+=Math.sin(seconds*1.8+1.1)*.014*quiet;
  p.hand_r[2]+=Math.sin(seconds*1.7)*.013*quiet;
  return p;
}
