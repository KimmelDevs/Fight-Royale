// Cel-shading material factory: toon, inverted-hull outline, double-sided cloth,
// stylized water, an analytic anime face, and helpers. Colors are authored in sRGB and the
// renderer outputs them untouched (color management off), so hex values look exactly as picked.
import * as THREE from "three";

THREE.ColorManagement.enabled = false;

/** Direction toward the sun in world space; the view-space copy is refreshed every frame. */
export const LIGHT_DIR = new THREE.Vector3(0.45, 0.8, 0.4).normalize();
export const lightView = { value: new THREE.Vector3() };
export const timeU = { value: 0 };

export function updateLight(camera: THREE.Camera) {
  lightView.value.copy(LIGHT_DIR).transformDirection(camera.matrixWorldInverse);
}

const TOON_VERT = /* glsl */ `
varying vec3 vN; varying vec3 vV;
void main(){
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vN = normalize(normalMatrix * normal);
  vV = normalize(-mv.xyz);
  gl_Position = projectionMatrix * mv;
}`;

const TOON_COMMON = /* glsl */ `
uniform vec3 shadeTint; uniform vec3 rimColor; uniform vec3 emission;
uniform float rimAmount; uniform vec3 lightView;
vec3 toonShade(vec3 base, vec3 n, vec3 v){
  float ndl = dot(n, normalize(lightView));
  float lit = smoothstep(-0.03, 0.03, ndl);
  vec3 col = mix(base * shadeTint, base, lit);
  float fres = 1.0 - clamp(dot(n, v), 0.0, 1.0);
  float rim = smoothstep(0.62, 0.68, fres) * (0.35 + 0.65 * lit);
  col += rimColor * 0.35 * rim * rimAmount;
  return col + emission;
}`;

const TOON_FRAG = /* glsl */ `
uniform vec3 albedo;
${TOON_COMMON}
varying vec3 vN; varying vec3 vV;
void main(){ gl_FragColor = vec4(toonShade(albedo, normalize(vN), normalize(vV)), 1.0); }`;

const OUTLINE_VERT = /* glsl */ `
uniform float width; uniform float wind; uniform float time;
void main(){
  vec3 p = position;
  p += normal * sin(mod(time, 100.0) * 3.0 + uv.x * 9.0 + uv.y * 4.0) * uv.y * uv.y * wind;
  p += normalize(normal) * width;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`;
const OUTLINE_FRAG = /* glsl */ `uniform vec3 color; void main(){ gl_FragColor = vec4(color, 1.0); }`;

const CLOTH_VERT = /* glsl */ `
uniform float wind; uniform float time;
varying vec3 vN; varying vec3 vV; varying vec2 vUv;
void main(){
  vec3 p = position + normal * sin(mod(time, 100.0) * 3.0 + uv.x * 9.0 + uv.y * 4.0) * uv.y * uv.y * wind;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); vUv = uv;
  gl_Position = projectionMatrix * mv;
}`;
const CLOTH_FRAG = /* glsl */ `
uniform vec3 albedo; uniform vec3 albedoBottom; uniform vec3 trimColor; uniform vec3 patternColor;
uniform float trimBottom; uniform float trimSides; uniform float patternStrength; uniform float patternV;
uniform float patternFreq; uniform float patternFill;
${TOON_COMMON}
varying vec3 vN; varying vec3 vV; varying vec2 vUv;
float line(float d, float hw){ float fw = max(fwidth(d), 0.0005); return 1.0 - smoothstep(hw - fw, hw + fw, d); }
void main(){
  vec3 base = mix(albedo, albedoBottom, smoothstep(0.15, 1.0, vUv.y));
  float crest = patternV + sin(vUv.x * patternFreq * 6.2831853) * 0.045;
  float crest2 = patternV + 0.08 + sin(vUv.x * patternFreq * 6.2831853 + 1.7) * 0.035;
  float l1 = line(abs(vUv.y - crest), 0.014);
  float l2 = line(abs(vUv.y - crest2), 0.009);
  if (patternFill > 0.0) {
    float fw = max(fwidth(vUv.y), 0.0005);
    float below = smoothstep(-fw, fw, vUv.y - crest);
    base = mix(base, patternColor, below * patternStrength);
    base = mix(base, albedo, l2 * below * patternStrength);
  } else {
    base = mix(base, patternColor, max(l1, l2 * 0.85) * patternStrength);
  }
  float trim = trimBottom > 0.0 ? step(1.0 - trimBottom, vUv.y) : 0.0;
  if (trimSides > 0.0) trim = max(trim, step(vUv.x, trimSides) + step(1.0 - trimSides, vUv.x));
  base = mix(base, trimColor, clamp(trim, 0.0, 1.0));
  vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
  gl_FragColor = vec4(toonShade(base, n, normalize(vV)), 1.0);
}`;

