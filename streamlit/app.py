from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from dataframes import load_dataframes


st.set_page_config(page_title="Freight Derivatives", layout="wide")
st.title("Freight Derivatives")

PROJECT_DIR = Path(__file__).resolve().parents[1]


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _clean_str(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].astype(str).fillna("").str.strip()
    return out


def _ensure_date(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "date" not in out.columns and "Date" in out.columns:
        out["date"] = pd.to_datetime(out["Date"], errors="coerce").dt.date
    return out


def _show_df(df: pd.DataFrame, **kwargs) -> None:
    """
    Display helper: show missing values as the literal string `null` (instead of NaN).
    Keeps computations on the original dataframe; only formatting changes.
    """
    try:
        st.dataframe(df.style.format(na_rep="null"), **kwargs)
    except Exception:
        st.dataframe(df.fillna("null"), **kwargs)


indices_json_path = PROJECT_DIR / "datasets/indices/json"
vessels_path = PROJECT_DIR / "datasets/exchange_reference/vessel_types.csv"
world_ports_path = PROJECT_DIR / "datasets/exchange_reference/ports_world_port_index.csv"
indices_path = PROJECT_DIR / "datasets/exchange_reference/indices.csv"
routes_path = PROJECT_DIR / "datasets/exchange_reference/routes.csv"
ffas_path = PROJECT_DIR / "datasets/ffas/ffa_instruments.csv"

df_ts, df_vessels, df_ports, df_indices, df_routes, df_ffas = load_dataframes(
    indices_json_path,
    str(vessels_path),
    str(world_ports_path),
    str(indices_path),
    str(routes_path),
    str(ffas_path),
)
df_ts = _ensure_date(df_ts)

df_index_components = _read_csv(PROJECT_DIR / "datasets/exchange_reference/index_components.csv")
df_index_catalog = _read_csv(PROJECT_DIR / "datasets/indices/index_catalog.csv")
df_ffa_brokers = _read_csv(PROJECT_DIR / "datasets/exchange_reference/ffa_brokers.csv")


def page_start_here() -> None:
    st.header("Start here")
    st.markdown(
        """
This app is for **beginners** learning the Baltic-style freight market.

**Three objects matter:**
1) **Routes**: the *assessed* freight rates for a specific lane / trip template (e.g. `S1B`, `C5`, `TC1`).  
2) **Indices**: published aggregates computed from routes (e.g. `BDI` is a composite of sub-indices).  
3) **FFAs / freight derivatives**: tradable contracts that **settle** to a route, an index, or a basket average.

Suggested learning path: **Routes → Indices → FFAs**.

**Mental model (one sentence):**  
*Brokers assess routes → baskets/indices are computed → derivatives settle to those published numbers.*

Quick examples:
- A **route** like `S1B` is one assessed Supramax trip definition.
- An **index** like `BSI` is a roll-up of several Supramax routes.
- An **FFA contract** might settle to a **route** (`C5`), an **index** (`BDI`), or a **basket** (`C5TC (182)`).
"""
    )

    df_r = _clean_str(df_routes, ["route_code", "market", "segment"])
    df_i = _clean_str(df_indices, ["index_code", "market"])
    df_f = _clean_str(df_ffas, ["venue", "underlying_kind", "underlying_code", "product_type"])
    df_t = _clean_str(df_ts, ["IndexName"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Routes (ref)", int(len(df_r)))
    c2.metric("Indices (ref)", int(len(df_i)))
    c3.metric("Cleared contracts", int(len(df_f)))
    c4.metric("Index TS series", int(df_t["IndexName"].nunique()) if not df_t.empty else 0)

    with st.expander("Glossary", expanded=False):
        st.markdown(
            """
| Term | Meaning | Example |
|---|---|---|
| Route assessment | A single assessed lane/trip | `S1B`, `C3`, `TC1` |
| Basket average | Avg of several routes | `C5TC (182)`, `S11TC`, `H7TC` |
| Index | Published aggregate | `BDI`, `BSI`, `BCTI` |
| FFA / derivative | Tradable contract that settles to an underlying | EEX `C5TM`, CME-cleared `TC2` |
"""
        )

    with st.expander("Primary sources", expanded=False):
        st.markdown(
            """
- Indices: https://www.balticexchange.com/en/data-services/market-information0/indices.html  
- Routes: https://www.balticexchange.com/en/data-services/routes.html  
- Baltic clearing list: https://www.balticexchange.com/en/data-services/freight-derivatives-/Clearing.html  
- EEX Dry Freight: https://www.eex.com/en/global-commodities/dry-freight  
"""
        )


def page_indices() -> None:
    st.header("Indices")
    st.markdown(
        """
Indices are **published aggregates**. Routes are the **inputs**.

Start with `Baltic Dry Index` (BDI) if you want a single headline series.
"""
    )

    include_non_baltic = st.checkbox("Include non-Baltic series", value=False)

    df = _clean_str(df_ts, ["IndexName"])
    if not include_non_baltic:
        df = df[df["IndexName"].str.startswith("Baltic ", na=False)]

    index_names = sorted({n for n in df["IndexName"].tolist() if n})
    if not index_names:
        st.info("No index time series found.")
        return

    default = ["Baltic Dry Index"] if "Baltic Dry Index" in index_names else index_names[:1]
    selected = st.multiselect("Pick indices", index_names, default=default)
    if not selected:
        return

    df_view = df[df["IndexName"].isin(set(selected))]

    st.subheader("Coverage")
    df_ranges = (
        df_view[["IndexName", "date"]]
        .dropna()
        .groupby("IndexName", as_index=False)["date"]
        .agg(start_date="min", end_date="max")
        .sort_values(["start_date", "IndexName"])
    )
    df_ranges["start_date"] = pd.to_datetime(df_ranges["start_date"])
    df_ranges["end_date"] = pd.to_datetime(df_ranges["end_date"])
    if df_ranges.empty:
        st.info("No dates for the selection.")
        return

    domain_min = df_ranges["start_date"].min() - pd.Timedelta(days=180)
    domain_max = df_ranges["end_date"].max() + pd.Timedelta(days=180)
    coverage = (
        alt.Chart(df_ranges)
        .mark_bar(color="#9CA3AF", size=10, cornerRadius=8, cornerRadiusEnd=8)
        .encode(
            y=alt.Y("IndexName:N", sort=selected, title="", axis=alt.Axis(labelLimit=0)),
            x=alt.X(
                "start_date:T",
                title="",
                axis=alt.Axis(format="%b %Y", labelAngle=0),
                scale=alt.Scale(domain=[domain_min, domain_max]),
            ),
            x2=alt.X2("end_date:T"),
            tooltip=[
                alt.Tooltip("IndexName:N", title="Index"),
                alt.Tooltip("start_date:T", title="Start"),
                alt.Tooltip("end_date:T", title="End"),
            ],
        )
    )
    st.altair_chart(coverage.interactive(), use_container_width=True)

    st.subheader("Price")
    df_plot = df_view[["date", "IndexName", "price"]].dropna()
    if df_plot.empty:
        st.info("No values for the selection.")
        return

    df_plot = df_plot.assign(date=pd.to_datetime(df_plot["date"]))
    line = (
        alt.Chart(df_plot)
        .mark_line()
        .encode(
            x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %Y", labelAngle=0)),
            y=alt.Y("price:Q", title="Value"),
            color=alt.Color("IndexName:N", legend=alt.Legend(title="", labelLimit=0)),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("IndexName:N", title="Index"),
                alt.Tooltip("price:Q", title="Value"),
            ],
        )
    )
    st.altair_chart(line.interactive(), use_container_width=True)

    df_inds = _clean_str(df_indices, ["index_code", "index_name"])
    name_to_code = {r["index_name"]: r["index_code"] for _, r in df_inds.iterrows() if r["index_name"] and r["index_code"]}
    df_r = _clean_str(df_routes, ["route_code", "short_description"])
    route_desc = df_r.set_index("route_code")["short_description"].to_dict() if not df_r.empty else {}

    with st.expander("Methodology (how it’s calculated)", expanded=False):
        df_cat = _clean_str(df_index_catalog, ["index_name", "index_short_name", "calculation", "detail_url"])
        for index_name in selected:
            code = name_to_code.get(index_name, "")
            row = df_cat[df_cat["index_name"] == index_name].head(1)
            st.markdown(f"**{index_name} ({code})**" if code else f"**{index_name}**")
            if row.empty or not row["calculation"].iloc[0]:
                st.write("No formula captured locally yet.")
            else:
                st.code(row["calculation"].iloc[0], language="text")
                if row["detail_url"].iloc[0]:
                    st.caption(row["detail_url"].iloc[0])

    with st.expander("Components (what routes feed it)", expanded=False):
        dfc = _clean_str(df_index_components, ["index_code", "component_code", "component_type", "weight"])
        for index_name in selected:
            code = name_to_code.get(index_name, "")
            st.markdown(f"**{index_name} ({code})**" if code else f"**{index_name}**")
            if not code or dfc.empty:
                st.write("No components available.")
                continue
            rows = dfc[dfc["index_code"] == code].copy()
            if rows.empty:
                st.write("No components captured.")
                continue
            rows = rows.sort_values(["component_type", "component_code"])
            for _, r in rows.iterrows():
                comp = r["component_code"]
                ctype = r["component_type"]
                w = r.get("weight", "")
                extra = route_desc.get(comp, "") if str(ctype).upper() == "ROUTE" else ""
                suffix = f" — {extra}" if extra else ""
                st.write(f"- `{comp}` ({ctype})" + (f", w={w}" if w else "") + suffix)


def page_ffas() -> None:
    st.header("FFAs / Freight derivatives")
    st.markdown(
        """
For beginners, the key idea is:

**A contract settles to an underlying** (route / index / basket).

Use the **Underlyings** view to see what’s actually being settled.
"""
    )

    df = _clean_str(
        df_ffas,
        [
            "venue",
            "exchange_name",
            "contract_code",
            "contract_name",
            "instrument_code",
            "product_type",
            "contract_variant",
            "underlying_kind",
            "underlying_code",
            "market",
            "segment",
            "unit",
            "currency",
            "notes",
            "source_url",
            "data_rows",
        ],
    )
    if df.empty:
        st.info("No contracts loaded.")
        return

    df["has_timeseries"] = (df["underlying_kind"].str.lower() == "index") & (df["data_rows"] != "")
    df["exchange_display"] = df["exchange_name"].where(df["exchange_name"] != "", df["venue"])

    view_mode = st.radio("View", ["Underlyings", "Contracts"], horizontal=True)

    f1, f2, f3, f4 = st.columns([1.0, 1.1, 1.2, 1.7])
    with f1:
        venues = sorted([v for v in df["venue"].unique().tolist() if v])
        venue_choice = st.selectbox("Venue", ["All"] + venues, index=0)
    with f2:
        markets = sorted([m for m in df["market"].unique().tolist() if m])
        market_choice = st.selectbox("Market", ["All"] + markets, index=0)
    with f3:
        include_options = st.checkbox("Include options", value=True)
    with f4:
        q = st.text_input("Search", value="")

    view = df
    if venue_choice != "All":
        view = view[view["venue"] == venue_choice]
    if market_choice != "All":
        view = view[view["market"] == market_choice]
    if not include_options:
        view = view[view["product_type"] != "OPTION"]
    if q.strip():
        needle = q.strip().lower()
        hay = (
            view["contract_code"]
            + " "
            + view["contract_name"]
            + " "
            + view["underlying_code"]
            + " "
            + view["notes"]
        ).str.lower()
        view = view[hay.str.contains(needle, na=False)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", int(len(view)))
    c2.metric("Underlyings", int(view["underlying_code"].replace("", pd.NA).dropna().nunique()))
    c3.metric("Options", int((view["product_type"] == "OPTION").sum()))
    c4.metric("Local index TS", int(view["has_timeseries"].sum()))

    if view_mode == "Underlyings":
        u = (
            view.groupby(["underlying_code", "underlying_kind", "market", "segment"], dropna=False)
            .agg(
                venues=("venue", lambda s: ", ".join(sorted({v for v in s.tolist() if v}))),
                contracts=("contract_code", "count"),
                options=("product_type", lambda s: int((s == "OPTION").sum())),
                local_index_ts=("has_timeseries", "sum"),
            )
            .reset_index()
            .sort_values(["market", "segment", "underlying_kind", "underlying_code"])
        )
        _show_df(u, use_container_width=True, hide_index=True)
    else:
        cols = [
            "venue",
            "exchange_display",
            "contract_code",
            "contract_name",
            "product_type",
            "contract_variant",
            "underlying_kind",
            "underlying_code",
            "market",
            "segment",
            "unit",
            "currency",
            "notes",
            "source_url",
        ]
        _show_df(
            view.reindex(columns=[c for c in cols if c in view.columns]).sort_values(
                ["venue", "market", "segment", "underlying_code", "contract_code"], na_position="last"
            ),
            use_container_width=True,
            hide_index=True,
        )

    if not df_ffa_brokers.empty and "broker_name" in df_ffa_brokers.columns:
        dfb = _clean_str(df_ffa_brokers, ["market", "segment", "broker_name", "website_url"])
        dfb = dfb[(dfb["market"].str.upper() == "DRY") & (dfb["segment"] == "FORWARD_ASSESSMENTS")]
        if not dfb.empty:
            with st.expander("Baltic-approved Forward Assessments brokers (Dry)", expanded=False):
                lines = []
                for _, r in dfb.sort_values(["broker_name"]).iterrows():
                    name = r["broker_name"]
                    url = r["website_url"]
                    lines.append(f"- [{name}]({url})" if url else f"- {name}")
                st.markdown("\n".join(lines))


def page_routes() -> None:
    st.header("Routes")
    st.markdown(
        """
Routes are the **building blocks** of indices and many freight derivatives.

You can use the “Explain a route” section at the bottom to see which indices and cleared contracts refer to it.
"""
    )

    df = _clean_str(
        df_routes,
        ["route_code", "short_description", "market", "segment", "port_of_embarkment", "port_of_arrival", "source_url"],
    )
    if df.empty:
        st.info("No routes loaded.")
        return
    df["has_ports"] = (df["port_of_embarkment"] != "") | (df["port_of_arrival"] != "")

    f1, f2, f3, f4 = st.columns([1.1, 1.1, 1.1, 1.7])
    with f1:
        markets = sorted([m for m in df["market"].unique().tolist() if m])
        market_choice = st.selectbox("Market", ["All"] + markets, index=0)
    with f2:
        segments = sorted([s for s in df["segment"].unique().tolist() if s])
        segment_choice = st.selectbox("Segment", ["All"] + segments, index=0)
    with f3:
        only_ports = st.checkbox("Only mapped ports", value=False)
    with f4:
        q = st.text_input("Search (code / description / port)", value="")

    view = df
    if market_choice != "All":
        view = view[view["market"] == market_choice]
    if segment_choice != "All":
        view = view[view["segment"] == segment_choice]
    if only_ports:
        view = view[view["has_ports"]]
    if q.strip():
        needle = q.strip().lower()
        hay = (
            view["route_code"]
            + " "
            + view["short_description"]
            + " "
            + view["port_of_embarkment"]
            + " "
            + view["port_of_arrival"]
        ).str.lower()
        view = view[hay.str.contains(needle, na=False)]

    m1, m2, m3 = st.columns(3)
    m1.metric("Routes", int(len(view)))
    m2.metric("With ports mapped", int(view["has_ports"].sum()))
    m3.metric("Segments", int(view["segment"].nunique()))

    cols = [
        "route_code",
        "short_description",
        "market",
        "segment",
        "port_of_embarkment",
        "port_of_arrival",
        "source_url",
    ]
    _show_df(
        view.reindex(columns=[c for c in cols if c in view.columns]).sort_values(["market", "segment", "route_code"]),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Explain a route")
    route_codes = sorted([c for c in view["route_code"].replace("", pd.NA).dropna().unique().tolist()])
    if not route_codes:
        return

    picked = st.selectbox("Route code", route_codes, index=0)
    row = df[df["route_code"] == picked].head(1)
    if not row.empty:
        r = row.iloc[0].to_dict()
        st.write(f"**{picked}** — {r.get('short_description','')}")
        if r.get("port_of_embarkment") or r.get("port_of_arrival"):
            st.caption(f"Ports (best effort): {r.get('port_of_embarkment') or '—'} → {r.get('port_of_arrival') or '—'}")
        if r.get("source_url"):
            st.caption(r["source_url"])

    dfc = _clean_str(df_index_components, ["index_code", "component_code", "component_type"])
    df_i = _clean_str(df_indices, ["index_code", "index_name"])
    code_to_name = {r["index_code"]: r["index_name"] for _, r in df_i.iterrows() if r["index_code"] and r["index_name"]}

    alias = {picked}
    if not picked.endswith("_63") and (picked + "_63") in set(df["route_code"].tolist()):
        alias.add(picked + "_63")

    idx = dfc[(dfc["component_type"].str.upper() == "ROUTE") & (dfc["component_code"].isin(alias))]
    idx_codes = sorted({c for c in idx["index_code"].tolist() if c})
    with st.expander("Indices that use this route", expanded=False):
        if not idx_codes:
            st.write("None captured in `index_components.csv`.")
        else:
            for c in idx_codes:
                st.write(f"- `{c}` — {code_to_name.get(c, '')}")

    dff = _clean_str(df_ffas, ["venue", "contract_code", "contract_name", "underlying_kind", "underlying_code", "product_type", "contract_variant", "source_url"])
    rel = dff[(dff["underlying_kind"].str.lower() == "route") & (dff["underlying_code"].isin(alias))]
    with st.expander("Cleared contracts that settle to this route", expanded=False):
        if rel.empty:
            st.write("None found in `ffa_instruments.csv`.")
        else:
            cols = ["venue", "contract_code", "contract_name", "product_type", "contract_variant", "source_url"]
            _show_df(
                rel.reindex(columns=[c for c in cols if c in rel.columns]).sort_values(["venue", "contract_code"]),
                use_container_width=True,
                hide_index=True,
            )


def page_reference() -> None:
    st.header("Reference")
    tabs = st.tabs(["Ports (World Port Index)", "Vessels"])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns([1.3, 1.6, 1.4, 1.7])
        with c1:
            selected_sizes = st.multiselect(
                "Harbor Size",
                ["Large", "Medium", "Small", "Very Small", "Unknown"],
                default=["Large"],
            )
        with c2:
            country_codes = sorted(
                {
                    c
                    for c in df_ports.get("Country Code", pd.Series(dtype=str))
                    .astype(str)
                    .fillna("")
                    .str.strip()
                    .tolist()
                    if c and c != "nan"
                }
            )
            selected_countries = st.multiselect("Country Code", country_codes, default=[])
        with c3:
            map_points = st.slider("Map points", min_value=200, max_value=5000, value=1500, step=100)
        with c4:
            q = st.text_input("Search (port / country / WPI)", value="")

        view = df_ports[df_ports["Harbor Size Label"].isin(selected_sizes)]
        if selected_countries:
            view = view[view["Country Code"].astype(str).str.strip().isin(set(selected_countries))]
        if q.strip():
            needle = q.strip().lower()
            hay = (
                view["Main Port Name"].astype(str)
                + " "
                + view["Country Code"].astype(str)
                + " "
                + view["World Port Index Number"].astype(str)
            ).str.lower()
            view = view[hay.str.contains(needle, na=False)]

        if view.empty:
            st.info("No ports match the filters.")
        else:
            df_map = view.sample(n=min(len(view), map_points), random_state=7) if len(view) > map_points else view
            view_state = pdk.ViewState(
                latitude=float(df_map["Latitude"].astype(float).mean()),
                longitude=float(df_map["Longitude"].astype(float).mean()),
                zoom=1.2,
                pitch=0,
            )
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position="[Longitude, Latitude]",
                get_radius="port_size",
                radius_min_pixels=2,
                radius_max_pixels=30,
                get_fill_color="port_color_rgba",
                pickable=True,
                auto_highlight=True,
            )
            st.pydeck_chart(
                pdk.Deck(
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
                ),
                use_container_width=True,
            )

            with st.expander("Port table", expanded=False):
                cols = [
                    "Main Port Name",
                    "Country Code",
                    "World Port Index Number",
                    "Harbor Size Label",
                    "Latitude",
                    "Longitude",
                ]
                _show_df(
                    view.reindex(columns=[c for c in cols if c in view.columns]).sort_values(
                        ["Country Code", "Main Port Name"], na_position="last"
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    with tabs[1]:
        dfv = _clean_str(df_vessels, ["vessel_type", "market", "segment", "notes", "source_url"])
        f1, f2, f3 = st.columns([1.2, 1.2, 2.0])
        with f1:
            markets = sorted([m for m in dfv["market"].unique().tolist() if m])
            market_choice = st.selectbox("Market", ["All"] + markets, index=0, key="v_market")
        with f2:
            segments = sorted([s for s in dfv["segment"].unique().tolist() if s])
            segment_choice = st.selectbox("Segment", ["All"] + segments, index=0, key="v_segment")
        with f3:
            q = st.text_input("Search (type / notes)", value="", key="v_search")

        view = dfv
        if market_choice != "All":
            view = view[view["market"] == market_choice]
        if segment_choice != "All":
            view = view[view["segment"] == segment_choice]
        if q.strip():
            needle = q.strip().lower()
            hay = (view["vessel_type"] + " " + view["notes"]).str.lower()
            view = view[hay.str.contains(needle, na=False)]

        cols = [
            "vessel_type",
            "market",
            "segment",
            "dwt_mt",
            "max_age_years",
            "loa_m",
            "beam_m",
            "tpc",
            "grain_cbm",
            "bale_cbm",
            "notes",
            "source_url",
        ]
        _show_df(
            view.reindex(columns=[c for c in cols if c in view.columns]).sort_values(
                ["market", "segment", "vessel_type"], na_position="last"
            ),
            use_container_width=True,
            hide_index=True,
        )


def page_data_model() -> None:
    st.header("Data model")
    choice = st.radio("Graph", ["Indices", "FFAs"], horizontal=True)
    target = "erd.html" if choice == "Indices" else "ffas_erd.html"
    erd_html_path = PROJECT_DIR / "data_model" / target
    if not erd_html_path.exists():
        generate_py = PROJECT_DIR / "data_model/generate.py"
        if generate_py.exists():
            with st.spinner("Generating data model…"):
                proc = subprocess.run(
                    [sys.executable, str(generate_py)],
                    cwd=str(PROJECT_DIR),
                    capture_output=True,
                    text=True,
                )
            if proc.returncode != 0:
                st.error(
                    f"Failed to generate `{erd_html_path}`.\n\n"
                    f"Command: `{sys.executable} {generate_py}`\n\n"
                    f"stdout:\n```\n{proc.stdout.strip()}\n```\n\n"
                    f"stderr:\n```\n{proc.stderr.strip()}\n```"
                )
        else:
            st.error(f"Missing `{erd_html_path}` and `{generate_py}`.")
    if not erd_html_path.exists():
        return
    st.components.v1.html(erd_html_path.read_text(encoding="utf-8"), height=900, scrolling=True)


page = st.sidebar.radio(
    "Navigate",
    ["Start here", "Routes", "Indices", "FFAs", "Reference", "Data model"],
    index=0,
)

if page == "Start here":
    page_start_here()
elif page == "Routes":
    page_routes()
elif page == "Indices":
    page_indices()
elif page == "FFAs":
    page_ffas()
elif page == "Reference":
    page_reference()
elif page == "Data model":
    page_data_model()
