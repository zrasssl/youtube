"""RASLHUSTLE avatar, 800x800, matching the banner: dawn sky, big sun, ridges, climber with flag.

YouTube crops it to a circle and shows it as small as ~40px, so the shapes are few and large.
Writes branding/avatar.png and branding/avatar_preview.png (circle crops at real sizes).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "daily", "film"))
import make_film as mf

S = 800
SUN = (400, 430)
y = np.linspace(0, 1, S, dtype=np.float32)[:, None, None]
x = np.linspace(0, 1, S, dtype=np.float32)[None, :, None]
k = np.clip(y / 0.66, 0, 1) ** 2.0
sky = np.array([14, 12, 32], np.float32) * (1 - k) + np.array([250, 140, 72], np.float32) * k
g = np.exp(-(((x * S - SUN[0]) / 330) ** 2 + ((y * S - SUN[1]) / 260) ** 2))
sky = sky + g * np.array([90, 55, 15], np.float32)
img = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)

rng = np.random.default_rng(4)
for _ in range(60):
    sx, sy = rng.random() * S, rng.random() * 220
    v = int(120 + 120 * rng.random())
    d.ellipse([sx - 1.6, sy - 1.6, sx + 1.6, sy + 1.6], fill=(v, v, v))

rays = Image.new("L", (S, S), 0)
rd = ImageDraw.Draw(rays)
for i in range(16):
    a = math.pi + (i + 0.5) / 16 * math.pi
    rd.polygon([SUN, (SUN[0] + 700 * math.cos(a - 0.05), SUN[1] + 700 * math.sin(a - 0.05)),
                (SUN[0] + 700 * math.cos(a + 0.05), SUN[1] + 700 * math.sin(a + 0.05))], fill=45)
img.paste((255, 195, 120), mask=rays.filter(ImageFilter.GaussianBlur(5)))
halo = Image.new("L", (S, S), 0)
ImageDraw.Draw(halo).ellipse([SUN[0] - 230, SUN[1] - 230, SUN[0] + 230, SUN[1] + 230], fill=140)
img.paste((255, 205, 140), mask=halo.filter(ImageFilter.GaussianBlur(40)))
d.ellipse([SUN[0] - 170, SUN[1] - 170, SUN[0] + 170, SUN[1] + 170], fill=(255, 222, 160))

# far ridge, mid ridge, near peak centred under the sun
d.polygon([(0, 560), (150, 500), (260, 540), (560, 470), (800, 540), (800, 800), (0, 800)], fill=(78, 44, 78))
d.polygon([(0, 620), (200, 560), (330, 600), (520, 570), (800, 610), (800, 800), (0, 800)], fill=(44, 28, 54))
NEAR = (16, 12, 26)
peak = (400, 470)
d.polygon([(30, 800), peak, (770, 800)], fill=NEAR)
mf.figure(d, peak[0], peak[1] + 2, 230, "up", col=NEAR)
d.line([peak[0] + 64, peak[1] + 2, peak[0] + 64, peak[1] - 210], fill=NEAR, width=11)
d.polygon([(peak[0] + 64, peak[1] - 210), (peak[0] + 190, peak[1] - 182), (peak[0] + 64, peak[1] - 150)], fill=NEAR)

img.save(os.path.join(HERE, "avatar.png"), optimize=True)

# preview: circle crops at 176 / 88 / 40 px on a white and a dark page
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).ellipse([0, 0, S - 1, S - 1], fill=255)
pv = Image.new("RGB", (640, 220), (255, 255, 255))
ImageDraw.Draw(pv).rectangle([320, 0, 640, 220], fill=(15, 15, 15))
for ox in (0, 320):
    xx = ox + 15
    for size in (176, 88, 40):
        a = img.resize((size, size), Image.LANCZOS)
        pv.paste(a, (xx, (220 - size) // 2), mask.resize((size, size), Image.LANCZOS))
        xx += size + 12
pv.save(os.path.join(HERE, "avatar_preview.png"))
print("ok")
