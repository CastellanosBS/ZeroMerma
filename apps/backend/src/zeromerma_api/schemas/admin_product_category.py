from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminProductCategoryOut(BaseModel):
    id: int
    code: str
    name: str
    quick_name: str | None = None
    show_in_pos: bool
    default_pos_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
