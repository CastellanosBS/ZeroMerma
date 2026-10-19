"""Create an empty canonical financial foundation; no historical adoption or backfill.

Revision ID: 20261019_0044_financial_ledger
Revises: 20261018_0043_operation_context
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261019_0044_financial_ledger"
down_revision: str | None = "20261018_0043_operation_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE financial_operations (
        id UUID NOT NULL,
        kind VARCHAR(40) NOT NULL,
        source_type VARCHAR(40) NOT NULL,
        source_id UUID NOT NULL,
        effect_code VARCHAR(40) NOT NULL,
        subject_type VARCHAR(32) NOT NULL,
        subject_id UUID NOT NULL,
        amount_due NUMERIC(12, 2) NOT NULL,
        opening_obligation_kind VARCHAR(32),
        opening_reason_code VARCHAR(64),
        source_evidence_reference UUID,
        cutover_at TIMESTAMP WITH TIME ZONE,
        related_operation_id UUID,
        relation_kind VARCHAR(24),
        branch_id UUID NOT NULL,
        workstation_id UUID,
        cash_session_id UUID,
        actor_id UUID,
        currency_code VARCHAR(3) NOT NULL,
        context_version INTEGER NOT NULL,
        source_app VARCHAR(20) NOT NULL,
        actor_type VARCHAR(20) NOT NULL,
        operation_id UUID NOT NULL,
        operation_code VARCHAR(160),
        correlation_id UUID NOT NULL,
        causation_id UUID,
        request_id VARCHAR(120),
        idempotency_key UUID,
        related_branch_ids JSONB DEFAULT '[]'::jsonb NOT NULL,
        occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
        recorded_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
        CONSTRAINT pk_financial_operations PRIMARY KEY (id),
        CONSTRAINT uq_financial_cause UNIQUE (source_type, source_id, effect_code),
        CONSTRAINT ck_financial_operations_context_valid CHECK (context_version = 1 AND
        operation_id IS NOT NULL AND correlation_id IS NOT NULL AND source_app IN
        ('POS','BACKOFFICE','API','SYSTEM','WORKER') AND ((actor_id IS NOT NULL AND actor_type
        = 'USER') OR (actor_id IS NULL AND actor_type = 'SYSTEM' AND source_app IN
        ('SYSTEM','WORKER')))),
        CONSTRAINT ck_financial_operations_currency_valid CHECK (currency_code = 'MXN'),
        CONSTRAINT ck_financial_operations_branches_array CHECK
        (jsonb_typeof(related_branch_ids) = 'array'),
        CONSTRAINT ck_financial_operations_amount_valid CHECK (amount_due >= 0 AND amount_due
        <> 'NaN'::numeric),
        CONSTRAINT ck_financial_operations_source_valid CHECK (effect_code = kind AND ((kind =
        'CASH_OPENING' AND source_type IN ('CASH_SESSION','OPENING_STATE')) OR (kind =
        'SALE_COLLECTION' AND source_type = 'SALE') OR (kind IN
        ('ORDER_ADVANCE','ORDER_SETTLEMENT','ORDER_REFUND') AND source_type = 'ORDER_PAYMENT')
        OR (kind = 'SALE_REFUND' AND source_type = 'SALE_RETURN') OR (kind =
        'OPERATIONAL_PAYMENT' AND source_type = 'OPERATIONAL_PAYMENT') OR (kind =
        'OPERATIONAL_CHARGE' AND source_type = 'OPERATIONAL_DISCOUNT') OR (kind =
        'CASH_DEPOSIT' AND source_type = 'CASH_DEPOSIT') OR (kind = 'CASH_WITHDRAWAL' AND
        source_type = 'CASH_WITHDRAWAL') OR (kind = 'TECHNICAL_REVERSAL' AND source_type =
        'FINANCIAL_ENTRY') OR (kind = 'OPENING_OBLIGATION' AND source_type =
        'OPENING_STATE'))),
        CONSTRAINT ck_financial_operations_opening_valid CHECK ((((source_type =
        'OPENING_STATE' AND opening_reason_code IS NOT NULL AND
        length(btrim(opening_reason_code)) > 0 AND source_evidence_reference IS NOT NULL AND
        cutover_at IS NOT NULL) OR (source_type <> 'OPENING_STATE' AND opening_reason_code IS
        NULL AND source_evidence_reference IS NULL AND cutover_at IS NULL)) AND ((kind =
        'OPENING_OBLIGATION' AND opening_obligation_kind IN
        ('RECEIVABLE','PAYABLE','CUSTOMER_ADVANCE') AND cash_session_id IS NULL AND
        workstation_id IS NULL) OR (kind <> 'OPENING_OBLIGATION' AND opening_obligation_kind
        IS NULL)) AND (kind <> 'CASH_OPENING' OR cash_session_id IS NOT NULL) AND (source_type
        <> 'CASH_SESSION' OR source_id = cash_session_id)) IS TRUE),
        CONSTRAINT ck_financial_operations_relation_valid CHECK (((kind IN
        ('SALE_REFUND','ORDER_REFUND') AND ((relation_kind = 'REFUND_OF' AND
        related_operation_id IS NOT NULL) OR (relation_kind IS NULL AND related_operation_id
        IS NULL))) OR (kind = 'TECHNICAL_REVERSAL' AND relation_kind = 'REVERSAL_OF' AND
        related_operation_id IS NOT NULL) OR (kind = 'ORDER_SETTLEMENT' AND ((relation_kind =
        'SETTLEMENT_OF' AND related_operation_id IS NOT NULL) OR (relation_kind IS NULL AND
        related_operation_id IS NULL))) OR (kind NOT IN
        ('SALE_REFUND','ORDER_REFUND','TECHNICAL_REVERSAL','ORDER_SETTLEMENT') AND
        relation_kind IS NULL AND related_operation_id IS NULL)) IS TRUE),
        CONSTRAINT ck_financial_operations_subject_valid CHECK (((kind IN
        ('SALE_COLLECTION','SALE_REFUND') AND subject_type = 'SALE') OR (kind IN
        ('ORDER_ADVANCE','ORDER_SETTLEMENT','ORDER_REFUND') AND subject_type = 'ORDER') OR
        (kind = 'OPERATIONAL_PAYMENT' AND subject_type = 'OPERATIONAL_PAYMENT') OR (kind =
        'OPERATIONAL_CHARGE' AND subject_type = 'OPERATIONAL_DISCOUNT') OR (kind IN
        ('CASH_OPENING','CASH_DEPOSIT','CASH_WITHDRAWAL') AND subject_type = 'CASH_SESSION'
        AND subject_id = cash_session_id) OR (kind = 'OPENING_OBLIGATION' AND
        ((opening_obligation_kind = 'CUSTOMER_ADVANCE' AND subject_type = 'ORDER') OR
        (opening_obligation_kind IN ('RECEIVABLE','PAYABLE') AND subject_type IN
        ('ORDER','OPENING_BALANCE')))) OR (kind = 'TECHNICAL_REVERSAL' AND subject_type IN
        ('SALE','ORDER','OPERATIONAL_PAYMENT','OPERATIONAL_DISCOUNT','CASH_SESSION','OPENING_BALANCE')))
        IS TRUE),
        CONSTRAINT ck_financial_operations_source_subject_valid CHECK (kind NOT IN
        ('SALE_COLLECTION','OPERATIONAL_PAYMENT','OPERATIONAL_CHARGE') OR source_id =
        subject_id),
        CONSTRAINT ck_financial_operations_not_self CHECK (related_operation_id IS NULL OR
        related_operation_id <> id),
        CONSTRAINT fk_financial_operations_related_operation_id_financial__64cc FOREIGN
        KEY(related_operation_id) REFERENCES financial_operations (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_operations_branch_id_branches FOREIGN KEY(branch_id)
        REFERENCES branches (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_operations_workstation_id_workstations FOREIGN
        KEY(workstation_id) REFERENCES workstations (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_operations_cash_session_id_cash_sessions FOREIGN
        KEY(cash_session_id) REFERENCES cash_sessions (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_operations_actor_id_users FOREIGN KEY(actor_id) REFERENCES
        users (id) ON DELETE RESTRICT
)
    """)
    op.execute("""
CREATE INDEX ix_financial_operations_branch_time ON financial_operations (branch_id,
        occurred_at)
    """)
    op.execute("""
CREATE INDEX ix_financial_operations_operation_id ON financial_operations (operation_id)
    """)
    op.execute("""
CREATE INDEX ix_financial_operations_subject ON financial_operations (subject_type,
        subject_id)
    """)
    op.execute("""
CREATE UNIQUE INDEX uq_financial_cash_opening ON financial_operations (cash_session_id) WHERE
        kind = 'CASH_OPENING'
    """)
    op.execute("""
CREATE TABLE financial_entries (
        id UUID NOT NULL,
        financial_operation_id UUID NOT NULL,
        leg_key VARCHAR(40) NOT NULL,
        payment_method_code VARCHAR(8) NOT NULL,
        direction VARCHAR(3) NOT NULL,
        amount NUMERIC(12, 2) NOT NULL,
        tendered_amount NUMERIC(12, 2),
        change_amount NUMERIC(12, 2) DEFAULT 0 NOT NULL,
        execution_mode VARCHAR(24) NOT NULL,
        state VARCHAR(16) NOT NULL,
        confirmed_at TIMESTAMP WITH TIME ZONE,
        resolution_kind VARCHAR(32),
        resolution_reference UUID,
        reverses_entry_id UUID,
        branch_id UUID NOT NULL,
        workstation_id UUID,
        cash_session_id UUID,
        actor_id UUID,
        currency_code VARCHAR(3) NOT NULL,
        context_version INTEGER NOT NULL,
        source_app VARCHAR(20) NOT NULL,
        actor_type VARCHAR(20) NOT NULL,
        operation_id UUID NOT NULL,
        operation_code VARCHAR(160),
        correlation_id UUID NOT NULL,
        causation_id UUID,
        request_id VARCHAR(120),
        idempotency_key UUID,
        related_branch_ids JSONB DEFAULT '[]'::jsonb NOT NULL,
        occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
        recorded_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
        CONSTRAINT pk_financial_entries PRIMARY KEY (id),
        CONSTRAINT uq_financial_entry_leg UNIQUE (financial_operation_id, leg_key),
        CONSTRAINT uq_financial_entry_reversal UNIQUE (reverses_entry_id),
        CONSTRAINT ck_financial_entries_context_valid CHECK (context_version = 1 AND
        operation_id IS NOT NULL AND correlation_id IS NOT NULL AND source_app IN
        ('POS','BACKOFFICE','API','SYSTEM','WORKER') AND ((actor_id IS NOT NULL AND actor_type
        = 'USER') OR (actor_id IS NULL AND actor_type = 'SYSTEM' AND source_app IN
        ('SYSTEM','WORKER')))),
        CONSTRAINT ck_financial_entries_currency_valid CHECK (currency_code = 'MXN'),
        CONSTRAINT ck_financial_entries_branches_array CHECK (jsonb_typeof(related_branch_ids)
        = 'array'),
        CONSTRAINT ck_financial_entries_amount_valid CHECK (amount > 0 AND amount <>
        'NaN'::numeric),
        CONSTRAINT ck_financial_entries_leg_key_valid CHECK (length(btrim(leg_key)) > 0),
        CONSTRAINT ck_financial_entries_method_valid CHECK (payment_method_code IN
        ('CASH','CARD')),
        CONSTRAINT ck_financial_entries_direction_valid CHECK (direction IN ('IN','OUT')),
        CONSTRAINT ck_financial_entries_execution_valid CHECK ((payment_method_code = 'CASH'
        AND execution_mode = 'LOCAL' AND cash_session_id IS NOT NULL) OR (payment_method_code
        = 'CARD' AND execution_mode IN
        ('ACCOUNTING_ONLY','PROVIDER_INTEGRATED','MANUAL_FALLBACK'))),
        CONSTRAINT ck_financial_entries_state_valid CHECK (state IN
        ('PENDING','PROCESSING','UNKNOWN','CONFIRMED','REJECTED','CANCELLED') AND ((state =
        'CONFIRMED' AND confirmed_at IS NOT NULL) OR (state <> 'CONFIRMED' AND confirmed_at IS
        NULL))),
        CONSTRAINT ck_financial_entries_evidence_valid CHECK (((resolution_kind IS NULL AND
        resolution_reference IS NULL AND state IN
        ('PENDING','PROCESSING','UNKNOWN','REJECTED','CANCELLED')) OR (resolution_kind =
        'LOCAL_CASH' AND payment_method_code = 'CASH' AND state = 'CONFIRMED' AND
        resolution_reference IS NULL) OR (resolution_reference IS NOT NULL AND
        ((resolution_kind = 'EXTERNAL_RECORDING' AND execution_mode = 'ACCOUNTING_ONLY' AND
        state = 'CONFIRMED') OR (resolution_kind = 'PROVIDER_CAPTURE' AND execution_mode =
        'PROVIDER_INTEGRATED' AND direction = 'IN' AND state = 'CONFIRMED') OR
        (resolution_kind = 'PROVIDER_REFUND' AND execution_mode = 'PROVIDER_INTEGRATED' AND
        direction = 'OUT' AND state = 'CONFIRMED') OR (resolution_kind = 'PROVIDER_REJECTION'
        AND execution_mode = 'PROVIDER_INTEGRATED' AND state = 'REJECTED') OR (resolution_kind
        = 'PROVIDER_VOID' AND execution_mode = 'PROVIDER_INTEGRATED' AND state = 'CANCELLED')
        OR (resolution_kind = 'MANUAL_RECONCILIATION' AND state IN
        ('CONFIRMED','REJECTED','CANCELLED'))))) IS TRUE),
        CONSTRAINT ck_financial_entries_tender_valid CHECK (change_amount >= 0 AND
        change_amount <> 'NaN'::numeric AND (tendered_amount IS NULL OR (tendered_amount > 0
        AND tendered_amount <> 'NaN'::numeric)) AND ((payment_method_code = 'CASH' AND
        direction = 'IN' AND tendered_amount IS NOT NULL AND tendered_amount = amount +
        change_amount) OR ((payment_method_code = 'CARD' OR direction = 'OUT') AND
        change_amount = 0 AND (tendered_amount IS NULL OR tendered_amount = amount)))),
        CONSTRAINT ck_financial_entries_not_self CHECK (reverses_entry_id IS NULL OR
        reverses_entry_id <> id),
        CONSTRAINT fk_financial_entries_financial_operation_id_financial_o_4720 FOREIGN
        KEY(financial_operation_id) REFERENCES financial_operations (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_entries_reverses_entry_id_financial_entries FOREIGN
        KEY(reverses_entry_id) REFERENCES financial_entries (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_entries_branch_id_branches FOREIGN KEY(branch_id) REFERENCES
        branches (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_entries_workstation_id_workstations FOREIGN
        KEY(workstation_id) REFERENCES workstations (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_entries_cash_session_id_cash_sessions FOREIGN
        KEY(cash_session_id) REFERENCES cash_sessions (id) ON DELETE RESTRICT,
        CONSTRAINT fk_financial_entries_actor_id_users FOREIGN KEY(actor_id) REFERENCES users
        (id) ON DELETE RESTRICT
)
    """)
    op.execute("""
CREATE INDEX ix_financial_entries_operation_id ON financial_entries (operation_id)
    """)
    op.execute("""
CREATE INDEX ix_financial_entries_session_state ON financial_entries (cash_session_id, state)
    """)
    op.execute("""
    CREATE FUNCTION validate_financial_context() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE station_branch uuid; cash_branch uuid; cash_station uuid;
    BEGIN
      IF NEW.workstation_id IS NOT NULL THEN
        SELECT branch_id INTO station_branch FROM workstations
          WHERE id = NEW.workstation_id FOR SHARE;
        IF NOT FOUND OR station_branch <> NEW.branch_id THEN
          RAISE EXCEPTION 'Financial workstation branch mismatch' USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.cash_session_id IS NOT NULL THEN
        SELECT branch_id, workstation_id INTO cash_branch, cash_station FROM cash_sessions
          WHERE id = NEW.cash_session_id FOR SHARE;
        IF NOT FOUND OR cash_branch <> NEW.branch_id
          OR NEW.workstation_id IS DISTINCT FROM cash_station THEN
          RAISE EXCEPTION 'Financial cash context mismatch' USING ERRCODE = '23514';
        END IF;
      END IF;
      NEW.recorded_at := clock_timestamp();
      RETURN NEW;
    END $$;

    CREATE FUNCTION protect_financial_operation() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE related financial_operations%ROWTYPE; original financial_entries%ROWTYPE;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'Financial operations are immutable' USING ERRCODE = '23514';
      END IF;
      IF NEW.related_operation_id IS NOT NULL THEN
        SELECT * INTO related FROM financial_operations WHERE id = NEW.related_operation_id;
        IF NOT FOUND OR related.branch_id <> NEW.branch_id
          OR related.currency_code <> NEW.currency_code
          OR related.subject_type <> NEW.subject_type OR related.subject_id <> NEW.subject_id THEN
          RAISE EXCEPTION 'Financial operation relation mismatch' USING ERRCODE = '23514';
        END IF;
        IF NEW.relation_kind = 'REFUND_OF' AND NOT (
          (NEW.kind = 'SALE_REFUND' AND related.kind = 'SALE_COLLECTION') OR
          (NEW.kind = 'ORDER_REFUND' AND (related.kind IN ('ORDER_ADVANCE','ORDER_SETTLEMENT')
            OR (related.kind = 'OPENING_OBLIGATION'
              AND related.opening_obligation_kind = 'CUSTOMER_ADVANCE')))) THEN
          RAISE EXCEPTION 'Invalid financial refund anchor' USING ERRCODE = '23514';
        END IF;
        IF NEW.relation_kind = 'SETTLEMENT_OF' AND
          (related.kind <> 'OPENING_OBLIGATION'
            OR related.opening_obligation_kind IS DISTINCT FROM 'RECEIVABLE') THEN
          RAISE EXCEPTION 'Invalid opening settlement relation' USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.kind = 'TECHNICAL_REVERSAL' THEN
        SELECT * INTO original FROM financial_entries WHERE id = NEW.source_id;
        IF NOT FOUND OR original.state <> 'CONFIRMED' OR original.reverses_entry_id IS NOT NULL
          OR original.financial_operation_id IS DISTINCT FROM NEW.related_operation_id
          OR original.amount <> NEW.amount_due THEN
          RAISE EXCEPTION 'Invalid financial reversal cause' USING ERRCODE = '23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;

    CREATE FUNCTION protect_financial_entry() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE parent financial_operations%ROWTYPE; original financial_entries%ROWTYPE;
      allocated numeric;
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Financial entries cannot be deleted' USING ERRCODE = '23514';
      END IF;
      IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'Financial entry writes require READ COMMITTED isolation'
          USING ERRCODE = '23514';
      END IF;
      IF TG_OP = 'UPDATE' THEN
        IF OLD.state IN ('CONFIRMED','REJECTED','CANCELLED') THEN
          RAISE EXCEPTION 'Terminal financial entries are immutable' USING ERRCODE = '23514';
        END IF;
        IF (to_jsonb(NEW) - ARRAY['state','confirmed_at','resolution_kind','resolution_reference'])
          IS DISTINCT FROM
          (to_jsonb(OLD) - ARRAY['state','confirmed_at','resolution_kind','resolution_reference'])
          THEN
          RAISE EXCEPTION 'Financial entry identity and amounts are immutable'
            USING ERRCODE = '23514';
        END IF;
        IF NEW.state = OLD.state OR NEW.state = 'PENDING'
          OR (OLD.state = 'UNKNOWN' AND NEW.state = 'PROCESSING') THEN
          RAISE EXCEPTION 'Invalid financial entry state transition' USING ERRCODE = '23514';
        END IF;
        IF OLD.state = 'UNKNOWN' AND
          (NEW.resolution_kind IS NULL OR NEW.resolution_reference IS NULL) THEN
          RAISE EXCEPTION 'Unknown financial result requires resolution evidence'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      -- FK inserts take KEY SHARE; NO KEY UPDATE serializes the budget without upgrading it.
      SELECT * INTO parent FROM financial_operations
        WHERE id = NEW.financial_operation_id FOR NO KEY UPDATE;
      IF NOT FOUND OR parent.branch_id <> NEW.branch_id
        OR parent.currency_code <> NEW.currency_code OR parent.kind = 'OPENING_OBLIGATION' THEN
        RAISE EXCEPTION 'Financial entry operation mismatch' USING ERRCODE = '23514';
      END IF;
      IF (parent.kind IN ('CASH_OPENING','SALE_COLLECTION','ORDER_ADVANCE','ORDER_SETTLEMENT',
          'OPERATIONAL_CHARGE','CASH_DEPOSIT') AND NEW.direction <> 'IN')
        OR (parent.kind IN ('SALE_REFUND','ORDER_REFUND','OPERATIONAL_PAYMENT','CASH_WITHDRAWAL')
          AND NEW.direction <> 'OUT') THEN
        RAISE EXCEPTION 'Financial entry direction mismatch' USING ERRCODE = '23514';
      END IF;
      IF parent.kind IN ('CASH_OPENING','CASH_DEPOSIT','CASH_WITHDRAWAL')
        AND (NEW.payment_method_code <> 'CASH'
        OR NEW.cash_session_id IS DISTINCT FROM parent.cash_session_id) THEN
        RAISE EXCEPTION 'Cash operation must affect its own drawer' USING ERRCODE = '23514';
      END IF;
      IF parent.kind = 'TECHNICAL_REVERSAL' THEN
        SELECT * INTO original FROM financial_entries WHERE id = parent.source_id;
        IF NEW.state <> 'CONFIRMED' OR NEW.reverses_entry_id IS DISTINCT FROM original.id
          OR NEW.amount <> original.amount
          OR NEW.payment_method_code <> original.payment_method_code
          OR NEW.currency_code <> original.currency_code OR NEW.direction = original.direction THEN
          RAISE EXCEPTION 'Technical reversal must exactly compensate its original entry'
            USING ERRCODE = '23514';
        END IF;
      ELSIF NEW.reverses_entry_id IS NOT NULL THEN
        RAISE EXCEPTION 'Only technical reversals may reverse entries' USING ERRCODE = '23514';
      END IF;
      SELECT COALESCE(sum(amount), 0) INTO allocated FROM financial_entries
        WHERE financial_operation_id = NEW.financial_operation_id AND id <> NEW.id
          AND state NOT IN ('REJECTED','CANCELLED');
      IF NEW.state NOT IN ('REJECTED','CANCELLED') THEN
        allocated := allocated + NEW.amount;
      END IF;
      IF allocated > parent.amount_due THEN
        RAISE EXCEPTION 'Financial entries exceed the admitted amount' USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END $$;

    CREATE TRIGGER financial_operation_context BEFORE INSERT ON financial_operations
      FOR EACH ROW EXECUTE FUNCTION validate_financial_context();
    CREATE TRIGGER financial_operation_protection BEFORE INSERT OR UPDATE OR DELETE
      ON financial_operations FOR EACH ROW EXECUTE FUNCTION protect_financial_operation();
    CREATE TRIGGER financial_entry_context BEFORE INSERT ON financial_entries
      FOR EACH ROW EXECUTE FUNCTION validate_financial_context();
    CREATE TRIGGER financial_entry_protection BEFORE INSERT OR UPDATE OR DELETE
      ON financial_entries FOR EACH ROW EXECUTE FUNCTION protect_financial_entry();
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM financial_operations)
        OR EXISTS (SELECT 1 FROM financial_entries) THEN
        RAISE EXCEPTION 'Financial evidence exists; use roll-forward or an approved restore';
      END IF;
    END $$;
    """)
    op.drop_table("financial_entries")
    op.drop_table("financial_operations")
    op.execute("DROP FUNCTION protect_financial_entry()")
    op.execute("DROP FUNCTION protect_financial_operation()")
    op.execute("DROP FUNCTION validate_financial_context()")
