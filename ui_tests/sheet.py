# Tiles screenshots into labelled contact sheets for visual review.
import sys
from pathlib import Path

from PIL import Image, ImageDraw

src, out_prefix, per_sheet = Path(sys.argv[1]), sys.argv[2], 8
COLS, THUMB_W, THUMB_H, LABEL_H = 2, 720, 450, 22

shots = sorted(p for p in src.glob("*.png") if "__" in p.name)
for start in range(0, len(shots), per_sheet):
	batch = shots[start : start + per_sheet]
	rows = (len(batch) + COLS - 1) // COLS
	sheet = Image.new("RGB", (COLS * THUMB_W, rows * (THUMB_H + LABEL_H)), "white")
	draw = ImageDraw.Draw(sheet)
	for i, path in enumerate(batch):
		x, y = (i % COLS) * THUMB_W, (i // COLS) * (THUMB_H + LABEL_H)
		sheet.paste(Image.open(path).convert("RGB").resize((THUMB_W, THUMB_H)), (x, y + LABEL_H))
		draw.text((x + 6, y + 4), path.stem, fill="black")
	sheet.save(f"{out_prefix}_{start // per_sheet + 1}.png")
	print(f"{out_prefix}_{start // per_sheet + 1}.png", [p.stem for p in batch])
