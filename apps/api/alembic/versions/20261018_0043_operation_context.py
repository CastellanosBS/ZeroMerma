"""Persist canonical operation context without inventing historical provenance.

Revision ID: 20261018_0043_operation_context
Revises: 20261018_0042_idempotency
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261018_0043_operation_context"
down_revision: str | None = "20261018_0042_idempotency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONTEXT_CHECK = (
    "(context_version = 0 AND source_app = 'UNKNOWN' AND actor_type = 'UNKNOWN') OR "
    "(context_version = 1 AND source_app IN ('POS','BACKOFFICE','API','SYSTEM','WORKER') "
    "AND operation_id IS NOT NULL AND correlation_id IS NOT NULL "
    "AND actor_type IN ('USER','SYSTEM','ANONYMOUS'))"
)
_CONTEXT_COLUMNS = (
    "context_version",
    "source_app",
    "actor_type",
    "operation_id",
    "correlation_id",
    "causation_id",
    "idempotency_key",
    "operation_code",
    "workstation_id",
    "cash_session_id",
    "related_branch_ids",
    "recorded_at",
)


def upgrade() -> None:
    for table in ("audit_log", "outbox_events"):
        op.add_column(
            table,
            sa.Column("context_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )
        op.add_column(
            table, sa.Column("source_app", sa.String(20), nullable=False, server_default="UNKNOWN")
        )
        op.add_column(
            table, sa.Column("actor_type", sa.String(20), nullable=False, server_default="UNKNOWN")
        )
        for name in (
            "operation_id",
            "correlation_id",
            "causation_id",
            "idempotency_key",
            "workstation_id",
            "cash_session_id",
        ):
            op.add_column(table, sa.Column(name, postgresql.UUID(as_uuid=True)))
        op.add_column(table, sa.Column("operation_code", sa.String(160)))
        op.add_column(
            table,
            sa.Column(
                "related_branch_ids",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
        # PostgreSQL must not backfill a made-up recording time onto existing evidence.
        op.add_column(table, sa.Column("recorded_at", sa.DateTime(timezone=True)))
        op.alter_column(table, "recorded_at", server_default=sa.text("clock_timestamp()"))
        op.create_check_constraint(
            op.f(f"ck_{table}_operation_context_valid"), table, _CONTEXT_CHECK
        )
        op.create_check_constraint(
            op.f(f"ck_{table}_related_branches_array"),
            table,
            "jsonb_typeof(related_branch_ids) = 'array'",
        )
        for name in ("operation_id", "correlation_id"):
            op.create_index(f"ix_{table}_{name}", table, [name])
    for name in ("actor_id", "branch_id"):
        op.add_column("outbox_events", sa.Column(name, postgresql.UUID(as_uuid=True)))
    op.add_column("outbox_events", sa.Column("request_id", sa.String(120)))
    op.add_column(
        "outbox_events",
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_check_constraint(
        op.f("ck_outbox_events_schema_version_valid"),
        "outbox_events",
        "schema_version >= 0 AND (context_version = 0 OR schema_version > 0)",
    )
    op.execute("""
    CREATE OR REPLACE FUNCTION audit_auth_session_state() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE event_name text; event_payload jsonb; actor uuid; request text;
      operation uuid; correlation uuid; causation uuid; source text; actor_kind text;
      branch uuid; workstation uuid; cash_session uuid; idempotency uuid;
      operation_code text; related_branches jsonb;
    BEGIN
      IF TG_OP='INSERT' THEN event_name := 'session.created';
      ELSIF NEW.status IS NOT DISTINCT FROM OLD.status THEN RETURN NEW;
      ELSE event_name := CASE NEW.status WHEN 'LOCKED' THEN 'session.locked'
        WHEN 'ACTIVE' THEN 'session.unlocked' WHEN 'EXPIRED' THEN 'session.expired'
        ELSE 'session.revoked' END; END IF;
      actor := NULLIF(current_setting('zeromerma.actor_id', true), '')::uuid;
      request := NULLIF(current_setting('zeromerma.request_id', true), '');
      operation := NULLIF(current_setting('zeromerma.operation_id', true), '')::uuid;
      correlation := NULLIF(current_setting('zeromerma.correlation_id', true), '')::uuid;
      causation := NULLIF(current_setting('zeromerma.causation_id', true), '')::uuid;
      source := NULLIF(current_setting('zeromerma.source_app', true), '');
      branch := NULLIF(current_setting('zeromerma.branch_id', true), '')::uuid;
      workstation := NULLIF(current_setting('zeromerma.workstation_id', true), '')::uuid;
      cash_session := NULLIF(current_setting('zeromerma.cash_session_id', true), '')::uuid;
      idempotency := NULLIF(current_setting('zeromerma.idempotency_key', true), '')::uuid;
      operation_code := NULLIF(current_setting('zeromerma.operation_code', true), '');
      related_branches := COALESCE(
        NULLIF(current_setting('zeromerma.related_branch_ids', true), '')::jsonb, '[]'::jsonb);
      IF branch IS NOT NULL THEN
        SELECT COALESCE(jsonb_agg(value ORDER BY value), '[]'::jsonb) INTO related_branches
        FROM (SELECT DISTINCT value FROM jsonb_array_elements_text(
          related_branches || jsonb_build_array(branch::text))) AS branch_values;
      END IF;
      IF operation IS NULL THEN
        operation := gen_random_uuid();
        correlation := operation;
        source := 'SYSTEM';
      END IF;
      correlation := COALESCE(correlation, operation);
      source := COALESCE(source, 'SYSTEM');
      actor_kind := CASE WHEN actor IS NOT NULL THEN 'USER'
        WHEN source IN ('SYSTEM','WORKER') THEN 'SYSTEM' ELSE 'ANONYMOUS' END;
      event_payload := jsonb_build_object('session_id',NEW.id,'user_id',NEW.user_id,
        'audience',NEW.audience,'status',NEW.status,'workstation_id',NEW.workstation_id,
        'cash_session_id',NEW.cash_session_id,'reason',NEW.revocation_reason);
      INSERT INTO audit_log(id,occurred_at,actor_id,action,resource_type,resource_id,
        branch_id,request_id,metadata,context_version,source_app,actor_type,operation_id,
        correlation_id,causation_id,idempotency_key,operation_code,workstation_id,
        cash_session_id,related_branch_ids)
      VALUES(gen_random_uuid(),clock_timestamp(),actor,event_name,'auth_session',NEW.id::text,
        branch,request,event_payload,1,source,actor_kind,operation,correlation,causation,
        idempotency,operation_code,workstation,cash_session,related_branches);
      INSERT INTO outbox_events(id,aggregate_type,aggregate_id,event_name,payload,headers,
        occurred_at,available_at,status,attempts,context_version,source_app,actor_type,
        actor_id,branch_id,request_id,operation_id,correlation_id,causation_id,idempotency_key,
        operation_code,workstation_id,cash_session_id,related_branch_ids,schema_version)
      VALUES(gen_random_uuid(),'auth_session',NEW.id::text,event_name,event_payload,
        jsonb_build_object('request_id',request),clock_timestamp(),clock_timestamp(),'pending',0,
        1,source,actor_kind,actor,branch,request,operation,correlation,causation,idempotency,
        operation_code,workstation,cash_session,related_branches,1);
      RETURN NEW;
    END $$;
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM audit_log WHERE context_version=1)
         OR EXISTS (SELECT 1 FROM outbox_events WHERE context_version=1) THEN
        RAISE EXCEPTION 'Operation context evidence requires roll-forward or a verified restore';
      END IF;
    END $$;
    CREATE OR REPLACE FUNCTION audit_auth_session_state() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE event_name text; event_payload jsonb; actor uuid; request text;
    BEGIN
      IF TG_OP='INSERT' THEN event_name := 'session.created';
      ELSIF NEW.status IS NOT DISTINCT FROM OLD.status THEN RETURN NEW;
      ELSE event_name := CASE NEW.status WHEN 'LOCKED' THEN 'session.locked'
        WHEN 'ACTIVE' THEN 'session.unlocked' WHEN 'EXPIRED' THEN 'session.expired'
        ELSE 'session.revoked' END; END IF;
      actor := NULLIF(current_setting('zeromerma.actor_id', true), '')::uuid;
      request := NULLIF(current_setting('zeromerma.request_id', true), '');
      event_payload := jsonb_build_object('session_id',NEW.id,'user_id',NEW.user_id,
        'audience',NEW.audience,'status',NEW.status,'workstation_id',NEW.workstation_id,
        'cash_session_id',NEW.cash_session_id,'reason',NEW.revocation_reason);
      INSERT INTO audit_log(id,occurred_at,actor_id,action,resource_type,resource_id,
        branch_id,request_id,metadata) VALUES(gen_random_uuid(),clock_timestamp(),actor,
        event_name,'auth_session',NEW.id::text,NULL,request,event_payload);
      INSERT INTO outbox_events(id,aggregate_type,aggregate_id,event_name,payload,headers,
        occurred_at,available_at,status,attempts) VALUES(gen_random_uuid(),'auth_session',
        NEW.id::text,event_name,event_payload,jsonb_build_object('request_id',request),
        clock_timestamp(),clock_timestamp(),'pending',0);
      RETURN NEW;
    END $$;
    """)
    op.drop_constraint(
        op.f("ck_outbox_events_schema_version_valid"), "outbox_events", type_="check"
    )
    for name in ("actor_id", "branch_id", "request_id", "schema_version"):
        op.drop_column("outbox_events", name)
    for table in ("audit_log", "outbox_events"):
        op.drop_constraint(op.f(f"ck_{table}_operation_context_valid"), table, type_="check")
        op.drop_constraint(op.f(f"ck_{table}_related_branches_array"), table, type_="check")
        for name in ("operation_id", "correlation_id"):
            op.drop_index(f"ix_{table}_{name}", table_name=table)
        for name in reversed(_CONTEXT_COLUMNS):
            op.drop_column(table, name)
