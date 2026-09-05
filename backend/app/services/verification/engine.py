from datetime import date

from app.core.constants import FINANCIAL_RULES, POWER_FACTOR_RULES, UNITS_RULES
from app.schemas.verification_dto import DiscrepancyItem, MathVerificationReport


class MathVerificationEngine:
    def __init__(self):
        self.units_epsilon = float(UNITS_RULES.get("tolerance_epsilon", 0.05))
        self.financial_tolerance = float(FINANCIAL_RULES.get("tolerance_rupees", 1.00))
        self.min_pf = float(POWER_FACTOR_RULES.get("min_valid_pf", 0.0))
        self.max_pf = float(POWER_FACTOR_RULES.get("max_valid_pf", 1.0))

    def verify(
        self,
        readings: list[dict],
        line_items: list[dict],
        total_units_kwh: float,
        net_amount_due: float,
        power_factor: float | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
        bill_date: date | None = None,
        due_date: date | None = None,
    ) -> MathVerificationReport:
        discrepancies: list[DiscrepancyItem] = []

        units_verified = True
        if readings:
            for reading in readings:
                prev = float(reading.get("previous_reading", 0.0))
                curr = float(reading.get("current_reading", 0.0))
                mf = float(reading.get("multiplying_factor", 1.0))
                reported_consumed = float(reading.get("consumed_units", 0.0))

                expected_consumed = (curr - prev) * mf
                delta = abs(expected_consumed - reported_consumed)

                if delta > self.units_epsilon:
                    units_verified = False
                    discrepancies.append(
                        DiscrepancyItem(
                            rule_name="METER_READINGS_CONSISTENCY",
                            field_name=f"meter_{reading.get('meter_number', 'unknown')}_units",
                            expected_value=round(expected_consumed, 2),
                            reported_value=round(reported_consumed, 2),
                            discrepancy_delta=round(delta, 2),
                            severity="CRITICAL",
                        )
                    )

        financial_verified = True
        if line_items:
            sum_line_items = sum(float(item.get("amount", 0.0)) for item in line_items)
            diff = abs(sum_line_items - net_amount_due)
            if diff > self.financial_tolerance and net_amount_due > 0:
                financial_verified = False
                discrepancies.append(
                    DiscrepancyItem(
                        rule_name="FINANCIAL_TOTAL_RECONCILIATION",
                        field_name="net_amount_due",
                        expected_value=round(sum_line_items, 2),
                        reported_value=round(net_amount_due, 2),
                        discrepancy_delta=round(diff, 2),
                        severity="WARNING",
                    )
                )

        power_factor_valid = True
        if power_factor is not None:
            effective_pf = power_factor / 100.0 if (10.0 <= power_factor <= 100.0) else power_factor
            if not (self.min_pf <= effective_pf <= self.max_pf):
                power_factor_valid = False
                discrepancies.append(
                    DiscrepancyItem(
                        rule_name="POWER_FACTOR_RANGE",
                        field_name="power_factor",
                        expected_value=0.95,
                        reported_value=round(effective_pf, 3),
                        discrepancy_delta=round(abs(effective_pf - 0.95), 3),
                        severity="CRITICAL",
                    )
                )

        dates_valid = True
        if period_start and period_end and period_start >= period_end:
            dates_valid = False
            discrepancies.append(
                DiscrepancyItem(
                    rule_name="BILLING_PERIOD_CHRONOLOGY",
                    field_name="billing_period_start",
                    expected_value=0.0,
                    reported_value=1.0,
                    discrepancy_delta=1.0,
                    severity="CRITICAL",
                )
            )

        if bill_date and due_date and due_date < bill_date:
            dates_valid = False
            discrepancies.append(
                DiscrepancyItem(
                    rule_name="DUE_DATE_AFTER_BILL_DATE",
                    field_name="due_date",
                    expected_value=0.0,
                    reported_value=1.0,
                    discrepancy_delta=1.0,
                    severity="CRITICAL",
                )
            )

        is_valid = units_verified and power_factor_valid and dates_valid

        return MathVerificationReport(
            is_valid=is_valid,
            units_verified=units_verified,
            financial_verified=financial_verified,
            power_factor_valid=power_factor_valid,
            dates_valid=dates_valid,
            discrepancies=discrepancies,
        )


verification_engine = MathVerificationEngine()
