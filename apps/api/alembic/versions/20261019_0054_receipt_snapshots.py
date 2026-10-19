"""Persist immutable operational receipt documents without fabricating old snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261019_0054_receipts"
down_revision = "20261019_0053_purchase_prod"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receipt_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "branch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("branches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "workstation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workstations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_kind", sa.String(24), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("document_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_kind", "source_id", name="uq_receipt_source"),
        sa.CheckConstraint(
            "source_kind IN ('SALE','ORDER_PAYMENT','RETURN')", name="ck_receipt_kind"
        ),
    )
    op.execute("""CREATE FUNCTION protect_receipt_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Receipt snapshots are immutable'; END; $$""")
    op.execute("""CREATE TRIGGER receipt_snapshot_immutable BEFORE UPDATE OR DELETE
        ON receipt_snapshots FOR EACH ROW EXECUTE FUNCTION protect_receipt_snapshot()""")


def downgrade() -> None:
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM receipt_snapshots) THEN
        RAISE EXCEPTION 'Cannot discard issued receipts; restore or roll forward';
        END IF; END $$""")
    op.drop_table("receipt_snapshots")
    op.execute("DROP FUNCTION protect_receipt_snapshot()")
