from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Column, Delete, Select, Table, and_, event, false, inspect, or_, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import (
    InstrumentedAttribute,
    Mapper,
    ORMExecuteState,
    Session,
    SessionTransaction,
    with_loader_criteria,
)
from sqlalchemy.orm.util import AliasedClass, AliasedInsp
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ClauseElement, ColumnElement, TextClause

from zeromerma_api.db.base import Base
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.idempotency.application.context import (
    authorization_boundary_initialization,
    metadata_statement_allowed,
    record_mutation_allowed,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    CapabilityCode,
    IdentitySurface,
)
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.identity.infrastructure.privileged_models import IdentityPrivilegeState
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent

AUTHORIZATION_METADATA_OPTION = "zeromerma_authorization_metadata"
_CONTEXT_KEY = "zeromerma_authorization_scope"
_IDENTITY_CAPABILITIES = frozenset({"users.manage", "roles.manage", "role_assignments.manage"})
_NON_ECONOMIC_CAPABILITIES = frozenset(
    {
        "branches.manage",
        "workstations.manage",
        "quality_hygiene.manage",
        "users.manage",
        "roles.manage",
        "role_assignments.manage",
        "audit.export",
        "reports.export",
    }
)

# Every persisted family is classified. New branch-bearing tables require an explicit rule.
DIRECT_SCOPE_COLUMNS: dict[str, tuple[str, ...]] = {
    "audit_log": ("branch_id",),
    "workstations": ("branch_id",),
    "cash_sessions": ("branch_id",),
    "cash_session_closes": ("branch_id",),
    "financial_reconciliations": ("branch_id",),
    "financial_operations": ("branch_id",),
    "financial_entries": ("branch_id",),
    "branch_counter_snapshots": ("branch_id",),
    "correction_documents": ("source_branch_id", "corrected_destination_branch_id"),
    "operational_discounts": ("branch_id",),
    "inventory_balances": ("branch_id",),
    "inventory_adjustments": ("branch_id",),
    "inventory_movements": ("branch_id",),
    "operation_documents": ("source_branch_id", "destination_branch_id"),
    "customer_orders": ("branch_id",),
    "operational_payments": ("branch_id",),
    "production_batches": ("branch_id",),
    "purchase_documents": ("receiving_branch_id",),
    "cleaning_logs": ("branch_id",),
    "sanitary_verifications": ("branch_id",),
    "equipment_assets": ("branch_id",),
    "quality_incidents": ("branch_id",),
    "sale_returns": ("branch_id",),
    "sales": ("branch_id",),
    "cash_movements": ("branch_id",),
    "supplier_branches": ("branch_id",),
    "branches": ("id",),
}
PARENT_SCOPE_COLUMNS: dict[str, tuple[str, ...]] = {
    "cash_session_close_payment_method_counts": ("cash_session_close_id",),
    "cash_session_close_product_counts": ("cash_session_close_id",),
    "cash_session_close_class_reconciliations": ("cash_session_close_id",),
    "cash_session_close_reconciliation_attributions": ("cash_session_close_id",),
    "cash_session_close_discrepancy_resolutions": ("cash_session_close_id",),
    "cash_session_close_issues": ("cash_session_close_id",),
    "branch_counter_snapshot_lines": ("snapshot_id",),
    "correction_document_lines": ("correction_document_id",),
    "operation_document_lines": ("operation_document_id",),
    "customer_order_items": ("customer_order_id",),
    "customer_order_payments": ("customer_order_id",),
    "production_batch_inputs": ("production_batch_id",),
    "purchase_document_lines": ("purchase_document_id",),
    "purchase_receipts": ("purchase_document_id",),
    "purchase_receipt_lines": ("purchase_receipt_id",),
    "cleaning_log_checklist_items": ("cleaning_log_id",),
    "sanitary_verification_checklist_items": ("verification_id",),
    "equipment_maintenance_records": ("equipment_id",),
    "quality_incident_follow_ups": ("incident_id",),
    "sale_return_lines": ("sale_return_id",),
    "sale_lines": ("sale_id",),
    "sale_payments": ("sale_id",),
}
SHARED_TABLES = frozenset(
    {
        "brands",
        "product_classes",
        "products",
        "recipes",
        "recipe_inputs",
        "system_settings",
        "system_setting_history",
        "correction_reasons",
        "operational_discount_categories",
        "commercial_discounts",
        "waste_reasons",
        "operational_payment_categories",
        "cleaning_templates",
        "cleaning_template_items",
        "sanitary_verification_templates",
        "sanitary_verification_template_items",
        "suppliers",
        "supplier_contacts",
        "supplier_products",
    }
)
IDENTITY_METADATA_TABLES = frozenset(
    {
        "users",
        "user_branch_assignments",
        "roles",
        "permissions",
        "role_permissions",
        "user_role_assignment_branch_scopes",
        "user_role_assignments",
        "identity_privilege_state",
        "identity_privileged_changes",
        "identity_recovery_credentials",
        "auth_sessions",
        "auth_login_limits",
        "password_reset_credentials",
    }
)
_BULK_DELETE_TABLES = frozenset(
    {
        "production_batch_inputs",
        "operation_document_lines",
        "system_settings",
    }
)
_TRACE_TABLES = frozenset({"audit_log", "outbox_events"})
COMMAND_METADATA_TABLES = frozenset({IdempotencyRecord.__tablename__})


