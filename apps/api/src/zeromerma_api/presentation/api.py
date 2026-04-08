from fastapi import APIRouter

from zeromerma_api.modules.branches.presentation.router import router as branches_router
from zeromerma_api.modules.cash.presentation.router import router as cash_router
from zeromerma_api.modules.identity.presentation.router import router as identity_router
from zeromerma_api.presentation.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(identity_router)
api_router.include_router(branches_router)
api_router.include_router(cash_router)
