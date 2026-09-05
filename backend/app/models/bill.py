from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Date, Float, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.bill_line_item import BillLineItem
    from app.models.meter_reading import MeterReading


class Bill(BaseModel):
    __tablename__ = "bills"

    discom_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    discom_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    consumer_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consumer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    bill_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    bill_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    tariff_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sanctioned_load_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    contract_demand_kva: Mapped[float | None] = mapped_column(Float, nullable=True)
    billed_demand_kva: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_factor: Mapped[float | None] = mapped_column(Float, nullable=True)

    total_units_kwh: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    total_units_kvah: Mapped[float | None] = mapped_column(Float, nullable=True)

    total_current_charges: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    net_amount_due: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    amount_after_due_date: Mapped[float | None] = mapped_column(Float, nullable=True)

    file_data: Mapped[bytes] = mapped_column(LargeBinary)
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)

    status: Mapped[str] = mapped_column(String(50), default="QUEUED", index=True)
    is_valid_bill: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bill_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_math_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    bounding_boxes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    readings: Mapped[list["MeterReading"]] = relationship(
        "MeterReading",
        back_populates="bill",
        cascade="all, delete-orphan",
    )
    line_items: Mapped[list["BillLineItem"]] = relationship(
        "BillLineItem",
        back_populates="bill",
        cascade="all, delete-orphan",
    )
