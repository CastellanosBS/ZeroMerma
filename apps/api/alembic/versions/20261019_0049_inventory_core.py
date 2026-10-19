"""Canonical physical evidence, exact units, weighted cost and reservations."""

from alembic import op

revision = "20261019_0049_inventory_core"
down_revision = "20261019_0048_financial_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
ALTER TABLE inventory_balances DROP CONSTRAINT
    ck_inventory_balances_location_valid;
ALTER TABLE inventory_balances ADD CONSTRAINT
    ck_inventory_balances_location_valid CHECK (location_code IN
    ('BACKROOM','COUNTER','IN_TRANSIT','QUARANTINE','WASTE','WIP'));
ALTER TABLE inventory_adjustments DROP CONSTRAINT
    ck_inventory_adjustments_location_valid;
ALTER TABLE inventory_adjustments ADD CONSTRAINT
    ck_inventory_adjustments_location_valid CHECK (location_code IN
    ('BACKROOM','COUNTER','IN_TRANSIT','QUARANTINE','WASTE','WIP'));
ALTER TABLE inventory_movements DROP CONSTRAINT
    ck_inventory_movements_type_valid;
ALTER TABLE inventory_movements ADD CONSTRAINT
    ck_inventory_movements_type_valid CHECK (movement_type IN
    ('CLOSE_COUNTER_ADJUSTMENT','CLOSE_WASTE_ADJUSTMENT','COUNTER_TRANSFER',
    'INVENTORY_COMPENSATION','MANUAL_ADJUSTMENT','OPENING_ADJUSTMENT','ORDER_DELIVERY',
    'PRODUCTION_CONSUMPTION','PRODUCTION_OUTPUT','PRODUCTION_RETURN','PRODUCTION_WASTE',
    'PURCHASE_RECEIPT','QUARANTINE_RELEASE','RETURN_QUARANTINE','RETURN_RESTOCK','RETURN_WASTE',
    'REVERSAL','SALE_CLASS_ATTRIBUTION','SALE_DIRECT','STOCK_COUNT_ADJUSTMENT',
    'TRANSFER_DISPATCH','TRANSFER_DISPOSITION','TRANSFER_RECEIPT','TRANSFER_RETURN',
    'WASTE_RECORD','WIP_TRANSFER'));
ALTER TABLE inventory_movements DROP CONSTRAINT
    ck_inventory_movements_location_valid;
ALTER TABLE inventory_movements ADD CONSTRAINT
    ck_inventory_movements_location_valid CHECK (location_code IN
    ('BACKROOM','COUNTER','IN_TRANSIT','QUARANTINE','WASTE','WIP'));
ALTER TABLE inventory_adjustments DROP CONSTRAINT ck_inventory_adjustments_quantity_positive;
ALTER TABLE inventory_adjustments ADD CONSTRAINT ck_inventory_adjustments_quantity_positive
    CHECK (quantity > 0 OR (adjustment_type = 'SET_COUNTED' AND quantity = 0));
ALTER TABLE inventory_balances ADD COLUMN quantity_reserved NUMERIC(12, 3) DEFAULT 0 NOT NULL;
ALTER TABLE inventory_balances ADD COLUMN inventory_value NUMERIC(24, 8);
ALTER TABLE inventory_balances ADD CONSTRAINT ck_inventory_balances_value_valid CHECK
    (inventory_value IS NULL OR (inventory_value >= 0 AND inventory_value <> 'NaN'::numeric AND
    quantity_on_hand >= 0 AND (quantity_on_hand <> 0 OR inventory_value = 0)));
ALTER TABLE inventory_balances ADD CONSTRAINT ck_inventory_balances_reserved_valid CHECK
    (quantity_reserved >= 0 AND quantity_reserved <> 'NaN'::numeric AND quantity_on_hand <>
    'NaN'::numeric);
