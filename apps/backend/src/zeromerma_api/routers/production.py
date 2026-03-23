from __future__ import annotations

from fastapi import APIRouter

from zeromerma_api.core.authz import ROLE_ADMIN, require_ctx_role
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
)
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
      - inventory_movement rows inserted (PRODUCTION_INPUT / PRODUCTION_OUTPUT)

    Auth:
      - ADMIN only in Phase 0/6.3 flow
      - created_by_id always comes from the authenticated user
    """
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})

    try:
        result = create_production_run(
            db,
            branch_id=payload.branch_id,
            created_by_id=int(ctx.user.id),
            inputs=[i.model_dump() for i in payload.inputs],
            outputs=[o.model_dump() for o in payload.outputs],
            note=payload.note,
        )
        db.commit()
        return ProductionRunOut.model_validate(result)
    except LookupError as e:
        db.rollback()
        raise DomainNotFoundError(message=str(e)) from e
    except ValueError as e:
        db.rollback()
        # Preserve existing API/test semantics: business-rule violations -> 409
        raise DomainConflictError(message=str(e)) from e
    except Exception:
        db.rollback()
        raise
