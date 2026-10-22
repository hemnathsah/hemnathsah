#!/usr/bin/env python3
"""Fetch hemnathsah's public GitHub contribution calendar without a PAT.

Supports both the traditional [data-date][data-level] day-cell markup and a
fallback where day dates/counts are exposed through linked <tool-tip> text or
accessible labels. The script refuses to overwrite live data unless it parses
at least 300 unique dated days with explicit counts (or an explicit zero level).
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
ISO_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
COUNT_RE = re.compile(r"\b([\d,]+)\s+contributions?\b", re.IGNORECASE)
NO_COUNT_RE = re.compile(r"\bno\s+contributions?\b", re.IGNORECASE)
WEEKDAY = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
MONTH_DATE_RE = re.compile(
    rf"\b(?:{WEEKDAY}\s*,?\s*)?({MONTH})\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(\d{{4}})\b",
    re.IGNORECASE,
)
DAY_MONTH_DATE_RE = re.compile(
    rf"\b(?:{WEEKDAY}\s*,?\s*)?(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH})[,]?\s+(\d{{4}})\b",
    re.IGNORECASE,
)


def _iso_date(raw: object) -> str | None:
    value = str(raw or "").strip()
    if not ISO_RE.fullmatch(value):
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


def _date_from_text(text: str) -> str | None:
    """Extract a full date from an accessible label or tooltip."""
    clean = " ".join(text.split())
    iso_match = ISO_RE.search(clean)
    if iso_match:
        candidate = _iso_date(iso_match.group(1))
        if candidate:
            return candidate

    for regex, order in ((MONTH_DATE_RE, "month-first"), (DAY_MONTH_DATE_RE, "day-first")):
        match = regex.search(clean)
        if not match:
            continue
        try:
            if order == "month-first":
                month, day, year = match.groups()
                formats = ("%B %d %Y", "%b %d %Y")
                raw = f"{month} {int(day)} {year}"
            else:
                day, month, year = match.groups()
                formats = ("%d %B %Y", "%d %b %Y")
                raw = f"{int(day)} {month} {year}"
            for fmt in formats:
                try:
                    return datetime.strptime(raw, fmt).date().isoformat()
                except ValueError:
                    continue
        except (ValueError, TypeError):
            continue
    return None


def _count_from_text(text: str) -> int | None:
    clean = " ".join(text.split())
    if NO_COUNT_RE.search(clean):
        return 0
    match = COUNT_RE.search(clean)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def _attr_count(node: Tag) -> int | None:
    raw = node.get("data-count")
    if raw is not None:
        try:
            return max(0, int(str(raw).replace(",", "").strip()))
        except ValueError:
            parsed = _count_from_text(str(raw))
            if parsed is not None:
                return parsed
    for attr in ("aria-label", "title", "data-tooltip-content"):
        value = node.get(attr)
        if value:
            parsed = _count_from_text(str(value))
            if parsed is not None:
                return parsed
    return None


def _level(node: Tag | None) -> int | None:
    if not isinstance(node, Tag):
        return None
    raw = node.get("data-level")
    try:
        value = int(str(raw))
        if 0 <= value <= 4:
            return value
    except (TypeError, ValueError):
        pass
    return None


def level_for(count: int, max_count: int) -> int:
    """Approximate level only when the page supplies no intensity attribute."""
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


def _all_text(node: Tag) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def parse_calendar(html_text: str) -> dict[str, dict[str, int]]:
    """Parse to {ISO date: {count, level?}} across common GitHub markup shapes."""
    soup = BeautifulSoup(html_text, "html.parser")
    parsed: dict[str, dict[str, int]] = {}
    unknown_counts: list[str] = []

    # Keep tooltips indexed both by their target ID and in document order.
    tooltips: list[Tag] = [node for node in soup.find_all("tool-tip") if isinstance(node, Tag)]
    tooltip_by_target: dict[str, Tag] = {}
    for tip in tooltips:
        target_id = tip.get("for") or tip.get("data-for")
        if target_id:
            tooltip_by_target[str(target_id)] = tip

    def add(day: str | None, count: int | None, source_level: int | None = None) -> None:
        if not day or count is None:
            return
        record: dict[str, int] = {"count": max(0, count)}
        if source_level is not None:
            record["level"] = source_level
        current = parsed.get(day)
        # Prefer a record with an actual intensity attribute if duplicate sources exist.
        if current is None or ("level" not in current and "level" in record):
            parsed[day] = record
        elif current["count"] != record["count"]:
            # The tooltip is the most direct human-readable count; use it over a
            # fallback attribute, but do not silently hide inconsistencies in debug.
            parsed[day] = record

    # Pass 1: conventional data-date day elements.
    for node in soup.select("[data-date]"):
        if not isinstance(node, Tag):
            continue
        day = _iso_date(node.get("data-date"))
        if not day:
            continue
        count = _attr_count(node)
        target_id = str(node.get("id", ""))
        tip = tooltip_by_target.get(target_id) if target_id else None
        if count is None and isinstance(tip, Tag):
            count = _count_from_text(_all_text(tip))
        level = _level(node)
        if count is None and level == 0:
            count = 0
        if count is None:
            unknown_counts.append(day)
            continue
        add(day, count, level)

    # Pass 2: modern/alternate markup where the day date lives only in a tooltip.
    # The associated cell can still contain its intensity in data-level.
    for tip in tooltips:
        tip_text = _all_text(tip)
        day = _date_from_text(tip_text) or _iso_date(tip.get("data-date"))
        count = _count_from_text(tip_text)
        target_id = tip.get("for") or tip.get("data-for")
        target = soup.find(id=str(target_id)) if target_id else None
        if day and count is not None:
            target_level = _level(target if isinstance(target, Tag) else None)
            add(day, count, target_level if target_level is not None else _level(tip))

    # Pass 3: accessible labels/title-based day cells, including markup with no data-date.
    for node in soup.select("[aria-label], [title], [data-tooltip-content]"):
        if not isinstance(node, Tag):
            continue
        texts = " ".join(
            str(node.get(attr, ""))
            for attr in ("aria-label", "title", "data-tooltip-content")
            if node.get(attr)
        )
        day = _iso_date(node.get("data-date")) or _date_from_text(texts)
        if not day:
            continue
        count = _attr_count(node)
        node_id = str(node.get("id", ""))
        tip = tooltip_by_target.get(node_id) if node_id else None
        if count is None and isinstance(tip, Tag):
            count = _count_from_text(_all_text(tip))
        level = _level(node)
        if count is None and level == 0:
            count = 0
        if count is not None:
            add(day, count, level)
        else:
            unknown_counts.append(day)

    return parsed


def _diagnostics(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    stats = {
        "data-date elements": len(soup.select("[data-date]")),
        "data-level elements": len(soup.select("[data-level]")),
        "tool-tip elements": len(soup.find_all("tool-tip")),
        "aria-label elements": len(soup.select("[aria-label]")),
        "elements with title": len(soup.select("[title]")),
    }
    tooltip_samples = []
    for tip in soup.find_all("tool-tip")[:3]:
        if isinstance(tip, Tag):
            text = _all_text(tip)
            if text:
                tooltip_samples.append(text[:120])
    return f"Markup counts: {stats}. Tooltip examples: {tooltip_samples or 'none'}"


def main() -> int:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; hemnathsah-profile-art/2.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERROR: Could not fetch {URL}: {exc}", file=sys.stderr)
        return 1

    parsed = parse_calendar(response.text)
    if len(parsed) < 300:
        preview = " ".join(BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True).split())[:260]
        print(
            "ERROR: Parsed only " + str(len(parsed)) + " dated contribution days; at least 300 are required. "
            "No output file was overwritten. This response's contribution markup was not understood.",
            file=sys.stderr,
        )
        print(_diagnostics(response.text), file=sys.stderr)
        if preview:
            print(f"Response preview: {preview}", file=sys.stderr)
        return 1

    all_days = sorted(parsed.items())
    max_count = max((entry["count"] for _, entry in all_days), default=0)
    days: list[dict[str, int | str]] = []
    for day, entry in all_days:
        count = entry["count"]
        level = entry.get("level")
        if level is None:
            level = level_for(count, max_count)
        days.append({"date": day, "count": count, "level": max(0, min(4, level))})

    payload: dict[str, Any] = {
        "username": USERNAME,
        "source_url": URL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "live",
        "total_contributions": sum(int(item["count"]) for item in days),
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
