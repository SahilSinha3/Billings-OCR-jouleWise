import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any


class BaseDiscomParser(ABC):
    @abstractmethod
    def parse(self, text: str, pages_data: list[Any]) -> dict[str, Any]:
        pass

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
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        return None

    def find_word_below(
        self,
        pages_data: list[Any],
        header_keyword: str,
        tolerance_x: float = 35.0,
        max_y_dist: float = 50.0,
    ) -> str | None:
        for page in pages_data:
            words = getattr(page, "words", [])
            header_boxes = [w for w in words if header_keyword.lower() in getattr(w, "text", "").lower()]
            if not header_boxes:
                continue

            h = header_boxes[0]
            candidates = [
                w
                for w in words
                if abs(getattr(w, "x", 0) - getattr(h, "x", 0)) <= tolerance_x
                and 5.0 <= (getattr(w, "y", 0) - getattr(h, "y", 0)) <= max_y_dist
            ]
            candidates.sort(key=lambda w: getattr(w, "y", 0))

            for cand in candidates:
                txt = getattr(cand, "text", "").strip()
                if txt and not any(ign in txt.lower() for ign in ["(kva)", "(kw)", "rs", "%"]):
                    return txt
        return None
