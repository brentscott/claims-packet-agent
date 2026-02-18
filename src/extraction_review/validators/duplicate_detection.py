"""Duplicate CPT code detection across documents and providers."""

from collections import defaultdict
from datetime import date

from ..schemas.common import ValidationResult, ValidationSeverity, ValidationStatus
from ..schemas.packet_output import ProcessedDocument


def run_duplicate_detection(
    documents: list[ProcessedDocument],
) -> list[ValidationResult]:
    """Detect duplicate CPT codes that may indicate double billing.

    Checks:
    - duplicate_cpt_cross_provider: Same CPT+date from different providers
    - duplicate_cpt_same_provider: Same CPT+date appearing 3+ times from same provider
    """
    results: list[ValidationResult] = []

    # Extract all service lines into normalized format
    service_lines = _extract_all_service_lines(documents)

    # Group by CPT + service date
    # Key: (cpt_code, service_date) -> list of {source, doc_id, provider, amount, description}
    by_cpt_date: dict[tuple[str, date | None], list[dict]] = defaultdict(list)
    for line in service_lines:
        if line.get("cpt_code"):
            key = (line["cpt_code"], line.get("service_date"))
            by_cpt_date[key].append(line)

    for (cpt_code, service_date), occurrences in by_cpt_date.items():
        if len(occurrences) < 2:
            continue

        # Group by provider
        by_provider: dict[str, list[dict]] = defaultdict(list)
        for occ in occurrences:
            provider = occ.get("provider") or "Unknown"
            by_provider[provider].append(occ)

        # Check for cross-provider duplicates
        providers = list(by_provider.keys())
        if len(providers) > 1:
            # Get unique doc_ids involved
            doc_ids = set(occ.get("doc_id") for occ in occurrences)
            if len(doc_ids) > 1:
                total_amount = sum(
                    occ.get("amount", 0) or 0
                    for occ in occurrences
                    if occ.get("amount")
                )
                date_str = (
                    service_date.isoformat()
                    if service_date
                    else "unknown date"
                )
                provider_list = ", ".join(providers[:3])
                if len(providers) > 3:
                    provider_list += f" and {len(providers) - 3} more"

                results.append(
                    ValidationResult(
                        check_name="duplicate_cpt_cross_provider",
                        status=ValidationStatus.WARNING,
                        severity=ValidationSeverity.MEDIUM,
                        detail=f"CPT {cpt_code} on {date_str} appears from multiple providers: {provider_list}. Total charged: ${total_amount:.2f}",
                        potential_overcharge=total_amount / 2
                        if total_amount > 0
                        else None,
                        recommendation=f"Verify if CPT {cpt_code} was legitimately performed by multiple providers or if this is duplicate billing",
                    )
                )

        # Check for same-provider duplicates (3+ occurrences)
        for provider, provider_occs in by_provider.items():
            if len(provider_occs) >= 3:
                total_amount = sum(
                    occ.get("amount", 0) or 0
                    for occ in provider_occs
                    if occ.get("amount")
                )
                date_str = (
                    service_date.isoformat()
                    if service_date
                    else "unknown date"
                )

                results.append(
                    ValidationResult(
                        check_name="duplicate_cpt_same_provider",
                        status=ValidationStatus.INFO,
                        severity=ValidationSeverity.LOW,
                        detail=f"CPT {cpt_code} on {date_str} appears {len(provider_occs)} times from {provider}. May be intentional for multiple units.",
                        recommendation="Verify units billed match services received",
                    )
                )

    return results


def _extract_all_service_lines(documents: list[ProcessedDocument]) -> list[dict]:
    """Extract and normalize service lines from all document types."""
    lines: list[dict] = []

    for doc in documents:
        doc_type = doc.envelope.classified_type.value
        data = doc.extracted_data
        doc_id = doc.envelope.doc_id
        provider = data.get("provider", {}).get("name")

        if doc_type == "EOB":
            for item in data.get("line_items", []):
                lines.append(
                    {
                        "cpt_code": item.get("cpt_code"),
                        "service_date": _parse_date(item.get("service_date")),
                        "description": item.get("description"),
                        "amount": item.get("billed_amount"),
                        "source": "EOB",
                        "doc_id": doc_id,
                        "provider": provider,
                    }
                )

        elif doc_type == "MEDICAL_BILL":
            for item in data.get("line_items", []):
                lines.append(
                    {
                        "cpt_code": item.get("cpt_code"),
                        "service_date": _parse_date(item.get("service_date")),
                        "description": item.get("description"),
                        "amount": item.get("amount"),
                        "source": "MEDICAL_BILL",
                        "doc_id": doc_id,
                        "provider": provider,
                    }
                )

        elif doc_type == "CMS-1500":
            provider = data.get("provider", {}).get("name")
            for item in data.get("service_lines", []):
                lines.append(
                    {
                        "cpt_code": item.get("cpt_code"),
                        "service_date": _parse_date(item.get("date_of_service_from")),
                        "description": None,
                        "amount": item.get("charges"),
                        "source": "CMS-1500",
                        "doc_id": doc_id,
                        "provider": provider,
                    }
                )

        elif doc_type == "UB-04":
            provider = data.get("provider", {}).get("name") or data.get("facility_name")
            for item in data.get("revenue_lines", []):
                lines.append(
                    {
                        "cpt_code": item.get("hcpcs_code"),
                        "service_date": _parse_date(item.get("service_date")),
                        "description": item.get("description"),
                        "amount": item.get("total_charges"),
                        "source": "UB-04",
                        "doc_id": doc_id,
                        "provider": provider,
                    }
                )

        elif doc_type == "LAB_REPORT":
            provider = (
                data.get("performing_lab", {}).get("name")
                or data.get("ordering_provider", {}).get("name")
            )
            for item in data.get("test_results", []):
                lines.append(
                    {
                        "cpt_code": item.get("cpt_code"),
                        "service_date": _parse_date(data.get("collection_date")),
                        "description": item.get("test_name"),
                        "amount": None,
                        "source": "LAB_REPORT",
                        "doc_id": doc_id,
                        "provider": provider,
                    }
                )

        elif doc_type == "DENTAL_CLAIM":
            billing = data.get("billing_provider", {}).get("name") or provider
            for item in data.get("service_lines", []):
                lines.append(
                    {
                        "cpt_code": item.get("cdt_code"),
                        "service_date": _parse_date(item.get("service_date")),
                        "description": item.get("description"),
                        "amount": item.get("fee"),
                        "source": "DENTAL_CLAIM",
                        "doc_id": doc_id,
                        "provider": billing,
                    }
                )

        elif doc_type == "ITEMIZED_STATEMENT":
            for item in data.get("charges", []):
                lines.append(
                    {
                        "cpt_code": item.get("cpt_code"),
                        "service_date": _parse_date(item.get("service_date")),
                        "description": item.get("description"),
                        "amount": item.get("amount"),
                        "source": "ITEMIZED_STATEMENT",
                        "doc_id": doc_id,
                        "provider": provider,
                    }
                )

    return lines


def _parse_date(value: str | date | None) -> date | None:
    """Parse a date value that may be string or date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None
