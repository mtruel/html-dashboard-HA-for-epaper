# HA Entities Export Helper

This folder contains two ways to export a clean JSON snapshot of entities for dashboard design and future updates:

- a Home Assistant Developer Tools template
- a Python API export script using your local `.env` token

## Files

- `export_entities_template.jinja`: Jinja template to run in Home Assistant Developer Tools.
- `export_entities_api.py`: Python script that calls `GET /api/states` and writes filtered output.
- `result.json`: output snapshot of entities.

## Option A - Python API export (recommended)

Prerequisites:

- project root `.env` file with:
  - `HA_URL=http://<HA_HOST>:8123`
  - `HA_TOKEN=<LONG_LIVED_ACCESS_TOKEN>`

Run from project root:

- `python3 ha_entities/export_entities_api.py`

Output:

- writes filtered entities to `ha_entities/result.json`

## Option B - Home Assistant template export

1. Open Home Assistant.
2. Go to `Developer Tools` -> `Template`.
3. Open `export_entities_template.jinja` from this folder and copy all its content.
4. Paste the template into the HA template editor and run it.
5. Copy the generated JSON output.
6. Paste it into `ha_entities/result.json` (replace previous content).

## What the script exports

For selected domains, each item includes:

- `entity_id`
- `name`
- `state`
- `unit`
- `device_class`
- `state_class`
- `icon`

Default included domains:

- `sensor`
- `binary_sensor`
- `weather`
- `climate`
- `calendar`
- `person`
- `device_tracker`
- `alarm_control_panel`
- `sun`

Default excluded prefixes:

- `update.`
- `automation.`
- `script.`
- `button.`
- `scene.`

## Updating filters later

Edit `export_entities_template.jinja`:

- `include_domains` to add/remove complete domains.
- `exclude_prefixes` to hide families you do not want in the export.

## Recommended workflow

- Re-run export whenever you add new devices/entities in Home Assistant.
- Keep `result.json` up to date before dashboard redesign iterations.
- If needed, create versioned snapshots, for example:
  - `result-2026-04-25.json`
  - `result-2026-05-10.json`
