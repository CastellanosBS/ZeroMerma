# Training Mode

## Chosen architecture

ZeroMerma training mode uses an explicit backend flag plus a separate local environment backed by a separate PostgreSQL database.

This is the safest canonical approach for the current architecture because it avoids mixing sandbox operations with live operational data, audit trails, outbox events, and cash-session state.

The training flow uses the same backend contracts and the same POS shell, but it must point to a dedicated database and worker process.

## Safeguards

- Backend flag: `ZEROMERMA_API_TRAINING_MODE_ENABLED=true`
- Backend label: `ZEROMERMA_API_TRAINING_MODE_LABEL=Modo entrenamiento`
- Backend validation rejects training mode in production.
- POS bootstrap exposes `training_mode`, and the POS shell shows a global `Modo entrenamiento` banner.
- Training mode does not silently mix with operational data because the recommended setup uses a separate database for both API and worker.
- The worker must use the same training database so outbox processing also stays isolated.

## What training mode does today

- Shows a visible POS banner: `Modo entrenamiento`
- Keeps the backend as the source of truth for the banner state
- Reuses the canonical local seed against a dedicated training database

## What training mode does not do today

- It does not create a separate contract surface.
- It does not introduce a parallel training tenant model.
- It does not fake operational success or bypass backend persistence.
- It does not allow production-mode training.

## Local setup

Create a dedicated `.env.training` at the repository root with a separate database for API and worker.

Example:

```env
ZEROMERMA_API_ENVIRONMENT=local
ZEROMERMA_API_DATABASE_URL=postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma_training
ZEROMERMA_API_TRAINING_MODE_ENABLED=true
ZEROMERMA_API_TRAINING_MODE_LABEL=Modo entrenamiento

ZEROMERMA_WORKER_ENVIRONMENT=local
ZEROMERMA_WORKER_DATABASE_URL=postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma_training
```

Apply migrations and seed the training database:

```powershell
Copy-Item .env.training .env
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api python scripts/bootstrap/seed-training-data.py
```

Start API and worker against the training database:

```powershell
uv run --project apps/api uvicorn zeromerma_api.main:create_app --factory --app-dir apps/api/src --reload --host 0.0.0.0 --port 8001
uv run --project apps/worker python -m zeromerma_worker
```

Point the POS app to the training API:

```powershell
Copy-Item apps\pos-web\.env.example apps\pos-web\.env.training
```

Set:

```env
VITE_API_BASE_URL=http://localhost:8001
VITE_POS_WORKSTATION_CODE=POS-01
```

Then start the POS app:

```powershell
corepack pnpm --filter @zeromerma/pos-web dev -- --mode training
```

If you do not want a dedicated frontend mode file, you can also place the same values in `apps/pos-web/.env`.

## Operational note

The canonical local workstation code stays the same (`POS-01`), but it is safe in training mode because the API and worker are connected to a separate database.

That isolation is the real safeguard. The banner is only the user-facing warning layer.
