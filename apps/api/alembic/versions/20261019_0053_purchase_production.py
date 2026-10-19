"""Freeze purchase evidence and release production plans with explicit reconciliation."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261019_0053_purchase_prod"
down_revision = "20261019_0052_transit_resolution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("production_batches", "started_at", new_column_name="released_at")
    op.alter_column(
        "production_batches", "started_by_user_id", new_column_name="released_by_user_id"
    )
    op.add_column(
        "purchase_receipt_lines", sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_purchase_receipt_line_lot",
        "purchase_receipt_lines",
        "inventory_lots",
        ["lot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "products",
        sa.Column("is_usable_as_input", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE products SET is_usable_as_input=true WHERE product_kind='RAW_MATERIAL' "
        "OR id IN (SELECT input_product_id FROM recipe_inputs)"
    )
    op.add_column("purchase_document_lines", sa.Column("source_unit_of_measure", sa.String(32)))
    op.add_column("purchase_document_lines", sa.Column("conversion_factor", sa.Numeric(18, 6)))
    op.add_column("purchase_document_lines", sa.Column("ordered_quantity_base", sa.Numeric(18, 3)))
    op.execute(
        "UPDATE purchase_document_lines SET source_unit_of_measure=unit_of_measure, "
        "conversion_factor=1, ordered_quantity_base=ordered_quantity"
    )
    for name in ("source_unit_of_measure", "conversion_factor", "ordered_quantity_base"):
        op.alter_column("purchase_document_lines", name, nullable=False)
    for name, kind in (
        ("source_unit_of_measure", sa.String(32)),
        ("conversion_factor", sa.Numeric(18, 6)),
        ("received_quantity_base", sa.Numeric(18, 3)),
        ("base_unit_of_measure", sa.String(32)),
        ("base_unit_cost", sa.Numeric(18, 8)),
    ):
        op.add_column("purchase_receipt_lines", sa.Column(name, kind))
    op.execute("""UPDATE purchase_receipt_lines r SET source_unit_of_measure=l.unit_of_measure,
        conversion_factor=1, received_quantity_base=r.received_quantity,
        base_unit_of_measure=l.unit_of_measure, base_unit_cost=r.unit_cost
        FROM purchase_document_lines l WHERE l.id=r.purchase_line_id""")
    for name in (
        "source_unit_of_measure",
        "conversion_factor",
        "received_quantity_base",
        "base_unit_of_measure",
        "base_unit_cost",
    ):
        op.alter_column("purchase_receipt_lines", name, nullable=False)
    op.create_index(
        "uq_purchase_supplier_invoice",
        "purchase_documents",
        ["supplier_id", sa.text("upper(btrim(external_document_number))")],
        unique=True,
        postgresql_where=sa.text(
            "external_document_type = 'INVOICE' AND external_document_number IS NOT NULL"
        ),
    )
    op.create_table(
        "purchase_receipt_reversals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "purchase_receipt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_receipts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("purchase_receipt_id", name="uq_purchase_receipt_reversal_original"),
    )
    for name, kind, default, nullable in (
        ("plan_status", sa.String(32), "DRAFT", False),
        ("run_id", postgresql.UUID(as_uuid=True), None, True),
        ("run_status", sa.String(32), None, True),
        ("recipe_snapshot", postgresql.JSONB(), None, True),
        ("reconciliation_evidence", sa.String(32), None, True),
        ("reconciliation_reason", sa.String(500), None, True),
        ("output_lot_code", sa.String(120), None, True),
        ("output_expires_at", sa.DateTime(timezone=True), None, True),
        ("reconciliation_finish_as", sa.String(32), None, True),
    ):
        op.add_column(
            "production_batches", sa.Column(name, kind, nullable=nullable, server_default=default)
        )
    op.create_unique_constraint("uq_production_batches_run_id", "production_batches", ["run_id"])
    op.drop_constraint("ck_production_batches_status_valid", "production_batches", type_="check")
    # Historic plans have no fabricated frozen recipe/reservation or physical start evidence.
    op.execute(
        "UPDATE production_batches SET status='PENDING_RECONCILIATION', run_id=id, "
        "run_status='PENDING_RECONCILIATION' WHERE status='IN_PROGRESS'"
    )
    op.execute(
        "UPDATE production_batches SET plan_status=CASE WHEN status='CANCELLED' THEN "
        "'CANCELLED' WHEN status IN ('COMPLETED','PENDING_RECONCILIATION') THEN "
        "'RELEASED' ELSE 'DRAFT' END"
    )
    op.create_check_constraint(
        "ck_production_batches_status_valid",
        "production_batches",
        "status IN ('DRAFT','RELEASED','PENDING_RECONCILIATION','COMPLETED','CANCELLED')",
    )
    for name, kind in (
        ("returned_qty", sa.Numeric(12, 3)),
        ("waste_qty", sa.Numeric(12, 3)),
        ("remainder_qty", sa.Numeric(12, 3)),
        ("reconciliation_reason", sa.String(500)),
        ("reservation_id", postgresql.UUID(as_uuid=True)),
        ("input_code_snapshot", sa.String(64)),
        ("input_name_snapshot", sa.String(160)),
        ("recipe_input_id", postgresql.UUID(as_uuid=True)),
    ):
        op.add_column("production_batch_inputs", sa.Column(name, kind))
    op.create_foreign_key(
        "fk_production_input_reservation",
        "production_batch_inputs",
        "inventory_reservations",
        ["reservation_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute("""
    CREATE FUNCTION zeromerma_preserve_purchase_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Purchase receipt evidence is immutable' USING ERRCODE='23514'; END $$""")
    for table in ("purchase_receipts", "purchase_receipt_lines", "purchase_receipt_reversals"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR "
            f"EACH ROW EXECUTE FUNCTION zeromerma_preserve_purchase_evidence()"
        )
    op.execute("""
    CREATE FUNCTION zeromerma_preserve_released_recipe() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE recipe_key uuid;
    BEGIN
      IF TG_TABLE_NAME='recipes' THEN
        recipe_key := OLD.id;
        IF TG_OP='UPDATE' AND
        ROW(NEW.product_id,NEW.version_name,NEW.yield_qty,NEW.yield_uom) IS NOT DISTINCT
        FROM ROW(OLD.product_id,OLD.version_name,OLD.yield_qty,OLD.yield_uom) THEN RETURN
        NEW; END IF;
      ELSE
        IF TG_OP='INSERT' THEN recipe_key:=NEW.recipe_id; ELSE recipe_key:=OLD.recipe_id; END IF;
        IF TG_OP='UPDATE' AND NEW.recipe_id IS DISTINCT FROM OLD.recipe_id AND EXISTS(
          SELECT 1 FROM production_batches WHERE recipe_id=NEW.recipe_id AND recipe_snapshot
        IS NOT NULL
        ) THEN RAISE EXCEPTION 'Released recipe versions are immutable' USING
        ERRCODE='23514'; END IF;
      END IF;
      IF EXISTS(SELECT 1 FROM production_batches WHERE recipe_id=recipe_key AND
        recipe_snapshot IS NOT NULL) THEN
        RAISE EXCEPTION 'Released recipe versions are immutable' USING ERRCODE='23514';
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$""")
    op.execute(
        "CREATE TRIGGER trg_released_recipe_immutable BEFORE UPDATE OR DELETE ON "
        "recipes FOR EACH ROW EXECUTE FUNCTION zeromerma_preserve_released_recipe()"
    )
    op.execute(
        "CREATE TRIGGER trg_released_recipe_inputs_immutable BEFORE INSERT OR UPDATE "
        "OR DELETE ON recipe_inputs FOR EACH ROW EXECUTE FUNCTION "
        "zeromerma_preserve_released_recipe()"
    )
    op.execute("""
    CREATE FUNCTION zeromerma_preserve_production_plan() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME='production_batches' THEN
        IF OLD.recipe_snapshot IS NOT NULL AND (TG_OP='DELETE' OR
ROW(NEW.product_id,NEW.recipe_id,NEW.branch_id,NEW.planned_output_qty,NEW.recipe_snapshot,NEW.run_id)
          IS DISTINCT FROM
        ROW(OLD.product_id,OLD.recipe_id,OLD.branch_id,OLD.planned_output_qty,OLD.recipe_snapshot,OLD.run_id))
        THEN
          RAISE EXCEPTION 'Released production plans are immutable' USING ERRCODE='23514';
        END IF;
      ELSE
        IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM production_batches WHERE
        id=NEW.production_batch_id AND recipe_snapshot IS NOT NULL) THEN
          RAISE EXCEPTION 'Released input plans cannot gain new lines' USING ERRCODE='23514';
        END IF;
        IF TG_OP='INSERT' THEN RETURN NEW; END IF;
        IF TG_OP='UPDATE' AND NEW.production_batch_id IS DISTINCT FROM OLD.production_batch_id
          AND EXISTS(SELECT 1 FROM production_batches WHERE id=NEW.production_batch_id
          AND recipe_snapshot IS NOT NULL) THEN
          RAISE EXCEPTION 'Released input plans cannot gain lines' USING ERRCODE='23514';
        END IF;
        IF EXISTS(SELECT 1 FROM production_batches WHERE id=OLD.production_batch_id AND
        recipe_snapshot IS NOT NULL)
          AND (TG_OP='DELETE' OR
        ROW(NEW.production_batch_id,NEW.input_product_id,NEW.required_qty,NEW.unit_of_measure,
        NEW.standard_cost_snapshot,NEW.reservation_id,NEW.input_code_snapshot,
        NEW.input_name_snapshot,NEW.recipe_input_id)
          IS DISTINCT FROM
        ROW(OLD.production_batch_id,OLD.input_product_id,OLD.required_qty,OLD.unit_of_measure,
        OLD.standard_cost_snapshot,OLD.reservation_id,OLD.input_code_snapshot,
        OLD.input_name_snapshot,OLD.recipe_input_id))
        THEN
          RAISE EXCEPTION 'Released production input plans are immutable' USING ERRCODE='23514';
        END IF;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$""")
    for table in ("production_batches", "production_batch_inputs"):
        events = (
            "INSERT OR UPDATE OR DELETE"
            if table == "production_batch_inputs"
            else "UPDATE OR DELETE"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table}_plan_immutable BEFORE {events} ON {table} FOR "
            f"EACH ROW EXECUTE FUNCTION zeromerma_preserve_production_plan()"
        )


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM purchase_receipt_reversals)
      OR EXISTS(SELECT 1 FROM purchase_receipt_lines WHERE lot_id IS NOT NULL
        OR conversion_factor <> 1 OR source_unit_of_measure <> base_unit_of_measure
        OR received_quantity_base <> received_quantity OR base_unit_cost <> unit_cost)
      OR EXISTS(SELECT 1 FROM production_batches WHERE run_id IS NOT NULL
        OR recipe_snapshot IS NOT NULL OR reconciliation_evidence IS NOT NULL
        OR reconciliation_reason IS NOT NULL OR output_lot_code IS NOT NULL
        OR output_expires_at IS NOT NULL OR reconciliation_finish_as IS NOT NULL)
      OR EXISTS(SELECT 1 FROM production_batch_inputs WHERE reservation_id IS NOT NULL
        OR returned_qty IS NOT NULL OR waste_qty IS NOT NULL OR remainder_qty IS NOT NULL
        OR reconciliation_reason IS NOT NULL)
      OR EXISTS(SELECT 1 FROM products p WHERE is_usable_as_input IS DISTINCT FROM
        (product_kind='RAW_MATERIAL' OR EXISTS(
          SELECT 1 FROM recipe_inputs r WHERE r.input_product_id=p.id)))
      THEN RAISE EXCEPTION
        'Purchase/production inventory evidence requires explicit archival before downgrade'
        USING ERRCODE='23514';
      END IF;
    END $$""")
    op.alter_column("production_batches", "released_at", new_column_name="started_at")
    op.alter_column(
        "production_batches", "released_by_user_id", new_column_name="started_by_user_id"
    )
    op.drop_constraint("fk_purchase_receipt_line_lot", "purchase_receipt_lines", type_="foreignkey")
    op.drop_column("purchase_receipt_lines", "lot_id")
    for table in ("production_batches", "production_batch_inputs"):
        op.execute(f"DROP TRIGGER trg_{table}_plan_immutable ON {table}")
    op.execute("DROP FUNCTION zeromerma_preserve_production_plan()")
    op.execute("DROP TRIGGER trg_released_recipe_immutable ON recipes")
    op.execute("DROP TRIGGER trg_released_recipe_inputs_immutable ON recipe_inputs")
    op.execute("DROP FUNCTION zeromerma_preserve_released_recipe()")
    for table in ("purchase_receipts", "purchase_receipt_lines", "purchase_receipt_reversals"):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION zeromerma_preserve_purchase_evidence()")
    op.drop_constraint(
        "fk_production_input_reservation", "production_batch_inputs", type_="foreignkey"
    )
    for name in (
        "returned_qty",
        "waste_qty",
        "remainder_qty",
        "reconciliation_reason",
        "reservation_id",
        "input_code_snapshot",
        "input_name_snapshot",
        "recipe_input_id",
    ):
        op.drop_column("production_batch_inputs", name)
    op.drop_constraint("ck_production_batches_status_valid", "production_batches", type_="check")
    op.execute(
        "UPDATE production_batches SET status='IN_PROGRESS' WHERE status IN "
        "('RELEASED','PENDING_RECONCILIATION')"
    )
    op.create_check_constraint(
        "ck_production_batches_status_valid",
        "production_batches",
        "status IN ('DRAFT','IN_PROGRESS','COMPLETED','CANCELLED')",
    )
    op.drop_constraint("uq_production_batches_run_id", "production_batches", type_="unique")
    for name in (
        "plan_status",
        "run_id",
        "run_status",
        "recipe_snapshot",
        "reconciliation_evidence",
        "reconciliation_reason",
        "output_lot_code",
        "output_expires_at",
        "reconciliation_finish_as",
    ):
        op.drop_column("production_batches", name)
    op.drop_table("purchase_receipt_reversals")
    op.drop_index("uq_purchase_supplier_invoice", "purchase_documents")
    for name in (
        "source_unit_of_measure",
        "conversion_factor",
        "received_quantity_base",
        "base_unit_of_measure",
        "base_unit_cost",
    ):
        op.drop_column("purchase_receipt_lines", name)
    for name in ("source_unit_of_measure", "conversion_factor", "ordered_quantity_base"):
        op.drop_column("purchase_document_lines", name)
    op.drop_column("products", "is_usable_as_input")
