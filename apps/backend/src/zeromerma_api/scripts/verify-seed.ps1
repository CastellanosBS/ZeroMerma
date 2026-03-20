# apps/backend/src/zeromerma_api/scripts/verify-seed.ps1
# PURPOSE:
#   Verify deterministic seed invariants:
#   - Categories exist
#   - Products have uom populated
#   - Snapshot (inventory_balance) matches ledger aggregation (inventory_movement)

$ErrorActionPreference = "Stop"

@"
from sqlalchemy import text
from zeromerma_api.db.engine import engine

def scalar(q, params=None):
    with engine.connect() as c:
        return c.execute(text(q), params or {}).scalar()

cat_count = scalar("SELECT COUNT(*) FROM product_category")
prod_count = scalar("SELECT COUNT(*) FROM product")
uom_null = scalar("SELECT COUNT(*) FROM product WHERE uom IS NULL")
neg_bal = scalar("SELECT COUNT(*) FROM inventory_balance WHERE on_hand < 0")

mismatch = scalar(r'''
SELECT COUNT(*) FROM (
  SELECT
    b.branch_id,
    b.product_id,
    b.on_hand,
    COALESCE(m.sum_qty, 0) AS ledger_qty
  FROM inventory_balance b
  LEFT JOIN (
    SELECT branch_id, product_id, SUM(qty) AS sum_qty
    FROM inventory_movement
    GROUP BY branch_id, product_id
  ) m
  ON m.branch_id = b.branch_id AND m.product_id = b.product_id
  WHERE b.on_hand <> COALESCE(m.sum_qty, 0)
) t
''')

print("product_category count:", cat_count)
print("product count:", prod_count)
print("product uom IS NULL:", uom_null)
print("inventory_balance negative on_hand:", neg_bal)
print("snapshot != ledger mismatches:", mismatch)

# Hard fail if invariants are violated
assert cat_count > 0, "Expected product_category to be seeded."
assert prod_count > 0, "Expected product to be seeded."
assert uom_null == 0, "Expected product.uom to be populated for all products."
assert neg_bal == 0, "inventory_balance has negative on_hand rows."
assert mismatch == 0, "inventory_balance snapshot does not match inventory_movement ledger."
print("OK: seed invariants satisfied.")
"@ | poetry run python
