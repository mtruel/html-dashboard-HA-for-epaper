# Home Assistant Dashboard for reTerminal E1001



This project is focused on building a custom web dashboard for Home Assistant that is displayed on a **Seeed Studio reTerminal E1001**.

### Why?
I wanted a dashboard better suited to this small ePaper display without touch interaction.

### How:
- The dashboard is an HTML page hosted on your Home Assistant instance. It has access to your Home Assistant entities and data.
- It is displayed in a Home Assistant dashboard view, then rendered as an image through the Puppeteer screenshot endpoint.
- The reTerminal screen runs ESPHome and is configured to access the Puppeteer screenshot endpoint. It refreshes the screen regularly with the latest dashboard image.
### Repository Contents

- `src/index.html`: custom 800x480 dashboard page (ePaper-oriented preview).
- `reterminal.yaml`: ESPHome configuration used by the reTerminal E1001 to display the dashboard image.
- `ha_entities/`: Notes and template for exporting Home Assistant entities.



## Deployment Process

This project uses a static HTML page hosted by Home Assistant, displayed in a Home Assistant dashboard view, then rendered as an image through the Puppeteer screenshot endpoint.

### 0) Clone this repository

```bash
git clone https://github.com/mtruel/html-dashboard-HA-for-epaper.git
cd homeassistant_dashboard
```

### 1) Deploy the dashboard page to Home Assistant

Copy the local dashboard file:

- from: `src/index.html`
- to: `/config/www/reterminal/index.html` on your Home Assistant instance

`/config/www` is served by Home Assistant as `/local`.

> I used the Visual Studio Code Server add-on to do the copy/paste.

**Validate page hosting**

Open in a browser: `http://<HA_URL>/local/reterminal/index.html`

The `<HA_URL>` is the URL used to access your Home Assistant instance (example: `homeassistant.local` or `192.168.x.x`)

If the page loads, static hosting is correct.
### 2) Configure Puppeteer and dashboard URLs

Use the following validated setup:

- Puppeteer add-on `home_assistant_url`:
  - `http://<HA_HOST>:8123`
- Home Assistant dashboard web page/card URL:
  - `http://<HA_HOST>:8123/local/reterminal/index.html`
- Screenshot URL used by ESPHome (`online_image.url`):
  - `http://<HA_HOST>:10000/dashboard-reterminal/0?viewport=800x480&colors=000000,FFFFFF&invert`

This avoids redirect issues seen with direct `:10000/local/...` captures and keeps screenshot rendering stable.

### 4) Flash/update device config

- Compile and upload `reterminal.yaml` with ESPHome.
- Wait for the next `online_image.update_interval` cycle (or trigger an update manually if desired).
- Confirm the ePaper shows the new rendered page.

## Updating the dashboard later

1. Edit `src/index.html`.
2. Copy it again to `/config/www/reterminal/index.html`.
3. Test page hosting directly:
   - `http://<HA_HOST>:8123/local/reterminal/index.html`
4. Verify screenshot endpoint:
   - `http://<HA_HOST>:10000/dashboard-reterminal/0?viewport=800x480&colors=000000,FFFFFF&invert`
5. Wait for next image refresh on the reTerminal.

Tip: if you see stale content in browser tests, add a cache buster:

- `http://<HA_HOST>:8123/local/reterminal/index.html?v=2`

## Local Development Process

To test the dashboard locally while developing, use the included preview server.
It reads your Home Assistant token from `.env`, injects it into browser `localStorage`, and proxies `/api/*` calls to Home Assistant.

1. Clone this repository:
   - `git clone https://github.com/<YOUR_ACCOUNT>/homeassistant_dashboard.git`
   - `cd homeassistant_dashboard`
2. Create your local environment file:
   - `cp .env.example .env`
3. Edit `.env`:
   - `HA_URL=http://<HA_HOST>:8123`
   - `HA_TOKEN=<LONG_LIVED_ACCESS_TOKEN>`
4. Start the local preview server:
   - `uv run scripts/dev_preview.py`
   - (alternative) `python3 scripts/dev_preview.py`
5. Open:
   - `http://127.0.0.1:8000`
6. Optional PNG render preview generated locally by the preview server:
   - open `http://127.0.0.1:8000/__preview.png`
   - optional query params: `width`, `height`, `delay_ms`, `bw`, `threshold`
   - by default `bw=true` (black/white output), threshold default is `128`
   - example: `http://127.0.0.1:8000/__preview.png?width=800&height=480&delay_ms=1500&threshold=140`
7. Optional live auto-reload page for PNG preview:
   - open `http://127.0.0.1:8000/preview`
   - optional query params: `refresh_ms` + all PNG params above
   - example: `http://127.0.0.1:8000/preview?refresh_ms=10000&threshold=140`

Notes:
- This is for local development only.
- `.env` is gitignored to avoid committing secrets.


## References
- Device reference: [Getting Started with reTerminal E1001](https://wiki.seeedstudio.com/getting_started_with_reterminal_e1001/)
- Screenshot workflow reference: [Take the Home Assistant dashboard as a screenshot](https://wiki.seeedstudio.com/reterminal_e10xx_with_esphome_advanced/#demo-2-take-the-home-assistant-dashboard-as-a-screenshot)

## Troubleshooting

- `:10000/local/...` redirects to `/home/overview` or wrong dashboard:
  - use `dashboard-reterminal/0` endpoint for screenshots,
  - keep Puppeteer `home_assistant_url` set to `http://<HA_HOST>:8123`,
  - use `/local/reterminal/index.html` only as the source page in HA.
- ePaper shows old image:
  - confirm `online_image.url` matches the deployed path,
  - check refresh interval and force a component update if needed.
- Layout does not fit:
  - keep page dimensions fixed to `800x480`,
  - avoid scrolling and animations for ePaper readability.
