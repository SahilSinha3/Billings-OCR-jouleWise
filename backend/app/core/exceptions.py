from typing import Any


class JouleWiseBaseException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class DocumentProcessingError(JouleWiseBaseException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code="ERR_OCR_FAILED",
            status_code=422,
            details=details,
        )


class MathVerificationError(JouleWiseBaseException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code="ERR_MATH_UNITS_MISMATCH",
            status_code=422,
            details=details,
        )


class BillNotFoundError(JouleWiseBaseException):
    def __init__(self, bill_id: str):
        super().__init__(
            message=f"Bill with ID '{bill_id}' was not found.",
            error_code="ERR_BILL_NOT_FOUND",
            status_code=404,
            details={"bill_id": bill_id},
        )
