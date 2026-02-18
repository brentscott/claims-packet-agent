"""Pharmacy receipt schema."""

from datetime import date

from pydantic import BaseModel

from .common import PatientInfo


class PharmacyReceiptSchema(BaseModel):
    """Pharmacy prescription receipt."""

    pharmacy_name: str | None = None
    pharmacy_address: str | None = None
    pharmacy_phone: str | None = None
    pharmacy_npi: str | None = None
    patient: PatientInfo = PatientInfo()
    rx_number: str | None = None
    fill_date: date | None = None
    medication_name: str | None = None
    ndc_code: str | None = None
    quantity: float | None = None
    days_supply: int | None = None
    prescriber_name: str | None = None
    prescriber_npi: str | None = None
    drug_cost: float | None = None
    insurance_paid: float | None = None
    patient_copay: float | None = None
    patient_coinsurance: float | None = None
    deductible_applied: float | None = None
    patient_paid: float | None = None
    formulary_tier: str | None = None
    prior_auth_required: bool | None = None
