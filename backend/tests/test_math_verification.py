from datetime import date

from app.services.verification.engine import MathVerificationEngine


def test_units_consistency_valid():
    engine = MathVerificationEngine()
    readings = [
        {
            "meter_number": "M-1",
            "previous_reading": 1000.0,
            "current_reading": 1500.0,
            "multiplying_factor": 1.0,
            "consumed_units": 500.0,
        }
    ]
    report = engine.verify(
        readings=readings,
        line_items=[],
        total_units_kwh=500.0,
        net_amount_due=3500.0,
        power_factor=0.95,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        bill_date=date(2026, 4, 5),
        due_date=date(2026, 4, 25),
    )
    assert report.is_valid is True
    assert report.units_verified is True
    assert report.power_factor_valid is True
    assert len(report.discrepancies) == 0


def test_units_consistency_mismatch_detected():
    engine = MathVerificationEngine()
    readings = [
        {
            "meter_number": "M-1",
            "previous_reading": 1000.0,
            "current_reading": 1500.0,
            "multiplying_factor": 1.0,
            "consumed_units": 600.0,
        }
    ]
    report = engine.verify(
        readings=readings,
        line_items=[],
        total_units_kwh=600.0,
        net_amount_due=3500.0,
        power_factor=0.95,
    )
    assert report.is_valid is False
    assert report.units_verified is False
    assert len(report.discrepancies) == 1
    assert report.discrepancies[0].rule_name == "METER_READINGS_CONSISTENCY"


def test_power_factor_invalid():
    engine = MathVerificationEngine()
    report = engine.verify(
        readings=[],
        line_items=[],
        total_units_kwh=100.0,
        net_amount_due=1000.0,
        power_factor=1.45,
    )
    assert report.is_valid is False
    assert report.power_factor_valid is False
    assert any(d.rule_name == "POWER_FACTOR_RANGE" for d in report.discrepancies)
