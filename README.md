# Claims Packet Agent

An AI-powered insurance claims document analyzer built on [LlamaAgents](https://developers.llamaindex.ai/python/llamaagents/llamactl/getting-started/). Upload a packet of insurance documents (EOBs, medical bills, pharmacy receipts, lab reports, claim forms) and get back a reconciled financial summary with billing error detection, duplicate charge identification, and plain-English recommended actions.

## Problem Statement

Medical billing errors affect an estimated 80% of hospital bills in the United States. Patients routinely receive Explanation of Benefits (EOBs), provider bills, pharmacy receipts, and lab reports that contain arithmetic errors, overcharges beyond insurer-allowed amounts, duplicate CPT codes billed across providers, and denied services the patient shouldn't owe. Reviewing these documents manually is:

- **Overwhelming**: A single ER visit can generate 5-8 separate documents across multiple providers
- **Error-prone**: Cross-referencing EOB allowed amounts against provider bills requires line-item matching across different formats
- **Time-sensitive**: Appeal deadlines are often 30-180 days from the EOB date, and patients miss them
- **Financially consequential**: Billing errors average hundreds of dollars per incident, and patients often pay without questioning

The Claims Packet Agent automates this entire review process — parsing, classifying, extracting structured data, running deterministic validation checks, and producing a clear summary with recommended actions and potential savings.

## Solution

The agent processes multiple insurance documents as a single packet through a 5-step pipeline:

1. **Parse** — Extracts text from uploaded PDFs using LlamaParse (agentic tier, multimodal)
2. **Classify** — Identifies each document as one of 11 types: EOB, CMS-1500, UB-04, Medical Bill, Pharmacy Receipt, Lab Report, Dental Claim, Prior Authorization, Appeal Decision, Itemized Statement, or Unknown
3. **Extract** — Pulls structured data from each document using type-specific schemas (85+ fields for EOBs, CDT codes for dental claims, authorization details for prior auths, etc.)
4. **Validate** — Runs 16 deterministic cross-document checks to find billing errors, overcharges, duplicate charges, denied claims, coverage gaps, and prior auth conflicts
5. **Summarize** — Generates a patient-friendly narrative with prioritized action items

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Document Upload Portal                  │
│    (EOBs, Medical Bills, Pharmacy Receipts, Lab Reports) │
└───────────────────┬─────────────────────────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │   Step 1: Parse (LlamaParse)      │
    │   - Agentic tier, multimodal      │
    │   - Extract text, tables, images  │
    │   - Bounding box coordinates      │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  Step 2: Classify (LlamaCloud)    │
    │  - 11 health insurance doc types  │
    │  - High-confidence classification │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  Step 3: Extract (LlamaCloud)     │
    │  - Type-specific PREMIUM schemas  │
    │  - 85+ fields per document type   │
    │  - Bounding box coordinates       │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  Step 4: Validate (Deterministic) │
    │  - 16 cross-document checks       │
    │  - Math, billing, duplicates      │
    │  - Coverage gaps, appeal tracking │
    │  - No LLM (pure Python)           │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  Step 5: Summarize (LLM)          │
    │  - Patient-friendly narrative     │
    │  - Prioritized action items       │
    │  - Potential savings calculation   │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │       Claims Packet Dashboard     │
    │  - Financial summary cards        │
    │  - Validation findings + severity │
    │  - Document-by-document review    │
    │  - Approve / Reject workflow      │
    └───────────────────────────────────┘
```

## Supported Document Types (11)

1. **Explanation of Benefits (EOB)** — Insurance payment summary with allowed amounts, deductibles, copays, coinsurance, and appeal deadlines
2. **CMS-1500** — Professional claim form with CPT codes, diagnosis codes, and provider information
3. **UB-04** — Institutional claim form for hospital and facility charges
4. **Medical Bill** — Provider bills with line-item charges, balances due, and payment history
5. **Pharmacy Receipt** — Prescription costs, copays, and insurance coverage details
6. **Lab Report** — Laboratory test results with billing codes and charges
7. **Dental Claim** — ADA dental claim forms with CDT procedure codes
8. **Prior Authorization** — Authorization letters with approval/denial status, expiration dates, and approved service codes
9. **Appeal Decision** — Appeal outcome notices (upheld, overturned, partially overturned) with external review options
10. **Itemized Statement** — Hospital/facility itemized charge breakdowns with revenue codes
11. **Unknown** — Fallback for unrecognized document types

## Validation Checks (16)

The validation engine runs entirely without LLM involvement (deterministic logic), making it fast, testable, and predictable:

### Math Checks (5)

1. **EOB Line Item Sum** — Verifies that individual service line amounts sum to the stated total
2. **Bill Line Item Sum** — Verifies that bill line items sum to the stated balance
3. **Deductible + Copay + Coinsurance** — Checks that the deductible, copay, and coinsurance breakdown equals the patient responsibility total
4. **Allowed vs Billed** — Verifies allowed amount does not exceed billed amount
5. **Balance Calculation** — Checks that billed minus insurance payment equals patient responsibility

### Billing Reconciliation (4)

6. **EOB vs Bill Amount** — Compares what your EOB says you owe vs. what the provider is billing you — catches overcharges
7. **Line Item Over Allowed** — Compares bill CPT charges vs. EOB allowed amounts at the line-item level
8. **Unmatched Documents** — Flags EOBs without matching bills or vice versa
9. **Missing Counterparts** — Flags when bills exist but no EOB explains the charges

### Duplicate Detection (2)

10. **Cross-Provider Duplicates** — Finds the same CPT/CDT code billed on the same date by different providers
11. **Same-Provider Duplicates** — Detects the same code appearing 3+ times from the same provider on the same date

### Coverage Checks (5)

12. **Claim Denied** — Identifies fully denied claims with appeal deadline tracking
13. **Zero Coverage** — Flags line items where allowed amount is $0 but billed amount is significant
14. **Prior Auth Denied/Expired** — Detects denied or expired prior authorizations
15. **Appeal Outcome** — Tracks whether appeal decisions upheld or overturned original denials
16. **Prior Auth vs EOB Denial** — Cross-document check: catches EOB denials that contradict an approved prior authorization — a strong signal the insurer made an error

### Example Output

For a packet with an EOB, hospital bill, pharmacy receipt, lab report, and CMS-1500:

- Detects a $300 overcharge where the hospital bills $678 but the EOB says patient responsibility is $378
- Flags a duplicate CPT 80053 (metabolic panel) billed by both the hospital and an outside lab
- Identifies a math error on a provider bill where line items don't sum to the stated total
- Calculates total potential savings of $540

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) 18+ and pnpm
- A [LlamaCloud](https://cloud.llamaindex.ai/) account and API key
- An LLM provider API key (see [LLM Configuration](#llm-configuration) below)

### Setup

1. Clone the repository and navigate to the project:

   ```bash
   cd claims-packet-agent
   ```

2. Copy the environment template and add your API keys:

   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. Install backend dependencies:

   ```bash
   uv sync
   ```

4. Install frontend dependencies:

   ```bash
   cd ui
   pnpm install
   cd ..
   ```

### Running Locally

```bash
# Start the full application (backend + frontend with hot reload)
uvx llamactl serve
```

Open the UI in your browser (URL shown in terminal output), upload your insurance documents, and review the analysis.

### Running Tests

```bash
# Run all tests
uv run hatch run test

# Run validator unit tests only
uv run pytest tests/test_validators.py -v

# Generate synthetic test PDFs (requires reportlab)
uv run python tests/generate_test_pdfs.py

# Run linting and type checking
uv run hatch run all-check
```

### Deploy to LlamaCloud

```bash
uvx llamactl deploy --name claims-packet-agent
```

## LLM Configuration

The agent uses an LLM in only one place: generating the plain-English summary narrative in Step 5. All document parsing, classification, and extraction are handled by LlamaCloud APIs, and all 16 validation checks are fully deterministic (no LLM).

By default, the agent uses OpenAI's `gpt-4o-mini`. To change this, edit the `get_llm()` function in `src/extraction_review/process_file.py`.

### Using Open-Source Models (HIPAA / On-Prem)

For healthcare deployments where HIPAA compliance requires keeping data on-premises, you can swap in an open-source model with minimal changes:

**Ollama (local, recommended for on-prem):**

```bash
pip install llama-index-llms-ollama
```

```python
# In src/extraction_review/process_file.py
def get_llm() -> LLM:
    from llama_index.llms.ollama import Ollama
    return Ollama(model="llama3.1:latest", request_timeout=120.0)
```

**LlamaCPP (local, no server needed):**

```bash
pip install llama-index-llms-llamacpp
```

```python
def get_llm() -> LLM:
    from llama_index.llms.llama_cpp import LlamaCPP
    return LlamaCPP(model_path="/path/to/model.gguf")
```

**Other hosted providers (Together AI, Groq, Replicate, etc.):**

LlamaIndex supports [40+ LLM integrations](https://docs.llamaindex.ai/en/stable/module_guides/models/llms/). Install the corresponding package and update `get_llm()`.

When using a local model, also update `pyproject.toml`:
- Replace `llama-index-llms-openai` with your chosen package in `dependencies`
- Remove `OPENAI_API_KEY` from `required_env_vars`

**Note:** For a fully on-prem deployment, the LlamaCloud APIs (parsing, classification, extraction) would also need to be replaced with self-hosted alternatives or local libraries. The validation engine and summary generation already run entirely locally.

## Sample Data

The `sample_docs/` directory (git-ignored) contains 8 synthetic test scenarios with 28 PDFs across all supported document types. Each scenario folder is named to describe what it tests:

| # | Scenario | Files | What It Tests |
|---|----------|-------|---|
| 1 | `scenario_1_billing_errors` | 5 | EOB math errors, overcharges on hospital and lab bills |
| 2 | `scenario_2_denied_claim` | 4 | Fully denied EOB with orthopedic and imaging bills |
| 3 | `scenario_3_clean_packet` | 3 | Clean packet that should pass all checks with no issues |
| 4 | `scenario_4_multi_provider` | 5 | ER visit with 4 different providers and a single facility EOB |
| 5 | `scenario_5_dental_billing_mismatch` | 3 | Dental claim + EOB where bill charges full amount instead of allowed amount |
| 6 | `scenario_6_prior_auth_vs_denial` | 3 | Approved prior auth but EOB denies the same CPT codes — triggers cross-document check |
| 7 | `scenario_7_appeal_overturned_itemized` | 3 | Denied EOB, overturned appeal decision, and itemized surgical statement still showing full balance |
| 8 | `scenario_8_denied_prior_auth_appeal_upheld` | 2 | Denied prior auth followed by upheld appeal with external review available |

To regenerate the sample PDFs, run `uv run python tests/generate_test_pdfs.py` (requires `reportlab`).

## Performance Benchmarks

- **Document Parsing**: ~2 seconds per document (LlamaParse, agentic tier)
- **Classification**: ~0.5 seconds per document (LlamaCloud Classifier)
- **Extraction**: ~1 second per document (LlamaCloud Extraction, PREMIUM mode)
- **Validation**: ~0.05 seconds per packet (deterministic, Python — all 16 checks)
- **Summary Generation**: ~3 seconds per packet (LLM, gpt-4o-mini)
- **End-to-End**: ~8-12 seconds for a 4-document packet

## Configuration

### Validation Thresholds (Customizable)

Key thresholds are defined in the validator modules under `src/extraction_review/validators/`:

- **Overcharge detection**: Any positive difference between provider bill and EOB patient responsibility triggers a flag
- **Duplicate CPT threshold**: Same code + same date from different providers triggers cross-provider duplicate
- **Same-provider duplicate**: 3+ occurrences of the same code from one provider on the same date
- **Appeal deadline tracking**: Extracts appeal deadline from EOBs and calculates days remaining
- **Prior auth expiration**: Compares authorization expiration date against service dates
- **Zero-allowed threshold**: Any line item where allowed amount is $0 but billed amount > $0

### LlamaCloud Configuration

Extraction schemas are defined in a unified configuration file at `configs/config.json`. This file contains type-specific schemas for all 11 document types, classification rules, and parse settings. Each document type's schema specifies the structured fields to extract with their types and descriptions, used by LlamaCloud's PREMIUM extraction tier.

## Project Structure

```
claims-packet-agent/
├── README.md                           # This file
├── EXTENDING.md                        # Developer guide for adding doc types + validators
├── .env.example                        # Environment template
├── pyproject.toml                      # Python project configuration
├── uv.lock                             # Dependency lock file
│
├── configs/
│   └── config.json                     # Extraction schemas, classification rules, parse settings
│
├── src/extraction_review/
│   ├── __init__.py
│   ├── process_file.py                 # Main 5-step workflow
│   ├── metadata_workflow.py            # Schema provider for the UI
│   ├── config.py                       # Configuration models
│   ├── clients.py                      # LlamaCloud client setup
│   ├── json_util.py                    # JSON schema utilities
│   │
│   ├── schemas/                        # Pydantic models for 11 document types + output
│   │   ├── common.py                   # Shared types (DocumentType, ValidationResult, etc.)
│   │   ├── packet_output.py            # ClaimsPacketOutput, FinancialSummary
│   │   ├── eob.py                      # Explanation of Benefits (85+ fields)
│   │   ├── cms1500.py                  # CMS-1500 professional claim form
│   │   ├── ub04.py                     # UB-04 institutional claim form
│   │   ├── medical_bill.py             # Provider bills
│   │   ├── pharmacy.py                 # Pharmacy receipts
│   │   ├── lab_report.py               # Lab reports
│   │   ├── dental_claim.py             # ADA dental claims (CDT codes)
│   │   ├── prior_auth.py               # Prior authorization letters
│   │   ├── appeal_decision.py          # Appeal decision notices
│   │   └── itemized_statement.py       # Itemized hospital/facility statements
│   │
│   ├── validators/                     # 16 deterministic cross-document checks
│   │   ├── __init__.py                 # Orchestrator
│   │   ├── math_checks.py             # Internal arithmetic validation (5 checks)
│   │   ├── billing_reconciliation.py   # EOB vs. bill comparison (4 checks)
│   │   ├── duplicate_detection.py      # Duplicate CPT code detection (2 checks)
│   │   └── coverage_checks.py         # Denied claims and coverage gaps (5 checks)
│   │
│   └── testing_utils/                  # Test infrastructure
│       ├── classify.py, extract.py, parse.py  # Mocked LlamaCloud operations
│       ├── pipelines.py                # End-to-end workflow testing
│       └── server.py                   # Local test server setup
│
├── ui/                                 # React 19 + TypeScript frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── App.tsx                     # Root application component
│   │   ├── main.tsx                    # Entry point
│   │   ├── index.css                   # Global styles (Tailwind)
│   │   ├── pages/
│   │   │   ├── HomePage.tsx            # Upload interface and packet grid
│   │   │   └── ItemPage.tsx            # Packet detail view with file navigator
│   │   ├── components/
│   │   │   └── PacketSummaryView.tsx   # Claims analysis results display
│   │   └── lib/
│   │       ├── WorkflowProgress.tsx    # Real-time workflow progress display
│   │       ├── MetadataProvider.tsx    # React context for metadata
│   │       ├── ToolbarContext.tsx      # Toolbar state management
│   │       ├── client.ts              # API client configuration
│   │       ├── config.ts              # Frontend configuration
│   │       ├── export.ts              # JSON export utilities
│   │       ├── useMetadata.ts         # Custom metadata hook
│   │       └── utils.ts              # Shared utility functions
│   └── postcss.config.mjs
│
├── tests/
│   ├── conftest.py                     # pytest fixtures
│   ├── test_workflow.py                # Full workflow integration tests
│   ├── test_validators.py             # Unit tests for validation logic
│   └── generate_test_pdfs.py          # Synthetic PDF generator (28 PDFs, 8 scenarios)
│
└── sample_docs/                        # Generated test PDF fixtures (gitignored)
    ├── scenario_1_billing_errors/
    ├── scenario_2_denied_claim/
    ├── scenario_3_clean_packet/
    ├── scenario_4_multi_provider/
    ├── scenario_5_dental_billing_mismatch/
    ├── scenario_6_prior_auth_vs_denial/
    ├── scenario_7_appeal_overturned_itemized/
    └── scenario_8_denied_prior_auth_appeal_upheld/
```

## Tech Stack

| Component | Technology |
|---|---|
| Workflow engine | LlamaIndex Workflows (`llama-index-workflows`) |
| Document parsing | LlamaParse (agentic tier, multimodal) |
| Classification | LlamaCloud Classifier API |
| Data extraction | LlamaCloud Extraction API (PREMIUM mode with bounding boxes) |
| Validation | Deterministic Python (no LLM) — 16 checks across 4 modules |
| Summary generation | Configurable LLM (default: OpenAI gpt-4o-mini) |
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS |
| UI components | @llamaindex/ui + shadcn/ui |
| Deployment | llamactl / LlamaCloud |
| Testing | pytest, synthetic PDF generation (reportlab) |

## What Makes This Unique

1. **Hybrid AI-Deterministic Architecture**: AI handles unstructured document parsing and classification; pure Python validates structured results with auditable, testable logic
2. **Cross-Document Intelligence**: Compares EOBs against provider bills, detects when prior authorizations contradict denial decisions, and reconciles charges across multiple providers
3. **16 Deterministic Validation Checks**: No LLM dependency for validation — results are fast, repeatable, and explainable
4. **Healthcare Billing Domain Depth**: Understands CPT/CDT codes, deductible/copay/coinsurance breakdowns, prior authorization workflows, appeal deadlines, and insurer remark codes
5. **Smart Savings Deduplication**: Validation engine avoids double-counting overlapping denial checks when calculating potential patient savings
6. **Multi-Document Packet Processing**: Handles 5-8 documents as a unified packet rather than isolated files, enabling cross-document reconciliation
7. **Patient-Friendly Output**: Translates complex billing jargon into plain-English action items with specific dollar amounts and deadlines
8. **Production-Ready**: Deployment via llamactl, structured logging, error handling, and extensible schema system

## Linting and Type Checking

Python:

```bash
uv run hatch run lint
uv run hatch run typecheck
uv run hatch run test
# run all at once
uv run hatch run all-fix
```

UI (from the `ui/` directory):

```bash
pnpm run lint
pnpm run format
pnpm run build
# run all checks
pnpm run all-check
```

## Contributing

We welcome contributions! Areas of interest:
- Additional document type support (dental EOBs, vision claims, workers comp)
- Enhanced validation checks (network status verification, timely filing)
- UI/UX improvements
- Performance optimization
- Additional test scenarios

## License

MIT License - see LICENSE file for details

## Contact

**Author**: Brent Scott

**Email**: bscott3125@gmail.com

**Repository**: [https://github.com/brentscott/claims-packet-agent](https://github.com/brentscott/claims-packet-agent)

## Acknowledgments

- Built with LlamaIndex Workflows, LlamaParse, and LlamaCloud
- Health insurance billing expertise and CPT/CDT code validation
- Community feedback and feature requests
