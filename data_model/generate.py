from __future__ import annotations

import csv
import html
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def _read_csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    return [h.strip() for h in header if h and h.strip()]


def _read_unique_values(path: Path, column: str) -> list[str]:
    if not path.exists():
        return []
    out: set[str] = set()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            v = (row.get(column) or "").strip()
            if v:
                out.add(v)
    return sorted(out)


def _mermaid_table(name: str, fields: list[tuple[str, str]]) -> str:
    lines = [f"{name} {{"]
    for t, f in fields:
        lines.append(f"  {t} {f}")
    lines.append("}")
    return "\n".join(lines)


def build_mermaid() -> str:
    # Reference datasets
    indices_ref = PROJECT_DIR / "datasets/exchange_reference/indices.csv"
    routes_ref = PROJECT_DIR / "datasets/exchange_reference/routes.csv"
    vessels_ref = PROJECT_DIR / "datasets/exchange_reference/vessel_types.csv"
    index_components = PROJECT_DIR / "datasets/exchange_reference/index_components.csv"

    # Derivatives datasets
    ffa_instruments = PROJECT_DIR / "datasets/ffas/ffa_instruments.csv"
    clearing_contracts = PROJECT_DIR / "datasets/ffas/clearing_contracts.csv"
    ffa_brokers = PROJECT_DIR / "datasets/exchange_reference/ffa_brokers.csv"

    baskets = _read_unique_values(ffa_instruments, "underlying_code")
    basket_kinds = _read_unique_values(ffa_instruments, "underlying_kind")
    # Only keep basket codes if we can identify basket rows.
    if "basket" in {k.lower() for k in basket_kinds}:
        basket_codes = _read_unique_values(ffa_instruments, "underlying_code")
        # A cheap filter: keep codes containing "TC" or parenthesized variants that appear in EEX-style baskets.
        basket_codes = [c for c in basket_codes if "TC" in c or "(" in c]
    else:
        basket_codes = []

    # Keep the ERD stable and “dbdiagram-like”: a small number of core tables.
    parts: list[str] = ["erDiagram"]

    parts.append(
        _mermaid_table(
            "INDICES",
            [
                ("string", "index_code PK"),
                ("string", "index_name"),
                ("string", "market"),
                ("string", "frequency"),
                ("string", "description"),
                ("string", "source_url"),
            ],
        )
    )

    parts.append(
        _mermaid_table(
            "INDEX_TIMESERIES",
            [
                ("string", "index_code FK"),
                ("date", "date"),
                ("float", "close"),
                ("float", "open"),
                ("float", "high"),
                ("float", "low"),
            ],
        )
    )

    parts.append(
        _mermaid_table(
            "ROUTES",
            [
                ("string", "route_code PK"),
                ("string", "short_description"),
                ("string", "market"),
                ("string", "segment"),
                ("string", "port_of_embarkment"),
                ("string", "port_of_arrival"),
                ("string", "source_url"),
            ],
        )
    )

    parts.append(
        _mermaid_table(
            "VESSEL_TYPES",
            [
                ("string", "vessel_type PK"),
                ("string", "market"),
                ("string", "segment"),
                ("int", "dwt_mt"),
                ("int", "max_age_years"),
                ("string", "notes"),
                ("string", "source_url"),
            ],
        )
    )

    parts.append(
        _mermaid_table(
            "INDEX_COMPONENTS",
            [
                ("string", "index_code FK"),
                ("string", "component_code"),
                ("string", "component_type"),
                ("string", "mode"),
                ("float", "weight"),
                ("float", "scale_factor"),
                ("string", "source_url"),
            ],
        )
    )

    parts.append(
        _mermaid_table(
            "CLEARING_CONTRACTS",
            [
                ("string", "clearing_house"),
                ("string", "contract_code"),
                ("string", "contract_name"),
                ("string", "contract_type"),
                ("string", "source_url"),
            ],
        )
    )

    parts.append(
        _mermaid_table(
            "FFA_CONTRACTS",
            [
                ("string", "venue"),
                ("string", "instrument_code PK"),
                ("string", "contract_code"),
                ("string", "contract_name"),
                ("string", "product_type"),
                ("string", "contract_variant"),
                ("string", "underlying_kind"),
                ("string", "underlying_code"),
                ("string", "market"),
                ("string", "segment"),
                ("string", "unit"),
                ("string", "currency"),
                ("string", "source_url"),
                ("string", "validation_search_url"),
            ],
        )
    )

    parts.append(
        _mermaid_table(
            "FFA_BROKERS",
            [
                ("string", "broker_name PK"),
                ("string", "market"),
                ("string", "segment"),
                ("string", "website_url"),
                ("string", "approved_by"),
            ],
        )
    )

    if basket_codes:
        parts.append(
            _mermaid_table(
                "BASKETS",
                [
                    ("string", "basket_code PK"),
                ],
            )
        )

    # Relationships (conceptual; some are conditional in practice).
    parts.append("INDICES ||--o{ INDEX_TIMESERIES : has")
    parts.append("INDICES ||--o{ INDEX_COMPONENTS : composed_of")
    parts.append("ROUTES ||--o{ INDEX_COMPONENTS : can_feed")
    parts.append("VESSEL_TYPES ||--o{ INDEX_COMPONENTS : specs")
    parts.append("CLEARING_CONTRACTS ||--o{ FFA_CONTRACTS : listed_as")
    parts.append("ROUTES ||--o{ FFA_CONTRACTS : settles_to")
    parts.append("INDICES ||--o{ FFA_CONTRACTS : settles_to")
    if basket_codes:
        parts.append("BASKETS ||--o{ FFA_CONTRACTS : settles_to")

    # Footnote-style “what this diagram is built from” section as Mermaid comments.
    parts.append("%% Sources in this repo:")
    parts.append(f"%% - {indices_ref.relative_to(PROJECT_DIR)} (columns: {', '.join(_read_csv_header(indices_ref)[:8])})")
    parts.append(f"%% - {routes_ref.relative_to(PROJECT_DIR)} (columns: {', '.join(_read_csv_header(routes_ref)[:8])})")
    parts.append(f"%% - {vessels_ref.relative_to(PROJECT_DIR)} (columns: {', '.join(_read_csv_header(vessels_ref)[:8])})")
    parts.append(f"%% - {index_components.relative_to(PROJECT_DIR)} (columns: {', '.join(_read_csv_header(index_components)[:8])})")
    parts.append(f"%% - {clearing_contracts.relative_to(PROJECT_DIR)} (columns: {', '.join(_read_csv_header(clearing_contracts)[:8])})")
    parts.append(f"%% - {ffa_instruments.relative_to(PROJECT_DIR)} (columns: {', '.join(_read_csv_header(ffa_instruments)[:8])})")

    return "\n\n".join(parts) + "\n"


