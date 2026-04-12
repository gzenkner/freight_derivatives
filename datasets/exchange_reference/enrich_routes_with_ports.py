from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Port:
    name: str
    country: str
    wpi: str


def _norm(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_ports(path: Path) -> list[Port]:
    ports: list[Port] = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            name = (row.get("Main Port Name") or "").strip()
            if not name:
                continue
            ports.append(
                Port(
                    name=name,
                    country=(row.get("Country Code") or "").strip(),
                    wpi=(row.get("World Port Index Number") or "").strip(),
                )
            )
    return ports


def _is_matchable_token(token: str) -> bool:
    t = _norm(token)
    if not t:
        return False
    if len(t) <= 3:
        return False

    # Skip obvious regions / vague geography that tends to false-match ports.
    region_words = {
        "africa",
        "asia",
        "atlantic",
        "australia",
        "black sea",
        "caribbean",
        "china",
        "continent",
        "east coast",
        "europe",
        "far east",
        "gulf",
        "india",
        "japan",
        "mediterranean",
        "middle east",
        "north sea",
        "north america",
        "pacific",
        "russia",
        "singapore",  # allow (it is a port), but only if it's standalone
        "south america",
        "uk cont",
        "uk continent",
        "united states",
        "us gulf",
        "west africa",
    }

    # Allow "singapore" (port/city) but reject composite tokens like "south china".
    if t == "singapore":
        return True

    for w in region_words:
        if w in t:
            return False
    return True


def _match_port(token: str, ports: list[Port], *, preferred_country: str | None = None) -> Port | None:
    if not _is_matchable_token(token):
        return None

    t = _norm(token)
    if not t:
        return None

    exact = [p for p in ports if _norm(p.name) == t]
    if preferred_country:
        exact_pref = [p for p in exact if p.country.upper() == preferred_country.upper()]
        if len(exact_pref) == 1:
            return exact_pref[0]
    if len(exact) == 1:
        return exact[0]

    # substring match (word-based)
    cand = [p for p in ports if t in _norm(p.name)]
    if preferred_country:
        cand_pref = [p for p in cand if p.country.upper() == preferred_country.upper()]
        if len(cand_pref) == 1:
            return cand_pref[0]
        if len(cand_pref) > 1:
            cand = cand_pref

    if not cand:
        return None

    # Choose the shortest name containing the token (more specific than very long strings).
    cand.sort(key=lambda p: (len(p.name), p.name))
    return cand[0]


def _extract_endpoints(route_code: str, short_description: str) -> tuple[str, str]:
    desc = (short_description or "").strip()
    if not desc:
        return "", ""

    # Route-specific overrides where the Baltic uses a location label that maps to a specific port name.
    overrides: dict[str, tuple[str, str]] = {
        "C2": ("Tubarao", "Rotterdam"),
        "C3": ("Tubarao", "Qingdao"),
        "C5": ("Port Hedland", "Qingdao"),
        "C7": ("Puerto Bolivar", "Rotterdam"),
        "C8_182": ("Europa Point", "Hamburg"),
        "C9_182": ("Rotterdam", "Tokyo Ko"),
        "C10_182": ("Tokyo Ko", "Los Angeles"),
        "C14_182": ("Tubarao", "Qingdao"),
        "C17": ("Saldanha Bay", "Qingdao"),
        # Panamax route proxies (best-effort representative ports)
        "P1A_82": ("Skagen Havn", "Europa Point"),
        "P2A_82": ("Skagen Havn", "Hong Kong"),
        "P3A_82": ("Hong Kong", "Busan"),
        "P4_82": ("Hong Kong", "Skagen Havn"),
        "P5_82": ("Guangzhou", "Balikpapan"),
        "P6_82": ("Singapore", "Rotterdam"),
        # Clean tankers (best-effort representative ports)
        "TC1": ("Mina Al Ahmadi", "Tokyo Ko"),
        "TC2_37": ("Rotterdam", "New York City"),
        "TC2": ("Rotterdam", "New York City"),
        "TC5": ("Mina Al Ahmadi", "Tokyo Ko"),
        "TC6": ("Arzew", "Augusta"),
        "TC7": ("Singapore", "Newcastle"),
        "TC8": ("Mina Al Ahmadi", "Rotterdam"),
        "TC9": ("Gdansk", "Rotterdam"),
        "TC10": ("Busan", "Los Angeles"),
        "TC11": ("Busan", "Singapore"),
        "TC12": ("Sikka", "Tokyo Ko"),
        "TC14": ("Houston", "Rotterdam"),
        "TC15": ("Augusta", "Tokyo Ko"),
        "TC16": ("Amsterdam", "Lome"),
        "TC17": ("Mina Al Ahmadi", "Mombasa"),
        "TC18": ("Houston", "Rio De Janeiro"),
        "TC23": ("Antwerpen", "Rotterdam"),
        # Dirty tankers (best-effort representative ports)
        "TD2": ("Mina Al Ahmadi", "Singapore"),
        "TD3C": ("Mina Al Ahmadi", "Qingdao"),
        "TD6": ("Novorossiysk", "Augusta"),
        "TD7": ("Hound Point Terminal", "Rotterdam"),
        "TD8": ("Mina Al Ahmadi", "Singapore"),
        "TD9": ("Kingston", "Houston"),
        "TD12": ("Rotterdam", "Houston"),
        "TD14": ("Singapore", "Newcastle"),
        "TD15": ("Bonny", "Qingdao"),
        "TD17": ("Primorsk", "Rotterdam"),
        "TD18": ("Primorsk", "Rotterdam"),
        "TD21": ("Kingston", "Houston"),
        "TD23": ("Mina Al Ahmadi", "Augusta"),
        "TD24": ("Vladivostok", "Qingdao"),
        "TD20": ("Bonny", "Rotterdam"),
        "TD22": ("Houston", "Qingdao"),
        "TD25": ("Houston", "Rotterdam"),
        "TD28": ("Vancouver", "Qingdao"),
        "BLNG1": ("Gladstone", "Tokyo"),
        "BLNG2": ("Sabine Pass", "Rotterdam"),
        "BLNG3": ("Sabine Pass", "Tokyo"),
        "BLNG1g": ("Gladstone", "Tokyo"),
        "BLNG2g": ("Sabine Pass", "Rotterdam"),
        "BLNG3g": ("Sabine Pass", "Tokyo"),
        # Supramax / Handysize route proxies (best-effort representative ports)
        "S1B": ("Canakkale", "Busan"),
        "S1C": ("Houston", "Tokyo Ko"),
        "S2": ("Qingdao", "Newcastle"),
        "S3": ("Qingdao", "Bonny"),
        "S4A": ("Houston", "Rotterdam"),
        "S4B": ("Rotterdam", "Houston"),
        "S5": ("Bonny", "Qingdao"),
        "S8": ("Guangzhou", "Chennai (Madras)"),
        "S9": ("Bonny", "Rotterdam"),
        "S10": ("Guangzhou", "Guangzhou"),
        "S15": ("Durban", "Tokyo Ko"),
        "HS1_38": ("Rotterdam", "Rio De Janeiro"),
        "HS2_38": ("Rotterdam", "Galveston"),
        "HS3_38": ("Rio De Janeiro", "Rotterdam"),
        "HS4_38": ("Houston", "Rotterdam"),
        "HS5_38": ("Singapore", "Tokyo Ko"),
        "HS6_38": ("Qingdao", "Tokyo Ko"),
        "HS7_38": ("Qingdao", "Singapore"),
    }
    if route_code in overrides:
        return overrides[route_code]

    # Common patterns.
    if " to " in desc and desc.count(" to ") == 1:
        left, right = desc.split(" to ", 1)
        return left.strip(), right.strip()

    # Some LNG routes are written as "X / Y RV".
    if "/" in desc and "RV" in desc.upper():
        parts = [p.strip() for p in desc.split("/") if p.strip()]
        if len(parts) >= 2:
            left = parts[0]
            right = re.sub(r"\bRV\b", "", parts[1], flags=re.IGNORECASE).strip()
            return left, right

    return "", ""


def main() -> None:
    ports_path = PROJECT_DIR / "datasets/exchange_reference/ports_world_port_index.csv"
    routes_path = PROJECT_DIR / "datasets/exchange_reference/routes.csv"
    if not ports_path.exists():
        raise SystemExit(f"Missing ports dataset: {ports_path}")
    if not routes_path.exists():
        raise SystemExit(f"Missing routes dataset: {routes_path}")

    ports = _load_ports(ports_path)

    with routes_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        routes = list(r)
        fieldnames = r.fieldnames or []

    # Add new columns if missing.
    for col in ["port_of_embarkment", "port_of_arrival"]:
        if col not in fieldnames:
            fieldnames.append(col)

    for row in routes:
        code = (row.get("route_code") or "").strip()
        desc = (row.get("short_description") or "").strip()

        embark_token, arrival_token = _extract_endpoints(code, desc)

        # Best-effort matches; leave blank when we only have a region or cannot match uniquely.
        preferred_country = None
        if code == "C7":
            preferred_country = "Colombia"

        embark = _match_port(embark_token, ports, preferred_country=preferred_country) if embark_token else None
        arrival = _match_port(arrival_token, ports) if arrival_token else None

        row["port_of_embarkment"] = embark.name if embark else ""
        row["port_of_arrival"] = arrival.name if arrival else ""

    with routes_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in routes:
            w.writerow({k: (row.get(k) or "") for k in fieldnames})


if __name__ == "__main__":
    main()
