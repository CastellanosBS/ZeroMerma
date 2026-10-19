"""Canonical stable identifiers shared by return receipts and financial projections."""

from uuid import UUID


def build_return_folio(return_id: UUID) -> str:
    return f"DEV-{return_id.hex.upper()}"
