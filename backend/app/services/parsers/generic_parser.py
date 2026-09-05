import re
from typing import Any

from app.services.parsers.base import BaseDiscomParser


class GenericFallbackParser(BaseDiscomParser):
    def parse(self, text: str, pages_data: list[Any]) -> dict[str, Any]:
        consumer_name = ""
        name_match = re.search(
            r"(?:Consumer Name|Name of Firm|Name|M/S)\s*[:\-]?\s*([A-Za-z0-9\.\s&]+)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            consumer_name = name_match.group(1).split("\n")[0].strip()

        consumer_number = ""
        num_match = re.search(
            r"(?:Consumer No|Account No|CA No|Consumer Number|K No)\s*[:\-]?\s*([A-Za-z0-9\-]+)",
            text,
            re.IGNORECASE,
        )
        if num_match:
            consumer_number = num_match.group(1).strip()

        bill_number = ""
        bill_match = re.search(
            r"(?:Bill No|Invoice No|Bill Number)\s*[:\-]?\s*([A-Za-z0-9\-]+)",
            text,
            re.IGNORECASE,
        )
        if bill_match:
            bill_number = bill_match.group(1).strip()

        net_amount = 0.0
        amt_match = re.search(
            r"(?:Net Amount Due|Total Due|Net Payable|Bill Amount|Amount Payable)\s*[:\-]?\s*(?:Rs\.?)?\s*([\d,]+\.?\d*)",
            text,
            re.IGNORECASE,
        )
        if amt_match:
            net_amount = self.clean_amount(amt_match.group(1))

        total_units = 0.0
        units_match = re.search(
            r"(?:Total Units|Units Consumed|Billed Units|Consumption)\s*[:\-]?\s*([\d,]+\.?\d*)",
            text,
            re.IGNORECASE,
        )
        if units_match:
            total_units = self.clean_amount(units_match.group(1))

        dates = re.findall(r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{2}-[A-Za-z]{3}-\d{4})\b", text)
        bill_date = self.parse_date(dates[0]) if len(dates) > 0 else None
        due_date = self.parse_date(dates[1]) if len(dates) > 1 else None

        readings: list[dict[str, Any]] = []
        if total_units > 0:
            readings.append(
                {
                    "meter_number": "METER-1",
                    "reading_type": "kWh",
                    "previous_reading": 0.0,
                    "current_reading": total_units,
                    "difference": total_units,
                    "multiplying_factor": 1.0,
                    "consumed_units": total_units,
                }
            )

        return {
            "discom_code": "GENERIC",
            "discom_name": "State Electricity Board",
            "consumer_name": consumer_name,
            "consumer_number": consumer_number,
            "account_number": consumer_number,
            "bill_number": bill_number,
            "bill_date": bill_date,
            "due_date": due_date,
            "billing_period_start": None,
            "billing_period_end": None,
            "total_units_kwh": total_units,
            "total_current_charges": net_amount,
            "net_amount_due": net_amount,
            "readings": readings,
            "line_items": [
                {
                    "category": "NET_CHARGES",
                    "description": "Total Billed Electricity Charges",
                    "amount": net_amount,
                }
            ]
            if net_amount > 0
            else [],
        }
