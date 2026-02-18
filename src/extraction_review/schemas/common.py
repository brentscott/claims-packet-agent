"""Shared types for insurance claims packet schemas."""

from datetime import date
from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    """Types of documents in an insurance claims packet."""

    EOB = "EOB"
    CMS1500 = "CMS-1500"
    UB04 = "UB-04"
    MEDICAL_BILL = "MEDICAL_BILL"
    PHARMACY_RECEIPT = "PHARMACY_RECEIPT"
    LAB_REPORT = "LAB_REPORT"
    UNKNOWN = "UNKNOWN"


class PatientInfo(BaseModel):
    """Patient demographic and insurance membership information."""

    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    member_id: str | None = None
    group_number: str | None = None
    address: str | None = None


class ProviderInfo(BaseModel):
    """Healthcare provider or facility information."""

    name: str | None = None
    npi: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None


class InsuranceInfo(BaseModel):
    """Insurance plan and policy information."""

    payer_name: str | None = None
    plan_name: str | None = None
    plan_type: str | None = None
    policy_number: str | None = None
    group_number: str | None = None


class ValidationSeverity(str, Enum):
    """Severity level for validation findings."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ValidationStatus(str, Enum):
    """Status outcome of a validation check."""

    PASS = "PASS"
    MISMATCH = "MISMATCH"
    WARNING = "WARNING"
    ERROR = "ERROR"
    INFO = "INFO"


class ValidationResult(BaseModel):
    """Result of a single validation check."""

    check_name: str
    status: ValidationStatus
    severity: ValidationSeverity
    detail: str
    potential_overcharge: float | None = None
    recommendation: str | None = None


class DocumentEnvelope(BaseModel):
    """Metadata wrapper for a processed document."""

    doc_id: str
    filename: str
    classified_type: DocumentType
    classification_confidence: float
    field_confidence: dict[str, float] = {}
    extraction_warnings: list[str] = []
