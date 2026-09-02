from __future__ import annotations

from medm2garmin.models import BloodPressureReading


class ValidationError(ValueError):
    """Validation error for blood pressure readings."""


def validate_reading(reading: BloodPressureReading) -> None:
    if reading.systolic <= 0 or reading.diastolic <= 0 or reading.pulse <= 0:
        raise ValidationError("Systolic, diastolic and pulse must be positive integers")
    if reading.systolic < reading.diastolic:
        raise ValidationError("Systolic must be greater than or equal to diastolic")
    if not 50 <= reading.systolic <= 280:
        raise ValidationError("Systolic value out of expected range (50-280)")
    if not 30 <= reading.diastolic <= 180:
        raise ValidationError("Diastolic value out of expected range (30-180)")
    if not 25 <= reading.pulse <= 250:
        raise ValidationError("Pulse value out of expected range (25-250)")
