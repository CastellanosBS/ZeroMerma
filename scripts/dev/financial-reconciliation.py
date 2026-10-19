"""Diagnose/dry-run by default; apply exact approved evidence in a controlled window."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.financial_ledger.application.reconciliation import (
    apply_financial_import_row,
    diagnose_financial_state,
    dry_run_financial_import,
)
from zeromerma_api.modules.financial_ledger.domain.money import FinancialModelError
from zeromerma_api.modules.financial_ledger.domain.reconciliation import FinancialImportManifest
from zeromerma_api.modules.identity.application.schemas import LoginRequest
from zeromerma_api.modules.identity.application.session_services import SessionService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("diagnose", "dry-run", "apply"))
    parser.add_argument("--branch-id", type=UUID)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--controlled-window-confirmed", action="store_true")
    parser.add_argument("--row-key", help="Apply one row; omit to resume all reviewed rows.")
    args = parser.parse_args()
    if args.mode == "diagnose":
        if args.branch_id is None:
            parser.error("diagnose requires --branch-id")
        with SessionLocal() as session:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            result = diagnose_financial_state(session, branch_id=args.branch_id)
            print(json.dumps(result, indent=2))
        return
    if args.manifest is None:
        parser.error("dry-run and apply require --manifest")
    manifest = FinancialImportManifest.model_validate_json(
        args.manifest.read_text(encoding="utf-8")
    )
    if args.mode == "dry-run":
        with SessionLocal() as session:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            print(json.dumps(dry_run_financial_import(session, manifest=manifest), indent=2))
        return
    if not args.controlled_window_confirmed or args.expected_manifest_sha256 != manifest.digest():
        parser.error("apply requires the exact dry-run hash and --controlled-window-confirmed")
    manifest.require_productive_source()
    if args.row_key is not None and args.row_key not in {row.row_key for row in manifest.rows}:
        parser.error("--row-key must identify a row in the reviewed manifest")
    # Credentials are read only from the terminal, never from arguments or the manifest.
    email = input("Authorized owner email: ")
    password = getpass.getpass("Password: ")
    request_id = str(uuid4())
    sessions = SessionService()
    with SessionLocal() as authentication_session:
        authentication = sessions.login(
            authentication_session,
            LoginRequest(email=email, password=password, audience="BACKOFFICE"),
            ip="127.0.0.1",
            request_id=request_id,
        )
        del password
        try:
            for row in manifest.rows:
                if args.row_key is not None and row.row_key != args.row_key:
                    continue
                with SessionLocal() as session:
                    active_authentication = sessions.authenticate(
                        session,
                        credential=authentication.credential,
                        audience="BACKOFFICE",
                        request_id=request_id,
                    )
                    applied = apply_financial_import_row(
                        session,
                        current_user=active_authentication.user,
                        manifest=manifest,
                        row_key=row.row_key,
                        expected_manifest_sha256=args.expected_manifest_sha256,
                        controlled_window_confirmed=True,
                    )
                    print(
                        json.dumps(
                            {
                                "row_key": row.row_key,
                                "replayed": applied.replayed,
                                "result": applied.payload,
                            }
                        )
                    )
        finally:
            sessions.logout(authentication_session, authentication, request_id)


if __name__ == "__main__":
    try:
        main()
    except (FinancialModelError, ValidationError, HTTPException) as error:
        print(f"Financial reconciliation rejected: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    except Exception as error:
        print(
            f"Financial reconciliation failed ({type(error).__name__}); "
            "inspect protected diagnostics.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
