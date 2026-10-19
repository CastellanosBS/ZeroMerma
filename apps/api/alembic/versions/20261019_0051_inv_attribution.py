"""Per-sale physical obligations and separate economic/physical return facts."""

from alembic import op

revision = "20261019_0051_inv_attribution"
down_revision = "20261019_0050_inventory_rebuild"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM sale_return_lines) THEN
            RAISE EXCEPTION 'Return contract normalization requires an empty development return
                dataset or approved archival/restore; immutable return acknowledgements cannot be
                rewritten';
          END IF;
          IF EXISTS (SELECT 1 FROM sale_lines WHERE capture_mode='CLASS_CAPTURE' AND
              physical_attribution_status='RECONCILED') THEN
            RAISE EXCEPTION 'Historical class attribution lacks per-sale evidence; adopt an
                approved physical opening in a clean deployment instead of inventing allocations';
          END IF;
        END $$;
        ALTER TABLE operation_documents ALTER COLUMN workstation_id DROP NOT NULL;
        CREATE TABLE class_inventory_obligations (
            id UUID NOT NULL,
            sale_line_id UUID NOT NULL,
            branch_id UUID NOT NULL,
            product_class_id UUID NOT NULL,
            required_quantity NUMERIC(12, 3) NOT NULL,
            attributed_quantity NUMERIC(12, 3) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT pk_class_inventory_obligations PRIMARY KEY (id),
            CONSTRAINT uq_class_inventory_obligation_sale_line UNIQUE (sale_line_id),
            CONSTRAINT ck_class_inventory_obligations_ck_class_obligation_required CHECK
                (required_quantity > 0),
            CONSTRAINT ck_class_inventory_obligations_ck_class_obligation_attributed CHECK
                (attributed_quantity >= 0 AND attributed_quantity <= required_quantity),
            CONSTRAINT ck_class_inventory_obligations_ck_class_obligation_status CHECK ((status =
                'OPEN' AND attributed_quantity < required_quantity) OR (status = 'FULFILLED' AND
                attributed_quantity = required_quantity)),
            CONSTRAINT fk_class_inventory_obligations_sale_line_id_sale_lines FOREIGN
                KEY(sale_line_id) REFERENCES sale_lines (id) ON DELETE RESTRICT,
            CONSTRAINT fk_class_inventory_obligations_branch_id_branches FOREIGN KEY(branch_id)
                REFERENCES branches (id),
            CONSTRAINT fk_class_inventory_obligations_product_class_id_product_classes FOREIGN
                KEY(product_class_id) REFERENCES product_classes (id)
        );
        CREATE TABLE class_inventory_attributions (
            id UUID NOT NULL,
            obligation_id UUID NOT NULL,
            product_id UUID NOT NULL,
            quantity NUMERIC(12, 3) NOT NULL,
            inventory_movement_id UUID,
            idempotency_record_id UUID NOT NULL,
            causal_effect_code VARCHAR(160) NOT NULL,
            source_document_type VARCHAR(64) NOT NULL,
            source_document_id UUID NOT NULL,
            actor_id UUID NOT NULL,
            occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT pk_class_inventory_attributions PRIMARY KEY (id),
            CONSTRAINT ck_class_inventory_attributions_ck_class_attribution_quantity CHECK
                (quantity > 0),
            CONSTRAINT uq_class_attribution_effect UNIQUE (idempotency_record_id,
                causal_effect_code),
            CONSTRAINT uq_class_attribution_movement UNIQUE (inventory_movement_id),
            CONSTRAINT fk_class_inventory_attributions_obligation_id_class_inv_4010 FOREIGN
                KEY(obligation_id) REFERENCES class_inventory_obligations (id) ON DELETE RESTRICT,
            CONSTRAINT fk_class_inventory_attributions_product_id_products FOREIGN KEY(product_id)
                REFERENCES products (id),
            CONSTRAINT fk_class_inventory_attributions_inventory_movement_id_i_f9f1 FOREIGN
                KEY(inventory_movement_id) REFERENCES inventory_movements (id) ON DELETE RESTRICT,
            CONSTRAINT fk_class_inventory_attributions_idempotency_record_id_i_cf7f FOREIGN
                KEY(idempotency_record_id) REFERENCES idempotency_records (id) ON DELETE RESTRICT,
            CONSTRAINT fk_class_inventory_attributions_actor_id_users FOREIGN KEY(actor_id)
                REFERENCES users (id)
        );
        CREATE TABLE return_disposition_allocations (
            id UUID NOT NULL,
            sale_return_line_id UUID NOT NULL,
            sequence INTEGER NOT NULL,
            returned_product_id UUID NOT NULL,
            returned_product_code_snapshot VARCHAR(64) NOT NULL,
            returned_product_name_snapshot VARCHAR(160) NOT NULL,
            returned_product_class_id UUID NOT NULL,
            returned_product_class_code_snapshot VARCHAR(64) NOT NULL,
            returned_product_class_name_snapshot VARCHAR(160) NOT NULL,
            quantity NUMERIC(12, 3) NOT NULL,
            disposition_code VARCHAR(32) NOT NULL,
            lot_id UUID,
            inventory_movement_id UUID,
            CONSTRAINT pk_return_disposition_allocations PRIMARY KEY (id),
            CONSTRAINT ck_return_disposition_allocations_ck_return_allocation_quantity CHECK
                (quantity > 0),
            CONSTRAINT ck_return_disposition_allocations_ck_return_allocation__f71b CHECK
                (disposition_code IN ('RESTOCK_COUNTER', 'RESTOCK_BACKROOM', 'QUARANTINE',
                'SEND_TO_WASTE', 'NO_STOCK')),
            CONSTRAINT uq_return_allocation_sequence UNIQUE (sale_return_line_id, sequence),
            CONSTRAINT uq_return_allocation_movement UNIQUE (inventory_movement_id),
            CONSTRAINT fk_return_disposition_allocations_sale_return_line_id_s_7ecb FOREIGN
                KEY(sale_return_line_id) REFERENCES sale_return_lines (id) ON DELETE RESTRICT,
            CONSTRAINT fk_return_disposition_allocations_returned_product_id_products FOREIGN
                KEY(returned_product_id) REFERENCES products (id) ON DELETE RESTRICT,
            CONSTRAINT fk_return_disposition_allocations_returned_product_clas_45e9 FOREIGN
                KEY(returned_product_class_id) REFERENCES product_classes (id) ON DELETE RESTRICT,
            CONSTRAINT fk_return_disposition_allocations_lot_id_inventory_lots FOREIGN KEY(lot_id)
                REFERENCES inventory_lots (id) ON DELETE RESTRICT,
            CONSTRAINT fk_return_disposition_allocations_inventory_movement_id_15a9 FOREIGN
                KEY(inventory_movement_id) REFERENCES inventory_movements (id) ON DELETE RESTRICT
        );
        ALTER TABLE sale_return_lines DROP COLUMN returned_product_id CASCADE;
        ALTER TABLE sale_return_lines DROP COLUMN returned_product_code_snapshot CASCADE;
        ALTER TABLE sale_return_lines DROP COLUMN returned_product_name_snapshot CASCADE;
        ALTER TABLE sale_return_lines DROP COLUMN returned_product_class_id CASCADE;
        ALTER TABLE sale_return_lines DROP COLUMN returned_product_class_code_snapshot CASCADE;
        ALTER TABLE sale_return_lines DROP COLUMN returned_product_class_name_snapshot CASCADE;
        ALTER TABLE sale_return_lines DROP COLUMN disposition_code CASCADE;
        INSERT INTO
            class_inventory_obligations(id,sale_line_id,branch_id,product_class_id,required_quantity,attributed_quantity,status,created_at)
        SELECT gen_random_uuid(), l.id, s.branch_id, l.product_class_id, l.quantity, 0, 'OPEN',
            s.confirmed_at
        FROM sale_lines l JOIN sales s ON s.id=l.sale_id WHERE l.capture_mode='CLASS_CAPTURE';
        CREATE FUNCTION protect_inventory_attribution_fact() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Physical attribution and return facts are immutable; create a causal
              compensation' USING ERRCODE='23514';
        END $$;
        CREATE TRIGGER class_attribution_immutable BEFORE UPDATE OR DELETE ON
            class_inventory_attributions FOR EACH ROW EXECUTE FUNCTION
            protect_inventory_attribution_fact();
        CREATE TRIGGER return_allocation_immutable BEFORE UPDATE OR DELETE ON
            return_disposition_allocations FOR EACH ROW EXECUTE FUNCTION
            protect_inventory_attribution_fact();
        CREATE TRIGGER sale_return_line_immutable BEFORE UPDATE OR DELETE ON sale_return_lines FOR
            EACH ROW EXECUTE FUNCTION protect_inventory_attribution_fact();
        CREATE TRIGGER sale_return_immutable BEFORE UPDATE OR DELETE ON sale_returns FOR EACH ROW
            EXECUTE FUNCTION protect_inventory_attribution_fact();
        CREATE FUNCTION protect_class_obligation_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP='DELETE' OR
              ROW(OLD.id,OLD.sale_line_id,OLD.branch_id,OLD.product_class_id,OLD.required_quantity,OLD.created_at)
              IS DISTINCT FROM
              ROW(NEW.id,NEW.sale_line_id,NEW.branch_id,NEW.product_class_id,NEW.required_quantity,NEW.created_at)
              THEN
            RAISE EXCEPTION 'Class obligation identity is immutable' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER class_obligation_identity BEFORE UPDATE OR DELETE ON
            class_inventory_obligations FOR EACH ROW EXECUTE FUNCTION
            protect_class_obligation_identity();

        ALTER TABLE cash_session_close_product_counts ADD COLUMN lot_counts JSONB NOT NULL DEFAULT
            '[]'::jsonb;
        CREATE TRIGGER close_product_count_immutable BEFORE UPDATE OR DELETE ON
            cash_session_close_product_counts FOR EACH ROW EXECUTE FUNCTION
            protect_inventory_attribution_fact();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN IF EXISTS (SELECT 1 FROM cash_session_close_product_counts WHERE lot_counts <>
            '[]'::jsonb) THEN RAISE EXCEPTION 'Lot counts require forward correction or restore';
            END IF; END $$;
        DROP TRIGGER close_product_count_immutable ON cash_session_close_product_counts;
        ALTER TABLE cash_session_close_product_counts DROP COLUMN lot_counts;

        DO $$ BEGIN
          IF EXISTS(SELECT 1 FROM class_inventory_obligations) OR EXISTS(SELECT 1 FROM
              return_disposition_allocations) OR EXISTS(SELECT 1 FROM operation_documents WHERE
              workstation_id IS NULL) THEN
            RAISE EXCEPTION 'Inventory attribution adoption requires forward correction or restore';
          END IF;
        END $$;
        DROP TRIGGER sale_return_immutable ON sale_returns;
        DROP TRIGGER sale_return_line_immutable ON sale_return_lines;
        DROP TABLE return_disposition_allocations;
        DROP TABLE class_inventory_attributions;
        DROP TABLE class_inventory_obligations;
        DROP FUNCTION protect_inventory_attribution_fact();
        DROP FUNCTION protect_class_obligation_identity();
        ALTER TABLE operation_documents ALTER COLUMN workstation_id SET NOT NULL;
        ALTER TABLE sale_return_lines ADD COLUMN returned_product_id UUID NOT NULL REFERENCES
            products(id) ON DELETE RESTRICT;
        ALTER TABLE sale_return_lines ADD COLUMN returned_product_code_snapshot VARCHAR(64) NOT
            NULL;
        ALTER TABLE sale_return_lines ADD COLUMN returned_product_name_snapshot VARCHAR(160) NOT
            NULL;
        ALTER TABLE sale_return_lines ADD COLUMN returned_product_class_id UUID NOT NULL
            REFERENCES product_classes(id) ON DELETE RESTRICT;
        ALTER TABLE sale_return_lines ADD COLUMN returned_product_class_code_snapshot VARCHAR(64)
            NOT NULL;
        ALTER TABLE sale_return_lines ADD COLUMN returned_product_class_name_snapshot VARCHAR(160)
            NOT NULL;
        ALTER TABLE sale_return_lines ADD COLUMN disposition_code VARCHAR(32) NOT NULL;
        ALTER TABLE sale_return_lines ADD CONSTRAINT
            ck_sale_return_lines_ck_sale_return_lines_disposition_valid CHECK(disposition_code IN
            ('RESTOCK_COUNTER','RESTOCK_BACKROOM','SEND_TO_WASTE'));
        """
    )