ALTER TABLE inventory_movements ADD COLUMN source_line_id UUID;
ALTER TABLE inventory_movements ADD COLUMN source_quantity NUMERIC(12, 3);
ALTER TABLE inventory_movements ADD COLUMN source_uom VARCHAR(32);
ALTER TABLE inventory_movements ADD COLUMN conversion_factor NUMERIC(12, 6);
ALTER TABLE inventory_movements ADD COLUMN context_version INTEGER;
ALTER TABLE inventory_movements ADD COLUMN idempotency_record_id UUID;
ALTER TABLE inventory_movements ADD COLUMN causal_effect_code VARCHAR(160);
ALTER TABLE inventory_movements ADD COLUMN source_app VARCHAR(20);
ALTER TABLE inventory_movements ADD COLUMN operation_code VARCHAR(160);
ALTER TABLE inventory_movements ADD COLUMN correlation_id UUID;
ALTER TABLE inventory_movements ADD COLUMN causation_id UUID;
ALTER TABLE inventory_movements ADD COLUMN request_id VARCHAR(128);
ALTER TABLE inventory_movements ADD COLUMN workstation_id UUID;
ALTER TABLE inventory_movements ADD COLUMN cash_session_id UUID;
ALTER TABLE inventory_movements ADD COLUMN related_branch_ids JSONB;
ALTER TABLE inventory_movements ADD COLUMN reversal_of_movement_id UUID;
ALTER TABLE inventory_movements ADD COLUMN unit_cost NUMERIC(18, 8);
ALTER TABLE inventory_movements ADD COLUMN total_cost NUMERIC(24, 8);
ALTER TABLE inventory_movements ADD COLUMN cost_evidence_reference VARCHAR(240);
ALTER TABLE inventory_movements ADD COLUMN recorded_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE inventory_movements ADD CONSTRAINT ck_inventory_movements_cost_valid CHECK
    (((unit_cost IS NULL AND total_cost IS NULL AND cost_evidence_reference IS NULL) OR
    (unit_cost >= 0 AND unit_cost <> 'NaN'::numeric AND total_cost >= 0 AND total_cost <>
    'NaN'::numeric AND length(btrim(cost_evidence_reference)) > 0)) IS TRUE);
ALTER TABLE inventory_movements ADD CONSTRAINT uq_inventory_cause UNIQUE (idempotency_record_id,
    causal_effect_code);
ALTER TABLE inventory_movements ADD CONSTRAINT ck_inventory_movements_cause_valid CHECK
    (context_version IS NULL OR (context_version = 1 AND idempotency_record_id IS NOT NULL AND
    causal_effect_code IS NOT NULL AND length(btrim(causal_effect_code)) > 0 AND
    source_document_type IS NOT NULL AND source_document_id IS NOT NULL AND operator_user_id IS
    NOT NULL AND source_app IS NOT NULL AND correlation_id IS NOT NULL AND source_quantity > 0
    AND source_quantity <> 'NaN'::numeric AND length(btrim(source_uom)) > 0 AND conversion_factor
    > 0 AND conversion_factor <> 'NaN'::numeric AND quantity = source_quantity *
    conversion_factor) IS TRUE);
ALTER TABLE inventory_movements ADD CONSTRAINT uq_inventory_reversal_cause UNIQUE
    (source_document_type, source_document_id, reversal_of_movement_id);
ALTER TABLE inventory_movements ADD CONSTRAINT
    fk_inventory_movements_cash_session_id_cash_sessions FOREIGN KEY(cash_session_id) REFERENCES
    cash_sessions (id) ON DELETE RESTRICT;
ALTER TABLE inventory_movements ADD CONSTRAINT fk_inventory_movements_workstation_id_workstations
    FOREIGN KEY(workstation_id) REFERENCES workstations (id) ON DELETE RESTRICT;
ALTER TABLE inventory_movements ADD CONSTRAINT
    fk_inventory_movements_idempotency_record_id_idempotenc_2e28 FOREIGN
    KEY(idempotency_record_id) REFERENCES idempotency_records (id) ON DELETE RESTRICT;
ALTER TABLE inventory_movements ADD CONSTRAINT
    fk_inventory_movements_reversal_of_movement_id_inventor_9e9e FOREIGN
    KEY(reversal_of_movement_id) REFERENCES inventory_movements (id) ON DELETE RESTRICT;

