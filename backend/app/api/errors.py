from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.repositories.errors import NotFoundError, RevisionConflictError
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
            version = str(exc) == "Version not found"
            return error_response(request_id, 404, "RESUME_VERSION_NOT_FOUND" if version else "RESUME_NOT_FOUND",
                                  "The requested version was not found." if version else "The requested resume was not found.")
        if isinstance(exc, RevisionConflictError):
            return error_response(request_id, 409, "RESUME_REVISION_CONFLICT", "The resume has changed. Retrieve its current revision.",
                                  current_revision=exc.current_revision)
        if isinstance(exc, IntegrityError):
            return error_response(request_id, 500, "INTERNAL_ERROR", "The operation could not be completed.")
        if isinstance(exc, DBAPIError):
            return error_response(request_id, 503, "DATABASE_UNAVAILABLE", "Database is temporarily unavailable.")
        if isinstance(exc, HTTPException):
            return error_response(request_id, exc.status_code, "INVALID_REQUEST", "The request could not be handled.")
        return error_response(request_id, 500, "INTERNAL_ERROR", "The operation could not be completed.")

    for kind in (RequestValidationError, IdentityUnavailableError, NotFoundError, RevisionConflictError,
                 SQLAlchemyError, ValidationError, HTTPException):
        app.add_exception_handler(kind, handler)
