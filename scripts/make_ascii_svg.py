#!/usr/bin/env python3
"""Convert a personal photo into a monochrome, self-typing ASCII SVG.

Requires Pillow (scripts/requirements-portrait.txt). Processing is local.
"""
from __future__ import annotations

import argparse
import html
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - helpful CLI message
    raise SystemExit(
        "Pillow is required for portrait generation. Install it with: "
        "python -m pip install -r scripts/requirements-portrait.txt"
    ) from exc

RAMP = " .`:-=+*cs#%@"


def convert(input_path: Path, output_path: Path, columns: int = 55, rows: int = 34) -> None:
    if not input_path.is_file():
        raise SystemExit(f"Input photo not found: {input_path}")
    with Image.open(input_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        # A portrait crop works best, but ImageOps.fit safely handles other aspect ratios.
        image = ImageOps.fit(image, (columns, rows), method=Image.Resampling.LANCZOS, centering=(0.5, 0.42))
        image = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
        pixels = list(image.getdata())

    lines = []
    for y in range(rows):
        line = ""
        for x in range(columns):
            brightness = pixels[y * columns + x]
            # White pixels map to spaces; dark pixels map to dense glyphs.
            index = round((255 - brightness) / 255 * (len(RAMP) - 1))
            line += RAMP[index]
        lines.append(line)

    font_size = 7.5
    char_width = 7.2
    row_height = 9.2
    left, top = 18, 54
    width = 450
    height = int(top + rows * row_height + 28)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
        '<title id="title">Hemnath Sah animated ASCII portrait</title>',
        f'<rect width="{width}" height="{height}" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '<rect x="1" y="1" width="448" height="37" rx="11" fill="#161b22"/>',
        '<path d="M1 27 H449 V38 H1 Z" fill="#161b22"/>',
        '<circle cx="20" cy="19" r="4" fill="#ff5f56"/><circle cx="34" cy="19" r="4" fill="#ffbd2e"/><circle cx="48" cy="19" r="4" fill="#27c93f"/>',
        '<text x="68" y="23" fill="#c9d1d9" font-family="monospace" font-size="12">hemnath@github ~ $ whoami</text>',
    ]
    clip_width = columns * char_width
    for row, line in enumerate(lines):
        y = top + row * row_height
        begin = row * 0.055
        clip_id = f"row{row}"
        parts.append(
            f'<clipPath id="{clip_id}"><rect x="{left}" y="{y - row_height + 1}" width="{clip_width}" height="{row_height}">'
            f'<animate attributeName="width" from="0" to="{clip_width}" begin="{begin:.3f}s" dur="0.52s" fill="freeze"/>'
            f'</rect></clipPath>'
        )
        parts.append(
            f'<text x="{left}" y="{y}" fill="#c9d1d9" font-family="monospace" font-size="{font_size}" '
            f'xml:space="preserve" clip-path="url(#{clip_id})">{html.escape(line)}</text>'
        )
    parts.extend([
        f'<text x="18" y="{height - 12}" fill="#8b949e" font-family="monospace" font-size="9">MONOCHROME ASCII · GENERATED LOCALLY FROM YOUR PHOTO</text>',
        '</svg>',
    ])
    output_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}. Preview it before committing; the SVG is public when you push it.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local photo to convert")
    parser.add_argument("--output", type=Path, default=Path("hemnath-ascii.svg"), help="SVG output path")
    parser.add_argument("--columns", type=int, default=55)
    parser.add_argument("--rows", type=int, default=34)
    args = parser.parse_args()
    convert(args.input, args.output, args.columns, args.rows)


if __name__ == "__main__":
    main()
