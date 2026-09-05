import re
from typing import Any

from app.services.parsers.base import BaseDiscomParser


class ApdclParser(BaseDiscomParser):
    def parse(self, text: str, pages_data: list[Any]) -> dict[str, Any]:
        consumer_name = ""
        name_match = re.search(r"Consumer Name:\s*([^\n]+)", text, re.IGNORECASE)
        if name_match:
            consumer_name = name_match.group(1).strip()

        consumer_number = ""
        num_match = re.search(r"Consumer Number:\s*(\d+)", text, re.IGNORECASE)
        if num_match:
            consumer_number = num_match.group(1).strip()

        bill_number = ""
        bill_match = re.search(r"Bill Number:\s*(\d+)", text, re.IGNORECASE)
        if bill_match:
            bill_number = bill_match.group(1).strip()

        bill_amount = 0.0
        amt_match = re.search(r"Bill Amount:\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if amt_match:
            bill_amount = self.clean_amount(amt_match.group(1))

        bill_date = None
        bdate_match = re.search(r"Bill Date:\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4})", text, re.IGNORECASE)
        if bdate_match:
            bill_date = self.parse_date(bdate_match.group(1))

        due_date = None
        ddate_match = re.search(r"Due Date:\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4})", text, re.IGNORECASE)
        if ddate_match:
            due_date = self.parse_date(ddate_match.group(1))

        period_start = None
        period_end = None
        period_match = re.search(
            r"Bill Period:\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4})\s*To\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4})",
            text,
            re.IGNORECASE,
        )
        if period_match:
            period_start = self.parse_date(period_match.group(1))
            period_end = self.parse_date(period_match.group(2))

        readings: list[dict[str, Any]] = []
        total_units = 0.0

        billable_match = re.search(r"Billable Units in\s*KWh\s*[:\n\s]*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if billable_match:
            total_units = self.clean_amount(billable_match.group(1))

        reading_blocks = re.findall(
            r"(KWH\([^\)]+\)|Current Reading|Previous Reading)\s*([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)",
            text,
        )
        for block in reading_blocks:
            lbl, prev, curr, diff, units = block
            p_val = self.clean_amount(prev)
            c_val = self.clean_amount(curr)
            u_val = self.clean_amount(units)
            readings.append(
                {
                    "meter_number": "METER-1",
                    "reading_type": lbl,
                    "previous_reading": p_val,
                    "current_reading": c_val,
                    "difference": round(c_val - p_val, 2),
                    "multiplying_factor": 1.0,
                    "consumed_units": u_val or round(c_val - p_val, 2),
                }
            )

        if not readings and total_units > 0:
            readings.append(
                {
                    "meter_number": "MAIN-METER",
                    "reading_type": "KWh",
                    "previous_reading": 0.0,
                    "current_reading": total_units,
                    "difference": total_units,
                    "multiplying_factor": 1.0,
                    "consumed_units": total_units,
                }
            )

        return {
            "discom_code": "APDCL",
            "discom_name": "Assam Power Distribution Company Limited",
            "consumer_name": consumer_name,
            "consumer_number": consumer_number,
            "account_number": consumer_number,
            "bill_number": bill_number,
            "bill_date": bill_date,
            "due_date": due_date,
            "billing_period_start": period_start,
            "billing_period_end": period_end,
            "total_units_kwh": total_units,
            "total_current_charges": bill_amount,
            "net_amount_due": bill_amount,
            "readings": readings,
            "line_items": [
                {
                    "category": "TOTAL_ENERGY_CHARGES",
                    "description": "Total Billed Energy Charges",
                    "amount": bill_amount,
                }
            ]
            if bill_amount > 0
            else [],
        }
