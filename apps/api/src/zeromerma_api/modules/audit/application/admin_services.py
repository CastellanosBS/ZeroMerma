from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.admin_schemas import (
    AdminAuditActorContextView,
    AdminAuditAvailableActionsView,
    AdminAuditChangeItemView,
    AdminAuditEntityContextView,
    AdminAuditEventDetailView,
    AdminAuditEventListItemView,
    AdminAuditEventsListResponse,
    AdminAuditExportResponse,
    AdminAuditExportRowView,
    AdminAuditFilterOptionsView,
    AdminAuditFilterOptionView,
    AdminAuditOverviewView,
    AdminAuditRelatedDocumentView,
    AdminAuditRequestContextView,
    AdminAuditSummaryView,
    AdminAuditTimelineEventView,
)
from zeromerma_api.modules.audit.domain.exceptions import AuditEventNotFoundError
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.infrastructure.models import (
    Role,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
)

SOURCE_APP_BACKOFFICE = "BACKOFFICE"
SOURCE_APP_POS = "POS"
SOURCE_APP_SYSTEM = "SYSTEM"

RESULT_SUCCESS = "success"
RESULT_FAILED = "failed"
RESULT_REJECTED = "rejected"
RESULT_BLOCKED = "blocked"
RESULT_SYSTEM_GENERATED = "system_generated"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

FINANCIAL_DOMAINS = {
    "cash",
    "cash_close",
    "discounts",
    "payments",
    "prices",
    "reconciliation",
}
INVENTORY_DOMAINS = {"inventory", "production", "transfers", "waste"}
ACCESS_DOMAINS = {"auth", "roles_permissions", "users"}
SENSITIVE_DOMAINS = FINANCIAL_DOMAINS | INVENTORY_DOMAINS | ACCESS_DOMAINS | {"configuration"}
FAILED_RESULTS = {RESULT_FAILED, RESULT_REJECTED, RESULT_BLOCKED}
SECRET_FIELD_TOKENS = (
    "authorization",
    "credential",
    "hash",
    "password",
    "refresh_token",
    "secret",
    "token",
)

DOMAIN_LABELS = {
    "auth": "Autenticacion",
    "cash": "Caja",
    "cash_close": "Cortes de caja",
    "catalog": "Catalogo",
    "configuration": "Configuracion",
    "discounts": "Descuentos",
    "hygiene_quality": "Calidad e higiene",
    "inventory": "Inventario",
    "orders": "Pedidos",
    "payments": "Pagos",
    "prices": "Precios",
    "production": "Produccion",
    "purchases": "Compras",
    "reconciliation": "Conciliacion",
    "reports": "Reportes",
    "returns": "Devoluciones",
    "roles_permissions": "Roles y permisos",
    "sales": "Ventas",
    "suppliers": "Proveedores",
    "system": "Sistema",
    "tickets": "Tickets",
    "transfers": "Transferencias",
    "users": "Usuarios",
    "waste": "Merma",
}

RESOURCE_DOMAIN_MAP = {
    "branch": "system",
    "branch_transfer": "transfers",
    "cash_close": "cash_close",
    "cash_flow": "cash",
    "cash_session": "cash",
    "discount": "discounts",
    "equipment_asset": "hygiene_quality",
    "financial_reconciliation": "reconciliation",
    "input_supply": "catalog",
    "inventory_balance": "inventory",
    "inventory_movement": "inventory",
    "incident": "hygiene_quality",
    "operational_payment": "payments",
    "payment": "payments",
    "price_rule": "prices",
    "production_order": "production",
    "product": "catalog",
    "product_class": "catalog",
    "purchase_document": "purchases",
    "recipe": "catalog",
    "return_or_correction": "returns",
    "role": "roles_permissions",
    "sale_ticket": "sales",
    "supplier": "suppliers",
    "ticket": "tickets",
    "user": "users",
    "waste_record": "waste",
    "workstation": "system",
}


