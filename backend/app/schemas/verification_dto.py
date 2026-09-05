from pydantic import BaseModel, Field


class DiscrepancyItem(BaseModel):
    rule_name: str = Field(..., description="Name of the failed validation rule")
    field_name: str = Field(..., description="Target field with inconsistency")
    expected_value: float = Field(..., description="Mathematically computed expected value")
    reported_value: float = Field(..., description="Value extracted from document")
    discrepancy_delta: float = Field(..., description="Absolute or percentage difference")
    severity: str = Field(..., description="CRITICAL, WARNING, or INFO")


class MathVerificationReport(BaseModel):
    is_valid: bool = Field(..., description="True if all critical checks passed")
    units_verified: bool = Field(..., description="True if (Current - Previous) * MF == Consumed Units")
    financial_verified: bool = Field(..., description="True if line items sum up to net payable")
    power_factor_valid: bool = Field(..., description="True if PF is between 0.0 and 1.0")
    dates_valid: bool = Field(..., description="True if billing dates are in proper chronology")
    discrepancies: list[DiscrepancyItem] = Field(
        default_factory=list, description="List of detected mathematical anomalies"
    )
