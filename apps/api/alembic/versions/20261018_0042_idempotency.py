"""Add durable globally unique command identities without importing request history.

Revision ID: 20261018_0042_idempotency
Revises: 20261018_0041_auth_sessions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261018_0042_idempotency"
down_revision: str | None = "20261018_0041_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_code", sa.String(120), nullable=False),
        sa.Column("fingerprint_version", sa.Integer(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("branches.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "workstation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workstations.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "cash_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cash_sessions.id", ondelete="RESTRICT"),
        ),
        sa.Column("context_data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resource_type", sa.String(120)),
        sa.Column("resource_id", sa.String(160)),
        sa.Column("response_status", sa.Integer()),
        sa.Column("response_schema_version", sa.String(40)),
        sa.Column("response_fingerprint", sa.String(64)),
        sa.Column("response_reference", postgresql.JSONB(none_as_null=True)),
        sa.Column("response_payload", postgresql.JSONB(none_as_null=True)),
        sa.Column("error_code", sa.String(120)),
        sa.Column("first_request_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("response_expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("idempotency_key", name="uq_idempotency_records_key"),
        sa.CheckConstraint(
            "idempotency_key::text ~ "
            "'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'",
            name="idempotency_key_uuid7",
        ),
        sa.CheckConstraint(
            "status IN ('PROCESSING','COMPLETED','REJECTED','UNKNOWN')",
            name="idempotency_status_valid",
        ),
        sa.CheckConstraint(
            "fingerprint_version > 0", name="idempotency_fingerprint_version_positive"
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="idempotency_fingerprint_format"
        ),
        sa.CheckConstraint(
            "response_status IS NULL OR response_status BETWEEN 100 AND 599",
            name="idempotency_response_status_valid",
        ),
        sa.CheckConstraint(
            "response_fingerprint IS NULL OR response_fingerprint ~ '^[0-9a-f]{64}$'",
            name="idempotency_response_fingerprint_format",
        ),
        sa.CheckConstraint(
            "response_payload IS NULL OR jsonb_typeof(response_payload) = 'object'",
            name="idempotency_response_payload_object",
        ),
        sa.CheckConstraint(
            "response_reference IS NULL OR jsonb_typeof(response_reference) = 'object'",
            name="idempotency_response_reference_object",
        ),
        sa.CheckConstraint(
            "status NOT IN ('COMPLETED','REJECTED') OR "
            "(completed_at IS NOT NULL AND response_status IS NOT NULL "
            "AND response_schema_version IS NOT NULL AND response_fingerprint IS NOT NULL "
            "AND (response_payload IS NOT NULL OR response_reference IS NOT NULL))",
            name="idempotency_terminal_result",
        ),
    )
    op.create_index(
        "ix_idempotency_records_response_expiry",
        "idempotency_records",
        ["response_expires_at"],
        postgresql_where=sa.text(
            "response_payload IS NOT NULL AND response_expires_at IS NOT NULL"
        ),
    )
    op.execute("""
    CREATE FUNCTION protect_idempotency_identity() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'Idempotency identities cannot be deleted' USING ERRCODE='23514';
      END IF;
      IF (NEW.id,NEW.idempotency_key,NEW.operation_code,NEW.fingerprint_version,
          NEW.request_fingerprint,NEW.actor_user_id,NEW.branch_id,NEW.workstation_id,
          NEW.cash_session_id,NEW.context_data,NEW.first_request_id,NEW.created_at)
         IS DISTINCT FROM
         (OLD.id,OLD.idempotency_key,OLD.operation_code,OLD.fingerprint_version,
          OLD.request_fingerprint,OLD.actor_user_id,OLD.branch_id,OLD.workstation_id,
          OLD.cash_session_id,OLD.context_data,OLD.first_request_id,OLD.created_at) THEN
        RAISE EXCEPTION 'Idempotency identity and context are immutable' USING ERRCODE='23514';
      END IF;
      IF OLD.status IN ('COMPLETED','REJECTED') AND NEW IS DISTINCT FROM OLD THEN
        IF (to_jsonb(NEW) - ARRAY['response_payload','updated_at'])
             IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['response_payload','updated_at'])
           OR OLD.response_payload IS NULL OR NEW.response_payload IS NOT NULL
           OR OLD.response_reference IS NULL OR OLD.response_expires_at IS NULL
           OR OLD.response_expires_at > clock_timestamp() THEN
          RAISE EXCEPTION 'Terminal idempotency results are immutable except expired payload purge'
            USING ERRCODE='23514';
        END IF;
        NEW.updated_at := clock_timestamp();
      END IF;
      IF OLD.status='UNKNOWN' AND NEW.status='PROCESSING' THEN
        RAISE EXCEPTION 'Unknown outcome requires reconciliation, not re-execution'
          USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER idempotency_identity_protection BEFORE UPDATE OR DELETE
      ON idempotency_records FOR EACH ROW EXECUTE FUNCTION protect_idempotency_identity();

    CREATE FUNCTION require_terminal_internal_idempotency() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM idempotency_records WHERE id=NEW.id AND status='PROCESSING') THEN
        RAISE EXCEPTION 'Internal idempotency reservation cannot commit while processing'
          USING ERRCODE='23514';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER idempotency_no_durable_processing
      AFTER INSERT OR UPDATE ON idempotency_records DEFERRABLE INITIALLY DEFERRED
      FOR EACH ROW EXECUTE FUNCTION require_terminal_internal_idempotency();
    """)


def downgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM idempotency_records) THEN
        RAISE EXCEPTION 'A populated idempotency store requires roll-forward or consistent restore';
      END IF;
    END $$;
    """)
    op.drop_index("ix_idempotency_records_response_expiry", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.execute("DROP FUNCTION require_terminal_internal_idempotency()")
    op.execute("DROP FUNCTION protect_idempotency_identity()")
