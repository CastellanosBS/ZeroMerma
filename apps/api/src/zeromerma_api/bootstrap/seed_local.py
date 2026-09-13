from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.config import get_settings
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.db.wait import wait_for_database
from zeromerma_api.modules.branches.infrastructure.models import Branch, Brand, Workstation
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
    CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.corrections.domain.constants import (
    CORRECTION_REASON_COUNT_MISMATCH,
    CORRECTION_REASON_DAMAGED_DURING_HANDLING,
    CORRECTION_REASON_DUPLICATE_CAPTURE,
    CORRECTION_REASON_OTHER,
    CORRECTION_REASON_WRONG_DESTINATION,
    CORRECTION_REASON_WRONG_PRODUCT,
    CORRECTION_REASON_WRONG_QUANTITY,
)
from zeromerma_api.modules.corrections.infrastructure.models import CorrectionReason
from zeromerma_api.modules.discounts.domain.constants import (
    DISCOUNT_CATEGORY_EMPLOYEE_INSURANCE,
    DISCOUNT_CATEGORY_EMPLOYEE_LOAN,
    DISCOUNT_CATEGORY_INTERNAL_CHARGE,
    DISCOUNT_CATEGORY_OTHER,
    DISCOUNT_CATEGORY_PAYROLL_ADVANCE_ADJUSTMENT,
)
from zeromerma_api.modules.discounts.infrastructure.models import OperationalDiscountCategory
from zeromerma_api.modules.identity.application.permissions import (
    PERMISSION_CATALOG,
    POS_PERMISSION_CODES,
)
from zeromerma_api.modules.identity.application.security import PasswordHasher
from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_ROLE_ADMIN,
    IDENTITY_ROLE_BRANCH_MANAGER,
    IDENTITY_ROLE_CASHIER,
    IDENTITY_SURFACE_BACKOFFICE,
    IDENTITY_SURFACE_POS,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.operations.domain.constants import (
    WASTE_REASON_CONTAMINATED,
    WASTE_REASON_DAMAGED,
    WASTE_REASON_EXPIRED,
    WASTE_REASON_OLD_COUNTER,
    WASTE_REASON_OTHER,
)
from zeromerma_api.modules.operations.infrastructure.models import WasteReason
from zeromerma_api.modules.payments.domain.constants import (
    PAYMENT_CATEGORY_GAS,
    PAYMENT_CATEGORY_LOGISTICS,
    PAYMENT_CATEGORY_OTHER,
    PAYMENT_CATEGORY_PURCHASE,
    PAYMENT_CATEGORY_SERVICES,
    PAYMENT_CATEGORY_SUPPLIER,
)
from zeromerma_api.modules.payments.infrastructure.models import OperationalPaymentCategory

SEED_BRANCH_CODE = "MAIN"
SEED_BRANCH_NAME = "Main Branch"
SEED_BRANCH_TIMEZONE = "America/Hermosillo"
SEED_BRAND_EL_MEJOR_PAN_CODE = "EL_MEJOR_PAN"
SEED_BRAND_EL_MEJOR_PAN_NAME = "El Mejor Pan"
SEED_BRAND_MERENNA_CODE = "MERENNA"
SEED_BRAND_MERENNA_NAME = "Merenna"

SEED_DESTINATION_BRANCH_CODE = "NORTE"
SEED_DESTINATION_BRANCH_NAME = "North Branch"
SEED_DESTINATION_BRANCH_TIMEZONE = "America/Hermosillo"

SEED_ALT_DESTINATION_BRANCH_CODE = "SUR"
SEED_ALT_DESTINATION_BRANCH_NAME = "South Branch"
SEED_ALT_DESTINATION_BRANCH_TIMEZONE = "America/Hermosillo"

SEED_WORKSTATION_CODE = "POS-01"
SEED_WORKSTATION_NAME = "Front Register 01"

SEED_DESTINATION_WORKSTATION_CODE = "POS-NORTE-01"
SEED_DESTINATION_WORKSTATION_NAME = "North Register 01"

