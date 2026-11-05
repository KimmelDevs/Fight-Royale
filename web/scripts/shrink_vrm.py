"""Shrink a VRM/GLB for the web: downscale its textures, keep everything else byte-identical.

Usage: python scripts/shrink_vrm.py <in.vrm> <out.vrm> [max_size=1024]

Images larger than max_size are resized (keeping aspect), the thumbnail goes to 256 px, and
all PNGs are re-encoded with optimization. Buffer views are repacked; meshes, skins, VRM
extensions (humanoid, spring bones, MToon, expressions) are untouched.
"""
import io, json, struct, sys
from PIL import Image


def main():
    src, dst = sys.argv[1], sys.argv[2]
    max_size = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    data = open(src, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    boff = 20 + jlen
    blen = struct.unpack("<I", data[boff:boff + 4])[0]
    binc = data[boff + 8:boff + 8 + blen]

    thumb = None
    ext = j.get("extensions", {})
    if "VRMC_vrm" in ext:
        thumb = ext["VRMC_vrm"].get("meta", {}).get("thumbnailImage")

    replaced = {}
    for idx, im in enumerate(j.get("images", [])):
        if "bufferView" not in im:
            continue
        bv = j["bufferViews"][im["bufferView"]]
        raw = binc[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]]
        img = Image.open(io.BytesIO(raw))
        limit = 256 if idx == thumb else max_size
        if max(img.size) > limit:
            k = limit / max(img.size)
            img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
        out = io.BytesIO()
        if im.get("mimeType") == "image/jpeg":
            img.convert("RGB").save(out, "JPEG", quality=90)
        else:
            img.save(out, "PNG", optimize=True)
        if len(out.getvalue()) < len(raw):
            replaced[im["bufferView"]] = out.getvalue()

    # Repack every buffer view in order, 4-byte aligned.
    new = bytearray()
    for i, bv in enumerate(j["bufferViews"]):
        chunk = replaced.get(i)
        if chunk is None:
            o = bv.get("byteOffset", 0)
            chunk = binc[o:o + bv["byteLength"]]
        while len(new) % 4:
            new.append(0)
        bv["byteOffset"] = len(new)
        bv["byteLength"] = len(chunk)
        new += chunk
    while len(new) % 4:
        new.append(0)
    j["buffers"][0]["byteLength"] = len(new)

    js = json.dumps(j, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(new)
    with open(dst, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(new), 0x004E4942)); f.write(new)
    print(f"{src} {len(data)/1e6:.1f} MB -> {dst} {total/1e6:.1f} MB ({len(replaced)} images shrunk)")


if __name__ == "__main__":
    main()
