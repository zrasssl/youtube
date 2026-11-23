"""Transcribe each clip with Whisper to catch garbled or skipped words."""
import os, sys, soundfile as sf, torch
sys.path.insert(0, os.path.dirname(__file__))
from voiceover import CLIPS, OUT
from transformers import pipeline
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", torch_dtype=torch.float32)
only = set(sys.argv[1:])
for cid, start, maxlen, voice, text, _ in CLIPS:
    if only and cid not in only: continue
    a, sr = sf.read(f"{OUT}/{cid}.wav")
    r = asr({"raw": a, "sampling_rate": sr}, generate_kwargs={"language": "en"})
    print(f"{cid} | want: {text}\n    | got:  {r['text'].strip()}")
