# JouleWise

JouleWise is an automated data extraction, mathematical audit, and verification platform for Indian state electricity distribution bills (HT/LT commercial & industrial tariffs).

It replaces manual bill data entry with a deterministic OCR pipeline, database-backed artifact storage, and an automated tariff audit engine.

---

## Architecture Overview

```
                          ┌──────────────────────┐
                          │   Client / Frontend  │
                          │ (Next.js Monochrome) │
                          └──────────┬───────────┘
                                     │ Multipart Upload (Single / Bulk)
                                     ▼
                          ┌──────────────────────┐
                          │   FastAPI Gateway    │
                          └──────────┬───────────┘
                                     │ SHA-256 Hash
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
       [ Cache Hit (<5ms) ]                    [ Cache Miss / Processing ]
       Redis (redis://:6379)                   PostgreSQL 17 (BYTEA Blob)
                 │                                       │
                 └──────────────┐                        ▼
                                │              asyncio.Queue Worker
                                │                        │
                                │                        ▼
                                │              Poppler (300 DPI Render)
                                │                        │
                                │                        ▼
                                │               Pure Tesseract OCR
                                │                        │
                                │                        ▼
                                │             Universal Bill Extractor
                                │             (Guardrail + Regex Heuristics)
                                │                        │
                                │            ┌───────────┴───────────┐
                                │            ▼                       ▼
                                │       Optional LLM           No LLM / Offline
                                │    (Gemini 2.5 / Ollama)    (Pure Tesseract OCR)
                                │            │                       │
                                │            └───────────┬───────────┘
                                │                        ▼
                                │             Math Verification Engine
                                │             (Delta, Slabs, PF, Dates)
                                │                        │
                                └────────────────────────┴──► PostgreSQL + Redis
```

### Core Design Decisions

1. **High-Speed Decoupled Tesseract OCR Pipeline (~2.2s)**
   Document pages are rasterized at 200 DPI using multi-threaded Poppler (`thread_count=4`) and converted to 8-bit grayscale. Text lines and token bounding boxes are reconstructed from a single neural Tesseract LSTM pass (`--oem 1`). Multi-page conversion is capped to the first 5 pages to maintain high throughput. OCR text extraction, field parsing, and deterministic math audit complete in ~2.2 seconds.

2. **Progressive AI Summarization with Deterministic Fallbacks**
   Summary generation is decoupled from the core OCR and audit pipeline. While pure Tesseract OCR and mathematical audit yield verified metrics immediately, plain-English summaries are synthesized asynchronously via Gemini 2.5 Flash or local Ollama (Llama 3.2). If offline or unconfigured, an instant deterministic summary is generated so extraction never blocks.

3. **Zero Local Disk Persistence (PostgreSQL 17 `BYTEA` Storage)**
   Bills are persisted directly into PostgreSQL as binary blobs (`LargeBinary` / `BYTEA`). No local temporary files or shared storage directories are touched. The backend provides a streaming endpoint (`GET /api/v1/bills/{id}/file`) so the frontend iframe renders the document directly from the database.

4. **Redis Deduplication & Caching**
   Uploaded documents are hashed via SHA-256 upon arrival. If an identical file was already processed, the verified data payload is returned directly from local Redis in under 5ms without triggering re-OCR.

5. **Screen-Blurring Global State Loader & CSS Modules**
   The frontend is built using pure **CSS Modules** (`page.module.css`) with Apple-inspired monochrome light-mode styling (`#fafafa` background and crisp `#09090b` typography). While documents are processing, a full-screen backdrop-blur shield obscures the workspace with an animated 5-phase ticker, preventing unverified or placeholder data from rendering until extraction completes.

6. **Full CSV Data Export & Download**
   - **All Bills**: `GET /api/v1/bills/export/csv` exports the entire repository of bills with consumption metrics and audit statuses.
   - **Individual Bill**: `GET /api/v1/bills/{id}/export/csv` exports a structured audit report including register breakdowns and line items.

7. **Document Classification Guardrail**
   Utility bill pipelines frequently receive non-bill attachments (register map sheets, meter datasheets, user manuals). The extractor runs a multi-signal keyword and pattern density classifier. Documents like Schneider EM6400 register maps are flagged and rejected immediately with `REJECTED_NON_BILL` before mathematical reconciliation runs.

---

## Automated Test Suite & Quality Assurance

All core subsystems—API endpoints, deterministic mathematical audit, multi-engine OCR extraction, and non-bill guardrails—are covered by an automated test suite executed via `pytest`.

### Test Execution Summary

| Metric | Result | Status |
| :--- | :--- | :---: |
| **Total Test Cases Written** | **11** | ✅ |
| **Tests Passed** | **11** | ✅ |
| **Tests Failed** | **0** | ✅ |
| **Passing Percentage** | **100.0%** | 🟢 **100%** |
| **Test Framework** | `pytest` 9.1.1 + `pytest-asyncio` | ✅ |
| **Execution Duration** | **20.24s** *(includes neural OCR on multi-page 200 DPI scanned bills)* | ⚡ Fast |

### Test Cases Breakdown

