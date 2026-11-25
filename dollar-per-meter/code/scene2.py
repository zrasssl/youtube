"""Сцена «ДЕНЬ 2» в стиле оригинального шорта: плоская 2D-графика, закат, силуэты в шапках.
Рисуется кодом (Pillow) с 2x-сглаживанием, собирается в mp4 через ffmpeg."""
import math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 2                          # supersampling
W, H, FPS, DUR = 1080, 1920, 30, 6.0
OUT = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def F(px): return ImageFont.truetype(FONT, int(px * S))
def P(v): return int(v * S)

CREAM = (255, 243, 205)
DARK = (28, 10, 32)
RED, YELLOW = (232, 78, 40), (240, 190, 40)
MONEY = (226, 150, 20)
GROUND_Y = 1440

def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

def back(x):  # «пружинка» при появлении
    x = max(0.0, min(1.0, x)); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------- статичный фон (небо, звёзды, солнце) ----------
def make_sky():
    img = Image.new("RGB", (W * S, H * S))
    d = ImageDraw.Draw(img)
    stops = [(0, (52, 22, 68)), (0.38, (150, 50, 95)), (0.55, (215, 85, 100)), (0.72, (245, 140, 90)), (1, (245, 140, 90))]
    for y in range(H * S):
        k = y / (H * S)
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if a <= k <= b:
                t = (k - a) / (b - a)
                c = tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)); break
        d.line([(0, y), (W * S, y)], fill=c)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([P(200), P(700), P(880), P(1300)], fill=(255, 190, 120, 140))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(P(120))))
    d = ImageDraw.Draw(img)
    rnd = random.Random(3)
    for _ in range(90):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, 900), rnd.uniform(1.5, 3.5)
        d.ellipse([P(x - r), P(y - r), P(x + r), P(y + r)], fill=(255, 235, 230, rnd.randint(120, 230)))
    d.ellipse([P(400), P(960), P(720), P(1280)], fill=(255, 230, 180))  # солнце
    return img

