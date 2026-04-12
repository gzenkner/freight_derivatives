from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import urllib.parse


PROJECT_DIR = Path(__file__).resolve().parents[2]

CLEARING_URL = "https://www.balticexchange.com/en/data-services/freight-derivatives-/Clearing.html"
ROUTES_URL = "https://www.balticexchange.com/en/data-services/routes.html"
INDICES_URL = "https://www.balticexchange.com/en/data-services/market-information0/indices.html"
EEX_DRY_URL = "https://www.eex.com/en/global-commodities/dry-freight"


@dataclass(frozen=True)
class IndexMeta:
    index_id: str
    index_name: str
    isin: str
    data_start_date: str
    data_end_date: str
    data_rows: str
    source_file: str


def _load_index_meta(indices_json_dir: Path) -> dict[str, IndexMeta]:
    meta: dict[str, IndexMeta] = {}
    if not indices_json_dir.exists():
        return meta

    for path in sorted(indices_json_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload.get("data", [])
        if not rows:
            continue

        code = str(rows[0].get("IndexShortName", "")).strip()
        if not code:
            continue

        dates: list[date] = []
        for r in rows:
            d = str(r.get("Date", "")).strip()
            if not d:
                continue
            try:
                yyyy, mm, dd = d.split("-")
                dates.append(date(int(yyyy), int(mm), int(dd)))
            except Exception:
                continue

        start = min(dates).isoformat() if dates else ""
        end = max(dates).isoformat() if dates else ""

        meta[code] = IndexMeta(
            index_id=str(rows[0].get("IndexId", "")).strip(),
            index_name=str(rows[0].get("IndexName", "")).strip(),
            isin=str(rows[0].get("ISIN", "")).strip(),
            data_start_date=start,
            data_end_date=end,
            data_rows=str(len(rows)),
            source_file=path.name,
        )

    return meta


def _load_routes(routes_csv: Path) -> dict[str, dict[str, str]]:
    routes: dict[str, dict[str, str]] = {}
    if not routes_csv.exists():
        return routes
    with routes_csv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            code = (row.get("route_code") or "").strip()
            if not code:
                continue
            routes[code] = {
                "market": (row.get("market") or "").strip(),
                "segment": (row.get("segment") or "").strip(),
                "short_description": (row.get("short_description") or "").strip(),
            }
    return routes


def _venue_name(venue: str) -> str:
    v = venue.strip().upper()
    if v == "EEX":
        return "European Energy Exchange (EEX)"
    if v == "ICE":
        return "ICE Futures Europe (ICE)"
    if v == "SGX":
        return "Singapore Exchange (SGX)"
    if v == "CME":
        return "CME Group (CME)"
    return venue.strip()


def _infer_basket_market_segment(underlying_code: str) -> tuple[str, str]:
    code = underlying_code.strip()
    if code.startswith("C5TC"):
        return "DRY_BULK", "CAPESIZE"
    if code == "P5TC":
        return "DRY_BULK", "PANAMAX"
    if code in {"S10TC", "S11TC"}:
        return "DRY_BULK", "SUPRAMAX"
    if code == "H7TC":
        return "DRY_BULK", "HANDYSIZE"
    if code.startswith("FBX"):
        return "CONTAINERS", "FBX"
    if code.startswith("BAI"):
        return "AIR_FREIGHT", "BAI"
    return "", ""


def _variant_from_contract_name(name: str, contract_type: str) -> str:
    n = (name or "").strip().upper()
    if "AVERAGE PRICE" in n and contract_type.strip().upper() == "OPTION":
        return "AVG_PRICE_OPTION"
    if "BALMO" in n:
        return "BALMO"
    if "DAILY" in n:
        return "DAILY"
    if "MINI" in n:
        return "MINI"
    if contract_type.strip().upper() == "OPTION":
        return "OPTION"
    return "FUTURE"

def _search_url(query: str) -> str:
    q = urllib.parse.quote_plus(query.strip())
    return f"https://duckduckgo.com/?q={q}"


def _sgx_blank_contract_underlying(contract_name: str) -> str:
    n = (contract_name or "").upper()
    if "CAPESIZE" in n and "182" in n:
        return "C5TC (182)"
    if "CAPESIZE" in n and "180" in n:
        return "C5TC (180)"
    if "PANAMAX" in n and "TIME CHARTER" in n:
        return "P5TC"
    if "SUPRAMAX" in n and "10" in n:
        return "S10TC"
    if "HANDYSIZE" in n and "7" in n:
        return "H7TC"
    return ""


def build() -> None:
    indices_json_dir = PROJECT_DIR / "datasets/indices/json"
    routes_csv = PROJECT_DIR / "datasets/exchange_reference/routes.csv"
    clearing_csv = PROJECT_DIR / "datasets/ffas/clearing_contracts.csv"
    eex_products_csv = PROJECT_DIR / "datasets/ffas/eex_dry_freight_products.csv"
    ice_products_csv = PROJECT_DIR / "datasets/ffas/ice_freight_products.csv"
    out_csv = PROJECT_DIR / "datasets/ffas/ffa_instruments.csv"

    index_meta = _load_index_meta(indices_json_dir)
    routes = _load_routes(routes_csv)

    fieldnames = [
        "venue",
        "exchange_name",
        "instrument_code",
        "contract_code",
        "contract_name",
        "underlying_code",
        "underlying_kind",
        "market",
        "segment",
        "unit",
        "currency",
        "notes",
        "index_id",
        "index_name",
        "isin",
        "data_start_date",
        "data_end_date",
        "data_rows",
        "source_file",
        "product_type",
        "contract_variant",
        "source_url",
        "validation_contract_url",
        "validation_underlying_url",
        "validation_search_url",
    ]

    rows_out: list[dict[str, str]] = []

    # EEX: use official product codes/specs for dry freight.
    if eex_products_csv.exists():
        with eex_products_csv.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                venue = (row.get("venue") or "EEX").strip() or "EEX"
                instrument_code = (row.get("product_code") or "").strip()
                contract_code = instrument_code
                contract_name = (row.get("product_name") or "").strip()
                underlying_code = (row.get("underlying_code") or "").strip()
                instrument_type = (row.get("instrument_type") or "").strip()
                pricing_unit = (row.get("pricing_unit") or "").strip()
                notes = (row.get("notes") or "").strip()

                if not instrument_code or not underlying_code:
                    continue

                if underlying_code in routes:
                    underlying_kind = "route"
                    market = routes[underlying_code]["market"]
                    segment = routes[underlying_code]["segment"]
                else:
                    underlying_kind = "basket"
                    market, segment = _infer_basket_market_segment(underlying_code)

                unit = pricing_unit
                currency = "USD" if "USD" in (pricing_unit or "").upper() or venue == "EEX" else ""

                rows_out.append(
                    {
                        "venue": "EEX",
                        "exchange_name": _venue_name("EEX"),
                        "instrument_code": instrument_code,
                        "contract_code": contract_code,
                        "contract_name": contract_name,
                        "underlying_code": underlying_code,
                        "underlying_kind": underlying_kind,
                        "market": market,
                        "segment": segment,
                        "unit": unit,
                        "currency": currency,
                        "notes": notes,
                        "index_id": "",
                        "index_name": "",
                        "isin": "",
                        "data_start_date": "",
                        "data_end_date": "",
                        "data_rows": "",
                        "source_file": "",
                        "product_type": "OPTION" if "OPTION" in instrument_type.upper() else "FUTURE",
                        "contract_variant": "OPTION" if "OPTION" in instrument_type.upper() else "FUTURE",
                        "source_url": "https://www.eex.com/en/global-commodities/dry-freight",
                    }
                )

    # ICE: include the local specs we have (BDI + TCH).
    if ice_products_csv.exists():
        with ice_products_csv.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                venue = (row.get("venue") or "ICE").strip() or "ICE"
                symbol = (row.get("contract_symbol") or "").strip()
                contract_code = symbol
                contract_name = (row.get("product_name") or "").strip()
                underlying = (row.get("underlying_code") or "").strip()
                if not symbol or not underlying:
                    continue
                # Normalize underlying into our index code space when possible.
                if underlying.upper().startswith("HANDYSIZE"):
                    underlying = "BHSI"
                underlying_kind = "index" if underlying in index_meta else "reference_index"
                market = ""
                segment = ""
                if underlying in index_meta:
                    # Market/segment are best read from indices.csv, but keep blank here to avoid stale mappings.
                    pass
                rows_out.append(
                    {
                        "venue": "ICE",
                        "exchange_name": _venue_name("ICE"),
                        "instrument_code": symbol,
                        "contract_code": contract_code,
                        "contract_name": contract_name,
                        "underlying_code": underlying,
                        "underlying_kind": underlying_kind,
                        "market": market,
                        "segment": segment,
                        "unit": (row.get("unit_of_trading") or "").strip(),
                        "currency": (row.get("currency") or "").strip(),
                        "notes": (row.get("notes") or "").strip(),
                        "index_id": "",
                        "index_name": "",
                        "isin": "",
                        "data_start_date": "",
                        "data_end_date": "",
                        "data_rows": "",
                        "source_file": "",
                        "product_type": (row.get("product_type") or "FUTURE").strip().upper(),
                        "contract_variant": "FUTURE",
                        "source_url": (row.get("source") or "").strip(),
                    }
                )

    # Clearing contract universe: CME / ICE / SGX (skip EEX here to avoid ambiguous contract_code like 5TC).
    if clearing_csv.exists():
        with clearing_csv.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                venue = (row.get("clearing_house") or "").strip().upper()
                if venue not in {"CME", "ICE", "SGX"}:
                    continue

                contract_code = (row.get("contract_code") or "").strip()
                contract_name = (row.get("contract_name") or "").strip()
                contract_type = (row.get("contract_type") or "").strip().upper() or "FUTURE"
                source_url = (row.get("source_url") or "").strip()

                underlying_code = contract_code
                if not underlying_code and venue == "SGX":
                    underlying_code = _sgx_blank_contract_underlying(contract_name)
                if not underlying_code:
                    continue

                contract_variant = _variant_from_contract_name(contract_name, contract_type)
                if contract_code:
                    instrument_code = f"{contract_code}_{contract_variant}"
                else:
                    safe = (
                        underlying_code.replace(" ", "")
                        .replace("(", "")
                        .replace(")", "")
                        .replace("/", "_")
                        .replace("__", "_")
                    )
                    instrument_code = f"{safe}_{contract_variant}"

                if underlying_code in index_meta:
                    underlying_kind = "index"
                elif underlying_code in routes:
                    underlying_kind = "route"
                else:
                    underlying_kind = "basket"

                if underlying_kind == "route":
                    market = routes[underlying_code]["market"]
                    segment = routes[underlying_code]["segment"]
                elif underlying_kind == "basket":
                    market, segment = _infer_basket_market_segment(underlying_code)
                else:
                    market = ""
                    segment = ""

                rows_out.append(
                    {
                        "venue": venue,
                        "exchange_name": _venue_name(venue),
                        "instrument_code": instrument_code,
                        "contract_code": contract_code,
                        "contract_name": contract_name,
                        "underlying_code": underlying_code,
                        "underlying_kind": underlying_kind,
                        "market": market,
                        "segment": segment,
                        "unit": "",
                        "currency": "",
                        "notes": contract_name,
                        "index_id": "",
                        "index_name": "",
                        "isin": "",
                        "data_start_date": "",
                        "data_end_date": "",
                        "data_rows": "",
                        "source_file": "",
                        "product_type": contract_type,
                        "contract_variant": contract_variant,
                        "source_url": source_url,
                    }
                )

    # Fill index metadata where possible.
    for r in rows_out:
        if r.get("underlying_kind") != "index":
            continue
        code = (r.get("underlying_code") or "").strip()
        meta = index_meta.get(code)
        if not meta:
            continue
        r["index_id"] = meta.index_id
        r["index_name"] = meta.index_name
        r["isin"] = meta.isin
        r["data_start_date"] = meta.data_start_date
        r["data_end_date"] = meta.data_end_date
        r["data_rows"] = meta.data_rows
        r["source_file"] = meta.source_file

    # Add validation links (deterministic: official landing pages + a per-row search link).
    for r in rows_out:
        venue = (r.get("venue") or "").strip().upper()
        underlying_kind = (r.get("underlying_kind") or "").strip().lower()
        underlying_code = (r.get("underlying_code") or "").strip()
        contract_code = (r.get("contract_code") or "").strip()
        contract_name = (r.get("contract_name") or "").strip()
        instrument_code = (r.get("instrument_code") or "").strip()

        r["validation_contract_url"] = EEX_DRY_URL if venue == "EEX" else CLEARING_URL
        if underlying_kind == "route":
            r["validation_underlying_url"] = ROUTES_URL
        elif underlying_kind == "index":
            r["validation_underlying_url"] = INDICES_URL
        elif underlying_kind == "basket":
            r["validation_underlying_url"] = EEX_DRY_URL if venue == "EEX" else INDICES_URL
        else:
            r["validation_underlying_url"] = ""

        parts: list[str] = []
        if venue:
            parts.append(venue)
        if contract_code:
            parts.append(contract_code)
        if instrument_code and instrument_code != contract_code:
            parts.append(instrument_code)
        if contract_name:
            parts.append(contract_name)
        if underlying_code:
            parts.append(f"settles to {underlying_code}")
        r["validation_search_url"] = _search_url(" ".join(parts))

    # De-duplicate by (venue, instrument_code).
    seen: set[tuple[str, str]] = set()
    unique_rows: list[dict[str, str]] = []
    for r in rows_out:
        k = (r.get("venue", "").strip(), r.get("instrument_code", "").strip())
        if not k[0] or not k[1]:
            continue
        if k in seen:
            continue
        seen.add(k)
        unique_rows.append(r)

    unique_rows.sort(key=lambda d: (d.get("venue", ""), d.get("market", ""), d.get("segment", ""), d.get("instrument_code", "")))

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in unique_rows:
            w.writerow({k: (r.get(k) or "") for k in fieldnames})


if __name__ == "__main__":
    build()
