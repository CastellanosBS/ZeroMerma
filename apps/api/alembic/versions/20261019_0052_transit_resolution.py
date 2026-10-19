"""Record immutable physical resolutions of outstanding transfer quantities."""

import sqlalchemy as sa
from alembic import op

revision = "20261019_0052_transit_resolution"
down_revision = "20261019_0051_inv_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transfer_transit_resolutions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "shipment_id",
            sa.UUID(),
            sa.ForeignKey("operation_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.UUID(),
            sa.ForeignKey("branches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "origin_branch_id",
            sa.UUID(),
            sa.ForeignKey("branches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "destination_branch_id",
            sa.UUID(),
            sa.ForeignKey("branches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "idempotency_record_id",
            sa.UUID(),
            sa.ForeignKey("idempotency_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("destination_location", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column(
            "actor_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "workstation_id",
            sa.UUID(),
            sa.ForeignKey("workstations.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "cash_session_id",
            sa.UUID(),
            sa.ForeignKey("cash_sessions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('RETURN_TO_ORIGIN', 'SEND_TO_WASTE')", name="kind_valid"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="reason_required"),
        sa.CheckConstraint("origin_branch_id <> destination_branch_id", name="branches_distinct"),
        sa.CheckConstraint(
            "(kind = 'RETURN_TO_ORIGIN' AND destination_location IN ('BACKROOM','QUARANTINE')) OR "
            "(kind = 'SEND_TO_WASTE' AND destination_location = 'WASTE')",
            name="destination_valid",
        ),
        sa.CheckConstraint(
            "(kind = 'RETURN_TO_ORIGIN' AND branch_id = origin_branch_id) OR "
            "(kind = 'SEND_TO_WASTE' AND branch_id = destination_branch_id)",
            name="physical_branch_valid",
        ),
        sa.UniqueConstraint("idempotency_record_id", name="uq_transfer_resolution_command"),
    )
    op.create_index(
        "ix_transfer_transit_resolutions_shipment_id",
        "transfer_transit_resolutions",
        ["shipment_id"],
    )
    op.create_table(
        "transfer_transit_resolution_lines",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "resolution_id",
            sa.UUID(),
            sa.ForeignKey("transfer_transit_resolutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "shipment_line_id",
            sa.UUID(),
            sa.ForeignKey("operation_document_lines.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.UUID(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_of_measure", sa.String(32), nullable=False),
        sa.CheckConstraint("quantity > 0", name="quantity_positive"),
        sa.UniqueConstraint(
            "resolution_id", "shipment_line_id", name="uq_transfer_resolution_line"
        ),
    )
    op.create_index(
        "ix_transfer_transit_resolution_lines_resolution_id",
        "transfer_transit_resolution_lines",
        ["resolution_id"],
    )
    op.execute("""
        CREATE FUNCTION reject_transfer_resolution_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Committed transfer resolutions are immutable';
        END $$;
        CREATE TRIGGER transfer_resolution_immutable BEFORE UPDATE OR DELETE
          ON transfer_transit_resolutions FOR EACH ROW
          EXECUTE FUNCTION reject_transfer_resolution_mutation();
        CREATE TRIGGER transfer_resolution_line_immutable BEFORE UPDATE OR DELETE
          ON transfer_transit_resolution_lines FOR EACH ROW
          EXECUTE FUNCTION reject_transfer_resolution_mutation();
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM transfer_transit_resolutions) THEN
            RAISE EXCEPTION 'Transfer evidence requires forward correction or verified restore';
          END IF;
        END $$;
    """)
    op.drop_table("transfer_transit_resolution_lines")
    op.drop_table("transfer_transit_resolutions")
    op.execute("DROP FUNCTION reject_transfer_resolution_mutation()")
