from pathlib import Path

import pytest

from app.services.ocr.engine import ocr_engine
from app.services.ocr.universal_extractor import universal_extractor

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "Datasets"


@pytest.mark.asyncio
async def test_extract_apdcl_scnel_bill():
    pdf_path = DATASETS_DIR / "Energy Bill Mar-26 SCNEL.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    ocr_result = ocr_engine.extract(file_bytes, pdf_path.name)
    assert len(ocr_result.text) > 100

    data = universal_extractor.parse_fast(ocr_result.text)
    assert data["is_valid_bill"] is True
    assert data["discom_code"] == "APDCL"
    assert data["consumer_name"] == "Star Cement North-East Limited"
    assert data["consumer_number"] == "006010060944"
    assert data["bill_number"] == "900237539"
    assert str(data["due_date"]) == "2026-04-27"
    assert data["total_units_kwh"] == 306161.46
    assert data["net_amount_due"] == 12968205.00
    assert data["power_factor"] == 99.00
    assert len(data["readings"]) == 3


@pytest.mark.asyncio
async def test_extract_apdcl_bill():
    pdf_path = DATASETS_DIR / "Energy Bill Mar-26 SCL.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    ocr_result = ocr_engine.extract(file_bytes, pdf_path.name)
    assert len(ocr_result.text) > 100

    data = await universal_extractor.parse(ocr_result.text)
    assert data["is_valid_bill"] is True
    assert data["discom_code"] == "APDCL"
    assert "CEMENT MANUFACTURING COMPANY" in data["consumer_name"]
    assert data["consumer_number"] == "006000002141"
    assert data["net_amount_due"] == 17306353.00


@pytest.mark.asyncio
async def test_extract_scanned_gescom_bill():
    pdf_path = DATASETS_DIR / "EB BILL_06JUN2025.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    ocr_result = ocr_engine.extract(file_bytes, pdf_path.name)
    assert len(ocr_result.text) > 100

    data = await universal_extractor.parse(ocr_result.text)
    assert data["is_valid_bill"] is True
    assert data["discom_code"] == "GESCOM"
    assert "Chettinad Cement" in data["consumer_name"]
    assert "EHT" in data["consumer_number"]
    assert data["power_factor"] == 0.94
    assert data["net_amount_due"] == 10855959.00


@pytest.mark.asyncio
async def test_non_bill_guardrail_rejection():
    pdf_path = DATASETS_DIR / "EM6400RegMap_V01.01.02.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    ocr_result = ocr_engine.extract(file_bytes, pdf_path.name)
    data = await universal_extractor.parse(ocr_result.text)
    assert data["is_valid_bill"] is False
    assert "technical manual" in data["validation_error"].lower() or "datasheet" in data["validation_error"].lower()
