import logging
from time import perf_counter
from uuid import uuid4

from app.api.errors import error_response

logger = logging.getLogger("hiresense.requests")
MAX_BODY_BYTES = 1_048_576


class RequestContextMiddleware:
    """Bound streamed bodies before JSON parsing and log only safe route metadata."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uuid4().hex
        scope["request_id"] = request_id
        start = perf_counter()
        status = 500

        async def correlated_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                if not any(key == b"cache-control" for key, _ in headers):
                    headers.append((b"cache-control", b"private, no-store"))
                if not any(key == b"x-content-type-options" for key, _ in headers):
                    headers.append((b"x-content-type-options", b"nosniff"))
                message["headers"] = headers
            await send(message)

        try:
            body = bytearray()
            # Buffer at most one MiB, including chunked/missing Content-Length bodies.
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    response = error_response(request_id, 413, "REQUEST_TOO_LARGE", "Request body exceeds 1 MiB.")
                    await response(scope, receive, correlated_send)
                    return
                body.extend(chunk)
                if not message.get("more_body", False):
                    break

            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, replay, correlated_send)
        except Exception:
            # Never log exception strings, SQL parameters, bodies or stack locals.
            response = error_response(request_id, 500, "INTERNAL_ERROR", "The operation could not be completed.")
            await response(scope, receive, correlated_send)
        finally:
            route = scope.get("route")
            logger.info("request method=%s route=%s status=%s request_id=%s duration_ms=%.2f category=%s",
                        scope["method"], getattr(route, "path", "unmatched"), status,
                        request_id, (perf_counter() - start) * 1000,
                        "error" if status >= 400 else "success")
