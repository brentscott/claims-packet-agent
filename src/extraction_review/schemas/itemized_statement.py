"""Itemized Statement schema."""

from datetime import date

from pydantic import BaseModel

from .common import PatientInfo, ProviderInfo


class ItemizedCharge(BaseModel):
    """Individual charge line from an itemized statement."""

    service_date: date | None = None
    revenue_code: str | None = None
    cpt_code: str | None = None
    description: str | None = None
    department: str | None = None
    quantity: int | None = None
    unit_price: float | None = None
    amount: float | None = None


class ItemizedStatementSchema(BaseModel):
    """Hospital or provider itemized statement with granular line-item detail."""

    # Identifiers
    account_number: str | None = None
    statement_date: date | None = None
    invoice_number: str | None = None
    medical_record_number: str | None = None
    # Parties
    patient: PatientInfo = PatientInfo()
    provider: ProviderInfo = ProviderInfo()
    # Admission / service details
    admission_date: date | None = None
    discharge_date: date | None = None
    date_of_service_start: date | None = None
    date_of_service_end: date | None = None
    # Itemized charges — much more granular than a regular bill
    charges: list[ItemizedCharge] = []
    # Financial summary
    total_charges: float | None = None
    total_adjustments: float | None = None
    total_insurance_payments: float | None = None
    total_patient_payments: float | None = None
    balance_due: float | None = None
    # Metadata
    page_count: int | None = None
    total_line_items: int | None = None
