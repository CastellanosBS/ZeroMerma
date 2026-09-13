from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.configuration.application.admin_schemas import (
    AdminSettingCategoryView,
    AdminSettingDefinitionView,
    AdminSettingDetailView,
    AdminSettingFilterOptionsView,
    AdminSettingHistoryItemView,
    AdminSettingListItemView,
    AdminSettingMetricsView,
    AdminSettingOptionView,
    AdminSettingsListResponse,
    AdminSettingValidationRuleView,
    AdminSettingValidationView,
    AdminSettingValueView,
    AdminSettingWarningView,
)
from zeromerma_api.modules.configuration.domain.exceptions import (
    SettingNotFoundError,
    SettingReadonlyError,
    SettingSensitiveConfirmationError,
    SettingValidationError,
)
from zeromerma_api.modules.configuration.infrastructure.models import (
    SystemSetting,
    SystemSettingHistory,
)
from zeromerma_api.modules.identity.application.actions import action_allowed
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User

SETTING_SCOPE_GLOBAL = "global"
SETTING_EMPTY_SCOPE_ID = ""
SETTING_STATUS_READY = "ready"
SETTING_STATUS_WARNING = "warning"
SETTING_STATUS_MISSING = "missing"
SETTING_WARNING_READY = "ready"
SETTING_WARNING_WARNING = "warning"
SETTING_WARNING_BLOCKED = "blocked"
AUDIT_ACTION_SETTING_UPDATED = "admin.setting.updated"
AUDIT_ACTION_SETTING_RESET = "admin.setting.reset"
SETTING_RESOURCE_TYPE = "system_setting"


@dataclass(frozen=True)
class _SettingOption:
    id: str
    label: str


@dataclass(frozen=True)
class _SettingDefinition:
    key: str
    label: str
    description: str
    category: str
    type: str
    default_value: Any
    affects_modules: tuple[str, ...]
    options: tuple[_SettingOption, ...] = ()
    is_required: bool = False
    is_sensitive: bool = False
    is_readonly: bool = False
    requires_restart: bool = False
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    min_length: int | None = None
    max_length: int | None = None
    supported_scopes: tuple[str, ...] = (SETTING_SCOPE_GLOBAL,)


