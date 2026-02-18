"""UB-04 institutional claim form schema."""

from datetime import date

from pydantic import BaseModel

from .common import InsuranceInfo, PatientInfo, ProviderInfo


class UB04RevenueLine(BaseModel):
    """Revenue line from UB-04 form."""

    revenue_code: str | None = None
    description: str | None = None
    hcpcs_code: str | None = None
    service_date: date | None = None
    units: int | None = None
    total_charges: float | None = None
    non_covered_charges: float | None = None


class UB04Schema(BaseModel):
    """UB-04 institutional claim form."""

    facility_name: str | None = None
    facility_address: str | None = None
    facility_type: str | None = None
    federal_tax_id: str | None = None
    patient: PatientInfo = PatientInfo()
    insurance: InsuranceInfo = InsuranceInfo()
    admission_date: date | None = None
    admission_type: str | None = None
    discharge_date: date | None = None
    discharge_status: str | None = None
    admission_diagnosis: str | None = None
    principal_diagnosis: str | None = None
    other_diagnoses: list[str] = []
    principal_procedure: str | None = None
    procedure_date: date | None = None
    revenue_lines: list[UB04RevenueLine] = []
    total_charges: float | None = None
    total_non_covered: float | None = None
    estimated_amount_due: float | None = None
    provider: ProviderInfo = ProviderInfo()
    attending_physician_npi: str | None = None