| Test Suite / File | Test Case | Target Subsystem | Assertions & Audit Scope | Status | Pass Rate |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `tests/test_api.py` | `test_health_check_endpoint` | API Gateway | Validates `GET /api/v1/health`, queue driver, and Tesseract readiness | **PASSED** | 100% |
| `tests/test_api.py` | `test_discoms_endpoint` | Configuration | Verifies DISCOM registry, tariff codes, and lookup keywords | **PASSED** | 100% |
| `tests/test_api.py` | `test_settings_endpoints` | Settings Service | Tests live updating of Gemini API key, Ollama URL, and connection latency | **PASSED** | 100% |
| `tests/test_api.py` | `test_bill_upload_and_stream` | Storage & Streaming | Verifies zero-disk PostgreSQL `BYTEA` upload and stream retrieval | **PASSED** | 100% |
| `tests/test_math_verification.py` | `test_units_consistency_valid` | Audit Engine | Verifies $(\text{Curr} - \text{Prev}) \times \text{MF} = \text{Consumed}$ with zero discrepancy | **PASSED** | 100% |
| `tests/test_math_verification.py` | `test_units_consistency_mismatch_detected` | Audit Engine | Asserts `METER_READINGS_CONSISTENCY` discrepancy flag on synthetic mismatch | **PASSED** | 100% |
| `tests/test_math_verification.py` | `test_power_factor_invalid` | Audit Engine | Asserts `POWER_FACTOR_RANGE` critical failure when $\text{PF} > 1.0$ (unphysical) | **PASSED** | 100% |
| `tests/test_parsers.py` | `test_extract_apdcl_scnel_bill` | TOD OCR Parser | Validates APDCL TOD sum ($306,161.46\text{ kWh}$), PF $99.00$, and bill metadata | **PASSED** | 100% |
| `tests/test_parsers.py` | `test_extract_apdcl_bill` | OCR Parser | Validates APDCL HT-II industrial bill (`SCL`), consumer ID, and net due | **PASSED** | 100% |
| `tests/test_parsers.py` | `test_extract_scanned_gescom_bill` | Neural Tesseract | Validates 200 DPI neural OCR recovery on degraded dot-matrix scanned bill | **PASSED** | 100% |
| `tests/test_parsers.py` | `test_non_bill_guardrail_rejection` | Guardrails | Confirms rejection of Schneider EM6400 datasheet (`REJECTED_NON_BILL`) | **PASSED** | 100% |

### Running the Test Suite

```bash
# Run the complete test suite
cd backend
.venv/bin/pytest

# Run tests with verbose output and per-test timing
.venv/bin/pytest -v --durations=10
```

---

## System Requirements

- **OS**: macOS (Apple Silicon / Intel) or Linux (Ubuntu 22.04+)
- **Python**: 3.11, 3.12, or 3.14
- **Node.js**: v18.x or v20.x
- **PostgreSQL**: 17 (or 16)
- **Redis**: 7.x or 8.x
- **Tesseract OCR**: 5.x
- **Poppler**: `pdftoppm` utility
- **Ollama** *(optional)*: for local Llama 3.2 summarization

---

## Installation & Setup

### 1. System Dependencies (macOS via Homebrew)

```bash
# Install core database, cache, OCR, and PDF rasterizer
brew install postgresql@17 redis tesseract poppler

# Start background services
brew services start postgresql@17
brew services start redis

# (Optional) Install and start Ollama for local LLM summarization
brew install ollama
brew services start ollama
ollama pull llama3.2
```

### 2. Database Initialization

Create the PostgreSQL database:

```bash
createdb joulewise_db
```

Verify Redis is responding:

```bash
redis-cli ping
# Expected output: PONG
```

### 3. Backend Setup

```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Verify database connection and create tables
python -c "
import asyncio
from app.db.session import engine, Base
import app.models.bill, app.models.bill_line_item, app.models.meter_reading

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Database schema initialized.')

asyncio.run(init())
"

# Run backend development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API documentation will be available at `http://127.0.0.1:8000/docs`.

### 4. Frontend Setup

In a separate terminal window:

```bash
cd frontend-joulewise

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Running the Automated Test Suite

From the `backend/` directory:

```bash
cd backend
source .venv/bin/activate

# Run all API and parser tests
pytest -v

# Run only API endpoints test
pytest tests/test_api.py -v

# Run parser and dataset test cases
pytest tests/test_parsers.py -v
```

All tests execute against local PostgreSQL and Redis instances.

---

## API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/bills/upload` | Upload single bill file; saves to PostgreSQL `BYTEA` and enqueues OCR. |
| `POST` | `/api/v1/bills/bulk-upload` | Bulk upload multiple bills simultaneously. |
| `GET` | `/api/v1/bills` | List processed bills with status filter (`VERIFIED`, `FLAGGED_FOR_REVIEW`, `REJECTED_NON_BILL`). |
| `GET` | `/api/v1/bills/{id}` | Get full extracted attributes, meter readings, line items, and math audit. |
| `GET` | `/api/v1/bills/{id}/file` | Stream original binary document directly from PostgreSQL storage. |
| `PUT` | `/api/v1/bills/{id}` | Update extracted fields manually with real-time math re-verification. |
| `DELETE` | `/api/v1/bills/{id}` | Delete bill and invalidate Redis cache entry. |
| `DELETE` | `/api/v1/bills` | Truncate all bills and flush Redis cache. |
| `GET` | `/api/v1/settings` | Get status of Tesseract, Poppler, Redis, PostgreSQL, Ollama, and Gemini. |
| `POST` | `/api/v1/settings` | Update Gemini API key, Ollama URL, or model at runtime. |
| `POST` | `/api/v1/settings/test` | Test connectivity and measure latency to Gemini or Ollama. |

---

## Production Deployment Considerations

1. **File Size Limits**: Default upload ceiling is set to 25MB per document.
2. **Database Sizing**: Storing 100,000 bills (average 250KB per PDF) requires ~25GB of PostgreSQL `BYTEA` storage. Ensure appropriate tablespace configuration and WAL settings.
3. **Queue Scalability**: The current worker implementation uses in-process `asyncio.Queue` suitable for single-node deployments. For distributed multi-worker topologies, wire the task payload to Redis streams or Celery.
