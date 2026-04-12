#!/usr/bin/env python3

"""
Download all "Shipping indexes" time series from SeeCapitalMarkets and write per-index Excel files.

Important implementation detail:
------------------------------
SeeCapitalMarkets' UI exports to Excel *in the browser* (ExcelJS). There is no stable direct
server-hosted .xlsx link per index. Instead, the site loads JSON via endpoints like:
  - /IndexValues/GetIndexValues
  - /SingleIndexValues/GetHistoryDataAscending

This script:
1) Calls /IndexValues/GetIndexValues to list all shipping indexes for a given date
2) For each index row, opens /en/index-detailed?IndexValueId=... to discover the internal indexId
3) Downloads the historical series as JSON
4) Backfills missing label/ISIN in history rows from the table listing
5) Writes a simple .xlsx file locally (standard library only)
6) Writes a catalog CSV describing what was found/downloaded
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


BASE = "https://seecapitalmarkets.com"
LIST_URL = f"{BASE}/en/shipping-indexes"
DETAIL_URL_TMPL = f"{BASE}/en/index-detailed?IndexValueId={{id}}"
LIST_API_URL_TMPL = f"{BASE}/IndexValues/GetIndexValues?date={{date}}&indexTypeId=1"
HISTORY_API_URL_TMPL = f"{BASE}/SingleIndexValues/GetHistoryDataAscending?indexId={{index_id}}&years={{years}}"


INDEX_ID_RE = re.compile(r"IndexValueId=(\d+)")
DETAIL_INDEXID_RE = re.compile(r'"indexId"\s*:\s*(\d+)', re.IGNORECASE)


def _fetch(url: str, *, timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; baltic-datasets/1.0; +https://example.invalid)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - user-requested public URL
        return resp.read()


def _extract_index_ids(list_html: str) -> list[str]:
    ids = sorted(set(INDEX_ID_RE.findall(list_html)), key=int)
    return ids


def _make_abs(url: str, base: str) -> str:
    return urllib.parse.urljoin(base, url)


def _discover_internal_index_id(detail_html: str) -> str:
    # Many blocks repeat "indexId": <num>. Take the first.
    m = DETAIL_INDEXID_RE.search(detail_html)
    return m.group(1) if m else ""


def _safe_filename(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "file"


def _download_json(url: str, *, timeout: int = 60) -> dict:
    raw = _fetch(url, timeout=timeout)
    return json.loads(raw.decode("utf-8", errors="replace"))


def _excel_col(n: int) -> str:
    # 1 -> A, 26 -> Z, 27 -> AA
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _xlsx_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _build_simple_xlsx(rows: list[list[str]], out_path: Path, sheet_name: str = "History") -> None:
    """
    Minimal .xlsx writer (1 sheet) using only the standard library.
    Cells are written as strings; Excel will still parse numeric-looking values.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build sharedStrings table
    shared: list[str] = []
    shared_index: dict[str, int] = {}

    def sst_idx(val: str) -> int:
        if val not in shared_index:
            shared_index[val] = len(shared)
            shared.append(val)
        return shared_index[val]

    # Sheet XML rows
    sheet_rows_xml: list[str] = []
    for r_i, row in enumerate(rows, start=1):
        cells_xml: list[str] = []
        for c_i, val in enumerate(row, start=1):
            cell_ref = f"{_excel_col(c_i)}{r_i}"
            idx = sst_idx(val)
            cells_xml.append(f'<c r="{cell_ref}" t="s"><v>{idx}</v></c>')
        sheet_rows_xml.append(f'<row r="{r_i}">{"".join(cells_xml)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(sheet_rows_xml)
        + "</sheetData>"
        "</worksheet>"
    )

    sst_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{_xlsx_escape(v)}</t></si>" for v in shared)
        + "</sst>"
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        f'<sheet name="{_xlsx_escape(sheet_name)}" sheetId="1" r:id="rId1"/>'
        "</sheets>"
        "</workbook>"
    )

    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    wb_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>'
        "</Relationships>"
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )

    with ZipFile(out_path, "w", compression=ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", rels_xml)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        z.writestr("xl/sharedStrings.xml", sst_xml)


@dataclass
class CatalogRow:
    index_value_id: str
    index_id: str
    index_short_name: str
    index_name: str
    isin: str
    detail_url: str
    history_url: str
    local_file: str
    rows: int
    status: str
    error: str


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="datasets/indices", help="Output base directory")
    parser.add_argument("--sleep", type=float, default=0.4, help="Seconds to sleep between requests")
    parser.add_argument("--limit", type=int, default=0, help="Max number of indices (0 = all)")
    parser.add_argument("--date", default="", help="Date for the index list (YYYY-MM-DD). Default: today.")
    parser.add_argument("--years", type=int, default=50, help="Years of history to request per index.")
    parser.add_argument(
        "--only-baltic",
        action="store_true",
        help="Only download indexes whose short code exists in datasets/exchange_reference/indices.csv",
    )
    parser.add_argument(
        "--baltic-index-csv",
        default="datasets/exchange_reference/indices.csv",
        help="Path to indices reference CSV for --only-baltic filter",
    )
    parser.add_argument("--dry-run", action="store_true", help="Discover only; do not download files")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser()
    excel_dir = out_dir / "excels"
    json_dir = out_dir / "json"
    catalog_path = out_dir / "index_catalog.csv"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[CatalogRow] = []

    # Determine date in YYYY-MM-DD (matches the site JS myDate()).
    if args.date:
        date_str = args.date.strip()
    else:
        import datetime as _dt

        date_str = _dt.date.today().strftime("%Y-%m-%d")

    list_api_url = LIST_API_URL_TMPL.format(date=date_str)
    listing = _download_json(list_api_url)
    items = listing.get("data") if isinstance(listing, dict) else None
    if not isinstance(items, list):
        items = []

    baltic_codes: set[str] = set()
    if args.only_baltic:
        p = Path(args.baltic_index_csv).expanduser()
        try:
            with p.open("r", encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    code = (row.get("index_code") or "").strip()
                    if code:
                        baltic_codes.add(code)
        except FileNotFoundError:
            raise SystemExit(f"--only-baltic set but file not found: {p}")

        # Filter items to those matching the Baltic index code list.
        filtered = []
        for it in items:
            short = str(it.get("IndexShortName", "")).strip()
            name = str(it.get("IndexName", "")).strip()
            if short in baltic_codes or name.startswith("Baltic "):
                filtered.append(it)
        items = filtered

    if args.limit and args.limit > 0:
        items = items[: args.limit]

    for idx, item in enumerate(items, start=1):
        index_value_id = str(item.get("Id", "")).strip()
        index_name = str(item.get("IndexName", "")).strip()
        index_short_name = str(item.get("IndexShortName", "")).strip()
        isin = str(item.get("ISIN", "")).strip()

        if not index_value_id:
            continue

        detail_url = DETAIL_URL_TMPL.format(id=index_value_id)
        try:
            detail_html = _fetch(detail_url).decode("utf-8", errors="replace")
            index_id = _discover_internal_index_id(detail_html)
            if not index_id:
                rows.append(
                    CatalogRow(
                        index_value_id=index_value_id,
                        index_id="",
                        index_short_name=index_short_name,
                        index_name=index_name,
                        isin=isin,
                        detail_url=detail_url,
                        history_url="",
                        local_file="",
                        rows=0,
                        status="no_index_id_found",
                        error="",
                    )
                )
                time.sleep(args.sleep)
                continue

            if args.dry_run:
                rows.append(
                    CatalogRow(
                        index_value_id=index_value_id,
                        index_id=index_id,
                        index_short_name=index_short_name,
                        index_name=index_name,
                        isin=isin,
                        detail_url=detail_url,
                        history_url=HISTORY_API_URL_TMPL.format(index_id=index_id, years=args.years),
                        local_file="",
                        rows=0,
                        status="dry_run",
                        error="",
                    )
                )
            else:
                history_url = HISTORY_API_URL_TMPL.format(index_id=index_id, years=args.years)
                history = _download_json(history_url)
                data = history.get("data") if isinstance(history, dict) else None
                if not isinstance(data, list):
                    data = []
                else:
                    # The history endpoint frequently returns empty IndexShortName / ISIN fields
                    # for shipping indexes. Fill them from the "Shipping indexes" table listing.
                    for r in data:
                        if not isinstance(r, dict):
                            continue
                        if not str(r.get("IndexShortName", "")).strip():
                            r["IndexShortName"] = index_short_name
                        if not str(r.get("ISIN", "")).strip():
                            r["ISIN"] = isin
                        if not str(r.get("IndexName", "")).strip():
                            r["IndexName"] = index_name

                # Save raw JSON for traceability
                json_path = json_dir / f"{_safe_filename(index_short_name or index_name)}_{index_id}.json"
                json_path.parent.mkdir(parents=True, exist_ok=True)
                json_path.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")

                # Build tabular rows for Excel
                header = ["Date", "Open", "High", "Low", "Close", "Change", "Turnover"]
                table_rows: list[list[str]] = [header]
                for r in data:
                    table_rows.append(
                        [
                            str(r.get("Date", ""))[:10],
                            str(r.get("Open", "")),
                            str(r.get("High", "")),
                            str(r.get("Low", "")),
                            str(r.get("Close", "")),
                            str(r.get("Change", "")),
                            str(r.get("Turnover", "")),
                        ]
                    )

                fname_base = _safe_filename(index_short_name or index_name or f"Index_{index_id}")
                xlsx_path = excel_dir / f"{fname_base}_{index_id}.xlsx"
                _build_simple_xlsx(table_rows, xlsx_path, sheet_name=(index_short_name or "History")[:31])

                rows.append(
                    CatalogRow(
                        index_value_id=index_value_id,
                        index_id=index_id,
                        index_short_name=index_short_name,
                        index_name=index_name,
                        isin=isin,
                        detail_url=detail_url,
                        history_url=history_url,
                        local_file=str(xlsx_path.relative_to(out_dir)),
                        rows=max(0, len(table_rows) - 1),
                        status="downloaded",
                        error="",
                    )
                )
        except Exception as e:
            rows.append(
                CatalogRow(
                    index_value_id=index_value_id,
                    index_id="",
                    index_short_name=index_short_name,
                    index_name=index_name,
                    isin=isin,
                    detail_url=detail_url,
                    history_url="",
                    local_file="",
                    rows=0,
                    status="error",
                    error=str(e),
                )
            )
        time.sleep(args.sleep)

    with catalog_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "index_value_id",
                "index_id",
                "index_short_name",
                "index_name",
                "isin",
                "detail_url",
                "history_url",
                "local_file",
                "rows",
                "status",
                "error",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "index_value_id": r.index_value_id,
                    "index_id": r.index_id,
                    "index_short_name": r.index_short_name,
                    "index_name": r.index_name,
                    "isin": r.isin,
                    "detail_url": r.detail_url,
                    "history_url": r.history_url,
                    "local_file": r.local_file,
                    "rows": r.rows,
                    "status": r.status,
                    "error": r.error,
                }
            )

    print(f"Wrote catalog: {catalog_path}")
    print(f"List API: {list_api_url}")
    print(f"Total indexes discovered: {len(items)}")
    print(f"Rows written: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
