#!/usr/bin/env python3
"""Render fetched GitHub contributions into a self-contained animated SVG."""
from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "contributions.json"
OUTPUT = ROOT / "contrib-heatmap.svg"
USERNAME = "hemnathsah"
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def read_data() -> tuple[dict[date, dict], str, bool]:
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, "Waiting for first live sync", False
    if payload.get("status") != "live" or not payload.get("days"):
        return {}, "Waiting for first live sync", False
    entries: dict[date, dict] = {}
    for item in payload["days"]:
        try:
            day = date.fromisoformat(item["date"])
            count = max(0, int(item.get("count", 0)))
            level = max(0, min(4, int(item.get("level", 0))))
            entries[day] = {"count": count, "level": level}
        except (KeyError, TypeError, ValueError):
            continue
    if len(entries) < 300:
        return {}, "Waiting for first live sync", False
    total = sum(v["count"] for v in entries.values())
    generated_at = payload.get("generated_at", "")
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        stamp = generated.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError, AttributeError):
        stamp = "date unavailable"
    return entries, f"{total:,} contributions in the captured calendar · updated {stamp}", True


def build_svg() -> str:
    data, footer, is_live = read_data()
    width, height = 860, 178
    cell, gap = 10, 3
    step = cell + gap
    grid_x, grid_y = 110, 48
    columns, rows = 53, 7

    if data:
        last = max(data)
    else:
        last = date.today()
    # The display window is exactly 53 full Monday-to-Sunday weeks.
    end_sunday = last + timedelta(days=(6 - last.weekday()))
    start_monday = end_sunday - timedelta(days=52 * 7 + 6)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Hemnath Sah GitHub contributions</title>',
        '<desc id="desc">A 53-week contribution heatmap generated from the public GitHub contribution calendar.</desc>',
        '<rect width="100%" height="100%" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '<circle cx="22" cy="19" r="4" fill="#ff5f56"/><circle cx="36" cy="19" r="4" fill="#ffbd2e"/><circle cx="50" cy="19" r="4" fill="#27c93f"/>',
        '<text x="70" y="23" fill="#c9d1d9" font-family="monospace" font-size="12">hemnath@github ~ /contributions</text>',
    ]

    # Month labels at the first visible week of each month.
    last_month = None
    for week in range(columns):
        monday = start_monday + timedelta(days=week * 7)
        if monday.month != last_month:
            label = monday.strftime("%b")
            out.append(f'<text x="{grid_x + week * step}" y="40" fill="#8b949e" font-family="monospace" font-size="10">{label}</text>')
            last_month = monday.month

    for row, label in [(0, "Mon"), (2, "Wed"), (4, "Fri")]:
        out.append(f'<text x="28" y="{grid_y + row * step + 8}" fill="#8b949e" font-family="monospace" font-size="9">{label}</text>')

    for week in range(columns):
        for row in range(rows):
            current = start_monday + timedelta(days=week * 7 + row)
            value = data.get(current, {"count": 0, "level": 0})
            level = max(0, min(4, int(value.get("level", 0))))
            count = max(0, int(value.get("count", 0)))
            x, y = grid_x + week * step, grid_y + row * step
            delay = min(week * 0.012 + row * 0.007, 0.9)
            out.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{PALETTE[level]}" stroke="#30363d" stroke-width="0.35" aria-label="{current.isoformat()}: {count} contributions">'
                f'<title>{current.isoformat()}: {count} contributions</title>'
                f'<animate attributeName="opacity" from="0.18" to="1" begin="{delay:.3f}s" dur="0.38s" fill="freeze"/>'
                '</rect>'
            )

    out.append('<text x="28" y="158" fill="#8b949e" font-family="monospace" font-size="10">Less</text>')
    for i, color in enumerate(PALETTE):
        out.append(f'<rect x="{62 + i * 13}" y="149" width="10" height="10" rx="2" fill="{color}" stroke="#30363d" stroke-width="0.35"/>')
        if i == 0:
            continue
    out.append('<text x="132" y="158" fill="#8b949e" font-family="monospace" font-size="10">More</text>')
    if not is_live:
        footer = "Waiting for first live sync · GitHub Actions → Update profile art → Run workflow"
    out.append(f'<text x="28" y="173" fill="#8b949e" font-family="monospace" font-size="9">{html.escape(footer)}</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"


def main() -> None:
    OUTPUT.write_text(build_svg(), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
