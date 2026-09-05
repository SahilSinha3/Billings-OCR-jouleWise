import json
from pathlib import Path
from typing import Any

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


def _load_json_config(filename: str) -> dict[str, Any]:
    config_path = CONFIGS_DIR / filename
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


DISCOMS_CONFIG = _load_json_config("discoms.json")
STATUS_CODES_CONFIG = _load_json_config("status_codes.json")
MATH_RULES_CONFIG = _load_json_config("math_rules.json")

DISCOMS_LIST = DISCOMS_CONFIG.get("discoms", [])
JOB_STATUSES = STATUS_CODES_CONFIG.get("job_statuses", {})
ERROR_CODES = STATUS_CODES_CONFIG.get("error_codes", {})
UNITS_RULES = MATH_RULES_CONFIG.get("units_calculation", {})
FINANCIAL_RULES = MATH_RULES_CONFIG.get("financial_reconciliation", {})
POWER_FACTOR_RULES = MATH_RULES_CONFIG.get("power_factor", {})
