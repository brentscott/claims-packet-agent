"""Lab report schema."""

from datetime import date

from pydantic import BaseModel

from .common import PatientInfo, ProviderInfo


class LabTestResult(BaseModel):
    """Individual test result from a lab report."""

    test_name: str | None = None
    cpt_code: str | None = None
    result_value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    flag: str | None = None


class LabReportSchema(BaseModel):
    """Laboratory test results report."""

    accession_number: str | None = None
    report_date: date | None = None
    patient: PatientInfo = PatientInfo()
    ordering_provider: ProviderInfo = ProviderInfo()
    performing_lab: ProviderInfo = ProviderInfo()
    collection_date: date | None = None
    specimen_type: str | None = None
    panel_name: str | None = None
    test_results: list[LabTestResult] = []
    total_charges: float | None = None
    diagnosis_codes: list[str] = []
