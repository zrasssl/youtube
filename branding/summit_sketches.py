"""SUMMIT SKETCHES channel art: banner (2560x1440) + avatar (800x800), drawn in code.

Look: a dawn mountain scene drawn like a coloured-pencil sketch: wobbly multi-pass outlines,
hatching on the slopes, a dashed trail up to the summit, a climber with an orange flag, paper grain.
Banner content sits in YouTube's visible strip (2560x423, y 508..931); title and climber stay in the
1546px phone-safe box. Fonts: Inter (system) + Caveat / Permanent Marker (OFL, branding/fonts).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "daily", "film"))
import make_film as mf  # stick figure

INTER_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
INTER_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
CAVEAT = os.path.join(HERE, "fonts", "Caveat-Bold.woff")

INK = (20, 15, 34)
WARM = (255, 176, 96)
FLAG = (255, 128, 64)
RNG = np.random.default_rng(2026)


# ------------------------------------------------------------------ helpers
def sky(w, h, horizon, sun, glow_r):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    hz = horizon / h
    k = np.clip(y / hz, 0, 1)
    top, mid, low = (np.array(c, np.float32) for c in ((13, 12, 36), (96, 52, 108), (255, 160, 86)))
    a = np.clip(k / 0.72, 0, 1) ** 1.6
    b = np.clip((k - 0.72) / 0.28, 0, 1) ** 1.3
    col = top * (1 - a) + mid * a
    col = col * (1 - b) + low * b
    d2 = ((x * w - sun[0]) / glow_r) ** 2 + ((y * h - sun[1]) / (glow_r * 0.6)) ** 2
    col = col + np.exp(-d2) * np.array([120, 76, 30], np.float32)
    return col


def paper(arr, strength=7.0, seed=1):
    r = np.random.default_rng(seed)
    h, w = arr.shape[:2]
    n = r.normal(0, 1, (h // 2 + 1, w // 2 + 1)).astype(np.float32)
    n = np.kron(n, np.ones((2, 2), np.float32))[:h, :w]
    fibers = np.zeros((h, w), np.float32)
    for _ in range(int(w * h / 9000)):
        y0, x0 = r.integers(0, h), r.integers(0, w)
        ln = r.integers(10, 40)
        fibers[y0, x0:x0 + ln] += r.uniform(-1, 1)
    return np.clip(arr + (n * strength + fibers * 6)[..., None], 0, 255)


def wobble(pts, amp, seed, step=10):
    """Resample a polyline and push each point a little off the line, like a hand-drawn stroke."""
    r = np.random.default_rng(seed)
    out = []
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(n):
            t = i / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    out.append(pts[-1])
    off = np.cumsum(r.normal(0, amp * 0.35, (len(out), 2)), 0)
    off -= np.linspace(off[0], off[-1], len(out))  # keep the ends in place
    off = np.clip(off, -amp, amp)
    return [(x + dx, y + dy) for (x, y), (dx, dy) in zip(out, off)]


def sketch_line(layer, pts, col, width, alpha=200, passes=3, amp=3.0, seed=0):
    d = ImageDraw.Draw(layer)
    for p in range(passes):
        a = int(alpha * (1.0 if p == 0 else 0.45))
        d.line(wobble(pts, amp, seed * 31 + p), fill=col + (a,), width=max(1, int(width * (1 if p == 0 else 0.6))), joint="curve")


def sketch_circle(layer, c, r, col, width, alpha=200, passes=2, seed=0, gap=0.0):
    pts = []
    rr = np.random.default_rng(seed)
    start = rr.random() * 6.28
    span = 2 * math.pi * (1.04 - gap)
    for i in range(181):
        a = start + span * i / 180
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    sketch_line(layer, pts, col, width, alpha, passes, amp=r * 0.012 + 1.5, seed=seed)


def hatch(layer, poly, angle, spacing, col, alpha, width=2, seed=0, density=1.0, box=None):
    """Pencil hatching clipped to a polygon."""
    w, h = layer.size
    tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = box or (0, 0, w, h)
    ca, sa = math.cos(angle), math.sin(angle)
    diag = math.hypot(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    off = -diag / 2
    while off < diag / 2:
        if r.random() < density:
            px, py = cx - sa * off, cy + ca * off
            a = r.uniform(-diag / 2, 0)
            b = r.uniform(0, diag / 2)
            p0 = (px + ca * a, py + sa * a)
            p1 = (px + ca * b, py + sa * b)
            d.line([p0, p1], fill=col + (int(alpha * r.uniform(0.5, 1.0)),), width=width)
        off += spacing * r.uniform(0.7, 1.3)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    tmp.putalpha(Image.fromarray(np.minimum(np.asarray(tmp.getchannel("A")), np.asarray(m))))
    layer.alpha_composite(tmp)


def ridge(w, base, amp, freqs, seed, peak=None, x0=0):
    r = np.random.default_rng(seed)
    xs = np.arange(x0, w + 1, 6, dtype=np.float32)
    ys = np.full(xs.shape, float(base))
    for f in freqs:
        ys += amp / f * np.sin(xs / w * 2 * math.pi * f + r.random() * 6.28)
    if peak:
        px, py, half = peak
        ys = np.minimum(ys, py + np.abs(xs - px) * (base - py) / half + 6 * np.sin(xs / 37))
    return [(float(a), float(b)) for a, b in zip(xs, ys)]


def text_layer(size, txt, font, fill, spacing=0, angle=0, shadow=True):
    w, h = size
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = 0
    for ch in txt:
        d.text((x, 0), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + spacing
    if angle:
        lay = lay.rotate(angle, resample=Image.BICUBIC, expand=False, center=(x / 2, font.size * 0.6))
    if shadow:
        a = lay.getchannel("A").filter(ImageFilter.GaussianBlur(10))
        sh = Image.new("RGBA", (w, h), (8, 4, 16, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.75)))
        sh2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh2.alpha_composite(sh, (6, 8))
        sh2.alpha_composite(lay)
        lay = sh2
    return lay, x


def climber(layer, peak, s, flag_col=FLAG):
    d = ImageDraw.Draw(layer)
    mf.figure(d, peak[0], peak[1] + 2, s, "up", col=INK + (255,))
    fx = peak[0] + s * 0.30
    pole_top = peak[1] - s * 0.98
    d.line([fx, peak[1] + 2, fx, pole_top], fill=INK + (255,), width=max(3, int(s * 0.045)))
    wv = s * 0.03
    d.polygon([(fx, pole_top), (fx + s * 0.62, pole_top + s * 0.12 + wv), (fx + s * 0.55, pole_top + s * 0.2),
               (fx, pole_top + s * 0.3)], fill=flag_col + (255,))
    sketch_line(layer, [(fx, pole_top), (fx + s * 0.62, pole_top + s * 0.12 + wv), (fx, pole_top + s * 0.3)],
                (120, 40, 20), max(2, int(s * 0.012)), alpha=180, passes=2, amp=1.2, seed=77)


def birds(layer, pts, size, seed=0):
    for i, (x, y) in enumerate(pts):
        s = size * (0.7 + 0.3 * ((i * 37) % 5) / 4)
        sketch_line(layer, [(x - s, y - s * 0.35), (x - s * 0.45, y - s * 0.55), (x, y)], INK, 3, 210, 2, 0.8, seed + i)
        sketch_line(layer, [(x, y), (x + s * 0.45, y - s * 0.55), (x + s, y - s * 0.35)], INK, 3, 210, 2, 0.8, seed + i + 50)


def scene(W, H, horizon, sun, sun_r, peak, ranges, trail, stars_until, seed=0, clouds=True, rings=(1.0, 1.18, 1.42)):
    """Shared landscape: returns an RGBA image."""
    base = sky(W, H, horizon, sun, sun_r * 6)
    base = paper(base, 6.0, seed)
    img = Image.fromarray(base.astype(np.uint8)).convert("RGBA")
    ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    r = np.random.default_rng(seed + 5)
    # stars as tiny pencil crosses
    for _ in range(int(W * stars_until / 5200)):
        x, y = r.random() * W, r.random() * stars_until
        a = int(220 * (1 - y / (stars_until * 1.15)))
        s = 2 + 3 * r.random() ** 3
        d.line([x - s, y, x + s, y], fill=(255, 245, 225, a), width=2)
        d.line([x, y - s, x, y + s], fill=(255, 245, 225, a), width=2)
    # sun: soft halo, disc, sketched rings and rays
    halo = Image.new("L", (W, H), 0)
    ImageDraw.Draw(halo).ellipse([sun[0] - sun_r * 1.9, sun[1] - sun_r * 1.9, sun[0] + sun_r * 1.9, sun[1] + sun_r * 1.9], fill=110)
    img.alpha_composite(Image.new("RGBA", (W, H), (255, 200, 130, 0)) if False else Image.merge("RGBA", (
        Image.new("L", (W, H), 255), Image.new("L", (W, H), 205), Image.new("L", (W, H), 140), halo.filter(ImageFilter.GaussianBlur(sun_r * 0.5)))))
    d.ellipse([sun[0] - sun_r, sun[1] - sun_r, sun[0] + sun_r, sun[1] + sun_r], fill=(255, 226, 168, 255))
    for i, rr in enumerate(rings):
        sketch_circle(ink, sun, sun_r * rr, (255, 214, 150), max(2, int(sun_r * 0.025)), alpha=210 - i * 55, seed=seed + i, gap=0.12 * i)
    for i in range(22):
        ang = math.pi + (i + 0.5) / 22 * math.pi
        a0, a1 = sun_r * (1.62 + 0.1 * (i % 2)), sun_r * (2.4 + 0.55 * (i % 3))
        sketch_line(ink, [(sun[0] + a0 * math.cos(ang), sun[1] + a0 * math.sin(ang)),
                          (sun[0] + a1 * math.cos(ang), sun[1] + a1 * math.sin(ang))],
                    (255, 205, 140), max(2, int(sun_r * 0.022)), alpha=150, passes=1, amp=1.0, seed=seed + 100 + i)
    # clouds: long thin pencil streaks across the sun
    for j, (cy, cx0, cx1) in enumerate(() if not clouds else ((sun[1] - sun_r * 0.25, sun[0] - sun_r * 2.6, sun[0] + sun_r * 1.4),
                                         (sun[1] + sun_r * 0.22, sun[0] - sun_r * 1.2, sun[0] + sun_r * 2.8))):
        th = sun_r * 0.11
        poly = [(cx0, cy), (cx0 + (cx1 - cx0) * 0.2, cy - th), (cx1 - (cx1 - cx0) * 0.25, cy - th * 0.8), (cx1, cy),
                (cx1 - (cx1 - cx0) * 0.3, cy + th * 0.6), (cx0 + (cx1 - cx0) * 0.25, cy + th * 0.5)]
        d.polygon(poly, fill=(236, 138, 128, 150))
        sketch_line(ink, poly + [poly[0]], (255, 190, 170), 2, 150, 2, 2.0, seed + 300 + j)
    img.alpha_composite(ink)
    ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # mountain ranges (far -> near) with hatching and wobbly outlines
    for n, (pts, fill, line, hatch_ang, hatch_alpha) in enumerate(ranges):
        poly = pts + [(W, H), (0, H)]
        ImageDraw.Draw(ink).polygon(poly, fill=fill + (255,))
        hatch(ink, poly, hatch_ang, 11 + n * 2, tuple(min(255, c + 40) for c in fill), hatch_alpha, 2, seed + 10 + n)
        sketch_line(ink, pts, line, 3 if n < 2 else 4, 200, 2, 2.5, seed + 20 + n)
    # rim light on the near ridge around the summit
    near = ranges[-1][0]
    rim = [p for p in near if abs(p[0] - peak[0]) < sun_r * 3.2]
    sketch_line(ink, rim, WARM, 5, 230, 2, 1.5, seed + 40)
    # dashed trail up the near mountain
    tr = wobble(trail, 4, seed + 60, step=8)
    for i in range(0, len(tr) - 2, 4):
        ImageDraw.Draw(ink).line([tr[i], tr[i + 2]], fill=(255, 196, 130, 230), width=5)
    img.alpha_composite(ink)
    return img


# ------------------------------------------------------------------ banner
def banner():
    W, H = 2560, 1440
    SY0, SY1 = 508, 931
    sun, sun_r = (1770, 742), 120
    peak = (1770, 676)
    ranges = [
        (ridge(W, 790, 150, [1.2, 2.9, 7.3], 3), (104, 62, 110), (150, 100, 150), 0.6, 70),
        (ridge(W, 850, 120, [1.6, 4.1, 9.7], 6), (62, 38, 78), (120, 80, 130), -0.7, 75),
        (ridge(W, 915, 50, [2.3, 6.1, 14.0], 8, peak=(peak[0], peak[1], 460)), (24, 17, 38), (90, 62, 104), 0.9, 90),
    ]
    trail = [(1440, 935), (1540, 872), (1490, 830), (1620, 780), (1590, 742), (1705, 712), (peak[0] - 18, peak[1] + 4)]
    img = scene(W, H, 905, sun, sun_r, peak, ranges, trail, stars_until=640, seed=11)
    ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    climber(ink, peak, 118)
    birds(ink, [(1560, 600), (1615, 575), (1650, 612)], 22, seed=5)
    img.alpha_composite(ink)

    # ---- title block (inside the phone-safe box, x >= 507)
    x0 = 560
    f_title = ImageFont.truetype(INTER_BLACK, 158)
    t, tw = text_layer((1200, 240), "SUMMIT", f_title, (255, 255, 255, 255), spacing=8)
    img.alpha_composite(t, (x0, 522))
    f_script = ImageFont.truetype(CAVEAT, 150)
    s, sw = text_layer((800, 260), "Sketches", f_script, WARM + (255,), spacing=2, angle=4)
    img.alpha_composite(s, (x0 + 360, 628))
    ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # hand-drawn swoosh under "Sketches"
    sw_pts = [(x0 + 380, 796), (x0 + 520, 790), (x0 + 660, 778), (x0 + 790, 760), (x0 + 850, 750)]
    sketch_line(ink, sw_pts, WARM, 7, 235, 3, 2.2, 501)
    # small pencil sparkles near the title
    for (cx, cy, s0) in ((x0 - 22, 548, 18), (x0 + 905, 556, 14)):
        for a in (0, math.pi / 2):
            sketch_line(ink, [(cx - s0 * math.cos(a), cy - s0 * math.sin(a)), (cx + s0 * math.cos(a), cy + s0 * math.sin(a))],
                        (255, 226, 168), 4, 230, 2, 0.8, int(cx))
    img.alpha_composite(ink)
    f_tag = ImageFont.truetype(INTER_SEMI, 44)
    tg, _ = text_layer((900, 70), "Animated stories for the climb.", f_tag, (238, 232, 246, 255))
    img.alpha_composite(tg, (x0 + 6, 812))
    f_small = ImageFont.truetype(INTER_BOLD, 28)
    sm, _ = text_layer((900, 50), "MOTIVATION  •  ANIMATION  •  MINDSET", f_small, (255, 214, 160, 255), spacing=3)
    img.alpha_composite(sm, (x0 + 8, 878))

    img = img.convert("RGB")
    img.save(os.path.join(HERE, "banner.png"), optimize=True)
    img.crop((0, SY0, W, SY1)).resize((1280, 212), Image.LANCZOS).save(os.path.join(HERE, "banner_preview_desktop.jpg"), quality=90)
    img.crop((507, SY0, 2053, SY1)).resize((1030, 282), Image.LANCZOS).save(os.path.join(HERE, "banner_preview_phone.jpg"), quality=90)
    img.resize((1280, 720), Image.LANCZOS).save(os.path.join(HERE, "banner_preview_tv.jpg"), quality=88)


# ------------------------------------------------------------------ avatar
def avatar():
    S = 800
    sun, sun_r = (400, 405), 165
    peak = (400, 452)
    ranges = [
        (ridge(S, 560, 70, [1.1, 2.7], 21), (104, 62, 110), (150, 100, 150), 0.6, 70),
        (ridge(S, 620, 60, [1.5, 3.3], 24), (62, 38, 78), (120, 80, 130), -0.7, 80),
        (ridge(S, 790, 10, [2.1], 27, peak=(peak[0], peak[1], 330)), (24, 17, 38), (90, 62, 104), 0.9, 95),
    ]
    trail = [(240, 800), (330, 720), (290, 650), (370, 560), (345, 515), (peak[0] - 12, peak[1] + 4)]
    img = scene(S, S, 640, sun, sun_r, peak, ranges, trail, stars_until=230, seed=31, clouds=False, rings=(1.0, 1.2))
    ink = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    climber(ink, peak, 205)
    birds(ink, [(600, 250), (650, 228)], 20, seed=9)
    # hand-drawn frame just inside the circle crop
    sketch_circle(ink, (S / 2, S / 2), 372, (255, 214, 160), 9, alpha=235, passes=3, seed=88)
    img.alpha_composite(ink)
    img = img.convert("RGB")
    img.save(os.path.join(HERE, "avatar.png"), optimize=True)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, S - 1, S - 1], fill=255)
    pv = Image.new("RGB", (660, 230), (255, 255, 255))
    ImageDraw.Draw(pv).rectangle([330, 0, 660, 230], fill=(15, 15, 15))
    for ox in (0, 330):
        xx = ox + 14
        for size in (176, 88, 40):
            pv.paste(img.resize((size, size), Image.LANCZOS), (xx, (230 - size) // 2), mask.resize((size, size), Image.LANCZOS))
            xx += size + 12
    pv.save(os.path.join(HERE, "avatar_preview.png"))


if __name__ == "__main__":
    banner()
    avatar()
    print("ok")
