from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Literal

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import hash_password
from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import SessionLocal, engine
from zeromerma_api.services.cash_session_service import (
    get_current_open_session,
    open_cash_session,
)
from zeromerma_api.services.inventory_balance_service import (
    bootstrap_inventory_balance_from_ledger,
)
from zeromerma_api.services.payment_service import add_payment
from zeromerma_api.services.sale_service import create_sale

log = logging.getLogger(__name__)

BootstrapProfile = Literal["core", "dev", "inventory-fixture"]

DEFAULT_BRANCH_CODE = "MAIN"
DEFAULT_BRANCH_NAME = "Main Branch"

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_NAME = "System Admin"
DEFAULT_ADMIN_PASSWORD = "admin1234"

DEFAULT_CASHIER_EMAIL = "cashier@example.com"
DEFAULT_CASHIER_NAME = "Cashier User"
DEFAULT_CASHIER_PASSWORD = "cashier1234"

SEED_REF_TYPE = "SEED"
SEED_REF_ID = 1
OPENING_NOTE = "BOOTSTRAP_OPENING_BALANCE"
SAMPLE_PAYMENT_REFERENCE = "BOOTSTRAP_SAMPLE_PAYMENT_V1"


@dataclass(frozen=True)
class CategoryDef:
    code: str
    name: str
    quick_name: str
    show_in_pos: bool
    default_pos_order: int


@dataclass(frozen=True)
class ProductDef:
    sku: str
    name: str
    quick_name: str
    category_code: str
    uom: str
    is_input: bool
    show_in_pos: bool
    is_sellable_in_pos: bool
    default_pos_order: int
    sale_price: Decimal | None
    standard_cost: Decimal | None
    opening_qty: Decimal


DEFAULT_CATEGORIES: list[CategoryDef] = [
    CategoryDef(
        code="DONUTS",
        name="Donuts",
        quick_name="Donuts",
        show_in_pos=True,
        default_pos_order=10,
    ),
    CategoryDef(
        code="PASTRY",
        name="Pastry",
        quick_name="Pastry",
        show_in_pos=True,
        default_pos_order=20,
    ),
    CategoryDef(
        code="BREAD",
        name="Bread",
        quick_name="Bread",
        show_in_pos=True,
        default_pos_order=30,
    ),
    CategoryDef(
        code="DRINKS",
        name="Drinks",
        quick_name="Drinks",
        show_in_pos=True,
        default_pos_order=40,
    ),
    CategoryDef(
        code="INGREDIENTS",
        name="Ingredients",
        quick_name="Ingredients",
        show_in_pos=False,
        default_pos_order=900,
    ),
]

DEFAULT_PRODUCTS: list[ProductDef] = [
    ProductDef(
        sku="DONUT-GLA",
        name="Donut Glazed",
        quick_name="Glazed",
        category_code="DONUTS",
        uom="PCS",
        is_input=False,
        show_in_pos=True,
        is_sellable_in_pos=True,
        default_pos_order=10,
        sale_price=Decimal("18.00"),
        standard_cost=Decimal("6.00"),
        opening_qty=Decimal("50.000"),
    ),
    ProductDef(
        sku="DONUT-CHO",
        name="Donut Chocolate",
        quick_name="Chocolate",
        category_code="DONUTS",
        uom="PCS",
        is_input=False,
        show_in_pos=True,
        is_sellable_in_pos=True,
        default_pos_order=20,
        sale_price=Decimal("20.00"),
        standard_cost=Decimal("7.00"),
        opening_qty=Decimal("40.000"),
    ),
    ProductDef(
        sku="COFFEE-AM",
        name="Coffee Americano",
        quick_name="Americano",
        category_code="DRINKS",
        uom="PCS",
        is_input=False,
        show_in_pos=True,
        is_sellable_in_pos=True,
        default_pos_order=10,
        sale_price=Decimal("35.00"),
        standard_cost=Decimal("10.00"),
        opening_qty=Decimal("30.000"),
    ),
    ProductDef(
        sku="FLOUR",
        name="Wheat Flour",
        quick_name="Flour",
        category_code="INGREDIENTS",
        uom="KG",
        is_input=True,
        show_in_pos=False,
        is_sellable_in_pos=False,
        default_pos_order=900,
        sale_price=None,
        standard_cost=Decimal("18.00"),
        opening_qty=Decimal("25.000"),
    ),
]


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Canonical transactional session scope for bootstrap scripts.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def backend_root() -> Path:
    """
    Resolve the backend root from this module location.

    bootstrap_db.py lives at:
      apps/backend/src/zeromerma_api/scripts/bootstrap_db.py
    """
    return Path(__file__).resolve().parents[3]


