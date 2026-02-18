"""Appeal Decision Letter schema."""

from datetime import date

from pydantic import BaseModel

from .common import InsuranceInfo, PatientInfo, ProviderInfo


class AppealDecisionSchema(BaseModel):
    """Appeal decision letter from an insurer regarding a denied or disputed claim."""

    # Identifiers
    appeal_reference_number: str | None = None
    original_claim_number: str | None = None
    original_authorization_number: str | None = None
    document_date: date | None = None
    # Parties
    patient: PatientInfo = PatientInfo()
    provider: ProviderInfo = ProviderInfo()
    insurance: InsuranceInfo = InsuranceInfo()
    # Original claim context
    date_of_service: date | None = None
    original_denial_date: date | None = None
    original_denial_reason: str | None = None
    original_billed_amount: float | None = None
    # Appeal decision
    appeal_level: str | None = None
    decision: str | None = None
    decision_date: date | None = None
    decision_rationale: str | None = None
    # If overturned/partially approved
    approved_amount: float | None = None
    approved_services: list[str] = []
    adjusted_patient_responsibility: float | None = None
    # If upheld (still denied)
    next_appeal_level: str | None = None
    next_appeal_deadline: date | None = None
    external_review_available: bool | None = None
    external_review_instructions: str | None = None
    # Procedure codes referenced
    cpt_codes: list[str] = []
    diagnosis_codes: list[str] = []
