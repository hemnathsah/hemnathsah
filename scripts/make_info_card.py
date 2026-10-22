#!/usr/bin/env python3
"""Create a custom animated terminal/neofetch card for Hemnath Sah."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "info-card.svg"

ROWS = [
    ("Focus", "Network automation + CCNA labs"),
    ("Project", "CCNA-Diagram-AI (in development)"),
    ("Core", "Python / Flask / PostgreSQL"),
    ("AI", "Local models with Ollama"),
    ("Systems", "Linux / RHEL / Git"),
    ("Approach", "Deterministic + testable"),
    ("Web", "hemnathsah.github.io"),
]


def main() -> None:
    width, height = 490, 320
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
        '<title id="title">Hemnath Sah terminal info card</title>',
        '<rect x="1" y="1" width="488" height="318" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '<rect x="1" y="1" width="488" height="38" rx="12" fill="#161b22"/>',
        '<path d="M1 27 H489 V39 H1 Z" fill="#161b22"/>',
        '<circle cx="20" cy="20" r="4" fill="#ff5f56"/><circle cx="34" cy="20" r="4" fill="#ffbd2e"/><circle cx="48" cy="20" r="4" fill="#27c93f"/>',
        '<text x="68" y="24" fill="#c9d1d9" font-family="monospace" font-size="12">hemnath@github:~</text>',
        '<text x="22" y="64" fill="#39d353" font-family="monospace" font-size="18" font-weight="bold">HEMNATH SAH</text>',
        '<text x="22" y="82" fill="#8b949e" font-family="monospace" font-size="10">developer profile / system info</text>',
        '<path d="M22 94 H468" stroke="#30363d"/>',
    ]
    y = 120
    for idx, (label, value) in enumerate(ROWS):
        delay = 0.15 + idx * 0.15
        plateau = min(delay / 1.5, 0.78)
        parts.append(
            f'<g opacity="1"><animate attributeName="opacity" values="0;0;1" keyTimes="0;{plateau:.3f};1" begin="0s" dur="1.5s" fill="freeze"/>'
            f'<text x="22" y="{y}" fill="#79c0ff" font-family="monospace" font-size="11">{label:10}</text>'
            f'<text x="116" y="{y}" fill="#c9d1d9" font-family="monospace" font-size="10">{value}</text></g>'
        )
        y += 25
    parts.extend([
        '<path d="M22 294 H468" stroke="#30363d"/>',
        '<text x="22" y="309" fill="#8b949e" font-family="monospace" font-size="9">LOCAL-FIRST · OPEN SOURCE LEARNING · BUILD IN PUBLIC</text>',
        '</svg>',
    ])
    OUTPUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
