"""Prior Authorization Letter schema."""

from datetime import date

from pydantic import BaseModel

from .common import InsuranceInfo, PatientInfo, ProviderInfo


class AuthorizedService(BaseModel):
    """Individual service authorized under a prior auth."""

    cpt_code: str | None = None
    description: str | None = None
    quantity_approved: int | None = None
    approved_amount: float | None = None


class PriorAuthSchema(BaseModel):
    """Prior Authorization approval or denial letter from an insurer."""

    # Identifiers
    authorization_number: str | None = None
    reference_number: str | None = None
    document_date: date | None = None
    # Parties
    patient: PatientInfo = PatientInfo()
    requesting_provider: ProviderInfo = ProviderInfo()
    servicing_provider: ProviderInfo = ProviderInfo()
    insurance: InsuranceInfo = InsuranceInfo()
    # Authorization details
    auth_status: str | None = None
    auth_type: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    diagnosis_codes: list[str] = []
    authorized_services: list[AuthorizedService] = []
    # Conditions and limitations
    conditions: list[str] = []
    place_of_service: str | None = None
    # Denial info (if denied)
    denial_reason: str | None = None
    appeal_deadline: date | None = None
    appeal_instructions: str | None = None
    # Totals
    total_approved_amount: float | None = None
