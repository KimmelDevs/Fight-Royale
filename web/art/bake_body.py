"""Bake a game-ready character GLB from an untextured image-to-3D mesh.

Usage: python art/bake_body.py <mesh.glb> <front.png> <back.png> <out.glb> [faces=24000]

- Decimates the mesh (fast-simplification) to `faces` triangles.
- Projects the front reference onto front-facing triangles and the back reference onto
  back-facing ones (orthographic, aligned by each image's character bounding box), packed
  side by side in one texture atlas. Keeps the reference art's face and eyes crisp.
- Mesh convention: character faces +Z, feet at the lowest Y.
"""
import io, sys
import numpy as np
import trimesh
import fast_simplification
from PIL import Image


def char_box(img: Image.Image):
    """Bounding box (x0, y0, x1, y1) of the non-background pixels (flat background)."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    bg = np.median(np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3)]), axis=0)
    mask = np.abs(a - bg).sum(axis=2) > 40
    ys, xs = np.nonzero(mask)
    # Robust to stray pixels.
    return (np.percentile(xs, 0.2), np.percentile(ys, 0.2), np.percentile(xs, 99.8), np.percentile(ys, 99.8))


def bleed(img: Image.Image, steps=48) -> Image.Image:
    """Spreads the character's edge colors into the flat background, so triangles seen
    edge-on (sides of limbs) never sample the grey backdrop."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    bg = np.median(np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3)]), axis=0)
    known = np.abs(a - bg).sum(axis=2) > 40
    for _ in range(steps):
        acc = np.zeros_like(a); cnt = np.zeros(a.shape[:2], np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = np.roll(known, (dy, dx), (0, 1)); c = np.roll(a, (dy, dx), (0, 1))
            acc += c * k[..., None]; cnt += k
        grow = (~known) & (cnt > 0)
        a[grow] = acc[grow] / cnt[grow][:, None]
        known |= grow
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def main():
    src, front_p, back_p, out = sys.argv[1:5]
    faces_target = int(sys.argv[5]) if len(sys.argv) > 5 else 24000
    mesh = trimesh.load(src, force="mesh")
    v, f = np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces, np.int64)
    ratio = 1 - faces_target / len(f)
    if ratio > 0:
        v, f = fast_simplification.simplify(v, f.astype(np.int32), target_reduction=ratio)
    m = trimesh.Trimesh(v, f, process=True)
    print("faces", len(m.faces), "verts", len(m.vertices))

    front, back = Image.open(front_p).convert("RGB"), Image.open(back_p).convert("RGB")
    W, H = front.size
    back = back.resize((W, H), Image.LANCZOS)
    lo, hi = m.bounds
    tri = m.vertices[m.faces]                      # (F, 3, 3)
    nz = m.face_normals[:, 2]
    uv = np.zeros((len(m.faces), 3, 2), np.float32)
    for side, img in ((0, front), (1, back)):
        x0, y0, x1, y1 = char_box(img)
        sel = (nz >= 0) if side == 0 else (nz < 0)
        p = tri[sel]
        tx = (p[..., 0] - lo[0]) / (hi[0] - lo[0])  # 0 = character's right (-X)
        if side == 1:
            tx = 1 - tx                              # seen from behind, +X is on the left
        ty = (p[..., 1] - lo[1]) / (hi[1] - lo[1])  # 0 = feet
        px = x0 + tx * (x1 - x0)
        py = y1 - ty * (y1 - y0)
        uv[sel, :, 0] = (px / W + side) / 2
        uv[sel, :, 1] = 1 - py / H
    atlas = Image.new("RGB", (W * 2, H))
    atlas.paste(bleed(front), (0, 0)); atlas.paste(bleed(back), (W, 0))
    atlas = atlas.resize((2048, int(2048 * H / (2 * W))), Image.LANCZOS)

    # Split vertices per triangle so each face can sample its own projection.
    vn = m.vertex_normals[m.faces].reshape(-1, 3)
    out_mesh = trimesh.Trimesh(tri.reshape(-1, 3), np.arange(len(m.faces) * 3).reshape(-1, 3),
                               vertex_normals=vn, process=False)
    buf = io.BytesIO(); atlas.save(buf, "JPEG", quality=88); buf.seek(0)
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.open(buf), metallicFactor=0, roughnessFactor=1)
    out_mesh.visual = trimesh.visual.TextureVisuals(uv=uv.reshape(-1, 2), material=mat)
    out_mesh.merge_vertices(merge_tex=False, merge_norm=True)  # re-share verts with equal UVs
    print("verts after merge", len(out_mesh.vertices))
    out_mesh.export(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
