# Optional: TBM tram via HACS (no personal API key)

If you prefer UI configuration over YAML REST sensors, use the community integration:

- Repository: https://github.com/kpagnat/tbm_horaires
- Install via **HACS → Integrations → Custom repositories**

## Setup

1. Add the repo URL in HACS.
2. Install **TBM Horaires**.
3. **Settings → Devices & services → Add integration → TBM Horaires**.
4. Pick line, stop, and direction in the UI.

The integration uses the same public SIRI-Lite key (`opendata-bordeaux-metropole-flux-gtfs-rt`) — no account.

A practical advantage of HACS here: you pick your stop and line **by name** in the UI, so you never have to deal with raw `LineRef` numbers — which is good, because TBM's tram `LineRef` codes don't map to letters intuitively (e.g. Tram A is line `59`, not `01`). See [FIND_YOUR_IDS.md](../FIND_YOUR_IDS.md) if you go the REST route instead and need to resolve these yourself.

## Entities for the dashboard

The integration exposes a sensor with a `departures` attribute (list). Example template sensors for the next 2 trams:

```yaml
template:
  - sensor:
      - name: "TBM Tram 1 min (HACS)"
        unit_of_measurement: "min"
        state: >
          {% set deps = state_attr('sensor.YOUR_TBM_SENSOR', 'departures') or [] %}
          {% if deps | length > 0 %}
            {{ deps[0].minutes }}
          {% else %}
            {{ none }}
          {% endif %}

      - name: "TBM Tram 2 min (HACS)"
        unit_of_measurement: "min"
        state: >
          {% set deps = state_attr('sensor.YOUR_TBM_SENSOR', 'departures') or [] %}
          {% if deps | length > 1 %}
            {{ deps[1].minutes }}
          {% else %}
            {{ none }}
          {% endif %}
```

> Sensors with `unit_of_measurement` are numeric to HA — the state template must render a number or `none`, never a text string like `"unavailable"` (that raises an error). `{{ none }}` renders `unknown` instead, which is safe.

Replace `sensor.YOUR_TBM_SENSOR` with the entity created by the integration (see **Developer tools → States**).

## When to use HACS vs REST

| | REST (`tram_siri_lite.yaml`) | HACS (`tbm_horaires`) |
|--|------------------------------|------------------------|
| API key | Public key in URL | Built-in public key |
| Maintenance | You own the YAML | Community updates |
| UI setup | Edit YAML IDs | Pick stop in UI |
| Future-proof | Direct official API | Depends on integration maintainer |

For **Le Vélo**, stay on the official REST example — no HACS needed.
