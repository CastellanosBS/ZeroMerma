# apps/backend/scripts/bootstrap_inventory_balance.ps1
# PURPOSE:
#   Bootstrap (or re-sync) inventory_balance from inventory_movement ledger.
#
# PROPERTIES:
#   - Idempotent: safe to run multiple times.
#   - Uses current DATABASE_URL via your app settings/engine.
#
# HOW IT WORKS:
#   1) Insert missing (branch_id, product_id) pairs from ledger into snapshot with 0.
#   2) Update snapshot.on_hand = SUM(ledger.qty) for every pair.
#
# USAGE (from apps/backend):
#   .\scripts\bootstrap_inventory_balance.ps1

@"
from sqlalchemy import text
from zeromerma_api.db.engine import engine

SQL = '''
-- 1) Ensure snapshot rows exist for every pair seen in ledger
INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
SELECT im.branch_id, im.product_id, 0, 0, now(), now()
FROM inventory_movement im
GROUP BY im.branch_id, im.product_id
ON CONFLICT (branch_id, product_id) DO NOTHING;

-- 2) Recompute on_hand from the ledger
UPDATE inventory_balance ib
SET on_hand = COALESCE(src.on_hand, 0),
    updated_at = now()
FROM (
    SELECT branch_id, product_id, SUM(qty) AS on_hand
    FROM inventory_movement
    GROUP BY branch_id, product_id
) AS src
WHERE ib.branch_id = src.branch_id
  AND ib.product_id = src.product_id;

-- 3) Optional: if you want to zero-out snapshot rows that have no ledger history,
-- you can do it here. We skip it to avoid surprising changes.

-- 4) Return a quick summary
SELECT COUNT(*) AS rows_in_inventory_balance FROM inventory_balance;
'''

with engine.begin() as conn:
    rows = conn.execute(text(SQL)).fetchall()

# Some drivers return the last SELECT results; print them if present
if rows:
    print("Bootstrap summary:", rows)
else:
    print("Bootstrap done (no summary returned).")
"@ | poetry run python
