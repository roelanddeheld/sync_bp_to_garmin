from __future__ import annotations

import csv
import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import requests

from medm2garmin.models import BloodPressureReading

LOG = logging.getLogger(__name__)


class MedMClient:
    def __init__(
        self,
        *,
        api_base_url: str | None,
        api_token: str | None,
        timeout_seconds: int = 20,
    ) -> None:
        self._api_base_url = api_base_url
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds

    def fetch_readings(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[BloodPressureReading]:
        if not self._api_base_url or not self._api_token:
            raise RuntimeError("MedM API is not configured")

        params: dict[str, str] = {"type": "blood_pressure"}
        if since is not None:
            params["from"] = since.isoformat()
        if until is not None:
            params["to"] = until.isoformat()

        headers = {"Authorization": "Bearer " + self._api_token}
        response = requests.get(
            f"{self._api_base_url.rstrip('/')}/measurements",
            headers=headers,
            params=params,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        entries = payload.get("measurements", payload)
        if not isinstance(entries, list):
            raise ValueError("Unexpected MedM API response format")
        return _parse_dict_entries(entries)


def load_csv_readings(path: Path) -> list[BloodPressureReading]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return _parse_dict_entries(rows)


def _parse_dict_entries(entries: Iterable[object]) -> list[BloodPressureReading]:
    readings: list[BloodPressureReading] = []
    for entry in entries:
        if not isinstance(entry, dict):
            LOG.debug("Skipping non-dictionary entry: %r", entry)
            continue
        timestamp_raw = _read_first(
            entry,
            ["timestamp", "measurement_time", "datetime", "date_time"],
        )
        if not isinstance(timestamp_raw, str):
            LOG.warning("Skipping row without parseable timestamp: %r", entry)
            continue
        readings.append(
            BloodPressureReading(
                timestamp=datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00")),
                systolic=_to_int(_read_first(entry, ["systolic", "systolic_bp"])),
                diastolic=_to_int(_read_first(entry, ["diastolic", "diastolic_bp"])),
                pulse=_to_int(_read_first(entry, ["pulse", "heart_rate"])),
                source_id=_to_str_or_none(
                    _read_first(entry, ["id", "measurement_id"], optional=True)
                ),
                note=_to_str_or_none(_read_first(entry, ["note", "notes"], optional=True)) or "",
            )
        )
    return readings


def _read_first(entry: dict[object, object], keys: list[str], optional: bool = False) -> object:
    for key in keys:
        if key in entry and entry[key] not in (None, ""):
            return entry[key]
    if optional:
        return None
    raise ValueError(f"Missing required key from set: {keys}")


def _to_str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean value is not a valid integer reading")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"Unsupported integer value type: {type(value).__name__}")