CREATE TABLE inventory_reservations (
	id UUID NOT NULL,
	branch_id UUID NOT NULL,
	product_id UUID NOT NULL,
	location_code VARCHAR(32) NOT NULL,
	quantity NUMERIC(12, 3) NOT NULL,
	consumed_quantity NUMERIC(12, 3) NOT NULL,
	released_quantity NUMERIC(12, 3) NOT NULL,
	unit_of_measure VARCHAR(32) NOT NULL,
	status VARCHAR(32) NOT NULL,
	source_document_type VARCHAR(64) NOT NULL,
	source_document_id UUID NOT NULL,
	source_line_id UUID,
	idempotency_record_id UUID NOT NULL,
	causal_effect_code VARCHAR(160) NOT NULL,
	operator_user_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_inventory_reservations PRIMARY KEY (id),
	CONSTRAINT ck_inventory_reservations_location_valid CHECK (location_code IN ('BACKROOM',
    'COUNTER')),
	CONSTRAINT ck_inventory_reservations_quantities_valid CHECK (quantity > 0 AND quantity <>
    'NaN'::numeric AND consumed_quantity >= 0 AND released_quantity >= 0 AND consumed_quantity +
    released_quantity <= quantity),
	CONSTRAINT ck_inventory_reservations_status_valid CHECK ((status = 'ACTIVE' AND
    consumed_quantity = 0 AND released_quantity < quantity) OR (status = 'PARTIALLY_CONSUMED' AND
    consumed_quantity > 0 AND consumed_quantity + released_quantity < quantity) OR (status =
    'CONSUMED' AND consumed_quantity = quantity) OR (status = 'RELEASED' AND released_quantity >
    0 AND consumed_quantity + released_quantity = quantity)),
	CONSTRAINT uq_inventory_reservation_cause UNIQUE (idempotency_record_id, causal_effect_code),
	CONSTRAINT fk_inventory_reservations_branch_id_branches FOREIGN KEY(branch_id) REFERENCES
    branches (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservations_product_id_products FOREIGN KEY(product_id) REFERENCES
    products (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservations_idempotency_record_id_idempot_cbb9 FOREIGN
    KEY(idempotency_record_id) REFERENCES idempotency_records (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservations_operator_user_id_users FOREIGN KEY(operator_user_id)
    REFERENCES users (id) ON DELETE RESTRICT
)

;

CREATE TABLE inventory_reservation_events (
	id UUID NOT NULL,
	reservation_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	event_type VARCHAR(16) NOT NULL,
	quantity NUMERIC(12, 3) NOT NULL,
	inventory_movement_id UUID,
	idempotency_record_id UUID NOT NULL,
	causal_effect_code VARCHAR(160) NOT NULL,
	operator_user_id UUID NOT NULL,
	reason VARCHAR(160),
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_inventory_reservation_events PRIMARY KEY (id),
	CONSTRAINT ck_inventory_reservation_events_type_valid CHECK (event_type IN ('RESERVE','RELEASE',
    'CONSUME')),
	CONSTRAINT ck_inventory_reservation_events_quantity_valid CHECK (quantity > 0 AND quantity <>
    'NaN'::numeric),
	CONSTRAINT ck_inventory_reservation_events_movement_valid CHECK ((event_type = 'CONSUME' AND
    inventory_movement_id IS NOT NULL) OR (event_type <> 'CONSUME' AND inventory_movement_id IS
    NULL)),
	CONSTRAINT uq_inventory_reservation_event_cause UNIQUE (idempotency_record_id,
    causal_effect_code),
	CONSTRAINT fk_inventory_reservation_events_reservation_id_inventor_1f2a FOREIGN
    KEY(reservation_id) REFERENCES inventory_reservations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservation_events_branch_id_branches FOREIGN KEY(branch_id) REFERENCES
    branches (id) ON DELETE RESTRICT,
	CONSTRAINT uq_inventory_reservation_events_inventory_movement_id UNIQUE (inventory_movement_id),
	CONSTRAINT fk_inventory_reservation_events_inventory_movement_id_i_98d0 FOREIGN
    KEY(inventory_movement_id) REFERENCES inventory_movements (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservation_events_idempotency_record_id_i_eaca FOREIGN
    KEY(idempotency_record_id) REFERENCES idempotency_records (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservation_events_operator_user_id_users FOREIGN KEY(operator_user_id)
    REFERENCES users (id) ON DELETE RESTRICT
)

;
    """)
    op.execute("""
ALTER TABLE products ADD COLUMN lot_tracking_enabled BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE products ADD COLUMN expiry_required BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE products ADD CONSTRAINT ck_products_lot_expiry_policy_valid CHECK (NOT
    expiry_required OR lot_tracking_enabled);

CREATE TABLE inventory_lots (
	id UUID NOT NULL,
	product_id UUID NOT NULL,
	lot_code VARCHAR(120) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE,
	produced_at TIMESTAMP WITH TIME ZONE,
	unidentified BOOLEAN NOT NULL,
	source_document_type VARCHAR(64) NOT NULL,
	source_document_id UUID NOT NULL,
	source_line_id UUID,
	idempotency_record_id UUID NOT NULL,
	operator_user_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_inventory_lots PRIMARY KEY (id),
	CONSTRAINT uq_inventory_lot_product_code UNIQUE (product_id, lot_code),
	CONSTRAINT ck_inventory_lots_code_required CHECK (length(btrim(lot_code)) > 0),
	CONSTRAINT ck_inventory_lots_unknown_expiry CHECK (NOT unidentified OR expires_at IS NULL),
	CONSTRAINT ck_inventory_lots_dates_valid CHECK (produced_at IS NULL OR expires_at IS NULL OR
    produced_at < expires_at),
	CONSTRAINT fk_inventory_lots_product_id_products FOREIGN KEY(product_id) REFERENCES products
    (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_lots_idempotency_record_id_idempotency_records FOREIGN
    KEY(idempotency_record_id) REFERENCES idempotency_records (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_lots_operator_user_id_users FOREIGN KEY(operator_user_id) REFERENCES
    users (id) ON DELETE RESTRICT
)

;

CREATE TABLE inventory_lot_balances (
	id UUID NOT NULL,
	branch_id UUID NOT NULL,
	product_id UUID NOT NULL,
	lot_id UUID NOT NULL,
	location_code VARCHAR(32) NOT NULL,
	quantity_on_hand NUMERIC(12, 3) NOT NULL,
	quantity_reserved NUMERIC(12, 3) NOT NULL,
	CONSTRAINT pk_inventory_lot_balances PRIMARY KEY (id),
	CONSTRAINT uq_inventory_lot_balance UNIQUE (branch_id, product_id, location_code, lot_id),
	CONSTRAINT ck_inventory_lot_balances_quantities_valid CHECK (quantity_on_hand >= 0 AND
    quantity_reserved >= 0 AND quantity_reserved <= quantity_on_hand AND quantity_on_hand <>
    'NaN'::numeric),
	CONSTRAINT ck_inventory_lot_balances_location_valid CHECK (location_code IN ('BACKROOM',
    'COUNTER','IN_TRANSIT','WASTE','QUARANTINE','WIP')),
	CONSTRAINT fk_inventory_lot_balances_branch_id_branches FOREIGN KEY(branch_id) REFERENCES
    branches (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_lot_balances_product_id_products FOREIGN KEY(product_id) REFERENCES
    products (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_lot_balances_lot_id_inventory_lots FOREIGN KEY(lot_id) REFERENCES
    inventory_lots (id) ON DELETE RESTRICT
)

;

CREATE TABLE inventory_movement_lot_allocations (
	id UUID NOT NULL,
	movement_id UUID NOT NULL,
	lot_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	quantity NUMERIC(12, 3) NOT NULL,
	CONSTRAINT pk_inventory_movement_lot_allocations PRIMARY KEY (id),
	CONSTRAINT uq_inventory_movement_lot UNIQUE (movement_id, lot_id),
	CONSTRAINT ck_inventory_movement_lot_allocations_quantity_valid CHECK (quantity > 0 AND quantity
    <> 'NaN'::numeric),
	CONSTRAINT fk_inventory_movement_lot_allocations_movement_id_inven_9daa FOREIGN KEY(movement_id)
    REFERENCES inventory_movements (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_movement_lot_allocations_lot_id_inventory_lots FOREIGN KEY(lot_id)
    REFERENCES inventory_lots (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_movement_lot_allocations_branch_id_branches FOREIGN KEY(branch_id)
    REFERENCES branches (id) ON DELETE RESTRICT
)

;

CREATE TABLE inventory_reservation_lot_allocations (
	id UUID NOT NULL,
	reservation_id UUID NOT NULL,
	lot_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	quantity NUMERIC(12, 3) NOT NULL,
	consumed_quantity NUMERIC(12, 3) NOT NULL,
	released_quantity NUMERIC(12, 3) NOT NULL,
	CONSTRAINT pk_inventory_reservation_lot_allocations PRIMARY KEY (id),
	CONSTRAINT uq_inventory_reservation_lot UNIQUE (reservation_id, lot_id),
	CONSTRAINT ck_inventory_reservation_lot_allocations_quantities_valid CHECK (quantity > 0 AND
    consumed_quantity >= 0 AND released_quantity >= 0 AND consumed_quantity + released_quantity
    <= quantity),
	CONSTRAINT fk_inventory_reservation_lot_allocations_reservation_id_179b FOREIGN
    KEY(reservation_id) REFERENCES inventory_reservations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservation_lot_allocations_lot_id_inventory_lots FOREIGN KEY(lot_id)
    REFERENCES inventory_lots (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservation_lot_allocations_branch_id_branches FOREIGN KEY(branch_id)
    REFERENCES branches (id) ON DELETE RESTRICT
)

;

CREATE TABLE inventory_reservation_event_lots (
	id UUID NOT NULL,
	reservation_event_id UUID NOT NULL,
	lot_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	quantity NUMERIC(12, 3) NOT NULL,
	CONSTRAINT pk_inventory_reservation_event_lots PRIMARY KEY (id),
	CONSTRAINT uq_inventory_reservation_event_lot UNIQUE (reservation_event_id, lot_id),
	CONSTRAINT ck_inventory_reservation_event_lots_quantity_valid CHECK (quantity > 0 AND quantity
    <> 'NaN'::numeric),
	CONSTRAINT fk_inventory_reservation_event_lots_reservation_event_i_a922 FOREIGN
    KEY(reservation_event_id) REFERENCES inventory_reservation_events (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservation_event_lots_lot_id_inventory_lots FOREIGN KEY(lot_id)
    REFERENCES inventory_lots (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_reservation_event_lots_branch_id_branches FOREIGN KEY(branch_id)
    REFERENCES branches (id) ON DELETE RESTRICT
)

;
    """)
    op.execute("""
        CREATE FUNCTION protect_inventory_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'INSERT' THEN
            IF NEW.context_version IS DISTINCT FROM 1 OR NOT EXISTS (
              SELECT 1 FROM idempotency_records i WHERE i.id = NEW.idempotency_record_id
                AND i.actor_user_id = NEW.operator_user_id AND i.status = 'PROCESSING'
            ) THEN
              RAISE EXCEPTION 'New inventory evidence requires its admitted command'
                USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
          END IF;
          RAISE EXCEPTION 'Inventory evidence is immutable; correct forward'
            USING ERRCODE = '23514';
        END $$;
        CREATE TRIGGER inventory_movement_immutable
          BEFORE INSERT OR UPDATE OR DELETE ON inventory_movements
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_history();

        CREATE FUNCTION protect_inventory_reservation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'inventory_reservations' THEN
            IF (to_jsonb(NEW) - ARRAY['consumed_quantity','released_quantity','status']) =
               (to_jsonb(OLD) - ARRAY['consumed_quantity','released_quantity','status']) THEN
              RETURN NEW;
            END IF;
          END IF;
          RAISE EXCEPTION 'Reservation identity and evidence are immutable'
            USING ERRCODE = '23514';
        END $$;
        CREATE TRIGGER inventory_reservation_identity
          BEFORE UPDATE OR DELETE ON inventory_reservations
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_reservation();
        CREATE TRIGGER inventory_reservation_event_immutable
          BEFORE UPDATE OR DELETE ON inventory_reservation_events
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_reservation();

        CREATE FUNCTION validate_inventory_reservation() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE reservation_id_to_check UUID; reservation inventory_reservations;
                reserved NUMERIC; consumed NUMERIC; released NUMERIC;
        BEGIN
          IF TG_TABLE_NAME = 'inventory_reservations' THEN
            reservation_id_to_check := NEW.id;
          ELSE
            reservation_id_to_check := NEW.reservation_id;
          END IF;
          SELECT * INTO reservation FROM inventory_reservations
            WHERE id = reservation_id_to_check;
          SELECT COALESCE(SUM(quantity) FILTER (WHERE event_type = 'RESERVE'),0),
                 COALESCE(SUM(quantity) FILTER (WHERE event_type = 'CONSUME'),0),
                 COALESCE(SUM(quantity) FILTER (WHERE event_type = 'RELEASE'),0)
            INTO reserved, consumed, released FROM inventory_reservation_events
            WHERE reservation_id = reservation_id_to_check;
          IF reserved <> reservation.quantity OR consumed <> reservation.consumed_quantity
            OR released <> reservation.released_quantity OR EXISTS (
              SELECT 1 FROM inventory_reservation_events e
              LEFT JOIN inventory_movements m ON m.id = e.inventory_movement_id
              WHERE e.reservation_id = reservation_id_to_check
                AND (e.branch_id <> reservation.branch_id OR
                  (e.event_type = 'CONSUME' AND (m.product_id <> reservation.product_id
                    OR m.branch_id <> reservation.branch_id
                    OR m.location_code <> reservation.location_code
                    OR m.quantity <> e.quantity OR m.direction <> 'OUT'
                    OR m.idempotency_record_id <> e.idempotency_record_id)))
            ) THEN
            RAISE EXCEPTION 'Reservation projection does not reconcile with its immutable events'
              USING ERRCODE = '23514';
          END IF;
          RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER inventory_reservation_reconciles
          AFTER INSERT OR UPDATE ON inventory_reservations DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION validate_inventory_reservation();
        CREATE CONSTRAINT TRIGGER inventory_reservation_event_reconciles
          AFTER INSERT ON inventory_reservation_events DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION validate_inventory_reservation();

        CREATE FUNCTION protect_inventory_base_uom() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF UPPER(BTRIM(OLD.unit_of_measure)) <> UPPER(BTRIM(NEW.unit_of_measure)) AND (
            EXISTS (SELECT 1 FROM inventory_movements WHERE product_id = OLD.id)
            OR EXISTS (SELECT 1 FROM inventory_reservations WHERE product_id = OLD.id)
            OR EXISTS (SELECT 1 FROM inventory_balances WHERE product_id = OLD.id
              AND (quantity_on_hand <> 0 OR quantity_reserved <> 0))
          ) THEN
            RAISE EXCEPTION 'Inventory base unit with physical evidence cannot be reinterpreted'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER inventory_product_uom_frozen BEFORE UPDATE ON products
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_base_uom();
    """)
    op.execute("""
        CREATE FUNCTION protect_inventory_lot_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'inventory_reservation_lot_allocations'
            AND (to_jsonb(NEW) - ARRAY['consumed_quantity','released_quantity']) =
                (to_jsonb(OLD) - ARRAY['consumed_quantity','released_quantity']) THEN
            RETURN NEW;
          END IF;
          RAISE EXCEPTION 'Inventory lot evidence is immutable; correct forward'
            USING ERRCODE = '23514';
        END $$;
        CREATE TRIGGER inventory_lot_immutable BEFORE UPDATE OR DELETE ON inventory_lots
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_lot_evidence();
        CREATE TRIGGER inventory_movement_lot_immutable
          BEFORE UPDATE OR DELETE ON inventory_movement_lot_allocations
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_lot_evidence();
        CREATE TRIGGER inventory_reservation_lot_identity
          BEFORE UPDATE OR DELETE ON inventory_reservation_lot_allocations
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_lot_evidence();
        CREATE TRIGGER inventory_reservation_event_lot_immutable
          BEFORE UPDATE OR DELETE ON inventory_reservation_event_lots
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_lot_evidence();

        CREATE FUNCTION validate_inventory_movement_lots() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE movement_id_to_check UUID; movement inventory_movements;
                tracked BOOLEAN; allocated NUMERIC;
        BEGIN
          IF TG_TABLE_NAME = 'inventory_movements' THEN
            movement_id_to_check := NEW.id;
          ELSE
            movement_id_to_check := NEW.movement_id;
          END IF;
          SELECT * INTO movement FROM inventory_movements WHERE id = movement_id_to_check;
          SELECT lot_tracking_enabled INTO tracked FROM products WHERE id = movement.product_id;
          SELECT COALESCE(SUM(quantity),0) INTO allocated
            FROM inventory_movement_lot_allocations WHERE movement_id = movement_id_to_check;
          IF (tracked AND allocated <> movement.quantity) OR (NOT tracked AND allocated <> 0)
            OR EXISTS (
              SELECT 1 FROM inventory_movement_lot_allocations a JOIN inventory_lots l ON
    l.id=a.lot_id
              WHERE a.movement_id=movement_id_to_check AND
                (l.product_id <> movement.product_id OR a.branch_id <> movement.branch_id)
            ) THEN
            RAISE EXCEPTION 'Inventory movement does not reconcile with lot allocations'
              USING ERRCODE = '23514';
          END IF;
          RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER inventory_movement_lots_reconcile
          AFTER INSERT ON inventory_movements DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION validate_inventory_movement_lots();
        CREATE CONSTRAINT TRIGGER inventory_movement_lot_reconciles
          AFTER INSERT ON inventory_movement_lot_allocations DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION validate_inventory_movement_lots();

        CREATE FUNCTION protect_inventory_lot_policy() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF (OLD.lot_tracking_enabled <> NEW.lot_tracking_enabled
            OR OLD.expiry_required <> NEW.expiry_required
            OR OLD.is_inventory_tracked <> NEW.is_inventory_tracked) AND (
            EXISTS (SELECT 1 FROM inventory_movements WHERE product_id = OLD.id)
            OR EXISTS (SELECT 1 FROM inventory_lots WHERE product_id = OLD.id)
            OR EXISTS (SELECT 1 FROM inventory_reservations WHERE product_id = OLD.id)
            OR EXISTS (SELECT 1 FROM inventory_balances WHERE product_id = OLD.id
              AND (quantity_on_hand <> 0 OR quantity_reserved <> 0))
          ) THEN
            RAISE EXCEPTION
    'Lot policy with physical evidence requires explicit cutover reconciliation'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER inventory_product_lot_policy BEFORE UPDATE ON products
          FOR EACH ROW EXECUTE FUNCTION protect_inventory_lot_policy();

        CREATE FUNCTION validate_inventory_reversal() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE original inventory_movements; reversed_quantity NUMERIC; reversed_value NUMERIC;
        BEGIN
          IF NEW.reversal_of_movement_id IS NULL THEN RETURN NULL; END IF;
          SELECT * INTO original FROM inventory_movements WHERE id=NEW.reversal_of_movement_id;
          PERFORM 1 FROM inventory_balances WHERE branch_id=original.branch_id
            AND product_id=original.product_id AND location_code=original.location_code
            FOR UPDATE;
          SELECT SUM(quantity), SUM(total_cost) INTO reversed_quantity, reversed_value
            FROM inventory_movements WHERE reversal_of_movement_id=original.id;
          IF original.id IS NULL OR original.branch_id <> NEW.branch_id
            OR original.product_id <> NEW.product_id OR original.location_code <> NEW.location_code
            OR original.unit_of_measure <> NEW.unit_of_measure OR original.direction=NEW.direction
            OR (original.total_cost IS NULL) IS DISTINCT FROM (NEW.total_cost IS NULL)
            OR reversed_quantity > original.quantity
            OR (original.total_cost IS NOT NULL AND reversed_value > original.total_cost)
            OR EXISTS (
              SELECT 1 FROM inventory_movements m
              JOIN inventory_movement_lot_allocations a ON a.movement_id=m.id
              LEFT JOIN inventory_movement_lot_allocations o
                ON o.movement_id=original.id AND o.lot_id=a.lot_id
              WHERE m.reversal_of_movement_id=original.id GROUP BY a.lot_id,o.quantity
              HAVING SUM(a.quantity)>COALESCE(o.quantity,0)
            ) THEN
            RAISE EXCEPTION 'Inventory compensation exceeds or changes its original evidence'
              USING ERRCODE='23514';
          END IF;
          RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER inventory_reversal_bounded AFTER INSERT ON inventory_movements
          DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_inventory_reversal();

        CREATE FUNCTION validate_inventory_admission() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM idempotency_records i WHERE i.id=NEW.idempotency_record_id
            AND i.actor_user_id=NEW.operator_user_id AND i.status='PROCESSING') THEN
            RAISE EXCEPTION 'Inventory evidence requires its admitted command'
              USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER inventory_lot_admitted BEFORE INSERT ON inventory_lots
          FOR EACH ROW EXECUTE FUNCTION validate_inventory_admission();
        CREATE TRIGGER inventory_reservation_admitted BEFORE INSERT ON inventory_reservations
          FOR EACH ROW EXECUTE FUNCTION validate_inventory_admission();
        CREATE TRIGGER inventory_reservation_event_admitted
          BEFORE INSERT ON inventory_reservation_events
          FOR EACH ROW EXECUTE FUNCTION validate_inventory_admission();
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM inventory_movements WHERE context_version IS NOT NULL)
            OR EXISTS (SELECT 1 FROM inventory_lots)
            OR EXISTS (SELECT 1 FROM inventory_lot_balances)
            OR EXISTS (SELECT 1 FROM inventory_reservations)
            OR EXISTS (SELECT 1 FROM inventory_reservation_events)
            OR EXISTS (SELECT 1 FROM inventory_balances WHERE quantity_reserved <> 0
              OR inventory_value IS NOT NULL OR location_code IN ('WIP','QUARANTINE'))
            OR EXISTS (SELECT 1 FROM inventory_adjustments
              WHERE quantity = 0 OR location_code IN ('WIP','QUARANTINE')) THEN
            RAISE EXCEPTION 'Inventory evidence requires forward correction or restore';
          END IF;
        END $$;
        DROP TRIGGER inventory_product_lot_policy ON products;
        DROP FUNCTION protect_inventory_lot_policy();
        DROP TRIGGER inventory_reversal_bounded ON inventory_movements;
        DROP FUNCTION validate_inventory_reversal();
        DROP TRIGGER inventory_movement_lots_reconcile ON inventory_movements;
        DROP TABLE inventory_reservation_event_lots;
        DROP TABLE inventory_reservation_lot_allocations;
        DROP TABLE inventory_movement_lot_allocations;
        DROP TABLE inventory_lot_balances;
        DROP TABLE inventory_lots;
        DROP FUNCTION validate_inventory_movement_lots();
        DROP FUNCTION protect_inventory_lot_evidence();
        ALTER TABLE products DROP COLUMN expiry_required, DROP COLUMN lot_tracking_enabled;
        DROP TRIGGER inventory_product_uom_frozen ON products;
        DROP FUNCTION protect_inventory_base_uom();
        DROP TABLE inventory_reservation_events;
        DROP TABLE inventory_reservations;
        DROP FUNCTION validate_inventory_admission();
        DROP FUNCTION validate_inventory_reservation();
        DROP FUNCTION protect_inventory_reservation();
        DROP TRIGGER inventory_movement_immutable ON inventory_movements;
        DROP FUNCTION protect_inventory_history();
        ALTER TABLE inventory_balances DROP COLUMN quantity_reserved, DROP COLUMN inventory_value;
        ALTER TABLE inventory_movements
          DROP COLUMN source_line_id, DROP COLUMN source_quantity, DROP COLUMN source_uom,
          DROP COLUMN conversion_factor, DROP COLUMN context_version,
          DROP COLUMN idempotency_record_id, DROP COLUMN causal_effect_code,
          DROP COLUMN source_app, DROP COLUMN operation_code, DROP COLUMN correlation_id,
          DROP COLUMN causation_id, DROP COLUMN request_id, DROP COLUMN workstation_id,
          DROP COLUMN cash_session_id, DROP COLUMN related_branch_ids,
          DROP COLUMN reversal_of_movement_id, DROP COLUMN unit_cost, DROP COLUMN total_cost,
          DROP COLUMN cost_evidence_reference, DROP COLUMN recorded_at;
        ALTER TABLE inventory_balances
          DROP CONSTRAINT ck_inventory_balances_location_valid,
          ADD CONSTRAINT ck_inventory_balances_location_valid
          CHECK (location_code IN ('BACKROOM','COUNTER','IN_TRANSIT','WASTE'));
        ALTER TABLE inventory_adjustments
          DROP CONSTRAINT ck_inventory_adjustments_quantity_positive,
          ADD CONSTRAINT ck_inventory_adjustments_quantity_positive CHECK (quantity > 0),
          DROP CONSTRAINT ck_inventory_adjustments_location_valid,
          ADD CONSTRAINT ck_inventory_adjustments_location_valid
          CHECK (location_code IN ('BACKROOM','COUNTER','IN_TRANSIT','WASTE'));
        ALTER TABLE inventory_movements
          DROP CONSTRAINT ck_inventory_movements_location_valid,
          ADD CONSTRAINT ck_inventory_movements_location_valid
          CHECK (location_code IN ('BACKROOM','COUNTER','IN_TRANSIT','WASTE')),
          DROP CONSTRAINT ck_inventory_movements_type_valid,
          ADD CONSTRAINT ck_inventory_movements_type_valid
          CHECK (movement_type IN ('MANUAL_ADJUSTMENT','STOCK_COUNT_ADJUSTMENT',
            'TRANSFER_DISPATCH','TRANSFER_RECEIPT','PURCHASE_RECEIPT',
            'PRODUCTION_CONSUMPTION','PRODUCTION_OUTPUT','WASTE_RECORD'));
    """)
