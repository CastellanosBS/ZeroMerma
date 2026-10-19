"""Loopback-only structured transport for the independent local bridge."""

import ipaddress

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from zeromerma_api.local_hardware.runtime import LocalHardwareBridge
from zeromerma_api.modules.hardware.domain.commands import DeviceCommandResult, SignedDeviceCommand


def create_bridge_app(bridge: LocalHardwareBridge, origins: list[str]) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError) -> JSONResponse:
        return JSONResponse({"code": "INVALID_DEVICE_COMMAND"}, status_code=422)

    def origin(request: Request) -> str:
        candidate = request.headers.get("Origin", "")
        try:
            loopback = (
                request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
            )
        except ValueError:
            loopback = False
        if not loopback or candidate not in origins:
            raise HTTPException(403, "Local pairing and allowed origin are required.")
        return candidate

    @app.get("/health")
    def health(request: Request) -> dict[str, object]:
        origin(request)
        return {"protocol_version": 1, "status": "RUNNING", "physical_action_performed": False}

    @app.post("/commands", response_model=DeviceCommandResult)
    def execute(grant: SignedDeviceCommand, request: Request) -> DeviceCommandResult:
        allowed_origin = origin(request)
        try:
            return bridge.submit(grant, origin=allowed_origin)
        except ValueError:
            raise HTTPException(403, "The local command is not authorized.") from None

    @app.post("/commands/status", response_model=DeviceCommandResult)
    def status(grant: SignedDeviceCommand, request: Request) -> DeviceCommandResult:
        try:
            return bridge.status(grant, origin=origin(request))
        except ValueError:
            raise HTTPException(403, "The local command is not authorized.") from None

    return app
