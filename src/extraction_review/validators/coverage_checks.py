"""Coverage validation checks for denied claims and zero-benefit scenarios."""

from datetime import date, timedelta

from ..schemas.common import ValidationResult, ValidationSeverity, ValidationStatus
from ..schemas.packet_output import ProcessedDocument


def run_coverage_checks(documents: list[ProcessedDocument]) -> list[ValidationResult]:
    """Run coverage-related validation checks.

    Checks:
    - claim_denied: Entire claim denied, with appeal deadline tracking
    - line_item_denied: Individual line items with denial_reason
    - zero_allowed_amount: Line items where allowed=0 but billed>0
    - patient_full_cost: Patient responsible for full billed amount
    """
    results: list[ValidationResult] = []

    for doc in documents:
        if doc.envelope.classified_type.value == "EOB":
            results.extend(_check_eob_coverage(doc))

    return results


def _check_eob_coverage(doc: ProcessedDocument) -> list[ValidationResult]:
    """Check EOB for coverage issues."""
    results: list[ValidationResult] = []
    data = doc.extracted_data
    doc_id = doc.envelope.doc_id

    # Check 1: claim_denied - whole claim denied
    claim_status = (data.get("claim_status") or "").lower()
    if "denied" in claim_status or "deny" in claim_status:
        appeal_deadline = _parse_date(data.get("appeal_deadline"))
        urgency = _get_appeal_urgency(appeal_deadline)
        provider = data.get("provider", {}).get("name", "provider")
        total_billed = data.get("total_billed")

        detail = f"Claim from {provider} was DENIED"
        if total_billed:
            detail += f" (${total_billed:.2f})"
        if appeal_deadline:
            detail += f". Appeal deadline: {appeal_deadline.isoformat()}"
            if urgency == "urgent":
                detail += " (URGENT - less than 14 days remaining)"

        results.append(
            ValidationResult(
                check_name="claim_denied",
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.HIGH,
                detail=detail,
                potential_overcharge=total_billed,
                recommendation="File an appeal immediately with insurance. Contact provider about claim denial.",
            )
        )

    # Check 2: line_item_denied - individual denied services
    for item in data.get("line_items", []):
        denial_reason = item.get("denial_reason")
        if denial_reason:
            cpt = item.get("cpt_code", "Unknown")
            billed = item.get("billed_amount")
            desc = item.get("description", "")

            detail = f"Service {cpt}"
            if desc:
                detail += f" ({desc})"
            detail += f" was denied: {denial_reason}"
            if billed:
                detail += f". Billed amount: ${billed:.2f}"

            results.append(
                ValidationResult(
                    check_name="line_item_denied",
                    status=ValidationStatus.ERROR,
                    severity=ValidationSeverity.HIGH,
                    detail=detail,
                    potential_overcharge=billed,
                    recommendation=f"Review denial reason for {cpt}. Consider appeal if service was medically necessary.",
                )
            )

    # Check 3: zero_allowed_amount - insurance allowed nothing
    for item in data.get("line_items", []):
        allowed = item.get("allowed_amount")
        billed = item.get("billed_amount")
        ins_paid = item.get("insurance_paid")

        if (
            allowed == 0
            and (ins_paid is None or ins_paid == 0)
            and billed
            and billed > 0
        ):
            cpt = item.get("cpt_code", "Unknown")
            desc = item.get("description", "")
            remark_codes = item.get("remark_codes", [])

            detail = f"Insurance allowed $0 for {cpt}"
            if desc:
                detail += f" ({desc})"
            detail += f" but provider billed ${billed:.2f}"
            if remark_codes:
                detail += f". Remark codes: {', '.join(remark_codes)}"

            results.append(
                ValidationResult(
                    check_name="zero_allowed_amount",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.MEDIUM,
                    detail=detail,
                    potential_overcharge=billed,
                    recommendation=f"Contact insurance to understand why {cpt} was not covered. May need prior authorization or may not be a covered benefit.",
                )
            )

    # Check 4: patient_full_cost - patient pays everything
    total_insurance_paid = data.get("total_insurance_paid")
    total_patient_resp = data.get("total_patient_responsibility")
    total_billed = data.get("total_billed")

    if (
        total_insurance_paid == 0
        and total_billed
        and total_billed > 0
        and total_patient_resp
        and abs(total_patient_resp - total_billed) < 0.01
    ):
        provider = data.get("provider", {}).get("name", "provider")

        results.append(
            ValidationResult(
                check_name="patient_full_cost",
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.HIGH,
                detail=f"Patient responsible for full billed amount (${total_billed:.2f}) from {provider}. Insurance paid $0.",
                potential_overcharge=total_billed,
                recommendation="Verify claim was submitted correctly. Check if provider is out-of-network or if deductible applies.",
            )
        )

    return results


def _parse_date(value: str | date | None) -> date | None:
    """Parse a date value."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _get_appeal_urgency(deadline: date | None) -> str:
    """Determine urgency based on appeal deadline."""
    if not deadline:
        return "unknown"
    days_remaining = (deadline - date.today()).days
    if days_remaining <= 14:
        return "urgent"
    if days_remaining <= 30:
        return "soon"
    return "normal"
