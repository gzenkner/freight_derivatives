#!/usr/bin/env python3

"""
Extract route metadata from a browser-exported HAR file for the Baltic Exchange interactive map.

Why HAR?
--------
The interactive map at https://www.balticexchange.com/en/data-services/routes.html is JS-driven.
Depending on how the site is built/served, the underlying route list may be delivered via one or more
JSON API calls that are easiest to capture from your browser session.

This script:
- Reads a HAR (JSON)
- Scans JSON responses
- Heuristically extracts route-like objects and route codes
- Writes a normalized CSV

It does not bypass authentication or scrape the site directly; you bring your own HAR export.

How to create a HAR (Chrome/Edge)
--------------------------------
1) Open DevTools -> Network tab
2) Enable "Preserve log"
3) Reload the page and click through a few families/routes
4) Right-click the request list -> "Save all as HAR with content"
5) Run this script.
"""

from __future__ import annotations

import base64
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROUTE_CODE_RE = re.compile(r"\b[A-Z]{1,5}\d{1,3}(?:_[0-9]{2,3})?\b")


def iter_json_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from iter_json_objects(v)
    elif isinstance(value, list):
        for item in value:
            yield from iter_json_objects(item)


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def maybe_decode_content(text: str, encoding: str | None) -> str:
    if encoding == "base64":
        return base64.b64decode(text).decode("utf-8", errors="replace")
    return text


def best_str(obj: dict[str, Any], keys: list[str]) -> str:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


@dataclass(frozen=True)
class RouteRow:
    route_code: str
    title: str
    description: str
    family: str
    category: str
    type: str
    source_url: str


def extract_route_rows(payload: Any, source_url: str) -> list[RouteRow]:
    rows: list[RouteRow] = []

    # 1) Look for objects that already resemble a route record (common key patterns).
    for obj in iter_json_objects(payload):
        code = best_str(obj, ["routeCode", "route_code", "shortCode", "short_code", "code", "id"])
        if code and ROUTE_CODE_RE.fullmatch(code):
            rows.append(
                RouteRow(
                    route_code=code,
                    title=best_str(obj, ["title", "name", "shortDescription", "short_description", "label"]),
                    description=best_str(obj, ["description", "longDescription", "long_description", "content", "details"]),
                    family=best_str(obj, ["family", "Family"]),
                    category=best_str(obj, ["category", "Category"]),
                    type=best_str(obj, ["type", "Type", "market", "Market"]),
                    source_url=source_url,
                )
            )

    if rows:
        return rows

    # 2) Fallback: if it doesn't have explicit objects, mine all strings for route codes and emit minimal rows.
    seen: set[str] = set()
    for s in iter_strings(payload):
        for m in ROUTE_CODE_RE.finditer(s):
            code = m.group(0)
            if code in seen:
                continue
            seen.add(code)
            rows.append(
                RouteRow(
                    route_code=code,
                    title="",
                    description="",
                    family="",
                    category="",
                    type="",
                    source_url=source_url,
                )
            )

    return rows


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--har", required=True, help="Path to HAR file (Save all as HAR with content)")
    parser.add_argument("--out", required=True, help="Output CSV path")
    args = parser.parse_args()

    har_path = Path(args.har)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    har = json.loads(har_path.read_text(encoding="utf-8"))
    entries = har.get("log", {}).get("entries", [])

    all_rows: list[RouteRow] = []
    for e in entries:
        req_url = (e.get("request") or {}).get("url") or ""
        resp = e.get("response") or {}
        content = (resp.get("content") or {})
        mime = (content.get("mimeType") or "").lower()
        text = content.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        if "json" not in mime and not text.lstrip().startswith(("{", "[")):
            continue

        decoded = maybe_decode_content(text, content.get("encoding"))
        try:
            payload = json.loads(decoded)
        except Exception:
            continue

        all_rows.extend(extract_route_rows(payload, req_url))

    # Deduplicate by route_code, preferring rows with more metadata.
    best: dict[str, RouteRow] = {}
    for r in all_rows:
        prev = best.get(r.route_code)
        if prev is None:
            best[r.route_code] = r
            continue
        score_prev = sum(bool(x) for x in [prev.title, prev.description, prev.family, prev.category, prev.type])
        score_new = sum(bool(x) for x in [r.title, r.description, r.family, r.category, r.type])
        if score_new > score_prev:
            best[r.route_code] = r

    rows_sorted = sorted(best.values(), key=lambda r: r.route_code)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["route_code", "title", "description", "family", "category", "type", "source_url"],
        )
        w.writeheader()
        for r in rows_sorted:
            w.writerow(
                {
                    "route_code": r.route_code,
                    "title": r.title,
                    "description": r.description,
                    "family": r.family,
                    "category": r.category,
                    "type": r.type,
                    "source_url": r.source_url,
                }
            )

    print(f"Extracted {len(rows_sorted)} routes -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

