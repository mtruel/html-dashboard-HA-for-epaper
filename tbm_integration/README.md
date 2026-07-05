# TBM integration (tram + Le Vélo) for Home Assistant

Guide to expose **TBM tram arrivals** and **Le Vélo station availability** as Home Assistant sensors, then read them from the reTerminal dashboard (`src/index.html`).

Designed for:

- **No personal API key** — only Bordeaux Métropole **public open-data** endpoints (no signup).
- **Future-proof sources** — official SIRI-Lite (tram) and Bordeaux DataHub API (bikes), referenced on [transport.data.gouv.fr](https://transport.data.gouv.fr/).
- **Server-side fetching in HA** — the ePaper page never calls TBM directly (avoids CORS and keeps one refresh pipeline).

The examples are pre-configured for:

| | Location | ID used |
|--|----------|---------|
| Tram → Bordeaux | **Alfred de Vigny** (platform BP:5235) | `sensor.tbm_tram_1_min`, `_2_min`, `_1_line`, `_2_line` |
| Tram → Mérignac | **Alfred de Vigny** (platform BP:5234) | `sensor.tbm_tram_merignac_1_min`, `_2_min`, `_1_line`, `_2_line` |
| Le Vélo | **Fontaine d'Arlac** | `ident: 90` |

That platform only serves Tram A (line 59) and Tram F (line 164), so no `LineRef` filter is used — both lines are shown mixed, sorted by arrival time, with a "line" sensor telling you which is which.

## Quick start (TL;DR)

1. If you need a *different* stop/station, find the IDs first:

   ```bash
   python3 tbm_integration/scripts/discover_ids.py tram "your stop name"
   python3 tbm_integration/scripts/discover_ids.py lines   # current tram A-F LineRefs
   python3 tbm_integration/scripts/discover_ids.py velo "your station name"
   ```

2. Copy `examples/package_tram_velo.yaml` → HA `config/packages/tbm/tram_velo.yaml` (already set for Alfred de Vigny + Fontaine d'Arlac; edit the `MonitoringRef=`/`ident=` values inside the URLs only if you want a different location).
3. Restart Home Assistant, confirm entities in **Developer tools → States**.
4. Add entity IDs to `src/index.html` (see `examples/index_html_entities.example.js`).

Full details, troubleshooting, and alternatives (HACS) below.

> **Tram line numbering isn't intuitive.** TBM now runs 6 tram lines (A–F), and their `LineRef` numbers don't correspond to the letters at all — Tram A is line `59`, Tram F is line `164`, while low numbers like `01`–`31` are bus "Lianes" routes. Always resolve line codes with `discover_ids.py lines`, never guess. See [FIND_YOUR_IDS.md](FIND_YOUR_IDS.md) for details.

## Architecture

```text
Bordeaux open data APIs
        │
        ▼
Home Assistant (REST + template sensors, 60–150 s)
        │
        ▼
src/index.html  →  /api/states  →  Puppeteer  →  reTerminal ePaper
```

## What you need to customize (once)

| Setting | Tram | Le Vélo |
|--------|------|---------|
| Location | `MonitoringRef` (SIRI stop ID) | `ident` (station number) |
| Direction / line | `LineRef` + optional destination filter | Station name only |
| Example files | `examples/tram_siri_lite.yaml` | `examples/velo_le_velo.yaml` |

Use `scripts/discover_ids.py` to search by stop/station name (see [FIND_YOUR_IDS.md](FIND_YOUR_IDS.md)).

## About the “API key” for trams

TBM SIRI-Lite uses a query parameter `AccountKey=opendata-bordeaux-metropole-flux-gtfs-rt`.

That value is **not a personal secret**. It is the **published public key** on Bordeaux Métropole open data — no account, no registration. It is included in all example URLs below.

Le Vélo (`ci_vcub_p`) needs **no key at all**.

## Recommended approach

| Data | Recommended | Why |
|------|-------------|-----|
| Tram next passages | **REST + template** (`examples/tram_siri_lite.yaml`) | Official SIRI-Lite, YAML-only, no HACS |
| Tram (UI setup) | [tbm_horaires](https://github.com/kpagnat/tbm_horaires) HACS integration | Pick line/stop in HA UI; same public key |
| Le Vélo bikes | **REST** (`examples/velo_le_velo.yaml`) | Official Bordeaux DataHub, no third party |
| Le Vélo (alternative) | CityBikes `network: v3-bordeaux` | No key, but aggregator (less “source of truth”) |

This folder focuses on **REST + template** (maximum control, official APIs).

## Install in Home Assistant

### Option A — Package (recommended)

1. Copy `examples/package_tram_velo.yaml` to your HA config, e.g.  
   `config/packages/tbm/tram_velo.yaml`
2. Edit the `MonitoringRef=`, `LineRef=`, and `ident=` values **directly inside the URL strings** (see the comment block at the top of the file, and [FIND_YOUR_IDS.md](FIND_YOUR_IDS.md)).
3. Ensure packages are enabled in `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages/
```

4. **Settings → System → Restart** Home Assistant.
5. **Developer tools → States** — confirm new `sensor.tbm_*` and `sensor.le_velo_*` entities.

### Option B — Paste into `configuration.yaml`

Merge the contents of:

- `examples/tram_siri_lite.yaml`
- `examples/velo_le_velo.yaml`
- `examples/template_sensors.yaml`

Adjust `unique_id` / names if you already have conflicts.

## Example entities (after install)

With default names from `package_tram_velo.yaml`:

| Entity | Meaning |
|--------|---------|
| `sensor.tbm_tram_raw` | Raw SIRI JSON (attributes hold visit list) |
| `sensor.tbm_tram_1_min` / `_2_min` | Minutes until 1st / 2nd tram |
| `sensor.tbm_tram_1_line` / `_2_line` | Which tram is coming (`A` or `F`) |
| `sensor.tbm_tram_1_destination` / `_2_destination` | Destination of 1st / 2nd tram |
| `sensor.le_velo_raw` | Raw station record |
| `sensor.le_velo_bikes` | Available bikes (`nbvelos`) |
| `sensor.le_velo_free_docks` | Free docks available now (`nbplaces`, a direct field — **not** total capacity) |

## Wire into the dashboard

See `examples/index_html_entities.example.js` — add entity IDs and render logic in `updateDashboardData()` in `src/index.html`.

Refresh interval: keep **60 s** on HA sensors and **30 s** on the dashboard (same as weather/calendar).

## Files in this folder

```text
tbm_integration/
├── README.md                 ← this file
├── FIND_YOUR_IDS.md          ← how to find stop / station IDs
├── examples/
│   ├── package_tram_velo.yaml
│   ├── tram_siri_lite.yaml
│   ├── velo_le_velo.yaml
│   ├── template_sensors.yaml
│   ├── index_html_entities.example.js
│   └── option_hacs_tbm_horaires.md
└── scripts/
    └── discover_ids.py       ← search tram stops & velo stations by name
```

## Official references

- TBM open data (tram, SIRI-Lite, GTFS):  
  https://opendata.bordeaux-metropole.fr/explore/dataset/offres-de-services-bus-tramway-gtfs/
- Le Vélo real-time stations:  
  https://datahub.bordeaux-metropole.fr/explore/dataset/ci_vcub_p/
- transport.data.gouv.fr dataset index:  
  https://transport.data.gouv.fr/datasets?organization_id=5b0d11f688ee382af4b18c95

## Troubleshooting

| Symptom | Check |
|--------|--------|
| `sensor.tbm_tram_raw` = `0` | No trams for that stop/line/direction right now (night, wrong `LineRef`, or wrong direction) — verify with `discover_ids.py tram "..."` |
| `sensor.tbm_tram_1_min` / `le_velo_bikes` = `unknown` | Underlying data missing (see note in `template_sensors.yaml`) — this is expected while no tram/bike data is present, not an error |
| `sensor.tbm_tram_raw` / `sensor.le_velo_raw` = `unavailable` | L’appel API a échoué (réseau, URL) — ouvrir l’URL `resource:` dans un navigateur ; vérifier qu’il n’y a plus d’erreur `availability_template` dans les journaux |
| `sensor.le_velo_bikes` stuck at wrong value | Wrong `ident`; run `discover_ids.py velo "Your station name"` |
| Dashboard shows `--` | Entity ID mismatch; verify exact names in **Developer tools → States** |
| CORS errors in browser | Expected if calling TBM/Le Vélo directly from `index.html` — always go through HA sensors |
