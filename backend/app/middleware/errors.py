"""Standard error model {error:{code,message,details}} (api-contracts.md)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error mapped to the standard error envelope."""

    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Map FastAPI/Pydantic 422s onto the standard error envelope with
        human-readable, field-scoped messages (api-contracts.md §Error model)."""
        fields = []
        for err in exc.errors():
            # Drop the leading "body"/"query"/"path" segment for a clean field path.
            path = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            fields.append({"field": ".".join(path) or "(request)", "message": err.get("msg", "")})
        message = (
            "; ".join(f"{f['field']}: {f['message']}" for f in fields)
            or "Request validation failed"
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message,
                    "details": {"fields": fields},
                }
            },
        )