def make_alembic_config() -> Config:
    """
    Build a canonical Alembic Config for CLI/bootstrap use.
    """
    root = backend_root()
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)

    return cfg


def get_current_revision() -> str | None:
    """
    Read the currently stamped migration revision from the configured database.
    """
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        return context.get_current_revision()


def get_head_revision() -> str:
    """
    Read the real Alembic head revision available in migrations/.
    """
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(make_alembic_config())
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("Alembic head revision could not be resolved.")
    return head


def ping_database() -> None:
    """
    Execute a lightweight health query against the configured DB.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def upgrade_head() -> None:
    """
    Apply Alembic migrations up to the real head revision.
    """
    command.upgrade(make_alembic_config(), "head")


def ensure_role(db: Session, *, code: str, name: str) -> int:
    row = db.execute(
        text("SELECT id FROM role WHERE code = :code"),
        {"code": code},
    ).fetchone()

    if row:
        role_id = int(row[0])
        db.execute(
            text(
                """
                UPDATE role
                SET name = :name,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"name": name, "id": role_id},
        )
        return role_id

    role_id = db.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()

    return int(role_id)


def ensure_branch(db: Session, *, code: str, name: str) -> int:
    row = db.execute(
        text("SELECT id FROM branch WHERE code = :code"),
        {"code": code},
    ).fetchone()

    if row:
        branch_id = int(row[0])
        db.execute(
            text(
                """
                UPDATE branch
                SET name = :name,
                    is_active = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"name": name, "id": branch_id},
        )
        return branch_id

    branch_id = db.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, true, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()

    return int(branch_id)


def ensure_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    branch_id: int,
    role_id: int,
    password: str,
) -> int:
    """
    Get-or-create a user and keep its branch/role/name/password current.
    """
    email_norm = email.strip().lower()

    row = db.execute(
        text("SELECT id, password_hash FROM user_account WHERE email = :email"),
        {"email": email_norm},
    ).fetchone()

    password_hash = hash_password(password)

    if row:
        user_id = int(row[0])

        db.execute(
            text(
                """
                UPDATE user_account
                SET branch_id = :branch_id,
                    role_id = :role_id,
                    full_name = :full_name,
                    password_hash = :password_hash,
                    is_active = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "branch_id": int(branch_id),
                "role_id": int(role_id),
                "full_name": full_name,
                "password_hash": password_hash,
                "id": user_id,
            },
        )
        return user_id

    user_id = db.execute(
        text(
            """
            INSERT INTO user_account
                (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
                (:branch_id, :role_id, :email, :full_name, :password_hash, true, now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "role_id": int(role_id),
            "email": email_norm,
            "full_name": full_name,
            "password_hash": password_hash,
        },
    ).scalar_one()

    return int(user_id)


def ensure_category(
    db: Session,
    *,
    code: str,
    name: str,
    quick_name: str,
    show_in_pos: bool,
    default_pos_order: int,
) -> int:
    row = db.execute(
        text("SELECT id FROM product_category WHERE code = :code"),
        {"code": code},
    ).fetchone()

    if row:
        category_id = int(row[0])
        db.execute(
            text(
                """
                UPDATE product_category
                SET name = :name,
                    quick_name = :quick_name,
                    show_in_pos = :show_in_pos,
                    default_pos_order = :default_pos_order,
                    is_active = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "name": name,
                "quick_name": quick_name,
                "show_in_pos": bool(show_in_pos),
                "default_pos_order": int(default_pos_order),
                "id": category_id,
            },
        )
        return category_id

    category_id = db.execute(
        text(
            """
            INSERT INTO product_category
                (code, name, quick_name, show_in_pos, default_pos_order, is_active, created_at, updated_at)
            VALUES
                (:code, :name, :quick_name, :show_in_pos, :default_pos_order, true, now(), now())
            RETURNING id
            """
        ),
        {
            "code": code,
            "name": name,
            "quick_name": quick_name,
            "show_in_pos": bool(show_in_pos),
            "default_pos_order": int(default_pos_order),
        },
    ).scalar_one()

    return int(category_id)


