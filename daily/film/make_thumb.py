"""Thumbnail for the DISCIPLINE film: summit-at-sunrise frame + bold hook text, 1280x720."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_film as mf

mf.TEXTS = []  # clean frame, no captions
img = Image.fromarray(mf.frame(143.0)).convert("RGB")
# push the frame warmer and brighter for a small-size thumbnail
a = np.asarray(img, np.float32)
a = np.clip((a - 10) * 1.25 + np.array([18, 6, -6]), 0, 255).astype(np.uint8)
img = Image.fromarray(a)
d = ImageDraw.Draw(img)
big = ImageFont.truetype(mf.F_BOLD, 150)
small = ImageFont.truetype(mf.F_BOLD, 74)


def shout(txt, f, y, fill, x=None):
    w = d.textlength(txt, font=f)
    x = (mf.W - w) / 2 if x is None else x
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).text((x + 8, y + 10), txt, font=f, fill=230)
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    img.paste((0, 0, 0), mask=sh)
    d.text((x, y), txt, font=f, fill=fill, stroke_width=6, stroke_fill=(10, 8, 16))


shout("DISCIPLINE", big, 70, (255, 255, 255), x=70)
shout("> TALENT", big, 240, (255, 196, 92), x=70)
shout("NOBODY'S WATCHING AT 5 AM.", small, 940, (240, 240, 240))
out = os.path.join(mf.ROOT, "daily/out/05-discipline-film-thumb.jpg")
img.resize((1280, 720), Image.LANCZOS).save(out, quality=92)
print(out, os.path.getsize(out))
