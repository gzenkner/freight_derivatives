#!/usr/bin/env python3

"""
Build a ports+coordinates reference dataset from the World Port Index (Pub 150).

Source dataset (example mirror):
  UpdatedPub150.csv (CSV, ~3.7k ports)

This script extracts a compact, analysis-friendly subset:
  - wpi_number
  - region_name
  - main_port_name
  - alternate_port_name
  - unlocode
  - country_code
  - latitude
  - longitude

It does not download the file itself; pair it with curl/wget or your own data pipeline.
"""

from __future__ import annotations

import csv
from pathlib import Path


IN_COLS = {
    "World Port Index Number": "wpi_number",
    "Region Name": "region_name",
    "Main Port Name": "main_port_name",
    "Alternate Port Name": "alternate_port_name",
    "UN/LOCODE": "unlocode",
    "Country Code": "country_code",
    "Latitude": "latitude",
    "Longitude": "longitude",
}

OUT_COLS = list(IN_COLS.values())


def _norm(s: str) -> str:
    return (s or "").strip()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True, help="Path to UpdatedPub150.csv")
    parser.add_argument("--out", dest="out_path", required=True, help="Output CSV path")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with in_path.open("r", encoding="utf-8-sig", newline="") as f_in:
        reader = csv.DictReader(f_in)
        missing = [c for c in IN_COLS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Missing expected columns: {missing}")

        with out_path.open("w", encoding="utf-8", newline="") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=OUT_COLS)
            writer.writeheader()

            for row in reader:
                out_row = {IN_COLS[k]: _norm(row.get(k, "")) for k in IN_COLS}
                # Keep only rows with coordinates and a name.
                if not out_row["main_port_name"]:
                    continue
                if not out_row["latitude"] or not out_row["longitude"]:
                    continue
                writer.writerow(out_row)

    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

