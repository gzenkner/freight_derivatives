import pandas as pd
import json
from pathlib import Path
from typing import Union

def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def load_bdi(baltic_indices_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load index time series.

    Backwards-compatible with older folder layouts that used `datasets/baltic_indices/...`.
    """
    baltic_indices_path = Path(baltic_indices_path)

    if baltic_indices_path.is_dir():
        # New layout: `datasets/indices/json`
        if (baltic_indices_path / "json").is_dir():
            baltic_indices_path = baltic_indices_path / "json"
        # Legacy layout(s)
        elif (baltic_indices_path / "datasets/baltic_indices/json").is_dir():
            baltic_indices_path = baltic_indices_path / "datasets/baltic_indices/json"
        elif (baltic_indices_path / "datasets/indices/json").is_dir():
            baltic_indices_path = baltic_indices_path / "datasets/indices/json"

    if baltic_indices_path.is_dir():
        complete_paths = sorted(baltic_indices_path.glob("*.json"))
        df_bdi = pd.DataFrame()

        for p in complete_paths:
            with open(p, "r", encoding="utf-8") as file:
                data = json.load(file).get("data", [])
            df = pd.json_normalize(data)
            df["SourceFile"] = p.name
            df_bdi = pd.concat([df_bdi, df], ignore_index=True)

        if df_bdi.empty:
            return df_bdi

        df_bdi["date"] = pd.to_datetime(df_bdi["Date"], errors="coerce").dt.date
        df_bdi["price"] = _to_float(df_bdi["Close"])
        df_bdi["open"] = _to_float(df_bdi["Open"])
        df_bdi["high"] = _to_float(df_bdi["High"])
        df_bdi["low"] = _to_float(df_bdi["Low"])
        df_bdi["change"] = _to_float(df_bdi["Change"])
        df_bdi["turnover"] = _to_float(df_bdi["Turnover"])

        df_bdi = df_bdi.dropna(subset=["date"]).sort_values(["IndexName", "date"])
        return df_bdi

    # Fallback: allow a CSV path.
    df_bdi = pd.read_csv(baltic_indices_path)
    if "Date" in df_bdi.columns:
        df_bdi["date"] = pd.to_datetime(df_bdi["Date"], errors="coerce").dt.date
    if "Close" in df_bdi.columns and "price" not in df_bdi.columns:
        df_bdi["price"] = _to_float(df_bdi["Close"])
    df_bdi = df_bdi.dropna(subset=["date"]).sort_values("date")
    return df_bdi


def load_vessels(vessels_path: str) -> pd.DataFrame:
    return pd.read_csv(vessels_path)


def load_ports(world_ports_path: str) -> pd.DataFrame:
    df_ports = pd.read_csv(world_ports_path)

    df_ports = df_ports[
        [
            "Latitude",
            "Longitude",
            "World Port Index Number",
            "Country Code",
            "Harbor Size",
            "Main Port Name",
        ]
    ]

    df_ports["port_size"] = df_ports["Harbor Size"].replace(
        {
            "Very Small": 2000,
            "Small": 4000,
            "Medium": 7000,
            "Large": 12000,
            " ": 2000,
            "": 2000,
        }
    ).astype(float)

    harbor_size_colors = {
        "Very Small": "#6a3d9a",
        "Small": "#33a02c",
        "Medium": "#ff7f00",
        "Large": "#e31a1c",
    }
    df_ports["port_color"] = (
        df_ports["Harbor Size"].astype(str).str.strip().map(harbor_size_colors).fillna("#cccccc")
    )
    df_ports["port_color_rgba"] = df_ports["port_color"].apply(
        lambda c: (
            [int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 160]
            if isinstance(c, str) and c.startswith("#") and len(c) == 7
            else [204, 204, 204, 160]
        )
    )

    df_ports["Harbor Size Label"] = df_ports["Harbor Size"].astype(str).str.strip()
    df_ports.loc[
        ~df_ports["Harbor Size Label"].isin(["Large", "Medium", "Small", "Very Small"]),
        "Harbor Size Label",
    ] = "Unknown"

    return df_ports

def load_indices(indices_path: str) -> pd.DataFrame:
    df_indices = pd.read_csv(indices_path)
    df_indices = df_indices[['index_code', 'index_name', 'market', 'frequency', 'description']]
    return df_indices 


def load_baltic_routes(baltic_routes_path: str) -> pd.DataFrame:
    df_baltic_routes = pd.read_csv(baltic_routes_path)
    return df_baltic_routes

def load_exchanges(exchanges_path: str) -> pd.DataFrame:
    df_exchanges = pd.read_csv(exchanges_path)
    return df_exchanges


def load_dataframes(
    baltic_indices_path: Union[str, Path],
    vessels_path: str,
    world_ports_path: str,
    indices_path: str,
    baltic_routes_path: str,
    exchanges_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_bdi = load_bdi(baltic_indices_path)
    df_vessels = load_vessels(vessels_path)
    df_ports = load_ports(world_ports_path)
    df_indices = load_indices(indices_path)
    df_baltic_routes = load_baltic_routes(baltic_routes_path)
    df_exchanges = load_exchanges(exchanges_path)

    return df_bdi, df_vessels, df_ports, df_indices, df_baltic_routes, df_exchanges


