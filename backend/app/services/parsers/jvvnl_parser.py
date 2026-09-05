import re
from typing import Any

from app.services.parsers.base import BaseDiscomParser


class JvvnlParser(BaseDiscomParser):
    def parse(self, text: str, pages_data: list[Any]) -> dict[str, Any]:
        consumer_name = ""
        name_match = re.search(r"Consumer Name & Address\.\s*\n([^\n]+)", text)
        if name_match:
            consumer_name = name_match.group(1).replace("null", "").strip()

        account_number = ""
        acc_match = re.search(r"Account No\.\s*:\s*([A-Za-z0-9]+)", text)
        if acc_match:
            account_number = acc_match.group(1).strip()
        else:
            kno_match = re.search(r"K\s*No:\s*(\d+)", text)
            if kno_match:
                account_number = kno_match.group(1).strip()

        bill_number = ""
        bill_match = re.search(r"Bill No:\s*([A-Za-z0-9\-]+)", text)
        if bill_match:
            bill_number = bill_match.group(1).strip()

        net_payable = 0.0
        pay_match = re.search(r"Net Payable Amount\s*\n\s*([\d,]+\.?\d*)", text)
        if pay_match:
            net_payable = self.clean_amount(pay_match.group(1))
        else:
            alt_pay = re.search(r"Net Payable Amount[^\n\d]*(\d{5,8})", text)
            if alt_pay:
                net_payable = self.clean_amount(alt_pay.group(1))

        bill_date = None
        due_date = None
        period_start = None

        dates_row = re.search(
            r"(\d{2}-[A-Za-z]{3}-\d{4})\s+(\d{2}-\d{2}-\d{4})\s+(\d{2}-\d{2}-\d{4})",
            text,
        )
        if dates_row:
            period_start = self.parse_date(dates_row.group(1))
            bill_date = self.parse_date(dates_row.group(2))
            due_date = self.parse_date(dates_row.group(3))
        else:
            all_dates = re.findall(r"\b(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\b", text)
            if len(all_dates) >= 2:
                bill_date = self.parse_date(all_dates[0])
                due_date = self.parse_date(all_dates[1])

        contract_demand = None
        cd_val = self.find_word_below(pages_data, "Cont.Demand")
        if cd_val:
            try:
                contract_demand = float(cd_val)
            except ValueError:
                contract_demand = None
        if contract_demand is None:
            cd_m = re.search(r"Cont\.Demand[^\n\d]*(\d+\.?\d*)", text)
            if cd_m:
                try:
                    contract_demand = float(cd_m.group(1))
                except ValueError:
                    contract_demand = None

        power_factor = None
        pf_val = self.find_word_below(pages_data, "P.F")
        if pf_val:
            try:
                power_factor = float(pf_val)
            except ValueError:
                power_factor = None
        if power_factor is None:
            pf_m = re.search(r"Av\.\s*P\.F[^\n\d]*(\d+\.\d{2,3})", text)
            if pf_m:
                try:
                    power_factor = float(pf_m.group(1))
                except ValueError:
                    power_factor = None

        readings: list[dict[str, Any]] = []
        total_units = 0.0

        r_matches = re.findall(
            r"(\d{5,8})\s+(\d)\s+(KWH|KVAH|KVA)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)",
            text,
        )
        for r in r_matches:
            mtr_no, _, r_type, curr, prev, diff, mf, cons = r
            curr_f = self.clean_amount(curr)
            prev_f = self.clean_amount(prev)
            diff_f = self.clean_amount(diff)
            mf_f = self.clean_amount(mf) or 1.0
            cons_f = self.clean_amount(cons)

            readings.append(
                {
                    "meter_number": mtr_no,
                    "reading_type": r_type,
                    "previous_reading": prev_f,
                    "current_reading": curr_f,
                    "difference": diff_f,
                    "multiplying_factor": mf_f,
                    "consumed_units": cons_f,
                }
            )
            if r_type.upper() == "KWH":
                total_units = cons_f

        if total_units == 0.0:
            units_m = re.search(r"Net KWH Cons\.[^\n]*\n\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
            if units_m:
                total_units = self.clean_amount(units_m.group(1))

        line_items: list[dict[str, Any]] = []
        charge_items = [
            ("Energy Charges", r"Energy Charges[^\n]*\n\s*([\d\.]+)"),
            ("Fixed Charges", r"Fixed Charges[^\n]*\n\s*([\d\.]+)"),
            ("Power Factor Incentive", r"Power Factor Sur\./Inct\.[^\n]*\n\s*([\-\d\.]+)"),
            ("TOD Surcharge", r"TOD Surcharge[^\n]*\n\s*([\d\.]+)"),
            ("Electricity Duty", r"CURRENT ED[^\n]*\n\s*([\d\.]+)"),
            ("Water Conservation Cess", r"CURRENT WCC[^\n]*\n\s*([\d\.]+)"),
        ]
        for desc, pat in charge_items:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                amt = self.clean_amount(m.group(1))
                if amt != 0.0:
                    line_items.append(
                        {
                            "category": desc.upper().replace(" ", "_"),
                            "description": desc,
                            "amount": amt,
                        }
                    )

        if not line_items and net_payable > 0:
            line_items.append(
                {
                    "category": "NET_PAYABLE_CHARGES",
                    "description": "Net Payable Amount",
                    "amount": net_payable,
                }
            )

        return {
            "discom_code": "JVVNL",
            "discom_name": "JAIPUR VIDYUT VITRAN NIGAM LIMITED",
            "consumer_name": consumer_name,
            "consumer_number": account_number,
            "account_number": account_number,
            "bill_number": bill_number,
            "bill_date": bill_date,
            "due_date": due_date,
            "billing_period_start": period_start,
            "billing_period_end": bill_date,
            "tariff_category": "HT-5 Large Industrial",
            "contract_demand_kva": contract_demand,
            "power_factor": power_factor,
            "total_units_kwh": total_units,
            "total_current_charges": net_payable,
            "net_amount_due": net_payable,
            "readings": readings,
            "line_items": line_items,
        }
