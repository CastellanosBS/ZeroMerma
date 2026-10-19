"""Durable provider intents and authenticated evidence; no real adapter is enabled."""

from alembic import op

revision = "20261019_0047_payment_terminal"
down_revision = "20261019_0046_close_counts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE payment_terminal_bindings (
        id UUID NOT NULL,
        branch_id UUID NOT NULL,
        workstation_id UUID NOT NULL,
        provider_code VARCHAR(32) NOT NULL,
        environment VARCHAR(16) NOT NULL,
        account_reference VARCHAR(120) NOT NULL,
        terminal_reference VARCHAR(120) NOT NULL,
        is_active BOOLEAN NOT NULL,
        contract_evidence_id UUID NOT NULL,
        hardware_evidence_id UUID NOT NULL,
        certification_evidence_id UUID NOT NULL,
        CONSTRAINT pk_payment_terminal_bindings PRIMARY KEY (id),
        CONSTRAINT uq_payment_terminal_binding UNIQUE (provider_code, environment,
        account_reference, terminal_reference),
        CONSTRAINT ck_payment_terminal_bindings_environment_valid CHECK (environment IN
        ('SANDBOX','PRODUCTION')),
        CONSTRAINT fk_payment_terminal_bindings_branch_id_branches FOREIGN KEY(branch_id)
        REFERENCES branches (id) ON DELETE RESTRICT,
        CONSTRAINT fk_payment_terminal_bindings_workstation_id_workstations FOREIGN
        KEY(workstation_id) REFERENCES workstations (id) ON DELETE RESTRICT
    )
    """)
    op.execute("""
    CREATE TABLE external_payment_operations (
        id UUID NOT NULL,
        financial_entry_id UUID NOT NULL,
        branch_id UUID NOT NULL,
        workstation_id UUID NOT NULL,
        cash_session_id UUID NOT NULL,
        actor_id UUID NOT NULL,
        terminal_binding_id UUID NOT NULL,
        idempotency_record_id UUID NOT NULL,
        original_operation_id UUID,
        operation_type VARCHAR(16) NOT NULL,
        status VARCHAR(16) NOT NULL,
        reconciliation_status VARCHAR(16) NOT NULL,
        provider_code VARCHAR(32) NOT NULL,
        environment VARCHAR(16) NOT NULL,
        account_reference VARCHAR(120) NOT NULL,
        terminal_reference VARCHAR(120) NOT NULL,
        provider_idempotency_key UUID NOT NULL,
        provider_operation_id VARCHAR(120),
        amount NUMERIC(12, 2) NOT NULL,
        currency_code VARCHAR(3) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        CONSTRAINT pk_external_payment_operations PRIMARY KEY (id),
        CONSTRAINT uq_external_payment_entry UNIQUE (financial_entry_id),
        CONSTRAINT uq_external_provider_key UNIQUE (provider_code, environment,
        account_reference, provider_idempotency_key),
        CONSTRAINT uq_external_provider_operation UNIQUE (provider_code, environment,
        account_reference, provider_operation_id),
        CONSTRAINT ck_external_payment_operations_amount_valid CHECK (amount > 0 AND amount <>
        'NaN'::numeric AND currency_code = 'MXN'),
        CONSTRAINT ck_external_payment_operations_type_valid CHECK (operation_type IN
        ('CAPTURE','REFUND')),
        CONSTRAINT ck_external_payment_operations_status_valid CHECK (status IN
        ('CREATED','PROCESSING','AUTHORIZED','UNKNOWN','CAPTURED','REFUNDED','DECLINED','FAILED')),
        CONSTRAINT ck_external_payment_operations_reconciliation_valid CHECK
        (reconciliation_status IN ('PENDING','MATCHED','DISCREPANCY')),
        CONSTRAINT ck_external_payment_operations_original_valid CHECK ((operation_type =
        'REFUND') = (original_operation_id IS NOT NULL)),
        CONSTRAINT fk_external_payment_operations_financial_entry_id_finan_e5fe FOREIGN
        KEY(financial_entry_id) REFERENCES financial_entries (id) ON DELETE RESTRICT,
        CONSTRAINT fk_external_payment_operations_branch_id_branches FOREIGN KEY(branch_id)
        REFERENCES branches (id) ON DELETE RESTRICT,
        CONSTRAINT fk_external_payment_operations_workstation_id_workstations FOREIGN
        KEY(workstation_id) REFERENCES workstations (id) ON DELETE RESTRICT,
        CONSTRAINT fk_external_payment_operations_cash_session_id_cash_sessions FOREIGN
        KEY(cash_session_id) REFERENCES cash_sessions (id) ON DELETE RESTRICT,
        CONSTRAINT fk_external_payment_operations_actor_id_users FOREIGN KEY(actor_id)
        REFERENCES users (id) ON DELETE RESTRICT,
        CONSTRAINT fk_external_payment_operations_terminal_binding_id_paym_dc9a FOREIGN
        KEY(terminal_binding_id) REFERENCES payment_terminal_bindings (id) ON DELETE RESTRICT,
        CONSTRAINT fk_external_payment_operations_idempotency_record_id_id_6ded FOREIGN
        KEY(idempotency_record_id) REFERENCES idempotency_records (id) ON DELETE RESTRICT,
        CONSTRAINT fk_external_payment_operations_original_operation_id_ex_90b2 FOREIGN
        KEY(original_operation_id) REFERENCES external_payment_operations (id) ON DELETE
        RESTRICT
    )
    """)
    op.execute("""
    CREATE TABLE external_payment_evidence (
        id UUID NOT NULL,
        external_operation_id UUID NOT NULL,
        branch_id UUID NOT NULL,
        provider_code VARCHAR(32) NOT NULL,
        environment VARCHAR(16) NOT NULL,
        account_reference VARCHAR(120) NOT NULL,
        event_id VARCHAR(120) NOT NULL,
        state VARCHAR(16) NOT NULL,
        fingerprint VARCHAR(64) NOT NULL,
        occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
        recorded_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
        CONSTRAINT pk_external_payment_evidence PRIMARY KEY (id),
        CONSTRAINT uq_external_provider_event UNIQUE (provider_code, environment,
        account_reference, event_id),
        CONSTRAINT fk_external_payment_evidence_external_operation_id_exte_b473 FOREIGN
        KEY(external_operation_id) REFERENCES external_payment_operations (id) ON DELETE
        RESTRICT,
        CONSTRAINT fk_external_payment_evidence_branch_id_branches FOREIGN KEY(branch_id)
        REFERENCES branches (id) ON DELETE RESTRICT
    )
    """)
    op.execute("""

    CREATE FUNCTION protect_external_payment_evidence() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION 'Provider evidence is append-only' USING ERRCODE = '23514';
    END;
    $$ LANGUAGE plpgsql;
    CREATE TRIGGER external_payment_evidence_immutable BEFORE UPDATE OR DELETE
      ON external_payment_evidence FOR EACH ROW EXECUTE FUNCTION
        protect_external_payment_evidence();
    CREATE FUNCTION protect_external_payment_operation() RETURNS trigger AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Provider operations cannot be deleted' USING ERRCODE = '23514';
      END IF;
      IF (to_jsonb(NEW) -
        ARRAY['status','reconciliation_status','provider_operation_id','updated_at'])
         IS DISTINCT FROM
         (to_jsonb(OLD) -
        ARRAY['status','reconciliation_status','provider_operation_id','updated_at'])
         OR (OLD.provider_operation_id IS NOT NULL AND
             NEW.provider_operation_id IS DISTINCT FROM OLD.provider_operation_id)
         OR (OLD.status IN ('CAPTURED','REFUNDED','DECLINED','FAILED') AND
             NEW.status IS DISTINCT FROM OLD.status) THEN
        RAISE EXCEPTION 'Provider operation identity or terminal result is immutable'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    CREATE TRIGGER external_payment_operation_immutable BEFORE UPDATE OR DELETE
      ON external_payment_operations FOR EACH ROW EXECUTE FUNCTION
        protect_external_payment_operation();
    CREATE FUNCTION protect_payment_terminal_binding() RETURNS trigger AS $$
    BEGIN
      IF (to_jsonb(NEW) - 'is_active') IS DISTINCT FROM (to_jsonb(OLD) - 'is_active') THEN
        RAISE EXCEPTION 'Replace terminal bindings instead of rewriting their identity'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    CREATE TRIGGER payment_terminal_binding_immutable BEFORE UPDATE
      ON payment_terminal_bindings FOR EACH ROW EXECUTE FUNCTION protect_payment_terminal_binding();

    """)


def downgrade() -> None:
    op.execute("""

    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM external_payment_operations) THEN
        RAISE EXCEPTION 'Restore a verified backup; provider evidence cannot be discarded';
      END IF;
    END $$;
    DROP TABLE external_payment_evidence;
    DROP TABLE external_payment_operations;
    DROP TABLE payment_terminal_bindings;
    DROP FUNCTION protect_external_payment_evidence();
    DROP FUNCTION protect_external_payment_operation();
    DROP FUNCTION protect_payment_terminal_binding();

    """)
