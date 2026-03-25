from __future__ import annotations

from typing import Generator, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.authz import ROLE_ADMIN, require_ctx_role, require_role
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.core.security import hash_password
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.product import Product
from zeromerma_api.models.product_category import ProductCategory
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.admin import (
    AdminPasswordResetIn,
    AdminUserCreateIn,
    AdminUserOut,
    AdminUserUpdateIn,
)
from zeromerma_api.schemas.admin_branch import AdminBranchOut
from zeromerma_api.schemas.admin_product import (
    AdminProductCategoryRef,
    AdminProductCreateIn,
    AdminProductOut,
    AdminProductUpdateIn,
    UomLiteral,
)
from zeromerma_api.schemas.admin_product_category import AdminProductCategoryOut
from zeromerma_api.schemas.admin_role import (
    AdminRoleCreateIn,
    AdminRoleOut,
    AdminRoleUpdateIn,
)
from zeromerma_api.schemas.admin_user_account import (
    AdminUserAccountBranchRef,
    AdminUserAccountCreateIn,
    AdminUserAccountOut,
    AdminUserAccountRoleRef,
    AdminUserAccountUpdateIn,
)
from zeromerma_api.services.admin_branch_service import list_branches
from zeromerma_api.services.admin_product_service import (
    create_product,
    deactivate_product,
    get_product_or_404,
    list_product_categories,
    list_products,
    update_product,
)
from zeromerma_api.services.admin_role_service import (
    create_role,
    deactivate_role,
    get_role_or_404,
    list_roles,
    update_role,
)
from zeromerma_api.services.admin_user_account_service import (
    create_user_account,
    deactivate_user_account,
    get_user_account_or_404,
    list_user_accounts,
    update_user_account,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI DB dependency: open a session, yield it, always close it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_admin(db: Session, current_user: UserAccount) -> None:
    """
    Enforce ADMIN role for /admin endpoints.
    """
    require_role(db, current_user=current_user, allowed_roles={ROLE_ADMIN})


def _basic_email_shape_ok(email: str) -> bool:
    """
    Minimal email shape validation.

    Why minimal:
    - We avoid strict validators that may reject special-use domains (.local).
    - We still prevent clearly invalid values.
    """
    if not email or "@" not in email:
        return False
    left, _, right = email.partition("@")
    if not left.strip() or not right.strip():
        return False
    return True


def _serialize_admin_user_account(user: UserAccount) -> AdminUserAccountOut:
    return AdminUserAccountOut(
        id=int(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        branch_id=int(user.branch_id),
        role_id=int(user.role_id),
        has_password=bool(user.password_hash),
        created_at=user.created_at,
        updated_at=user.updated_at,
        role=AdminUserAccountRoleRef(
            id=int(user.role.id),
            code=user.role.code,
            name=user.role.name,
            is_active=bool(user.role.is_active),
        ),
        branch=AdminUserAccountBranchRef(
            id=int(user.branch.id),
            code=user.branch.code,
            name=user.branch.name,
            is_active=bool(user.branch.is_active),
        ),
    )


def _serialize_admin_product_category(
    category: ProductCategory,
) -> AdminProductCategoryOut:
    return AdminProductCategoryOut.model_validate(category)


def _serialize_admin_product(
    product: Product,
) -> AdminProductOut:
    category_ref = None

    if product.category is not None:
        category_ref = AdminProductCategoryRef(
            id=int(product.category.id),
            code=product.category.code,
            name=product.category.name,
            quick_name=product.category.quick_name,
            is_active=bool(product.category.is_active),
        )

    return AdminProductOut(
        id=int(product.id),
        sku=product.sku,
        name=product.name,
        quick_name=product.quick_name,
        category_id=int(product.category_id) if product.category_id is not None else None,
        uom=cast(UomLiteral, product.uom),
        is_input=bool(product.is_input),
        show_in_pos=bool(product.show_in_pos),
        is_sellable_in_pos=bool(product.is_sellable_in_pos),
        default_pos_order=int(product.default_pos_order),
        sale_price=product.sale_price,
        standard_cost=product.standard_cost,
        is_active=bool(product.is_active),
        created_at=product.created_at,
        updated_at=product.updated_at,
        category=category_ref,
    )


@router.get("/whoami")
def whoami(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> dict:
    """
    Convenience endpoint to verify auth + role resolution works.
    """
    _require_admin(db, current_user)

    role = db.execute(select(Role).where(Role.id == current_user.role_id)).scalar_one_or_none()

    return {
        "id": int(current_user.id),
        "email": current_user.email,
        "branch_id": int(current_user.branch_id),
        "role_id": int(current_user.role_id),
        "role_code": role.code if role else None,
        "is_active": bool(current_user.is_active),
    }


# -------------------------------------------------------------------------
# Roles
# -------------------------------------------------------------------------


@router.get("/roles", response_model=list[AdminRoleOut])
def api_list_roles(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    include_inactive: bool = True,
) -> list[AdminRoleOut]:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    rows = list_roles(db, include_inactive=include_inactive)
    return [AdminRoleOut.model_validate(row) for row in rows]


@router.get("/roles/{role_id}", response_model=AdminRoleOut)
def api_get_role(
    role_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminRoleOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = get_role_or_404(db, role_id=role_id)
    return AdminRoleOut.model_validate(row)


@router.post("/roles", response_model=AdminRoleOut, status_code=201)
def api_create_role(
    payload: AdminRoleCreateIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminRoleOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = create_role(
        db,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    return AdminRoleOut.model_validate(row)


@router.patch("/roles/{role_id}", response_model=AdminRoleOut)
def api_update_role(
    role_id: int,
    payload: AdminRoleUpdateIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminRoleOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = update_role(
        db,
        role_id=role_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    return AdminRoleOut.model_validate(row)


@router.delete("/roles/{role_id}", response_model=AdminRoleOut)
def api_delete_role(
    role_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminRoleOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = deactivate_role(db, role_id=role_id)
    return AdminRoleOut.model_validate(row)


# -------------------------------------------------------------------------
# Branches
# -------------------------------------------------------------------------


@router.get("/branches", response_model=list[AdminBranchOut])
def api_list_branches(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    include_inactive: bool = False,
) -> list[AdminBranchOut]:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    rows = list_branches(db, include_inactive=include_inactive)
    return [AdminBranchOut.model_validate(row) for row in rows]


# -------------------------------------------------------------------------
# Legacy admin users endpoints
# -------------------------------------------------------------------------


@router.get("/users", response_model=List[AdminUserOut])
def list_users(
    branch_id: Optional[int] = Query(None, ge=1, description="Optional branch filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> List[UserAccount]:
    """
    List users (ADMIN only), optionally filtered by branch_id.
    """
    _require_admin(db, current_user)

    stmt = select(UserAccount).order_by(UserAccount.id.asc())

    if branch_id is not None:
        stmt = stmt.where(UserAccount.branch_id == int(branch_id))

    stmt = stmt.offset(int(offset)).limit(int(limit))

    return list(db.execute(stmt).scalars().all())


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreateIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> UserAccount:
    """
    Create a new user (ADMIN only).
    """
    _require_admin(db, current_user)

    email = payload.email.strip().lower()
    if not _basic_email_shape_ok(email):
        raise HTTPException(status_code=422, detail="Invalid email format.")

    branch = db.execute(
        select(Branch).where(Branch.id == int(payload.branch_id))
    ).scalar_one_or_none()
    if branch is None:
        raise HTTPException(
            status_code=404,
            detail=f"Branch {payload.branch_id} not found.",
        )

    role = db.execute(select(Role).where(Role.id == int(payload.role_id))).scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=404,
            detail=f"Role {payload.role_id} not found.",
        )

    existing = db.execute(
        select(UserAccount).where(UserAccount.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already exists.")

    user = UserAccount(
        branch_id=int(payload.branch_id),
        role_id=int(payload.role_id),
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_active=bool(payload.is_active),
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists.") from exc

    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdateIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> UserAccount:
    """
    Update user fields (ADMIN only).
    """
    _require_admin(db, current_user)

    user = db.execute(
        select(UserAccount).where(UserAccount.id == int(user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    if payload.role_id is not None:
        role = db.execute(select(Role).where(Role.id == int(payload.role_id))).scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=404,
                detail=f"Role {payload.role_id} not found.",
            )
        user.role_id = int(payload.role_id)

    if payload.branch_id is not None:
        branch = db.execute(
            select(Branch).where(Branch.id == int(payload.branch_id))
        ).scalar_one_or_none()
        if branch is None:
            raise HTTPException(
                status_code=404,
                detail=f"Branch {payload.branch_id} not found.",
            )
        user.branch_id = int(payload.branch_id)

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()

    if payload.is_active is not None:
        user.is_active = bool(payload.is_active)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=AdminUserOut)
def reset_password(
    user_id: int,
    payload: AdminPasswordResetIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> UserAccount:
    """
    Reset a user's password (ADMIN only).
    """
    _require_admin(db, current_user)

    user = db.execute(
        select(UserAccount).where(UserAccount.id == int(user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    user.password_hash = hash_password(payload.new_password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# -------------------------------------------------------------------------
# New admin user_accounts endpoints
# -------------------------------------------------------------------------


@router.get("/user-accounts", response_model=list[AdminUserAccountOut])
def api_list_user_accounts(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    include_inactive: bool = True,
    q: str | None = None,
) -> list[AdminUserAccountOut]:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    rows = list_user_accounts(
        db,
        include_inactive=include_inactive,
        q=q,
    )
    return [_serialize_admin_user_account(row) for row in rows]


@router.get("/user-accounts/{user_id}", response_model=AdminUserAccountOut)
def api_get_user_account(
    user_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminUserAccountOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = get_user_account_or_404(db, user_id=user_id)
    return _serialize_admin_user_account(row)


@router.post("/user-accounts", response_model=AdminUserAccountOut, status_code=201)
def api_create_user_account(
    payload: AdminUserAccountCreateIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminUserAccountOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = create_user_account(
        db,
        email=payload.email,
        full_name=payload.full_name,
        branch_id=int(payload.branch_id),
        role_id=int(payload.role_id),
        password=payload.password,
        is_active=bool(payload.is_active),
    )
    return _serialize_admin_user_account(row)


@router.patch("/user-accounts/{user_id}", response_model=AdminUserAccountOut)
def api_update_user_account(
    user_id: int,
    payload: AdminUserAccountUpdateIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminUserAccountOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = update_user_account(
        db,
        user_id=int(user_id),
        actor_user_id=int(ctx.user.id),
        email=payload.email,
        full_name=payload.full_name,
        branch_id=payload.branch_id,
        role_id=payload.role_id,
        new_password=payload.new_password,
        is_active=payload.is_active,
    )
    return _serialize_admin_user_account(row)


@router.delete("/user-accounts/{user_id}", response_model=AdminUserAccountOut)
def api_delete_user_account(
    user_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminUserAccountOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = deactivate_user_account(
        db,
        user_id=int(user_id),
        actor_user_id=int(ctx.user.id),
    )
    return _serialize_admin_user_account(row)


# -------------------------------------------------------------------------
# Product categories
# -------------------------------------------------------------------------


@router.get("/product-categories", response_model=list[AdminProductCategoryOut])
def api_list_product_categories(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    include_inactive: bool = False,
) -> list[AdminProductCategoryOut]:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    rows = list_product_categories(db, include_inactive=include_inactive)
    return [_serialize_admin_product_category(row) for row in rows]


# -------------------------------------------------------------------------
# Products
# -------------------------------------------------------------------------


@router.get("/products", response_model=list[AdminProductOut])
def api_list_products(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    include_inactive: bool = True,
    q: str | None = None,
    category_id: int | None = None,
    is_input: bool | None = None,
) -> list[AdminProductOut]:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    rows = list_products(
        db,
        include_inactive=include_inactive,
        q=q,
        category_id=category_id,
        is_input=is_input,
    )
    return [_serialize_admin_product(row) for row in rows]


@router.get("/products/{product_id}", response_model=AdminProductOut)
def api_get_product(
    product_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminProductOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = get_product_or_404(db, product_id=int(product_id))
    return _serialize_admin_product(row)


@router.post("/products", response_model=AdminProductOut, status_code=201)
def api_create_product(
    payload: AdminProductCreateIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminProductOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})

    row = create_product(
        db,
        sku=payload.sku,
        name=payload.name,
        quick_name=payload.quick_name,
        category_id=int(payload.category_id),
        uom=payload.uom,
        is_input=bool(payload.is_input),
        show_in_pos=bool(payload.show_in_pos),
        is_sellable_in_pos=bool(payload.is_sellable_in_pos),
        default_pos_order=int(payload.default_pos_order),
        sale_price=payload.sale_price,
        standard_cost=payload.standard_cost,
        is_active=bool(payload.is_active),
    )

    return _serialize_admin_product(row)


@router.patch("/products/{product_id}", response_model=AdminProductOut)
def api_update_product(
    product_id: int,
    payload: AdminProductUpdateIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminProductOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})

    row = update_product(
        db,
        product_id=int(product_id),
        sku=payload.sku,
        name=payload.name,
        quick_name=payload.quick_name,
        category_id=payload.category_id,
        uom=payload.uom,
        is_input=payload.is_input,
        show_in_pos=payload.show_in_pos,
        is_sellable_in_pos=payload.is_sellable_in_pos,
        default_pos_order=payload.default_pos_order,
        sale_price=payload.sale_price,
        standard_cost=payload.standard_cost,
        is_active=payload.is_active,
    )

    return _serialize_admin_product(row)


@router.delete("/products/{product_id}", response_model=AdminProductOut)
def api_delete_product(
    product_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> AdminProductOut:
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    row = deactivate_product(db, product_id=int(product_id))
    return _serialize_admin_product(row)
