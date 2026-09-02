from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    medm_api_base_url: str | None
    medm_api_token: str | None
    medm_csv_path: Path | None
    garmin_email: str | None
    garmin_secret: str | None
    garmin_token_dir: Path
    state_file: Path
    log_level: str
    dry_run: bool

    @property
    def has_medm_api(self) -> bool:
        return bool(self.medm_api_base_url and self.medm_api_token)


def _load_file_values(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    flat: dict[str, str] = {}
    for section in ("medm", "garmin", "sync"):
        section_data = data.get(section, {})
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                flat[f"{section}.{key}"] = str(value)
    return flat


def load_settings() -> Settings:
    config_file = os.getenv("MEDM2GARMIN_CONFIG_FILE")
    config_path = Path(config_file).expanduser() if config_file else None
    file_values = _load_file_values(config_path)

    medm_api_base_url = os.getenv("MEDM2GARMIN_MEDM_API_BASE_URL") or file_values.get(
        "medm.api_base_url"
    )
    medm_api_token = os.getenv("MEDM2GARMIN_MEDM_API_TOKEN") or file_values.get("medm.api_token")
    medm_csv_path_raw = os.getenv("MEDM2GARMIN_MEDM_CSV_PATH") or file_values.get("medm.csv_path")
    garmin_email = os.getenv("MEDM2GARMIN_GARMIN_EMAIL") or file_values.get("garmin.email")
    garmin_secret = os.getenv("MEDM2GARMIN_GARMIN_PASSWORD") or file_values.get("garmin.password")

    token_dir_raw = os.getenv("MEDM2GARMIN_GARMIN_TOKEN_DIR") or file_values.get(
        "garmin.token_dir", ".medm2garmin_tokens"
    )
    state_file_raw = os.getenv("MEDM2GARMIN_STATE_FILE") or file_values.get(
        "sync.state_file", ".medm2garmin_state.json"
    )
    log_level = os.getenv("MEDM2GARMIN_LOG_LEVEL") or file_values.get("sync.log_level", "INFO")
    dry_run = _parse_bool(
        os.getenv("MEDM2GARMIN_DRY_RUN") or file_values.get("sync.dry_run"),
        default=False,
    )

    medm_csv_path = Path(medm_csv_path_raw).expanduser() if medm_csv_path_raw else None

    return Settings(
        medm_api_base_url=medm_api_base_url,
        medm_api_token=medm_api_token,
        medm_csv_path=medm_csv_path,
        garmin_email=garmin_email,
        garmin_secret=garmin_secret,
        garmin_token_dir=Path(token_dir_raw).expanduser(),
        state_file=Path(state_file_raw).expanduser(),
        log_level=log_level,
        dry_run=dry_run,
    )
