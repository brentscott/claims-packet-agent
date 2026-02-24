# Extending the Claims Packet Agent

A developer guide for adding new document types, validation rules, and customizing the agent for different health insurance workflows.

## Overview

The Claims Packet Agent is designed around a **schema-driven pipeline**. Every document flows through the same 5-step process (parse → classify → extract → validate → summarize), and extending the system means adding configuration and schemas — not rewriting pipeline logic.

There are three common extension scenarios:

1. **Same document types, different layouts** — A new insurer's EOBs look different from the ones we've seen before
2. **New document types** — Supporting forms that don't exist yet (dental EOBs, vision claims, workers comp, etc.)
3. **New validation rules** — Insurer-specific business logic or additional billing checks

This guide walks through each scenario with concrete steps and code examples.

---

## Scenario 1: Onboarding a New Insurer (Same Document Types)

**Example**: UnitedHealthcare EOBs use different field labels and layouts than Aetna EOBs.

**Good news**: This mostly works out of the box. LlamaParse and LlamaCloud's extraction tier handle layout variation at the AI layer — they don't rely on fixed templates, coordinates, or regex. The extraction schemas in `configs/config.json` define *what* fields to pull (e.g., `patient_responsibility`, `allowed_amount`), not *where* they appear on the page.

### What you might need to adjust

If the insurer uses fundamentally different terminology, you may need to update field descriptions in `configs/config.json` to help the extraction model understand. For example, if an insurer uses "Member Obligation" instead of "Patient Responsibility":

```json
"patient_responsibility": {
  "type": ["number", "null"],
  "description": "Total amount the patient owes. May appear as Patient Responsibility, Member Obligation, Your Cost, Amount You Owe, or Balance Due."
}
```

Adding `description` fields to your extraction schema helps LlamaCloud understand what to look for, even when the document uses non-standard terminology.

### Testing a new insurer

1. Collect 3-5 sample documents from the insurer (at minimum: one EOB and one provider bill)
2. Upload them through the UI and review extraction results
3. If critical fields are missing or incorrect, add `description` hints to the relevant fields in `configs/config.json`
4. Re-test until extraction accuracy is satisfactory

---

## Scenario 2: Adding a New Document Type

**Example**: Adding support for a "Vision Claim" that contains optical service codes, lens prescriptions, frame allowances, and contact lens coverage details.

This is a 4-step process that stays entirely within the existing architecture.

### Step 1: Add the DocumentType enum value

In `src/extraction_review/schemas/common.py`, add your new type to the `DocumentType` enum:

```python
class DocumentType(str, Enum):
    """Types of documents in an insurance claims packet."""
    EOB = "EOB"
    CMS1500 = "CMS-1500"
    # ... existing types ...
    VISION_CLAIM = "VISION_CLAIM"    # ← Add here
    UNKNOWN = "UNKNOWN"
```

**Important**: Keep `UNKNOWN` as the last entry.

### Step 2: Create the Pydantic extraction schema

Create a new file `src/extraction_review/schemas/vision_claim.py`:

```python
"""Schema for vision claim documents."""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class VisionServiceLine(BaseModel):
    """Individual vision service line item."""
    service_code: Optional[str] = None
    description: Optional[str] = None
    date_of_service: Optional[date] = None
    billed_amount: Optional[float] = None
    allowed_amount: Optional[float] = None
    insurance_paid: Optional[float] = None
    patient_responsibility: Optional[float] = None


class VisionClaimSchema(BaseModel):
    """Extracted data from a vision claim document."""
    # Patient info
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    member_id: Optional[str] = None
    group_number: Optional[str] = None

    # Provider info
    provider_name: Optional[str] = None
    provider_npi: Optional[str] = None

    # Claim details
    claim_number: Optional[str] = None
    date_of_service: Optional[date] = None
    frame_allowance: Optional[float] = None
    lens_allowance: Optional[float] = None
    contact_lens_allowance: Optional[float] = None
    exam_copay: Optional[float] = None
    total_billed: Optional[float] = None
    total_allowed: Optional[float] = None
    insurance_paid: Optional[float] = None
    patient_responsibility: Optional[float] = None

    # Service lines
    service_lines: List[VisionServiceLine] = Field(default_factory=list)
```

