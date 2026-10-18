"""HTTP boundary controls; only explicitly trusted peers may supply proxy metadata."""

from __future__ import annotations

from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from zeromerma_api.core.config import ApiSettings
from zeromerma_api.presentation.errors import ApiErrorResponse, unhandled_exception_handler

API_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
    "Cache-Control": "no-store",
}


def security_headers(*, https: bool) -> dict[str, str]:
    return {
        **API_SECURITY_HEADERS,
        **({"Strict-Transport-Security": "max-age=31536000"} if https else {}),
    }


class SecurityBoundaryMiddleware:
    def __init__(self, app: ASGIApp, *, settings: ApiSettings) -> None:
        self.app = app
        self.settings = settings
        self.deployed = settings.environment in {"staging", "production"}
        self.proxy_networks = tuple(ip_network(value) for value in settings.trusted_proxy_ips)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_state = scope.setdefault("state", {})
        scope = dict(scope)
        headers = Headers(scope=scope)
        peer = scope.get("client")
        trusted = False
        if peer:
            try:
                trusted = any(ip_address(peer[0]) in network for network in self.proxy_networks)
            except ValueError:
                trusted = False
        forwarded = any(
            name in headers
            for name in ("forwarded", "x-forwarded-for", "x-forwarded-proto", "x-forwarded-host")
        )
        error: str | None = None
        if forwarded:
            if not trusted:
                error = "Untrusted proxy metadata is forbidden."
            elif any(
                len(headers.getlist(name)) > 1 for name in ("x-forwarded-for", "x-forwarded-proto")
            ):
                error = "Duplicate proxy metadata is forbidden."
            elif "forwarded" in headers or "x-forwarded-host" in headers:
                error = "Unsupported proxy metadata is forbidden."
            else:
                protocol = headers.get("x-forwarded-proto")
                if protocol not in {"http", "https"}:
                    error = "The proxy protocol is invalid."
                else:
                    scope["scheme"] = protocol
                client_ip = headers.get("x-forwarded-for")
                if client_ip:
                    try:
                        scope["client"] = (str(ip_address(client_ip)), 0)
                    except ValueError:
                        error = "The proxy client address is invalid."
        raw_hosts = headers.getlist("host")
        raw_host = raw_hosts[0] if raw_hosts else ""
        try:
            parsed_host = urlsplit("//" + raw_host)
            host = parsed_host.hostname
            port = parsed_host.port
        except ValueError:
            host = None
            port = None
        allowed = {value.strip("[]") for value in self.settings.allowed_hosts}
        if (
            len(raw_hosts) != 1
            or host not in allowed
            or any(character in raw_host for character in "/@?#\\")
            or any(character.isspace() for character in raw_host)
            or (port is not None and not 1 <= port <= 65535)
        ):
            error = "The request host is not authorized."
        if self.deployed and scope.get("scheme") != "https":
            error = "HTTPS is required."
        https = scope.get("scheme") == "https"
        request_state["zeromerma_verified_https"] = https

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                for key, value in security_headers(https=https).items():
                    response_headers[key] = value
            await send(message)

        if error:
            payload = ApiErrorResponse(
                code="FORBIDDEN", message=error, details=None, request_id=None, field_errors=None
            )
            await JSONResponse(status_code=403, content=payload.model_dump(mode="json"))(
                scope, receive, secure_send
            )
            return
        await self.app(scope, receive, secure_send)


def install_security_boundary(app: FastAPI, settings: ApiSettings) -> None:
    app.add_middleware(SecurityBoundaryMiddleware, settings=settings)

    async def safe_server_error(request: Request, exc: Exception) -> JSONResponse:
        response = await unhandled_exception_handler(request, exc)
        response.headers.update(
            security_headers(
                https=bool(request.scope.get("state", {}).get("zeromerma_verified_https"))
            )
        )
        return response

    app.add_exception_handler(Exception, safe_server_error)
