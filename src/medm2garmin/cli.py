from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from medm2garmin.config import Settings, load_settings
from medm2garmin.garmin import GarminClient
from medm2garmin.logging_config import configure_logging
from medm2garmin.medm import MedMClient, load_csv_readings
from medm2garmin.models import BloodPressureReading
from medm2garmin.state import StateStore
from medm2garmin.syncer import ReadingSource, sync_readings
from medm2garmin.validation import ValidationError, validate_reading

LOG = logging.getLogger(__name__)


class ConfiguredReadingSource(ReadingSource):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._medm_client = MedMClient(
            api_base_url=settings.medm_api_base_url,
            api_token=settings.medm_api_token,
        )

    def get(self, *, since: datetime | None, until: datetime | None) -> list[BloodPressureReading]:
        if self._settings.has_medm_api:
            try:
                LOG.info("Fetching blood pressure data from MedM API")
                return self._medm_client.fetch_readings(since=since, until=until)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("MedM API retrieval failed, falling back to CSV if configured: %s", exc)

        if self._settings.medm_csv_path is None:
            raise RuntimeError(
                "No MedM source configured. Set MedM API settings or MEDM2GARMIN_MEDM_CSV_PATH"
            )

        LOG.info("Loading blood pressure data from CSV export: %s", self._settings.medm_csv_path)
        readings = load_csv_readings(self._settings.medm_csv_path)
        if since is not None:
            readings = [r for r in readings if r.timestamp >= since]
        if until is not None:
            readings = [r for r in readings if r.timestamp <= until]
        return readings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="medm2garmin")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Run incremental synchronization")
    sync_parser.add_argument("--since", type=str, default=None, help="ISO-8601 lower bound")
    sync_parser.add_argument("--until", type=str, default=None, help="ISO-8601 upper bound")
    sync_parser.add_argument("--dry-run", action="store_true", help="Log actions without uploading")

    backfill_parser = subparsers.add_parser("backfill", help="Backfill historical data")
    backfill_parser.add_argument("--days", type=int, default=90, help="Days to backfill")
    backfill_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without uploading",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate MedM readings")
    validate_parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional CSV path override",
    )

    subparsers.add_parser("status", help="Show synchronization status")

    return parser.parse_args()


def _parse_iso8601(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def run_sync(
    settings: Settings,
    *,
    since: datetime | None,
    until: datetime | None,
    dry_run: bool,
) -> int:
    state_store = StateStore(settings.state_file)
    state = state_store.load()

    if since is None:
        since = state.last_synced_at

    source = ConfiguredReadingSource(settings)
    garmin = GarminClient(
        email=settings.garmin_email,
        secret=settings.garmin_secret,
        token_dir=settings.garmin_token_dir,
    )

    state, result = sync_readings(
        source=source,
        garmin=garmin,
        state=state,
        since=since,
        until=until,
        dry_run=dry_run,
    )
    state_store.save(state)
    LOG.info("Sync result: %s", asdict(result))
    return 0


def run_backfill(settings: Settings, *, days: int, dry_run: bool) -> int:
    since = datetime.now() - timedelta(days=days)
    return run_sync(settings, since=since, until=None, dry_run=dry_run)


def run_validate(settings: Settings, *, csv_path: Path | None) -> int:
    if csv_path is not None:
        readings = load_csv_readings(csv_path)
    elif settings.medm_csv_path is not None:
        readings = load_csv_readings(settings.medm_csv_path)
    else:
        source = ConfiguredReadingSource(settings)
        readings = source.get(since=None, until=None)

    failures: list[dict[str, str]] = []
    for reading in readings:
        try:
            validate_reading(reading)
        except ValidationError as exc:
            failures.append({"timestamp": reading.timestamp.isoformat(), "error": str(exc)})

    if failures:
        print(json.dumps({"valid": False, "errors": failures}, indent=2))
        return 1

    print(json.dumps({"valid": True, "count": len(readings)}, indent=2))
    return 0


def run_status(settings: Settings) -> int:
    state = StateStore(settings.state_file).load()
    payload = {
        "state_file": str(settings.state_file),
        "last_synced_at": state.last_synced_at.isoformat() if state.last_synced_at else None,
        "tracked_uploaded_fingerprints": len(state.uploaded_fingerprints),
    }
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    args = parse_args()
    settings = load_settings()
    configure_logging(settings.log_level)

    if args.command == "sync":
        return run_sync(
            settings,
            since=_parse_iso8601(args.since),
            until=_parse_iso8601(args.until),
            dry_run=bool(args.dry_run or settings.dry_run),
        )
    if args.command == "backfill":
        return run_backfill(
            settings,
            days=args.days,
            dry_run=bool(args.dry_run or settings.dry_run),
        )
    if args.command == "validate":
        return run_validate(settings, csv_path=args.csv)
    if args.command == "status":
        return run_status(settings)

    raise AssertionError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
