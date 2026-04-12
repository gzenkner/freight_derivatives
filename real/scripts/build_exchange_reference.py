#!/usr/bin/env python3

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


SOURCE_URL = "https://www.balticexchange.com/en/data-services/market-information0/indices.html"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


@dataclass(frozen=True)
class Route:
    route_code: str
    short_description: str
    market: str
    segment: str


@dataclass(frozen=True)
class Index:
    index_code: str
    index_name: str
    market: str
    frequency: str
    description: str


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]  # .../freight_derivatives/real/scripts -> repo/freight_derivatives
    out_dir = repo_root / "datasets" / "exchange_reference"

    # -------------------------
    # Routes (as displayed on the Baltic Exchange indices page)
    # -------------------------
    routes: list[Route] = []

    # Dry bulk: Capesize
    routes += [
        Route("C2", "Tubarao to Rotterdam", "DRY_BULK", "CAPESIZE"),
        Route("C3", "Tubarao to Qingdao", "DRY_BULK", "CAPESIZE"),
        Route("C5", "West Australia to Qingdao", "DRY_BULK", "CAPESIZE"),
        Route("C7", "Bolivar to Rotterdam", "DRY_BULK", "CAPESIZE"),
        Route("C8_182", "Gibraltar/Hamburg transatlantic round voyage", "DRY_BULK", "CAPESIZE"),
        Route("C9_182", "Continent/Mediterranean trip China-Japan", "DRY_BULK", "CAPESIZE"),
        Route("C10_182", "China-Japan transpacific round voyage", "DRY_BULK", "CAPESIZE"),
        Route("C14_182", "China-Brazil round voyage", "DRY_BULK", "CAPESIZE"),
        Route("C16_182", "Revised backhaul", "DRY_BULK", "CAPESIZE"),
        Route("C17", "Saldanha Bay to Qingdao", "DRY_BULK", "CAPESIZE"),
    ]

    # Dry bulk: Panamax
    routes += [
        Route("P1A_82", "Skaw-Gib transatlantic round voyage", "DRY_BULK", "PANAMAX"),
        Route("P2A_82", "Skaw-Gib trip HK-S Korea incl Taiwan", "DRY_BULK", "PANAMAX"),
        Route("P3A_82", "Hong Kong-South Korea transpacific round voyage", "DRY_BULK", "PANAMAX"),
        Route("P4_82", "Hong Kong-South Korea trip to Skaw-Passero", "DRY_BULK", "PANAMAX"),
        Route("P5_82", "South China, one Indonesian round voyage", "DRY_BULK", "PANAMAX"),
        Route("P6_82", "Dely Singapore for one round voyage via Atlantic", "DRY_BULK", "PANAMAX"),
    ]

    # Dry bulk: Supramax
    routes += [
        Route("S1B", "Canakkale trip via Med or Bl Sea to China-South Korea", "DRY_BULK", "SUPRAMAX"),
        Route("S1C", "US Gulf trip to China-south Japan", "DRY_BULK", "SUPRAMAX"),
        Route("S2", "North China one Australian or Pacific round voyage", "DRY_BULK", "SUPRAMAX"),
        Route("S3", "North China trip to West Africa", "DRY_BULK", "SUPRAMAX"),
        Route("S4A", "US Gulf trip to Skaw-Passero", "DRY_BULK", "SUPRAMAX"),
        Route("S4B", "Skaw-Passero trip to US Gulf", "DRY_BULK", "SUPRAMAX"),
        Route("S5", "West Africa trip via east coast South America to north China", "DRY_BULK", "SUPRAMAX"),
        Route("S8", "South China trip via Indonesia to east coast India", "DRY_BULK", "SUPRAMAX"),
        Route("S9", "West Africa trip via east coast South America to Skaw-Passero", "DRY_BULK", "SUPRAMAX"),
        Route("S10", "South China trip via Indonesia to south China", "DRY_BULK", "SUPRAMAX"),
        Route("S15", "Indian Ocean trip via South Africa to the Far East", "DRY_BULK", "SUPRAMAX"),
    ]

    # Dry bulk: Handysize
    routes += [
        Route("HS1_38", "Skaw-Passero trip to Rio de Janeiro-Recalada", "DRY_BULK", "HANDYSIZE"),
        Route("HS2_38", "Skaw-Passero trip to Boston-Galveston", "DRY_BULK", "HANDYSIZE"),
        Route("HS3_38", "Rio de Janeiro-Recalada trip to Skaw-Passero", "DRY_BULK", "HANDYSIZE"),
        Route("HS4_38", "US Gulf trip via US Gulf or north coast South America to Skaw-Passero", "DRY_BULK", "HANDYSIZE"),
        Route("HS5_38", "South East Asia trip to Singapore-Japan", "DRY_BULK", "HANDYSIZE"),
        Route("HS6_38", "North China-South Korea-Japan trip to North China-South Korea-Japan", "DRY_BULK", "HANDYSIZE"),
        Route("HS7_38", "North China-South Korea-Japan trip to south east Asia", "DRY_BULK", "HANDYSIZE"),
    ]

    # Tankers: Clean
    routes += [
        Route("TC1", "Middle East Gulf to Japan (CPP, UNL, naphtha condensate)", "TANKERS", "CLEAN"),
        Route("TC2_37", "Continent to US Atlantic coast (CPP, UNL)", "TANKERS", "CLEAN"),
        Route("TC5", "Middle East Gulf to Japan (CPP, UNL, naphtha condensate)", "TANKERS", "CLEAN"),
        Route("TC6", "Algeria to European Mediterranean (CPP, UNL)", "TANKERS", "CLEAN"),
        Route("TC7", "Singapore to east coast Australia (CPP)", "TANKERS", "CLEAN"),
        Route("TC8", "Middle East Gulf to UK-Cont. (CPP, UNL)", "TANKERS", "CLEAN"),
        Route("TC9", "Baltic to UK-Cont. (CPP, UNL, ULSD)", "TANKERS", "CLEAN"),
        Route("TC10", "South Korea to NoPac west coast (CPP/UNL)", "TANKERS", "CLEAN"),
        Route("TC11", "South Korea to Singapore (CPP)", "TANKERS", "CLEAN"),
        Route("TC12", "Sikka (WCI) to Japan (naphtha)", "TANKERS", "CLEAN"),
        Route("TC14", "US Gulf to Continent (CPP, UNL, diesel)", "TANKERS", "CLEAN"),
        Route("TC15", "Med / Far East (naphtha)", "TANKERS", "CLEAN"),
        Route("TC16", "Amsterdam to offshore Lome (CPP)", "TANKERS", "CLEAN"),
        Route("TC17", "Middle East Gulf to East Africa", "TANKERS", "CLEAN"),
        Route("TC18", "US Gulf to Brazil", "TANKERS", "CLEAN"),
    ]

    # Tankers: Dirty
    routes += [
        Route("TD2", "Middle East Gulf to Singapore", "TANKERS", "DIRTY"),
        Route("TD3C", "Middle East Gulf to China", "TANKERS", "DIRTY"),
        Route("TD6", "Black Sea to Mediterranean", "TANKERS", "DIRTY"),
        Route("TD7", "North Sea to Continent", "TANKERS", "DIRTY"),
        Route("TD8", "Kuwait to Singapore (Crude/DPP heat 135F)", "TANKERS", "DIRTY"),
        Route("TD9", "Caribbean to US Gulf", "TANKERS", "DIRTY"),
        Route("TD12", "Amsterdam-Rotterdam-Antwerp to US Gulf", "TANKERS", "DIRTY"),
        Route("TD14", "South East Asia to east coast Australia", "TANKERS", "DIRTY"),
        Route("TD15", "West Africa to China", "TANKERS", "DIRTY"),
        Route("TD17", "Baltic to UK-Cont", "TANKERS", "DIRTY"),
        Route("TD18", "Baltic to UK-Cont", "TANKERS", "DIRTY"),
        Route("TD19", "Cross Mediterranean", "TANKERS", "DIRTY"),
        Route("TD20", "West Africa to UK-Continent", "TANKERS", "DIRTY"),
        Route("TD21", "Caribbean to US Gulf (50,000mt fuel oil)", "TANKERS", "DIRTY"),
        Route("TD22", "US Gulf to China (assessed in US $/lumpsum)", "TANKERS", "DIRTY"),
        Route("TD23", "Middle East Gulf to Mediterranean (Light Crude)", "TANKERS", "DIRTY"),
        Route("TD24", "Pacific Russia to China", "TANKERS", "DIRTY"),
        Route("TD25", "US Gulf to A-R-A", "TANKERS", "DIRTY"),
        # TD26 is referenced in the Aframax TCE basket on the indices page but is not listed in the table.
        Route("TD26", "", "TANKERS", "DIRTY"),
    ]

    # Gas
    routes += [
        Route("BLNG1", "Gladstone / Tokyo RV", "GAS", "LNG"),
        Route("BLNG2", "Sabine / UK Cont RV", "GAS", "LNG"),
        Route("BLNG3", "Sabine / Tokyo RV", "GAS", "LNG"),
        Route("BLPG1", "Middle East Gulf to Japan", "GAS", "LPG"),
        Route("BLPG2", "US Gulf to Continent", "GAS", "LPG"),
        Route("BLPG3", "US Gulf to Japan", "GAS", "LPG"),
    ]

    # Containers (Freightos Baltic Index lanes)
    routes += [
        Route("FBX00", "Global Container Index", "CONTAINERS", "FBX"),
        Route("FBX01", "China/East Asia to North America", "CONTAINERS", "FBX"),
        Route("FBX02", "North America West Coast to China/East Asia", "CONTAINERS", "FBX"),
        Route("FBX03", "China/East Asia to North America East Coast", "CONTAINERS", "FBX"),
        Route("FBX04", "North America East Coast to China/East Asia", "CONTAINERS", "FBX"),
        Route("FBX11", "China/East Asia to North Europe", "CONTAINERS", "FBX"),
        Route("FBX12", "North Europe to China/East Asia", "CONTAINERS", "FBX"),
        Route("FBX13", "China/East Asia to Mediterranean", "CONTAINERS", "FBX"),
        Route("FBX14", "Mediterranean to China/East Asia", "CONTAINERS", "FBX"),
        Route("FBX21", "North America East Coast to Europe", "CONTAINERS", "FBX"),
        Route("FBX22", "Europe to North America East Coast", "CONTAINERS", "FBX"),
        Route("FBX24", "Europe to South America East Coast", "CONTAINERS", "FBX"),
        Route("FBX26", "Europe to South America West Coast", "CONTAINERS", "FBX"),
    ]

    # Air freight (BAI)
    routes += [
        Route("BAI00", "Baltic Air Freight Index", "AIR_FREIGHT", "BAI"),
        Route("BAI20", "Frankfurt Outbound Index", "AIR_FREIGHT", "BAI"),
        Route("BAI30", "Hong Kong Outbound Index", "AIR_FREIGHT", "BAI"),
        Route("BAI40", "London Heathrow Outbound Index", "AIR_FREIGHT", "BAI"),
        Route("BAI50", "O'Hare Int'l, Chicago Outbound Index", "AIR_FREIGHT", "BAI"),
        Route("BAI60", "Singapore Outbound index", "AIR_FREIGHT", "BAI"),
        Route("BAI80", "Shanghai Pudong Outbound Index", "AIR_FREIGHT", "BAI"),
        Route("BAI22", "Frankfurt to North America", "AIR_FREIGHT", "BAI"),
        Route("BAI23", "Frankfurt to South East Asia", "AIR_FREIGHT", "BAI"),
        Route("BAI24", "Frankfurt to USA", "AIR_FREIGHT", "BAI"),
        Route("BAI25", "Frankfurt to China", "AIR_FREIGHT", "BAI"),
        Route("BAI31", "Hong Kong to Europe", "AIR_FREIGHT", "BAI"),
        Route("BAI32", "Hong Kong to North America", "AIR_FREIGHT", "BAI"),
        Route("BAI33", "Hong Kong to South East Asia", "AIR_FREIGHT", "BAI"),
        Route("BAI34", "Hong Kong to USA", "AIR_FREIGHT", "BAI"),
        Route("BAI42", "London Heathrow to North America", "AIR_FREIGHT", "BAI"),
        Route("BAI43", "London Heathrow to South East Asia", "AIR_FREIGHT", "BAI"),
        Route("BAI44", "London Heathrow to USA", "AIR_FREIGHT", "BAI"),
        Route("BAI51", "O'Hare Int'l, Chicago to Europe", "AIR_FREIGHT", "BAI"),
        Route("BAI53", "O'Hare Int'l, Chicago to South East Asia", "AIR_FREIGHT", "BAI"),
        Route("BAI63", "Singapore to South East Asia", "AIR_FREIGHT", "BAI"),
        Route("BAI81", "Shanghai Pudong to Europe", "AIR_FREIGHT", "BAI"),
        Route("BAI82", "Shanghai Pudong to North America", "AIR_FREIGHT", "BAI"),
        Route("BAI84", "Shanghai Pudong to USA", "AIR_FREIGHT", "BAI"),
    ]

    # -------------------------
    # Indices / tools
    # -------------------------
    indices: list[Index] = [
        Index(
            "BDI",
            "Baltic Dry Index",
            "DRY_BULK",
            "DAILY",
            "Composite of Capesize (40%), Panamax (30%), Supramax (30%) timecharter averages.",
        ),
        Index("BCI", "Baltic Capesize Index", "DRY_BULK", "DAILY", "Derived from 5TC weighted timecharter average."),
        Index("BPI", "Baltic Panamax Index", "DRY_BULK", "DAILY", "Derived from 5TC weighted timecharter average."),
        Index("BSI", "Baltic Supramax Index", "DRY_BULK", "DAILY", "Derived from S11TC weighted timecharter average."),
        Index("BHSI", "Baltic Handysize Index", "DRY_BULK", "DAILY", "Derived from 7TC weighted timecharter average."),
        Index("BCTI", "Baltic Clean Tanker Index", "TANKERS", "DAILY", "Average of selected clean routes multiplied by a constant."),
        Index("BDTI", "Baltic Dirty Tanker Index", "TANKERS", "DAILY", "Weighted sum of selected dirty routes multiplied by a constant."),
        Index("BLPG", "Baltic LPG Index", "GAS", "DAILY", "Average of BLPG1/2/3 (TCE) multiplied by 0.1."),
        Index("FBX00", "FBX Global Container Index", "CONTAINERS", "WEEKLY", "Headline index; weighted average of 12 underlying tradelanes."),
        Index("BAI00", "Baltic Air Freight Index", "AIR_FREIGHT", "WEEKLY", "Headline index; weighted average of 17 destination basket routes."),
        Index("BAI20", "Frankfurt Outbound Index", "AIR_FREIGHT", "WEEKLY", "Outbound index; weighted average of destination baskets from FRA."),
        Index("BAI30", "Hong Kong Outbound Index", "AIR_FREIGHT", "WEEKLY", "Outbound index; weighted average of destination baskets from HKG."),
        Index("BAI40", "London Heathrow Outbound Index", "AIR_FREIGHT", "WEEKLY", "Outbound index; weighted average of destination baskets from LHR."),
        Index("BAI50", "O'Hare (Chicago) Outbound Index", "AIR_FREIGHT", "WEEKLY", "Outbound index; weighted average of destination baskets from ORD."),
        Index("BAI60", "Singapore Outbound Index", "AIR_FREIGHT", "WEEKLY", "Outbound index; weighted average of destination baskets from SIN."),
        Index("BAI80", "Shanghai Pudong Outbound Index", "AIR_FREIGHT", "WEEKLY", "Outbound index; weighted average of destination baskets from PVG."),
        Index("DOPEX", "Baltic Operating Expenses Index - Dry", "INVESTOR_TOOLS", "QUARTERLY", "Daily vessel operating expenses for dry bulk classes."),
        Index("TOPEX", "Baltic Operating Expenses Index - Tanker", "INVESTOR_TOOLS", "QUARTERLY", "Daily vessel operating expenses for tanker classes."),
        Index("GOPEX", "Baltic Operating Expenses Index - Gas", "INVESTOR_TOOLS", "QUARTERLY", "Daily vessel operating expenses for LNG/LPG carriers."),
    ]

    # -------------------------
    # Index components (structured where the page provides explicit constituents)
    # -------------------------
    components: list[dict] = []

    def add_components(
        index_code: str,
        component_codes: list[str],
        component_type: str,
        weight: float | None,
        scale_factor: float | None,
        mode: str,
    ) -> None:
        for code in component_codes:
            components.append(
                {
                    "index_code": index_code,
                    "component_code": code,
                    "component_type": component_type,
                    "mode": mode,
                    "weight": "" if weight is None else weight,
                    "scale_factor": "" if scale_factor is None else scale_factor,
                    "source_url": SOURCE_URL,
                }
            )

    # BDI composite
    for code, w in [("BCI", 0.4), ("BPI", 0.3), ("BSI", 0.3)]:
        components.append(
            {
                "index_code": "BDI",
                "component_code": code,
                "component_type": "INDEX",
                "mode": "WEIGHTED_SUM",
                "weight": w,
                "scale_factor": 1.0,
                "source_url": SOURCE_URL,
            }
        )

    # BCI (5TC)
    bci_routes = ["C8_182", "C9_182", "C10_182", "C14_182", "C16_182"]
    bci_weights = [0.15, 0.125, 0.35, 0.25, 0.125]
    for code, w in zip(bci_routes, bci_weights):
        components.append(
            {
                "index_code": "BCI",
                "component_code": code,
                "component_type": "ROUTE",
                "mode": "WEIGHTED_SUM",
                "weight": w,
                "scale_factor": 0.11026,
                "source_url": SOURCE_URL,
            }
        )

    # BPI coefficients as displayed
    for code, coeff in [
        ("P1A_82", 0.027777775),
        ("P2A_82", 0.01111111),
        ("P3A_82", 0.027777775),
        ("P4_82", 0.01111111),
        ("P6_82", 0.03333333),
    ]:
        components.append(
            {
                "index_code": "BPI",
                "component_code": code,
                "component_type": "ROUTE",
                "mode": "COEFFICIENT_SUM",
                "weight": coeff,
                "scale_factor": "",
                "source_url": SOURCE_URL,
            }
        )

    # BSI weights + scale factor as displayed (note: route codes shown in formula include _63 suffix)
    for code, w in [
        ("S1B_63", 0.05),
        ("S1C_63", 0.05),
        ("S2_63", 0.15),
        ("S3_63", 0.15),
        ("S4A_63", 0.075),
        ("S4B_63", 0.10),
        ("S5_63", 0.05),
        ("S8_63", 0.10),
        ("S9_63", 0.075),
        ("S10_63", 0.10),
        ("S15_63", 0.10),
    ]:
        components.append(
            {
                "index_code": "BSI",
                "component_code": code,
                "component_type": "ROUTE",
                "mode": "WEIGHTED_SUM",
                "weight": w,
                "scale_factor": 0.079112625,
                "source_url": SOURCE_URL,
            }
        )

    # BHSI coefficients as displayed
    for code, coeff in [
        ("HS1_38", 0.006944444),
        ("HS2_38", 0.006944444),
        ("HS3_38", 0.006944444),
        ("HS4_38", 0.006944444),
        ("HS5_38", 0.011111111),
        ("HS6_38", 0.011111111),
        ("HS7_38", 0.005555556),
    ]:
        components.append(
            {
                "index_code": "BHSI",
                "component_code": code,
                "component_type": "ROUTE",
                "mode": "COEFFICIENT_SUM",
                "weight": coeff,
                "scale_factor": "",
                "source_url": SOURCE_URL,
            }
        )

    # BCTI: average * constant
    add_components(
        "BCTI",
        ["TC1", "TC2_37", "TC5", "TC6", "TC9", "TC16"],
        "ROUTE",
        1.0 / 6.0,
        4.54072288,
        "AVERAGE",
    )

    # BDTI: weighted sum * constant
    add_components(
        "BDTI",
        ["TD2", "TD3C", "TD6", "TD7", "TD8", "TD9", "TD14", "TD15", "TD18", "TD19", "TD20"],
        "ROUTE",
        1.0 / 11.0,
        8.415737054,
        "WEIGHTED_SUM",
    )

    # BLPG: average * 0.1
    add_components("BLPG", ["BLPG1", "BLPG2", "BLPG3"], "ROUTE", 1.0 / 3.0, 0.1, "AVERAGE")

    # FBX00 constituents (weights not specified on the indices page)
    add_components(
        "FBX00",
        ["FBX01", "FBX02", "FBX03", "FBX04", "FBX11", "FBX12", "FBX13", "FBX14", "FBX21", "FBX22", "FBX24", "FBX26"],
        "ROUTE",
        None,
        None,
        "WEIGHTED_AVG_UNSPECIFIED",
    )

    # BAI00 constituents (weights not specified on the indices page)
    add_components(
        "BAI00",
        ["BAI22", "BAI23", "BAI24", "BAI25", "BAI31", "BAI32", "BAI33", "BAI34", "BAI42", "BAI43", "BAI44", "BAI51", "BAI53", "BAI63", "BAI81", "BAI82", "BAI84"],
        "ROUTE",
        None,
        None,
        "WEIGHTED_AVG_UNSPECIFIED",
    )

    # Outbound indices: group membership only (weights not specified)
    for outbound, members in [
        ("BAI20", ["BAI22", "BAI23", "BAI24", "BAI25"]),
        ("BAI30", ["BAI31", "BAI32", "BAI33", "BAI34"]),
        ("BAI40", ["BAI42", "BAI43", "BAI44"]),
        ("BAI50", ["BAI51", "BAI53"]),
        ("BAI60", ["BAI63"]),
        ("BAI80", ["BAI81", "BAI82", "BAI84"]),
    ]:
        add_components(outbound, members, "ROUTE", None, None, "WEIGHTED_AVG_UNSPECIFIED")

    # OPEX indices: vessel class scope
    for idx, classes in [
        ("DOPEX", ["CAPESIZE", "PANAMAX", "SUPRAMAX", "HANDYSIZE"]),
        ("TOPEX", ["AFRAMAX", "MR_PRODUCT"]),
        ("GOPEX", ["LPG_CARRIER", "LNG_CARRIER"]),
    ]:
        for c in classes:
            components.append(
                {
                    "index_code": idx,
                    "component_code": c,
                    "component_type": "VESSEL_CLASS",
                    "mode": "SCOPE",
                    "weight": "",
                    "scale_factor": "",
                    "source_url": SOURCE_URL,
                }
            )

    # -------------------------
    # Vessel types/specs
    # -------------------------
    vessel_types: list[dict] = [
        {
            "vessel_type": "CAPESIZE_182_DWT",
            "market": "DRY_BULK",
            "segment": "CAPESIZE",
            "dwt_mt": 182000,
            "max_age_years": 10,
            "loa_m": 290,
            "beam_m": 45,
            "tpc": 121,
            "grain_cbm": 198000,
            "notes": "Timecharter vessel description for Capesize (non scrubber fitted).",
            "source_url": SOURCE_URL,
        },
        {
            "vessel_type": "PANAMAX_82500_DWT",
            "market": "DRY_BULK",
            "segment": "PANAMAX",
            "dwt_mt": 82500,
            "max_age_years": 12,
            "loa_m": 229,
            "beam_m": 32.25,
            "tpc": 70.5,
            "grain_cbm": 97000,
            "notes": "Timecharter vessel description for Panamax (non scrubber fitted).",
            "source_url": SOURCE_URL,
        },
        {
            "vessel_type": "SUPRAMAX_63500_DWT",
            "market": "DRY_BULK",
            "segment": "SUPRAMAX",
            "dwt_mt": 63500,
            "max_age_years": 15,
            "loa_m": 199.98,
            "beam_m": 32.24,
            "tpc": 61.4,
            "grain_cbm": 80500,
            "bale_cbm": 76200,
            "notes": "BSI63 vessel description (non-scrubber fitted); see page for full speeds/consumptions.",
            "source_url": SOURCE_URL,
        },
        {
            "vessel_type": "HANDYSIZE_38200_DWT",
            "market": "DRY_BULK",
            "segment": "HANDYSIZE",
            "dwt_mt": 38200,
            "max_age_years": 15,
            "loa_m": 180,
            "beam_m": 29.8,
            "tpc": 49,
            "grain_cbm": 47125,
            "bale_cbm": 45300,
            "notes": "Handysize 38 vessel description (non-scrubber fitted); geared bulk carrier.",
            "source_url": SOURCE_URL,
        },
        # Sale & Purchase: 5yo vessel types listed on the indices page
        {"vessel_type": "S&P_5Y_CAPESIZE_180000_DWT", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": 180000, "notes": "Weekly 5yo vessel price assessment.", "source_url": SOURCE_URL},
        {"vessel_type": "S&P_5Y_PANAMAX_82500_DWT", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": 82500, "notes": "Weekly 5yo vessel price assessment.", "source_url": SOURCE_URL},
        {"vessel_type": "S&P_5Y_SUPERHANDY_TESS58", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": "", "notes": "Weekly 5yo vessel price assessment (Tess 58 type).", "source_url": SOURCE_URL},
        {"vessel_type": "S&P_5Y_HANDYSIZE_38200_DWT", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": 38200, "notes": "Weekly 5yo vessel price assessment.", "source_url": SOURCE_URL},
        {"vessel_type": "S&P_5Y_VLCC_305000_DWT", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": 305000, "notes": "Weekly 5yo vessel price assessment.", "source_url": SOURCE_URL},
        {"vessel_type": "S&P_5Y_SUEZMAX_158000_DWT", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": 158000, "notes": "Weekly 5yo vessel price assessment.", "source_url": SOURCE_URL},
        {"vessel_type": "S&P_5Y_AFRAMAX_115000_DWT", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": 115000, "notes": "Weekly 5yo vessel price assessment.", "source_url": SOURCE_URL},
        {"vessel_type": "S&P_5Y_MR_PRODUCT_TANKER_51000_DWT", "market": "INVESTOR_TOOLS", "segment": "S&P", "dwt_mt": 51000, "notes": "Weekly 5yo vessel price assessment.", "source_url": SOURCE_URL},
    ]

    # -------------------------
    # Write outputs
    # -------------------------
    write_csv(
        out_dir / "routes.csv",
        [
            {
                "route_code": r.route_code,
                "short_description": r.short_description,
                "market": r.market,
                "segment": r.segment,
                "source_url": SOURCE_URL,
            }
            for r in routes
        ],
        ["route_code", "short_description", "market", "segment", "source_url"],
    )

    write_csv(
        out_dir / "indices.csv",
        [
            {
                "index_code": i.index_code,
                "index_name": i.index_name,
                "market": i.market,
                "frequency": i.frequency,
                "description": i.description,
                "source_url": SOURCE_URL,
            }
            for i in indices
        ],
        ["index_code", "index_name", "market", "frequency", "description", "source_url"],
    )

    write_csv(
        out_dir / "index_components.csv",
        components,
        ["index_code", "component_code", "component_type", "mode", "weight", "scale_factor", "source_url"],
    )

    write_csv(
        out_dir / "vessel_types.csv",
        vessel_types,
        [
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
        ],
    )

    readme = out_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Baltic Exchange indices reference (public)\n",
                "",
                "This folder contains reference tables derived from the public Baltic Exchange indices page:",
                f"- Source: {SOURCE_URL}",
                "",
                "Files:",
                "- `indices.csv`: index codes + descriptions + frequency",
                "- `routes.csv`: route codes / lane codes + short descriptions",
                "- `index_components.csv`: index constituents where explicitly provided on the page",
                "- `vessel_types.csv`: vessel class specs and investor-tool vessel types listed on the page",
                "",
                "Notes:",
                "- `TD26` is referenced in the Aframax TCE basket on the page but is not listed in the dirty tanker route table.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Wrote reference dataset -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
