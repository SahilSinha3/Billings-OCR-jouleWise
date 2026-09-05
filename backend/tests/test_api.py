from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "Datasets"


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ocr_engine" in data


@pytest.mark.asyncio
async def test_discoms_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/discoms")
    assert response.status_code == 200
    discoms = response.json()
    assert isinstance(discoms, list)
    assert len(discoms) > 0
    codes = [d["code"] for d in discoms]
    assert "BESCOM" in codes
    assert "MSEDCL" in codes


@pytest.mark.asyncio
async def test_settings_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/settings")
        assert res.status_code == 200
        data = res.json()
        assert "tesseract_status" in data
        assert "ollama_status" in data

        # Test updating settings
        update_res = await ac.post(
            "/api/v1/settings",
            json={"ollama_model": "llama3.2"},
        )
        assert update_res.status_code == 200
        assert update_res.json()["ollama_model"] == "llama3.2"

        # Test connection endpoint
        test_res = await ac.post(
            "/api/v1/settings/test",
            json={"provider": "ollama"},
        )
        assert test_res.status_code == 200
        assert "success" in test_res.json()


@pytest.mark.asyncio
async def test_bill_upload_and_stream():
    transport = ASGITransport(app=app)
    pdf_path = DATASETS_DIR / "Energy Bill Mar-26 SCL.pdf"
    assert pdf_path.exists()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with open(pdf_path, "rb") as f:
            files = {"file": ("Energy Bill Mar-26 SCL.pdf", f, "application/pdf")}
            upload_res = await ac.post("/api/v1/bills/upload", files=files)
        assert upload_res.status_code == 202
        bill_data = upload_res.json()
        bill_id = bill_data["bill_id"]

        # Test streaming the file directly from PostgreSQL BYTEA storage
        file_res = await ac.get(f"/api/v1/bills/{bill_id}/file")
        assert file_res.status_code == 200
        assert len(file_res.content) > 1000
        assert file_res.headers.get("content-type") == "application/pdf"