@dataclass(frozen=True)
class _AuditContext:
    record: AuditLog
    actor: User | None
    branch: Branch | None


class AdminAuditService:
    def list_events(
        self,
        session: Session,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
        search: str | None,
        actor_user_id: uuid.UUID | None,
        actor_email: str | None,
        module: str | None,
        action: str | None,
        entity_type: str | None,
        entity_id: str | None,
        branch_id: uuid.UUID | None,
        workstation: str | None,
        severity: str | None,
        sensitive: str | None,
        result: str | None,
        source_app: str | None,
        related_reference: str | None,
        warning_state: str | None,
        page: int,
        page_size: int,
    ) -> AdminAuditEventsListResponse:
        contexts = self._resolve_contexts(
            session,
            date_from=date_from,
            date_to=date_to,
        )
        filter_options = self._build_filter_options(contexts)
        filtered = self._apply_filters(
            contexts,
            search=search,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            module=module,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            branch_id=branch_id,
            workstation=workstation,
            severity=severity,
            sensitive=sensitive,
            result=result,
            source_app=source_app,
            related_reference=related_reference,
            warning_state=warning_state,
        )
        total = len(filtered)
        start = (page - 1) * page_size
        page_contexts = filtered[start : start + page_size]

        return AdminAuditEventsListResponse(
            filter_options=filter_options,
            items=[self._to_list_item(context) for context in page_contexts],
            metrics=self._build_metrics(filtered),
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_event_detail(
        self,
        session: Session,
        *,
        event_id: uuid.UUID,
    ) -> AdminAuditEventDetailView:
        record = session.get(AuditLog, event_id)
        if record is None:
            raise AuditEventNotFoundError("Audit event was not found.")

        context = self._build_context(session, record)
        overview = AdminAuditOverviewView(
            **self._to_list_item(context).model_dump(),
            request_id=record.request_id,
        )
        request_context = self._build_request_context(record)
        related_documents = self._build_related_documents(context)

        return AdminAuditEventDetailView(
            overview=overview,
            actor_context=self._build_actor_context(session, context),
            entity_context=self._build_entity_context(context),
            change_summary=self._build_change_summary(record.metadata_ or {}),
            request_context=request_context,
            related_documents=related_documents,
            timeline_related_events=self._build_timeline(session, context),
            available_actions=AdminAuditAvailableActionsView(
                can_copy_correlation_id=bool(
                    request_context and request_context.correlation_id,
                ),
                can_open_related_document=bool(related_documents),
                can_open_user=context.actor is not None,
            ),
        )

    def export_events(
        self,
        session: Session,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
        search: str | None,
        actor_user_id: uuid.UUID | None,
        actor_email: str | None,
        module: str | None,
        action: str | None,
        entity_type: str | None,
        entity_id: str | None,
        branch_id: uuid.UUID | None,
        workstation: str | None,
        severity: str | None,
        sensitive: str | None,
        result: str | None,
        source_app: str | None,
        related_reference: str | None,
        warning_state: str | None,
    ) -> AdminAuditExportResponse:
        contexts = self._apply_filters(
            self._resolve_contexts(session, date_from=date_from, date_to=date_to),
            search=search,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            module=module,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            branch_id=branch_id,
            workstation=workstation,
            severity=severity,
            sensitive=sensitive,
            result=result,
            source_app=source_app,
            related_reference=related_reference,
            warning_state=warning_state,
        )
        rows = [
            AdminAuditExportRowView(
                occurred_at=context.record.occurred_at,
                actor=self._actor_name(context),
                actor_email=context.actor.email if context.actor is not None else None,
                source_app=self._source_app(context.record),
                module=self._domain(context.record),
                action=context.record.action,
                entity_type=context.record.resource_type,
                entity_id=context.record.resource_id,
                entity_reference=self._entity_reference(context.record),
                result=self._result(context.record),
                branch_name=context.branch.name if context.branch is not None else None,
                workstation_name=self._metadata_text(context.record, "workstation_name")
                or self._metadata_text(context.record, "workstation_code"),
                is_sensitive=self._is_sensitive(context.record),
            )
            for context in contexts[:5000]
        ]
        return AdminAuditExportResponse(
            generated_at=datetime.now(tz=UTC),
            total=len(contexts),
            rows=rows,
        )

    def _resolve_contexts(
        self,
        session: Session,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[_AuditContext]:
        query = select(AuditLog)
        if date_from is not None:
            query = query.where(AuditLog.occurred_at >= date_from)
        if date_to is not None:
            query = query.where(AuditLog.occurred_at <= date_to)
        records = session.execute(
            query.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc()),
        ).scalars().all()
        return [self._build_context(session, record) for record in records]

    def _build_context(self, session: Session, record: AuditLog) -> _AuditContext:
        actor = session.get(User, record.actor_id) if record.actor_id is not None else None
        branch = session.get(Branch, record.branch_id) if record.branch_id is not None else None
        return _AuditContext(record=record, actor=actor, branch=branch)

    def _apply_filters(
        self,
        contexts: list[_AuditContext],
        *,
        search: str | None,
        actor_user_id: uuid.UUID | None,
        actor_email: str | None,
        module: str | None,
        action: str | None,
        entity_type: str | None,
        entity_id: str | None,
        branch_id: uuid.UUID | None,
        workstation: str | None,
        severity: str | None,
        sensitive: str | None,
        result: str | None,
        source_app: str | None,
        related_reference: str | None,
        warning_state: str | None,
    ) -> list[_AuditContext]:
        filtered = contexts
        normalized_search = _normalize(search)
        if normalized_search:
            filtered = [
                context
                for context in filtered
                if normalized_search in self._search_blob(context)
            ]
        if actor_user_id is not None:
            filtered = [
                context for context in filtered if context.record.actor_id == actor_user_id
            ]
        normalized_actor_email = _normalize(actor_email)
        if normalized_actor_email:
            filtered = [
                context
                for context in filtered
                if context.actor is not None
                and normalized_actor_email in context.actor.email.lower()
            ]
        normalized_module = _normalize_filter(module)
        if normalized_module:
            filtered = [
                context
                for context in filtered
                if self._domain(context.record) == normalized_module
            ]
        normalized_action = _normalize_filter(action)
        if normalized_action:
            filtered = [
                context
                for context in filtered
                if context.record.action == normalized_action
            ]
        normalized_entity_type = _normalize_filter(entity_type)
        if normalized_entity_type:
            filtered = [
                context
                for context in filtered
                if context.record.resource_type == normalized_entity_type
            ]
        normalized_entity_id = _normalize(entity_id)
        if normalized_entity_id:
            filtered = [
                context
                for context in filtered
                if context.record.resource_id
                and normalized_entity_id in context.record.resource_id.lower()
            ]
        if branch_id is not None:
            filtered = [context for context in filtered if context.record.branch_id == branch_id]
        normalized_workstation = _normalize(workstation)
        if normalized_workstation:
            filtered = [
                context
                for context in filtered
                if normalized_workstation
                in " ".join(
                    [
                        self._metadata_text(context.record, "workstation_id") or "",
                        self._metadata_text(context.record, "workstation_code") or "",
                        self._metadata_text(context.record, "workstation_name") or "",
                    ],
                ).lower()
            ]
        normalized_severity = _normalize_filter(severity)
        if normalized_severity:
            filtered = [
                context
                for context in filtered
                if self._severity(context.record) == normalized_severity
            ]
        normalized_sensitive = _normalize_filter(sensitive)
        if normalized_sensitive == "yes":
            filtered = [context for context in filtered if self._is_sensitive(context.record)]
        elif normalized_sensitive == "no":
            filtered = [context for context in filtered if not self._is_sensitive(context.record)]
        normalized_result = _normalize_filter(result)
        if normalized_result:
            filtered = [
                context
                for context in filtered
                if self._result(context.record) == normalized_result
            ]
        normalized_source_app = _normalize_filter(source_app)
        if normalized_source_app:
            filtered = [
                context
                for context in filtered
                if self._source_app(context.record) == normalized_source_app
            ]
        normalized_related_reference = _normalize(related_reference)
        if normalized_related_reference:
            filtered = [
                context
                for context in filtered
                if normalized_related_reference in self._related_reference_blob(context.record)
            ]
        normalized_warning = _normalize_filter(warning_state)
        if normalized_warning:
            filtered = [
                context
                for context in filtered
                if self._warning_state(context.record) == normalized_warning
            ]
        return filtered

    def _to_list_item(self, context: _AuditContext) -> AdminAuditEventListItemView:
        record = context.record
        metadata = record.metadata_ or {}
        workstation_id = self._metadata_text(record, "workstation_id")
        workstation_name = self._metadata_text(record, "workstation_name") or self._metadata_text(
            record,
            "workstation_code",
        )
        return AdminAuditEventListItemView(
            id=record.id,
            occurred_at=record.occurred_at,
            actor_user_id=record.actor_id,
            actor_name=self._actor_name(context),
            actor_email=context.actor.email if context.actor is not None else None,
            actor_type=self._actor_type(record),
            source_app=self._source_app(record),
            module=self._domain(record),
            module_label=DOMAIN_LABELS.get(self._domain(record), _humanize(self._domain(record))),
            action=record.action,
            action_label=_humanize(record.action),
            entity_type=record.resource_type,
            entity_id=record.resource_id,
            entity_reference=self._entity_reference(record),
            result=self._result(record),
            severity=self._severity(record),
            is_sensitive=self._is_sensitive(record),
            branch_id=record.branch_id,
            branch_name=context.branch.name
            if context.branch is not None
            else _to_optional_text(metadata.get("branch_name") or metadata.get("branch_code")),
            workstation_id=workstation_id,
            workstation_name=workstation_name,
            warning_state=self._warning_state(record),
        )

    def _build_metrics(self, contexts: list[_AuditContext]) -> AdminAuditSummaryView:
        active_actor_ids = {
            context.record.actor_id for context in contexts if context.record.actor_id is not None
        }
        access_events = sum(
            1 for context in contexts if self._domain(context.record) in ACCESS_DOMAINS
        )
        failed_events = sum(
            1 for context in contexts if self._result(context.record) in FAILED_RESULTS
        )
        financial_events = sum(
            1 for context in contexts if self._domain(context.record) in FINANCIAL_DOMAINS
        )
        inventory_events = sum(
            1 for context in contexts if self._domain(context.record) in INVENTORY_DOMAINS
        )
        system_events = sum(
            1
            for context in contexts
            if self._source_app(context.record) == SOURCE_APP_SYSTEM
        )
        return AdminAuditSummaryView(
            access_events=access_events,
            active_actors=len(active_actor_ids),
            failed_events=failed_events,
            financial_events=financial_events,
            inventory_events=inventory_events,
            sensitive_events=sum(1 for context in contexts if self._is_sensitive(context.record)),
            system_events=system_events,
            total_events=len(contexts),
        )

    def _build_filter_options(self, contexts: list[_AuditContext]) -> AdminAuditFilterOptionsView:
        return AdminAuditFilterOptionsView(
            actions=_options({context.record.action for context in contexts}),
            branches=_options(
                {
                    str(context.record.branch_id): context.branch.name
                    if context.branch is not None
                    else str(context.record.branch_id)
                    for context in contexts
                    if context.record.branch_id is not None
                },
            ),
            entity_types=_options({context.record.resource_type for context in contexts}),
            modules=_options(
                {
                    self._domain(context.record): DOMAIN_LABELS.get(
                        self._domain(context.record),
                        _humanize(self._domain(context.record)),
                    )
                    for context in contexts
                },
            ),
            results=_options({self._result(context.record) for context in contexts}),
            sensitivities=[
                AdminAuditFilterOptionView(code="yes", label="Sensibles"),
                AdminAuditFilterOptionView(code="no", label="No sensibles"),
            ],
            severities=_options({self._severity(context.record) for context in contexts}),
            source_apps=_options({self._source_app(context.record) for context in contexts}),
            users=_options(
                {
                    str(context.actor.id): context.actor.email
                    for context in contexts
                    if context.actor is not None
                },
            ),
            warning_states=_options({self._warning_state(context.record) for context in contexts}),
        )

    def _build_actor_context(
        self,
        session: Session,
        context: _AuditContext,
    ) -> AdminAuditActorContextView:
        actor = context.actor
        if actor is None:
            return AdminAuditActorContextView(
                full_name=self._actor_name(context),
                can_open_user=False,
            )

        roles = session.execute(
            select(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == actor.id,
                UserRoleAssignment.is_active.is_(True),
            )
            .order_by(Role.name.asc()),
        ).scalars().all()
        branches = session.execute(
            select(Branch.name)
            .join(UserBranchAssignment, UserBranchAssignment.branch_id == Branch.id)
            .where(
                UserBranchAssignment.user_id == actor.id,
                UserBranchAssignment.is_active.is_(True),
            )
            .order_by(Branch.name.asc()),
        ).scalars().all()
        return AdminAuditActorContextView(
            user_id=actor.id,
            full_name=actor.full_name,
            email=actor.email,
            user_status=_user_status(actor),
            roles_summary=", ".join(roles) if roles else None,
            branch_assignments_summary=", ".join(branches) if branches else None,
            can_open_user=True,
        )

    def _build_entity_context(self, context: _AuditContext) -> AdminAuditEntityContextView:
        record = context.record
        return AdminAuditEntityContextView(
            entity_type=record.resource_type,
            entity_id=record.resource_id,
            entity_reference=self._entity_reference(record),
            branch_id=record.branch_id,
            branch_name=context.branch.name if context.branch is not None else None,
            workstation_id=self._metadata_text(record, "workstation_id"),
            workstation_name=self._metadata_text(record, "workstation_name")
            or self._metadata_text(record, "workstation_code"),
            cash_session_id=self._metadata_text(record, "cash_session_id"),
            related_module=self._domain(record),
            can_open_related_document=False,
        )

    def _build_request_context(self, record: AuditLog) -> AdminAuditRequestContextView | None:
        metadata = record.metadata_ or {}
        request_context = metadata.get("request_context")
        if not isinstance(request_context, dict):
            request_context = {}

        view = AdminAuditRequestContextView(
            request_id=record.request_id or _to_optional_text(request_context.get("request_id")),
            correlation_id=_to_optional_text(
                metadata.get("correlation_id") or request_context.get("correlation_id"),
            ),
            endpoint=_to_optional_text(metadata.get("endpoint") or request_context.get("endpoint")),
            method=_to_optional_text(metadata.get("method") or request_context.get("method")),
            ip_address=_to_optional_text(
                metadata.get("ip_address") or request_context.get("ip_address"),
            ),
            user_agent=_to_optional_text(
                metadata.get("user_agent") or request_context.get("user_agent"),
            ),
            status_code=_to_optional_int(
                metadata.get("status_code") or request_context.get("status_code"),
            ),
            error_code=_to_optional_text(
                metadata.get("error_code") or request_context.get("error_code"),
            ),
            duration_ms=_to_optional_int(
                metadata.get("duration_ms") or request_context.get("duration_ms"),
            ),
        )
        if not any(value is not None for value in view.model_dump().values()):
            return None
        return view

    def _build_related_documents(
        self,
        context: _AuditContext,
    ) -> list[AdminAuditRelatedDocumentView]:
        record = context.record
        related: list[AdminAuditRelatedDocumentView] = []
        if record.resource_id:
            related.append(
                AdminAuditRelatedDocumentView(
                    document_type=record.resource_type,
                    document_id=record.resource_id,
                    reference=self._entity_reference(record),
                    label=f"Documento origen: {_humanize(record.resource_type)}",
                    module=self._domain(record),
                    can_open=False,
                ),
            )

        metadata = record.metadata_ or {}
        for key, value in sorted(metadata.items()):
            if not key.endswith("_id") or value is None:
                continue
            document_type = key.removesuffix("_id")
            if document_type in {"actor", "branch", "created_by_user", "operator_user"}:
                continue
            text_value = _to_optional_text(value)
            if not text_value or text_value == record.resource_id:
                continue
            related.append(
                AdminAuditRelatedDocumentView(
                    document_type=document_type,
                    document_id=text_value,
                    reference=_to_optional_text(
                        metadata.get(f"{document_type}_folio")
                        or metadata.get(f"{document_type}_reference")
                        or metadata.get(f"{document_type}_code"),
                    ),
                    label=_humanize(document_type),
                    module=RESOURCE_DOMAIN_MAP.get(document_type, self._domain(record)),
                    can_open=False,
                ),
            )
        return related[:12]

    def _build_timeline(
        self,
        session: Session,
        context: _AuditContext,
    ) -> list[AdminAuditTimelineEventView]:
        record = context.record
        conditions = [AuditLog.id != record.id]
        if record.resource_id:
            conditions.extend(
                [
                    AuditLog.resource_type == record.resource_type,
                    AuditLog.resource_id == record.resource_id,
                ],
            )
        elif record.request_id:
            conditions.append(AuditLog.request_id == record.request_id)
        else:
            return []

        records = session.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
            .limit(6),
        ).scalars().all()
        contexts = [self._build_context(session, item) for item in records]
        return [
            AdminAuditTimelineEventView(
                id=item.record.id,
                occurred_at=item.record.occurred_at,
                action=item.record.action,
                action_label=_humanize(item.record.action),
                actor_name=self._actor_name(item),
                result=self._result(item.record),
                is_sensitive=self._is_sensitive(item.record),
            )
            for item in contexts
        ]

    def _build_change_summary(self, metadata: dict[str, Any]) -> list[AdminAuditChangeItemView]:
        pairs = _extract_change_pairs(metadata)
        changes: list[AdminAuditChangeItemView] = []
        for field, old_value, new_value in pairs:
            changes.append(
                AdminAuditChangeItemView(
                    field=field,
                    old_value_masked=_mask_value(field, old_value),
                    new_value_masked=_mask_value(field, new_value),
                    change_type=_change_type(old_value, new_value),
                ),
            )
        return changes[:40]

    def _search_blob(self, context: _AuditContext) -> str:
        record = context.record
        pieces = [
            str(record.id),
            record.action,
            record.resource_type,
            record.resource_id or "",
            record.request_id or "",
            self._actor_name(context),
            context.actor.email if context.actor is not None else "",
            self._entity_reference(record) or "",
            json.dumps(_mask_json(record.metadata_ or {}), default=str, sort_keys=True),
        ]
        return " ".join(pieces).lower()

    def _related_reference_blob(self, record: AuditLog) -> str:
        metadata = record.metadata_ or {}
        references = [
            record.resource_id or "",
            record.request_id or "",
            self._entity_reference(record) or "",
        ]
        for key, value in metadata.items():
            if "folio" in key or "reference" in key or key.endswith("_code"):
                references.append(_to_optional_text(value) or "")
        return " ".join(references).lower()

    def _actor_name(self, context: _AuditContext) -> str:
        if context.actor is not None:
            return context.actor.full_name
        metadata_actor = self._metadata_text(context.record, "actor_name")
        return metadata_actor or "Sistema / Worker"

    def _actor_type(self, record: AuditLog) -> str:
        metadata_value = _normalize_filter(self._metadata_text(record, "actor_type"))
        if metadata_value:
            return metadata_value
        if record.actor_id is None:
            return "system"
        return "user"

    def _domain(self, record: AuditLog) -> str:
        metadata_module = _normalize_filter(self._metadata_text(record, "module"))
        if metadata_module:
            return metadata_module
        action_prefix = record.action.split(".", maxsplit=2)
        if len(action_prefix) >= 2:
            if action_prefix[0] == "admin" and action_prefix[1] in {
                "role",
                "roles",
                "permission",
            }:
                return "roles_permissions"
            if action_prefix[0] == "admin" and action_prefix[1] == "user":
                return "users"
            if action_prefix[0] in {"auth", "pos"}:
                return action_prefix[0]
            mapped = RESOURCE_DOMAIN_MAP.get(action_prefix[1])
            if mapped:
                return mapped
        return RESOURCE_DOMAIN_MAP.get(record.resource_type, "system")

    def _source_app(self, record: AuditLog) -> str:
        value = self._metadata_text(record, "source_app") or self._metadata_text(record, "surface")
        normalized = (value or "").upper()
        if normalized in {SOURCE_APP_BACKOFFICE, SOURCE_APP_POS, SOURCE_APP_SYSTEM}:
            return normalized
        if record.actor_id is None:
            return SOURCE_APP_SYSTEM
        if record.action.startswith("pos.") or record.resource_type.startswith("pos"):
            return SOURCE_APP_POS
        return SOURCE_APP_BACKOFFICE

    def _result(self, record: AuditLog) -> str:
        value = _normalize_filter(
            self._metadata_text(record, "result") or self._metadata_text(record, "event_result"),
        )
        if value in {
            RESULT_SUCCESS,
            RESULT_FAILED,
            RESULT_REJECTED,
            RESULT_BLOCKED,
            RESULT_SYSTEM_GENERATED,
        }:
            return value
        status = _normalize_filter(self._metadata_text(record, "status"))
        if status in FAILED_RESULTS:
            return status
        if self._metadata_text(record, "error_code"):
            return RESULT_FAILED
        return RESULT_SUCCESS

    def _severity(self, record: AuditLog) -> str:
        value = _normalize_filter(
            self._metadata_text(record, "severity") or self._metadata_text(record, "risk_level"),
        )
        if value in {SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_HIGH, SEVERITY_CRITICAL}:
            return value
        if self._result(record) in FAILED_RESULTS:
            return SEVERITY_HIGH
        if self._is_sensitive(record):
            return SEVERITY_WARNING
        return SEVERITY_INFO

    def _is_sensitive(self, record: AuditLog) -> bool:
        metadata = record.metadata_ or {}
        if isinstance(metadata.get("is_sensitive"), bool):
            return bool(metadata["is_sensitive"])
        if self._domain(record) in SENSITIVE_DOMAINS:
            return True
        lowered_action = record.action.lower()
        return any(
            token in lowered_action
            for token in (
                "adjust",
                "cancel",
                "close",
                "created",
                "deactivate",
                "lock",
                "permission",
                "price",
                "reconcile",
                "refund",
                "role",
                "status",
                "updated",
            )
        )

    def _warning_state(self, record: AuditLog) -> str:
        result = self._result(record)
        if result in FAILED_RESULTS:
            return "failed"
        if self._severity(record) in {SEVERITY_HIGH, SEVERITY_CRITICAL}:
            return "high_risk"
        if self._is_sensitive(record):
            return "sensitive"
        if self._source_app(record) == SOURCE_APP_SYSTEM:
            return "system"
        return "none"

    def _entity_reference(self, record: AuditLog) -> str | None:
        metadata = record.metadata_ or {}
        value = (
            metadata.get("folio")
            or metadata.get("reference")
            or metadata.get("code")
            or metadata.get("document_reference")
            or metadata.get("source_reference")
            or metadata.get("name")
            or metadata.get("email")
        )
        return _to_optional_text(value)

    def _metadata_text(self, record: AuditLog, key: str) -> str | None:
        return _to_optional_text((record.metadata_ or {}).get(key))


