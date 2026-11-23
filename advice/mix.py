"""Place generated clips on the timeline, duck the original music, and mux into the video."""
import os, sys, subprocess
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from voiceover import CLIPS, OUT

video = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "Advice_EN_voiceover.mp4")
SR = 48000
total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "csv=p=0", video]))
voice = np.zeros(int(total * SR) + SR, dtype=np.float32)
for cid, start, maxlen, *_ in CLIPS:
    src = f"{OUT}/{cid}.wav"
    tmp = f"{OUT}/{cid}_48k.wav"
    wav, sr = sf.read(src)
    dur = len(wav) / sr - 0.15  # decoder pads ~0.1s each side
    tempo = min(max(dur / maxlen, 1.0), 1.3)  # speed up only when it overflows its slot
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    f"silenceremove=start_periods=1:start_threshold=-45dB,atempo={tempo:.3f}",
                    "-ar", str(SR), "-ac", "1", tmp], check=True)
    w, _ = sf.read(tmp, dtype="float32")
    w = w / (np.abs(w).max() + 1e-9) * 0.9
    i = int(start * SR)
    j = min(i + len(w), len(voice))
    voice[i:j] += w[: j - i]
    print(f"{cid}: {start:5.1f}s  {len(w)/SR:.2f}s/{maxlen}s  tempo {tempo:.2f}")
vpath = f"{OUT}/voice_track.wav"
sf.write(vpath, np.clip(voice, -1, 1), SR)
# duck music under the voice with sidechain compression, then mix
flt = ("[0:a]aresample=48000,volume=0.55[m];[1:a]asplit=2[v][sc];"
       "[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];"
       "[duck][v]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", vpath, "-filter_complex", flt,
                "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", dst], check=True)
print("saved", dst)
