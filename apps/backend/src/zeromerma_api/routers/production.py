from __future__ import annotations

from fastapi import APIRouter

from zeromerma_api.core.authz import ROLE_ADMIN, require_ctx_role
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.schemas.production import ProductionRunCreate, ProductionRunOut
from zeromerma_api.services.production_service import create_production_run

router = APIRouter(prefix="/production", tags=["production"])


@router.post("/runs", response_model=ProductionRunOut)
def api_create_production_run(
    payload: ProductionRunCreate,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> ProductionRunOut:
    """
    Create a production run.

    Side effects (single transaction):
    - inventory_balance updated (inputs decrement, outputs increment)
    - inventory_movement rows inserted
    """
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})

    try:
        result = create_production_run(
            db,
            branch_id=payload.branch_id,
            created_by_id=int(ctx.user.id),
            inputs=[item.model_dump() for item in payload.inputs],
            outputs=[item.model_dump() for item in payload.outputs],
            note=payload.note,
        )
        db.commit()
        return ProductionRunOut.model_validate(result)
    except Exception:
        db.rollback()
        raise
