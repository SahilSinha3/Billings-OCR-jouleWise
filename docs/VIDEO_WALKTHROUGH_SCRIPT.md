# JouleWise Video Walkthrough Script

**Target Duration**: 5–7 minutes
**Tone**: Confident, engineering-focused, structured, and easy to follow.
**Audience**: Technical evaluators, engineering leads, product stakeholders.

---

## 🎬 Scene Breakdown Overview

| Scene | Duration | What to Show on Screen | Key File / URL to Open |
| :--- | :--- | :--- | :--- |
| **Scene 1** | ~1:00 min | Architecture Overview & HLD Diagram | [`docs/ARCHITECTURE_HLD_LLD.md`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/docs/ARCHITECTURE_HLD_LLD.md) |
| **Scene 2** | ~1:00 min | Low-Level Design & Codebase Map | [`docs/ARCHITECTURE_HLD_LLD.md`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/docs/ARCHITECTURE_HLD_LLD.md) & [`bill.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/models/bill.py) |
| **Scene 3** | ~1:30 min | Deep Dive into the 4 Core Engine Files | [`engine.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/services/ocr/engine.py), [`universal_extractor.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/services/ocr/universal_extractor.py), [`engine.py (Audit)`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/services/verification/engine.py), [`bills.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/api/v1/endpoints/bills.py) |
| **Scene 4** | ~0:45 min | Automated Test Suite (100% Pass) | Terminal: `pytest -v` |
| **Scene 5** | ~2:00 min | Live Frontend Walkthrough & Edge Cases | Browser: `http://localhost:3000` |
| **Scene 6** | ~0:30 min | Wrap-up & Summary | Browser / GitHub Repo |

---

## 📋 Detailed Scene-by-Scene Script

---

### Scene 1: Introduction & High-Level Design (HLD)

**⏱️ Time**: 0:00 – 1:00
**🖥️ What to show**: Open [`docs/ARCHITECTURE_HLD_LLD.md`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/docs/ARCHITECTURE_HLD_LLD.md) in your editor and scroll down to the **System Topology Diagram** (`Section 1.2`).

> **🗣️ Spoken Script**:
> *"Hi everyone! Welcome to this technical walkthrough of **JouleWise**.*
>
> *JouleWise is an automated, high-performance extraction and mathematical audit platform built specifically for complex Indian state electricity bills—such as APDCL, JVVNL, and GESCOM.*
>
> *Let's start right here with the **High-Level Design (HLD)**.*
> *(Point to the Mermaid diagram)*
>
> *The system is divided into five clean tiers:*
> 1. *A modern **Next.js 16 Client** with an Apple-inspired monochrome design that supports single and bulk drag-and-drop.*
> 2. *A **FastAPI Ingress Gateway** that immediately fingerprints every incoming file using cryptographic **SHA-256**.*
> 3. *An in-memory **Redis Cache** that resolves pre-existing bills in **under 5 milliseconds**, eliminating redundant OCR runs.*
> 4. *A **PostgreSQL 17 Database** with zero-disk persistence—storing raw document bytes directly as `BYTEA` blobs for enterprise security.*
> 5. *And an asynchronous **Queue Worker Pipeline** combining multi-threaded Poppler PDF rasterization, neural Tesseract OCR, regex heuristics, and a mathematical tariff audit engine."*

---

### Scene 2: Low-Level Design (LLD) & Codebase Structure

**⏱️ Time**: 1:00 – 2:00
**🖥️ What to show**: Scroll down to `Section 2: Codebase Map` in [`docs/ARCHITECTURE_HLD_LLD.md`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/docs/ARCHITECTURE_HLD_LLD.md), then briefly switch to the file explorer showing `backend/app/`.

> **🗣️ Spoken Script**:
> *"Now let’s look at the **Low-Level Design (LLD)** and how the code is organized.*
>
> *Everything is organized modularly into clean directories:*
> - *Under `backend/app/api/v1/endpoints/bills.py`, we have our HTTP route handlers for uploading, streaming, and exporting.*
> - *Under `backend/app/models/bill.py`, we define our SQLAlchemy models.*
> - *Under `backend/app/services/ocr/`, we have our Poppler rasterizer and Tesseract OCR engine.*
> - *Under `backend/app/services/verification/`, we have our deterministic math audit engine.*
> - *And under `frontend-joulewise/app/page.tsx`, we have our Next.js dashboard built with pure CSS Modules.*
>
> *Now, let's open the code and inspect the four most important files that power the system."*

