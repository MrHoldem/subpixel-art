#!/usr/bin/env python3
import argparse
from subpixel_art import make_subpixel_art
from subpixel_art.converter import SubpixelOptions


def main():
    p = argparse.ArgumentParser(description="Subpixel art converter")
    p.add_argument("input", help="input image path")
    p.add_argument("output", help="output image path (.png/.bmp)")
    p.add_argument("--width", type=int, default=None, help="final physical width")
    p.add_argument("--grayscale", action="store_true", help="use grayscale (default)")
    p.add_argument("--dither", action="store_true", help="use 1-bit + dithering")
    p.add_argument("--no-aspect", action="store_true", help="do not keep aspect ratio")

    args = p.parse_args()

    options = SubpixelOptions(
        final_width=args.width,
        grayscale=True if (args.grayscale or not args.dither) else False,
        dither=args.dither,
        keep_aspect=not args.no_aspect,
    )

    out = make_subpixel_art(args.input, args.output, options)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
