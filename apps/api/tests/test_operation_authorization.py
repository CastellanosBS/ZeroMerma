from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import monotonic, sleep
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, aliased

from zeromerma_api.db.access_scope import (
    DIRECT_SCOPE_COLUMNS,
    PARENT_SCOPE_COLUMNS,
    bind_authorization_scope,
)
from zeromerma_api.db.base import Base
from zeromerma_api.db.session import SessionLocal, get_session
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.permissions import PERMISSION_CODES
from zeromerma_api.modules.identity.application.privileged_access import lock_privileged_lifecycle
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.identity.application.security import TokenService
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryBalance
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.suppliers.infrastructure.models import Supplier
from zeromerma_api.presentation.access_policy import ENDPOINT_POLICIES, install_access_policies
from zeromerma_api.presentation.errors import install_error_handlers


def _actor(
    session: Session, capabilities: tuple[CapabilityCode, ...], branches: list[UUID]
) -> AuthenticatedUser:
    user = User(
        email=f"operation-{uuid4()}@example.test",
        full_name="Scoped operator",
        password_hash="unusable",
        allowed_surfaces=["BACKOFFICE"],
        default_surface="BACKOFFICE",
    )
    role = Role(code=f"scope_{uuid4().hex}", name="Scoped role", surfaces=["BACKOFFICE"])
    session.add_all([user, role])
    session.flush()
    assignment = UserRoleAssignment(user_id=user.id, role_id=role.id, scope_type="BRANCH_SET")
    session.add(assignment)
    session.flush()
    session.add_all(
        [UserBranchAssignment(user_id=user.id, branch_id=branch) for branch in branches]
        + [
            UserRoleAssignmentBranchScope(assignment_id=assignment.id, branch_id=branch)
            for branch in branches
        ]
        + [
            RolePermission(role_id=role.id, permission_id=permission)
            for permission in session.scalars(
                select(Permission.id).where(Permission.code.in_(capabilities))
            )
        ]
    )
    session.commit()
    return resolve_authorization(session, user, surface="BACKOFFICE")


