from __future__ import annotations

import csv
import urllib.parse
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]


CLEARING_URL = "https://www.balticexchange.com/en/data-services/freight-derivatives-/Clearing.html"
ROUTES_URL = "https://www.balticexchange.com/en/data-services/routes.html"
INDICES_URL = "https://www.balticexchange.com/en/data-services/market-information0/indices.html"
EEX_DRY_URL = "https://www.eex.com/en/global-commodities/dry-freight"
EEX_PRODUCT_CODES_URL = "https://www.eex.com/en/trading-resources/product-specifications/contract-details-product-codes"


def _search_url(query: str) -> str:
    q = urllib.parse.quote_plus(query.strip())
    return f"https://duckduckgo.com/?q={q}"


def main() -> None:
    in_path = PROJECT_DIR / "datasets/ffas/ffa_instruments.csv"
    if not in_path.exists():
        raise SystemExit(f"Missing {in_path}")

    with in_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    new_cols = [
        "validation_contract_url",
        "validation_underlying_url",
        "validation_search_url",
    ]
    for c in new_cols:
        if c not in fieldnames:
            fieldnames.append(c)

    for row in rows:
        venue = (row.get("venue") or "").strip().upper()
        contract_code = (row.get("contract_code") or "").strip()
        contract_name = (row.get("contract_name") or "").strip()
        instrument_code = (row.get("instrument_code") or "").strip()
        underlying_kind = (row.get("underlying_kind") or "").strip().lower()
        underlying_code = (row.get("underlying_code") or "").strip()

        # Contract validation: where to find this contract listed/spec'd.
        if venue == "EEX":
            row["validation_contract_url"] = EEX_DRY_URL
        else:
            row["validation_contract_url"] = CLEARING_URL

        # Underlying validation: where to read the definition of what it settles to.
        if underlying_kind == "route":
            row["validation_underlying_url"] = ROUTES_URL
        elif underlying_kind == "index":
            row["validation_underlying_url"] = INDICES_URL
        elif underlying_kind == "basket":
            # Baskets are typically described in indices methodology and/or venue spec tables.
            row["validation_underlying_url"] = EEX_DRY_URL if venue == "EEX" else INDICES_URL
        else:
            row["validation_underlying_url"] = ""

        # Search validation: quick way to find an official page/PDF by code/name.
        parts = []
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
        row["validation_search_url"] = _search_url(" ".join(parts))

        # For EEX, also point users at the product-codes landing page via the existing `source_url` field.
        if venue == "EEX" and not (row.get("source_url") or "").strip():
            row["source_url"] = EEX_PRODUCT_CODES_URL

    with in_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (row.get(k) or "") for k in fieldnames})


if __name__ == "__main__":
    main()