class AdminSettingService:
    def __init__(
        self,
        *,
        audit_recorder: AuditRecorder | None = None,
        settings: ApiSettings | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._settings = settings or get_settings()

    def list_settings(
        self,
        session: Session,
        *,
        search: str | None,
        category: str | None,
        status_filter: str | None,
        sensitivity: str | None,
        readonly: str | None,
        scope: str | None,
        affected_module: str | None,
    ) -> AdminSettingsListResponse:
        overrides = self._load_overrides(session)
        updated_by = self._load_users(
            session,
            [setting.updated_by_user_id for setting in overrides.values()],
        )
        items = [
            self._to_list_item(session, definition, overrides.get(definition.key), updated_by)
            for definition in _SETTING_DEFINITIONS
        ]
        filtered = self._apply_filters(
            items,
            search=search,
            category=category,
            status_filter=status_filter,
            sensitivity=sensitivity,
            readonly=readonly,
            scope=scope,
            affected_module=affected_module,
        )
        return AdminSettingsListResponse(
            categories=[
                AdminSettingCategoryView(id=key, label=label, description=description)
                for key, (label, description) in CATEGORY_DEFINITIONS.items()
            ],
            filter_options=self._filter_options(),
            items=filtered,
            metrics=self._metrics(session, items, overrides),
            total=len(filtered),
        )

    def get_setting_detail(self, session: Session, *, key: str) -> AdminSettingDetailView:
        definition = self._get_definition(key)
        override = self._get_override(session, definition.key)
        updated_by = self._load_users(
            session,
            [override.updated_by_user_id if override else None],
        )
        value_view = self._to_value_view(definition, override, updated_by)
        warnings = self._warnings(definition, value_view)
        return AdminSettingDetailView(
            available_actions=self._available_actions(session, definition, override),
            definition=self._definition_view(definition),
            history=self._history(session, definition),
            validation=AdminSettingValidationView(
                is_valid=value_view.status != SETTING_STATUS_MISSING,
                messages=[
                    warning.message for warning in warnings if warning.severity == "critical"
                ],
            ),
            value=value_view,
            warnings=warnings,
        )

    def update_setting(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        key: str,
        value: Any,
        change_note: str | None,
        confirm_sensitive: bool,
        request_id: str | None,
    ) -> AdminSettingDetailView:
        definition = self._get_definition(key)
        if definition.is_readonly:
            raise SettingReadonlyError("This setting is read-only.")
        if definition.is_sensitive and not confirm_sensitive:
            raise SettingSensitiveConfirmationError("Sensitive setting changes must be confirmed.")

        normalized_value = self._validate_value(definition, value)
        override = self._get_override(session, definition.key)
        old_value = self._current_value(definition, override)
        now = datetime.now(tz=UTC)

        if override is None:
            override = SystemSetting(
                key=definition.key,
                scope=SETTING_SCOPE_GLOBAL,
                scope_id=SETTING_EMPTY_SCOPE_ID,
                value=normalized_value,
                updated_by_user_id=current_user.id,
                created_at=now,
                updated_at=now,
            )
            session.add(override)
        else:
            override.value = normalized_value
            override.updated_by_user_id = current_user.id
            override.updated_at = now

        self._add_history(
            session,
            current_user=current_user,
            definition=definition,
            old_value=old_value,
            new_value=normalized_value,
            change_note=change_note,
        )
        self._record_audit(
            session,
            action=AUDIT_ACTION_SETTING_UPDATED,
            current_user=current_user,
            definition=definition,
            old_value=old_value,
            new_value=normalized_value,
            request_id=request_id,
        )
        session.commit()
        return self.get_setting_detail(session, key=definition.key)

    def reset_setting(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        key: str,
        change_note: str | None,
        confirm_sensitive: bool,
        request_id: str | None,
    ) -> AdminSettingDetailView:
        definition = self._get_definition(key)
        if definition.is_readonly:
            raise SettingReadonlyError("This setting is read-only.")
        if definition.is_sensitive and not confirm_sensitive:
            raise SettingSensitiveConfirmationError("Sensitive setting changes must be confirmed.")

        override = self._get_override(session, definition.key)
        old_value = self._current_value(definition, override)
        default_value = self._default_value(definition)
        if override is not None:
            session.execute(
                delete(SystemSetting).where(SystemSetting.id == override.id),
            )
        self._add_history(
            session,
            current_user=current_user,
            definition=definition,
            old_value=old_value,
            new_value=default_value,
            change_note=change_note or "Reset to default value.",
        )
        self._record_audit(
            session,
            action=AUDIT_ACTION_SETTING_RESET,
            current_user=current_user,
            definition=definition,
            old_value=old_value,
            new_value=default_value,
            request_id=request_id,
        )
        session.commit()
        return self.get_setting_detail(session, key=definition.key)

    def _load_overrides(self, session: Session) -> dict[str, SystemSetting]:
        rows = session.execute(
            select(SystemSetting).where(
                SystemSetting.scope == SETTING_SCOPE_GLOBAL,
                SystemSetting.scope_id == SETTING_EMPTY_SCOPE_ID,
            )
        ).scalars()
        return {setting.key: setting for setting in rows}

    def _get_override(self, session: Session, key: str) -> SystemSetting | None:
        return session.execute(
            select(SystemSetting).where(
                SystemSetting.key == key,
                SystemSetting.scope == SETTING_SCOPE_GLOBAL,
                SystemSetting.scope_id == SETTING_EMPTY_SCOPE_ID,
            )
        ).scalar_one_or_none()

    def _load_users(
        self,
        session: Session,
        user_ids: Iterable[uuid.UUID | None],
    ) -> dict[uuid.UUID, User]:
        ids = {user_id for user_id in user_ids if user_id is not None}
        if not ids:
            return {}
        users = session.execute(select(User).where(User.id.in_(ids))).scalars().all()
        return {user.id: user for user in users}

    def _to_list_item(
        self,
        session: Session,
        definition: _SettingDefinition,
        override: SystemSetting | None,
        updated_by: dict[uuid.UUID, User],
    ) -> AdminSettingListItemView:
        value = self._to_value_view(definition, override, updated_by)
        warnings = self._warnings(definition, value)
        return AdminSettingListItemView(
            available_actions=self._available_actions(session, definition, override),
            definition=self._definition_view(definition),
            value=value,
            warnings=warnings,
        )

    def _definition_view(self, definition: _SettingDefinition) -> AdminSettingDefinitionView:
        return AdminSettingDefinitionView(
            affects_modules=list(definition.affects_modules),
            category=definition.category,
            category_label=CATEGORY_DEFINITIONS[definition.category][0],
            default_value=self._public_value(definition, self._default_value(definition)),
            description=definition.description,
            is_readonly=definition.is_readonly,
            is_required=definition.is_required,
            is_sensitive=definition.is_sensitive,
            key=definition.key,
            label=definition.label,
            options=[
                AdminSettingOptionView(id=option.id, label=option.label)
                for option in definition.options
            ],
            requires_restart=definition.requires_restart,
            scope=SETTING_SCOPE_GLOBAL,
            supported_scopes=list(definition.supported_scopes),
            type=definition.type,
            validation_rules=self._validation_rules(definition),
        )

    def _to_value_view(
        self,
        definition: _SettingDefinition,
        override: SystemSetting | None,
        updated_by: dict[uuid.UUID, User],
    ) -> AdminSettingValueView:
        effective_value = self._current_value(definition, override)
        updated_user = (
            updated_by.get(override.updated_by_user_id)
            if override and override.updated_by_user_id
            else None
        )
        status = self._status(definition, effective_value)
        warning_state = self._warning_state(definition, status)
        return AdminSettingValueView(
            current_value=self._public_value(definition, effective_value),
            effective_value=self._public_value(definition, effective_value),
            inherited_from=None if override else "default",
            key=definition.key,
            scope=SETTING_SCOPE_GLOBAL,
            scope_id=None,
            status=status,
            updated_at=override.updated_at if override else None,
            updated_by=updated_user.full_name if updated_user else None,
            warning_state=warning_state,
        )

    def _public_value(self, definition: _SettingDefinition, value: Any) -> Any:
        if definition.is_sensitive:
            return self._mask_value(value)
        return value

    def _mask_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "habilitado" if value else "deshabilitado"
        if value is None:
            return "sin valor"
        return "valor sensible"

    def _current_value(self, definition: _SettingDefinition, override: SystemSetting | None) -> Any:
        if override is not None:
            return override.value
        return self._default_value(definition)

    def _default_value(self, definition: _SettingDefinition) -> Any:
        if definition.key == "advanced.environment":
            return self._settings.environment
        if definition.key == "waste.high_impact_merma_quantity_threshold":
            return str(self._settings.waste_high_impact_quantity_threshold)
        if definition.key == "returns.high_refund_amount_threshold":
            return str(self._settings.return_high_refund_amount_threshold)
        return definition.default_value

    def _status(self, definition: _SettingDefinition, value: Any) -> str:
        if definition.is_required and self._is_empty(value):
            return SETTING_STATUS_MISSING
        if definition.category == "integrations" and value == "not_configured":
            return SETTING_STATUS_WARNING
        if definition.is_sensitive or definition.is_readonly or definition.requires_restart:
            return SETTING_STATUS_WARNING
        return SETTING_STATUS_READY

    def _warning_state(self, definition: _SettingDefinition, status: str) -> str:
        if status == SETTING_STATUS_MISSING:
            return SETTING_WARNING_BLOCKED
        if status == SETTING_STATUS_WARNING or definition.is_sensitive:
            return SETTING_WARNING_WARNING
        return SETTING_WARNING_READY

    def _warnings(
        self,
        definition: _SettingDefinition,
        value: AdminSettingValueView,
    ) -> list[AdminSettingWarningView]:
        warnings: list[AdminSettingWarningView] = []
        if value.status == SETTING_STATUS_MISSING:
            warnings.append(
                AdminSettingWarningView(
                    code="required_missing",
                    message="Esta configuracion requerida no tiene valor efectivo.",
                    severity="critical",
                )
            )
        if definition.is_readonly:
            warnings.append(
                AdminSettingWarningView(
                    code="readonly",
                    message="Esta configuracion es de solo lectura desde Backoffice.",
                    severity="info",
                )
            )
        if definition.is_sensitive:
            warnings.append(
                AdminSettingWarningView(
                    code="sensitive",
                    message="Cambiar este valor puede afectar operacion sensible.",
                    severity="warning",
                )
            )
        if definition.requires_restart:
            warnings.append(
                AdminSettingWarningView(
                    code="requires_restart",
                    message="El cambio puede requerir reinicio o recarga de clientes.",
                    severity="warning",
                )
            )
        if definition.category == "integrations" and value.effective_value == "not_configured":
            warnings.append(
                AdminSettingWarningView(
                    code="integration_not_configured",
                    message="La integracion esta documentada pero no configurada.",
                    severity="warning",
                )
            )
        return warnings

    def _available_actions(
        self,
        session: Session,
        definition: _SettingDefinition,
        override: SystemSetting | None,
    ) -> list[str]:
        actions = ["view", "copy_key", "view_history"]
        if not definition.is_readonly and action_allowed(
            session, "config.manage", global_only=True
        ):
            actions.append("edit")
            if override is not None:
                actions.append("reset")
        return actions

    def _validate_value(self, definition: _SettingDefinition, value: Any) -> Any:
        if definition.type == "boolean":
            if not isinstance(value, bool):
                raise SettingValidationError("Boolean settings require true or false.")
            return value
        if definition.type == "enum":
            text_value = self._validate_string(definition, value)
            option_ids = {option.id for option in definition.options}
            if text_value not in option_ids:
                raise SettingValidationError("Setting value is not allowed.")
            return text_value
        if definition.type == "string":
            return self._validate_string(definition, value)
        if definition.type in {"money", "number", "percentage", "duration"}:
            return self._validate_numeric(definition, value)
        raise SettingValidationError("Unsupported setting type.")

    def _validate_string(self, definition: _SettingDefinition, value: Any) -> str:
        if not isinstance(value, str):
            raise SettingValidationError("Text settings require a string value.")
        text_value = value.strip()
        if definition.is_required and not text_value:
            raise SettingValidationError("This setting is required.")
        if definition.min_length is not None and len(text_value) < definition.min_length:
            raise SettingValidationError("Setting value is too short.")
        if definition.max_length is not None and len(text_value) > definition.max_length:
            raise SettingValidationError("Setting value is too long.")
        return text_value

    def _validate_numeric(self, definition: _SettingDefinition, value: Any) -> int | str:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise SettingValidationError("Numeric settings require a valid number.") from error
        if definition.type == "number" and decimal_value != decimal_value.to_integral_value():
            raise SettingValidationError("This setting requires a whole number.")
        if definition.min_value is not None and decimal_value < definition.min_value:
            raise SettingValidationError("Setting value is below the allowed minimum.")
        if definition.max_value is not None and decimal_value > definition.max_value:
            raise SettingValidationError("Setting value is above the allowed maximum.")
        if definition.type == "number" or definition.type == "duration":
            return int(decimal_value)
        return str(decimal_value.normalize())

    def _add_history(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        definition: _SettingDefinition,
        old_value: Any,
        new_value: Any,
        change_note: str | None,
    ) -> None:
        session.add(
            SystemSettingHistory(
                setting_key=definition.key,
                scope=SETTING_SCOPE_GLOBAL,
                scope_id=SETTING_EMPTY_SCOPE_ID,
                old_value=old_value,
                new_value=new_value,
                changed_by_user_id=current_user.id,
                change_note=change_note,
            )
        )

    def _record_audit(
        self,
        session: Session,
        *,
        action: str,
        current_user: AuthenticatedUser,
        definition: _SettingDefinition,
        old_value: Any,
        new_value: Any,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=SETTING_RESOURCE_TYPE,
            resource_id=definition.key,
            branch_id=None,
            request_id=request_id,
            metadata={
                "category": definition.category,
                "is_sensitive": definition.is_sensitive,
                "module": "configuration",
                "new_value": self._mask_for_audit(definition, new_value),
                "old_value": self._mask_for_audit(definition, old_value),
                "result": "success",
                "scope": SETTING_SCOPE_GLOBAL,
                "setting_key": definition.key,
            },
        )

    def _mask_for_audit(self, definition: _SettingDefinition, value: Any) -> Any:
        if definition.is_sensitive:
            return self._mask_value(value)
        return value

    def _history(
        self,
        session: Session,
        definition: _SettingDefinition,
    ) -> list[AdminSettingHistoryItemView]:
        history_rows = (
            session.execute(
                select(SystemSettingHistory)
                .where(SystemSettingHistory.setting_key == definition.key)
                .order_by(SystemSettingHistory.changed_at.desc())
                .limit(10)
            )
            .scalars()
            .all()
        )
        users = self._load_users(session, [row.changed_by_user_id for row in history_rows])
        return [
            AdminSettingHistoryItemView(
                changed_at=row.changed_at,
                changed_by=users[row.changed_by_user_id].full_name
                if row.changed_by_user_id in users
                else None,
                new_value_masked=str(self._mask_for_audit(definition, row.new_value)),
                note=row.change_note,
                old_value_masked=str(self._mask_for_audit(definition, row.old_value)),
                scope=row.scope,
            )
            for row in history_rows
        ]

    def _validation_rules(
        self,
        definition: _SettingDefinition,
    ) -> list[AdminSettingValidationRuleView]:
        rules: list[AdminSettingValidationRuleView] = []
        if definition.is_required:
            rules.append(
                AdminSettingValidationRuleView(
                    rule="required",
                    message="El valor es obligatorio.",
                    value=True,
                )
            )
        if definition.min_value is not None:
            rules.append(
                AdminSettingValidationRuleView(
                    rule="min",
                    message="Valor minimo permitido.",
                    value=str(definition.min_value),
                )
            )
        if definition.max_value is not None:
            rules.append(
                AdminSettingValidationRuleView(
                    rule="max",
                    message="Valor maximo permitido.",
                    value=str(definition.max_value),
                )
            )
        if definition.max_length is not None:
            rules.append(
                AdminSettingValidationRuleView(
                    rule="max_length",
                    message="Longitud maxima permitida.",
                    value=definition.max_length,
                )
            )
        return rules

    def _metrics(
        self,
        session: Session,
        items: list[AdminSettingListItemView],
        overrides: dict[str, SystemSetting],
    ) -> AdminSettingMetricsView:
        recent_since = datetime.now(tz=UTC) - timedelta(days=7)
        recent_changes = (
            session.execute(
                select(SystemSettingHistory).where(SystemSettingHistory.changed_at >= recent_since)
            )
            .scalars()
            .all()
        )
        return AdminSettingMetricsView(
            active_settings=len(items),
            incomplete_required=sum(
                1 for item in items if item.value.status == SETTING_STATUS_MISSING
            ),
            integration_settings=sum(
                1 for item in items if item.definition.category == "integrations"
            ),
            recent_changes=len(recent_changes),
            scoped_overrides=sum(1 for setting in overrides.values() if setting.scope != "global"),
            sensitive_settings=sum(1 for item in items if item.definition.is_sensitive),
            warning_settings=sum(
                1 for item in items if item.value.warning_state != SETTING_WARNING_READY
            ),
        )

    def _filter_options(self) -> AdminSettingFilterOptionsView:
        modules = sorted(
            {module for definition in _SETTING_DEFINITIONS for module in definition.affects_modules}
        )
        return AdminSettingFilterOptionsView(
            categories=[
                AdminSettingOptionView(id=key, label=label)
                for key, (label, _description) in CATEGORY_DEFINITIONS.items()
            ],
            modules=[
                AdminSettingOptionView(id=module, label=_humanize(module)) for module in modules
            ],
            readonly_states=[
                AdminSettingOptionView(id="editable", label="Editables"),
                AdminSettingOptionView(id="readonly", label="Solo lectura"),
            ],
            scopes=[AdminSettingOptionView(id=SETTING_SCOPE_GLOBAL, label="Global")],
            sensitivities=[
                AdminSettingOptionView(id="sensitive", label="Sensibles"),
                AdminSettingOptionView(id="standard", label="Operativas"),
            ],
            statuses=[
                AdminSettingOptionView(id=SETTING_STATUS_READY, label="Listas"),
                AdminSettingOptionView(id=SETTING_STATUS_WARNING, label="Con advertencias"),
                AdminSettingOptionView(id=SETTING_STATUS_MISSING, label="Pendientes"),
            ],
        )

    def _apply_filters(
        self,
        items: list[AdminSettingListItemView],
        *,
        search: str | None,
        category: str | None,
        status_filter: str | None,
        sensitivity: str | None,
        readonly: str | None,
        scope: str | None,
        affected_module: str | None,
    ) -> list[AdminSettingListItemView]:
        filtered = items
        normalized_search = _normalize(search)
        if normalized_search:
            filtered = [
                item
                for item in filtered
                if normalized_search
                in " ".join(
                    [
                        item.definition.key,
                        item.definition.label,
                        item.definition.description,
                        item.definition.category_label,
                        *item.definition.affects_modules,
                    ]
                ).lower()
            ]
        if _active_filter(category):
            filtered = [item for item in filtered if item.definition.category == category]
        if _active_filter(status_filter):
            filtered = [item for item in filtered if item.value.status == status_filter]
        if sensitivity == "sensitive":
            filtered = [item for item in filtered if item.definition.is_sensitive]
        elif sensitivity == "standard":
            filtered = [item for item in filtered if not item.definition.is_sensitive]
        if readonly == "readonly":
            filtered = [item for item in filtered if item.definition.is_readonly]
        elif readonly == "editable":
            filtered = [item for item in filtered if not item.definition.is_readonly]
        if _active_filter(scope):
            filtered = [item for item in filtered if item.value.scope == scope]
        if _active_filter(affected_module):
            filtered = [
                item for item in filtered if affected_module in item.definition.affects_modules
            ]
        return filtered

    def _get_definition(self, key: str) -> _SettingDefinition:
        normalized = key.strip().lower()
        for definition in _SETTING_DEFINITIONS:
            if definition.key == normalized:
                return definition
        raise SettingNotFoundError("Setting key is not registered.")

    def _is_empty(self, value: Any) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())


