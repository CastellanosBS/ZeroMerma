"""Immutable evidence manifests and resumable financial import progress."""

from alembic import op

revision = "20261019_0048_financial_import"
down_revision = "20261019_0047_payment_terminal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE financial_import_manifests (
          id UUID CONSTRAINT pk_financial_import_manifests PRIMARY KEY,
          branch_id UUID NOT NULL CONSTRAINT fk_financial_import_manifests_branch_id_branches
            REFERENCES branches(id) ON DELETE RESTRICT,
          manifest_sha256 VARCHAR(64) NOT NULL,
          evidence JSONB NOT NULL,
          admitted_by_user_id UUID NOT NULL
            CONSTRAINT fk_financial_import_manifests_admitted_by_user_id_users
            REFERENCES users(id) ON DELETE RESTRICT,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
        );
        CREATE TABLE financial_import_rows (
          id UUID CONSTRAINT pk_financial_import_rows PRIMARY KEY,
          manifest_id UUID NOT NULL
            CONSTRAINT fk_financial_import_rows_manifest_id_financial_import_manifests
            REFERENCES financial_import_manifests(id) ON DELETE RESTRICT,
          branch_id UUID NOT NULL CONSTRAINT fk_financial_import_rows_branch_id_branches
            REFERENCES branches(id) ON DELETE RESTRICT,
          row_key VARCHAR(80) NOT NULL,
          row_sha256 VARCHAR(64) NOT NULL,
          financial_operation_id UUID NOT NULL
            CONSTRAINT uq_financial_import_rows_financial_operation_id UNIQUE
            CONSTRAINT fk_financial_import_rows_financial_operation_id_financi_2703
            REFERENCES financial_operations(id) ON DELETE RESTRICT,
          operation_id UUID NOT NULL,
          reconciliation JSONB NOT NULL,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
          CONSTRAINT uq_financial_import_row UNIQUE (manifest_id, row_key)
        );
        CREATE FUNCTION protect_financial_import_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Financial import evidence is immutable; restore or correct forward'
            USING ERRCODE = '23514';
        END $$;
        CREATE TRIGGER financial_import_manifest_immutable
          BEFORE UPDATE OR DELETE ON financial_import_manifests
          FOR EACH ROW EXECUTE FUNCTION protect_financial_import_evidence();
        CREATE TRIGGER financial_import_row_immutable
          BEFORE UPDATE OR DELETE ON financial_import_rows
          FOR EACH ROW EXECUTE FUNCTION protect_financial_import_evidence();
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM financial_import_manifests)
            OR EXISTS (SELECT 1 FROM financial_import_rows) THEN
            RAISE EXCEPTION 'Financial import evidence requires forward correction or restore';
          END IF;
        END $$;
        DROP TABLE financial_import_rows;
        DROP TABLE financial_import_manifests;
        DROP FUNCTION protect_financial_import_evidence();
    """)
