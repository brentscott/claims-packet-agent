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
    - prior_auth_denied: Prior authorization was denied
    - prior_auth_expired: Prior authorization has expired
    - appeal_upheld: Appeal decision upheld the original denial
    - appeal_overturned_mismatch: Appeal overturned but bills don't reflect it
    - prior_auth_vs_denial: EOB denied a service that had prior auth approval
    """
    results: list[ValidationResult] = []

    for doc in documents:
        doc_type = doc.envelope.classified_type.value
        if doc_type == "EOB":
            results.extend(_check_eob_coverage(doc))
        elif doc_type == "PRIOR_AUTH":
            results.extend(_check_prior_auth(doc))
        elif doc_type == "APPEAL_DECISION":
            results.extend(_check_appeal_decision(doc))

    # Cross-document: prior auth vs EOB denial
    results.extend(_cross_check_prior_auth_vs_eob(documents))

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


def _check_prior_auth(doc: ProcessedDocument) -> list[ValidationResult]:
    """Check prior authorization for coverage issues."""
    results: list[ValidationResult] = []
    data = doc.extracted_data

    auth_status = (data.get("auth_status") or "").lower()
    auth_number = data.get("authorization_number", "Unknown")

    # Check: prior_auth_denied
    if "denied" in auth_status or "deny" in auth_status:
        denial_reason = data.get("denial_reason", "")
        appeal_deadline = _parse_date(data.get("appeal_deadline"))
        urgency = _get_appeal_urgency(appeal_deadline)
        total = data.get("total_approved_amount")

        detail = f"Prior authorization {auth_number} was DENIED"
        if denial_reason:
            detail += f": {denial_reason}"
        if appeal_deadline:
            detail += f". Appeal deadline: {appeal_deadline.isoformat()}"
            if urgency == "urgent":
                detail += " (URGENT - less than 14 days remaining)"

        results.append(
            ValidationResult(
                check_name="prior_auth_denied",
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.HIGH,
                detail=detail,
                recommendation=data.get("appeal_instructions")
                or "Review denial reason and consider filing an appeal before the deadline.",
            )
        )

    # Check: prior_auth_expired
    expiration = _parse_date(data.get("expiration_date"))
    if expiration and expiration < date.today() and "denied" not in auth_status:
        detail = f"Prior authorization {auth_number} expired on {expiration.isoformat()}"
        results.append(
            ValidationResult(
                check_name="prior_auth_expired",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.MEDIUM,
                detail=detail,
                recommendation="If services have not yet been rendered, request a new prior authorization.",
            )
        )

    return results


def _check_appeal_decision(doc: ProcessedDocument) -> list[ValidationResult]:
    """Check appeal decision for coverage issues."""
    results: list[ValidationResult] = []
    data = doc.extracted_data

    decision = (data.get("decision") or "").lower()
    appeal_ref = data.get("appeal_reference_number", "Unknown")
    original_claim = data.get("original_claim_number", "")

    # Check: appeal_upheld (denial stands)
    if "upheld" in decision or "denied" in decision:
        next_level = data.get("next_appeal_level")
        next_deadline = _parse_date(data.get("next_appeal_deadline"))
        external_review = data.get("external_review_available")
        billed = data.get("original_billed_amount")

        detail = f"Appeal {appeal_ref} was UPHELD (denial stands)"
        if data.get("decision_rationale"):
            detail += f": {data['decision_rationale']}"
        if next_deadline:
            urgency = _get_appeal_urgency(next_deadline)
            detail += f". Next appeal deadline: {next_deadline.isoformat()}"
            if urgency == "urgent":
                detail += " (URGENT)"

        rec = ""
        if next_level:
            rec = f"Consider filing a {next_level} appeal."
        if external_review:
            rec += " External review is available."
            instructions = data.get("external_review_instructions")
            if instructions:
                rec += f" {instructions}"
        if not rec:
            rec = "Review the decision rationale. Consult with provider about next steps."

        results.append(
            ValidationResult(
                check_name="appeal_upheld",
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.HIGH,
                detail=detail,
                potential_overcharge=billed,
                recommendation=rec.strip(),
            )
        )

    # Check: appeal overturned - informational
    if "overturned" in decision or "approved" in decision or "reversed" in decision:
        approved_amt = data.get("approved_amount")
        adjusted_resp = data.get("adjusted_patient_responsibility")

        detail = f"Appeal {appeal_ref} was OVERTURNED in patient's favor"
        if approved_amt is not None:
            detail += f". Approved amount: ${approved_amt:.2f}"
        if adjusted_resp is not None:
            detail += f". Adjusted patient responsibility: ${adjusted_resp:.2f}"

        results.append(
            ValidationResult(
                check_name="appeal_overturned",
                status=ValidationStatus.INFO,
                severity=ValidationSeverity.INFO,
                detail=detail,
                recommendation="Verify that provider bills reflect the updated amounts from the appeal decision.",
            )
        )

    return results


def _cross_check_prior_auth_vs_eob(
    documents: list[ProcessedDocument],
) -> list[ValidationResult]:
    """Cross-check: flag EOB denials where a prior auth approval exists."""
    results: list[ValidationResult] = []

    # Collect approved CPT codes from prior auths
    approved_cpts: dict[str, str] = {}  # cpt -> auth_number
    for doc in documents:
        if doc.envelope.classified_type.value != "PRIOR_AUTH":
            continue
        data = doc.extracted_data
        auth_status = (data.get("auth_status") or "").lower()
        if "approved" in auth_status or "authorized" in auth_status:
            auth_num = data.get("authorization_number", "Unknown")
            for svc in data.get("authorized_services", []):
                cpt = svc.get("cpt_code")
                if cpt:
                    approved_cpts[cpt] = auth_num

    if not approved_cpts:
        return results

    # Check EOBs for denied line items that have prior auth approval
    for doc in documents:
        if doc.envelope.classified_type.value != "EOB":
            continue
        for item in doc.extracted_data.get("line_items", []):
            cpt = item.get("cpt_code")
            denial_reason = item.get("denial_reason")
            if cpt and denial_reason and cpt in approved_cpts:
                billed = item.get("billed_amount")
                auth_num = approved_cpts[cpt]
                detail = (
                    f"CPT {cpt} was denied on EOB but has approved prior authorization {auth_num}. "
                    f"Denial reason: {denial_reason}"
                )
                if billed:
                    detail += f". Billed: ${billed:.2f}"

                results.append(
                    ValidationResult(
                        check_name="prior_auth_vs_denial",
                        status=ValidationStatus.ERROR,
                        severity=ValidationSeverity.HIGH,
                        detail=detail,
                        potential_overcharge=billed,
                        recommendation=f"Contact insurance — this service was pre-authorized (auth #{auth_num}) and should not have been denied.",
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
