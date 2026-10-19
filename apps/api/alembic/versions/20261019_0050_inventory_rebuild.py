"""Preserve inventory count authority and resumable reconciliation evidence."""

from alembic import op

revision = "20261019_0050_inventory_rebuild"
down_revision = "20261019_0049_inventory_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""

CREATE TABLE inventory_reconciliation_manifests (
	id UUID NOT NULL,
	branch_id UUID NOT NULL,
	manifest_sha256 VARCHAR(64) NOT NULL,
	evidence JSONB NOT NULL,
	admitted_by_user_id UUID NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	CONSTRAINT pk_inventory_reconciliation_manifests PRIMARY KEY (id),
	CONSTRAINT fk_inventory_reconciliation_manifests_branch_id_branches FOREIGN KEY(branch_id)
    REFERENCES branches (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reconciliation_manifests_admitted_by_user_id_users FOREIGN
    KEY(admitted_by_user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;

CREATE TABLE inventory_reconciliation_rows (
	id UUID NOT NULL,
	manifest_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	row_key VARCHAR(80) NOT NULL,
	row_sha256 VARCHAR(64) NOT NULL,
	action VARCHAR(16) NOT NULL,
	idempotency_record_id UUID NOT NULL,
	inventory_movement_id UUID,
	reconciliation JSONB NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	CONSTRAINT pk_inventory_reconciliation_rows PRIMARY KEY (id),
	CONSTRAINT uq_inventory_reconciliation_row UNIQUE (manifest_id, row_key),
	CONSTRAINT ck_inventory_reconciliation_rows_action_valid CHECK (action IN
    ('OPENING','REBUILD')),

	CONSTRAINT fk_inventory_reconciliation_rows_manifest_id_inventory__7ed1 FOREIGN KEY(manifest_id)
    REFERENCES inventory_reconciliation_manifests (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reconciliation_rows_branch_id_branches FOREIGN KEY(branch_id) REFERENCES
    branches (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reconciliation_rows_idempotency_record_id__e0a8 FOREIGN
    KEY(idempotency_record_id) REFERENCES idempotency_records (id) ON DELETE RESTRICT,
	CONSTRAINT uq_inventory_reconciliation_rows_inventory_movement_id UNIQUE
    (inventory_movement_id),

	CONSTRAINT fk_inventory_reconciliation_rows_inventory_movement_id__3aa5 FOREIGN
    KEY(inventory_movement_id) REFERENCES inventory_movements (id) ON DELETE RESTRICT
)

;
        CREATE FUNCTION protect_inventory_reconciliation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Inventory reconciliation evidence is immutable; correct forward'
            USING ERRCODE = '23514';
        END $$;
        CREATE TRIGGER inventory_reconciliation_manifest_immutable
          BEFORE UPDATE OR DELETE ON inventory_reconciliation_manifests
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_reconciliation();
        CREATE TRIGGER inventory_reconciliation_row_immutable
          BEFORE UPDATE OR DELETE ON inventory_reconciliation_rows
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_reconciliation();
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM inventory_reconciliation_manifests)
            OR EXISTS (SELECT 1 FROM inventory_reconciliation_rows) THEN
            RAISE EXCEPTION 'Inventory reconciliation requires forward correction or restore';
          END IF;
        END $$;
        DROP TABLE inventory_reconciliation_rows;
        DROP TABLE inventory_reconciliation_manifests;
        DROP FUNCTION protect_inventory_reconciliation();
    """)
