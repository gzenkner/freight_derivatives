# SeeCapitalMarkets (Shipping Indexes) downloader

This folder contains a small script to:
1) read all index pages linked from:
```text
https://seecapitalmarkets.com/en/shipping-indexes
```
2) discover each `IndexValueId=...` detail page
3) pull historical data via the site’s JSON endpoints
4) write the Excel file(s) locally

Run (from repo root):
```bash
python3 datasets/indices/download_seecapitalmarkets_shipping_indexes.py
```

Useful options:
```bash
# only print what would be downloaded
python3 datasets/indices/download_seecapitalmarkets_shipping_indexes.py --dry-run

# limit number of indices (for testing)
python3 datasets/indices/download_seecapitalmarkets_shipping_indexes.py --limit 5

# only Baltic Exchange indices (filters by datasets/exchange_reference/indices.csv)
python3 datasets/indices/download_seecapitalmarkets_shipping_indexes.py --only-baltic

# write files somewhere else
python3 datasets/indices/download_seecapitalmarkets_shipping_indexes.py --out-dir /tmp/indices
```

Outputs:
- `index_catalog.csv`: one row per IndexValueId (detail URL, discovered Excel URL, local filename, status)
- `excels/`: downloaded `.xls`/`.xlsx` files
- `json/`: raw JSON payloads used to build the Excel files

Note:
- This script is intended for normal, respectful use. It rate-limits requests and does not attempt to bypass paywalls or bot protection.
