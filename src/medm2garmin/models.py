from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BloodPressureReading:
    timestamp: datetime
    systolic: int
    diastolic: int
    pulse: int
    source_id: str | None = None
    note: str = ""

    def fingerprint(self) -> str:
        payload = (
            f"{self.timestamp.isoformat()}|{self.systolic}|{self.diastolic}|"
            f"{self.pulse}|{self.source_id or ''}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
