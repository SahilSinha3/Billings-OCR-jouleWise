import hashlib
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BillNotFoundError
from app.db.session import get_db_session
from app.models.bill import Bill
from app.models.bill_line_item import BillLineItem
from app.models.meter_reading import MeterReading
from app.schemas.bill_dto import (
    BillDetailResponse,
    BillLineItemDTO,
    BillUpdatePayload,
    BillUploadResponse,
    MeterReadingDTO,
)
from app.schemas.verification_dto import MathVerificationReport
from app.services.cache.redis_client import cache_service
from app.services.verification.engine import verification_engine
from app.workers.queue import task_queue

router = APIRouter()


def _build_bill_response(b: Bill) -> BillDetailResponse:
    ver_report = MathVerificationReport(**b.verification_details) if b.verification_details else None
    return BillDetailResponse(
        id=b.id,
        discom_code=b.discom_code,
        discom_name=b.discom_name,
        consumer_number=b.consumer_number,
        account_number=b.account_number,
        consumer_name=b.consumer_name,
        billing_address=b.billing_address,
        bill_number=b.bill_number,
        bill_date=b.bill_date,
        billing_period_start=b.billing_period_start,
        billing_period_end=b.billing_period_end,
        due_date=b.due_date,
        tariff_category=b.tariff_category,
        sanctioned_load_kw=b.sanctioned_load_kw,
        contract_demand_kva=b.contract_demand_kva,
        billed_demand_kva=b.billed_demand_kva,
        power_factor=b.power_factor,
        total_units_kwh=b.total_units_kwh,
        total_units_kvah=b.total_units_kvah,
        total_current_charges=b.total_current_charges,
        net_amount_due=b.net_amount_due,
        amount_after_due_date=b.amount_after_due_date,
        status=b.status,
        is_valid_bill=b.is_valid_bill,
        validation_error=b.validation_error,
        bill_summary=b.bill_summary,
        raw_extracted_text=b.raw_extracted_text,
        confidence_score=b.confidence_score,
        is_math_verified=b.is_math_verified,
        verification_details=ver_report,
        bounding_boxes=b.bounding_boxes,
        readings=[
            MeterReadingDTO(
                id=r.id,
                meter_number=r.meter_number,
                reading_type=r.reading_type,
                previous_reading=r.previous_reading,
                current_reading=r.current_reading,
                difference=r.difference,
                multiplying_factor=r.multiplying_factor,
                consumed_units=r.consumed_units,
            )
            for r in b.readings
        ],
        line_items=[
            BillLineItemDTO(
                id=li.id,
                category=li.category,
                description=li.description,
                rate=li.rate,
                quantity=li.quantity,
                amount=li.amount,
            )
            for li in b.line_items
        ],
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


@router.post(
    "/upload",
    response_model=BillUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Electricity Bill",
    description="Upload a state electricity bill PDF or image directly into PostgreSQL storage for asynchronous OCR extraction and verification.",
)
async def upload_bill(
    file: UploadFile,
    session: AsyncSession = Depends(get_db_session),
) -> BillUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    sha256_hash = hashlib.sha256(contents).hexdigest()

    # Deduplication & cache check
    stmt = select(Bill).where(Bill.file_sha256 == sha256_hash)
    result = await session.execute(stmt)
    existing_bill = result.scalar_one_or_none()
    if existing_bill:
        return BillUploadResponse(
            bill_id=existing_bill.id,
            file_name=existing_bill.file_name,
            status=existing_bill.status,
            message="Document already processed (retrieved from database/cache).",
        )

    mime_type = file.content_type or ("application/pdf" if file.filename.lower().endswith(".pdf") else "image/png")

    bill = Bill(
        discom_code="PENDING",
        discom_name="Detecting...",
        consumer_number="PENDING",
        consumer_name="Processing...",
        bill_number=f"DOC-{sha256_hash[:8]}",
        file_data=contents,
        file_name=file.filename,
        mime_type=mime_type,
        file_sha256=sha256_hash,
        status="QUEUED",
        total_units_kwh=0.0,
        total_current_charges=0.0,
        net_amount_due=0.0,
    )

    session.add(bill)
    await session.commit()
    await session.refresh(bill)

    await task_queue.enqueue(bill.id)

    return BillUploadResponse(
        bill_id=bill.id,
        file_name=file.filename,
        status=bill.status,
        message="Bill uploaded successfully and queued for extraction.",
    )


@router.post(
    "/bulk-upload",
    response_model=list[BillUploadResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk Upload Electricity Bills",
    description="Upload multiple electricity bill PDFs/images simultaneously for batch ingestion and processing.",
)
async def bulk_upload_bills(
    files: list[UploadFile],
    session: AsyncSession = Depends(get_db_session),
) -> list[BillUploadResponse]:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided.",
        )

    responses: list[BillUploadResponse] = []
    for file in files:
        if not file.filename:
            continue
        contents = await file.read()
        if len(contents) == 0:
            continue

        sha256_hash = hashlib.sha256(contents).hexdigest()
        stmt = select(Bill).where(Bill.file_sha256 == sha256_hash)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            responses.append(
                BillUploadResponse(
                    bill_id=existing.id,
                    file_name=existing.file_name,
                    status=existing.status,
                    message="Document already processed (retrieved from cache).",
                )
            )
            continue

        mime_type = file.content_type or ("application/pdf" if file.filename.lower().endswith(".pdf") else "image/png")

        bill = Bill(
            discom_code="PENDING",
            discom_name="Detecting...",
            consumer_number="PENDING",
            consumer_name="Processing...",
            bill_number=f"DOC-{sha256_hash[:8]}",
            file_data=contents,
            file_name=file.filename,
            mime_type=mime_type,
            file_sha256=sha256_hash,
            status="QUEUED",
            total_units_kwh=0.0,
            total_current_charges=0.0,
            net_amount_due=0.0,
        )

        session.add(bill)
        await session.commit()
        await session.refresh(bill)

        await task_queue.enqueue(bill.id)

        responses.append(
            BillUploadResponse(
                bill_id=bill.id,
                file_name=file.filename,
                status=bill.status,
                message="Queued for extraction.",
            )
        )

    return responses


@router.get(
    "/{bill_id}/file",
    summary="Stream Original Bill File",
    description="Stream the original uploaded PDF or image file directly from PostgreSQL BYTEA storage.",
)
async def get_bill_file(
    bill_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    stmt = select(Bill).where(Bill.id == bill_id)
    result = await session.execute(stmt)
    bill = result.scalar_one_or_none()
    if not bill or not bill.file_data:
        raise BillNotFoundError(bill_id)

    return StreamingResponse(
        io.BytesIO(bill.file_data),
        media_type=bill.mime_type or "application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{bill.file_name}"',
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.get(
    "",
    response_model=list[BillDetailResponse],
    summary="List All Bills",
    description="Retrieve paginated list of bills with optional status filtering.",
)
async def list_bills(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[BillDetailResponse]:
    stmt = (
        select(Bill)
        .options(selectinload(Bill.readings), selectinload(Bill.line_items))
        .order_by(Bill.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if status_filter:
        stmt = stmt.where(Bill.status == status_filter.upper())

    result = await session.execute(stmt)
    bills = result.scalars().all()

    return [_build_bill_response(b) for b in bills]


@router.get(
    "/{bill_id}",
    response_model=BillDetailResponse,
    summary="Get Bill Details",
    description="Retrieve full extracted details, line items, and math verification report for a specific bill.",
)
async def get_bill(
    bill_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> BillDetailResponse:
    stmt = select(Bill).options(selectinload(Bill.readings), selectinload(Bill.line_items)).where(Bill.id == bill_id)
    result = await session.execute(stmt)
    b = result.scalar_one_or_none()
    if not b:
        raise BillNotFoundError(bill_id)

    return _build_bill_response(b)


@router.put(
    "/{bill_id}",
    response_model=BillDetailResponse,
    summary="Update and Verify Bill",
    description="Manually edit extracted bill fields with real-time math re-verification.",
)
async def update_bill(
    bill_id: str,
    payload: BillUpdatePayload,
    session: AsyncSession = Depends(get_db_session),
) -> BillDetailResponse:
    stmt = select(Bill).options(selectinload(Bill.readings), selectinload(Bill.line_items)).where(Bill.id == bill_id)
    result = await session.execute(stmt)
    bill = result.scalar_one_or_none()
    if not bill:
        raise BillNotFoundError(bill_id)

    if payload.consumer_name is not None:
        bill.consumer_name = payload.consumer_name
    if payload.consumer_number is not None:
        bill.consumer_number = payload.consumer_number
    if payload.bill_number is not None:
        bill.bill_number = payload.bill_number
    if payload.bill_date is not None:
        bill.bill_date = payload.bill_date
    if payload.billing_period_start is not None:
        bill.billing_period_start = payload.billing_period_start
    if payload.billing_period_end is not None:
        bill.billing_period_end = payload.billing_period_end
    if payload.due_date is not None:
        bill.due_date = payload.due_date
    if payload.total_units_kwh is not None:
        bill.total_units_kwh = payload.total_units_kwh
    if payload.net_amount_due is not None:
        bill.net_amount_due = payload.net_amount_due
    if payload.power_factor is not None:
        bill.power_factor = payload.power_factor

    audit = verification_engine.verify(
        readings=[
            {
                "previous_reading": r.previous_reading,
                "current_reading": r.current_reading,
                "multiplying_factor": r.multiplying_factor,
                "consumed_units": r.consumed_units,
                "meter_number": r.meter_number,
            }
            for r in bill.readings
        ],
        line_items=[{"amount": li.amount} for li in bill.line_items],
        total_units_kwh=bill.total_units_kwh,
        net_amount_due=bill.net_amount_due,
        power_factor=bill.power_factor,
        period_start=bill.billing_period_start,
        period_end=bill.billing_period_end,
        bill_date=bill.bill_date,
        due_date=bill.due_date,
    )

    bill.is_math_verified = audit.is_valid
    bill.verification_details = audit.model_dump()
    bill.status = "VERIFIED" if audit.is_valid else "FLAGGED_FOR_REVIEW"

    await session.commit()
    return await get_bill(bill_id=bill.id, session=session)


@router.delete(
    "/{bill_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a Bill",
    description="Delete an individual bill and its associated meter readings and line items, invalidating cache.",
)
async def delete_bill(
    bill_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(Bill).where(Bill.id == bill_id)
    result = await session.execute(stmt)
    bill = result.scalar_one_or_none()
    if not bill:
        raise BillNotFoundError(bill_id)

    # Invalidate Redis cache
    if bill.file_sha256:
        await cache_service.delete_cached_bill(bill.file_sha256)

    await session.delete(bill)
    await session.commit()
    return {"status": "success", "message": f"Bill {bill_id} deleted successfully."}


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    summary="Clear All Bills",
    description="Delete all bills, readings, and line items from the database and flush Redis cache.",
)
async def clear_all_bills(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    await session.execute(delete(BillLineItem))
    await session.execute(delete(MeterReading))
    await session.execute(delete(Bill))
    await session.commit()

    # Clear all cached bills from Redis
    await cache_service.clear_all()
    return {"status": "success", "message": "All bills and caches cleared successfully."}
