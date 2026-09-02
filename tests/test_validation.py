from __future__ import annotations

from datetime import datetime

import pytest

from medm2garmin.models import BloodPressureReading
from medm2garmin.validation import ValidationError, validate_reading


def test_validate_reading_accepts_reasonable_values() -> None:
    reading = BloodPressureReading(
        timestamp=datetime(2026, 1, 1, 10, 30),
        systolic=120,
        diastolic=80,
        pulse=65,
    )

    validate_reading(reading)


@pytest.mark.parametrize(
    ("systolic", "diastolic", "pulse"),
    [
        (70, 80, 60),
        (290, 80, 60),
        (120, 20, 60),
        (120, 80, 0),
    ],
)
def test_validate_reading_rejects_invalid_values(systolic: int, diastolic: int, pulse: int) -> None:
    reading = BloodPressureReading(
        timestamp=datetime(2026, 1, 1, 10, 30),
        systolic=systolic,
        diastolic=diastolic,
        pulse=pulse,
    )

    with pytest.raises(ValidationError):
        validate_reading(reading)