SEED_ALT_DESTINATION_WORKSTATION_CODE = "POS-SUR-01"
SEED_ALT_DESTINATION_WORKSTATION_NAME = "South Register 01"

SEED_USER_EMAIL = "cashier@zeromerma.local"
SEED_USER_FULL_NAME = "Main Branch Cashier"
SEED_USER_PASSWORD = "ChangeMe123!"

SEED_ADMIN_EMAIL = "admin@zeromerma.local"
SEED_ADMIN_FULL_NAME = "ZeroMerma Admin"
SEED_ADMIN_PASSWORD = "AdminChangeMe123!"

SEED_PRODUCT_CLASS_PAN_DULCE_CODE = "PAN-DULCE"
SEED_PRODUCT_CLASS_BOLILLO_CODE = "BOLILLO"
SEED_PRODUCT_CLASS_TELERA_CODE = "TELERA"
SEED_PRODUCT_CLASS_BEBIDAS_CODE = "BEBIDAS"
SEED_PRODUCT_CLASS_PASTELES_CODE = "PASTELES"

SEED_PRODUCT_CONCHA_VAN_CODE = "CONCHA-VAN"
SEED_PRODUCT_CONCHA_CHOCO_CODE = "CONCHA-CHOCO"
SEED_PRODUCT_CUERNO_MANTEQUILLA_CODE = "CUERNO-MANTEQUILLA"
SEED_PRODUCT_BOLILLO_STD_CODE = "BOLILLO-STD"
SEED_PRODUCT_TELERA_STD_CODE = "TELERA-STD"
SEED_PRODUCT_COCA_355_CODE = "COCA-355"
SEED_PRODUCT_CAFE_AMERICANO_CODE = "CAFE-AMERICANO"
SEED_PRODUCT_PASTEL_CHOC_IND_CODE = "PASTEL-CHOC-IND"
SEED_PRODUCT_REBANADA_TRES_LECHES_CODE = "REBANADA-TRES-LECHES"


def _upsert_brand(
    session: Session,
    *,
    code: str,
    name: str,
) -> Brand:
    brand = session.execute(select(Brand).where(Brand.code == code)).scalar_one_or_none()
    if brand is None:
        brand = Brand(code=code, name=name, is_active=True)
        session.add(brand)
        session.flush()
        return brand

    brand.name = name
    brand.is_active = True
    session.flush()
    return brand


def _upsert_branch(
    session: Session,
    *,
    brand_id: uuid.UUID,
    code: str,
    name: str,
    timezone: str,
) -> Branch:
    branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one_or_none()
    if branch is None:
        branch = Branch(brand_id=brand_id, code=code, name=name, timezone=timezone, is_active=True)
        session.add(branch)
        session.flush()
        return branch

    branch.brand_id = brand_id
    branch.name = name
    branch.timezone = timezone
    branch.is_active = True
    session.flush()
    return branch


def _upsert_workstation(
    session: Session,
    *,
    branch_id: uuid.UUID,
    code: str,
    name: str,
) -> Workstation:
    workstation = session.execute(
        select(Workstation).where(Workstation.code == code)
    ).scalar_one_or_none()
    if workstation is None:
        workstation = Workstation(
            branch_id=branch_id,
            code=code,
            name=name,
            is_active=True,
        )
        session.add(workstation)
        session.flush()
        return workstation

    workstation.branch_id = branch_id
    workstation.name = name
    workstation.is_active = True
    session.flush()
    return workstation


def _upsert_user(
    session: Session,
    *,
    email: str,
    full_name: str,
    password: str,
    default_surface: str,
    allowed_surfaces: list[str] | None = None,
    password_hasher: PasswordHasher,
) -> User:
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    password_hash = password_hasher.hash_password(password)
    resolved_allowed_surfaces = allowed_surfaces or [default_surface]
    if user is None:
        user = User(
            allowed_surfaces=resolved_allowed_surfaces,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            default_surface=default_surface,
            is_active=True,
        )
        session.add(user)
        session.flush()
        return user

    user.full_name = full_name
    user.password_hash = password_hash
    user.allowed_surfaces = resolved_allowed_surfaces
    user.default_surface = default_surface
    user.is_active = True
    user.is_locked = False
    session.flush()
    return user