---

### Scene 3: Backend Code Deep Dive (4 Key Files)

**⏱️ Time**: 2:00 – 3:30
**🖥️ What to show**: Walk through these 4 files sequentially in VS Code.

#### File 1: PostgreSQL Zero-Disk Model
* **File to open**: [`backend/app/models/bill.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/models/bill.py)
* **Lines to highlight**: Lines 24–44 (`file_data: Mapped[bytes] = mapped_column(LargeBinary)`)
> **🗣️ Spoken Script**:
> *"First, in `bill.py`, notice `file_data` is stored as `LargeBinary`—a PostgreSQL `BYTEA` column. We never save PDFs or slices to the server's local hard drive. Furthermore, all parameters are nullable so when a document is rejected as a non-bill, it cleanly stores `null` without fake placeholders."*

#### File 2: High-Speed OCR Pipeline
* **File to open**: [`backend/app/services/ocr/engine.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/services/ocr/engine.py)
* **Lines to highlight**: Function `extract()` (Lines 40–80)
> **🗣️ Spoken Script**:
> *"Second, in `engine.py`, function `extract()`. For PDFs, we invoke Poppler (`pdftoppm`) at 200 DPI across 4 worker threads, converting pages to 8-bit grayscale. Then Tesseract 5 runs with neural LSTM `--oem 1` in a single pass. The entire extraction completes in just ~2.2 seconds."*

