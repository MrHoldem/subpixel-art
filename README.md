# Subpixel Art Converter

Простой модуль для конвертации изображения в субпиксельный арт (RGB).

## Установка
```bash
pip install -r requirements.txt
```

## CLI
```bash
python cli.py input.jpg output.png --width 800 --grayscale
# или 1-bit + dithering
python cli.py input.jpg output.png --width 800 --dither
```

## Использование как модуль
```python
from subpixel_art import make_subpixel_art
from subpixel_art.converter import SubpixelOptions

out = make_subpixel_art("input.jpg", "out.png", SubpixelOptions(final_width=800))
```
