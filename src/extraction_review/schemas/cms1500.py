"""CMS-1500 professional claim form schema."""

from datetime import date

from pydantic import BaseModel

from .common import InsuranceInfo, PatientInfo, ProviderInfo


class DiagnosisCode(BaseModel):
    """ICD-10 diagnosis code with pointer reference."""

    pointer: str
    icd10_code: str
    description: str | None = None


class CMS1500ServiceLine(BaseModel):
    """Service line from CMS-1500 Box 24."""

    date_of_service_from: date | None = None
    date_of_service_to: date | None = None
    place_of_service: str | None = None
    cpt_code: str | None = None
    modifier_1: str | None = None
    modifier_2: str | None = None
    diagnosis_pointer: str | None = None
    charges: float | None = None
    units: int | None = None
    rendering_provider_npi: str | None = None


class CMS1500Schema(BaseModel):
    """CMS-1500 professional claim form."""

    payer_type: str | None = None
    patient: PatientInfo = PatientInfo()
    insured: PatientInfo = PatientInfo()
    provider: ProviderInfo = ProviderInfo()
    referring_provider: ProviderInfo | None = None
    insurance: InsuranceInfo = InsuranceInfo()
    patient_account_number: str | None = None
    accept_assignment: bool | None = None
    prior_authorization: str | None = None
    diagnosis_codes: list[DiagnosisCode] = []
    service_lines: list[CMS1500ServiceLine] = []
    total_charge: float | None = None
    amount_paid: float | None = None
    balance_due: float | None = None
    patient_signature_date: date | None = None
    physician_signature_date: date | None = None
