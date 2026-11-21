# youtube

## Бесплатная озвучка (`voiceover.py`)

Озвучивает текст или субтитры голосами Microsoft Edge через [edge-tts](https://github.com/rany2/edge-tts). Это бесплатно и без API-ключа.

### Установка

1. Python 3.9+ и [ffmpeg](https://ffmpeg.org/download.html) (`ffmpeg` должен запускаться из терминала).
2. `pip install -r requirements.txt`

### Использование

```bash
# Текст -> mp3
python voiceover.py text.txt -o voice.mp3

# Субтитры -> озвучка, каждая фраза встаёт на своё время
python voiceover.py subs.srt -o voice.mp3

# Субтитры -> готовое видео (оригинальный звук приглушается до 15%)
python voiceover.py subs.srt --video in.mp4 -o out.mp4

# Полностью заменить звук видео
python voiceover.py subs.srt --video in.mp4 --original-volume 0 -o out.mp4

# Другой голос, быстрее и ниже
python voiceover.py text.txt -o voice.mp3 --voice ru-RU-SvetlanaNeural --rate +10% --pitch -5Hz

# Список голосов
python voiceover.py --list-voices ru
```

Русские голоса: `ru-RU-DmitryNeural` (мужской, по умолчанию) и `ru-RU-SvetlanaNeural` (женский).

Если фраза не помещается до следующего субтитра, она ускоряется, но не больше чем в 1.6 раза.