@dataclass
class TransferReceiptCause:
    shipment: OperationDocument
    receipt: OperationDocument
    transaction: SessionTransaction
    workstation_id: UUID
    actor_id: UUID


@dataclass
class AuthorizationScope:
    user: AuthenticatedUser
    capabilities: tuple[CapabilityCode, ...]
    surface: IdentitySurface | None
    mutation: bool
    global_only: bool
    request_id: str | None
    branch_ids: frozenset[UUID] | None
    identity_mutation: bool
    resource_branch_ids: set[UUID] = field(default_factory=set)
    transfer_receipts: dict[OperationDocument, SessionTransaction] = field(default_factory=dict)
    received_shipments: dict[OperationDocument, TransferReceiptCause] = field(default_factory=dict)
    validating: bool = False

    @property
    def economic(self) -> bool:
        return self.mutation and not set(self.capabilities).issubset(_NON_ECONOMIC_CAPABILITIES)


def _deny(message: str = "This operation is outside your branch scope.") -> HTTPException:
    return HTTPException(status_code=403, detail=message)


def authorization_scope(session: Session) -> AuthorizationScope | None:
    value = session.info.get(_CONTEXT_KEY)
    return value if isinstance(value, AuthorizationScope) else None


def _models() -> dict[str, type[Base]]:
    return {
        _table(cast(type[Base], mapper.class_)).name: cast(type[Base], mapper.class_)
        for mapper in Base.registry.mappers
    }


def _table(model: type[Base]) -> Table:
    table = inspect(model).local_table
    if not isinstance(table, Table):
        raise _deny("Mapped branch ownership requires a declared table.")
    return table


def _value(instance: Base, name: str) -> object:
    return getattr(instance, name)


def _column(model: type[Base] | AliasedClass[Base], name: str) -> InstrumentedAttribute[Any]:
    return cast(InstrumentedAttribute[Any], getattr(model, name))


def _intersection(
    user: AuthenticatedUser, capabilities: tuple[CapabilityCode, ...], *, global_only: bool
) -> frozenset[UUID] | None:
    branches: set[UUID] | None = None
    for capability in capabilities:
        grant = require_branches(user, capability, (), global_only=global_only)
        if grant.scope_type == "BRANCH_SET":
            branches = (
                set(grant.branch_ids)
                if branches is None
                else branches.intersection(grant.branch_ids)
            )
    if branches is not None and not branches:
        raise _deny()
    return None if branches is None else frozenset(branches)


