from __future__ import annotations

from datetime import datetime

from medm2garmin.state import StateStore, SyncState


def test_state_roundtrip(tmp_path) -> None:
    state_file = tmp_path / "state.json"
    store = StateStore(state_file)
    state = SyncState(
        uploaded_fingerprints={"a", "b"},
        last_synced_at=datetime(2026, 1, 2, 3, 4, 5),
    )

    store.save(state)
    loaded = store.load()

    assert loaded.uploaded_fingerprints == {"a", "b"}
    assert loaded.last_synced_at == datetime(2026, 1, 2, 3, 4, 5)