def make_city(seed, color, hmin, hmax, wid=1800):
    img = Image.new("RGBA", (wid * S, P(700)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img); rnd = random.Random(seed); x = 0
    while x < wid:
        w, h = rnd.randint(80, 220), rnd.randint(hmin, hmax)
        d.rectangle([P(x), P(700 - h), P(x + w), P(700)], fill=color)
        if rnd.random() < 0.35:
            ax = x + rnd.randint(15, w - 15)
            d.rectangle([P(ax), P(700 - h - 70), P(ax + 4), P(700 - h)], fill=color)
        x += w - rnd.randint(0, 30)
    return img

SKY = make_sky()
CITY_FAR = make_city(1, (150, 55, 95, 255), 200, 520)
CITY_NEAR = make_city(2, (110, 35, 75, 255), 120, 380)

def tile(img, layer, offset, y):
    lw = layer.width
    off = int(offset * S) % lw
    img.alpha_composite(layer, (-off, y))
    img.alpha_composite(layer, (lw - off, y))

# ---------- человечек ----------
def walker(d, x, phase, hat, scale=1.0):
    """Силуэт с кремовой обводкой. x — центр, phase — фаза шага."""
    s = scale
    hip = (x, GROUND_Y - 230 * s)
    neck = (x + 8 * s, GROUND_Y - 420 * s)
    head = (x + 15 * s, GROUND_Y - 490 * s)
    def limb(root, ang, bend, l1, l2):
        k = (root[0] + math.sin(ang) * l1, root[1] + math.cos(ang) * l1)
        a2 = ang - bend
        e = (k[0] + math.sin(a2) * l2, k[1] + math.cos(a2) * l2)
        return [root, k, e]
    legs, arms = [], []
    for side in (0, 1):
        p = phase + side * math.pi
        a = math.sin(p) * 0.5
        bend = (max(0.0, math.cos(p)) * 1.1 + 0.1)  # колено сгибается, когда нога идёт вперёд по воздуху
        legs.append(limb(hip, a, bend, 115 * s, 115 * s))
        arms.append(limb((neck[0], neck[1] + 20 * s), -math.sin(p) * 0.6, -0.5, 85 * s, 80 * s))
    body = [(neck[0] - 45 * s, neck[1]), (neck[0] + 45 * s, neck[1] + 5 * s), (hip[0] + 38 * s, hip[1] + 15 * s), (hip[0] - 40 * s, hip[1] + 15 * s)]

    for col, extra in ((CREAM, 7), (DARK, 0)):      # 1 — обводка, 2 — заливка
        w = (34 + 2 * extra) * s
        for pts in [legs[1], arms[1], legs[0], arms[0]]:
            d.line([(P(a), P(b)) for a, b in pts], fill=col, width=P(w), joint="curve")
            for a, b in (pts[0], pts[-1]):
                d.ellipse([P(a - w / 2), P(b - w / 2), P(a + w / 2), P(b + w / 2)], fill=col)
        d.polygon([(P(a + (extra * s if a > x else -extra * s)), P(b)) for a, b in body], fill=col)
        r = (55 + extra) * s
        d.ellipse([P(head[0] - r), P(head[1] - r), P(head[0] + r), P(head[1] + r)], fill=col)
    # шапка
    hx, hy = head
    d.chord([P(hx - 60 * s), P(hy - 75 * s), P(hx + 60 * s), P(hy + 30 * s)], 180, 360, fill=hat)
    darker = tuple(int(c * 0.75) for c in hat)
    d.rounded_rectangle([P(hx - 66 * s), P(hy - 32 * s), P(hx + 66 * s), P(hy - 14 * s)], P(8), fill=darker)
    d.ellipse([P(x - 70 * s), P(GROUND_Y - 8 * s), P(x + 80 * s), P(GROUND_Y + 14 * s)], fill=(20, 5, 20))

# ---------- UI-элементы ----------
def text_c(d, cx, y, s, font, fill, stroke=0, sfill=DARK):
    w = d.textlength(s, font=font)
    d.text((P(cx) - w / 2, P(y)), s, font=font, fill=fill, stroke_width=P(stroke), stroke_fill=sfill)

def money(v): return "$" + f"{int(v):,}".replace(",", " ")

def card(img, t):
    k = back((t - 0.1) / 0.5)
    if k <= 0: return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = 150, 230, 930, 400
    d.rounded_rectangle([P(x0 + 6), P(y0 + 10), P(x1 + 6), P(y1 + 10)], P(30), fill=(40, 10, 30, 110))
    d.rounded_rectangle([P(x0), P(y0), P(x1), P(y1)], P(30), fill=CREAM)
    cnt = ease((t - 0.4) / 2.2)
    for cx, lab, val in [(200, "ДЕНЬ", None), (370, "МАКС", 60_000 + 40_000 * cnt), (650, "САНЯ", 25_000 + 25_000 * cnt)]:
        d.text((P(cx), P(y0 + 28)), lab, font=F(26), fill=(150, 120, 110))
        if val is None: d.text((P(cx), P(y0 + 72)), "2", font=F(66), fill=DARK)
        else: d.text((P(cx), P(y0 + 76)), money(round(val, -2)), font=F(50), fill=MONEY)
    sc = max(0.01, k)
    layer = layer.resize((int(img.width * sc), int(img.height * sc)))
    img.alpha_composite(layer, (int(img.width * (1 - sc) / 2), int(P(315) * (1 - sc))))

def title(d, t):
    k = back(t / 0.45)
    if k <= 0: return
    text_c(d, W / 2, 440 + (1 - k) * 60, "ДЕНЬ 2", F(130 * max(0.3, k)), CREAM, 0)

def sticker(img, t):
    k = back((t - 1.4) / 0.4)
    if k <= 0: return
    lay = Image.new("RGBA", (P(420), P(200)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([P(10), P(14), P(410), P(190)], P(24), fill=(40, 10, 30, 100))
    d.rounded_rectangle([0, 0, P(400), P(176)], P(24), fill=CREAM)
    d.text((P(28), P(22)), "Макс · скрин", font=F(30), fill=(130, 100, 90))
    d.text((P(28), P(70)), "$100 000", font=F(70), fill=MONEY)
    lay = lay.rotate(6 * k, expand=True, resample=Image.BICUBIC)
    sc = max(0.05, k)
    lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))))
    img.alpha_composite(lay, (P(620) - lay.width // 2, P(760) - lay.height // 2))

SUBS = [(0.0, 1.3, "МАКС УЖЕ", "ПРИСЫЛАЕТ"), (1.3, 2.9, "ЕМУ", "СКРИНШОТЫ."),
        (2.9, 4.4, "А НА ТРЕТИЙ", "ДЕНЬ"), (4.4, 6.0, "МАКС НЕ МОЖЕТ", "ВСТАТЬ.")]

def subtitle(d, t):
    for a, b, white, yellow in SUBS:
        if a <= t < b:
            k = back((t - a) / 0.18)
            f = F(64 * (0.85 + 0.15 * k))
            full = white + " " + yellow
            wfull = d.textlength(full, font=f); x = P(W / 2) - wfull / 2; y = P(1640)
            d.text((x, y), white + " ", font=f, fill=(255, 255, 255), stroke_width=P(6), stroke_fill=(0, 0, 0))
            d.text((x + d.textlength(white + " ", font=f), y), yellow, font=f, fill=(255, 205, 40), stroke_width=P(6), stroke_fill=(0, 0, 0))

def road(d, t):
    d.rectangle([0, P(GROUND_Y), P(W), P(H)], fill=(34, 12, 40))
    d.polygon([(P(400), P(GROUND_Y)), (P(700), P(GROUND_Y)), (P(980), P(H)), (P(120), P(H))], fill=(74, 32, 44))
    off = (t * 320) % 260
    for i in range(-1, 6):
        x = i * 260 - off
        d.rectangle([P(x), P(1520), P(x + 110), P(1530)], fill=(130, 90, 80))

def frame(t):
    img = SKY.copy()
    tile(img, CITY_FAR, t * 25, P(GROUND_Y - 700))
    tile(img, CITY_NEAR, t * 60 + 400, P(GROUND_Y - 700))
    d = ImageDraw.Draw(img)
    road(d, t)
    walker(d, 330, t * 7.5, RED)          # Макс
    walker(d, 720, t * 7.5 + 1.3, YELLOW)  # Саня
    card(img, t); d = ImageDraw.Draw(img)
    title(d, t)
    sticker(img, t); d = ImageDraw.Draw(img)
    subtitle(d, t)
    return img.convert("RGB").resize((W, H), Image.LANCZOS)

if __name__ == "__main__":
    frame(2.2).save(os.path.join(OUT, "kadr2.png"))
    if "--still" in sys.argv: sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "20",
                           "-pix_fmt", "yuv420p", os.path.join(OUT, "animaciya2.mp4")], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        ff.stdin.write(frame(i / FPS).tobytes())
    ff.stdin.close(); ff.wait(); print("готово")
