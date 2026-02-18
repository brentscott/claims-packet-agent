"""Output schemas for the claims packet workflow."""

from typing import Any

from pydantic import BaseModel

from .common import DocumentEnvelope, DocumentType, PatientInfo, ValidationResult


class ProcessedDocument(BaseModel):
    """A single document after extraction and validation."""

    envelope: DocumentEnvelope
    extracted_data: dict[str, Any]
    schema_used: DocumentType


class FinancialSummary(BaseModel):
    """Aggregated financial information across all documents."""

    total_billed: float | None = None
    total_allowed: float | None = None
    total_insurance_paid: float | None = None
    total_patient_responsibility_per_eob: float | None = None
    total_patient_responsibility_per_bills: float | None = None
    discrepancy_amount: float | None = None
    potential_savings: float | None = None
    flagged_issues: int = 0


class ClaimsPacketOutput(BaseModel):
    """Complete output from the claims packet workflow."""

    packet_id: str
    patient: PatientInfo
    documents: list[ProcessedDocument] = []
    validation_results: list[ValidationResult] = []
    financial_summary: FinancialSummary
    recommended_actions: list[str] = []
    summary_narrative: str | None = None
