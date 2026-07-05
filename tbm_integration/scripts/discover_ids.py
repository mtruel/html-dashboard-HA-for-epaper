#!/usr/bin/env python3
"""Search TBM tram/bus stops (SIRI), TBM tram lines, and Le Vélo stations (Bordeaux DataHub)."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# Matches "Tram A" .. "Tram F" but NOT "Navette Tram 100" (shuttle buses feeding
# tram stations, which also contain the word "Tram" in their LineName).
TRAM_LINE_NAME_RE = re.compile(r"^Tram [A-Z]$")

TBM_ACCOUNT_KEY = "opendata-bordeaux-metropole-flux-gtfs-rt"
TBM_STOPPOINTS_URL = (
    "https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux/stoppoints-discovery.json"
)
TBM_LINES_URL = "https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux/lines-discovery.json"
VELO_API = (
    "https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/records"
)


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "homeassistant-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get_tram_line_refs() -> dict[str, dict]:
    """Return {LineRef: {code, name, destinations}} for lines whose LineName contains 'Tram'.

    IMPORTANT: tram LineRef numbers are NOT fixed (e.g. Tram A is line 59, not line 01 —
    low numbers are actually bus "Lianes" routes). Always resolve via LineName, never guess.
    """
    url = f"{TBM_LINES_URL}?AccountKey={urllib.parse.quote(TBM_ACCOUNT_KEY)}"
    data = fetch_json(url)
    lines = data["Siri"]["LinesDelivery"]["AnnotatedLineRef"]
    trams = {}
    for line in lines:
        name = line.get("LineName", [{}])[0].get("value", "")
        if TRAM_LINE_NAME_RE.match(name):
            ref = line.get("LineRef", {}).get("value", "")
            code = line.get("LineCode", {}).get("value", "")
            dests = [
                d.get("PlaceName", [{}])[0].get("value", "")
                for d in line.get("Destinations", [])
            ]
            trams[ref] = {"code": code, "name": name, "destinations": dests}
    return trams


def list_tram_lines() -> None:
    trams = get_tram_line_refs()
    if not trams:
        print("No tram lines found (unexpected — check API availability).")
        return
    print("Current TBM tram lines (live, verified via LineName — do not assume this from memory):\n")
    for ref, info in sorted(trams.items(), key=lambda kv: kv[1]["code"]):
        print(f"  {info['name']} (code {info['code']})")
        print(f"    LineRef: {ref}")
        if info["destinations"]:
            print(f"    Destinations: {' / '.join(info['destinations'])}")
        print()


def search_tram(query: str, limit: int = 15) -> None:
    tram_refs = get_tram_line_refs()

    url = f"{TBM_STOPPOINTS_URL}?AccountKey={urllib.parse.quote(TBM_ACCOUNT_KEY)}"
    data = fetch_json(url)
    delivery = data["Siri"]["StopPointsDelivery"]
    points = delivery.get("AnnotatedStopPointRef", [])
    q = query.casefold()
    matches = []
    for pt in points:
        stop_name = pt.get("StopName", {})
        name = stop_name.get("value", "") if isinstance(stop_name, dict) else ""
        ref_obj = pt.get("StopPointRef", {})
        ref = ref_obj.get("value", "") if isinstance(ref_obj, dict) else str(ref_obj)
        lines = [line.get("value", line) for line in pt.get("Lines", [])]
        if q in name.casefold() or q in ref.casefold():
            matches.append((name, ref, lines))
    matches = matches[:limit]
    if not matches:
        print(f"No stop matching {query!r}")
        return
    print(f"Stops matching {query!r}:\n")
    for name, ref, lines in matches:
        print(f"  {name}")
        print(f"    MonitoringRef: {ref}")
        for line_ref in lines[:8]:
            tag = tram_refs.get(line_ref)
            label = f"TRAM {tag['name']}" if tag else "bus"
            print(f"      - {line_ref}  ({label})")
        print()
    if not any(lr in tram_refs for _, _, lines in matches for lr in lines):
        print("Note: none of the Lines above matched a known tram LineRef.")
        print("Run 'discover_ids.py lines' to see current tram lines, or query")
        print(f"stop-monitoring.json for one of the MonitoringRef values above")
        print("(without a LineRef filter) to see exactly what serves that platform.")


def search_velo(query: str, limit: int = 15) -> None:
    params = urllib.parse.urlencode({"limit": limit, "where": f'search(nom,"{query}")'})
    data = fetch_json(f"{VELO_API}?{params}")
    results = data.get("results", [])
    if not results:
        print(f"No Le Vélo station matching {query!r}")
        return
    print(f"Le Vélo stations matching {query!r}:\n")
    for row in results:
        # nbplaces = free docks (NOT total capacity) per the official field description.
        free_docks = row.get("nbplaces")
        bikes = row.get("nbvelos")
        capacity = (bikes or 0) + (free_docks or 0) if bikes is not None and free_docks is not None else None
        print(f"  {row.get('nom')} (ident={row.get('ident')})")
        print(
            f"    bikes={bikes}  free_docks={free_docks}"
            f"  capacity≈{capacity}  etat={row.get('etat')}"
        )
        print()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage:")
        print('  discover_ids.py tram "stop name"')
        print('  discover_ids.py velo "station name"')
        print("  discover_ids.py lines        (list current tram lines A-F with LineRefs)")
        return 1
    mode = sys.argv[1].lower()
    query = " ".join(sys.argv[2:])
    try:
        if mode == "tram":
            if not query:
                print('Usage: discover_ids.py tram "stop name"')
                return 1
            search_tram(query)
        elif mode in ("velo", "bike", "vcub"):
            if not query:
                print('Usage: discover_ids.py velo "station name"')
                return 1
            search_velo(query)
        elif mode in ("lines", "tramlines"):
            list_tram_lines()
        else:
            print(f"Unknown mode {mode!r}. Use tram, velo, or lines.")
            return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1
    except (KeyError, json.JSONDecodeError) as exc:
        print(f"Unexpected API response: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
