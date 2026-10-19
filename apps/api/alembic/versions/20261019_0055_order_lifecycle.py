"""Preserve explicit order policy versions and commercial commitments."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "20261019_0055_order_lifecycle"
down_revision = "20261019_0054_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_orders", sa.Column("version", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("customer_orders", sa.Column("production_commit_at", sa.DateTime(timezone=True)))
    op.add_column(
        "customer_orders", sa.Column("production_committed_at", sa.DateTime(timezone=True))
    )
    op.add_column("customer_orders", sa.Column("cancellation_responsibility", sa.String(20)))
    op.drop_constraint("ck_customer_orders_status_valid", "customer_orders", type_="check")
    op.create_check_constraint(
        "ck_customer_orders_status_valid",
        "customer_orders",
        "status IN ('PENDING', 'READY', 'DELIVERED', 'CANCELED', 'EXPIRED', 'NO_SHOW')",
    )
    op.create_table(
        "order_commitment_policies",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("branch_id", pg.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("lead_time_minutes", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("branch_id", "version", name="uq_order_commitment_policy_version"),
        sa.CheckConstraint("lead_time_minutes >= 0", name="ck_order_commitment_policy_lead_time"),
        sa.CheckConstraint("version > 0", name="ck_order_commitment_policy_version"),
    )
    op.create_table(
        "order_revisions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("branch_id", pg.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column(
            "order_id", pg.UUID(as_uuid=True), sa.ForeignKey("customer_orders.id"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "policy_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("order_commitment_policies.id"),
            nullable=False,
        ),
        sa.Column("quote_fingerprint", sa.String(64), nullable=False),
        sa.Column("snapshot", pg.JSONB(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "confirmed_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.UniqueConstraint("order_id", "version", name="uq_order_revision_version"),
    )
    op.create_table(
        "order_production_commitments",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("branch_id", pg.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column(
            "order_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("customer_orders.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "revision_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("order_revisions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
    )
    op.execute("""CREATE FUNCTION reject_order_evidence_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'Order policy, revision and commitment evidence is immutable'; END $$""")
    for table in ("order_commitment_policies", "order_revisions", "order_production_commitments"):
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_order_evidence_mutation()"
        )


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM order_revisions)
        OR EXISTS (SELECT 1 FROM order_commitment_policies)
        THEN RAISE EXCEPTION 'Restore or roll forward: order evidence cannot be discarded'; END IF;
        END $$""")
    for table in ("order_production_commitments", "order_revisions", "order_commitment_policies"):
        op.drop_table(table)
    op.execute("DROP FUNCTION reject_order_evidence_mutation()")
    op.drop_constraint("ck_customer_orders_status_valid", "customer_orders", type_="check")
    op.create_check_constraint(
        "ck_customer_orders_status_valid",
        "customer_orders",
        "status IN ('PENDING', 'READY', 'DELIVERED', 'CANCELED')",
    )
    for column in (
        "cancellation_responsibility",
        "production_committed_at",
        "production_commit_at",
        "version",
    ):
        op.drop_column("customer_orders", column)
