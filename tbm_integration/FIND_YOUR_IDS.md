# Find your tram stop and Le Vélo station IDs

## Quick discovery script

From the repo root:

```bash
# Tram: search SIRI stoppoints by name (needs network) — also tags known tram lines
python3 tbm_integration/scripts/discover_ids.py tram "Alfred de Vigny"

# List all current tram lines (A-F) with their real LineRef codes
python3 tbm_integration/scripts/discover_ids.py lines

# Le Vélo: search Bordeaux open data by station name
python3 tbm_integration/scripts/discover_ids.py velo "Arlac"
```

## Tram — `MonitoringRef`

Format: `bordeaux:StopPoint:BP:<number>:LOC`

### Method 1 — SIRI stoppoints-discovery (official)

```text
GET https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux/stoppoints-discovery.json
    ?AccountKey=opendata-bordeaux-metropole-flux-gtfs-rt
```

Search the JSON for your stop name. Use the stop's **`StopPointRef.value`** as `MonitoringRef` (e.g. `bordeaux:StopPoint:BP:5235:LOC`).

### Method 2 — GTFS `stops.txt`

1. Download GTFS from [opendata.bordeaux-metropole.fr](https://opendata.bordeaux-metropole.fr/explore/dataset/offres-de-services-bus-tramway-gtfs/).
2. Open `stops.txt`, find `stop_name`.
3. Build: `bordeaux:StopPoint:BP:<stop_id>:LOC`.

## Line reference — `LineRef`

**Critical: tram letters do NOT map to low line numbers.** For example, in the current data (checked live): Tram A is line **59**, Tram B is line **60**, Tram F is line **164** — while `Line:01`–`Line:31` etc. are **bus** routes branded "Lianes". Never guess a `LineRef` from a tram letter or from memory — TBM has expanded its tram network over time (it now has lines **A through F**), and numbering isn't documented anywhere predictable.

### The reliable way — `lines-discovery.json`

This endpoint returns the real `LineName` (e.g. `"Tram A"`) for every `LineRef`, plus its destinations:

```text
GET https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux/lines-discovery.json
    ?AccountKey=opendata-bordeaux-metropole-flux-gtfs-rt
```

Or simply:

```bash
python3 tbm_integration/scripts/discover_ids.py lines
```

Watch out for **"Navette Tram 100"**–**"Navette Tram 406"** style entries — these are shuttle *buses* that connect to tram stations, not trams themselves, despite the word "Tram" in their name. The script already filters these out and only lists real `Tram A`–`Tram F` lines.

### Confirming what serves your stop

`discover_ids.py tram "..."` cross-checks each line at a matching stop against the live tram-line list and tags each one `(TRAM Tram X)` or `(bus)`. If a line isn't tagged as tram, don't assume it is one.

### Disambiguating two directions/branches at the same stop

Each visit in a `stop-monitoring.json` response includes `LineRef`, `DirectionRef` (`0`/`1`), and `DestinationName`. If your stop serves more than one tram line or both directions and you only want one:

- Add `&LineRef=bordeaux:Line:<n>:LOC` to keep only one line, and/or
- Filter by `DestinationName` inside the template sensor if direction still isn't unique.

If you don't filter by `LineRef` at all, you get **everything serving that exact platform** — which is fine (and often desired) if the platform only serves the lines you care about, as in the example config (Alfred de Vigny only serves Tram A + Tram F, so no filter is needed).

### Test in browser

```text
https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux/stop-monitoring.json
  ?AccountKey=opendata-bordeaux-metropole-flux-gtfs-rt
  &MonitoringRef=bordeaux:StopPoint:BP:5235:LOC
  &MaximumStopVisits=4
```

Empty `MonitoredStopVisit` usually means no service at that time (night) or a wrong `MonitoringRef` — not necessarily a wrong `LineRef`.

## Le Vélo — station `ident`

### Method 1 — DataHub API (official, no key)

```text
GET https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/records
    ?limit=5
    &where=search(nom,"Arlac")
```

Use field **`ident`** (integer) in `examples/velo_le_velo.yaml`.

### Method 2 — Browse the dataset

Open [ci_vcub_p on DataHub](https://datahub.bordeaux-metropole.fr/explore/dataset/ci_vcub_p/) and search your station name.

Fields useful for the dashboard (verified against the official field descriptions):

| Field | Meaning |
|-------|---------|
| `nbvelos` | **Total** bikes available now |
| `nbelec` | Electric bikes available now |
| `nbclassiq` | Classic bikes available now |
| `nbplaces` | **Free docks available now** (not total capacity!) |
| `etat` | `CONNECTEE` / `DECONNECTEE` / `MAINTENANCE` |

Total capacity ≈ `nbvelos + nbplaces` (not `nbplaces` alone, and not `nbplaces - nbvelos`). For example, Fontaine d'Arlac (`ident=90`) has `nbvelos=16`, `nbplaces=2` → 16 bikes docked, only 2 free spots, ~18 total capacity — a nearly-full station, not a nearly-empty one.