Follow the pattern of existing schemas: use `Optional` with `None` defaults for all fields, use Python native types (`str`, `float`, `date`), and use `List[SubModel]` with `Field(default_factory=list)` for nested arrays.

### Step 3: Add the extraction schema to config.json

Add a new entry in the document-type-specific section of `configs/config.json`:

```json
"VISION_CLAIM": {
  "json_schema": {
    "type": "object",
    "properties": {
      "patient_first_name": { "type": ["string", "null"] },
      "patient_last_name": { "type": ["string", "null"] },
      "frame_allowance": {
        "type": ["number", "null"],
        "description": "Maximum frame benefit amount from vision plan"
      }
    }
  },
  "settings": {
    "extraction_mode": "PREMIUM",
    "citation_bbox": true
  }
}
```

Also add a classification rule in the `classify.rules` section:

```json
{
  "type": "VISION_CLAIM",
  "description": "Vision insurance claim or explanation of benefits for eye exams, eyeglasses, contact lenses, or optical services."
}
```

### Step 4: Register in process_file.py

Add the new type to the schema mapping in the `extract_data` step of `src/extraction_review/process_file.py`:

```python
# In the extract_data step, add to the type-to-config mapping:
config_map["VISION_CLAIM"] = vision_config
```

### That's it for basic support

At this point, the new document type will flow through the full pipeline: LlamaParse will parse it, LlamaCloud will classify it as `VISION_CLAIM`, extraction will pull the structured fields, and the summary step will include it.

---

## Scenario 3: Adding New Validation Rules

Validation checks are where the real business logic lives. Each check is an independent function that follows a simple contract.

### The validation function contract

Every validation check function:
- **Takes**: `list[ProcessedDocument]` (all documents in the packet)
- **Returns**: `ValidationResult` (status, severity, detail, optional recommendation and potential_overcharge)
- **Lives in**: One of the validator modules under `src/extraction_review/validators/`

Here's the anatomy of a validation check:

```python
from ..schemas.common import (
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from ..schemas.packet_output import ProcessedDocument


def vision_frame_overcharge(documents: list[ProcessedDocument]) -> list[ValidationResult]:
    """
    Check if a vision provider is billing more than the plan's frame allowance.
    """
    results = []

    # 1. Find the documents you need
    vision_docs = [
        d for d in documents
        if d.envelope.classified_type.value == "VISION_CLAIM"
    ]

    for doc in vision_docs:
        data = doc.extracted_data

        # 2. Extract the data you need
        frame_allowance = data.get("frame_allowance")
        frame_billed = None
        for line in data.get("service_lines", []):
            if "frame" in (line.get("description") or "").lower():
                frame_billed = line.get("billed_amount")
                break

        if frame_allowance is None or frame_billed is None:
            continue

        # 3. Apply your business logic
        if frame_billed > frame_allowance:
            overcharge = frame_billed - frame_allowance
            results.append(ValidationResult(
                check_name="vision_frame_overcharge",
                status=ValidationStatus.MISMATCH,
                severity=ValidationSeverity.MEDIUM,
                detail=f"Frame charge ${frame_billed:.2f} exceeds plan allowance ${frame_allowance:.2f} by ${overcharge:.2f}.",
                potential_overcharge=overcharge,
                recommendation="Verify frame selection is within plan benefit. Patient may owe the difference.",
            ))

    # 4. Return results (empty list if no issues found)
    return results
```

### Registering your new check

Add your function to the appropriate validator module. For example, if you're adding billing-related checks, add to `billing_reconciliation.py`:

```python
def run_billing_reconciliation_checks(documents: list[ProcessedDocument]) -> list[ValidationResult]:
    results = []
    # ... existing checks ...
    results.extend(vision_frame_overcharge(documents))    # ← Add here
    return results
```

### Creating an entirely new validator module

If your checks don't fit neatly into the existing modules (math, billing, duplicates, coverage), create a new one:

