"""Validation engine for insurance claims packet cross-document checks."""

from ..schemas.common import ValidationResult, ValidationSeverity
from ..schemas.packet_output import ProcessedDocument
from .billing_reconciliation import run_billing_reconciliation_checks
from .coverage_checks import run_coverage_checks
from .duplicate_detection import run_duplicate_detection
from .math_checks import run_math_checks

__all__ = [
    "run_all_validations",
    "run_math_checks",
    "run_billing_reconciliation_checks",
    "run_duplicate_detection",
    "run_coverage_checks",
]


def run_all_validations(documents: list[ProcessedDocument]) -> list[ValidationResult]:
    """Run all validation checks across documents and return sorted results.

    Executes 11 deterministic checks across 4 validator modules:
    - Math checks: EOB/bill line item sums
    - Billing reconciliation: EOB vs bill cross-document matching
    - Duplicate detection: CPT code duplicates across providers
    - Coverage checks: Denied services, appeal deadlines

    Results are sorted by severity (HIGH first, then MEDIUM, LOW, INFO).
    """
    results: list[ValidationResult] = []

    # Run all validator modules
    results.extend(run_math_checks(documents))
    results.extend(run_billing_reconciliation_checks(documents))
    results.extend(run_duplicate_detection(documents))
    results.extend(run_coverage_checks(documents))

    # Sort by severity: HIGH > MEDIUM > LOW > INFO
    severity_order = {
        ValidationSeverity.HIGH: 0,
        ValidationSeverity.MEDIUM: 1,
        ValidationSeverity.LOW: 2,
        ValidationSeverity.INFO: 3,
    }
    results.sort(key=lambda r: severity_order.get(r.severity, 4))

    return results
