from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

from dataframes import load_dataframes


def _js_string(value: str) -> str:
    """
    Return a JS string literal (double-quoted) safe to embed in a <script>.
    Also prevents prematurely closing the script tag.
    """
    s = json.dumps(value)
    return s.replace("</script>", "<\\/script>")


def _iframe_srcdoc(element_id: str, doc_html: str, height: int) -> str:
    return (
        f'<iframe class="embed" id="{html.escape(element_id)}" '
        f'title="{html.escape(element_id)}" style="height:{int(height)}px"></iframe>\n'
        f"<script>document.getElementById({_js_string(element_id)}).srcdoc = {_js_string(doc_html)};</script>\n"
    )


def _altair_iframe(element_id: str, chart, height: int) -> str:
    # Embed full HTML for isolation (avoids Vega global conflicts).
    doc_html = chart.to_html()
    return _iframe_srcdoc(element_id, doc_html, height=height)


def _pydeck_iframe(element_id: str, deck, height: int) -> str:
    doc_html = deck.to_html(as_string=True)
    return _iframe_srcdoc(element_id, doc_html, height=height)


def _df_table(df) -> str:
    return df.to_html(index=False, escape=True, classes="df")


def build_report(out_path: Path) -> None:
    try:
        import altair as alt
        import pandas as pd
        import pydeck as pdk
    except ModuleNotFoundError as exc:
        missing = exc.name or "a required dependency"
        print(
            f"Missing dependency: {missing}. Run this exporter in the same environment as Streamlit "
            f"(needs pandas, altair, pydeck).",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    # Allow exporting full datasets (Altair defaults to a 5000-row limit).
    alt.data_transformers.disable_max_rows()

    project_dir = Path(__file__).resolve().parents[1]

    indices_json_path = project_dir / "datasets/indices/json"
    vessels_path = project_dir / "datasets/exchange_reference/vessel_types.csv"
    world_ports_path = project_dir / "datasets/exchange_reference/ports_world_port_index.csv"
    indices_path = project_dir / "datasets/exchange_reference/indices.csv"
    routes_path = project_dir / "datasets/exchange_reference/routes.csv"

    df_bdi, df_vessels, df_ports, _df_indices, df_baltic_routes = load_dataframes(
        baltic_indices_path=indices_json_path,
        vessels_path=str(vessels_path),
        world_ports_path=str(world_ports_path),
        indices_path=str(indices_path),
        baltic_routes_path=str(routes_path),
    )

    # ---- Indices: Coverage ----
    coverage_color = "#9CA3AF"
    domain_pad_days = 180
    df_dates = df_bdi.copy()
    if "date" not in df_dates.columns and "Date" in df_dates.columns:
        df_dates["date"] = pd.to_datetime(df_dates["Date"], errors="coerce").dt.date

    df_dates = df_dates[df_dates["IndexName"].astype(str).str.strip().str.startswith("Baltic ", na=False)]

    df_ranges = (
        df_dates[["IndexName", "date"]]
        .dropna()
        .groupby("IndexName", as_index=False)["date"]
        .agg(start_date="min", end_date="max")
        .sort_values(["start_date", "IndexName"])
    )
    df_ranges["start_date"] = pd.to_datetime(df_ranges["start_date"])
    df_ranges["end_date"] = pd.to_datetime(df_ranges["end_date"])
    domain_min = df_ranges["start_date"].min() - pd.Timedelta(days=domain_pad_days)
    domain_max = df_ranges["end_date"].max() + pd.Timedelta(days=domain_pad_days)

    base = alt.Chart(df_ranges).encode(
        y=alt.Y(
            "IndexName:N",
            sort="-x",
            title="Index",
            axis=alt.Axis(labelLimit=0),
        ),
        tooltip=[
            alt.Tooltip("IndexName:N", title="Index"),
            alt.Tooltip("start_date:T", title="Start"),
            alt.Tooltip("end_date:T", title="End"),
        ],
    )
    range_bar = base.mark_bar(
        color=coverage_color,
        size=10,
        cornerRadius=8,
        cornerRadiusEnd=8,
        opacity=0.9,
    ).encode(
        x=alt.X(
            "start_date:T",
            title="Date",
            axis=alt.Axis(format="%b %Y", labelAngle=0),
            scale=alt.Scale(domain=[domain_min, domain_max]),
        ),
        x2=alt.X2("end_date:T"),
    )
    start_handle = base.mark_circle(size=70, color=coverage_color, stroke="#111827", strokeWidth=1.2).encode(
        x="start_date:T"
    )
    end_handle = base.mark_circle(size=70, color=coverage_color, stroke="#111827", strokeWidth=1.2).encode(
        x="end_date:T"
    )
    coverage_chart = (
        alt.layer(range_bar, start_handle, end_handle)
        .properties(padding={"left": 40, "right": 40, "top": 14, "bottom": 14})
        .interactive()
    )

    # ---- Indices: Price (all Baltic indices) ----
    df_bdi = df_bdi[df_bdi["IndexName"].astype(str).str.strip().str.startswith("Baltic ", na=False)]
    df_plot = df_bdi[["date", "IndexName", "price"]].dropna()
    df_plot = df_plot.assign(date=pd.to_datetime(df_plot["date"]))

    price_chart = (
        alt.Chart(df_plot)
        .mark_line()
        .encode(
            x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %Y", labelAngle=0)),
            y=alt.Y("price:Q", title="Price"),
            color=alt.Color("IndexName:N", legend=alt.Legend(title="Index", labelLimit=0)),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("IndexName:N", title="Index"),
                alt.Tooltip("price:Q", title="Price"),
            ],
        )
    ).interactive()

    # ---- World Port Routes: PyDeck ----
    if df_ports.empty:
        ports_embed = "<p>No ports available.</p>"
    else:
        view_state = pdk.ViewState(
            latitude=float(df_ports["Latitude"].astype(float).mean()),
            longitude=float(df_ports["Longitude"].astype(float).mean()),
            zoom=1.2,
            pitch=0,
        )
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_ports,
            get_position="[Longitude, Latitude]",
            get_radius="port_size",
            radius_min_pixels=2,
            radius_max_pixels=30,
            get_fill_color="port_color_rgba",
            pickable=True,
            auto_highlight=True,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            tooltip={
                "html": "<b>Port:</b> {Main Port Name}<br/>"
                "<b>WPI:</b> {World Port Index Number}<br/>"
                "<b>Country:</b> {Country Code}<br/>"
                "<b>Harbor Size:</b> {Harbor Size Label}",
                "style": {"backgroundColor": "white", "color": "black"},
            },
        )
        ports_embed = _pydeck_iframe("ports_map", deck, height=700)

    # ---- Data Model: ERD ----
    erd_html_path = project_dir / "data_model/erd.html"
    if not erd_html_path.exists():
        generate_py = project_dir / "data_model/generate.py"
        if generate_py.exists():
            proc = subprocess.run(
                [sys.executable, str(generate_py)],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
            )
            # Best-effort: if generation fails, fall back to an error block below.
            if proc.returncode != 0:
                pass
    if erd_html_path.exists():
        erd_html = erd_html_path.read_text(encoding="utf-8")
        erd_embed = _iframe_srcdoc("erd", erd_html, height=900)
    else:
        generate_py = project_dir / "data_model/generate.py"
        erd_embed = (
            f"<p>Missing <code>{html.escape(str(erd_html_path))}</code>.</p>"
            f"<p>Generate it with: <code>{html.escape(sys.executable)} {html.escape(str(generate_py))}</code></p>"
        )

    # ---- Compose HTML ----
    html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Baltic Dry Index — Report</title>
    <style>
      :root {{
        --bg: #0b1220;
        --panel: #0f1a2d;
        --text: #e8eef9;
        --muted: #a7b3c7;
        --link: #67b7ff;
        --border: rgba(255,255,255,0.12);
      }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: var(--text);
        background: linear-gradient(180deg, var(--bg), #070b13);
      }}
      a {{ color: var(--link); text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      header {{
        padding: 28px 22px 18px;
        border-bottom: 1px solid var(--border);
        background: rgba(15, 26, 45, 0.7);
        backdrop-filter: blur(10px);
        position: sticky;
        top: 0;
        z-index: 5;
      }}
      header h1 {{
        margin: 0 0 8px;
        font-size: 20px;
        letter-spacing: 0.2px;
      }}
      header .meta {{
        color: var(--muted);
        font-size: 13px;
      }}
      main {{ max-width: 1200px; margin: 0 auto; padding: 18px 22px 60px; }}
      nav.toc {{
        background: rgba(15, 26, 45, 0.9);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px 16px;
        margin: 18px 0 26px;
      }}
      nav.toc a {{ display: inline-block; margin: 6px 14px 6px 0; font-size: 14px; }}
      section {{
        background: rgba(15, 26, 45, 0.85);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        margin: 18px 0;
      }}
      section h2 {{
        margin: 0 0 10px;
        font-size: 18px;
      }}
      section h3 {{
        margin: 14px 0 10px;
        font-size: 15px;
        color: var(--muted);
        font-weight: 600;
      }}
      .embed {{
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: #fff;
      }}
      .table-wrap {{
        overflow: auto;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: rgba(255,255,255,0.03);
      }}
      table.df {{
        border-collapse: collapse;
        width: 100%;
        min-width: 860px;
        font-size: 12px;
      }}
      table.df th, table.df td {{
        border-bottom: 1px solid rgba(255,255,255,0.10);
        padding: 8px 10px;
        vertical-align: top;
        color: var(--text);
        white-space: nowrap;
      }}
      table.df th {{
        position: sticky;
        top: 0;
        background: rgba(11, 18, 32, 0.96);
        z-index: 1;
        text-align: left;
        font-weight: 600;
      }}
      .note {{ color: var(--muted); font-size: 13px; margin-top: 6px; }}
    </style>
  </head>
  <body>
    <header>
      <h1>Baltic Dry Index — HTML Report</h1>
      <div class="meta">
        Generated from <code>{html.escape(str(project_dir / "streamlit/app.py"))}</code>
      </div>
    </header>
    <main>
      <nav class="toc">
        <strong>Contents:</strong>
        <a href="#indices">1. Indices</a>
        <a href="#ports">2. World Port Routes</a>
        <a href="#baltic_routes">3. Baltic Routes</a>
        <a href="#vessels">4. Vessels</a>
        <a href="#data_model">5. Data Model</a>
      </nav>

      <section id="indices">
        <h2>1. Indices</h2>
        <h3>Coverage</h3>
        {_altair_iframe("indices_coverage", coverage_chart, height=520)}
        <h3>Price (All Baltic Indices)</h3>
        {_altair_iframe("indices_price", price_chart, height=520)}
        <div class="note">Tip: use the legend to toggle series; scroll/drag to zoom.</div>
      </section>

      <section id="ports">
        <h2>2. World Port Routes</h2>
        {ports_embed}
        <div class="note">Basemap tiles load from an online source; points/tooltip remain interactive.</div>
      </section>

      <section id="baltic_routes">
        <h2>3. Baltic Routes</h2>
        <div class="table-wrap">{_df_table(df_baltic_routes)}</div>
      </section>

      <section id="vessels">
        <h2>4. Vessels</h2>
        <div class="table-wrap">{_df_table(df_vessels)}</div>
      </section>

      <section id="data_model">
        <h2>5. Data Model</h2>
        {erd_embed}
      </section>
    </main>
  </body>
</html>
"""

    out_path.write_text(html_doc, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the Baltic Streamlit app to a standalone HTML report.")
    parser.add_argument(
        "--out",
        default="freight_derivatives_report.html",
        help="Output HTML path (default: freight_derivatives_report.html in current directory).",
    )
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    build_report(out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
