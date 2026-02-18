"""Billing reconciliation checks comparing EOBs against provider bills."""

from datetime import date

from ..schemas.common import ValidationResult, ValidationSeverity, ValidationStatus
from ..schemas.packet_output import ProcessedDocument


def run_billing_reconciliation_checks(
    documents: list[ProcessedDocument],
) -> list[ValidationResult]:
    """Run billing reconciliation checks between EOBs and bills.

    Checks:
    - eob_vs_bill_amount: Compare EOB patient responsibility vs bill balance
    - line_item_over_allowed: Compare bill CPT charges vs EOB allowed amounts
    - unmatched_eob/unmatched_bill: Flag documents without matching counterpart
    - missing_eobs/missing_bills: Flag when one type exists but not other
    """
    results: list[ValidationResult] = []

    eobs = [d for d in documents if d.envelope.classified_type.value == "EOB"]
    bills = [d for d in documents if d.envelope.classified_type.value == "MEDICAL_BILL"]

    # Check for missing document types
    if eobs and not bills:
        results.append(
            ValidationResult(
                check_name="missing_bills",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.LOW,
                detail="Found EOB(s) but no provider bills. Cannot fully reconcile without bills.",
                recommendation="Obtain bills from providers to verify amounts owed",
            )
        )

    if bills and not eobs:
        results.append(
            ValidationResult(
                check_name="missing_eobs",
                status=ValidationStatus.WARNING,
                severity=ValidationSeverity.MEDIUM,
                detail="Found provider bill(s) but no EOB. Cannot verify insurance processing.",
                recommendation="Request EOB from insurance before paying bills",
            )
        )

    # Match EOBs to bills and run reconciliation
    matched_eobs: set[str] = set()
    matched_bills: set[str] = set()

    for eob in eobs:
        eob_data = eob.extracted_data
        eob_provider = _normalize_provider_name(
            eob_data.get("provider", {}).get("name", "")
        )
        eob_dos_start = _parse_date(eob_data.get("date_of_service_start"))
        eob_dos_end = _parse_date(eob_data.get("date_of_service_end"))

        for bill in bills:
            bill_data = bill.extracted_data
            bill_provider = _normalize_provider_name(
                bill_data.get("provider", {}).get("name", "")
            )
            bill_dos_start = _parse_date(bill_data.get("date_of_service_start"))
            bill_dos_end = _parse_date(bill_data.get("date_of_service_end"))

            # Check if they match (fuzzy provider name + overlapping dates)
            if _providers_match(eob_provider, bill_provider) and _dates_overlap(
                eob_dos_start, eob_dos_end, bill_dos_start, bill_dos_end
            ):
                matched_eobs.add(eob.envelope.doc_id)
                matched_bills.add(bill.envelope.doc_id)

                # Compare amounts
                eob_patient_resp = eob_data.get("total_patient_responsibility")
                bill_balance = bill_data.get("balance_due")

                if (
                    eob_patient_resp is not None
                    and bill_balance is not None
                    and abs(eob_patient_resp - bill_balance) > 0.01
                ):
                    overcharge = bill_balance - eob_patient_resp
                    results.append(
                        ValidationResult(
                            check_name="eob_vs_bill_amount",
                            status=ValidationStatus.MISMATCH,
                            severity=ValidationSeverity.HIGH,
                            detail=f"Bill from {bill_provider or 'provider'} shows balance of ${bill_balance:.2f} but EOB says patient responsibility is ${eob_patient_resp:.2f}",
                            potential_overcharge=overcharge if overcharge > 0 else None,
                            recommendation=f"Contact {bill_provider or 'provider'} to request adjustment to match EOB amount"
                            if overcharge > 0
                            else "Verify with insurance if additional payment is expected",
                        )
                    )

                # Compare line items by CPT
                results.extend(_compare_line_items(eob, bill))

    # Flag unmatched documents
    for eob in eobs:
        if eob.envelope.doc_id not in matched_eobs:
            provider = eob.extracted_data.get("provider", {}).get("name", "Unknown")
            results.append(
                ValidationResult(
                    check_name="unmatched_eob",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.LOW,
                    detail=f"EOB from {provider} could not be matched to any provider bill",
                    recommendation="Obtain corresponding bill from provider",
                )
            )

    for bill in bills:
        if bill.envelope.doc_id not in matched_bills:
            provider = bill.extracted_data.get("provider", {}).get("name", "Unknown")
            results.append(
                ValidationResult(
                    check_name="unmatched_bill",
                    status=ValidationStatus.WARNING,
                    severity=ValidationSeverity.MEDIUM,
                    detail=f"Bill from {provider} could not be matched to any EOB",
                    recommendation="Request EOB from insurance for this service before paying",
                )
            )

    return results


