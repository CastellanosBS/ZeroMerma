"""Persist opaque sessions and transactional security revocation.

Revision ID: 20261018_0041_auth_sessions
Revises: 20260912_0040_authorization
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261018_0041_auth_sessions"
down_revision: str | None = "20260912_0040_authorization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("credential_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("audience", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(80)),
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
        sa.CheckConstraint("audience IN ('POS','BACKOFFICE')", name="auth_session_audience"),
        sa.CheckConstraint(
            "status IN ('ACTIVE','LOCKED','REVOKED','EXPIRED')", name="auth_session_status"
        ),
        sa.CheckConstraint(
            "(audience='POS' AND workstation_id IS NOT NULL) OR "
            "(audience='BACKOFFICE' AND workstation_id IS NULL AND cash_session_id IS NULL)",
            name="auth_session_binding",
        ),
        sa.CheckConstraint("idle_expires_at <= absolute_expires_at", name="auth_session_expiry"),
    )
    op.create_index(
        "uq_auth_sessions_pos_slot",
        "auth_sessions",
        ["user_id", "workstation_id"],
        unique=True,
        postgresql_where=sa.text("audience='POS' AND status IN ('ACTIVE','LOCKED')"),
    )
    op.create_index("ix_auth_sessions_user_status", "auth_sessions", ["user_id", "status"])
    op.create_table(
        "auth_login_limits",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "password_reset_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credential_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
    )
    op.execute("""
    CREATE FUNCTION audit_auth_session_state() RETURNS trigger LANGUAGE plpgsql AS $$
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
    CREATE TRIGGER auth_session_state_audit AFTER INSERT OR UPDATE OF status ON auth_sessions
      FOR EACH ROW EXECUTE FUNCTION audit_auth_session_state();
    CREATE FUNCTION revoke_user_auth_sessions(target uuid, reason text) RETURNS void
      LANGUAGE sql AS $$ UPDATE auth_sessions SET status='REVOKED', revoked_at=clock_timestamp(),
        revocation_reason=reason WHERE user_id=target AND status IN ('ACTIVE','LOCKED') $$;
    CREATE FUNCTION revoke_identity_auth_sessions() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE before_row jsonb; after_row jsonb; affected uuid; role_ids uuid[]; user_ids uuid[];
    BEGIN
      IF TG_OP<>'INSERT' THEN before_row := to_jsonb(OLD); END IF;
      IF TG_OP<>'DELETE' THEN after_row := to_jsonb(NEW); END IF;
      IF TG_TABLE_NAME='users' THEN
        IF (before_row->'password_hash',before_row->'is_active',before_row->'is_locked',
          before_row->'allowed_surfaces',before_row->'password_reset_required',before_row->'email')
          IS NOT DISTINCT FROM (after_row->'password_hash',after_row->'is_active',
          after_row->'is_locked',
          after_row->'allowed_surfaces',after_row->'password_reset_required',after_row->'email')
          THEN RETURN NEW; END IF;
        user_ids := ARRAY[(after_row->>'id')::uuid];
        IF before_row->'password_hash' IS DISTINCT FROM after_row->'password_hash' THEN
          UPDATE password_reset_credentials SET consumed_at=clock_timestamp()
            WHERE user_id=(after_row->>'id')::uuid AND consumed_at IS NULL;
        END IF;
      ELSIF TG_TABLE_NAME IN ('user_branch_assignments','user_role_assignments') THEN
        user_ids := ARRAY[(before_row->>'user_id')::uuid,(after_row->>'user_id')::uuid];
      ELSIF TG_TABLE_NAME='user_role_assignment_branch_scopes' THEN
        SELECT array_agg(user_id) INTO user_ids FROM user_role_assignments WHERE id IN
          ((before_row->>'assignment_id')::uuid,(after_row->>'assignment_id')::uuid);
      ELSE
        IF TG_TABLE_NAME='roles' THEN
          role_ids := ARRAY[(before_row->>'id')::uuid,(after_row->>'id')::uuid];
        ELSIF TG_TABLE_NAME='role_permissions' THEN
          role_ids := ARRAY[(before_row->>'role_id')::uuid,(after_row->>'role_id')::uuid];
        ELSE SELECT array_agg(role_id) INTO role_ids FROM role_permissions WHERE permission_id IN
          ((before_row->>'id')::uuid,(after_row->>'id')::uuid); END IF;
        SELECT array_agg(user_id) INTO user_ids FROM user_role_assignments
          WHERE role_id=ANY(role_ids);
      END IF;
      FOR affected IN SELECT DISTINCT unnest(user_ids) LOOP
        PERFORM revoke_user_auth_sessions(affected,'AUTHORIZATION_CHANGED');
      END LOOP;
      RETURN COALESCE(NEW,OLD);
    END $$;
    CREATE TRIGGER users_revoke_auth AFTER UPDATE OF password_hash,is_active,is_locked,
      allowed_surfaces,password_reset_required,email
      ON users FOR EACH ROW EXECUTE FUNCTION revoke_identity_auth_sessions();
    CREATE TRIGGER roles_revoke_auth AFTER UPDATE OF is_active,surfaces ON roles
      FOR EACH ROW EXECUTE FUNCTION revoke_identity_auth_sessions();
    CREATE TRIGGER permissions_revoke_auth AFTER UPDATE OF is_active,surfaces,code ON permissions
      FOR EACH ROW EXECUTE FUNCTION revoke_identity_auth_sessions();
    """)
    for table in (
        "user_branch_assignments",
        "user_role_assignments",
        "user_role_assignment_branch_scopes",
        "role_permissions",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_revoke_auth AFTER INSERT OR UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION revoke_identity_auth_sessions()"
        )
    op.execute("""
    CREATE FUNCTION bind_cash_auth_sessions() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.status='OPEN' THEN
        UPDATE auth_sessions SET cash_session_id=NEW.id WHERE audience='POS'
          AND user_id=NEW.user_id AND workstation_id=NEW.workstation_id
          AND status IN ('ACTIVE','LOCKED');
      ELSIF NEW.status='CLOSED' AND OLD.status='OPEN' THEN
        UPDATE auth_sessions SET status='REVOKED',revoked_at=clock_timestamp(),
          revocation_reason='CASH_SESSION_CLOSED' WHERE audience='POS'
          AND cash_session_id=NEW.id AND status IN ('ACTIVE','LOCKED');
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER cash_sessions_bind_auth AFTER INSERT OR UPDATE OF status ON cash_sessions
      FOR EACH ROW EXECUTE FUNCTION bind_cash_auth_sessions();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER cash_sessions_bind_auth ON cash_sessions")
    op.execute("DROP FUNCTION bind_cash_auth_sessions()")
    for table in (
        "users",
        "roles",
        "permissions",
        "user_branch_assignments",
        "user_role_assignments",
        "user_role_assignment_branch_scopes",
        "role_permissions",
    ):
        op.execute(f"DROP TRIGGER {table}_revoke_auth ON {table}")
    op.execute("DROP FUNCTION revoke_identity_auth_sessions()")
    op.execute("DROP FUNCTION revoke_user_auth_sessions(uuid,text)")
    op.execute("DROP TABLE password_reset_credentials")
    op.execute("DROP TABLE auth_login_limits")
    op.execute("DROP TABLE auth_sessions")
    op.execute("DROP FUNCTION audit_auth_session_state()")
