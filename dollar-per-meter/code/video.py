"""Полный шорт «$1 за каждый метр»: 10 сцен, субтитры по озвучке, сборка в mp4.
Запуск: python3 video.py voice.mp3  [--preview]   (--preview рендерит по кадру на сцену)"""
import json, math, os, random, re, subprocess, sys
from PIL import Image, ImageDraw
import scene2 as B          # фон, человечки, шрифты из прошлой сцены
from scene2 import P, F, W, H, CREAM, DARK, RED, YELLOW, MONEY, GROUND_Y, ease, back, text_c

S, FPS = B.S, 30
OUT = os.path.dirname(os.path.abspath(__file__))
SUBY = 1660
GOLD = (255, 205, 40)

# ---------- сценарий: (сцена, текст фразы) ----------
SCRIPT = """1|Доллар за каждый метр.
1|Звучит как ерунда?
1|А ведь ты мог бы уже быть миллионером — просто живя свою жизнь.
2|Обычный человек делает около 6 000 шагов в день.
2|Это 4,5 километра — 4 500 долларов.
2|За год — больше полутора миллионов.
3|Правила простые.
3|Макс и Саня получают одно и то же сообщение: доллар за каждый метр.
3|Только пешком — машина, лифт и беговая дорожка не считаются.
4|Макс срывается с места и идёт весь день и всю ночь.
4|60 километров — 60 000 долларов за сутки!
4|А Саня спокойно проходит 25 километров и ложится спать.
5|На второй день Макс выжимает ещё 40.
5|У него 100 000, у Сани — 50.
5|Макс уже шлёт ему скриншоты.
6|А на третий день Макс не может встать.
6|Ноги стёрты, колени не гнутся.
6|Две недели — по 2 километра в день.
6|Потом он приходит в себя, но больше не рискует — по 10 километров в день.
7|А Саня идёт.
7|25 километров каждый день — в дождь, в выходные, с музыкой в ушах.
7|И уже на пятый день он обгоняет Макса.
8|Проходит год.
8|У Макса — 3,6 миллиона.
8|Неплохо.
8|А у Сани — 9 миллионов!
8|В два с половиной раза больше.
8|Не потому, что он быстрее.
8|А потому, что он ни разу не остановился.
9|И напоследок.
9|За 70 лет человек проходит около 115 000 километров — почти три раза вокруг Земли.
9|Это 115 миллионов долларов.
9|Просто за то, что ты ходишь.
10|А ты бы рванул, как Макс, или шёл, как Саня?"""
LINES = [(int(a), b) for a, b in (l.split("|", 1) for l in SCRIPT.splitlines())]
KEY = {"доллар", "метр", "миллионером", "миллионов", "миллиона", "правила", "пешком", "макс", "саня", "сани",
       "скриншоты", "не", "встать", "идёт", "обгоняет", "год", "остановился", "земли", "ходишь", "рванул", "шёл"}

