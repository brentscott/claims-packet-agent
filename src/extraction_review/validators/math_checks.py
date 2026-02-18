"""Math validation checks for EOB and bill line item sums."""

from ..schemas.common import ValidationResult, ValidationSeverity, ValidationStatus
from ..schemas.packet_output import ProcessedDocument

TOLERANCE = 0.01


def _safe_sum(values: list[float | None]) -> float:
    """Sum values, skipping None."""
    return sum(v for v in values if v is not None)


def run_math_checks(documents: list[ProcessedDocument]) -> list[ValidationResult]:
    """Run all math validation checks.

    Checks:
    - eob_billed_sum: Sum of EOB line item billed_amount vs total_billed
    - eob_paid_sum: Sum of EOB line item insurance_paid vs total_insurance_paid
    - eob_patient_responsibility_breakdown: Deductible + copay + coinsurance vs total
    - bill_line_item_sum: Sum of bill line item amount vs total_charges
    - bill_balance_due_math: total_charges - adjustments - payments vs balance_due
    """
    results: list[ValidationResult] = []

    for doc in documents:
        doc_type = doc.envelope.classified_type.value
        data = doc.extracted_data
        doc_id = doc.envelope.doc_id

        if doc_type == "EOB":
            results.extend(_check_eob_math(data, doc_id))
        elif doc_type == "MEDICAL_BILL":
            results.extend(_check_bill_math(data, doc_id))

    return results


def _check_eob_math(data: dict, doc_id: str) -> list[ValidationResult]:
    """Check EOB-specific math."""
    results: list[ValidationResult] = []
    line_items = data.get("line_items", [])

    # Check 1: eob_billed_sum
    total_billed = data.get("total_billed")
    if total_billed is not None and line_items:
        line_sum = _safe_sum([item.get("billed_amount") for item in line_items])
        if abs(line_sum - total_billed) > TOLERANCE:
            results.append(
                ValidationResult(
                    check_name="eob_billed_sum",
                    status=ValidationStatus.MISMATCH,
                    severity=ValidationSeverity.MEDIUM,
                    detail=f"EOB {doc_id}: Line item billed amounts sum to ${line_sum:.2f} but total_billed is ${total_billed:.2f}",
                    potential_overcharge=abs(line_sum - total_billed),
                    recommendation="Review the EOB for calculation errors",
                )
            )

    # Check 2: eob_paid_sum
    total_insurance_paid = data.get("total_insurance_paid")
    if total_insurance_paid is not None and line_items:
        line_sum = _safe_sum([item.get("insurance_paid") for item in line_items])
        if abs(line_sum - total_insurance_paid) > TOLERANCE:
            results.append(
                ValidationResult(
                    check_name="eob_paid_sum",
                    status=ValidationStatus.MISMATCH,
                    severity=ValidationSeverity.MEDIUM,
                    detail=f"EOB {doc_id}: Line item insurance_paid sum ${line_sum:.2f} doesn't match total ${total_insurance_paid:.2f}",
                    potential_overcharge=None,
                    recommendation="Contact insurance to verify payment amounts",
                )
            )

    # Check 3: eob_patient_responsibility_breakdown
    total_patient = data.get("total_patient_responsibility")
    total_deductible = data.get("total_deductible") or 0
    total_copay = data.get("total_copay") or 0
    total_coinsurance = data.get("total_coinsurance") or 0
    if total_patient is not None:
        breakdown_sum = total_deductible + total_copay + total_coinsurance
        if abs(breakdown_sum - total_patient) > TOLERANCE and breakdown_sum > 0:
            results.append(
                ValidationResult(
                    check_name="eob_patient_responsibility_breakdown",
                    status=ValidationStatus.MISMATCH,
                    severity=ValidationSeverity.MEDIUM,
                    detail=f"EOB {doc_id}: Deductible (${total_deductible:.2f}) + copay (${total_copay:.2f}) + coinsurance (${total_coinsurance:.2f}) = ${breakdown_sum:.2f}, but total patient responsibility is ${total_patient:.2f}",
                    potential_overcharge=abs(breakdown_sum - total_patient)
                    if breakdown_sum < total_patient
                    else None,
                    recommendation="Verify patient responsibility calculation with insurance",
                )
            )

    return results


def _check_bill_math(data: dict, doc_id: str) -> list[ValidationResult]:
    """Check medical bill math."""
    results: list[ValidationResult] = []
    line_items = data.get("line_items", [])

    # Check 4: bill_line_item_sum
    total_charges = data.get("total_charges")
    if total_charges is not None and line_items:
        line_sum = _safe_sum([item.get("amount") for item in line_items])
        if abs(line_sum - total_charges) > TOLERANCE:
            results.append(
                ValidationResult(
                    check_name="bill_line_item_sum",
                    status=ValidationStatus.ERROR,
                    severity=ValidationSeverity.HIGH,
                    detail=f"Bill {doc_id}: Line items sum to ${line_sum:.2f} but total_charges is ${total_charges:.2f}",
                    potential_overcharge=total_charges - line_sum
                    if total_charges > line_sum
                    else None,
                    recommendation="Request itemized bill from provider to verify charges",
                )
            )

    # Check 5: bill_balance_due_math
    balance_due = data.get("balance_due")
    if balance_due is not None and total_charges is not None:
        adjustments = data.get("insurance_adjustments") or 0
        ins_payments = data.get("insurance_payments") or 0
        patient_payments = data.get("patient_payments") or 0
        expected_balance = total_charges - adjustments - ins_payments - patient_payments
        if abs(expected_balance - balance_due) > TOLERANCE:
            results.append(
                ValidationResult(
                    check_name="bill_balance_due_math",
                    status=ValidationStatus.MISMATCH,
                    severity=ValidationSeverity.MEDIUM,
                    detail=f"Bill {doc_id}: Expected balance ${expected_balance:.2f} (charges ${total_charges:.2f} - adjustments ${adjustments:.2f} - insurance paid ${ins_payments:.2f} - patient paid ${patient_payments:.2f}), but balance_due shows ${balance_due:.2f}",
                    potential_overcharge=balance_due - expected_balance
                    if balance_due > expected_balance
                    else None,
                    recommendation="Contact billing department to clarify balance calculation",
                )
            )

    return results
