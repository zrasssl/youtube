#!/usr/bin/env python3
"""Бесплатная озвучка через edge-tts (голоса Microsoft Edge).

Примеры:
  python voiceover.py text.txt -o voice.mp3
  python voiceover.py subs.srt -o voice.mp3
  python voiceover.py subs.srt --video in.mp4 -o out.mp4
  python voiceover.py --list-voices ru
"""
import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import edge_tts

SAMPLE_RATE = 24000
DEFAULT_VOICE = "ru-RU-DmitryNeural"
MAX_SPEEDUP = 1.6  # во сколько раз можно ускорить фразу, чтобы влезла в субтитр


def run_ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def get_proxy(cli_proxy):
    return cli_proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")


async def synthesize(text, out_mp3, voice, rate, pitch, volume, proxy):
    """Озвучивает текст в mp3. Повторяет попытку при сетевых сбоях."""
    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(
                text, voice, rate=rate, pitch=pitch, volume=volume, proxy=proxy
            )
            await comm.save(str(out_mp3))
            return
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2 * (attempt + 1))


def to_wav(src, dst, speed=1.0):
    """Конвертирует в WAV 24 кГц моно, при необходимости ускоряя (atempo)."""
    filters = []
    s = speed
    while s > 2.0:  # atempo принимает максимум 2.0 за раз
        filters.append("atempo=2.0")
        s /= 2.0
    if abs(s - 1.0) > 1e-3:
        filters.append(f"atempo={s:.4f}")
    args = ["-i", str(src), "-ac", "1", "-ar", str(SAMPLE_RATE)]
    if filters:
        args += ["-filter:a", ",".join(filters)]
    run_ffmpeg(*args, str(dst))


def wav_frames(path):
    with wave.open(str(path), "rb") as w:
        return w.readframes(w.getnframes())


def frames_duration(frames):
    return len(frames) / 2 / SAMPLE_RATE  # 16 бит моно


# ---------- SRT ----------

TIME_RE = re.compile(
    r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)"
)


def parse_srt(text):
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "").strip()):
        lines = block.strip().split("\n")
        for i, line in enumerate(lines):
            m = TIME_RE.search(line)
            if m:
                g = [int(x) for x in m.groups()]
                start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
                end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
                body = " ".join(lines[i + 1:]).strip()
                body = re.sub(r"<[^>]+>|\{[^}]+\}", "", body)  # убрать теги
                if body:
                    cues.append((start, end, body))
                break
    return cues


async def build_from_srt(cues, out_wav, tmp, tts_kwargs, concurrency=4):
    sem = asyncio.Semaphore(concurrency)

    async def one(i, text):
        async with sem:
            mp3 = tmp / f"cue{i:05d}.mp3"
            await synthesize(text, mp3, **tts_kwargs)
            print(f"  [{i + 1}/{len(cues)}] {text[:60]}", file=sys.stderr)
            return mp3

    mp3s = await asyncio.gather(*(one(i, c[2]) for i, c in enumerate(cues)))

    out = bytearray()
    for i, ((start, end, _), mp3) in enumerate(zip(cues, mp3s)):
        wav = tmp / f"cue{i:05d}.wav"
        to_wav(mp3, wav)
        frames = wav_frames(wav)
        dur = frames_duration(frames)
        next_start = cues[i + 1][0] if i + 1 < len(cues) else None
        slot = (next_start if next_start is not None else end) - start
        if slot > 0 and dur > slot and next_start is not None:
            speed = min(dur / slot, MAX_SPEEDUP)
            to_wav(mp3, wav, speed)
            frames = wav_frames(wav)
        # тишина до начала фразы
        cur = frames_duration(out)
        if start > cur:
            out += b"\x00\x00" * int((start - cur) * SAMPLE_RATE)
        out += frames

    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(out))


# ---------- сборка ----------

def export_audio(wav, out):
    if out.suffix.lower() == ".wav":
        shutil.copy(wav, out)
    else:
        run_ffmpeg("-i", str(wav), "-b:a", "192k", str(out))


def mux_video(video, voice_wav, out, original_volume):
    if original_volume <= 0:
        run_ffmpeg(
            "-i", str(video), "-i", str(voice_wav),
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", str(out),
        )
        return
    has_audio = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    ).stdout.strip()
    if not has_audio:
        return mux_video(video, voice_wav, out, 0)
    run_ffmpeg(
        "-i", str(video), "-i", str(voice_wav),
        "-filter_complex",
        f"[0:a]volume={original_volume}[bg];"
        "[bg][1:a]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "192k", str(out),
    )


async def list_voices(prefix):
    voices = await edge_tts.list_voices()
    for v in sorted(voices, key=lambda v: v["ShortName"]):
        if v["Locale"].lower().startswith(prefix.lower()):
            print(f'{v["ShortName"]:35} {v["Gender"]}')


async def main():
    p = argparse.ArgumentParser(description="Бесплатная озвучка через edge-tts")
    p.add_argument("input", nargs="?", help="файл .txt или .srt")
    p.add_argument("-o", "--output", help="результат: .mp3/.wav или .mp4 с --video")
    p.add_argument("--voice", default=DEFAULT_VOICE, help=f"голос (по умолчанию {DEFAULT_VOICE})")
    p.add_argument("--rate", default="+0%", help="скорость речи, например +10%% или -5%%")
    p.add_argument("--pitch", default="+0Hz", help="высота голоса, например -5Hz")
    p.add_argument("--volume", default="+0%", help="громкость, например +20%%")
    p.add_argument("--video", help="видео, на которое наложить озвучку")
    p.add_argument("--original-volume", type=float, default=0.15,
                   help="громкость исходного звука видео (0 = убрать, 1 = как есть)")
    p.add_argument("--proxy", help="прокси (по умолчанию из HTTPS_PROXY)")
    p.add_argument("--list-voices", metavar="ЯЗЫК", help="показать голоса, например ru или en-US")
    a = p.parse_args()

    if a.list_voices:
        await list_voices(a.list_voices)
        return
    if not a.input or not a.output:
        p.error("нужны входной файл и -o")
    if not shutil.which("ffmpeg"):
        sys.exit("Не найден ffmpeg — установите его (https://ffmpeg.org).")

    src = Path(a.input)
    out = Path(a.output)
    text = src.read_text(encoding="utf-8-sig")
    tts_kwargs = dict(voice=a.voice, rate=a.rate, pitch=a.pitch,
                      volume=a.volume, proxy=get_proxy(a.proxy))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        voice_wav = tmp / "voice.wav"
        if src.suffix.lower() == ".srt":
            cues = parse_srt(text)
            if not cues:
                sys.exit("В .srt не найдено ни одного субтитра.")
            print(f"Озвучиваю {len(cues)} субтитров голосом {a.voice}…", file=sys.stderr)
            await build_from_srt(cues, voice_wav, tmp, tts_kwargs)
        else:
            print(f"Озвучиваю текст голосом {a.voice}…", file=sys.stderr)
            mp3 = tmp / "voice.mp3"
            await synthesize(text, mp3, **tts_kwargs)
            to_wav(mp3, voice_wav)

        if a.video:
            mux_video(Path(a.video), voice_wav, out, a.original_volume)
        else:
            export_audio(voice_wav, out)
    print(f"Готово: {out}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
