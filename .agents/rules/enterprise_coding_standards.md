# Enterprise Development Rules for AI Agents

1. **No Unnecessary Comments**: Write self-documenting code with meaningful names. Add comments only for domain-specific electricity tariff formulas or complex OCR matrix transformations.
2. **Zero Hardcoding**: All static UI options, DISCOM names, status codes, regex templates, and tariff configurations must be placed in `.json` configuration files or strongly typed constants. Never hardcode data inside components or service logic.
3. **Clean Architecture & DRY**: Keep strict separation between API layers, business services, math verification engines, OCR adapters, and database repositories. Reuse components and calculation utilities across the codebase.
4. **Strict Typing**:
   - Python: 100% type hints with Pydantic v2 schemas and Python 3.11+ union syntax (`str | None`).
   - TypeScript: Strict typing without `any`.
5. **FastAPI & Swagger**: All FastAPI routes must include response models, status codes, docstrings/summaries, and tags for complete Swagger/OpenAPI documentation.
6. **Robust Error Handling**: Standardized error responses with error codes, clear messages, and validation details.
7. **Testing**: Maintain high test coverage with automated unit tests for math verification and Cypress for frontend user flows.
