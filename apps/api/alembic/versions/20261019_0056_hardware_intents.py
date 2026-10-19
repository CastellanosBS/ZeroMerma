"""Keep local device authority causal and separate from economic commands."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "20261019_0056_hardware"
down_revision = "20261019_0055_order_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hardware_device_bindings",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "branch_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("branches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "workstation_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("workstations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("adapter_code", sa.String(64), nullable=False),
        sa.Column("adapter_version", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("origin", sa.String(200), nullable=False),
        sa.Column("certification_evidence_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("kind IN ('PRINTER','DRAWER')", name="ck_hardware_binding_kind"),
        sa.CheckConstraint(
            "environment IN ('SANDBOX','PRODUCTION')", name="ck_hardware_environment"
        ),
        sa.CheckConstraint("version > 0", name="ck_hardware_binding_version"),
    )
    op.create_table(
        "hardware_command_intents",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "branch_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("branches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "workstation_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("workstations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "binding_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("hardware_device_bindings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cash_entry_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("financial_entries.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("command", pg.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("""CREATE FUNCTION protect_hardware_intent() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Hardware command intents are immutable'; END; $$""")
    op.execute("""CREATE TRIGGER hardware_intent_immutable BEFORE UPDATE OR DELETE
        ON hardware_command_intents FOR EACH ROW EXECUTE FUNCTION protect_hardware_intent()""")


def downgrade() -> None:
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM hardware_command_intents) THEN
        RAISE EXCEPTION 'Cannot discard physical command identities'; END IF; END $$""")
    op.drop_table("hardware_command_intents")
    op.drop_table("hardware_device_bindings")
    op.execute("DROP FUNCTION protect_hardware_intent()")
