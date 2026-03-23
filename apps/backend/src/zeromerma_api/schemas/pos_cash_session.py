# apps/backend/src/zeromerma_api/schemas/pos_cash_session.py
"""
Deprecated compatibility shim.

The canonical cash-session API contracts now live in:
    zeromerma_api.schemas.cash_session

This module remains only to avoid breaking older imports during Phase 0.
Remove it after all imports are migrated.
"""

from .cash_session import (
    CashSessionCloseIn as CashSessionCloseRequest,
)
from .cash_session import (
    CashSessionOpenIn as CashSessionOpenRequest,
)
from .cash_session import CashSessionOut

__all__ = [
    "CashSessionOpenRequest",
    "CashSessionCloseRequest",
    "CashSessionOut",
]
