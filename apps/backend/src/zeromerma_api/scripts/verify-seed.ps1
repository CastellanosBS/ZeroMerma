# apps/backend/scripts/verify-seed.ps1
# Verifies dev seed invariants:
# - basic counts exist
# - ledger matches snapshot

$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $BackendRoot

$EnvFile = Join-Path $BackendRoot ".env"
if (-not $env:DATABASE_URL) {
  if (Test-Path $EnvFile) {
    $line = Get-Content $EnvFile | Select-String '^DATABASE_URL=' | Select-Object -First 1
    if ($line) {
      $env:DATABASE_URL = $line.ToString().Split('=',2)[1].Trim()
    }
  } else {
    Write-Warning "No .env found at $EnvFile. Assuming DATABASE_URL is already configured in environment."
  }
}

@"
from decimal import Decimal
from sqlalchemy import text
from zeromerma_api.db.engine import engine

def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)

with engine.connect() as c:
    db = c.execute(text("select current_database()")).scalar()
    ip = c.execute(text("select inet_server_addr()")).scalar()
    ver = c.execute(text("select version()")).scalar().splitlines()[0]
    print(f"current_database: {db}")
    print(f"inet_server_addr: {ip}")
    print(f"version: {ver}")

    counts = c.execute(text(r'''
        SELECT
          (SELECT count(*) FROM branch) AS branch_count,
          (SELECT count(*) FROM role) AS role_count,
          (SELECT count(*) FROM user_account) AS user_count,
          (SELECT count(*) FROM product) AS product_count,
          (SELECT count(*) FROM inventory_movement) AS movement_count,
          (SELECT count(*) FROM inventory_balance) AS balance_count,
          (SELECT count(*) FROM cash_session) AS cash_session_count,
          (SELECT count(*) FROM sale) AS sale_count,
          (SELECT count(*) FROM sale_item) AS sale_item_count,
          (SELECT count(*) FROM payment) AS payment_count
    ''')).mappings().one()

    print("counts:", dict(counts))

    assert_true(counts["branch_count"] >= 1, "Expected at least 1 branch.")
    assert_true(counts["role_count"] >= 2, "Expected at least 2 roles.")
    assert_true(counts["user_count"] >= 1, "Expected at least 1 user_account.")
    assert_true(counts["product_count"] >= 1, "Expected at least 1 product.")
    assert_true(counts["balance_count"] >= 1, "Expected at least 1 inventory_balance row.")

    tol = Decimal("0.001")

    mismatches = c.execute(text(r'''
        WITH ledger AS (
          SELECT branch_id, product_id, COALESCE(SUM(qty), 0) AS ledger_on_hand
          FROM inventory_movement
          GROUP BY branch_id, product_id
        )
        SELECT
          b.branch_id,
          b.product_id,
          b.on_hand AS snapshot_on_hand,
          COALESCE(l.ledger_on_hand, 0) AS ledger_on_hand,
          (b.on_hand - COALESCE(l.ledger_on_hand, 0)) AS diff
        FROM inventory_balance b
        LEFT JOIN ledger l
          ON l.branch_id = b.branch_id AND l.product_id = b.product_id
        WHERE ABS(b.on_hand - COALESCE(l.ledger_on_hand, 0)) > :tol
        ORDER BY b.branch_id, b.product_id
    '''), {"tol": float(tol)}).mappings().all()

    if mismatches:
        print("MISMATCHES (snapshot vs ledger):")
        for row in mismatches:
            print(dict(row))
        raise AssertionError(f"Inventory snapshot mismatch count={len(mismatches)}")
    else:
        print("OK: inventory_balance matches inventory_movement ledger (within tolerance).")

print("VERIFY_SEED: PASS")
"@ | poetry run python
