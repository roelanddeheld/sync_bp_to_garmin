from __future__ import annotations

from datetime import datetime

from medm2garmin.models import BloodPressureReading
from medm2garmin.state import SyncState
from medm2garmin.syncer import sync_readings


class FakeSource:
    def __init__(self, readings: list[BloodPressureReading]) -> None:
        self._readings = readings

    def get(self, *, since: datetime | None, until: datetime | None) -> list[BloodPressureReading]:
        data = self._readings
        if since is not None:
            data = [r for r in data if r.timestamp >= since]
        if until is not None:
            data = [r for r in data if r.timestamp <= until]
        return data


class FakeGarmin:
    def __init__(self, existing: set[str] | None = None) -> None:
        self._existing = existing or set()
        self.uploaded: list[BloodPressureReading] = []

    def list_existing_fingerprints(self, start: datetime, end: datetime) -> set[str]:
        _ = (start, end)
        return set(self._existing)

    def upload(self, reading: BloodPressureReading, *, dry_run: bool) -> None:
        if not dry_run:
            self.uploaded.append(reading)


class FailingListGarmin(FakeGarmin):
    def list_existing_fingerprints(self, start: datetime, end: datetime) -> set[str]:
        raise AssertionError("Should not query Garmin existing data in dry-run mode")


def test_sync_skips_known_duplicates_and_uploads_new_values() -> None:
    existing = BloodPressureReading(datetime(2026, 1, 1, 9, 0), 120, 80, 65)
    new = BloodPressureReading(datetime(2026, 1, 2, 9, 0), 121, 81, 66)

    source = FakeSource([existing, new])
    garmin = FakeGarmin(existing={existing.fingerprint()})
    state = SyncState(uploaded_fingerprints=set(), last_synced_at=None)

    updated, result = sync_readings(
        source=source,
        garmin=garmin,
        state=state,
        since=None,
        until=None,
        dry_run=False,
    )

    assert [r.fingerprint() for r in garmin.uploaded] == [new.fingerprint()]
    assert result.uploaded == 1
    assert result.skipped_duplicates == 1
    assert len(updated.uploaded_fingerprints) == 2


def test_sync_dry_run_does_not_require_garmin_existing_lookup() -> None:
    reading = BloodPressureReading(datetime(2026, 1, 3, 9, 0), 119, 79, 64)
    source = FakeSource([reading])
    garmin = FailingListGarmin()
    state = SyncState(uploaded_fingerprints=set(), last_synced_at=None)

    updated, result = sync_readings(
        source=source,
        garmin=garmin,
        state=state,
        since=None,
        until=None,
        dry_run=True,
    )

    assert result.uploaded == 1
    assert reading.fingerprint() in updated.uploaded_fingerprints
