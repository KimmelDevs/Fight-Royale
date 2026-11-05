"""Slice a 4x4 icon sheet (from ChatGPT image generation) into round 128 px WebP icons.

Usage (from the web folder):
  python scripts/slice_icons.py <sheet.png> <out_dir> name1 name2 ... name16

The 16 names are read row by row (left to right, top to bottom). Use "-" to skip a cell.
Names may include subfolders, e.g. "chars/kira" or "skills/kicks-c". Each icon is cut as a
circle just inside the gold rim, with transparent corners, and saved as <out_dir>/<name>.webp.

Example:
  python scripts/slice_icons.py sheet.png public/icons chars/aster chars/vesper - - ...
"""
import os
import sys

from PIL import Image, ImageDraw

SIZE = 128


def main():
    sheet, out, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    if len(names) != 16:
        sys.exit(f"need 16 names (use - to skip a cell), got {len(names)}")
    img = Image.open(sheet).convert("RGBA")
    w, h = img.size
    cw, ch = w / 4, h / 4
    # Antialiased circular mask, slightly inside the gold rim edge.
    big = SIZE * 4
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((big * 0.035, big * 0.035, big * 0.965, big * 0.965), fill=255)
    mask = mask.resize((SIZE, SIZE), Image.LANCZOS)
    saved = 0
    for i, name in enumerate(names):
        if name == "-":
            continue
        r, c = divmod(i, 4)
        # Icons are circles centered in each cell, about 88% of the cell wide.
        cx, cy = (c + 0.5) * cw, (r + 0.5) * ch
        rad = min(cw, ch) * 0.445
        crop = img.crop((round(cx - rad), round(cy - rad), round(cx + rad), round(cy + rad)))
        crop = crop.resize((SIZE, SIZE), Image.LANCZOS)
        crop.putalpha(mask)
        path = os.path.join(out, name + ".webp")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        crop.save(path, "WEBP", quality=86, method=6)
        saved += 1
    print("saved", saved, "icons to", out)


if __name__ == "__main__":
    main()
