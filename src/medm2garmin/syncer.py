from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from medm2garmin.models import BloodPressureReading
from medm2garmin.state import SyncState
from medm2garmin.validation import ValidationError, validate_reading

LOG = logging.getLogger(__name__)


class ReadingSource(Protocol):
    def get(self, *, since: datetime | None, until: datetime | None) -> list[BloodPressureReading]:
        ...


class GarminUploader(Protocol):
    def list_existing_fingerprints(self, start: datetime, end: datetime) -> set[str]:
        ...

    def upload(self, reading: BloodPressureReading, *, dry_run: bool) -> None:
        ...


@dataclass(slots=True)
class SyncResult:
    retrieved: int
    uploaded: int
    skipped_duplicates: int
    skipped_invalid: int


def sync_readings(
    *,
    source: ReadingSource,
    garmin: GarminUploader,
    state: SyncState,
    since: datetime | None,
    until: datetime | None,
    dry_run: bool,
) -> tuple[SyncState, SyncResult]:
    readings = source.get(since=since, until=until)
    if not readings:
        return state, SyncResult(retrieved=0, uploaded=0, skipped_duplicates=0, skipped_invalid=0)

    effective_start = min(r.timestamp for r in readings)
    effective_end = max(r.timestamp for r in readings)
    garmin_fingerprints = (
        set() if dry_run else garmin.list_existing_fingerprints(effective_start, effective_end)
    )

    uploaded = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    known = set(state.uploaded_fingerprints)
    known.update(garmin_fingerprints)

    for reading in sorted(readings, key=lambda r: r.timestamp):
        try:
            validate_reading(reading)
        except ValidationError as exc:
            skipped_invalid += 1
            LOG.warning("Skipping invalid reading at %s: %s", reading.timestamp.isoformat(), exc)
            continue

        fingerprint = reading.fingerprint()
        if fingerprint in known:
            skipped_duplicates += 1
            continue

        garmin.upload(reading, dry_run=dry_run)
        uploaded += 1
        known.add(fingerprint)

    state.uploaded_fingerprints = known
    state.last_synced_at = datetime.now(tz=effective_end.tzinfo)
    return state, SyncResult(
        retrieved=len(readings),
        uploaded=uploaded,
        skipped_duplicates=skipped_duplicates,
        skipped_invalid=skipped_invalid,
    )