def _compare_line_items(
    eob: ProcessedDocument, bill: ProcessedDocument
) -> list[ValidationResult]:
    """Compare line items between matched EOB and bill."""
    results: list[ValidationResult] = []

    eob_items = eob.extracted_data.get("line_items", [])
    bill_items = bill.extracted_data.get("line_items", [])

    # Build lookup of allowed amounts by CPT from EOB
    eob_allowed_by_cpt: dict[str, float] = {}
    for item in eob_items:
        cpt = item.get("cpt_code")
        allowed = item.get("allowed_amount")
        if cpt and allowed is not None:
            eob_allowed_by_cpt[cpt] = allowed

    # Check each bill line item against allowed amount
    for item in bill_items:
        cpt = item.get("cpt_code")
        amount = item.get("amount")
        if cpt and amount is not None and cpt in eob_allowed_by_cpt:
            allowed = eob_allowed_by_cpt[cpt]
            if amount > allowed + 0.01:
                overcharge = amount - allowed
                results.append(
                    ValidationResult(
                        check_name="line_item_over_allowed",
                        status=ValidationStatus.MISMATCH,
                        severity=ValidationSeverity.MEDIUM,
                        detail=f"Bill charges ${amount:.2f} for CPT {cpt} but EOB allowed amount is only ${allowed:.2f}",
                        potential_overcharge=overcharge,
                        recommendation=f"Request provider adjust CPT {cpt} charge to insurance allowed amount",
                    )
                )

    return results


def _normalize_provider_name(name: str | None) -> str:
    """Normalize provider name for matching."""
    if not name:
        return ""
    return name.lower().strip()


def _providers_match(name1: str, name2: str) -> bool:
    """Check if two provider names likely refer to the same entity."""
    if not name1 or not name2:
        return False

    # Exact match
    if name1 == name2:
        return True

    # Substring containment
    if name1 in name2 or name2 in name1:
        return True

    # Common abbreviations
    abbrev_map = {
        "hospital": "hosp",
        "medical": "med",
        "center": "ctr",
        "healthcare": "health",
    }
    n1 = name1
    n2 = name2
    for full, abbr in abbrev_map.items():
        n1 = n1.replace(full, abbr)
        n2 = n2.replace(full, abbr)
    if n1 == n2 or n1 in n2 or n2 in n1:
        return True

    return False


def _parse_date(value: str | date | None) -> date | None:
    """Parse a date value that may be string or date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    # Try ISO format
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _dates_overlap(
    start1: date | None,
    end1: date | None,
    start2: date | None,
    end2: date | None,
) -> bool:
    """Check if two date ranges overlap or if any dates match."""
    # If we don't have enough date info, assume possible match
    if not any([start1, end1, start2, end2]):
        return True

    # Use single dates for comparison if ranges not complete
    date1 = start1 or end1
    date2 = start2 or end2

    # If we only have single dates, check equality
    if date1 and date2 and not (end1 and end2):
        return date1 == date2

    # Range overlap check
    if start1 and end1 and start2 and end2:
        return start1 <= end2 and start2 <= end1

    # Partial range - be permissive
    return True