#### File 3: Guardrail & Heuristic Extractor
* **File to open**: [`backend/app/services/ocr/universal_extractor.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/services/ocr/universal_extractor.py)
* **Lines to highlight**:
  - `validate_is_electricity_bill()` (Lines 50–90): Non-bill classifier.
  - `extract_heuristic_fields()` (Lines 210–260): Multi-DISCOM parsing.
> **🗣️ Spoken Script**:
> *"Third, in `universal_extractor.py`:
> 1. Function `validate_is_electricity_bill()` acts as a guardrail. If someone uploads a technical manual or meter register map, it rejects it immediately with `REJECTED_NON_BILL`.
> 2. Function `extract_heuristic_fields()` handles complex Indian bill formats:
>    - For JVVNL, it captures the true Net Payable Amount right above the words ending in 'Rupees Only' (₹585,217), ignoring intermediate subtotals like NET ND.
>    - It maps multi-line tabular headers like `Av. P.F` to `0.990`.
>    - And for GESCOM, it captures the dispatch reference `CNL/AEE/SA/25-26/` and normalizes verbal dates like '16th of July' into `2025-07-16`."*

#### File 4: Deterministic Mathematical Tariff Audit
* **File to open**: [`backend/app/services/verification/engine.py`](file:///Users/sahilsinha/PGAGI/Personal%20/jouleWise/backend/app/services/verification/engine.py)
* **Lines to highlight**: Function `verify()` (Lines 40–95)
> **🗣️ Spoken Script**:
> *"Fourth, in `engine.py`, function `verify()`. It checks four physical and financial invariants:
> 1. Delta Consistency: $(Current - Previous) \times Multiplier = Consumed$.
> 2. Power Factor bounds: $0.0 \le PF \le 1.0$.
> 3. Date chronology.
> 4. Financial sum matching.
> If everything reconciles, it marks the bill `VERIFIED` with zero human review needed."*

---

### Scene 4: Automated Test Suite (100% Pass Rate)

**⏱️ Time**: 3:30 – 4:15
**🖥️ What to show**: Open the terminal in `backend/` and run the tests.

```bash
cd backend
.venv/bin/pytest -v
```

> **🗣️ Spoken Script**:
> *"Before we look at the UI, let's verify code correctness by running the full test suite.
> *(Hit Enter on `pytest -v`)*
>
> *Here we have 12 comprehensive unit and integration tests covering our API gateway, mathematical audit rules, multi-page neural OCR, and non-bill guardrails.*
>
> *(Wait for green output)*
> *All 12 tests pass 100% in under 30 seconds."*

---

### Scene 5: Live Frontend Walkthrough & Edge Cases

**⏱️ Time**: 4:15 – 6:15
**🖥️ What to show**: Switch to your browser at `http://localhost:3000`.

#### Action 1: Bulk Ingestion
* **Action**: Drag and drop all 5 test files from the `Datasets/` folder into the dropzone:
  1. `Energy Bill Mar-26 SCNEL.pdf`
  2. `Energy Bill Mar-26 SCL.pdf`
  3. `Electricity Bill July'25.pdf`
  4. `EB BILL_06JUN2025.pdf`
  5. `EM6400RegMap_V01.01.02.pdf`
> **🗣️ Spoken Script**:
> *"Now let's switch to the live application at `localhost:3000`.
> Watch what happens when I drag and drop all 5 sample PDFs at once.
> Notice the screen-blurring loader that shields the workspace with a 5-phase ticker while processing occurs.
> In ~10 seconds, all 5 documents are parsed, audited, and rendered."*

#### Action 2: Inspect Verified Bills
* **Action**: Click on each bill in the left column:
  - Click **Star Cement** (SCNEL): Show APDCL, units `306,161.46 kWh`, Net `₹12,968,205`, green `VERIFIED` badge.
  - Click **JBM Auto** (JVVNL): Show Net Amount Due is exactly `₹585,217`, Power Factor is `0.990`, and Due Date is `14-Aug-2025`.
  - Click **Chettinad Cement** (GESCOM): Show Bill Number `CNL/AEE/SA/25-26/`, Date `03.07.2025`, Due Date `16.07.2025`, Net `₹10,855,959`.
  - Click **EM6400 Register Map**: Show status is `REJECTED_NON_BILL` with clean `null`/empty metrics—no confusing zeroes or placeholders.
> **🗣️ Spoken Script**:
> *"Look at JBM Auto: The final payable amount of ₹585,217 and Power Factor of 0.990 are extracted with 100% precision.
> Look at GESCOM: The dispatch reference and correct 2025 bill date are extracted cleanly.
> And look at the Schneider EM6400 document: JouleWise accurately identified it as a technical register map and rejected it as `REJECTED_NON_BILL`, leaving all financial fields empty."*

#### Action 3: Test Deduplication & Re-upload
* **Action**: Re-upload the exact same bill (`Electricity Bill July'25.pdf`).
> **🗣️ Spoken Script**:
> *"Now let's test our deduplication system. If I drag in `Electricity Bill July'25.pdf` again:
> Notice that instead of re-running OCR, an 'Already Parsed' notification banner appears, and the existing verified bill opens instantly."*

#### Action 4: Test Deletion & Input Reset
* **Action**: Click the red trash icon on one bill, delete it, and then immediately re-upload that same bill.
> **🗣️ Spoken Script**:
> *"And if we delete a bill and choose to re-upload it, the file input automatically resets its DOM reference, allowing immediate re-ingestion."*

#### Action 5: CSV Export
* **Action**: Click the **Export All** button in the header of the Processed Bills list. Open the downloaded CSV.
> **🗣️ Spoken Script**:
> *"Finally, let's click 'Export All'.
> Here is the exported CSV: all 16 parameters—Consumer Name, CA Number, Bill Number, Units, Power Factor, and Net Amount—are neatly organized, and the rejected non-bill row is stored cleanly without fake numbers."*

---

### Scene 6: Conclusion

**⏱️ Time**: 6:15 – 6:45
**🖥️ What to show**: Back to the dashboard or repository overview.

> **🗣️ Spoken Script**:
> *"To summarize: JouleWise delivers deterministic OCR accuracy for Indian electricity bills in ~2 seconds, provides zero-disk enterprise security via PostgreSQL `BYTEA`, sub-5ms Redis caching, non-bill guardrails, and complete CSV reporting.
>
> Thank you for watching!"*