def _lock_boundary(session: Session, *, exclusive: bool) -> None:
    if exclusive:
        from zeromerma_api.modules.identity.application.privileged_access import (
            lock_privileged_lifecycle,
        )

        lock_privileged_lifecycle(session)
        return
    statement = (
        select(IdentityPrivilegeState.id)
        .where(IdentityPrivilegeState.id == 1)
        .with_for_update(read=True)
    )
    if session.scalar(statement) is None:
        with authorization_boundary_initialization(session):
            session.execute(insert(IdentityPrivilegeState).values(id=1).on_conflict_do_nothing())
        if session.scalar(statement) is None:
            raise _deny("The authorization boundary is unavailable.")


def bind_authorization_scope(
    session: Session,
    *,
    user: AuthenticatedUser,
    capabilities: tuple[CapabilityCode, ...],
    mutation: bool,
    global_only: bool = False,
    request_id: str | None = None,
    surface: IdentitySurface | None = None,
) -> AuthorizationScope:
    install_scope_guards()
    identity_mutation = mutation and bool(set(capabilities).intersection(_IDENTITY_CAPABILITIES))
    if mutation:
        _lock_boundary(session, exclusive=identity_mutation)
    refreshed = resolve_authorization(session, user, surface=surface)
    branches = _intersection(refreshed, capabilities, global_only=global_only)
    # Authentication may have populated the identity map before the scope was installed.
    # Detach those clean objects so Session.get cannot reuse an unscoped cached entity.
    if session.new or session.dirty or session.deleted:
        raise _deny("Authorization must be established before changing data.")
    session.expunge_all()
    context = AuthorizationScope(
        user=refreshed,
        capabilities=capabilities,
        surface=surface,
        mutation=mutation,
        global_only=global_only,
        request_id=request_id,
        branch_ids=branches,
        identity_mutation=identity_mutation,
    )
    session.info[_CONTEXT_KEY] = context
    user.effective_grants = refreshed.effective_grants
    user.authorization_version = refreshed.authorization_version
    user.authorization_surface = refreshed.authorization_surface
    user.is_superadministrator = refreshed.is_superadministrator
    return context


def require_session_capabilities(
    session: Session, capabilities: Iterable[CapabilityCode]
) -> AuthorizationScope:
    context = authorization_scope(session)
    if context is None:
        raise _deny("An explicit authorization context is required.")
    combined = tuple(dict.fromkeys((*context.capabilities, *capabilities)))
    branches = _intersection(context.user, combined, global_only=context.global_only)
    if session.new or session.dirty or session.deleted:
        raise _deny("Required capabilities must be declared before changing data.")
    session.expunge_all()
    context.capabilities = combined
    context.branch_ids = branches
    return context


def session_allows_capabilities(session: Session, capabilities: Iterable[CapabilityCode]) -> bool:
    context = authorization_scope(session)
    if context is None:
        return False
    try:
        _intersection(
            context.user,
            tuple(dict.fromkeys((*context.capabilities, *capabilities))),
            global_only=context.global_only,
        )
    except HTTPException:
        return False
    return True


@contextmanager
def scoped_session_capabilities(
    session: Session, capabilities: Iterable[CapabilityCode]
) -> Iterator[None]:
    context = authorization_scope(session)
    if context is None:
        raise _deny("An explicit authorization context is required.")
    previous = context.capabilities, context.branch_ids
    require_session_capabilities(session, capabilities)
    try:
        yield
    finally:
        if session.new or session.dirty or session.deleted:
            raise _deny("A temporary read scope cannot change records.")
        session.expunge_all()
        context.capabilities, context.branch_ids = previous


def _parent(
    table: Table, column_name: str, models: dict[str, type[Base]]
) -> tuple[type[Base], str]:
    foreign_keys = list(table.c[column_name].foreign_keys)
    if len(foreign_keys) != 1:
        raise _deny("A branch ownership relationship is not classified.")
    column = foreign_keys[0].column
    model = models.get(column.table.name)
    if model is None:
        raise _deny("A branch ownership relationship is unavailable.")
    return model, column.name


def _trace_predicate(
    model: type[Base], allowed: frozenset[UUID], entity: AliasedClass[Base] | None = None
) -> ColumnElement[bool]:
    table_name = _table(model).name
    attribute = _column(
        entity if entity is not None else model,
        "metadata_" if table_name == "audit_log" else "headers",
    )
    provenance = attribute["authorization"]
    branches = provenance["branch_ids"].cast(JSONB)
    return and_(
        provenance["scope_type"].as_string() == "BRANCH_SET",
        branches != [],
        branches.contained_by([str(branch_id) for branch_id in sorted(allowed, key=str)]),
    )