def _upsert_assignment(
    session: Session,
    *,
    user_id: uuid.UUID,
    branch_id: uuid.UUID,
    is_default: bool = False,
) -> UserBranchAssignment:
    assignment = session.execute(
        select(UserBranchAssignment).where(
            UserBranchAssignment.user_id == user_id,
            UserBranchAssignment.branch_id == branch_id,
        )
    ).scalar_one_or_none()
    if assignment is None:
        assignment = UserBranchAssignment(
            user_id=user_id,
            branch_id=branch_id,
            is_active=True,
            is_default=is_default,
        )
        session.add(assignment)
        session.flush()
        return assignment

    assignment.is_active = True
    assignment.is_default = is_default
    session.flush()
    return assignment


def _seed_permissions(session: Session) -> dict[str, Permission]:
    permissions: dict[str, Permission] = {}
    for definition in PERMISSION_CATALOG:
        permission = session.execute(
            select(Permission).where(Permission.code == definition.code)
        ).scalar_one_or_none()
        if permission is None:
            permission = Permission(code=definition.code)
            session.add(permission)
        permission.label = definition.label
        permission.description = definition.description
        permission.module = definition.module
        permission.module_label = definition.module_label
        permission.action = definition.action
        permission.surfaces = list(definition.surfaces)
        permission.is_sensitive = definition.is_sensitive
        permission.is_active = True
        session.flush()
        permissions[definition.code] = permission
    return permissions


def _upsert_role(
    session: Session,
    *,
    code: str,
    name: str,
    description: str,
    surfaces: list[str],
    permission_codes: list[str],
    permissions: dict[str, Permission],
    is_system: bool,
) -> Role:
    role = session.execute(select(Role).where(Role.code == code)).scalar_one_or_none()
    if role is None:
        role = Role(code=code)
        session.add(role)
    role.name = name
    role.description = description
    role.surfaces = surfaces
    role.is_active = True
    role.is_system = is_system
    session.flush()

    existing = (
        session.execute(select(RolePermission).where(RolePermission.role_id == role.id))
        .scalars()
        .all()
    )
    for row in existing:
        session.delete(row)
    session.flush()
    for permission_code in permission_codes:
        session.add(
            RolePermission(
                role_id=role.id,
                permission_id=permissions[permission_code].id,
            )
        )
    session.flush()
    return role


def _upsert_user_role_assignment(
    session: Session,
    *,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    assigned_by_user_id: uuid.UUID | None,
) -> UserRoleAssignment:
    assignment = session.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
        )
    ).scalar_one_or_none()
    if assignment is None:
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            assigned_by_user_id=assigned_by_user_id,
            scope_type="BRANCH_SET",
        )
        session.add(assignment)
    assignment.is_active = True
    assignment.assigned_by_user_id = assigned_by_user_id
    session.flush()
    assignment.scope_type = "BRANCH_SET"
    existing_scopes = list(
        session.scalars(
            select(UserRoleAssignmentBranchScope).where(
                UserRoleAssignmentBranchScope.assignment_id == assignment.id,
            )
        )
    )
    for scope in existing_scopes:
        session.delete(scope)
    session.flush()
    branch_ids = list(
        session.scalars(
            select(UserBranchAssignment.branch_id).where(
                UserBranchAssignment.user_id == user_id,
                UserBranchAssignment.is_active.is_(True),
            )
        )
    )
    if not branch_ids:
        raise ValueError("Demo roles require explicit active branch assignments.")
    session.add_all(
        [
            UserRoleAssignmentBranchScope(assignment_id=assignment.id, branch_id=branch_id)
            for branch_id in branch_ids
        ]
    )
    session.flush()
    return assignment