def _option(id_: str, label: str) -> _SettingOption:
    return _SettingOption(id=id_, label=label)


def _normalize(value: str | None) -> str:
    return value.strip().lower() if value else ""


def _active_filter(value: str | None) -> bool:
    return bool(value and value != "all")


def _humanize(value: str) -> str:
    return value.replace("_", " ").replace(".", " ").title()


CATEGORY_DEFINITIONS: dict[str, tuple[str, str]] = {
    "general": ("General", "Identidad del negocio y defaults operativos."),
    "localization": ("Localizacion", "Formato de moneda, idioma, fecha y zona horaria."),
    "pos": ("POS", "Comportamiento operativo del punto de venta."),
    "cash": ("Caja", "Reglas de apertura, cierre, metodos y diferencias de caja."),
    "orders": ("Pedidos", "Politicas de anticipos, cancelaciones y tiempos."),
    "returns": ("Devoluciones y correcciones", "Reglas de devoluciones y ajustes."),
    "inventory": ("Inventario", "Politicas de stock, conteos y ajustes."),
    "production": ("Produccion", "Defaults para recetas, faltantes y variaciones."),
    "waste": ("Merma", "Politicas de merma, evidencia y notificaciones."),
    "purchases": ("Compras", "Defaults de compras, recepcion y proveedores."),
    "quality": ("Calidad e higiene", "Limpieza, verificaciones, incidencias y mantenimiento."),
    "tickets": ("Tickets y comprobantes", "Texto y comportamiento de comprobantes."),
    "notifications": ("Notificaciones", "Alertas operativas de alto impacto."),
    "integrations": ("Integraciones", "Estado de integraciones externas sin secretos."),
    "advanced": ("Avanzado", "Metadatos seguros y banderas del sistema."),
}


