"""Render a motivational kinetic-typography video from a script JSON and per-scene voice clips.

Layout per scene: a small caps header fades in, then the big line reveals word by word while the
narrator speaks it. Scene length follows its voice clip, so audio and text stay in sync.

Usage: python daily/make_video.py <slug>
  reads  daily/scripts/<slug>.json   and   daily/voice/<slug>/<NN>.mp3  (NN = scene index, 01..)
  writes daily/out/<slug>.mp4
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1920, 1080, 30, 48000
FONT_HEAD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_BIG = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
LEAD, TAIL = 0.35, 0.55  # silence before/after each voice clip inside its scene


def background():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / (W * 0.55)) ** 2 + ((y - H * 0.42) / (H * 0.75)) ** 2)
    v = np.clip(1 - r, 0, 1) ** 1.6
    base = 10 + 46 * v
    return np.repeat(base[..., None], 3, axis=2)


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def text_layer(text, font, y_top, max_w, upto_words=None):
    """RGBA layer with text centred horizontally, showing only the first `upto_words` words."""
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    lines = wrap(d, text, font, max_w)
    lh = int(font.size * 1.18)
    shown = 0
    for i, line in enumerate(lines):
        words = line.split()
        if upto_words is not None:
            k = max(0, min(len(words), upto_words - shown))
            shown += len(words)
            part = " ".join(words[:k])
        else:
            part = line
        full_w = d.textlength(line, font=font)
        d.text(((W - full_w) / 2, y_top + i * lh), part, font=font, fill=255)
    return img, len(lines) * lh


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def render(slug):
    spec = json.load(open(f"{ROOT}/scripts/{slug}.json"))
    vdir = f"{ROOT}/voice/{slug}"
    os.makedirs(f"{ROOT}/out", exist_ok=True)
    tmp = f"{ROOT}/out/.{slug}"
    os.makedirs(tmp, exist_ok=True)
    head_f, big_f = ImageFont.truetype(FONT_HEAD, 34), ImageFont.truetype(FONT_BIG, 74)
    bg = background()

    # voice: trim silence, measure, build the track
    scenes, t = [], 0.0
    voice = []
    for i, sc in enumerate(spec["scenes"], 1):
        src = sc.get("voice_file") or f"{vdir}/{i:02d}.mp3"
        wav = f"{tmp}/{i:02d}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                        "-ar", str(SR), "-ac", "1", "-f", "f32le", wav], check=True)
        a = np.fromfile(wav, dtype=np.float32)
        a = a / (np.abs(a).max() + 1e-9) * 0.9
        dur = LEAD + len(a) / SR + TAIL
        scenes.append((t, dur, len(a) / SR, sc))
        voice.append(np.concatenate([np.zeros(int(LEAD * SR), np.float32), a,
                                     np.zeros(int(TAIL * SR), np.float32)]))
        t += dur
    total = t + 0.4
    vtrack = np.zeros(int(total * SR), np.float32)
    pos = 0
    for v in voice:
        vtrack[pos:pos + len(v)] = v; pos += len(v)
    vtrack.tofile(f"{tmp}/voice.f32")
    make_music(total, f"{tmp}/music.f32", seed=sum(map(ord, slug)))

    # video frames
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f"{tmp}/voice.f32",
                            "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", f"{tmp}/music.f32",
                            "-filter_complex",
                            "[2:a]lowpass=f=900,lowpass=f=1800,volume=0.5[m];[1:a]aformat=channel_layouts=stereo,asplit=2[v][sc];"
                            "[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=500[d];"
                            "[d][v]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]",
                            "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                            "-shortest", f"{ROOT}/out/{slug}.mp4"], stdin=subprocess.PIPE)
    n_frames = int(total * FPS)
    cache = {}
    for f in range(n_frames):
        tt = f / FPS
        frame = bg.copy()
        breathe = 1 + 0.04 * np.sin(tt * 0.6)
        frame *= breathe
        cur = next((s for s in scenes if s[0] <= tt < s[0] + s[1]), None)
        if cur:
            start, dur, vdur, sc = cur
            lt = tt - start
            fade = ease(lt / 0.3) * ease((dur - lt) / 0.3)
            key = ("n", id(sc))
            if key not in cache:
                d = ImageDraw.Draw(Image.new("L", (1, 1)))
                cache[key] = len(wrap(d, sc["big"].upper(), big_f, 1600))
            head_y = 455 - cache[key] * 44
            big_y = head_y + 72
            key = ("h", id(sc))
            if key not in cache:
                cache[key] = np.asarray(text_layer(sc["head"].upper(), head_f, head_y, 1500)[0], np.float32) / 255
            h = cache[key] * ease(lt / 0.35) * 0.85
            nwords = len(sc["big"].split())
            reveal = (lt - LEAD) / max(vdur * 0.75, 0.3)
            k = nwords if reveal >= 1 else max(0, int(reveal * nwords) + 1) if lt >= LEAD else 0
            key = ("b", id(sc), k)
            if key not in cache:
                lay = text_layer(sc["big"].upper(), big_f, big_y, 1600, upto_words=k)[0]
                glow = lay.filter(ImageFilter.GaussianBlur(14))
                cache[key] = (np.asarray(lay, np.float32) / 255, np.asarray(glow, np.float32) / 255)
            b, g = cache[key]
            pulse = 1.0 if sc.get("accent") else 0.6
            alpha = np.clip(h + b + g * 0.55 * pulse, 0, 1)[..., None] * fade
            frame = frame * (1 - alpha) + 245 * alpha
        frame = np.clip(frame, 0, 255).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"saved daily/out/{slug}.mp4  ({total:.1f}s, {len(scenes)} scenes)")


def make_music(seconds, path, seed=0):
    """Original ambient pad: slow progression of detuned saws with a soft sub (low-passed at mix time)."""
    rng = np.random.default_rng(seed)
    progs = [[57, 53, 60, 55], [50, 46, 53, 48], [52, 48, 55, 50], [45, 41, 48, 43]]
    prog = progs[seed % len(progs)]
    t = np.arange(int(seconds * SR)) / SR
    out = np.zeros((len(t), 2), np.float32)
    chord_len = 4.0
    for ci in range(int(seconds / chord_len) + 1):
        root = prog[ci % len(prog)]
        a, b = int(ci * chord_len * SR), int(min((ci + 1) * chord_len + 1.5, seconds) * SR)
        if a >= len(t):
            break
        tt = t[a:b] - t[a]
        env = np.minimum(tt / 1.2, 1) * np.clip((chord_len + 1.5 - tt) / 1.5, 0, 1)
        for semi, amp in [(0, 0.5), (3, 0.35), (7, 0.35), (12, 0.2), (-12, 0.3)]:
            f0 = 440 * 2 ** ((root + semi - 69) / 12)
            for ch, det in enumerate((-0.12, 0.12)):
                ph = rng.random()
                x = 2 * ((f0 * (1 + det / 100) * tt + ph) % 1) - 1
                out[a:b, ch] += (amp * env * x).astype(np.float32)
    sub = 0.25 * np.sin(2 * np.pi * 440 * 2 ** ((prog[0] - 24 - 69) / 12) * t)
    out += sub[:, None].astype(np.float32)
    fade = np.minimum(t / 2.0, 1) * np.clip((seconds - t) / 2.5, 0, 1)
    out *= fade[:, None]
    out = out / (np.abs(out).max() + 1e-9) * 0.35
    out.astype(np.float32).tofile(path)


if __name__ == "__main__":
    render(sys.argv[1])
