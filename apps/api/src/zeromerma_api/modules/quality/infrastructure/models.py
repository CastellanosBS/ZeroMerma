from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.quality.domain.constants import (
    CLEANING_AREA_TYPE_OTHER,
    CLEANING_FREQUENCY_AS_NEEDED,
    CLEANING_LOG_STATUS_PENDING,
    CLEANING_RISK_MEDIUM,
    CLEANING_SHIFT_MORNING,
    CLEANING_TYPE_ROUTINE,
    EQUIPMENT_AREA_TYPE_OTHER,
    EQUIPMENT_STATUS_OPERATIONAL,
    EQUIPMENT_TYPE_OTHER,
    INCIDENT_SEVERITY_MEDIUM,
    INCIDENT_SOURCE_MANUAL,
    INCIDENT_STATUS_OPEN,
    INCIDENT_TYPE_OTHER,
    MAINTENANCE_RESULT_NOT_COMPLETED,
    MAINTENANCE_STATUS_PENDING,
    MAINTENANCE_TYPE_PREVENTIVE,
    SANITARY_ITEM_RESULT_PENDING,
    SANITARY_PROCESS_OTHER,
    SANITARY_RESULT_NOT_EVALUATED,
    SANITARY_STATUS_PENDING,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class CleaningTemplate(Base):
    __tablename__ = "cleaning_templates"
    __table_args__ = (
        CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name="ck_cleaning_templates_area_type_valid",
        ),
        CheckConstraint(
            "frequency IN ('PER_SHIFT', 'DAILY', 'WEEKLY', 'MONTHLY', 'AS_NEEDED')",
            name="ck_cleaning_templates_frequency_valid",
        ),
        CheckConstraint(
            "cleaning_type IN ('ROUTINE', 'DEEP_CLEANING', 'EQUIPMENT', 'SANITATION', "
            "'SPILL_RESPONSE', 'OTHER')",
            name="ck_cleaning_templates_type_valid",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_cleaning_templates_risk_level_valid",
        ),
        CheckConstraint(
            "estimated_duration_minutes IS NULL OR estimated_duration_minutes >= 0",
            name="ck_cleaning_templates_duration_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_type: Mapped[str] = mapped_column(
        String(40), default=CLEANING_AREA_TYPE_OTHER, nullable=False
    )
    frequency: Mapped[str] = mapped_column(
        String(32), default=CLEANING_FREQUENCY_AS_NEEDED, nullable=False
    )
    cleaning_type: Mapped[str] = mapped_column(
        String(40), default=CLEANING_TYPE_ROUTINE, nullable=False
    )
    method_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_tools: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(16), default=CLEANING_RISK_MEDIUM, nullable=False
    )
    requires_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class CleaningTemplateItem(Base):
    __tablename__ = "cleaning_template_items"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "display_order",
            name="uq_cleaning_template_items_template_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cleaning_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class CleaningLog(Base):
    __tablename__ = "cleaning_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'MISSED', "
            "'CANCELLED', 'REQUIRES_REVIEW')",
            name="ck_cleaning_logs_status_valid",
        ),
        CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name="ck_cleaning_logs_area_type_valid",
        ),
        CheckConstraint(
            "frequency IS NULL OR frequency IN ("
            "'PER_SHIFT', 'DAILY', 'WEEKLY', 'MONTHLY', 'AS_NEEDED'"
            ")",
            name="ck_cleaning_logs_frequency_valid",
        ),
        CheckConstraint(
            "cleaning_type IN ('ROUTINE', 'DEEP_CLEANING', 'EQUIPMENT', 'SANITATION', "
            "'SPILL_RESPONSE', 'OTHER')",
            name="ck_cleaning_logs_type_valid",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_cleaning_logs_risk_level_valid",
        ),
        CheckConstraint(
            "shift_code IN ('MORNING', 'AFTERNOON', 'NIGHT', 'MIXED')",
            name="ck_cleaning_logs_shift_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    area_name: Mapped[str] = mapped_column(String(160), nullable=False)
    area_type: Mapped[str] = mapped_column(
        String(40), default=CLEANING_AREA_TYPE_OTHER, nullable=False
    )
    equipment_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    task_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cleaning_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_name: Mapped[str] = mapped_column(String(160), nullable=False)
    cleaning_type: Mapped[str] = mapped_column(
        String(40), default=CLEANING_TYPE_ROUTINE, nullable=False
    )
    frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(16), default=CLEANING_RISK_MEDIUM, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=CLEANING_LOG_STATUS_PENDING, nullable=False
    )
    shift_code: Mapped[str] = mapped_column(
        String(32), default=CLEANING_SHIFT_MORNING, nullable=False
    )
    responsible_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class CleaningLogChecklistItem(Base):
    __tablename__ = "cleaning_log_checklist_items"
    __table_args__ = (
        UniqueConstraint(
            "cleaning_log_id",
            "display_order",
            name="uq_cleaning_log_checklist_items_log_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    cleaning_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cleaning_logs.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cleaning_template_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SanitaryVerificationTemplate(Base):
    __tablename__ = "sanitary_verification_templates"
    __table_args__ = (
        CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name="ck_sanitary_verification_templates_area_type_valid",
        ),
        CheckConstraint(
            "process_type IN ('STORAGE', 'PRODUCTION', 'DISPLAY', 'EQUIPMENT', "
            "'SANITATION', 'OTHER')",
            name="ck_sanitary_verification_templates_process_type_valid",
        ),
        CheckConstraint(
            "frequency IN ('PER_SHIFT', 'DAILY', 'WEEKLY', 'MONTHLY', 'AS_NEEDED')",
            name="ck_sanitary_verification_templates_frequency_valid",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_sanitary_verification_templates_risk_level_valid",
        ),
        CheckConstraint(
            "pass_threshold_percent >= 0 AND pass_threshold_percent <= 100",
            name="ck_sanitary_verification_templates_threshold_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_type: Mapped[str] = mapped_column(
        String(40), default=CLEANING_AREA_TYPE_OTHER, nullable=False
    )
    process_type: Mapped[str] = mapped_column(
        String(40), default=SANITARY_PROCESS_OTHER, nullable=False
    )
    frequency: Mapped[str] = mapped_column(
        String(32), default=CLEANING_FREQUENCY_AS_NEEDED, nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(16), default=CLEANING_RISK_MEDIUM, nullable=False
    )
    pass_threshold_percent: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    requires_evidence_on_failure: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SanitaryVerificationTemplateItem(Base):
    __tablename__ = "sanitary_verification_template_items"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_sanitary_verification_template_items_risk_level_valid",
        ),
        UniqueConstraint(
            "template_id",
            "display_order",
            name="uq_sanitary_verification_template_items_template_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sanitary_verification_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_standard: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(16), default=CLEANING_RISK_MEDIUM, nullable=False
    )
    evidence_required_on_failure: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class SanitaryVerification(Base):
    __tablename__ = "sanitary_verifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'IN_PROGRESS', 'COMPLETED', "
            "'CANCELLED', 'REQUIRES_FOLLOW_UP')",
            name="ck_sanitary_verifications_status_valid",
        ),
        CheckConstraint(
            "result IN ('NOT_EVALUATED', 'PASSED', 'FAILED', 'PARTIAL')",
            name="ck_sanitary_verifications_result_valid",
        ),
        CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name="ck_sanitary_verifications_area_type_valid",
        ),
        CheckConstraint(
            "process_type IN ('STORAGE', 'PRODUCTION', 'DISPLAY', 'EQUIPMENT', "
            "'SANITATION', 'OTHER')",
            name="ck_sanitary_verifications_process_type_valid",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_sanitary_verifications_risk_level_valid",
        ),
        CheckConstraint(
            "score_percent IS NULL OR (score_percent >= 0 AND score_percent <= 100)",
            name="ck_sanitary_verifications_score_percent_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    area_name: Mapped[str] = mapped_column(String(160), nullable=False)
    area_type: Mapped[str] = mapped_column(
        String(40), default=CLEANING_AREA_TYPE_OTHER, nullable=False
    )
    equipment_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    process_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    process_type: Mapped[str] = mapped_column(
        String(40), default=SANITARY_PROCESS_OTHER, nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sanitary_verification_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_name: Mapped[str] = mapped_column(String(160), nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(16), default=CLEANING_RISK_MEDIUM, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=SANITARY_STATUS_PENDING, nullable=False
    )
    result: Mapped[str] = mapped_column(
        String(32), default=SANITARY_RESULT_NOT_EVALUATED, nullable=False
    )
    inspector_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_incident: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    incident_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follow_up_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_applicable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checklist_total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_threshold_percent: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SanitaryVerificationChecklistItem(Base):
    __tablename__ = "sanitary_verification_checklist_items"
    __table_args__ = (
        CheckConstraint(
            "result IN ('PENDING', 'PASSED', 'FAILED', 'NOT_APPLICABLE')",
            name="ck_sanitary_verification_checklist_items_result_valid",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_sanitary_verification_checklist_items_risk_level_valid",
        ),
        UniqueConstraint(
            "verification_id",
            "display_order",
            name="uq_sanitary_verification_checklist_items_verification_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sanitary_verifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sanitary_verification_template_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    expected_standard: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    result: Mapped[str] = mapped_column(
        String(32), default=SANITARY_ITEM_RESULT_PENDING, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(16), default=CLEANING_RISK_MEDIUM, nullable=False
    )
    evidence_required_on_failure: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class EquipmentAsset(Base):
    __tablename__ = "equipment_assets"
    __table_args__ = (
        CheckConstraint(
            "equipment_type IN ('OVEN', 'MIXER', 'REFRIGERATION', 'DISPLAY_CASE', "
            "'SCALE', 'PACKAGING', 'SANITATION', 'OTHER')",
            name="ck_equipment_assets_type_valid",
        ),
        CheckConstraint(
            "area_type IN ('PRODUCTION', 'REFRIGERATION', 'DISPLAY_COUNTER', 'STORAGE', "
            "'CLEANING_SANITATION', 'OTHER')",
            name="ck_equipment_assets_area_type_valid",
        ),
        CheckConstraint(
            "operational_status IN ('OPERATIONAL', 'OUT_OF_SERVICE', 'UNDER_MAINTENANCE', "
            "'RETIRED', 'INACTIVE')",
            name="ck_equipment_assets_status_valid",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_equipment_assets_risk_level_valid",
        ),
        CheckConstraint(
            "maintenance_frequency_days IS NULL OR maintenance_frequency_days > 0",
            name="ck_equipment_assets_frequency_positive",
        ),
        CheckConstraint(
            "warranty_expires_at IS NULL OR purchase_date IS NULL "
            "OR warranty_expires_at >= purchase_date",
            name="ck_equipment_assets_warranty_after_purchase",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    equipment_type: Mapped[str] = mapped_column(
        String(40), default=EQUIPMENT_TYPE_OTHER, nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    area_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    area_type: Mapped[str] = mapped_column(
        String(40), default=EQUIPMENT_AREA_TYPE_OTHER, nullable=False
    )
    operational_status: Mapped[str] = mapped_column(
        String(32), default=EQUIPMENT_STATUS_OPERATIONAL, nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(16), default=CLEANING_RISK_MEDIUM, nullable=False
    )
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    maintenance_frequency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    food_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    out_of_service_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class EquipmentMaintenanceRecord(Base):
    __tablename__ = "equipment_maintenance_records"
    __table_args__ = (
        CheckConstraint(
            "maintenance_type IN ('PREVENTIVE', 'CORRECTIVE', 'INSPECTION', "
            "'CALIBRATION', 'CLEANING_TECHNICAL')",
            name="ck_equipment_maintenance_records_type_valid",
        ),
        CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'IN_PROGRESS', 'COMPLETED', "
            "'OVERDUE', 'CANCELLED')",
            name="ck_equipment_maintenance_records_status_valid",
        ),
        CheckConstraint(
            "result IN ('NOT_COMPLETED', 'COMPLETED_SUCCESSFULLY', "
            "'COMPLETED_WITH_OBSERVATIONS', 'FAILED', 'REQUIRES_FOLLOW_UP', 'CANCELLED')",
            name="ck_equipment_maintenance_records_result_valid",
        ),
        CheckConstraint(
            "expected_cost IS NULL OR expected_cost >= 0",
            name="ck_equipment_maintenance_records_expected_cost_non_negative",
        ),
        CheckConstraint(
            "cost IS NULL OR cost >= 0",
            name="ck_equipment_maintenance_records_cost_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    maintenance_type: Mapped[str] = mapped_column(
        String(40), default=MAINTENANCE_TYPE_PREVENTIVE, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=MAINTENANCE_STATUS_PENDING, nullable=False
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    technician_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    result: Mapped[str] = mapped_column(
        String(40), default=MAINTENANCE_RESULT_NOT_COMPLETED, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    related_incident_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_document_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_document_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class QualityIncident(Base):
    __tablename__ = "quality_incidents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'IN_REVIEW', 'IN_PROGRESS', 'WAITING_ACTION', "
            "'RESOLVED', 'CLOSED', 'CANCELLED')",
            name="ck_quality_incidents_status_valid",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_quality_incidents_severity_valid",
        ),
        CheckConstraint(
            "incident_type IN ('SANITATION_ISSUE', 'CLEANING_NON_COMPLIANCE', "
            "'EQUIPMENT_FAILURE', 'PRODUCTION_ISSUE', 'INVENTORY_ISSUE', "
            "'TRANSFER_ISSUE', 'WASTE_ISSUE', 'SAFETY_ISSUE', 'CUSTOMER_COMPLAINT', "
            "'PROCESS_DEVIATION', 'OTHER')",
            name="ck_quality_incidents_type_valid",
        ),
        CheckConstraint(
            "source_type IN ('MANUAL', 'CLEANING_LOG', 'SANITARY_VERIFICATION', "
            "'EQUIPMENT', 'PRODUCTION', 'INVENTORY', 'TRANSFER', 'WASTE_MERMA', "
            "'CUSTOMER_REPORT', 'CORRECTION')",
            name="ck_quality_incidents_source_valid",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_quality_incidents_risk_level_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    area_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    equipment_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    process_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    product_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    production_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(40), default=INCIDENT_SOURCE_MANUAL, nullable=False
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_type: Mapped[str] = mapped_column(
        String(40), default=INCIDENT_TYPE_OTHER, nullable=False
    )
    severity: Mapped[str] = mapped_column(
        String(16), default=INCIDENT_SEVERITY_MEDIUM, nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(16), default=INCIDENT_SEVERITY_MEDIUM, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=INCIDENT_STATUS_OPEN, nullable=False)
    operational_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    food_safety_impact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_result: Mapped[str | None] = mapped_column(String(160), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class QualityIncidentFollowUp(Base):
    __tablename__ = "quality_incident_follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quality_incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status_change: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
