from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class SyncState:
    uploaded_fingerprints: set[str]
    last_synced_at: datetime | None


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> SyncState:
        if not self._path.exists():
            return SyncState(uploaded_fingerprints=set(), last_synced_at=None)
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        uploaded = payload.get("uploaded_fingerprints", [])
        last_synced_raw = payload.get("last_synced_at")
        return SyncState(
            uploaded_fingerprints=set(uploaded),
            last_synced_at=datetime.fromisoformat(last_synced_raw) if last_synced_raw else None,
        )

    def save(self, state: SyncState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "uploaded_fingerprints": sorted(state.uploaded_fingerprints),
            "last_synced_at": state.last_synced_at.isoformat() if state.last_synced_at else None,
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