def _upsert_product_class(
    session: Session,
    *,
    brand_id: uuid.UUID,
    code: str,
    name: str,
    quick_name: str | None,
    search_aliases: str | None,
    display_order: int,
    capture_mode_default: str,
    class_capture_unit_price: Decimal | None,
) -> ProductClass:
    product_class = session.execute(
        select(ProductClass).where(ProductClass.code == code)
    ).scalar_one_or_none()
    if product_class is None:
        product_class = ProductClass(
            brand_id=brand_id,
            code=code,
            name=name,
            quick_name=quick_name,
            search_aliases=search_aliases,
            display_order=display_order,
            capture_mode_default=capture_mode_default,
            class_capture_unit_price=class_capture_unit_price,
            currency_code="MXN",
            is_active=True,
            is_sellable=True,
        )
        session.add(product_class)

    product_class.brand_id = brand_id
    product_class.name = name
    product_class.quick_name = quick_name
    product_class.search_aliases = search_aliases
    product_class.display_order = display_order
    product_class.capture_mode_default = capture_mode_default
    product_class.class_capture_unit_price = class_capture_unit_price
    product_class.currency_code = "MXN"
    product_class.is_active = True
    product_class.is_sellable = True
    session.flush()
    return product_class


def _upsert_product(
    session: Session,
    *,
    product_class_id: uuid.UUID,
    code: str,
    name: str,
    quick_name: str | None,
    search_aliases: str | None,
    display_order: int,
    unit_price: Decimal,
) -> Product:
    product = session.execute(select(Product).where(Product.code == code)).scalar_one_or_none()
    if product is None:
        product = Product(
            product_class_id=product_class_id,
            code=code,
            name=name,
            quick_name=quick_name,
            search_aliases=search_aliases,
            display_order=display_order,
            unit_price=unit_price,
            currency_code="MXN",
            is_active=True,
            is_sellable=True,
        )
        session.add(product)

    product.product_class_id = product_class_id
    product.name = name
    product.quick_name = quick_name
    product.search_aliases = search_aliases
    product.display_order = display_order
    product.unit_price = unit_price
    product.currency_code = "MXN"
    product.is_active = True
    product.is_sellable = True
    session.flush()
    return product


def _upsert_waste_reason(
    session: Session,
    *,
    code: str,
    name: str,
    display_order: int,
) -> WasteReason:
    waste_reason = session.execute(
        select(WasteReason).where(WasteReason.code == code)
    ).scalar_one_or_none()
    if waste_reason is None:
        waste_reason = WasteReason(
            code=code,
            name=name,
            is_active=True,
            display_order=display_order,
        )
        session.add(waste_reason)

    waste_reason.name = name
    waste_reason.is_active = True
    waste_reason.display_order = display_order
    session.flush()
    return waste_reason


def _seed_waste_reasons(session: Session) -> None:
    _upsert_waste_reason(
        session,
        code=WASTE_REASON_OLD_COUNTER,
        name="Old Counter",
        display_order=10,
    )
    _upsert_waste_reason(
        session,
        code=WASTE_REASON_DAMAGED,
        name="Damaged",
        display_order=20,
    )
    _upsert_waste_reason(
        session,
        code=WASTE_REASON_CONTAMINATED,
        name="Contaminated",
        display_order=30,
    )
    _upsert_waste_reason(
        session,
        code=WASTE_REASON_EXPIRED,
        name="Expired",
        display_order=40,
    )
    _upsert_waste_reason(
        session,
        code=WASTE_REASON_OTHER,
        name="Other",
        display_order=50,
    )


