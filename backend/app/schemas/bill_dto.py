from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.verification_dto import MathVerificationReport


class MeterReadingDTO(BaseModel):
    id: str | None = None
    meter_number: str = Field(..., description="Serial or meter identification number")
    reading_type: str = Field(default="kWh", description="kWh, kVAh, kW_MD, kVA_MD, TOD")
    previous_reading: float = Field(..., description="Previous meter register reading")
    current_reading: float = Field(..., description="Current meter register reading")
    difference: float = Field(..., description="Current minus Previous reading")
    multiplying_factor: float = Field(default=1.0, description="Meter multiplication constant")
    consumed_units: float = Field(..., description="Billed units for this meter register")


class BillLineItemDTO(BaseModel):
    id: str | None = None
    category: str = Field(..., description="FIXED_CHARGE, ENERGY_CHARGE, TOD_SURCHARGE, TAX, PENALTY, REBATE")
    description: str = Field(..., description="Detailed description of charge")
    rate: float | None = Field(default=None, description="Per unit or per kW/kVA rate")
    quantity: float | None = Field(default=None, description="Quantity or connected load")
    amount: float = Field(..., description="Line item charge amount")


class BillUploadResponse(BaseModel):
    bill_id: str = Field(..., description="Unique generated bill identifier")
    file_name: str = Field(..., description="Original uploaded filename")
    status: str = Field(..., description="Current processing pipeline status")
    message: str = Field(..., description="Status summary message")


class BillDetailResponse(BaseModel):
    id: str = Field(..., description="Unique bill record ID")
    discom_code: str | None = Field(default=None, description="Normalized DISCOM code")
    discom_name: str | None = Field(default=None, description="State electricity board name")
    consumer_number: str | None = Field(default=None, description="Consumer ID / Account ID / CA number")
    account_number: str | None = Field(default=None, description="Sub-account or billing ID")
    consumer_name: str | None = Field(default=None, description="Billed entity or individual name")
    billing_address: str | None = Field(default=None, description="Premises service address")

    bill_number: str | None = Field(default=None, description="Official invoice/bill number")
    bill_date: date | None = Field(default=None, description="Date bill was issued")
    billing_period_start: date | None = Field(default=None, description="Billing cycle start")
    billing_period_end: date | None = Field(default=None, description="Billing cycle end")
    due_date: date | None = Field(default=None, description="Payment due date")

    tariff_category: str | None = Field(default=None, description="HT/LT industrial/commercial tariff category")
    sanctioned_load_kw: float | None = Field(default=None, description="Connected or sanctioned load in kW")
    contract_demand_kva: float | None = Field(default=None, description="Contract demand in kVA")
    billed_demand_kva: float | None = Field(default=None, description="Recorded peak demand in kVA")
    power_factor: float | None = Field(default=None, description="Average billed power factor")

    total_units_kwh: float | None = Field(default=None, description="Total active energy consumption in kWh")
    total_units_kvah: float | None = Field(default=None, description="Apparent energy consumption in kVAh")

    total_current_charges: float | None = Field(default=None, description="Net current billing cycle charges")
    net_amount_due: float | None = Field(default=None, description="Total payable amount including taxes and arrears")
    amount_after_due_date: float | None = Field(default=None, description="Late payment surcharge amount")

    status: str = Field(..., description="QUEUED, PARSED, VERIFIED, FLAGGED_FOR_REVIEW")
    is_valid_bill: bool = Field(default=True, description="True if document was recognized as a valid electricity bill")
    validation_error: str | None = Field(default=None, description="Explanation if document is invalid")
    bill_summary: str | None = Field(default=None, description="Plain-English summary of the bill")
    raw_extracted_text: str | None = Field(default=None, description="Complete raw OCR text")
    confidence_score: float = Field(..., description="Overall OCR extraction confidence score (0.0 to 1.0)")
    is_math_verified: bool = Field(..., description="True if mathematical audit passed without anomalies")
    verification_details: MathVerificationReport | None = Field(
        default=None, description="Detailed math verification report"
    )
    bounding_boxes: dict[str, Any] | None = Field(default=None, description="Field coordinate mappings on document")

    readings: list[MeterReadingDTO] = Field(default_factory=list, description="Meter reading entries")
    line_items: list[BillLineItemDTO] = Field(default_factory=list, description="Breakdown line item entries")
    created_at: datetime
    updated_at: datetime


class BillUpdatePayload(BaseModel):
    consumer_name: str | None = None
    consumer_number: str | None = None
    bill_number: str | None = None
    bill_date: date | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    due_date: date | None = None
    total_units_kwh: float | None = None
    net_amount_due: float | None = None
    power_factor: float | None = None
    readings: list[MeterReadingDTO] | None = None
    line_items: list[BillLineItemDTO] | None = None
