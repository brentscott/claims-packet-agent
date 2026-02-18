# Claims Packet Agent

An AI-powered insurance claims document analyzer built on [LlamaAgents](https://developers.llamaindex.ai/python/llamaagents/llamactl/getting-started/). Upload a packet of insurance documents (EOBs, medical bills, pharmacy receipts, lab reports, claim forms) and get back a reconciled financial summary with billing error detection, duplicate charge identification, and plain-English recommended actions.

## What It Does

The agent processes multiple insurance documents as a single packet through a 5-step pipeline:

1. **Parse** — Extracts text from uploaded PDFs using LlamaParse (agentic tier, multimodal)
2. **Classify** — Identifies each document as one of 11 types: EOB, CMS-1500, UB-04, Medical Bill, Pharmacy Receipt, Lab Report, Dental Claim, Prior Authorization, Appeal Decision, Itemized Statement, or Unknown
3. **Extract** — Pulls structured data from each document using type-specific schemas (85+ fields for EOBs, CDT codes for dental claims, authorization details for prior auths, etc.)
4. **Validate** — Runs 16 deterministic cross-document checks to find billing errors, overcharges, duplicate charges, denied claims, coverage gaps, and prior auth conflicts
5. **Summarize** — Generates a patient-friendly narrative with prioritized action items

### Validation Checks

The validation engine runs entirely without LLM involvement (deterministic logic), making it fast, testable, and predictable:

- **Math checks (5):** Verifies internal arithmetic on EOBs and bills (line item sums, balance calculations)
- **Billing reconciliation (4):** Compares what your EOB says you owe vs. what the provider is billing you — catches overcharges (supports medical bills and itemized statements)
- **Duplicate detection (2):** Finds the same CPT/CDT code billed on the same date by different providers (supports dental claims and itemized statements)
- **Coverage checks (5):** Identifies denied claims, zero-coverage services, tracks appeal deadlines, flags denied/expired prior authorizations, and detects when appeal decisions uphold or overturn denials
- **Cross-document checks (bonus):** Catches EOB denials that contradict an approved prior authorization — a strong signal the insurer made an error

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

2. Create a `.env` file with your API keys:

   ```bash
   LLAMA_CLOUD_API_KEY=your_llama_cloud_key
   OPENAI_API_KEY=your_openai_key    # or see LLM Configuration below
   ```

3. Run locally:

   ```bash
   uvx llamactl serve
   ```

   This starts both the Python backend workflows and the React UI with hot reload.

4. Open the UI in your browser (URL shown in terminal output), upload your insurance documents, and review the analysis.

### Deploy to LlamaCloud

```bash
uvx llamactl deploy --name claims-packet-agent
```

## LLM Configuration

The agent uses an LLM in only one place: generating the plain-English summary narrative in Step 5. All document parsing, classification, and extraction are handled by LlamaCloud APIs, and all 11 validation checks are fully deterministic (no LLM).

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

| Scenario | Files | What It Tests |
|---|---|---|
| `scenario_1_billing_errors` | 5 | EOB math errors, overcharges on hospital and lab bills |
| `scenario_2_denied_claim` | 4 | Fully denied EOB with orthopedic and imaging bills |
| `scenario_3_clean_packet` | 3 | Clean packet that should pass all checks with no issues |
| `scenario_4_multi_provider` | 5 | ER visit with 4 different providers and a single facility EOB |
| `scenario_5_dental_billing_mismatch` | 3 | Dental claim + EOB where bill charges full amount instead of allowed amount |
| `scenario_6_prior_auth_vs_denial` | 3 | Approved prior auth but EOB denies the same CPT codes — triggers cross-document check |
| `scenario_7_appeal_overturned_itemized` | 3 | Denied EOB, overturned appeal decision, and itemized surgical statement still showing full balance |
| `scenario_8_denied_prior_auth_appeal_upheld` | 2 | Denied prior auth followed by upheld appeal with external review available |

To regenerate the sample PDFs, run `python tests/generate_test_pdfs.py` (requires `reportlab`).

## Project Structure

```
claims-packet-agent/
├── configs/
│   └── config.json                # Extraction schemas, classification rules, parse settings
├── src/extraction_review/
│   ├── process_file.py            # Main 5-step workflow
│   ├── metadata_workflow.py       # Schema provider for the UI
│   ├── config.py                  # Configuration models
│   ├── clients.py                 # LlamaCloud client setup
│   ├── schemas/                   # Pydantic models for 11 document types + output
│   │   ├── common.py              # Shared types (DocumentType, ValidationResult, etc.)
│   │   ├── packet_output.py       # ClaimsPacketOutput, FinancialSummary
│   │   ├── eob.py                 # Explanation of Benefits
│   │   ├── cms1500.py             # CMS-1500 professional claim form
│   │   ├── ub04.py                # UB-04 institutional claim form
│   │   ├── medical_bill.py        # Provider bills
│   │   ├── pharmacy.py            # Pharmacy receipts
│   │   ├── lab_report.py          # Lab reports
│   │   ├── dental_claim.py        # ADA dental claims (CDT codes)
│   │   ├── prior_auth.py          # Prior authorization letters
│   │   ├── appeal_decision.py     # Appeal decision notices
│   │   └── itemized_statement.py  # Itemized hospital/facility statements
│   └── validators/                # 16 deterministic cross-document checks
│       ├── __init__.py            # Orchestrator
│       ├── math_checks.py         # Internal arithmetic validation
│       ├── billing_reconciliation.py  # EOB vs. bill comparison
│       ├── duplicate_detection.py # Duplicate CPT code detection
│       └── coverage_checks.py     # Denied claims and coverage gaps
├── ui/                            # React + TypeScript frontend
│   └── src/
│       ├── pages/
│       │   ├── HomePage.tsx       # Upload interface and packet grid
│       │   └── ItemPage.tsx       # Packet detail view with file navigator
│       ├── components/
│       │   └── PacketSummaryView.tsx  # Claims analysis results display
│       └── lib/
│           ├── WorkflowProgress.tsx   # Real-time processing status log
│           └── ...
├── sample_docs/                   # 8 synthetic test scenarios (git-ignored)
├── tests/                         # Unit tests for validators + workflow
├── pyproject.toml                 # Dependencies + llamactl deployment config
└── .env                           # API keys (not committed)
```

## Tech Stack

| Component | Technology |
|---|---|
| Workflow engine | LlamaIndex Workflows (`llama-index-workflows`) |
| Document parsing | LlamaParse (agentic tier, multimodal) |
| Classification | LlamaCloud Classifier API |
| Data extraction | LlamaCloud Extraction API (PREMIUM mode with bounding boxes) |
| Validation | Deterministic Python (no LLM) |
| Summary generation | Configurable LLM (default: OpenAI gpt-4o-mini) |
| Frontend | React 19 + TypeScript + Vite + @llamaindex/ui |
| Deployment | llamactl / LlamaCloud |

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
