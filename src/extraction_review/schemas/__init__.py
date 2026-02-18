"""Insurance claims packet schemas for document extraction and validation."""

from .common import (
    DocumentEnvelope,
    DocumentType,
    InsuranceInfo,
    PatientInfo,
    ProviderInfo,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from .cms1500 import CMS1500Schema, CMS1500ServiceLine, DiagnosisCode
from .eob import EOBLineItem, EOBSchema
from .lab_report import LabReportSchema, LabTestResult
from .medical_bill import BillLineItem, MedicalBillSchema
from .packet_output import ClaimsPacketOutput, FinancialSummary, ProcessedDocument
from .pharmacy import PharmacyReceiptSchema
from .ub04 import UB04RevenueLine, UB04Schema
from .dental_claim import DentalClaimSchema, DentalServiceLine
from .prior_auth import AuthorizedService, PriorAuthSchema
from .appeal_decision import AppealDecisionSchema
from .itemized_statement import ItemizedCharge, ItemizedStatementSchema

__all__ = [
    # Common
    "DocumentType",
    "PatientInfo",
    "ProviderInfo",
    "InsuranceInfo",
    "ValidationSeverity",
    "ValidationStatus",
    "ValidationResult",
    "DocumentEnvelope",
    # EOB
    "EOBLineItem",
    "EOBSchema",
    # Medical Bill
    "BillLineItem",
    "MedicalBillSchema",
    # CMS-1500
    "DiagnosisCode",
    "CMS1500ServiceLine",
    "CMS1500Schema",
    # UB-04
    "UB04RevenueLine",
    "UB04Schema",
    # Pharmacy
    "PharmacyReceiptSchema",
    # Lab Report
    "LabTestResult",
    "LabReportSchema",
    # Dental Claim
    "DentalServiceLine",
    "DentalClaimSchema",
    # Prior Authorization
    "AuthorizedService",
    "PriorAuthSchema",
    # Appeal Decision
    "AppealDecisionSchema",
    # Itemized Statement
    "ItemizedCharge",
    "ItemizedStatementSchema",
    # Output
    "ProcessedDocument",
    "FinancialSummary",
    "ClaimsPacketOutput",
]

# Schema registry for mapping document types to their schemas
SCHEMA_REGISTRY: dict[str, type] = {
    "EOB": EOBSchema,
    "CMS-1500": CMS1500Schema,
    "UB-04": UB04Schema,
    "MEDICAL_BILL": MedicalBillSchema,
    "PHARMACY_RECEIPT": PharmacyReceiptSchema,
    "LAB_REPORT": LabReportSchema,
    "DENTAL_CLAIM": DentalClaimSchema,
    "PRIOR_AUTH": PriorAuthSchema,
    "APPEAL_DECISION": AppealDecisionSchema,
    "ITEMIZED_STATEMENT": ItemizedStatementSchema,
}
