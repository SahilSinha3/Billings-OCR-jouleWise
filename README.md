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

## Dataset Validation Cases

The platform is validated against 5 benchmark files in `Datasets/`:

| File | Utility / DISCOM | Type | Key Findings & Extracted Attributes | Status |
| :--- | :--- | :--- | :--- | :--- |
| `Electricity Bill July'25.pdf` | JVVNL (Jaipur Vidyut) | Digital HT-5 | Acc: `97811741`, Units: `69,185 kWh`, Net Due: `₹5,50,624.78`, Due Date: `14-08-2025` | **Verified** |
| `Energy Bill Mar-26 SCL.pdf` | APDCL (Assam Power) | Digital HT-II | Consumer: `M/S CEMENT MFG CO`, Acc: `006000002141`, Net Due: `₹1,73,06,353.00` | **Verified** |
| `Energy Bill Mar-26 SCNEL.pdf` | APDCL (Assam Power) | Digital HT-II | Consumer: `Star Cement North-East Ltd`, Acc: `006010060944`, Bill: `900237539`, TOD Units: `306,161.46 kWh`, Net Due: `₹1,29,68,205.00`, Due Date: `27-April-2026`, PF: `99.00` | **Verified** |
| `EB BILL_06JUN2025.pdf` | GESCOM (Gulbarga) | Scanned EHT | Consumer: `Chettinad Cement`, Acc: `EHT 5`, Units: `1,008,700 kWh`, Net Due: `₹1,08,55,959.00` | **Verified** |
| `EM6400RegMap_V01.01.02.pdf` | Schneider Electric | Technical Manual | Modbus register map. Correctly triggered non-bill guardrail. | **Rejected (Guardrail)** |

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
