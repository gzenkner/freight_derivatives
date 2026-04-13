from __future__ import annotations

import html
import json
import re
import csv
from dataclasses import dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]

MAX_DIAGRAM_COLS = 10


@dataclass(frozen=True)
class Column:
    name: str
    typ: str = "string"
    pk: bool = False
    fk: bool = False
    ref_table: str | None = None
    ref_col: str | None = None


@dataclass(frozen=True)
class Table:
    name: str
    source: str | None
    columns: list[Column]
    description: str = ""


_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]+")


def _sanitize_column(raw: str) -> str:
    raw = raw.replace("\ufeff", "").strip()
    out = _SANITIZE_RE.sub("_", raw).strip("_").lower()
    return out or "col"


def _tbl_mermaid(table: Table, cols: list[Column]) -> str:
    lines = [f"{table.name} {{"]
    for c in cols:
        suffix = ""
        if c.pk:
            suffix += " PK"
        if c.fk:
            suffix += " FK"
        lines.append(f"  {c.typ} {c.name}{suffix}")
    lines.append("}")
    return "\n".join(lines)


def _table_json(table: Table) -> dict:
    return {
        "name": table.name,
        "source": table.source,
        "description": table.description,
        "columns": [
            {
                "name": c.name,
                "type": c.typ,
                "pk": c.pk,
                "fk": c.fk,
                "ref_table": c.ref_table,
                "ref_col": c.ref_col,
            }
            for c in table.columns
        ],
    }