def _predicate(
    model: type[Base],
    allowed: frozenset[UUID],
    models: dict[str, type[Base]],
    *,
    entity: AliasedClass[Base] | None = None,
) -> ColumnElement[bool]:
    table = _table(model)
    name = table.name
    scoped_model = entity if entity is not None else model
    if name == "outbox_events":
        return _trace_predicate(model, allowed, entity)
    conditions: list[ColumnElement[bool]] = []
    for column_name in DIRECT_SCOPE_COLUMNS.get(name, ()):
        attribute = _column(scoped_model, column_name)
        condition: ColumnElement[bool] = attribute.in_(allowed)
        if name == "audit_log":
            metadata = _column(scoped_model, "metadata_")
            condition = and_(
                or_(condition, attribute.is_(None)),
                or_(
                    _trace_predicate(model, allowed, entity),
                    and_(attribute.is_not(None), metadata["authorization"].is_(None)),
                ),
            )
        elif table.c[column_name].nullable:
            condition = or_(attribute.is_(None), condition)
        conditions.append(condition)
    parent_columns = PARENT_SCOPE_COLUMNS.get(name, ())
    if name == "correction_documents":
        parent_columns = (*parent_columns, "target_document_id")
    for column_name in parent_columns:
        parent_model, parent_key = _parent(table, column_name, models)
        permitted_parent_ids = select(_column(parent_model, parent_key)).where(
            _predicate(parent_model, allowed, models),
        )
        conditions.append(_column(scoped_model, column_name).in_(permitted_parent_ids))
    return and_(*conditions) if conditions else false()


def _statement_tables(statement: Any) -> set[str]:
    return {
        node.name
        for node in visitors.iterate(cast(ClauseElement, statement))
        if isinstance(node, Table)
    }