_SETTING_DEFINITIONS: tuple[_SettingDefinition, ...] = (
    _SettingDefinition(
        key="general.business_name",
        label="Nombre del negocio",
        description="Nombre comercial que se usa como valor operativo por defecto.",
        category="general",
        type="string",
        default_value="ZeroMerma",
        affects_modules=("backoffice", "tickets", "reports"),
        is_required=True,
        max_length=120,
    ),
    _SettingDefinition(
        key="localization.default_currency",
        label="Moneda predeterminada",
        description="Moneda operativa por defecto para vistas administrativas y comprobantes.",
        category="localization",
        type="enum",
        default_value="MXN",
        affects_modules=("sales", "cash", "purchases", "reports"),
        is_required=True,
        options=(_option("MXN", "MXN"), _option("USD", "USD")),
    ),
    _SettingDefinition(
        key="localization.default_timezone",
        label="Zona horaria predeterminada",
        description="Zona horaria global cuando una sucursal no tiene una propia.",
        category="localization",
        type="enum",
        default_value="America/Hermosillo",
        affects_modules=("pos", "reports", "audit"),
        is_required=True,
        options=(
            _option("America/Hermosillo", "America/Hermosillo"),
            _option("America/Mexico_City", "America/Mexico_City"),
        ),
    ),
    _SettingDefinition(
        key="localization.default_locale",
        label="Idioma y region predeterminada",
        description="Locale usado para formato general en Backoffice.",
        category="localization",
        type="enum",
        default_value="es-MX",
        affects_modules=("backoffice", "reports"),
        is_required=True,
        options=(_option("es-MX", "Espanol Mexico"), _option("en-US", "English US")),
    ),
    _SettingDefinition(
        key="pos.default_ticket_requested",
        label="Ticket solicitado por defecto",
        description="Valor inicial para solicitud de ticket en flujos POS compatibles.",
        category="pos",
        type="boolean",
        default_value=True,
        affects_modules=("pos", "tickets"),
    ),
    _SettingDefinition(
        key="pos.numpad_hints_enabled",
        label="Ayudas de teclado numerico",
        description="Muestra sugerencias de teclado/numpad donde el POS lo soporte.",
        category="pos",
        type="boolean",
        default_value=True,
        affects_modules=("pos",),
    ),
    _SettingDefinition(
        key="pos.product_search_min_length",
        label="Minimo de busqueda de producto",
        description="Numero minimo de caracteres para activar busquedas asistidas.",
        category="pos",
        type="number",
        default_value=2,
        affects_modules=("pos", "catalog"),
        min_value=Decimal("1"),
        max_value=Decimal("5"),
    ),
    _SettingDefinition(
        key="pos.allow_mixed_payment",
        label="Permitir pago mixto",
        description="Habilita pagos mixtos cuando el flujo POS y pagos lo soporte.",
        category="pos",
        type="boolean",
        default_value=True,
        affects_modules=("pos", "payments", "cash"),
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="cash.cash_opening_required",
        label="Apertura de caja obligatoria",
        description="Regla central: una caja debe abrir sesion antes de operar.",
        category="cash",
        type="boolean",
        default_value=True,
        affects_modules=("pos", "cash"),
        is_readonly=True,
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="cash.cash_closing_required",
        label="Cierre de caja obligatorio",
        description="Regla central: toda sesion de caja debe cerrarse.",
        category="cash",
        type="boolean",
        default_value=True,
        affects_modules=("pos", "cash_close"),
        is_readonly=True,
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="cash.cash_difference_tolerance",
        label="Tolerancia de diferencia de caja",
        description="Monto de referencia para marcar diferencias de caja.",
        category="cash",
        type="money",
        default_value="50",
        affects_modules=("cash_close", "reconciliation", "reports"),
        is_sensitive=True,
        min_value=Decimal("0"),
        max_value=Decimal("10000"),
    ),
    _SettingDefinition(
        key="cash.high_impact_cash_difference_threshold",
        label="Diferencia de caja de alto impacto",
        description="Umbral para resaltar diferencias de caja sensibles.",
        category="cash",
        type="money",
        default_value="500",
        affects_modules=("cash_close", "audit", "notifications"),
        is_sensitive=True,
        min_value=Decimal("0"),
        max_value=Decimal("100000"),
    ),
    _SettingDefinition(
        key="orders.minimum_deposit_percentage",
        label="Anticipo minimo de pedido",
        description="Porcentaje recomendado de anticipo para pedidos.",
        category="orders",
        type="percentage",
        default_value="30",
        affects_modules=("orders", "payments"),
        is_sensitive=True,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    ),
    _SettingDefinition(
        key="orders.cancellation_refund_cutoff_days",
        label="Ventana de cancelacion reembolsable",
        description="Dias antes de entrega para permitir reembolso segun politica.",
        category="orders",
        type="number",
        default_value=1,
        affects_modules=("orders", "returns"),
        is_sensitive=True,
        min_value=Decimal("0"),
        max_value=Decimal("30"),
    ),
    _SettingDefinition(
        key="returns.return_window_days",
        label="Ventana de devolucion",
        description="Dias de referencia para revisar devoluciones operativas.",
        category="returns",
        type="number",
        default_value=7,
        affects_modules=("returns", "tickets"),
        min_value=Decimal("0"),
        max_value=Decimal("365"),
    ),
    _SettingDefinition(
        key="returns.high_refund_amount_threshold",
        label="Reembolso de alto impacto",
        description="Monto de devolucion que debe resaltarse como sensible.",
        category="returns",
        type="money",
        default_value="200",
        affects_modules=("returns", "audit", "notifications"),
        is_sensitive=True,
        min_value=Decimal("0"),
        max_value=Decimal("100000"),
    ),
    _SettingDefinition(
        key="inventory.allow_negative_stock",
        label="Permitir stock negativo",
        description="Politica de referencia para movimientos que podrian dejar stock negativo.",
        category="inventory",
        type="boolean",
        default_value=False,
        affects_modules=("inventory", "production", "waste"),
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="inventory.low_stock_warning_enabled",
        label="Advertencia de stock bajo",
        description="Activa alertas operativas para productos debajo de minimo.",
        category="inventory",
        type="boolean",
        default_value=True,
        affects_modules=("inventory", "notifications", "reports"),
    ),
    _SettingDefinition(
        key="production.require_active_recipe",
        label="Requerir receta activa",
        description="Politica para producir solo con receta activa cuando aplique.",
        category="production",
        type="boolean",
        default_value=True,
        affects_modules=("production", "recipes"),
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="production.yield_variance_threshold",
        label="Umbral de variacion de rendimiento",
        description="Porcentaje para marcar variaciones de produccion.",
        category="production",
        type="percentage",
        default_value="5",
        affects_modules=("production", "reports"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    ),
    _SettingDefinition(
        key="waste.reason_required",
        label="Motivo de merma obligatorio",
        description="Regla central: toda merma confirmada debe tener motivo.",
        category="waste",
        type="boolean",
        default_value=True,
        affects_modules=("waste", "inventory"),
        is_readonly=True,
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="waste.high_impact_merma_quantity_threshold",
        label="Cantidad de merma de alto impacto",
        description="Cantidad que resalta merma sensible y notificaciones operativas.",
        category="waste",
        type="number",
        default_value=10,
        affects_modules=("waste", "operations", "notifications"),
        is_sensitive=True,
        min_value=Decimal("1"),
        max_value=Decimal("100000"),
    ),
    _SettingDefinition(
        key="purchases.default_purchase_currency",
        label="Moneda predeterminada de compras",
        description="Moneda sugerida para documentos de compras y abastecimiento.",
        category="purchases",
        type="enum",
        default_value="MXN",
        affects_modules=("purchases", "suppliers"),
        options=(_option("MXN", "MXN"), _option("USD", "USD")),
    ),
    _SettingDefinition(
        key="purchases.receipt_discrepancy_reason_required",
        label="Motivo requerido en discrepancias",
        description="Requiere nota al registrar diferencias de recepcion.",
        category="purchases",
        type="boolean",
        default_value=True,
        affects_modules=("purchases", "inventory"),
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="quality.cleaning_evidence_required_for_high_risk",
        label="Evidencia en limpieza de alto riesgo",
        description="Requiere evidencia para zonas/tareas de limpieza de alto riesgo.",
        category="quality",
        type="boolean",
        default_value=False,
        affects_modules=("cleaning_logs", "audit"),
        is_sensitive=True,
    ),
    _SettingDefinition(
        key="quality.sanitary_verification_pass_threshold",
        label="Umbral de aprobacion sanitaria",
        description="Porcentaje minimo de cumplimiento para verificaciones sanitarias.",
        category="quality",
        type="percentage",
        default_value="80",
        affects_modules=("sanitary_verifications", "incidents"),
        is_sensitive=True,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    ),
    _SettingDefinition(
        key="quality.incident_high_risk_notification_enabled",
        label="Alertar incidencias de alto riesgo",
        description="Activa notificaciones Backoffice para incidencias criticas.",
        category="quality",
        type="boolean",
        default_value=True,
        affects_modules=("incidents", "notifications"),
    ),
    _SettingDefinition(
        key="tickets.receipt_footer_text",
        label="Pie de ticket",
        description="Texto operativo mostrado en comprobantes cuando el emisor lo soporte.",
        category="tickets",
        type="string",
        default_value="Gracias por su compra.",
        affects_modules=("tickets", "pos"),
        max_length=240,
    ),
    _SettingDefinition(
        key="notifications.cash_difference_enabled",
        label="Notificar diferencias de caja",
        description="Activa alertas internas para diferencias relevantes.",
        category="notifications",
        type="boolean",
        default_value=True,
        affects_modules=("cash_close", "notifications"),
    ),
    _SettingDefinition(
        key="notifications.low_stock_enabled",
        label="Notificar stock bajo",
        description="Activa alertas internas para bajo stock.",
        category="notifications",
        type="boolean",
        default_value=True,
        affects_modules=("inventory", "notifications"),
    ),
    _SettingDefinition(
        key="integrations.payment_terminal_status",
        label="Terminal de pago",
        description="Estado visible de la integracion de terminales, sin exponer secretos.",
        category="integrations",
        type="enum",
        default_value="not_configured",
        affects_modules=("payments", "pos"),
        is_readonly=True,
        options=(
            _option("not_configured", "No configurada"),
            _option("configured", "Configurada"),
            _option("disabled", "Deshabilitada"),
        ),
    ),
    _SettingDefinition(
        key="advanced.environment",
        label="Ambiente del sistema",
        description="Ambiente runtime reportado por la API. No se modifica desde Backoffice.",
        category="advanced",
        type="string",
        default_value="local",
        affects_modules=("system", "audit"),
        is_readonly=True,
    ),
    _SettingDefinition(
        key="advanced.feature_flags_supported",
        label="Feature flags desde Backoffice",
        description="Indica si hay contrato backend para feature flags administrables.",
        category="advanced",
        type="boolean",
        default_value=False,
        affects_modules=("system", "backoffice"),
        is_readonly=True,
    ),
)
