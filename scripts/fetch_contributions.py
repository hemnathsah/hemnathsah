#!/usr/bin/env python3
"""Fetch the public GitHub contribution calendar without a personal access token."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "hemnathsah"
URL = f"https://github.com/users/{USERNAME}/contributions"
OUTPUT = ROOT / "data" / "contributions.json"


def level_for(count: int, max_count: int) -> int:
    if count <= 0:
        return 0
    if max_count <= 1:
        return 4
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def main() -> int:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; hemnathsah-profile-art/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERROR: Could not fetch {URL}: {exc}", file=sys.stderr)
        return 1

    soup = BeautifulSoup(response.text, "html.parser")
    parsed: dict[str, int] = {}

    # Current contribution markup uses data-date/data-count/data-level on day cells.
    # Try the whole document so minor class-name changes do not break the parser.
    for element in soup.select("[data-date]"):
        raw_date = element.get("data-date", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            continue
        raw_count = element.get("data-count")
        if raw_count is None:
            # Some accessible cell markup exposes the count only in aria-label.
            aria = element.get("aria-label", "")
            match = re.search(r"([\d,]+) contributions?", aria, flags=re.I)
            if match:
                raw_count = match.group(1).replace(",", "")
        try:
            count = max(0, int(str(raw_count)))
        except (TypeError, ValueError):
            continue
        parsed[raw_date] = count

    if len(parsed) < 300:
        preview = " ".join(soup.get_text(" ", strip=True).split())[:260]
        print(
            "ERROR: Expected a year-like contribution calendar but found only "
            f"{len(parsed)} dated cells. GitHub's public HTML may have changed or "
            "the response may be a challenge/error page. No output file was overwritten.",
            file=sys.stderr,
        )
        if preview:
            print(f"Response preview: {preview}", file=sys.stderr)
        return 1

    all_days = sorted(parsed.items())
    max_count = max((count for _, count in all_days), default=0)
    days = [
        {"date": day, "count": count, "level": level_for(count, max_count)}
        for day, count in all_days
    ]
    payload = {
        "username": USERNAME,
        "source_url": URL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "live",
        "total_contributions": sum(item["count"] for item in all_days),
        "day_count": len(days),
        "days": days,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)
    print(
        f"Saved {len(days)} days from {days[0]['date']} to {days[-1]['date']} "
        f"({payload['total_contributions']:,} total contribution events) to {OUTPUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