def build_model() -> tuple[str, str, list[dict]]:
    """
    Produces:
    - Mermaid ERD source (diagram view): max 10 columns per table.
    - Mermaid ERD source (full): all columns.
    - JSON schema for the HTML “expand columns” panel.
    """
    def read_header(rel_path: str) -> list[str]:
        path = PROJECT_DIR / rel_path
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            return next(reader, [])

    def extend_from_header(table: Table) -> Table:
        if not table.source:
            return table
        header = read_header(table.source)
        if not header:
            return table
        existing = {c.name for c in table.columns}
        extra: list[Column] = []
        for raw in header:
            name = _sanitize_column(raw)
            if name in existing:
                continue
            extra.append(Column(name))
        if not extra:
            return table
        return Table(
            name=table.name,
            source=table.source,
            description=table.description,
            columns=table.columns + extra,
        )

    port_pk = "main_port_name"
    ports = extend_from_header(
        Table(
        name="PORTS",
        source="datasets/exchange_reference/ports_world_port_index.csv",
        description="World Port Index reference data (trimmed in diagram; full schema expandable).",
        columns=[
            Column(port_pk, pk=True),
            Column("world_port_index_number"),
            Column("country_code"),
            Column("un_locode"),
            Column("region_name"),
            Column("world_water_body"),
            Column("harbor_size"),
            Column("publication_link"),
            Column("latitude", typ="float"),
            Column("longitude", typ="float"),
        ],
        )
    )

    routes = Table(
        name="ROUTES",
        source="datasets/exchange_reference/routes.csv",
        description="Baltic-style route definitions (assessed lane / trip templates).",
        columns=[
            Column("route_code", pk=True),
            Column("short_description"),
            Column("market"),
            Column("segment"),
            Column("source_url"),
            Column(
                "port_of_embarkment",
                fk=True,
                ref_table="PORTS",
                ref_col=port_pk,
            ),
            Column(
                "port_of_arrival",
                fk=True,
                ref_table="PORTS",
                ref_col=port_pk,
            ),
        ],
    )

    vessel_types = Table(
        name="VESSEL_TYPES",
        source="datasets/exchange_reference/vessel_types.csv",
        description="Reference vessel templates used by timecharter-style routes.",
        columns=[
            Column("vessel_type", pk=True),
            Column("market"),
            Column("segment"),
            Column("dwt_mt", typ="int"),
            Column("max_age_years", typ="int"),
            Column("loa_m", typ="float"),
            Column("beam_m", typ="float"),
            Column("tpc", typ="float"),
            Column("grain_cbm", typ="float"),
            Column("bale_cbm", typ="float"),
            Column("notes"),
            Column("source_url"),
        ],
    )

    indices = Table(
        name="INDICES",
        source="datasets/exchange_reference/indices.csv",
        description="Index reference table (published aggregates).",
        columns=[
            Column("index_code", pk=True),
            Column("index_name"),
            Column("market"),
            Column("frequency"),
            Column("description"),
            Column("source_url"),
        ],
    )

    index_components = Table(
        name="INDEX_COMPONENTS",
        source="datasets/exchange_reference/index_components.csv",
        description="How an index is composed from routes and/or other indices.",
        columns=[
            Column("index_code", typ="string", pk=True, fk=True, ref_table="INDICES", ref_col="index_code"),
            Column("component_code", pk=True),
            Column("component_type"),
            Column("mode"),
            Column("weight", typ="float"),
            Column("scale_factor", typ="float"),
            Column("source_url"),
        ],
    )

    index_catalog = Table(
        name="INDEX_CATALOG",
        source="datasets/indices/index_catalog.csv",
        description="Metadata and captured calculation snippets for indices.",
        columns=[
            Column("index_id", pk=True),
            Column("index_value_id"),
            Column("index_short_name"),
            Column("index_name"),
            Column("isin"),
            Column("detail_url"),
            Column("history_url"),
            Column("local_file"),
            Column("rows", typ="int"),
            Column("status"),
            Column("error"),
            Column("calculation"),
        ],
    )

    index_timeseries = Table(
        name="INDEX_TIMESERIES",
        source="datasets/indices/json/*",
        description="Time series values for published indices.",
        columns=[
            Column("index_name", pk=True, fk=True, ref_table="INDICES", ref_col="index_name"),
            Column("date", typ="date", pk=True),
            Column("price", typ="float"),
            Column("open", typ="float"),
            Column("high", typ="float"),
            Column("low", typ="float"),
            Column("source_file"),
        ],
    )

    ffa_instruments = extend_from_header(
        Table(
        name="FFA_INSTRUMENTS",
        source="datasets/ffas/ffa_instruments.csv",
        description="Tradable freight derivatives instruments (contracts and options).",
        columns=[
            Column("instrument_code", pk=True),
            Column("venue"),
            Column("exchange_name"),
            Column("contract_code"),
            Column("contract_name"),
            Column("product_type"),
            Column("contract_variant"),
            Column("underlying_kind"),
            Column("underlying_code"),
            Column("market"),
            Column("segment"),
            Column("unit"),
            Column("currency"),
            Column("notes"),
            Column("source_url"),
            Column("validation_contract_url"),
            Column("validation_underlying_url"),
            Column("validation_search_url"),
        ],
        )
    )

    clearing_contracts = Table(
        name="CLEARING_CONTRACTS",
        source="datasets/ffas/clearing_contracts.csv",
        description="Clearing lists (which underlying contracts a clearing house supports).",
        columns=[
            Column("clearing_house", pk=True),
            Column("contract_code", pk=True),
            Column("contract_name"),
            Column("contract_type"),
            Column("source_url"),
        ],
    )

    ffa_brokers = Table(
        name="FFA_BROKERS",
        source="datasets/exchange_reference/ffa_brokers.csv",
        description="Broker reference list (incl. Baltic-approved Forward Assessments brokers).",
        columns=[
            Column("broker_name", pk=True),
            Column("market"),
            Column("segment"),
            Column("website_url"),
            Column("approved_by"),
            Column("notes"),
        ],
    )

    tables: list[Table] = [
        ports,
        routes,
        vessel_types,
        indices,
        index_components,
        index_catalog,
        index_timeseries,
        clearing_contracts,
        ffa_instruments,
        ffa_brokers,
    ]

    diagram_parts: list[str] = ["erDiagram"]
    full_parts: list[str] = ["erDiagram"]

    schema_json = [_table_json(t) for t in tables]

    for t in tables:
        full_parts.append(_tbl_mermaid(t, t.columns))
        if len(t.columns) <= MAX_DIAGRAM_COLS:
            diagram_parts.append(_tbl_mermaid(t, t.columns))
        else:
            shown = t.columns[:MAX_DIAGRAM_COLS]
            remaining = len(t.columns) - len(shown)
            diagram_parts.append(
                _tbl_mermaid(
                    t,
                    shown + [Column(f"…_{remaining}_more_columns", typ="string")],
                )
            )

    # Relationships (use real FK columns where we have them; others are conceptual)
    rels = [
        "PORTS ||--o{ ROUTES : embarkment",
        "PORTS ||--o{ ROUTES : arrival",
        "INDICES ||--o{ INDEX_COMPONENTS : composed_of",
        "ROUTES ||--o{ INDEX_COMPONENTS : can_feed",
        "INDICES ||--o{ INDEX_COMPONENTS : can_feed",
        "INDICES ||--o{ INDEX_TIMESERIES : has",
        "ROUTES ||--o{ FFA_INSTRUMENTS : settles_to",
        "INDICES ||--o{ FFA_INSTRUMENTS : settles_to",
    ]
    diagram_parts += rels
    full_parts += rels

    # Mermaid comments with sources
    diagram_parts.append("%% Tip: diagram shows max 10 columns per table; expand on the right for full schema.")
    full_parts.append("%% Tip: diagram shows full schemas (used by the right-hand panel).")

    return "\n\n".join(diagram_parts) + "\n", "\n\n".join(full_parts) + "\n", schema_json