const WATER_FRAG = /* glsl */ `
uniform vec3 deepColor; uniform float deepAlpha; uniform vec3 foamColor; uniform float alphaMult;
uniform float glow; uniform float time;
varying vec3 vN; varying vec3 vV; varying vec2 vUv;
void main(){
  float fres = pow(1.0 - clamp(dot(normalize(vN), normalize(vV)), 0.0, 1.0), 2.0);
  float w = sin(vUv.x * 18.0 + vUv.y * 9.0 + mod(time, 100.0) * 3.0) * 0.5 + 0.5;
  float band = smoothstep(0.72, 0.78, w);
  vec3 c = mix(deepColor, foamColor, clamp(fres + band * 0.6, 0.0, 1.0));
  gl_FragColor = vec4(min(c * glow, vec3(1.0)), clamp(mix(deepAlpha, 1.0, fres) * alphaMult, 0.0, 1.0));
}`;
const WATER_VERT = /* glsl */ `
varying vec3 vN; varying vec3 vV; varying vec2 vUv;
void main(){
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); vUv = uv;
  gl_Position = projectionMatrix * mv;
}`;

const FACE_VERT = /* glsl */ `
varying vec3 vN; varying vec3 vLocal;
void main(){
  vLocal = position;
  vN = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;
const FACE_FRAG = /* glsl */ `
uniform vec3 skin; uniform vec3 shadeTint; uniform vec3 eyeDark; uniform vec3 irisTop; uniform vec3 irisBottom;
uniform vec3 blush; uniform vec3 mouth; uniform vec3 tongue; uniform vec3 lightView; uniform float blink; uniform float eyeScale;
varying vec3 vN; varying vec3 vLocal;
float ell(vec2 p, vec2 c, vec2 r){ return length((p - c) / r); }
float fill(float d){ float w = max(fwidth(d), 0.001); return 1.0 - smoothstep(1.0 - w, 1.0 + w, d); }
void main(){
  vec3 n = normalize(vLocal);
  vec2 p = vec2(atan(n.x, n.z), asin(clamp(n.y, -1.0, 1.0)));
  float front = smoothstep(0.0, 0.2, n.z);
  float lit = smoothstep(-0.03, 0.03, dot(normalize(vN), normalize(lightView)));
  vec3 col = mix(skin * shadeTint, skin, lit);
  float open = 1.0 - blink * 0.93;
  for (int i = 0; i < 2; i++) {
    float side = i == 0 ? 1.0 : -1.0;
    vec2 ec = vec2(0.37 * side, -0.03);
    vec2 er = vec2(0.15, 0.19 * open) * eyeScale;
    float b = fill(ell(p, vec2(0.58 * side, -0.3), vec2(0.13, 0.055)));
    col = mix(col, blush, b * 0.35 * front);
    float eye = fill(ell(p, ec, er)) * front;
    float t = clamp((p.y - (ec.y - er.y)) / (2.0 * er.y), 0.0, 1.0);
    vec3 iris = mix(irisBottom, irisTop, t);
    float inner = fill(ell(p, ec + vec2(0.0, -0.01 * open), er * 0.8));
    vec3 ecol = mix(eyeDark, iris, inner);
    float pupil = fill(ell(p, ec + vec2(0.0, 0.015 * open), vec2(0.05, 0.08 * open)));
    ecol = mix(ecol, eyeDark, pupil * 0.8);
    float h1 = fill(ell(p, ec + vec2(-0.045 * side, 0.065 * open), vec2(0.035, 0.042 * open)));
    float h2 = fill(ell(p, ec + vec2(0.04 * side, -0.075 * open), vec2(0.018, 0.018)));
    ecol = mix(ecol, vec3(1.0), max(h1, h2 * 0.9));
    col = mix(col, ecol, eye);
    float outer = fill(ell(p, ec + vec2(0.0, 0.012), er * vec2(1.14, 1.12) + vec2(0.0, 0.02)));
    float lash = outer * (1.0 - eye) * step(ec.y + er.y * 0.15, p.y) * front;
    col = mix(col, eyeDark, lash);
  }
  vec2 mc = vec2(0.0, -0.43);
  float m = fill(ell(p, mc, vec2(0.11, 0.085))) * step(p.y, mc.y + 0.012) * front;
  float tg = fill(ell(p, mc + vec2(0.0, -0.06), vec2(0.065, 0.04))) * m;
  col = mix(col, mouth, m);
  col = mix(col, tongue, tg);
  gl_FragColor = vec4(col, 1.0);
}`;

export const OUTLINE_WIDTH = 0.0065;
export const DEFAULT_SHADE = new THREE.Color(0.74, 0.72, 0.9);

const c3 = (c: THREE.ColorRepresentation) => new THREE.Color(c);
const toonCache = new Map<string, THREE.ShaderMaterial>();
const outlineCache = new Map<string, THREE.ShaderMaterial>();

export interface ToonOpts {
  rim?: number;
  emission?: THREE.ColorRepresentation;
  shade?: THREE.ColorRepresentation;
  outline?: boolean;
  width?: number;
}

/** A material pair: the fill, plus an optional outline drawn as a second mesh. */
export interface MatPair {
  fill: THREE.Material;
  outline: THREE.Material | null;
}

export function outlineMat(color: THREE.ColorRepresentation, width = OUTLINE_WIDTH, wind = 0): THREE.ShaderMaterial {
  const c = c3(color);
  const key = `${c.getHexString()}|${width}|${wind}`;
  let m = outlineCache.get(key);
  if (!m) {
    // Anime outlines are a darker, cooler version of the fill, not pure black.
    m = new THREE.ShaderMaterial({
      vertexShader: OUTLINE_VERT,
      fragmentShader: OUTLINE_FRAG,
      side: THREE.BackSide,
      uniforms: {
        color: { value: new THREE.Color(c.r * 0.38, c.g * 0.36, c.b * 0.5) },
        width: { value: width },
        wind: { value: wind },
        time: timeU,
      },
    });
    outlineCache.set(key, m);
  }
  return m;
}

export function toon(color: THREE.ColorRepresentation, o: ToonOpts = {}): MatPair {
  const c = c3(color);
  const shade = c3(o.shade ?? DEFAULT_SHADE);
  const em = c3(o.emission ?? 0x000000);
  const rim = o.rim ?? 0.3;
  const key = `${c.getHexString()}|${rim}|${em.getHexString()}|${shade.getHexString()}`;
  let m = toonCache.get(key);
  if (!m) {
    m = new THREE.ShaderMaterial({
      vertexShader: TOON_VERT,
      fragmentShader: TOON_FRAG,
      uniforms: {
        albedo: { value: c },
        shadeTint: { value: shade },
        rimColor: { value: new THREE.Color(1, 1, 1) },
        emission: { value: em },
        rimAmount: { value: rim },
        lightView,
      },
    });
    toonCache.set(key, m);
  }
  return { fill: m, outline: o.outline === false ? null : outlineMat(c, o.width ?? OUTLINE_WIDTH) };
}

export interface ClothOpts {
  bottom?: THREE.ColorRepresentation;
  trimBottom?: number;
  trimSides?: number;
  pattern?: THREE.ColorRepresentation;
  patternStrength?: number;
  patternV?: number;
  patternFreq?: number;
  patternFill?: number;
  wind?: number;
  shade?: THREE.ColorRepresentation;
  trim?: THREE.ColorRepresentation;
}

export function cloth(color: THREE.ColorRepresentation, o: ClothOpts = {}): MatPair {
  const c = c3(color);
  const wind = o.wind ?? 0;
  const m = new THREE.ShaderMaterial({
    vertexShader: CLOTH_VERT,
    fragmentShader: CLOTH_FRAG,
    side: THREE.DoubleSide,
    uniforms: {
      albedo: { value: c },
      albedoBottom: { value: c3(o.bottom ?? c) },
      trimColor: { value: c3(o.trim ?? 0xe6c26e) },
      patternColor: { value: c3(o.pattern ?? 0xffffff) },
      trimBottom: { value: o.trimBottom ?? 0 },
      trimSides: { value: o.trimSides ?? 0 },
      patternStrength: { value: o.patternStrength ?? 0 },
      patternV: { value: o.patternV ?? 0.75 },
      patternFreq: { value: o.patternFreq ?? 6 },
      patternFill: { value: o.patternFill ?? 0 },
      wind: { value: wind },
      time: timeU,
      shadeTint: { value: c3(o.shade ?? DEFAULT_SHADE) },
      rimColor: { value: new THREE.Color(1, 1, 1) },
      emission: { value: new THREE.Color(0, 0, 0) },
      rimAmount: { value: 0.3 },
      lightView,
    },
  });
  return { fill: m, outline: outlineMat(c, OUTLINE_WIDTH * 0.8, wind) };
}

export function water(deep: THREE.ColorRepresentation, alpha = 0.75, glow = 1.4): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    vertexShader: WATER_VERT,
    fragmentShader: WATER_FRAG,
    transparent: true,
    depthWrite: false,
    uniforms: {
      deepColor: { value: c3(deep) },
      deepAlpha: { value: alpha },
      foamColor: { value: new THREE.Color(0.75, 0.97, 1.0) },
      alphaMult: { value: 1 },
      glow: { value: glow },
      time: timeU,
    },
  });
}

export function face(skin: THREE.ColorRepresentation, look: any): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    vertexShader: FACE_VERT,
    fragmentShader: FACE_FRAG,
    uniforms: {
      skin: { value: c3(skin) },
      shadeTint: { value: new THREE.Color(1.0, 0.82, 0.82) },
      eyeDark: { value: c3(look.eye_dark ?? 0x1a2a66) },
      irisTop: { value: c3(look.iris_top ?? 0x1f6fd0) },
      irisBottom: { value: c3(look.iris_bottom ?? 0x73dcf5) },
      blush: { value: new THREE.Color(1.0, 0.65, 0.7) },
      mouth: { value: new THREE.Color(0.55, 0.18, 0.25) },
      tongue: { value: new THREE.Color(0.98, 0.55, 0.6) },
      lightView,
      blink: { value: 0 },
      eyeScale: { value: look.body === "m" ? 0.86 : 1.04 },
    },
  });
}

/** Bright unlit color (glows, gems). */
export function glow(color: THREE.ColorRepresentation): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({ color: c3(color) });
}

/** Additive, transparent unlit material for flashes, rings and trails. */
export function additive(color: THREE.ColorRepresentation, opacity = 1): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({
    color: c3(color),
    transparent: true,
    opacity,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}
