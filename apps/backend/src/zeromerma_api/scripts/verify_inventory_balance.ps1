# apps/backend/scripts/verify_inventory_balance.ps1
# PURPOSE:
#   Verify snapshot matches ledger sums for all (branch_id, product_id) pairs.

@"
from sqlalchemy import text
from zeromerma_api.db.engine import engine

SQL = '''
WITH ledger AS (
  SELECT branch_id, product_id, COALESCE(SUM(qty),0) AS ledger_on_hand
  FROM inventory_movement
  GROUP BY branch_id, product_id
)
SELECT
  ib.branch_id,
  ib.product_id,
  ib.on_hand AS snapshot_on_hand,
  l.ledger_on_hand,
  (ib.on_hand - l.ledger_on_hand) AS diff
FROM inventory_balance ib
JOIN ledger l
  ON l.branch_id = ib.branch_id AND l.product_id = ib.product_id
WHERE (ib.on_hand - l.ledger_on_hand) <> 0
ORDER BY ib.branch_id, ib.product_id;
'''

with engine.connect() as conn:
    rows = conn.execute(text(SQL)).fetchall()
    if not rows:
        print("OK: inventory_balance matches ledger for all pairs.")
    else:
        print("MISMATCH rows:")
        for r in rows:
            print(r)
"@ | poetry run python
