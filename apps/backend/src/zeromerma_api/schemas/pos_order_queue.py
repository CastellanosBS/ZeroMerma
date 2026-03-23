from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import ORMReadSchema

PosOrderDueBucket = Literal["OVERDUE", "TODAY", "FUTURE", "UNSCHEDULED"]


class PosOrderQueueItemPreviewOut(ORMReadSchema):
    """
    Small item preview used in queue screens.

    This is intentionally compact so admin/bakers/cashier can scan the queue
    quickly without loading the full order detail first.
    """

    product_id: int
    sku: str | None = None
    name: str
    quick_name: str | None = None
    qty: Decimal


class PosOrderQueueItemOut(ORMReadSchema):
    """
    One order row inside an operational queue bucket.
    """

    id: int
    branch_id: int
    status: str

    customer_name: str | None = None
    customer_phone: str | None = None
    note: str | None = None

    requested_for_at: datetime | None = None
    created_at: datetime

    subtotal: Decimal
    tax: Decimal
    total: Decimal

    lines_count: int
    total_units: Decimal
    due_bucket: PosOrderDueBucket | str

    items_preview: list[PosOrderQueueItemPreviewOut] = Field(default_factory=list)


class PosOrderQueueCountsOut(ORMReadSchema):
    """
    Lightweight counts summary for queue dashboards.
    """

    created: int
    sent_to_bakery: int
    ready: int
    delivered: int
    canceled: int
    active_total: int


class PosOrderQueueOut(ORMReadSchema):
    """
    Full operational queue payload.

    Buckets:
    - pending_intake: CREATED
    - bakery_work: SENT_TO_BAKERY
    - ready_for_pickup: READY

    Closed statuses are intentionally not listed in queue buckets in 2B.2/2B.3,
    but they are still reflected in aggregate counts.
    """

    branch_id: int
    generated_at: datetime
    counts: PosOrderQueueCountsOut

    pending_intake: list[PosOrderQueueItemOut] = Field(default_factory=list)
    bakery_work: list[PosOrderQueueItemOut] = Field(default_factory=list)
    ready_for_pickup: list[PosOrderQueueItemOut] = Field(default_factory=list)
