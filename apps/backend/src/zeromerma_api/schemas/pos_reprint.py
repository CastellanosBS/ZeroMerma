from __future__ import annotations

from typing import Literal

from .common import ORMReadSchema
from .pos_receipt import PosReceiptOut

ReprintSource = Literal["SNAPSHOT", "RECONSTRUCTED"]


class PosReprintOut(ORMReadSchema):
    """
    Canonical response for POS receipt reprint.

    source:
    - SNAPSHOT: original persisted receipt payload from checkout time
    - RECONSTRUCTED: fallback payload rebuilt from persisted sale/items/payments
    """

    sale_id: int
    source: ReprintSource | str
    reprint_count: int
    receipt: PosReceiptOut
