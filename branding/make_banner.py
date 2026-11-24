"""RASLHUSTLE channel banner, 2560x1440.

YouTube shows the centred 2560x423 strip on desktop (y 508..931) and the centred 1546x423 box on
phones, so the whole composition lives in that strip; the rest only extends the scene for TV.
Writes branding/banner.png plus desktop / phone crop previews.
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "daily", "film"))
import make_film as mf  # stick figure

W, H = 2560, 1440
SAFE_Y0, SAFE_Y1 = 508, 931
SAFE_X0, SAFE_X1 = (W - 1546) // 2, (W + 1546) // 2
BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
SUN = (1880, 800)

# ---- sky: deep night at the top, warm dawn at the horizon, glow around the sun
y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
x = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
hz = 830 / H
k = np.clip(y / hz, 0, 1) ** 2.2
sky = np.array([10, 9, 26], np.float32) * (1 - k) + np.array([120, 58, 92], np.float32) * k
warm = np.clip((y - hz * 0.75) / (hz * 0.25), 0, 1) ** 1.5
sky = sky * (1 - warm) + np.array([250, 140, 72], np.float32) * warm
dx = (x * W - SUN[0]) / 900
dy = (y * H - SUN[1]) / 500
sky = sky + np.exp(-(dx ** 2 + dy ** 2)) * np.array([110, 70, 25], np.float32)
img = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)

# ---- stars in the dark upper part
rng = np.random.default_rng(21)
for _ in range(420):
    sx, sy = rng.random() * W, rng.random() * 700
    v = int((60 + 190 * rng.random()) * (1 - sy / 760))
    r = 1.2 if rng.random() < 0.85 else 2.2
    d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(v, v, min(255, v + 20)))

# ---- soft sun rays + sun
rays = Image.new("L", (W, H), 0)
rd = ImageDraw.Draw(rays)
for i in range(28):
    a = math.pi + i / 27 * math.pi  # upper half only
    rd.polygon([(SUN[0], SUN[1]),
                (SUN[0] + 1500 * math.cos(a - 0.025), SUN[1] + 1500 * math.sin(a - 0.025)),
                (SUN[0] + 1500 * math.cos(a + 0.025), SUN[1] + 1500 * math.sin(a + 0.025))], fill=30)
img.paste((255, 190, 110), mask=rays.filter(ImageFilter.GaussianBlur(16)))
halo = Image.new("L", (W, H), 0)
ImageDraw.Draw(halo).ellipse([SUN[0] - 210, SUN[1] - 210, SUN[0] + 210, SUN[1] + 210], fill=120)
img.paste((255, 205, 140), mask=halo.filter(ImageFilter.GaussianBlur(60)))
d.ellipse([SUN[0] - 115, SUN[1] - 115, SUN[0] + 115, SUN[1] + 115], fill=(255, 222, 160))


# ---- three mountain ranges (far -> near)
def ridge(base, amp, freqs, seed, peak=None):
    r = np.random.default_rng(seed)
    xs = np.arange(0, W + 1, 4)
    ys = np.full(xs.shape, float(base))
    for f in freqs:
        ys += amp / f * np.sin(xs / W * 2 * np.pi * f + r.random() * 6.28)
    if peak:
        px, py, width = peak
        ys = np.minimum(ys, py + np.abs(xs - px) * (base - py) / width)
    return list(zip(xs, ys))


layers = [
    (ridge(780, 140, [1.3, 3.1, 7.7], 2), (78, 44, 78)),
    (ridge(840, 120, [1.7, 4.3, 9.1], 5), (44, 28, 54)),
    (ridge(905, 70, [2.2, 5.9, 13.0], 9, peak=(SUN[0], 735, 420)), (16, 12, 26)),
]
for pts, col in layers:
    d.polygon(pts + [(W, H), (0, H)], fill=col)

# ---- the climber on the near peak, arms up, with a flag
NEAR = (16, 12, 26)
px, py = SUN[0], 737
mf.figure(d, px, py, 120, "up", col=NEAR)
d.line([px + 34, py, px + 34, py - 112], fill=NEAR, width=6)
d.polygon([(px + 34, py - 112), (px + 104, py - 97), (px + 34, py - 80)], fill=NEAR)


# ---- type
def glow_text(xy, txt, f, fill, glow=(0, 0, 0), blur=14, strength=210, spacing=0):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).text((xy[0] + 4, xy[1] + 6), txt, font=f, fill=strength)
    img.paste(glow, mask=m.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text(xy, txt, font=f, fill=fill)


fb = ImageFont.truetype(BLACK if os.path.exists(BLACK) else BOLD, 168)
fs = ImageFont.truetype(SEMI, 54)
ft = ImageFont.truetype(BOLD, 34)
tx = SAFE_X0 + 30
glow_text((tx, 560), "RASLHUSTLE", fb, (255, 255, 255))
glow_text((tx + 6, 765), "A push forward, every day.", fs, (255, 206, 140))
# accent bar + tags
d = ImageDraw.Draw(img)
d.rounded_rectangle([tx + 8, 748, tx + 130, 754], 3, fill=(255, 170, 90))
tags = "MOTIVATION   •   DISCIPLINE   •   MINDSET"
glow_text((tx + 8, 852), tags, ft, (225, 222, 235), blur=8, strength=170)

out = os.path.join(HERE, "banner.png")
img.save(out, optimize=True)
# previews of what YouTube actually shows
img.crop((0, SAFE_Y0, W, SAFE_Y1)).resize((1280, 212)).save(os.path.join(HERE, "banner_preview_desktop.jpg"), quality=88)
img.crop((SAFE_X0, SAFE_Y0, SAFE_X1, SAFE_Y1)).resize((1030, 282)).save(os.path.join(HERE, "banner_preview_phone.jpg"), quality=88)
img.resize((1280, 720)).save(os.path.join(HERE, "banner_preview_tv.jpg"), quality=85)
print(out, os.path.getsize(out))
