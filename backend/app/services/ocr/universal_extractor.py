import json
import re
from datetime import date, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.core.constants import DISCOMS_LIST
from app.core.logging import logger


class UniversalBillExtractor:
    BILL_SIGNALS = [
        "electricity bill",
        "energy bill",
        "ht bill",
        "lt bill",
        "power distribution",
        "consumer name",
        "consumer number",
        "account number",
        "meter reading",
        "meter no",
        "units in kwh",
        "kwh",
        "kvah",
        "net payable",
        "net amount",
        "due date",
        "tariff",
        "discom",
        "jvvnl",
        "apdcl",
        "gescom",
        "bescom",
        "msedcl",
        "tangedco",
        "uppcl",
    ]

    NON_BILL_KEYWORDS = [
        "register map",
        "user manual",
        "instruction manual",
        "specifications",
        "modbus",
        "consolidated register map",
        "author: pd sw team",
        "datasheet",
    ]

    def validate_is_electricity_bill(self, text: str) -> tuple[bool, str | None]:
        lower_text = text.lower()

        # Check for explicit manual/datasheet keywords
        manual_matches = [k for k in self.NON_BILL_KEYWORDS if k in lower_text]
        if len(manual_matches) >= 2:
            return (
                False,
                f"Document recognized as technical manual or datasheet ({', '.join(manual_matches)}), not an electricity bill.",
            )

        # Count positive electricity billing signals
        signal_count = sum(1 for s in self.BILL_SIGNALS if s in lower_text)
        if signal_count < 2:
            return (
                False,
                "Uploaded document does not contain recognizable electricity billing indicators. Please upload an electricity utility bill.",
            )

        return True, None

    def clean_amount(self, raw_val: str | None) -> float:
        if not raw_val:
            return 0.0
        cleaned = re.sub(r"[^\d.]", "", raw_val)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def parse_date(self, raw_date_str: str | None) -> date | None:
        if not raw_date_str:
            return None
        cleaned = raw_date_str.strip()
        date_formats = [
            "%d-%b-%Y",
            "%d-%B-%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d-%m-%y",
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        return None

    def detect_discom(self, text: str) -> tuple[str, str]:
        lower_text = text.lower()
        if "assam power distribution" in lower_text or "apdcl" in lower_text:
            return "APDCL", "Assam Power Distribution Company Limited"
        if "jaipur vidyut" in lower_text or "jvvnl" in lower_text:
            return "JVVNL", "JAIPUR VIDYUT VITRAN NIGAM LIMITED"
        if "gulbarga electricity" in lower_text or "gescom" in lower_text:
            return "GESCOM", "Gulbarga Electricity Supply Company Limited"

        for d in DISCOMS_LIST:
            code = d.get("code", "GENERIC")
            name = d.get("name", "State Electricity Board")
            keywords = d.get("keywords", [])
            if any(k.lower() in lower_text for k in keywords):
                return code, name

        return "GENERIC", "State Electricity Distribution Company"

    def extract_heuristic_fields(self, text: str) -> dict[str, Any]:
        discom_code, discom_name = self.detect_discom(text)
        # Normalize OCR spaces around dots (e.g. 399066 .0000 -> 399066.0000)
        clean_text = re.sub(r"(\d+)\s*\.\s*(\d+)", r"\1.\2", text)

        # 1. Consumer Name
        consumer_name = ""
        name_patterns = [
            r"Consumer Name:\s*([^\n\r]+?)(?=\s+Consumer Number|\s+Bill Amount|\n|$)",
            r"Name of the Firm\s*:\s*([^\n@]+?)(?=\s*@|\n|$)",
            r"(M/S\s+[A-Za-z0-9\.\s]+?)(?=\s+null|\n|,|\s{3,})",
            r"(?:Customer Name|Billed To)\s*[:\-]?\s*([^\n@]{3,60})",
            r"Consumer Name & Address\.\s*\n(?:null\s*)?([^\n,]+)",
        ]
        for pat in name_patterns:
            m = re.search(pat, clean_text, re.IGNORECASE)
            if m:
                cand = m.group(1).replace("null", "").strip()
                if len(cand) > 3 and not any(
                    ign in cand.lower() for ign in ["number", "address", "ind.area", "reading date", "date payment"]
                ):
                    consumer_name = cand
                    break

        # 2. Account / Consumer Number
        consumer_number = ""
        acc_patterns = [
            r"Consumer Number:\s*([A-Za-z0-9]+)",
            r"Acc No:\s*([A-Za-z0-9]+)",
            r"K\s*No:\s*(\d+)",
            r"R\.R\.\s*No:\s*([A-Za-z0-9\s\-]+?)(?=\s+Last|\n|$)",
            r"(?:Consumer No|CA Number)\s*[:\-]?\s*(\d{8,15})",
        ]
        for pat in acc_patterns:
            m = re.search(pat, clean_text, re.IGNORECASE)
            if m:
                consumer_number = m.group(1).strip()
                break

        # 3. Bill Number
        bill_number = ""
        bill_patterns = [
            r"Bill Number:\s*([A-Za-z0-9\-]+)",
            r"Bill No:\s*([A-Za-z0-9\-]+)",
            r"Invoice\s*No\s*[:\-]?\s*([A-Za-z0-9\-]{5,20})",
        ]
        for pat in bill_patterns:
            m = re.search(pat, clean_text, re.IGNORECASE)
            if m:
                bill_number = m.group(1).strip()
                break

        # 4. Dates
        bill_date = None
        due_date = None
        period_start = None
        period_end = None

        # JVVNL 3-date pattern (Reading Date, Issue Date, Due Date)
        jvvnl_dates = re.search(
            r"(\d{2}-[A-Za-z]{3}-\d{4})\s*\|?\s*(\d{2}-\d{2}-\d{4})\s+(\d{2}-\d{2}-\d{4})",
            clean_text,
        )
        if jvvnl_dates:
            period_start = self.parse_date(jvvnl_dates.group(1))
            bill_date = self.parse_date(jvvnl_dates.group(2))
            due_date = self.parse_date(jvvnl_dates.group(3))
        else:
            # APDCL period
            period_m = re.search(
                r"Bill Period:\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4})\s*To\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4})",
                clean_text,
                re.IGNORECASE,
            )
            if period_m:
                period_start = self.parse_date(period_m.group(1))
                period_end = self.parse_date(period_m.group(2))

            # GESCOM month
            month_m = re.search(r"Month\s*of\s*([A-Za-z]+)\s*(\d{4})", clean_text, re.IGNORECASE)
            year_val = None
            if month_m:
                m_name, m_yr = month_m.groups()
                year_val = int(m_yr)
                if not period_start:
                    period_start = self.parse_date(f"01-{m_name}-{m_yr}")
                    period_end = self.parse_date(f"31-{m_name}-{m_yr}")

            bdate_m = re.search(
                r"(?:Bill Date|Date of Bill|Date:\s*|Bill Issue Date)\s*[:\-]?\s*([0-9]{1,2}[\.\-\/][A-Za-z0-9]{2,9}[\.\-\/][0-9]{4})",
                clean_text,
                re.IGNORECASE,
            )
            if bdate_m:
                bill_date = self.parse_date(bdate_m.group(1))
                if bill_date and not year_val:
                    year_val = bill_date.year

            due_m = re.search(
                r"(?:Due Date|Last Date of Payment)\s*[:\-]?\s*([0-9]{1,2}(?:st|nd|rd|th)?\s*(?:of)?\s*[A-Za-z0-9]{2,9}[\.\-\/][0-9]{4}|[0-9]{1,2}(?:st|nd|rd|th)?\s*(?:of)?\s*[A-Za-z]+)",
                clean_text,
                re.IGNORECASE,
            )
            if due_m:
                raw_due = due_m.group(1)
                due_date = self.parse_date(raw_due)
                if not due_date and year_val:
                    clean_tokens = re.findall(r"\d{1,2}|[A-Za-z]+", raw_due)
                    if len(clean_tokens) >= 2:
                        due_date = self.parse_date(f"{clean_tokens[0]}-{clean_tokens[1]}-{year_val}")

        # 5. Net Amount Due
        net_amount_due = 0.0
        amt_patterns = [
            r"Say[^\d]*(\d{6,10})",
            r"=\s*(\d{7,10})",
            r"Grand Total[^\n]*?(\d{7,9}[\s\.]\d{2})",
            r"(?:Grand Total|Net Payable Amount|Net Amount Due|Total Due)[^\n=]*?(?:=|\:|Rs\.?|₹)?\s*(\d{6,10})",
            r"Bill Amount:\s*([\d,]+\.?\d*)",
            r"Net Payable Amount\s*\n\s*([\d,]+\.?\d*)",
            r"Payable amount before due date[^\d]*([\d,]+\.?\d*)",
        ]
        for pat in amt_patterns:
            m = re.search(pat, clean_text, re.IGNORECASE)
            if m:
                raw = m.group(1).replace(" ", ".")
                val = self.clean_amount(raw)
                if val > 0:
                    net_amount_due = val
                    break

        # 6. Total Units (kWh)
        total_units = 0.0
        units_patterns = [
            r"Billable Units in\s*KWh\s*[:\n\s]*([\d,]+\.?\d*)",
            r"Net KWH Cons\.[^\n]*\n\s*([\d,]+\.?\d*)",
            r"(?:IMainmR|Main\s*MR)[^\n]*?(\d{6,8})",
            r"(\d{6,8})\|?Units",
            r"Total[^\d]*(\d{6,8})\s*(?:Units|kWh|KWh)?",
            r"Total Units Consumed[^\d]*([\d,]+\.?\d*)",
        ]
        for pat in units_patterns:
            m = re.search(pat, clean_text, re.IGNORECASE)
            if m:
                val = self.clean_amount(m.group(1))
                if val > 0:
                    total_units = val
                    break

        # 7. Contract Demand & Power Factor
        contract_demand = None
        cd_m = re.search(r"Contract(?:ed)?\s*Demand[^\d]*(\d+\.?\d*)", clean_text, re.IGNORECASE)
        if cd_m:
            contract_demand = self.clean_amount(cd_m.group(1)) or None

        power_factor = None
        pf_m = re.search(r"(?:Bpf|Av\.\s*P\.F|Power Factor)[,\s:]*([\d\.]+)", clean_text, re.IGNORECASE)
        if pf_m:
            try:
                val = float(pf_m.group(1))
                if 0.0 <= val <= 1.0:
                    power_factor = val
            except ValueError:
                pass

        # 8. Tariff Category
        tariff_category = None
        t_m = re.search(r"Tariff(?: Category)?:\s*([A-Za-z0-9\(\)\s\-]{3,40})", clean_text, re.IGNORECASE)
        if t_m:
            tariff_category = t_m.group(1).strip()

        # 9. Meter Readings
        readings: list[dict[str, Any]] = []
        r_matches = re.findall(
            r"(\d{5,8})\s+(\d)\s+(KWH|KVAH|KVA)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)",
            clean_text,
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
            if r_type.upper() == "KWH" and total_units == 0.0:
                total_units = cons_f

        if not readings and total_units > 0:
            readings.append(
                {
                    "meter_number": consumer_number or "MAIN-METER",
                    "reading_type": "KWh",
                    "previous_reading": 0.0,
                    "current_reading": total_units,
                    "difference": total_units,
                    "multiplying_factor": 1.0,
                    "consumed_units": total_units,
                }
            )

        line_items = (
            [
                {
                    "category": "NET_CURRENT_CHARGES",
                    "description": "Total Billed Electricity Charges",
                    "amount": net_amount_due,
                }
            ]
            if net_amount_due > 0
            else []
        )

        return {
            "discom_code": discom_code,
            "discom_name": discom_name,
            "consumer_name": consumer_name,
            "consumer_number": consumer_number,
            "account_number": consumer_number,
            "bill_number": bill_number,
            "bill_date": bill_date,
            "due_date": due_date,
            "billing_period_start": period_start,
            "billing_period_end": period_end,
            "tariff_category": tariff_category,
            "contract_demand_kva": contract_demand,
            "power_factor": power_factor,
            "total_units_kwh": total_units,
            "total_current_charges": net_amount_due,
            "net_amount_due": net_amount_due,
            "readings": readings,
            "line_items": line_items,
        }

    async def _call_gemini(self, prompt: str) -> dict[str, Any] | None:
        if not settings.GEMINI_API_KEY:
            return None
        for model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json",
                    },
                }
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text_resp = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                            return json.loads(text_resp)
            except Exception as e:
                logger.info(f"Gemini {model} call attempt failed: {e!s}")
        return None

    async def _call_ollama(self, prompt: str) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                if res.status_code == 200:
                    raw_resp = res.json().get("response", "{}")
                    return json.loads(raw_resp)
        except Exception as e:
            logger.info(f"Ollama {settings.OLLAMA_MODEL} call failed: {e!s}")
        return None

    def build_deterministic_summary(self, data: dict[str, Any]) -> str:
        c_name = data.get("consumer_name") or "the consumer"
        c_no = data.get("consumer_number") or data.get("account_number") or ""
        c_str = f" ({c_no})" if c_no else ""
        d_name = data.get("discom_name") or "the state electricity distribution utility"
        amt_val = data.get("net_amount_due", 0.0)
        units_val = data.get("total_units_kwh", 0.0)
        due_val = data.get("due_date")
        pf_val = data.get("power_factor")

        amt_str = f"₹{amt_val:,.2f}" if amt_val > 0 else "the billed amount"
        units_str = f"{units_val:,.0f} kWh" if units_val > 0 else "metered consumption"
        due_str = f" with payment due on {due_val}" if due_val else ""
        pf_str = f" (operating power factor: {pf_val})" if pf_val else ""

        return (
            f"Electricity utility bill for {c_name}{c_str} issued by {d_name}. "
            f"Total billed active energy is {units_str}{pf_str} and the net amount due is {amt_str}{due_str}."
        )

    async def generate_bill_summary_and_fallback(self, text: str, data: dict[str, Any]) -> tuple[dict[str, Any], str]:
        prompt = (
            f"You are an enterprise utility bill auditor. Based on the OCR text of an electricity bill below:\n"
            f"1. Generate a concise, plain-English summary (2-3 sentences) in easy terms explaining: "
            f"who the customer is, which utility issued it, total units (kWh) consumed, net amount due, and due date.\n"
            f"2. Extract or confirm: consumer_name, net_amount_due (float), total_units_kwh (float), "
            f"due_date (YYYY-MM-DD), account_number (str).\n"
            f"Respond ONLY in valid JSON format with keys: 'summary', 'consumer_name', 'net_amount_due', "
            f"'total_units_kwh', 'due_date', 'account_number'.\n\n"
            f"OCR TEXT:\n{text[:3500]}"
        )

        llm_json: dict[str, Any] | None = None
        # 1. Try Gemini 2.5 Flash if configured
        if settings.GEMINI_API_KEY:
            llm_json = await self._call_gemini(prompt)

        # 2. Fall back to local Ollama Llama 3.2
        if not llm_json and settings.OLLAMA_BASE_URL:
            llm_json = await self._call_ollama(prompt)

        summary: str | None = None
        if llm_json and isinstance(llm_json, dict):
            if llm_json.get("summary"):
                summary = str(llm_json["summary"]).strip()
            if not data.get("consumer_name") and llm_json.get("consumer_name"):
                data["consumer_name"] = str(llm_json["consumer_name"]).strip()
            if not data.get("net_amount_due") and llm_json.get("net_amount_due"):
                try:
                    data["net_amount_due"] = float(llm_json["net_amount_due"])
                    data["total_current_charges"] = data["net_amount_due"]
                except (ValueError, TypeError):
                    pass
            if (not data.get("total_units_kwh") or data.get("total_units_kwh") == 0.0) and llm_json.get(
                "total_units_kwh"
            ):
                try:
                    data["total_units_kwh"] = float(llm_json["total_units_kwh"])
                except (ValueError, TypeError):
                    pass
            if not data.get("due_date") and llm_json.get("due_date"):
                parsed_d = self.parse_date(str(llm_json["due_date"]))
                if parsed_d:
                    data["due_date"] = parsed_d
            if not data.get("account_number") and llm_json.get("account_number"):
                data["account_number"] = str(llm_json["account_number"]).strip()
                if not data.get("consumer_number"):
                    data["consumer_number"] = data["account_number"]

        if not summary:
            summary = self.build_deterministic_summary(data)

        return data, summary

    def parse_fast(self, text: str) -> dict[str, Any]:
        is_valid, validation_err = self.validate_is_electricity_bill(text)
        if not is_valid:
            return {
                "is_valid_bill": False,
                "validation_error": validation_err,
                "discom_code": "INVALID",
                "discom_name": "Non-Utility Document",
                "consumer_name": "",
                "consumer_number": "",
                "bill_number": "",
                "total_units_kwh": 0.0,
                "net_amount_due": 0.0,
                "readings": [],
                "line_items": [],
                "bill_summary": validation_err,
            }

        extracted_data = self.extract_heuristic_fields(text)
        extracted_data["is_valid_bill"] = True
        extracted_data["validation_error"] = None
        extracted_data["bill_summary"] = self.build_deterministic_summary(extracted_data)
        return extracted_data

    async def parse(self, text: str) -> dict[str, Any]:
        fast_data = self.parse_fast(text)
        if not fast_data.get("is_valid_bill", True):
            return fast_data

        updated_data, summary = await self.generate_bill_summary_and_fallback(text, fast_data)
        updated_data["bill_summary"] = summary
        return updated_data


universal_extractor = UniversalBillExtractor()
