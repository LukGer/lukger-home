#!/usr/bin/env python3
"""Daily flight tracker using the Kiwi Tequila API (searching via RapidAPI optional)."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

WORKSPACE = Path.home() / ".openclaw" / "workspace"
CONFIG_PATH = WORKSPACE / "private_config.json"
API_URL = "https://tequila-api.kiwi.com/v2/search"
EXCLUDED_CARRIERS = {"CA", "MU", "CZ", "HU", "ZH", "FM", "NX", "KN", "EY"}

STATE_FILE = WORKSPACE / ".flight_watcher_state.json"
CACHE_LIMIT = 10


@dataclass
class RouteSegment:
    airline: str
    city_from: str
    city_to: str
    local_departure: str
    local_arrival: str
    return_flag: int


@dataclass
class FlightOffer:
    price: float
    currency: str
    route: List[RouteSegment]
    layover_minutes: float
    destination: str


def load_config() -> Mapping:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("private_config.json not found; cannot run flight watcher")
    data = json.loads(CONFIG_PATH.read_text())
    if "tequila_api_key" not in data or not data["tequila_api_key"]:
        raise KeyError("tequila_api_key missing from private_config.json; please add your Tequila API key")
    return data


def call_api(destination: str, api_key: str) -> Sequence[Mapping]:
    params = {
        "fly_from": "VIE",
        "fly_to": destination,
        "date_from": "10/09/2026",
        "date_to": "10/09/2026",
        "return_from": "01/10/2026",
        "return_to": "01/10/2026",
        "curr": "EUR",
        "limit": CACHE_LIMIT,
        "sort": "price",
        "max_stopovers": 1,
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url)
    request.add_header("apikey", api_key)
    request.add_header("Accept", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return payload.get("data", [])


def parse_route(entry: Mapping) -> List[RouteSegment]:
    segments = []
    for segment in entry.get("route", []):
        segments.append(
            RouteSegment(
                airline=segment.get("airline", ""),
                city_from=segment.get("cityFrom", ""),
                city_to=segment.get("cityTo", ""),
                local_departure=segment.get("local_departure", ""),
                local_arrival=segment.get("local_arrival", ""),
                return_flag=segment.get("return", 0),
            )
        )
    return segments


def max_layover(route: Sequence[RouteSegment]) -> float:
    max_gap = 0.0
    for current, nxt in zip(route, route[1:]):
        if current.return_flag != nxt.return_flag:
            continue
        if not current.local_arrival or not nxt.local_departure:
            continue
        try:
            arrived = datetime.fromisoformat(current.local_arrival)
            trg = datetime.fromisoformat(nxt.local_departure)
        except ValueError:
            continue
        gap = (trg - arrived).total_seconds() / 60
        if gap > max_gap:
            max_gap = gap
    return max_gap


def filter_offers(entries: Iterable[Mapping]) -> List[FlightOffer]:
    offers = []
    for entry in entries:
        price = entry.get("price")
        currency = entry.get("currency", "EUR")
        if not price:
            continue
        route = parse_route(entry)
        if not route:
            continue
        if any(seg.airline in EXCLUDED_CARRIERS for seg in route):
            continue
        layover_min = max_layover(route)
        if layover_min > 300:
            continue
        destination = route[-1].city_to or entry.get("flyTo", "")
        offers.append(
            FlightOffer(
                price=float(price),
                currency=currency,
                route=route,
                layover_minutes=layover_min,
                destination=destination,
            )
        )
    return sorted(offers, key=lambda o: o.price)


def summarize_offer(offer: FlightOffer) -> str:
    legs = []
    current_return = offer.route[0].return_flag
    chunk = []
    for segment in offer.route:
        if segment.return_flag != current_return and chunk:
            legs.append((current_return, chunk))
            chunk = []
            current_return = segment.return_flag
        chunk.append(segment)
    if chunk:
        legs.append((current_return, chunk))
    lines = [f"EUR {offer.price:.2f} → {offer.destination} ({len(offer.route)} segments; layover max {offer.layover_minutes:.0f} min)"]
    for direction, segments in legs:
        label = "Return" if direction == 1 else "Outbound"
        seg_desc = []
        for seg in segments:
            seg_desc.append(f"{seg.city_from}→{seg.city_to} ({seg.airline}) {seg.local_departure}–{seg.local_arrival}")
        lines.append(f"  {label}: {'; '.join(seg_desc)}")
    return "\n".join(lines)


def load_state() -> Mapping[str, float]:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text())


def save_state(state: Mapping[str, float]) -> None:
    STATE_FILE.write_text(json.dumps(state))


def collect_offers(api_key: str) -> List[FlightOffer]:
    results = []
    for destination in ("HND", "NRT"):
        entries = call_api(destination, api_key)
        results.extend(filter_offers(entries))
    return results[:10]


def main() -> int:
    config = load_config()
    api_key = config["rapidapi_key"]
    offers = collect_offers(api_key)
    if not offers:
        print("No matching flights were found today.")
        return 0
    summary_lines = ["Top 3 flight options:"]
    for idx, offer in enumerate(offers[:3], start=1):
        summary_lines.append(f"{idx}. {summarize_offer(offer)}")
    best_price = offers[0].price
    previous = load_state().get("best_price")
    note = ""
    if previous is None or best_price < previous:
        note = f"New best price discovered: EUR {best_price:.2f} (prev: {previous if previous else 'none'})"
    else:
        note = f"No change in best price (EUR {best_price:.2f})."
    summary = note + "\n" + "\n".join(summary_lines)
    print(summary)
    save_state({"best_price": best_price, "timestamp": datetime.utcnow().isoformat()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
