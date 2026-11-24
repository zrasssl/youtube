"""Channel branding for RASLHUSTLE: avatar (800x800) and banner (2560x1440, text inside the 1546x423 safe area)."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "daily", "film"))
import make_film as mf  # reuse the stick figure

BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def sky(w, h, horizon):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    top = np.array([16, 14, 34], np.float32)
    mid = np.array([70, 40, 80], np.float32)
    low = np.array([245, 140, 70], np.float32)
    k = np.clip(y / horizon, 0, 1) ** 1.8
    col = top * (1 - k) + (mid * (1 - k) + low * k) * k
    glow = np.exp(-(((x - 0.5) * w / h) ** 2 + (y - horizon) ** 2) / 0.08)
    col = col + glow * np.array([90, 60, 20], np.float32)
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))


def sun_and_peak(img, cx, peak_y, base_y, sun_r, rays=True, fig=1.0):
    d = ImageDraw.Draw(img)
    w, h = img.size
    sy = peak_y - sun_r * 0.35
    if rays:
        for i in range(24):
            a = i / 24 * 2 * math.pi
            d.line([cx + sun_r * 1.25 * math.cos(a), sy + sun_r * 1.25 * math.sin(a),
                    cx + sun_r * 6 * math.cos(a), sy + sun_r * 6 * math.sin(a)], fill=(235, 160, 80), width=max(2, int(sun_r * 0.04)))
    d.ellipse([cx - sun_r, sy - sun_r, cx + sun_r, sy + sun_r], fill=(255, 218, 150))
    span = (base_y - peak_y) * 1.6
    d.polygon([(cx - span, base_y), (cx, peak_y), (cx + span, base_y), (w, base_y), (w, h), (0, h), (0, base_y)], fill=(20, 16, 30))
    s = (base_y - peak_y) * 0.42 * fig
    mf.figure(d, cx, peak_y, s, "up", col=(20, 16, 30))
    d.line([cx + s * 0.27, peak_y, cx + s * 0.27, peak_y - s * 0.95], fill=(20, 16, 30), width=max(3, int(s * 0.04)))
    d.polygon([(cx + s * 0.27, peak_y - s * 0.95), (cx + s * 0.85, peak_y - s * 0.82), (cx + s * 0.27, peak_y - s * 0.66)], fill=(20, 16, 30))
    return d


def text_shadow(img, xy, txt, f, fill, spacing=0):
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).text((xy[0] + 6, xy[1] + 8), txt, font=f, fill=200)
    img.paste((0, 0, 0), mask=sh.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(img).text(xy, txt, font=f, fill=fill)


# ---- avatar 800x800 (shown as a circle)
av = sky(800, 800, 0.72)
sun_and_peak(av, 400, 470, 800, 150, fig=1.0)
f = ImageFont.truetype(BOLD, 150)
d = ImageDraw.Draw(av)
txt = "RH"
text_shadow(av, ((800 - d.textlength(txt, font=f)) / 2, 520), txt, f, (255, 255, 255))
av.save(os.path.join(HERE, "avatar.png"))

# ---- banner 2560x1440; YouTube safe area is the centred 1546x423 box (y 508..931)
bn = sky(2560, 1440, 0.62)
sun_and_peak(bn, 1280 + 520, 640, 900, 120, fig=0.9)
d = ImageDraw.Draw(bn)
fb, fs = ImageFont.truetype(BOLD, 150), ImageFont.truetype(SEMI, 56)
x0 = 1280 - 773 + 40
text_shadow(bn, (x0, 560), "RASLHUSTLE", fb, (255, 255, 255))
text_shadow(bn, (x0 + 6, 750), "A push forward, every day.", fs, (255, 205, 130))
text_shadow(bn, (x0 + 6, 830), "MOTIVATION  •  DISCIPLINE  •  MINDSET", ImageFont.truetype(BOLD, 40), (230, 230, 235))
bn.save(os.path.join(HERE, "banner.png"))
# preview with the safe area marked (not for upload)
pv = bn.copy()
ImageDraw.Draw(pv).rectangle([1280 - 773, 720 - 212, 1280 + 773, 720 + 211], outline=(0, 255, 0), width=4)
pv.resize((1280, 720)).save(os.path.join(HERE, "banner_safe_area_preview.jpg"), quality=85)
print("ok")
