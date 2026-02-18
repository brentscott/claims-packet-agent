"""Medical bill schema for provider statements."""

from datetime import date

from pydantic import BaseModel

from .common import PatientInfo, ProviderInfo


class BillLineItem(BaseModel):
    """Individual charge line from a medical bill."""

    service_date: date | None = None
    cpt_code: str | None = None
    description: str | None = None
    quantity: int | None = None
    unit_price: float | None = None
    amount: float | None = None


class MedicalBillSchema(BaseModel):
    """Provider bill or patient statement."""

    account_number: str | None = None
    statement_date: date | None = None
    invoice_number: str | None = None
    patient: PatientInfo = PatientInfo()
    provider: ProviderInfo = ProviderInfo()
    date_of_service_start: date | None = None
    date_of_service_end: date | None = None
    line_items: list[BillLineItem] = []
    # Financial summary
    total_charges: float | None = None
    insurance_adjustments: float | None = None
    insurance_payments: float | None = None
    patient_payments: float | None = None
    balance_due: float | None = None
    due_date: date | None = None
    payment_plan_available: bool | None = None
    financial_assistance_note: str | None = None