def build_html(mermaid_src: str) -> str:
    mermaid_escaped = html.escape(mermaid_src)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Freight Derivatives — Data Model</title>
    <style>
      :root {{
        --bg: #0b1020;
        --panel: #0f172a;
        --text: #e5e7eb;
        --muted: #9ca3af;
        --border: rgba(255,255,255,0.10);
        --code: #0b1224;
      }}
      body {{
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
        background: var(--bg);
        color: var(--text);
      }}
      header {{
        padding: 18px 22px;
        border-bottom: 1px solid var(--border);
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0));
      }}
      header h1 {{
        font-size: 16px;
        margin: 0 0 6px 0;
        font-weight: 650;
        letter-spacing: 0.2px;
      }}
      header p {{
        margin: 0;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.35;
      }}
      main {{
        padding: 18px 22px 28px;
        max-width: 1200px;
        margin: 0 auto;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px;
        overflow: auto;
      }}
      details {{
        margin-top: 14px;
      }}
      summary {{
        cursor: pointer;
        color: var(--muted);
        font-size: 13px;
      }}
      pre {{
        margin: 10px 0 0;
        padding: 12px;
        background: var(--code);
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: auto;
        color: #d1d5db;
        font-size: 12px;
        line-height: 1.35;
      }}
      a {{
        color: #93c5fd;
      }}
    </style>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({{
        startOnLoad: true,
        theme: "dark",
        securityLevel: "loose",
        er: {{ useMaxWidth: true }},
      }});
    </script>
  </head>
  <body>
    <header>
      <h1>Freight Derivatives — Data Model</h1>
      <p>“dbdiagram-style” ERD rendered with Mermaid. Open this file in any browser.</p>
    </header>
    <main>
      <div class="panel">
        <div class="mermaid">
{mermaid_escaped}
        </div>
      </div>
      <details>
        <summary>Show Mermaid source</summary>
        <pre><code>{mermaid_escaped}</code></pre>
      </details>
      <p style="color:var(--muted);font-size:12px;margin-top:14px">
        Note: some relationships are conditional in practice (e.g. FFA underlyings can be routes, indices, or baskets).
      </p>
    </main>
  </body>
</html>
"""


def main() -> None:
    out_dir = PROJECT_DIR / "data_model"
    out_dir.mkdir(parents=True, exist_ok=True)

    mermaid_src = build_mermaid()
    (out_dir / "erd.mmd").write_text(mermaid_src, encoding="utf-8")
    (out_dir / "erd.html").write_text(build_html(mermaid_src), encoding="utf-8")


if __name__ == "__main__":
    main()