1. Create `src/extraction_review/validators/vision_checks.py` with your check functions and a `run_vision_checks()` entry point
2. Register it in `src/extraction_review/validators/__init__.py`:

```python
from .vision_checks import run_vision_checks

def run_all_validations(documents: list[ProcessedDocument]) -> list[ValidationResult]:
    results = []
    results.extend(run_math_checks(documents))
    results.extend(run_billing_reconciliation_checks(documents))
    results.extend(run_duplicate_detection(documents))
    results.extend(run_coverage_checks(documents))
    results.extend(run_vision_checks(documents))      # ← Add here
    # ... sorting logic ...
    return results
```

---

## Quick Reference: Where Things Live

| What you want to do | Where to change |
|---|---|
| Add a document type enum | `src/extraction_review/schemas/common.py` → `DocumentType` |
| Create an extraction schema | `src/extraction_review/schemas/{doc_type}.py` (new file) |
| Add classification rule | `configs/config.json` → `classify.rules[]` |
| Add extraction config | `configs/config.json` → document-type entry |
| Add a validation check | `src/extraction_review/validators/{module}.py` → add function + register in `run_*_checks()` |
| Add a new validator module | `src/extraction_review/validators/{module}.py` (new file) + register in `__init__.py` |
| Add test PDFs | `tests/generate_test_pdfs.py` → add new scenario builder functions |
| Adjust validation thresholds | `src/extraction_review/validators/` → modify constants in relevant module |

---

## What Does NOT Need to Change

When extending the system, these components work generically and should not require modification:

- **`process_file.py` pipeline logic** — Processes whatever document types come through
- **UI (React frontend)** — Renders whatever `ClaimsPacketOutput`, `ValidationResult`, and `FinancialSummary` data it receives
- **LlamaParse integration** — Parses any document type without configuration
- **Summary generation** — The LLM summarizer works off structured data, not document-type-specific prompts
- **Financial summary calculation** — Aggregates totals from whatever documents are present

---

## Testing Your Extensions

### Generate test PDFs

Add your test scenario to `tests/generate_test_pdfs.py` following the existing pattern. Each scenario is a set of builder functions that create PDF tables using ReportLab:

```bash
# Regenerate all test PDFs including your new scenario
uv run python tests/generate_test_pdfs.py

# Upload the new scenario folder through the UI to test
```

### Add validator unit tests

Add test cases to `tests/test_validators.py`:

```python
def test_vision_frame_overcharge():
    """Test vision frame overcharge detection."""
    docs = [
        _make_doc("VISION_CLAIM", {
            "frame_allowance": 150.00,
            "service_lines": [
                {"description": "Designer Frame", "billed_amount": 275.00}
            ],
        }),
    ]
    results = vision_frame_overcharge(docs)
    assert len(results) == 1
    assert results[0].severity == ValidationSeverity.MEDIUM
    assert results[0].potential_overcharge == 125.00
```

### Run the test suite

```bash
uv run hatch run test
```

---

## Tips for Extension Development

1. **Start with the schema**. Define what data you need to extract before writing any validation logic. The schema drives everything downstream.

2. **Use `Optional[type] = None` for all fields**. Documents are messy — fields will be missing. Your validation logic should handle `None` gracefully.

3. **Keep validation functions independent**. Each check should be self-contained, reading from `ProcessedDocument` data and returning `ValidationResult` objects. No shared state between checks.

4. **Follow severity conventions**:
   - `HIGH` — Patient is being overcharged, critical deadline approaching, denied claim needs action
   - `MEDIUM` — Potential billing error, missing document, minor inconsistency
   - `LOW` — Informational, best-practice suggestion
   - `INFO` — Check completed, no issues found

5. **Add `description` fields to your extraction JSON schema** in `configs/config.json`. These descriptions help LlamaCloud understand what to extract from unfamiliar document layouts.

6. **Use `potential_overcharge`** on `ValidationResult` when a check identifies a specific dollar amount the patient may be overpaying. The financial summary aggregates these automatically.

7. **Test with real documents** as early as possible. Synthetic PDFs validate the logic, but real-world documents expose extraction edge cases (handwritten notes, poor scans, unexpected layouts).