def _upsert_correction_reason(
    session: Session,
    *,
    code: str,
    name: str,
    display_order: int,
) -> CorrectionReason:
    correction_reason = session.execute(
        select(CorrectionReason).where(CorrectionReason.code == code)
    ).scalar_one_or_none()
    if correction_reason is None:
        correction_reason = CorrectionReason(
            code=code,
            name=name,
            is_active=True,
            display_order=display_order,
        )
        session.add(correction_reason)

    correction_reason.name = name
    correction_reason.is_active = True
    correction_reason.display_order = display_order
    session.flush()
    return correction_reason


def _seed_correction_reasons(session: Session) -> None:
    _upsert_correction_reason(
        session,
        code=CORRECTION_REASON_WRONG_QUANTITY,
        name="Wrong Quantity",
        display_order=10,
    )
    _upsert_correction_reason(
        session,
        code=CORRECTION_REASON_WRONG_PRODUCT,
        name="Wrong Product",
        display_order=20,
    )
    _upsert_correction_reason(
        session,
        code=CORRECTION_REASON_DUPLICATE_CAPTURE,
        name="Duplicate Capture",
        display_order=30,
    )
    _upsert_correction_reason(
        session,
        code=CORRECTION_REASON_DAMAGED_DURING_HANDLING,
        name="Damaged During Handling",
        display_order=40,
    )
    _upsert_correction_reason(
        session,
        code=CORRECTION_REASON_COUNT_MISMATCH,
        name="Count Mismatch",
        display_order=50,
    )
    _upsert_correction_reason(
        session,
        code=CORRECTION_REASON_WRONG_DESTINATION,
        name="Wrong Destination",
        display_order=60,
    )
    _upsert_correction_reason(
        session,
        code=CORRECTION_REASON_OTHER,
        name="Other",
        display_order=70,
    )


def _upsert_payment_category(
    session: Session,
    *,
    code: str,
    name: str,
    display_order: int,
) -> OperationalPaymentCategory:
    category = session.execute(
        select(OperationalPaymentCategory).where(OperationalPaymentCategory.code == code)
    ).scalar_one_or_none()
    if category is None:
        category = OperationalPaymentCategory(
            code=code,
            name=name,
            is_active=True,
            display_order=display_order,
        )
        session.add(category)

    category.name = name
    category.is_active = True
    category.display_order = display_order
    session.flush()
    return category


def _seed_payment_categories(session: Session) -> None:
    _upsert_payment_category(
        session,
        code=PAYMENT_CATEGORY_GAS,
        name="Gasolina",
        display_order=10,
    )
    _upsert_payment_category(
        session,
        code=PAYMENT_CATEGORY_SUPPLIER,
        name="Proveedor",
        display_order=20,
    )
    _upsert_payment_category(
        session,
        code=PAYMENT_CATEGORY_SERVICES,
        name="Servicios",
        display_order=30,
    )
    _upsert_payment_category(
        session,
        code=PAYMENT_CATEGORY_LOGISTICS,
        name="Logistica",
        display_order=40,
    )
    _upsert_payment_category(
        session,
        code=PAYMENT_CATEGORY_PURCHASE,
        name="Compra urgente",
        display_order=50,
    )
    _upsert_payment_category(
        session,
        code=PAYMENT_CATEGORY_OTHER,
        name="Otro",
        display_order=60,
    )


def _upsert_discount_category(
    session: Session,
    *,
    code: str,
    name: str,
    display_order: int,
) -> OperationalDiscountCategory:
    category = session.execute(
        select(OperationalDiscountCategory).where(OperationalDiscountCategory.code == code)
    ).scalar_one_or_none()
    if category is None:
        category = OperationalDiscountCategory(
            code=code,
            name=name,
            is_active=True,
            display_order=display_order,
        )
        session.add(category)

    category.name = name
    category.is_active = True
    category.display_order = display_order
    session.flush()
    return category


