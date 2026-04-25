# HA Entities Export Helper

This folder contains a reusable Home Assistant Developer Tools template script to export a clean JSON snapshot of entities for dashboard design and future updates.

## Files

- `export_entities_template.jinja`: Jinja template to run in Home Assistant Developer Tools.
- `result.txt`: optional output file where you can paste/export the latest JSON snapshot.

## How to use

1. Open Home Assistant.
2. Go to `Developer Tools` -> `Template`.
3. Open `export_entities_template.jinja` from this folder and copy all its content.
4. Paste the template into the HA template editor and run it.
5. Copy the generated JSON output.
6. Paste it into `ha_entities/result.txt` (replace previous content).

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
- Keep `result.txt` up to date before dashboard redesign iterations.
- If needed, create versioned snapshots, for example:
  - `result-2026-04-25.txt`
  - `result-2026-05-10.txt`
