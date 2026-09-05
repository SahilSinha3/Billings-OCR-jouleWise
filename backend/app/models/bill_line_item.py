from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.bill import Bill


class BillLineItem(BaseModel):
    __tablename__ = "bill_line_items"

    bill_id: Mapped[str] = mapped_column(String(36), ForeignKey("bills.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(255))
    rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)

    bill: Mapped["Bill"] = relationship("Bill", back_populates="line_items")
