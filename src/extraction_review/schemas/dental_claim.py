"""ADA Dental Claim Form schema."""

from datetime import date

from pydantic import BaseModel

from .common import InsuranceInfo, PatientInfo, ProviderInfo


class DentalServiceLine(BaseModel):
    """Individual service line from a dental claim."""

    service_date: date | None = None
    area_of_oral_cavity: str | None = None
    tooth_system: str | None = None
    tooth_number: str | None = None
    tooth_surface: str | None = None
    cdt_code: str | None = None
    description: str | None = None
    fee: float | None = None


class DentalClaimSchema(BaseModel):
    """ADA Dental Claim Form (J430/J431)."""

    # Identifiers
    claim_number: str | None = None
    predetermination_number: str | None = None
    document_date: date | None = None
    # Parties
    patient: PatientInfo = PatientInfo()
    subscriber: PatientInfo = PatientInfo()
    provider: ProviderInfo = ProviderInfo()
    billing_provider: ProviderInfo = ProviderInfo()
    insurance: InsuranceInfo = InsuranceInfo()
    # Treatment details
    date_of_service: date | None = None
    place_of_treatment: str | None = None
    is_orthodontic: bool | None = None
    is_prosthesis_replacement: bool | None = None
    prior_prosthesis_date: date | None = None
    diagnosis_codes: list[str] = []
    service_lines: list[DentalServiceLine] = []
    # Totals
    total_fee: float | None = None
    amount_paid: float | None = None
    patient_responsibility: float | None = None
    # Remarks
    remarks: str | None = None
