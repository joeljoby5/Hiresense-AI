from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.repositories.errors import AnalysisNotFound, JobConflict, JobNotFound, NotFoundError, RevisionConflictError
from app.services.analyses import AnalysisLimitError
from app.services.writing import SuggestionInputError
from app.documents.render import ExportBusyError, ExportContentError
from app.schemas.errors import APIError, APIErrorResponse
from app.services.errors import IdentityUnavailableError


def error_response(request_id, status, code, message, **metadata):
    error = APIError(code=code, message=message, request_id=request_id, **metadata)
    return JSONResponse(APIErrorResponse(error=error).model_dump(mode="json"), status_code=status,
                        headers={"X-Request-ID": request_id})


def install_error_handlers(app):
    async def handler(request, exc):
        request_id = request.scope.get("request_id", "unavailable")
        if isinstance(exc, RequestValidationError):
            fields = []
            for item in exc.errors()[:50]:
                location = list(item["loc"])
                if item["type"] == "extra_forbidden" and location:
                    location[-1] = "unknown_field"
                fields.append({"field": location, "code": item["type"]})
            code = "INVALID_RESUME_CONTENT" if any("content" in f["field"] for f in fields) else "INVALID_REQUEST"
            return error_response(request_id, 422, code, "Request validation failed.", fields=fields)
        if isinstance(exc, IdentityUnavailableError):
            return error_response(request_id, 503, "DEVELOPMENT_IDENTITY_UNAVAILABLE", "Local development identity is unavailable.")
        if isinstance(exc, NotFoundError):
            if isinstance(exc, AnalysisNotFound):
                return error_response(request_id, 404, "ANALYSIS_NOT_FOUND", "The requested analysis was not found.")
            if isinstance(exc, JobNotFound):
                return error_response(request_id, 404, "JOB_NOT_FOUND", "The requested job listing was not found.")
            if str(exc) == "Export not found":
                return error_response(request_id, 404, "RESUME_EXPORT_NOT_FOUND", "The requested export was not found.")
            version = str(exc) == "Version not found"
            return error_response(request_id, 404, "RESUME_VERSION_NOT_FOUND" if version else "RESUME_NOT_FOUND",
                                  "The requested version was not found." if version else "The requested resume was not found.")
        if isinstance(exc, RevisionConflictError):
            if isinstance(exc, JobConflict):
                return error_response(request_id, 409, "JOB_REVISION_CONFLICT", "The job listing has changed.",
                                      current_revision=exc.current_revision)
            return error_response(request_id, 409, "RESUME_REVISION_CONFLICT", "The resume has changed. Retrieve its current revision.",
                                  current_revision=exc.current_revision)
        if isinstance(exc, ExportContentError):
            return error_response(request_id, 422, "UNSUPPORTED_EXPORT_CONTENT", str(exc))
        if isinstance(exc, ExportBusyError):
            return error_response(request_id, 503, "EXPORT_BUSY", "The document renderer is busy. Try again shortly.")
        if isinstance(exc, AnalysisLimitError):
            return error_response(request_id, 422, "ANALYSIS_TOO_LARGE", "The analysis exceeds the size limit.")
        if isinstance(exc, SuggestionInputError):
            return error_response(request_id, 422, "SUGGESTION_INPUT_REQUIRED", "Provide a saved summary and any required consent.")
        if isinstance(exc, ProviderUnavailable):
            return error_response(request_id, 503, "AI_UNAVAILABLE", "The selected writing provider is unavailable.")
        if isinstance(exc, ProviderTimeout):
            return error_response(request_id, 504, "AI_TIMEOUT", "The selected writing provider timed out.")
        if isinstance(exc, ProviderRateLimited):
            return error_response(request_id, 429, "AI_BUSY", "The writing provider is busy. Try again shortly.")
        if isinstance(exc, InvalidProviderResponse):
            return error_response(request_id, 502, "AI_INVALID_RESPONSE", "The writing provider returned an invalid suggestion.")
        if isinstance(exc, IntegrityError):
            return error_response(request_id, 500, "INTERNAL_ERROR", "The operation could not be completed.")
        if isinstance(exc, DBAPIError):
            return error_response(request_id, 503, "DATABASE_UNAVAILABLE", "Database is temporarily unavailable.")
        if isinstance(exc, HTTPException):
            return error_response(request_id, exc.status_code, "INVALID_REQUEST", "The request could not be handled.")
        return error_response(request_id, 500, "INTERNAL_ERROR", "The operation could not be completed.")

    for kind in (RequestValidationError, IdentityUnavailableError, NotFoundError, RevisionConflictError,
                 SQLAlchemyError, ValidationError, HTTPException, ExportContentError, ExportBusyError, AnalysisLimitError,
                 SuggestionInputError, ProviderUnavailable, ProviderTimeout, ProviderRateLimited, InvalidProviderResponse):
        app.add_exception_handler(kind, handler)
from app.ai.contracts import InvalidProviderResponse, ProviderRateLimited, ProviderTimeout, ProviderUnavailable
