import asyncio
from typing import Any

from sqlalchemy import select

from app.core.logging import logger
from app.db.session import async_session_factory
from app.models.bill import Bill
from app.models.bill_line_item import BillLineItem
from app.models.meter_reading import MeterReading
from app.services.cache.redis_client import cache_service
from app.services.ocr.engine import ocr_engine
from app.services.ocr.universal_extractor import universal_extractor
from app.services.verification.engine import verification_engine


class ProcessingQueue:
    def __init__(self):
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def start(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def enqueue(self, bill_id: str):
        await self._queue.put(bill_id)

    async def _worker_loop(self):
        while True:
            bill_id = await self._queue.get()
            try:
                await self._process_bill(bill_id)
            except Exception as e:
                logger.error(f"Error processing bill job {bill_id}: {e!s}", exc_info=True)
            finally:
                self._queue.task_done()

    async def _process_bill(self, bill_id: str):
        async with async_session_factory() as session:
            stmt = select(Bill).where(Bill.id == bill_id)
            result = await session.execute(stmt)
            bill = result.scalar_one_or_none()
            if not bill:
                return

            bill.status = "EXTRACTING"
            await session.commit()

            file_bytes = bill.file_data
            if not file_bytes:
                bill.status = "FAILED"
                bill.validation_error = "Document binary data is missing."
                await session.commit()
                return

            ocr_result = ocr_engine.extract(file_bytes, bill.file_name)
            parsed_data: dict[str, Any] = await universal_extractor.parse(ocr_result.text)

            is_valid = parsed_data.get("is_valid_bill", True)
            bill.is_valid_bill = is_valid
            bill.validation_error = parsed_data.get("validation_error")
            bill.bill_summary = parsed_data.get("bill_summary")
            bill.raw_extracted_text = ocr_result.text
            bill.confidence_score = ocr_result.confidence_score

            if not is_valid:
                bill.status = "REJECTED_NON_BILL"
                await session.commit()
                await cache_service.set_cached_bill(
                    bill.file_sha256,
                    {
                        "id": bill.id,
                        "status": bill.status,
                        "is_valid_bill": False,
                        "validation_error": bill.validation_error,
                        "bill_summary": bill.bill_summary,
                        "file_name": bill.file_name,
                    },
                )
                logger.warning(f"Bill {bill.id} rejected: Not a valid electricity bill ({bill.validation_error})")
                return

            readings = parsed_data.get("readings", [])
            line_items = parsed_data.get("line_items", [])
            total_units = float(parsed_data.get("total_units_kwh", 0.0))
            net_amount = float(parsed_data.get("net_amount_due", 0.0))
            power_factor = parsed_data.get("power_factor")

            audit_report = verification_engine.verify(
                readings=readings,
                line_items=line_items,
                total_units_kwh=total_units,
                net_amount_due=net_amount,
                power_factor=power_factor,
                period_start=parsed_data.get("billing_period_start"),
                period_end=parsed_data.get("billing_period_end"),
                bill_date=parsed_data.get("bill_date"),
                due_date=parsed_data.get("due_date"),
            )

            bill.discom_code = parsed_data.get("discom_code", bill.discom_code or "GENERIC")
            bill.discom_name = parsed_data.get("discom_name", bill.discom_name or "State Electricity Board")
            bill.consumer_name = parsed_data.get("consumer_name") or "Consumer"
            bill.consumer_number = parsed_data.get("consumer_number") or bill.file_sha256[:10]
            bill.account_number = parsed_data.get("account_number")
            bill.bill_number = parsed_data.get("bill_number") or f"INV-{bill.file_sha256[:8]}"
            bill.bill_date = parsed_data.get("bill_date")
            bill.due_date = parsed_data.get("due_date")
            bill.billing_period_start = parsed_data.get("billing_period_start")
            bill.billing_period_end = parsed_data.get("billing_period_end")
            bill.contract_demand_kva = parsed_data.get("contract_demand_kva")
            bill.power_factor = parsed_data.get("power_factor")
            bill.tariff_category = parsed_data.get("tariff_category")
            bill.total_units_kwh = total_units
            bill.total_current_charges = float(parsed_data.get("total_current_charges", net_amount))
            bill.net_amount_due = net_amount
            bill.is_math_verified = audit_report.is_valid
            bill.verification_details = audit_report.model_dump()
            bill.status = "VERIFIED" if audit_report.is_valid else "FLAGGED_FOR_REVIEW"

            for r in readings:
                session.add(
                    MeterReading(
                        bill_id=bill.id,
                        meter_number=r.get("meter_number", "METER-1"),
                        reading_type=r.get("reading_type", "kWh"),
                        previous_reading=float(r.get("previous_reading", 0.0)),
                        current_reading=float(r.get("current_reading", 0.0)),
                        difference=float(r.get("difference", 0.0)),
                        multiplying_factor=float(r.get("multiplying_factor", 1.0)),
                        consumed_units=float(r.get("consumed_units", 0.0)),
                    )
                )

            for item in line_items:
                session.add(
                    BillLineItem(
                        bill_id=bill.id,
                        category=item.get("category", "ENERGY_CHARGE"),
                        description=item.get("description", "Energy Charge"),
                        amount=float(item.get("amount", 0.0)),
                    )
                )

            await session.commit()

            cached_payload = {
                "id": bill.id,
                "discom_code": bill.discom_code,
                "discom_name": bill.discom_name,
                "consumer_number": bill.consumer_number,
                "account_number": bill.account_number,
                "consumer_name": bill.consumer_name,
                "bill_number": bill.bill_number,
                "bill_date": bill.bill_date.isoformat() if bill.bill_date else None,
                "billing_period_start": bill.billing_period_start.isoformat() if bill.billing_period_start else None,
                "billing_period_end": bill.billing_period_end.isoformat() if bill.billing_period_end else None,
                "due_date": bill.due_date.isoformat() if bill.due_date else None,
                "total_units_kwh": bill.total_units_kwh,
                "net_amount_due": bill.net_amount_due,
                "power_factor": bill.power_factor,
                "status": bill.status,
                "is_valid_bill": bill.is_valid_bill,
                "validation_error": bill.validation_error,
                "bill_summary": bill.bill_summary,
                "confidence_score": bill.confidence_score,
                "is_math_verified": bill.is_math_verified,
            }
            await cache_service.set_cached_bill(bill.file_sha256, cached_payload)
            logger.info(f"Processed bill {bill.id} - Status: {bill.status}")


task_queue = ProcessingQueue()
