#!/usr/bin/env python3
"""Export filtered Home Assistant entities through the REST API."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "result.json"

INCLUDE_DOMAINS = {
    "sensor",
    "binary_sensor",
    "weather",
    "climate",
    "calendar",
    "person",
    "device_tracker",
    "alarm_control_panel",
    "sun",
}

EXCLUDE_PREFIXES = (
    "update.",
    "automation.",
    "script.",
    "button.",
    "scene.",
)


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip().strip("'").strip('"')
    return env


def should_include(entity_id: str) -> bool:
    domain = entity_id.split(".", 1)[0]
    if domain not in INCLUDE_DOMAINS:
        return False
    return not any(entity_id.startswith(prefix) for prefix in EXCLUDE_PREFIXES)


def normalize_entity(entity: dict) -> dict:
    attributes = entity.get("attributes", {})
    return {
        "entity_id": entity.get("entity_id"),
        "name": attributes.get("friendly_name"),
        "state": entity.get("state"),
        "unit": attributes.get("unit_of_measurement"),
        "device_class": attributes.get("device_class"),
        "state_class": attributes.get("state_class"),
        "icon": attributes.get("icon"),
    }


def fetch_states(ha_url: str, token: str) -> list[dict]:
    base_url = ha_url.rstrip("/")
    request = Request(f"{base_url}/api/states", method="GET")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/json")

    with urlopen(request, timeout=20) as response:
        payload = response.read().decode("utf-8")
    states = json.loads(payload)
    if not isinstance(states, list):
        raise ValueError("Unexpected response format from /api/states (expected list)")
    return states


def main() -> int:
    env = load_env_file(ENV_PATH)
    ha_url = env.get("HA_URL", "").strip()
    token = env.get("HA_TOKEN", "").strip()

    if not ha_url:
        print(f"Missing HA_URL in {ENV_PATH}", file=sys.stderr)
        return 1
    if not token:
        print(f"Missing HA_TOKEN in {ENV_PATH}", file=sys.stderr)
        return 1

    try:
        states = fetch_states(ha_url, token)
    except HTTPError as exc:
        print(f"HTTP error from Home Assistant: {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Cannot reach Home Assistant: {exc.reason}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    filtered = [
        normalize_entity(entity)
        for entity in states
        if isinstance(entity, dict) and should_include(entity.get("entity_id", ""))
    ]
    filtered.sort(key=lambda item: item["entity_id"] or "")

    output_path = DEFAULT_OUTPUT_PATH
    output_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(filtered)} entities to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
