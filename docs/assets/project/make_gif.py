"""
Creates two outputs:
  1. Animated GIF  — SMAP (left) | AE (right), one frame per year.
  2. Static PNG    — SMAP top row / AE bottom row, one column per year.
Run from any directory:
    python docs/assets/project/make_gif.py
Requires: pip install Pillow
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
AE_DIR   = BASE / "AE"
SMAP_DIR = BASE / "SMAP"
OUT_GIF    = BASE / "soil_moisture_comparison.gif"
OUT_STATIC = BASE / "soil_moisture_timeline.png"

YEARS = sorted(
    int(p.stem.split("-")[1])
    for p in AE_DIR.glob("AE-*.png")
    if (SMAP_DIR / f"SMAP-{p.stem.split('-')[1]}.png").exists()
)

FRAME_HEIGHT  = 512   # px; both images are resized to this height
LABEL_HEIGHT  = 40    # px reserved above each frame for the year + source labels
GAP           = 8     # px gap between the two images
DURATION_MS   = 900   # ms per frame
BG_COLOR      = (20, 20, 20)
TEXT_COLOR    = (255, 255, 255)

try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
except OSError:
    font = ImageFont.load_default()
    small_font = font


def load_resized(path: Path, height: int) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    ratio = height / img.height
    return img.resize((int(img.width * ratio), height), Image.LANCZOS)


frames = []
for year in YEARS:
    ae   = load_resized(AE_DIR   / f"AE-{year}.png",   FRAME_HEIGHT)
    smap = load_resized(SMAP_DIR / f"SMAP-{year}.png", FRAME_HEIGHT)

    total_w = smap.width + GAP + ae.width
    total_h = LABEL_HEIGHT + FRAME_HEIGHT

    frame = Image.new("RGBA", (total_w, total_h), BG_COLOR)
    draw  = ImageDraw.Draw(frame)

    # Year centred at top
    draw.text((total_w // 2, 4), str(year), fill=TEXT_COLOR, font=font, anchor="mt")

    # Source labels under the year
    draw.text((smap.width // 2, 24), "SMAP", fill=(180, 180, 255), font=small_font, anchor="mt")
    draw.text((smap.width + GAP + ae.width // 2, 24), "AlphaEarth", fill=(180, 255, 180), font=small_font, anchor="mt")

    # Paste the two images
    frame.paste(smap, (0,              LABEL_HEIGHT))
    frame.paste(ae,   (smap.width + GAP, LABEL_HEIGHT))

    frames.append(frame.convert("RGB"))

if not frames:
    raise SystemExit("No matching year pairs found in AE/ and SMAP/ directories.")

frames[0].save(
    OUT_GIF,
    save_all=True,
    append_images=frames[1:],
    duration=DURATION_MS,
    loop=0,           # loop forever
    optimize=False,
)

print(f"Saved {len(frames)} frames → {OUT_GIF}")

# ── Static timeline: SMAP top row, AE bottom row ─────────────────────────────
THUMB_H      = 256   # height of each thumbnail in the static image
COL_LABEL_H  = 28    # space above each column for the year number
ROW_LABEL_W  = 80    # space to the left of each row for the source label
COL_GAP      = 6     # horizontal gap between columns
ROW_GAP      = 6     # vertical gap between rows

ae_imgs   = [load_resized(AE_DIR   / f"AE-{y}.png",   THUMB_H) for y in YEARS]
smap_imgs = [load_resized(SMAP_DIR / f"SMAP-{y}.png", THUMB_H) for y in YEARS]

col_w  = max(img.width for img in ae_imgs + smap_imgs)
n_cols = len(YEARS)

total_w = ROW_LABEL_W + n_cols * col_w + (n_cols - 1) * COL_GAP
total_h = COL_LABEL_H + 2 * THUMB_H + ROW_GAP

static = Image.new("RGB", (total_w, total_h), BG_COLOR)
draw   = ImageDraw.Draw(static)

# Row labels
draw.text((ROW_LABEL_W // 2, COL_LABEL_H + THUMB_H // 2),
          "SMAP", fill=(180, 180, 255), font=font, anchor="mm")
draw.text((ROW_LABEL_W // 2, COL_LABEL_H + THUMB_H + ROW_GAP + THUMB_H // 2),
          "AE",   fill=(180, 255, 180), font=font, anchor="mm")

for i, year in enumerate(YEARS):
    x = ROW_LABEL_W + i * (col_w + COL_GAP)

    # Year label centred above each column
    draw.text((x + col_w // 2, COL_LABEL_H // 2),
              str(year), fill=TEXT_COLOR, font=small_font, anchor="mm")

    # SMAP top row, AE bottom row
    static.paste(smap_imgs[i], (x, COL_LABEL_H))
    static.paste(ae_imgs[i],   (x, COL_LABEL_H + THUMB_H + ROW_GAP))

static.save(OUT_STATIC)
print(f"Saved static timeline  → {OUT_STATIC}")
