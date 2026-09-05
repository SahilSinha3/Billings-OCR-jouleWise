from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.bill import Bill


class MeterReading(BaseModel):
    __tablename__ = "meter_readings"

    bill_id: Mapped[str] = mapped_column(String(36), ForeignKey("bills.id", ondelete="CASCADE"), index=True)
    meter_number: Mapped[str] = mapped_column(String(100))
    reading_type: Mapped[str] = mapped_column(String(50), default="kWh")

    previous_reading: Mapped[float] = mapped_column(Float, default=0.0)
    current_reading: Mapped[float] = mapped_column(Float, default=0.0)
    difference: Mapped[float] = mapped_column(Float, default=0.0)
    multiplying_factor: Mapped[float] = mapped_column(Float, default=1.0)
    consumed_units: Mapped[float] = mapped_column(Float, default=0.0)

    bill: Mapped["Bill"] = relationship("Bill", back_populates="readings")
