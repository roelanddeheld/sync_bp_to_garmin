from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from medm2garmin.models import BloodPressureReading

LOG = logging.getLogger(__name__)


class GarminClient:
    def __init__(self, *, email: str | None, secret: str | None, token_dir: Path) -> None:
        self._email = email
        self._secret = secret
        self._token_dir = token_dir
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from garminconnect import Garmin
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("garminconnect dependency is required for Garmin upload") from exc

        self._token_dir.mkdir(parents=True, exist_ok=True)
        client = Garmin()
        try:
            client.login(str(self._token_dir))
            LOG.debug("Logged in to Garmin using token directory")
        except Exception as exc:  # noqa: BLE001
            if not self._email or not self._secret:
                raise RuntimeError(
                    "Garmin login failed with token cache and no email/password were provided"
                ) from exc
            client = Garmin(self._email, self._secret)
            client.login()
            client.garth.dump(str(self._token_dir))
            LOG.debug("Logged in to Garmin using credentials and refreshed token cache")

        self._client = client
        return client

    def list_existing_fingerprints(self, start: datetime, end: datetime) -> set[str]:
        client = self._ensure_client()
        data = client.get_blood_pressure(start.date().isoformat(), end.date().isoformat())
        summaries = data.get("measurementSummaries", [])
        fingerprints: set[str] = set()
        for summary in summaries:
            measurements = summary.get("measurements", [])
            if not isinstance(measurements, list):
                continue
            for m in measurements:
                if not isinstance(m, dict):
                    continue
                ts_raw = m.get("measurementTimestampLocal")
                if not isinstance(ts_raw, str):
                    continue
                reading = BloodPressureReading(
                    timestamp=datetime.fromisoformat(ts_raw),
                    systolic=int(m["systolic"]),
                    diastolic=int(m["diastolic"]),
                    pulse=int(m["pulse"]),
                    source_id=None,
                )
                fingerprints.add(reading.fingerprint())
        return fingerprints

    def upload(self, reading: BloodPressureReading, *, dry_run: bool) -> None:
        if dry_run:
            LOG.info(
                "Dry-run: would upload %s %s/%s pulse=%s",
                reading.timestamp.isoformat(),
                reading.systolic,
                reading.diastolic,
                reading.pulse,
            )
            return

        client = self._ensure_client()
        client.set_blood_pressure(
            reading.systolic,
            reading.diastolic,
            reading.pulse,
            reading.timestamp.isoformat(),
            notes=reading.note,
        )
