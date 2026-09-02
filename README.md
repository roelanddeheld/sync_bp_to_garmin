# medm2garmin

Synchronize blood pressure measurements from MedM Health to Garmin Connect.

## Why

Garmin Connect supports blood pressure storage, but does not provide a standard end-user import workflow. This project automates synchronization from MedM data sources.

## Features

- Python 3.12+
- Pixi + `pyproject.toml`
- Typed codebase
- Standard `logging`
- Environment-variable configuration with optional TOML config file
- MedM ingestion:
  - preferred official API workflow (when available/configured)
  - CSV export fallback workflow
- Garmin authentication and upload
- Duplicate avoidance using fingerprints and Garmin-side checks
- Synchronization state tracking
- Dry-run mode
- Incremental sync (`sync`)
- Historical backfill (`backfill --days N`)
- Validation (`validate`)
- Status reporting (`status`)

## CLI

```bash
medm2garmin sync
medm2garmin backfill --days 180
medm2garmin validate
medm2garmin status
```

## Configuration

Environment variables:

- `MEDM2GARMIN_MEDM_API_BASE_URL`
- `MEDM2GARMIN_MEDM_API_TOKEN`
- `MEDM2GARMIN_MEDM_CSV_PATH`
- `MEDM2GARMIN_GARMIN_EMAIL`
- `MEDM2GARMIN_GARMIN_PASSWORD`
- `MEDM2GARMIN_GARMIN_TOKEN_DIR`
- `MEDM2GARMIN_STATE_FILE`
- `MEDM2GARMIN_LOG_LEVEL`
- `MEDM2GARMIN_DRY_RUN`
- `MEDM2GARMIN_CONFIG_FILE` (optional TOML config path)

Example config file: [`examples/config.example.toml`](examples/config.example.toml)

## Development with Pixi

```bash
pixi run test
pixi run lint
pixi run typecheck
```

## CI

GitHub Actions workflow runs lint, type-check, and tests.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for diagram and assumptions.

## Notes on external API behavior

Before implementing the Garmin upload layer, this repository reviewed approaches used by existing projects such as `omramin` and `bpconnect`, which both rely on Garmin web API client behavior for blood pressure uploads and duplicate handling patterns.