def _seed_discount_categories(session: Session) -> None:
    _upsert_discount_category(
        session,
        code=DISCOUNT_CATEGORY_EMPLOYEE_INSURANCE,
        name="Seguro del empleado",
        display_order=10,
    )
    _upsert_discount_category(
        session,
        code=DISCOUNT_CATEGORY_EMPLOYEE_LOAN,
        name="Prestamo del empleado",
        display_order=20,
    )
    _upsert_discount_category(
        session,
        code=DISCOUNT_CATEGORY_INTERNAL_CHARGE,
        name="Cargo interno",
        display_order=30,
    )
    _upsert_discount_category(
        session,
        code=DISCOUNT_CATEGORY_PAYROLL_ADVANCE_ADJUSTMENT,
        name="Ajuste de adelanto de nomina",
        display_order=40,
    )
    _upsert_discount_category(
        session,
        code=DISCOUNT_CATEGORY_OTHER,
        name="Otro",
        display_order=50,
    )


def _seed_pos_catalog(session: Session, *, brand_id: uuid.UUID) -> None:
    pan_dulce = _upsert_product_class(
        session,
        brand_id=brand_id,
        code=SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
        name="Pan dulce",
        quick_name="Dulce",
        search_aliases="pan dulce dulce pieza concha cuerno",
        display_order=10,
        capture_mode_default=CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
        class_capture_unit_price=Decimal("12.00"),
    )
    bolillo = _upsert_product_class(
        session,
        brand_id=brand_id,
        code=SEED_PRODUCT_CLASS_BOLILLO_CODE,
        name="Bolillo",
        quick_name="Bolillo",
        search_aliases="bolillo pan salado",
        display_order=20,
        capture_mode_default=CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
        class_capture_unit_price=Decimal("3.00"),
    )
    telera = _upsert_product_class(
        session,
        brand_id=brand_id,
        code=SEED_PRODUCT_CLASS_TELERA_CODE,
        name="Telera",
        quick_name="Telera",
        search_aliases="telera pan sandwich",
        display_order=30,
        capture_mode_default=CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
        class_capture_unit_price=Decimal("4.00"),
    )
    bebidas = _upsert_product_class(
        session,
        brand_id=brand_id,
        code=SEED_PRODUCT_CLASS_BEBIDAS_CODE,
        name="Bebidas",
        quick_name="Bebidas",
        search_aliases="bebidas refrescos cafe",
        display_order=110,
        capture_mode_default=CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
        class_capture_unit_price=None,
    )
    pasteles = _upsert_product_class(
        session,
        brand_id=brand_id,
        code=SEED_PRODUCT_CLASS_PASTELES_CODE,
        name="Pasteles",
        quick_name="Pasteles",
        search_aliases="pasteles postres rebanadas",
        display_order=120,
        capture_mode_default=CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
        class_capture_unit_price=None,
    )

    _upsert_product(
        session,
        product_class_id=pan_dulce.id,
        code=SEED_PRODUCT_CONCHA_VAN_CODE,
        name="Vanilla Concha",
        quick_name="Concha Van",
        search_aliases="concha vainilla pan dulce",
        display_order=10,
        unit_price=Decimal("12.00"),
    )
    _upsert_product(
        session,
        product_class_id=pan_dulce.id,
        code=SEED_PRODUCT_CONCHA_CHOCO_CODE,
        name="Chocolate Concha",
        quick_name="Concha Choco",
        search_aliases="concha chocolate pan dulce",
        display_order=20,
        unit_price=Decimal("12.00"),
    )
    _upsert_product(
        session,
        product_class_id=pan_dulce.id,
        code=SEED_PRODUCT_CUERNO_MANTEQUILLA_CODE,
        name="Butter Croissant",
        quick_name="Cuerno",
        search_aliases="cuerno mantequilla croissant pan dulce",
        display_order=30,
        unit_price=Decimal("14.00"),
    )
    _upsert_product(
        session,
        product_class_id=bolillo.id,
        code=SEED_PRODUCT_BOLILLO_STD_CODE,
        name="Standard Bolillo",
        quick_name="Bolillo Std",
        search_aliases="bolillo standard",
        display_order=10,
        unit_price=Decimal("3.00"),
    )
    _upsert_product(
        session,
        product_class_id=telera.id,
        code=SEED_PRODUCT_TELERA_STD_CODE,
        name="Standard Telera",
        quick_name="Telera Std",
        search_aliases="telera standard",
        display_order=10,
        unit_price=Decimal("4.00"),
    )
    _upsert_product(
        session,
        product_class_id=bebidas.id,
        code=SEED_PRODUCT_COCA_355_CODE,
        name="Coca-Cola 355 ml",
        quick_name="Coca 355",
        search_aliases="coca cola refresco",
        display_order=10,
        unit_price=Decimal("18.00"),
    )
    _upsert_product(
        session,
        product_class_id=bebidas.id,
        code=SEED_PRODUCT_CAFE_AMERICANO_CODE,
        name="Cafe americano",
        quick_name="Americano",
        search_aliases="cafe americano bebida caliente",
        display_order=20,
        unit_price=Decimal("22.00"),
    )
    _upsert_product(
        session,
        product_class_id=pasteles.id,
        code=SEED_PRODUCT_PASTEL_CHOC_IND_CODE,
        name="Individual Chocolate Cake",
        quick_name="Chocolate",
        search_aliases="pastel chocolate individual",
        display_order=10,
        unit_price=Decimal("48.00"),
    )
    _upsert_product(
        session,
        product_class_id=pasteles.id,
        code=SEED_PRODUCT_REBANADA_TRES_LECHES_CODE,
        name="Tres Leches Slice",
        quick_name="Tres Leches",
        search_aliases="rebanada tres leches",
        display_order=20,
        unit_price=Decimal("38.00"),
    )


