from app.core.constants import DISCOMS_LIST
from app.services.parsers.apdcl_parser import ApdclParser
from app.services.parsers.base import BaseDiscomParser
from app.services.parsers.generic_parser import GenericFallbackParser
from app.services.parsers.gescom_parser import GescomParser
from app.services.parsers.jvvnl_parser import JvvnlParser


class DiscomParserFactory:
    def __init__(self):
        self._parsers: dict[str, BaseDiscomParser] = {
            "APDCL": ApdclParser(),
            "JVVNL": JvvnlParser(),
            "GESCOM": GescomParser(),
            "GENERIC": GenericFallbackParser(),
        }

    def detect_and_get_parser(self, text: str) -> BaseDiscomParser:
        normalized_text = text.lower()

        if "assam power distribution" in normalized_text or "apdcl" in normalized_text:
            return self._parsers["APDCL"]

        if "jaipur vidyut" in normalized_text or "jvvnl" in normalized_text:
            return self._parsers["JVVNL"]

        if "gulbarga electricity" in normalized_text or "gescom" in normalized_text:
            return self._parsers["GESCOM"]

        for discom in DISCOMS_LIST:
            code = discom.get("code")
            keywords: list[str] = discom.get("keywords", [])
            if any(k.lower() in normalized_text for k in keywords):
                if code in self._parsers:
                    return self._parsers[code]

        return self._parsers["GENERIC"]


parser_factory = DiscomParserFactory()