def ensure_product(
    db: Session,
    *,
    sku: str,
    name: str,
    quick_name: str,
    category_id: int | None,
    uom: str,
    is_input: bool,
    show_in_pos: bool,
    is_sellable_in_pos: bool,
    default_pos_order: int,
    sale_price: Decimal | None,
    standard_cost: Decimal | None,
    is_active: bool = True,
) -> int:
    sku_norm = sku.strip().upper()

    row = db.execute(
        text("SELECT id FROM product WHERE sku = :sku"),
        {"sku": sku_norm},
    ).fetchone()

    params = {
        "sku": sku_norm,
        "name": name,
        "quick_name": quick_name,
        "category_id": int(category_id) if category_id is not None else None,
        "uom": uom,
        "is_input": bool(is_input),
        "show_in_pos": bool(show_in_pos),
        "is_sellable_in_pos": bool(is_sellable_in_pos),
        "default_pos_order": int(default_pos_order),
        "sale_price": sale_price,
        "standard_cost": standard_cost,
        "is_active": bool(is_active),
    }

    if row:
        product_id = int(row[0])
        db.execute(
            text(
                """
                UPDATE product
                SET name = :name,
                    quick_name = :quick_name,
                    category_id = :category_id,
                    uom = :uom,
                    is_input = :is_input,
                    show_in_pos = :show_in_pos,
                    is_sellable_in_pos = :is_sellable_in_pos,
                    default_pos_order = :default_pos_order,
                    sale_price = :sale_price,
                    standard_cost = :standard_cost,
                    is_active = :is_active,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**params, "id": product_id},
        )
        return product_id

    product_id = db.execute(
        text(
            """
            INSERT INTO product
                (
                    sku,
                    name,
                    quick_name,
                    category_id,
                    uom,
                    is_input,
                    show_in_pos,
                    is_sellable_in_pos,
                    default_pos_order,
                    sale_price,
                    standard_cost,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    :sku,
                    :name,
                    :quick_name,
                    :category_id,
                    :uom,
                    :is_input,
                    :show_in_pos,
                    :is_sellable_in_pos,
                    :default_pos_order,
                    :sale_price,
                    :standard_cost,
                    :is_active,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        params,
    ).scalar_one()

    return int(product_id)


def ensure_opening_balance_movements(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
    products: list[tuple[int, Decimal]],
) -> int:
    """
    Create stable OPENING_BALANCE ledger rows exactly once per seeded product.
    """
    created = 0

    for product_id, opening_qty in products:
        opening_qty = Decimal(opening_qty)
        if opening_qty < 0:
            raise ValueError(
                f"opening_qty must be >= 0 (product_id={product_id}, qty={opening_qty})"
            )
        if opening_qty == 0:
            continue

        exists = db.execute(
            text(
                """
                SELECT 1
                FROM inventory_movement
                WHERE branch_id = :branch_id
                  AND product_id = :product_id
                  AND reason = 'OPENING_BALANCE'
                  AND ref_type = :ref_type
                  AND ref_id = :ref_id
                  AND note = :note
                LIMIT 1
                """
            ),
            {
                "branch_id": int(branch_id),
                "product_id": int(product_id),
                "ref_type": SEED_REF_TYPE,
                "ref_id": SEED_REF_ID,
                "note": OPENING_NOTE,
            },
        ).fetchone()

        if exists:
            continue

        db.execute(
            text(
                """
                INSERT INTO inventory_movement
                    (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
                VALUES
                    (:branch_id, :product_id, :qty, 'OPENING_BALANCE', :ref_type, :ref_id, :note, :created_by_id, now(), now())
                """
            ),
            {
                "branch_id": int(branch_id),
                "product_id": int(product_id),
                "qty": opening_qty,
                "ref_type": SEED_REF_TYPE,
                "ref_id": SEED_REF_ID,
                "note": OPENING_NOTE,
                "created_by_id": int(created_by_id),
            },
        )
        created += 1

    return created


def assert_ledger_non_negative(db: Session, *, branch_id: int) -> None:
    """
    Guardrail before rebuilding snapshot from ledger.
    """
    rows = db.execute(
        text(
            """
            SELECT product_id, SUM(qty) AS sum_qty
            FROM inventory_movement
            WHERE branch_id = :branch_id
            GROUP BY product_id
            HAVING SUM(qty) < 0
            ORDER BY SUM(qty) ASC
            """
        ),
        {"branch_id": int(branch_id)},
    ).fetchall()

    if rows:
        details = ", ".join(f"(product_id={int(r[0])}, sum_qty={r[1]})" for r in rows)
        raise RuntimeError(
            "Ledger contains negative net stock for some products. "
            f"branch_id={branch_id}, negatives={details}"
        )


def get_on_hand(db: Session, *, branch_id: int, product_id: int) -> Decimal:
    value = db.execute(
        text(
            """
            SELECT COALESCE(on_hand, 0)
            FROM inventory_balance
            WHERE branch_id = :branch_id
              AND product_id = :product_id
            """
        ),
        {"branch_id": int(branch_id), "product_id": int(product_id)},
    ).scalar_one_or_none()

    return Decimal(str(value or 0))


def get_or_create_open_cash_session_id(
    db: Session,
    *,
    branch_id: int,
    opened_by_id: int,
    opening_amount: Decimal,
) -> int:
    current = get_current_open_session(db, branch_id=int(branch_id))
    if current is not None:
        return int(current.id)

    cs = open_cash_session(
        db=db,
        branch_id=int(branch_id),
        opened_by_id=int(opened_by_id),
        opening_amount=opening_amount,
    )
    db.flush()
    return int(cs.id)


def sample_sale_already_seeded(db: Session) -> bool:
    row = db.execute(
        text("SELECT 1 FROM payment WHERE reference = :ref LIMIT 1"),
        {"ref": SAMPLE_PAYMENT_REFERENCE},
    ).fetchone()
    return bool(row)


def create_sample_sale_and_payment(
    db: Session,
    *,
    branch_id: int,
    cash_session_id: int,
    created_by_id: int,
    product_id: int,
    unit_price: Decimal,
    qty: Decimal,
) -> int:
    sale = create_sale(
        db,
        branch_id=int(branch_id),
        cash_session_id=int(cash_session_id),
        created_by_id=int(created_by_id),
        items=[
            {
                "product_id": int(product_id),
                "qty": qty,
                "unit_price": unit_price,
            }
        ],
    )
    db.flush()

    add_payment(
        db,
        sale_id=int(sale.id),
        method="CASH",
        amount=sale.total,
        reference=SAMPLE_PAYMENT_REFERENCE,
    )
    db.flush()

    return int(sale.id)


def ensure_core_seed(db: Session) -> dict[str, int]:
    """
    Seed the minimum operable core:
      - roles
      - MAIN branch
      - admin user
      - cashier user
    """
    branch_id = ensure_branch(db, code=DEFAULT_BRANCH_CODE, name=DEFAULT_BRANCH_NAME)

    admin_role_id = ensure_role(db, code="ADMIN", name="Administrator")
    cashier_role_id = ensure_role(db, code="CASHIER", name="Cashier")
    baker_role_id = ensure_role(db, code="BAKER", name="Baker")

    admin_user_id = ensure_user(
        db,
        email=DEFAULT_ADMIN_EMAIL,
        full_name=DEFAULT_ADMIN_NAME,
        branch_id=branch_id,
        role_id=admin_role_id,
        password=DEFAULT_ADMIN_PASSWORD,
    )

    cashier_user_id = ensure_user(
        db,
        email=DEFAULT_CASHIER_EMAIL,
        full_name=DEFAULT_CASHIER_NAME,
        branch_id=branch_id,
        role_id=cashier_role_id,
        password=DEFAULT_CASHIER_PASSWORD,
    )

    return {
        "branch_id": int(branch_id),
        "admin_role_id": int(admin_role_id),
        "cashier_role_id": int(cashier_role_id),
        "baker_role_id": int(baker_role_id),
        "admin_user_id": int(admin_user_id),
        "cashier_user_id": int(cashier_user_id),
    }


def ensure_dev_catalog_and_inventory(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
) -> dict[str, int]:
    """
    Seed categories, products, deterministic opening balances, and snapshot.
    """
    category_ids: dict[str, int] = {}
    for cat in DEFAULT_CATEGORIES:
        category_ids[cat.code] = ensure_category(
            db,
            code=cat.code,
            name=cat.name,
            quick_name=cat.quick_name,
            show_in_pos=cat.show_in_pos,
            default_pos_order=cat.default_pos_order,
        )

    sku_to_product_id: dict[str, int] = {}
    products_with_qty: list[tuple[int, Decimal]] = []

    for prod in DEFAULT_PRODUCTS:
        product_id = ensure_product(
            db,
            sku=prod.sku,
            name=prod.name,
            quick_name=prod.quick_name,
            category_id=category_ids.get(prod.category_code),
            uom=prod.uom,
            is_input=prod.is_input,
            show_in_pos=prod.show_in_pos,
            is_sellable_in_pos=prod.is_sellable_in_pos,
            default_pos_order=prod.default_pos_order,
            sale_price=prod.sale_price,
            standard_cost=prod.standard_cost,
            is_active=True,
        )
        sku_to_product_id[prod.sku] = product_id
        products_with_qty.append((product_id, prod.opening_qty))

    created_movements = ensure_opening_balance_movements(
        db,
        branch_id=branch_id,
        created_by_id=created_by_id,
        products=products_with_qty,
    )

    assert_ledger_non_negative(db, branch_id=branch_id)
    bootstrap_inventory_balance_from_ledger(db, branch_id=branch_id)

    return {
        "created_opening_movements": int(created_movements),
        **{f"product_{sku}": int(pid) for sku, pid in sku_to_product_id.items()},
    }


def ensure_inventory_fixture(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
) -> dict[str, int]:
    """
    Deterministic fixture for inventory endpoints:
      - one finished product
      - +10 OPENING_BALANCE
      - -3 SALE
      - snapshot rebuilt from ledger
    """
    cat_id = ensure_category(
        db,
        code="DONUTS",
        name="Donuts",
        quick_name="Donuts",
        show_in_pos=True,
        default_pos_order=10,
    )
    product_id = ensure_product(
        db,
        sku="DONUT-GLA",
        name="Donut Glazed",
        quick_name="Glazed",
        category_id=cat_id,
        uom="PCS",
        is_input=False,
        show_in_pos=True,
        is_sellable_in_pos=True,
        default_pos_order=10,
        sale_price=Decimal("18.00"),
        standard_cost=Decimal("6.00"),
        is_active=True,
    )

    db.execute(
        text(
            """
            DELETE FROM inventory_movement
            WHERE branch_id = :branch_id
              AND product_id = :product_id
            """
        ),
        {"branch_id": int(branch_id), "product_id": int(product_id)},
    )

    db.execute(
        text(
            """
            INSERT INTO inventory_movement
                (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :qty, :reason, :ref_type, :ref_id, :note, :created_by_id, now(), now())
            """
        ),
        {
            "branch_id": int(branch_id),
            "product_id": int(product_id),
            "qty": Decimal("10.000"),
            "reason": "OPENING_BALANCE",
            "ref_type": "SEED_FIXTURE",
            "ref_id": 1,
            "note": "INVENTORY_FIXTURE",
            "created_by_id": int(created_by_id),
        },
    )
    db.execute(
        text(
            """
            INSERT INTO inventory_movement
                (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :qty, :reason, :ref_type, :ref_id, :note, :created_by_id, now(), now())
            """
        ),
        {
            "branch_id": int(branch_id),
            "product_id": int(product_id),
            "qty": Decimal("-3.000"),
            "reason": "SALE",
            "ref_type": "SEED_FIXTURE",
            "ref_id": 2,
            "note": "INVENTORY_FIXTURE",
            "created_by_id": int(created_by_id),
        },
    )

    assert_ledger_non_negative(db, branch_id=branch_id)
    bootstrap_inventory_balance_from_ledger(db, branch_id=branch_id)

    return {"fixture_product_id": int(product_id)}


def ensure_sample_pos_transaction(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
    preferred_sku: str = "DONUT-GLA",
) -> dict[str, int] | None:
    """
    Create one deterministic sample sale + payment when safe and not already present.
    """
    if sample_sale_already_seeded(db):
        return None

    product_id = db.execute(
        text("SELECT id FROM product WHERE sku = :sku"),
        {"sku": preferred_sku},
    ).scalar_one_or_none()

    if product_id is None:
        return None

    on_hand = get_on_hand(db, branch_id=branch_id, product_id=int(product_id))
    qty = Decimal("2.000")
    if on_hand < qty:
        return None

    unit_price = db.execute(
        text("SELECT COALESCE(sale_price, 10.00) FROM product WHERE id = :id"),
        {"id": int(product_id)},
    ).scalar_one()

    cash_session_id = get_or_create_open_cash_session_id(
        db,
        branch_id=branch_id,
        opened_by_id=created_by_id,
        opening_amount=Decimal("1000.00"),
    )

    sale_id = create_sample_sale_and_payment(
        db,
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        created_by_id=created_by_id,
        product_id=int(product_id),
        unit_price=Decimal(str(unit_price)),
        qty=qty,
    )

    return {
        "sample_sale_id": int(sale_id),
        "cash_session_id": int(cash_session_id),
    }


def bootstrap_database(
    *,
    profile: BootstrapProfile = "core",
    apply_migrations: bool = True,
    create_sample_sale: bool | None = None,
) -> dict[str, object]:
    """
    Canonical bootstrap entry point.

    Profiles:
      - core: minimum operable admin data only
      - dev: core + catalog + inventory snapshot + optional sample sale
      - inventory-fixture: core + deterministic inventory fixture

    Returns a summary dict suitable for logs/CLI output.
    """
    _ = get_settings()
    ping_database()

    if apply_migrations:
        upgrade_head()

    summary: dict[str, object] = {
        "profile": profile,
        "db_current_revision": get_current_revision(),
        "db_head_revision": get_head_revision(),
    }

    with session_scope() as db:
        core = ensure_core_seed(db)
        summary["core"] = core

        branch_id = int(core["branch_id"])
        admin_user_id = int(core["admin_user_id"])

        if profile == "dev":
            dev_info = ensure_dev_catalog_and_inventory(
                db,
                branch_id=branch_id,
                created_by_id=admin_user_id,
            )
            summary["dev"] = dev_info

            should_create_sample = True if create_sample_sale is None else bool(create_sample_sale)
            if should_create_sample:
                sample_info = ensure_sample_pos_transaction(
                    db,
                    branch_id=branch_id,
                    created_by_id=admin_user_id,
                )
                summary["sample_sale"] = sample_info

        elif profile == "inventory-fixture":
            fixture_info = ensure_inventory_fixture(
                db,
                branch_id=branch_id,
                created_by_id=admin_user_id,
            )
            summary["inventory_fixture"] = fixture_info

    return summary