def _scope_statement(state: ORMExecuteState) -> None:
    context = authorization_scope(state.session)
    if context is None:
        return
    statement = state.statement
    tables = _statement_tables(statement)
    if metadata_statement_allowed(state.session, statement):
        return
    if tables.intersection(COMMAND_METADATA_TABLES):
        raise _deny("Idempotency records require the canonical command boundary.")
    if any(
        isinstance(node, TextClause) for node in visitors.iterate(cast(ClauseElement, statement))
    ):
        raise _deny("Unclassified SQL is not permitted in an authorized operation.")
    if state.execution_options.get(AUTHORIZATION_METADATA_OPTION):
        if not isinstance(statement, Select) or not tables.issubset(
            IDENTITY_METADATA_TABLES | {"branches"}
        ):
            raise _deny("Authorization metadata access cannot query operational records.")
        return
    known = (
        set(DIRECT_SCOPE_COLUMNS)
        | set(PARENT_SCOPE_COLUMNS)
        | SHARED_TABLES
        | IDENTITY_METADATA_TABLES
        | {"outbox_events"}
    )
    if tables - known:
        raise _deny("A queried entity has no branch ownership policy.")
    if tables and tables.issubset(IDENTITY_METADATA_TABLES):
        if isinstance(statement, Select) or context.identity_mutation:
            return
        raise _deny("Identity mutations require explicit identity authority.")
    if isinstance(statement, Delete):
        if (
            not context.mutation
            or not state.is_orm_statement
            or not tables.issubset(_BULK_DELETE_TABLES)
        ):
            raise _deny("This bulk mutation has no authorization policy.")
    elif not isinstance(statement, Select):
        raise _deny("This database command has no authorization policy.")
    if context.branch_ids is None:
        return
    models = _models()
    scoped_tables = tables.intersection(
        set(DIRECT_SCOPE_COLUMNS) | set(PARENT_SCOPE_COLUMNS) | {"outbox_events"}
    )
    annotated_tables: set[str] = set()
    nodes = tuple(visitors.iterate(cast(ClauseElement, statement)))
    mapped_aliases = {
        id(entity.selectable): entity
        for node in nodes
        if isinstance(entity := getattr(node, "_annotations", {}).get("parententity"), AliasedInsp)
    }
    for node in nodes:
        annotations = getattr(node, "_annotations", {})
        mapper = annotations.get("parentmapper")
        if isinstance(node, Select):
            for source in (*node._raw_columns, *node._from_obj):
                if (
                    isinstance(source, Table)
                    and source.name in scoped_tables
                    and not source._annotations.get("parentmapper")
                ):
                    raise _deny("Operational subqueries must declare mapped branch ownership.")
                for projected in visitors.iterate(source):
                    if not isinstance(projected, Column):
                        continue
                    column_owner = getattr(projected.table, "original", projected.table)
                    if (
                        isinstance(column_owner, Table)
                        and column_owner.name in scoped_tables
                        and not projected._annotations.get("parentmapper")
                    ):
                        raise _deny("Operational projections must declare mapped branch ownership.")
        if isinstance(mapper, Mapper):
            annotated_tables.add(_table(cast(type[Base], mapper.class_)).name)
        original = getattr(node, "original", None)
        if (
            isinstance(original, Table)
            and original.name in scoped_tables
            and id(cast(ClauseElement, node)._deannotate()) not in mapped_aliases
        ):
            raise _deny("Core aliases must declare mapped branch ownership.")
    if scoped_tables - annotated_tables:
        raise _deny("Operational queries must use mapped branch ownership.")
    for name in sorted(scoped_tables):
        model = models.get(name)
        if model is not None:
            statement = statement.options(
                with_loader_criteria(
                    model,
                    _predicate(model, context.branch_ids, models),
                    include_aliases=False,
                )
            )
    for alias in mapped_aliases.values():
        model = cast(type[Base], alias.mapper.class_)
        if _table(model).name not in scoped_tables:
            continue
        alias_entity = cast(AliasedClass[Base], alias.entity)
        statement = statement.options(
            with_loader_criteria(
                alias_entity,
                _predicate(model, context.branch_ids, models, entity=alias_entity),
                include_aliases=False,
            )
        )
    state.statement = statement


def _reference(session: Session, model: type[Base], key: str, identifier: object) -> Base:
    for candidate in session.new:
        if isinstance(candidate, model) and getattr(candidate, key) == identifier:
            return candidate
    statement = select(model).where(_column(model, key) == identifier)
    result = session.scalar(statement)
    if result is None:
        raise _deny("A referenced record is unavailable in the authorized scope.")
    return result


def _entity_branches(
    session: Session,
    instance: Base,
    models: dict[str, type[Base]],
    trail: frozenset[tuple[str, str]] = frozenset(),
) -> set[UUID]:
    table = _table(type(instance))
    name = table.name
    marker = (name, str(getattr(instance, "id", id(instance))))
    if marker in trail:
        raise _deny("A branch ownership relationship is cyclic.")
    branches: set[UUID] = set()
    for column_name in DIRECT_SCOPE_COLUMNS.get(name, ()):
        value = getattr(instance, column_name)
        if value is None:
            if not table.c[column_name].nullable:
                raise _deny("A branch-owned record requires a branch.")
        elif isinstance(value, UUID):
            branches.add(value)
        else:
            raise _deny("A branch identifier is invalid.")
    parent_columns = PARENT_SCOPE_COLUMNS.get(name, ())
    if name == "correction_documents":
        parent_columns = (*parent_columns, "target_document_id")
    for column_name in parent_columns:
        value = getattr(instance, column_name)
        if value is None:
            raise _deny("A branch-owned record requires its parent.")
        parent_model, parent_key = _parent(table, column_name, models)
        parent = _reference(session, parent_model, parent_key, value)
        branches.update(_entity_branches(session, parent, models, trail | {marker}))
    return branches


