from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image


@dataclass
class SubpixelOptions:
    final_width: Optional[int] = None  # итоговая физическая ширина
    grayscale: bool = True  # если False -> 1-bit + dither
    dither: bool = False
    keep_aspect: bool = True


def make_subpixel_art(input_path: str, output_path: str, options: Optional[SubpixelOptions] = None) -> str:
    """
    Конвертирует изображение в субпиксельный арт (RGB). Возвращает путь к выходному файлу.
    """
    if options is None:
        options = SubpixelOptions()

    img = Image.open(input_path)

    # Расчет пропорций
    if options.final_width:
        if options.keep_aspect:
            w_percent = options.final_width / float(img.size[0])
            final_height = int(float(img.size[1]) * float(w_percent))
        else:
            final_height = img.size[1]
        final_width = options.final_width
    else:
        final_width = img.size[0]
        final_height = img.size[1]

    # Рабочая ширина x3
    working_width = final_width * 3
    img = img.resize((working_width, final_height), Image.Resampling.LANCZOS)

    # Градации серого / дизеринг
    if options.grayscale:
        bw = img.convert("L")
    else:
        # 1-bit + dithering
        dither = Image.Dither.FLOYDSTEINBERG if options.dither else Image.Dither.NONE
        bw = img.convert("1", dither=dither).convert("L")

    bw_array = np.array(bw, dtype=np.uint8)

    # Субпиксельная упаковка
    out_array = np.zeros((final_height, final_width, 3), dtype=np.uint8)
    out_array[:, :, 0] = bw_array[:, 0::3]
    out_array[:, :, 1] = bw_array[:, 1::3]
    out_array[:, :, 2] = bw_array[:, 2::3]

    result_img = Image.fromarray(out_array, mode="RGB")

    if not output_path.lower().endswith((".png", ".bmp")):
        output_path = output_path.rsplit(".", 1)[0] + ".png"

    result_img.save(output_path, format="PNG")
    return output_path