def build_html(mermaid_src: str, schema: list[dict]) -> str:
    escaped = html.escape(mermaid_src)
    schema_blob = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Freight Derivatives — Data Model</title>
    <style>
      :root {{
        --bg: #f6f7fb;
        --panel: #ffffff;
        --text: #0f172a;
        --muted: #475569;
        --border: rgba(15,23,42,0.10);
        --shadow: 0 10px 30px rgba(15,23,42,0.08);
        --btn: #111827;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
        color: var(--text);
        background: var(--bg);
      }}
      header {{
        position: sticky;
        top: 0;
        z-index: 10;
        display: flex;
        gap: 14px;
        align-items: center;
        padding: 10px 14px;
        border-bottom: 1px solid var(--border);
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(10px);
      }}
      header .title {{
        display: flex;
        flex-direction: column;
        gap: 2px;
        min-width: 240px;
      }}
      header h1 {{
        font-size: 14px;
        margin: 0;
        font-weight: 650;
        letter-spacing: 0.2px;
      }}
      header p {{
        margin: 0;
        font-size: 12px;
        color: var(--muted);
        line-height: 1.2;
      }}
      .toolbar {{
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
      }}
      button {{
        appearance: none;
        border: 1px solid var(--border);
        background: var(--panel);
        color: var(--btn);
        padding: 7px 10px;
        border-radius: 10px;
        font-size: 12px;
        cursor: pointer;
        box-shadow: 0 1px 0 rgba(0,0,0,0.02);
      }}
      button:hover {{
        box-shadow: 0 6px 16px rgba(15,23,42,0.08);
      }}
      main {{
        padding: 14px;
      }}
      .grid {{
        display: grid;
        grid-template-columns: 1.7fr 1fr;
        gap: 12px;
        height: calc(100vh - 74px);
      }}
      .frame {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: var(--shadow);
        overflow: hidden;
        min-height: 0;
      }}
      #diagram {{
        height: 100%;
        width: 100%;
        cursor: grab;
      }}
      #diagram:active {{
        cursor: grabbing;
      }}
      .side {{
        display: flex;
        flex-direction: column;
        min-height: 0;
      }}
      .side h2 {{
        margin: 0 0 10px;
        font-size: 13px;
        letter-spacing: 0.2px;
      }}
      .side .hint {{
        margin: 0 0 10px;
        color: var(--muted);
        font-size: 12px;
        line-height: 1.25;
      }}
      .schema {{
        overflow: auto;
        padding: 10px;
      }}
      .table {{
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 10px;
      }}
      .table header {{
        position: static;
        padding: 0;
        border: 0;
        background: transparent;
        backdrop-filter: none;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }}
      .table header .name {{
        font-weight: 700;
        font-size: 12px;
      }}
      .table header .meta {{
        color: var(--muted);
        font-size: 11px;
        line-height: 1.25;
      }}
      .cols {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 8px;
        font-size: 11px;
      }}
      .cols th, .cols td {{
        text-align: left;
        padding: 6px 6px;
        border-bottom: 1px solid var(--border);
        vertical-align: top;
      }}
      .cols th {{
        color: var(--muted);
        font-weight: 650;
      }}
      .badge {{
        display: inline-block;
        font-size: 10px;
        padding: 1px 6px;
        border-radius: 999px;
        border: 1px solid var(--border);
        margin-left: 6px;
        color: var(--muted);
      }}
      .btn-link {{
        border: 0;
        background: transparent;
        padding: 6px 0 0;
        color: #2563eb;
        cursor: pointer;
        font-size: 11px;
      }}
      @media (max-width: 980px) {{
        .grid {{ grid-template-columns: 1fr; height: auto; }}
        .frame {{ height: 520px; }}
      }}
      details {{
        margin-top: 12px;
      }}
      summary {{
        cursor: pointer;
        font-size: 12px;
        color: var(--muted);
      }}
      pre {{
        margin: 8px 0 0;
        padding: 12px;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: #0b1220;
        color: #e5e7eb;
        overflow: auto;
        font-size: 12px;
        line-height: 1.35;
      }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
  </head>
  <body>
    <header>
      <div class="title">
        <h1>Freight Derivatives — Data Model</h1>
        <p>Mermaid ERD with pan/zoom (dbdiagram-like navigation).</p>
      </div>
      <div class="toolbar">
        <button id="fit">Fit</button>
        <button id="center">Center</button>
        <button id="zin">Zoom in</button>
        <button id="zout">Zoom out</button>
        <button id="reset">Reset</button>
      </div>
    </header>
    <main>
      <div class="grid">
        <div class="frame">
          <div id="diagram" aria-label="ER diagram"></div>
        </div>
        <div class="frame side">
          <div class="schema">
            <h2>Tables</h2>
            <p class="hint">The ERD shows up to {MAX_DIAGRAM_COLS} columns per table. Expand below to see full schemas (PK/FK included).</p>
            <div id="schema"></div>
          </div>
        </div>
      </div>
      <details>
        <summary>Show Mermaid source (diagram)</summary>
        <pre><code>{escaped}</code></pre>
      </details>
    </main>

    <script id="schema-json" type="application/json">{schema_blob}</script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

      const src = `{escaped}`.replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
      const schema = JSON.parse(document.getElementById("schema-json").textContent || "[]");

      mermaid.initialize({{
        startOnLoad: false,
        securityLevel: "loose",
        theme: "default",
        er: {{ useMaxWidth: false }},
        themeVariables: {{
          primaryColor: "#ffffff",
          primaryBorderColor: "#cbd5e1",
          primaryTextColor: "#0f172a",
          lineColor: "#94a3b8",
          tertiaryColor: "#f8fafc",
        }},
      }});

      const container = document.getElementById("diagram");
      const {{ svg }} = await mermaid.render("erd", src);
      container.innerHTML = svg;

      const svgEl = container.querySelector("svg");
      svgEl.setAttribute("width", "100%");
      svgEl.setAttribute("height", "100%");

      const panZoom = window.svgPanZoom(svgEl, {{
        zoomEnabled: true,
        controlIconsEnabled: false,
        fit: true,
        center: true,
        minZoom: 0.1,
        maxZoom: 25,
        zoomScaleSensitivity: 0.25,
      }});

      const bind = (id, fn) => {{
        const el = document.getElementById(id);
        if (el) el.addEventListener("click", fn);
      }};

      bind("fit", () => panZoom.fit());
      bind("center", () => panZoom.center());
      bind("zin", () => panZoom.zoomIn());
      bind("zout", () => panZoom.zoomOut());
      bind("reset", () => {{ panZoom.resetZoom(); panZoom.center(); }});

      const schemaRoot = document.getElementById("schema");
      const renderTable = (t) => {{
        const wrap = document.createElement("section");
        wrap.className = "table";

        const head = document.createElement("header");
        const name = document.createElement("div");
        name.className = "name";
        name.textContent = t.name;
        head.appendChild(name);

        const meta = document.createElement("div");
        meta.className = "meta";
        const parts = [];
        if (t.source) parts.push(t.source);
        if (t.description) parts.push(t.description);
        meta.textContent = parts.join(" — ");
        head.appendChild(meta);
        wrap.appendChild(head);

        const table = document.createElement("table");
        table.className = "cols";
        table.innerHTML = `<thead><tr><th>Column</th><th>Type</th><th>Keys</th><th>References</th></tr></thead>`;
        const body = document.createElement("tbody");
        table.appendChild(body);
        wrap.appendChild(table);

        const rows = t.columns || [];
        let expanded = false;
        const draw = () => {{
          body.innerHTML = "";
          const max = expanded ? rows.length : Math.min(rows.length, {MAX_DIAGRAM_COLS});
          for (let i = 0; i < max; i++) {{
            const c = rows[i];
            const tr = document.createElement("tr");
            const keys = [];
            if (c.pk) keys.push("PK");
            if (c.fk) keys.push("FK");
            const ref = (c.ref_table && c.ref_col) ? `${{c.ref_table}}.${{c.ref_col}}` : "";
            tr.innerHTML = `<td><code>${{c.name}}</code></td><td>${{c.type}}</td><td>${{keys.join(", ")}}</td><td>${{ref}}</td>`;
            body.appendChild(tr);
          }}
        }};
        draw();

        if (rows.length > {MAX_DIAGRAM_COLS}) {{
          const btn = document.createElement("button");
          btn.className = "btn-link";
          btn.type = "button";
          const update = () => {{
            btn.textContent = expanded ? "Show fewer columns" : `Show all columns (${{rows.length}})`;
          }};
          update();
          btn.addEventListener("click", () => {{
            expanded = !expanded;
            update();
            draw();
          }});
          wrap.appendChild(btn);
        }}

        return wrap;
      }};

      schema.forEach((t) => schemaRoot.appendChild(renderTable(t)));
    </script>
  </body>
</html>
"""


def main() -> None:
    out_dir = PROJECT_DIR / "data_model"
    out_dir.mkdir(parents=True, exist_ok=True)

    mermaid_diagram, mermaid_full, schema = build_model()
    (out_dir / "erd.mmd").write_text(mermaid_full, encoding="utf-8")
    (out_dir / "erd.html").write_text(build_html(mermaid_diagram, schema), encoding="utf-8")


if __name__ == "__main__":
    main()
