"""Emotional English voice-over for Advice_EN.mp4 using VoiceStudio OmniVoice.

Usage: python advice/voiceover.py [clip_id ...]   (no args = generate all missing clips)
"""
import os, sys, time
import numpy as np, soundfile as sf, torch
from voicestudio.models.ommivoice import OmniVoiceForConditionalGeneration, OmniVoiceProcessor

OUT = os.path.join(os.path.dirname(__file__), "clips")
os.makedirs(OUT, exist_ok=True)

NARRATOR = "male, middle-aged, low pitch, american accent"
# id, start_sec, max_len_sec, voice ("narrator" = cloned narrator, else voice-design attributes), text, speed
CLIPS = [
    ("01", 0.4, 3.6, "narrator", "Want to understand a person? Listen to the advice they give.", None),
    ("02", 4.4, 2.9, "narrator", "In every knock... a mechanic hears a breakdown.", None),
    ("03", 7.4, 2.0, "narrator", "Someone who got ahead by taking risks will say:", None),
    ("03q", 9.5, 1.4, "male, young adult, moderate pitch, american accent", "Risk it all!", None),
    ("04", 11.0, 2.4, "narrator", "Someone who lost everything on a risk will say:", None),
    ("04q", 13.5, 1.4, "male, elderly, low pitch, american accent", "[sigh] Play it safe.", None),
    ("05", 14.9, 2.1, "narrator", "A mom who never finished school will say:", None),
    ("05q", 17.0, 1.0, "female, middle-aged, moderate pitch, american accent", "Study.", None),
    ("06", 18.0, 2.0, "narrator", "Someone who grew up with no money will say:", None),
    ("06q", 20.0, 1.9, "male, middle-aged, very low pitch, american accent", "Money first... dreams later.", None),
    ("07", 22.0, 2.9, "narrator", "A friend who quit... and is happy, will say:", None),
    ("07q", 25.0, 1.0, "female, young adult, high pitch, american accent", "[laughter] Quit!", None),
    ("08", 26.0, 2.5, "narrator", "And someone who never even tried will say:", None),
    ("08q", 28.5, 1.4, "male, young adult, low pitch, american accent", "It's impossible.", None),
    ("09", 30.3, 1.6, "narrator", "None of them is lying.", None),
    ("10", 32.0, 2.3, "narrator", "They're just telling... their own story.", None),
    ("11", 34.4, 3.5, "narrator", "Any piece of advice is someone's whole life... squeezed into one line.", None),
    ("12", 38.0, 2.8, "narrator", "Listen to advice like stories... not like orders.", None),
    ("13", 41.0, 4.6, "narrator", "And every time, ask yourself: is this about my life... or theirs?", None),
    ("14", 46.0, 2.6, "narrator", "Because the one who lives with the decision... is you.", None),
    ("15", 49.0, 3.4, "narrator", "Subscribe, if you sometimes need a push forward.", None),
]
REF_ID = "01"

def main(only):
    torch.set_num_threads(os.cpu_count())
    proc = OmniVoiceProcessor.from_pretrained("k2-fsa/OmniVoice")
    model = OmniVoiceForConditionalGeneration.from_pretrained("k2-fsa/OmniVoice").eval()
    sr = proc.sampling_rate
    # reference clip first so the narrator voice is fixed for the rest
    order = sorted(CLIPS, key=lambda c: c[0] != REF_ID)
    for cid, start, maxlen, voice, text, speed in order:
        path = f"{OUT}/{cid}.wav"
        if only and cid not in only: continue
        if not only and os.path.exists(path): continue
        torch.manual_seed(int(cid[:2]) * 7 + 1)
        kw = dict(text=text, language="English")
        if voice == "narrator" and cid != REF_ID:
            ref, rsr = sf.read(f"{OUT}/{REF_ID}.wav")
            kw.update(reference_audio=ref, reference_text=CLIPS[0][4], sampling_rate=rsr)
        else:
            kw["instruct"] = NARRATOR if voice == "narrator" else voice
        if speed: kw["speed"] = speed
        t = time.time()
        with torch.inference_mode():
            codes = model.generate(**proc(**kw))
        wav = np.asarray(proc.batch_decode(codes)[0], dtype=np.float32)
        sf.write(path, wav, sr)
        print(f"{cid}: {len(wav)/sr:.2f}s (slot {maxlen}s) in {time.time()-t:.0f}s  {text}", flush=True)

if __name__ == "__main__":
    main(set(sys.argv[1:]))
