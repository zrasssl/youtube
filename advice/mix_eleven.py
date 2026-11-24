"""Lay ElevenLabs clips on the Advice_EN timeline and duck the original music under them."""
import os, sys, subprocess
import numpy as np, soundfile as sf

D = os.path.join(os.path.dirname(__file__), "eleven")
video = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "Advice_EN_elevenlabs.mp4")
# clip id -> second its on-screen text appears
SCENES = [("01", 0.4), ("02", 4.4), ("03", 7.4), ("04", 11.0), ("05", 14.9), ("06", 18.0), ("07", 22.0),
          ("08", 26.0), ("09", 30.3), ("11", 34.4), ("12", 38.0), ("13", 41.0), ("14", 46.0), ("15", 49.0)]
SR, EARLY, SLACK, GAP, MAX_TEMPO = 48000, 0.3, 0.4, 0.12, 1.25
total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "csv=p=0", video]))
track = np.zeros(int((total + 1) * SR), np.float32)
prev_end = 0.0
for i, (cid, s) in enumerate(SCENES):
    w, _ = sf.read(f"{D}/{cid}.wav", dtype="float32")  # already silence-trimmed, 48 kHz mono
    start = max(s - EARLY, prev_end + GAP) if i else s
    limit = (SCENES[i + 1][1] + SLACK) if i + 1 < len(SCENES) else total - 0.3
    tempo = min(max(len(w) / SR / (limit - start), 1.0), MAX_TEMPO)
    if tempo > 1.0:
        out = f"{D}/{cid}_fit.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{D}/{cid}.wav", "-af", f"atempo={tempo:.3f}", out], check=True)
        w, _ = sf.read(out, dtype="float32")
    w = w / (np.abs(w).max() + 1e-9) * 0.9
    a = int(start * SR); track[a:a + len(w)] += w
    prev_end = start + len(w) / SR
    print(f"{cid}: text {s:5.1f}s  voice {start:5.2f}-{prev_end:5.2f}s  tempo {tempo:.2f}")
vpath = f"{D}/voice_track.wav"
sf.write(vpath, np.clip(track[: int(total * SR)], -1, 1), SR)
flt = ("[0:a]aresample=48000,volume=0.55[m];[1:a]asplit=2[v][sc];"
       "[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];"
       "[duck][v]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", vpath, "-filter_complex", flt, "-map", "0:v",
                "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst], check=True)
print("saved", dst)
