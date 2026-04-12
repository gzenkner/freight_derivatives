#!/usr/bin/env python3

"""
Update Baltic Exchange route reference tables from a browser-exported HAR capture.

The Baltic Exchange interactive route map is JS-driven:
  https://www.balticexchange.com/en/data-services/routes.html

In many cases, the easiest reliable way to extract the complete route list is:
1) capture network traffic in your browser (HAR export with content)
2) parse the JSON responses

This script:
- extracts routes from a HAR (via `extract_routes_from_har.py`)
- writes `routes_interactive_map.csv`
- writes a merged union file `routes_merged.csv` that prefers richer metadata

It does not attempt to bypass access controls; you provide the HAR from your own session.
"""

from __future__ import annotations

import csv
from pathlib import Path

from extract_routes_from_har import extract_route_rows, maybe_decode_content  # type: ignore


def _read_existing_routes(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        out: dict[str, dict] = {}
        for row in r:
            code = (row.get("route_code") or "").strip()
            if not code:
                continue
            out[code] = dict(row)
        return out


def _write_routes(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["route_code", "short_description", "market", "segment", "source"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def _score(row: dict) -> int:
    return sum(bool((row.get(k) or "").strip()) for k in ["short_description", "market", "segment"])


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--har", required=True, help="Path to HAR file (Save all as HAR with content)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]  # .../freight_derivatives/real/scripts -> repo/freight_derivatives
    ref_dir = repo_root / "datasets" / "exchange_reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    base_routes_path = ref_dir / "routes.csv"
    map_routes_path = ref_dir / "routes_interactive_map.csv"
    merged_routes_path = ref_dir / "routes_merged.csv"

    har_path = Path(args.har)
    har = json.loads(har_path.read_text(encoding="utf-8"))
    entries = har.get("log", {}).get("entries", [])

    extracted: dict[str, dict] = {}

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

        for r in extract_route_rows(payload, req_url):
            # Normalize into the same shape as datasets/exchange_reference/routes.csv
            short_description = (r.title or r.description or "").strip()
            normalized = {
                "route_code": r.route_code,
                "short_description": short_description,
                "market": (r.type or r.category or "").strip(),
                "segment": (r.family or "").strip(),
                "source": "interactive_map_har",
            }
            prev = extracted.get(r.route_code)
            if prev is None or _score(normalized) > _score(prev):
                extracted[r.route_code] = normalized

    extracted_rows = sorted(extracted.values(), key=lambda x: x["route_code"])
    _write_routes(map_routes_path, extracted_rows)

    base = _read_existing_routes(base_routes_path)
    merged: dict[str, dict] = dict(base)
    for code, row in extracted.items():
        prev = merged.get(code)
        if prev is None:
            merged[code] = row
            continue
        # Prefer the row with more filled fields; keep the base market/segment if they look more structured.
        if _score(row) > _score(prev):
            merged[code] = {**prev, **row}

    merged_rows = sorted(merged.values(), key=lambda x: (x.get("route_code") or ""))
    _write_routes(merged_routes_path, merged_rows)

    print(f"Wrote: {map_routes_path}")
    print(f"Wrote: {merged_routes_path}")
    print(f"Base : {base_routes_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