def _headers(actor: AuthenticatedUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {TokenService().issue_access_token(actor.id)}"}


def test_scoped_queries_filter_columns_aliases_aggregates_subqueries_and_cached_get() -> None:
    with SessionLocal() as session:
        branches = list(session.scalars(select(Branch.id).order_by(Branch.code)))
        product = session.scalars(select(Product.id)).first()
        assert product is not None
        session.add_all(
            [
                InventoryBalance(
                    product_id=product,
                    branch_id=branch,
                    location_code="BACKROOM",
                    quantity_on_hand=1,
                )
                for branch in branches
            ]
        )
        session.commit()
        actor = _actor(session, ("inventory.view",), branches[:1])
        expected = set(
            session.scalars(
                select(InventoryBalance.id).where(InventoryBalance.branch_id == branches[0])
            )
        )
        foreign = session.scalars(
            select(InventoryBalance).where(InventoryBalance.branch_id != branches[0])
        ).first()
        assert foreign is not None
        foreign_id = foreign.id
        bind_authorization_scope(
            session,
            user=actor,
            capabilities=("inventory.view",),
            mutation=False,
            surface="BACKOFFICE",
        )
        assert session.get(InventoryBalance, foreign_id) is None
        assert set(session.scalars(select(InventoryBalance.id))) == expected
        balance_alias = aliased(InventoryBalance)
        assert set(session.scalars(select(balance_alias.id))) == expected
        assert session.scalar(
            select(func.count()).select_from(select(InventoryBalance.id).subquery())
        ) == len(expected)
        assert session.scalar(select(func.count(InventoryBalance.id))) == len(expected)
        assert set(session.scalars(select(InventoryBalance.branch_id).distinct())) == {branches[0]}
        assert set(session.scalars(select(Branch.id))) == {branches[0]}


@pytest.mark.parametrize(
    "query_kind", ["text", "core", "core_alias", "mixed_alias", "mixed_scalar", "mixed_core_count"]
)
def test_unclassified_sql_cannot_bypass_branch_scope(query_kind: str) -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        assert branch is not None
        actor = _actor(session, ("inventory.view",), [branch])
        bind_authorization_scope(
            session, user=actor, capabilities=("inventory.view",), mutation=False
        )
        queries = {
            "text": text("SELECT id FROM inventory_balances"),
            "core": select(InventoryBalance.__table__.c.id),
            "core_alias": select(InventoryBalance.__table__.alias("unmapped").c.id),
            "mixed_alias": select(
                InventoryBalance.id, InventoryBalance.__table__.alias("mixed").c.id
            ),
            "mixed_scalar": select(
                InventoryBalance.id,
                select(InventoryBalance.__table__.c.id).limit(1).scalar_subquery(),
            ),
            "mixed_core_count": select(
                InventoryBalance.id,
                select(func.count()).select_from(InventoryBalance.__table__).scalar_subquery(),
            ),
        }
        with pytest.raises(HTTPException) as denied:
            session.execute(queries[query_kind])
        assert denied.value.status_code == 403


def test_mutations_reject_foreign_branch_and_shared_master_without_side_effects() -> None:
    with SessionLocal() as session:
        branches = list(session.scalars(select(Branch.id).order_by(Branch.code)))
        actor = _actor(session, ("inventory.adjust",), branches[:1])
        product_id = session.scalars(select(Product.id)).first()
        assert product_id is not None
        bind_authorization_scope(
            session, user=actor, capabilities=("inventory.adjust",), mutation=True
        )
        session.add(
            InventoryBalance(product_id=product_id, branch_id=branches[1], location_code="WASTE")
        )
        with pytest.raises(HTTPException) as denied:
            session.flush()
        assert denied.value.status_code == 403
        session.rollback()
    with SessionLocal() as session:
        actor = resolve_authorization(session, actor)
        bind_authorization_scope(
            session, user=actor, capabilities=("inventory.adjust",), mutation=True
        )
        product = session.get(Product, product_id)
        assert product is not None
        product.name = "Unauthorized shared edit"
        with pytest.raises(HTTPException) as denied:
            session.flush()
        assert denied.value.status_code == 403
        session.rollback()


def test_foreign_workstation_reference_is_rejected_even_if_both_branches_are_allowed() -> None:
    with SessionLocal() as session:
        stations = list(session.scalars(select(Workstation).order_by(Workstation.code)))
        source = stations[0]
        foreign = next(station for station in stations if station.branch_id != source.branch_id)
        source_branch, foreign_branch, foreign_station = (
            source.branch_id,
            foreign.branch_id,
            foreign.id,
        )
        actor = _actor(session, ("transfers.manage",), [source_branch, foreign_branch])
        bind_authorization_scope(
            session, user=actor, capabilities=("transfers.manage",), mutation=True
        )
        session.add(
            OperationDocument(
                source_branch_id=source_branch,
                destination_branch_id=foreign_branch,
                workstation_id=foreign_station,
                created_by_user_id=actor.id,
                document_type="BRANCH_TRANSFER_SHIPMENT",
                status="DRAFT",
            )
        )
        with pytest.raises(HTTPException) as denied:
            session.flush()
        assert denied.value.status_code == 403
        session.rollback()


def test_http_families_deny_missing_capability_and_view_does_not_grant_mutation(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        assert branch is not None
        actor = _actor(session, ("catalog.view",), [branch])
        audit_count = session.scalar(select(func.count(AuditLog.id)))
        outbox_count = session.scalar(select(func.count(OutboxEvent.id)))
    headers = _headers(actor)
    paths = [
        "inventory",
        "production",
        "purchases",
        "suppliers",
        "transfers",
        "orders",
        "sales",
        "returns-corrections/returns",
        "returns-corrections/corrections",
        "waste",
        "discounts",
        "reports",
        "audit",
        "cash-cuts",
        "prices",
        "recipes",
        "cleaning-logs",
        "users",
        "roles",
    ]
    # Resolve real paths from the manifest so no absent endpoint can make a denial pass.
    from zeromerma_api.presentation.access_policy import ENDPOINT_POLICIES

    for family in paths:
        matching = [
            path
            for (method, path), policy in ENDPOINT_POLICIES.items()
            if method == "GET"
            and path.startswith(f"/v1/admin/{family}")
            and "{" not in path
            and policy.capabilities
            and not policy.exception_reason
        ]
        assert matching, family
        for path in matching:
            response = client.get(path, headers=headers)
            assert response.status_code == 403, (path, response.text)
    response = client.get("/v1/admin/products", headers=headers)
    assert response.status_code == 200, response.text
    response = client.post("/v1/admin/products", headers=headers, json={})
    assert response.status_code == 403, response.text
    with SessionLocal() as session:
        assert session.scalar(select(func.count(AuditLog.id))) > audit_count
        denied = list(
            session.scalars(select(AuditLog).where(AuditLog.action == "authorization.denied"))
        )
        assert denied
        assert all(
            record.actor_id == actor.id and record.metadata_["result"] == "denied"
            for record in denied
        )
        assert session.scalar(select(func.count(OutboxEvent.id))) == outbox_count


def test_http_inventory_scope_filters_omitted_and_foreign_filters_and_denies_mutation(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        branches = list(session.scalars(select(Branch.id).order_by(Branch.code)))
        actor = _actor(session, ("inventory.view", "inventory.adjust"), branches[:1])
        product = session.scalars(select(Product.id)).first()
        assert product is not None
    headers = _headers(actor)
    response = client.get("/v1/admin/inventory", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert str(branches[1]) not in str(data)
    foreign_filter = client.get(f"/v1/admin/inventory?branch_id={branches[1]}", headers=headers)
    assert foreign_filter.status_code == 403, foreign_filter.text
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers=headers,
        json={
            "adjustment_type": "INCREASE",
            "branch_id": str(branches[1]),
            "location_code": "BACKROOM",
            "product_id": str(product),
            "quantity": "1.000",
            "reason": "Denied foreign mutation",
        },
    )
    assert response.status_code in {403, 404}, response.text
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers=headers,
        json={
            "adjustment_type": "INCREASE",
            "branch_id": str(branches[0]),
            "location_code": "BACKROOM",
            "product_id": str(product),
            "quantity": "1.000",
            "reason": "Authorized mutation",
        },
    )
    assert response.status_code == 201, response.text
    with SessionLocal() as session:
        record = session.scalars(
            select(AuditLog).where(AuditLog.action == "admin.inventory.adjustment.created")
        ).first()
        assert record is not None
        assert record.metadata_["authorization"]["branch_ids"] == [str(branches[0])]


def test_report_definition_cannot_bypass_its_domain_capability(client: TestClient) -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        assert branch is not None
        actor = _actor(session, ("reports.view",), [branch])
    headers = _headers(actor)
    response = client.get("/v1/admin/reports", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0
    response = client.post(
        "/v1/admin/reports/sales_summary_by_branch/preview", headers=headers, json={"filters": {}}
    )
    assert response.status_code == 403, response.text


def test_all_scoped_families_support_mapped_reads_and_aggregate_subqueries() -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        assert branch is not None
        actor = _actor(session, ("inventory.view",), [branch])
        bind_authorization_scope(
            session, user=actor, capabilities=("inventory.view",), mutation=False
        )
        for mapper in Base.registry.mappers:
            if mapper.local_table.name not in set(DIRECT_SCOPE_COLUMNS) | set(
                PARENT_SCOPE_COLUMNS
            ) | {"outbox_events"}:
                continue
            model = mapper.class_
            session.scalars(select(model).limit(1)).all()
            assert (
                session.scalar(select(func.count()).select_from(select(model).subquery()))
                is not None
            )


def test_authorized_branch_reader_can_open_all_declared_admin_list_families(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        assert branch is not None
        actor = _actor(session, tuple(PERMISSION_CODES), [branch])
    for (method, path), policy in ENDPOINT_POLICIES.items():
        if (
            method != "GET"
            or policy.surface != "BACKOFFICE"
            or "{" in path
            or not policy.capabilities
        ):
            continue
        response = client.get(path, headers=_headers(actor))
        assert response.status_code == 200, (path, response.text)


def test_supplier_actions_do_not_infer_manage_from_view_or_scoped_manage(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        assert branch is not None
        supplier = Supplier(code="SCOPED-SUPPLIER", legal_name="Shared supplier")
        session.add(supplier)
        session.commit()
        supplier_id = supplier.id
        actor = _actor(session, ("suppliers.view", "suppliers.manage"), [branch])
    response = client.get(f"/v1/admin/suppliers/{supplier_id}", headers=_headers(actor))
    assert response.status_code == 200, response.text
    assert response.json()["available_actions"]
    assert not any(response.json()["available_actions"].values())
    response = client.patch(f"/v1/admin/suppliers/{supplier_id}", headers=_headers(actor), json={})
    assert response.status_code == 403, response.text


def test_transfer_children_require_both_endpoints_and_inactive_history_is_readable() -> None:
    with SessionLocal() as session:
        stations = list(session.scalars(select(Workstation).order_by(Workstation.code)))
        station = stations[0]
        other = next(item for item in stations if item.branch_id != station.branch_id)
        source, destination = station.branch_id, other.branch_id
        user_id = session.scalars(select(User.id)).first()
        product = session.scalars(select(Product)).first()
        assert user_id is not None and product is not None
        documents = [
            OperationDocument(
                source_branch_id=source,
                destination_branch_id=end,
                workstation_id=station.id,
                created_by_user_id=user_id,
                document_type="BRANCH_TRANSFER_SHIPMENT",
                status="DRAFT",
            )
            for end in (source, destination)
        ]
        session.add_all(documents)
        session.flush()
        for document in documents:
            session.add(
                OperationDocumentLine(
                    operation_document_id=document.id,
                    line_number=1,
                    product_id=product.id,
                    product_code_snapshot=product.code,
                    product_name_snapshot=product.name,
                    product_class_id=product.product_class_id,
                    product_class_code_snapshot="CLASS",
                    product_class_name_snapshot="Class",
                    quantity=1,
                )
            )
        branch = session.get(Branch, source)
        assert branch is not None
        branch.is_active = False
        session.commit()
        expected_id = documents[0].id
        actor = _actor(session, ("transfers.view", "inventory.adjust"), [source])
        bind_authorization_scope(
            session, user=actor, capabilities=("transfers.view",), mutation=False
        )
        assert list(session.scalars(select(OperationDocument.id))) == [expected_id]
        assert list(session.scalars(select(OperationDocumentLine.operation_document_id))) == [
            expected_id
        ]
        session.rollback()

    with SessionLocal() as session:
        bind_authorization_scope(
            session, user=actor, capabilities=("inventory.adjust",), mutation=True
        )
        session.add(
            InventoryBalance(branch_id=source, product_id=product.id, location_code="WASTE")
        )
        with pytest.raises(HTTPException) as denied:
            session.flush()
        assert denied.value.status_code == 403
        session.rollback()


def test_preview_uses_view_authority_and_export_remains_separate(client: TestClient) -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        assert branch is not None
        actor = _actor(session, ("reports.view", "inventory.view"), [branch])
    headers = _headers(actor)
    response = client.post(
        "/v1/admin/reports/inventory_low_negative_stock/preview",
        headers=headers,
        json={"filters": {}},
    )
    assert response.status_code == 200, response.text
    response = client.post(
        "/v1/admin/reports/inventory_low_negative_stock/export",
        headers=headers,
        json={"filters": {}, "format": "json"},
    )
    assert response.status_code == 403, response.text


@pytest.mark.parametrize("revocation", ["privilege", "branch"])
def test_economic_transaction_and_privilege_revocation_share_one_lock_boundary(
    revocation: str,
) -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        product = session.scalars(select(Product.id)).first()
        assert branch is not None and product is not None
        actor = _actor(session, ("inventory.adjust",), [branch])
    ready: Queue[int] = Queue()

    def revoke() -> None:
        with SessionLocal() as revoker:
            backend_pid = revoker.scalar(select(func.pg_backend_pid()))
            assert backend_pid is not None
            ready.put(backend_pid)
            if revocation == "privilege":
                lock_privileged_lifecycle(revoker)
                assignment = revoker.scalar(
                    select(UserRoleAssignment).where(UserRoleAssignment.user_id == actor.id)
                )
                assert assignment is not None
                assignment.is_active = False
            else:
                target_branch = revoker.get(Branch, branch)
                assert target_branch is not None
                target_branch.is_active = False
            revoker.commit()

    with ThreadPoolExecutor(max_workers=1) as executor, SessionLocal() as session:
        bind_authorization_scope(
            session, user=actor, capabilities=("inventory.adjust",), mutation=True
        )
        session.add(InventoryBalance(branch_id=branch, product_id=product, location_code="WASTE"))
        session.flush()
        future = executor.submit(revoke)
        blocked_pid = ready.get(timeout=5)
        try:
            with SessionLocal() as observer:
                deadline = monotonic() + 5
                while monotonic() < deadline:
                    if observer.scalar(select(func.pg_blocking_pids(blocked_pid))):
                        break
                    sleep(0.02)
                else:
                    pytest.fail("Privilege revocation did not wait on the economic shared lock.")
            assert not future.done()
            session.commit()
        finally:
            session.rollback()
        future.result(timeout=10)
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as denied:
            bind_authorization_scope(
                session, user=actor, capabilities=("inventory.adjust",), mutation=True
            )
            session.add(
                InventoryBalance(branch_id=branch, product_id=product, location_code="COUNTER")
            )
            session.flush()
        assert denied.value.status_code == 403
        session.rollback()
        assert session.scalar(select(func.count(InventoryBalance.id))) == 1


def test_denial_audit_commits_only_after_all_flushed_business_writes_are_rolled_back() -> None:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch.id)).first()
        product = session.scalars(select(Product.id)).first()
        assert branch is not None and product is not None
        actor = _actor(session, ("inventory.adjust",), [branch])
    router = APIRouter()

    @router.post("/v1/admin/inventory/adjustments")
    def denied_after_flush(session: Annotated[Session, Depends(get_session)]) -> None:
        session.add(InventoryBalance(branch_id=branch, product_id=product, location_code="WASTE"))
        session.add(AuditLog(action="must.rollback", resource_type="test", actor_id=actor.id))
        session.flush()
        raise HTTPException(status_code=403, detail="A related record is outside the scope.")

    install_access_policies(router)
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app)
    with TestClient(app) as client:
        response = client.post(
            "/v1/admin/inventory/adjustments",
            headers={**_headers(actor), "X-Request-ID": "denial-rollback-proof"},
            json={"secret": "must-not-be-audited"},
        )
    assert response.status_code == 403
    with SessionLocal() as session:
        assert session.scalar(select(func.count(InventoryBalance.id))) == 0
        assert session.scalar(select(func.count(OutboxEvent.id))) == 0
        records = list(session.scalars(select(AuditLog)))
        assert len(records) == 1
        record = records[0]
        assert record.action == "authorization.denied"
        assert record.actor_id == actor.id
        assert record.request_id == "denial-rollback-proof"
        assert record.metadata_["required_capabilities"] == ["inventory.adjust"]
        assert (
            record.metadata_["authorization"]["authorization_version"]
            == actor.authorization_version
        )
        assert "must-not-be-audited" not in str(record.metadata_)


def test_multibranch_audit_metadata_requires_all_related_branches() -> None:
    with SessionLocal() as session:
        branches = list(session.scalars(select(Branch.id).order_by(Branch.code)))
        for action, related in [("single-branch", branches[:1]), ("two-branches", branches[:2])]:
            session.add(
                AuditLog(
                    action=action,
                    resource_type="test",
                    branch_id=branches[0],
                    metadata_={
                        "authorization": {
                            "scope_type": "BRANCH_SET",
                            "branch_ids": [str(branch) for branch in related],
                        }
                    },
                )
            )
        session.commit()
        actor = _actor(session, ("audit.view",), branches[:1])
        bind_authorization_scope(session, user=actor, capabilities=("audit.view",), mutation=False)
        assert list(session.scalars(select(AuditLog.action))) == ["single-branch"]
