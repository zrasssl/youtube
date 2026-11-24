"""DISCIPLINE: a 2:39 minimalist animated motivational film, drawn entirely in code.

Story: 5 AM alarm -> walk through the rain -> climbing the staircase of days -> the fall ->
heartbeat, "get up" -> the climb graph (day 31 to 365) -> summit at sunrise -> title card.
Voice lines are ElevenLabs clips in daily/film/voice/v01..v09.mp3 (+ the shared subscribe line).

Usage: python daily/film/make_film.py   ->  daily/out/05-discipline-film.mp4
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
from make_video import make_music  # noqa: E402  (ambient pad, original)

W, H, FPS, SR, TOTAL = 1920, 1080, 30, 48000, 159.0
F_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FONTS = {}

VOICE = [("v01", 6.5), ("v02", 13.0), ("v03", 31.5), ("v04", 46.0), ("v05", 59.3), ("v06", 83.5),
         ("v07", 97.3), ("v08", 102.0), ("v09", 138.0), (os.path.join(ROOT, "advice/eleven/15.mp3"), 152.3)]

# (start, end, text, size, y)
TEXTS = [
    (1.0, 6.0, "5:00 AM", 44, 170),
    (6.5, 11.5, "NOBODY'S WATCHING.", 76, 170),
    (13.0, 20.5, "IT'S COLD. IT'S DARK.", 72, 170),
    (21.0, 28.8, "YOU GO ANYWAY.", 76, 170),
    (46.5, 54.5, "STILL NOTHING.", 52, 260),
    (59.3, 61.4, "YOU WILL FALL.", 76, 170),
    (61.4, 73.5, "YOU WILL WANT TO STOP.", 76, 170),
    (83.5, 94.0, "GET UP.", 120, 230),
    (97.3, 101.8, "DISCIPLINE IS CHOOSING WHAT YOU WANT MOST", 58, 150),
    (102.0, 110.0, "OVER WHAT YOU WANT NOW.", 76, 150),
    (138.0, 140.6, "AND ONE DAY...", 64, 60),
    (140.6, 146.4, "THEY'LL CALL IT TALENT.", 80, 60),
    (147.8, 151.8, "D I S C I P L I N E", 110, 470),
    (152.2, 158.4, "SUBSCRIBE IF YOU SOMETIMES", 40, 440),
    (152.2, 158.4, "NEED A PUSH FORWARD.", 80, 500),
]


def font(path, size):
    k = (path, size)
    if k not in FONTS:
        FONTS[k] = ImageFont.truetype(path, size)
    return FONTS[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def window(t, a, b, f=0.4):
    return ease((t - a) / f) * ease((b - t) / f)


def lerp(a, b, k):
    return a + (b - a) * k


# ---------------------------------------------------------------- backgrounds
Y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
X = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
VIGN = (1 - 0.55 * np.clip(np.sqrt((X - 0.5) ** 2 * 1.6 + (Y - 0.45) ** 2 * 2.2), 0, 1)).astype(np.float32)
NIGHT = (np.array([10, 12, 22], np.float32) + Y * np.array([8, 10, 18], np.float32)) * VIGN
DAWN = (np.array([38, 34, 70], np.float32) * (1 - Y) + np.array([235, 130, 70], np.float32) * Y ** 1.6) * VIGN


def dawn_amount(t):
    if t < 100:
        return 0.0
    if t < 146.5:
        return ease((t - 100) / 38)
    return 1 - ease((t - 146.5) / 1.2)


# ---------------------------------------------------------------- stick figure
def figure(d, x, y, s, pose="stand", ph=0.0, tilt=0.0, col=(240, 240, 240)):
    """Draw a stick figure whose feet touch (x, y). tilt in degrees rotates the whole body about the feet."""
    leg, body, arm, head = 0.42 * s, 0.36 * s, 0.32 * s, 0.10 * s
    hip = (0.0, -leg)
    lean = {"run": 0.12, "walk": 0.04, "climb": 0.08}.get(pose, 0.0) * s
    neck = (lean, hip[1] - body)
    pts = {}
    if pose in ("walk", "run", "climb"):
        amp = 0.55 if pose == "run" else 0.38
        a1, a2 = amp * math.sin(ph), -amp * math.sin(ph)
        k1, k2 = 0.5 * max(0, math.sin(ph + 1.2)), 0.5 * max(0, math.sin(ph + 1.2 + math.pi))
        legs = [(a1, k1), (a2, k2)]
        arms = [(-a1 * 0.9, -0.6), (-a2 * 0.9, -0.6)]
    elif pose == "sit":
        legs = [(1.45, 1.45), (1.35, 1.45)]
        arms = [(0.35, -0.2), (0.25, -0.2)]
        hip = (0.0, -0.45 * leg)
        neck = (0.02 * s, hip[1] - body)
    elif pose == "up":
        legs = [(0.12, 0.0), (-0.12, 0.0)]
        arms = [(2.7, 0.2), (-2.7, -0.2)]
    elif pose == "slump":
        legs = [(0.08, 0.1), (-0.08, 0.1)]
        arms = [(0.15, 0.0), (-0.1, 0.0)]
        neck = (0.10 * s, hip[1] - body * 0.95)
    else:  # stand
        legs = [(0.09, 0.0), (-0.09, 0.0)]
        arms = [(0.22, -0.1), (-0.22, 0.1)]
    th, sh = leg * 0.5, leg * 0.5
    ua = arm * 0.5
    lines = []
    for a, k in legs:
        knee = (hip[0] + th * math.sin(a), hip[1] + th * math.cos(a))
        foot = (knee[0] + sh * math.sin(a - k), knee[1] + sh * math.cos(a - k))
        lines += [(hip, knee), (knee, foot)]
    shoulder = (lerp(hip[0], neck[0], 0.85), lerp(hip[1], neck[1], 0.85))
    for a, k in arms:
        elbow = (shoulder[0] + ua * math.sin(a), shoulder[1] + ua * math.cos(a))
        hand = (elbow[0] + ua * math.sin(a + k), elbow[1] + ua * math.cos(a + k))
        lines += [(shoulder, elbow), (elbow, hand)]
    lines.append((hip, neck))
    hc = (neck[0] + 0.02 * s, neck[1] - head * 1.15)
    if pose == "slump":
        hc = (neck[0] + head * 0.8, neck[1] - head * 0.6)
    r = math.radians(tilt)
    cr, sr = math.cos(r), math.sin(r)

    def tr(p):
        return (x + p[0] * cr - p[1] * sr, y + p[0] * sr + p[1] * cr)

    wdt = max(3, int(s * 0.045))
    for a, b in lines:
        A, B = tr(a), tr(b)
        d.line([A, B], fill=col, width=wdt)
        for P in (A, B):
            d.ellipse([P[0] - wdt / 2, P[1] - wdt / 2, P[0] + wdt / 2, P[1] + wdt / 2], fill=col)
    c = tr(hc)
    d.ellipse([c[0] - head, c[1] - head, c[0] + head, c[1] + head], fill=col)


def text_c(d, txt, size, y, a, bold=True, col=255):
    if a <= 0.01:
        return
    f = font(F_BOLD if bold else F_SEMI, size)
    w = d.textlength(txt, font=f)
    v = int(col * a)
    d.text(((W - w) / 2, y), txt, font=f, fill=(v, v, v))


# ---------------------------------------------------------------- scenes
RAIN = np.random.default_rng(7).random((160, 3))
STARS = np.random.default_rng(3).random((140, 3))
STAIR_X0, STAIR_W, STAIR_R, STAIR_BASE = 260, 112, 48, 940


def stair_top(i):
    return STAIR_X0 + (i + 0.5) * STAIR_W, STAIR_BASE - (i + 1) * STAIR_R


def draw_stairs(d, a):
    c = int(150 * a)
    pts = [(STAIR_X0 - 200, STAIR_BASE)]
    for i in range(12):
        x0, yv = STAIR_X0 + i * STAIR_W, STAIR_BASE - (i + 1) * STAIR_R
        pts += [(x0, pts[-1][1]), (x0, yv), (x0 + STAIR_W, yv)]
    d.line(pts, fill=(c, c, c), width=4)


GRAPH = None


def graph_points():
    global GRAPH
    if GRAPH is None:
        rng = np.random.default_rng(11)
        xs = np.linspace(160, 1760, 70)
        base = np.linspace(0, 1, 70) ** 1.35
        noise = np.cumsum(rng.normal(0, 0.018, 70))
        dips = np.where(rng.random(70) < 0.12, -0.05, 0)
        ys = 880 - 560 * np.clip(base + noise * 0.4 + dips, 0, 1.05)
        GRAPH = np.stack([xs, ys], 1)
    return GRAPH


def mountain_y(x):
    px, py = 1150, 400
    if x <= px:
        return lerp(960, py, clamp((x - 250) / (px - 250)))
    return lerp(py, 960, clamp((x - px) / (1920 - px)))


def frame(t):
    dawn = dawn_amount(t)
    bg = NIGHT * (1 - dawn) + DAWN * dawn
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    dim = 1.0

    if t < 12:  # bedroom at 5 AM
        # window with stars
        d.rectangle([380, 300, 620, 520], outline=(70, 80, 110), width=4)
        d.line([500, 300, 500, 520], fill=(70, 80, 110), width=3)
        for sx, sy, sb in STARS[:14]:
            v = int(90 + 120 * sb * (0.6 + 0.4 * math.sin(t * 2 + sb * 9)))
            d.ellipse([390 + sx * 220, 310 + sy * 200, 393 + sx * 220, 313 + sy * 200], fill=(v, v, v))
        d.rectangle([760, 720, 1180, 770], outline=(110, 110, 120), width=4)  # bed
        d.rectangle([760, 690, 830, 720], outline=(110, 110, 120), width=3)  # pillow
        on = t >= 6 or int(t * 2) % 2 == 0
        d.rounded_rectangle([1260, 640, 1460, 730], 14, outline=(120, 120, 130), width=4)
        if on:
            f = font(F_BOLD, 56)
            col = (240, 80, 70)
            d.text((1360 - d.textlength("05:00", font=f) / 2, 650), "05:00", font=f, fill=col)
        if t < 3:
            figure(d, 1150, 712, 230, "stand", tilt=-90 + 4 * math.sin(t * 1.5))
        else:
            k = ease((t - 3) / 2)
            if k < 1:
                figure(d, lerp(1150, 1060, k), lerp(712, 770, k), 230, "stand", tilt=lerp(-90, 0, k))
            else:
                figure(d, 1060, 770, 230, "sit")
        d.line([0, 770, W, 770], fill=(45, 45, 55), width=3)

    elif t < 30:  # walking in the rain
        lt = t - 12
        d.line([0, 800, W, 800], fill=(90, 90, 100), width=4)
        for lx in (420, 960, 1500):
            d.line([lx, 800, lx, 470], fill=(80, 80, 90), width=6)
            d.line([lx, 470, lx + 60, 470], fill=(80, 80, 90), width=6)
            glow = 60 + 20 * math.sin(t * 3 + lx)
            d.ellipse([lx + 40, 470, lx + 80, 500], fill=(int(glow * 2.5), int(glow * 2.2), int(glow * 1.4)))
        for rx, ry, rs in RAIN:
            x0 = (rx * (W + 300) + lt * 260 * (0.8 + rs)) % (W + 300) - 300
            y0 = (ry * H + lt * 1400 * (0.7 + rs * 0.6)) % H
            d.line([x0, y0, x0 - 14, y0 + 38], fill=(95, 105, 130), width=2)
        x = lerp(140, 1760, clamp((t - 12.5) / 17))
        figure(d, x, 800, 260, "walk", ph=t * 5.2)

    elif t < 75:  # staircase of days, then the fall
        draw_stairs(d, 1.0 if t < 74 else 1 - (t - 74))
        if t < 31:
            sx, sy = STAIR_X0 - 90, STAIR_BASE
            figure(d, sx, sy, 220, "stand")
            day = 1
        elif t < 46:
            p = (t - 31) / 1.5
            i, f = int(p), p - int(p)
            mv = ease(f / 0.55)
            ax, ay = (STAIR_X0 - 90, STAIR_BASE) if i == 0 else stair_top(i - 1)
            bx, by = stair_top(i)
            x, y = lerp(ax, bx, mv), lerp(ay, by, mv) - 30 * math.sin(math.pi * mv)
            figure(d, x, y, 220, "climb" if mv < 1 else "stand", ph=f * 9)
            day = 1 + int(round(29 * clamp((t - 31) / 15)))
        elif t < 57:
            x, y = stair_top(9)
            figure(d, x, y, 220, "slump" if t > 47 else "stand")
            day = 30
        else:
            k = ease((t - 57) / 2)
            ax, ay = stair_top(9)
            bx, by = stair_top(4)
            x, y = lerp(ax, bx, k), lerp(ay, by, k)
            figure(d, x, y, 220, "stand", tilt=lerp(0, -82, ease((t - 57) / 1.2)))
            day = 30
            dim = 1 - 0.35 * ease((t - 59) / 4)
        if t < 57:
            text_c(d, f"DAY {day}", 64, 120, window(t, 30.5, 56.8, 0.5), col=230)

    elif t < 95:  # heartbeat, get up
        lt = t - 75
        beat = (t * 1.15) % 1.0
        pulse = math.exp(-beat * 6) + 0.6 * math.exp(-max(0, beat - 0.22) * 7) * (beat > 0.22)
        inten = ease(lt / 8) * (0.5 + 0.5 * pulse)
        r = 180 + 90 * pulse
        for k in range(6, 0, -1):
            v = int(inten * 26 * (7 - k) / 6)
            rr = r * k / 3
            d.ellipse([960 - rr, 760 - rr * 0.6, 960 + rr, 760 + rr * 0.6], fill=(v + 12, v // 2 + 12, v // 2 + 20))
        if lt > 10:
            for sx, sy, sb in STARS:
                v = int(clamp((lt - 10) / 4) * (60 + 120 * sb))
                d.ellipse([sx * W, sy * 600, sx * W + 3, sy * 600 + 3], fill=(v, v, v))
        d.line([300, 800, 1620, 800], fill=(70, 70, 80), width=3)
        k = ease((t - 84) / 2.5)
        figure(d, 960, 800, 240, "stand", tilt=lerp(-82, 0, k) + (0 if k > 0 else 2 * math.sin(t)))

    elif t < 125:  # the climb graph, day 31 -> 365
        g = graph_points()
        p = clamp((t - 95.5) / 27.5)
        n = max(2, int(p * (len(g) - 1)) + 1)
        frac = p * (len(g) - 1) - (n - 1)
        pts = [tuple(v) for v in g[:n]]
        if n < len(g):
            nx = g[n - 1] + (g[n] - g[n - 1]) * clamp(frac)
            pts.append(tuple(nx))
        d.line([(150, 900), (1780, 900)], fill=(90, 90, 100), width=3)
        d.line([(150, 900), (150, 280)], fill=(90, 90, 100), width=3)
        d.line(pts, fill=(250, 200, 120), width=6, joint="curve")
        tx, ty = pts[-1]
        figure(d, tx, ty - 3, 150, "run", ph=t * 9)
        day = 31 + int(334 * p)
        f = font(F_BOLD, 54)
        txt = f"DAY {day}"
        d.text((1760 - d.textlength(txt, font=f), 300), txt, font=f, fill=(235, 235, 235))

    elif t < 147:  # summit at sunrise
        sun_y = lerp(760, 330, ease((t - 125) / 13))
        rays = clamp((t - 135) / 3)
        for i in range(18):
            ang = i / 18 * 2 * math.pi + t * 0.08
            if rays > 0:
                c = (int(255 * rays * 0.55), int(200 * rays * 0.5), int(120 * rays * 0.4))
                d.line([1150 + 150 * math.cos(ang), sun_y + 150 * math.sin(ang),
                        1150 + 700 * math.cos(ang), sun_y + 700 * math.sin(ang)], fill=c, width=5)
        d.ellipse([1150 - 120, sun_y - 120, 1150 + 120, sun_y + 120], fill=(255, 214, 150))
        d.polygon([(250, 960), (1150, 400), (1920, 960), (1920, H), (0, H), (0, 960)], fill=(22, 18, 34))
        k = clamp((t - 125.5) / 9.5)
        x = lerp(330, 1150, k)
        y = mountain_y(x)
        if k < 1:
            figure(d, x, y, 170, "climb", ph=t * 6, col=(15, 12, 25))
        else:
            figure(d, 1150, 400, 170, "up" if t > 136 else "stand", col=(15, 12, 25))
            if t > 137:
                fk = ease((t - 137) / 1.0)
                d.line([1195, 400, 1195, 400 - 150 * fk], fill=(15, 12, 25), width=6)
                if fk >= 1:
                    wv = 6 * math.sin(t * 5)
                    d.polygon([(1195, 252), (1290, 270 + wv), (1195, 300)], fill=(15, 12, 25))

    for a, b, txt, size, y in TEXTS:
        if a - 0.5 <= t <= b + 0.5:
            text_c(d, txt, size, y, window(t, a, b, 0.35), bold=size >= 50)

    arr = np.asarray(img, dtype=np.float32)
    fade = 1.0
    for c in (12.0, 30.0, 75.0, 95.0, 125.0, 147.0):  # dip to black between scenes
        fade = min(fade, clamp(abs(t - c) / 0.5))
    fade *= ease(t / 1.0) * ease((TOTAL - t) / 1.0)
    return np.clip(arr * dim * fade, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- sound
def sound(tmp):
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    make_music(TOTAL, f"{tmp}/pad.f32", seed=5)
    pad = np.fromfile(f"{tmp}/pad.f32", dtype=np.float32).reshape(-1, 2)[:n]
    level = np.interp(t, [0, 12, 30, 55, 75, 95, 125, 140, 147, 152, TOTAL],
                      [0.5, 0.55, 0.6, 0.65, 0.4, 0.75, 0.9, 1.0, 0.9, 0.6, 0.0])
    fx = np.zeros(n, np.float32)
    rng = np.random.default_rng(1)
    # alarm beeps 0-6s
    for k in range(12):
        a = int((0.25 + k * 0.5) * SR)
        m = int(0.12 * SR)
        fx[a:a + m] += 0.18 * np.sin(2 * np.pi * 1760 * np.arange(m) / SR) * np.hanning(m)
    # rain 12-30s: smoothed noise
    a, b = int(12 * SR), int(30 * SR)
    rain = np.convolve(rng.normal(0, 1, b - a), np.ones(6) / 6, mode="same")
    fx[a:b] += (0.05 * rain * np.minimum(1, np.minimum((t[a:b] - 12) / 1.5, (30 - t[a:b]) / 1.5))).astype(np.float32)

    def thump(at, amp, f0=70, f1=40, dur=0.35):
        a = int(at * SR)
        m = int(dur * SR)
        if a + m > n:
            return
        tt = np.arange(m) / SR
        freq = f1 + (f0 - f1) * np.exp(-tt * 18)
        fx[a:a + m] += (amp * np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-tt * 9)).astype(np.float32)

    # heartbeat 75-95
    bt = 75.0
    while bt < 95:
        amp = 0.25 + 0.45 * clamp((bt - 75) / 8)
        thump(bt, amp, 60, 38)
        thump(bt + 0.22, amp * 0.7, 55, 36)
        bt += 1 / 1.15
    # driving pulse 95-147, crescendo
    bt = 95.0
    while bt < 147:
        thump(bt, 0.35 + 0.4 * clamp((bt - 95) / 45), 120, 45, 0.3)
        if bt > 105:
            a = int((bt + 0.25) * SR)
            m = int(0.05 * SR)
            fx[a:a + m] += (0.05 * clamp((bt - 105) / 20) * rng.normal(0, 1, m) * np.linspace(1, 0, m)).astype(np.float32)
        bt += 0.5
    # swells
    for at, amp in ((134.5, 0.25), (146.8, 0.3)):
        a = int((at - 1.5) * SR)
        m = int(3 * SR)
        env = np.concatenate([np.linspace(0, 1, int(1.5 * SR)) ** 2, np.exp(-np.linspace(0, 6, m - int(1.5 * SR)))])
        sw = np.convolve(rng.normal(0, 1, m), np.ones(3) / 3, mode="same")
        fx[a:a + m] += (amp * env * sw).astype(np.float32)
    music = pad * level[:, None].astype(np.float32) + fx[:, None]
    music = music / (np.abs(music).max() + 1e-9) * 0.8
    music.astype(np.float32).tofile(f"{tmp}/music.f32")

    voice = np.zeros(n, np.float32)
    for name, at in VOICE:
        src = name if os.path.isabs(name) else f"{HERE}/voice/{name}.mp3"
        raw = f"{tmp}/{os.path.basename(src)}.f32"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB",
                        "-ar", str(SR), "-ac", "1", "-f", "f32le", raw], check=True)
        v = np.fromfile(raw, dtype=np.float32)
        v = v / (np.abs(v).max() + 1e-9) * 0.9
        a = int(at * SR)
        voice[a:a + len(v)] += v[: max(0, n - a)]
    voice.tofile(f"{tmp}/voice.f32")


def main():
    out = os.path.join(ROOT, "daily/out/05-discipline-film.mp4")
    tmp = os.path.join(ROOT, "daily/out/.film")
    os.makedirs(tmp, exist_ok=True)
    only = float(sys.argv[1]) if len(sys.argv) > 1 else None
    if only is not None:  # preview a single frame
        Image.fromarray(frame(only)).save(f"{tmp}/preview_{only:.1f}.jpg", quality=85)
        print(f"{tmp}/preview_{only:.1f}.jpg")
        return
    sound(tmp)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f"{tmp}/voice.f32",
                            "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", f"{tmp}/music.f32",
                            "-filter_complex",
                            "[2:a]lowpass=f=6000[m];[1:a]aformat=channel_layouts=stereo,asplit=2[v][sc];"
                            "[m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=30:release=500[d];"
                            "[d][v]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]",
                            "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                            "-t", str(TOTAL), out], stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        enc.stdin.write(frame(i / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
