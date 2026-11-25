# $1 за каждый метр / $1 for every meter

Вертикальный шорт 1080×1920, 30 fps, графика нарисована кодом (Pillow + ffmpeg), озвучка ElevenLabs (eleven_v4).

| Файл | Что это |
|---|---|
| `video/ru.mp4` | Русская версия, 1:37, голос Makos |
| `video/en.mp4` | Английская версия, 1:38, голос Jeffery S |
| `audio/ru.mp3`, `audio/en.mp3` | Озвучка целиком (один файл на ролик) |
| `timing/ru.json`, `timing/en.json` | `timeline`: `[начало, конец, сцена, фраза]` в секундах; `scenes`: `[сцена, начало, конец]` |
| `code/` | `scene2.py` (фон, персонажи), `video.py` (RU), `video_en.py` (EN) |

Тайминги фраз подобраны по паузам в озвучке (ffmpeg silencedetect), точность ±0,5 с.

Сцены: 1 крючок · 2 расчёт шагов · 3 правила · 4 день 1 · 5 день 2 · 6 день 3 · 7 день 5 (обгон) · 8 через год · 9 за 70 лет · 10 вопрос зрителю.

Сборка: `cd code && python3 video.py ../audio/ru.mp3` (нужны Pillow, ffmpeg, шрифт DejaVu Sans Bold).
