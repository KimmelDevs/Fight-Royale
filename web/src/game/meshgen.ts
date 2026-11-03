// Procedural geometry for cloth sheets and hair strands, with UVs and counter-clockwise
// (three.js front-face) winding so toon fill + back-face outline work.
import * as THREE from "three";

type V = THREE.Vector3;

function pushTri(pos: number[], nrm: number[], uv: number[], p: V[], n: V[], t: THREE.Vector2[], expected: V) {
  const e1 = new THREE.Vector3().subVectors(p[1], p[0]);
  const e2 = new THREE.Vector3().subVectors(p[2], p[0]);
  // CCW (as seen from the outside) means the geometric normal points along `expected`.
  const order = e1.cross(e2).dot(expected) >= 0 ? [0, 1, 2] : [0, 2, 1];
  for (const i of order) {
    pos.push(p[i].x, p[i].y, p[i].z);
    nrm.push(n[i].x, n[i].y, n[i].z);
    uv.push(t[i].x, t[i].y);
  }
}

function build(pos: number[], nrm: number[], uv: number[]): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  return g;
}

/**
 * Cone-shaped sheet hanging down from y = 0 (skirts, sleeves, capes).
 * Angles are radians around Y with 0 = +Z (front). UV.x runs a0 -> a1, UV.y runs top -> hem.
 */
export function coneSheet(
  topR: number, bottomR: number, height: number, a0 = 0, a1 = Math.PI * 2,
  segA = 32, segV = 6, ruffleAmp = 0, ruffleFreq = 0, extraLen?: (a: number) => number,
): THREE.BufferGeometry {
  const closed = Math.abs(a1 - a0 - Math.PI * 2) < 1e-4;
  const grid: V[][] = [];
  for (let i = 0; i <= segA; i++) {
    const a = a0 + ((a1 - a0) * i) / segA;
    const len = height + (extraLen ? extraLen(a) : 0);
    const col: V[] = [];
    for (let j = 0; j <= segV; j++) {
      const v = j / segV;
      const r = topR + (bottomR - topR) * v + ruffleAmp * Math.sin(a * ruffleFreq) * v * v;
      col.push(new THREE.Vector3(Math.sin(a) * r, -v * len, Math.cos(a) * r));
    }
    grid.push(col);
  }
  const normals: V[][] = [];
  for (let i = 0; i <= segA; i++) {
    const a = a0 + ((a1 - a0) * i) / segA;
    const radial = new THREE.Vector3(Math.sin(a), 0, Math.cos(a));
    const col: V[] = [];
    for (let j = 0; j <= segV; j++) {
      let ip = i + 1, im = i - 1;
      if (closed) {
        if (i === segA) ip = 1;
        if (i === 0) im = segA - 1;
      }
      ip = Math.min(ip, segA);
      im = Math.max(im, 0);
      const du = new THREE.Vector3().subVectors(grid[ip][j], grid[im][j]);
      const dv = new THREE.Vector3().subVectors(grid[i][Math.min(j + 1, segV)], grid[i][Math.max(j - 1, 0)]);
      const n = du.cross(dv).normalize();
      if (n.dot(radial) < 0) n.negate();
      col.push(n);
    }
    normals.push(col);
  }
  const pos: number[] = [], nrm: number[] = [], uv: number[] = [];
  for (let i = 0; i < segA; i++) {
    for (let j = 0; j < segV; j++) {
      const ids = [[i, j], [i + 1, j], [i, j + 1], [i + 1, j + 1]];
      const p = ids.map(([a, b]) => grid[a][b]);
      const n = ids.map(([a, b]) => normals[a][b]);
      const t = ids.map(([a, b]) => new THREE.Vector2(a / segA, b / segV));
      const exp = new THREE.Vector3().addVectors(n[0], n[3]).normalize();
      pushTri(pos, nrm, uv, [p[0], p[1], p[3]], [n[0], n[1], n[3]], [t[0], t[1], t[3]], exp);
      pushTri(pos, nrm, uv, [p[0], p[3], p[2]], [n[0], n[3], n[2]], [t[0], t[3], t[2]], exp);
    }
  }
  return build(pos, nrm, uv);
}

/**
 * Tapered, flattened hair lock along a quadratic bezier p0 -> p1 -> p2.
 * The flat face points away from `center` (the head center), so locks hug the head.
 */
export function strand(
  p0: V, p1: V, p2: V, width: number, thick: number, center = new THREE.Vector3(), seg = 8, sides = 8,
): THREE.BufferGeometry {
  const rings: V[][] = [];
  const ringN: V[][] = [];
  for (let k = 0; k <= seg; k++) {
    const t = k / seg;
    const pos = p0.clone().multiplyScalar((1 - t) * (1 - t))
      .add(p1.clone().multiplyScalar(2 * (1 - t) * t))
      .add(p2.clone().multiplyScalar(t * t));
    const tan = p1.clone().sub(p0).multiplyScalar(2 * (1 - t)).add(p2.clone().sub(p1).multiplyScalar(2 * t)).normalize();
    const out = pos.clone().sub(center);
    const nrm = out.clone().sub(tan.clone().multiplyScalar(out.dot(tan))).normalize();
    const bin = tan.clone().cross(nrm).normalize();
    const s01 = Math.min(Math.max(t / 0.25, 0), 1);
    const taper = Math.pow(1 - t, 0.75) * (0.75 + 0.25 * s01 * s01 * (3 - 2 * s01));
    const ring: V[] = [], norms: V[] = [];
    for (let s = 0; s <= sides; s++) {
      const th = (Math.PI * 2 * s) / sides;
      ring.push(pos.clone()
        .add(bin.clone().multiplyScalar(Math.cos(th) * width * taper))
        .add(nrm.clone().multiplyScalar(Math.sin(th) * thick * taper)));
      norms.push(bin.clone().multiplyScalar(Math.cos(th) / width).add(nrm.clone().multiplyScalar(Math.sin(th) / thick)).normalize());
    }
    rings.push(ring);
    ringN.push(norms);
  }
  const pos: number[] = [], nrm: number[] = [], uv: number[] = [];
  for (let k = 0; k < seg; k++) {
    for (let s = 0; s < sides; s++) {
      const p = [rings[k][s], rings[k][s + 1], rings[k + 1][s], rings[k + 1][s + 1]];
      const n = [ringN[k][s], ringN[k][s + 1], ringN[k + 1][s], ringN[k + 1][s + 1]];
      const t = [new THREE.Vector2(s / sides, k / seg), new THREE.Vector2((s + 1) / sides, k / seg),
        new THREE.Vector2(s / sides, (k + 1) / seg), new THREE.Vector2((s + 1) / sides, (k + 1) / seg)];
      const exp = new THREE.Vector3().addVectors(n[0], n[3]).normalize();
      pushTri(pos, nrm, uv, [p[0], p[1], p[3]], [n[0], n[1], n[3]], [t[0], t[1], t[3]], exp);
      pushTri(pos, nrm, uv, [p[0], p[3], p[2]], [n[0], n[3], n[2]], [t[0], t[3], t[2]], exp);
    }
  }
  return build(pos, nrm, uv);
}
