# JouleWise: Enterprise AI & Engineering Coding Standards & Rules

> **Scope**: Mandatory standards, rules, and best practices for both human engineers and AI coding assistants working on the JouleWise platform.

---

## 1. Core Engineering Principles

1. **DRY (Don't Repeat Yourself)**: Eliminate duplicate logic. Extract shared business formulas, validation routines, transformation mappers, and UI primitives into centralized, reusable modules.
2. **SOLID Design Principles**:
   - **Single Responsibility**: Each module, class, service, and component must have one single reason to change.
   - **Open/Closed**: Software entities should be open for extension, but closed for modification (e.g., add new DISCOM parsers via the `IDiscomParser` interface without editing existing parsers).
   - **Liskov Substitution**: OCR and parser implementations must adhere strictly to their base contracts without surprising side effects.
   - **Interface Segregation**: Keep interfaces lean and specialized.
   - **Dependency Inversion**: High-level business logic must depend on abstractions/protocols, not concrete low-level I/O drivers.
3. **Clean Architecture (Separation of Concerns)**:
   - **Domain / Core**: Pure business rules, entities, and math verification algorithms. Zero external library dependencies.
   - **Application / Services**: Use cases orchestrating domain entities, OCR processing, and tariff computation.
   - **Adapters / Infrastructure**: Database repositories, OCR engine wrappers, S3 clients, external message queues.
   - **Presentation / API**: FastAPI routers, request/response DTOs, Next.js UI components.

---

## 2. Mandatory Rules for AI & Code Generation

### 2.1 Zero Unnecessary Comments
- **DO NOT** write obvious or decorative comments (e.g., `# initialize variable`, `// render button`, `# get user from db`).
- **DO NOT** clutter code with commented-out code blocks or changelog headers.
- **DO** write concise, high-value comments ONLY when explaining non-obvious mathematical formulas (e.g., Power Factor penalty calculation according to state tariff orders) or edge cases in PDF coordinate extraction.
- **Code must be self-documenting**: Use descriptive naming for functions, variables, and types.

### 2.2 Zero Hardcoding & Data Segregation
- **DO NOT** hardcode magic numbers, magic strings, API routes, status codes, regex patterns, or DISCOM lists directly inside components or services.
- **DO** externalize all static lists, options, dropdown choices, status codes, and configuration schemas into dedicated `.json` configuration files or strongly-typed constant files:
  - Backend: `backend/app/configs/*.json` or `backend/app/core/constants.py`
  - Frontend: `frontend-joulewise/configs/*.json` or `frontend-joulewise/lib/constants.ts`
- **DO** load environment-specific values strictly from `.env` via validated settings objects (`pydantic_settings.BaseSettings` in FastAPI, `process.env` with zod validation in Next.js).

### 2.3 Strict Typing Everywhere
- **Python**: 100% type-hinted code using Python 3.11+ syntax (`list[str]`, `str | None`, `typing.Annotated`). Strict Pydantic v2 schemas for all payloads. MyPy / Pyright must pass without `type: ignore` unless strictly documented.
- **TypeScript**: TypeScript strict mode enabled (`"strict": true`, `"noImplicitAny": true`). **Never use `any`**. Use `unknown` with type guards, generic constraints, or explicit discriminated union interfaces.

---

## 3. Backend Standards (Python / FastAPI)

### 3.1 Project Structure
```
backend/
├── app/
│   ├── api/                    # API Routers & Endpoints
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── bills.py
│   │   │   │   ├── ocr.py
│   │   │   │   ├── tariffs.py
│   │   │   │   └── consumers.py
│   │   │   └── api_router.py
│   │   └── deps.py             # FastAPI dependency injections
│   ├── core/                   # Core configurations, security, base errors
│   │   ├── config.py           # Pydantic Settings
│   │   ├── constants.py
│   │   ├── exceptions.py       # Domain & HTTP exceptions
│   │   └── logging.py          # Structured JSON logger
│   ├── db/                     # Database session & base models
│   │   ├── session.py          # Async SQLAlchemy engine & sessionmaker
│   │   ├── base.py
│   │   └── migrations/         # Alembic migrations
│   ├── models/                 # SQLAlchemy 2.0 ORM Models
│   │   ├── bill.py
│   │   ├── consumer.py
│   │   ├── meter_reading.py
│   │   └── tariff.py
│   ├── schemas/                # Pydantic v2 Request/Response DTOs
│   │   ├── bill_dto.py
│   │   ├── ocr_dto.py
│   │   └── tariff_dto.py
│   ├── services/               # Pure Business Logic
│   │   ├── ocr/
│   │   │   ├── adapters/       # Tesseract, EasyOCR, Textract adapters
│   │   │   ├── parsers/        # DISCOM-specific parsing strategies
│   │   │   ├── preprocessor.py # OpenCV deskew, contrast, binarization
│   │   │   └── engine.py       # OCR Pipeline Orchestrator
│   │   ├── verification/       # Mathematical Reconciliation Engine
│   │   └── tariffs/            # Tariff Calculator
│   ├── repositories/           # Data Access Layer (CRUD)
│   ├── configs/                # Static JSON metadata (discoms.json, tariff_rules.json)
│   └── workers/                # Celery / ARQ background tasks
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/               # Sample PDF/Image test bills
├── pyproject.toml
└── Dockerfile
```

### 3.2 FastAPI Best Practices
1. **Full OpenAPI / Swagger Documentation**: Every route must specify:
   - `summary`, `description`, `response_model`, `status_code`
   - `responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}`
   - Accurate tag grouping (`tags=["Bills", "OCR", "Tariffs"]`).
2. **Async First**: Use `async def` for I/O bound endpoints, database access with `asyncpg`, and non-blocking S3 operations.
3. **Centralized Error Handling**: Define a uniform error response schema conforming to RFC 7807:
   ```json
   {
     "error_code": "MATH_VERIFICATION_FAILED",
     "message": "Calculated consumed units (4200 kWh) do not match billed units (4500 kWh)",
     "details": { "difference": 300, "confidence": 0.94 },
     "timestamp": "2026-09-05T02:56:00Z"
   }
   ```
4. **Dependency Injection**: Use FastAPI `Depends()` for database sessions, current user authentication, and service instances.

---

## 4. Frontend Standards (Next.js / TypeScript)

### 4.1 Enterprise Tooling & Quality Gates
- **Husky & Lint-Staged**: Pre-commit hooks running Prettier formatting, ESLint validation, and TypeScript typechecking.
- **Styling**: Standardized Tailwind CSS v4 design tokens or CSS Modules with structured design tokens (Colors, Typography, Spacing, Shadows). **No arbitrary inline CSS strings**.
- **State Management**:
  - Server State: `@tanstack/react-query` for API caching, deduplication, and optimistic updates.
  - Client State: `zustand` for viewer UI state (zoom levels, active bounding box, review mode).
- **Component Design**: Atomic design principles (`components/ui` for primitives, `components/features` for domain-specific widgets).
- **Testing**:
  - Unit/Component: `Vitest` or `Jest` + `@testing-library/react`.
  - End-to-End: `Cypress` for testing the entire bill upload -> OCR preview -> edit -> save -> tariff verification workflow.

### 4.2 Data Management in Frontend
- All static label maps, DISCOM dropdowns, status indicators, and column schemas must be imported from `configs/*.json` or typed constants.
- Never hardcode mock items inside UI components.

---

## 5. OCR & Data Extraction Quality Bar

1. **Extraction Accuracy Target**: >98% field accuracy for standard computerized bills, with automatic fallback and interactive human review flagging for low-confidence (<85%) or degraded scan documents.
2. **Confidence Scoring**: Every extracted field must include a confidence score (0.0 to 1.0) and bounding box coordinate tuple `[x, y, width, height]` to enable interactive UI inspection.
3. **Deterministic Math Validation**: OCR output must never be directly committed to the primary ledger without passing the Math Verification Engine. Any mismatch triggers an automated discrepancy alert.

---

## 6. Testing & CI/CD Standards

1. **Test Coverage**: Minimum 85% unit test coverage across business services (verification engine, tariff calculators, parsers).
2. **Regression Golden Dataset**: The test suite must run against the reference bills in `Datasets/` to ensure extraction accuracy does not regress upon algorithm tuning.
3. **CI Pipeline**: Automated GitHub Actions executing:
   - Backend: Ruff lint, MyPy type check, Pytest with coverage.
   - Frontend: ESLint, Prettier check, TypeScript compilation, Cypress E2E headless tests.
   - Docker container build and security scan.

---
