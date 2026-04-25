#!/usr/bin/env python3
"""Local preview server for the Home Assistant dashboard.

Reads Home Assistant settings from `.env`, serves `src/index.html`,
injects the HA token in localStorage for browser-side code, and proxies
`/api/*` requests to Home Assistant to avoid CORS issues during local dev.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
ENV_PATH = ROOT_DIR / ".env"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_PNG_ROUTE = "/__preview.png"
DEFAULT_CAPTURE_WIDTH = 800
DEFAULT_CAPTURE_HEIGHT = 480
DEFAULT_CAPTURE_DELAY_MS = 1200
DEFAULT_BW_THRESHOLD = 128

_ENV_CACHE: dict[str, str] = {}
_ENV_MTIME_NS: int | None = None
_INDEX_CACHE = ""
_INDEX_MTIME_NS: int | None = None


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        env[key] = value

    return env


def get_env() -> dict[str, str]:
    global _ENV_CACHE, _ENV_MTIME_NS
    if not ENV_PATH.exists():
        _ENV_CACHE = {}
        _ENV_MTIME_NS = None
        return {}

    mtime_ns = ENV_PATH.stat().st_mtime_ns
    if _ENV_MTIME_NS != mtime_ns:
        _ENV_CACHE = load_env_file(ENV_PATH)
        _ENV_MTIME_NS = mtime_ns

    return _ENV_CACHE


def get_index_html() -> str:
    global _INDEX_CACHE, _INDEX_MTIME_NS
    mtime_ns = (SRC_DIR / "index.html").stat().st_mtime_ns
    if _INDEX_MTIME_NS != mtime_ns:
        _INDEX_CACHE = (SRC_DIR / "index.html").read_text(encoding="utf-8")
        _INDEX_MTIME_NS = mtime_ns
    return _INDEX_CACHE


def get_dev_version() -> str:
    index_mtime = (SRC_DIR / "index.html").stat().st_mtime_ns
    env_mtime = ENV_PATH.stat().st_mtime_ns if ENV_PATH.exists() else 0
    return f"{index_mtime}-{env_mtime}"


def build_injected_token_script(token: str) -> str:
    escaped = token.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "<script>"
        '(function(){'
        'const payload={access_token:"%s"};'
        'localStorage.setItem("hassTokens", JSON.stringify(payload));'
        "})();"
        "</script>"
    ) % escaped


def build_live_reload_script(version: str) -> str:
    return (
        "<script>"
        '(function(){'
        f'let currentVersion="{version}";'
        "setInterval(async function(){"
        "try {"
        'const response=await fetch("/__dev_version",{cache:"no-store"});'
        "if(!response.ok)return;"
        "const nextVersion=(await response.text()).trim();"
        "if(nextVersion&&nextVersion!==currentVersion){"
        "location.reload();"
        "}"
        "} catch(_) {"
        "}"
        "},1000);"
        "})();"
        "</script>"
    )


class DashboardDevHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._dotenv: dict[str, str] = {}
        super().__init__(*args, directory=str(SRC_DIR), **kwargs)

    def _send_bytes_response(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (HTTP method naming)
        self._dotenv = get_env()
        request_path = urlsplit(self.path).path

        if self.path == "/__dev_version":
            version = get_dev_version().encode("utf-8")
            self._send_bytes_response(200, version, "text/plain; charset=utf-8")
            return

        if request_path == DEFAULT_PNG_ROUTE:
            self._proxy_png_preview()
            return

        if request_path.startswith("/api/"):
            self._proxy_home_assistant()
            return

        if request_path in {"/", "/index.html"}:
            self._serve_index()
            return

        super().do_GET()

    def _serve_index(self) -> None:
        html = get_index_html()
        token = self._dotenv.get("HA_TOKEN")
        dev_version = get_dev_version()
        if token:
            token_script = build_injected_token_script(token)
            if "<head>" in html:
                html = html.replace("<head>", f"<head>\n    {token_script}", 1)
            else:
                html = html.replace("</body>", f"    {token_script}\n  </body>")

        live_reload_script = build_live_reload_script(dev_version)
        html = html.replace("</body>", f"    {live_reload_script}\n  </body>")

        encoded = html.encode("utf-8")
        self._send_bytes_response(200, encoded, "text/html; charset=utf-8")

    def _proxy_home_assistant(self) -> None:
        base_url = self._dotenv.get("HA_URL", "").rstrip("/")
        token = self._dotenv.get("HA_TOKEN")
        if not base_url:
            self.send_error(500, "HA_URL missing in .env")
            return
        if not token:
            self.send_error(500, "HA_TOKEN missing in .env")
            return

        parsed = urlsplit(base_url)
        path = self.path if self.path.startswith("/") else f"/{self.path}"
        target_url = urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
        request = Request(target_url, method="GET")

        auth_header = self.headers.get("Authorization")
        request.add_header("Authorization", auth_header or f"Bearer {token}")
        request.add_header("Accept", "application/json")

        try:
            with urlopen(request, timeout=15) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
                self._send_bytes_response(response.status, body, content_type)
        except HTTPError as exc:
            body = exc.read() or str(exc).encode("utf-8")
            self._send_bytes_response(exc.code, body, "application/json")
        except URLError as exc:
            self.send_error(502, f"Unable to reach Home Assistant: {exc.reason}")

    def _proxy_png_preview(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        width = self._int_query_value(query, "width", DEFAULT_CAPTURE_WIDTH)
        height = self._int_query_value(query, "height", DEFAULT_CAPTURE_HEIGHT)
        delay_ms = self._int_query_value(query, "delay_ms", DEFAULT_CAPTURE_DELAY_MS)
        threshold = self._int_query_value(query, "threshold", DEFAULT_BW_THRESHOLD)
        bw = self._bool_query_value(query, "bw", True)

        if width <= 0 or height <= 0:
            self.send_error(400, "width and height must be positive integers")
            return
        if delay_ms < 0:
            self.send_error(400, "delay_ms must be >= 0")
            return
        if not 0 <= threshold <= 255:
            self.send_error(400, "threshold must be in range 0..255")
            return

        page_query = urlencode({"_capture_ts": get_dev_version()})
        page_url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/index.html?{page_query}"

        chrome_path = self._resolve_chrome_binary()
        if chrome_path is None:
            self.send_error(
                500,
                "No Chrome binary found. Install google-chrome/chromium for PNG preview.",
            )
            return

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            png_path = Path(tmp_file.name)

        command = [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={delay_ms}",
            f"--screenshot={png_path}",
            page_url,
        ]

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                details = (result.stderr or result.stdout or "").strip()
                if len(details) > 500:
                    details = f"{details[:500]}..."
                self.send_error(500, f"PNG capture failed: {details or 'unknown error'}")
                return

            if bw:
                self._convert_png_to_bw(png_path, threshold)
            body = png_path.read_bytes()
            self._send_bytes_response(200, body, "image/png")
        except subprocess.TimeoutExpired:
            self.send_error(504, "PNG capture timed out")
        finally:
            try:
                png_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _int_query_value(query: dict[str, list[str]], key: str, default: int) -> int:
        values = query.get(key)
        if not values:
            return default
        try:
            return int(values[0])
        except ValueError:
            return default

    @staticmethod
    def _bool_query_value(query: dict[str, list[str]], key: str, default: bool) -> bool:
        values = query.get(key)
        if not values:
            return default
        value = values[0].strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return True
        if value in {"0", "false", "no", "off"}:
            return False
        return default

    @staticmethod
    def _convert_png_to_bw(path: Path, threshold: int) -> None:
        with Image.open(path) as image:
            grayscale = image.convert("L")
            binary = grayscale.point(lambda pixel: 255 if pixel >= threshold else 0, mode="1")
            binary.convert("L").save(path, format="PNG", optimize=True)

    @staticmethod
    def _resolve_chrome_binary() -> str | None:
        for candidate in ("google-chrome", "chromium", "chromium-browser"):
            path = shutil.which(candidate)
            if path:
                return path
        return None


def main() -> None:
    host = os.environ.get("DEV_PREVIEW_HOST", DEFAULT_HOST)
    port = int(os.environ.get("DEV_PREVIEW_PORT", DEFAULT_PORT))

    server = ThreadingHTTPServer((host, port), DashboardDevHandler)
    print(f"Local dashboard preview: http://{host}:{port}")
    print(f"Preview PNG route: http://{host}:{port}{DEFAULT_PNG_ROUTE}")
    print(f"Using dotenv file: {ENV_PATH}")
    print("Expected .env keys: HA_URL, HA_TOKEN")
    print("PNG preview uses local headless Chrome capture")
    server.serve_forever()


if __name__ == "__main__":
    main()
