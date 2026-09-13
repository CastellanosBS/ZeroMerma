"""Normalize capability scopes and privileged administration.

Revision ID: 20260912_0040_authorization
Revises: 20260520_0039_system_settings
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0040_authorization"
down_revision: str | None = "20260520_0039_system_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen DEC-03 catalog. Future catalog changes require a deliberate migration.
CAPABILITIES: tuple[tuple[str, str, str, str, str, tuple[str, ...], bool], ...] = (
    ("pos.operate", "Operar POS", "pos", "POS", "operate", ("POS",), True),
    (
        "sales_tickets.view",
        "Consultar Ventas / Tickets",
        "sales_tickets",
        "Ventas / Tickets",
        "view",
        ("POS", "BACKOFFICE"),
        False,
    ),
    (
        "sales_tickets.reprint",
        "Reimprimir Ventas / Tickets",
        "sales_tickets",
        "Ventas / Tickets",
        "reprint",
        ("POS", "BACKOFFICE"),
        True,
    ),
    ("orders.view", "Consultar Pedidos", "orders", "Pedidos", "view", ("POS", "BACKOFFICE"), False),
    (
        "orders.manage",
        "Gestionar Pedidos",
        "orders",
        "Pedidos",
        "manage",
        ("POS", "BACKOFFICE"),
        True,
    ),
    (
        "orders.cancel",
        "Cancelar Pedidos",
        "orders",
        "Pedidos",
        "cancel",
        ("POS", "BACKOFFICE"),
        True,
    ),
    (
        "returns_corrections.view",
        "Consultar Devoluciones / Correcciones",
        "returns_corrections",
        "Devoluciones / Correcciones",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "returns_corrections.manage",
        "Gestionar Devoluciones / Correcciones",
        "returns_corrections",
        "Devoluciones / Correcciones",
        "manage",
        ("POS", "BACKOFFICE"),
        True,
    ),
    ("catalog.view", "Consultar Catálogo", "catalog", "Catálogo", "view", ("BACKOFFICE",), False),
    (
        "catalog.manage",
        "Gestionar Catálogo",
        "catalog",
        "Catálogo",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    (
        "catalog.availability.manage",
        "Gestionar disponibilidad Catálogo",
        "catalog",
        "Catálogo",
        "availability.manage",
        ("BACKOFFICE",),
        True,
    ),
    ("pricing.view", "Consultar Precios", "pricing", "Precios", "view", ("BACKOFFICE",), False),
    ("pricing.manage", "Gestionar Precios", "pricing", "Precios", "manage", ("BACKOFFICE",), True),
    ("recipes.view", "Consultar Recetas", "recipes", "Recetas", "view", ("BACKOFFICE",), False),
    ("recipes.manage", "Gestionar Recetas", "recipes", "Recetas", "manage", ("BACKOFFICE",), True),
    (
        "discounts.view",
        "Consultar Descuentos",
        "discounts",
        "Descuentos",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "discounts.manage",
        "Gestionar Descuentos",
        "discounts",
        "Descuentos",
        "manage",
        ("POS", "BACKOFFICE"),
        True,
    ),
    (
        "inventory.view",
        "Consultar Inventario",
        "inventory",
        "Inventario",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "inventory.adjust",
        "Ajustar Inventario",
        "inventory",
        "Inventario",
        "adjust",
        ("BACKOFFICE",),
        True,
    ),
    (
        "branches.view",
        "Consultar Sucursales",
        "branches",
        "Sucursales",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "branches.manage",
        "Gestionar Sucursales",
        "branches",
        "Sucursales",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    (
        "workstations.view",
        "Consultar Estaciones",
        "workstations",
        "Estaciones",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "workstations.manage",
        "Gestionar Estaciones",
        "workstations",
        "Estaciones",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    (
        "transfers.view",
        "Consultar Transferencias",
        "transfers",
        "Transferencias",
        "view",
        ("POS", "BACKOFFICE"),
        False,
    ),
    (
        "transfers.manage",
        "Gestionar Transferencias",
        "transfers",
        "Transferencias",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    (
        "transfers.execute",
        "Ejecutar Transferencias",
        "transfers",
        "Transferencias",
        "execute",
        ("POS", "BACKOFFICE"),
        True,
    ),
    (
        "transfers.cancel",
        "Cancelar Transferencias",
        "transfers",
        "Transferencias",
        "cancel",
        ("BACKOFFICE",),
        True,
    ),
    (
        "production.view",
        "Consultar Producción",
        "production",
        "Producción",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "production.manage",
        "Gestionar Producción",
        "production",
        "Producción",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    (
        "production.execute",
        "Ejecutar Producción",
        "production",
        "Producción",
        "execute",
        ("BACKOFFICE",),
        True,
    ),
    (
        "production.cancel",
        "Cancelar Producción",
        "production",
        "Producción",
        "cancel",
        ("BACKOFFICE",),
        True,
    ),
    ("waste.view", "Consultar Merma", "waste", "Merma", "view", ("BACKOFFICE",), False),
    ("waste.manage", "Gestionar Merma", "waste", "Merma", "manage", ("BACKOFFICE",), True),
    (
        "suppliers.view",
        "Consultar Proveedores",
        "suppliers",
        "Proveedores",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "suppliers.manage",
        "Gestionar Proveedores",
        "suppliers",
        "Proveedores",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    ("purchases.view", "Consultar Compras", "purchases", "Compras", "view", ("BACKOFFICE",), False),
    (
        "purchases.manage",
        "Gestionar Compras",
        "purchases",
        "Compras",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    (
        "purchases.confirm",
        "Confirmar Compras",
        "purchases",
        "Compras",
        "confirm",
        ("BACKOFFICE",),
        True,
    ),
    (
        "purchases.receive",
        "Recibir Compras",
        "purchases",
        "Compras",
        "receive",
        ("BACKOFFICE",),
        True,
    ),
    (
        "purchases.cancel",
        "Cancelar Compras",
        "purchases",
        "Compras",
        "cancel",
        ("BACKOFFICE",),
        True,
    ),
    (
        "cash_finance.view",
        "Consultar Caja y finanzas",
        "cash_finance",
        "Caja y finanzas",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "cash_finance.manage",
        "Gestionar Caja y finanzas",
        "cash_finance",
        "Caja y finanzas",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    (
        "quality_hygiene.view",
        "Consultar Calidad e higiene",
        "quality_hygiene",
        "Calidad e higiene",
        "view",
        ("BACKOFFICE",),
        False,
    ),
    (
        "quality_hygiene.manage",
        "Gestionar Calidad e higiene",
        "quality_hygiene",
        "Calidad e higiene",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    ("users.view", "Consultar Usuarios", "users", "Usuarios", "view", ("BACKOFFICE",), True),
    ("users.manage", "Gestionar Usuarios", "users", "Usuarios", "manage", ("BACKOFFICE",), True),
    ("roles.view", "Consultar Roles", "roles", "Roles", "view", ("BACKOFFICE",), True),
    ("roles.manage", "Gestionar Roles", "roles", "Roles", "manage", ("BACKOFFICE",), True),
    (
        "role_assignments.manage",
        "Gestionar Asignaciones de roles",
        "role_assignments",
        "Asignaciones de roles",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
    ("audit.view", "Consultar Auditoría", "audit", "Auditoría", "view", ("BACKOFFICE",), True),
    ("audit.export", "Exportar Auditoría", "audit", "Auditoría", "export", ("BACKOFFICE",), True),
    ("reports.view", "Consultar Reportes", "reports", "Reportes", "view", ("BACKOFFICE",), False),
    ("reports.export", "Exportar Reportes", "reports", "Reportes", "export", ("BACKOFFICE",), True),
    (
        "config.view",
        "Consultar Configuración",
        "config",
        "Configuración",
        "view",
        ("BACKOFFICE",),
        True,
    ),
    (
        "config.manage",
        "Gestionar Configuración",
        "config",
        "Configuración",
        "manage",
        ("BACKOFFICE",),
        True,
    ),
)


def upgrade() -> None:
    op.add_column("user_role_assignments", sa.Column("scope_type", sa.String(20), nullable=True))
    op.create_table(
        "user_role_assignment_branch_scopes",
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["user_role_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("assignment_id", "branch_id"),
    )
    op.execute("""
        INSERT INTO user_role_assignment_branch_scopes (assignment_id, branch_id)
        SELECT ura.id, uba.branch_id FROM user_role_assignments ura
        JOIN user_branch_assignments uba ON uba.user_id = ura.user_id AND uba.is_active
    """)
    # Keep the original assignment in audit evidence before revoking an unscopable grant.
    op.execute("""
        INSERT INTO audit_log
            (id, occurred_at, actor_id, action, resource_type, resource_id, branch_id,
             request_id, metadata)
        SELECT gen_random_uuid(), now(), NULL, 'identity.scope_migration.revoked',
               'user_role_assignment', ura.id::text, NULL, NULL,
               jsonb_build_object('source_revision', '20260520_0039_system_settings',
                   'reason', 'NO_ACTIVE_BRANCH_ASSIGNMENT', 'requires_review', true,
                   'assignment', to_jsonb(ura))
        FROM user_role_assignments ura
        WHERE NOT EXISTS (SELECT 1 FROM user_role_assignment_branch_scopes bs
                          WHERE bs.assignment_id = ura.id)
    """)
    op.execute("""
        DELETE FROM user_role_assignments ura
        WHERE NOT EXISTS (SELECT 1 FROM user_role_assignment_branch_scopes bs
                          WHERE bs.assignment_id = ura.id)
    """)
    op.execute("UPDATE user_role_assignments SET scope_type = 'BRANCH_SET'")
    op.alter_column("user_role_assignments", "scope_type", nullable=False)
    op.create_check_constraint(
        "ck_role_assignment_scope",
        "user_role_assignments",
        "scope_type IN ('GLOBAL', 'BRANCH_SET')",
    )
    canonical_codes = [item[0] for item in CAPABILITIES]
    connection = op.get_bind()
    obsolete_roles = connection.execute(
        sa.text("""
        SELECT DISTINCT r.id FROM roles r
        JOIN role_permissions rp ON rp.role_id = r.id
        JOIN permissions p ON p.id = rp.permission_id
        WHERE p.code NOT IN :codes
    """).bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": canonical_codes},
    ).scalars()
    for role_id in list(obsolete_roles):
        connection.execute(
            sa.text("""
            INSERT INTO audit_log
                (id, occurred_at, action, resource_type, resource_id, metadata)
            SELECT gen_random_uuid(), now(), 'identity.catalog_migration.review_required',
                   'role', r.id::text,
                   jsonb_build_object('reason', 'AMBIGUOUS_RETIRED_CAPABILITY',
                       'requires_review', true, 'role', to_jsonb(r),
                       'previous_permission_codes', (SELECT jsonb_agg(p.code ORDER BY p.code)
                           FROM role_permissions rp JOIN permissions p ON p.id=rp.permission_id
                           WHERE rp.role_id=r.id))
            FROM roles r WHERE r.id=:role_id
        """),
            {"role_id": role_id},
        )
        connection.execute(
            sa.text("UPDATE roles SET is_active=false WHERE id=:id"), {"id": role_id}
        )
    connection.execute(
        sa.text("DELETE FROM permissions WHERE code NOT IN :codes").bindparams(
            sa.bindparam("codes", expanding=True),
        ),
        {"codes": canonical_codes},
    )
    for code, label, module, module_label, action, surface, sensitive in CAPABILITIES:
        connection.execute(
            sa.text("""
            INSERT INTO permissions (id, code, label, description, module, module_label, action,
                                     surfaces, is_sensitive, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), :code, :label, :description, :module, :module_label,
                    :action, CAST(:surfaces AS jsonb),
                    :sensitive, true, now(), now())
            ON CONFLICT (code) DO UPDATE SET label=EXCLUDED.label, description=EXCLUDED.description,
                module=EXCLUDED.module, module_label=EXCLUDED.module_label, action=EXCLUDED.action,
                surfaces=EXCLUDED.surfaces, is_sensitive=EXCLUDED.is_sensitive, updated_at=now()
        """),
            {
                "code": code,
                "label": label,
                "description": f"{label} dentro del alcance autorizado.",
                "module": module,
                "module_label": module_label,
                "action": action,
                "surfaces": json.dumps(surface),
                "sensitive": sensitive,
            },
        )
    op.execute("""
        INSERT INTO outbox_events
            (id, aggregate_type, aggregate_id, event_name, payload, headers,
             occurred_at, available_at, status, attempts)
        SELECT gen_random_uuid(), resource_type, resource_id,
               'identity.authorization_migration.review_required.v1', metadata,
               '{"migration":"20260912_0040_authorization_scopes"}'::jsonb,
               occurred_at, occurred_at, 'pending', 0
        FROM audit_log WHERE action IN ('identity.scope_migration.revoked',
                                       'identity.catalog_migration.review_required')
    """)
    _create_privilege_tables()
    _create_scope_constraints()


def _create_privilege_tables() -> None:
    op.create_table(
        "identity_privilege_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initial_owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_provisioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_identity_privilege_state_singleton"),
        sa.ForeignKeyConstraint(["initial_owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO identity_privilege_state (id) VALUES (1)")
    op.create_table(
        "identity_privileged_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_role_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("initiator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "approver_user_id IS NULL OR approver_user_id <> initiator_user_id",
            name="ck_identity_privileged_changes_distinct_approver",
        ),
        sa.CheckConstraint("expires_at > created_at", name="ck_identity_privileged_changes_expiry"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["initiator_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "identity_recovery_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_sha256", sa.String(64), nullable=False),
        sa.Column("authorized_host", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_sha256", name="uq_identity_recovery_credentials_token_sha256"),
    )


def _create_scope_constraints() -> None:
    op.execute("""
        CREATE FUNCTION check_role_assignment_scope() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE assignment_uuid uuid; assignment_uuids uuid[];
                assignment_scope text; branch_count integer;
        BEGIN
            IF TG_TABLE_NAME = 'user_role_assignments' THEN
                assignment_uuids := ARRAY[NEW.id, OLD.id];
            ELSE
                assignment_uuids := ARRAY[NEW.assignment_id, OLD.assignment_id];
            END IF;
            FOR assignment_uuid IN SELECT DISTINCT unnest(assignment_uuids) LOOP
                SELECT scope_type INTO assignment_scope FROM user_role_assignments
                    WHERE id = assignment_uuid FOR UPDATE;
                IF NOT FOUND THEN CONTINUE; END IF;
                SELECT count(*) INTO branch_count FROM user_role_assignment_branch_scopes
                    WHERE assignment_id = assignment_uuid;
                IF (assignment_scope = 'GLOBAL' AND branch_count <> 0)
                    OR (assignment_scope = 'BRANCH_SET' AND branch_count = 0) THEN
                    RAISE EXCEPTION 'Invalid role assignment branch scope'
                        USING ERRCODE = '23514',
                              CONSTRAINT = 'ck_role_assignment_branch_cardinality';
                END IF;
            END LOOP;
            RETURN NULL;
        END $$
    """)
    for table in ("user_role_assignments", "user_role_assignment_branch_scopes"):
        op.execute(f"""
            CREATE CONSTRAINT TRIGGER validate_assignment_scope
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION check_role_assignment_scope()
        """)


def downgrade() -> None:
    # Restore is required: downgrading would discard explicit authority and durable approvals.
    raise RuntimeError("Authorization scopes require roll-forward or a verified database restore.")
