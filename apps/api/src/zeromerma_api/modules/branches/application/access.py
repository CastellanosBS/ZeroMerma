from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAssignmentRequiredError,
    BranchInactiveError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
)
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.identity.infrastructure.models import UserBranchAssignment


@dataclass(frozen=True)
class WorkstationContext:
    branch_id: UUID
    branch_code: str
    branch_name: str
    branch_timezone: str
    branch_is_active: bool
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    workstation_is_active: bool


class WorkstationAccessService:
    def resolve_context(
        self,
        session: Session,
        *,
        user_id: UUID,
        workstation_code: str,
    ) -> WorkstationContext:
        statement = (
            select(
                Branch.id.label("branch_id"),
                Branch.code.label("branch_code"),
                Branch.name.label("branch_name"),
                Branch.timezone.label("branch_timezone"),
                Branch.is_active.label("branch_is_active"),
                Workstation.id.label("workstation_id"),
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                Workstation.is_active.label("workstation_is_active"),
            )
            .select_from(Workstation)
            .join(Branch, Branch.id == Workstation.branch_id)
            .where(Workstation.code == workstation_code)
        )
        result = session.execute(statement).mappings().one_or_none()

        if result is None:
            raise WorkstationNotFoundError(f"Workstation {workstation_code} was not found.")

        if not result["branch_is_active"]:
            raise BranchInactiveError(f"Branch for workstation {workstation_code} is inactive.")

        if not result["workstation_is_active"]:
            raise WorkstationInactiveError(f"Workstation {workstation_code} is inactive.")

        assignment = session.execute(
            select(UserBranchAssignment.id).where(
                UserBranchAssignment.user_id == user_id,
                UserBranchAssignment.branch_id == result["branch_id"],
                UserBranchAssignment.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if assignment is None:
            raise BranchAssignmentRequiredError(
                f"User is not assigned to branch {result['branch_code']}."
            )

        return WorkstationContext(
            branch_id=result["branch_id"],
            branch_code=result["branch_code"],
            branch_name=result["branch_name"],
            branch_timezone=result["branch_timezone"],
            branch_is_active=result["branch_is_active"],
            workstation_id=result["workstation_id"],
            workstation_code=result["workstation_code"],
            workstation_name=result["workstation_name"],
            workstation_is_active=result["workstation_is_active"],
        )
