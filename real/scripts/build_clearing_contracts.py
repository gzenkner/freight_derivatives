#!/usr/bin/env python3

"""
Build a contracts-to-clearing-house mapping from the Baltic Exchange clearing page.

Source page:
  https://www.balticexchange.com/en/data-services/freight-derivatives-/Clearing.html

The page has sections like:
  ## CME Group / ## EEX Group / ## ICE / ## SGX
and each includes a "### Contracts" list.

This script extracts those contract lines into a normalized CSV:
  - clearing_house
  - contract_name
  - contract_code (best-effort)
  - contract_type (FUTURE|OPTION)
  - source_url

It can either fetch the URL (default) or parse a saved HTML file.
"""

from __future__ import annotations

import csv
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


SOURCE_URL = "https://www.balticexchange.com/en/data-services/freight-derivatives-/Clearing.html"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._chunks)


CODE_RE = re.compile(r"\b([A-Za-z]{1,6}\d{1,3}[A-Za-z]?(?:_[0-9]{2,3})?)\b")


def _infer_contract_type(name: str) -> str:
    return "OPTION" if "option" in name.lower() else "FUTURE"


def _extract_code(name: str) -> str:
    # Prefer codes at the very beginning (e.g., "FBX01 (Baltic) Futures", "TC2 ...", "TD3C ...")
    m = re.match(r"^\s*([A-Za-z]{1,6}\d{1,3}[A-Za-z]?(?:_[0-9]{2,3})?)\b", name)
    if m:
        return m.group(1)
    # Otherwise, look for common Baltic route/index style codes embedded in the name (e.g., "C5", "P2E", "5TC")
    # Keep it best-effort and lightweight.
    m2 = CODE_RE.search(name)
    return m2.group(1) if m2 else ""


def _extract_sections(lines: list[str]) -> dict[str, list[str]]:
    houses = ["CME Group", "EEX Group", "ICE", "SGX"]
    sections: dict[str, list[str]] = {}

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in houses:
            house = "CME" if line == "CME Group" else ("EEX" if line == "EEX Group" else line)
            # Find the "Contracts" marker after this heading.
            j = i + 1
            while j < len(lines) and lines[j].strip() != "Contracts":
                j += 1
            if j >= len(lines):
                i += 1
                continue
            j += 1
            items: list[str] = []
            while j < len(lines):
                t = lines[j].strip()
                if not t:
                    j += 1
                    continue
                if t in houses:
                    break
                if t in {"General Clearing Members (All)", "General Clearing Members (Freight)"}:
                    break
                if t == "Contracts":
                    j += 1
                    continue
                # Contract lines are short-ish; ignore obvious non-contract boilerplate.
                if t.startswith("www.") or t.startswith("http"):
                    j += 1
                    continue
                items.append(t)
                j += 1

            sections[house] = items
            i = j
            continue
        i += 1

    return sections


def _load_html(html_path: Path | None) -> str:
    if html_path is not None:
        return html_path.read_text(encoding="utf-8")
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as resp:  # nosec - public URL fetch
        return resp.read().decode("utf-8", errors="replace")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--html", default="", help="Optional path to saved HTML (skip fetching)")
    args = parser.parse_args()

    html_path = Path(args.html) if args.html else None
    html = _load_html(html_path)

    parser_text = _TextExtractor()
    parser_text.feed(html)
    text = parser_text.text()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    sections = _extract_sections(lines)
    rows: list[dict[str, str]] = []
    for house, items in sections.items():
        for name in items:
            rows.append(
                {
                    "clearing_house": house,
                    "contract_name": name,
                    "contract_code": _extract_code(name),
                    "contract_type": _infer_contract_type(name),
                    "source_url": SOURCE_URL,
                }
            )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["clearing_house", "contract_code", "contract_name", "contract_type", "source_url"],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