def _extract_change_pairs(metadata: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    pairs: list[tuple[str, Any, Any]] = []
    previous = metadata.get("previous") or metadata.get("before") or metadata.get("old")
    current = metadata.get("current") or metadata.get("after") or metadata.get("new")
    if isinstance(previous, dict) and isinstance(current, dict):
        for key in sorted(set(previous) | set(current)):
            old_value = previous.get(key)
            new_value = current.get(key)
            if old_value != new_value:
                pairs.append((key, old_value, new_value))

    changes = metadata.get("changes")
    if isinstance(changes, list):
        for item in changes:
            if isinstance(item, dict) and "field" in item:
                pairs.append(
                    (
                        str(item["field"]),
                        item.get("old") or item.get("previous"),
                        item.get("new") or item.get("current"),
                    ),
                )
    elif isinstance(changes, dict):
        for key, value in changes.items():
            if isinstance(value, dict):
                pairs.append(
                    (
                        str(key),
                        value.get("old") or value.get("previous"),
                        value.get("new") or value.get("current"),
                    ),
                )

    for key, old_value in metadata.items():
        if key.startswith("previous_"):
            field = key.removeprefix("previous_")
            new_key = f"new_{field}"
            if new_key in metadata and old_value != metadata.get(new_key):
                pairs.append((field, old_value, metadata.get(new_key)))
        if key.startswith("old_"):
            field = key.removeprefix("old_")
            new_key = f"new_{field}"
            if new_key in metadata and old_value != metadata.get(new_key):
                pairs.append((field, old_value, metadata.get(new_key)))

    deduped: dict[str, tuple[str, Any, Any]] = {}
    for field, old_value, new_value in pairs:
        deduped[field] = (field, old_value, new_value)
    return list(deduped.values())


def _mask_value(field: str, value: Any) -> str | None:
    if value is None:
        return None
    if _is_secret_field(field):
        return "[masked]"
    return _stringify_safe(value)


def _mask_json(value: Any, *, field_name: str = "") -> Any:
    if _is_secret_field(field_name):
        return "[masked]"
    if isinstance(value, dict):
        return {key: _mask_json(child, field_name=key) for key, child in value.items()}
    if isinstance(value, list):
        return [_mask_json(child, field_name=field_name) for child in value]
    return value


def _is_secret_field(field: str) -> bool:
    lowered = field.lower()
    return any(token in lowered for token in SECRET_FIELD_TOKENS)


def _stringify_safe(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(_mask_json(value), default=str, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text if len(text) <= 240 else f"{text[:237]}..."


def _change_type(old_value: Any, new_value: Any) -> str:
    if old_value is None and new_value is not None:
        return "created"
    if old_value is not None and new_value is None:
        return "removed"
    return "updated"


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    return stripped or None


def _normalize_filter(value: str | None) -> str | None:
    normalized = _normalize(value)
    if normalized in {None, "all"}:
        return None
    return normalized


def _to_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _humanize(value: str) -> str:
    return value.replace("_", " ").replace(".", " ").strip().title()


def _options(values: set[str] | dict[str, str]) -> list[AdminAuditFilterOptionView]:
    if isinstance(values, dict):
        items = values.items()
    else:
        items = ((value, _humanize(value)) for value in values)
    return [
        AdminAuditFilterOptionView(code=str(code), label=str(label))
        for code, label in sorted(items, key=lambda item: str(item[1]).lower())
        if str(code).strip()
    ]


def _user_status(user: User) -> str:
    if not user.is_active:
        return "inactive"
    if user.is_locked:
        return "locked"
    return "active"
