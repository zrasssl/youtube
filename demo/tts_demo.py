import sys, time
import soundfile as sf
import torch
from voicestudio.models.ommivoice import OmniVoiceForConditionalGeneration, OmniVoiceProcessor

text = sys.argv[1] if len(sys.argv) > 1 else (
    "Привет! Добро пожаловать на мой канал. "
    "Сегодня я расскажу вам кое-что очень интересное, так что устраивайтесь поудобнее."
)
out = sys.argv[2] if len(sys.argv) > 2 else "demo/voice_demo.wav"
instruct = sys.argv[3] if len(sys.argv) > 3 else "male, middle-aged, low pitch"

torch.set_num_threads(4)
model_id = "k2-fsa/OmniVoice"
processor = OmniVoiceProcessor.from_pretrained(model_id)
model = OmniVoiceForConditionalGeneration.from_pretrained(model_id).eval()

t = time.time()
inputs = processor(text=text, language="Russian", instruct=instruct)
with torch.inference_mode():
    codes = model.generate(**inputs)
wave = processor.batch_decode(codes)[0]
sf.write(out, wave, processor.sampling_rate)
print(f"saved {out}: {len(wave)/processor.sampling_rate:.1f}s audio, generated in {time.time()-t:.0f}s")