def _has_live_transfer_receipt(session: Session, cause: TransferReceiptCause) -> bool:
    shipment, receipt = cause.shipment, cause.receipt
    shipment_state, receipt_state = inspect(shipment), inspect(receipt)
    return (
        cause.transaction is session.get_transaction()
        and shipment_state.session is session
        and shipment_state.persistent
        and shipment not in session.deleted
        and receipt_state.session is session
        and receipt_state.persistent
        and receipt not in session.deleted
        and shipment.document_type == "BRANCH_TRANSFER_SHIPMENT"
        and shipment.status in {"RECEIVED", "RECEIVED_WITH_VARIANCE"}
        and receipt.document_type == "BRANCH_TRANSFER_RECEIPT"
        and receipt.reference_document_id == shipment.id
        and receipt.source_branch_id == shipment.source_branch_id
        and receipt.destination_branch_id == shipment.destination_branch_id
        and receipt.workstation_id == cause.workstation_id
        and receipt.created_by_user_id == cause.actor_id
        and receipt.status == shipment.status
    )


def _received_shipment_cause(
    session: Session,
    context: AuthorizationScope,
    instance: Base,
    workstation_id: UUID | None,
) -> TransferReceiptCause | None:
    if (
        not isinstance(instance, OperationDocument)
        or instance.document_type != "BRANCH_TRANSFER_SHIPMENT"
        or "transfers.execute" not in context.capabilities
        or instance in session.deleted
        or workstation_id is None
    ):
        return None
    state = inspect(instance)
    changed = {attribute.key for attribute in state.attrs if attribute.history.has_changes()}
    if (
        not state.persistent
        or changed != {"status"}
        or list(state.attrs.status.history.deleted) != ["IN_TRANSIT"]
        or instance.status not in {"RECEIVED", "RECEIVED_WITH_VARIANCE"}
    ):
        return None
    for receipt, transaction in context.transfer_receipts.items():
        cause = TransferReceiptCause(
            instance, receipt, transaction, workstation_id, context.user.id
        )
        if _has_live_transfer_receipt(session, cause):
            return cause
    return None


def _validate_transfer_receipt_causes(session: Session, context: AuthorizationScope) -> None:
    for cause in context.received_shipments.values():
        if not _has_live_transfer_receipt(session, cause):
            raise _deny("A received shipment requires its current-transaction receipt.")


