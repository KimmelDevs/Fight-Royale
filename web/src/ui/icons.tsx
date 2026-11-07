// BALANCE_KIRA_KAEDE_PATTERN_AI_AIR_ICON_20261107_V1
"use client";
// Icon images live in public/icons (generated with ChatGPT and sliced from sheets):
//   skills/<set>-<key>.webp  where set = kit, or mage-<element> for mages; key = z, x, c or v
//   emblems/<id>.webp, chars/<character id>.webp, gold.webp, diamond.webp
// Each <Icon> falls back to its text when the image is missing.
import { useState } from "react";

// Air attacks reuse the regular skill artwork; no missing *_air.webp requests.
export const skillIcon = (kit: string, element: string, key: string) =>
  `/icons/skills/${kit === "mage" ? `mage-${element}` : kit === "glaive" && element === "metal" ? "glaive-metal" : kit}-${key.replace(/_air$/, "")}.webp`;
export const emblemIcon = (id: string) => `/icons/emblems/${id}.webp`;
/** Character portrait; "random" is the question mark. */
export const charIcon = (id: string) => `/icons/chars/${id}.webp`;

export function Icon({ src, alt, size = 40, fallback }: { src: string; alt: string; size?: number; fallback?: React.ReactNode }) {
  const [bad, setBad] = useState(false);
  if (bad) return <>{fallback ?? null}</>;
  return <img src={src} alt={alt} width={size} height={size} className="icon-img" draggable={false} onError={() => setBad(true)} />;
}

export const Gold = ({ size = 16 }: { size?: number }) => <Icon src="/icons/gold.webp" alt="gold" size={size} fallback={<span>gold</span>} />;
export const Diamond = ({ size = 16 }: { size?: number }) => <Icon src="/icons/diamond.webp" alt="diamonds" size={size} fallback={<span>diamonds</span>} />;