def seed_local_data(session: Session) -> None:
    password_hasher = PasswordHasher()
    el_mejor_pan_brand = _upsert_brand(
        session,
        code=SEED_BRAND_EL_MEJOR_PAN_CODE,
        name=SEED_BRAND_EL_MEJOR_PAN_NAME,
    )
    merenna_brand = _upsert_brand(
        session,
        code=SEED_BRAND_MERENNA_CODE,
        name=SEED_BRAND_MERENNA_NAME,
    )

    main_branch = _upsert_branch(
        session,
        brand_id=el_mejor_pan_brand.id,
        code=SEED_BRANCH_CODE,
        name=SEED_BRANCH_NAME,
        timezone=SEED_BRANCH_TIMEZONE,
    )
    north_branch = _upsert_branch(
        session,
        brand_id=merenna_brand.id,
        code=SEED_DESTINATION_BRANCH_CODE,
        name=SEED_DESTINATION_BRANCH_NAME,
        timezone=SEED_DESTINATION_BRANCH_TIMEZONE,
    )
    south_branch = _upsert_branch(
        session,
        brand_id=el_mejor_pan_brand.id,
        code=SEED_ALT_DESTINATION_BRANCH_CODE,
        name=SEED_ALT_DESTINATION_BRANCH_NAME,
        timezone=SEED_ALT_DESTINATION_BRANCH_TIMEZONE,
    )

    _upsert_workstation(
        session,
        branch_id=main_branch.id,
        code=SEED_WORKSTATION_CODE,
        name=SEED_WORKSTATION_NAME,
    )
    _upsert_workstation(
        session,
        branch_id=north_branch.id,
        code=SEED_DESTINATION_WORKSTATION_CODE,
        name=SEED_DESTINATION_WORKSTATION_NAME,
    )
    _upsert_workstation(
        session,
        branch_id=south_branch.id,
        code=SEED_ALT_DESTINATION_WORKSTATION_CODE,
        name=SEED_ALT_DESTINATION_WORKSTATION_NAME,
    )

    user = _upsert_user(
        session,
        email=SEED_USER_EMAIL,
        full_name=SEED_USER_FULL_NAME,
        password=SEED_USER_PASSWORD,
        default_surface=IDENTITY_SURFACE_POS,
        allowed_surfaces=[IDENTITY_SURFACE_POS],
        password_hasher=password_hasher,
    )
    admin_user = _upsert_user(
        session,
        email=SEED_ADMIN_EMAIL,
        full_name=SEED_ADMIN_FULL_NAME,
        password=SEED_ADMIN_PASSWORD,
        default_surface=IDENTITY_SURFACE_BACKOFFICE,
        allowed_surfaces=[IDENTITY_SURFACE_BACKOFFICE],
        password_hasher=password_hasher,
    )
    _upsert_assignment(session, user_id=user.id, branch_id=main_branch.id, is_default=True)
    _upsert_assignment(session, user_id=user.id, branch_id=north_branch.id)
    _upsert_assignment(session, user_id=user.id, branch_id=south_branch.id)
    _upsert_assignment(session, user_id=admin_user.id, branch_id=main_branch.id, is_default=True)
    _upsert_assignment(session, user_id=admin_user.id, branch_id=north_branch.id)
    _upsert_assignment(session, user_id=admin_user.id, branch_id=south_branch.id)
    permissions = _seed_permissions(session)
    admin_role = _upsert_role(
        session,
        code=IDENTITY_ROLE_ADMIN,
        name="Administrador",
        description="Administración de demostración limitada a sucursales asignadas.",
        surfaces=[IDENTITY_SURFACE_BACKOFFICE],
        permission_codes=[code for code in permissions if code != "pos.operate"],
        permissions=permissions,
        is_system=True,
    )
    cashier_role = _upsert_role(
        session,
        code=IDENTITY_ROLE_CASHIER,
        name="Cajero POS",
        description="Operacion basica de punto de venta en sucursales asignadas.",
        surfaces=[IDENTITY_SURFACE_POS],
        permission_codes=list(POS_PERMISSION_CODES),
        permissions=permissions,
        is_system=True,
    )
    _upsert_role(
        session,
        code=IDENTITY_ROLE_BRANCH_MANAGER,
        name="Encargado de sucursal",
        description="Gestion operativa de sucursal con consulta financiera y calidad.",
        surfaces=[IDENTITY_SURFACE_POS, IDENTITY_SURFACE_BACKOFFICE],
        permission_codes=[
            "pos.operate",
            "sales_tickets.view",
            "orders.manage",
            "returns_corrections.manage",
            "inventory.adjust",
            "cash_finance.view",
            "quality_hygiene.manage",
            "reports.export",
        ],
        permissions=permissions,
        is_system=True,
    )
    _upsert_user_role_assignment(
        session,
        user_id=user.id,
        role_id=cashier_role.id,
        assigned_by_user_id=admin_user.id,
    )
    _upsert_user_role_assignment(
        session,
        user_id=admin_user.id,
        role_id=admin_role.id,
        assigned_by_user_id=admin_user.id,
    )
    _seed_pos_catalog(session, brand_id=el_mejor_pan_brand.id)
    _seed_waste_reasons(session)
    _seed_correction_reasons(session)
    _seed_payment_categories(session)
    _seed_discount_categories(session)


def main() -> int:
    settings = get_settings()
    wait_for_database(str(settings.database_url))

    with SessionLocal() as session:
        seed_local_data(session)
        session.commit()

    print(
        "Seeded branches "
        f"{SEED_BRANCH_CODE}, {SEED_DESTINATION_BRANCH_CODE}, "
        f"and {SEED_ALT_DESTINATION_BRANCH_CODE}, workstations "
        f"{SEED_WORKSTATION_CODE}, {SEED_DESTINATION_WORKSTATION_CODE}, "
        f"and {SEED_ALT_DESTINATION_WORKSTATION_CODE}."
    )
    print(f"Seeded cashier {SEED_USER_EMAIL} with password {SEED_USER_PASSWORD}.")
    print(f"Seeded admin {SEED_ADMIN_EMAIL} with password {SEED_ADMIN_PASSWORD}.")
    print(
        "Seeded operational catalog products, waste reasons, correction reasons, "
        "payment categories, discount categories, and cash close payment-method defaults."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