def _validate_entity(
    session: Session, context: AuthorizationScope, instance: Base, models: dict[str, type[Base]]
) -> None:
    table = _table(type(instance))
    name = table.name
    if name in COMMAND_METADATA_TABLES:
        if not record_mutation_allowed(session, instance):
            raise _deny("Idempotency records require the canonical command boundary.")
        return
    from zeromerma_api.modules.identity.application.session_services import (
        AUTH_CONTEXT_KEY,
        SessionAuthentication,
    )

    authentication = session.info.get(AUTH_CONTEXT_KEY)
    receipt_cause = None
    if isinstance(authentication, SessionAuthentication):
        if name == "auth_sessions" and getattr(instance, "id", None) == authentication.record.id:
            changed = {
                attribute.key
                for attribute in inspect(instance).attrs
                if attribute.history.has_changes()
            }
            if changed <= {"last_activity_at", "idle_expires_at"}:
                return
        if (
            authentication.record.audience == "POS"
            and "workstation_id" in table.c
            and name not in _TRACE_TABLES
        ):
            state = inspect(instance)
            history = state.attrs.workstation_id.history
            workstation_ids = {
                _value(instance, "workstation_id"),
                *history.deleted,
            }
            if state.persistent and history.has_changes() and not history.deleted:
                # Assigning an expired attribute can omit its original value from ORM history.
                assert state.identity is not None
                workstation_ids.add(
                    session.scalar(
                        select(_column(type(instance), "workstation_id")).where(
                            *(
                                _column(
                                    type(instance), state.mapper.get_property_by_column(key).key
                                )
                                == value
                                for key, value in zip(
                                    state.mapper.primary_key, state.identity, strict=True
                                )
                            )
                        )
                    )
                )
            workstation_ids -= {None, authentication.record.workstation_id}
            if workstation_ids:
                receipt_cause = _received_shipment_cause(
                    session, context, instance, authentication.record.workstation_id
                )
                if receipt_cause is None:
                    raise _deny("This POS session is bound to another workstation.")
    if name in IDENTITY_METADATA_TABLES:
        if not context.identity_mutation:
            raise _deny("Identity mutations require explicit identity authority.")
        return
    if name in _TRACE_TABLES:
        if isinstance(instance, AuditLog) and instance.branch_id is not None:
            for capability in context.capabilities:
                require_branches(context.user, capability, [instance.branch_id])
            context.resource_branch_ids.add(instance.branch_id)
        return
    if name in SHARED_TABLES:
        if context.branch_ids is not None:
            raise _deny("Shared master changes require explicit GLOBAL authority.")
        return
    if name not in DIRECT_SCOPE_COLUMNS and name not in PARENT_SCOPE_COLUMNS:
        raise _deny("This entity has no mutation ownership policy.")
    branches = _entity_branches(session, instance, models)
    if not branches:
        raise _deny("A mutation requires an explicit branch.")
    for capability in context.capabilities:
        require_branches(context.user, capability, branches)
    context.resource_branch_ids.update(branches)
    if context.economic and name != "branches":
        branch_model = models["branches"]
        active = set(
            session.scalars(
                select(_column(branch_model, "id"))
                .where(
                    _column(branch_model, "id").in_(branches),
                    _column(branch_model, "is_active").is_(True),
                )
                .order_by(_column(branch_model, "id"))
                .with_for_update(read=True)
            )
        )
        if active != branches:
            raise _deny("Inactive branches cannot perform ordinary economic operations.")
    for column in table.columns:
        value = getattr(instance, column.key)
        if value is None:
            continue
        for foreign_key in column.foreign_keys:
            parent_table = foreign_key.column.table.name
            if parent_table == "users" and column.key in {
                "responsible_user_id",
                "inspector_user_id",
            }:
                state = inspect(instance)
                if state.pending or state.attrs[column.key].history.has_changes():
                    memberships = set(
                        session.scalars(
                            select(UserBranchAssignment.branch_id)
                            .join(User, User.id == UserBranchAssignment.user_id)
                            .where(
                                User.id == value,
                                User.is_active.is_(True),
                                User.is_locked.is_(False),
                                UserBranchAssignment.is_active.is_(True),
                            )
                        )
                    )
                    if not branches.issubset(memberships):
                        raise _deny("The responsible user is not active in the document branch.")
            if (
                parent_table not in DIRECT_SCOPE_COLUMNS
                and parent_table not in PARENT_SCOPE_COLUMNS
            ):
                continue
            parent_model = models[parent_table]
            if parent_table == "workstations" and context.economic:
                # The service may have cached this workstation before another request changed it.
                # Read authoritative columns under the lock held until the economic commit.
                workstation = session.execute(
                    select(Workstation.branch_id, Workstation.is_active)
                    .where(Workstation.id == value)
                    .with_for_update(read=True)
                ).one_or_none()
                if workstation is None or not workstation.is_active:
                    raise _deny("An ordinary economic operation requires an active workstation.")
                related_branches = {workstation.branch_id}
            else:
                parent = _reference(session, parent_model, foreign_key.column.name, value)
                related_branches = _entity_branches(session, parent, models)
            for capability in context.capabilities:
                require_branches(context.user, capability, related_branches)
            if len(branches) == 1 and name not in {"operation_documents", "correction_documents"}:
                if not related_branches.issubset(branches):
                    raise _deny("Related records must belong to the same authorized branch.")
            if column.key == "workstation_id":
                expected = getattr(
                    instance, "source_branch_id", getattr(instance, "branch_id", None)
                )
                if (
                    name == "operation_documents"
                    and getattr(instance, "document_type", None) == "BRANCH_TRANSFER_RECEIPT"
                ):
                    expected = getattr(instance, "destination_branch_id", None)
                if expected is not None and related_branches != {expected}:
                    raise _deny("The workstation does not belong to the document branch.")
    cash_session_id = getattr(
        instance, "cash_session_id", getattr(instance, "active_cash_session_id", None)
    )
    workstation_id = getattr(instance, "workstation_id", None)
    if cash_session_id is not None and workstation_id is not None:
        cash_session = _reference(session, models["cash_sessions"], "id", cash_session_id)
        if _value(cash_session, "workstation_id") != workstation_id:
            raise _deny("The cash session and workstation do not match.")
    if (
        isinstance(instance, OperationDocument)
        and instance.document_type == "BRANCH_TRANSFER_RECEIPT"
        and inspect(instance).pending
    ):
        transaction = session.get_transaction()
        if transaction is not None:
            # Only validated inserts in this transaction can authorize the source status update.
            context.transfer_receipts[instance] = transaction
    if receipt_cause is not None:
        context.received_shipments[receipt_cause.shipment] = receipt_cause


