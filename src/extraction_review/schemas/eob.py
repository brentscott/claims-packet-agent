"""Explanation of Benefits (EOB) schema."""

from datetime import date

from pydantic import BaseModel

from .common import InsuranceInfo, PatientInfo, ProviderInfo


class EOBLineItem(BaseModel):
    """Individual service line from an EOB."""

    service_date: date | None = None
    cpt_code: str | None = None
    description: str | None = None
    billed_amount: float | None = None
    allowed_amount: float | None = None
    insurance_paid: float | None = None
    deductible_applied: float | None = None
    copay: float | None = None
    coinsurance: float | None = None
    patient_responsibility: float | None = None
    remark_codes: list[str] = []
    denial_reason: str | None = None


class EOBSchema(BaseModel):
    """Explanation of Benefits from an insurance company."""

    # Identifiers
    claim_number: str | None = None
    document_date: date | None = None
    # Parties
    patient: PatientInfo = PatientInfo()
    provider: ProviderInfo = ProviderInfo()
    insurance: InsuranceInfo = InsuranceInfo()
    # Service details
    date_of_service_start: date | None = None
    date_of_service_end: date | None = None
    place_of_service: str | None = None
    line_items: list[EOBLineItem] = []
    # Totals
    total_billed: float | None = None
    total_allowed: float | None = None
    total_insurance_paid: float | None = None
    total_patient_responsibility: float | None = None
    total_deductible: float | None = None
    total_copay: float | None = None
    total_coinsurance: float | None = None
    # Benefit accumulators
    deductible_met_ytd: float | None = None
    deductible_remaining: float | None = None
    out_of_pocket_met_ytd: float | None = None
    out_of_pocket_max: float | None = None
    # Status
    claim_status: str | None = None
    appeal_deadline: date | None = None
