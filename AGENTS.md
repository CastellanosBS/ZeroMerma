# ZeroMerma - Codex Working Rules

## Mission
Build ZeroMerma as a clean greenfield platform for multi-branch bakery operations.

## Non-negotiables
- No legacy compatibility layers
- No parallel architectures
- No drift between backend and frontend contracts
- Backend is the only source of truth for contracts
- Separate POS web and backoffice web
- Independent Python worker
- Transactional outbox
- Full audit trail for sensitive operations
- English for code, file names, technical comments, and implementation prompts

## Business rules
- Official sale capture modes: PRODUCT_DIRECT and CLASS_CAPTURE
- PRODUCT_DIRECT = immediate financial capture + direct physical attribution
- CLASS_CAPTURE = immediate financial capture + deferred physical attribution resolved at close
- Cash session opening is mandatory before operating
- Cash session closing is mandatory
- Sensitive operations must be auditable
- Critical operations must leave useful traces for analytics and future AI/ML

## Architecture defaults
- Modular monolith backend
- PostgreSQL as canonical database
- FastAPI + Pydantic v2 + SQLAlchemy 2.x + Alembic
- React + Vite + TypeScript for web apps
- TanStack Router + TanStack Query + Zustand
- Tailwind + shadcn/ui
- Worker based on the transactional outbox
- No microservices
- No handwritten shared domain types across Python and TypeScript

## Mandatory execution protocol
1. Inspect the repository before making changes.
2. Return a short plan.
3. List files to create, modify, and delete.
4. Implement canonically.
5. Run validation commands.
6. Report results, remaining risks, and follow-up actions.

## Quality bar
- Keep modules cohesive
- Prefer deletion over coexistence
- Keep naming explicit
- Avoid generic dumping-ground folders
- Leave scripts for validation and local execution