def _revalidate(session: Session, context: AuthorizationScope) -> None:
    if context.identity_mutation:
        # Identity owns its approved lifecycle and holds the exclusive boundary lock.
        # A legitimate self-change can remove the actor's original grant at commit.
        return
    refreshed = resolve_authorization(session, context.user, surface=context.surface)
    branches = _intersection(refreshed, context.capabilities, global_only=context.global_only)
    for capability in context.capabilities:
        require_branches(
            refreshed, capability, context.resource_branch_ids, global_only=context.global_only
        )
    context.user = refreshed
    context.branch_ids = branches


def _stamp_traces(context: AuthorizationScope, instances: Iterable[object]) -> None:
    branch_ids = context.resource_branch_ids or set(context.branch_ids or ())
    provenance = {
        "actor_id": str(context.user.id),
        "capabilities": list(context.capabilities),
        "authorization_version": context.user.authorization_version,
        "scope_type": "BRANCH_SET" if branch_ids else "GLOBAL",
        "branch_ids": [str(value) for value in sorted(branch_ids, key=str)],
        "request_id": context.request_id,
    }
    for instance in instances:
        if not isinstance(instance, Base):
            continue
        if isinstance(instance, AuditLog):
            instance.metadata_ = {**(instance.metadata_ or {}), "authorization": provenance}
        elif isinstance(instance, OutboxEvent):
            instance.headers = {**(instance.headers or {}), "authorization": provenance}


def _before_flush(session: Session, flush_context: object, instances: object) -> None:
    context = authorization_scope(session)
    if context is None or context.validating:
        return
    if not context.mutation:
        raise _deny("A read operation cannot mutate data.")
    context.validating = True
    try:
        _revalidate(session, context)
        models = _models()
        changed = tuple(session.new) + tuple(session.dirty) + tuple(session.deleted)
        for instance in changed:
            if isinstance(instance, Base):
                _validate_entity(session, context, instance, models)
        _validate_transfer_receipt_causes(session, context)
        _stamp_traces(context, session.new)
    finally:
        context.validating = False


def _before_commit(session: Session) -> None:
    context = authorization_scope(session)
    if context is not None and context.mutation and not context.validating:
        context.validating = True
        try:
            _revalidate(session, context)
            _validate_transfer_receipt_causes(session, context)
        finally:
            context.validating = False


def _after_transaction_end(session: Session, transaction: SessionTransaction) -> None:
    context = authorization_scope(session)
    if context is not None and transaction.parent is None:
        context.transfer_receipts.clear()
        context.received_shipments.clear()


def _after_soft_rollback(session: Session, transaction: SessionTransaction) -> None:
    context = authorization_scope(session)
    if context is not None and transaction.nested and session.is_active:
        context.transfer_receipts = {
            receipt: owner
            for receipt, owner in context.transfer_receipts.items()
            if inspect(receipt).session is session and inspect(receipt).persistent
        }
        context.received_shipments = {
            shipment: cause
            for shipment, cause in context.received_shipments.items()
            if _has_live_transfer_receipt(session, cause)
        }


def install_scope_guards() -> None:
    if not event.contains(Session, "do_orm_execute", _scope_statement):
        event.listen(Session, "do_orm_execute", _scope_statement)
        event.listen(Session, "before_flush", _before_flush)
        event.listen(Session, "before_commit", _before_commit)
        event.listen(Session, "after_transaction_end", _after_transaction_end)
        event.listen(Session, "after_soft_rollback", _after_soft_rollback)