# ---------- выравнивание фраз по паузам в озвучке ----------
def audio_len(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

def silences(path):
    r = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=noise=-32dB:d=0.12", "-f", "null", "-"], capture_output=True, text=True)
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [((a + b) / 2, b - a) for a, b in zip(st, en)]

def align(path):
    total = audio_len(path)
    sil = silences(path)
    w = [len(t) + 8 for _, t in LINES]            # +8 — средняя пауза после фразы
    cum, acc = [], 0
    for x in w[:-1]:
        acc += x; cum.append(acc / sum(w) * total)
    bounds, used = [], set()
    for i, est in enumerate(cum):
        lo = bounds[-1] + 0.4 if bounds else 0.4
        cands = [(abs(m - est) - 0.6 * d, m) for j, (m, d) in enumerate(sil) if j not in used and m > lo and abs(m - est) < 2.5]
        if cands:
            _, m = min(cands); used.add([s[0] for s in sil].index(m)); bounds.append(m)
        else:
            bounds.append(max(est, lo))
    starts = [0.0] + bounds
    ends = bounds + [total]
    return [(s, e, sc, t) for (sc, t), s, e in zip(LINES, starts, ends)], total

# ---------- субтитры ----------
def chunks(text, n=3):
    words = text.split()
    out, cur = [], []
    for wd in words:
        cur.append(wd)
        if len(cur) >= n or wd.endswith((".", "!", "?", ",", ":")) and len(cur) >= 2:
            out.append(cur); cur = []
    if cur:
        if out and len(cur) == 1 and cur[0] in "—": out[-1] += cur
        else: out.append(cur)
    return out

def is_key(wd):
    c = wd.strip(".,!?:—").lower()
    return any(ch.isdigit() for ch in c) or c in KEY

def subtitle(d, t, timeline):
    for s, e, _, text in timeline:
        if s <= t < e:
            parts = chunks(text)
            lens = [sum(len(x) for x in p) + 2 for p in parts]
            acc, tot = s, sum(lens)
            for p, L in zip(parts, lens):
                dur = (e - s) * L / tot
                if acc <= t < acc + dur:
                    k = back((t - acc) / 0.15)
                    words = [x for x in p if x != "—"]
                    line = " ".join(words).upper()
                    fit = min(68, 68 * 960 / max(1, F(68).getlength(line) / S))
                    f = F(fit * (0.85 + 0.15 * k))
                    x = P(W / 2) - d.textlength(line, font=f) / 2
                    for wd in words:
                        s_ = wd.upper() + " "
                        d.text((x, P(SUBY)), s_, font=f, fill=GOLD if is_key(wd) else (255, 255, 255),
                               stroke_width=P(7), stroke_fill=(0, 0, 0))
                        x += d.textlength(s_, font=f)
                    return
                acc += dur

# ---------- элементы ----------
def pill(img, cx, cy, text, t0, t, bg=CREAM, fg=(225, 70, 40), size=64, rot=-3):
    k = back((t - t0) / 0.35)
    if t < t0 or k <= 0: return
    f = F(size)
    tmp = ImageDraw.Draw(img)
    tw = tmp.textlength(text, font=f)
    lay = Image.new("RGBA", (int(tw + P(90)), P(size * 1.9)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([P(8), P(12), lay.width - 1, lay.height - 1], P(22), fill=(40, 10, 30, 110))
    d.rounded_rectangle([0, 0, lay.width - P(8), lay.height - P(12)], P(22), fill=bg)
    d.text((P(37), P(size * 0.28)), text, font=f, fill=fg)
    lay = lay.rotate(rot * k, expand=True, resample=Image.BICUBIC)
    sc = max(0.05, k)
    lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))))
    img.alpha_composite(lay, (P(cx) - lay.width // 2, P(cy) - lay.height // 2))

def card(img, x0, y0, x1, y1, cols, t0, t):
    """cols: [(подпись, значение-строка, цвет)]"""
    k = back((t - t0) / 0.4)
    if t < t0 or k <= 0: return
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([P(x0 + 6), P(y0 + 10), P(x1 + 6), P(y1 + 10)], P(30), fill=(40, 10, 30, 110))
    d.rounded_rectangle([P(x0), P(y0), P(x1), P(y1)], P(30), fill=CREAM)
    n = len(cols); cw = (x1 - x0) / n
    for i, (lab, val, col) in enumerate(cols):
        cx = x0 + cw * i + cw / 2
        text_c(d, cx, y0 + 26, lab, F(26), (150, 120, 110))
        text_c(d, cx, y0 + 70, val, F(40 if len(val) > 7 else 56), col)
    sc = max(0.01, k)
    cy = (y0 + y1) / 2
    lay = lay.resize((int(img.width * sc), int(img.height * sc)))
    img.alpha_composite(lay, (int(img.width * (1 - sc) / 2), int(P(cy) * (1 - sc))))

def big(d, y, text, t0, t, size=130, col=CREAM):
    k = back((t - t0) / 0.4)
    if t < t0 or k <= 0: return
    text_c(d, W / 2, y + (1 - min(k, 1)) * 50, text, F(size * max(0.3, k)), col, 0)

def money(v): return "$" + f"{int(round(v)):,}".replace(",", " ")

def sitter(d, x):
    """Макс сидит на дороге, обхватив колени."""
    hip = (x, GROUND_Y - 40)
    knee = (x + 110, GROUND_Y - 150)
    foot = (x + 170, GROUND_Y - 5)
    neck = (x + 40, GROUND_Y - 220)
    head = (x + 95, GROUND_Y - 260)
    hand = (knee[0] + 10, knee[1] + 20)
    for col, ex in ((CREAM, 7), (DARK, 0)):
        w = 34 + 2 * ex
        for pts in ([hip, knee, foot], [neck, hand]):
            d.line([(P(a), P(b)) for a, b in pts], fill=col, width=P(w), joint="curve")
            for a, b in (pts[0], pts[-1]):
                d.ellipse([P(a - w / 2), P(b - w / 2), P(a + w / 2), P(b + w / 2)], fill=col)
        d.polygon([(P(a), P(b)) for a, b in [(neck[0] - 40 - ex, neck[1] - ex), (neck[0] + 40 + ex, neck[1] + 10), (hip[0] + 45 + ex, hip[1]), (hip[0] - 45 - ex, hip[1] + ex)]], fill=col)
        r = 55 + ex
        d.ellipse([P(head[0] - r), P(head[1] - r), P(head[0] + r), P(head[1] + r)], fill=col)
    hx, hy = head
    d.chord([P(hx - 60), P(hy - 75), P(hx + 60), P(hy + 30)], 180, 360, fill=RED)
    d.rounded_rectangle([P(hx - 66), P(hy - 32), P(hx + 66), P(hy - 14)], P(8), fill=(174, 58, 30))
    for i in range(3):
        sx, sy = hx + 75 + i * 16, hy - 30 + i * 28
        d.ellipse([P(sx), P(sy), P(sx + 13), P(sy + 20)], fill=(140, 200, 255))

def rain(d, t):
    rnd = random.Random(7)
    for _ in range(120):
        x0, sp = rnd.uniform(0, W + 200), rnd.uniform(1400, 2000)
        y = (rnd.uniform(0, H) + t * sp) % H
        x = x0 - y * 0.18
        d.line([(P(x), P(y)), (P(x - 10), P(y + 45))], fill=(200, 210, 255, 150), width=P(3))

def earth(img, t, t0):
    d = ImageDraw.Draw(img)
    k = back((t - t0) / 0.5)
    if k <= 0: return
    cx, cy, r = W / 2, 980, 230 * min(1.0, k)
    d.ellipse([P(cx - r - 14), P(cy - r - 14), P(cx + r + 14), P(cy + r + 14)], fill=(255, 220, 170, 70))
    d.ellipse([P(cx - r), P(cy - r), P(cx + r), P(cy + r)], fill=(60, 120, 200))
    rnd = random.Random(5)
    for _ in range(9):
        a, rr, s = rnd.uniform(0, 6.28), rnd.uniform(0, r * 0.7), rnd.uniform(0.18, 0.35) * r
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        d.ellipse([P(x - s), P(y - s * 0.7), P(x + s), P(y + s * 0.7)], fill=(90, 170, 100))
    # три витка вокруг Земли
    prog = ease((t - t0 - 0.4) / 4.0) * 3
    for lap in range(3):
        rr = r + 45 + lap * 32
        ext = max(0.0, min(1.0, prog - lap)) * 360
        if ext > 1:
            d.arc([P(cx - rr), P(cy - rr), P(cx + rr), P(cy + rr)], -90, -90 + ext, fill=GOLD, width=P(10))

def bars(img, t, t0):
    d = ImageDraw.Draw(img)
    base, maxh = 1350, 560
    for cx, name, col, val, tt in [(300, "МАКС", RED, 3_600_000, t0), (780, "САНЯ", YELLOW, 9_000_000, t0 + 2.2)]:
        p = ease((t - tt) / 1.6)
        if t < tt: continue
        h = maxh * val / 9_000_000 * p
        d.rounded_rectangle([P(cx - 120), P(base - h), P(cx + 120), P(base)], P(24), fill=col)
        text_c(d, cx, base - h - 90, money(val * p), F(58), CREAM, 4)
        text_c(d, cx, base + 25, name, F(52), col, 3)

# ---------- кадр ----------
def frame(t, timeline, scenes):
    sc, s0, s1 = next(((sc, a, b) for sc, a, b in scenes if a <= t < b), scenes[-1])
    lt = t - s0                          # время внутри сцены
    img = B.SKY.copy()
    B.tile(img, B.CITY_FAR, t * 25, P(GROUND_Y - 700))
    B.tile(img, B.CITY_NEAR, t * 60 + 400, P(GROUND_Y - 700))
    d = ImageDraw.Draw(img, "RGBA")
    B.road(d, t)

    if sc == 1:
        B.walker(d, 330, t * 7.5, RED); B.walker(d, 720, t * 7.5 + 1.3, YELLOW)
        big(d, 250, "$1", 0.0, lt, 230); big(d, 520, "ЗА КАЖДЫЙ МЕТР", 0.3, lt, 92, (255, 215, 120))
        pill(img, W / 2, 760, "КТО БОГАЧЕ?", 1.2, lt)
    elif sc == 2:
        B.walker(d, 540, t * 7.5, (120, 170, 255))
        card(img, 290, 260, 790, 420, [("ШАГОВ ЗА ДЕНЬ", "6 000", DARK)], 0.0, lt)
        big(d, 480, "= 4,5 КМ", 1.6, lt, 110)
        big(d, 620, "= $4 500", 2.6, lt, 110, GOLD)
        pill(img, W / 2, 840, "ЗА ГОД: $1 642 500", 4.2, lt, size=58, fg=(200, 120, 0))
    elif sc == 3:
        B.walker(d, 330, t * 7.5, RED); B.walker(d, 720, t * 7.5 + 1.3, YELLOW)
        big(d, 230, "ПРАВИЛА", 0.0, lt, 120)
        pill(img, W / 2, 470, "$1 = 1 МЕТР", 0.8, lt, size=70, fg=(200, 120, 0), rot=2)
        for i, w_ in enumerate(["МАШИНА", "ЛИФТ", "ДОРОЖКА"]):
            pill(img, 230 + i * 310, 650, "✕ " + w_, 3.0 + i * 0.35, lt, size=40, rot=(-4, 3, -2)[i])
        if lt > 1.6:
            text_c(d, 330, 820, "МАКС", F(50), RED, 3); text_c(d, 720, 820, "САНЯ", F(50), YELLOW, 3)
    elif sc == 4:
        run = ease(lt / 2.0) * 160
        B.walker(d, 330 + run, t * 12.0, RED); B.walker(d, 720 + run * 0.15, t * 7.0 + 1.3, YELLOW)
        p1, p2 = ease((lt - 0.5) / 3.0), ease((lt - 4.5) / 2.0)
        card(img, 150, 230, 930, 400, [("ДЕНЬ", "1", DARK), ("МАКС", money(60_000 * p1), MONEY), ("САНЯ", money(25_000 * p2), MONEY)], 0.0, lt)
        big(d, 440, "ДЕНЬ 1", 0.2, lt)
        pill(img, 760, 760, "ВСЮ НОЧЬ", 1.2, lt, size=52)
    elif sc == 5:
        B.walker(d, 490, t * 9.0, RED); B.walker(d, 720, t * 7.0 + 1.3, YELLOW)
        p = ease((lt - 0.3) / 2.2)
        card(img, 150, 230, 930, 400, [("ДЕНЬ", "2", DARK), ("МАКС", money(60_000 + 40_000 * p), MONEY), ("САНЯ", money(25_000 + 25_000 * p), MONEY)], 0.0, lt)
        big(d, 440, "ДЕНЬ 2", 0.1, lt)
        pill(img, 640, 760, "Макс · скрин $100 000", max(0.2, (s1 - s0) - 2.6), lt, size=46, fg=MONEY, rot=6)
    elif sc == 6:
        sitter(d, 180); B.walker(d, 720, t * 7.0 + 1.3, YELLOW)
        card(img, 150, 230, 930, 400, [("ДЕНЬ", "3", DARK), ("МАКС", "$100 000", (150, 150, 150)), ("САНЯ", money(50_000 + 25_000 * ease(lt / 3)), MONEY)], 0.0, lt)
        big(d, 440, "ДЕНЬ 3", 0.1, lt, col=(255, 150, 130))
        pill(img, 330, 700, "2 КМ / ДЕНЬ", (s1 - s0) * 0.45, lt, size=46, rot=-5)
        pill(img, 330, 820, "ПОТОМ 10 КМ", (s1 - s0) * 0.72, lt, size=46, rot=4, fg=(150, 90, 60))
    elif sc == 7:
        rain(d, t)
        B.walker(d, 330 + ease(lt / 3) * 120, t * 7.0 + 1.3, YELLOW)
        B.walker(d, 740, t * 4.5, RED, 0.9)
        p = ease((lt - (s1 - s0) * 0.55) / 1.2)
        card(img, 150, 230, 930, 400, [("ДЕНЬ", "5", DARK), ("МАКС", money(104_000 + 4_000 * p), MONEY), ("САНЯ", money(100_000 + 25_000 * p), MONEY)], 0.0, lt)
        big(d, 440, "ДЕНЬ 5", 0.1, lt)
        pill(img, W / 2, 700, "ОБГОН!", (s1 - s0) * 0.6, lt, bg=(255, 205, 40), fg=DARK, size=72, rot=-6)
    elif sc == 8:
        big(d, 150, "ГОД СПУСТЯ", 0.0, lt, 100)
        bars(img, lt, 0.8)
        pill(img, 780, 540, "×2,5", 4.0, lt, bg=(255, 205, 40), fg=DARK, size=64, rot=8)
        if lt > (s1 - s0) * 0.62:
            pill(img, W / 2, 1530, "ОН НИ РАЗУ НЕ ОСТАНОВИЛСЯ", (s1 - s0) * 0.62, lt, size=46, fg=(200, 70, 40), rot=-2)
    elif sc == 9:
        earth(img, lt, 0.6)
        d = ImageDraw.Draw(img, "RGBA")
        big(d, 230, "70 ЛЕТ ХОДЬБЫ", 0.0, lt, 90)
        big(d, 360, "115 000 КМ", 1.5, lt, 110, (255, 215, 120))
        pill(img, W / 2, 1380, "$115 000 000", (s1 - s0) * 0.55, lt, bg=(255, 205, 40), fg=DARK, size=80, rot=-3)
    elif sc == 10:
        B.walker(d, 330, t * 12.0, RED); B.walker(d, 720, t * 7.0 + 1.3, YELLOW)
        pill(img, 330, 600, "РВАНУТЬ", 0.5, lt, bg=(255, 205, 40), fg=DARK, size=64, rot=-6)
        pill(img, 740, 600, "ИДТИ", 1.6, lt, bg=CREAM, fg=(200, 70, 40), size=64, rot=5)
        big(d, 260, "А ТЫ?", 0.0, lt, 140)

    d = ImageDraw.Draw(img, "RGBA")
    subtitle(d, t, timeline)
    return img.convert("RGB").resize((W, H), Image.LANCZOS)

def build_scenes(timeline, total):
    out = []
    for sc in sorted({x[2] for x in timeline}):
        rows = [x for x in timeline if x[2] == sc]
        out.append((sc, rows[0][0], rows[-1][1]))
    out[-1] = (out[-1][0], out[-1][1], total + 1.0)
    return out

if __name__ == "__main__":
    voice = sys.argv[1]
    timeline, total = align(voice)
    scenes = build_scenes(timeline, total)
    json.dump({"timeline": timeline, "scenes": scenes}, open(os.path.join(OUT, "timing.json"), "w"), ensure_ascii=False, indent=1)
    if "--preview" in sys.argv:
        for sc, a, b in scenes:
            frame(a + (b - a) * 0.8, timeline, scenes).save(os.path.join(OUT, f"prev_{sc:02d}.png"))
        print("preview ok"); sys.exit()
    dur = total + 1.0
    silent = os.path.join(OUT, "_video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", silent],
                          stdin=subprocess.PIPE)
    n = int(dur * FPS)
    for i in range(n):
        ff.stdin.write(frame(i / FPS, timeline, scenes).tobytes())
        if i % 300 == 0: print(f"{i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", voice, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", os.path.join(OUT, "shorts_1_dollar_za_metr.mp4")], check=True)
    os.remove(silent); print("готово")
