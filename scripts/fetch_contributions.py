#!/usr/bin/env python3
"""Fetch the public GitHub contribution calendar without a personal access token.

GitHub currently exposes day dates/levels on calendar cells and commonly exposes
exact counts in a linked <tool-tip for="cell-id"> element. This parser supports
that markup as well as older data-count/aria-label variants.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "hemnathsah"
URL = f"https://github.com/users/{USERNAME}/contributions"
OUTPUT = ROOT / "data" / "contributions.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COUNT_RE = re.compile(r"([\d,]+)\s+contributions?\b", re.IGNORECASE)


def level_for(count: int, max_count: int) -> int:
    """Fallback intensity mapping used only when GitHub omits data-level."""
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


def _count_from_text(text: str) -> int | None:
    clean = " ".join(text.split())
    if re.search(r"\bno contributions\b", clean, flags=re.IGNORECASE):
        return 0
    match = COUNT_RE.search(clean)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def _count_for_cell(cell: Tag, soup: BeautifulSoup) -> int | None:
    """Return a precise day count from attributes, accessible text, or tooltip."""
    raw_count = cell.get("data-count")
    if raw_count is not None:
        try:
            return max(0, int(str(raw_count).replace(",", "").strip()))
        except ValueError:
            parsed = _count_from_text(str(raw_count))
            if parsed is not None:
                return parsed

    parsed = _count_from_text(str(cell.get("aria-label", "")))
    if parsed is not None:
        return parsed

    cell_id = cell.get("id")
    if cell_id:
        tooltip = soup.find(lambda node: isinstance(node, Tag)
                            and node.name and node.name.lower() == "tool-tip"
                            and node.get("for") == cell_id)
        if isinstance(tooltip, Tag):
            parsed = _count_from_text(tooltip.get_text(" ", strip=True))
            if parsed is not None:
                return parsed

    # A zero-intensity cell is safely a zero-count day even if tooltip text is absent.
    if str(cell.get("data-level", "")) == "0":
        return 0
    return None


def parse_calendar(html_text: str) -> dict[str, dict[str, int]]:
    """Parse the contribution calendar into {ISO date: {count, level}}."""
    soup = BeautifulSoup(html_text, "html.parser")
    parsed: dict[str, dict[str, int]] = {}
    missing_positive_count: list[str] = []

    # GitHub's current public calendar uses <td data-date="..." data-level="...">.
    # Keep a broad fallback for markup variants that move these attrs to another cell.
    cells = soup.select("td[data-date]") or soup.select("[data-date]")
    for cell in cells:
        if not isinstance(cell, Tag):
            continue
        raw_date = str(cell.get("data-date", ""))
        if not DATE_RE.fullmatch(raw_date):
            continue

        raw_level = cell.get("data-level")
        source_level: int | None = None
        try:
            candidate_level = int(str(raw_level))
            if 0 <= candidate_level <= 4:
                source_level = candidate_level
        except (TypeError, ValueError):
            pass

        count = _count_for_cell(cell, soup)
        if count is None:
            if source_level == 0:
                count = 0
            else:
                missing_positive_count.append(raw_date)
                continue

        entry: dict[str, int] = {"count": max(0, count)}
        if source_level is not None:
            entry["level"] = source_level
        parsed[raw_date] = entry

    if missing_positive_count:
        examples = ", ".join(missing_positive_count[:5])
        raise ValueError(
            "Found contribution cells but could not read their exact counts "
            f"from data attributes, aria-labels, or linked tooltips (examples: {examples})."
        )

    return parsed


def main() -> int:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; hemnathsah-profile-art/1.1)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERROR: Could not fetch {URL}: {exc}", file=sys.stderr)
        return 1

    try:
        parsed = parse_calendar(response.text)
    except ValueError as exc:
        print(f"ERROR: Could not parse GitHub's contribution calendar: {exc}", file=sys.stderr)
        preview = " ".join(BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True).split())[:300]
        if preview:
            print(f"Response preview: {preview}", file=sys.stderr)
        return 1

    # A normal rolling-year page contains roughly 365 dated cells. Fail safely if
    # GitHub returned a login/challenge page or materially changed its markup.
    if len(parsed) < 300:
        soup = BeautifulSoup(response.text, "html.parser")
        preview = " ".join(soup.get_text(" ", strip=True).split())[:300]
        print(
            "ERROR: Expected at least 300 dated contribution cells but found "
            f"{len(parsed)}. GitHub may have returned a challenge/error page or changed its markup.",
            file=sys.stderr,
        )
        if preview:
            print(f"Response preview: {preview}", file=sys.stderr)
        return 1

    all_days = sorted(parsed.items())
    max_count = max((entry["count"] for _, entry in all_days), default=0)
    days = []
    for day, entry in all_days:
        count = entry["count"]
        level = entry.get("level", level_for(count, max_count))
        days.append({"date": day, "count": count, "level": max(0, min(4, level))})

    payload: dict[str, Any] = {
        "username": USERNAME,
        "source_url": URL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "live",
        "total_contributions": sum(item["count"] for item in days),
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
